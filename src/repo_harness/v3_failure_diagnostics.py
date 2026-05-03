"""V3 core failure diagnostics and filtering evidence."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.reward import CoreFailureDiagnostics
from repo_harness.schema_versions import CORE_FAILURE_DIAGNOSTICS_SCHEMA_VERSION
from repo_harness.trajectory import ArtifactRef, read_jsonl
from repo_harness.v3_acceptance import CommandLogEntry
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash


CORE_REPORT_VERSION = "repo_harness_core_failure_diagnostics_report_v3_v0"
FAILURE_DISTRIBUTION_REPORT_VERSION = "repo_harness_failure_distribution_report_v3_v0"
FAILURE_DIAGNOSTICS_STAGE_REPORT_VERSION = "repo_harness_v3_failure_diagnostics_stage_report_v0"

REQUIRED_CORE_FIELDS = (
    "patch_size",
    "files_changed",
    "tool_call_count",
    "test_run_count",
    "invalid_tool_call_count",
    "unfinished_trajectory",
    "permission_violation_count",
    "regression_detected",
    "environment_failure_category",
    "parser_low_confidence",
    "no_patch_generated",
    "provider_transient",
    "deterministic_verifier_failure",
    "context_limit_failure",
    "no_progress_detected",
)

REQUIRED_DISTRIBUTION_CATEGORIES = (
    "provider",
    "docker_backend",
    "environment_setup",
    "verifier",
    "permission",
    "tool_protocol",
    "context_limit",
    "task_quality",
    "parser_confidence",
    "deterministic_verifier_failure",
)


def build_v3_failure_diagnostics(
    *,
    run_dir: str | Path,
    output_dir: str | Path,
    context_report: str | Path | None = None,
    long_rollout_report: str | Path | None = None,
) -> Path:
    """Build V3 core failure diagnostics from an existing RepoHarness run."""

    started_at = _utc_timestamp()
    source_run = Path(run_dir)
    output_root = Path(output_dir)
    if output_root.exists():
        raise ConfigError(f"Stage 10 output directory 已存在，不能覆盖：{output_root}")
    if not source_run.exists():
        raise ConfigError(f"run directory 不存在：{source_run}")
    output_root.mkdir(parents=True)

    copied_run = output_root / "input_run"
    shutil.copytree(source_run, copied_run)
    copied_context_report = _copy_optional_report(
        Path(context_report) if context_report is not None else None,
        output_root / "supporting_inputs" / "context_compaction_report.json",
    )
    copied_long_report = _copy_optional_report(
        Path(long_rollout_report) if long_rollout_report is not None else None,
        output_root / "supporting_inputs" / "long_rollout_diagnostics.json",
    )

    core_report_path = output_root / "failure_diagnostics_core_report.json"
    distribution_report_path = output_root / "failure_distribution_report.json"
    command_log_path = output_root / "command_log.jsonl"
    stage_report_path = output_root / "v3_failure_diagnostics_report.json"

    facts = _collect_core_facts(
        run_dir=copied_run,
        output_root=output_root,
        context_report=copied_context_report,
        long_rollout_report=copied_long_report,
    )
    core_report = _build_core_report(
        output_root=output_root,
        run_dir=copied_run,
        facts=facts,
        context_report=copied_context_report,
        long_rollout_report=copied_long_report,
    )
    _write_json(core_report_path, core_report)
    distribution_report = _build_distribution_report(
        output_root=output_root,
        run_dir=copied_run,
        core_report_path=core_report_path,
        facts=facts,
    )
    _write_json(distribution_report_path, distribution_report)
    stage_report = {
        "schema_version": FAILURE_DIAGNOSTICS_STAGE_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "input_run_ref": _artifact_ref(
            copied_run,
            base_dir=output_root,
            artifact_id="stage10_input_run",
            kind="directory",
        ),
        "core_report_ref": _artifact_ref(
            core_report_path,
            base_dir=output_root,
            artifact_id="failure_diagnostics_core_report",
            kind="json",
        ),
        "distribution_report_ref": _artifact_ref(
            distribution_report_path,
            base_dir=output_root,
            artifact_id="failure_distribution_report",
            kind="json",
        ),
    }
    _write_json(stage_report_path, stage_report)
    command_argv = [
        "repo-harness",
        "build-v3-reward-diagnostics",
        "--run-dir",
        source_run.as_posix(),
        "--output-dir",
        output_root.as_posix(),
    ]
    if context_report is not None:
        command_argv.extend(["--context-report", Path(context_report).as_posix()])
    if long_rollout_report is not None:
        command_argv.extend(["--long-rollout-report", Path(long_rollout_report).as_posix()])
    _append_command_log(
        command_log_path,
        command_name="build-v3-reward-diagnostics",
        argv=command_argv,
        started_at=started_at,
        input_paths=[
            source_run,
            *((Path(context_report),) if context_report is not None else ()),
            *((Path(long_rollout_report),) if long_rollout_report is not None else ()),
        ],
        output_paths=[core_report_path, distribution_report_path, stage_report_path],
        exit_code=0,
    )
    return output_root


def inspect_reward_diagnostics(
    run_dir: str | Path,
    *,
    core_report: str | Path,
    distribution_report: str | Path,
    assert_core_complete: bool = False,
) -> str:
    """Read and validate V3 core failure diagnostics reports."""

    root = Path(run_dir)
    core_path = Path(core_report)
    distribution_path = Path(distribution_report)
    failures: list[str] = []
    core = _read_json_for_inspect(core_path, failures)
    distribution = _read_json_for_inspect(distribution_path, failures)
    if core.get("schema_version") != CORE_REPORT_VERSION:
        failures.append("failure_diagnostics_core_report schema_version 无效。")
    if distribution.get("schema_version") != FAILURE_DISTRIBUTION_REPORT_VERSION:
        failures.append("failure_distribution_report schema_version 无效。")

    _inspect_artifact_ref(root, core.get("input_run_ref"), failures)
    _inspect_report_refs(root, core, failures)
    _inspect_distribution_refs(root, distribution, failures)
    _inspect_diagnostics(core, failures)

    core_fields = core.get("core_fields", {})
    category_counts = distribution.get("category_counts", {})
    if assert_core_complete:
        if not isinstance(core_fields, dict):
            failures.append("failure_diagnostics_core_report core_fields 必须是 object。")
            core_fields = {}
        for field in REQUIRED_CORE_FIELDS:
            if field not in core_fields:
                failures.append(f"core failure diagnostics 缺少字段：{field}")
        if not isinstance(category_counts, dict):
            failures.append("failure_distribution_report category_counts 必须是 object。")
            category_counts = {}
        for category in REQUIRED_DISTRIBUTION_CATEGORIES:
            if category not in category_counts:
                failures.append(f"failure distribution 缺少类别：{category}")
        recommendation = core.get("training_filter_recommendation", {})
        if recommendation.get("recommended_state") not in {"trainable", "diagnostic_only", "blocked"}:
            failures.append("training_filter_recommendation recommended_state 无效。")
        if core_fields.get("no_patch_generated") is True and "no_patch_generated" not in recommendation.get("reasons", []):
            failures.append("no_patch_generated 必须进入 training filter reason。")
        if core_fields.get("deterministic_verifier_failure") is True and category_counts.get("deterministic_verifier_failure", 0) < 1:
            failures.append("deterministic verifier failure 必须进入分布统计。")

    lines = [
        f"Reward diagnostics directory: {root}",
        f"Core report: {core_path}",
        f"Distribution report: {distribution_path}",
        f"Core field count: {len(core_fields) if isinstance(core_fields, dict) else 0}",
        "Distribution categories: " + ", ".join(sorted(category_counts)) if isinstance(category_counts, dict) else "Distribution categories: invalid",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_core_complete:
        lines.append("Inspect reward diagnostics: core complete")
    lines.append("Inspect reward diagnostics: passed")
    return "\n".join(lines)


def _collect_core_facts(
    *,
    run_dir: Path,
    output_root: Path,
    context_report: Path | None,
    long_rollout_report: Path | None,
) -> dict[str, Any]:
    metrics = _read_json_if_exists(run_dir / "metrics.json")
    verifier = _read_json_if_exists(run_dir / "verifier.json")
    baseline = _read_json_if_exists(run_dir / "baseline.json")
    status = _read_json_if_exists(run_dir / "run_status.json")
    events = read_jsonl(run_dir / "events.jsonl")
    patch_stats = metrics.get("patch_stats", {}) if isinstance(metrics.get("patch_stats"), dict) else {}
    files_changed = _files_changed(patch_stats)
    patch_size = int(patch_stats.get("added_lines", 0) or 0) + int(patch_stats.get("removed_lines", 0) or 0)
    final_verifier_failed = verifier.get("accepted") is False and verifier.get("verifier_stage") == "final"
    parser_low_confidence = (
        float(verifier.get("parser_confidence", 1.0) or 0.0) < 0.5
        or float(baseline.get("parser_confidence", 1.0) or 0.0) < 0.5
        or verifier.get("error_type") == "low_parser_confidence"
    )
    no_progress_detected = _long_report_has(long_rollout_report, "no_progress")
    repeated_tool_call_loop = _long_report_has(long_rollout_report, "repeated_tool_call")
    context_limit_failure = (
        metrics.get("interaction_efficiency", {}).get("agent_stop_reason") == "context_limit"
        or any(event.get("error_type") == "context_limit" for event in events)
        or _long_report_has(long_rollout_report, "context_limit")
    )
    provider_transient = any(
        event.get("event_type") == "model_error"
        or event.get("data", {}).get("model_error_type") in {"rate_limit", "timeout", "provider_transient"}
        for event in events
    )
    environment_failure_category = _environment_failure_category(baseline, verifier, events)
    status_value = str(status.get("status") or "")
    unfinished_trajectory = status_value not in {"FINALIZED"} or metrics.get("interaction_efficiency", {}).get("agent_stop_reason") in {
        "max_turns",
        "context_limit",
        "timeout",
    }
    pass_to_pass = verifier.get("pass_to_pass", {}) if isinstance(verifier.get("pass_to_pass"), dict) else {}
    regression_detected = verifier.get("error_type") == "regression_detected" or int(pass_to_pass.get("passed", 0) or 0) < int(pass_to_pass.get("total", 0) or 0)
    deterministic_verifier_failure = bool(
        final_verifier_failed
        and verifier.get("error_type") not in {
            "dependency_error",
            "low_parser_confidence",
            "patch_apply_failed",
            "verification_workspace_error",
        }
        and not verifier.get("timeout")
    )
    core_fields = {
        "patch_size": patch_size,
        "files_changed": files_changed,
        "file_change_count": len(files_changed),
        "tool_call_count": int(metrics.get("tool_call_count", 0) or 0),
        "test_run_count": int(metrics.get("test_run_count", 0) or 0),
        "invalid_tool_call_count": int(metrics.get("invalid_tool_call_count", 0) or 0),
        "unfinished_trajectory": unfinished_trajectory,
        "permission_violation_count": int(metrics.get("permission_denial_count", 0) or 0),
        "regression_detected": regression_detected,
        "environment_failure_category": environment_failure_category,
        "environment_unstable": baseline.get("status") == "flaky",
        "docker_backend_failure": any(event.get("error_type") == "docker_backend" for event in events),
        "container_timeout": bool(verifier.get("timeout")) or any(event.get("error_type") == "container_timeout" for event in events),
        "source_materialization_failed": any(event.get("error_type") == "source_materialization_failed" for event in events),
        "dependency_setup_failed": baseline.get("dependency_error") in {"setup_failed", "setup_timeout", "dependency_error"},
        "parser_low_confidence": parser_low_confidence,
        "public_tests_pass_hidden_tests_fail": False,
        "no_patch_generated": patch_size == 0 and not files_changed,
        "no_progress_detected": no_progress_detected,
        "repeated_tool_call_loop": repeated_tool_call_loop,
        "provider_transient": provider_transient,
        "deterministic_verifier_failure": deterministic_verifier_failure,
        "context_limit_failure": context_limit_failure,
    }
    core_fields["source_refs"] = _source_file_refs(
        run_dir=run_dir,
        output_root=output_root,
        context_report=context_report,
        long_rollout_report=long_rollout_report,
    )
    return {
        "core_fields": core_fields,
        "run_id": str(metrics.get("run_id") or status.get("run_id") or run_dir.name),
        "task_id": str(baseline.get("task_id") or ""),
        "final_verifier_failed": final_verifier_failed,
        "verifier_error_type": verifier.get("error_type"),
        "baseline_status": baseline.get("status"),
        "status_value": status_value,
    }


def _build_core_report(
    *,
    output_root: Path,
    run_dir: Path,
    facts: dict[str, Any],
    context_report: Path | None,
    long_rollout_report: Path | None,
) -> dict[str, Any]:
    core_fields = facts["core_fields"]
    diagnostics = _build_diagnostics(
        run_dir=run_dir,
        facts=facts,
        source_refs=core_fields["source_refs"],
    )
    reasons = _training_filter_reasons(core_fields)
    return {
        "schema_version": CORE_REPORT_VERSION,
        "core_diagnostic_schema_version": CORE_FAILURE_DIAGNOSTICS_SCHEMA_VERSION,
        "generated_at": _utc_timestamp(),
        "subject_id": facts.get("run_id"),
        "task_id": facts.get("task_id"),
        "input_run_ref": _artifact_ref(
            run_dir,
            base_dir=output_root,
            artifact_id="core_failure_input_run",
            kind="directory",
        ),
        "supporting_report_refs": {
            "context_compaction": (
                _artifact_ref(
                    context_report,
                    base_dir=output_root,
                    artifact_id="context_compaction_report",
                    kind="json",
                )
                if context_report is not None
                else None
            ),
            "long_rollout": (
                _artifact_ref(
                    long_rollout_report,
                    base_dir=output_root,
                    artifact_id="long_rollout_diagnostics",
                    kind="json",
                )
                if long_rollout_report is not None
                else None
            ),
        },
        "core_fields": core_fields,
        "diagnostic_records": diagnostics,
        "training_filter_recommendation": {
            "recommended_state": "diagnostic_only" if reasons else "trainable",
            "reasons": reasons,
            "model_visible": False,
            "filtering_evidence_only": True,
        },
        "deferred_enhancements": [
            "penalty_weights",
            "deep_reward_hacking_analysis",
            "complex_distribution_statistics",
        ],
    }


def _build_distribution_report(
    *,
    output_root: Path,
    run_dir: Path,
    core_report_path: Path,
    facts: dict[str, Any],
) -> dict[str, Any]:
    core_fields = facts["core_fields"]
    category_counts = {category: 0 for category in REQUIRED_DISTRIBUTION_CATEGORIES}
    diagnostic_types: Counter[str] = Counter()

    if core_fields["provider_transient"]:
        category_counts["provider"] += 1
        diagnostic_types["provider_transient"] += 1
    if core_fields["docker_backend_failure"]:
        category_counts["docker_backend"] += 1
        diagnostic_types["docker_backend_failure"] += 1
    if core_fields["environment_failure_category"] != "none":
        category_counts["environment_setup"] += 1
        diagnostic_types[core_fields["environment_failure_category"]] += 1
    if facts["final_verifier_failed"]:
        category_counts["verifier"] += 1
        diagnostic_types["final_verifier_failed"] += 1
    if core_fields["permission_violation_count"] > 0:
        category_counts["permission"] += core_fields["permission_violation_count"]
        diagnostic_types["permission_violation"] += core_fields["permission_violation_count"]
    if core_fields["invalid_tool_call_count"] > 0:
        category_counts["tool_protocol"] += core_fields["invalid_tool_call_count"]
        diagnostic_types["invalid_tool_call"] += core_fields["invalid_tool_call_count"]
    if core_fields["context_limit_failure"]:
        category_counts["context_limit"] += 1
        diagnostic_types["context_limit_failure"] += 1
    if facts["baseline_status"] in {"invalid", "flaky"}:
        category_counts["task_quality"] += 1
        diagnostic_types["baseline_quality_failed"] += 1
    if core_fields["parser_low_confidence"]:
        category_counts["parser_confidence"] += 1
        diagnostic_types["parser_low_confidence"] += 1
    if core_fields["deterministic_verifier_failure"]:
        category_counts["deterministic_verifier_failure"] += 1
        diagnostic_types["deterministic_verifier_failure"] += 1
    if core_fields["no_patch_generated"]:
        diagnostic_types["no_patch_generated"] += 1
    if core_fields["no_progress_detected"]:
        diagnostic_types["no_progress_detected"] += 1
    if core_fields["repeated_tool_call_loop"]:
        diagnostic_types["repeated_tool_call_loop"] += 1

    return {
        "schema_version": FAILURE_DISTRIBUTION_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "subject_id": facts.get("run_id"),
        "input_run_ref": _artifact_ref(
            run_dir,
            base_dir=output_root,
            artifact_id="failure_distribution_input_run",
            kind="directory",
        ),
        "core_report_ref": _artifact_ref(
            core_report_path,
            base_dir=output_root,
            artifact_id="failure_distribution_core_report",
            kind="json",
        ),
        "category_counts": category_counts,
        "diagnostic_type_distribution": dict(sorted(diagnostic_types.items())),
        "distribution_scope": {
            "single_run": True,
            "categories_required_by_v3_core": list(REQUIRED_DISTRIBUTION_CATEGORIES),
            "enhanced_statistics_enabled": False,
        },
    }


def _build_diagnostics(
    *,
    run_dir: Path,
    facts: dict[str, Any],
    source_refs: dict[str, Any],
) -> list[dict[str, Any]]:
    core_fields = facts["core_fields"]
    diagnostics: list[CoreFailureDiagnostics] = []
    common = {
        "run_id": str(facts.get("run_id") or run_dir.name),
        "patch_size": core_fields["patch_size"],
        "files_changed": core_fields["files_changed"],
        "tool_call_count": core_fields["tool_call_count"],
        "test_run_count": core_fields["test_run_count"],
        "invalid_tool_call_count": core_fields["invalid_tool_call_count"],
        "permission_violation_count": core_fields["permission_violation_count"],
        "regression_detected": core_fields["regression_detected"],
        "environment_failure_category": core_fields["environment_failure_category"],
        "environment_unstable": core_fields["environment_unstable"],
        "docker_backend_failure": core_fields["docker_backend_failure"],
        "container_timeout": core_fields["container_timeout"],
        "source_materialization_failed": core_fields["source_materialization_failed"],
        "dependency_setup_failed": core_fields["dependency_setup_failed"],
        "parser_low_confidence": core_fields["parser_low_confidence"],
        "public_tests_pass_hidden_tests_fail": core_fields["public_tests_pass_hidden_tests_fail"],
        "unfinished_trajectory": core_fields["unfinished_trajectory"],
        "no_patch_generated": core_fields["no_patch_generated"],
        "no_progress": core_fields["no_progress_detected"],
        "repeated_tool_call_loop": core_fields["repeated_tool_call_loop"],
        "context_limit_failure": core_fields["context_limit_failure"],
        "provider_transient": core_fields["provider_transient"],
        "deterministic_verifier_failure": core_fields["deterministic_verifier_failure"],
        "reward_hacking_suspected": False,
    }
    verifier_ref = source_refs.get("verifier_file_ref")
    if core_fields["deterministic_verifier_failure"]:
        diagnostics.append(
            CoreFailureDiagnostics(
                diagnostic_id=f"{facts.get('run_id') or run_dir.name}:deterministic_verifier_failure",
                failure_category="verifier",
                failure_type="deterministic_verifier_failure",
                source_component="final_verifier",
                blocks_training=True,
                hidden_details_ref=ArtifactRef.model_validate(verifier_ref) if isinstance(verifier_ref, dict) else None,
                **common,
            )
        )
    if core_fields["no_patch_generated"]:
        diagnostics.append(
            CoreFailureDiagnostics(
                diagnostic_id=f"{facts.get('run_id') or run_dir.name}:no_patch_generated",
                failure_category="agent_output",
                failure_type="no_patch_generated",
                source_component="agent_loop",
                blocks_training=True,
                hidden_details_ref=ArtifactRef.model_validate(source_refs["metrics_file_ref"]),
                **common,
            )
        )
    if core_fields["no_progress_detected"]:
        diagnostics.append(
            CoreFailureDiagnostics(
                diagnostic_id=f"{facts.get('run_id') or run_dir.name}:no_progress_detected",
                failure_category="long_rollout",
                failure_type="no_progress_detected",
                source_component="agent_loop",
                blocks_training=True,
                hidden_details_ref=(
                    ArtifactRef.model_validate(source_refs["long_rollout_report_ref"])
                    if isinstance(source_refs.get("long_rollout_report_ref"), dict)
                    else None
                ),
                **common,
            )
        )
    if not diagnostics:
        diagnostics.append(
            CoreFailureDiagnostics(
                diagnostic_id=f"{facts.get('run_id') or run_dir.name}:no_core_failure",
                failure_category="none",
                failure_type="no_core_failure",
                source_component="core_diagnostics",
                blocks_training=False,
                **common,
            )
        )
    visibility_guard_fields = {
        "reward_metadata_visible_to_model",
        "run_outcome_visible_to_model",
        "hidden_failure_details_visible_to_model",
    }
    return [
        item.model_dump(mode="json", exclude=visibility_guard_fields)
        for item in diagnostics
    ]


def _training_filter_reasons(core_fields: dict[str, Any]) -> list[str]:
    reasons = []
    for field in [
        "unfinished_trajectory",
        "regression_detected",
        "parser_low_confidence",
        "no_patch_generated",
        "provider_transient",
        "deterministic_verifier_failure",
        "context_limit_failure",
        "no_progress_detected",
    ]:
        if core_fields.get(field):
            reasons.append(field)
    if core_fields.get("permission_violation_count", 0) > 0:
        reasons.append("permission_violation")
    if core_fields.get("invalid_tool_call_count", 0) > 0:
        reasons.append("invalid_tool_call")
    if core_fields.get("environment_failure_category") != "none":
        reasons.append(str(core_fields.get("environment_failure_category")))
    return reasons


def _files_changed(patch_stats: dict[str, Any]) -> list[str]:
    files: set[str] = set()
    for key in [
        "changed_files",
        "modified_files",
        "added_files",
        "deleted_files",
        "renamed_files",
        "untracked_text_files",
        "binary_files",
        "symlink_files",
    ]:
        value = patch_stats.get(key, [])
        if isinstance(value, list):
            files.update(str(item) for item in value)
    return sorted(files)


def _environment_failure_category(
    baseline: dict[str, Any],
    verifier: dict[str, Any],
    events: list[dict[str, Any]],
) -> str:
    dependency_error = baseline.get("dependency_error")
    if dependency_error:
        return str(dependency_error)
    if baseline.get("status") == "flaky":
        return "flaky_baseline"
    if baseline.get("status") == "invalid":
        return "invalid_baseline"
    verifier_error = verifier.get("error_type")
    if verifier_error in {"dependency_error", "verification_workspace_error"}:
        return str(verifier_error)
    if any(event.get("error_type") == "source_materialization_failed" for event in events):
        return "source_materialization_failed"
    return "none"


def _source_file_refs(
    *,
    run_dir: Path,
    output_root: Path,
    context_report: Path | None,
    long_rollout_report: Path | None,
) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for name, key, kind in [
        ("metrics.json", "metrics_file_ref", "json"),
        ("verifier.json", "verifier_file_ref", "json"),
        ("baseline.json", "baseline_file_ref", "json"),
        ("events.jsonl", "events_file_ref", "jsonl"),
        ("final.patch", "final_patch_file_ref", "patch"),
    ]:
        path = run_dir / name
        if path.exists():
            refs[key] = _artifact_ref(
                path,
                base_dir=output_root,
                artifact_id=f"source_{Path(name).stem}",
                kind=kind,
            )
    if context_report is not None:
        refs["context_report_ref"] = _artifact_ref(
            context_report,
            base_dir=output_root,
            artifact_id="source_context_report",
            kind="json",
        )
    if long_rollout_report is not None:
        refs["long_rollout_report_ref"] = _artifact_ref(
            long_rollout_report,
            base_dir=output_root,
            artifact_id="source_long_rollout_report",
            kind="json",
        )
    return refs

def _long_report_has(path: Path | None, diagnostic_type: str) -> bool:
    if path is None or not path.exists():
        return False
    payload = _read_json_if_exists(path)
    diagnostics = payload.get("diagnostics", [])
    if not isinstance(diagnostics, list):
        return False
    return any(item.get("diagnostic_type") == diagnostic_type for item in diagnostics if isinstance(item, dict))


def _inspect_report_refs(root: Path, payload: dict[str, Any], failures: list[str]) -> None:
    source_refs = payload.get("core_fields", {}).get("source_refs", {})
    if not isinstance(source_refs, dict):
        failures.append("core_fields.source_refs 必须是 object。")
        return
    for key, ref in source_refs.items():
        if ref is not None:
            _inspect_artifact_ref(root, ref, failures, label=key)
    supporting_refs = payload.get("supporting_report_refs", {})
    if isinstance(supporting_refs, dict):
        for key, ref in supporting_refs.items():
            if ref is not None:
                _inspect_artifact_ref(root, ref, failures, label=f"supporting_report_refs.{key}")


def _inspect_distribution_refs(root: Path, payload: dict[str, Any], failures: list[str]) -> None:
    _inspect_artifact_ref(root, payload.get("input_run_ref"), failures, label="distribution.input_run_ref")
    _inspect_artifact_ref(root, payload.get("core_report_ref"), failures, label="distribution.core_report_ref")


def _inspect_diagnostics(payload: dict[str, Any], failures: list[str]) -> None:
    diagnostics = payload.get("diagnostic_records", [])
    if not isinstance(diagnostics, list) or not diagnostics:
        failures.append("diagnostic_records 必须是非空列表。")
        return
    for index, raw in enumerate(diagnostics):
        try:
            diagnostic = CoreFailureDiagnostics.model_validate(raw)
        except ValidationError as exc:
            failures.append(f"diagnostic_records[{index}] schema 无效：{exc}")
            continue
        if diagnostic.model_visible_summary:
            failures.append(f"{diagnostic.diagnostic_id} 不应包含 model_visible_summary。")
        if diagnostic.blocks_training and not diagnostic.diagnostic_only:
            failures.append(f"{diagnostic.diagnostic_id} 阻断训练时必须 diagnostic_only。")


def _inspect_artifact_ref(
    root: Path,
    ref_payload: Any,
    failures: list[str],
    *,
    label: str = "ArtifactRef",
) -> Path | None:
    if not isinstance(ref_payload, dict):
        failures.append(f"{label} 缺失或不是 object。")
        return None
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        failures.append(f"{label} schema 无效：{exc}")
        return None
    relative = Path(ref.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        failures.append(f"{label} relative_path 必须留在诊断目录内：{ref.relative_path}")
        return None
    path = root / relative
    if not path.exists():
        failures.append(f"{label} 路径不存在：{ref.relative_path}")
        return None
    actual_sha = compute_source_tree_hash(path) if path.is_dir() else compute_file_sha256(path)
    if actual_sha != ref.sha256:
        failures.append(f"{label} sha256 不匹配：{ref.relative_path}")
    if not path.is_dir() and path.stat().st_size != ref.size_bytes:
        failures.append(f"{label} size_bytes 不匹配：{ref.relative_path}")
    return path


def _copy_optional_report(source: Path | None, target: Path) -> Path | None:
    if source is None:
        return None
    if not source.exists():
        raise ConfigError(f"supporting report 不存在：{source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def _artifact_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
    redaction_status: str = "not_required",
) -> dict[str, Any]:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = compute_file_sha256(path)
        size_bytes = path.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status=redaction_status,
        retention_policy="keep",
    ).model_dump(mode="json")


def _append_command_log(
    path: Path,
    *,
    command_name: str,
    argv: list[str],
    started_at: str,
    input_paths: list[Path],
    output_paths: list[Path],
    exit_code: int,
) -> None:
    entry = CommandLogEntry(
        command_name=command_name,
        argv=argv,
        cwd=Path.cwd().as_posix(),
        input_refs=[
            _artifact_ref(item, base_dir=Path.cwd(), artifact_id=f"{command_name}_input_{index}", kind=_kind_for_path(item))
            for index, item in enumerate(input_paths, start=1)
            if item.exists()
        ],
        output_refs=[
            _artifact_ref(item, base_dir=Path.cwd(), artifact_id=f"{command_name}_output_{index}", kind=_kind_for_path(item))
            for index, item in enumerate(output_paths, start=1)
            if item.exists()
        ],
        exit_code=exit_code,
        tool_or_cli_version=f"repo-harness {__version__}",
        started_at=started_at,
        finished_at=_utc_timestamp(),
    )
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")


def _kind_for_path(path: Path) -> str:
    if path.is_dir():
        return "directory"
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "file"


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"JSON 文件不存在：{path}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 文件无效：{path}: {exc}")
        return {}
    if not isinstance(data, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return data


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
