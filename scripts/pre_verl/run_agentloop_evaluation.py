#!/usr/bin/env python3
"""Prepare or execute pre-verl AgentLoop evaluation through repo-harness run-task."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from repo_harness.config import load_run_config  # noqa: E402
from repo_harness.pre_verl_agentloop import (  # noqa: E402
    PRE_VERL_AGENTLOOP_ADAPTER_ID,
    PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
    PRE_VERL_AGENTLOOP_BOUNDARY_INDEX_VERSION,
    PRE_VERL_AGENTLOOP_MODE,
)
from repo_harness.pre_verl_evaluation import _pre_verl_environment_for_repo  # noqa: E402
from repo_harness.scaffolds import build_scaffold, resolve_allowed_tools, resolve_feedback_policy  # noqa: E402
from repo_harness.tasks import TaskAdapter  # noqa: E402


SMOKE_TASK_IDS = [
    "pre_verl_dev_001_sqlfluff__sqlfluff_1625",
    "pre_verl_dev_006_marshmallow_code__marshmallow_1359",
    "pre_verl_dev_009_pvlib__pvlib_python_1072",
    "pre_verl_dev_013_pylint_dev__astroid_1978",
    "pre_verl_dev_020_pydicom__pydicom_1413",
]
FORBIDDEN_SCAFFOLD_IDS = ["single_shot_patch_no_tools"]


@dataclass(frozen=True)
class SelectedTask:
    task_id: str
    source_record_path: Path
    source_record: dict[str, Any]
    adapter_visible_input: dict[str, Any]
    evaluator_only_evidence: dict[str, Any]
    materialization_entry: dict[str, Any]
    verifier_plan: dict[str, Any]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and not args.allow_existing_output:
        raise SystemExit(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    task_set_manifest_path = Path(args.pre_verl_task_set_manifest).resolve()
    task_set_manifest = _read_json(task_set_manifest_path)
    selected = _select_tasks(task_set_manifest, task_set_manifest_path, args)

    command_log_path = output_dir / "pre_verl_agentloop_external_command_log.jsonl"
    command_log_path.touch()
    logs_dir = output_dir / "command_logs"
    tasks_dir = output_dir / "task_definitions"
    configs_dir = output_dir / "run_configs"
    selectors_dir = output_dir / "selector_refs"
    runs_dir = output_dir / "run_task_runs"
    for directory in (logs_dir, tasks_dir, configs_dir, selectors_dir, runs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for task in selected:
        task_path, selector_refs = _write_task_definition(
            task=task,
            task_set_manifest_path=task_set_manifest_path,
            tasks_dir=tasks_dir,
            selectors_dir=selectors_dir,
        )
        config_path = _write_run_config(
            task=task,
            config_path=configs_dir / f"{task.task_id}_{args.provider}_{args.model_id}.yaml",
            output_dir=runs_dir,
            args=args,
        )
        loaded = TaskAdapter().load(task_path)
        run_config = load_run_config(config_path)
        scaffold = build_scaffold(run_config.runtime.scaffold_id)
        feedback_policy = resolve_feedback_policy(
            run_config=run_config,
            scaffold=scaffold,
            task=loaded.runnable_task,
        )
        resolved_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
        run_id = f"{args.run_id_prefix}_{task.task_id}_{args.provider}_{_safe_id(args.model_id)}"
        entries.append(
            {
                "task_id": task.task_id,
                "source_instance_id": task.source_record.get("source_instance_id"),
                "repo": task.source_record.get("repo"),
                "tier": task.source_record.get("tier"),
                "task_definition_ref": _file_ref(task_path),
                "run_config_ref": _file_ref(config_path),
                "selector_refs": selector_refs,
                "scaffold_id": args.scaffold_id,
                "provider": args.provider,
                "model_id": args.model_id,
                "test_feedback_policy": args.test_feedback_policy,
                "resolved_tools": resolved_tools,
                "run_id": run_id,
                "run_task_run_dir": (runs_dir / run_id).as_posix(),
                "status": "planned",
            }
        )

    task_manifest_path = output_dir / "pre_verl_agentloop_task_definition_manifest.json"
    _write_json(
        task_manifest_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_task_definition_manifest_v0",
            "created_at": _timestamp(),
            "pre_verl_adapter": PRE_VERL_AGENTLOOP_ADAPTER_ID,
            "pre_verl_swebench_dev_manifest_path": task_set_manifest_path.as_posix(),
            "pre_verl_agentloop_mode": PRE_VERL_AGENTLOOP_MODE,
            "pre_verl_agentloop_baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
            "mode": args.mode,
            "selected_task_count": len(entries),
            "task_definition_refs": [entry["task_definition_ref"] for entry in entries],
            "entries": entries,
        },
    )
    run_config_manifest_path = output_dir / "pre_verl_agentloop_run_config_manifest.json"
    _write_json(
        run_config_manifest_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_run_config_manifest_v0",
            "created_at": _timestamp(),
            "mode": args.mode,
            "baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
            "forbidden_scaffold_ids": FORBIDDEN_SCAFFOLD_IDS,
            "entries": entries,
        },
    )
    configuration_manifest_path = _write_configuration_manifests(
        output_dir=output_dir,
        task_set_manifest_path=task_set_manifest_path,
        entries=entries,
        args=args,
    )

    _run_checked_command(
        [
            *args.repo_harness_argv,
            "inspect-pre-verl-agentloop-task-definitions",
            task_manifest_path.as_posix(),
            "--assert-run-task-compatible",
            "--assert-evaluator-only-hidden-inputs",
            "--assert-no-hidden-material-in-model-visible-fields",
        ],
        cwd=REPO_ROOT,
        logs_dir=logs_dir,
        command_log_path=command_log_path,
        command_name="inspect-pre-verl-agentloop-task-definitions",
    )
    _run_checked_command(
        [
            *args.repo_harness_argv,
            "inspect-pre-verl-agentloop-run-config",
            run_config_manifest_path.as_posix(),
            "--assert-final-only-test-feedback-disabled",
            "--assert-resolved-tools-derived",
            "--assert-no-hidden-feedback-visible",
        ],
        cwd=REPO_ROOT,
        logs_dir=logs_dir,
        command_log_path=command_log_path,
        command_name="inspect-pre-verl-agentloop-run-config",
    )

    if args.execute:
        for entry in entries:
            command = [
                *args.repo_harness_argv,
                "run-task",
                entry["task_definition_ref"]["path"],
                "--config",
                entry["run_config_ref"]["path"],
                "--output-dir",
                runs_dir.as_posix(),
                "--run-id",
                entry["run_id"],
            ]
            result, entry_path = _run_logged_command(
                command,
                cwd=REPO_ROOT,
                logs_dir=logs_dir,
                command_log_path=command_log_path,
                command_name="run-task",
                input_refs=[entry["task_definition_ref"], entry["run_config_ref"]],
            )
            entry["run_task_command_log_entry_ref"] = _file_ref(entry_path)
            entry["status"] = "executed" if result.returncode == 0 else "command_failed"
            entry["run_task_exit_code"] = result.returncode
            if result.returncode != 0 and not args.continue_on_task_command_failure:
                _write_run_matrix(output_dir, entries, args)
                raise SystemExit(result.returncode)
        boundary_index_path = _write_boundary_index(output_dir, entries)
        _run_checked_command(
            [
                *args.repo_harness_argv,
                "inspect-pre-verl-agentloop-boundary-index",
                boundary_index_path.as_posix(),
                "--assert-all-formal-runs-bound",
                "--assert-command-order",
                "--assert-clean-source-origin",
                "--assert-run-task-lineage",
                "--assert-no-legacy-adapter",
            ],
            cwd=REPO_ROOT,
            logs_dir=logs_dir,
            command_log_path=command_log_path,
            command_name="inspect-pre-verl-agentloop-boundary-index",
        )

    run_matrix_path = _write_run_matrix(output_dir, entries, args)
    print(
        json.dumps(
            {
                "status": "prepared_and_executed" if args.execute else "prepared",
                "configuration_manifest": configuration_manifest_path.as_posix(),
                "task_definition_manifest": task_manifest_path.as_posix(),
                "run_config_manifest": run_config_manifest_path.as_posix(),
                "run_matrix_manifest": run_matrix_path.as_posix(),
                "command_log": command_log_path.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre-verl-task-set-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=["smoke", "formal"], default="smoke")
    parser.add_argument("--task-id", action="append", default=[])
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--model-id", default="deepseek-v4-flash")
    parser.add_argument("--scaffold-id", default="patch_focused_react")
    parser.add_argument("--test-feedback-policy", default="disabled")
    parser.add_argument("--run-id-prefix", default="pre_verl_agentloop")
    parser.add_argument("--execution-mode", choices=["local_process", "docker"], default="local_process")
    parser.add_argument("--permission-mode", choices=["plan", "ask", "auto", "deny"], default="auto")
    parser.add_argument("--max-turns", type=int, default=24)
    parser.add_argument("--max-tool-calls", type=int, default=96)
    parser.add_argument("--max-test-runs", type=int, default=0)
    parser.add_argument("--task-timeout-sec", type=int, default=1200)
    parser.add_argument("--command-timeout-sec", type=int, default=90)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-local-secret-file", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--repo-harness-bin", default="repo-harness")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--continue-on-task-command-failure", action="store_true")
    parser.add_argument("--allow-existing-output", action="store_true")
    args = parser.parse_args(argv)
    args.repo_harness_argv = shlex.split(args.repo_harness_bin)
    if not args.repo_harness_argv:
        parser.error("--repo-harness-bin 不能为空")
    if args.scaffold_id in FORBIDDEN_SCAFFOLD_IDS:
        parser.error("formal pre-verl AgentLoop baseline 不能使用 single_shot_patch_no_tools")
    if args.test_feedback_policy != "disabled":
        parser.error("formal pre-verl final-only 任务必须使用 test_feedback_policy=disabled")
    if args.max_test_runs != 0:
        parser.error("formal pre-verl final-only 任务必须设置 max_test_runs=0")
    return args


def _select_tasks(
    manifest: dict[str, Any],
    manifest_path: Path,
    args: argparse.Namespace,
) -> list[SelectedTask]:
    records = []
    for ref in manifest.get("task_definition_refs", []):
        path = _path_from_ref(ref, manifest_path.parent)
        if not path.exists():
            continue
        record = _read_json(path)
        if record.get("tier") != "swebench_lite_development":
            continue
        if not record.get("agent_run_ready") or not record.get("runnable"):
            continue
        records.append((str(record.get("task_id")), path, record))
    by_id = {task_id: (path, record) for task_id, path, record in records}
    selected_ids = args.task_id or (SMOKE_TASK_IDS if args.mode == "smoke" else [task_id for task_id, _, _ in records])
    selected: list[SelectedTask] = []
    for task_id in selected_ids:
        if task_id not in by_id:
            raise SystemExit(f"selected task is not runnable SWE-Bench Lite development task: {task_id}")
        path, record = by_id[task_id]
        adapter_visible = _read_json(_path_from_ref(record["adapter_visible_input_ref"], manifest_path.parent))
        evaluator_only = _read_json(_path_from_ref(record["evaluator_only_evidence_ref"], manifest_path.parent))
        materialization_entry = _read_json(
            _path_from_ref(record["swebench_dev_materialization_entry_ref"], manifest_path.parent)
        )
        verifier_plan = _read_json(_path_from_ref(record["verifier_plan_ref"], manifest_path.parent))
        selected.append(
            SelectedTask(
                task_id=task_id,
                source_record_path=path,
                source_record=record,
                adapter_visible_input=adapter_visible,
                evaluator_only_evidence=evaluator_only,
                materialization_entry=materialization_entry,
                verifier_plan=verifier_plan,
            )
        )
    return selected


def _write_task_definition(
    *,
    task: SelectedTask,
    task_set_manifest_path: Path,
    tasks_dir: Path,
    selectors_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    env_spec = _pre_verl_environment_for_repo(
        str(task.source_record.get("repo") or ""),
        str(task.source_record.get("version") or ""),
    )
    f2p_path = selectors_dir / f"{task.task_id}_fail_to_pass_selectors.json"
    p2p_path = selectors_dir / f"{task.task_id}_pass_to_pass_selectors.json"
    fail_to_pass = [str(item) for item in task.verifier_plan.get("fail_to_pass_selectors", [])]
    pass_to_pass = [str(item) for item in task.evaluator_only_evidence.get("PASS_TO_PASS", [])]
    _write_json(f2p_path, fail_to_pass)
    _write_json(p2p_path, pass_to_pass)
    materialization_entry_path = _path_from_ref(
        task.source_record["swebench_dev_materialization_entry_ref"],
        task_set_manifest_path.parent,
    )
    materialization_root = materialization_entry_path.parents[2]
    source_dir = materialization_root / "source_checkouts" / task.task_id / "source"
    hidden_test_patch_ref = dict(task.verifier_plan["test_patch_ref"])
    hidden_self_check_ref = dict(task.materialization_entry.get("test_patch_apply_result_ref") or {})
    hidden_self_check_ref["status"] = task.materialization_entry.get("test_patch_apply_status")
    verifier_command = _verifier_command(env_spec)
    task_definition = {
        "id": task.task_id,
        "task_version": f"{task.task_id}_pre_verl_agentloop_v0",
        "dataset_name": "pre_verl_swebench_lite_development_custom_subset",
        "source_kind": "swebench_lite_dev_materialized",
        "dataset_split": "dev",
        "created_at": _timestamp(),
        "repo": source_dir.as_posix(),
        "repo_source_spec": {
            "source_type": "local_repository",
            "source_path": source_dir.as_posix(),
            "base_commit": task.source_record.get("base_commit"),
            "working_tree_clean": True,
            "allow_dirty_snapshot": False,
            "decontamination_status": "unknown",
        },
        "base_commit": task.source_record.get("base_commit"),
        "issue": task.adapter_visible_input.get("problem_statement") or "",
        "setup_command": None,
        "test_command": "python -m pytest -q",
        "timeouts": {
            "setup_timeout_sec": int(env_spec.get("setup_timeout_sec", 1200)),
            "test_timeout_sec": int(env_spec.get("test_timeout_sec", 300)),
            "agent_timeout_sec": 1200,
            "final_verifier_timeout_sec": int(env_spec.get("test_timeout_sec", 300)) * 2,
        },
        "environment": {
            "execution_image": env_spec.get("execution_image"),
            "python_version": str(env_spec.get("execution_image", "")).replace("python:", "") or None,
            "package_manager": "pip",
            "setup_network_policy": "controlled_network_for_setup_only",
            "dependency_state_policy": "rerun_setup",
        },
        "expected_files": [],
        "fail_to_pass_tests": fail_to_pass,
        "pass_to_pass_tests": pass_to_pass,
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "tags": ["pre_verl", "swebench_lite_dev", str(task.source_record.get("repo") or "unknown")],
        "metadata": {
            "pre_verl_adapter": PRE_VERL_AGENTLOOP_ADAPTER_ID,
            "pre_verl_swebench_dev_manifest_path": task_set_manifest_path.as_posix(),
            "pre_verl_agentloop_mode": PRE_VERL_AGENTLOOP_MODE,
            "pre_verl_agentloop_baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
            "swe_bench_like_final_only": True,
            "final_only": True,
            "pre_verl_setup_shell": env_spec["setup_shell"],
            "pre_verl_verifier_command": verifier_command,
            "source_instance_id": task.source_record.get("source_instance_id"),
            "repo": task.source_record.get("repo"),
            "version": task.source_record.get("version"),
            "environment_id": env_spec.get("environment_id"),
            "hidden_test_patch_ref": hidden_test_patch_ref,
            "fail_to_pass_selectors_ref": _file_ref(f2p_path, visibility="evaluator_only"),
            "pass_to_pass_selectors_ref": _file_ref(p2p_path, visibility="evaluator_only"),
            "hidden_patch_clean_source_self_check_ref": hidden_self_check_ref,
            "source_tree_sha256": task.source_record.get("source_tree_sha256"),
            "custom_frozen_subset": True,
            "leaderboard_comparable": False,
        },
    }
    path = tasks_dir / f"{task.task_id}.yaml"
    _write_yaml(path, task_definition)
    return path, {
        "fail_to_pass_selectors_ref": _file_ref(f2p_path, visibility="evaluator_only"),
        "pass_to_pass_selectors_ref": _file_ref(p2p_path, visibility="evaluator_only"),
        "hidden_test_patch_ref": hidden_test_patch_ref,
    }


def _write_run_config(
    *,
    task: SelectedTask,
    config_path: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> Path:
    provider_options = {"allow_local_secret_file": bool(args.allow_local_secret_file)}
    config = {
        "run_id_prefix": args.run_id_prefix,
        "model": {
            "provider": args.provider,
            "model_id": args.model_id,
            "temperature": args.temperature,
            "max_output_tokens": args.max_output_tokens,
            "retry_policy": "none",
            "credential_policy": "env_or_local_secret_file" if args.allow_local_secret_file else "env_only",
            "provider_request_logging": "redact_secrets",
            "provider_specific_options": provider_options,
        },
        "runtime": {
            "scaffold_id": args.scaffold_id,
            "execution_mode": args.execution_mode,
            "permission_mode": args.permission_mode,
            "test_feedback_policy": args.test_feedback_policy,
            "max_turns": args.max_turns,
            "max_tool_calls": args.max_tool_calls,
            "max_test_runs": args.max_test_runs,
            "task_timeout_sec": args.task_timeout_sec,
            "seed": args.seed,
        },
        "workspace": {
            "output_dir": output_dir.as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": args.command_timeout_sec,
            "network_policy": "deny_agent_run",
        },
        "context_management": {
            "max_context_tokens": 120000,
            "tool_result_aggregate_budget_chars": 40000,
            "keep_recent_turns": 6,
            "keep_recent_test_results": 0,
            "summarize_old_test_outputs": True,
        },
        "evaluation": {
            "concurrency": 1,
            "rerun_final_verifier": True,
            "final_verifier_mode": "strict_patch_replay",
            "fail_on_invalid_task": False,
        },
    }
    _write_yaml(config_path, config)
    return config_path


def _write_configuration_manifests(
    *,
    output_dir: Path,
    task_set_manifest_path: Path,
    entries: list[dict[str, Any]],
    args: argparse.Namespace,
) -> Path:
    scaffold = build_scaffold(args.scaffold_id)
    prompt_hash = hashlib.sha256(scaffold.prompt_fragment.encode("utf-8")).hexdigest()
    resolved_tools = entries[0]["resolved_tools"] if entries else []
    configuration = {
        "schema_version": "repo_harness_pre_verl_agentloop_configuration_manifest_v0",
        "created_at": _timestamp(),
        "mode": args.mode,
        "baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
        "pre_verl_adapter": PRE_VERL_AGENTLOOP_ADAPTER_ID,
        "pre_verl_swebench_dev_manifest_path": task_set_manifest_path.as_posix(),
        "pre_verl_agentloop_mode": PRE_VERL_AGENTLOOP_MODE,
        "forbidden_scaffold_ids": FORBIDDEN_SCAFFOLD_IDS,
        "old_pilot_allowed": False,
        "old_pilot_scaffold_id": "single_shot_patch_no_tools",
        "all_results_must_have_run_task_run_dir": True,
        "provider": args.provider,
        "model_id": args.model_id,
        "scaffold_id": args.scaffold_id,
        "scaffold_version": scaffold.scaffold_version,
        "scaffold_prompt_sha256": prompt_hash,
        "test_feedback_policy": args.test_feedback_policy,
        "resolved_tools": resolved_tools,
        "budget": _budget_payload(args),
        "selected_task_count": len(entries),
    }
    configuration_path = output_dir / "pre_verl_agentloop_configuration_manifest.json"
    _write_json(configuration_path, configuration)
    prompt_policy_path = output_dir / "pre_verl_agentloop_prompt_and_tool_policy_report.json"
    _write_json(
        prompt_policy_path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_prompt_and_tool_policy_report_v0",
            "status": "frozen",
            "scaffold_id": args.scaffold_id,
            "scaffold_version": scaffold.scaffold_version,
            "scaffold_prompt_sha256": prompt_hash,
            "scaffold_prompt_text": scaffold.prompt_fragment,
            "test_feedback_policy": args.test_feedback_policy,
            "resolved_tools": resolved_tools,
            "scaffold_comparison_policy": (
                "current baseline fixes scaffold and tool permissions; later scaffold comparison "
                "must either compare full scaffold packages or force the same resolved tools."
            ),
        },
    )
    budget_path = output_dir / "formal_budget_freeze_manifest.json"
    _write_json(
        budget_path,
        {
            "schema_version": "repo_harness_pre_verl_formal_budget_freeze_manifest_v0",
            "status": "frozen",
            "created_at": _timestamp(),
            "provider": args.provider,
            "model_id": args.model_id,
            "budget": _budget_payload(args),
            "temperature": args.temperature,
            "seed": args.seed,
            "requires_new_baseline_id_if_changed": [
                "max_turns",
                "max_tool_calls",
                "max_test_runs",
                "task_timeout_sec",
                "command_timeout_sec",
                "max_output_tokens",
                "temperature",
                "scaffold_prompt_sha256",
                "resolved_tools",
                "model_id",
            ],
        },
    )
    return configuration_path


def _write_run_matrix(output_dir: Path, entries: list[dict[str, Any]], args: argparse.Namespace) -> Path:
    path = output_dir / "pre_verl_agentloop_smoke_run_matrix_manifest.json"
    if args.mode == "formal":
        path = output_dir / "pre_verl_agentloop_formal_run_matrix_manifest.json"
    _write_json(
        path,
        {
            "schema_version": "repo_harness_pre_verl_agentloop_run_matrix_manifest_v0",
            "created_at": _timestamp(),
            "mode": args.mode,
            "baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
            "entry_count": len(entries),
            "entries": entries,
        },
    )
    return path


def _write_boundary_index(output_dir: Path, entries: list[dict[str, Any]]) -> Path:
    path = output_dir / "pre_verl_agentloop_final_verifier_boundary_index.json"
    _write_json(
        path,
        {
            "schema_version": PRE_VERL_AGENTLOOP_BOUNDARY_INDEX_VERSION,
            "created_at": _timestamp(),
            "baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
            "entries": [
                {
                    "task_id": entry["task_id"],
                    "run_task_run_dir": entry["run_task_run_dir"],
                    "final_verifier_boundary_ref": _file_ref(
                        Path(entry["run_task_run_dir"]) / "final_verifier_boundary.json"
                    ),
                    "scaffold_id": entry["scaffold_id"],
                    "provider": entry["provider"],
                    "model_id": entry["model_id"],
                    "run_task_command_log_entry_ref": entry.get("run_task_command_log_entry_ref"),
                }
                for entry in entries
                if entry.get("status") == "executed"
            ],
        },
    )
    return path


def _verifier_command(env_spec: dict[str, Any]) -> str:
    prefix = ". .pre_verl_venv/bin/activate"
    pythonpath = str(env_spec.get("pythonpath") or "").strip()
    if pythonpath:
        prefix = f"{prefix} && export PYTHONPATH={shlex.quote(pythonpath)}"
    return f"{prefix} && python -m pytest -q"


def _budget_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "max_turns": args.max_turns,
        "max_tool_calls": args.max_tool_calls,
        "max_test_runs": args.max_test_runs,
        "task_timeout_sec": args.task_timeout_sec,
        "command_timeout_sec": args.command_timeout_sec,
        "max_output_tokens": args.max_output_tokens,
    }


def _run_checked_command(
    argv: list[str],
    *,
    cwd: Path,
    logs_dir: Path,
    command_log_path: Path,
    command_name: str,
) -> subprocess.CompletedProcess[str]:
    result, _entry_path = _run_logged_command(
        argv,
        cwd=cwd,
        logs_dir=logs_dir,
        command_log_path=command_log_path,
        command_name=command_name,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def _run_logged_command(
    argv: list[str],
    *,
    cwd: Path,
    logs_dir: Path,
    command_log_path: Path,
    command_name: str,
    input_refs: list[dict[str, Any]] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    started_at = _timestamp()
    safe_name = f"{len(command_log_path.read_text(encoding='utf-8').splitlines()) + 1:04d}_{command_name}"
    stdout_path = logs_dir / f"{safe_name}.stdout.txt"
    stderr_path = logs_dir / f"{safe_name}.stderr.txt"
    env = os.environ.copy()
    env["PATH"] = f"{(REPO_ROOT / '.venv' / 'bin').as_posix()}:{env.get('PATH', '')}"
    env["PYTHONPATH"] = f"{SRC_ROOT.as_posix()}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    finished_at = _timestamp()
    entry = {
        "schema_version": "repo_harness_pre_verl_agentloop_external_command_log_entry_v0",
        "command_name": command_name,
        "argv": argv,
        "cwd": cwd.as_posix(),
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": result.returncode,
        "input_refs": input_refs or [],
        "stdout_ref": _file_ref(stdout_path),
        "stderr_ref": _file_ref(stderr_path),
    }
    entry_path = logs_dir / f"{safe_name}.entry.json"
    _write_json(entry_path, entry)
    with command_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return result, entry_path


def _path_from_ref(ref: Any, base: Path) -> Path:
    if isinstance(ref, dict):
        value = ref.get("path") or ref.get("relative_path")
    else:
        value = ref
    if not isinstance(value, str) or not value:
        raise SystemExit(f"invalid evidence ref: {ref!r}")
    path = Path(value)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _file_ref(path: Path, *, visibility: str | None = None) -> dict[str, Any]:
    ref = {
        "path": path.resolve().as_posix(),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    if visibility is not None:
        ref["visibility"] = visibility
    return ref


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
