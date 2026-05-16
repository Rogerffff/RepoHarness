from pathlib import Path

from repo_harness.agent_loop.loop import _record_tool_result
from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.budget import BudgetState
from repo_harness.config import ContextManagementConfig
from repo_harness.context import ToolResultArtifactIndex
from repo_harness.rl import (
    build_training_budget_policy,
    context_config_from_training_policy,
)
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolResult
from repo_harness.trajectory import RunRecorder


def test_stage8_training_policy_projects_tool_output_caps_to_context_config() -> None:
    policy = build_training_budget_policy(
        {"max_context_tokens": 16000, "max_tool_observation_tokens": 200},
        run_mode="training_fast",
    )
    config = context_config_from_training_policy(
        policy,
        base_config=ContextManagementConfig(
            max_context_tokens=120000,
            max_single_tool_result_chars=50000,
            max_tool_results_per_turn_chars=200000,
        ),
    )

    assert config.max_context_tokens == 16000
    assert config.max_single_tool_result_chars == 200
    assert config.max_tool_results_per_turn_chars == 200


def test_stage8_large_tool_output_becomes_artifact_backed_preview(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    messages: list[dict[str, object]] = []
    state = AgentLoopState(
        run_id="stage8-context-slimming",
        task_id="task",
        messages=messages,
        budget_state=BudgetState(started_at="2026-05-16T00:00:00+00:00"),
    )
    original = "very large tool output\n" * 80
    tool_result = ToolResult(
        tool_result_id="call_large_result",
        tool_call_id="call_large",
        tool_name="grep",
        requested_tool_name="grep",
        effective_tool_name="grep",
        requested_arguments={"query": "needle"},
        normalized_arguments={"query": "needle"},
        effective_arguments={"query": "needle"},
        normalized_input_hash=stable_hash({"query": "needle"}),
        status="ok",
        content_preview=original,
        typed={"result_envelope": {"context_effects": []}},
    )
    policy = build_training_budget_policy(
        {"max_tool_observation_tokens": 120},
        run_mode="training_fast",
    )
    config = context_config_from_training_policy(policy)

    with RunRecorder("stage8-context-slimming", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _record_tool_result(
            tool_result_artifact_index=index,
            context_config=config,
            run_id="stage8-context-slimming",
            task_id="task",
            turn=1,
            tool_result=tool_result,
            state=state,
            recorder=recorder,
            messages=messages,
        )

    assert len(index.records_by_artifact_id) == 1
    record = next(iter(index.records_by_artifact_id.values()))
    assert record.size_chars == len(original)
    assert messages[0]["content"] != original
    assert "<persisted-output>" in str(messages[0]["content"])
    assert record.artifact_id in str(messages[0]["content"])
    assert messages[0]["typed"]["single_tool_result_persisted"] is True
    assert messages[0]["typed"]["single_tool_result_original_chars"] == len(original)
    assert messages[0]["typed"]["result_envelope"]["model_visible_text_truncated"] is True
    assert "tool_result_recoverable" in messages[0]["typed"]["result_envelope"]["context_effects"]

