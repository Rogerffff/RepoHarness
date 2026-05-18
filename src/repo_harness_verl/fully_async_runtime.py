"""Stage 13.3-A local fully async runtime adapter helpers.

This module intentionally avoids importing ``verl``, ``ray``, ``torch`` or
``tensordict``.  It provides a local producer / queue / trainer-side filtering
path that mirrors the safety boundaries of reference/verl fully async without
claiming that real trainer policy loss or parameter synchronization has run.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections import deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.rl import (
    LLMGateway,
    RepoHarnessEpisodeRequest,
    RepoHarnessEpisodeResult,
    RepoHarnessRuntime,
)
from repo_harness.schema_base import StrictBaseModel

from .fully_async_bridge import (
    RepoHarnessFullyAsyncQueueFacts,
    RepoHarnessFullyAsyncSelectionReport,
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    deserialize_message_queue_payload,
    queue_facts_from_rollout_sample,
    serialize_rollout_sample_for_message_queue,
    validate_rollout_sample_for_trainer_batch,
)

QueueOverflowPolicy = Literal["reject", "drop_oldest"]
DEFAULT_QUEUE_DEQUEUE_TIMEOUT_SECONDS = 1.0


class RepoHarnessFullyAsyncProducerConfig(StrictBaseModel):
    """Runtime-only config for the local fully async producer loop."""

    required_samples: int = Field(default=1, gt=0)
    max_queue_backlog: int = Field(default=16, gt=0)
    producer_concurrency: int = Field(default=1, gt=0)
    episode_wait_timeout_seconds: float | None = Field(default=None, gt=0)
    queue_put_timeout_seconds: float | None = Field(default=None, gt=0)
    current_global_steps: int = Field(default=0, ge=0)
    staleness_threshold: int | None = Field(default=None, ge=0)
    partial_rollout_supported: bool = False
    partial_rollout_status: str = "not_requested"
    visibility_scan_status: Literal["passed", "failed", "missing"] = "passed"
    visibility_scan_digest: str | None = "sha256:stage13-3a-local-visibility"
    serializer: Literal["cloudpickle", "pickle"] = "cloudpickle"
    queue_diagnostic_payloads: bool = False

    @model_validator(mode="after")
    def validate_config(self) -> "RepoHarnessFullyAsyncProducerConfig":
        if self.max_queue_backlog < self.required_samples:
            raise ValueError("max_queue_backlog must be >= required_samples")
        if self.visibility_scan_status == "passed" and not self.visibility_scan_digest:
            raise ValueError("passed visibility scan requires visibility_scan_digest")
        return self


class RepoHarnessFullyAsyncProducerResult(StrictBaseModel):
    """Local producer loop execution report."""

    schema_version: str = "repo_harness_verl_fully_async_producer_result_v0"
    started_episode_count: int = Field(default=0, ge=0)
    completed_episode_count: int = Field(default=0, ge=0)
    cancelled_episode_count: int = Field(default=0, ge=0)
    timeout_episode_count: int = Field(default=0, ge=0)
    queue_put_success_count: int = Field(default=0, ge=0)
    queue_put_failure_count: int = Field(default=0, ge=0)
    produced_sample_count: int = Field(default=0, ge=0)
    valid_candidate_count: int = Field(default=0, ge=0)
    rejected_candidate_count: int = Field(default=0, ge=0)
    diagnostic_candidate_count: int = Field(default=0, ge=0)
    queue_size_after_produce: int = Field(default=0, ge=0)
    producer_diagnostics: list[str] = Field(default_factory=list)
    produced_sample_ids: list[str] = Field(default_factory=list)
    rejected_sample_ids: list[str] = Field(default_factory=list)
    diagnostic_sample_ids: list[str] = Field(default_factory=list)


class FakeFullyAsyncTrainerStepReport(StrictBaseModel):
    """Local fake trainer-side selection report.

    ``real_policy_loss_executed`` is deliberately always false in Stage 13.3-A.
    Real policy loss and real parameter synchronization belong to Stage 13.3-B.
    """

    schema_version: str = "repo_harness_verl_fake_fully_async_trainer_step_report_v0"
    required_samples: int = Field(gt=0)
    selected_valid_sample_count: int = Field(ge=0)
    selected_sample_ids: list[str] = Field(default_factory=list)
    current_global_steps: int = Field(default=0, ge=0)
    next_global_steps: int = Field(default=0, ge=0)
    current_param_version: int = Field(default=0, ge=0)
    next_param_version: int = Field(default=0, ge=0)
    stale_sample_count: int = Field(default=0, ge=0)
    filtered_stale_sample_count: int = Field(default=0, ge=0)
    partial_rejected_count: int = Field(default=0, ge=0)
    visibility_rejected_count: int = Field(default=0, ge=0)
    pending_reward_rejected_count: int = Field(default=0, ge=0)
    rejected_sample_count: int = Field(default=0, ge=0)
    diagnostic_sample_count: int = Field(default=0, ge=0)
    real_policy_loss_executed: bool = False
    fake_selection_step_executed: bool = True
    policy_loss_execution_mode: str = "fake_local_selection_only"
    insufficient_valid_samples: bool = False
    rejection_reasons: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_report(self) -> "FakeFullyAsyncTrainerStepReport":
        if self.real_policy_loss_executed:
            raise ValueError("Stage 13.3-A cannot claim real policy loss execution")
        if self.selected_valid_sample_count != len(self.selected_sample_ids):
            raise ValueError("selected_valid_sample_count must match selected_sample_ids length")
        if self.next_global_steps < self.current_global_steps:
            raise ValueError("next_global_steps cannot go backwards")
        if self.next_param_version < self.current_param_version:
            raise ValueError("next_param_version cannot go backwards")
        return self


class FakeParameterClock(StrictBaseModel):
    """Small local clock used to make version and staleness facts testable."""

    current_global_steps: int = Field(default=0, ge=0)
    current_param_version: int = Field(default=0, ge=0)
    trigger_parameter_sync_step: int = Field(default=2, gt=0)

    def next_after_fake_step(self) -> tuple[int, int]:
        next_global_steps = self.current_global_steps + 1
        next_param_version = self.current_param_version
        if next_global_steps % self.trigger_parameter_sync_step == 0:
            next_param_version += 1
        return next_global_steps, next_param_version


@dataclass(frozen=True)
class QueuePayloadLedger:
    """External visibility ledger for one serialized queue payload."""

    visibility_scan_status: str
    visibility_scan_digest: str


@dataclass(frozen=True)
class _QueueEntry:
    payload: bytes | None
    ledger: QueuePayloadLedger | None


class InMemoryFullyAsyncMessageQueueClient:
    """Local fake of reference/verl ``MessageQueueClient``.

    The class returns ``(sample, queue_len)`` from ``get_sample()``, matching the
    current reference trainer.  A sidecar visibility ledger is kept outside the
    serialized payload so deserialization cannot self-attest visibility facts.
    """

    def __init__(
        self,
        *,
        max_queue_size: int = 1000,
        overflow_policy: QueueOverflowPolicy = "reject",
    ) -> None:
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        self.max_queue_size = max_queue_size
        self.overflow_policy = overflow_policy
        self._queue: deque[_QueueEntry] = deque()
        self._consumed_ledgers_by_payload_digest: dict[str, deque[QueuePayloadLedger | None]] = {}
        self._running = True
        self._condition = asyncio.Condition()
        self.total_produced = 0
        self.total_consumed = 0
        self.dropped_samples = 0
        self.rejected_samples = 0

    async def put_sample(
        self,
        sample: bytes | None,
        *,
        visibility_scan_status: str | None = None,
        visibility_scan_digest: str | None = None,
    ) -> bool:
        async with self._condition:
            if sample is None:
                if len(self._queue) >= self.max_queue_size:
                    self._queue.popleft()
                    self.dropped_samples += 1
                self._queue.append(_QueueEntry(payload=None, ledger=None))
                self.total_produced += 1
                self._condition.notify_all()
                return True

            if len(self._queue) >= self.max_queue_size:
                if self.overflow_policy == "drop_oldest":
                    self._queue.popleft()
                    self.dropped_samples += 1
                else:
                    self.rejected_samples += 1
                    return False

            ledger = None
            if visibility_scan_status is not None and visibility_scan_digest is not None:
                ledger = QueuePayloadLedger(
                    visibility_scan_status=visibility_scan_status,
                    visibility_scan_digest=visibility_scan_digest,
                )
            self._queue.append(_QueueEntry(payload=sample, ledger=ledger))
            self.total_produced += 1
            self._condition.notify_all()
            return True

    async def get_sample(self) -> tuple[bytes | None, int]:
        async with self._condition:
            while not self._queue and self._running:
                await self._condition.wait()
            if not self._queue and not self._running:
                return None, 0
            entry = self._queue.popleft()
            sample = entry.payload
            if isinstance(sample, bytes):
                digest = _payload_digest(sample)
                self._consumed_ledgers_by_payload_digest.setdefault(digest, deque()).append(entry.ledger)
            self.total_consumed += 1
            return sample, len(self._queue)

    async def get_queue_size(self) -> int:
        async with self._condition:
            return len(self._queue)

    async def get_statistics(self) -> dict[str, object]:
        async with self._condition:
            return {
                "queue_size": len(self._queue),
                "total_produced": self.total_produced,
                "total_consumed": self.total_consumed,
                "dropped_samples": self.dropped_samples,
                "rejected_samples": self.rejected_samples,
                "max_queue_size": self.max_queue_size,
            }

    async def shutdown(self) -> None:
        async with self._condition:
            self._running = False
            self._condition.notify_all()

    def visibility_ledger_for_payload(self, payload: bytes) -> QueuePayloadLedger:
        digest = _payload_digest(payload)
        ledger_queue = self._consumed_ledgers_by_payload_digest.get(digest)
        ledger = None if not ledger_queue else ledger_queue.popleft()
        if ledger_queue is not None and not ledger_queue:
            self._consumed_ledgers_by_payload_digest.pop(digest, None)
        if ledger is None:
            raise ValueError("missing_external_visibility_scan_ledger")
        return ledger

    def discard_visibility_ledger_for_payload(self, payload: bytes) -> None:
        digest = _payload_digest(payload)
        ledger_queue = self._consumed_ledgers_by_payload_digest.get(digest)
        if not ledger_queue:
            return
        ledger_queue.popleft()
        if not ledger_queue:
            self._consumed_ledgers_by_payload_digest.pop(digest, None)


async def run_fully_async_producer_loop(
    *,
    runtime: RepoHarnessRuntime,
    requests: Sequence[RepoHarnessEpisodeRequest],
    llm_gateway_factory: Callable[[RepoHarnessEpisodeRequest, int], LLMGateway] | None = None,
    llm_gateway: LLMGateway | None = None,
    message_queue_client: Any,
    producer_config: RepoHarnessFullyAsyncProducerConfig | Mapping[str, Any] | None = None,
    rollout_sample_factory: Callable[[RepoHarnessEpisodeResult, RepoHarnessFullyAsyncQueueFacts], Any] | None = None,
) -> RepoHarnessFullyAsyncProducerResult:
    """Run a local async producer loop and write terminal samples to a queue."""

    config = (
        producer_config
        if isinstance(producer_config, RepoHarnessFullyAsyncProducerConfig)
        else RepoHarnessFullyAsyncProducerConfig.model_validate(producer_config or {})
    )
    if llm_gateway is None and llm_gateway_factory is None:
        raise ValueError("llm_gateway or llm_gateway_factory is required")

    diagnostics: list[str] = []
    active_handles: list[Any] = []
    started = completed = cancelled = timed_out = 0
    queue_success = queue_failure = produced = valid = rejected = diagnostic = 0
    produced_ids: list[str] = []
    rejected_ids: list[str] = []
    diagnostic_ids: list[str] = []
    semaphore = asyncio.Semaphore(config.producer_concurrency)

    async def produce_one(index: int, request: RepoHarnessEpisodeRequest) -> None:
        nonlocal started, completed, cancelled, timed_out
        nonlocal queue_success, queue_failure, produced, valid, rejected, diagnostic
        async with semaphore:
            gateway = llm_gateway_factory(request, index) if llm_gateway_factory is not None else llm_gateway
            if gateway is None:
                raise ValueError("llm_gateway_factory returned None")
            handle = await runtime.start_episode(request, llm_gateway=gateway)
            active_handles.append(handle)
            started += 1
            try:
                result = await handle.wait_result(timeout=config.episode_wait_timeout_seconds)
            except asyncio.TimeoutError:
                timed_out += 1
                diagnostics.append(f"{request.episode_id}:episode_wait_timeout")
                await _cancel_handle_with_bounded_wait(
                    handle,
                    reason="stage13_3a_episode_wait_timeout",
                    diagnostics=diagnostics,
                    wait_timeout_seconds=_active_handle_cleanup_timeout(config),
                )
                return
            except asyncio.CancelledError:
                cancelled += 1
                await handle.cancel("stage13_3a_producer_cancelled")
                raise
            completed += 1
            facts = build_queue_facts_from_episode_result(
                result,
                visibility_scan_status=config.visibility_scan_status,
                visibility_scan_digest=config.visibility_scan_digest,
                current_global_steps=config.current_global_steps,
                staleness_threshold=config.staleness_threshold,
                partial_rollout_supported=config.partial_rollout_supported,
                partial_rollout_status=config.partial_rollout_status,
            )
            if facts.sample_classification == "valid":
                valid += 1
                produced_ids.append(facts.sample_id)
            elif facts.sample_classification == "diagnostic":
                diagnostic += 1
                diagnostic_ids.append(facts.sample_id)
            else:
                rejected += 1
                rejected_ids.append(facts.sample_id)

            if facts.sample_classification != "valid" and not config.queue_diagnostic_payloads:
                diagnostics.append(f"{facts.sample_id}:not_enqueued:{facts.rejection_reason or facts.invalid_reason}")
                return

            rollout_sample = _build_rollout_sample(result, facts, rollout_sample_factory)
            payload = serialize_rollout_sample_for_message_queue(
                rollout_sample,
                visibility_scan_status=config.visibility_scan_status,
                visibility_scan_digest=config.visibility_scan_digest,
                serializer=config.serializer,
            )
            try:
                put_coro = _put_sample_with_optional_ledger(
                    message_queue_client,
                    payload,
                    visibility_scan_status=config.visibility_scan_status,
                    visibility_scan_digest=config.visibility_scan_digest,
                )
                success = await _maybe_wait_for(put_coro, config.queue_put_timeout_seconds)
            except asyncio.TimeoutError:
                queue_failure += 1
                diagnostics.append(f"{facts.sample_id}:queue_put_timeout")
                return
            if success:
                produced += 1
                queue_success += 1
            else:
                queue_failure += 1
                diagnostics.append(f"{facts.sample_id}:queue_put_failed")

    tasks = [asyncio.create_task(produce_one(index, request)) for index, request in enumerate(requests)]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        await _cancel_pending_producer_work(
            tasks,
            active_handles,
            reason="stage13_3a_producer_cancelled",
            diagnostics=diagnostics,
            wait_timeout_seconds=_active_handle_cleanup_timeout(config),
        )
        raise
    except Exception:
        await _cancel_pending_producer_work(
            tasks,
            active_handles,
            reason="stage13_3a_producer_exception",
            diagnostics=diagnostics,
            wait_timeout_seconds=_active_handle_cleanup_timeout(config),
        )
        raise

    queue_size = 0
    if hasattr(message_queue_client, "get_queue_size"):
        queue_size = int(await message_queue_client.get_queue_size())
    return RepoHarnessFullyAsyncProducerResult(
        started_episode_count=started,
        completed_episode_count=completed,
        cancelled_episode_count=cancelled,
        timeout_episode_count=timed_out,
        queue_put_success_count=queue_success,
        queue_put_failure_count=queue_failure,
        produced_sample_count=produced,
        valid_candidate_count=valid,
        rejected_candidate_count=rejected,
        diagnostic_candidate_count=diagnostic,
        queue_size_after_produce=queue_size,
        producer_diagnostics=diagnostics,
        produced_sample_ids=produced_ids,
        rejected_sample_ids=rejected_ids,
        diagnostic_sample_ids=diagnostic_ids,
    )


async def select_valid_samples_from_message_queue(
    message_queue_client: Any,
    *,
    required_samples: int,
    visibility_scan_ledger: Callable[[bytes], QueuePayloadLedger | tuple[str, str] | Mapping[str, str]] | None = None,
    current_global_steps: int | None = None,
    staleness_threshold: int | None = None,
    max_dequeue_count: int | None = None,
    dequeue_timeout_seconds: float | None = None,
    serializer: Literal["cloudpickle", "pickle"] = "cloudpickle",
) -> tuple[list[Any], RepoHarnessFullyAsyncSelectionReport]:
    """Read queue payloads until enough valid samples are selected or input ends."""

    if required_samples <= 0:
        raise ValueError("required_samples must be positive")
    if max_dequeue_count is None:
        max_dequeue_count = max(required_samples, required_samples * 8)
    if dequeue_timeout_seconds is None:
        dequeue_timeout_seconds = DEFAULT_QUEUE_DEQUEUE_TIMEOUT_SECONDS
    selected: list[Any] = []
    rejected_reasons: dict[str, str] = {}
    rejected_count = 0
    diagnostic_count = 0
    observed = 0

    while len(selected) < required_samples and observed < max_dequeue_count:
        rollout_sample = None
        try:
            raw = await _maybe_wait_for(message_queue_client.get_sample(), dequeue_timeout_seconds)
        except asyncio.TimeoutError:
            rejected_reasons[f"queue-timeout-{observed}"] = "queue_get_timeout"
            break
        payload, _queue_len = _coerce_queue_get_result(raw)
        if payload is None:
            break
        observed += 1
        try:
            ledger = _resolve_visibility_ledger(
                payload,
                visibility_scan_ledger=visibility_scan_ledger,
                message_queue_client=message_queue_client,
            )
            rollout_sample = deserialize_message_queue_payload(
                payload,
                visibility_scan_status=ledger.visibility_scan_status,
                visibility_scan_digest=ledger.visibility_scan_digest,
                serializer=serializer,
            )
            facts = queue_facts_from_rollout_sample(rollout_sample)
            if not facts.valid_for_policy_loss:
                raise ValueError(facts.rejection_reason or facts.invalid_reason or facts.sample_classification)
            validate_rollout_sample_for_trainer_batch(
                rollout_sample,
                current_global_steps=current_global_steps,
                staleness_threshold=staleness_threshold,
            )
        except Exception as exc:
            sample_id = f"unparseable-{observed}"
            try:
                if rollout_sample is not None:
                    facts = queue_facts_from_rollout_sample(rollout_sample)
                    sample_id = facts.sample_id
                    if facts.sample_classification == "diagnostic":
                        diagnostic_count += 1
                    else:
                        rejected_count += 1
                else:
                    rejected_count += 1
            except Exception:
                rejected_count += 1
            rejected_reasons[sample_id] = str(exc)
            continue
        selected.append(rollout_sample)

    insufficient = len(selected) < required_samples
    return selected, RepoHarnessFullyAsyncSelectionReport(
        required_samples=required_samples,
        observed_queue_samples=observed,
        valid_sample_count=len(selected),
        rejected_sample_count=rejected_count,
        diagnostic_sample_count=diagnostic_count,
        insufficient_valid_samples=insufficient,
        insufficient_reason="insufficient_valid_queue_samples" if insufficient else None,
        selected_sample_ids=[queue_facts_from_rollout_sample(sample).sample_id for sample in selected],
        rejected_reasons=rejected_reasons,
    )


def build_fake_trainer_step_report(
    selection_report: RepoHarnessFullyAsyncSelectionReport,
    *,
    parameter_clock: FakeParameterClock | Mapping[str, Any] | None = None,
) -> FakeFullyAsyncTrainerStepReport:
    """Build a local fake trainer step report from a selection report."""

    clock = (
        parameter_clock
        if isinstance(parameter_clock, FakeParameterClock)
        else FakeParameterClock.model_validate(parameter_clock or {})
    )
    next_global_steps, next_param_version = clock.next_after_fake_step()
    rejected_reasons = dict(selection_report.rejected_reasons)
    return FakeFullyAsyncTrainerStepReport(
        required_samples=selection_report.required_samples,
        selected_valid_sample_count=selection_report.valid_sample_count,
        selected_sample_ids=list(selection_report.selected_sample_ids),
        current_global_steps=clock.current_global_steps,
        next_global_steps=next_global_steps,
        current_param_version=clock.current_param_version,
        next_param_version=next_param_version,
        stale_sample_count=_count_reasons(rejected_reasons, "stale"),
        filtered_stale_sample_count=_count_reasons(rejected_reasons, "stale"),
        partial_rejected_count=_count_reasons(rejected_reasons, "partial"),
        visibility_rejected_count=_count_any_reason(rejected_reasons, ("visibility", "ledger")),
        pending_reward_rejected_count=_count_any_reason(rejected_reasons, ("pending", "reward")),
        rejected_sample_count=selection_report.rejected_sample_count,
        diagnostic_sample_count=selection_report.diagnostic_sample_count,
        real_policy_loss_executed=False,
        fake_selection_step_executed=selection_report.valid_sample_count >= selection_report.required_samples,
        policy_loss_execution_mode="fake_local_selection_only",
        insufficient_valid_samples=selection_report.insufficient_valid_samples,
        rejection_reasons=rejected_reasons,
    )


def default_rollout_sample_factory(
    _result: RepoHarnessEpisodeResult,
    facts: RepoHarnessFullyAsyncQueueFacts,
) -> Any:
    """Create a tiny RolloutSample-shaped object without importing verl."""

    return SimpleNamespace(
        full_batch=SimpleNamespace(
            batch={
                "responses": [[1]],
                "response_mask": [[1]],
            },
            non_tensor_batch={},
            meta_info={"metrics": [{"generate_sequences": 0.0, "tool_calls": 0.0}]},
        ),
        sample_id=facts.sample_id,
        epoch=0,
        rollout_status={},
    )


def _build_rollout_sample(
    result: RepoHarnessEpisodeResult,
    facts: RepoHarnessFullyAsyncQueueFacts,
    rollout_sample_factory: Callable[[RepoHarnessEpisodeResult, RepoHarnessFullyAsyncQueueFacts], Any] | None,
) -> Any:
    sample = (
        rollout_sample_factory(result, facts)
        if rollout_sample_factory is not None
        else default_rollout_sample_factory(result, facts)
    )
    return attach_queue_facts_to_rollout_sample(sample, facts)


async def _put_sample_with_optional_ledger(
    message_queue_client: Any,
    payload: bytes,
    *,
    visibility_scan_status: str | None,
    visibility_scan_digest: str | None,
) -> bool:
    try:
        return bool(
            await message_queue_client.put_sample(
                payload,
                visibility_scan_status=visibility_scan_status,
                visibility_scan_digest=visibility_scan_digest,
            )
        )
    except TypeError:
        return bool(await message_queue_client.put_sample(sample=payload))


async def _maybe_wait_for(awaitable: Awaitable[Any], timeout: float | None) -> Any:
    if timeout is None:
        return await awaitable
    return await asyncio.wait_for(awaitable, timeout=timeout)


def _coerce_queue_get_result(raw: Any) -> tuple[bytes | None, int]:
    if raw is None:
        return None, 0
    if isinstance(raw, tuple) and len(raw) == 2:
        payload, queue_len = raw
        if payload is not None and not isinstance(payload, bytes):
            raise ValueError("queue_payload_must_be_bytes_or_none")
        return payload, int(queue_len)
    if isinstance(raw, bytes):
        return raw, 0
    raise ValueError("unexpected_message_queue_get_sample_shape")


def _resolve_visibility_ledger(
    payload: bytes,
    *,
    visibility_scan_ledger: Callable[[bytes], QueuePayloadLedger | tuple[str, str] | Mapping[str, str]] | None,
    message_queue_client: Any,
) -> QueuePayloadLedger:
    if visibility_scan_ledger is not None:
        if hasattr(message_queue_client, "discard_visibility_ledger_for_payload"):
            message_queue_client.discard_visibility_ledger_for_payload(payload)
        raw = visibility_scan_ledger(payload)
    elif hasattr(message_queue_client, "visibility_ledger_for_payload"):
        raw = message_queue_client.visibility_ledger_for_payload(payload)
    else:
        raise ValueError("missing_external_visibility_scan_ledger")
    if isinstance(raw, QueuePayloadLedger):
        return raw
    if isinstance(raw, tuple) and len(raw) == 2:
        return QueuePayloadLedger(visibility_scan_status=str(raw[0]), visibility_scan_digest=str(raw[1]))
    if isinstance(raw, Mapping):
        return QueuePayloadLedger(
            visibility_scan_status=str(raw["visibility_scan_status"]),
            visibility_scan_digest=str(raw["visibility_scan_digest"]),
        )
    raise ValueError("invalid_external_visibility_scan_ledger")


def _payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


async def _cancel_pending_producer_work(
    tasks: Sequence[asyncio.Task[Any]],
    active_handles: Sequence[Any],
    *,
    reason: str,
    diagnostics: list[str],
    wait_timeout_seconds: float,
) -> None:
    """Cancel producer tasks and wait briefly for active episode handles to release."""

    terminal_statuses = {"completed", "cancelled", "timeout", "failed", "orphaned"}
    for handle in list(active_handles):
        snapshot = handle.snapshot()
        if snapshot.async_status in terminal_statuses:
            continue
        await _cancel_handle_with_bounded_wait(
            handle,
            reason=reason,
            diagnostics=diagnostics,
            wait_timeout_seconds=wait_timeout_seconds,
        )

    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _active_handle_cleanup_timeout(config: RepoHarnessFullyAsyncProducerConfig) -> float:
    if config.episode_wait_timeout_seconds is None:
        return 1.0
    return min(max(config.episode_wait_timeout_seconds, 0.1), 5.0)


async def _cancel_handle_with_bounded_wait(
    handle: Any,
    *,
    reason: str,
    diagnostics: list[str],
    wait_timeout_seconds: float,
) -> None:
    snapshot = handle.snapshot()
    try:
        await handle.cancel(reason)
    except Exception as exc:  # pragma: no cover - defensive diagnostic path.
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_failed:{exc.__class__.__name__}: {exc}")
    try:
        await handle.wait_result(timeout=wait_timeout_seconds)
    except asyncio.TimeoutError:
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_wait_timeout")
    except asyncio.CancelledError:
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_wait_cancelled")
    except Exception as exc:
        diagnostics.append(f"{snapshot.run_id}:handle_cancel_wait_error:{exc.__class__.__name__}: {exc}")


def _count_reasons(rejected_reasons: Mapping[str, str], marker: str) -> int:
    return sum(1 for reason in rejected_reasons.values() if marker in reason)


def _count_any_reason(rejected_reasons: Mapping[str, str], markers: tuple[str, ...]) -> int:
    return sum(1 for reason in rejected_reasons.values() if any(marker in reason for marker in markers))
