"""第二版导出目录、manifest 和文件哈希辅助函数。"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.export.schemas import ExportDataFile, ExportManifest, ExportPolicy
from repo_harness.schema_base import stable_hash

EXPORTER_VERSION = "repo_harness_exporter_v2_v0"

DATA_FILE_NAMES = {
    "sft_jsonl": "data.sft.jsonl",
    "rl_jsonl": "data.rl.jsonl",
    "preference_jsonl": "data.preference.jsonl",
    "provider_reasoning_trace_training_export": "data.provider_reasoning_trace.jsonl",
}

CONVENIENCE_FILE_NAMES = {
    "sft_jsonl": "sft.jsonl",
    "rl_jsonl": "rl.jsonl",
    "preference_jsonl": "preference.jsonl",
    "provider_reasoning_trace_training_export": "provider_reasoning_trace_training_export.jsonl",
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_export_id(
    export_format: str,
    *,
    source_run_dirs: list[str],
    generated_at: str,
) -> str:
    short_format = {
        "sft_jsonl": "sft",
        "rl_jsonl": "rl",
        "preference_jsonl": "preference",
        "provider_reasoning_trace_training_export": "provider_reasoning_trace",
    }.get(export_format, export_format)
    compact_time = generated_at.replace("-", "").replace(":", "").replace("+00:00", "Z")
    compact_time = compact_time.replace(".", "").replace("Z", "Z")
    digest = stable_hash(
        {
            "format": export_format,
            "source_run_dirs": source_run_dirs,
            "generated_at": generated_at,
        }
    )[:10]
    return f"{short_format}_{compact_time}_{digest}"


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    digest = sha256_bytes(text.encode("utf-8"))
    os.replace(tmp_path, path)
    return digest


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    digest = sha256_bytes(text.encode("utf-8"))
    os.replace(tmp_path, path)
    return digest


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    digest = sha256_file(tmp_path)
    os.replace(tmp_path, path)
    return digest


def build_data_file(path: Path, *, relative_path: str, record_count: int) -> ExportDataFile:
    return ExportDataFile(
        relative_path=relative_path,
        sha256=sha256_file(path),
        record_count=record_count,
    )


def build_export_manifest(
    *,
    export_id: str,
    export_format: str,
    source_run_dirs: list[str],
    command_args: dict[str, Any],
    data_files: list[ExportDataFile],
    generated_at: str,
    audit_report_path: str,
    audit_report_sha256: str,
    audit_report_md_path: str,
    audit_report_md_sha256: str,
    record_count: int,
    included_count: int,
    filtered_count: int,
    skipped_count: int,
    invalid_count: int,
    diagnostic_only_count: int,
    policy: ExportPolicy,
) -> ExportManifest:
    return ExportManifest(
        export_id=export_id,
        format=export_format,  # type: ignore[arg-type]
        export_policy_version=policy.export_policy_version,
        source_run_dirs=source_run_dirs,
        command_args=command_args,
        data_files=data_files,
        record_count=record_count,
        included_count=included_count,
        filtered_count=filtered_count,
        skipped_count=skipped_count,
        invalid_count=invalid_count,
        diagnostic_only_count=diagnostic_only_count,
        generated_at=generated_at,
        exporter_version=EXPORTER_VERSION,
        audit_report_path=audit_report_path,
        audit_report_sha256=audit_report_sha256,
        audit_report_md_path=audit_report_md_path,
        audit_report_md_sha256=audit_report_md_sha256,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
