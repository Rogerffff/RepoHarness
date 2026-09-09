"""W1b 第一集成切片（F5）：termination 事实 producer 接线 + post-finalize 失败域分流。

被测事实（rh2/src/repoharness2/adapters/slime/generate.py）：
- finally 段 receipt 持久化成功后 `termination_facts_payload(receipt)`（只对形成 Outcome v2 的
  attempt），载荷挂 audit，`generate()` 返回前盖到交付面；
- **post-finalize 失败域五分流**（W1b 切片一 codex 复核 必修 1，取代切片一初版"任意 post-finalize
  异常撤销 finalized 洗成 missing/ABORTED"的兜底——那会让 Outcome schema/producer bug、docker
  完整性检查异常、核心 sidecar 磁盘失败被 miles 当普通缺员丢弃并补采）：
    ①② **W3a（决策包 D2-1）起撤销**：评分后不再回读原 workspace 复核指纹（rollout 容器在
       artifact 持久化后、评分之前已释放）——verify_integrity() 返回 False / 抛异常都**不再被
       调用**，不再产生 `snapshot_integrity_mismatch` / `integrity_recheck_failed`；本文件保留
       drifted / raising 两种 FrozenWorkspace 替身作反例，证明它们对正式链无影响；
    ③ Outcome producer / 契约异常     → run-fatal `outcome_producer_failed`，且 producer 只允许调用一次
                                        （二次调用本身 = run-fatal `outcome_producer_called_twice`）；
    ④ 核心 admission sidecar 写失败   → run-fatal `admission_artifact_write_failed`（cleanup 仍执行）；
    ⑤ finalize 之前的**已归因** task-local 故障 → 仍是普通 ABORTED（missing Outcome，miles 补采）；
       批 A（I05，2026-09-09）起"已归因"= typed 码在 FAILURE_CODE_TERMINATION_MAP 内；未映射
       的 typed 码与任何非 typed 异常 → run-fatal `pre_finalize_failure_unclassified`（⑤b/⑤c/⑤d）；
  另：可选 telemetry（组修复信号转发通道）写失败 → 记录后照常交付，不改写样本处置；
  通用 except 里若发现 `audit.finalized is not None` → 不该到达的状态，升 fatal
  `post_finalize_failure_unclassified`，不撤销 finalized。
- in-flight Fatal 的 receipt disposition = fatal_run_halt（build_finalization_receipt）。
"""

from __future__ import annotations

import dataclasses
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
from repoharness2.adapters.slime.generate import QuiescenceConfirmed, SlimeBindingError  # noqa: E402
from repoharness2.adapters.slime.outcome_producer import FAILURE_CODE_TERMINATION_MAP  # noqa: E402
from repoharness2.envpack.termination_facts import (  # noqa: E402
    TERMINATION_FACTS_METADATA_KEY,
    TerminationFactsError,
    assert_payload_dereferences,
    derive_termination_facts,
    resolve_termination_facts,
)

PAID = "exec_F22#p1-cafe1234"  # _stamp_fa_identity 的固定 attempt 身份


class _FrozenWs:
    """quiescence_barrier.FrozenWorkspace 的替身形状：run_bash 委托 + snapshot_ref（mismatch 分支的证据引用）。"""

    snapshot_ref = "sha256:abc"

    def __init__(self, underlying):
        self._u = underlying

    async def run_bash(self, script):
        return await self._u.run_bash(script)


class _IntactWs(_FrozenWs):
    async def verify_integrity(self) -> bool:
        return True


class _DriftedWs(_FrozenWs):
    async def verify_integrity(self) -> bool:
        return False


class _RaisingIntegrityWs(_FrozenWs):
    async def verify_integrity(self) -> bool:
        raise OSError("docker exec channel broken during post-grading integrity re-check")


class _Barrier:
    ws_cls = _IntactWs

    async def establish(self, *, workspace, audit):
        return QuiescenceConfirmed(
            frozen_grading_workspace=self.ws_cls(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",)
        )


class _DriftedBarrier(_Barrier):
    ws_cls = _DriftedWs


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


def _spy_producer(orchestrator) -> list[dict]:
    """记录 Outcome producer 的每次调用（守卫入口层面）。"""

    calls: list[dict] = []
    original = orchestrator._produce_outcome_v2

    def spy(**kw):
        calls.append(kw)
        return original(**kw)

    orchestrator._produce_outcome_v2 = spy
    return calls


# ---------------------------------------------------------------------------
# post-finalize 失败域五分流
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("barrier_cls", [_DriftedBarrier, _RaisingBarrier])
async def test_split_1_2_frozen_workspace_probe_not_consulted_after_release(barrier_cls):
    """①② W3a（D2-1，T1 oracle 改动，原 split_1 = 漂移 → missing/ABORTED、split_2 = 复核异常
    → run-fatal）：评分后不再回读原 workspace——drifted / raising 的 verify_integrity 都不被调用，
    attempt 正常 finalize、present_complete、真实交付；producer 恰好一次；receipt delivery_prepared；
    容器在评分前已释放。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store, barrier=barrier_cls())
    calls = _spy_producer(chain.orchestrator)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert "step8_gate_finalized" in audit.steps
    assert "snapshot_integrity_mismatch" not in _steps(audit)
    assert "integrity_recheck_failed" not in _steps(audit)
    assert audit.finalized is not None and audit.runtime_quiescence_confirmed is True
    assert audit.rollout_container_released_before_grading is True
    assert len(calls) == 1
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "delivery_prepared"
    assert receipt.outcome_v2.completion_class == "present_complete"
    assert receipt.outcome_v2.reason_code is None
    assert receipt.grading_report_id is not None and receipt.eligibility_report_id is not None
    facts = derive_termination_facts(receipt)
    assert facts.fresh_grading_complete is True
    assert delivered and all(leaf.remove_sample is False for leaf in delivered)
    payload = resolve_termination_facts({**delivered[0].metadata, "rh2_physical_attempt_id": PAID,
                                         "rh2_rollout_execution_id": "exec_F22"})
    assert_payload_dereferences(payload, receipt)


async def test_split_3_outcome_producer_exception_is_run_fatal_and_called_once(monkeypatch):
    """③ producer/契约异常：run-fatal；producer 只被调用一次（不允许二次产出 missing 洗成 ABORTED）。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    calls = _spy_producer(chain.orchestrator)

    def _contract_boom(**kw):
        raise ValueError("forced Outcome v2 contract violation")

    monkeypatch.setattr(generate_mod, "build_outcome_v2", _contract_boom)
    with pytest.raises(FatalExecutionInfrastructureError, match="outcome_producer_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert len(calls) == 1
    assert audit.finalized is not None and audit.outcome_v2 is None
    assert any(f.stage == "outcome_producer" and f.error_type == "ValueError" for f in audit.failure_records)
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"
    assert receipt.terminal_reason_code == "outcome_producer_failed"
    assert "cleanup_completed" in _steps(audit)


async def test_split_3b_producer_second_call_itself_is_run_fatal():
    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2 is not None
    with pytest.raises(FatalExecutionInfrastructureError, match="outcome_producer_called_twice"):
        chain.orchestrator._produce_outcome_v2(
            audit=audit, raw_meta=chain.base_sample.metadata, termination_kind="completed",
            failure_category="capture_incomplete", reason_code="x", failed_component="deliver",
            task_resolved=None, turn_weight_versions=None, current_version_at_finalize=None,
            eligibility_report_id=None,
        )


async def test_split_4_core_admission_sidecar_write_failure_is_run_fatal_cleanup_still_runs(tmp_path):
    """④ 核心 admission sidecar（eligibility/grading report、projection、capture、tape）写失败：
    真实文件系统失败（artifact_dir 位置被普通文件占住）→ run-fatal，样本不交付，cleanup 仍执行。"""

    blocked = tmp_path / "artifacts"
    blocked.write_text("not a directory")
    store = FakeFinalizationStore()
    chain = _formal_chain(store, artifact_dir=blocked)
    calls = _spy_producer(chain.orchestrator)
    with pytest.raises(FatalExecutionInfrastructureError, match="admission_artifact_write_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert len(calls) == 1 and audit.outcome_v2 is not None  # 成功 Outcome 已产出，不被改写
    assert audit.finalized is not None
    assert any(f.error_type == "admission_artifact_write_failed" for f in audit.failure_records)
    assert audit.delivered_sample_count == 0 and "step9_samples_delivered" not in audit.steps
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"
    assert receipt.terminal_reason_code == "admission_artifact_write_failed"
    assert receipt.eligibility_report_id == receipt.outcome_v2.eligibility_report_id is not None
    assert "cleanup_completed" in _steps(audit) and audit.lease_released is True


async def test_split_5_pre_finalize_task_local_failure_stays_aborted():
    """⑤ finalize 之前的**已归因** task-local 故障（harness 驱动引导失败，typed
    `harness_bootstrap_failed`）：仍是普通 ABORTED——missing Outcome，receipt aborted，producer
    恰好一次，无 Fatal。批 A T1 oracle 改动：此前用裸 RuntimeError 模拟"harness 崩溃"，现在裸
    异常 = 未归因 → run-fatal（见 5b）。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(
        store, crash=SlimeBindingError("harness_bootstrap_failed", "docker exec failed (exit=1): useradd")
    )
    calls = _spy_producer(chain.orchestrator)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert "step8_gate_finalized" not in audit.steps and audit.finalized is None
    assert len(calls) == 1
    (aborted,) = delivered
    assert aborted.remove_sample is True
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "aborted"
    assert receipt.outcome_v2.completion_class == "missing"
    assert receipt.outcome_v2.failure_category == "harness_crash"
    payload = resolve_termination_facts(aborted.metadata)
    assert payload.termination_kind == "harness_crash" and payload.fresh_grading_complete is False


async def test_split_5b_unclassified_pre_finalize_exception_is_run_fatal_and_cleans_up():
    """⑤b 批 A（I05，第二组 §2 / 06 §2）：finalize 之前的**非 typed** 异常（裸 RuntimeError，模拟
    harness 驱动内的编程错误）不再洗成 ABORTED——run-fatal `pre_finalize_failure_unclassified`；
    producer 不被调用（无 Outcome，不伪造 missing）；receipt 记 fatal_run_halt；cleanup 照常
    （容器 rm + drop_session），不留残留。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store, crash=RuntimeError("harness driver bug"))
    calls = _spy_producer(chain.orchestrator)
    with pytest.raises(FatalExecutionInfrastructureError, match="pre_finalize_failure_unclassified"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert calls == [] and audit.outcome_v2 is None and audit.finalized is None
    assert "pre_finalize_failure_unclassified" in _steps(audit)
    assert any(f.stage == "harness_run" and f.error_type == "RuntimeError" for f in audit.failure_records)
    assert len(chain.docker.removed) == 1 and audit.lease_released is True  # cleanup 照常
    assert len(chain.adapter_ref["adapter"].dropped) == 1
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"


async def test_split_5c_leaf_facts_programming_error_is_run_fatal():
    """⑤c 批 A（第二组 §2 的例子）：我方 `_leaf_facts_fn` 抛 TypeError → run-fatal（stage=assemble），
    不是 missing/ABORTED——否则只在有分支的轨迹上触发的 bug 会静默筛选训练分布。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)

    def _buggy(sid, samples, hook):
        raise TypeError("'NoneType' object is not iterable")

    chain.orchestrator._leaf_facts_fn = _buggy
    with pytest.raises(FatalExecutionInfrastructureError, match="pre_finalize_failure_unclassified"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert any(f.stage == "assemble" and f.error_type == "TypeError" for f in audit.failure_records)
    assert audit.outcome_v2 is None
    assert len(chain.docker.removed) == 1  # cleanup 照常


@pytest.mark.parametrize("code", ["capture_record_unknown_in_backfill", "leaf_facts_length_mismatch"])
async def test_split_5d_structural_contradiction_codes_are_run_fatal(code):
    """⑤d 批 A（第二组 §1 点名的两个账实矛盾）：leaf_facts_length_mismatch（两条分支只配一份事实）
    与 capture_record_unknown_in_backfill（回链引用没有对应 TurnTape）不再按 capture_incomplete
    收口为 ABORTED——run-fatal。判定唯一来源 = 这两个码**不在** FAILURE_CODE_TERMINATION_MAP 内
    （Codex 批 A 审查可简化项：不另设公开集合，两码只在本参数化里点名）。"""

    assert code not in FAILURE_CODE_TERMINATION_MAP
    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    original = chain.orchestrator._leaf_facts_fn

    def _fn(sid, samples, hook):
        facts = list(original(sid, samples, hook))
        if code == "leaf_facts_length_mismatch":
            return facts * 2
        return [dataclasses.replace(f, capture_record_ids=("cap_ghost",)) for f in facts]

    chain.orchestrator._leaf_facts_fn = _fn
    with pytest.raises(FatalExecutionInfrastructureError, match="pre_finalize_failure_unclassified"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert any(f.stage == "assemble" and f"[{code}]" in f.detail for f in audit.failure_records)
    assert audit.outcome_v2 is None and len(chain.docker.removed) == 1


async def test_telemetry_repair_signal_sink_failure_records_and_still_delivers():
    """可选 telemetry：组修复信号转发通道写失败 → 记录 failure_record，样本照常交付（不 ABORTED）。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)

    def _sink_boom(signal):
        raise OSError("repair signal sink: disk full")

    chain.orchestrator._repair_signal_sink = _sink_boom
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert audit.steps[-1] == "step9_samples_delivered" and audit.delivered_sample_count == len(delivered)
    assert all(leaf.remove_sample is False for leaf in delivered)
    assert audit.repair_signal_forwarded is False
    assert any(f.error_type == "repair_signal_sink_failed" for f in audit.failure_records)
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "delivery_prepared"
    assert all(TERMINATION_FACTS_METADATA_KEY in leaf.metadata for leaf in delivered)


async def test_post_finalize_unclassified_exception_is_run_fatal_not_laundered():
    """删除兜底后的行为：deliver 阶段冒出未分类异常（模拟程序 bug）→ 通用 except 发现
    finalized 在场 → fatal `post_finalize_failure_unclassified`，不撤销 finalized，不二次产出。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    calls = _spy_producer(chain.orchestrator)

    def _deliver_bug(**kw):
        raise RuntimeError("unexpected bug inside _deliver")

    chain.orchestrator._deliver = _deliver_bug
    with pytest.raises(FatalExecutionInfrastructureError, match="post_finalize_failure_unclassified"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]

    assert len(calls) == 1 and audit.outcome_v2 is not None
    assert audit.finalized is not None and audit.runtime_quiescence_confirmed is True
    assert "post_finalize_failure_unclassified" in _steps(audit)
    assert "finalized_refs_cleared_on_exception" not in _steps(audit)
    assert any(f.stage == "deliver" and f.error_type == "RuntimeError" for f in audit.failure_records)
    (receipt,) = store.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"
    assert receipt.terminal_reason_code == "post_finalize_failure_unclassified"
    assert "cleanup_completed" in _steps(audit)


# ---------------------------------------------------------------------------
# producer 正常接线
# ---------------------------------------------------------------------------


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
    with pytest.raises(TerminationFactsError, match="不一致"):
        assert_payload_dereferences(payload, receipt_b)


async def test_attempt_without_outcome_skips_facts_without_forging():
    """身份不全的 fa_formal 派发（W1a 负例形状；Brief §6 起为 typed run-fatal）：无 Outcome v2 → 不派生、
    不伪造，如实记跳过；receipt 仍先 durable。"""

    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    chain.base_sample.metadata = {}  # 未铸造身份
    with pytest.raises(FatalExecutionInfrastructureError, match="fa_identity_incomplete_in_formal_mode"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2 is None and store.receipts
    assert "termination_facts_skipped_no_outcome" in _steps(audit)
    assert audit.termination_facts_payload is None


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
