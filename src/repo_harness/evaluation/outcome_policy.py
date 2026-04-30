"""Run outcome 派生策略。"""

from __future__ import annotations

from repo_harness.schema_versions import OUTCOME_POLICY_VERSION


def derive_run_outcome(
    *,
    baseline_status: str | None = None,
    final_verifier_status: str | None = None,
    agent_stop_reason: str | None = None,
    final_verifier_ran: bool = True,
) -> str:
    """按照第一版策略从质量门控和 final verifier 状态派生 run_outcome。"""

    if baseline_status == "invalid":
        return "invalid_task"
    if baseline_status == "flaky":
        return "flaky_task"
    if agent_stop_reason == "manual_stop" and not final_verifier_ran:
        return "interrupted"
    if final_verifier_status == "accepted":
        return "success"
    if final_verifier_status == "failed":
        return "failed"
    if final_verifier_status in {"timeout", "error"}:
        return "inconclusive"
    return "inconclusive"


__all__ = ["OUTCOME_POLICY_VERSION", "derive_run_outcome"]
