from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from repo_harness.errors import WorkspaceError
from repo_harness.workspace import (
    RESOURCE_CLEANUP_COMPLETED,
    RESOURCE_CLEANUP_FAILED,
    WorkspaceLease,
    WorkspaceLeaseHandle,
    WorkspaceSnapshotKey,
    WorkspaceSnapshotManager,
    build_workspace_snapshot_key,
    copy_declared_dependency_paths,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


def _write_source(root: Path, *, content: str = "print('hello')\n") -> Path:
    source = root / "source"
    package = source / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "main.py").write_text(content, encoding="utf-8")
    (source / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    return source


def _snapshot_key(source: Path, *, environment_id: str = "py312"):
    return build_workspace_snapshot_key(
        repo_ref="github.com/example/demo",
        base_commit="abc123",
        environment_id=environment_id,
        setup_command="python -m pip install -e .",
        dependency_lock_hash="lock-hash",
        harness_version="stage6-test",
        source_tree_hash=compute_source_tree_hash(source),
    )


def test_stage6_snapshot_key_is_stable_and_changes_on_environment() -> None:
    first = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="py312",
        setup_command="setup",
        dependency_lock_hash="lock",
        harness_version="harness",
        source_archive_sha256="a" * 64,
    )
    second = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="py312",
        setup_command="setup",
        dependency_lock_hash="lock",
        harness_version="harness",
        source_archive_sha256="a" * 64,
    )
    changed = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="py313",
        setup_command="setup",
        dependency_lock_hash="lock",
        harness_version="harness",
        source_archive_sha256="a" * 64,
    )

    assert first.snapshot_key == second.snapshot_key
    assert first.snapshot_key != changed.snapshot_key


def test_stage6_snapshot_create_then_hit_uses_published_facts(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache", creator_id="test-creator")
    key = _snapshot_key(source)

    first = manager.create_or_get_snapshot(key, source_path=source)
    second = manager.create_or_get_snapshot(key, source_path=source)

    assert first.snapshot_cache_hit is False
    assert second.snapshot_cache_hit is True
    assert first.facts.snapshot_key == second.facts.snapshot_key == key.snapshot_key
    assert first.facts.source_tree_hash == compute_source_tree_hash(source)
    assert first.facts.clean_state_verified is False
    assert first.facts.clean_state_verification == "source_tree_hash_verified_after_materialization"
    assert (tmp_path / "cache" / "snapshots" / key.snapshot_key / "snapshot_facts.json").exists()


def test_stage6_snapshot_key_supports_prelookup_then_post_materialization_verification(
    tmp_path: Path,
) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    prelookup_key = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="env",
        setup_command_hash="setup-hash",
        dependency_lock_hash="lock-hash",
        harness_version="stage6-test",
        source_archive_sha256="b" * 64,
        diagnostics=["source_tree_hash unavailable before materialization"],
    )

    result = manager.create_or_get_snapshot(prelookup_key, source_path=source)

    assert result.snapshot_cache_hit is False
    assert result.facts.source_tree_hash == compute_source_tree_hash(source)
    assert result.facts.diagnostics == ["source_tree_hash unavailable before materialization"]


def test_stage6_snapshot_without_prelookup_hash_computes_source_identity_before_lookup(
    tmp_path: Path,
) -> None:
    source_a = _write_source(tmp_path / "a", content="print('a')\n")
    source_b = _write_source(tmp_path / "b", content="print('b')\n")
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key_without_content_hash = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="env",
        setup_command_hash="setup-hash",
        dependency_lock_hash="lock-hash",
        harness_version="stage6-test",
    )

    first = manager.create_or_get_snapshot(key_without_content_hash, source_path=source_a)
    second = manager.create_or_get_snapshot(key_without_content_hash, source_path=source_b)
    third = manager.create_or_get_snapshot(key_without_content_hash, source_path=source_a)

    assert first.snapshot_cache_hit is False
    assert second.snapshot_cache_hit is False
    assert third.snapshot_cache_hit is True
    assert first.facts.source_tree_hash != second.facts.source_tree_hash
    assert first.facts.snapshot_key != second.facts.snapshot_key
    assert "source_tree_hash computed from source_path" in first.facts.diagnostics[0]


def test_stage6_rejects_unsafe_snapshot_key_and_lease_id(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    with pytest.raises(ValueError, match="snapshot_key"):
        WorkspaceSnapshotKey(
            snapshot_key="../escape",
            repo_ref="repo",
            base_commit="base",
            environment_id="env",
            toolchain_version="python-3.12",
            harness_version="stage6-test",
            source_tree_hash=compute_source_tree_hash(source),
        )

    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    snapshot = manager.create_or_get_snapshot(_snapshot_key(source), source_path=source)
    with pytest.raises(ValueError, match="lease_id"):
        manager.acquire_workspace(snapshot, lease_id="../escape")


def test_stage6_snapshot_rejects_post_materialization_source_hash_mismatch(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="env",
        setup_command_hash="setup-hash",
        dependency_lock_hash="lock-hash",
        harness_version="stage6-test",
        source_tree_hash="0" * 64,
    )

    with pytest.raises(WorkspaceError, match="source_tree_hash mismatch"):
        manager.create_or_get_snapshot(key, source_path=source)


def test_stage6_snapshot_rejects_source_tree_symlink_escape(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    host_secret = tmp_path / "host-secret.txt"
    host_secret.write_text("secret outside source tree", encoding="utf-8")
    (source / "pkg" / "external-secret-link").symlink_to(host_secret)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")

    with pytest.raises(WorkspaceError, match="workspace snapshot source symlink"):
        manager.create_or_get_snapshot(_snapshot_key(source), source_path=source)


def test_stage6_snapshot_cache_hit_rejects_published_symlink_escape(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key = _snapshot_key(source)
    snapshot = manager.create_or_get_snapshot(key, source_path=source)
    host_secret = tmp_path / "host-secret.txt"
    host_secret.write_text("secret outside source tree", encoding="utf-8")
    snapshot_workspace = (
        tmp_path
        / "cache"
        / "snapshots"
        / snapshot.facts.snapshot_key
        / "workspace"
    )
    (snapshot_workspace / "pkg" / "external-secret-link").symlink_to(host_secret)

    with pytest.raises(WorkspaceError, match="published workspace snapshot symlink"):
        manager.create_or_get_snapshot(key, source_path=source)


def test_stage6_workspace_lease_rejects_published_snapshot_symlink_escape(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    snapshot = manager.create_or_get_snapshot(_snapshot_key(source), source_path=source)
    host_secret = tmp_path / "host-secret.txt"
    host_secret.write_text("secret outside source tree", encoding="utf-8")
    snapshot_workspace = (
        tmp_path
        / "cache"
        / "snapshots"
        / snapshot.facts.snapshot_key
        / "workspace"
    )
    (snapshot_workspace / "pkg" / "external-secret-link").symlink_to(host_secret)

    with pytest.raises(WorkspaceError, match="published workspace snapshot symlink"):
        manager.acquire_workspace(snapshot, lease_id="symlink-escape")


def test_stage6_concurrent_snapshot_create_publishes_once(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key = _snapshot_key(source)

    def create_snapshot():
        return manager.create_or_get_snapshot(key, source_path=source).snapshot_cache_hit

    with ThreadPoolExecutor(max_workers=2) as executor:
        hits = list(executor.map(lambda _: create_snapshot(), range(2)))

    assert sorted(hits) == [False, True]
    assert (tmp_path / "cache" / "snapshots" / key.snapshot_key).is_dir()


def test_stage6_leases_are_isolated_and_cleanup_is_recorded(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    snapshot = manager.create_or_get_snapshot(_snapshot_key(source), source_path=source)

    first = manager.acquire_workspace(snapshot, lease_id="episode-a")
    second = manager.acquire_workspace(snapshot, lease_id="episode-b")
    (first.workspace_path / "only-a.txt").write_text("episode a", encoding="utf-8")

    assert first.lease.lease_id != second.lease.lease_id
    assert first.workspace_path != second.workspace_path
    assert not (second.workspace_path / "only-a.txt").exists()
    assert not (
        tmp_path
        / "cache"
        / "snapshots"
        / snapshot.facts.snapshot_key
        / "workspace"
        / "only-a.txt"
    ).exists()

    released = manager.release_workspace(first)

    assert released.lease.cleanup_status == RESOURCE_CLEANUP_COMPLETED
    assert not released.workspace_path.exists()


def test_stage6_cleanup_failure_is_structured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    snapshot = manager.create_or_get_snapshot(_snapshot_key(source), source_path=source)
    lease = manager.acquire_workspace(snapshot, lease_id="cleanup-fails")

    def fail_rmtree(path: Path) -> None:
        raise OSError("simulated cleanup failure")

    monkeypatch.setattr("repo_harness.workspace.reuse.shutil.rmtree", fail_rmtree)

    released = manager.release_workspace(lease)

    assert released.lease.cleanup_status == RESOURCE_CLEANUP_FAILED
    assert released.lease.cleanup_error == "simulated cleanup failure"
    assert "workspace lease cleanup failed" in released.lease.diagnostics


def test_stage6_release_does_not_delete_workspace_outside_manager_leases_dir(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    snapshot = manager.create_or_get_snapshot(_snapshot_key(source), source_path=source)
    external = tmp_path / "external-workspace"
    external.mkdir()
    (external / "keep.txt").write_text("do not delete", encoding="utf-8")
    forged_lease = WorkspaceLease(
        lease_id="forged",
        workspace_id="workspace-forged",
        snapshot_key=snapshot.facts.snapshot_key,
        workspace_path=f"leases/{snapshot.facts.snapshot_key}/forged",
        created_at_unix=1.0,
    )
    forged_handle = WorkspaceLeaseHandle(lease=forged_lease, workspace_path=external)

    released = manager.release_workspace(forged_handle)

    assert released.lease.cleanup_status == RESOURCE_CLEANUP_FAILED
    assert "workspace lease path ownership check failed" in released.lease.diagnostics
    assert (external / "keep.txt").exists()


def test_stage6_copy_declared_dependency_paths_rejects_sensitive_and_escape_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "dep-source"
    destination = tmp_path / "dep-destination"
    (source / ".venv" / "lib").mkdir(parents=True)
    (source / ".venv" / "lib" / "package.py").write_text("x = 1\n", encoding="utf-8")
    (source / ".env").write_text("SECRET=1\n", encoding="utf-8")

    copied = copy_declared_dependency_paths(
        source_root=source,
        destination_root=destination,
        declared_paths=[".venv"],
    )

    assert copied == [".venv"]
    assert (destination / ".venv" / "lib" / "package.py").exists()
    with pytest.raises(WorkspaceError, match="sensitive"):
        copy_declared_dependency_paths(
            source_root=source,
            destination_root=tmp_path / "bad-sensitive",
            declared_paths=[".env"],
        )
    with pytest.raises(WorkspaceError, match="relative"):
        copy_declared_dependency_paths(
            source_root=source,
            destination_root=tmp_path / "bad-parent",
            declared_paths=["../outside"],
        )


def test_stage6_copy_declared_dependency_paths_rejects_nested_sensitive_files(
    tmp_path: Path,
) -> None:
    sensitive_names = [
        ".env",
        ".env.local",
        ".SSH/config",
        ".AWS/credentials",
        ".config/gh/hosts.yml",
        ".config/gcloud/configurations/config_default",
        "token.txt",
        "TOKEN.TXT",
        "secret.txt",
        "SECRET.txt",
        "credential",
        "credential.json",
        "credentials.toml",
        "private.PEM",
        "private.KEY",
    ]
    for index, sensitive_name in enumerate(sensitive_names):
        source = tmp_path / f"dep-source-{index}"
        destination = tmp_path / f"dep-destination-{index}"
        (source / ".venv" / "lib").mkdir(parents=True)
        (source / ".venv" / "lib" / "package.py").write_text("x = 1\n", encoding="utf-8")
        sensitive_path = source / ".venv" / sensitive_name
        sensitive_path.parent.mkdir(parents=True, exist_ok=True)
        sensitive_path.write_text("SECRET=1\n", encoding="utf-8")

        with pytest.raises(WorkspaceError, match="sensitive"):
            copy_declared_dependency_paths(
                source_root=source,
                destination_root=destination,
                declared_paths=[".venv"],
            )
        assert not (destination / ".venv" / sensitive_name).exists()


def test_stage6_copy_declared_dependency_paths_rejects_escape_symlink(tmp_path: Path) -> None:
    source = tmp_path / "dep-source"
    destination = tmp_path / "dep-destination"
    host_secret = tmp_path / "host-secret.txt"
    (source / ".venv").mkdir(parents=True)
    host_secret.write_text("secret", encoding="utf-8")
    (source / ".venv" / "leak").symlink_to(host_secret)

    with pytest.raises(WorkspaceError, match="absolute target|escapes allowed root"):
        copy_declared_dependency_paths(
            source_root=source,
            destination_root=destination,
            declared_paths=[".venv"],
        )
