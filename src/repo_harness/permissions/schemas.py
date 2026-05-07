"""权限决策 schema。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import PERMISSION_POLICY_VERSION


class PermissionDecision(StrictBaseModel):
    schema_version: str = "repo_harness_permission_decision_v0"
    decision_id: str
    tool_call_id: str
    tool_name: str
    requested_tool_name: str
    effective_tool_name: str
    decision: Literal["allow", "deny", "ask"]
    mode: Literal["plan", "ask", "auto", "deny"]
    matched_rule: str | None = None
    policy_version: str = PERMISSION_POLICY_VERSION
    rule_source: str | None = None
    reason: str
    normalized_input_hash: str
    resolved_paths: list[str] = Field(default_factory=list)
    command_category: str | None = None
    network_policy: str | None = None
    requested_cwd: str | None = None
    effective_cwd: str | None = None
    policy_decision: str | None = None
    reason_code: str | None = None
    safe_argv: list[str] | None = None
    recovery_hint: str | None = None
    timeout_sec: int | None = None
    shell_execution: bool = False
    non_interactive_resolution: str | None = None
    requires_user_input: bool = False
