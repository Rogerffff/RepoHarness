"""Verifier-aligned reward metadata 计算。"""

from __future__ import annotations

from typing import Any

from repo_harness.reward.schemas import RewardMetadata
from repo_harness.schema_versions import REWARD_VERSION
from repo_harness.verifier.schemas import VerifierResult


def compute_reward_metadata(
    final_verifier: VerifierResult,
    *,
    patch_stats: dict[str, Any] | None = None,
    event_counts: dict[str, int] | None = None,
) -> RewardMetadata:
    patch_stats = patch_stats or {}
    event_counts = event_counts or {}
    fail_total = final_verifier.fail_to_pass.get("total", 0)
    pass_total = final_verifier.pass_to_pass.get("total", 0)
    if fail_total > 0:
        fail_score = final_verifier.fail_to_pass.get("passed", 0) / fail_total
        fail_component_available = True
    else:
        fail_score = 0.0
        fail_component_available = False
    pass_score = (
        final_verifier.pass_to_pass.get("passed", 0) / pass_total if pass_total > 0 else 1.0
    )
    accepted_bonus = 1.0 if final_verifier.accepted else 0.0
    added = int(patch_stats.get("added_lines", 0) or 0)
    removed = int(patch_stats.get("removed_lines", 0) or 0)
    patch_size_penalty = min((added + removed) / 500.0, 0.2)
    timeout_penalty = 0.3 if final_verifier.timeout else 0.0
    regression_penalty = 0.4 if final_verifier.error_type == "regression_detected" else 0.0
    cost_penalty = 0.0

    if fail_component_available:
        formula = (
            "0.7 * fail_to_pass_score + 0.2 * pass_to_pass_score + 0.1 * accepted_bonus "
            "- cost_penalty - patch_size_penalty - regression_penalty - timeout_penalty"
        )
        raw_reward = (
            0.7 * fail_score
            + 0.2 * pass_score
            + 0.1 * accepted_bonus
            - cost_penalty
            - patch_size_penalty
            - regression_penalty
            - timeout_penalty
        )
    else:
        formula = (
            "0.6 * accepted_bonus + 0.4 * pass_to_pass_score "
            "- cost_penalty - patch_size_penalty - regression_penalty - timeout_penalty"
        )
        raw_reward = (
            0.6 * accepted_bonus
            + 0.4 * pass_score
            - cost_penalty
            - patch_size_penalty
            - regression_penalty
            - timeout_penalty
        )
    final_reward = max(0.0, min(1.0, raw_reward))
    invalid_for_training = bool(
        final_verifier.timeout
        or final_verifier.error_type in {"low_parser_confidence", "patch_apply_failed"}
        or final_verifier.parser_confidence < 0.5
    )
    invalid_reason = None
    if invalid_for_training:
        invalid_reason = final_verifier.error_type or "inconclusive_final_verifier"

    return RewardMetadata(
        reward_version=REWARD_VERSION,
        final_reward=round(final_reward, 6),
        formula=formula,
        components={
            "fail_to_pass_score": fail_score,
            "pass_to_pass_score": pass_score,
            "accepted_bonus": accepted_bonus,
            "cost_penalty": cost_penalty,
            "patch_size_penalty": patch_size_penalty,
            "regression_penalty": regression_penalty,
            "timeout_penalty": timeout_penalty,
        },
        sources={
            "turn_count": event_counts.get("turn_count", 0),
            "tool_call_count": event_counts.get("tool_call_count", 0),
            "test_run_count": event_counts.get("test_run_count", 0),
            "patch_added_lines": added,
            "patch_removed_lines": removed,
        },
        invalid_for_training=invalid_for_training,
        invalid_reason=invalid_reason,
        acceptance_policy_version=final_verifier.acceptance_policy_version,
    )
