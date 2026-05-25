from __future__ import annotations

import json
from pathlib import Path

from repo_harness.evaluation.runner import run_task


def test_stage16f5_run_task_writes_legacy_entrypoint_metadata(tmp_path: Path) -> None:
    run_dir = run_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f5_legacy_run_task",
    )

    report = json.loads((run_dir / "legacy_entrypoint_report.json").read_text(encoding="utf-8"))

    assert report["entrypoint"] == "run_task"
    assert report["entrypoint_classification"] == "legacy_compatibility"
    assert report["canonical_entrypoint"] == "run_episode_task"
    assert report["formal_online_rl_eligible"] is False
    assert report["policy_loss_candidate"] is False
    assert report["formal_training_data_candidate"] is False
    assert report["new_training_data_default_candidate"] is False
    assert report["new_training_data_default_entrypoint"] is False
    assert report["training_data_eligibility_asserted"] is False
