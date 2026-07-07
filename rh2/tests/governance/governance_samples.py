"""S1-5 governance 测试的共享样例与执行助手。

原则与 contract_samples 相同：工厂返回全新 dict，测试在副本上做局部
破坏构造非法/降级形态。`run_finalize` 是唯一执行入口的测试包装——
所有测试都走 `finalize_rollout`（生产路径），不直接触碰 gate 私有函数。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from contract_samples import (
    valid_backend_handshake,
    valid_capture_record,
    valid_grading_report,
    valid_infra_grading_report,
    valid_trajectory_projection,
)

from repoharness2.contracts import (
    AntiCheatFinding,
    BackendHandshake,
    GenerationCaptureRecord,
    GradingReport,
    TrajectoryProjection,
)
from repoharness2.governance import FinalizedRollout, finalize_rollout
from repoharness2.grading.queue import BackpressureEvent

# 固定 id 与时间戳：同输入两次 finalize 的报告可逐字节比对（确定性测试用）。
FIXED_REPORT_ID = "elig_test_0001"
FIXED_CREATED_AT = datetime(2026, 7, 7, 9, 30, 25, tzinfo=timezone.utc)


def infra_grading_payload() -> dict[str, Any]:
    """infra_failure 评分报告，改挂到 traj_0001（与投影样例同轨迹）。"""

    payload = valid_infra_grading_report()
    payload["trajectory_id"] = "traj_0001"
    return payload


def infra_reward_facts() -> dict[str, Any]:
    """infra 样本的诚实 reward 事实：scope=none、raw_reward=None（P4 红线形态）。"""

    return {
        "reward_scope": "none",
        "raw_reward": None,
        "components": {},
        "reward_event_refs": ["rpt_grading_0002"],
        "credit_assignment_strategy": "direct_trace_reward",
        "group_id": "group_task42",
        "parent_rollout_id": "rollout_7",
        "segment_index": 0,
        "segment_count": 1,
        "rollout_loss_denominator": 16,
    }


def executed_finding_payload() -> dict[str, Any]:
    """executed 级反作弊 finding（评分期 post_hoc_scan 检出的测试篡改）。"""

    return {
        "schema_id": "rh2.anti_cheat_finding.v1",
        "finding_id": "finding_exec_0001",
        "trajectory_id": "traj_0001",
        "category": "test_tampering",
        "phase": "grading",
        "enforcement": "executed",
        "detection_layer": "post_hoc_scan",
        "evidence_refs": ["diff_evidence_0001"],
        "description": "final patch rewrote tests/test_validators.py assertions",
        "detected_at_utc": "2026-07-07T09:30:25Z",
    }


def tampered_hygiene_grading_payload() -> dict[str, Any]:
    """S1-4 hygiene 封顶后的真实形态：篡改段剥离重放，f2p 全过也只给 tests_failed。"""

    payload = valid_grading_report()
    payload["outcome"] = "unresolved"
    payload["failure_category"] = "tests_failed"
    payload["reward"] = 0.0
    payload["patch_hygiene"] = {
        "cleaned_patch_digest": "sha256:" + "d" * 64,
        "replayed_on_clean_checkout": True,
        "test_files_modified": True,
        "forbidden_path_touched": False,
        "forbidden_paths": [],
        "verdict": "rejected_test_tampering",
    }
    return payload


def backpressure_event(
    *, event_id: str = "bp_0001", trajectory_id: str = "traj_0001"
) -> BackpressureEvent:
    return BackpressureEvent.model_validate(
        {
            "event_id": event_id,
            "trajectory_id": trajectory_id,
            "task_id": "django__django-11099",
            "queue_capacity": 8,
            "queue_depth": 8,
            "active_grading_count": 4,
            "concurrency_limit": 4,
            "occurred_at_utc": "2026-07-07T09:30:25Z",
        }
    )


_DEFAULT = object()  # handshake 参数的哨兵：区分"用默认样例"与"显式传 None"


async def run_finalize(
    *,
    projection: dict[str, Any] | TrajectoryProjection | None = None,
    grading: dict[str, Any] | GradingReport | None = None,
    captures: Sequence[Any] | None = None,
    findings: Sequence[Any] = (),
    handshake: Any = _DEFAULT,
    backpressure: Sequence[BackpressureEvent] = (),
    report_id: str = FIXED_REPORT_ID,
    created_at: datetime = FIXED_CREATED_AT,
) -> FinalizedRollout:
    """以生产入口 finalize_rollout 执行一次完整 finalize（测试唯一执行路径）。"""

    projection_obj = _as(TrajectoryProjection, projection, valid_trajectory_projection)
    grading_obj = _as(GradingReport, grading, valid_grading_report)
    if captures is None:
        captures = [valid_capture_record()]
    capture_objs = [_as(GenerationCaptureRecord, item, None) for item in captures]
    finding_objs = [_as(AntiCheatFinding, item, None) for item in findings]
    if handshake is _DEFAULT:
        handshake_obj = BackendHandshake.model_validate(valid_backend_handshake())
    elif handshake is None:
        handshake_obj = None
    else:
        handshake_obj = _as(BackendHandshake, handshake, None)
    return await finalize_rollout(
        grade=lambda: grading_obj,
        project=lambda report: projection_obj,
        capture_records=capture_objs,
        handshake=handshake_obj,
        findings=finding_objs,
        backpressure_events=list(backpressure),
        report_id=report_id,
        created_at_utc=created_at,
    )


def _as(model_cls: type, value: Any, default_factory: Any) -> Any:
    if value is None and default_factory is not None:
        value = default_factory()
    if isinstance(value, model_cls):
        return value
    return model_cls.model_validate(value)
