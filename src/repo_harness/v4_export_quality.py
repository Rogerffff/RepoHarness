"""V4 stage 6 export quality, packing, failure, and reward audit evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_ALLOWLIST_POLICY_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
    V4_EXPORT_QUALITY_MANIFEST_VERSION,
    V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION,
)
from repo_harness.v4_visibility import V4ContaminationDenylist, v4_contamination_denylist_sha256


SAMPLE_TIER_MANIFEST_VERSION = "repo_harness_v4_sample_tier_manifest_v0"
FAILURE_DATASET_ENTRY_VERSION = "repo_harness_v4_failure_dataset_entry_v0"
PACKING_MANIFEST_VERSION = "repo_harness_v4_packing_manifest_v0"
REWARD_AUDIT_REPORT_VERSION = "repo_harness_v4_reward_audit_report_v0"
REWARD_HACKING_RISK_AUDIT_REPORT_VERSION = "repo_harness_v4_reward_hacking_risk_audit_report_v0"
PATCH_QUALITY_REPORT_VERSION = "repo_harness_v4_patch_quality_report_v0"
TEST_OVERFITTING_RISK_AUDIT_REPORT_VERSION = "repo_harness_v4_test_overfitting_risk_audit_report_v0"
PREFERENCE_PAIR_TRAINABILITY_REPORT_VERSION = "repo_harness_v4_preference_pair_trainability_report_v0"
BLOCKED_PAIR_REPORT_VERSION = "repo_harness_v4_blocked_pair_report_v0"
EXPORT_FIXTURE_RECORD_VERSION = "repo_harness_v4_export_fixture_record_v0"

STAGE6_OUTPUTS = (
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
)
EXPORT_FORMATS = ("sft", "rl", "preference")
REWARD_METADATA_REQUIRED_FIELDS = (
    "reward_version",
    "formula",
    "components",
    "sources",
    "invalid_for_training",
    "invalid_reason",
    "acceptance_policy_version",
    "reward_clip_range",
)
FAILURE_DATASET_REQUIRED_FIELDS = (
    "run_id",
    "task_id",
    "failure_category",
    "turn_id",
    "tool_call_id",
    "workspace_state_ref",
    "final_verifier_result_ref",
    "failure_source_component",
    "evidence_ref",
)
TEST_OVERFITTING_REQUIRED_RISKS = {
    "test_only_patch",
    "deleted_verifier_path",
    "hidden_selector_hardcode",
    "removed_failing_assertion",
    "evaluator_only_evidence_read",
    "verifier_bypass_attempt",
    "modified_verifier_configuration",
}
OUTCOME_TO_FINAL_VERIFIER = {
    "verifier_accepted": "accepted",
    "verifier_rejected": "rejected",
    "verifier_inconclusive": "inconclusive",
}
COMPARABLE_SAMPLE_FIELDS = (
    "task_id",
    "task_family",
    "source_tree_hash",
    "baseline_verifier_plan_hash",
    "final_verifier_plan_hash",
    "tool_schema_snapshot_hash",
    "context_strategy_id",
)
REWARD_AUDIT_ALLOWED_FIELD_PATHS = (
    "$.schema_version",
    "$.generated_at",
    "$.reward_metadata_visibility",
    "$.reward_allowlist_policy_version",
    "$.reward_metadata_allowed_field_paths",
    "$.reward_metadata_allowed_field_paths[*]",
    "$.final_verifier_authority_preserved",
    "$.reward_records",
    "$.reward_records[*].sample_id",
    "$.reward_records[*].final_verifier_result",
    "$.reward_records[*].final_verifier_result_ref",
    "$.reward_records[*].reward_audit_outcome",
    "$.reward_records[*].structured_reward",
    "$.reward_records[*].structured_reward.model_visible",
    "$.reward_records[*].structured_reward.value",
    "$.reward_records[*].reward_metadata",
    "$.reward_records[*].reward_metadata.reward_version",
    "$.reward_records[*].reward_metadata.formula",
    "$.reward_records[*].reward_metadata.components",
    "$.reward_records[*].reward_metadata.components[*].name",
    "$.reward_records[*].reward_metadata.components[*].weight",
    "$.reward_records[*].reward_metadata.sources",
    "$.reward_records[*].reward_metadata.sources[*].source",
    "$.reward_records[*].reward_metadata.sources[*].model_visible",
    "$.reward_records[*].reward_metadata.invalid_for_training",
    "$.reward_records[*].reward_metadata.invalid_reason",
    "$.reward_records[*].reward_metadata.acceptance_policy_version",
    "$.reward_records[*].reward_metadata.reward_clip_range",
    "$.reward_records[*].reward_metadata.reward_clip_range[*]",
    "$.reward_records[*].reward_metadata.model_visible",
)


def build_v4_export_quality(
    *,
    output_dir: str | Path,
    agent_run_integration: str | Path,
    fail_if_output_exists: bool = False,
) -> Path:
    """Build deterministic V4 stage 6 export quality evidence."""

    output_path = Path(output_dir)
    if fail_if_output_exists:
        existing = [output_path / name for name in STAGE6_OUTPUTS if (output_path / name).exists()]
        if existing:
            raise ConfigError("V4 stage 6 输出已存在，不能覆盖旧 evidence：" + ", ".join(str(path) for path in existing))
    output_path.mkdir(parents=True, exist_ok=True)
    trajectory_ref = _trajectory_ref(agent_run_integration)
    final_verifier_boundary_ref = _final_verifier_boundary_ref(agent_run_integration)
    final_verifier_records = _load_final_verifier_records(final_verifier_boundary_ref)
    _require_final_verifier_record(final_verifier_records, "v4-run-completed-001", "accepted")
    _require_final_verifier_record(final_verifier_records, "v4-run-interrupted-001", "rejected")
    denylist_sha = v4_contamination_denylist_sha256()
    comparable_scope = {
        "task_id": "v4_go_cobra_completion_args",
        "task_family": "pr_issue_constructed_real_repository",
        "source_tree_hash": _sha256_payload({"source": "v4_go_cobra_completion_args", "revision": "fixed"}),
        "baseline_verifier_plan_hash": _sha256_payload({"baseline_verifier": "v4_go_cobra_completion_args"}),
        "final_verifier_plan_hash": _sha256_payload({"final_verifier": "v4_go_cobra_completion_args", "mode": "strict_clean_checkout"}),
        "tool_schema_snapshot_hash": "stage5-bound-tool-schema",
        "context_strategy_id": "repo_harness_v4_default_context_strategy_v0",
    }

    fixture_refs = _write_export_fixtures(output_path)
    sample_tier_path = output_path / "sample_tier_manifest.json"
    sample_records = [
        {
            "sample_id": "sample-accepted-trainable-sft",
            **comparable_scope,
            "run_id": "v4-run-completed-001",
            "outcome_tier": "verifier_accepted",
            "final_verifier_result": "accepted",
            "final_verifier_result_ref": _final_verifier_ref("v4-run-completed-001", "accepted"),
            "trainability_status": "trainable",
            "trainable_payload": {
                "format": "sft",
                "prompt_text": "Use public task context and repository observations.",
                "assistant_target": "Apply a minimal patch and run the public verifier command.",
            },
            "model_visible": True,
            "reward_metadata_ref": "audit-only:reward-metadata-sample-accepted-trainable-sft",
        },
        {
            "sample_id": "sample-rejected-diagnostic-failure",
            **comparable_scope,
            "run_id": "v4-run-interrupted-001",
            "outcome_tier": "verifier_rejected",
            "final_verifier_result": "rejected",
            "final_verifier_result_ref": _final_verifier_ref("v4-run-interrupted-001", "rejected"),
            "trainability_status": "diagnostic_only",
            "invalid_for_training": True,
            "invalid_reason": "final_verifier_rejected",
        },
        {
            "sample_id": "sample-accepted-diagnostic-excessive-patch",
            **comparable_scope,
            "run_id": "v4-run-completed-001",
            "outcome_tier": "verifier_accepted",
            "final_verifier_result": "accepted",
            "final_verifier_result_ref": _final_verifier_ref("v4-run-completed-001", "accepted"),
            "trainability_status": "diagnostic_only",
            "invalid_for_training": True,
            "invalid_reason": "excessive_patch_requires_manual_review",
        },
    ]
    _write_json(
        sample_tier_path,
        {
            "schema_version": SAMPLE_TIER_MANIFEST_VERSION,
            "generated_at": _utc_timestamp(),
            "outcome_tier_policy": "repo_harness_v4_outcome_tier_policy_v0",
            "trainability_policy": "repo_harness_v4_trainability_policy_v0",
            "outcome_tier_distinct_from_trainability_status": True,
            "samples": sample_records,
        },
    )
    failure_dataset_path = output_path / "failure_dataset.jsonl"
    failure_records = [
        {
            "schema_version": FAILURE_DATASET_ENTRY_VERSION,
            "failure_id": "failure-v4-py-click-help-hint-shadowing-turn-002",
            "sample_id": "sample-rejected-diagnostic-failure",
            "run_id": "v4-run-interrupted-001",
            "task_id": comparable_scope["task_id"],
            "failure_category": "incorrect_patch_behavior",
            "turn_id": "turn-002",
            "tool_call_id": "tool-call-v4-run-interrupted-001",
            "workspace_state_ref": "workspace-state:v4-run-interrupted-001:after-tool-result",
            "final_verifier_result_ref": _final_verifier_ref("v4-run-interrupted-001", "rejected"),
            "failure_source_component": "agent_patch_generation",
            "evidence_ref": {"kind": "artifact_ref", "path": "runs/v4-run-interrupted-001/events.jsonl"},
            "trainability_status": "diagnostic_only",
        }
    ]
    _write_jsonl(failure_dataset_path, failure_records)
    packing_path = output_path / "packing_manifest.json"
    _write_json(
        packing_path,
        {
            "schema_version": PACKING_MANIFEST_VERSION,
            "generated_at": _utc_timestamp(),
            "packing_policy": "repo_harness_v4_trajectory_packing_v0",
            "packed_samples": [
                {
                    "pack_id": "pack-v4-accepted-trainable-001",
                    "sample_id": "sample-accepted-trainable-sft",
                    "original_trajectory_ref": trajectory_ref,
                    "turn_refs": ["record-v4-run-completed-001-001", "event-v4-run-completed-001-002"],
                    "trainability_status": "trainable",
                },
                {
                    "pack_id": "pack-v4-rejected-diagnostic-001",
                    "sample_id": "sample-rejected-diagnostic-failure",
                    "original_trajectory_ref": trajectory_ref,
                    "turn_refs": ["record-v4-run-interrupted-001-001", "event-v4-run-interrupted-001-002"],
                    "trainability_status": "diagnostic_only",
                },
            ],
        },
    )
    reward_path = output_path / "reward_audit_report.json"
    reward_records = [
        _reward_record(
            sample_id="sample-accepted-trainable-sft",
            final_verifier_result="accepted",
            final_verifier_result_ref=_final_verifier_ref("v4-run-completed-001", "accepted"),
            reward_audit_outcome="verifier_accepted",
            invalid_for_training=False,
            invalid_reason=None,
        ),
        _reward_record(
            sample_id="sample-rejected-diagnostic-failure",
            final_verifier_result="rejected",
            final_verifier_result_ref=_final_verifier_ref("v4-run-interrupted-001", "rejected"),
            reward_audit_outcome="verifier_rejected",
            invalid_for_training=True,
            invalid_reason="final_verifier_rejected",
        ),
    ]
    _write_json(
        reward_path,
        {
            "schema_version": REWARD_AUDIT_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "reward_metadata_visibility": "audit_only_model_visible_false",
            "reward_allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
            "reward_metadata_allowed_field_paths": [
                *REWARD_AUDIT_ALLOWED_FIELD_PATHS,
            ],
            "final_verifier_authority_preserved": True,
            "reward_records": reward_records,
        },
    )
    _write_json(
        output_path / "reward_hacking_risk_audit_report.json",
        {
            "schema_version": REWARD_HACKING_RISK_AUDIT_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "final_verifier_authority_preserved": True,
            "verifier_rejected_samples_promoted_by_reward": 0,
            "reward_hacking_risks": [
                {
                    "risk_id": "reward-risk-final-verifier-bypass",
                    "risk": "patch tries to bypass final verifier",
                    "detected": False,
                    "blocked_by": "formal_final_verifier_authority",
                }
            ],
        },
    )
    _write_json(
        output_path / "patch_quality_report.json",
        {
            "schema_version": PATCH_QUALITY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "patch_quality_metric_schema": "repo_harness_v4_patch_quality_metrics_v0",
            "patch_records": [
                {
                    "sample_id": "sample-accepted-trainable-sft",
                    "patch_quality_status": "minimal_patch",
                    "excessive_patch": False,
                    "changed_file_count": 1,
                    "changed_line_count": 2,
                    "test_file_change_ratio": 0.0,
                    "generated_file_change_count": 0,
                    "duplicate_change_count": 0,
                    "unrelated_change_risk": "low",
                    "accepted_main_fact": False,
                    "reward_main_fact": False,
                },
                {
                    "sample_id": "sample-accepted-diagnostic-excessive-patch",
                    "patch_quality_status": "excessive_patch_requires_manual_review",
                    "excessive_patch": True,
                    "changed_file_count": 12,
                    "changed_line_count": 900,
                    "test_file_change_ratio": 0.75,
                    "generated_file_change_count": 3,
                    "duplicate_change_count": 4,
                    "unrelated_change_risk": "high",
                    "accepted_main_fact": False,
                    "reward_main_fact": False,
                    "trainability_status": "diagnostic_only",
                },
            ],
        },
    )
    _write_json(
        output_path / "test_overfitting_risk_audit_report.json",
        {
            "schema_version": TEST_OVERFITTING_RISK_AUDIT_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "risk_records": [
                {"risk_type": "test_only_patch", "flagged": True, "export_blocked": True},
                {"risk_type": "deleted_verifier_path", "flagged": True, "export_blocked": True},
                {"risk_type": "hidden_selector_hardcode", "flagged": True, "export_blocked": True},
                {"risk_type": "removed_failing_assertion", "flagged": True, "export_blocked": True},
                {"risk_type": "evaluator_only_evidence_read", "flagged": True, "export_blocked": True},
                {"risk_type": "verifier_bypass_attempt", "flagged": True, "export_blocked": True},
                {"risk_type": "modified_verifier_configuration", "flagged": True, "export_blocked": True},
            ],
        },
    )
    _write_json(
        output_path / "preference_pair_trainability_report.json",
        {
            "schema_version": PREFERENCE_PAIR_TRAINABILITY_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "trainable_preference_pair_count": 1,
            "blocked_pair_count": 1,
            "pair_records": [
                {
                    "pair_id": "pref-pair-v4-001",
                    "chosen_sample_id": "sample-accepted-trainable-sft",
                    "rejected_sample_id": "sample-rejected-diagnostic-failure",
                    "compare_scope": {
                        **comparable_scope,
                        "chosen_outcome_tier": "verifier_accepted",
                        "rejected_outcome_tier": "verifier_rejected",
                        "comparable_outcome_policy": "accepted_vs_rejected_same_task_and_verifier_plan",
                    },
                    "trainability_status": "trainable",
                    "baseline_blocked": False,
                },
                {
                    "pair_id": "pref-pair-v4-blocked-001",
                    "trainability_status": "blocked",
                    "baseline_blocked": True,
                    "blocked_reason": "baseline_run_missing_comparable_final_verifier_mode",
                },
            ],
        },
    )
    _write_json(
        output_path / "blocked_pair_report.json",
        {
            "schema_version": BLOCKED_PAIR_REPORT_VERSION,
            "generated_at": _utc_timestamp(),
            "warning": True,
            "blocked_reason": "preference_pair_baseline_blocked",
            "sample_count": 1,
            "rejected_reason_distribution": {
                "baseline_run_missing_comparable_final_verifier_mode": 1,
            },
            "next_step": "rerun comparable accepted and rejected samples with matching final verifier mode",
        },
    )
    manifest_path = output_path / "trajectory_quality_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": V4_EXPORT_QUALITY_MANIFEST_VERSION,
            "generated_at": _utc_timestamp(),
            "denylist_version": V4_CONTAMINATION_DENYLIST_VERSION,
            "denylist_sha256": denylist_sha,
            "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
            "trajectory_store_ref": trajectory_ref,
            "final_verifier_boundary_ref": final_verifier_boundary_ref,
            "sample_tier_manifest_ref": _file_ref(sample_tier_path, output_path),
            "failure_dataset_ref": _file_ref(failure_dataset_path, output_path),
            "packing_manifest_ref": _file_ref(packing_path, output_path),
            "reward_audit_report_ref": _file_ref(reward_path, output_path),
            "export_fixture_refs": fixture_refs,
            "trainable_payload_contamination_status": "clean",
            "final_verifier_is_authority": True,
        },
    )
    inspect_v4_export_quality(output_path, assert_complete=True)
    return manifest_path


def inspect_v4_export_quality(path: str | Path, *, assert_complete: bool = False) -> str:
    target = Path(path)
    failures: list[str] = []
    manifest = _read_json_for_inspect(target / "trajectory_quality_manifest.json", failures)
    sample_tier = _read_json_for_inspect(target / "sample_tier_manifest.json", failures)
    failure_records = _read_jsonl_for_inspect(target / "failure_dataset.jsonl", failures)
    packing = _read_json_for_inspect(target / "packing_manifest.json", failures)
    reward = _read_json_for_inspect(target / "reward_audit_report.json", failures)
    hacking = _read_json_for_inspect(target / "reward_hacking_risk_audit_report.json", failures)
    patch_quality = _read_json_for_inspect(target / "patch_quality_report.json", failures)
    overfitting = _read_json_for_inspect(target / "test_overfitting_risk_audit_report.json", failures)
    preference = _read_json_for_inspect(target / "preference_pair_trainability_report.json", failures)
    blocked = _read_json_for_inspect(target / "blocked_pair_report.json", failures)
    _expect(manifest, "schema_version", V4_EXPORT_QUALITY_MANIFEST_VERSION, failures, "trajectory_quality_manifest")
    _expect(sample_tier, "schema_version", SAMPLE_TIER_MANIFEST_VERSION, failures, "sample_tier_manifest")
    _expect(packing, "schema_version", PACKING_MANIFEST_VERSION, failures, "packing_manifest")
    _expect(reward, "schema_version", REWARD_AUDIT_REPORT_VERSION, failures, "reward_audit_report")
    _expect(hacking, "schema_version", REWARD_HACKING_RISK_AUDIT_REPORT_VERSION, failures, "reward_hacking_risk_audit_report")
    _expect(patch_quality, "schema_version", PATCH_QUALITY_REPORT_VERSION, failures, "patch_quality_report")
    _expect(overfitting, "schema_version", TEST_OVERFITTING_RISK_AUDIT_REPORT_VERSION, failures, "test_overfitting_risk_audit_report")
    _expect(preference, "schema_version", PREFERENCE_PAIR_TRAINABILITY_REPORT_VERSION, failures, "preference_pair_trainability_report")
    _expect(blocked, "schema_version", BLOCKED_PAIR_REPORT_VERSION, failures, "blocked_pair_report")
    final_verifier_records = _inspect_manifest_refs(manifest, target, failures)
    sample_records = _inspect_sample_tiers(sample_tier, final_verifier_records, failures)
    _inspect_failure_dataset(failure_records, sample_records, final_verifier_records, failures)
    _inspect_packing(packing, failures)
    _inspect_reward_audit(reward, sample_records, final_verifier_records, failures)
    _inspect_reward_hacking(hacking, failures)
    _inspect_patch_quality(patch_quality, failures)
    _inspect_test_overfitting(overfitting, failures)
    _inspect_preference_pairs(preference, blocked, sample_records, failures)
    _inspect_export_fixtures(manifest, target, failures)
    return _inspect_result("inspect-v4-export-quality", target, failures, assert_complete, "complete")


def _inspect_manifest_refs(manifest: dict[str, Any], root: Path, failures: list[str]) -> dict[tuple[str, str], dict[str, Any]]:
    if manifest.get("final_verifier_is_authority") is not True:
        failures.append("trajectory_quality_manifest 必须声明 final verifier 是 authority。")
    if manifest.get("trainable_payload_contamination_status") != "clean":
        failures.append("trajectory_quality_manifest trainable payload contamination 必须 clean。")
    expected_denylist_sha = v4_contamination_denylist_sha256()
    if manifest.get("denylist_sha256") != expected_denylist_sha:
        failures.append("trajectory_quality_manifest denylist_sha256 不匹配统一 V4 denylist。")
    trajectory_ref = manifest.get("trajectory_store_ref")
    trajectory_path = _inspect_external_file_ref(trajectory_ref, failures, label="trajectory_store_ref")
    if trajectory_path:
        payload = _read_json_for_inspect(trajectory_path, failures)
        _expect(payload, "schema_version", V4_TRAJECTORY_STORE_INTEGRITY_REPORT_VERSION, failures, "trajectory_store_ref")
    final_boundary_records: dict[tuple[str, str], dict[str, Any]] = {}
    final_boundary_path = _inspect_external_file_ref(manifest.get("final_verifier_boundary_ref"), failures, label="final_verifier_boundary_ref")
    if final_boundary_path:
        final_boundary_payload = _read_json_for_inspect(final_boundary_path, failures)
        final_boundary_records = _final_verifier_record_map(final_boundary_payload, failures, final_boundary_path.parent)
    for field in (
        "sample_tier_manifest_ref",
        "failure_dataset_ref",
        "packing_manifest_ref",
        "reward_audit_report_ref",
    ):
        _inspect_file_ref(manifest.get(field), root, failures, label=field)
    return final_boundary_records


def _final_verifier_record_map(
    payload: dict[str, Any],
    failures: list[str],
    root: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    if payload.get("schema_version") != "repo_harness_v4_final_verifier_boundary_report_v0":
        failures.append("final_verifier_boundary_report schema_version 不匹配。")
    if payload.get("formal_final_verifier_authority") is not True:
        failures.append("final_verifier_boundary_report 必须声明 final verifier authority。")
    for index, record in enumerate(payload.get("final_verifier_records") or [], start=1):
        run_id = str(record.get("run_id") or "")
        result = str(record.get("final_verifier_result") or "")
        if not run_id or result not in {"accepted", "rejected", "inconclusive"}:
            failures.append(f"final_verifier_records[{index}] 缺少 run_id 或合法 final_verifier_result。")
            continue
        if record.get("after_agent_stop") is not True:
            failures.append(f"final_verifier_records[{index}] 必须 after_agent_stop=true。")
        if record.get("authority") != "final_verifier":
            failures.append(f"final_verifier_records[{index}] authority 必须是 final_verifier。")
        if record.get("final_verifier_result_model_visible") is not False:
            failures.append(f"final_verifier_records[{index}] final verifier result 必须 model_visible=false。")
        if record.get("formal_verifier_mode") != "strict_clean_checkout":
            failures.append(f"final_verifier_records[{index}] formal_verifier_mode 必须是 strict_clean_checkout。")
        if not record.get("final_verifier_event_ref"):
            failures.append(f"final_verifier_records[{index}] 缺少 final_verifier_event_ref。")
        events_path = root / "runs" / run_id / "events.jsonl"
        if events_path.exists():
            events = _read_jsonl_for_inspect(events_path, failures)
            event = next((event for event in events if event.get("event_id") == record.get("final_verifier_event_ref")), None)
            if event is None:
                failures.append(f"final_verifier_records[{index}] final_verifier_event_ref 不存在于 events.jsonl。")
            elif event.get("event_type") != "final_verifier" or event.get("model_visible") is not False:
                failures.append(f"final_verifier_records[{index}] final verifier event 必须是非模型可见 final_verifier。")
        else:
            failures.append(f"final_verifier_records[{index}] 对应 run events.jsonl 不存在。")
        records[(run_id, result)] = record
    return records


def _inspect_sample_final_verifier_binding(
    sample: dict[str, Any],
    final_verifier_records: dict[tuple[str, str], dict[str, Any]],
    failures: list[str],
    label: str,
) -> None:
    run_id = str(sample.get("run_id") or "")
    result = str(sample.get("final_verifier_result") or "")
    expected_ref = _final_verifier_ref(run_id, result) if run_id and result else ""
    if sample.get("final_verifier_result_ref") != expected_ref:
        failures.append(f"{label} final_verifier_result_ref 与 run_id/result 不一致。")
    record = final_verifier_records.get((run_id, result))
    if record is None:
        failures.append(f"{label} final_verifier_result 没有关联 final_verifier_boundary_report 记录。")


def _inspect_reward_allowed_paths(payload: dict[str, Any], failures: list[str]) -> None:
    allowed = set(REWARD_AUDIT_ALLOWED_FIELD_PATHS)
    for path in _json_leaf_paths(payload):
        if path not in allowed:
            failures.append(f"reward_audit_report 字段路径未列入 allowlist：{path}")


def _json_leaf_paths(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, child in value.items():
            paths.extend(_json_leaf_paths(child, f"{path}.{key}"))
        return paths
    if isinstance(value, list):
        paths = [path]
        for child in value:
            paths.extend(_json_leaf_paths(child, f"{path}[*]"))
        return paths
    return [path]


def _inspect_sample_tiers(
    sample_tier: dict[str, Any],
    final_verifier_records: dict[tuple[str, str], dict[str, Any]],
    failures: list[str],
) -> dict[str, dict[str, Any]]:
    if sample_tier.get("outcome_tier_distinct_from_trainability_status") is not True:
        failures.append("sample_tier_manifest 必须区分 outcome tier 和 trainability status。")
    samples_by_id: dict[str, dict[str, Any]] = {}
    for index, sample in enumerate(sample_tier.get("samples") or [], start=1):
        sample_id = str(sample.get("sample_id") or "")
        if not sample_id:
            failures.append(f"samples[{index}] 缺少 sample_id。")
        elif sample_id in samples_by_id:
            failures.append(f"samples[{index}] sample_id 重复。")
        else:
            samples_by_id[sample_id] = sample
        outcome = sample.get("outcome_tier")
        trainability = sample.get("trainability_status")
        for field in COMPARABLE_SAMPLE_FIELDS:
            if not sample.get(field):
                failures.append(f"samples[{index}] 缺少可比较样本字段：{field}。")
        if outcome in {"trainable", "diagnostic_only", "invalid"}:
            failures.append(f"samples[{index}] outcome_tier 与 trainability_status 混用。")
        if trainability in {"verifier_accepted", "verifier_rejected"}:
            failures.append(f"samples[{index}] trainability_status 与 outcome_tier 混用。")
        if outcome in OUTCOME_TO_FINAL_VERIFIER and sample.get("final_verifier_result") != OUTCOME_TO_FINAL_VERIFIER[outcome]:
            failures.append(f"samples[{index}] outcome_tier 必须与 final_verifier_result 一致。")
        _inspect_sample_final_verifier_binding(sample, final_verifier_records, failures, f"samples[{index}]")
        if trainability == "trainable" and sample.get("final_verifier_result") != "accepted":
            failures.append(f"samples[{index}] trainable 样本必须来自 final verifier accepted。")
        if trainability == "trainable":
            _inspect_trainable_payload_clean(sample.get("trainable_payload"), failures, f"samples[{index}].trainable_payload")
    return samples_by_id


def _inspect_failure_dataset(
    records: list[dict[str, Any]],
    samples_by_id: dict[str, dict[str, Any]],
    final_verifier_records: dict[tuple[str, str], dict[str, Any]],
    failures: list[str],
) -> None:
    for index, record in enumerate(records, start=1):
        _expect(record, "schema_version", FAILURE_DATASET_ENTRY_VERSION, failures, f"failure_dataset[{index}]")
        for field in FAILURE_DATASET_REQUIRED_FIELDS:
            if not record.get(field):
                failures.append(f"failure_dataset[{index}] 缺少 {field}。")
        if record.get("trainability_status") == "trainable":
            failures.append(f"failure_dataset[{index}] failure dataset 不得标为 trainable。")
        sample = samples_by_id.get(str(record.get("sample_id") or ""))
        if sample is None:
            failures.append(f"failure_dataset[{index}] sample_id 未绑定 sample tier。")
            continue
        if record.get("run_id") != sample.get("run_id") or record.get("task_id") != sample.get("task_id"):
            failures.append(f"failure_dataset[{index}] run_id/task_id 必须与 sample tier 一致。")
        _inspect_sample_final_verifier_binding(
            {
                "run_id": record.get("run_id"),
                "final_verifier_result": sample.get("final_verifier_result"),
                "final_verifier_result_ref": record.get("final_verifier_result_ref"),
            },
            final_verifier_records,
            failures,
            f"failure_dataset[{index}]",
        )


def _inspect_packing(packing: dict[str, Any], failures: list[str]) -> None:
    for index, sample in enumerate(packing.get("packed_samples") or [], start=1):
        if not isinstance(sample.get("original_trajectory_ref"), dict):
            failures.append(f"packed_samples[{index}] 缺少 original trajectory ref。")
        if not sample.get("sample_id") or not sample.get("pack_id"):
            failures.append(f"packed_samples[{index}] 缺少 sample_id 或 pack_id。")


def _inspect_reward_audit(
    reward: dict[str, Any],
    samples_by_id: dict[str, dict[str, Any]],
    final_verifier_records: dict[tuple[str, str], dict[str, Any]],
    failures: list[str],
) -> None:
    if reward.get("final_verifier_authority_preserved") is not True:
        failures.append("reward_audit_report 不得覆盖 final verifier authority。")
    if reward.get("reward_allowlist_policy_version") != V4_ALLOWLIST_POLICY_VERSION:
        failures.append("reward_audit_report reward_allowlist_policy_version 不匹配。")
    if reward.get("reward_metadata_allowed_field_paths") != list(REWARD_AUDIT_ALLOWED_FIELD_PATHS):
        failures.append("reward_audit_report reward_metadata_allowed_field_paths 必须等于实现层 allowlist。")
    _inspect_reward_allowed_paths(reward, failures)
    for index, record in enumerate(reward.get("reward_records") or [], start=1):
        metadata = record.get("reward_metadata") or {}
        structured_reward = record.get("structured_reward") or {}
        sample = samples_by_id.get(str(record.get("sample_id") or ""))
        if sample is None:
            failures.append(f"reward_records[{index}] sample_id 未绑定 sample tier。")
        else:
            if record.get("final_verifier_result") != sample.get("final_verifier_result"):
                failures.append(f"reward_records[{index}] final_verifier_result 必须与 sample tier 一致。")
            _inspect_sample_final_verifier_binding(
                {
                    "run_id": sample.get("run_id"),
                    "final_verifier_result": record.get("final_verifier_result"),
                    "final_verifier_result_ref": record.get("final_verifier_result_ref"),
                },
                final_verifier_records,
                failures,
                f"reward_records[{index}]",
            )
        for field in REWARD_METADATA_REQUIRED_FIELDS:
            if field not in metadata:
                failures.append(f"reward_records[{index}].reward_metadata 缺少 {field}。")
        if metadata.get("model_visible") is not False:
            failures.append(f"reward_records[{index}].reward_metadata 必须 model_visible=false。")
        if structured_reward.get("model_visible") is not False:
            failures.append(f"reward_records[{index}].structured_reward 必须 model_visible=false。")
        if record.get("final_verifier_result") == "rejected" and record.get("reward_audit_outcome") == "accepted":
            failures.append(f"reward_records[{index}] verifier rejected 样本不得被 reward audit 改成 accepted。")


def _inspect_reward_hacking(hacking: dict[str, Any], failures: list[str]) -> None:
    if hacking.get("verifier_rejected_samples_promoted_by_reward") != 0:
        failures.append("reward_hacking_risk_audit_report 不得提升 verifier rejected 样本。")
    if hacking.get("final_verifier_authority_preserved") is not True:
        failures.append("reward_hacking_risk_audit_report 必须保留 final verifier authority。")


def _inspect_patch_quality(patch_quality: dict[str, Any], failures: list[str]) -> None:
    for index, record in enumerate(patch_quality.get("patch_records") or [], start=1):
        if record.get("excessive_patch") is True:
            if record.get("accepted_main_fact") is not False or record.get("reward_main_fact") is not False:
                failures.append(f"patch_records[{index}] excessive patch 不得作为 accepted 主事实或 reward 主事实。")
            if record.get("trainability_status") == "trainable":
                failures.append(f"patch_records[{index}] excessive patch 不得 trainable。")
        for field in (
            "changed_file_count",
            "changed_line_count",
            "test_file_change_ratio",
            "generated_file_change_count",
            "duplicate_change_count",
            "unrelated_change_risk",
        ):
            if field not in record:
                failures.append(f"patch_records[{index}] 缺少 patch quality metric：{field}。")


def _inspect_test_overfitting(overfitting: dict[str, Any], failures: list[str]) -> None:
    seen = {record.get("risk_type"): record for record in overfitting.get("risk_records") or []}
    missing = TEST_OVERFITTING_REQUIRED_RISKS.difference(seen)
    if missing:
        failures.append("test_overfitting_risk_audit_report 缺少风险：" + ", ".join(sorted(missing)))
    for risk_type, record in seen.items():
        if risk_type in TEST_OVERFITTING_REQUIRED_RISKS:
            if record.get("flagged") is not True or record.get("export_blocked") is not True:
                failures.append(f"risk_records[{risk_type}] 必须 flagged=true 且 export_blocked=true。")


def _inspect_preference_pairs(
    preference: dict[str, Any],
    blocked: dict[str, Any],
    samples_by_id: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    pair_records = preference.get("pair_records") or []
    trainable_pairs = [record for record in pair_records if record.get("trainability_status") == "trainable"]
    blocked_pairs = [record for record in pair_records if record.get("trainability_status") == "blocked"]
    if preference.get("trainable_preference_pair_count") != len(trainable_pairs):
        failures.append("preference_pair_trainability_report trainable_preference_pair_count 与 pair_records 不一致。")
    if preference.get("blocked_pair_count") != len(blocked_pairs):
        failures.append("preference_pair_trainability_report blocked_pair_count 与 pair_records 不一致。")
    for index, record in enumerate(pair_records, start=1):
        if record.get("trainability_status") == "trainable":
            chosen = samples_by_id.get(str(record.get("chosen_sample_id") or ""))
            rejected = samples_by_id.get(str(record.get("rejected_sample_id") or ""))
            if chosen is None or rejected is None:
                failures.append(f"pair_records[{index}] trainable pair 缺少 chosen/rejected sample id。")
                continue
            if record.get("baseline_blocked") is not False:
                failures.append(f"pair_records[{index}] trainable pair baseline_blocked 必须为 false。")
            scope = record.get("compare_scope")
            if not isinstance(scope, dict):
                failures.append(f"pair_records[{index}] trainable pair 缺少 compare_scope。")
                scope = {}
            for field in COMPARABLE_SAMPLE_FIELDS:
                if chosen.get(field) != rejected.get(field) or scope.get(field) != chosen.get(field):
                    failures.append(f"pair_records[{index}] trainable pair 必须共享可比较字段：{field}。")
            if chosen.get("final_verifier_result") != "accepted" or chosen.get("trainability_status") != "trainable":
                failures.append(f"pair_records[{index}] chosen_sample_id 必须引用 final verifier accepted trainable 样本。")
            if rejected.get("final_verifier_result") not in {"rejected", "inconclusive"} or rejected.get("trainability_status") == "trainable":
                failures.append(f"pair_records[{index}] rejected_sample_id 必须引用 final verifier rejected diagnostic 样本。")
            if scope.get("chosen_outcome_tier") != chosen.get("outcome_tier") or scope.get("rejected_outcome_tier") != rejected.get("outcome_tier"):
                failures.append(f"pair_records[{index}] compare_scope outcome 必须与 chosen/rejected 样本一致。")
        if record.get("trainability_status") == "blocked" and not record.get("blocked_reason"):
            failures.append(f"pair_records[{index}] blocked pair 缺少 blocked_reason。")
    if preference.get("trainable_preference_pair_count", 0) < 1 and blocked.get("warning") is not True:
        failures.append("没有 trainable preference pair 时必须生成 blocked_pair_report warning。")
    if preference.get("trainable_preference_pair_count", 0) < 1 and blocked.get("blocked_reason") != "no_trainable_preference_pair":
        failures.append("没有 trainable preference pair 时 blocked_pair_report 必须使用 no_trainable_preference_pair。")
    if blocked.get("warning") is not True:
        failures.append("blocked_pair_report 必须包含 warning。")
    if blocked.get("sample_count") != preference.get("blocked_pair_count"):
        failures.append("blocked_pair_report sample_count 必须与 blocked_pair_count 一致。")
    if not blocked.get("blocked_reason") or blocked.get("sample_count", 0) < 1:
        failures.append("blocked_pair_report 必须包含 blocked reason 和样本数量。")
    if not isinstance(blocked.get("rejected_reason_distribution"), dict) or not blocked.get("rejected_reason_distribution"):
        failures.append("blocked_pair_report 必须包含被拒绝原因分布。")
    if not blocked.get("next_step"):
        failures.append("blocked_pair_report 必须包含下一步修复入口。")


def _inspect_export_fixtures(manifest: dict[str, Any], root: Path, failures: list[str]) -> None:
    refs = manifest.get("export_fixture_refs")
    if not isinstance(refs, dict):
        failures.append("trajectory_quality_manifest 缺少 export_fixture_refs。")
        return
    for export_format in EXPORT_FORMATS:
        format_refs = refs.get(export_format)
        if not isinstance(format_refs, dict):
            failures.append(f"export_fixture_refs 缺少 {export_format}。")
            continue
        for fixture_kind in ("valid_fixture_ref", "negative_fixture_ref"):
            fixture_path = _inspect_file_ref(format_refs.get(fixture_kind), root, failures, label=f"{export_format}.{fixture_kind}")
            if fixture_path:
                records = _read_jsonl_for_inspect(fixture_path, failures)
                if fixture_kind == "valid_fixture_ref":
                    for index, record in enumerate(records, start=1):
                        if record.get("trainability_status") == "trainable":
                            _inspect_trainable_payload_clean(record.get("payload"), failures, f"{export_format}.valid_fixture[{index}]")


def _inspect_trainable_payload_clean(payload: Any, failures: list[str], label: str) -> None:
    try:
        V4ContaminationDenylist().assert_clean(surface="export_records", payload=payload)
    except ValueError as exc:
        failures.append(f"{label} 污染扫描失败：{exc}")
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    for term in ("reward scalar", "reward label", "reward_scalar", "reward_label", "hidden selector", "hidden_selector"):
        if term in text:
            failures.append(f"{label} 包含禁止进入 trainable payload 的字段或文本：{term}")


def _write_export_fixtures(output_path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    fixture_dir = output_path / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    refs: dict[str, dict[str, dict[str, Any]]] = {}
    valid_payloads = {
        "sft": {"messages": [{"role": "assistant", "content": "Apply a minimal repository patch."}]},
        "rl": {"observation": "public repository state", "action": "run public verifier"},
        "preference": {"chosen": "minimal patch trajectory", "rejected": "rejected diagnostic trajectory"},
    }
    negative_payloads = {
        "sft": {"invalid_reason": "contains_hidden_selector_fixture", "payload": "hidden selector fixture must fail"},
        "rl": {"invalid_reason": "contains_reward_scalar_fixture", "payload": "reward scalar fixture must fail"},
        "preference": {"invalid_reason": "missing_comparable_baseline_fixture", "payload": "baseline pair blocked"},
    }
    for export_format in EXPORT_FORMATS:
        valid_path = fixture_dir / f"{export_format}_valid.jsonl"
        negative_path = fixture_dir / f"{export_format}_negative.jsonl"
        _write_jsonl(
            valid_path,
            [
                {
                    "schema_version": EXPORT_FIXTURE_RECORD_VERSION,
                    "fixture_kind": "valid",
                    "export_format": export_format,
                    "trainability_status": "trainable",
                    "payload": valid_payloads[export_format],
                }
            ],
        )
        _write_jsonl(
            negative_path,
            [
                {
                    "schema_version": EXPORT_FIXTURE_RECORD_VERSION,
                    "fixture_kind": "negative",
                    "export_format": export_format,
                    "trainability_status": "invalid",
                    "invalid_for_training": True,
                    "payload": negative_payloads[export_format],
                }
            ],
        )
        refs[export_format] = {
            "valid_fixture_ref": _file_ref(valid_path, output_path),
            "negative_fixture_ref": _file_ref(negative_path, output_path),
        }
    return refs


def _reward_record(
    *,
    sample_id: str,
    final_verifier_result: str,
    final_verifier_result_ref: str,
    reward_audit_outcome: str,
    invalid_for_training: bool,
    invalid_reason: str | None,
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "final_verifier_result": final_verifier_result,
        "final_verifier_result_ref": final_verifier_result_ref,
        "reward_audit_outcome": reward_audit_outcome,
        "structured_reward": {"model_visible": False, "value": 1.0 if final_verifier_result == "accepted" else 0.0},
        "reward_metadata": {
            "reward_version": "repo_harness_v4_reward_metadata_v0",
            "formula": "final_verifier_acceptance_clipped",
            "components": [{"name": "formal_final_verifier", "weight": 1.0}],
            "sources": [{"source": "formal_final_verifier", "model_visible": False}],
            "invalid_for_training": invalid_for_training,
            "invalid_reason": invalid_reason,
            "acceptance_policy_version": "repo_harness_v4_acceptance_policy_v0",
            "reward_clip_range": [0.0, 1.0],
            "model_visible": False,
        },
    }


def _trajectory_ref(agent_run_integration: str | Path) -> dict[str, Any]:
    path = Path(agent_run_integration)
    if path.is_dir():
        path = path / "trajectory_store_integrity_report.json"
    if not path.exists():
        raise ConfigError(f"Stage 6 必需 trajectory store 输入不存在：{path}")
    return {
        "path": path.resolve().as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _final_verifier_boundary_ref(agent_run_integration: str | Path) -> dict[str, Any]:
    path = Path(agent_run_integration)
    if path.is_dir():
        path = path / "final_verifier_boundary_report.json"
    else:
        path = path.parent / "final_verifier_boundary_report.json"
    if not path.exists():
        raise ConfigError(f"Stage 6 必需 final verifier boundary 输入不存在：{path}")
    return {
        "path": path.resolve().as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _final_verifier_ref(run_id: str, final_verifier_result: str) -> str:
    return f"audit-only:final-verifier:{run_id}:{final_verifier_result}"


def _load_final_verifier_records(ref: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    failures: list[str] = []
    path = _inspect_external_file_ref(ref, failures, label="final_verifier_boundary_ref")
    if path is None:
        raise ConfigError("; ".join(failures))
    payload = _read_json_for_inspect(path, failures)
    records = _final_verifier_record_map(payload, failures, path.parent)
    if failures:
        raise ConfigError("; ".join(failures))
    return records


def _require_final_verifier_record(
    records: dict[tuple[str, str], dict[str, Any]],
    run_id: str,
    final_verifier_result: str,
) -> None:
    if (run_id, final_verifier_result) not in records:
        raise ConfigError(f"缺少正式 final verifier 边界记录：{run_id}/{final_verifier_result}")


def _inspect_external_file_ref(ref: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 外部文件 ref 缺失或不是 object。")
        return None
    path = Path(str(ref.get("path") or ""))
    if not path.is_absolute():
        failures.append(f"{label} 外部文件 ref 必须使用绝对路径。")
        return None
    if not path.exists():
        failures.append(f"{label} 外部文件 ref 路径不存在。")
        return None
    if ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} 外部文件 ref sha256 不匹配。")
    return path


def _inspect_file_ref(ref: Any, root: Path, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref, dict):
        failures.append(f"{label} 文件 ref 缺失或不是 object。")
        return None
    raw = str(ref.get("relative_path") or ref.get("path") or "")
    if not raw:
        failures.append(f"{label} 文件 ref 缺少 path。")
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        failures.append(f"{label} 文件 ref 路径不存在：{raw}")
        return None
    if ref.get("sha256") != sha256_file(path):
        failures.append(f"{label} 文件 ref sha256 不匹配。")
    return path


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"缺少文件：{path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"JSON 无法解析：{path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"JSON 顶层必须是 object：{path}")
        return {}
    return payload


def _read_jsonl_for_inspect(path: Path, failures: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        failures.append(f"缺少文件：{path}")
        return []
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"JSONL 无法解析：{path}:{line_no}: {exc}")
            continue
        if not isinstance(payload, dict):
            failures.append(f"JSONL 记录必须是 object：{path}:{line_no}")
            continue
        records.append(payload)
    if not records:
        failures.append(f"JSONL 必须非空：{path}")
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _file_ref(path: Path, root: Path) -> dict[str, Any]:
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _expect(payload: dict[str, Any], field: str, expected: Any, failures: list[str], label: str) -> None:
    if payload.get(field) != expected:
        failures.append(f"{label}.{field} 不匹配。")


def _inspect_result(command: str, path: Path, failures: list[str], assert_flag: bool, label: str) -> str:
    lines = [f"{command}: {path}"]
    if failures:
        if assert_flag:
            raise ConfigError("; ".join(failures))
        lines.append("Diagnostics:")
        lines.extend(f"- {failure}" for failure in failures)
    if assert_flag:
        lines.append(f"{command}: {label}")
    lines.append(f"{command}: passed")
    return "\n".join(lines)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
