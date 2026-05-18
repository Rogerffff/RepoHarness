from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import (
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
)
from repo_harness_verl import (
    InMemoryFullyAsyncMessageQueueClient,
    RepoHarnessFullyAsyncProducerConfig,
    run_fully_async_producer_loop,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(suffix: str) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    payload["episode_id"] = f"stage13-3a-resource-episode-{suffix}"
    payload["run_id"] = f"stage13-3a-resource-run-{suffix}"
    payload["task_id"] = f"stage13-3a-resource-task-{suffix}"
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _gateway_response(request: LLMGatewayRequest) -> LLMGatewayResponse:
    return LLMGatewayResponse(
        route=request.route,
        inference_backend=request.inference_backend,
        model_call_id=request.model_call_id,
        assistant_message={"role": "assistant", "content": "done"},
        prompt_ids=[101],
        output_token_ids=[901],
        output_logprobs=[-0.1],
        response_mask=[1],
        stop_reason="stop",
        usage={"input_tokens": 1, "output_tokens": 1},
    )


class BlockingGateway:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.started.set()
        await self.release.wait()
        return _gateway_response(request)


class ImmediateGateway:
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        return _gateway_response(request)


class CompletingAfterPeerStartsGateway:
    def __init__(self, peer_started: asyncio.Event) -> None:
        self.peer_started = peer_started

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        await self.peer_started.wait()
        return _gateway_response(request)


def test_stage13_3a_message_queue_termination_signal_is_not_rejected_when_full() -> None:
    async def scenario() -> None:
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=1, overflow_policy="reject")
        assert await queue.put_sample(b"payload-without-ledger") is True
        assert await queue.put_sample(None) is True
        sample, queue_len = await queue.get_sample()
        stats = await queue.get_statistics()

        assert sample is None
        assert queue_len == 0
        assert stats["dropped_samples"] == 1

    asyncio.run(scenario())


def test_stage13_3a_episode_wait_timeout_does_not_enqueue_pending_sample_and_run_id_can_retry() -> None:
    async def scenario() -> None:
        runtime = RepoHarnessRuntime()
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        request = _episode_request("timeout")
        gateway = BlockingGateway()

        result = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=[request],
            llm_gateway=gateway,
            message_queue_client=queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(
                required_samples=1,
                max_queue_backlog=4,
                episode_wait_timeout_seconds=0.01,
            ),
        )

        assert result.timeout_episode_count == 1
        assert result.queue_put_success_count == 0
        assert await queue.get_queue_size() == 0

        retry_queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        retry = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=[request],
            llm_gateway=ImmediateGateway(),
            message_queue_client=retry_queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=1, max_queue_backlog=4),
        )
        assert retry.completed_episode_count == 1
        assert retry.timeout_episode_count == 0

        gateway.release.set()

    asyncio.run(scenario())


def test_stage13_3a_producer_loop_cancellation_does_not_leave_run_id_locked() -> None:
    async def scenario() -> None:
        runtime = RepoHarnessRuntime()
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        request = _episode_request("cancel")
        gateway = BlockingGateway()

        producer_task = asyncio.create_task(
            run_fully_async_producer_loop(
                runtime=runtime,
                requests=[request],
                llm_gateway=gateway,
                message_queue_client=queue,
                producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=1, max_queue_backlog=4),
            )
        )
        await asyncio.wait_for(gateway.started.wait(), timeout=1)
        producer_task.cancel()
        try:
            await producer_task
        except asyncio.CancelledError:
            pass
        else:  # pragma: no cover - defensive assertion.
            raise AssertionError("producer task cancellation must propagate asyncio.CancelledError")

        gateway.release.set()
        await asyncio.sleep(0.05)
        assert await queue.get_queue_size() == 0

        retry_queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        retry = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=[request],
            llm_gateway=ImmediateGateway(),
            message_queue_client=retry_queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=1, max_queue_backlog=4),
        )
        assert retry.completed_episode_count == 1

    asyncio.run(scenario())


def test_stage13_3a_producer_exception_cancels_active_handles_and_unlocks_run_id() -> None:
    async def scenario() -> None:
        runtime = RepoHarnessRuntime()
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        blocked_request = _episode_request("producer-exception-blocked")
        failing_request = _episode_request("producer-exception-failing")
        blocking_gateway = BlockingGateway()
        completing_gateway = CompletingAfterPeerStartsGateway(blocking_gateway.started)

        def gateway_factory(request: RepoHarnessEpisodeRequest, index: int) -> object:
            if index == 0:
                return blocking_gateway
            if index == 1:
                return completing_gateway
            raise AssertionError(f"unexpected request index: {index}")

        def rollout_sample_factory(result: object, facts: object) -> object:
            raise RuntimeError("stage13-3a-rollout-sample-boom")

        with pytest.raises(RuntimeError, match="stage13-3a-rollout-sample-boom"):
            await run_fully_async_producer_loop(
                runtime=runtime,
                requests=[blocked_request, failing_request],
                llm_gateway_factory=gateway_factory,  # type: ignore[arg-type]
                message_queue_client=queue,
                producer_config=RepoHarnessFullyAsyncProducerConfig(
                    required_samples=1,
                    max_queue_backlog=4,
                    producer_concurrency=2,
                    queue_diagnostic_payloads=True,
                ),
                rollout_sample_factory=rollout_sample_factory,  # type: ignore[arg-type]
            )

        blocking_gateway.release.set()
        await asyncio.sleep(0.05)
        assert await queue.get_queue_size() == 0

        retry_queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        retry = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=[blocked_request],
            llm_gateway=ImmediateGateway(),
            message_queue_client=retry_queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=1, max_queue_backlog=4),
        )
        assert retry.completed_episode_count == 1

    asyncio.run(scenario())
