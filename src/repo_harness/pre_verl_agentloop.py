"""Pre-verl AgentLoop formal baseline inspection helpers."""

from __future__ import annotations

import json
import shlex
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.config import RunConfig, load_run_config
from repo_harness.context import ContextBuilder
from repo_harness.errors import ConfigError, TaskValidationError
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.scaffolds import build_scaffold, resolve_allowed_tools, resolve_feedback_policy
from repo_harness.tasks import RunnableTask, TaskAdapter, TaskDefinition
from repo_harness.trajectory import ArtifactRef, RunRecorder, TrajectoryEvent
from repo_harness.verifier.pytest_parser import PytestTextParser
from repo_harness.verifier.schemas import TestCaseResult, VerifierResult
from repo_harness.workspace import DependencyState, ExecutionResult, RunWorkspace
from repo_harness.workspace.protocol import WorkspaceAdapter
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

PRE_VERL_AGENTLOOP_ADAPTER_ID = "swebench_lite_dev_agentloop_v0"
PRE_VERL_AGENTLOOP_MODE = "formal_baseline"
PRE_VERL_AGENTLOOP_BASELINE_SOURCE = "repo_harness_agentloop_run_task"
LEGACY_V3_SWEBENCH_LIKE_ADAPTER_ID = "swebench_like_fixed"
PRE_VERL_FINAL_VERIFIER_ADAPTER_ID = "pre_verl_swebench_lite_dev_final_verifier_v0"
PRE_VERL_FINAL_VERIFIER_BOUNDARY_VERSION = "repo_harness_pre_verl_final_verifier_boundary_v0"
PRE_VERL_AGENTLOOP_BOUNDARY_INDEX_VERSION = "repo_harness_pre_verl_agentloop_boundary_index_v0"

_MODEL_PATCH_STEP = "pre_verl_model_final_patch_apply"
_HIDDEN_PATCH_STEP = "pre_verl_hidden_test_patch_apply"
_F2P_STEP = "pre_verl_fail_to_pass_test_execution"
_P2P_STEP = "pre_verl_pass_to_pass_test_execution"

_REQUIRED_EVALUATOR_ONLY_REFS = (
    "hidden_test_patch_ref",
    "fail_to_pass_selectors_ref",
    "pass_to_pass_selectors_ref",
)
_HIDDEN_MARKERS = (
    "hidden_test.patch",
    "test_patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "gold_patch",
    "official_harness_report",
    "official_resolved",
    "final_verifier_raw_output",
    "reward scalar",
    "reward label",
)


@dataclass(frozen=True)
class PreVerlSwebenchDevRuntimePlan:
    task_id: str
    manifest_path: Path
    hidden_test_patch_path: Path
    fail_to_pass_selectors: list[str]
    pass_to_pass_selectors: list[str]
    hidden_test_patch_ref: dict[str, Any]
    fail_to_pass_selectors_ref: dict[str, Any]
    pass_to_pass_selectors_ref: dict[str, Any]
    hidden_patch_clean_source_self_check_ref: dict[str, Any] | None
    verifier_command: str
    setup_shell: str | None
    setup_timeout_sec: int
    final_verifier_timeout_sec: int
    source_instance_id: str | None
    repo: str | None
    environment_id: str | None


def is_formal_pre_verl_agentloop_metadata(metadata: dict[str, Any]) -> bool:
    """Return true only for the single approved formal pre-verl metadata shape."""

    manifest_path = metadata.get("pre_verl_swebench_dev_manifest_path")
    return (
        metadata.get("pre_verl_adapter") == PRE_VERL_AGENTLOOP_ADAPTER_ID
        and isinstance(manifest_path, str)
        and bool(manifest_path.strip())
        and metadata.get("pre_verl_agentloop_mode") == PRE_VERL_AGENTLOOP_MODE
        and metadata.get("pre_verl_agentloop_baseline_source")
        == PRE_VERL_AGENTLOOP_BASELINE_SOURCE
        and metadata.get("swe_bench_like_final_only") is True
        and metadata.get("final_only") is True
    )


def load_pre_verl_swebench_dev_runtime_plan(
    task: RunnableTask,
) -> PreVerlSwebenchDevRuntimePlan | None:
    metadata = task.metadata or {}
    pre_verl_declared = any(
        key in metadata
        for key in (
            "pre_verl_adapter",
            "pre_verl_swebench_dev_manifest_path",
            "pre_verl_agentloop_mode",
            "pre_verl_agentloop_baseline_source",
        )
    )
    formal_metadata = is_formal_pre_verl_agentloop_metadata(metadata)
    if formal_metadata and metadata.get("v3_adapter") == LEGACY_V3_SWEBENCH_LIKE_ADAPTER_ID:
        raise ConfigError(
            "formal pre-verl AgentLoop baseline cannot use legacy "
            "v3_adapter=swebench_like_fixed."
        )
    if not formal_metadata:
        if pre_verl_declared:
            raise ConfigError(
                "pre-verl AgentLoop metadata is incomplete; formal run-task requires "
                "pre_verl_adapter, pre_verl_swebench_dev_manifest_path, "
                "pre_verl_agentloop_mode, pre_verl_agentloop_baseline_source, "
                "swe_bench_like_final_only=true, and final_only=true."
            )
        return None
    manifest_path = Path(str(metadata["pre_verl_swebench_dev_manifest_path"]))
    if not manifest_path.exists():
        raise ConfigError(f"pre-verl SWE-Bench development manifest 不存在：{manifest_path}")
    hidden_ref = _required_ref(metadata, "hidden_test_patch_ref")
    f2p_ref = _required_ref(metadata, "fail_to_pass_selectors_ref")
    p2p_ref = _required_ref(metadata, "pass_to_pass_selectors_ref")
    hidden_patch_path = _resolve_ref_path(hidden_ref, manifest_path.parent)
    f2p_selectors = _read_selector_ref(f2p_ref, manifest_path.parent)
    p2p_selectors = _read_selector_ref(p2p_ref, manifest_path.parent)
    if not hidden_patch_path.exists():
        raise ConfigError(f"pre-verl hidden test patch 不存在：{hidden_patch_path}")
    if not f2p_selectors:
        raise ConfigError("pre-verl fail-to-pass selector ref 不能为空。")
    return PreVerlSwebenchDevRuntimePlan(
        task_id=task.task_id,
        manifest_path=manifest_path,
        hidden_test_patch_path=hidden_patch_path,
        fail_to_pass_selectors=f2p_selectors,
        pass_to_pass_selectors=p2p_selectors,
        hidden_test_patch_ref=hidden_ref,
        fail_to_pass_selectors_ref=f2p_ref,
        pass_to_pass_selectors_ref=p2p_ref,
        hidden_patch_clean_source_self_check_ref=(
            metadata.get("hidden_patch_clean_source_self_check_ref")
            if isinstance(metadata.get("hidden_patch_clean_source_self_check_ref"), dict)
            else None
        ),
        verifier_command=str(metadata.get("pre_verl_verifier_command") or task.verifier_config.test_command),
        setup_shell=(
            str(metadata.get("pre_verl_setup_shell"))
            if metadata.get("pre_verl_setup_shell") is not None
            else None
        ),
        setup_timeout_sec=task.timeouts.setup_timeout_sec,
        final_verifier_timeout_sec=task.timeouts.final_verifier_timeout_sec,
        source_instance_id=(
            str(metadata.get("source_instance_id"))
            if metadata.get("source_instance_id") is not None
            else None
        ),
        repo=str(metadata.get("repo") or metadata.get("source_repo") or "")
        or None,
        environment_id=(
            str(metadata.get("environment_id"))
            if metadata.get("environment_id") is not None
            else None
        ),
    )


def build_pre_verl_baseline_verifier(plan: PreVerlSwebenchDevRuntimePlan) -> VerifierResult:
    f2p_total = len(plan.fail_to_pass_selectors)
    p2p_total = len(plan.pass_to_pass_selectors)
    return VerifierResult(
        verifier_stage="baseline",
        parser_confidence=1.0,
        command="pre_verl_frozen_baseline_evidence",
        test_cases=[
            *[
                TestCaseResult(test_id=f"fail_to_pass::{selector}", status="failed")
                for selector in plan.fail_to_pass_selectors
            ],
            *[
                TestCaseResult(test_id=f"pass_to_pass::{selector}", status="passed")
                for selector in plan.pass_to_pass_selectors
            ],
        ],
        accepted=False,
        accepted_fallback_reason=None,
        pass_ratio=(p2p_total / max(1, f2p_total + p2p_total)),
        fail_to_pass={"passed": 0, "total": f2p_total},
        pass_to_pass={"passed": p2p_total, "total": p2p_total},
        exit_code=1,
        timeout=False,
        error_type="assertion_failure",
    )


def run_pre_verl_swebench_dev_final_verifier(
    *,
    plan: PreVerlSwebenchDevRuntimePlan,
    source_checkout: str | Path,
    dependency_state: DependencyState,
    final_patch_path: str | Path,
    run_dir: str | Path,
    adapter: WorkspaceAdapter,
    recorder: RunRecorder,
    setup_command: str | None = None,
    agent_stop_reason: str | None = None,
) -> VerifierResult:
    run_root = Path(run_dir)
    verification_workspace = run_root / "workspaces" / "pre_verl_final_verification_workspace"
    result_refs: dict[str, Any] = {}
    command_order: list[str] = []
    accepted = False
    final_status = "not_executed"
    failure_category: str | None = None
    failure_owner: str | None = None
    clean_hash: str | None = None
    after_model_hash: str | None = None
    after_hidden_hash: str | None = None
    selector_payloads: dict[str, dict[str, Any] | None] = {"fail_to_pass": None, "pass_to_pass": None}
    workspace_created = False

    try:
        clean_hash = compute_source_tree_hash(Path(source_checkout))
        if verification_workspace.exists():
            shutil.rmtree(verification_workspace)
        shutil.copytree(
            Path(source_checkout),
            verification_workspace,
            symlinks=True,
            ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__", "*.pyc"),
        )
        workspace_created = True
        creation_result = adapter.run_command(
            verification_workspace,
            ["python", "-c", "pass"],
            timeout_sec=30,
            recorder=recorder,
            command_semantics="pre_verl_verification_workspace_creation",
            artifact_metadata={"redaction_status": "evaluator_only"},
        )
        creation_path = run_root / "pre_verl_verification_workspace_creation_result.json"
        _write_json(creation_path, _execution_result_payload(creation_result))
        result_refs["workspace_creation_result_ref"] = _file_ref(
            creation_path,
            base_dir=run_root,
            artifact_id="pre_verl_verification_workspace_creation_result",
            kind="pre_verl_verification_workspace_creation_result",
            redaction_status="evaluator_only",
        )
        if creation_result.exit_code != 0 or creation_result.timeout:
            failure_category = "verification_workspace_creation_failed"
            failure_owner = "harness_or_environment"
            final_status = "not_executed"
        else:
            if failure_category is None and Path(final_patch_path).stat().st_size == 0:
                empty_patch_path = run_root / "pre_verl_empty_final_patch_result.json"
                failure_category = (
                    "budget_exhausted_empty_patch"
                    if agent_stop_reason
                    in {"max_turns", "max_tool_calls", "task_timeout", "timeout", "context_limit"}
                    else "empty_final_patch"
                )
                failure_owner = (
                    "budget_or_timeout"
                    if failure_category == "budget_exhausted_empty_patch"
                    else "model_no_patch_generated"
                )
                final_status = "not_executed"
                _write_json(
                    empty_patch_path,
                    {
                        "schema_version": "repo_harness_pre_verl_empty_final_patch_result_v0",
                        "status": "failed",
                        "failure_category": failure_category,
                        "failure_owner": failure_owner,
                        "agent_stop_reason": agent_stop_reason,
                        "final_patch_path": str(final_patch_path),
                        "final_patch_size_bytes": 0,
                    },
                )
                result_refs["empty_final_patch_result_ref"] = _file_ref(
                    empty_patch_path,
                    base_dir=run_root,
                    artifact_id="pre_verl_empty_final_patch_result",
                    kind="pre_verl_empty_final_patch_result",
                    redaction_status="evaluator_only",
                )
            if (
                failure_category is None
                and agent_stop_reason in {"task_timeout", "timeout"}
                and Path(final_patch_path).stat().st_size > 0
            ):
                timeout_skip_path = run_root / "pre_verl_final_verifier_task_timeout_skip.json"
                failure_category = "task_timeout_before_final_verifier"
                failure_owner = "budget_or_timeout"
                final_status = "not_executed"
                _write_json(
                    timeout_skip_path,
                    {
                        "schema_version": "repo_harness_pre_verl_final_verifier_task_timeout_skip_v0",
                        "status": "skipped",
                        "failure_category": failure_category,
                        "failure_owner": failure_owner,
                        "agent_stop_reason": agent_stop_reason,
                        "final_patch_path": str(final_patch_path),
                        "final_patch_size_bytes": Path(final_patch_path).stat().st_size,
                    },
                )
                result_refs["final_verifier_task_timeout_skip_ref"] = _file_ref(
                    timeout_skip_path,
                    base_dir=run_root,
                    artifact_id="pre_verl_final_verifier_task_timeout_skip",
                    kind="pre_verl_final_verifier_task_timeout_skip",
                    redaction_status="evaluator_only",
                )
            if failure_category is None:
                try:
                    adapter.restore_dependency_state(
                        verification_workspace,
                        dependency_state,
                        setup_command,
                        setup_timeout_sec=plan.setup_timeout_sec,
                        recorder=recorder,
                    )
                except Exception as exc:  # noqa: BLE001 - boundary must be written for terminal failures.
                    setup_path = run_root / "pre_verl_dependency_restore_error.json"
                    _write_json(setup_path, {"status": "failed", "message": str(exc)})
                    result_refs["dependency_restore_result_ref"] = _file_ref(
                        setup_path,
                        base_dir=run_root,
                        artifact_id="pre_verl_dependency_restore_error",
                        kind="pre_verl_dependency_restore_result",
                        redaction_status="evaluator_only",
                    )
                    failure_category = "environment_setup_failed"
                    failure_owner = "harness_or_environment"
                    final_status = "not_executed"
            if failure_category is None:
                model_apply = adapter.apply_patch(
                    verification_workspace,
                    final_patch_path,
                    recorder=recorder,
                    command_semantics=_MODEL_PATCH_STEP,
                )
                command_order.append(_MODEL_PATCH_STEP)
                _append_boundary_step_event(
                    recorder=recorder,
                    plan=plan,
                    command_semantics=_MODEL_PATCH_STEP,
                    result=model_apply,
                )
                model_apply_path = run_root / "pre_verl_model_final_patch_apply_result.json"
                _write_json(model_apply_path, _execution_result_payload(model_apply))
                result_refs["model_final_patch_apply_result_ref"] = _file_ref(
                    model_apply_path,
                    base_dir=run_root,
                    artifact_id="pre_verl_model_final_patch_apply_result",
                    kind="pre_verl_model_final_patch_apply_result",
                    redaction_status="evaluator_only",
                )
                if model_apply.exit_code != 0 or model_apply.timeout:
                    failure_category = "model_patch_apply_failed"
                    failure_owner = "model_patch_format_or_path"
                    final_status = "not_executed"
                else:
                    after_model_hash = compute_source_tree_hash(verification_workspace)
                    staged_hidden_patch_path = _stage_hidden_test_patch(plan, run_root)
                    result_refs["staged_hidden_test_patch_ref"] = _file_ref(
                        staged_hidden_patch_path,
                        base_dir=run_root,
                        artifact_id="pre_verl_staged_hidden_test_patch",
                        kind="hidden_test_patch",
                        redaction_status="evaluator_only",
                    )
                    hidden_apply = adapter.apply_patch(
                        verification_workspace,
                        staged_hidden_patch_path,
                        recorder=recorder,
                        command_semantics=_HIDDEN_PATCH_STEP,
                    )
                    command_order.append(_HIDDEN_PATCH_STEP)
                    _append_boundary_step_event(
                        recorder=recorder,
                        plan=plan,
                        command_semantics=_HIDDEN_PATCH_STEP,
                        result=hidden_apply,
                    )
                    hidden_apply_path = run_root / "pre_verl_hidden_test_patch_apply_result.json"
                    _write_json(hidden_apply_path, _execution_result_payload(hidden_apply))
                    result_refs["hidden_test_patch_apply_result_ref"] = _file_ref(
                        hidden_apply_path,
                        base_dir=run_root,
                        artifact_id="pre_verl_hidden_test_patch_apply_result",
                        kind="pre_verl_hidden_test_patch_apply_result",
                        redaction_status="evaluator_only",
                    )
                    if hidden_apply.exit_code != 0 or hidden_apply.timeout:
                        failure_category = _hidden_patch_failure_category(plan)
                        failure_owner = (
                            "model_patch_quality"
                            if failure_category == "hidden_test_patch_conflict_after_candidate_patch"
                            else "harness_or_environment"
                        )
                        final_status = "not_executed"
                    else:
                        after_hidden_hash = compute_source_tree_hash(verification_workspace)
                        f2p = _run_selector_suite(
                            plan=plan,
                            verification_workspace=verification_workspace,
                            adapter=adapter,
                            recorder=recorder,
                            run_root=run_root,
                            suite="fail_to_pass",
                            selectors=plan.fail_to_pass_selectors,
                            command_semantics=_F2P_STEP,
                        )
                        command_order.append(_F2P_STEP)
                        selector_payloads["fail_to_pass"] = f2p
                        result_refs["fail_to_pass_result_ref"] = _file_ref(
                            run_root / "pre_verl_fail_to_pass_result.json",
                            base_dir=run_root,
                            artifact_id="pre_verl_fail_to_pass_result",
                            kind="pre_verl_selector_result",
                            redaction_status="evaluator_only",
                        )
                        p2p = _run_selector_suite(
                            plan=plan,
                            verification_workspace=verification_workspace,
                            adapter=adapter,
                            recorder=recorder,
                            run_root=run_root,
                            suite="pass_to_pass",
                            selectors=plan.pass_to_pass_selectors,
                            command_semantics=_P2P_STEP,
                        )
                        command_order.append(_P2P_STEP)
                        selector_payloads["pass_to_pass"] = p2p
                        result_refs["pass_to_pass_result_ref"] = _file_ref(
                            run_root / "pre_verl_pass_to_pass_result.json",
                            base_dir=run_root,
                            artifact_id="pre_verl_pass_to_pass_result",
                            kind="pre_verl_selector_result",
                            redaction_status="evaluator_only",
                        )
                        timeout = bool(f2p.get("timeout") or p2p.get("timeout"))
                        selector_input_error = _selector_input_error(f2p) or _selector_input_error(p2p)
                        accepted = bool(
                            f2p.get("exit_code") == 0
                            and p2p.get("exit_code") == 0
                            and not timeout
                            and not selector_input_error
                        )
                        if accepted:
                            final_status = "accepted"
                            failure_category = None
                            failure_owner = None
                        elif timeout:
                            final_status = "timeout"
                            failure_category = "verifier_timeout_budget"
                            failure_owner = "budget_or_timeout"
                        elif selector_input_error:
                            final_status = "not_executed"
                            failure_category = "selector_input_invalid"
                            failure_owner = "harness_or_verifier_input"
                        else:
                            final_status = "rejected"
                            failure_category = "model_patch_rejected_by_final_verifier"
                            failure_owner = "model_wrong_fix"
    except Exception as exc:  # noqa: BLE001 - final verifier boundary is the authority record.
        failure_category = "verification_workspace_error"
        failure_owner = "harness_or_environment"
        final_status = "not_executed"
        error_path = run_root / "pre_verl_final_verifier_unhandled_error.json"
        _write_json(error_path, {"status": "failed", "message": str(exc)})
        result_refs["final_verifier_error_ref"] = _file_ref(
            error_path,
            base_dir=run_root,
            artifact_id="pre_verl_final_verifier_unhandled_error",
            kind="pre_verl_final_verifier_error",
            redaction_status="evaluator_only",
        )

    boundary = _pre_verl_boundary_payload(
        plan=plan,
        run_root=run_root,
        verification_workspace=verification_workspace,
        source_checkout=Path(source_checkout),
        final_patch_path=Path(final_patch_path),
        clean_hash=clean_hash,
        after_model_hash=after_model_hash,
        after_hidden_hash=after_hidden_hash,
        command_order=command_order,
        result_refs=result_refs,
        selector_payloads=selector_payloads,
        accepted=accepted,
        final_status=final_status,
        failure_category=failure_category,
        failure_owner=failure_owner,
        workspace_created=workspace_created,
    )
    boundary_path = run_root / "final_verifier_boundary.json"
    _write_json(boundary_path, boundary)
    final_result_path = run_root / "pre_verl_final_verifier_result.json"
    final_result_payload = _pre_verl_final_result_payload(boundary, selector_payloads)
    _write_json(final_result_path, final_result_payload)
    return _verifier_result_from_pre_verl_payload(final_result_payload)


def inspect_pre_verl_agentloop_task_definitions(
    manifest: str | Path,
    *,
    assert_run_task_compatible: bool = False,
    assert_evaluator_only_hidden_inputs: bool = False,
    assert_no_hidden_material_in_model_visible_fields: bool = False,
) -> str:
    manifest_path = Path(manifest)
    payload = _read_structured(manifest_path)
    task_paths = _collect_paths(payload, manifest_path, ("task_definition_refs", "task_definitions", "tasks"))
    failures: list[str] = []
    if not task_paths:
        failures.append("task definition manifest does not reference any task definitions")
    adapter = TaskAdapter()
    for task_path in task_paths:
        definition = _load_task_definition(task_path, failures)
        if definition is None:
            continue
        if assert_run_task_compatible:
            try:
                adapter.load(task_path)
            except TaskValidationError as exc:
                failures.append(f"{task_path}: not run-task compatible: {exc}")
        _inspect_formal_metadata(definition, failures, task_path)
        if assert_evaluator_only_hidden_inputs:
            _inspect_evaluator_only_refs(definition, failures, task_path)
        if assert_no_hidden_material_in_model_visible_fields:
            _inspect_model_visible_fields(definition, failures, task_path)
    return _inspect_result(
        "Inspect pre-verl AgentLoop task definitions",
        manifest_path,
        failures,
        assert_requested=(
            assert_run_task_compatible
            or assert_evaluator_only_hidden_inputs
            or assert_no_hidden_material_in_model_visible_fields
        ),
    )


def inspect_pre_verl_agentloop_run_config(
    manifest: str | Path,
    *,
    assert_final_only_test_feedback_disabled: bool = False,
    assert_resolved_tools_derived: bool = False,
    assert_no_hidden_feedback_visible: bool = False,
) -> str:
    manifest_path = Path(manifest)
    payload = _read_structured(manifest_path)
    entries = _collect_run_config_entries(payload, manifest_path)
    failures: list[str] = []
    if not entries:
        failures.append("run config manifest does not reference any task/config pairs")
    for entry in entries:
        task_path = entry["task_path"]
        config_path = entry["config_path"]
        definition = _load_task_definition(task_path, failures)
        if definition is None:
            continue
        _inspect_formal_metadata(definition, failures, task_path)
        try:
            run_config = load_run_config(config_path)
        except ConfigError as exc:
            failures.append(f"{config_path}: invalid run config: {exc}")
            continue
        if assert_final_only_test_feedback_disabled:
            if run_config.runtime.test_feedback_policy != "disabled":
                failures.append(f"{config_path}: final-only task must set test_feedback_policy=disabled")
            if run_config.runtime.max_test_runs != 0:
                failures.append(f"{config_path}: final-only task must set max_test_runs=0")
        _inspect_deepseek_formal_provider_config(
            definition=definition,
            run_config=run_config,
            config_path=config_path,
            failures=failures,
        )
        _inspect_resolved_policy_and_context(
            definition=definition,
            run_config=run_config,
            config_path=config_path,
            expected_resolved_tools=entry.get("resolved_tools"),
            failures=failures,
            assert_resolved_tools_derived=assert_resolved_tools_derived,
            assert_no_hidden_feedback_visible=assert_no_hidden_feedback_visible,
        )
    return _inspect_result(
        "Inspect pre-verl AgentLoop run config",
        manifest_path,
        failures,
        assert_requested=(
            assert_final_only_test_feedback_disabled
            or assert_resolved_tools_derived
            or assert_no_hidden_feedback_visible
        ),
    )


def inspect_pre_verl_agentloop_boundary_index(
    index: str | Path,
    *,
    assert_all_formal_runs_bound: bool = False,
    assert_command_order: bool = False,
    assert_clean_source_origin: bool = False,
    assert_run_task_lineage: bool = False,
    assert_no_legacy_adapter: bool = False,
) -> str:
    index_path = Path(index)
    payload = _read_structured(index_path)
    failures: list[str] = []
    if not isinstance(payload, dict):
        failures.append("boundary index 顶层必须是 JSON/YAML object")
        entries: list[Any] = []
    else:
        if payload.get("schema_version") != PRE_VERL_AGENTLOOP_BOUNDARY_INDEX_VERSION:
            failures.append("boundary index schema_version 不匹配")
        entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
        if not entries:
            failures.append("boundary index entries 不能为空")
    for index_num, entry in enumerate(entries):
        label = f"entries[{index_num}]"
        if not isinstance(entry, dict):
            failures.append(f"{label}: entry 必须是 object")
            continue
        run_dir = _entry_run_dir(entry, index_path)
        boundary_path = _boundary_path_from_entry(entry, run_dir, index_path)
        if assert_all_formal_runs_bound:
            _inspect_formal_run_files(run_dir, boundary_path, failures, label)
        boundary = _read_optional_json(boundary_path, failures, f"{label}.boundary")
        if not isinstance(boundary, dict):
            continue
        if assert_no_legacy_adapter:
            _inspect_no_legacy_boundary(entry, boundary, failures, label)
        if assert_clean_source_origin:
            _inspect_clean_source_boundary(boundary, failures, label)
        if assert_command_order:
            _inspect_boundary_command_order(boundary, failures, label)
        if assert_run_task_lineage:
            _inspect_run_task_lineage(run_dir, boundary, entry, index_path, failures, label)
    return _inspect_result(
        "Inspect pre-verl AgentLoop final verifier boundary index",
        index_path,
        failures,
        assert_requested=(
            assert_all_formal_runs_bound
            or assert_command_order
            or assert_clean_source_origin
            or assert_run_task_lineage
            or assert_no_legacy_adapter
        ),
    )


def _required_ref(metadata: dict[str, Any], key: str) -> dict[str, Any]:
    ref = metadata.get(key)
    if not isinstance(ref, dict):
        raise ConfigError(f"formal pre-verl metadata.{key} 必须是 evidence ref。")
    return ref


def _resolve_ref_path(ref: dict[str, Any], base: Path) -> Path:
    value = ref.get("path") or ref.get("relative_path")
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("pre-verl evidence ref 缺少 path 或 relative_path。")
    raw = Path(value)
    if raw.is_absolute():
        return raw
    for candidate_base in (base, Path.cwd()):
        candidate = candidate_base / raw
        if candidate.exists():
            return candidate
    return base / raw


def _read_selector_ref(ref: dict[str, Any], base: Path) -> list[str]:
    path = _resolve_ref_path(ref, base)
    payload = _read_structured(path)
    if isinstance(payload, list):
        selectors = [str(item) for item in payload if str(item).strip()]
        _validate_pytest_selector_shapes(selectors, path)
        return selectors
    if isinstance(payload, dict):
        for key in ("selectors", "expanded_selectors", "FAIL_TO_PASS", "PASS_TO_PASS"):
            value = payload.get(key)
            if isinstance(value, list):
                selectors = [str(item) for item in value if str(item).strip()]
                _validate_pytest_selector_shapes(selectors, path)
                return selectors
    raise ConfigError(f"selector ref 必须绑定 selector list：{path}")


def _validate_pytest_selector_shapes(selectors: list[str], path: Path) -> None:
    invalid = [selector for selector in selectors if not _pytest_selector_shape_is_collectable(selector)]
    if invalid:
        preview = ", ".join(invalid[:5])
        raise ConfigError(f"selector ref 包含不可 collect 的 pytest selector：{path}: {preview}")


def _pytest_selector_shape_is_collectable(selector: str) -> bool:
    if not selector.strip() or "::" not in selector:
        return False
    suffix = selector.rsplit("::", 1)[-1]
    return suffix.count("[") == suffix.count("]")


def _stage_hidden_test_patch(plan: PreVerlSwebenchDevRuntimePlan, run_root: Path) -> Path:
    staged_dir = run_root / "evaluator_only_inputs"
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged_path = staged_dir / f"{plan.task_id}_hidden_test.patch"
    shutil.copyfile(plan.hidden_test_patch_path, staged_path)
    return staged_path


def _run_selector_suite(
    *,
    plan: PreVerlSwebenchDevRuntimePlan,
    verification_workspace: Path,
    adapter: WorkspaceAdapter,
    recorder: RunRecorder,
    run_root: Path,
    suite: str,
    selectors: list[str],
    command_semantics: str,
) -> dict[str, Any]:
    if not selectors:
        payload = _selector_result_payload(
            plan=plan,
            suite=suite,
            selectors=[],
            command=[],
            result=None,
            stdout="",
            stderr="",
        )
        _write_json(run_root / f"pre_verl_{suite}_result.json", payload)
        return payload
    command = _selector_command(plan.verifier_command, selectors)
    result = adapter.run_command(
        verification_workspace,
        command,
        timeout_sec=plan.final_verifier_timeout_sec,
        recorder=recorder,
        command_semantics=command_semantics,
        allow_shell=isinstance(command, str),
        artifact_metadata={"redaction_status": "evaluator_only"},
    )
    _append_boundary_step_event(
        recorder=recorder,
        plan=plan,
        command_semantics=command_semantics,
        result=result,
    )
    stdout, stderr = _read_execution_output(run_root=run_root, result=result)
    payload = _selector_result_payload(
        plan=plan,
        suite=suite,
        selectors=selectors,
        command=command,
        result=result,
        stdout=stdout,
        stderr=stderr,
    )
    _write_json(run_root / f"pre_verl_{suite}_result.json", payload)
    return payload


def _selector_command(base_command: str, selectors: list[str]) -> list[str] | str:
    if _requires_shell_selector_command(base_command):
        quoted = " ".join(shlex.quote(item) for item in selectors)
        return f"{base_command} {quoted}".strip()
    try:
        parts = shlex.split(base_command)
    except ValueError:
        quoted = " ".join(shlex.quote(item) for item in selectors)
        return f"{base_command} {quoted}".strip()
    if not parts:
        parts = ["python", "-m", "pytest", "-q"]
    return [*parts, *selectors]


def _requires_shell_selector_command(command: str) -> bool:
    stripped = command.strip()
    return any(marker in stripped for marker in ("&&", "||", ";", "|")) or stripped.startswith((". ", "source "))


def _selector_result_payload(
    *,
    plan: PreVerlSwebenchDevRuntimePlan,
    suite: str,
    selectors: list[str],
    command: list[str] | str,
    result: ExecutionResult | None,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    parser = PytestTextParser()
    exit_code = result.exit_code if result is not None else 0
    timeout = bool(result.timeout) if result is not None else False
    status = "passed" if exit_code == 0 and not timeout else ("timeout" if timeout else "failed")
    test_cases = [{"test_id": selector, "status": status} for selector in selectors]
    return {
        "schema_version": "repo_harness_pre_verl_selector_result_v0",
        "task_id": plan.task_id,
        "suite": suite,
        "command": command,
        "timeout_sec": plan.final_verifier_timeout_sec,
        "selectors": selectors,
        "selector_input_validated": all(
            _pytest_selector_shape_is_collectable(selector) for selector in selectors
        ),
        "selector_input_invalid": False,
        "exit_code": exit_code,
        "timeout": timeout,
        "parser_id": parser.parser_id,
        "parser_version": parser.parser_version,
        "parser_confidence": parser.parser_confidence(stdout, stderr, exit_code),
        "error_type": parser.error_type(stdout, stderr, exit_code, timeout),
        "test_cases": test_cases,
        "passed_count": sum(1 for case in test_cases if case["status"] == "passed"),
        "total_count": len(test_cases),
        "output_artifact_ref": (
            result.output_artifact_ref.model_dump(mode="json")
            if result is not None and result.output_artifact_ref is not None
            else None
        ),
        "container_execution_facts_ref": (
            result.container_execution_facts_ref if result is not None else None
        ),
        "execution_backend": str(result.execution_backend) if result is not None else "not_executed",
    }


def _selector_input_error(payload: dict[str, Any]) -> bool:
    return bool(payload.get("selector_input_invalid"))


def _execution_result_payload(result: ExecutionResult) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_pre_verl_execution_result_v0",
        "status": _status_from_execution(result),
        "exit_code": result.exit_code,
        "timeout": result.timeout,
        "stdout_preview": result.stdout_preview,
        "stderr_preview": result.stderr_preview,
        "output_artifact_ref": (
            result.output_artifact_ref.model_dump(mode="json")
            if result.output_artifact_ref is not None
            else None
        ),
        "container_execution_facts_ref": result.container_execution_facts_ref,
        "execution_backend": str(result.execution_backend),
        "command_semantics": result.command_semantics,
    }


def _status_from_execution(result: ExecutionResult) -> str:
    if result.timeout:
        return "timeout"
    return "passed" if result.exit_code == 0 else "failed"


def _append_boundary_step_event(
    *,
    recorder: RunRecorder,
    plan: PreVerlSwebenchDevRuntimePlan,
    command_semantics: str,
    result: ExecutionResult,
) -> None:
    recorder.append_event(
        TrajectoryEvent(
            event_id=recorder.next_event_id("pre_verl_final_verifier"),
            timestamp=_timestamp(),
            run_id=recorder.run_id,
            task_id=plan.task_id,
            event_type="pre_verl_final_verifier_step",
            artifact_refs=[result.output_artifact_ref] if result.output_artifact_ref else [],
            data={
                "verifier_adapter_id": PRE_VERL_FINAL_VERIFIER_ADAPTER_ID,
                "command_semantics": command_semantics,
                "exit_code": result.exit_code,
                "timeout": result.timeout,
            },
        )
    )


def _read_execution_output(*, run_root: Path, result: ExecutionResult) -> tuple[str, str]:
    if result.output_artifact_ref is None:
        return result.stdout_preview, result.stderr_preview
    output_path = run_root / result.output_artifact_ref.relative_path
    if not output_path.exists():
        return result.stdout_preview, result.stderr_preview
    text = output_path.read_text(encoding="utf-8")
    stdout_marker = "\n\n[stdout]\n"
    stderr_marker = "\n\n[stderr]\n"
    if stdout_marker not in text or stderr_marker not in text:
        return result.stdout_preview, result.stderr_preview
    stdout_part = text.split(stdout_marker, 1)[1]
    stdout, stderr = stdout_part.split(stderr_marker, 1)
    return stdout, stderr


def _pre_verl_boundary_payload(
    *,
    plan: PreVerlSwebenchDevRuntimePlan,
    run_root: Path,
    verification_workspace: Path,
    source_checkout: Path,
    final_patch_path: Path,
    clean_hash: str | None,
    after_model_hash: str | None,
    after_hidden_hash: str | None,
    command_order: list[str],
    result_refs: dict[str, Any],
    selector_payloads: dict[str, dict[str, Any] | None],
    accepted: bool,
    final_status: str,
    failure_category: str | None,
    failure_owner: str | None,
    workspace_created: bool,
) -> dict[str, Any]:
    boundary: dict[str, Any] = {
        "schema_version": PRE_VERL_FINAL_VERIFIER_BOUNDARY_VERSION,
        "task_id": plan.task_id,
        "source_instance_id": plan.source_instance_id,
        "repo": plan.repo,
        "environment_id": plan.environment_id,
        "verifier_adapter_id": PRE_VERL_FINAL_VERIFIER_ADAPTER_ID,
        "baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
        "run_task_entrypoint": "repo-harness run-task",
        "setup_timeout_sec": plan.setup_timeout_sec,
        "final_verifier_timeout_sec": plan.final_verifier_timeout_sec,
        "verification_workspace_source": "clean_frozen_source",
        "workspace_created": workspace_created,
        "workspace_creation_input_ref": _file_ref(
            source_checkout,
            base_dir=run_root,
            artifact_id="pre_verl_clean_source_checkout",
            kind="source_directory",
            redaction_status="evaluator_only",
        ),
        "verification_workspace_ref": (
            _file_ref(
                verification_workspace,
                base_dir=run_root,
                artifact_id="pre_verl_final_verification_workspace",
                kind="source_directory",
                redaction_status="evaluator_only",
            )
            if verification_workspace.exists()
            else None
        ),
        "clean_source_tree_sha256": clean_hash,
        "after_model_patch_tree_sha256": after_model_hash,
        "after_hidden_test_patch_tree_sha256": after_hidden_hash,
        "patch_application_order": [
            "model_final_patch",
            "evaluator_only_hidden_test_patch",
        ],
        "observed_command_order": command_order,
        "model_final_patch_ref": _file_ref(
            final_patch_path,
            base_dir=run_root,
            artifact_id="pre_verl_model_final_patch",
            kind="final_patch",
            redaction_status="evaluator_only",
        ),
        "hidden_test_patch_ref": plan.hidden_test_patch_ref,
        "fail_to_pass_selectors_ref": plan.fail_to_pass_selectors_ref,
        "pass_to_pass_selectors_ref": plan.pass_to_pass_selectors_ref,
        "hidden_patch_clean_source_self_check_ref": plan.hidden_patch_clean_source_self_check_ref,
        "accepted": accepted,
        "final_verifier_status": final_status,
        "final_verifier_ran": bool(selector_payloads.get("fail_to_pass")),
        "accepted_authority": "strict_final_verifier_only",
        "reward_authority": "strict_final_verifier",
        "failure_category": failure_category,
        "failure_owner": failure_owner,
        "legacy_v3_adapter_used": False,
        "old_pilot_used": False,
    }
    boundary.update(result_refs)
    return boundary


def _pre_verl_final_result_payload(
    boundary: dict[str, Any],
    selector_payloads: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    f2p = selector_payloads.get("fail_to_pass") or _skipped_selector_payload(boundary, "fail_to_pass")
    p2p = selector_payloads.get("pass_to_pass") or _skipped_selector_payload(boundary, "pass_to_pass")
    total = max(1, int(f2p.get("total_count", 0)) + int(p2p.get("total_count", 0)))
    passed = int(f2p.get("passed_count", 0)) + int(p2p.get("passed_count", 0))
    return {
        "schema_version": "repo_harness_pre_verl_final_verifier_result_v0",
        "task_id": boundary["task_id"],
        "verifier_adapter_id": PRE_VERL_FINAL_VERIFIER_ADAPTER_ID,
        "accepted": bool(boundary.get("accepted")),
        "final_verifier_status": boundary.get("final_verifier_status"),
        "fail_to_pass_result": f2p,
        "pass_to_pass_result": p2p,
        "fail_to_pass": {
            "passed": int(f2p.get("passed_count", 0)),
            "total": int(f2p.get("total_count", 0)),
        },
        "pass_to_pass": {
            "passed": int(p2p.get("passed_count", 0)),
            "total": int(p2p.get("total_count", 0)),
        },
        "pass_ratio": passed / total,
        "parser_confidence": min(
            float(f2p.get("parser_confidence", 0.0)),
            float(p2p.get("parser_confidence", 1.0)),
        ),
        "error_type": boundary.get("failure_category"),
    }


def _skipped_selector_payload(boundary: dict[str, Any], suite: str) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_pre_verl_selector_result_v0",
        "task_id": boundary.get("task_id"),
        "suite": suite,
        "status": "skipped",
        "structured_skip_reason": boundary.get("failure_category") or "not_executed",
        "selectors": [],
        "exit_code": None,
        "timeout": False,
        "parser_confidence": 0.0,
        "error_type": boundary.get("failure_category") or "not_executed",
        "test_cases": [],
        "passed_count": 0,
        "total_count": 0,
    }


def _verifier_result_from_pre_verl_payload(payload: dict[str, Any]) -> VerifierResult:
    f2p = payload.get("fail_to_pass_result", {})
    p2p = payload.get("pass_to_pass_result", {})
    test_cases = []
    for suite_payload in (f2p, p2p):
        for case in suite_payload.get("test_cases", []) or []:
            test_cases.append(
                TestCaseResult(
                    test_id=str(case.get("test_id", "unknown")),
                    status=str(case.get("status", "unknown")),  # type: ignore[arg-type]
                )
            )
    total = max(1, len(test_cases))
    passed = sum(1 for case in test_cases if case.status == "passed")
    timeout = bool(f2p.get("timeout") or p2p.get("timeout"))
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=float(payload.get("parser_confidence", 0.0)),
        command="pre_verl_swebench_lite_dev_fail_to_pass_and_pass_to_pass",
        test_cases=test_cases,
        accepted=bool(payload.get("accepted")),
        pass_ratio=passed / total,
        fail_to_pass=payload.get("fail_to_pass", {"passed": 0, "total": 0}),
        pass_to_pass=payload.get("pass_to_pass", {"passed": 0, "total": 0}),
        exit_code=0 if payload.get("accepted") else 1,
        timeout=timeout,
        error_type=payload.get("error_type"),
    )


def _hidden_patch_failure_category(plan: PreVerlSwebenchDevRuntimePlan) -> str:
    ref = plan.hidden_patch_clean_source_self_check_ref
    if isinstance(ref, dict):
        status = ref.get("status") or ref.get("self_check_status")
        if status == "passed":
            return "hidden_test_patch_conflict_after_candidate_patch"
    return "hidden_test_patch_apply_failed_on_clean_source"


def _file_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
    redaction_status: str = "not_required",
) -> dict[str, Any]:
    target = path if path.is_absolute() else base_dir / path
    if target.is_dir():
        digest = compute_source_tree_hash(target)
        size_bytes = 0
    else:
        digest = compute_file_sha256(target)
        size_bytes = target.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(target, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status=redaction_status,
        retention_policy="keep",
    ).model_dump(mode="json")


def _relative_path(path: Path, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _entry_run_dir(entry: dict[str, Any], index_path: Path) -> Path:
    value = entry.get("run_task_run_dir") or entry.get("run_dir")
    if isinstance(value, dict):
        value = value.get("path") or value.get("relative_path")
    if not isinstance(value, str) or not value.strip():
        return index_path.parent / "<missing-run-dir>"
    path = Path(value)
    return path if path.is_absolute() else index_path.parent / path


def _boundary_path_from_entry(entry: dict[str, Any], run_dir: Path, index_path: Path) -> Path:
    ref = entry.get("final_verifier_boundary_ref") or entry.get("boundary_ref")
    if isinstance(ref, dict):
        value = ref.get("path") or ref.get("relative_path")
        if isinstance(value, str) and value.strip():
            path = Path(value)
            return path if path.is_absolute() else index_path.parent / path
    return run_dir / "final_verifier_boundary.json"


def _inspect_formal_run_files(
    run_dir: Path,
    boundary_path: Path,
    failures: list[str],
    label: str,
) -> None:
    for required in ("run_metadata.json", "metrics.json", "events.jsonl", "transcript.jsonl"):
        if not (run_dir / required).exists():
            failures.append(f"{label}: run_task_run_dir 缺少 {required}")
    for required in ("final.patch", "final.diff", "artifacts"):
        if not (run_dir / required).exists():
            failures.append(f"{label}: run_task_run_dir 缺少 {required}")
    if not boundary_path.exists():
        failures.append(f"{label}: 缺少 final_verifier_boundary.json")


def _read_optional_json(path: Path, failures: list[str], label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        failures.append(f"{label}: 无法读取 {path}: {exc}")
    except json.JSONDecodeError as exc:
        failures.append(f"{label}: JSON 解析失败 {path}: {exc}")
    return None


def _inspect_no_legacy_boundary(
    entry: dict[str, Any],
    boundary: dict[str, Any],
    failures: list[str],
    label: str,
) -> None:
    if entry.get("v3_adapter") == LEGACY_V3_SWEBENCH_LIKE_ADAPTER_ID:
        failures.append(f"{label}: formal run 不能使用 legacy v3_adapter=swebench_like_fixed")
    if boundary.get("legacy_v3_adapter_used") is True:
        failures.append(f"{label}: boundary 标记 legacy_v3_adapter_used=true")
    if boundary.get("old_pilot_used") is True:
        failures.append(f"{label}: boundary 标记 old_pilot_used=true")
    if boundary.get("verifier_adapter_id") != PRE_VERL_FINAL_VERIFIER_ADAPTER_ID:
        failures.append(f"{label}: verifier_adapter_id 必须是 {PRE_VERL_FINAL_VERIFIER_ADAPTER_ID}")
    if entry.get("scaffold_id") == "single_shot_patch_no_tools":
        failures.append(f"{label}: forbidden scaffold single_shot_patch_no_tools 不能进入正式结果")
    if boundary.get("schema_version") != PRE_VERL_FINAL_VERIFIER_BOUNDARY_VERSION:
        failures.append(f"{label}: boundary schema_version 不匹配")


def _inspect_clean_source_boundary(
    boundary: dict[str, Any],
    failures: list[str],
    label: str,
) -> None:
    if boundary.get("verification_workspace_source") != "clean_frozen_source":
        failures.append(f"{label}: verification_workspace_source 必须是 clean_frozen_source")
    if boundary.get("baseline_workspace_ref") is not None:
        failures.append(f"{label}: formal pre-verl boundary 不能绑定 baseline_workspace_ref")
    if not boundary.get("workspace_creation_input_ref"):
        failures.append(f"{label}: 缺少 workspace_creation_input_ref")
    if not boundary.get("clean_source_tree_sha256"):
        failures.append(f"{label}: 缺少 clean_source_tree_sha256")


def _inspect_boundary_command_order(
    boundary: dict[str, Any],
    failures: list[str],
    label: str,
) -> None:
    timeout_sec = boundary.get("final_verifier_timeout_sec")
    if not isinstance(timeout_sec, int) or timeout_sec <= 0:
        failures.append(f"{label}: final_verifier_timeout_sec 必须显式绑定为正整数")
    if boundary.get("patch_application_order") != [
        "model_final_patch",
        "evaluator_only_hidden_test_patch",
    ]:
        failures.append(f"{label}: patch_application_order 不符合正式顺序")
    observed = boundary.get("observed_command_order")
    if not isinstance(observed, list):
        failures.append(f"{label}: 缺少 observed_command_order")
        return
    empty_patch_failure = boundary.get("failure_category") in {
        "empty_final_patch",
        "budget_exhausted_empty_patch",
    }
    pre_patch_terminal_failure = boundary.get("failure_category") in {
        "empty_final_patch",
        "budget_exhausted_empty_patch",
        "task_timeout_before_final_verifier",
        "verification_workspace_creation_failed",
        "environment_setup_failed",
    }
    if _MODEL_PATCH_STEP not in observed and not pre_patch_terminal_failure:
        failures.append(f"{label}: observed_command_order 缺少 {_MODEL_PATCH_STEP}")
    if boundary.get("model_final_patch_apply_result_ref") is None and not pre_patch_terminal_failure:
        failures.append(f"{label}: 缺少 model_final_patch_apply_result_ref")
    if empty_patch_failure and boundary.get("empty_final_patch_result_ref") is None:
        failures.append(f"{label}: 空补丁失败必须绑定 empty_final_patch_result_ref")
    model_apply_failed = boundary.get("failure_category") == "model_patch_apply_failed"
    if not model_apply_failed and not pre_patch_terminal_failure:
        if _HIDDEN_PATCH_STEP not in observed:
            failures.append(f"{label}: observed_command_order 缺少 {_HIDDEN_PATCH_STEP}")
        if boundary.get("hidden_test_patch_apply_result_ref") is None:
            failures.append(f"{label}: 缺少 hidden_test_patch_apply_result_ref")
    hidden_patch_failed = str(boundary.get("failure_category") or "").startswith("hidden_test_patch")
    if (
        not model_apply_failed
        and not pre_patch_terminal_failure
        and not hidden_patch_failed
        and boundary.get("final_verifier_status") != "not_executed"
    ):
        if _F2P_STEP not in observed:
            failures.append(f"{label}: observed_command_order 缺少 {_F2P_STEP}")
        if boundary.get("fail_to_pass_result_ref") is None:
            failures.append(f"{label}: 缺少 fail_to_pass_result_ref")
        if _P2P_STEP not in observed:
            failures.append(f"{label}: observed_command_order 缺少 {_P2P_STEP}")
        if boundary.get("pass_to_pass_result_ref") is None:
            failures.append(f"{label}: 缺少 pass_to_pass_result_ref")
    _require_order(observed, _MODEL_PATCH_STEP, _HIDDEN_PATCH_STEP, failures, label)
    if _HIDDEN_PATCH_STEP in observed:
        for selector_step in (_F2P_STEP, _P2P_STEP):
            if selector_step in observed:
                _require_order(observed, _HIDDEN_PATCH_STEP, selector_step, failures, label)


def _require_order(
    observed: list[Any],
    before: str,
    after: str,
    failures: list[str],
    label: str,
) -> None:
    if before not in observed or after not in observed:
        return
    if observed.index(before) > observed.index(after):
        failures.append(f"{label}: command order 必须满足 {before} 早于 {after}")


def _inspect_run_task_lineage(
    run_dir: Path,
    boundary: dict[str, Any],
    entry: dict[str, Any],
    index_path: Path,
    failures: list[str],
    label: str,
) -> None:
    if boundary.get("run_task_entrypoint") != "repo-harness run-task":
        failures.append(f"{label}: run_task_entrypoint 必须是 repo-harness run-task")
    if boundary.get("baseline_source") != PRE_VERL_AGENTLOOP_BASELINE_SOURCE:
        failures.append(f"{label}: baseline_source 必须是 {PRE_VERL_AGENTLOOP_BASELINE_SOURCE}")
    boundary_ref = entry.get("final_verifier_boundary_ref") or entry.get("boundary_ref")
    _inspect_index_artifact_ref(boundary_ref, index_path.parent, failures, f"{label}.final_verifier_boundary_ref")
    metadata = _read_optional_json(run_dir / "run_metadata.json", failures, f"{label}.run_metadata")
    run_id = None
    if isinstance(metadata, dict):
        run_id = metadata.get("run_id")
        if not run_id:
            failures.append(f"{label}: run_metadata.json 缺少 run_id")
        if metadata.get("scaffold_id") == "single_shot_patch_no_tools":
            failures.append(f"{label}: run_metadata 不能使用 single_shot_patch_no_tools")
    run_config_facts = _read_optional_json(
        run_dir / "run_config_facts.json", failures, f"{label}.run_config_facts"
    )
    if isinstance(run_config_facts, dict):
        if run_config_facts.get("final_verifier_mode") != "strict_patch_replay":
            failures.append(f"{label}: run_config_facts.final_verifier_mode 必须是 strict_patch_replay")
        if run_config_facts.get("test_feedback_policy") != "disabled":
            failures.append(f"{label}: run_config_facts.test_feedback_policy 必须是 disabled")
        if run_config_facts.get("scaffold_id") == "single_shot_patch_no_tools":
            failures.append(f"{label}: run_config_facts 不能使用 single_shot_patch_no_tools")
        tool_protocol = run_config_facts.get("tool_protocol")
        tool_ref = tool_protocol.get("tool_schema_snapshot_ref") if isinstance(tool_protocol, dict) else None
        _inspect_run_artifact_ref(tool_ref, run_dir, failures, f"{label}.tool_schema_snapshot_ref")
    _inspect_run_task_command_entry(
        entry=entry,
        index_path=index_path,
        run_id=str(run_id or ""),
        failures=failures,
        label=label,
    )
    events = _read_jsonl_events(run_dir / "events.jsonl", failures, f"{label}.events")
    if not events:
        failures.append(f"{label}: events.jsonl 为空，无法证明 AgentLoop events")
    else:
        _inspect_agentloop_events(events, run_dir, failures, label)
    transcript_path = run_dir / "transcript.jsonl"
    if not transcript_path.exists() or transcript_path.stat().st_size == 0:
        failures.append(f"{label}: transcript.jsonl 缺失或为空，无法证明 AgentLoop transcript")


def _inspect_run_task_command_entry(
    *,
    entry: dict[str, Any],
    index_path: Path,
    run_id: str,
    failures: list[str],
    label: str,
) -> None:
    ref = entry.get("run_task_command_log_entry_ref")
    if not isinstance(ref, dict):
        failures.append(f"{label}: 缺少 run_task_command_log_entry_ref")
        return
    _inspect_index_artifact_ref(ref, index_path.parent, failures, f"{label}.run_task_command_log_entry_ref")
    path = _ref_path(ref, index_path.parent)
    payload = _read_optional_json(path, failures, f"{label}.run_task_command_log_entry")
    if not isinstance(payload, dict):
        return
    if payload.get("command_name") != "run-task":
        failures.append(f"{label}: command log entry.command_name 必须是 run-task")
    if payload.get("exit_code") != 0:
        failures.append(f"{label}: run-task command log entry exit_code 必须是 0")
    argv = payload.get("argv")
    if not isinstance(argv, list):
        failures.append(f"{label}: run-task command log entry argv 必须是 list")
        return
    argv_strings = [str(item) for item in argv]
    if "run-task" not in argv_strings:
        failures.append(f"{label}: run-task command log entry argv 缺少 run-task")
    if run_id:
        try:
            run_id_index = argv_strings.index("--run-id")
        except ValueError:
            failures.append(f"{label}: run-task command log entry argv 缺少 --run-id")
        else:
            observed_run_id = argv_strings[run_id_index + 1] if run_id_index + 1 < len(argv_strings) else None
            if observed_run_id != run_id:
                failures.append(f"{label}: run-task command log entry --run-id 与 run_metadata.run_id 不一致")


def _inspect_agentloop_events(
    events: list[dict[str, Any]],
    run_dir: Path,
    failures: list[str],
    label: str,
) -> None:
    event_types = [str(event.get("event_type") or "") for event in events]
    for required in ("run_started", "baseline_completed", "context_prepared", "model_call_started", "model_call_completed", "run_finished"):
        if required not in event_types:
            failures.append(f"{label}: events.jsonl 缺少 AgentLoop 事件 {required}")
    started_calls = _model_call_ids(events, "model_call_started")
    completed_calls = _model_call_ids(events, "model_call_completed")
    if set(started_calls) != set(completed_calls):
        failures.append(f"{label}: model_call_started 与 model_call_completed 不配对")
    for index, event in enumerate(events):
        if event.get("event_type") != "model_call_completed":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        _inspect_run_artifact_ref(
            data.get("raw_provider_request_ref"),
            run_dir,
            failures,
            f"{label}.model_call_completed[{index}].raw_provider_request_ref",
        )
        _inspect_run_artifact_ref(
            data.get("raw_provider_response_ref"),
            run_dir,
            failures,
            f"{label}.model_call_completed[{index}].raw_provider_response_ref",
        )
    requested_tool_ids = _tool_call_ids(events, {"tool_requested"})
    terminal_tool_ids = _tool_call_ids(
        events,
        {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"},
    )
    missing_results = sorted(set(requested_tool_ids) - set(terminal_tool_ids))
    unexpected_results = sorted(set(terminal_tool_ids) - set(requested_tool_ids))
    if missing_results:
        failures.append(f"{label}: tool_use 缺少对应 tool_result: {missing_results}")
    if unexpected_results:
        failures.append(f"{label}: tool_result 没有对应 tool_use: {unexpected_results}")


def _model_call_ids(events: list[dict[str, Any]], event_type: str) -> list[str]:
    ids: list[str] = []
    for event in events:
        if event.get("event_type") != event_type:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        model_call_id = data.get("model_call_id")
        if isinstance(model_call_id, str) and model_call_id:
            ids.append(model_call_id)
    return ids


def _tool_call_ids(events: list[dict[str, Any]], event_types: set[str]) -> list[str]:
    ids: list[str] = []
    for event in events:
        if event.get("event_type") not in event_types:
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        tool_call_id = data.get("tool_call_id")
        if isinstance(tool_call_id, str) and tool_call_id:
            ids.append(tool_call_id)
    return ids


def _inspect_run_artifact_ref(ref: Any, run_dir: Path, failures: list[str], label: str) -> None:
    if not isinstance(ref, dict):
        failures.append(f"{label}: 缺少 artifact ref")
        return
    path = _ref_path(ref, run_dir)
    if not path.exists():
        failures.append(f"{label}: artifact path 不存在")
        return
    expected_sha = ref.get("sha256")
    if not isinstance(expected_sha, str):
        failures.append(f"{label}: artifact ref 缺少 sha256")
    expected_size = ref.get("size_bytes")
    if not isinstance(expected_size, int):
        failures.append(f"{label}: artifact ref 缺少 size_bytes")
    if isinstance(expected_size, int) and path.is_file() and path.stat().st_size != expected_size:
        failures.append(f"{label}: artifact size_bytes drift")
    if isinstance(expected_sha, str) and path.is_file() and compute_file_sha256(path) != expected_sha:
        failures.append(f"{label}: artifact sha256 drift")


def _inspect_index_artifact_ref(ref: Any, base_dir: Path, failures: list[str], label: str) -> None:
    if not isinstance(ref, dict):
        failures.append(f"{label}: 缺少 artifact ref")
        return
    path = _ref_path(ref, base_dir)
    if not path.exists():
        failures.append(f"{label}: artifact path 不存在")
        return
    expected_sha = ref.get("sha256")
    if not isinstance(expected_sha, str):
        failures.append(f"{label}: artifact ref 缺少 sha256")
    expected_size = ref.get("size_bytes")
    if not isinstance(expected_size, int):
        failures.append(f"{label}: artifact ref 缺少 size_bytes")
    if isinstance(expected_size, int) and path.is_file() and path.stat().st_size != expected_size:
        failures.append(f"{label}: artifact size_bytes drift")
    if isinstance(expected_sha, str) and path.is_file() and compute_file_sha256(path) != expected_sha:
        failures.append(f"{label}: artifact sha256 drift")


def _read_jsonl_events(path: Path, failures: list[str], label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        failures.append(f"{label}: 无法读取 {path}: {exc}")
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{label}: 第 {line_number} 行 JSON 解析失败: {exc}")
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _ref_path(ref: dict[str, Any], base_dir: Path) -> Path:
    value = ref.get("path") or ref.get("relative_path")
    if not isinstance(value, str) or not value.strip():
        return base_dir / "<missing-ref-path>"
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _inspect_formal_metadata(definition: TaskDefinition, failures: list[str], path: Path) -> None:
    metadata = definition.metadata or {}
    required = {
        "pre_verl_adapter": PRE_VERL_AGENTLOOP_ADAPTER_ID,
        "pre_verl_agentloop_mode": PRE_VERL_AGENTLOOP_MODE,
        "pre_verl_agentloop_baseline_source": PRE_VERL_AGENTLOOP_BASELINE_SOURCE,
        "swe_bench_like_final_only": True,
        "final_only": True,
    }
    for key, expected in required.items():
        if metadata.get(key) != expected:
            failures.append(f"{path}: metadata.{key} must be {expected!r}")
    manifest_path = metadata.get("pre_verl_swebench_dev_manifest_path")
    if not isinstance(manifest_path, str) or not manifest_path.strip():
        failures.append(f"{path}: metadata.pre_verl_swebench_dev_manifest_path must be a non-empty string")
    if metadata.get("v3_adapter") == LEGACY_V3_SWEBENCH_LIKE_ADAPTER_ID:
        failures.append(f"{path}: formal pre-verl task cannot use legacy v3_adapter=swebench_like_fixed")
    if not is_formal_pre_verl_agentloop_metadata(metadata):
        failures.append(f"{path}: formal pre-verl metadata shape is incomplete")


def _inspect_evaluator_only_refs(
    definition: TaskDefinition,
    failures: list[str],
    path: Path,
) -> None:
    metadata = definition.metadata or {}
    for key in _REQUIRED_EVALUATOR_ONLY_REFS:
        ref = metadata.get(key)
        if not isinstance(ref, dict):
            failures.append(f"{path}: metadata.{key} must be an evaluator-only ref")
            continue
        visibility = ref.get("visibility") or ref.get("redaction_status")
        if visibility != "evaluator_only":
            failures.append(f"{path}: metadata.{key} must have visibility=evaluator_only")
        ref_path = ref.get("path") or ref.get("relative_path")
        if not isinstance(ref_path, str) or not ref_path.strip():
            failures.append(f"{path}: metadata.{key} must bind path or relative_path")
        sha256 = ref.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64 or not _is_lower_hex_sha256(sha256):
            failures.append(f"{path}: metadata.{key} must bind sha256")
        size_bytes = ref.get("size_bytes")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            failures.append(f"{path}: metadata.{key} must bind non-negative size_bytes")
        if key.endswith("_selectors_ref"):
            ref_path = _metadata_ref_path(ref, path.parent)
            if ref_path.exists():
                try:
                    selectors = _read_selector_ref(ref, path.parent)
                except ConfigError as exc:
                    failures.append(f"{path}: metadata.{key} selector list invalid: {exc}")
                else:
                    if not selectors and key == "fail_to_pass_selectors_ref":
                        failures.append(f"{path}: metadata.{key} must not be empty")
    if definition.gold_patch is not None:
        failures.append(f"{path}: formal pre-verl TaskDefinition must not inline raw gold_patch")


def _metadata_ref_path(ref: dict[str, Any], base_dir: Path) -> Path:
    value = ref.get("path") or ref.get("relative_path")
    if not isinstance(value, str) or not value.strip():
        return base_dir / "<missing-ref-path>"
    raw = Path(value)
    return raw if raw.is_absolute() else base_dir / raw


def _inspect_model_visible_fields(
    definition: TaskDefinition,
    failures: list[str],
    path: Path,
) -> None:
    fields = {
        "issue": definition.issue,
        "expected_files": definition.expected_files,
        "tags": definition.tags,
    }
    for field, value in fields.items():
        finding = _find_hidden_marker(value)
        if finding:
            failures.append(f"{path}: model-visible field {field} contains hidden marker {finding!r}")


def _inspect_deepseek_formal_provider_config(
    *,
    definition: TaskDefinition,
    run_config: RunConfig,
    config_path: Path,
    failures: list[str],
) -> None:
    if run_config.model.provider != "deepseek":
        return
    if run_config.runtime.execution_mode != "docker":
        failures.append(f"{config_path}: DeepSeek formal pre-verl run config must use execution_mode=docker")
    expected_image = definition.environment.execution_image
    actual_image = run_config.runtime.docker_backend.build_base_image
    if not expected_image:
        failures.append(
            f"{config_path}: DeepSeek formal pre-verl task must set TaskDefinition.environment.execution_image"
        )
    elif actual_image != expected_image:
        failures.append(
            f"{config_path}: runtime.docker_backend.build_base_image={actual_image!r} "
            f"must equal TaskDefinition.environment.execution_image={expected_image!r}"
        )
    thinking = run_config.model.provider_specific_options.get("thinking")
    if not isinstance(thinking, dict) or thinking.get("type") not in {"enabled", "disabled"}:
        failures.append(
            f"{config_path}: DeepSeek formal pre-verl run config must explicitly set provider_specific_options.thinking.type"
        )
    compatibility = run_config.model.provider_specific_options.get("reasoning_compatibility")
    if isinstance(thinking, dict) and thinking.get("type") == "enabled" and compatibility != "provider_private_state_replay":
        failures.append(
            f"{config_path}: DeepSeek thinking enabled requires reasoning_compatibility=provider_private_state_replay"
        )


def _inspect_resolved_policy_and_context(
    *,
    definition: TaskDefinition,
    run_config: RunConfig,
    config_path: Path,
    expected_resolved_tools: list[str] | None,
    failures: list[str],
    assert_resolved_tools_derived: bool,
    assert_no_hidden_feedback_visible: bool,
) -> None:
    runnable = RunnableTask.from_definition(definition)
    scaffold = build_scaffold(run_config.runtime.scaffold_id)
    try:
        feedback_policy = resolve_feedback_policy(
            run_config=run_config,
            scaffold=scaffold,
            task=definition,
        )
    except ConfigError as exc:
        failures.append(f"{config_path}: feedback policy invalid: {exc}")
        return
    resolved_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    if assert_resolved_tools_derived and expected_resolved_tools is not None:
        if list(expected_resolved_tools) != resolved_tools:
            failures.append(f"{config_path}: resolved_tools does not match scaffold/test feedback policy")
    if assert_resolved_tools_derived and expected_resolved_tools is None:
        failures.append(f"{config_path}: resolved_tools audit field is required")
    if assert_no_hidden_feedback_visible:
        if feedback_policy.hidden_feedback_visible_to_model:
            failures.append(f"{config_path}: hidden feedback is model-visible")
        if feedback_policy.resolved_test_feedback_policy.value != "disabled":
            failures.append(f"{config_path}: final-only task resolved test feedback must be disabled")
        _inspect_context_redaction(
            runnable=runnable,
            run_config=run_config,
            scaffold=scaffold,
            resolved_tools=resolved_tools,
            failures=failures,
            config_path=config_path,
        )


def _inspect_context_redaction(
    *,
    runnable: RunnableTask,
    run_config: RunConfig,
    scaffold: Any,
    resolved_tools: list[str],
    failures: list[str],
    config_path: Path,
) -> None:
    with tempfile.TemporaryDirectory(prefix="repo_harness_pre_verl_context_") as temp:
        workspace = RunWorkspace(
            run_id="pre_verl_context_inspect",
            workspace_path=temp,
            artifact_dir=str(Path(temp) / "artifacts"),
            dependency_state=DependencyState(),
        )
        plan = ResolvedVerifierPlan(
            verifier_config=runnable.verifier_config,
            parser_confidence=1.0,
            resolved_verifier_plan_id="pre_verl_context_inspect",
        )
        messages = ContextBuilder().build_initial_messages(
            task=runnable,
            workspace=workspace,
            run_config=run_config,
            resolved_verifier_plan=plan,
            allowed_tools=resolved_tools,
            scaffold=scaffold,
        )
    user_content = messages[1].get("content")
    if not isinstance(user_content, dict):
        failures.append(f"{config_path}: prepared user message is not structured")
        return
    if user_content.get("test_command") is not None:
        failures.append(f"{config_path}: prepared messages exposed test_command")
    if user_content.get("test_command_visibility") != "redacted_final_only":
        failures.append(f"{config_path}: test_command_visibility must be redacted_final_only")
    finding = _find_hidden_marker(messages)
    if finding:
        failures.append(f"{config_path}: prepared messages contain hidden marker {finding!r}")


def _collect_run_config_entries(payload: Any, base: Path) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("entries"), list):
        entries = []
        for item in payload["entries"]:
            if not isinstance(item, dict):
                continue
            task_ref = item.get("task_definition_ref") or item.get("task_ref") or item.get("task_definition")
            config_ref = item.get("run_config_ref") or item.get("config_ref") or item.get("run_config")
            if task_ref and config_ref:
                entries.append(
                    {
                        "task_path": _path_from_ref(task_ref, base),
                        "config_path": _path_from_ref(config_ref, base),
                        "resolved_tools": item.get("resolved_tools"),
                    }
                )
        return entries
    task_paths = _collect_paths(payload, base, ("task_definition_refs", "task_definitions", "tasks"))
    config_paths = _collect_paths(payload, base, ("run_config_refs", "run_configs", "configs"))
    if len(task_paths) != len(config_paths):
        return []
    return [
        {"task_path": task_path, "config_path": config_path, "resolved_tools": None}
        for task_path, config_path in zip(task_paths, config_paths)
    ]


def _collect_paths(payload: Any, base: Path, keys: tuple[str, ...]) -> list[Path]:
    records: Any = payload if isinstance(payload, list) else None
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
    if not isinstance(records, list):
        return []
    return [_path_from_ref(item, base) for item in records]


def _path_from_ref(ref: Any, base: Path) -> Path:
    value: str
    if isinstance(ref, str):
        value = ref
    elif isinstance(ref, dict):
        raw = ref.get("path") or ref.get("relative_path")
        if not raw:
            return base.parent / "<missing>"
        value = str(raw)
    else:
        return base.parent / "<invalid>"
    path = Path(value)
    return path if path.is_absolute() else (base.parent / path)


def _load_task_definition(path: Path, failures: list[str]) -> TaskDefinition | None:
    try:
        raw = _read_structured(path)
        return TaskDefinition.model_validate(raw)
    except (OSError, ValidationError, ConfigError) as exc:
        failures.append(f"{path}: invalid TaskDefinition: {exc}")
        return None


def _read_structured(path: str | Path) -> Any:
    target = Path(path)
    try:
        return yaml.safe_load(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"无法读取文件：{target}") from exc


def _write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _find_hidden_marker(value: Any) -> str | None:
    if isinstance(value, str):
        for marker in _HIDDEN_MARKERS:
            if marker in value:
                return marker
        return None
    if isinstance(value, dict):
        for item in value.values():
            finding = _find_hidden_marker(item)
            if finding:
                return finding
    if isinstance(value, list):
        for item in value:
            finding = _find_hidden_marker(item)
            if finding:
                return finding
    return None


def _is_lower_hex_sha256(value: str) -> bool:
    return all(char in "0123456789abcdef" for char in value)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _inspect_result(
    title: str,
    path: str | Path,
    failures: list[str],
    *,
    assert_requested: bool,
) -> str:
    if failures and assert_requested:
        raise ConfigError("; ".join(failures))
    status = "passed" if not failures else "failed"
    payload = {
        "path": str(path),
        "status": status,
        "failure_count": len(failures),
        "failures": failures,
    }
    return f"{title}: {status}\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
