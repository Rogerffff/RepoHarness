"""W1b 第一集成切片（F6/F5）envpack 层测试。

覆盖：
- trusted-prep 产物形态（公开三文件 + runtime-private 文件）、权限位、digest 账；
- 公开产物零私有内容（golden / test_patch / eval_cmd / version）+ marker 零命中；
- prompt 行 metadata 的 rh2_ 保留键边界（F1 第二道边界）；
- actor 侧三个读取口的 fail-closed：字节篡改、prompt 文本改写、题面漂移、manifest 记录错位、
  私有产物 digest/权限/内容篡改、args.prompt_data 绑定；
- actor 内从 v2 safe view 构造评分 spec：parser 闭包只捕获 PrivateGradingBundleV2，对象图无 golden，
  eval 脚本标记与 swebench 常量逐字对拍；
- 真实 216 题：trusted_prep CLI 一次性产出 → 完整 loader 全部封死后 actor 侧仍可加载；
- termination 事实载荷（F5）中立性/一致性 + 五类 join 反例 + 唯一解引用。
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w1b_synthetic_tasks import (  # noqa: E402
    IIDS,
    TID1,
    TID2,
    golden_content,
    make_controller,
    prepare_synthetic,
    judge_content,
)

from repoharness2.contracts import scan_for_forbidden_markers  # noqa: E402
from repoharness2.contracts.fa_runtime import ExecutionIdentity, RolloutAttemptOutcomeV2  # noqa: E402
from repoharness2.contracts.finalization import FinalizationReceiptV1, SessionDrainReceiptV1  # noqa: E402
from repoharness2.envpack import prepared_tasks as pt  # noqa: E402
from repoharness2.envpack.bundles import PrivateGradingBundle  # noqa: E402
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2, ValidationOnlyBundle  # noqa: E402
from repoharness2.envpack.termination_facts import (  # noqa: E402
    TERMINATION_FACTS_METADATA_KEY,
    TerminationFactsError,
    TerminationFactsPayloadV1,
    assert_payload_dereferences,
    resolve_termination_facts,
    stamp_termination_facts,
    termination_facts_payload,
)
from repoharness2.envpack.training_view import HostGradingView, RolloutTaskView  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ATTEMPT_KEY = "rh2_physical_attempt_id"
EXEC_KEY = "rh2_rollout_execution_id"


@pytest.fixture()
def prepared(tmp_path):
    return prepare_synthetic(tmp_path)


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _jsonl(rows) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode("utf-8")


def _rewrite_public(fx, name: str, rows) -> None:
    """改写公开文件并同步 manifest 里的 sha256——模拟"digest 自洽但内容被改"的产物。"""

    data = _jsonl(rows)
    (fx.prepared_dir / name).write_bytes(data)
    mpath = fx.prepared_dir / pt.MANIFEST_FILE
    doc = json.loads(mpath.read_text())
    doc["files"][name]["sha256"] = hashlib.sha256(data).hexdigest()
    mpath.write_text(json.dumps(doc, ensure_ascii=False, indent=2))


def _walk(root):
    seen: set[int] = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        yield obj
        if isinstance(obj, dict):
            stack.extend(obj.keys())
            stack.extend(obj.values())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            stack.extend(obj)
        elif isinstance(obj, BaseModel):
            stack.extend(getattr(obj, name) for name in type(obj).model_fields)
        elif hasattr(obj, "__dict__"):
            stack.extend(vars(obj).values())


# ---------------------------------------------------------------------------
# 产物形态 / 权限 / 泄漏
# ---------------------------------------------------------------------------


def test_prepare_artifacts_shape_permissions_and_no_private_leak(prepared):
    fx = prepared
    for name in (pt.MANIFEST_FILE, pt.PROMPTS_FILE, pt.ROLLOUT_VIEWS_FILE):
        assert (fx.prepared_dir / name).is_file()
    assert fx.host_path.is_file()
    assert stat.S_IMODE(fx.private_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(fx.host_path.stat().st_mode) == 0o600

    m = fx.manifest
    assert m.task_count == 2 and m.task_ids() == (TID1, TID2)
    assert pt.load_prepared_manifest(fx.prepared_dir) == m
    assert m.host_grading_artifact_sha256 == hashlib.sha256(fx.host_path.read_bytes()).hexdigest()
    for name in (pt.PROMPTS_FILE, pt.ROLLOUT_VIEWS_FILE):
        assert m.files[name].sha256 == hashlib.sha256((fx.prepared_dir / name).read_bytes()).hexdigest()

    # prompt 行 = miles --input-key prompt --label-key label --metadata-key metadata 的形状
    rows = _rows(fx.prompts_path)
    assert [r["label"] for r in rows] == [TID1, TID2]
    for row in rows:
        assert set(row) == {"prompt", "label", "metadata"}
        assert not any(k.startswith(pt.RESERVED_METADATA_PREFIX) for k in row["metadata"])
        assert set(row["metadata"]) == set(pt.PromptRowMetadata.model_fields)
        assert row["metadata"] == m.record(row["metadata"]["task_id"]).model_dump(mode="json")
        assert set(pt.DISPATCH_METADATA_KEYS) <= set(row["metadata"])

    # 公开产物：marker 零命中，且逐字不含任何私有内容
    public_rows = rows + _rows(fx.prepared_dir / pt.ROLLOUT_VIEWS_FILE)
    assert scan_for_forbidden_markers(public_rows) == []
    public_text = fx.prompts_path.read_text() + (fx.prepared_dir / pt.ROLLOUT_VIEWS_FILE).read_text()
    for iid in IIDS:
        assert golden_content(iid) not in public_text
        assert judge_content(iid) not in public_text
    assert "eval_cmd" not in public_text and '"4.1"' not in public_text

    # 私有产物：评分材料在、golden 不在（v2 三分体系）
    private_text = fx.host_path.read_text()
    for iid in IIDS:
        assert judge_content(iid) in private_text
        assert golden_content(iid) not in private_text
    assert "golden_patch" not in private_text


def test_reader_round_trip_equals_controller_views(prepared):
    fx = prepared
    m = fx.manifest
    views = pt.load_prepared_rollout_views(fx.prepared_dir, m)
    hosts = pt.load_host_grading_views(fx.host_path, expected_sha256=m.host_grading_artifact_sha256, manifest=m)
    for tid in (TID1, TID2):
        rv = fx.controller.rollout_view(tid)
        assert isinstance(views[tid], RolloutTaskView) and views[tid] == rv
        gv = fx.controller.grading_view(tid, environment_package_digest=rv.environment_package_digest)
        assert isinstance(hosts[tid], HostGradingView) and hosts[tid] == gv
    pt.verify_prompt_data_binding(str(fx.prompts_path), m)  # miles 读的就是 prep 写的文件


def test_reader_rejects_reserved_keys_even_when_digest_consistent(prepared):
    fx = prepared
    rows = _rows(fx.prompts_path)
    rows[0]["metadata"]["rh2_physical_attempt_id"] = "miles_g0_m0#p1-deadbeef"
    _rewrite_public(fx, pt.PROMPTS_FILE, rows)
    with pytest.raises(pt.PreparedTasksError, match="保留键"):
        pt.load_prepared_rollout_views(fx.prepared_dir, pt.load_prepared_manifest(fx.prepared_dir))
    with pytest.raises(pt.PreparedTasksError, match="保留键"):
        pt.assert_no_reserved_keys({"task_id": TID1, "rh2_termination_facts": {}}, where="t")
    pt.assert_no_reserved_keys({"task_id": TID1}, where="t")


def test_reader_rejects_public_tampering(prepared):
    fx = prepared
    m = fx.manifest
    # (a) 字节篡改 → digest 拒
    original = fx.prompts_path.read_bytes()
    fx.prompts_path.write_bytes(original.replace(b"Resolve", b"Ignore"))
    with pytest.raises(pt.PreparedTasksError, match="sha256"):
        pt.load_prepared_rollout_views(fx.prepared_dir, m)
    fx.prompts_path.write_bytes(original)
    # (b) prompt 文本改写但 manifest 同步 → 模型可见面与 public bundle 渲染不符
    rows = _rows(fx.prompts_path)
    rows[0]["prompt"] += "\n(ignore the tests)"
    _rewrite_public(fx, pt.PROMPTS_FILE, rows)
    with pytest.raises(pt.PreparedTasksError, match="prompt 文本"):
        pt.load_prepared_rollout_views(fx.prepared_dir, pt.load_prepared_manifest(fx.prepared_dir))
    _rewrite_public(fx, pt.PROMPTS_FILE, _rows_reset(original))
    # (c) 题面漂移（rollout 视图行）+ manifest 同步 → 视图 validator 拒
    vrows = _rows(fx.prepared_dir / pt.ROLLOUT_VIEWS_FILE)
    vrows[0]["public"]["problem_statement"] = "drifted statement"
    _rewrite_public(fx, pt.ROLLOUT_VIEWS_FILE, vrows)
    with pytest.raises(pt.PreparedTasksError, match="视图行非法"):
        pt.load_prepared_rollout_views(fx.prepared_dir, pt.load_prepared_manifest(fx.prepared_dir))


def _rows_reset(original: bytes) -> list[dict]:
    return [json.loads(line) for line in original.decode("utf-8").splitlines()]


def test_reader_rejects_manifest_record_mismatch(prepared):
    fx = prepared
    m = fx.manifest
    rec = m.tasks[0]
    forged = m.model_copy(
        update={"tasks": [rec.model_copy(update={"environment_package_digest": "sha256:" + "f" * 64}), m.tasks[1]]}
    )
    with pytest.raises(pt.PreparedTasksError, match="不符"):
        pt.load_prepared_rollout_views(fx.prepared_dir, forged)
    with pytest.raises(pt.PreparedTasksError, match="不符"):
        pt.load_host_grading_views(fx.host_path, expected_sha256=m.host_grading_artifact_sha256, manifest=forged)


def test_host_grading_reader_fail_closed(prepared):
    fx = prepared
    m = fx.manifest
    good = m.host_grading_artifact_sha256
    # 启动参数交回的期望值与 manifest 分家
    with pytest.raises(pt.PreparedTasksError, match="分家"):
        pt.load_host_grading_views(fx.host_path, expected_sha256="1" * 64, manifest=m)
    # 期望值一致但内容不符
    m_wrong = m.model_copy(update={"host_grading_artifact_sha256": "1" * 64})
    with pytest.raises(pt.PreparedTasksError, match="sha256 不符"):
        pt.load_host_grading_views(fx.host_path, expected_sha256="1" * 64, manifest=m_wrong)
    # 内容篡改（F2P 加一条）+ 期望值同步 → revalidated 的 digest 自证拒绝
    original = fx.host_path.read_bytes()
    rows = _rows(fx.host_path)
    rows[0]["grading"]["fail_to_pass"].append("t.py::forged")
    forged_bytes = _jsonl(rows)
    fx.host_path.write_bytes(forged_bytes)
    forged_sha = hashlib.sha256(forged_bytes).hexdigest()
    with pytest.raises(pt.PreparedTasksError, match="视图行非法"):
        pt.load_host_grading_views(
            fx.host_path, expected_sha256=forged_sha,
            manifest=m.model_copy(update={"host_grading_artifact_sha256": forged_sha}),
        )
    fx.host_path.write_bytes(original)
    # 权限放宽（文件 / 目录）→ 拒
    os.chmod(fx.host_path, 0o644)
    with pytest.raises(pt.PreparedTasksError, match="权限"):
        pt.load_host_grading_views(fx.host_path, expected_sha256=good, manifest=m)
    os.chmod(fx.host_path, 0o600)
    os.chmod(fx.private_dir, 0o755)
    with pytest.raises(pt.PreparedTasksError, match="权限"):
        pt.load_host_grading_views(fx.host_path, expected_sha256=good, manifest=m)
    os.chmod(fx.private_dir, 0o700)
    assert len(pt.load_host_grading_views(fx.host_path, expected_sha256=good, manifest=m)) == 2


def test_verify_prompt_data_binding_rejects_other_file(prepared, tmp_path):
    fx = prepared
    other = tmp_path / "other.jsonl"
    other.write_text(fx.prompts_path.read_text().replace("Resolve", "Ignore"))
    with pytest.raises(pt.PreparedTasksError, match="args.prompt_data"):
        pt.verify_prompt_data_binding(str(other), fx.manifest)
    with pytest.raises(pt.PreparedTasksError, match="prompt_data"):
        pt.verify_prompt_data_binding(None, fx.manifest)


def test_prepare_is_one_shot_and_refuses_overwrite(prepared):
    fx = prepared
    with pytest.raises(pt.PreparedTasksError, match="不覆盖"):
        pt.prepare_tasks(fx.controller, out_dir=fx.prepared_dir, private_dir=fx.private_dir)


# ---------------------------------------------------------------------------
# actor 内 v2 评分 spec 构造（无 golden）
# ---------------------------------------------------------------------------


def test_v2_grading_spec_built_in_actor_from_safe_view_without_golden(prepared):
    from repoharness2.adapters.slime.prepared_task_face import (
        V2_EVAL_END_MARKER,
        V2_EVAL_START_MARKER,
        GradingMaterialsError,
        PreparedTaskFace,
    )

    fx = prepared
    face = PreparedTaskFace.load(
        prepared_dir=fx.prepared_dir, host_grading_path=fx.host_path,
        host_grading_sha256=fx.manifest.host_grading_artifact_sha256,
        time_budget_seconds=600, prompt_data_path=fx.prompts_path,
    )
    rec1 = fx.manifest.record(TID1)
    rec2 = fx.manifest.record(TID2)

    # rollout 侧任务面：只带 public 面 + digest 锚，grading_spec=None
    spec_r = face.rollout_spec(TID1)
    assert spec_r.grading_spec is None and spec_r.task_id == TID1
    assert spec_r.public_bundle_digest == rec1.public_bundle_digest
    payload_text = spec_r.public_bundle_payload.decode("utf-8")
    assert json.loads(payload_text)["instance_id"] == IIDS[0]
    assert judge_content(IIDS[0]) not in payload_text and golden_content(IIDS[0]) not in payload_text

    assignment = SimpleNamespace(
        task_id=TID1, environment_package_digest=rec1.environment_package_digest,
        public_bundle_digest=rec1.public_bundle_digest,
    )
    gs = face.grading_spec(assignment)
    assert gs.task_id == TID1 and gs.image == spec_r.image
    assert gs.image_manifest_digest == spec_r.image_manifest_digest
    assert judge_content(IIDS[0]) in gs.eval_script
    assert golden_content(IIDS[0]) not in gs.eval_script
    assert gs.eval_script.count(V2_EVAL_START_MARKER) == 1 and gs.eval_script.count(V2_EVAL_END_MARKER) == 1
    assert gs.hygiene.test_files == ("t.py",)
    # 标记与官方 parser 用的 swebench 常量逐字一致（惰性 import）
    from swebench.harness.constants import END_TEST_OUTPUT, START_TEST_OUTPUT

    assert (V2_EVAL_START_MARKER, V2_EVAL_END_MARKER) == (START_TEST_OUTPUT, END_TEST_OUTPUT)
    # parser 闭包只捕获 v2 评分面（无 golden 字段的 PrivateGradingBundleV2）
    cells = [c.cell_contents for c in (gs.parse_log.__closure__ or ())]
    assert any(isinstance(c, PrivateGradingBundleV2) for c in cells)
    assert not any(isinstance(c, (PrivateGradingBundle, ValidationOnlyBundle)) for c in cells)
    # 整个任务面对象图：无 validation 面、无 v1 私有面、无 golden 内容字符串
    for obj in _walk((face, gs)):
        assert not isinstance(obj, (ValidationOnlyBundle, PrivateGradingBundle))
        if isinstance(obj, str):
            for iid in IIDS:
                assert golden_content(iid) not in obj

    # join 反例：合法 package B 的 digest 配 A 的 task_id → 拒；unknown task → 拒
    swapped = SimpleNamespace(
        task_id=TID1, environment_package_digest=rec2.environment_package_digest,
        public_bundle_digest=rec1.public_bundle_digest,
    )
    with pytest.raises(GradingMaterialsError, match="grading_dispatch_not_authoritative"):
        face.grading_spec(swapped)
    with pytest.raises(GradingMaterialsError, match="grading_dispatch_not_authoritative"):
        face.grading_spec(SimpleNamespace(task_id="swe_gym_lite::nope", environment_package_digest="x", public_bundle_digest="y"))
    with pytest.raises(pt.PreparedTasksError, match="unknown task_id"):
        face.rollout_spec("swe_gym_lite::nope")


def test_prepared_face_requires_private_ref_and_digest(prepared):
    from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace

    fx = prepared
    with pytest.raises(pt.PreparedTasksError, match="opaque 路径与期望"):
        PreparedTaskFace.load(prepared_dir=fx.prepared_dir, host_grading_path=None, host_grading_sha256=None,
                              time_budget_seconds=600)


# ---------------------------------------------------------------------------
# 真实 216 题：一次性 CLI → actor 侧加载（完整 loader 全部封死）
# ---------------------------------------------------------------------------


def test_trusted_prep_cli_real_assets_then_actor_loads_without_full_loader(tmp_path, monkeypatch, capsys):
    from repoharness2.envpack import trusted_prep

    out = tmp_path / "pub"
    priv = tmp_path / "priv"
    rc = trusted_prep.main(["--repo-root", str(REPO_ROOT), "--out-dir", str(out), "--private-dir", str(priv)])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert set(summary) == {
        "prepared_dir", "manifest", "prompt_data", "host_grading_artifact_path",
        "host_grading_artifact_sha256", "task_count",
    }
    assert summary["task_count"] == 216

    # actor 侧：完整 loader 与 controller 构造全部封死后仍能加载并复核
    import repoharness2.envpack.ingest_swegym_lite as ingest
    import repoharness2.envpack.training_view as tv

    def _boom(*a, **k):
        raise AssertionError("actor 不得调用完整 loader / 构造 controller")

    monkeypatch.setattr(ingest, "load_trusted_ingest_outputs", _boom)
    monkeypatch.setattr(ingest, "load_ingest_outputs", _boom)
    monkeypatch.setattr(tv, "load_trusted_ingest_outputs", _boom)
    monkeypatch.setattr(tv.TrustedTaskController, "_build", classmethod(lambda cls, *a, **k: _boom()))
    monkeypatch.setattr(tv.TrustedTaskController, "from_repo_root", classmethod(lambda cls, *a, **k: _boom()))

    m = pt.load_prepared_manifest(out)
    views = pt.load_prepared_rollout_views(out, m)
    hosts = pt.load_host_grading_views(
        summary["host_grading_artifact_path"], expected_sha256=summary["host_grading_artifact_sha256"], manifest=m
    )
    assert len(views) == len(hosts) == 216 and set(views) == set(hosts) == set(m.task_ids())
    assert scan_for_forbidden_markers(_rows(out / pt.PROMPTS_FILE)) == []
    assert stat.S_IMODE(Path(summary["host_grading_artifact_path"]).stat().st_mode) == 0o600


# ---------------------------------------------------------------------------
# F5：termination 事实载荷 + join 反例
# ---------------------------------------------------------------------------


def _drain(*, trajectory: str, pa: str, receipt_id: str) -> SessionDrainReceiptV1:
    return SessionDrainReceiptV1(
        receipt_id=receipt_id, session_id=f"s-{pa}", trajectory_id=trajectory,
        task_id=TID1, physical_attempt_id=pa, revoke_enforced=True, capture_record_count=1,
        pending_turns_after_drain=0, unfinalized_drafts_after_drain=0, poison_clean=True,
        drained_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )


def _receipt_for(*, trajectory: str, pa: str, seq: int, slot: int, outcome_id: str, receipt_id: str,
                 eligibility: str | None = "er_1", grading: str | None = "gr_1") -> FinalizationReceiptV1:
    outcome = RolloutAttemptOutcomeV2(
        outcome_id=outcome_id,
        identity=ExecutionIdentity(prompt_group_id="miles_g0", group_index=0, rollout_execution_id=trajectory,
                                   physical_attempt_id=pa, physical_attempt_seq=seq),
        member_slot=slot, attempt_number=seq, completion_class="present_complete", termination_kind="completed",
        task_outcome="unresolved", recovery_scope="none", turn_weight_versions=["1"],
        intra_execution_version_span=0, current_version_at_finalize="1", eligibility_report_id=eligibility,
    )
    return FinalizationReceiptV1(
        receipt_id=receipt_id, task_id=TID1, trajectory_id=trajectory, session_id=f"s-{pa}",
        physical_attempt_id=pa, attempt_disposition="delivery_prepared",
        drain_receipt=_drain(trajectory=trajectory, pa=pa, receipt_id=f"drain_{receipt_id}"),
        drain_receipt_ref=f"drain_{receipt_id}", outcome_v2=outcome,
        frozen_patch_digest="sha256:" + "a" * 64, grading_report_id=grading, eligibility_report_id=eligibility,
        runtime_quiescence_confirmed=True, started_epoch_seconds=100.0,
        finalized_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )


PA1 = "miles_g0_m0#p1-deadbeef"
PA1_RETRY = "miles_g0_m0#p2-cafef00d"
PA_SIBLING = "miles_g0_m1#p1-0badf00d"


def test_termination_facts_payload_is_neutral_and_consistent():
    fields = set(TerminationFactsPayloadV1.model_fields)
    for root in ("disposition", "admission", "reward", "mask", "train", "penal", "sample"):
        assert not any(root in f for f in fields), root
    receipt = _receipt_for(trajectory="miles_g0_m0", pa=PA1, seq=1, slot=0, outcome_id="ov2_1", receipt_id="rcpt_1")
    p = termination_facts_payload(receipt)
    assert p.physical_attempt_id == PA1 and p.rollout_execution_id == "miles_g0_m0" and p.task_id == TID1
    assert p.receipt_id == "rcpt_1" and p.outcome_id == "ov2_1"
    assert p.termination_kind == "completed"
    assert p.triggered_by_policy_horizon is False and p.triggered_by_hard_wall is False
    assert p.execution_scope_quiescent and p.canonical_frozen_patch_formed and p.fresh_grading_complete
    assert p.grading_report_id == "gr_1" and p.eligibility_report_id == "er_1"
    dump = p.model_dump(mode="json")
    # 派生矛盾在模型层不可表示；处置字段 extra=forbid 拒绝
    with pytest.raises(ValidationError):
        TerminationFactsPayloadV1(**{**dump, "triggered_by_hard_wall": True})
    with pytest.raises(ValidationError):
        TerminationFactsPayloadV1(**{**dump, "fresh_grading_complete": False})
    with pytest.raises(ValidationError):
        TerminationFactsPayloadV1(**{**dump, "disposition": "KEEP_FULL"})
    # 无 outcome 的 receipt 不可派生（fail-closed）
    with pytest.raises(TerminationFactsError):
        termination_facts_payload(receipt.model_copy(update={"outcome_v2": None, "attempt_disposition": "aborted",
                                                             "drain_receipt": None, "drain_receipt_ref": None}))


def test_termination_facts_join_negatives_five_classes_and_unique_dereference():
    r1 = _receipt_for(trajectory="miles_g0_m0", pa=PA1, seq=1, slot=0, outcome_id="ov2_1", receipt_id="rcpt_1")
    r_retry = _receipt_for(trajectory="miles_g0_m0", pa=PA1_RETRY, seq=2, slot=0, outcome_id="ov2_2", receipt_id="rcpt_2")
    r_sib = _receipt_for(trajectory="miles_g0_m1", pa=PA_SIBLING, seq=1, slot=1, outcome_id="ov2_3", receipt_id="rcpt_3")
    p1, p_retry, p_sib = (termination_facts_payload(r) for r in (r1, r_retry, r_sib))

    own = {ATTEMPT_KEY: PA1, EXEC_KEY: "miles_g0_m0", TERMINATION_FACTS_METADATA_KEY: p1.model_dump(mode="json")}
    assert resolve_termination_facts(own) == p1

    # ① 同题 n=8 sibling 的事实放到本样本上 → 拒
    with pytest.raises(TerminationFactsError, match="attempt"):
        resolve_termination_facts({**own, TERMINATION_FACTS_METADATA_KEY: p_sib.model_dump(mode="json")})
    # ② 同 member 旧 retry attempt 的事实放到新 attempt 样本上 → 拒
    with pytest.raises(TerminationFactsError, match="attempt"):
        resolve_termination_facts({**own, ATTEMPT_KEY: PA1_RETRY})
    # ③ fan-out 叶各自携带别的 attempt 的事实 → 盖章拒（fresh 叶无身份键也不放行）
    forged_leaf = SimpleNamespace(metadata={TERMINATION_FACTS_METADATA_KEY: p_sib.model_dump(mode="json")})
    with pytest.raises(TerminationFactsError, match="fan-out"):
        stamp_termination_facts([forged_leaf], p1)
    # ④ 错 attempt：叶身份 attempt 与载荷不符 → 盖章拒；resolve 同样拒
    with pytest.raises(TerminationFactsError, match="错 attempt"):
        stamp_termination_facts([SimpleNamespace(metadata={ATTEMPT_KEY: PA1_RETRY, EXEC_KEY: "miles_g0_m0"})], p1)
    # ⑤ 错 trajectory：attempt 对得上但 execution 不符 → 盖章拒；resolve 拒
    with pytest.raises(TerminationFactsError, match="错 trajectory"):
        stamp_termination_facts([SimpleNamespace(metadata={ATTEMPT_KEY: PA1, EXEC_KEY: "miles_g0_m9"})], p1)
    with pytest.raises(TerminationFactsError, match="trajectory"):
        resolve_termination_facts({**own, EXEC_KEY: "miles_g0_m9"})
    # 缺身份/缺载荷都不可 join
    with pytest.raises(TerminationFactsError, match="缺失"):
        resolve_termination_facts({ATTEMPT_KEY: PA1, EXEC_KEY: "miles_g0_m0"})
    with pytest.raises(TerminationFactsError, match="rh2_physical_attempt_id"):
        resolve_termination_facts({TERMINATION_FACTS_METADATA_KEY: p1.model_dump(mode="json")})

    # 唯一解引用：载荷只对应它自己的 receipt/outcome
    assert_payload_dereferences(p1, r1)
    for other in (r_retry, r_sib):
        with pytest.raises(TerminationFactsError, match="解引用"):
            assert_payload_dereferences(p1, other)

    # 合法覆盖：同一样本对象经 reset_for_retry 后带着旧 attempt 的事实历史，新 attempt 盖章覆盖
    retried = SimpleNamespace(metadata={ATTEMPT_KEY: PA1_RETRY, EXEC_KEY: "miles_g0_m0",
                                        TERMINATION_FACTS_METADATA_KEY: p1.model_dump(mode="json")})
    stamp_termination_facts([retried], p_retry)
    assert resolve_termination_facts(retried.metadata) == p_retry
    # 同一载荷重复盖章幂等；盖到没有身份键的 fresh 叶 = 正常 producer 路径
    stamp_termination_facts([retried], p_retry)
    fresh = SimpleNamespace(metadata={})
    stamp_termination_facts([[fresh]], p1)
    assert fresh.metadata[TERMINATION_FACTS_METADATA_KEY]["physical_attempt_id"] == PA1


def test_synthetic_controller_still_holds_no_golden():
    """夹具自证：合成 controller 的 rollout/grading 视图不含 golden（W2a 纪律沿用）。"""

    c = make_controller()
    for obj in _walk(c):
        assert not isinstance(obj, ValidationOnlyBundle)
        if isinstance(obj, str):
            for iid in IIDS:
                assert golden_content(iid) not in obj
