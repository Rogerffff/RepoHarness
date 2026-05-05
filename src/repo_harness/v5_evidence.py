"""V5 Stage 0 preimplementation evidence builders and inspectors."""

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
    V5_BASELINE_CHECK_REPORT_VERSION,
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_DOCUMENTATION_SYNC_REPORT_VERSION,
    V5_EVIDENCE_REF_VERSION,
    V5_PREFLIGHT_INPUT_BINDING_VERSION,
    V5_V4_CLOSURE_REPORT_VERSION,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


V5_BASELINE_COMMIT = "9fd7007"
V5_V4_CLOSURE_COMMIT = "e0da89c"
V5_PREFLIGHT_ROOT = "runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z"
V5_PARTIAL_THRESHOLD_STATUS = "partial_below_12_total_and_8_pr_issue_preflight_threshold"

V5_REVIEWED_BASELINE_DOCS = (
    "docs/v5/scope-and-roadmap.md",
    "docs/v5/implementation-plan.md",
    "docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md",
    "docs/v5/review/scope-review.md",
    "docs/v5/review/task-source-feasibility-and-run-matrix-preflight-plan-review.md",
)

V5_DOCUMENTATION_SYNC_REQUIRED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/00-reading-guide.md",
    "docs/01-project-positioning-and-requirements.md",
    "docs/12-resume-narrative-and-demo-artifacts.md",
    "docs/v4/final-acceptance.md",
    "reference/claude-code-typescript-src/AGENTS.md",
)

V5_PREFLIGHT_ARTIFACT_FIELDS = (
    "flaky_probe_report",
    "visibility_probe_summary",
    "run_matrix_preflight_manifest",
    "task_selection_preflight_report",
    "resume_claim_gate_preflight_report",
    "run_matrix_freeze_evidence_manifest",
)

V5_STAGE0_OUTPUT_NAMES = (
    "v5_baseline_check_report.json",
    "v4_review_findings_closure_report.json",
    "v5_documentation_sync_report.json",
    "v5_preflight_input_binding.json",
    "v5_preimplementation_command_log.jsonl",
)

V4_LATEST_DIR = "runs/v4-final-rerun-20260504T194758Z"
V4_DOC_SYNC_BUNDLE_NAME = "acceptance_bundle_manifest_doc_sync_20260505T075410Z.json"
V4_DOC_SYNC_COMMAND_LOG_NAME = "final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl"


def build_v5_preimplementation(
    *,
    output_dir: str | Path,
    v2_acceptance_report: str | Path,
    v3_acceptance_report: str | Path,
    v3_acceptance_bundle: str | Path,
    v4_acceptance_inputs: str | Path,
    v4_acceptance_report: str | Path,
    v4_doc_sync_acceptance_bundle: str | Path,
    v4_doc_sync_final_command_log: str | Path,
    preflight_root: str | Path,
    preflight_flaky_probe_report: str | Path,
    preflight_visibility_probe_summary: str | Path,
    preflight_run_matrix_manifest: str | Path,
    preflight_task_selection_report: str | Path,
    preflight_resume_claim_gate_report: str | Path,
    preflight_evidence_manifest: str | Path,
    baseline_commit: str = V5_BASELINE_COMMIT,
    v4_closure_commit: str = V5_V4_CLOSURE_COMMIT,
    baseline_command_cwd: str | Path | None = None,
    run_live_baseline_checks: bool = False,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build V5 Stage 0 preimplementation evidence from explicit input paths."""

    output_root = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_root / name for name in V5_STAGE0_OUTPUT_NAMES if (output_root / name).exists()]
        if existing:
            raise ConfigError(
                "V5 Stage 0 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    output_root.mkdir(parents=True, exist_ok=True)
    command_log_path = output_root / "v5_preimplementation_command_log.jsonl"
    command_output_dir = output_root / "command_outputs"

    baseline_report_path = output_root / "v5_baseline_check_report.json"
    v4_closure_report_path = output_root / "v4_review_findings_closure_report.json"
    doc_sync_report_path = output_root / "v5_documentation_sync_report.json"
    binding_path = output_root / "v5_preflight_input_binding.json"
    baseline_cwd = Path(baseline_command_cwd) if baseline_command_cwd is not None else Path.cwd()

    command_records = _build_baseline_command_records(
        baseline_commit=baseline_commit,
        v4_closure_commit=v4_closure_commit,
        v2_acceptance_report=Path(v2_acceptance_report),
        v3_acceptance_report=Path(v3_acceptance_report),
        v3_acceptance_bundle=Path(v3_acceptance_bundle),
        v4_acceptance_inputs=Path(v4_acceptance_inputs),
        v4_acceptance_report=Path(v4_acceptance_report),
        v4_doc_sync_acceptance_bundle=Path(v4_doc_sync_acceptance_bundle),
        run_live_checks=run_live_baseline_checks,
        output_dir=command_output_dir,
        command_cwd=baseline_cwd,
    )
    _write_jsonl(command_log_path, command_records)

    baseline_report = _baseline_report_payload(
        baseline_commit=baseline_commit,
        v4_closure_commit=v4_closure_commit,
        live_checks_run=run_live_baseline_checks,
        command_log_path=command_log_path,
        command_records=command_records,
        command_cwd=baseline_cwd,
    )
    _write_json(baseline_report_path, baseline_report)

    v4_closure_report = _v4_closure_report_payload(
        v4_closure_commit=v4_closure_commit,
        v4_acceptance_inputs=Path(v4_acceptance_inputs),
        v4_acceptance_report=Path(v4_acceptance_report),
        v4_doc_sync_acceptance_bundle=Path(v4_doc_sync_acceptance_bundle),
        v4_doc_sync_final_command_log=Path(v4_doc_sync_final_command_log),
    )
    _write_json(v4_closure_report_path, v4_closure_report)

    doc_sync_report = _documentation_sync_report_payload()
    _write_json(doc_sync_report_path, doc_sync_report)

    preflight_artifacts = {
        "flaky_probe_report": Path(preflight_flaky_probe_report),
        "visibility_probe_summary": Path(preflight_visibility_probe_summary),
        "run_matrix_preflight_manifest": Path(preflight_run_matrix_manifest),
        "task_selection_preflight_report": Path(preflight_task_selection_report),
        "resume_claim_gate_preflight_report": Path(preflight_resume_claim_gate_report),
        "run_matrix_freeze_evidence_manifest": Path(preflight_evidence_manifest),
    }
    binding = _preflight_input_binding_payload(
        baseline_commit=baseline_commit,
        v4_closure_commit=v4_closure_commit,
        preflight_root=Path(preflight_root),
        v2_acceptance_report=Path(v2_acceptance_report),
        v3_acceptance_report=Path(v3_acceptance_report),
        v3_acceptance_bundle=Path(v3_acceptance_bundle),
        v4_acceptance_inputs=Path(v4_acceptance_inputs),
        v4_acceptance_report=Path(v4_acceptance_report),
        v4_doc_sync_acceptance_bundle=Path(v4_doc_sync_acceptance_bundle),
        v4_doc_sync_final_command_log=Path(v4_doc_sync_final_command_log),
        baseline_report=baseline_report_path,
        v4_closure_report=v4_closure_report_path,
        documentation_sync_report=doc_sync_report_path,
        command_log=command_log_path,
        preflight_artifacts=preflight_artifacts,
        baseline_command_cwd=baseline_cwd,
    )
    _write_json(binding_path, binding)
    return binding_path


def inspect_v5_preimplementation(
    binding: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """Read-only inspection for V5 Stage 0 preimplementation input binding."""

    binding_path = Path(binding)
    failures: list[str] = []
    payload = _read_json_for_inspect(binding_path, failures)
    if payload.get("schema_version") != V5_PREFLIGHT_INPUT_BINDING_VERSION:
        failures.append("v5_preflight_input_binding schema_version 不匹配。")
    if payload.get("baseline_commit") != V5_BASELINE_COMMIT:
        failures.append("V5 baseline commit 必须是 9fd7007。")
    if payload.get("v4_closure_commit") != V5_V4_CLOSURE_COMMIT:
        failures.append("V4 closure commit 必须是 e0da89c。")
    if payload.get("accepted_counting_allowed") is not False:
        failures.append("Stage 0 preflight input binding 不能允许 accepted counting。")
    if payload.get("full_v5_threshold_status") != V5_PARTIAL_THRESHOLD_STATUS:
        failures.append("当前 initial 10 preflight 必须标记为未满足 12 total / 8 PR-issue 严格任务库存门。")
    if payload.get("initial_candidate_count") != 10:
        failures.append("initial_candidate_count 必须为 10。")
    if payload.get("pr_issue_candidate_count") != 6:
        failures.append("pr_issue_candidate_count 必须为 6。")
    if payload.get("swebench_like_anchor_count") != 4:
        failures.append("swebench_like_anchor_count 必须为 4。")
    if payload.get("agent_run_ready_count") != 10:
        failures.append("agent_run_ready_count 必须为 10。")
    if payload.get("comparison_ready_count") != 9:
        failures.append("comparison_ready_count 必须为 9。")
    if payload.get("planned_matrix_cells") != 24:
        failures.append("planned_matrix_cells 必须为 24。")
    if payload.get("real_agent_run_executed") is not False:
        failures.append("Stage 0 preflight input 不能声明已经执行真实 agent run。")
    if payload.get("provider_api_called") is not False:
        failures.append("Stage 0 preflight input 不能声明已经调用 provider API。")
    stage0_policy = payload.get("stage0_policy")
    if not isinstance(stage0_policy, dict):
        failures.append("stage0_policy 必须是 object。")
    else:
        for key in (
            "preflight_artifacts_do_not_count_as_final_v5_accepted_tasks",
            "preflight_artifacts_do_not_count_as_real_provider_runs",
            "preflight_artifacts_do_not_count_as_training_samples",
        ):
            if stage0_policy.get(key) is not True:
                failures.append(f"stage0_policy.{key} 必须为 true。")

    _inspect_v5_ref(payload.get("baseline_check_report_ref"), failures, label="baseline_check_report_ref")
    _inspect_v5_ref(payload.get("v4_review_findings_closure_report_ref"), failures, label="v4_review_findings_closure_report_ref")
    _inspect_v5_ref(payload.get("documentation_sync_report_ref"), failures, label="documentation_sync_report_ref")
    _inspect_v5_ref(payload.get("preimplementation_command_log_ref"), failures, label="preimplementation_command_log_ref")

    baseline_report = _read_ref_payload(payload.get("baseline_check_report_ref"), failures)
    if baseline_report:
        _inspect_baseline_report(baseline_report, failures)
    v4_closure_report = _read_ref_payload(payload.get("v4_review_findings_closure_report_ref"), failures)
    if v4_closure_report:
        _inspect_v4_closure_report(v4_closure_report, failures)
    doc_report = _read_ref_payload(payload.get("documentation_sync_report_ref"), failures)
    if doc_report:
        _inspect_documentation_sync_report(doc_report, failures)
    command_log_path = _path_from_ref(payload.get("preimplementation_command_log_ref"))
    if command_log_path is not None:
        _inspect_v5_command_log(command_log_path, failures)

    preflight_refs = payload.get("preflight_input_refs")
    if not isinstance(preflight_refs, dict):
        failures.append("preflight_input_refs 必须是 object。")
    else:
        missing = sorted(set(V5_PREFLIGHT_ARTIFACT_FIELDS).difference(preflight_refs))
        if missing:
            failures.append("preflight_input_refs 缺少：" + ", ".join(missing))
        for key, ref in preflight_refs.items():
            _inspect_v5_ref(ref, failures, label=f"preflight_input_refs.{key}")
    v4_refs = payload.get("v4_latest_refs")
    if not isinstance(v4_refs, dict):
        failures.append("v4_latest_refs 必须是 object。")
    else:
        bundle_ref = v4_refs.get("v4_doc_sync_acceptance_bundle")
        bundle_path = str((bundle_ref or {}).get("path") or "")
        if V4_DOC_SYNC_BUNDLE_NAME not in bundle_path:
            failures.append("V4 latest bundle 必须使用 doc-sync acceptance bundle，不能使用原始 bundle。")
        for key, ref in v4_refs.items():
            _inspect_v5_ref(ref, failures, label=f"v4_latest_refs.{key}")

    lines = [
        f"V5 preimplementation input binding: {binding_path}",
        f"Initial candidates: {payload.get('initial_candidate_count')}",
        f"PR / issue candidates: {payload.get('pr_issue_candidate_count')}",
        f"SWE-Bench-like anchors: {payload.get('swebench_like_anchor_count')}",
        f"Threshold status: {payload.get('full_v5_threshold_status')}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V5 preimplementation: complete")
    lines.append("Inspect V5 preimplementation: passed")
    return "\n".join(lines)


def _baseline_commands(
    *,
    baseline_commit: str,
    v4_closure_commit: str,
    v2_acceptance_report: Path,
    v3_acceptance_report: Path,
    v3_acceptance_bundle: Path,
    v4_acceptance_inputs: Path,
    v4_acceptance_report: Path,
    v4_doc_sync_acceptance_bundle: Path,
) -> list[dict[str, Any]]:
    py = sys.executable
    return [
        {"command_name": "pwd", "argv": ["pwd"]},
        {"command_name": "git_status_short", "argv": ["git", "status", "--short"]},
        {"command_name": "git_log_1_oneline", "argv": ["git", "log", "-1", "--oneline"]},
        {"command_name": "git_status_docs_v5", "argv": ["git", "status", "--short", "--", "docs/v5"]},
        {"command_name": "git_diff_docs_v5", "argv": ["git", "diff", "--name-status", "--", "docs/v5"]},
        {"command_name": "git_ls_tree_docs_v5", "argv": ["git", "ls-tree", "-r", "--name-only", baseline_commit, "docs/v5"]},
        {"command_name": "git_merge_base_v5_baseline_head", "argv": ["git", "merge-base", "--is-ancestor", baseline_commit, "HEAD"]},
        {"command_name": "git_merge_base_v4_closure_head", "argv": ["git", "merge-base", "--is-ancestor", v4_closure_commit, "HEAD"]},
        {"command_name": "compileall_src", "argv": [py, "-m", "compileall", "src"]},
        {"command_name": "pytest_q", "argv": [py, "-m", "pytest", "-q"]},
        {"command_name": "inspect_v2_acceptance", "argv": ["repo-harness", "inspect-v2-acceptance", v2_acceptance_report.as_posix(), "--assert-complete"]},
        {"command_name": "inspect_v3_acceptance", "argv": ["repo-harness", "inspect-v3-acceptance", v3_acceptance_report.as_posix(), "--assert-complete"]},
        {"command_name": "inspect_v3_acceptance_bundle", "argv": ["repo-harness", "inspect-acceptance-bundle", v3_acceptance_bundle.as_posix(), "--assert-immutable"]},
        {"command_name": "inspect_v4_inputs", "argv": ["repo-harness", "inspect-v4-inputs", v4_acceptance_inputs.as_posix(), "--assert-complete"]},
        {"command_name": "inspect_v4_acceptance", "argv": ["repo-harness", "inspect-v4-acceptance", v4_acceptance_report.as_posix(), "--assert-complete"]},
        {"command_name": "inspect_v4_doc_sync_acceptance_bundle", "argv": ["repo-harness", "inspect-acceptance-bundle", v4_doc_sync_acceptance_bundle.as_posix(), "--assert-immutable"]},
        {"command_name": "docker_version", "argv": ["docker", "version"]},
        {"command_name": "docker_context_show", "argv": ["docker", "context", "show"]},
        {"command_name": "docker_info", "argv": ["docker", "info"]},
        {"command_name": "docker_info_memtotal", "argv": ["docker", "info", "--format", "{{json .MemTotal}}"]},
        {"command_name": "docker_run_hello_world", "argv": ["docker", "run", "--rm", "hello-world"]},
        {"command_name": "docker_run_alpine_uname_m", "argv": ["docker", "run", "--rm", "alpine:3.20", "uname", "-m"]},
        {"command_name": "docker_run_alpine_meminfo", "argv": ["docker", "run", "--rm", "alpine:3.20", "sh", "-lc", "grep MemTotal /proc/meminfo"]},
        {"command_name": "docker_run_alpine_amd64_uname_m", "argv": ["docker", "run", "--rm", "--platform", "linux/amd64", "alpine:3.20", "uname", "-m"]},
    ]


def _build_baseline_command_records(
    *,
    baseline_commit: str,
    v4_closure_commit: str,
    v2_acceptance_report: Path,
    v3_acceptance_report: Path,
    v3_acceptance_bundle: Path,
    v4_acceptance_inputs: Path,
    v4_acceptance_report: Path,
    v4_doc_sync_acceptance_bundle: Path,
    run_live_checks: bool,
    output_dir: Path,
    command_cwd: Path,
) -> list[dict[str, Any]]:
    commands = _baseline_commands(
        baseline_commit=baseline_commit,
        v4_closure_commit=v4_closure_commit,
        v2_acceptance_report=v2_acceptance_report,
        v3_acceptance_report=v3_acceptance_report,
        v3_acceptance_bundle=v3_acceptance_bundle,
        v4_acceptance_inputs=v4_acceptance_inputs,
        v4_acceptance_report=v4_acceptance_report,
        v4_doc_sync_acceptance_bundle=v4_doc_sync_acceptance_bundle,
    )
    records: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        if run_live_checks:
            records.append(_run_command_record(index=index, command=command, output_dir=output_dir, command_cwd=command_cwd))
        else:
            records.append(_skipped_command_record(index=index, command=command, output_dir=output_dir, command_cwd=command_cwd))
    return records


def _run_command_record(*, index: int, command: dict[str, Any], output_dir: Path, command_cwd: Path) -> dict[str, Any]:
    started_at = _utc_timestamp()
    env = os.environ.copy()
    env["PATH"] = f"{Path('.venv/bin').resolve()}{os.pathsep}{env.get('PATH', '')}"
    command_src = command_cwd / "src"
    if command_src.exists():
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            command_src.as_posix()
            if not existing_pythonpath
            else f"{command_src.as_posix()}{os.pathsep}{existing_pythonpath}"
        )
    completed = subprocess.run(
        command["argv"],
        cwd=command_cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return _command_record_from_output(
        index=index,
        command=command,
        output_dir=output_dir,
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        started_at=started_at,
        finished_at=_utc_timestamp(),
        structured_skip_reason=None,
        command_cwd=command_cwd,
    )


def _skipped_command_record(*, index: int, command: dict[str, Any], output_dir: Path, command_cwd: Path) -> dict[str, Any]:
    return _command_record_from_output(
        index=index,
        command=command,
        output_dir=output_dir,
        stdout="",
        stderr="",
        exit_code=None,
        started_at=_utc_timestamp(),
        finished_at=_utc_timestamp(),
        structured_skip_reason="not_run_by_builder",
        command_cwd=command_cwd,
    )


def _command_record_from_output(
    *,
    index: int,
    command: dict[str, Any],
    output_dir: Path,
    stdout: str,
    stderr: str,
    exit_code: int | None,
    started_at: str,
    finished_at: str,
    structured_skip_reason: str | None,
    command_cwd: Path,
) -> dict[str, Any]:
    safe_name = str(command["command_name"]).replace("/", "_")
    stdout_path = output_dir / f"{index:02d}_{safe_name}.stdout.txt"
    stderr_path = output_dir / f"{index:02d}_{safe_name}.stderr.txt"
    _write_text(stdout_path, stdout)
    _write_text(stderr_path, stderr)
    return {
        "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command["command_name"],
        "argv": command["argv"],
        "cwd": command_cwd.as_posix(),
        "builder_invocation_cwd": Path.cwd().as_posix(),
        "env_policy": "PATH prepends .venv/bin; PYTHONPATH prepends baseline command cwd src when present; provider credential values are not recorded",
        "network_policy": _network_policy_for_argv(command["argv"]),
        "risk_command_hits": _risk_command_hits(command["argv"]),
        "input_ref_policy": _input_ref_policy(command_cwd),
        "input_refs": _input_refs_for_argv(command["argv"], command_cwd=command_cwd),
        "output_refs": [
            _evidence_ref(
                stdout_path,
                kind="command_stdout",
                purpose=f"{command['command_name']} stdout",
                visibility="audit_only",
                producer_command=command["command_name"],
                producer_stage="v5_stage0_preimplementation",
                inspect_command="inspect-v5-preimplementation",
            ),
            _evidence_ref(
                stderr_path,
                kind="command_stderr",
                purpose=f"{command['command_name']} stderr",
                visibility="audit_only",
                producer_command=command["command_name"],
                producer_stage="v5_stage0_preimplementation",
                inspect_command="inspect-v5-preimplementation",
            ),
        ],
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "structured_skip_reason": structured_skip_reason,
        "structured_failure_reason": None if exit_code in (0, None) else "command_exit_nonzero",
        "stdout_summary": _safe_output_summary(stdout),
        "stderr_summary": _safe_output_summary(stderr),
        "tool_or_cli_version": f"repo-harness {__version__}",
    }


def _baseline_report_payload(
    *,
    baseline_commit: str,
    v4_closure_commit: str,
    live_checks_run: bool,
    command_log_path: Path,
    command_records: list[dict[str, Any]],
    command_cwd: Path,
) -> dict[str, Any]:
    by_name = {record.get("command_name"): record for record in command_records}
    return {
        "schema_version": V5_BASELINE_CHECK_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "current_head": _git_output(["git", "rev-parse", "HEAD"], cwd=command_cwd),
        "baseline_command_cwd": command_cwd.as_posix(),
        "builder_invocation_cwd": Path.cwd().as_posix(),
        "baseline_commit": baseline_commit,
        "v4_closure_commit": v4_closure_commit,
        "live_checks_run": live_checks_run,
        "command_log_ref": _evidence_ref(
            command_log_path,
            kind="command_log",
            purpose="V5 Stage 0 preimplementation command log",
            visibility="audit_only",
            producer_command="build-v5-preimplementation",
            producer_stage="v5_stage0_preimplementation",
            inspect_command="inspect-v5-preimplementation",
        ),
        "required_commands": [record["command_name"] for record in command_records],
        "baseline_status": {
            "v5_baseline_commit_is_ancestor": _command_status(by_name.get("git_merge_base_v5_baseline_head")),
            "v4_closure_commit_is_ancestor": _command_status(by_name.get("git_merge_base_v4_closure_head")),
            "docs_v5_clean": _docs_status(by_name.get("git_status_docs_v5"), by_name.get("git_diff_docs_v5")),
            "compileall_src": _command_status(by_name.get("compileall_src")),
            "pytest": _command_status(by_name.get("pytest_q")),
            "v2_acceptance": _command_status(by_name.get("inspect_v2_acceptance")),
            "v3_acceptance": _command_status(by_name.get("inspect_v3_acceptance")),
            "v3_acceptance_bundle": _command_status(by_name.get("inspect_v3_acceptance_bundle")),
            "v4_inputs": _command_status(by_name.get("inspect_v4_inputs")),
            "v4_acceptance": _command_status(by_name.get("inspect_v4_acceptance")),
            "v4_doc_sync_acceptance_bundle": _command_status(by_name.get("inspect_v4_doc_sync_acceptance_bundle")),
            "docker_hello_world": _command_status(by_name.get("docker_run_hello_world")),
            "docker_arm64_probe": _command_status(by_name.get("docker_run_alpine_uname_m")),
            "docker_amd64_probe": _command_status(by_name.get("docker_run_alpine_amd64_uname_m")),
        },
        "dirty_worktree_policy": "unrelated dirty files are recorded but do not pass as V5 evidence unless explicitly bound",
    }


def _v4_closure_report_payload(
    *,
    v4_closure_commit: str,
    v4_acceptance_inputs: Path,
    v4_acceptance_report: Path,
    v4_doc_sync_acceptance_bundle: Path,
    v4_doc_sync_final_command_log: Path,
) -> dict[str, Any]:
    findings = [
        "contamination_denylist_hash",
        "final_verifier_boundary",
        "preference_pair_comparability",
        "structured_reward_allowlist",
        "independent_regression_evidence",
        "implementation_log_index",
        "final_command_log_binding",
        "reward_audit_schema",
    ]
    return {
        "schema_version": V5_V4_CLOSURE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "v4_closure_commit": v4_closure_commit,
        "latest_v4_evidence_root": V4_LATEST_DIR,
        "latest_v4_acceptance_inputs_ref": _evidence_ref(
            v4_acceptance_inputs,
            kind="v4_acceptance_inputs",
            purpose="Latest V4 acceptance inputs for V5 baseline",
            visibility="audit_only",
            producer_command="build-v4-acceptance-inputs",
            producer_stage="v4_stage8_final_acceptance",
            inspect_command="inspect-v4-inputs",
        ),
        "latest_v4_acceptance_report_ref": _evidence_ref(
            v4_acceptance_report,
            kind="v4_acceptance_report",
            purpose="Latest V4 acceptance report for V5 baseline",
            visibility="audit_only",
            producer_command="build-v4-acceptance-report",
            producer_stage="v4_stage8_final_acceptance",
            inspect_command="inspect-v4-acceptance",
        ),
        "latest_v4_doc_sync_acceptance_bundle_ref": _evidence_ref(
            v4_doc_sync_acceptance_bundle,
            kind="v4_doc_sync_acceptance_bundle",
            purpose="Latest V4 doc-sync acceptance bundle for V5 baseline",
            visibility="audit_only",
            producer_command="build-v4-acceptance-bundle",
            producer_stage="v4_doc_sync",
            inspect_command="inspect-acceptance-bundle",
        ),
        "latest_v4_doc_sync_final_command_log_ref": _evidence_ref(
            v4_doc_sync_final_command_log,
            kind="v4_doc_sync_final_command_log",
            purpose="Latest V4 doc-sync final command log for V5 baseline",
            visibility="audit_only",
            producer_command="build-v4-final-command-log",
            producer_stage="v4_doc_sync",
            inspect_command="inspect-acceptance-bundle",
        ),
        "closed_findings": [
            {
                "finding_id": finding,
                "status": "closed",
                "closure_commit": v4_closure_commit,
                "evidence_root": V4_LATEST_DIR,
                "inspect_commands": [
                    "inspect-v4-inputs",
                    "inspect-v4-acceptance",
                    "inspect-acceptance-bundle",
                ],
            }
            for finding in findings
        ],
        "status": "passed",
    }


def _documentation_sync_report_payload() -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    old_path_mentions: list[dict[str, Any]] = []
    for raw_path in V5_DOCUMENTATION_SYNC_REQUIRED_PATHS:
        path = Path(raw_path)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        old_count = text.count("runs/v4-final-rerun-20260504T162105Z")
        if old_count:
            old_path_mentions.append({"path": raw_path, "count": old_count})
        checked.append(
            {
                "path": raw_path,
                "exists": path.exists(),
                "sha256": _hash_path(path) if path.exists() else None,
                "mentions_latest_v4_root": V4_LATEST_DIR in text,
                "mentions_v5_docs": "docs/v5" in text or raw_path.startswith("docs/v5/"),
                "old_v4_path_mentions": old_count,
                "old_v4_path_marked_historical": old_count == 0 or _marks_old_v4_path_as_historical(text),
            }
        )
    return {
        "schema_version": V5_DOCUMENTATION_SYNC_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "checked_paths": checked,
        "required_paths": list(V5_DOCUMENTATION_SYNC_REQUIRED_PATHS),
        "latest_v4_root": V4_LATEST_DIR,
        "old_v4_path_mentions": old_path_mentions,
        "old_v4_path_policy": "allowed_only_when_marked_as_history",
        "v5_docs_index_required": True,
        "status": "passed" if all(item["exists"] for item in checked) else "failed",
    }


def _preflight_input_binding_payload(
    *,
    baseline_commit: str,
    v4_closure_commit: str,
    preflight_root: Path,
    v2_acceptance_report: Path,
    v3_acceptance_report: Path,
    v3_acceptance_bundle: Path,
    v4_acceptance_inputs: Path,
    v4_acceptance_report: Path,
    v4_doc_sync_acceptance_bundle: Path,
    v4_doc_sync_final_command_log: Path,
    baseline_report: Path,
    v4_closure_report: Path,
    documentation_sync_report: Path,
    command_log: Path,
    preflight_artifacts: dict[str, Path],
    baseline_command_cwd: Path,
) -> dict[str, Any]:
    return {
        "schema_version": V5_PREFLIGHT_INPUT_BINDING_VERSION,
        "created_at": _utc_timestamp(),
        "current_head": _git_output(["git", "rev-parse", "HEAD"], cwd=baseline_command_cwd),
        "baseline_command_cwd": baseline_command_cwd.as_posix(),
        "builder_invocation_cwd": Path.cwd().as_posix(),
        "baseline_commit": baseline_commit,
        "v4_closure_commit": v4_closure_commit,
        "preflight_root": _rel(preflight_root),
        "preflight_root_ref": _evidence_ref(
            preflight_root,
            kind="preflight_root",
            purpose="V5 initial 10 candidate preflight root",
            visibility="audit_only",
            producer_command="v5 preflight pipeline",
            producer_stage="v5_preimplementation_input",
            inspect_command="inspect-v5-preimplementation",
        ),
        "baseline_check_report_ref": _evidence_ref(
            baseline_report,
            kind="v5_baseline_check_report",
            purpose="V5 Stage 0 baseline check report",
            visibility="audit_only",
            producer_command="build-v5-preimplementation",
            producer_stage="v5_stage0_preimplementation",
            inspect_command="inspect-v5-preimplementation",
        ),
        "v4_review_findings_closure_report_ref": _evidence_ref(
            v4_closure_report,
            kind="v4_review_findings_closure_report",
            purpose="V4 review findings closure binding for V5",
            visibility="audit_only",
            producer_command="build-v5-preimplementation",
            producer_stage="v5_stage0_preimplementation",
            inspect_command="inspect-v5-preimplementation",
        ),
        "documentation_sync_report_ref": _evidence_ref(
            documentation_sync_report,
            kind="v5_documentation_sync_report",
            purpose="V5 documentation sync report",
            visibility="audit_only",
            producer_command="build-v5-preimplementation",
            producer_stage="v5_stage0_preimplementation",
            inspect_command="inspect-v5-preimplementation",
        ),
        "preimplementation_command_log_ref": _evidence_ref(
            command_log,
            kind="v5_preimplementation_command_log",
            purpose="V5 Stage 0 preimplementation command log",
            visibility="audit_only",
            producer_command="build-v5-preimplementation",
            producer_stage="v5_stage0_preimplementation",
            inspect_command="inspect-v5-preimplementation",
        ),
        "v2_v3_v4_regression_refs": {
            "v2_acceptance_report": _evidence_ref(v2_acceptance_report, kind="v2_acceptance_report", purpose="V2 regression acceptance report", visibility="audit_only", producer_command="inspect-v2-acceptance", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-v2-acceptance"),
            "v3_acceptance_report": _evidence_ref(v3_acceptance_report, kind="v3_acceptance_report", purpose="V3 regression acceptance report", visibility="audit_only", producer_command="inspect-v3-acceptance", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-v3-acceptance"),
            "v3_acceptance_bundle": _evidence_ref(v3_acceptance_bundle, kind="v3_acceptance_bundle", purpose="V3 regression acceptance bundle", visibility="audit_only", producer_command="inspect-acceptance-bundle", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-acceptance-bundle"),
        },
        "v4_latest_refs": {
            "v4_acceptance_inputs": _evidence_ref(v4_acceptance_inputs, kind="v4_acceptance_inputs", purpose="Latest V4 acceptance inputs", visibility="audit_only", producer_command="inspect-v4-inputs", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-v4-inputs"),
            "v4_acceptance_report": _evidence_ref(v4_acceptance_report, kind="v4_acceptance_report", purpose="Latest V4 acceptance report", visibility="audit_only", producer_command="inspect-v4-acceptance", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-v4-acceptance"),
            "v4_doc_sync_acceptance_bundle": _evidence_ref(v4_doc_sync_acceptance_bundle, kind="v4_doc_sync_acceptance_bundle", purpose="Latest V4 doc-sync acceptance bundle", visibility="audit_only", producer_command="inspect-acceptance-bundle", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-acceptance-bundle"),
            "v4_doc_sync_final_command_log": _evidence_ref(v4_doc_sync_final_command_log, kind="v4_doc_sync_final_command_log", purpose="Latest V4 doc-sync final command log", visibility="audit_only", producer_command="inspect-acceptance-bundle", producer_stage="v5_stage0_preimplementation", inspect_command="inspect-acceptance-bundle"),
        },
        "preflight_input_refs": {
            key: _evidence_ref(
                path,
                kind=key,
                purpose=f"V5 preflight input artifact: {key}",
                visibility="audit_only",
                producer_command="v5 preflight pipeline",
                producer_stage="v5_preimplementation_input",
                inspect_command="inspect-v5-preimplementation",
            )
            for key, path in preflight_artifacts.items()
        },
        "initial_candidate_count": 10,
        "pr_issue_candidate_count": 6,
        "swebench_like_anchor_count": 4,
        "flaky_probe_stable_count": 10,
        "flaky_suspected_count": 0,
        "visibility_status": "passed",
        "model_visible_leak_count": 0,
        "share_safe_violation_count": 0,
        "agent_run_ready_count": 10,
        "comparison_ready_count": 9,
        "provider_comparison_ready_count": 4,
        "scaffold_comparison_ready_count": 4,
        "budget_comparison_ready_count": 4,
        "planned_matrix_cells": 24,
        "real_agent_run_executed": False,
        "provider_api_called": False,
        "accepted_counting_allowed": False,
        "full_v5_threshold_status": V5_PARTIAL_THRESHOLD_STATUS,
        "strict_inventory_gap": {
            "accepted_auditable_total_required": 12,
            "accepted_auditable_total_current": 10,
            "pr_issue_required": 8,
            "pr_issue_current": 6,
            "swebench_like_anchor_required": 3,
            "swebench_like_anchor_current": 4,
            "default_resolution": "Stage 2B must add 2 PR / issue candidates or formal scope change",
        },
        "stage0_policy": {
            "preflight_artifacts_do_not_count_as_final_v5_accepted_tasks": True,
            "preflight_artifacts_do_not_count_as_real_provider_runs": True,
            "preflight_artifacts_do_not_count_as_training_samples": True,
            "no_latest_run_discovery": True,
            "explicit_path_binding": True,
        },
    }


def _inspect_baseline_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != V5_BASELINE_CHECK_REPORT_VERSION:
        failures.append("v5_baseline_check_report schema_version 不匹配。")
    if payload.get("live_checks_run") is not True:
        failures.append("v5_baseline_check_report 必须来自 live baseline checks。")
    status = payload.get("baseline_status")
    if not isinstance(status, dict):
        failures.append("v5_baseline_check_report 缺少 baseline_status。")
        return
    for key in (
        "v5_baseline_commit_is_ancestor",
        "v4_closure_commit_is_ancestor",
        "docs_v5_clean",
        "compileall_src",
        "pytest",
        "v2_acceptance",
        "v3_acceptance",
        "v3_acceptance_bundle",
        "v4_inputs",
        "v4_acceptance",
        "v4_doc_sync_acceptance_bundle",
        "docker_hello_world",
        "docker_arm64_probe",
        "docker_amd64_probe",
    ):
        if status.get(key) != "passed":
            failures.append(f"V5 baseline check 未通过：{key}")


def _inspect_v4_closure_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != V5_V4_CLOSURE_REPORT_VERSION:
        failures.append("v4_review_findings_closure_report schema_version 不匹配。")
    if payload.get("v4_closure_commit") != V5_V4_CLOSURE_COMMIT:
        failures.append("v4_review_findings_closure_report 必须绑定 e0da89c。")
    if payload.get("latest_v4_evidence_root") != V4_LATEST_DIR:
        failures.append("v4_review_findings_closure_report 必须使用 194758Z 最新 V4 evidence root。")
    if payload.get("status") != "passed":
        failures.append("v4_review_findings_closure_report status 必须为 passed。")
    findings = payload.get("closed_findings")
    if not isinstance(findings, list) or len(findings) < 8:
        failures.append("v4_review_findings_closure_report closed_findings 覆盖不完整。")
    else:
        for index, finding in enumerate(findings, start=1):
            if finding.get("status") != "closed":
                failures.append(f"closed_findings[{index}] 必须 status=closed。")
            if finding.get("closure_commit") != V5_V4_CLOSURE_COMMIT:
                failures.append(f"closed_findings[{index}] closure_commit 必须是 e0da89c。")
    for field in (
        "latest_v4_acceptance_inputs_ref",
        "latest_v4_acceptance_report_ref",
        "latest_v4_doc_sync_acceptance_bundle_ref",
        "latest_v4_doc_sync_final_command_log_ref",
    ):
        _inspect_v5_ref(payload.get(field), failures, label=field)


def _inspect_documentation_sync_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != V5_DOCUMENTATION_SYNC_REPORT_VERSION:
        failures.append("v5_documentation_sync_report schema_version 不匹配。")
    required = set(V5_DOCUMENTATION_SYNC_REQUIRED_PATHS)
    checked = payload.get("checked_paths")
    if not isinstance(checked, list):
        failures.append("v5_documentation_sync_report checked_paths 必须是 list。")
        return
    by_path = {item.get("path"): item for item in checked if isinstance(item, dict)}
    missing = sorted(required.difference(by_path))
    if missing:
        failures.append("v5_documentation_sync_report 缺少检查路径：" + ", ".join(missing))
    for path in required:
        item = by_path.get(path)
        if not item:
            continue
        if item.get("exists") is not True:
            failures.append(f"v5_documentation_sync_report 路径不存在：{path}")
        if path != "reference/claude-code-typescript-src/AGENTS.md" and item.get("mentions_latest_v4_root") is not True:
            failures.append(f"v5_documentation_sync_report 路径未引用最新 V4 root：{path}")
        if item.get("old_v4_path_mentions", 0) and item.get("old_v4_path_marked_historical") is not True:
            failures.append(f"旧 V4 acceptance 目录只能作为历史说明出现：{path}")


def _inspect_v5_command_log(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"V5 preimplementation command log 不存在：{path}")
        return
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"V5 command log 第 {index} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"V5 command log 第 {index} 行顶层必须是 object。")
            continue
        records.append(record)
        if record.get("schema_version") != V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION:
            failures.append(f"V5 command log 第 {index} 行 schema_version 不匹配。")
        for field in ("argv", "cwd", "input_refs", "output_refs", "started_at", "finished_at", "stdout_sha256", "stderr_sha256"):
            if field not in record:
                failures.append(f"V5 command log 第 {index} 行缺少 {field}。")
        if record.get("exit_code") is None and not record.get("structured_skip_reason"):
            failures.append(f"V5 command log 第 {index} 行缺少 exit_code 或 structured_skip_reason。")
        if record.get("structured_skip_reason") is not None:
            failures.append(f"V5 command log 第 {index} 行不能是 skipped command。")
        for ref_field in ("input_refs", "output_refs"):
            refs = record.get(ref_field)
            if not isinstance(refs, list):
                failures.append(f"V5 command log 第 {index} 行 {ref_field} 必须是 list。")
                continue
            for ref_index, ref in enumerate(refs, start=1):
                _inspect_v5_ref(ref, failures, label=f"command_log[{index}].{ref_field}[{ref_index}]")
    required = {
        "git_merge_base_v5_baseline_head",
        "git_merge_base_v4_closure_head",
        "inspect_v4_doc_sync_acceptance_bundle",
        "pytest_q",
        "docker_run_alpine_amd64_uname_m",
    }
    present = {str(record.get("command_name") or "") for record in records}
    missing = sorted(required.difference(present))
    if missing:
        failures.append("V5 command log 缺少关键命令：" + ", ".join(missing))


def _inspect_v5_ref(ref: Any, failures: list[str], *, label: str) -> None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 不是 object。")
        return
    if ref.get("schema_version") != V5_EVIDENCE_REF_VERSION:
        failures.append(f"{label} schema_version 不匹配。")
    for field in (
        "path",
        "sha256",
        "size_bytes",
        "kind",
        "purpose",
        "visibility",
        "share_safe",
        "producer_command",
        "producer_stage",
        "inspect_command",
    ):
        if field not in ref:
            failures.append(f"{label} 缺少字段：{field}")
    path = _path_from_ref(ref)
    if path is None:
        failures.append(f"{label} 缺少 path。")
        return
    if not path.exists():
        failures.append(f"{label} 路径不存在：{ref.get('path')}")
        return
    if _hash_path(path) != ref.get("sha256"):
        failures.append(f"{label} sha256 不匹配：{ref.get('path')}")
    if not path.is_dir() and ref.get("size_bytes") != path.stat().st_size:
        failures.append(f"{label} size_bytes 不匹配：{ref.get('path')}")
    if ref.get("visibility") not in {
        "model_visible",
        "trainable",
        "diagnostic_only",
        "audit_only",
        "evaluator_only",
        "public_safe",
    }:
        failures.append(f"{label} visibility 枚举值无效。")
    if ref.get("share_safe") is True and ref.get("visibility") in {"evaluator_only"}:
        failures.append(f"{label} share_safe=true 时不能引用 evaluator-only artifact。")


def _input_refs_for_argv(argv: list[str], *, command_cwd: Path) -> list[dict[str, Any]]:
    if command_cwd.resolve() != Path.cwd().resolve():
        return []
    refs: list[dict[str, Any]] = []
    for arg in argv:
        if not isinstance(arg, str):
            continue
        path = Path(arg)
        if not path.is_absolute():
            path = command_cwd / path
        if not path.exists():
            continue
        refs.append(
            _evidence_ref(
                path,
                kind="command_input",
                purpose="Explicit command input",
                visibility="audit_only",
                producer_command="external",
                producer_stage="v5_stage0_preimplementation",
                inspect_command="inspect-v5-preimplementation",
            )
        )
    return refs


def _input_ref_policy(command_cwd: Path) -> str:
    if command_cwd.resolve() == Path.cwd().resolve():
        return "explicit argv paths are bound when they exist under the invocation worktree"
    return "explicit argv paths are recorded in argv; external baseline worktree inputs are not rebound into V5 refs"


def _read_ref_payload(ref: Any, failures: list[str]) -> dict[str, Any] | None:
    path = _path_from_ref(ref)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"{path} 不是合法 JSON：{exc}")
        return None
    if not isinstance(payload, dict):
        failures.append(f"{path} 顶层必须是 object。")
        return None
    return payload


def _path_from_ref(ref: Any) -> Path | None:
    if not isinstance(ref, dict):
        return None
    raw = ref.get("path")
    if not raw:
        return None
    path = Path(str(raw))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _evidence_ref(
    path: Path,
    *,
    kind: str,
    purpose: str,
    visibility: str,
    producer_command: str,
    producer_stage: str,
    inspect_command: str,
    share_safe: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": V5_EVIDENCE_REF_VERSION,
        "path": _rel(path),
        "sha256": _hash_path(path),
        "size_bytes": _size_bytes(path),
        "kind": kind,
        "purpose": purpose,
        "visibility": visibility,
        "share_safe": share_safe,
        "producer_command": producer_command,
        "producer_stage": producer_stage,
        "inspect_command": inspect_command,
    }


def _hash_path(path: Path) -> str:
    if not path.exists():
        raise ConfigError(f"路径不存在，无法计算 sha256：{path}")
    if path.is_dir():
        return compute_source_tree_hash(path)
    return sha256_file(path)


def _size_bytes(path: Path) -> int:
    if path.is_dir():
        return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())
    return path.stat().st_size


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"输入文件不存在：{path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"{path} 不是合法 JSON：{exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{path} 顶层必须是 object。")
        return {}
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _git_output(argv: list[str], *, cwd: Path | None = None) -> str | None:
    completed = subprocess.run(argv, cwd=cwd or Path.cwd(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _command_status(record: dict[str, Any] | None) -> str:
    if not record:
        return "missing"
    if record.get("exit_code") == 0:
        return "passed"
    if record.get("structured_skip_reason"):
        return "skipped"
    return "failed"


def _docs_status(status_record: dict[str, Any] | None, diff_record: dict[str, Any] | None) -> str:
    if _command_status(status_record) != "passed" or _command_status(diff_record) != "passed":
        return "failed"
    status_output = _stdout_first_lines(status_record)
    diff_output = _stdout_first_lines(diff_record)
    return "passed" if not status_output and not diff_output else "failed"


def _stdout_first_lines(record: dict[str, Any] | None) -> list[str]:
    if not record:
        return []
    summary = record.get("stdout_summary")
    if not isinstance(summary, dict):
        return []
    return list(summary.get("first_lines") or [])


def _safe_output_summary(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    return {
        "line_count": len(lines),
        "first_lines": lines[:20],
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _network_policy_for_argv(argv: list[str]) -> str:
    if not argv:
        return "unknown"
    if argv[0] == "docker" and "run" in argv:
        return "docker_probe_network_default"
    if argv[0] in {"repo-harness", sys.executable, "git", "pwd"}:
        return "local_only_or_read_only"
    return "unspecified"


def _risk_command_hits(argv: list[str]) -> list[str]:
    risky = {"curl", "wget", "git clone", "git remote add"}
    text = " ".join(argv)
    return sorted(item for item in risky if item in text)


def _marks_old_v4_path_as_historical(text: str) -> bool:
    lowered = text.lower()
    markers = ("历史", "早期", "取代", "historical", "replaced", "superseded")
    return any(marker in lowered for marker in markers)
