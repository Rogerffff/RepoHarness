from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.rl import build_baseline_profile_from_run_dirs, build_hot_path_report


def _write_run(run_dir: Path, *, artifact_size: int, tool_duration_ms: int, artifact_duration_ms: int) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_type": "tool_execution_completed", "duration_ms": tool_duration_ms}),
                json.dumps({"event_type": "artifact_write_completed", "duration_ms": artifact_duration_ms}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "artifacts.json").write_text(
        json.dumps({"artifacts": [{"kind": "stdout", "size_bytes": artifact_size}]}),
        encoding="utf-8",
    )


def test_stage12_5_hot_path_report_measures_recorder_and_tool_costs(tmp_path: Path) -> None:
    first = tmp_path / "run-a"
    second = tmp_path / "run-b"
    _write_run(first, artifact_size=100, tool_duration_ms=200, artifact_duration_ms=20)
    _write_run(second, artifact_size=300, tool_duration_ms=400, artifact_duration_ms=60)

    report = build_hot_path_report([first, second])

    assert report.episode_count == 2
    assert report.artifact_count_per_episode == 1.0
    assert report.artifact_bytes_per_episode == 200.0
    assert report.tool_seconds_p50 == pytest.approx(0.3)
    assert report.tool_call_count_per_episode == 1.0
    assert report.manifest_rewrite_count_per_episode == 1.0


def test_stage12_5_baseline_profile_keeps_unsupported_diagnostics_structured(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-a"
    _write_run(run_dir, artifact_size=128, tool_duration_ms=100, artifact_duration_ms=10)

    profile = build_baseline_profile_from_run_dirs(
        [run_dir],
        unsupported_diagnostics=["tokenizer_profile_unavailable_on_fake_gateway"],
    )

    assert profile.hot_path_report is not None
    assert profile.hot_path_report.artifact_bytes_per_episode == 128.0
    assert profile.unsupported_diagnostics == ["tokenizer_profile_unavailable_on_fake_gateway"]
