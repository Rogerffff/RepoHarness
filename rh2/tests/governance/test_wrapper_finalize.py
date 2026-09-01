"""finalize_rollout（唯一关口）的行为测试：顺序、A3 无封顶、接线校验、确定性。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from contract_samples import (
    valid_backend_handshake,
    valid_capture_record,
    valid_grading_report,
    valid_trajectory_projection,
)
from governance_samples import (
    FIXED_CREATED_AT,
    FIXED_REPORT_ID,
    backpressure_event,
    executed_finding_payload,
    run_finalize,
)

from repoharness2.contracts import (
    BackendHandshake,
    GenerationCaptureRecord,
    GradingReport,
    TrajectoryProjection,
    compute_facts_digest,
)
from repoharness2.governance import (
    GATE_VERSION,
    GateInputError,
    finalize_rollout,
)


def _default_captures() -> list[GenerationCaptureRecord]:
    return [GenerationCaptureRecord.model_validate(valid_capture_record())]


def _default_handshake() -> BackendHandshake:
    return BackendHandshake.model_validate(valid_backend_handshake())


async def test_happy_path_all_dimensions_ok_is_online():
    """七维全过（含正向 sandbox 能力事实在场）的完美样本：A3 起无封顶 → online、零理由码。"""

    final = await run_finalize()
    report = final.eligibility_report

    assert report.facts.all_ok()
    assert report.eligibility_class == "online_policy_loss_eligible"
    assert report.reason_codes == []
    # 自证字段：digest 重算一致、派生视图互检字段已填好
    assert report.facts_digest == compute_facts_digest(report.facts)
    assert report.derived_view_report_ref == report.report_id == FIXED_REPORT_ID
    assert report.derived_view_class == report.eligibility_class
    assert report.gate_version == GATE_VERSION
    # 扫描留痕：干净也要在 security 维 evidence 里可见（区分"扫过且干净"与"没扫"）
    assert final.scan_result.clean
    assert (
        "public_projection_scan:clean:rh2.trajectory_projection.v1"
        in report.facts.security_and_leakage.evidence_refs
    )
    # staleness 维 evidence 回链 handshake
    assert "hs_0001" in report.facts.policy_staleness.evidence_refs


async def test_group_repair_signal_first_class_on_happy_path():
    """组修复信号一等暴露：全过样本 degraded=False，组账目可用。"""

    final = await run_finalize()
    signal = final.group_repair_signal
    assert signal.degraded is False
    assert signal.failed_dimensions == []
    assert signal.group_id == "group_task42"
    assert signal.parent_rollout_id == "rollout_7"
    assert signal.report_ref == final.eligibility_report.report_id
    assert signal.eligibility_class == final.eligibility_report.eligibility_class


def test_s1_tier_cap_deleted_and_gate_version_bumped():
    """A3（D1 已批）：S1_TIER_CAP / ceiling reason code / cap 分支整体删除；GATE_VERSION 机械升版
    （被动版本号，不是解锁）。"""

    import repoharness2.governance as governance
    from repoharness2.governance import gate

    assert not hasattr(gate, "S1_TIER_CAP") and not hasattr(gate, "S1_CEILING_REASON_CODE")
    assert not hasattr(governance, "S1_TIER_CAP") and not hasattr(governance, "S1_CEILING_REASON_CODE")
    assert "s1_default_ceiling_offline" not in gate.__dict__.values()
    assert GATE_VERSION == "rh2.gate.w1b.v2"


async def test_wrapper_fixes_call_order_grade_then_project():
    """grade -> project 顺序固化：project 收到的必须是本次 grade 的产物（同一对象）。"""

    calls: list[str] = []
    grading_obj = GradingReport.model_validate(valid_grading_report())
    projection_obj = TrajectoryProjection.model_validate(valid_trajectory_projection())

    def grade():
        calls.append("grade")
        return grading_obj

    def project(report):
        calls.append("project")
        assert report is grading_obj  # 不是副本、不是别的轨迹的报告
        return projection_obj

    final = await finalize_rollout(
        grade=grade,
        project=project,
        capture_records=_default_captures(),
        handshake=_default_handshake(),
        report_id=FIXED_REPORT_ID,
        created_at_utc=FIXED_CREATED_AT,
    )
    assert calls == ["grade", "project"]
    assert final.grading_report is grading_obj
    assert final.projection is projection_obj


async def test_async_grade_and_project_callables_supported():
    """评分队列（GradingQueue.submit）是 async 的：grade/project 允许为协程函数。"""

    grading_obj = GradingReport.model_validate(valid_grading_report())
    projection_obj = TrajectoryProjection.model_validate(valid_trajectory_projection())

    async def grade():
        return grading_obj

    async def project(report):
        assert report is grading_obj
        return projection_obj

    final = await finalize_rollout(
        grade=grade,
        project=project,
        capture_records=_default_captures(),
        handshake=_default_handshake(),
        report_id=FIXED_REPORT_ID,
        created_at_utc=FIXED_CREATED_AT,
    )
    assert final.eligibility_report.eligibility_class == "audit_only_or_rejected"  # 未传能力事实 → security 失败


async def test_grade_callable_returning_wrong_type_rejected():
    """回调返回错误类型 fail-closed：不进入后续步骤。"""

    with pytest.raises(GateInputError, match="GradingReport"):
        await finalize_rollout(
            grade=lambda: {"not": "a_report"},  # type: ignore[arg-type]
            project=lambda report: None,  # type: ignore[arg-type]
            capture_records=_default_captures(),
            handshake=_default_handshake(),
        )


async def test_mismatched_grading_trajectory_raises_input_error():
    """接线错误（别的轨迹的评分报告）不是降级而是当场炸——掩盖 bug 比降级更危险。"""

    grading = valid_grading_report()
    grading["trajectory_id"] = "traj_9999"
    with pytest.raises(GateInputError, match="traj_9999"):
        await run_finalize(grading=grading)


async def test_duplicate_capture_record_ids_raise_input_error():
    """捕获记录 id 重复 = 证据索引歧义，拒绝判定。"""

    with pytest.raises(GateInputError, match="重复"):
        await run_finalize(captures=[valid_capture_record(), valid_capture_record()])


async def test_foreign_finding_raises_input_error():
    """别的轨迹的 finding 不是本样本的事实，接进来即编排 bug。"""

    finding = executed_finding_payload()
    finding["trajectory_id"] = "traj_9999"
    with pytest.raises(GateInputError, match="finding_exec_0001"):
        await run_finalize(findings=[finding])


async def test_missing_handshake_fails_staleness_dimension():
    """handshake 显式传 None：staleness 事实缺失 -> fail-closed 降级。"""

    final = await run_finalize(handshake=None)
    fact = final.eligibility_report.facts.policy_staleness
    assert not fact.ok
    assert fact.reason_codes == ["staleness_facts_missing"]
    assert final.eligibility_report.eligibility_class == "offline_or_sft_candidate"
    assert final.group_repair_signal.degraded is True
    assert final.group_repair_signal.failed_dimensions == ["policy_staleness"]


async def test_backpressure_events_recorded_but_not_degrading():
    """反压事件：理由码进报告、事件 id 进 clean_grading evidence，不构成降级；
    其他轨迹的事件被过滤（全局观测流，不算接线错误）。"""

    own = backpressure_event(event_id="bp_0001")
    foreign = backpressure_event(event_id="bp_foreign", trajectory_id="traj_other")
    final = await run_finalize(backpressure=[own, foreign])
    report = final.eligibility_report

    assert report.reason_codes == ["grading_backpressure_queue_full"]  # 只有观测理由码，无封顶
    assert report.facts.all_ok()  # 不降级
    assert report.eligibility_class == "online_policy_loss_eligible"
    assert final.group_repair_signal.degraded is False
    assert "bp_0001" in report.facts.clean_grading.evidence_refs
    assert "bp_foreign" not in report.facts.clean_grading.evidence_refs


async def test_finalize_is_deterministic_given_fixed_id_and_time():
    """同输入 + 固定 report_id/时间戳 -> 两次 finalize 逐字节一致（evidence 可复现）。"""

    first = await run_finalize()
    second = await run_finalize()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


async def test_default_report_id_and_timestamp_generated():
    """不传 report_id/created_at 时自动生成（id 形如 elig_xxxxxxxxxxxx、时间带时区）。"""

    final = await finalize_rollout(
        grade=lambda: GradingReport.model_validate(valid_grading_report()),
        project=lambda report: TrajectoryProjection.model_validate(
            valid_trajectory_projection()
        ),
        capture_records=_default_captures(),
        handshake=_default_handshake(),
    )
    assert final.eligibility_report.report_id.startswith("elig_")
    assert final.eligibility_report.created_at_utc.tzinfo is not None
    assert final.eligibility_report.created_at_utc <= datetime.now(timezone.utc)
