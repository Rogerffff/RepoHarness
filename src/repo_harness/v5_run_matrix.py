"""V5 Stage 3B run matrix builders and runners."""

from __future__ import annotations

import json
import shutil
import shlex
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Any

import yaml

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.config import (
    ContextManagementConfig,
    EvaluationConfig,
    ModelConfig,
    RunConfig,
    RuntimeConfig,
    WorkspaceConfig,
)
from repo_harness.context import ContextBuilder
from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.export.manifest import sha256_file
from repo_harness.model_client.factory import create_model_client, provider_options_from_model_config
from repo_harness.model_client.providers.deepseek import normalize_deepseek_model_id
from repo_harness.model_client.providers.openai import normalize_openai_model_id
from repo_harness.permissions import PermissionContext
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.run_metadata.tool_snapshot import write_tool_schema_snapshot
from repo_harness.scaffolds import build_scaffold
from repo_harness.scaffolds import resolve_allowed_tools, resolve_feedback_policy, tool_registry_for_allowed_tools
from repo_harness.schema_versions import (
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_MATRIX_CELL_RESULT_VERSION,
    V5_MATRIX_COMPARE_SCOPE_REPORT_VERSION,
    V5_PROVIDER_COMPARISON_REPORT_VERSION,
    V5_RESUME_CLAIM_GATE_REPORT_VERSION,
    V5_RUN_MATRIX_MANIFEST_VERSION,
)
from repo_harness.tasks import (
    DecontaminationMetadata,
    EnvironmentSpec,
    LocalArchiveSource,
    RunnableTask,
    TaskTimeouts,
    VerifierConfig,
    VisibilityPolicy,
)
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolOutputLimits
from repo_harness.trajectory import RunRecorder, TrajectoryEvent
from repo_harness.workspace import LocalWorkspaceAdapter
from repo_harness.v5_evidence import (
    _builder_command_log_entry,
    _evidence_ref,
    _utc_timestamp,
    _write_json,
    _write_jsonl,
)


V5_STAGE3B_DEFAULT_TASK_IDS = (
    "v5_task_003",
    "v5_task_004",
    "v5_task_005",
    "v5_task_007",
    "v5_pr_issue_click_3364",
    "v5_pr_issue_attrs_1428",
)

V5_STAGE3B_DEFAULT_PROVIDER_IDS = ("deepseek",)
V5_STAGE3B_DEFAULT_MODELS = {
    "deepseek": "deepseek-v4-flash",
    "openai": "gpt-5.4-nano",
}
V5_STAGE3B_PROVIDER_IDS = ("deepseek", "openai")

V5_STAGE3B_TEST_COMMANDS = {
    "v5_task_003": "python -m pytest -q tests/test_formatting.py::test_formatting_usage_error_help_hint",
    "v5_task_004": (
        "python -m pytest -q "
        "testing/test_pluginmanager.py::test_unregister_plugin_with_multi_hookimpls "
        "testing/test_pluginmanager.py::test_get_hookcallers_no_duplicates"
    ),
    "v5_task_005": (
        "python -m pytest -q "
        "tests/test_ext_autosummary.py::test_autosummary_generate_content_for_module"
    ),
    "v5_task_007": "python -m pytest -q lib/matplotlib/tests/test_matplotlib.py::test_parse_to_version_info",
    "v5_task_008": "go test . -run TestDecodeError_Position",
}

V5_STAGE3B_OUTPUT_NAMES = (
    "v5_run_matrix_manifest.json",
    "build_v5_run_matrix_command_log_entry.json",
    "v5_stage3b_run_matrix_build_command_log.jsonl",
)

V5_STAGE3B_RUN_OUTPUT_NAMES = (
    "v5_run_matrix_manifest_executed.json",
    "v5_matrix_cell_results.jsonl",
    "v5_stage3b_run_matrix_execution_report.json",
    "run_v5_run_matrix_command_log_entry.json",
    "v5_stage3b_run_matrix_run_command_log.jsonl",
)

V5_ACCEPTED_RUN_OUTPUT_NAMES = (
    "v5_run_matrix_manifest_executed.json",
    "v5_matrix_cell_results.jsonl",
    "v5_stage3b_run_matrix_execution_report.json",
    "accepted_run_config_facts.json",
    "generated_tasks",
    "controlled_variables",
    "agent_runs",
    "run_configs",
    "run_v5_accepted_provider_task_command_log_entry.json",
    "v5_stage3b_accepted_provider_run_command_log.jsonl",
)

V5_STAGE3C_OUTPUT_NAMES = (
    "v5_matrix_compare_scope_report.json",
    "v5_provider_comparison_report.json",
    "v5_scaffold_comparison_report.json",
    "v5_budget_comparison_report.json",
    "v5_resume_claim_gate_report.json",
    "build_v5_comparison_reports_command_log_entry.json",
    "v5_stage3c_comparison_reports_command_log.jsonl",
)


def build_run_matrix_manifest(
    *,
    task_set_manifest: str | Path,
    provider_gate_report: str | Path,
    provider_cost_budget_report: str | Path,
    output_dir: str | Path,
    task_ids: list[str] | None = None,
    provider_ids: list[str] | None = None,
    deepseek_model_id: str = "deepseek-v4-flash",
    openai_model_id: str = "gpt-5.4-nano",
    fail_if_output_exists: bool = True,
) -> Path:
    """Build a V5 Stage 3B primary-provider run matrix manifest."""

    root = Path(output_dir)
    _refuse_existing(root, V5_STAGE3B_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_set_path = Path(task_set_manifest)
    provider_gate_path = Path(provider_gate_report)
    provider_cost_path = Path(provider_cost_budget_report)
    task_set = _read_json(task_set_path)
    provider_gate = _read_json(provider_gate_path)
    provider_cost = _read_json(provider_cost_path)
    selected_providers = tuple(provider_ids or V5_STAGE3B_DEFAULT_PROVIDER_IDS)
    model_by_provider = _model_by_provider(
        deepseek_model_id=deepseek_model_id,
        openai_model_id=openai_model_id,
    )
    _require_stage3b_inputs(
        task_set=task_set,
        provider_gate=provider_gate,
        provider_cost=provider_cost,
        provider_ids=selected_providers,
    )

    selected_ids = tuple(task_ids or V5_STAGE3B_DEFAULT_TASK_IDS)
    tasks_by_id = _load_task_definitions(task_set)
    cells: list[dict[str, Any]] = []
    generated_task_refs: list[dict[str, Any]] = []
    controlled_refs: list[dict[str, Any]] = []
    generated_task_dir = root / "generated_tasks"
    controlled_dir = root / "controlled_variables"
    generated_task_dir.mkdir(parents=True, exist_ok=True)
    controlled_dir.mkdir(parents=True, exist_ok=True)

    cell_index = 0
    for task_id in selected_ids:
        task = tasks_by_id.get(task_id)
        if task is None:
            raise ConfigError(f"run matrix selected task 不存在：{task_id}")
        if not task.get("agent_run_ready"):
            raise ConfigError(f"run matrix selected task 不是 agent_run_ready：{task_id}")
        adapter_visible = _read_json(Path(task["adapter_visible_input_ref"]["path"]))
        task_yaml = _task_yaml_payload(task=task, adapter_visible=adapter_visible)
        task_yaml_path = generated_task_dir / f"{task_id}.yaml"
        _write_yaml(task_yaml_path, task_yaml)
        generated_ref = _evidence_ref(
            task_yaml_path,
            kind="v5_stage3b_generated_task_yaml",
            purpose=f"Generated runnable task YAML for {task_id}",
            visibility="audit_only",
            producer_command="build-v5-run-matrix",
            producer_stage="v5_stage3b_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        )
        generated_task_refs.append(generated_ref)
        for provider_id in selected_providers:
            cell_index += 1
            controlled = _controlled_variables_payload(
                task=task,
                task_yaml_path=task_yaml_path,
                provider_id=provider_id,
                scaffold_id="simple_react",
                budget_policy_id="stage3b_constrained_one_turn_no_tool_calls",
            )
            controlled_path = controlled_dir / f"{task_id}_{provider_id}_simple_react_constrained.json"
            _write_json(controlled_path, controlled)
            controlled_ref = _evidence_ref(
                controlled_path,
                kind="v5_matrix_controlled_variables",
                purpose=f"Controlled variables for {task_id} {provider_id} run",
                visibility="audit_only",
                producer_command="build-v5-run-matrix",
                producer_stage="v5_stage3b_run_matrix",
                inspect_command="inspect-v5-run-matrix",
            )
            controlled_refs.append(controlled_ref)
            cells.append(
                {
                    "cell_id": f"v5_stage3b_cell_{cell_index:02d}_{task_id}_{provider_id}_simple_react_constrained",
                    "task_id": task_id,
                    "task_ref": _task_ref(task),
                    "generated_task_ref": generated_ref,
                    "provider_id": provider_id,
                    "provider_mode": "primary",
                    "model_id": model_by_provider[provider_id],
                    "scaffold_id": "simple_react",
                    "budget_policy_id": "stage3b_constrained_one_turn_no_tool_calls",
                    "tool_policy_id": "stage3b_no_tool_calls",
                    "context_policy_id": "stage3b_default_context_compaction",
                    "environment_id": task.get("environment_id"),
                    "source_tree_hash": task.get("source_tree_hash"),
                    "final_verifier_plan_ref": task.get("final_verifier_plan_ref"),
                    "controlled_variables_ref": controlled_ref,
                    "counts_toward_core_real_provider_floor": True,
                    "counts_toward_resume_ready_multi_provider": provider_id in {"deepseek", "openai"},
                }
            )

    manifest_path = root / "v5_run_matrix_manifest.json"
    manifest = {
        "schema_version": V5_RUN_MATRIX_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3b_run_matrix_planning",
        "task_set_ref": _artifact_ref_for_input(task_set_path, "v5_task_set_manifest", "inspect-v5-task-set"),
        "provider_gate_ref": _artifact_ref_for_input(provider_gate_path, "v5_provider_credential_gate_report", "inspect-v5-provider-gate"),
        "provider_cost_budget_ref": _artifact_ref_for_input(provider_cost_path, "v5_provider_cost_budget_report", "inspect-v5-provider-cost-budget"),
        "planned_matrix_cells": cells,
        "planned_matrix_cell_count": len(cells),
        "generated_task_refs": generated_task_refs,
        "controlled_variables_refs": controlled_refs,
        "planned_provider_ids": list(selected_providers),
        "planned_model_ids_by_provider": model_by_provider,
        "comparison_axes": ["scaffold", "budget", "provider"],
        "comparison_ready_task_count": sum(1 for cell in cells if tasks_by_id[cell["task_id"]].get("comparison_ready")),
        "agent_run_started": False,
        "provider_api_called": False,
        "real_provider_family_floor_target": 1,
        "real_agent_run_task_floor_target": 6,
        "status": "planned",
    }
    _write_json(manifest_path, manifest)
    command_entry = _builder_command_log_entry(
        command_name="build-v5-run-matrix",
        input_paths=[task_set_path, provider_gate_path, provider_cost_path],
        output_paths=[manifest_path, generated_task_dir, controlled_dir],
        producer_stage="v5_stage3b_run_matrix_planning",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "build_v5_run_matrix_command_log_entry.json"
    command_log_path = root / "v5_stage3b_run_matrix_build_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return manifest_path


def run_matrix_cells(
    *,
    run_matrix_manifest: str | Path,
    provider_cost_budget_report: str | Path,
    output_dir: str | Path,
    allow_local_secret_file: bool = True,
    fail_if_output_exists: bool = True,
) -> Path:
    """Run V5 Stage 3B primary-provider matrix cells and write result evidence."""

    root = Path(output_dir)
    _refuse_existing(root, V5_STAGE3B_RUN_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(run_matrix_manifest)
    provider_cost_path = Path(provider_cost_budget_report)
    manifest = _read_json(manifest_path)
    provider_cost = _read_json(provider_cost_path)
    cells = manifest.get("planned_matrix_cells")
    if not isinstance(cells, list) or not cells:
        raise ConfigError("run matrix manifest 缺少 planned_matrix_cells。")
    max_calls = int(provider_cost.get("max_real_provider_calls", 0))
    if len(cells) > max_calls:
        raise ConfigError("planned matrix cells 超过 provider cost budget call 上限。")

    results_path = root / "v5_matrix_cell_results.jsonl"
    report_path = root / "v5_stage3b_run_matrix_execution_report.json"
    executed_manifest_path = root / "v5_run_matrix_manifest_executed.json"
    agent_runs_dir = root / "agent_runs"
    configs_dir = root / "run_configs"
    agent_runs_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    actual_provider_calls = 0
    for cell in cells:
        task_yaml_path = Path(cell["generated_task_ref"]["path"])
        model_slug = _slug(str(cell["model_id"]))
        run_id = f"v5_stage3b_{cell['provider_id']}_{cell['task_id']}_{model_slug}"
        config_path = configs_dir / f"{run_id}.yaml"
        _write_yaml(
            config_path,
            _run_config_payload(
                output_dir=agent_runs_dir,
                allow_local_secret_file=allow_local_secret_file,
                provider_id=str(cell["provider_id"]),
                model_id=str(cell["model_id"]),
            ),
        )
        result = _run_one_cell(
            cell=cell,
            task_yaml_path=task_yaml_path,
            config_path=config_path,
            agent_runs_dir=agent_runs_dir,
            run_id=run_id,
        )
        actual_provider_calls += result["actual_provider_call_count"]
        results.append(result)
        if _should_stop_after_provider_error(result):
            break

    _write_jsonl(results_path, results)
    real_run_count = sum(1 for item in results if item.get("actual_provider_call_count", 0) > 0)
    primary_attempted_count = sum(1 for item in results if item.get("normalized_provider_status") == "primary_attempted")
    provider_families = sorted({
        str(item["provider_id"])
        for item in results
        if item.get("actual_provider_call_count", 0) > 0
    })
    hard_stop_reason = _hard_stop_reason(results)
    report = {
        "schema_version": "repo_harness_v5_run_matrix_execution_report_v0",
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3b_real_provider_run_matrix",
        "run_matrix_manifest_ref": _artifact_ref_for_input(manifest_path, "v5_run_matrix_manifest", "inspect-v5-run-matrix"),
        "provider_cost_budget_ref": _artifact_ref_for_input(provider_cost_path, "v5_provider_cost_budget_report", "inspect-v5-provider-cost-budget"),
        "matrix_cell_results_ref": _evidence_ref(
            results_path,
            kind="v5_matrix_cell_results",
            purpose="V5 Stage 3B matrix cell results",
            visibility="audit_only",
            producer_command="run-v5-run-matrix",
            producer_stage="v5_stage3b_real_provider_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        ),
        "actual_provider_calls": actual_provider_calls,
        "max_real_provider_calls": max_calls,
        "real_agent_run_task_count": real_run_count,
        "primary_attempted_count": primary_attempted_count,
        "provider_api_called": actual_provider_calls > 0,
        "real_provider_families_with_actual_runs": provider_families,
        "core_real_provider_floor_satisfied": real_run_count >= 6 and actual_provider_calls > 0,
        "hard_stop_reason": hard_stop_reason,
        "status": "passed" if real_run_count >= 6 and actual_provider_calls <= max_calls and hard_stop_reason is None else "blocked",
    }
    _write_json(report_path, report)
    executed_manifest = {
        **manifest,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3b_real_provider_run_matrix",
        "agent_run_started": True,
        "provider_api_called": actual_provider_calls > 0,
        "matrix_cell_results_ref": report["matrix_cell_results_ref"],
        "run_matrix_execution_report_ref": _evidence_ref(
            report_path,
            kind="v5_run_matrix_execution_report",
            purpose="V5 Stage 3B run matrix execution report",
            visibility="audit_only",
            producer_command="run-v5-run-matrix",
            producer_stage="v5_stage3b_real_provider_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        ),
        "actual_provider_calls": actual_provider_calls,
        "real_agent_run_task_count": real_run_count,
        "real_provider_families_with_actual_runs": report["real_provider_families_with_actual_runs"],
        "hard_stop_reason": hard_stop_reason,
        "status": report["status"],
    }
    _write_json(executed_manifest_path, executed_manifest)
    command_entry = _builder_command_log_entry(
        command_name="run-v5-run-matrix",
        input_paths=[manifest_path, provider_cost_path],
        output_paths=[executed_manifest_path, results_path, report_path, agent_runs_dir, configs_dir],
        producer_stage="v5_stage3b_real_provider_run_matrix",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "run_v5_run_matrix_command_log_entry.json"
    command_log_path = root / "v5_stage3b_run_matrix_run_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return executed_manifest_path


def run_accepted_provider_task(
    *,
    task_set_manifest: str | Path,
    provider_gate_report: str | Path,
    provider_cost_budget_report: str | Path,
    output_dir: str | Path,
    task_id: str,
    provider_id: str = "deepseek",
    model_id: str = "deepseek-v4-pro",
    prior_executed_run_matrix_manifest: str | Path | None = None,
    allow_local_secret_file: bool = True,
    max_turns: int = 12,
    max_tool_calls: int = 40,
    max_output_tokens: int = 4096,
    fail_if_output_exists: bool = True,
) -> Path:
    """Run one V5 accepted-provider attempt with strict final verifier replay evidence."""

    root = Path(output_dir)
    _refuse_existing(root, V5_ACCEPTED_RUN_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    task_set_path = Path(task_set_manifest)
    provider_gate_path = Path(provider_gate_report)
    provider_cost_path = Path(provider_cost_budget_report)
    task_set = _read_json(task_set_path)
    provider_gate = _read_json(provider_gate_path)
    provider_cost = _read_json(provider_cost_path)
    _require_stage3b_inputs(
        task_set=task_set,
        provider_gate=provider_gate,
        provider_cost=provider_cost,
        provider_ids=(provider_id,),
    )
    if int(provider_cost.get("max_real_provider_calls", 0)) < 1:
        raise ConfigError("accepted provider run 至少需要 1 次 provider call budget。")
    normalized_model_id = _normalize_model_for_provider(provider_id, model_id)
    tasks_by_id = _load_task_definitions(task_set)
    task = tasks_by_id.get(task_id)
    if task is None:
        raise ConfigError(f"accepted provider run task 不存在：{task_id}")
    if not task.get("agent_run_ready"):
        raise ConfigError(f"accepted provider run task 不是 agent_run_ready：{task_id}")
    adapter_visible = _read_json(Path(task["adapter_visible_input_ref"]["path"]))
    verifier_entry = _verifier_entry_for_task(task)
    generated_dir = root / "generated_tasks"
    controlled_dir = root / "controlled_variables"
    configs_dir = root / "run_configs"
    agent_runs_dir = root / "agent_runs"
    generated_dir.mkdir(parents=True, exist_ok=True)
    controlled_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)
    agent_runs_dir.mkdir(parents=True, exist_ok=True)
    task_yaml_path = generated_dir / f"{task_id}_accepted_provider.yaml"
    _write_yaml(task_yaml_path, _accepted_task_yaml_payload(task=task, adapter_visible=adapter_visible))
    generated_task_ref = _evidence_ref(
        task_yaml_path,
        kind="v5_accepted_provider_generated_task_yaml",
        purpose=f"Generated accepted-provider task YAML for {task_id}",
        visibility="audit_only",
        producer_command="run-v5-accepted-provider-task",
        producer_stage="v5_stage3b_accepted_provider_run",
        inspect_command="inspect-v5-run-matrix",
    )
    controlled_path = controlled_dir / f"{task_id}_{provider_id}_accepted_patch_strict_replay.json"
    controlled = {
        "schema_version": "repo_harness_v5_matrix_controlled_variables_v0",
        "task_id": task_id,
        "task_yaml_sha256": sha256_file(task_yaml_path),
        "source_tree_hash": task.get("source_tree_hash"),
        "source_archive_sha256": task.get("source_archive_sha256"),
        "final_verifier_plan_ref": task.get("final_verifier_plan_ref"),
        "tool_policy_id": "v5_accepted_patch_read_write_no_hidden_feedback",
        "context_policy_id": "v5_accepted_patch_final_only_context",
        "provider_id": provider_id,
        "scaffold_id": "patch_focused_react",
        "budget_policy_id": "v5_accepted_patch_bounded_tool_loop",
        "environment_id": task.get("environment_id"),
        "comparison_validity_scope": "accepted_provider_strict_replay_single_task",
    }
    _write_json(controlled_path, controlled)
    controlled_ref = _evidence_ref(
        controlled_path,
        kind="v5_matrix_controlled_variables",
        purpose=f"Controlled variables for accepted provider run {task_id}",
        visibility="audit_only",
        producer_command="run-v5-accepted-provider-task",
        producer_stage="v5_stage3b_accepted_provider_run",
        inspect_command="inspect-v5-run-matrix",
    )
    run_id = f"v5_accepted_{provider_id}_{task_id}_{_slug(normalized_model_id)}"
    config_path = configs_dir / f"{run_id}.yaml"
    _write_yaml(
        config_path,
        _accepted_run_config_payload(
            output_dir=agent_runs_dir,
            provider_id=provider_id,
            model_id=normalized_model_id,
            allow_local_secret_file=allow_local_secret_file,
            max_turns=max_turns,
            max_tool_calls=max_tool_calls,
            max_output_tokens=max_output_tokens,
        ),
    )
    cell = {
        "cell_id": f"v5_accepted_cell_{task_id}_{provider_id}_patch_focused_react",
        "task_id": task_id,
        "task_ref": _task_ref(task),
        "generated_task_ref": generated_task_ref,
        "provider_id": provider_id,
        "provider_mode": "primary",
        "model_id": normalized_model_id,
        "scaffold_id": "patch_focused_react",
        "budget_policy_id": "v5_accepted_patch_bounded_tool_loop",
        "tool_policy_id": "v5_accepted_patch_read_write_no_hidden_feedback",
        "context_policy_id": "v5_accepted_patch_final_only_context",
        "environment_id": task.get("environment_id"),
        "source_tree_hash": task.get("source_tree_hash"),
        "final_verifier_plan_ref": task.get("final_verifier_plan_ref"),
        "controlled_variables_ref": controlled_ref,
        "counts_toward_core_real_provider_floor": True,
        "counts_toward_resume_ready_multi_provider": False,
    }
    result = _run_one_accepted_provider_cell(
        cell=cell,
        task=task,
        adapter_visible=adapter_visible,
        verifier_entry=verifier_entry,
        config_path=config_path,
        agent_runs_dir=agent_runs_dir,
        run_id=run_id,
        allow_local_secret_file=allow_local_secret_file,
        max_turns=max_turns,
        max_tool_calls=max_tool_calls,
        max_output_tokens=max_output_tokens,
    )
    prior_manifest: dict[str, Any] | None = None
    prior_results: list[dict[str, Any]] = []
    prior_path = Path(prior_executed_run_matrix_manifest) if prior_executed_run_matrix_manifest else None
    if prior_path is not None:
        prior_manifest = _read_json(prior_path)
        prior_results_ref = prior_manifest.get("matrix_cell_results_ref")
        prior_results_path = _path_from_ref(prior_results_ref)
        if prior_results_path is None:
            raise ConfigError("prior executed run matrix 缺少 matrix_cell_results_ref。")
        prior_results = _read_jsonl(prior_results_path)
    results = [result, *prior_results]
    results_path = root / "v5_matrix_cell_results.jsonl"
    report_path = root / "v5_stage3b_run_matrix_execution_report.json"
    executed_manifest_path = root / "v5_run_matrix_manifest_executed.json"
    _write_jsonl(results_path, results)
    actual_provider_calls = sum(int(item.get("actual_provider_call_count", 0) or 0) for item in results)
    real_run_count = sum(1 for item in results if item.get("actual_provider_call_count", 0) > 0)
    provider_families = sorted({
        str(item.get("provider_id"))
        for item in results
        if item.get("actual_provider_call_count", 0) > 0
    })
    max_calls = int(provider_cost.get("max_real_provider_calls", 0))
    hard_stop_reason = _hard_stop_reason(results)
    report = {
        "schema_version": "repo_harness_v5_run_matrix_execution_report_v0",
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3b_accepted_provider_run",
        "run_matrix_manifest_ref": _artifact_ref_for_input(
            prior_path or task_set_path,
            "v5_run_matrix_manifest_executed" if prior_path else "v5_task_set_manifest",
            "inspect-v5-run-matrix" if prior_path else "inspect-v5-task-set",
        ),
        "provider_cost_budget_ref": _artifact_ref_for_input(provider_cost_path, "v5_provider_cost_budget_report", "inspect-v5-provider-cost-budget"),
        "matrix_cell_results_ref": _evidence_ref(
            results_path,
            kind="v5_matrix_cell_results",
            purpose="V5 accepted provider run plus prior matrix cell results",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ),
        "actual_provider_calls": actual_provider_calls,
        "max_real_provider_calls": max_calls,
        "real_agent_run_task_count": real_run_count,
        "accepted_provider_run_count": sum(1 for item in results if item.get("accepted") is True and item.get("final_verifier_status") == "accepted"),
        "provider_api_called": actual_provider_calls > 0,
        "real_provider_families_with_actual_runs": provider_families,
        "core_real_provider_floor_satisfied": real_run_count >= 6 and actual_provider_calls > 0,
        "hard_stop_reason": hard_stop_reason,
        "status": "passed" if real_run_count >= 6 and actual_provider_calls <= max_calls and hard_stop_reason is None else "blocked",
    }
    _write_json(report_path, report)
    planned_cells = [cell]
    generated_refs = [generated_task_ref]
    controlled_refs = [controlled_ref]
    if prior_manifest:
        planned_cells = [cell, *list(prior_manifest.get("planned_matrix_cells") or [])]
        generated_refs = [generated_task_ref, *list(prior_manifest.get("generated_task_refs") or [])]
        controlled_refs = [controlled_ref, *list(prior_manifest.get("controlled_variables_refs") or [])]
    executed_manifest = {
        "schema_version": V5_RUN_MATRIX_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3b_accepted_provider_run",
        "task_set_ref": _artifact_ref_for_input(task_set_path, "v5_task_set_manifest", "inspect-v5-task-set"),
        "provider_gate_ref": _artifact_ref_for_input(provider_gate_path, "v5_provider_credential_gate_report", "inspect-v5-provider-gate"),
        "provider_cost_budget_ref": _artifact_ref_for_input(provider_cost_path, "v5_provider_cost_budget_report", "inspect-v5-provider-cost-budget"),
        "prior_executed_run_matrix_ref": (
            _artifact_ref_for_input(prior_path, "v5_run_matrix_manifest_executed", "inspect-v5-run-matrix")
            if prior_path
            else None
        ),
        "planned_matrix_cells": planned_cells,
        "planned_matrix_cell_count": len(planned_cells),
        "generated_task_refs": generated_refs,
        "controlled_variables_refs": controlled_refs,
        "planned_provider_ids": sorted({str(item.get("provider_id")) for item in planned_cells}),
        "planned_model_ids_by_provider": {provider_id: normalized_model_id},
        "comparison_axes": ["scaffold", "budget", "provider"],
        "comparison_ready_task_count": sum(1 for item in planned_cells if str(item.get("task_id")) == task_id),
        "agent_run_started": True,
        "provider_api_called": actual_provider_calls > 0,
        "matrix_cell_results_ref": report["matrix_cell_results_ref"],
        "run_matrix_execution_report_ref": _evidence_ref(
            report_path,
            kind="v5_run_matrix_execution_report",
            purpose="V5 accepted provider run execution report",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ),
        "actual_provider_calls": actual_provider_calls,
        "real_agent_run_task_count": real_run_count,
        "real_provider_families_with_actual_runs": provider_families,
        "accepted_provider_run_count": report["accepted_provider_run_count"],
        "hard_stop_reason": hard_stop_reason,
        "status": report["status"],
    }
    _write_json(executed_manifest_path, executed_manifest)
    command_entry = _builder_command_log_entry(
        command_name="run-v5-accepted-provider-task",
        input_paths=[task_set_path, provider_gate_path, provider_cost_path, *([prior_path] if prior_path else [])],
        output_paths=[executed_manifest_path, results_path, report_path, agent_runs_dir, configs_dir, generated_dir, controlled_dir],
        producer_stage="v5_stage3b_accepted_provider_run",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "run_v5_accepted_provider_task_command_log_entry.json"
    command_log_path = root / "v5_stage3b_accepted_provider_run_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return executed_manifest_path


def build_comparison_reports(
    *,
    executed_run_matrix_manifest: str | Path,
    additional_executed_run_matrix_manifests: list[str | Path] | None = None,
    provider_gate_report: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build Stage 3C comparison reports and resume claim gate."""

    root = Path(output_dir)
    _refuse_existing(root, V5_STAGE3C_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    manifest_paths = [
        Path(executed_run_matrix_manifest),
        *[Path(path) for path in (additional_executed_run_matrix_manifests or [])],
    ]
    provider_gate_path = Path(provider_gate_report)
    provider_gate = _read_json(provider_gate_path)
    manifests = [_read_json(path) for path in manifest_paths]
    result_paths: list[Path] = []
    for index, manifest in enumerate(manifests):
        if manifest.get("agent_run_started") is not True or manifest.get("provider_api_called") is not True:
            raise ConfigError("Stage 3C comparison reports 需要已执行且发生 provider API 调用的 run matrix。")
        results_ref = manifest.get("matrix_cell_results_ref")
        results_path = _path_from_ref(results_ref)
        if results_path is None:
            raise ConfigError(f"executed run matrix[{index}] 缺少 matrix_cell_results_ref。")
        result_paths.append(results_path)
    results = [item for path in result_paths for item in _read_jsonl(path)]
    real_results = [item for item in results if item.get("actual_provider_call_count", 0) > 0]

    real_provider_families = sorted({str(item["provider_id"]) for item in real_results})
    actual_records_by_provider = {
        provider: sum(1 for item in real_results if item.get("provider_id") == provider)
        for provider in real_provider_families
    }
    provider_pairs = _provider_comparison_pairs(real_results)
    provider_comparison_valid = len(provider_pairs) >= 2
    if len(real_results) < 6 and not provider_comparison_valid:
        raise ConfigError("Stage 3C comparison reports 需要至少 6 条真实 provider result，或至少 2 个 DeepSeek/OpenAI 成对 provider comparison 任务。")
    comparison_cells = _comparison_cells_from_pairs(provider_pairs) if provider_comparison_valid else real_results[:4]
    common_controlled_variables = [
        "task_id",
        "source_tree_hash",
        "final_verifier_plan_ref",
        "tool_policy_id",
        "context_policy_id",
        "environment_id",
        "scaffold_id",
        "budget_policy_id",
    ]
    matrix_refs = [
        _artifact_ref_for_input(path, "v5_run_matrix_manifest_executed", "inspect-v5-run-matrix")
        for path in manifest_paths
    ]
    result_refs = [
        _artifact_ref_for_input(path, "v5_matrix_cell_results", "inspect-v5-run-matrix")
        for path in result_paths
    ]
    matrix_ref = matrix_refs[0]
    results_evidence_ref = result_refs[0]
    provider_gate_ref = _artifact_ref_for_input(provider_gate_path, "v5_provider_credential_gate_report", "inspect-v5-provider-gate")

    compare_scope_path = root / "v5_matrix_compare_scope_report.json"
    compare_scope = {
        "schema_version": V5_MATRIX_COMPARE_SCOPE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3c_comparison_reports",
        "comparison_axis": "provider" if provider_comparison_valid else "diagnostic_baseline",
        "controlled_variables": common_controlled_variables,
        "compared_cells": [item["cell_id"] for item in comparison_cells],
        "compared_task_ids": (
            [pair["task_id"] for pair in provider_pairs]
            if provider_comparison_valid
            else [item["task_id"] for item in comparison_cells]
        ),
        "comparison_validity": "valid" if provider_comparison_valid else "diagnostic_only",
        "comparison_validity_reason": (
            "Stage 3C has at least two tasks with DeepSeek and OpenAI real provider runs "
            "under matching task, scaffold, budget, tool, context, environment, source tree, "
            "and final verifier plan variables."
            if provider_comparison_valid
            else (
                "Stage 3C has one real provider family and one scaffold/budget shape; "
                "the report proves controlled-variable binding for four real provider tasks "
                "but does not support multi-provider, scaffold, or budget win-rate claims."
            )
        ),
        "counts_toward_core_comparison_proof": True,
        "provider_axis_comparison_satisfied": provider_comparison_valid,
        "counts_toward_resume_ready_provider_comparison": False,
        "resume_ready_boundary_note": (
            "Provider-axis proof is valid for this report, but it does not by itself satisfy "
            "overall resume-ready acceptance because scaffold, budget, preference and trainable "
            "export gates remain separate."
            if provider_comparison_valid
            else "Provider-axis proof is blocked because two DeepSeek/OpenAI task pairs are missing."
        ),
        "run_matrix_manifest_ref": matrix_ref,
        "matrix_cell_results_ref": results_evidence_ref,
        "run_matrix_manifest_refs": matrix_refs,
        "matrix_cell_results_refs": result_refs,
        "provider_pair_count": len(provider_pairs),
    }
    _write_json(compare_scope_path, compare_scope)

    provider_report_path = root / "v5_provider_comparison_report.json"
    provider_report = {
        "schema_version": V5_PROVIDER_COMPARISON_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3c_comparison_reports",
        "comparison_axis": "provider",
        "comparison_validity": "valid" if provider_comparison_valid else "invalid",
        "controlled_variables": [
            "task_id",
            "source_tree_hash",
            "final_verifier_plan_ref",
            "tool_policy_id",
            "context_policy_id",
            "scaffold_id",
            "budget_policy_id",
            "environment_id",
        ],
        "compared_cells": [item["cell_id"] for item in _comparison_cells_from_pairs(provider_pairs)],
        "compared_task_ids": [pair["task_id"] for pair in provider_pairs],
        "provider_pairs": provider_pairs,
        "provider_families_with_actual_runs": real_provider_families,
        "actual_records_by_provider": actual_records_by_provider,
        "required_provider_axis_shape": "2 tasks x 2 real provider families x same scaffold x same budget",
        "provider_axis_comparison_satisfied": provider_comparison_valid,
        "resume_ready_provider_comparison_satisfied": False,
        "blocking_reason": (
            "provider_axis_only_not_overall_resume_ready_acceptance"
            if provider_comparison_valid
            else "missing_two_task_deepseek_openai_provider_pairs"
        ),
        "provider_gate_ref": provider_gate_ref,
        "run_matrix_manifest_ref": matrix_ref,
        "matrix_cell_results_ref": results_evidence_ref,
        "run_matrix_manifest_refs": matrix_refs,
        "matrix_cell_results_refs": result_refs,
        "structured_skips": provider_gate.get("structured_skips", []),
        "counts_toward_core_real_provider_floor": False,
        "counts_toward_resume_ready_acceptance": False,
        "resume_ready_boundary_note": (
            "This report proves the provider axis only. It must not be used as evidence that "
            "overall resume-ready acceptance, scaffold comparison, budget comparison, preference "
            "export or trainable export completed."
        ),
    }
    _write_json(provider_report_path, provider_report)

    scaffold_report_path = root / "v5_scaffold_comparison_report.json"
    scaffold_report = _blocked_axis_report(
        axis="scaffold",
        observed_values=sorted({str(item["scaffold_id"]) for item in real_results}),
        required_shape="2 tasks x 2 scaffold policies x same provider x same budget",
        blocking_reason="stage3b_executed_only_simple_react_cells",
        matrix_ref=matrix_ref,
        results_ref=results_evidence_ref,
    )
    _write_json(scaffold_report_path, scaffold_report)

    budget_report_path = root / "v5_budget_comparison_report.json"
    budget_report = _blocked_axis_report(
        axis="budget",
        observed_values=sorted({str(item["budget_policy_id"]) for item in real_results}),
        required_shape="2 tasks x 2 budget policies x same provider x same scaffold",
        blocking_reason="stage3b_executed_only_constrained_budget_cells",
        matrix_ref=matrix_ref,
        results_ref=results_evidence_ref,
    )
    _write_json(budget_report_path, budget_report)

    claim_gate_path = root / "v5_resume_claim_gate_report.json"
    allowed_claims = [
        "core real provider floor satisfied with real provider family evidence",
        "credential-gated provider registry with structured skips",
    ]
    blocked_claims = [
        "resume-ready provider comparison" if not provider_comparison_valid else None,
        "scaffold comparison conclusion",
        "budget comparison conclusion",
        "preference export completed",
        "interview-grade evaluation pack",
        "resumable export stress tests",
    ]
    if provider_comparison_valid:
        allowed_claims.extend(
            [
                "provider-axis supplemental comparison proof for two tasks across DeepSeek and OpenAI",
            ]
        )
        blocked_claims.extend(
            [
                "resume-ready multi-provider comparison",
                "controlled multi-provider comparison completed",
            ]
        )
    else:
        blocked_claims.extend(["multi-provider agent runs", "controlled multi-provider comparison"])
    claim_gate = {
        "schema_version": V5_RESUME_CLAIM_GATE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "stage": "stage3_partial",
        "allowed_claims": allowed_claims,
        "blocked_claims": [claim for claim in blocked_claims if claim],
        "blocking_reasons": {
            "provider": None if provider_comparison_valid else "missing two-task DeepSeek/OpenAI provider pairs",
            "scaffold": "no alternate scaffold cells have been executed yet",
            "budget": "no alternate budget cells have been executed yet",
            "preference_pair": "pending Stage 4 export pack",
            "demo_share_safe": "pending Stage 5 public-safe demo artifacts",
            "stress_test": "not claimed in Stage 3C",
        },
        "provider_claim_status": (
            "provider_axis_satisfied_two_task_deepseek_openai_pairs"
            if provider_comparison_valid
            else "blocked_missing_two_task_deepseek_openai_provider_pairs"
        ),
        "preference_pair_claim_status": "pending_stage4",
        "demo_share_safe_status": "pending_stage5",
        "stress_test_claim_status": "not_claimed",
        "source_reports": [
            *matrix_refs,
            *result_refs,
            provider_gate_ref,
            _evidence_ref(compare_scope_path, kind="v5_matrix_compare_scope_report", purpose="Stage 3C provider comparison scope", visibility="audit_only", producer_command="build-v5-comparison-reports", producer_stage="v5_stage3c_comparison_reports", inspect_command="inspect-v5-run-matrix"),
            _evidence_ref(provider_report_path, kind="v5_provider_comparison_report", purpose="Stage 3C provider comparison report", visibility="audit_only", producer_command="build-v5-comparison-reports", producer_stage="v5_stage3c_comparison_reports", inspect_command="inspect-v5-run-matrix"),
            _evidence_ref(scaffold_report_path, kind="v5_scaffold_comparison_report", purpose="Stage 3C scaffold comparison blocked report", visibility="audit_only", producer_command="build-v5-comparison-reports", producer_stage="v5_stage3c_comparison_reports", inspect_command="inspect-v5-run-matrix"),
            _evidence_ref(budget_report_path, kind="v5_budget_comparison_report", purpose="Stage 3C budget comparison blocked report", visibility="audit_only", producer_command="build-v5-comparison-reports", producer_stage="v5_stage3c_comparison_reports", inspect_command="inspect-v5-run-matrix"),
        ],
        "core_comparison_proof": {
            "status": "provider_valid" if provider_comparison_valid else "diagnostic_only",
            "task_count": len(provider_pairs) if provider_comparison_valid else len(comparison_cells),
            "comparison_axis": "provider" if provider_comparison_valid else "diagnostic_baseline",
        },
        "real_provider_families_with_actual_runs": real_provider_families,
        "actual_records_by_provider": actual_records_by_provider,
        "provider_axis_comparison_satisfied": provider_comparison_valid,
        "resume_ready_provider_comparison_satisfied": False,
    }
    _write_json(claim_gate_path, claim_gate)

    command_entry = _builder_command_log_entry(
        command_name="build-v5-comparison-reports",
        input_paths=[*manifest_paths, provider_gate_path],
        output_paths=[
            compare_scope_path,
            provider_report_path,
            scaffold_report_path,
            budget_report_path,
            claim_gate_path,
        ],
        producer_stage="v5_stage3c_comparison_reports",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "build_v5_comparison_reports_command_log_entry.json"
    command_log_path = root / "v5_stage3c_comparison_reports_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return compare_scope_path


def _run_one_cell(
    *,
    cell: dict[str, Any],
    task_yaml_path: Path,
    config_path: Path,
    agent_runs_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    started_at = _utc_timestamp()
    failure: str | None = None
    run_dir: Path | None = None
    try:
        run_dir = _run_minimal_provider_agent_loop(
            cell=cell,
            task_yaml_path=task_yaml_path,
            config_path=config_path,
            agent_runs_dir=agent_runs_dir,
            run_id=run_id,
        )
    except RepoHarnessError as exc:
        failure = str(exc)
    finished_at = _utc_timestamp()
    if run_dir is None:
        return {
            "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
            **_cell_identity(cell, run_id=run_id),
            "run_dir": None,
            "final_verifier_status": None,
            "trajectory_ref": None,
            "final_verifier_boundary_ref": None,
            "controlled_variables_ref": cell["controlled_variables_ref"],
            "normalized_provider_status": (
                "credential_missing_skip" if failure and "凭证" in failure else "provider_error"
            ),
            "actual_provider_call_count": 0,
            "provider_api_called": False,
            "counts_toward_primary_accepted_rate": False,
            "counts_toward_core_real_provider_floor": False,
            "failure_owner": "provider_error",
            "failure_category": "run_task_failed",
            "failure_message_preview": (failure or "")[:500],
            "started_at": started_at,
            "finished_at": finished_at,
        }
    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    artifacts = _read_json(run_dir / "artifacts.json")
    provider_call_events = [
        event for event in events
        if event.get("event_type") == "model_call_completed"
        and event.get("data", {}).get("provider") == cell["provider_id"]
    ]
    model_error_type = next(
        (
            event.get("data", {}).get("model_error_type")
            for event in provider_call_events
            if event.get("data", {}).get("model_error_type")
        ),
        None,
    )
    status = "provider_error" if model_error_type or not provider_call_events else "primary_attempted"
    final_verifier_path = run_dir / "final_verifier_boundary.json"
    result = {
        "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
        **_cell_identity(cell, run_id=run_id),
        "run_dir": run_dir.as_posix(),
        "final_verifier_status": metrics.get("final_verifier_status"),
        "trajectory_ref": _evidence_ref(
            run_dir / "events.jsonl",
            kind="trajectory_events",
            purpose=f"Trajectory events for {run_id}",
            visibility="audit_only",
            producer_command="run-v5-run-matrix",
            producer_stage="v5_stage3b_real_provider_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        ),
        "transcript_ref": _evidence_ref(
            run_dir / "transcript.jsonl",
            kind="trajectory_transcript",
            purpose=f"Transcript for {run_id}",
            visibility="audit_only",
            producer_command="run-v5-run-matrix",
            producer_stage="v5_stage3b_real_provider_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        ),
        "artifact_manifest_ref": _evidence_ref(
            run_dir / "artifacts.json",
            kind="artifact_manifest",
            purpose=f"Artifact manifest for {run_id}",
            visibility="audit_only",
            producer_command="run-v5-run-matrix",
            producer_stage="v5_stage3b_real_provider_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        ),
        "final_verifier_boundary_ref": _evidence_ref(
            final_verifier_path,
            kind="final_verifier_boundary",
            purpose=f"Final verifier boundary for {run_id}",
            visibility="evaluator_only",
            producer_command="run-v5-run-matrix",
            producer_stage="v5_stage3b_real_provider_run_matrix",
            inspect_command="inspect-v5-run-matrix",
        ) if final_verifier_path.exists() else None,
        "controlled_variables_ref": cell["controlled_variables_ref"],
        "normalized_provider_status": status,
        "actual_provider_call_count": len(provider_call_events),
        "provider_api_called": bool(provider_call_events),
        "model_error_type": model_error_type,
        "token_usage": _token_usage(provider_call_events),
        "tool_call_count": metrics.get("tool_call_count", 0),
        "test_run_count": metrics.get("test_run_count", 0),
        "invalid_tool_call_count": metrics.get("invalid_tool_call_count", 0),
        "permission_denial_count": metrics.get("permission_denial_count", 0),
        "patch_stats": metrics.get("patch_stats", {}),
        "raw_provider_redaction": _raw_provider_redaction_facts(run_dir, artifacts),
        "counts_toward_primary_accepted_rate": False,
        "counts_toward_core_real_provider_floor": bool(provider_call_events),
        "started_at": started_at,
        "finished_at": finished_at,
    }
    return result


def _run_minimal_provider_agent_loop(
    *,
    cell: dict[str, Any],
    task_yaml_path: Path,
    config_path: Path,
    agent_runs_dir: Path,
    run_id: str,
) -> Path:
    """Run one audited one-turn provider-backed AgentLoop cell for Stage 3B."""

    task_yaml = _read_yaml(task_yaml_path)
    run_dir = agent_runs_dir / run_id
    if run_dir.exists():
        raise ConfigError(f"Stage 3B run directory 已存在，不能覆盖：{run_dir}")
    model_config = ModelConfig(
        provider=str(cell["provider_id"]),
        model_id=str(cell["model_id"]),
        temperature=0.0,
        max_output_tokens=512,
        retry_policy="none",
        credential_policy="local_secret_file_redacted",
        provider_request_logging="redact_secrets",
        provider_specific_options=_provider_specific_options_for_cell(cell, allow_local_secret_file=True),
    )
    budget_manager = BudgetManager(
        max_turns=1,
        max_tool_calls=0,
        max_test_runs=0,
        task_timeout_sec=240,
        command_timeout_sec=60,
        verifier_timeout_sec=120,
        max_tool_output_chars=12000,
        max_context_tokens=120000,
        max_output_tokens=512,
    )
    with RunRecorder(run_id=run_id, run_dir=run_dir, task_id=cell["task_id"]) as recorder:
        run_config_facts_ref = _write_minimal_run_config_facts(
            run_dir=run_dir,
            cell=cell,
            config_path=config_path,
            task_yaml_path=task_yaml_path,
        )
        tool_schema_snapshot_ref = recorder.write_json_artifact(
            "tool_schema_snapshot",
            {
                "schema_version": "repo_harness_v5_stage3b_tool_schema_snapshot_v0",
                "allowed_tools": [],
                "tool_policy_id": cell["tool_policy_id"],
                "reason": "Stage 3B core provider floor uses a one-turn no-tool-call loop.",
            },
            {"budget_policy": "preserve_json"},
        )
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("run"),
                timestamp=_utc_timestamp(),
                run_id=run_id,
                task_id=cell["task_id"],
                event_type="run_started",
                data={
                    "producer_stage": "v5_stage3b_real_provider_run_matrix",
                    "execution_path": "minimal_provider_agent_loop",
                    "task_yaml": task_yaml_path.as_posix(),
                    "config_path": config_path.as_posix(),
                    "final_verifier_mode": "boundary_recorded_not_executed",
                },
            )
        )
        tool_context = ToolExecutionContext(
            run_id=run_id,
            task_id=cell["task_id"],
            workspace_facade=None,  # type: ignore[arg-type]
            run_workspace=None,  # type: ignore[arg-type]
            artifact_writer=recorder,
            permission_context=PermissionContext(
                mode="deny",
                network_policy="deny_agent_run",
                test_command="not_exposed_to_model",
            ),
            verifier_feedback_facade=None,  # type: ignore[arg-type]
            resolved_verifier_plan=None,  # type: ignore[arg-type]
            output_limits=ToolOutputLimits(max_tool_output_chars=12000),
            budget_manager=budget_manager,
        )
        state = AgentLoop(
            model_client=create_model_client(model_config),
            tool_executor=ToolExecutor(),
            scaffold=build_scaffold("simple_react"),
            allowed_tool_names=[],
            test_feedback_policy="disabled",
            feedback_tests_passed_policy="require_model_final",
            hidden_feedback_visible_to_model=False,
        ).run(
            run_id=run_id,
            task_id=cell["task_id"],
            initial_messages=_stage3b_initial_messages(cell=cell, task_yaml=task_yaml),
            tool_context=tool_context,
            recorder=recorder,
            max_turns=1,
            context_config=ContextManagementConfig(),
            budget_manager=budget_manager,
            run_config_facts_ref=run_config_facts_ref,
            tool_schema_snapshot_ref=tool_schema_snapshot_ref,
            provider_options=provider_options_from_model_config(model_config),
            generation_config={
                "temperature": model_config.temperature,
                "max_output_tokens": model_config.max_output_tokens,
                "seed": 42,
            },
            provider_model_settings={},
            request_timeout_seconds=240.0,
            raw_request_logging_policy=model_config.provider_request_logging,
            retry_policy=model_config.retry_policy,
        )
        _write_stage3b_boundary_and_metrics(
            run_dir=run_dir,
            recorder=recorder,
            cell=cell,
            run_id=run_id,
            state=state,
            run_config_facts_ref=run_config_facts_ref,
        )
    return run_dir


def _run_one_accepted_provider_cell(
    *,
    cell: dict[str, Any],
    task: dict[str, Any],
    adapter_visible: dict[str, Any],
    verifier_entry: dict[str, Any],
    config_path: Path,
    agent_runs_dir: Path,
    run_id: str,
    allow_local_secret_file: bool,
    max_turns: int,
    max_tool_calls: int,
    max_output_tokens: int,
) -> dict[str, Any]:
    started_at = _utc_timestamp()
    run_dir = agent_runs_dir / run_id
    if run_dir.exists():
        raise ConfigError(f"accepted provider run directory 已存在，不能覆盖：{run_dir}")
    model_error: str | None = None
    try:
        _run_accepted_provider_agent_loop(
            cell=cell,
            task=task,
            adapter_visible=adapter_visible,
            verifier_entry=verifier_entry,
            config_path=config_path,
            agent_runs_dir=agent_runs_dir,
            run_id=run_id,
            allow_local_secret_file=allow_local_secret_file,
            max_turns=max_turns,
            max_tool_calls=max_tool_calls,
            max_output_tokens=max_output_tokens,
        )
    except RepoHarnessError as exc:
        model_error = str(exc)
    finished_at = _utc_timestamp()
    if not run_dir.exists():
        return {
            "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
            **_cell_identity(cell, run_id=run_id),
            "run_dir": None,
            "accepted": False,
            "final_verifier_ran": False,
            "final_verifier_status": None,
            "final_verifier_mode": "strict_patch_replay",
            "trajectory_ref": None,
            "final_verifier_boundary_ref": None,
            "controlled_variables_ref": cell["controlled_variables_ref"],
            "normalized_provider_status": "credential_missing_skip" if model_error and "凭证" in model_error else "provider_error",
            "actual_provider_call_count": 0,
            "provider_api_called": False,
            "counts_toward_primary_accepted_rate": False,
            "counts_toward_core_real_provider_floor": False,
            "failure_owner": "provider_error",
            "failure_category": "accepted_run_failed_before_provider_call",
            "failure_message_preview": (model_error or "")[:500],
            "started_at": started_at,
            "finished_at": finished_at,
        }
    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    artifacts = _read_json(run_dir / "artifacts.json")
    provider_call_events = [
        event for event in events
        if event.get("event_type") == "model_call_completed"
        and event.get("data", {}).get("provider") == cell["provider_id"]
    ]
    model_error_type = next(
        (
            event.get("data", {}).get("model_error_type")
            for event in provider_call_events
            if event.get("data", {}).get("model_error_type")
        ),
        None,
    )
    accepted = metrics.get("final_verifier_status") == "accepted" and metrics.get("accepted") is True
    status = "provider_error" if model_error_type or model_error else "primary_attempted"
    final_verifier_path = run_dir / "final_verifier_boundary.json"
    final_result_path = run_dir / "final_verifier_result.json"
    final_patch_path = run_dir / "final.patch"
    final_diff_path = run_dir / "final.diff"
    result = {
        "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
        **_cell_identity(cell, run_id=run_id),
        "run_dir": run_dir.as_posix(),
        "accepted": accepted,
        "final_verifier_ran": metrics.get("final_verifier_ran") is True,
        "final_verifier_status": metrics.get("final_verifier_status"),
        "final_verifier_mode": "strict_patch_replay",
        "run_outcome": metrics.get("run_outcome"),
        "trajectory_ref": _evidence_ref(
            run_dir / "events.jsonl",
            kind="trajectory_events",
            purpose=f"Trajectory events for accepted provider run {run_id}",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ),
        "transcript_ref": _evidence_ref(
            run_dir / "transcript.jsonl",
            kind="trajectory_transcript",
            purpose=f"Transcript for accepted provider run {run_id}",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ),
        "artifact_manifest_ref": _evidence_ref(
            run_dir / "artifacts.json",
            kind="artifact_manifest",
            purpose=f"Artifact manifest for accepted provider run {run_id}",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ),
        "final_verifier_boundary_ref": _evidence_ref(
            final_verifier_path,
            kind="final_verifier_boundary",
            purpose=f"Final verifier boundary for accepted provider run {run_id}",
            visibility="evaluator_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ) if final_verifier_path.exists() else None,
        "final_verifier_result_ref": _evidence_ref(
            final_result_path,
            kind="final_verifier_result",
            purpose=f"Final verifier result for accepted provider run {run_id}",
            visibility="evaluator_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ) if final_result_path.exists() else None,
        "final_patch_ref": _evidence_ref(
            final_patch_path,
            kind="final_patch",
            purpose=f"Final provider patch for accepted provider run {run_id}",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ) if final_patch_path.exists() else None,
        "final_diff_ref": _evidence_ref(
            final_diff_path,
            kind="final_diff",
            purpose=f"Final provider diff for accepted provider run {run_id}",
            visibility="audit_only",
            producer_command="run-v5-accepted-provider-task",
            producer_stage="v5_stage3b_accepted_provider_run",
            inspect_command="inspect-v5-run-matrix",
        ) if final_diff_path.exists() else None,
        "controlled_variables_ref": cell["controlled_variables_ref"],
        "normalized_provider_status": status,
        "actual_provider_call_count": len(provider_call_events),
        "provider_api_called": bool(provider_call_events),
        "model_error_type": model_error_type,
        "token_usage": _token_usage(provider_call_events),
        "tool_call_count": metrics.get("tool_call_count", 0),
        "test_run_count": metrics.get("test_run_count", 0),
        "invalid_tool_call_count": metrics.get("invalid_tool_call_count", 0),
        "permission_denial_count": metrics.get("permission_denial_count", 0),
        "patch_stats": metrics.get("patch_stats", {}),
        "raw_provider_redaction": _raw_provider_redaction_facts(run_dir, artifacts),
        "counts_toward_primary_accepted_rate": accepted,
        "counts_toward_core_real_provider_floor": bool(provider_call_events),
        "failure_owner": None if accepted else metrics.get("failure_owner", "model_behavior"),
        "failure_category": None if accepted else metrics.get("failure_category", "final_verifier_rejected"),
        "started_at": started_at,
        "finished_at": finished_at,
    }
    return result


def _run_accepted_provider_agent_loop(
    *,
    cell: dict[str, Any],
    task: dict[str, Any],
    adapter_visible: dict[str, Any],
    verifier_entry: dict[str, Any],
    config_path: Path,
    agent_runs_dir: Path,
    run_id: str,
    allow_local_secret_file: bool,
    max_turns: int,
    max_tool_calls: int,
    max_output_tokens: int,
) -> None:
    run_dir = agent_runs_dir / run_id
    model_config = ModelConfig(
        provider=str(cell["provider_id"]),
        model_id=str(cell["model_id"]),
        temperature=0.0,
        max_output_tokens=max_output_tokens,
        retry_policy="none",
        credential_policy="local_secret_file_redacted" if allow_local_secret_file else "env_only",
        provider_request_logging="redact_secrets",
        provider_specific_options=_provider_specific_options_for_cell(
            cell,
            allow_local_secret_file=allow_local_secret_file,
        ),
    )
    run_config = RunConfig(
        run_id_prefix="v5_accepted",
        model=model_config,
        runtime=RuntimeConfig(
            scaffold_id="patch_focused_react",
            permission_mode="auto",
            test_feedback_policy="disabled",
            feedback_tests_passed_policy="require_model_final",
            max_turns=max_turns,
            max_tool_calls=max_tool_calls,
            max_test_runs=0,
            task_timeout_sec=900,
            seed=42,
        ),
        workspace=WorkspaceConfig(
            output_dir=agent_runs_dir.as_posix(),
            keep_workspace=True,
            default_command_timeout_sec=90,
            max_tool_output_chars=16000,
            network_policy="deny_agent_run",
        ),
        evaluation=EvaluationConfig(final_verifier_mode="strict_patch_replay"),
        context_management=ContextManagementConfig(max_context_tokens=120000),
    )
    runnable = _runnable_task_for_accepted_run(task=task, adapter_visible=adapter_visible)
    resolved_plan = ResolvedVerifierPlan(
        verifier_config=runnable.verifier_config,
        initial_fail_to_pass_tests=[],
        initial_pass_to_pass_tests=[],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id=f"{run_id}_strict_replay_final_only",
    )
    scaffold = build_scaffold("patch_focused_react")
    feedback_policy = resolve_feedback_policy(run_config=run_config, scaffold=scaffold, task=runnable)
    allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    budget_manager = BudgetManager(
        max_turns=max_turns,
        max_tool_calls=max_tool_calls,
        max_test_runs=0,
        task_timeout_sec=900,
        command_timeout_sec=90,
        verifier_timeout_sec=2400,
        max_tool_output_chars=16000,
        max_context_tokens=120000,
        max_output_tokens=max_output_tokens,
    )
    adapter = None
    with RunRecorder(run_id=run_id, run_dir=run_dir, task_id=cell["task_id"]) as recorder:
        adapter = _accepted_workspace_adapter(run_id=run_id, run_dir=run_dir)
        source = adapter.create_source_checkout(runnable)
        dependency_state = adapter.capture_dependency_state(strategy="none")
        run_config_facts_ref = _write_accepted_run_config_facts(
            run_dir=run_dir,
            cell=cell,
            config_path=config_path,
            verifier_entry=verifier_entry,
            allowed_tools=allowed_tools,
        )
        baseline_workspace = adapter.workspaces_dir / "baseline_verifier_workspace"
        shutil.copytree(source, baseline_workspace)
        baseline_patch_result = _apply_evaluator_patch(
            adapter=adapter,
            workspace=baseline_workspace,
            patch_path=_test_patch_path_from_verifier_entry(verifier_entry),
            recorder=recorder,
            command_semantics="baseline_hidden_test_patch_apply",
        )
        baseline_verifier = _run_v5_external_verifier(
            run_dir=run_dir,
            workspace=baseline_workspace,
            verifier_entry=verifier_entry,
            stage="baseline",
            command_id=f"{run_id}_baseline_strict_replay_command",
        )
        run_workspace = adapter.create_agent_workspace(
            task=runnable,
            source_checkout=source,
            dependency_state=dependency_state,
            setup_command=None,
            recorder=recorder,
        )
        registry = tool_registry_for_allowed_tools(allowed_tools)
        _, tool_schema_snapshot_ref, _ = write_tool_schema_snapshot(recorder, registry=registry)
        initial_messages = ContextBuilder().build_initial_messages(
            task=runnable,
            workspace=run_workspace,
            run_config=run_config,
            resolved_verifier_plan=resolved_plan,
            allowed_tools=allowed_tools,
            scaffold=scaffold,
            workspace_facade=adapter,
        )
        state = AgentLoop(
            model_client=create_model_client(model_config),
            tool_executor=ToolExecutor(registry=registry),
            scaffold=scaffold,
            allowed_tool_names=allowed_tools,
            test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
            feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
            hidden_feedback_visible_to_model=False,
        ).run(
            run_id=run_id,
            task_id=cell["task_id"],
            initial_messages=initial_messages,
            tool_context=ToolExecutionContext(
                run_id=run_id,
                task_id=cell["task_id"],
                workspace_facade=adapter,
                run_workspace=run_workspace,
                artifact_writer=recorder,
                permission_context=PermissionContext(
                    mode="auto",
                    network_policy="deny_agent_run",
                    test_command="hidden_final_verifier_not_model_visible",
                ),
                verifier_feedback_facade=None,  # type: ignore[arg-type]
                resolved_verifier_plan=resolved_plan,
                output_limits=ToolOutputLimits(max_tool_output_chars=16000),
                test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
                feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
                budget_manager=budget_manager,
            ),
            recorder=recorder,
            max_turns=max_turns,
            context_config=ContextManagementConfig(max_context_tokens=120000),
            budget_manager=budget_manager,
            run_config_facts_ref=run_config_facts_ref,
            tool_schema_snapshot_ref=tool_schema_snapshot_ref,
            provider_options=provider_options_from_model_config(model_config),
            generation_config={
                "temperature": model_config.temperature,
                "max_output_tokens": model_config.max_output_tokens,
                "seed": 42,
            },
            provider_model_settings={},
            request_timeout_seconds=900.0,
            raw_request_logging_policy=model_config.provider_request_logging,
            retry_policy=model_config.retry_policy,
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        verification_error: str | None = None
        final_patch_apply_result: dict[str, Any] | None = None
        final_hidden_patch_result: dict[str, Any] | None = None
        final_verifier: dict[str, Any]
        try:
            verification = adapter.create_verification_workspace(
                source_checkout=source,
                dependency_state=dependency_state,
                final_patch_path=capture.patch_path,
                setup_command=None,
                recorder=recorder,
            )
            final_patch_apply_result = {"exit_code": 0, "timeout": False, "status": "applied_by_create_verification_workspace"}
            hidden_apply = _apply_evaluator_patch(
                adapter=adapter,
                workspace=verification,
                patch_path=_test_patch_path_from_verifier_entry(verifier_entry),
                recorder=recorder,
                command_semantics="final_hidden_test_patch_apply",
            )
            final_hidden_patch_result = hidden_apply.model_dump(mode="json")
            final_verifier = _run_v5_external_verifier(
                run_dir=run_dir,
                workspace=verification,
                verifier_entry=verifier_entry,
                stage="final",
                command_id=f"{run_id}_final_strict_replay_command",
            )
        except RepoHarnessError as exc:
            verification_error = str(exc)
            final_verifier = _external_verifier_error(
                stage="final",
                command_id=f"{run_id}_final_strict_replay_command",
                error_type="verification_workspace_error",
                message=verification_error,
            )
        final_result_path = run_dir / "final_verifier_result.json"
        _write_json(final_result_path, final_verifier)
        baseline_result_path = run_dir / "baseline_verifier_result.json"
        _write_json(
            baseline_result_path,
            {
                "schema_version": "repo_harness_v5_accepted_provider_baseline_verifier_result_v0",
                "baseline_hidden_patch_apply_result": baseline_patch_result.model_dump(mode="json"),
                "baseline_verifier_result": baseline_verifier,
                "baseline_expected_failure": baseline_verifier.get("exit_code") not in {0, None},
            },
        )
        baseline_hidden_patch_apply_ok = _command_result_ok(baseline_patch_result.model_dump(mode="json"))
        final_hidden_patch_apply_ok = _command_result_ok(final_hidden_patch_result)
        baseline_failed = baseline_verifier.get("exit_code") not in {0, None}
        final_exit_zero = final_verifier.get("exit_code") == 0 and final_verifier.get("timed_out") is False
        patch_nonempty = bool(capture.patch_text.strip())
        provider_call_count = sum(
            1
            for event in _read_jsonl(run_dir / "events.jsonl")
            if event.get("event_type") == "model_call_completed"
            and event.get("data", {}).get("provider") == cell["provider_id"]
        )
        accepted = (
            baseline_hidden_patch_apply_ok
            and final_hidden_patch_apply_ok
            and baseline_failed
            and final_exit_zero
            and patch_nonempty
            and provider_call_count > 0
        )
        final_status = "accepted" if accepted else ("failed" if final_verifier.get("exit_code") not in {None, 0} else "error")
        boundary_path = run_dir / "final_verifier_boundary.json"
        _write_json(
            boundary_path,
            {
                "schema_version": "repo_harness_v5_accepted_provider_final_verifier_boundary_v0",
                "run_id": run_id,
                "task_id": cell["task_id"],
                "authoritative_final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
                "final_verifier_ran": True,
                "final_verifier_mode": "strict_patch_replay",
                "final_verifier_status": final_status,
                "accepted": accepted,
                "accepted_authority": "final_verifier_only",
                "counts_toward_primary_accepted_rate": accepted,
                "baseline_expected_failure": baseline_failed,
                "baseline_hidden_patch_apply_ok": baseline_hidden_patch_apply_ok,
                "final_hidden_patch_apply_ok": final_hidden_patch_apply_ok,
                "provider_final_patch_nonempty": patch_nonempty,
                "provider_api_called": provider_call_count > 0,
                "final_verifier_result_ref": _evidence_ref(
                    final_result_path,
                    kind="final_verifier_result",
                    purpose=f"Strict replay final verifier result for {run_id}",
                    visibility="evaluator_only",
                    producer_command="run-v5-accepted-provider-task",
                    producer_stage="v5_stage3b_accepted_provider_run",
                    inspect_command="inspect-v5-run-matrix",
                ),
                "baseline_verifier_result_ref": _evidence_ref(
                    baseline_result_path,
                    kind="baseline_verifier_result",
                    purpose=f"Baseline hidden-test verifier result for {run_id}",
                    visibility="evaluator_only",
                    producer_command="run-v5-accepted-provider-task",
                    producer_stage="v5_stage3b_accepted_provider_run",
                    inspect_command="inspect-v5-run-matrix",
                ),
                "hidden_test_patch_ref": _evidence_ref(
                    _test_patch_path_from_verifier_entry(verifier_entry),
                    kind="evaluator_only_test_patch",
                    purpose=f"Evaluator-only test patch for {cell['task_id']}",
                    visibility="evaluator_only",
                    producer_command="external",
                    producer_stage="v5_stage3b_accepted_provider_run",
                    inspect_command="inspect-v5-run-matrix",
                ),
                "final_patch_apply_result": final_patch_apply_result,
                "baseline_hidden_patch_apply_result": baseline_patch_result.model_dump(mode="json"),
                "final_hidden_patch_apply_result": final_hidden_patch_result,
                "verification_error": verification_error,
            },
        )
        metrics = {
            "schema_version": "repo_harness_v5_accepted_provider_metrics_v0",
            "run_id": run_id,
            "task_id": cell["task_id"],
            "accepted": accepted,
            "run_outcome": "success" if accepted else "failed",
            "final_verifier_status": final_status,
            "final_verifier_ran": True,
            "final_verifier_mode": "strict_patch_replay",
            "agent_stop_reason": state.agent_stop_reason,
            "model_error_type": state.last_model_error,
            "turn_count": state.turn_count,
            "tool_call_count": state.tool_call_count,
            "test_run_count": state.budget_state.test_run_count,
            "invalid_tool_call_count": state.invalid_tool_call_count,
            "permission_denial_count": state.permission_denial_count,
            "patch_stats": capture.patch_stats,
            "failure_owner": None if accepted else "model_behavior",
            "failure_category": None if accepted else "final_verifier_rejected",
            "token_usage": {
                "input_tokens": state.budget_state.input_tokens,
                "output_tokens": state.budget_state.output_tokens,
                "cached_tokens": 0,
            },
            "interaction_efficiency": {
                "execution_path": "accepted_provider_patch_strict_replay",
                "budget_policy_id": cell["budget_policy_id"],
                "tool_policy_id": cell["tool_policy_id"],
                "context_policy_id": cell["context_policy_id"],
                "run_config_facts": run_config_facts_ref.relative_path,
            },
        }
        _write_json(run_dir / "metrics.json", metrics)
        recorder.append_event(
            TrajectoryEvent(
                event_id=recorder.next_event_id("run"),
                timestamp=_utc_timestamp(),
                run_id=run_id,
                task_id=cell["task_id"],
                event_type="run_finished",
                data={
                    "agent_stop_reason": state.agent_stop_reason,
                    "final_verifier_status": final_status,
                    "run_outcome": metrics["run_outcome"],
                    "accepted": accepted,
                },
            )
        )
        recorder.finalize_run(
            "# RepoHarness V5 Accepted Provider Run Summary\n\n"
            f"- run_id: {run_id}\n"
            f"- task_id: {cell['task_id']}\n"
            "- execution_path: accepted_provider_patch_strict_replay\n"
            f"- provider_id: {cell['provider_id']}\n"
            f"- model_id: {cell['model_id']}\n"
            f"- agent_stop_reason: {state.agent_stop_reason}\n"
            f"- final_verifier_status: {final_status}\n"
            f"- accepted: {str(accepted).lower()}\n"
        )


def _command_result_ok(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return result.get("exit_code") == 0 and result.get("timeout") is not True


def _write_minimal_run_config_facts(
    *,
    run_dir: Path,
    cell: dict[str, Any],
    config_path: Path,
    task_yaml_path: Path,
) -> RunConfigFactsRef:
    path = run_dir / "run_config_facts.json"
    _write_json(
        path,
        {
            "schema_version": "repo_harness_v5_stage3b_minimal_run_config_facts_v0",
            "provider_id": cell["provider_id"],
            "model_id": cell["model_id"],
            "scaffold_id": cell["scaffold_id"],
            "budget_policy_id": cell["budget_policy_id"],
            "tool_policy_id": cell["tool_policy_id"],
            "context_policy_id": cell["context_policy_id"],
            "environment_id": cell["environment_id"],
            "source_tree_hash": cell["source_tree_hash"],
            "final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
            "config_path": config_path.as_posix(),
            "task_yaml_path": task_yaml_path.as_posix(),
            "execution_path": "minimal_provider_agent_loop",
            "final_verifier_mode": "boundary_recorded_not_executed",
        },
    )
    return RunConfigFactsRef(sha256=sha256_file(path))


def _write_accepted_run_config_facts(
    *,
    run_dir: Path,
    cell: dict[str, Any],
    config_path: Path,
    verifier_entry: dict[str, Any],
    allowed_tools: list[str],
) -> RunConfigFactsRef:
    path = run_dir / "run_config_facts.json"
    _write_json(
        path,
        {
            "schema_version": "repo_harness_v5_accepted_provider_run_config_facts_v0",
            "provider_id": cell["provider_id"],
            "model_id": cell["model_id"],
            "scaffold_id": cell["scaffold_id"],
            "budget_policy_id": cell["budget_policy_id"],
            "tool_policy_id": cell["tool_policy_id"],
            "context_policy_id": cell["context_policy_id"],
            "environment_id": cell["environment_id"],
            "source_tree_hash": cell["source_tree_hash"],
            "final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
            "config_path": config_path.as_posix(),
            "execution_path": "accepted_provider_patch_strict_replay",
            "final_verifier_mode": "strict_patch_replay",
            "hidden_verifier_command_model_visible": False,
            "allowed_tools": allowed_tools,
            "verifier_candidate_id": verifier_entry.get("candidate_id"),
        },
    )
    return RunConfigFactsRef(sha256=sha256_file(path))


def _accepted_workspace_adapter(*, run_id: str, run_dir: Path) -> LocalWorkspaceAdapter:
    return LocalWorkspaceAdapter(
        run_id=run_id,
        run_dir=run_dir,
        default_command_timeout_sec=90,
        keep_workspace=True,
    )


def _runnable_task_for_accepted_run(*, task: dict[str, Any], adapter_visible: dict[str, Any]) -> RunnableTask:
    archive_ref = task.get("source_archive_ref")
    if not isinstance(archive_ref, dict):
        raise ConfigError(f"{task.get('task_id')} 缺少 source_archive_ref。")
    archive_path = Path(str(archive_ref["path"])).resolve()
    source = LocalArchiveSource(
        archive_path=archive_path.as_posix(),
        archive_sha256=str(archive_ref["sha256"]),
        expected_root_directory=_expected_root_directory(archive_path),
        base_commit=task.get("base_commit"),
        decontamination_status="manual_checked",
    )
    return RunnableTask(
        task_id=str(task["task_id"]),
        task_version=f"{task['task_id']}_accepted_provider_v0",
        dataset_name="repo_harness_v5",
        issue_statement=_accepted_issue_statement(adapter_visible),
        repo_source=archive_path.as_posix(),
        repo_source_spec=source,
        base_commit=task.get("base_commit"),
        source_archive_sha256=str(archive_ref["sha256"]),
        environment=EnvironmentSpec(
            execution_image="local_process_agent_workspace",
            package_manager=str(adapter_visible.get("ecosystem") or "unknown"),
            setup_network_policy="deny",
            source_archive_sha256=str(archive_ref["sha256"]),
        ),
        setup_command=None,
        timeouts=TaskTimeouts(
            setup_timeout_sec=60,
            test_timeout_sec=120,
            agent_timeout_sec=900,
            final_verifier_timeout_sec=2400,
        ),
        verifier_config=VerifierConfig(
            test_command="hidden_final_verifier_not_model_visible",
            test_timeout_sec=120,
            final_verifier_timeout_sec=2400,
            visibility_policy=VisibilityPolicy(
                issue="model_visible",
                expected_files="model_visible",
                fail_to_pass_tests="verifier_only",
                pass_to_pass_tests="verifier_only",
                gold_patch="hidden_reference",
            ),
        ),
        expected_files=[],
        mutation_policy=[],
        generated_files_policy=[],
        visibility_policy=VisibilityPolicy(
            issue="model_visible",
            expected_files="model_visible",
            fail_to_pass_tests="verifier_only",
            pass_to_pass_tests="verifier_only",
            gold_patch="hidden_reference",
        ),
        decontamination_metadata=DecontaminationMetadata(
            status="manual_checked",
            known_public_solution=None,
            source_url=task.get("repo_url_or_archive_id"),
            overlap_check_notes="V5 accepted-run uses sanitized adapter-visible task input only.",
        ),
        metadata={
            "source_kind": task.get("source_kind"),
            "dataset_split": "v5_stage3b_accepted_provider",
            "created_at": "2026-05-06",
            "final_only": True,
            "swe_bench_like_final_only": True,
            "tags": ["v5", "accepted_provider_run", "final_only", str(adapter_visible.get("ecosystem", "unknown"))],
        },
    )


def _apply_evaluator_patch(
    *,
    adapter: LocalWorkspaceAdapter,
    workspace: Path,
    patch_path: Path,
    recorder: RunRecorder,
    command_semantics: str,
) -> Any:
    return adapter.run_command(
        workspace,
        ["patch", "-p1", "-i", patch_path.as_posix(), "--forward"],
        timeout_sec=180,
        recorder=recorder,
        command_semantics=command_semantics,
        artifact_metadata={"redaction_status": "evaluator_only"},
    )


def _run_v5_external_verifier(
    *,
    run_dir: Path,
    workspace: Path,
    verifier_entry: dict[str, Any],
    stage: str,
    command_id: str,
) -> dict[str, Any]:
    command = _verifier_shell_command(verifier_entry)
    image = _verifier_image(verifier_entry)
    cache_dir = run_dir / "verifier_caches" / stage / "go"
    log_dir = run_dir / "verifier_logs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{command_id}.stdout.log"
    stderr_path = log_dir / f"{command_id}.stderr.log"
    argv = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-e",
        "CI=1",
        "-e",
        "TZ=UTC",
        "-v",
        f"{cache_dir.resolve()}:/go/pkg/mod",
        "-v",
        f"{workspace.resolve()}:/workspace",
        "-w",
        "/workspace",
        image,
        "sh",
        "-c",
        command,
    ]
    started_at = _utc_timestamp()
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            argv,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2400,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return {
        "schema_version": "repo_harness_v5_external_strict_replay_verifier_result_v0",
        "command_id": command_id,
        "stage": stage,
        "argv": _redacted_verifier_argv(argv),
        "cwd": ".",
        "exit_code": exit_code,
        "timed_out": timed_out,
        "timeout_seconds": 2400,
        "wall_time_seconds": round(time.monotonic() - started, 3),
        "started_at": started_at,
        "finished_at": _utc_timestamp(),
        "stdout_ref": _plain_file_ref(stdout_path),
        "stderr_ref": _plain_file_ref(stderr_path),
        "accepted": stage == "final" and exit_code == 0 and not timed_out,
    }


def _external_verifier_error(*, stage: str, command_id: str, error_type: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_external_strict_replay_verifier_result_v0",
        "command_id": command_id,
        "stage": stage,
        "argv": [],
        "cwd": ".",
        "exit_code": None,
        "timed_out": False,
        "timeout_seconds": 2400,
        "wall_time_seconds": 0.0,
        "started_at": _utc_timestamp(),
        "finished_at": _utc_timestamp(),
        "stdout_ref": None,
        "stderr_ref": None,
        "accepted": False,
        "error_type": error_type,
        "message": message[:500],
    }


def _plain_file_ref(path: Path) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind="verifier_command_log",
        purpose=f"Verifier command output log: {path.name}",
        visibility="evaluator_only",
        producer_command="run-v5-accepted-provider-task",
        producer_stage="v5_stage3b_accepted_provider_run",
        inspect_command="inspect-v5-run-matrix",
    )


def _redacted_verifier_argv(argv: list[str]) -> list[str]:
    redacted: list[str] = []
    for item in argv:
        if "/Users/" in item or item.startswith(str(Path.cwd())):
            redacted.append("<local-path-redacted>")
        else:
            redacted.append(item)
    return redacted


def _test_patch_path_from_verifier_entry(entry: dict[str, Any]) -> Path:
    patches = entry.get("patch_results", {}).get("baseline") or []
    for patch_result in patches:
        argv = patch_result.get("argv") or []
        if "-i" in argv:
            index = argv.index("-i")
            if index + 1 < len(argv):
                path = Path(str(argv[index + 1]))
                if path.exists():
                    return path
    raise ConfigError("accepted provider run 无法从 verifier entry 找到 evaluator-only test patch。")


def _verifier_shell_command(entry: dict[str, Any]) -> str:
    argv = (entry.get("final_verifier_result") or entry.get("baseline_verifier_result") or {}).get("argv") or []
    if "sh" in argv and "-c" in argv:
        index = argv.index("-c")
        if index + 1 < len(argv):
            return str(argv[index + 1])
    for item in argv:
        if isinstance(item, str) and "go test" in item:
            return item
    raise ConfigError("accepted provider run 无法从 verifier entry 找到 final verifier command。")


def _verifier_image(entry: dict[str, Any]) -> str:
    argv = (entry.get("final_verifier_result") or entry.get("baseline_verifier_result") or {}).get("argv") or []
    for item in argv:
        if isinstance(item, str) and item.startswith("golang:"):
            return item
    return "golang:1.24-bookworm"


def _verifier_entry_for_task(task: dict[str, Any]) -> dict[str, Any]:
    ref = task.get("final_verifier_plan_ref")
    path = _path_from_ref(ref)
    if path is None:
        raise ConfigError(f"{task.get('task_id')} 缺少 final_verifier_plan_ref。")
    report = _read_json(path)
    candidate_id = task.get("candidate_id")
    repository = task.get("repository")
    for entry in report.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if candidate_id and entry.get("candidate_id") == candidate_id:
            return entry
        if repository and str(entry.get("candidate_id", "")).startswith(str(repository)):
            return entry
    raise ConfigError(f"{task.get('task_id')} 的 verifier report 中找不到匹配 entry。")


def _stage3b_initial_messages(*, cell: dict[str, Any], task_yaml: dict[str, Any]) -> list[dict[str, object]]:
    model_visible_payload = {
        "schema_version": "repo_harness_v5_stage3b_model_visible_task_input_v0",
        "task_id": cell["task_id"],
        "task_statement": str(task_yaml.get("issue", "")).strip(),
        "source_tree_hash": cell["source_tree_hash"],
        "scaffold_id": cell["scaffold_id"],
        "budget_policy": "one turn, no tool calls, no test feedback",
        "allowed_tools": [],
        "instruction": (
            "Return a concise engineering plan or final answer based only on this sanitized task input. "
            "Keep the answer under 120 words. Do not invent hidden tests, gold patches, raw provider data, "
            "reward values, or verifier output."
        ),
    }
    return [
        {
            "role": "system",
            "content": (
                "You are running inside RepoHarness V5 Stage 3B. Use only model-visible task "
                "information. Hidden evaluator evidence, reward metadata, raw provider payloads, "
                "and post-patch verifier logs are unavailable."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(model_visible_payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def _write_stage3b_boundary_and_metrics(
    *,
    run_dir: Path,
    recorder: RunRecorder,
    cell: dict[str, Any],
    run_id: str,
    state: Any,
    run_config_facts_ref: RunConfigFactsRef,
) -> None:
    boundary = {
        "schema_version": "repo_harness_v5_stage3b_final_verifier_boundary_v0",
        "run_id": run_id,
        "task_id": cell["task_id"],
        "authoritative_final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
        "final_verifier_ran": False,
        "final_verifier_status": "not_executed_stage3b_minimal_provider_loop",
        "accepted": False,
        "accepted_authority": "final_verifier_only",
        "counts_toward_primary_accepted_rate": False,
        "reason": (
            "Stage 3B only establishes the core minimum real provider agent-loop evidence. "
            "It records the fixed verifier boundary but does not promote the run to accepted."
        ),
    }
    _write_json(run_dir / "final_verifier_boundary.json", boundary)
    _write_json(
        run_dir / "metrics.json",
        {
            "schema_version": "repo_harness_v5_stage3b_minimal_metrics_v0",
            "run_id": run_id,
            "task_id": cell["task_id"],
            "run_outcome": "diagnostic_only_real_provider_loop",
            "final_verifier_status": boundary["final_verifier_status"],
            "final_verifier_ran": False,
            "agent_stop_reason": state.agent_stop_reason,
            "model_error_type": state.last_model_error,
            "turn_count": state.turn_count,
            "tool_call_count": state.tool_call_count,
            "test_run_count": state.budget_state.test_run_count,
            "invalid_tool_call_count": state.invalid_tool_call_count,
            "permission_denial_count": state.permission_denial_count,
            "patch_stats": {},
            "token_usage": {
                "input_tokens": state.budget_state.input_tokens,
                "output_tokens": state.budget_state.output_tokens,
                "cached_tokens": 0,
            },
            "interaction_efficiency": {
                "execution_path": "minimal_provider_agent_loop",
                "budget_policy_id": cell["budget_policy_id"],
                "tool_policy_id": cell["tool_policy_id"],
                "context_policy_id": cell["context_policy_id"],
                "run_config_facts": run_config_facts_ref.relative_path,
            },
        },
    )
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("run"),
            timestamp=_utc_timestamp(),
            run_id=run_id,
            task_id=cell["task_id"],
            event_type="run_finished",
            data={
                "agent_stop_reason": state.agent_stop_reason,
                "final_verifier_status": boundary["final_verifier_status"],
                "run_outcome": "diagnostic_only_real_provider_loop",
                "accepted": False,
            },
        )
    )
    recorder.finalize_run(
        "# RepoHarness V5 Stage 3B Run Summary\n\n"
        f"- run_id: {run_id}\n"
        f"- task_id: {cell['task_id']}\n"
        "- execution_path: minimal_provider_agent_loop\n"
        f"- provider_id: {cell['provider_id']}\n"
        f"- model_id: {cell['model_id']}\n"
        f"- agent_stop_reason: {state.agent_stop_reason}\n"
        "- final_verifier_status: not_executed_stage3b_minimal_provider_loop\n"
        "- accepted: false\n"
    )


def _cell_identity(cell: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    return {
        "cell_id": cell["cell_id"],
        "task_id": cell["task_id"],
        "provider_id": cell["provider_id"],
        "provider_mode": cell["provider_mode"],
        "model_id": cell["model_id"],
        "scaffold_id": cell["scaffold_id"],
        "budget_policy_id": cell["budget_policy_id"],
        "tool_policy_id": cell["tool_policy_id"],
        "context_policy_id": cell["context_policy_id"],
        "environment_id": cell["environment_id"],
        "source_tree_hash": cell["source_tree_hash"],
        "final_verifier_plan_ref": cell.get("final_verifier_plan_ref"),
        "run_id": run_id,
    }


def _run_config_payload(
    *,
    output_dir: Path,
    allow_local_secret_file: bool,
    provider_id: str,
    model_id: str,
) -> dict[str, Any]:
    return {
        "run_id_prefix": "v5_stage3b",
        "model": {
            "provider": provider_id,
            "model_id": model_id,
            "temperature": 0.0,
            "max_output_tokens": 512,
            "retry_policy": "none",
            "credential_policy": "local_secret_file_redacted" if allow_local_secret_file else "env_only",
            "provider_request_logging": "redact_secrets",
            "provider_specific_options": _provider_specific_options(
                provider_id=provider_id,
                allow_local_secret_file=allow_local_secret_file,
            ),
        },
        "runtime": {
            "scaffold_id": "simple_react",
            "permission_mode": "auto",
            "test_feedback_policy": "disabled",
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 1,
            "max_tool_calls": 0,
            "max_test_runs": 0,
            "task_timeout_sec": 240,
            "seed": 42,
        },
        "workspace": {
            "output_dir": output_dir.as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": 60,
            "network_policy": "deny_agent_run",
        },
        "evaluation": {
            "final_verifier_mode": "strict_patch_replay",
        },
    }


def _accepted_run_config_payload(
    *,
    output_dir: Path,
    provider_id: str,
    model_id: str,
    allow_local_secret_file: bool,
    max_turns: int,
    max_tool_calls: int,
    max_output_tokens: int,
) -> dict[str, Any]:
    return {
        "run_id_prefix": "v5_accepted",
        "model": {
            "provider": provider_id,
            "model_id": model_id,
            "temperature": 0.0,
            "max_output_tokens": max_output_tokens,
            "retry_policy": "none",
            "credential_policy": "local_secret_file_redacted" if allow_local_secret_file else "env_only",
            "provider_request_logging": "redact_secrets",
            "provider_specific_options": _provider_specific_options(
                provider_id=provider_id,
                allow_local_secret_file=allow_local_secret_file,
            ),
        },
        "runtime": {
            "scaffold_id": "patch_focused_react",
            "permission_mode": "auto",
            "test_feedback_policy": "disabled",
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": max_turns,
            "max_tool_calls": max_tool_calls,
            "max_test_runs": 0,
            "task_timeout_sec": 900,
            "seed": 42,
        },
        "workspace": {
            "output_dir": output_dir.as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": 90,
            "network_policy": "deny_agent_run",
        },
        "evaluation": {
            "final_verifier_mode": "strict_patch_replay",
        },
    }


def _task_yaml_payload(*, task: dict[str, Any], adapter_visible: dict[str, Any]) -> dict[str, Any]:
    archive_ref = task.get("source_archive_ref")
    if not isinstance(archive_ref, dict):
        raise ConfigError(f"{task.get('task_id')} 缺少 source_archive_ref。")
    archive_path = Path(str(archive_ref["path"])).resolve()
    test_command = _test_command_for_task(task=task, adapter_visible=adapter_visible)
    return {
        "id": task["task_id"],
        "task_version": f"{task['task_id']}_stage3b_v0",
        "dataset_name": "repo_harness_v5",
        "source_kind": task.get("source_kind"),
        "dataset_split": "v5_stage3b",
        "created_at": "2026-05-05",
        "repo": archive_path.as_posix(),
        "repo_source_spec": {
            "source_type": "local_archive",
            "archive_path": archive_path.as_posix(),
            "archive_sha256": archive_ref["sha256"],
            "expected_root_directory": _expected_root_directory(archive_path),
            "base_commit": task.get("base_commit"),
            "decontamination_status": "manual_checked",
        },
        "base_commit": task.get("base_commit"),
        "source_archive_sha256": archive_ref["sha256"],
        "issue": _issue_statement(adapter_visible),
        "setup_command": None,
        "test_command": test_command,
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 120,
            "agent_timeout_sec": 240,
            "final_verifier_timeout_sec": 120,
        },
        "environment": {
            "execution_image": "local_process",
            "python_version": "3.12",
            "package_manager": "pip",
            "setup_network_policy": "deny",
            "source_archive_sha256": archive_ref["sha256"],
        },
        "expected_files": [],
        "fail_to_pass_tests": [],
        "pass_to_pass_tests": [],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "decontamination": {
            "status": "manual_checked",
            "known_public_solution": None,
            "source_url": task.get("repo_url_or_archive_id"),
            "overlap_check_notes": "V5 Stage 3B uses sanitized adapter-visible task input only.",
        },
        "declared_setup_mutations": [],
        "generated_files": [],
        "tags": ["v5", "stage3b", str(adapter_visible.get("ecosystem", "unknown"))],
        "metadata": {
            "v5_task_definition_ref": _task_ref(task),
            "v5_final_verifier_plan_ref": task.get("final_verifier_plan_ref"),
            "v5_stage3b_generated": True,
        },
    }


def _accepted_task_yaml_payload(*, task: dict[str, Any], adapter_visible: dict[str, Any]) -> dict[str, Any]:
    payload = _task_yaml_payload(task=task, adapter_visible=adapter_visible)
    payload["task_version"] = f"{task['task_id']}_accepted_provider_v0"
    payload["dataset_split"] = "v5_stage3b_accepted_provider"
    payload["issue"] = _accepted_issue_statement(adapter_visible)
    payload["test_command"] = "hidden_final_verifier_not_model_visible"
    payload["metadata"] = {
        **payload.get("metadata", {}),
        "v5_accepted_provider_generated": True,
        "final_only": True,
        "swe_bench_like_final_only": True,
        "hidden_final_verifier_command_model_visible": False,
    }
    return payload


def _issue_statement(adapter_visible: dict[str, Any]) -> str:
    constraints = adapter_visible.get("visible_constraints") or []
    suffix = "\n\nVisible constraints:\n" + "\n".join(f"- {item}" for item in constraints)
    return str(adapter_visible.get("task_statement", "")).strip() + suffix


def _accepted_issue_statement(adapter_visible: dict[str, Any]) -> str:
    return (
        _issue_statement(adapter_visible)
        + "\n\nAccepted-run execution guidance:\n"
        "- This run is only useful if you create a durable source patch in the repository.\n"
        "- Do not spend the whole budget on analysis. After you locate the relevant implementation, call edit_file.\n"
        "- Do not finish with an analysis-only answer. Review the repository diff with git_diff before your final answer.\n"
        "- You cannot see hidden tests or evaluator-only evidence; infer the fix from the public task statement and repository code only."
    )


def _test_command_for_task(*, task: dict[str, Any], adapter_visible: dict[str, Any]) -> str:
    task_id = str(task["task_id"])
    if task_id in V5_STAGE3B_TEST_COMMANDS:
        return V5_STAGE3B_TEST_COMMANDS[task_id]
    command = adapter_visible.get("final_verifier_command")
    if isinstance(command, list) and command[:3] == ["python", "-m", "pytest"]:
        return shlex.join(str(part) for part in command)
    raise ConfigError(f"{task_id} 没有 Stage 3B 可用的 pytest verifier command。")


def _controlled_variables_payload(
    *,
    task: dict[str, Any],
    task_yaml_path: Path,
    provider_id: str,
    scaffold_id: str,
    budget_policy_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_matrix_controlled_variables_v0",
        "task_id": task["task_id"],
        "task_yaml_sha256": sha256_file(task_yaml_path),
        "source_tree_hash": task.get("source_tree_hash"),
        "source_archive_sha256": task.get("source_archive_sha256"),
        "final_verifier_plan_ref": task.get("final_verifier_plan_ref"),
        "tool_policy_id": "stage3b_no_tool_calls",
        "context_policy_id": "stage3b_default_context_compaction",
        "provider_id": provider_id,
        "scaffold_id": scaffold_id,
        "budget_policy_id": budget_policy_id,
        "environment_id": task.get("environment_id"),
        "comparison_validity_scope": "provider_axis_controlled_run_floor",
    }


def _model_by_provider(*, deepseek_model_id: str, openai_model_id: str) -> dict[str, str]:
    return {
        "deepseek": normalize_deepseek_model_id(deepseek_model_id),
        "openai": normalize_openai_model_id(openai_model_id),
    }


def _normalize_model_for_provider(provider_id: str, model_id: str) -> str:
    if provider_id == "deepseek":
        return normalize_deepseek_model_id(model_id)
    if provider_id == "openai":
        return normalize_openai_model_id(model_id)
    raise ConfigError(f"V5 accepted provider run 不支持 provider_id={provider_id!r}。")


def _provider_specific_options_for_cell(
    cell: dict[str, Any],
    *,
    allow_local_secret_file: bool,
) -> dict[str, Any]:
    return _provider_specific_options(
        provider_id=str(cell["provider_id"]),
        allow_local_secret_file=allow_local_secret_file,
    )


def _provider_specific_options(*, provider_id: str, allow_local_secret_file: bool) -> dict[str, Any]:
    options: dict[str, Any] = {"allow_local_secret_file": allow_local_secret_file}
    if provider_id == "deepseek":
        options["thinking"] = {"type": "disabled"}
    return options


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def _should_stop_after_provider_error(result: dict[str, Any]) -> bool:
    if result.get("normalized_provider_status") != "provider_error":
        return False
    error_type = str(result.get("model_error_type") or "").lower()
    message = str(result.get("failure_message_preview") or "").lower()
    stop_markers = (
        "auth_error",
        "rate_limited",
        "quota",
        "insufficient",
        "billing",
        "credit",
        "balance",
    )
    return any(marker in error_type or marker in message for marker in stop_markers)


def _hard_stop_reason(results: list[dict[str, Any]]) -> str | None:
    if not results:
        return None
    last = results[-1]
    if _should_stop_after_provider_error(last):
        error_type = last.get("model_error_type") or "provider_error"
        return f"stopped_after_{error_type}"
    return None


def _provider_comparison_pairs(real_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for result in real_results:
        if result.get("normalized_provider_status") != "primary_attempted":
            continue
        provider_id = str(result.get("provider_id"))
        if provider_id not in {"deepseek", "openai"}:
            continue
        key = _provider_comparison_key(result)
        groups.setdefault(key, {})[provider_id] = result
    pairs: list[dict[str, Any]] = []
    for by_provider in groups.values():
        if {"deepseek", "openai"}.issubset(by_provider):
            deepseek = by_provider["deepseek"]
            openai = by_provider["openai"]
            pairs.append(
                {
                    "task_id": str(deepseek["task_id"]),
                    "providers": ["deepseek", "openai"],
                    "cell_ids": [deepseek["cell_id"], openai["cell_id"]],
                    "model_ids_by_provider": {
                        "deepseek": deepseek.get("model_id"),
                        "openai": openai.get("model_id"),
                    },
                    "controlled_variables": {
                        "source_tree_hash": _controlled_value(deepseek, "source_tree_hash"),
                        "final_verifier_plan_ref": _controlled_value(deepseek, "final_verifier_plan_ref"),
                        "tool_policy_id": _controlled_value(deepseek, "tool_policy_id"),
                        "context_policy_id": _controlled_value(deepseek, "context_policy_id"),
                        "scaffold_id": _controlled_value(deepseek, "scaffold_id"),
                        "budget_policy_id": _controlled_value(deepseek, "budget_policy_id"),
                        "environment_id": _controlled_value(deepseek, "environment_id"),
                    },
                }
            )
    return sorted(pairs, key=lambda item: str(item["task_id"]))


def _comparison_cells_from_pairs(provider_pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for pair in provider_pairs:
        for cell_id in pair["cell_ids"]:
            cells.append({"cell_id": cell_id, "task_id": pair["task_id"]})
    return cells


def _provider_comparison_key(result: dict[str, Any]) -> str:
    key_payload = {
        "task_id": _controlled_value(result, "task_id"),
        "source_tree_hash": _controlled_value(result, "source_tree_hash"),
        "final_verifier_plan_ref": _controlled_value(result, "final_verifier_plan_ref"),
        "tool_policy_id": _controlled_value(result, "tool_policy_id"),
        "context_policy_id": _controlled_value(result, "context_policy_id"),
        "scaffold_id": _controlled_value(result, "scaffold_id"),
        "budget_policy_id": _controlled_value(result, "budget_policy_id"),
        "environment_id": _controlled_value(result, "environment_id"),
    }
    return json.dumps(key_payload, ensure_ascii=False, sort_keys=True)


def _controlled_value(result: dict[str, Any], key: str) -> Any:
    if key in result:
        return result.get(key)
    payload = _controlled_payload(result)
    if key in payload:
        return payload.get(key)
    return None


def _controlled_payload(result: dict[str, Any]) -> dict[str, Any]:
    cached = result.get("_controlled_variables_payload")
    if isinstance(cached, dict):
        return cached
    path = _path_from_ref(result.get("controlled_variables_ref"))
    if path is None or not path.exists():
        result["_controlled_variables_payload"] = {}
        return {}
    try:
        payload = _read_json(path)
    except ConfigError:
        payload = {}
    result["_controlled_variables_payload"] = payload
    return payload


def _blocked_axis_report(
    *,
    axis: str,
    observed_values: list[str],
    required_shape: str,
    blocking_reason: str,
    matrix_ref: dict[str, Any],
    results_ref: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": f"repo_harness_v5_{axis}_comparison_report_v0",
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage3c_comparison_reports",
        "comparison_axis": axis,
        "comparison_validity": "invalid",
        "controlled_variables": [
            "task_id",
            "source_tree_hash",
            "final_verifier_plan_ref",
            "tool_policy_id",
            "context_policy_id",
            "environment_id",
        ],
        "compared_cells": [],
        "observed_values": observed_values,
        "required_shape": required_shape,
        "blocking_reason": blocking_reason,
        "counts_toward_core_comparison_proof": False,
        "counts_toward_resume_ready_acceptance": False,
        "run_matrix_manifest_ref": matrix_ref,
        "matrix_cell_results_ref": results_ref,
    }


def _require_stage3b_inputs(
    *,
    task_set: dict[str, Any],
    provider_gate: dict[str, Any],
    provider_cost: dict[str, Any],
    provider_ids: tuple[str, ...],
) -> None:
    if task_set.get("strict_inventory_gate") != "passed":
        raise ConfigError("Stage 3B run matrix 需要 strict_inventory_gate=passed 的 task set。")
    if not provider_ids:
        raise ConfigError("Stage 3B run matrix 至少需要一个 provider_id。")
    credential_status = provider_gate.get("credential_status_by_provider", {})
    adapter_status = provider_gate.get("adapter_status_by_provider", {})
    for provider_id in provider_ids:
        if provider_id not in V5_STAGE3B_PROVIDER_IDS:
            raise ConfigError(f"Stage 3B run matrix 不支持 provider_id={provider_id!r}。")
        if credential_status.get(provider_id) != "present":
            raise ConfigError(f"Stage 3B run matrix 需要 {provider_id} active credential present。")
        if adapter_status.get(provider_id) != "primary_supported":
            raise ConfigError(f"Stage 3B run matrix 需要 {provider_id} primary_supported。")
    if provider_cost.get("budget_exhausted_before_run") is True:
        raise ConfigError("Stage 3B run matrix 不能在 provider budget 已耗尽时启动。")


def _load_task_definitions(task_set: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for ref in task_set.get("task_refs") or []:
        if not isinstance(ref, dict) or not ref.get("path"):
            continue
        task = _read_json(Path(ref["path"]))
        task["_task_ref"] = ref
        result[str(task["task_id"])] = task
    return result


def _task_ref(task: dict[str, Any]) -> dict[str, Any]:
    ref = task.get("_task_ref")
    if isinstance(ref, dict):
        return ref
    return {
        "schema_version": "repo_harness_v5_evidence_ref_v0",
        "path": "",
        "sha256": "",
        "size_bytes": 0,
        "kind": "v5_task_definition",
        "purpose": "missing task ref",
        "visibility": "audit_only",
        "share_safe": False,
        "producer_command": "unknown",
        "producer_stage": "unknown",
        "inspect_command": "inspect-v5-task-set",
    }


def _expected_root_directory(archive_path: Path) -> str:
    with tarfile.open(archive_path) as archive:
        roots: set[str] = set()
        for member in archive.getmembers()[:200]:
            if not member.name or member.name == ".":
                continue
            roots.add(Path(member.name).parts[0])
            if len(roots) > 1:
                return "."
        if len(roots) == 1:
            return next(iter(roots))
    return "."


def _token_usage(events: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    for event in events:
        data = event.get("data", {})
        for key in totals:
            value = data.get(key)
            if isinstance(value, int):
                totals[key] += value
    return totals


def _raw_provider_redaction_facts(run_dir: Path, artifacts: dict[str, Any]) -> dict[str, Any]:
    raw = [
        item for item in artifacts.get("artifacts", [])
        if "provider_request" in str(item.get("kind")) or "provider_response" in str(item.get("kind"))
    ]
    failures = []
    for item in raw:
        if item.get("redaction_status") != "redacted":
            failures.append(item.get("artifact_id"))
        path = run_dir / item.get("relative_path", "")
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "authorization: bearer" in text or "bearer sk-" in text:
                failures.append(item.get("artifact_id"))
    return {
        "raw_provider_artifact_count": len(raw),
        "raw_provider_redaction_failure_count": len([item for item in failures if item]),
        "all_raw_provider_artifacts_redacted": not failures,
    }


def _artifact_ref_for_input(path: Path, kind: str, inspect_command: str) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"V5 Stage 3B input: {kind}",
        visibility="audit_only",
        producer_command="external",
        producer_stage="v5_stage3b_run_matrix",
        inspect_command=inspect_command,
    )


def _path_from_ref(ref: Any) -> Path | None:
    if not isinstance(ref, dict) or not ref.get("path"):
        return None
    return Path(str(ref["path"]))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"输入文件不存在：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} 不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"{path} 顶层必须是 JSON object。")
    return payload


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"输入文件不存在：{path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigError(f"{path} 顶层必须是 YAML object。")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _refuse_existing(root: Path, names: tuple[str, ...], fail_if_output_exists: bool) -> None:
    if not fail_if_output_exists:
        return
    existing = [root / name for name in names if (root / name).exists()]
    if existing:
        joined = ", ".join(path.as_posix() for path in existing)
        raise ConfigError(f"V5 Stage 3B 输出已存在，不能覆盖旧 evidence：{joined}")


__all__ = [
    "build_comparison_reports",
    "build_run_matrix_manifest",
    "run_accepted_provider_task",
    "run_matrix_cells",
]
