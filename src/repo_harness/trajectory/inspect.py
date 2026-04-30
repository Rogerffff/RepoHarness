"""run directory 只读检查工具。"""

from __future__ import annotations

import json
from pathlib import Path

from repo_harness.trajectory.recorder import read_jsonl, verify_artifact_manifest


def inspect_run(run_dir: str | Path) -> str:
    """读取 run directory 并返回面向人的摘要。"""

    run_path = Path(run_dir)
    status_path = run_path / "run_status.json"
    events_path = run_path / "events.jsonl"
    manifest_path = run_path / "artifacts.json"
    metrics_path = run_path / "metrics.json"
    summary_path = run_path / "summary.md"

    status = "MISSING"
    diagnostics: list[str] = []
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8")).get("status", "UNKNOWN")
        except json.JSONDecodeError:
            status = "CORRUPT_PARTIAL"
            diagnostics.append("run_status.json is corrupt")

    events = []
    try:
        events = read_jsonl(events_path)
    except json.JSONDecodeError as exc:
        status = "CORRUPT_PARTIAL"
        diagnostics.append(f"events.jsonl is corrupt: line {exc.lineno}")
    manifest_missing = not manifest_path.exists()
    artifact_errors: list[str] = []
    if not manifest_missing:
        try:
            artifact_errors = verify_artifact_manifest(run_path)
        except (json.JSONDecodeError, OSError) as exc:
            status = "CORRUPT_PARTIAL"
            artifact_errors = [f"artifacts.json is corrupt: {exc}"]
    artifact_count = 0
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_count = len(manifest.get("artifacts", []))
        except json.JSONDecodeError:
            status = "CORRUPT_PARTIAL"
            diagnostics.append("artifacts.json is corrupt")

    lines = [
        f"Run directory: {run_path}",
        f"Status: {status}",
        f"Events: {len(events)}",
        f"Artifacts: {artifact_count}",
    ]
    if manifest_missing:
        lines.append("Artifacts manifest: missing")
    elif artifact_errors:
        lines.append("Artifacts manifest: invalid")
        lines.extend(f"- {error}" for error in artifact_errors)
    else:
        lines.append("Artifacts manifest: ok")

    if diagnostics:
        lines.append("Diagnostics:")
        lines.extend(f"- {diagnostic}" for diagnostic in diagnostics)

    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        lines.append(f"Run outcome: {metrics.get('run_outcome', 'unknown')}")
    else:
        lines.append("Metrics: missing")

    if summary_path.exists():
        lines.append("Summary: present")
    else:
        lines.append("Summary: missing")

    if events:
        lines.append(f"Last event: {events[-1].get('event_type', 'unknown')}")

    return "\n".join(lines)
