"""Tool result artifact persistence and model-visible recovery helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from repo_harness.context.schemas import ToolResultArtifactRecord
from repo_harness.trajectory import ArtifactRef, RunRecorder

DEFAULT_TOOL_RESULT_PREVIEW_CHARS = 2000
DEFAULT_TOOL_RESULT_READ_LIMIT = 8000
MAX_TOOL_RESULT_READ_LIMIT = 50000


class ToolResultArtifactError(ValueError):
    """Raised when a model asks for a tool result artifact it cannot recover."""


@dataclass
class ToolResultArtifactIndex:
    """Positive allowlist of tool result artifacts recoverable in one run."""

    run_dir: Path
    records_by_artifact_id: dict[str, ToolResultArtifactRecord] = field(default_factory=dict)

    def add(self, record: ToolResultArtifactRecord) -> ToolResultArtifactRecord:
        self.records_by_artifact_id[record.artifact_id] = record
        return record

    def unlock_after_provider_commit(self, artifact_id: str) -> ToolResultArtifactRecord:
        record = self._record(artifact_id)
        unlocked = record.model_copy(update={"recovery_unlocked_after_provider_commit": True})
        return self.add(ToolResultArtifactRecord.model_validate(unlocked.model_dump(mode="json")))

    def read(self, artifact_id: str, *, offset: int = 0, limit: int = DEFAULT_TOOL_RESULT_READ_LIMIT) -> dict[str, Any]:
        if offset < 0:
            raise ToolResultArtifactError("offset must be >= 0.")
        if limit <= 0:
            raise ToolResultArtifactError("limit must be > 0.")
        limit = min(limit, MAX_TOOL_RESULT_READ_LIMIT)
        record = self._record(artifact_id)
        if not record.model_visible_recoverable:
            raise ToolResultArtifactError(
                "tool result artifact is not unlocked for model recovery."
            )
        path = _safe_artifact_path(self.run_dir, record.artifact_ref)
        text = path.read_text(encoding="utf-8")
        digest = _sha256_text(text)
        if digest != record.content_sha256 or len(text) != record.size_chars:
            raise ToolResultArtifactError(
                "stored tool result artifact content does not match the registered hash."
            )
        page = text[offset : offset + limit]
        next_offset = offset + len(page) if offset + len(page) < len(text) else None
        return {
            "artifact_id": record.artifact_id,
            "tool_result_id": record.tool_result_id,
            "tool_call_id": record.tool_call_id,
            "tool_name": record.tool_name,
            "offset": offset,
            "limit": limit,
            "content": page,
            "next_offset": next_offset,
            "size_chars": len(text),
            "content_sha256": digest,
            "model_visible_recoverable": record.model_visible_recoverable,
        }

    def _record(self, artifact_id: str) -> ToolResultArtifactRecord:
        if not _safe_artifact_id(artifact_id):
            raise ToolResultArtifactError("artifact_id must be an opaque tool result artifact id.")
        record = self.records_by_artifact_id.get(artifact_id)
        if record is None:
            raise ToolResultArtifactError("artifact_id is not registered in ToolResultArtifactIndex.")
        return record


def persist_tool_result_content(
    *,
    recorder: RunRecorder,
    tool_result_id: str,
    tool_call_id: str,
    tool_name: str | None,
    content: str,
    publishable_after_visibility_scan: bool = False,
    contamination_scan_status: str = "not_scanned",
) -> ToolResultArtifactRecord:
    ref = recorder.write_artifact(
        "tool_result_original_content",
        content,
        {"budget_policy": "preserve_json", "redaction_status": contamination_scan_status},
    )
    if ref.sha256 != _sha256_text(content) or ref.size_bytes != len(content.encode("utf-8")):
        raise ToolResultArtifactError(
            "stored tool result artifact was not preserved exactly."
        )
    return ToolResultArtifactRecord(
        artifact_id=ref.artifact_id,
        tool_result_id=tool_result_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        content_sha256=_sha256_text(content),
        size_chars=len(content),
        artifact_ref=ref,
        publishable_after_visibility_scan=publishable_after_visibility_scan,
        recovery_unlocked_after_provider_commit=False,
        contamination_scan_status=contamination_scan_status,  # type: ignore[arg-type]
    )


def build_persisted_tool_result_preview(
    record: ToolResultArtifactRecord,
    original_content: str,
    *,
    preview_chars: int = DEFAULT_TOOL_RESULT_PREVIEW_CHARS,
) -> str:
    size_kb = record.size_chars / 1024
    if not record.publishable_after_visibility_scan:
        return (
            "<persisted-output>\n"
            f"Output too large ({size_kb:.1f} KB). Full output was stored but is not "
            "available for model recovery because visibility scanning did not pass.\n"
            "</persisted-output>"
        )
    preview = original_content[:preview_chars]
    suffix = "\n...[preview truncated]" if len(original_content) > preview_chars else ""
    return (
        "<persisted-output>\n"
        f"Output too large ({size_kb:.1f} KB). Full output saved as tool result artifact.\n"
        f"artifact_id: {record.artifact_id}\n"
        f"tool_result_id: {record.tool_result_id}\n"
        f"sha256: {record.content_sha256}\n"
        f"recovery_call: read_tool_result_artifact(artifact_id={record.artifact_id!r}, offset=0, limit={DEFAULT_TOOL_RESULT_READ_LIMIT})\n\n"
        "recovery_hint: Use read_tool_result_artifact only if the full output is needed for the current task.\n\n"
        f"Preview (first {min(preview_chars, len(original_content))} chars):\n"
        f"{preview}{suffix}\n"
        "</persisted-output>"
    )


def read_tool_result_artifact(
    index: ToolResultArtifactIndex,
    *,
    artifact_id: str,
    offset: int = 0,
    limit: int = DEFAULT_TOOL_RESULT_READ_LIMIT,
) -> dict[str, Any]:
    return index.read(artifact_id, offset=offset, limit=limit)


def _safe_artifact_id(artifact_id: str) -> bool:
    if not artifact_id or artifact_id in {".", ".."}:
        return False
    if "/" in artifact_id or "\\" in artifact_id:
        return False
    return ".." not in PurePosixPath(artifact_id).parts


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_artifact_path(run_dir: Path, ref: ArtifactRef) -> Path:
    relative = PurePosixPath(ref.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ToolResultArtifactError("artifact relative path is not safe.")
    run_root = run_dir.resolve()
    path = (run_root / Path(relative.as_posix())).resolve()
    if run_root not in (path, *path.parents):
        raise ToolResultArtifactError("artifact path escapes run directory.")
    if not path.exists():
        raise ToolResultArtifactError("artifact file is missing.")
    return path
