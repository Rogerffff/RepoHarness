from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import (
    AsyncEpisodeStartError,
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(**updates: Any) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    for key, value in updates.items():
        payload[key] = value
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _gateway_response(request: LLMGatewayRequest, *, token_id: int = 901) -> LLMGatewayResponse:
    return LLMGatewayResponse(
        route=request.route,
        inference_backend=request.inference_backend,
        model_call_id=request.model_call_id,
        assistant_message={"role": "assistant", "content": f"stage13.1 token {token_id}"},
        prompt_ids=[101],
        output_token_ids=[token_id],
        output_logprobs=[-0.1],
        response_mask=[1],
        stop_reason="stop",
        duration_ms=1,
        usage={"input_tokens": 1, "output_tokens": 1},
    )


class BlockingGateway:
    def __init__(self) -> None:
        self.requests: list[LLMGatewayRequest] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        self.started.set()
        await self.release.wait()
        return _gateway_response(request)


async def _run_successful_episode(
    runtime: RepoHarnessRuntime,
    request: RepoHarnessEpisodeRequest,
    gateway: BlockingGateway,
):
    handle = await runtime.start_episode(request, llm_gateway=gateway)
    await asyncio.wait_for(gateway.started.wait(), timeout=1)
    gateway.release.set()
    result = await handle.wait_result(timeout=1)
    return handle, result


def test_stage13_1_start_episode_returns_handle_and_terminal_result() -> None:
    async def scenario() -> None:
        request = _episode_request()
        runtime = RepoHarnessRuntime()
        gateway = BlockingGateway()

        handle = await runtime.start_episode(request, llm_gateway=gateway)
        assert handle.handle_ref.handle_ref.startswith("rh://async/")
        assert handle.sample_attempt_id == "stage0h-episode-success:attempt-0"

        await asyncio.wait_for(gateway.started.wait(), timeout=1)
        pending_snapshot = handle.snapshot()
        assert pending_snapshot.final_audit_write_completed is False
        assert pending_snapshot.run_directory_writer_active is True
        assert pending_snapshot.resume.resume_supported is False

        gateway.release.set()
        result = await handle.wait_result(timeout=1)

        assert result.status == "succeeded"
        assert result.invalid_for_training is False
        assert result.invalid_for_online_rl is False
        assert result.training_view.response_ids == [901]
        assert gateway.requests[0].route == "verl"

        terminal_snapshot = handle.snapshot()
        assert terminal_snapshot.async_status == "completed"
        assert terminal_snapshot.episode_status == "succeeded"
        assert terminal_snapshot.final_audit_write_completed is True
        assert terminal_snapshot.run_directory_writer_active is False

    asyncio.run(scenario())


def test_stage13_1_sample_attempt_id_increments_per_episode_id() -> None:
    async def scenario() -> None:
        runtime = RepoHarnessRuntime()
        first_request = _episode_request(episode_id="stage13-episode", run_id="stage13-run-a")
        second_request = _episode_request(episode_id="stage13-episode", run_id="stage13-run-b")

        first_handle, first_result = await _run_successful_episode(runtime, first_request, BlockingGateway())
        second_handle, second_result = await _run_successful_episode(runtime, second_request, BlockingGateway())

        assert first_result.status == "succeeded"
        assert second_result.status == "succeeded"
        assert first_handle.sample_attempt_id == "stage13-episode:attempt-0"
        assert second_handle.sample_attempt_id == "stage13-episode:attempt-1"

    asyncio.run(scenario())


def test_stage13_1_duplicate_run_id_is_rejected_before_second_task_starts() -> None:
    async def scenario() -> None:
        runtime = RepoHarnessRuntime()
        first_gateway = BlockingGateway()
        second_gateway = BlockingGateway()
        first_request = _episode_request(episode_id="stage13-episode-a", run_id="shared-run-id")
        second_request = _episode_request(episode_id="stage13-episode-b", run_id="shared-run-id")

        first_handle = await runtime.start_episode(first_request, llm_gateway=first_gateway)
        await asyncio.wait_for(first_gateway.started.wait(), timeout=1)

        with pytest.raises(AsyncEpisodeStartError, match="run_id already has an active async episode"):
            await runtime.start_episode(second_request, llm_gateway=second_gateway)

        assert second_gateway.requests == []
        first_gateway.release.set()
        first_result = await first_handle.wait_result(timeout=1)
        assert first_result.status == "succeeded"

    asyncio.run(scenario())
