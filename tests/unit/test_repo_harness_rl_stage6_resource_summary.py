from __future__ import annotations

from pathlib import Path

import pytest

from repo_harness.rl import ResourceSummary, build_timing_summary
from repo_harness.workspace import (
    WorkspaceLease,
    WorkspaceSnapshotFacts,
    WorkspaceSnapshotManager,
    build_workspace_snapshot_key,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


def _source(root: Path) -> Path:
    source = root / "source"
    source.mkdir(parents=True)
    (source / "app.py").write_text("print('stage6')\n", encoding="utf-8")
    return source


def test_stage6_workspace_reuse_projects_safe_resource_and_timing_summary(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="env",
        setup_command_hash="setup",
        dependency_lock_hash="lock",
        harness_version="stage6-test",
        source_tree_hash=compute_source_tree_hash(source),
    )
    snapshot = manager.create_or_get_snapshot(key, source_path=source)
    lease = manager.acquire_workspace(snapshot, lease_id="episode-1", dependency_restore_seconds=0.001)
    released = manager.release_workspace(lease)

    resource = ResourceSummary(
        **manager.resource_summary_fields(
            snapshot=snapshot,
            lease=released.lease,
            workspace_backend="local_process",
            dependency_cache_key="dep-cache-key",
            dependency_cache_hit=False,
            baseline_cache_hit=False,
            container_reuse_hit=False,
            run_dir="runs/stage6-resource-summary",
        )
    )
    timing_fields = manager.timing_summary_fields(released)
    timing = build_timing_summary(
        rollout_wall_seconds=sum(timing_fields.values()),
        **timing_fields,
    )

    assert resource.snapshot_key == snapshot.facts.snapshot_key
    assert resource.snapshot_cache_hit is False
    assert resource.snapshot_restore_strategy == "directory_copy"
    assert resource.dependency_cache_key == "dep-cache-key"
    assert resource.dependency_cache_hit is False
    assert resource.baseline_cache_hit is False
    assert resource.container_reuse_hit is False
    assert resource.lease_id == "episode-1"
    assert resource.cleanup_status == "completed"
    assert resource.workspace_path == "leases/" + snapshot.facts.snapshot_key + "/episode-1"
    assert resource.run_dir == "runs/stage6-resource-summary"
    assert "/Users/" not in resource.model_dump_json()
    assert str(tmp_path) not in resource.model_dump_json()
    assert timing.workspace_materialization_seconds >= 0.0
    assert timing.dependency_restore_seconds == 0.001
    assert timing.cleanup_seconds >= 0.0


def test_stage6_resource_summary_rejects_snapshot_and_lease_mismatch(tmp_path: Path) -> None:
    source_a = _source(tmp_path / "a")
    source_b = _source(tmp_path / "b")
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key_a = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base-a",
        environment_id="env",
        setup_command_hash="setup",
        dependency_lock_hash="lock",
        harness_version="stage6-test",
        source_tree_hash=compute_source_tree_hash(source_a),
    )
    key_b = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base-b",
        environment_id="env",
        setup_command_hash="setup",
        dependency_lock_hash="lock",
        harness_version="stage6-test",
        source_tree_hash=compute_source_tree_hash(source_b),
    )
    snapshot_a = manager.create_or_get_snapshot(key_a, source_path=source_a)
    snapshot_b = manager.create_or_get_snapshot(key_b, source_path=source_b)
    lease_b = manager.acquire_workspace(snapshot_b, lease_id="episode-b")

    with pytest.raises(Exception, match="snapshot_key does not match"):
        manager.resource_summary_fields(
            snapshot=snapshot_a,
            lease=lease_b.lease,
            workspace_backend="local_process",
        )


def test_stage6_resource_summary_rejects_malformed_lease_path(tmp_path: Path) -> None:
    source = _source(tmp_path)
    manager = WorkspaceSnapshotManager(tmp_path / "cache")
    key = build_workspace_snapshot_key(
        repo_ref="repo",
        base_commit="base",
        environment_id="env",
        setup_command_hash="setup",
        dependency_lock_hash="lock",
        harness_version="stage6-test",
        source_tree_hash=compute_source_tree_hash(source),
    )
    snapshot = manager.create_or_get_snapshot(key, source_path=source)
    lease = WorkspaceLease(
        lease_id="episode-1",
        workspace_id="workspace-episode-1",
        snapshot_key=snapshot.facts.snapshot_key,
        workspace_path=f"leases/{snapshot.facts.snapshot_key}/different-id",
        created_at_unix=1.0,
    )

    with pytest.raises(Exception, match="leases/<snapshot_key>/<lease_id>"):
        manager.resource_summary_fields(
            snapshot=snapshot,
            lease=lease,
            workspace_backend="local_process",
        )


def test_stage6_resource_summary_rejects_absolute_workspace_and_run_paths() -> None:
    with pytest.raises(ValueError, match="workspace_path"):
        ResourceSummary(workspace_path="/Users/roger/private/workspace")
    with pytest.raises(ValueError, match="run_dir"):
        ResourceSummary(run_dir="/Users/roger/private/run")
    with pytest.raises(ValueError, match="snapshot_key"):
        ResourceSummary(snapshot_key="/Users/roger/private/snapshot")
    with pytest.raises(ValueError, match="lease_id"):
        ResourceSummary(lease_id="/Users/roger/private/lease")
    with pytest.raises(ValueError, match="dependency_cache_key"):
        ResourceSummary(dependency_cache_key="/Users/roger/private/dependency-cache")


def test_stage6_snapshot_facts_and_lease_reject_absolute_path_projection() -> None:
    with pytest.raises(ValueError, match="diagnostics"):
        WorkspaceSnapshotFacts(
            snapshot_key="wssnap-test",
            snapshot_ref="rh://workspace-snapshot/wssnap-test",
            toolchain_version="python-3.12",
            harness_version="stage6-test",
            source_tree_hash="a" * 64,
            created_by="test",
            created_at_unix=1.0,
            diagnostics=["leaked /Users/roger/private/cache"],
        )
    with pytest.raises(ValueError, match="workspace_path"):
        WorkspaceLease(
            lease_id="lease-1",
            workspace_id="workspace-1",
            snapshot_key="wssnap-test",
            workspace_path="/Users/roger/private/workspace",
            created_at_unix=1.0,
        )
