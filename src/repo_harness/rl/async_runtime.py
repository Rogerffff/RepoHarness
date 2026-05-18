"""Runtime-only async episode facade for Stage 13.1."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Awaitable, Callable

from .async_contracts import (
    AsyncEpisodeHandleRef,
    AsyncEpisodeSnapshot,
    AsyncEpisodeStatus,
    ResumeCapability,
)
from .episode import RepoHarnessEpisodeRequest, RepoHarnessEpisodeResult


TERMINAL_ASYNC_EPISODE_STATUSES = frozenset({"cancelled", "timeout", "failed", "completed", "orphaned"})


class AsyncEpisodeStartError(RuntimeError):
    """Raised when an async episode cannot be started safely."""


@dataclass
class AsyncEpisodeState:
    request: RepoHarnessEpisodeRequest
    sample_attempt_id: str
    handle_ref: AsyncEpisodeHandleRef
    runtime_mode: str
    status: AsyncEpisodeStatus = "created"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: RepoHarnessEpisodeResult | None = None
    exception: BaseException | None = None
    diagnostics: list[str] = field(default_factory=list)
    cancel_requested: bool = False
    cleanup_status: str | None = None
    task: asyncio.Task[RepoHarnessEpisodeResult] | None = None
    started: bool = False
    cancel_result_factory: Callable[[], RepoHarnessEpisodeResult] | None = None
    _lock: RLock = field(default_factory=RLock)

    def set_task(self, task: asyncio.Task[RepoHarnessEpisodeResult]) -> None:
        with self._lock:
            self.task = task
            if self.status == "created":
                self.status = "queued"
            self.updated_at = datetime.now(timezone.utc)

    def set_status(self, status: AsyncEpisodeStatus, *, diagnostic: str | None = None) -> None:
        with self._lock:
            if self.result is not None and status not in TERMINAL_ASYNC_EPISODE_STATUSES:
                return
            self.status = status
            if diagnostic:
                self.diagnostics.append(diagnostic)
            self.updated_at = datetime.now(timezone.utc)

    def mark_cancel_requested(self, reason: str) -> None:
        with self._lock:
            self.cancel_requested = True
            if self.result is None and self.status not in TERMINAL_ASYNC_EPISODE_STATUSES:
                self.status = "cancelling"
            self.diagnostics.append(reason)
            self.updated_at = datetime.now(timezone.utc)

    def mark_started(self) -> None:
        with self._lock:
            self.started = True
            self.updated_at = datetime.now(timezone.utc)

    def mark_result(self, result: RepoHarnessEpisodeResult) -> None:
        with self._lock:
            self.result = result
            self.cleanup_status = (
                None if result.resource_summary is None else result.resource_summary.cleanup_status
            )
            if result.status == "cancelled":
                self.status = "cancelled"
            elif result.status == "timeout":
                self.status = "timeout"
            elif result.status == "infrastructure_error":
                self.status = "failed"
            else:
                self.status = "completed"
            self.updated_at = datetime.now(timezone.utc)

    def mark_exception(self, exc: BaseException) -> None:
        with self._lock:
            self.exception = exc
            self.status = "orphaned"
            self.diagnostics.append(f"{exc.__class__.__name__}: {exc}")
            self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        with self._lock:
            return self.result is not None or self.status in TERMINAL_ASYNC_EPISODE_STATUSES


class AsyncEpisodeHandle:
    """Runtime-only handle for a background RepoHarness episode."""

    def __init__(
        self,
        state: AsyncEpisodeState,
        *,
        unregister: Callable[["AsyncEpisodeHandle"], Awaitable[None]] | None = None,
    ) -> None:
        self._state = state
        self._unregister = unregister

    @property
    def handle_ref(self) -> AsyncEpisodeHandleRef:
        return self._state.handle_ref

    @property
    def sample_attempt_id(self) -> str:
        return self._state.sample_attempt_id

    def attach_task(self, task: asyncio.Task[RepoHarnessEpisodeResult]) -> None:
        self._state.set_task(task)

    def status(self) -> AsyncEpisodeStatus:
        with self._state._lock:
            return self._state.status

    def snapshot(self) -> AsyncEpisodeSnapshot:
        with self._state._lock:
            result = self._state.result
            status = self._state.status
            diagnostics = list(self._state.diagnostics)
            cleanup_status = self._state.cleanup_status
            cancel_requested = self._state.cancel_requested
            created_at = self._state.created_at
            updated_at = self._state.updated_at

        if result is not None:
            audit_refs = {"result": f"rh://async/{self.handle_ref.episode_id}/{self.sample_attempt_id}/result"}
            if result.training_view.extra_fields.get("repo_harness_audit_manifest_ref"):
                audit_refs["audit_manifest"] = str(
                    result.training_view.extra_fields["repo_harness_audit_manifest_ref"]
                )
            resource_lease_refs = {}
            if result.resource_summary is not None and result.resource_summary.lease_id:
                resource_lease_refs["episode_lease"] = f"rh://resource/lease/{result.resource_summary.lease_id}"
            workspace_released = (
                result.resource_summary is not None
                and result.resource_summary.cleanup_status in {"completed", "skipped", "not_applicable"}
            )
            return AsyncEpisodeSnapshot(
                episode_id=result.episode_id,
                run_id=result.run_id,
                task_id=result.task_id,
                sample_attempt_id=self.sample_attempt_id,
                async_status=status,
                episode_status=result.status,
                resource_lease_refs=resource_lease_refs,
                audit_refs=audit_refs,
                created_at=created_at,
                updated_at=updated_at,
                resume=ResumeCapability(),
                cancel_requested=cancel_requested,
                cleanup_status=cleanup_status,
                final_audit_write_completed=True,
                run_directory_writer_active=False,
                verifier_worker_may_still_access_workspace=False,
                workspace_lease_safely_released=workspace_released,
            )

        orphan_diagnostics = diagnostics if status == "orphaned" else []
        writer_active = status not in {"created", "queued", "orphaned"}
        real_episode_running = self._state.runtime_mode == "real_episode" and status not in {
            "created",
            "queued",
            "orphaned",
        }
        return AsyncEpisodeSnapshot(
            episode_id=self.handle_ref.episode_id,
            run_id=self.handle_ref.run_id,
            task_id=self._state.request.task_id,
            sample_attempt_id=self.sample_attempt_id,
            async_status=status,
            episode_status=None,
            resource_lease_refs={},
            audit_refs={"handle": self.handle_ref.handle_ref},
            created_at=created_at,
            updated_at=updated_at,
            resume=ResumeCapability(),
            cancel_requested=cancel_requested,
            cleanup_status=cleanup_status,
            orphan_diagnostics=orphan_diagnostics,
            final_audit_write_completed=False,
            run_directory_writer_active=writer_active,
            verifier_worker_may_still_access_workspace=real_episode_running,
            workspace_lease_safely_released=False,
        )

    async def wait_result(self, timeout: float | None = None) -> RepoHarnessEpisodeResult:
        task = self._state.task
        if task is None:
            raise RuntimeError("async episode task has not been attached")
        if timeout is None:
            return await asyncio.shield(task)
        return await asyncio.wait_for(asyncio.shield(task), timeout=timeout)

    async def cancel(self, reason: str = "cancel_requested") -> AsyncEpisodeSnapshot:
        self._state.mark_cancel_requested(reason)
        task = self._state.task
        started = self._state.started
        if task is not None and not task.done() and started:
            task.cancel()
            await asyncio.sleep(0)
        elif task is not None and not task.done():
            await asyncio.sleep(0)
        return self.snapshot()

    async def _run_and_record(
        self,
        runner: Callable[[], Awaitable[RepoHarnessEpisodeResult]],
    ) -> RepoHarnessEpisodeResult:
        self._state.mark_started()
        self._state.set_status("running")
        if self._state.cancel_requested and self._state.cancel_result_factory is not None:
            result = self._state.cancel_result_factory()
            self._state.mark_result(result)
            if self._unregister is not None:
                await self._unregister(self)
            return result
        try:
            result = await runner()
        except asyncio.CancelledError as exc:
            if self._state.cancel_requested and self._state.cancel_result_factory is not None:
                result = self._state.cancel_result_factory()
                self._state.mark_result(result)
                return result
            self._state.mark_exception(exc)
            raise
        except BaseException as exc:
            self._state.mark_exception(exc)
            raise
        else:
            self._state.mark_result(result)
            return result
        finally:
            if self._unregister is not None:
                await self._unregister(self)
