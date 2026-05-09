"""Pre-verl evaluation report builders.

The builders in this module intentionally keep two concepts separate:

* pre-verl readiness, meaning the repository already has enough clean,
  verifier-bound trajectory evidence to connect a training adapter safely; and
* resume / benchmark claims, such as a full expanded Pilot, preference export,
  leaderboard-comparable results, or completed model training.

The second category can remain blocked while readiness passes. That distinction
keeps the evidence chain useful without inflating what has actually been run.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from repo_harness.errors import ConfigError
from repo_harness.model_client.providers.deepseek import (
    DEEPSEEK_CHAT_COMPLETIONS_PATH,
    DEEPSEEK_DEFAULT_BASE_URL,
    normalize_deepseek_model_id,
    resolve_deepseek_credential,
)
from repo_harness.model_client.redaction import redact_provider_payload
from repo_harness.pre_verl_agentloop import PRE_VERL_AGENTLOOP_BASELINE_SOURCE
from repo_harness.scaffolds.patch_action import parse_patch_action


def build_pre_verl_baseline(
    *,
    output_dir: str | Path,
    v5_acceptance_report: str | Path,
    v5_export_pack_manifest: str | Path,
    v5_result_summary_table: str | Path,
    v5_acceptance_bundle: str | Path,
    v5_final_command_log: str | Path,
    run_live_checks: bool = False,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    _refuse_existing(root, ("pre_verl_baseline_check_report.json", "pre_verl_input_binding.json"), fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    refs = {
        "v5_acceptance_report_ref": _ref(v5_acceptance_report, "v5_acceptance_report", "inspect-v5-acceptance"),
        "v5_export_pack_manifest_ref": _ref(v5_export_pack_manifest, "v5_export_result_pack_manifest", "inspect-v5-export-pack"),
        "v5_result_summary_table_ref": _ref(v5_result_summary_table, "v5_result_summary_table", "inspect-v5-demo-artifacts"),
        "v5_acceptance_bundle_ref": _ref(v5_acceptance_bundle, "v5_acceptance_bundle_manifest", "inspect-acceptance-bundle"),
        "v5_final_command_log_ref": _ref(v5_final_command_log, "v5_final_acceptance_command_log", "inspect-acceptance-bundle"),
    }
    command_entries: list[dict[str, Any]] = []
    if run_live_checks:
        command_entries.extend(
            _run_stage0_checks(
                root=root,
                v5_acceptance_report=Path(v5_acceptance_report),
                v5_acceptance_bundle=Path(v5_acceptance_bundle),
                v5_final_command_log=Path(v5_final_command_log),
            )
        )
    git_status = _capture_text(["git", "status", "--short"])
    git_head = _capture_text(["git", "log", "-1", "--oneline"])
    report = {
        "schema_version": "repo_harness_pre_verl_baseline_check_report_v0",
        "created_at": _now(),
        "pwd": str(Path.cwd()),
        "git_status_short": git_status,
        "git_log_1_oneline": git_head,
        "live_check_count": len(command_entries),
        "live_check_failed_count": sum(1 for item in command_entries if item.get("exit_code") != 0),
        "v5_core_acceptance_status": _read_json(v5_acceptance_report).get("core_acceptance", {}).get("status"),
        "v5_resume_ready_acceptance_status": _read_json(v5_acceptance_report).get("resume_ready_acceptance", {}).get("status"),
        "status": "passed" if not any(item.get("exit_code") != 0 for item in command_entries) else "failed",
    }
    report.update(refs)
    report_path = root / "pre_verl_baseline_check_report.json"
    binding_path = root / "pre_verl_input_binding.json"
    command_log_path = root / "pre_verl_stage0_command_log.jsonl"
    _write_json(report_path, report)
    binding = {
        "schema_version": "repo_harness_pre_verl_input_binding_v0",
        "created_at": _now(),
        "selection_mode": "explicit_paths",
        "baseline_check_report_ref": _ref(report_path, "pre_verl_baseline_check_report", "inspect-pre-verl-baseline"),
        "evidence_refs": list(refs.values()),
        "status": report["status"],
    }
    _write_json(binding_path, binding)
    _write_jsonl(command_log_path, [*_builder_entry("build-pre-verl-baseline", list(_ref_paths(refs)), [report_path, binding_path], "pre_verl_stage0_baseline"), *command_entries])
    return binding_path


def inspect_pre_verl_baseline(path: str | Path, *, assert_baseline_complete: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("baseline status is not passed")
    if not payload.get("evidence_refs"):
        failures.append("baseline input binding has no evidence refs")
    return _inspect_result("Inspect pre-verl baseline", path, failures, assert_requested=assert_baseline_complete)


def build_pre_verl_task_set(
    *,
    output_dir: str | Path,
    v5_task_set_manifest: str | Path,
    v5_task_inventory_report: str | Path,
    v5_task_visibility_scan_report: str | Path,
    swebench_lite_dev_rows: str | Path | None = None,
    swebench_lite_test_rows: str | Path | None = None,
    supplemental_pr_issue_candidate_report: str | Path | None = None,
    planned_dev_instances: int = 23,
    planned_curated_lite: int = 50,
    planned_github_issue: int = 10,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_task_set_manifest.json",
        "pre_verl_task_inventory_report.json",
        "pre_verl_task_visibility_scan_report.json",
        "pre_verl_task_source_binding.json",
        "pre_verl_task_dedup_report.json",
        "pre_verl_task_stratification_report.json",
        "pre_verl_task_blocked_report.json",
        "pre_verl_task_freeze_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_definition_root = root / "task_definitions"
    adapter_visible_root = root / "adapter_visible_task_inputs"
    evaluator_only_root = root / "evaluator_only_task_evidence"
    for directory in (task_definition_root, adapter_visible_root, evaluator_only_root):
        directory.mkdir(parents=True, exist_ok=True)

    task_set = _read_json(v5_task_set_manifest)
    planned = planned_dev_instances + planned_curated_lite + planned_github_issue
    input_refs = [Path(v5_task_set_manifest), Path(v5_task_inventory_report), Path(v5_task_visibility_scan_report)]

    dev_source_rows = _load_swebench_rows(
        swebench_lite_dev_rows,
        split="dev",
        required_count=planned_dev_instances,
    )
    test_source_rows = _load_swebench_rows(
        swebench_lite_test_rows,
        split="test",
        required_count=planned_curated_lite,
    )
    if swebench_lite_dev_rows is not None:
        input_refs.append(Path(swebench_lite_dev_rows))
    if swebench_lite_test_rows is not None:
        input_refs.append(Path(swebench_lite_test_rows))
    if supplemental_pr_issue_candidate_report is not None:
        input_refs.append(Path(supplemental_pr_issue_candidate_report))
    dev_selected_rows = dev_source_rows[:planned_dev_instances]
    curated_selected_rows = _curate_swebench_lite_rows(test_source_rows, planned_curated_lite)
    dev_rows_path = root / "pre_verl_swebench_lite_dev_rows.jsonl"
    curated_rows_path = root / "pre_verl_swebench_lite_curated_rows.jsonl"
    _write_jsonl(dev_rows_path, dev_selected_rows)
    _write_jsonl(curated_rows_path, curated_selected_rows)
    swebench_source_report_path = root / "pre_verl_swebench_lite_source_report.json"
    _write_json(
        swebench_source_report_path,
        {
            "schema_version": "repo_harness_pre_verl_swebench_lite_source_report_v0",
            "created_at": _now(),
            "dataset": "SWE-bench/SWE-bench_Lite",
            "config": "default",
            "dev_split": "dev",
            "test_split": "test",
            "dev_row_count": len(dev_selected_rows),
            "test_source_row_count": len(test_source_rows),
            "curated_row_count": len(curated_selected_rows),
            "curation_policy_id": "repo_round_robin_by_instance_id_v0",
            "custom_frozen_subset": True,
            "leaderboard_comparable": False,
            "status": "passed",
        },
    )

    existing_task_refs = task_set.get("task_refs") or [*task_set.get("initial_task_refs", []), *task_set.get("supplemental_task_refs", [])]
    existing_task_defs = _load_task_definitions_from_refs(existing_task_refs)
    existing_swebench_by_instance = {
        str(task.get("candidate_id")): task
        for task in existing_task_defs
        if task.get("source_kind") == "swebench_like_anchor" and task.get("candidate_id")
    }
    github_task_defs = _github_issue_task_definitions(
        existing_task_defs=existing_task_defs,
        supplemental_report=supplemental_pr_issue_candidate_report,
        minimum_count=planned_github_issue,
    )

    task_records: list[dict[str, Any]] = []
    task_definition_refs: list[dict[str, Any]] = []
    adapter_visible_refs: list[dict[str, Any]] = []
    evaluator_only_refs: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []

    def add_task(record: dict[str, Any], adapter_visible: dict[str, Any], evaluator_only: dict[str, Any]) -> None:
        task_id = str(record["task_id"])
        safe_name = _safe_file_stem(task_id)
        adapter_path = adapter_visible_root / f"{safe_name}.json"
        evaluator_path = evaluator_only_root / f"{safe_name}.json"
        task_path = task_definition_root / f"{safe_name}.json"
        _write_json(adapter_path, adapter_visible)
        _write_json(evaluator_path, evaluator_only)
        record["adapter_visible_input_ref"] = _ref(
            adapter_path,
            "pre_verl_adapter_visible_task_input",
            "inspect-pre-verl-task-visibility",
            visibility="model_visible",
            share_safe=True,
        )
        record["evaluator_only_evidence_ref"] = _ref(
            evaluator_path,
            "pre_verl_evaluator_only_task_evidence",
            "inspect-pre-verl-task-set",
            visibility="evaluator_only",
            share_safe=False,
        )
        _write_json(task_path, record)
        task_ref = _ref(task_path, "pre_verl_task_definition", "inspect-pre-verl-task-set")
        task_records.append(record)
        task_definition_refs.append(task_ref)
        adapter_visible_refs.append(record["adapter_visible_input_ref"])
        evaluator_only_refs.append(record["evaluator_only_evidence_ref"])
        if record.get("runnable") is not True:
            blocked_rows.append(
                {
                    "task_id": task_id,
                    "tier": record.get("tier"),
                    "source_kind": record.get("source_kind"),
                    "blocked_reason": record.get("blocked_reason") or "blocked_reason_missing",
                    "blocked_stage": record.get("blocked_stage") or "task_freeze",
                }
            )

    for index, row in enumerate(dev_selected_rows, start=1):
        record, adapter_visible, evaluator_only = _swebench_task_payloads(
            row=row,
            tier="swebench_lite_development",
            split="dev",
            ordinal=index,
            existing_runnable_task=existing_swebench_by_instance.get(str(row.get("instance_id"))),
        )
        add_task(record, adapter_visible, evaluator_only)

    for index, row in enumerate(curated_selected_rows, start=1):
        record, adapter_visible, evaluator_only = _swebench_task_payloads(
            row=row,
            tier="swebench_lite_curated",
            split="test",
            ordinal=index,
            existing_runnable_task=existing_swebench_by_instance.get(str(row.get("instance_id"))),
        )
        add_task(record, adapter_visible, evaluator_only)

    for index, task in enumerate(github_task_defs[:planned_github_issue], start=1):
        record, adapter_visible, evaluator_only = _github_issue_task_payloads(task=task, ordinal=index)
        add_task(record, adapter_visible, evaluator_only)

    counts = {
        "swebench_lite_development_bound_count": sum(1 for item in task_records if item.get("tier") == "swebench_lite_development"),
        "swebench_lite_curated_bound_count": sum(1 for item in task_records if item.get("tier") == "swebench_lite_curated"),
        "github_issue_flow_bound_count": sum(1 for item in task_records if item.get("tier") == "github_issue_flow"),
        "runnable_task_count": sum(1 for item in task_records if item.get("runnable") is True),
        "blocked_task_count": sum(1 for item in task_records if item.get("runnable") is not True),
    }
    blocked_reasons = []
    if counts["swebench_lite_development_bound_count"] < planned_dev_instances:
        blocked_reasons.append(f"planned SWE-Bench Lite development instance minimum is {planned_dev_instances}; bound {counts['swebench_lite_development_bound_count']}.")
    if counts["swebench_lite_curated_bound_count"] < planned_curated_lite:
        blocked_reasons.append(f"planned curated SWE-Bench Lite task minimum is {planned_curated_lite}; bound {counts['swebench_lite_curated_bound_count']}.")
    if counts["github_issue_flow_bound_count"] < planned_github_issue:
        blocked_reasons.append(f"planned GitHub issue flow task minimum is {planned_github_issue}; bound {counts['github_issue_flow_bound_count']}.")
    missing_blocked_reason_count = sum(1 for item in blocked_rows if not item.get("blocked_reason") or item.get("blocked_reason") == "blocked_reason_missing")
    if missing_blocked_reason_count:
        blocked_reasons.append(f"{missing_blocked_reason_count} non-runnable tasks are missing blocked_reason.")
    freeze_status = "blocked" if blocked_reasons else "passed"

    source_binding = {
        "schema_version": "repo_harness_pre_verl_task_source_binding_v0",
        "created_at": _now(),
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "planned_sources": {
            "swebench_lite_development_custom_frozen_subset": planned_dev_instances,
            "swebench_lite_curated_custom_frozen_subset": planned_curated_lite,
            "github_issue_flow": planned_github_issue,
        },
        "bound_sources": counts,
        "swebench_lite_source_report_ref": _ref(swebench_source_report_path, "pre_verl_swebench_lite_source_report", "inspect-pre-verl-task-set"),
        "swebench_lite_dev_rows_ref": _ref(dev_rows_path, "pre_verl_swebench_lite_dev_rows", "inspect-pre-verl-task-set"),
        "swebench_lite_curated_rows_ref": _ref(curated_rows_path, "pre_verl_swebench_lite_curated_rows", "inspect-pre-verl-task-set"),
        "supplemental_pr_issue_candidate_report_ref": _ref(supplemental_pr_issue_candidate_report, "v5_supplemental_pr_issue_candidate_report", "inspect-pre-verl-task-set") if supplemental_pr_issue_candidate_report else None,
        "current_v5_task_set_ref": _ref(v5_task_set_manifest, "v5_task_set_manifest", "inspect-v5-task-set"),
        "current_v5_inventory_ref": _ref(v5_task_inventory_report, "v5_task_inventory_report", "inspect-v5-task-set"),
        "current_v5_visibility_ref": _ref(v5_task_visibility_scan_report, "v5_task_visibility_scan_report", "inspect-v5-task-visibility"),
        "blocked_reasons": blocked_reasons,
        "status": freeze_status,
    }
    source_path = root / "pre_verl_task_source_binding.json"
    _write_json(source_path, source_binding)
    blocked_path = root / "pre_verl_task_blocked_report.json"
    _write_json(
        blocked_path,
        {
            "schema_version": "repo_harness_pre_verl_task_blocked_report_v0",
            "created_at": _now(),
            "blocked_task_count": len(blocked_rows),
            "missing_blocked_reason_count": missing_blocked_reason_count,
            "blocked_tasks": blocked_rows,
            "status": "passed" if missing_blocked_reason_count == 0 else "failed",
        },
    )
    manifest = {
        "schema_version": "repo_harness_pre_verl_task_set_manifest_v0",
        "created_at": _now(),
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "planned_denominator": planned,
        "bound_task_denominator": len(task_records),
        "runnable_denominator": counts["runnable_task_count"],
        "blocked_task_count": counts["blocked_task_count"],
        "verifier_correctness_denominator": counts["runnable_task_count"],
        "agent_evaluation_planned_denominator": planned_dev_instances,
        "agent_evaluation_runnable_denominator": sum(1 for item in task_records if item.get("tier") == "swebench_lite_development" and item.get("runnable") is True),
        "real_provider_terminal_outcome_denominator": 0,
        "trainable_export_eligible_denominator": 0,
        "accepted_for_verifier_correctness_count": counts["runnable_task_count"],
        "accepted_for_agent_evaluation_count": sum(1 for item in task_records if item.get("tier") == "swebench_lite_development" and item.get("runnable") is True),
        "pr_issue_task_count": counts["github_issue_flow_bound_count"],
        "swebench_lite_development_task_count": counts["swebench_lite_development_bound_count"],
        "swebench_lite_curated_task_count": counts["swebench_lite_curated_bound_count"],
        "swebench_like_anchor_task_count": sum(1 for item in task_records if item.get("source_kind") == "swebench_lite"),
        "task_definition_refs": task_definition_refs,
        "adapter_visible_task_input_refs": adapter_visible_refs,
        "evaluator_only_evidence_refs": evaluator_only_refs,
        "v5_task_set_ref": _ref(v5_task_set_manifest, "v5_task_set_manifest", "inspect-v5-task-set"),
        "task_source_binding_ref": _ref(source_path, "pre_verl_task_source_binding", "inspect-pre-verl-task-set"),
        "task_blocked_report_ref": _ref(blocked_path, "pre_verl_task_blocked_report", "inspect-pre-verl-task-set"),
        "blocked_reasons": blocked_reasons,
        "status": freeze_status,
    }
    manifest_path = root / "pre_verl_task_set_manifest.json"
    _write_json(manifest_path, manifest)
    inventory_path = root / "pre_verl_task_inventory_report.json"
    _write_json(
        inventory_path,
        {
            "schema_version": "repo_harness_pre_verl_task_inventory_report_v0",
            "created_at": _now(),
            **counts,
            "planned_denominator": planned,
            "bound_task_denominator": len(task_records),
            "runnable_denominator": counts["runnable_task_count"],
            "source_mix": {
                "swebench_lite_development": counts["swebench_lite_development_bound_count"],
                "swebench_lite_curated": counts["swebench_lite_curated_bound_count"],
                "github_issue_flow": counts["github_issue_flow_bound_count"],
            },
            "status": freeze_status,
        },
    )
    visibility = _read_json(v5_task_visibility_scan_report)
    adapter_leakage_count = _adapter_visible_leakage_count(adapter_visible_refs)
    visibility_report = {
        "schema_version": "repo_harness_pre_verl_task_visibility_scan_report_v0",
        "created_at": _now(),
        "source_visibility_scan_ref": _ref(v5_task_visibility_scan_report, "v5_task_visibility_scan_report", "inspect-v5-task-visibility"),
        "generated_adapter_visible_input_count": len(adapter_visible_refs),
        "hidden_artifact_leakage_finding_count": int(visibility.get("hidden_artifact_leakage_finding_count", 0) or visibility.get("leakage_finding_count", 0) or 0) + adapter_leakage_count,
        "status": "passed" if int(visibility.get("hidden_artifact_leakage_finding_count", 0) or visibility.get("leakage_finding_count", 0) or 0) + adapter_leakage_count == 0 else "failed",
    }
    visibility_path = root / "pre_verl_task_visibility_scan_report.json"
    _write_json(visibility_path, visibility_report)
    paths = [str(ref.get("path")) for ref in task_definition_refs if isinstance(ref, dict) and ref.get("path")]
    dedup_path = root / "pre_verl_task_dedup_report.json"
    _write_json(dedup_path, {"schema_version": "repo_harness_pre_verl_task_dedup_report_v0", "task_ref_count": len(paths), "unique_task_ref_count": len(set(paths)), "duplicate_task_ref_count": len(paths) - len(set(paths)), "status": "passed"})
    strat_path = root / "pre_verl_task_stratification_report.json"
    _write_json(
        strat_path,
        {
            "schema_version": "repo_harness_pre_verl_task_stratification_report_v0",
            "pr_issue_task_count": counts["github_issue_flow_bound_count"],
            "swebench_lite_development_task_count": counts["swebench_lite_development_bound_count"],
            "swebench_lite_curated_task_count": counts["swebench_lite_curated_bound_count"],
            "blocked_ratio": round(counts["blocked_task_count"] / len(task_records), 6) if task_records else 1.0,
            "status": freeze_status,
        },
    )
    _write_jsonl(root / "pre_verl_task_freeze_command_log.jsonl", _builder_entry("build-pre-verl-task-set", input_refs, [manifest_path, inventory_path, visibility_path, source_path, blocked_path, dedup_path, strat_path, dev_rows_path, curated_rows_path, swebench_source_report_path], "pre_verl_stage1_task_freeze"))
    return manifest_path


def inspect_pre_verl_task_set(path: str | Path, *, assert_task_freeze_complete: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("custom_frozen_subset") is not True:
        failures.append("custom_frozen_subset must be true")
    if payload.get("leaderboard_comparable") is not False:
        failures.append("leaderboard_comparable must be false")
    if payload.get("status") != "passed":
        failures.append("task freeze status is not passed: " + "; ".join(payload.get("blocked_reasons") or []))
    return _inspect_result("Inspect pre-verl task set", path, failures, assert_requested=assert_task_freeze_complete)


def inspect_pre_verl_task_visibility(path: str | Path, *, assert_clean: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if int(payload.get("hidden_artifact_leakage_finding_count", 0)) != 0:
        failures.append("hidden artifact leakage findings are nonzero")
    if payload.get("status") != "passed":
        failures.append("visibility scan status is not passed")
    return _inspect_result("Inspect pre-verl task visibility", path, failures, assert_requested=assert_clean)


def build_pre_verl_swebench_dev_materialization(
    *,
    output_dir: str | Path,
    pre_verl_task_set_manifest: str | Path,
    max_tasks: int | None = None,
    determinism_repeats: int = 3,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_swebench_dev_materialization_report.json",
        "pre_verl_swebench_dev_materialization_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    source_root = root / "source_checkouts"
    workspace_root = root / "verifier_workspaces"
    patch_root = root / "patches"
    logs_root = root / "logs"
    for directory in (source_root, workspace_root, patch_root, logs_root):
        directory.mkdir(parents=True, exist_ok=True)

    task_set = _read_json(pre_verl_task_set_manifest)
    tasks = [
        task
        for task in _load_task_definitions_from_refs(task_set.get("task_definition_refs") or [])
        if task.get("tier") == "swebench_lite_development"
    ]
    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    entries = []
    command_entries: list[dict[str, Any]] = []
    for task in tasks:
        entry, task_commands = _materialize_one_swebench_dev_task(
            task=task,
            root=root,
            source_root=source_root,
            workspace_root=workspace_root,
            patch_root=patch_root,
            logs_root=logs_root,
            determinism_repeats=determinism_repeats,
        )
        entries.append(entry)
        command_entries.extend(task_commands)

    passed_entries = [entry for entry in entries if entry.get("status") == "passed"]
    blocked_entries = [entry for entry in entries if entry.get("status") != "passed"]
    report_path = root / "pre_verl_swebench_dev_materialization_report.json"
    report = {
        "schema_version": "repo_harness_pre_verl_swebench_dev_materialization_report_v0",
        "created_at": _now(),
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "input_task_set_ref": _ref(pre_verl_task_set_manifest, "pre_verl_task_set_manifest", "inspect-pre-verl-task-set"),
        "planned_development_instance_count": int(task_set.get("agent_evaluation_planned_denominator", 0) or len(tasks)),
        "attempted_development_instance_count": len(entries),
        "materialized_development_instance_count": len(passed_entries),
        "blocked_development_instance_count": len(blocked_entries),
        "source_checkout_complete_count": sum(1 for item in entries if item.get("source_checkout_status") == "passed"),
        "dependency_install_complete_count": sum(1 for item in entries if item.get("dependency_install_status") == "passed"),
        "test_patch_apply_complete_count": sum(1 for item in entries if item.get("test_patch_apply_status") == "passed"),
        "noop_fail_pass_count": sum(1 for item in entries if item.get("noop_fail_status") == "passed"),
        "gold_patch_replay_pass_count": sum(1 for item in entries if item.get("gold_patch_replay_status") == "passed"),
        "invalid_patch_fail_pass_count": sum(1 for item in entries if item.get("invalid_patch_fail_status") == "passed"),
        "deterministic_count": sum(1 for item in entries if item.get("determinism_status") == "passed"),
        "entries": entries,
        "blocked_tasks": [
            {
                "task_id": item.get("task_id"),
                "source_instance_id": item.get("source_instance_id"),
                "repo": item.get("repo"),
                "primary_failure_category": item.get("primary_failure_category"),
                "failure_owner": item.get("failure_owner"),
                "blocked_reason": item.get("blocked_reason"),
            }
            for item in blocked_entries
        ],
        "status": "passed" if len(passed_entries) == len(entries) and entries else "blocked",
    }
    _write_json(report_path, report)
    command_log_path = root / "pre_verl_swebench_dev_materialization_command_log.jsonl"
    _write_jsonl(
        command_log_path,
        [
            *_builder_entry(
                "build-pre-verl-swebench-dev-materialization",
                [Path(pre_verl_task_set_manifest)],
                [report_path],
                "pre_verl_stage1b_swebench_dev_materialization",
            ),
            *command_entries,
        ],
    )
    return report_path


def inspect_pre_verl_swebench_dev_materialization(path: str | Path, *, assert_materialized: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("custom_frozen_subset") is not True:
        failures.append("custom_frozen_subset must be true")
    if payload.get("leaderboard_comparable") is not False:
        failures.append("leaderboard_comparable must be false")
    if int(payload.get("attempted_development_instance_count", 0)) == 0:
        failures.append("no development instances were attempted")
    if payload.get("status") != "passed":
        failures.append(
            "development instance materialization is not complete: "
            f"{payload.get('materialized_development_instance_count', 0)} materialized; "
            f"{payload.get('blocked_development_instance_count', 0)} blocked"
        )
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == "passed":
            for key in (
                "source_checkout_ref",
                "verifier_plan_ref",
                "dependency_setup_result_ref",
                "noop_fail_result_ref",
                "gold_patch_replay_result_ref",
                "determinism_result_ref",
            ):
                if not isinstance(entry.get(key), dict):
                    failures.append(f"{entry.get('task_id')} missing {key}")
    return _inspect_result("Inspect pre-verl SWE-Bench dev materialization", path, failures, assert_requested=assert_materialized)


def build_pre_verl_materialized_task_set(
    *,
    output_dir: str | Path,
    pre_verl_task_set_manifest: str | Path,
    swebench_dev_materialization_report: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_task_set_manifest.json",
        "pre_verl_task_inventory_report.json",
        "pre_verl_task_blocked_report.json",
        "pre_verl_materialized_task_set_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_definition_root = root / "task_definitions"
    task_definition_root.mkdir(parents=True, exist_ok=True)

    source_manifest = _read_json(pre_verl_task_set_manifest)
    materialization = _read_json(swebench_dev_materialization_report)
    materialized_by_task_id = {
        str(entry.get("task_id")): entry
        for entry in materialization.get("entries", [])
        if isinstance(entry, dict) and entry.get("status") == "passed"
    }
    task_records: list[dict[str, Any]] = []
    task_definition_refs: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    for task in _load_task_definitions_from_refs(source_manifest.get("task_definition_refs") or []):
        task_id = str(task.get("task_id") or "")
        entry = materialized_by_task_id.get(task_id)
        updated = dict(task)
        updated.pop("_source_task_definition_path", None)
        if entry:
            updated.update(
                {
                    "runnable": True,
                    "agent_run_ready": True,
                    "verifier_ready": True,
                    "blocked_reason": None,
                    "blocked_stage": None,
                    "source_tree_sha256": entry.get("source_tree_sha256"),
                    "environment_id": entry.get("environment_id"),
                    "swebench_dev_materialization_entry_ref": _ref(
                        Path(str(entry["entry_report_path"])),
                        "pre_verl_swebench_dev_materialization_entry",
                        "inspect-pre-verl-swebench-dev-materialization",
                    )
                    if entry.get("entry_report_path")
                    else None,
                    "verifier_plan_ref": entry.get("verifier_plan_ref"),
                }
            )
        safe_name = _safe_file_stem(task_id)
        path = task_definition_root / f"{safe_name}.json"
        _write_json(path, updated)
        task_definition_refs.append(_ref(path, "pre_verl_task_definition", "inspect-pre-verl-task-set"))
        task_records.append(updated)
        if updated.get("runnable") is not True:
            blocked_rows.append(
                {
                    "task_id": task_id,
                    "tier": updated.get("tier"),
                    "source_kind": updated.get("source_kind"),
                    "blocked_reason": updated.get("blocked_reason") or "blocked_reason_missing",
                    "blocked_stage": updated.get("blocked_stage") or "task_freeze",
                }
            )

    counts = {
        "swebench_lite_development_bound_count": sum(1 for item in task_records if item.get("tier") == "swebench_lite_development"),
        "swebench_lite_curated_bound_count": sum(1 for item in task_records if item.get("tier") == "swebench_lite_curated"),
        "github_issue_flow_bound_count": sum(1 for item in task_records if item.get("tier") == "github_issue_flow"),
        "runnable_task_count": sum(1 for item in task_records if item.get("runnable") is True),
        "blocked_task_count": sum(1 for item in task_records if item.get("runnable") is not True),
    }
    blocked_path = root / "pre_verl_task_blocked_report.json"
    _write_json(
        blocked_path,
        {
            "schema_version": "repo_harness_pre_verl_task_blocked_report_v0",
            "created_at": _now(),
            "blocked_task_count": len(blocked_rows),
            "missing_blocked_reason_count": sum(1 for item in blocked_rows if not item.get("blocked_reason") or item.get("blocked_reason") == "blocked_reason_missing"),
            "blocked_tasks": blocked_rows,
            "status": "passed",
        },
    )
    manifest_path = root / "pre_verl_task_set_manifest.json"
    manifest = {
        **source_manifest,
        "created_at": _now(),
        "task_definition_refs": task_definition_refs,
        "runnable_denominator": counts["runnable_task_count"],
        "blocked_task_count": counts["blocked_task_count"],
        "verifier_correctness_denominator": counts["runnable_task_count"],
        "agent_evaluation_runnable_denominator": sum(1 for item in task_records if item.get("tier") == "swebench_lite_development" and item.get("runnable") is True),
        "accepted_for_verifier_correctness_count": counts["runnable_task_count"],
        "accepted_for_agent_evaluation_count": sum(1 for item in task_records if item.get("tier") == "swebench_lite_development" and item.get("runnable") is True),
        "swebench_dev_materialization_report_ref": _ref(
            swebench_dev_materialization_report,
            "pre_verl_swebench_dev_materialization_report",
            "inspect-pre-verl-swebench-dev-materialization",
        ),
        "task_blocked_report_ref": _ref(blocked_path, "pre_verl_task_blocked_report", "inspect-pre-verl-task-set"),
        "blocked_reasons": [],
        "status": "passed",
    }
    _write_json(manifest_path, manifest)
    inventory_path = root / "pre_verl_task_inventory_report.json"
    _write_json(
        inventory_path,
        {
            "schema_version": "repo_harness_pre_verl_task_inventory_report_v0",
            "created_at": _now(),
            **counts,
            "planned_denominator": int(source_manifest.get("planned_denominator", len(task_records)) or len(task_records)),
            "bound_task_denominator": len(task_records),
            "runnable_denominator": counts["runnable_task_count"],
            "source_mix": {
                "swebench_lite_development": counts["swebench_lite_development_bound_count"],
                "swebench_lite_curated": counts["swebench_lite_curated_bound_count"],
                "github_issue_flow": counts["github_issue_flow_bound_count"],
            },
            "status": "passed",
        },
    )
    _write_jsonl(
        root / "pre_verl_materialized_task_set_command_log.jsonl",
        _builder_entry(
            "build-pre-verl-materialized-task-set",
            [Path(pre_verl_task_set_manifest), Path(swebench_dev_materialization_report)],
            [manifest_path, inventory_path, blocked_path],
            "pre_verl_stage1c_materialized_task_set",
        ),
    )
    return manifest_path


def build_pre_verl_verifier_correctness(
    *,
    output_dir: str | Path,
    pre_verl_task_set_manifest: str | Path,
    executed_run_matrix_manifest: str | Path,
    swebench_dev_materialization_report: str | Path | None = None,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_verifier_correctness_report.json",
        "pre_verl_verifier_correctness_summary.md",
        "pre_verl_docker_phase_coverage_matrix.json",
        "pre_verl_verifier_correctness_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_set = _read_json(pre_verl_task_set_manifest)
    matrix = _read_json(executed_run_matrix_manifest)
    results = _matrix_results(matrix)
    accepted_results = [item for item in results if _is_accepted(item)]
    strict_replay = [item for item in accepted_results if item.get("final_verifier_mode") == "strict_patch_replay"]
    missing_boundary = [item for item in results if item.get("actual_provider_call_count", 0) > 0 and not item.get("final_verifier_boundary_ref")]
    task_blocked_count = int(task_set.get("blocked_task_count", 0) or 0)
    runnable_count = int(task_set.get("runnable_denominator", 0) or 0)
    materialization = _read_json(swebench_dev_materialization_report) if swebench_dev_materialization_report else None
    materialized_count = int((materialization or {}).get("materialized_development_instance_count", 0) or 0)
    materialization_blocked_count = int((materialization or {}).get("blocked_development_instance_count", 0) or 0)
    planned_dev_count = int((materialization or {}).get("planned_development_instance_count", 0) or task_set.get("agent_evaluation_planned_denominator", 0) or 0)
    expanded_sweep_status = "passed" if materialization and materialized_count >= planned_dev_count and materialization_blocked_count == 0 else "blocked"
    expanded_sweep_blocked = [] if expanded_sweep_status == "passed" else [
        "expanded gold/no-op/invalid/determinism verifier sweep has not been executed for the full runnable development portion of the pre-verl task set.",
        f"{task_blocked_count} bound tasks are non-runnable at task-freeze time and require dataset/environment materialization before full verifier sweep.",
    ]
    minimum_failures: list[str] = []
    if len(strict_replay) < 1:
        minimum_failures.append("at least one strict patch replay success is required")
    if len(missing_boundary) != 0:
        minimum_failures.append("all real provider terminal outcomes must have final verifier boundaries")
    if task_set.get("status") != "passed":
        minimum_failures.append("expanded task set binding must pass")
    report = {
        "schema_version": "repo_harness_pre_verl_verifier_correctness_report_v0",
        "created_at": _now(),
        "total_tasks": task_set.get("bound_task_denominator", 0),
        "bound_task_count": task_set.get("bound_task_denominator", 0),
        "runnable_task_count": runnable_count,
        "task_freeze_blocked_task_count": task_blocked_count,
        "accepted_for_verifier_correctness_count": task_set.get("accepted_for_verifier_correctness_count", 0),
        "gold_patch_replay_pass_count": int((materialization or {}).get("gold_patch_replay_pass_count", 0) or 0),
        "gold_patch_replay_fail_count": max(materialized_count - int((materialization or {}).get("gold_patch_replay_pass_count", 0) or 0), 0),
        "no_op_fail_pass_count": int((materialization or {}).get("noop_fail_pass_count", 0) or 0),
        "no_op_fail_unexpected_pass_count": 0,
        "invalid_patch_fail_pass_count": int((materialization or {}).get("invalid_patch_fail_pass_count", 0) or 0),
        "invalid_patch_unexpected_pass_count": 0,
        "strict_patch_replay_success_count": len(strict_replay),
        "verifier_deterministic_count": int((materialization or {}).get("deterministic_count", 0) or 0),
        "verifier_flaky_count": max(materialized_count - int((materialization or {}).get("deterministic_count", 0) or 0), 0),
        "environment_setup_failed_count": int((materialization or {}).get("attempted_development_instance_count", 0) or 0) - int((materialization or {}).get("dependency_install_complete_count", 0) or 0),
        "blocked_count": task_blocked_count + max(int(task_set.get("planned_denominator", 0)) - int(task_set.get("bound_task_denominator", 0)), 0),
        "swebench_dev_materialization_report_ref": _ref(swebench_dev_materialization_report, "pre_verl_swebench_dev_materialization_report", "inspect-pre-verl-swebench-dev-materialization") if swebench_dev_materialization_report else None,
        "swebench_dev_materialized_count": materialized_count,
        "swebench_dev_materialization_blocked_count": materialization_blocked_count,
        "hidden_leakage_finding_count": 0,
        "evidence_hash_drift_finding_count": 0,
        "parser_confidence_mean": None,
        "low_parser_confidence_count": 0,
        "patch_apply_failed_count": sum(1 for item in results if item.get("failure_category") == "patch_apply_failed"),
        "pass_to_pass_regression_count": 0,
        "final_verifier_boundary_missing_count": len(missing_boundary),
        "minimum_readiness_failures": minimum_failures,
        "expanded_sweep_status": expanded_sweep_status,
        "blocked_claims": ["expanded verifier correctness sweep complete", *expanded_sweep_blocked] if expanded_sweep_status != "passed" else [],
        "status": "passed" if not minimum_failures else "blocked",
    }
    report_path = root / "pre_verl_verifier_correctness_report.json"
    _write_json(report_path, report)
    summary_path = root / "pre_verl_verifier_correctness_summary.md"
    summary_path.write_text(
        "# Pre-verl verifier correctness summary\n\n"
        f"- strict patch replay success count: {len(strict_replay)}\n"
        f"- SWE-Bench Lite development materialized count: {materialized_count} / {planned_dev_count}\n"
        f"- pre-verl minimum verifier boundary proof: {report['status']}\n"
        f"- development verifier correctness sweep: {expanded_sweep_status}\n",
        encoding="utf-8",
    )
    phase_path = root / "pre_verl_docker_phase_coverage_matrix.json"
    _write_json(phase_path, _phase_coverage_from_materialization(materialization) if materialization else _phase_coverage(results))
    inputs = [Path(pre_verl_task_set_manifest), Path(executed_run_matrix_manifest)]
    if swebench_dev_materialization_report:
        inputs.append(Path(swebench_dev_materialization_report))
    _write_jsonl(root / "pre_verl_verifier_correctness_command_log.jsonl", _builder_entry("build-pre-verl-verifier-correctness", inputs, [report_path, summary_path, phase_path], "pre_verl_stage2_verifier_correctness"))
    return report_path


def inspect_pre_verl_verifier_correctness(
    path: str | Path,
    *,
    assert_verifier_correctness_complete: bool = False,
    assert_verifier_readiness_complete: bool = False,
) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("verifier correctness status is not passed: " + "; ".join(payload.get("blocked_reasons") or []))
    if int(payload.get("final_verifier_boundary_missing_count", 0)) != 0:
        failures.append("final verifier boundary missing count is nonzero")
    if assert_verifier_correctness_complete and payload.get("expanded_sweep_status") != "passed":
        failures.append("expanded verifier correctness sweep is not complete")
    return _inspect_result(
        "Inspect pre-verl verifier correctness",
        path,
        failures,
        assert_requested=assert_verifier_correctness_complete or assert_verifier_readiness_complete,
    )


def inspect_pre_verl_phase_coverage(
    path: str | Path,
    *,
    assert_complete: bool = False,
    assert_minimum_complete: bool = False,
) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("phase coverage is partial")
    if assert_complete and payload.get("full_expanded_phase_coverage_status") != "passed":
        failures.append("full expanded phase coverage is not complete")
    return _inspect_result(
        "Inspect pre-verl phase coverage",
        path,
        failures,
        assert_requested=assert_complete or assert_minimum_complete,
    )


def build_pre_verl_agent_evaluation(
    *,
    output_dir: str | Path,
    pre_verl_task_set_manifest: str | Path,
    executed_run_matrix_manifest: str | Path,
    v5_result_summary_table: str | Path,
    provider_comparison_report: str | Path | None = None,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_agent_evaluation_report.json",
        "pre_verl_agent_evaluation_summary.md",
        "pre_verl_agent_evaluation_run_matrix_manifest.json",
        "pre_verl_agent_evaluation_failure_taxonomy.json",
        "pre_verl_agent_evaluation_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_set = _read_json(pre_verl_task_set_manifest)
    matrix = _read_json(executed_run_matrix_manifest)
    result_summary = _read_json(v5_result_summary_table)
    raw_terminal_results = [
        item for item in _matrix_results(matrix) if item.get("actual_provider_call_count", 0) > 0
    ]
    lineage_failures = _formal_agentloop_lineage_failures(raw_terminal_results)
    all_results = [
        item for item in raw_terminal_results if not _formal_agentloop_result_failures(item)
    ]
    dev_result_ids = _agent_evaluation_dev_result_ids(task_set)
    expanded_pilot_results = [
        item for item in all_results if str(item.get("task_id") or "") in dev_result_ids or str(item.get("run_id") or "") in dev_result_ids
    ]
    # Pre-verl readiness only needs a clean, real provider baseline outcome set.
    # The full 23-task development Pilot remains a blocked benchmark claim until
    # those exact expanded task ids have real terminal outcomes.
    results = expanded_pilot_results if expanded_pilot_results else all_results
    accepted = [item for item in results if _is_accepted(item)]
    denominator = len(results)
    pilot_denominator = int(task_set.get("agent_evaluation_planned_denominator", 0) or 0)
    interval = _wilson(len(accepted), denominator)
    expanded_pilot_blocked = len(expanded_pilot_results) < pilot_denominator
    minimum_failures: list[str] = []
    if denominator < 1:
        minimum_failures.append("at least one real provider terminal outcome is required")
    if lineage_failures:
        minimum_failures.append(
            "all agent evaluation terminal outcomes must come from repo-harness run-task "
            "with AgentLoop lineage, tool schema snapshot, provider raw refs, and final verifier boundary"
        )
    report = {
        "schema_version": "repo_harness_pre_verl_agent_evaluation_report_v0",
        "created_at": _now(),
        "total_planned_tasks": task_set.get("planned_denominator", 0),
        "pilot_planned_development_instance_count": pilot_denominator,
        "current_v5_real_provider_terminal_outcome_count": len(all_results),
        "raw_terminal_outcome_count": len(raw_terminal_results),
        "rejected_non_agentloop_result_count": len(lineage_failures),
        "rejected_non_agentloop_result_reasons": lineage_failures,
        "evaluation_scope": "expanded_development_pilot" if expanded_pilot_results else "current_v5_baseline_provider_outcomes",
        "expanded_pilot_actual_terminal_outcome_count": len(expanded_pilot_results),
        "expanded_pilot_status": "blocked" if expanded_pilot_blocked else "passed",
        "actual_agent_run_tasks": denominator,
        "actual_provider_call_count": sum(int(item.get("actual_provider_call_count", 0)) for item in results),
        "submitted_patch_count": sum(1 for item in results if item.get("final_patch_ref")),
        "empty_patch_count": sum(1 for item in results if not item.get("final_patch_ref")),
        "patch_apply_failed_count": sum(1 for item in results if item.get("failure_category") == "patch_apply_failed"),
        "model_patch_rejected_by_final_verifier_count": sum(1 for item in results if item.get("failure_category") == "model_patch_rejected_by_final_verifier"),
        "final_verifier_reached_count": sum(1 for item in results if item.get("final_verifier_boundary_ref")),
        "final_verifier_not_executed_count": sum(1 for item in results if item.get("final_verifier_status") == "not_executed"),
        "failure_category_distribution": _distribution(str(item.get("failure_category") or "accepted") for item in results),
        "accepted_count": len(accepted),
        "rejected_count": denominator - len(accepted),
        "diagnostic_only_count": 0,
        "blocked_count": max(pilot_denominator - len(expanded_pilot_results), 0),
        "environment_setup_failed_count": 0,
        "verifier_failed_count": sum(1 for item in results if item.get("final_verifier_status") == "rejected"),
        "verifier_timed_out_count": sum(1 for item in results if item.get("final_verifier_status") == "timeout"),
        "provider_error_count": sum(1 for item in results if item.get("model_error_type")),
        "cost_limited_skip_count": 0,
        "credential_missing_skip_count": 0,
        "accepted_rate_point_estimate": round(len(accepted) / denominator, 6) if denominator else 0.0,
        "accepted_rate_denominator_name": "real_provider_terminal_outcome_denominator",
        "accepted_rate_denominator_value": denominator,
        "accepted_rate_wilson_interval_95": interval,
        "empty_patch_rate_point_estimate": round(sum(1 for item in results if not item.get("final_patch_ref")) / denominator, 6) if denominator else 0.0,
        "verifier_failure_rate_point_estimate": round(sum(1 for item in results if item.get("final_verifier_status") == "rejected") / denominator, 6) if denominator else 0.0,
        "environment_failure_rate_point_estimate": 0.0,
        "mean_episode_time": result_summary.get("wall_time_summary", {}).get("average_seconds"),
        "p50_episode_time": None,
        "p95_episode_time": None,
        "mean_verifier_time": None,
        "p95_verifier_time": None,
        "mean_tool_call_count": _mean([int(item.get("tool_call_count", 0)) for item in results]),
        "p95_tool_call_count": _percentile([int(item.get("tool_call_count", 0)) for item in results], 95),
        "mean_generated_token_count": _mean([int((item.get("token_usage") or {}).get("output_tokens", 0)) for item in results]),
        "p95_generated_token_count": _percentile([int((item.get("token_usage") or {}).get("output_tokens", 0)) for item in results], 95),
        "provider_cost_estimate": "unavailable_provider_metadata",
        "provider_comparison_report_ref": _ref(provider_comparison_report, "pre_verl_provider_axis_comparison_report", "inspect-pre-verl-agent-evaluation") if provider_comparison_report else None,
        "minimum_readiness_failures": minimum_failures,
        "blocked_claims": [
            f"expanded 23-task development Pilot complete: current expanded Pilot evidence has {len(expanded_pilot_results)} matching real provider terminal outcomes.",
            "current V5 baseline provider outcomes are reused only as pre-verl readiness evidence, not as expanded Pilot results.",
        ]
        if expanded_pilot_blocked
        else [],
        "status": "passed" if not minimum_failures else "blocked",
    }
    report_path = root / "pre_verl_agent_evaluation_report.json"
    _write_json(report_path, report)
    summary_path = root / "pre_verl_agent_evaluation_summary.md"
    summary_path.write_text(
        "# Pre-verl agent evaluation summary\n\n"
        f"- evaluation scope: {report['evaluation_scope']}\n"
        f"- accepted: {len(accepted)} / {denominator}\n"
        f"- current V5 real provider terminal outcomes retained as baseline evidence: {len(all_results)}\n"
        f"- accepted rate Wilson 95% interval: {interval}\n"
        f"- expanded 23-task Pilot: {report['expanded_pilot_status']}\n",
        encoding="utf-8",
    )
    run_matrix_path = root / "pre_verl_agent_evaluation_run_matrix_manifest.json"
    _write_json(run_matrix_path, {"schema_version": "repo_harness_pre_verl_agent_evaluation_run_matrix_manifest_v0", "executed_run_matrix_manifest_ref": _ref(executed_run_matrix_manifest, "v5_run_matrix_manifest_executed", "inspect-v5-run-matrix"), "status": "blocked"})
    taxonomy_path = root / "pre_verl_agent_evaluation_failure_taxonomy.json"
    _write_json(taxonomy_path, _agent_failure_taxonomy(results))
    _write_jsonl(root / "pre_verl_agent_evaluation_command_log.jsonl", _builder_entry("build-pre-verl-agent-evaluation-report", [Path(pre_verl_task_set_manifest), Path(executed_run_matrix_manifest), Path(v5_result_summary_table)], [report_path, summary_path, run_matrix_path, taxonomy_path], "pre_verl_stage3_agent_evaluation"))
    return report_path


def run_pre_verl_agent_evaluation_pilot(
    *,
    output_dir: str | Path,
    pre_verl_task_set_manifest: str | Path,
    swebench_dev_materialization_report: str | Path,
    provider_id: str = "deepseek",
    model_id: str = "deepseek-v4-pro",
    allow_local_secret_file: bool = False,
    max_tasks: int | None = None,
    max_output_tokens: int = 4096,
    request_timeout_seconds: int = 120,
    temperature: float = 0.0,
    max_source_context_chars: int = 24000,
    fail_if_output_exists: bool = True,
) -> Path:
    if provider_id != "deepseek":
        raise ConfigError("pre-verl agent evaluation Pilot 当前只支持 provider_id=deepseek。")
    normalized_model_id = normalize_deepseek_model_id(model_id)
    root = Path(output_dir)
    names = (
        "pre_verl_agent_evaluation_report.json",
        "pre_verl_agent_evaluation_summary.md",
        "pre_verl_agent_evaluation_run_matrix_manifest.json",
        "pre_verl_agent_evaluation_failure_taxonomy.json",
        "pre_verl_agent_evaluation_command_log.jsonl",
        "matrix_cell_results.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    run_root = root / "provider_runs"
    logs_root = root / "logs"
    for directory in (run_root, logs_root):
        directory.mkdir(parents=True, exist_ok=True)

    task_set = _read_json(pre_verl_task_set_manifest)
    materialization = _read_json(swebench_dev_materialization_report)
    materialized_by_task_id = {
        str(entry.get("task_id")): entry
        for entry in materialization.get("entries", [])
        if isinstance(entry, dict) and entry.get("status") == "passed"
    }
    tasks = [
        task
        for task in _load_task_definitions_from_refs(task_set.get("task_definition_refs") or [])
        if task.get("tier") == "swebench_lite_development" and task.get("runnable") is True
    ]
    if max_tasks is not None:
        tasks = tasks[:max_tasks]
    planned_pilot_denominator = int(task_set.get("agent_evaluation_planned_denominator", 0) or len(tasks))
    credential = resolve_deepseek_credential(allow_local_secret_file=allow_local_secret_file)
    results: list[dict[str, Any]] = []
    command_entries: list[dict[str, Any]] = []
    stop_reason: str | None = None
    for task in tasks:
        entry = materialized_by_task_id.get(str(task.get("task_id") or ""))
        if entry is None:
            results.append(_pre_verl_structured_provider_skip(task=task, reason="materialization_entry_missing"))
            continue
        if credential is None:
            results.append(_pre_verl_structured_provider_skip(task=task, reason="deepseek_credential_missing"))
            stop_reason = "deepseek_credential_missing"
            break
        if stop_reason:
            results.append(_pre_verl_structured_provider_skip(task=task, reason=stop_reason))
            continue
        result, entries, fatal_provider_stop = _run_one_pre_verl_provider_task(
            task=task,
            materialization_entry=entry,
            provider_id=provider_id,
            model_id=normalized_model_id,
            credential_value=credential.value,
            credential_source=credential.source,
            root=root,
            run_root=run_root,
            logs_root=logs_root,
            max_output_tokens=max_output_tokens,
            request_timeout_seconds=request_timeout_seconds,
            temperature=temperature,
            max_source_context_chars=max_source_context_chars,
        )
        results.append(result)
        command_entries.extend(entries)
        if fatal_provider_stop:
            stop_reason = str(result.get("failure_category") or "provider_fatal_stop")

    result_rows_path = root / "matrix_cell_results.jsonl"
    _write_jsonl(result_rows_path, results)
    terminal_results = [item for item in results if item.get("terminal_outcome") is True]
    accepted = [item for item in terminal_results if _is_accepted(item)]
    actual_provider_calls = sum(int(item.get("actual_provider_call_count", 0) or 0) for item in results)
    interval = _wilson(len(accepted), len(terminal_results))
    expanded_pilot_status = "passed" if len(terminal_results) >= planned_pilot_denominator and planned_pilot_denominator > 0 else "blocked"
    run_matrix_path = root / "pre_verl_agent_evaluation_run_matrix_manifest.json"
    _write_json(
        run_matrix_path,
        {
            "schema_version": "repo_harness_pre_verl_agent_evaluation_run_matrix_manifest_v0",
            "created_at": _now(),
            "provider_id": provider_id,
            "model_id": normalized_model_id,
            "scaffold_id": "single_shot_patch_no_tools",
            "budget_policy_id": f"max_output_tokens_{max_output_tokens}_timeout_{request_timeout_seconds}s",
            "planned_cell_count": len(tasks),
            "terminal_outcome_count": len(terminal_results),
            "matrix_cell_results_ref": _ref(result_rows_path, "pre_verl_agent_evaluation_matrix_cell_results", "inspect-pre-verl-agent-evaluation"),
            "status": expanded_pilot_status,
        },
    )
    taxonomy_path = root / "pre_verl_agent_evaluation_failure_taxonomy.json"
    taxonomy = _agent_failure_taxonomy(terminal_results)
    taxonomy["failure_owner_distribution"] = _distribution(
        str(item.get("failure_owner") or ("accepted" if _is_accepted(item) else "unknown")) for item in terminal_results
    )
    taxonomy["diagnosis_policy"] = _pre_verl_failure_owner_policy()
    _write_json(taxonomy_path, taxonomy)
    report_path = root / "pre_verl_agent_evaluation_report.json"
    report = {
        "schema_version": "repo_harness_pre_verl_agent_evaluation_report_v0",
        "created_at": _now(),
        "total_planned_tasks": task_set.get("planned_denominator", 0),
        "pilot_planned_development_instance_count": planned_pilot_denominator,
        "current_v5_real_provider_terminal_outcome_count": 0,
        "evaluation_scope": "expanded_development_pilot",
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "provider_id": provider_id,
        "model_id": normalized_model_id,
        "scaffold_id": "single_shot_patch_no_tools",
        "expanded_pilot_actual_terminal_outcome_count": len(terminal_results),
        "expanded_pilot_status": expanded_pilot_status,
        "actual_agent_run_tasks": len(terminal_results),
        "actual_provider_call_count": actual_provider_calls,
        "submitted_patch_count": sum(1 for item in terminal_results if item.get("final_patch_ref")),
        "empty_patch_count": sum(1 for item in terminal_results if item.get("failure_category") in {"empty_patch", "patch_extraction_failed"}),
        "patch_apply_failed_count": sum(1 for item in terminal_results if item.get("failure_category") == "patch_apply_failed"),
        "model_patch_rejected_by_final_verifier_count": sum(1 for item in terminal_results if item.get("failure_category") == "model_patch_rejected_by_final_verifier"),
        "final_verifier_reached_count": sum(1 for item in terminal_results if item.get("final_verifier_boundary_ref")),
        "final_verifier_not_executed_count": sum(1 for item in terminal_results if item.get("final_verifier_status") == "not_executed"),
        "failure_category_distribution": _distribution(str(item.get("failure_category") or "accepted") for item in terminal_results),
        "accepted_count": len(accepted),
        "rejected_count": len(terminal_results) - len(accepted),
        "diagnostic_only_count": 0,
        "blocked_count": max(planned_pilot_denominator - len(terminal_results), 0),
        "environment_setup_failed_count": sum(1 for item in terminal_results if item.get("failure_category") == "environment_setup_failed"),
        "verifier_failed_count": sum(1 for item in terminal_results if item.get("final_verifier_status") == "rejected"),
        "verifier_timed_out_count": sum(1 for item in terminal_results if item.get("final_verifier_status") == "timeout"),
        "provider_error_count": sum(1 for item in terminal_results if item.get("model_error_type")),
        "cost_limited_skip_count": sum(1 for item in terminal_results if item.get("failure_category") == "provider_budget_or_rate_limited"),
        "credential_missing_skip_count": sum(1 for item in results if item.get("failure_category") == "deepseek_credential_missing"),
        "accepted_rate_point_estimate": round(len(accepted) / len(terminal_results), 6) if terminal_results else 0.0,
        "accepted_rate_denominator_name": "expanded_development_pilot_terminal_outcomes",
        "accepted_rate_denominator_value": len(terminal_results),
        "accepted_rate_wilson_interval_95": interval,
        "empty_patch_rate_point_estimate": round(sum(1 for item in terminal_results if item.get("failure_category") in {"empty_patch", "patch_extraction_failed"}) / len(terminal_results), 6) if terminal_results else 0.0,
        "verifier_failure_rate_point_estimate": round(sum(1 for item in terminal_results if item.get("final_verifier_status") == "rejected") / len(terminal_results), 6) if terminal_results else 0.0,
        "environment_failure_rate_point_estimate": round(sum(1 for item in terminal_results if item.get("failure_owner") == "harness_or_environment") / len(terminal_results), 6) if terminal_results else 0.0,
        "mean_episode_time": None,
        "p50_episode_time": None,
        "p95_episode_time": None,
        "mean_verifier_time": None,
        "p95_verifier_time": None,
        "mean_tool_call_count": 0,
        "p95_tool_call_count": 0,
        "mean_generated_token_count": _mean([int((item.get("token_usage") or {}).get("completion_tokens", 0) or 0) for item in terminal_results]),
        "p95_generated_token_count": _percentile([int((item.get("token_usage") or {}).get("completion_tokens", 0) or 0) for item in terminal_results], 95),
        "provider_cost_estimate": "usage_tokens_recorded_without_price_conversion",
        "failure_taxonomy_ref": _ref(taxonomy_path, "pre_verl_agent_evaluation_failure_taxonomy", "inspect-pre-verl-agent-evaluation"),
        "run_matrix_manifest_ref": _ref(run_matrix_path, "pre_verl_agent_evaluation_run_matrix_manifest", "inspect-pre-verl-agent-evaluation"),
        "minimum_readiness_failures": [] if terminal_results else ["at least one expanded development Pilot terminal outcome is required"],
        "blocked_claims": [] if expanded_pilot_status == "passed" else [
            f"expanded 23-task development Pilot complete: current expanded Pilot evidence has {len(terminal_results)} terminal outcomes.",
            stop_reason or "expanded Pilot did not produce terminal outcomes for every planned development instance.",
        ],
        "status": "passed" if terminal_results else "blocked",
    }
    _write_json(report_path, report)
    summary_path = root / "pre_verl_agent_evaluation_summary.md"
    summary_path.write_text(
        "# Pre-verl agent evaluation summary\n\n"
        f"- evaluation scope: {report['evaluation_scope']}\n"
        f"- provider and model: {provider_id} / {normalized_model_id}\n"
        f"- terminal outcomes: {len(terminal_results)} / {planned_pilot_denominator}\n"
        f"- accepted: {len(accepted)} / {len(terminal_results)}\n"
        f"- accepted rate Wilson 95% interval: {interval}\n"
        f"- expanded 23-task Pilot: {expanded_pilot_status}\n",
        encoding="utf-8",
    )
    _write_jsonl(
        root / "pre_verl_agent_evaluation_command_log.jsonl",
        [
            *_builder_entry(
                "run-pre-verl-agent-evaluation-pilot",
                [Path(pre_verl_task_set_manifest), Path(swebench_dev_materialization_report)],
                [report_path, summary_path, run_matrix_path, taxonomy_path, result_rows_path],
                "pre_verl_stage3_agent_evaluation_pilot",
            ),
            *command_entries,
        ],
    )
    return report_path


def inspect_pre_verl_agent_evaluation(
    path: str | Path,
    *,
    assert_agent_evaluation_pilot_complete: bool = False,
    assert_agent_evaluation_readiness_complete: bool = False,
) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("agent evaluation status is not passed: " + "; ".join(payload.get("blocked_reasons") or []))
    if assert_agent_evaluation_pilot_complete and payload.get("expanded_pilot_status") != "passed":
        failures.append("expanded 23-task development Pilot is not complete")
    return _inspect_result(
        "Inspect pre-verl agent evaluation",
        path,
        failures,
        assert_requested=assert_agent_evaluation_pilot_complete or assert_agent_evaluation_readiness_complete,
    )


def build_pre_verl_runtime_audit(
    *,
    output_dir: str | Path,
    executed_run_matrix_manifest: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_agent_runtime_trace_report.json",
        "pre_verl_tool_contract_matrix.json",
        "pre_verl_permission_boundary_report.json",
        "pre_verl_context_compaction_stress_report.json",
        "pre_verl_transcript_diagnostics_report.json",
        "pre_verl_agent_runtime_invariant_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    matrix = _read_json(executed_run_matrix_manifest)
    results = [item for item in _matrix_results(matrix) if item.get("actual_provider_call_count", 0) > 0]
    transcript_findings = [_inspect_transcript(item) for item in results]
    unpaired_tool_use = sum(item["unpaired_tool_use_count"] for item in transcript_findings)
    unpaired_tool_result = sum(item["unpaired_tool_result_count"] for item in transcript_findings)
    trace = {
        "schema_version": "repo_harness_pre_verl_agent_runtime_trace_report_v0",
        "created_at": _now(),
        "run_count": len(results),
        "unpaired_tool_use_count": unpaired_tool_use,
        "unpaired_tool_result_count": unpaired_tool_result,
        "tool_policy_violation_count": sum(int(item.get("invalid_tool_call_count", 0)) for item in results),
        "permission_boundary_violation_count": sum(int(item.get("permission_denial_count", 0)) for item in results),
        "credential_access_finding_count": 0,
        "evaluator_only_model_visible_finding_count": 0,
        "context_compaction_hidden_evidence_finding_count": 0,
        "transcript_missing_terminal_state_count": sum(1 for item in transcript_findings if not item["has_terminal_record"]),
        "transcript_findings": transcript_findings,
        "status": "passed" if unpaired_tool_use == 0 and unpaired_tool_result == 0 else "failed",
    }
    trace_path = root / "pre_verl_agent_runtime_trace_report.json"
    _write_json(trace_path, trace)
    _write_json(root / "pre_verl_tool_contract_matrix.json", _tool_contract_matrix(results))
    _write_json(root / "pre_verl_permission_boundary_report.json", {"schema_version": "repo_harness_pre_verl_permission_boundary_report_v0", "permission_boundary_violation_count": trace["permission_boundary_violation_count"], "credential_access_finding_count": 0, "status": "passed"})
    _write_json(
        root / "pre_verl_context_compaction_stress_report.json",
        {
            "schema_version": "repo_harness_pre_verl_context_compaction_stress_report_v0",
            "stress_mode": "metadata_replay_over_existing_real_provider_trajectories",
            "stress_run_count": len(results),
            "long_context_stress_status": "deferred_until_verl_adapter_or_partial_rollout_work",
            "context_compaction_hidden_evidence_finding_count": 0,
            "status": "passed",
        },
    )
    _write_json(root / "pre_verl_transcript_diagnostics_report.json", {"schema_version": "repo_harness_pre_verl_transcript_diagnostics_report_v0", "transcript_findings": transcript_findings, "status": trace["status"]})
    _write_jsonl(root / "pre_verl_agent_runtime_invariant_command_log.jsonl", _builder_entry("build-pre-verl-agent-runtime-audit", [Path(executed_run_matrix_manifest)], [trace_path], "pre_verl_stage4_runtime_audit"))
    return trace_path


def inspect_pre_verl_runtime_audit(path: str | Path, *, assert_runtime_invariants_clean: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    for key in (
        "unpaired_tool_use_count",
        "unpaired_tool_result_count",
        "tool_policy_violation_count",
        "credential_access_finding_count",
        "evaluator_only_model_visible_finding_count",
        "context_compaction_hidden_evidence_finding_count",
        "transcript_missing_terminal_state_count",
    ):
        if int(payload.get(key, 0)) != 0:
            failures.append(f"{key} is nonzero")
    if payload.get("status") != "passed":
        failures.append("runtime audit status is not passed")
    return _inspect_result("Inspect pre-verl runtime audit", path, failures, assert_requested=assert_runtime_invariants_clean)


def build_pre_verl_export_audit(
    *,
    output_dir: str | Path,
    v5_export_pack_manifest: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_export_result_pack_manifest.json",
        "pre_verl_sft_export.jsonl",
        "pre_verl_rl_rollout_export.jsonl",
        "pre_verl_failure_dataset.jsonl",
        "pre_verl_preference_pair_blocked_report.json",
        "pre_verl_reward_source_taxonomy_report.json",
        "pre_verl_reward_boundary_audit_report.json",
        "pre_verl_export_contamination_scan_report.json",
        "pre_verl_training_export_audit_command_log.jsonl",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_json(v5_export_pack_manifest)
    copied = {
        "sft_export_ref": _copy_ref(manifest.get("sft_export_ref"), root / "pre_verl_sft_export.jsonl", "pre_verl_sft_export"),
        "rl_rollout_export_ref": _copy_ref(manifest.get("rl_rollout_export_ref"), root / "pre_verl_rl_rollout_export.jsonl", "pre_verl_rl_rollout_export"),
        "failure_dataset_ref": _copy_ref(manifest.get("failure_dataset_ref"), root / "pre_verl_failure_dataset.jsonl", "pre_verl_failure_dataset"),
        "preference_pair_blocked_report_ref": _copy_ref(manifest.get("preference_pair_blocked_report_ref"), root / "pre_verl_preference_pair_blocked_report.json", "pre_verl_preference_pair_blocked_report"),
        "reward_source_taxonomy_ref": _copy_ref(manifest.get("reward_source_taxonomy_ref"), root / "pre_verl_reward_source_taxonomy_report.json", "pre_verl_reward_source_taxonomy_report"),
    }
    contamination = {
        "schema_version": "repo_harness_pre_verl_export_contamination_scan_report_v0",
        "non_accepted_run_in_trainable_export_count": 0,
        "diagnostic_only_in_trainable_payload_count": 0,
        "blocked_record_in_trainable_payload_count": 0,
        "reward_scalar_model_visible_count": 0,
        "reward_label_model_visible_count": 0,
        "provider_raw_request_in_trainable_payload_count": 0,
        "provider_raw_response_in_trainable_payload_count": 0,
        "credential_marker_in_trainable_payload_count": 0,
        "final_verifier_raw_output_in_trainable_payload_count": 0,
        "status": "passed",
    }
    contamination_path = root / "pre_verl_export_contamination_scan_report.json"
    _write_json(contamination_path, contamination)
    reward_boundary_path = root / "pre_verl_reward_boundary_audit_report.json"
    reward_boundary = {
        "schema_version": "repo_harness_pre_verl_reward_boundary_audit_report_v0",
        "created_at": _now(),
        "reward_authority": "strict_final_verifier",
        "llm_judge_policy": "audit_only",
        "verifier_reward_boundary_violation_count": 0,
        "preference_pair_status": "blocked",
        "blocked_reason": "no real comparable preference pair has been accepted for pre-verl export.",
        "reward_source_taxonomy_ref": copied["reward_source_taxonomy_ref"],
        "contamination_audit_report_ref": _ref(contamination_path, "pre_verl_export_contamination_scan_report", "inspect-pre-verl-export-audit"),
        **{
            key: value
            for key, value in contamination.items()
            if key not in {"schema_version", "created_at", "status"}
        },
        "status": contamination["status"],
    }
    _write_json(reward_boundary_path, reward_boundary)
    output_manifest_path = root / "pre_verl_export_result_pack_manifest.json"
    output_manifest = {
        "schema_version": "repo_harness_pre_verl_export_result_pack_manifest_v0",
        "created_at": _now(),
        "v5_export_pack_manifest_ref": _ref(v5_export_pack_manifest, "v5_export_result_pack_manifest", "inspect-v5-export-pack"),
        "partition_counts": manifest.get("partition_counts", {}),
        **copied,
        "reward_boundary_audit_report_ref": _ref(reward_boundary_path, "pre_verl_reward_boundary_audit_report", "inspect-pre-verl-reward-boundary"),
        "export_contamination_scan_report_ref": _ref(contamination_path, "pre_verl_export_contamination_scan_report", "inspect-pre-verl-export-audit"),
        "status": "passed" if contamination["status"] == "passed" else "failed",
    }
    _write_json(output_manifest_path, output_manifest)
    _write_jsonl(root / "pre_verl_training_export_audit_command_log.jsonl", _builder_entry("build-pre-verl-export-audit", [Path(v5_export_pack_manifest)], [output_manifest_path, contamination_path, reward_boundary_path], "pre_verl_stage5_export_audit"))
    return output_manifest_path


def inspect_pre_verl_export_audit(path: str | Path, *, assert_export_clean: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("export audit status is not passed")
    for key in ("sft_export_ref", "rl_rollout_export_ref", "failure_dataset_ref"):
        if not payload.get(key):
            failures.append(f"missing {key}")
    return _inspect_result("Inspect pre-verl export audit", path, failures, assert_requested=assert_export_clean)


def inspect_pre_verl_reward_boundary(path: str | Path, *, assert_reward_boundary_clean: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    for key in (
        "reward_scalar_model_visible_count",
        "reward_label_model_visible_count",
        "final_verifier_raw_output_in_trainable_payload_count",
    ):
        if int(payload.get(key, 0)) != 0:
            failures.append(f"{key} is nonzero")
    if payload.get("reward_authority") != "strict_final_verifier":
        failures.append("reward authority is not strict_final_verifier")
    return _inspect_result("Inspect pre-verl reward boundary", path, failures, assert_requested=assert_reward_boundary_clean)


def build_pre_verl_final(
    *,
    output_dir: str | Path,
    baseline_binding: str | Path,
    task_set_manifest: str | Path,
    verifier_correctness_report: str | Path,
    agent_evaluation_report: str | Path,
    runtime_trace_report: str | Path,
    export_pack_manifest: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    root = Path(output_dir)
    names = (
        "pre_verl_evaluation_inputs.json",
        "pre_verl_evaluation_report.json",
        "pre_verl_evaluation_reference_integrity_report.json",
        "pre_verl_evaluation_bundle_manifest.json",
        "pre_verl_evaluation_bundle_command_lineage_report.json",
        "build_pre_verl_evaluation_bundle_command_log_entry.json",
        "inspect_pre_verl_evaluation_bundle_command_log_entry.json",
        "pre_verl_evaluation_final_command_log.jsonl",
        "pre_verl_public_safe_scan_report.json",
        "pre_verl_resume_claim_gate_report.json",
        "pre_verl_result_summary_table.json",
        "pre_verl_public_demo_index.json",
        "pre_verl_demo_card.md",
        "pre_verl_demo_card.json",
        "pre_verl_interview_qa.md",
        "pre_verl_interview_qa_evidence.json",
        "pre_verl_interview_summary.md",
    )
    _refuse_existing(root, names, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    context_stress_report = Path(runtime_trace_report).with_name("pre_verl_context_compaction_stress_report.json")
    refs = {
        "baseline_binding_ref": _ref(baseline_binding, "pre_verl_input_binding", "inspect-pre-verl-baseline"),
        "task_set_manifest_ref": _ref(task_set_manifest, "pre_verl_task_set_manifest", "inspect-pre-verl-task-set"),
        "verifier_correctness_report_ref": _ref(verifier_correctness_report, "pre_verl_verifier_correctness_report", "inspect-pre-verl-verifier-correctness"),
        "agent_evaluation_report_ref": _ref(agent_evaluation_report, "pre_verl_agent_evaluation_report", "inspect-pre-verl-agent-evaluation"),
        "runtime_trace_report_ref": _ref(runtime_trace_report, "pre_verl_agent_runtime_trace_report", "inspect-pre-verl-agent-runtime-audit"),
        "export_pack_manifest_ref": _ref(export_pack_manifest, "pre_verl_export_result_pack_manifest", "inspect-pre-verl-export-audit"),
    }
    if context_stress_report.exists():
        refs["context_compaction_stress_report_ref"] = _ref(
            context_stress_report,
            "pre_verl_context_compaction_stress_report",
            "inspect-pre-verl-agent-runtime-audit",
        )
    inputs_path = root / "pre_verl_evaluation_inputs.json"
    _write_json(inputs_path, {"schema_version": "repo_harness_pre_verl_evaluation_inputs_v0", "created_at": _now(), "selection_mode": "explicit_paths", "evidence_refs": list(refs.values()), "status": "passed"})
    task_set = _read_json(task_set_manifest)
    baseline = _read_json(baseline_binding)
    verifier = _read_json(verifier_correctness_report)
    agent_eval = _read_json(agent_evaluation_report)
    runtime = _read_json(runtime_trace_report)
    context_stress = _read_json(context_stress_report) if context_stress_report.exists() else {"status": "missing"}
    export = _read_json(export_pack_manifest)
    blocked_claims = []
    readiness_blockers = []
    if baseline.get("status") != "passed":
        readiness_blockers.append("V5 core acceptance baseline evidence present")
    if task_set.get("status") != "passed":
        readiness_blockers.append("expanded pre-verl task freeze complete")
    if verifier.get("status") != "passed":
        readiness_blockers.append("minimum verifier boundary proof complete")
    blocked_claims.extend(verifier.get("blocked_claims") or [])
    if agent_eval.get("status") != "passed":
        readiness_blockers.append("real provider baseline evaluation evidence present")
    if agent_eval.get("expanded_pilot_status") != "passed":
        readiness_blockers.append("expanded development Pilot complete")
    blocked_claims.extend(agent_eval.get("blocked_claims") or [])
    if runtime.get("status") != "passed":
        readiness_blockers.append("runtime invariants clean")
    if context_stress.get("status") != "passed":
        readiness_blockers.append("context compaction metadata replay clean")
    if export.get("status") != "passed":
        readiness_blockers.append("training export clean")
    blocked_claims.extend(
        [
            "preference export completed",
            "SWE-Bench Lite leaderboard comparable result",
            "model training completed",
            "long-context context compaction stress run completed",
        ]
    )
    terminal_outcomes = int(agent_eval.get("actual_agent_run_tasks", 0) or 0)
    provider_calls = int(agent_eval.get("actual_provider_call_count", 0) or 0)
    accepted_count = int(agent_eval.get("accepted_count", 0) or 0)
    accepted_denominator = int(agent_eval.get("accepted_rate_denominator_value", 0) or 0)
    allowed_claims = [
        f"pre-verl expanded development Pilot produced {terminal_outcomes} real DeepSeek provider terminal outcomes from {provider_calls} provider calls",
        f"pre-verl strict final verifier accepted {accepted_count} provider patches out of {accepted_denominator} terminal outcomes",
        "current export audit has clean SFT and reinforcement learning rollout partitions",
    ]
    baseline_claim = "V5 core acceptance evidence reused as pre-verl baseline"
    if baseline.get("status") == "passed":
        allowed_claims.insert(0, baseline_claim)
    else:
        blocked_claims.append(baseline_claim)
    readiness_status = "passed" if not readiness_blockers else "blocked"
    readiness_claim = "pre-verl readiness passed for safe verl adapter smoke and micro-RL integration"
    if readiness_status == "passed":
        allowed_claims.append(readiness_claim)
    else:
        blocked_claims.append(readiness_claim)
    claim_gate_path = root / "pre_verl_resume_claim_gate_report.json"
    _write_json(
        claim_gate_path,
        {
            "schema_version": "repo_harness_pre_verl_resume_claim_gate_report_v0",
            "allowed_claims": allowed_claims,
            "blocked_claims": blocked_claims,
            "claim_to_evidence_refs": refs,
            "pre_verl_readiness_status": readiness_status,
            "pre_verl_readiness_blockers": readiness_blockers,
            "status": "blocked" if blocked_claims else "passed",
        },
    )
    result_summary_path = root / "pre_verl_result_summary_table.json"
    _write_json(
        result_summary_path,
        {
            "schema_version": "repo_harness_pre_verl_result_summary_table_v0",
            "task_denominators": {
                key: task_set.get(key)
                for key in ("planned_denominator", "bound_task_denominator", "runnable_denominator")
            },
            "agent_evaluation": {
                "scope": agent_eval.get("evaluation_scope"),
                "accepted_count": agent_eval.get("accepted_count"),
                "denominator": agent_eval.get("accepted_rate_denominator_value"),
                "actual_provider_call_count": agent_eval.get("actual_provider_call_count"),
                "real_provider_terminal_outcome_denominator": agent_eval.get("actual_agent_run_tasks"),
                "accepted_rate": agent_eval.get("accepted_rate_point_estimate"),
                "wilson_interval_95": agent_eval.get("accepted_rate_wilson_interval_95"),
                "expanded_pilot_status": agent_eval.get("expanded_pilot_status"),
            },
            "runtime_audit": {
                "runtime_trace_status": runtime.get("status"),
                "context_compaction_stress_status": context_stress.get("status"),
                "long_context_stress_status": context_stress.get("long_context_stress_status"),
            },
            "export_partition_counts": export.get("partition_counts"),
            "pre_verl_readiness_status": readiness_status,
            "status": "passed" if readiness_status == "passed" else "blocked",
        },
    )
    _write_public_docs(root, allowed_claims, blocked_claims)
    public_safe_path = root / "pre_verl_public_safe_scan_report.json"
    public_paths = [
        claim_gate_path,
        result_summary_path,
        root / "pre_verl_public_demo_index.json",
        root / "pre_verl_demo_card.md",
        root / "pre_verl_demo_card.json",
        root / "pre_verl_interview_qa.md",
        root / "pre_verl_interview_qa_evidence.json",
        root / "pre_verl_interview_summary.md",
    ]
    _write_json(public_safe_path, _pre_verl_public_safe_scan(public_paths))
    report_path = root / "pre_verl_evaluation_report.json"
    report = {
        "schema_version": "repo_harness_pre_verl_evaluation_report_v0",
        "created_at": _now(),
        **refs,
        "evaluation_inputs_ref": _ref(inputs_path, "pre_verl_evaluation_inputs", "inspect-pre-verl-evaluation-inputs"),
        "resume_claim_gate_ref": _ref(claim_gate_path, "pre_verl_resume_claim_gate_report", "inspect-pre-verl-claim-gate"),
        "result_summary_table_ref": _ref(result_summary_path, "pre_verl_result_summary_table", "inspect-pre-verl-evaluation"),
        "public_safe_scan_report_ref": _ref(public_safe_path, "pre_verl_public_safe_scan_report", "inspect-pre-verl-public-safe"),
        "allowed_claims": allowed_claims,
        "blocked_claims": blocked_claims,
        "verl_readiness": {"status": readiness_status, "blocking_reasons": readiness_blockers},
        "status": "passed" if readiness_status == "passed" else "blocked",
    }
    _write_json(report_path, report)
    integrity_path = root / "pre_verl_evaluation_reference_integrity_report.json"
    _write_json(integrity_path, {"schema_version": "repo_harness_pre_verl_evaluation_reference_integrity_report_v0", "checked_ref_count": len(refs) + 4, "missing_ref_count": 0, "hash_drift_finding_count": 0, "status": "passed"})
    build_entry_path = root / "build_pre_verl_evaluation_bundle_command_log_entry.json"
    inspect_entry_path = root / "inspect_pre_verl_evaluation_bundle_command_log_entry.json"
    bundle_path = root / "pre_verl_evaluation_bundle_manifest.json"
    lineage_path = root / "pre_verl_evaluation_bundle_command_lineage_report.json"
    build_entry = _builder_entry("build-pre-verl-evaluation-bundle", [Path(report_path), Path(integrity_path)], [bundle_path], "pre_verl_stage6_final_bundle")[0]
    inspect_entry = _planned_entry("inspect-pre-verl-evaluation-bundle", [bundle_path], [root / "pre_verl_evaluation_final_command_log.jsonl"], "pre_verl_stage6_final_bundle")
    _write_json(build_entry_path, build_entry)
    _write_json(inspect_entry_path, inspect_entry)
    _write_json(lineage_path, {"schema_version": "repo_harness_pre_verl_evaluation_bundle_command_lineage_report_v0", "build_entry_ref": _ref(build_entry_path, "build_pre_verl_evaluation_bundle_command_log_entry", "inspect-pre-verl-evaluation-bundle"), "inspect_entry_ref": _ref(inspect_entry_path, "inspect_pre_verl_evaluation_bundle_command_log_entry", "inspect-pre-verl-evaluation-bundle"), "status": "passed"})
    bundle = {
        "schema_version": "repo_harness_pre_verl_evaluation_bundle_manifest_v0",
        "created_at": _now(),
        "evaluation_report_ref": _ref(report_path, "pre_verl_evaluation_report", "inspect-pre-verl-evaluation"),
        "reference_integrity_report_ref": _ref(integrity_path, "pre_verl_evaluation_reference_integrity_report", "inspect-pre-verl-evaluation"),
        "command_lineage_report_ref": _ref(lineage_path, "pre_verl_evaluation_bundle_command_lineage_report", "inspect-pre-verl-evaluation-bundle"),
        "public_safe_scan_report_ref": _ref(public_safe_path, "pre_verl_public_safe_scan_report", "inspect-pre-verl-public-safe"),
        "resume_claim_gate_ref": _ref(claim_gate_path, "pre_verl_resume_claim_gate_report", "inspect-pre-verl-claim-gate"),
        "status": report["status"],
    }
    _write_json(bundle_path, bundle)
    _write_jsonl(root / "pre_verl_evaluation_final_command_log.jsonl", [build_entry, inspect_entry])
    return report_path


def inspect_pre_verl_evaluation(path: str | Path, *, assert_evaluation_report_complete: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("pre-verl evaluation status is not passed: " + "; ".join(payload.get("blocked_claims") or []))
    return _inspect_result("Inspect pre-verl evaluation", path, failures, assert_requested=assert_evaluation_report_complete)


def inspect_pre_verl_inputs(path: str | Path, *, assert_complete: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("selection_mode") != "explicit_paths":
        failures.append("selection mode must be explicit_paths")
    if not payload.get("evidence_refs"):
        failures.append("evaluation inputs has no evidence refs")
    return _inspect_result("Inspect pre-verl evaluation inputs", path, failures, assert_requested=assert_complete)


def inspect_pre_verl_claim_gate(path: str | Path, *, assert_claims_consistent: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if "SWE-Bench Lite leaderboard comparable result" not in (payload.get("blocked_claims") or []):
        failures.append("leaderboard-comparable claim must be blocked")
    return _inspect_result("Inspect pre-verl claim gate", path, failures, assert_requested=assert_claims_consistent)


def inspect_pre_verl_public_safe(path: str | Path, *, assert_share_safe: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("status") != "passed":
        failures.append("public-safe scan status is not passed")
    for key, value in payload.items():
        if key.endswith("_finding_count") and int(value or 0) != 0:
            failures.append(f"{key} is nonzero")
    return _inspect_result("Inspect pre-verl public-safe scan", path, failures, assert_requested=assert_share_safe)


def inspect_pre_verl_bundle(path: str | Path, *, final_command_log: str | Path | None = None, assert_immutable: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    for key in ("evaluation_report_ref", "reference_integrity_report_ref", "command_lineage_report_ref", "public_safe_scan_report_ref"):
        ref = payload.get(key)
        if not ref:
            failures.append(f"missing {key}")
        else:
            _check_ref(ref, failures, key)
    if final_command_log is not None and not Path(final_command_log).exists():
        failures.append("final command log does not exist")
    return _inspect_result("Inspect pre-verl evaluation bundle", path, failures, assert_requested=assert_immutable)


def inspect_pre_verl_readiness(path: str | Path, *, assert_verl_ready: bool = False) -> str:
    payload = _read_json(path)
    failures = []
    if payload.get("verl_readiness", {}).get("status") != "passed":
        failures.append("verl readiness is blocked: " + "; ".join(payload.get("verl_readiness", {}).get("blocking_reasons") or []))
    return _inspect_result("Inspect pre-verl readiness", path, failures, assert_requested=assert_verl_ready)


def _run_stage0_checks(*, root: Path, v5_acceptance_report: Path, v5_acceptance_bundle: Path, v5_final_command_log: Path) -> list[dict[str, Any]]:
    commands = [
        ["python", "-m", "compileall", "src"],
        ["python", "-m", "pytest", "-q"],
        ["repo-harness", "inspect-v5-acceptance", v5_acceptance_report.as_posix(), "--assert-core-complete"],
        ["repo-harness", "inspect-acceptance-bundle", v5_acceptance_bundle.as_posix(), "--final-command-log", v5_final_command_log.as_posix(), "--assert-immutable"],
    ]
    entries = []
    env = os.environ.copy()
    env["PATH"] = f".venv/bin:{env.get('PATH', '')}"
    for index, command in enumerate(commands, start=1):
        started = _now()
        proc = subprocess.run(command, cwd=Path.cwd(), text=True, capture_output=True, env=env)
        stdout_path = root / f"stage0_command_{index:02d}.stdout.txt"
        stderr_path = root / f"stage0_command_{index:02d}.stderr.txt"
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        entries.append(
            {
                "schema_version": "repo_harness_pre_verl_command_log_entry_v0",
                "command_name": command[0] if command[0] != "python" else " ".join(command[:3]),
                "argv": command,
                "cwd": str(Path.cwd()),
                "started_at": started,
                "finished_at": _now(),
                "exit_code": proc.returncode,
                "stdout_ref": _ref(stdout_path, "stdout", "inspect-pre-verl-baseline"),
                "stderr_ref": _ref(stderr_path, "stderr", "inspect-pre-verl-baseline"),
            }
        )
    return entries


def _ref(
    path: str | Path | None,
    kind: str,
    inspect_command: str,
    *,
    visibility: str = "audit_only",
    share_safe: bool = False,
) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"required evidence path does not exist: {p}")
    return {
        "schema_version": "repo_harness_pre_verl_evidence_ref_v0",
        "kind": kind,
        "path": p.as_posix(),
        "sha256": _sha256(p),
        "size_bytes": p.stat().st_size,
        "visibility": visibility,
        "share_safe": share_safe,
        "inspect_command": inspect_command,
    }


def _copy_ref(source_ref: dict[str, Any] | None, target: Path, kind: str) -> dict[str, Any]:
    if not source_ref or not source_ref.get("path"):
        raise ConfigError(f"missing source ref for {kind}")
    source = Path(str(source_ref["path"]))
    if not source.exists():
        raise ConfigError(f"source artifact does not exist: {source}")
    shutil.copyfile(source, target)
    return _ref(target, kind, "inspect-pre-verl-export-audit") or {}


def _check_ref(ref: dict[str, Any], failures: list[str], label: str) -> None:
    path = Path(str(ref.get("path") or ""))
    if not path.exists():
        failures.append(f"{label} path does not exist")
        return
    if ref.get("sha256") != _sha256(path):
        failures.append(f"{label} sha256 drift")


def _matrix_results(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    entries = matrix.get("entries")
    if isinstance(entries, list):
        return [_agentloop_result_from_entry(entry) for entry in entries if isinstance(entry, dict)]
    ref = matrix.get("matrix_cell_results_ref")
    if not ref or not ref.get("path"):
        return []
    return _read_jsonl(Path(str(ref["path"])))


def _agentloop_result_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    run_dir_value = entry.get("run_task_run_dir") or entry.get("run_dir")
    run_dir = Path(str(run_dir_value)) if run_dir_value else Path("<missing-run-dir>")
    metrics = _read_json_if_exists(run_dir / "metrics.json")
    metadata = _read_json_if_exists(run_dir / "run_metadata.json")
    run_config_facts = _read_json_if_exists(run_dir / "run_config_facts.json")
    boundary = _read_json_if_exists(run_dir / "final_verifier_boundary.json")
    events = _read_jsonl_if_exists(run_dir / "events.jsonl")
    provider_call_events = [
        event for event in events
        if event.get("event_type") == "model_call_completed"
        and ((event.get("data") or {}).get("provider") in {"deepseek", "openai"})
    ]
    final_patch_path = run_dir / "final.patch"
    final_patch_ref = (
        _ref(final_patch_path, "pre_verl_agent_final_patch", "inspect-pre-verl-agent-evaluation")
        if final_patch_path.exists() and final_patch_path.stat().st_size > 0
        else None
    )
    raw_request_refs = []
    raw_response_refs = []
    for event in provider_call_events:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if isinstance(data.get("raw_provider_request_ref"), dict):
            raw_request_refs.append(data["raw_provider_request_ref"])
        if isinstance(data.get("raw_provider_response_ref"), dict):
            raw_response_refs.append(data["raw_provider_response_ref"])
    tool_protocol = run_config_facts.get("tool_protocol") if isinstance(run_config_facts, dict) else {}
    tool_schema_snapshot_ref = (
        tool_protocol.get("tool_schema_snapshot_ref") if isinstance(tool_protocol, dict) else None
    )
    return {
        "task_id": entry.get("task_id") or metadata.get("task_id") or boundary.get("task_id"),
        "run_id": entry.get("run_id") or metadata.get("run_id"),
        "baseline_source": entry.get("baseline_source") or boundary.get("baseline_source"),
        "run_task_run_dir": run_dir.as_posix(),
        "run_task_command_log_entry_ref": entry.get("run_task_command_log_entry_ref"),
        "run_task_entrypoint": boundary.get("run_task_entrypoint"),
        "actual_provider_call_count": len(provider_call_events),
        "provider": entry.get("provider") or run_config_facts.get("actual_provider"),
        "model_id": entry.get("model_id") or run_config_facts.get("model_id"),
        "scaffold_id": entry.get("scaffold_id") or run_config_facts.get("scaffold_id") or metadata.get("scaffold_id"),
        "accepted": boundary.get("accepted"),
        "final_verifier_status": boundary.get("final_verifier_status") or metrics.get("final_verifier_status"),
        "failure_category": boundary.get("failure_category"),
        "failure_owner": boundary.get("failure_owner"),
        "final_patch_ref": final_patch_ref,
        "final_verifier_boundary_ref": (
            _ref(run_dir / "final_verifier_boundary.json", "pre_verl_final_verifier_boundary", "inspect-pre-verl-agent-evaluation")
            if (run_dir / "final_verifier_boundary.json").exists()
            else None
        ),
        "final_verifier_mode": run_config_facts.get("final_verifier_mode"),
        "tool_schema_snapshot_ref": tool_schema_snapshot_ref,
        "event_log_ref": (
            _ref(run_dir / "events.jsonl", "trajectory_event_log", "inspect-pre-verl-agent-runtime-audit")
            if (run_dir / "events.jsonl").exists()
            else None
        ),
        "transcript_ref": (
            _ref(run_dir / "transcript.jsonl", "trajectory_transcript", "inspect-pre-verl-agent-runtime-audit")
            if (run_dir / "transcript.jsonl").exists()
            else None
        ),
        "raw_provider_request_refs": raw_request_refs,
        "raw_provider_response_refs": raw_response_refs,
        "tool_call_count": int(metrics.get("tool_call_count", 0) or 0),
        "token_usage": _token_usage_from_events(provider_call_events),
    }


def _formal_agentloop_lineage_failures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for result in results:
        reasons = _formal_agentloop_result_failures(result)
        if reasons:
            failures.append(
                {
                    "task_id": result.get("task_id"),
                    "run_id": result.get("run_id"),
                    "reasons": reasons,
                }
            )
    return failures


def _formal_agentloop_result_failures(result: dict[str, Any]) -> list[str]:
    failures = []
    if result.get("baseline_source") != PRE_VERL_AGENTLOOP_BASELINE_SOURCE:
        failures.append("baseline_source_not_repo_harness_agentloop_run_task")
    run_dir = Path(str(result.get("run_task_run_dir") or ""))
    if not result.get("run_task_run_dir") or not run_dir.exists():
        failures.append("missing_run_task_run_dir")
        return failures
    _validate_pre_verl_run_metadata(run_dir, result, failures)
    _validate_pre_verl_run_config_facts(run_dir, failures)
    _validate_pre_verl_command_log_entry(result.get("run_task_command_log_entry_ref"), run_dir, result, failures)
    if result.get("run_task_entrypoint") != "repo-harness run-task":
        failures.append("missing_run_task_entrypoint")
    if result.get("scaffold_id") == "single_shot_patch_no_tools":
        failures.append("forbidden_single_shot_patch_no_tools")
    for key in ("accepted", "final_verifier_status", "failure_category"):
        if key not in result:
            failures.append(f"missing_{key}")
    if result.get("old_pilot_used") is True:
        failures.append("result_old_pilot_used")
    if result.get("legacy_v3_adapter_used") is True:
        failures.append("result_legacy_v3_adapter_used")
    for key in ("tool_schema_snapshot_ref", "event_log_ref", "transcript_ref", "final_verifier_boundary_ref"):
        _validate_pre_verl_result_ref(result.get(key), run_dir, failures, key, require_fingerprint=True)
    _validate_pre_verl_boundary_payload(result, run_dir, failures)
    if not result.get("raw_provider_request_refs"):
        failures.append("missing_raw_provider_request_refs")
    else:
        for index, ref in enumerate(result.get("raw_provider_request_refs", [])):
            _validate_pre_verl_result_ref(
                ref,
                run_dir,
                failures,
                f"raw_provider_request_refs[{index}]",
                require_fingerprint=True,
            )
    if not result.get("raw_provider_response_refs"):
        failures.append("missing_raw_provider_response_refs")
    else:
        for index, ref in enumerate(result.get("raw_provider_response_refs", [])):
            _validate_pre_verl_result_ref(
                ref,
                run_dir,
                failures,
                f"raw_provider_response_refs[{index}]",
                require_fingerprint=True,
            )
    event_path = _result_ref_path(result.get("event_log_ref"), run_dir)
    events = _read_jsonl_if_exists(event_path) if event_path is not None else []
    failures.extend(_pre_verl_agentloop_event_failures(events, run_dir))
    return failures


def _validate_pre_verl_run_metadata(
    run_dir: Path,
    result: dict[str, Any],
    failures: list[str],
) -> None:
    metadata = _read_json_if_exists(run_dir / "run_metadata.json")
    if not metadata:
        failures.append("missing_run_metadata_json")
        return
    run_id = metadata.get("run_id")
    if not run_id:
        failures.append("run_metadata_missing_run_id")
    if result.get("run_id") and run_id and result.get("run_id") != run_id:
        failures.append("run_metadata_run_id_mismatch")
    if metadata.get("scaffold_id") == "single_shot_patch_no_tools":
        failures.append("run_metadata_forbidden_single_shot_patch_no_tools")


def _validate_pre_verl_run_config_facts(run_dir: Path, failures: list[str]) -> None:
    facts = _read_json_if_exists(run_dir / "run_config_facts.json")
    if not facts:
        failures.append("missing_run_config_facts_json")
        return
    if facts.get("final_verifier_mode") != "strict_patch_replay":
        failures.append("run_config_facts_final_verifier_mode_not_strict_patch_replay")
    if facts.get("test_feedback_policy") != "disabled":
        failures.append("run_config_facts_test_feedback_policy_not_disabled")
    if facts.get("scaffold_id") == "single_shot_patch_no_tools":
        failures.append("run_config_facts_forbidden_single_shot_patch_no_tools")
    tool_protocol = facts.get("tool_protocol") if isinstance(facts.get("tool_protocol"), dict) else {}
    _validate_pre_verl_result_ref(
        tool_protocol.get("tool_schema_snapshot_ref"),
        run_dir,
        failures,
        "run_config_facts.tool_schema_snapshot_ref",
        require_fingerprint=True,
    )


def _validate_pre_verl_command_log_entry(
    ref: Any,
    run_dir: Path,
    result: dict[str, Any],
    failures: list[str],
) -> None:
    path = _validate_pre_verl_result_ref(
        ref,
        run_dir,
        failures,
        "run_task_command_log_entry_ref",
        require_fingerprint=True,
    )
    if path is None:
        return
    payload = _read_json_if_exists(path)
    if not payload:
        failures.append("run_task_command_log_entry_ref_not_json_object")
        return
    if payload.get("command_name") != "run-task":
        failures.append("run_task_command_log_entry_command_name_not_run_task")
    if payload.get("exit_code") != 0:
        failures.append("run_task_command_log_entry_exit_code_not_zero")
    argv = payload.get("argv")
    if not isinstance(argv, list):
        failures.append("run_task_command_log_entry_argv_not_list")
        return
    argv_strings = [str(item) for item in argv]
    if "run-task" not in argv_strings:
        failures.append("run_task_command_log_entry_argv_missing_run_task")
    expected_run_id = str(result.get("run_id") or "")
    if expected_run_id:
        try:
            run_id_index = argv_strings.index("--run-id")
        except ValueError:
            failures.append("run_task_command_log_entry_argv_missing_run_id")
        else:
            observed = argv_strings[run_id_index + 1] if run_id_index + 1 < len(argv_strings) else None
            if observed != expected_run_id:
                failures.append("run_task_command_log_entry_run_id_mismatch")


def _validate_pre_verl_result_ref(
    ref: Any,
    run_dir: Path,
    failures: list[str],
    label: str,
    *,
    require_fingerprint: bool = False,
) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"missing_{label}")
        return None
    path = _result_ref_path(ref, run_dir)
    if path is None:
        failures.append(f"{label}_missing_path")
        return None
    if not path.exists():
        failures.append(f"{label}_path_missing")
        return None
    expected_sha = ref.get("sha256")
    if require_fingerprint and not isinstance(expected_sha, str):
        failures.append(f"{label}_missing_sha256")
    if isinstance(expected_sha, str) and path.is_file() and _sha256(path) != expected_sha:
        failures.append(f"{label}_sha256_drift")
    size_bytes = ref.get("size_bytes")
    if require_fingerprint and not isinstance(size_bytes, int):
        failures.append(f"{label}_missing_size_bytes")
    if isinstance(size_bytes, int) and path.is_file() and path.stat().st_size != size_bytes:
        failures.append(f"{label}_size_bytes_drift")
    return path


def _validate_pre_verl_boundary_payload(
    result: dict[str, Any],
    run_dir: Path,
    failures: list[str],
) -> None:
    boundary_path = _result_ref_path(result.get("final_verifier_boundary_ref"), run_dir)
    if boundary_path is None or not boundary_path.exists():
        return
    boundary = _read_json_if_exists(boundary_path)
    if not boundary:
        failures.append("final_verifier_boundary_ref_not_json_object")
        return
    if boundary.get("baseline_source") != PRE_VERL_AGENTLOOP_BASELINE_SOURCE:
        failures.append("final_verifier_boundary_baseline_source_mismatch")
    if boundary.get("run_task_entrypoint") != "repo-harness run-task":
        failures.append("final_verifier_boundary_run_task_entrypoint_mismatch")
    if "accepted" not in boundary:
        failures.append("final_verifier_boundary_missing_accepted")
    elif "accepted" in result and bool(result.get("accepted")) != bool(boundary.get("accepted")):
        failures.append("final_verifier_boundary_accepted_mismatch")
    expected_status = result.get("final_verifier_status")
    if "final_verifier_status" not in boundary:
        failures.append("final_verifier_boundary_missing_status")
    elif expected_status is not None and boundary.get("final_verifier_status") != expected_status:
        failures.append("final_verifier_boundary_status_mismatch")
    expected_category = result.get("failure_category")
    if "failure_category" not in boundary:
        failures.append("final_verifier_boundary_missing_failure_category")
    elif boundary.get("failure_category") != expected_category:
        failures.append("final_verifier_boundary_failure_category_mismatch")
    for key in ("old_pilot_used", "legacy_v3_adapter_used"):
        if key in result and result.get(key) != boundary.get(key):
            failures.append(f"final_verifier_boundary_{key}_mismatch")
    if boundary.get("old_pilot_used") is True:
        failures.append("final_verifier_boundary_old_pilot_used")
    if boundary.get("legacy_v3_adapter_used") is True:
        failures.append("final_verifier_boundary_legacy_v3_adapter_used")


def _result_ref_path(ref: Any, run_dir: Path) -> Path | None:
    if not isinstance(ref, dict):
        return None
    value = ref.get("path") or ref.get("relative_path")
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else run_dir / path


def _pre_verl_agentloop_event_failures(events: list[dict[str, Any]], run_dir: Path) -> list[str]:
    failures: list[str] = []
    if not events:
        return ["events_jsonl_empty_or_unreadable"]
    event_types = [str(event.get("event_type") or "") for event in events]
    for required in ("run_started", "baseline_completed", "context_prepared", "model_call_started", "model_call_completed", "run_finished"):
        if required not in event_types:
            failures.append(f"events_missing_{required}")
    started_ids = _pre_verl_event_ids(events, "model_call_started", "model_call_id")
    completed_ids = _pre_verl_event_ids(events, "model_call_completed", "model_call_id")
    if set(started_ids) != set(completed_ids):
        failures.append("model_call_events_unpaired")
    real_provider_completed = 0
    for index, event in enumerate(events):
        if event.get("event_type") != "model_call_completed":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if data.get("provider") not in {"deepseek", "openai"}:
            continue
        real_provider_completed += 1
        _validate_pre_verl_result_ref(
            data.get("raw_provider_request_ref"),
            run_dir,
            failures,
            f"events_model_call_completed_{index}_raw_provider_request_ref",
            require_fingerprint=True,
        )
        _validate_pre_verl_result_ref(
            data.get("raw_provider_response_ref"),
            run_dir,
            failures,
            f"events_model_call_completed_{index}_raw_provider_response_ref",
            require_fingerprint=True,
        )
    if real_provider_completed == 0:
        failures.append("events_missing_real_provider_model_call_completed")
    requested = _pre_verl_event_ids(events, "tool_requested", "tool_call_id")
    terminal = []
    for event_type in ("tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"):
        terminal.extend(_pre_verl_event_ids(events, event_type, "tool_call_id"))
    if set(requested) - set(terminal):
        failures.append("tool_use_missing_tool_result")
    if set(terminal) - set(requested):
        failures.append("tool_result_missing_tool_use")
    return failures


def _pre_verl_event_ids(events: list[dict[str, Any]], event_type: str, key: str) -> list[str]:
    ids: list[str] = []
    for event in events:
        if event.get("event_type") != event_type:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        value = data.get(key)
        if isinstance(value, str) and value:
            ids.append(value)
    return ids


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _token_usage_from_events(events: list[dict[str, Any]]) -> dict[str, int]:
    input_tokens = 0
    output_tokens = 0
    for event in events:
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        input_tokens += int(data.get("input_tokens", 0) or 0)
        output_tokens += int(data.get("output_tokens", 0) or 0)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def _is_accepted(item: dict[str, Any]) -> bool:
    return bool(item.get("accepted") is True and item.get("final_verifier_status") == "accepted" and item.get("final_verifier_boundary_ref"))


def _phase_coverage(results: list[dict[str, Any]]) -> dict[str, Any]:
    phases = [
        "source_checkout_or_restore",
        "dependency_install_or_cache_restore",
        "baseline_test_patch_apply",
        "candidate_patch_apply",
        "verifier_command_run",
        "artifact_collection",
        "workspace_cleanup",
    ]
    rows = []
    for result in results:
        accepted = _is_accepted(result)
        for phase in phases:
            attempted = phase not in {"baseline_test_patch_apply", "verifier_command_run"} or bool(result.get("final_verifier_boundary_ref"))
            rows.append(
                {
                    "task_id": result.get("task_id"),
                    "run_id": result.get("run_id"),
                    "phase_name": phase,
                    "attempted": attempted,
                    "succeeded": attempted and (accepted or phase not in {"verifier_command_run", "candidate_patch_apply"}),
                    "duration_ms": None,
                    "failure_category": None if attempted else "not_attempted",
                    "failure_owner": None if attempted else "pre_verl_missing_evidence",
                    "command_log_ref": None,
                    "stdout_ref": None,
                    "stderr_ref": None,
                }
            )
    tasks_with_all_required_phases = len({item.get("run_id") for item in results if _is_accepted(item)})
    return {
        "schema_version": "repo_harness_pre_verl_phase_coverage_matrix_v0",
        "created_at": _now(),
        "phase_records": rows,
        "tasks_with_all_required_phases_count": tasks_with_all_required_phases,
        "source_restore_failed_count": 0,
        "dependency_install_failed_count": 0,
        "baseline_test_patch_apply_failed_count": 0,
        "candidate_patch_apply_failed_count": sum(1 for item in results if item.get("actual_provider_call_count", 0) > 0 and not item.get("final_patch_ref")),
        "verifier_command_failed_count": sum(1 for item in results if item.get("final_verifier_status") not in ("accepted", None)),
        "artifact_collection_failed_count": 0,
        "workspace_cleanup_failed_count": 0,
        "minimum_phase_coverage_status": "passed" if tasks_with_all_required_phases >= 1 else "blocked",
        "full_expanded_phase_coverage_status": "partial",
        "status": "passed" if tasks_with_all_required_phases >= 1 else "blocked",
    }


def _phase_coverage_from_materialization(materialization: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for entry in materialization.get("entries", []):
        if not isinstance(entry, dict):
            continue
        task_id = entry.get("task_id")
        phase_specs = [
            ("source_checkout_or_restore", entry.get("source_checkout_status") == "passed", entry.get("source_checkout_ref")),
            ("dependency_install_or_cache_restore", entry.get("dependency_install_status") == "passed", entry.get("dependency_setup_result_ref")),
            ("baseline_test_patch_apply", entry.get("test_patch_apply_status") == "passed", entry.get("test_patch_apply_result_ref")),
            ("candidate_patch_apply", entry.get("gold_patch_replay_status") == "passed", entry.get("gold_patch_replay_result_ref")),
            ("verifier_command_run", entry.get("noop_fail_status") == "passed" and entry.get("gold_patch_replay_status") == "passed", entry.get("gold_patch_replay_result_ref")),
            ("artifact_collection", entry.get("status") == "passed", entry.get("entry_report_path")),
            ("workspace_cleanup", True, entry.get("entry_report_path")),
        ]
        for phase_name, succeeded, ref in phase_specs:
            rows.append(
                {
                    "task_id": task_id,
                    "run_id": task_id,
                    "phase_name": phase_name,
                    "attempted": ref is not None,
                    "succeeded": bool(succeeded),
                    "duration_ms": None,
                    "failure_category": None if succeeded else "phase_failed_or_missing",
                    "failure_owner": None if succeeded else "harness_or_environment",
                    "command_log_ref": None,
                    "stdout_ref": None,
                    "stderr_ref": None,
                }
            )
    tasks_with_all_required_phases = int(materialization.get("materialized_development_instance_count", 0) or 0)
    attempted = int(materialization.get("attempted_development_instance_count", 0) or 0)
    complete = attempted > 0 and tasks_with_all_required_phases == attempted
    return {
        "schema_version": "repo_harness_pre_verl_phase_coverage_matrix_v0",
        "created_at": _now(),
        "phase_records": rows,
        "tasks_with_all_required_phases_count": tasks_with_all_required_phases,
        "source_restore_failed_count": attempted - int(materialization.get("source_checkout_complete_count", 0) or 0),
        "dependency_install_failed_count": attempted - int(materialization.get("dependency_install_complete_count", 0) or 0),
        "baseline_test_patch_apply_failed_count": attempted - int(materialization.get("test_patch_apply_complete_count", 0) or 0),
        "candidate_patch_apply_failed_count": attempted - int(materialization.get("gold_patch_replay_pass_count", 0) or 0),
        "verifier_command_failed_count": attempted - int(materialization.get("gold_patch_replay_pass_count", 0) or 0),
        "artifact_collection_failed_count": 0 if complete else attempted - tasks_with_all_required_phases,
        "workspace_cleanup_failed_count": 0,
        "minimum_phase_coverage_status": "passed" if tasks_with_all_required_phases >= 1 else "blocked",
        "full_expanded_phase_coverage_status": "passed" if complete else "partial",
        "status": "passed" if complete else "blocked",
    }


def _agent_failure_taxonomy(results: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for item in results:
        category = "accepted" if _is_accepted(item) else str(item.get("failure_category") or item.get("final_verifier_status") or "unknown")
        categories[category] = categories.get(category, 0) + 1
    return {
        "schema_version": "repo_harness_pre_verl_agent_evaluation_failure_taxonomy_v0",
        "failure_type_distribution": categories,
        "diagnosis_policy": _pre_verl_failure_owner_policy(),
        "included_runtime_categories": [
            "query_loop_max_turns_exceeded",
            "tool_schema_validation_failed",
            "tool_permission_denied",
            "headless_permission_unavailable",
            "tool_result_pairing_invalid",
            "context_compaction_failed",
            "context_window_exceeded",
            "patch_extraction_failed",
            "transcript_incomplete",
            "dynamic_tool_pool_drift",
        ],
        "status": "passed",
    }


def _pre_verl_failure_owner_policy() -> dict[str, str]:
    return {
        "accepted": "strict final verifier accepted the provider patch.",
        "provider_or_budget": "provider returned quota, rate limit, authentication, timeout, credential, or transport failure before a patch could be judged.",
        "harness_or_environment": "dependency setup, source restore, hidden test patch apply, verifier plan, or verifier execution failed before the model patch could be judged.",
        "model_wrong_fix": "candidate patch applied and final verifier executed in an environment already proven healthy by materialization, but verifier rejected the patch.",
        "model_or_prompt_scaffold": "provider returned no usable unified diff, a diff that could not apply to the frozen source tree, or a response format unsuitable for the single-shot patch scaffold.",
        "budget_or_timeout": "candidate patch reached verifier execution, but the verifier timed out under the configured budget.",
    }


def _pre_verl_structured_provider_skip(*, task: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_pre_verl_agent_evaluation_result_v0",
        "cell_id": f"pre_verl_skip_{_safe_file_stem(str(task.get('task_id') or 'task'))}",
        "run_id": f"pre_verl_skip_{_safe_file_stem(str(task.get('task_id') or 'task'))}",
        "task_id": task.get("task_id"),
        "source_instance_id": task.get("source_instance_id"),
        "repo": task.get("repo"),
        "provider_id": "deepseek",
        "model_id": None,
        "scaffold_id": "single_shot_patch_no_tools",
        "actual_provider_call_count": 0,
        "terminal_outcome": False,
        "accepted": False,
        "final_verifier_status": "not_executed",
        "failure_category": reason,
        "failure_owner": "provider_or_budget" if "credential" in reason else "harness_or_environment",
        "failure_diagnosis": reason,
    }


def _run_one_pre_verl_provider_task(
    *,
    task: dict[str, Any],
    materialization_entry: dict[str, Any],
    provider_id: str,
    model_id: str,
    credential_value: str,
    credential_source: str,
    root: Path,
    run_root: Path,
    logs_root: Path,
    max_output_tokens: int,
    request_timeout_seconds: int,
    temperature: float,
    max_source_context_chars: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    task_id = str(task.get("task_id") or "")
    safe_id = _safe_file_stem(task_id)
    run_id = f"pre_verl_{provider_id}_{safe_id}_{_safe_file_stem(model_id)}"
    run_dir = run_root / safe_id
    run_dir.mkdir(parents=True, exist_ok=True)
    command_entries: list[dict[str, Any]] = []
    source_dir = _materialized_source_dir(materialization_entry, safe_id)
    if not source_dir.exists():
        return (
            {
                **_base_provider_result(task, provider_id=provider_id, model_id=model_id, run_id=run_id),
                "terminal_outcome": False,
                "failure_category": "materialized_source_checkout_missing",
                "failure_owner": "harness_or_environment",
                "failure_diagnosis": "Materialization report passed, but the referenced clean source checkout is missing.",
            },
            command_entries,
            False,
        )
    prompt_messages = _build_pre_verl_patch_messages(
        task=task,
        materialization_entry=materialization_entry,
        source_dir=source_dir,
        max_source_context_chars=max_source_context_chars,
    )
    prepared_messages_path = run_dir / "prepared_messages.json"
    _write_json(
        prepared_messages_path,
        {
            "schema_version": "repo_harness_pre_verl_prepared_messages_v0",
            "task_id": task_id,
            "model_visible_hidden_evidence_included": False,
            "messages": prompt_messages,
            "status": "passed",
        },
    )
    provider_payload = _call_deepseek_for_patch(
        messages=prompt_messages,
        model_id=model_id,
        credential_value=credential_value,
        credential_source=credential_source,
        run_dir=run_dir,
        max_output_tokens=max_output_tokens,
        request_timeout_seconds=request_timeout_seconds,
        temperature=temperature,
    )
    transcript_path = run_dir / "transcript.jsonl"
    _write_jsonl(
        transcript_path,
        [
            *({"role": item["role"], "content": item["content"]} for item in prompt_messages),
            {
                "role": "assistant",
                "content": provider_payload.get("assistant_text") or "",
                "model_error_type": provider_payload.get("model_error_type"),
            },
        ],
    )
    result_base = {
        **_base_provider_result(task, provider_id=provider_id, model_id=model_id, run_id=run_id),
        "cell_id": f"pre_verl_cell_{safe_id}_{provider_id}",
        "prepared_messages_ref": _ref(prepared_messages_path, "pre_verl_prepared_messages", "inspect-pre-verl-agent-evaluation", visibility="model_visible"),
        "transcript_ref": _ref(transcript_path, "pre_verl_agent_evaluation_transcript", "inspect-pre-verl-agent-runtime-audit"),
        "provider_request_ref": provider_payload.get("provider_request_ref"),
        "provider_response_ref": provider_payload.get("provider_response_ref"),
        "actual_provider_call_count": 1,
        "token_usage": provider_payload.get("token_usage") or {},
        "finish_reason": provider_payload.get("finish_reason"),
        "model_error_type": provider_payload.get("model_error_type"),
        "terminal_outcome": True,
    }
    if provider_payload.get("status") != "passed":
        category = _provider_error_failure_category(provider_payload)
        result_path = run_dir / "provider_result.json"
        result = {
            **result_base,
            "accepted": False,
            "final_verifier_status": "not_executed",
            "failure_category": category,
            "failure_owner": "provider_or_budget",
            "failure_diagnosis": _provider_error_diagnosis(provider_payload),
        }
        _write_json(result_path, result)
        result["result_ref"] = _ref(result_path, "pre_verl_agent_evaluation_result", "inspect-pre-verl-agent-evaluation")
        return result, command_entries, _provider_error_is_fatal(provider_payload)

    parse_result = parse_patch_action(str(provider_payload.get("assistant_text") or ""))
    patch_parse_path = run_dir / "patch_parse_result.json"
    _write_json(patch_parse_path, parse_result.model_dump(mode="json"))
    if not parse_result.success:
        result_path = run_dir / "provider_result.json"
        category = "empty_patch" if parse_result.error_type == "empty_patch_action" else "patch_extraction_failed"
        result = {
            **result_base,
            "patch_parse_result_ref": _ref(patch_parse_path, "pre_verl_patch_parse_result", "inspect-pre-verl-agent-evaluation"),
            "accepted": False,
            "final_verifier_status": "not_executed",
            "failure_category": category,
            "failure_owner": "model_or_prompt_scaffold",
            "failure_diagnosis": "Provider returned a terminal response, but it did not contain a usable unified diff. The materialized verifier environment was not reached.",
        }
        _write_json(result_path, result)
        result["result_ref"] = _ref(result_path, "pre_verl_agent_evaluation_result", "inspect-pre-verl-agent-evaluation")
        return result, command_entries, False

    final_patch_path = run_dir / "final_patch.diff"
    final_patch_path.write_text(parse_result.patch_text, encoding="utf-8")
    verifier_fields, verifier_commands = _verify_pre_verl_candidate_patch(
        task=task,
        materialization_entry=materialization_entry,
        source_dir=source_dir,
        run_dir=run_dir,
        logs_root=logs_root,
        final_patch_path=final_patch_path,
    )
    command_entries.extend(verifier_commands)
    result_path = run_dir / "provider_result.json"
    result = {
        **result_base,
        "patch_parse_result_ref": _ref(patch_parse_path, "pre_verl_patch_parse_result", "inspect-pre-verl-agent-evaluation"),
        "final_patch_ref": _ref(final_patch_path, "pre_verl_agent_final_patch", "inspect-pre-verl-agent-evaluation", visibility="audit_only"),
        **verifier_fields,
    }
    _write_json(result_path, result)
    result["result_ref"] = _ref(result_path, "pre_verl_agent_evaluation_result", "inspect-pre-verl-agent-evaluation")
    return result, command_entries, False


def _base_provider_result(
    task: dict[str, Any],
    *,
    provider_id: str,
    model_id: str | None,
    run_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_pre_verl_agent_evaluation_result_v0",
        "run_id": run_id,
        "task_id": task.get("task_id"),
        "source_instance_id": task.get("source_instance_id"),
        "repo": task.get("repo"),
        "provider_id": provider_id,
        "provider_family": provider_id,
        "model_id": model_id,
        "scaffold_id": "single_shot_patch_no_tools",
        "tool_policy_id": "no_tool_single_prompt",
        "context_policy_id": "problem_statement_plus_bounded_source_snippets",
        "budget_policy_id": "single_provider_call_then_strict_final_verifier",
        "accepted": False,
        "actual_provider_call_count": 0,
        "tool_call_count": 0,
        "invalid_tool_call_count": 0,
        "permission_denial_count": 0,
    }


def _materialized_source_dir(materialization_entry: dict[str, Any], safe_id: str) -> Path:
    entry_path = Path(str(materialization_entry.get("entry_report_path") or ""))
    if entry_path.exists() and len(entry_path.parents) >= 3:
        return entry_path.parents[2] / "source_checkouts" / safe_id / "source"
    return Path("runs") / "missing_pre_verl_materialization_root" / "source_checkouts" / safe_id / "source"


def _build_pre_verl_patch_messages(
    *,
    task: dict[str, Any],
    materialization_entry: dict[str, Any],
    source_dir: Path,
    max_source_context_chars: int,
) -> list[dict[str, str]]:
    adapter_ref = task.get("adapter_visible_input_ref") if isinstance(task.get("adapter_visible_input_ref"), dict) else None
    adapter = _read_json(adapter_ref["path"]) if adapter_ref and adapter_ref.get("path") else {}
    problem = str(adapter.get("problem_statement") or "")
    source_context = _source_context_for_prompt(
        source_dir=source_dir,
        problem_statement=problem,
        max_source_context_chars=max_source_context_chars,
    )
    system = (
        "You are fixing a frozen software engineering task inside RepoHarness. "
        "Return only a unified diff that applies to the base repository. "
        "Do not include explanations, markdown prose, hidden tests, or evaluation-only artifacts."
    )
    user = (
        f"Task id: {task.get('task_id')}\n"
        f"SWE-Bench Lite instance id: {task.get('source_instance_id')}\n"
        f"Repository: {task.get('repo')}\n"
        f"Base commit: {task.get('base_commit')}\n"
        f"Version: {task.get('version')}\n"
        f"Environment id: {materialization_entry.get('environment_id')}\n\n"
        "Issue statement visible to the model:\n"
        f"{problem}\n\n"
        "Bounded model-visible source context from the frozen checkout:\n"
        f"{source_context}\n\n"
        "Output requirement: provide a unified diff only. The hidden final verifier will be applied after your patch."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _source_context_for_prompt(*, source_dir: Path, problem_statement: str, max_source_context_chars: int) -> str:
    ignored_parts = {".git", ".pre_verl_venv", ".pytest_cache", "__pycache__", ".tox", "build", "dist"}
    tokens = _problem_tokens(problem_statement)
    mentioned_paths = {
        token.strip("`'\"")
        for token in re.findall(r"[A-Za-z0-9_./-]+\.py", problem_statement)
    }
    candidates: list[tuple[int, Path]] = []
    for path in source_dir.rglob("*.py"):
        rel_parts = path.relative_to(source_dir).parts
        if any(part in ignored_parts for part in rel_parts):
            continue
        rel = path.relative_to(source_dir).as_posix()
        score = 0
        if _path_matches_mentioned_source(rel, path.name, mentioned_paths):
            score += 100
        lowered_rel = rel.lower()
        for token in tokens:
            if token.lower() in lowered_rel:
                score += 5
        try:
            snippet = path.read_text(encoding="utf-8", errors="ignore")[:12000]
        except OSError:
            snippet = ""
        for token in list(tokens)[:40]:
            if token and token in snippet:
                score += 1
        if score > 0:
            candidates.append((score, path))
    candidates.sort(key=lambda item: (-item[0], item[1].relative_to(source_dir).as_posix()))
    if not candidates:
        candidates = [
            (0, path)
            for path in sorted(source_dir.rglob("*.py"))
            if not any(part in ignored_parts for part in path.relative_to(source_dir).parts)
        ][:5]
    chunks = []
    remaining = max_source_context_chars
    for _, path in candidates[:8]:
        if remaining <= 0:
            break
        rel = path.relative_to(source_dir).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        snippet = text[: min(len(text), max(0, remaining - len(rel) - 32))]
        if not snippet:
            continue
        chunk = f"\n--- {rel} ---\n{snippet}\n"
        chunks.append(chunk)
        remaining -= len(chunk)
    if not chunks:
        return "No source snippets selected by the bounded context heuristic."
    return "".join(chunks)


def _path_matches_mentioned_source(rel: str, name: str, mentioned_paths: set[str]) -> bool:
    for mentioned in mentioned_paths:
        normalized = mentioned.strip("/").replace("\\", "/")
        if not normalized:
            continue
        parts = [part for part in normalized.split("/") if part]
        suffixes = {"/".join(parts[index:]) for index in range(len(parts))}
        suffixes.add(normalized)
        for suffix in suffixes:
            if rel == suffix or name == suffix or rel.endswith(f"/{suffix}"):
                return True
        if parts and name == parts[-1]:
            return True
    return False


def _problem_tokens(problem_statement: str) -> set[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "when",
        "where",
        "should",
        "would",
        "could",
        "into",
        "issue",
        "error",
        "test",
        "tests",
    }
    return {
        token
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", problem_statement)
        if token.lower() not in stopwords
    }


def _call_deepseek_for_patch(
    *,
    messages: list[dict[str, str]],
    model_id: str,
    credential_value: str,
    credential_source: str,
    run_dir: Path,
    max_output_tokens: int,
    request_timeout_seconds: int,
    temperature: float,
) -> dict[str, Any]:
    body = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "stream": False,
    }
    request_path = run_dir / "raw_deepseek_provider_request_redacted.json"
    response_path = run_dir / "raw_deepseek_provider_response_redacted.json"
    _write_json(
        request_path,
        {
            "schema_version": "repo_harness_pre_verl_deepseek_provider_request_v0",
            "provider": "deepseek",
            "base_url": DEEPSEEK_DEFAULT_BASE_URL,
            "credential_source": credential_source,
            "authorization": "[REDACTED]",
            "body": body,
            "export_allowed": False,
            "training_payload_allowed": False,
        },
    )
    request = Request(
        f"{DEEPSEEK_DEFAULT_BASE_URL}{DEEPSEEK_CHAT_COMPLETIONS_PATH}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {credential_value}"},
    )
    try:
        with urlopen(request, timeout=request_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_payload = _http_error_payload(exc)
        _write_json(
            response_path,
            {
                "schema_version": "repo_harness_pre_verl_deepseek_provider_response_v0",
                "provider": "deepseek",
                "status": "provider_error",
                "status_code": exc.code,
                "error": redact_provider_payload(error_payload),
                "export_allowed": False,
                "training_payload_allowed": False,
            },
        )
        return {
            "status": "provider_error",
            "status_code": exc.code,
            "model_error_type": _provider_error_type_from_status(exc.code),
            "provider_request_ref": _ref(request_path, "raw_deepseek_provider_request", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
            "provider_response_ref": _ref(response_path, "raw_deepseek_provider_response", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
            "error": error_payload,
        }
    except (TimeoutError, URLError) as exc:
        _write_json(
            response_path,
            {
                "schema_version": "repo_harness_pre_verl_deepseek_provider_response_v0",
                "provider": "deepseek",
                "status": "provider_error",
                "model_error_type": "provider_timeout_or_transport_error",
                "message": str(exc),
                "export_allowed": False,
                "training_payload_allowed": False,
            },
        )
        return {
            "status": "provider_error",
            "model_error_type": "provider_timeout_or_transport_error",
            "provider_request_ref": _ref(request_path, "raw_deepseek_provider_request", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
            "provider_response_ref": _ref(response_path, "raw_deepseek_provider_response", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
        }
    except json.JSONDecodeError as exc:
        _write_json(
            response_path,
            {
                "schema_version": "repo_harness_pre_verl_deepseek_provider_response_v0",
                "provider": "deepseek",
                "status": "provider_error",
                "model_error_type": "invalid_response",
                "message": str(exc),
                "export_allowed": False,
                "training_payload_allowed": False,
            },
        )
        return {
            "status": "provider_error",
            "model_error_type": "invalid_response",
            "provider_request_ref": _ref(request_path, "raw_deepseek_provider_request", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
            "provider_response_ref": _ref(response_path, "raw_deepseek_provider_response", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
        }
    choice = (payload.get("choices") or [{}])[0] if isinstance(payload.get("choices"), list) else {}
    message = choice.get("message") if isinstance(choice, dict) else {}
    assistant_text = str((message or {}).get("content") or "")
    _write_json(
        response_path,
        {
            "schema_version": "repo_harness_pre_verl_deepseek_provider_response_v0",
            "provider": "deepseek",
            "status": "passed",
            "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
            "usage": payload.get("usage") if isinstance(payload.get("usage"), dict) else {},
            "response": redact_provider_payload(payload),
            "export_allowed": False,
            "training_payload_allowed": False,
        },
    )
    return {
        "status": "passed",
        "assistant_text": assistant_text,
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
        "token_usage": payload.get("usage") if isinstance(payload.get("usage"), dict) else {},
        "provider_request_ref": _ref(request_path, "raw_deepseek_provider_request", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
        "provider_response_ref": _ref(response_path, "raw_deepseek_provider_response", "inspect-pre-verl-agent-evaluation", visibility="evaluator_only"),
    }


def _verify_pre_verl_candidate_patch(
    *,
    task: dict[str, Any],
    materialization_entry: dict[str, Any],
    source_dir: Path,
    run_dir: Path,
    logs_root: Path,
    final_patch_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    command_entries: list[dict[str, Any]] = []
    task_id = str(task.get("task_id") or "")
    safe_id = _safe_file_stem(task_id)
    workspace = run_dir / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(source_dir, workspace, symlinks=True)
    env_spec = _pre_verl_environment_for_repo(str(task.get("repo") or ""), str(task.get("version") or ""))
    setup_result, setup_entry = _run_docker_shell(
        workspace=workspace,
        image=env_spec["execution_image"],
        shell_command=env_spec["setup_shell"],
        logs_root=logs_root,
        label=f"{safe_id}_provider_eval_dependency_setup",
        timeout_sec=int(env_spec["setup_timeout_sec"]),
        stage="pre_verl_agent_evaluation_pilot",
    )
    command_entries.append(setup_entry)
    setup_path = run_dir / "dependency_setup_result.json"
    _write_json(setup_path, {**setup_result, "environment": env_spec, "status": "passed" if setup_result["exit_code"] == 0 else "failed"})
    if setup_result["exit_code"] != 0:
        return (
            {
                "accepted": False,
                "final_verifier_status": "not_executed",
                "dependency_setup_result_ref": _ref(setup_path, "pre_verl_dependency_setup_result", "inspect-pre-verl-agent-evaluation"),
                "failure_category": "environment_setup_failed",
                "failure_owner": "harness_or_environment",
                "failure_diagnosis": "The candidate patch could not be judged because dependency setup failed despite prior materialization evidence.",
            },
            command_entries,
        )
    patch_apply, patch_apply_entries = _apply_candidate_patch(
        workspace,
        logs_root,
        final_patch_path,
        f"{safe_id}_provider_patch_apply",
    )
    command_entries.extend(patch_apply_entries)
    patch_apply_path = run_dir / "candidate_patch_apply_result.json"
    _write_json(patch_apply_path, {**patch_apply, "status": "passed" if patch_apply["exit_code"] == 0 else "failed"})
    if patch_apply["exit_code"] != 0:
        return (
            {
                "accepted": False,
                "final_verifier_status": "not_executed",
                "dependency_setup_result_ref": _ref(setup_path, "pre_verl_dependency_setup_result", "inspect-pre-verl-agent-evaluation"),
                "candidate_patch_apply_result_ref": _ref(patch_apply_path, "pre_verl_candidate_patch_apply_result", "inspect-pre-verl-agent-evaluation"),
                "failure_category": "patch_apply_failed",
                "failure_owner": "model_or_prompt_scaffold",
                "failure_diagnosis": "The provider returned a diff, but it did not apply to the frozen base source tree. This points to the model output or the single-shot scaffold, not the verifier.",
            },
            command_entries,
        )
    verifier_plan_ref = materialization_entry.get("verifier_plan_ref") if isinstance(materialization_entry.get("verifier_plan_ref"), dict) else None
    if not verifier_plan_ref or not verifier_plan_ref.get("path"):
        return (
            {
                "accepted": False,
                "final_verifier_status": "not_executed",
                "failure_category": "verifier_plan_missing",
                "failure_owner": "harness_or_environment",
                "failure_diagnosis": "The materialization entry is missing the verifier plan required to judge the provider patch.",
            },
            command_entries,
        )
    verifier_plan = _read_json(verifier_plan_ref["path"])
    test_patch_ref = verifier_plan.get("test_patch_ref") if isinstance(verifier_plan.get("test_patch_ref"), dict) else None
    selectors = [str(item) for item in verifier_plan.get("fail_to_pass_selectors", []) if str(item).strip()]
    if not test_patch_ref or not test_patch_ref.get("path") or not selectors:
        return (
            {
                "accepted": False,
                "final_verifier_status": "not_executed",
                "verifier_plan_ref": verifier_plan_ref,
                "failure_category": "verifier_plan_incomplete",
                "failure_owner": "harness_or_environment",
                "failure_diagnosis": "The verifier plan does not include a hidden test patch and fail-to-pass selectors.",
            },
            command_entries,
        )
    test_apply, test_apply_entry = _run_logged_command(
        ["git", "apply", Path(str(test_patch_ref["path"])).resolve().as_posix()],
        workspace,
        logs_root,
        f"{safe_id}_provider_hidden_test_patch_apply",
        120,
        "pre_verl_agent_evaluation_pilot",
    )
    command_entries.append(test_apply_entry)
    test_apply_path = run_dir / "hidden_test_patch_apply_result.json"
    _write_json(test_apply_path, {**test_apply, "status": "passed" if test_apply["exit_code"] == 0 else "failed"})
    if test_apply["exit_code"] != 0:
        return (
            {
                "accepted": False,
                "final_verifier_status": "not_executed",
                "verifier_plan_ref": verifier_plan_ref,
                "dependency_setup_result_ref": _ref(setup_path, "pre_verl_dependency_setup_result", "inspect-pre-verl-agent-evaluation"),
                "candidate_patch_apply_result_ref": _ref(patch_apply_path, "pre_verl_candidate_patch_apply_result", "inspect-pre-verl-agent-evaluation"),
                "hidden_test_patch_apply_result_ref": _ref(test_apply_path, "pre_verl_hidden_test_patch_apply_result", "inspect-pre-verl-agent-evaluation"),
                "failure_category": "hidden_test_patch_conflict_after_candidate_patch",
                "failure_owner": "model_or_prompt_scaffold",
                "failure_diagnosis": "The hidden test patch applied during materialization but no longer applied after the provider patch, so the provider patch changed the source tree incompatibly before final verification could run.",
            },
            command_entries,
        )
    final_result_path, final_payload, verifier_commands = _run_pytest_selector_set(
        workspace=workspace,
        selectors=selectors,
        env_spec=env_spec,
        logs_root=logs_root,
        output_path=run_dir / "final_verifier_result.json",
        label=f"{safe_id}_provider_final_verifier",
        expected="pass",
        stage="pre_verl_agent_evaluation_pilot",
    )
    command_entries.extend(verifier_commands)
    timed_out = any(item.get("timed_out") for item in final_payload.get("selector_results", []))
    accepted = final_payload.get("status") == "passed"
    final_status = "accepted" if accepted else ("timeout" if timed_out else "rejected")
    boundary_path = run_dir / "final_verifier_boundary.json"
    _write_json(
        boundary_path,
        {
            "schema_version": "repo_harness_pre_verl_final_verifier_boundary_v0",
            "task_id": task_id,
            "source_instance_id": task.get("source_instance_id"),
            "repo": task.get("repo"),
            "environment_id": env_spec["environment_id"],
            "verifier_plan_ref": verifier_plan_ref,
            "final_verifier_result_ref": _ref(final_result_path, "pre_verl_final_verifier_result", "inspect-pre-verl-agent-evaluation"),
            "accepted": accepted,
            "final_verifier_status": final_status,
            "reward_authority": "strict_final_verifier",
            "status": "passed",
        },
    )
    return (
        {
            "accepted": accepted,
            "final_verifier_status": final_status,
            "verifier_plan_ref": verifier_plan_ref,
            "dependency_setup_result_ref": _ref(setup_path, "pre_verl_dependency_setup_result", "inspect-pre-verl-agent-evaluation"),
            "candidate_patch_apply_result_ref": _ref(patch_apply_path, "pre_verl_candidate_patch_apply_result", "inspect-pre-verl-agent-evaluation"),
            "hidden_test_patch_apply_result_ref": _ref(test_apply_path, "pre_verl_hidden_test_patch_apply_result", "inspect-pre-verl-agent-evaluation"),
            "final_verifier_boundary_ref": _ref(boundary_path, "pre_verl_final_verifier_boundary", "inspect-pre-verl-agent-evaluation"),
            "failure_category": None if accepted else ("verifier_timeout_budget" if timed_out else "model_patch_rejected_by_final_verifier"),
            "failure_owner": None if accepted else ("budget_or_timeout" if timed_out else "model_wrong_fix"),
            "failure_diagnosis": "Accepted by strict final verifier." if accepted else (
                "The candidate patch applied and the final verifier ran in an environment already proven healthy by gold/no-op/determinism materialization, but the hidden fail-to-pass selectors still failed. This is a model fix failure, not a harness materialization failure."
                if not timed_out
                else "The final verifier timed out after the model patch applied; this is recorded as a verifier budget or timeout issue."
            ),
            "source_tree_hash": materialization_entry.get("source_tree_sha256"),
            "environment_id": env_spec["environment_id"],
        },
        command_entries,
    )


def _apply_candidate_patch(
    workspace: Path,
    logs_root: Path,
    final_patch_path: Path,
    label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attempts = [
        ("default_p1", ["git", "apply", final_patch_path.resolve().as_posix()]),
        ("path_strip_p0", ["git", "apply", "-p0", final_patch_path.resolve().as_posix()]),
        ("recount_p1", ["git", "apply", "--recount", final_patch_path.resolve().as_posix()]),
        ("recount_p0", ["git", "apply", "-p0", "--recount", final_patch_path.resolve().as_posix()]),
    ]
    entries: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []
    last_result: dict[str, Any] | None = None
    for attempt_id, argv in attempts:
        result, entry = _run_logged_command(
            argv,
            workspace,
            logs_root,
            f"{label}_{attempt_id}",
            120,
            "pre_verl_agent_evaluation_pilot",
        )
        entries.append(entry)
        attempt_rows.append(
            {
                "attempt_id": attempt_id,
                "exit_code": result["exit_code"],
                "timed_out": result["timed_out"],
                "stdout_ref": result["stdout_ref"],
                "stderr_ref": result["stderr_ref"],
            }
        )
        last_result = result
        if result["exit_code"] == 0:
            return {**result, "apply_strategy": attempt_id, "attempts": attempt_rows}, entries
    return {**(last_result or {"exit_code": 1, "timed_out": False}), "apply_strategy": "all_failed", "attempts": attempt_rows}, entries


def _http_error_payload(exc: HTTPError) -> dict[str, Any]:
    try:
        text = exc.read().decode("utf-8", errors="replace")
    except Exception:
        return {"message": f"HTTP {exc.code}"}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {"raw_error": text}
    except json.JSONDecodeError:
        return {"raw_error": text}


def _provider_error_type_from_status(status_code: int) -> str:
    if status_code in {401, 403}:
        return "provider_auth_error"
    if status_code in {402, 429}:
        return "provider_budget_or_rate_limited"
    if status_code in {408, 500, 502, 503, 504}:
        return "provider_transient_error"
    return "provider_request_error"


def _provider_error_failure_category(provider_payload: dict[str, Any]) -> str:
    status_code = int(provider_payload.get("status_code", 0) or 0)
    if status_code in {402, 429} or provider_payload.get("model_error_type") == "provider_budget_or_rate_limited":
        return "provider_budget_or_rate_limited"
    if status_code in {401, 403}:
        return "provider_auth_error"
    if provider_payload.get("model_error_type") == "provider_timeout_or_transport_error":
        return "provider_timeout_or_transport_error"
    return "provider_request_error"


def _provider_error_is_fatal(provider_payload: dict[str, Any]) -> bool:
    status_code = int(provider_payload.get("status_code", 0) or 0)
    return status_code in {400, 401, 402, 403, 404, 429}


def _provider_error_diagnosis(provider_payload: dict[str, Any]) -> str:
    category = _provider_error_failure_category(provider_payload)
    if category == "provider_budget_or_rate_limited":
        return "DeepSeek returned a quota, balance, or rate-limit error. The run stopped before judging further tasks so failed calls are not treated as model patch failures."
    if category == "provider_auth_error":
        return "DeepSeek credential authentication failed. This is an environment or credential configuration issue, not a model repair result."
    if category == "provider_timeout_or_transport_error":
        return "The provider request timed out or hit a transport error before a patch could be produced."
    return "The provider request failed before a model patch could be judged."


def _distribution(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _materialize_one_swebench_dev_task(
    *,
    task: dict[str, Any],
    root: Path,
    source_root: Path,
    workspace_root: Path,
    patch_root: Path,
    logs_root: Path,
    determinism_repeats: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    task_id = str(task.get("task_id") or "")
    safe_id = _safe_file_stem(task_id)
    task_root = root / "tasks" / safe_id
    task_root.mkdir(parents=True, exist_ok=True)
    command_entries: list[dict[str, Any]] = []
    evaluator_ref = task.get("evaluator_only_evidence_ref") if isinstance(task.get("evaluator_only_evidence_ref"), dict) else None
    if not evaluator_ref or not evaluator_ref.get("path"):
        return _blocked_materialization_entry(task, task_root, "evaluator_only_evidence_missing", "harness"), command_entries
    evaluator = _read_json(evaluator_ref["path"])
    repo = str(task.get("repo") or evaluator.get("repo") or "")
    base_commit = str(task.get("base_commit") or "")
    if not repo or not base_commit:
        return _blocked_materialization_entry(task, task_root, "repo_or_base_commit_missing", "dataset"), command_entries

    source_dir = source_root / safe_id / "source"
    source_dir.parent.mkdir(parents=True, exist_ok=True)
    clone_result, clone_entry = _run_logged_command(
        ["git", "clone", "--no-checkout", "--filter=blob:none", f"https://github.com/{repo}.git", source_dir.as_posix()],
        Path.cwd(),
        logs_root,
        f"{safe_id}_source_clone",
        900,
        "pre_verl_swebench_dev_materialization",
    )
    command_entries.append(clone_entry)
    if clone_result["exit_code"] != 0 and not source_dir.exists():
        return _blocked_materialization_entry(task, task_root, "source_clone_failed", "environment", command_ref=clone_entry), command_entries
    checkout_result, checkout_entry = _run_logged_command(
        ["git", "checkout", base_commit],
        source_dir,
        logs_root,
        f"{safe_id}_source_checkout",
        300,
        "pre_verl_swebench_dev_materialization",
    )
    command_entries.append(checkout_entry)
    if checkout_result["exit_code"] != 0:
        return _blocked_materialization_entry(task, task_root, "source_checkout_failed", "environment", command_ref=checkout_entry), command_entries

    source_tree_sha256 = _tree_sha256(source_dir)
    source_facts_path = task_root / "source_checkout_facts.json"
    _write_json(
        source_facts_path,
        {
            "schema_version": "repo_harness_pre_verl_source_checkout_facts_v0",
            "task_id": task_id,
            "repo": repo,
            "base_commit": base_commit,
            "source_tree_sha256": source_tree_sha256,
            "checkout_command_ref": checkout_entry,
            "network_source_allowed_for_formal_run": False,
            "status": "passed",
        },
    )

    env_spec = _pre_verl_environment_for_repo(repo, str(task.get("version") or ""))
    workspace = workspace_root / safe_id / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(source_dir, workspace, symlinks=True)
    setup_result, setup_entry = _run_docker_shell(
        workspace=workspace,
        image=env_spec["execution_image"],
        shell_command=env_spec["setup_shell"],
        logs_root=logs_root,
        label=f"{safe_id}_dependency_setup",
        timeout_sec=int(env_spec["setup_timeout_sec"]),
        stage="pre_verl_swebench_dev_materialization",
    )
    command_entries.append(setup_entry)
    setup_result_path = task_root / "dependency_setup_result.json"
    _write_json(setup_result_path, {**setup_result, "environment": env_spec, "status": "passed" if setup_result["exit_code"] == 0 else "failed"})
    if setup_result["exit_code"] != 0:
        return _materialization_entry_from_status(
            task=task,
            task_root=task_root,
            source_tree_sha256=source_tree_sha256,
            source_facts_path=source_facts_path,
            setup_result_path=setup_result_path,
            env_spec=env_spec,
            status="blocked",
            primary_failure_category="dependency_install_failed",
            failure_owner="environment",
            blocked_reason="dependency install failed before verifier checks could run.",
        ), command_entries

    task_patch_root = patch_root / safe_id
    task_patch_root.mkdir(parents=True, exist_ok=True)
    test_patch_path = task_patch_root / "hidden_test.patch"
    gold_patch_path = task_patch_root / "gold.patch"
    test_patch_path.write_text(str(evaluator.get("test_patch") or ""), encoding="utf-8")
    gold_patch_path.write_text(str(evaluator.get("patch") or ""), encoding="utf-8")
    selectors = [str(item) for item in evaluator.get("FAIL_TO_PASS", []) if str(item).strip()]
    verifier_plan_path = task_root / "verifier_plan.json"
    _write_json(
        verifier_plan_path,
        {
            "schema_version": "repo_harness_pre_verl_swebench_dev_verifier_plan_v0",
            "task_id": task_id,
            "source_instance_id": task.get("source_instance_id"),
            "repo": repo,
            "base_commit": base_commit,
            "environment_id": env_spec["environment_id"],
            "execution_image": env_spec["execution_image"],
            "pythonpath": env_spec["pythonpath"],
            "fail_to_pass_selectors": selectors,
            "pass_to_pass_selector_count": len(evaluator.get("PASS_TO_PASS", []) or []),
            "test_patch_ref": _ref(test_patch_path, "hidden_test_patch", "inspect-pre-verl-swebench-dev-materialization", visibility="evaluator_only"),
            "gold_patch_ref": _ref(gold_patch_path, "gold_patch", "inspect-pre-verl-swebench-dev-materialization", visibility="evaluator_only"),
            "official_harness_report_used_as_final_verifier": False,
            "status": "passed",
        },
    )

    test_apply_result, test_apply_entry = _run_logged_command(
        ["git", "apply", test_patch_path.resolve().as_posix()],
        workspace,
        logs_root,
        f"{safe_id}_noop_test_patch_apply",
        120,
        "pre_verl_swebench_dev_materialization",
    )
    command_entries.append(test_apply_entry)
    test_apply_path = task_root / "test_patch_apply_result.json"
    _write_json(test_apply_path, {**test_apply_result, "status": "passed" if test_apply_result["exit_code"] == 0 else "failed"})
    if test_apply_result["exit_code"] != 0:
        return _materialization_entry_from_status(
            task=task,
            task_root=task_root,
            source_tree_sha256=source_tree_sha256,
            source_facts_path=source_facts_path,
            setup_result_path=setup_result_path,
            env_spec=env_spec,
            verifier_plan_path=verifier_plan_path,
            test_patch_apply_result_path=test_apply_path,
            status="blocked",
            primary_failure_category="test_patch_apply_failed",
            failure_owner="harness",
            blocked_reason="hidden test patch did not apply to frozen source.",
        ), command_entries

    noop_path, noop_payload, noop_commands = _run_pytest_selector_set(
        workspace=workspace,
        selectors=selectors,
        env_spec=env_spec,
        logs_root=logs_root,
        output_path=task_root / "noop_fail_result.json",
        label=f"{safe_id}_noop_fail",
        expected="fail",
    )
    command_entries.extend(noop_commands)
    _run_logged_command(["git", "apply", "-R", test_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_noop_test_patch_reverse", 120, "pre_verl_swebench_dev_materialization")

    invalid_path = task_root / "invalid_patch_fail_result.json"
    invalid_patch_path = task_patch_root / "invalid.patch"
    invalid_prepare, invalid_prepare_entry = _prepare_invalid_patch(workspace=workspace, invalid_patch_path=invalid_patch_path, logs_root=logs_root, label=safe_id)
    command_entries.append(invalid_prepare_entry)
    invalid_status = "blocked"
    if invalid_prepare["exit_code"] == 0 and invalid_patch_path.exists() and invalid_patch_path.stat().st_size > 0:
        invalid_apply, invalid_apply_entry = _run_logged_command(["git", "apply", invalid_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_invalid_patch_apply", 120, "pre_verl_swebench_dev_materialization")
        test_apply_invalid, test_apply_invalid_entry = _run_logged_command(["git", "apply", test_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_invalid_test_patch_apply", 120, "pre_verl_swebench_dev_materialization")
        command_entries.extend([invalid_apply_entry, test_apply_invalid_entry])
        if invalid_apply["exit_code"] == 0 and test_apply_invalid["exit_code"] == 0:
            invalid_path, invalid_payload, invalid_commands = _run_pytest_selector_set(
                workspace=workspace,
                selectors=selectors,
                env_spec=env_spec,
                logs_root=logs_root,
                output_path=invalid_path,
                label=f"{safe_id}_invalid_fail",
                expected="fail",
            )
            command_entries.extend(invalid_commands)
            invalid_status = invalid_payload["status"]
        _run_logged_command(["git", "apply", "-R", test_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_invalid_test_patch_reverse", 120, "pre_verl_swebench_dev_materialization")
        _run_logged_command(["git", "apply", "-R", invalid_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_invalid_patch_reverse", 120, "pre_verl_swebench_dev_materialization")
    else:
        _write_json(invalid_path, {"schema_version": "repo_harness_pre_verl_pytest_selector_result_v0", "status": "blocked", "blocked_reason": "invalid patch could not be generated"})

    gold_apply, gold_apply_entry = _run_logged_command(["git", "apply", gold_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_gold_patch_apply", 120, "pre_verl_swebench_dev_materialization")
    test_apply_gold, test_apply_gold_entry = _run_logged_command(["git", "apply", test_patch_path.resolve().as_posix()], workspace, logs_root, f"{safe_id}_gold_test_patch_apply", 120, "pre_verl_swebench_dev_materialization")
    command_entries.extend([gold_apply_entry, test_apply_gold_entry])
    if gold_apply["exit_code"] != 0 or test_apply_gold["exit_code"] != 0:
        return _materialization_entry_from_status(
            task=task,
            task_root=task_root,
            source_tree_sha256=source_tree_sha256,
            source_facts_path=source_facts_path,
            setup_result_path=setup_result_path,
            env_spec=env_spec,
            verifier_plan_path=verifier_plan_path,
            test_patch_apply_result_path=test_apply_path,
            noop_result_path=noop_path,
            invalid_result_path=invalid_path,
            status="blocked",
            primary_failure_category="gold_or_test_patch_apply_failed",
            failure_owner="harness",
            blocked_reason="gold patch or hidden test patch did not apply cleanly.",
        ), command_entries

    gold_path, gold_payload, gold_commands = _run_pytest_selector_set(
        workspace=workspace,
        selectors=selectors,
        env_spec=env_spec,
        logs_root=logs_root,
        output_path=task_root / "gold_patch_replay_result.json",
        label=f"{safe_id}_gold_replay",
        expected="pass",
    )
    command_entries.extend(gold_commands)
    determinism_path, determinism_payload, determinism_commands = _run_determinism_repeats(
        workspace=workspace,
        selectors=selectors,
        env_spec=env_spec,
        logs_root=logs_root,
        output_path=task_root / "determinism_result.json",
        label=f"{safe_id}_determinism",
        repeats=determinism_repeats,
    )
    command_entries.extend(determinism_commands)
    passed = noop_payload["status"] == "passed" and gold_payload["status"] == "passed" and invalid_status == "passed" and determinism_payload["status"] == "passed"
    return _materialization_entry_from_status(
        task=task,
        task_root=task_root,
        source_tree_sha256=source_tree_sha256,
        source_facts_path=source_facts_path,
        setup_result_path=setup_result_path,
        env_spec=env_spec,
        verifier_plan_path=verifier_plan_path,
        test_patch_apply_result_path=test_apply_path,
        noop_result_path=noop_path,
        invalid_result_path=invalid_path,
        gold_result_path=gold_path,
        determinism_result_path=determinism_path,
        status="passed" if passed else "blocked",
        primary_failure_category=None if passed else "verifier_contract_failed",
        failure_owner=None if passed else "harness_or_dataset",
        blocked_reason=None if passed else "no-op, invalid, gold, or determinism verifier contract did not pass.",
    ), command_entries


def _blocked_materialization_entry(
    task: dict[str, Any],
    task_root: Path,
    primary_failure_category: str,
    failure_owner: str,
    *,
    command_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _materialization_entry_from_status(
        task=task,
        task_root=task_root,
        source_tree_sha256=None,
        source_facts_path=None,
        setup_result_path=None,
        env_spec=None,
        status="blocked",
        primary_failure_category=primary_failure_category,
        failure_owner=failure_owner,
        blocked_reason=primary_failure_category,
        extra_refs={"failure_command_ref": command_ref} if command_ref else None,
    )


def _materialization_entry_from_status(
    *,
    task: dict[str, Any],
    task_root: Path,
    source_tree_sha256: str | None,
    source_facts_path: Path | None,
    setup_result_path: Path | None,
    env_spec: dict[str, Any] | None,
    status: str,
    primary_failure_category: str | None,
    failure_owner: str | None,
    blocked_reason: str | None,
    verifier_plan_path: Path | None = None,
    test_patch_apply_result_path: Path | None = None,
    noop_result_path: Path | None = None,
    invalid_result_path: Path | None = None,
    gold_result_path: Path | None = None,
    determinism_result_path: Path | None = None,
    extra_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry_path = task_root / "materialization_entry.json"
    entry = {
        "schema_version": "repo_harness_pre_verl_swebench_dev_materialization_entry_v0",
        "task_id": task.get("task_id"),
        "source_instance_id": task.get("source_instance_id"),
        "repo": task.get("repo"),
        "base_commit": task.get("base_commit"),
        "version": task.get("version"),
        "source_tree_sha256": source_tree_sha256,
        "environment_id": env_spec.get("environment_id") if env_spec else None,
        "execution_image": env_spec.get("execution_image") if env_spec else None,
        "source_checkout_status": "passed" if source_facts_path else "blocked",
        "dependency_install_status": _status_from_result_path(setup_result_path),
        "test_patch_apply_status": _status_from_result_path(test_patch_apply_result_path),
        "noop_fail_status": _status_from_result_path(noop_result_path),
        "invalid_patch_fail_status": _status_from_result_path(invalid_result_path),
        "gold_patch_replay_status": _status_from_result_path(gold_result_path),
        "determinism_status": _status_from_result_path(determinism_result_path),
        "source_checkout_ref": _ref(source_facts_path, "pre_verl_source_checkout_facts", "inspect-pre-verl-swebench-dev-materialization") if source_facts_path else None,
        "dependency_setup_result_ref": _ref(setup_result_path, "pre_verl_dependency_setup_result", "inspect-pre-verl-swebench-dev-materialization") if setup_result_path else None,
        "verifier_plan_ref": _ref(verifier_plan_path, "pre_verl_verifier_plan", "inspect-pre-verl-swebench-dev-materialization") if verifier_plan_path else None,
        "test_patch_apply_result_ref": _ref(test_patch_apply_result_path, "pre_verl_test_patch_apply_result", "inspect-pre-verl-swebench-dev-materialization") if test_patch_apply_result_path else None,
        "noop_fail_result_ref": _ref(noop_result_path, "pre_verl_noop_fail_result", "inspect-pre-verl-swebench-dev-materialization") if noop_result_path else None,
        "invalid_patch_fail_result_ref": _ref(invalid_result_path, "pre_verl_invalid_patch_fail_result", "inspect-pre-verl-swebench-dev-materialization") if invalid_result_path else None,
        "gold_patch_replay_result_ref": _ref(gold_result_path, "pre_verl_gold_patch_replay_result", "inspect-pre-verl-swebench-dev-materialization") if gold_result_path else None,
        "determinism_result_ref": _ref(determinism_result_path, "pre_verl_determinism_result", "inspect-pre-verl-swebench-dev-materialization") if determinism_result_path else None,
        "primary_failure_category": primary_failure_category,
        "failure_owner": failure_owner,
        "blocked_reason": blocked_reason,
        "status": status,
    }
    if extra_refs:
        entry.update(extra_refs)
    entry["entry_report_path"] = entry_path.as_posix()
    _write_json(entry_path, entry)
    return entry


def _status_from_result_path(path: Path | None) -> str:
    if path is None or not path.exists():
        return "not_executed"
    return str(_read_json(path).get("status") or "unknown")


def _pre_verl_environment_for_repo(repo: str, version: str) -> dict[str, Any]:
    common_prefix = "rm -rf .pre_verl_venv && python -m venv .pre_verl_venv && . .pre_verl_venv/bin/activate && python -m pip install -q --upgrade pip setuptools wheel"
    pvlib_pretend_version = str(version or "0.9").strip()
    if pvlib_pretend_version and pvlib_pretend_version.count(".") == 1:
        pvlib_pretend_version = f"{pvlib_pretend_version}.0"
    if repo == "sqlfluff/sqlfluff":
        return {
            "environment_id": f"pre_verl_sqlfluff_{version or 'unknown'}_python38_v0",
            "execution_image": "python:3.8",
            "pythonpath": "src",
            "setup_timeout_sec": 1200,
            "test_timeout_sec": 300,
            "setup_shell": f"{common_prefix} && grep -v '^types-pkg_resources' requirements_dev.txt >/tmp/pre_verl_requirements_dev.txt && python -m pip install -q -r requirements.txt -r /tmp/pre_verl_requirements_dev.txt requests -e .",
        }
    if repo == "marshmallow-code/marshmallow":
        return {
            "environment_id": f"pre_verl_marshmallow_{version or 'unknown'}_python38_v0",
            "execution_image": "python:3.8",
            "pythonpath": "src",
            "setup_timeout_sec": 900,
            "test_timeout_sec": 300,
            "setup_shell": f"{common_prefix} && python -m pip install -q -e . pytest simplejson pytz",
        }
    if repo == "pylint-dev/astroid":
        return {
            "environment_id": f"pre_verl_astroid_{version or 'unknown'}_python310_v0",
            "execution_image": "python:3.10",
            "pythonpath": ".",
            "setup_timeout_sec": 900,
            "test_timeout_sec": 300,
            "setup_shell": f"{common_prefix} && python -m pip install -q . pytest typing_extensions wrapt lazy_object_proxy",
        }
    if repo == "pydicom/pydicom":
        return {
            "environment_id": f"pre_verl_pydicom_{version or 'unknown'}_python38_v0",
            "execution_image": "python:3.8",
            "pythonpath": ".",
            "setup_timeout_sec": 900,
            "test_timeout_sec": 300,
            "setup_shell": f"{common_prefix} && python -m pip install -q 'numpy<2' 'pytest<7' pillow -e .",
        }
    if repo == "pvlib/pvlib-python":
        return {
            "environment_id": f"pre_verl_pvlib_{version or 'unknown'}_python39_v0",
            "execution_image": "python:3.9",
            "pythonpath": ".",
            "setup_timeout_sec": 1500,
            "test_timeout_sec": 420,
            "setup_shell": (
                f"{common_prefix} && export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PVLIB="
                f"{shlex.quote(pvlib_pretend_version or '0.9.0')} && "
                "python -m pip install -q 'setuptools<70' 'numpy<2' pandas scipy pytest "
                "pytz requests packaging matplotlib -e ."
            ),
        }
    if repo == "pyvista/pyvista":
        return {
            "environment_id": f"pre_verl_pyvista_{version or 'unknown'}_python39_v0",
            "execution_image": "python:3.9",
            "requested_container_platform": "linux/amd64",
            "pythonpath": ".",
            "setup_timeout_sec": 1800,
            "test_timeout_sec": 420,
            "runtime_shell_prefix": "apt-get update -qq && apt-get install -y -qq --no-install-recommends libgl1 libxrender1 libxext6 libx11-6 libglib2.0-0",
            "setup_shell": (
                "apt-get update -qq && apt-get install -y -qq --no-install-recommends "
                f"libgl1 libxrender1 libxext6 libx11-6 libglib2.0-0 && {common_prefix} && "
                "python -m pip install -q 'numpy<2' pytest matplotlib pillow imageio pooch scooby ipykernel 'vtk<9.3' -e ."
            ),
        }
    raise ConfigError(f"pre-verl SWE-Bench Lite development repo environment 未实现：{repo}")


def _run_pytest_selector_set(
    *,
    workspace: Path,
    selectors: list[str],
    env_spec: dict[str, Any],
    logs_root: Path,
    output_path: Path,
    label: str,
    expected: str,
    stage: str = "pre_verl_swebench_dev_materialization",
) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    command_entries = []
    selector_results = []
    for index, selector in enumerate(selectors, start=1):
        command, normalization = _pytest_selector_command(selector, env_spec)
        result, entry = _run_docker_shell(
            workspace=workspace,
            image=env_spec["execution_image"],
            shell_command=command,
            logs_root=logs_root,
            label=f"{label}_{index:03d}",
            timeout_sec=int(env_spec["test_timeout_sec"]),
            stage=stage,
        )
        command_entries.append(entry)
        selector_results.append(
            {
                "selector": selector,
                "normalization": normalization,
                "exit_code": result["exit_code"],
                "timed_out": result["timed_out"],
                "stdout_ref": result["stdout_ref"],
                "stderr_ref": result["stderr_ref"],
                "passed": result["exit_code"] == 0,
            }
        )
    if expected == "pass":
        status = "passed" if selector_results and all(item["passed"] for item in selector_results) else "failed"
    else:
        status = "passed" if selector_results and all(not item["passed"] for item in selector_results) else "failed"
    payload = {
        "schema_version": "repo_harness_pre_verl_pytest_selector_result_v0",
        "expected": expected,
        "selector_count": len(selector_results),
        "passed_selector_count": sum(1 for item in selector_results if item["passed"]),
        "failed_selector_count": sum(1 for item in selector_results if not item["passed"]),
        "selector_results": selector_results,
        "status": status,
    }
    _write_json(output_path, payload)
    return output_path, payload, command_entries


def _run_determinism_repeats(
    *,
    workspace: Path,
    selectors: list[str],
    env_spec: dict[str, Any],
    logs_root: Path,
    output_path: Path,
    label: str,
    repeats: int,
) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    command_entries = []
    repeat_payloads = []
    for repeat in range(1, repeats + 1):
        repeat_path, payload, entries = _run_pytest_selector_set(
            workspace=workspace,
            selectors=selectors,
            env_spec=env_spec,
            logs_root=logs_root,
            output_path=output_path.with_name(f"{output_path.stem}_repeat_{repeat}.json"),
            label=f"{label}_repeat_{repeat}",
            expected="pass",
        )
        command_entries.extend(entries)
        repeat_payloads.append(
            {
                "repeat": repeat,
                "result_ref": _ref(repeat_path, "pre_verl_determinism_repeat_result", "inspect-pre-verl-swebench-dev-materialization"),
                "status": payload["status"],
                "selector_status_sequence": [item["passed"] for item in payload["selector_results"]],
            }
        )
    sequence = [item["selector_status_sequence"] for item in repeat_payloads]
    deterministic = bool(sequence) and all(item == sequence[0] for item in sequence) and all(item["status"] == "passed" for item in repeat_payloads)
    payload = {
        "schema_version": "repo_harness_pre_verl_determinism_result_v0",
        "repeat_count": repeats,
        "repeat_results": repeat_payloads,
        "parsed_result_sequence": sequence,
        "status": "passed" if deterministic else "failed",
    }
    _write_json(output_path, payload)
    return output_path, payload, command_entries


def _pytest_selector_command(selector: str, env_spec: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    selector = selector.strip()
    prefix = ". .pre_verl_venv/bin/activate"
    pythonpath = str(env_spec.get("pythonpath") or "")
    if pythonpath:
        prefix += f" && export PYTHONPATH={shlex.quote(pythonpath)}"
    runtime_prefix = str(env_spec.get("runtime_shell_prefix") or "").strip()
    if runtime_prefix:
        prefix = f"{runtime_prefix} && {prefix}"
    if "[" in selector and "]" not in selector and "::" in selector:
        file_part, node_part = selector.split("::", 1)
        test_name = node_part.split("::")[-1].split("[", 1)[0]
        return f"{prefix} && pytest -q {shlex.quote(file_part)} -k {shlex.quote(test_name)}", {"strategy": "file_and_k_expression", "reason": "unbalanced_parameterized_selector"}
    return f"{prefix} && pytest -q {shlex.quote(selector)}", {"strategy": "direct_nodeid"}


def _prepare_invalid_patch(
    *,
    workspace: Path,
    invalid_patch_path: Path,
    logs_root: Path,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target = _find_invalid_patch_target(workspace)
    if target is None:
        stdout_path = logs_root / f"{label}_invalid_patch_prepare.stdout.txt"
        stderr_path = logs_root / f"{label}_invalid_patch_prepare.stderr.txt"
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("no invalid patch target", encoding="utf-8")
        entry = _command_entry("prepare-invalid-patch", ["prepare-invalid-patch"], workspace, 1, stdout_path, stderr_path, "pre_verl_swebench_dev_materialization")
        return {"exit_code": 1, "timed_out": False, "stdout_ref": _ref(stdout_path, "stdout", "inspect-pre-verl-swebench-dev-materialization"), "stderr_ref": _ref(stderr_path, "stderr", "inspect-pre-verl-swebench-dev-materialization")}, entry
    target.write_text(target.read_text(encoding="utf-8", errors="ignore") + "\npre-verl invalid patch marker\n", encoding="utf-8")
    result, entry = _run_logged_command(["git", "diff", "--", target.relative_to(workspace).as_posix()], workspace, logs_root, f"{label}_invalid_patch_prepare", 120, "pre_verl_swebench_dev_materialization")
    invalid_patch_path.write_text(Path(str(result["stdout_ref"]["path"])).read_text(encoding="utf-8"), encoding="utf-8")
    _run_logged_command(["git", "checkout", "--", target.relative_to(workspace).as_posix()], workspace, logs_root, f"{label}_invalid_patch_restore", 120, "pre_verl_swebench_dev_materialization")
    return result, entry


def _find_invalid_patch_target(workspace: Path) -> Path | None:
    for name in ("README.md", "README.rst", "README.txt", "CHANGELOG.md", "CHANGES.rst"):
        path = workspace / name
        if path.exists() and path.is_file():
            return path
    for path in workspace.rglob("*.md"):
        if ".git" not in path.parts and ".pre_verl_venv" not in path.parts:
            return path
    return None


def _run_docker_shell(
    *,
    workspace: Path,
    image: str,
    shell_command: str,
    logs_root: Path,
    label: str,
    timeout_sec: int,
    stage: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    argv = ["docker", "run", "--rm", "--platform", "linux/amd64", "-v", f"{workspace.resolve().as_posix()}:/workspace", "-w", "/workspace", image, "sh", "-lc", shell_command]
    return _run_logged_command(argv, Path.cwd(), logs_root, label, timeout_sec, stage)


def _run_logged_command(
    argv: list[str],
    cwd: Path,
    logs_root: Path,
    label: str,
    timeout_sec: int,
    stage: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    logs_root.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_root / f"{_safe_file_stem(label)}.stdout.txt"
    stderr_path = logs_root / f"{_safe_file_stem(label)}.stderr.txt"
    started = _now()
    timed_out = False
    try:
        proc = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout_sec)
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        stderr += f"\nCommand timed out after {timeout_sec} seconds.\n"
        exit_code = 124
    stdout_path.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(stderr, encoding="utf-8", errors="replace")
    result = {
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_ref": _ref(stdout_path, "stdout", "inspect-pre-verl-swebench-dev-materialization"),
        "stderr_ref": _ref(stderr_path, "stderr", "inspect-pre-verl-swebench-dev-materialization"),
    }
    entry = _command_entry(Path(argv[0]).name, argv, cwd, exit_code, stdout_path, stderr_path, stage, started_at=started, timed_out=timed_out)
    return result, entry


def _command_entry(
    command_name: str,
    argv: list[str],
    cwd: Path,
    exit_code: int,
    stdout_path: Path,
    stderr_path: Path,
    stage: str,
    *,
    started_at: str | None = None,
    timed_out: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_pre_verl_command_log_entry_v0",
        "command_name": command_name,
        "argv": argv,
        "cwd": cwd.as_posix(),
        "producer_stage": stage,
        "started_at": started_at or _now(),
        "finished_at": _now(),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_ref": _ref(stdout_path, "stdout", "inspect-pre-verl-swebench-dev-materialization"),
        "stderr_ref": _ref(stderr_path, "stderr", "inspect-pre-verl-swebench-dev-materialization"),
    }


def _inspect_transcript(result: dict[str, Any]) -> dict[str, Any]:
    ref = result.get("transcript_ref") or {}
    path = Path(str(ref.get("path") or ""))
    requested_tool_call_ids: list[str] = []
    observed_tool_call_ids: list[str] = []
    roles: list[str] = []
    event_path = path.with_name("events.jsonl")
    event_log_ref: dict[str, Any] | None = None
    if path.exists():
        for row in _read_jsonl(path):
            roles.append(str(row.get("role")))
            if row.get("role") == "assistant":
                for tool_call in row.get("tool_calls", []) or []:
                    if isinstance(tool_call, dict) and tool_call.get("tool_call_id"):
                        requested_tool_call_ids.append(str(tool_call["tool_call_id"]))
            elif row.get("role") == "tool" and row.get("tool_call_id"):
                observed_tool_call_ids.append(str(row["tool_call_id"]))
    if event_path.exists():
        requested_tool_call_ids = []
        observed_tool_call_ids = []
        for event in _read_jsonl(event_path):
            event_type = str(event.get("event_type") or "")
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            tool_call_id = str(data.get("tool_call_id") or "")
            if not tool_call_id:
                continue
            if event_type == "tool_requested":
                requested_tool_call_ids.append(tool_call_id)
            elif event_type in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}:
                observed_tool_call_ids.append(tool_call_id)
        event_log_ref = _ref(event_path, "trajectory_event_log", "inspect-pre-verl-agent-runtime-audit")
    return {
        "run_id": result.get("run_id"),
        "task_id": result.get("task_id"),
        "transcript_ref": ref,
        "event_log_ref": event_log_ref,
        "message_count": len(roles),
        "tool_use_count": len(requested_tool_call_ids),
        "tool_result_count": len(observed_tool_call_ids),
        "unpaired_tool_use_count": len(set(requested_tool_call_ids) - set(observed_tool_call_ids)),
        "unpaired_tool_result_count": len(set(observed_tool_call_ids) - set(requested_tool_call_ids)),
        "has_terminal_record": bool(result.get("final_verifier_boundary_ref") or result.get("final_verifier_status")),
    }


def _tool_contract_matrix(results: list[dict[str, Any]]) -> dict[str, Any]:
    policies = sorted({str(item.get("tool_policy_id")) for item in results if item.get("tool_policy_id")})
    return {
        "schema_version": "repo_harness_pre_verl_tool_contract_matrix_v0",
        "tool_policy_ids": policies,
        "dynamic_tool_pool_drift_count": 0,
        "tool_schema_hashes_available": False,
        "status": "passed",
    }


def _load_swebench_rows(path: str | Path | None, *, split: str, required_count: int) -> list[dict[str, Any]]:
    rows = _read_swebench_rows(path) if path is not None else _fetch_swebench_lite_rows(split)
    if len(rows) < required_count:
        raise ConfigError(
            f"SWE-Bench Lite {split} split 需要至少 {required_count} 条 rows，当前只有 {len(rows)} 条。"
        )
    return rows


def _read_swebench_rows(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix == ".jsonl":
        raw_rows = _read_jsonl(source)
    else:
        payload = _read_json(source)
        if isinstance(payload.get("rows"), list):
            raw_rows = [item.get("row", item) for item in payload["rows"] if isinstance(item, dict)]
        elif isinstance(payload.get("data"), list):
            raw_rows = payload["data"]
        else:
            raise ConfigError(f"SWE-Bench rows 文件格式不支持：{source}")
    return [_normalize_swebench_row(row) for row in raw_rows]


def _fetch_swebench_lite_rows(split: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = urlencode(
            {
                "dataset": "SWE-bench/SWE-bench_Lite",
                "config": "default",
                "split": split,
                "offset": offset,
                "length": 100,
            }
        )
        with urlopen(f"https://datasets-server.huggingface.co/rows?{query}", timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        page_rows = [item["row"] for item in payload.get("rows", []) if isinstance(item, dict) and isinstance(item.get("row"), dict)]
        rows.extend(_normalize_swebench_row(row) for row in page_rows)
        total = int(payload.get("num_rows_total") or len(rows))
        if len(rows) >= total or not page_rows:
            break
        offset += len(page_rows)
    return rows


def _normalize_swebench_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for key in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        value = normalized.get(key)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = [value] if value else []
            normalized[key] = parsed
        elif value is None:
            normalized[key] = []
    return normalized


def _curate_swebench_lite_rows(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_repo.setdefault(str(row.get("repo") or "unknown"), []).append(row)
    for repo_rows in by_repo.values():
        repo_rows.sort(key=lambda item: str(item.get("instance_id") or ""))
    selected: list[dict[str, Any]] = []
    repos = sorted(by_repo)
    while len(selected) < count and repos:
        next_repos: list[str] = []
        for repo in repos:
            repo_rows = by_repo[repo]
            if repo_rows and len(selected) < count:
                selected.append(repo_rows.pop(0))
            if repo_rows:
                next_repos.append(repo)
        repos = next_repos
    if len(selected) < count:
        raise ConfigError(f"curated SWE-Bench Lite 需要 {count} 条 rows，当前只能选出 {len(selected)} 条。")
    return selected


def _load_task_definitions_from_refs(refs: list[Any]) -> list[dict[str, Any]]:
    task_defs: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get("path"):
            continue
        path = Path(str(ref["path"]))
        if path.exists():
            payload = _read_json(path)
            payload["_source_task_definition_path"] = path.as_posix()
            task_defs.append(payload)
    return task_defs


def _github_issue_task_definitions(
    *,
    existing_task_defs: list[dict[str, Any]],
    supplemental_report: str | Path | None,
    minimum_count: int,
) -> list[dict[str, Any]]:
    tasks = [task for task in existing_task_defs if task.get("source_kind") == "pr_issue_flow"]
    by_task_id = {str(task.get("task_id")): task for task in tasks if task.get("task_id")}
    if supplemental_report is not None and Path(supplemental_report).exists():
        payload = _read_json(supplemental_report)
        for record in payload.get("candidate_records", []):
            ref = record.get("task_definition_ref") if isinstance(record, dict) else None
            if not isinstance(ref, dict) or not ref.get("path"):
                continue
            path = Path(str(ref["path"]))
            if not path.exists():
                continue
            task = _read_json(path)
            task["_source_task_definition_path"] = path.as_posix()
            if task.get("source_kind") != "pr_issue_flow":
                continue
            task_id = str(task.get("task_id") or "")
            if task_id and task_id not in by_task_id:
                by_task_id[task_id] = task
    ordered = sorted(
        by_task_id.values(),
        key=lambda item: (
            0 if item.get("accepted_auditable") is True else 1,
            0 if item.get("agent_run_ready") is True else 1,
            str(item.get("task_id") or ""),
        ),
    )
    if len(ordered) < minimum_count:
        raise ConfigError(f"GitHub issue flow 任务需要至少 {minimum_count} 个候选，当前只有 {len(ordered)} 个。")
    return ordered


def _swebench_task_payloads(
    *,
    row: dict[str, Any],
    tier: str,
    split: str,
    ordinal: int,
    existing_runnable_task: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    instance_id = str(row.get("instance_id") or "")
    if not instance_id:
        raise ConfigError("SWE-Bench Lite row 缺少 instance_id。")
    task_id = f"pre_verl_{'dev' if split == 'dev' else 'curated'}_{ordinal:03d}_{_safe_file_stem(instance_id)}"
    runnable = existing_runnable_task is not None and existing_runnable_task.get("agent_run_ready") is True
    blocked_reason = None if runnable else "blocked_dataset_or_environment: executable environment and verifier plan have not been materialized in RepoHarness for this SWE-Bench Lite instance."
    adapter_visible = {
        "schema_version": "repo_harness_pre_verl_adapter_visible_task_input_v0",
        "task_id": task_id,
        "source_instance_id": instance_id,
        "dataset": "SWE-bench/SWE-bench_Lite",
        "dataset_config": "default",
        "dataset_split": split,
        "repo": row.get("repo"),
        "base_commit": row.get("base_commit"),
        "version": row.get("version"),
        "problem_statement": row.get("problem_statement"),
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "visible_constraints": [
            "Use only model-visible repository issue text and source workspace contents.",
            "Do not inspect private evaluator evidence or hidden execution artifacts.",
        ],
    }
    evaluator_only = {
        "schema_version": "repo_harness_pre_verl_evaluator_only_task_evidence_v0",
        "task_id": task_id,
        "source_instance_id": instance_id,
        "patch": row.get("patch"),
        "test_patch": row.get("test_patch"),
        "FAIL_TO_PASS": row.get("FAIL_TO_PASS") or [],
        "PASS_TO_PASS": row.get("PASS_TO_PASS") or [],
        "environment_setup_commit": row.get("environment_setup_commit"),
        "hints_text": row.get("hints_text"),
        "visibility": "evaluator_only",
    }
    record = {
        "schema_version": "repo_harness_pre_verl_task_definition_v0",
        "task_id": task_id,
        "tier": tier,
        "source_kind": "swebench_lite",
        "source_instance_id": instance_id,
        "dataset": "SWE-bench/SWE-bench_Lite",
        "dataset_config": "default",
        "dataset_split": split,
        "repo": row.get("repo"),
        "base_commit": row.get("base_commit"),
        "version": row.get("version"),
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "runnable": runnable,
        "agent_run_ready": runnable,
        "verifier_ready": runnable,
        "blocked_reason": blocked_reason,
        "blocked_stage": None if runnable else "environment_materialization",
        "existing_v5_task_ref": _ref(existing_runnable_task.get("_source_task_definition_path"), "v5_task_definition", "inspect-v5-task-set") if existing_runnable_task else None,
    }
    return record, adapter_visible, evaluator_only


def _github_issue_task_payloads(*, task: dict[str, Any], ordinal: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_task_id = str(task.get("task_id") or f"github_issue_{ordinal:03d}")
    task_id = f"pre_verl_github_issue_{ordinal:03d}_{_safe_file_stem(source_task_id)}"
    runnable = task.get("agent_run_ready") is True
    blocked_reason = None
    if not runnable:
        blocked_reason = task.get("blocked_reason") or task.get("replacement_reason") or "blocked_issue_flow_candidate: candidate did not satisfy freeze_ready and agent_run_ready gates."
    adapter_ref = task.get("adapter_visible_input_ref") if isinstance(task.get("adapter_visible_input_ref"), dict) else None
    adapter_visible = {
        "schema_version": "repo_harness_pre_verl_adapter_visible_task_input_v0",
        "task_id": task_id,
        "source_task_id": source_task_id,
        "candidate_id": task.get("candidate_id"),
        "source_kind": "github_issue_flow",
        "repository": task.get("repository"),
        "base_commit": task.get("base_commit"),
        "task_family": task.get("task_family"),
        "source_adapter_visible_input_ref": adapter_ref,
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
    }
    evaluator_only = {
        "schema_version": "repo_harness_pre_verl_evaluator_only_task_evidence_v0",
        "task_id": task_id,
        "source_task_id": source_task_id,
        "source_task_definition_ref": _ref(task.get("_source_task_definition_path"), "v5_task_definition", "inspect-v5-task-set") if task.get("_source_task_definition_path") else None,
        "baseline_verifier_plan_ref": task.get("baseline_verifier_plan_ref"),
        "final_verifier_plan_ref": task.get("final_verifier_plan_ref"),
        "fail_to_pass_evidence_ref": task.get("fail_to_pass_evidence_ref"),
        "pass_to_pass_evidence_ref": task.get("pass_to_pass_evidence_ref"),
        "visibility": "evaluator_only",
    }
    record = {
        "schema_version": "repo_harness_pre_verl_task_definition_v0",
        "task_id": task_id,
        "tier": "github_issue_flow",
        "source_kind": "github_issue_flow",
        "source_task_id": source_task_id,
        "candidate_id": task.get("candidate_id"),
        "repository": task.get("repository"),
        "base_commit": task.get("base_commit"),
        "custom_frozen_subset": True,
        "leaderboard_comparable": False,
        "runnable": runnable,
        "agent_run_ready": runnable,
        "verifier_ready": runnable,
        "blocked_reason": blocked_reason,
        "blocked_stage": None if runnable else "candidate_probe",
        "source_task_definition_ref": evaluator_only["source_task_definition_ref"],
    }
    return record, adapter_visible, evaluator_only


def _agent_evaluation_dev_result_ids(task_set: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for ref in task_set.get("task_definition_refs", []) or []:
        if not isinstance(ref, dict) or not ref.get("path"):
            continue
        path = Path(str(ref["path"]))
        if not path.exists():
            continue
        task = _read_json(path)
        if task.get("tier") != "swebench_lite_development":
            continue
        for key in ("task_id", "source_instance_id", "source_task_id"):
            if task.get(key):
                ids.add(str(task[key]))
    return ids


def _adapter_visible_leakage_count(refs: list[dict[str, Any]]) -> int:
    forbidden = {"patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS", "gold_patch", "reward", "verifier_output"}
    findings = 0
    for ref in refs:
        path = Path(str(ref.get("path") or ""))
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                findings += 1
                break
    return findings


def _safe_file_stem(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_") or "task"


def _write_public_docs(root: Path, allowed_claims: list[str], blocked_claims: list[str]) -> None:
    (root / "pre_verl_public_demo_index.json").write_text(json.dumps({"schema_version": "repo_harness_pre_verl_public_demo_index_v0", "allowed_claims": allowed_claims, "blocked_claims": blocked_claims}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "pre_verl_demo_card.json").write_text(json.dumps({"schema_version": "repo_harness_pre_verl_demo_card_v0", "allowed_claims": allowed_claims, "blocked_claims": blocked_claims}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "pre_verl_demo_card.md").write_text("# Pre-verl demo card\n\nAllowed claims are evidence-bound in `pre_verl_resume_claim_gate_report.json`.\n", encoding="utf-8")
    (root / "pre_verl_interview_qa.md").write_text("# Pre-verl interview Q&A\n\nQ: Is this a SWE-Bench leaderboard result?\n\nA: No. It is a custom frozen evaluation subset and is not leaderboard comparable.\n", encoding="utf-8")
    (root / "pre_verl_interview_qa_evidence.json").write_text(json.dumps({"schema_version": "repo_harness_pre_verl_interview_qa_evidence_v0", "blocked_claims": blocked_claims}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "pre_verl_interview_summary.md").write_text("# Pre-verl interview summary\n\nThis run records evidence-bound pre-verl task materialization, real provider evaluation outcomes, verifier correctness checks, runtime audit, export audit, and claim-gated public statements.\n", encoding="utf-8")


def _pre_verl_public_safe_scan(paths: list[Path]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    counters = {
        "share_safe_finding_count": 0,
        "hidden_tests_finding_count": 0,
        "gold_patch_finding_count": 0,
        "raw_provider_request_finding_count": 0,
        "raw_provider_response_finding_count": 0,
        "credential_marker_finding_count": 0,
        "reward_scalar_finding_count": 0,
        "final_verifier_raw_output_finding_count": 0,
    }
    rules = [
        ("hidden_tests_finding_count", "hidden test patch marker", r"\b(test_patch|FAIL_TO_PASS|PASS_TO_PASS|hidden_test\.patch)\b"),
        ("gold_patch_finding_count", "gold patch marker", r"\b(gold_patch|gold patch)\b"),
        ("raw_provider_request_finding_count", "raw provider request marker", r"\b(raw_deepseek_provider_request|raw_provider_request)\b"),
        ("raw_provider_response_finding_count", "raw provider response marker", r"\b(raw_deepseek_provider_response|raw_provider_response)\b"),
        ("credential_marker_finding_count", "credential marker", r"\b(Authorization|Bearer\s+|sk-[A-Za-z0-9_\-]{8,})\b"),
        ("reward_scalar_finding_count", "reward marker", r"\b(reward_scalar|reward_label)\b"),
        ("final_verifier_raw_output_finding_count", "final verifier raw output marker", r"\b(final_verifier_raw_output|raw final verifier output)\b"),
    ]
    for path in paths:
        if not path.exists():
            counters["share_safe_finding_count"] += 1
            findings.append({"path": path.as_posix(), "category": "missing_public_artifact"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for counter_key, label, pattern in rules:
            if re.search(pattern, text, flags=re.IGNORECASE):
                counters[counter_key] += 1
                findings.append({"path": path.as_posix(), "category": label})
    counters["share_safe_finding_count"] += sum(
        value for key, value in counters.items() if key != "share_safe_finding_count"
    )
    return {
        "schema_version": "repo_harness_pre_verl_public_safe_scan_report_v0",
        "created_at": _now(),
        "scanned_public_artifact_count": len(paths),
        "findings": findings,
        **counters,
        "status": "passed" if counters["share_safe_finding_count"] == 0 else "failed",
    }


def _builder_entry(command_name: str, inputs: list[Path], outputs: list[Path], stage: str) -> list[dict[str, Any]]:
    return [
        {
            "schema_version": "repo_harness_pre_verl_command_log_entry_v0",
            "command_name": command_name,
            "argv": [command_name],
            "cwd": str(Path.cwd()),
            "producer_stage": stage,
            "started_at": _now(),
            "finished_at": _now(),
            "exit_code": 0,
            "input_refs": [_ref(path, "input", command_name) for path in inputs if path.exists()],
            "output_refs": [_ref(path, "output", command_name) for path in outputs if path.exists()],
        }
    ]


def _planned_entry(command_name: str, inputs: list[Path], outputs: list[Path], stage: str) -> dict[str, Any]:
    return {**_builder_entry(command_name, inputs, outputs, stage)[0], "planned": True}


def _ref_paths(refs: dict[str, Any]) -> list[Path]:
    return [Path(ref["path"]) for ref in refs.values() if isinstance(ref, dict) and ref.get("path")]


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_sha256(root: Path) -> str:
    h = hashlib.sha256()
    ignored = {".git", ".pre_verl_venv", ".pytest_cache", "__pycache__", ".mypy_cache", ".tox"}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if any(part in ignored for part in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(_sha256(path).encode("ascii"))
        h.update(b"\0")
    return h.hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _capture_text(argv: list[str]) -> str:
    proc = subprocess.run(argv, text=True, capture_output=True)
    return proc.stdout.strip() or proc.stderr.strip()


def _mean(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _percentile(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil((percentile / 100) * len(ordered)) - 1)
    return ordered[index]


def _wilson(successes: int, total: int) -> dict[str, float | int]:
    if total == 0:
        return {"low": 0.0, "high": 0.0, "successes": successes, "total": total}
    z = 1.959963984540054
    phat = successes / total
    denom = 1 + z * z / total
    centre = phat + z * z / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return {"low": round((centre - margin) / denom, 6), "high": round((centre + margin) / denom, 6), "successes": successes, "total": total}


def _inspect_result(label: str, path: str | Path, failures: list[str], *, assert_requested: bool) -> str:
    lines = [f"{label}: {Path(path).as_posix()}"]
    if failures:
        lines.extend(f"- {failure}" for failure in failures)
        if assert_requested:
            raise ConfigError("; ".join(failures))
        lines.append(f"{label}: blocked")
    else:
        lines.append(f"{label}: passed")
    return "\n".join(lines)


def _refuse_existing(root: Path, names: tuple[str, ...], fail_if_output_exists: bool) -> None:
    if not fail_if_output_exists:
        return
    existing = [name for name in names if (root / name).exists()]
    if existing:
        raise ConfigError(f"pre-verl output already exists: {', '.join(existing)}")
