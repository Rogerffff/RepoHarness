"""W1b 第一集成切片（F5）：termination 事实 producer 接线 + 登记边界判定。

被测事实（rh2/src/repoharness2/adapters/slime/generate.py）：
- finally 段 receipt 持久化成功后 `termination_facts_payload(receipt)`（只对形成 Outcome v2
  的 attempt），载荷挂 audit，`generate()` 返回前盖到交付面；
- 登记边界：step8（audit.finalized 已设）之后、成功 Outcome 产出之前的通用异常路径**真实可达**
  （fa_formal 的 verify_integrity 走 docker 通道，可抛 OSError）——按 P1-1 先例撤销静止事实并
  清 finalized 引用，receipt/outcome 引用对称、事实可派生、abort 形状照常返回；
- Outcome 已产出（CAS）后 deliver 阶段失败：引用两侧同源，不清；
- 派生失败 = run-halt（receipt 已 durable）；盖章冲突 = run-halt；无 Outcome 的 attempt 记跳过；
- s1_compat 零改变。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    FakeFinalizationStore,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
)

from repoharness2.adapters.slime import generate as generate_mod  # noqa: E402
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402
from repoharness2.envpack.termination_facts import (  # noqa: E402
    TERMINATION_FACTS_METADATA_KEY,
    TerminationFactsError,
    assert_payload_dereferences,
    derive_termination_facts,
    resolve_termination_facts,
)

PAID = "exec_F22#p1-cafe1234"  # _stamp_fa_identity 的固定 attempt 身份


class _FrozenWs:
    def __init__(self, underlying):
        self._u = underlying

    async def run_bash(self, script):
        return await self._u.run_bash(script)


class _RaisingIntegrityWs(_FrozenWs):
    async def verify_integrity(self) -> bool:
        raise OSError("docker exec channel broken during post-grading integrity re-check")


class _Barrier:
    ws_cls = _FrozenWs

    async def establish(self, *, workspace, audit):
        return QuiescenceConfirmed(
            frozen_grading_workspace=self.ws_cls(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",)
        )


class _RaisingBarrier(_Barrier):
    ws_cls = _RaisingIntegrityWs


def _formal_chain(store=None, *, barrier=None, **kwargs):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=barrier or _Barrier(), turns=turns,
        finalization_store=store, **kwargs,
    )
    _stamp_fa_identity(chain.base_sample)
    return chain


def _steps(audit) -> list[str]:
    return [e.step for e in audit.timeline]


async def test_exception_after_finalize_is_reachable_and_handled_per_p1_1():
    """登记边界：step8 之后 verify_integrity 的通道异常——之前 receipt 会带 finalized 的
    grading/eligibility 引用而 Outcome 引用为 None（派生 fail-closed）；现按 P1-1 先例
    先撤销静止事实、清 finalized 引用，再走异常收口。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store, barrier=_RaisingBarrier())
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert "step8_gate_finalized" in audit.steps  # 边界确实在 finalize 之后
    assert audit.finalized is None
    assert "finalized_refs_cleared_on_exception" in _steps(audit)
    assert any(f.stage == "finalize" and f.error_type == "OSError" for f in audit.failure_records)
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "aborted"
    assert receipt.grading_report_id is None and receipt.eligibility_report_id is None
    assert receipt.outcome_v2 is not None
    assert receipt.outcome_v2.eligibility_report_id is None
    assert receipt.outcome_v2.completion_class == "missing"  # 静止事实已撤销 → missing
    assert receipt.runtime_quiescence_confirmed is False
    facts = derive_termination_facts(receipt)  # 派生不再 fail-closed
    assert facts.fresh_grading_complete is False and facts.eligibility_report_id is None
    assert "termination_facts_derived" in _steps(audit)
    # abort 形状照常返回，且带本 attempt 的事实载荷
    (aborted,) = delivered
    assert aborted.remove_sample is True
    payload = resolve_termination_facts(aborted.metadata)
    assert payload.physical_attempt_id == PAID and payload.fresh_grading_complete is False
    assert_payload_dereferences(payload, receipt)
    assert "cleanup_completed" in _steps(audit)


async def test_deliver_failure_after_outcome_keeps_symmetric_refs():
    """Outcome 已产出（CAS）后 deliver 阶段失败：finalized 引用不清，receipt 与 Outcome 引用同源。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)

    def _sink_boom(signal):
        raise OSError("repair signal sink: disk full")

    chain.orchestrator._repair_signal_sink = _sink_boom
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.finalized is not None
    assert "finalized_refs_cleared_on_exception" not in _steps(audit)
    assert any(f.stage == "deliver" for f in audit.failure_records)
    (receipt,) = store.receipts
    assert receipt.eligibility_report_id == receipt.outcome_v2.eligibility_report_id is not None
    assert receipt.grading_report_id is not None
    payload = resolve_termination_facts(delivered[0].metadata)
    assert payload.fresh_grading_complete is True and payload.eligibility_report_id == receipt.eligibility_report_id
    assert delivered[0].remove_sample is True


async def test_happy_path_payload_on_every_leaf_and_unique_dereference():
    store_a = FakeFinalizationStore()
    chain_a = _formal_chain(store_a)
    delivered = await chain_a.orchestrator.generate(_Args(), chain_a.base_sample, dict(SAMPLING_PARAMS))
    audit = chain_a.orchestrator.audits[0]
    assert audit.steps[-1] == "step9_samples_delivered"
    assert audit.termination_facts_payload is not None
    (receipt_a,) = store_a.receipts
    assert delivered and all(TERMINATION_FACTS_METADATA_KEY in leaf.metadata for leaf in delivered)
    payload = resolve_termination_facts({**delivered[0].metadata, "rh2_physical_attempt_id": PAID,
                                         "rh2_rollout_execution_id": "exec_F22"})
    assert payload.physical_attempt_id == PAID and payload.rollout_execution_id == "exec_F22"
    assert payload.eligibility_report_id == audit.finalized.eligibility_report.report_id
    assert payload.grading_report_id == audit.finalized.grading_report.report_id
    assert payload.termination_kind == "completed" and payload.execution_scope_quiescent is True
    assert_payload_dereferences(payload, receipt_a)
    # 另一次 attempt 的 receipt：同一载荷不得解引用过去
    store_b = FakeFinalizationStore()
    chain_b = _formal_chain(store_b)
    chain_b.base_sample.metadata["rh2_physical_attempt_id"] = "exec_F22#p2-feedbeef"
    chain_b.base_sample.metadata["rh2_physical_attempt_seq"] = 2
    await chain_b.orchestrator.generate(_Args(), chain_b.base_sample, dict(SAMPLING_PARAMS))
    (receipt_b,) = store_b.receipts
    with pytest.raises(TerminationFactsError, match="解引用"):
        assert_payload_dereferences(payload, receipt_b)


async def test_attempt_without_outcome_skips_facts_without_forging():
    """身份不全的 fa_formal 派发（W1a 负例形状）：无 Outcome v2 → 不派生、不伪造，如实记跳过。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    chain.base_sample.metadata = {}  # 未铸造身份
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2 is None and store.receipts
    assert "termination_facts_skipped_no_outcome" in _steps(audit)
    assert audit.termination_facts_payload is None
    assert TERMINATION_FACTS_METADATA_KEY not in delivered[0].metadata


async def test_underivable_facts_is_run_halt_after_receipt_durable(monkeypatch):
    store = FakeFinalizationStore()
    chain = _formal_chain(store)

    def _boom(receipt):
        raise TerminationFactsError("forced contradiction")

    monkeypatch.setattr(generate_mod, "termination_facts_payload", _boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="termination_facts_underivable"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert store.receipts  # receipt 先 durable
    assert any(f.error_type == "termination_facts_underivable" for f in audit.failure_records)
    assert "cleanup_completed" in _steps(audit)  # 不阻止清理


async def test_stamp_conflict_is_run_halt(monkeypatch):
    chain = _formal_chain(FakeFinalizationStore())

    def _boom(outputs, payload):
        raise TerminationFactsError("forced leaf/attempt mismatch")

    monkeypatch.setattr(generate_mod, "stamp_termination_facts", _boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="termination_facts_stamp_conflict"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))


async def test_s1_compat_unchanged_no_payload():
    chain = build_dense_chain()
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.steps[-1] == "step9_samples_delivered"
    assert audit.termination_facts_payload is None
    assert not any(s.startswith("termination_facts") for s in _steps(audit))
    assert all(TERMINATION_FACTS_METADATA_KEY not in leaf.metadata for leaf in delivered)
