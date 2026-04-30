"""预算配置和运行时预算状态 schema。"""

from __future__ import annotations

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel


class BudgetManager(StrictBaseModel):
    schema_version: str = "repo_harness_budget_manager_v0"
    max_turns: int = Field(gt=0)
    max_tool_calls: int = Field(ge=0)
    max_test_runs: int = Field(ge=0)
    task_timeout_sec: int = Field(gt=0)
    command_timeout_sec: int = Field(gt=0)
    verifier_timeout_sec: int = Field(gt=0)
    max_tool_output_chars: int = Field(gt=0)
    max_context_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    max_cost: float | None = Field(default=None, ge=0.0)
    max_artifact_bytes: int | None = Field(default=None, gt=0)
    max_concurrent_tasks: int = Field(default=1, gt=0)


class BudgetState(StrictBaseModel):
    schema_version: str = "repo_harness_budget_state_v0"
    started_at: str
    turn_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    test_run_count: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)
    stop_reason: str | None = None
