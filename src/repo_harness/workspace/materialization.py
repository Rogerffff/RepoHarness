"""Source materialization for auditable repository snapshots."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import WorkspaceError
from repo_harness.run_metadata.schemas import SourceCheckoutFacts
from repo_harness.tasks.schemas import (
    FixtureRepositorySource,
    LocalArchiveSource,
    LocalRepositorySource,
    PublicSnapshotSource,
    RunnableTask,
)
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

SOURCE_MATERIALIZATION_POLICY_VERSION = "repo_harness_source_materialization_v0"


@dataclass(frozen=True)
class SourceCheckout:
    """Materialized source checkout plus serializable facts."""

    root: Path
    facts: SourceCheckoutFacts


def materialize_source(task: RunnableTask, destination: str | Path) -> SourceCheckout:
    """Materialize task source into ``destination`` and return checkout facts."""

    destination_path = Path(destination)
    if destination_path.exists():
        shutil.rmtree(destination_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    source = task.repo_source_spec or FixtureRepositorySource(
        path=task.repo_source,
        base_commit=task.base_commit,
        synthetic_base_id=None if task.base_commit else f"{task.task_id}_synthetic_base",
    )
    if isinstance(source, FixtureRepositorySource):
        _copy_source_tree(Path(source.path), destination_path)
        facts = _facts_for_local_tree(
            task=task,
            root=destination_path,
            source_type="fixture_path",
            remote_url=task.decontamination_metadata.source_url,
            mirror_source="fixture_path",
            base_commit=task.base_commit or source.base_commit,
            resolved_commit=task.base_commit or source.base_commit,
            synthetic_base_id=source.synthetic_base_id,
            archive_sha256=task.source_archive_sha256,
            mirror_sha256=None,
            decontamination_status=task.decontamination_metadata.status,
            remotes_stripped=True,
            branches_stripped=True,
            tags_stripped=True,
            materialization_command_facts=_copy_command_facts(
                source_type="fixture_path",
                input_kind="fixture_path",
            ),
        )
        return SourceCheckout(root=destination_path, facts=facts)
    if isinstance(source, LocalRepositorySource):
        return _materialize_local_repository(task, source, destination_path)
    if isinstance(source, LocalArchiveSource):
        return _materialize_archive(
            task=task,
            source=source,
            destination=destination_path,
            source_type="local_archive",
            archive_path=Path(source.archive_path),
            archive_sha256=source.archive_sha256,
            expected_root_directory=source.expected_root_directory,
            base_commit=source.base_commit,
            synthetic_base_id=source.synthetic_base_id,
            decontamination_status=source.decontamination_status,
            remotes_stripped=True,
            branches_stripped=True,
            tags_stripped=True,
        )
    if isinstance(source, PublicSnapshotSource):
        if source.archive_path is None or source.expected_root_directory is None:
            raise WorkspaceError(
                "public_snapshot materialization requires a pre-downloaded archive_path "
                "and expected_root_directory; RepoHarness Stage 12 does not download from network."
            )
        return _materialize_archive(
            task=task,
            source=source,
            destination=destination_path,
            source_type="public_snapshot",
            archive_path=Path(source.archive_path),
            archive_sha256=source.archive_sha256,
            expected_root_directory=source.expected_root_directory,
            base_commit=source.commit_sha,
            synthetic_base_id=None,
            decontamination_status=source.decontamination_status,
            remotes_stripped=source.remotes_stripped,
            branches_stripped=source.branches_stripped,
            tags_stripped=source.tags_stripped,
        )
    raise WorkspaceError(f"Unsupported repo source specification: {type(source).__name__}")


def _materialize_local_repository(
    task: RunnableTask,
    source: LocalRepositorySource,
    destination: Path,
) -> SourceCheckout:
    source_path = Path(source.source_path)
    if not source_path.exists() or not source_path.is_dir():
        raise WorkspaceError(f"local_repository source does not exist: {source_path}")
    if not (source_path / ".git").exists() and source.base_commit:
        _copy_source_tree(source_path, destination)
        facts = _facts_for_local_tree(
            task=task,
            root=destination,
            source_type="fixed_local_mirror",
            remote_url=task.decontamination_metadata.source_url,
            mirror_source=task.decontamination_metadata.source_url or "fixed_local_mirror",
            base_commit=source.base_commit,
            resolved_commit=source.base_commit,
            synthetic_base_id=None,
            archive_sha256=task.source_archive_sha256,
            mirror_sha256=_metadata_sha256(task, "source_tree_hash"),
            decontamination_status=source.decontamination_status,
            current_commit=None,
            working_tree_clean=source.working_tree_clean,
            dirty_snapshot_allowed=source.allow_dirty_snapshot,
            remotes_stripped=True,
            branches_stripped=True,
            tags_stripped=True,
            materialization_command_facts=_copy_command_facts(
                source_type="fixed_local_mirror",
                input_kind="local_directory",
            ),
        )
        return SourceCheckout(root=destination, facts=facts)
    git_commit = _git_output(source_path, ["rev-parse", "HEAD"])
    if git_commit is None and source.base_commit:
        _copy_source_tree(source_path, destination)
        facts = _facts_for_local_tree(
            task=task,
            root=destination,
            source_type="fixed_local_mirror",
            remote_url=task.decontamination_metadata.source_url,
            mirror_source=task.decontamination_metadata.source_url or "fixed_local_mirror",
            base_commit=source.base_commit,
            resolved_commit=source.base_commit,
            synthetic_base_id=None,
            archive_sha256=task.source_archive_sha256,
            mirror_sha256=_metadata_sha256(task, "source_tree_hash"),
            decontamination_status=source.decontamination_status,
            current_commit=None,
            working_tree_clean=source.working_tree_clean,
            dirty_snapshot_allowed=source.allow_dirty_snapshot,
            remotes_stripped=True,
            branches_stripped=True,
            tags_stripped=True,
            materialization_command_facts=_copy_command_facts(
                source_type="fixed_local_mirror",
                input_kind="local_directory",
            ),
        )
        return SourceCheckout(root=destination, facts=facts)
    if git_commit is None:
        raise WorkspaceError("local_repository source must be a Git repository with readable HEAD.")
    if source.current_commit is not None and git_commit is not None and source.current_commit != git_commit:
        raise WorkspaceError(
            "local_repository current_commit does not match the repository HEAD."
        )
    current_commit = git_commit
    actual_working_tree_clean = _git_working_tree_clean(source_path)
    if actual_working_tree_clean is None:
        raise WorkspaceError("local_repository source must have readable git status.")
    if (
        source.working_tree_clean is not None
        and actual_working_tree_clean is not None
        and source.working_tree_clean != actual_working_tree_clean
    ):
        raise WorkspaceError(
            "local_repository working_tree_clean declaration does not match git status."
        )
    working_tree_clean = (
        actual_working_tree_clean
        if actual_working_tree_clean is not None
        else source.working_tree_clean
    )
    if working_tree_clean is False and not source.allow_dirty_snapshot:
        raise WorkspaceError(
            "local_repository source has a dirty working tree; set allow_dirty_snapshot=true "
            "only for explicitly controlled task snapshots."
        )
    _copy_source_tree(source_path, destination)
    facts = _facts_for_local_tree(
        task=task,
        root=destination,
        source_type="local_repository",
        remote_url=task.decontamination_metadata.source_url,
        mirror_source=task.decontamination_metadata.source_url or "local_repository",
        base_commit=source.base_commit or current_commit or task.base_commit,
        resolved_commit=current_commit or source.base_commit or task.base_commit,
        synthetic_base_id=source.synthetic_base_id if not (source.base_commit or current_commit or task.base_commit) else None,
        archive_sha256=task.source_archive_sha256,
        mirror_sha256=None,
        decontamination_status=source.decontamination_status,
        current_commit=current_commit,
        working_tree_clean=working_tree_clean,
        dirty_snapshot_allowed=source.allow_dirty_snapshot,
        remotes_stripped=True,
        branches_stripped=True,
        tags_stripped=True,
        materialization_command_facts=_copy_command_facts(
            source_type="local_repository",
            input_kind="git_worktree_copy",
        ),
    )
    return SourceCheckout(root=destination, facts=facts)


def _materialize_archive(
    *,
    task: RunnableTask,
    source: object,
    destination: Path,
    source_type: str,
    archive_path: Path,
    archive_sha256: str,
    expected_root_directory: str,
    base_commit: str | None,
    synthetic_base_id: str | None,
    decontamination_status: str,
    remotes_stripped: bool,
    branches_stripped: bool,
    tags_stripped: bool,
) -> SourceCheckout:
    if not archive_path.exists() or not archive_path.is_file():
        raise WorkspaceError(f"{source_type} archive does not exist: {archive_path}")
    actual_sha = compute_file_sha256(archive_path)
    if actual_sha != archive_sha256:
        raise WorkspaceError(
            f"{source_type} archive sha256 mismatch: expected {archive_sha256}, got {actual_sha}"
        )
    with tempfile.TemporaryDirectory(prefix="repo_harness_extract_") as temp_dir:
        extract_root = Path(temp_dir)
        _extract_archive(archive_path, extract_root)
        source_root = (extract_root / expected_root_directory).resolve()
        try:
            source_root.relative_to(extract_root.resolve())
        except ValueError as exc:
            raise WorkspaceError("expected_root_directory escapes extracted archive root.") from exc
        if not source_root.exists() or not source_root.is_dir():
            raise WorkspaceError(
                f"expected_root_directory not found in archive: {expected_root_directory}"
            )
        _copy_source_tree(source_root, destination)
    facts = _facts_for_local_tree(
        task=task,
        root=destination,
        source_type=source_type,
        remote_url=getattr(source, "remote_url", None) or task.decontamination_metadata.source_url,
        mirror_source=getattr(source, "mirror_source", None) or source_type,
        base_commit=base_commit,
        resolved_commit=base_commit,
        synthetic_base_id=synthetic_base_id,
        archive_sha256=archive_sha256,
        mirror_sha256=None,
        decontamination_status=decontamination_status,
        remotes_stripped=remotes_stripped,
        branches_stripped=branches_stripped,
        tags_stripped=tags_stripped,
        materialization_command_facts=_extract_command_facts(
            source_type=source_type,
            expected_root_directory=expected_root_directory,
        ),
    )
    return SourceCheckout(root=destination, facts=facts)


def _facts_for_local_tree(
    *,
    task: RunnableTask,
    root: Path,
    source_type: str,
    remote_url: str | None,
    mirror_source: str | None,
    base_commit: str | None,
    resolved_commit: str | None,
    synthetic_base_id: str | None,
    archive_sha256: str | None,
    mirror_sha256: str | None,
    decontamination_status: str | None,
    current_commit: str | None = None,
    working_tree_clean: bool | None = None,
    dirty_snapshot_allowed: bool = False,
    remotes_stripped: bool | None = None,
    branches_stripped: bool | None = None,
    tags_stripped: bool | None = None,
    materialization_command_facts: dict[str, Any] | None = None,
) -> SourceCheckoutFacts:
    return SourceCheckoutFacts(
        source_kind=task.metadata.get("source_kind") or source_type,
        source_type=source_type,
        remote_url=remote_url,
        mirror_source=mirror_source,
        base_commit=base_commit,
        resolved_commit=resolved_commit or current_commit or base_commit,
        synthetic_base_id=synthetic_base_id if not base_commit else None,
        source_archive_sha256=archive_sha256,
        mirror_sha256=mirror_sha256,
        source_tree_hash=compute_source_tree_hash(root),
        checkout_path_status="redacted",
        decontamination_status=decontamination_status,
        current_commit=current_commit,
        working_tree_clean=working_tree_clean,
        dirty_snapshot_allowed=dirty_snapshot_allowed,
        remotes_stripped=remotes_stripped,
        branches_stripped=branches_stripped,
        tags_stripped=tags_stripped,
        materialization_policy_version=SOURCE_MATERIALIZATION_POLICY_VERSION,
        materialization_command_facts=materialization_command_facts or {},
    )


def _copy_command_facts(*, source_type: str, input_kind: str) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_source_materialization_command_facts_v3_v0",
        "command_name": "copy_source_tree",
        "argv": ["copy_source_tree", "<source:redacted>", "<destination:redacted>"],
        "source_type": source_type,
        "input_kind": input_kind,
        "cwd_status": "not_applicable",
        "input_path_status": "redacted",
        "output_path_status": "redacted",
        "network_used": False,
    }


def _extract_command_facts(*, source_type: str, expected_root_directory: str) -> dict[str, Any]:
    return {
        "schema_version": "repo_harness_source_materialization_command_facts_v3_v0",
        "command_name": "extract_fixed_archive",
        "argv": [
            "extract_fixed_archive",
            "<archive:redacted>",
            expected_root_directory,
            "<destination:redacted>",
        ],
        "source_type": source_type,
        "input_kind": "fixed_archive",
        "cwd_status": "not_applicable",
        "input_path_status": "redacted",
        "output_path_status": "redacted",
        "expected_root_directory": expected_root_directory,
        "network_used": False,
    }


def _metadata_sha256(task: RunnableTask, key: str) -> str | None:
    value = task.metadata.get(key)
    if isinstance(value, str) and len(value) == 64:
        return value
    return None


def _copy_source_tree(source: Path, destination: Path) -> None:
    if not source.exists() or not source.is_dir():
        raise WorkspaceError(f"source directory does not exist: {source}")
    shutil.copytree(source, destination, ignore=_ignore_source_control, symlinks=True)


def _ignore_source_control(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in {".git", ".hg", ".svn"}}


def _extract_archive(archive_path: Path, destination: Path) -> None:
    suffixes = "".join(archive_path.suffixes)
    if suffixes.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                _ensure_safe_archive_member(destination, member.filename)
            archive.extractall(destination)
        return
    if suffixes.endswith((".tar", ".tar.gz", ".tgz")):
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                _ensure_safe_archive_member(destination, member.name)
            archive.extractall(destination, filter="data")
        return
    raise WorkspaceError(f"unsupported archive format: {archive_path.name}")


def _ensure_safe_archive_member(destination: Path, member_name: str) -> None:
    target = (destination / member_name).resolve()
    try:
        target.relative_to(destination.resolve())
    except ValueError as exc:
        raise WorkspaceError(f"archive member escapes extraction root: {member_name}") from exc


def _git_output(repo_path: Path, args: list[str]) -> str | None:
    result = subprocess.run(
        ["git", "-C", repo_path.as_posix(), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_working_tree_clean(repo_path: Path) -> bool | None:
    status = _git_output(repo_path, ["status", "--short"])
    if status is None:
        return None
    return status == ""
