import asyncio
import json
import threading
from pathlib import Path
from typing import Any

from repo_harness.rl import (
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
    ResourceConcurrencyPolicy,
    ResourceLeaseManager,
)
from repo_harness.verifier import VerifierPoolOptions, VerifierResult, VerifierWorkerPool


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
        assistant_message={"role": "assistant", "content": f"stage9 token {token_id}"},
        prompt_ids=[101, 102],
        output_token_ids=[token_id],
        output_logprobs=[-0.1],
        response_mask=[1],
        stop_reason="stop",
        duration_ms=0,
        usage={"input_tokens": 2, "output_tokens": 1},
    )


def _verifier_result() -> VerifierResult:
    return VerifierResult.model_validate(
        {
            "verifier_stage": "final",
            "parser_confidence": 0.9,
            "command": "pytest -q",
            "test_cases": [],
            "accepted": True,
            "pass_ratio": 1.0,
            "fail_to_pass": {"passed": 1, "total": 1},
            "pass_to_pass": {"passed": 1, "total": 1},
            "exit_code": 0,
            "timeout": False,
            "error_type": None,
        }
    )


class ControlledGateway:
    def __init__(self) -> None:
        self.requests: list[LLMGatewayRequest] = []
        self.started_count = 0
        self.active_count = 0
        self.max_active_count = 0
        self.first_started = asyncio.Event()
        self.release_first = asyncio.Event()
        self._lock = asyncio.Lock()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        async with self._lock:
            self.requests.append(request)
            self.started_count += 1
            current = self.started_count
            self.active_count += 1
            self.max_active_count = max(self.max_active_count, self.active_count)
            if current == 1:
                self.first_started.set()
        try:
            if current == 1:
                await self.release_first.wait()
            return _gateway_response(request, token_id=900 + current)
        finally:
            async with self._lock:
                self.active_count -= 1


class NeverReleaseGateway(ControlledGateway):
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        async with self._lock:
            self.requests.append(request)
            self.started_count += 1
            self.active_count += 1
            self.max_active_count = max(self.max_active_count, self.active_count)
            self.first_started.set()
        try:
            await self.release_first.wait()
            return _gateway_response(request)
        finally:
            async with self._lock:
                self.active_count -= 1


class BlockingCleanup:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = asyncio.Event()

    async def __call__(self) -> None:
        self.started.set()
        try:
            await self.release.wait()
        finally:
            self.finished.set()


def _runtime(
    *,
    route_timeout: float | None = None,
    max_route_concurrency: int = 1,
) -> RepoHarnessRuntime:
    policy = ResourceConcurrencyPolicy(
        max_concurrent_episodes=4,
        max_workspace_leases=4,
        max_gateway_route_concurrency_by_route={"verl": max_route_concurrency},
        route_queue_timeout_seconds=route_timeout,
    )
    return RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(resource_lease_manager=ResourceLeaseManager(policy))
    )


def test_stage9_runtime_runs_two_episodes_without_route_overlap() -> None:
    async def scenario() -> tuple[Any, Any, ControlledGateway]:
        gateway = ControlledGateway()
        runtime = _runtime(max_route_concurrency=1)
        first = asyncio.create_task(
            runtime.run_episode(
                _episode_request(run_id="stage9-run-a", episode_id="stage9-episode-a"),
                llm_gateway=gateway,
            )
        )
        await gateway.first_started.wait()
        second = asyncio.create_task(
            runtime.run_episode(
                _episode_request(run_id="stage9-run-b", episode_id="stage9-episode-b"),
                llm_gateway=gateway,
            )
        )
        await asyncio.sleep(0.01)
        assert gateway.max_active_count == 1
        gateway.release_first.set()
        return (*await asyncio.gather(first, second), gateway)

    first_result, second_result, gateway = asyncio.run(scenario())

    assert first_result.run_id != second_result.run_id
    assert first_result.audit_ref.run_dir != second_result.audit_ref.run_dir
    assert first_result.resource_summary is not None
    assert second_result.resource_summary is not None
    assert first_result.resource_summary.lease_id != second_result.resource_summary.lease_id
    assert first_result.resource_summary.inference_concurrency_slot is not None
    assert second_result.resource_summary.inference_concurrency_slot is not None
    assert first_result.resource_summary.cleanup_status == "completed"
    assert second_result.resource_summary.cleanup_status == "completed"
    assert gateway.max_active_count == 1
    assert (
        first_result.resource_summary.queue_wait_seconds_by_resource["gateway_route"] > 0
        or second_result.resource_summary.queue_wait_seconds_by_resource["gateway_route"] > 0
    )
    assert "/Users/" not in first_result.resource_summary.model_dump_json()
    assert "/Users/" not in second_result.training_view.model_dump_json()


def test_stage9_runtime_route_queue_timeout_returns_untrainable_timeout() -> None:
    async def scenario() -> tuple[Any, Any, NeverReleaseGateway]:
        gateway = NeverReleaseGateway()
        runtime = _runtime(route_timeout=0.01, max_route_concurrency=1)
        first = asyncio.create_task(
            runtime.run_episode(
                _episode_request(run_id="stage9-route-timeout-a", episode_id="stage9-route-timeout-a"),
                llm_gateway=gateway,
            )
        )
        await gateway.first_started.wait()
        second = await runtime.run_episode(
            _episode_request(run_id="stage9-route-timeout-b", episode_id="stage9-route-timeout-b"),
            llm_gateway=gateway,
        )
        gateway.release_first.set()
        first_result = await first
        return first_result, second, gateway

    first_result, second_result, gateway = asyncio.run(scenario())

    assert first_result.status == "succeeded"
    assert second_result.status == "timeout"
    assert second_result.status_reason == "gateway_route_queue_timeout"
    assert second_result.invalid_for_training is True
    assert second_result.invalid_for_online_rl is True
    assert second_result.resource_summary is not None
    assert second_result.resource_summary.cleanup_status == "completed"
    assert second_result.resource_summary.queue_wait_seconds_by_resource["gateway_route"] > 0
    assert second_result.timing_summary is not None
    assert second_result.timing_summary.model_call_seconds == 0
    assert len(gateway.requests) == 1


def test_stage9_runtime_episode_timeout_counts_submitted_gateway_request() -> None:
    async def scenario() -> tuple[Any, NeverReleaseGateway]:
        gateway = NeverReleaseGateway()
        runtime = _runtime(max_route_concurrency=1)
        result = await runtime.run_episode(
            _episode_request(
                run_id="stage9-model-timeout",
                episode_id="stage9-model-timeout",
                budgets={**_load_json("canonical_episode_request.json")["budgets"], "max_wall_seconds": 0.01},
            ),
            llm_gateway=gateway,
        )
        return result, gateway

    result, gateway = asyncio.run(scenario())

    assert result.status == "timeout"
    assert result.status_reason == "episode_timeout"
    assert len(gateway.requests) == 1
    assert result.timing_summary is not None
    assert result.timing_summary.model_call_seconds > 0
    assert result.timing_summary.model_call_count == 1
    assert result.budget_consumption is not None
    assert result.budget_consumption.used_model_calls == 1
    assert result.budget_consumption.used_model_call_seconds == result.timing_summary.model_call_seconds


def test_stage9_runtime_duplicate_run_writer_is_infrastructure_error() -> None:
    async def scenario() -> tuple[Any, Any]:
        gateway = ControlledGateway()
        runtime = _runtime(max_route_concurrency=1)
        first = asyncio.create_task(
            runtime.run_episode(
                _episode_request(run_id="stage9-same-run", episode_id="stage9-same-run-a"),
                llm_gateway=gateway,
            )
        )
        await gateway.first_started.wait()
        second = await runtime.run_episode(
            _episode_request(run_id="stage9-same-run", episode_id="stage9-same-run-b"),
            llm_gateway=gateway,
        )
        gateway.release_first.set()
        first_result = await first
        return first_result, second

    first_result, second_result = asyncio.run(scenario())

    assert first_result.status == "succeeded"
    assert second_result.status == "infrastructure_error"
    assert second_result.status_reason == "run_directory_lock_conflict"
    assert second_result.invalid_for_training is True
    assert second_result.training_view.extra_fields["repo_harness_invalid_reason"] == "run_lock_conflict"


def test_stage9_runtime_cancellation_releases_route_slot_for_next_episode() -> None:
    async def scenario() -> tuple[Any, Any, NeverReleaseGateway]:
        gateway = NeverReleaseGateway()
        runtime = _runtime(route_timeout=0.05, max_route_concurrency=1)
        first = asyncio.create_task(
            runtime.run_episode(
                _episode_request(run_id="stage9-cancel-a", episode_id="stage9-cancel-a"),
                llm_gateway=gateway,
            )
        )
        await gateway.first_started.wait()
        first.cancel()
        cancelled_result = await first
        gateway.release_first.set()
        second_result = await runtime.run_episode(
            _episode_request(run_id="stage9-cancel-b", episode_id="stage9-cancel-b"),
            llm_gateway=gateway,
        )
        return cancelled_result, second_result, gateway

    cancelled_result, second_result, gateway = asyncio.run(scenario())

    assert cancelled_result.status == "cancelled"
    assert cancelled_result.resource_summary is not None
    assert cancelled_result.resource_summary.cleanup_status == "completed"
    assert second_result.status == "succeeded"
    assert len(gateway.requests) == 2


def test_stage9_runtime_cancellation_during_cleanup_releases_episode_resources() -> None:
    async def scenario() -> tuple[Any, Any, Any, BlockingCleanup]:
        cleanup = BlockingCleanup()
        manager = ResourceLeaseManager(
            ResourceConcurrencyPolicy(
                max_concurrent_episodes=1,
                max_workspace_leases=1,
                episode_queue_timeout_seconds=0.01,
            )
        )
        runtime = RepoHarnessRuntime(
            RepoHarnessRuntimeOptions(
                resource_lease_manager=manager,
                cleanup_callback=cleanup,
            )
        )
        task = asyncio.create_task(
            runtime.run_episode(
                _episode_request(run_id="stage9-cleanup-cancel-run", episode_id="stage9-cleanup-cancel-a"),
                llm_gateway=ControlledGatewayWithoutWait(),
            )
        )
        await cleanup.started.wait()
        task.cancel()
        await asyncio.sleep(0)
        retry_runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(resource_lease_manager=manager))
        retry_before_cleanup = await retry_runtime.run_episode(
            _episode_request(run_id="stage9-cleanup-cancel-run", episode_id="stage9-cleanup-cancel-b"),
            llm_gateway=ControlledGatewayWithoutWait(),
        )
        assert cleanup.finished.is_set() is False
        cleanup.release.set()
        cancelled_result = await task
        retry_after_cleanup = await retry_runtime.run_episode(
            _episode_request(run_id="stage9-cleanup-cancel-run", episode_id="stage9-cleanup-cancel-c"),
            llm_gateway=ControlledGatewayWithoutWait(),
        )
        return cancelled_result, retry_before_cleanup, retry_after_cleanup, cleanup

    cancelled_result, retry_before_cleanup, retry_after_cleanup, cleanup = asyncio.run(scenario())

    assert cancelled_result.status == "cancelled"
    assert cancelled_result.status_reason == "runtime_cancelled"
    assert cancelled_result.resource_summary is not None
    assert cancelled_result.resource_summary.cleanup_status == "completed"
    assert any(diagnostic.code == "cleanup_cancelled" for diagnostic in cancelled_result.audit_diagnostics)
    assert retry_before_cleanup.status == "infrastructure_error"
    assert retry_before_cleanup.status_reason == "run_directory_lock_conflict"
    assert cleanup.finished.is_set() is True
    assert retry_after_cleanup.status == "succeeded"


def test_stage9_runtime_cleanup_callback_cancelled_does_not_hang_or_mark_episode_cancelled() -> None:
    async def cancelled_cleanup() -> None:
        raise asyncio.CancelledError()

    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            resource_lease_manager=ResourceLeaseManager(
                ResourceConcurrencyPolicy(max_concurrent_episodes=1, max_workspace_leases=1)
            ),
            cleanup_callback=cancelled_cleanup,
        )
    )

    result = asyncio.run(
        asyncio.wait_for(
            runtime.run_episode(
                _episode_request(run_id="stage9-cleanup-self-cancel", episode_id="stage9-cleanup-self-cancel"),
                llm_gateway=ControlledGatewayWithoutWait(),
            ),
            timeout=1.0,
        )
    )

    assert result.status == "succeeded"
    assert result.resource_summary is not None
    assert result.resource_summary.cleanup_status == "failed"
    assert any(diagnostic.code == "cleanup_callback_cancelled" for diagnostic in result.audit_diagnostics)


def test_stage9_runtime_cancellation_during_final_verifier_holds_run_until_verifier_finishes() -> None:
    async def scenario() -> tuple[Any, Any, Any, threading.Event]:
        verifier_started = threading.Event()
        verifier_release = threading.Event()
        verifier_finished = threading.Event()

        def blocking_verifier() -> VerifierResult:
            verifier_started.set()
            verifier_release.wait(timeout=2.0)
            verifier_finished.set()
            return _verifier_result()

        manager = ResourceLeaseManager(
            ResourceConcurrencyPolicy(
                max_concurrent_episodes=1,
                max_workspace_leases=1,
                episode_queue_timeout_seconds=0.01,
            )
        )
        pool = VerifierWorkerPool(VerifierPoolOptions(max_workers=1, max_pending_jobs=0))
        runtime = RepoHarnessRuntime(
            RepoHarnessRuntimeOptions(
                resource_lease_manager=manager,
                final_verifier_callable=blocking_verifier,
                verifier_worker_pool=pool,
            )
        )
        retry_runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(resource_lease_manager=manager))
        try:
            task = asyncio.create_task(
                runtime.run_episode(
                    _episode_request(run_id="stage9-verifier-cancel-run", episode_id="stage9-verifier-cancel-a"),
                    llm_gateway=ControlledGatewayWithoutWait(),
                )
            )
            await asyncio.to_thread(verifier_started.wait, 2.0)
            task.cancel()
            await asyncio.sleep(0)
            retry_before_verifier_finished = await retry_runtime.run_episode(
                _episode_request(run_id="stage9-verifier-cancel-run", episode_id="stage9-verifier-cancel-b"),
                llm_gateway=ControlledGatewayWithoutWait(),
            )
            assert verifier_finished.is_set() is False
            verifier_release.set()
            cancelled_result = await task
            retry_after_verifier_finished = await retry_runtime.run_episode(
                _episode_request(run_id="stage9-verifier-cancel-run", episode_id="stage9-verifier-cancel-c"),
                llm_gateway=ControlledGatewayWithoutWait(),
            )
            return cancelled_result, retry_before_verifier_finished, retry_after_verifier_finished, verifier_finished
        finally:
            verifier_release.set()
            pool.close()

    cancelled_result, retry_before_verifier_finished, retry_after_verifier_finished, verifier_finished = asyncio.run(
        scenario()
    )

    assert cancelled_result.status == "cancelled"
    assert retry_before_verifier_finished.status == "infrastructure_error"
    assert retry_before_verifier_finished.status_reason == "run_directory_lock_conflict"
    assert verifier_finished.is_set() is True
    assert retry_after_verifier_finished.status == "succeeded"


def test_stage9_runtime_cancellation_during_direct_final_verifier_holds_run_until_verifier_finishes() -> None:
    async def scenario() -> tuple[Any, Any, Any, threading.Event]:
        verifier_started = threading.Event()
        verifier_release = threading.Event()
        verifier_finished = threading.Event()

        def blocking_verifier() -> VerifierResult:
            verifier_started.set()
            verifier_release.wait(timeout=2.0)
            verifier_finished.set()
            return _verifier_result()

        manager = ResourceLeaseManager(
            ResourceConcurrencyPolicy(
                max_concurrent_episodes=1,
                max_workspace_leases=1,
                episode_queue_timeout_seconds=0.01,
            )
        )
        runtime = RepoHarnessRuntime(
            RepoHarnessRuntimeOptions(
                resource_lease_manager=manager,
                final_verifier_callable=blocking_verifier,
            )
        )
        retry_runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(resource_lease_manager=manager))
        try:
            task = asyncio.create_task(
                runtime.run_episode(
                    _episode_request(run_id="stage9-direct-verifier-cancel-run", episode_id="stage9-direct-verifier-cancel-a"),
                    llm_gateway=ControlledGatewayWithoutWait(),
                )
            )
            await asyncio.to_thread(verifier_started.wait, 2.0)
            task.cancel()
            await asyncio.sleep(0)
            retry_before_verifier_finished = await retry_runtime.run_episode(
                _episode_request(run_id="stage9-direct-verifier-cancel-run", episode_id="stage9-direct-verifier-cancel-b"),
                llm_gateway=ControlledGatewayWithoutWait(),
            )
            assert verifier_finished.is_set() is False
            verifier_release.set()
            cancelled_result = await task
            retry_after_verifier_finished = await retry_runtime.run_episode(
                _episode_request(run_id="stage9-direct-verifier-cancel-run", episode_id="stage9-direct-verifier-cancel-c"),
                llm_gateway=ControlledGatewayWithoutWait(),
            )
            return cancelled_result, retry_before_verifier_finished, retry_after_verifier_finished, verifier_finished
        finally:
            verifier_release.set()

    cancelled_result, retry_before_verifier_finished, retry_after_verifier_finished, verifier_finished = asyncio.run(
        scenario()
    )

    assert cancelled_result.status == "cancelled"
    assert retry_before_verifier_finished.status == "infrastructure_error"
    assert retry_before_verifier_finished.status_reason == "run_directory_lock_conflict"
    assert verifier_finished.is_set() is True
    assert retry_after_verifier_finished.status == "succeeded"


def test_stage9_runtime_cleanup_failure_preserves_primary_status_and_canonical_status() -> None:
    def fail_cleanup() -> None:
        raise RuntimeError("cleanup boom")

    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            resource_lease_manager=ResourceLeaseManager(
                ResourceConcurrencyPolicy(max_concurrent_episodes=1, max_workspace_leases=1)
            ),
            cleanup_callback=fail_cleanup,
        )
    )

    result = asyncio.run(
        runtime.run_episode(
            _episode_request(run_id="stage9-cleanup-failure", episode_id="stage9-cleanup-failure"),
            llm_gateway=ControlledGatewayWithoutWait(),
        )
    )

    assert result.status == "succeeded"
    assert result.resource_summary is not None
    assert result.resource_summary.cleanup_status == "failed"
    assert any(diagnostic.code == "cleanup_failed" for diagnostic in result.audit_diagnostics)


class ControlledGatewayWithoutWait:
    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        return _gateway_response(request, token_id=999)
