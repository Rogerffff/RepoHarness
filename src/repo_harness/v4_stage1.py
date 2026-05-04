"""V4 schema, inspect command skeletons, and acceptance skeleton."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION,
    V4_ACCEPTANCE_INPUTS_VERSION,
    V4_ACCEPTANCE_REPORT_VERSION,
    V4_AGENT_RUN_INTEGRATION_REPORT_VERSION,
    V4_ALLOWLIST_POLICY_VERSION,
    V4_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
    V4_BATCH_RESUME_REPORT_VERSION,
    V4_BUDGET_CONTROL_REPORT_VERSION,
    V4_CARDS_MANIFEST_VERSION,
    V4_CHECKPOINT_STATE_REPORT_VERSION,
    V4_CONTAMINATION_SCAN_REPORT_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
    V4_EXPORT_QUALITY_MANIFEST_VERSION,
    V4_LEASE_STATE_REPORT_VERSION,
    V4_RESOURCE_LOCK_REPORT_VERSION,
    V4_RESOURCE_USAGE_REPORT_VERSION,
    V4_RETRY_POLICY_REPORT_VERSION,
    V4_REGRESSION_EVIDENCE_REPORT_VERSION,
    V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
    V4_RUN_SELECTION_MANIFEST_VERSION,
    V4_RUN_SELECTION_QUERY_REPORT_VERSION,
    V4_TASK_FREEZE_MANIFEST_VERSION,
    V4_TASK_VALIDITY_REPORT_VERSION,
    V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
    V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
    V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION,
    V4_WORKER_RUN_LOG_ENTRY_VERSION,
)
from repo_harness.v4_visibility import (
    V4_CARD_CLAIM_DENYLIST_VERSION,
    v4_card_claim_denylist_sha256,
    v4_contamination_denylist_sha256,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


V4_REQUIRED_ACCEPTANCE_INPUT_CATEGORIES = (
    "run_selection_manifest",
    "v2_acceptance",
    "v3_acceptance",
    "v3_acceptance_bundle",
    "real_repository_regression",
    "swebench_like_regression",
    "implementation_inputs",
    "rollout_queue",
    "lease_state",
    "retry_policy",
    "budget_control",
    "resource_locks",
    "resource_usage",
    "batch_resume",
    "run_selection_query",
    "task_freeze",
    "task_validity",
    "tool_contract",
    "tool_lifecycle",
    "agent_run_integration",
    "trajectory_store",
    "export_quality",
    "cards",
    "contamination_scan",
    "command_log",
    "pre_acceptance_docs",
)


V4_FINAL_ACCEPTANCE_COMMAND_LOG_REQUIRED_COMMANDS = (
    "inspect-v4-acceptance",
    "build-v4-acceptance-bundle",
    "inspect-acceptance-bundle",
)


V4_REQUIRED_FINAL_ACCEPTANCE_ROLES = (
    "v3_regression",
    "v2_regression",
    "real_repository_regression",
    "swebench_like_regression",
    "v4_pr_issue_task_freeze",
    "v4_swebench_like_task_freeze",
    "v4_rollout_orchestration",
    "v4_rollout_resume",
    "v4_agent_run_integration",
    "v4_export_quality",
    "v4_tool_lifecycle_audit",
    "v4_cards",
)


V4_ARTIFACT_INSPECT_TRACKING_ROWS: tuple[dict[str, Any], ...] = (
    {
        "scope": "Stage 0 input freeze",
        "artifacts": [
            "v4_implementation_input_manifest.json",
            "v4_feasibility_input_binding.json",
            "v4_baseline_check_report.json",
        ],
        "inspect_command": "inspect-v4-implementation-inputs",
    },
    {
        "scope": "P0-1 queue",
        "artifacts": ["rollout_queue_manifest.json", "worker_run_log.jsonl"],
        "inspect_command": "inspect-rollout-queue",
    },
    {"scope": "P0-1 lease", "artifacts": ["lease_state_report.json"], "inspect_command": "inspect-rollout-leases"},
    {"scope": "P0-1 retry", "artifacts": ["retry_policy_report.json"], "inspect_command": "inspect-rollout-retry"},
    {"scope": "P0-1 budget", "artifacts": ["budget_control_report.json"], "inspect_command": "inspect-rollout-budget"},
    {"scope": "P0-1 resource locks", "artifacts": ["resource_lock_report.json"], "inspect_command": "inspect-resource-locks"},
    {"scope": "P0-1 resource usage", "artifacts": ["resource_usage_report.json"], "inspect_command": "inspect-resource-usage"},
    {
        "scope": "P0-1 resume",
        "artifacts": ["batch_resume_report.json", "checkpoint_state_report.json"],
        "inspect_command": "inspect-rollout-resume",
    },
    {"scope": "P0-1 selection", "artifacts": ["run_selection_query_report.json"], "inspect_command": "inspect-run-selection-query"},
    {
        "scope": "P0-2 task freeze",
        "artifacts": [
            "pr_task_construction_manifest.json",
            "source_archive_manifest.json",
            "source_materialization_report.json",
            "baseline_verifier_report.json",
            "post_patch_verifier_report.json",
            "flaky_detection_report.json",
            "environment_stability_report.json",
            "dependency_cache_report.json",
            "license_provenance_review_report.json",
            "use_boundary_review_report.json",
            "task_validity_report.json",
            "generated_task_definition.jsonl",
            "adapter_visible_task_input_manifest.json",
            "evaluator_only_evidence_manifest.json",
            "task_visibility_scan_report.json",
        ],
        "inspect_command": "inspect-v4-task-freeze",
    },
    {
        "scope": "P0-2 task validity",
        "artifacts": [
            "source_materialization_report.json",
            "baseline_verifier_report.json",
            "post_patch_verifier_report.json",
            "flaky_detection_report.json",
            "environment_stability_report.json",
            "dependency_cache_report.json",
            "license_provenance_review_report.json",
            "use_boundary_review_report.json",
            "task_validity_report.json",
        ],
        "inspect_command": "inspect-v4-task-validity",
    },
    {
        "scope": "Final regression evidence",
        "artifacts": [
            "real_repository_regression_report.json",
            "swebench_like_regression_report.json",
        ],
        "inspect_command": "inspect-v4-acceptance",
        "secondary_inspect_commands": ["inspect-v4-inputs"],
    },
    {
        "scope": "P1-2 tool contract",
        "artifacts": [
            "permission_policy_snapshot.json",
            "hook_policy_snapshot.json",
            "mcp_policy_snapshot.json",
            "tool_contract_v4_snapshot.json",
        ],
        "inspect_command": "inspect-v4-tool-contract",
    },
    {
        "scope": "P1-2 lifecycle",
        "artifacts": ["permission_decision_trace.jsonl", "tool_lifecycle_trace.jsonl", "hook_audit_report.json"],
        "inspect_command": "inspect-v4-tool-lifecycle",
    },
    {
        "scope": "Stage 5 run integration",
        "artifacts": [
            "v4_agent_run_integration_report.json",
            "runspec_metadata_report.json",
            "final_verifier_boundary_report.json",
            "prepared_messages_binding_report.json",
            "interrupted_run_recovery_report.json",
            "trajectory_store_integrity_report.json",
        ],
        "inspect_command": "inspect-v4-agent-run-integration",
    },
    {
        "scope": "Stage 5 trajectory store",
        "artifacts": [
            "transcript.jsonl",
            "events.jsonl",
            "artifacts.json",
            "run_config_facts.json",
            "run_metadata.json",
            "final.patch",
            "no_patch_fact.json",
            "interrupted_run_facts.json",
            "crash_facts.json",
            "trajectory_store_integrity_report.json",
        ],
        "inspect_command": "inspect-v4-trajectory-store",
    },
    {
        "scope": "P0-3 export quality",
        "artifacts": [
            "trajectory_quality_manifest.json",
            "sample_tier_manifest.json",
            "failure_dataset.jsonl",
            "packing_manifest.json",
            "reward_audit_report.json",
            "reward_hacking_risk_audit_report.json",
            "patch_quality_report.json",
            "test_overfitting_risk_audit_report.json",
            "preference_pair_trainability_report.json",
            "blocked_pair_report.json",
        ],
        "inspect_command": "inspect-v4-export-quality",
    },
    {
        "scope": "P1-4 cards",
        "artifacts": [
            "dataset_card.md",
            "dataset_card.json",
            "run_card.json",
            "export_card.json",
            "provenance_summary.json",
            "contamination_scan_summary.json",
            "repro_command_index.json",
        ],
        "inspect_command": "inspect-v4-cards",
    },
    {
        "scope": "Global contamination scan",
        "artifacts": [
            "contamination_scan_report.json",
            "task_visibility_scan_report.json",
            "contamination_scan_summary.json",
        ],
        "inspect_command": "inspect-v4-contamination-scan",
    },
    {
        "scope": "Final acceptance",
        "artifacts": [
            "run_selection_manifest.json",
            "v4_acceptance_inputs.json",
            "v4_acceptance_report.json",
            "acceptance_bundle_manifest.json",
            "acceptance_command_log.jsonl",
        ],
        "inspect_command": "inspect-v4-acceptance",
        "secondary_inspect_commands": ["inspect-v4-inputs", "inspect-acceptance-bundle"],
    },
)


@dataclass(frozen=True)
class V4ArtifactSetSpec:
    command_name: str
    input_kind: str
    complete_label: str
    required_files: tuple[tuple[str, str | None], ...] = ()
    jsonl_files: tuple[tuple[str, str | None], ...] = ()
    direct_schema_version: str | None = None
    required_fields: tuple[str, ...] = ()
    referenced_artifacts: tuple[str, ...] = ()


V4_ARTIFACT_SET_SPECS: dict[str, V4ArtifactSetSpec] = {
    "rollout_queue": V4ArtifactSetSpec(
        command_name="inspect-rollout-queue",
        input_kind="directory",
        complete_label="complete",
        required_files=(("rollout_queue_manifest.json", V4_ROLLOUT_QUEUE_MANIFEST_VERSION),),
        jsonl_files=(("worker_run_log.jsonl", V4_WORKER_RUN_LOG_ENTRY_VERSION),),
    ),
    "rollout_leases": V4ArtifactSetSpec(
        command_name="inspect-rollout-leases",
        input_kind="directory",
        complete_label="complete",
        required_files=(("lease_state_report.json", V4_LEASE_STATE_REPORT_VERSION),),
    ),
    "rollout_retry": V4ArtifactSetSpec(
        command_name="inspect-rollout-retry",
        input_kind="directory",
        complete_label="complete",
        required_files=(("retry_policy_report.json", V4_RETRY_POLICY_REPORT_VERSION),),
    ),
    "rollout_budget": V4ArtifactSetSpec(
        command_name="inspect-rollout-budget",
        input_kind="directory",
        complete_label="complete",
        required_files=(("budget_control_report.json", V4_BUDGET_CONTROL_REPORT_VERSION),),
    ),
    "resource_locks": V4ArtifactSetSpec(
        command_name="inspect-resource-locks",
        input_kind="directory",
        complete_label="complete",
        required_files=(("resource_lock_report.json", V4_RESOURCE_LOCK_REPORT_VERSION),),
    ),
    "resource_usage": V4ArtifactSetSpec(
        command_name="inspect-resource-usage",
        input_kind="directory",
        complete_label="complete",
        required_files=(("resource_usage_report.json", V4_RESOURCE_USAGE_REPORT_VERSION),),
    ),
    "rollout_resume": V4ArtifactSetSpec(
        command_name="inspect-rollout-resume",
        input_kind="directory",
        complete_label="complete",
        required_files=(
            ("batch_resume_report.json", V4_BATCH_RESUME_REPORT_VERSION),
            ("checkpoint_state_report.json", V4_CHECKPOINT_STATE_REPORT_VERSION),
        ),
    ),
    "run_selection_query": V4ArtifactSetSpec(
        command_name="inspect-run-selection-query",
        input_kind="file",
        complete_label="complete",
        direct_schema_version=V4_RUN_SELECTION_QUERY_REPORT_VERSION,
        required_fields=("query_predicate", "input_manifest_hash"),
    ),
    "task_freeze": V4ArtifactSetSpec(
        command_name="inspect-v4-task-freeze",
        input_kind="file",
        complete_label="complete",
        direct_schema_version=V4_TASK_FREEZE_MANIFEST_VERSION,
        referenced_artifacts=(
            "pr_task_construction_manifest.json",
            "source_archive_manifest.json",
            "source_materialization_report.json",
            "baseline_verifier_report.json",
            "post_patch_verifier_report.json",
            "flaky_detection_report.json",
            "environment_stability_report.json",
            "dependency_cache_report.json",
            "license_provenance_review_report.json",
            "use_boundary_review_report.json",
            "task_validity_report.json",
            "generated_task_definition.jsonl",
            "adapter_visible_task_input_manifest.json",
            "evaluator_only_evidence_manifest.json",
            "task_visibility_scan_report.json",
        ),
    ),
    "task_validity": V4ArtifactSetSpec(
        command_name="inspect-v4-task-validity",
        input_kind="file",
        complete_label="complete",
        direct_schema_version=V4_TASK_VALIDITY_REPORT_VERSION,
        referenced_artifacts=(
            "source_materialization_report.json",
            "baseline_verifier_report.json",
            "post_patch_verifier_report.json",
            "flaky_detection_report.json",
            "environment_stability_report.json",
            "dependency_cache_report.json",
            "license_provenance_review_report.json",
            "use_boundary_review_report.json",
        ),
    ),
    "tool_contract": V4ArtifactSetSpec(
        command_name="inspect-v4-tool-contract",
        input_kind="directory",
        complete_label="frozen",
        required_files=(
            ("permission_policy_snapshot.json", None),
            ("hook_policy_snapshot.json", None),
            ("mcp_policy_snapshot.json", None),
            ("tool_contract_v4_snapshot.json", V4_TOOL_CONTRACT_SNAPSHOT_VERSION),
        ),
    ),
    "tool_lifecycle": V4ArtifactSetSpec(
        command_name="inspect-v4-tool-lifecycle",
        input_kind="directory",
        complete_label="complete",
        required_files=(("hook_audit_report.json", None),),
        jsonl_files=(
            ("permission_decision_trace.jsonl", None),
            ("tool_lifecycle_trace.jsonl", V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION),
        ),
    ),
    "agent_run_integration": V4ArtifactSetSpec(
        command_name="inspect-v4-agent-run-integration",
        input_kind="directory",
        complete_label="complete",
        required_files=(
            ("v4_agent_run_integration_report.json", V4_AGENT_RUN_INTEGRATION_REPORT_VERSION),
            ("runspec_metadata_report.json", None),
            ("final_verifier_boundary_report.json", None),
            ("prepared_messages_binding_report.json", None),
            ("interrupted_run_recovery_report.json", None),
            ("trajectory_store_integrity_report.json", V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION),
        ),
    ),
    "trajectory_store": V4ArtifactSetSpec(
        command_name="inspect-v4-trajectory-store",
        input_kind="directory",
        complete_label="readable",
        required_files=(
            ("artifacts.json", None),
            ("run_config_facts.json", None),
            ("run_metadata.json", None),
            ("trajectory_store_integrity_report.json", V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION),
        ),
        jsonl_files=(("transcript.jsonl", None), ("events.jsonl", None)),
    ),
    "export_quality": V4ArtifactSetSpec(
        command_name="inspect-v4-export-quality",
        input_kind="directory",
        complete_label="complete",
        required_files=(
            ("trajectory_quality_manifest.json", V4_EXPORT_QUALITY_MANIFEST_VERSION),
            ("sample_tier_manifest.json", None),
            ("packing_manifest.json", None),
            ("reward_audit_report.json", None),
            ("reward_hacking_risk_audit_report.json", None),
            ("patch_quality_report.json", None),
            ("test_overfitting_risk_audit_report.json", None),
            ("preference_pair_trainability_report.json", None),
            ("blocked_pair_report.json", None),
        ),
        jsonl_files=(("failure_dataset.jsonl", None),),
    ),
    "cards": V4ArtifactSetSpec(
        command_name="inspect-v4-cards",
        input_kind="directory",
        complete_label="complete",
        required_files=(
            ("cards_manifest.json", V4_CARDS_MANIFEST_VERSION),
            ("dataset_card.md", None),
            ("dataset_card.json", None),
            ("run_card.json", None),
            ("export_card.json", None),
            ("provenance_summary.json", None),
            ("contamination_scan_summary.json", None),
            ("repro_command_index.json", None),
        ),
    ),
    "contamination_scan": V4ArtifactSetSpec(
        command_name="inspect-v4-contamination-scan",
        input_kind="file",
        complete_label="clean",
        direct_schema_version=V4_CONTAMINATION_SCAN_REPORT_VERSION,
        required_fields=(
            "clean",
            "findings",
            "denylist_version",
            "denylist_sha256",
            "allowlist_policy_version",
            "card_claim_denylist_version",
            "card_claim_denylist_sha256",
        ),
        referenced_artifacts=("task_visibility_scan_report.json", "contamination_scan_summary.json"),
    ),
}


def inspect_v4_artifact_set(
    spec_id: str,
    path: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    spec = V4_ARTIFACT_SET_SPECS[spec_id]
    target = Path(path)
    failures: list[str] = []
    if spec.input_kind == "directory":
        if not target.exists() or not target.is_dir():
            failures.append(f"{spec.command_name} 输入目录不存在：{target}")
        for name, schema_version in spec.required_files:
            file_path = target / name
            if schema_version is None and file_path.suffix.lower() not in {".json"}:
                if not file_path.exists():
                    failures.append(f"{name} 不存在：{file_path}")
                continue
            payload = _read_json_for_inspect(file_path, failures)
            if file_path.exists():
                _inspect_schema_version(payload, schema_version, failures, label=name)
        for name, schema_version in spec.jsonl_files:
            _inspect_jsonl_file(target / name, schema_version, failures, label=name)
    else:
        payload = _read_json_for_inspect(target, failures)
        if target.exists():
            _inspect_schema_version(payload, spec.direct_schema_version, failures, label=target.name)
            for field in spec.required_fields:
                if field not in payload:
                    failures.append(f"{target.name} 缺少必需字段：{field}")
            _inspect_embedded_artifact_refs(
                payload,
                expected_names=spec.referenced_artifacts,
                failures=failures,
                label=target.name,
            )
            if spec_id == "contamination_scan":
                _inspect_v4_contamination_scan_report(payload, failures)

    lines = [
        f"{spec.command_name}: {target}",
        f"Input kind: {spec.input_kind}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append(f"{spec.command_name}: {spec.complete_label}")
    lines.append(f"{spec.command_name}: passed")
    return "\n".join(lines)


def _inspect_v4_contamination_scan_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("clean") is not True:
        failures.append("V4 contamination scan report clean 必须为 true。")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        failures.append("V4 contamination scan report findings 必须是 list。")
    elif findings:
        failures.append("V4 contamination scan report findings 必须为空。")
    if payload.get("denylist_version") != V4_CONTAMINATION_DENYLIST_VERSION:
        failures.append("V4 contamination scan report denylist_version 不匹配。")
    if payload.get("denylist_sha256") != v4_contamination_denylist_sha256():
        failures.append("V4 contamination scan report denylist_sha256 不匹配。")
    if payload.get("allowlist_policy_version") != V4_ALLOWLIST_POLICY_VERSION:
        failures.append("V4 contamination scan report allowlist_policy_version 不匹配。")
    if payload.get("card_claim_denylist_version") != V4_CARD_CLAIM_DENYLIST_VERSION:
        failures.append("V4 contamination scan report card_claim_denylist_version 不匹配。")
    if payload.get("card_claim_denylist_sha256") != v4_card_claim_denylist_sha256():
        failures.append("V4 contamination scan report card_claim_denylist_sha256 不匹配。")


def _inspect_v4_command_log(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"acceptance_command_log 不存在：{path}")
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        failures.append("acceptance_command_log 必须至少包含一条记录。")
        return
    for index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"acceptance_command_log 第 {index} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"acceptance_command_log 第 {index} 行顶层必须是 object。")
            continue
        if record.get("schema_version") != "repo_harness_command_log_entry_v4_v0":
            failures.append(f"acceptance_command_log 第 {index} 行 schema_version 不匹配。")
        for field in ("command_name", "argv", "cwd", "tool_or_cli_version", "started_at", "finished_at"):
            if not record.get(field):
                failures.append(f"acceptance_command_log 第 {index} 行缺少 {field}。")
        if record.get("exit_code") is None and not record.get("structured_skip_reason"):
            failures.append(f"acceptance_command_log 第 {index} 行缺少 exit_code 或 structured skip reason。")
        for refs_field in ("input_refs", "output_refs"):
            refs = record.get(refs_field)
            if refs is None:
                failures.append(f"acceptance_command_log 第 {index} 行缺少 {refs_field}。")
                continue
            if not isinstance(refs, list):
                failures.append(f"acceptance_command_log 第 {index} 行 {refs_field} 必须是 list。")
                continue
            for ref_index, ref in enumerate(refs, start=1):
                _inspect_command_log_artifact_ref(ref, failures, label=f"acceptance_command_log[{index}].{refs_field}[{ref_index}]")
        for paths_field, reason_field in (
            ("self_referential_input_paths", "self_referential_input_reason"),
            ("self_referential_output_paths", "self_referential_output_reason"),
        ):
            paths = record.get(paths_field)
            if paths in (None, []):
                continue
            if not isinstance(paths, list) or not all(isinstance(item, str) and item for item in paths):
                failures.append(f"acceptance_command_log 第 {index} 行 {paths_field} 必须是非空字符串列表。")
            if not record.get(reason_field):
                failures.append(f"acceptance_command_log 第 {index} 行声明 {paths_field} 时必须提供 {reason_field}。")


def _inspect_command_log_artifact_ref(ref: Any, failures: list[str], *, label: str) -> None:
    if not isinstance(ref, dict):
        failures.append(f"{label} artifact ref 缺失或不是 object。")
        return
    raw = str(ref.get("path") or ref.get("relative_path") or "")
    if not raw:
        failures.append(f"{label} artifact ref 缺少 path。")
        return
    if not ref.get("sha256"):
        failures.append(f"{label} artifact ref 缺少 sha256。")
        return
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        failures.append(f"{label} artifact ref 路径不存在：{raw}")
        return
    actual_sha = _hash_path(path)
    if actual_sha != ref.get("sha256"):
        failures.append(f"{label} sha256 不匹配：{raw}")
    if not path.is_dir() and ref.get("size_bytes") is not None and path.stat().st_size != ref.get("size_bytes"):
        failures.append(f"{label} size_bytes 不匹配：{raw}")


def inspect_v4_regression_evidence_report(
    report: str | Path,
    *,
    expected_role: str | None = None,
    assert_complete: bool = False,
) -> str:
    report_path = Path(report)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload:
        _inspect_schema_version(payload, V4_REGRESSION_EVIDENCE_REPORT_VERSION, failures, label=report_path.name)
    role = payload.get("role")
    if expected_role is not None and role != expected_role:
        failures.append(f"V4 regression evidence role 不匹配：expected={expected_role} actual={role}")
    if role not in {"real_repository_regression", "swebench_like_regression"}:
        failures.append("V4 regression evidence role 必须是 real_repository_regression 或 swebench_like_regression。")
    if payload.get("model_visible") is not False:
        failures.append("V4 regression evidence 必须声明 model_visible=false。")
    if payload.get("independent_regression_evidence") is not True:
        failures.append("V4 regression evidence 必须声明 independent_regression_evidence=true。")
    if payload.get("source_role_reused_as_regression_evidence") is not False:
        failures.append("V4 regression evidence 不能复用 task freeze / validity 作为 regression 主证据。")
    if assert_complete and payload.get("result") != "passed":
        failures.append("V4 regression evidence assert-complete 要求 result=passed。")
    for label in ("regression_command_log_ref", "source_task_freeze_ref", "source_task_validity_ref"):
        ref_path = _inspect_file_ref(payload.get(label), failures, label=label)
        if label == "regression_command_log_ref" and ref_path is not None:
            _inspect_v4_command_log(ref_path, failures)
    refs_by_category = payload.get("regression_evidence_refs_by_category")
    if not isinstance(refs_by_category, dict) or not refs_by_category:
        failures.append("V4 regression evidence 缺少 regression_evidence_refs_by_category。")
    elif assert_complete:
        for category in ("agent_run_integration", "export_quality"):
            refs = refs_by_category.get(category)
            if not isinstance(refs, list) or not refs:
                failures.append(f"V4 regression evidence 缺少 {category} evidence ref。")
                continue
            for index, ref in enumerate(refs, start=1):
                _inspect_file_ref(ref, failures, label=f"regression_evidence_refs_by_category.{category}[{index}]")
    policy = payload.get("role_evidence_independence_policy")
    if not isinstance(policy, dict):
        failures.append("V4 regression evidence 缺少 role_evidence_independence_policy。")
    elif assert_complete:
        for field in (
            "must_not_equal_v4_pr_issue_task_freeze_ref",
            "must_not_equal_v4_swebench_like_task_freeze_ref",
            "acceptance_report_must_bind_this_report_directly",
        ):
            if policy.get(field) is not True:
                failures.append(f"V4 regression evidence independence policy 缺少或未启用：{field}")
    lines = [
        f"V4 regression evidence report: {report_path}",
        f"Role: {role}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V4 regression evidence: complete")
    lines.append("Inspect V4 regression evidence: passed")
    return "\n".join(lines)


def _inspect_v4_final_acceptance_command_log(
    path: Path,
    *,
    bundle_manifest_path: Path,
    acceptance_report_path: Path,
    failures: list[str],
) -> None:
    if not path.exists():
        failures.append(f"final acceptance command log 不存在：{path}")
        return
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"final acceptance command log 第 {index} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"final acceptance command log 第 {index} 行顶层必须是 object。")
            continue
        records.append(record)
    by_command: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_command.setdefault(str(record.get("command_name") or ""), []).append(record)
    missing = [
        command
        for command in V4_FINAL_ACCEPTANCE_COMMAND_LOG_REQUIRED_COMMANDS
        if not by_command.get(command)
    ]
    if missing:
        failures.append("final acceptance command log 缺少最终验收命令：" + ", ".join(missing))
    for command in V4_FINAL_ACCEPTANCE_COMMAND_LOG_REQUIRED_COMMANDS:
        for record in by_command.get(command, []):
            if record.get("exit_code") != 0:
                failures.append(f"final acceptance command log {command} 必须 exit_code=0。")
    bundle_relative = _relative_path(bundle_manifest_path, Path.cwd())
    report_relative = _relative_path(acceptance_report_path, Path.cwd())
    inspect_acceptance_records = by_command.get("inspect-v4-acceptance") or []
    for record in inspect_acceptance_records:
        if not _record_argv_contains_path(record, acceptance_report_path):
            failures.append("inspect-v4-acceptance argv 必须指向当前 v4_acceptance_report。")
        if "--assert-complete" not in (record.get("argv") or []):
            failures.append("inspect-v4-acceptance argv 必须包含 --assert-complete。")
        if not _record_refs_contain_path(record, "input_refs", acceptance_report_path):
            failures.append("inspect-v4-acceptance input_refs 必须绑定当前 v4_acceptance_report。")
    build_records = by_command.get("build-v4-acceptance-bundle") or []
    for record in build_records:
        if not _record_argv_option_matches_path(record, "--acceptance-report", acceptance_report_path):
            failures.append("build-v4-acceptance-bundle argv 必须用 --acceptance-report 指向当前 v4_acceptance_report。")
        if not _record_argv_option_matches_path(record, "--output", bundle_manifest_path):
            failures.append("build-v4-acceptance-bundle argv 必须用 --output 指向当前 acceptance_bundle_manifest。")
        if not _record_argv_option_matches_path(record, "--final-command-log", path):
            failures.append("build-v4-acceptance-bundle argv 必须用 --final-command-log 指向当前 final command log。")
        if not _record_refs_contain_path(record, "input_refs", acceptance_report_path):
            failures.append("build-v4-acceptance-bundle input_refs 必须绑定当前 v4_acceptance_report。")
        if bundle_relative not in (record.get("self_referential_output_paths") or []):
            failures.append("build-v4-acceptance-bundle 记录必须把 bundle manifest 声明为自引用输出。")
    inspect_records = by_command.get("inspect-acceptance-bundle") or []
    for record in inspect_records:
        if not _record_argv_contains_path(record, bundle_manifest_path):
            failures.append("inspect-acceptance-bundle argv 必须指向当前 acceptance_bundle_manifest。")
        if "--assert-immutable" not in (record.get("argv") or []):
            failures.append("inspect-acceptance-bundle argv 必须包含 --assert-immutable。")
        if bundle_relative not in (record.get("self_referential_input_paths") or []):
            failures.append("inspect-acceptance-bundle 记录必须把 bundle manifest 声明为自引用输入。")
    if report_relative == bundle_relative:
        failures.append("final command log 当前 report 和 bundle 路径不能相同。")


def _record_argv_option_matches_path(record: dict[str, Any], option: str, expected_path: Path) -> bool:
    argv = record.get("argv")
    if not isinstance(argv, list):
        return False
    for index, arg in enumerate(argv):
        if arg == option and index + 1 < len(argv):
            return _command_arg_matches_path(str(argv[index + 1]), expected_path)
        prefix = f"{option}="
        if isinstance(arg, str) and arg.startswith(prefix):
            return _command_arg_matches_path(arg[len(prefix):], expected_path)
    return False


def _record_argv_contains_path(record: dict[str, Any], expected_path: Path) -> bool:
    argv = record.get("argv")
    if not isinstance(argv, list):
        return False
    return any(_command_arg_matches_path(str(arg), expected_path) for arg in argv)


def _command_arg_matches_path(raw_arg: str, expected_path: Path) -> bool:
    if not raw_arg or raw_arg.startswith("-"):
        return False
    expected_resolved = expected_path.resolve(strict=False)
    expected_relative = _relative_path(expected_path, Path.cwd())
    if raw_arg == expected_relative or raw_arg == expected_resolved.as_posix():
        return True
    candidate = Path(raw_arg)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate.resolve(strict=False) == expected_resolved


def _record_refs_contain_path(record: dict[str, Any], refs_field: str, expected_path: Path) -> bool:
    refs = record.get(refs_field)
    if not isinstance(refs, list):
        return False
    expected_resolved = expected_path.resolve(strict=False)
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        raw = str(ref.get("path") or ref.get("relative_path") or "")
        if not raw:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if candidate.resolve(strict=False) == expected_resolved:
            return True
    return False


def _inspect_v4_acceptance_role_evidence(role_evidence_refs: Any, failures: list[str]) -> None:
    if not isinstance(role_evidence_refs, dict):
        return
    try:
        from repo_harness.v2_acceptance import inspect_v2_acceptance
        from repo_harness.v3_acceptance import inspect_v3_acceptance
        from repo_harness.v4_agent_run import inspect_v4_agent_run_integration
        from repo_harness.v4_cards import inspect_v4_cards
        from repo_harness.v4_export_quality import inspect_v4_export_quality
        from repo_harness.v4_rollout import inspect_rollout_queue, inspect_rollout_resume
        from repo_harness.v4_task_freeze import inspect_v4_task_freeze, inspect_v4_task_validity
        from repo_harness.v4_tool_lifecycle import inspect_v4_tool_lifecycle
    except ImportError as exc:
        failures.append(f"V4 acceptance role evidence inspector import failed：{exc}")
        return
    inspectors = {
        "v2_regression": lambda path: inspect_v2_acceptance(path, assert_complete=True),
        "v3_regression": lambda path: inspect_v3_acceptance(path, assert_complete=True),
        "real_repository_regression": lambda path: inspect_v4_regression_evidence_report(
            path,
            expected_role="real_repository_regression",
            assert_complete=True,
        ),
        "swebench_like_regression": lambda path: inspect_v4_regression_evidence_report(
            path,
            expected_role="swebench_like_regression",
            assert_complete=True,
        ),
        "v4_pr_issue_task_freeze": lambda path: inspect_v4_task_freeze(path, assert_complete=True),
        "v4_swebench_like_task_freeze": lambda path: inspect_v4_task_validity(path, assert_complete=True),
        "v4_rollout_orchestration": lambda path: inspect_rollout_queue(path, assert_complete=True),
        "v4_rollout_resume": lambda path: inspect_rollout_resume(path, assert_complete=True),
        "v4_agent_run_integration": lambda path: inspect_v4_agent_run_integration(path, assert_complete=True),
        "v4_export_quality": lambda path: inspect_v4_export_quality(path, assert_complete=True),
        "v4_tool_lifecycle_audit": lambda path: inspect_v4_tool_lifecycle(path, assert_complete=True),
        "v4_cards": lambda path: inspect_v4_cards(path, assert_complete=True),
    }
    duplicate_pairs = (
        ("real_repository_regression", "v4_pr_issue_task_freeze"),
        ("swebench_like_regression", "v4_swebench_like_task_freeze"),
    )
    for regression_role, source_role in duplicate_pairs:
        regression_ref = role_evidence_refs.get(regression_role)
        source_ref = role_evidence_refs.get(source_role)
        if isinstance(regression_ref, dict) and isinstance(source_ref, dict):
            if _role_evidence_identity(regression_ref) == _role_evidence_identity(source_ref):
                failures.append(f"role_evidence_refs.{regression_role} 不能复用 {source_role} 的同一证据。")
            if regression_ref.get("category") != regression_role:
                failures.append(f"role_evidence_refs.{regression_role} category 必须是 {regression_role}。")
    for role in V4_REQUIRED_FINAL_ACCEPTANCE_ROLES:
        ref = role_evidence_refs.get(role)
        if not isinstance(ref, dict):
            failures.append(f"role_evidence_refs 缺少 {role}。")
            continue
        path = _inspect_file_ref(ref, failures, label=f"role_evidence_refs.{role}")
        if path is None:
            continue
        try:
            inspectors[role](path)
        except ConfigError as exc:
            failures.append(f"role_evidence_refs.{role} 递归复核失败：{exc}")


def _role_evidence_identity(ref: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(ref.get("path") or ref.get("relative_path") or ""),
        str(ref.get("sha256") or ""),
        str(ref.get("kind") or ""),
    )


def inspect_v4_inputs(manifest: str | Path, *, assert_complete: bool = False) -> str:
    manifest_path = Path(manifest)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if payload:
        _inspect_schema_version(payload, V4_ACCEPTANCE_INPUTS_VERSION, failures, label=manifest_path.name)
    if payload.get("selection_mode") != "explicit":
        failures.append("V4 acceptance inputs 必须使用 explicit selection_mode。")
    if payload.get("latest_run_auto_selection") is not False:
        failures.append("V4 acceptance inputs 禁止 latest run 自动选择。")
    refs_by_category = payload.get("input_refs_by_category")
    if not isinstance(refs_by_category, dict):
        failures.append("V4 acceptance inputs 缺少 input_refs_by_category。")
        refs_by_category = {}
    for category, refs in refs_by_category.items():
        if not isinstance(refs, list):
            failures.append(f"input_refs_by_category.{category} 必须是列表。")
            continue
        for index, ref in enumerate(refs, start=1):
            _inspect_file_ref(ref, failures, label=f"{category}[{index}]")
    if assert_complete:
        missing = [category for category in V4_REQUIRED_ACCEPTANCE_INPUT_CATEGORIES if not refs_by_category.get(category)]
        if missing:
            failures.append("V4 acceptance inputs 缺少必需类别：" + ", ".join(missing))
    run_selection_ref = (refs_by_category.get("run_selection_manifest") or [None])[0]
    run_selection_path = _inspect_file_ref(run_selection_ref, failures, label="run_selection_manifest") if run_selection_ref else None
    if run_selection_path:
        _inspect_v4_run_selection_manifest(run_selection_path, failures)
    tracking_ref = payload.get("artifact_inspect_tracking_table_ref")
    if tracking_ref:
        tracking_path = _inspect_file_ref(tracking_ref, failures, label="artifact_inspect_tracking_table_ref")
        if tracking_path:
            _inspect_artifact_tracking_table(tracking_path, failures)
    elif assert_complete:
        failures.append("V4 acceptance inputs 缺少 artifact_inspect_tracking_table_ref。")
    if assert_complete:
        _inspect_bound_acceptance_categories(refs_by_category, failures)
    lines = [
        f"V4 acceptance inputs: {manifest_path}",
        f"Categories: {len(refs_by_category)}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V4 inputs: complete")
    lines.append("Inspect V4 inputs: passed")
    return "\n".join(lines)


def inspect_v4_acceptance(report: str | Path, *, assert_complete: bool = False) -> str:
    report_path = Path(report)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload:
        _inspect_schema_version(payload, V4_ACCEPTANCE_REPORT_VERSION, failures, label=report_path.name)
    if assert_complete and payload.get("status") != "passed":
        failures.append("assert-complete 要求 V4 acceptance report status=passed。")
    inputs_ref = payload.get("acceptance_inputs_ref")
    inputs_path = _inspect_file_ref(inputs_ref, failures, label="acceptance_inputs_ref")
    if inputs_path:
        try:
            inspect_v4_inputs(inputs_path, assert_complete=assert_complete)
        except ConfigError as exc:
            failures.append(f"acceptance_inputs_ref 复查失败：{exc}")
    role_statuses = payload.get("role_statuses", {})
    if assert_complete:
        missing_roles = [role for role in V4_REQUIRED_FINAL_ACCEPTANCE_ROLES if role_statuses.get(role) != "passed"]
        if missing_roles:
            failures.append("V4 acceptance report 缺少通过的必需 role：" + ", ".join(missing_roles))
        _inspect_v4_acceptance_role_evidence(payload.get("role_evidence_refs"), failures)
        if payload.get("accepted_auditable_task_definition_count", 0) < 8:
            failures.append("V4 acceptance report accepted / auditable task definitions 少于 8。")
        if payload.get("pr_issue_accepted_auditable_task_definition_count", 0) < 4:
            failures.append("V4 acceptance report PR / issue accepted / auditable task definitions 少于 4。")
        if payload.get("final_verifier_authority_preserved") is not True:
            failures.append("V4 acceptance report 必须保留 final verifier authority。")
        if payload.get("trainable_payload_contamination_status") != "clean":
            failures.append("V4 acceptance report trainable payload contamination status 必须 clean。")
        if payload.get("evaluator_only_evidence_model_visible") is not False:
            failures.append("V4 acceptance report 必须证明 evaluator-only evidence 没有进入模型可见上下文。")
    command_log_ref = payload.get("acceptance_command_log_ref")
    if command_log_ref is not None:
        command_log_path = _inspect_file_ref(command_log_ref, failures, label="acceptance_command_log_ref")
        if command_log_path:
            _inspect_v4_command_log(command_log_path, failures)
    lines = [
        f"V4 acceptance report: {report_path}",
        f"Report status: {payload.get('status')}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V4 acceptance: complete")
    lines.append("Inspect V4 acceptance: passed")
    return "\n".join(lines)


def inspect_v4_acceptance_bundle(manifest: str | Path, *, assert_immutable: bool = False) -> str:
    manifest_path = Path(manifest)
    failures: list[str] = []
    payload = _read_json_for_inspect(manifest_path, failures)
    if payload:
        _inspect_schema_version(payload, V4_ACCEPTANCE_BUNDLE_MANIFEST_VERSION, failures, label=manifest_path.name)
    report_ref = payload.get("acceptance_report_ref") or payload.get("report_ref")
    report_path = _inspect_file_ref(report_ref, failures, label="acceptance_report_ref")
    if report_path and assert_immutable:
        try:
            inspect_v4_acceptance(report_path, assert_complete=True)
        except ConfigError as exc:
            failures.append(f"acceptance bundle 传递性复查 v4_acceptance_report 失败：{exc}")
    for label in ("acceptance_inputs_ref", "acceptance_command_log_ref"):
        if payload.get(label) is not None:
            _inspect_file_ref(payload.get(label), failures, label=label)
    final_command_log_ref = payload.get("final_acceptance_command_log_ref")
    if assert_immutable and not isinstance(final_command_log_ref, dict):
        failures.append("V4 acceptance bundle 缺少 final_acceptance_command_log_ref。")
    final_command_log_path = None
    if final_command_log_ref is not None:
        final_command_log_path = _inspect_file_ref(
            final_command_log_ref,
            failures,
            label="final_acceptance_command_log_ref",
        )
    if final_command_log_path is not None:
        _inspect_v4_command_log(final_command_log_path, failures)
        _inspect_v4_final_acceptance_command_log(
            final_command_log_path,
            bundle_manifest_path=manifest_path,
            acceptance_report_path=report_path,
            failures=failures,
        )
    docs = payload.get("documentation_refs")
    if assert_immutable and (not isinstance(docs, list) or not docs):
        failures.append("V4 acceptance bundle 必须绑定 post-acceptance documentation refs。")
    if isinstance(docs, list):
        for index, ref in enumerate(docs, start=1):
            _inspect_file_ref(ref, failures, label=f"documentation_refs[{index}]")
    _inspect_v4_post_docs_not_report_inputs(payload, failures)
    lines = [
        f"V4 acceptance bundle: {manifest_path}",
        f"Schema version: {payload.get('schema_version')}",
    ]
    if failures:
        if assert_immutable:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_immutable:
        lines.append("Inspect acceptance bundle: immutable")
    lines.append("Inspect acceptance bundle: passed")
    return "\n".join(lines)


def build_artifact_inspect_tracking_table_payload() -> dict[str, Any]:
    return {
        "schema_version": V4_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
        "rows": list(V4_ARTIFACT_INSPECT_TRACKING_ROWS),
        "required_inspect_commands": sorted(
            {
                row["inspect_command"]
                for row in V4_ARTIFACT_INSPECT_TRACKING_ROWS
            }
            | {
                command
                for row in V4_ARTIFACT_INSPECT_TRACKING_ROWS
                for command in row.get("secondary_inspect_commands", [])
            }
        ),
    }


def _inspect_v4_run_selection_manifest(path: Path, failures: list[str]) -> None:
    payload = _read_json_for_inspect(path, failures)
    if not payload:
        return
    _inspect_schema_version(payload, V4_RUN_SELECTION_MANIFEST_VERSION, failures, label=path.name)
    if payload.get("selection_mode") != "explicit":
        failures.append("RUN_SELECTION_MANIFEST 必须使用 explicit selection_mode。")
    if payload.get("latest_run_auto_selection") is not False:
        failures.append("RUN_SELECTION_MANIFEST 禁止 latest run 自动选择。")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("RUN_SELECTION_MANIFEST entries 必须是非空列表。")
        return
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            failures.append(f"RUN_SELECTION_MANIFEST entries[{index}] 不是 object。")
            continue
        if not entry.get("role"):
            failures.append(f"RUN_SELECTION_MANIFEST entries[{index}] 缺少 role。")
        raw_path = str(entry.get("run_ref") or entry.get("path") or entry.get("run_dir") or "")
        if not raw_path:
            failures.append(f"RUN_SELECTION_MANIFEST entries[{index}] 缺少 selected run ref。")
        if _looks_like_report_artifact(raw_path):
            failures.append("RUN_SELECTION_MANIFEST 不能绑定报告类产物路径：" + raw_path)


def _inspect_artifact_tracking_table(path: Path, failures: list[str]) -> None:
    payload = _read_json_for_inspect(path, failures)
    if not payload:
        return
    _inspect_schema_version(payload, V4_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION, failures, label=path.name)
    commands = set(payload.get("required_inspect_commands") or [])
    expected = set(build_artifact_inspect_tracking_table_payload()["required_inspect_commands"])
    missing = sorted(expected.difference(commands))
    if missing:
        failures.append("artifact inspect tracking table 缺少 inspect 命令：" + ", ".join(missing))


def _inspect_bound_acceptance_categories(
    refs_by_category: dict[str, Any],
    failures: list[str],
) -> None:
    _inspect_external_acceptance_categories(refs_by_category, failures)
    category_specs = {
        "rollout_queue": "rollout_queue",
        "lease_state": "rollout_leases",
        "retry_policy": "rollout_retry",
        "budget_control": "rollout_budget",
        "resource_locks": "resource_locks",
        "resource_usage": "resource_usage",
        "batch_resume": "rollout_resume",
        "run_selection_query": "run_selection_query",
        "task_freeze": "task_freeze",
        "task_validity": "task_validity",
        "tool_contract": "tool_contract",
        "tool_lifecycle": "tool_lifecycle",
        "agent_run_integration": "agent_run_integration",
        "trajectory_store": "trajectory_store",
        "export_quality": "export_quality",
        "cards": "cards",
    }
    for category in ("real_repository_regression", "swebench_like_regression"):
        refs = refs_by_category.get(category)
        if not isinstance(refs, list) or not refs:
            continue
        path = _path_from_ref(refs[0])
        if path is None or not path.exists():
            continue
        try:
            inspect_v4_regression_evidence_report(path, expected_role=category, assert_complete=True)
        except ConfigError as exc:
            failures.append(f"{category} 绑定产物递归复核失败：{exc}")
    for category, spec_id in category_specs.items():
        refs = refs_by_category.get(category)
        if not isinstance(refs, list) or not refs:
            continue
        path = _path_from_ref(refs[0])
        if path is None or not path.exists():
            continue
        try:
            if spec_id == "task_freeze":
                from repo_harness.v4_task_freeze import inspect_v4_task_freeze

                inspect_v4_task_freeze(path, assert_complete=True)
            elif spec_id == "task_validity":
                from repo_harness.v4_task_freeze import inspect_v4_task_validity

                inspect_v4_task_validity(path, assert_complete=True)
            elif spec_id == "trajectory_store":
                from repo_harness.v4_agent_run import inspect_v4_trajectory_store

                inspect_v4_trajectory_store(path, assert_readable=True)
            else:
                inspect_v4_artifact_set(spec_id, path, assert_complete=True)
        except ConfigError as exc:
            failures.append(f"{category} 绑定产物递归复核失败：{exc}")
    scan_refs = refs_by_category.get("contamination_scan") or refs_by_category.get("contamination_summary")
    if isinstance(scan_refs, list) and scan_refs:
        path = _path_from_ref(scan_refs[0])
        if path is not None and path.exists():
            try:
                inspect_v4_artifact_set("contamination_scan", path, assert_complete=True)
            except ConfigError as exc:
                failures.append(f"contamination_scan 绑定产物递归复核失败：{exc}")


def _inspect_external_acceptance_categories(refs_by_category: dict[str, Any], failures: list[str]) -> None:
    external = {
        "v2_acceptance": ("v2_acceptance", lambda path: __import__("repo_harness.v2_acceptance", fromlist=["inspect_v2_acceptance"]).inspect_v2_acceptance(path, assert_complete=True)),
        "v3_acceptance": ("v3_acceptance", lambda path: __import__("repo_harness.v3_acceptance", fromlist=["inspect_v3_acceptance"]).inspect_v3_acceptance(path, assert_complete=True)),
        "v3_acceptance_bundle": ("v3_acceptance_bundle", lambda path: __import__("repo_harness.v3_acceptance", fromlist=["inspect_acceptance_bundle"]).inspect_acceptance_bundle(path, assert_immutable=True)),
        "implementation_inputs": ("implementation_inputs", lambda path: __import__("repo_harness.v4_implementation_inputs", fromlist=["inspect_v4_implementation_inputs"]).inspect_v4_implementation_inputs(path, assert_complete=True)),
    }
    for category, (_, inspector) in external.items():
        refs = refs_by_category.get(category)
        if not isinstance(refs, list) or not refs:
            continue
        path = _path_from_ref(refs[0])
        if path is None or not path.exists():
            continue
        try:
            inspector(path)
        except ConfigError as exc:
            failures.append(f"{category} 绑定产物递归复核失败：{exc}")
    command_refs = refs_by_category.get("command_log")
    if isinstance(command_refs, list) and command_refs:
        path = _path_from_ref(command_refs[0])
        if path is not None and path.exists():
            _inspect_v4_command_log(path, failures)
    doc_refs = refs_by_category.get("pre_acceptance_docs")
    if isinstance(doc_refs, list):
        for index, ref in enumerate(doc_refs, start=1):
            path = _inspect_file_ref(ref, failures, label=f"pre_acceptance_docs[{index}]")
            if path is not None and path.suffix.lower() != ".md":
                failures.append(f"pre_acceptance_docs[{index}] 必须是 markdown 文档。")


def _inspect_v4_post_docs_not_report_inputs(bundle_payload: dict[str, Any], failures: list[str]) -> None:
    docs = bundle_payload.get("documentation_refs")
    input_ref = bundle_payload.get("acceptance_inputs_ref")
    if not isinstance(docs, list) or not isinstance(input_ref, dict):
        return
    input_path = _path_from_ref(input_ref)
    if input_path is None or not input_path.exists():
        return
    input_payload = _read_json_for_inspect(input_path, failures)
    report_input_paths: set[str] = set()
    for refs in (input_payload.get("input_refs_by_category") or {}).values():
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if isinstance(ref, dict):
                raw = str(ref.get("path") or ref.get("relative_path") or "")
                if raw:
                    report_input_paths.add(raw)
    for index, ref in enumerate(docs, start=1):
        if not isinstance(ref, dict):
            continue
        raw = str(ref.get("path") or ref.get("relative_path") or "")
        if raw and raw in report_input_paths:
            failures.append(f"post-acceptance documentation_refs[{index}] 不能作为 acceptance report 输入。")


def _inspect_embedded_artifact_refs(
    payload: dict[str, Any],
    *,
    expected_names: tuple[str, ...],
    failures: list[str],
    label: str,
) -> None:
    if not expected_names:
        return
    refs_by_name = payload.get("artifact_refs_by_name")
    if not isinstance(refs_by_name, dict):
        failures.append(f"{label} 缺少 artifact_refs_by_name。")
        return
    for name in expected_names:
        ref = refs_by_name.get(name)
        if ref is None:
            failures.append(f"{label} artifact_refs_by_name 缺少：{name}")
            continue
        ref_path = _inspect_file_ref(ref, failures, label=f"{label}.{name}")
        if ref_path is None:
            continue
        if Path(str(ref.get("path") or ref.get("relative_path") or "")).name != name:
            failures.append(f"{label}.{name} ref path 文件名不匹配。")


def _inspect_schema_version(
    payload: dict[str, Any],
    expected: str | None,
    failures: list[str],
    *,
    label: str,
) -> None:
    if "schema_version" not in payload:
        failures.append(f"{label} 缺少 schema_version。")
        return
    if expected is not None and payload.get("schema_version") != expected:
        failures.append(f"{label} schema_version 不匹配。")


def _inspect_file_ref(ref: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("path") or ref.get("relative_path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    if not ref.get("sha256"):
        failures.append(f"{label} 文件 ref 缺少 sha256。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    actual_sha = _hash_path(path)
    if actual_sha != ref.get("sha256"):
        failures.append(f"{label} sha256 不匹配：{raw}")
    if not path.is_dir() and ref.get("size_bytes") is not None and path.stat().st_size != ref.get("size_bytes"):
        failures.append(f"{label} size_bytes 不匹配：{raw}")
    return path


def _path_from_ref(ref: Any) -> Path | None:
    if not isinstance(ref, dict):
        return None
    raw = str(ref.get("path") or ref.get("relative_path") or "")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else Path.cwd() / path


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _inspect_jsonl_file(path: Path, expected_schema_version: str | None, failures: list[str], *, label: str) -> None:
    if not path.exists():
        failures.append(f"{label} 不存在：{path}")
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        failures.append(f"{label} 必须至少包含一条 JSONL 记录。")
        return
    for index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{label} 第 {index} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(record, dict):
            failures.append(f"{label} 第 {index} 行顶层必须是 object。")
            continue
        _inspect_schema_version(record, expected_schema_version, failures, label=f"{label}[{index}]")


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


def _hash_path(path: Path) -> str:
    return compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)


def _looks_like_report_artifact(path: str) -> bool:
    lowered = path.lower()
    return (
        lowered.endswith(".json")
        or lowered.endswith(".jsonl")
        or lowered.endswith(".md")
        or "_report" in lowered
        or "manifest" in lowered
    )
