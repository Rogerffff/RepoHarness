"""ingestion 构造器测试（S2-1 T2-c）。

合成夹具单测 + 真实 216 题集成测试（读冻结 docs 资产，确定性可重跑）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from repoharness2.envpack.ingest_swegym_lite import (
    HELDOUT_BASENAMES,
    STRIP_SPEC_SHA256,
    SWE_BENCH_FAMILY_FIELD_CLASSES,
    IngestError,
    build_duplicate_clusters,
    build_task,
    check_strip_spec_fields,
    ingest_swegym_lite,
    load_ingest_outputs,
    load_trusted_ingest_outputs,
    verify_bundle_relations_non_authoritative,
    write_ingest_outputs_for_tests,
    verify_package_relations,
    write_ingest_outputs,
)
from repoharness2.envpack.t1_pins import T1PinsError, load_and_verify_t1_pins
from repoharness2.taskset.image_manifest_store import Store

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
IMG_DIG = "sha256:" + "b" * 64
D = "sha256:" + "a" * 64


def make_row(iid: str = "getmoto__moto-1", repo: str = "getmoto/moto",
             commit: str = "0" * 40, statement: str = "Fix the moto bug.") -> dict:
    return {
        "instance_id": iid,
        "repo": repo,
        "base_commit": commit,
        "version": "4.1",
        "created_at": "2023-01-01T00:00:00Z",
        "problem_statement": statement,
        "hints_text": "maintainer said: apply this diff ...",  # strip 类，绝不进 bundle
        "patch": f"diff --git a/m.py b/m.py\n-bug\n+fix({iid})\n",
        "test_patch": f"diff --git a/t.py b/t.py\n+test({iid})\n",
        "FAIL_TO_PASS": [f"t.py::test_{iid[-1]}"],
        "PASS_TO_PASS": ["t.py::test_ok"],
    }


def make_image_entry(iid: str) -> dict:
    return {
        "instance_id": iid,
        "source_image_ref": f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest",
        "resolved_manifest_digest": IMG_DIG,
    }


def _build(row):
    return build_task(row, make_image_entry(row["instance_id"]),
                      raw_archive_sha256=D, image_manifest_keyed_sha256=D)


# ---- strip_spec 驱动的 fail-closed ---------------------------------------------

def test_unknown_field_fail_closed():
    row = {**make_row(), "smuggled_answer": "x"}
    with pytest.raises(IngestError, match="未列字段"):
        check_strip_spec_fields(row)


def test_missing_field_fail_closed():
    row = make_row()
    del row["created_at"]
    with pytest.raises(IngestError, match="行缺"):
        check_strip_spec_fields(row)


def test_strip_class_fields_never_enter_bundles():
    public, grading, validation, package = _build(make_row())
    for m in (public, grading, validation, package):
        dumped = json.dumps(m.model_dump(mode="json"), ensure_ascii=False)
        assert "maintainer said" not in dumped  # hints_text 内容
        assert "hints_text" not in type(m).model_fields


def test_strip_spec_constant_matches_frozen_yaml():
    yaml = pytest.importorskip("yaml", reason="pyyaml（data 依赖组）未装，跳过语义等价复核")
    p = DOCS / "data_freeze/strip_spec.yaml"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == STRIP_SPEC_SHA256
    spec = yaml.safe_load(p.read_text())
    assert spec["swe_bench_family"] == SWE_BENCH_FAMILY_FIELD_CLASSES


# ---- D5 与身份 ------------------------------------------------------------------

def test_heldout_injection_rejected():
    row = make_row(iid="bokeh__bokeh-99", repo="bokeh/bokeh")
    with pytest.raises(IngestError, match="D5 违反"):
        _build(row)
    assert HELDOUT_BASENAMES == {"tornado", "pyramid", "hydra", "bokeh"}


def test_image_entry_id_mismatch_rejected():
    row = make_row()
    with pytest.raises(IngestError, match="instance_id 不符"):
        build_task(row, make_image_entry("other__task-2"),
                   raw_archive_sha256=D, image_manifest_keyed_sha256=D)


# ---- 去重语义：只标记不删除 ------------------------------------------------------

def test_shared_environment_distinct_tasks_not_flagged():
    a = make_row(iid="getmoto__moto-1")
    b = make_row(iid="getmoto__moto-2", statement="A different bug.")
    b["FAIL_TO_PASS"] = ["t.py::test_other"]
    clusters = build_duplicate_clusters([a, b])
    assert len(clusters) == 1
    assert clusters[0].classification == "distinct_tasks_shared_environment"


def test_true_duplicate_flagged_not_dropped():
    a = make_row(iid="getmoto__moto-1")
    b = {**make_row(iid="getmoto__moto-1b"),  # 五重内容全同（只有 id 不同）
         "problem_statement": a["problem_statement"],
         "patch": a["patch"], "test_patch": a["test_patch"],
         "FAIL_TO_PASS": a["FAIL_TO_PASS"], "PASS_TO_PASS": a["PASS_TO_PASS"]}
    clusters = build_duplicate_clusters([a, b])
    assert clusters[0].classification == "suspected_duplicate"
    assert set(clusters[0].members) == {"getmoto__moto-1", "getmoto__moto-1b"}  # 都在，没删


# ---- 消费期重验 ------------------------------------------------------------------

def test_verify_relations_catches_swapped_bundle():
    public, grading, validation, package = _build(make_row())
    verify_bundle_relations_non_authoritative(package, public, grading, validation)
    _, _, validation2, _ = _build(make_row(iid="getmoto__moto-2", statement="other"))
    with pytest.raises(IngestError, match="validation digest 不符"):
        verify_bundle_relations_non_authoritative(package, public, grading, validation2)


# ---- 真实 216 题集成（读冻结资产；确定性） ---------------------------------------

@pytest.fixture(scope="module")
def real_ingest():
    from repoharness2.taskset.image_manifest_store import load_state
    df = DOCS / "data_freeze"
    survivors = [s.strip() for s in (df / "labels/static_gate_survivors.txt").read_text().splitlines() if s.strip()]
    frozen_refs = {l.strip() for l in (df / "meta/image_refs_swegym.txt").read_text().splitlines() if l.strip()}
    refs_digest = hashlib.sha256((df / "meta/image_refs_swegym.txt").read_bytes()).hexdigest()

    def expected_ref(iid: str) -> str:
        return f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"

    store = load_state(DOCS / "s2/image_manifest_keyed.json",
                       DOCS / "s2/raw/image_registry_evidence.jsonl",
                       set(survivors), frozen_refs, refs_digest, expected_ref)
    raw = DOCS / "s2/raw/swe_gym_lite_full_f70b1a29.jsonl"
    rows = [json.loads(l) for l in raw.read_text().splitlines() if l.strip()]
    return ingest_swegym_lite(
        rows=rows, survivors=survivors, image_store=store,
        raw_archive_sha256="sha256:" + hashlib.sha256(raw.read_bytes()).hexdigest(),
        image_manifest_keyed_sha256="sha256:" + hashlib.sha256(
            (DOCS / "s2/image_manifest_keyed.json").read_bytes()).hexdigest(),
    )


def test_real_216_construction(real_ingest):
    assert len(real_ingest.packages) == 216
    ids = {p.instance_id for p in real_ingest.packages}
    # T1 实测两对同环境不同任务必须保留（去重语义定案的回归锚点）
    for a, b in (("getmoto__moto-6469", "getmoto__moto-6470"),
                 ("python__mypy-11824", "python__mypy-11857")):
        assert a in ids and b in ids
    # 两对所在簇必须是 distinct，且真实数据当前不应有 suspected_duplicate
    assert all(c.classification == "distinct_tasks_shared_environment"
               for c in real_ingest.duplicate_clusters)


def test_real_outputs_deterministic(real_ingest, tmp_path):
    d1 = write_ingest_outputs_for_tests(real_ingest, tmp_path / "run1")
    d2 = write_ingest_outputs_for_tests(real_ingest, tmp_path / "run2")
    assert d1 == d2


# ---- 轮次 14 一般 3：输入面 fail-closed 扩展 -----------------------------------

def test_duplicate_raw_instance_id_rejected():
    rows = [make_row(), make_row()]  # 同 id 两行
    st = Store()
    with pytest.raises(IngestError, match="raw 行重复 instance_id"):
        ingest_swegym_lite(rows=rows, survivors=["getmoto__moto-1"],
                           image_store=st, raw_archive_sha256=D,
                           image_manifest_keyed_sha256=D)


def test_f2p_internal_duplicate_rejected():
    row = make_row()
    row["FAIL_TO_PASS"] = ["t.py::a", "t.py::a"]
    with pytest.raises(IngestError, match="含重复测试项"):
        _build(row)


def test_f2p_p2p_overlap_rejected():
    row = make_row()
    row["PASS_TO_PASS"] = list(row["FAIL_TO_PASS"])
    with pytest.raises(IngestError, match="交集非空"):
        _build(row)


# ---- 轮次 14 严重 1/2 + 一般 4：pins / strict validator / loader ----------------

@pytest.fixture(scope="module")
def real_pins():
    return load_and_verify_t1_pins(REPO_ROOT)


@pytest.fixture(scope="module")
def real_store():
    from repoharness2.taskset.image_manifest_store import load_state
    df = DOCS / "data_freeze"
    survivors = [s.strip() for s in (df / "labels/static_gate_survivors.txt").read_text().splitlines() if s.strip()]
    frozen_refs = {l.strip() for l in (df / "meta/image_refs_swegym.txt").read_text().splitlines() if l.strip()}
    refs_digest = hashlib.sha256((df / "meta/image_refs_swegym.txt").read_bytes()).hexdigest()

    def expected_ref(iid: str) -> str:
        return f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"

    return load_state(DOCS / "s2/image_manifest_keyed.json",
                      DOCS / "s2/raw/image_registry_evidence.jsonl",
                      set(survivors), frozen_refs, refs_digest, expected_ref)


def test_t1_pins_verify_ok_on_real_repo(real_pins):
    assert len(vars(real_pins)) == 7


def test_t1_pins_tamper_detected(tmp_path):
    import shutil
    from repoharness2.envpack import t1_pins as tp
    fake_root = tmp_path
    src = REPO_ROOT / tp.T1_PINS_RELPATH
    dst = fake_root / tp.T1_PINS_RELPATH
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    doc = json.loads(src.read_text())
    for ent in doc["pins"].values():
        if ent["kind"] != "repo_file":
            continue
        p = fake_root / ent["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / ent["path"], p)
    raw_rel = doc["pins"]["raw_archive"]["path"]
    p = fake_root / raw_rel
    p.write_bytes(p.read_bytes() + b"\n")  # 篡改一个字节级差异
    with pytest.raises(T1PinsError, match="T1 输入漂移"):
        load_and_verify_t1_pins(fake_root)


@pytest.fixture(scope="module")
def real_survivors():
    return [s.strip() for s in
            (DOCS / "data_freeze/labels/static_gate_survivors.txt").read_text().splitlines()
            if s.strip()]


def _load_real(pins, store, survivors, out=None):
    return load_ingest_outputs(out or (DOCS / "s2/ingest"), pins=pins,
                               image_store=store, expected_survivors=set(survivors))


def test_strict_validator_rejects_vendor_digest_tamper(real_pins, real_store, real_survivors):
    result = _load_real(real_pins, real_store, real_survivors)
    from repoharness2.envpack.bundles_v2 import EnvironmentPackageV1
    pkg, pub, grd, val = (result.packages[0], result.public_bundles[0],
                          result.grading_bundles[0], result.validation_bundles[0])
    tampered = EnvironmentPackageV1(**{**pkg.model_dump(), "spec_vendor_json_sha256": "sha256:" + "e" * 64})
    with pytest.raises(IngestError, match="固定注册表不符"):
        verify_package_relations(tampered, pub, grd, val, pins=real_pins, image_store=real_store)


def test_strict_validator_rejects_provenance_tamper(real_pins, real_store, real_survivors):
    result = _load_real(real_pins, real_store, real_survivors)
    from repoharness2.envpack.bundles_v2 import EnvironmentPackageV1
    pkg, pub, grd, val = (result.packages[0], result.public_bundles[0],
                          result.grading_bundles[0], result.validation_bundles[0])
    tampered = EnvironmentPackageV1(**{**pkg.model_dump(), "raw_archive_sha256": "sha256:" + "d" * 64})
    with pytest.raises(IngestError, match="T1 封板 pin 不符"):
        verify_package_relations(tampered, pub, grd, val, pins=real_pins, image_store=real_store)


def test_strict_loader_real_roundtrip(real_pins, real_store, real_survivors):
    result = _load_real(real_pins, real_store, real_survivors)
    assert len(result.packages) == 216
    assert len(result.duplicate_clusters) == 2


def test_strict_loader_rejects_data_file_tamper(tmp_path, real_pins, real_store, real_survivors):
    import shutil
    dst = tmp_path / "ingest"
    shutil.copytree(DOCS / "s2/ingest", dst)
    f = dst / "public_bundles_v0.jsonl"
    f.write_bytes(f.read_bytes() + b"\n")
    with pytest.raises(IngestError, match="与提交记录不符"):
        _load_real(real_pins, real_store, real_survivors, out=dst)


# ---- 轮次 15：外部锚 / 全集绑定 / 簇重算 / 契约不变量 ---------------------------

def _reseal_manifest(out_dir: Path, real_pins) -> None:
    """模拟'一致性篡改者'：按目录现状重算五文件 digest/行数并重写提交记录
    （t1_input_pins 用真实值——攻击者能做到这一步，外部锚才是最后防线）。"""
    from repoharness2.envpack.ingest_swegym_lite import (
        _DATA_FILES, INGEST_MANIFEST_NAME, INGEST_MANIFEST_SCHEMA_ID)
    files = {}
    for name in _DATA_FILES:
        data = (out_dir / name).read_bytes()
        n = (len([l for l in data.decode().splitlines() if l.strip()])
             if name.endswith(".jsonl") else len(json.loads(data)))
        files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "count": n}
    manifest = {
        "schema_id": INGEST_MANIFEST_SCHEMA_ID,
        "files": files,
        "package_count": files["environment_packages_v0.jsonl"]["count"],
        "t1_input_pins": {k: getattr(real_pins, k) for k in sorted(vars(real_pins))},
    }
    (out_dir / INGEST_MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n")


def test_subset_truncation_rejected_by_fullset_binding(tmp_path, real_pins, real_store, real_survivors):
    """codex 轮次 15 严重 2 反例：裁成 1 条 + 重封提交记录 → 全集绑定必须拒。"""
    import shutil
    dst = tmp_path / "ingest"
    shutil.copytree(DOCS / "s2/ingest", dst)
    for name in ("environment_packages_v0.jsonl", "public_bundles_v0.jsonl",
                 "grading_bundles_v2_v0.jsonl", "validation_bundles_v0.jsonl"):
        first = (dst / name).read_text().splitlines()[0]
        (dst / name).write_text(first + "\n")
    (dst / "duplicate_clusters_v0.json").write_text("[]\n")
    _reseal_manifest(dst, real_pins)
    with pytest.raises(IngestError, match="可信 survivor 全集"):
        _load_real(real_pins, real_store, real_survivors, out=dst)


def test_cluster_recompute_catches_report_tamper(tmp_path, real_pins, real_store, real_survivors):
    """簇报告被改（分类翻转）+ 重封提交记录 → 重算比对必须拒。"""
    import shutil
    dst = tmp_path / "ingest"
    shutil.copytree(DOCS / "s2/ingest", dst)
    clusters = json.loads((dst / "duplicate_clusters_v0.json").read_text())
    clusters[0]["classification"] = "suspected_duplicate"
    (dst / "duplicate_clusters_v0.json").write_text(
        json.dumps(clusters, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    _reseal_manifest(dst, real_pins)
    with pytest.raises(IngestError, match="重算结果不符"):
        _load_real(real_pins, real_store, real_survivors, out=dst)


def test_trusted_entry_real_load_ok():
    trusted = load_trusted_ingest_outputs(REPO_ROOT)
    assert len(trusted.result.packages) == 216
    assert len(trusted.survivors) == 216


def test_trusted_entry_rejects_pin_mismatch(monkeypatch):
    """外部锚（codex 轮次 15 严重 1）：提交记录若被审计外重生成/篡改（含一致性
    篡改），代码 pin 不匹配即拒——用 monkeypatch 模拟 pin 与文件不符。"""
    from repoharness2.envpack import ingest_swegym_lite as mod
    monkeypatch.setattr(mod, "INGEST_MANIFEST_SHA256_PIN", "0" * 64)
    with pytest.raises(IngestError, match="代码 pin 不符"):
        load_trusted_ingest_outputs(REPO_ROOT)


def test_grading_schema_rejects_f2p_p2p_contradiction():
    """轮次 15 一般 3：矛盾评分事实在模型层不可表示（绕过构造器也拦得住）。"""
    from pydantic import ValidationError
    from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
    base = dict(
        instance_id="getmoto__moto-1", repo="getmoto/moto",
        repo_key_lower="getmoto/moto", version="4.1", base_commit="0" * 40,
        test_patch="d", eval_cmd="pytest -n0 -rA", python_version="3.12",
        spec_vendor_id="swegym_constants_242429c1",
    )
    with pytest.raises(ValidationError, match="交集非空"):
        PrivateGradingBundleV2(**base, fail_to_pass=["t::a"], pass_to_pass=["t::a"])
    with pytest.raises(ValidationError, match="重复测试项"):
        PrivateGradingBundleV2(**base, fail_to_pass=["t::a", "t::a"], pass_to_pass=[])


def test_python_version_cross_checked_at_consumption():
    from repoharness2.envpack.spec_vendor import VendorSpecError, verify_grading_eval_cmd
    from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
    g = PrivateGradingBundleV2(
        instance_id="getmoto__moto-1", repo="getmoto/moto",
        repo_key_lower="getmoto/moto", version="4.1", base_commit="0" * 40,
        test_patch="d", fail_to_pass=["t::a"], pass_to_pass=[],
        eval_cmd="pytest -n0 -rA", python_version="2.7",  # 与 vendor 派生 3.12 不符
        spec_vendor_id="swegym_constants_242429c1",
    )
    with pytest.raises(VendorSpecError, match="python_version"):
        verify_grading_eval_cmd(g)
