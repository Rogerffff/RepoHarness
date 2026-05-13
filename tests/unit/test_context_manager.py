from pathlib import Path

import pytest

from repo_harness.config import ContextManagementConfig
from repo_harness.context import ContextManager, ToolResultArtifactIndex
from repo_harness.context.schemas import ToolResultArtifactRecord
from repo_harness.trajectory import RunRecorder


def test_context_management_config_exposes_compact_policy_defaults():
    config = ContextManagementConfig()

    assert config.schema_version == "repo_harness_context_management_config_v1"
    assert config.initial_context_policy_version == (
        "repo_harness_initial_context_policy_v1_lean_hints"
    )
    assert config.repository_hints.mode == "balanced_eval"
    assert config.repository_hints.resolved_max_candidate_files == 8
    assert config.repository_hints.resolved_max_matched_terms_per_file == 6
    assert config.repository_hints.resolved_max_fallback_search_terms == 8
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
    assert config.repository_hints.mode == "balanced_eval"
    assert config.repository_hints.resolved_max_candidate_files == 8
    assert config.tool_result_compact_policy == "claude_code_fresh_only_v1"
    assert config.microcompact_enabled is True
    assert config.auto_compact_enabled is True


@pytest.mark.parametrize(
    ("mode", "expected_limit", "expected_fallback_terms", "expected_low_limit"),
    [
        ("disabled", 0, 0, 0),
        ("strict_eval", 3, 5, 0),
        ("balanced_eval", 8, 8, 0),
        ("weak_model_scaffold", 12, 8, 2),
    ],
)
def test_repository_hints_config_resolves_mode_defaults(
    mode: str,
    expected_limit: int,
    expected_fallback_terms: int,
    expected_low_limit: int,
):
    config = ContextManagementConfig.model_validate(
        {"repository_hints": {"mode": mode}}
    )

    assert config.repository_hints.resolved_max_candidate_files == expected_limit
    assert (
        config.repository_hints.resolved_max_fallback_search_terms
        == expected_fallback_terms
    )
    assert (
        config.repository_hints.resolved_include_low_confidence_limit
        == expected_low_limit
    )


def test_repository_hints_config_accepts_custom_limits():
    config = ContextManagementConfig.model_validate(
        {
            "repository_hints": {
                "mode": "custom",
                "max_candidate_files": 5,
                "include_low_confidence_limit": 1,
                "max_matched_terms_per_file": 4,
                "max_fallback_search_terms": 3,
            }
        }
    )

    assert config.repository_hints.resolved_max_candidate_files == 5
    assert config.repository_hints.resolved_max_matched_terms_per_file == 4
    assert config.repository_hints.resolved_max_fallback_search_terms == 3
    assert config.repository_hints.resolved_include_low_confidence_limit == 1
    assert config.repository_hints.max_matched_terms_per_file == 4
    assert config.repository_hints.max_fallback_search_terms == 3


def test_repository_hints_custom_mode_requires_explicit_candidate_limit():
    with pytest.raises(ValueError, match="max_candidate_files"):
        ContextManagementConfig.model_validate(
            {"repository_hints": {"mode": "custom"}}
        )


def test_repository_hints_disabled_mode_rejects_explicit_candidate_limit():
    with pytest.raises(ValueError, match="disabled"):
        ContextManagementConfig.model_validate(
            {"repository_hints": {"mode": "disabled", "max_candidate_files": 5}}
        )


def test_repository_hints_candidate_limit_has_upper_bound():
    with pytest.raises(ValueError):
        ContextManagementConfig.model_validate(
            {"repository_hints": {"mode": "custom", "max_candidate_files": 21}}
        )


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


def test_current_turn_aggregate_budget_persists_largest_fresh_tool_result(tmp_path: Path):
    large_content = "large tool output\n" * 80
    small_content = "small output\n" * 5
    messages = [
        {
            "role": "assistant",
            "content": "call tools",
            "turn": 1,
            "tool_calls": [
                {"tool_call_id": "call_large", "tool_name": "grep", "arguments": {}, "turn": 1},
                {"tool_call_id": "call_small", "tool_name": "read_file", "arguments": {}, "turn": 1},
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_large",
            "tool_result_id": "call_large_result",
            "tool_name": "grep",
            "content": large_content,
            "normalized_arguments": {"query": "needle"},
        },
        {
            "role": "tool",
            "tool_call_id": "call_small",
            "tool_result_id": "call_small_result",
            "tool_name": "read_file",
            "content": small_content,
            "normalized_arguments": {"path": "small.py"},
        },
    ]

    with RunRecorder("context-replacement", tmp_path / "run", task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
        prepared = ContextManager().prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(
                max_tool_results_per_turn_chars=len(small_content) + 20,
            ),
            tool_result_artifact_index=index,
        )

    large_replacement = prepared.messages[1]["content"]

    assert "<persisted-output>" in large_replacement
    assert "read_tool_result_artifact" in large_replacement
    assert prepared.messages[2]["content"] == small_content
    assert prepared.context_event.data["context_reduction"]["replaced_tool_result_ids"] == [
        "call_large_result"
    ]
    assert prepared.context_event.data["context_reduction"]["fresh_tool_result_ids"] == [
        "call_large_result",
        "call_small_result",
    ]
    assert len(index.records_by_artifact_id) == 1
    record = next(iter(index.records_by_artifact_id.values()))
    assert record.tool_result_id == "call_large_result"
    assert record.model_visible_recoverable is False
    assert prepared.content_replacement_state is not None
    large_state = next(
        item
        for item in prepared.content_replacement_state.records
        if item.original_tool_result_id == "call_large_result"
    )
    assert large_state.replacement_decision == "prepared_candidate"
    assert large_state.replaced is True


def test_uncommitted_candidate_does_not_freeze_replacement_decision(tmp_path: Path):
    content = "large tool output\n" * 80
    messages = [
        {
            "role": "assistant",
            "content": "call tool",
            "turn": 1,
            "tool_calls": [
                {"tool_call_id": "call_large", "tool_name": "grep", "arguments": {}, "turn": 1}
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_large",
            "tool_result_id": "call_large_result",
            "tool_name": "grep",
            "content": content,
            "normalized_arguments": {"query": "needle"},
        },
    ]
    manager = ContextManager()
    with RunRecorder("context-candidate", tmp_path / "run", task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10),
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10000),
        )

    assert "<persisted-output>" in str(first.messages[1]["content"])
    assert second.messages[1]["content"] == content
    assert second.context_event.data["context_reduction"]["replaced_tool_result_ids"] == []


def test_committed_full_visible_tool_result_is_not_later_replaced_by_l0_budget(tmp_path: Path):
    content = "visible once, then frozen"
    messages = [
        {
            "role": "assistant",
            "content": "call tool",
            "turn": 1,
            "tool_calls": [
                {"tool_call_id": "call_read", "tool_name": "read_file", "arguments": {}, "turn": 1}
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_read",
            "tool_result_id": "call_read_result",
            "tool_name": "read_file",
            "content": content,
            "normalized_arguments": {"path": "demo.py"},
        },
    ]
    manager = ContextManager()
    with RunRecorder("context-frozen-full", tmp_path / "run", task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10000),
        )
        commit = manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="model-call-1",
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=1),
        )

    assert commit["committed_full_visible_tool_result_ids"] == ["call_read_result"]
    assert second.messages[1]["content"] == content
    assert second.context_event.data["context_reduction"]["replaced_tool_result_ids"] == []
    state = second.content_replacement_state
    assert state is not None
    record = next(item for item in state.records if item.original_tool_result_id == "call_read_result")
    assert record.replacement_decision == "provider_committed_full_visible"


def test_committed_persisted_preview_is_replayed_and_recovery_unlocked(tmp_path: Path):
    content = "large tool output\n" * 80
    messages = [
        {
            "role": "assistant",
            "content": "call tool",
            "turn": 1,
            "tool_calls": [
                {"tool_call_id": "call_grep", "tool_name": "grep", "arguments": {}, "turn": 1}
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_grep",
            "tool_result_id": "call_grep_result",
            "tool_name": "grep",
            "content": content,
            "normalized_arguments": {"query": "needle"},
        },
    ]
    run_dir = tmp_path / "run"
    manager = ContextManager()
    with RunRecorder("context-frozen-preview", run_dir, task_id="task") as recorder:
        index = ToolResultArtifactIndex(run_dir=run_dir)
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10),
            tool_result_artifact_index=index,
        )
        first_preview = first.messages[1]["content"]
        commit = manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="model-call-1",
            tool_result_artifact_index=index,
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10000),
            tool_result_artifact_index=index,
        )

    assert commit["committed_persisted_preview_tool_result_ids"] == ["call_grep_result"]
    assert len(commit["unlocked_tool_result_artifact_ids"]) == 1
    artifact_id = commit["unlocked_tool_result_artifact_ids"][0]
    assert index.records_by_artifact_id[artifact_id].model_visible_recoverable is True
    assert second.messages[1]["content"] == first_preview
    assert second.context_event.data["context_reduction"]["reapplied_persisted_tool_result_ids"] == [
        "call_grep_result"
    ]


def test_microcompact_clears_old_committed_compactable_tool_results(tmp_path: Path):
    messages = _tool_result_messages(count=32, tool_name="read_file")
    manager = ContextManager()
    with RunRecorder("context-microcompact", tmp_path / "run", task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(
                microcompact_trigger_compactable_tool_result_chars=1000,
            ),
        )
        manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="model-call-1",
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

    reduction = second.context_event.data["context_reduction"]
    cleared_ids = [f"call_{index}_result" for index in range(17)]
    kept_ids = [f"call_{index}_result" for index in range(17, 32)]

    assert reduction["microcompact_applied"] is True
    assert reduction["microcompact_cleared_tool_result_ids"] == cleared_ids
    assert reduction["microcompact_kept_recent_tool_result_ids"] == kept_ids
    assert second.context_event.data["tool_pairing_validation"]["ok"] is True
    for message in second.messages[1:18]:
        assert message["content"] == "[Old tool result content cleared]"
        assert message["typed"]["microcompact_cleared"] is True
        assert message["typed"]["microcompact_recovery_status"] == "raw_trajectory_only"
    for message in second.messages[18:]:
        assert message["content"] != "[Old tool result content cleared]"
    state = second.content_replacement_state
    assert state is not None
    assert {
        record.replacement_decision
        for record in state.records
        if record.original_tool_result_id in cleared_ids
    } == {"provider_committed_full_visible"}


def test_microcompact_skips_non_allowlisted_tool_results(tmp_path: Path):
    messages = _tool_result_messages(count=32, tool_name="run_tests")
    manager = ContextManager()
    with RunRecorder("context-microcompact-skip", tmp_path / "run", task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(
                microcompact_trigger_compactable_tool_result_chars=1000,
            ),
        )
        manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="model-call-1",
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

    assert second.context_event.data["context_reduction"]["microcompact_applied"] is False
    assert all(
        message["content"] != "[Old tool result content cleared]"
        for message in second.messages
        if message.get("role") == "tool"
    )


def test_microcompact_does_not_clear_committed_persisted_preview(tmp_path: Path):
    content = "large tool output\n" * 80
    messages = [
        {
            "role": "assistant",
            "content": "call tool",
            "turn": 1,
            "tool_calls": [
                {"tool_call_id": "call_grep", "tool_name": "grep", "arguments": {}, "turn": 1}
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_grep",
            "tool_result_id": "call_grep_result",
            "tool_name": "grep",
            "content": content,
            "normalized_arguments": {"query": "needle"},
        },
    ]
    manager = ContextManager()
    with RunRecorder("context-microcompact-preview", tmp_path / "run", task_id="task") as recorder:
        first = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=1,
            context_config=ContextManagementConfig(max_tool_results_per_turn_chars=10),
        )
        manager.commit_prepared_tool_result_decisions(
            context_revision=first.context_revision,
            prepared_messages_ref=first.prepared_messages_ref,
            model_call_id="model-call-1",
        )
        second = manager.prepare_messages(
            messages=messages,
            recorder=recorder,
            task_id="task",
            turn=2,
            context_config=ContextManagementConfig(
                microcompact_trigger_compactable_tool_result_count=1,
                microcompact_trigger_compactable_tool_result_chars=1,
            ),
        )

    assert second.context_event.data["context_reduction"]["microcompact_applied"] is False
    assert second.messages[1]["content"] == first.messages[1]["content"]


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
