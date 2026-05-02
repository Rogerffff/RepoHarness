from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.v3_experiment_resume import build_v3_experiment_resume, inspect_experiment_resume


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "tests/fixtures/run_configs/v3/experiment_resume_smoke.yaml"


def test_v3_experiment_resume_builds_and_inspects(tmp_path: Path):
    output_dir = tmp_path / "v3_resume"

    result_dir = build_v3_experiment_resume(
        config_path=CONFIG,
        output_dir=output_dir,
        inject_interrupt_after="baseline",
    )
    output = inspect_experiment_resume(
        result_dir,
        manifest=result_dir / "experiment_resume_manifest.json",
        assert_resumable=True,
    )

    manifest = _read_json(result_dir / "experiment_resume_manifest.json")
    diagnostics = _read_json(result_dir / "interrupted_run_diagnostics.json")

    assert "Inspect experiment resume: passed" in output
    assert manifest["state_distribution"]["completed"] == 3
    assert manifest["state_distribution"]["interrupted"] == 1
    assert any(entry["resume_action"] == "skip_completed" for entry in manifest["runs"])
    assert any(entry["resume_action"] == "continue_pending" for entry in manifest["runs"])
    assert any(entry["parent_run_id"] for entry in manifest["runs"])
    assert diagnostics["original_evidence_preserved"]["run_status"] == "INTERRUPTED"
    assert diagnostics["original_evidence_preserved"]["run_metadata_json"] is False
    assert diagnostics["continuation_created_new_run_id"] is True
    assert (result_dir / "command_log.jsonl").exists()


def test_v3_experiment_resume_cli(tmp_path: Path, capsys):
    output_dir = tmp_path / "v3_resume_cli"

    assert main(
        [
            "build-v3-experiment-resume",
            "--config",
            str(CONFIG),
            "--output-dir",
            str(output_dir),
            "--inject-interrupt-after",
            "baseline",
        ]
    ) == 0
    assert "V3 experiment resume 产物目录" in capsys.readouterr().out
    assert main(
        [
            "inspect-experiment-resume",
            str(output_dir),
            "--manifest",
            str(output_dir / "experiment_resume_manifest.json"),
            "--assert-resumable",
        ]
    ) == 0
    assert "Inspect experiment resume: passed" in capsys.readouterr().out


def test_inspect_experiment_resume_rejects_premature_run_metadata_ref(tmp_path: Path):
    output_dir = tmp_path / "v3_resume_bad_checkpoint"
    result_dir = build_v3_experiment_resume(
        config_path=CONFIG,
        output_dir=output_dir,
        inject_interrupt_after="baseline",
    )
    checkpoint_manifest = _read_json(result_dir / "run_checkpoint_manifest.json")
    interrupted_ref = next(
        ref for ref in checkpoint_manifest["checkpoint_refs"] if ref["artifact_id"].endswith("_interrupted")
    )
    interrupted_checkpoint = result_dir / interrupted_ref["relative_path"]
    payload = _read_json(interrupted_checkpoint)
    completed_checkpoint = next(
        checkpoint
        for checkpoint in checkpoint_manifest["checkpoints"]
        if checkpoint["status"] == "completed" and checkpoint.get("run_metadata_ref")
    )
    payload["run_metadata_ref"] = completed_checkpoint["run_metadata_ref"]
    interrupted_checkpoint.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="run_metadata_ref"):
        inspect_experiment_resume(
            result_dir,
            manifest=result_dir / "experiment_resume_manifest.json",
            assert_resumable=True,
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
