"""第二版训练导出审计和 training eligibility 映射。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.export.manifest import EXPORTER_VERSION, sha256_file
from repo_harness.export.schemas import (
    ExportAuditItem,
    ExportAuditReport,
    ExportAuditSample,
    ExportPolicy,
    ExportRecord,
    ExportRecordQuality,
    TrainingEligibility,
)
from repo_harness.run_metadata.reader import inspect_run_metadata
from repo_harness.schema_base import stable_hash
from repo_harness.trajectory import read_jsonl, verify_artifact_manifest

CRITICAL_AUDIT_ITEMS = {
    "artifact_manifest_valid",
    "artifact_refs_resolve",
    "tool_call_pairing_valid",
    "prepared_observation_source_valid",
    "loss_targets_valid",
    "formal_final_verifier_source_valid",
    "reward_metadata_present",
    "hidden_fields_absent",
    "hidden_test_feedback_not_visible",
    "local_paths_redacted",
    "provider_raw_response_not_target",
    "provider_reasoning_trace_policy_satisfied",
    "tool_schema_snapshot_valid",
    "preference_pairing_policy_satisfied",
    "compact_only_calls_not_trainable",
    "training_prompt_provider_projection_equivalent",
    "training_prompt_lean_context_fields_absent",
}

HIDDEN_MARKERS = (
    "gold_patch",
    "hidden_tests",
    "hidden_test",
    "fail_to_pass_tests",
    "pass_to_pass_tests",
    "baseline_raw_log",
    "baseline_stdout",
    "baseline_stderr",
    "expected_outcome",
    "reward_only",
    "reward scalar",
    "reward_scalar",
    "reward label",
    "reward_label",
    "accepted outcome",
    "accepted_outcome",
    "final_verifier_raw_output",
    "hidden test",
    "hidden_test_patch",
    "fail_to_pass_selectors",
    "pass_to_pass_selectors",
    "hidden_test_selector",
    "evaluator_only_selector",
    "evaluator-only artifact",
    "evaluator_only_artifact",
    "decontamination_metadata",
)

HIDDEN_FEEDBACK_MARKERS = (
    "fail_to_pass",
    "pass_to_pass",
    "hidden accepted",
    "hidden_accepted",
)

PROVIDER_RAW_MARKERS = (
    "raw_response",
    "raw_request",
    "raw_request_body",
    "reasoning_summary",
    "reasoning_content",
    "authorization",
)

PREFERENCE_PAIRING_METADATA_KEYS = {
    "pairing_policy_version",
    "compare_scope",
    "blocked_reasons",
    "source_run_ids",
}

LEAN_CONTEXT_BLOCKED_PROMPT_MARKERS = (
    "repository_action_index",
    "repository_action_index_full",
    "repository_context_index",
    "source_text_span_hash",
    "raw_provider_request_ref",
    "raw_provider_response_ref",
    "redaction_report",
    "authorization",
    "credential_policy",
    "provider_options",
    "tool_schema_snapshot_ref",
)

PROVIDER_VISIBLE_MESSAGE_KEYS = {"role", "content", "tool_call_id", "tool_calls"}
HARNESS_CONTROL_PROMPT_MARKERS = {
    "repo_harness_control_message": "harness_control_message",
    "convergence_nudge": "convergence_nudge",
    "context_warning": "context_warning",
}


@dataclass(frozen=True)
class AuditedExportRecord:
    record: ExportRecord
    audit_items: list[ExportAuditItem]
    artifact_refs: list[dict[str, Any]]
    source_metadata: dict[str, Any]


def audit_export_records(
    records: list[ExportRecord],
    *,
    run_paths: dict[str, Path],
    export_format: str,
    policy: ExportPolicy,
) -> list[AuditedExportRecord]:
    return [
        _audit_record(
            record,
            run_paths=_record_run_paths(record, run_paths),
            export_format=export_format,
            policy=policy,
        )
        for record in records
    ]


def build_audit_report(
    audited_records: list[AuditedExportRecord],
    *,
    export_id: str,
    export_format: str,
    source_run_dirs: list[str],
    data_file_relative_path: str | None,
    generated_at: str,
    line_numbers: dict[str, int],
    skipped_reason: str | None = None,
) -> ExportAuditReport:
    samples = [
        ExportAuditSample(
            sample_id=audited.record.sample_id,
            data_file=data_file_relative_path if audited.record.sample_id in line_numbers else None,
            line_number=line_numbers.get(audited.record.sample_id),
            run_id=audited.record.source_run_id,
            task_id=audited.record.task_id,
            training_eligibility=audited.record.quality.training_eligibility,
            filter_status=audited.record.filter_status,
            invalid_for_training=audited.record.invalid_for_training,
            invalid_reason=audited.record.invalid_reason,
            quality_reasons=audited.record.quality.quality_reasons,
            audit_items=audited.audit_items,
            artifact_refs=audited.artifact_refs,
            metadata_source=audited.source_metadata.get("metadata_source"),
            source_run_ids=audited.source_metadata.get("source_run_ids", []),
        )
        for audited in audited_records
    ]
    summary = _summary(samples, skipped_reason=skipped_reason)
    return ExportAuditReport(
        export_id=export_id,
        format=export_format,  # type: ignore[arg-type]
        status=_report_status(samples, skipped_reason=skipped_reason),
        source_run_dirs=source_run_dirs,
        data_files=[data_file_relative_path] if data_file_relative_path else [],
        generated_at=generated_at,
        exporter_version=EXPORTER_VERSION,
        summary=summary,
        samples=samples,
    )


def render_audit_markdown(report: ExportAuditReport) -> str:
    summary = report.summary
    lines = [
        f"# Export Audit: {report.export_id}",
        "",
        f"- Format: `{report.format}`",
        f"- Status: `{report.status}`",
        f"- Total samples: {summary.get('total_samples', 0)}",
        f"- Trainable: {summary.get('trainable_count', 0)}",
        f"- Diagnostic-only: {summary.get('diagnostic_only_count', 0)}",
        f"- Skipped: {summary.get('skipped_count', 0)}",
        f"- Invalid: {summary.get('invalid_count', 0)}",
        f"- Data files: {', '.join(report.data_files) if report.data_files else 'none'}",
        "- JSON audit report: `audit_report.json`",
        "",
        "## Eligibility Distribution",
        "",
    ]
    distribution = summary.get("training_eligibility_distribution", {})
    for name in ("trainable", "diagnostic_only", "skipped", "invalid"):
        lines.append(f"- {name}: {distribution.get(name, 0)}")
    failed_distribution = summary.get("failed_audit_item_distribution", {})
    lines.extend(["", "## Failed Audit Items", ""])
    if failed_distribution:
        for name, count in sorted(failed_distribution.items()):
            lines.append(f"- {name}: {count}")
    else:
        lines.append("- none")
    quality_reasons = summary.get("top_quality_reasons", {})
    lines.extend(["", "## Quality Reasons", ""])
    if quality_reasons:
        for reason, count in sorted(quality_reasons.items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")
    if summary.get("skipped_reason"):
        lines.extend(["", "## Skipped Reason", "", f"- {summary['skipped_reason']}"])
    return "\n".join(lines) + "\n"


def _audit_record(
    record: ExportRecord,
    *,
    run_paths: list[Path],
    export_format: str,
    policy: ExportPolicy,
) -> AuditedExportRecord:
    items: list[ExportAuditItem] = []
    diagnostic_reasons: list[str] = []
    skipped_reasons: list[str] = []
    artifact_refs = _collect_artifact_refs(record.model_dump(mode="json"))
    metadata_inspections = [inspect_run_metadata(run_path) for run_path in run_paths]
    source_metadata = {
        "metadata_source": _combined_metadata_source(metadata_inspections),
        "source_run_ids": [run_path.name for run_path in run_paths],
    }
    run_skipped_reason = _run_skipped_reason(run_paths)
    if run_skipped_reason:
        skipped_reasons.append(run_skipped_reason)

    artifact_errors = _all_artifact_errors(run_paths)
    if not run_paths:
        items.append(_item("artifact_manifest_valid", "skipped", "warning", "source run directory not available"))
    elif artifact_errors:
        items.append(_item("artifact_manifest_valid", "failed", "error", artifact_errors[0]))
    else:
        items.append(_item("artifact_manifest_valid", "passed", "info", "artifact manifest is valid"))

    unresolved_refs = _unresolved_artifact_refs(run_paths, artifact_refs)
    if unresolved_refs:
        items.append(_item("artifact_refs_resolve", "failed", "error", unresolved_refs[0]))
    else:
        items.append(_item("artifact_refs_resolve", "passed", "info", "artifact refs resolve"))

    tool_pairing_error = _tool_pairing_error(run_paths)
    if tool_pairing_error:
        items.append(_item("tool_call_pairing_valid", "failed", "error", tool_pairing_error))
    else:
        items.append(_item("tool_call_pairing_valid", "passed", "info", "tool calls have terminal results"))

    prepared_error = _prepared_observation_error(record, export_format, run_paths=run_paths)
    if prepared_error:
        items.append(_item("prepared_observation_source_valid", "failed", "error", prepared_error))
    else:
        items.append(_item("prepared_observation_source_valid", "passed", "info", "observations come from prepared messages"))

    projection_error = _training_prompt_projection_error(record, export_format)
    if projection_error:
        items.append(
            _item(
                "training_prompt_provider_projection_equivalent",
                "failed",
                "error",
                projection_error,
            )
        )
    else:
        items.append(
            _item(
                "training_prompt_provider_projection_equivalent",
                "passed",
                "info",
                "trainable prompt messages match the provider-visible projection",
            )
        )

    lean_prompt_error = _lean_context_prompt_error(record, export_format)
    if lean_prompt_error:
        items.append(
            _item(
                "training_prompt_lean_context_fields_absent",
                "failed",
                "error",
                lean_prompt_error,
            )
        )
    else:
        items.append(
            _item(
                "training_prompt_lean_context_fields_absent",
                "passed",
                "info",
                "lean-context forbidden fields are absent from trainable prompts",
            )
        )

    control_prompt_counts = _harness_control_prompt_context_counts(record, export_format)
    if control_prompt_counts["total"] > 0:
        items.append(
            _item(
                "training_prompt_harness_control_context_labeled",
                "warning",
                "warning",
                (
                    "trainable prompt contains harness control context; sample is policy-conditioned "
                    f"rather than a plain user-only prompt: {control_prompt_counts}"
                ),
            )
        )
    else:
        items.append(
            _item(
                "training_prompt_harness_control_context_labeled",
                "passed",
                "info",
                "trainable prompt does not contain harness control messages",
            )
        )

    loss_error = _loss_target_error(record, export_format)
    if loss_error:
        items.append(_item("loss_targets_valid", "failed", "error", loss_error))
    else:
        items.append(_item("loss_targets_valid", "passed", "info", "loss targets cover assistant actions only"))

    terminal_quality_reasons = _record_export_quality_diagnostic_reasons(record)
    if terminal_quality_reasons:
        diagnostic_reasons.extend(terminal_quality_reasons)
        items.append(
            _item(
                "trajectory_terminal_quality",
                "warning",
                "warning",
                ", ".join(terminal_quality_reasons),
            )
        )
    else:
        items.append(_item("trajectory_terminal_quality", "passed", "info", "terminal trajectory quality is trainable"))

    formal_reason = None if run_skipped_reason else _formal_final_verifier_invalid_reason(run_paths)
    if run_skipped_reason:
        items.append(_item("formal_final_verifier_source_valid", "skipped", "info", run_skipped_reason))
    elif formal_reason:
        items.append(_item("formal_final_verifier_source_valid", "failed", "error", formal_reason))
    else:
        items.append(_item("formal_final_verifier_source_valid", "passed", "info", "formal final verifier is strict patch replay"))

    reward_reason = None if run_skipped_reason else _reward_metadata_missing_reason(run_paths)
    if run_skipped_reason:
        items.append(_item("reward_metadata_present", "skipped", "info", run_skipped_reason))
    elif reward_reason:
        items.append(_item("reward_metadata_present", "failed", "error", reward_reason))
    else:
        items.append(_item("reward_metadata_present", "passed", "info", "reward metadata is present"))

    payload_text = json.dumps(
        {"payload": record.payload, "metadata": record.metadata},
        ensure_ascii=False,
        sort_keys=True,
    )
    hidden_reason = _marker_reason(payload_text, HIDDEN_MARKERS)
    if hidden_reason:
        items.append(_item("hidden_fields_absent", "failed", "error", hidden_reason))
    else:
        items.append(_item("hidden_fields_absent", "passed", "info", "hidden fields are absent"))

    local_path_reason = _local_path_reason(payload_text)
    if local_path_reason:
        items.append(_item("local_paths_redacted", "failed", "error", local_path_reason))
    else:
        items.append(_item("local_paths_redacted", "passed", "info", "local paths are absent"))

    provider_raw_reason = _provider_raw_marker_reason(
        payload_text,
        export_format=export_format,
        policy=policy,
    )
    if provider_raw_reason:
        items.append(_item("provider_raw_response_not_target", "failed", "error", provider_raw_reason))
    else:
        items.append(_item("provider_raw_response_not_target", "passed", "info", "provider raw payload is absent"))

    reasoning_trace_reason = _provider_reasoning_trace_policy_reason(
        record,
        export_format=export_format,
        policy=policy,
    )
    if reasoning_trace_reason:
        items.append(
            _item(
                "provider_reasoning_trace_policy_satisfied",
                "failed",
                "error",
                reasoning_trace_reason,
            )
        )
    elif export_format == "provider_reasoning_trace_training_export":
        items.append(
            _item(
                "provider_reasoning_trace_policy_satisfied",
                "passed",
                "info",
                "provider reasoning trace export is explicitly allowed and isolated",
            )
        )

    pairing_reason = _preference_pairing_reason(record, export_format)
    if pairing_reason:
        items.append(_item("preference_pairing_policy_satisfied", "failed", "error", pairing_reason))
    elif export_format == "preference_jsonl":
        items.append(
            _item(
                "preference_pairing_policy_satisfied",
                "passed",
                "info",
                "preference pair satisfies pairing policy",
            )
        )

    feedback_policy = _feedback_policy(run_paths)
    hidden_feedback_reason = _marker_reason(payload_text, HIDDEN_FEEDBACK_MARKERS)
    if feedback_policy != "oracle_hidden_feedback" and hidden_feedback_reason:
        items.append(_item("hidden_test_feedback_not_visible", "failed", "error", hidden_feedback_reason))
    else:
        items.append(_item("hidden_test_feedback_not_visible", "passed", "info", "hidden test feedback policy is respected"))

    if feedback_policy == "oracle_hidden_feedback":
        oracle_label_reason = _oracle_label_reason(run_paths)
        if oracle_label_reason:
            items.append(_item("oracle_feedback_labeled", "failed", "error", oracle_label_reason))
        else:
            items.append(_item("oracle_feedback_labeled", "passed", "info", "oracle feedback is labeled"))
        if policy.allow_oracle_feedback_training:
            items.append(_item("oracle_feedback_training_allowed", "passed", "info", "export policy explicitly allows oracle feedback training"))
        else:
            items.append(_item("oracle_feedback_training_allowed", "warning", "warning", "oracle feedback defaults to diagnostic_only"))
            diagnostic_reasons.append("oracle_hidden_feedback_diagnostic_only")
    else:
        items.append(_item("oracle_feedback_labeled", "skipped", "info", "not oracle hidden feedback"))
        items.append(_item("oracle_feedback_training_allowed", "skipped", "info", "not oracle hidden feedback"))

    compact_pollution_reason = _compact_only_training_pollution_reason(run_paths)
    if compact_pollution_reason:
        items.append(
            _item(
                "compact_only_calls_not_trainable",
                "failed",
                "error",
                compact_pollution_reason,
            )
        )
    else:
        items.append(
            _item(
                "compact_only_calls_not_trainable",
                "passed",
                "info",
                "compact-only calls are audit-only and absent from trainable transcript",
            )
        )

    for metadata_inspection in metadata_inspections:
        if metadata_inspection.run_metadata_status == "legacy_missing":
            diagnostic_reasons.append("legacy_metadata_inferred")
        elif metadata_inspection.run_metadata_status in {"missing", "invalid"}:
            diagnostic_reasons.append(f"run_metadata_{metadata_inspection.run_metadata_status}")
        if metadata_inspection.tool_schema_snapshot_status == "missing":
            diagnostic_reasons.append("tool_schema_snapshot_missing")
        elif metadata_inspection.tool_schema_snapshot_status == "invalid":
            items.append(_item("tool_schema_snapshot_valid", "failed", "error", "tool schema snapshot is invalid"))
    eligibility, reason, quality_reasons = _training_eligibility(
        items,
        diagnostic_reasons=diagnostic_reasons,
        skipped_reasons=skipped_reasons,
        original_record=record,
    )
    updated_record = _record_with_quality(record, eligibility=eligibility, reason=reason, quality_reasons=quality_reasons)
    return AuditedExportRecord(
        record=updated_record,
        audit_items=items,
        artifact_refs=artifact_refs,
        source_metadata=source_metadata,
    )


def _training_eligibility(
    items: list[ExportAuditItem],
    *,
    diagnostic_reasons: list[str],
    skipped_reasons: list[str],
    original_record: ExportRecord,
) -> tuple[TrainingEligibility, str | None, list[str]]:
    failed_critical = [
        item
        for item in items
        if item.status == "failed" and item.name in CRITICAL_AUDIT_ITEMS
    ]
    if failed_critical:
        reason = original_record.invalid_reason or failed_critical[0].reason
        return "invalid", reason, sorted(set([reason, *(item.name for item in failed_critical)]))
    if skipped_reasons:
        return "skipped", skipped_reasons[0], sorted(set(skipped_reasons))
    if original_record.invalid_for_training and original_record.invalid_reason:
        if original_record.invalid_reason in {"invalid_task", "flaky_task", "interrupted", "inconclusive"}:
            return "skipped", original_record.invalid_reason, [original_record.invalid_reason]
        return "invalid", original_record.invalid_reason, [original_record.invalid_reason]
    warning_diagnostics = [
        item.name
        for item in items
        if item.name == "oracle_feedback_training_allowed" and item.status == "warning"
    ]
    reasons = sorted(set([*diagnostic_reasons, *warning_diagnostics]))
    if reasons:
        reason = diagnostic_reasons[0] if diagnostic_reasons else reasons[0]
        return "diagnostic_only", reason, reasons
    return "trainable", None, []


def _record_with_quality(
    record: ExportRecord,
    *,
    eligibility: TrainingEligibility,
    reason: str | None,
    quality_reasons: list[str],
) -> ExportRecord:
    filter_status = "included" if eligibility == "trainable" else "filtered"
    if eligibility == "skipped":
        filter_status = "skipped"
    quality = ExportRecordQuality(
        training_eligibility=eligibility,
        quality_reasons=quality_reasons,
        artifact_manifest_status="ok",
        tool_pairing_status="ok",
        redaction_status="passed",
        reward_source=(
            "formal_final_verifier"
            if eligibility == "trainable" or "formal_final_verifier_source_valid" not in quality_reasons
            else "invalid"
        ),
    )
    payload = record.model_dump(mode="json")
    payload.update(
        {
            "quality": quality.model_dump(mode="json"),
            "filter_status": filter_status,
            "invalid_for_training": eligibility != "trainable",
            "invalid_reason": reason,
        }
    )
    return ExportRecord.model_validate(payload)


def _summary(samples: list[ExportAuditSample], *, skipped_reason: str | None) -> dict[str, Any]:
    distribution = {name: 0 for name in ("trainable", "diagnostic_only", "skipped", "invalid")}
    failed_distribution: dict[str, int] = {}
    quality_reasons: dict[str, int] = {}
    for sample in samples:
        distribution[sample.training_eligibility] += 1
        for item in sample.audit_items:
            if item.status == "failed":
                failed_distribution[item.name] = failed_distribution.get(item.name, 0) + 1
        for reason in sample.quality_reasons:
            quality_reasons[reason] = quality_reasons.get(reason, 0) + 1
    return {
        "total_samples": len(samples),
        "trainable_count": distribution["trainable"],
        "diagnostic_only_count": distribution["diagnostic_only"],
        "skipped_count": distribution["skipped"],
        "invalid_count": distribution["invalid"],
        "training_eligibility_distribution": distribution,
        "failed_audit_item_distribution": failed_distribution,
        "top_quality_reasons": quality_reasons,
        "skipped_reason": skipped_reason,
    }


def _report_status(samples: list[ExportAuditSample], *, skipped_reason: str | None) -> str:
    if skipped_reason and not samples:
        return "skipped"
    if any(sample.training_eligibility == "invalid" for sample in samples):
        return "failed"
    if any(sample.training_eligibility in {"diagnostic_only", "skipped"} for sample in samples):
        return "passed_with_warnings"
    return "passed"


def _item(name: str, status: str, severity: str, reason: str) -> ExportAuditItem:
    return ExportAuditItem(
        name=name,
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        reason=reason,
    )


def _record_run_paths(record: ExportRecord, run_paths_by_id: dict[str, Path]) -> list[Path]:
    source_run_ids = record.metadata.get("source_run_ids")
    if isinstance(source_run_ids, list):
        return [
            run_paths_by_id[run_id]
            for run_id in source_run_ids
            if isinstance(run_id, str) and run_id in run_paths_by_id
        ]
    run_path = run_paths_by_id.get(record.source_run_id)
    return [run_path] if run_path is not None else []


def _combined_metadata_source(metadata_inspections: list[Any]) -> str | None:
    if not metadata_inspections:
        return None
    sources = {inspection.metadata_source for inspection in metadata_inspections}
    if len(sources) == 1:
        return next(iter(sources))
    return "mixed"


def _all_artifact_errors(run_paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for run_path in run_paths:
        errors.extend(f"{run_path.name}: {error}" for error in verify_artifact_manifest(run_path))
    return errors


def _formal_final_verifier_invalid_reason(run_paths: list[Path]) -> str | None:
    if not run_paths:
        return None
    for run_path in run_paths:
        reason = _formal_final_verifier_invalid_reason_for_run(run_path)
        if reason:
            return f"{run_path.name}: {reason}"
    return None


def _formal_final_verifier_invalid_reason_for_run(run_path: Path) -> str | None:
    verifier = _read_json_if_exists(run_path / "verifier.json")
    reward = _read_json_if_exists(run_path / "reward.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    final_mode = metrics.get("interaction_efficiency", {}).get("final_verifier_mode")
    if not verifier:
        return "missing_formal_final_verifier"
    if verifier.get("verifier_stage") != "final":
        return "non_final_verifier_reward_source"
    if final_mode != "strict_patch_replay":
        return "non_strict_patch_replay_reward_source"
    if not reward:
        return "missing_reward_metadata"
    return None


def _reward_metadata_missing_reason(run_paths: list[Path]) -> str | None:
    for run_path in run_paths:
        if not (run_path / "reward.json").exists():
            return f"{run_path.name}: missing_reward_metadata"
    return None


def _run_skipped_reason(run_paths: list[Path]) -> str | None:
    for run_path in run_paths:
        metrics = _read_json_if_exists(run_path / "metrics.json")
        baseline = _read_json_if_exists(run_path / "baseline.json")
        if baseline.get("status") in {"invalid", "flaky"}:
            return f"{run_path.name}: baseline_{baseline['status']}"
        outcome = metrics.get("run_outcome")
        if outcome in {"invalid_task", "flaky_task", "interrupted", "inconclusive"}:
            return f"{run_path.name}: {outcome}"
    return None


def _tool_pairing_error(run_paths: list[Path]) -> str | None:
    for run_path in run_paths:
        if not (run_path / "events.jsonl").exists():
            continue
        events = read_jsonl(run_path / "events.jsonl")
        requested = {
            event.get("data", {}).get("tool_call_id")
            for event in events
            if event.get("event_type") == "tool_requested"
        }
        terminal = {
            event.get("data", {}).get("tool_call_id")
            for event in events
            if event.get("event_type")
            in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
        }
        missing = sorted(str(call_id) for call_id in requested if call_id and call_id not in terminal)
        if missing:
            return f"{run_path.name}: tool calls without terminal result: {', '.join(missing)}"
    return None


def _prepared_observation_error(
    record: ExportRecord,
    export_format: str,
    *,
    run_paths: list[Path],
) -> str | None:
    binding_error = _v3_binding_error(record, run_paths=run_paths)
    if binding_error:
        return binding_error
    if export_format == "sft_jsonl":
        audit_bindings = record.payload.get("prompt_message_audit_bindings", [])
        if not isinstance(audit_bindings, list):
            audit_bindings = []
        audit_by_index = {
            binding.get("message_index"): binding
            for binding in audit_bindings
            if isinstance(binding, dict)
        }
        for index, message in enumerate(record.payload.get("messages", [])):
            if not isinstance(message, dict) or message.get("role") != "tool":
                continue
            binding = audit_by_index.get(index)
            if not isinstance(binding, dict):
                return "tool observation is missing prompt_message_audit_bindings entry"
            if binding.get("observation_source") != "prepared_messages":
                return "tool observation does not come from prepared_messages"
            missing = _missing_v3_observation_fields(binding)
            if missing:
                return f"tool observation missing V3 binding fields: {', '.join(missing)}"
            source_error = _prepared_binding_source_error(
                binding,
                run_paths=run_paths,
                expected_content=message.get("content"),
                tool_call_id=message.get("tool_call_id"),
            )
            if source_error:
                return source_error
    if export_format == "rl_jsonl":
        for step in record.payload.get("trajectory", []):
            observation = step.get("observation", {})
            if "preview" in observation and observation.get("observation_source") != "prepared_messages":
                return "trajectory observation preview does not come from prepared_messages"
            if observation.get("observation_source") == "prepared_messages":
                missing = _missing_v3_observation_fields(observation)
                if missing:
                    return f"trajectory observation missing V3 binding fields: {', '.join(missing)}"
                source_error = _prepared_binding_source_error(
                    observation,
                    run_paths=run_paths,
                    expected_content=observation.get("preview"),
                    tool_call_id=step.get("action", {}).get("tool_call_id"),
                )
                if source_error:
                    return source_error
    return None


def _training_prompt_projection_error(
    record: ExportRecord,
    export_format: str,
) -> str | None:
    if export_format not in {"sft_jsonl", "rl_jsonl"}:
        return None
    prompt_messages = _training_prompt_messages(record, export_format)
    message_key_error = _provider_visible_message_key_error(prompt_messages)
    if message_key_error:
        return message_key_error
    source = record.payload.get("training_sample_source")
    if source != "model_input_snapshot":
        return None
    equivalence = _prompt_equivalence_report(record, export_format)
    if not isinstance(equivalence, dict):
        return "model_input_snapshot export is missing provider_visible_prompt_equivalence"
    if equivalence.get("export_prompt_body_equivalent") is not True:
        return "export prompt projection does not match provider-visible message projection"
    if equivalence.get("prepared_messages_body_equivalent") is False:
        return "prepared_messages projection does not match provider body messages"
    expected_count = equivalence.get("export_prompt_message_count")
    if isinstance(expected_count, int) and len(prompt_messages) != expected_count:
        return "export prompt message count does not match equivalence report"
    actual_hash = stable_hash(_training_message_projection(prompt_messages))
    if actual_hash != equivalence.get("export_prompt_projection_hash"):
        return "export prompt projection hash does not match payload messages"
    return None


def _lean_context_prompt_error(record: ExportRecord, export_format: str) -> str | None:
    if export_format not in {"sft_jsonl", "rl_jsonl", "preference_jsonl"}:
        return None
    prompt_text = json.dumps(
        _training_message_projection(_training_prompt_messages(record, export_format)),
        ensure_ascii=False,
        sort_keys=True,
    )
    lowered = prompt_text.lower()
    for marker in LEAN_CONTEXT_BLOCKED_PROMPT_MARKERS:
        if marker.lower() in lowered:
            return f"trainable prompt contains blocked field {marker}"
    return None


def _prompt_equivalence_report(record: ExportRecord, export_format: str) -> Any:
    if export_format == "sft_jsonl":
        return record.payload.get("provider_visible_prompt_equivalence")
    if export_format == "rl_jsonl":
        prompt = record.payload.get("prompt", {})
        if isinstance(prompt, dict):
            return (
                prompt.get("provider_visible_prompt_equivalence")
                or record.payload.get("provider_visible_prompt_equivalence")
            )
    return None


def _training_prompt_messages(record: ExportRecord, export_format: str) -> list[dict[str, Any]]:
    if export_format == "sft_jsonl":
        messages = record.payload.get("messages", [])
        if not isinstance(messages, list):
            return []
        loss_mask = record.payload.get("loss_mask", [])
        if isinstance(loss_mask, list) and len(loss_mask) == len(messages):
            return [
                message
                for message, loss in zip(messages, loss_mask)
                if isinstance(message, dict) and not loss
            ]
        return [message for message in messages if isinstance(message, dict)]
    if export_format == "rl_jsonl":
        prompt = record.payload.get("prompt", {})
        if not isinstance(prompt, dict):
            return []
        messages = prompt.get("messages", [])
        return [message for message in messages if isinstance(message, dict)] if isinstance(messages, list) else []
    return []


def _training_message_projection(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for message in messages:
        item = {
            "role": message.get("role"),
            "content": message.get("content"),
            "tool_call_id": message.get("tool_call_id"),
            "tool_calls": message.get("tool_calls"),
        }
        projected.append({key: value for key, value in item.items() if value is not None})
    return projected


def _harness_control_prompt_context_counts(
    record: ExportRecord,
    export_format: str,
) -> dict[str, int]:
    counts = {"total": 0, "harness_control_message": 0, "convergence_nudge": 0, "context_warning": 0}
    for message in _training_prompt_messages(record, export_format):
        text = json.dumps(message, ensure_ascii=False, sort_keys=True)
        matched = False
        for marker, count_key in HARNESS_CONTROL_PROMPT_MARKERS.items():
            if marker in text:
                counts[count_key] += 1
                matched = True
        if matched:
            counts["total"] += 1
    return counts


def _provider_visible_message_key_error(messages: list[dict[str, Any]]) -> str | None:
    for index, message in enumerate(messages):
        extra = sorted(set(message) - PROVIDER_VISIBLE_MESSAGE_KEYS)
        if extra:
            return (
                "export prompt message contains provider-invisible audit keys "
                f"at index {index}: {', '.join(extra)}"
            )
    return None


def _v3_binding_error(record: ExportRecord, *, run_paths: list[Path]) -> str | None:
    bindings = record.payload.get("v3_observation_bindings", [])
    if bindings is None:
        bindings = []
    if not isinstance(bindings, list):
        return "v3_observation_bindings must be a list"
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            return f"v3_observation_bindings[{index}] is not an object"
        missing = _missing_v3_observation_fields(binding)
        if missing:
            return f"v3_observation_bindings[{index}] missing: {', '.join(missing)}"
        if binding.get("observation_matches_prepared_messages") is not True:
            return f"v3_observation_bindings[{index}] observation does not match prepared messages"
        source_error = _prepared_binding_source_error(
            binding,
            run_paths=run_paths,
            expected_content=None,
            tool_call_id=binding.get("tool_call_id"),
        )
        if source_error:
            return f"v3_observation_bindings[{index}] {source_error}"
    return None


def _prepared_binding_source_error(
    binding: dict[str, Any],
    *,
    run_paths: list[Path],
    expected_content: Any,
    tool_call_id: Any,
) -> str | None:
    ref = binding.get("prepared_messages_ref")
    if not isinstance(ref, dict):
        return "prepared_messages_ref is not an object"
    run_path = _run_path_for_ref(run_paths, ref)
    if run_path is None:
        return "prepared_messages_ref source_run_id is unknown"
    relative_path = Path(str(ref.get("relative_path", "")))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return "prepared_messages_ref has unsafe relative_path"
    prepared_path = run_path / relative_path
    if not prepared_path.exists():
        return "prepared_messages_ref does not exist"
    actual_sha = sha256_file(prepared_path)
    expected_sha = binding.get("prepared_messages_sha256")
    if expected_sha != actual_sha:
        return "prepared_messages_sha256 does not match prepared_messages_ref"
    if ref.get("sha256") and ref.get("sha256") != actual_sha:
        return "prepared_messages_ref sha256 does not match file"
    try:
        payload = json.loads(prepared_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "prepared_messages_ref is not valid JSON"
    if payload.get("model_input_hash") != binding.get("model_input_hash"):
        return "model_input_hash does not match prepared_messages artifact"
    if payload.get("context_revision") != binding.get("context_revision"):
        return "context_revision does not match prepared_messages artifact"
    if payload.get("content_replacement_state_ref") != binding.get("content_replacement_state_ref"):
        return "content_replacement_state_ref does not match prepared_messages artifact"
    tool_message = _prepared_tool_message(payload, str(tool_call_id or binding.get("tool_call_id") or ""))
    if tool_message is None:
        return "prepared_messages artifact does not contain matching tool_call_id"
    if expected_content is not None and tool_message.get("content") != expected_content:
        return "tool observation content does not match prepared_messages artifact"
    tool_observation_ref = binding.get("tool_observation_ref")
    if (
        isinstance(tool_observation_ref, dict)
        and tool_observation_ref.get("kind") == "trajectory_event"
        and tool_observation_ref.get("event_id") != binding.get("observation_source_event_ref")
    ):
        return "tool_observation_ref event_id does not match observation_source_event_ref"
    if not _tool_observation_ref_matches(tool_observation_ref, tool_message):
        return "tool_observation_ref does not match prepared_messages artifact"
    event_error = _tool_event_source_error(
        run_path,
        event_id=binding.get("observation_source_event_ref"),
        tool_call_id=str(tool_call_id or binding.get("tool_call_id") or ""),
    )
    if event_error:
        return event_error
    return None


def _run_path_for_ref(run_paths: list[Path], ref: dict[str, Any]) -> Path | None:
    source_run_id = ref.get("source_run_id")
    if isinstance(source_run_id, str):
        return {run_path.name: run_path for run_path in run_paths}.get(source_run_id)
    if len(run_paths) == 1:
        return run_paths[0]
    return None


def _prepared_tool_message(payload: dict[str, Any], tool_call_id: str) -> dict[str, Any] | None:
    for message in payload.get("messages", []):
        if message.get("role") == "tool" and str(message.get("tool_call_id") or "") == tool_call_id:
            return message
    return None


def _tool_observation_ref_matches(ref: Any, tool_message: dict[str, Any]) -> bool:
    if not isinstance(ref, dict):
        return False
    if ref.get("kind") == "trajectory_event" and ref.get("event_id"):
        return True
    artifact_refs = tool_message.get("artifact_refs", [])
    if not isinstance(artifact_refs, list):
        return False
    return any(
        isinstance(artifact_ref, dict)
        and artifact_ref.get("artifact_id") == ref.get("artifact_id")
        and artifact_ref.get("sha256") == ref.get("sha256")
        for artifact_ref in artifact_refs
    )


def _tool_event_source_error(run_path: Path, *, event_id: Any, tool_call_id: str) -> str | None:
    if not isinstance(event_id, str) or not event_id:
        return "observation_source_event_ref is missing"
    for event in read_jsonl(run_path / "events.jsonl"):
        if event.get("event_id") != event_id:
            continue
        if event.get("event_type") not in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}:
            return "observation_source_event_ref is not a terminal tool event"
        if str(event.get("data", {}).get("tool_call_id") or "") != tool_call_id:
            return "observation_source_event_ref tool_call_id mismatch"
        return None
    return "observation_source_event_ref does not exist"


def _missing_v3_observation_fields(value: dict[str, Any]) -> list[str]:
    required = [
        "prepared_messages_ref",
        "prepared_messages_sha256",
        "model_input_hash",
        "context_revision",
        "content_replacement_state_ref",
        "tool_observation_ref",
        "observation_source_event_ref",
        "observation_matches_prepared_messages",
    ]
    missing = []
    for field in required:
        field_value = value.get(field)
        if field_value is None or field_value == "":
            missing.append(field)
    return missing


def _loss_target_error(record: ExportRecord, export_format: str) -> str | None:
    if export_format == "provider_reasoning_trace_training_export":
        targets = record.payload.get("reasoning_trace_targets")
        if not isinstance(targets, list) or not targets:
            return "provider reasoning trace export missing reasoning_trace_targets"
        for index, item in enumerate(targets):
            if not isinstance(item, dict):
                return f"reasoning_trace_targets[{index}] is not an object"
            target = item.get("target")
            if not isinstance(target, dict):
                return f"reasoning_trace_targets[{index}].target is missing"
            if target.get("type") != "provider_reasoning_trace":
                return f"reasoning_trace_targets[{index}] target type mismatch"
            if not isinstance(target.get("reasoning_content"), str) or not target.get("reasoning_content"):
                return f"reasoning_trace_targets[{index}] missing reasoning_content target"
        return None
    if export_format != "sft_jsonl":
        return None
    messages = record.payload.get("messages", [])
    loss_mask = record.payload.get("loss_mask", [])
    observation_mask = record.payload.get("observation_mask", [])
    if len(messages) != len(loss_mask) or len(messages) != len(observation_mask):
        return "loss or observation mask length does not match messages"
    for index, loss in enumerate(loss_mask):
        if not loss:
            continue
        role = messages[index].get("role")
        if role != "assistant":
            return f"loss target covers non-assistant message at index {index}"
        if observation_mask[index]:
            return f"loss target covers tool observation at index {index}"
    return None


def _record_export_quality_diagnostic_reasons(record: ExportRecord) -> list[str]:
    reasons = record.metadata.get("export_quality_diagnostic_reasons", [])
    if not isinstance(reasons, list):
        return []
    return sorted({str(reason) for reason in reasons if reason})


def _feedback_policy(run_paths: list[Path]) -> str | None:
    if not run_paths:
        return None
    policies = []
    for run_path in run_paths:
        facts = _read_json_if_exists(run_path / "run_config_facts.json")
        policy = facts.get("test_feedback_policy")
        if isinstance(policy, str):
            policies.append(policy)
    if len(set(policies)) > 1:
        return "mixed"
    return policies[0] if policies else None


def _oracle_label_reason(run_paths: list[Path]) -> str | None:
    if not run_paths:
        return "missing_run_config_facts"
    for run_path in run_paths:
        reason = _oracle_label_reason_for_run(run_path)
        if reason:
            return f"{run_path.name}: {reason}"
    return None


def _oracle_label_reason_for_run(run_path: Path) -> str | None:
    facts = _read_json_if_exists(run_path / "run_config_facts.json")
    if facts.get("test_feedback_policy") != "oracle_hidden_feedback":
        return "not_oracle_hidden_feedback"
    if facts.get("hidden_feedback_visible_to_model") is not True:
        return "oracle_hidden_feedback_not_labeled_visible"
    if facts.get("swe_bench_like_final_only") is True:
        return "oracle_hidden_feedback_on_swe_bench_like_final_only"
    return None


def _compact_only_training_pollution_reason(run_paths: list[Path]) -> str | None:
    for run_path in run_paths:
        compact_model_call_ids = _compact_model_call_ids_for_run(run_path)
        if not compact_model_call_ids:
            continue
        for event in read_jsonl(run_path / "events.jsonl"):
            if event.get("event_type") != "model_input_accepted":
                continue
            model_call_id = str(event.get("data", {}).get("model_call_id") or "")
            if model_call_id in compact_model_call_ids:
                return f"{run_path.name}: compact-only model call {model_call_id} was accepted as main model input"
        for artifact in _artifact_manifest_refs(run_path, kind="model_input_snapshot"):
            payload = _artifact_payload(run_path, artifact)
            model_call_id = str(payload.get("model_call_id") or "")
            if model_call_id in compact_model_call_ids and payload.get("trainable") is not False:
                return f"{run_path.name}: compact-only model call {model_call_id} has trainable model_input_snapshot"
        for index, record in enumerate(read_jsonl(run_path / "transcript.jsonl")):
            model_call_id = str(record.get("model_call_id") or "")
            if model_call_id not in compact_model_call_ids:
                continue
            if record.get("role") == "assistant" or record.get("model_visible") is True:
                return (
                    f"{run_path.name}: transcript[{index}] contains compact-only "
                    f"model call {model_call_id} as ordinary model-visible action"
                )
            if record.get("trainable") is not False:
                return (
                    f"{run_path.name}: transcript[{index}] contains compact-only "
                    f"model call {model_call_id} without trainable=false"
                )
    return None


def _compact_model_call_ids_for_run(run_path: Path) -> set[str]:
    ids: set[str] = set()
    for event in read_jsonl(run_path / "events.jsonl"):
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event.get("event_type") == "auto_compact_model_call_started":
            model_call_id = data.get("model_call_id")
            if isinstance(model_call_id, str) and model_call_id:
                ids.add(model_call_id)
        if event.get("event_type") not in {"auto_compact_applied", "reactive_compact_applied"}:
            continue
        record_ref = _event_artifact_ref(event, "auto_compact_record")
        record = _artifact_payload(run_path, record_ref)
        model_call = _artifact_payload(run_path, record.get("compact_model_call_ref"))
        model_call_id = model_call.get("model_call_id")
        if isinstance(model_call_id, str) and model_call_id:
            ids.add(model_call_id)
    return ids


def _event_artifact_ref(event: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for ref in event.get("artifact_refs", []) or []:
        if isinstance(ref, dict) and ref.get("kind") == kind:
            return ref
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    for value in data.values():
        if isinstance(value, dict) and value.get("kind") == kind:
            return value
    return None


def _artifact_manifest_refs(run_path: Path, *, kind: str) -> list[dict[str, Any]]:
    manifest = _read_json_if_exists(run_path / "artifacts.json")
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict) and artifact.get("kind") == kind
    ]


def _artifact_payload(run_path: Path, ref: Any) -> dict[str, Any]:
    if not isinstance(ref, dict):
        return {}
    relative_path = ref.get("relative_path")
    if not isinstance(relative_path, str) or not relative_path:
        return {}
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        return {}
    return _read_json_if_exists(run_path / path)


def _collect_artifact_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("artifact_id"), str) and isinstance(value.get("relative_path"), str):
            refs.append(value)
        for nested in value.values():
            refs.extend(_collect_artifact_refs(nested))
    elif isinstance(value, list):
        for nested in value:
            refs.extend(_collect_artifact_refs(nested))
    return refs


def _unresolved_artifact_refs(run_paths: list[Path], refs: list[dict[str, Any]]) -> list[str]:
    if not run_paths:
        return []
    run_path_by_id = {run_path.name: run_path for run_path in run_paths}
    errors = []
    for ref in refs:
        ref_source_run_id = ref.get("source_run_id")
        run_path = (
            run_path_by_id.get(ref_source_run_id)
            if isinstance(ref_source_run_id, str)
            else run_paths[0]
        )
        if run_path is None:
            errors.append(f"{ref.get('artifact_id')}: unknown source_run_id {ref_source_run_id}")
            continue
        relative = Path(str(ref.get("relative_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{ref.get('artifact_id')}: unsafe artifact relative_path")
            continue
        artifact_path = run_path / relative
        if not artifact_path.exists():
            errors.append(f"{ref.get('artifact_id')}: missing artifact file")
    return errors


def _marker_reason(text: str, markers: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for marker in markers:
        if marker.lower() in lowered:
            return f"contains blocked marker {marker}"
    return None


def _provider_raw_marker_reason(
    text: str,
    *,
    export_format: str,
    policy: ExportPolicy,
) -> str | None:
    markers = PROVIDER_RAW_MARKERS
    if (
        export_format == "provider_reasoning_trace_training_export"
        and policy.allow_provider_reasoning_trace_training
    ):
        markers = tuple(marker for marker in markers if marker != "reasoning_content")
    return _marker_reason(text, markers)


def _provider_reasoning_trace_policy_reason(
    record: ExportRecord,
    *,
    export_format: str,
    policy: ExportPolicy,
) -> str | None:
    if export_format != "provider_reasoning_trace_training_export":
        return None
    if not policy.allow_provider_reasoning_trace_training:
        return "provider reasoning trace training export requires explicit export policy opt-in"
    if record.payload.get("ordinary_sft_target_allowed") is not False:
        return "provider reasoning trace export must not allow ordinary SFT targets"
    if record.payload.get("default_training_payload_allowed") is not False:
        return "provider reasoning trace export must not allow default training payloads"
    if record.payload.get("not_public_safe_by_default") is not True:
        return "provider reasoning trace export must be marked not_public_safe_by_default"
    if record.payload.get("requires_explicit_reasoning_export_policy") is not True:
        return "provider reasoning trace export must require explicit reasoning export policy"
    targets = record.payload.get("reasoning_trace_targets")
    if not isinstance(targets, list) or not targets:
        return "provider reasoning trace export contains no trace targets"
    for index, item in enumerate(targets):
        if not isinstance(item, dict):
            return f"reasoning_trace_targets[{index}] is not an object"
        if item.get("provider") != "deepseek":
            return f"reasoning_trace_targets[{index}] provider must be deepseek"
        if item.get("reasoning_trace_training_allowed") is not True:
            return f"reasoning_trace_targets[{index}] missing source opt-in flag"
        if item.get("ordinary_sft_target_allowed") is not False:
            return f"reasoning_trace_targets[{index}] ordinary SFT target flag must be false"
        if item.get("default_training_payload_allowed") is not False:
            return f"reasoning_trace_targets[{index}] default training target flag must be false"
        if item.get("not_public_safe_by_default") is not True:
            return f"reasoning_trace_targets[{index}] must be marked not public safe"
        if item.get("requires_explicit_reasoning_export_policy") is not True:
            return f"reasoning_trace_targets[{index}] must require explicit export policy"
        if item.get("raw_provider_artifact") is not False:
            return f"reasoning_trace_targets[{index}] must not be a raw provider artifact"
        source_ref = item.get("source_ref")
        if not isinstance(source_ref, dict):
            return f"reasoning_trace_targets[{index}] missing source_ref"
    return None


def _preference_pairing_reason(record: ExportRecord, export_format: str) -> str | None:
    if export_format != "preference_jsonl":
        return None
    metadata = record.metadata
    missing = sorted(key for key in PREFERENCE_PAIRING_METADATA_KEYS if key not in metadata)
    if missing:
        return f"preference pair missing pairing metadata: {', '.join(missing)}"
    if metadata.get("blocked_reasons"):
        return "preference pair has blocked reasons"
    source_run_ids = metadata.get("source_run_ids")
    if not isinstance(source_run_ids, list) or len(source_run_ids) != 2:
        return "preference pair must bind exactly two source run ids"
    compare_scope = metadata.get("compare_scope")
    if not isinstance(compare_scope, dict) or not compare_scope.get("canonical_key_fields"):
        return "preference pair missing compare scope fields"
    return None


def _local_path_reason(text: str) -> str | None:
    if re.search(r"(?<![A-Za-z0-9_])/(Users|private|var/folders)/", text):
        return "contains local absolute path"
    return None


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
