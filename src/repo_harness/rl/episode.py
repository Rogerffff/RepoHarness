"""Episode request/result schema for RepoHarness 强化学习接入。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .gateway import GenerationRecord
from .timing import ResourceSummary, TimingSummary
from .training_view import (
    AuditRef,
    TrainingView,
    formal_online_rl_sample_from_training_view,
    validate_formal_online_rl_batch,
    validate_training_view_for_online_rl,
)
from .visibility import (
    CONTRACT_VERSION,
    GatewayRoute,
    InferenceBackend,
    OFFLINE_PROVIDER_ALLOWED_USES,
    PROVIDER_ROUTES,
    default_invalid_for_online_rl,
    validate_inference_backend,
    validate_no_forbidden_model_visible_content,
    validate_opaque_ref,
    validate_safe_identifier,
)

EpisodeStatus = Literal[
    "succeeded",
    "failed",
    "invalid",
    "invalid_task",
    "infrastructure_error",
    "cancelled",
    "timeout",
    "no_progress",
]
RunMode = Literal["full_audit", "training_fast", "training_debug"]


class ProviderRoutePolicy(StrictBaseModel):
    schema_version: str = "repo_harness_verl_provider_route_policy_v0"
    route: GatewayRoute
    invalid_for_online_rl: bool | None = None
    allowed_uses: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_provider_policy(self) -> "ProviderRoutePolicy":
        if self.route in PROVIDER_ROUTES:
            if self.invalid_for_online_rl is None:
                self.invalid_for_online_rl = True
            if self.invalid_for_online_rl is not True:
                raise ValueError("provider routes must default invalid_for_online_rl=true")
            if not self.allowed_uses:
                raise ValueError("provider route policy must document at least one offline allowed use")
            unknown_uses = set(self.allowed_uses) - OFFLINE_PROVIDER_ALLOWED_USES
            if unknown_uses:
                raise ValueError(f"unknown offline provider allowed use: {sorted(unknown_uses)}")
        elif self.invalid_for_online_rl is None:
            self.invalid_for_online_rl = default_invalid_for_online_rl(self.route)
        return self


class EpisodeTaskRef(StrictBaseModel):
    schema_version: str = "repo_harness_verl_episode_task_ref_v0"
    task_ref: str | None = None
    task_id: str | None = None
    task_path: str | None = None
    dataset_name: str | None = None
    dataset_split: str | None = None
    dataset_revision: str | None = None
    repo_ref: str | None = None
    base_commit: str | None = None
    environment_id: str | None = None
    source_archive_ref: str | None = None
    task_freeze_ref: str | None = None
    verifier_plan_ref: str | None = None
    model_visible_summary: str | None = None


class EpisodeVisibilityPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_verl_episode_visibility_policy_v0"
    model_visible_fields: list[str] = Field(default_factory=list)
    trainer_tensor_fields: list[str] = Field(default_factory=list)
    trainer_non_tensor_filter_fields: list[str] = Field(default_factory=list)
    audit_only_fields: list[str] = Field(default_factory=list)
    forbidden_fields: list[str] = Field(default_factory=list)


class EpisodeBudgets(StrictBaseModel):
    schema_version: str = "repo_harness_verl_episode_budgets_v0"
    max_turns: int | None = Field(default=None, gt=0)
    max_wall_seconds: float | None = Field(default=None, gt=0)
    max_model_calls: int | None = Field(default=None, gt=0)
    max_model_call_seconds: float | None = Field(default=None, gt=0)
    request_timeout_seconds: float | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    max_prompt_tokens: int | None = Field(default=None, gt=0)
    max_total_tokens: int | None = Field(default=None, gt=0)
    max_context_tokens: int | None = Field(default=None, gt=0)
    generation_timeout_seconds: float | None = Field(default=None, gt=0)
    max_tool_observation_tokens: int | None = Field(default=None, ge=0)
    max_tool_calls: int | None = Field(default=None, ge=0)
    max_test_runs: int | None = Field(default=None, ge=0)
    max_verifier_seconds: float | None = Field(default=None, gt=0)
    max_workspace_materialization_seconds: float | None = Field(default=None, gt=0)
    provider_retry_budget: int | None = Field(default=None, ge=0)
    reasoning_effort: str | None = None
    thinking_mode: str | None = None
    max_artifact_bytes: int | None = Field(default=None, gt=0)
    no_progress_policy: dict[str, Any] = Field(default_factory=dict)


class RepoHarnessEpisodeRequest(StrictBaseModel):
    schema_version: str = "repo_harness_verl_episode_request_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    episode_id: str
    run_id: str
    task_id: str
    llm_gateway_route: GatewayRoute
    inference_backend: InferenceBackend | None = None
    provider_route_policy_examples: list[ProviderRoutePolicy] = Field(default_factory=list)
    raw_prompt: list[dict[str, Any]] = Field(default_factory=list)
    raw_prompt_source: Literal["external", "episode_execution_spec"] = "external"
    task_ref: EpisodeTaskRef
    episode_execution_spec_ref: str | None = None
    episode_execution_spec_sha256: str | None = None
    task_definition_sha256: str | None = None
    run_config_sha256: str | None = None
    permission_mode: str | None = None
    network_policy: str | None = None
    run_mode_hint: str | None = None
    allowed_tool_names: list[str] = Field(default_factory=list)
    tool_registry_digest: str | None = None
    resolved_verifier_plan_digest: str | None = None
    test_feedback_policy: str | None = None
    feedback_tests_passed_policy: str | None = None
    agent_policy_ref: str | None = None
    budget_ref: str | None = None
    run_config_ref: str | None = None
    episode_seed: int | None = None
    run_mode: RunMode | None = None
    visibility_policy: EpisodeVisibilityPolicy = Field(default_factory=EpisodeVisibilityPolicy)
    budgets: EpisodeBudgets = Field(default_factory=EpisodeBudgets)

    @model_validator(mode="after")
    def validate_episode_request(self) -> "RepoHarnessEpisodeRequest":
        validate_safe_identifier(self.episode_id, field_name="episode_id")
        validate_safe_identifier(self.run_id, field_name="run_id")
        validate_safe_identifier(self.task_id, field_name="task_id")
        validate_inference_backend(self.llm_gateway_route, self.inference_backend)
        validate_no_forbidden_model_visible_content(self.raw_prompt, field_name="raw_prompt")
        if self.episode_execution_spec_ref:
            validate_opaque_ref(self.episode_execution_spec_ref, field_name="episode_execution_spec_ref")
        for policy in self.provider_route_policy_examples:
            if policy.route in PROVIDER_ROUTES and policy.invalid_for_online_rl is not True:
                raise ValueError("provider route examples must be invalid_for_online_rl")
        return self


class BudgetConsumption(StrictBaseModel):
    schema_version: str = "repo_harness_verl_budget_consumption_v0"
    max_turns: int | None = Field(default=None, ge=0)
    used_turns: int | None = Field(default=None, ge=0)
    max_wall_seconds: float | None = Field(default=None, ge=0)
    used_wall_seconds: float | None = Field(default=None, ge=0)
    max_model_calls: int | None = Field(default=None, ge=0)
    used_model_calls: int | None = Field(default=None, ge=0)
    max_model_call_seconds: float | None = Field(default=None, ge=0)
    used_model_call_seconds: float | None = Field(default=None, ge=0)
    max_tool_calls: int | None = Field(default=None, ge=0)
    used_tool_calls: int | None = Field(default=None, ge=0)
    max_artifact_bytes: int | None = Field(default=None, ge=0)
    used_artifact_bytes: int | None = Field(default=None, ge=0)
    stop_reason: str | None = None
    rollout_response_length: int | None = Field(default=None, ge=0)
    actual_response_length: int | None = Field(default=None, ge=0)


class AuditDiagnostic(StrictBaseModel):
    schema_version: str = "repo_harness_verl_audit_diagnostic_v0"
    code: str
    message: str


class RewardSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_reward_summary_v0"
    score: float | None = None
    invalid_for_training: bool = False
    invalid_reason: str | None = None
    reward_metadata_ref: str | None = None

    @model_validator(mode="after")
    def validate_reward_summary(self) -> "RewardSummary":
        if self.invalid_for_training and not self.invalid_reason:
            raise ValueError("invalid reward summary requires invalid_reason")
        if self.reward_metadata_ref:
            validate_opaque_ref(self.reward_metadata_ref, field_name="reward_metadata_ref")
        return self


class VerifierSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_verifier_summary_v0"
    accepted: bool | None = None
    status: str | None = None
    summary_ref: str | None = None

    @model_validator(mode="after")
    def validate_verifier_summary(self) -> "VerifierSummary":
        if self.summary_ref:
            validate_opaque_ref(self.summary_ref, field_name="summary_ref")
        return self


class PatchSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_patch_summary_v0"
    has_patch: bool | None = None
    diff_sha256: str | None = None
    patch_ref: str | None = None

    @model_validator(mode="after")
    def validate_patch_summary(self) -> "PatchSummary":
        if self.patch_ref:
            validate_opaque_ref(self.patch_ref, field_name="patch_ref")
        return self


class RepoHarnessEpisodeResult(StrictBaseModel):
    schema_version: str = "repo_harness_verl_episode_result_v0"
    contract_version: str = CONTRACT_VERSION
    fixture_kind: str | None = None
    episode_id: str
    run_id: str
    task_id: str
    status: EpisodeStatus
    status_reason: str | None = None
    retryable: bool = False
    invalid_for_training: bool = False
    invalid_for_online_rl: bool = False
    attempted_reward_score: float | None = None
    budget_consumption: BudgetConsumption | None = None
    training_view: TrainingView
    audit_ref: AuditRef
    audit_diagnostics: list[AuditDiagnostic] = Field(default_factory=list)
    reward: RewardSummary | None = None
    verifier_summary: VerifierSummary | None = None
    patch_summary: PatchSummary | None = None
    generation_records: list[GenerationRecord] = Field(default_factory=list)
    timing_summary: TimingSummary | None = None
    resource_summary: ResourceSummary | None = None

    @model_validator(mode="after")
    def validate_episode_result(self) -> "RepoHarnessEpisodeResult":
        self._validate_gateway_route_consistency()
        self._validate_generation_record_token_provenance()
        if self.status in {"invalid", "invalid_task", "infrastructure_error"}:
            if not self.invalid_for_training:
                raise ValueError(f"status={self.status} requires invalid_for_training=true")
            if not self.invalid_for_online_rl:
                raise ValueError(f"status={self.status} requires invalid_for_online_rl=true")
        if self.invalid_for_training and not self.status_reason:
            raise ValueError("invalid episode result requires status_reason")
        if self.attempted_reward_score is not None and not self.training_view.response_ids:
            if self.training_view.reward_score is not None or not self.invalid_for_training:
                raise ValueError("empty response with attempted reward must be blocked before training")
        if len(self.training_view.response_ids) > self.training_view.rollout_limits.response_length:
            if not self.invalid_for_training or self.status_reason != "response_length_exceeded":
                raise ValueError("response overflow must be represented as invalid response_length_exceeded")
        if not self.invalid_for_training and not self.invalid_for_online_rl:
            training_view = self._training_view_for_online_rl_validation()
            validate_training_view_for_online_rl(training_view)
            validate_formal_online_rl_batch(
                [
                    formal_online_rl_sample_from_training_view(
                        training_view,
                        generation_records=self.generation_records,
                        sample_id=self.episode_id,
                        invalid_for_training=self.invalid_for_training,
                        invalid_for_online_rl=self.invalid_for_online_rl,
                        invalid_reason=self.status_reason,
                    )
                ]
            )
        return self

    def _training_view_for_online_rl_validation(self) -> TrainingView:
        if "repo_harness_llm_gateway_route" in self.training_view.extra_fields:
            return self.training_view
        if not self.generation_records:
            return self.training_view
        record_routes = {record.gateway_route for record in self.generation_records}
        if record_routes != {"verl"}:
            raise ValueError("generation_records_invalid_for_online_rl")
        return self.training_view.model_copy(
            update={
                "extra_fields": {
                    **self.training_view.extra_fields,
                    "repo_harness_llm_gateway_route": "verl",
                }
            }
        )

    def _validate_gateway_route_consistency(self) -> None:
        training_route = self.training_view.extra_fields.get("repo_harness_llm_gateway_route")
        if training_route is None or not self.generation_records:
            return
        record_routes = {record.gateway_route for record in self.generation_records}
        if training_route == "mixed" and len(record_routes) > 1 and self.invalid_for_online_rl:
            return
        if record_routes != {training_route}:
            raise ValueError("gateway_route_mismatch_between_training_view_and_generation_records")

    def _validate_generation_record_token_provenance(self) -> None:
        if not self.generation_records:
            return
        record_ids = [record.model_call_id for record in self.generation_records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("duplicate_generation_record_model_call_id")
        expected_records = [record for record in self.generation_records if record.output_token_ids]
        assistant_spans = [
            span
            for span in self.training_view.response_spans
            if span.source_type == "assistant_generation"
        ]
        if len(assistant_spans) != len(expected_records):
            raise ValueError("assistant_generation_span_count_mismatch_generation_records")

        assistant_token_sequence: list[int] = []
        expected_token_sequence: list[int] = []
        assistant_logprob_sequence: list[float] = []
        expected_logprob_sequence: list[float] = []
        for span, record in zip(assistant_spans, expected_records):
            if not span.model_call_id:
                raise ValueError("assistant_generation_span_missing_model_call_id")
            if span.model_call_id != record.model_call_id:
                raise ValueError("assistant_generation_span_order_mismatch_generation_records")
            span_ids = self.training_view.response_ids[span.start : span.end]
            if span_ids != record.output_token_ids:
                raise ValueError("assistant_generation_tokens_mismatch_generation_records")
            assistant_token_sequence.extend(span_ids)
            expected_token_sequence.extend(record.output_token_ids)
            if self.training_view.response_logprobs is not None:
                if record.output_logprobs is None:
                    raise ValueError("assistant_generation_logprobs_mismatch_generation_records")
                span_logprobs = self.training_view.response_logprobs[span.start : span.end]
                if span_logprobs != record.output_logprobs:
                    raise ValueError("assistant_generation_logprobs_mismatch_generation_records")
                assistant_logprob_sequence.extend(span_logprobs)
                expected_logprob_sequence.extend(record.output_logprobs)
        if assistant_token_sequence != expected_token_sequence:
            raise ValueError("assistant_generation_token_sequence_mismatch_generation_records")
        if self.training_view.response_logprobs is not None and assistant_logprob_sequence != expected_logprob_sequence:
            raise ValueError("assistant_generation_logprob_sequence_mismatch_generation_records")
