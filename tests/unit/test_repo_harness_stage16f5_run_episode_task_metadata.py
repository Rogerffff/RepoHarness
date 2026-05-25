from __future__ import annotations

import json
from pathlib import Path

from repo_harness.evaluation.entrypoint_policy import inspect_stage16f5_entrypoint_policy
from repo_harness.evaluation.episode_runner import run_episode_task


def test_stage16f5_run_episode_task_writes_canonical_entrypoint_metadata(tmp_path: Path) -> None:
    run_dir = run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f5_canonical_run_episode_task",
        gateway_route="mock",
        assert_projection_complete=True,
    )

    report = json.loads((run_dir / "entrypoint_report.json").read_text(encoding="utf-8"))

    assert report["entrypoint"] == "run_episode_task"
    assert report["entrypoint_classification"] == "canonical_run_episode_task"
    assert report["episode_execution_spec_sha256"]
    assert report["compat_projection_complete"] is True
    assert report["provider_route"] == "mock"
    assert report["formal_online_rl_eligible"] is False
    assert report["policy_loss_candidate"] is False
    assert report["new_training_data_default_entrypoint"] is True
    assert report["training_data_eligibility_asserted"] is False


def test_stage16f5_inspector_passes_real_legacy_and_canonical_runs(tmp_path: Path) -> None:
    from repo_harness.evaluation.runner import run_task

    run_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f5_legacy",
    )
    run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f5_canonical",
        gateway_route="mock",
        assert_projection_complete=True,
    )

    report = json.loads(inspect_stage16f5_entrypoint_policy(tmp_path / "runs", assert_complete=False))

    assert report["passed"] is True
    assert report["legacy_run_task_report_count"] == 1
    assert report["canonical_run_episode_task_report_count"] == 1
