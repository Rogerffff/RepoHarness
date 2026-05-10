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
    "context_limit_preflight_after_autocompact",
    "auto_compact_failed_preflight",
    "reactive_compact_failed",
    "context_limit_after_reactive_compact",
    "context_limit_reactive_compact_disabled",
    "context_integrity_error",
    "model_error",
    "output_token_limit_reached",
    "tool_call_parse_failure_unrecovered",
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
    permission_denial_reasons: list[str] = Field(default_factory=list)
    last_verifier_result: dict[str, Any] | None = None
    budget_state: BudgetState
    tool_pairing_state: ToolPairingState = Field(default_factory=ToolPairingState)
    context_revision: int = Field(default=0, ge=0)
    auto_compact_count: int = Field(default=0, ge=0)
    auto_compact_consecutive_failures: int = Field(default=0, ge=0)
    last_auto_compact_record_ref: dict[str, Any] | None = None
    last_auto_compact_summary_ref: dict[str, Any] | None = None
    last_auto_compact_context_revision_before: int | None = Field(default=None, ge=0)
    last_auto_compact_context_revision_after: int | None = Field(default=None, ge=0)
    post_compact_above_target: bool = False
    current_phase: str | None = None
    phase_history: list[dict[str, Any]] = Field(default_factory=list)
    last_model_error: str | None = None
    last_tool_parse_error: str | None = None
    agent_stop_reason: AgentStopReason | None = None
    feedback_verifier_accepted: bool = False
    first_feedback_accept_turn: int | None = Field(default=None, ge=0)
    first_feedback_accept_ref: dict[str, Any] | None = None
    feedback_tests_passed_policy: str = "stop_immediately"
    test_feedback_policy: str = "oracle_hidden_feedback"
    hidden_feedback_visible_to_model: bool = True
    public_tests_ran: bool = False
    hidden_feedback_ran: bool = False
    loop_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    loop_diagnostics_summary: dict[str, Any] = Field(default_factory=dict)
    working_state: dict[str, Any] | None = None
