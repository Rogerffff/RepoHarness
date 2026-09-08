"""W1b 第二段：三终态在交付面的落点（adapters/slime/generate.py，fa_formal 链）。

被测事实：
- ③ 完整 finalize 但不合格（failed_to_grade）→ **真实样本**交付（remove_sample=False、
  status 非 aborted）+ typed admission 载荷，不再压成 abort 形状（`rh2_gate_degraded` 在 fa_formal
  下消失）；unsafe（present + 永久拒绝，契约封闭豁免集）同样真实交付、载荷无 EligibilityReport；
- ② 真实 ABORTED 只给 completion=missing（harness 崩溃）；
- ① 结构矛盾 typed raise：present Outcome 却走 abort 形状、载荷派生矛盾；
- termination_facts_stamp_conflict 发生在 receipt/审计落盘之后：经现有审计通道追加 attempt-bound
  fatal 事实（第二条 append-only 记录），receipt 仍显示 delivery_prepared；
- 前置清理批（决策包 D2+B v2，2026-09-04）：合格轨迹**不需要任何 sandbox 能力事实**即 online /
  KEEP_FULL（D2-2：provider 注入位、required、lease 绑定全部删除）；fa_formal **不配置**
  staleness_threshold 也能启动并完成 finalize（旧 `staleness_threshold_required_in_formal_chain` /
  `staleness_threshold_unconfigured` fail-fast 已不存在），握手里的阈值只是 consume-time 阈值的
  记录用镜像，finalize-time lag 超过镜像也不影响资格（B-1）；s1_compat 仍写冻结的 S1 历史值。
"""

from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    FakeFinalizationStore,
    _Args,
    _dummy_orchestrator,
    _formal_config,
    build_dense_chain,
    dense_turns,
    make_task,
    TASK_ID_DENSE,
)
from test_w1b_termination_facts_producer import _Barrier, _steps  # noqa: E402

from repoharness2.adapters.slime import generate as generate_mod  # noqa: E402
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.generate import (  # noqa: E402
    S1_COMPAT_LEGACY_STALENESS_THRESHOLD,
    STALENESS_THRESHOLD_MIRROR_UNBOUNDED,
    SlimeBindingError,
)
from repoharness2.envpack.termination_facts import resolve_termination_facts  # noqa: E402
from repoharness2.governance.admission import (  # noqa: E402
    ADMISSION_METADATA_KEY,
    DispositionPolicy,
    decide_member_disposition,
    resolve_admission_payload,
)

PAID = "exec_F22#p1-cafe1234"
EXEC = "exec_F22"
IDENTITY = {"rh2_physical_attempt_id": PAID, "rh2_rollout_execution_id": EXEC}


def _formal_chain(store=None, *, barrier=None, config_overrides=None, turn_weight_version="5", **kwargs):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = turn_weight_version
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal", **(config_overrides or {})),
        runtime_quiescence_barrier=barrier or _Barrier(), turns=turns,
        finalization_store=store or FakeFinalizationStore(), **kwargs,
    )
    _stamp_fa_identity(chain.base_sample)
    return chain


def _resolve(leaf):
    return resolve_admission_payload({**leaf.metadata, **IDENTITY})


def _decide(payload, policy=None):
    return decide_member_disposition(payload, policy=policy or DispositionPolicy())


# ---------------------------------------------------------------------------
# ③ 完整 finalize 的成员：真实交付 + 载荷
# ---------------------------------------------------------------------------


async def test_failed_to_grade_is_delivered_as_real_sample_not_aborted(tmp_path):
    chain = _formal_chain(infra_grading=True, artifact_dir=tmp_path)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert audit.finalized.group_repair_signal.degraded is True
    assert audit.steps[-1] == "step9_samples_delivered" and "step9_degraded_signal_forwarded" not in audit.steps
    assert "degraded_member_delivered_for_group_admission" in _steps(audit)
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.status == "completed"
    assert leaf.metadata.get("abort_reason") is None
    assert isinstance(leaf.reward, float) and math.isnan(leaf.reward)  # reward 不可得：NaN 占位，不是 0.0/None
    assert leaf.loss_mask and sum(leaf.loss_mask) > 0 and leaf.rollout_log_probs  # 真实 provenance 保留
    payload = _resolve(leaf)
    assert payload.eligibility_report.eligibility_class == "audit_only_or_rejected"
    assert payload.outcome.completion_class == "present_complete"
    assert payload.outcome.failure_category == "grading_infra_failure" and payload.outcome.reward_unavailable
    assert payload.grading_outcome == "failed_to_grade" and payload.grading_reward is None
    assert payload.finalize_staleness_steps == 0  # 只是观测值（current 5 − min(seen) 5）
    assert leaf.metadata["eligibility_report_ref"] == payload.eligibility_report.report_id
    facts = resolve_termination_facts({**leaf.metadata, **IDENTITY})
    assert facts.eligibility_report_id == payload.eligibility_report.report_id
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "reward_scope_none")
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "delivery_prepared"
    assert (next(p for p in tmp_path.iterdir() if p.is_dir()) / "eligibility_report.json").exists()


async def test_all_ok_without_any_sandbox_sidecar_is_online_and_keep_full():
    """D2-2：合格轨迹在没有任何 sandbox 能力事实（编排根本没有 provider 注入位）的情况下
    直接 online / KEEP_FULL——证明交付面与 gate 都不再读 sidecar；security 维 evidence 为空
    （本次轨迹没有执行级违规事实）。W1b 第二段的"缺能力事实 → DROP_GROUP"形态不可达。"""

    import inspect

    from repoharness2.adapters.slime.generate import RolloutOrchestrator

    assert "sandbox_capability_facts_provider" not in inspect.signature(RolloutOrchestrator.__init__).parameters
    chain = _formal_chain()
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.finalized.group_repair_signal.degraded is False
    assert "degraded_member_delivered_for_group_admission" not in _steps(audit)
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.reward == 1.0
    assert leaf.metadata["training_eligibility_class"] == "online_policy_loss_eligible"
    payload = _resolve(leaf)
    report = payload.eligibility_report
    assert report.facts.all_ok() and report.eligibility_class == "online_policy_loss_eligible"
    security = report.facts.security_and_leakage
    assert security.ok and security.reason_codes == [] and security.evidence_refs == []
    assert "sandbox_capability" not in " ".join(report.reason_codes)
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("KEEP_FULL", "all_dimensions_ok")


def _frozen_ws_with_entries(census_lines: str, *, regular: dict[str, str] | None = None,
                            symlinks: dict[str, str] | None = None):
    """构造导出 census/内容抓取罐头的 FrozenWorkspace 替身 + 屏障（W3a 起 verify_integrity 不被调用）。"""

    from types import SimpleNamespace

    from repoharness2.adapters.slime.generate import QuiescenceConfirmed as _QC

    regular = regular or {}
    symlinks = symlinks or {}

    class _Ws:
        snapshot_ref = "sha256:abc"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=census_lines, stderr="")
            if "base64 <" in script or "readlink" in script:
                lines = [f"{p}\t{b}\n" for p, b in regular.items()] + [f"{p}\t{b}\n" for p, b in symlinks.items()]
                return SimpleNamespace(exit_code=0, stdout="".join(lines), stderr="")
            return await self._u.run_bash(script)

        async def verify_integrity(self):
            raise AssertionError("W3a：正式链不得再调用 verify_integrity")

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return _QC(frozen_grading_workspace=_Ws(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",))

    return _Barrier()


async def test_test_path_change_is_projected_not_unsafe_and_keeps_full():
    """W3a（D2-3，T1 oracle 改动）：只改测试文件的 artifact **不再是 unsafe**——控制面 entry 拆进
    ignored_validation_delta（不重放），grader 正常出分（stub 给 resolved）、EligibilityReport 在场、
    复合 filter KEEP_FULL；unsafe_artifact_permanent_rejection 从未出现。"""

    import base64
    import hashlib

    from repoharness2.grading.manager import HygieneRules

    content = b"def test_evil():\n    assert True\n"
    b64 = base64.b64encode(content).decode()
    sha = hashlib.sha256(content).hexdigest()
    barrier = _frozen_ws_with_entries(
        f"regular\t100644\t{sha}\ttests/test_evil.py\n", regular={"tests/test_evil.py": b64},
    )
    base_task = make_task(TASK_ID_DENSE)
    task = dataclasses.replace(
        base_task, grading_spec=dataclasses.replace(base_task.grading_spec, hygiene=HygieneRules(test_globs=("tests/*",)))
    )
    chain = _formal_chain(barrier=barrier, task=task)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (call,) = chain.grading.calls
    assert call["frozen_delta"].projection.included_entry_paths == ()
    assert audit.finalized is not None and audit.unsafe_artifact_reasons == []
    assert audit.trusted_projection["ignored_validation_counts_by_class"] == {
        "official_test_file": 0, "test_glob": 1, "reserved_namespace": 0,
    }
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.reward == 1.0
    payload = _resolve(leaf)
    assert payload.outcome.reason_code is None and payload.eligibility_report is not None
    assert "ignored_validation_delta:test_glob:add:tests/test_evil.py" in payload.outcome.evidence_refs
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("KEEP_FULL", "all_dimensions_ok")


async def test_structurally_unsafe_artifact_is_delivered_without_report_and_drops_by_exemption():
    """附录 A 契约豁免集（W3a 起触发条件收窄为**结构不安全** artifact——此处 symlink 逃逸）：
    present + unsafe 永久拒绝——真实交付、载荷无 EligibilityReport，receipt=delivery_prepared，
    审计 disposition 仍派生 permanent_rejected；容器同样在本体持久化后释放。"""

    import base64
    import hashlib
    import json
    import tempfile

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    target = b"../../etc/passwd"
    tb64 = base64.b64encode(target).decode()
    tsha = hashlib.sha256(target).hexdigest()
    barrier = _frozen_ws_with_entries(
        f"symlink\t120000\t{tsha}\tsrc/escape\n", symlinks={"src/escape": tb64},
    )
    chain = _formal_chain(barrier=barrier)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == [] and audit.finalized is None
    assert audit.unsafe_artifact_reasons == ["unsafe_symlink_escape:src/escape"]
    assert audit.rollout_container_released_before_grading is True
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.status == "completed" and math.isnan(leaf.reward)
    assert "eligibility_report_ref" not in leaf.metadata and "training_eligibility_class" not in leaf.metadata
    assert "present_member_delivered_without_report" in _steps(audit)
    payload = _resolve(leaf)
    assert payload.eligibility_report is None and payload.grading_report_id is None
    assert payload.outcome.reason_code == "unsafe_artifact_permanent_rejection"
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "unsafe_artifact_permanent_rejection")
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "delivery_prepared" and receipt.eligibility_report_id is None
    with tempfile.TemporaryDirectory() as td:
        jsonl = Path(td) / "a.jsonl"
        write_execution_audit_record(None, audit, jsonl)
        rec = json.loads(jsonl.read_text().strip())
    assert rec["disposition"] == "permanent_rejected"


async def test_missing_outcome_stays_aborted_without_admission_payload():
    # 批 A T1：已归因 task-local 故障用 typed 码（裸 RuntimeError 现在是未归因 → run-fatal）
    chain = _formal_chain(crash=SlimeBindingError("harness_bootstrap_failed", "docker exec failed"))
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (aborted,) = delivered
    assert aborted.remove_sample is True and aborted.status == "aborted"
    assert ADMISSION_METADATA_KEY not in aborted.metadata
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "aborted" and receipt.outcome_v2.completion_class == "missing"


async def test_evaluation_placeholder_unchanged_in_formal_mode():
    chain = _formal_chain()
    (placeholder,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS), evaluation=True)
    assert placeholder.remove_sample is True and placeholder.reward == 1.0
    assert ADMISSION_METADATA_KEY not in placeholder.metadata


# ---------------------------------------------------------------------------
# ① 结构矛盾 typed raise
# ---------------------------------------------------------------------------


async def test_abort_shape_for_present_outcome_is_fatal():
    chain = _formal_chain()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2["completion_class"] == "present_complete"
    with pytest.raises(FatalExecutionInfrastructureError, match="abort_shape_for_present_outcome"):
        chain.orchestrator._abort_result(chain.base_sample, reason="x", task=make_task(TASK_ID_DENSE), audit=audit)
    assert "abort_shape_for_present_outcome" in _steps(audit)
    # s1_compat 不受本守卫约束（冻结路径）
    s1 = build_dense_chain()
    await s1.orchestrator.generate(_Args(), s1.base_sample, dict(SAMPLING_PARAMS))
    s1.orchestrator._abort_result(s1.base_sample, reason="x", task=make_task(TASK_ID_DENSE), audit=s1.orchestrator.audits[0])


async def test_admission_payload_build_failure_is_fatal(monkeypatch):
    chain = _formal_chain()

    def _boom(**kw):
        from repoharness2.governance.admission import AdmissionError

        raise AdmissionError("admission_payload_inconsistent", "forced")

    monkeypatch.setattr(generate_mod, "derive_admission_payload", _boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="admission_payload_build_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert any(f.error_type == "admission_payload_build_failed" for f in audit.failure_records)
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"


# ---------------------------------------------------------------------------
# 复核修复 #2：结构契约类异常显式提升 run-fatal（白名单：GateInputError / AdmissionError /
# finalize·deliver 阶段的 pydantic ValidationError）；task-local 故障仍 ABORTED
# ---------------------------------------------------------------------------


def _forced_validation_error():
    from pydantic import ValidationError

    from repoharness2.contracts import EligibilityReport

    try:
        EligibilityReport.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("unreachable")


async def test_gate_input_error_in_finalize_is_run_fatal_not_aborted(monkeypatch):
    from repoharness2.governance import GateInputError

    chain = _formal_chain()

    async def _wiring_boom(**kw):
        raise GateInputError("forced: GradingReport.trajectory_id(traj_9999) 与投影不一致")

    monkeypatch.setattr(generate_mod, "finalize_rollout", _wiring_boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="gate_wiring_error"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2 is None and chain.orchestrator.outcomes == []  # producer 未被调用产 missing
    assert audit.delivered_sample_count == 0 and "step9_samples_delivered" not in audit.steps
    assert any(f.stage == "finalize" and f.error_type == "GateInputError" for f in audit.failure_records)
    assert "gate_wiring_error" in _steps(audit)
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "fatal_run_halt" and receipt.terminal_reason_code == "gate_wiring_error"
    assert receipt.outcome_v2 is None
    assert "cleanup_completed" in _steps(audit)


async def test_validation_error_inside_finalize_is_run_fatal(monkeypatch):
    chain = _formal_chain()
    err = _forced_validation_error()

    async def _contract_boom(**kw):
        raise err

    monkeypatch.setattr(generate_mod, "finalize_rollout", _contract_boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="rh2_contract_validation_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2 is None
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"


async def test_pre_finalize_validation_error_and_task_local_failure_stay_aborted(monkeypatch):
    """对照：finalize 之前的 ValidationError（预算闭环 Brief §6 待确认项，确认前保持 stage fallback）
    与**已归因**的 task-local 故障（typed `harness_bootstrap_failed`）仍归 missing/ABORTED；
    批 A（I05）起裸 RuntimeError = 未归因 → run-fatal `pre_finalize_failure_unclassified`。"""

    chain = _formal_chain()
    err = _forced_validation_error()

    async def _materialize_boom(*a, **kw):
        raise err

    monkeypatch.setattr(chain.orchestrator, "_materialize_rollout_sandbox", _materialize_boom)
    (aborted,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert aborted.remove_sample is True and aborted.status == "aborted"
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2["completion_class"] == "missing"
    assert any(f.stage == "materialize" and f.error_type == "ValidationError" for f in audit.failure_records)
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "aborted"

    crashed = _formal_chain(crash=SlimeBindingError("harness_bootstrap_failed", "claude cli exploded"))
    (aborted2,) = await crashed.orchestrator.generate(_Args(), crashed.base_sample, dict(SAMPLING_PARAMS))
    assert aborted2.status == "aborted"
    assert crashed.finalization.receipts[0].outcome_v2.failure_category == "harness_crash"

    # 批 A（I05）：同一位置的裸异常 = 未归因 → run-fatal，不产 Outcome、不返回 ABORTED
    unclassified = _formal_chain(crash=RuntimeError("claude cli exploded"))
    with pytest.raises(FatalExecutionInfrastructureError, match="pre_finalize_failure_unclassified"):
        await unclassified.orchestrator.generate(_Args(), unclassified.base_sample, dict(SAMPLING_PARAMS))
    assert unclassified.orchestrator.audits[0].outcome_v2 is None


# ---------------------------------------------------------------------------
# stamp_conflict：receipt 落盘之后的 fatal 经现有审计追加 attempt-bound 事实
# ---------------------------------------------------------------------------


async def test_stamp_conflict_appends_attempt_bound_fatal_fact_via_existing_audit(monkeypatch):
    sink_calls: list[dict] = []

    def audit_sink(audit):
        sink_calls.append({
            "physical_attempt_id": audit.physical_attempt_id,
            "failure_types": [f.error_type for f in audit.failure_records],
            "n_records": len(audit.failure_records),
        })

    chain = _formal_chain(audit_sink=audit_sink)

    def _boom(outputs, payload):
        from repoharness2.envpack.termination_facts import TerminationFactsError

        raise TerminationFactsError("forced leaf/attempt mismatch")

    monkeypatch.setattr(generate_mod, "stamp_termination_facts", _boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="termination_facts_stamp_conflict"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    # 磁盘证据：receipt 与首条审计记录都显示成功……
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "delivery_prepared"
    assert sink_calls[0]["failure_types"] == [] and sink_calls[0]["physical_attempt_id"] == PAID
    # ……随后经同一审计通道追加第二条、attempt-bound 的 fatal 事实
    assert len(sink_calls) == 2
    assert sink_calls[1]["physical_attempt_id"] == PAID
    assert sink_calls[1]["failure_types"] == ["termination_facts_stamp_conflict"]
    assert "termination_facts_stamp_conflict" in _steps(audit)
    assert audit.timeline[-1].physical_attempt_id == PAID


async def test_stamp_conflict_audit_append_failure_is_secondary(monkeypatch):
    calls = {"n": 0}

    def audit_sink(audit):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("audit store down on append")

    chain = _formal_chain(audit_sink=audit_sink)

    def _boom(outputs, payload):
        from repoharness2.envpack.termination_facts import TerminationFactsError

        raise TerminationFactsError("forced")

    monkeypatch.setattr(generate_mod, "stamp_termination_facts", _boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="termination_facts_stamp_conflict"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert [f.error_type for f in audit.failure_records] == [
        "termination_facts_stamp_conflict", "post_receipt_fatal_audit_append_failed",
    ]


# ---------------------------------------------------------------------------
# staleness：finalize-time 阈值不再是资格门（B-1 改判 D1-4）
# ---------------------------------------------------------------------------


async def test_finalize_completes_without_staleness_threshold_and_records_mirror_sentinel():
    """fa_formal 不配置 staleness_threshold：启动不拒（旧 `staleness_threshold_required_in_formal_chain`
    已删）、握手构造不 run-fatal（旧 `staleness_threshold_unconfigured` 已删）；握手里写"未镜像 /
    无上界"哨兵并在 audit 时间线留痕；样本照常 online / KEEP_FULL。"""

    chain = _formal_chain(config_overrides={"staleness_threshold": None})  # 曾在此 StartupCheckError
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.handshake.staleness_threshold == STALENESS_THRESHOLD_MIRROR_UNBOUNDED
    assert audit.handshake.staleness_within_threshold is True
    assert "staleness_threshold_mirror_unconfigured" in _steps(audit)
    assert not any(f.error_type.startswith("staleness_threshold") for f in audit.failure_records)
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.metadata["training_eligibility_class"] == "online_policy_loss_eligible"
    payload = _resolve(leaf)
    assert payload.finalize_staleness_steps == 0
    assert _decide(payload).verdict == "KEEP_FULL"
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "delivery_prepared"


async def test_finalize_lag_beyond_recorded_mirror_is_observation_only():
    """turns 版本 3、current 5、镜像阈值 0：握手 lag=2 > 0（staleness_within_threshold=False）——
    只是观测值：第七维通过（版本合法）、样本 online、KEEP_FULL；过期与否由 miles consume-time 判。"""

    chain = _formal_chain(config_overrides={"staleness_threshold": 0}, turn_weight_version="3")
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.handshake.staleness_steps == 2 and audit.handshake.staleness_within_threshold is False
    assert audit.handshake.staleness_threshold == 0
    assert "staleness_threshold_mirror_unconfigured" not in _steps(audit)
    (leaf,) = delivered
    payload = _resolve(leaf)
    fact = payload.eligibility_report.facts.policy_staleness
    assert fact.ok is True and "finalize_lag_observed:2" in fact.evidence_refs
    assert "staleness_exceeded" not in payload.eligibility_report.reason_codes
    assert payload.eligibility_report.eligibility_class == "online_policy_loss_eligible"
    assert payload.finalize_staleness_steps == 2
    assert _decide(payload).verdict == "KEEP_FULL"


def test_handshake_threshold_mirror_defaults_by_mode():
    """镜像缺省：s1_compat 写冻结的 S1 历史值 4（冻结路径零改变）；非 s1 写无上界哨兵；
    显式值原样写入（within 只是记录派生，不是判定）。"""

    from fixtures.common import FixtureSlimeSample

    s1 = _dummy_orchestrator(_formal_config(staleness_threshold=None))  # execution_mode 缺省 = s1_compat
    handshake = s1._build_handshake("traj_hs", [FixtureSlimeSample(weight_versions=["3", "4"], index=0)])
    assert handshake.staleness_threshold == S1_COMPAT_LEGACY_STALENESS_THRESHOLD == 4
    formal = _formal_chain(config_overrides={"staleness_threshold": None}).orchestrator
    handshake2 = formal._build_handshake("traj_hs", [FixtureSlimeSample(weight_versions=["5"], index=0)])
    assert handshake2.staleness_threshold == STALENESS_THRESHOLD_MIRROR_UNBOUNDED
    assert handshake2.staleness_within_threshold is True
    explicit = _dummy_orchestrator(_formal_config(staleness_threshold=1))
    handshake3 = explicit._build_handshake("traj_hs", [FixtureSlimeSample(weight_versions=["3", "4"], index=0)])
    assert handshake3.staleness_threshold == 1 and handshake3.staleness_within_threshold is False
