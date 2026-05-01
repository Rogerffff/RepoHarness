"""Stage 06 minimal experiment runner and inspection."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.evaluation.runner import run_task
from repo_harness.evaluation.schemas import ExperimentConfig, ExperimentMinimums
from repo_harness.export import export_preference_jsonl, inspect_export


def load_experiment_config(path: str | Path, *, output_dir: str | Path | None = None) -> ExperimentConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"无法读取实验配置：{config_path}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("ExperimentConfig 文件顶层必须是 YAML mapping。")
    if output_dir is not None:
        raw = {**raw, "output_dir": str(output_dir)}
    try:
        return ExperimentConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def run_experiment(
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    config = load_experiment_config(config_path, output_dir=output_dir)
    experiment_dir = Path(config.output_dir)
    experiment_dir.mkdir(parents=True, exist_ok=True)
    config_dir = experiment_dir / ".repo_harness_experiment_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    compare_scope_path = experiment_dir / "compare_scope.json"
    _write_json(compare_scope_path, config.compare_scope.model_dump(mode="json"))

    records: list[dict[str, Any]] = []
    for task_path in config.tasks:
        task_id = _task_id(task_path)
        for rollout_index in range(config.rollout_count):
            run_id = _run_id(config, task_id=task_id, rollout_index=rollout_index)
            run_config_path = config_dir / f"{run_id}.yaml"
            _write_yaml(run_config_path, _run_config_payload(config, task_path=task_path))
            record = {
                "task_path": str(task_path),
                "task_id": task_id,
                "rollout_index": rollout_index,
                "model_alias": config.model_alias,
                "model_provider": config.model_provider,
                "model_id": config.model_id,
                "scaffold_id": config.scaffold_id,
                "run_id": run_id,
                "run_dir": str(experiment_dir / run_id),
                "status": "pending",
                "failure_reason": None,
            }
            try:
                run_dir = run_task(
                    task_path,
                    config_path=run_config_path,
                    output_dir=experiment_dir,
                    run_id=run_id,
                )
                metrics = _read_json(run_dir / "metrics.json")
                verifier = _read_json_if_exists(run_dir / "verifier.json")
                interaction = metrics.get("interaction_efficiency", {})
                patch_stats = metrics.get("patch_stats", {})
                record.update(
                    {
                        "status": str(metrics.get("run_outcome", "unknown")),
                        "run_dir": str(run_dir),
                        "entered_agent_loop": (run_dir / "resolved_verifier_plan.json").exists(),
                        "formal_final_verifier_ran": verifier.get("verifier_stage") == "final",
                        "baseline_status": interaction.get("baseline_status"),
                        "quality_gate_reason": interaction.get("quality_gate_reason"),
                        "agent_stop_reason": interaction.get("agent_stop_reason"),
                        "final_verifier_status": metrics.get("final_verifier_status"),
                        "turn_count": metrics.get("turn_count", 0),
                        "tool_call_count": metrics.get("tool_call_count", 0),
                        "test_run_count": metrics.get("test_run_count", 0),
                        "timeout": metrics.get("timeout", False),
                        "permission_denial_count": metrics.get("permission_denial_count", 0),
                        "invalid_tool_call_count": metrics.get("invalid_tool_call_count", 0),
                        "patch_added_lines": patch_stats.get("added_lines", 0),
                        "patch_removed_lines": patch_stats.get("removed_lines", 0),
                        "fail_to_pass": verifier.get("fail_to_pass", {}),
                        "pass_to_pass": verifier.get("pass_to_pass", {}),
                        "failure_reason": None if metrics.get("run_outcome") == "success" else metrics.get("run_outcome"),
                    }
                )
            except RepoHarnessError as exc:
                record.update({"status": "error", "failure_reason": str(exc)})
            records.append(record)

    aggregate = _aggregate_metrics(records)
    aggregate_path = experiment_dir / "aggregate_metrics.json"
    _write_json(aggregate_path, aggregate)
    preference_export_path = None
    if config.generate_preference_export:
        preference_export_path = str(
            export_preference_jsonl(experiment_dir, compare_scope_path=compare_scope_path)
        )
    manifest = {
        "schema_version": "repo_harness_experiment_manifest_v2_v0",
        "experiment_id": config.experiment_id,
        "config_path": str(config_path),
        "output_dir": str(experiment_dir),
        "model_provider": config.model_provider,
        "model_alias": config.model_alias,
        "model_id": config.model_id,
        "scaffold_id": config.scaffold_id,
        "rollout_count": config.rollout_count,
        "compare_scope": config.compare_scope.model_dump(mode="json"),
        "compare_scope_path": "compare_scope.json",
        "aggregate_metrics_path": "aggregate_metrics.json",
        "preference_export_path": preference_export_path,
        "runs": records,
    }
    manifest_path = experiment_dir / "experiment_manifest.json"
    _write_json(manifest_path, manifest)
    _write_summary(experiment_dir / "experiment_summary.md", manifest=manifest, aggregate=aggregate)
    return manifest_path


def inspect_experiment(
    experiment_dir: str | Path,
    *,
    minimums_path: str | Path | None = None,
) -> str:
    root = Path(experiment_dir)
    failures: list[str] = []
    manifest_path = root / "experiment_manifest.json"
    aggregate_path = root / "aggregate_metrics.json"
    if not manifest_path.exists():
        failures.append("experiment_manifest.json missing")
        manifest = {}
    else:
        manifest = _read_json(manifest_path)
    if not aggregate_path.exists():
        failures.append("aggregate_metrics.json missing")
        aggregate = {}
    else:
        aggregate = _read_json(aggregate_path)
    minimums = _load_minimums(minimums_path)
    if minimums.require_experiment_manifest and not manifest_path.exists():
        failures.append("require_experiment_manifest not satisfied")
    if minimums.require_aggregate_metrics and not aggregate_path.exists():
        failures.append("require_aggregate_metrics not satisfied")
    if int(aggregate.get("total_runs", 0)) < minimums.min_total_runs:
        failures.append("min_total_runs not satisfied")
    if int(aggregate.get("task_count", 0)) < minimums.min_task_count:
        failures.append("min_task_count not satisfied")
    if int(aggregate.get("recorded_runs", 0)) < minimums.min_recorded_runs:
        failures.append("min_recorded_runs not satisfied")
    if int(aggregate.get("agent_loop_runs", 0)) < minimums.min_agent_loop_runs:
        failures.append("min_agent_loop_runs not satisfied")
    if int(aggregate.get("formal_final_verifier_runs", 0)) < minimums.min_formal_final_verifier_runs:
        failures.append("min_formal_final_verifier_runs not satisfied")
    if int(aggregate.get("success_count", 0)) < minimums.min_success_count:
        failures.append("min_success_count not satisfied")
    if int(aggregate.get("structured_skipped_runs", 0)) < minimums.min_structured_skipped_runs:
        failures.append("min_structured_skipped_runs not satisfied")
    if minimums.require_failure_records and "error" not in aggregate.get("status_distribution", {}):
        failures.append("require_failure_records not satisfied")
    if minimums.require_failure_records:
        missing_failure_reason = [
            run.get("run_id", "unknown")
            for run in manifest.get("runs", [])
            if run.get("status") == "error" and not run.get("failure_reason")
        ]
        if missing_failure_reason:
            failures.append(
                "failure records missing failure_reason: " + ", ".join(map(str, missing_failure_reason))
            )
    if minimums.require_no_all_skipped_success:
        total = int(aggregate.get("total_runs", 0))
        skipped = sum(
            int(aggregate.get("status_distribution", {}).get(status, 0))
            for status in ("invalid_task", "flaky_task", "inconclusive")
        )
        if total > 0 and skipped == total:
            failures.append("all runs were skipped or inconclusive")
    if minimums.require_export_audit_clean:
        export_status = _export_audit_status(root)
        if export_status["status"] != "clean":
            failures.append(f"export audit not clean: {export_status['reason']}")

    lines = [
        f"Experiment directory: {root}",
        f"Experiment manifest: {'present' if manifest_path.exists() else 'missing'}",
        f"Aggregate metrics: {'present' if aggregate_path.exists() else 'missing'}",
        f"Total runs: {aggregate.get('total_runs', 0)}",
        f"Task count: {aggregate.get('task_count', 0)}",
        f"Recorded runs: {aggregate.get('recorded_runs', 0)}",
        f"Agent loop runs: {aggregate.get('agent_loop_runs', 0)}",
        f"Formal final verifier runs: {aggregate.get('formal_final_verifier_runs', 0)}",
        f"Success count: {aggregate.get('success_count', 0)}",
        f"Structured skipped runs: {aggregate.get('structured_skipped_runs', 0)}",
        f"Error runs: {aggregate.get('error_runs', 0)}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    lines.append("Inspect experiment: passed")
    return "\n".join(lines)


def _run_config_payload(config: ExperimentConfig, *, task_path: str) -> dict[str, Any]:
    return {
        "run_id_prefix": config.experiment_id,
        "tasks": [task_path],
        "model": {
            "provider": config.model_provider,
            "model_id": config.model_id,
            "replay_script_path": config.replay_script_path,
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens,
            "provider_specific_options": {},
        },
        "runtime": {
            "scaffold_id": config.scaffold_id,
            "execution_mode": config.execution_mode,
            "permission_mode": config.permission_mode,
            **(
                {"test_feedback_policy": config.test_feedback_policy}
                if config.test_feedback_policy is not None
                else {}
            ),
            **(
                {"feedback_tests_passed_policy": config.feedback_tests_passed_policy}
                if config.feedback_tests_passed_policy is not None
                else {}
            ),
            "max_turns": config.max_turns,
            "max_tool_calls": config.max_tool_calls,
            "max_test_runs": config.max_test_runs,
            "task_timeout_sec": config.task_timeout_sec,
            "seed": config.seed,
        },
        "workspace": {
            "output_dir": config.output_dir,
            "keep_workspace": config.keep_workspace,
            "default_command_timeout_sec": config.command_timeout_sec,
        },
        "evaluation": {
            "concurrency": 1,
            "fail_on_invalid_task": config.fail_on_invalid_task,
            "final_verifier_mode": "strict_patch_replay",
        },
    }


def _run_id(config: ExperimentConfig, *, task_id: str, rollout_index: int) -> str:
    raw = config.run_id_template.format(
        experiment_id=config.experiment_id,
        task_id=task_id,
        model_alias=config.model_alias,
        scaffold_id=config.scaffold_id,
        rollout_index=rollout_index,
    )
    return _slug(raw)


def _task_id(task_path: str | Path) -> str:
    try:
        payload = yaml.safe_load(Path(task_path).read_text(encoding="utf-8")) or {}
    except OSError:
        return _slug(Path(task_path).stem)
    if isinstance(payload, dict) and payload.get("id"):
        return _slug(str(payload["id"]))
    return _slug(Path(task_path).stem)


def _aggregate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_distribution = Counter(str(record.get("status", "unknown")) for record in records)
    recorded = [record for record in records if record.get("status") != "error"]
    success_count = status_distribution.get("success", 0)
    fail_to_pass_passed = sum(
        int((record.get("fail_to_pass") or {}).get("passed", 0))
        for record in recorded
    )
    fail_to_pass_total = sum(
        int((record.get("fail_to_pass") or {}).get("total", 0))
        for record in recorded
    )
    pass_to_pass_passed = sum(
        int((record.get("pass_to_pass") or {}).get("passed", 0))
        for record in recorded
    )
    pass_to_pass_total = sum(
        int((record.get("pass_to_pass") or {}).get("total", 0))
        for record in recorded
    )
    structured_skipped = [
        record
        for record in recorded
        if record.get("status") in {"invalid_task", "flaky_task", "inconclusive"}
        and (record.get("quality_gate_reason") or record.get("failure_reason"))
    ]
    return {
        "schema_version": "repo_harness_aggregate_metrics_v2_v0",
        "total_runs": len(records),
        "task_count": len({record.get("task_id") for record in records}),
        "recorded_runs": len(recorded),
        "error_runs": status_distribution.get("error", 0),
        "status_distribution": dict(sorted(status_distribution.items())),
        "final_verifier_status_distribution": dict(
            sorted(Counter(str(record.get("final_verifier_status", "unknown")) for record in records).items())
        ),
        "run_outcome_distribution": dict(sorted(status_distribution.items())),
        "success_count": success_count,
        "task_success_rate": (success_count / len(recorded)) if recorded else 0.0,
        "agent_loop_runs": sum(1 for record in recorded if record.get("entered_agent_loop")),
        "formal_final_verifier_runs": sum(
            1 for record in recorded if record.get("formal_final_verifier_ran")
        ),
        "structured_skipped_runs": len(structured_skipped),
        "quality_gate_reason_distribution": dict(
            sorted(
                Counter(
                    str(record.get("quality_gate_reason") or "none")
                    for record in recorded
                    if record.get("quality_gate_reason")
                ).items()
            )
        ),
        "fail_to_pass_pass_rate": (
            fail_to_pass_passed / fail_to_pass_total if fail_to_pass_total else None
        ),
        "pass_to_pass_keep_rate": (
            pass_to_pass_passed / pass_to_pass_total if pass_to_pass_total else None
        ),
        "average_turn_count": _average(recorded, "turn_count"),
        "average_tool_call_count": _average(recorded, "tool_call_count"),
        "average_test_run_count": _average(recorded, "test_run_count"),
        "permission_denial_rate": (
            sum(int(record.get("permission_denial_count", 0)) for record in recorded)
            / len(recorded)
            if recorded
            else 0.0
        ),
        "invalid_tool_call_rate": (
            sum(int(record.get("invalid_tool_call_count", 0)) for record in recorded)
            / len(recorded)
            if recorded
            else 0.0
        ),
        "timeout_rate": (
            sum(1 for record in recorded if record.get("timeout")) / len(recorded)
            if recorded
            else 0.0
        ),
        "patch_size": {
            "average_added_lines": _average(recorded, "patch_added_lines"),
            "average_removed_lines": _average(recorded, "patch_removed_lines"),
        },
        "environment_failure_distribution": dict(
            sorted(
                Counter(
                    str(record.get("quality_gate_reason") or record.get("failure_reason"))
                    for record in recorded
                    if record.get("status") in {"invalid_task", "flaky_task", "inconclusive"}
                ).items()
            )
        ),
    }


def _average(records: list[dict[str, Any]], key: str) -> float:
    if not records:
        return 0.0
    return sum(float(record.get(key, 0) or 0) for record in records) / len(records)


def _export_audit_status(root: Path) -> dict[str, str]:
    exports = root / "exports"
    if not exports.exists() or not exports.is_dir():
        return {"status": "missing", "reason": "exports directory missing"}
    try:
        inspect_export(exports, all_exports=True, assert_clean=True)
    except RepoHarnessError as exc:
        return {"status": "failed", "reason": str(exc)}
    return {"status": "clean", "reason": "inspect-export --assert-clean passed"}


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _load_minimums(path: str | Path | None) -> ExperimentMinimums:
    if path is None:
        return ExperimentMinimums()
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ConfigError(f"无法读取实验阈值配置：{path}") from exc
    try:
        return ExperimentMinimums.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def _write_summary(path: Path, *, manifest: dict[str, Any], aggregate: dict[str, Any]) -> None:
    lines = [
        f"# Experiment {manifest['experiment_id']}",
        "",
        f"- Total runs: {aggregate['total_runs']}",
        f"- Recorded runs: {aggregate['recorded_runs']}",
        f"- Error runs: {aggregate['error_runs']}",
        f"- Model: {manifest['model_provider']} / {manifest['model_id']}",
        f"- Scaffold: {manifest['scaffold_id']}",
        "",
        "## Status Distribution",
        "",
    ]
    for status, count in aggregate["status_distribution"].items():
        lines.append(f"- {status}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
