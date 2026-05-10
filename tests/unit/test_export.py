import json
import hashlib
from pathlib import Path

import pytest

from repo_harness.errors import ExportError
from repo_harness.export import CompareScope, ExportPolicy, inspect_export
from repo_harness.export.exporter import (
    export_preference_jsonl,
    export_provider_reasoning_trace_training_export,
    export_rl_jsonl,
    export_run_or_runs,
    export_sft_jsonl,
)
from repo_harness.export.exporter import _sanitize_text


FORBIDDEN_FORMAL_FIELDS = {
    "final_verifier_ref",
    "reward_metadata_ref",
    "reward_metadata",
    "verifier",
    "run_outcome",
    "final_verifier_status",
    "chosen_run_metadata",
    "rejected_run_metadata",
    "chosen_verifier_result_ref",
    "rejected_verifier_result_ref",
}


def test_preference_export_writes_skipped_manifest_when_not_enough_runs(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run_one"
    run_dir.mkdir(parents=True)
    (run_dir / "metrics.json").write_text('{"run_outcome": "success"}\n', encoding="utf-8")
    (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (run_dir / "baseline.json").write_text('{"task_id": "task_001"}\n', encoding="utf-8")

    output = export_preference_jsonl(runs_dir)

    payload = json.loads(output.read_text(encoding="utf-8"))
    export_dir = _latest_export_dir(runs_dir / "exports")
    assert output.name == "preference_skipped.json"
    assert payload["filter_status"] == "skipped"
    assert payload["reason"] == "not_enough_runs_for_same_task"
    assert (export_dir / "preference_skipped.json").exists()
    assert (export_dir / "export_manifest.json").exists()
    assert (export_dir / "audit_report.json").exists()
    assert (export_dir / "audit_report.md").exists()


def test_export_sanitizes_provider_credentials():
    text = (
        "Authorization: Bearer sk-testsecret123456789 "
        "api_key=abc123456789 password: hunter2 token='tok_123456789'"
    )

    sanitized = _sanitize_text(text)

    assert "sk-testsecret" not in sanitized
    assert "abc123456789" not in sanitized
    assert "hunter2" not in sanitized
    assert "tok_123456789" not in sanitized
    assert sanitized.count("<REDACTED_CREDENTIAL>") >= 3


def test_provider_reasoning_trace_export_requires_explicit_policy(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_reasoning_trace_no_policy",
        task_id="task_001",
        include_formal_verifier=True,
    )
    _add_reasoning_trace_artifact(run_dir, "DeepSeek private reasoning target")

    with pytest.raises(ExportError, match="allow_provider_reasoning_trace_training=true"):
        export_provider_reasoning_trace_training_export(run_dir)


def test_provider_reasoning_trace_export_is_isolated_from_default_exports(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_reasoning_trace",
        task_id="task_001",
        include_formal_verifier=True,
    )
    _add_reasoning_trace_artifact(run_dir, "DeepSeek private reasoning target")

    default_sft = export_sft_jsonl(run_dir)
    default_rl = export_rl_jsonl(run_dir)
    output = export_provider_reasoning_trace_training_export(
        run_dir,
        policy=ExportPolicy(allow_provider_reasoning_trace_training=True),
    )
    export_dir = _latest_export_dir(run_dir / "exports")
    manifest = json.loads((export_dir / "export_manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))
    record = _read_jsonl(output)[0]

    assert "DeepSeek private reasoning target" not in default_sft.read_text(encoding="utf-8")
    assert "DeepSeek private reasoning target" not in default_rl.read_text(encoding="utf-8")
    assert output.name == "provider_reasoning_trace_training_export.jsonl"
    assert manifest["format"] == "provider_reasoning_trace_training_export"
    assert manifest["included_count"] == 1
    assert audit["status"] == "passed"
    assert record["payload"]["reasoning_trace_targets"][0]["target"]["reasoning_content"] == (
        "DeepSeek private reasoning target"
    )
    assert record["payload"]["ordinary_sft_target_allowed"] is False
    assert record["payload"]["requires_explicit_reasoning_export_policy"] is True
    assert record["payload"]["reasoning_trace_targets"][0]["raw_provider_artifact"] is False
    assert "Inspect export: clean" in inspect_export(export_dir, assert_clean=True, require_trainable_samples=True)


def test_provider_reasoning_trace_export_available_through_dispatcher(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_reasoning_trace_dispatch",
        task_id="task_001",
        include_formal_verifier=True,
    )
    _add_reasoning_trace_artifact(run_dir, "dispatch reasoning target")

    output = export_run_or_runs(
        run_dir,
        export_format="provider_reasoning_trace_training_export",
        policy=ExportPolicy(allow_provider_reasoning_trace_training=True),
    )

    assert _read_jsonl(output)[0]["payload"]["reasoning_trace_targets"][0]["target"][
        "reasoning_content"
    ] == "dispatch reasoning target"


def test_default_sft_export_excludes_harness_convergence_nudge_context(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_convergence_nudge_export",
        task_id="task_001",
        include_formal_verifier=True,
    )
    (run_dir / "transcript.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_id": "record_1",
                        "run_id": run_dir.name,
                        "task_id": "task_001",
                        "message_id": "initial_0",
                        "turn": 0,
                        "role": "system",
                        "content_preview": "system",
                        "model_visible": True,
                        "trainable": False,
                        "created_at": "2026-05-08T00:00:00+00:00",
                    }
                ),
                json.dumps(
                    {
                        "record_id": "record_2",
                        "run_id": run_dir.name,
                        "task_id": "task_001",
                        "message_id": "convergence_nudge_3_1",
                        "turn": 3,
                        "role": "user",
                        "content_preview": json.dumps(
                            {
                                "repo_harness_control_message": {
                                    "type": "convergence_nudge",
                                    "policy_version": "repo_harness_convergence_nudge_v1",
                                }
                            }
                        ),
                        "model_visible": True,
                        "trainable": False,
                        "created_at": "2026-05-08T00:00:01+00:00",
                    }
                ),
                json.dumps(
                    {
                        "record_id": "record_3",
                        "run_id": run_dir.name,
                        "task_id": "task_001",
                        "message_id": "context_warning_4_warning_80",
                        "turn": 4,
                        "role": "user",
                        "content_preview": json.dumps(
                            {
                                "repo_harness_control_message": {
                                    "type": "context_warning",
                                    "policy_version": "repo_harness_context_warning_v1",
                                }
                            }
                        ),
                        "model_visible": True,
                        "trainable": False,
                        "created_at": "2026-05-08T00:00:02+00:00",
                    }
                ),
                json.dumps(
                    {
                        "record_id": "record_4",
                        "run_id": run_dir.name,
                        "task_id": "task_001",
                        "message_id": "assistant_4",
                        "turn": 4,
                        "role": "assistant",
                        "content_preview": "final answer",
                        "model_visible": True,
                        "trainable": True,
                        "created_at": "2026-05-08T00:00:03+00:00",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    output = export_sft_jsonl(run_dir)
    record = _read_jsonl(output)[0]
    payload_text = json.dumps(record["payload"], ensure_ascii=False)

    assert record["payload"]["excluded_harness_control_message_count"] == 2
    assert "convergence_nudge" not in payload_text
    assert "context_warning" not in payload_text
    assert [message["role"] for message in record["payload"]["messages"]] == ["system", "assistant"]


def test_rl_export_without_formal_final_verifier_is_invalid_for_training(tmp_path: Path):
    run_dir = _minimal_run(tmp_path / "run_missing_formal", task_id="task_001")

    output = export_rl_jsonl(run_dir)
    export_dir = _latest_export_dir(run_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((export_dir / "export_manifest.json").read_text(encoding="utf-8"))

    assert _read_jsonl(output) == []
    assert manifest["included_count"] == 0
    assert manifest["invalid_count"] == 1
    assert audit["samples"][0]["invalid_for_training"] is True
    assert audit["samples"][0]["invalid_reason"] == "missing_formal_final_verifier"


def test_rl_export_filters_invalid_reward_sample_even_with_formal_verifier(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_invalid_reward",
        task_id="task_001",
        reward=0.0,
        include_formal_verifier=True,
    )
    (run_dir / "reward.json").write_text(
        json.dumps(
            {
                "final_reward": 0.0,
                "reward_version": "repo_harness_reward_v0",
                "invalid_for_training": True,
                "invalid_reason": "task_timeout_before_final_verifier",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output = export_rl_jsonl(run_dir)
    export_dir = _latest_export_dir(run_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((export_dir / "export_manifest.json").read_text(encoding="utf-8"))

    assert _read_jsonl(output) == []
    assert manifest["included_count"] == 0
    assert manifest["invalid_count"] == 1
    assert audit["samples"][0]["invalid_reason"] == "task_timeout_before_final_verifier"


def test_export_rejects_manifest_artifact_path_escape(tmp_path: Path):
    run_dir = _minimal_run(tmp_path / "runs" / "run_escape", task_id="task_001")
    leak = tmp_path / "leak.json"
    leak.write_text('{"messages": [{"role": "system", "content": "LEAK"}]}\n', encoding="utf-8")
    (run_dir / "artifacts.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_run_v0",
                "run_id": "run_escape",
                "artifacts": [
                    {
                        "schema_version": "repo_harness_artifact_v0",
                        "artifact_id": "escape_artifact",
                        "relative_path": "../../leak.json",
                        "kind": "prepared_messages",
                        "sha256": "not_checked_before_fix",
                        "size_bytes": 1,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output = export_rl_jsonl(run_dir)
    export_dir = _latest_export_dir(run_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))

    assert _read_jsonl(output) == []
    assert audit["status"] == "failed"
    assert audit["samples"][0]["training_eligibility"] == "invalid"
    assert audit["samples"][0]["invalid_reason"] == "artifact_manifest_invalid"


def test_sft_export_uses_structured_tool_call_events_not_preview(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_structured_sft",
        task_id="task_001",
        include_formal_verifier=True,
    )
    long_content = "x" * 5000
    (run_dir / "transcript.jsonl").write_text(
        json.dumps(
            {
                "role": "assistant",
                "turn": 1,
                "content_preview": "[{'tool_call_id': 'call_big', 'tool_name': 'create_file', 'arguments': {'content': '",
                "model_visible": True,
                "trainable": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool_requested",
                "turn": 1,
                "data": {
                    "tool_call_id": "call_big",
                    "tool_name": "create_file",
                    "arguments": {"path": "big.txt", "content": long_content},
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "tool_completed",
                "turn": 1,
                "data": {
                    "tool_call_id": "call_big",
                    "status": "ok",
                    "effective_tool_name": "create_file",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output = export_sft_jsonl(run_dir)
    record = _read_jsonl(output)[0]
    assistant = next(message for message in record["payload"]["messages"] if message["role"] == "assistant")

    assert assistant["content"] is None
    assert assistant["tool_calls"][0]["tool_call_id"] == "call_big"
    assert assistant["tool_calls"][0]["arguments"]["content"] == long_content


def test_preference_export_pairs_equal_reward_when_outcome_differs(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(
        runs_dir / "run_success",
        task_id="task_001",
        reward=0.5,
        run_outcome="success",
        final_verifier_status="accepted",
        include_formal_verifier=True,
    )
    _minimal_run(
        runs_dir / "run_failed",
        task_id="task_001",
        reward=0.5,
        run_outcome="failed",
        final_verifier_status="failed",
        include_formal_verifier=True,
    )

    output = export_preference_jsonl(runs_dir)
    skipped = json.loads(output.read_text(encoding="utf-8"))

    assert output.name == "preference_skipped.json"
    assert skipped["blocked_reason_distribution"] == {"reward_tie": 1}


def test_export_writes_manifest_audit_and_formal_trainable_file(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_trainable",
        task_id="task_001",
        include_formal_verifier=True,
    )

    output = export_rl_jsonl(run_dir)
    export_dir = _latest_export_dir(run_dir / "exports")
    manifest = json.loads((export_dir / "export_manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))
    data_file = export_dir / "data.rl.jsonl"
    data_records = _read_jsonl(data_file)

    assert output == run_dir / "exports" / "rl.jsonl"
    assert data_file.exists()
    assert (export_dir / "audit_report.md").exists()
    assert manifest["included_count"] == 1
    assert manifest["data_files"][0]["relative_path"] == "data.rl.jsonl"
    assert audit["status"] == "passed"
    assert data_records[0]["quality"]["training_eligibility"] == "trainable"
    assert _forbidden_formal_field_paths(data_records[0]) == []
    assert "Inspect export: clean" in inspect_export(export_dir, assert_clean=True, require_trainable_samples=True)


def test_formal_trainable_jsonl_omits_evaluator_and_result_fields(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_clean_training_payload",
        task_id="task_001",
        reward=1.0,
        include_formal_verifier=True,
    )
    sft_record = _read_jsonl(export_sft_jsonl(run_dir))[0]
    rl_record = _read_jsonl(export_rl_jsonl(run_dir))[0]

    preference_runs = tmp_path / "preference_runs"
    _minimal_run(
        preference_runs / "chosen",
        task_id="task_001",
        reward=1.0,
        include_formal_verifier=True,
    )
    _minimal_run(
        preference_runs / "rejected",
        task_id="task_001",
        reward=0.0,
        run_outcome="failed",
        final_verifier_status="failed",
        include_formal_verifier=True,
    )
    preference_record = _read_jsonl(export_preference_jsonl(preference_runs))[0]

    for record in (sft_record, rl_record, preference_record):
        assert record["quality"]["training_eligibility"] == "trainable"
        assert _forbidden_formal_field_paths(record) == []


def test_exports_use_one_record_per_model_input_snapshot(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_snapshot_export",
        task_id="task_001",
        reward=1.0,
        include_formal_verifier=True,
    )
    first = _add_model_input_snapshot_fixture(
        run_dir,
        index=1,
        model_visible_content="first visible input",
        assistant_content="first answer",
    )
    second = _add_model_input_snapshot_fixture(
        run_dir,
        index=2,
        model_visible_content="post compact summary",
        assistant_content="answer after compact",
    )

    sft_records = _read_jsonl(export_sft_jsonl(run_dir))
    rl_records = _read_jsonl(export_rl_jsonl(run_dir))
    sft_text = json.dumps(sft_records, ensure_ascii=False)
    second_rl_prompt = rl_records[1]["payload"]["prompt"]
    second_rl_text = json.dumps(second_rl_prompt, ensure_ascii=False)

    assert len(sft_records) == 2
    assert len(rl_records) == 2
    assert sft_records[0]["payload"]["model_input_snapshot_ref"]["artifact_id"] == (
        first["snapshot_ref"]["artifact_id"]
    )
    assert sft_records[1]["payload"]["model_input_snapshot_ref"]["artifact_id"] == (
        second["snapshot_ref"]["artifact_id"]
    )
    assert sft_records[1]["payload"]["model_call_id"] == "run_snapshot_export_model_call_0002"
    assert sft_records[1]["payload"]["training_sample_source"] == "model_input_snapshot"
    assert sft_records[1]["payload"]["messages"][0]["content"] == "post compact summary"
    assert sft_records[1]["payload"]["messages"][-1]["content"] == "answer after compact"
    assert rl_records[1]["payload"]["prompt"]["model_input_snapshot_ref"]["artifact_id"] == (
        second["snapshot_ref"]["artifact_id"]
    )
    assert second_rl_prompt["provider_request_projection_hash"] == "4" * 64
    assert second_rl_prompt["provider_request_artifact_ref"]["kind"] == "raw_replay_request"
    assert second_rl_prompt["provider_response_artifact_ref"]["kind"] == "raw_replay_response"
    assert "post compact summary" in second_rl_text
    assert "first visible input" not in second_rl_text
    assert "first visible input" in sft_text
    assert "post compact summary" in sft_text


def test_export_downgrades_max_turns_success_to_diagnostic_only(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_max_turns_success",
        task_id="task_001",
        reward=0.996,
        run_outcome="success",
        final_verifier_status="accepted",
        include_formal_verifier=True,
    )
    _write_max_turns_metrics_and_events(run_dir)

    sft_output = export_sft_jsonl(run_dir)
    sft_export_dir = _latest_export_dir(run_dir / "exports")
    sft_audit = json.loads((sft_export_dir / "audit_report.json").read_text(encoding="utf-8"))
    rl_output = export_rl_jsonl(run_dir)
    rl_export_dir = _latest_export_dir(run_dir / "exports")
    rl_audit = json.loads((rl_export_dir / "audit_report.json").read_text(encoding="utf-8"))

    for output, audit in ((sft_output, sft_audit), (rl_output, rl_audit)):
        assert _read_jsonl(output) == []
        sample = audit["samples"][0]
        assert sample["training_eligibility"] == "diagnostic_only"
        assert sample["invalid_for_training"] is True
        assert {
            "agent_stop_reason_max_turns",
            "require_model_final_not_satisfied",
            "last_tool_observation_not_observed_by_model",
        }.issubset(set(sample["quality_reasons"]))
        assert any(
            item["name"] == "trajectory_terminal_quality"
            and item["status"] == "warning"
            for item in sample["audit_items"]
        )


def test_provider_raw_response_in_payload_is_audit_invalid(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_provider_raw",
        task_id="task_001",
        include_formal_verifier=True,
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool_requested",
                "turn": 1,
                "data": {
                    "tool_call_id": "call_raw",
                    "tool_name": "create_file",
                    "arguments": {"path": "raw.txt", "content": "raw_response should not be targeted"},
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "tool_completed",
                "turn": 1,
                "data": {"tool_call_id": "call_raw", "status": "ok"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "transcript.jsonl").write_text(
        json.dumps(
            {
                "role": "assistant",
                "turn": 1,
                "content_preview": "",
                "model_visible": True,
                "trainable": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output = export_sft_jsonl(run_dir)
    export_dir = _latest_export_dir(run_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))

    assert _read_jsonl(output) == []
    assert audit["status"] == "failed"
    assert audit["samples"][0]["training_eligibility"] == "invalid"
    assert audit["samples"][0]["invalid_reason"] == "contains blocked marker raw_response"
    with pytest.raises(ExportError, match="audit_report status is failed"):
        inspect_export(export_dir, assert_clean=True)


def test_preference_export_audits_underlying_source_runs(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(
        runs_dir / "run_success",
        task_id="task_001",
        reward=1.0,
        run_outcome="success",
        include_formal_verifier=True,
    )
    _minimal_run(
        runs_dir / "run_failed",
        task_id="task_001",
        reward=0.0,
        run_outcome="failed",
        final_verifier_status="failed",
        include_formal_verifier=False,
    )

    output = export_preference_jsonl(runs_dir)
    skipped = json.loads(output.read_text(encoding="utf-8"))
    export_dir = _latest_export_dir(runs_dir / "exports")

    assert skipped["blocked_pair_count"] == 1
    assert skipped["blocked_reason_distribution"] == {"missing_formal_final_verifier": 1}
    assert (export_dir / "preference_skipped.json").exists()


def test_export_metadata_reads_v2_run_config_facts(tmp_path: Path):
    run_dir = _minimal_run(
        tmp_path / "run_metadata_facts",
        task_id="task_001",
        include_formal_verifier=True,
    )

    output = export_rl_jsonl(run_dir)
    record = _read_jsonl(output)[0]

    assert record["metadata"]["metadata_source"] == "v2"
    assert record["metadata"]["provider"] == "replay"
    assert record["metadata"]["model_id"] == "replay-script-v0"
    assert record["metadata"]["scaffold_version"] == "repo_harness_simple_react_v0"
    assert record["metadata"]["tool_schema_snapshot_hash"] == "b" * 64


def test_preference_export_blocks_base_commit_mismatch(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(runs_dir / "run_a", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(runs_dir / "run_b", task_id="task_001", reward=0.0, include_formal_verifier=True)
    _update_run_config(runs_dir / "run_b", {"base_commit": "other"})

    output = export_preference_jsonl(runs_dir)
    skipped = json.loads(output.read_text(encoding="utf-8"))

    assert skipped["blocked_reason_distribution"] == {"compare_key_mismatch": 1}


def test_preference_export_blocks_tool_schema_snapshot_mismatch(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(runs_dir / "run_a", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(runs_dir / "run_b", task_id="task_001", reward=0.0, include_formal_verifier=True)
    _update_run_config(
        runs_dir / "run_b",
        {"tool_protocol": {"tool_schema_snapshot_sha256": "d" * 64}},
        merge_tool_protocol=True,
    )

    output = export_preference_jsonl(runs_dir)
    skipped = json.loads(output.read_text(encoding="utf-8"))

    assert skipped["blocked_reason_distribution"] == {"tool_schema_snapshot_mismatch": 1}


def test_preference_export_blocks_context_policy_snapshot_mismatch(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(runs_dir / "run_a", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(runs_dir / "run_b", task_id="task_001", reward=0.0, include_formal_verifier=True)
    _update_run_config(
        runs_dir / "run_a",
        {
            "context_policy_snapshot_hash": "c" * 64,
            "tool_result_compact_policy": "claude_code_fresh_only_v1",
        },
    )
    _update_run_config(
        runs_dir / "run_b",
        {
            "context_policy_snapshot_hash": "d" * 64,
            "tool_result_compact_policy": "different_policy",
        },
    )

    output = export_preference_jsonl(runs_dir)
    skipped = json.loads(output.read_text(encoding="utf-8"))

    assert skipped["blocked_reason_distribution"] == {"context_policy_mismatch": 1}


def test_preference_export_blocks_scaffold_mismatch_unless_compare_scope_allows(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(runs_dir / "run_a", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(runs_dir / "run_b", task_id="task_001", reward=0.0, include_formal_verifier=True)
    _update_run_config(
        runs_dir / "run_b",
        {
            "scaffold_id": "single_shot_patch",
            "scaffold_version": "repo_harness_single_shot_patch_v0",
        },
    )

    blocked = json.loads(export_preference_jsonl(runs_dir).read_text(encoding="utf-8"))
    compare_scope_path = tmp_path / "compare_scope.json"
    compare_scope_path.write_text(
        json.dumps(
            CompareScope(
                experimental_variables=["scaffold_id", "scaffold_version"],
                training_export_allowed=True,
            ).model_dump(mode="json"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    allowed_output = export_preference_jsonl(runs_dir, compare_scope_path=compare_scope_path)

    assert blocked["blocked_reason_distribution"] == {"compare_key_mismatch": 1}
    assert _read_jsonl(allowed_output)[0]["metadata"]["compare_scope"]["experimental_variables"] == [
        "scaffold_id",
        "scaffold_version",
    ]


def test_preference_export_allows_different_seed_same_compare_key(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(runs_dir / "run_seed_1", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(runs_dir / "run_seed_2", task_id="task_001", reward=0.0, include_formal_verifier=True)
    _update_run_config(runs_dir / "run_seed_1", {"seed": 1})
    _update_run_config(runs_dir / "run_seed_2", {"seed": 2})

    output = export_preference_jsonl(runs_dir)

    assert _read_jsonl(output)


def test_preference_export_blocks_reward_tie_and_missing_reward(tmp_path: Path):
    tie_runs = tmp_path / "tie_runs"
    _minimal_run(tie_runs / "run_a", task_id="task_001", reward=0.5, include_formal_verifier=True)
    _minimal_run(tie_runs / "run_b", task_id="task_001", reward=0.5, include_formal_verifier=True)
    tie_output = export_preference_jsonl(tie_runs)

    missing_runs = tmp_path / "missing_runs"
    _minimal_run(missing_runs / "run_a", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(missing_runs / "run_b", task_id="task_001", reward=0.0, include_formal_verifier=True)
    (missing_runs / "run_b" / "reward.json").unlink()
    missing_output = export_preference_jsonl(missing_runs)

    assert json.loads(tie_output.read_text(encoding="utf-8"))["blocked_reason_distribution"] == {"reward_tie": 1}
    assert json.loads(missing_output.read_text(encoding="utf-8"))["blocked_reason_distribution"] == {"missing_reward": 1}


def test_preference_export_blocks_non_formal_verifier_source(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(runs_dir / "run_a", task_id="task_001", reward=1.0, include_formal_verifier=True)
    _minimal_run(runs_dir / "run_b", task_id="task_001", reward=0.0, include_formal_verifier=True)
    (runs_dir / "run_b" / "verifier.json").write_text(
        json.dumps({"verifier_stage": "feedback"}) + "\n",
        encoding="utf-8",
    )

    output = export_preference_jsonl(runs_dir)
    skipped = json.loads(output.read_text(encoding="utf-8"))

    assert skipped["blocked_reason_distribution"] == {"non_formal_reward_source": 1}


def _minimal_run(
    run_dir: Path,
    *,
    task_id: str,
    reward: float = 0.0,
    run_outcome: str = "success",
    final_verifier_status: str = "accepted",
    include_formal_verifier: bool = False,
    include_run_metadata: bool = True,
) -> Path:
    run_dir.mkdir(parents=True)
    (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "baseline.json").write_text(
        json.dumps({"task_id": task_id}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_outcome": run_outcome,
                "final_verifier_status": final_verifier_status,
                "interaction_efficiency": {"final_verifier_mode": "strict_patch_replay"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "reward.json").write_text(
        json.dumps({"final_reward": reward, "reward_version": "repo_harness_reward_v0"}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "final.patch").write_text("diff --git a/demo.py b/demo.py\n", encoding="utf-8")
    if include_formal_verifier:
        (run_dir / "verifier.json").write_text(
            json.dumps({"verifier_stage": "final"}) + "\n",
            encoding="utf-8",
        )
    if include_run_metadata:
        _write_minimal_v2_metadata(run_dir)
    return run_dir


def _add_reasoning_trace_artifact(run_dir: Path, reasoning_content: str) -> None:
    artifact_path = run_dir / "artifacts" / "deepseek_reasoning_trace.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "repo_harness_provider_reasoning_trace_training_source_v0",
        "provider": "deepseek",
        "state_id": f"{run_dir.name}_model_call_0001_deepseek_reasoning",
        "run_id": run_dir.name,
        "model_call_id": f"{run_dir.name}_model_call_0001",
        "target_kind": "provider_reasoning_trace",
        "reasoning_content": reasoning_content,
        "reasoning_trace_training_allowed": True,
        "ordinary_sft_target_allowed": False,
        "default_training_payload_allowed": False,
        "not_public_safe_by_default": True,
        "public_demo_allowed": False,
        "requires_explicit_reasoning_export_policy": True,
        "raw_provider_artifact": False,
    }
    artifact_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "artifact_deepseek_reasoning_trace",
        "relative_path": "artifacts/deepseek_reasoning_trace.json",
        "kind": "deepseek_provider_reasoning_trace",
        "sha256": _sha256_file(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
        "redaction_status": "not_redacted_explicit_reasoning_trace_opt_in",
        "retention_policy": "provider_reasoning_trace_training_opt_in",
    }
    manifest_path = run_dir / "artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.setdefault("artifacts", [])
    artifacts.append(ref)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")


def _add_model_input_snapshot_fixture(
    run_dir: Path,
    *,
    index: int,
    model_visible_content: str,
    assistant_content: str,
) -> dict[str, dict]:
    model_call_id = f"{run_dir.name}_model_call_{index:04d}"
    state_ref = _append_json_artifact(
        run_dir,
        kind="content_replacement_state",
        filename=f"content_replacement_state_{index}.json",
        payload={
            "schema_version": "repo_harness_content_replacement_state_v0",
            "state_hash": f"{index}" * 64,
            "records": [],
            "seen_tool_result_ids": [],
            "last_context_revision": index,
        },
    )
    model_input_hash = f"{index}" * 64
    prepared_ref = _append_json_artifact(
        run_dir,
        kind="prepared_messages",
        filename=f"prepared_messages_{index}.json",
        payload={
            "messages": [{"role": "user", "content": model_visible_content}],
            "context_revision": index,
            "model_input_hash": model_input_hash,
            "content_replacement_state_ref": state_ref,
        },
    )
    request_ref = _append_json_artifact(
        run_dir,
        kind="raw_replay_request",
        filename=f"raw_replay_request_{index}.json",
        payload={
            "model_call_id": model_call_id,
            "prepared_messages_ref": prepared_ref,
            "model_input_hash": model_input_hash,
        },
    )
    response_ref = _append_json_artifact(
        run_dir,
        kind="raw_replay_response",
        filename=f"raw_replay_response_{index}.json",
        payload={"model_call_id": model_call_id, "status": "ok"},
    )
    assistant_ref = _append_json_artifact(
        run_dir,
        kind="assistant_message",
        filename=f"assistant_message_{index}.json",
        payload={
            "schema_version": "repo_harness_assistant_message_transcript_payload_v0",
            "content": assistant_content,
            "tool_calls": [],
            "finish_reason": "stop",
            "model_error_type": None,
        },
    )
    snapshot_ref = _append_json_artifact(
        run_dir,
        kind="model_input_snapshot",
        filename=f"model_input_snapshot_{index}.json",
        payload={
            "schema_version": "repo_harness_model_input_snapshot_v1",
            "model_call_id": model_call_id,
            "prepared_messages_ref": prepared_ref,
            "model_input_hash": model_input_hash,
            "provider_request_projection_hash": f"{index + 2}" * 64,
            "context_policy_snapshot_ref": None,
            "provider_request_artifact_ref": request_ref,
            "provider_response_artifact_ref": response_ref,
            "context_compact_state_ref": state_ref,
            "trainable": True,
        },
    )
    _append_jsonl(
        run_dir / "events.jsonl",
        {
            "event_type": "model_input_accepted",
            "turn": index,
            "data": {
                "model_call_id": model_call_id,
                "model_input_snapshot_ref": snapshot_ref,
                "prepared_messages_ref": prepared_ref,
                "model_input_hash": model_input_hash,
            },
        },
    )
    _append_jsonl(
        run_dir / "events.jsonl",
        {
            "event_type": "model_call_completed",
            "turn": index,
            "data": {
                "model_call_id": model_call_id,
                "provider": "replay",
                "model_id": "replay-script-v0",
                "model_error_type": None,
                "raw_provider_request_ref": request_ref,
                "raw_provider_response_ref": response_ref,
            },
        },
    )
    _append_jsonl(
        run_dir / "transcript.jsonl",
        {
            "role": "assistant",
            "turn": index,
            "model_call_id": model_call_id,
            "content_preview": assistant_content,
            "content_artifact_refs": [assistant_ref],
            "model_visible": True,
            "trainable": True,
        },
    )
    return {
        "prepared_ref": prepared_ref,
        "snapshot_ref": snapshot_ref,
        "assistant_ref": assistant_ref,
    }


def _append_json_artifact(
    run_dir: Path,
    *,
    kind: str,
    filename: str,
    payload: dict,
) -> dict:
    artifact_path = run_dir / "artifacts" / filename
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": f"artifact_{filename.replace('.', '_')}",
        "relative_path": f"artifacts/{filename}",
        "kind": kind,
        "sha256": _sha256_file(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
        "redaction_status": "not_sensitive",
        "retention_policy": "keep",
    }
    manifest_path = run_dir / "artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("artifacts", []).append(ref)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    return ref


def _append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_max_turns_metrics_and_events(run_dir: Path) -> None:
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_outcome": "success",
                "final_verifier_status": "accepted",
                "interaction_efficiency": {
                    "agent_stop_reason": "max_turns",
                    "feedback_tests_passed_policy": "require_model_final",
                    "final_verifier_mode": "strict_patch_replay",
                    "feedback_verifier_accepted": False,
                    "public_tests_ran": False,
                    "hidden_feedback_ran": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool_requested",
                "turn": 8,
                "data": {
                    "tool_call_id": "call_final_edit",
                    "tool_name": "edit_file",
                    "arguments": {"path": "calculator.py", "old_text": "bad", "new_text": "good"},
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "tool_completed",
                "turn": 8,
                "data": {
                    "tool_call_id": "call_final_edit",
                    "status": "ok",
                    "effective_tool_name": "edit_file",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _forbidden_formal_field_paths(value: object, path: str = "$") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, nested in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_FORMAL_FIELDS:
                paths.append(child_path)
            paths.extend(_forbidden_formal_field_paths(nested, child_path))
        return paths
    if isinstance(value, list):
        paths = []
        for index, nested in enumerate(value):
            paths.extend(_forbidden_formal_field_paths(nested, f"{path}[{index}]"))
        return paths
    return []


def _latest_export_dir(exports_dir: Path) -> Path:
    export_dirs = [
        path
        for path in exports_dir.iterdir()
        if path.is_dir() and (path / "export_manifest.json").exists()
    ]
    assert export_dirs
    return max(export_dirs, key=lambda path: path.stat().st_mtime_ns)


def _write_minimal_v2_metadata(run_dir: Path) -> None:
    snapshot_sha = "b" * 64
    tool_snapshot_path = run_dir / "artifacts" / "tool_schema_snapshot.json"
    tool_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    tool_snapshot_path.write_text(
        json.dumps({"snapshot_id": "snapshot_001", "snapshot_sha256": snapshot_sha}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    artifact_sha = _sha256_file(tool_snapshot_path)
    artifact_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "artifact_tool_schema_snapshot",
        "relative_path": "artifacts/tool_schema_snapshot.json",
        "kind": "tool_schema_snapshot",
        "sha256": artifact_sha,
        "size_bytes": tool_snapshot_path.stat().st_size,
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    tool_protocol = {
        "tool_schema_snapshot_ref": artifact_ref,
        "tool_schema_snapshot_sha256": snapshot_sha,
        "tool_order": ["read_file", "create_file", "run_tests"],
        "tool_parser_version": "repo_harness_tool_call_parser_v0",
        "tool_result_format_version": "repo_harness_tool_result_v0",
    }
    (run_dir / "artifacts.json").write_text(
        json.dumps({"artifacts": [artifact_ref]}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run_config = {
        "task_id": "task_001",
        "task_version": "task_001_v0",
        "base_commit": "fixture",
        "source_archive_sha256": None,
        "environment_fingerprint": {
            "environment_spec_hash": "c" * 64,
            "workspace_execution": {
                "environment_spec_hash": "c" * 64,
                "setup_artifact_hash": "none",
                "workspace_backend": {
                    "backend": "local_process",
                    "execution_mode": {"resolved_execution_mode": "local_process"},
                },
                "source_checkout": {"base_commit": "fixture"},
            },
        },
        "provider": "replay",
        "model_id": "replay-script-v0",
        "temperature": 0.0,
        "max_output_tokens": 1024,
        "scaffold_id": "simple_react",
        "scaffold_version": "repo_harness_simple_react_v0",
        "allowed_tools_policy": "repo_harness_tools_v0",
        "phase_policy": "repo_harness_simple_react_single_phase_v0",
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
    config_sha = _sha256_file(run_dir / "run_config_facts.json")
    (run_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "metadata_source": "v2",
                "run_config_facts_ref": {
                    "relative_path": "run_config_facts.json",
                    "sha256": config_sha,
                },
                "tool_protocol": tool_protocol,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _update_run_config(
    run_dir: Path,
    updates: dict,
    *,
    merge_tool_protocol: bool = False,
) -> None:
    config_path = run_dir / "run_config_facts.json"
    metadata_path = run_dir / "run_metadata.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if merge_tool_protocol and "tool_protocol" in updates:
        merged = {**config.get("tool_protocol", {}), **updates["tool_protocol"]}
        updates = {**updates, "tool_protocol": merged}
    config.update(updates)
    config_path.write_text(json.dumps(config, sort_keys=True) + "\n", encoding="utf-8")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["run_config_facts_ref"]["sha256"] = _sha256_file(config_path)
        if "tool_protocol" in updates:
            metadata["tool_protocol"] = updates["tool_protocol"]
        metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
