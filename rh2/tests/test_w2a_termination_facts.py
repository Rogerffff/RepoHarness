"""W2a termination 事实派生视图测试（F5 修复后的接口）。

原 `TerminationFactsV1` 独立记录已删除（Wave1 复核 F5：缺 attempt 身份 +
第二事实 owner）。现在的被测面 = `derive_termination_facts(receipt)` 只读
派生：所有事实来自 `FinalizationReceiptV1 + 内嵌 RolloutAttemptOutcomeV2`，
不存在任何可独立注入的布尔字段。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from repoharness2.contracts.fa_runtime import (
    ExecutionIdentity,
    RolloutAttemptOutcomeV2,
)
from repoharness2.contracts.finalization import (
    FinalizationReceiptV1,
    SessionDrainReceiptV1,
)
from repoharness2.envpack.termination_facts import (
    TerminationFactsError,
    TerminationFactsView,
    derive_termination_facts,
)

_PA = "exec_1#p1-deadbeef"


def _identity(pa: str | None = _PA) -> ExecutionIdentity:
    return ExecutionIdentity(
        prompt_group_id="miles_g0",
        group_index=0,
        rollout_execution_id="exec_1",
        physical_attempt_id=pa,
        # ExecutionIdentity 约束：attempt id 与 seq 同现同缺
        physical_attempt_seq=None if pa is None else 1,
    )


def _outcome(*, kind: str = "completed", pa: str | None = _PA, **over) -> RolloutAttemptOutcomeV2:
    base = dict(
        outcome_id="o1", identity=_identity(pa), member_slot=0, attempt_number=1,
        completion_class="present_complete", termination_kind=kind,
        task_outcome="unresolved", recovery_scope="none",
        turn_weight_versions=["1"], intra_execution_version_span=0,
        current_version_at_finalize="1", eligibility_report_id="er_1",
    )
    base.update(over)
    return RolloutAttemptOutcomeV2(**base)


_UNSET = object()


def _drain(pa: str) -> SessionDrainReceiptV1:
    return SessionDrainReceiptV1(
        receipt_id="drain_1", session_id="s-1", trajectory_id="traj_1",
        task_id="swe_gym_lite::t1", physical_attempt_id=pa,
        revoke_enforced=True, capture_record_count=1,
        pending_turns_after_drain=0, unfinalized_drafts_after_drain=0,
        poison_clean=True,
        drained_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )


def _receipt(*, pa: str | None = _PA, outcome: object = _UNSET,
             **over) -> FinalizationReceiptV1:
    base = dict(
        receipt_id="rcpt_1", task_id="swe_gym_lite::t1", trajectory_id="traj_1",
        physical_attempt_id=pa, attempt_disposition="delivery_prepared",
        session_id="s-1" if pa else None,
        drain_receipt=_drain(pa) if pa else None,
        drain_receipt_ref="drain_1" if pa else None,
        outcome_v2=_outcome(pa=pa) if outcome is _UNSET else outcome,
        frozen_patch_digest="sha256:" + "a" * 64,
        grading_report_id="gr_1", eligibility_report_id="er_1",
        runtime_quiescence_confirmed=True,
        started_epoch_seconds=100.0,
        finalized_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    base.update(over)
    return FinalizationReceiptV1(**base)


# ---------------------------------------------------------------------------
# 正例：派生属性来自权威对象
# ---------------------------------------------------------------------------


def test_derive_policy_horizon_facts():
    facts = derive_termination_facts(
        _receipt(outcome=_outcome(kind="task_token_budget_exhausted",
                                  completion_class="present_truncated"))
    )
    assert facts.physical_attempt_id == _PA
    assert facts.task_id == "swe_gym_lite::t1"
    assert facts.trajectory_id == "traj_1"
    assert facts.termination_kind == "task_token_budget_exhausted"
    assert facts.triggered_by_policy_horizon is True
    assert facts.triggered_by_hard_wall is False
    assert facts.execution_scope_quiescent is True
    assert facts.canonical_frozen_patch_formed is True
    assert facts.fresh_grading_complete is True
    assert facts.grading_report_id == "gr_1"
    assert facts.eligibility_report_id == "er_1"
    # exact ref：底层权威对象可回链
    assert facts.outcome.outcome_id == "o1"
    assert facts.receipt_id == "rcpt_1"


def test_derive_hard_wall_facts():
    facts = derive_termination_facts(
        _receipt(outcome=_outcome(kind="hard_wall_timeout",
                                  completion_class="present_truncated"))
    )
    assert facts.triggered_by_hard_wall is True
    assert facts.triggered_by_policy_horizon is False


def test_derive_incomplete_closure_facts_are_false_not_error():
    """frozen patch / grading 引用缺失 = 事实为"未形成/未完成"，不是派生错误。"""

    facts = derive_termination_facts(
        _receipt(frozen_patch_digest=None, grading_report_id=None,
                 eligibility_report_id=None,  # outcome missing 类无 eligibility 引用，receipt 亦不得声称
                 runtime_quiescence_confirmed=False,
                 attempt_disposition="aborted",
                 outcome=_outcome(kind="harness_crash", completion_class="missing",
                                  failure_category="harness_crash",
                                  task_outcome="unknown", reward_unavailable=True,
                                  turn_weight_versions=[],
                                  intra_execution_version_span=None,
                                  current_version_at_finalize=None,
                                  eligibility_report_id=None))
    )
    assert facts.canonical_frozen_patch_formed is False
    assert facts.fresh_grading_complete is False
    assert facts.execution_scope_quiescent is False


def test_wall_clock_is_passthrough_correlation_only():
    facts = derive_termination_facts(_receipt())
    assert facts.started_epoch_seconds == 100.0
    assert facts.finalized_at_utc == datetime(2026, 9, 2, tzinfo=timezone.utc)
    # 刻意不提供 duration 属性（monotonic 时长归 execution audit）
    assert not hasattr(facts, "coarse_duration_s")


# ---------------------------------------------------------------------------
# 负例：唯一归属校验（F5 验收面）
# ---------------------------------------------------------------------------


def test_receipt_without_attempt_id_rejected():
    """receipt 自身缺 attempt 锚（schema 允许 None）——派生拒绝。"""

    with pytest.raises(TerminationFactsError, match="physical_attempt_id"):
        derive_termination_facts(
            _receipt(pa=None, outcome=_outcome(),
                     attempt_disposition="aborted", terminal_reason_code="x")
        )


def test_receipt_without_outcome_rejected():
    with pytest.raises(TerminationFactsError, match="outcome_v2"):
        derive_termination_facts(_receipt(outcome=None))


def test_attempt_identity_mismatch_rejected():
    """receipt 与 outcome 的 attempt 身份错接（同题不同 member/retry 的对象
    被错误拼装）必须拒绝。"""

    with pytest.raises(TerminationFactsError, match="不一致"):
        derive_termination_facts(_receipt(outcome=_outcome(pa="exec_1#p2-cafebabe")))


def test_outcome_without_attempt_id_unrepresentable_at_contract_level():
    """RolloutAttemptOutcomeV2 契约本身强制携带 physical_attempt_id（D2 四层
    身份）——"outcome 无 attempt 锚"在上游就不可表示，派生层只需守
    receipt↔outcome 的一致性。"""

    with pytest.raises(Exception, match="physical_attempt_id"):
        _outcome(pa=None)


def test_view_is_read_only():
    """无独立存储、无公开 setter：__slots__ 拒绝新增属性，事实全为派生。"""

    facts = derive_termination_facts(_receipt())
    with pytest.raises(AttributeError):
        facts.fresh_grading_complete = False  # type: ignore[misc]
    with pytest.raises(AttributeError):
        facts.injected = True  # type: ignore[attr-defined]
    assert isinstance(facts, TerminationFactsView)


def test_outcome_property_is_isolated_copy():
    """二轮复核：`outcome` 交出深拷贝——改副本的嵌套 list 不得反向污染 receipt。"""

    receipt = _receipt()
    facts = derive_termination_facts(receipt)
    copy = facts.outcome
    copy.turn_weight_versions.append("999")
    assert receipt.outcome_v2.turn_weight_versions == ["1"]
    assert facts.outcome.turn_weight_versions == ["1"]
    assert facts.outcome_id == "o1"


def test_eligibility_ref_mismatch_rejected():
    """二轮复核：receipt 与 outcome 各自携带的 eligibility 引用必须一致。"""

    with pytest.raises(TerminationFactsError, match="eligibility_report_id"):
        derive_termination_facts(_receipt(eligibility_report_id="er_other"))
    # 快速复核补的反方向：receipt 为 None 而 outcome 有引用，同样是不对称
    with pytest.raises(TerminationFactsError, match="eligibility_report_id"):
        derive_termination_facts(_receipt(eligibility_report_id=None))
    # 双方都为 None 合法（missing 类 / 豁免集合）
    facts = derive_termination_facts(
        _receipt(attempt_disposition="aborted", frozen_patch_digest=None,
                 grading_report_id=None, runtime_quiescence_confirmed=False,
                 eligibility_report_id=None,
                 outcome=_outcome(kind="harness_crash", completion_class="missing",
                                  failure_category="harness_crash",
                                  task_outcome="unknown", reward_unavailable=True,
                                  turn_weight_versions=[],
                                  intra_execution_version_span=None,
                                  current_version_at_finalize=None,
                                  eligibility_report_id=None))
    )
    assert facts.eligibility_report_id is None
    # outcome 无引用（missing 类）而 receipt 声称有 → 同样拒绝
    with pytest.raises(TerminationFactsError, match="eligibility_report_id"):
        derive_termination_facts(
            _receipt(attempt_disposition="aborted", frozen_patch_digest=None,
                     grading_report_id=None, runtime_quiescence_confirmed=False,
                     eligibility_report_id="er_1",
                     outcome=_outcome(kind="harness_crash", completion_class="missing",
                                      failure_category="harness_crash",
                                      task_outcome="unknown", reward_unavailable=True,
                                      turn_weight_versions=[],
                                      intra_execution_version_span=None,
                                      current_version_at_finalize=None,
                                      eligibility_report_id=None))
        )

