"""TrainingView、AuditRef 和正式 online RL batch 校验。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .visibility import (
    CONTRACT_VERSION,
    FlatScalar,
    GatewayRoute,
    validate_batch_extra_fields,
    validate_no_absolute_local_path,
    validate_opaque_ref,
)

IncludedSpanType = Literal["assistant_generation", "tool_observation", "environment_observation"]
ExcludedSpanType = Literal["padding_excluded", "truncated_excluded"]
ResponseSpanType = IncludedSpanType | ExcludedSpanType


class RolloutLimits(StrictBaseModel):
    schema_version: str = "repo_harness_verl_rollout_limits_v0"
    prompt_length: int = Field(gt=0)
    response_length: int = Field(gt=0)


def _unbounded_rollout_limits() -> RolloutLimits:
    return RolloutLimits(prompt_length=10**9, response_length=10**9)


class ResponseSpan(StrictBaseModel):
    schema_version: str = "repo_harness_verl_response_span_v0"
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    source_type: ResponseSpanType
    model_call_id: str | None = None
    tool_call_id: str | None = None
    artifact_ref: str
    response_mask_value: Literal[0, 1] | None
    logprob_policy: str
    policy_version: dict[str, Any] = Field(default_factory=dict)
    global_steps: int = Field(ge=0)
    min_global_steps: int = Field(ge=0)
    max_global_steps: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_span(self) -> "ResponseSpan":
        if self.start > self.end:
            raise ValueError("response span start must be <= end")
        if not (self.min_global_steps <= self.global_steps <= self.max_global_steps):
            raise ValueError("response span global_steps must be within min/max bounds")
        validate_opaque_ref(self.artifact_ref, field_name="artifact_ref")

        if self.source_type == "assistant_generation":
            if self.response_mask_value != 1:
                raise ValueError("assistant_generation span requires response_mask_value=1")
            if self.start == self.end:
                raise ValueError("assistant_generation span must cover at least one token")
        elif self.source_type in {"tool_observation", "environment_observation"}:
            if self.response_mask_value != 0:
                raise ValueError(f"{self.source_type} span requires response_mask_value=0")
            if self.start == self.end:
                raise ValueError(f"{self.source_type} span must cover at least one token")
        else:
            if self.start != self.end:
                raise ValueError(f"{self.source_type} span must be a zero-width explanatory span")
            if self.response_mask_value is not None:
                raise ValueError(f"{self.source_type} span must not set response_mask_value")
        return self


class TrainingView(StrictBaseModel):
    schema_version: str = "repo_harness_verl_training_view_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    online_rl_eligible: bool | None = None
    rollout_limits: RolloutLimits = Field(default_factory=_unbounded_rollout_limits)
    prompt_ids: list[int]
    response_ids: list[int]
    response_mask: list[Literal[0, 1]]
    response_logprobs: list[float] | None
    response_spans: list[ResponseSpan] = Field(default_factory=list)
    reward_score: float | None
    num_turns: int | None = Field(default=None, ge=0)
    verl_metrics: dict[str, int | float] = Field(default_factory=dict)
    repo_harness_metrics_ref: str | None = None
    extra_fields: dict[str, FlatScalar] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_training_view(self) -> "TrainingView":
        if len(self.prompt_ids) > self.rollout_limits.prompt_length:
            raise ValueError("prompt_ids exceeds rollout prompt_length")
        if len(self.response_ids) != len(self.response_mask):
            raise ValueError("response_ids and response_mask must have equal length")
        if self.response_logprobs is not None and len(self.response_logprobs) != len(self.response_ids):
            raise ValueError("response_logprobs must align with response_ids")
        if self.response_logprobs is not None:
            for mask, logprob in zip(self.response_mask, self.response_logprobs):
                if mask == 0 and logprob != 0.0:
                    raise ValueError("response_mask=0 tokens must use response_logprobs=0.0")
        if not self.response_ids and self.reward_score is not None:
            raise ValueError("empty response_ids cannot carry a normal reward_score")
        if self.repo_harness_metrics_ref is not None:
            validate_opaque_ref(self.repo_harness_metrics_ref, field_name="repo_harness_metrics_ref")

        validate_batch_extra_fields(self.extra_fields)
        self._validate_response_spans()
        return self

    def _validate_response_spans(self) -> None:
        covered: set[int] = set()
        for span in self.response_spans:
            if span.end > len(self.response_ids):
                raise ValueError("response span exceeds response_ids length")
            if span.source_type in {"padding_excluded", "truncated_excluded"}:
                continue
            expected_mask = 1 if span.source_type == "assistant_generation" else 0
            for index in range(span.start, span.end):
                if index in covered:
                    raise ValueError("response_spans must not overlap")
                covered.add(index)
                if self.response_mask[index] != expected_mask:
                    raise ValueError("response span mask provenance does not match response_mask")
        if covered != set(range(len(self.response_ids))):
            raise ValueError("response_spans must explain every response token")


class AuditRef(StrictBaseModel):
    schema_version: str = "repo_harness_verl_audit_ref_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    run_id: str
    episode_id: str
    task_id: str
    run_dir: str
    transcript_path: str | None = None
    events_path: str | None = None
    artifacts_manifest_path: str | None = None
    run_status_path: str | None = None
    run_summary_path: str | None = None
    run_metadata_path: str | None = None
    reward_metadata_path: str | None = None
    final_verifier_path: str | None = None
    patch_path: str | None = None
    timing_summary_path: str | None = None
    resource_summary_path: str | None = None
    trajectory_store_facts_path: str | None = None
    export_audit_path: str | None = None
    important_artifact_refs: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_audit_ref(self) -> "AuditRef":
        for field_name in [
            "run_dir",
            "transcript_path",
            "events_path",
            "artifacts_manifest_path",
            "run_status_path",
            "run_summary_path",
            "run_metadata_path",
            "reward_metadata_path",
            "final_verifier_path",
            "patch_path",
            "timing_summary_path",
            "resource_summary_path",
            "trajectory_store_facts_path",
            "export_audit_path",
        ]:
            value = getattr(self, field_name)
            if value is not None:
                validate_no_absolute_local_path(value, field_name=field_name)
        for key, value in self.important_artifact_refs.items():
            validate_opaque_ref(value, field_name=f"important_artifact_refs.{key}")
        return self


class FormalOnlineRLSample(StrictBaseModel):
    schema_version: str = "repo_harness_verl_formal_online_rl_sample_v0"
    sample_id: str | None = None
    route: GatewayRoute
    invalid_for_training: bool = False
    invalid_reason: str | None = None
    prompt_ids: list[int]
    response_ids: list[int]
    response_mask: list[Literal[0, 1]]
    response_logprobs: list[float] | None
    reward_score: float | None

    @model_validator(mode="after")
    def validate_sample_shape(self) -> "FormalOnlineRLSample":
        if len(self.response_ids) != len(self.response_mask):
            raise ValueError("response_ids and response_mask must have equal length")
        if self.response_logprobs is not None and len(self.response_logprobs) != len(self.response_ids):
            raise ValueError("response_logprobs must align with response_ids")
        if self.response_logprobs is not None:
            for mask, logprob in zip(self.response_mask, self.response_logprobs):
                if mask == 0 and logprob != 0.0:
                    raise ValueError("response_mask=0 tokens must use response_logprobs=0.0")
        return self


class MixedLogprobBatchRejectionFixture(StrictBaseModel):
    schema_version: str = "repo_harness_verl_batch_rejection_fixture_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    batch_id: str
    training_algorithm: Literal["ppo", "grpo"]
    formal_online_rl_batch: bool
    expected_status: Literal["rejected"]
    expected_rejection_reason: str
    samples: list[FormalOnlineRLSample]


def validate_training_view_for_online_rl(view: TrainingView | dict[str, Any]) -> TrainingView:
    parsed = view if isinstance(view, TrainingView) else TrainingView.model_validate(view)
    if not parsed.response_ids:
        raise ValueError("empty_response_with_reward_blocked")
    if len(parsed.response_ids) > parsed.rollout_limits.response_length:
        raise ValueError("response_length_exceeded")
    if parsed.response_logprobs is None:
        raise ValueError("missing_response_logprobs_in_formal_batch")
    route = parsed.extra_fields.get("repo_harness_llm_gateway_route")
    if route is None:
        raise ValueError("missing_llm_gateway_route_for_online_rl")
    if route != "verl":
        raise ValueError("non_verl_route_invalid_for_online_rl")
    if parsed.reward_score is None:
        raise ValueError("missing_reward_score")
    if parsed.online_rl_eligible is False:
        raise ValueError("training_view_marked_ineligible_for_online_rl")
    if parsed.extra_fields.get("repo_harness_invalid_for_training") is True:
        raise ValueError(str(parsed.extra_fields.get("repo_harness_invalid_reason") or "invalid_for_training"))
    if parsed.extra_fields.get("repo_harness_invalid_for_online_rl") is True:
        raise ValueError("invalid_for_online_rl")
    return parsed


def validate_formal_online_rl_batch(
    samples: list[FormalOnlineRLSample | TrainingView | dict[str, Any]],
    *,
    formal_online_rl_batch: bool = True,
) -> list[FormalOnlineRLSample]:
    parsed: list[FormalOnlineRLSample] = []
    for index, sample in enumerate(samples):
        if isinstance(sample, FormalOnlineRLSample):
            parsed.append(sample)
        elif isinstance(sample, TrainingView):
            route = sample.extra_fields.get("repo_harness_llm_gateway_route")
            if formal_online_rl_batch and route is None:
                raise ValueError("missing_llm_gateway_route_for_online_rl")
            parsed.append(
                FormalOnlineRLSample(
                    sample_id=str(sample.extra_fields.get("repo_harness_episode_id") or index),
                    route=str(route or "verl"),
                    invalid_for_training=sample.extra_fields.get("repo_harness_invalid_for_training") is True,
                    invalid_reason=sample.extra_fields.get("repo_harness_invalid_reason"),
                    prompt_ids=sample.prompt_ids,
                    response_ids=sample.response_ids,
                    response_mask=sample.response_mask,
                    response_logprobs=sample.response_logprobs,
                    reward_score=sample.reward_score,
                )
            )
        else:
            parsed.append(FormalOnlineRLSample.model_validate(sample))

    if not formal_online_rl_batch:
        return parsed

    missing_logprobs = [sample for sample in parsed if sample.response_logprobs is None]
    present_logprobs = [sample for sample in parsed if sample.response_logprobs is not None]
    if missing_logprobs:
        if present_logprobs:
            raise ValueError("mixed_response_logprobs_in_formal_batch")
        raise ValueError("missing_response_logprobs_in_formal_batch")

    if any(sample.route != "verl" for sample in parsed):
        raise ValueError("non_verl_route_invalid_for_online_rl")
    if any(sample.invalid_for_training for sample in parsed):
        raise ValueError("invalid_for_training_sample_in_formal_batch")
    if any(not sample.response_ids for sample in parsed):
        raise ValueError("empty_response_with_reward_blocked")
    if any(sample.reward_score is None for sample in parsed):
        raise ValueError("missing_reward_score")
    return parsed
