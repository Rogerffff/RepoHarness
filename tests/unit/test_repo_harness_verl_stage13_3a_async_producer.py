from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from repo_harness.rl import (
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeResult,
    RepoHarnessEpisodeRequest,
)
from repo_harness_verl import (
    InMemoryFullyAsyncMessageQueueClient,
    RepoHarnessFullyAsyncProducerConfig,
    run_fully_async_producer_loop,
    select_valid_samples_from_message_queue,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(suffix: str) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    payload["episode_id"] = f"stage13-3a-producer-episode-{suffix}"
    payload["run_id"] = f"stage13-3a-producer-run-{suffix}"
    payload["task_id"] = f"stage13-3a-producer-task-{suffix}"
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _episode_result(suffix: str) -> RepoHarnessEpisodeResult:
    payload = _load_json("canonical_episode_result.json")
    payload["episode_id"] = f"stage13-3a-producer-episode-{suffix}"
    payload["run_id"] = f"stage13-3a-producer-run-{suffix}"
    payload["task_id"] = f"stage13-3a-producer-task-{suffix}"
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_episode_id": payload["episode_id"],
        "repo_harness_run_id": payload["run_id"],
        "repo_harness_task_id": payload["task_id"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return RepoHarnessEpisodeResult.model_validate(payload)


class StaticAsyncHandle:
    def __init__(self, result: RepoHarnessEpisodeResult) -> None:
        self.result = result
        self.cancelled = False

    async def wait_result(self, timeout: float | None = None) -> RepoHarnessEpisodeResult:
        return self.result

    async def cancel(self, reason: str = "cancel_requested"):
        self.cancelled = True
        return None


class StaticAsyncRuntime:
    def __init__(self) -> None:
        self.started_requests: list[RepoHarnessEpisodeRequest] = []

    async def start_episode(self, request: RepoHarnessEpisodeRequest, *, llm_gateway: object) -> StaticAsyncHandle:
        self.started_requests.append(request)
        suffix = request.episode_id.removeprefix("stage13-3a-producer-episode-")
        return StaticAsyncHandle(_episode_result(suffix))


class ImmediateGateway:
    def __init__(self, token_id: int) -> None:
        self.token_id = token_id
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        return LLMGatewayResponse(
            route=request.route,
            inference_backend=request.inference_backend,
            model_call_id=request.model_call_id,
            assistant_message={"role": "assistant", "content": f"done {self.token_id}"},
            prompt_ids=[101],
            output_token_ids=[self.token_id],
            output_logprobs=[-0.1],
            response_mask=[1],
            stop_reason="stop",
            usage={"input_tokens": 1, "output_tokens": 1},
        )


def test_stage13_3a_producer_loop_writes_terminal_valid_samples_to_queue() -> None:
    async def scenario() -> None:
        runtime = StaticAsyncRuntime()
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=8)
        requests = [_episode_request("a"), _episode_request("b")]
        gateways: list[ImmediateGateway] = []

        def gateway_factory(_request: RepoHarnessEpisodeRequest, index: int) -> ImmediateGateway:
            gateway = ImmediateGateway(910 + index)
            gateways.append(gateway)
            return gateway

        result = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=requests,
            llm_gateway_factory=gateway_factory,
            message_queue_client=queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=2, max_queue_backlog=8),
        )

        assert result.started_episode_count == 2
        assert result.completed_episode_count == 2
        assert result.valid_candidate_count == 2
        assert result.queue_put_success_count == 2
        assert result.queue_size_after_produce == 2
        assert len(runtime.started_requests) == 2
        assert [len(gateway.requests) for gateway in gateways] == [0, 0]

        selected, selection_report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=2,
            current_global_steps=10,
            staleness_threshold=2,
        )
        assert len(selected) == 2
        assert selection_report.valid_sample_count == 2
        assert selection_report.insufficient_valid_samples is False

    asyncio.run(scenario())


def test_stage13_3a_producer_queue_put_failure_keeps_diagnostic_and_releases_run_id() -> None:
    async def scenario() -> None:
        runtime = StaticAsyncRuntime()
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=1, overflow_policy="reject")
        request_a = _episode_request("queue-full-a")
        request_b = _episode_request("queue-full-b")

        result = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=[request_a, request_b],
            llm_gateway_factory=lambda _request, index: ImmediateGateway(930 + index),
            message_queue_client=queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=1, max_queue_backlog=1),
        )

        assert result.queue_put_success_count == 1
        assert result.queue_put_failure_count == 1
        assert any("queue_put_failed" in item for item in result.producer_diagnostics)

        retry_queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=1)
        retry_result = await run_fully_async_producer_loop(
            runtime=runtime,
            requests=[request_b],
            llm_gateway=ImmediateGateway(999),
            message_queue_client=retry_queue,
            producer_config=RepoHarnessFullyAsyncProducerConfig(required_samples=1, max_queue_backlog=1),
        )
        assert retry_result.queue_put_success_count == 1
        assert len(runtime.started_requests) == 3

    asyncio.run(scenario())
