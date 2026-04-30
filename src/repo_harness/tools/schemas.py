"""工具调用和工具结果 schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import TOOL_POLICY_VERSION
from repo_harness.trajectory import ArtifactRef


class ToolCall(StrictBaseModel):
    schema_version: str = "repo_harness_tool_call_v0"
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    turn: int = Field(ge=0)


class ToolResult(StrictBaseModel):
    schema_version: str = "repo_harness_tool_result_v0"
    tool_result_id: str
    tool_call_id: str
    tool_name: str
    requested_tool_name: str
    effective_tool_name: str
    requested_arguments: dict[str, Any] = Field(default_factory=dict)
    normalized_arguments: dict[str, Any] = Field(default_factory=dict)
    effective_arguments: dict[str, Any] = Field(default_factory=dict)
    normalization_policy_version: str = "repo_harness_tool_normalization_v0"
    normalized_input_hash: str
    route_reason: str | None = None
    route_policy_version: str = TOOL_POLICY_VERSION
    status: Literal["ok", "error", "denied", "timeout", "interrupted"]
    content_preview: str
    error_type: str | None = None
    truncated: bool = False
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    duration_ms: int | None = Field(default=None, ge=0)
    typed: dict[str, Any] = Field(default_factory=dict)
