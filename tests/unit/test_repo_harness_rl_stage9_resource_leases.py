import asyncio

import pytest
from pydantic import ValidationError

from repo_harness.rl import (
    AsyncResourceLimiter,
    LLMGatewayRequest,
    RepoHarnessEpisodeRequest,
    ResourceConcurrencyPolicy,
    ResourceLeaseError,
    ResourceLeaseManager,
    ResourceSummary,
    combine_cleanup_status,
    normalize_cleanup_status,
)

from pathlib import Path
import json


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_stage9_cleanup_status_uses_canonical_mapping() -> None:
    assert normalize_cleanup_status("ok") == "completed"
    assert normalize_cleanup_status("not_required") == "skipped"
    assert normalize_cleanup_status("not_started") == "not_started"
    assert normalize_cleanup_status("completed") == "completed"
    assert normalize_cleanup_status("failed") == "failed"
    assert normalize_cleanup_status("skipped") == "skipped"
    assert combine_cleanup_status("skipped", "completed") == "completed"
    assert combine_cleanup_status("completed", "failed") == "failed"


def test_stage9_resource_policy_roundtrips_and_rejects_unknown_routes() -> None:
    policy = ResourceConcurrencyPolicy(
        worker_id="worker-a",
        concurrency_group="stage9-local",
        max_concurrent_episodes=2,
        max_workspace_leases=2,
        max_gateway_route_concurrency_by_route={"mock": 1, "verl": 2},
        route_queue_timeout_seconds=0.05,
    )

    dumped = policy.model_dump(mode="json")
    assert ResourceConcurrencyPolicy.model_validate(dumped) == policy

    with pytest.raises(ValueError, match="unknown gateway route"):
        ResourceConcurrencyPolicy(max_gateway_route_concurrency_by_route={"bad_route": 1})


def test_stage9_async_resource_limiter_waits_and_releases_slot() -> None:
    async def scenario() -> tuple[float, int]:
        limiter = AsyncResourceLimiter(resource_name="gateway_route_mock", max_concurrency=1)
        first = await limiter.acquire(owner_id="owner-a")
        waiter = asyncio.create_task(limiter.acquire(owner_id="owner-b"))
        await asyncio.sleep(0.01)
        assert limiter.active_count == 1
        await limiter.release(first)
        second = await waiter
        wait_seconds = second.queue_wait_seconds
        await limiter.release(second)
        return wait_seconds, limiter.active_count

    wait_seconds, active_count = asyncio.run(scenario())

    assert wait_seconds > 0
    assert active_count == 0


def test_stage9_async_resource_limiter_queue_timeout_does_not_hold_slot() -> None:
    async def scenario() -> int:
        limiter = AsyncResourceLimiter(
            resource_name="gateway_route_mock",
            max_concurrency=1,
            queue_timeout_seconds=0.01,
            timeout_status_reason="gateway_route_queue_timeout",
        )
        first = await limiter.acquire(owner_id="owner-a")
        with pytest.raises(ResourceLeaseError) as exc_info:
            await limiter.acquire(owner_id="owner-b")
        assert exc_info.value.status_reason == "gateway_route_queue_timeout"
        assert exc_info.value.episode_status == "timeout"
        await limiter.release(first)
        third = await limiter.acquire(owner_id="owner-c")
        await limiter.release(third)
        return limiter.active_count

    assert asyncio.run(scenario()) == 0


def test_stage9_async_resource_limiter_cancelled_waiter_does_not_leak_slot() -> None:
    async def scenario() -> int:
        limiter = AsyncResourceLimiter(resource_name="gateway_route_mock", max_concurrency=1)
        first = await limiter.acquire(owner_id="owner-a")
        waiter = asyncio.create_task(limiter.acquire(owner_id="owner-b"))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        await limiter.release(first)
        second = await limiter.acquire(owner_id="owner-c")
        await limiter.release(second)
        return limiter.active_count

    assert asyncio.run(scenario()) == 0


def test_stage9_resource_manager_rejects_duplicate_active_run_id() -> None:
    async def scenario() -> str:
        manager = ResourceLeaseManager(
            ResourceConcurrencyPolicy(max_concurrent_episodes=2, max_workspace_leases=2)
        )
        first = await manager.acquire_episode(
            episode_id="episode-a",
            run_id="same-run",
            task_id="task",
        )
        try:
            with pytest.raises(ResourceLeaseError) as exc_info:
                await manager.acquire_episode(
                    episode_id="episode-b",
                    run_id="same-run",
                    task_id="task",
                )
            return exc_info.value.status_reason
        finally:
            await manager.release_episode(first)

    assert asyncio.run(scenario()) == "run_directory_lock_conflict"


@pytest.mark.parametrize("field_name", ["episode_id", "run_id", "task_id"])
def test_stage9_resource_manager_rejects_path_semantics_in_direct_api(field_name: str) -> None:
    async def scenario() -> None:
        manager = ResourceLeaseManager(
            ResourceConcurrencyPolicy(max_concurrent_episodes=1, max_workspace_leases=1)
        )
        kwargs = {"episode_id": "episode-safe", "run_id": "run-safe", "task_id": "task-safe"}
        kwargs[field_name] = "../escape"
        with pytest.raises(ValueError, match=field_name):
            await manager.acquire_episode(**kwargs)

    asyncio.run(scenario())


def test_stage9_resource_summary_rejects_absolute_queue_resource_name() -> None:
    with pytest.raises(ValueError, match="queue_wait_seconds_by_resource"):
        ResourceSummary(queue_wait_seconds_by_resource={"/Users/roger/private": 0.1})


@pytest.mark.parametrize("cleanup_status", ["ok", "not_required", "bad"])
def test_stage9_resource_summary_rejects_non_canonical_cleanup_status(cleanup_status: str) -> None:
    with pytest.raises(ValidationError):
        ResourceSummary(cleanup_status=cleanup_status)


@pytest.mark.parametrize("field_name", ["run_id", "episode_id", "task_id"])
@pytest.mark.parametrize("bad_value", ["../escape", "foo/bar", ".", ".."])
def test_stage9_episode_request_rejects_path_semantics_in_identifiers(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _load_json("canonical_episode_request.json")
    payload[field_name] = bad_value

    with pytest.raises(ValidationError, match=field_name):
        RepoHarnessEpisodeRequest.model_validate(payload)


@pytest.mark.parametrize("field_name", ["run_id", "episode_id", "task_id", "model_call_id"])
@pytest.mark.parametrize("bad_value", ["../escape", "foo/bar", ".", ".."])
def test_stage9_gateway_request_rejects_path_semantics_in_identifiers(
    field_name: str,
    bad_value: str,
) -> None:
    payload = _load_json("canonical_llm_gateway_request.json")
    payload[field_name] = bad_value

    with pytest.raises(ValidationError, match=field_name):
        LLMGatewayRequest.model_validate(payload)
