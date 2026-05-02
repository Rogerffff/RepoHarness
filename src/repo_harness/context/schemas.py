"""Context Builder 和 Context Manager schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

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
