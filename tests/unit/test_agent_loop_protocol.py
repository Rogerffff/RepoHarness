import json
import time
from pathlib import Path

import pytest

from repo_harness.agent_loop import AgentLoop
from repo_harness.agent_loop.loop import _record_interrupted_tool_calls, _record_tool_result
from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.budget import BudgetManager
from repo_harness.budget.schemas import BudgetState
from repo_harness.config import ContextManagementConfig
from repo_harness.context import ToolResultArtifactIndex
from repo_harness.model_client import FakeModelClient, ModelCallEvent, ModelMessage, ModelResponse
from repo_harness.model_client.provider_private_state import provider_private_state_store
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolCall
from repo_harness.tools import ToolExecutor
from repo_harness.tools import ToolResult
from repo_harness.trajectory import RunRecorder


def test_agent_loop_accepts_valid_final_answer(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
    )

    assert state.agent_stop_reason == "final_answer"


def test_record_tool_result_persists_single_oversized_result(tmp_path: Path):
    run_dir = tmp_path / "run"
    messages: list[dict[str, object]] = []
    state = AgentLoopState(
        run_id="single-tool-budget",
        task_id="task",
        messages=messages,
        budget_state=BudgetState(started_at="2026-05-10T00:00:00+00:00"),
    )
    content = "large tool output\n" * 20
    tool_result = ToolResult(
        tool_result_id="call_big_result",
        tool_call_id="call_big",
        tool_name="grep",
        requested_tool_name="grep",
        effective_tool_name="grep",
        normalized_input_hash=stable_hash({"query": "large"}),
        status="ok",
        content_preview=content,
    )
    with RunRecorder("single-tool-budget", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _record_tool_result(
            tool_result_artifact_index=index,
            context_config=ContextManagementConfig(max_single_tool_result_chars=50),
            run_id="single-tool-budget",
            task_id="task",
            turn=1,
            tool_result=tool_result,
            state=state,
            recorder=recorder,
            messages=messages,
        )

    assert len(index.records_by_artifact_id) == 1
    record = next(iter(index.records_by_artifact_id.values()))
    assert record.tool_result_id == "call_big_result"
    assert record.recovery_unlocked_after_provider_commit is False
    assert messages[0]["content"] != content
    assert "<persisted-output>" in str(messages[0]["content"])
    assert record.artifact_id in str(messages[0]["content"])
    assert messages[0]["typed"]["single_tool_result_persisted"] is True
    assert messages[0]["typed"]["single_tool_result_original_chars"] == len(content)
    assert messages[0]["artifact_refs"][0]["kind"] == "tool_result_original_content"


def test_record_tool_result_does_not_persist_recovery_tool_result(tmp_path: Path):
    run_dir = tmp_path / "run"
    messages: list[dict[str, object]] = []
    state = AgentLoopState(
        run_id="recovery-tool-budget",
        task_id="task",
        messages=messages,
        budget_state=BudgetState(started_at="2026-05-10T00:00:00+00:00"),
    )
    content = "recovered artifact content\n" * 20
    tool_result = ToolResult(
        tool_result_id="call_recover_result",
        tool_call_id="call_recover",
        tool_name="read_tool_result_artifact",
        requested_tool_name="read_tool_result_artifact",
        effective_tool_name="read_tool_result_artifact",
        normalized_input_hash=stable_hash({"artifact_id": "tool-result/example"}),
        status="ok",
        content_preview=content,
    )
    with RunRecorder("recovery-tool-budget", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _record_tool_result(
            tool_result_artifact_index=index,
            context_config=ContextManagementConfig(max_single_tool_result_chars=1),
            run_id="recovery-tool-budget",
            task_id="task",
            turn=1,
            tool_result=tool_result,
            state=state,
            recorder=recorder,
            messages=messages,
        )

    assert index.records_by_artifact_id == {}
    assert messages[0]["content"] == content
    assert messages[0]["typed"].get("single_tool_result_persisted") is None


def test_interrupted_tool_calls_use_single_tool_result_budget(tmp_path: Path):
    run_dir = tmp_path / "run"
    messages: list[dict[str, object]] = []
    state = AgentLoopState(
        run_id="interrupted-tool-budget",
        task_id="task",
        messages=messages,
        budget_state=BudgetState(started_at="2026-05-10T00:00:00+00:00"),
    )
    calls = [
        ToolCall(
            tool_call_id="call_remaining",
            tool_name="read_file",
            arguments={"path": "demo.py"},
            turn=1,
        )
    ]
    with RunRecorder("interrupted-tool-budget", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _record_interrupted_tool_calls(
            tool_result_artifact_index=index,
            context_config=ContextManagementConfig(max_single_tool_result_chars=10),
            run_id="interrupted-tool-budget",
            task_id="task",
            turn=1,
            tool_calls=calls,
            reason="max_tool_calls",
            state=state,
            recorder=recorder,
            messages=messages,
            emit_tool_requested=False,
        )

    assert len(index.records_by_artifact_id) == 1
    record = next(iter(index.records_by_artifact_id.values()))
    assert record.tool_result_id == "call_remaining_result"
    assert messages[0]["tool_call_id"] == "call_remaining"
    assert "<persisted-output>" in str(messages[0]["content"])
    assert record.artifact_id in str(messages[0]["content"])
    assert messages[0]["typed"]["single_tool_result_persisted"] is True
    assert messages[0]["artifact_refs"][0]["kind"] == "tool_result_original_content"


def test_agent_loop_calls_model_with_model_request_context(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RecordingClient()
    with RunRecorder("request-context", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="request-context",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.agent_stop_reason == "final_answer"
    assert client.request is not None
    assert client.request.model_call_id == "request-context_model_call_0001"
    assert client.request.turn == 1
    assert client.request.scaffold_phase == "act"
    assert client.request.budget_state["turn_count"] == 1
    assert [tool["name"] for tool in client.request.allowed_tool_definitions] == ["read_file"]
    assert client.request.provider_request_projection_hash is not None
    assert client.request.provider_request_token_estimate > 0
    assert client.request.context_budget_facts["effective_context_budget_tokens"] == 120000
    events = _read_events(run_dir)
    started = next(event for event in events if event["event_type"] == "model_call_started")
    assert started["data"]["scaffold_phase"] == "act"
    assert started["data"]["budget_state"]["turn_count"] == 1
    assert started["data"]["provider_request_projection_hash"] == (
        client.request.provider_request_projection_hash
    )


def test_agent_loop_accepts_model_input_before_freezing_tool_result_decisions(tmp_path: Path):
    run_dir = tmp_path / "run"
    initial_messages = [
        {
            "role": "assistant",
            "content": "call tool",
            "turn": 1,
            "tool_calls": [
                {
                    "tool_call_id": "call_large",
                    "tool_name": "grep",
                    "arguments": {"query": "needle"},
                    "turn": 1,
                }
            ],
        },
        {
            "role": "tool",
            "turn": 1,
            "tool_call_id": "call_large",
            "tool_result_id": "call_large_result",
            "tool_name": "grep",
            "content": "large tool output\n" * 80,
            "normalized_arguments": {"query": "needle"},
            "normalized_input_hash": stable_hash({"query": "needle"}),
            "status": "ok",
            "typed": {},
            "artifact_refs": [],
        },
    ]

    with RunRecorder("accepted-input", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="accepted-input",
                task_id="task",
                steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
            ),
            tool_executor=ToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="accepted-input",
            task_id="task",
            initial_messages=initial_messages,
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10),
        )

    assert state.agent_stop_reason == "final_answer"
    events = _read_events(run_dir)
    accepted = next(event for event in events if event["event_type"] == "model_input_accepted")
    assert accepted["data"]["committed_persisted_preview_tool_result_ids"] == [
        "call_large_result"
    ]
    assert accepted["data"]["committed_full_visible_tool_result_ids"] == []
    assert accepted["data"]["model_input_hash"]
    assert accepted["data"]["model_call_id"] == "accepted-input_model_call_0001"
    snapshot_ref = accepted["data"]["model_input_snapshot_ref"]
    snapshot = _read_artifact_payload(run_dir, snapshot_ref)
    assert snapshot["schema_version"] == "repo_harness_model_input_snapshot_v1"
    assert snapshot["model_call_id"] == "accepted-input_model_call_0001"
    assert snapshot["prepared_messages_ref"]["kind"] == "prepared_messages"
    assert snapshot["model_input_hash"] == accepted["data"]["model_input_hash"]
    assert snapshot["provider_request_projection_hash"] == (
        accepted["data"]["provider_request_projection_hash"]
    )
    assert snapshot["provider_request_artifact_ref"]["kind"] == "raw_replay_request"
    assert snapshot["provider_response_artifact_ref"]["kind"] == "raw_replay_response"
    assert snapshot["context_compact_state_ref"] == accepted["data"][
        "content_replacement_state_ref"
    ]
    assert snapshot["trainable"] is True
    artifact_kinds = [artifact["kind"] for artifact in _read_artifacts(run_dir)]
    assert "model_input_snapshot" in artifact_kinds


def test_agent_loop_does_not_freeze_tool_result_decisions_on_provider_context_limit(
    tmp_path: Path,
):
    run_dir = tmp_path / "run"
    initial_messages = [
        {
            "role": "assistant",
            "content": "call tool",
            "turn": 1,
            "tool_calls": [
                {
                    "tool_call_id": "call_large",
                    "tool_name": "grep",
                    "arguments": {"query": "needle"},
                    "turn": 1,
                }
            ],
        },
        {
            "role": "tool",
            "turn": 1,
            "tool_call_id": "call_large",
            "tool_result_id": "call_large_result",
            "tool_name": "grep",
            "content": "large tool output\n" * 80,
            "normalized_arguments": {"query": "needle"},
            "normalized_input_hash": stable_hash({"query": "needle"}),
            "status": "ok",
            "typed": {},
            "artifact_refs": [],
        },
    ]

    with RunRecorder("rejected-input", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="rejected-input",
                task_id="task",
                steps=[
                    {
                        "step_id": "context-limit",
                        "action": "model_error",
                        "model_error_type": "context_limit",
                    }
                ],
            ),
            tool_executor=ToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="rejected-input",
            task_id="task",
            initial_messages=initial_messages,
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10),
        )

    events = _read_events(run_dir)
    assert state.last_model_error == "context_limit"
    assert not any(event["event_type"] == "model_input_accepted" for event in events)
    assert not any(
        artifact["kind"] == "model_input_snapshot" for artifact in _read_artifacts(run_dir)
    )


def test_agent_loop_repairs_one_malformed_tool_call_response(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _MalformedThenFinalClient()
    with RunRecorder("tool-repair", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="tool-repair",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
        )

    assert state.agent_stop_reason == "final_answer"
    assert len(client.requests) == 2
    assert "tool call 结构不合法" in str(client.requests[1].prepared_messages[-1]["content"])
    events = _read_events(run_dir)
    assert any(event["event_type"] == "tool_call_repair_requested" for event in events)


def test_agent_loop_binds_provider_retry_attempt_refs_in_model_event(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RetryMetadataClient()
    with RunRecorder("retry-event", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="retry-event",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.agent_stop_reason == "final_answer"
    events = _read_events(run_dir)
    completed = next(event for event in events if event["event_type"] == "model_call_completed")
    assert completed["data"]["attempt_count"] == 2
    assert completed["data"]["retry_count"] == 1
    assert len(completed["data"]["provider_attempt_refs"]) == 2
    assert completed["data"]["retry_policy_ref"] is not None
    for ref in completed["data"]["provider_attempt_refs"]:
        assert (run_dir / ref["relative_path"]).exists()


def test_agent_loop_marks_repeated_malformed_tool_call_unrecovered(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _AlwaysMalformedClient()
    with RunRecorder("tool-repair-failed", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="tool-repair-failed",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
        )

    assert state.agent_stop_reason == "tool_call_parse_failure_unrecovered"
    assert state.last_model_error == "tool_call_parse_failure"
    events = _read_events(run_dir)
    assert sum(1 for event in events if event["event_type"] == "tool_call_repair_requested") == 1


def test_agent_loop_stops_before_provider_on_context_pairing_error(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RaisingClient()
    with RunRecorder("context-hard-gate", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="context-hard-gate",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"tool_call_id": "missing_result", "tool_name": "read_file", "arguments": {}}
                    ],
                },
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "context_integrity_error"
    assert state.last_model_error == "context_integrity_error"
    assert any(event["event_type"] == "context_integrity_error" for event in events)
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_stops_before_provider_on_interrupted_tool_result_block(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RaisingClient()
    with RunRecorder("context-block-order", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="context-block-order",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"tool_call_id": "call_read", "tool_name": "read_file", "arguments": {}}
                    ],
                },
                {"role": "user", "content": "interrupts tool result block"},
                {"role": "tool", "tool_call_id": "call_read", "tool_result_id": "call_read_result", "content": "late"},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    events = _read_events(run_dir)
    integrity = next(event for event in events if event["event_type"] == "context_integrity_error")
    assert state.agent_stop_reason == "context_integrity_error"
    assert integrity["data"]["tool_pairing_validation"]["out_of_order_tool_result_ids"] == [
        "call_read",
        "call_read",
    ]
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_preserves_safe_provider_private_metadata_for_next_turn(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _ProviderPrivateMetadataClient()
    with RunRecorder("provider-private", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="provider-private",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=2,
        )

    assert state.agent_stop_reason == "final_answer"
    assert len(client.requests) == 2
    second_messages = client.requests[1].prepared_messages
    assistant = next(message for message in second_messages if message.get("role") == "assistant")
    assert assistant["metadata"]["provider_private"]["deepseek"]["state_id"] == "state-1"
    assert assistant["metadata"]["provider_private"]["deepseek"]["redacted_state_ref"]["sha256"] == "a" * 64
    assert assistant["metadata"]["provider_private"]["deepseek"]["api_key"] == "<REDACTED_CREDENTIAL>"
    message_text = json.dumps(second_messages, ensure_ascii=False)
    assert "must be redacted before messages" not in message_text
    assert '"reasoning_content":' not in message_text


def test_agent_loop_transcript_preserves_content_and_tool_calls(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _ContentAndToolCallClient()
    with RunRecorder("content-tool", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="content-tool",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.agent_stop_reason == "max_turns"
    transcript = [
        json.loads(line)
        for line in (run_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assistant = next(record for record in transcript if record["role"] == "assistant")
    assert "I will inspect the file first." in assistant["content_preview"]
    assert "tool_calls=" in assistant["content_preview"]
    artifact_ref = assistant["content_artifact_refs"][0]
    payload = json.loads((run_dir / artifact_ref["relative_path"]).read_text(encoding="utf-8"))
    assert payload["content"] == "I will inspect the file first."
    assert payload["tool_calls"][0]["tool_name"] == "unknown_tool"


def test_agent_loop_clears_provider_private_state_after_run(tmp_path: Path):
    store = provider_private_state_store()
    state_record = store.put_deepseek_reasoning(
        run_id="provider-private-cleanup",
        model_call_id="provider-private-cleanup_model_call_0001",
        reasoning_content="live private state",
    )
    run_dir = tmp_path / "run"

    with RunRecorder("provider-private-cleanup", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="cleanup",
                task_id="task",
                steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
            ),
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="provider-private-cleanup",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.agent_stop_reason == "final_answer"
    assert store.get_deepseek_reasoning(state_record.state_id) is None


def test_agent_loop_clears_provider_private_state_after_exception(tmp_path: Path):
    store = provider_private_state_store()
    state_record = store.put_deepseek_reasoning(
        run_id="provider-private-exception-cleanup",
        model_call_id="provider-private-exception-cleanup_model_call_0001",
        reasoning_content="live private state",
    )
    run_dir = tmp_path / "run"

    with pytest.raises(RuntimeError, match="provider failed unexpectedly"):
        with RunRecorder("provider-private-exception-cleanup", run_dir, task_id="task") as recorder:
            AgentLoop(
                model_client=_RaisingClient(),
                tool_executor=ToolExecutor(),
                allowed_tool_names=["read_file"],
            ).run(
                run_id="provider-private-exception-cleanup",
                task_id="task",
                initial_messages=[{"role": "system", "content": "system"}],
                tool_context=None,  # type: ignore[arg-type]
                recorder=recorder,
                max_turns=1,
            )

    assert store.get_deepseek_reasoning(state_record.state_id) is None


def test_agent_loop_rejects_empty_no_tool_response(tmp_path: Path):
    state = _run_loop(
        tmp_path,
        steps=[{"step_id": "empty", "action": "assistant"}],
    )

    assert state.agent_stop_reason == "model_error"
    assert state.last_model_error == "invalid_final_answer"


def test_agent_loop_scaffold_allowed_tools_block_disallowed_known_tool(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="restricted",
        task_id="task",
        steps=[
            {
                "step_id": "diff",
                "action": "tool_call",
                "tool_call_id": "call_diff",
                "tool_name": "git_diff",
                "arguments": {},
            },
            {"step_id": "final", "action": "final_answer", "assistant_text": "done"},
        ],
    )

    with RunRecorder("restricted", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
        ).run(
            run_id="restricted",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=2,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "final_answer"
    assert any(event["event_type"] == "tool_not_allowed" for event in events)
    assert not any(event["event_type"] == "permission_decision" for event in events)


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


def test_agent_loop_pairs_tool_calls_returned_with_model_error(tmp_path: Path):
    run_dir = tmp_path / "run"
    with RunRecorder("model-error-tools", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=_ModelErrorWithToolCallsClient(),
            tool_executor=ToolExecutor(),
        ).run(
            run_id="model-error-tools",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "model_error"
    assert state.last_model_error == "provider_error"
    assert any(
        event["event_type"] == "tool_interrupted"
        and event["data"]["tool_call_id"] == "call_after_error"
        and event["data"]["error_type"] == "provider_error"
        for event in events
    )
    _assert_tool_events_are_paired(events)


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


def test_agent_loop_records_no_progress_diagnostics_without_hard_stop(tmp_path: Path):
    run_dir = tmp_path / "run"
    budget = BudgetManager(
        max_turns=12,
        max_tool_calls=20,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    client = _RepeatedGrepClient()
    with RunRecorder("no-progress", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="no-progress",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=budget.max_turns,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    _assert_tool_events_are_paired(events)
    diagnostic_events = [
        event for event in events if event["event_type"] == "loop_progress_diagnostic"
    ]
    nudge_events = [
        event for event in events if event["event_type"] == "convergence_nudge_injected"
    ]
    signal_keys = {
        signal["signal_key"]
        for event in diagnostic_events
        for signal in event["data"]["signals"]
    }

    assert state.agent_stop_reason == "max_turns"
    assert diagnostic_events
    assert {
        "long_read_only_streak",
        "repeated_tool_input",
        "empty_search_accumulation",
        "near_turn_budget_without_patch",
    }.issubset(signal_keys)
    assert all(event["data"]["hard_stop_enabled"] is False for event in diagnostic_events)
    assert all(event["data"]["agent_stop_reason_changed"] is False for event in diagnostic_events)
    assert any(event["data"]["model_visible_message_injected"] is True for event in diagnostic_events)
    assert nudge_events
    nudge_levels = {event["data"]["nudge_level"] for event in nudge_events}
    assert "exploration_no_progress" in nudge_levels
    assert "near_budget_patch_or_stop" in nudge_levels
    assert all(event["data"]["trainable"] is False for event in nudge_events)
    assert all(event["data"]["resolved_trainable"] is False for event in nudge_events)
    assert all(event["data"]["inserted_after_all_tool_results"] is True for event in nudge_events)
    near_budget_nudge = next(
        event for event in nudge_events if event["data"]["nudge_level"] == "near_budget_patch_or_stop"
    )
    assert near_budget_nudge["data"]["has_patch"] is False
    assert near_budget_nudge["data"]["turns_remaining"] <= 6
    first_nudge = nudge_events[0]
    same_turn_event_types = [
        event["event_type"] for event in events if event.get("turn") == first_nudge["turn"]
    ]
    assert same_turn_event_types.index("tool_completed") < same_turn_event_types.index(
        "loop_progress_diagnostic"
    )
    assert same_turn_event_types.index("loop_progress_diagnostic") < same_turn_event_types.index(
        "convergence_nudge_injected"
    )
    transcript = [
        json.loads(line)
        for line in (run_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    nudge_records = [
        record for record in transcript if record["message_id"].startswith("convergence_nudge_")
    ]
    assert nudge_records
    assert all(record["model_visible"] is True for record in nudge_records)
    assert all(record["trainable"] is False for record in nudge_records)
    nudge_text = json.dumps(nudge_records, ensure_ascii=False).lower()
    assert "hidden" not in nudge_text
    assert "gold" not in nudge_text
    assert "selector" not in nudge_text
    assert any(
        "convergence_nudge" in json.dumps(request.prepared_messages, ensure_ascii=False)
        for request in client.requests[1:]
    )
    assert state.loop_diagnostics
    assert state.loop_diagnostics_summary["diagnostic_status"] == "no_progress_suspected"
    assert state.loop_diagnostics_summary["patch_tool_call_count"] == 0
    assert state.loop_diagnostics_summary["read_only_tool_call_count"] == 12


def test_agent_loop_does_not_inject_convergence_nudge_on_final_turn(tmp_path: Path):
    run_dir = tmp_path / "run"
    budget = BudgetManager(
        max_turns=3,
        max_tool_calls=20,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )

    with RunRecorder("no-progress-final-turn", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=_RepeatedGrepClient(),
            tool_executor=_NoProgressToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="no-progress-final-turn",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=budget.max_turns,
            budget_manager=budget,
        )

    events = _read_events(run_dir)
    diagnostic_events = [
        event for event in events if event["event_type"] == "loop_progress_diagnostic"
    ]

    assert state.agent_stop_reason == "max_turns"
    assert diagnostic_events
    assert not any(event["event_type"] == "convergence_nudge_injected" for event in events)
    assert all(
        event["data"]["model_visible_message_injected"] is False
        for event in diagnostic_events
    )


def test_agent_loop_no_progress_summary_resets_after_patch_progress(tmp_path: Path):
    run_dir = tmp_path / "run"

    with RunRecorder("no-progress-reset", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=_SearchThenPatchClient(),
            tool_executor=_NoProgressThenPatchToolExecutor(),
            allowed_tool_names=["grep", "edit_file"],
        ).run(
            run_id="no-progress-reset",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=10,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "final_answer"
    assert any(event["event_type"] == "loop_progress_diagnostic" for event in events)
    assert state.loop_diagnostics_summary["diagnostic_status"] == "ok"
    assert state.loop_diagnostics_summary["patch_tool_call_count"] == 1
    assert state.loop_diagnostics_summary["read_only_tool_call_count"] == 0
    assert state.loop_diagnostics_summary["total_read_only_tool_call_count"] == 4
    assert state.loop_diagnostics_summary["analysis_window_started_after_patch_tool_call"] is True


def test_agent_loop_no_progress_events_can_recur_after_patch_progress(tmp_path: Path):
    run_dir = tmp_path / "run"

    with RunRecorder("no-progress-recur", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=_SearchPatchThenSearchClient(),
            tool_executor=_NoProgressThenPatchToolExecutor(),
            allowed_tool_names=["grep", "edit_file"],
        ).run(
            run_id="no-progress-recur",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=10,
        )

    diagnostic_events = [
        event for event in _read_events(run_dir) if event["event_type"] == "loop_progress_diagnostic"
    ]
    repeated_or_empty_events = [
        event
        for event in diagnostic_events
        if {
            "repeated_tool_input",
            "empty_search_accumulation",
        }.intersection(event["data"]["new_signal_keys"])
    ]

    assert state.agent_stop_reason == "final_answer"
    assert len(repeated_or_empty_events) >= 2
    assert repeated_or_empty_events[0]["data"]["diagnostic_dedupe_scope"] == "run_start"
    assert repeated_or_empty_events[-1]["data"]["diagnostic_dedupe_scope"] == "call_edit_result"
    assert state.loop_diagnostics_summary["diagnostic_status"] == "no_progress_suspected"
    assert state.loop_diagnostics_summary["analysis_window_started_after_patch_tool_call"] is True
    assert state.loop_diagnostics_summary["read_only_tool_call_count"] == 4


def test_agent_loop_near_budget_finalize_nudge_after_patch_is_not_blocked_by_earlier_nudge(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"

    with RunRecorder("near-budget-finalize", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=_SearchPatchThenSearchClient(),
            tool_executor=_NoProgressThenPatchToolExecutor(),
            allowed_tool_names=["grep", "edit_file", "git_diff"],
        ).run(
            run_id="near-budget-finalize",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=10,
        )

    nudge_events = [
        event for event in _read_events(run_dir) if event["event_type"] == "convergence_nudge_injected"
    ]
    levels = [event["data"]["nudge_level"] for event in nudge_events]

    assert state.agent_stop_reason == "final_answer"
    assert "exploration_no_progress" in levels
    assert "near_budget_finalize_patch" in levels
    finalize = next(
        event for event in nudge_events if event["data"]["nudge_level"] == "near_budget_finalize_patch"
    )
    assert finalize["data"]["has_patch"] is True
    assert finalize["data"]["turns_remaining"] <= 4
    assert finalize["data"]["post_nudge_action"] == "pending_observation"
    nudge_text = json.dumps(nudge_events, ensure_ascii=False).lower()
    assert "hidden" not in nudge_text
    assert "gold" not in nudge_text
    assert "selector" not in nudge_text


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
            context_config=ContextManagementConfig(auto_compact_enabled=False),
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "context_limit"
    assert any(event["event_type"] == "context_prepared" for event in events)
    assert any(event["event_type"] == "budget_exhausted" for event in events)
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_context_warning_reprepares_before_provider_call(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RequestListClient()
    budget = BudgetManager(
        max_turns=1,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=7000,
        max_output_tokens=4096,
    )

    with RunRecorder("context-warning", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="context-warning",
            task_id="task",
            initial_messages=[{"role": "system", "content": "x" * 10000}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
            context_config=ContextManagementConfig(auto_compact_enabled=False),
        )

    events = _read_events(run_dir)
    context_events = [event for event in events if event["event_type"] == "context_prepared"]
    warning_event = next(event for event in events if event["event_type"] == "context_warning_injected")
    model_event = next(event for event in events if event["event_type"] == "model_call_started")
    warning_index = events.index(warning_event)
    model_index = events.index(model_event)
    context_indices = [events.index(event) for event in context_events]

    assert state.agent_stop_reason == "final_answer"
    assert len(client.requests) == 1
    assert len(context_events) == 2
    assert context_indices[0] < warning_index < context_indices[1] < model_index
    assert warning_event["data"]["requires_prepare_messages_rerun"] is True
    assert warning_event["data"]["provider_request_created_before_warning"] is False
    assert model_event["data"]["context_revision"] == context_events[1]["data"]["context_revision"]
    assert "context_warning" in json.dumps(client.requests[0].prepared_messages, ensure_ascii=False)


def test_agent_loop_runs_auto_compact_before_main_model_call(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _AutoCompactThenFinalClient()
    config = ContextManagementConfig(
        model_context_window_tokens=12000,
        main_output_reserve_tokens=0,
        estimator_safety_margin_ratio=0.0,
        estimator_safety_margin_min_tokens=0,
        auto_compact_trigger_ratio=0.1,
        hard_context_limit_ratio=0.95,
        post_compact_target_max_tokens=2000,
    )

    with RunRecorder("loop-auto-compact", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-auto-compact",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {"role": "assistant", "turn": 1, "content": "old analysis " * 600},
                {"role": "user", "turn": 2, "content": "old follow up " * 600},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=config,
        )

    assert state.agent_stop_reason == "final_answer"
    assert state.auto_compact_count == 1
    assert state.auto_compact_consecutive_failures == 0
    assert len(client.requests) == 2
    assert client.requests[0].scaffold_phase == "compact"
    assert client.requests[0].allowed_tool_definitions == []
    assert client.requests[0].tool_choice == "none"
    assert client.requests[1].model_call_id == "loop-auto-compact_model_call_0001"
    main_messages = json.dumps(client.requests[1].prepared_messages, ensure_ascii=False)
    assert "repo_harness_auto_compact_boundary" in main_messages
    assert "repo_harness_auto_compact_summary" in main_messages
    assert "old analysis " not in main_messages

    events = _read_events(run_dir)
    event_types = [event["event_type"] for event in events]
    assert "auto_compact_triggered" in event_types
    assert "auto_compact_applied" in event_types
    assert "context_post_compact_prepared" in event_types
    model_started = next(event for event in events if event["event_type"] == "model_call_started")
    post_prepared = next(
        event for event in events if event["event_type"] == "context_post_compact_prepared"
    )
    assert model_started["data"]["prepared_messages_ref"] == post_prepared["data"]["prepared_messages_ref"]


def test_agent_loop_reactive_compact_retries_provider_context_limit_without_history_pollution(
    tmp_path: Path,
):
    run_dir = tmp_path / "run"
    client = _ReactiveContextLimitThenFinalClient()

    with RunRecorder("loop-reactive-compact", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-reactive-compact",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {"role": "assistant", "turn": 1, "content": "old analysis " * 400},
                {"role": "user", "turn": 2, "content": "old follow up " * 400},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            context_config=ContextManagementConfig(
                model_context_window_tokens=12000,
                main_output_reserve_tokens=0,
                estimator_safety_margin_ratio=0.0,
                estimator_safety_margin_min_tokens=0,
                auto_compact_trigger_ratio=0.99,
                reactive_compact_enabled=True,
                reactive_compact_retry_limit=1,
            ),
        )

    assert state.agent_stop_reason == "final_answer"
    assert state.reactive_compact_count == 1
    assert state.reactive_compact_retry_count == 1
    assert [request.scaffold_phase for request in client.requests] == ["act", "compact", "act"]
    retry_messages = json.dumps(client.requests[-1].prepared_messages, ensure_ascii=False)
    assert "repo_harness_auto_compact_summary" in retry_messages
    assert "provider context limit rejected this input" not in retry_messages

    events = _read_events(run_dir)
    event_types = [event["event_type"] for event in events]
    assert "reactive_compact_triggered" in event_types
    assert "reactive_compact_applied" in event_types
    assert not any(
        event["event_type"] == "model_input_accepted"
        and event["data"].get("model_call_id") == "loop-reactive-compact_model_call_0001"
        for event in events
    )
    transcript_text = (run_dir / "transcript.jsonl").read_text(encoding="utf-8")
    assert "provider context limit rejected this input" not in transcript_text
    assistant_artifacts = [
        artifact for artifact in _read_artifacts(run_dir) if artifact["kind"] == "assistant_message"
    ]
    assert assistant_artifacts
    assert all(
        "provider context limit rejected this input"
        not in json.dumps(_read_artifact_payload(run_dir, artifact), ensure_ascii=False)
        for artifact in assistant_artifacts
    )


def test_agent_loop_reactive_compact_retry_can_run_on_last_ordinary_turn(
    tmp_path: Path,
):
    run_dir = tmp_path / "run"
    client = _ReactiveContextLimitThenFinalClient()

    with RunRecorder("loop-reactive-last-turn", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-reactive-last-turn",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=ContextManagementConfig(
                model_context_window_tokens=12000,
                main_output_reserve_tokens=0,
                estimator_safety_margin_ratio=0.0,
                estimator_safety_margin_min_tokens=0,
                auto_compact_trigger_ratio=0.99,
                reactive_compact_enabled=True,
                reactive_compact_retry_limit=1,
            ),
        )

    assert state.agent_stop_reason == "final_answer"
    assert state.turn_count == 1
    assert state.reactive_compact_retry_count == 1
    assert [request.model_call_id for request in client.requests if request.scaffold_phase == "act"] == [
        "loop-reactive-last-turn_model_call_0001",
        "loop-reactive-last-turn_model_call_0002",
    ]
    events = _read_events(run_dir)
    assert any(event["event_type"] == "reactive_compact_applied" for event in events)
    accepted_model_call_ids = [
        event["data"].get("model_call_id")
        for event in events
        if event["event_type"] == "model_input_accepted"
    ]
    assert accepted_model_call_ids == ["loop-reactive-last-turn_model_call_0002"]


def test_agent_loop_ptl_fallback_drops_complete_old_round_after_emergency_compact_failure(
    tmp_path: Path,
):
    run_dir = tmp_path / "run"
    client = _ReactiveContextLimitEmergencyFailThenFinalClient()

    with RunRecorder("loop-ptl-fallback", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="loop-ptl-fallback",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {
                    "role": "assistant",
                    "content": None,
                    "turn": 1,
                    "tool_calls": [
                        {
                            "tool_call_id": "call_old",
                            "tool_name": "grep",
                            "arguments": {"query": "old"},
                            "turn": 1,
                        }
                    ],
                },
                {
                    "role": "tool",
                    "turn": 1,
                    "tool_call_id": "call_old",
                    "tool_result_id": "call_old_result",
                    "tool_name": "grep",
                    "content": "old provider-visible tool output " * 300,
                    "normalized_arguments": {"query": "old"},
                    "normalized_input_hash": stable_hash({"query": "old"}),
                    "status": "ok",
                    "typed": {},
                    "artifact_refs": [],
                },
                {"role": "user", "content": "Recent visible requirement."},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            context_config=ContextManagementConfig(
                model_context_window_tokens=12000,
                main_output_reserve_tokens=0,
                estimator_safety_margin_ratio=0.0,
                estimator_safety_margin_min_tokens=0,
                auto_compact_trigger_ratio=0.99,
                reactive_compact_enabled=True,
                reactive_compact_retry_limit=1,
                ptl_retry_policy="auto_compact_then_round_truncate",
            ),
        )

    assert state.agent_stop_reason == "final_answer"
    assert state.reactive_compact_count == 1
    assert state.ptl_truncation_count == 1
    assert [request.scaffold_phase for request in client.requests] == ["act", "compact", "act"]
    retry_messages = json.dumps(client.requests[-1].prepared_messages, ensure_ascii=False)
    assert "repo_harness_ptl_truncation_marker" in retry_messages
    assert "old provider-visible tool output" not in retry_messages
    assert "call_old" not in retry_messages
    assert "Recent visible requirement." in retry_messages

    events = _read_events(run_dir)
    assert any(event["event_type"] == "ptl_truncation_applied" for event in events)
    ptl_event = next(event for event in events if event["event_type"] == "ptl_truncation_applied")
    ptl_record = _read_artifact_payload(run_dir, ptl_event["data"]["ptl_truncation_ref"])
    assert state.last_ptl_truncation_ref == ptl_event["data"]["ptl_truncation_ref"]
    assert ptl_event["data"]["original_model_call_id"] == "loop-ptl-fallback_model_call_0001"
    assert ptl_event["data"]["recovery_retry_index"] == 1
    assert ptl_event["data"]["token_estimate_before"] > ptl_event["data"]["token_estimate_after"]
    assert ptl_event["data"]["synthetic_marker_id"] == ptl_record["synthetic_marker_id"]
    assert ptl_record["schema_version"] == "repo_harness_ptl_truncation_record_v1"
    assert ptl_record["policy"] == "auto_compact_then_round_truncate"
    assert ptl_record["reason"] == "provider_context_limit_retry"
    assert ptl_record["original_model_call_id"] == "loop-ptl-fallback_model_call_0001"
    assert ptl_record["original_prepared_messages_ref"]["kind"] == "prepared_messages"
    assert ptl_record["original_model_input_hash"]
    assert ptl_record["original_provider_request_ref"]["kind"] == "raw_provider_request"
    assert ptl_record["original_provider_response_ref"]["kind"] == "raw_provider_response"
    assert ptl_record["emergency_compact_record_ref"]["kind"] == "auto_compact_record"
    assert "invalid_compact_summary" in ptl_record["emergency_compact_failure_reason"]
    assert ptl_record["synthetic_marker_message"]["role"] == "user"
    marker_text = json.dumps(ptl_record["synthetic_marker_message"], ensure_ascii=False)
    assert "repo_harness_ptl_truncation_marker" in marker_text
    assert "provider context limit rejected this input" not in marker_text
    assert ptl_record["omitted_round_count"] == 1
    assert ptl_record["retained_round_count"] >= 1
    assert ptl_record["message_count_before"] > ptl_record["message_count_after"]
    assert ptl_record["token_estimate_before"] > ptl_record["token_estimate_after"]
    assert ptl_record["hard_context_limit_tokens"] > 0
    assert isinstance(ptl_record["post_truncation_above_hard_limit"], bool)
    assert ptl_record["tool_pairing_preservation_policy"] == "drop_complete_rounds_only_v1"
    assert ptl_record["omitted_rounds"][0]["roles"] == ["assistant", "tool"]
    assert "call_old" in ptl_record["omitted_rounds"][0]["tool_call_ids"]
    accepted_model_call_ids = [
        event["data"].get("model_call_id")
        for event in events
        if event["event_type"] == "model_input_accepted"
    ]
    assert accepted_model_call_ids == ["loop-ptl-fallback_model_call_0002"]


def test_agent_loop_ptl_retry_stops_when_retry_still_hits_context_limit(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _ReactiveContextLimitEmergencyFailThenContextLimitClient()

    with RunRecorder("loop-ptl-fallback-second-limit", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["grep"],
        ).run(
            run_id="loop-ptl-fallback-second-limit",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {
                    "role": "assistant",
                    "content": None,
                    "turn": 1,
                    "tool_calls": [
                        {
                            "tool_call_id": "call_old",
                            "tool_name": "grep",
                            "arguments": {"query": "old"},
                            "turn": 1,
                        }
                    ],
                },
                {
                    "role": "tool",
                    "turn": 1,
                    "tool_call_id": "call_old",
                    "tool_result_id": "call_old_result",
                    "tool_name": "grep",
                    "content": "old provider-visible tool output " * 300,
                    "normalized_arguments": {"query": "old"},
                    "normalized_input_hash": stable_hash({"query": "old"}),
                    "status": "ok",
                    "typed": {},
                    "artifact_refs": [],
                },
                {"role": "user", "content": "Recent visible requirement."},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            context_config=ContextManagementConfig(
                model_context_window_tokens=12000,
                main_output_reserve_tokens=0,
                estimator_safety_margin_ratio=0.0,
                estimator_safety_margin_min_tokens=0,
                auto_compact_trigger_ratio=0.99,
                reactive_compact_enabled=True,
                reactive_compact_retry_limit=1,
                ptl_retry_policy="auto_compact_then_round_truncate",
            ),
        )

    assert state.agent_stop_reason == "context_limit_after_reactive_compact"
    assert state.ptl_truncation_count == 1
    events = _read_events(run_dir)
    assert any(event["event_type"] == "ptl_truncation_applied" for event in events)
    assert any(
        event["event_type"] == "reactive_compact_retry_limit_exhausted"
        for event in events
    )
    assert not any(event["event_type"] == "model_input_accepted" for event in events)
    assert not any(
        artifact["kind"] == "model_input_snapshot" for artifact in _read_artifacts(run_dir)
    )


def test_agent_loop_stops_on_second_context_limit_after_reactive_compact(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _ReactiveContextLimitThenContextLimitClient()

    with RunRecorder("loop-reactive-compact-second-limit", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-reactive-compact-second-limit",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            context_config=ContextManagementConfig(
                model_context_window_tokens=12000,
                main_output_reserve_tokens=0,
                estimator_safety_margin_ratio=0.0,
                estimator_safety_margin_min_tokens=0,
                auto_compact_trigger_ratio=0.99,
                reactive_compact_enabled=True,
                reactive_compact_retry_limit=1,
            ),
        )

    assert state.agent_stop_reason == "context_limit_after_reactive_compact"
    events = _read_events(run_dir)
    assert any(
        event["event_type"] == "reactive_compact_retry_limit_exhausted"
        for event in events
    )


def test_agent_loop_does_not_append_context_limit_when_reactive_compact_disabled(
    tmp_path: Path,
):
    run_dir = tmp_path / "run"
    client = _ContextLimitOnlyClient()

    with RunRecorder("loop-reactive-disabled", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-reactive-disabled",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=ContextManagementConfig(reactive_compact_enabled=False),
        )

    assert state.agent_stop_reason == "context_limit_reactive_compact_disabled"
    assert len(state.messages) == 1
    assert "provider context limit rejected this input" not in json.dumps(
        state.messages,
        ensure_ascii=False,
    )
    assert not any(
        event["event_type"] == "model_input_accepted" for event in _read_events(run_dir)
    )


def test_agent_loop_continues_after_auto_compact_failure_below_hard_limit(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _AutoCompactThenFinalClient(compact_content="not json")
    config = ContextManagementConfig(
        model_context_window_tokens=12000,
        main_output_reserve_tokens=0,
        estimator_safety_margin_ratio=0.0,
        estimator_safety_margin_min_tokens=0,
        auto_compact_trigger_ratio=0.1,
        hard_context_limit_ratio=0.95,
        post_compact_target_max_tokens=2000,
    )

    with RunRecorder("loop-auto-compact-fail-soft", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-auto-compact-fail-soft",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {"role": "assistant", "turn": 1, "content": "old analysis " * 600},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=config,
        )

    assert state.agent_stop_reason == "final_answer"
    assert state.auto_compact_count == 0
    assert state.auto_compact_consecutive_failures == 1
    assert len(client.requests) == 2
    assert client.requests[0].scaffold_phase == "compact"
    assert client.requests[1].scaffold_phase == "act"
    events = _read_events(run_dir)
    assert any(event["event_type"] == "auto_compact_failed" for event in events)
    assert any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_stops_when_auto_compact_fails_above_hard_limit(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _AutoCompactThenFinalClient()
    config = ContextManagementConfig(
        model_context_window_tokens=1000,
        main_output_reserve_tokens=0,
        estimator_safety_margin_ratio=0.0,
        estimator_safety_margin_min_tokens=0,
        auto_compact_trigger_ratio=0.2,
        hard_context_limit_ratio=0.3,
        post_compact_target_max_tokens=800,
    )

    with RunRecorder("loop-auto-compact-fail-hard", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
        ).run(
            run_id="loop-auto-compact-fail-hard",
            task_id="task",
            initial_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "Fix the bug."},
                {"role": "assistant", "turn": 1, "content": "old analysis " * 2000},
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            context_config=config,
        )

    assert state.agent_stop_reason == "auto_compact_failed_preflight"
    assert client.requests == []
    events = _read_events(run_dir)
    assert any(event["event_type"] == "auto_compact_failed" for event in events)
    assert not any(event["event_type"] == "model_call_started" for event in events)
    exhausted = next(event for event in events if event["event_type"] == "budget_exhausted")
    assert exhausted["error_type"] == "auto_compact_failed_preflight"


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


def test_agent_loop_uses_external_task_deadline_before_model_call(tmp_path: Path):
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
    )

    with RunRecorder("external-deadline", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=FakeModelClient.from_steps(
                script_id="external-deadline",
                task_id="task",
                steps=[{"step_id": "final", "action": "final_answer", "assistant_text": "done"}],
            ),
            tool_executor=ToolExecutor(),
        ).run(
            run_id="external-deadline",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            budget_manager=budget,
            task_deadline_monotonic=time.monotonic() - 1,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "timeout"
    assert any(event["event_type"] == "budget_exhausted" for event in events)
    assert not any(event["event_type"] == "context_prepared" for event in events)
    assert not any(event["event_type"] == "model_call_started" for event in events)


def test_agent_loop_clamps_provider_request_timeout_to_remaining_deadline(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RequestListClient()

    with RunRecorder("deadline-clamp", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="deadline-clamp",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            task_deadline_monotonic=time.monotonic() + 30,
            request_timeout_seconds=2400,
            provider_timeout_grace_sec=2,
            min_provider_request_timeout_sec=5,
        )

    assert state.agent_stop_reason == "final_answer"
    assert len(client.requests) == 1
    request = client.requests[0]
    assert 20 <= request.request_timeout_seconds <= 28
    facts = request.request_timeout_policy_facts
    assert facts["task_deadline_monotonic_present"] is True
    assert facts["configured_request_timeout_seconds"] == 2400
    assert facts["provider_timeout_grace_sec"] == 2
    assert facts["absolute_deadline_enforced"] is True
    assert facts["effective_request_timeout_seconds"] <= 28


def test_agent_loop_skips_provider_call_when_deadline_too_close(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = _RequestListClient()

    with RunRecorder("deadline-skip", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="deadline-skip",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
            task_deadline_monotonic=time.monotonic() + 4,
            request_timeout_seconds=2400,
            provider_timeout_grace_sec=2,
            min_provider_request_timeout_sec=5,
        )

    events = _read_events(run_dir)
    assert state.agent_stop_reason == "timeout"
    assert client.requests == []
    assert any(
        event["event_type"] == "provider_call_skipped_due_to_task_deadline"
        and event["error_type"] == "task_timeout_before_provider_call"
        for event in events
    )
    exhausted = next(event for event in events if event["event_type"] == "budget_exhausted")
    assert exhausted["data"]["provider_call_skipped_due_to_task_deadline"] is True


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


def test_agent_loop_updates_structured_working_state(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="working-state",
        task_id="task",
        steps=[
            {
                "step_id": "state",
                "action": "tool_call",
                "tool_call_id": "call_state",
                "tool_name": "update_working_state",
                "arguments": {"next_action": "read parser"},
            }
        ],
    )

    with RunRecorder("working-state", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_WorkingStateExecutor(),
            allowed_tool_names=["update_working_state"],
        ).run(
            run_id="working-state",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.working_state is not None
    assert state.working_state["next_action"] == "read parser"
    assert state.tool_pairing_state.tool_result_ids["call_state"] == "call_state_result"


def test_agent_loop_records_tool_duration_on_event_and_result_payload(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="tool-duration",
        task_id="task",
        steps=[
            {
                "step_id": "state",
                "action": "tool_call",
                "tool_call_id": "call_state",
                "tool_name": "update_working_state",
                "arguments": {"next_action": "read parser"},
            }
        ],
    )

    with RunRecorder("tool-duration", run_dir, task_id="task") as recorder:
        AgentLoop(
            model_client=client,
            tool_executor=_WorkingStateExecutor(),
            allowed_tool_names=["update_working_state"],
        ).run(
            run_id="tool-duration",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    events = _read_events(run_dir)
    completed = next(event for event in events if event["event_type"] == "tool_completed")
    assert isinstance(completed["duration_ms"], int)
    assert completed["duration_ms"] >= 0
    assert completed["data"]["duration_ms"] == completed["duration_ms"]
    assert completed["data"]["typed"]["duration_ms"] == completed["duration_ms"]
    assert completed["data"]["typed"]["execution_duration_ms"] == completed["duration_ms"]


def test_agent_loop_does_not_update_working_state_from_error_result(tmp_path: Path):
    run_dir = tmp_path / "run"
    client = FakeModelClient.from_steps(
        script_id="working-state-error",
        task_id="task",
        steps=[
            {
                "step_id": "state_error",
                "action": "tool_call",
                "tool_call_id": "call_state_error",
                "tool_name": "update_working_state",
                "arguments": {"next_action": "read parser"},
            }
        ],
    )

    with RunRecorder("working-state-error", run_dir, task_id="task") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=_WorkingStateErrorExecutor(),
            allowed_tool_names=["update_working_state"],
        ).run(
            run_id="working-state-error",
            task_id="task",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=1,
        )

    assert state.working_state is None
    assert state.tool_pairing_state.tool_result_ids["call_state_error"] == "call_state_error_result"


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


class _WorkingStateExecutor(_MultiToolExecutor):
    def execute(self, tool_call, context):  # noqa: ANN001
        from repo_harness.tools import ToolResult
        from repo_harness.schema_base import stable_hash

        working_state = {
            "schema_version": "repo_harness_working_state_v0",
            "current_hypothesis": "",
            "candidate_files": [],
            "next_action": tool_call.arguments["next_action"],
            "completed_steps": [],
            "blocking_question": "",
            "skipped_candidate_file_count": 0,
            "policy_version": "repo_harness_update_working_state_v0",
        }
        return ToolResult(
            tool_result_id=f"{tool_call.tool_call_id}_result",
            tool_call_id=tool_call.tool_call_id,
            tool_name=tool_call.tool_name,
            requested_tool_name=tool_call.tool_name,
            effective_tool_name="update_working_state",
            requested_arguments=tool_call.arguments,
            normalized_arguments=tool_call.arguments,
            effective_arguments=tool_call.arguments,
            normalized_input_hash=stable_hash(tool_call.arguments),
            status="ok",
            content_preview="working_state_updated",
            typed={"status": "ok", "working_state": working_state},
        )


class _WorkingStateErrorExecutor(_WorkingStateExecutor):
    def execute(self, tool_call, context):  # noqa: ANN001
        result = super().execute(tool_call, context)
        return result.model_copy(
            update={
                "status": "error",
                "error_type": "working_state_empty",
                "content_preview": "working_state_empty",
            }
        )


class _RecordingClient:
    def __init__(self) -> None:
        self.request = None

    def generate(self, request, recorder):  # noqa: ANN001
        self.request = request
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _RequestListClient:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _AutoCompactThenFinalClient:
    def __init__(self, *, compact_content: str | None = None) -> None:
        self.requests = []
        self.compact_content = compact_content or json.dumps(
            {
                "schema_version": "repo_harness_compact_summary_v1",
                "task_intent": "Continue the task from visible context.",
                "repository_facts": ["The task is to fix a public bug."],
                "actions_taken": ["Earlier context was summarized."],
                "patch_state": {
                    "changed_files": [],
                    "important_diffs": [],
                },
                "test_state": {
                    "commands_run": [],
                    "passing": [],
                    "failing": [],
                    "unknown": ["Verification has not run yet."],
                },
                "tool_recovery_index": [],
                "open_questions": [],
                "next_step": "Inspect the relevant code and make the smallest fix.",
                "visibility_policy": "model_visible_only",
            }
        )

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        if request.scaffold_phase == "compact":
            raw_request_ref = recorder.write_json_artifact(
                "raw_auto_compact_test_request",
                {
                    "model_call_id": request.model_call_id,
                    "messages": request.prepared_messages,
                    "tools": request.allowed_tool_definitions,
                    "tool_choice": request.tool_choice,
                    "scaffold_phase": request.scaffold_phase,
                },
            )
            raw_response_ref = recorder.write_json_artifact(
                "raw_auto_compact_test_response",
                {"content": self.compact_content},
            )
            return ModelResponse(
                assistant_message=ModelMessage(role="assistant", content=self.compact_content),
                raw_provider_request_ref=raw_request_ref,
                raw_provider_response_ref=raw_response_ref,
                finish_reason="stop",
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _ReactiveContextLimitThenFinalClient(_AutoCompactThenFinalClient):
    def __init__(self) -> None:
        super().__init__()
        self.main_call_count = 0

    def generate(self, request, recorder):  # noqa: ANN001
        if request.scaffold_phase == "compact":
            return super().generate(request, recorder)
        self.requests.append(request)
        self.main_call_count += 1
        if self.main_call_count == 1:
            return _model_response_for_request(
                request,
                recorder,
                content="provider context limit rejected this input",
                finish_reason="error",
                model_error_type="context_limit",
            )
        return _model_response_for_request(
            request,
            recorder,
            content="done after reactive compact",
            finish_reason="stop",
            model_error_type=None,
        )


class _ReactiveContextLimitThenContextLimitClient(_ReactiveContextLimitThenFinalClient):
    def generate(self, request, recorder):  # noqa: ANN001
        if request.scaffold_phase == "compact":
            return _AutoCompactThenFinalClient.generate(self, request, recorder)
        self.requests.append(request)
        self.main_call_count += 1
        return _model_response_for_request(
            request,
            recorder,
            content="provider context limit rejected this input",
            finish_reason="error",
            model_error_type="context_limit",
        )


class _ReactiveContextLimitEmergencyFailThenFinalClient(_ReactiveContextLimitThenFinalClient):
    def __init__(self) -> None:
        super().__init__()
        self.compact_content = "not json"


class _ReactiveContextLimitEmergencyFailThenContextLimitClient(
    _ReactiveContextLimitThenContextLimitClient
):
    def __init__(self) -> None:
        super().__init__()
        self.compact_content = "not json"


class _ContextLimitOnlyClient:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, recorder):  # noqa: ANN001
        self.requests.append(request)
        return _model_response_for_request(
            request,
            recorder,
            content="provider context limit rejected this input",
            finish_reason="error",
            model_error_type="context_limit",
        )


class _MalformedThenFinalClient:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(
                assistant_message=ModelMessage(
                    role="assistant",
                    content="malformed tool call",
                    metadata={
                        "provider_error_message": "provider tool call arguments were not valid JSON"
                    },
                ),
                finish_reason="error",
                model_error_type="tool_call_parse_failure",
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _RetryMetadataClient:
    def generate(self, request, recorder):  # noqa: ANN001
        retry_policy_ref = recorder.write_json_artifact(
            "provider_retry_policy",
            {"policy_id": "provider_retry_no_sleep_v0", "max_attempts": 3},
        )
        first_attempt = recorder.write_json_artifact(
            "provider_attempt",
            {"attempt_index": 1, "retryable": True, "error_type": "rate_limited"},
        )
        second_attempt = recorder.write_json_artifact(
            "provider_attempt",
            {"attempt_index": 2, "retryable": False, "error_type": None},
        )
        raw_request_ref = recorder.write_json_artifact("raw_provider_request", {"body": {}})
        raw_response_ref = recorder.write_json_artifact("raw_provider_response", {"status": "ok"})
        event = ModelCallEvent(
            model_call_id=request.model_call_id,
            provider=request.provider_options.provider,
            model_id=request.provider_options.model_id,
            context_revision=request.context_revision,
            prepared_messages_ref=request.prepared_messages_ref,
            model_input_hash=request.model_input_hash,
            provider_message_format=request.provider_message_format,
            tool_schema_hash="1" * 64,
            attempt_count=2,
            retry_count=1,
            retry_policy_ref=retry_policy_ref,
        )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            raw_provider_request_ref=raw_request_ref,
            raw_provider_response_ref=raw_response_ref,
            provider_attempt_refs=[first_attempt, second_attempt],
            retry_policy_ref=retry_policy_ref,
            attempt_count=2,
            retry_count=1,
            finish_reason="stop",
            model_call_event=event,
        )


class _AlwaysMalformedClient:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        return ModelResponse(
            assistant_message=ModelMessage(
                role="assistant",
                content="malformed tool call",
                metadata={"provider_error_message": "provider tool call missing function name"},
            ),
            finish_reason="error",
            model_error_type="tool_call_parse_failure",
        )


class _ProviderPrivateMetadataClient:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(
                assistant_message=ModelMessage(
                    role="assistant",
                    content=None,
                    metadata={
                        "provider_private": {
                            "deepseek": {
                                "state_id": "state-1",
                                "redacted_state_ref": {"sha256": "a" * 64, "size_bytes": 123},
                                "api_key": "sk-test-provider-private-secret-1234567890",
                                "reasoning_content_required_for_replay": True,
                                "reasoning_content": "must be redacted before messages",
                            }
                        }
                    },
                ),
                tool_calls=[
                    ToolCall(
                        tool_call_id="call_unknown",
                        tool_name="unknown_tool",
                        arguments={},
                        turn=1,
                    )
                ],
                finish_reason="tool_calls",
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _ContentAndToolCallClient:
    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="I will inspect the file first."),
            tool_calls=[
                ToolCall(
                    tool_call_id="call_unknown",
                    tool_name="unknown_tool",
                    arguments={"path": "demo.py"},
                    turn=1,
                )
            ],
            finish_reason="tool_calls",
        )


class _RaisingClient:
    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        raise RuntimeError("provider failed unexpectedly")


class _ModelErrorWithToolCallsClient:
    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content=None),
            tool_calls=[
                ToolCall(
                    tool_call_id="call_after_error",
                    tool_name="read_file",
                    arguments={"path": "demo.py"},
                    turn=1,
                )
            ],
            finish_reason="tool_calls",
            model_error_type="provider_error",
        )


class _RepeatedGrepClient:
    def __init__(self) -> None:
        self.requests = []

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


class _SearchThenPatchClient:
    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        if request.turn <= 4:
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
        if request.turn == 5:
            return ModelResponse(
                assistant_message=ModelMessage(role="assistant", content=None),
                tool_calls=[
                    ToolCall(
                        tool_call_id="call_edit",
                        tool_name="edit_file",
                        arguments={
                            "path": "src/demo.py",
                            "old_text": "before",
                            "new_text": "after",
                        },
                        turn=request.turn,
                    )
                ],
                finish_reason="tool_calls",
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            finish_reason="stop",
        )


class _SearchPatchThenSearchClient:
    def generate(self, request, recorder):  # noqa: ANN001, ARG002
        if request.turn in {1, 2, 3, 4, 6, 7, 8, 9}:
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
        if request.turn == 5:
            return ModelResponse(
                assistant_message=ModelMessage(role="assistant", content=None),
                tool_calls=[
                    ToolCall(
                        tool_call_id="call_edit",
                        tool_name="edit_file",
                        arguments={
                            "path": "src/demo.py",
                            "old_text": "before",
                            "new_text": "after",
                        },
                        turn=request.turn,
                    )
                ],
                finish_reason="tool_calls",
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
            content_preview=(
                "No matches found after scanning all 0 model-visible files under root='src'."
            ),
            typed={
                "result_kind": "complete_no_match",
                "total_match_count": 0,
                "match_count": 0,
            },
        )


class _NoProgressThenPatchToolExecutor(_NoProgressToolExecutor):
    def execute(self, tool_call, context):  # noqa: ANN001, ARG002
        normalized = self.normalize(tool_call, context)
        if normalized.effective_tool_name == "edit_file":
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
                content_preview="Updated src/demo.py",
                typed={"status": "ok", "path": "src/demo.py"},
            )
        return super().execute(tool_call, context)


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


def _model_response_for_request(
    request,
    recorder,
    *,
    content: str,
    finish_reason: str,
    model_error_type: str | None,
) -> ModelResponse:
    raw_request_ref = recorder.write_json_artifact(
        "raw_provider_request",
        {
            "model_call_id": request.model_call_id,
            "prepared_messages_ref": request.prepared_messages_ref.model_dump(mode="json"),
            "model_input_hash": request.model_input_hash,
        },
    )
    raw_response_ref = recorder.write_json_artifact(
        "raw_provider_response",
        {
            "model_call_id": request.model_call_id,
            "content": content,
            "finish_reason": finish_reason,
            "model_error_type": model_error_type,
        },
    )
    event = ModelCallEvent(
        model_call_id=request.model_call_id,
        provider=request.provider_options.provider,
        model_id=request.provider_options.model_id,
        context_revision=request.context_revision,
        prepared_messages_ref=request.prepared_messages_ref,
        model_input_hash=request.model_input_hash,
        provider_message_format=request.provider_message_format,
        tool_schema_hash=stable_hash(request.allowed_tool_definitions),
        model_error_type=model_error_type,
    )
    return ModelResponse(
        assistant_message=ModelMessage(role="assistant", content=content),
        raw_provider_request_ref=raw_request_ref,
        raw_provider_response_ref=raw_response_ref,
        finish_reason=finish_reason,
        model_error_type=model_error_type,
        model_call_event=event,
    )


def _read_events(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_artifacts(run_dir: Path) -> list[dict]:
    return json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8")).get(
        "artifacts",
        [],
    )


def _read_artifact_payload(run_dir: Path, ref: dict) -> dict:
    return json.loads((run_dir / ref["relative_path"]).read_text(encoding="utf-8"))


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
