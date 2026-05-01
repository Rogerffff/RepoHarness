import json
import hashlib
from pathlib import Path

import pytest

from repo_harness.errors import ExportError
from repo_harness.export import inspect_export
from repo_harness.export.exporter import export_preference_jsonl, export_rl_jsonl, export_sft_jsonl
from repo_harness.export.exporter import _sanitize_text


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


def test_rl_export_without_formal_final_verifier_is_invalid_for_training(tmp_path: Path):
    run_dir = _minimal_run(tmp_path / "run_missing_formal", task_id="task_001")

    output = export_rl_jsonl(run_dir)
    record = _read_jsonl(output)[0]

    assert record["invalid_for_training"] is True
    assert record["invalid_reason"] == "missing_formal_final_verifier"
    assert record["payload"]["reward_metadata"]["formal_final_verifier"] is False


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
    record = _read_jsonl(output)[0]
    export_dir = _latest_export_dir(run_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))

    assert record["invalid_for_training"] is True
    assert record["invalid_reason"] == "artifact_manifest_invalid"
    assert audit["status"] == "failed"
    assert audit["samples"][0]["training_eligibility"] == "invalid"


def test_sft_export_uses_structured_tool_call_events_not_preview(tmp_path: Path):
    run_dir = _minimal_run(tmp_path / "run_structured_sft", task_id="task_001")
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
    record = _read_jsonl(output)[0]

    assert output.name == "preference.jsonl"
    assert record["payload"]["chosen"]["source_run_id"] == "run_success"
    assert record["payload"]["rejected"]["source_run_id"] == "run_failed"


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
    assert "Inspect export: clean" in inspect_export(export_dir, assert_clean=True, require_trainable_samples=True)


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
    record = _read_jsonl(output)[0]
    export_dir = _latest_export_dir(run_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))

    assert record["quality"]["training_eligibility"] == "invalid"
    assert record["invalid_reason"] == "contains blocked marker raw_response"
    assert audit["status"] == "failed"
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
    record = _read_jsonl(output)[0]
    export_dir = _latest_export_dir(runs_dir / "exports")
    audit = json.loads((export_dir / "audit_report.json").read_text(encoding="utf-8"))

    assert record["quality"]["training_eligibility"] == "invalid"
    assert record["invalid_reason"] == "run_failed: missing_formal_final_verifier"
    assert audit["samples"][0]["source_run_ids"] == ["run_success", "run_failed"]
    assert audit["samples"][0]["metadata_source"] == "v2"
    assert _read_jsonl(export_dir / "data.preference.jsonl") == []


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


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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
    }
    (run_dir / "artifacts.json").write_text(
        json.dumps({"artifacts": [artifact_ref]}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run_config = {
        "provider": "replay",
        "model_id": "replay-script-v0",
        "scaffold_id": "simple_react",
        "scaffold_version": "repo_harness_simple_react_v0",
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
