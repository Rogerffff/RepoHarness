from __future__ import annotations

import hashlib
import json
from pathlib import Path

from repo_harness.trajectory import inspect_run


def test_inspect_run_reports_legacy_missing_metadata(tmp_path: Path):
    run_dir = tmp_path / "legacy"
    run_dir.mkdir()
    _write_json(run_dir / "run_status.json", {"status": "FINALIZED"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": []})
    _write_json(run_dir / "baseline.json", {"task_id": "task_001", "status": "valid"})
    _write_json(run_dir / "metrics.json", {"run_outcome": "success"})
    (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")

    output = inspect_run(run_dir)

    assert "Run config facts: missing" in output
    assert "Run metadata: legacy_missing" in output
    assert "Metadata source: legacy_inferred" in output
    assert "Export audit: not_generated" in output


def test_inspect_run_reports_v2_missing_final_metadata(tmp_path: Path):
    run_dir = tmp_path / "partial_v2"
    run_dir.mkdir()
    _write_json(run_dir / "run_status.json", {"status": "RUNNING"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": []})
    _write_json(
        run_dir / "run_config_facts.json",
        {
            "provider": "replay",
            "model_id": "replay-script-v0",
            "scaffold_id": "simple_react",
            "scaffold_version": "repo_harness_simple_react_v0",
        },
    )

    output = inspect_run(run_dir)

    assert "Run config facts: ok" in output
    assert "Run metadata: missing" in output
    assert "Metadata source: missing" in output
    assert "Provider: replay" in output
    assert "Scaffold: simple_react (repo_harness_simple_react_v0)" in output


def test_inspect_run_reports_v2_metadata_and_tool_snapshot(tmp_path: Path):
    run_dir = tmp_path / "v2"
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True)
    tool_snapshot_path = artifact_dir / "tool_schema_snapshot.json"
    snapshot_sha = "b" * 64
    _write_json(tool_snapshot_path, {"snapshot_id": "snapshot_001", "snapshot_sha256": snapshot_sha})
    tool_snapshot_sha = _sha256_file(tool_snapshot_path)
    artifact_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "artifact_tool_schema_snapshot",
        "relative_path": "artifacts/tool_schema_snapshot.json",
        "kind": "tool_schema_snapshot",
        "sha256": tool_snapshot_sha,
        "size_bytes": tool_snapshot_path.stat().st_size,
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    tool_protocol = {
        "tool_schema_snapshot_ref": artifact_ref,
        "tool_schema_snapshot_sha256": snapshot_sha,
    }
    _write_json(run_dir / "artifacts.json", {"artifacts": [artifact_ref]})
    _write_json(run_dir / "run_status.json", {"status": "FINALIZED"})
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "run_finished", "task_id": "task_001"}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "baseline.json", {"task_id": "task_001", "status": "valid"})
    _write_json(run_dir / "metrics.json", {"run_outcome": "failed"})
    _write_json(
        run_dir / "run_config_facts.json",
        {
            "provider": "replay",
            "model_id": "replay-script-v0",
            "scaffold_id": "simple_react",
            "scaffold_version": "repo_harness_simple_react_v0",
            "tool_protocol": tool_protocol,
        },
    )
    config_sha = _sha256_file(run_dir / "run_config_facts.json")
    _write_json(
        run_dir / "run_metadata.json",
        {
            "metadata_source": "v2",
            "run_config_facts_ref": {
                "relative_path": "run_config_facts.json",
                "sha256": config_sha,
            },
            "tool_protocol": tool_protocol,
            "failure_diagnostics": [
                {
                    "failure_category": "environment_failure",
                    "failure_type": "final_verifier_failed",
                    "recoverable": False,
                }
            ],
        },
    )

    output = inspect_run(run_dir)

    assert "Run config facts: ok" in output
    assert "Run metadata: ok" in output
    assert "Metadata source: v2" in output
    assert "Tool schema snapshot: ok" in output
    assert "Provider: replay" in output
    assert "Model id: replay-script-v0" in output
    assert "Failure diagnostics:" in output
    assert "environment_failure:final_verifier_failed:recoverable=False" in output


def test_inspect_run_marks_corrupt_config_as_invalid_not_legacy(tmp_path: Path):
    run_dir = tmp_path / "corrupt_config"
    run_dir.mkdir()
    _write_json(run_dir / "run_status.json", {"status": "RUNNING"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": []})
    (run_dir / "run_config_facts.json").write_text("{", encoding="utf-8")

    output = inspect_run(run_dir)

    assert "Run config facts: invalid" in output
    assert "Run metadata: missing" in output
    assert "Metadata source: missing" in output
    assert "legacy_inferred" not in output
    assert "run_config_facts.json is corrupt" in output


def test_inspect_run_marks_corrupt_metadata_as_invalid_not_legacy(tmp_path: Path):
    run_dir = tmp_path / "corrupt_metadata"
    run_dir.mkdir()
    _write_json(run_dir / "run_status.json", {"status": "RUNNING"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": []})
    (run_dir / "run_metadata.json").write_text("{", encoding="utf-8")

    output = inspect_run(run_dir)

    assert "Run config facts: missing" in output
    assert "Run metadata: invalid" in output
    assert "Metadata source: invalid" in output
    assert "legacy_missing" not in output
    assert "run_metadata.json is corrupt" in output


def test_inspect_run_reports_run_config_ref_hash_mismatch(tmp_path: Path):
    run_dir = tmp_path / "metadata_ref_mismatch"
    run_dir.mkdir()
    _write_json(run_dir / "run_status.json", {"status": "FINALIZED"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": []})
    _write_json(run_dir / "run_config_facts.json", {"provider": "replay"})
    _write_json(
        run_dir / "run_metadata.json",
        {
            "metadata_source": "v2",
            "run_config_facts_ref": {
                "relative_path": "run_config_facts.json",
                "sha256": "c" * 64,
            },
        },
    )

    output = inspect_run(run_dir)

    assert "Run config facts: ok" in output
    assert "Run metadata: invalid" in output
    assert "run_config_facts_ref sha256 不匹配" in output


def test_inspect_run_reports_tool_snapshot_protocol_hash_mismatch(tmp_path: Path):
    run_dir = tmp_path / "tool_snapshot_hash_mismatch"
    artifact_ref = _write_tool_snapshot(run_dir, snapshot_sha="b" * 64)
    tool_protocol = {
        "tool_schema_snapshot_ref": artifact_ref,
        "tool_schema_snapshot_sha256": "c" * 64,
    }
    _write_json(run_dir / "run_status.json", {"status": "FINALIZED"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": [artifact_ref]})
    _write_json(run_dir / "run_config_facts.json", {"tool_protocol": tool_protocol})
    config_sha = _sha256_file(run_dir / "run_config_facts.json")
    _write_json(
        run_dir / "run_metadata.json",
        {
            "metadata_source": "v2",
            "run_config_facts_ref": {
                "relative_path": "run_config_facts.json",
                "sha256": config_sha,
            },
            "tool_protocol": tool_protocol,
        },
    )

    output = inspect_run(run_dir)

    assert "Run metadata: ok" in output
    assert "Tool schema snapshot: invalid" in output


def test_inspect_run_reports_missing_tool_snapshot_artifact(tmp_path: Path):
    run_dir = tmp_path / "tool_snapshot_missing_artifact"
    run_dir.mkdir()
    artifact_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "artifact_tool_schema_snapshot",
        "relative_path": "artifacts/tool_schema_snapshot.json",
        "kind": "tool_schema_snapshot",
        "sha256": "d" * 64,
        "size_bytes": 100,
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    tool_protocol = {
        "tool_schema_snapshot_ref": artifact_ref,
        "tool_schema_snapshot_sha256": "b" * 64,
    }
    _write_json(run_dir / "run_status.json", {"status": "FINALIZED"})
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"artifacts": [artifact_ref]})
    _write_json(run_dir / "run_config_facts.json", {"tool_protocol": tool_protocol})

    output = inspect_run(run_dir)

    assert "Run config facts: ok" in output
    assert "Tool schema snapshot: invalid" in output


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tool_snapshot(run_dir: Path, *, snapshot_sha: str) -> dict:
    tool_snapshot_path = run_dir / "artifacts" / "tool_schema_snapshot.json"
    _write_json(
        tool_snapshot_path,
        {"snapshot_id": f"tool_schema_snapshot_{snapshot_sha[:12]}", "snapshot_sha256": snapshot_sha},
    )
    artifact_sha = _sha256_file(tool_snapshot_path)
    return {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "artifact_tool_schema_snapshot",
        "relative_path": "artifacts/tool_schema_snapshot.json",
        "kind": "tool_schema_snapshot",
        "sha256": artifact_sha,
        "size_bytes": tool_snapshot_path.stat().st_size,
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
