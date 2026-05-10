"""Context Builder 和 Context Manager schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    CONTEXT_BUILDER_VERSION,
    CONTEXT_COMPACTION_FACTS_SCHEMA_VERSION,
    CONTEXT_POLICY_VERSION,
    PROMPT_TEMPLATE_VERSION,
    TOKEN_ESTIMATOR_VERSION,
)
from repo_harness.trajectory import ArtifactRef, TrajectoryEvent


class ContextBuilderConfig(StrictBaseModel):
    schema_version: str = "repo_harness_context_builder_config_v0"
    context_builder_version: str = CONTEXT_BUILDER_VERSION
    prompt_template_version: str = PROMPT_TEMPLATE_VERSION
    visible_context_policy: str = "repo_harness_visible_context_v0"
    hidden_metadata_policy: str = "exclude_evaluator_only_v0"


class ContentReplacementRecord(StrictBaseModel):
    schema_version: str = "repo_harness_content_replacement_record_v0"
    tool_call_id: str
    original_tool_result_id: str
    replacement_decision: Literal[
        "prepared_candidate",
        "provider_committed_full_visible",
        "provider_committed_persisted_preview",
        "microcompact_cleared",
    ] = "prepared_candidate"
    replaced: bool
    first_visible_form: Literal["full", "preview", "replacement"]
    first_visible_content_hash: str
    replacement_allowed_after_first_seen: bool
    replacement_text_hash: str | None = None
    replacement_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    replacement_preview_hash: str | None = None
    first_replaced_at_context_revision: int | None = Field(default=None, ge=0)
    first_seen_at_context_revision: int = Field(ge=0)


class ContentReplacementState(StrictBaseModel):
    schema_version: str = "repo_harness_content_replacement_state_v0"
    context_policy_version: str = CONTEXT_POLICY_VERSION
    seen_tool_result_ids: list[str] = Field(default_factory=list)
    records: list[ContentReplacementRecord] = Field(default_factory=list)
    state_hash: str
    last_context_revision: int = Field(ge=0)


class ToolResultCompactRecord(StrictBaseModel):
    schema_version: str = "repo_harness_tool_result_compact_record_v1"
    tool_call_id: str
    tool_result_id: str
    tool_name: str | None = None
    replacement_decision: Literal[
        "prepared_candidate",
        "provider_committed_full_visible",
        "provider_committed_persisted_preview",
        "microcompact_cleared",
    ]
    candidate_prepared_messages_ref: ArtifactRef | None = None
    provider_request_materialized_ref: ArtifactRef | None = None
    provider_request_materialized_projection_hash: str | None = None
    model_input_accepted_ref: ArtifactRef | None = None
    original_content_hash: str
    model_visible_content_hash: str
    replacement_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    first_seen_at_context_revision: int = Field(ge=0)


class ToolResultArtifactRecord(StrictBaseModel):
    schema_version: str = "repo_harness_tool_result_artifact_record_v1"
    artifact_id: str
    tool_result_id: str
    tool_call_id: str
    tool_name: str | None = None
    content_sha256: str
    size_chars: int = Field(ge=0)
    artifact_ref: ArtifactRef
    publishable_after_visibility_scan: bool = False
    recovery_unlocked_after_provider_commit: bool = False
    model_visible_recoverable: bool = False
    contamination_scan_status: Literal["clean", "failed", "not_scanned"] = "not_scanned"
    recovery_denial_reason: str | None = None

    @model_validator(mode="after")
    def derive_recoverable_flag(self) -> "ToolResultArtifactRecord":
        if self.publishable_after_visibility_scan and self.contamination_scan_status != "clean":
            raise ValueError(
                "publishable_after_visibility_scan=true 时 contamination_scan_status 必须为 clean。"
            )
        if self.recovery_unlocked_after_provider_commit and not self.publishable_after_visibility_scan:
            raise ValueError(
                "recovery_unlocked_after_provider_commit=true 时必须已经通过可发布检查。"
            )
        recoverable = (
            self.publishable_after_visibility_scan
            and self.recovery_unlocked_after_provider_commit
        )
        object.__setattr__(self, "model_visible_recoverable", recoverable)
        return self


class MicroCompactRecord(StrictBaseModel):
    schema_version: str = "repo_harness_microcompact_record_v1"
    context_revision: int = Field(ge=0)
    compactable_tool_result_count_before: int = Field(ge=0)
    compactable_tool_result_chars_before: int = Field(ge=0)
    cleared_tool_result_ids: list[str] = Field(default_factory=list)
    kept_recent_tool_result_ids: list[str] = Field(default_factory=list)
    cleared_message_hash: str


class AutoCompactState(StrictBaseModel):
    schema_version: str = "repo_harness_auto_compact_state_v1"
    consecutive_failures: int = Field(default=0, ge=0)
    last_trigger_reason: str | None = None
    last_compact_record_ref: ArtifactRef | None = None
    disabled_for_current_run: bool = False


class AutoCompactRecord(StrictBaseModel):
    schema_version: str = "repo_harness_auto_compact_record_v1"
    compact_id: str
    trigger_reason: str
    mode: Literal["proactive", "hard_preflight", "emergency"] = "proactive"
    source_prepared_messages_ref: ArtifactRef
    source_model_input_hash: str
    compact_source_messages_ref: ArtifactRef | None = None
    compact_source_projection_hash: str | None = None
    tokens_before: int = Field(ge=0)
    tokens_after: int = Field(ge=0)
    effective_context_budget_tokens: int = Field(gt=0)
    summary_artifact_ref: ArtifactRef | None = None
    compact_model_call_ref: ArtifactRef | None = None
    rebuilt_messages_ref: ArtifactRef | None = None
    post_compact_above_target: bool = False
    status: Literal["applied", "failed", "skipped"] = "applied"
    failure_reason: str | None = None


class CompactPatchState(StrictBaseModel):
    schema_version: str = "repo_harness_compact_patch_state_v1"
    changed_files: list[str] = Field(default_factory=list)
    important_diffs: list[str] = Field(default_factory=list)


class CompactTestState(StrictBaseModel):
    schema_version: str = "repo_harness_compact_test_state_v1"
    commands_run: list[str] = Field(default_factory=list)
    passing: list[str] = Field(default_factory=list)
    failing: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)


class CompactToolRecoveryEntry(StrictBaseModel):
    schema_version: str = "repo_harness_compact_tool_recovery_entry_v1"
    tool_result_id: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    artifact_id: str | None = None
    sha256: str | None = None
    recovery_status: Literal[
        "artifact_recoverable",
        "cleared_without_recoverable_artifact",
        "preview_only",
        "not_needed",
    ] = "not_needed"


class CompactSummary(StrictBaseModel):
    schema_version: str = "repo_harness_compact_summary_v1"
    task_intent: str
    repository_facts: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    patch_state: CompactPatchState = Field(default_factory=CompactPatchState)
    test_state: CompactTestState = Field(default_factory=CompactTestState)
    tool_recovery_index: list[CompactToolRecoveryEntry] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_step: str
    visibility_policy: Literal["model_visible_only"] = "model_visible_only"


class AutoCompactResult(StrictBaseModel):
    schema_version: str = "repo_harness_auto_compact_result_v1"
    compact_id: str
    mode: Literal["proactive", "hard_preflight", "emergency"]
    trigger_reason: str
    status: Literal["applied", "failed", "skipped"]
    failure_reason: str | None = None
    source_prepared_messages_ref: ArtifactRef
    source_model_input_hash: str
    compact_source_messages_ref: ArtifactRef | None = None
    compact_source_projection_hash: str | None = None
    compact_model_request_ref: ArtifactRef | None = None
    compact_model_response_ref: ArtifactRef | None = None
    summary_artifact_ref: ArtifactRef | None = None
    rebuilt_messages_ref: ArtifactRef | None = None
    record_ref: ArtifactRef | None = None
    tokens_before: int = Field(ge=0)
    tokens_after: int = Field(ge=0)
    effective_context_budget_tokens: int = Field(gt=0)
    post_compact_target_tokens: int = Field(gt=0)
    hard_context_limit_tokens: int = Field(gt=0)
    post_compact_above_target: bool = False
    rebuilt_messages: list[dict[str, Any]] = Field(default_factory=list)
    summary: CompactSummary | None = None


class ContextPolicySnapshot(StrictBaseModel):
    schema_version: str = "repo_harness_context_policy_snapshot_v1"
    context_budget_policy: str
    model_context_window_tokens: int | Literal["auto"]
    harness_context_cap_tokens: int | None = None
    main_output_reserve_tokens: int
    estimator_safety_margin_ratio: float
    estimator_safety_margin_min_tokens: int
    max_context_tokens: int
    tool_result_aggregate_budget_chars: int
    keep_recent_turns: int
    keep_recent_test_results: int
    summarize_old_test_outputs: bool
    compact_strategy: str
    compact_threshold_ratio: float
    tool_result_compact_policy: str
    freeze_tool_result_budget_decisions: bool
    freeze_tool_result_decisions_at: str
    max_single_tool_result_chars: int
    max_tool_results_per_turn_chars: int
    tool_result_recovery_tool: str
    legacy_history_tool_result_replacement: bool
    microcompact_enabled: bool
    microcompact_policy: str
    microcompact_trigger_compactable_tool_result_count: int
    microcompact_trigger_compactable_tool_result_chars: int
    microcompact_keep_recent_compactable_tool_results: int
    microcompact_cleared_message: str
    auto_compact_enabled: bool
    auto_compact_trigger_ratio: float
    hard_context_limit_ratio: float
    post_compact_target_ratio: float
    post_compact_target_max_tokens: int
    auto_compact_max_consecutive_failures: int
    auto_compact_summary_max_output_tokens: int
    preserve_recent_turns_after_compact: int
    preserve_recent_tail_token_budget: int
    reactive_compact_enabled: bool
    local_context_limit_policy: str
    reactive_compact_policy: str
    ptl_retry_policy: str
    reactive_compact_retry_limit: int
    context_policy_version: str
    token_estimator: str


class ModelInputSnapshot(StrictBaseModel):
    schema_version: str = "repo_harness_model_input_snapshot_v1"
    model_call_id: str
    prepared_messages_ref: ArtifactRef
    model_input_hash: str
    provider_request_projection_hash: str
    context_policy_snapshot_ref: ArtifactRef | None = None
    provider_request_artifact_ref: ArtifactRef | None = None
    provider_response_artifact_ref: ArtifactRef | None = None
    context_compact_state_ref: ArtifactRef | None = None
    trainable: bool = True


class ContextReductionRecord(StrictBaseModel):
    schema_version: str = "repo_harness_context_reduction_record_v0"
    context_revision: int = Field(ge=0)
    source_message_ids: list[str] = Field(default_factory=list)
    kept_message_ids: list[str] = Field(default_factory=list)
    dropped_message_ids: list[str] = Field(default_factory=list)
    replaced_tool_result_ids: list[str] = Field(default_factory=list)
    replacement_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    replacement_preview_hash: str | None = None
    summary_artifact_ref: ArtifactRef | None = None
    model_visible: bool = True


class PreparedMessages(StrictBaseModel):
    schema_version: str = "repo_harness_prepared_messages_v0"
    messages: list[dict[str, Any]]
    prepared_messages_ref: ArtifactRef
    model_input_hash: str
    context_revision: int = Field(ge=0)
    context_event: TrajectoryEvent
    content_replacement_state: ContentReplacementState | None = None
    token_estimate: int = Field(ge=0)
    token_estimator_version: str = TOKEN_ESTIMATOR_VERSION
    internal_char_estimate: int = Field(default=0, ge=0)
    internal_token_estimate: int = Field(default=0, ge=0)
    provider_body_char_estimate: int = Field(default=0, ge=0)
    provider_ready_token_estimate: int = Field(default=0, ge=0)
    provider_ready_token_estimator_version: str = "provider_body_char4_token_estimator_v1"
    threshold_decision_source: str = "provider_ready_token_estimate"


class ContextCompactionFacts(StrictBaseModel):
    schema_version: str = CONTEXT_COMPACTION_FACTS_SCHEMA_VERSION
    run_id: str
    trigger_event_id: str
    context_revision_before: int = Field(ge=0)
    context_revision_after: int = Field(ge=0)
    tokens_before: int = Field(ge=0)
    tokens_after: int = Field(ge=0)
    compaction_strategy: str = "deterministic_preview_replacement"
    content_replacement_state_ref: ArtifactRef
    observation_replacement_refs: list[ArtifactRef] = Field(default_factory=list)
    model_visible_summary_ref: ArtifactRef | None = None
    original_content_retained_evaluator_only: bool = True
    contamination_scan_status: Literal["clean", "failed", "not_scanned"]

    def model_post_init(self, __context: Any) -> None:
        if self.context_revision_after <= self.context_revision_before:
            raise ValueError("context_revision_after 必须大于 context_revision_before。")
        if self.tokens_after > self.tokens_before:
            raise ValueError("context compaction 后 token 数不能增加。")
