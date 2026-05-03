"""V3 SWE-Bench-like verifier plan and final verifier evidence."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import ConfigError
from repo_harness.tasks import SweBenchLikeEnvironmentSpec
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_swebench_fixture import EXPECTED_ACCEPTED_TASK_IDS
from repo_harness.verifier.pytest_parser import PytestTextParser
from repo_harness.verifier.schemas import SweBenchLikeVerifierPlan
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

SWEBENCH_LIKE_MANIFEST_VERSION = "repo_harness_swebench_like_task_manifest_v3_v0"
SWEBENCH_LIKE_COMMAND_RESULT_VERSION = "repo_harness_swebench_like_command_result_v3_v0"
SWEBENCH_LIKE_FINAL_RESULT_VERSION = "repo_harness_swebench_like_final_verifier_result_v3_v0"
SWEBENCH_LIKE_INSPECT_VERSION = "repo_harness_swebench_like_inspect_v3_v0"
SELECTOR_CACHE_VERSION = "repo_harness_swebench_like_selector_cache_v3_v0"
SETUP_COMMANDS_VERSION = "repo_harness_swebench_like_setup_commands_v3_v0"
PATCH_APPLY_FACTS_VERSION = "repo_harness_swebench_like_patch_apply_facts_v3_v0"


def build_v3_swebench_like(
    *,
    source_materialization_run: str | Path,
    hidden_verifier_inputs: str | Path,
    gold_patch_predictions: str | Path,
    output_dir: str | Path,
    execute: bool = True,
) -> Path:
    """Build resolved plans and RepoHarness-owned verifier evidence for fixed tasks."""

    source_root = Path(source_materialization_run)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    source_report = _read_json(source_root / "source_materialization_report.json")
    source_entries = {
        entry["task_id"]: entry for entry in source_report.get("entries", []) if entry.get("task_category") == "swebench_like"
    }
    hidden_rows = _read_jsonl(Path(hidden_verifier_inputs))
    gold_rows = _read_jsonl(Path(gold_patch_predictions))
    hidden_by_id = {row["instance_id"]: row for row in hidden_rows}
    gold_by_id = {row["instance_id"]: row for row in gold_rows}
    entries: list[dict[str, Any]] = []
    for task_id in EXPECTED_ACCEPTED_TASK_IDS:
        if task_id not in source_entries:
            raise ConfigError(f"source materialization report 缺少 SWE-Bench-like task：{task_id}")
        if task_id not in hidden_by_id:
            raise ConfigError(f"hidden verifier inputs 缺少 SWE-Bench-like task：{task_id}")
        if task_id not in gold_by_id:
            raise ConfigError(f"gold patch predictions 缺少 SWE-Bench-like task：{task_id}")
        entries.append(
            _build_task_evidence(
                output_root=output_root,
                source_root=source_root,
                source_entry=source_entries[task_id],
                hidden_row=hidden_by_id[task_id],
                gold_row=gold_by_id[task_id],
                execute=execute,
            )
        )
    manifest = {
        "schema_version": SWEBENCH_LIKE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "task_count": len(entries),
        "accepted_task_ids": list(EXPECTED_ACCEPTED_TASK_IDS),
        "source_materialization_report_ref": _artifact_ref(
            source_root / "source_materialization_report.json",
            artifact_id="source_materialization_report",
            kind="json",
        ).model_dump(mode="json"),
        "hidden_verifier_inputs_ref": _artifact_ref(
            Path(hidden_verifier_inputs),
            artifact_id="hidden_verifier_inputs",
            kind="jsonl",
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
        "gold_patch_predictions_ref": _artifact_ref(
            Path(gold_patch_predictions),
            artifact_id="gold_patch_predictions",
            kind="jsonl",
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
        "entries": entries,
        "official_harness_report_used_as_final_verifier": False,
    }
    _write_json(output_root / "swebench_like_task_manifest.json", manifest)
    return output_root


def inspect_swebench_like(
    run_dir: str | Path,
    *,
    manifest: str | Path,
    assert_complete: bool = False,
) -> str:
    """Inspect SWE-Bench-like verifier plans and evidence."""

    run_root = Path(run_dir)
    manifest_path = Path(manifest)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if failures:
        return _inspect_result(run_root, failures, assert_complete)
    if payload.get("schema_version") != SWEBENCH_LIKE_MANIFEST_VERSION:
        failures.append("swebench_like_task_manifest schema_version 不匹配。")
    if payload.get("accepted_task_ids") != list(EXPECTED_ACCEPTED_TASK_IDS):
        failures.append("SWE-Bench-like accepted task id 集合不匹配。")
    if payload.get("official_harness_report_used_as_final_verifier") is not False:
        failures.append("禁止把 official harness report 当作 V3 final verifier。")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(EXPECTED_ACCEPTED_TASK_IDS):
        failures.append("swebench_like_task_manifest 必须包含 3 个 accepted task。")
        entries = []
    _inspect_artifact_ref(run_root, payload.get("source_materialization_report_ref"), failures, "source_materialization_report_ref")
    _inspect_artifact_ref(run_root, payload.get("hidden_verifier_inputs_ref"), failures, "hidden_verifier_inputs_ref")
    _inspect_artifact_ref(run_root, payload.get("gold_patch_predictions_ref"), failures, "gold_patch_predictions_ref")
    for entry in entries:
        _inspect_swebench_entry(run_root, entry, failures, assert_complete=assert_complete)
    return _inspect_result(run_root, failures, assert_complete)


def expand_swebench_selectors(raw_selectors: list[str], *, test_patch: str, instance_id: str) -> list[str]:
    """Expand path node ids and bare function selectors into pytest node ids."""

    patched_test_files = _patched_test_files(test_patch)
    expanded: list[str] = []
    for selector in raw_selectors:
        if not selector or not isinstance(selector, str):
            raise ConfigError(f"SWE-Bench-like selector 为空：{instance_id}")
        if "::" in selector or "/" in selector:
            expanded.append(selector)
            continue
        if len(patched_test_files) != 1:
            raise ConfigError(f"裸函数名 selector 无法唯一映射 test_patch 文件：{instance_id}:{selector}")
        expanded.append(f"{patched_test_files[0]}::{selector}")
    if not expanded:
        raise ConfigError(f"SWE-Bench-like selector 转换结果为空：{instance_id}")
    return expanded


def _build_task_evidence(
    *,
    output_root: Path,
    source_root: Path,
    source_entry: dict[str, Any],
    hidden_row: dict[str, Any],
    gold_row: dict[str, Any],
    execute: bool,
) -> dict[str, Any]:
    task_id = source_entry["task_id"]
    task_root = output_root / "tasks" / task_id
    task_root.mkdir(parents=True, exist_ok=True)
    raw_f2p = _parse_selector_json(hidden_row["FAIL_TO_PASS"], task_id, "FAIL_TO_PASS")
    raw_p2p = _parse_selector_json(hidden_row["PASS_TO_PASS"], task_id, "PASS_TO_PASS")
    expanded_f2p = expand_swebench_selectors(raw_f2p, test_patch=hidden_row["test_patch"], instance_id=task_id)
    expanded_p2p = expand_swebench_selectors(raw_p2p, test_patch=hidden_row["test_patch"], instance_id=task_id)
    selector_cache = {
        "schema_version": SELECTOR_CACHE_VERSION,
        "instance_id": task_id,
        "selector_source": "evaluator_only_manifest_ref",
        "selector_conversion_rule": "path_node_id_passthrough_or_bare_function_to_patch_file",
        "raw_fail_to_pass": raw_f2p,
        "raw_pass_to_pass": raw_p2p,
        "expanded_fail_to_pass": expanded_f2p,
        "expanded_pass_to_pass": expanded_p2p,
        "patched_test_files": _patched_test_files(hidden_row["test_patch"]),
        "hidden_visibility_policy": "evaluator_only",
    }
    selector_cache_path = task_root / "selector_cache.json"
    _write_json(selector_cache_path, selector_cache)

    environment = _environment_for_task(task_id, hidden_row, task_root)
    task_definition = _read_yaml(_resolve_ref(source_root, source_entry["task_definition_ref"]["relative_path"]))
    setup_commands_path = task_root / "setup_commands.json"
    _write_json(setup_commands_path, environment["setup_commands_payload"])
    environment_spec = SweBenchLikeEnvironmentSpec(
        instance_id=task_id,
        repo=hidden_row["repo"],
        base_commit=hidden_row["base_commit"],
        environment_setup_commit=task_definition.get("metadata", {}).get("environment_setup_commit"),
        execution_image=environment["execution_image"],
        image_build_source="docker_hub_official_python_image",
        requested_container_platform="linux/amd64",
        python_version=environment["python_version"],
        setup_commands_ref=_artifact_ref(
            setup_commands_path,
            artifact_id=f"{task_id}_setup_commands",
            kind="json",
            base_dir=output_root,
        ),
        setup_timeout_sec=environment["setup_timeout_sec"],
        network_policy="controlled_network_for_setup_only_verifier_tests_network_none",
        mount_policy="workspace_bind_mount_read_write",
        expected_parser="pytest",
    )
    environment_spec_path = task_root / "swebench_like_environment_spec.json"
    _write_json(environment_spec_path, environment_spec.model_dump(mode="json"))

    verifier_patch_path = _copy_ref_from_source_root(
        source_root=source_root,
        ref_payload=source_entry["verifier_patch_ref"],
        destination=task_root / "evaluator_only" / "verifier.patch",
    )
    gold_patch_path = task_root / "evaluator_only" / "gold.patch"
    gold_patch_path.parent.mkdir(parents=True, exist_ok=True)
    gold_patch_path.write_text(gold_row["model_patch"], encoding="utf-8")
    model_patch_path = task_root / "evaluator_only" / "model_final.patch"
    model_patch_path.write_text(gold_row["model_patch"], encoding="utf-8")

    fail_command = _pytest_command(expanded_f2p)
    pass_command = _pytest_command(expanded_p2p)
    plan = SweBenchLikeVerifierPlan(
        instance_id=task_id,
        base_test_command="python -m pytest -q",
        fail_to_pass_command=fail_command,
        pass_to_pass_command=pass_command,
        selector_source="evaluator_only_manifest_ref",
        selector_cache_ref=_artifact_ref(
            selector_cache_path,
            artifact_id=f"{task_id}_selector_cache",
            kind="json",
            base_dir=output_root,
            redaction_status="evaluator_only",
        ),
        fail_to_pass_selector_count=len(expanded_f2p),
        pass_to_pass_selector_count=len(expanded_p2p),
        verifier_patch_ref=_artifact_ref(
            verifier_patch_path,
            artifact_id=f"{task_id}_verifier_patch",
            kind="patch",
            base_dir=output_root,
            redaction_status="evaluator_only",
        ),
        per_command_timeout_sec=environment["test_timeout_sec"],
        model_visible_test_command=None,
    )

    baseline_workspace = task_root / "baseline_workspace"
    _copy_tree(_resolve_ref(source_root, source_entry["verifier_workspace_ref"]["relative_path"]), baseline_workspace)
    setup_result = _run_setup(
        workspace=baseline_workspace,
        task_root=task_root,
        environment=environment,
        label=f"{task_id}_baseline_setup",
        execute=execute,
    )
    gold_workspace = task_root / "gold_workspace"
    final_workspace = task_root / "model_final_workspace"
    _copy_tree(baseline_workspace, gold_workspace)
    _copy_tree(baseline_workspace, final_workspace)
    gold_patch_apply = _apply_patch(
        workspace=gold_workspace,
        patch_path=gold_patch_path,
        task_root=task_root,
        label=f"{task_id}_gold_patch_apply",
        execute=execute,
    )
    final_patch_apply = _apply_patch(
        workspace=final_workspace,
        patch_path=model_patch_path,
        task_root=task_root,
        label=f"{task_id}_model_final_patch_apply",
        execute=execute,
    )
    evidence = _run_all_verifier_commands(
        task_id=task_id,
        task_root=task_root,
        environment=environment,
        plan=plan,
        selector_cache=selector_cache,
        baseline_workspace=baseline_workspace,
        gold_workspace=gold_workspace,
        final_workspace=final_workspace,
        execute=execute,
    )
    final_result_path = task_root / "final_verifier_result.json"
    final_result = _aggregate_final_result(
        task_id=task_id,
        final_patch_apply=final_patch_apply,
        model_results=evidence["model_final"],
        selector_cache=selector_cache,
    )
    _write_json(final_result_path, final_result)
    plan = plan.model_copy(
        update={
            "expected_artifact_refs": [
                _artifact_ref(
                    evidence["baseline"]["fail_to_pass_path"],
                    artifact_id=f"{task_id}_baseline_fail_to_pass",
                    kind="json",
                    base_dir=output_root,
                    redaction_status="evaluator_only",
                ),
                _artifact_ref(
                    evidence["baseline"]["pass_to_pass_path"],
                    artifact_id=f"{task_id}_baseline_pass_to_pass",
                    kind="json",
                    base_dir=output_root,
                    redaction_status="evaluator_only",
                ),
                _artifact_ref(
                    evidence["gold"]["combined_path"],
                    artifact_id=f"{task_id}_gold_patch_passing_evidence",
                    kind="json",
                    base_dir=output_root,
                    redaction_status="evaluator_only",
                ),
                _artifact_ref(
                    final_result_path,
                    artifact_id=f"{task_id}_final_verifier_result",
                    kind="json",
                    base_dir=output_root,
                    redaction_status="evaluator_only",
                ),
            ]
        }
    )
    plan_path = task_root / "swebench_like_verifier_plan.json"
    _write_json(plan_path, plan.model_dump(mode="json"))
    return {
        "task_id": task_id,
        "instance_id": task_id,
        "repo": hidden_row["repo"],
        "base_commit": hidden_row["base_commit"],
        "environment_spec_ref": _artifact_ref(
            environment_spec_path,
            artifact_id=f"{task_id}_environment_spec",
            kind="json",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "verifier_plan_ref": _artifact_ref(
            plan_path,
            artifact_id=f"{task_id}_verifier_plan",
            kind="json",
            base_dir=output_root,
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
        "selector_cache_ref": plan.selector_cache_ref.model_dump(mode="json"),
        "baseline_fail_to_pass_evidence_ref": plan.expected_artifact_refs[0].model_dump(mode="json"),
        "pass_to_pass_baseline_evidence_ref": plan.expected_artifact_refs[1].model_dump(mode="json"),
        "gold_patch_passing_evidence_ref": plan.expected_artifact_refs[2].model_dump(mode="json"),
        "model_final_verifier_result_ref": plan.expected_artifact_refs[3].model_dump(mode="json"),
        "baseline_workspace_ref": _artifact_ref(
            baseline_workspace,
            artifact_id=f"{task_id}_baseline_workspace",
            kind="source_directory",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "gold_workspace_ref": _artifact_ref(
            gold_workspace,
            artifact_id=f"{task_id}_gold_workspace",
            kind="source_directory",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "model_final_workspace_ref": _artifact_ref(
            final_workspace,
            artifact_id=f"{task_id}_model_final_workspace",
            kind="source_directory",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "verifier_patch_ref": plan.verifier_patch_ref.model_dump(mode="json"),
        "gold_patch_ref": _artifact_ref(
            gold_patch_path,
            artifact_id=f"{task_id}_gold_patch",
            kind="patch",
            base_dir=output_root,
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
        "model_final_patch_ref": _artifact_ref(
            model_patch_path,
            artifact_id=f"{task_id}_model_final_patch",
            kind="patch",
            base_dir=output_root,
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
        "setup_result": setup_result,
        "gold_patch_apply": gold_patch_apply,
        "model_final_patch_apply": final_patch_apply,
        "final_verifier_accepted": final_result["accepted"],
        "model_final_patch_source": "stage6_reference_patch_probe_from_fixed_gold_prediction",
        "hidden_visibility_policy": "evaluator_only",
    }


def _environment_for_task(task_id: str, hidden_row: dict[str, Any], task_root: Path) -> dict[str, Any]:
    if hidden_row["repo"] == "pytest-dev/pytest":
        return {
            "execution_image": "python:3.8-slim",
            "python_version": "3.8",
            "setup_timeout_sec": 1200,
            "test_timeout_sec": 300,
            "pythonpath": "src",
            "setup_commands_payload": {
                "schema_version": SETUP_COMMANDS_VERSION,
                "instance_id": task_id,
                "commands": [
                    "python -m venv .v3_verifier_venv",
                    ". .v3_verifier_venv/bin/activate",
                    "python -m pip install -q --upgrade pip",
                    "SETUPTOOLS_SCM_PRETEND_VERSION=5.0.0 python -m pip install -q -e '.[testing]'",
                ],
                "network_policy": "controlled_network_for_setup_only",
            },
            "setup_shell": (
                "rm -rf .v3_verifier_venv && python -m venv .v3_verifier_venv "
                "&& . .v3_verifier_venv/bin/activate "
                "&& python -m pip install -q --upgrade pip "
                "&& SETUPTOOLS_SCM_PRETEND_VERSION=5.0.0 python -m pip install -q -e '.[testing]'"
            ),
        }
    if hidden_row["repo"] == "sympy/sympy":
        return {
            "execution_image": "python:3.11-slim",
            "python_version": "3.11",
            "setup_timeout_sec": 900,
            "test_timeout_sec": 300,
            "pythonpath": ".",
            "setup_commands_payload": {
                "schema_version": SETUP_COMMANDS_VERSION,
                "instance_id": task_id,
                "commands": [
                    "python -m venv .v3_verifier_venv",
                    ". .v3_verifier_venv/bin/activate",
                    "python -m pip install -q --upgrade pip pytest mpmath",
                ],
                "network_policy": "controlled_network_for_setup_only",
            },
            "setup_shell": (
                "rm -rf .v3_verifier_venv && python -m venv .v3_verifier_venv "
                "&& . .v3_verifier_venv/bin/activate "
                "&& python -m pip install -q --upgrade pip pytest mpmath"
            ),
        }
    raise ConfigError(f"未知 SWE-Bench-like repo environment：{hidden_row['repo']}")


def _run_setup(
    *,
    workspace: Path,
    task_root: Path,
    environment: dict[str, Any],
    label: str,
    execute: bool,
) -> dict[str, Any]:
    if not execute:
        return {"status": "skipped", "structured_skip_reason": "execute_false"}
    return _run_docker_shell(
        workspace=workspace,
        task_root=task_root,
        image=environment["execution_image"],
        command=environment["setup_shell"],
        timeout_sec=environment["setup_timeout_sec"],
        label=label,
        network="default",
        pythonpath=None,
    )


def _run_all_verifier_commands(
    *,
    task_id: str,
    task_root: Path,
    environment: dict[str, Any],
    plan: SweBenchLikeVerifierPlan,
    selector_cache: dict[str, Any],
    baseline_workspace: Path,
    gold_workspace: Path,
    final_workspace: Path,
    execute: bool,
) -> dict[str, Any]:
    evidence_root = task_root / "verifier_evidence"
    result: dict[str, Any] = {"baseline": {}, "gold": {}, "model_final": {}}
    phases = [
        ("baseline", baseline_workspace),
        ("gold", gold_workspace),
        ("model_final", final_workspace),
    ]
    for phase, workspace in phases:
        f2p = _run_verifier_command(
            task_id=task_id,
            task_root=task_root,
            workspace=workspace,
            environment=environment,
            command=plan.fail_to_pass_command,
            selectors=selector_cache["expanded_fail_to_pass"],
            phase=phase,
            suite="fail_to_pass",
            execute=execute,
        )
        p2p = _run_verifier_command(
            task_id=task_id,
            task_root=task_root,
            workspace=workspace,
            environment=environment,
            command=plan.pass_to_pass_command,
            selectors=selector_cache["expanded_pass_to_pass"],
            phase=phase,
            suite="pass_to_pass",
            execute=execute,
        )
        phase_payload = {
            "schema_version": "repo_harness_swebench_like_phase_evidence_v3_v0",
            "instance_id": task_id,
            "phase": phase,
            "fail_to_pass": f2p,
            "pass_to_pass": p2p,
        }
        combined_path = evidence_root / phase / "combined_evidence.json"
        _write_json(combined_path, phase_payload)
        result[phase] = {
            "fail_to_pass": f2p,
            "pass_to_pass": p2p,
            "combined_path": combined_path,
            "fail_to_pass_path": evidence_root / phase / "fail_to_pass.json",
            "pass_to_pass_path": evidence_root / phase / "pass_to_pass.json",
        }
        _write_json(result[phase]["fail_to_pass_path"], f2p)
        _write_json(result[phase]["pass_to_pass_path"], p2p)
    return result


def _run_verifier_command(
    *,
    task_id: str,
    task_root: Path,
    workspace: Path,
    environment: dict[str, Any],
    command: str,
    selectors: list[str],
    phase: str,
    suite: str,
    execute: bool,
) -> dict[str, Any]:
    if not execute:
        return {
            "schema_version": SWEBENCH_LIKE_COMMAND_RESULT_VERSION,
            "instance_id": task_id,
            "phase": phase,
            "suite": suite,
            "status": "skipped",
            "structured_skip_reason": "execute_false",
            "command": command,
            "selectors": selectors,
        }
    docker_result = _run_docker_shell(
        workspace=workspace,
        task_root=task_root,
        image=environment["execution_image"],
        command=_test_shell(command, environment),
        timeout_sec=environment["test_timeout_sec"],
        label=f"{task_id}_{phase}_{suite}",
        network="none",
        pythonpath=environment["pythonpath"],
    )
    parser = PytestTextParser()
    stdout = _read_ref_text(task_root, docker_result.get("stdout_ref"))
    stderr = _read_ref_text(task_root, docker_result.get("stderr_ref"))
    parser_confidence = parser.parser_confidence(stdout, stderr, docker_result["exit_code"])
    error_type = parser.error_type(stdout, stderr, docker_result["exit_code"], docker_result["timeout"])
    status = _suite_status(docker_result["exit_code"], docker_result["timeout"])
    test_cases = [{"test_id": selector, "status": status} for selector in selectors]
    return {
        "schema_version": SWEBENCH_LIKE_COMMAND_RESULT_VERSION,
        "instance_id": task_id,
        "phase": phase,
        "suite": suite,
        "command": command,
        "selectors": selectors,
        "exit_code": docker_result["exit_code"],
        "timeout": docker_result["timeout"],
        "parser_id": parser.parser_id,
        "parser_version": parser.parser_version,
        "parser_confidence": parser_confidence,
        "error_type": error_type,
        "test_cases": test_cases,
        "passed_count": sum(1 for case in test_cases if case["status"] == "passed"),
        "total_count": len(test_cases),
        "stdout_ref": docker_result.get("stdout_ref"),
        "stderr_ref": docker_result.get("stderr_ref"),
        "container_execution_facts": docker_result,
    }


def _aggregate_final_result(
    *,
    task_id: str,
    final_patch_apply: dict[str, Any],
    model_results: dict[str, Any],
    selector_cache: dict[str, Any],
) -> dict[str, Any]:
    f2p = model_results["fail_to_pass"]
    p2p = model_results["pass_to_pass"]
    f2p_passed = f2p.get("passed_count", 0)
    p2p_passed = p2p.get("passed_count", 0)
    f2p_total = len(selector_cache["expanded_fail_to_pass"])
    p2p_total = len(selector_cache["expanded_pass_to_pass"])
    low_confidence = min(f2p.get("parser_confidence", 0.0), p2p.get("parser_confidence", 0.0)) < 0.5
    accepted = (
        final_patch_apply.get("status") == "passed"
        and f2p_passed == f2p_total
        and p2p_passed == p2p_total
        and not low_confidence
    )
    error_type = None
    if not accepted:
        if final_patch_apply.get("status") != "passed":
            error_type = "patch_apply_failed"
        elif low_confidence:
            error_type = "low_parser_confidence"
        elif p2p_passed != p2p_total:
            error_type = "regression_detected"
        else:
            error_type = "assertion_failure"
    return {
        "schema_version": SWEBENCH_LIKE_FINAL_RESULT_VERSION,
        "instance_id": task_id,
        "verifier_stage": "final",
        "accepted": accepted,
        "error_type": error_type,
        "fail_to_pass": {"passed": f2p_passed, "total": f2p_total},
        "pass_to_pass": {"passed": p2p_passed, "total": p2p_total},
        "parser_confidence": min(f2p.get("parser_confidence", 0.0), p2p.get("parser_confidence", 0.0)),
        "final_patch_apply": final_patch_apply,
        "fail_to_pass_result": f2p,
        "pass_to_pass_result": p2p,
        "official_harness_report_used": False,
        "hidden_visibility_policy": "evaluator_only",
    }


def _inspect_swebench_entry(
    run_root: Path,
    entry: dict[str, Any],
    failures: list[str],
    *,
    assert_complete: bool,
) -> None:
    task_id = entry.get("task_id")
    for field in (
        "task_id",
        "environment_spec_ref",
        "verifier_plan_ref",
        "selector_cache_ref",
        "baseline_fail_to_pass_evidence_ref",
        "pass_to_pass_baseline_evidence_ref",
        "gold_patch_passing_evidence_ref",
        "model_final_verifier_result_ref",
    ):
        if not entry.get(field):
            failures.append(f"SWE-Bench-like manifest entry 字段为空：{task_id}:{field}")
    env_path = _inspect_artifact_ref(run_root, entry.get("environment_spec_ref"), failures, "environment_spec_ref")
    plan_path = _inspect_artifact_ref(run_root, entry.get("verifier_plan_ref"), failures, "verifier_plan_ref")
    selector_path = _inspect_artifact_ref(run_root, entry.get("selector_cache_ref"), failures, "selector_cache_ref")
    baseline_f2p_path = _inspect_artifact_ref(
        run_root,
        entry.get("baseline_fail_to_pass_evidence_ref"),
        failures,
        "baseline_fail_to_pass_evidence_ref",
    )
    baseline_p2p_path = _inspect_artifact_ref(
        run_root,
        entry.get("pass_to_pass_baseline_evidence_ref"),
        failures,
        "pass_to_pass_baseline_evidence_ref",
    )
    gold_path = _inspect_artifact_ref(
        run_root,
        entry.get("gold_patch_passing_evidence_ref"),
        failures,
        "gold_patch_passing_evidence_ref",
    )
    final_path = _inspect_artifact_ref(
        run_root,
        entry.get("model_final_verifier_result_ref"),
        failures,
        "model_final_verifier_result_ref",
    )
    if env_path is not None:
        _inspect_environment_spec(env_path, task_id, failures)
    plan = {}
    if plan_path is not None:
        plan = _inspect_verifier_plan(plan_path, task_id, failures)
    selector_cache = {}
    if selector_path is not None:
        selector_cache = _inspect_selector_cache(selector_path, task_id, failures)
    if baseline_f2p_path is not None:
        baseline_f2p = _read_json_for_inspect(baseline_f2p_path, failures)
        _inspect_evaluator_only_output_refs(baseline_f2p, task_id, failures)
        if baseline_f2p.get("exit_code") == 0:
            failures.append(f"baseline fail-to-pass 必须失败：{task_id}")
    if baseline_p2p_path is not None:
        baseline_p2p = _read_json_for_inspect(baseline_p2p_path, failures)
        _inspect_evaluator_only_output_refs(baseline_p2p, task_id, failures)
        if baseline_p2p.get("exit_code") != 0:
            failures.append(f"baseline pass-to-pass 必须通过：{task_id}")
    if gold_path is not None:
        gold = _read_json_for_inspect(gold_path, failures)
        _inspect_evaluator_only_output_refs(gold, task_id, failures)
        if gold.get("fail_to_pass", {}).get("exit_code") != 0 or gold.get("pass_to_pass", {}).get("exit_code") != 0:
            failures.append(f"gold patch fail-to-pass/pass-to-pass 必须通过：{task_id}")
    if final_path is not None:
        final = _read_json_for_inspect(final_path, failures)
        _inspect_evaluator_only_output_refs(final, task_id, failures)
        if final.get("accepted") is not True:
            failures.append(f"model final verifier result 必须 accepted：{task_id}")
    if assert_complete and not failures and plan and selector_cache:
        _rerun_plan_commands(run_root, entry, plan, selector_cache, failures)


def _inspect_environment_spec(path: Path, task_id: str | None, failures: list[str]) -> None:
    payload = _read_json_for_inspect(path, failures)
    try:
        SweBenchLikeEnvironmentSpec.model_validate(payload)
    except ValidationError as exc:
        failures.append(f"SweBenchLikeEnvironmentSpec 无效：{task_id}:{exc}")
    if payload.get("hidden_verifier_command_visible_to_model"):
        failures.append(f"hidden verifier command 不能模型可见：{task_id}")
    if not payload.get("execution_image") or not payload.get("setup_commands_ref"):
        failures.append(f"environment spec 缺少 execution image 或 setup commands：{task_id}")
    environment_setup_commit = payload.get("environment_setup_commit")
    if not isinstance(environment_setup_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", environment_setup_commit):
        failures.append(f"environment_setup_commit 必须记录真实 40 位提交号：{task_id}")


def _inspect_verifier_plan(path: Path, task_id: str | None, failures: list[str]) -> dict[str, Any]:
    payload = _read_json_for_inspect(path, failures)
    try:
        SweBenchLikeVerifierPlan.model_validate(payload)
    except ValidationError as exc:
        failures.append(f"SweBenchLikeVerifierPlan 无效：{task_id}:{exc}")
    conversion_rule = payload.get(
        "selector_conversion_rule",
        "path_node_id_passthrough_or_bare_function_to_patch_file",
    )
    if conversion_rule != "path_node_id_passthrough_or_bare_function_to_patch_file":
        failures.append(f"selector conversion rule 不完整：{task_id}")
    if not payload.get("fail_to_pass_command") or not payload.get("pass_to_pass_command"):
        failures.append(f"verifier plan 缺少 F2P/P2P command：{task_id}")
    return payload


def _inspect_selector_cache(path: Path, task_id: str | None, failures: list[str]) -> dict[str, Any]:
    payload = _read_json_for_inspect(path, failures)
    if payload.get("schema_version") != SELECTOR_CACHE_VERSION:
        failures.append(f"selector cache schema_version 不匹配：{task_id}")
    if not payload.get("expanded_fail_to_pass"):
        failures.append(f"selector cache expanded_fail_to_pass 为空：{task_id}")
    if not payload.get("expanded_pass_to_pass"):
        failures.append(f"selector cache expanded_pass_to_pass 为空：{task_id}")
    if task_id == "sympy__sympy-24909":
        expected = "sympy/physics/units/tests/test_prefixes.py::test_prefix_operations"
        if expected not in payload.get("expanded_fail_to_pass", []):
            failures.append("sympy__sympy-24909 必须覆盖裸函数名 selector 转换。")
    return payload


def _inspect_evaluator_only_output_refs(payload: Any, task_id: str | None, failures: list[str]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"stdout_ref", "stderr_ref"} and isinstance(value, dict):
                if value.get("redaction_status") != "evaluator_only":
                    failures.append(f"hidden verifier output ref 必须 evaluator_only：{task_id}:{key}")
            else:
                _inspect_evaluator_only_output_refs(value, task_id, failures)
    elif isinstance(payload, list):
        for item in payload:
            _inspect_evaluator_only_output_refs(item, task_id, failures)


def _rerun_plan_commands(
    run_root: Path,
    entry: dict[str, Any],
    plan: dict[str, Any],
    selector_cache: dict[str, Any],
    failures: list[str],
) -> None:
    task_id = entry["task_id"]
    env_path = _resolve_ref(run_root, entry["environment_spec_ref"]["relative_path"])
    environment_spec = _read_json(env_path)
    environment = {
        "execution_image": environment_spec["execution_image"],
        "test_timeout_sec": plan["per_command_timeout_sec"],
        "pythonpath": "src" if entry.get("repo") == "pytest-dev/pytest" else ".",
    }
    rerun_root = run_root / "inspect_rerun" / task_id
    baseline = _resolve_ref(run_root, entry["baseline_workspace_ref"]["relative_path"])
    gold = _resolve_ref(run_root, entry["gold_workspace_ref"]["relative_path"])
    final = _resolve_ref(run_root, entry["model_final_workspace_ref"]["relative_path"])
    checks = [
        ("baseline", "fail_to_pass", baseline, plan["fail_to_pass_command"], False),
        ("baseline", "pass_to_pass", baseline, plan["pass_to_pass_command"], True),
        ("gold", "fail_to_pass", gold, plan["fail_to_pass_command"], True),
        ("gold", "pass_to_pass", gold, plan["pass_to_pass_command"], True),
        ("model_final", "fail_to_pass", final, plan["fail_to_pass_command"], True),
        ("model_final", "pass_to_pass", final, plan["pass_to_pass_command"], True),
    ]
    for phase, suite, workspace, command, should_pass in checks:
        result = _run_docker_shell(
            workspace=workspace,
            task_root=rerun_root,
            image=environment["execution_image"],
            command=_test_shell(command, environment),
            timeout_sec=environment["test_timeout_sec"],
            label=f"{task_id}_{phase}_{suite}_inspect",
            network="none",
            pythonpath=environment["pythonpath"],
        )
        if should_pass and result["exit_code"] != 0:
            failures.append(f"inspect rerun command 未通过：{task_id}:{phase}:{suite}")
        if not should_pass and result["exit_code"] == 0:
            failures.append(f"inspect rerun baseline fail-to-pass 意外通过：{task_id}")
    if not selector_cache.get("expanded_fail_to_pass") or not selector_cache.get("expanded_pass_to_pass"):
        failures.append(f"inspect rerun selector cache 为空：{task_id}")


def _run_docker_shell(
    *,
    workspace: Path,
    task_root: Path,
    image: str,
    command: str,
    timeout_sec: int,
    label: str,
    network: str,
    pythonpath: str | None,
) -> dict[str, Any]:
    started_at = _utc_timestamp()
    output_root = task_root / "command_outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    stdout_path = output_root / f"{_safe_label(label)}.stdout.txt"
    stderr_path = output_root / f"{_safe_label(label)}.stderr.txt"
    docker_args = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
    ]
    if network == "none":
        docker_args.extend(["--network", "none"])
    docker_args.extend(
        [
            "-v",
            f"{workspace.resolve()}:/workspace",
            "-w",
            "/workspace",
            image,
            "sh",
            "-lc",
            command,
        ]
    )
    try:
        completed = subprocess.run(
            docker_args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            check=False,
        )
        exit_code = completed.returncode
        timeout = False
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        timeout = True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    finished_at = _utc_timestamp()
    stdout_ref = _artifact_ref(
        stdout_path,
        artifact_id=f"{label}_stdout",
        kind="text",
        base_dir=task_root,
        redaction_status="evaluator_only",
    )
    stderr_ref = _artifact_ref(
        stderr_path,
        artifact_id=f"{label}_stderr",
        kind="text",
        base_dir=task_root,
        redaction_status="evaluator_only",
    )
    return {
        "schema_version": "repo_harness_swebench_like_container_execution_facts_v3_v0",
        "label": label,
        "command": command,
        "argv": _redacted_docker_argv(docker_args),
        "workspace_mount_status": "redacted",
        "image": image,
        "image_id": _docker_image_id(image),
        "requested_container_platform": "linux/amd64",
        "network_policy": "none" if network == "none" else "controlled_network_for_setup_only",
        "pythonpath": pythonpath,
        "exit_code": exit_code,
        "timeout": timeout,
        "timeout_sec": timeout_sec,
        "started_at": started_at,
        "finished_at": finished_at,
        "stdout_ref": stdout_ref.model_dump(mode="json"),
        "stderr_ref": stderr_ref.model_dump(mode="json"),
    }


def _apply_patch(
    *,
    workspace: Path,
    patch_path: Path,
    task_root: Path,
    label: str,
    execute: bool,
) -> dict[str, Any]:
    if not execute:
        return {"schema_version": PATCH_APPLY_FACTS_VERSION, "status": "skipped"}
    started_at = _utc_timestamp()
    output_root = task_root / "patch_apply_outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", patch_path.resolve().as_posix()],
        cwd=workspace,
        env=_patch_apply_environment(workspace),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    stdout_path = output_root / f"{label}.stdout.txt"
    stderr_path = output_root / f"{label}.stderr.txt"
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    return {
        "schema_version": PATCH_APPLY_FACTS_VERSION,
        "label": label,
        "status": "passed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "patch_sha256": compute_file_sha256(patch_path),
        "workspace_sha256_after": compute_source_tree_hash(workspace),
        "started_at": started_at,
        "finished_at": _utc_timestamp(),
        "stdout_ref": _artifact_ref(
            stdout_path,
            artifact_id=f"{label}_stdout",
            kind="text",
            base_dir=task_root,
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
        "stderr_ref": _artifact_ref(
            stderr_path,
            artifact_id=f"{label}_stderr",
            kind="text",
            base_dir=task_root,
            redaction_status="evaluator_only",
        ).model_dump(mode="json"),
    }


def _test_shell(command: str, environment: dict[str, Any]) -> str:
    exports = ""
    if environment.get("pythonpath"):
        exports = f"export PYTHONPATH={shlex.quote(environment['pythonpath'])} && "
    return (
        'export VIRTUAL_ENV="$PWD/.v3_verifier_venv" '
        '&& export PATH="$VIRTUAL_ENV/bin:$PATH" '
        f"&& {exports}{command}"
    )


def _pytest_command(selectors: list[str]) -> str:
    if any(_selector_has_param_with_node_separator(selector) for selector in selectors):
        files: list[str] = []
        functions: list[str] = []
        for selector in selectors:
            path, rest = _split_pytest_selector(selector)
            if path not in files:
                files.append(path)
            function = rest.split("[", 1)[0].split("::")[-1]
            if function not in functions:
                functions.append(function)
        if len(files) == 1 and functions:
            expression = " or ".join(functions)
            return "python -m pytest -q " + shlex.quote(files[0]) + " -k " + shlex.quote(expression)
    return "python -m pytest -q " + " ".join(shlex.quote(selector) for selector in selectors)


def _selector_has_param_with_node_separator(selector: str) -> bool:
    return bool(re.search(r"\[[^\]]*::[^\]]*\]$", selector))


def _split_pytest_selector(selector: str) -> tuple[str, str]:
    marker = ".py::"
    if marker not in selector:
        raise ConfigError(f"pytest selector 缺少文件路径：{selector}")
    path, rest = selector.split(marker, 1)
    return path + ".py", rest


def _suite_status(exit_code: int | None, timeout: bool) -> str:
    if timeout:
        return "timeout"
    if exit_code == 0:
        return "passed"
    if exit_code == 1:
        return "failed"
    return "error"


def _parse_selector_json(value: str, instance_id: str, field: str) -> list[str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{field} selector JSON 无效：{instance_id}") from exc
    if not isinstance(payload, list) or not payload:
        raise ConfigError(f"{field} selector 列表为空：{instance_id}")
    if not all(isinstance(item, str) and item for item in payload):
        raise ConfigError(f"{field} selector 必须是非空字符串：{instance_id}")
    return payload


def _patched_test_files(test_patch: str) -> list[str]:
    paths: list[str] = []
    for line in test_patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :].strip()
            if "test" in Path(path).name or "/tests/" in path or path.startswith("testing/"):
                paths.append(path)
    return sorted(set(paths))


def _copy_ref_from_source_root(*, source_root: Path, ref_payload: dict[str, Any], destination: Path) -> Path:
    source_path = _resolve_ref(source_root, ref_payload["relative_path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)
    return destination


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__", "*.pyc"),
    )


def _patch_apply_environment(workspace: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CEILING_DIRECTORIES"] = workspace.parent.resolve().as_posix()
    return env


def _redacted_docker_argv(argv: list[str]) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            redacted.append("<workspace-mount:redacted>" if ":/workspace" in arg else arg)
            skip_next = False
            continue
        redacted.append(arg)
        if arg == "-v":
            skip_next = True
    return redacted


def _docker_image_id(image: str) -> str | None:
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _safe_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _read_ref_text(task_root: Path, ref_payload: dict[str, Any] | None) -> str:
    if not isinstance(ref_payload, dict):
        return ""
    path = task_root / ref_payload["relative_path"]
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _inspect_artifact_ref(
    run_root: Path,
    value: Any,
    failures: list[str],
    label: str,
) -> Path | None:
    if not isinstance(value, dict):
        failures.append(f"{label} 缺少 ArtifactRef。")
        return None
    try:
        ref = ArtifactRef.model_validate(value)
    except ValidationError as exc:
        failures.append(f"{label} ArtifactRef 无效：{exc}")
        return None
    path = _resolve_ref(run_root, ref.relative_path)
    if not path.exists():
        failures.append(f"{label} 引用路径不存在：{ref.relative_path}")
        return None
    if path.is_dir():
        actual_sha = compute_source_tree_hash(path)
        actual_size = 0
    else:
        actual_sha = compute_file_sha256(path)
        actual_size = path.stat().st_size
    if actual_sha != ref.sha256:
        failures.append(f"{label} sha256 不匹配：{ref.relative_path}")
    if actual_size != ref.size_bytes:
        failures.append(f"{label} size_bytes 不匹配：{ref.relative_path}")
    return path


def _resolve_ref(run_root: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ConfigError(f"ArtifactRef 不能使用绝对路径：{relative_path}")
    for base in (run_root, Path.cwd()):
        path = base / candidate
        if path.exists():
            return path
    return run_root / relative_path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"JSON 文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 文件无效：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"JSON 顶层必须是 object：{path}")
    return payload


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        return _read_json(path)
    except ConfigError as exc:
        failures.append(str(exc))
        return {}


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"YAML 文件不存在：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"YAML 顶层必须是 object：{path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ConfigError(f"JSONL 文件不存在：{path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"JSONL 第 {line_number} 行无效：{path}") from exc
        if not isinstance(row, dict):
            raise ConfigError(f"JSONL 第 {line_number} 行必须是 object：{path}")
        rows.append(row)
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_ref(
    path: Path,
    *,
    artifact_id: str,
    kind: str,
    base_dir: Path | None = None,
    redaction_status: str = "not_required",
) -> ArtifactRef:
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
    )


def _relative_path(path: Path, base_dir: Path | None = None) -> str:
    resolved = path.resolve()
    candidates = [base_dir.resolve()] if base_dir is not None else []
    candidates.append(Path.cwd().resolve())
    for base in candidates:
        try:
            return resolved.relative_to(base).as_posix()
        except ValueError:
            continue
    return resolved.as_posix()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _inspect_result(run_root: Path, failures: list[str], assert_complete: bool) -> str:
    payload = {
        "schema_version": SWEBENCH_LIKE_INSPECT_VERSION,
        "run_dir": str(run_root),
        "status": "failed" if failures else "passed",
        "checks": [] if failures else ["swebench_like=complete"],
        "failures": failures,
    }
    if failures and assert_complete:
        raise ConfigError("SWE-Bench-like 检查失败：" + "; ".join(failures))
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
