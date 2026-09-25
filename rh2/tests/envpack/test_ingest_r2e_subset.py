"""R2E-Gym-Subset 来源材料接线的验收（R2E 接线 R-a，2026-09-20）。

覆盖计划 §5.1 R-a 行：48 行 ingest 往返；公开面逐键扫描无 expected / gold / prompt；环境包与三份 bundle 的摘要关系；
SWE 既有 ingest 产物逐字节不变、默认来源集合仍是只含 SWE 的 216 题；gold 固定上游实现，比较纳入文件集合与
应用后的内容（不比补丁字节）。
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from repoharness2.envpack import ingest_r2e_subset as r2e
from repoharness2.envpack import ingest_swegym_lite as swe
from repoharness2.envpack.bundles_v2 import (
    EnvironmentPackageV1,
    PrivateGradingBundleR2E,
    PrivateGradingBundleV2,
    R2EHiddenTestFile,
    build_environment_package,
    r2e_hidden_tests_tree_digest,
)
from repoharness2.envpack.prepared_tasks import prepare_tasks
from repoharness2.envpack.r2e_parsers import (
    R2E_DATASET_REVISION,
    R2E_RULE_SOURCE_SHA256,
    R2E_RULE_SOURCE_VENDOR_RELPATH,
    extract_gold_patch,
    gold_patch_included_paths,
)
from repoharness2.envpack.training_view import (
    DEFAULT_TASK_SOURCES,
    HostGradingView,
    TrustedTaskController,
    TrustedViewError,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/：共享合成夹具 r2e_synthetic_tasks
from r2e_synthetic_tasks import (  # noqa: E402
    R2E_FIX_COMMIT,
    R2E_IMAGE_HEAD,
    ingest_r2e_synthetic,
    make_commit_doc,
    make_r2e_facts_doc,
    make_r2e_row,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIX = R2E_FIX_COMMIT
HEAD = R2E_IMAGE_HEAD


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 合成夹具（小而完整：一行来源 + 一条镜像事实）：构造器定义在 tests/r2e_synthetic_tasks.py，
# 与 tests/adapters_miles/test_r2e_group_transport.py 共用；本模块只留沿用的私有别名
# ---------------------------------------------------------------------------

_commit_doc = make_commit_doc
_row = make_r2e_row
_facts_doc = make_r2e_facts_doc
_ingest = ingest_r2e_synthetic


# ---------------------------------------------------------------------------
# 单题构造与 fail-closed
# ---------------------------------------------------------------------------


def test_one_row_builds_four_faces_with_the_expected_split():
    result = _ingest()
    public, grading, validation, package = (
        result.public_bundles[0], result.grading_bundles[0], result.validation_bundles[0], result.packages[0],
    )
    iid = f"demo__{FIX}"
    assert public.instance_id == grading.instance_id == validation.instance_id == package.instance_id == iid
    assert package.task_id == f"r2e_gym_subset::{iid}" and package.source == "r2e_gym_subset"
    assert public.base_commit == grading.base_commit == package.base_commit == HEAD  # 镜像 HEAD，不是来源行的符号形式
    assert public.repo == "demo" and public.workdir == "/testbed"
    assert public.image_manifest_digest == "sha256:" + "c" * 64
    # 评分面：期望原文逐字保留、入口原文、隐藏测试清单按路径排序
    assert grading.expected_output_json == _row()["expected_output_json"]
    assert grading.expected_map() == {"TestCore.test_x": "PASSED", "TestCore.test_legacy": "FAILED"}
    assert [f.path for f in grading.hidden_test_files] == ["__init__.py", "test_1.py"]
    assert grading.rule_source_id == "prime_envs_c4d04dfe" and grading.spec_vendor_id == "r2e_gym_subset_e8b9fcbc"
    # gold：只含非测试 .py（tests/ 与 .rst 被上游规则排除）
    assert "pkg/core.py" in validation.golden_patch
    assert "tests/test_core.py" not in validation.golden_patch and "notes.rst" not in validation.golden_patch
    # 包记录：三份摘要 + provenance 三 digest（规则源 digest 由注册表派生）
    assert package.public_bundle_digest == public.digest()
    assert package.grading_bundle_digest == grading.digest()
    assert package.validation_bundle_digest == validation.digest()
    assert package.spec_vendor_json_sha256 == "sha256:" + R2E_RULE_SOURCE_SHA256
    r2e.verify_r2e_bundle_relations_non_authoritative(package, public, grading, validation)


def test_public_face_carries_no_private_source_material():
    result = _ingest()
    row = _row()
    dumped = json.dumps(result.public_bundles[0].model_dump(mode="json"), ensure_ascii=False)
    for private_field in ("expected_output_json", "parsed_commit_content", "execution_result_content",
                          "modified_files", "modified_entity_summaries", "relevant_files", "prompt"):
        assert f'"{private_field}"' not in dumped
    assert "test_legacy" not in dumped and row["prompt"] not in dumped and "x = 2" not in dumped


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda row, doc: row.update(new_column=1), "未列字段"),
        (lambda row, doc: row.pop("prompt"), "缺字段"),
        (lambda row, doc: row.update(docker_image="namanjain12/other_final:" + FIX), "镜像引用不符"),
        (lambda row, doc: doc["tasks"][0].update(expected_n=3), "期望键数"),
        (lambda row, doc: row.update(expected_output_json=json.dumps({"a": "SKIPPED"})), "状态"),
        (lambda row, doc: row.update(expected_output_json='{"a": "PASSED", "a": "FAILED"}'), "重复键"),
        (lambda row, doc: row.update(
            expected_output_json=json.dumps({"T.a - x": "FAILED", "T.a - y": "FAILED"})), "碰撞"),
        (lambda row, doc: row.update(problem_statement="see " + row["expected_output_json"]), "原样包含"),
        (lambda row, doc: doc["tasks"][0]["git"].update(head_is_ancestor_of_fix="no"), "HEAD 事实"),
        (lambda row, doc: doc["tasks"][0]["run_tests_sh"].update(text="pytest -q"), "run_tests.sh"),
        (lambda row, doc: doc["tasks"][0]["image"].update(workdir="/app"), "workdir"),
        (lambda row, doc: doc["tasks"][0].update(source_revision="0" * 40), "revision"),
    ],
)
def test_ingest_fails_closed_on_input_drift(mutate, message):
    row, doc = _row(), _facts_doc()
    mutate(row, doc)
    with pytest.raises((r2e.R2EIngestError, ValueError), match=message):
        _ingest(rows=[row], facts_doc=doc)


def test_row_set_and_fact_set_must_be_equal_and_rows_unique():
    other = "d" * 40
    with pytest.raises(r2e.R2EIngestError, match="集合不相等"):
        _ingest(rows=[_row(), _row(commit=other)], expected_task_count=2)
    with pytest.raises(r2e.R2EIngestError, match="重复 commit_hash"):
        _ingest(rows=[_row(), _row()], expected_task_count=2)
    with pytest.raises(r2e.R2EIngestError, match="数量异常"):
        _ingest(expected_task_count=48)


def test_gold_without_any_non_test_python_change_is_rejected():
    row = _row()
    doc = _commit_doc()
    doc["file_diffs"] = [fd for fd in doc["file_diffs"] if fd["header"]["file"]["path"] != "pkg/core.py"]
    row["parsed_commit_content"] = json.dumps(doc)
    with pytest.raises(r2e.R2EIngestError, match="重建不出 gold"):
        _ingest(rows=[row])


# ---------------------------------------------------------------------------
# 评分面模型
# ---------------------------------------------------------------------------


def test_r2e_bundle_is_self_attesting():
    g = _ingest().grading_bundles[0]
    payload = g.model_dump(mode="json")
    assert PrivateGradingBundleR2E.model_validate(payload) == g
    for field, value, message in [
        ("expected_output_json", '{"a": "PASSED"}', "expected_output_json_sha256"),
        ("run_tests_sh", "bash evil.sh", "run_tests_sh_sha256"),
        ("hidden_tests_tree_sha256", "sha256:" + "0" * 64, "树摘要"),
        ("instance_id", "demo__" + "e" * 40, "instance_id"),
        ("repo_key_lower", "Demo", "小写投影"),
        ("source_revision", "0" * 40, "revision 前缀"),
    ]:
        bad = copy.deepcopy(payload)
        bad[field] = value
        with pytest.raises(ValueError, match=message):
            PrivateGradingBundleR2E.model_validate(bad)
    with pytest.raises(ValueError, match="路径不安全"):
        R2EHiddenTestFile(path="../escape.py", sha256=_sha("x"))
    with pytest.raises(ValueError, match="字节码缓存"):
        R2EHiddenTestFile(path="__pycache__/test_1.cpython-39.pyc", sha256=_sha("x"))


def test_hidden_tests_tree_digest_matches_the_container_side_sha256sum_pipeline(tmp_path):
    files = {"test_1.py": b"print(1)\n", "__init__.py": b"", "conftest.py": b"import pytest\n", "Zeta.py": b"z\n"}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "test_1.cpython-39.pyc").write_bytes(b"\x00")
    ours = r2e_hidden_tests_tree_digest((n, "sha256:" + hashlib.sha256(d).hexdigest()) for n, d in files.items())
    sha256sum = shutil.which("sha256sum") or shutil.which("gsha256sum")
    if sha256sum is None:
        pytest.skip("本机没有 sha256sum（macOS 默认只有 shasum）；容器内口径由 R-c 的 Docker 夹具往返验证")
    cmd = (
        f"cd {tmp_path} && find . -type f -not -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z "
        f"| xargs -0 {sha256sum} | {sha256sum}"
    )
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True).stdout.split()[0]
    assert ours == "sha256:" + out


def test_package_builder_rejects_a_source_that_does_not_match_the_grading_face():
    result = _ingest()
    with pytest.raises(ValueError, match="不匹配"):
        build_environment_package(
            public=result.public_bundles[0], grading=result.grading_bundles[0],
            validation=result.validation_bundles[0], source="swe_gym_lite",
            raw_archive_sha256="sha256:" + "1" * 64, image_manifest_keyed_sha256="sha256:" + "2" * 64,
        )


# ---------------------------------------------------------------------------
# 落盘 / 严格加载 / pins
# ---------------------------------------------------------------------------


def _tmp_repo(tmp_path: Path) -> tuple[Path, str]:
    """小型仓库根：合成来源行 + 事实表 + revision + 规则源副本，封板后返回 (root, pins 记录 sha256)。"""

    import importlib.util

    root = tmp_path / "repo"
    for rel, payload in [
        (r2e.R2E_RAW_ARCHIVE_RELPATH, (json.dumps(_row()) + "\n").encode()),
        (r2e.R2E_SOURCE_REVISION_RELPATH, (R2E_DATASET_REVISION + "\n").encode()),
        (r2e.R2E_IMAGE_FACTS_RELPATH, json.dumps(_facts_doc()).encode()),
        (R2E_RULE_SOURCE_VENDOR_RELPATH, (REPO_ROOT / R2E_RULE_SOURCE_VENDOR_RELPATH).read_bytes()),
        (r2e.R2E_MATERIAL_REVISIONS_RELPATH,
         json.dumps({"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": []}).encode()),
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    spec = importlib.util.spec_from_file_location("build_r2e_ingest", REPO_ROOT / "rh2/scripts/build_r2e_ingest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.seal_pins(root) == 0
    assert module.seal_pins(root) == 2  # 封板记录不覆盖
    return root, hashlib.sha256((root / r2e.R2E_PINS_RELPATH).read_bytes()).hexdigest()


def test_pins_three_level_verification_and_input_drift(tmp_path, capsys):
    root, sealed = _tmp_repo(tmp_path)
    pins = r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)
    assert pins.rule_source == R2E_RULE_SOURCE_SHA256
    with pytest.raises(r2e.R2EIngestError, match="digest 不符"):
        r2e.load_and_verify_r2e_pins(root)  # 合成 pins 记录不等于代码常量
    (root / r2e.R2E_SOURCE_REVISION_RELPATH).write_text("0" * 40 + "\n")
    with pytest.raises(r2e.R2EIngestError, match="输入漂移"):
        r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)


def test_write_then_strict_load_round_trip_and_tamper_detection(tmp_path):
    root, sealed = _tmp_repo(tmp_path)
    pins = r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)
    facts = r2e.load_r2e_image_facts(root, pins)
    rows, revision = r2e.load_r2e_rows(root, pins)
    result = r2e.ingest_r2e_subset(
        rows=rows, image_facts=facts, raw_archive_sha256="sha256:" + pins.raw_archive,
        image_facts_sha256="sha256:" + pins.image_facts, source_revision=revision, expected_task_count=1,
    )
    out = tmp_path / "out"
    first = r2e.write_r2e_ingest_outputs(result, out, pins=pins)
    again = r2e.write_r2e_ingest_outputs(result, tmp_path / "out2", pins=pins)
    assert first == again  # 无时间戳：同一输入逐字节相同
    ids = {p.instance_id for p in result.packages}
    loaded = r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids=ids)
    assert [p.digest() for p in loaded.packages] == [p.digest() for p in result.packages]

    with pytest.raises(r2e.R2EIngestError, match="可信任务全集"):
        r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids=ids | {"x__" + "0" * 40})
    target = out / "grading_bundles_r2e_v0.jsonl"
    target.write_text(target.read_text().replace("PASSED", "FAILED", 1))
    with pytest.raises(r2e.R2EIngestError, match="digest 与提交记录不符"):
        r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids=ids)


def test_strict_relation_check_binds_package_to_image_facts_and_pins(tmp_path):
    root, sealed = _tmp_repo(tmp_path)
    pins = r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)
    facts = r2e.load_r2e_image_facts(root, pins)
    result = _ingest()  # provenance digest 是占位值 → 与封板 pins 不符
    with pytest.raises(r2e.R2EIngestError, match="封板 pin"):
        r2e.verify_r2e_package_relations(
            result.packages[0], result.public_bundles[0], result.grading_bundles[0], result.validation_bundles[0],
            pins=pins, image_facts=facts,
        )


# ---------------------------------------------------------------------------
# 多来源 controller 与评分视图
# ---------------------------------------------------------------------------


def _swe_result() -> swe.IngestResult:
    from repoharness2.envpack.bundles import PublicTaskBundle
    from repoharness2.envpack.bundles_v2 import ValidationOnlyBundle, build_private_grading_bundle

    statement = "bug"
    public = PublicTaskBundle(
        instance_id="getmoto__moto-5752", repo="getmoto/moto", base_commit="0" * 40,
        image="xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest", image_manifest_digest="sha256:" + "9" * 64,
        problem_statement=statement, problem_statement_sha256=_sha(statement),
    )
    grading = build_private_grading_bundle(
        instance_id="getmoto__moto-5752", repo="getmoto/moto", version="4.1", base_commit="0" * 40,
        test_patch="diff --git a/t.py b/t.py\n+x\n", fail_to_pass=["t.py::a"], pass_to_pass=[],
    )
    patch = "diff --git a/m.py b/m.py\n-bug\n+fix\n"
    validation = ValidationOnlyBundle(instance_id="getmoto__moto-5752", golden_patch=patch, golden_patch_sha256=_sha(patch))
    package = build_environment_package(
        public=public, grading=grading, validation=validation,
        raw_archive_sha256="sha256:" + "1" * 64, image_manifest_keyed_sha256="sha256:" + "2" * 64,
    )
    return swe.IngestResult(packages=[package], public_bundles=[public], grading_bundles=[grading],
                            validation_bundles=[validation])


def test_mixed_source_controller_dispatches_grading_view_by_schema_id(tmp_path):
    controller = TrustedTaskController.build_for_tests_from_ingest_result(_swe_result(), _ingest())
    swe_id, r2e_id = "swe_gym_lite::getmoto__moto-5752", f"r2e_gym_subset::demo__{FIX}"
    assert controller.task_ids() == tuple(sorted([swe_id, r2e_id]))
    rv = controller.rollout_view(r2e_id)
    gv = controller.grading_view(r2e_id, environment_package_digest=rv.environment_package_digest)
    assert isinstance(gv.grading, PrivateGradingBundleR2E) and gv.source == "r2e_gym_subset"
    swe_gv = controller.grading_view(
        swe_id, environment_package_digest=controller.rollout_view(swe_id).environment_package_digest)
    assert isinstance(swe_gv.grading, PrivateGradingBundleV2)
    # JSON 往返后仍按 schema_id 选对类型（prepared 产物的加载路径）
    assert isinstance(HostGradingView.model_validate(json.loads(gv.model_dump_json())).grading, PrivateGradingBundleR2E)
    assert isinstance(HostGradingView.model_validate(json.loads(swe_gv.model_dump_json())).grading, PrivateGradingBundleV2)
    # 来源写 swe、评分面却是 R2E 形状：没有构造路径
    forged = gv.model_dump(mode="python")
    forged.update(source="swe_gym_lite", task_id=f"swe_gym_lite::demo__{FIX}")
    with pytest.raises(ValueError, match="不匹配"):
        HostGradingView.model_validate(forged)
    # 公开 / 私有两份 prepared 产物：R2E 行与 SWE 行同形
    manifest = prepare_tasks(controller, out_dir=tmp_path / "pub", private_dir=tmp_path / "priv")
    assert {t.source for t in manifest.tasks} == {"swe_gym_lite", "r2e_gym_subset"}
    views = (tmp_path / "pub" / "rollout_task_views.jsonl").read_text()
    assert "test_legacy" not in views and "expected_output_json" not in views and "hidden_test" not in views


def test_same_task_twice_across_results_is_rejected():
    with pytest.raises(TrustedViewError, match="重复 task_id"):
        TrustedTaskController.build_for_tests_from_ingest_result(_ingest(), _ingest())


# ---------------------------------------------------------------------------
# 真实 48 题 + SWE 不变性
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def trusted_r2e() -> r2e.TrustedR2EIngest:
    return r2e.load_trusted_r2e_ingest_outputs(REPO_ROOT)


def test_real_48_tasks_load_through_the_trusted_entry(trusted_r2e):
    result = trusted_r2e.result
    assert len(result.packages) == len(trusted_r2e.image_facts) == 48
    assert {p.source for p in result.packages} == {"r2e_gym_subset"}
    assert sorted({g.repo for g in result.grading_bundles}) == [
        "aiohttp", "coveragepy", "datalad", "numpy", "orange3", "pandas", "pillow", "scrapy"]
    entry_kinds = {"xvfb": 0, "pytest": 0, "custom": 0}
    for g in result.grading_bundles:
        text = g.run_tests_sh
        entry_kinds["xvfb" if "xvfb-run" in text else "pytest" if "-m pytest -rA r2e_tests" in text else "custom"] += 1
    assert entry_kinds == {"xvfb": 7, "pytest": 40, "custom": 1}
    # 公开面逐题复查：不含期望原文 / gold / 任何非公开来源字段名
    by_grading = {g.instance_id: g for g in result.grading_bundles}
    by_validation = {v.instance_id: v for v in result.validation_bundles}
    for public in result.public_bundles:
        dumped = json.dumps(public.model_dump(mode="json"), ensure_ascii=False)
        assert by_grading[public.instance_id].expected_output_json not in dumped
        assert by_validation[public.instance_id].golden_patch not in dumped
        assert not {"expected_output_json", "parsed_commit_content", "prompt"} & set(public.model_dump())


def test_default_sources_stay_swe_only_and_r2e_is_an_explicit_opt_in():
    assert DEFAULT_TASK_SOURCES == ("swe_gym_lite",)
    default = TrustedTaskController.from_repo_root(REPO_ROOT)
    assert len(default.task_ids()) == 216 and all(t.startswith("swe_gym_lite::") for t in default.task_ids())
    both = TrustedTaskController.from_repo_root(REPO_ROOT, sources=("swe_gym_lite", "r2e_gym_subset"))
    assert len(both.task_ids()) == 264
    assert set(default.task_ids()) < set(both.task_ids())
    only_r2e = TrustedTaskController.from_repo_root(REPO_ROOT, sources=("r2e_gym_subset",))
    assert len(only_r2e.task_ids()) == 48 and all(t.startswith("r2e_gym_subset::") for t in only_r2e.task_ids())
    for bad in ((), ("swe_gym_lite", "swe_gym_lite"), ("r2e",)):
        with pytest.raises(TrustedViewError):
            TrustedTaskController.from_repo_root(REPO_ROOT, sources=bad)


def test_swe_ingest_artifacts_reserialize_to_identical_bytes():
    """枚举放宽 + 联合类型之后，SWE 四面模型的序列化仍与已提交产物逐字节相同。"""

    trusted = swe.load_trusted_ingest_outputs(REPO_ROOT)
    recorded = json.loads((REPO_ROOT / swe.INGEST_OUT_RELPATH / swe.INGEST_MANIFEST_NAME).read_text())["files"]
    with tempfile.TemporaryDirectory() as td:
        digests = swe.write_ingest_outputs(trusted.result, Path(td), pins=trusted.pins)
    for name, ent in recorded.items():
        assert digests[name] == ent["sha256"], name
    assert digests[swe.INGEST_MANIFEST_NAME] == swe.INGEST_MANIFEST_SHA256_PIN
    assert all(isinstance(p, EnvironmentPackageV1) and p.source == "swe_gym_lite" for p in trusted.result.packages)


def test_gold_follows_the_pinned_upstream_rule_and_reproduces_the_source_new_files(trusted_r2e):
    """B 线 B2：不比补丁字节，比纳入文件集合与应用后的内容。这里直接对来源的 new_file_content 比，比"与独立 runner
    互比"更强；纳入文件集合另与事实表里独立 runner 的 `l4_gold_patch.included` 对照。"""

    if shutil.which("git") is None:
        pytest.skip("需要 git")
    pins = trusted_r2e.pins
    rows, _ = r2e.load_r2e_rows(REPO_ROOT, pins)
    facts_raw = {t["commit_hash"]: t for t in json.loads((REPO_ROOT / r2e.R2E_IMAGE_FACTS_RELPATH).read_text())["tasks"]}
    by_validation = {v.instance_id: v for v in trusted_r2e.result.validation_bundles}
    for row in rows:
        commit_doc = json.loads(row["parsed_commit_content"])
        included = gold_patch_included_paths(commit_doc)
        assert sorted(included) == sorted(facts_raw[row["commit_hash"]]["l4_gold_patch"]["included"])
        gold = extract_gold_patch(commit_doc)
        assert gold == by_validation[f"{row['repo_name']}__{row['commit_hash']}"].golden_patch
        by_path = {fd["header"]["file"]["path"]: fd for fd in commit_doc["file_diffs"]}
        with tempfile.TemporaryDirectory() as td:
            for path in included:
                target = Path(td) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                old = by_path[path].get("old_file_content")
                if old:
                    target.write_text(old, encoding="utf-8", newline="")
            subprocess.run(["git", "init", "-q", td], check=True)
            applied = subprocess.run(["git", "-C", td, "apply", "--whitespace=nowarn", "-"],
                                     input=gold.encode("utf-8"), capture_output=True)
            assert applied.returncode == 0, (row["commit_hash"], applied.stderr[:200])
            for path in included:
                target = Path(td) / path
                got = target.read_text(encoding="utf-8") if target.exists() else ""
                assert got == (by_path[path].get("new_file_content") or ""), (row["commit_hash"], path)


# ---------------------------------------------------------------------------
# 材料修订（用户 2026-09-24 批准 T0-1 / T0-2 之后加入）
# ---------------------------------------------------------------------------


def _rev(**over) -> dict:
    base = {
        "revision_id": "r2e-mr-001", "instance_id": "demo__" + "a" * 40, "kind": r2e.REVISION_KIND_EXPECTED,
        "target": "expected_output_json",
        "edits": [{"old": '"TestCore.test_legacy": "FAILED"', "new": '"TestCore.test_legacy": "PASSED"'}],
        "sha256_before": "", "sha256_after": "", "revised_file": None,
        "expected_change": {"changed": {"TestCore.test_legacy": ["FAILED", "PASSED"]}, "added": {}, "removed": []},
        "decision_ref": "test", "reason": "test", "evidence": ["test"],
    }
    base.update(over)
    return base


def _expected_rev_doc(row: dict, **over) -> dict:
    text = row["expected_output_json"]
    after = text.replace('"TestCore.test_legacy": "FAILED"', '"TestCore.test_legacy": "PASSED"', 1)
    ent = _rev(sha256_before=_sha(text), sha256_after=_sha(after))
    ent.update(over)
    return {"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": [ent]}


_REVISED_FILE = "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/files/demo/"


def _with_content(revs: dict, content: bytes) -> dict:
    """parse 只给结构；revised_content 在正式流程里由 load_r2e_material_revisions 读文件附上，这里直接附。"""

    return {iid: tuple(replace(r, revised_content=content) for r in rs) for iid, rs in revs.items()}


def test_expected_revision_is_replayed_from_the_source_text_and_marked_on_the_grading_face():
    row = _row()
    revs = r2e.parse_r2e_material_revisions(_expected_rev_doc(row))
    result = _ingest([row], revisions=revs)
    g = result.grading_bundles[0]
    assert g.material_revisions == ["r2e-mr-001"]
    assert g.expected_map() == {"TestCore.test_x": "PASSED", "TestCore.test_legacy": "PASSED"}
    assert _ingest([_row()]).grading_bundles[0].material_revisions == []  # 无修订 = 来源原件
    # 原文摘要对不上 / 片段不唯一：拒
    with pytest.raises(r2e.R2EIngestError, match="sha256_before"):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(_expected_rev_doc(row, sha256_before=_sha("x"))))
    with pytest.raises(r2e.R2EIngestError, match="恰好 1 次"):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(_expected_rev_doc(
            row, edits=[{"old": '"TestCore.test_absent": "FAILED"', "new": '"TestCore.test_absent": "PASSED"'}])))
    # 文本替换改了键名：实际变化（删一个键、加一个键）与声明（改一个状态）不符 → 拒
    renamed = row["expected_output_json"].replace('"TestCore.test_legacy": "FAILED"', '"TestCore.test_other": "FAILED"', 1)
    with pytest.raises(r2e.R2EIngestError, match="expected_change 不符"):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(_expected_rev_doc(
            row, edits=[{"old": '"TestCore.test_legacy"', "new": '"TestCore.test_other"'}], sha256_after=_sha(renamed))))
    # 文本替换类不许声明增删键（增删键必须走整份期望替换）
    with pytest.raises(r2e.R2EIngestError, match="只许改状态值"):
        r2e.parse_r2e_material_revisions(_expected_rev_doc(
            row, expected_change={"changed": {}, "added": {"TestCore.test_other": "FAILED"}, "removed": ["TestCore.test_legacy"]}))


def test_expected_file_replace_may_add_and_remove_keys_only_exactly_as_declared():
    """fixture 恢复后参数化用例展开（例 r2e-mr-007）：删掉原 ERROR 键、加上展开后的键；声明必须与重算差异逐键相同。"""
    row = _row()
    source = row["expected_output_json"]
    revised = json.dumps({"TestCore.test_x": "PASSED", "TestCore.test_legacy[a]": "PASSED", "TestCore.test_legacy[b]": "FAILED"}, indent=4)
    change = {"changed": {}, "added": {"TestCore.test_legacy[a]": "PASSED", "TestCore.test_legacy[b]": "FAILED"},
              "removed": ["TestCore.test_legacy"]}

    def doc(**over):
        return _expected_rev_doc(row, kind=r2e.REVISION_KIND_EXPECTED_FILE, edits=None, sha256_before=_sha(source),
                                 sha256_after=_sha(revised), revised_file=_REVISED_FILE + "expected_output.json",
                                 expected_change=change, **over)

    revs = _with_content(r2e.parse_r2e_material_revisions(doc()), revised.encode())
    g = _ingest([row], revisions=revs).grading_bundles[0]
    assert g.expected_map() == json.loads(revised) and g.expected_output_json_sha256 == _sha(revised)
    assert r2e.expected_key_delta(next(iter(revs.values()))) == 1  # 事实表记 2 键，修订后 3 键
    with pytest.raises(r2e.R2EIngestError, match="load_r2e_material_revisions"):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(doc()))  # 没附修订后内容
    wrong = dict(change, added={"TestCore.test_legacy[a]": "PASSED", "TestCore.test_legacy[b]": "PASSED"})
    with pytest.raises(r2e.R2EIngestError, match="expected_change 不符"):
        _ingest([row], revisions=_with_content(r2e.parse_r2e_material_revisions(
            _expected_rev_doc(row, kind=r2e.REVISION_KIND_EXPECTED_FILE, edits=None, sha256_before=_sha(source),
                              sha256_after=_sha(revised), revised_file=_REVISED_FILE + "expected_output.json",
                              expected_change=wrong)), revised.encode()))
    with pytest.raises(r2e.R2EIngestError, match="非法状态词"):
        r2e.parse_r2e_material_revisions(_expected_rev_doc(
            row, kind=r2e.REVISION_KIND_EXPECTED_FILE, edits=None, revised_file=_REVISED_FILE + "e.json",
            expected_change={"changed": {}, "added": {"TestCore.test_y": "SKIPPED"}, "removed": []}))
    with pytest.raises(r2e.R2EIngestError, match="不用 edits"):
        r2e.parse_r2e_material_revisions(doc(**{}) | {"revisions": [dict(doc()["revisions"][0], edits=[{"old": "a", "new": "b"}])]})


def test_hidden_test_revision_needs_the_source_text_and_changes_the_tree_digest():
    original = "t"  # 与合成镜像事实里 test_1.py 的内容一致（sha256(b"t")）
    revised = "u"
    row = _row()
    row["execution_result_content"] = json.dumps({"test_file_names": ["test_1.py"], "test_file_codes": [original]})
    doc = {"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": [_rev(
        kind=r2e.REVISION_KIND_HIDDEN_TEST, target="test_1.py", edits=[{"old": "t", "new": "u"}], expected_change=None,
        sha256_before=_sha(original), sha256_after=_sha(revised), revised_file=_REVISED_FILE + "r2e_tests/test_1.py")]}
    revs = r2e.parse_r2e_material_revisions(doc)
    result = _ingest([row], revisions=revs)
    g = result.grading_bundles[0]
    assert dict((f.path, f.sha256) for f in g.hidden_test_files)["test_1.py"] == _sha(revised)
    unrevised = _ingest([_row()]).grading_bundles[0]
    assert g.hidden_tests_tree_sha256 != unrevised.hidden_tests_tree_sha256
    # 来源行没有原文 → 无法重放，拒
    with pytest.raises(r2e.R2EIngestError, match="原文"):
        _ingest([_row()], revisions=revs)


def test_hidden_test_file_add_accepts_binary_content_and_rejects_existing_targets():
    """新增隐藏测试文件（例 r2e-mr-003 的夹具 egg、r2e-mr-006 的私有 conftest）：目标原本不得存在，内容可为二进制。"""
    row = _row()
    egg = b"PK\x03\x04\x00\xffbinary"

    def doc(**over):
        ent = _rev(kind=r2e.REVISION_KIND_HIDDEN_ADD, target="test.egg", edits=None, expected_change=None,
                   sha256_before=None, sha256_after="sha256:" + hashlib.sha256(egg).hexdigest(),
                   revised_file=_REVISED_FILE + "r2e_tests/test.egg")
        ent.update(over)
        return {"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": [ent]}

    revs = _with_content(r2e.parse_r2e_material_revisions(doc()), egg)
    g = _ingest([row], revisions=revs).grading_bundles[0]
    files = dict((f.path, f.sha256) for f in g.hidden_test_files)
    assert files["test.egg"] == "sha256:" + hashlib.sha256(egg).hexdigest() and "test_1.py" in files
    assert g.hidden_tests_tree_sha256 == r2e_hidden_tests_tree_digest(tuple(sorted(files.items())))
    assert g.expected_map() == _ingest([_row()]).grading_bundles[0].expected_map()  # 只加文件不改期望
    with pytest.raises(r2e.R2EIngestError, match="已存在"):
        _ingest([row], revisions=_with_content(r2e.parse_r2e_material_revisions(doc(target="test_1.py")), egg))
    with pytest.raises(r2e.R2EIngestError, match="sha256_after"):
        _ingest([row], revisions=_with_content(r2e.parse_r2e_material_revisions(doc()), egg + b"x"))
    with pytest.raises(r2e.R2EIngestError, match="必须为 null"):
        r2e.parse_r2e_material_revisions(doc(sha256_before=_sha("t")))


def test_load_attaches_revised_content_after_checking_its_digest(tmp_path):
    root, sealed = _tmp_repo(tmp_path)
    pins = r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)
    body = b"\x00egg"
    rel = _REVISED_FILE + "r2e_tests/test.egg"
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(body)
    ent = _rev(kind=r2e.REVISION_KIND_HIDDEN_ADD, target="test.egg", edits=None, expected_change=None,
               sha256_before=None, sha256_after="sha256:" + hashlib.sha256(body).hexdigest(), revised_file=rel)
    (root / r2e.R2E_MATERIAL_REVISIONS_RELPATH).write_text(
        json.dumps({"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": [ent]}), encoding="utf-8")
    revs = r2e.load_r2e_material_revisions(root, pins)
    assert next(iter(revs.values()))[0].revised_content == body
    (root / rel).write_bytes(body + b"!")
    with pytest.raises(r2e.R2EIngestError, match="sha256_after"):
        r2e.load_r2e_material_revisions(root, pins)


def test_consumption_check_binds_the_grading_face_to_the_sealed_revisions(tmp_path):
    root, sealed = _tmp_repo(tmp_path)
    pins = r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)
    facts = r2e.load_r2e_image_facts(root, pins)
    rows, revision = r2e.load_r2e_rows(root, pins)
    revs = r2e.parse_r2e_material_revisions(_expected_rev_doc(rows[0]))
    result = r2e.ingest_r2e_subset(
        rows=rows, image_facts=facts, raw_archive_sha256="sha256:" + pins.raw_archive,
        image_facts_sha256="sha256:" + pins.image_facts, source_revision=revision, expected_task_count=1, revisions=revs,
    )
    args = (result.packages[0], result.public_bundles[0], result.grading_bundles[0], result.validation_bundles[0])
    r2e.verify_r2e_package_relations(*args, pins=pins, image_facts=facts, revisions=revs)
    with pytest.raises(r2e.R2EIngestError, match="修订标记"):
        r2e.verify_r2e_package_relations(*args, pins=pins, image_facts=facts)  # 不给修订单：修订过的评分面被拒
    out = tmp_path / "out"
    r2e.write_r2e_ingest_outputs(result, out, pins=pins, revisions=revs)
    ids = {p.instance_id for p in result.packages}
    r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids=ids, revisions=revs)
    with pytest.raises(r2e.R2EIngestError, match="material_revisions"):
        r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids=ids)


def test_revision_list_rejects_orphans_duplicates_and_unsafe_paths():
    row = _row()
    with pytest.raises(r2e.R2EIngestError, match="不存在的任务"):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(_expected_rev_doc(row, instance_id="demo__" + "e" * 40)))
    doc = _expected_rev_doc(row)
    doc["revisions"].append(dict(doc["revisions"][0]))
    with pytest.raises(r2e.R2EIngestError, match="重复"):
        r2e.parse_r2e_material_revisions(doc)
    for bad in ("../x.py", "/abs.py", "a/__pycache__/x.pyc", "a//b.py", "./x.py"):
        with pytest.raises(r2e.R2EIngestError, match="不安全"):
            r2e.parse_r2e_material_revisions({"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": [_rev(
                kind=r2e.REVISION_KIND_HIDDEN_ADD, target=bad, edits=None, expected_change=None, sha256_before=None,
                sha256_after=_sha("b"), revised_file=_REVISED_FILE + "x.py")]})
    with pytest.raises(r2e.R2EIngestError, match="schema_id"):
        r2e.parse_r2e_material_revisions({"schema_id": "rh2.s2_r2e.material_revisions.v1", "revisions": []})


def test_real_revisions_are_exactly_the_user_approved_ones(trusted_r2e):
    """封板修订单 = 用户逐项批准的 T0-1 / T0-2（09-24）、T0-5 / T0-6 代表题（09-24 晚）与 T0-6 第二步 / T0-7 方案 B
    （09-24 夜），其余 37 题无修订。"""
    revs = trusted_r2e.revisions
    assert {iid: [r.revision_id for r in rs] for iid, rs in revs.items()} == {
        "coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae": ["r2e-mr-001"],
        "datalad__58ba5165234cb16de0e8463ee75097362099835f": ["r2e-mr-002"],
        "pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199": ["r2e-mr-006", "r2e-mr-007"],
        "scrapy__cfed9b6659c90e0799361911b1d72ed127edf471": ["r2e-mr-003", "r2e-mr-004", "r2e-mr-005"],
        "pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf": ["r2e-mr-008", "r2e-mr-009"],
        "pandas__294cbc8d1faa15ba245391c5624752ecebd7f63b": ["r2e-mr-010", "r2e-mr-011"],
        "pandas__877876098c88fbf9dae2eb5cdcbecd52c6ffdd2d": ["r2e-mr-012", "r2e-mr-013"],
        "pandas__f656217a06b31e48474702036e0a5c49f664186c": ["r2e-mr-014", "r2e-mr-015"],
        "pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0": ["r2e-mr-016", "r2e-mr-017"],
        "pandas__7dd34ea7a121ce4282ce095b058c5c46568f07af": ["r2e-mr-018", "r2e-mr-019"],
        "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040": ["r2e-mr-020"],
    }
    by_grading = {g.instance_id: g for g in trusted_r2e.result.grading_bundles}
    assert all(not g.material_revisions for iid, g in by_grading.items() if iid not in revs)
    cov = by_grading["coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae"].expected_map()
    assert cov["MockingProtectionTest.test_os_path_exists"] == "PASSED"
    assert sum(v != "PASSED" for v in cov.values()) == 0 and len(cov) == 15
    dat = by_grading["datalad__58ba5165234cb16de0e8463ee75097362099835f"]
    rev = revs[dat.instance_id][0]
    revised_bytes = (REPO_ROOT / rev.revised_file).read_bytes()
    assert revised_bytes.startswith(b"from .test_2 import (\n")
    assert dict((f.path, f.sha256) for f in dat.hidden_test_files)["test_1.py"] == rev.sha256_after
    pan = by_grading["pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199"]
    pmap = pan.expected_map()
    assert len(pmap) == 237 and "test_groupby_quantile_NA_float" not in pmap
    assert pmap["test_groupby_quantile_NA_float[Float32]"] == "PASSED" and sum(v != "PASSED" for v in pmap.values()) == 0
    assert "conftest.py" in {f.path for f in pan.hidden_test_files}
    scr = by_grading["scrapy__cfed9b6659c90e0799361911b1d72ed127edf471"]
    assert scr.expected_map() == {k: "PASSED" for k in scr.expected_map()} and len(scr.expected_map()) == 9
    egg = next(r for r in revs[scr.instance_id] if r.target == "test.egg")
    assert egg.kind == r2e.REVISION_KIND_HIDDEN_ADD and egg.revised_content.startswith(b"PK")  # 真实 egg 是 zip
    # T0-6 第二步：另 6 道 pandas 题补私有 conftest 后期望全 PASSED（键数 = 修复后 gold 试跑的键数）
    for iid, n_keys in {"pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf": 162, "pandas__294cbc8d1faa15ba245391c5624752ecebd7f63b": 21,
                        "pandas__877876098c88fbf9dae2eb5cdcbecd52c6ffdd2d": 58, "pandas__f656217a06b31e48474702036e0a5c49f664186c": 353,
                        "pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0": 92, "pandas__7dd34ea7a121ce4282ce095b058c5c46568f07af": 46}.items():
        g = by_grading[iid]
        emap = g.expected_map()
        assert len(emap) == n_keys and set(emap.values()) == {"PASSED"}, iid
        assert "conftest.py" in {f.path for f in g.hidden_test_files}, iid
    # T0-7 方案 B：orange3 9b5494e2 两个恢复键改 PASSED，两个 scorer 键仍 FAILED（未完成项）
    ora = by_grading["orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"].expected_map()
    assert len(ora) == 13 and ora["TestLogisticRegressionLearner.test_LogisticRegression"] == "PASSED"
    assert ora["TestLogisticRegressionLearner.test_coefficients"] == "PASSED"
    assert {k for k, v in ora.items() if v != "PASSED"} == {"TestLogisticRegressionLearner.test_learner_scorer",
                                                          "TestLogisticRegressionLearner.test_learner_scorer_multiclass"}


def test_r2e_public_hints_match_the_r2e_environment(trusted_r2e):
    """E09（09-25）：R2E 公开面用 R2E 自己的提示——不再声称 conda 环境、pip 可用或"评分会重置测试文件"。"""
    from repoharness2.envpack.bundles import PUBLIC_SYSTEM_HINTS

    hints = {p.public_hints for p in trusted_r2e.result.public_bundles}
    assert hints == {r2e.R2E_PUBLIC_HINTS} and r2e.R2E_PUBLIC_HINTS != PUBLIC_SYSTEM_HINTS
    assert "conda" not in r2e.R2E_PUBLIC_HINTS and "/testbed/.venv" in r2e.R2E_PUBLIC_HINTS
    assert "resets the test files" not in r2e.R2E_PUBLIC_HINTS and "python -m pytest" in r2e.R2E_PUBLIC_HINTS
