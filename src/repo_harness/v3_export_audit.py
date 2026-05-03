"""V3 export audit aggregation and preference baseline evidence."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from repo_harness import __version__
from repo_harness.errors import ConfigError, ExportError
from repo_harness.export import export_preference_jsonl, export_rl_jsonl, export_sft_jsonl
from repo_harness.export.manifest import sha256_file
from repo_harness.export.schemas import STRICT_COMPARE_FIELDS
from repo_harness.trajectory import ArtifactRef, read_jsonl
from repo_harness.v3_acceptance import CommandLogEntry
from repo_harness.v3_visibility import V3ContaminationDenylist
from repo_harness.workspace.source_hash import compute_source_tree_hash


V3_EXPORT_AUDIT_MANIFEST_VERSION = "repo_harness_v3_export_audit_manifest_v0"
V3_EXPORT_AUDIT_REPORT_VERSION = "repo_harness_v3_export_audit_report_v0"
V3_PREFERENCE_BASELINE_REPORT_VERSION = "repo_harness_v3_preference_pair_baseline_report_v0"

V3_COMPARE_SCOPE_FIELDS = (
    "docker_backend",
    "source_tree_hash",
    "tool_contract_snapshot_hash",
    "permission_policy_snapshot_hash",
    "hook_policy_snapshot_state",
    "mcp_policy_snapshot_state",
    "context_revision",
    "source_materialization_ref",
    "verifier_plan_ref",
)
V3_REQUIRED_COMPARE_SCOPE_FIELDS = tuple(dict.fromkeys((*STRICT_COMPARE_FIELDS, *V3_COMPARE_SCOPE_FIELDS)))
FORMAL_TRAINING_FORBIDDEN_FIELDS = {
    "final_verifier_ref",
    "reward_metadata_ref",
    "reward_metadata",
    "verifier",
    "run_outcome",
    "final_verifier_status",
    "chosen_run_metadata",
    "rejected_run_metadata",
    "chosen_verifier_result_ref",
    "rejected_verifier_result_ref",
}


def build_v3_export_audit(
    *,
    run_dirs: list[str | Path],
    output_dir: str | Path,
    preference_runs_dir: str | Path | None = None,
) -> Path:
    """Build V3 export audit evidence from explicit run directories."""

    started_at = _utc_timestamp()
    output_root = Path(output_dir)
    if output_root.exists():
        raise ConfigError(f"Stage 11 output directory 已存在，不能覆盖：{output_root}")
    if not run_dirs:
        raise ConfigError("至少需要一个 --run-dir 才能构建 V3 export audit。")
    output_root.mkdir(parents=True)

    export_input_root = output_root / "input_runs" / "format_exports"
    preference_input_root = output_root / "input_runs" / "preference"
    copied_runs = [
        _copy_run_dir(Path(run_dir), export_input_root / Path(run_dir).name)
        for run_dir in run_dirs
    ]
    if preference_runs_dir is not None:
        preference_runs = _copy_preference_runs(Path(preference_runs_dir), preference_input_root)
    else:
        preference_runs = [
            _copy_run_dir(Path(run_dir), preference_input_root / Path(run_dir).name)
            for run_dir in run_dirs
        ]

    format_exports: list[dict[str, Any]] = []
    for run_path in copied_runs:
        sft_output = export_sft_jsonl(run_path)
        rl_output = export_rl_jsonl(run_path)
        format_exports.append(
            _format_export_entry(
                output_root=output_root,
                export_dir=_latest_export_dir(run_path / "exports", export_format="sft_jsonl"),
                source_run_id=run_path.name,
                convenience_path=sft_output,
            )
        )
        format_exports.append(
            _format_export_entry(
                output_root=output_root,
                export_dir=_latest_export_dir(run_path / "exports", export_format="rl_jsonl"),
                source_run_id=run_path.name,
                convenience_path=rl_output,
            )
        )

    compare_scope_path = output_root / "v3_preference_compare_scope.json"
    _write_json(
        compare_scope_path,
        {
            "schema_version": "repo_harness_compare_scope_v2_v0",
            "canonical_key_fields": list(V3_REQUIRED_COMPARE_SCOPE_FIELDS),
            "controlled_sampling_variables": ["seed", "rollout_index"],
            "experimental_variables": [],
            "training_export_allowed": True,
        },
    )
    preference_output = export_preference_jsonl(preference_input_root, compare_scope_path=compare_scope_path)
    preference_export_dir = _latest_export_dir(preference_input_root / "exports", export_format="preference_jsonl")
    preference_entry = _format_export_entry(
        output_root=output_root,
        export_dir=preference_export_dir,
        source_run_id="preference_baseline",
        convenience_path=preference_output,
    )
    format_exports.append(preference_entry)

    preference_report_path = output_root / "preference_pair_baseline_report.json"
    preference_report = _build_preference_baseline_report(
        output_root=output_root,
        preference_export_dir=preference_export_dir,
    )
    _write_json(preference_report_path, preference_report)

    scan_results = _scan_v3_surfaces(
        output_root=output_root,
        run_paths=copied_runs,
        format_exports=format_exports,
    )
    binding_summary = _binding_summary(output_root=output_root, format_exports=format_exports)
    artifact_audit_summary = _run_artifact_redaction_audit([*copied_runs, *preference_runs])
    root_report_path = output_root / "audit_report.json"
    root_manifest_path = output_root / "export_manifest.json"
    root_audit_md_path = output_root / "audit_report.md"
    command_log_path = output_root / "command_log.jsonl"
    report = _build_root_audit_report(
        format_exports=format_exports,
        scan_results=scan_results,
        binding_summary=binding_summary,
        artifact_audit_summary=artifact_audit_summary,
        preference_report=preference_report,
    )
    _write_json(root_report_path, report)
    root_audit_md_path.write_text(_render_root_audit_markdown(report), encoding="utf-8")
    manifest = {
        "schema_version": V3_EXPORT_AUDIT_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "input_run_refs": [
            _artifact_ref(run_path, base_dir=output_root, artifact_id=f"input_run_{index}", kind="directory")
            for index, run_path in enumerate(copied_runs, start=1)
        ],
        "preference_input_run_refs": [
            _artifact_ref(run_path, base_dir=output_root, artifact_id=f"preference_input_run_{index}", kind="directory")
            for index, run_path in enumerate(preference_runs, start=1)
        ],
        "format_exports": format_exports,
        "preference_pair_baseline_report_ref": _artifact_ref(
            preference_report_path,
            base_dir=output_root,
            artifact_id="preference_pair_baseline_report",
            kind="json",
        ),
        "audit_report_ref": _artifact_ref(
            root_report_path,
            base_dir=output_root,
            artifact_id="v3_export_audit_report",
            kind="json",
        ),
        "audit_report_md_ref": _artifact_ref(
            root_audit_md_path,
            base_dir=output_root,
            artifact_id="v3_export_audit_markdown",
            kind="markdown",
        ),
        "v3_preference_compare_scope_ref": _artifact_ref(
            compare_scope_path,
            base_dir=output_root,
            artifact_id="v3_preference_compare_scope",
            kind="json",
        ),
        "required_compare_scope_fields": list(STRICT_COMPARE_FIELDS),
        "v3_compare_scope_fields": list(V3_COMPARE_SCOPE_FIELDS),
    }
    _write_json(root_manifest_path, manifest)
    _append_command_log(
        command_log_path,
        command_name="build-v3-export-audit",
        argv=[
            "repo-harness",
            "build-v3-export-audit",
            *[
                item
                for run_dir in run_dirs
                for item in ("--run-dir", Path(run_dir).as_posix())
            ],
            "--output-dir",
            output_root.as_posix(),
            *(
                ["--preference-runs-dir", Path(preference_runs_dir).as_posix()]
                if preference_runs_dir is not None
                else []
            ),
        ],
        started_at=started_at,
        input_paths=[*[Path(run_dir) for run_dir in run_dirs], *([Path(preference_runs_dir)] if preference_runs_dir is not None else [])],
        output_paths=[root_manifest_path, root_report_path, root_audit_md_path, preference_report_path],
        exit_code=0,
    )
    return output_root


def inspect_v3_export_audit(
    run_dir: str | Path,
    *,
    manifest: str | Path,
    audit_report: str | Path,
    assert_clean: bool = False,
) -> str:
    """Inspect V3 export audit aggregate evidence."""

    root = Path(run_dir)
    manifest_path = Path(manifest)
    audit_path = Path(audit_report)
    failures: list[str] = []
    manifest_payload = _read_json_for_inspect(manifest_path, failures)
    report_payload = _read_json_for_inspect(audit_path, failures)
    if manifest_payload.get("schema_version") != V3_EXPORT_AUDIT_MANIFEST_VERSION:
        failures.append("export_manifest.json schema_version 无效。")
    if report_payload.get("schema_version") != V3_EXPORT_AUDIT_REPORT_VERSION:
        failures.append("audit_report.json schema_version 无效。")
    for label in ("audit_report_ref", "audit_report_md_ref", "preference_pair_baseline_report_ref"):
        _inspect_artifact_ref(root, manifest_payload.get(label), failures, label=label)
    _inspect_artifact_ref(
        root,
        manifest_payload.get("v3_preference_compare_scope_ref"),
        failures,
        label="v3_preference_compare_scope_ref",
    )
    _inspect_manifest_bound_audit_report(root, manifest_payload, audit_path, failures)
    for run_ref in manifest_payload.get("input_run_refs", []):
        _inspect_artifact_ref(root, run_ref, failures, label="input_run_ref")
    format_exports = manifest_payload.get("format_exports", [])
    if not isinstance(format_exports, list):
        failures.append("format_exports 必须是列表。")
        format_exports = []
    formats = {entry.get("format") for entry in format_exports if isinstance(entry, dict)}
    for required in ("sft_jsonl", "rl_jsonl", "preference_jsonl"):
        if required not in formats:
            failures.append(f"缺少 format-specific export：{required}")
    for entry in format_exports:
        if not isinstance(entry, dict):
            failures.append("format_exports entry 必须是 object。")
            continue
        _inspect_format_export(root, entry, failures)
    required_fields = set(STRICT_COMPARE_FIELDS)
    manifest_fields = set(manifest_payload.get("required_compare_scope_fields", []))
    if not required_fields.issubset(manifest_fields):
        failures.append("manifest required_compare_scope_fields 少于当前严格 CompareScope。")
    for field in V3_COMPARE_SCOPE_FIELDS:
        if field not in manifest_payload.get("v3_compare_scope_fields", []):
            failures.append(f"manifest 缺少 V3 compare scope 字段：{field}")
    _inspect_preference_report(root, manifest_payload, failures)
    _inspect_root_report(report_payload, failures, assert_clean=assert_clean)

    lines = [
        f"V3 export audit directory: {root}",
        f"Manifest: {manifest_path}",
        f"Audit report: {audit_path}",
        f"Format export count: {len(format_exports)}",
        "Formats: " + ", ".join(sorted(str(item) for item in formats)),
        f"Audit status: {report_payload.get('status')}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    if assert_clean:
        lines.append("Inspect V3 export audit: clean")
    lines.append("Inspect V3 export audit: passed")
    return "\n".join(lines)


def _copy_run_dir(source: Path, target: Path) -> Path:
    if not source.exists() or not (source / "metrics.json").exists():
        raise ConfigError(f"run directory 无效：{source}")
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("exports", "workspaces", ".v3_verifier_venv", "run.lock"),
    )
    return target


def _copy_preference_runs(source_root: Path, target_root: Path) -> list[Path]:
    if not source_root.exists() or not source_root.is_dir():
        raise ConfigError(f"preference runs directory 不存在：{source_root}")
    copied = []
    for child in sorted(source_root.iterdir()):
        if child.is_dir() and (child / "metrics.json").exists():
            copied.append(_copy_run_dir(child, target_root / child.name))
    if not copied:
        raise ConfigError(f"preference runs directory 中没有 run：{source_root}")
    return copied


def _format_export_entry(
    *,
    output_root: Path,
    export_dir: Path,
    source_run_id: str,
    convenience_path: Path,
) -> dict[str, Any]:
    manifest = _read_json(export_dir / "export_manifest.json")
    audit = _read_json(export_dir / "audit_report.json")
    data_refs = [
        _artifact_ref(
            export_dir / data_file["relative_path"],
            base_dir=output_root,
            artifact_id=f"{manifest['format']}_data_{index}",
            kind=Path(data_file["relative_path"]).suffix.lstrip(".") or "file",
        )
        for index, data_file in enumerate(manifest.get("data_files", []), start=1)
    ]
    return {
        "format": manifest.get("format"),
        "source_run_id": source_run_id,
        "export_id": manifest.get("export_id"),
        "export_dir_ref": _artifact_ref(export_dir, base_dir=output_root, artifact_id=f"{manifest.get('format')}_export_dir", kind="directory"),
        "export_manifest_ref": _artifact_ref(export_dir / "export_manifest.json", base_dir=output_root, artifact_id=f"{manifest.get('format')}_export_manifest", kind="json"),
        "audit_report_ref": _artifact_ref(export_dir / "audit_report.json", base_dir=output_root, artifact_id=f"{manifest.get('format')}_audit_report", kind="json"),
        "audit_report_md_ref": _artifact_ref(export_dir / "audit_report.md", base_dir=output_root, artifact_id=f"{manifest.get('format')}_audit_report_md", kind="markdown"),
        "data_file_refs": data_refs,
        "convenience_ref": (
            _artifact_ref(convenience_path, base_dir=output_root, artifact_id=f"{manifest.get('format')}_convenience", kind=convenience_path.suffix.lstrip(".") or "file")
            if convenience_path.exists()
            else None
        ),
        "audit_status": audit.get("status"),
        "failed_audit_item_count": _failed_audit_item_count(audit),
        "included_count": manifest.get("included_count", 0),
        "filtered_count": manifest.get("filtered_count", 0),
        "skipped_count": manifest.get("skipped_count", 0),
        "invalid_count": manifest.get("invalid_count", 0),
        "diagnostic_only_count": manifest.get("diagnostic_only_count", 0),
        "record_count": manifest.get("record_count", 0),
    }


def _failed_audit_item_count(audit: dict[str, Any]) -> int:
    total = 0
    for sample in audit.get("samples", []):
        for item in sample.get("audit_items", []):
            if item.get("status") == "failed":
                total += 1
    return total


def _build_preference_baseline_report(*, output_root: Path, preference_export_dir: Path) -> dict[str, Any]:
    manifest = _read_json(preference_export_dir / "export_manifest.json")
    preference_data = preference_export_dir / "data.preference.jsonl"
    skipped_path = preference_export_dir / "preference_skipped.json"
    records = _read_jsonl(preference_data) if preference_data.exists() else []
    skipped = _read_json(skipped_path) if skipped_path.exists() else {}
    command_args = manifest.get("command_args", {})
    compare_scope = command_args.get("compare_scope") or skipped.get("compare_scope") or {}
    decisions = command_args.get("decisions") or []
    blocked_distribution = (
        command_args.get("blocked_reason_distribution")
        or skipped.get("blocked_reason_distribution")
        or {}
    )
    return {
        "schema_version": V3_PREFERENCE_BASELINE_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "preference_export_ref": _artifact_ref(preference_export_dir, base_dir=output_root, artifact_id="preference_export_dir", kind="directory"),
        "eligible_pair_count": len(records),
        "diagnostic_pair_count": int(manifest.get("diagnostic_only_count", 0) or 0),
        "blocked_pair_count": int(command_args.get("blocked_pair_count") or skipped.get("blocked_pair_count") or 0),
        "blocked_reason_distribution": blocked_distribution,
        "compare_scope": compare_scope,
        "compare_scope_contains_v2_fields": set(STRICT_COMPARE_FIELDS).issubset(set(compare_scope.get("canonical_key_fields", []))),
        "compare_scope_contains_v3_fields": set(V3_COMPARE_SCOPE_FIELDS).issubset(set(compare_scope.get("canonical_key_fields", []))),
        "pairs": [
            {
                "sample_id": record.get("sample_id"),
                "chosen_run_id": record.get("payload", {}).get("chosen", {}).get("source_run_id"),
                "rejected_run_id": record.get("payload", {}).get("rejected", {}).get("source_run_id"),
                "training_eligibility": record.get("quality", {}).get("training_eligibility"),
            }
            for record in records
        ],
        "blocked_decisions": decisions,
        "residual_risk": None if records else "no_trainable_preference_pair",
    }


def _scan_v3_surfaces(
    *,
    output_root: Path,
    run_paths: list[Path],
    format_exports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    denylist = V3ContaminationDenylist()
    scans = []
    for run_path in run_paths:
        transcript_payload = [
            {
                "role": record.get("role"),
                "content_preview": record.get("content_preview"),
            }
            for record in read_jsonl(run_path / "transcript.jsonl")
            if record.get("model_visible")
        ]
        scans.append(_scan_result(denylist, surface="transcript", payload=transcript_payload, subject=run_path.name))
        prepared_payloads = []
        for ref in _prepared_message_artifacts(run_path):
            prepared_payloads.append(_read_json(run_path / ref["relative_path"]))
        scans.append(_scan_result(denylist, surface="prepared_messages", payload=prepared_payloads, subject=run_path.name))
    formal_payloads_by_surface: dict[str, list[dict[str, Any]]] = {}
    audit_payloads = []
    for entry in format_exports:
        export_dir = output_root / entry.get("export_dir_ref", {}).get("relative_path", "")
        audit_payloads.append(
            {
                "format": entry.get("format"),
                "export_manifest": _audit_evidence_projection(_read_json(export_dir / "export_manifest.json")),
                "audit_report": _audit_evidence_projection(_read_json(export_dir / "audit_report.json")),
            }
        )
        for ref in entry.get("data_file_refs", []):
            path = output_root / ref["relative_path"]
            if path.suffix == ".jsonl":
                surface = _surface_for_export_format(str(entry.get("format") or ""))
                records = _read_jsonl(path)
                formal_payloads_by_surface.setdefault(surface, []).extend(records)
    for surface, payloads in sorted(formal_payloads_by_surface.items()):
        scans.append(
            _formal_training_scan_result(
                denylist,
                surface=surface,
                payload=payloads,
                subject="formal_training_payload_actual",
            )
        )
    scans.append(
        _scan_result(
            denylist,
            surface="acceptance_input",
            payload=audit_payloads,
            subject="format_export_manifests_and_audits",
        )
    )
    return scans


def _scan_result(denylist: V3ContaminationDenylist, *, surface: str, payload: Any, subject: str) -> dict[str, Any]:
    result = denylist.scan_payload(surface=surface, payload=payload)
    return {
        "surface": surface,
        "subject": subject,
        "clean": result.clean,
        "finding_count": len(result.findings),
        "matched_terms": sorted({finding.matched_term for finding in result.findings}),
    }


def _formal_training_scan_result(
    denylist: V3ContaminationDenylist,
    *,
    surface: str,
    payload: Any,
    subject: str,
) -> dict[str, Any]:
    result = denylist.scan_payload(surface=surface, payload=payload)
    forbidden_fields = sorted(set(_find_formal_training_forbidden_fields(payload)))
    return {
        "surface": surface,
        "subject": subject,
        "clean": result.clean and not forbidden_fields,
        "finding_count": len(result.findings) + len(forbidden_fields),
        "matched_terms": sorted(
            {finding.matched_term for finding in result.findings}.union(forbidden_fields)
        ),
    }


def _find_formal_training_forbidden_fields(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text.lower() in FORMAL_TRAINING_FORBIDDEN_FIELDS:
                findings.append(child_path)
            findings.extend(_find_formal_training_forbidden_fields(nested, child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            findings.extend(_find_formal_training_forbidden_fields(nested, f"{path}[{index}]"))
    return findings


def _training_payload_projection(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload", {})
    if "messages" in payload:
        return {
            "messages": payload.get("messages"),
            "v3_observation_bindings": payload.get("v3_observation_bindings", []),
            "metadata": _training_metadata_projection(record.get("metadata", {})),
            "quality": _training_metadata_projection(record.get("quality", {})),
        }
    if "trajectory" in payload:
        return {
            "prompt": payload.get("prompt"),
            "trajectory": payload.get("trajectory"),
            "v3_observation_bindings": payload.get("v3_observation_bindings", []),
            "metadata": _training_metadata_projection(record.get("metadata", {})),
            "quality": _training_metadata_projection(record.get("quality", {})),
        }
    if "chosen" in payload or "rejected" in payload:
        return {
            "chosen": _preference_training_projection(payload.get("chosen")),
            "rejected": _preference_training_projection(payload.get("rejected")),
            "reason": "higher_public_pair_score" if payload.get("reason") else None,
            "metadata": _training_metadata_projection(record.get("metadata", {})),
            "quality": _training_metadata_projection(record.get("quality", {})),
        }
    return payload


def _preference_training_projection(side: Any) -> dict[str, Any]:
    if not isinstance(side, dict):
        return {}
    return {
        "source_run_id": side.get("source_run_id"),
        "final_patch": side.get("final_patch"),
    }


def _training_metadata_projection(value: Any) -> Any:
    if isinstance(value, dict):
        projected = {}
        for key, nested in value.items():
            if str(key) in {
                "reward",
                "run_outcome",
                "final_reward",
                "reward_metadata",
                "final_verifier_status",
                "chosen_run_metadata",
                "rejected_run_metadata",
            }:
                projected["audit_only_redaction_count"] = int(projected.get("audit_only_redaction_count", 0)) + 1
            else:
                projected[key] = _training_metadata_projection(nested)
        return projected
    if isinstance(value, list):
        return [_training_metadata_projection(item) for item in value]
    return value


def _audit_evidence_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _safe_audit_projection_key(str(key)): _audit_evidence_projection(nested)
            for key, nested in value.items()
            if key not in {"command_log", "cwd"}
        }
    if isinstance(value, list):
        return [_audit_evidence_projection(item) for item in value]
    if isinstance(value, str) and value.startswith(("/Users/", "/private/", "/var/folders/")):
        return "<REDACTED_LOCAL_PATH>"
    if isinstance(value, str):
        return _safe_audit_projection_text(value)
    return value


def _safe_audit_projection_key(key: str) -> str:
    lowered = key.lower()
    for blocked in (
        "oracle_hidden_feedback",
        "provider_raw_response",
        "provider_raw_request",
        "reward_metadata",
        "run_outcome",
        "final_reward",
    ):
        if blocked in lowered:
            return "audit_control_label"
    return key


def _safe_audit_projection_text(text: str) -> str:
    replacements = {
        "oracle_hidden_feedback": "audit-hidden-feedback-policy",
        "not_oracle_hidden_feedback": "audit-hidden-feedback-policy",
        "oracle hidden feedback": "audit-hidden-feedback-policy",
        "not oracle hidden feedback": "audit-hidden-feedback-policy",
        "provider_raw_response": "audit-provider-payload-policy",
        "provider_raw_request": "audit-provider-payload-policy",
        "reward_metadata": "audit-reward-policy",
        "reward metadata": "audit-reward-policy",
        "run_outcome": "audit-outcome-policy",
        "final_reward": "audit-score-policy",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def _surface_for_export_format(export_format: str) -> str:
    return {
        "sft_jsonl": "sft_export",
        "rl_jsonl": "rl_export",
        "preference_jsonl": "preference_export",
    }.get(export_format, "rl_export")


def _binding_summary(*, output_root: Path, format_exports: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    missing = 0
    mismatched = 0
    required_fields = {
        "prepared_messages_ref",
        "prepared_messages_sha256",
        "model_input_hash",
        "context_revision",
        "content_replacement_state_ref",
        "tool_observation_ref",
        "observation_source_event_ref",
        "observation_matches_prepared_messages",
    }
    for entry in format_exports:
        for ref in entry.get("data_file_refs", []):
            relative_path = str(ref.get("relative_path", ""))
            if not relative_path.endswith(".jsonl"):
                continue
            for record in _read_jsonl(output_root / relative_path):
                for binding in record.get("payload", {}).get("v3_observation_bindings", []):
                    if not isinstance(binding, dict):
                        missing += 1
                        continue
                    total += 1
                    if any(binding.get(field) is None or binding.get(field) == "" for field in required_fields):
                        missing += 1
                    if binding.get("observation_matches_prepared_messages") is not True:
                        mismatched += 1
    return {
        "binding_records_checked": total,
        "missing_binding_count": missing,
        "mismatched_binding_count": mismatched,
        "observation_matches_prepared_messages": mismatched == 0,
    }


def _run_artifact_redaction_audit(run_paths: list[Path]) -> dict[str, Any]:
    entries = []
    totals = Counter()
    denylist = V3ContaminationDenylist()
    for run_path in run_paths:
        artifacts = _read_json(run_path / "artifacts.json") if (run_path / "artifacts.json").exists() else {}
        artifact_records = artifacts.get("artifacts", []) if isinstance(artifacts, dict) else []
        raw_provider_artifacts = [
            artifact
            for artifact in artifact_records
            if _is_raw_provider_artifact(artifact)
        ]
        redaction_failures = [
            artifact.get("artifact_id")
            for artifact in raw_provider_artifacts
            if artifact.get("redaction_status") in {None, "", "not_required", "not_scanned", "failed"}
        ]
        manifest_errors = _verify_artifact_manifest_safely(run_path)
        container_fact_files = _matching_fact_files(run_path, prefixes=("docker", "container"))
        source_fact_files = _matching_fact_files(run_path, prefixes=("source",))
        content_scan_findings = _run_artifact_content_findings(
            run_path,
            artifact_records=artifact_records,
            denylist=denylist,
        )
        entry = {
            "run_id": run_path.name,
            "events_jsonl_present": (run_path / "events.jsonl").exists(),
            "artifacts_json_present": (run_path / "artifacts.json").exists(),
            "run_metadata_present": (run_path / "run_metadata.json").exists(),
            "run_config_facts_present": (run_path / "run_config_facts.json").exists(),
            "content_scan_file_count": content_scan_findings["file_count"],
            "content_scan_failure_count": len(content_scan_findings["findings"]),
            "raw_provider_artifact_count": len(raw_provider_artifacts),
            "raw_provider_redaction_failure_count": len(redaction_failures),
            "container_fact_count": len(container_fact_files),
            "source_fact_count": len(source_fact_files),
            "artifact_manifest_error_count": len(manifest_errors),
            "manifest_errors": manifest_errors[:3],
            "redaction_failures": [item for item in redaction_failures if item][:3],
            "content_scan_findings": content_scan_findings["findings"][:3],
        }
        for key, value in entry.items():
            if key.endswith("_count") and isinstance(value, int):
                totals[key] += value
        for key in (
            "events_jsonl_present",
            "artifacts_json_present",
            "run_metadata_present",
            "run_config_facts_present",
        ):
            if entry[key] is True:
                totals[key] += 1
        entries.append(entry)
    return {
        "run_count": len(entries),
        "events_jsonl_covered": int(totals["events_jsonl_present"]),
        "artifacts_json_covered": int(totals["artifacts_json_present"]),
        "run_metadata_covered": int(totals["run_metadata_present"]),
        "run_config_facts_covered": int(totals["run_config_facts_present"]),
        "content_scan_file_count": int(totals["content_scan_file_count"]),
        "content_scan_failure_count": int(totals["content_scan_failure_count"]),
        "raw_provider_artifact_count": int(totals["raw_provider_artifact_count"]),
        "raw_provider_redaction_failure_count": int(totals["raw_provider_redaction_failure_count"]),
        "container_fact_count": int(totals["container_fact_count"]),
        "source_fact_count": int(totals["source_fact_count"]),
        "artifact_manifest_error_count": int(totals["artifact_manifest_error_count"]),
        "entries": entries,
    }


def _is_raw_provider_artifact(artifact: dict[str, Any]) -> bool:
    text = " ".join(
        str(artifact.get(key, ""))
        for key in ("artifact_id", "kind", "relative_path")
    ).lower()
    return any(
        marker in text
        for marker in (
            "provider_raw",
            "raw_provider",
            "raw_request",
            "raw_response",
            "reasoning_summary",
            "reasoning_content",
        )
    )


def _run_artifact_content_findings(
    run_path: Path,
    *,
    artifact_records: list[dict[str, Any]],
    denylist: V3ContaminationDenylist,
) -> dict[str, Any]:
    files = [
        run_path / "events.jsonl",
        run_path / "artifacts.json",
        run_path / "transcript.jsonl",
        run_path / "run_metadata.json",
        run_path / "run_config_facts.json",
    ]
    for artifact in artifact_records:
        if artifact.get("kind") == "prepared_messages" or _is_raw_model_artifact(artifact):
            relative_path = Path(str(artifact.get("relative_path", "")))
            if not relative_path.is_absolute() and ".." not in relative_path.parts:
                files.append(run_path / relative_path)
    findings = []
    scanned = 0
    for path in files:
        if not path.exists() or path.is_dir():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        result = denylist.scan_payload(surface="acceptance_input", payload={"text": text})
        for finding in result.findings:
            if finding.category in {"provider_raw", "credential"}:
                findings.append(
                    {
                        "relative_path": _relative_path(path, run_path),
                        "matched_term": finding.matched_term,
                        "category": finding.category,
                    }
                )
    return {"file_count": scanned, "findings": findings}


def _is_raw_model_artifact(artifact: dict[str, Any]) -> bool:
    text = " ".join(
        str(artifact.get(key, ""))
        for key in ("artifact_id", "kind", "relative_path")
    ).lower()
    return _is_raw_provider_artifact(artifact) or "raw_replay_request" in text or "raw_replay_response" in text


def _matching_fact_files(run_path: Path, *, prefixes: tuple[str, ...]) -> list[str]:
    matches = []
    for child in run_path.glob("*.json"):
        name = child.name
        if any(name.startswith(prefix) for prefix in prefixes):
            matches.append(name)
    return sorted(matches)


def _verify_artifact_manifest_safely(run_path: Path) -> list[str]:
    from repo_harness.trajectory import verify_artifact_manifest

    return list(verify_artifact_manifest(run_path))


def _build_root_audit_report(
    *,
    format_exports: list[dict[str, Any]],
    scan_results: list[dict[str, Any]],
    binding_summary: dict[str, Any],
    artifact_audit_summary: dict[str, Any],
    preference_report: dict[str, Any],
) -> dict[str, Any]:
    failed_exports = [
        entry
        for entry in format_exports
        if entry.get("audit_status") == "failed" and int(entry.get("failed_audit_item_count", 0) or 0) > 0
    ]
    dirty_scans = [scan for scan in scan_results if scan.get("clean") is not True]
    artifact_failures = []
    if artifact_audit_summary.get("artifact_manifest_error_count", 0) > 0:
        artifact_failures.append("artifact_manifest_errors")
    if artifact_audit_summary.get("raw_provider_redaction_failure_count", 0) > 0:
        artifact_failures.append("raw_provider_redaction_failures")
    if artifact_audit_summary.get("content_scan_failure_count", 0) > 0:
        artifact_failures.append("run_artifact_content_scan_failures")
    if artifact_audit_summary.get("events_jsonl_covered", 0) < artifact_audit_summary.get("run_count", 0):
        artifact_failures.append("missing_events_jsonl")
    if artifact_audit_summary.get("artifacts_json_covered", 0) < artifact_audit_summary.get("run_count", 0):
        artifact_failures.append("missing_artifacts_json")
    checks = [
        "format_specific_export_directories_present",
        "v2_export_manifest_contract_bound",
        "v2_audit_report_contract_bound",
        "formal_data_files_hash_bound",
        "run_artifact_redaction_audit_covered",
        "v3_contamination_scans_clean",
        "v3_observation_binding_fields_present",
        "preference_compare_scope_contains_v2_and_v3_fields",
    ]
    warnings = []
    if preference_report.get("eligible_pair_count", 0) == 0:
        warnings.append("preference_pair_baseline_blocked")
    if any(int(entry.get("invalid_count", 0) or 0) for entry in format_exports):
        warnings.append("non_trainable_export_records_present")
    status = "passed"
    if failed_exports or dirty_scans or binding_summary.get("mismatched_binding_count") or artifact_failures:
        status = "failed"
    elif warnings:
        status = "passed_with_warnings"
    return {
        "schema_version": V3_EXPORT_AUDIT_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "format_export_summary": {
            "format_count": len(format_exports),
            "included_count": sum(int(entry.get("included_count", 0) or 0) for entry in format_exports),
            "filtered_count": sum(int(entry.get("filtered_count", 0) or 0) for entry in format_exports),
            "skipped_count": sum(int(entry.get("skipped_count", 0) or 0) for entry in format_exports),
            "invalid_count": sum(int(entry.get("invalid_count", 0) or 0) for entry in format_exports),
            "diagnostic_only_count": sum(int(entry.get("diagnostic_only_count", 0) or 0) for entry in format_exports),
            "audit_status_distribution": dict(Counter(str(entry.get("audit_status")) for entry in format_exports)),
        },
        "v3_contamination_scan_results": scan_results,
        "run_artifact_redaction_audit": artifact_audit_summary,
        "sample_binding_summary": binding_summary,
        "preference_pair_baseline": {
            "eligible_pair_count": preference_report.get("eligible_pair_count", 0),
            "diagnostic_pair_count": preference_report.get("diagnostic_pair_count", 0),
            "blocked_pair_count": preference_report.get("blocked_pair_count", 0),
            "blocked_reason_distribution": preference_report.get("blocked_reason_distribution", {}),
            "residual_risk": preference_report.get("residual_risk"),
        },
        "failures": [
            *[f"{entry.get('format')}:{entry.get('source_run_id')}:audit_failed" for entry in failed_exports],
            *[f"{scan.get('surface')}:{scan.get('subject')}:contamination" for scan in dirty_scans],
            *artifact_failures,
        ],
    }


def _render_root_audit_markdown(report: dict[str, Any]) -> str:
    summary = report.get("format_export_summary", {})
    lines = [
        "# V3 Export Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Format exports: `{summary.get('format_count', 0)}`",
        f"- Included: `{summary.get('included_count', 0)}`",
        f"- Filtered: `{summary.get('filtered_count', 0)}`",
        f"- Invalid: `{summary.get('invalid_count', 0)}`",
        f"- Diagnostic-only: `{summary.get('diagnostic_only_count', 0)}`",
        f"- Preference eligible pairs: `{report.get('preference_pair_baseline', {}).get('eligible_pair_count', 0)}`",
        "",
        "## Checks",
        "",
        *[f"- {check}" for check in report.get("checks", [])],
    ]
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines) + "\n"


def _inspect_format_export(root: Path, entry: dict[str, Any], failures: list[str]) -> None:
    export_dir = _inspect_artifact_ref(root, entry.get("export_dir_ref"), failures, label="export_dir_ref")
    _inspect_artifact_ref(root, entry.get("export_manifest_ref"), failures, label="export_manifest_ref")
    _inspect_artifact_ref(root, entry.get("audit_report_ref"), failures, label="audit_report_ref")
    _inspect_artifact_ref(root, entry.get("audit_report_md_ref"), failures, label="audit_report_md_ref")
    for data_ref in entry.get("data_file_refs", []):
        data_path = _inspect_artifact_ref(root, data_ref, failures, label="data_file_ref")
        if data_path and data_path.suffix == ".jsonl":
            for line_number, record in enumerate(_read_jsonl(data_path), start=1):
                if record.get("quality", {}).get("training_eligibility") != "trainable":
                    failures.append(f"{data_ref.get('relative_path')}: formal JSONL 中包含非 trainable 样本。")
                if record.get("invalid_for_training"):
                    failures.append(f"{data_ref.get('relative_path')}: formal JSONL 中包含 invalid 样本。")
                forbidden = _find_formal_training_forbidden_fields(record)
                if forbidden:
                    failures.append(
                        f"{data_ref.get('relative_path')}:{line_number}: formal JSONL 包含 evaluator/result 字段："
                        + ", ".join(forbidden[:5])
                    )
                _inspect_record_bindings(record, failures)
    if export_dir is not None:
        manifest = _read_json_for_inspect(export_dir / "export_manifest.json", failures)
        audit = _read_json_for_inspect(export_dir / "audit_report.json", failures)
        if audit.get("export_id") != manifest.get("export_id"):
            failures.append(f"{export_dir}: audit export_id 与 manifest 不一致。")
        if manifest.get("audit_report_sha256") != sha256_file(export_dir / "audit_report.json"):
            failures.append(f"{export_dir}: audit_report.json sha256 不匹配。")
        if manifest.get("audit_report_md_sha256") != sha256_file(export_dir / "audit_report.md"):
            failures.append(f"{export_dir}: audit_report.md sha256 不匹配。")


def _inspect_record_bindings(record: dict[str, Any], failures: list[str]) -> None:
    payload = record.get("payload", {})
    bindings = payload.get("v3_observation_bindings", [])
    if bindings and not isinstance(bindings, list):
        failures.append(f"{record.get('sample_id')}: v3_observation_bindings 必须是列表。")
        return
    for binding in bindings:
        missing = [
            field
            for field in [
                "prepared_messages_ref",
                "prepared_messages_sha256",
                "model_input_hash",
                "context_revision",
                "content_replacement_state_ref",
                "tool_observation_ref",
                "observation_source_event_ref",
                "observation_matches_prepared_messages",
            ]
            if binding.get(field) is None or binding.get(field) == ""
        ]
        if missing:
            failures.append(f"{record.get('sample_id')}: observation binding 缺少字段：{', '.join(missing)}")
        if binding.get("observation_matches_prepared_messages") is not True:
            failures.append(f"{record.get('sample_id')}: observation_matches_prepared_messages 不是 true。")


def _inspect_preference_report(root: Path, manifest_payload: dict[str, Any], failures: list[str]) -> None:
    report_path = _inspect_artifact_ref(
        root,
        manifest_payload.get("preference_pair_baseline_report_ref"),
        failures,
        label="preference_pair_baseline_report_ref",
    )
    if report_path is None:
        return
    report = _read_json_for_inspect(report_path, failures)
    if report.get("schema_version") != V3_PREFERENCE_BASELINE_REPORT_VERSION:
        failures.append("preference_pair_baseline_report schema_version 无效。")
    if report.get("compare_scope_contains_v2_fields") is not True:
        failures.append("preference compare scope 少于 V2 strict fields。")
    if report.get("compare_scope_contains_v3_fields") is not True:
        failures.append("preference compare scope 缺少 V3 fields。")
    if (
        report.get("eligible_pair_count", 0) == 0
        and report.get("diagnostic_pair_count", 0) == 0
        and not report.get("blocked_reason_distribution")
    ):
        failures.append("没有合格或 diagnostic preference pair 时必须记录 blocked_reason_distribution。")


def _inspect_root_report(report_payload: dict[str, Any], failures: list[str], *, assert_clean: bool) -> None:
    if report_payload.get("sample_binding_summary", {}).get("observation_matches_prepared_messages") is not True:
        failures.append("sample binding summary 显示 observation 不匹配 prepared messages。")
    artifact_audit = report_payload.get("run_artifact_redaction_audit", {})
    if not isinstance(artifact_audit, dict):
        failures.append("run_artifact_redaction_audit 缺失或不是 object。")
    else:
        if artifact_audit.get("artifact_manifest_error_count", 0) > 0:
            failures.append("run artifact audit 存在 artifact manifest 错误。")
        if artifact_audit.get("raw_provider_redaction_failure_count", 0) > 0:
            failures.append("run artifact audit 存在 raw provider redaction 错误。")
        if artifact_audit.get("content_scan_failure_count", 0) > 0:
            failures.append("run artifact audit 存在 provider raw 或 credential 内容扫描错误。")
        if artifact_audit.get("events_jsonl_covered", 0) < artifact_audit.get("run_count", 0):
            failures.append("run artifact audit 未覆盖所有 events.jsonl。")
        if artifact_audit.get("artifacts_json_covered", 0) < artifact_audit.get("run_count", 0):
            failures.append("run artifact audit 未覆盖所有 artifacts.json。")
    for scan in report_payload.get("v3_contamination_scan_results", []):
        if scan.get("clean") is not True:
            failures.append(f"V3 contamination scan failed: {scan.get('surface')}:{scan.get('subject')}")
    if assert_clean and report_payload.get("status") == "failed":
        failures.append("V3 export audit status is failed。")


def _latest_export_dir(exports_dir: Path, *, export_format: str) -> Path:
    export_dirs = [
        child
        for child in exports_dir.iterdir()
        if child.is_dir()
        and (child / "export_manifest.json").exists()
        and _read_json(child / "export_manifest.json").get("format") == export_format
    ]
    if not export_dirs:
        raise ExportError(f"没有找到 {export_format} export directory：{exports_dir}")
    return max(export_dirs, key=lambda path: path.stat().st_mtime_ns)


def _prepared_message_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _read_json(run_path / "artifacts.json") if (run_path / "artifacts.json").exists() else {}
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "prepared_messages"
    ]


def _artifact_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
) -> dict[str, Any]:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = sha256_file(path)
        size_bytes = path.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status="not_required",
        retention_policy="keep",
    ).model_dump(mode="json")


def _inspect_artifact_ref(root: Path, ref_payload: Any, failures: list[str], *, label: str) -> Path | None:
    if not isinstance(ref_payload, dict):
        failures.append(f"{label} 缺失或不是 object。")
        return None
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except ValidationError as exc:
        failures.append(f"{label} schema 无效：{exc}")
        return None
    relative = Path(ref.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        failures.append(f"{label} relative_path 必须留在 V3 export audit 目录内：{ref.relative_path}")
        return None
    path = root / relative
    if not path.exists():
        failures.append(f"{label} 路径不存在：{ref.relative_path}")
        return None
    actual_sha = compute_source_tree_hash(path) if path.is_dir() else sha256_file(path)
    if actual_sha != ref.sha256:
        failures.append(f"{label} sha256 不匹配：{ref.relative_path}")
    if not path.is_dir() and path.stat().st_size != ref.size_bytes:
        failures.append(f"{label} size_bytes 不匹配：{ref.relative_path}")
    return path


def _inspect_manifest_bound_audit_report(
    root: Path,
    manifest_payload: dict[str, Any],
    audit_path: Path,
    failures: list[str],
) -> None:
    ref_payload = manifest_payload.get("audit_report_ref")
    if not isinstance(ref_payload, dict):
        return
    expected_relative = ref_payload.get("relative_path")
    if not isinstance(expected_relative, str):
        failures.append("audit_report_ref.relative_path 缺失。")
        return
    try:
        actual_relative = audit_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        failures.append("命令行 audit_report 必须位于 V3 export audit 目录内。")
        return
    if actual_relative != expected_relative:
        failures.append("命令行 audit_report 必须与 manifest audit_report_ref 指向同一文件。")


def _append_command_log(
    path: Path,
    *,
    command_name: str,
    argv: list[str],
    started_at: str,
    input_paths: list[Path],
    output_paths: list[Path],
    exit_code: int,
) -> None:
    entry = CommandLogEntry(
        command_name=command_name,
        argv=argv,
        cwd=Path.cwd().as_posix(),
        input_refs=[
            _artifact_ref(item, base_dir=Path.cwd(), artifact_id=f"{command_name}_input_{index}", kind=_kind_for_path(item))
            for index, item in enumerate(input_paths, start=1)
            if item.exists()
        ],
        output_refs=[
            _artifact_ref(item, base_dir=Path.cwd(), artifact_id=f"{command_name}_output_{index}", kind=_kind_for_path(item))
            for index, item in enumerate(output_paths, start=1)
            if item.exists()
        ],
        exit_code=exit_code,
        tool_or_cli_version=f"repo-harness {__version__}",
        started_at=started_at,
        finished_at=_utc_timestamp(),
    )
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")


def _kind_for_path(path: Path) -> str:
    if path.is_dir():
        return "directory"
    return path.suffix.lower().lstrip(".") or "file"


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
