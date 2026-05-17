"""Stage 12.5 valid sample refill / resample helpers."""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.rl import (
    FormalOnlineRLSample,
    RepoHarnessEpisodeResult,
    TrainingView,
    validate_formal_online_rl_batch,
)
from repo_harness.schema_base import StrictBaseModel

from .conversion import project_generation_records_route

SampleClass = Literal[
    "valid_trainable_sample",
    "valid_verifier_rejected_negative_sample",
    "infrastructure_failure",
    "invalid_task",
    "model_format_failure",
    "verifier_rejected",
    "timeout",
    "context_or_length_invalid",
    "missing_logprobs",
    "mixed_route",
    "visibility_rejected",
]


class Stage125RefillPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_refill_policy_v0"
    target_valid_sample_count: int = Field(gt=0)
    max_attempts: int = Field(gt=0)
    max_wall_seconds: float | None = Field(default=None, gt=0.0)
    allow_same_task_retry: bool = True
    deduplicate_task_ids: bool = False


class Stage125SampleClassification(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_sample_classification_v0"
    sample_id: str
    task_id: str | None = None
    status: str | None = None
    sample_class: SampleClass
    reason: str | None = None
    formal_online_rl_valid: bool = False


class Stage125BatchRefillReport(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_batch_refill_report_v0"
    target_valid_sample_count: int
    attempts_used: int = Field(ge=0)
    valid_sample_count: int = Field(ge=0)
    invalid_sample_count: int = Field(ge=0)
    insufficient_valid_batch: bool = False
    insufficient_reason: str | None = None
    classifications: list[Stage125SampleClassification] = Field(default_factory=list)
    valid_sample_ids: list[str] = Field(default_factory=list)
    elapsed_seconds: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_counts(self) -> "Stage125BatchRefillReport":
        if self.valid_sample_count != len(self.valid_sample_ids):
            raise ValueError("valid_sample_count must match valid_sample_ids length")
        if self.valid_sample_count + self.invalid_sample_count != len(self.classifications):
            raise ValueError("sample counts must match classifications length")
        return self


def classify_episode_result_for_refill(
    result: RepoHarnessEpisodeResult | dict[str, Any],
) -> Stage125SampleClassification:
    parsed = (
        result if isinstance(result, RepoHarnessEpisodeResult) else RepoHarnessEpisodeResult.model_validate(result)
    )
    sample_id = parsed.episode_id
    task_id = parsed.task_id
    if parsed.invalid_for_training or parsed.invalid_for_online_rl:
        return _classification(
            parsed,
            _invalid_class_from_reason(parsed.status_reason),
            parsed.status_reason or "episode_marked_invalid_for_training_or_online_rl",
        )
    if parsed.status == "infrastructure_error":
        return _classification(parsed, "infrastructure_failure", parsed.status_reason)
    if parsed.status == "invalid_task":
        return _classification(parsed, "invalid_task", parsed.status_reason)
    if parsed.status == "timeout":
        return _classification(parsed, "timeout", parsed.status_reason)
    if parsed.training_view.response_logprobs is None:
        return _classification(parsed, "missing_logprobs", "missing_response_logprobs")
    if parsed.status_reason in {"context_too_large", "prompt_length_exceeded", "response_length_exceeded"}:
        return _classification(parsed, "context_or_length_invalid", parsed.status_reason)
    try:
        project_generation_records_route(parsed.generation_records)
        validate_formal_online_rl_batch(
            [_formal_sample_from_episode_result(parsed)],
            formal_online_rl_batch=True,
        )
    except ValueError as exc:
        reason = str(exc)
        if "route" in reason:
            sample_class: SampleClass = "mixed_route"
        elif "visibility" in reason or "forbidden" in reason:
            sample_class = "visibility_rejected"
        elif "logprobs" in reason:
            sample_class = "missing_logprobs"
        elif "length" in reason or "empty_response" in reason:
            sample_class = "context_or_length_invalid"
        else:
            sample_class = "model_format_failure"
        return _classification(parsed, sample_class, reason)
    if parsed.status == "failed":
        if not _is_trusted_verifier_rejected_negative(parsed):
            return _classification(
                parsed,
                "verifier_rejected",
                "untrusted_or_inconsistent_final_verifier_rejected",
            )
        sample_class: SampleClass = "valid_verifier_rejected_negative_sample"
    else:
        sample_class = "valid_trainable_sample"
    return Stage125SampleClassification(
        sample_id=sample_id,
        task_id=task_id,
        status=parsed.status,
        sample_class=sample_class,
        reason="trusted_final_verifier_rejected_negative_sample" if parsed.status == "failed" else None,
        formal_online_rl_valid=True,
    )


def build_refill_report(
    candidates: Sequence[RepoHarnessEpisodeResult | dict[str, Any]],
    *,
    policy: Stage125RefillPolicy,
    started_at: float | None = None,
) -> Stage125BatchRefillReport:
    start = time.perf_counter() if started_at is None else started_at
    classifications: list[Stage125SampleClassification] = []
    valid_ids: list[str] = []
    seen_tasks: set[str] = set()
    attempts = 0
    insufficient_reason = None
    for candidate in candidates:
        if attempts >= policy.max_attempts:
            insufficient_reason = "max_attempts_exhausted"
            break
        if policy.max_wall_seconds is not None and time.perf_counter() - start > policy.max_wall_seconds:
            insufficient_reason = "max_wall_seconds_exhausted"
            break
        attempts += 1
        classification = classify_episode_result_for_refill(candidate)
        if (
            policy.deduplicate_task_ids
            and classification.task_id is not None
            and classification.task_id in seen_tasks
        ):
            classification = classification.model_copy(
                update={
                    "sample_class": "model_format_failure",
                    "reason": "duplicate_task_filtered",
                    "formal_online_rl_valid": False,
                }
            )
        if classification.task_id is not None:
            seen_tasks.add(classification.task_id)
        classifications.append(classification)
        if classification.formal_online_rl_valid:
            valid_ids.append(classification.sample_id)
            if len(valid_ids) >= policy.target_valid_sample_count:
                break
    if len(valid_ids) < policy.target_valid_sample_count and insufficient_reason is None:
        insufficient_reason = "candidate_pool_exhausted"
    return Stage125BatchRefillReport(
        target_valid_sample_count=policy.target_valid_sample_count,
        attempts_used=attempts,
        valid_sample_count=len(valid_ids),
        invalid_sample_count=len(classifications) - len(valid_ids),
        insufficient_valid_batch=len(valid_ids) < policy.target_valid_sample_count,
        insufficient_reason=insufficient_reason if len(valid_ids) < policy.target_valid_sample_count else None,
        classifications=classifications,
        valid_sample_ids=valid_ids,
        elapsed_seconds=max(0.0, time.perf_counter() - start),
    )


def select_valid_training_views(
    candidates: Iterable[RepoHarnessEpisodeResult | dict[str, Any]],
    *,
    policy: Stage125RefillPolicy,
) -> tuple[list[TrainingView], Stage125BatchRefillReport]:
    materialized = list(candidates)
    report = build_refill_report(materialized, policy=policy)
    views: list[TrainingView] = []
    for candidate, classification in zip(materialized, report.classifications):
        if not classification.formal_online_rl_valid:
            continue
        parsed = (
            candidate
            if isinstance(candidate, RepoHarnessEpisodeResult)
            else RepoHarnessEpisodeResult.model_validate(candidate)
        )
        views.append(parsed.training_view)
    return views[: policy.target_valid_sample_count], report


def _classification(
    parsed: RepoHarnessEpisodeResult,
    sample_class: SampleClass,
    reason: str | None,
) -> Stage125SampleClassification:
    return Stage125SampleClassification(
        sample_id=parsed.episode_id,
        task_id=parsed.task_id,
        status=parsed.status,
        sample_class=sample_class,
        reason=reason,
        formal_online_rl_valid=False,
    )


def _formal_sample_from_episode_result(parsed: RepoHarnessEpisodeResult) -> FormalOnlineRLSample:
    view = parsed.training_view
    return FormalOnlineRLSample(
        sample_id=parsed.episode_id,
        route=str(view.extra_fields.get("repo_harness_llm_gateway_route") or "verl"),
        invalid_for_training=parsed.invalid_for_training
        or view.extra_fields.get("repo_harness_invalid_for_training") is True,
        invalid_for_online_rl=parsed.invalid_for_online_rl
        or view.extra_fields.get("repo_harness_invalid_for_online_rl") is True,
        invalid_reason=str(view.extra_fields.get("repo_harness_invalid_reason") or parsed.status_reason or "")
        or None,
        prompt_ids=view.prompt_ids,
        response_ids=view.response_ids,
        response_mask=view.response_mask,
        response_logprobs=view.response_logprobs,
        response_spans=view.response_spans,
        generation_records=parsed.generation_records,
        reward_score=view.reward_score,
    )


def _invalid_class_from_reason(reason: str | None) -> SampleClass:
    if reason in {"missing_response_logprobs", "assistant_generation_logprobs_mismatch_generation_records"}:
        return "missing_logprobs"
    if reason in {"context_too_large", "prompt_length_exceeded", "response_length_exceeded"}:
        return "context_or_length_invalid"
    if reason and "route" in reason:
        return "mixed_route"
    if reason and "timeout" in reason:
        return "timeout"
    if reason and "verifier" in reason:
        return "verifier_rejected"
    return "model_format_failure"


def _is_trusted_verifier_rejected_negative(parsed: RepoHarnessEpisodeResult) -> bool:
    summary = parsed.verifier_summary
    if summary is None:
        return False
    if summary.accepted is not False:
        return False
    if summary.status != "rejected":
        return False
    return parsed.status_reason in {None, "final_verifier_rejected", "verifier_rejected"}
