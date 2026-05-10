from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from repo_harness.agent_loop import AgentLoop
from repo_harness.agent_loop.loop import _record_tool_result
from repo_harness.agent_loop.schemas import AgentLoopState
from repo_harness.budget.schemas import BudgetState
from repo_harness.config import ContextManagementConfig
from repo_harness.context import (
    ContextManager,
    ToolResultArtifactIndex,
    read_tool_result_artifact,
)
from repo_harness.export import inspect_export
from repo_harness.export.exporter import export_sft_jsonl
from repo_harness.model_client import ModelCallEvent, ModelMessage, ModelResponse
from repo_harness.pre_verl_agentloop import inspect_model_visible_context
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolExecutor, ToolResult
from repo_harness.trajectory import RunRecorder


def test_layer_single_tool_result_persisted_preview_recovery_and_export(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "single_tool_result"
    messages: list[dict[str, object]] = []
    state = AgentLoopState(
        run_id="single-tool-result-layer",
        task_id="task",
        messages=messages,
        budget_state=BudgetState(started_at="2026-05-10T00:00:00+00:00"),
    )
    large_content = "single large tool output\n" * 120
    manager = ContextManager()

    with RunRecorder("single-tool-result-layer", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _record_tool_result(
            tool_result_artifact_index=index,
            context_config=ContextManagementConfig(max_single_tool_result_chars=80),
            run_id="single-tool-result-layer",
            task_id="task",
            turn=1,
            tool_result=ToolResult(
                tool_result_id="call_single_result",
                tool_call_id="call_single",
                tool_name="grep",
                requested_tool_name="grep",
                effective_tool_name="grep",
                normalized_input_hash=stable_hash({"query": "large"}),
                status="ok",
                content_preview=large_content,
            ),
            state=state,
            recorder=recorder,
            messages=messages,
        )
        prepared = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=100000),
            tool_result_artifact_index=index,
        )
        recorder.append_event(prepared.context_event)
        commit = manager.commit_prepared_tool_result_decisions(
            context_revision=prepared.context_revision,
            prepared_messages_ref=prepared.prepared_messages_ref,
            model_call_id="single-tool-result-layer_model_call_0001",
            tool_result_artifact_index=index,
        )
        _bind_model_input_snapshot(
            recorder=recorder,
            run_dir=run_dir,
            prepared=prepared,
            model_call_id="single-tool-result-layer_model_call_0001",
            turn=1,
        )

    preview = str(prepared.messages[0]["content"])
    artifact_id = commit["unlocked_tool_result_artifact_ids"][0]
    recovered = read_tool_result_artifact(index, artifact_id=artifact_id, offset=0, limit=64)

    assert "<persisted-output>" in preview
    assert "recovery_call:" in preview
    assert "recovery_hint:" in preview
    assert recovered["content"] == large_content[:64]
    assert recovered["model_visible_recoverable"] is True
    _write_training_files(run_dir)
    _assert_inspect_and_sft_export_clean(run_dir, assert_tool_results_recoverable=True)


def test_layer_current_turn_aggregate_budget_freezes_preview_and_exports(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "aggregate_budget"
    large_content = "aggregate large tool output\n" * 120
    small_content = "small result\n" * 4
    messages = [
        {
            "role": "assistant",
            "content": "call two tools",
            "turn": 1,
            "tool_calls": [
                {
                    "tool_call_id": "call_large",
                    "tool_name": "grep",
                    "arguments": {"query": "needle"},
                    "turn": 1,
                },
                {
                    "tool_call_id": "call_small",
                    "tool_name": "read_file",
                    "arguments": {"path": "small.py"},
                    "turn": 1,
                },
            ],
        },
        {
            "role": "tool",
            "turn": 1,
            "tool_call_id": "call_large",
            "tool_result_id": "call_large_result",
            "tool_name": "grep",
            "content": large_content,
            "normalized_arguments": {"query": "needle"},
            "status": "ok",
            "typed": {},
            "artifact_refs": [],
        },
        {
            "role": "tool",
            "turn": 1,
            "tool_call_id": "call_small",
            "tool_result_id": "call_small_result",
            "tool_name": "read_file",
            "content": small_content,
            "normalized_arguments": {"path": "small.py"},
            "status": "ok",
            "typed": {},
            "artifact_refs": [],
        },
    ]
    manager = ContextManager()

    with RunRecorder("aggregate-budget-layer", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _append_terminal_tool_events(recorder, messages)
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(
                max_tool_results_per_turn_chars=len(small_content) + 20,
            ),
            tool_result_artifact_index=index,
        )
        recorder.append_event(first.context_event)
        manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="aggregate-budget-layer_model_call_0001",
            tool_result_artifact_index=index,
        )
        _bind_model_input_snapshot(
            recorder=recorder,
            run_dir=run_dir,
            prepared=first,
            model_call_id="aggregate-budget-layer_model_call_0001",
            turn=1,
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=100000),
            tool_result_artifact_index=index,
        )
        recorder.append_event(second.context_event)
        _bind_model_input_snapshot(
            recorder=recorder,
            run_dir=run_dir,
            prepared=second,
            model_call_id="aggregate-budget-layer_model_call_0002",
            turn=2,
        )

    assert first.context_event.data["context_reduction"]["replaced_tool_result_ids"] == [
        "call_large_result"
    ]
    assert "recovery_hint:" in str(first.messages[1]["content"])
    assert second.messages[1]["content"] == first.messages[1]["content"]
    assert second.context_event.data["context_reduction"][
        "reapplied_persisted_tool_result_ids"
    ] == ["call_large_result"]
    _write_training_files(run_dir)
    _assert_inspect_and_sft_export_clean(run_dir, assert_tool_results_recoverable=True)


def test_layer_microcompact_keeps_recent_allowlisted_results_and_exports(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "microcompact"
    messages = _tool_result_messages(count=32, tool_name="read_file")
    manager = ContextManager()

    with RunRecorder("microcompact-layer", run_dir, task_id="task") as recorder:
        _append_terminal_tool_events(recorder, messages)
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(
                microcompact_trigger_compactable_tool_result_chars=1000,
            ),
        )
        recorder.append_event(first.context_event)
        manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="microcompact-layer_model_call_0001",
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(
                microcompact_trigger_compactable_tool_result_chars=1000,
            ),
        )
        recorder.append_event(second.context_event)
        _bind_model_input_snapshot(
            recorder=recorder,
            run_dir=run_dir,
            prepared=second,
            model_call_id="microcompact-layer_model_call_0002",
            turn=2,
        )

    reduction = second.context_event.data["context_reduction"]

    assert reduction["microcompact_applied"] is True
    assert len(reduction["microcompact_cleared_tool_result_ids"]) == 17
    assert len(reduction["microcompact_kept_recent_tool_result_ids"]) == 15
    assert second.messages[1]["content"] == "[Old tool result content cleared]"
    assert second.messages[-1]["content"] != "[Old tool result content cleared]"
    _write_training_files(run_dir)
    _assert_inspect_and_sft_export_clean(run_dir, assert_provider_body_equivalent=False)


def test_layer_auto_compact_rebuilds_context_and_exports_retry_snapshot(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "auto_compact"
    client = _AutoCompactThenFinalClient()

    with RunRecorder("auto-compact-layer", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="auto-compact-layer",
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

    events = _read_jsonl(run_dir / "events.jsonl")
    model_started = next(event for event in events if event["event_type"] == "model_call_started")
    post_prepared = next(
        event for event in events if event["event_type"] == "context_post_compact_prepared"
    )

    assert state.agent_stop_reason == "final_answer"
    assert state.auto_compact_count == 1
    assert [request.scaffold_phase for request in client.requests] == ["compact", "act"]
    assert client.requests[0].allowed_tool_definitions == []
    assert client.requests[0].tool_choice == "none"
    assert model_started["data"]["prepared_messages_ref"] == post_prepared["data"][
        "prepared_messages_ref"
    ]
    _write_training_files(run_dir, stop_reason=state.agent_stop_reason)
    _assert_inspect_and_sft_export_clean(run_dir, assert_provider_body_equivalent=False)


def test_layer_reactive_compact_retries_without_context_limit_pollution(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "reactive_compact"
    client = _ReactiveContextLimitThenFinalClient()

    with RunRecorder("reactive-compact-layer", run_dir, task_id="task") as recorder:
        state = AgentLoop(model_client=client, tool_executor=ToolExecutor()).run(
            run_id="reactive-compact-layer",
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

    events = _read_jsonl(run_dir / "events.jsonl")
    accepted_call_ids = [
        event["data"].get("model_call_id")
        for event in events
        if event["event_type"] == "model_input_accepted"
    ]

    assert state.agent_stop_reason == "final_answer"
    assert state.reactive_compact_count == 1
    assert [request.scaffold_phase for request in client.requests] == ["act", "compact", "act"]
    assert accepted_call_ids == ["reactive-compact-layer_model_call_0002"]
    assert "provider context limit rejected this input" not in (
        run_dir / "transcript.jsonl"
    ).read_text(encoding="utf-8")
    _write_training_files(run_dir, stop_reason=state.agent_stop_reason)
    _assert_inspect_and_sft_export_clean(run_dir, assert_provider_body_equivalent=False)
    exported_text = export_sft_jsonl(run_dir).read_text(encoding="utf-8")
    assert "provider context limit rejected this input" not in exported_text


def test_synthetic_context_compaction_pipeline_covers_all_layers(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "synthetic_pipeline"
    manager = ContextManager()
    config = ContextManagementConfig(
        max_tool_results_per_turn_chars=205000,
        microcompact_trigger_compactable_tool_result_count=30,
        microcompact_trigger_compactable_tool_result_chars=1000,
        model_context_window_tokens=16000,
        main_output_reserve_tokens=0,
        estimator_safety_margin_ratio=0.0,
        estimator_safety_margin_min_tokens=0,
        auto_compact_trigger_ratio=0.1,
        hard_context_limit_ratio=0.95,
        reactive_compact_enabled=True,
        reactive_compact_retry_limit=1,
        post_compact_target_max_tokens=3000,
    )
    messages = _synthetic_pressure_messages()
    client = _ReactiveContextLimitThenFinalClient()

    with RunRecorder("synthetic-context-pipeline", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        _append_terminal_tool_events(recorder, messages)
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=config,
            tool_result_artifact_index=index,
        )
        recorder.append_event(first.context_event)
        manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="synthetic-context-pipeline_layer_model_call_0001",
            tool_result_artifact_index=index,
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=config,
            tool_result_artifact_index=index,
        )
        recorder.append_event(second.context_event)
        _bind_model_input_snapshot(
            recorder=recorder,
            run_dir=run_dir,
            prepared=second,
            model_call_id="synthetic-context-pipeline_layer_model_call_0002",
            turn=2,
        )
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["grep", "read_file"],
        ).run(
            run_id="synthetic-context-pipeline",
            task_id="task",
            initial_messages=[
                *second.messages,
                {
                    "role": "user",
                    "turn": 3,
                    "content": "Continue from the compressed tool history and finish.",
                },
            ],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            context_config=config,
        )

    events = _read_jsonl(run_dir / "events.jsonl")
    context_events = [event for event in events if event["event_type"] == "context_prepared"]
    event_types = [event["event_type"] for event in events]
    accepted_call_ids = [
        event["data"].get("model_call_id")
        for event in events
        if event["event_type"] == "model_input_accepted"
    ]
    final_request_messages = json.dumps(client.requests[-1].prepared_messages, ensure_ascii=False)

    assert state.agent_stop_reason == "final_answer"
    assert len(context_events) >= 4
    assert first.context_event.data["context_reduction"]["replaced_tool_result_ids"]
    assert any(
        ref.get("kind") == "tool_result_original_content"
        for ref in first.context_event.data["context_reduction"]["replacement_artifact_refs"]
    )
    assert second.context_event.data["context_reduction"]["microcompact_applied"] is True
    assert "auto_compact_model_call_started" in event_types
    assert "auto_compact_applied" in event_types
    assert "reactive_compact_triggered" in event_types
    assert state.auto_compact_count >= 1
    assert state.reactive_compact_count == 1
    assert "synthetic-context-pipeline_model_call_0001" not in accepted_call_ids
    assert accepted_call_ids[-1] == "synthetic-context-pipeline_model_call_0002"
    assert "repo_harness_auto_compact_summary" in final_request_messages
    assert "provider context limit rejected this input" not in final_request_messages
    _write_training_files(run_dir, stop_reason=state.agent_stop_reason)
    _assert_inspect_and_sft_export_clean(
        run_dir,
        assert_tool_results_recoverable=True,
        assert_provider_body_equivalent=False,
    )
    exported_text = export_sft_jsonl(run_dir).read_text(encoding="utf-8")
    assert "provider context limit rejected this input" not in exported_text


def _bind_model_input_snapshot(
    *,
    recorder: RunRecorder,
    run_dir: Path,
    prepared: Any,
    model_call_id: str,
    turn: int,
) -> None:
    prepared_payload = _read_ref_json(run_dir, prepared.prepared_messages_ref.model_dump(mode="json"))
    projection = _provider_projection(prepared_payload["messages"])
    projection_hash = stable_hash(projection)
    tool_schema_ref = recorder.write_json_artifact(
        "tool_schema_snapshot",
        {
            "schema_version": "repo_harness_tool_schema_snapshot_test_v0",
            "tools": [],
        },
        {"budget_policy": "preserve_json"},
    )
    request_body = {"messages": projection}
    request_ref = recorder.write_json_artifact(
        "raw_provider_request",
        {
            "schema_version": "repo_harness_raw_provider_request_test_v0",
            "provider": "generic",
            "turn": turn,
            "body": request_body,
            "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(mode="json"),
            "tool_schema_snapshot_ref": tool_schema_ref.model_dump(mode="json"),
            "export_allowed": False,
            "training_payload_allowed": False,
            "prepared_messages_body_equivalent": True,
            "provider_body_hash_before_redaction": stable_hash(request_body),
            "redacted_body_hash": stable_hash(request_body),
            "provider_body_message_projection_hash": projection_hash,
            "prepared_messages_projection_hash": projection_hash,
            "redaction_report": {
                "ordinary_text_whole_field_redaction_allowed": False,
            },
        },
        {"budget_policy": "preserve_json"},
    )
    response_payload = {
        "schema_version": "repo_harness_raw_provider_response_test_v0",
        "status": "ok",
        "response": {
            "choices": [
                {
                    "message": {"content": "done", "tool_calls": []},
                    "finish_reason": "stop",
                }
            ]
        },
    }
    response_ref = recorder.write_json_artifact(
        "raw_provider_response",
        {
            **response_payload,
            "raw_provider_request_ref": request_ref.model_dump(mode="json"),
            "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(mode="json"),
            "tool_schema_snapshot_ref": tool_schema_ref.model_dump(mode="json"),
            "export_allowed": False,
            "training_payload_allowed": False,
            "response_body_hash_before_redaction": stable_hash(response_payload["response"]),
            "redacted_response_body_hash": stable_hash(response_payload["response"]),
            "parsed_tool_calls_hash": stable_hash({"error": None, "tool_calls": []}),
            "finish_reason": "stop",
            "redaction_report": {
                "ordinary_text_whole_field_redaction_allowed": False,
            },
        },
        {"budget_policy": "preserve_json"},
    )
    snapshot_ref = recorder.write_json_artifact(
        "model_input_snapshot",
        {
            "schema_version": "repo_harness_model_input_snapshot_v1",
            "model_call_id": model_call_id,
            "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(mode="json"),
            "model_input_hash": prepared.model_input_hash,
            "provider_request_projection_hash": projection_hash,
            "context_policy_snapshot_ref": None,
            "provider_request_artifact_ref": request_ref.model_dump(mode="json"),
            "provider_response_artifact_ref": response_ref.model_dump(mode="json"),
            "context_compact_state_ref": prepared.context_event.data[
                "content_replacement_state_ref"
            ],
            "trainable": True,
        },
        {"budget_policy": "preserve_json"},
    )
    assistant_ref = recorder.write_json_artifact(
        "assistant_message",
        {
            "schema_version": "repo_harness_assistant_message_transcript_payload_v0",
            "content": "done",
            "tool_calls": [],
            "finish_reason": "stop",
            "model_error_type": None,
        },
        {"budget_policy": "preserve_json"},
    )
    recorder.append_event(
        {
            "event_id": recorder.next_event_id("model"),
            "timestamp": "2026-05-10T00:00:00+00:00",
            "run_id": recorder.run_id,
            "task_id": "task",
            "turn": turn,
            "event_type": "model_call_started",
            "artifact_refs": [prepared.prepared_messages_ref.model_dump(mode="json")],
            "data": {
                "model_call_id": model_call_id,
                "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(mode="json"),
                "model_input_hash": prepared.model_input_hash,
                "scaffold_phase": "act",
            },
        }
    )
    recorder.append_event(
        {
            "event_id": recorder.next_event_id("model_input"),
            "timestamp": "2026-05-10T00:00:01+00:00",
            "run_id": recorder.run_id,
            "task_id": "task",
            "turn": turn,
            "event_type": "model_input_accepted",
            "artifact_refs": [
                prepared.prepared_messages_ref.model_dump(mode="json"),
                snapshot_ref.model_dump(mode="json"),
                request_ref.model_dump(mode="json"),
                response_ref.model_dump(mode="json"),
            ],
            "data": {
                "model_call_id": model_call_id,
                "prepared_messages_ref": prepared.prepared_messages_ref.model_dump(mode="json"),
                "model_input_hash": prepared.model_input_hash,
                "model_input_snapshot_ref": snapshot_ref.model_dump(mode="json"),
            },
        }
    )
    recorder.append_event(
        {
            "event_id": recorder.next_event_id("model"),
            "timestamp": "2026-05-10T00:00:02+00:00",
            "run_id": recorder.run_id,
            "task_id": "task",
            "turn": turn,
            "event_type": "model_call_completed",
            "artifact_refs": [request_ref.model_dump(mode="json"), response_ref.model_dump(mode="json")],
            "data": {
                "model_call_id": model_call_id,
                "raw_provider_request_ref": request_ref.model_dump(mode="json"),
                "raw_provider_response_ref": response_ref.model_dump(mode="json"),
                "model_error_type": None,
            },
        }
    )
    recorder.append_transcript(
        {
            "record_id": recorder.next_record_id("assistant"),
            "run_id": recorder.run_id,
            "task_id": "task",
            "message_id": f"{model_call_id}_assistant",
            "turn": turn,
            "role": "assistant",
            "model_call_id": model_call_id,
            "content_preview": "done",
            "content_artifact_refs": [assistant_ref.model_dump(mode="json")],
            "model_visible": True,
            "trainable": True,
            "created_at": "2026-05-10T00:00:03+00:00",
        }
    )


def _assert_inspect_and_sft_export_clean(
    run_dir: Path,
    *,
    assert_tool_results_recoverable: bool = False,
    assert_provider_body_equivalent: bool = True,
) -> None:
    inspect_result = inspect_model_visible_context(
        run_dir,
        assert_prepared_messages_bound=True,
        assert_provider_body_equivalent=assert_provider_body_equivalent,
        assert_tool_results_recoverable=assert_tool_results_recoverable,
        assert_no_hidden_test_material=True,
    )
    assert "passed" in inspect_result
    output = export_sft_jsonl(run_dir)
    export_dir = _latest_export_dir(run_dir / "exports")
    assert _read_jsonl(output)
    assert "Inspect export: clean" in inspect_export(
        export_dir,
        assert_clean=True,
        require_trainable_samples=True,
    )


def _append_terminal_tool_events(
    recorder: RunRecorder,
    messages: list[dict[str, object]],
) -> None:
    for message in messages:
        if message.get("role") != "tool":
            continue
        tool_call_id = str(message.get("tool_call_id") or "")
        recorder.append_event(
            {
                "event_id": recorder.next_event_id("tool"),
                "timestamp": "2026-05-10T00:00:00+00:00",
                "run_id": recorder.run_id,
                "task_id": "task",
                "turn": int(message.get("turn") or 1),
                "event_type": "tool_completed",
                "data": {
                    "tool_call_id": tool_call_id,
                    "tool_result_id": str(message.get("tool_result_id") or tool_call_id),
                    "effective_tool_name": str(message.get("tool_name") or "unknown"),
                    "status": str(message.get("status") or "ok"),
                },
            }
        )


def _write_training_files(
    run_dir: Path,
    *,
    stop_reason: str | None = "final_answer",
) -> None:
    (run_dir / "baseline.json").write_text(
        json.dumps({"task_id": "task"}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_outcome": "success",
                "final_verifier_status": "accepted",
                "interaction_efficiency": {
                    "final_verifier_mode": "strict_patch_replay",
                    "agent_stop_reason": stop_reason,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "reward.json").write_text(
        json.dumps({"final_reward": 1.0, "reward_version": "repo_harness_reward_v0"})
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "verifier.json").write_text(
        json.dumps({"verifier_stage": "final", "accepted": True}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "final.patch").write_text(
        "diff --git a/demo.py b/demo.py\n",
        encoding="utf-8",
    )
    _write_minimal_v2_metadata(run_dir)


def _write_minimal_v2_metadata(run_dir: Path) -> None:
    snapshot_sha = "b" * 64
    tool_snapshot_path = run_dir / "artifacts" / "tool_schema_snapshot.json"
    tool_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    tool_snapshot_path.write_text(
        json.dumps(
            {"snapshot_id": "snapshot_001", "snapshot_sha256": snapshot_sha},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    artifact_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "artifact_tool_schema_snapshot",
        "relative_path": "artifacts/tool_schema_snapshot.json",
        "kind": "tool_schema_snapshot",
        "sha256": _sha256_file(tool_snapshot_path),
        "size_bytes": tool_snapshot_path.stat().st_size,
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    _append_artifact_ref(run_dir, artifact_ref)
    tool_protocol = {
        "tool_schema_snapshot_ref": artifact_ref,
        "tool_schema_snapshot_sha256": snapshot_sha,
        "tool_order": ["grep", "read_file"],
        "tool_parser_version": "repo_harness_tool_call_parser_v0",
        "tool_result_format_version": "repo_harness_tool_result_v0",
    }
    run_config = {
        "task_id": "task",
        "task_version": "task_v0",
        "base_commit": "fixture",
        "provider": "replay",
        "model_id": "replay-script-v0",
        "temperature": 0.0,
        "max_output_tokens": 1024,
        "scaffold_id": "patch_focused_react",
        "scaffold_version": "repo_harness_patch_focused_react_v0",
        "allowed_tools_policy": "repo_harness_tools_v0",
        "phase_policy": "repo_harness_patch_focused_react_v0",
        "verifier_name": "pytest",
        "verifier_version": "pytest_parser_v0",
        "reward_formula_version": "repo_harness_reward_v0",
        "final_verifier_mode": "strict_patch_replay",
        "context_policy_version": "repo_harness_context_policy_v0",
        "prompt_template_version": "repo_harness_prompt_v0",
        "permission_policy_version": "repo_harness_permissions_v0",
        "max_turns": 8,
        "max_tool_calls": 20,
        "max_test_runs": 4,
        "task_timeout_sec": 120,
        "test_feedback_policy": "public_only",
        "hidden_feedback_visible_to_model": False,
        "tool_protocol": tool_protocol,
    }
    (run_dir / "run_config_facts.json").write_text(
        json.dumps(run_config, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "metadata_source": "v2",
                "run_config_facts_ref": {
                    "relative_path": "run_config_facts.json",
                    "sha256": _sha256_file(run_dir / "run_config_facts.json"),
                },
                "tool_protocol": tool_protocol,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _append_artifact_ref(run_dir: Path, artifact_ref: dict[str, Any]) -> None:
    manifest_path = run_dir / "artifacts.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"artifacts": []}
    )
    artifacts = manifest.setdefault("artifacts", [])
    if not any(
        artifact.get("artifact_id") == artifact_ref["artifact_id"]
        for artifact in artifacts
    ):
        artifacts.append(artifact_ref)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")


def _tool_result_messages(*, count: int, tool_name: str) -> list[dict[str, object]]:
    tool_calls = [
        {
            "tool_call_id": f"call_{index}",
            "tool_name": tool_name,
            "arguments": {"path": f"file_{index}.py"},
            "turn": 1,
        }
        for index in range(count)
    ]
    messages: list[dict[str, object]] = [
        {
            "role": "assistant",
            "content": "call tools",
            "turn": 1,
            "tool_calls": tool_calls,
        }
    ]
    for index in range(count):
        messages.append(
            {
                "role": "tool",
                "turn": 1,
                "tool_call_id": f"call_{index}",
                "tool_result_id": f"call_{index}_result",
                "tool_name": tool_name,
                "content": f"tool output {index}\n" + ("x" * 100),
                "normalized_arguments": {"path": f"file_{index}.py"},
                "status": "ok",
                "typed": {},
                "artifact_refs": [],
            }
        )
    return messages


def _synthetic_pressure_messages() -> list[dict[str, object]]:
    tool_calls: list[dict[str, object]] = []
    messages: list[dict[str, object]] = [
        {"role": "system", "content": "system"},
        {"role": "user", "turn": 1, "content": "Investigate a long-context issue."},
        {"role": "assistant", "content": "call pressure tools", "turn": 1, "tool_calls": tool_calls},
    ]
    for index in range(10):
        tool_call = {
            "tool_call_id": f"call_large_{index}",
            "tool_name": "grep",
            "arguments": {"query": f"needle_{index}"},
            "turn": 1,
        }
        tool_calls.append(tool_call)
        messages.append(
            {
                "role": "tool",
                "turn": 1,
                "tool_call_id": f"call_large_{index}",
                "tool_result_id": f"call_large_{index}_result",
                "tool_name": "grep",
                "content": f"large result {index}\n" + ("L" * 40000),
                "normalized_arguments": {"query": f"needle_{index}"},
                "status": "ok",
                "typed": {},
                "artifact_refs": [],
            }
        )
    for index in range(32):
        tool_call = {
            "tool_call_id": f"call_read_{index}",
            "tool_name": "read_file",
            "arguments": {"path": f"file_{index}.py"},
            "turn": 1,
        }
        tool_calls.append(tool_call)
        messages.append(
            {
                "role": "tool",
                "turn": 1,
                "tool_call_id": f"call_read_{index}",
                "tool_result_id": f"call_read_{index}_result",
                "tool_name": "read_file",
                "content": f"read result {index}\n" + ("R" * 120),
                "normalized_arguments": {"path": f"file_{index}.py"},
                "status": "ok",
                "typed": {},
                "artifact_refs": [],
            }
        )
    return messages


def _provider_projection(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        item: dict[str, Any] = {
            "role": role,
            "content": _provider_content(message.get("content")),
        }
        if role == "tool":
            item["tool_call_id"] = str(
                message.get("tool_call_id") or message.get("tool_result_id") or ""
            )
        if role == "assistant" and message.get("tool_calls"):
            item["tool_calls"] = [
                {
                    "id": str(call.get("tool_call_id") or call.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(call.get("tool_name") or call.get("name") or ""),
                        "arguments": json.dumps(
                            call.get("arguments") or {},
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                }
                for call in message.get("tool_calls", [])
                if isinstance(call, dict)
            ]
        projected.append({key: value for key, value in item.items() if value is not None})
    return projected


def _provider_content(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


class _AutoCompactThenFinalClient:
    def __init__(self, *, compact_content: str | None = None) -> None:
        self.requests: list[Any] = []
        self.compact_content = compact_content or json.dumps(
            {
                "schema_version": "repo_harness_compact_summary_v1",
                "task_intent": "Continue the task from visible context.",
                "repository_facts": ["The task is to fix a public bug."],
                "actions_taken": ["Earlier context was summarized."],
                "patch_state": {"changed_files": [], "important_diffs": []},
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

    def generate(self, request: Any, recorder: RunRecorder) -> ModelResponse:
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
                    "export_allowed": False,
                    "training_payload_allowed": False,
                    "redaction_report": {
                        "ordinary_text_whole_field_redaction_allowed": False,
                    },
                },
            )
            raw_response_ref = recorder.write_json_artifact(
                "raw_auto_compact_test_response",
                {
                    "content": self.compact_content,
                    "export_allowed": False,
                    "training_payload_allowed": False,
                    "redaction_report": {
                        "ordinary_text_whole_field_redaction_allowed": False,
                    },
                },
            )
            return ModelResponse(
                assistant_message=ModelMessage(role="assistant", content=self.compact_content),
                raw_provider_request_ref=raw_request_ref,
                raw_provider_response_ref=raw_response_ref,
                finish_reason="stop",
            )
        return _model_response_for_request(
            request,
            recorder,
            content="done",
            finish_reason="stop",
            model_error_type=None,
        )


class _ReactiveContextLimitThenFinalClient(_AutoCompactThenFinalClient):
    def __init__(self) -> None:
        super().__init__()
        self.main_call_count = 0

    def generate(self, request: Any, recorder: RunRecorder) -> ModelResponse:
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


def _model_response_for_request(
    request: Any,
    recorder: RunRecorder,
    *,
    content: str,
    finish_reason: str,
    model_error_type: str | None,
) -> ModelResponse:
    tool_schema_ref = recorder.write_json_artifact(
        "tool_schema_snapshot",
        {
            "schema_version": "repo_harness_tool_schema_snapshot_test_v0",
            "tools": request.allowed_tool_definitions,
        },
    )
    raw_request_ref = recorder.write_json_artifact(
        "raw_provider_request",
        {
            "model_call_id": request.model_call_id,
            "prepared_messages_ref": request.prepared_messages_ref.model_dump(mode="json"),
            "tool_schema_snapshot_ref": tool_schema_ref.model_dump(mode="json"),
            "model_input_hash": request.model_input_hash,
            "export_allowed": False,
            "training_payload_allowed": False,
            "redaction_report": {
                "ordinary_text_whole_field_redaction_allowed": False,
            },
        },
    )
    raw_response_ref = recorder.write_json_artifact(
        "raw_provider_response",
        {
            "model_call_id": request.model_call_id,
            "content": content,
            "finish_reason": finish_reason,
            "model_error_type": model_error_type,
            "export_allowed": False,
            "training_payload_allowed": False,
            "redaction_report": {
                "ordinary_text_whole_field_redaction_allowed": False,
            },
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


def _latest_export_dir(exports_dir: Path) -> Path:
    candidates = [path for path in exports_dir.iterdir() if path.is_dir()]
    assert candidates
    return sorted(candidates)[-1]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_ref_json(run_dir: Path, ref: dict[str, Any]) -> dict[str, Any]:
    return json.loads((run_dir / ref["relative_path"]).read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
