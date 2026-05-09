"""运行指标聚合 helper。"""

from __future__ import annotations

from typing import Any

from repo_harness.evaluation.outcome_policy import OUTCOME_POLICY_VERSION
from repo_harness.trajectory import MetricsRecord
from repo_harness.verifier.schemas import VerifierResult


def build_metrics_record(
    *,
    final_verifier: VerifierResult,
    run_outcome: str,
    final_verifier_status: str | None = None,
    agent_stop_reason: str | None = None,
    timeout: bool | None = None,
    turn_count: int = 0,
    tool_call_count: int = 0,
    test_run_count: int = 0,
    patch_stats: dict[str, Any] | None = None,
    permission_denial_count: int = 0,
    invalid_tool_call_count: int = 0,
    feedback_verifier_accepted: bool = False,
    first_feedback_accept_turn: int | None = None,
    first_feedback_accept_ref: dict[str, Any] | None = None,
    feedback_tests_passed_policy: str | None = None,
    test_feedback_policy: str | None = None,
    hidden_feedback_visible_to_model: bool = False,
    public_tests_ran: bool = False,
    hidden_feedback_ran: bool = False,
    loop_diagnostics_summary: dict[str, Any] | None = None,
    loop_diagnostic_count: int = 0,
) -> MetricsRecord:
    final_status = final_verifier_status or derive_final_verifier_status(final_verifier)
    return MetricsRecord(
        task_success=run_outcome == "success",
        final_verifier_status=final_status,
        run_outcome=run_outcome,  # type: ignore[arg-type]
        turn_count=turn_count,
        tool_call_count=tool_call_count,
        test_run_count=test_run_count,
        timeout=final_verifier.timeout if timeout is None else timeout,
        patch_stats=patch_stats or {},
        permission_denial_count=permission_denial_count,
        invalid_tool_call_count=invalid_tool_call_count,
        interaction_efficiency={
            "agent_stop_reason": agent_stop_reason,
            "outcome_policy_version": OUTCOME_POLICY_VERSION,
            "feedback_verifier_accepted": feedback_verifier_accepted,
            "first_feedback_accept_turn": first_feedback_accept_turn,
            "first_feedback_accept_ref": first_feedback_accept_ref,
            "feedback_tests_passed_policy": feedback_tests_passed_policy,
            "test_feedback_policy": test_feedback_policy,
            "hidden_feedback_visible_to_model": hidden_feedback_visible_to_model,
            "public_tests_ran": public_tests_ran,
            "hidden_feedback_ran": hidden_feedback_ran,
            "loop_diagnostics_summary": loop_diagnostics_summary or {},
            "loop_diagnostic_count": loop_diagnostic_count,
        },
    )


def derive_final_verifier_status(final_verifier: VerifierResult) -> str:
    if final_verifier.accepted:
        return "accepted"
    if final_verifier.timeout:
        return "timeout"
    if final_verifier.parser_confidence < 0.5 or final_verifier.error_type in {
        "low_parser_confidence",
        "test_command_error",
        "dependency_error",
        "patch_apply_failed",
        "verification_workspace_error",
        "budget_exhausted_empty_patch",
        "harness_context_integrity_empty_patch",
        "provider_or_model_error_empty_patch",
        "output_token_limit_empty_patch",
        "tool_call_parse_failure_unrecovered",
        "empty_final_patch",
        "task_timeout_before_final_verifier",
        "selector_input_invalid",
        "model_patch_apply_failed",
        "hidden_test_patch_conflict_after_candidate_patch",
        "hidden_test_patch_apply_failed_on_clean_source",
    }:
        return "error"
    return "failed"


def derive_run_outcome(final_verifier_status: str) -> str:
    """兼容早期调用方的 final-verifier-only outcome helper。"""

    if final_verifier_status == "accepted":
        return "success"
    if final_verifier_status == "failed":
        return "failed"
    if final_verifier_status in {"timeout", "error"}:
        return "inconclusive"
    return "inconclusive"
