"""运行指标聚合 helper。"""

from __future__ import annotations

from typing import Any

from repo_harness.trajectory import MetricsRecord
from repo_harness.verifier.schemas import VerifierResult


def build_metrics_record(
    *,
    final_verifier: VerifierResult,
    run_outcome: str,
    agent_stop_reason: str | None = None,
    turn_count: int = 0,
    tool_call_count: int = 0,
    test_run_count: int = 0,
    patch_stats: dict[str, Any] | None = None,
    permission_denial_count: int = 0,
    invalid_tool_call_count: int = 0,
) -> MetricsRecord:
    final_status = "accepted" if final_verifier.accepted else "failed"
    if final_verifier.timeout:
        final_status = "timeout"
    elif final_verifier.error_type == "low_parser_confidence":
        final_status = "error"
    return MetricsRecord(
        task_success=run_outcome == "success",
        final_verifier_status=final_status,
        run_outcome=run_outcome,  # type: ignore[arg-type]
        turn_count=turn_count,
        tool_call_count=tool_call_count,
        test_run_count=test_run_count,
        timeout=final_verifier.timeout,
        patch_stats=patch_stats or {},
        permission_denial_count=permission_denial_count,
        invalid_tool_call_count=invalid_tool_call_count,
        interaction_efficiency={"agent_stop_reason": agent_stop_reason},
    )
