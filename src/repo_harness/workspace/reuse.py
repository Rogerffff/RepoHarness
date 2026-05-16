"""Auditable workspace snapshot reuse primitives for training runs."""

from __future__ import annotations

import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.errors import WorkspaceError
from repo_harness.schema_base import StrictBaseModel, stable_hash
from repo_harness.workspace.source_hash import compute_source_tree_hash

WORKSPACE_REUSE_POLICY_VERSION = "repo_harness_workspace_reuse_stage6_v0"
WORKSPACE_SNAPSHOT_RESTORE_DIRECTORY_COPY = "directory_copy"
RESOURCE_CLEANUP_NOT_STARTED = "not_started"
RESOURCE_CLEANUP_COMPLETED = "completed"
RESOURCE_CLEANUP_FAILED = "failed"
RESOURCE_CLEANUP_SKIPPED = "skipped"
LEASE_STATUS_ACTIVE = "active"
LEASE_STATUS_RELEASED = "released"
LEASE_STATUS_CLEANUP_FAILED = "cleanup_failed"
LEASE_STATUS_ORPHANED = "orphaned"
SNAPSHOT_FACTS_FILENAME = "snapshot_facts.json"
SNAPSHOT_WORKSPACE_DIRNAME = "workspace"

CleanupStatus = Literal["not_started", "completed", "failed", "skipped"]
LeaseLifecycleStatus = Literal["active", "released", "cleanup_failed", "orphaned"]

SENSITIVE_DEPENDENCY_PARTS = {
    ".aws",
    ".config/gh",
    ".config/gcloud",
    ".env",
    ".gnupg",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".ssh",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "pip.conf",
    "pip.ini",
    "secret",
    "secret.json",
    "secrets.json",
    "token",
    "token.json",
}
SENSITIVE_DEPENDENCY_STEMS = {"credential", "credentials", "secret", "token"}
SENSITIVE_DEPENDENCY_SUFFIXES = {".cer", ".crt", ".key", ".p12", ".pem", ".pfx"}


class WorkspaceReusePolicy(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_reuse_policy_stage6_v0"
    policy_version: str = WORKSPACE_REUSE_POLICY_VERSION
    enable_snapshots: bool = True
    enable_dependency_cache: bool = False
    restore_strategy: Literal["directory_copy"] = WORKSPACE_SNAPSHOT_RESTORE_DIRECTORY_COPY
    cleanup_leases: bool = True
    max_cache_bytes: int | None = Field(default=None, gt=0)


class WorkspaceSnapshotKey(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_snapshot_key_stage6_v0"
    snapshot_key: str | None = None
    repo_ref: str | None = None
    base_commit: str | None = None
    environment_id: str | None = None
    docker_image_digest: str | None = None
    setup_command_hash: str = "none"
    dependency_lock_hash: str = "none"
    toolchain_version: str
    harness_version: str
    source_tree_hash: str | None = None
    source_archive_sha256: str | None = None
    mirror_sha256: str | None = None
    workspace_reuse_policy_version: str = WORKSPACE_REUSE_POLICY_VERSION
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_and_fill_snapshot_key(self) -> "WorkspaceSnapshotKey":
        for field_name in [
            "repo_ref",
            "base_commit",
            "environment_id",
            "docker_image_digest",
            "setup_command_hash",
            "dependency_lock_hash",
            "toolchain_version",
            "harness_version",
            "source_tree_hash",
            "source_archive_sha256",
            "mirror_sha256",
            "workspace_reuse_policy_version",
        ]:
            value = getattr(self, field_name)
            if value is not None:
                _validate_no_absolute_local_path(value, field_name=field_name)
        for diagnostic in self.diagnostics:
            _validate_no_absolute_local_path(diagnostic, field_name="diagnostics")
        payload = {
            "repo_ref": self.repo_ref,
            "base_commit": self.base_commit,
            "environment_id": self.environment_id,
            "docker_image_digest": self.docker_image_digest,
            "setup_command_hash": self.setup_command_hash,
            "dependency_lock_hash": self.dependency_lock_hash,
            "toolchain_version": self.toolchain_version,
            "harness_version": self.harness_version,
            "source_tree_hash": self.source_tree_hash,
            "source_archive_sha256": self.source_archive_sha256,
            "mirror_sha256": self.mirror_sha256,
            "workspace_reuse_policy_version": self.workspace_reuse_policy_version,
        }
        object.__setattr__(
            self,
            "snapshot_key",
            self.snapshot_key or f"wssnap-{stable_hash(payload)[:24]}",
        )
        _validate_safe_identifier(str(self.snapshot_key), field_name="snapshot_key")
        return self


class WorkspaceSnapshotFacts(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_snapshot_facts_stage6_v0"
    snapshot_key: str
    snapshot_ref: str
    restore_strategy: Literal["directory_copy"] = WORKSPACE_SNAPSHOT_RESTORE_DIRECTORY_COPY
    workspace_reuse_policy_version: str = WORKSPACE_REUSE_POLICY_VERSION
    repo_ref: str | None = None
    base_commit: str | None = None
    environment_id: str | None = None
    docker_image_digest: str | None = None
    setup_command_hash: str = "none"
    dependency_lock_hash: str = "none"
    toolchain_version: str
    harness_version: str
    source_tree_hash: str
    source_archive_sha256: str | None = None
    mirror_sha256: str | None = None
    clean_state_verified: bool = False
    clean_state_verification: str = "source_tree_hash_verified_after_materialization"
    created_by: str
    created_at_unix: float = Field(ge=0.0)
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_snapshot_facts(self) -> "WorkspaceSnapshotFacts":
        if not self.snapshot_ref.startswith("rh://workspace-snapshot/"):
            raise ValueError("snapshot_ref must be an opaque workspace snapshot ref")
        _validate_safe_identifier(self.snapshot_key, field_name="snapshot_key")
        for field_name in [
            "snapshot_key",
            "snapshot_ref",
            "repo_ref",
            "base_commit",
            "environment_id",
            "docker_image_digest",
            "setup_command_hash",
            "dependency_lock_hash",
            "toolchain_version",
            "harness_version",
            "source_tree_hash",
            "source_archive_sha256",
            "mirror_sha256",
            "clean_state_verification",
            "created_by",
        ]:
            value = getattr(self, field_name)
            if value is not None:
                _validate_no_absolute_local_path(value, field_name=field_name)
        for diagnostic in self.diagnostics:
            _validate_no_absolute_local_path(diagnostic, field_name="diagnostics")
        return self


class WorkspaceSnapshotResult(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_snapshot_result_stage6_v0"
    facts: WorkspaceSnapshotFacts
    snapshot_cache_hit: bool
    snapshot_restore_strategy: Literal["directory_copy"] = WORKSPACE_SNAPSHOT_RESTORE_DIRECTORY_COPY
    diagnostics: list[str] = Field(default_factory=list)


class WorkspaceLease(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_lease_stage6_v0"
    lease_id: str
    workspace_id: str
    snapshot_key: str
    workspace_path: str
    lifecycle_status: LeaseLifecycleStatus = LEASE_STATUS_ACTIVE
    cleanup_status: CleanupStatus = RESOURCE_CLEANUP_NOT_STARTED
    created_at_unix: float = Field(ge=0.0)
    released_at_unix: float | None = Field(default=None, ge=0.0)
    cleanup_error: str | None = None
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_lease(self) -> "WorkspaceLease":
        _validate_safe_identifier(self.lease_id, field_name="lease_id")
        _validate_safe_identifier(self.workspace_id, field_name="workspace_id")
        _validate_safe_identifier(self.snapshot_key, field_name="snapshot_key")
        _validate_safe_relative_path(self.workspace_path, field_name="workspace_path")
        for field_name in ["lease_id", "workspace_id", "snapshot_key", "cleanup_error"]:
            value = getattr(self, field_name)
            if value is not None:
                _validate_no_absolute_local_path(value, field_name=field_name)
        for diagnostic in self.diagnostics:
            _validate_no_absolute_local_path(diagnostic, field_name="diagnostics")
        return self


@dataclass(frozen=True)
class WorkspaceLeaseHandle:
    lease: WorkspaceLease
    workspace_path: Path
    workspace_materialization_seconds: float = 0.0
    dependency_restore_seconds: float = 0.0
    cleanup_seconds: float = 0.0


class WorkspaceSnapshotManager:
    """Create clean snapshots and isolated writable episode workspace leases."""

    def __init__(
        self,
        cache_root: str | Path,
        *,
        policy: WorkspaceReusePolicy | None = None,
        creator_id: str | None = None,
        lock_timeout_seconds: float = 10.0,
    ) -> None:
        if lock_timeout_seconds <= 0:
            raise ValueError("lock_timeout_seconds must be > 0")
        self.cache_root = Path(cache_root)
        self.policy = policy or WorkspaceReusePolicy()
        self.creator_id = creator_id or f"pid-{os.getpid()}"
        self.lock_timeout_seconds = lock_timeout_seconds
        self.snapshots_dir = self.cache_root / "snapshots"
        self.tmp_dir = self.cache_root / ".tmp"
        self.locks_dir = self.cache_root / ".locks"
        self.leases_dir = self.cache_root / "leases"
        self.lease_facts_dir = self.cache_root / "lease_facts"
        for directory in [
            self.snapshots_dir,
            self.tmp_dir,
            self.locks_dir,
            self.leases_dir,
            self.lease_facts_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def create_or_get_snapshot(
        self,
        key: WorkspaceSnapshotKey,
        *,
        source_path: str | Path,
    ) -> WorkspaceSnapshotResult:
        source_root = Path(source_path).resolve()
        if not source_root.exists() or not source_root.is_dir():
            raise WorkspaceError(f"snapshot source_path must be an existing directory: {source_path}")
        key = self._key_with_source_identity(key, source_root)
        snapshot_key = _require_snapshot_key(key)
        with _SnapshotLocalLock(
            self.locks_dir / f"{snapshot_key}.lock",
            timeout_seconds=self.lock_timeout_seconds,
        ):
            snapshot_dir = self._snapshot_dir(snapshot_key)
            if snapshot_dir.exists():
                facts = self._load_and_validate_snapshot(snapshot_dir, key)
                return WorkspaceSnapshotResult(
                    facts=facts,
                    snapshot_cache_hit=True,
                    snapshot_restore_strategy=facts.restore_strategy,
                )
            tmp_snapshot_dir = self.tmp_dir / f"{snapshot_key}.{uuid.uuid4().hex}"
            try:
                workspace_tmp = tmp_snapshot_dir / SNAPSHOT_WORKSPACE_DIRNAME
                _validate_tree_symlinks_within_root(
                    source_root,
                    source_root,
                    context="workspace snapshot source",
                )
                shutil.copytree(source_root, workspace_tmp, symlinks=True)
                _validate_tree_symlinks_within_root(
                    workspace_tmp,
                    workspace_tmp,
                    context="workspace snapshot",
                )
                source_tree_hash = compute_source_tree_hash(workspace_tmp)
                if key.source_tree_hash is not None and key.source_tree_hash != source_tree_hash:
                    raise WorkspaceError(
                        "source_tree_hash mismatch while creating workspace snapshot"
                    )
                facts = self._snapshot_facts(key, source_tree_hash=source_tree_hash)
                _write_json(tmp_snapshot_dir / SNAPSHOT_FACTS_FILENAME, facts.model_dump(mode="json"))
                if snapshot_dir.exists():
                    existing = self._load_and_validate_snapshot(snapshot_dir, key)
                    shutil.rmtree(tmp_snapshot_dir, ignore_errors=True)
                    return WorkspaceSnapshotResult(
                        facts=existing,
                        snapshot_cache_hit=True,
                        snapshot_restore_strategy=existing.restore_strategy,
                    )
                tmp_snapshot_dir.rename(snapshot_dir)
                return WorkspaceSnapshotResult(
                    facts=facts,
                    snapshot_cache_hit=False,
                    snapshot_restore_strategy=facts.restore_strategy,
                )
            except Exception:
                shutil.rmtree(tmp_snapshot_dir, ignore_errors=True)
                raise

    def acquire_workspace(
        self,
        snapshot: WorkspaceSnapshotResult | WorkspaceSnapshotFacts,
        *,
        lease_id: str | None = None,
        dependency_restore_seconds: float = 0.0,
    ) -> WorkspaceLeaseHandle:
        facts = snapshot.facts if isinstance(snapshot, WorkspaceSnapshotResult) else snapshot
        start = time.perf_counter()
        lease_id = lease_id or f"lease-{uuid.uuid4().hex}"
        _validate_safe_identifier(lease_id, field_name="lease_id")
        workspace_id = f"workspace-{lease_id}"
        workspace_relative_path = PurePosixPath("leases") / facts.snapshot_key / lease_id
        workspace_path = self.cache_root / workspace_relative_path
        if workspace_path.exists():
            raise WorkspaceError(f"workspace lease path already exists: {workspace_relative_path}")
        snapshot_workspace = self._snapshot_dir(facts.snapshot_key) / SNAPSHOT_WORKSPACE_DIRNAME
        if not snapshot_workspace.exists():
            raise WorkspaceError(f"snapshot workspace is missing for key: {facts.snapshot_key}")
        _validate_tree_symlinks_within_root(
            snapshot_workspace,
            snapshot_workspace,
            context="published workspace snapshot",
        )
        shutil.copytree(snapshot_workspace, workspace_path, symlinks=True)
        _validate_tree_symlinks_within_root(
            workspace_path,
            workspace_path,
            context="workspace lease",
        )
        materialization_seconds = time.perf_counter() - start
        lease = WorkspaceLease(
            lease_id=lease_id,
            workspace_id=workspace_id,
            snapshot_key=facts.snapshot_key,
            workspace_path=workspace_relative_path.as_posix(),
            lifecycle_status=LEASE_STATUS_ACTIVE,
            cleanup_status=RESOURCE_CLEANUP_NOT_STARTED,
            created_at_unix=time.time(),
        )
        handle = WorkspaceLeaseHandle(
            lease=lease,
            workspace_path=workspace_path,
            workspace_materialization_seconds=materialization_seconds,
            dependency_restore_seconds=dependency_restore_seconds,
        )
        self._write_lease_facts(handle)
        return handle

    def release_workspace(self, handle: WorkspaceLeaseHandle) -> WorkspaceLeaseHandle:
        start = time.perf_counter()
        if handle.lease.lifecycle_status != LEASE_STATUS_ACTIVE:
            return handle
        try:
            self._assert_lease_handle_belongs_to_manager(handle)
        except Exception as exc:
            cleanup_seconds = time.perf_counter() - start
            lease = handle.lease.model_copy(
                update={
                    "lifecycle_status": LEASE_STATUS_CLEANUP_FAILED,
                    "cleanup_status": RESOURCE_CLEANUP_FAILED,
                    "released_at_unix": time.time(),
                    "cleanup_error": str(exc),
                    "diagnostics": [
                        *handle.lease.diagnostics,
                        "workspace lease path ownership check failed",
                    ],
                }
            )
            released = WorkspaceLeaseHandle(
                lease=lease,
                workspace_path=handle.workspace_path,
                workspace_materialization_seconds=handle.workspace_materialization_seconds,
                dependency_restore_seconds=handle.dependency_restore_seconds,
                cleanup_seconds=cleanup_seconds,
            )
            self._write_lease_facts(released)
            return released
        try:
            if handle.workspace_path.exists():
                shutil.rmtree(handle.workspace_path)
            cleanup_seconds = time.perf_counter() - start
            lease = handle.lease.model_copy(
                update={
                    "lifecycle_status": LEASE_STATUS_RELEASED,
                    "cleanup_status": RESOURCE_CLEANUP_COMPLETED,
                    "released_at_unix": time.time(),
                    "cleanup_error": None,
                }
            )
        except Exception as exc:
            cleanup_seconds = time.perf_counter() - start
            lease = handle.lease.model_copy(
                update={
                    "lifecycle_status": LEASE_STATUS_CLEANUP_FAILED,
                    "cleanup_status": RESOURCE_CLEANUP_FAILED,
                    "released_at_unix": time.time(),
                    "cleanup_error": str(exc),
                    "diagnostics": [
                        *handle.lease.diagnostics,
                        "workspace lease cleanup failed",
                    ],
                }
            )
        released = WorkspaceLeaseHandle(
            lease=lease,
            workspace_path=handle.workspace_path,
            workspace_materialization_seconds=handle.workspace_materialization_seconds,
            dependency_restore_seconds=handle.dependency_restore_seconds,
            cleanup_seconds=cleanup_seconds,
        )
        self._write_lease_facts(released)
        return released

    def resource_summary_fields(
        self,
        *,
        snapshot: WorkspaceSnapshotResult,
        lease: WorkspaceLease,
        workspace_backend: str,
        dependency_cache_key: str | None = None,
        dependency_cache_hit: bool | None = False,
        baseline_cache_hit: bool | None = False,
        container_reuse_hit: bool | None = False,
        run_dir: str | None = None,
    ) -> dict[str, str | bool | None]:
        self._assert_lease_matches_snapshot(snapshot.facts, lease)
        fields: dict[str, str | bool | None] = {
            "snapshot_key": snapshot.facts.snapshot_key,
            "snapshot_cache_hit": snapshot.snapshot_cache_hit,
            "snapshot_restore_strategy": snapshot.snapshot_restore_strategy,
            "dependency_state_key": dependency_cache_key,
            "dependency_cache_key": dependency_cache_key,
            "dependency_cache_hit": dependency_cache_hit,
            "baseline_cache_hit": baseline_cache_hit,
            "container_reuse_hit": container_reuse_hit,
            "lease_id": lease.lease_id,
            "workspace_backend": workspace_backend,
            "workspace_path": lease.workspace_path,
            "cleanup_status": lease.cleanup_status,
        }
        if run_dir is not None:
            _validate_safe_relative_path(run_dir, field_name="run_dir")
            fields["run_dir"] = run_dir
        return fields

    @staticmethod
    def timing_summary_fields(handle: WorkspaceLeaseHandle) -> dict[str, float]:
        return {
            "workspace_materialization_seconds": handle.workspace_materialization_seconds,
            "dependency_restore_seconds": handle.dependency_restore_seconds,
            "cleanup_seconds": handle.cleanup_seconds,
        }

    def _key_with_source_identity(
        self,
        key: WorkspaceSnapshotKey,
        source_root: Path,
    ) -> WorkspaceSnapshotKey:
        if key.source_tree_hash is not None:
            return key
        diagnostics = list(key.diagnostics)
        if key.source_archive_sha256 is None and key.mirror_sha256 is None:
            diagnostics.append(
                "source_tree_hash computed from source_path because no prelookup source hash was provided"
            )
        return WorkspaceSnapshotKey(
            repo_ref=key.repo_ref,
            base_commit=key.base_commit,
            environment_id=key.environment_id,
            docker_image_digest=key.docker_image_digest,
            setup_command_hash=key.setup_command_hash,
            dependency_lock_hash=key.dependency_lock_hash,
            toolchain_version=key.toolchain_version,
            harness_version=key.harness_version,
            source_tree_hash=compute_source_tree_hash(source_root),
            source_archive_sha256=key.source_archive_sha256,
            mirror_sha256=key.mirror_sha256,
            workspace_reuse_policy_version=key.workspace_reuse_policy_version,
            diagnostics=diagnostics,
        )

    def _snapshot_dir(self, snapshot_key: str) -> Path:
        return self.snapshots_dir / snapshot_key

    def _snapshot_facts(self, key: WorkspaceSnapshotKey, *, source_tree_hash: str) -> WorkspaceSnapshotFacts:
        snapshot_key = _require_snapshot_key(key)
        return WorkspaceSnapshotFacts(
            snapshot_key=snapshot_key,
            snapshot_ref=f"rh://workspace-snapshot/{snapshot_key}",
            restore_strategy=self.policy.restore_strategy,
            workspace_reuse_policy_version=key.workspace_reuse_policy_version,
            repo_ref=key.repo_ref,
            base_commit=key.base_commit,
            environment_id=key.environment_id,
            docker_image_digest=key.docker_image_digest,
            setup_command_hash=key.setup_command_hash,
            dependency_lock_hash=key.dependency_lock_hash,
            toolchain_version=key.toolchain_version,
            harness_version=key.harness_version,
            source_tree_hash=source_tree_hash,
            source_archive_sha256=key.source_archive_sha256,
            mirror_sha256=key.mirror_sha256,
            clean_state_verified=False,
            clean_state_verification="source_tree_hash_verified_after_materialization",
            created_by=self.creator_id,
            created_at_unix=time.time(),
            diagnostics=list(key.diagnostics),
        )

    def _load_and_validate_snapshot(
        self,
        snapshot_dir: Path,
        key: WorkspaceSnapshotKey,
    ) -> WorkspaceSnapshotFacts:
        facts_path = snapshot_dir / SNAPSHOT_FACTS_FILENAME
        workspace_path = snapshot_dir / SNAPSHOT_WORKSPACE_DIRNAME
        if not facts_path.exists() or not workspace_path.exists():
            raise WorkspaceError("published workspace snapshot is missing facts or workspace directory")
        facts = WorkspaceSnapshotFacts.model_validate_json(facts_path.read_text(encoding="utf-8"))
        if facts.snapshot_key != _require_snapshot_key(key):
            raise WorkspaceError("published workspace snapshot key does not match requested key")
        if facts.workspace_reuse_policy_version != key.workspace_reuse_policy_version:
            raise WorkspaceError("published workspace snapshot policy version does not match requested key")
        if key.source_tree_hash is not None and facts.source_tree_hash != key.source_tree_hash:
            raise WorkspaceError("published workspace snapshot source_tree_hash does not match requested key")
        _validate_tree_symlinks_within_root(
            workspace_path,
            workspace_path,
            context="published workspace snapshot",
        )
        return facts

    def _assert_lease_handle_belongs_to_manager(self, handle: WorkspaceLeaseHandle) -> None:
        expected = (self.cache_root / handle.lease.workspace_path).resolve(strict=False)
        actual = handle.workspace_path.resolve(strict=False)
        leases_root = self.leases_dir.resolve(strict=False)
        if actual != expected:
            raise WorkspaceError("workspace lease handle path does not match lease facts")
        try:
            actual.relative_to(leases_root)
        except ValueError as exc:
            raise WorkspaceError("workspace lease path is outside this manager leases directory") from exc
        self._assert_lease_path_shape(handle.lease)

    def _assert_lease_matches_snapshot(
        self,
        snapshot: WorkspaceSnapshotFacts,
        lease: WorkspaceLease,
    ) -> None:
        if lease.snapshot_key != snapshot.snapshot_key:
            raise WorkspaceError("workspace lease snapshot_key does not match snapshot facts")
        self._assert_lease_path_shape(lease)

    @staticmethod
    def _assert_lease_path_shape(lease: WorkspaceLease) -> None:
        expected = PurePosixPath("leases") / lease.snapshot_key / lease.lease_id
        if PurePosixPath(lease.workspace_path) != expected:
            raise WorkspaceError("workspace lease path does not match leases/<snapshot_key>/<lease_id>")

    def _write_lease_facts(self, handle: WorkspaceLeaseHandle) -> None:
        _write_json(
            self.lease_facts_dir / f"{handle.lease.lease_id}.json",
            handle.lease.model_dump(mode="json"),
        )


def build_workspace_snapshot_key(
    *,
    repo_ref: str | None = None,
    base_commit: str | None = None,
    environment_id: str | None = None,
    docker_image_digest: str | None = None,
    setup_command: str | None = None,
    setup_command_hash: str | None = None,
    dependency_lock_hash: str | None = None,
    toolchain_version: str | None = None,
    harness_version: str,
    source_tree_hash: str | None = None,
    source_archive_sha256: str | None = None,
    mirror_sha256: str | None = None,
    diagnostics: list[str] | None = None,
) -> WorkspaceSnapshotKey:
    if setup_command_hash is None:
        setup_command_hash = "none" if not setup_command else stable_hash({"setup_command": setup_command})
    return WorkspaceSnapshotKey(
        repo_ref=repo_ref,
        base_commit=base_commit,
        environment_id=environment_id,
        docker_image_digest=docker_image_digest,
        setup_command_hash=setup_command_hash,
        dependency_lock_hash=dependency_lock_hash or "none",
        toolchain_version=toolchain_version or f"python-{sys.version_info.major}.{sys.version_info.minor}",
        harness_version=harness_version,
        source_tree_hash=source_tree_hash,
        source_archive_sha256=source_archive_sha256,
        mirror_sha256=mirror_sha256,
        diagnostics=list(diagnostics or []),
    )


def copy_declared_dependency_paths(
    *,
    source_root: str | Path,
    destination_root: str | Path,
    declared_paths: list[str | Path],
) -> list[str]:
    source_root_path = Path(source_root).resolve()
    destination_root_path = Path(destination_root).resolve()
    if not source_root_path.exists() or not source_root_path.is_dir():
        raise WorkspaceError(f"dependency source_root must be an existing directory: {source_root}")
    destination_root_path.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for declared in declared_paths:
        relative = _validate_declared_dependency_path(declared)
        source = source_root_path / relative
        if not source.exists() and not source.is_symlink():
            raise WorkspaceError(f"declared dependency path does not exist: {relative.as_posix()}")
        _validate_path_within_root(source, source_root_path, field_name=relative.as_posix())
        _validate_dependency_tree_for_copy(source, source_root_path)
        _validate_symlinks_within_root(source, source_root_path)
        destination = destination_root_path / relative
        _validate_path_within_root(destination.parent, destination_root_path, field_name=relative.as_posix())
        if destination.exists() or destination.is_symlink():
            raise WorkspaceError(f"declared dependency destination already exists: {relative.as_posix()}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)
        copied.append(relative.as_posix())
    return copied


def _require_snapshot_key(key: WorkspaceSnapshotKey) -> str:
    if key.snapshot_key is None:
        raise WorkspaceError("workspace snapshot key was not populated")
    return key.snapshot_key


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    data = stable_json(payload)
    with tmp_path.open("w", encoding="utf-8") as file:
        file.write(data)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    tmp_path.replace(path)


def stable_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _validate_declared_dependency_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise WorkspaceError(f"declared dependency path must be relative and stay in root: {value}")
    if path.as_posix() in {"", "."}:
        raise WorkspaceError("declared dependency path must name a concrete path")
    _reject_sensitive_dependency_path(path)
    return path


def _reject_sensitive_dependency_path(relative: Path) -> None:
    normalized = relative.as_posix()
    normalized_lower = normalized.lower()
    name = relative.name.lower()
    stem = Path(name).stem
    parts = tuple(part.lower() for part in relative.parts)
    if any(_contains_sensitive_path_parts(parts, item) for item in SENSITIVE_DEPENDENCY_PARTS):
        raise WorkspaceError(f"declared dependency path is sensitive: {normalized}")
    if any(
        normalized_lower == item or normalized_lower.startswith(f"{item}/")
        for item in SENSITIVE_DEPENDENCY_PARTS
    ):
        raise WorkspaceError(f"declared dependency path is sensitive: {normalized}")
    if name.startswith(".env") or stem in SENSITIVE_DEPENDENCY_STEMS:
        raise WorkspaceError(f"declared dependency path is sensitive: {normalized}")
    if relative.suffix.lower() in SENSITIVE_DEPENDENCY_SUFFIXES:
        raise WorkspaceError(f"declared dependency path has sensitive suffix: {normalized}")


def _contains_sensitive_path_parts(parts: tuple[str, ...], sensitive_path: str) -> bool:
    sensitive_parts = tuple(PurePosixPath(sensitive_path.lower()).parts)
    if not sensitive_parts:
        return False
    if len(sensitive_parts) == 1:
        return sensitive_parts[0] in parts
    window_size = len(sensitive_parts)
    return any(
        parts[index : index + window_size] == sensitive_parts
        for index in range(0, len(parts) - window_size + 1)
    )


def _validate_dependency_tree_for_copy(path: Path, root: Path) -> None:
    candidates = [path]
    if path.is_dir() and not path.is_symlink():
        candidates.extend(path.rglob("*"))
    for candidate in candidates:
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise WorkspaceError(f"path escapes allowed root: {candidate}") from exc
        _reject_sensitive_dependency_path(relative)


def _validate_path_within_root(path: Path, root: Path, *, field_name: str) -> None:
    resolved_root = root.resolve()
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspaceError(f"path escapes allowed root: {field_name}") from exc


def _validate_symlinks_within_root(path: Path, root: Path) -> None:
    _validate_tree_symlinks_within_root(path, root, context="declared dependency")


def _validate_tree_symlinks_within_root(path: Path, root: Path, *, context: str) -> None:
    resolved_root = root.resolve()
    candidates = [path]
    if path.is_dir() and not path.is_symlink():
        candidates.extend(path.rglob("*"))
    for candidate in candidates:
        if not candidate.is_symlink():
            continue
        if candidate.readlink().is_absolute():
            raise WorkspaceError(
                f"{context} symlink uses an absolute target: {candidate}"
            )
        target = candidate.resolve(strict=False)
        try:
            target.relative_to(resolved_root)
        except ValueError as exc:
            raise WorkspaceError(
                f"{context} symlink escapes allowed root: {candidate}"
            ) from exc


def _validate_safe_relative_path(value: str, *, field_name: str) -> None:
    _validate_no_absolute_local_path(value, field_name=field_name)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a safe relative path")


def _validate_safe_identifier(value: str, *, field_name: str) -> None:
    _validate_no_absolute_local_path(value, field_name=field_name)
    path = PurePosixPath(value)
    if value in {"", ".", ".."} or "/" in value or "\\" in value or ".." in path.parts:
        raise ValueError(f"{field_name} must be a safe identifier")


def _validate_no_absolute_local_path(value: str, *, field_name: str) -> None:
    if (
        value.startswith("/")
        or "/Users/" in value
        or (len(value) > 2 and value[1:3] == ":\\")
    ):
        raise ValueError(f"{field_name} must not contain an absolute local path")


class _SnapshotLocalLock:
    def __init__(self, lock_path: Path, *, timeout_seconds: float) -> None:
        self.lock_path = lock_path
        self.timeout_seconds = timeout_seconds
        self.acquired = False

    def __enter__(self) -> "_SnapshotLocalLock":
        deadline = time.monotonic() + self.timeout_seconds
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.lock_path.mkdir()
                self.acquired = True
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise WorkspaceError(f"timed out acquiring workspace snapshot lock: {self.lock_path.name}")
                time.sleep(0.01)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.acquired:
            try:
                self.lock_path.rmdir()
            finally:
                self.acquired = False
