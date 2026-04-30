import json
import time
from pathlib import Path

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.model_client import FakeModelClient, ModelMessage
from repo_harness.tools import ToolCall
from repo_harness.tools import ToolExecutor
from repo_harness.trajectory import RunRecorder


def test_agent_loop_accepts_valid_final_answer(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
    )

    assert state.agent_stop_reason == "final_answer"


def test_agent_loop_rejects_empty_no_tool_response(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[{"step_id": "empty", "action": "assistant"}],
    )

    assert state.agent_stop_reason == "model_error"
    assert state.last_model_error == "invalid_final_answer"


def test_agent_loop_rejects_refusal_like_final_answer(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[
            {
                "step_id": "refusal",
                "action": "final_answer",
                "assistant_text": "I cannot continue from previous context.",
            }
        ],
    )

    assert state.agent_stop_reason == "model_error"
    assert state.last_model_error == "invalid_final_answer"


def test_agent_loop_rejects_json_like_final_answer(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[
            {
                "step_id": "json",
                "action": "final_answer",
                "assistant_text": '{"tool_call": {"name": "read_file"',
            }
        ],
    )

    assert state.agent_stop_reason == "model_error"
    assert state.last_model_error == "invalid_final_answer"


def test_agent_loop_stops_on_model_error(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[
            {
                "step_id": "error",
                "action": "model_error",
                "assistant_text": "provider failed",
                "model_error_type": "provider_error",
            }
        ],
    )

    assert state.agent_stop_reason == "model_error"
    assert state.last_model_error == "provider_error"


def test_agent_loop_max_turns_is_deterministic(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[
            {
                "step_id": "unknown",
                "action": "tool_call",
                "tool_call_id": "call_unknown",
                "tool_name": "missing_tool",
                "arguments": {},
            }
        ],
        budget=BudgetManager(
            max_turns=1,
            max_tool_calls=10,
            max_test_runs=10,
            task_timeout_sec=60,
            command_timeout_sec=30,
            verifier_timeout_sec=30,
            max_tool_output_chars=4000,
            max_context_tokens=120000,
            max_output_tokens=4096,
        ),
    )

    assert state.agent_stop_reason == "max_turns"


def test_agent_loop_context_limit_records_prepared_context(tmp_path: Path):
    run_dir = tmp_path / "run"
    budget = BudgetManager(
        max_turns=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=1,
        max_output_tokens=4096,
    )

    with RunRecorder("context-limit", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="context-limit",
                task_id="task",
                steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
            ),
            tool_executor=ToolExecutor(),
        ).run(
            run_id="context-limit",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system " * 20}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "context_limit"
    assert any(event["event_type"] == "context_prepared" for event in events)
    assert any(event["event_type"] == "budget_exhausted" for event in events)
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_max_cost_zero_stops_before_model_call(tmp_path: Path):
    run_dir = tmp_path / "run"
    budget = BudgetManager(
        max_turns=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
        max_cost=0.0,
    )

    with RunRecorder("max-cost", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="max-cost",
                task_id="task",
                steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
            ),
            tool_executor=ToolExecutor(),
        ).run(
            run_id="max-cost",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "max_cost"
    assert any(event["event_type"] == "budget_exhausted" and event["error_type"] == "max_cost" for event in events)
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_timeout_after_model_interrupts_tool_calls_before_execution(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="timeout-after-model",
        task_id="task",
        steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "unused"}],
    )

    def slow_tool_response(**_kwargs):  # noqa: ANN001
        time.sleep(1.1)
        return _SingleToolResponse()

    client.generate = slow_tool_response  # type: ignore[method-assign]
    budget = BudgetManager(
        max_turns=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=1,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    with RunRecorder("timeout-after-model", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="timeout-after-model",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    event_types = [event["event_type"] for event in events]
    assert state.agent_stop_reason == "timeout"
    assert state.tool_pairing_state.tool_result_ids["call_read"] == "call_read_result"
    assert "permission_decision" not in event_types
    assert "tool_completed" not in event_types
    assert event_types.index("budget_exhausted") < event_types.index("tool_interrupted")
    _assert_tool_events_are_paired(events)


def test_agent_loop_max_tool_calls_pairs_interrupted_result(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="max-tools",
        task_id="task",
        steps=[
            {
                "step_id": "read",
                "action": "tool_call",
                "tool_call_id": "call_read",
                "tool_name": "read_file",
                "arguments": {"path": "demo.py"},
            }
        ],
    )
    budget = BudgetManager(
        max_turns=1,
        max_tool_calls=0,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )
    with RunRecorder("max-tools", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="max-tools",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
        )

    assert state.agent_stop_reason == "max_tool_calls"
    assert state.tool_pairing_state.tool_result_ids["call_read"] == "call_read_result"


def test_agent_loop_max_tool_calls_interrupts_remaining_parsed_calls(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="max-tools-many",
        task_id="task",
        steps=[
            {
                "step_id": "final",
                "action": "final_answer",
                "assistant_text": "unused",
            }
        ],
    )
    client.generate = lambda **_kwargs: _MultiToolResponse()  # type: ignore[method-assign]
    budget = BudgetManager(
        max_turns=1,
        max_tool_calls=0,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    with RunRecorder("max-tools-many", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="max-tools-many",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
        )

    assert state.agent_stop_reason == "max_tool_calls"
    assert state.tool_pairing_state.tool_result_ids == {
        "call_tests": "call_tests_result",
        "call_after": "call_after_result",
    }
    _assert_tool_events_are_paired(_read_events(run_dir))


def test_agent_loop_interrupts_remaining_tools_when_feedback_passes(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="multi-feedback",
        task_id="task",
        steps=[
            {
                "step_id": "final",
                "action": "final_answer",
                "assistant_text": "unused",
            }
        ],
    )
    client.generate = lambda **_kwargs: _MultiToolResponse()  # type: ignore[method-assign]
    with RunRecorder("multi-feedback", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_MultiToolExecutor(),
        ).run(
            run_id="multi-feedback",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.agent_stop_reason == "feedback_tests_passed"
    assert state.tool_pairing_state.tool_result_ids["call_tests"] == "call_tests_result"
    assert state.tool_pairing_state.tool_result_ids["call_after"] == "call_after_result"
    _assert_tool_events_are_paired(_read_events(run_dir))


class _MultiToolExecutor(ToolExecutor):
    def is_known(self, tool_name: str) -> bool:
        return True

    def check_permission(self, tool_call, context):  # noqa: ANN001
        from repo_harness.permissions import PermissionDecision
        from repo_harness.schema_base import stable_hash

        return PermissionDecision(
            decision_id=f"{tool_call.tool_call_id}_permission",
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            requested_tool_name=tool_call.tool_name,
            effective_tool_name=tool_call.tool_name,
            decision="allow",
            mode="auto",
            reason="test allow",
            normalized_input_hash=stable_hash(tool_call.arguments),
        )

    def execute(self, tool_call, context):  # noqa: ANN001
        from repo_harness.tools import ToolResult
        from repo_harness.schema_base import stable_hash

        return ToolResult(
            tool_result_id=f"{tool_call.tool_call_id}_result",
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            requested_tool_name=tool_call.tool_name,
            effective_tool_name="run_tests",
            requested_arguments=tool_call.arguments,
            normalized_arguments=tool_call.arguments,
            effective_arguments=tool_call.arguments,
            normalized_input_hash=stable_hash(tool_call.arguments),
            status="ok",
            content_preview="tests passed",
            typed={"status": "ok", "verifier_result_preview": {"accepted": True}},
        )


class _MultiToolResponse:
    assistant_message = ModelMessage(role="assistant", content=None)
    tool_calls = [
        ToolCall(tool_call_id="call_tests", tool_name="run_tests", arguments={}, turn=1),
        ToolCall(tool_call_id="call_after", tool_name="read_file", arguments={"path": "demo.py"}, turn=1),
    ]
    raw_provider_request_ref = None
    raw_provider_response_ref = None
    finish_reason = "tool_calls"
    model_error_type = None
    model_call_event = None


class _SingleToolResponse:
    assistant_message = ModelMessage(role="assistant", content=None)
    tool_calls = [
        ToolCall(tool_call_id="call_read", tool_name="read_file", arguments={"path": "demo.py"}, turn=1),
    ]
    raw_provider_request_ref = None
    raw_provider_response_ref = None
    finish_reason = "tool_calls"
    model_error_type = None
    model_call_event = None


def _run_loop(
    tmp_path: Path,
    *,
    steps: list[dict[str, object]],
    budget: BudgetManager | None = None,
):
    with RunRecorder("loop-test", tmp_path / "run", task_id="task") as recorder:
        return AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="loop",
                task_id="task",
                steps=steps,
            ),
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-test",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=budget.max_turns if budget else 3,
            budget_manager=budget,
        )


def _read_events(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_tool_events_are_paired(events: list[dict]) -> None:
    requested = {
        event["data"]["tool_call_id"]
        for event in events
        if event["event_type"] == "tool_requested"
    }
    completed = {
        event["data"]["tool_call_id"]
        for event in events
        if event["event_type"] in {
            "tool_completed",
            "tool_denied",
            "tool_failed",
            "tool_timeout",
            "tool_interrupted",
        }
    }
    assert requested == completed
