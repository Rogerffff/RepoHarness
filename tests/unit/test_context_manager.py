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
            "tool_calls": [
                {
                    "tool_call_id": "call_big",
                    "tool_name": "read_file",
                    "arguments": {"path": "src/example.py", "start_line": 1},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_big",
            "tool_result_id": "call_big_result",
            "tool_name": "read_file",
            "requested_tool_name": "read_file",
            "effective_tool_name": "read_file",
            "requested_arguments": {"path": "src/example.py", "start_line": 1},
            "normalized_arguments": {"path": "src/example.py", "start_line": 1, "max_lines": 200},
            "effective_arguments": {"path": "src/example.py", "start_line": 1, "max_lines": 200},
            "normalized_input_hash": "hash-read-file-input",
            "content": "\n".join(f"line {index}" for index in range(200)),
            "typed": {
                "path": "src/example.py",
                "start_line": 1,
                "end_line": 200,
                "total_lines": 260,
                "next_start_line": 201,
            },
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
    assert "tool_name: read_file" in str(first_tool["content"])
    assert "normalized_arguments_sha256: hash-read-file-input" in str(first_tool["content"])
    assert "recovery_call: read_file(path='src/example.py', start_line=201)" in str(first_tool["content"])
    assert '"total_lines":260' in str(first_tool["content"])
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
    replacement_ref = first.context_event.data["context_reduction"]["replacement_artifact_refs"][0]
    replacement_payload = json.loads(
        (run_dir / replacement_ref["relative_path"]).read_text(encoding="utf-8")
    )
    assert replacement_payload["recovery"]["recommended_call"] == (
        "read_file(path='src/example.py', start_line=201)"
    )


def test_context_manager_redacts_evaluator_only_replacement_preview(tmp_path: Path):
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"tool_call_id": "call_hidden", "tool_name": "read_file", "arguments": {}}],
        },
        {
            "role": "tool",
            "tool_call_id": "call_hidden",
            "tool_result_id": "call_hidden_result",
            "tool_name": "read_file",
            "normalized_arguments": {"path": "hidden.patch"},
            "content": "secret hidden selector output\n" * 20,
            "artifact_refs": [
                {
                    "schema_version": "repo_harness_artifact_ref_v0",
                    "artifact_id": "hidden_test_selector_artifact",
                    "relative_path": "artifacts/hidden_selector.txt",
                    "kind": "hidden_test_selector",
                    "sha256": "hidden-sha",
                    "size_bytes": 50,
                    "redaction_status": "evaluator_only",
                    "retention_policy": "keep",
                }
            ],
        },
    ]
    with RunRecorder("context-hidden", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(tool_result_aggregate_budget_chars=1),
        )

    replacement = str(prepared.messages[1]["content"])
    assert "preview_redacted" in replacement
    assert "secret hidden selector output" not in replacement
    assert "hidden.patch" not in replacement
    assert "hidden_test_selector_artifact" not in replacement
    assert "hidden_test_selector" not in replacement
    assert "not_available_evaluator_only_source_artifact" in replacement
    replacement_ref = prepared.context_event.data["context_reduction"]["replacement_artifact_refs"][0]
    replacement_payload = json.loads(
        ((tmp_path / "run") / replacement_ref["relative_path"]).read_text(encoding="utf-8")
    )
    assert replacement_payload["source_artifact_ref"]["redacted"] is True
    assert replacement_payload["source_artifact_ref"]["artifact_id"] == "redacted_sensitive_artifact"
    assert replacement_payload["source_artifact_ref"]["kind"] == "redacted_sensitive_artifact"
    assert replacement_payload["recovery"]["normalized_arguments"] == {"redacted": True}


def test_context_manager_recovery_call_preserves_grep_scope(tmp_path: Path):
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "tool_call_id": "call_grep",
                    "tool_name": "grep",
                    "arguments": {
                        "query": "needle",
                        "root": "tests",
                        "glob": "*.py",
                        "offset": 40,
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_grep",
            "tool_result_id": "call_grep_result",
            "tool_name": "grep",
            "requested_tool_name": "grep",
            "effective_tool_name": "grep",
            "normalized_arguments": {
                "query": "needle",
                "mode": "literal",
                "root": "tests",
                "glob": "*.py",
                "offset": 40,
                "max_matches": 25,
                "context_lines": 2,
            },
            "normalized_input_hash": "hash-grep-input",
            "content": "\n".join(f"tests/test_{index}.py: needle" for index in range(100)),
            "typed": {"next_offset": 65},
            "artifact_refs": [
                {
                    "schema_version": "repo_harness_artifact_ref_v0",
                    "artifact_id": "grep_artifact",
                    "relative_path": "artifacts/grep.txt",
                    "kind": "tool_output",
                    "sha256": "grep-sha",
                    "size_bytes": 500,
                    "redaction_status": "not_scanned",
                    "retention_policy": "keep",
                }
            ],
        },
    ]
    with RunRecorder("context-grep", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(tool_result_aggregate_budget_chars=1),
        )

    replacement = str(prepared.messages[1]["content"])
    assert "recovery_call: grep(" in replacement
    assert "root='tests'" in replacement
    assert "glob='*.py'" in replacement
    assert "offset=65" in replacement
    assert "max_matches=25" in replacement
    assert "context_lines=2" in replacement


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
    assert prepared.context_event.data["tool_pairing_validation"]["duplicate_tool_call_ids"] == []
    assert prepared.context_event.data["tool_pairing_validation"]["duplicate_tool_result_ids"] == []


def test_context_manager_detects_duplicate_and_out_of_order_tool_results(tmp_path: Path):
    messages = [
        {"role": "tool", "tool_call_id": "call_late", "tool_result_id": "call_late_result", "content": "early"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"tool_call_id": "call_late", "tool_name": "read_file", "arguments": {}},
                {"tool_call_id": "call_late", "tool_name": "read_file", "arguments": {}},
            ],
        },
        {"role": "tool", "tool_call_id": "call_late", "tool_result_id": "call_late_result_2", "content": "late"},
    ]
    with RunRecorder("context-duplicates", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
        )

    validation = prepared.context_event.data["tool_pairing_validation"]
    assert validation["ok"] is False
    assert validation["duplicate_tool_call_ids"] == ["call_late"]
    assert validation["duplicate_tool_result_ids"] == ["call_late"]
    assert validation["out_of_order_tool_result_ids"] == ["call_late", "call_late"]


def test_context_manager_rejects_interrupted_tool_result_block(tmp_path: Path):
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"tool_call_id": "call_read", "tool_name": "read_file", "arguments": {}}],
        },
        {"role": "user", "content": "unexpected user message"},
        {"role": "tool", "tool_call_id": "call_read", "tool_result_id": "call_read_result", "content": "late"},
    ]
    with RunRecorder("context-interrupted-block", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
        )

    validation = prepared.context_event.data["tool_pairing_validation"]
    assert validation["ok"] is False
    assert validation["out_of_order_tool_result_ids"] == ["call_read", "call_read"]


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
