from __future__ import annotations

import asyncio
from pathlib import Path

from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessRuntime,
    ResourceConcurrencyPolicy,
    ResourceLeaseManager,
)

from test_repo_harness_verl_stage12a_real_episode_smoke import (
    _mock_gateway_responses,
    _mock_request,
    _runtime_options,
)


class BlockingFirstGateway:
    def __init__(self, responses: list[LLMGatewayResponse]) -> None:
        self.responses = list(responses)
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            self.started.set()
            await self.release.wait()
        if not self.responses:
            raise AssertionError("blocking gateway output queue exhausted")
        return self.responses.pop(0)


def _request_for(*, run_id: str, episode_id: str, task_id: str):
    return _mock_request().model_copy(update={"run_id": run_id, "episode_id": episode_id, "task_id": task_id})


def test_stage12a_concurrent_real_episodes_share_snapshot_but_isolate_workspaces_and_runs(tmp_path: Path) -> None:
    resource_manager = ResourceLeaseManager(
        ResourceConcurrencyPolicy(
            max_concurrent_episodes=2,
            max_workspace_leases=2,
            max_gateway_route_concurrency_by_route={
                "verl": 1,
                "openai": 1,
                "deepseek": 1,
                "local_vllm": 1,
                "local_sglang": 1,
                "replay": 1,
                "mock": 1,
            },
        )
    )
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, resource_lease_manager=resource_manager))
    first_request = _request_for(
        run_id="stage12a-concurrency-run-a",
        episode_id="stage12a-concurrency-episode-a",
        task_id="stage12a-concurrency-task",
    )
    second_request = _request_for(
        run_id="stage12a-concurrency-run-b",
        episode_id="stage12a-concurrency-episode-b",
        task_id="stage12a-concurrency-task",
    )
    first_gateway = BlockingFirstGateway(_mock_gateway_responses())
    second_gateway = FakeLLMGateway(_mock_gateway_responses())

    async def scenario():
        first = asyncio.create_task(runtime.run_episode(first_request, llm_gateway=first_gateway))
        await asyncio.wait_for(first_gateway.started.wait(), timeout=1.0)
        second = asyncio.create_task(runtime.run_episode(second_request, llm_gateway=second_gateway))
        await asyncio.sleep(0.05)
        assert not second.done()
        first_gateway.release.set()
        first_result, second_result = await asyncio.gather(first, second)
        return first_result, second_result

    first_result, second_result = asyncio.run(scenario())

    assert first_result.status == "succeeded"
    assert second_result.status == "succeeded"
    assert first_result.resource_summary is not None
    assert second_result.resource_summary is not None
    assert first_result.resource_summary.snapshot_key == second_result.resource_summary.snapshot_key
    assert first_result.resource_summary.workspace_path != second_result.resource_summary.workspace_path
    assert first_result.resource_summary.run_dir != second_result.resource_summary.run_dir
    assert first_result.resource_summary.cleanup_status == "completed"
    assert second_result.resource_summary.cleanup_status == "completed"
    assert first_result.resource_summary.inference_concurrency_slot is not None
    assert second_result.resource_summary.inference_concurrency_slot is not None
    assert not resource_manager._active_run_ids
    assert resource_manager._episode_limiter.active_count == 0
    assert resource_manager._workspace_limiter.active_count == 0
    assert resource_manager._route_limiter("mock").active_count == 0

    first_manifest = tmp_path / "stage12a_runs" / first_request.run_id / "artifacts.json"
    second_manifest = tmp_path / "stage12a_runs" / second_request.run_id / "artifacts.json"
    assert first_manifest.exists()
    assert second_manifest.exists()
    assert first_manifest != second_manifest
