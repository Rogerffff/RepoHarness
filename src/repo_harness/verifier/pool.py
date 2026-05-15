"""Bounded verifier worker pool for blocking reward computation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import SimpleQueue
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.verifier.schemas import VerifierResult


VerifierCallable = Callable[[], VerifierResult]


class VerifierPoolOptions(StrictBaseModel):
    schema_version: str = "repo_harness_verifier_pool_options_v0"
    pool_id: str = "verifier-pool-local-v1"
    max_workers: int = Field(default=1, ge=1)
    max_pending_jobs: int = Field(default=0, ge=0)
    queue_timeout_seconds: float | None = Field(default=None, gt=0)
    default_execution_timeout_seconds: float | None = Field(default=None, gt=0)
    record_worker_diagnostics: bool = True


@dataclass(frozen=True)
class VerifierJob:
    """Runtime-only final verifier job.

    The callable is deliberately not a pydantic field because it can close over
    local paths, workspace adapters, recorders, and other evaluator-only state.
    """

    job_id: str
    run_id: str
    episode_id: str
    task_id: str
    verifier_stage: Literal["baseline", "feedback", "final"]
    callable: VerifierCallable
    timeout_seconds: float | None = None


class VerifierJobResult(StrictBaseModel):
    schema_version: str = "repo_harness_verifier_job_result_v0"
    job_id: str
    run_id: str
    episode_id: str
    task_id: str
    verifier_stage: Literal["baseline", "feedback", "final"]
    pool_id: str
    worker_id: str | None = None
    queue_wait_seconds: float = Field(default=0.0, ge=0.0)
    execution_seconds: float = Field(default=0.0, ge=0.0)
    submitted_at_seconds: float = Field(ge=0.0)
    started_at_seconds: float | None = Field(default=None, ge=0.0)
    finished_at_seconds: float | None = Field(default=None, ge=0.0)
    timeout: bool = False
    error_type: str | None = None
    error_message: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    verifier_result: VerifierResult | None = None

    @model_validator(mode="after")
    def validate_terminal_fact(self) -> "VerifierJobResult":
        if self.verifier_result is None and not self.error_type:
            raise ValueError("verifier job result requires verifier_result or error_type")
        return self


class VerifierWorkerPoolClosedError(RuntimeError):
    """Raised when submitting to a closed verifier worker pool."""


class VerifierExecutionError(RuntimeError):
    """Raised for unexpected verifier execution failures."""


class VerifierWorkerPool:
    """A local bounded worker pool for blocking verifier jobs.

    The pool bounds both running worker count and admitted pending jobs. It does
    not rely on ThreadPoolExecutor's internal unbounded queue for admission.
    """

    def __init__(self, options: VerifierPoolOptions | None = None) -> None:
        self.options = options or VerifierPoolOptions()
        self._executor = ThreadPoolExecutor(
            max_workers=self.options.max_workers,
            thread_name_prefix=self.options.pool_id,
        )
        self._admission_slots = asyncio.BoundedSemaphore(
            self.options.max_workers + self.options.max_pending_jobs
        )
        self._worker_slots = asyncio.BoundedSemaphore(self.options.max_workers)
        self._worker_ids: SimpleQueue[str] = SimpleQueue()
        for index in range(self.options.max_workers):
            self._worker_ids.put(f"verifier-worker-{index}")
        self._closed = False
        self._lock = Lock()
        self._started_jobs: dict[str, tuple[str, float]] = {}

    async def run(self, job: VerifierJob) -> VerifierJobResult:
        self._raise_if_closed()
        submitted_at = perf_counter()
        admitted = await self._try_acquire_slot(job, submitted_at)
        if admitted is not None:
            return admitted
        self._raise_if_closed(release_slot=True)
        try:
            worker_slot = await self._try_acquire_worker_slot(job, submitted_at)
        except asyncio.CancelledError:
            self._admission_slots.release()
            raise
        if worker_slot is not None:
            return worker_slot
        self._raise_if_closed(release_slot=True, release_worker_slot=True)
        worker_id = self._worker_ids.get()
        started_at = perf_counter()
        with self._lock:
            self._started_jobs[job.job_id] = (worker_id, started_at)

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(
            self._executor,
            self._execute_job,
            job,
            submitted_at,
            worker_id,
            started_at,
        )
        future.add_done_callback(lambda _: self._release_running_job_slots())
        timeout_seconds = job.timeout_seconds or self.options.default_execution_timeout_seconds
        try:
            if timeout_seconds is None:
                return await asyncio.shield(future)
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout_seconds)
        except TimeoutError:
            return self._execution_timeout_result(job, submitted_at)

    def close(self, *, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=True)

    async def aclose(self, *, wait: bool = True) -> None:
        await asyncio.to_thread(self.close, wait=wait)

    def __enter__(self) -> "VerifierWorkerPool":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    async def __aenter__(self) -> "VerifierWorkerPool":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def _try_acquire_slot(
        self,
        job: VerifierJob,
        submitted_at: float,
    ) -> VerifierJobResult | None:
        try:
            if self.options.queue_timeout_seconds is None:
                await self._admission_slots.acquire()
            else:
                await asyncio.wait_for(
                    self._admission_slots.acquire(),
                    timeout=self.options.queue_timeout_seconds,
                )
        except TimeoutError:
            now = perf_counter()
            return VerifierJobResult(
                job_id=job.job_id,
                run_id=job.run_id,
                episode_id=job.episode_id,
                task_id=job.task_id,
                verifier_stage=job.verifier_stage,
                pool_id=self.options.pool_id,
                queue_wait_seconds=now - submitted_at,
                execution_seconds=0.0,
                submitted_at_seconds=submitted_at,
                finished_at_seconds=now,
                timeout=True,
                error_type="queue_timeout",
                error_message="verifier worker pool queue timeout before job admission",
                diagnostics=["job was not submitted to executor because no verifier slot was available"],
            )
        return None

    async def _try_acquire_worker_slot(
        self,
        job: VerifierJob,
        submitted_at: float,
    ) -> VerifierJobResult | None:
        try:
            if self.options.queue_timeout_seconds is None:
                await self._worker_slots.acquire()
            else:
                elapsed = perf_counter() - submitted_at
                remaining = self.options.queue_timeout_seconds - elapsed
                if remaining <= 0:
                    raise TimeoutError
                await asyncio.wait_for(self._worker_slots.acquire(), timeout=remaining)
        except TimeoutError:
            self._admission_slots.release()
            now = perf_counter()
            return VerifierJobResult(
                job_id=job.job_id,
                run_id=job.run_id,
                episode_id=job.episode_id,
                task_id=job.task_id,
                verifier_stage=job.verifier_stage,
                pool_id=self.options.pool_id,
                queue_wait_seconds=now - submitted_at,
                execution_seconds=0.0,
                submitted_at_seconds=submitted_at,
                finished_at_seconds=now,
                timeout=True,
                error_type="queue_timeout",
                error_message="verifier worker pool queue timeout before worker start",
                diagnostics=["job was not submitted to executor because no verifier worker was available"],
            )
        return None

    def _execute_job(
        self,
        job: VerifierJob,
        submitted_at: float,
        worker_id: str,
        started_at: float,
    ) -> VerifierJobResult:
        try:
            verifier_result = job.callable()
            finished_at = perf_counter()
            return VerifierJobResult(
                job_id=job.job_id,
                run_id=job.run_id,
                episode_id=job.episode_id,
                task_id=job.task_id,
                verifier_stage=job.verifier_stage,
                pool_id=self.options.pool_id,
                worker_id=worker_id,
                queue_wait_seconds=started_at - submitted_at,
                execution_seconds=finished_at - started_at,
                submitted_at_seconds=submitted_at,
                started_at_seconds=started_at,
                finished_at_seconds=finished_at,
                verifier_result=verifier_result,
            )
        except Exception as exc:  # pragma: no cover - concrete tests cover result shape.
            finished_at = perf_counter()
            return VerifierJobResult(
                job_id=job.job_id,
                run_id=job.run_id,
                episode_id=job.episode_id,
                task_id=job.task_id,
                verifier_stage=job.verifier_stage,
                pool_id=self.options.pool_id,
                worker_id=worker_id,
                queue_wait_seconds=started_at - submitted_at,
                execution_seconds=finished_at - started_at,
                submitted_at_seconds=submitted_at,
                started_at_seconds=started_at,
                finished_at_seconds=finished_at,
                error_type="pool_executor_error",
                error_message=str(exc),
                diagnostics=[exc.__class__.__name__],
            )
        finally:
            self._worker_ids.put(worker_id)
            with self._lock:
                self._started_jobs.pop(job.job_id, None)

    def _execution_timeout_result(self, job: VerifierJob, submitted_at: float) -> VerifierJobResult:
        now = perf_counter()
        with self._lock:
            started = self._started_jobs.get(job.job_id)
        worker_id = None
        started_at = None
        if started is not None:
            worker_id, started_at = started
        queue_wait_seconds = 0.0 if started_at is None else max(0.0, started_at - submitted_at)
        execution_seconds = 0.0 if started_at is None else max(0.0, now - started_at)
        return VerifierJobResult(
            job_id=job.job_id,
            run_id=job.run_id,
            episode_id=job.episode_id,
            task_id=job.task_id,
            verifier_stage=job.verifier_stage,
            pool_id=self.options.pool_id,
            worker_id=worker_id,
            queue_wait_seconds=queue_wait_seconds,
            execution_seconds=execution_seconds,
            submitted_at_seconds=submitted_at,
            started_at_seconds=started_at,
            finished_at_seconds=now,
            timeout=True,
            error_type="execution_timeout",
            error_message="verifier execution timeout elapsed; underlying sync callable may still be running",
            diagnostics=["execution timeout does not imply a forced thread stop"],
        )

    def _raise_if_closed(
        self,
        *,
        release_slot: bool = False,
        release_worker_slot: bool = False,
    ) -> None:
        with self._lock:
            closed = self._closed
        if closed:
            if release_worker_slot:
                self._worker_slots.release()
            if release_slot:
                self._admission_slots.release()
            raise VerifierWorkerPoolClosedError("verifier worker pool is closed")

    def _release_running_job_slots(self) -> None:
        self._worker_slots.release()
        self._admission_slots.release()
