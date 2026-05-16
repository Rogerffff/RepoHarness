"""Stage 7 verifier-to-reward boundary helpers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from repo_harness.reward import RewardMetadata, compute_reward_metadata
from repo_harness.schema_base import StrictBaseModel
from repo_harness.verifier import VerifierJobResult, VerifierResult

from .episode import EpisodeStatus, RewardSummary, VerifierSummary
from .visibility import FlatScalar

INVALID_TASK_VERIFIER_ERRORS = {"test_command_error"}
INFRASTRUCTURE_VERIFIER_ERRORS = {
    "dependency_error",
    "verification_workspace_error",
    "docker_error",
    "container_error",
    "pool_executor_error",
    "final_verifier_environment_error",
    "low_parser_confidence",
    "patch_apply_failed",
}
TIMEOUT_VERIFIER_ERRORS = {
    "queue_timeout",
    "execution_timeout",
    "test_timeout",
    "task_timeout_before_final_verifier",
}
LOW_CONFIDENCE_THRESHOLD = 0.5


class Stage7RewardBoundaryResult(StrictBaseModel):
    schema_version: str = "repo_harness_stage7_reward_boundary_result_v0"
    status: EpisodeStatus
    status_reason: str | None = None
    invalid_for_training: bool = False
    invalid_for_online_rl: bool = False
    reward_score: float | None = None
    reward_metadata: RewardMetadata | None = None
    reward_summary: RewardSummary
    verifier_summary: VerifierSummary
    verifier_pool_id: str | None = None
    verifier_worker_id: str | None = None
    verifier_queue_wait_seconds: float = Field(default=0.0, ge=0.0)
    final_verifier_seconds: float = Field(default=0.0, ge=0.0)
    reward_compute_seconds: float = Field(default=0.0, ge=0.0)
    extra_fields: dict[str, FlatScalar] = Field(default_factory=dict)


def build_stage7_reward_boundary(
    *,
    final_verifier: VerifierResult | None,
    pool_result: VerifierJobResult | None = None,
    reward_metadata_ref: str,
    final_verifier_ref: str,
    patch_stats: dict[str, Any] | None = None,
    event_counts: dict[str, int] | None = None,
    source_refs: dict[str, Any] | None = None,
    reward_compute_seconds: float = 0.0,
) -> Stage7RewardBoundaryResult:
    verifier = final_verifier or (None if pool_result is None else pool_result.verifier_result)
    status, status_reason = map_stage7_verifier_status(verifier, pool_result=pool_result)
    invalid_for_training = status in {
        "invalid",
        "invalid_task",
        "infrastructure_error",
        "cancelled",
        "timeout",
        "no_progress",
    }
    reward_metadata = None
    if verifier is not None:
        reward_metadata = compute_reward_metadata(
            verifier,
            patch_stats=patch_stats,
            event_counts=event_counts,
            source_refs=source_refs,
        )
        if invalid_for_training and not reward_metadata.invalid_for_training:
            reward_metadata = reward_metadata.model_copy(
                update={
                    "final_reward": 0.0,
                    "invalid_for_training": True,
                    "invalid_reason": status_reason or "invalid_verifier_boundary",
                }
            )
        elif not invalid_for_training and reward_metadata.invalid_for_training:
            diagnostic_reward = reward_metadata.components.get(
                "diagnostic_reward_before_invalid_clip",
                reward_metadata.final_reward,
            )
            reward_metadata = reward_metadata.model_copy(
                update={
                    "final_reward": max(0.0, min(1.0, diagnostic_reward)),
                    "invalid_for_training": False,
                    "invalid_reason": None,
                    "sources": {
                        **reward_metadata.sources,
                        "stage7_invalid_authority": "reward_boundary",
                        "legacy_reward_invalid_reason": reward_metadata.invalid_reason,
                    },
                }
            )

    reward_score = None
    if reward_metadata is not None and not invalid_for_training:
        reward_score = reward_metadata.final_reward

    reward_summary = RewardSummary(
        score=reward_score,
        invalid_for_training=invalid_for_training,
        invalid_reason=status_reason if invalid_for_training else None,
        reward_metadata_ref=reward_metadata_ref if reward_metadata is not None else None,
    )
    verifier_summary = _verifier_summary(
        verifier,
        pool_result=pool_result,
        status=status,
        status_reason=status_reason,
        final_verifier_ref=final_verifier_ref,
    )
    extra_fields: dict[str, FlatScalar] = {
        "repo_harness_final_verifier_ref": final_verifier_ref,
    }
    if reward_metadata is not None:
        extra_fields["repo_harness_reward_metadata_ref"] = reward_metadata_ref
    if pool_result is not None:
        extra_fields["repo_harness_verifier_worker_pool_id"] = pool_result.pool_id
        if pool_result.worker_id is not None:
            extra_fields["repo_harness_verifier_worker_id"] = pool_result.worker_id
        extra_fields["repo_harness_verifier_queue_wait_seconds"] = round(
            pool_result.queue_wait_seconds,
            6,
        )
    return Stage7RewardBoundaryResult(
        status=status,
        status_reason=status_reason,
        invalid_for_training=invalid_for_training,
        invalid_for_online_rl=invalid_for_training,
        reward_score=reward_score,
        reward_metadata=reward_metadata,
        reward_summary=reward_summary,
        verifier_summary=verifier_summary,
        verifier_pool_id=None if pool_result is None else pool_result.pool_id,
        verifier_worker_id=None if pool_result is None else pool_result.worker_id,
        verifier_queue_wait_seconds=0.0 if pool_result is None else pool_result.queue_wait_seconds,
        final_verifier_seconds=0.0 if pool_result is None else pool_result.execution_seconds,
        reward_compute_seconds=reward_compute_seconds,
        extra_fields=extra_fields,
    )


def map_stage7_verifier_status(
    final_verifier: VerifierResult | None,
    *,
    pool_result: VerifierJobResult | None = None,
) -> tuple[EpisodeStatus, str | None]:
    if pool_result is not None and pool_result.error_type:
        return _status_from_error_type(pool_result.error_type, timeout=pool_result.timeout)
    if final_verifier is None:
        return "infrastructure_error", "missing_final_verifier_result"
    if final_verifier.timeout:
        return "timeout", final_verifier.error_type or "test_timeout"
    if final_verifier.parser_confidence < LOW_CONFIDENCE_THRESHOLD:
        return "infrastructure_error", final_verifier.error_type or "low_parser_confidence"
    if final_verifier.error_type:
        status, reason = _status_from_error_type(final_verifier.error_type, timeout=final_verifier.timeout)
        if status in {"invalid_task", "infrastructure_error", "timeout"}:
            return status, reason
    if final_verifier.accepted:
        return "succeeded", None
    return "failed", final_verifier.error_type or "final_verifier_rejected"


def _status_from_error_type(
    error_type: str,
    *,
    timeout: bool = False,
) -> tuple[EpisodeStatus, str]:
    if timeout or _is_timeout_error(error_type):
        return "timeout", error_type
    if error_type in INVALID_TASK_VERIFIER_ERRORS:
        return "invalid_task", error_type
    if error_type in INFRASTRUCTURE_VERIFIER_ERRORS:
        return "infrastructure_error", error_type
    return "failed", error_type


def _is_timeout_error(error_type: str) -> bool:
    normalized = error_type.lower()
    return error_type in TIMEOUT_VERIFIER_ERRORS or "timeout" in normalized or "timed_out" in normalized


def _verifier_summary(
    final_verifier: VerifierResult | None,
    *,
    pool_result: VerifierJobResult | None,
    status: EpisodeStatus,
    status_reason: str | None,
    final_verifier_ref: str,
) -> VerifierSummary:
    if final_verifier is not None:
        if final_verifier.accepted:
            summary_status = "accepted"
        elif final_verifier.timeout:
            summary_status = "timeout"
        elif status in {"invalid_task", "infrastructure_error"}:
            summary_status = "error"
        else:
            summary_status = "rejected"
        return VerifierSummary(
            accepted=final_verifier.accepted,
            status=summary_status,
            summary_ref=final_verifier_ref,
        )
    if pool_result is not None:
        return VerifierSummary(
            accepted=False,
            status=status_reason or pool_result.error_type or "error",
            summary_ref=final_verifier_ref,
        )
    return VerifierSummary(accepted=False, status="missing", summary_ref=final_verifier_ref)
