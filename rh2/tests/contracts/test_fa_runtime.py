"""FA-0 契约测试：三层身份 / RolloutAttemptOutcome / 协调器协议 / 调用账目。

验收对应（05 计划 FA-0）：validator fail-closed 逐条 + 三层身份在真实 P3
事件元数据夹具上的完整往返（j4_formal 的 44→31→19 与 group5×8branch 反例）。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from repoharness2.contracts.fa_runtime import (
    ExecutionIdentity,
    ModelCallAttempt,
    RolloutAttemptOutcome,
    TrainingRuntimeWindow,
)
from repoharness2.contracts.trajectory import RoutingTensorRef

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _identity(**overrides) -> ExecutionIdentity:
    payload = dict(prompt_group_id="pg_5", group_index=5, rollout_execution_id="exec_22")
    payload.update(overrides)
    return ExecutionIdentity(**payload)


def _outcome(**overrides) -> RolloutAttemptOutcome:
    payload = dict(
        outcome_id="o1",
        identity=_identity(),
        member_slot=2,
        attempt_number=1,
        completion_class="present",
        task_outcome="unresolved",
        recovery_scope="none",
        turn_weight_versions=["1", "1", "3"],
        intra_execution_version_span=2,
        current_version_at_finalize="3",
        eligibility_report_id="er_1",
    )
    payload.update(overrides)
    return RolloutAttemptOutcome(**payload)


# ------------------------------------------------------------- Outcome 校验器


def test_present_negative_sample_is_member_not_missing():
    """可信 reward=0 负样本 = present + unresolved（讨论稿 §2.1 的 schema 落点）。"""

    outcome = _outcome()
    assert outcome.completion_class == "present"
    assert outcome.task_outcome == "unresolved"


def test_present_requires_eligibility_reference():
    with pytest.raises(ValidationError, match="eligibility_report_id"):
        _outcome(eligibility_report_id=None)


def test_present_rejects_unknown_outcome_and_failure_category():
    with pytest.raises(ValidationError, match="unknown"):
        _outcome(task_outcome="unknown")
    with pytest.raises(ValidationError, match="failure_category"):
        _outcome(failure_category="harness_crash")


def test_present_requires_turn_versions():
    with pytest.raises(ValidationError, match="weight_version"):
        _outcome(turn_weight_versions=[], intra_execution_version_span=None)


def test_missing_member_requires_unknown_outcome_and_category():
    outcome = _outcome(
        completion_class="missing_after_local_retry",
        task_outcome="unknown",
        failure_category="harness_crash",
        eligibility_report_id=None,
        turn_weight_versions=["1"],
        intra_execution_version_span=0,
        current_version_at_finalize=None,
    )
    assert outcome.completion_class == "missing_after_local_retry"
    with pytest.raises(ValidationError, match="unknown"):
        _outcome(completion_class="missing_after_local_retry", failure_category="harness_crash")
    with pytest.raises(ValidationError, match="failure_category"):
        _outcome(
            completion_class="missing_after_local_retry",
            task_outcome="unknown",
            eligibility_report_id=None,
        )


def test_version_span_is_cross_checked():
    with pytest.raises(ValidationError, match="intra_execution_version_span"):
        _outcome(intra_execution_version_span=1)  # 真实跨度 2


def test_consume_time_facts_forbidden_at_finalize():
    """current_version_at_consume / worst_token_lag 是 FA-3 消费时刻事实。"""

    with pytest.raises(ValidationError, match="消费时刻"):
        _outcome(current_version_at_consume="4")
    with pytest.raises(ValidationError, match="消费时刻"):
        _outcome(worst_token_lag=1)


# ------------------------------------------------------- 协调器窗口协议校验器


def _window(**overrides) -> TrainingRuntimeWindow:
    payload = dict(
        update_epoch=3,
        phase="ACTIVE",
        old_version="2",
        target_version="3",
        active_version="3",
        window_started_at=NOW,
        window_completed_at=NOW + timedelta(seconds=12),
        fencing_token="fence_3",
    )
    payload.update(overrides)
    return TrainingRuntimeWindow(**payload)


def test_window_active_requires_completion_and_version_advance():
    assert _window().phase == "ACTIVE"
    with pytest.raises(ValidationError, match="window_completed_at"):
        _window(window_completed_at=None)
    with pytest.raises(ValidationError, match="active_version"):
        _window(active_version="2")


def test_window_in_progress_forbids_completion_timestamp():
    window = _window(phase="UPDATING", window_completed_at=None, active_version="2")
    assert window.phase == "UPDATING"
    with pytest.raises(ValidationError, match="进行中"):
        _window(phase="PAUSING", active_version="2")


def test_window_completion_not_before_start():
    with pytest.raises(ValidationError, match="早于"):
        _window(window_completed_at=NOW - timedelta(seconds=1))


def test_window_requires_version_advance():
    """codex FA-0 审查：old == target 的"无前进窗口"是事实矛盾，任何 phase 都拒绝。"""

    with pytest.raises(ValidationError, match="版本前进"):
        _window(old_version="3", target_version="3")
    with pytest.raises(ValidationError, match="版本前进"):
        _window(phase="UPDATING", window_completed_at=None,
                old_version="3", target_version="3", active_version="3")


def test_delivered_attempt_requires_weight_version():
    """codex FA-0 审查：delivered 即 provenance 事实，weight_version 必填。"""

    with pytest.raises(ValidationError, match="weight_version"):
        ModelCallAttempt(
            logical_turn_id="turn_7",
            model_call_attempt_id="a1",
            attempt_number=1,
            delivery_status="delivered",
            capture_record_ref="cap_7",
        )


# --------------------------------------------------------- 调用账目校验器


def test_model_call_attempt_delivery_consistency():
    delivered = ModelCallAttempt(
        logical_turn_id="turn_7",
        model_call_attempt_id="a2",
        attempt_number=2,
        delivery_status="delivered",
        capture_record_ref="cap_7",
        weight_version="3",
    )
    assert delivered.delivery_status == "delivered"
    with pytest.raises(ValidationError, match="capture"):
        ModelCallAttempt(
            logical_turn_id="turn_7",
            model_call_attempt_id="a1",
            attempt_number=1,
            delivery_status="delivered",
        )
    with pytest.raises(ValidationError, match="审计物"):
        ModelCallAttempt(
            logical_turn_id="turn_7",
            model_call_attempt_id="a1",
            attempt_number=1,
            delivery_status="non_delivered_aborted",
            capture_record_ref="cap_7",
            abort_update_epoch=3,
        )
    with pytest.raises(ValidationError, match="update_epoch"):
        ModelCallAttempt(
            logical_turn_id="turn_7",
            model_call_attempt_id="a1",
            attempt_number=1,
            delivery_status="non_delivered_aborted",
        )


def test_proxy_regeneration_ledger_shape():
    """D-FA-3 形状：同 logical_turn 的 abort attempt_1 + delivered attempt_2。"""

    a1 = ModelCallAttempt(
        logical_turn_id="turn_7",
        model_call_attempt_id="a1",
        attempt_number=1,
        delivery_status="non_delivered_aborted",
        abort_update_epoch=3,
        abort_fencing_token="fence_3",
        weight_version="2",
        evidence_refs=["partial_output_audit_ref"],
    )
    a2 = ModelCallAttempt(
        logical_turn_id="turn_7",
        model_call_attempt_id="a2",
        attempt_number=2,
        delivery_status="delivered",
        capture_record_ref="cap_7",
        weight_version="3",
    )
    assert a1.logical_turn_id == a2.logical_turn_id
    assert a1.capture_record_ref is None  # 半截输出绝不回链训练面
    assert a2.weight_version == "3"  # 重生成轮 provenance 落在新版本


# --------------------------------------------------------- start_len 扩展位


def test_routing_start_len_slot_fail_closed():
    """FA-0 第 8 条：字段在场、默认 0；非 0（中段拼接未实现）fail-closed。"""

    ref = RoutingTensorRef(alignment="not_applicable_dense_model")
    assert ref.routed_experts_start_len == 0
    with pytest.raises(ValidationError, match="routed_experts_start_len"):
        RoutingTensorRef(alignment="not_applicable_dense_model", routed_experts_start_len=1)


# ----------------------------------------------- 三层身份 × P3 真实事件夹具


_P3_EVENTS = (
    Path(__file__).resolve().parents[3]
    / "docs/agentic_RL/repo_harness_rh2_workstreams/preflight/remote_evidence_20260708"
    / "bringup_selected/j4_formal_20260708T160749Z"
)


def _load_j4_events() -> list[dict]:
    if not _P3_EVENTS.exists():
        pytest.skip("P3 evidence 不在本地（浅 checkout），夹具往返跳过")
    files = sorted(_P3_EVENTS.rglob("bringup_events.jsonl"))
    if not files:
        pytest.skip("j4_formal bringup_events.jsonl 缺失")
    return [json.loads(line) for line in files[0].read_text().splitlines() if line.strip()]


def test_three_layer_identity_round_trip_on_real_p3_metadata():
    """FA-0 验收：三层身份在 J4 formal 真实元数据上完整往返。

    同时把 A 类失败的三个关键计数（44 returned / 31 kept / 19 有效 rollout）
    与 group5×8branch 反例钉进回归——这正是"branch 不是 execution、更不是
    GRPO 采样"的物证。
    """

    events = _load_j4_events()
    assert len(events) == 32  # 名义 8 题 × n4

    returned_total = 0
    kept_total = 0
    valid_rollouts = 0
    identities: list[ExecutionIdentity] = []
    for event in events:
        returned = int(event.get("returned_samples") or 0)
        removes = list(event.get("remove_sample") or [])
        kept = sum(1 for flag in removes if flag is False)
        returned_total += returned
        kept_total += kept
        if kept > 0:
            valid_rollouts += 1
        group_index = int(event["group_index"])
        exec_index = int(event["index"])
        for branch_pos in range(returned):
            identities.append(
                ExecutionIdentity(
                    prompt_group_id=f"pg_{group_index}",
                    group_index=group_index,
                    rollout_execution_id=f"exec_{exec_index}",
                    branch_id=f"exec_{exec_index}_b{branch_pos}",
                )
            )

    # A 类失败的真实形状（formal J4：num_rollouts 19 < global_batch_size 32）
    assert returned_total == 44
    assert kept_total == 31
    assert valid_rollouts == 19

    # 反例：group_index=5 / index=22 一次执行 fan-out 8 个 branch
    g5 = [i for i in identities if i.group_index == 5 and i.rollout_execution_id == "exec_22"]
    assert len(g5) == 8
    assert len({i.rollout_execution_id for i in g5}) == 1  # 8 branch 只算 1 次执行

    # 往返：dump -> validate 逐字段一致；branch 计数永远 >= execution 计数
    for identity in identities:
        restored = ExecutionIdentity.model_validate(identity.model_dump(mode="json"))
        assert restored == identity
    executions = {i.rollout_execution_id for i in identities}
    assert len(identities) == returned_total
    assert len(executions) == len(events)  # execution 按事件计，不随 branch 膨胀
