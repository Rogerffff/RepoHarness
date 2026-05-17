from __future__ import annotations

from pathlib import Path

from repo_harness.workspace import WorkspaceSnapshotManager, build_workspace_snapshot_key


def _source_tree(root: Path) -> Path:
    source = root / "source"
    source.mkdir()
    (source / "calculator.py").write_text("VALUE = 1\n", encoding="utf-8")
    return source


def test_stage12_5_shared_workspace_snapshot_cache_hits_across_episodes(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "shared-cache")
    key = build_workspace_snapshot_key(
        repo_ref="stage12-5-repo",
        environment_id="rhenv-shared",
        dependency_lock_hash="lock-hash",
        harness_version="stage12_5",
    )

    first = manager.create_or_get_snapshot(key, source_path=source)
    second = manager.create_or_get_snapshot(key, source_path=source)

    assert first.snapshot_cache_hit is False
    assert second.snapshot_cache_hit is True
    assert first.facts.snapshot_key == second.facts.snapshot_key


def test_stage12_5_directory_copy_lease_write_does_not_pollute_snapshot_or_other_lease(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "shared-cache")
    snapshot = manager.create_or_get_snapshot(
        build_workspace_snapshot_key(
            repo_ref="stage12-5-repo",
            environment_id="rhenv-shared",
            dependency_lock_hash="lock-hash",
            harness_version="stage12_5",
        ),
        source_path=source,
    )

    first = manager.acquire_workspace(snapshot, lease_id="lease-one")
    second = manager.acquire_workspace(snapshot, lease_id="lease-two")
    (first.workspace_path / "calculator.py").write_text("VALUE = 99\n", encoding="utf-8")

    assert (second.workspace_path / "calculator.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    snapshot_file = manager.snapshots_dir / snapshot.facts.snapshot_key / "workspace" / "calculator.py"
    assert snapshot_file.read_text(encoding="utf-8") == "VALUE = 1\n"
