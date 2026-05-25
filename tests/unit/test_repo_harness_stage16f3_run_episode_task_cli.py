from __future__ import annotations

import json
from pathlib import Path

from repo_harness.cli.main import main


def test_stage16f3_run_episode_task_cli_writes_complete_projection(tmp_path: Path) -> None:
    output_dir = tmp_path / "runs"

    exit_code = main(
        [
            "run-episode-task",
            "tests/fixtures/tasks/task_001.yaml",
            "--config",
            "tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "stage16f3_cli_mock",
            "--assert-projection-complete",
        ]
    )

    assert exit_code == 0
    projection_dir = output_dir / "stage16f3_cli_mock" / "compat_projection"
    validation = json.loads((projection_dir / "projection_validation_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((projection_dir / "compat_projection_manifest.json").read_text(encoding="utf-8"))
    route_report = json.loads((projection_dir / "provider_route_qualification.json").read_text(encoding="utf-8"))

    assert validation["projection_complete"] is True
    assert manifest["provider_route"] == "mock"
    assert route_report["formal_online_rl_eligible"] is False
    assert route_report["policy_loss_candidate"] is False
    assert "raw_prompt" not in manifest


def test_stage16f3_mock_route_runs_real_final_verifier_accepted_projection(tmp_path: Path) -> None:
    output_dir = tmp_path / "runs"

    exit_code = main(
        [
            "run-episode-task",
            "tests/fixtures/tasks/task_stage16f3_passing.yaml",
            "--config",
            "tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "stage16f3_cli_mock_accept",
            "--gateway-route",
            "mock",
            "--assert-projection-complete",
        ]
    )

    assert exit_code == 0
    projection_dir = output_dir / "stage16f3_cli_mock_accept" / "compat_projection"
    verifier = json.loads((projection_dir / "verifier_summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((projection_dir / "metrics.json").read_text(encoding="utf-8"))
    route_report = json.loads((projection_dir / "provider_route_qualification.json").read_text(encoding="utf-8"))

    assert verifier["verifier_summary"]["accepted"] is True
    assert metrics["run_outcome"] == "succeeded"
    assert route_report["provider_route"] == "mock"
    assert route_report["policy_loss_candidate"] is False
