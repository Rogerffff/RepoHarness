from pathlib import Path

import pytest

from repo_harness.config import ContextManagementConfig
from repo_harness.context import ContextManager
from repo_harness.context.schemas import ToolResultArtifactRecord
from repo_harness.trajectory import RunRecorder


def test_context_management_config_exposes_compact_policy_defaults():
    config = ContextManagementConfig()

    assert config.schema_version == "repo_harness_context_management_config_v1"
    assert config.max_context_tokens == 120000
    assert config.tool_result_aggregate_budget_chars == 40000
    assert config.context_budget_policy == "model_window_with_optional_cap"
    assert config.max_single_tool_result_chars == 50000
    assert config.max_tool_results_per_turn_chars == 200000
    assert config.freeze_tool_result_decisions_at == "provider_committed"
    assert config.microcompact_trigger_compactable_tool_result_count == 30
    assert config.microcompact_keep_recent_compactable_tool_results == 15
    assert config.auto_compact_trigger_ratio == 0.85
    assert config.hard_context_limit_ratio == 0.97
    assert config.reactive_compact_policy == "provider_verified_reactive"


def test_context_management_config_accepts_legacy_fields_without_new_fields():
    config = ContextManagementConfig.model_validate(
        {
            "schema_version": "repo_harness_context_management_config_v0",
            "max_context_tokens": 64000,
            "tool_result_aggregate_budget_chars": 12345,
            "keep_recent_turns": 4,
        }
    )

    assert config.schema_version == "repo_harness_context_management_config_v0"
    assert config.max_context_tokens == 64000
    assert config.tool_result_aggregate_budget_chars == 12345
    assert config.keep_recent_turns == 4
    assert config.tool_result_compact_policy == "claude_code_fresh_only_v1"
    assert config.microcompact_enabled is True
    assert config.auto_compact_enabled is True


def test_tool_result_artifact_record_derives_recoverable_flag(tmp_path: Path):
    with RunRecorder("artifact-record", tmp_path / "run", task_id="task") as recorder:
        ref = recorder.write_artifact(
            "tool_result_original_content",
            "content",
            {"budget_policy": "preserve_text"},
        )

    record = ToolResultArtifactRecord(
        artifact_id="tool-result-001",
        tool_result_id="tool-result-001",
        tool_call_id="call-001",
        content_sha256=ref.sha256,
        size_chars=7,
        artifact_ref=ref,
        publishable_after_visibility_scan=True,
        recovery_unlocked_after_provider_commit=True,
        contamination_scan_status="clean",
    )

    assert record.model_visible_recoverable is True


def test_tool_result_artifact_record_does_not_unlock_candidate_stage(tmp_path: Path):
    with RunRecorder("artifact-record-candidate", tmp_path / "run", task_id="task") as recorder:
        ref = recorder.write_artifact(
            "tool_result_original_content",
            "content",
            {"budget_policy": "preserve_text"},
        )

    base = {
        "artifact_id": "tool-result-001",
        "tool_result_id": "tool-result-001",
        "tool_call_id": "call-001",
        "content_sha256": ref.sha256,
        "size_chars": 7,
        "artifact_ref": ref,
    }

    assert ToolResultArtifactRecord(**base).model_visible_recoverable is False
    assert ToolResultArtifactRecord(
        **base,
        publishable_after_visibility_scan=True,
        contamination_scan_status="clean",
    ).model_visible_recoverable is False
    assert ToolResultArtifactRecord(
        **base,
        model_visible_recoverable=True,
    ).model_visible_recoverable is False
    with pytest.raises(ValueError, match="必须已经通过可发布检查"):
        ToolResultArtifactRecord(
            **base,
            recovery_unlocked_after_provider_commit=True,
        )
    with pytest.raises(ValueError, match="contamination_scan_status 必须为 clean"):
        ToolResultArtifactRecord(
            **base,
            publishable_after_visibility_scan=True,
            contamination_scan_status="failed",
        )


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
