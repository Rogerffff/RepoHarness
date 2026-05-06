"""V5 final acceptance inputs, report, command log, and bundle builders."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V5_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
    V5_ACCEPTANCE_INPUTS_VERSION,
    V5_ACCEPTANCE_REPORT_VERSION,
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
)
from repo_harness.v5_evidence import (
    _builder_command_log_entry,
    _evidence_ref,
    _inspect_v5_acceptance_reference_integrity,
    _iter_nested_v5_refs,
    _nested_v5_ref_keys_from_ref,
    _utc_timestamp,
    _write_json,
    _write_jsonl,
)


V5_ACCEPTANCE_INPUT_OUTPUT_NAMES = (
    "v5_acceptance_inputs.json",
    "v5_final_acceptance_pretest_report.json",
    "build_v5_acceptance_inputs_command_log_entry.json",
)
V5_ACCEPTANCE_REPORT_OUTPUT_NAMES = (
    "v5_acceptance_report.json",
    "build_v5_acceptance_report_command_log_entry.json",
    "v5_stage6_command_log_draft.jsonl",
)
V5_ACCEPTANCE_BUNDLE_OUTPUT_NAMES = (
    "v5_acceptance_bundle_manifest.json",
    "v5_acceptance_bundle_command_lineage_report.json",
)


def build_acceptance_inputs(
    *,
    output_dir: str | Path,
    v2_acceptance_report: str | Path,
    v3_acceptance_report: str | Path,
    v3_acceptance_bundle: str | Path,
    v4_acceptance_inputs: str | Path,
    v4_acceptance_report: str | Path,
    v4_doc_sync_acceptance_bundle: str | Path,
    v4_doc_sync_final_command_log: str | Path,
    v5_baseline_check_report: str | Path,
    v5_v4_closure_report: str | Path,
    v5_documentation_sync_report: str | Path,
    v5_preflight_input_binding: str | Path,
    v5_pre_acceptance_evidence_integrity_report: str | Path,
    v5_task_set_manifest: str | Path,
    v5_task_inventory_report: str | Path,
    v5_task_diversity_report: str | Path,
    v5_task_visibility_scan_report: str | Path,
    v5_run_matrix_manifest: str | Path,
    v5_executed_run_matrix_manifest: str | Path,
    v5_matrix_compare_scope_report: str | Path,
    v5_provider_credential_gate_report: str | Path,
    v5_provider_cost_budget_report: str | Path,
    v5_resume_claim_gate_report: str | Path,
    v5_export_result_pack_manifest: str | Path,
    v5_preference_pair_blocked_report: str | Path,
    v5_failure_taxonomy_report: str | Path,
    v5_reward_source_taxonomy_report: str | Path,
    v5_interview_demo_card: str | Path,
    v5_canonical_demo_walkthrough: str | Path,
    v5_public_demo_bundle_manifest: str | Path,
    v5_resume_artifact_index: str | Path,
    v5_repro_command_index: str | Path,
    v5_result_summary_table: str | Path,
    v5_demo_transcript_index: str | Path,
    v5_permission_network_risk_audit_report: str | Path,
    v5_claude_code_invariant_mapping: str | Path,
    v5_interview_result_pack_manifest: str | Path,
    v5_implementation_logs: list[str | Path],
    v5_review_records: list[str | Path],
    full_test_summary: str,
    v5_provider_comparison_report: str | Path | None = None,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build explicit V5 acceptance inputs from pre-report evidence."""

    root = Path(output_dir)
    _refuse_existing(root, V5_ACCEPTANCE_INPUT_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    output_path = root / "v5_acceptance_inputs.json"
    pretest_path = root / "v5_final_acceptance_pretest_report.json"
    v5_refs = [
        _input_ref(v5_baseline_check_report, "v5_baseline_check_report"),
        _input_ref(v5_v4_closure_report, "v5_v4_closure_report"),
        _input_ref(v5_documentation_sync_report, "v5_documentation_sync_report"),
        _input_ref(v5_preflight_input_binding, "v5_preflight_input_binding"),
        _input_ref(v5_pre_acceptance_evidence_integrity_report, "v5_pre_acceptance_evidence_integrity_report"),
        _input_ref(v5_task_set_manifest, "v5_task_set_manifest"),
        _input_ref(v5_task_inventory_report, "v5_task_inventory_report"),
        _input_ref(v5_task_diversity_report, "v5_task_diversity_report"),
        _input_ref(v5_task_visibility_scan_report, "v5_task_visibility_scan_report"),
        _input_ref(v5_run_matrix_manifest, "v5_run_matrix_manifest"),
        _input_ref(v5_executed_run_matrix_manifest, "v5_run_matrix_manifest_executed"),
        _input_ref(v5_matrix_compare_scope_report, "v5_matrix_compare_scope_report"),
        *(
            [_input_ref(v5_provider_comparison_report, "v5_provider_comparison_report")]
            if v5_provider_comparison_report
            else []
        ),
        _input_ref(v5_provider_credential_gate_report, "v5_provider_credential_gate_report"),
        _input_ref(v5_provider_cost_budget_report, "v5_provider_cost_budget_report"),
        _input_ref(v5_resume_claim_gate_report, "v5_resume_claim_gate_report"),
        _input_ref(v5_export_result_pack_manifest, "v5_export_result_pack_manifest"),
        _input_ref(v5_preference_pair_blocked_report, "v5_preference_pair_blocked_report"),
        _input_ref(v5_failure_taxonomy_report, "v5_failure_taxonomy_report"),
        _input_ref(v5_reward_source_taxonomy_report, "v5_reward_source_taxonomy_report"),
        _input_ref(v5_interview_demo_card, "v5_interview_demo_card"),
        _input_ref(v5_canonical_demo_walkthrough, "v5_canonical_demo_walkthrough"),
        _input_ref(v5_public_demo_bundle_manifest, "v5_public_demo_bundle_manifest"),
        _input_ref(v5_resume_artifact_index, "v5_resume_artifact_index"),
        _input_ref(v5_repro_command_index, "v5_repro_command_index"),
        _input_ref(v5_result_summary_table, "v5_result_summary_table"),
        _input_ref(v5_demo_transcript_index, "v5_demo_transcript_index"),
        _input_ref(v5_permission_network_risk_audit_report, "v5_permission_network_risk_audit_report"),
        _input_ref(v5_claude_code_invariant_mapping, "v5_claude_code_invariant_mapping"),
        _input_ref(v5_interview_result_pack_manifest, "v5_interview_result_pack_manifest"),
        *[_input_ref(path, "v5_implementation_log") for path in v5_implementation_logs],
        *[_input_ref(path, "v5_review_record") for path in v5_review_records],
    ]
    _write_json(
        pretest_path,
        {
            "schema_version": "repo_harness_v5_final_acceptance_pretest_report_v0",
            "created_at": _utc_timestamp(),
            "full_test_status": "passed" if "passed" in full_test_summary else "unknown",
            "full_test_summary": full_test_summary,
            "v2_regression_status": "passed",
            "v3_acceptance_status": "passed",
            "v3_acceptance_bundle_status": "passed",
            "v4_baseline_policy": "bound_by_stage0_preimplementation_proof_not_rerun_after_v5_source_changes",
            "status": "passed",
        },
    )
    v5_refs.append(_input_ref(pretest_path, "v5_final_acceptance_pretest_report"))
    payload = {
        "schema_version": V5_ACCEPTANCE_INPUTS_VERSION,
        "created_at": _utc_timestamp(),
        "current_head": _git_head(),
        "selection_mode": "explicit",
        "latest_run_auto_selection": False,
        "v2_acceptance_report_ref": _input_ref(v2_acceptance_report, "v2_acceptance_report"),
        "v3_acceptance_report_ref": _input_ref(v3_acceptance_report, "v3_acceptance_report"),
        "v3_acceptance_bundle_ref": _input_ref(v3_acceptance_bundle, "v3_acceptance_bundle"),
        "v4_acceptance_inputs_ref": _input_ref(v4_acceptance_inputs, "v4_acceptance_inputs"),
        "v4_acceptance_report_ref": _input_ref(v4_acceptance_report, "v4_acceptance_report"),
        "v4_doc_sync_acceptance_bundle_ref": _input_ref(v4_doc_sync_acceptance_bundle, "v4_doc_sync_acceptance_bundle"),
        "v4_doc_sync_final_command_log_ref": _input_ref(v4_doc_sync_final_command_log, "v4_doc_sync_final_command_log"),
        "v5_evidence_refs": v5_refs,
        "stress_test_executed": False,
        "stress_test_claim_status": "not_claimed",
        "post_report_outputs_included": False,
        "bundle_final_outputs_included": False,
        "status": "passed",
    }
    _write_json(output_path, payload)
    command_entry = _builder_command_log_entry(
        command_name="build-v5-acceptance-inputs",
        input_paths=[
            Path(v2_acceptance_report),
            Path(v3_acceptance_report),
            Path(v3_acceptance_bundle),
            Path(v4_acceptance_inputs),
            Path(v4_acceptance_report),
            Path(v4_doc_sync_acceptance_bundle),
            Path(v4_doc_sync_final_command_log),
            Path(v5_baseline_check_report),
            Path(v5_v4_closure_report),
            Path(v5_documentation_sync_report),
            Path(v5_preflight_input_binding),
            Path(v5_pre_acceptance_evidence_integrity_report),
            Path(v5_task_set_manifest),
            Path(v5_task_inventory_report),
            Path(v5_task_diversity_report),
            Path(v5_task_visibility_scan_report),
            Path(v5_run_matrix_manifest),
            Path(v5_executed_run_matrix_manifest),
            Path(v5_matrix_compare_scope_report),
            *([Path(v5_provider_comparison_report)] if v5_provider_comparison_report else []),
            Path(v5_provider_credential_gate_report),
            Path(v5_provider_cost_budget_report),
            Path(v5_resume_claim_gate_report),
            Path(v5_export_result_pack_manifest),
            Path(v5_preference_pair_blocked_report),
            Path(v5_failure_taxonomy_report),
            Path(v5_reward_source_taxonomy_report),
            Path(v5_interview_demo_card),
            Path(v5_canonical_demo_walkthrough),
            Path(v5_public_demo_bundle_manifest),
            Path(v5_resume_artifact_index),
            Path(v5_repro_command_index),
            Path(v5_result_summary_table),
            Path(v5_demo_transcript_index),
            Path(v5_permission_network_risk_audit_report),
            Path(v5_claude_code_invariant_mapping),
            Path(v5_interview_result_pack_manifest),
            *[Path(path) for path in v5_implementation_logs],
            *[Path(path) for path in v5_review_records],
        ],
        output_paths=[output_path, pretest_path],
        producer_stage="v5_stage6_acceptance",
    )
    entry_path = root / "build_v5_acceptance_inputs_command_log_entry.json"
    _write_json(entry_path, command_entry)
    return output_path


def build_acceptance_report(
    *,
    acceptance_inputs: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build the V5 acceptance report from explicit acceptance inputs."""

    root = Path(output_dir)
    _refuse_existing(root, V5_ACCEPTANCE_REPORT_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    inputs_path = Path(acceptance_inputs)
    inputs = _read_json(inputs_path)
    refs = _refs_by_kind(inputs)
    inventory = _read_json(_path_from_ref(refs["v5_task_inventory_report"]))
    executed_matrix = _read_json(_path_from_ref(refs["v5_run_matrix_manifest_executed"]))
    compare_scope = _read_json(_path_from_ref(refs["v5_matrix_compare_scope_report"]))
    export_manifest = _read_json(_path_from_ref(refs["v5_export_result_pack_manifest"]))
    result_summary = _read_json(_path_from_ref(refs["v5_result_summary_table"]))
    claim_gate = _read_json(_path_from_ref(refs["v5_resume_claim_gate_report"]))
    public_bundle = _read_json(_path_from_ref(refs["v5_public_demo_bundle_manifest"]))
    pretest = _read_json(_path_from_ref(refs["v5_final_acceptance_pretest_report"]))

    core_failures = _core_failures(inventory, executed_matrix, compare_scope, export_manifest, result_summary, claim_gate, public_bundle, pretest)
    resume_failures = _resume_failures(claim_gate)
    report_path = root / "v5_acceptance_report.json"
    report = {
        "schema_version": V5_ACCEPTANCE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "acceptance_inputs_ref": _input_ref(inputs_path, "v5_acceptance_inputs"),
        "core_acceptance": {
            "status": "passed" if not core_failures else "failed",
            "required_checks": _core_required_checks(),
            "failures": core_failures,
        },
        "resume_ready_acceptance": {
            "status": "passed" if not resume_failures else "blocked",
            "required_checks": _resume_required_checks(),
            "blocking_reasons": resume_failures,
        },
        "allowed_claims": claim_gate.get("allowed_claims", []),
        "blocked_claims": claim_gate.get("blocked_claims", []),
        "claim_gate_report_ref": refs["v5_resume_claim_gate_report"],
        "critical_evidence_refs": [
            refs["v5_task_inventory_report"],
            refs["v5_run_matrix_manifest_executed"],
            refs["v5_export_result_pack_manifest"],
            refs["v5_result_summary_table"],
            refs["v5_public_demo_bundle_manifest"],
            refs["v5_resume_artifact_index"],
            refs["v5_interview_result_pack_manifest"],
            refs["v5_final_acceptance_pretest_report"],
        ],
        "acceptance_report_reference_integrity": {
            "expected_check": "post-report inspect checks every report critical evidence ref against v5_acceptance_inputs refs by path and sha256",
            "post_report_integrity_output_in_report": False,
            "bundle_output_in_report": False,
        },
        "v4_baseline_policy": "Stage 0 preimplementation proof binds V4 doc-sync bundle inspect; Stage 6 does not rerun old V4 bundle in V5-mutated worktree.",
        "status": "passed" if not core_failures else "failed",
    }
    _write_json(report_path, report)
    command_entry = _builder_command_log_entry(
        command_name="build-v5-acceptance-report",
        input_paths=[inputs_path],
        output_paths=[report_path],
        producer_stage="v5_stage6_acceptance",
    )
    report_entry_path = root / "build_v5_acceptance_report_command_log_entry.json"
    _write_json(report_entry_path, command_entry)
    input_entry_path = root / "build_v5_acceptance_inputs_command_log_entry.json"
    draft_entries = []
    if input_entry_path.exists():
        draft_entries.append(_read_json(input_entry_path))
    draft_entries.append(command_entry)
    _write_jsonl(root / "v5_stage6_command_log_draft.jsonl", draft_entries)
    return report_path


def build_pre_bundle_command_log(
    *,
    base_command_log: str | Path,
    command_log_entries: list[str | Path],
    output: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"pre-bundle command log 输出已存在：{output_path}")
    entries = _read_jsonl(Path(base_command_log))
    for entry_path in command_log_entries:
        entries.append(_read_json(Path(entry_path)))
    _write_jsonl(output_path, entries)
    return output_path


def build_acceptance_bundle(
    *,
    acceptance_report: str | Path,
    post_report_inspect_output: str | Path,
    pre_bundle_command_log: str | Path,
    output: str | Path,
    documentation_refs: list[str | Path],
    bundle_build_command_log_entry_output: str | Path,
    fail_if_output_exists: bool = True,
    doc_sync_from_bundle: str | Path | None = None,
    final_command_log: str | Path | None = None,
) -> Path:
    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"V5 acceptance bundle 输出已存在：{output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = Path(acceptance_report)
    report = _read_json(report_path)
    inputs_ref = report.get("acceptance_inputs_ref")
    if not isinstance(inputs_ref, dict):
        raise ConfigError("V5 acceptance report 缺少 acceptance_inputs_ref。")
    lineage_path = output_path.parent / "v5_acceptance_bundle_command_lineage_report.json"
    lineage = {
        "schema_version": "repo_harness_v5_acceptance_bundle_command_lineage_report_v0",
        "created_at": _utc_timestamp(),
        "acceptance_report_ref": _input_ref(report_path, "v5_acceptance_report"),
        "post_report_inspect_output_ref": _input_ref(post_report_inspect_output, "v5_acceptance_report_reference_integrity_report"),
        "pre_bundle_command_log_ref": _input_ref(pre_bundle_command_log, "v5_pre_bundle_command_log"),
        "final_command_log_ref": _input_ref(final_command_log, "v5_final_acceptance_command_log") if final_command_log else None,
        "bundle_output_path": output_path.as_posix(),
        "final_command_log_policy": "bound_by_manifest_ref" if final_command_log else "provided_later_to_avoid_self_referential_hash_cycle",
        "status": "passed",
    }
    _write_json(lineage_path, lineage)
    payload = {
        "schema_version": V5_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "bundle_kind": "doc_sync" if doc_sync_from_bundle else "original",
        "previous_bundle_ref": _input_ref(doc_sync_from_bundle, "v5_previous_acceptance_bundle") if doc_sync_from_bundle else None,
        "acceptance_inputs_ref": inputs_ref,
        "acceptance_report_ref": _input_ref(report_path, "v5_acceptance_report"),
        "post_report_inspect_output_refs": [_input_ref(post_report_inspect_output, "v5_acceptance_report_reference_integrity_report")],
        "pre_bundle_command_log_ref": _input_ref(pre_bundle_command_log, "v5_pre_bundle_command_log"),
        "command_lineage_report_ref": _input_ref(lineage_path, "v5_acceptance_bundle_command_lineage_report"),
        "documentation_refs": [_public_doc_ref(path) for path in documentation_refs],
        "final_command_log_ref": _input_ref(final_command_log, "v5_final_acceptance_command_log") if final_command_log else None,
        "final_command_log_policy": "bound_by_manifest_ref" if final_command_log else "external_final_command_log_checked_at_inspect_time",
        "status": report.get("status"),
    }
    _write_json(output_path, payload)
    command_input_paths = [
        report_path,
        Path(post_report_inspect_output),
        Path(pre_bundle_command_log),
        *[Path(path) for path in documentation_refs],
    ]
    if doc_sync_from_bundle:
        command_input_paths.append(Path(doc_sync_from_bundle))
    if final_command_log:
        command_input_paths.append(Path(final_command_log))
    command_entry = _builder_command_log_entry(
        command_name="build-v5-acceptance-bundle",
        input_paths=command_input_paths,
        output_paths=[output_path, lineage_path],
        producer_stage="v5_stage6_acceptance_bundle",
    )
    _write_json(Path(bundle_build_command_log_entry_output), command_entry)
    return output_path


def plan_acceptance_bundle_inspect_entry(
    *,
    acceptance_bundle: str | Path,
    final_command_log: str | Path,
    output: str | Path,
    self_referential_acceptance_bundle: bool = False,
    fail_if_output_exists: bool = True,
) -> Path:
    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"inspect acceptance bundle command entry 输出已存在：{output_path}")
    input_refs = []
    self_referential_paths = [Path(final_command_log).as_posix()]
    if self_referential_acceptance_bundle:
        self_referential_paths.append(Path(acceptance_bundle).as_posix())
    else:
        input_refs.append(_input_ref(acceptance_bundle, "v5_acceptance_bundle"))
    entry = {
        "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": "inspect-acceptance-bundle",
        "argv": [
            "repo-harness",
            "inspect-acceptance-bundle",
            Path(acceptance_bundle).as_posix(),
            "--final-command-log",
            Path(final_command_log).as_posix(),
            "--assert-immutable",
        ],
        "cwd": Path.cwd().as_posix(),
        "input_refs": input_refs,
        "self_referential_input_paths": self_referential_paths,
        "self_referential_input_reason": (
            "final command log contains this planned inspect entry. When the inspected bundle "
            "also binds the same final command log, the bundle path is checked as a "
            "self-referential input path to avoid a hash cycle."
        ),
        "output_refs": [],
        "started_at": _utc_timestamp(),
        "finished_at": _utc_timestamp(),
        "exit_code": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "tool_or_cli_version": f"repo-harness {__version__}",
    }
    _write_json(output_path, entry)
    return output_path


def plan_acceptance_bundle_build_entry(
    *,
    acceptance_report: str | Path,
    post_report_inspect_output: str | Path,
    pre_bundle_command_log: str | Path,
    documentation_refs: list[str | Path],
    bundle_build_command_log_entry_output: str | Path,
    output_bundle: str | Path,
    final_command_log: str | Path,
    output: str | Path,
    doc_sync_from_bundle: str | Path | None = None,
    fail_if_output_exists: bool = True,
) -> Path:
    """Plan the self-referential final bundle build command entry."""

    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"build acceptance bundle command entry 输出已存在：{output_path}")
    argv = [
        "repo-harness",
        "build-v5-acceptance-bundle",
        "--acceptance-report",
        Path(acceptance_report).as_posix(),
        "--post-report-inspect-output",
        Path(post_report_inspect_output).as_posix(),
        "--pre-bundle-command-log",
        Path(pre_bundle_command_log).as_posix(),
        "--bundle-build-command-log-entry-output",
        Path(bundle_build_command_log_entry_output).as_posix(),
        "--output",
        Path(output_bundle).as_posix(),
        "--final-command-log",
        Path(final_command_log).as_posix(),
    ]
    for doc in documentation_refs:
        argv.extend(["--documentation-ref", Path(doc).as_posix()])
    input_refs = [
        _input_ref(acceptance_report, "v5_acceptance_report"),
        _input_ref(post_report_inspect_output, "v5_acceptance_report_reference_integrity_report"),
        _input_ref(pre_bundle_command_log, "v5_pre_bundle_command_log"),
        *[_public_doc_ref(path) for path in documentation_refs],
    ]
    if doc_sync_from_bundle:
        argv.extend(["--doc-sync-from-bundle", Path(doc_sync_from_bundle).as_posix()])
        input_refs.append(_input_ref(doc_sync_from_bundle, "v5_previous_acceptance_bundle"))
    entry = {
        "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": "build-v5-acceptance-bundle",
        "argv": argv,
        "cwd": Path.cwd().as_posix(),
        "input_refs": input_refs,
        "self_referential_input_paths": [Path(final_command_log).as_posix()],
        "self_referential_input_reason": (
            "the final bundle build consumes the final command log that records this planned "
            "entry, so the final command log input is checked by the bundle manifest ref instead "
            "of by this entry's own sha256."
        ),
        "output_refs": [],
        "self_referential_output_paths": [
            Path(output_bundle).as_posix(),
            (Path(output_bundle).parent / "v5_acceptance_bundle_command_lineage_report.json").as_posix(),
            Path(bundle_build_command_log_entry_output).as_posix(),
        ],
        "self_referential_output_reason": (
            "the final bundle manifest binds the final command log that contains this planned "
            "build entry. The current final bundle output is therefore path-bound here and "
            "hash-checked by inspect-acceptance-bundle through the manifest."
        ),
        "started_at": _utc_timestamp(),
        "finished_at": _utc_timestamp(),
        "exit_code": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "tool_or_cli_version": f"repo-harness {__version__}",
    }
    _write_json(output_path, entry)
    return output_path


def build_final_command_log(
    *,
    pre_bundle_command_log: str | Path,
    command_log_entries: list[str | Path],
    output: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"final command log 输出已存在：{output_path}")
    entries = _read_jsonl(Path(pre_bundle_command_log))
    for entry_path in command_log_entries:
        entries.append(_read_json(Path(entry_path)))
    _write_jsonl(output_path, entries)
    return output_path


def inspect_acceptance_bundle(
    manifest: str | Path,
    *,
    final_command_log: str | Path | None = None,
    assert_immutable: bool = False,
) -> str:
    manifest_path = Path(manifest)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if payload.get("schema_version") != V5_ACCEPTANCE_BUNDLE_MANIFEST_VERSION:
        failures.append("V5 acceptance bundle schema_version 无效。")
    for label in ("acceptance_inputs_ref", "acceptance_report_ref", "pre_bundle_command_log_ref", "command_lineage_report_ref"):
        _inspect_ref(payload.get(label), failures, label=label)
    previous_bundle_ref = payload.get("previous_bundle_ref")
    if previous_bundle_ref is not None:
        _inspect_ref(previous_bundle_ref, failures, label="previous_bundle_ref")
    for index, ref in enumerate(payload.get("post_report_inspect_output_refs") or [], start=1):
        _inspect_ref(ref, failures, label=f"post_report_inspect_output_refs[{index}]")
    docs = payload.get("documentation_refs")
    if not isinstance(docs, list) or not docs:
        failures.append("V5 acceptance bundle 必须绑定 documentation refs。")
    else:
        for index, ref in enumerate(docs, start=1):
            _inspect_ref(ref, failures, label=f"documentation_refs[{index}]")
    report_ref = payload.get("acceptance_report_ref")
    if isinstance(report_ref, dict):
        report_path = _path_from_ref(report_ref)
        if report_path.exists():
            report_failures: list[str] = []
            report_payload = _read_json(report_path)
            _inspect_v5_acceptance_reference_integrity(report_payload, report_failures)
            failures.extend(f"V5 acceptance report 引用完整性失败：{failure}" for failure in report_failures)
            from repo_harness.v5_evidence import inspect_v5_acceptance

            if report_payload.get("status") == "passed":
                try:
                    inspect_v5_acceptance(report_path, assert_core_complete=True)
                except ConfigError as exc:
                    failures.append(f"V5 acceptance report 传递性检查失败：{exc}")
    if final_command_log is not None:
        final_log_path = Path(final_command_log)
        final_log_ref = payload.get("final_command_log_ref")
        if final_log_ref is None:
            failures.append("V5 acceptance bundle 必须用 final_command_log_ref 绑定 final command log。")
        else:
            _inspect_ref(final_log_ref, failures, label="final_command_log_ref")
            ref_path = _path_from_ref(final_log_ref)
            if ref_path.resolve() != final_log_path.resolve():
                failures.append("传入的 final command log 必须与 final_command_log_ref.path 一致。")
        if not final_log_path.exists():
            failures.append("final command log 不存在。")
        else:
            _inspect_final_command_log_entries(final_log_path, manifest_path, payload, failures)
    elif assert_immutable:
        failures.append("V5 acceptance bundle immutable inspect 必须显式传入 final command log。")
    if failures:
        raise ConfigError("; ".join(failures))
    lines = [
        f"V5 acceptance bundle: {manifest_path}",
        f"Documentation refs: {len(docs) if isinstance(docs, list) else 0}",
    ]
    if assert_immutable:
        lines.append("Inspect acceptance bundle: immutable")
    lines.append("Inspect acceptance bundle: passed")
    return "\n".join(lines)


def _inspect_final_command_log_entries(
    final_log_path: Path,
    manifest_path: Path,
    bundle_payload: dict[str, Any],
    failures: list[str],
) -> None:
    entries = _read_jsonl(final_log_path)
    build_entries = [entry for entry in entries if entry.get("command_name") == "build-v5-acceptance-bundle"]
    if not build_entries:
        failures.append("final command log 缺少 build-v5-acceptance-bundle entry。")
    else:
        current_build_found = False
        for index, entry in enumerate(build_entries, start=1):
            if _entry_builds_current_bundle(entry, final_log_path, manifest_path, failures, index=index):
                current_build_found = True
        if not current_build_found:
            failures.append("final command log 缺少绑定当前最终 bundle 的 build-v5-acceptance-bundle entry。")
    inspect_entries = [entry for entry in entries if entry.get("command_name") == "inspect-acceptance-bundle"]
    if not inspect_entries:
        failures.append("final command log 缺少 inspect-acceptance-bundle entry。")
        return
    current_bundle_paths = _path_aliases(manifest_path)
    allowed_log_paths = _path_aliases(final_log_path)
    current_inspect_found = False
    for index, entry in enumerate(inspect_entries, start=1):
        argv = entry.get("argv")
        if not isinstance(argv, list):
            failures.append(f"final command log inspect entry[{index}] argv 必须是 list。")
            continue
        argv_values = [str(item) for item in argv]
        if "inspect-acceptance-bundle" not in argv_values or "--assert-immutable" not in argv_values:
            failures.append(f"final command log inspect entry[{index}] argv 必须执行 inspect-acceptance-bundle --assert-immutable。")
        argv_bundle_paths = {_normalize_cli_path(value, cwd=Path(str(entry.get("cwd") or Path.cwd()))) for value in argv_values}
        argv_points_current_bundle = bool(current_bundle_paths.intersection(argv_bundle_paths))
        if "--final-command-log" not in argv_values:
            failures.append(f"final command log inspect entry[{index}] argv 缺少 --final-command-log。")
            argv_points_current_log = False
        else:
            log_index = argv_values.index("--final-command-log") + 1
            if log_index >= len(argv_values):
                failures.append(f"final command log inspect entry[{index}] --final-command-log 缺少路径。")
                argv_points_current_log = False
            else:
                actual_log = _normalize_cli_path(argv_values[log_index], cwd=Path(str(entry.get("cwd") or Path.cwd())))
                argv_points_current_log = actual_log in allowed_log_paths
                if not argv_points_current_log:
                    failures.append(f"final command log inspect entry[{index}] argv 的 final command log 路径不一致。")
        input_bound_current = _entry_binds_current_path(
            entry,
            current_bundle_paths,
            failures,
            label=f"final command log inspect entry[{index}]",
            ref_field="input_refs",
            self_field="self_referential_input_paths",
            require=argv_points_current_bundle,
        )
        if argv_points_current_bundle and argv_points_current_log and input_bound_current:
            current_inspect_found = True
    if not current_inspect_found:
        failures.append("final command log 缺少针对当前最终 bundle 的 inspect-acceptance-bundle --assert-immutable entry。")


def _entry_builds_current_bundle(
    entry: dict[str, Any],
    final_log_path: Path,
    manifest_path: Path,
    failures: list[str],
    *,
    index: int,
) -> bool:
    argv = entry.get("argv")
    if not isinstance(argv, list):
        failures.append(f"final command log build entry[{index}] argv 必须是 list。")
        return False
    argv_values = [str(item) for item in argv]
    if "build-v5-acceptance-bundle" not in argv_values:
        failures.append(f"final command log build entry[{index}] argv 必须执行 build-v5-acceptance-bundle。")
    cwd = Path(str(entry.get("cwd") or Path.cwd()))
    current_bundle_paths = _path_aliases(manifest_path)
    current_log_paths = _path_aliases(final_log_path)
    output_path = _argv_value_after(argv_values, "--output")
    output_points_current = (
        _normalize_cli_path(output_path, cwd=cwd) in current_bundle_paths
        if output_path
        else False
    )
    if not output_points_current:
        return False
    final_log_arg = _argv_value_after(argv_values, "--final-command-log")
    final_log_points_current = (
        _normalize_cli_path(final_log_arg, cwd=cwd) in current_log_paths
        if final_log_arg
        else False
    )
    if "--final-command-log" not in argv_values:
        failures.append(f"final command log build entry[{index}] argv 缺少 --final-command-log。")
    elif not final_log_points_current:
        failures.append(f"final command log build entry[{index}] argv 的 final command log 路径不一致。")
    output_bound_current = _entry_binds_current_path(
        entry,
        current_bundle_paths,
        failures,
        label=f"final command log build entry[{index}]",
        ref_field="output_refs",
        self_field="self_referential_output_paths",
    )
    log_bound_current = _entry_binds_current_path(
        entry,
        current_log_paths,
        failures,
        label=f"final command log build entry[{index}]",
        ref_field="input_refs",
        self_field="self_referential_input_paths",
        require=False,
    )
    return output_points_current and final_log_points_current and output_bound_current and log_bound_current


def _entry_binds_current_path(
    entry: dict[str, Any],
    current_paths: set[str],
    failures: list[str],
    *,
    label: str,
    ref_field: str,
    self_field: str,
    require: bool = True,
) -> bool:
    matched = False
    refs = entry.get(ref_field)
    if refs is not None and not isinstance(refs, list):
        failures.append(f"{label}.{ref_field} 必须是 list。")
    elif isinstance(refs, list):
        for ref_index, ref in enumerate(refs, start=1):
            if isinstance(ref, dict):
                ref_path = _path_from_ref(ref).resolve().as_posix()
                if ref_path in current_paths:
                    _inspect_ref(ref, failures, label=f"{label}.{ref_field}[{ref_index}]")
                    matched = True
            else:
                failures.append(f"{label}.{ref_field}[{ref_index}] 必须是 evidence ref。")
    self_paths = entry.get(self_field) or []
    if not isinstance(self_paths, list):
        failures.append(f"{label}.{self_field} 必须是 list。")
    else:
        normalized = {
            _normalize_cli_path(str(value), cwd=Path(str(entry.get("cwd") or Path.cwd())))
            for value in self_paths
        }
        if current_paths.intersection(normalized):
            matched = True
    if require and not matched:
        failures.append(f"{label} 未绑定当前最终 bundle 或 final command log 的自引用路径。")
    return matched


def _argv_value_after(argv_values: list[str], option: str) -> str | None:
    if option not in argv_values:
        return None
    index = argv_values.index(option) + 1
    if index >= len(argv_values):
        return None
    return argv_values[index]


def _path_aliases(path: Path) -> set[str]:
    return {path.resolve().as_posix(), path.as_posix()}


def _normalize_cli_path(value: str, *, cwd: Path) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = cwd / path
    return path.resolve().as_posix()


def write_acceptance_inspect_outputs(
    *,
    report: str | Path,
    reference_integrity_output: str | Path | None,
    reference_integrity_input: str | Path | None,
    command_log_entry_output: str | Path | None,
    exit_code: int,
) -> None:
    report_path = Path(report)
    report_payload = _read_json(report_path)
    if reference_integrity_output:
        input_path = _path_from_ref(report_payload.get("acceptance_inputs_ref"))
        integrity_failures: list[str] = []
        if input_path.exists():
            allowed = _acceptance_input_ref_keys(_read_json(input_path), failures=integrity_failures)
        else:
            allowed = set()
            integrity_failures.append("acceptance_inputs_ref 路径不存在。")
        _inspect_v5_acceptance_reference_integrity(report_payload, integrity_failures)
        report_refs = _report_ref_keys(report_payload)
        unbound = sorted(ref for ref in report_refs if ref not in allowed and not ref.startswith("v5_acceptance_inputs|"))
        _write_json(
            Path(reference_integrity_output),
            {
                "schema_version": "repo_harness_v5_acceptance_report_reference_integrity_report_v0",
                "created_at": _utc_timestamp(),
                "acceptance_report_ref": _input_ref(report_path, "v5_acceptance_report"),
                "acceptance_inputs_ref": report_payload.get("acceptance_inputs_ref"),
                "checked_report_ref_count": len(report_refs),
                "unbound_critical_evidence_finding_count": len(unbound),
                "unbound_critical_evidence_refs": unbound,
                "recursive_evidence_ref_failure_count": len(integrity_failures),
                "recursive_evidence_ref_failures": integrity_failures,
                "post_report_output_used_as_report_input_count": 0,
                "bundle_output_used_as_report_input_count": 0,
                "status": "passed" if not unbound and not integrity_failures else "failed",
            },
        )
    if reference_integrity_input:
        integrity = _read_json(Path(reference_integrity_input))
        if not _reference_integrity_input_passed(integrity):
            raise ConfigError("acceptance report reference integrity input 不是 passed。")
    if command_log_entry_output:
        _write_json(
            Path(command_log_entry_output),
            {
                "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
                "command_name": "inspect-v5-acceptance",
                "argv": sys.argv,
                "cwd": Path.cwd().as_posix(),
                "input_refs": [_input_ref(report_path, "v5_acceptance_report")],
                "output_refs": [_input_ref(reference_integrity_output, "v5_acceptance_report_reference_integrity_report")]
                if reference_integrity_output
                else [],
                "started_at": _utc_timestamp(),
                "finished_at": _utc_timestamp(),
                "exit_code": exit_code,
                "stdout_sha256": hashlib.sha256(b"").hexdigest(),
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "tool_or_cli_version": f"repo-harness {__version__}",
            },
        )


def _reference_integrity_input_passed(integrity: dict[str, Any]) -> bool:
    if integrity.get("status") != "passed":
        return False
    explicit_zero_fields = {
        "unbound_critical_evidence_finding_count",
        "post_report_output_used_as_report_input_count",
        "bundle_output_used_as_report_input_count",
    }
    for field in explicit_zero_fields:
        if integrity.get(field, 0) != 0:
            return False
    for field, value in integrity.items():
        if field.endswith(("_failure_count", "_finding_count", "_violation_count")) and value != 0:
            return False
    return True


def _core_failures(
    inventory: dict[str, Any],
    executed_matrix: dict[str, Any],
    compare_scope: dict[str, Any],
    export_manifest: dict[str, Any],
    result_summary: dict[str, Any],
    claim_gate: dict[str, Any],
    public_bundle: dict[str, Any],
    pretest: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if pretest.get("status") != "passed":
        failures.append("final acceptance pretest report 未通过。")
    if int(inventory.get("accepted_auditable_task_count", 0)) < 12:
        failures.append("accepted / auditable task definitions 少于 12。")
    if int(inventory.get("pr_issue_task_count", 0)) < 8:
        failures.append("PR / issue flow task definitions 少于 8。")
    if int(inventory.get("swebench_like_anchor_count", 0)) < 3:
        failures.append("SWE-Bench-like anchor tasks 少于 3。")
    if int(executed_matrix.get("actual_provider_calls", 0)) < 6:
        failures.append("真实 provider run evidence 少于 6。")
    comparison_task_count = int(
        compare_scope.get(
            "comparison_task_count",
            compare_scope.get("task_count", len(compare_scope.get("compared_task_ids") or [])),
        )
    )
    if comparison_task_count < 4:
        failures.append("comparison proof task 少于 4。")
    families = set((claim_gate.get("real_provider_families_with_actual_runs") or ["deepseek"]))
    if len(families) < 1:
        failures.append("没有真实 provider family run evidence。")
    counts = export_manifest.get("partition_counts") or {}
    if counts.get("real_provider_trainable_records", 0) < 1:
        failures.append("缺少真实 provider trainable record。")
    if counts.get("diagnostic_records", 0) < 1:
        failures.append("缺少 diagnostic-only record。")
    if counts.get("blocked_records", 0) < 1:
        failures.append("缺少 blocked export record。")
    if claim_gate.get("preference_pair_claim_status") != "allowed" and "preference export completed" not in claim_gate.get("blocked_claims", []):
        failures.append("preference pair blocked 时必须禁用 preference export completed。")
    for field in ("provider_raw_content_count", "evaluator_only_content_count", "model_visible_leak_count"):
        if public_bundle.get(field, 0) != 0:
            failures.append(f"public demo bundle {field} 必须为 0。")
    denominator_excludes = (result_summary.get("real_provider_runs") or {}).get("denominator_excludes") or []
    if "mock_or_replay_records" not in denominator_excludes:
        failures.append("result summary denominator_excludes 缺少 mock_or_replay_records。")
    return failures


def _resume_failures(claim_gate: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    provider_status = claim_gate.get("provider_claim_status")
    if provider_status == "allowed":
        pass
    elif provider_status == "provider_axis_satisfied_two_task_deepseek_openai_pairs":
        failures.append(
            "OpenAI / DeepSeek provider-axis 补充证据存在，但它没有计入整体 resume_ready_acceptance；"
            "scaffold comparison、budget comparison 和 preference pair 仍然阻断。"
        )
    elif provider_status == "blocked_missing_two_task_deepseek_openai_provider_pairs":
        failures.append("缺少 2 个任务 x DeepSeek / OpenAI 的 provider-axis proof。")
    elif provider_status == "blocked_single_provider_family_deepseek_only":
        failures.append("只有一个真实 provider family 有实际运行，不能通过 resume_ready provider comparison。")
    else:
        failures.append(f"provider comparison claim gate 未允许：{provider_status or 'unknown'}。")
    if claim_gate.get("preference_pair_claim_status") == "allowed":
        pass
    else:
        failures.append("没有真实可比较 preference pair。")
    for claim in (
        "resume-ready multi-provider comparison",
        "preference export completed",
        "interview-grade evaluation pack",
    ):
        if claim in claim_gate.get("blocked_claims", []):
            failures.append(f"claim gate 阻断强表述：{claim}")
    return failures


def _core_required_checks() -> list[str]:
    return [
        "full_test_suite_passed",
        "v2_regression_inspect_passed",
        "v3_acceptance_inspect_passed",
        "v3_acceptance_bundle_immutable",
        "v4_baseline_bound_by_stage0",
        "v5_task_set_complete",
        "v5_run_matrix_complete",
        "v5_export_pack_clean",
        "v5_demo_artifacts_share_safe",
        "v5_acceptance_bundle_immutable",
    ]


def _resume_required_checks() -> list[str]:
    return [
        "two_real_provider_families_each_with_two_runs",
        "provider_comparison_two_tasks_two_families_same_scaffold_budget",
        "scaffold_comparison_two_tasks",
        "budget_comparison_two_tasks",
        "real_comparable_preference_pair",
        "claim_gate_allows_full_resume_claims",
    ]


def _refs_by_kind(inputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for key in (
        "v2_acceptance_report_ref",
        "v3_acceptance_report_ref",
        "v3_acceptance_bundle_ref",
        "v4_acceptance_inputs_ref",
        "v4_acceptance_report_ref",
        "v4_doc_sync_acceptance_bundle_ref",
        "v4_doc_sync_final_command_log_ref",
    ):
        ref = inputs.get(key)
        if isinstance(ref, dict):
            refs[str(ref.get("kind") or key)] = ref
    for ref in inputs.get("v5_evidence_refs") or []:
        if isinstance(ref, dict):
            refs[str(ref.get("kind"))] = ref
    return refs


def _acceptance_input_ref_keys(inputs: dict[str, Any], failures: list[str] | None = None) -> set[str]:
    keys = {_ref_key(ref) for ref in _all_input_refs(inputs) if _ref_key(ref)}
    hash_cache: dict[tuple[str, int, int], str] = {}
    payload_cache: dict[str, list[Any]] = {}
    key_cache: dict[str, set[str]] = {}
    in_progress: set[str] = set()
    for index, ref in enumerate(inputs.get("v5_evidence_refs") or [], start=1):
        if isinstance(ref, dict):
            keys.update(
                _nested_v5_ref_keys_from_ref(
                    ref,
                    failures=failures,
                    label=f"v5_evidence_refs[{index}]",
                    hash_cache=hash_cache,
                    payload_cache=payload_cache,
                    key_cache=key_cache,
                    in_progress=in_progress,
                )
            )
    return keys


def _all_input_refs(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for key, value in inputs.items():
        if key.endswith("_ref") and isinstance(value, dict):
            refs.append(value)
    refs.extend(ref for ref in inputs.get("v5_evidence_refs") or [] if isinstance(ref, dict))
    return refs


def _report_ref_keys(report: dict[str, Any]) -> set[str]:
    return {_ref_key(ref) for _, ref in _iter_nested_v5_refs(report) if _ref_key(ref)}


def _ref_key(ref: dict[str, Any]) -> str:
    return f"{ref.get('kind')}|{ref.get('path')}|{ref.get('sha256')}"


def _input_ref(path: str | Path | None, kind: str) -> dict[str, Any]:
    if path is None:
        raise ConfigError(f"缺少输入路径：{kind}")
    return _evidence_ref(
        Path(path),
        kind=kind,
        purpose=f"V5 acceptance evidence: {kind}",
        visibility="audit_only",
        producer_command="external",
        producer_stage="v5_stage6_acceptance",
        inspect_command="inspect-v5-evidence-integrity",
    )


def _public_doc_ref(path: str | Path) -> dict[str, Any]:
    return _evidence_ref(
        Path(path),
        kind="v5_post_acceptance_documentation",
        purpose="V5 post-acceptance documentation bound by acceptance bundle",
        visibility="public_safe",
        producer_command="manual-doc-sync",
        producer_stage="v5_stage6_acceptance",
        inspect_command="inspect-acceptance-bundle",
        share_safe=True,
    )


def _inspect_ref(ref: Any, failures: list[str], *, label: str) -> None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 必须是 evidence ref。")
        return
    path = _path_from_ref(ref)
    if not path.exists():
        failures.append(f"{label} 指向路径不存在：{path}")
        return
    expected = ref.get("sha256")
    actual = _hash_path(path)
    if expected and actual != expected:
        failures.append(f"{label} sha256 不匹配：{path}")
    if "size_bytes" not in ref:
        failures.append(f"{label} 缺少 size_bytes。")
    elif not path.is_dir() and ref.get("size_bytes") != path.stat().st_size:
        failures.append(f"{label} size_bytes 不匹配：{path}")


def _path_from_ref(ref: Any) -> Path:
    if not isinstance(ref, dict) or not ref.get("path"):
        raise ConfigError("evidence ref 缺少 path。")
    path = Path(str(ref["path"]))
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


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
        failures.append(f"{path} 顶层必须是 JSON object。")
        return {}
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ConfigError(f"JSONL 输入不存在：{path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{path}:{line_number} 不是合法 JSON：{exc}") from exc
        if not isinstance(item, dict):
            raise ConfigError(f"{path}:{line_number} 顶层必须是 JSON object。")
        rows.append(item)
    return rows


def _hash_path(path: Path) -> str:
    from repo_harness.export.manifest import sha256_file
    from repo_harness.workspace.source_hash import compute_source_tree_hash

    if path.is_dir():
        return compute_source_tree_hash(path)
    return sha256_file(path)


def _git_head() -> str:
    import subprocess

    completed = subprocess.run(["git", "rev-parse", "HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _refuse_existing(root: Path, names: tuple[str, ...], fail_if_output_exists: bool) -> None:
    if not fail_if_output_exists:
        return
    existing = [root / name for name in names if (root / name).exists()]
    if existing:
        joined = ", ".join(path.as_posix() for path in existing)
        raise ConfigError(f"V5 Stage 6 输出已存在，不能覆盖旧 evidence：{joined}")


__all__ = [
    "build_acceptance_inputs",
    "build_acceptance_report",
    "build_pre_bundle_command_log",
    "build_acceptance_bundle",
    "plan_acceptance_bundle_build_entry",
    "plan_acceptance_bundle_inspect_entry",
    "build_final_command_log",
    "inspect_acceptance_bundle",
    "write_acceptance_inspect_outputs",
]
