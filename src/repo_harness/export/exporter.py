"""Training export implementations for recorded run directories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from repo_harness.errors import ExportError
from repo_harness.export.audit import (
    audit_export_records,
    build_audit_report,
    render_audit_markdown,
)
from repo_harness.export.manifest import (
    CONVENIENCE_FILE_NAMES,
    DATA_FILE_NAMES,
    EXPORTER_VERSION,
    build_data_file,
    build_export_id,
    build_export_manifest,
    utc_timestamp,
    sha256_file,
    write_json,
    write_jsonl,
    write_text,
)
from repo_harness.export.pairing import (
    PairDecision,
    PairingSummary,
    build_preference_pairing,
    load_pairing_policy,
)
from repo_harness.export.schemas import ExportPolicy, ExportRecord, ExportRecordQuality
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import EXPORT_SCHEMA_VERSION
from repo_harness.trajectory import read_jsonl, verify_artifact_manifest

ExportFormat = Literal[
    "sft_jsonl",
    "rl_jsonl",
    "preference_jsonl",
    "provider_reasoning_trace_training_export",
]


def export_run_or_runs(
    run_dir_or_runs_dir: str | Path,
    *,
    export_format: ExportFormat,
    policy: ExportPolicy | None = None,
    compare_scope_path: str | Path | None = None,
) -> Path:
    path = Path(run_dir_or_runs_dir)
    if export_format == "sft_jsonl":
        if _looks_like_run_dir(path):
            return export_sft_jsonl(path, policy=policy)
        return _export_many(path, export_format, policy=policy)
    if export_format == "rl_jsonl":
        if _looks_like_run_dir(path):
            return export_rl_jsonl(path, policy=policy)
        return _export_many(path, export_format, policy=policy)
    if export_format == "preference_jsonl":
        return export_preference_jsonl(path, policy=policy, compare_scope_path=compare_scope_path)
    if export_format == "provider_reasoning_trace_training_export":
        if _looks_like_run_dir(path):
            return export_provider_reasoning_trace_training_export(path, policy=policy)
        return _export_many_provider_reasoning_trace(path, policy=policy)
    raise ExportError(f"不支持的导出格式：{export_format}")


def _export_many(
    runs_dir: Path,
    export_format: Literal["sft_jsonl", "rl_jsonl"],
    *,
    policy: ExportPolicy | None = None,
) -> Path:
    if not runs_dir.exists() or not runs_dir.is_dir():
        raise ExportError(f"runs directory 不存在：{runs_dir}")
    builders = {
        "sft_jsonl": _build_sft_record,
        "rl_jsonl": _build_rl_record,
    }
    run_paths = [run_dir for run_dir in sorted(runs_dir.iterdir()) if _looks_like_run_dir(run_dir)]
    records = [
        record
        for run_dir in run_paths
        for record in _build_records_safely(
            run_dir,
            export_format,
            builders[export_format],
        )
    ]
    if not records:
        raise ExportError(f"runs directory 中没有可导出的 run：{runs_dir}")
    return _write_format_export(
        export_root=runs_dir / "exports",
        export_format=export_format,
        records=records,
        run_paths=run_paths,
        skipped_reason=None,
        policy=policy or ExportPolicy(),
    )


def export_sft_jsonl(run_dir: str | Path, *, policy: ExportPolicy | None = None) -> Path:
    run_path = _require_run_dir(run_dir)
    records = _build_records_safely(run_path, "sft_jsonl", _build_sft_record)
    return _write_format_export(
        export_root=run_path / "exports",
        export_format="sft_jsonl",
        records=records,
        run_paths=[run_path],
        skipped_reason=None,
        policy=policy or ExportPolicy(),
    )


def export_rl_jsonl(run_dir: str | Path, *, policy: ExportPolicy | None = None) -> Path:
    run_path = _require_run_dir(run_dir)
    records = _build_records_safely(run_path, "rl_jsonl", _build_rl_record)
    return _write_format_export(
        export_root=run_path / "exports",
        export_format="rl_jsonl",
        records=records,
        run_paths=[run_path],
        skipped_reason=None,
        policy=policy or ExportPolicy(),
    )


def export_provider_reasoning_trace_training_export(
    run_dir: str | Path,
    *,
    policy: ExportPolicy | None = None,
) -> Path:
    resolved_policy = policy or ExportPolicy()
    _require_provider_reasoning_trace_opt_in(resolved_policy)
    run_path = _require_run_dir(run_dir)
    record = _build_record_safely(
        run_path,
        "provider_reasoning_trace_training_export",
        _build_provider_reasoning_trace_record,
    )
    return _write_format_export(
        export_root=run_path / "exports",
        export_format="provider_reasoning_trace_training_export",
        records=[record],
        run_paths=[run_path],
        skipped_reason=None,
        policy=resolved_policy,
    )


def _export_many_provider_reasoning_trace(
    runs_dir: Path,
    *,
    policy: ExportPolicy | None = None,
) -> Path:
    resolved_policy = policy or ExportPolicy()
    _require_provider_reasoning_trace_opt_in(resolved_policy)
    if not runs_dir.exists() or not runs_dir.is_dir():
        raise ExportError(f"runs directory 不存在：{runs_dir}")
    run_paths = [run_dir for run_dir in sorted(runs_dir.iterdir()) if _looks_like_run_dir(run_dir)]
    records = [
        _build_record_safely(
            run_dir,
            "provider_reasoning_trace_training_export",
            _build_provider_reasoning_trace_record,
        )
        for run_dir in run_paths
    ]
    if not records:
        raise ExportError(f"runs directory 中没有可导出的 run：{runs_dir}")
    return _write_format_export(
        export_root=runs_dir / "exports",
        export_format="provider_reasoning_trace_training_export",
        records=records,
        run_paths=run_paths,
        skipped_reason=None,
        policy=resolved_policy,
    )


def _require_provider_reasoning_trace_opt_in(policy: ExportPolicy) -> None:
    if not policy.allow_provider_reasoning_trace_training:
        raise ExportError(
            "provider_reasoning_trace_training_export requires "
            "allow_provider_reasoning_trace_training=true"
        )


def export_preference_jsonl(
    runs_dir: str | Path,
    *,
    policy: ExportPolicy | None = None,
    compare_scope_path: str | Path | None = None,
) -> Path:
    root = Path(runs_dir)
    if not root.exists() or not root.is_dir():
        raise ExportError(f"runs directory 不存在：{root}")
    resolved_policy = policy or ExportPolicy()
    pairing_policy = load_pairing_policy(compare_scope_path)
    run_paths = [run_dir for run_dir in sorted(root.iterdir()) if _looks_like_run_dir(run_dir)]
    pairing = build_preference_pairing(
        run_paths,
        pairing_policy=pairing_policy,
        export_policy=resolved_policy,
    )
    records = _build_preference_records(pairing.decisions, pairing_summary=pairing.summary, export_policy=resolved_policy)
    if not records:
        return _write_preference_skipped_export(
            export_root=root / "exports",
            source_run_dirs=_source_run_dirs(run_paths),
            reason=_preference_skipped_reason(pairing.summary),
            policy=resolved_policy,
            pairing_summary=pairing.summary,
            compare_scope_path=compare_scope_path,
        )
    return _write_format_export(
        export_root=root / "exports",
        export_format="preference_jsonl",
        records=records,
        run_paths=run_paths,
        skipped_reason=None,
        policy=resolved_policy,
        command_args_extra=_pairing_command_args(pairing.summary, compare_scope_path=compare_scope_path),
    )


def _build_record_safely(
    run_path: Path,
    export_format: ExportFormat,
    builder: Any,
) -> ExportRecord:
    records = _build_records_safely(run_path, export_format, builder)
    return records[0]


def _build_records_safely(
    run_path: Path,
    export_format: ExportFormat,
    builder: Any,
) -> list[ExportRecord]:
    try:
        result = builder(run_path)
        return result if isinstance(result, list) else [result]
    except (ExportError, ValueError, json.JSONDecodeError) as exc:
        reason = _export_failure_reason(exc)
        return [
            ExportRecord(
                sample_id=f"{run_path.name}_{_format_short_name(export_format)}",
                task_id=_task_id(run_path),
                source_run_id=run_path.name,
                payload={},
                quality=ExportRecordQuality(
                    training_eligibility="invalid",
                    quality_reasons=[reason],
                    artifact_manifest_status="invalid"
                    if "artifact_manifest" in reason
                    else "not_checked",
                    redaction_status="failed" if "hidden" in reason else "not_checked",
                ),
                metadata={
                    "export_policy_version": ExportPolicy().export_policy_version,
                    "export_format": export_format,
                    "source_run_id": run_path.name,
                    "build_error_type": type(exc).__name__,
                },
                filter_status="filtered",
                invalid_for_training=True,
                invalid_reason=reason,
            )
        ]


def _write_format_export(
    *,
    export_root: Path,
    export_format: ExportFormat,
    records: list[ExportRecord],
    run_paths: list[Path],
    skipped_reason: str | None,
    policy: ExportPolicy,
    command_args_extra: dict[str, Any] | None = None,
) -> Path:
    generated_at = utc_timestamp()
    source_run_dirs = _source_run_dirs(run_paths)
    export_id = build_export_id(export_format, source_run_dirs=source_run_dirs, generated_at=generated_at)
    export_dir = export_root / export_id
    data_file_name = DATA_FILE_NAMES[export_format]
    data_path = export_dir / data_file_name
    convenience_path = export_root / CONVENIENCE_FILE_NAMES[export_format]
    run_paths_by_id = {run_path.name: run_path for run_path in run_paths}
    audited = audit_export_records(
        records,
        run_paths=run_paths_by_id,
        export_format=export_format,
        policy=policy,
    )
    trainable_records = [
        audited_record.record
        for audited_record in audited
        if audited_record.record.quality.training_eligibility == "trainable"
    ]
    trainable_payloads = [record.model_dump(mode="json") for record in trainable_records]
    write_jsonl(data_path, trainable_payloads)
    write_jsonl(convenience_path, trainable_payloads)
    line_numbers = {record.sample_id: index + 1 for index, record in enumerate(trainable_records)}
    report = build_audit_report(
        audited,
        export_id=export_id,
        export_format=export_format,
        source_run_dirs=source_run_dirs,
        data_file_relative_path=data_file_name,
        generated_at=generated_at,
        line_numbers=line_numbers,
        skipped_reason=skipped_reason,
    )
    audit_json_sha = write_json(export_dir / "audit_report.json", report.model_dump(mode="json"))
    audit_md = render_audit_markdown(report)
    audit_md_sha = write_text(export_dir / "audit_report.md", audit_md)
    data_files = [build_data_file(data_path, relative_path=data_file_name, record_count=len(trainable_records))]
    command_args = {
        "format": export_format,
        "include_diagnostic": False,
        "allow_oracle_feedback_training": policy.allow_oracle_feedback_training,
        "allow_provider_reasoning_trace_training": policy.allow_provider_reasoning_trace_training,
    }
    command_args.update(command_args_extra or {})
    manifest = build_export_manifest(
        export_id=export_id,
        export_format=export_format,
        source_run_dirs=source_run_dirs,
        command_args=command_args,
        data_files=data_files,
        generated_at=generated_at,
        audit_report_path="audit_report.json",
        audit_report_sha256=audit_json_sha,
        audit_report_md_path="audit_report.md",
        audit_report_md_sha256=audit_md_sha,
        record_count=len(audited),
        included_count=len(trainable_records),
        filtered_count=sum(1 for item in audited if item.record.filter_status == "filtered"),
        skipped_count=sum(1 for item in audited if item.record.quality.training_eligibility == "skipped"),
        invalid_count=sum(1 for item in audited if item.record.quality.training_eligibility == "invalid"),
        diagnostic_only_count=sum(
            1 for item in audited if item.record.quality.training_eligibility == "diagnostic_only"
        ),
        policy=policy,
    )
    write_json(export_dir / "export_manifest.json", manifest.model_dump(mode="json"))
    return convenience_path


def _write_preference_skipped_export(
    *,
    export_root: Path,
    source_run_dirs: list[str],
    reason: str,
    policy: ExportPolicy,
    pairing_summary: PairingSummary | None = None,
    compare_scope_path: str | Path | None = None,
) -> Path:
    generated_at = utc_timestamp()
    export_id = build_export_id(
        "preference_jsonl",
        source_run_dirs=source_run_dirs,
        generated_at=generated_at,
    )
    export_dir = export_root / export_id
    skipped_payload = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "format": "preference_jsonl",
        "filter_status": "skipped",
        "reason": reason,
        "candidate_run_count": pairing_summary.candidate_run_count if pairing_summary else 0,
        "blocked_pair_count": pairing_summary.blocked_pair_count if pairing_summary else 0,
        "blocked_reason_distribution": (
            pairing_summary.blocked_reason_distribution if pairing_summary else {}
        ),
        "pairing_policy_version": pairing_summary.pairing_policy_version if pairing_summary else None,
        "compare_scope": pairing_summary.compare_scope if pairing_summary else None,
        "export_policy_version": policy.export_policy_version,
    }
    canonical_path = export_dir / "preference_skipped.json"
    convenience_path = export_root / "preference_skipped.json"
    write_json(canonical_path, skipped_payload)
    write_json(convenience_path, skipped_payload)
    report = build_audit_report(
        [],
        export_id=export_id,
        export_format="preference_jsonl",
        source_run_dirs=source_run_dirs,
        data_file_relative_path="preference_skipped.json",
        generated_at=generated_at,
        line_numbers={},
        skipped_reason=reason,
    )
    audit_json_sha = write_json(export_dir / "audit_report.json", report.model_dump(mode="json"))
    audit_md_sha = write_text(export_dir / "audit_report.md", render_audit_markdown(report))
    data_files = [
        build_data_file(
            canonical_path,
            relative_path="preference_skipped.json",
            record_count=0,
        )
    ]
    command_args = {
        "format": "preference_jsonl",
        "include_diagnostic": False,
        "allow_oracle_feedback_training": policy.allow_oracle_feedback_training,
        "allow_provider_reasoning_trace_training": policy.allow_provider_reasoning_trace_training,
    }
    command_args.update(_pairing_command_args(pairing_summary, compare_scope_path=compare_scope_path))
    manifest = build_export_manifest(
        export_id=export_id,
        export_format="preference_jsonl",
        source_run_dirs=source_run_dirs,
        command_args=command_args,
        data_files=data_files,
        generated_at=generated_at,
        audit_report_path="audit_report.json",
        audit_report_sha256=audit_json_sha,
        audit_report_md_path="audit_report.md",
        audit_report_md_sha256=audit_md_sha,
        record_count=0,
        included_count=0,
        filtered_count=0,
        skipped_count=1,
        invalid_count=0,
        diagnostic_only_count=0,
        policy=policy,
    )
    write_json(export_dir / "export_manifest.json", manifest.model_dump(mode="json"))
    return convenience_path


def _source_run_dirs(run_paths: list[Path]) -> list[str]:
    return [run_path.name for run_path in run_paths]


def _preference_skipped_reason(pairing_summary: PairingSummary) -> str:
    if pairing_summary.candidate_run_count < 2:
        return "not_enough_runs_for_same_task"
    if pairing_summary.blocked_pair_count:
        top_reason = next(iter(pairing_summary.blocked_reason_distribution), "compare_key_mismatch")
        return f"all_candidate_pairs_blocked:{top_reason}"
    return "not_enough_runs_for_same_task"


def _pairing_command_args(
    pairing_summary: PairingSummary | None,
    *,
    compare_scope_path: str | Path | None,
) -> dict[str, Any]:
    if pairing_summary is None:
        return {}
    return {
        "pairing_policy_version": pairing_summary.pairing_policy_version,
        "compare_scope": pairing_summary.compare_scope,
        "compare_scope_path": str(compare_scope_path) if compare_scope_path is not None else None,
        "candidate_run_count": pairing_summary.candidate_run_count,
        "candidate_pair_count": pairing_summary.candidate_pair_count,
        "blocked_pair_count": pairing_summary.blocked_pair_count,
        "blocked_reason_distribution": pairing_summary.blocked_reason_distribution,
    }


def _format_short_name(export_format: str) -> str:
    return {
        "sft_jsonl": "sft",
        "rl_jsonl": "rl",
        "preference_jsonl": "preference",
        "provider_reasoning_trace_training_export": "provider_reasoning_trace",
    }.get(export_format, export_format)


def _export_failure_reason(exc: Exception) -> str:
    message = str(exc)
    if "artifact manifest" in message:
        return "artifact_manifest_invalid"
    if "隐藏" in message or "hidden" in message:
        return "hidden_fields_absent"
    return "export_record_build_failed"


def _build_sft_record(run_path: Path) -> ExportRecord | list[ExportRecord]:
    snapshots = _model_input_snapshot_bindings(run_path)
    if snapshots:
        return [
            _build_sft_record_from_model_input_snapshot(
                run_path,
                binding,
                sample_index=index,
            )
            for index, binding in enumerate(snapshots, start=1)
        ]
    return _build_legacy_sft_record(run_path)


def _build_legacy_sft_record(run_path: Path) -> ExportRecord:
    transcript = read_jsonl(run_path / "transcript.jsonl")
    prepared_observations = _prepared_tool_observations(run_path)
    assistant_tool_calls = _assistant_tool_calls_by_turn(run_path)
    messages: list[dict[str, Any]] = []
    prompt_message_audit_bindings: list[dict[str, Any]] = []
    loss_mask: list[int] = []
    observation_mask: list[int] = []
    trainable_messages: list[int] = []
    excluded_control_message_count = 0
    for record in transcript:
        if not record.get("model_visible", False):
            continue
        if _is_default_export_excluded_control_message(record):
            excluded_control_message_count += 1
            continue
        message = _message_from_transcript(record, prepared_observations, assistant_tool_calls)
        if message is None:
            continue
        message = _sanitize_for_export(message)
        provider_message, audit_binding = _provider_visible_message_with_audit_binding(
            message,
            message_index=len(messages),
        )
        messages.append(provider_message)
        if audit_binding:
            prompt_message_audit_bindings.append(audit_binding)
        is_assistant_target = record.get("role") == "assistant" and bool(record.get("trainable"))
        is_tool_observation = record.get("role") == "tool"
        if is_assistant_target:
            trainable_messages.append(len(messages) - 1)
        loss_mask.append(1 if is_assistant_target else 0)
        observation_mask.append(1 if is_tool_observation else 0)

    metadata = _safe_metadata(run_path, export_format="sft_jsonl")
    payload = {
        "messages": messages,
        "trainable_messages": trainable_messages,
        "loss_mask": loss_mask,
        "observation_mask": observation_mask,
        "target": {
            "final_patch": _read_text_if_exists(run_path / "final.patch"),
        },
        "prepared_message_refs": _prepared_message_artifacts(run_path),
        "content_replacement_state_refs": _content_replacement_state_artifacts(run_path),
        "prompt_message_audit_bindings": prompt_message_audit_bindings,
        "v3_observation_bindings": _v3_observation_bindings(run_path),
        "excluded_harness_control_message_count": excluded_control_message_count,
        "harness_control_message_export_policy": "exclude_harness_generated_untrainable_control_messages_v1",
    }
    return ExportRecord(
        sample_id=f"{run_path.name}_sft",
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=_sanitize_for_export(payload),
        metadata=metadata,
        invalid_for_training=_invalid_for_training(run_path),
        invalid_reason=_invalid_reason(run_path),
    )


def _build_sft_record_from_model_input_snapshot(
    run_path: Path,
    binding: dict[str, Any],
    *,
    sample_index: int,
) -> ExportRecord:
    prepared_payload = binding["prepared_payload"]
    source_events = _tool_observation_source_events(run_path)
    prepared_audit_messages = [
        _prepared_snapshot_message_for_export(
            message,
            binding=binding,
            prepared_payload=prepared_payload,
            source_events=source_events,
        )
        for message in prepared_payload.get("messages", [])
    ]
    (
        prompt_messages,
        prompt_equivalence,
        prompt_message_audit_bindings,
    ) = _provider_visible_prompt_messages_for_export(
        run_path,
        binding,
        prepared_audit_messages=prepared_audit_messages,
    )
    assistant_target = _assistant_target_for_model_call(
        run_path,
        str(binding["snapshot"].get("model_call_id") or ""),
    )
    assistant_message = _sanitize_for_export(assistant_target["message"])
    messages = [*prompt_messages, assistant_message]
    trainable_target = (
        binding["snapshot"].get("trainable") is True
        and assistant_target.get("trainable") is True
    )
    metadata = _safe_metadata(run_path, export_format="sft_jsonl")
    payload = {
        "messages": messages,
        "trainable_messages": [len(messages) - 1] if trainable_target else [],
        "loss_mask": [0 for _ in prompt_messages] + [1 if trainable_target else 0],
        "observation_mask": [
            1 if message.get("role") == "tool" else 0 for message in prompt_messages
        ]
        + [0],
        "target": {
            "final_patch": _read_text_if_exists(run_path / "final.patch"),
            "assistant_message": assistant_message,
            "assistant_message_ref": assistant_target.get("assistant_message_ref"),
        },
        "training_sample_source": "model_input_snapshot",
        "model_call_id": binding["snapshot"].get("model_call_id"),
        "model_input_snapshot_ref": binding["snapshot_ref"],
        "model_input_snapshot": binding["snapshot"],
        "prepared_messages_ref": binding["prepared_messages_ref"],
        "prepared_messages_sha256": binding["prepared_messages_sha256"],
        "model_input_hash": binding["snapshot"].get("model_input_hash"),
        "provider_request_projection_hash": binding["snapshot"].get(
            "provider_request_projection_hash"
        ),
        "provider_request_artifact_ref": binding["snapshot"].get(
            "provider_request_artifact_ref"
        ),
        "provider_response_artifact_ref": binding["snapshot"].get(
            "provider_response_artifact_ref"
        ),
        "provider_visible_prompt_equivalence": prompt_equivalence,
        "prompt_message_audit_bindings": prompt_message_audit_bindings,
        "context_policy_snapshot_ref": binding["snapshot"].get(
            "context_policy_snapshot_ref"
        ),
        "context_compact_state_ref": binding["snapshot"].get(
            "context_compact_state_ref"
        ),
        "prepared_message_refs": [binding["prepared_messages_ref"]],
        "model_input_snapshot_refs": [binding["snapshot_ref"]],
        "content_replacement_state_refs": _content_replacement_state_artifacts(run_path),
        "v3_observation_bindings": _v3_observation_bindings(run_path),
        "excluded_harness_control_message_count": 0,
        "harness_control_message_export_policy": "exact_model_input_snapshot_v1",
    }
    return ExportRecord(
        sample_id=(
            f"{run_path.name}_sft_model_call_{sample_index:04d}"
        ),
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=_sanitize_for_export(payload),
        metadata=metadata,
        invalid_for_training=_invalid_for_training(run_path) or not trainable_target,
        invalid_reason=_invalid_reason(run_path)
        or (None if trainable_target else "model_input_snapshot_not_trainable"),
    )


def _prepared_snapshot_message_for_export(
    message: dict[str, Any],
    *,
    binding: dict[str, Any],
    prepared_payload: dict[str, Any],
    source_events: dict[str, str],
) -> dict[str, Any]:
    sanitized = _sanitize_for_export(message)
    if sanitized.get("role") != "tool":
        return sanitized
    tool_call_id = str(sanitized.get("tool_call_id") or "")
    artifact_refs = sanitized.get("artifact_refs", [])
    if not isinstance(artifact_refs, list):
        artifact_refs = []
    observation_source_event_ref = source_events.get(tool_call_id)
    tool_observation_ref = (
        artifact_refs[0]
        if artifact_refs
        else {
            "kind": "trajectory_event",
            "event_id": observation_source_event_ref,
        }
    )
    return {
        **sanitized,
        "artifact_refs": artifact_refs,
        "observation_source": "prepared_messages",
        "context_revision": prepared_payload.get("context_revision"),
        "prepared_messages_ref": binding["prepared_messages_ref"],
        "prepared_messages_sha256": binding["prepared_messages_sha256"],
        "model_input_hash": prepared_payload.get("model_input_hash"),
        "content_replacement_state_ref": prepared_payload.get(
            "content_replacement_state_ref"
        ),
        "tool_observation_ref": tool_observation_ref,
        "observation_source_event_ref": observation_source_event_ref,
        "observation_matches_prepared_messages": True,
        "context_replacement": bool(sanitized.get("context_replacement", False)),
    }


def _build_rl_record(run_path: Path) -> ExportRecord | list[ExportRecord]:
    snapshots = _model_input_snapshot_bindings(run_path)
    if snapshots:
        return [
            _build_rl_record_from_model_input_snapshot(
                run_path,
                binding,
                sample_index=index,
            )
            for index, binding in enumerate(snapshots, start=1)
        ]
    return _build_legacy_rl_record(run_path)


def _build_legacy_rl_record(run_path: Path) -> ExportRecord:
    metadata = _safe_metadata(run_path, export_format="rl_jsonl")
    reward = _read_json_if_exists(run_path / "reward.json")
    formal_final_reason = _formal_final_verifier_invalid_reason(run_path)
    payload = {
        "prompt": _prompt_from_prepared_messages(run_path),
        "trajectory": _trajectory_from_events(run_path),
        "reward": float(reward.get("final_reward", 0.0)) if reward else 0.0,
        "prepared_message_refs": _prepared_message_artifacts(run_path),
        "content_replacement_state_refs": _content_replacement_state_artifacts(run_path),
        "v3_observation_bindings": _v3_observation_bindings(run_path),
    }
    return ExportRecord(
        sample_id=f"{run_path.name}_rl",
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=_sanitize_for_export(payload),
        metadata=metadata,
        invalid_for_training=_invalid_for_training(run_path),
        invalid_reason=_invalid_reason(run_path),
    )


def _build_rl_record_from_model_input_snapshot(
    run_path: Path,
    binding: dict[str, Any],
    *,
    sample_index: int,
) -> ExportRecord:
    metadata = _safe_metadata(run_path, export_format="rl_jsonl")
    reward = _read_json_if_exists(run_path / "reward.json")
    trainable_snapshot = binding["snapshot"].get("trainable") is True
    prompt = _prompt_from_model_input_snapshot_binding(run_path, binding)
    payload = {
        "prompt": prompt,
        "trajectory": _trajectory_from_events(run_path),
        "reward": float(reward.get("final_reward", 0.0)) if reward else 0.0,
        "training_sample_source": "model_input_snapshot",
        "model_call_id": binding["snapshot"].get("model_call_id"),
        "model_input_snapshot_ref": binding["snapshot_ref"],
        "model_input_snapshot": binding["snapshot"],
        "provider_visible_prompt_equivalence": prompt.get(
            "provider_visible_prompt_equivalence"
        ),
        "prepared_message_refs": [binding["prepared_messages_ref"]],
        "model_input_snapshot_refs": [binding["snapshot_ref"]],
        "content_replacement_state_refs": _content_replacement_state_artifacts(run_path),
        "v3_observation_bindings": _v3_observation_bindings(run_path),
    }
    return ExportRecord(
        sample_id=f"{run_path.name}_rl_model_call_{sample_index:04d}",
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=_sanitize_for_export(payload),
        metadata=metadata,
        invalid_for_training=_invalid_for_training(run_path) or not trainable_snapshot,
        invalid_reason=_invalid_reason(run_path)
        or (None if trainable_snapshot else "model_input_snapshot_not_trainable"),
    )


def _build_provider_reasoning_trace_record(run_path: Path) -> ExportRecord:
    metadata = _safe_metadata(
        run_path,
        export_format="provider_reasoning_trace_training_export",
    )
    traces = []
    for index, ref in enumerate(_provider_reasoning_trace_artifacts(run_path), start=1):
        source = _read_artifact_json(run_path, ref)
        reasoning_content = source.get("reasoning_content")
        if not isinstance(reasoning_content, str) or not reasoning_content:
            continue
        traces.append(
            {
                "trace_index": index,
                "provider": source.get("provider", "deepseek"),
                "model_call_id": source.get("model_call_id"),
                "state_id": source.get("state_id"),
                "target": {
                    "type": "provider_reasoning_trace",
                    "reasoning_content": _sanitize_text(reasoning_content),
                },
                "source_ref": ref,
                "reasoning_trace_training_allowed": source.get(
                    "reasoning_trace_training_allowed"
                )
                is True,
                "ordinary_sft_target_allowed": False,
                "default_training_payload_allowed": False,
                "not_public_safe_by_default": True,
                "requires_explicit_reasoning_export_policy": True,
                "raw_provider_artifact": False,
            }
        )
    invalid_reason = _invalid_reason(run_path)
    if not traces:
        invalid_reason = invalid_reason or "missing_provider_reasoning_trace_source"
    payload = {
        "target_type": "provider_reasoning_trace",
        "provider": "deepseek",
        "reasoning_trace_targets": traces,
        "ordinary_sft_target_allowed": False,
        "default_training_payload_allowed": False,
        "not_public_safe_by_default": True,
        "requires_explicit_reasoning_export_policy": True,
    }
    return ExportRecord(
        sample_id=f"{run_path.name}_provider_reasoning_trace",
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=payload,
        metadata=metadata,
        invalid_for_training=bool(invalid_reason),
        invalid_reason=invalid_reason,
    )


def _build_preference_records(
    decisions: list[PairDecision],
    *,
    pairing_summary: PairingSummary,
    export_policy: ExportPolicy,
) -> list[ExportRecord]:
    records: list[ExportRecord] = []
    pair_index = 0
    for decision in decisions:
        if not decision.allowed:
            continue
        pair_index += 1
        chosen = _candidate_to_run_dict(decision.chosen)
        rejected = _candidate_to_run_dict(decision.rejected)
        payload = {
            "chosen": _preference_side(chosen),
            "rejected": _preference_side(rejected),
        }
        metadata = {
            "export_policy_version": export_policy.export_policy_version,
            "pairing_policy": pairing_summary.pairing_policy_version,
            "pairing_policy_version": pairing_summary.pairing_policy_version,
            "compare_scope": pairing_summary.compare_scope,
            "blocked_reasons": [],
            "source_run_ids": [chosen["run_id"], rejected["run_id"]],
        }
        records.append(
            ExportRecord(
                sample_id=f"{decision.chosen.task_id}_preference_{pair_index:04d}",
                task_id=decision.chosen.task_id,
                source_run_id=f"{chosen['run_id']}__vs__{rejected['run_id']}",
                payload=_sanitize_for_export(payload),
                metadata=_sanitize_for_export(metadata),
            )
        )
    return records


def _candidate_to_run_dict(candidate: Any) -> dict[str, Any]:
    return {
        "run_id": candidate.run_id,
        "run_dir": str(candidate.run_dir),
        "task_id": candidate.task_id,
        "reward": float(candidate.reward or 0.0),
        "run_outcome": candidate.run_outcome,
        "final_verifier_status": candidate.final_verifier_status,
    }


def _message_from_transcript(
    record: dict[str, Any],
    prepared_observations: dict[str, dict[str, Any]],
    assistant_tool_calls: dict[int, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    role = record.get("role")
    content = record.get("content_preview", "")
    if role in {"system", "user"}:
        return {"role": role, "content": content}
    if role == "assistant":
        tool_calls = assistant_tool_calls.get(int(record.get("turn") or 0), [])
        if tool_calls:
            return {"role": "assistant", "content": None, "tool_calls": tool_calls}
        return {"role": "assistant", "content": content}
    if role == "tool":
        tool_call_id = record.get("tool_call_id")
        prepared = prepared_observations.get(str(tool_call_id))
        if prepared is not None:
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": prepared["content"],
                "artifact_refs": prepared["artifact_refs"],
                "observation_source": "prepared_messages",
                "context_revision": prepared["context_revision"],
                "prepared_messages_ref": prepared["prepared_messages_ref"],
                "prepared_messages_sha256": prepared["prepared_messages_sha256"],
                "model_input_hash": prepared["model_input_hash"],
                "content_replacement_state_ref": prepared["content_replacement_state_ref"],
                "tool_observation_ref": prepared["tool_observation_ref"],
                "observation_source_event_ref": prepared["observation_source_event_ref"],
                "observation_matches_prepared_messages": prepared["observation_matches_prepared_messages"],
                "context_replacement": prepared["context_replacement"],
            }
        return None
    return None


def _is_default_export_excluded_control_message(record: dict[str, Any]) -> bool:
    if record.get("role") != "user":
        return False
    if record.get("trainable") is not False:
        return False
    message_id = str(record.get("message_id") or "")
    if message_id.startswith(("convergence_nudge_", "context_warning_")):
        return True
    preview = str(record.get("content_preview") or "")
    return "repo_harness_control_message" in preview and (
        "convergence_nudge" in preview or "context_warning" in preview
    )


def _assistant_tool_calls_by_turn(run_path: Path) -> dict[int, list[dict[str, Any]]]:
    calls_by_turn: dict[int, list[dict[str, Any]]] = {}
    for event in read_jsonl(run_path / "events.jsonl"):
        if event.get("event_type") != "tool_requested":
            continue
        turn = event.get("turn")
        if not isinstance(turn, int):
            continue
        call = event.get("data", {})
        tool_name = str(call.get("tool_name") or "")
        requested_arguments = call.get("arguments", {})
        arguments = _canonical_tool_arguments_for_provider_visible_export(
            tool_name,
            requested_arguments,
        )
        calls_by_turn.setdefault(turn, []).append(
            _provider_tool_call_for_export(
                {
                    "tool_call_id": call.get("tool_call_id"),
                    "tool_name": tool_name,
                    "arguments": arguments,
                }
            )
        )
    return calls_by_turn


def _model_input_snapshot_bindings(run_path: Path) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    accepted_snapshot_events = _accepted_model_input_snapshot_events(run_path)
    snapshot_artifacts = _model_input_snapshot_artifacts(run_path)
    for snapshot_ref in snapshot_artifacts:
        accepted_event = accepted_snapshot_events.get(str(snapshot_ref.get("artifact_id")))
        if accepted_event is None:
            continue
        snapshot = _read_artifact_json(run_path, snapshot_ref)
        event_data = accepted_event.get("data", {})
        event_model_call_id = event_data.get("model_call_id")
        if event_model_call_id and snapshot.get("model_call_id") != event_model_call_id:
            raise ExportError("model_input_snapshot model_call_id does not match accepted event")
        if event_data.get("model_input_hash") and snapshot.get("model_input_hash") != event_data.get(
            "model_input_hash"
        ):
            raise ExportError("model_input_snapshot model_input_hash does not match accepted event")
        prepared_ref = snapshot.get("prepared_messages_ref")
        if not isinstance(prepared_ref, dict):
            raise ExportError("model_input_snapshot missing prepared_messages_ref")
        event_prepared_ref = event_data.get("prepared_messages_ref")
        if isinstance(event_prepared_ref, dict) and (
            event_prepared_ref.get("artifact_id") != prepared_ref.get("artifact_id")
            or event_prepared_ref.get("sha256") != prepared_ref.get("sha256")
        ):
            raise ExportError("model_input_snapshot prepared_messages_ref does not match accepted event")
        prepared_payload = _read_artifact_json(run_path, prepared_ref)
        prepared_path = _artifact_path(run_path, prepared_ref)
        prepared_sha = sha256_file(prepared_path)
        if prepared_ref.get("sha256") and prepared_ref.get("sha256") != prepared_sha:
            raise ExportError("model_input_snapshot prepared_messages_ref sha mismatch")
        if prepared_payload.get("model_input_hash") != snapshot.get("model_input_hash"):
            raise ExportError("model_input_snapshot model_input_hash mismatch")
        bindings.append(
            {
                "snapshot_ref": snapshot_ref,
                "snapshot": snapshot,
                "prepared_messages_ref": prepared_ref,
                "prepared_messages_sha256": prepared_sha,
                "prepared_payload": prepared_payload,
            }
        )
    if snapshot_artifacts and not bindings:
        raise ExportError(
            "model_input_snapshot artifacts exist but none are bound to model_input_accepted"
        )
    return bindings


def _accepted_model_input_snapshot_events(run_path: Path) -> dict[str, dict[str, Any]]:
    accepted: dict[str, dict[str, Any]] = {}
    for event in read_jsonl(run_path / "events.jsonl"):
        if event.get("event_type") != "model_input_accepted":
            continue
        ref = event.get("data", {}).get("model_input_snapshot_ref")
        if not isinstance(ref, dict):
            continue
        artifact_id = ref.get("artifact_id")
        if isinstance(artifact_id, str) and artifact_id:
            accepted[artifact_id] = event
    return accepted


def _prompt_from_model_input_snapshot_binding(
    run_path: Path,
    binding: dict[str, Any],
) -> dict[str, Any]:
    snapshot = binding["snapshot"]
    prepared_payload = binding["prepared_payload"]
    source_events = _tool_observation_source_events(run_path)
    prepared_audit_messages = [
        _prepared_snapshot_message_for_export(
            message,
            binding=binding,
            prepared_payload=prepared_payload,
            source_events=source_events,
        )
        for message in prepared_payload.get("messages", [])
    ]
    (
        prompt_messages,
        prompt_equivalence,
        prompt_message_audit_bindings,
    ) = _provider_visible_prompt_messages_for_export(
        run_path,
        binding,
        prepared_audit_messages=prepared_audit_messages,
    )
    return _sanitize_for_export(
        {
            "messages": prompt_messages,
            "training_sample_source": "model_input_snapshot",
            "model_call_id": snapshot.get("model_call_id"),
            "model_input_snapshot_ref": binding["snapshot_ref"],
            "prepared_messages_ref": binding["prepared_messages_ref"],
            "prepared_messages_sha256": binding["prepared_messages_sha256"],
            "context_revision": prepared_payload.get("context_revision"),
            "model_input_hash": snapshot.get("model_input_hash"),
            "provider_request_projection_hash": snapshot.get(
                "provider_request_projection_hash"
            ),
            "content_replacement_state_ref": snapshot.get("context_compact_state_ref")
            or prepared_payload.get("content_replacement_state_ref"),
            "provider_request_artifact_ref": snapshot.get(
                "provider_request_artifact_ref"
            ),
            "provider_response_artifact_ref": snapshot.get(
                "provider_response_artifact_ref"
            ),
            "context_policy_snapshot_ref": snapshot.get("context_policy_snapshot_ref"),
            "provider_visible_prompt_equivalence": prompt_equivalence,
            "prompt_message_audit_bindings": prompt_message_audit_bindings,
        }
    )


def _provider_visible_prompt_messages_for_export(
    run_path: Path,
    binding: dict[str, Any],
    *,
    prepared_audit_messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    prepared_payload = binding["prepared_payload"]
    prepared_messages = prepared_payload.get("messages", [])
    if not isinstance(prepared_messages, list):
        prepared_messages = []
    raw_request_ref = binding["snapshot"].get("provider_request_artifact_ref")
    raw_request = _read_artifact_json(run_path, raw_request_ref) if isinstance(raw_request_ref, dict) else {}
    provider = str(raw_request.get("provider") or "")
    provider_body_messages = _provider_body_message_projection(raw_request)
    prepared_projection = _safe_project_prepared_messages(
        prepared_messages,
        provider=provider,
    )
    prepared_export_projection = _export_training_message_projection(
        [_sanitize_for_export(message) for message in prepared_projection]
    )
    provider_body_export_projection = (
        _export_training_message_projection(
            [_sanitize_for_export(message) for message in provider_body_messages]
        )
        if provider_body_messages is not None
        else None
    )
    if provider_body_messages is not None:
        projection = provider_body_export_projection or []
        projection_source = "raw_provider_request_body"
    else:
        projection = prepared_export_projection
        projection_source = "prepared_messages_provider_projection"
    prompt_messages = [_sanitize_for_export(message) for message in projection]
    prompt_message_audit_bindings = _prompt_message_audit_bindings(
        prepared_audit_messages
    )
    export_projection = _export_training_message_projection(prompt_messages)
    provider_body_available = provider_body_messages is not None
    prepared_body_equivalent = (
        raw_request.get("prepared_messages_body_equivalent")
        if provider_body_available
        else None
    )
    if prepared_body_equivalent is None and provider_body_available:
        prepared_body_equivalent = prepared_projection == provider_body_messages
    expected_export_projection = (
        provider_body_export_projection
        if provider_body_available
        else prepared_export_projection
    )
    export_body_equivalent = (
        export_projection == expected_export_projection
    )
    return (
        prompt_messages,
        {
            "schema_version": "repo_harness_provider_visible_prompt_equivalence_v0",
            "source": projection_source,
            "provider_body_available": provider_body_available,
            "prepared_messages_ref": binding["prepared_messages_ref"],
            "raw_provider_request_ref": raw_request_ref,
            "prepared_messages_projection_hash": stable_hash(prepared_projection),
            "provider_body_message_projection_hash": (
                stable_hash(provider_body_messages) if provider_body_available else None
            ),
            "provider_body_export_projection_hash": (
                stable_hash(provider_body_export_projection)
                if provider_body_available
                else None
            ),
            "prepared_messages_export_projection_hash": stable_hash(
                prepared_export_projection
            ),
            "export_prompt_projection_hash": stable_hash(export_projection),
            "prepared_messages_body_equivalent": prepared_body_equivalent,
            "export_prompt_body_equivalent": export_body_equivalent,
            "prepared_message_count": len(prepared_projection),
            "provider_body_message_count": (
                len(provider_body_messages) if provider_body_available else None
            ),
            "export_prompt_message_count": len(export_projection),
        },
        prompt_message_audit_bindings,
    )


def _provider_body_message_projection(raw_request: dict[str, Any]) -> list[dict[str, Any]] | None:
    body = raw_request.get("body")
    if isinstance(body, dict) and isinstance(body.get("messages"), list):
        return _export_training_message_projection(body.get("messages", []))
    return None


def _safe_project_prepared_messages(
    prepared_messages: list[Any],
    *,
    provider: str,
) -> list[dict[str, Any]]:
    del provider
    projected: list[dict[str, Any]] = []
    for message in prepared_messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        converted: dict[str, Any] = {"role": role}
        if role == "assistant":
            converted["content"] = _content_to_export_string(message.get("content"))
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                converted["tool_calls"] = _provider_tool_calls_for_export(tool_calls)
        elif role == "tool":
            converted["content"] = _content_to_export_string(message.get("content"))
            converted["tool_call_id"] = str(
                message.get("tool_call_id") or message.get("tool_result_id") or ""
            )
        else:
            converted["content"] = _content_to_export_string(message.get("content"))
        projected.append(
            {key: value for key, value in converted.items() if value is not None}
        )
    return projected


def _content_to_export_string(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def _canonical_tool_arguments_for_provider_visible_export(
    tool_name: str,
    arguments: Any,
) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        return {}
    canonical = dict(arguments)
    if tool_name == "grep" and "pattern" in canonical:
        if "query" not in canonical:
            canonical["query"] = canonical["pattern"]
        canonical.pop("pattern", None)
    return canonical


def _provider_tool_call_for_export(call: Any) -> dict[str, Any]:
    if not isinstance(call, dict):
        call = {}
    function = call.get("function") if isinstance(call.get("function"), dict) else {}
    tool_name = str(call.get("tool_name") or call.get("name") or function.get("name") or "")
    raw_arguments = call.get("arguments")
    if raw_arguments is None:
        raw_arguments = function.get("arguments") or {}
    if isinstance(raw_arguments, str):
        try:
            raw_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            raw_arguments = {}
    arguments = _canonical_tool_arguments_for_provider_visible_export(
        tool_name,
        raw_arguments,
    )
    return {
        "id": str(call.get("tool_call_id") or call.get("id") or ""),
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": json.dumps(
                arguments,
                ensure_ascii=False,
                sort_keys=True,
            ),
        },
    }


def _prompt_message_audit_bindings(
    audit_messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for index, audit in enumerate(audit_messages):
        if not isinstance(audit, dict):
            continue
        _, audit_binding = _provider_visible_message_with_audit_binding(
            audit,
            message_index=index,
        )
        if audit_binding:
            bindings.append(audit_binding)
    return bindings


def _provider_visible_message_with_audit_binding(
    message: dict[str, Any],
    *,
    message_index: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    provider_message = {
        key: value
        for key, value in message.items()
        if key in {"role", "content", "tool_call_id", "tool_calls"}
    }
    audit_only = {
        key: value
        for key, value in message.items()
        if key not in {"role", "content", "tool_call_id", "tool_calls"}
        and value is not None
    }
    if not audit_only:
        return _sanitize_for_export(provider_message), None
    return (
        _sanitize_for_export(provider_message),
        _sanitize_for_export(
            {
                "message_index": message_index,
                "role": message.get("role"),
                **audit_only,
            }
        ),
    )


def _export_training_message_projection(messages: list[Any]) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        item = {
            "role": message.get("role"),
            "content": message.get("content"),
            "tool_call_id": message.get("tool_call_id"),
            "tool_calls": _provider_tool_calls_for_export(message.get("tool_calls")),
        }
        projected.append({key: value for key, value in item.items() if value is not None})
    return projected


def _provider_tool_calls_for_export(tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_calls, list):
        return []
    return [_provider_tool_call_for_export(call) for call in tool_calls]


def _assistant_target_for_model_call(run_path: Path, model_call_id: str) -> dict[str, Any]:
    for record in read_jsonl(run_path / "transcript.jsonl"):
        if record.get("role") != "assistant":
            continue
        if str(record.get("model_call_id") or "") != model_call_id:
            continue
        for ref in record.get("content_artifact_refs", []) or []:
            if isinstance(ref, dict) and ref.get("kind") == "assistant_message":
                payload = _read_artifact_json(run_path, ref)
                message = {
                    "role": "assistant",
                    "content": payload.get("content"),
                }
                tool_calls = payload.get("tool_calls") or []
                if tool_calls:
                    message["tool_calls"] = _provider_tool_calls_for_export(tool_calls)
                return {
                    "message": message,
                    "assistant_message_ref": ref,
                    "trainable": record.get("trainable") is True
                    and payload.get("model_error_type") is None,
                }
        return {
            "message": {
                "role": "assistant",
                "content": record.get("content_preview", ""),
            },
            "assistant_message_ref": None,
            "trainable": record.get("trainable") is True,
        }
    return {
        "message": {"role": "assistant", "content": ""},
        "assistant_message_ref": None,
        "trainable": False,
    }


def _prompt_from_prepared_messages(run_path: Path) -> dict[str, Any]:
    snapshots = _model_input_snapshot_bindings(run_path)
    if snapshots:
        return _prompt_from_model_input_snapshot_binding(run_path, snapshots[0])
    prepared = _prepared_message_artifacts(run_path)
    if not prepared:
        return {"messages": []}
    first = _read_artifact_json(run_path, prepared[0])
    messages = [
        message
        for message in first.get("messages", [])
        if message.get("role") in {"system", "user"}
    ]
    return _sanitize_for_export(
        {
            "messages": messages,
            "prepared_messages_ref": prepared[0],
            "context_revision": first.get("context_revision"),
            "model_input_hash": first.get("model_input_hash"),
            "content_replacement_state_ref": first.get("content_replacement_state_ref"),
        }
    )


def _trajectory_from_events(run_path: Path) -> list[dict[str, Any]]:
    events = read_jsonl(run_path / "events.jsonl")
    prepared_observations = _prepared_tool_observations(run_path)
    results_by_call = {
        event.get("data", {}).get("tool_call_id"): event
        for event in events
        if event.get("event_type")
        in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
    }
    trajectory = []
    for event in events:
        if event.get("event_type") != "tool_requested":
            continue
        call = event.get("data", {})
        result = results_by_call.get(call.get("tool_call_id"))
        observation = {}
        if result is not None:
            data = result.get("data", {})
            prepared = prepared_observations.get(str(call.get("tool_call_id")))
            if prepared is not None:
                observation = {
                    "status": data.get("status"),
                    "preview": prepared["content"],
                    "truncated": data.get("truncated", False),
                    "artifact_refs": prepared["artifact_refs"],
                    "error_type": data.get("error_type"),
                    "observation_source": "prepared_messages",
                    "context_revision": prepared["context_revision"],
                    "prepared_messages_ref": prepared["prepared_messages_ref"],
                    "prepared_messages_sha256": prepared["prepared_messages_sha256"],
                    "model_input_hash": prepared["model_input_hash"],
                    "content_replacement_state_ref": prepared["content_replacement_state_ref"],
                    "tool_observation_ref": prepared["tool_observation_ref"],
                    "observation_source_event_ref": prepared["observation_source_event_ref"],
                    "observation_matches_prepared_messages": prepared["observation_matches_prepared_messages"],
                    "context_replacement": prepared["context_replacement"],
                }
            else:
                observation = {
                    "observation_source": "not_observed_by_model",
                }
        trajectory.append(
            _sanitize_for_export(
                {
                    "turn": event.get("turn"),
                    "context_revision": _context_revision_for_turn(events, event.get("turn")),
                    "action": {
                        "type": "tool_call",
                        "tool_call_id": call.get("tool_call_id"),
                        "tool_name": call.get("tool_name"),
                        "arguments": _canonical_tool_arguments_for_provider_visible_export(
                            str(call.get("tool_name") or ""),
                            call.get("arguments", {}),
                        ),
                    },
                    "observation": observation,
                }
            )
        )
    return trajectory


def _context_revision_for_turn(events: list[dict[str, Any]], turn: int | None) -> int | None:
    for event in events:
        if event.get("event_type") == "context_prepared" and event.get("turn") == turn:
            return event.get("data", {}).get("context_revision")
    return None


def _safe_metadata(run_path: Path, *, export_format: str) -> dict[str, Any]:
    run_config = _read_json_if_exists(run_path / "run_config_facts.json")
    run_metadata = _read_json_if_exists(run_path / "run_metadata.json")
    task = _read_json_if_exists(run_path / "task.yaml")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    events = read_jsonl(run_path / "events.jsonl")
    first_model = next((event for event in events if event.get("event_type") == "model_call_completed"), {})
    model_data = first_model.get("data", {})
    metadata_source = run_metadata.get("metadata_source") or (
        "v2_config_facts" if run_config else "legacy_inferred"
    )
    tool_protocol = run_config.get("tool_protocol") or run_metadata.get("tool_protocol") or {}
    environment = run_config.get("environment_fingerprint", {})
    workspace_execution = environment.get("workspace_execution", {})
    workspace_backend = workspace_execution.get("workspace_backend", {})
    source_checkout = workspace_execution.get("source_checkout", {})
    initial_context = run_metadata.get("initial_context_artifacts", {})
    if not isinstance(initial_context, dict):
        initial_context = {}
    repository_hints_mode = (
        run_config.get("repository_hints_mode")
        or initial_context.get("repository_hints_mode")
    )
    repository_hints_hash = initial_context.get("repository_hints_model_visible_hash")
    if repository_hints_hash is None and repository_hints_mode == "disabled":
        repository_hints_hash = "disabled"
    context_strategy = {
        "initial_context_policy_version": (
            run_config.get("initial_context_policy_version")
            or initial_context.get("initial_context_policy_version")
        ),
        "repository_hints_mode": repository_hints_mode,
        "repository_hints_model_visible_hash": repository_hints_hash,
        "tool_schema_snapshot_hash": tool_protocol.get("tool_schema_snapshot_sha256"),
        "context_policy_snapshot_hash": run_config.get("context_policy_snapshot_hash"),
    }
    return _sanitize_for_export(
        {
            "export_policy_version": ExportPolicy().export_policy_version,
            "export_format": export_format,
            "source_run_id": run_path.name,
            "metadata_source": metadata_source,
            "provider": run_config.get("provider") or model_data.get("provider"),
            "model_id": run_config.get("model_id") or model_data.get("model_id"),
            "task_version": run_config.get("task_version") or task.get("task_version"),
            "dataset_name": run_config.get("dataset_name") or task.get("dataset_name"),
            "dataset_split": task.get("dataset_split"),
            "source_kind": run_config.get("source_kind") or task.get("source_kind"),
            "source_type": source_checkout.get("source_type"),
            "source_tree_hash": source_checkout.get("source_tree_hash"),
            "source_archive_sha256": (
                run_config.get("source_archive_sha256")
                or source_checkout.get("source_archive_sha256")
            ),
            "working_tree_clean": source_checkout.get("working_tree_clean"),
            "dirty_snapshot_allowed": source_checkout.get("dirty_snapshot_allowed"),
            "decontamination_status": (
                source_checkout.get("decontamination_status")
                or task.get("decontamination", {}).get("status")
            ),
            "repo_base_commit": (
                run_config.get("base_commit")
                or source_checkout.get("base_commit")
                or task.get("base_commit")
            ),
            "scaffold_id": run_config.get("scaffold_id") or metrics.get("interaction_efficiency", {}).get("scaffold_id", "simple_react"),
            "scaffold_version": run_config.get("scaffold_version"),
            "export_quality_diagnostic_reasons": _export_quality_diagnostic_reasons(run_path),
            "permission_mode": run_config.get("permission_mode") or _initial_user_field(run_path, "permission_mode"),
            "permission_policy_version": run_config.get("permission_policy_version"),
            "execution_mode": workspace_backend.get("backend") or _initial_user_field(run_path, "execution_mode"),
            "tool_policy_version": run_config.get("allowed_tools_policy"),
            "tool_schema_snapshot_hash": tool_protocol.get("tool_schema_snapshot_sha256"),
            "context_policy_version": run_config.get("context_policy_version"),
            "context_policy_snapshot_hash": context_strategy[
                "context_policy_snapshot_hash"
            ],
            "initial_context_policy_version": context_strategy[
                "initial_context_policy_version"
            ],
            "repository_hints_mode": context_strategy["repository_hints_mode"],
            "repository_hints_model_visible_hash": context_strategy[
                "repository_hints_model_visible_hash"
            ],
            "context_strategy_hash": stable_hash(context_strategy),
            "prompt_template_version": run_config.get("prompt_template_version"),
            "reward_formula_version": run_config.get("reward_formula_version"),
            "final_verifier_mode": run_config.get("final_verifier_mode"),
            "schema_version": EXPORT_SCHEMA_VERSION,
        }
    )


def _initial_user_field(run_path: Path, key: str) -> Any:
    prepared = _prepared_message_artifacts(run_path)
    if not prepared:
        return None
    payload = _read_artifact_json(run_path, prepared[0])
    for message in payload.get("messages", []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, dict):
            return content.get(key)
    return None


def _safe_verifier_summary(run_path: Path) -> dict[str, Any]:
    verifier = _read_json_if_exists(run_path / "verifier.json")
    return {
        "accepted": verifier.get("accepted"),
        "pass_ratio": verifier.get("pass_ratio"),
        "error_type": verifier.get("error_type"),
        "verifier_stage": verifier.get("verifier_stage"),
    }


def _invalid_for_training(run_path: Path) -> bool:
    metrics = _read_json_if_exists(run_path / "metrics.json")
    reward = _read_json_if_exists(run_path / "reward.json")
    return bool(
        reward.get("invalid_for_training")
        or _formal_final_verifier_invalid_reason(run_path) is not None
        or metrics.get("run_outcome") in {
            "failed",
            "invalid_task",
            "flaky_task",
            "interrupted",
            "inconclusive",
        }
        or metrics.get("interaction_efficiency", {}).get("agent_stop_reason")
        in {"model_error", "timeout", "task_timeout"}
        or _has_model_error_event(run_path)
        or metrics.get("final_verifier_status") in {"timeout", "error"}
    )


def _export_quality_diagnostic_reasons(run_path: Path) -> list[str]:
    metrics = _read_json_if_exists(run_path / "metrics.json")
    facts = _read_json_if_exists(run_path / "run_config_facts.json")
    interaction = metrics.get("interaction_efficiency", {})
    agent_stop_reason = interaction.get("agent_stop_reason")
    feedback_tests_passed_policy = (
        interaction.get("feedback_tests_passed_policy")
        or facts.get("feedback_tests_passed_policy")
    )
    reasons: list[str] = []
    if agent_stop_reason == "max_turns":
        reasons.append("agent_stop_reason_max_turns")
    if agent_stop_reason in {"timeout", "task_timeout"}:
        reasons.append(f"agent_stop_reason_{agent_stop_reason}")
    if feedback_tests_passed_policy == "require_model_final" and agent_stop_reason != "final_answer":
        reasons.append("require_model_final_not_satisfied")
    should_check_unobserved_terminal_tool = agent_stop_reason == "max_turns" or (
        feedback_tests_passed_policy == "require_model_final"
        and agent_stop_reason not in {None, "final_answer"}
    )
    if should_check_unobserved_terminal_tool and _last_successful_tool_observation_unseen(
        run_path,
        agent_stop_reason=agent_stop_reason,
    ):
        reasons.append("last_tool_observation_not_observed_by_model")
    return reasons


def _last_successful_tool_observation_unseen(
    run_path: Path,
    *,
    agent_stop_reason: str | None,
) -> bool:
    if agent_stop_reason == "feedback_tests_passed":
        return False
    events = read_jsonl(run_path / "events.jsonl")
    terminal_events = [
        event
        for event in events
        if event.get("event_type")
        in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
    ]
    if not terminal_events:
        return False
    last_terminal = terminal_events[-1]
    data = last_terminal.get("data", {})
    if last_terminal.get("event_type") != "tool_completed" or data.get("status") != "ok":
        return False
    tool_call_id = str(data.get("tool_call_id") or "")
    if not tool_call_id:
        return False
    return tool_call_id not in _prepared_tool_observations(run_path)


def _invalid_reason(run_path: Path) -> str | None:
    if not _invalid_for_training(run_path):
        return None
    metrics = _read_json_if_exists(run_path / "metrics.json")
    reward = _read_json_if_exists(run_path / "reward.json")
    return (
        reward.get("invalid_reason")
        or _formal_final_verifier_invalid_reason(run_path)
        or _model_error_invalid_reason(run_path)
        or _agent_stop_invalid_reason(run_path)
        or metrics.get("run_outcome")
        or "filtered_by_export_policy"
    )


def _has_model_error_event(run_path: Path) -> bool:
    return _model_error_invalid_reason(run_path) is not None


def _agent_stop_invalid_reason(run_path: Path) -> str | None:
    metrics = _read_json_if_exists(run_path / "metrics.json")
    agent_stop_reason = metrics.get("interaction_efficiency", {}).get("agent_stop_reason")
    if agent_stop_reason in {"timeout", "task_timeout"}:
        return f"agent_stop_reason:{agent_stop_reason}"
    return None


def _model_error_invalid_reason(run_path: Path) -> str | None:
    events = read_jsonl(run_path / "events.jsonl")
    accepted_model_call_ids = {
        str(event.get("data", {}).get("model_call_id"))
        for event in events
        if event.get("event_type") == "model_input_accepted"
        and event.get("data", {}).get("model_call_id")
    }
    rejected_context_limit_errors = {
        "context_limit",
        "prompt_too_long",
        "prompt too long",
        "request_too_large",
        "payload_too_large",
    }
    for index, event in enumerate(events):
        if event.get("event_type") != "model_call_completed":
            continue
        data = event.get("data", {})
        model_error_type = data.get("model_error_type")
        model_call_id = str(data.get("model_call_id") or "")
        if (
            model_error_type in rejected_context_limit_errors
            and model_call_id not in accepted_model_call_ids
            and _has_later_reactive_recovery_accepted(events, index)
        ):
            continue
        if model_error_type:
            return f"model_error:{model_error_type}"
    return None


def _has_later_reactive_recovery_accepted(events: list[dict[str, Any]], index: int) -> bool:
    saw_recovery = False
    for event in events[index + 1 :]:
        if event.get("event_type") in {
            "reactive_compact_applied",
            "ptl_truncation_applied",
        }:
            saw_recovery = True
            continue
        if saw_recovery and event.get("event_type") == "model_input_accepted":
            return True
    return False


def _formal_final_verifier_invalid_reason(run_path: Path) -> str | None:
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


def _run_score(run_path: Path) -> dict[str, Any]:
    reward = _read_json_if_exists(run_path / "reward.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    return {
        "run_id": run_path.name,
        "run_dir": str(run_path),
        "task_id": _task_id(run_path),
        "reward": float(reward.get("final_reward", 0.0)) if reward else 0.0,
        "run_outcome": metrics.get("run_outcome"),
        "final_verifier_status": metrics.get("final_verifier_status"),
    }


def _preference_side(run: dict[str, Any]) -> dict[str, Any]:
    run_path = Path(run["run_dir"])
    return {
        "source_run_id": run["run_id"],
        "final_patch": _read_text_if_exists(run_path / "final.patch"),
    }


def _prepared_tool_observations(run_path: Path) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    source_events = _tool_observation_source_events(run_path)
    for prepared_ref in _prepared_message_artifacts(run_path):
        payload = _read_artifact_json(run_path, prepared_ref)
        state_ref = payload.get("content_replacement_state_ref")
        prepared_sha = prepared_ref.get("sha256") or sha256_file(run_path / prepared_ref["relative_path"])
        for message in payload.get("messages", []):
            if message.get("role") != "tool":
                continue
            tool_call_id = str(message.get("tool_call_id") or "")
            if not tool_call_id or tool_call_id in observations:
                continue
            artifact_refs = message.get("artifact_refs", [])
            observations[tool_call_id] = {
                "content": str(message.get("content", "")),
                "artifact_refs": artifact_refs,
                "context_revision": payload.get("context_revision"),
                "prepared_messages_ref": prepared_ref,
                "prepared_messages_sha256": prepared_sha,
                "model_input_hash": payload.get("model_input_hash"),
                "content_replacement_state_ref": state_ref,
                "tool_observation_ref": (
                    artifact_refs[0]
                    if artifact_refs
                    else {
                        "kind": "trajectory_event",
                        "event_id": source_events.get(tool_call_id),
                    }
                ),
                "observation_source_event_ref": source_events.get(tool_call_id),
                "observation_matches_prepared_messages": True,
                "context_replacement": bool(message.get("context_replacement", False)),
            }
    return observations


def _v3_observation_bindings(run_path: Path) -> list[dict[str, Any]]:
    return [
        {
            "tool_call_id": tool_call_id,
            "prepared_messages_ref": observation["prepared_messages_ref"],
            "prepared_messages_sha256": observation["prepared_messages_sha256"],
            "model_input_hash": observation["model_input_hash"],
            "context_revision": observation["context_revision"],
            "content_replacement_state_ref": observation["content_replacement_state_ref"],
            "tool_observation_ref": observation["tool_observation_ref"],
            "observation_source_event_ref": observation["observation_source_event_ref"],
            "observation_matches_prepared_messages": observation["observation_matches_prepared_messages"],
            "context_replacement": observation["context_replacement"],
        }
        for tool_call_id, observation in sorted(_prepared_tool_observations(run_path).items())
    ]


def _tool_observation_source_events(run_path: Path) -> dict[str, str]:
    return {
        str(event.get("data", {}).get("tool_call_id")): str(event.get("event_id"))
        for event in read_jsonl(run_path / "events.jsonl")
        if event.get("event_type")
        in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
        and event.get("data", {}).get("tool_call_id")
    }


def _prepared_message_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _safe_artifact_manifest(run_path)
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "prepared_messages"
    ]


def _model_input_snapshot_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _safe_artifact_manifest(run_path)
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "model_input_snapshot"
    ]


def _content_replacement_state_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _safe_artifact_manifest(run_path)
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "content_replacement_state"
    ]


def _provider_reasoning_trace_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _safe_artifact_manifest(run_path)
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "deepseek_provider_reasoning_trace"
    ]


def _safe_artifact_manifest(run_path: Path) -> dict[str, Any]:
    errors = verify_artifact_manifest(run_path)
    if errors:
        raise ExportError(f"artifact manifest invalid: {errors[0]}")
    return _read_json_if_exists(run_path / "artifacts.json")


def _read_artifact_json(run_path: Path, artifact_ref: dict[str, Any]) -> dict[str, Any]:
    return _read_json(_artifact_path(run_path, artifact_ref))


def _artifact_path(run_path: Path, artifact_ref: dict[str, Any]) -> Path:
    relative = Path(str(artifact_ref.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative.parts[:1] != ("artifacts",):
        raise ExportError("artifact manifest contains unsafe relative_path.")
    artifact_path = (run_path / relative).resolve()
    try:
        artifact_path.relative_to((run_path / "artifacts").resolve())
    except ValueError as exc:
        raise ExportError("artifact manifest contains path escaping artifacts/.") from exc
    return artifact_path


def _task_id(run_path: Path) -> str:
    baseline = _read_json_if_exists(run_path / "baseline.json")
    if baseline.get("task_id"):
        return str(baseline["task_id"])
    task = _read_json_if_exists(run_path / "task.yaml")
    if task.get("id"):
        return str(task["id"])
    events = read_jsonl(run_path / "events.jsonl")
    for event in events:
        if event.get("task_id"):
            return str(event["task_id"])
    return "unknown_task"


def _relative_ref(run_path: Path, relative_path: str, kind: str) -> dict[str, Any]:
    path = run_path / relative_path
    return {
        "kind": kind,
        "relative_path": relative_path,
        "exists": path.exists(),
        "manifest_backed": False,
    }


def _manifest_ref(
    run_path: Path,
    artifact_kind: str,
    fallback_relative_path: str,
    fallback_kind: str,
) -> dict[str, Any]:
    manifest = _safe_artifact_manifest(run_path)
    for artifact in manifest.get("artifacts", []):
        if artifact.get("kind") == artifact_kind:
            return {**artifact, "manifest_backed": True}
    return _relative_ref(run_path, fallback_relative_path, fallback_kind)


def _with_source_run_id(ref: dict[str, Any], source_run_id: str) -> dict[str, Any]:
    return {**ref, "source_run_id": source_run_id}


def _outcome_rank(run_outcome: str | None) -> int:
    return {
        "success": 4,
        "failed": 3,
        "inconclusive": 2,
        "interrupted": 1,
        "invalid_task": 0,
        "flaky_task": 0,
    }.get(run_outcome or "", 0)


def _require_run_dir(run_dir: str | Path) -> Path:
    run_path = Path(run_dir)
    if not _looks_like_run_dir(run_path):
        raise ExportError(f"不是有效 run directory：{run_path}")
    return run_path


def _looks_like_run_dir(path: Path) -> bool:
    return path.is_dir() and (path / "metrics.json").exists() and (path / "transcript.jsonl").exists()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return _sanitize_text(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _sanitize_for_export(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_for_export(nested)
            for key, nested in value.items()
            if key != "provider_private"
        }
    if isinstance(value, list):
        return [_sanitize_for_export(nested) for nested in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _sanitize_text(text: str) -> str:
    text = re.sub(
        r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]{8,}",
        r"\1<REDACTED_CREDENTIAL>",
        text,
    )
    text = re.sub(
        r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}",
        r"\1<REDACTED_CREDENTIAL>",
        text,
    )
    text = re.sub(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b", "<REDACTED_CREDENTIAL>", text)
    text = re.sub(
        (
            r"(?i)(?P<key>\b(?:api[_-]?key|token|password|secret)\b\s*[:=]\s*)"
            r"(?P<quote>['\"]?)"
            r"(?P<value>[A-Za-z0-9_\-./=:+]{6,})"
            r"(?P=quote)"
        ),
        lambda match: (
            f"{match.group('key')}{match.group('quote')}"
            f"<REDACTED_CREDENTIAL>{match.group('quote')}"
        ),
        text,
    )
    text = re.sub(r"/Users/[^\s,'\"})\]]+", "<REDACTED_LOCAL_PATH>", text)
    text = re.sub(r"/private/[^\s,'\"})\]]+", "<REDACTED_LOCAL_PATH>", text)
    if text.startswith("/"):
        return "<REDACTED_LOCAL_PATH>"
    return text
