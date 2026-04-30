"""Agent loop 状态 schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from repo_harness.budget import BudgetState
from repo_harness.schema_base import StrictBaseModel


AgentStopReason = Literal[
    "final_answer",
    "feedback_tests_passed",
    "max_turns",
    "max_tool_calls",
    "max_test_runs",
    "max_cost",
    "timeout",
    "permission_denied",
    "tool_error",
    "invalid_tool_call",
    "context_limit",
    "model_error",
    "no_progress",
    "manual_stop",
]


class ToolPairingState(StrictBaseModel):
    schema_version: str = "repo_harness_tool_pairing_state_v0"
    pending_tool_call_ids: list[str] = Field(default_factory=list)
    completed_tool_call_ids: list[str] = Field(default_factory=list)
    tool_result_ids: dict[str, str] = Field(default_factory=dict)


class AgentLoopState(StrictBaseModel):
    schema_version: str = "repo_harness_agent_loop_state_v0"
    run_id: str
    task_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    turn_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    permission_denial_count: int = Field(default=0, ge=0)
    invalid_tool_call_count: int = Field(default=0, ge=0)
    last_verifier_result: dict[str, Any] | None = None
    budget_state: BudgetState
    tool_pairing_state: ToolPairingState = Field(default_factory=ToolPairingState)
    context_revision: int = Field(default=0, ge=0)
    last_model_error: str | None = None
    last_tool_parse_error: str | None = None
    agent_stop_reason: AgentStopReason | None = None
