"""TrainingView、AuditRef 和正式 online RL batch 校验。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .gateway import GenerationRecord
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
    invalid_for_online_rl: bool = False
    invalid_reason: str | None = None
    prompt_ids: list[int]
    response_ids: list[int]
    response_mask: list[Literal[0, 1]]
    response_logprobs: list[float] | None
    response_spans: list[ResponseSpan] = Field(default_factory=list)
    generation_records: list[GenerationRecord] = Field(default_factory=list)
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
        _validate_response_span_coverage(
            response_ids=self.response_ids,
            response_mask=self.response_mask,
            response_spans=self.response_spans,
        )
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


def validate_training_view_for_online_rl(
    view: TrainingView | dict[str, Any],
    *,
    require_explicit_eligibility: bool = False,
) -> TrainingView:
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
    if require_explicit_eligibility and parsed.online_rl_eligible is not True:
        raise ValueError("training_view_missing_online_rl_eligibility")
    if parsed.extra_fields.get("repo_harness_invalid_for_training") is True:
        raise ValueError(str(parsed.extra_fields.get("repo_harness_invalid_reason") or "invalid_for_training"))
    if parsed.extra_fields.get("repo_harness_invalid_for_online_rl") is True:
        raise ValueError("invalid_for_online_rl")
    return parsed


def formal_online_rl_sample_from_training_view(
    view: TrainingView | dict[str, Any],
    *,
    generation_records: list[GenerationRecord | dict[str, Any]] | None = None,
    sample_id: str | None = None,
    invalid_for_training: bool = False,
    invalid_for_online_rl: bool = False,
    invalid_reason: str | None = None,
) -> FormalOnlineRLSample:
    """从 TrainingView 和 generation_records 构造正式 online RL 样本。

    TrainingView 本身只描述 batch 可见 token、mask、logprob 和投影字段。
    正式 online RL 样本还必须携带 runtime-only generation_records，
    这样后续 validator 才能证明 assistant token 不是从最终文本重新分词伪造出来的。
    """

    parsed_view = view if isinstance(view, TrainingView) else TrainingView.model_validate(view)
    records = [
        record if isinstance(record, GenerationRecord) else GenerationRecord.model_validate(record)
        for record in (generation_records or [])
    ]
    route = parsed_view.extra_fields.get("repo_harness_llm_gateway_route")
    if route is None and records:
        record_routes = {record.gateway_route for record in records}
        if record_routes != {"verl"}:
            raise ValueError("generation_records_route_must_all_be_verl")
        route = "verl"
    return FormalOnlineRLSample(
        sample_id=sample_id,
        route=str(route or "verl"),
        invalid_for_training=invalid_for_training,
        invalid_for_online_rl=invalid_for_online_rl,
        invalid_reason=invalid_reason,
        prompt_ids=parsed_view.prompt_ids,
        response_ids=parsed_view.response_ids,
        response_mask=parsed_view.response_mask,
        response_logprobs=parsed_view.response_logprobs,
        response_spans=parsed_view.response_spans,
        generation_records=records,
        reward_score=parsed_view.reward_score,
    )


def validate_formal_sample_token_provenance(sample: FormalOnlineRLSample) -> None:
    """校验 formal online RL sample 的 assistant token 来源可追溯到 generation_records。"""

    if not sample.generation_records:
        raise ValueError("missing_generation_records_for_formal_online_rl_sample")
    if not sample.response_spans:
        raise ValueError("missing_response_spans_for_formal_online_rl_sample")
    routes = {record.gateway_route for record in sample.generation_records}
    if routes != {"verl"}:
        raise ValueError("generation_records_route_must_all_be_verl")
    _validate_generation_record_token_provenance(
        response_ids=sample.response_ids,
        response_logprobs=sample.response_logprobs,
        response_spans=sample.response_spans,
        generation_records=sample.generation_records,
    )


def validate_formal_online_rl_batch(
    samples: list[FormalOnlineRLSample | TrainingView | dict[str, Any]],
    *,
    formal_online_rl_batch: bool = True,
) -> list[FormalOnlineRLSample]:
    parsed: list[FormalOnlineRLSample] = []
    for index, sample in enumerate(samples):
        if isinstance(sample, FormalOnlineRLSample):
            parsed.append(FormalOnlineRLSample.model_validate(sample.model_dump(mode="python")))
        elif isinstance(sample, TrainingView):
            if formal_online_rl_batch:
                validate_training_view_for_online_rl(sample, require_explicit_eligibility=True)
            route = sample.extra_fields.get("repo_harness_llm_gateway_route")
            if formal_online_rl_batch and route is None:
                raise ValueError("missing_llm_gateway_route_for_online_rl")
            parsed.append(
                formal_online_rl_sample_from_training_view(
                    sample,
                    sample_id=str(sample.extra_fields.get("repo_harness_episode_id") or index),
                    invalid_for_training=sample.extra_fields.get("repo_harness_invalid_for_training") is True,
                    invalid_for_online_rl=sample.extra_fields.get("repo_harness_invalid_for_online_rl") is True,
                    invalid_reason=sample.extra_fields.get("repo_harness_invalid_reason"),
                )
            )
        else:
            if isinstance(sample, dict) and ("online_rl_eligible" in sample or "extra_fields" in sample):
                view = TrainingView.model_validate(sample)
                if formal_online_rl_batch:
                    validate_training_view_for_online_rl(view, require_explicit_eligibility=True)
                route = view.extra_fields.get("repo_harness_llm_gateway_route")
                parsed.append(
                    formal_online_rl_sample_from_training_view(
                        view,
                        sample_id=str(view.extra_fields.get("repo_harness_episode_id") or index),
                        invalid_for_training=view.extra_fields.get("repo_harness_invalid_for_training") is True,
                        invalid_for_online_rl=view.extra_fields.get("repo_harness_invalid_for_online_rl") is True,
                        invalid_reason=view.extra_fields.get("repo_harness_invalid_reason"),
                    )
                )
                continue
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
    if any(sample.invalid_for_online_rl for sample in parsed):
        raise ValueError("invalid_for_online_rl_sample_in_formal_batch")
    if any(not sample.response_ids for sample in parsed):
        raise ValueError("empty_response_with_reward_blocked")
    if any(sample.reward_score is None for sample in parsed):
        raise ValueError("missing_reward_score")
    for sample in parsed:
        validate_formal_sample_token_provenance(sample)
    return parsed


def _validate_response_span_coverage(
    *,
    response_ids: list[int],
    response_mask: list[Literal[0, 1]],
    response_spans: list[ResponseSpan],
) -> None:
    if not response_spans:
        return
    covered: set[int] = set()
    for span in response_spans:
        if span.end > len(response_ids):
            raise ValueError("response span exceeds response_ids length")
        if span.source_type in {"padding_excluded", "truncated_excluded"}:
            continue
        expected_mask = 1 if span.source_type == "assistant_generation" else 0
        for index in range(span.start, span.end):
            if index in covered:
                raise ValueError("response_spans must not overlap")
            covered.add(index)
            if response_mask[index] != expected_mask:
                raise ValueError("response span mask provenance does not match response_mask")
    if covered != set(range(len(response_ids))):
        raise ValueError("response_spans must explain every response token")


def _validate_generation_record_token_provenance(
    *,
    response_ids: list[int],
    response_logprobs: list[float] | None,
    response_spans: list[ResponseSpan],
    generation_records: list[GenerationRecord],
) -> None:
    record_ids = [record.model_call_id for record in generation_records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("duplicate_generation_record_model_call_id")
    expected_records = [record for record in generation_records if record.output_token_ids]
    assistant_spans = [span for span in response_spans if span.source_type == "assistant_generation"]
    if response_ids and not expected_records:
        raise ValueError("missing_assistant_generation_records_for_response_tokens")
    if len(assistant_spans) != len(expected_records):
        raise ValueError("assistant_generation_span_count_mismatch_generation_records")
    for span, record in zip(assistant_spans, expected_records):
        if not span.model_call_id:
            raise ValueError("assistant_generation_span_missing_model_call_id")
        if span.model_call_id != record.model_call_id:
            raise ValueError("assistant_generation_span_order_mismatch_generation_records")
        if response_ids[span.start : span.end] != record.output_token_ids:
            raise ValueError("assistant_generation_tokens_mismatch_generation_records")
        if response_logprobs is not None:
            if record.output_logprobs is None:
                raise ValueError("assistant_generation_logprobs_mismatch_generation_records")
            if response_logprobs[span.start : span.end] != record.output_logprobs:
                raise ValueError("assistant_generation_logprobs_mismatch_generation_records")
