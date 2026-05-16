"""Local resource lease helpers for concurrent RepoHarness episodes."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel, stable_hash

from .visibility import (
    ALLOWED_ROUTES,
    CONTRACT_VERSION,
    GatewayRoute,
    validate_no_absolute_local_path,
    validate_safe_identifier,
)

RESOURCE_LEASE_POLICY_VERSION = "repo_harness_resource_lease_stage9_v0"
CLEANUP_STATUS_NOT_STARTED = "not_started"
CLEANUP_STATUS_COMPLETED = "completed"
CLEANUP_STATUS_FAILED = "failed"
CLEANUP_STATUS_SKIPPED = "skipped"
CANONICAL_CLEANUP_STATUSES = {
    CLEANUP_STATUS_NOT_STARTED,
    CLEANUP_STATUS_COMPLETED,
    CLEANUP_STATUS_FAILED,
    CLEANUP_STATUS_SKIPPED,
}

ResourceErrorStatus = Literal["timeout", "infrastructure_error", "invalid_task", "cancelled"]
CleanupStatus = Literal["not_started", "completed", "failed", "skipped"]


class ResourceLeaseError(RuntimeError):
    """Raised when a local resource lease cannot be acquired or released safely."""

    def __init__(
        self,
        message: str,
        *,
        status_reason: str,
        episode_status: ResourceErrorStatus = "infrastructure_error",
        resource_name: str | None = None,
        queue_wait_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_reason = status_reason
        self.episode_status = episode_status
        self.resource_name = resource_name
        self.queue_wait_seconds = queue_wait_seconds


class ResourceConcurrencyPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_resource_concurrency_policy_stage9_v0"
    contract_version: str = CONTRACT_VERSION
    policy_version: str = RESOURCE_LEASE_POLICY_VERSION
    worker_id: str = "local-worker-0"
    concurrency_group: str = "training-fast-local"
    max_concurrent_episodes: int = Field(default=1, ge=1)
    max_workspace_leases: int = Field(default=1, ge=1)
    max_gateway_route_concurrency_by_route: dict[str, int] = Field(
        default_factory=lambda: {
            "verl": 8,
            "openai": 2,
            "deepseek": 2,
            "local_vllm": 4,
            "local_sglang": 4,
            "replay": 32,
            "mock": 32,
        }
    )
    episode_queue_timeout_seconds: float | None = Field(default=None, gt=0)
    workspace_queue_timeout_seconds: float | None = Field(default=None, gt=0)
    route_queue_timeout_seconds: float | None = Field(default=None, gt=0)
    recorder_lock_timeout_seconds: float | None = Field(default=None, gt=0)
    cleanup_timeout_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_policy(self) -> "ResourceConcurrencyPolicy":
        for field_name in ["worker_id", "concurrency_group"]:
            validate_no_absolute_local_path(getattr(self, field_name), field_name=field_name)
        unknown_routes = set(self.max_gateway_route_concurrency_by_route) - ALLOWED_ROUTES
        if unknown_routes:
            raise ValueError(f"unknown gateway route limit keys: {sorted(unknown_routes)}")
        for route, value in self.max_gateway_route_concurrency_by_route.items():
            if value < 1:
                raise ValueError(f"gateway route concurrency must be >= 1 for {route}")
        return self


class ResourceLeaseDiagnostics(StrictBaseModel):
    schema_version: str = "repo_harness_resource_lease_diagnostic_stage9_v0"
    code: str
    message: str
    resource_name: str | None = None
    queue_wait_seconds: float | None = Field(default=None, ge=0.0)
    slot_id: str | None = None

    @model_validator(mode="after")
    def validate_diagnostic(self) -> "ResourceLeaseDiagnostics":
        for field_name in ["code", "message", "resource_name", "slot_id"]:
            value = getattr(self, field_name)
            if value:
                validate_no_absolute_local_path(value, field_name=field_name)
        return self


class ResourceSlotLease(StrictBaseModel):
    schema_version: str = "repo_harness_resource_slot_lease_stage9_v0"
    resource_name: str
    owner_id: str
    slot_id: str
    acquired_at_unix: float = Field(ge=0.0)
    queue_wait_seconds: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_slot(self) -> "ResourceSlotLease":
        for field_name in ["resource_name", "owner_id", "slot_id"]:
            validate_no_absolute_local_path(getattr(self, field_name), field_name=field_name)
        return self


class EpisodeResourceLease(StrictBaseModel):
    schema_version: str = "repo_harness_episode_resource_lease_stage9_v0"
    contract_version: str = CONTRACT_VERSION
    policy_version: str = RESOURCE_LEASE_POLICY_VERSION
    episode_id: str
    run_id: str
    task_id: str
    worker_id: str
    concurrency_group: str
    run_dir_ref: str
    lease_id: str
    workspace_lease_id: str | None = None
    gateway_route_slot_id: str | None = None
    verifier_pool_id: str | None = None
    acquired_at_unix: float = Field(ge=0.0)
    released_at_unix: float | None = Field(default=None, ge=0.0)
    cleanup_status: CleanupStatus = CLEANUP_STATUS_NOT_STARTED
    queue_wait_seconds_by_resource: dict[str, float] = Field(default_factory=dict)
    diagnostics: list[ResourceLeaseDiagnostics] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_episode_lease(self) -> "EpisodeResourceLease":
        for field_name in [
            "episode_id",
            "run_id",
            "task_id",
            "worker_id",
            "concurrency_group",
            "run_dir_ref",
            "lease_id",
            "workspace_lease_id",
            "gateway_route_slot_id",
            "verifier_pool_id",
            "cleanup_status",
        ]:
            value = getattr(self, field_name)
            if value:
                validate_no_absolute_local_path(value, field_name=field_name)
        for resource_name in self.queue_wait_seconds_by_resource:
            validate_no_absolute_local_path(resource_name, field_name="queue_wait_seconds_by_resource")
        return self


class AsyncResourceLimiter:
    """Small async semaphore wrapper that records queue wait and slot identity."""

    def __init__(
        self,
        *,
        resource_name: str,
        max_concurrency: int,
        queue_timeout_seconds: float | None = None,
        timeout_status_reason: str | None = None,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        validate_no_absolute_local_path(resource_name, field_name="resource_name")
        self.resource_name = resource_name
        self.max_concurrency = max_concurrency
        self.queue_timeout_seconds = queue_timeout_seconds
        self.timeout_status_reason = timeout_status_reason or f"{resource_name}_queue_timeout"
        self._semaphore = asyncio.BoundedSemaphore(max_concurrency)
        self._lock = Lock()
        self._active_slots: dict[str, str] = {}
        self._slot_counter = 0

    async def acquire(self, *, owner_id: str) -> ResourceSlotLease:
        validate_no_absolute_local_path(owner_id, field_name="owner_id")
        start = perf_counter()
        try:
            if self.queue_timeout_seconds is None:
                await self._semaphore.acquire()
            else:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=self.queue_timeout_seconds)
        except TimeoutError as exc:
            queue_wait_seconds = perf_counter() - start
            raise ResourceLeaseError(
                f"{self.resource_name} queue timeout after {queue_wait_seconds:.6f} seconds",
                status_reason=self.timeout_status_reason,
                episode_status="timeout",
                resource_name=self.resource_name,
                queue_wait_seconds=queue_wait_seconds,
            ) from exc
        except asyncio.CancelledError:
            raise

        queue_wait_seconds = perf_counter() - start
        try:
            with self._lock:
                self._slot_counter += 1
                slot_id = f"{self.resource_name}-slot-{self._slot_counter}"
                lease = ResourceSlotLease(
                    resource_name=self.resource_name,
                    owner_id=owner_id,
                    slot_id=slot_id,
                    acquired_at_unix=time.time(),
                    queue_wait_seconds=queue_wait_seconds,
                )
                self._active_slots[slot_id] = owner_id
            return lease
        except BaseException:
            self._semaphore.release()
            raise

    async def release(self, lease: ResourceSlotLease) -> ResourceLeaseDiagnostics | None:
        if lease.resource_name != self.resource_name:
            raise ResourceLeaseError(
                "resource slot lease belongs to a different limiter",
                status_reason=f"{self.resource_name}_owner_mismatch",
                resource_name=self.resource_name,
            )
        with self._lock:
            owner = self._active_slots.get(lease.slot_id)
            if owner is None:
                return ResourceLeaseDiagnostics(
                    code=f"{self.resource_name}_double_release",
                    message="resource slot was already released",
                    resource_name=self.resource_name,
                    slot_id=lease.slot_id,
                )
            if owner != lease.owner_id:
                raise ResourceLeaseError(
                    "resource slot owner mismatch",
                    status_reason=f"{self.resource_name}_owner_mismatch",
                    resource_name=self.resource_name,
                )
            del self._active_slots[lease.slot_id]
        self._semaphore.release()
        return None

    @property
    def active_count(self) -> int:
        return len(self._active_slots)


@dataclass
class ResourceLeaseHandle:
    manager: "ResourceLeaseManager"
    owner_id: str
    lease: EpisodeResourceLease
    episode_slot: ResourceSlotLease | None = None
    workspace_slot: ResourceSlotLease | None = None
    route_slots: list[ResourceSlotLease] = field(default_factory=list)
    diagnostics: list[ResourceLeaseDiagnostics] = field(default_factory=list)
    released: bool = False

    def record_route_slot(self, slot: ResourceSlotLease) -> None:
        self.route_slots.append(slot)
        self.lease.queue_wait_seconds_by_resource["gateway_route"] = (
            self.lease.queue_wait_seconds_by_resource.get("gateway_route", 0.0)
            + slot.queue_wait_seconds
        )
        self.lease.gateway_route_slot_id = slot.slot_id


class ResourceLeaseManager:
    """Single-process resource lease manager for Stage 9 runtime safety."""

    def __init__(self, policy: ResourceConcurrencyPolicy | None = None) -> None:
        self.policy = policy or ResourceConcurrencyPolicy()
        self._episode_limiter = AsyncResourceLimiter(
            resource_name="episode",
            max_concurrency=self.policy.max_concurrent_episodes,
            queue_timeout_seconds=self.policy.episode_queue_timeout_seconds,
            timeout_status_reason="episode_queue_timeout",
        )
        self._workspace_limiter = AsyncResourceLimiter(
            resource_name="workspace_lease",
            max_concurrency=self.policy.max_workspace_leases,
            queue_timeout_seconds=self.policy.workspace_queue_timeout_seconds,
            timeout_status_reason="workspace_lease_queue_timeout",
        )
        self._route_limiters: dict[str, AsyncResourceLimiter] = {}
        self._run_lock = asyncio.Lock()
        self._active_run_ids: set[str] = set()

    async def acquire_episode(
        self,
        *,
        episode_id: str,
        run_id: str,
        task_id: str,
    ) -> ResourceLeaseHandle:
        validate_safe_identifier(episode_id, field_name="episode_id")
        validate_safe_identifier(run_id, field_name="run_id")
        validate_safe_identifier(task_id, field_name="task_id")
        owner_id = _owner_id(episode_id=episode_id, run_id=run_id)
        acquired_run_lock = False
        episode_slot: ResourceSlotLease | None = None
        workspace_slot: ResourceSlotLease | None = None
        try:
            await self._acquire_run_directory(run_id)
            acquired_run_lock = True
            episode_slot = await self._episode_limiter.acquire(owner_id=owner_id)
            workspace_slot = await self._workspace_limiter.acquire(owner_id=owner_id)
            lease_id = f"lease-{stable_hash({'episode_id': episode_id, 'run_id': run_id})[:16]}"
            lease = EpisodeResourceLease(
                episode_id=episode_id,
                run_id=run_id,
                task_id=task_id,
                worker_id=self.policy.worker_id,
                concurrency_group=self.policy.concurrency_group,
                run_dir_ref=f"runs/{run_id}",
                lease_id=lease_id,
                workspace_lease_id=workspace_slot.slot_id,
                acquired_at_unix=time.time(),
                queue_wait_seconds_by_resource={
                    "episode": episode_slot.queue_wait_seconds,
                    "workspace_lease": workspace_slot.queue_wait_seconds,
                },
            )
            return ResourceLeaseHandle(
                manager=self,
                owner_id=owner_id,
                lease=lease,
                episode_slot=episode_slot,
                workspace_slot=workspace_slot,
            )
        except BaseException:
            if workspace_slot is not None:
                await self._workspace_limiter.release(workspace_slot)
            if acquired_run_lock:
                await self._release_run_directory(run_id)
            if episode_slot is not None:
                await self._episode_limiter.release(episode_slot)
            raise

    @asynccontextmanager
    async def route_call(
        self,
        *,
        handle: ResourceLeaseHandle,
        route: GatewayRoute | str,
    ) -> AsyncIterator[ResourceSlotLease]:
        limiter = self._route_limiter(str(route))
        slot = await limiter.acquire(owner_id=handle.owner_id)
        handle.record_route_slot(slot)
        try:
            yield slot
        finally:
            diagnostic = await limiter.release(slot)
            if diagnostic is not None:
                handle.diagnostics.append(diagnostic)

    async def release_episode(self, handle: ResourceLeaseHandle) -> EpisodeResourceLease:
        if handle.released:
            diagnostic = ResourceLeaseDiagnostics(
                code="episode_resource_double_release",
                message="episode resource lease was already released",
                resource_name="episode",
                slot_id=handle.lease.lease_id,
            )
            handle.diagnostics.append(diagnostic)
            return handle.lease.model_copy(
                update={"diagnostics": [*handle.lease.diagnostics, diagnostic]}
            )
        cleanup_status: CleanupStatus = CLEANUP_STATUS_COMPLETED
        release_diagnostics = list(handle.diagnostics)
        try:
            if handle.workspace_slot is not None:
                diagnostic = await self._workspace_limiter.release(handle.workspace_slot)
                if diagnostic is not None:
                    release_diagnostics.append(diagnostic)
            await self._release_run_directory(handle.lease.run_id)
            if handle.episode_slot is not None:
                diagnostic = await self._episode_limiter.release(handle.episode_slot)
                if diagnostic is not None:
                    release_diagnostics.append(diagnostic)
        except Exception as exc:
            cleanup_status = CLEANUP_STATUS_FAILED
            release_diagnostics.append(
                ResourceLeaseDiagnostics(
                    code="resource_lease_release_failed",
                    message=str(exc),
                    resource_name="episode",
                    slot_id=handle.lease.lease_id,
                )
            )
        handle.released = True
        handle.lease = handle.lease.model_copy(
            update={
                "released_at_unix": time.time(),
                "cleanup_status": cleanup_status,
                "diagnostics": [*handle.lease.diagnostics, *release_diagnostics],
            }
        )
        return handle.lease

    def summary_fields(self, handle: ResourceLeaseHandle) -> dict[str, object]:
        lease = handle.lease
        return {
            "worker_id": lease.worker_id,
            "concurrency_group": lease.concurrency_group,
            "lease_id": lease.lease_id,
            "inference_concurrency_slot": lease.gateway_route_slot_id,
            "queue_wait_seconds_by_resource": dict(lease.queue_wait_seconds_by_resource),
            "cleanup_status": lease.cleanup_status,
        }

    def _route_limiter(self, route: str) -> AsyncResourceLimiter:
        if route not in ALLOWED_ROUTES:
            raise ResourceLeaseError(
                f"unknown gateway route: {route}",
                status_reason="unknown_gateway_route",
                episode_status="invalid_task",
                resource_name="gateway_route",
            )
        limiter = self._route_limiters.get(route)
        if limiter is None:
            limiter = AsyncResourceLimiter(
                resource_name=f"gateway_route_{route}",
                max_concurrency=self.policy.max_gateway_route_concurrency_by_route.get(route, 1),
                queue_timeout_seconds=self.policy.route_queue_timeout_seconds,
                timeout_status_reason="gateway_route_queue_timeout",
            )
            self._route_limiters[route] = limiter
        return limiter

    async def _acquire_run_directory(self, run_id: str) -> None:
        validate_safe_identifier(run_id, field_name="run_id")
        async with self._run_lock:
            if run_id in self._active_run_ids:
                raise ResourceLeaseError(
                    f"run directory is already active for run_id={run_id}",
                    status_reason="run_directory_lock_conflict",
                    episode_status="infrastructure_error",
                    resource_name="run_directory",
                )
            self._active_run_ids.add(run_id)

    async def _release_run_directory(self, run_id: str) -> None:
        async with self._run_lock:
            self._active_run_ids.discard(run_id)


def normalize_cleanup_status(value: str | None) -> CleanupStatus | None:
    if value is None:
        return None
    mapping = {
        "ok": CLEANUP_STATUS_COMPLETED,
        "not_required": CLEANUP_STATUS_SKIPPED,
        "not_applicable": CLEANUP_STATUS_SKIPPED,
        CLEANUP_STATUS_NOT_STARTED: CLEANUP_STATUS_NOT_STARTED,
        CLEANUP_STATUS_COMPLETED: CLEANUP_STATUS_COMPLETED,
        CLEANUP_STATUS_FAILED: CLEANUP_STATUS_FAILED,
        CLEANUP_STATUS_SKIPPED: CLEANUP_STATUS_SKIPPED,
    }
    normalized = mapping.get(value)
    if normalized is None:
        raise ValueError(f"unknown cleanup_status: {value}")
    return normalized  # type: ignore[return-value]


def combine_cleanup_status(*statuses: str | None) -> CleanupStatus:
    normalized = [status for status in (normalize_cleanup_status(value) for value in statuses) if status is not None]
    if not normalized:
        return CLEANUP_STATUS_SKIPPED
    if CLEANUP_STATUS_FAILED in normalized:
        return CLEANUP_STATUS_FAILED
    if CLEANUP_STATUS_COMPLETED in normalized:
        return CLEANUP_STATUS_COMPLETED
    if CLEANUP_STATUS_NOT_STARTED in normalized:
        return CLEANUP_STATUS_NOT_STARTED
    return CLEANUP_STATUS_SKIPPED


def _owner_id(*, episode_id: str, run_id: str) -> str:
    return f"owner-{stable_hash({'episode_id': episode_id, 'run_id': run_id})[:16]}"
