"""规范导出目录只读检查。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from repo_harness.errors import ExportError
from repo_harness.export.manifest import sha256_file


def inspect_export(
    export_path: str | Path,
    *,
    all_exports: bool = False,
    export_format: str | None = None,
    assert_clean: bool = False,
    require_trainable_samples: bool = False,
    allow_provider_reasoning_trace_diagnostic_only: bool = False,
) -> str:
    root = Path(export_path)
    export_dirs = _export_dirs(root, all_exports=all_exports)
    if export_format is not None:
        export_dirs = [
            export_dir
            for export_dir in export_dirs
            if _read_json(export_dir / "export_manifest.json").get("format") == export_format
        ]
    if not export_dirs:
        raise ExportError(f"没有找到规范导出目录：{root}")

    lines = [f"Export path: {root}", f"Export directories: {len(export_dirs)}"]
    total_trainable = 0
    failures: list[str] = []
    for export_dir in export_dirs:
        result = _inspect_one(
            export_dir,
            allow_provider_reasoning_trace_diagnostic_only=(
                allow_provider_reasoning_trace_diagnostic_only
            ),
        )
        lines.extend(result["lines"])
        total_trainable += result["trainable_count"]
        failures.extend(result["failures"])

    if require_trainable_samples and total_trainable <= 0:
        failures.append("require_trainable_samples requested but no trainable records were found")
    if assert_clean and failures:
        raise ExportError("; ".join(failures))
    if failures:
        lines.append("Failures:")
        lines.extend(f"- {failure}" for failure in failures)
    else:
        lines.append("Inspect export: clean")
    return "\n".join(lines)


def _export_dirs(path: Path, *, all_exports: bool) -> list[Path]:
    if (path / "export_manifest.json").exists():
        return [path]
    if all_exports:
        return sorted(
            child
            for child in path.iterdir()
            if child.is_dir() and (child / "export_manifest.json").exists()
        )
    if path.is_dir():
        dirs = sorted(
            child
            for child in path.iterdir()
            if child.is_dir() and (child / "export_manifest.json").exists()
        )
        if len(dirs) == 1:
            return dirs
    return []


def _inspect_one(
    export_dir: Path,
    *,
    allow_provider_reasoning_trace_diagnostic_only: bool = False,
) -> dict:
    failures: list[str] = []
    manifest_path = export_dir / "export_manifest.json"
    audit_path = export_dir / "audit_report.json"
    audit_md_path = export_dir / "audit_report.md"
    manifest = _read_json(manifest_path)
    audit = _read_json(audit_path)
    lines = [
        f"- Export id: {manifest.get('export_id')}",
        f"  Format: {manifest.get('format')}",
        f"  Audit status: {audit.get('status')}",
        f"  Included: {manifest.get('included_count', 0)}",
        f"  Invalid: {manifest.get('invalid_count', 0)}",
        f"  Diagnostic-only: {manifest.get('diagnostic_only_count', 0)}",
        f"  Skipped: {manifest.get('skipped_count', 0)}",
    ]
    if manifest.get("audit_report_path") != "audit_report.json":
        failures.append(f"{export_dir.name}: manifest audit_report_path mismatch")
    if not audit_path.exists() or sha256_file(audit_path) != manifest.get("audit_report_sha256"):
        failures.append(f"{export_dir.name}: audit_report.json sha256 mismatch")
    if manifest.get("audit_report_md_path") != "audit_report.md":
        failures.append(f"{export_dir.name}: manifest audit_report_md_path mismatch")
    if not audit_md_path.exists() or sha256_file(audit_md_path) != manifest.get("audit_report_md_sha256"):
        failures.append(f"{export_dir.name}: audit_report.md sha256 mismatch")
    if audit.get("export_id") != manifest.get("export_id"):
        failures.append(f"{export_dir.name}: audit export_id mismatch")
    provider_trace_diagnostic_only = (
        allow_provider_reasoning_trace_diagnostic_only
        and manifest.get("format") == "provider_reasoning_trace_training_export"
        and audit.get("format") == "provider_reasoning_trace_training_export"
        and _provider_reasoning_trace_failure_is_diagnostic_only(audit)
    )
    if audit.get("status") == "failed" and not provider_trace_diagnostic_only:
        failures.append(f"{export_dir.name}: audit_report status is failed")
    for sample in audit.get("samples", []):
        for item in sample.get("audit_items", []):
            if item.get("status") == "failed":
                failures.append(f"{export_dir.name}: failed audit item {item.get('name')}")

    trainable_count = 0
    for data_file in manifest.get("data_files", []):
        relative_path = data_file.get("relative_path")
        if not isinstance(relative_path, str):
            failures.append(f"{export_dir.name}: data file missing relative_path")
            continue
        path = export_dir / relative_path
        if not path.exists():
            failures.append(f"{export_dir.name}: data file missing: {relative_path}")
            continue
        if sha256_file(path) != data_file.get("sha256"):
            failures.append(f"{export_dir.name}: data file sha256 mismatch: {relative_path}")
        if path.suffix == ".jsonl":
            records = _read_jsonl(path)
            if len(records) != data_file.get("record_count"):
                failures.append(f"{export_dir.name}: data file record_count mismatch: {relative_path}")
            for record in records:
                eligibility = record.get("quality", {}).get("training_eligibility")
                if eligibility != "trainable":
                    failures.append(f"{export_dir.name}: non-trainable sample in formal data file")
                if record.get("invalid_for_training"):
                    failures.append(f"{export_dir.name}: invalid sample in formal data file")
            text = path.read_text(encoding="utf-8")
            if _contains_hidden_or_local_text(text):
                failures.append(f"{export_dir.name}: hidden field or local path found in data file")
            trainable_count += len(records)

    for sample in audit.get("samples", []):
        if sample.get("training_eligibility") == "invalid" and sample.get("line_number"):
            failures.append(f"{export_dir.name}: invalid sample has a formal data line")
    return {"lines": lines, "failures": failures, "trainable_count": trainable_count}


def _provider_reasoning_trace_failure_is_diagnostic_only(audit: dict) -> bool:
    samples = audit.get("samples", [])
    if not isinstance(samples, list) or not samples:
        return False
    for sample in samples:
        if not isinstance(sample, dict):
            return False
        for item in sample.get("audit_items", []):
            if isinstance(item, dict) and item.get("status") == "failed":
                return False
        eligibility = sample.get("training_eligibility")
        if eligibility == "trainable":
            continue
        if eligibility in {"diagnostic_only", "skipped"}:
            continue
        if eligibility != "invalid":
            return False
        if not _provider_reasoning_trace_diagnostic_invalid_reason(
            str(sample.get("invalid_reason") or "")
        ):
            return False
    return True


def _provider_reasoning_trace_diagnostic_invalid_reason(reason: str) -> bool:
    if reason in {"failed", "invalid_task", "flaky_task", "interrupted", "inconclusive"}:
        return True
    if reason.startswith("agent_stop_reason:"):
        return True
    return False


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ExportError(f"导出文件不可读：{path}") from exc


def _read_jsonl(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ExportError(f"JSONL 解析失败：{path}:{line_number}") from exc
    return records


def _contains_hidden_or_local_text(text: str) -> bool:
    lowered = text.lower()
    blocked = [
        "gold_patch",
        "hidden_tests",
        "fail_to_pass_tests",
        "pass_to_pass_tests",
        "baseline_raw_log",
        "raw_response",
        "raw_request_body",
        "reasoning_summary",
        "authorization",
    ]
    if any(marker in lowered for marker in blocked):
        return True
    return bool(re.search(r"(?<![A-Za-z0-9_])/(Users|private|var/folders)/", text))
