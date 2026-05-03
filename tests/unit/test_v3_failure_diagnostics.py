from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.v3_failure_diagnostics import (
    build_v3_failure_diagnostics,
    inspect_reward_diagnostics,
)


def test_v3_failure_diagnostics_builds_and_inspects(tmp_path: Path):
    source_run = _write_failed_run(tmp_path / "source_run")
    long_report = _write_long_rollout_report(tmp_path / "long_rollout_diagnostics.json")
    context_report = _write_context_report(tmp_path / "context_compaction_report.json")
    output_dir = tmp_path / "stage10"

    result_dir = build_v3_failure_diagnostics(
        run_dir=source_run,
        output_dir=output_dir,
        context_report=context_report,
        long_rollout_report=long_report,
    )
    output = inspect_reward_diagnostics(
        result_dir,
        core_report=result_dir / "failure_diagnostics_core_report.json",
        distribution_report=result_dir / "failure_distribution_report.json",
        assert_core_complete=True,
    )

    core = _read_json(result_dir / "failure_diagnostics_core_report.json")
    distribution = _read_json(result_dir / "failure_distribution_report.json")

    assert "Inspect reward diagnostics: passed" in output
    assert core["core_fields"]["patch_size"] == 0
    assert core["core_fields"]["no_patch_generated"] is True
    assert core["core_fields"]["deterministic_verifier_failure"] is True
    assert core["core_fields"]["no_progress_detected"] is True
    assert "no_patch_generated" in core["training_filter_recommendation"]["reasons"]
    assert distribution["category_counts"]["verifier"] == 1
    assert distribution["category_counts"]["deterministic_verifier_failure"] == 1
    assert (result_dir / "command_log.jsonl").exists()


def test_v3_failure_diagnostics_cli(tmp_path: Path, capsys):
    source_run = _write_failed_run(tmp_path / "source_run_cli")
    long_report = _write_long_rollout_report(tmp_path / "long_rollout_cli.json")
    output_dir = tmp_path / "stage10_cli"

    assert main(
        [
            "build-v3-reward-diagnostics",
            "--run-dir",
            str(source_run),
            "--long-rollout-report",
            str(long_report),
            "--output-dir",
            str(output_dir),
        ]
    ) == 0
    assert "V3 reward diagnostics 产物目录" in capsys.readouterr().out
    assert main(
        [
            "inspect-reward-diagnostics",
            str(output_dir),
            "--core-report",
            str(output_dir / "failure_diagnostics_core_report.json"),
            "--distribution-report",
            str(output_dir / "failure_distribution_report.json"),
            "--assert-core-complete",
        ]
    ) == 0
    assert "Inspect reward diagnostics: passed" in capsys.readouterr().out


def test_inspect_reward_diagnostics_rejects_artifact_sha_drift(tmp_path: Path):
    source_run = _write_failed_run(tmp_path / "source_run_bad_sha")
    output_dir = build_v3_failure_diagnostics(
        run_dir=source_run,
        output_dir=tmp_path / "stage10_bad_sha",
    )
    core_path = output_dir / "failure_diagnostics_core_report.json"
    core = _read_json(core_path)
    core["core_fields"]["source_refs"]["metrics_file_ref"]["sha256"] = "0" * 64
    core_path.write_text(
        json.dumps(core, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="sha256"):
        inspect_reward_diagnostics(
            output_dir,
            core_report=core_path,
            distribution_report=output_dir / "failure_distribution_report.json",
            assert_core_complete=True,
        )


def _write_failed_run(path: Path) -> Path:
    path.mkdir(parents=True)
    _write_json(
        path / "run_status.json",
        {
            "schema_version": "repo_harness_schema_v0",
            "run_id": "v3_stage_10_unit_failed_run",
            "status": "FINALIZED",
        },
    )
    _write_json(
        path / "metrics.json",
        {
            "schema_version": "repo_harness_metrics_v0",
            "task_success": False,
            "final_verifier_status": "failed",
            "run_outcome": "failed",
            "turn_count": 3,
            "tool_call_count": 2,
            "test_run_count": 0,
            "timeout": False,
            "patch_stats": {
                "added_lines": 0,
                "removed_lines": 0,
                "changed_files": [],
                "modified_files": [],
                "added_files": [],
                "deleted_files": [],
            },
            "permission_denial_count": 0,
            "invalid_tool_call_count": 0,
            "interaction_efficiency": {"agent_stop_reason": "final_answer"},
        },
    )
    _write_json(
        path / "baseline.json",
        {
            "schema_version": "repo_harness_baseline_result_v0",
            "task_id": "task_stage_10",
            "status": "valid",
            "dependency_error": None,
            "parser_confidence": 0.9,
        },
    )
    _write_json(
        path / "verifier.json",
        {
            "schema_version": "repo_harness_verifier_result_v0",
            "verifier_stage": "final",
            "accepted": False,
            "error_type": "assertion_failure",
            "timeout": False,
            "parser_confidence": 0.9,
            "fail_to_pass": {"passed": 0, "total": 1},
            "pass_to_pass": {"passed": 2, "total": 2},
        },
    )
    (path / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema_version": "repo_harness_event_v0",
                        "event_id": "evt_001",
                        "timestamp": "2026-05-02T00:00:00Z",
                        "run_id": "v3_stage_10_unit_failed_run",
                        "task_id": "task_stage_10",
                        "event_type": "tool_requested",
                        "severity": "info",
                        "data": {
                            "tool_name": "read_file",
                            "arguments": {"path": "long_context.txt"},
                        },
                    },
                    sort_keys=True,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "final.patch").write_text("", encoding="utf-8")
    return path


def _write_long_rollout_report(path: Path) -> Path:
    _write_json(
        path,
        {
            "schema_version": "repo_harness_v3_long_rollout_diagnostics_v0",
            "run_id": "v3_stage_10_unit_failed_run",
            "diagnostics": [
                {
                    "diagnostic_type": "no_progress",
                    "severity": "warning",
                    "diagnostic_only": True,
                },
                {
                    "diagnostic_type": "repeated_tool_call",
                    "severity": "warning",
                    "diagnostic_only": True,
                },
            ],
        },
    )
    return path


def _write_context_report(path: Path) -> Path:
    _write_json(
        path,
        {
            "schema_version": "repo_harness_context_compaction_facts_v3_v0",
            "compaction_observed": True,
            "observation_matches_prepared_messages": True,
        },
    )
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
