from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from repo_harness.rl.runtime import _tool_seconds_from_run_dir


def _write_events(run_dir: Path, events: list[dict[str, object]]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )


def test_stage12_5_tool_timing_is_aggregated_from_structured_events(tmp_path: Path) -> None:
    _write_events(
        tmp_path,
        [
            {"event_type": "tool_execution_completed", "duration_ms": 250},
            {"event_type": "workspace_command_finished", "duration_ms": 1250},
            {"event_type": "model_call_completed", "duration_ms": 9999},
            {"event_type": "tool_call_failed", "duration_ms": -100},
        ],
    )

    assert _tool_seconds_from_run_dir(tmp_path, SimpleNamespace(tool_call_count=2)) == 1.5


def test_stage12_5_tool_timing_falls_back_to_zero_without_events(tmp_path: Path) -> None:
    assert _tool_seconds_from_run_dir(tmp_path, SimpleNamespace(tool_call_count=2)) == 0.0
