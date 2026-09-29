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
from repoharness2.envpack.bundles import BundleLeakError
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
    （09-24 夜）；09-29 单题闭环试行第 1 轮追加 r2e-mr-021 至 033（numpy 18b7/5e83/a5ea、pillow 3a61、scrapy e938/7545/9a15，统一标准 v1 D4 授权、Codex 复核通过）；09-29 第 2 轮追加 r2e-mr-034 至 047（coveragepy 9799/ea69/5dbb、aiohttp 1c1c/22a1/6183、pillow 3ac9，同上授权与复核）；09-29 第 3 轮追加 r2e-mr-048 至 050（datalad 19f5、pandas 32dd，同上授权与复核）；09-29 第 4 轮追加 r2e-mr-051 至 052（aiohttp 240d，同上授权与复核）；09-29 第 5 轮追加 r2e-mr-053 至 056（coveragepy f5eb、pandas 4ec8、numpy d805，同上授权与复核）；09-29 第 6 轮追加 r2e-mr-057（orange3 4014，同上授权与复核）；09-29 第 7 轮追加 r2e-mr-058 至 060（numpy d89b，同上授权与复核）；09-29 第 8 轮追加 r2e-mr-061 至 063（aiohttp 4075、pillow 2d01，同上授权与复核），其余 15 题无修订。"""
    revs = trusted_r2e.revisions
    assert {iid: [r.revision_id for r in rs] for iid, rs in revs.items()} == {
        "coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae": ["r2e-mr-001"],
        "datalad__58ba5165234cb16de0e8463ee75097362099835f": ["r2e-mr-002"],
        "pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199": ["r2e-mr-006", "r2e-mr-007", "r2e-mr-055"],
        "scrapy__cfed9b6659c90e0799361911b1d72ed127edf471": ["r2e-mr-003", "r2e-mr-004", "r2e-mr-005"],
        "pandas__19c5eea5db0046276bfc0eef8a67febf090eeaaf": ["r2e-mr-008", "r2e-mr-009"],
        "pandas__294cbc8d1faa15ba245391c5624752ecebd7f63b": ["r2e-mr-010", "r2e-mr-011"],
        "pandas__877876098c88fbf9dae2eb5cdcbecd52c6ffdd2d": ["r2e-mr-012", "r2e-mr-013"],
        "pandas__f656217a06b31e48474702036e0a5c49f664186c": ["r2e-mr-014", "r2e-mr-015"],
        "pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0": ["r2e-mr-016", "r2e-mr-017", "r2e-mr-050"],
        "pandas__7dd34ea7a121ce4282ce095b058c5c46568f07af": ["r2e-mr-018", "r2e-mr-019"],
        "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040": ["r2e-mr-020"],
        "pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96": ["r2e-mr-063"],
        "aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a": ["r2e-mr-061", "r2e-mr-062"],
        "numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd": ["r2e-mr-058", "r2e-mr-059", "r2e-mr-060"],
        "orange3__4014f2483e3bab0621c9ae0f994947c008183253": ["r2e-mr-057"],
        "numpy__d805e9b66228e68a0eb14d901cd350159c49af18": ["r2e-mr-056"],
        "coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96": ["r2e-mr-053", "r2e-mr-054"],
        "aiohttp__240da100151933883d7dea0528d45877df025b92": ["r2e-mr-051", "r2e-mr-052"],
        "datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb": ["r2e-mr-048", "r2e-mr-049"],
        "pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605": ["r2e-mr-046", "r2e-mr-047"],
        "aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2": ["r2e-mr-044", "r2e-mr-045"],
        "aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac": ["r2e-mr-042", "r2e-mr-043"],
        "aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52": ["r2e-mr-040", "r2e-mr-041"],
        "coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9": ["r2e-mr-038", "r2e-mr-039"],
        "coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5": ["r2e-mr-036", "r2e-mr-037"],
        "coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266": ["r2e-mr-034", "r2e-mr-035"],
        "scrapy__9a15fcf89a151811de8ac783419df0512c863d5e": ["r2e-mr-031", "r2e-mr-032", "r2e-mr-033"],
        "scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67": ["r2e-mr-028", "r2e-mr-029", "r2e-mr-030"],
        "scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4": ["r2e-mr-026", "r2e-mr-027"],
        "pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07": ["r2e-mr-024", "r2e-mr-025"],
        "numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764": ["r2e-mr-023"],
        "numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb": ["r2e-mr-022"],
        "numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9": ["r2e-mr-021"],
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


# ---------------------------------------------------------------------------
# 第五类修订：题面文本替换（统一标准 v1 §5 R-f / §9 D6，2026-09-29）
# ---------------------------------------------------------------------------

# 两条 edits 依次作用：第二条的 old 只在第一条替换之后才出现（"每条在当前文本里恰好出现一次"）
_STATEMENT_EDITS = [
    {"old": "it is 1.", "new": "`x` is 1 on the base commit."},
    {"old": "on the base commit.", "new": "on the base commit (reproduced by importing the module)."},
]


def _edited(text: str, edits: list[dict]) -> str:
    for e in edits:
        text = text.replace(e["old"], e["new"], 1)
    return text


def _statement_rev(row: dict, edits: list[dict] | None = None, **over) -> dict:
    """一条题面修订条目：摘要按来源题面与依次替换后的文本算好；`over` 覆盖其余字段。"""

    edits = _STATEMENT_EDITS if edits is None else edits
    source = row["problem_statement"]
    ent = _rev(kind=r2e.REVISION_KIND_STATEMENT, target="problem_statement", edits=edits, expected_change=None,
               sha256_before=_sha(source), sha256_after=_sha(_edited(source, edits)), revised_file=None)
    ent.update(over)
    return ent


def _revs_doc(*entries: dict) -> dict:
    return {"schema_id": r2e.R2E_MATERIAL_REVISIONS_SCHEMA_ID, "revisions": list(entries)}


def test_statement_revision_rewrites_only_the_public_statement_and_is_recorded():
    row = _row()
    source = row["problem_statement"]
    revised = _edited(source, _STATEMENT_EDITS)
    assert "(reproduced by importing the module)" in revised  # 第二条 edit 依赖第一条的结果
    base = _ingest([_row()])
    result = _ingest([row], revisions=r2e.parse_r2e_material_revisions(_revs_doc(_statement_rev(row))))
    public, grading, validation, package = (
        result.public_bundles[0], result.grading_bundles[0], result.validation_bundles[0], result.packages[0],
    )
    # 公开面：题面与题面摘要都是修订后的（摘要由 PublicTaskBundle 自证）；其余公开字段不变
    assert base.public_bundles[0].problem_statement == source
    assert public.problem_statement == revised and public.problem_statement_sha256 == _sha(revised)
    stmt_fields = {"problem_statement", "problem_statement_sha256"}
    assert public.model_dump(exclude=stmt_fields) == base.public_bundles[0].model_dump(exclude=stmt_fields)
    # 修订记录：编号与其余四类记在同一字段（评分面 material_revisions）
    assert grading.material_revisions == ["r2e-mr-001"]
    # 评分材料不变：除修订标记外评分面逐字段相同；验证面（gold）不变
    assert (grading.model_dump(exclude={"material_revisions"})
            == base.grading_bundles[0].model_dump(exclude={"material_revisions"}))
    assert validation == base.validation_bundles[0]
    # 包记录绑定修订后的公开面
    assert package.public_bundle_digest == public.digest() != base.packages[0].public_bundle_digest
    r2e.verify_r2e_bundle_relations_non_authoritative(package, public, grading, validation)


def test_statement_revision_coexists_with_a_grading_revision_on_the_same_task():
    """同一题一条期望修订 + 一条题面修订（目标不同）：各自生效；评分面与"只有期望修订"时除修订标记外相同。"""
    row = _row()
    expected_rev = _expected_rev_doc(row)["revisions"][0]  # r2e-mr-001：test_legacy FAILED → PASSED
    revs = r2e.parse_r2e_material_revisions(_revs_doc(expected_rev, _statement_rev(row, revision_id="r2e-mr-002")))
    result = _ingest([row], revisions=revs)
    g, p = result.grading_bundles[0], result.public_bundles[0]
    assert g.material_revisions == ["r2e-mr-001", "r2e-mr-002"]
    assert p.problem_statement == _edited(row["problem_statement"], _STATEMENT_EDITS)
    only_expected = _ingest([_row()], revisions=r2e.parse_r2e_material_revisions(_expected_rev_doc(_row())))
    assert g.expected_map() == {"TestCore.test_x": "PASSED", "TestCore.test_legacy": "PASSED"}
    assert (g.model_dump(exclude={"material_revisions"})
            == only_expected.grading_bundles[0].model_dump(exclude={"material_revisions"}))


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"target": "expected_output_json"}, "target 必须是 problem_statement"),
        ({"target": "test_1.py"}, "target 必须是 problem_statement"),
        ({"revised_file": _REVISED_FILE + "problem_statement.md"}, "revised_file 必须为 null"),
        ({"expected_change": {"changed": {"TestCore.test_legacy": ["FAILED", "PASSED"]}, "added": {}, "removed": []}},
         "expected_change 必须为 null"),
        ({"edits": None}, "edits 必须是非空列表"),
        ({"edits": []}, "edits 必须是非空列表"),
        ({"edits": [{"old": "it is 1.", "new": "it is 1."}]}, "两者不同"),
        ({"sha256_before": None}, "sha256_before 不是"),
    ],
)
def test_statement_revision_entry_is_rejected_at_parse(over, message):
    ent = _statement_rev(_row())
    ent.update(over)
    with pytest.raises(r2e.R2EIngestError, match=message):
        r2e.parse_r2e_material_revisions(_revs_doc(ent))


def test_at_most_one_statement_revision_per_task():
    """沿用"同一题同一目标只许一条修订"：同一题的第二条题面修订在解析时即拒（多处改动写成同一条的多个 edits）；
    别的题各有一条不受影响。"""
    row = _row()
    first = _statement_rev(row)
    second = _statement_rev(row, [{"old": "x should be 2", "new": "x must be 2"}], revision_id="r2e-mr-002")
    with pytest.raises(r2e.R2EIngestError, match="同一题的同一目标只允许一条修订"):
        r2e.parse_r2e_material_revisions(_revs_doc(first, second))
    other = dict(second, instance_id="demo__" + "e" * 40)
    assert set(r2e.parse_r2e_material_revisions(_revs_doc(first, other))) == {"demo__" + "a" * 40, "demo__" + "e" * 40}


@pytest.mark.parametrize(
    ("edits", "over", "message"),
    [
        ([{"old": "no such text", "new": "x"}], {}, "出现 0 次"),
        ([{"old": "ISSUE]", "new": "ISSUE}"}], {}, "出现 2 次"),
        # 第二条的片段已被第一条换掉，在当前文本里找不到
        ([{"old": "it is 1.", "new": "it is one."}, {"old": "it is 1.", "new": "it is uno."}], {}, "第 2 处.*出现 0 次"),
        (None, {"sha256_before": _sha("another statement")}, "sha256_before"),
        (None, {"sha256_after": _sha("another statement")}, "sha256_after"),
        ([{"old": _row()["problem_statement"], "new": ""}], {}, "题面为空"),
        ([{"old": "it is 1.", "new": "it is one."}, {"old": "it is one.", "new": "it is 1."}], {}, "没有改变题面"),
    ],
)
def test_statement_revision_is_rejected_when_edits_or_digests_do_not_match(edits, over, message):
    row = _row()
    ent = _statement_rev(row, edits)
    ent.update(over)
    with pytest.raises(r2e.R2EIngestError, match=message):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(_revs_doc(ent)))


@pytest.mark.parametrize(
    ("new_text", "message"),
    [
        ("it is 1 (the hidden test checks this).", "hidden_test"),  # 公开面泄漏标记扫描
        (_row()["expected_output_json"], "原样包含 expected_output_json"),
        (extract_gold_patch(_row()["parsed_commit_content"]), "原样包含 gold"),
    ],
)
def test_revised_statement_still_goes_through_the_public_face_checks(new_text, message):
    """扫描的是修订后的题面：泄漏标记扫描与"期望原文 / gold / 造题指令不得原样出现"两道检查照常生效。"""
    row = _row()
    ent = _statement_rev(row, [{"old": "it is 1.", "new": new_text}])
    with pytest.raises((BundleLeakError, r2e.R2EIngestError), match=message):
        _ingest([row], revisions=r2e.parse_r2e_material_revisions(_revs_doc(ent)))


def test_statement_revision_is_recorded_in_the_manifest_and_bound_at_consumption(tmp_path):
    root, sealed = _tmp_repo(tmp_path)
    pins = r2e.load_and_verify_r2e_pins(root, pins_sha256=sealed)
    facts = r2e.load_r2e_image_facts(root, pins)
    rows, revision = r2e.load_r2e_rows(root, pins)
    source = rows[0]["problem_statement"]
    revs = r2e.parse_r2e_material_revisions(_revs_doc(_statement_rev(rows[0])))
    kw = dict(rows=rows, image_facts=facts, raw_archive_sha256="sha256:" + pins.raw_archive,
              image_facts_sha256="sha256:" + pins.image_facts, source_revision=revision, expected_task_count=1)
    result = r2e.ingest_r2e_subset(**kw, revisions=revs)
    args = (result.packages[0], result.public_bundles[0], result.grading_bundles[0], result.validation_bundles[0])
    iid = args[1].instance_id
    r2e.verify_r2e_package_relations(*args, pins=pins, image_facts=facts, revisions=revs)
    with pytest.raises(r2e.R2EIngestError, match="修订标记"):
        r2e.verify_r2e_package_relations(*args, pins=pins, image_facts=facts)  # 不给修订单：带修订的题被拒
    # 提交记录逐条列出题面修订（编号 / 类型 / 目标 / 前后摘要）；严格加载要求它与封板修订单一致
    out = tmp_path / "out"
    r2e.write_r2e_ingest_outputs(result, out, pins=pins, revisions=revs)
    manifest = json.loads((out / r2e.R2E_INGEST_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["material_revisions"] == [{
        "revision_id": "r2e-mr-001", "instance_id": iid, "kind": "statement_text_replace", "target": "problem_statement",
        "sha256_before": _sha(source), "sha256_after": _sha(_edited(source, _STATEMENT_EDITS)), "decision_ref": "test",
    }]
    loaded = r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids={iid}, revisions=revs)
    assert loaded.public_bundles[0].problem_statement == _edited(source, _STATEMENT_EDITS)
    with pytest.raises(r2e.R2EIngestError, match="material_revisions"):
        r2e.load_r2e_ingest_outputs(out, pins=pins, image_facts=facts, expected_instance_ids={iid})
    # 评分面声称应用了题面修订、公开面却仍是来源题面（其余关系都自洽）：消费期拒绝
    plain = r2e.ingest_r2e_subset(**kw)
    forged = PrivateGradingBundleR2E.model_validate(
        {**plain.grading_bundles[0].model_dump(mode="json"), "material_revisions": ["r2e-mr-001"]})
    forged_package = build_environment_package(
        public=plain.public_bundles[0], grading=forged, validation=plain.validation_bundles[0],
        source="r2e_gym_subset", raw_archive_sha256="sha256:" + pins.raw_archive,
        image_manifest_keyed_sha256="sha256:" + pins.image_facts,
    )
    with pytest.raises(r2e.R2EIngestError, match="公开面的题面摘要不是修订后的摘要"):
        r2e.verify_r2e_package_relations(forged_package, plain.public_bundles[0], forged, plain.validation_bundles[0],
                                         pins=pins, image_facts=facts, revisions=revs)


def test_real_ingest_reproduces_the_sealed_outputs_and_statements_follow_the_revision_list(trusted_r2e, tmp_path):
    """题面修订接入后（09-29）：用当前代码从封板输入重跑 48 题 ingest，四个数据文件与提交记录逐字节等于已封板产物
    （现有四类修订与未修订题的产物不变）；公开面题面 = 来源题面套上封板修订单里的题面修订（目前没有，即逐字等于来源）。"""
    pins = trusted_r2e.pins
    rows, revision = r2e.load_r2e_rows(REPO_ROOT, pins)
    result = r2e.ingest_r2e_subset(
        rows=rows, image_facts=trusted_r2e.image_facts, raw_archive_sha256="sha256:" + pins.raw_archive,
        image_facts_sha256="sha256:" + pins.image_facts, source_revision=revision, revisions=trusted_r2e.revisions,
    )
    digests = r2e.write_r2e_ingest_outputs(result, tmp_path, pins=pins, revisions=trusted_r2e.revisions)
    recorded = json.loads((REPO_ROOT / r2e.R2E_INGEST_OUT_RELPATH / r2e.R2E_INGEST_MANIFEST_NAME).read_text())["files"]
    assert {name: digests[name] for name in recorded} == {name: ent["sha256"] for name, ent in recorded.items()}
    assert digests[r2e.R2E_INGEST_MANIFEST_NAME] == r2e.R2E_INGEST_MANIFEST_SHA256_PIN
    by_public = {p.instance_id: p for p in trusted_r2e.result.public_bundles}
    assert len(rows) == len(by_public) == 48
    for row in rows:
        iid = f"{row['repo_name']}__{row['commit_hash']}"
        want = r2e.apply_statement_revisions(iid, row["problem_statement"], trusted_r2e.revisions.get(iid, ()))
        assert by_public[iid].problem_statement == want, iid
