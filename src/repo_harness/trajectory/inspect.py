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
    baseline_path = run_path / "baseline.json"
    verifier_path = run_path / "verifier.json"
    reward_path = run_path / "reward.json"
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
    task_id = _task_id(events, baseline_path)
    if task_id is not None:
        lines.append(f"Task id: {task_id}")
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

    metrics = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        interaction = metrics.get("interaction_efficiency", {})
        lines.append(f"Run outcome: {metrics.get('run_outcome', 'unknown')}")
        lines.append(f"Agent stop reason: {interaction.get('agent_stop_reason', 'unknown')}")
        lines.append(f"Final verifier status: {metrics.get('final_verifier_status', 'unknown')}")
    else:
        lines.append("Metrics: missing")

    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        lines.append(f"Baseline status: {baseline.get('status', 'unknown')}")
    else:
        lines.append("Baseline: missing")

    if verifier_path.exists():
        verifier = json.loads(verifier_path.read_text(encoding="utf-8"))
        lines.append(f"Final verifier accepted: {verifier.get('accepted', 'unknown')}")
        if verifier.get("error_type"):
            lines.append(f"Final verifier error: {verifier['error_type']}")
    else:
        lines.append("Final verifier: missing or skipped")

    if reward_path.exists():
        reward = json.loads(reward_path.read_text(encoding="utf-8"))
        lines.append(f"Reward: {reward.get('final_reward', 'unknown')}")
    else:
        lines.append("Reward: missing or skipped")

    if summary_path.exists():
        lines.append("Summary: present")
    else:
        lines.append("Summary: missing")

    if events:
        lines.append(f"Last event: {events[-1].get('event_type', 'unknown')}")

    key_artifacts = [
        name
        for name in [
            "summary.md",
            "baseline.json",
            "resolved_verifier_plan.json",
            "final.patch",
            "final.diff",
            "verifier.json",
            "reward.json",
            "metrics.json",
        ]
        if (run_path / name).exists()
    ]
    if key_artifacts:
        lines.append("Key artifacts:")
        lines.extend(f"- {name}" for name in key_artifacts)

    return "\n".join(lines)


def _task_id(events: list[dict], baseline_path: Path) -> str | None:
    for event in events:
        raw_task_id = event.get("task_id")
        if isinstance(raw_task_id, str) and raw_task_id:
            return raw_task_id
    if baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        raw_task_id = baseline.get("task_id")
        if isinstance(raw_task_id, str) and raw_task_id:
            return raw_task_id
    return None
