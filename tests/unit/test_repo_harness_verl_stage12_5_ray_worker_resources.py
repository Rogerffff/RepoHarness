from __future__ import annotations

import pytest

from repo_harness_verl import build_ray_worker_resource_profile, build_system_resource_profile


MANAGER_MODES = {
    "runtime_manager": "per_ray_worker",
    "workspace_snapshot_manager": "cross_ray_worker_shared_cache",
    "dependency_environment_manager": "cross_ray_worker_shared_cache",
    "verifier_pool": "per_ray_worker",
    "resource_lease_manager": "per_ray_worker",
    "route_limiter": "per_ray_worker",
}


def test_stage12_5_ray_worker_profile_records_manager_sharing_boundaries() -> None:
    profile = build_ray_worker_resource_profile(
        manager_modes=MANAGER_MODES,
        ray_worker_id="worker-0",
        active_agent_loop_threads=2,
        queue_wait_seconds=[0.1, 0.3],
        ray_actor_cpu_percent=62.5,
    )

    assert profile.workspace_snapshot_manager_mode == "cross_ray_worker_shared_cache"
    assert profile.agent_loop_worker_queue_wait_seconds_p50 == 0.2
    assert profile.active_agent_loop_threads == 2


def test_stage12_5_ray_worker_profile_rejects_unknown_manager_mode() -> None:
    bad = {**MANAGER_MODES, "route_limiter": "global_unbounded"}

    with pytest.raises(ValueError, match="route_limiter"):
        build_ray_worker_resource_profile(manager_modes=bad)


def test_stage12_5_system_resource_profile_records_cleanup_and_io_facts() -> None:
    profile = build_system_resource_profile(
        open_file_descriptor_count=128,
        disk_read_bytes=1024,
        disk_write_bytes=2048,
        run_directory_file_count=64,
        cleanup_orphan_count=1,
        workspace_cleanup_seconds=[0.2, 0.4],
        verifier_subprocess_count=2,
    )

    assert profile.workspace_cleanup_seconds_p50 == pytest.approx(0.3)
    assert profile.cleanup_orphan_count == 1
