from __future__ import annotations

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
)
from repo_harness.verifier import VerifierResult


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(**updates: Any) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    payload["run_mode"] = "training_fast"
    payload["budgets"] = {
        **payload["budgets"],
        "max_turns": 4,
        "max_model_calls": 4,
        "max_tool_calls": 4,
        "max_artifact_bytes": 2_000_000,
    }
    for key, value in updates.items():
        payload[key] = value
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
        self.requests: list[LLMGatewayRequest] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        self.started.set()
        await self.release.wait()
        return _gateway_response(request)


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


def _source_repo(tmp_path: Path) -> Path:
    source = tmp_path / "source_repo"
    source.mkdir()
    (source / "README.md").write_text("stage 13.1 tiny repo\n", encoding="utf-8")
    return source


def _verifier_result(*, accepted: bool) -> VerifierResult:
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=1.0,
        command="python - <<'PY'\nprint('ok')\nPY",
        accepted=accepted,
        pass_ratio=1.0 if accepted else 0.0,
        fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
        pass_to_pass={"passed": 1, "total": 1},
        exit_code=0 if accepted else 1,
    )


def _real_runtime_options(tmp_path: Path, source: Path) -> RepoHarnessRuntimeOptions:
    def verifier_factory(context):
        def verify() -> VerifierResult:
            fixed_file = context.workspace_path / "fixed.txt"
            return _verifier_result(
                accepted=fixed_file.exists() and fixed_file.read_text(encoding="utf-8") == "done\n"
            )

        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=tmp_path / "runs_stage13_1",
        real_episode_source_resolver=lambda _request: source,
        real_episode_final_verifier_factory=verifier_factory,
        tool_observation_token_projector=lambda _content: [77_001, 77_002],
    )


def _tool_response(request: LLMGatewayRequest) -> LLMGatewayResponse:
    return LLMGatewayResponse(
        route=request.route,
        inference_backend=request.inference_backend,
        model_call_id=request.model_call_id,
        assistant_message={"role": "assistant", "content": "I will create the file."},
        tool_calls=[
            {
                "tool_call_id": "call_create_fixed",
                "tool_name": "create_file",
                "arguments": {"path": "fixed.txt", "content": "done\n"},
            }
        ],
        prompt_ids=[101],
        output_token_ids=[91_001],
        output_logprobs=[-0.11],
        response_mask=[1],
        stop_reason="tool_calls",
        usage={"input_tokens": 1, "output_tokens": 1},
        provider_request_id="provider-call-0",
    )


def _final_response(request: LLMGatewayRequest) -> LLMGatewayResponse:
    return LLMGatewayResponse(
        route=request.route,
        inference_backend=request.inference_backend,
        model_call_id=request.model_call_id,
        assistant_message={"role": "assistant", "content": "done"},
        prompt_ids=[102],
        output_token_ids=[92_001],
        output_logprobs=[-0.22],
        response_mask=[1],
        stop_reason="stop",
        usage={"input_tokens": 1, "output_tokens": 1},
        provider_request_id="provider-call-1",
    )


class FirstTurnBlockingGateway:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            self.started.set()
            await asyncio.to_thread(self.release.wait)
            return _tool_response(request)
        return _final_response(request)


def test_stage13_1_wait_result_timeout_does_not_cancel_underlying_episode() -> None:
    async def scenario() -> None:
        request = _episode_request()
        gateway = BlockingGateway()
        runtime = RepoHarnessRuntime()
        handle = await runtime.start_episode(request, llm_gateway=gateway)
        await asyncio.wait_for(gateway.started.wait(), timeout=1)

        try:
            await handle.wait_result(timeout=0.01)
        except asyncio.TimeoutError:
            pass
        else:  # pragma: no cover - defensive assertion.
            raise AssertionError("wait_result(timeout=...) must raise asyncio.TimeoutError")

        assert handle.status() in {"running", "cancelling", "cleanup_running"}
        gateway.release.set()
        result = await handle.wait_result(timeout=1)

        assert result.status == "succeeded"
        assert result.status_reason is None

    asyncio.run(scenario())


def test_stage13_1_cancel_returns_snapshot_without_waiting_for_cleanup() -> None:
    async def scenario() -> None:
        request = _episode_request()
        gateway = BlockingGateway()
        cleanup = BlockingCleanup()
        runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(cleanup_callback=cleanup))
        handle = await runtime.start_episode(request, llm_gateway=gateway)
        await asyncio.wait_for(gateway.started.wait(), timeout=1)

        snapshot = await asyncio.wait_for(handle.cancel(), timeout=0.1)

        assert snapshot.cancel_requested is True
        assert snapshot.async_status in {"cancelling", "cancelled"}
        await asyncio.wait_for(cleanup.started.wait(), timeout=1)
        assert cleanup.finished.is_set() is False

        cleanup.release.set()
        result = await handle.wait_result(timeout=1)

        assert result.status == "cancelled"
        assert cleanup.finished.is_set() is True
        terminal_snapshot = handle.snapshot()
        assert terminal_snapshot.final_audit_write_completed is True
        assert terminal_snapshot.run_directory_writer_active is False

    asyncio.run(scenario())


def test_stage13_1_immediate_cancel_still_returns_terminal_result_and_unregisters_run_id() -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage13-immediate-cancel-run")
        gateway = BlockingGateway()
        runtime = RepoHarnessRuntime()

        handle = await runtime.start_episode(request, llm_gateway=gateway)
        snapshot = await asyncio.wait_for(handle.cancel(), timeout=0.1)

        assert snapshot.cancel_requested is True
        result = await handle.wait_result(timeout=1)
        assert result.status == "cancelled"
        assert result.status_reason == "runtime_cancelled"
        assert gateway.requests == []

        retry_gateway = BlockingGateway()
        retry_handle = await runtime.start_episode(request, llm_gateway=retry_gateway)
        await asyncio.wait_for(retry_gateway.started.wait(), timeout=1)
        retry_gateway.release.set()
        retry_result = await retry_handle.wait_result(timeout=1)
        assert retry_result.status == "succeeded"

    asyncio.run(scenario())


def test_stage13_1_runtime_close_before_task_start_keeps_structured_result_and_unregisters() -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage13-close-before-start-run")
        gateway = BlockingGateway()
        runtime = RepoHarnessRuntime()

        handle = await runtime.start_episode(request, llm_gateway=gateway)
        runtime.close()

        result = await handle.wait_result(timeout=1)
        assert result.status == "cancelled"
        assert result.status_reason == "runtime_cancelled"
        assert gateway.requests == []

        retry_gateway = BlockingGateway()
        retry_handle = await runtime.start_episode(request, llm_gateway=retry_gateway)
        await asyncio.wait_for(retry_gateway.started.wait(), timeout=1)
        retry_gateway.release.set()
        retry_result = await retry_handle.wait_result(timeout=1)
        assert retry_result.status == "succeeded"

    asyncio.run(scenario())


def test_stage13_1_runtime_close_does_not_shutdown_real_episode_executor_before_workspace_release(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        source = _source_repo(tmp_path)
        request = _episode_request(run_id="stage13-close-real-episode-run")
        gateway = FirstTurnBlockingGateway()
        runtime = RepoHarnessRuntime(_real_runtime_options(tmp_path, source))

        handle = await runtime.start_episode(request, llm_gateway=gateway)
        assert await asyncio.to_thread(gateway.started.wait, 1.0)
        runtime.close()
        gateway.release.set()

        result = await handle.wait_result(timeout=3)
        assert result.status == "cancelled"
        assert result.status_reason == "runtime_cancelled"
        assert result.resource_summary is not None
        assert result.resource_summary.cleanup_status != "failed"
        assert not any(
            diagnostic.code == "workspace_lease_release_failed"
            for diagnostic in result.audit_diagnostics
        )

    asyncio.run(scenario())
