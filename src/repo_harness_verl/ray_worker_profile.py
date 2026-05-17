"""Stage 12.5 Ray worker and local system resource profile schemas."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

ManagerSharingMode = Literal["per_episode", "per_ray_worker", "cross_ray_worker_shared_cache"]


class RayWorkerResourceProfile(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_ray_worker_resource_profile_v0"
    ray_worker_id: str | None = None
    runtime_manager_mode: ManagerSharingMode
    workspace_snapshot_manager_mode: ManagerSharingMode
    dependency_environment_manager_mode: ManagerSharingMode
    verifier_pool_mode: ManagerSharingMode
    resource_lease_manager_mode: ManagerSharingMode
    route_limiter_mode: ManagerSharingMode
    active_agent_loop_threads: int = Field(default=0, ge=0)
    agent_loop_worker_queue_wait_seconds_p50: float | None = Field(default=None, ge=0.0)
    agent_loop_worker_queue_wait_seconds_p95: float | None = Field(default=None, ge=0.0)
    ray_actor_cpu_percent: float | None = Field(default=None, ge=0.0)
    diagnostics: list[str] = Field(default_factory=list)


class SystemResourceProfile(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_system_resource_profile_v0"
    open_file_descriptor_count: int | None = Field(default=None, ge=0)
    disk_read_bytes: int | None = Field(default=None, ge=0)
    disk_write_bytes: int | None = Field(default=None, ge=0)
    run_directory_file_count: int | None = Field(default=None, ge=0)
    cleanup_orphan_count: int = Field(default=0, ge=0)
    workspace_cleanup_seconds_p50: float | None = Field(default=None, ge=0.0)
    workspace_cleanup_seconds_p95: float | None = Field(default=None, ge=0.0)
    verifier_subprocess_count: int | None = Field(default=None, ge=0)
    diagnostics: list[str] = Field(default_factory=list)


def build_ray_worker_resource_profile(
    *,
    manager_modes: Mapping[str, str],
    ray_worker_id: str | None = None,
    active_agent_loop_threads: int = 0,
    queue_wait_seconds: list[float] | None = None,
    ray_actor_cpu_percent: float | None = None,
    diagnostics: list[str] | None = None,
) -> RayWorkerResourceProfile:
    waits = list(queue_wait_seconds or [])
    return RayWorkerResourceProfile(
        ray_worker_id=ray_worker_id,
        runtime_manager_mode=_mode(manager_modes, "runtime_manager"),
        workspace_snapshot_manager_mode=_mode(manager_modes, "workspace_snapshot_manager"),
        dependency_environment_manager_mode=_mode(manager_modes, "dependency_environment_manager"),
        verifier_pool_mode=_mode(manager_modes, "verifier_pool"),
        resource_lease_manager_mode=_mode(manager_modes, "resource_lease_manager"),
        route_limiter_mode=_mode(manager_modes, "route_limiter"),
        active_agent_loop_threads=active_agent_loop_threads,
        agent_loop_worker_queue_wait_seconds_p50=_percentile(waits, 50),
        agent_loop_worker_queue_wait_seconds_p95=_percentile(waits, 95),
        ray_actor_cpu_percent=ray_actor_cpu_percent,
        diagnostics=list(diagnostics or []),
    )


def build_system_resource_profile(
    *,
    open_file_descriptor_count: int | None = None,
    disk_read_bytes: int | None = None,
    disk_write_bytes: int | None = None,
    run_directory_file_count: int | None = None,
    cleanup_orphan_count: int = 0,
    workspace_cleanup_seconds: list[float] | None = None,
    verifier_subprocess_count: int | None = None,
    diagnostics: list[str] | None = None,
) -> SystemResourceProfile:
    cleanup = list(workspace_cleanup_seconds or [])
    return SystemResourceProfile(
        open_file_descriptor_count=open_file_descriptor_count,
        disk_read_bytes=disk_read_bytes,
        disk_write_bytes=disk_write_bytes,
        run_directory_file_count=run_directory_file_count,
        cleanup_orphan_count=cleanup_orphan_count,
        workspace_cleanup_seconds_p50=_percentile(cleanup, 50),
        workspace_cleanup_seconds_p95=_percentile(cleanup, 95),
        verifier_subprocess_count=verifier_subprocess_count,
        diagnostics=list(diagnostics or []),
    )


def _mode(manager_modes: Mapping[str, str], key: str) -> ManagerSharingMode:
    value = manager_modes.get(key)
    allowed = {"per_episode", "per_ray_worker", "cross_ray_worker_shared_cache"}
    if value not in allowed:
        raise ValueError(f"{key} mode must be one of {sorted(allowed)}")
    return value  # type: ignore[return-value]


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
