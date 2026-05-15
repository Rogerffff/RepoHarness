"""RunRecorder、JSONL 记录和 artifact manifest。"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from repo_harness.errors import RepoHarnessError
from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import SCHEMA_VERSION
from repo_harness.trajectory.schemas import ArtifactRef, TrajectoryEvent, TranscriptRecord

RunStatus = Literal["RUNNING", "FINALIZED", "INTERRUPTED", "CORRUPT_PARTIAL"]
RecorderRunMode = Literal["full_audit", "training_fast", "training_debug"]
RawArtifactRetention = Literal["keep", "projection"]
PreparedMessagesRetention = Literal["keep", "keep_export_audit_compat"]
ReasoningTraceRetention = Literal["keep", "hash_only"]

RETENTION_FACTS_SCHEMA_VERSION = "repo_harness_artifact_retention_facts_v0"
PROFILE_FACT_ARTIFACT_KINDS = {
    "artifact_retention_facts",
    "artifact_projection_facts",
}
PREPARED_MESSAGES_KIND = "prepared_messages"


class RunRecorderError(RepoHarnessError):
    """RunRecorder 读写失败。"""


class RecorderProfile(StrictBaseModel):
    """Artifact retention policy selected by RepoHarness run_mode."""

    schema_version: str = "repo_harness_recorder_profile_v0"
    mode: RecorderRunMode = "full_audit"
    save_raw_provider_request: bool = True
    save_raw_provider_response: bool = True
    save_reasoning_trace: bool = True
    save_prepared_messages: bool = True
    raw_artifact_retention: RawArtifactRetention = "keep"
    prepared_messages_retention: PreparedMessagesRetention = "keep"
    reasoning_trace_retention: ReasoningTraceRetention = "keep"
    artifact_compression: str = "none"
    artifact_sampling_policy: str = "none"
    raw_artifact_preview_chars: int = Field(default=0, ge=0)
    critical_artifact_kinds: list[str] = Field(
        default_factory=lambda: [
            "artifact_manifest",
            "content_replacement_state",
            "events",
            "final_verifier",
            "metrics",
            "patch",
            "prepared_messages",
            "reward_metadata",
            "run_metadata",
            "timing_summary",
            "trajectory_facts",
            "transcript",
            "verifier_result",
        ]
    )

    @classmethod
    def for_run_mode(cls, mode: RecorderRunMode | str | None) -> "RecorderProfile":
        selected = mode or "full_audit"
        if selected == "full_audit":
            return cls(mode="full_audit", raw_artifact_preview_chars=0)
        if selected == "training_fast":
            return cls(
                mode="training_fast",
                save_raw_provider_request=False,
                save_raw_provider_response=False,
                save_reasoning_trace=False,
                save_prepared_messages=True,
                raw_artifact_retention="projection",
                prepared_messages_retention="keep_export_audit_compat",
                reasoning_trace_retention="hash_only",
                raw_artifact_preview_chars=0,
            )
        if selected == "training_debug":
            return cls(
                mode="training_debug",
                save_raw_provider_request=False,
                save_raw_provider_response=False,
                save_reasoning_trace=False,
                save_prepared_messages=True,
                raw_artifact_retention="projection",
                prepared_messages_retention="keep",
                reasoning_trace_retention="hash_only",
                artifact_sampling_policy="debug_projection",
                raw_artifact_preview_chars=2048,
            )
        raise RunRecorderError(f"unknown recorder run_mode: {selected}")

    @model_validator(mode="after")
    def validate_run_mode_safety(self) -> "RecorderProfile":
        if self.mode == "training_fast":
            if self.save_raw_provider_request or self.save_raw_provider_response:
                raise ValueError("training_fast recorder profile must not save full raw provider payloads")
            if self.save_reasoning_trace:
                raise ValueError("training_fast recorder profile must not save plaintext reasoning trace")
            if self.raw_artifact_retention != "projection":
                raise ValueError("training_fast recorder profile must use raw artifact projection")
            if self.reasoning_trace_retention != "hash_only":
                raise ValueError("training_fast recorder profile must keep reasoning trace hash-only")
        if self.mode == "training_debug":
            if self.save_raw_provider_request or self.save_raw_provider_response:
                raise ValueError("training_debug recorder profile must not save full raw provider payloads")
            if self.save_reasoning_trace:
                raise ValueError("training_debug recorder profile must not save plaintext reasoning trace by default")
            if self.raw_artifact_retention != "projection":
                raise ValueError("training_debug recorder profile must use raw artifact projection")
            if self.reasoning_trace_retention != "hash_only":
                raise ValueError("training_debug recorder profile must keep reasoning trace hash-only by default")
        return self


@dataclass(frozen=True)
class _RetentionRewrite:
    artifact_kind: str
    data: bytes | str | Path
    metadata: dict[str, Any]
    event_data: dict[str, Any]


class RunRecorder:
    """统一写入 transcript、events 和 artifact manifest。"""

    def __init__(
        self,
        run_id: str,
        run_dir: str | Path,
        *,
        task_id: str | None = None,
        max_artifact_bytes: int | None = None,
        recorder_profile: RecorderProfile | Mapping[str, Any] | RecorderRunMode | None = None,
    ) -> None:
        self.run_id = run_id
        self.task_id = task_id
        if max_artifact_bytes is not None and max_artifact_bytes <= 0:
            raise RunRecorderError("max_artifact_bytes 必须为正数。")
        self.max_artifact_bytes = max_artifact_bytes
        self.recorder_profile = _coerce_recorder_profile(recorder_profile)
        self.run_dir = Path(run_dir)
        self.artifact_dir = self.run_dir / "artifacts"
        self.transcript_path = self.run_dir / "transcript.jsonl"
        self.events_path = self.run_dir / "events.jsonl"
        self.manifest_path = self.run_dir / "artifacts.json"
        self.status_path = self.run_dir / "run_status.json"
        self.summary_path = self.run_dir / "summary.md"
        self.lock_path = self.run_dir / "run.lock"

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        existing_status = self._read_status()
        if existing_status == "FINALIZED":
            raise RunRecorderError(f"run directory 已经 FINALIZED，不能重新打开写入：{self.run_dir}")
        self._acquire_lock()
        self._ensure_jsonl_files()
        self._artifact_counter = self._load_manifest_counter()
        self._event_counter = _count_jsonl_records(self.events_path)
        self._transcript_counter = _count_jsonl_records(self.transcript_path)
        if not self.status_path.exists():
            self._write_status("RUNNING")
        if not self.manifest_path.exists():
            self._write_manifest([])

    def _acquire_lock(self) -> None:
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RunRecorderError(f"run directory 已被写入进程锁定：{self.run_dir}") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(str(os.getpid()))

    def _ensure_jsonl_files(self) -> None:
        self.transcript_path.touch(exist_ok=True)
        self.events_path.touch(exist_ok=True)

    def close(self) -> None:
        if self.lock_path.exists():
            self.lock_path.unlink()

    def __enter__(self) -> "RunRecorder":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def next_event_id(self, prefix: str = "event") -> str:
        self._event_counter += 1
        return f"{self.run_id}_{prefix}_{self._event_counter:06d}"

    def next_record_id(self, prefix: str = "record") -> str:
        self._transcript_counter += 1
        return f"{self.run_id}_{prefix}_{self._transcript_counter:06d}"

    def append_event(self, event: TrajectoryEvent | Mapping[str, Any]) -> TrajectoryEvent:
        try:
            parsed = event if isinstance(event, TrajectoryEvent) else TrajectoryEvent.model_validate(event)
        except ValidationError as exc:
            raise RunRecorderError("event schema 校验失败") from exc
        _append_jsonl(self.events_path, parsed.model_dump(mode="json"))
        return parsed

    def append_transcript(
        self, record: TranscriptRecord | Mapping[str, Any]
    ) -> TranscriptRecord:
        try:
            parsed = (
                record if isinstance(record, TranscriptRecord) else TranscriptRecord.model_validate(record)
            )
        except ValidationError as exc:
            raise RunRecorderError("transcript record schema 校验失败") from exc
        _append_jsonl(self.transcript_path, parsed.model_dump(mode="json"))
        return parsed

    def write_artifact(
        self,
        kind: str,
        data: bytes | str | Path,
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        metadata = dict(metadata or {})
        explicit_created_by_event_id = metadata.get("created_by_event_id")
        created_by_event_id = explicit_created_by_event_id or self.next_event_id("artifact")
        artifact_kind = kind
        retention_rewrite = self._retention_rewrite(kind, data, metadata)
        retention_event_data: dict[str, Any] | None = None
        if retention_rewrite is not None:
            artifact_kind = retention_rewrite.artifact_kind
            data = retention_rewrite.data
            metadata = retention_rewrite.metadata
            retention_event_data = retention_rewrite.event_data
        else:
            retention_event_data = self._retention_event_for_complete_artifact(kind, data, metadata)
        self._artifact_counter += 1
        artifact_id = f"{self.run_id}_artifact_{self._artifact_counter:06d}"
        suffix = _artifact_suffix(data, metadata)
        original_size_bytes = _artifact_size_bytes(data)
        budget_policy = str(metadata.get("budget_policy", "truncate"))
        preserve_artifact = budget_policy == "preserve_json"
        oversized = (
            self.max_artifact_bytes is not None
            and original_size_bytes > self.max_artifact_bytes
        )
        truncated = (
            oversized
            and not preserve_artifact
        )
        if truncated:
            if suffix == ".json" and budget_policy == "truncate_json":
                data = _truncate_json_artifact_data(
                    kind=artifact_kind,
                    original_size_bytes=original_size_bytes,
                    max_bytes=self.max_artifact_bytes or 0,
                )
            else:
                data = _truncate_artifact_data(data, self.max_artifact_bytes or 0)
            metadata["retention_policy"] = "truncated"
        filename = f"{artifact_id}_{_safe_filename(artifact_kind)}{suffix}"
        relative_path = Path("artifacts") / filename
        target_path = self.run_dir / relative_path
        tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")

        if isinstance(data, Path):
            shutil.copyfile(data, tmp_path)
        elif isinstance(data, bytes):
            tmp_path.write_bytes(data)
        else:
            tmp_path.write_text(data, encoding="utf-8")

        digest = _sha256_file(tmp_path)
        size_bytes = tmp_path.stat().st_size
        os.replace(tmp_path, target_path)

        ref = ArtifactRef(
            artifact_id=artifact_id,
            relative_path=relative_path.as_posix(),
            kind=artifact_kind,
            sha256=digest,
            size_bytes=size_bytes,
            created_by_event_id=created_by_event_id,
            redaction_status=metadata.get("redaction_status", "not_scanned"),
            retention_policy=metadata.get("retention_policy", "keep"),
        )
        manifest = self._read_manifest()
        manifest.append(ref.model_dump(mode="json"))
        self._write_manifest(manifest)
        if explicit_created_by_event_id is None:
            self.append_event(
                TrajectoryEvent(
                    event_id=created_by_event_id,
                    timestamp=_timestamp(),
                    run_id=self.run_id,
                    task_id=self.task_id,
                    event_type="artifact_created",
                    severity="debug",
                    artifact_refs=[ref],
                    data={
                        "artifact_id": ref.artifact_id,
                        "kind": ref.kind,
                        "relative_path": ref.relative_path,
                        "size_bytes": ref.size_bytes,
                    },
                )
            )
        if oversized:
            self.append_event(
                TrajectoryEvent(
                    event_id=self.next_event_id("artifact_budget"),
                    timestamp=_timestamp(),
                    run_id=self.run_id,
                    task_id=self.task_id,
                    event_type="artifact_budget_exhausted",
                    severity="warning",
                    artifact_refs=[ref],
                    data={
                        "artifact_id": ref.artifact_id,
                        "kind": ref.kind,
                        "relative_path": ref.relative_path,
                        "original_size_bytes": original_size_bytes,
                        "stored_size_bytes": ref.size_bytes,
                        "max_artifact_bytes": self.max_artifact_bytes,
                        "budget_policy": budget_policy,
                        "truncated": truncated,
                        "preserved": preserve_artifact,
                    },
                )
            )
        if retention_event_data is not None:
            self.append_event(
                TrajectoryEvent(
                    event_id=self.next_event_id("artifact_retention"),
                    timestamp=_timestamp(),
                    run_id=self.run_id,
                    task_id=self.task_id,
                    event_type="artifact_retention_policy_applied",
                    severity="info",
                    artifact_refs=[ref],
                    data={
                        **retention_event_data,
                        "artifact_id": ref.artifact_id,
                        "kind": ref.kind,
                        "relative_path": ref.relative_path,
                        "stored_size_bytes": ref.size_bytes,
                        "stored_sha256": ref.sha256,
                    },
                )
            )
        return ref

    def write_json_artifact(
        self,
        kind: str,
        obj: Any,
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        data = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        merged = {"suffix": ".json", "budget_policy": "truncate_json", **(metadata or {})}
        return self.write_artifact(kind, data, merged)

    def finalize_run(self, summary: str, *, status: RunStatus = "FINALIZED") -> None:
        current_status = self._read_status()
        if current_status == "FINALIZED":
            existing_summary = (
                self.summary_path.read_text(encoding="utf-8") if self.summary_path.exists() else None
            )
            if status == "FINALIZED" and existing_summary == summary:
                return
            raise RunRecorderError("run 已经 FINALIZED，不能改写 summary 或状态。")
        if self.summary_path.exists() and status == "FINALIZED":
            existing_summary = self.summary_path.read_text(encoding="utf-8")
            if existing_summary != summary:
                raise RunRecorderError("finalize_run 不能用不同内容改写已有 summary。")
        self.summary_path.write_text(summary, encoding="utf-8")
        self._write_status(status)

    def mark_interrupted(self, summary: str) -> None:
        self.finalize_run(summary, status="INTERRUPTED")

    def _load_manifest_counter(self) -> int:
        if not self.manifest_path.exists():
            return 0
        manifest = self._read_manifest()
        return len(manifest)

    def _read_manifest(self) -> list[dict[str, Any]]:
        if not self.manifest_path.exists():
            return []
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RunRecorderError("artifacts.json 不是合法 JSON") from exc
        artifacts = data.get("artifacts", data if isinstance(data, list) else None)
        if not isinstance(artifacts, list):
            raise RunRecorderError("artifacts.json 缺少 artifacts 列表")
        return artifacts

    def _write_manifest(self, artifacts: list[dict[str, Any]]) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "artifacts": artifacts,
        }
        tmp_path = self.manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        os.replace(tmp_path, self.manifest_path)

    def _write_status(self, status: RunStatus) -> None:
        payload = {"schema_version": SCHEMA_VERSION, "run_id": self.run_id, "status": status}
        self.status_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    def _read_status(self) -> str | None:
        if not self.status_path.exists():
            return None
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "CORRUPT_PARTIAL"
        status = payload.get("status")
        return str(status) if status is not None else None

    def _retention_rewrite(
        self,
        kind: str,
        data: bytes | str | Path,
        metadata: dict[str, Any],
    ) -> _RetentionRewrite | None:
        decision = _retention_decision(kind, self.recorder_profile)
        if decision is None:
            return None
        original_size_bytes = _artifact_size_bytes(data)
        original_sha256 = _sha256_artifact_data(data)
        preview_allowed = metadata.get("redaction_status") == "redacted"
        include_preview = (
            decision != "reasoning_trace_hash_only"
            and self.recorder_profile.raw_artifact_preview_chars > 0
            and preview_allowed
        )
        preview = (
            _artifact_text_preview(data, self.recorder_profile.raw_artifact_preview_chars)
            if include_preview
            else ""
        )
        retention_policy = (
            f"{self.recorder_profile.mode}_reasoning_trace_hash_only"
            if decision == "reasoning_trace_hash_only"
            else f"{self.recorder_profile.mode}_raw_artifact_projection"
        )
        fact_payload = {
            "schema_version": RETENTION_FACTS_SCHEMA_VERSION,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "target_kind": kind,
            "run_mode": self.recorder_profile.mode,
            "retention_policy": retention_policy,
            "original_size_bytes": original_size_bytes,
            "original_sha256": original_sha256,
            "raw_payload_persisted": False,
            "projection_only": decision != "reasoning_trace_hash_only",
            "hash_only": decision == "reasoning_trace_hash_only",
            "preview_chars": len(preview),
            "preview_size_bytes": len(preview.encode("utf-8")),
            "preview": preview or None,
            "preview_omitted_reason": (
                "source_not_redacted"
                if (
                    decision != "reasoning_trace_hash_only"
                    and self.recorder_profile.raw_artifact_preview_chars > 0
                    and not preview_allowed
                )
                else None
            ),
            "reason": _retention_reason(decision),
            "recorder_profile": self.recorder_profile.model_dump(
                mode="json",
                exclude={"critical_artifact_kinds"},
            ),
            "source_redaction_status": metadata.get("redaction_status"),
            "source_retention_policy": metadata.get("retention_policy"),
        }
        rewritten_metadata = {
            **metadata,
            "suffix": ".json",
            "budget_policy": "preserve_json",
            "retention_policy": retention_policy,
        }
        event_data = {
            key: value
            for key, value in fact_payload.items()
            if key not in {"preview", "recorder_profile"}
        }
        fact_artifact_kind = (
            "artifact_retention_facts"
            if decision == "reasoning_trace_hash_only"
            else "artifact_projection_facts"
        )
        event_data["fact_payload_kind"] = fact_artifact_kind
        return _RetentionRewrite(
            artifact_kind=fact_artifact_kind,
            data=json.dumps(fact_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            metadata=rewritten_metadata,
            event_data=event_data,
        )

    def _retention_event_for_complete_artifact(
        self,
        kind: str,
        data: bytes | str | Path,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        if self.recorder_profile.mode != "training_fast":
            return None
        if kind != PREPARED_MESSAGES_KIND:
            return None
        return {
            "schema_version": RETENTION_FACTS_SCHEMA_VERSION,
            "run_mode": self.recorder_profile.mode,
            "target_kind": kind,
            "retention_policy": "training_fast_keep_export_audit_compat",
            "original_size_bytes": _artifact_size_bytes(data),
            "original_sha256": _sha256_artifact_data(data),
            "raw_payload_persisted": True,
            "projection_only": False,
            "hash_only": False,
            "reason": (
                "prepared_messages is kept complete in Stage 3 unless export/audit "
                "projection support is implemented in the same change"
            ),
            "source_redaction_status": metadata.get("redaction_status"),
            "source_retention_policy": metadata.get("retention_policy"),
        }


def load_artifact_manifest(run_dir: str | Path) -> dict[str, Any]:
    manifest_path = Path(run_dir) / "artifacts.json"
    if not manifest_path.exists():
        return {"schema_version": SCHEMA_VERSION, "artifacts": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def verify_artifact_manifest(run_dir: str | Path) -> list[str]:
    run_path = Path(run_dir)
    manifest = load_artifact_manifest(run_path)
    errors: list[str] = []
    for raw_ref in manifest.get("artifacts", []):
        try:
            ref = ArtifactRef.model_validate(raw_ref)
        except ValidationError as exc:
            errors.append(f"invalid artifact ref: {exc}")
            continue
        relative_path = Path(ref.relative_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            errors.append(f"{ref.artifact_id}: unsafe relative_path {ref.relative_path}")
            continue
        artifact_path = (run_path / relative_path).resolve()
        try:
            artifact_path.relative_to(run_path.resolve())
        except ValueError:
            errors.append(f"{ref.artifact_id}: artifact path escapes run directory")
            continue
        if relative_path.parts[:1] != ("artifacts",):
            errors.append(f"{ref.artifact_id}: artifact path must be under artifacts/")
            continue
        if not artifact_path.exists():
            errors.append(f"{ref.artifact_id}: missing file {ref.relative_path}")
            continue
        digest = _sha256_file(artifact_path)
        if digest != ref.sha256:
            errors.append(f"{ref.artifact_id}: sha256 mismatch")
        size_bytes = artifact_path.stat().st_size
        if size_bytes != ref.size_bytes:
            errors.append(f"{ref.artifact_id}: size mismatch")
    return errors


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    jsonl_path = Path(path)
    if not jsonl_path.exists():
        return records
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _safe_filename(kind: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", kind).strip("_") or "artifact"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_suffix(data: bytes | str | Path, metadata: Mapping[str, Any]) -> str:
    explicit = metadata.get("suffix")
    if isinstance(explicit, str) and explicit.startswith("."):
        return explicit
    if isinstance(data, Path):
        return data.suffix or ".bin"
    if isinstance(data, bytes):
        return ".bin"
    return ".txt"


def _artifact_size_bytes(data: bytes | str | Path) -> int:
    if isinstance(data, Path):
        return data.stat().st_size
    if isinstance(data, bytes):
        return len(data)
    return len(data.encode("utf-8"))


def _coerce_recorder_profile(
    profile: RecorderProfile | Mapping[str, Any] | RecorderRunMode | None,
) -> RecorderProfile:
    if profile is None:
        return RecorderProfile.for_run_mode("full_audit")
    if isinstance(profile, RecorderProfile):
        return profile
    if isinstance(profile, str):
        return RecorderProfile.for_run_mode(profile)
    payload = dict(profile)
    mode = payload.get("mode")
    if isinstance(mode, str):
        default_profile = RecorderProfile.for_run_mode(mode).model_dump(mode="json")
        return RecorderProfile.model_validate({**default_profile, **payload})
    return RecorderProfile.model_validate(payload)


def _retention_decision(kind: str, profile: RecorderProfile) -> str | None:
    if profile.mode == "full_audit":
        return None
    normalized = kind.lower()
    if normalized in PROFILE_FACT_ARTIFACT_KINDS:
        return None
    if "reasoning_trace" in normalized or "thinking_trace" in normalized:
        if not profile.save_reasoning_trace or profile.reasoning_trace_retention == "hash_only":
            return "reasoning_trace_hash_only"
        return None
    if _is_raw_request_artifact(normalized):
        if not profile.save_raw_provider_request or profile.raw_artifact_retention == "projection":
            return "raw_request_projection"
    if _is_raw_response_artifact(normalized):
        if not profile.save_raw_provider_response or profile.raw_artifact_retention == "projection":
            return "raw_response_projection"
    return None


def _is_raw_request_artifact(kind: str) -> bool:
    if not kind.startswith("raw_"):
        return False
    return (
        "provider_request" in kind
        or kind.endswith("_request")
        or kind.endswith("_provider_request")
    )


def _is_raw_response_artifact(kind: str) -> bool:
    if not kind.startswith("raw_"):
        return False
    return (
        "provider_response" in kind
        or kind.endswith("_response")
        or kind.endswith("_provider_response")
    )


def _retention_reason(decision: str) -> str:
    if decision == "reasoning_trace_hash_only":
        return "run_mode forbids plaintext reasoning/thinking trace by default"
    if decision == "raw_request_projection":
        return "run_mode stores raw provider request as retention facts instead of full payload"
    if decision == "raw_response_projection":
        return "run_mode stores raw provider response as retention facts instead of full payload"
    return "run_mode artifact retention policy applied"


def _sha256_artifact_data(data: bytes | str | Path) -> str:
    import hashlib

    if isinstance(data, Path):
        return _sha256_file(data)
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _artifact_text_preview(data: bytes | str | Path, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if isinstance(data, Path):
        text = data.read_bytes().decode("utf-8", errors="replace")
    elif isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = data
    return text[:max_chars]


def _truncate_artifact_data(data: bytes | str | Path, max_bytes: int) -> bytes | str:
    if isinstance(data, Path):
        return data.read_bytes()[:max_bytes]
    if isinstance(data, bytes):
        return data[:max_bytes]
    marker = "\n[artifact truncated by max_artifact_bytes]\n"
    marker_bytes = marker.encode("utf-8")
    raw = data.encode("utf-8")
    if max_bytes <= len(marker_bytes):
        return marker_bytes[:max_bytes].decode("utf-8", errors="ignore")
    keep = max_bytes - len(marker_bytes)
    return raw[:keep].decode("utf-8", errors="ignore") + marker


def _truncate_json_artifact_data(
    *,
    kind: str,
    original_size_bytes: int,
    max_bytes: int,
) -> str:
    candidates = [
        {
            "schema_version": "repo_harness_truncated_json_artifact_v0",
            "truncated": True,
            "kind": kind,
            "original_size_bytes": original_size_bytes,
        },
        {"truncated": True, "kind": kind},
        {"truncated": True},
    ]
    for candidate in candidates:
        text = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        if len(text.encode("utf-8")) <= max_bytes:
            return text
    if max_bytes >= 2:
        return "{}"
    return "0"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
