"""RunRecorder、JSONL 记录和 artifact manifest。"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from repo_harness.errors import RepoHarnessError
from repo_harness.schema_versions import SCHEMA_VERSION
from repo_harness.trajectory.schemas import ArtifactRef, TrajectoryEvent, TranscriptRecord

RunStatus = Literal["RUNNING", "FINALIZED", "INTERRUPTED", "CORRUPT_PARTIAL"]


class RunRecorderError(RepoHarnessError):
    """RunRecorder 读写失败。"""


class RunRecorder:
    """统一写入 transcript、events 和 artifact manifest。"""

    def __init__(self, run_id: str, run_dir: str | Path, *, task_id: str | None = None) -> None:
        self.run_id = run_id
        self.task_id = task_id
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
        metadata = metadata or {}
        self._artifact_counter += 1
        artifact_id = f"{self.run_id}_artifact_{self._artifact_counter:06d}"
        suffix = _artifact_suffix(data, metadata)
        filename = f"{artifact_id}_{_safe_filename(kind)}{suffix}"
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
            kind=kind,
            sha256=digest,
            size_bytes=size_bytes,
            created_by_event_id=metadata.get("created_by_event_id"),
            redaction_status=metadata.get("redaction_status", "not_scanned"),
            retention_policy=metadata.get("retention_policy", "keep"),
        )
        manifest = self._read_manifest()
        manifest.append(ref.model_dump(mode="json"))
        self._write_manifest(manifest)
        return ref

    def write_json_artifact(
        self,
        kind: str,
        obj: Any,
        metadata: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        data = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        merged = {"suffix": ".json", **(metadata or {})}
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


def _artifact_suffix(data: bytes | str | Path, metadata: Mapping[str, Any]) -> str:
    explicit = metadata.get("suffix")
    if isinstance(explicit, str) and explicit.startswith("."):
        return explicit
    if isinstance(data, Path):
        return data.suffix or ".bin"
    if isinstance(data, bytes):
        return ".bin"
    return ".txt"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
