import json
from pathlib import Path

from repo_harness.agent_loop import AgentLoop
from repo_harness.model_client import ModelMessage, ModelResponse
from repo_harness.scaffolds import (
    build_scaffold,
    resolve_allowed_tools,
    resolve_allowed_tools_for_phase,
    resolve_feedback_policy,
)
from repo_harness.tools import DEFAULT_TOOL_ORDER, ToolExecutor
from repo_harness.trajectory import RunRecorder


def test_planner_coder_verifier_scaffold_declares_phase_policy():
    scaffold = build_scaffold("planner_coder_verifier")

    assert scaffold.scaffold_id == "planner_coder_verifier"
    assert scaffold.initial_phase == "planner"
    assert scaffold.phases() == ["planner", "coder", "verifier", "repair", "final"]
    assert scaffold.allowed_tools_for_phase("planner") == [
        "list_files",
        "glob_files",
        "read_file",
        "grep",
        "symbol_search",
        "update_working_state",
        "git_diff",
    ]
    assert "edit_file" not in scaffold.allowed_tools_for_phase("planner")
    assert "run_tests" in scaffold.allowed_tools_for_phase("verifier")
    assert scaffold.allowed_tools_for_phase("final") == []
    assert scaffold.default_feedback_tests_passed_policy.value == "require_model_final"


def test_phase_allowed_tools_respect_disabled_test_feedback():
    scaffold = build_scaffold("planner_coder_verifier")
    feedback_policy = resolve_feedback_policy(
        run_config=_run_config_with_disabled_feedback(),
        scaffold=scaffold,
    )

    allowed = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    verifier_allowed = resolve_allowed_tools_for_phase(
        scaffold=scaffold,
        feedback_policy=feedback_policy,
        phase="verifier",
    )

    assert "run_tests" not in allowed
    assert "run_tests" not in verifier_allowed
    assert verifier_allowed == ["glob_files", "read_file", "grep", "symbol_search", "update_working_state", "git_diff"]


def test_agent_loop_records_phase_transitions_and_phase_context(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _PhaseRecordingClient()
    scaffold = build_scaffold("planner_coder_verifier")
    with RunRecorder("phase-loop", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            scaffold=scaffold,
            allowed_tool_names=list(DEFAULT_TOOL_ORDER),
        ).run(
            run_id="phase-loop",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=2,
        )

    events = _read_events(run_dir)
    assert [request.scaffold_phase for request in client.requests] == ["planner", "coder"]
    assert client.requests[0].prepared_messages[-1]["content"]["scaffold_phase_metadata"] == {
        "schema_version": "repo_harness_scaffold_phase_context_v0",
        "scaffold_id": "planner_coder_verifier",
        "scaffold_version": "repo_harness_planner_coder_verifier_v0",
        "current_phase": "planner",
        "phase_sequence": ["planner", "coder", "verifier", "repair", "final"],
        "phase_prompt": "Plan the repository change. Inspect files as needed, but do not edit code.",
        "allowed_tools_for_phase": ["list_files", "glob_files", "read_file", "grep", "symbol_search", "update_working_state", "git_diff"],
        "phase_transition_policy": "repo_harness_planner_coder_verifier_linear_v0",
    }
    assert client.requests[0].allowed_tool_definitions[-1]["name"] == "git_diff"
    assert "edit_file" not in [tool["name"] for tool in client.requests[0].allowed_tool_definitions]
    assert client.requests[1].scaffold_phase == "coder"
    assert "edit_file" in [tool["name"] for tool in client.requests[1].allowed_tool_definitions]
    assert state.current_phase == "verifier"
    assert state.agent_stop_reason == "max_turns"
    transitions = [
        event["data"]
        for event in events
        if event["event_type"] == "scaffold_phase_transition"
    ]
    assert [(event["from_phase"], event["to_phase"]) for event in transitions] == [
        ("planner", "coder"),
        ("coder", "verifier"),
    ]


def _run_config_with_disabled_feedback():
    from repo_harness.config import RunConfig

    config = RunConfig()
    config.runtime.scaffold_id = "planner_coder_verifier"
    config.runtime.test_feedback_policy = "disabled"
    return config


def _read_events(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class _PhaseRecordingClient:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, recorder):  # noqa: ANN001
        self.requests.append(request)
        return ModelResponse(
            assistant_message=ModelMessage(
                role="assistant",
                content=f"phase {request.scaffold_phase} complete",
            ),
            finish_reason="stop",
        )
