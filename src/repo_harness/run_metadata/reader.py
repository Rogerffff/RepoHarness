"""第二版 run metadata 只读读取和检查。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunMetadataInspection:
    run_config_facts_status: str
    run_metadata_status: str
    metadata_source: str
    provider: str | None = None
    model_id: str | None = None
    scaffold_id: str | None = None
    scaffold_version: str | None = None
    tool_schema_snapshot_status: str = "missing"
    export_audit_status: str = "not_generated"
    failure_diagnostics: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


def inspect_run_metadata(run_dir: str | Path) -> RunMetadataInspection:
    run_path = Path(run_dir)
    config_path = run_path / "run_config_facts.json"
    metadata_path = run_path / "run_metadata.json"

    config_payload, config_error = _read_json(config_path)
    metadata_payload, metadata_error = _read_json(metadata_path)
    diagnostics: list[str] = []

    if config_error:
        diagnostics.append(f"run_config_facts.json is corrupt: {config_error}")
    if metadata_error:
        diagnostics.append(f"run_metadata.json is corrupt: {metadata_error}")

    if config_error:
        config_status = "invalid"
    elif config_payload is None:
        config_status = "missing"
    else:
        config_status = "ok"

    if metadata_error:
        metadata_status = "invalid"
        metadata_source = "invalid"
    elif metadata_payload is None:
        if not config_path.exists():
            metadata_status = "legacy_missing"
            metadata_source = "legacy_inferred"
        else:
            metadata_status = "missing"
            metadata_source = "missing"
    else:
        metadata_status = "invalid" if metadata_error else "ok"
        metadata_source = str(metadata_payload.get("metadata_source", "v2"))

    if metadata_payload and config_payload:
        ref = metadata_payload.get("run_config_facts_ref", {})
        expected_sha = ref.get("sha256")
        if expected_sha and expected_sha != _sha256_file(config_path):
            metadata_status = "invalid"
            diagnostics.append("run_metadata.json 中的 run_config_facts_ref sha256 不匹配。")

    source = metadata_payload or config_payload or {}
    provider = _first_text(source, ["provider"], fallback=_first_text(config_payload or {}, ["provider"]))
    model_id = _first_text(source, ["model_id"], fallback=_first_text(config_payload or {}, ["model_id"]))
    scaffold_id = _first_text(
        source,
        ["scaffold_id"],
        fallback=_first_text(config_payload or {}, ["scaffold_id"]),
    )
    scaffold_version = _first_text(
        source,
        ["scaffold_version"],
        fallback=_first_text(config_payload or {}, ["scaffold_version"]),
    )
    tool_protocol = (metadata_payload or {}).get("tool_protocol") or (config_payload or {}).get(
        "tool_protocol"
    )
    return RunMetadataInspection(
        run_config_facts_status=config_status,
        run_metadata_status=metadata_status,
        metadata_source=metadata_source,
        provider=provider,
        model_id=model_id,
        scaffold_id=scaffold_id,
        scaffold_version=scaffold_version,
        tool_schema_snapshot_status=_tool_schema_snapshot_status(run_path, tool_protocol),
        export_audit_status=_export_audit_status(run_path),
        failure_diagnostics=_failure_diagnostics(metadata_payload or {}),
        diagnostics=diagnostics,
    )


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (json.JSONDecodeError, OSError) as exc:
        return None, str(exc)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_text(payload: dict[str, Any], keys: list[str], fallback: str | None = None) -> str | None:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return fallback
        current = current.get(key)
    return current if isinstance(current, str) and current else fallback


def _tool_schema_snapshot_status(run_path: Path, tool_protocol: Any) -> str:
    if not isinstance(tool_protocol, dict):
        return "missing"
    ref = tool_protocol.get("tool_schema_snapshot_ref")
    if not isinstance(ref, dict):
        return "missing"
    protocol_snapshot_sha = tool_protocol.get("tool_schema_snapshot_sha256")
    if not isinstance(protocol_snapshot_sha, str):
        return "invalid"
    artifact_id = ref.get("artifact_id")
    relative_path = ref.get("relative_path")
    if not isinstance(artifact_id, str) or not isinstance(relative_path, str):
        return "invalid"
    manifest_payload, manifest_error = _read_json(run_path / "artifacts.json")
    if manifest_error or manifest_payload is None:
        return "invalid"
    artifacts = manifest_payload.get("artifacts", [])
    manifest_ref = next(
        (
            artifact
            for artifact in artifacts
            if isinstance(artifact, dict) and artifact.get("artifact_id") == artifact_id
        ),
        None,
    )
    if manifest_ref is None:
        return "invalid"
    artifact_path = run_path / relative_path
    if not artifact_path.exists():
        return "invalid"
    artifact_file_sha = _sha256_file(artifact_path)
    ref_sha = ref.get("sha256")
    if not isinstance(ref_sha, str) or ref_sha != artifact_file_sha:
        return "invalid"
    expected_sha = manifest_ref.get("sha256")
    if not isinstance(expected_sha, str) or expected_sha != artifact_file_sha:
        return "invalid"
    snapshot_payload, snapshot_error = _read_json(artifact_path)
    if snapshot_error or snapshot_payload is None:
        return "invalid"
    snapshot_sha = snapshot_payload.get("snapshot_sha256")
    if not isinstance(snapshot_sha, str) or snapshot_sha != protocol_snapshot_sha:
        return "invalid"
    return "ok"


def _export_audit_status(run_path: Path) -> str:
    exports_dir = run_path / "exports"
    if not exports_dir.exists():
        return "not_generated"
    audit_reports = list(exports_dir.glob("**/audit_report.json"))
    if not audit_reports:
        return "not_generated"
    return "generated"


def _failure_diagnostics(metadata_payload: dict[str, Any]) -> list[str]:
    diagnostics = []
    for item in metadata_payload.get("failure_diagnostics", []):
        if not isinstance(item, dict):
            continue
        failure_type = item.get("failure_type", "unknown_failure")
        category = item.get("failure_category", "unknown_failure")
        recoverable = item.get("recoverable", False)
        diagnostics.append(f"{category}:{failure_type}:recoverable={recoverable}")
    return diagnostics
