"""轨迹、事件、artifact 和运行汇总 schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    ARTIFACT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION,
    TRANSCRIPT_SCHEMA_VERSION,
)


class ArtifactRef(StrictBaseModel):
    schema_version: str = ARTIFACT_SCHEMA_VERSION
    artifact_id: str
    relative_path: str
    kind: str
    sha256: str
    size_bytes: int = Field(ge=0)
    created_by_event_id: str | None = None
    redaction_status: str = "not_scanned"
    retention_policy: str = "keep"


class TranscriptRecord(StrictBaseModel):
    schema_version: str = TRANSCRIPT_SCHEMA_VERSION
    record_id: str
    run_id: str
    task_id: str
    message_id: str
    parent_message_id: str | None = None
    turn: int = Field(ge=0)
    role: Literal["system", "user", "assistant", "tool", "verifier", "termination"]
    model_call_id: str | None = None
    tool_call_id: str | None = None
    tool_result_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)
    content_preview: str = ""
    content_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    model_visible: bool
    trainable: bool
    created_at: str


class TrajectoryEvent(StrictBaseModel):
    schema_version: str = EVENT_SCHEMA_VERSION
    event_id: str
    timestamp: str
    run_id: str
    task_id: str | None = None
    turn: int | None = Field(default=None, ge=0)
    event_type: str
    severity: Literal["debug", "info", "warning", "error"] = "info"
    duration_ms: int | None = Field(default=None, ge=0)
    error_type: str | None = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class RunSummary(StrictBaseModel):
    schema_version: str = "repo_harness_run_summary_v0"
    run_id: str
    task_id: str | None = None
    agent_stop_reason: str | None = None
    final_verifier_status: Literal["accepted", "failed", "timeout", "error", "skipped"] = "skipped"
    run_outcome: Literal["success", "failed", "invalid_task", "flaky_task", "interrupted", "inconclusive"]
    key_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    failure_diagnostics: list[str] = Field(default_factory=list)
    human_summary: str


class MetricsRecord(StrictBaseModel):
    schema_version: str = "repo_harness_metrics_v0"
    task_success: bool = False
    final_verifier_status: Literal["accepted", "failed", "timeout", "error", "skipped"] = "skipped"
    run_outcome: Literal["success", "failed", "invalid_task", "flaky_task", "interrupted", "inconclusive"]
    turn_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    test_run_count: int = Field(default=0, ge=0)
    timeout: bool = False
    patch_stats: dict[str, Any] = Field(default_factory=dict)
    permission_denial_count: int = Field(default=0, ge=0)
    invalid_tool_call_count: int = Field(default=0, ge=0)
    cost_estimate: float = Field(default=0.0, ge=0.0)
    code_quality_checks: dict[str, Any] = Field(default_factory=dict)
    interaction_efficiency: dict[str, Any] = Field(default_factory=dict)
    patch_locality: dict[str, Any] = Field(default_factory=dict)
