from pathlib import Path
import json

from repo_harness.config import ContextManagementConfig
from repo_harness.context import ContextManager
from repo_harness.trajectory import RunRecorder


def test_context_manager_replaces_large_old_tool_output_deterministically(tmp_path: Path):
    run_dir = tmp_path / "run"
    messages = [
        {"role": "system", "content": "system"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"tool_call_id": "call_big", "tool_name": "bash", "arguments": {}}],
        },
        {
            "role": "tool",
            "tool_call_id": "call_big",
            "tool_result_id": "call_big_result",
            "content": "\n".join(f"line {index}" for index in range(200)),
            "artifact_refs": [
                {
                    "schema_version": "repo_harness_artifact_ref_v0",
                    "artifact_id": "artifact_big",
                    "relative_path": "artifacts/big.txt",
                    "kind": "command_output",
                    "sha256": "abc",
                    "size_bytes": 123,
                    "redaction_status": "not_scanned",
                    "retention_policy": "keep",
                }
            ],
        },
    ]
    config = ContextManagementConfig(tool_result_aggregate_budget_chars=100)
    manager = ContextManager()
    with RunRecorder("context-test", run_dir, task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=config,
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=config,
        )

    first_tool = first.messages[2]
    second_tool = second.messages[2]
    assert first_tool["content"] == second_tool["content"]
    assert "[tool result replaced]" in str(first_tool["content"])
    assert "artifact_big" in str(first_tool["content"])
    assert first.model_input_hash == second.model_input_hash
    assert first.content_replacement_state is not None
    assert first.content_replacement_state.records[0].replacement_preview_hash is not None
    assert first.context_event.data["tool_pairing_validation"]["ok"] is True
    assert first.token_estimate == first.context_event.data["tokens_after"]
    assert first.context_event.data["tokens_after"] < first.context_event.data["tokens_before"]
    state_ref = first.context_event.data["content_replacement_state_ref"]
    persisted_state = json.loads((run_dir / state_ref["relative_path"]).read_text(encoding="utf-8"))
    assert persisted_state["records"][0]["replacement_preview_hash"] is not None
    prepared_payload = json.loads(
        (run_dir / first.prepared_messages_ref.relative_path).read_text(encoding="utf-8")
    )
    assert prepared_payload["model_input_hash"] == first.model_input_hash


def test_context_manager_detects_missing_tool_result(tmp_path: Path):
    messages = [
        {"role": "system", "content": "system"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"tool_call_id": "missing", "tool_name": "read_file", "arguments": {}}],
        },
    ]
    with RunRecorder("context-missing", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
        )

    assert prepared.context_event.data["tool_pairing_validation"]["ok"] is False
    assert prepared.context_event.data["tool_pairing_validation"]["missing_tool_result_ids"] == ["missing"]


def test_context_manager_preserves_first_visible_record_when_replacing_later(tmp_path: Path):
    run_dir = tmp_path / "run"
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"tool_call_id": "call_later", "tool_name": "bash", "arguments": {}}],
        },
        {
            "role": "tool",
            "tool_call_id": "call_later",
            "tool_result_id": "call_later_result",
            "content": "short output",
        },
    ]
    manager = ContextManager()
    with RunRecorder("context-later", run_dir, task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(tool_result_aggregate_budget_chars=1000),
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(tool_result_aggregate_budget_chars=1),
        )

    first_record = first.content_replacement_state.records[0]
    second_record = second.content_replacement_state.records[0]
    assert first_record.first_visible_form == "preview"
    assert second_record.replaced is True
    assert second_record.first_visible_form == "preview"
    assert second_record.first_seen_at_context_revision == first_record.first_seen_at_context_revision
    assert second_record.first_visible_content_hash == first_record.first_visible_content_hash


def test_context_manager_preserves_recent_test_feedback_over_older_output(tmp_path: Path):
    run_dir = tmp_path / "run"
    old_output = "older output " * 10
    recent_feedback = "run_tests accepted=True pass_ratio=1.00"
    messages = [
        {
            "role": "assistant",
            "content": None,
            "turn": 1,
            "tool_calls": [{"tool_call_id": "call_old", "tool_name": "bash", "arguments": {}}],
        },
        {
            "role": "tool",
            "turn": 1,
            "tool_call_id": "call_old",
            "tool_result_id": "call_old_result",
            "tool_name": "bash",
            "content": old_output,
        },
        {
            "role": "assistant",
            "content": None,
            "turn": 2,
            "tool_calls": [{"tool_call_id": "call_tests", "tool_name": "run_tests", "arguments": {}}],
        },
        {
            "role": "tool",
            "turn": 2,
            "tool_call_id": "call_tests",
            "tool_result_id": "call_tests_result",
            "tool_name": "run_tests",
            "effective_tool_name": "run_tests",
            "content": recent_feedback,
            "typed": {"verifier_result_preview": {"accepted": True}},
        },
    ]

    with RunRecorder("context-recent-tests", run_dir, task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=3,
            context_config=ContextManagementConfig(
                tool_result_aggregate_budget_chars=len(old_output) + 5,
                keep_recent_test_results=1,
                keep_recent_turns=0,
            ),
        )

    old_tool = prepared.messages[1]
    test_tool = prepared.messages[3]
    assert "[tool result replaced]" in str(old_tool["content"])
    assert test_tool["content"] == recent_feedback
    assert not test_tool.get("context_replacement", False)
