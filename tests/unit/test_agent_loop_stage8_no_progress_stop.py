import json
from pathlib import Path
from typing import Any

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.model_client import ModelMessage, ModelResponse
from repo_harness.rl import build_training_budget_policy
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolCall, ToolExecutor, ToolResult
from repo_harness.trajectory import RunRecorder


def test_stage8_no_progress_hard_stop_records_event_and_skips_nudge(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    client = _RepeatedGrepClient()
    policy = build_training_budget_policy(
        {
            "max_turns": 12,
            "max_model_calls": 20,
            "max_tool_calls": 20,
            "no_progress_policy": {"hard_stop_enabled": True},
        },
        run_mode="training_fast",
    )

    with RunRecorder("stage8-no-progress", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="stage8-no-progress",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=12,
            training_budget_policy=policy,
        )

    events = _read_events(run_dir)
    hard_stop = next(event for event in events if event["event_type"] == "no_progress_hard_stop")
    diagnostic = next(
        event
        for event in events
        if event["event_type"] == "loop_progress_diagnostic"
        and event["data"].get("hard_stop_enabled") is True
    )

    assert state.agent_stop_reason == "no_progress"
    assert state.budget_state.stop_reason in {
        "no_progress_empty_search_loop",
        "no_progress_read_only_loop",
        "no_progress_repeated_tool_input",
        "no_progress_no_patch_after_budget",
    }
    assert hard_stop["error_type"] == state.budget_state.stop_reason
    assert hard_stop["data"]["stop_reason"] == state.budget_state.stop_reason
    assert hard_stop["data"]["trainable"] is False
    assert hard_stop["data"]["invalid_for_training"] is True
    assert hard_stop["data"]["invalid_for_online_rl"] is True
    assert diagnostic["data"]["hard_stop_reason"] == state.budget_state.stop_reason
    assert diagnostic["data"]["model_visible_message_injected"] is False
    assert not any(event["event_type"] == "convergence_nudge_injected" for event in events)
    assert state.budget_state.model_call_count == len(client.requests)


def test_stage8_no_progress_policy_can_disable_model_visible_nudge_without_hard_stop(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    client = _RepeatedGrepClient()
    policy = build_training_budget_policy(
        {
            "max_turns": 12,
            "max_model_calls": 20,
            "max_tool_calls": 20,
            "no_progress_policy": {
                "hard_stop_enabled": False,
                "allow_model_visible_nudge": False,
            },
        },
        run_mode="training_fast",
    )

    with RunRecorder("stage8-no-nudge", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="stage8-no-nudge",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=12,
            training_budget_policy=policy,
        )

    events = _read_events(run_dir)
    diagnostics = [event for event in events if event["event_type"] == "loop_progress_diagnostic"]

    assert state.agent_stop_reason == "max_turns"
    assert diagnostics
    assert not any(event["event_type"] == "convergence_nudge_injected" for event in events)
    assert all(event["data"]["model_visible_message_injected"] is False for event in diagnostics)


def test_stage8_no_progress_policy_thresholds_drive_hard_stop_timing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    client = _RepeatedGrepClient()
    policy = build_training_budget_policy(
        {
            "max_turns": 12,
            "max_model_calls": 12,
            "max_tool_calls": 20,
            "no_progress_policy": {
                "hard_stop_enabled": True,
                "read_only_streak_threshold": 1,
                "repeated_input_threshold": 1,
                "empty_search_threshold": 1,
            },
        },
        run_mode="training_fast",
    )

    with RunRecorder("stage8-thresholds", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="stage8-thresholds",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=12,
            training_budget_policy=policy,
        )

    events = _read_events(run_dir)
    hard_stop = next(event for event in events if event["event_type"] == "no_progress_hard_stop")

    assert state.agent_stop_reason == "no_progress"
    assert len(client.requests) == 1
    assert hard_stop["data"]["thresholds"]["read_only_streak_threshold"] == 1
    assert hard_stop["data"]["thresholds"]["empty_search_threshold"] == 1


def test_stage8_max_model_calls_stops_before_submitting_next_provider_request(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    client = _ToolThenFinalClient()
    budget = BudgetManager(
        max_turns=5,
        max_model_calls=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    with RunRecorder("stage8-max-model-calls", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="stage8-max-model-calls",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=5,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    exhausted = next(
        event
        for event in events
        if event["event_type"] == "budget_exhausted"
        and event["error_type"] == "max_model_calls_exceeded"
    )

    assert state.agent_stop_reason == "max_model_calls_exceeded"
    assert state.budget_state.stop_reason == "max_model_calls_exceeded"
    assert state.budget_state.model_call_count == 1
    assert len(client.requests) == 1
    assert exhausted["data"]["stop_reason"] == "max_model_calls_exceeded"
    assert exhausted["data"]["provider_request_submitted"] is False
    assert exhausted["data"]["used_model_calls"] == 1


def test_stage8_auto_compact_retry_attempts_count_against_model_call_budget(tmp_path: Path) -> None:
    from repo_harness.config import ContextManagementConfig

    run_dir = tmp_path / "run"
    client = _AutoCompactRetryClient()
    budget = BudgetManager(
        max_turns=3,
        max_model_calls=3,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    with RunRecorder("stage8-compact-retry-count", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="stage8-compact-retry-count",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {"role": "assistant", "turn": 1, "content": "old analysis " * 600},
                {"role": "user", "turn": 2, "content": "old follow up " * 600},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            budget_manager=budget,
            context_config=ContextManagementConfig(
                model_context_window_tokens=12000,
                main_output_reserve_tokens=0,
                estimator_safety_margin_ratio=0.0,
                estimator_safety_margin_min_tokens=0,
                auto_compact_trigger_ratio=0.1,
                hard_context_limit_ratio=0.95,
                post_compact_target_max_tokens=2000,
            ),
        )

    events = _read_events(run_dir)
    completed = next(
        event for event in events if event["event_type"] == "auto_compact_model_call_completed"
    )
    exhausted = next(
        event
        for event in events
        if event["event_type"] == "budget_exhausted"
        and event["error_type"] == "max_model_calls_exceeded"
    )

    assert completed["data"]["attempt_count"] == 3
    assert completed["data"]["retry_count"] == 2
    assert state.budget_state.model_call_count == 3
    assert state.agent_stop_reason == "max_model_calls_exceeded"
    assert [request.scaffold_phase for request in client.requests] == ["compact"]
    assert exhausted["data"]["used_model_calls"] == 3


def test_stage8_provider_retry_overrun_records_submitted_request(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    client = _RetryToolCallClient()
    budget = BudgetManager(
        max_turns=3,
        max_model_calls=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    with RunRecorder("stage8-retry-overrun", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="stage8-retry-overrun",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    exhausted = next(
        event
        for event in events
        if event["event_type"] == "budget_exhausted"
        and event["error_type"] == "max_model_calls_exceeded"
    )

    assert state.agent_stop_reason == "max_model_calls_exceeded"
    assert state.budget_state.model_call_count == 3
    assert len(client.requests) == 1
    assert exhausted["data"]["provider_request_submitted"] is True
    assert exhausted["data"]["over_budget_after_response"] is True
    assert exhausted["data"]["attempt_count"] == 3
    assert exhausted["data"]["retry_count"] == 2
    assert exhausted["data"]["used_model_calls"] == 3


def test_stage8_retry_attempts_are_counted_in_budget_state(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    client = _RetryAttemptClient()

    with RunRecorder("stage8-retry-count", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="stage8-retry-count",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.agent_stop_reason == "final_answer"
    assert state.budget_state.model_call_count == 3


class _RepeatedGrepClient:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content=None),
            tool_calls=[
                ToolCall(
                    tool_call_id=f"call_grep_{request.turn}",
                    tool_name="grep",
                    arguments={"query": "missing-symbol", "root": "src"},
                    turn=request.turn,
                )
            ],
            finish_reason="tool_calls",
        )


class _ToolThenFinalClient:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(
                assistant_message=ModelMessage(role="assistant", content=None),
                tool_calls=[
                    ToolCall(
                        tool_call_id="call_grep_1",
                        tool_name="grep",
                        arguments={"query": "missing-symbol", "root": "src"},
                        turn=request.turn,
                    )
                ],
                finish_reason="tool_calls",
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _RetryAttemptClient:
    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
            attempt_count=3,
            retry_count=2,
        )


class _RetryToolCallClient:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content=None),
            tool_calls=[
                ToolCall(
                    tool_call_id="call_grep_retry",
                    tool_name="grep",
                    arguments={"query": "missing-symbol", "root": "src"},
                    turn=request.turn,
                )
            ],
            finish_reason="tool_calls",
            attempt_count=3,
            retry_count=2,
        )


class _AutoCompactRetryClient:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        if request.scaffold_phase == "compact":
            compact_content = json.dumps(
                {
                    "schema_version": "repo_harness_compact_summary_v1",
                    "task_intent": "Continue from visible context.",
                    "repository_facts": ["The task is public."],
                    "actions_taken": ["Old context was summarized."],
                    "patch_state": {"changed_files": [], "important_diffs": []},
                    "test_state": {
                        "commands_run": [],
                        "passing": [],
                        "failing": [],
                        "unknown": ["not run"],
                    },
                    "tool_recovery_index": [],
                    "open_questions": [],
                    "next_step": "Inspect the relevant file.",
                    "visibility_policy": "model_visible_only",
                }
            )
            return ModelResponse(
                assistant_message=ModelMessage(role="assistant", content=compact_content),
                finish_reason="stop",
                attempt_count=3,
                retry_count=2,
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _NoProgressToolExecutor(ToolExecutor):
    def validate_input(self, tool_call, context):  # noqa: ANN001, ARG002
        return None

    def check_permission(self, tool_call, context):  # noqa: ANN001, ARG002
        from repo_harness.permissions import PermissionDecision

        normalized = self.normalize(tool_call, context)
        return PermissionDecision(
            decision_id=f"{tool_call.tool_call_id}_permission",
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            requested_tool_name=normalized.requested_tool_name,
            effective_tool_name=normalized.effective_tool_name,
            decision="allow",
            mode="auto",
            reason="test allow",
            normalized_input_hash=normalized.normalized_input_hash,
        )

    def execute(self, tool_call, context):  # noqa: ANN001, ARG002
        normalized = self.normalize(tool_call, context)
        return ToolResult(
            tool_result_id=f"{tool_call.tool_call_id}_result",
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            requested_tool_name=normalized.requested_tool_name,
            effective_tool_name=normalized.effective_tool_name,
            requested_arguments=normalized.requested_arguments,
            normalized_arguments=normalized.normalized_arguments,
            effective_arguments=normalized.effective_arguments,
            normalized_input_hash=stable_hash(normalized.normalized_arguments),
            status="ok",
            content_preview="No matches found under root='src'.",
            typed={
                "result_kind": "complete_no_match",
                "total_match_count": 0,
                "match_count": 0,
            },
        )


def _read_events(run_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
