from __future__ import annotations

import json
from pathlib import Path

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.evaluation.experiment import inspect_experiment, run_experiment


ROOT = Path(__file__).resolve().parents[2]


def test_experiment_runner_writes_manifest_and_aggregate(tmp_path: Path):
    exp_dir = tmp_path / "experiment"

    manifest_path = run_experiment(
        config_path=ROOT / "tests/fixtures/run_configs/v2/experiment_smoke.yaml",
        output_dir=exp_dir,
    )

    manifest = _read_json(manifest_path)
    aggregate = _read_json(exp_dir / "aggregate_metrics.json")

    assert manifest_path == exp_dir / "experiment_manifest.json"
    assert (exp_dir / "experiment_summary.md").exists()
    assert (exp_dir / "compare_scope.json").exists()
    assert aggregate["total_runs"] == 4
    assert aggregate["recorded_runs"] == 2
    assert aggregate["error_runs"] == 2
    run_ids = [record["run_id"] for record in manifest["runs"]]
    assert "v2_exp_smoke_task_001_replay_simple_react_r000" in run_ids
    assert "v2_exp_smoke_task_001_replay_simple_react_r001" in run_ids
    success_records = [record for record in manifest["runs"] if record["task_id"] == "task_001"]
    assert all(record["model_alias"] == "replay" for record in success_records)
    assert all(record["scaffold_id"] == "simple_react" for record in success_records)
    assert all(record["status"] == "success" for record in success_records)
    error_records = [record for record in manifest["runs"] if record["status"] == "error"]
    assert error_records and all(record["failure_reason"] for record in error_records)
    assert manifest["preference_export_path"]


def test_inspect_experiment_assert_minimums_passes_and_fails(tmp_path: Path):
    exp_dir = tmp_path / "experiment"
    run_experiment(
        config_path=ROOT / "tests/fixtures/run_configs/v2/experiment_smoke.yaml",
        output_dir=exp_dir,
    )
    ok = inspect_experiment(
        exp_dir,
        minimums_path=ROOT / "tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml",
    )
    strict_thresholds = tmp_path / "strict_thresholds.yaml"
    strict_thresholds.write_text(
        "min_total_runs: 10\nmin_recorded_runs: 10\n",
        encoding="utf-8",
    )

    assert "Inspect experiment: passed" in ok
    try:
        inspect_experiment(exp_dir, minimums_path=strict_thresholds)
    except ConfigError as exc:
        assert "min_total_runs" in str(exc)
    else:
        raise AssertionError("strict minimums should fail")


def test_inspect_experiment_requires_error_failure_reason(tmp_path: Path):
    exp_dir = tmp_path / "experiment"
    run_experiment(
        config_path=ROOT / "tests/fixtures/run_configs/v2/experiment_smoke.yaml",
        output_dir=exp_dir,
    )
    manifest_path = exp_dir / "experiment_manifest.json"
    manifest = _read_json(manifest_path)
    for record in manifest["runs"]:
        if record["status"] == "error":
            record["failure_reason"] = None
            break
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    try:
        inspect_experiment(
            exp_dir,
            minimums_path=ROOT / "tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml",
        )
    except ConfigError as exc:
        assert "failure_reason" in str(exc)
    else:
        raise AssertionError("missing failure_reason should fail minimum inspection")


def test_experiment_cli_commands(tmp_path: Path, capsys):
    exp_dir = tmp_path / "experiment_cli"

    assert main(
        [
            "run-experiment",
            "--config",
            str(ROOT / "tests/fixtures/run_configs/v2/experiment_smoke.yaml"),
            "--output-dir",
            str(exp_dir),
        ]
    ) == 0
    assert "实验运行完成" in capsys.readouterr().out
    assert main(
        [
            "inspect-experiment",
            str(exp_dir),
            "--assert-minimums",
            str(ROOT / "tests/fixtures/run_configs/v2/experiment_smoke_thresholds.yaml"),
        ]
    ) == 0
    assert "Inspect experiment: passed" in capsys.readouterr().out


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
