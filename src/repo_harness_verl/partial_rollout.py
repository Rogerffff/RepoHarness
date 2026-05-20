"""Stage 15.1 local partial-rollout resume adapter.

This module is intentionally local and conservative.  It does not import
``verl``, ``ray``, ``torch`` or ``tensordict``.  It models the first RepoHarness
partial-rollout path as:

``paused same-process async handle -> resume queue -> same-process resume ->
terminal RepoHarness episode result -> valid fully-async policy-loss payload``.

The partial checkpoint itself is never converted into a policy-loss sample.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.rl import LLMGateway, RepoHarnessEpisodeRequest, RepoHarnessEpisodeResult, RepoHarnessRuntime
from repo_harness.rl.async_runtime import AsyncEpisodeHandle
from repo_harness.rl.partial_checkpoint import (
    PartialEpisodeCheckpoint,
    compute_partial_checkpoint_visibility_digest,
    partial_checkpoint_to_queue_facts,
    validate_partial_checkpoint_not_trainable,
    validate_partial_checkpoint_roundtrip,
)
from repo_harness.schema_base import StrictBaseModel

from .fully_async_bridge import (
    RepoHarnessFullyAsyncQueueFacts,
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    serialize_rollout_sample_for_message_queue,
)
from .fully_async_runtime import InMemoryFullyAsyncMessageQueueClient, default_rollout_sample_factory


DEFAULT_STAGE15_VISIBILITY_DIGEST = "sha256:" + ("15" * 32)


class PartialRolloutProducerConfig(StrictBaseModel):
    """Runtime-only configuration for the local partial-rollout producer."""

    pause_wait_timeout_seconds: float = Field(default=5.0, gt=0)
    pause_cancel_wait_timeout_seconds: float = Field(default=2.0, gt=0)
    current_global_steps: int = Field(default=0, ge=0)
    current_param_version: int = Field(default=0, ge=0)
    visibility_scan_status: Literal["passed", "failed", "missing"] = "passed"
    visibility_scan_digest: str | None = DEFAULT_STAGE15_VISIBILITY_DIGEST
    serializer: Literal["cloudpickle", "pickle"] = "cloudpickle"

    @model_validator(mode="after")
    def validate_config(self) -> "PartialRolloutProducerConfig":
        if self.visibility_scan_status == "passed" and not self.visibility_scan_digest:
            raise ValueError("passed visibility scan requires visibility_scan_digest")
        return self


class ResumeSchedulerConfig(StrictBaseModel):
    """Runtime-only configuration for the same-process resume scheduler."""

    resume_wait_timeout_seconds: float = Field(default=10.0, gt=0)
    resume_cancel_wait_timeout_seconds: float = Field(default=2.0, gt=0)
    current_global_steps: int = Field(default=0, ge=0)
    current_param_version: int = Field(default=0, ge=0)
    staleness_threshold: int | None = Field(default=None, ge=0)
    visibility_scan_status: Literal["passed", "failed", "missing"] = "passed"
    visibility_scan_digest: str | None = DEFAULT_STAGE15_VISIBILITY_DIGEST
    serializer: Literal["cloudpickle", "pickle"] = "cloudpickle"

    @model_validator(mode="after")
    def validate_config(self) -> "ResumeSchedulerConfig":
        if self.visibility_scan_status == "passed" and not self.visibility_scan_digest:
            raise ValueError("passed visibility scan requires visibility_scan_digest")
        return self


class PartialResumeQueueItemFacts(StrictBaseModel):
    """Runtime-local identity facts for one partial resume queue entry."""

    schema_version: str = "repo_harness_verl_partial_resume_queue_item_v0"
    sample_id: str
    episode_id: str
    run_id: str
    task_id: str
    sample_attempt_id: str
    runtime_scope_id: str
    handle_ref: str
    checkpoint_id: str
    checkpoint_ref: str
    checkpoint_status: str
    checkpoint_content_digest: str
    checkpoint_visibility_digest: str
    checkpoint_generation_record_digest: str
    checkpoint_trajectory_digest: str
    lease_token_digest: str
    recorder_cursor_digest: str
    partial_rollout_supported: bool = True
    partial_rollout_status: str = "paused_same_process_stage15_1"
    valid_for_policy_loss: bool = False
    sample_classification: Literal["partial_resume_candidate", "diagnostic"] = "partial_resume_candidate"
    rejection_reason: str | None = "partial_checkpoint_not_policy_loss_sample"
    visibility_scan_status: Literal["passed", "failed", "missing"] = "passed"
    visibility_scan_digest: str | None = DEFAULT_STAGE15_VISIBILITY_DIGEST

    @model_validator(mode="after")
    def validate_item(self) -> "PartialResumeQueueItemFacts":
        if self.valid_for_policy_loss:
            raise ValueError("partial resume queue item cannot be valid for policy loss")
        if self.visibility_scan_status == "passed" and not self.visibility_scan_digest:
            raise ValueError("passed visibility scan requires visibility_scan_digest")
        for field_name in [
            "checkpoint_content_digest",
            "checkpoint_visibility_digest",
            "checkpoint_generation_record_digest",
            "checkpoint_trajectory_digest",
            "lease_token_digest",
            "recorder_cursor_digest",
        ]:
            _require_sha256(getattr(self, field_name), field_name=field_name)
        return self


class PartialRolloutProducerReport(StrictBaseModel):
    """Local producer report for Stage 15.1."""

    schema_version: str = "repo_harness_verl_partial_rollout_producer_report_v0"
    started_episode_count: int = Field(default=0, ge=0)
    paused_checkpoint_count: int = Field(default=0, ge=0)
    enqueued_resume_candidate_count: int = Field(default=0, ge=0)
    pause_timeout_count: int = Field(default=0, ge=0)
    cancelled_episode_count: int = Field(default=0, ge=0)
    active_handle_retained_count: int = Field(default=0, ge=0)
    diagnostic_count: int = Field(default=0, ge=0)
    policy_loss_enqueued_count: int = Field(default=0, ge=0)
    queued_checkpoint_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_report(self) -> "PartialRolloutProducerReport":
        if self.policy_loss_enqueued_count != 0:
            raise ValueError("partial rollout producer cannot enqueue policy-loss samples")
        return self


class ResumeSchedulerReport(StrictBaseModel):
    """Resume scheduler report for Stage 15.1."""

    schema_version: str = "repo_harness_verl_resume_scheduler_report_v0"
    resume_attempt_count: int = Field(default=0, ge=0)
    resumed_terminal_episode_count: int = Field(default=0, ge=0)
    resumed_valid_sample_count: int = Field(default=0, ge=0)
    policy_loss_enqueued_count: int = Field(default=0, ge=0)
    resume_timeout_count: int = Field(default=0, ge=0)
    resume_cancelled_count: int = Field(default=0, ge=0)
    active_handle_retained_count: int = Field(default=0, ge=0)
    rejected_resume_candidate_count: int = Field(default=0, ge=0)
    duplicate_resume_rejected_count: int = Field(default=0, ge=0)
    missing_live_handle_rejected_count: int = Field(default=0, ge=0)
    missing_resume_state_rejected_count: int = Field(default=0, ge=0)
    stale_rejected_count: int = Field(default=0, ge=0)
    selected_sample_ids: list[str] = Field(default_factory=list)
    source_partial_checkpoint_ids: list[str] = Field(default_factory=list)
    resume_attempt_ids: list[str] = Field(default_factory=list)
    diagnostics: dict[str, str] = Field(default_factory=dict)


@dataclass
class PartialResumeQueueEntry:
    """Runtime-private queue entry.

    ``handle`` is deliberately runtime-private.  It must never be serialized to
    TransferQueue, DataProto or any policy-loss batch.
    """

    facts: PartialResumeQueueItemFacts
    checkpoint: PartialEpisodeCheckpoint
    handle: AsyncEpisodeHandle


class InMemoryPartialResumeQueue:
    """Small in-memory resume queue bound to one runtime ownership scope."""

    def __init__(self) -> None:
        self._queue: deque[PartialResumeQueueEntry] = deque()
        self._condition = asyncio.Condition()

    async def put(self, entry: PartialResumeQueueEntry) -> None:
        async with self._condition:
            self._queue.append(entry)
            self._condition.notify_all()

    async def get(self, timeout: float | None = None) -> PartialResumeQueueEntry | None:
        async with self._condition:
            if timeout is None:
                while not self._queue:
                    await self._condition.wait()
            elif not self._queue:
                try:
                    await asyncio.wait_for(self._condition.wait_for(lambda: bool(self._queue)), timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            if not self._queue:
                return None
            return self._queue.popleft()

    async def qsize(self) -> int:
        async with self._condition:
            return len(self._queue)

    async def snapshot_facts(self) -> list[PartialResumeQueueItemFacts]:
        async with self._condition:
            return [entry.facts for entry in self._queue]


class InMemoryPartialDiagnosticChannel:
    """Side channel for rejected partial, resume and diagnostic samples."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def record(self, *, reason: str, facts: Mapping[str, Any] | None = None) -> None:
        self._records.append({"reason": reason, "facts": dict(facts or {})})

    @property
    def records(self) -> list[dict[str, Any]]:
        return list(self._records)


class RepoHarnessPartialRolloutProducer:
    """Produce local partial checkpoints from same-process async episodes."""

    def __init__(
        self,
        *,
        runtime: RepoHarnessRuntime,
        resume_queue: InMemoryPartialResumeQueue,
        diagnostic_channel: InMemoryPartialDiagnosticChannel | None = None,
        config: PartialRolloutProducerConfig | Mapping[str, Any] | None = None,
    ) -> None:
        self.runtime = runtime
        self.resume_queue = resume_queue
        self.diagnostic_channel = diagnostic_channel or InMemoryPartialDiagnosticChannel()
        self.config = (
            config
            if isinstance(config, PartialRolloutProducerConfig)
            else PartialRolloutProducerConfig.model_validate(config or {})
        )
        self.runtime_scope_id = runtime_scope_id(runtime)
        self.retained_active_handles: dict[str, AsyncEpisodeHandle] = {}

    async def produce_one(
        self,
        request: RepoHarnessEpisodeRequest,
        *,
        llm_gateway: LLMGateway,
    ) -> PartialRolloutProducerReport:
        diagnostics: list[str] = []
        handle: AsyncEpisodeHandle | None = None
        try:
            handle = await self.runtime.start_episode(request, llm_gateway=llm_gateway)
            pause_outcome = await handle.request_pause_at_next_turn_boundary(
                reason="stage15_1_partial_rollout_requested",
                timeout=self.config.pause_wait_timeout_seconds,
            )
            if pause_outcome.status == "paused" and pause_outcome.checkpoint is not None:
                checkpoint = validate_partial_checkpoint_roundtrip(pause_outcome.checkpoint)
                validate_partial_checkpoint_not_trainable(checkpoint)
                queue_facts = build_partial_resume_queue_item_facts(
                    runtime_scope_id=self.runtime_scope_id,
                    handle=handle,
                    checkpoint=checkpoint,
                    visibility_scan_status=self.config.visibility_scan_status,
                    visibility_scan_digest=self.config.visibility_scan_digest,
                )
                await self.resume_queue.put(PartialResumeQueueEntry(facts=queue_facts, checkpoint=checkpoint, handle=handle))
                return PartialRolloutProducerReport(
                    started_episode_count=1,
                    paused_checkpoint_count=1,
                    enqueued_resume_candidate_count=1,
                    queued_checkpoint_ids=[checkpoint.checkpoint_id],
                    diagnostics=diagnostics,
                )

            diagnostics.append(f"{request.run_id}:pause_not_enqueued:{pause_outcome.status}")
            self.diagnostic_channel.record(
                reason=f"pause_not_enqueued:{pause_outcome.status}",
                facts={"run_id": request.run_id, "episode_id": request.episode_id},
            )
            if pause_outcome.status == "pause_timeout" and handle is not None:
                cancelled = await _cancel_handle_with_bounded_wait(
                    handle,
                    reason="stage15_1_pause_timeout",
                    wait_timeout_seconds=self.config.pause_cancel_wait_timeout_seconds,
                    diagnostics=diagnostics,
                )
                if not cancelled:
                    self.retained_active_handles[request.run_id] = handle
                    self.diagnostic_channel.record(
                        reason="pause_timeout_cleanup_running",
                        facts={
                            "run_id": request.run_id,
                            "handle_ref": handle.handle_ref.handle_ref,
                            "async_status": handle.snapshot().async_status,
                        },
                    )
                return PartialRolloutProducerReport(
                    started_episode_count=1,
                    pause_timeout_count=1,
                    cancelled_episode_count=1 if cancelled else 0,
                    active_handle_retained_count=0 if cancelled else 1,
                    diagnostic_count=1,
                    diagnostics=diagnostics,
                )
            return PartialRolloutProducerReport(
                started_episode_count=1,
                diagnostic_count=1,
                diagnostics=diagnostics,
            )
        except Exception as exc:
            diagnostics.append(f"{request.run_id}:partial_producer_error:{exc.__class__.__name__}: {exc}")
            self.diagnostic_channel.record(
                reason="partial_producer_error",
                facts={"run_id": request.run_id, "error": f"{exc.__class__.__name__}: {exc}"},
            )
            cancelled = False
            if handle is not None:
                cancelled = await _cancel_handle_with_bounded_wait(
                    handle,
                    reason="stage15_1_partial_producer_error",
                    wait_timeout_seconds=self.config.pause_cancel_wait_timeout_seconds,
                    diagnostics=diagnostics,
                )
                if not cancelled:
                    self.retained_active_handles[request.run_id] = handle
                    self.diagnostic_channel.record(
                        reason="partial_producer_error_cleanup_running",
                        facts={
                            "run_id": request.run_id,
                            "handle_ref": handle.handle_ref.handle_ref,
                            "async_status": handle.snapshot().async_status,
                        },
                    )
            return PartialRolloutProducerReport(
                started_episode_count=1 if handle is not None else 0,
                cancelled_episode_count=1 if handle is not None and cancelled else 0,
                active_handle_retained_count=1 if handle is not None and not cancelled else 0,
                diagnostic_count=1,
                diagnostics=diagnostics,
            )


class RepoHarnessResumeScheduler:
    """Resume same-process partial checkpoints and enqueue terminal valid samples."""

    def __init__(
        self,
        *,
        runtime: RepoHarnessRuntime,
        resume_queue: InMemoryPartialResumeQueue,
        policy_loss_queue: InMemoryFullyAsyncMessageQueueClient,
        diagnostic_channel: InMemoryPartialDiagnosticChannel | None = None,
        config: ResumeSchedulerConfig | Mapping[str, Any] | None = None,
        rollout_sample_factory: Callable[[RepoHarnessEpisodeResult, RepoHarnessFullyAsyncQueueFacts], Any] | None = None,
    ) -> None:
        self.runtime = runtime
        self.runtime_scope_id = runtime_scope_id(runtime)
        self.resume_queue = resume_queue
        self.policy_loss_queue = policy_loss_queue
        self.diagnostic_channel = diagnostic_channel or InMemoryPartialDiagnosticChannel()
        self.config = (
            config
            if isinstance(config, ResumeSchedulerConfig)
            else ResumeSchedulerConfig.model_validate(config or {})
        )
        self.rollout_sample_factory = rollout_sample_factory
        self._consumed_checkpoint_ids: set[str] = set()
        self.retained_active_handles: dict[str, AsyncEpisodeHandle] = {}

    async def resume_available(
        self,
        *,
        max_items: int | None = None,
        queue_get_timeout_seconds: float | None = 0.0,
    ) -> ResumeSchedulerReport:
        report = ResumeSchedulerReport()
        processed = 0
        while max_items is None or processed < max_items:
            entry = await self.resume_queue.get(timeout=queue_get_timeout_seconds)
            if entry is None:
                break
            processed += 1
            report = await self._resume_entry(entry, report)
        return report

    async def _resume_entry(
        self,
        entry: PartialResumeQueueEntry,
        report: ResumeSchedulerReport,
    ) -> ResumeSchedulerReport:
        data = report.model_dump(mode="python")
        diagnostics: dict[str, str] = dict(data["diagnostics"])
        data["resume_attempt_count"] += 1
        checkpoint_id = entry.facts.checkpoint_id
        resume_attempt_id = f"{checkpoint_id}:resume-{data['resume_attempt_count']}"
        data["resume_attempt_ids"].append(resume_attempt_id)
        data["source_partial_checkpoint_ids"].append(checkpoint_id)
        owned_by_runtime = False

        async def reject(reason: str, *, cancel_owned_handle: bool = False) -> ResumeSchedulerReport:
            diagnostics[checkpoint_id] = reason
            data["diagnostics"] = diagnostics
            data["rejected_resume_candidate_count"] += 1
            if "duplicate" in reason:
                data["duplicate_resume_rejected_count"] += 1
            if "missing_live_handle" in reason or "runtime_scope_mismatch" in reason:
                data["missing_live_handle_rejected_count"] += 1
            if "resume_state" in reason or "unsupported_cross_process" in reason:
                data["missing_resume_state_rejected_count"] += 1
            if "stale" in reason:
                data["stale_rejected_count"] += 1
            if cancel_owned_handle and owned_by_runtime:
                snapshot = entry.handle.snapshot()
                if snapshot.async_status not in {"completed", "cancelled", "timeout", "failed", "orphaned"}:
                    cancel_diagnostics: list[str] = []
                    cancelled = await _cancel_handle_with_bounded_wait(
                        entry.handle,
                        reason=f"stage15_1_rejected_resume_candidate:{reason}",
                        wait_timeout_seconds=self.config.resume_cancel_wait_timeout_seconds,
                        diagnostics=cancel_diagnostics,
                    )
                    for index, diagnostic in enumerate(cancel_diagnostics):
                        diagnostics[f"{checkpoint_id}:cancel:{index}"] = diagnostic
                    data["diagnostics"] = diagnostics
                    if not cancelled:
                        data["active_handle_retained_count"] += 1
                        self.retained_active_handles[entry.facts.run_id] = entry.handle
                        self.diagnostic_channel.record(
                            reason="rejected_resume_candidate_cleanup_running",
                            facts={
                                "run_id": entry.facts.run_id,
                                "handle_ref": entry.facts.handle_ref,
                                "async_status": entry.handle.snapshot().async_status,
                            },
                        )
            self.diagnostic_channel.record(reason=reason, facts=entry.facts.model_dump(mode="json"))
            return ResumeSchedulerReport.model_validate(data)

        try:
            checkpoint = validate_partial_checkpoint_roundtrip(entry.checkpoint)
            validate_partial_checkpoint_not_trainable(checkpoint)
            owned_by_runtime = await self.runtime.owns_async_episode_handle(entry.handle)
            if not owned_by_runtime:
                return await reject("runtime_scope_mismatch_or_missing_live_handle")
            expected_facts = build_partial_resume_queue_item_facts(
                runtime_scope_id=self.runtime_scope_id,
                handle=entry.handle,
                checkpoint=checkpoint,
                visibility_scan_status=entry.facts.visibility_scan_status,
                visibility_scan_digest=entry.facts.visibility_scan_digest,
            )
            if expected_facts.model_dump(mode="json") != entry.facts.model_dump(mode="json"):
                return await reject("partial_resume_queue_facts_mismatch", cancel_owned_handle=True)
            if entry.facts.runtime_scope_id != self.runtime_scope_id:
                return await reject("runtime_scope_mismatch", cancel_owned_handle=True)
            if checkpoint_id in self._consumed_checkpoint_ids:
                return await reject("duplicate_partial_checkpoint_resume_attempt", cancel_owned_handle=True)
            snapshot = entry.handle.snapshot()
            if snapshot.async_status != "paused" or snapshot.run_id != entry.facts.run_id:
                return await reject("missing_live_handle_or_not_paused", cancel_owned_handle=True)
            if snapshot.resume.resume_supported is not True:
                return await reject("missing_live_handle_resume_capability", cancel_owned_handle=True)
            resume_outcome = await entry.handle.resume(checkpoint)
            if resume_outcome.status != "resumed":
                return await reject(resume_outcome.status, cancel_owned_handle=True)
            self._consumed_checkpoint_ids.add(checkpoint_id)
            try:
                result = await entry.handle.wait_result(timeout=self.config.resume_wait_timeout_seconds)
            except asyncio.TimeoutError:
                data["resume_timeout_count"] += 1
                cancelled = await _cancel_handle_with_bounded_wait(
                    entry.handle,
                    reason="stage15_1_resume_timeout",
                    wait_timeout_seconds=self.config.resume_cancel_wait_timeout_seconds,
                    diagnostics=list(diagnostics.values()),
                )
                if not cancelled:
                    data["active_handle_retained_count"] += 1
                    self.retained_active_handles[entry.facts.run_id] = entry.handle
                    self.diagnostic_channel.record(
                        reason="resume_timeout_cleanup_running",
                        facts={
                            "run_id": entry.facts.run_id,
                            "handle_ref": entry.facts.handle_ref,
                            "async_status": entry.handle.snapshot().async_status,
                        },
                    )
                return await reject("resume_timeout")
            except asyncio.CancelledError:
                data["resume_cancelled_count"] += 1
                cancelled = await _cancel_handle_with_bounded_wait(
                    entry.handle,
                    reason="stage15_1_resume_scheduler_cancelled",
                    wait_timeout_seconds=self.config.resume_cancel_wait_timeout_seconds,
                    diagnostics=list(diagnostics.values()),
                )
                if not cancelled:
                    data["active_handle_retained_count"] += 1
                    self.retained_active_handles[entry.facts.run_id] = entry.handle
                    self.diagnostic_channel.record(
                        reason="resume_cancelled_cleanup_running",
                        facts={
                            "run_id": entry.facts.run_id,
                            "handle_ref": entry.facts.handle_ref,
                            "async_status": entry.handle.snapshot().async_status,
                        },
                    )
                return await reject("resume_cancelled")

            data["resumed_terminal_episode_count"] += 1
            facts = build_queue_facts_from_episode_result(
                result,
                visibility_scan_status=self.config.visibility_scan_status,
                visibility_scan_digest=self.config.visibility_scan_digest,
                current_global_steps=self.config.current_global_steps,
                staleness_threshold=self.config.staleness_threshold,
                partial_rollout_supported=True,
                partial_rollout_status="complete",
            )
            if not facts.valid_for_policy_loss:
                return await reject(facts.rejection_reason or facts.invalid_reason or facts.sample_classification)
            rollout_sample = self._build_rollout_sample(result, facts)
            payload = serialize_rollout_sample_for_message_queue(
                rollout_sample,
                visibility_scan_status=self.config.visibility_scan_status,
                visibility_scan_digest=self.config.visibility_scan_digest,
                serializer=self.config.serializer,
            )
            success = await self.policy_loss_queue.put_sample(
                payload,
                visibility_scan_status=self.config.visibility_scan_status,
                visibility_scan_digest=self.config.visibility_scan_digest,
            )
            if not success:
                return await reject("policy_loss_queue_put_failed")
            data["resumed_valid_sample_count"] += 1
            data["policy_loss_enqueued_count"] += 1
            data["selected_sample_ids"].append(facts.sample_id)
            data["diagnostics"] = diagnostics
            return ResumeSchedulerReport.model_validate(data)
        except Exception as exc:
            return await reject(f"{exc.__class__.__name__}: {exc}", cancel_owned_handle=owned_by_runtime)

    def _build_rollout_sample(
        self,
        result: RepoHarnessEpisodeResult,
        facts: RepoHarnessFullyAsyncQueueFacts,
    ) -> Any:
        sample = (
            self.rollout_sample_factory(result, facts)
            if self.rollout_sample_factory is not None
            else default_rollout_sample_factory(result, facts)
        )
        return attach_queue_facts_to_rollout_sample(sample, facts)


def build_partial_resume_queue_item_facts(
    *,
    runtime_scope_id: str,
    handle: AsyncEpisodeHandle,
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
    visibility_scan_status: Literal["passed", "failed", "missing"] = "passed",
    visibility_scan_digest: str | None = DEFAULT_STAGE15_VISIBILITY_DIGEST,
) -> PartialResumeQueueItemFacts:
    """Build batch-safe queue facts from a paused checkpoint and live handle."""

    checkpoint = validate_partial_checkpoint_roundtrip(checkpoint)
    validate_partial_checkpoint_not_trainable(checkpoint)
    partial_checkpoint_to_queue_facts(checkpoint)
    snapshot = handle.snapshot()
    if snapshot.run_id != checkpoint.run_id:
        raise ValueError("checkpoint_handle_run_id_mismatch")
    checkpoint_ref = f"rh://partial-checkpoints/{checkpoint.checkpoint_id}"
    return PartialResumeQueueItemFacts(
        sample_id=f"partial-resume:{checkpoint.checkpoint_id}",
        episode_id=checkpoint.episode_id,
        run_id=checkpoint.run_id,
        task_id=checkpoint.task_id,
        sample_attempt_id=checkpoint.sample_attempt_id,
        runtime_scope_id=runtime_scope_id,
        handle_ref=handle.handle_ref.handle_ref,
        checkpoint_id=checkpoint.checkpoint_id,
        checkpoint_ref=checkpoint_ref,
        checkpoint_status=checkpoint.checkpoint_status,
        checkpoint_content_digest=checkpoint.content_digest,
        checkpoint_visibility_digest=compute_partial_checkpoint_visibility_digest(checkpoint),
        checkpoint_generation_record_digest=checkpoint.token_provenance.generation_record_digest,
        checkpoint_trajectory_digest=checkpoint.token_provenance.trajectory_digest,
        lease_token_digest=_sha256_string(checkpoint.durable_writer_lease.lease_token),
        recorder_cursor_digest=checkpoint.recorder_cursor.recorder_cursor_digest,
        visibility_scan_status=visibility_scan_status,
        visibility_scan_digest=visibility_scan_digest,
    )


def runtime_scope_id(runtime: RepoHarnessRuntime) -> str:
    """Return a runtime-local ownership scope id.

    The value is runtime-private and intended only for local process checks.
    It is deliberately not a durable cross-process identifier.
    """

    return "runtime-scope-" + hashlib.sha256(str(id(runtime)).encode("utf-8")).hexdigest()[:16]


async def _cancel_handle_with_bounded_wait(
    handle: AsyncEpisodeHandle,
    *,
    reason: str,
    wait_timeout_seconds: float,
    diagnostics: list[str],
) -> bool:
    snapshot = handle.snapshot()
    try:
        await handle.cancel(reason)
    except Exception as exc:  # pragma: no cover - defensive diagnostic path.
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_failed:{exc.__class__.__name__}: {exc}")
        return False
    try:
        await handle.wait_result(timeout=wait_timeout_seconds)
        return True
    except asyncio.TimeoutError:
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_wait_timeout")
        return False
    except asyncio.CancelledError:
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_wait_cancelled")
        return False
    except Exception as exc:
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_wait_error:{exc.__class__.__name__}: {exc}")
        return False


def _sha256_string(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_sha256(value: str, *, field_name: str) -> None:
    if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
        raise ValueError(f"{field_name} must be a sha256 digest")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


__all__ = [
    "DEFAULT_STAGE15_VISIBILITY_DIGEST",
    "InMemoryPartialDiagnosticChannel",
    "InMemoryPartialResumeQueue",
    "PartialResumeQueueEntry",
    "PartialResumeQueueItemFacts",
    "PartialRolloutProducerConfig",
    "PartialRolloutProducerReport",
    "RepoHarnessPartialRolloutProducer",
    "RepoHarnessResumeScheduler",
    "ResumeSchedulerConfig",
    "ResumeSchedulerReport",
    "build_partial_resume_queue_item_facts",
    "runtime_scope_id",
]
