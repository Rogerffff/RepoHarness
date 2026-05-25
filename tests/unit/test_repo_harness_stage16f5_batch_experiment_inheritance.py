from __future__ import annotations

import json
from pathlib import Path

import yaml

from repo_harness.evaluation.experiment import run_experiment
from repo_harness.evaluation.runner import run_batch


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_stage16f5_run_batch_children_inherit_legacy_entrypoint_metadata(tmp_path: Path) -> None:
    config_path = tmp_path / "batch.yaml"
    _write_yaml(
        config_path,
        {
            "run_id_prefix": "stage16f5_batch",
            "tasks": ["tests/fixtures/tasks/task_001.yaml"],
            "model": {
                "provider": "replay",
                "model_id": "replay-script-v0",
                "replay_script_path": "tests/fixtures/replays/task_001_success.yaml",
            },
            "runtime": {
                "scaffold_id": "simple_react",
                "execution_mode": "local_process",
                "permission_mode": "auto",
                "max_turns": 8,
                "max_tool_calls": 20,
                "max_test_runs": 4,
            },
            "workspace": {
                "output_dir": str(tmp_path / "batch_runs"),
                "keep_workspace": True,
                "default_command_timeout_sec": 60,
            },
            "evaluation": {"concurrency": 1, "fail_on_invalid_task": False},
        },
    )

    manifest_path = run_batch(config_path=config_path, output_dir=tmp_path / "batch_runs")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_dir = Path(manifest["runs"][0]["run_dir"])
    report = json.loads((run_dir / "legacy_entrypoint_report.json").read_text(encoding="utf-8"))

    assert report["entrypoint_classification"] == "legacy_compatibility"
    assert report["formal_training_data_candidate"] is False


def test_stage16f5_run_experiment_children_inherit_legacy_entrypoint_metadata(tmp_path: Path) -> None:
    config_path = tmp_path / "experiment.yaml"
    _write_yaml(
        config_path,
        {
            "experiment_id": "stage16f5_exp",
            "tasks": ["tests/fixtures/tasks/task_001.yaml"],
            "rollout_count": 1,
            "model_provider": "replay",
            "model_alias": "replay",
            "model_id": "replay-script-v0",
            "replay_script_path": "tests/fixtures/replays/task_001_success.yaml",
            "scaffold_id": "simple_react",
            "permission_mode": "auto",
            "output_dir": str(tmp_path / "experiment_runs"),
            "run_id_template": "{experiment_id}_{task_id}_{model_alias}_{scaffold_id}_r{rollout_index:03d}",
            "max_turns": 8,
            "max_tool_calls": 20,
            "max_test_runs": 4,
            "task_timeout_sec": 120,
            "command_timeout_sec": 60,
            "generate_preference_export": False,
        },
    )

    manifest_path = run_experiment(config_path=config_path, output_dir=tmp_path / "experiment_runs")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_dir = Path(manifest["runs"][0]["run_dir"])
    report = json.loads((run_dir / "legacy_entrypoint_report.json").read_text(encoding="utf-8"))

    assert report["entrypoint_classification"] == "legacy_compatibility"
    assert report["new_training_data_default_entrypoint"] is False
