"""W1b 第二段：三终态在交付面的落点（adapters/slime/generate.py，fa_formal 链）。

被测事实：
- ③ 完整 finalize 但不合格（failed_to_grade / 缺能力事实）→ **真实样本**交付（remove_sample=False、
  status 非 aborted）+ typed admission 载荷，不再压成 abort 形状（`rh2_gate_degraded` 在 fa_formal
  下消失）；unsafe（present + 永久拒绝，契约封闭豁免集）同样真实交付、载荷无 EligibilityReport；
- ② 真实 ABORTED 只给 completion=missing（harness 崩溃）；
- ① 结构矛盾 typed raise：present Outcome 却走 abort 形状、载荷派生矛盾；
- termination_facts_stamp_conflict 发生在 receipt/审计落盘之后：经现有审计通道追加 attempt-bound
  fatal 事实（第二条 append-only 记录），receipt 仍显示 delivery_prepared；
- staleness 阈值参数化接口：fa_formal 缺显式阈值启动即拒；非 s1 模式握手缺阈值 run-fatal；
  s1_compat 回退冻结的 S1 历史值。
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
    StartupCheckError,
)
from repoharness2.envpack.termination_facts import resolve_termination_facts  # noqa: E402
from repoharness2.governance import REQUIRED_SANDBOX_CAPABILITIES, SandboxCapabilityFacts  # noqa: E402
from repoharness2.governance.admission import (  # noqa: E402
    ADMISSION_METADATA_KEY,
    DispositionPolicy,
    decide_member_disposition,
    resolve_admission_payload,
)

PAID = "exec_F22#p1-cafe1234"
EXEC = "exec_F22"
IDENTITY = {"rh2_physical_attempt_id": PAID, "rh2_rollout_execution_id": EXEC}


def _capability_facts_provider(audit):
    return SandboxCapabilityFacts(
        trajectory_id=audit.trajectory_id,
        lease_id=audit.lease.lease_id if audit.lease is not None else "lease_test",
        verified_capabilities=list(REQUIRED_SANDBOX_CAPABILITIES),
        violations=[],
        evidence_refs=["sandbox_probe_test"],
        verified_at_utc=generate_mod._now_utc(),
    )


def _formal_chain(store=None, *, barrier=None, **kwargs):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=barrier or _Barrier(), turns=turns,
        finalization_store=store or FakeFinalizationStore(), **kwargs,
    )
    _stamp_fa_identity(chain.base_sample)
    return chain


def _resolve(leaf):
    return resolve_admission_payload({**leaf.metadata, **IDENTITY})


def _decide(payload, policy=None):
    return decide_member_disposition(payload, policy=policy or DispositionPolicy(), finalize_staleness_threshold=4)


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
    assert payload.finalize_staleness_threshold == 4
    assert leaf.metadata["eligibility_report_ref"] == payload.eligibility_report.report_id
    facts = resolve_termination_facts({**leaf.metadata, **IDENTITY})
    assert facts.eligibility_report_id == payload.eligibility_report.report_id
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "reward_scope_none")
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "delivery_prepared"
    assert (next(p for p in tmp_path.iterdir() if p.is_dir()) / "eligibility_report.json").exists()


async def test_all_ok_without_capability_facts_is_delivered_but_drops_by_a3():
    chain = _formal_chain()
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.reward == 1.0
    payload = _resolve(leaf)
    report = payload.eligibility_report
    assert report.eligibility_class == "audit_only_or_rejected"
    assert report.facts.security_and_leakage.reason_codes == ["sandbox_capability_facts_missing"]
    assert all(getattr(report.facts, d).ok for d in (
        "token_provenance", "logprob_alignment", "loss_mask_integrity", "reward_scope", "clean_grading", "policy_staleness"))
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "sandbox_capability_facts_missing")


async def test_all_ok_with_capability_facts_is_online_and_keep_full():
    chain = _formal_chain(sandbox_capability_facts_provider=_capability_facts_provider)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.finalized.group_repair_signal.degraded is False
    assert "degraded_member_delivered_for_group_admission" not in _steps(audit)
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.reward == 1.0
    assert leaf.metadata["training_eligibility_class"] == "online_policy_loss_eligible"
    payload = _resolve(leaf)
    assert payload.eligibility_report.facts.all_ok()
    assert "sandbox_capability_facts:lease_" in " ".join(payload.eligibility_report.facts.security_and_leakage.evidence_refs)
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("KEEP_FULL", "all_dimensions_ok")


async def test_unsafe_is_delivered_without_report_and_drops_by_exemption():
    """附录 A 契约豁免集：present + unsafe 永久拒绝——真实交付、载荷无 EligibilityReport，
    receipt=delivery_prepared，审计 disposition 仍派生 permanent_rejected。"""

    import base64
    import hashlib
    import json
    import tempfile

    from repoharness2.adapters.slime.bringup import write_execution_audit_record
    from repoharness2.adapters.slime.generate import QuiescenceConfirmed as _QC
    from repoharness2.grading.manager import HygieneRules

    content = b"def test_evil():\n    assert True\n"
    b64 = base64.b64encode(content).decode()
    sha = hashlib.sha256(content).hexdigest()  # census 行的 digest 列是裸 hex（与 test_b5 的 _TamperWs 同形）

    class _TamperWs:
        snapshot_ref = "sha256:abc"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            from types import SimpleNamespace

            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=f"regular\t100644\t{sha}\ttests/test_evil.py\n", stderr="")
            if "base64 <" in script:
                return SimpleNamespace(exit_code=0, stdout=f"tests/test_evil.py\t{b64}\n", stderr="")
            return await self._u.run_bash(script)

        async def verify_integrity(self):
            return True

    class _TamperBarrier:
        async def establish(self, *, workspace, audit):
            return _QC(frozen_grading_workspace=_TamperWs(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",))

    base_task = make_task(TASK_ID_DENSE)
    task = dataclasses.replace(
        base_task, grading_spec=dataclasses.replace(base_task.grading_spec, hygiene=HygieneRules(test_globs=("tests/*",)))
    )
    chain = _formal_chain(barrier=_TamperBarrier(), task=task)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == [] and audit.finalized is None
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
    chain = _formal_chain(crash=RuntimeError("harness crashed mid-run"))
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (aborted,) = delivered
    assert aborted.remove_sample is True and aborted.status == "aborted"
    assert ADMISSION_METADATA_KEY not in aborted.metadata
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "aborted" and receipt.outcome_v2.completion_class == "missing"


async def test_evaluation_placeholder_unchanged_in_formal_mode():
    chain = _formal_chain(sandbox_capability_facts_provider=_capability_facts_provider)
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
# staleness 阈值参数化接口（D1-4）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, True, -1])
def test_formal_chain_requires_explicit_staleness_threshold_at_startup(bad):
    with pytest.raises(StartupCheckError, match="staleness_threshold_required_in_formal_chain"):
        build_dense_chain(
            config=_formal_config(policy_version="5", execution_mode="fa_formal", staleness_threshold=bad),
            runtime_quiescence_barrier=_Barrier(),
        )


def test_handshake_without_threshold_is_fatal_in_non_s1_and_legacy_pin_in_s1():
    from fixtures.common import FixtureSlimeSample

    chain = _formal_chain()
    orch = chain.orchestrator
    orch.config = dataclasses.replace(orch.config, staleness_threshold=None)
    with pytest.raises(FatalExecutionInfrastructureError, match="staleness_threshold_unconfigured"):
        orch._build_handshake("traj_hs", [FixtureSlimeSample(weight_versions=["5"], index=0)])
    s1 = _dummy_orchestrator(_formal_config(staleness_threshold=None))  # execution_mode 缺省 = s1_compat
    handshake = s1._build_handshake("traj_hs", [FixtureSlimeSample(weight_versions=["3", "4"], index=0)])
    assert handshake.staleness_threshold == S1_COMPAT_LEGACY_STALENESS_THRESHOLD == 4
    explicit = _dummy_orchestrator(_formal_config(staleness_threshold=1))
    assert explicit._build_handshake("traj_hs", [FixtureSlimeSample(weight_versions=["3", "4"], index=0)]).staleness_within_threshold is False
