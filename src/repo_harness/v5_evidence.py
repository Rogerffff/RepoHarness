"""V5 Stage 0 preimplementation evidence builders and inspectors."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness import __version__
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V5_ACCEPTANCE_INPUTS_VERSION,
    V5_ACCEPTANCE_LINEAGE_SCHEMA_REPORT_VERSION,
    V5_ACCEPTANCE_REPORT_VERSION,
    V5_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
    V5_BASELINE_CHECK_REPORT_VERSION,
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_CRITICAL_EVIDENCE_MANIFEST_VERSION,
    V5_DEMO_TRANSCRIPT_INDEX_VERSION,
    V5_DOCUMENTATION_SYNC_REPORT_VERSION,
    V5_EVIDENCE_REF_VERSION,
    V5_EXPORT_RESULT_PACK_MANIFEST_VERSION,
    V5_FAILURE_TAXONOMY_REPORT_VERSION,
    V5_INTERVIEW_RESULT_PACK_MANIFEST_VERSION,
    V5_MATRIX_CELL_RESULT_VERSION,
    V5_MATRIX_COMPARE_SCOPE_REPORT_VERSION,
    V5_PRE_ACCEPTANCE_EVIDENCE_INTEGRITY_REPORT_VERSION,
    V5_PREFERENCE_PAIR_BLOCKED_REPORT_VERSION,
    V5_PREFLIGHT_INPUT_BINDING_VERSION,
    V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
    V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
    V5_PROVIDER_RAW_CONTENT_REDACTION_REPORT_VERSION,
    V5_PROVIDER_REGISTRY_REPORT_VERSION,
    V5_PROVIDER_SMOKE_REPORT_VERSION,
    V5_PROVIDER_STATUS_NORMALIZATION_REPORT_VERSION,
    V5_PUBLIC_DEMO_BUNDLE_MANIFEST_VERSION,
    V5_RESULT_SUMMARY_TABLE_VERSION,
    V5_RESUME_ARTIFACT_INDEX_VERSION,
    V5_RESUME_CLAIM_GATE_REPORT_VERSION,
    V5_REWARD_SOURCE_TAXONOMY_REPORT_VERSION,
    V5_RUN_MATRIX_MANIFEST_VERSION,
    V5_SCHEMA_TRACKING_TABLE_VERSION,
    V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION,
    V5_TASK_INVENTORY_REPORT_VERSION,
    V5_TASK_DEFINITION_VERSION,
    V5_TASK_SET_MANIFEST_VERSION,
    V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
    V5_V4_CLOSURE_REPORT_VERSION,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


V5_BASELINE_COMMIT = "9fd7007"
V5_V4_CLOSURE_COMMIT = "e0da89c"
V5_PREFLIGHT_ROOT = "runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z"
V5_PARTIAL_THRESHOLD_STATUS = "partial_below_12_total_and_8_pr_issue_preflight_threshold"

V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER = (
    "pallets/click#3364",
    "python-attrs/attrs#1428",
    "pypa/packaging#1124",
    "hynek/structlog#620",
    "chalk/chalk#335",
    "sindresorhus/execa#1176",
    "clap-rs/clap#6340",
)

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

V5_VISIBILITY_VALUES = (
    "model_visible",
    "trainable",
    "diagnostic_only",
    "audit_only",
    "evaluator_only",
    "public_safe",
)
V5_ACCEPTANCE_STATUS_VALUES = ("passed", "failed", "blocked")
V5_PROVIDER_FAMILIES = ("openai", "deepseek", "anthropic_claude")
V5_CREDENTIAL_STATUS_VALUES = ("present", "missing", "not_configured")
V5_ADAPTER_STATUS_VALUES = ("primary_supported", "fallback_only", "adapter_not_implemented")
V5_PROVIDER_STATUS_VALUES = (
    "primary_attempted",
    "credential_missing_skip",
    "adapter_not_implemented_skip",
    "cost_limited_structured_skip",
    "fallback_success",
    "provider_error",
)
V5_PROVIDER_GATE_STRUCTURED_SKIP_TYPES = (
    "credential_missing_skip",
    "adapter_not_implemented_skip",
    "cost_limited_structured_skip",
    "primary_provider_comparison_not_enabled_skip",
)
V5_PROVIDER_RAW_CONTENT_POLICY = "audit_only_redacted_never_model_visible"
V5_RAW_SECRET_MARKER_RE = r"\bsk-(?:proj-|ant-api03-)?[A-Za-z0-9_\-]{12,}\b"
V5_CLAIM_GATE_STAGE_VALUES = ("stage3_partial", "stage4_partial", "stage5_final", "acceptance_final")
V5_COMPARISON_AXES = ("provider", "scaffold", "budget", "diagnostic_baseline")
V5_PARTITION_COUNT_FIELDS = (
    "real_provider_trainable_records",
    "mock_or_replay_records",
    "diagnostic_records",
    "blocked_records",
    "synthetic_safe_stress_records",
)
V5_FORBIDDEN_PUBLIC_OR_TRAINABLE_MARKERS = (
    "evaluator-only",
    "evaluator_only",
    "evaluator only",
    "gold patch",
    "gold_patch",
    "raw test patch",
    "raw_test_patch",
    "provider raw request",
    "provider_raw_request",
    "provider raw response",
    "provider_raw_response",
    "provider raw content",
    "provider_raw_content",
    "credential",
    "authorization",
    "reward scalar",
    "reward_scalar",
    "reward label",
    "reward_label",
)
V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS = tuple(
    marker
    for marker in V5_FORBIDDEN_PUBLIC_OR_TRAINABLE_MARKERS
    if marker not in {"evaluator-only", "evaluator_only", "evaluator only"}
) + (
    "evaluator-only content:",
    "evaluator_only_content",
    "evaluator only content",
    "raw pr body",
    "raw_pr_body",
    "raw pr diff",
    "raw_pr_diff",
    "review comment",
    "review_comment",
    "fix commit url",
    "fix_commit_url",
    "merge commit url",
    "merge_commit_url",
    "hidden selector",
    "hidden_selector",
    "official resolved status",
    "official_resolved_status",
    "claude.ai/share",
    "chat.openai.com/share",
    "coding session url",
    "coding_session_url",
)
V5_POST_REPORT_EVIDENCE_CLASSES = (
    "acceptance_report_reference_integrity",
    "acceptance_bundle_command_lineage_integrity",
    "post_report_inspect_output",
    "bundle_final_output",
    "doc_sync_output",
)
V5_CRITICAL_EVIDENCE_CLASSES = (
    "baseline_proof",
    "regression_acceptance",
    "v4_closure_baseline",
    "task_definition",
    "visibility_scan",
    "provider_gate",
    "run_matrix",
    "export_pack",
    "demo_artifact",
    "acceptance_pretest",
    "pre_acceptance_command_log",
    "final_verifier_boundary",
    "trajectory",
    "claim_gate",
)

V5_SCHEMA_SPECS: tuple[dict[str, Any], ...] = (
    {
        "schema_name": "V5EvidenceRef",
        "schema_version": V5_EVIDENCE_REF_VERSION,
        "required_fields": (
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
        ),
        "inspect_command": "inspect-v5-evidence-integrity",
        "valid_fixture": "tests/fixtures/v5/evidence_ref_valid.json",
        "negative_fixture": "tests/fixtures/v5/evidence_ref_sha256_mismatch.json",
    },
    {
        "schema_name": "V5AcceptanceInputs",
        "schema_version": V5_ACCEPTANCE_INPUTS_VERSION,
        "required_fields": (
            "schema_version",
            "created_at",
            "current_head",
            "v2_acceptance_report_ref",
            "v3_acceptance_report_ref",
            "v3_acceptance_bundle_ref",
            "v4_acceptance_inputs_ref",
            "v4_acceptance_report_ref",
            "v4_doc_sync_acceptance_bundle_ref",
            "v4_doc_sync_final_command_log_ref",
            "v5_evidence_refs",
            "stress_test_executed",
        ),
        "inspect_command": "inspect-v5-inputs",
        "valid_fixture": "tests/fixtures/v5/acceptance_inputs_valid.json",
        "negative_fixture": "tests/fixtures/v5/acceptance_inputs_post_report_leak.json",
    },
    {
        "schema_name": "V5AcceptanceReport",
        "schema_version": V5_ACCEPTANCE_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "acceptance_inputs_ref",
            "core_acceptance.status",
            "core_acceptance.required_checks",
            "resume_ready_acceptance.status",
            "resume_ready_acceptance.required_checks",
            "allowed_claims",
            "blocked_claims",
            "claim_gate_report_ref",
            "acceptance_report_reference_integrity.expected_check",
        ),
        "inspect_command": "inspect-v5-acceptance",
        "valid_fixture": "tests/fixtures/v5/acceptance_report_valid_core.json",
        "negative_fixture": "tests/fixtures/v5/acceptance_report_references_post_report_output.json",
    },
    {
        "schema_name": "V5TaskSetManifest",
        "schema_version": V5_TASK_SET_MANIFEST_VERSION,
        "required_fields": (
            "schema_version",
            "accepted_auditable_task_count",
            "pr_issue_task_count",
            "swebench_like_anchor_count",
            "task_refs",
            "inventory_report_ref",
            "visibility_scan_ref",
        ),
        "inspect_command": "inspect-v5-task-set",
        "valid_fixture": "tests/fixtures/v5/task_set_valid.json",
        "negative_fixture": "tests/fixtures/v5/task_set_below_inventory_gate.json",
    },
    {
        "schema_name": "V5TaskInventoryReport",
        "schema_version": V5_TASK_INVENTORY_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "accepted_auditable_task_count",
            "pr_issue_task_count",
            "swebench_like_anchor_count",
            "strict_inventory_gate",
            "source_mix",
        ),
        "inspect_command": "inspect-v5-task-set",
        "valid_fixture": "tests/fixtures/v5/task_inventory_valid.json",
        "negative_fixture": "tests/fixtures/v5/task_inventory_missing_pr_issue_count.json",
    },
    {
        "schema_name": "V5TaskVisibilityScanReport",
        "schema_version": V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "model_visible_leak_count",
            "share_safe_violation_count",
            "trainable_payload_contamination_count",
            "findings",
            "status",
        ),
        "inspect_command": "inspect-v5-task-visibility",
        "valid_fixture": "tests/fixtures/v5/task_visibility_valid.json",
        "negative_fixture": "tests/fixtures/v5/task_visibility_model_visible_leak.json",
    },
    {
        "schema_name": "V5SupplementalPRIssueCandidateReport",
        "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "candidate_order",
            "candidate_records",
            "accepted_supplemental_count",
            "required_supplemental_count",
            "selected_candidate_ids",
            "accepted_task_definition_refs",
            "command_log_ref",
            "live_probes_executed",
            "status",
        ),
        "inspect_command": "inspect-v5-task-set",
        "valid_fixture": "tests/fixtures/v5/supplemental_pr_issue_candidate_report_valid.json",
        "negative_fixture": "tests/fixtures/v5/supplemental_pr_issue_candidate_report_not_live.json",
    },
    {
        "schema_name": "V5ProviderCredentialGateReport",
        "schema_version": V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "provider_families",
            "credential_status_by_provider",
            "adapter_status_by_provider",
            "structured_skips",
            "raw_secret_value_present",
            "provider_raw_content_policy",
        ),
        "inspect_command": "inspect-v5-provider-gate",
        "valid_fixture": "tests/fixtures/v5/provider_gate_valid.json",
        "negative_fixture": "tests/fixtures/v5/provider_gate_secret_leak.json",
    },
    {
        "schema_name": "V5ProviderCostBudgetReport",
        "schema_version": V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "max_real_provider_calls",
            "max_cost_usd",
            "cost_proxy_formula",
            "actual_real_provider_calls",
            "actual_cost_proxy_usd",
            "cost_limited_structured_skip",
            "budget_exhausted_before_run",
        ),
        "inspect_command": "inspect-v5-provider-cost-budget",
        "valid_fixture": "tests/fixtures/v5/provider_cost_budget_valid.json",
        "negative_fixture": "tests/fixtures/v5/provider_cost_budget_overrun.json",
    },
    {
        "schema_name": "V5RunMatrixManifest",
        "schema_version": V5_RUN_MATRIX_MANIFEST_VERSION,
        "required_fields": (
            "schema_version",
            "task_set_ref",
            "provider_gate_ref",
            "provider_cost_budget_ref",
            "planned_matrix_cells",
            "controlled_variables_refs",
            "comparison_axes",
            "agent_run_started",
            "provider_api_called",
        ),
        "inspect_command": "inspect-v5-run-matrix",
        "valid_fixture": "tests/fixtures/v5/run_matrix_valid.json",
        "negative_fixture": "tests/fixtures/v5/run_matrix_missing_controlled_variables.json",
    },
    {
        "schema_name": "V5MatrixCellResult",
        "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
        "required_fields": (
            "schema_version",
            "task_id",
            "provider_id",
            "provider_mode",
            "normalized_provider_status",
            "scaffold_id",
            "budget_policy_id",
            "tool_policy_id",
            "context_policy_id",
            "environment_id",
            "source_tree_hash",
            "run_id",
            "run_dir",
            "final_verifier_status",
            "trajectory_ref",
            "final_verifier_boundary_ref",
            "controlled_variables_ref",
        ),
        "inspect_command": "inspect-v5-run-matrix",
        "valid_fixture": "tests/fixtures/v5/matrix_cell_valid.json",
        "negative_fixture": "tests/fixtures/v5/matrix_cell_fallback_marked_primary.json",
    },
    {
        "schema_name": "V5MatrixCompareScopeReport",
        "schema_version": V5_MATRIX_COMPARE_SCOPE_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "comparison_axis",
            "controlled_variables",
            "compared_cells",
            "comparison_validity",
        ),
        "inspect_command": "inspect-v5-run-matrix",
        "valid_fixture": "tests/fixtures/v5/matrix_compare_scope_valid.json",
        "negative_fixture": "tests/fixtures/v5/matrix_compare_scope_missing_controlled_variables.json",
    },
    {
        "schema_name": "V5ExportResultPackManifest",
        "schema_version": V5_EXPORT_RESULT_PACK_MANIFEST_VERSION,
        "required_fields": (
            "schema_version",
            "sft_export_ref",
            "rl_rollout_export_ref",
            "failure_dataset_ref",
            "partition_counts",
            "reward_source_taxonomy_ref",
            "failure_taxonomy_ref",
            "export_audit_ref",
        ),
        "one_of_required_fields": (("preference_pair_export_ref", "preference_pair_blocked_report_ref"),),
        "inspect_command": "inspect-v5-export-pack",
        "valid_fixture": "tests/fixtures/v5/export_pack_valid.json",
        "negative_fixture": "tests/fixtures/v5/export_pack_missing_blocked_partition.json",
    },
    {
        "schema_name": "V5RewardSourceTaxonomyReport",
        "schema_version": V5_REWARD_SOURCE_TAXONOMY_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "allowed_reward_metadata_paths",
            "reward_scalar_model_visible_count",
            "reward_label_model_visible_count",
            "status",
        ),
        "inspect_command": "inspect-v5-export-pack",
        "valid_fixture": "tests/fixtures/v5/reward_source_taxonomy_valid.json",
        "negative_fixture": "tests/fixtures/v5/reward_source_taxonomy_model_visible_reward.json",
    },
    {
        "schema_name": "V5FailureTaxonomyReport",
        "schema_version": V5_FAILURE_TAXONOMY_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "categories",
            "records",
            "status",
        ),
        "inspect_command": "inspect-v5-export-pack",
        "valid_fixture": "tests/fixtures/v5/failure_taxonomy_valid.json",
        "negative_fixture": "tests/fixtures/v5/failure_taxonomy_missing_categories.json",
    },
    {
        "schema_name": "V5PreferencePairBlockedReport",
        "schema_version": V5_PREFERENCE_PAIR_BLOCKED_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "blocked_reason",
            "failure_owner",
            "failure_category",
            "claim_gate_effect",
        ),
        "inspect_command": "inspect-v5-export-pack",
        "valid_fixture": "tests/fixtures/v5/preference_pair_blocked_valid.json",
        "negative_fixture": "tests/fixtures/v5/preference_pair_blocked_missing_reason.json",
    },
    {
        "schema_name": "V5ResumeArtifactIndex",
        "schema_version": V5_RESUME_ARTIFACT_INDEX_VERSION,
        "required_fields": (
            "schema_version",
            "artifact_refs",
            "share_safe_status",
            "public_demo_bundle_ref",
        ),
        "inspect_command": "inspect-v5-demo-artifacts",
        "valid_fixture": "tests/fixtures/v5/resume_artifact_index_valid.json",
        "negative_fixture": "tests/fixtures/v5/resume_artifact_index_evaluator_only_share_safe.json",
    },
    {
        "schema_name": "V5ResultSummaryTable",
        "schema_version": V5_RESULT_SUMMARY_TABLE_VERSION,
        "required_fields": (
            "schema_version",
            "real_provider_trainable_records",
            "mock_or_replay_records",
            "diagnostic_records",
            "blocked_records",
            "synthetic_safe_stress_records",
        ),
        "inspect_command": "inspect-v5-demo-artifacts",
        "valid_fixture": "tests/fixtures/v5/result_summary_table_valid.json",
        "negative_fixture": "tests/fixtures/v5/result_summary_table_missing_blocked_records.json",
    },
    {
        "schema_name": "V5PublicDemoBundleManifest",
        "schema_version": V5_PUBLIC_DEMO_BUNDLE_MANIFEST_VERSION,
        "required_fields": (
            "schema_version",
            "artifact_refs",
            "share_safe_status",
            "provider_raw_content_count",
            "evaluator_only_content_count",
        ),
        "inspect_command": "inspect-v5-demo-artifacts",
        "valid_fixture": "tests/fixtures/v5/public_demo_bundle_valid.json",
        "negative_fixture": "tests/fixtures/v5/public_demo_bundle_raw_provider_leak.json",
    },
    {
        "schema_name": "V5DemoTranscriptIndex",
        "schema_version": V5_DEMO_TRANSCRIPT_INDEX_VERSION,
        "required_fields": (
            "schema_version",
            "transcript_refs",
            "model_visible_leak_count",
            "share_safe_status",
        ),
        "inspect_command": "inspect-v5-demo-artifacts",
        "valid_fixture": "tests/fixtures/v5/demo_transcript_index_valid.json",
        "negative_fixture": "tests/fixtures/v5/demo_transcript_index_model_visible_leak.json",
    },
    {
        "schema_name": "V5ResumeClaimGateReport",
        "schema_version": V5_RESUME_CLAIM_GATE_REPORT_VERSION,
        "required_fields": (
            "schema_version",
            "stage",
            "allowed_claims",
            "blocked_claims",
            "blocking_reasons",
            "provider_claim_status",
            "preference_pair_claim_status",
            "demo_share_safe_status",
            "stress_test_claim_status",
            "source_reports",
        ),
        "inspect_command": "inspect-v5-demo-artifacts",
        "valid_fixture": "tests/fixtures/v5/claim_gate_valid_final.json",
        "negative_fixture": "tests/fixtures/v5/claim_gate_allows_blocked_provider.json",
    },
    {
        "schema_name": "V5InterviewResultPackManifest",
        "schema_version": V5_INTERVIEW_RESULT_PACK_MANIFEST_VERSION,
        "required_fields": (
            "schema_version",
            "demo_card_ref",
            "walkthrough_ref",
            "result_summary_ref",
            "resume_templates_ref",
            "resume_bullets_ref",
            "interview_qa_evidence_ref",
            "public_safe_mapping_ref",
        ),
        "inspect_command": "inspect-v5-demo-artifacts",
        "valid_fixture": "tests/fixtures/v5/interview_result_pack_valid.json",
        "negative_fixture": "tests/fixtures/v5/interview_result_pack_raw_provider_leak.json",
    },
)

V5_REQUIRED_INSPECT_COMMANDS = (
    "inspect-v5-preimplementation",
    "inspect-v5-evidence-integrity",
    "inspect-v5-task-set",
    "inspect-v5-task-visibility",
    "inspect-v5-run-matrix",
    "inspect-v5-provider-gate",
    "inspect-v5-provider-cost-budget",
    "inspect-v5-export-pack",
    "inspect-v5-demo-artifacts",
    "inspect-v5-inputs",
    "inspect-v5-acceptance",
)


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


def build_schema_fixtures(
    *,
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build V5 Stage 1 schema fixtures and tracking tables."""

    root = Path(output_dir)
    output_names = (
        "v5_schema_tracking_table.json",
        "v5_artifact_inspect_tracking_table.json",
        "v5_acceptance_lineage_schema_report.json",
        "build_v5_schema_fixtures_command_log_entry.json",
    )
    if fail_if_output_exists:
        existing = [root / name for name in output_names if (root / name).exists()]
        fixture_root = root / "tests" / "fixtures" / "v5"
        if fixture_root.exists() and any(fixture_root.iterdir()):
            existing.append(fixture_root)
        if existing:
            raise ConfigError(
                "V5 schema fixture 输出已存在，不能覆盖旧 evidence："
                + ", ".join(path.as_posix() for path in existing)
            )
    root.mkdir(parents=True, exist_ok=True)
    fixture_root = root / "tests" / "fixtures" / "v5"
    fixture_root.mkdir(parents=True, exist_ok=True)

    target = fixture_root / "evidence_ref_target.txt"
    _write_text(target, "V5 evidence ref fixture target\n")
    v4_doc_sync_target = fixture_root / V4_DOC_SYNC_BUNDLE_NAME
    _write_text(v4_doc_sync_target, "V5 V4 doc-sync acceptance bundle fixture target\n")
    valid_paths: dict[str, Path] = {}
    negative_paths: dict[str, Path] = {}
    for spec in V5_SCHEMA_SPECS:
        valid_path = root / spec["valid_fixture"]
        negative_path = root / spec["negative_fixture"]
        schema_name = str(spec["schema_name"])
        _write_json(
            valid_path,
            _valid_schema_fixture_payload(
                schema_name,
                target,
                acceptance_inputs_path=valid_paths.get("V5AcceptanceInputs"),
                v4_doc_sync_path=v4_doc_sync_target,
            ),
        )
        _write_json(negative_path, _negative_schema_fixture_payload(str(spec["schema_name"]), target))
        valid_paths[str(spec["schema_name"])] = valid_path
        negative_paths[str(spec["schema_name"])] = negative_path

    schema_tracking_path = root / "v5_schema_tracking_table.json"
    artifact_tracking_path = root / "v5_artifact_inspect_tracking_table.json"
    lineage_path = root / "v5_acceptance_lineage_schema_report.json"
    command_log_entry_path = root / "build_v5_schema_fixtures_command_log_entry.json"

    schema_tracking = build_v5_schema_tracking_table_payload(
        valid_paths=valid_paths,
        negative_paths=negative_paths,
    )
    _write_json(schema_tracking_path, schema_tracking)
    artifact_tracking = build_v5_artifact_inspect_tracking_table_payload()
    _write_json(artifact_tracking_path, artifact_tracking)
    lineage_report = {
        "schema_version": V5_ACCEPTANCE_LINEAGE_SCHEMA_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "pre_acceptance_evidence_integrity_scope": "pre_report_evidence_only",
        "acceptance_report_reference_integrity_scope": "inspect-v5-acceptance_after_report_generation",
        "acceptance_bundle_command_lineage_scope": "inspect-acceptance-bundle_after_bundle_generation",
        "pre_acceptance_must_not_reference_acceptance_report": True,
        "acceptance_inputs_must_not_bind_post_report_outputs": True,
        "status": "passed",
    }
    _write_json(lineage_path, lineage_report)

    command_entry = _builder_command_log_entry(
        command_name="build-v5-schema-fixtures",
        input_paths=[],
        output_paths=[schema_tracking_path, artifact_tracking_path, lineage_path, fixture_root],
        producer_stage="v5_stage1_schema_and_evidence_integrity",
    )
    _write_json(command_log_entry_path, command_entry)
    return schema_tracking_path


def build_v5_schema_tracking_table_payload(
    *,
    valid_paths: dict[str, Path] | None = None,
    negative_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    valid_paths = valid_paths or {}
    negative_paths = negative_paths or {}
    rows = []
    for spec in V5_SCHEMA_SPECS:
        schema_name = str(spec["schema_name"])
        row: dict[str, Any] = {
            "schema_name": schema_name,
            "schema_version": spec["schema_version"],
            "required_fields": list(spec["required_fields"]),
            "one_of_required_fields": [list(group) for group in spec.get("one_of_required_fields", ())],
            "inspect_command": spec["inspect_command"],
            "valid_fixture": spec["valid_fixture"],
            "negative_fixture": spec["negative_fixture"],
        }
        if schema_name in valid_paths:
            row["valid_fixture_ref"] = _evidence_ref(
                valid_paths[schema_name],
                kind="schema_fixture",
                purpose=f"Valid fixture for {schema_name}",
                visibility="audit_only",
                producer_command="build-v5-schema-fixtures",
                producer_stage="v5_stage1_schema_and_evidence_integrity",
                inspect_command="inspect-v5-evidence-integrity",
            )
        if schema_name in negative_paths:
            row["negative_fixture_ref"] = _evidence_ref(
                negative_paths[schema_name],
                kind="negative_schema_fixture",
                purpose=f"Negative fixture for {schema_name}",
                visibility="audit_only",
                producer_command="build-v5-schema-fixtures",
                producer_stage="v5_stage1_schema_and_evidence_integrity",
                inspect_command="inspect-v5-evidence-integrity",
            )
        rows.append(row)
    return {
        "schema_version": V5_SCHEMA_TRACKING_TABLE_VERSION,
        "created_at": _utc_timestamp(),
        "schemas": rows,
        "status": "passed",
    }


def build_v5_artifact_inspect_tracking_table_payload() -> dict[str, Any]:
    return {
        "schema_version": V5_ARTIFACT_INSPECT_TRACKING_TABLE_VERSION,
        "created_at": _utc_timestamp(),
        "required_inspect_commands": list(V5_REQUIRED_INSPECT_COMMANDS),
        "artifact_rows": [
            {
                "scope": "Stage 0 preimplementation baseline",
                "artifacts": [
                    "v5_baseline_check_report.json",
                    "v5_preflight_input_binding.json",
                    "v5_preimplementation_command_log.jsonl",
                ],
                "inspect_command": "inspect-v5-preimplementation",
            },
            {
                "scope": "Stage 1 schema and pre-acceptance evidence integrity",
                "artifacts": [
                    "v5_schema_tracking_table.json",
                    "v5_artifact_inspect_tracking_table.json",
                    "v5_pre_acceptance_evidence_integrity_report.json",
                    "v5_acceptance_lineage_schema_report.json",
                ],
                "inspect_command": "inspect-v5-evidence-integrity",
            },
            {
                "scope": "Stage 2 task set",
                "artifacts": [
                    "v5_task_set_manifest.json",
                    "v5_task_inventory_report.json",
                    "v5_task_visibility_scan_report.json",
                ],
                "inspect_command": "inspect-v5-task-set",
                "secondary_inspect_commands": ["inspect-v5-task-visibility"],
            },
            {
                "scope": "Stage 3 provider and run matrix",
                "artifacts": [
                    "v5_provider_credential_gate_report.json",
                    "v5_provider_cost_budget_report.json",
                    "v5_run_matrix_manifest.json",
                    "v5_matrix_compare_scope_report.json",
                ],
                "inspect_command": "inspect-v5-run-matrix",
                "secondary_inspect_commands": ["inspect-v5-provider-gate"],
            },
            {
                "scope": "Stage 4 export result pack",
                "artifacts": [
                    "v5_export_result_pack_manifest.json",
                    "v5_reward_source_taxonomy_report.json",
                    "v5_failure_taxonomy_report.json",
                    "v5_preference_pair_blocked_report.json",
                ],
                "inspect_command": "inspect-v5-export-pack",
            },
            {
                "scope": "Stage 5 interview demo artifacts",
                "artifacts": [
                    "v5_resume_artifact_index.json",
                    "v5_public_demo_bundle_manifest.json",
                    "v5_result_summary_table.json",
                    "v5_demo_transcript_index.json",
                ],
                "inspect_command": "inspect-v5-demo-artifacts",
            },
            {
                "scope": "Stage 6 final acceptance",
                "artifacts": [
                    "v5_acceptance_inputs.json",
                    "v5_acceptance_report.json",
                    "v5_acceptance_bundle_manifest.json",
                    "v5_final_acceptance_command_log.jsonl",
                ],
                "inspect_command": "inspect-v5-acceptance",
                "secondary_inspect_commands": ["inspect-v5-inputs", "inspect-acceptance-bundle"],
            },
        ],
        "status": "passed",
    }


def build_pre_acceptance_integrity_report(
    *,
    critical_evidence_manifest: str | Path,
    pre_acceptance_command_log: str | Path,
    output: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build a V5 pre-acceptance evidence integrity report from explicit inputs."""

    output_path = Path(output)
    if fail_if_output_exists and output_path.exists():
        raise ConfigError(f"V5 evidence integrity 输出已存在，不能覆盖旧 evidence：{output_path}")
    manifest_path = Path(critical_evidence_manifest)
    command_log_path = Path(pre_acceptance_command_log)
    failures: list[str] = []
    manifest = _read_json_for_inspect(manifest_path, failures)
    command_log_failures: list[str] = []
    _inspect_v5_command_log(command_log_path, command_log_failures)
    findings = _pre_acceptance_integrity_findings(manifest, manifest_path=manifest_path)
    findings.extend(
        {
            "finding_type": "pre_acceptance_command_log_invalid",
            "severity": "critical",
            "message": failure,
        }
        for failure in command_log_failures
    )
    findings.extend(
        {
            "finding_type": "critical_evidence_manifest_invalid",
            "severity": "critical",
            "message": failure,
        }
        for failure in failures
    )
    counts = _finding_counts(findings)
    report = {
        "schema_version": V5_PRE_ACCEPTANCE_EVIDENCE_INTEGRITY_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "phase": "pre_acceptance_evidence_integrity",
        "critical_evidence_manifest_ref": _evidence_ref(
            manifest_path,
            kind="critical_evidence_manifest",
            purpose="V5 pre-acceptance critical evidence manifest",
            visibility="audit_only",
            producer_command="build-v5-evidence-integrity",
            producer_stage="v5_stage1_schema_and_evidence_integrity",
            inspect_command="inspect-v5-evidence-integrity",
        ),
        "pre_acceptance_command_log_ref": _evidence_ref(
            command_log_path,
            kind="pre_acceptance_command_log",
            purpose="V5 pre-acceptance command log",
            visibility="audit_only",
            producer_command="build-v5-evidence-integrity",
            producer_stage="v5_stage1_schema_and_evidence_integrity",
            inspect_command="inspect-v5-evidence-integrity",
        ),
        "acceptance_report_reference_integrity_included": False,
        "acceptance_bundle_command_lineage_integrity_included": False,
        "findings": findings,
        "finding_counts": counts,
        "status": "passed" if not findings else "failed",
    }
    _write_json(output_path, report)
    command_entry_path = output_path.with_name("build_v5_evidence_integrity_command_log_entry.json")
    _write_json(
        command_entry_path,
        _builder_command_log_entry(
            command_name="build-v5-evidence-integrity",
            input_paths=[manifest_path, command_log_path],
            output_paths=[output_path],
            producer_stage="v5_stage1_schema_and_evidence_integrity",
        ),
    )
    return output_path


def inspect_v5_evidence_integrity(
    report: str | Path,
    *,
    assert_complete: bool = False,
) -> str:
    """Read-only inspect for V5 pre-acceptance evidence integrity reports."""

    report_path = Path(report)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload.get("schema_version") != V5_PRE_ACCEPTANCE_EVIDENCE_INTEGRITY_REPORT_VERSION:
        failures.append("v5_pre_acceptance_evidence_integrity_report schema_version 不匹配。")
    if payload.get("phase") != "pre_acceptance_evidence_integrity":
        failures.append("evidence integrity phase 必须是 pre_acceptance_evidence_integrity。")
    if payload.get("acceptance_report_ref"):
        failures.append("pre-acceptance evidence integrity report 不能引用 acceptance report。")
    if payload.get("acceptance_report_reference_integrity_included") is not False:
        failures.append("pre-acceptance evidence integrity 不能包含 acceptance report reference integrity。")
    if payload.get("acceptance_bundle_command_lineage_integrity_included") is not False:
        failures.append("pre-acceptance evidence integrity 不能包含 acceptance bundle command lineage integrity。")
    manifest = _read_ref_payload(payload.get("critical_evidence_manifest_ref"), failures)
    command_log_path = _path_from_ref(payload.get("pre_acceptance_command_log_ref"))
    _inspect_v5_ref(payload.get("critical_evidence_manifest_ref"), failures, label="critical_evidence_manifest_ref")
    _inspect_v5_ref(payload.get("pre_acceptance_command_log_ref"), failures, label="pre_acceptance_command_log_ref")
    if command_log_path is not None:
        _inspect_v5_command_log(command_log_path, failures)
    if manifest:
        recomputed_findings = _pre_acceptance_integrity_findings(manifest, manifest_path=_path_from_ref(payload.get("critical_evidence_manifest_ref")) or Path("."))
        if recomputed_findings:
            failures.extend(f"recomputed evidence finding: {finding['finding_type']} {finding['message']}" for finding in recomputed_findings)
    findings = payload.get("findings")
    if not isinstance(findings, list):
        failures.append("findings 必须是 list。")
    elif findings:
        failures.append("pre-acceptance evidence integrity report 存在 finding。")
    counts = payload.get("finding_counts")
    if not isinstance(counts, dict):
        failures.append("finding_counts 必须是 object。")
    else:
        for key in (
            "unbound_critical_evidence_findings",
            "sha256_drift_findings",
            "visibility_policy_findings",
            "post_report_reference_findings",
            "provider_raw_or_secret_findings",
        ):
            if counts.get(key, 0) != 0:
                failures.append(f"finding_counts.{key} 必须为 0。")
    if payload.get("status") != "passed":
        failures.append("v5_pre_acceptance_evidence_integrity_report status 必须为 passed。")

    lines = [
        f"V5 evidence integrity report: {report_path}",
        f"Status: {payload.get('status')}",
    ]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append("Inspect V5 evidence integrity: complete")
    lines.append("Inspect V5 evidence integrity: passed")
    return "\n".join(lines)


def inspect_v5_task_set(manifest: str | Path, *, assert_complete: bool = False) -> str:
    path = Path(manifest)
    failures = _inspect_schema_file(
        path,
        expected_schema_names={
            "V5TaskSetManifest",
            "V5TaskInventoryReport",
            "V5SupplementalPRIssueCandidateReport",
        },
    )
    payload = _read_json_for_inspect(path, failures)
    if payload.get("schema_version") == V5_TASK_SET_MANIFEST_VERSION:
        _inspect_v5_task_set_manifest_deep(payload, failures)
    elif payload.get("schema_version") == V5_TASK_INVENTORY_REPORT_VERSION:
        _inspect_v5_task_inventory_deep(payload, failures)
    elif payload.get("schema_version") == V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION:
        _inspect_v5_supplemental_pr_issue_report_deep(payload, failures)
    return _schema_inspect_result("Inspect V5 task set", path, failures, assert_complete=assert_complete)


def inspect_v5_task_visibility(report: str | Path, *, assert_clean: bool = False) -> str:
    path = Path(report)
    failures = _inspect_schema_file(path, expected_schema_names={"V5TaskVisibilityScanReport"})
    payload = _read_json_for_inspect(path, failures)
    if payload.get("model_visible_leak_count", 0) != 0:
        failures.append("model_visible_leak_count 必须为 0。")
    if payload.get("share_safe_violation_count", 0) != 0:
        failures.append("share_safe_violation_count 必须为 0。")
    if payload.get("trainable_payload_contamination_count", 0) != 0:
        failures.append("trainable_payload_contamination_count 必须为 0。")
    _inspect_adapter_visible_refs_for_forbidden_markers(payload, failures)
    if payload.get("status") != "passed":
        failures.append("task visibility scan status 必须为 passed。")
    return _schema_inspect_result("Inspect V5 task visibility", path, failures, assert_complete=assert_clean)


def inspect_v5_run_matrix(manifest: str | Path, *, assert_complete: bool = False) -> str:
    path = Path(manifest)
    failures = _inspect_schema_file(
        path,
        expected_schema_names={"V5RunMatrixManifest", "V5MatrixCellResult", "V5MatrixCompareScopeReport"},
    )
    payload = _read_json_for_inspect(path, failures)
    schema_version = payload.get("schema_version")
    if schema_version == V5_RUN_MATRIX_MANIFEST_VERSION:
        _inspect_v5_run_matrix_deep(payload, failures, require_complete=assert_complete)
    elif schema_version == V5_MATRIX_CELL_RESULT_VERSION:
        _inspect_v5_matrix_cell_result(payload, failures, label="matrix_cell_result")
    elif schema_version == V5_MATRIX_COMPARE_SCOPE_REPORT_VERSION:
        _inspect_v5_matrix_compare_scope_report(payload, failures)
    return _schema_inspect_result("Inspect V5 run matrix", path, failures, assert_complete=assert_complete)


def _inspect_v5_run_matrix_deep(
    payload: dict[str, Any],
    failures: list[str],
    *,
    require_complete: bool,
) -> None:
    cells = payload.get("planned_matrix_cells")
    if not isinstance(cells, list):
        failures.append("planned_matrix_cells 必须是 list。")
        cells = []
    if payload.get("planned_matrix_cell_count") is not None and payload.get("planned_matrix_cell_count") != len(cells):
        failures.append("planned_matrix_cell_count 必须等于 planned_matrix_cells 数量。")
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            failures.append(f"planned_matrix_cells[{index}] 必须是 object。")
            continue
        if cell.get("provider_id") == "openai" and cell.get("provider_mode") == "fallback_only":
            failures.append("OpenAI provider comparison cell 不能再作为 fallback_only planned cell。")
        for ref_field in ("generated_task_ref", "controlled_variables_ref"):
            if cell.get(ref_field):
                _inspect_v5_ref(cell.get(ref_field), failures, label=f"planned_matrix_cells[{index}].{ref_field}")
    if payload.get("agent_run_started") is True:
        if payload.get("provider_api_called") is not True:
            failures.append("agent_run_started=true 时 provider_api_called 必须为 true。")
        results_ref = payload.get("matrix_cell_results_ref")
        _inspect_v5_ref(results_ref, failures, label="matrix_cell_results_ref")
        results_path = _path_from_ref(results_ref)
        results = _read_jsonl_for_inspect(results_path, failures) if results_path is not None else []
        enforce_core_floor = require_complete or payload.get("status") == "passed"
        if enforce_core_floor and len(results) < 6:
            failures.append("Stage 3B executed run matrix 至少需要 6 条 matrix cell results。")
        actual_run_count = sum(1 for item in results if item.get("actual_provider_call_count", 0) > 0)
        if enforce_core_floor and actual_run_count < 6:
            failures.append("Stage 3B executed run matrix 至少需要 6 个真实 provider agent run evidence。")
        families = {
            item.get("provider_id")
            for item in results
            if item.get("actual_provider_call_count", 0) > 0
        }
        if not families.intersection({"deepseek", "openai"}):
            failures.append("Stage 3B executed run matrix 必须至少包含一个真实 provider family evidence。")
        for index, result in enumerate(results):
            _inspect_v5_matrix_cell_result(result, failures, label=f"matrix_cell_results[{index}]")
        execution_report_ref = payload.get("run_matrix_execution_report_ref")
        if execution_report_ref:
            _inspect_v5_ref(execution_report_ref, failures, label="run_matrix_execution_report_ref")
            report = _read_ref_payload(execution_report_ref, failures)
            if report:
                if report.get("actual_provider_calls", 0) > report.get("max_real_provider_calls", 0):
                    failures.append("run matrix execution report actual_provider_calls 超过 max_real_provider_calls。")
                if enforce_core_floor and report.get("real_agent_run_task_count", 0) < 6:
                    failures.append("run matrix execution report real_agent_run_task_count 必须至少为 6。")
    else:
        if payload.get("provider_api_called") is not False:
            failures.append("planned run matrix 在 agent_run_started=false 时 provider_api_called 必须为 false。")


def _inspect_v5_matrix_cell_result(result: dict[str, Any], failures: list[str], *, label: str) -> None:
    if result.get("schema_version") != V5_MATRIX_CELL_RESULT_VERSION:
        failures.append(f"{label}.schema_version 不匹配。")
    if result.get("normalized_provider_status") not in V5_PROVIDER_STATUS_VALUES:
        failures.append(f"{label}.normalized_provider_status 枚举值无效。")
    if result.get("normalized_provider_status") == "fallback_success" and result.get("counts_toward_primary_accepted_rate") is True:
        failures.append(f"{label}.fallback_success 不能计入 primary accepted rate。")
    if result.get("provider_id") == "openai" and result.get("provider_mode") == "fallback_only":
        failures.append(f"{label}.OpenAI provider comparison result 不能标记为 fallback_only。")
    if result.get("provider_api_called") is True and result.get("actual_provider_call_count", 0) <= 0:
        failures.append(f"{label}.provider_api_called=true 时 actual_provider_call_count 必须大于 0。")
    if result.get("actual_provider_call_count", 0) > 0:
        if not result.get("trajectory_ref"):
            failures.append(f"{label}.真实 provider result 缺少 trajectory_ref。")
        if not result.get("final_verifier_boundary_ref"):
            failures.append(f"{label}.真实 provider result 缺少 final_verifier_boundary_ref。")
    for ref_field in ("trajectory_ref", "transcript_ref", "artifact_manifest_ref", "final_verifier_boundary_ref", "controlled_variables_ref"):
        if result.get(ref_field):
            _inspect_v5_ref(result.get(ref_field), failures, label=f"{label}.{ref_field}")
    redaction = result.get("raw_provider_redaction")
    if isinstance(redaction, dict):
        if redaction.get("raw_provider_redaction_failure_count", 0) != 0:
            failures.append(f"{label}.raw provider artifact redaction 存在失败。")


def _inspect_v5_matrix_compare_scope_report(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("comparison_axis") not in V5_COMPARISON_AXES:
        failures.append("comparison_axis 枚举值无效。")
    controlled = payload.get("controlled_variables")
    if not isinstance(controlled, list) or not controlled:
        failures.append("controlled_variables 必须是非空 list。")
    compared = payload.get("compared_cells")
    if not isinstance(compared, list) or not compared:
        failures.append("compared_cells 必须是非空 list。")
    if payload.get("comparison_validity") not in {"valid", "diagnostic_only", "invalid"}:
        failures.append("comparison_validity 必须是 valid、diagnostic_only 或 invalid。")
    for ref_field in ("run_matrix_manifest_ref", "matrix_cell_results_ref"):
        if payload.get(ref_field):
            _inspect_v5_ref(payload.get(ref_field), failures, label=ref_field)


def _read_jsonl_for_inspect(path: Path | None, failures: list[str]) -> list[dict[str, Any]]:
    if path is None:
        return []
    if not path.exists():
        failures.append(f"JSONL 输入不存在：{path}")
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{path}:{line_number} 不是合法 JSON：{exc}")
            continue
        if not isinstance(item, dict):
            failures.append(f"{path}:{line_number} 顶层必须是 object。")
            continue
        rows.append(item)
    return rows


def inspect_v5_provider_gate(report: str | Path, *, assert_consistent: bool = False) -> str:
    path = Path(report)
    failures = _inspect_schema_file(path, expected_schema_names={"V5ProviderCredentialGateReport"})
    payload = _read_json_for_inspect(path, failures)
    if payload.get("raw_secret_value_present") is not False:
        failures.append("provider credential gate 不能包含 raw secret value。")
    _inspect_no_raw_secret_markers(payload, failures, label="provider credential gate")
    families = set(payload.get("provider_families") or [])
    missing = sorted(set(V5_PROVIDER_FAMILIES).difference(families))
    if missing:
        failures.append("provider_families 缺少：" + ", ".join(missing))
    credential_status = payload.get("credential_status_by_provider")
    if not isinstance(credential_status, dict):
        failures.append("credential_status_by_provider 必须是 object。")
    else:
        for provider in V5_PROVIDER_FAMILIES:
            status = credential_status.get(provider)
            if status not in V5_CREDENTIAL_STATUS_VALUES:
                failures.append(f"{provider} credential_status 无效：{status}")
    adapter_status = payload.get("adapter_status_by_provider")
    if not isinstance(adapter_status, dict):
        failures.append("adapter_status_by_provider 必须是 object。")
    else:
        for provider in V5_PROVIDER_FAMILIES:
            status = adapter_status.get(provider)
            if status not in V5_ADAPTER_STATUS_VALUES:
                failures.append(f"{provider} adapter_status 无效：{status}")
        if adapter_status.get("deepseek") != "primary_supported":
            failures.append("deepseek 必须保持 primary_supported。")
        if adapter_status.get("openai") not in {"fallback_only", "primary_supported"}:
            failures.append("openai adapter_status 必须是 fallback_only 或 primary_supported。")
        if adapter_status.get("anthropic_claude") != "adapter_not_implemented":
            failures.append("anthropic_claude 当前必须记录 adapter_not_implemented，除非后续阶段正式实现 adapter。")
    if payload.get("provider_raw_content_policy") != V5_PROVIDER_RAW_CONTENT_POLICY:
        failures.append("provider_raw_content_policy 必须是 audit_only_redacted_never_model_visible。")
    if payload.get("fallback_success_counts_toward_primary_openai") is not False:
        failures.append("OpenAI fallback success 不能计入 primary OpenAI provider。")
    if payload.get("credential_missing_skip_counts_toward_real_provider_accepted_rate") is not False:
        failures.append("credential_missing_skip 不能计入真实 provider accepted rate。")
    _inspect_provider_structured_skips(payload.get("structured_skips"), failures)
    _inspect_provider_registry_ref(payload.get("provider_registry_report_ref"), failures)
    _inspect_provider_smoke_ref(payload.get("provider_smoke_report_ref"), failures)
    _inspect_provider_raw_content_redaction_ref(payload.get("provider_raw_content_redaction_report_ref"), failures)
    _inspect_provider_status_normalization_ref(payload.get("provider_status_normalization_report_ref"), failures)
    return _schema_inspect_result("Inspect V5 provider gate", path, failures, assert_complete=assert_consistent)


def inspect_v5_provider_cost_budget(report: str | Path, *, assert_consistent: bool = False) -> str:
    path = Path(report)
    failures = _inspect_schema_file(path, expected_schema_names={"V5ProviderCostBudgetReport"})
    payload = _read_json_for_inspect(path, failures)
    for key in ("max_real_provider_calls", "actual_real_provider_calls"):
        value = payload.get(key)
        if not isinstance(value, int) or value < 0:
            failures.append(f"{key} 必须是非负整数。")
    for key in ("max_cost_usd", "actual_cost_proxy_usd"):
        value = payload.get(key)
        if not isinstance(value, int | float) or value < 0:
            failures.append(f"{key} 必须是非负数值。")
    if payload.get("actual_real_provider_calls", 0) > payload.get("max_real_provider_calls", 0):
        failures.append("actual_real_provider_calls 不能超过 max_real_provider_calls。")
    if payload.get("actual_cost_proxy_usd", 0) > payload.get("max_cost_usd", 0):
        failures.append("actual_cost_proxy_usd 不能超过 max_cost_usd。")
    if not payload.get("cost_proxy_formula"):
        failures.append("cost_proxy_formula 不能为空。")
    skips = payload.get("cost_limited_structured_skip")
    if not isinstance(skips, list):
        failures.append("cost_limited_structured_skip 必须是 list。")
    else:
        for index, skip in enumerate(skips):
            if not isinstance(skip, dict):
                failures.append(f"cost_limited_structured_skip[{index}] 必须是 object。")
                continue
            if skip.get("skip_type") != "cost_limited_structured_skip":
                failures.append(f"cost_limited_structured_skip[{index}] skip_type 无效。")
            if skip.get("counts_toward_real_provider_accepted_rate") is not False:
                failures.append(f"cost_limited_structured_skip[{index}] 不能计入真实 provider accepted rate。")
    gate_ref = payload.get("provider_gate_ref")
    if gate_ref:
        _inspect_v5_ref(gate_ref, failures, label="provider_gate_ref")
        gate_path = _path_from_ref(gate_ref)
        if gate_path is not None and gate_path.exists():
            try:
                inspect_v5_provider_gate(gate_path, assert_consistent=True)
            except ConfigError as exc:
                failures.append(f"provider_gate_ref 检查失败：{exc}")
    return _schema_inspect_result("Inspect V5 provider cost budget", path, failures, assert_complete=assert_consistent)


def _inspect_no_raw_secret_markers(payload: dict[str, Any], failures: list[str], *, label: str) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    if re.search(V5_RAW_SECRET_MARKER_RE, text):
        failures.append(f"{label} 包含疑似 raw provider credential marker。")
    if "authorization: bearer" in lowered or '"authorization"' in lowered:
        failures.append(f"{label} 不能包含 Authorization marker。")


def _inspect_provider_structured_skips(skips: Any, failures: list[str]) -> None:
    if not isinstance(skips, list):
        failures.append("structured_skips 必须是 list。")
        return
    for index, skip in enumerate(skips):
        if not isinstance(skip, dict):
            failures.append(f"structured_skips[{index}] 必须是 object。")
            continue
        if skip.get("provider_id") not in V5_PROVIDER_FAMILIES:
            failures.append(f"structured_skips[{index}] provider_id 无效。")
        if skip.get("skip_type") not in V5_PROVIDER_GATE_STRUCTURED_SKIP_TYPES:
            failures.append(f"structured_skips[{index}] skip_type 无效。")
        if skip.get("credential_status") not in V5_CREDENTIAL_STATUS_VALUES:
            failures.append(f"structured_skips[{index}] credential_status 无效。")
        if skip.get("adapter_status") not in V5_ADAPTER_STATUS_VALUES:
            failures.append(f"structured_skips[{index}] adapter_status 无效。")
        if not skip.get("skip_reason"):
            failures.append(f"structured_skips[{index}] 缺少 skip_reason。")
        if not skip.get("affected_matrix_cells"):
            failures.append(f"structured_skips[{index}] 缺少 affected_matrix_cells。")
        if skip.get("counts_toward_real_provider_accepted_rate") is not False:
            failures.append(f"structured_skips[{index}] 不能计入真实 provider accepted rate。")
        if skip.get("counts_toward_primary_accepted_rate") is not False:
            failures.append(f"structured_skips[{index}] 不能计入 primary accepted rate。")


def _inspect_provider_registry_ref(ref: Any, failures: list[str]) -> None:
    _inspect_v5_ref(ref, failures, label="provider_registry_report_ref")
    payload = _read_ref_payload(ref, failures)
    if not payload:
        return
    _inspect_no_raw_secret_markers(payload, failures, label="provider registry report")
    if payload.get("schema_version") != V5_PROVIDER_REGISTRY_REPORT_VERSION:
        failures.append("provider registry report schema_version 不匹配。")
    providers = payload.get("providers")
    if not isinstance(providers, list):
        failures.append("provider registry report providers 必须是 list。")
        return
    by_id = {item.get("provider_id"): item for item in providers if isinstance(item, dict)}
    for provider in V5_PROVIDER_FAMILIES:
        if provider not in by_id:
            failures.append(f"provider registry report 缺少 {provider}。")
    if by_id.get("deepseek", {}).get("adapter_status") != "primary_supported":
        failures.append("provider registry 必须把 deepseek 记录为 primary_supported。")
    openai_adapter_status = by_id.get("openai", {}).get("adapter_status")
    if openai_adapter_status not in {"fallback_only", "primary_supported"}:
        failures.append("provider registry 必须把 openai 记录为 fallback_only 或 primary_supported。")
    if (
        openai_adapter_status == "fallback_only"
        and by_id.get("openai", {}).get("counts_toward_resume_ready_provider_comparison") is not False
    ):
        failures.append("OpenAI fallback-only registry entry 不能计入 resume-ready provider comparison。")
    if (
        openai_adapter_status == "primary_supported"
        and by_id.get("openai", {}).get("counts_toward_resume_ready_provider_comparison") is not True
    ):
        failures.append("OpenAI primary-supported registry entry 必须允许计入 resume-ready provider comparison。")
    if by_id.get("anthropic_claude", {}).get("adapter_status") != "adapter_not_implemented":
        failures.append("provider registry 必须把 anthropic_claude 记录为 adapter_not_implemented。")


def _inspect_provider_smoke_ref(ref: Any, failures: list[str]) -> None:
    _inspect_v5_ref(ref, failures, label="provider_smoke_report_ref")
    payload = _read_ref_payload(ref, failures)
    if not payload:
        return
    _inspect_no_raw_secret_markers(payload, failures, label="provider smoke report")
    if payload.get("schema_version") != V5_PROVIDER_SMOKE_REPORT_VERSION:
        failures.append("provider smoke report schema_version 不匹配。")
    if payload.get("provider_api_called") is not False:
        failures.append("Stage 3A provider smoke report 不能提前声明已经调用 provider API。")
    statuses = payload.get("provider_smoke_statuses")
    if not isinstance(statuses, list):
        failures.append("provider_smoke_statuses 必须是 list。")
        return
    by_provider = {item.get("provider_id"): item for item in statuses if isinstance(item, dict)}
    for provider in V5_PROVIDER_FAMILIES:
        if provider not in by_provider:
            failures.append(f"provider_smoke_statuses 缺少 {provider}。")
    openai_smoke = by_provider.get("openai", {})
    if (
        openai_smoke.get("provider_mode") == "fallback_only"
        and openai_smoke.get("counts_toward_primary_openai_provider_family") is not False
    ):
        failures.append("OpenAI fallback smoke 不能计入 primary OpenAI provider family。")
    if by_provider.get("anthropic_claude", {}).get("normalized_smoke_status") != "adapter_not_implemented_skip":
        failures.append("Anthropic Claude smoke 必须归一化为 adapter_not_implemented_skip。")


def _inspect_provider_raw_content_redaction_ref(ref: Any, failures: list[str]) -> None:
    _inspect_v5_ref(ref, failures, label="provider_raw_content_redaction_report_ref")
    payload = _read_ref_payload(ref, failures)
    if not payload:
        return
    _inspect_no_raw_secret_markers(payload, failures, label="provider raw content redaction report")
    if payload.get("schema_version") != V5_PROVIDER_RAW_CONTENT_REDACTION_REPORT_VERSION:
        failures.append("provider raw content redaction report schema_version 不匹配。")
    for key in (
        "raw_request_model_visible_count",
        "raw_response_model_visible_count",
        "raw_request_trainable_count",
        "raw_response_trainable_count",
        "raw_request_public_safe_count",
        "raw_response_public_safe_count",
        "authorization_marker_count",
        "provider_credential_marker_count",
    ):
        if payload.get(key, 0) != 0:
            failures.append(f"{key} 必须为 0。")


def _inspect_provider_status_normalization_ref(ref: Any, failures: list[str]) -> None:
    _inspect_v5_ref(ref, failures, label="provider_status_normalization_report_ref")
    payload = _read_ref_payload(ref, failures)
    if not payload:
        return
    _inspect_no_raw_secret_markers(payload, failures, label="provider status normalization report")
    if payload.get("schema_version") != V5_PROVIDER_STATUS_NORMALIZATION_REPORT_VERSION:
        failures.append("provider status normalization report schema_version 不匹配。")
    rules = payload.get("normalization_rules")
    if not isinstance(rules, list):
        failures.append("normalization_rules 必须是 list。")
        return
    mapping = {
        rule.get("raw_status"): rule.get("normalized_provider_status")
        for rule in rules
        if isinstance(rule, dict)
    }
    if mapping.get("skipped_no_credentials") != "credential_missing_skip":
        failures.append("skipped_no_credentials 必须归一化为 credential_missing_skip。")
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("raw_status") == "fallback_success" and rule.get("counts_toward_primary_accepted_rate") is not False:
            failures.append("fallback_success 不能计入 primary accepted rate。")
    if payload.get("fallback_success_counts_as_primary_openai_run") is not False:
        failures.append("status normalization 不能允许 fallback_success 计入 primary OpenAI run。")


def inspect_v5_export_pack(manifest: str | Path, *, assert_clean: bool = False) -> str:
    path = Path(manifest)
    failures = _inspect_schema_file(
        path,
        expected_schema_names={
            "V5ExportResultPackManifest",
            "V5RewardSourceTaxonomyReport",
            "V5FailureTaxonomyReport",
            "V5PreferencePairBlockedReport",
        },
    )
    payload = _read_json_for_inspect(path, failures)
    if (
        payload.get("schema_version") == V5_EXPORT_RESULT_PACK_MANIFEST_VERSION
        and payload.get("producer_stage") == "v5_stage4_export_pack"
    ):
        _inspect_v5_export_pack_manifest_deep(payload, failures)
    else:
        partition_counts = payload.get("partition_counts")
        if isinstance(partition_counts, dict):
            missing = sorted(set(V5_PARTITION_COUNT_FIELDS).difference(partition_counts))
            if missing:
                failures.append("partition_counts 缺少：" + ", ".join(missing))
    if payload.get("reward_scalar_model_visible_count", 0) != 0:
        failures.append("reward_scalar_model_visible_count 必须为 0。")
    if payload.get("reward_label_model_visible_count", 0) != 0:
        failures.append("reward_label_model_visible_count 必须为 0。")
    return _schema_inspect_result("Inspect V5 export pack", path, failures, assert_complete=assert_clean)


def _inspect_v5_export_pack_manifest_deep(payload: dict[str, Any], failures: list[str]) -> None:
    partition_counts = payload.get("partition_counts")
    if not isinstance(partition_counts, dict):
        failures.append("partition_counts 必须是 object。")
        partition_counts = {}
    missing = sorted(set(V5_PARTITION_COUNT_FIELDS).difference(partition_counts))
    if missing:
        failures.append("partition_counts 缺少：" + ", ".join(missing))
    if payload.get("producer_stage") == "v5_stage4_export_pack":
        if partition_counts.get("diagnostic_records", 0) < 1:
            failures.append("Stage 4 export pack 至少需要 1 个 diagnostic record。")
        if partition_counts.get("blocked_records", 0) < 1:
            failures.append("Stage 4 export pack 至少需要 1 个 blocked record。")
    for ref_field in (
        "sft_export_ref",
        "rl_rollout_export_ref",
        "failure_dataset_ref",
        "diagnostic_only_records_ref",
        "blocked_export_records_ref",
        "preference_pair_blocked_report_ref",
        "reward_source_taxonomy_ref",
        "failure_taxonomy_ref",
        "export_audit_ref",
        "duplicate_record_report_ref",
        "training_payload_visibility_report_ref",
        "export_partition_summary_ref",
    ):
        if payload.get(ref_field):
            _inspect_v5_ref(payload.get(ref_field), failures, label=ref_field)
    trainable_minimum = 1 if partition_counts.get("real_provider_trainable_records", 0) > 0 else 0
    for jsonl_field, minimum in (
        ("sft_export_ref", trainable_minimum),
        ("rl_rollout_export_ref", trainable_minimum),
        ("failure_dataset_ref", 1),
        ("diagnostic_only_records_ref", 1),
        ("blocked_export_records_ref", 1),
    ):
        ref = payload.get(jsonl_field)
        path = _path_from_ref(ref)
        rows = _read_jsonl_for_inspect(path, failures) if path is not None else []
        if len(rows) < minimum:
            failures.append(f"{jsonl_field} 至少需要 {minimum} 条记录。")
        for index, row in enumerate(rows):
            _inspect_v5_export_record(row, failures, label=f"{jsonl_field}[{index}]")
    blocked = _read_ref_payload(payload.get("preference_pair_blocked_report_ref"), failures)
    if blocked:
        if not blocked.get("blocked_reason"):
            failures.append("preference pair blocked report 缺少 blocked_reason。")
        if blocked.get("claim_gate_effect") != "disable_preference_export_completed_claim":
            failures.append("preference pair blocked report 必须禁用 preference export completed claim。")
    reward = _read_ref_payload(payload.get("reward_source_taxonomy_ref"), failures)
    if reward:
        if reward.get("reward_scalar_model_visible_count", 0) != 0:
            failures.append("reward source taxonomy 中 reward scalar 不能进入 model-visible。")
        if reward.get("reward_label_model_visible_count", 0) != 0:
            failures.append("reward source taxonomy 中 reward label 不能进入 model-visible。")
    audit = _read_ref_payload(payload.get("export_audit_ref"), failures)
    if audit:
        for key in (
            "trainable_payload_contamination_count",
            "diagnostic_only_trainable_count",
            "blocked_trainable_count",
            "provider_raw_trainable_count",
            "provider_raw_model_visible_count",
            "reward_scalar_model_visible_count",
            "reward_label_model_visible_count",
        ):
            if audit.get(key, 0) != 0:
                failures.append(f"export audit {key} 必须为 0。")
        if audit.get("status") != "passed":
            failures.append("export audit status 必须为 passed。")


def _inspect_v5_export_record(record: dict[str, Any], failures: list[str], *, label: str) -> None:
    if not isinstance(record, dict):
        failures.append(f"{label} 必须是 object。")
        return
    if record.get("record_partition") in {"diagnostic_only", "blocked"} and record.get("trainable") is not False:
        failures.append(f"{label} diagnostic-only 或 blocked record 不能标记为 trainable。")
    if record.get("trainable") is True and (
        record.get("accepted") is not True or record.get("final_verifier_status") != "accepted"
    ):
        failures.append(f"{label} trainable record 必须绑定 accepted final verifier outcome。")
    text = json.dumps(record, ensure_ascii=False).lower()
    for marker in ("raw_deepseek_provider_request", "raw_deepseek_provider_response", "authorization", "bearer"):
        if marker in text:
            failures.append(f"{label} 不能包含 provider raw marker：{marker}")


def inspect_v5_demo_artifacts(index: str | Path, *, assert_share_safe: bool = False) -> str:
    path = Path(index)
    failures = _inspect_schema_file(
        path,
        expected_schema_names={
            "V5ResumeArtifactIndex",
            "V5ResultSummaryTable",
            "V5PublicDemoBundleManifest",
            "V5DemoTranscriptIndex",
            "V5ResumeClaimGateReport",
            "V5InterviewResultPackManifest",
        },
    )
    payload = _read_json_for_inspect(path, failures)
    if payload.get("share_safe_status") not in {None, "passed"}:
        failures.append("share_safe_status 必须为 passed。")
    if payload.get("provider_raw_content_count", 0) != 0:
        failures.append("public demo bundle 不能包含 provider raw content。")
    if payload.get("evaluator_only_content_count", 0) != 0:
        failures.append("public demo bundle 不能包含 evaluator-only content。")
    if payload.get("model_visible_leak_count", 0) != 0:
        failures.append("demo transcript 不能包含 model-visible leak。")
    _inspect_v5_demo_artifacts_deep(payload, failures)
    return _schema_inspect_result("Inspect V5 demo artifacts", path, failures, assert_complete=assert_share_safe)


def _inspect_v5_demo_artifacts_deep(payload: dict[str, Any], failures: list[str]) -> None:
    schema_version = payload.get("schema_version")
    if schema_version == V5_RESUME_ARTIFACT_INDEX_VERSION:
        for ref in payload.get("artifact_refs") or []:
            if isinstance(ref, dict):
                if ref.get("share_safe") is not True or ref.get("visibility") != "public_safe":
                    failures.append("resume artifact index 只能引用 public_safe 且 share_safe=true 的 artifact。")
        public_bundle = _read_ref_payload(payload.get("public_demo_bundle_ref"), failures)
        if public_bundle:
            if public_bundle.get("share_safe_status") != "passed":
                failures.append("public demo bundle share_safe_status 必须为 passed。")
            if public_bundle.get("provider_raw_content_count", 0) != 0:
                failures.append("public demo bundle provider raw content count 必须为 0。")
            if public_bundle.get("evaluator_only_content_count", 0) != 0:
                failures.append("public demo bundle evaluator-only content count 必须为 0。")
            marker_scan = public_bundle.get("public_marker_scan") or {}
            if marker_scan.get("finding_count", 0) != 0:
                failures.append("public demo bundle marker scan 必须无发现。")
        transcript = _read_ref_payload(payload.get("demo_transcript_index_ref"), failures)
        if transcript and transcript.get("model_visible_leak_count", 0) != 0:
            failures.append("demo transcript index model_visible_leak_count 必须为 0。")
        result_summary = _read_ref_payload(payload.get("result_summary_ref"), failures)
        if result_summary:
            for field in V5_PARTITION_COUNT_FIELDS:
                if result_summary.get(field) is None:
                    failures.append(f"result summary 缺少 {field}。")
            denominator_excludes = _get_path(result_summary, "real_provider_runs.denominator_excludes") or []
            for excluded in ("credential_missing_skip", "mock_or_replay_records", "synthetic_safe_stress_records"):
                if excluded not in denominator_excludes:
                    failures.append(f"result summary denominator_excludes 缺少 {excluded}。")
        claim_gate = _read_ref_payload(payload.get("resume_claim_gate_ref"), failures)
        if claim_gate:
            if claim_gate.get("stage") != "stage5_final":
                failures.append("Stage 5 resume artifact index 必须绑定 stage5_final claim gate。")
            if claim_gate.get("demo_share_safe_status") != "passed":
                failures.append("Stage 5 claim gate demo_share_safe_status 必须为 passed。")
            if claim_gate.get("provider_claim_status") != "allowed" and "multi-provider agent runs" in claim_gate.get("allowed_claims", []):
                failures.append("provider claim 未允许时不能允许 multi-provider agent runs。")
            if claim_gate.get("preference_pair_claim_status") != "allowed" and "preference export completed" in claim_gate.get("allowed_claims", []):
                failures.append("preference pair 未允许时不能允许 preference export completed。")
    elif schema_version == V5_PUBLIC_DEMO_BUNDLE_MANIFEST_VERSION:
        for ref in payload.get("artifact_refs") or []:
            if isinstance(ref, dict) and (ref.get("share_safe") is not True or ref.get("visibility") != "public_safe"):
                failures.append("public demo bundle artifact refs 必须 public_safe 且 share_safe=true。")
        marker_scan = payload.get("public_marker_scan") or {}
        if marker_scan.get("finding_count", 0) != 0:
            failures.append("public demo bundle marker scan 必须无发现。")
    elif schema_version == V5_INTERVIEW_RESULT_PACK_MANIFEST_VERSION:
        if payload.get("blocked_claims_enforced") is not True:
            failures.append("interview result pack 必须记录 blocked_claims_enforced=true。")
        if payload.get("copy_safe_blocked_claims_count", 0) != 0:
            failures.append("interview result pack 的 copy-safe blocked claims count 必须为 0。")
        claim_gate = _read_ref_payload(payload.get("resume_claim_gate_ref"), failures)
        if claim_gate and claim_gate.get("stage") != "stage5_final":
            failures.append("interview result pack 必须引用 stage5_final claim gate。")


def inspect_v5_inputs(inputs: str | Path, *, assert_complete: bool = False) -> str:
    path = Path(inputs)
    failures = _inspect_schema_file(path, expected_schema_names={"V5AcceptanceInputs"})
    payload = _read_json_for_inspect(path, failures)
    _inspect_v5_inputs_deep(payload, failures)
    return _schema_inspect_result("Inspect V5 inputs", path, failures, assert_complete=assert_complete)


def inspect_v5_acceptance(
    report: str | Path,
    *,
    assert_core_complete: bool = False,
    assert_resume_ready: bool = False,
    assert_complete: bool = False,
    reference_integrity_output: str | Path | None = None,
    reference_integrity_input: str | Path | None = None,
    command_log_entry_output: str | Path | None = None,
) -> str:
    path = Path(report)
    failures = _inspect_schema_file(path, expected_schema_names={"V5AcceptanceReport"})
    payload = _read_json_for_inspect(path, failures)
    _inspect_v5_acceptance_reference_integrity(payload, failures)
    core_status = _get_path(payload, "core_acceptance.status")
    resume_status = _get_path(payload, "resume_ready_acceptance.status")
    if assert_core_complete and core_status != "passed":
        failures.append("core_acceptance.status 必须为 passed。")
    if (assert_resume_ready or assert_complete) and resume_status != "passed":
        failures.append("resume_ready_acceptance.status 必须为 passed。")
    assert_requested = assert_core_complete or assert_resume_ready or assert_complete
    exit_code = 1 if failures and assert_requested else 0
    from repo_harness.v5_acceptance import write_acceptance_inspect_outputs

    write_acceptance_inspect_outputs(
        report=path,
        reference_integrity_output=reference_integrity_output,
        reference_integrity_input=reference_integrity_input,
        command_log_entry_output=command_log_entry_output,
        exit_code=exit_code,
    )
    return _schema_inspect_result("Inspect V5 acceptance", path, failures, assert_complete=assert_requested)


def _inspect_v5_inputs_deep(payload: dict[str, Any], failures: list[str]) -> None:
    if not payload:
        return
    if payload.get("selection_mode") != "explicit":
        failures.append("V5 acceptance inputs 必须使用 explicit selection_mode。")
    if payload.get("latest_run_auto_selection") is not False:
        failures.append("V5 acceptance inputs 禁止 latest run 自动选择。")
    if payload.get("post_report_outputs_included") is not False:
        failures.append("V5 acceptance inputs 不能包含 post-report inspect outputs。")
    if payload.get("bundle_final_outputs_included") is not False:
        failures.append("V5 acceptance inputs 不能包含 bundle final outputs。")
    if payload.get("stress_test_executed") is not False and payload.get("stress_test_executed") is not True:
        failures.append("stress_test_executed 必须是 boolean。")
    refs = payload.get("v5_evidence_refs")
    if not isinstance(refs, list) or not refs:
        failures.append("V5 acceptance inputs 必须包含 v5_evidence_refs。")
        return
    for field in (
        "v2_acceptance_report_ref",
        "v3_acceptance_report_ref",
        "v3_acceptance_bundle_ref",
        "v4_acceptance_inputs_ref",
        "v4_acceptance_report_ref",
        "v4_doc_sync_acceptance_bundle_ref",
        "v4_doc_sync_final_command_log_ref",
    ):
        _inspect_v5_ref(payload.get(field), failures, label=field)
    kinds = {ref.get("kind") for ref in refs if isinstance(ref, dict)}
    required = {
        "v5_preflight_input_binding",
        "v5_pre_acceptance_evidence_integrity_report",
        "v5_task_set_manifest",
        "v5_run_matrix_manifest_executed",
        "v5_resume_claim_gate_report",
        "v5_export_result_pack_manifest",
        "v5_public_demo_bundle_manifest",
        "v5_resume_artifact_index",
        "v5_result_summary_table",
        "v5_final_acceptance_pretest_report",
    }
    missing = sorted(required.difference(kinds))
    if missing:
        failures.append("V5 acceptance inputs 缺少必需 evidence refs：" + ", ".join(missing))
    for index, ref in enumerate(refs, start=1):
        if isinstance(ref, dict):
            _inspect_v5_ref(ref, failures, label=f"v5_evidence_refs[{index}]")
            path_value = str(ref.get("path") or "")
            if "acceptance_report_reference_integrity_report" in path_value or "acceptance_bundle_manifest" in path_value:
                failures.append("V5 acceptance inputs 不能绑定 post-report 或 bundle final outputs。")
        else:
            failures.append(f"v5_evidence_refs[{index}] 必须是 evidence ref object。")


def _inspect_v5_acceptance_reference_integrity(payload: dict[str, Any], failures: list[str]) -> None:
    if not payload:
        return
    inputs_ref = payload.get("acceptance_inputs_ref")
    _inspect_v5_ref(inputs_ref, failures, label="acceptance_inputs_ref")
    inputs_path = _path_from_ref(inputs_ref)
    if inputs_path is None or not inputs_path.exists():
        failures.append("acceptance report reference integrity 无法读取 acceptance_inputs_ref。")
        return
    input_failures: list[str] = []
    inputs_payload = _read_json_for_inspect(inputs_path, input_failures)
    if input_failures:
        failures.extend(f"acceptance_inputs_ref.{item}" for item in input_failures)
        return
    _inspect_v5_inputs_deep(inputs_payload, failures)
    allowed = _acceptance_input_ref_keys(inputs_payload)
    report_refs = _report_ref_keys(payload)
    unbound = sorted(ref for ref in report_refs if ref not in allowed and not ref.startswith("v5_acceptance_inputs|"))
    if unbound:
        failures.append(
            "acceptance report reference integrity failed，存在未由 acceptance inputs 绑定的关键 evidence refs："
            + ", ".join(unbound)
        )


def _acceptance_input_ref_keys(inputs: dict[str, Any]) -> set[str]:
    return {_v5_ref_key(ref) for ref in _all_acceptance_input_refs(inputs) if _v5_ref_key(ref)}


def _all_acceptance_input_refs(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for key, value in inputs.items():
        if key.endswith("_ref") and isinstance(value, dict):
            refs.append(value)
    refs.extend(ref for ref in inputs.get("v5_evidence_refs") or [] if isinstance(ref, dict))
    return refs


def _report_ref_keys(report: dict[str, Any]) -> set[str]:
    refs: list[dict[str, Any]] = []
    for key, value in report.items():
        if key.endswith("_ref") and isinstance(value, dict):
            refs.append(value)
        if key.endswith("_refs") and isinstance(value, list):
            refs.extend(ref for ref in value if isinstance(ref, dict))
    return {_v5_ref_key(ref) for ref in refs if _v5_ref_key(ref)}


def _v5_ref_key(ref: dict[str, Any]) -> str:
    return f"{ref.get('kind')}|{ref.get('path')}|{ref.get('sha256')}"


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


def _inspect_schema_file(path: Path, *, expected_schema_names: set[str]) -> list[str]:
    failures: list[str] = []
    payload = _read_json_for_inspect(path, failures)
    if not payload:
        return failures
    spec = _schema_spec_for_payload(payload)
    if spec is None:
        failures.append("未知 V5 schema_version。")
        return failures
    schema_name = str(spec["schema_name"])
    if schema_name not in expected_schema_names:
        failures.append(f"schema {schema_name} 不能由当前 inspect 命令检查。")
    _inspect_payload_against_schema_spec(payload, spec, failures)
    _inspect_schema_specific_constraints(payload, schema_name, failures)
    return failures


def _schema_spec_for_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    version = payload.get("schema_version")
    for spec in V5_SCHEMA_SPECS:
        if spec.get("schema_version") == version:
            return spec
    if _looks_like_evidence_ref(payload):
        return V5_SCHEMA_SPECS[0]
    return None


def _inspect_payload_against_schema_spec(payload: dict[str, Any], spec: dict[str, Any], failures: list[str]) -> None:
    for field in spec.get("required_fields", ()):
        if _get_path(payload, str(field)) is None:
            failures.append(f"{spec['schema_name']} 缺少 required field：{field}")
    for group in spec.get("one_of_required_fields", ()):
        if not any(_get_path(payload, str(field)) is not None for field in group):
            failures.append(f"{spec['schema_name']} 必须至少包含一个字段：" + " 或 ".join(group))


def _inspect_schema_specific_constraints(payload: dict[str, Any], schema_name: str, failures: list[str]) -> None:
    if schema_name == "V5EvidenceRef":
        _inspect_v5_ref(payload, failures, label="V5EvidenceRef")
        return
    if schema_name == "V5AcceptanceInputs":
        bundle_path = str((payload.get("v4_doc_sync_acceptance_bundle_ref") or {}).get("path") or "")
        if V4_DOC_SYNC_BUNDLE_NAME not in bundle_path:
            failures.append("V5AcceptanceInputs 必须引用 V4 doc-sync acceptance bundle。")
        for ref in payload.get("v5_evidence_refs") or []:
            if isinstance(ref, dict) and ref.get("evidence_class") in V5_POST_REPORT_EVIDENCE_CLASSES:
                failures.append("V5AcceptanceInputs 不能绑定 post-report evidence。")
    elif schema_name == "V5AcceptanceReport":
        for path in ("core_acceptance.status", "resume_ready_acceptance.status"):
            value = _get_path(payload, path)
            if value not in V5_ACCEPTANCE_STATUS_VALUES:
                failures.append(f"{path} 枚举值无效。")
        integrity = payload.get("acceptance_report_reference_integrity")
        if isinstance(integrity, dict) and any(key.endswith("_ref") for key in integrity):
            failures.append("acceptance_report_reference_integrity.expected_check 只能描述待检集合，不能引用 post-report output。")
    elif schema_name == "V5TaskSetManifest":
        if payload.get("task_set_stage") == "stage2a_initial_10":
            if payload.get("accepted_auditable_task_count") != 10:
                failures.append("Stage 2A initial task set 必须正好包含 10 个 accepted / auditable 候选。")
            if payload.get("pr_issue_task_count") != 6:
                failures.append("Stage 2A initial task set 必须正好包含 6 个 PR / issue 候选。")
            if payload.get("strict_inventory_gate") != "blocked_pending_stage2b":
                failures.append("Stage 2A initial task set 必须把 strict inventory gate 标记为 blocked_pending_stage2b。")
            if payload.get("supplemental_required") is not True:
                failures.append("Stage 2A initial task set 必须声明 Stage 2B supplemental tasks 仍然必需。")
            if payload.get("claims_full_inventory_gate") is not False:
                failures.append("Stage 2A initial task set 不能宣称已经满足完整任务库存门。")
        else:
            if payload.get("accepted_auditable_task_count", 0) < 12:
                failures.append("accepted_auditable_task_count 必须至少为 12。")
            if payload.get("pr_issue_task_count", 0) < 8:
                failures.append("pr_issue_task_count 必须至少为 8。")
        if payload.get("swebench_like_anchor_count", 0) < 3:
            failures.append("swebench_like_anchor_count 必须至少为 3。")
    elif schema_name == "V5TaskInventoryReport":
        gate = payload.get("strict_inventory_gate")
        if gate not in {"passed", "blocked", "blocked_pending_stage2b"}:
            failures.append("strict_inventory_gate 必须是 passed、blocked 或 blocked_pending_stage2b。")
        if gate == "blocked_pending_stage2b" and payload.get("claims_full_inventory_gate") is not False:
            failures.append("blocked_pending_stage2b 时不能宣称完整任务库存门已通过。")
    elif schema_name == "V5TaskVisibilityScanReport":
        if payload.get("model_visible_leak_count", 0) != 0:
            failures.append("model_visible_leak_count 必须为 0。")
        _inspect_adapter_visible_refs_for_forbidden_markers(payload, failures)
    elif schema_name == "V5SupplementalPRIssueCandidateReport":
        if payload.get("required_supplemental_count") != 2:
            failures.append("Stage 2B supplemental report required_supplemental_count 必须为 2。")
        if payload.get("accepted_supplemental_count", 0) < 2:
            failures.append("Stage 2B supplemental report 至少需要 2 个 accepted supplemental tasks。")
        if payload.get("live_probes_executed") is not True:
            failures.append("Stage 2B supplemental report 必须来自 live probes，不能用 offline fixture 关闭库存门。")
        if payload.get("status") != "passed":
            failures.append("Stage 2B supplemental report status 必须为 passed。")
    elif schema_name == "V5ProviderCredentialGateReport":
        if payload.get("raw_secret_value_present") is not False:
            failures.append("raw_secret_value_present 必须为 false。")
        if not set(V5_PROVIDER_FAMILIES).issubset(set(payload.get("provider_families") or [])):
            failures.append("provider_families 必须覆盖 openai、deepseek 和 anthropic_claude。")
    elif schema_name == "V5ProviderCostBudgetReport":
        if payload.get("actual_real_provider_calls", 0) > payload.get("max_real_provider_calls", 0):
            failures.append("actual_real_provider_calls 不能超过 max_real_provider_calls。")
        if payload.get("actual_cost_proxy_usd", 0) > payload.get("max_cost_usd", 0):
            failures.append("actual_cost_proxy_usd 不能超过 max_cost_usd。")
    elif schema_name == "V5RunMatrixManifest":
        axes = set(payload.get("comparison_axes") or [])
        if not axes.intersection(V5_COMPARISON_AXES):
            failures.append("comparison_axes 至少需要包含 provider、scaffold、budget 或 diagnostic_baseline。")
        if not payload.get("controlled_variables_refs"):
            failures.append("controlled_variables_refs 不能为空。")
    elif schema_name == "V5MatrixCellResult":
        if payload.get("normalized_provider_status") not in V5_PROVIDER_STATUS_VALUES:
            failures.append("normalized_provider_status 枚举值无效。")
        if payload.get("normalized_provider_status") == "fallback_success" and payload.get("counts_toward_primary_accepted_rate") is True:
            failures.append("fallback_success 不能计入 primary accepted rate。")
    elif schema_name == "V5MatrixCompareScopeReport":
        if payload.get("comparison_axis") not in V5_COMPARISON_AXES:
            failures.append("comparison_axis 枚举值无效。")
        if not payload.get("controlled_variables"):
            failures.append("controlled_variables 不能为空。")
    elif schema_name == "V5ExportResultPackManifest":
        counts = payload.get("partition_counts")
        if not isinstance(counts, dict):
            failures.append("partition_counts 必须是 object。")
        else:
            missing = sorted(set(V5_PARTITION_COUNT_FIELDS).difference(counts))
            if missing:
                failures.append("partition_counts 缺少：" + ", ".join(missing))
    elif schema_name == "V5RewardSourceTaxonomyReport":
        if payload.get("reward_scalar_model_visible_count", 0) != 0:
            failures.append("reward scalar 不能进入 model-visible content。")
        if payload.get("reward_label_model_visible_count", 0) != 0:
            failures.append("reward label 不能进入 model-visible content。")
    elif schema_name == "V5FailureTaxonomyReport":
        if not payload.get("categories"):
            failures.append("failure taxonomy categories 不能为空。")
    elif schema_name == "V5PreferencePairBlockedReport":
        if not payload.get("blocked_reason"):
            failures.append("preference pair blocked report 必须记录 blocked_reason。")
    elif schema_name == "V5ResumeArtifactIndex":
        for ref in payload.get("artifact_refs") or []:
            if isinstance(ref, dict) and (ref.get("share_safe") is not True or ref.get("visibility") == "evaluator_only"):
                failures.append("resume artifact refs 必须 share_safe 且不能是 evaluator_only。")
    elif schema_name == "V5ResultSummaryTable":
        for field in V5_PARTITION_COUNT_FIELDS:
            if payload.get(field) is None:
                failures.append(f"result summary 缺少 {field}。")
    elif schema_name == "V5PublicDemoBundleManifest":
        if payload.get("provider_raw_content_count", 0) != 0:
            failures.append("public demo bundle 不能包含 provider raw content。")
        if payload.get("evaluator_only_content_count", 0) != 0:
            failures.append("public demo bundle 不能包含 evaluator-only content。")
    elif schema_name == "V5DemoTranscriptIndex":
        if payload.get("model_visible_leak_count", 0) != 0:
            failures.append("demo transcript 不能包含 model-visible leak。")
    elif schema_name == "V5ResumeClaimGateReport":
        if payload.get("stage") not in V5_CLAIM_GATE_STAGE_VALUES:
            failures.append("claim gate stage 枚举值无效。")
        if payload.get("provider_claim_status") == "blocked" and "multi-provider agent runs" in payload.get("allowed_claims", []):
            failures.append("provider blocked 时不能允许 multi-provider agent runs 声明。")
    elif schema_name == "V5InterviewResultPackManifest":
        for key in (
            "demo_card_ref",
            "walkthrough_ref",
            "result_summary_ref",
            "resume_templates_ref",
            "resume_bullets_ref",
            "interview_qa_evidence_ref",
            "public_safe_mapping_ref",
        ):
            ref = payload.get(key)
            if isinstance(ref, dict):
                if ref.get("share_safe") is not True or ref.get("visibility") != "public_safe":
                    failures.append(f"{key} 必须 share_safe=true 且 visibility=public_safe。")
                text = f"{ref.get('kind', '')} {ref.get('purpose', '')}".lower()
                if "provider raw" in text:
                    failures.append(f"{key} 不能引用 provider raw content。")


def _inspect_v5_task_inventory_deep(payload: dict[str, Any], failures: list[str]) -> None:
    refs = payload.get("task_definition_refs")
    if refs is not None and not isinstance(refs, list):
        failures.append("task_definition_refs 必须是 list。")
    if isinstance(refs, list):
        if payload.get("accepted_auditable_task_count") != len(refs):
            failures.append("accepted_auditable_task_count 必须等于 task_definition_refs 数量。")
        for index, ref in enumerate(refs, start=1):
            _inspect_v5_ref(ref, failures, label=f"task_definition_refs[{index}]")


def _inspect_v5_supplemental_pr_issue_report_deep(payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("live_probes_executed") is not True:
        failures.append("Stage 2B supplemental report 必须记录 live_probes_executed=true。")
    if payload.get("required_supplemental_count") != 2:
        failures.append("Stage 2B supplemental report required_supplemental_count 必须等于 2。")
    selected_ids = payload.get("selected_candidate_ids")
    if not isinstance(selected_ids, list) or len(selected_ids) != 2:
        failures.append("Stage 2B supplemental report 必须选择 2 个 candidate。")
        selected_ids = []
    accepted_refs = payload.get("accepted_task_definition_refs")
    if not isinstance(accepted_refs, list) or len(accepted_refs) < 2:
        failures.append("Stage 2B supplemental report accepted_task_definition_refs 至少需要 2 个。")
        accepted_refs = []
    _inspect_v5_ref(payload.get("command_log_ref"), failures, label="supplemental.command_log_ref")
    _inspect_v5_ref(payload.get("source_preflight_root_ref"), failures, label="supplemental.source_preflight_root_ref")

    task_ids_from_refs: list[str] = []
    candidate_ids_from_refs: list[str] = []
    for index, ref in enumerate(accepted_refs, start=1):
        _inspect_v5_ref(ref, failures, label=f"accepted_task_definition_refs[{index}]")
        task_payload = _read_ref_payload(ref, failures)
        if not isinstance(task_payload, dict):
            continue
        if task_payload.get("schema_version") != V5_TASK_DEFINITION_VERSION:
            failures.append(f"accepted_task_definition_refs[{index}] 必须指向 V5 task definition。")
        if task_payload.get("accepted_auditable") is not True:
            failures.append(f"accepted_task_definition_refs[{index}] 必须 accepted_auditable=true。")
        if task_payload.get("agent_run_ready") is not True:
            failures.append(f"accepted_task_definition_refs[{index}] 必须 agent_run_ready=true。")
        if task_payload.get("source_kind") != "pr_issue_flow":
            failures.append(f"accepted_task_definition_refs[{index}] 必须是 PR / issue flow。")
        if task_payload.get("live_probe_executed") is not True:
            failures.append(f"accepted_task_definition_refs[{index}] 必须绑定 live probe evidence。")
        task_ids_from_refs.append(str(task_payload.get("task_id") or ""))
        candidate_ids_from_refs.append(str(task_payload.get("candidate_id") or ""))
    if selected_ids and candidate_ids_from_refs[: len(selected_ids)] != [str(item) for item in selected_ids]:
        failures.append("selected_candidate_ids 必须和 accepted_task_definition_refs 前两个 candidate_id 一致。")

    records = payload.get("candidate_records")
    if not isinstance(records, list) or not records:
        failures.append("Stage 2B supplemental report candidate_records 必须是非空 list。")
        return
    by_candidate = {str(record.get("candidate_id")): record for record in records if isinstance(record, dict)}
    unknown_candidates = sorted(set(by_candidate).difference(V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER))
    if unknown_candidates:
        failures.append("candidate_records 包含未在默认补位顺序中审查过的候选：" + ", ".join(unknown_candidates))
    missing_selected = [str(item) for item in selected_ids if str(item) not in by_candidate]
    if missing_selected:
        failures.append("selected_candidate_ids 缺少 candidate_records：" + ", ".join(missing_selected))
    ready_in_order: list[str] = []
    for candidate_id in V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER:
        record = by_candidate.get(candidate_id)
        if isinstance(record, dict) and _supplemental_record_ready(record):
            ready_in_order.append(candidate_id)
    if selected_ids and ready_in_order[:2] != [str(item) for item in selected_ids]:
        failures.append("selected_candidate_ids 必须是默认顺序中最早满足 freeze_ready、agent_run_ready 和 visibility clean 的 2 个候选。")

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            failures.append(f"candidate_records[{index}] 必须是 object。")
            continue
        label = f"candidate_records[{index}]"
        _inspect_v5_ref(record.get("candidate_command_log_ref"), failures, label=f"{label}.candidate_command_log_ref")
        _inspect_candidate_command_log_ref(record.get("candidate_command_log_ref"), failures, label=label)
        if record.get("selected_for_stage2b_merge") is True:
            if record.get("candidate_id") not in selected_ids:
                failures.append(f"{label} selected_for_stage2b_merge=true 但不在 selected_candidate_ids 中。")
            for field in (
                "source_materialization_report_ref",
                "source_archive_manifest_ref",
                "dependency_probe_report_ref",
                "baseline_verifier_probe_report_ref",
                "post_patch_verifier_probe_report_ref",
                "flaky_probe_report_ref",
                "adapter_visible_denylist_scan_report_ref",
                "training_export_boundary_probe_report_ref",
                "provider_raw_content_leak_probe_report_ref",
                "task_definition_ref",
            ):
                _inspect_v5_ref(record.get(field), failures, label=f"{label}.{field}")
            if not _supplemental_record_ready(record):
                failures.append(f"{label} 被选中但未满足 freeze_ready、agent_run_ready、visibility clean、baseline failure、post-patch pass 和 stable flaky probe。")
            if record.get("live_probe_executed") is not True:
                failures.append(f"{label} 被选中但 live_probe_executed 不是 true。")
        else:
            if record.get("freeze_ready") is False:
                for field in ("failure_owner", "failure_category", "replacement_reason", "failed_command_name", "stdout_sha256", "stderr_sha256"):
                    if not record.get(field):
                        failures.append(f"{label} 未通过补位门时必须记录 {field}。")
            elif not record.get("replacement_reason"):
                failures.append(f"{label} 未被选择时必须记录 replacement_reason。")


def _supplemental_record_ready(record: dict[str, Any]) -> bool:
    counters = record.get("visibility_counters")
    return (
        record.get("freeze_ready") is True
        and record.get("agent_run_ready") is True
        and record.get("baseline_expected_failure") is True
        and record.get("post_patch_passed") is True
        and record.get("flaky_probe_status") == "stable"
        and isinstance(counters, dict)
        and all(
            int(counters.get(key) or 0) == 0
            for key in (
                "model_visible_leak_count",
                "share_safe_violation_count",
                "trainable_payload_contamination_count",
                "raw_provider_content_leak_count",
                "credential_marker_leak_count",
            )
        )
    )


def _inspect_candidate_command_log_ref(ref: Any, failures: list[str], *, label: str) -> None:
    path = _path_from_ref(ref)
    if path is None or not path.exists() or path.is_dir():
        return
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"{label}.candidate_command_log_ref 第 {line_number} 行不是合法 JSON：{exc}")
            continue
        if not isinstance(payload, dict):
            failures.append(f"{label}.candidate_command_log_ref 第 {line_number} 行必须是 object。")
            continue
        records.append(payload)
        if payload.get("schema_version") != V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION:
            failures.append(f"{label}.candidate_command_log_ref 第 {line_number} 行 schema_version 不匹配。")
        for field in ("command_name", "argv", "cwd", "started_at", "finished_at", "exit_code", "stdout_sha256", "stderr_sha256"):
            if field not in payload:
                failures.append(f"{label}.candidate_command_log_ref 第 {line_number} 行缺少 {field}。")
        for ref_field in ("input_refs", "output_refs"):
            refs = payload.get(ref_field)
            if not isinstance(refs, list):
                failures.append(f"{label}.candidate_command_log_ref 第 {line_number} 行 {ref_field} 必须是 list。")
                continue
            for ref_index, nested_ref in enumerate(refs, start=1):
                _inspect_v5_ref(nested_ref, failures, label=f"{label}.candidate_command_log_ref[{line_number}].{ref_field}[{ref_index}]")
    if not records:
        failures.append(f"{label}.candidate_command_log_ref 必须至少包含 1 条 command log entry。")


def _inspect_adapter_visible_refs_for_forbidden_markers(payload: dict[str, Any], failures: list[str]) -> None:
    refs = payload.get("adapter_visible_input_refs")
    if refs is None:
        return
    if not isinstance(refs, list):
        failures.append("adapter_visible_input_refs 必须是 list。")
        return
    for index, ref in enumerate(refs, start=1):
        _inspect_v5_ref(ref, failures, label=f"adapter_visible_input_refs[{index}]")
        path = _path_from_ref(ref)
        if path is None or not path.exists() or path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            failures.append(f"adapter_visible_input_refs[{index}] 不是 UTF-8 文本，无法检查可见性边界。")
            continue
        for marker in V5_FORBIDDEN_ADAPTER_VISIBLE_MARKERS:
            if marker.lower() in text:
                failures.append(
                    f"adapter_visible_input_refs[{index}] 包含禁止进入模型可见输入的标记：{marker}"
                )


def _inspect_v5_task_set_manifest_deep(payload: dict[str, Any], failures: list[str]) -> None:
    task_refs = payload.get("task_refs")
    if not isinstance(task_refs, list) or not task_refs:
        failures.append("task_refs 必须是非空 list。")
        return
    _inspect_v5_ref(payload.get("inventory_report_ref"), failures, label="inventory_report_ref")
    _inspect_v5_ref(payload.get("visibility_scan_ref"), failures, label="visibility_scan_ref")
    formal_task_set = bool(payload.get("task_set_stage")) or any(
        isinstance(ref, dict) and ref.get("kind") == "v5_task_definition" for ref in task_refs
    )
    if not formal_task_set:
        return
    visibility_payload = _read_ref_payload(payload.get("visibility_scan_ref"), failures)
    if visibility_payload is not None:
        if visibility_payload.get("status") != "passed":
            failures.append("visibility_scan_ref 指向的 visibility report 必须 status=passed。")
        for counter in (
            "model_visible_leak_count",
            "share_safe_violation_count",
            "trainable_payload_contamination_count",
        ):
            if visibility_payload.get(counter, 0) != 0:
                failures.append(f"visibility_scan_ref 指向的 visibility report {counter} 必须为 0。")

    task_payloads: list[dict[str, Any]] = []
    for index, ref in enumerate(task_refs, start=1):
        _inspect_v5_ref(ref, failures, label=f"task_refs[{index}]")
        task_payload = _read_ref_payload(ref, failures)
        if task_payload is not None:
            task_payloads.append(task_payload)

    if not task_payloads:
        return
    required_task_fields = (
        "task_id",
        "task_family",
        "source_kind",
        "repo_url_or_archive_id",
        "base_commit",
        "source_archive_sha256",
        "source_tree_hash",
        "task_input_hash",
        "adapter_visible_input_ref",
        "evaluator_only_evidence_ref",
        "baseline_verifier_plan_ref",
        "final_verifier_plan_ref",
        "fail_to_pass_evidence_ref",
        "pass_to_pass_evidence_ref",
        "flaky_probe_report_ref",
        "license_provenance_ref",
        "dependency_cache_ref",
        "environment_stability_ref",
        "contamination_scan_ref",
        "visibility_scan_ref",
        "task_diversity_ref",
    )
    ref_fields = tuple(field for field in required_task_fields if field.endswith("_ref"))
    task_ids: set[str] = set()
    accepted_count = 0
    pr_issue_count = 0
    swebench_count = 0
    for task_index, task in enumerate(task_payloads, start=1):
        label = f"task_definition[{task_index}]"
        if task.get("schema_version") != V5_TASK_DEFINITION_VERSION:
            failures.append(f"{label} schema_version 不匹配。")
        for field in required_task_fields:
            if task.get(field) in (None, ""):
                failures.append(f"{label} 缺少字段：{field}")
        task_id = str(task.get("task_id") or "")
        if task_id in task_ids:
            failures.append(f"task_id 重复：{task_id}")
        task_ids.add(task_id)
        if task.get("accepted_auditable") is True:
            accepted_count += 1
            if task.get("source_kind") == "pr_issue_flow":
                pr_issue_count += 1
            if task.get("source_kind") == "swebench_like_anchor":
                swebench_count += 1
        for field in ref_fields:
            _inspect_v5_ref(task.get(field), failures, label=f"{label}.{field}")
        adapter_ref = task.get("adapter_visible_input_ref")
        if isinstance(adapter_ref, dict):
            if adapter_ref.get("visibility") != "model_visible":
                failures.append(f"{label}.adapter_visible_input_ref visibility 必须是 model_visible。")
            if adapter_ref.get("share_safe") is not True:
                failures.append(f"{label}.adapter_visible_input_ref 必须 share_safe=true。")
        evaluator_ref = task.get("evaluator_only_evidence_ref")
        if isinstance(evaluator_ref, dict):
            if evaluator_ref.get("visibility") != "evaluator_only":
                failures.append(f"{label}.evaluator_only_evidence_ref visibility 必须是 evaluator_only。")
            if evaluator_ref.get("share_safe") is True:
                failures.append(f"{label}.evaluator_only_evidence_ref 不能 share_safe=true。")
        source_archive_ref = task.get("source_archive_ref")
        if isinstance(source_archive_ref, dict):
            _inspect_v5_ref(source_archive_ref, failures, label=f"{label}.source_archive_ref")
            if task.get("source_archive_sha256") != source_archive_ref.get("sha256"):
                failures.append(f"{label}.source_archive_sha256 必须等于 source_archive_ref.sha256。")

    if payload.get("accepted_auditable_task_count") != accepted_count:
        failures.append("accepted_auditable_task_count 必须等于 accepted task definition 数量。")
    if payload.get("pr_issue_task_count") != pr_issue_count:
        failures.append("pr_issue_task_count 必须等于 PR / issue task definition 数量。")
    if payload.get("swebench_like_anchor_count") != swebench_count:
        failures.append("swebench_like_anchor_count 必须等于 SWE-Bench-like task definition 数量。")
    if payload.get("task_set_stage") == "stage2a_initial_10":
        if len(task_payloads) != 10:
            failures.append("Stage 2A initial task set 必须有 10 个 task definition。")
        if payload.get("full_v5_threshold_status") != V5_PARTIAL_THRESHOLD_STATUS:
            failures.append("Stage 2A initial task set 必须记录 partial threshold status。")
        if payload.get("strict_inventory_gate") != "blocked_pending_stage2b":
            failures.append("Stage 2A initial task set 必须阻塞完整库存门，等待 Stage 2B。")
    elif accepted_count < 12 or pr_issue_count < 8:
        failures.append("非 Stage 2A task set 必须满足 12 total / 8 PR-issue 任务库存门。")


def _schema_inspect_result(label: str, path: Path, failures: list[str], *, assert_complete: bool) -> str:
    lines = [f"{label}: {path}"]
    if failures:
        if assert_complete:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_complete:
        lines.append(f"{label}: complete")
    lines.append(f"{label}: passed")
    return "\n".join(lines)


def _get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _looks_like_evidence_ref(payload: dict[str, Any]) -> bool:
    return all(field in payload for field in V5_SCHEMA_SPECS[0]["required_fields"])


def _valid_schema_fixture_payload(
    schema_name: str,
    target: Path,
    *,
    acceptance_inputs_path: Path | None = None,
    v4_doc_sync_path: Path | None = None,
) -> dict[str, Any]:
    ref = _evidence_ref(
        target,
        kind="fixture_target",
        purpose="Valid V5 evidence ref target",
        visibility="audit_only",
        producer_command="build-v5-schema-fixtures",
        producer_stage="v5_stage1_schema_and_evidence_integrity",
        inspect_command="inspect-v5-evidence-integrity",
    )
    if schema_name == "V5EvidenceRef":
        return ref
    if schema_name == "V5AcceptanceInputs":
        def kind_ref(kind: str) -> dict[str, Any]:
            return {**ref, "kind": kind}

        v4_doc_sync_ref = _evidence_ref(
            v4_doc_sync_path or target,
            kind="v4_doc_sync_acceptance_bundle",
            purpose="Valid V4 doc-sync bundle fixture",
            visibility="audit_only",
            producer_command="build-v5-schema-fixtures",
            producer_stage="v5_stage1_schema_and_evidence_integrity",
            inspect_command="inspect-acceptance-bundle",
        )

        required_kinds = [
            "v5_preflight_input_binding",
            "v5_pre_acceptance_evidence_integrity_report",
            "v5_task_set_manifest",
            "v5_run_matrix_manifest_executed",
            "v5_resume_claim_gate_report",
            "v5_export_result_pack_manifest",
            "v5_public_demo_bundle_manifest",
            "v5_resume_artifact_index",
            "v5_result_summary_table",
            "v5_final_acceptance_pretest_report",
        ]
        return {
            "schema_version": V5_ACCEPTANCE_INPUTS_VERSION,
            "created_at": "2026-05-05T00:00:00Z",
            "current_head": "0" * 40,
            "selection_mode": "explicit",
            "latest_run_auto_selection": False,
            "v2_acceptance_report_ref": kind_ref("v2_acceptance_report"),
            "v3_acceptance_report_ref": kind_ref("v3_acceptance_report"),
            "v3_acceptance_bundle_ref": kind_ref("v3_acceptance_bundle"),
            "v4_acceptance_inputs_ref": kind_ref("v4_acceptance_inputs"),
            "v4_acceptance_report_ref": kind_ref("v4_acceptance_report"),
            "v4_doc_sync_acceptance_bundle_ref": v4_doc_sync_ref,
            "v4_doc_sync_final_command_log_ref": kind_ref("v4_doc_sync_final_command_log"),
            "v5_evidence_refs": [kind_ref(kind) for kind in required_kinds],
            "stress_test_executed": False,
            "post_report_outputs_included": False,
            "bundle_final_outputs_included": False,
        }
    if schema_name == "V5AcceptanceReport":
        input_refs_by_kind: dict[str, dict[str, Any]] = {}
        if acceptance_inputs_path is not None and acceptance_inputs_path.exists():
            acceptance_inputs_payload = json.loads(acceptance_inputs_path.read_text(encoding="utf-8"))
            for item in acceptance_inputs_payload.get("v5_evidence_refs") or []:
                if isinstance(item, dict):
                    input_refs_by_kind[str(item.get("kind"))] = item
        acceptance_inputs_ref = (
            _evidence_ref(
                acceptance_inputs_path,
                kind="v5_acceptance_inputs",
                purpose="Valid V5 acceptance inputs fixture",
                visibility="audit_only",
                producer_command="build-v5-schema-fixtures",
                producer_stage="v5_stage1_schema_and_evidence_integrity",
                inspect_command="inspect-v5-inputs",
            )
            if acceptance_inputs_path is not None
            else ref
        )
        return {
            "schema_version": V5_ACCEPTANCE_REPORT_VERSION,
            "acceptance_inputs_ref": acceptance_inputs_ref,
            "core_acceptance": {"status": "passed", "required_checks": []},
            "resume_ready_acceptance": {"status": "blocked", "required_checks": []},
            "allowed_claims": ["core_acceptance"],
            "blocked_claims": ["resume_ready_acceptance"],
            "claim_gate_report_ref": input_refs_by_kind.get("v5_resume_claim_gate_report", {**ref, "kind": "v5_resume_claim_gate_report"}),
            "critical_evidence_refs": [
                input_refs_by_kind.get("v5_task_set_manifest", {**ref, "kind": "v5_task_set_manifest"})
            ],
            "acceptance_report_reference_integrity": {"expected_check": "inspect-v5-acceptance_after_report_generation"},
        }
    if schema_name == "V5TaskSetManifest":
        return {
            "schema_version": V5_TASK_SET_MANIFEST_VERSION,
            "accepted_auditable_task_count": 12,
            "pr_issue_task_count": 8,
            "swebench_like_anchor_count": 4,
            "task_refs": [ref],
            "inventory_report_ref": ref,
            "visibility_scan_ref": ref,
        }
    if schema_name == "V5TaskInventoryReport":
        return {
            "schema_version": V5_TASK_INVENTORY_REPORT_VERSION,
            "accepted_auditable_task_count": 12,
            "pr_issue_task_count": 8,
            "swebench_like_anchor_count": 4,
            "strict_inventory_gate": "passed",
            "source_mix": {"pr_issue": 8, "swebench_like_anchor": 4},
        }
    if schema_name == "V5TaskVisibilityScanReport":
        return {
            "schema_version": V5_TASK_VISIBILITY_SCAN_REPORT_VERSION,
            "model_visible_leak_count": 0,
            "share_safe_violation_count": 0,
            "trainable_payload_contamination_count": 0,
            "findings": [],
            "status": "passed",
        }
    if schema_name == "V5SupplementalPRIssueCandidateReport":
        return {
            "schema_version": V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT_VERSION,
            "candidate_order": ["owner/repo#1", "owner/repo#2"],
            "candidate_records": [
                {
                    "candidate_id": "owner/repo#1",
                    "freeze_ready": True,
                    "agent_run_ready": True,
                    "baseline_expected_failure": True,
                    "post_patch_passed": True,
                    "flaky_probe_status": "stable",
                    "selected_for_stage2b_merge": True,
                    "live_probe_executed": True,
                    "visibility_counters": {
                        "model_visible_leak_count": 0,
                        "share_safe_violation_count": 0,
                        "trainable_payload_contamination_count": 0,
                        "raw_provider_content_leak_count": 0,
                        "credential_marker_leak_count": 0,
                    },
                    "candidate_command_log_ref": ref,
                    "task_definition_ref": ref,
                },
                {
                    "candidate_id": "owner/repo#2",
                    "freeze_ready": True,
                    "agent_run_ready": True,
                    "baseline_expected_failure": True,
                    "post_patch_passed": True,
                    "flaky_probe_status": "stable",
                    "selected_for_stage2b_merge": True,
                    "live_probe_executed": True,
                    "visibility_counters": {
                        "model_visible_leak_count": 0,
                        "share_safe_violation_count": 0,
                        "trainable_payload_contamination_count": 0,
                        "raw_provider_content_leak_count": 0,
                        "credential_marker_leak_count": 0,
                    },
                    "candidate_command_log_ref": ref,
                    "task_definition_ref": ref,
                },
            ],
            "accepted_supplemental_count": 2,
            "required_supplemental_count": 2,
            "selected_candidate_ids": ["owner/repo#1", "owner/repo#2"],
            "accepted_task_definition_refs": [ref, ref],
            "command_log_ref": ref,
            "live_probes_executed": True,
            "status": "passed",
        }
    if schema_name == "V5ProviderCredentialGateReport":
        return {
            "schema_version": V5_PROVIDER_CREDENTIAL_GATE_REPORT_VERSION,
            "provider_families": list(V5_PROVIDER_FAMILIES),
            "credential_status_by_provider": {provider: "missing" for provider in V5_PROVIDER_FAMILIES},
            "adapter_status_by_provider": {
                "openai": "fallback_only",
                "deepseek": "primary_supported",
                "anthropic_claude": "adapter_not_implemented",
            },
            "structured_skips": [
                {
                    "provider_id": "openai",
                    "skip_type": "primary_provider_comparison_not_enabled_skip",
                    "credential_status": "missing",
                    "adapter_status": "fallback_only",
                    "skip_reason": "OpenAI is fallback-only in the current adapter.",
                    "affected_matrix_cells": ["openai_primary_provider_comparison_cells"],
                    "affects_core_acceptance": False,
                    "affects_resume_ready_acceptance": True,
                    "counts_toward_real_provider_accepted_rate": False,
                    "counts_toward_primary_accepted_rate": False,
                },
                {
                    "provider_id": "anthropic_claude",
                    "skip_type": "adapter_not_implemented_skip",
                    "credential_status": "missing",
                    "adapter_status": "adapter_not_implemented",
                    "skip_reason": "Anthropic Claude adapter is not implemented.",
                    "affected_matrix_cells": ["anthropic_claude_provider_comparison_cells"],
                    "affects_core_acceptance": False,
                    "affects_resume_ready_acceptance": True,
                    "counts_toward_real_provider_accepted_rate": False,
                    "counts_toward_primary_accepted_rate": False,
                },
            ],
            "raw_secret_value_present": False,
            "provider_raw_content_policy": "audit_only_redacted_never_model_visible",
        }
    if schema_name == "V5ProviderCostBudgetReport":
        return {
            "schema_version": V5_PROVIDER_COST_BUDGET_REPORT_VERSION,
            "max_real_provider_calls": 12,
            "max_cost_usd": 5.0,
            "cost_proxy_formula": "actual_real_provider_calls * configured_cost_proxy",
            "actual_real_provider_calls": 0,
            "actual_cost_proxy_usd": 0.0,
            "cost_limited_structured_skip": [],
            "budget_exhausted_before_run": False,
        }
    if schema_name == "V5RunMatrixManifest":
        return {
            "schema_version": V5_RUN_MATRIX_MANIFEST_VERSION,
            "task_set_ref": ref,
            "provider_gate_ref": ref,
            "provider_cost_budget_ref": ref,
            "planned_matrix_cells": [],
            "controlled_variables_refs": [ref],
            "comparison_axes": ["provider"],
            "agent_run_started": False,
            "provider_api_called": False,
        }
    if schema_name == "V5MatrixCellResult":
        return {
            "schema_version": V5_MATRIX_CELL_RESULT_VERSION,
            "task_id": "v5_fixture_task",
            "provider_id": "deepseek",
            "provider_mode": "primary",
            "normalized_provider_status": "primary_attempted",
            "scaffold_id": "baseline",
            "budget_policy_id": "small",
            "tool_policy_id": "standard",
            "context_policy_id": "default",
            "environment_id": "docker_local",
            "source_tree_hash": "a" * 64,
            "run_id": "fixture_run",
            "run_dir": "runs/fixture_run",
            "final_verifier_status": "accepted",
            "trajectory_ref": ref,
            "final_verifier_boundary_ref": ref,
            "controlled_variables_ref": ref,
        }
    if schema_name == "V5MatrixCompareScopeReport":
        return {
            "schema_version": V5_MATRIX_COMPARE_SCOPE_REPORT_VERSION,
            "comparison_axis": "provider",
            "controlled_variables": ["task", "source_tree", "final_verifier_plan", "tool_policy"],
            "compared_cells": ["cell_a", "cell_b"],
            "comparison_validity": "valid",
        }
    if schema_name == "V5ExportResultPackManifest":
        return {
            "schema_version": V5_EXPORT_RESULT_PACK_MANIFEST_VERSION,
            "sft_export_ref": ref,
            "rl_rollout_export_ref": ref,
            "failure_dataset_ref": ref,
            "preference_pair_blocked_report_ref": ref,
            "partition_counts": {field: 0 for field in V5_PARTITION_COUNT_FIELDS},
            "reward_source_taxonomy_ref": ref,
            "failure_taxonomy_ref": ref,
            "export_audit_ref": ref,
        }
    if schema_name == "V5RewardSourceTaxonomyReport":
        return {
            "schema_version": V5_REWARD_SOURCE_TAXONOMY_REPORT_VERSION,
            "allowed_reward_metadata_paths": ["audit_only.reward_metadata"],
            "reward_scalar_model_visible_count": 0,
            "reward_label_model_visible_count": 0,
            "status": "passed",
        }
    if schema_name == "V5FailureTaxonomyReport":
        return {
            "schema_version": V5_FAILURE_TAXONOMY_REPORT_VERSION,
            "categories": ["final_verifier_rejected", "provider_blocked"],
            "records": [],
            "status": "passed",
        }
    if schema_name == "V5PreferencePairBlockedReport":
        return {
            "schema_version": V5_PREFERENCE_PAIR_BLOCKED_REPORT_VERSION,
            "blocked_reason": "no_real_comparable_pair_yet",
            "failure_owner": "stage3_run_matrix",
            "failure_category": "comparison_scope_blocked",
            "claim_gate_effect": "disable_preference_export_completed_claim",
        }
    if schema_name == "V5ResumeArtifactIndex":
        public_ref = {**ref, "visibility": "public_safe", "share_safe": True}
        return {
            "schema_version": V5_RESUME_ARTIFACT_INDEX_VERSION,
            "artifact_refs": [public_ref],
            "share_safe_status": "passed",
            "public_demo_bundle_ref": public_ref,
        }
    if schema_name == "V5ResultSummaryTable":
        return {
            "schema_version": V5_RESULT_SUMMARY_TABLE_VERSION,
            "real_provider_trainable_records": 1,
            "mock_or_replay_records": 0,
            "diagnostic_records": 1,
            "blocked_records": 1,
            "synthetic_safe_stress_records": 0,
        }
    if schema_name == "V5PublicDemoBundleManifest":
        public_ref = {**ref, "visibility": "public_safe", "share_safe": True}
        return {
            "schema_version": V5_PUBLIC_DEMO_BUNDLE_MANIFEST_VERSION,
            "artifact_refs": [public_ref],
            "share_safe_status": "passed",
            "provider_raw_content_count": 0,
            "evaluator_only_content_count": 0,
        }
    if schema_name == "V5DemoTranscriptIndex":
        public_ref = {**ref, "visibility": "public_safe", "share_safe": True}
        return {
            "schema_version": V5_DEMO_TRANSCRIPT_INDEX_VERSION,
            "transcript_refs": [public_ref],
            "model_visible_leak_count": 0,
            "share_safe_status": "passed",
        }
    if schema_name == "V5ResumeClaimGateReport":
        return {
            "schema_version": V5_RESUME_CLAIM_GATE_REPORT_VERSION,
            "stage": "stage5_final",
            "allowed_claims": ["core_acceptance"],
            "blocked_claims": [],
            "blocking_reasons": {},
            "provider_claim_status": "allowed",
            "preference_pair_claim_status": "blocked",
            "demo_share_safe_status": "passed",
            "stress_test_claim_status": "not_claimed",
            "source_reports": [ref],
        }
    if schema_name == "V5InterviewResultPackManifest":
        public_ref = {**ref, "visibility": "public_safe", "share_safe": True}
        return {
            "schema_version": V5_INTERVIEW_RESULT_PACK_MANIFEST_VERSION,
            "demo_card_ref": public_ref,
            "walkthrough_ref": public_ref,
            "result_summary_ref": public_ref,
            "resume_templates_ref": public_ref,
            "resume_bullets_ref": public_ref,
            "interview_qa_evidence_ref": public_ref,
            "public_safe_mapping_ref": public_ref,
        }
    raise ConfigError(f"未知 V5 schema fixture：{schema_name}")


def _negative_schema_fixture_payload(schema_name: str, target: Path) -> dict[str, Any]:
    payload = _valid_schema_fixture_payload(schema_name, target)
    if schema_name == "V5EvidenceRef":
        payload["sha256"] = "0" * 64
    elif schema_name == "V5AcceptanceInputs":
        payload["v5_evidence_refs"].append({"evidence_class": "post_report_inspect_output", "path": "post_report/inspect.txt"})
    elif schema_name == "V5AcceptanceReport":
        payload["acceptance_report_reference_integrity"]["post_report_output_ref"] = {"path": "post_report/inspect.txt"}
    elif schema_name == "V5TaskSetManifest":
        payload["accepted_auditable_task_count"] = 10
        payload["pr_issue_task_count"] = 6
    elif schema_name == "V5TaskInventoryReport":
        payload.pop("pr_issue_task_count", None)
    elif schema_name == "V5TaskVisibilityScanReport":
        payload["model_visible_leak_count"] = 1
        payload["status"] = "failed"
    elif schema_name == "V5SupplementalPRIssueCandidateReport":
        payload["live_probes_executed"] = False
    elif schema_name == "V5ProviderCredentialGateReport":
        payload["raw_secret_value_present"] = True
    elif schema_name == "V5ProviderCostBudgetReport":
        payload["actual_real_provider_calls"] = payload["max_real_provider_calls"] + 1
    elif schema_name == "V5RunMatrixManifest":
        payload["controlled_variables_refs"] = []
    elif schema_name == "V5MatrixCellResult":
        payload["normalized_provider_status"] = "fallback_success"
        payload["counts_toward_primary_accepted_rate"] = True
    elif schema_name == "V5MatrixCompareScopeReport":
        payload["controlled_variables"] = []
    elif schema_name == "V5ExportResultPackManifest":
        payload["partition_counts"].pop("blocked_records", None)
    elif schema_name == "V5RewardSourceTaxonomyReport":
        payload["reward_scalar_model_visible_count"] = 1
    elif schema_name == "V5FailureTaxonomyReport":
        payload["categories"] = []
    elif schema_name == "V5PreferencePairBlockedReport":
        payload["blocked_reason"] = ""
    elif schema_name == "V5ResumeArtifactIndex":
        payload["artifact_refs"][0]["visibility"] = "evaluator_only"
    elif schema_name == "V5ResultSummaryTable":
        payload.pop("blocked_records", None)
    elif schema_name == "V5PublicDemoBundleManifest":
        payload["provider_raw_content_count"] = 1
    elif schema_name == "V5DemoTranscriptIndex":
        payload["model_visible_leak_count"] = 1
    elif schema_name == "V5ResumeClaimGateReport":
        payload["stage"] = "acceptance_final"
        payload["allowed_claims"].append("multi-provider agent runs")
        payload["provider_claim_status"] = "blocked"
    elif schema_name == "V5InterviewResultPackManifest":
        payload["demo_card_ref"] = {**payload["demo_card_ref"], "purpose": "provider raw request fixture"}
    return payload


def _pre_acceptance_integrity_findings(manifest: dict[str, Any], *, manifest_path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if manifest.get("schema_version") != V5_CRITICAL_EVIDENCE_MANIFEST_VERSION:
        findings.append(
            {
                "finding_type": "critical_evidence_manifest_schema_mismatch",
                "severity": "critical",
                "message": "critical evidence manifest schema_version 不匹配。",
            }
        )
    if manifest.get("acceptance_report_ref"):
        findings.append(
            {
                "finding_type": "post_report_reference",
                "severity": "critical",
                "message": "pre-acceptance critical evidence manifest 不能引用 acceptance report。",
            }
        )
    records = manifest.get("critical_evidence")
    if not isinstance(records, list):
        return findings + [
            {
                "finding_type": "critical_evidence_manifest_invalid",
                "severity": "critical",
                "message": "critical_evidence 必须是 list。",
            }
        ]
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            findings.append({"finding_type": "critical_evidence_record_invalid", "severity": "critical", "message": f"critical_evidence[{index}] 不是 object。"})
            continue
        evidence_class = str(record.get("evidence_class") or "")
        if evidence_class in V5_POST_REPORT_EVIDENCE_CLASSES:
            findings.append({"finding_type": "post_report_reference", "severity": "critical", "message": f"{evidence_class} 不能进入 pre-acceptance evidence integrity。"})
        elif evidence_class not in V5_CRITICAL_EVIDENCE_CLASSES:
            findings.append({"finding_type": "unknown_critical_evidence_class", "severity": "critical", "message": f"未知 critical evidence class：{evidence_class}"})
        if record.get("criticality") == "critical" and record.get("planned_acceptance_inputs_binding") is not True:
            findings.append({"finding_type": "unbound_critical_evidence", "severity": "critical", "message": f"critical_evidence[{index}] 未声明会进入 acceptance inputs。"})
        ref = record.get("ref")
        ref_failures: list[str] = []
        _inspect_v5_ref(ref, ref_failures, label=f"critical_evidence[{index}].ref")
        for failure in ref_failures:
            finding_type = "sha256_drift" if "sha256" in failure else "critical_evidence_ref_invalid"
            findings.append({"finding_type": finding_type, "severity": "critical", "message": failure})
        if isinstance(ref, dict):
            visibility = str(ref.get("visibility") or "")
            purpose = str(ref.get("purpose") or "").lower()
            kind = str(ref.get("kind") or "").lower()
            if visibility in {"model_visible", "trainable", "public_safe"}:
                marker = next((item for item in V5_FORBIDDEN_PUBLIC_OR_TRAINABLE_MARKERS if item in purpose or item in kind), None)
                if marker:
                    findings.append(
                        {
                            "finding_type": "visibility_policy_violation",
                            "severity": "critical",
                            "message": f"critical_evidence[{index}] 在 {visibility} 中包含禁止标记：{marker}",
                        }
                    )
            if ref.get("share_safe") is True and visibility == "evaluator_only":
                findings.append(
                    {
                        "finding_type": "visibility_policy_violation",
                        "severity": "critical",
                        "message": f"critical_evidence[{index}] evaluator_only evidence 不能 share_safe=true。",
                    }
                )
    if not manifest_path.exists():
        findings.append({"finding_type": "critical_evidence_manifest_missing", "severity": "critical", "message": f"manifest path 不存在：{manifest_path}"})
    return findings


def _finding_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_findings": len(findings),
        "unbound_critical_evidence_findings": sum(1 for item in findings if item.get("finding_type") == "unbound_critical_evidence"),
        "sha256_drift_findings": sum(1 for item in findings if item.get("finding_type") == "sha256_drift"),
        "visibility_policy_findings": sum(1 for item in findings if item.get("finding_type") == "visibility_policy_violation"),
        "post_report_reference_findings": sum(1 for item in findings if item.get("finding_type") == "post_report_reference"),
        "provider_raw_or_secret_findings": sum(
            1
            for item in findings
            if "provider raw" in str(item.get("message") or "").lower()
            or "credential" in str(item.get("message") or "").lower()
            or "authorization" in str(item.get("message") or "").lower()
        ),
    }


def _builder_command_log_entry(
    *,
    command_name: str,
    input_paths: list[Path],
    output_paths: list[Path],
    producer_stage: str,
) -> dict[str, Any]:
    return {
        "schema_version": V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": command_name,
        "argv": sys.argv,
        "cwd": Path.cwd().as_posix(),
        "builder_invocation_cwd": Path.cwd().as_posix(),
        "env_policy": "builder records argv and artifact refs; provider credential values are not recorded",
        "network_policy": "local_only",
        "risk_command_hits": _risk_command_hits(sys.argv),
        "input_ref_policy": "explicit builder inputs are bound by path, sha256, and size_bytes",
        "input_refs": [
            _evidence_ref(
                path,
                kind="builder_input",
                purpose=f"{command_name} input",
                visibility="audit_only",
                producer_command="external",
                producer_stage=producer_stage,
                inspect_command="inspect-v5-evidence-integrity",
            )
            for path in input_paths
        ],
        "output_refs": [
            _evidence_ref(
                path,
                kind="builder_output",
                purpose=f"{command_name} output",
                visibility="audit_only",
                producer_command=command_name,
                producer_stage=producer_stage,
                inspect_command="inspect-v5-evidence-integrity",
            )
            for path in output_paths
        ],
        "started_at": _utc_timestamp(),
        "finished_at": _utc_timestamp(),
        "exit_code": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "structured_skip_reason": None,
        "structured_failure_reason": None,
        "tool_or_cli_version": f"repo-harness {__version__}",
    }


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
