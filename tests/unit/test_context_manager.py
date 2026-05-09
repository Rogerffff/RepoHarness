from pathlib import Path

from repo_harness.config import ContextManagementConfig
from repo_harness.context import ContextManager
from repo_harness.trajectory import RunRecorder


def test_prepared_messages_artifact_does_not_embed_replacement_state_hash(tmp_path: Path):
    with RunRecorder("context-test", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=[{"role": "system", "content": "system"}],
            recorder=recorder,
            task_id="task",
            turn=1,
        )

    prepared_path = tmp_path / "run" / prepared.prepared_messages_ref.relative_path
    prepared_text = prepared_path.read_text(encoding="utf-8")

    assert prepared.content_replacement_state is not None
    assert prepared.content_replacement_state.state_hash not in prepared_text
    assert "content_replacement_state_ref" in prepared_text
    assert '"content_replacement_state":' not in prepared_text


def test_prepared_messages_records_provider_ready_estimate_separately(tmp_path: Path):
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "tool_call_id": "call_read",
                    "tool_name": "read_file",
                    "arguments": {"path": "demo.py"},
                    "turn": 1,
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_read",
            "tool_result_id": "call_read_result",
            "tool_name": "read_file",
            "content": "short visible content",
            "normalized_arguments": {"path": "demo.py", "debug_payload": "x" * 20000},
            "typed": {"status": "ok"},
        },
    ]

    with RunRecorder("context-estimate", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            provider_name="deepseek",
        )

    event_data = prepared.context_event.data

    assert prepared.threshold_decision_source == "provider_ready_token_estimate"
    assert prepared.token_estimate == prepared.provider_ready_token_estimate
    assert prepared.internal_token_estimate > prepared.provider_ready_token_estimate
    assert event_data["threshold_decision_source"] == "provider_ready_token_estimate"
    assert event_data["provider_ready_token_estimate"] == prepared.provider_ready_token_estimate
    assert event_data["internal_token_estimate_after"] == prepared.internal_token_estimate
    assert event_data["provider_returned_prompt_tokens"] is None
    assert event_data["provider_usage_metadata_status"] == "unavailable_before_provider_call"


def test_tool_result_replacement_prefers_result_envelope_recovery(tmp_path: Path):
    messages = [
        {"role": "assistant", "content": "call tool", "turn": 1},
        {
            "role": "tool",
            "tool_call_id": "call_read",
            "tool_result_id": "call_read_result",
            "tool_name": "read_file",
            "content": "large tool output\n" * 200,
            "normalized_arguments": {"path": "large.py"},
            "typed": {
                "result_envelope": {
                    "recovery_call": "read_file(path='large.py', start_line=88)",
                    "recovery_hint": "Envelope recovery should survive replacement.",
                }
            },
        },
    ]

    with RunRecorder("context-replacement", tmp_path / "run", task_id="task") as recorder:
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(
                tool_result_aggregate_budget_chars=10,
                keep_recent_turns=0,
                keep_recent_test_results=0,
            ),
        )

    replacement = prepared.messages[1]["content"]

    assert "[tool result replaced]" in replacement
    assert "recovery_call: read_file(path='large.py', start_line=88)" in replacement
    assert "Envelope recovery should survive replacement." in replacement
