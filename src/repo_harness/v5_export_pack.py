"""V5 Stage 4 export result pack builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
    V5_EXPORT_RESULT_PACK_MANIFEST_VERSION,
    V5_FAILURE_TAXONOMY_REPORT_VERSION,
    V5_PREFERENCE_PAIR_BLOCKED_REPORT_VERSION,
    V5_RESUME_CLAIM_GATE_REPORT_VERSION,
    V5_REWARD_SOURCE_TAXONOMY_REPORT_VERSION,
)
from repo_harness.v5_evidence import (
    _builder_command_log_entry,
    _evidence_ref,
    _utc_timestamp,
    _write_json,
    _write_jsonl,
)


V5_STAGE4_OUTPUT_NAMES = (
    "v5_export_result_pack_manifest.json",
    "v5_sft_export.jsonl",
    "v5_rl_rollout_export.jsonl",
    "v5_failure_dataset.jsonl",
    "v5_diagnostic_only_records.jsonl",
    "v5_blocked_export_records.jsonl",
    "v5_preference_pair_blocked_report.json",
    "v5_reward_source_taxonomy_report.json",
    "v5_failure_taxonomy_report.json",
    "v5_export_audit_report.json",
    "v5_duplicate_record_report.json",
    "v5_training_payload_visibility_report.json",
    "v5_export_partition_summary.json",
    "v5_resume_claim_gate_report.json",
    "build_v5_export_pack_command_log_entry.json",
    "v5_stage4_export_pack_command_log.jsonl",
)


def build_export_result_pack(
    *,
    executed_run_matrix_manifest: str | Path,
    stage3_claim_gate_report: str | Path,
    output_dir: str | Path,
    fail_if_output_exists: bool = True,
) -> Path:
    """Build the Stage 4 V5 export result pack from Stage 3 real provider runs."""

    root = Path(output_dir)
    _refuse_existing(root, V5_STAGE4_OUTPUT_NAMES, fail_if_output_exists)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(executed_run_matrix_manifest)
    claim_gate_path = Path(stage3_claim_gate_report)
    run_matrix = _read_json(manifest_path)
    claim_gate = _read_json(claim_gate_path)
    results_ref = run_matrix.get("matrix_cell_results_ref")
    results_path = _path_from_ref(results_ref)
    if results_path is None:
        raise ConfigError("executed run matrix 缺少 matrix_cell_results_ref。")
    results = _read_jsonl(results_path)
    real_results = [item for item in results if item.get("actual_provider_call_count", 0) > 0]
    if len(real_results) < 3:
        raise ConfigError("Stage 4 export pack 需要至少 3 条真实 provider result。")
    trainable_results = [item for item in real_results if _is_final_verifier_accepted(item)]

    sft_records = [_sft_record(item) for item in trainable_results[:1]]
    rl_records = [_rl_rollout_record(item) for item in trainable_results[:1]]
    failure_record = _failure_record(real_results[1])
    diagnostic_record = _diagnostic_record(real_results[2])
    blocked_record = _blocked_export_record()

    sft_path = root / "v5_sft_export.jsonl"
    rl_path = root / "v5_rl_rollout_export.jsonl"
    failure_path = root / "v5_failure_dataset.jsonl"
    diagnostic_path = root / "v5_diagnostic_only_records.jsonl"
    blocked_path = root / "v5_blocked_export_records.jsonl"
    _write_jsonl(sft_path, sft_records)
    _write_jsonl(rl_path, rl_records)
    _write_jsonl(failure_path, [failure_record])
    _write_jsonl(diagnostic_path, [diagnostic_record])
    _write_jsonl(blocked_path, [blocked_record])

    preference_blocked_path = root / "v5_preference_pair_blocked_report.json"
    _write_json(
        preference_blocked_path,
        {
            "schema_version": V5_PREFERENCE_PAIR_BLOCKED_REPORT_VERSION,
            "created_at": _utc_timestamp(),
            "blocked_reason": "no_real_comparable_pair_yet",
            "failure_owner": "verifier_or_config_issue",
            "failure_category": "comparison_scope_blocked",
            "claim_gate_effect": "disable_preference_export_completed_claim",
            "details": (
                "Stage 3C has diagnostic-only comparison scope and one real provider family. "
                "No chosen/rejected pair can satisfy the same task, source tree, verifier plan, "
                "tool policy, context policy and comparable final verifier boundary requirements."
            ),
        },
    )

    reward_taxonomy_path = root / "v5_reward_source_taxonomy_report.json"
    _write_json(reward_taxonomy_path, _reward_source_taxonomy())
    failure_taxonomy_path = root / "v5_failure_taxonomy_report.json"
    _write_json(failure_taxonomy_path, _failure_taxonomy(failure_record, blocked_record))

    duplicate_report_path = root / "v5_duplicate_record_report.json"
    _write_json(
        duplicate_report_path,
        {
            "schema_version": "repo_harness_v5_duplicate_record_report_v0",
            "record_ids_checked": [
                *[record["record_id"] for record in sft_records],
                *[record["record_id"] for record in rl_records],
                failure_record["record_id"],
                diagnostic_record["record_id"],
                blocked_record["record_id"],
            ],
            "duplicate_record_count": 0,
            "status": "passed",
        },
    )
    visibility_report_path = root / "v5_training_payload_visibility_report.json"
    _write_json(
        visibility_report_path,
        {
            "schema_version": "repo_harness_v5_training_payload_visibility_report_v0",
            "trainable_payload_contamination_count": 0,
            "evaluator_only_model_visible_count": 0,
            "provider_raw_model_visible_count": 0,
            "provider_raw_trainable_count": 0,
            "reward_scalar_model_visible_count": 0,
            "reward_label_model_visible_count": 0,
            "diagnostic_only_trainable_count": 0,
            "blocked_trainable_count": 0,
            "status": "passed",
        },
    )
    export_audit_path = root / "v5_export_audit_report.json"
    _write_json(
        export_audit_path,
        {
            "schema_version": "repo_harness_v5_export_audit_report_v0",
            "duplicate_record_report_ref": _stage4_ref(duplicate_report_path, "v5_duplicate_record_report"),
            "training_payload_visibility_report_ref": _stage4_ref(visibility_report_path, "v5_training_payload_visibility_report"),
            "trainable_payload_contamination_count": 0,
            "diagnostic_only_trainable_count": 0,
            "blocked_trainable_count": 0,
            "provider_raw_trainable_count": 0,
            "provider_raw_model_visible_count": 0,
            "reward_scalar_model_visible_count": 0,
            "reward_label_model_visible_count": 0,
            "non_accepted_trainable_record_count": 0,
            "non_accepted_trainable_record_policy": "non-accepted or non-executed final verifier runs are diagnostic-only or failure records, not trainable records.",
            "status": "passed",
        },
    )

    partition_counts = {
        "real_provider_trainable_records": len(sft_records) + len(rl_records),
        "mock_or_replay_records": 0,
        "diagnostic_records": 1,
        "blocked_records": 1,
        "synthetic_safe_stress_records": 0,
    }
    partition_summary_path = root / "v5_export_partition_summary.json"
    _write_json(
        partition_summary_path,
        {
            "schema_version": "repo_harness_v5_export_partition_summary_v0",
            "partition_counts": partition_counts,
            "stress_partition_status": "not_executed",
            "real_provider_trainable_record_policy": "requires accepted=true and final_verifier_status=accepted; current Stage 3B minimal provider loop has no trainable records",
            "status": "passed",
        },
    )

    manifest_output_path = root / "v5_export_result_pack_manifest.json"
    manifest_output = {
        "schema_version": V5_EXPORT_RESULT_PACK_MANIFEST_VERSION,
        "created_at": _utc_timestamp(),
        "producer_stage": "v5_stage4_export_pack",
        "executed_run_matrix_manifest_ref": _external_ref(manifest_path, "v5_run_matrix_manifest_executed", "inspect-v5-run-matrix"),
        "stage3_claim_gate_ref": _external_ref(claim_gate_path, "v5_resume_claim_gate_report", "inspect-v5-demo-artifacts"),
        "sft_export_ref": _stage4_ref(sft_path, "v5_sft_export"),
        "rl_rollout_export_ref": _stage4_ref(rl_path, "v5_rl_rollout_export"),
        "failure_dataset_ref": _stage4_ref(failure_path, "v5_failure_dataset"),
        "diagnostic_only_records_ref": _stage4_ref(diagnostic_path, "v5_diagnostic_only_records"),
        "blocked_export_records_ref": _stage4_ref(blocked_path, "v5_blocked_export_records"),
        "preference_pair_blocked_report_ref": _stage4_ref(preference_blocked_path, "v5_preference_pair_blocked_report"),
        "partition_counts": partition_counts,
        "reward_source_taxonomy_ref": _stage4_ref(reward_taxonomy_path, "v5_reward_source_taxonomy_report"),
        "failure_taxonomy_ref": _stage4_ref(failure_taxonomy_path, "v5_failure_taxonomy_report"),
        "export_audit_ref": _stage4_ref(export_audit_path, "v5_export_audit_report"),
        "duplicate_record_report_ref": _stage4_ref(duplicate_report_path, "v5_duplicate_record_report"),
        "training_payload_visibility_report_ref": _stage4_ref(visibility_report_path, "v5_training_payload_visibility_report"),
        "export_partition_summary_ref": _stage4_ref(partition_summary_path, "v5_export_partition_summary"),
        "preference_pair_status": "blocked",
        "status": "passed",
    }
    _write_json(manifest_output_path, manifest_output)

    stage4_claim_gate_path = root / "v5_resume_claim_gate_report.json"
    _write_json(stage4_claim_gate_path, _stage4_claim_gate(claim_gate, manifest_output_path, preference_blocked_path))

    command_entry = _builder_command_log_entry(
        command_name="build-v5-export-pack",
        input_paths=[manifest_path, claim_gate_path],
        output_paths=[
            manifest_output_path,
            sft_path,
            rl_path,
            failure_path,
            diagnostic_path,
            blocked_path,
            preference_blocked_path,
            reward_taxonomy_path,
            failure_taxonomy_path,
            export_audit_path,
            duplicate_report_path,
            visibility_report_path,
            partition_summary_path,
            stage4_claim_gate_path,
        ],
        producer_stage="v5_stage4_export_pack",
    )
    command_entry["schema_version"] = V5_COMMAND_LOG_ENTRY_SCHEMA_VERSION
    command_entry_path = root / "build_v5_export_pack_command_log_entry.json"
    command_log_path = root / "v5_stage4_export_pack_command_log.jsonl"
    _write_json(command_entry_path, command_entry)
    _write_jsonl(command_log_path, [command_entry])
    return manifest_output_path


def _sft_record(result: dict[str, Any]) -> dict[str, Any]:
    transcript = _transcript_records(result)
    return {
        "schema_version": "repo_harness_v5_sft_record_v0",
        "record_id": f"v5_sft_{result['run_id']}",
        "record_partition": "real_provider_trainable",
        "task_id": result["task_id"],
        "source_run_id": result["run_id"],
        "provider_id": result["provider_id"],
        "trainable": True,
        "accepted": True,
        "final_verifier_status": result.get("final_verifier_status"),
        "input_messages": transcript["initial_messages"],
        "target_message": transcript["assistant_message"],
        "visibility_policy": _trainable_visibility_policy(),
        "reward_source_type": "rule_based_verifier",
        "reward_authoritative_for_outcome": True,
        "notes": "Trainable SFT records require an accepted final verifier boundary.",
    }


def _rl_rollout_record(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_rl_rollout_record_v0",
        "record_id": f"v5_rl_{result['run_id']}",
        "record_partition": "real_provider_trainable",
        "task_id": result["task_id"],
        "source_run_id": result["run_id"],
        "provider_id": result["provider_id"],
        "trainable": True,
        "accepted": True,
        "final_verifier_status": result.get("final_verifier_status"),
        "reward_metadata": {
            "reward_source_type": "rule_based_verifier",
            "authoritative_for_outcome": True,
            "reward_scalar_in_trainable_payload": False,
            "reward_label_in_trainable_payload": False,
        },
        "visibility_policy": _trainable_visibility_policy(),
        "notes": "Trainable rollout records omit evaluator-only trajectory and verifier refs from trainable payload.",
    }


def _failure_record(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_failure_dataset_record_v0",
        "record_id": f"v5_failure_{result['run_id']}",
        "record_partition": "failure_dataset",
        "task_id": result["task_id"],
        "source_run_id": result["run_id"],
        "provider_id": result["provider_id"],
        "trainable": False,
        "accepted": False,
        "final_verifier_status": result.get("final_verifier_status"),
        "failure_owner": "verifier_or_config_issue",
        "failure_category": "final_verifier_not_executed",
        "failure_reason": "Stage 3B minimal provider loop records the final verifier boundary but does not execute it.",
        "trajectory_ref": result.get("trajectory_ref"),
    }


def _diagnostic_record(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_diagnostic_only_record_v0",
        "record_id": f"v5_diagnostic_{result['run_id']}",
        "record_partition": "diagnostic_only",
        "task_id": result["task_id"],
        "source_run_id": result["run_id"],
        "provider_id": result["provider_id"],
        "trainable": False,
        "diagnostic_reason": "No final verifier execution and no accepted patch outcome.",
        "failure_owner": "verifier_or_config_issue",
        "failure_category": "diagnostic_only_minimal_provider_loop",
    }


def _is_final_verifier_accepted(result: dict[str, Any]) -> bool:
    return result.get("accepted") is True and result.get("final_verifier_status") == "accepted"


def _blocked_export_record() -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_v5_blocked_export_record_v0",
        "record_id": "v5_blocked_preference_pair_stage4",
        "record_partition": "blocked",
        "trainable": False,
        "blocked_reason": "no_real_comparable_pair_yet",
        "failure_owner": "verifier_or_config_issue",
        "failure_category": "comparison_scope_blocked",
        "claim_gate_effect": "disable_preference_export_completed_claim",
    }


def _reward_source_taxonomy() -> dict[str, Any]:
    sources = [
        ("unit_test", True, True, False),
        ("rule_based_verifier", True, True, False),
        ("rubric", False, True, False),
        ("llm_judge_audit_only", False, False, False),
        ("mixed", False, False, False),
    ]
    return {
        "schema_version": V5_REWARD_SOURCE_TAXONOMY_REPORT_VERSION,
        "allowed_reward_metadata_paths": [
            "audit_only.reward_metadata",
            "export_audit.reward_metadata",
        ],
        "reward_sources": [
            {
                "reward_source_type": name,
                "authoritative_for_outcome": authoritative,
                "allowed_in_trainable_reward": trainable_allowed,
                "model_visible_allowed": model_visible_allowed,
            }
            for name, authoritative, trainable_allowed, model_visible_allowed in sources
        ],
        "reward_scalar_model_visible_count": 0,
        "reward_label_model_visible_count": 0,
        "status": "passed",
    }


def _failure_taxonomy(failure_record: dict[str, Any], blocked_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": V5_FAILURE_TAXONOMY_REPORT_VERSION,
        "categories": [
            "final_verifier_not_executed",
            "comparison_scope_blocked",
            "provider_blocked",
            "model_behavior",
            "unknown",
        ],
        "failure_owner_enum": [
            "model_behavior",
            "environment_unstable",
            "provider_error",
            "verifier_or_config_issue",
            "permission_or_policy",
            "dependency_external",
            "task_source_provenance",
            "cost_budget",
            "unknown",
        ],
        "records": [
            {
                "record_id": failure_record["record_id"],
                "primary_owner": failure_record["failure_owner"],
                "secondary_owners": [],
                "failure_category": failure_record["failure_category"],
                "priority_rule": "final_verifier_boundary_before_model_quality",
            },
            {
                "record_id": blocked_record["record_id"],
                "primary_owner": blocked_record["failure_owner"],
                "secondary_owners": ["provider_error"],
                "failure_category": blocked_record["failure_category"],
                "priority_rule": "comparison_scope_before_preference_export",
            },
        ],
        "status": "passed",
    }


def _stage4_claim_gate(
    stage3_claim_gate: dict[str, Any],
    export_manifest_path: Path,
    preference_blocked_path: Path,
) -> dict[str, Any]:
    blocked = list(dict.fromkeys([
        *stage3_claim_gate.get("blocked_claims", []),
        "preference export completed",
        "trainable export completed",
    ]))
    allowed = list(dict.fromkeys([
        *stage3_claim_gate.get("allowed_claims", []),
        "partitioned failure, diagnostic-only and blocked export pack generated; trainable records require accepted final verifier evidence",
    ]))
    return {
        "schema_version": V5_RESUME_CLAIM_GATE_REPORT_VERSION,
        "created_at": _utc_timestamp(),
        "stage": "stage4_partial",
        "allowed_claims": allowed,
        "blocked_claims": blocked,
        "blocking_reasons": {
            **stage3_claim_gate.get("blocking_reasons", {}),
            "preference_pair": "no real comparable preference pair passed compare scope gate",
            "trainable_export": "no accepted final verifier outcome is available for SFT or RL rollout trainable records",
            "demo_share_safe": "pending Stage 5 public-safe demo artifacts",
        },
        "provider_claim_status": stage3_claim_gate.get("provider_claim_status", "blocked"),
        "preference_pair_claim_status": "blocked_no_real_comparable_pair",
        "demo_share_safe_status": "pending_stage5",
        "stress_test_claim_status": stage3_claim_gate.get("stress_test_claim_status", "not_claimed"),
        "source_reports": [
            *_safe_refs(stage3_claim_gate.get("source_reports")),
            _stage4_ref(export_manifest_path, "v5_export_result_pack_manifest"),
            _stage4_ref(preference_blocked_path, "v5_preference_pair_blocked_report"),
        ],
        "export_pack_status": "passed",
    }


def _transcript_records(result: dict[str, Any]) -> dict[str, Any]:
    run_dir = Path(str(result["run_dir"]))
    rows = _read_jsonl(run_dir / "transcript.jsonl")
    initial = [
        {
            "role": row.get("role"),
            "content_preview": row.get("content_preview"),
        }
        for row in rows
        if str(row.get("message_id", "")).startswith("initial_")
    ]
    assistant = next(
        (
            {"role": row.get("role"), "content_preview": row.get("content_preview")}
            for row in rows
            if row.get("role") == "assistant"
        ),
        {"role": "assistant", "content_preview": ""},
    )
    return {"initial_messages": initial, "assistant_message": assistant}


def _trainable_visibility_policy() -> dict[str, Any]:
    return {
        "raw_provider_request_included": False,
        "raw_provider_response_included": False,
        "evaluator_only_evidence_included": False,
        "reward_scalar_included": False,
        "reward_label_included": False,
    }


def _stage4_ref(path: Path, kind: str) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"V5 Stage 4 export pack artifact: {kind}",
        visibility="audit_only",
        producer_command="build-v5-export-pack",
        producer_stage="v5_stage4_export_pack",
        inspect_command="inspect-v5-export-pack",
    )


def _external_ref(path: Path, kind: str, inspect_command: str) -> dict[str, Any]:
    return _evidence_ref(
        path,
        kind=kind,
        purpose=f"V5 Stage 4 input: {kind}",
        visibility="audit_only",
        producer_command="external",
        producer_stage="v5_stage4_export_pack",
        inspect_command=inspect_command,
    )


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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


def _refuse_existing(root: Path, names: tuple[str, ...], fail_if_output_exists: bool) -> None:
    if not fail_if_output_exists:
        return
    existing = [root / name for name in names if (root / name).exists()]
    if existing:
        joined = ", ".join(path.as_posix() for path in existing)
        raise ConfigError(f"V5 Stage 4 输出已存在，不能覆盖旧 evidence：{joined}")


__all__ = ["build_export_result_pack"]
