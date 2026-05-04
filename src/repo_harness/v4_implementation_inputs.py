"""V4 stage 0 implementation input freeze builder and inspector."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ALLOWLIST_POLICY_VERSION,
    V4_BASELINE_CHECK_REPORT_VERSION,
    V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
    V4_FEASIBILITY_INPUT_BINDING_VERSION,
    V4_IMPLEMENTATION_INPUT_AUDIT_REPORT_VERSION,
    V4_IMPLEMENTATION_INPUT_MANIFEST_VERSION,
    V4_VISIBILITY_POLICY_VERSION,
)
from repo_harness.v4_visibility import V4ContaminationDenylist, v4_contamination_denylist_sha256
from repo_harness.workspace.source_hash import compute_source_tree_hash


V4_REQUIRED_DOCS = (
    "docs/v4/scope-and-roadmap.md",
    "docs/v4/implementation-plan.md",
    "docs/v4/pr-issue-task-source-plan.md",
    "docs/v4/swe-task-feasibility-experiment-plan.md",
    "docs/v4/review/scope-review.md",
    "docs/v4/review/implementation-plan-review.md",
    "docs/v4/review/pr-issue-task-source-plan-review.md",
)

V4_STAGE0_OUTPUTS = (
    "v4_baseline_check_report.json",
    "v4_feasibility_input_binding.json",
    "v4_implementation_input_audit_report.json",
    "v4_implementation_input_manifest.json",
)

PR_ISSUE_FREEZE_READY_CANDIDATES = (
    ("go_cobra_2356", "v4_go_cobra_completion_args"),
    ("go_testify_1531", "v4_go_testify_numeric_equal_values"),
    ("go_toml_1041", "v4_go_toml_error_position"),
    ("py_click_3208", "v4_py_click_help_hint_shadowing"),
    ("py_pluggy_646", "v4_py_pluggy_multi_hook_unregister"),
    ("js_execa_1176", "v4_js_execa_escaped_template_newlines"),
    ("js_yargs_2332", "v4_js_yargs_completion_parser_config"),
    ("rust_fd_1805", "v4_rust_fd_exec_null_separator"),
)

PUBLIC_SWEBENCH_LIKE_CANDIDATES = (
    "django__django-11283",
    "astropy__astropy-14182",
    "sphinx-doc__sphinx-7686",
    "matplotlib__matplotlib-18869",
    "scikit-learn__scikit-learn-10297",
)


def build_v4_implementation_inputs(
    *,
    pr_issue_run: str | Path,
    public_swebench_run: str | Path,
    output_dir: str | Path,
    v2_acceptance: str | Path,
    v3_acceptance: str | Path,
    v3_acceptance_bundle: str | Path,
    baseline_commit: str = "f38cb93",
    v3_closure_commit: str = "17b1b95",
    run_live_baseline_checks: bool = False,
    fail_if_output_exists: bool = False,
) -> Path:
    """Freeze V4 stage 0 implementation inputs into explicit manifests."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in V4_STAGE0_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError(
                "V4 stage 0 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    pr_run_path = Path(pr_issue_run)
    public_run_path = Path(public_swebench_run)
    baseline_report_path = output_path / "v4_baseline_check_report.json"
    binding_path = output_path / "v4_feasibility_input_binding.json"
    audit_report_path = output_path / "v4_implementation_input_audit_report.json"
    manifest_path = output_path / "v4_implementation_input_manifest.json"

    baseline_report = _build_baseline_check_report(
        baseline_commit=baseline_commit,
        v3_closure_commit=v3_closure_commit,
        v2_acceptance=Path(v2_acceptance),
        v3_acceptance=Path(v3_acceptance),
        v3_acceptance_bundle=Path(v3_acceptance_bundle),
        run_live_checks=run_live_baseline_checks,
    )

    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(baseline_report_path, baseline_report)

    binding = _build_feasibility_binding(
        pr_issue_run=pr_run_path,
        public_swebench_run=public_run_path,
    )
    _write_json(binding_path, binding)

    preliminary_manifest_payload = _implementation_manifest_payload(
        baseline_commit=baseline_commit,
        v3_closure_commit=v3_closure_commit,
        baseline_report_path=baseline_report_path,
        binding_path=binding_path,
        audit_report_path=audit_report_path,
        pr_issue_run=pr_run_path,
        public_swebench_run=public_run_path,
        include_audit_ref=False,
    )
    audit_report = _build_audit_report(manifest_payload=preliminary_manifest_payload, binding=binding)
    _write_json(audit_report_path, audit_report)
    manifest_payload = _implementation_manifest_payload(
        baseline_commit=baseline_commit,
        v3_closure_commit=v3_closure_commit,
        baseline_report_path=baseline_report_path,
        binding_path=binding_path,
        audit_report_path=audit_report_path,
        pr_issue_run=pr_run_path,
        public_swebench_run=public_run_path,
        include_audit_ref=True,
    )
    _write_json(manifest_path, manifest_payload)
    inspect_v4_implementation_inputs(manifest_path, assert_complete=True)
    return manifest_path


def inspect_v4_implementation_inputs(
    manifest: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """Read-only inspection for V4 stage 0 implementation input manifests."""

    manifest_path = Path(manifest)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if payload.get("schema_version") != V4_IMPLEMENTATION_INPUT_MANIFEST_VERSION:
        failures.append("v4 implementation input manifest schema_version 不匹配。")
    if payload.get("visibility_policy_version") != V4_VISIBILITY_POLICY_VERSION:
        failures.append("visibility_policy_version 不匹配。")
    if payload.get("contamination_denylist_version") != V4_CONTAMINATION_DENYLIST_VERSION:
        failures.append("contamination_denylist_version 不匹配。")
    if payload.get("contamination_denylist_sha256") != v4_contamination_denylist_sha256():
        failures.append("contamination_denylist_sha256 不匹配。")
    if payload.get("allowlist_policy_version") != V4_ALLOWLIST_POLICY_VERSION:
        failures.append("allowlist_policy_version 不匹配。")
    if payload.get("accepted_counting_allowed") is not False:
        failures.append("Stage 0 implementation inputs 不能允许 accepted counting。")

    try:
        _scan_safe_manifest_payload(payload)
    except ConfigError as exc:
        failures.append(str(exc))

    baseline_report = _inspect_bound_ref(payload.get("baseline_check_report_ref"), failures)
    binding = _inspect_bound_ref(payload.get("feasibility_input_binding_ref"), failures)
    audit_report = _inspect_bound_ref(payload.get("implementation_input_audit_report_ref"), failures)

    if baseline_report:
        _inspect_baseline_report(baseline_report, failures)
    if binding:
        _inspect_feasibility_binding(binding, failures)
    if audit_report:
        _inspect_audit_report(audit_report, failures)

    for doc in V4_REQUIRED_DOCS:
        if not Path(doc).exists():
            failures.append(f"V4 必需文档缺失：{doc}")
    if payload.get("required_docs") and sorted(payload["required_docs"]) != sorted(V4_REQUIRED_DOCS):
        failures.append("required_docs 与 V4 stage 0 文档清单不一致。")

    lines = [
        f"V4 implementation input manifest: {manifest_path}",
        f"Baseline commit: {payload.get('baseline_commit')}",
        f"V3 closure commit: {payload.get('v3_closure_commit')}",
        f"PR / issue candidates: {payload.get('candidate_summary', {}).get('pr_issue_freeze_ready_count', 0)}",
        f"Public SWE-Bench-like candidates: {payload.get('candidate_summary', {}).get('public_swebench_like_candidate_count', 0)}",
        "Accepted counting allowed: false",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V4 implementation inputs: complete")
    lines.append("Inspect V4 implementation inputs: passed")
    return "\n".join(lines)


def _build_baseline_check_report(
    *,
    baseline_commit: str,
    v3_closure_commit: str,
    v2_acceptance: Path,
    v3_acceptance: Path,
    v3_acceptance_bundle: Path,
    run_live_checks: bool,
) -> dict[str, Any]:
    commands = _baseline_commands(
        baseline_commit=baseline_commit,
        v3_closure_commit=v3_closure_commit,
        v2_acceptance=v2_acceptance,
        v3_acceptance=v3_acceptance,
        v3_acceptance_bundle=v3_acceptance_bundle,
    )
    command_results = [
        _run_command(command) if run_live_checks else _skipped_command(command)
        for command in commands
    ]
    named = {result["command_name"]: result for result in command_results}
    docker_amd64 = named.get("docker_run_alpine_amd64_uname_m", {})
    architecture_risk = None
    if docker_amd64.get("exit_code") not in (0, None):
        architecture_risk = {
            "risk": "architecture_compatibility_risk",
            "details": "linux/amd64 Docker probe failed during V4 baseline checks.",
        }
    if docker_amd64.get("stdout_summary", {}).get("first_line") == "x86_64":
        architecture_risk = None

    return {
        "schema_version": V4_BASELINE_CHECK_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "baseline_commit": baseline_commit,
        "v3_closure_commit": v3_closure_commit,
        "live_checks_run": run_live_checks,
        "required_commands": [command["command_name"] for command in commands],
        "command_results": command_results,
        "baseline_status": {
            "v4_baseline_commit_is_ancestor": _command_status(named.get("git_merge_base_v4_baseline_head")),
            "v3_closure_commit_is_ancestor": _command_status(named.get("git_merge_base_v3_closure_head")),
            "docs_v4_clean_before_stage0_outputs": _docs_v4_clean_status(named),
            "compileall_src": _command_status(named.get("compileall_src")),
            "pytest": _command_status(named.get("pytest_q")),
            "v2_acceptance": _command_status(named.get("inspect_v2_acceptance")),
            "v3_acceptance": _command_status(named.get("inspect_v3_acceptance")),
            "v3_acceptance_bundle": _command_status(named.get("inspect_v3_acceptance_bundle")),
            "docker_amd64_probe": _command_status(docker_amd64),
        },
        "architecture_compatibility_risk": architecture_risk,
        "unrelated_dirty_worktree_policy": "record_only_do_not_revert_or_commit_unrelated_changes",
    }


def _baseline_commands(
    *,
    baseline_commit: str,
    v3_closure_commit: str,
    v2_acceptance: Path,
    v3_acceptance: Path,
    v3_acceptance_bundle: Path,
) -> list[dict[str, Any]]:
    py = sys.executable
    return [
        {"command_name": "pwd", "argv": ["pwd"]},
        {"command_name": "git_status_short", "argv": ["git", "status", "--short"]},
        {"command_name": "git_log_1_oneline", "argv": ["git", "log", "-1", "--oneline"]},
        {"command_name": "git_status_docs_v4", "argv": ["git", "status", "--short", "--", "docs/v4"]},
        {"command_name": "git_diff_docs_v4", "argv": ["git", "diff", "--name-status", "--", "docs/v4"]},
        {"command_name": "git_ls_tree_docs_v4", "argv": ["git", "ls-tree", "-r", "--name-only", baseline_commit, "docs/v4"]},
        {"command_name": "git_merge_base_v4_baseline_head", "argv": ["git", "merge-base", "--is-ancestor", baseline_commit, "HEAD"]},
        {"command_name": "git_merge_base_v3_closure_head", "argv": ["git", "merge-base", "--is-ancestor", v3_closure_commit, "HEAD"]},
        {"command_name": "compileall_src", "argv": [py, "-m", "compileall", "src"]},
        {"command_name": "pytest_q", "argv": [py, "-m", "pytest", "-q"]},
        {"command_name": "inspect_v2_acceptance", "argv": ["repo-harness", "inspect-v2-acceptance", v2_acceptance.as_posix(), "--assert-complete"]},
        {"command_name": "inspect_v3_acceptance", "argv": ["repo-harness", "inspect-v3-acceptance", v3_acceptance.as_posix(), "--assert-complete"]},
        {"command_name": "inspect_v3_acceptance_bundle", "argv": ["repo-harness", "inspect-acceptance-bundle", v3_acceptance_bundle.as_posix(), "--assert-immutable"]},
        {"command_name": "docker_version", "argv": ["docker", "version"]},
        {"command_name": "docker_context_show", "argv": ["docker", "context", "show"]},
        {"command_name": "docker_info", "argv": ["docker", "info"]},
        {"command_name": "docker_info_memtotal", "argv": ["docker", "info", "--format", "{{json .MemTotal}}"]},
        {"command_name": "docker_run_hello_world", "argv": ["docker", "run", "--rm", "hello-world"]},
        {"command_name": "docker_run_alpine_uname_m", "argv": ["docker", "run", "--rm", "alpine:3.20", "uname", "-m"]},
        {"command_name": "docker_run_alpine_meminfo", "argv": ["docker", "run", "--rm", "alpine:3.20", "sh", "-lc", "grep MemTotal /proc/meminfo"]},
        {"command_name": "docker_run_alpine_amd64_uname_m", "argv": ["docker", "run", "--rm", "--platform", "linux/amd64", "alpine:3.20", "uname", "-m"]},
    ]


def _run_command(command: dict[str, Any]) -> dict[str, Any]:
    started_at = _utc_timestamp()
    env = os.environ.copy()
    env["PATH"] = f"{Path('.venv/bin').resolve()}{os.pathsep}{env.get('PATH', '')}"
    completed = subprocess.run(
        command["argv"],
        cwd=Path.cwd(),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command["command_name"],
        "argv": command["argv"],
        "cwd": ".",
        "input_paths": _known_input_paths(command["argv"]),
        "input_sha256": _known_input_hashes(command["argv"]),
        "output_paths": [],
        "output_sha256": {
            "stdout": _sha256_text(completed.stdout),
            "stderr": _sha256_text(completed.stderr),
        },
        "exit_code": completed.returncode,
        "tool_or_cli_version": f"repo-harness {__version__}",
        "started_at": started_at,
        "finished_at": _utc_timestamp(),
        "structured_skip_reason": None,
        "structured_failure_reason": None if completed.returncode == 0 else "command_exit_nonzero",
        "stdout_summary": _safe_output_summary(completed.stdout),
        "stderr_summary": _safe_output_summary(completed.stderr),
    }


def _skipped_command(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command["command_name"],
        "argv": command["argv"],
        "cwd": ".",
        "input_paths": _known_input_paths(command["argv"]),
        "input_sha256": _known_input_hashes(command["argv"]),
        "output_paths": [],
        "output_sha256": {},
        "exit_code": None,
        "tool_or_cli_version": f"repo-harness {__version__}",
        "started_at": _utc_timestamp(),
        "finished_at": _utc_timestamp(),
        "structured_skip_reason": "not_run_by_builder",
        "structured_failure_reason": None,
        "stdout_summary": {},
        "stderr_summary": {},
    }


def _build_feasibility_binding(
    *,
    pr_issue_run: Path,
    public_swebench_run: Path,
) -> dict[str, Any]:
    pr_freeze = pr_issue_run / "manifests/pr_issue_task_freeze_readiness_report.json"
    pr_adapter = pr_issue_run / "manifests/adapter_visible_task_freeze_manifest.json"
    pr_docker = pr_issue_run / "manifests/docker_feasibility_summary_report.json"
    pr_flaky = pr_issue_run / "manifests/flaky_probe_report.json"
    pr_boundary = pr_issue_run / "manifests/training_export_boundary_report.json"
    pr_scan = pr_issue_run / "manifests/adapter_visible_denylist_scan_report.json"
    pr_source = pr_issue_run / "manifests/source_archive_manifest.json"

    public_probe_manifest = public_swebench_run / "manifests/public_swebench_initial_probe_result_manifest.json"
    public_probe_result = public_swebench_run / "baseline/public_swebench_initial_probe_result.json"
    public_freeze = public_swebench_run / "freeze/public_swebench_initial_freeze_readiness_report.json"
    public_selection = public_swebench_run / "inventory/public_swebench_initial_probe_selection.json"

    binding = {
        "schema_version": V4_FEASIBILITY_INPUT_BINDING_VERSION,
        "generated_at": _utc_timestamp(),
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "accepted_counting_allowed": False,
        "accepted_counting_reason": (
            "Stage 0 only freezes implementation inputs. Feasibility candidates are not "
            "V4 accepted / auditable task definitions until later adapter integration, "
            "task validity inspect, run selection, acceptance inputs, and final V4 acceptance."
        ),
        "sources": [
            {
                "source_id": "v4_pr_issue_feasibility",
                "source_kind": "auditable_pr_issue_feasibility_run",
                "run_path": _rel(pr_issue_run),
                "run_path_exists": pr_issue_run.exists(),
                "primary_input_manifest_ref": _file_ref(pr_freeze, "pr_issue_freeze_readiness_report"),
                "manifest_refs": [
                    _file_ref(pr_freeze, "pr_issue_freeze_readiness_report"),
                    _file_ref(pr_adapter, "adapter_visible_task_freeze_manifest"),
                    _file_ref(pr_docker, "docker_feasibility_summary_report"),
                    _file_ref(pr_flaky, "flaky_probe_report"),
                    _file_ref(pr_boundary, "training_export_boundary_report"),
                    _file_ref(pr_scan, "adapter_visible_denylist_scan_report"),
                    _file_ref(pr_source, "source_archive_manifest"),
                ],
                "adapter_visible_manifest_ref": _file_ref(pr_adapter, "adapter_visible_task_freeze_manifest"),
                "audit_only_historical_artifacts": [
                    {
                        "path": _rel(pr_issue_run / "manifests/docker_feasibility_probe_report.partial.json"),
                        "downgrade_reason": "partial historical probe artifact; upper summary manifest is the counting gate",
                    },
                    {
                        "path": _rel(pr_issue_run / "manifests/flaky_probe_report.partial.json"),
                        "downgrade_reason": "partial historical probe artifact; upper summary manifest is the counting gate",
                    },
                ],
                "count_summary": _pr_issue_count_summary(pr_freeze),
            },
            {
                "source_id": "v4_public_swebench_like_feasibility",
                "source_kind": "public_swebench_like_feasibility_run",
                "run_path": _rel(public_swebench_run),
                "run_path_exists": public_swebench_run.exists(),
                "primary_input_manifest_ref": _file_ref(public_freeze, "public_swebench_freeze_readiness_report"),
                "manifest_refs": [
                    _file_ref(public_probe_manifest, "public_swebench_initial_probe_result_manifest"),
                    _file_ref(public_probe_result, "public_swebench_safe_probe_result_summary"),
                    _file_ref(public_freeze, "public_swebench_freeze_readiness_report"),
                    _file_ref(public_selection, "public_swebench_selection_summary_audit_only"),
                ],
                "audit_only_selector_or_patch_metadata_refs": [
                    _file_ref(public_selection, "public_swebench_selection_summary_audit_only")
                ],
                "count_summary": _public_swe_count_summary(public_freeze),
            },
        ],
    }
    return binding


def _implementation_manifest_payload(
    *,
    baseline_commit: str,
    v3_closure_commit: str,
    baseline_report_path: Path,
    binding_path: Path,
    audit_report_path: Path,
    pr_issue_run: Path,
    public_swebench_run: Path,
    include_audit_ref: bool,
) -> dict[str, Any]:
    payload = {
        "schema_version": V4_IMPLEMENTATION_INPUT_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "implementation_stage": "stage_0_baseline_confirmation_and_input_freeze",
        "baseline_commit": baseline_commit,
        "v3_closure_commit": v3_closure_commit,
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "accepted_counting_allowed": False,
        "accepted_counting_reason": "Implementation inputs are audit-only stage 0 evidence, not final accepted task definitions.",
        "required_docs": list(V4_REQUIRED_DOCS),
        "baseline_check_report_ref": _file_ref(baseline_report_path, "v4_baseline_check_report"),
        "feasibility_input_binding_ref": _file_ref(binding_path, "v4_feasibility_input_binding"),
        "input_run_roots": [
            {
                "source_id": "v4_pr_issue_feasibility",
                "path": _rel(pr_issue_run),
                "model_visible": False,
                "accepted_counting_allowed": False,
            },
            {
                "source_id": "v4_public_swebench_like_feasibility",
                "path": _rel(public_swebench_run),
                "model_visible": False,
                "accepted_counting_allowed": False,
            },
        ],
        "candidate_summary": {
            "pr_issue_freeze_ready_count": len(PR_ISSUE_FREEZE_READY_CANDIDATES),
            "pr_issue_freeze_ready_candidates": [
                {"candidate_id": candidate_id, "adapter_visible_task_id": task_id}
                for candidate_id, task_id in PR_ISSUE_FREEZE_READY_CANDIDATES
            ],
            "public_swebench_like_candidate_count": len(PUBLIC_SWEBENCH_LIKE_CANDIDATES),
            "public_swebench_like_candidates": list(PUBLIC_SWEBENCH_LIKE_CANDIDATES),
        },
        "visibility_boundary": {
            "adapter_visible_input_policy": "sanitized public problem statement only",
            "private_evaluation_material_policy": "hash_and_ref_only_until_verifier_or_acceptance",
            "public_swebench_selection_summary_policy": "audit_only_not_model_visible",
            "candidate_solution_material_policy": "absent_from_manifest_text",
            "provider_response_text_policy": "absent_from_manifest_text",
            "verifier_output_text_policy": "absent_from_manifest_text",
        },
    }
    if include_audit_ref:
        payload["implementation_input_audit_report_ref"] = _file_ref(
            audit_report_path,
            "v4_implementation_input_audit_report",
        )
    return payload


def _build_audit_report(
    *,
    manifest_payload: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        _scan_safe_manifest_payload(manifest_payload)
    except ConfigError as exc:
        failures.append(str(exc))
    try:
        _inspect_feasibility_binding(binding, failures)
    except ConfigError as exc:
        failures.append(str(exc))
    return {
        "schema_version": V4_IMPLEMENTATION_INPUT_AUDIT_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "contamination_denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
        "contamination_denylist_sha256": v4_contamination_denylist_sha256(),
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "status": "passed" if not failures else "failed",
        "checks": [
            "implementation_manifest_contains_no_solution_or_provider_response_text",
            "adapter_visible_inputs_scanned_with_v4_denylist",
            "feasibility_counts_consistent_or_historical_artifacts_downgraded",
            "accepted_counting_disabled_for_stage0_inputs",
        ],
        "failures": failures,
    }


def _inspect_baseline_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != V4_BASELINE_CHECK_REPORT_VERSION:
        failures.append("v4_baseline_check_report schema_version 不匹配。")
    if payload.get("live_checks_run") is not True:
        failures.append("v4_baseline_check_report 必须来自 live baseline checks。")
    expected_commands = {
        command["command_name"]
        for command in _baseline_commands(
            baseline_commit=str(payload.get("baseline_commit") or "f38cb93"),
            v3_closure_commit=str(payload.get("v3_closure_commit") or "17b1b95"),
            v2_acceptance=Path("v2_acceptance_report.json"),
            v3_acceptance=Path("v3_acceptance_report.json"),
            v3_acceptance_bundle=Path("acceptance_bundle_manifest.json"),
        )
    }
    required_commands = set(payload.get("required_commands") or [])
    if required_commands != expected_commands:
        failures.append("v4_baseline_check_report required_commands 覆盖不完整。")
    result_commands = {
        result.get("command_name")
        for result in payload.get("command_results", [])
        if isinstance(result, dict)
    }
    missing_results = sorted(expected_commands.difference(result_commands))
    if missing_results:
        failures.append("v4_baseline_check_report 缺少 command_results：" + ", ".join(missing_results))
    status = payload.get("baseline_status", {})
    for key in (
        "v4_baseline_commit_is_ancestor",
        "v3_closure_commit_is_ancestor",
        "docs_v4_clean_before_stage0_outputs",
        "compileall_src",
        "pytest",
        "v2_acceptance",
        "v3_acceptance",
        "v3_acceptance_bundle",
        "docker_amd64_probe",
    ):
        if status.get(key) != "passed":
            failures.append(f"baseline check 未通过：{key}")
    if payload.get("architecture_compatibility_risk"):
        failures.append("linux/amd64 Docker probe 存在 architecture compatibility risk。")


def _inspect_feasibility_binding(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != V4_FEASIBILITY_INPUT_BINDING_VERSION:
        failures.append("v4_feasibility_input_binding schema_version 不匹配。")
    if payload.get("contamination_denylist_sha256") != v4_contamination_denylist_sha256():
        failures.append("v4_feasibility_input_binding contamination_denylist_sha256 不匹配。")
    if payload.get("accepted_counting_allowed") is not False:
        failures.append("feasibility binding 必须保持 accepted_counting_allowed=false。")
    sources = payload.get("sources", [])
    if not isinstance(sources, list) or len(sources) < 2:
        failures.append("feasibility binding 至少需要 PR / issue 和 public SWE-Bench-like 两类 source。")
        return
    for source in sources:
        run_path = Path(str(source.get("run_path", "")))
        if not run_path.exists():
            failures.append(f"feasibility run path 不存在：{run_path}")
        for ref in source.get("manifest_refs", []):
            _inspect_file_ref(ref, failures)
        if source.get("primary_input_manifest_ref"):
            primary_payload = _inspect_bound_ref(source["primary_input_manifest_ref"], failures)
            if primary_payload:
                _inspect_count_consistency(
                    source_id=str(source.get("source_id")),
                    payload=primary_payload,
                    failures=failures,
                    downgraded=False,
                )
        count_summary = source.get("count_summary")
        if not isinstance(count_summary, dict):
            failures.append(f"{source.get('source_id')} 缺少 count_summary。")
        if source.get("adapter_visible_manifest_ref"):
            adapter_manifest = _inspect_bound_ref(source["adapter_visible_manifest_ref"], failures)
            if adapter_manifest:
                _inspect_adapter_visible_manifest(
                    adapter_manifest=adapter_manifest,
                    run_path=run_path,
                    failures=failures,
                )


def _inspect_audit_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != V4_IMPLEMENTATION_INPUT_AUDIT_REPORT_VERSION:
        failures.append("v4_implementation_input_audit_report schema_version 不匹配。")
    if payload.get("contamination_denylist_sha256") != v4_contamination_denylist_sha256():
        failures.append("v4_implementation_input_audit_report contamination_denylist_sha256 不匹配。")
    if payload.get("status") != "passed":
        failures.append("v4_implementation_input_audit_report 未通过。")


def _inspect_count_consistency(
    *,
    source_id: str,
    payload: dict[str, Any],
    failures: list[str],
    downgraded: bool,
) -> None:
    if "candidate_rows" in payload:
        rows = payload.get("candidate_rows")
        if not isinstance(rows, list):
            failures.append(f"{source_id} candidate_rows 不是列表。")
            return
        candidate_count = payload.get("candidate_count")
        if candidate_count != len(rows):
            if not downgraded:
                failures.append(f"{source_id} candidate_count 与 candidate_rows 数量不一致。")
        if "freeze_ready_count" in payload:
            actual = sum(1 for row in rows if row.get("final_status") == "freeze_ready")
            if payload.get("freeze_ready_count") != actual and not downgraded:
                failures.append(f"{source_id} freeze_ready_count 与明细行不一致。")
        if "docker_probe_passed_count" in payload:
            actual = sum(1 for row in rows if row.get("docker_final_status") == "docker_probe_passed")
            if payload.get("docker_probe_passed_count") != actual and not downgraded:
                failures.append(f"{source_id} docker_probe_passed_count 与明细行不一致。")
    if "task_readiness" in payload:
        rows = payload.get("task_readiness")
        if not isinstance(rows, list):
            failures.append(f"{source_id} task_readiness 不是列表。")
            return
        if payload.get("candidate_count") != len(rows):
            failures.append(f"{source_id} candidate_count 与 task_readiness 数量不一致。")
        ready = sum(1 for row in rows if row.get("final_status") == "gold_patch_probe_resolved")
        if payload.get("freeze_ready_public_swebench_like_count") != ready:
            failures.append(f"{source_id} public SWE-Bench-like freeze-ready count 不一致。")


def _inspect_adapter_visible_manifest(
    *,
    adapter_manifest: dict[str, Any],
    run_path: Path,
    failures: list[str],
) -> None:
    records = adapter_manifest.get("records")
    if not isinstance(records, list):
        failures.append("adapter_visible_task_freeze_manifest.records 不是列表。")
        return
    if adapter_manifest.get("task_count") != len(records):
        failures.append("adapter_visible_task_freeze_manifest task_count 与 records 数量不一致。")
    denylist = V4ContaminationDenylist()
    for record in records:
        relative = record.get("adapter_visible_path")
        digest = record.get("adapter_visible_sha256")
        path = run_path / str(relative)
        if not path.exists():
            failures.append(f"adapter-visible input 不存在：{path}")
            continue
        if digest and sha256_file(path) != digest:
            failures.append(f"adapter-visible input sha256 不匹配：{path}")
        task_payload = _read_json_for_inspect(path, failures)
        scan = denylist.scan_payload(
            surface="adapter_visible_task_input",
            payload=task_payload,
            adapter_visible=True,
        )
        if not scan.clean:
            terms = ", ".join(sorted({finding.matched_term for finding in scan.findings}))
            failures.append(f"adapter-visible input 污染：{relative}: {terms}")


def _scan_safe_manifest_payload(payload: dict[str, Any]) -> None:
    scan = V4ContaminationDenylist().scan_payload(
        surface="implementation_input_manifest",
        payload=payload,
        adapter_visible=False,
    )
    if not scan.clean:
        matched = ", ".join(sorted({finding.matched_term for finding in scan.findings}))
        raise ConfigError("V4 implementation input manifest 含禁止原始材料：" + matched)


def _pr_issue_count_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    rows = payload.get("candidate_rows", [])
    return {
        "candidate_count": payload.get("candidate_count"),
        "detail_count": len(rows) if isinstance(rows, list) else None,
        "freeze_ready_count": payload.get("freeze_ready_count"),
        "accepted_counting_allowed": payload.get("accepted_counting_allowed"),
    }


def _public_swe_count_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    rows = payload.get("task_readiness", [])
    return {
        "candidate_count": payload.get("candidate_count"),
        "detail_count": len(rows) if isinstance(rows, list) else None,
        "freeze_ready_count": payload.get("freeze_ready_public_swebench_like_count"),
        "accepted_counting_allowed": False,
    }


def _command_status(result: dict[str, Any] | None) -> str:
    if not result:
        return "missing"
    if result.get("exit_code") == 0:
        return "passed"
    if result.get("structured_skip_reason"):
        return "skipped"
    return "failed"


def _docs_v4_clean_status(named: dict[str, dict[str, Any]]) -> str:
    status = named.get("git_status_docs_v4", {})
    diff = named.get("git_diff_docs_v4", {})
    if status.get("exit_code") == 0 and diff.get("exit_code") == 0:
        if not status.get("stdout_summary", {}).get("has_output") and not diff.get("stdout_summary", {}).get("has_output"):
            return "passed"
    if status.get("structured_skip_reason") or diff.get("structured_skip_reason"):
        return "skipped"
    return "failed"


def _safe_output_summary(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    first_line = lines[0].strip() if lines else None
    safe_first_line = None
    if first_line and not first_line.startswith("/Users/"):
        safe_first_line = first_line[:200]
    return {
        "has_output": bool(text),
        "line_count": len(lines),
        "first_line": safe_first_line,
    }


def _known_input_paths(argv: list[str]) -> list[str]:
    paths = [item for item in argv if item.endswith(".json") or item.endswith(".md")]
    return paths


def _known_input_hashes(argv: list[str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for raw in _known_input_paths(argv):
        path = Path(raw)
        if path.exists():
            output[_rel(path)] = _hash_path(path)
    return output


def _inspect_bound_ref(ref: Any, failures: list[str]) -> dict[str, Any]:
    if not isinstance(ref, dict):
        failures.append("绑定 ref 缺失或不是 object。")
        return {}
    path = _inspect_file_ref(ref, failures)
    if path is None:
        return {}
    return _read_json_for_inspect(path, failures)


def _inspect_file_ref(ref: Any, failures: list[str]) -> Path | None:
    if not isinstance(ref, dict):
        failures.append("文件 ref 不是 object。")
        return None
    raw = str(ref.get("path") or "")
    if not raw:
        failures.append("文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        failures.append(f"文件 ref 路径不存在：{raw}")
        return None
    expected_sha = ref.get("sha256")
    if expected_sha and _hash_path(path) != expected_sha:
        failures.append(f"文件 ref sha256 不匹配：{raw}")
    expected_size = ref.get("size_bytes")
    if expected_size is not None and not path.is_dir() and path.stat().st_size != expected_size:
        failures.append(f"文件 ref size_bytes 不匹配：{raw}")
    return path


def _file_ref(path: Path, category: str) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"输入路径不存在：{path}")
    return {
        "path": _rel(path),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "sha256": _hash_path(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
        "model_visible": False,
    }


def _hash_path(path: Path) -> str:
    return compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"JSON 文件不存在：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"JSON 顶层必须是 object：{path}")
    return payload


def _read_json_for_inspect(path: Path | None, failures: list[str]) -> dict[str, Any]:
    if path is None:
        failures.append("JSON 路径缺失。")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"JSON 文件不存在：{path}")
        return {}
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 文件无效：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
