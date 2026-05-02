from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_agent_loop import inspect_v3_agent_loop_integration, scan_v3_run_surfaces
from repo_harness.workspace.source_hash import compute_file_sha256


def test_scan_v3_run_surfaces_detects_model_visible_forbidden_term(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_json(run_dir / "artifacts.json", {"schema_version": "test", "artifacts": []})
    _write_jsonl(
        run_dir / "transcript.jsonl",
        [
            {
                "role": "assistant",
                "model_visible": True,
                "message_id": "assistant_1",
                "content_preview": "gold_patch should never be model visible",
            }
        ],
    )

    result = scan_v3_run_surfaces(run_dir)

    assert result["clean"] is False
    assert result["finding_count"] >= 1


def test_inspect_v3_agent_loop_integration_rejects_unclean_scan(tmp_path: Path):
    root = tmp_path / "stage7"
    real = _minimal_run(root, "real", task_id="realrepo_local_buggy_calculator")
    swe = _minimal_run(root, "swe", task_id="pytest-dev__pytest-7220")
    final_root = swe / "v3_swebench_like_final_verifier" / "pytest-dev__pytest-7220"
    final_root.mkdir(parents=True)
    _write_json(final_root / "final_verifier_result.json", {"official_harness_report_used": False})
    clean_scan = root / "clean_scan.json"
    dirty_scan = root / "dirty_scan.json"
    _write_json(clean_scan, {"clean": True})
    _write_json(dirty_scan, {"clean": False, "findings": [{"matched_term": "gold_patch"}]})
    report = {
        "schema_version": "repo_harness_v3_agent_loop_integration_report_v0",
        "runs": {
            "real_repository": {
                "run_dir": real.as_posix(),
                "run_outcome": "success",
                "final_verifier_status": "accepted",
                "task_id": "realrepo_local_buggy_calculator",
            },
            "swebench_like": {
                "run_dir": swe.as_posix(),
                "agent_loop_entered": True,
                "task_id": "pytest-dev__pytest-7220",
            },
        },
        "contamination_scan_refs": [
            _ref(clean_scan, root, "clean_scan"),
            _ref(dirty_scan, root, "dirty_scan"),
        ],
        "tool_pairing": {
            "real_repository": {"missing_terminal_tool_call_ids": []},
            "swebench_like": {"missing_terminal_tool_call_ids": []},
        },
    }
    report_path = root / "report.json"
    _write_json(report_path, report)

    with pytest.raises(ConfigError, match="污染扫描未通过"):
        inspect_v3_agent_loop_integration(root, report=report_path, assert_complete=True)


def _minimal_run(root: Path, name: str, *, task_id: str) -> Path:
    run_dir = root / name
    run_dir.mkdir(parents=True)
    for filename in ("transcript.jsonl", "events.jsonl"):
        (run_dir / filename).write_text("", encoding="utf-8")
    _write_json(run_dir / "artifacts.json", {"schema_version": "test", "artifacts": []})
    _write_json(run_dir / "run_config_facts.json", {})
    _write_json(run_dir / "run_metadata.json", {})
    _write_json(run_dir / "task.yaml", {"id": task_id})
    (run_dir / "final.patch").write_text("diff --git a/a b/a\n", encoding="utf-8")
    _write_json(
        run_dir / "docker_backend_status.json",
        {
            "mode": "docker_backend",
            "status": "passed",
            "container_execution_facts_refs": ["container_execution_facts/example.json"],
        },
    )
    return run_dir


def _ref(path: Path, base: Path, artifact_id: str) -> dict:
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=path.relative_to(base).as_posix(),
        kind="json",
        sha256=compute_file_sha256(path),
        size_bytes=path.stat().st_size,
    ).model_dump(mode="json")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
