from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import (
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
    formal_async_online_rl_sample_from_episode_result,
    formal_online_rl_sample_from_training_view,
    validate_formal_async_online_rl_batch,
    validate_formal_online_rl_batch,
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


def _source_repo(tmp_path: Path) -> Path:
    source = tmp_path / "source_repo"
    source.mkdir()
    (source / "README.md").write_text("stage 14.3 tiny repo\n", encoding="utf-8")
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


def _runtime_options(
    tmp_path: Path,
    source: Path,
    *,
    verifier_started: threading.Event | None = None,
) -> RepoHarnessRuntimeOptions:
    def verifier_factory(context):
        def verify() -> VerifierResult:
            if verifier_started is not None:
                verifier_started.set()
            fixed_file = context.workspace_path / "fixed.txt"
            return _verifier_result(
                accepted=fixed_file.exists() and fixed_file.read_text(encoding="utf-8") == "done\n"
            )

        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=tmp_path / "runs",
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
        assistant_message={"role": "assistant", "content": "Final answer."},
        tool_calls=[],
        prompt_ids=[102],
        output_token_ids=[92_001],
        output_logprobs=[-0.22],
        response_mask=[1],
        stop_reason="stop",
        usage={"input_tokens": 1, "output_tokens": 1},
        provider_request_id="provider-call-1",
    )


class BlockingFirstTurnGateway:
    def __init__(self, *, final_only: bool = False) -> None:
        self.requests: list[LLMGatewayRequest] = []
        self.first_started = asyncio.Event()
        self.release_first = asyncio.Event()
        self.final_only = final_only

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            self.first_started.set()
            await self.release_first.wait()
            return _final_response(request) if self.final_only else _tool_response(request)
        return _final_response(request)


def test_stage14_3_pauses_at_tool_boundary_and_resumes_to_terminal_result(tmp_path: Path) -> None:
    async def scenario() -> None:
        source = _source_repo(tmp_path)
        request = _episode_request()
        runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
        gateway = BlockingFirstTurnGateway()
        handle = await runtime.start_episode(request, llm_gateway=gateway)

        await asyncio.wait_for(gateway.first_started.wait(), timeout=1)
        pause_task = asyncio.create_task(
            handle.request_pause_at_next_turn_boundary(reason="test_pause", timeout=2)
        )
        gateway.release_first.set()
        pause_outcome = await pause_task

        assert pause_outcome.status == "paused"
        assert pause_outcome.checkpoint is not None
        assert pause_outcome.checkpoint.checkpoint_status == "partial"
        assert pause_outcome.checkpoint.writer_state.run_directory_writer_active is True
        assert pause_outcome.checkpoint.writer_state.verifier_may_still_write is False
        assert pause_outcome.checkpoint.reward_finality.reward_state == "not_started"
        assert pause_outcome.checkpoint.tool_pairing.tool_pairing_status == "closed"
        assert pause_outcome.checkpoint.tool_pairing.completed_tool_call_ids == [
            "call_create_fixed"
        ]
        assert pause_outcome.checkpoint.tool_pairing.tool_result_refs == {
            "call_create_fixed": f"rh://tool-results/{request.run_id}/call_create_fixed_result"
        }
        assert pause_outcome.checkpoint.tool_pairing.observation_token_projection_digest is not None
        assert pause_outcome.checkpoint.token_provenance.response_ids == [91_001, 77_001, 77_002]
        assert pause_outcome.checkpoint.token_provenance.response_mask == [1, 0, 0]
        assert pause_outcome.checkpoint.token_provenance.response_logprobs == [-0.11, 0.0, 0.0]

        snapshot = handle.snapshot()
        assert snapshot.async_status == "paused"
        assert snapshot.resume.resume_supported is True
        assert snapshot.run_directory_writer_active is True
        assert snapshot.workspace_lease_safely_released is False
        assert snapshot.final_audit_write_completed is False
        with pytest.raises(asyncio.TimeoutError):
            await handle.wait_result(timeout=0.05)

        tampered_checkpoint = pause_outcome.checkpoint.model_copy(update={"run_id": "forged-run-id"})
        tampered_resume = await handle.resume(tampered_checkpoint)
        assert tampered_resume.status == "checkpoint_mismatch"

        resume_outcome = await handle.resume(pause_outcome.checkpoint)
        assert resume_outcome.status == "resumed"
        result = await handle.wait_result(timeout=2)

        assert result.status == "succeeded"
        assert result.training_view.response_ids == [91_001, 77_001, 77_002, 92_001]
        formal_sample = formal_online_rl_sample_from_training_view(
            result.training_view,
            generation_records=result.generation_records,
            sample_id=result.episode_id,
            invalid_for_training=result.invalid_for_training,
            invalid_for_online_rl=result.invalid_for_online_rl,
            invalid_reason=result.status_reason,
        )
        validate_formal_online_rl_batch([formal_sample])
        async_sample = formal_async_online_rl_sample_from_episode_result(
            result,
            visibility_scan_status="passed",
            visibility_scan_digest="sha256:" + "a" * 64,
        )
        validate_formal_async_online_rl_batch([async_sample])
        terminal_snapshot = handle.snapshot()
        assert terminal_snapshot.async_status == "completed"
        assert terminal_snapshot.run_directory_writer_active is False
        assert terminal_snapshot.final_audit_write_completed is True

    asyncio.run(scenario())


def test_stage14_3_pause_timeout_keeps_request_until_boundary(tmp_path: Path) -> None:
    async def scenario() -> None:
        source = _source_repo(tmp_path)
        request = _episode_request(run_id="stage14-3-pause-timeout-run")
        runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
        gateway = BlockingFirstTurnGateway()
        handle = await runtime.start_episode(request, llm_gateway=gateway)

        await asyncio.wait_for(gateway.first_started.wait(), timeout=1)
        timeout_outcome = await handle.request_pause_at_next_turn_boundary(
            reason="slow_boundary",
            timeout=0.01,
        )
        assert timeout_outcome.status == "pause_timeout"

        pause_task = asyncio.create_task(handle.request_pause_at_next_turn_boundary(timeout=2))
        gateway.release_first.set()
        pause_outcome = await pause_task
        assert pause_outcome.status == "paused"

        await handle.resume(pause_outcome.checkpoint)
        result = await handle.wait_result(timeout=2)
        assert result.status == "succeeded"

    asyncio.run(scenario())


def test_stage14_3_rejects_schema_valid_checkpoint_without_runtime_store_entry(tmp_path: Path) -> None:
    async def scenario() -> None:
        source = _source_repo(tmp_path)
        request = _episode_request(run_id="stage14-3-missing-store-run")
        runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
        gateway = BlockingFirstTurnGateway()
        handle = await runtime.start_episode(request, llm_gateway=gateway)

        await asyncio.wait_for(gateway.first_started.wait(), timeout=1)
        pause_task = asyncio.create_task(handle.request_pause_at_next_turn_boundary(timeout=2))
        gateway.release_first.set()
        pause_outcome = await pause_task
        assert pause_outcome.checkpoint is not None

        assert handle._state.pause_controller is not None
        handle._state.pause_controller.resume_state_store.clear()
        resume_outcome = await handle.resume(pause_outcome.checkpoint)
        assert resume_outcome.status == "unsupported_cross_process_resume_in_stage14_3"

        await handle.cancel("test_cleanup_after_rejected_resume")
        result = await handle.wait_result(timeout=2)
        assert result.status == "cancelled"
        run_status = json.loads(
            (tmp_path / "runs" / request.run_id / "run_status.json").read_text(encoding="utf-8")
        )
        assert run_status["status"] == "FINALIZED"

    asyncio.run(scenario())


def test_stage14_3_can_pause_final_answer_before_final_verifier(tmp_path: Path) -> None:
    async def scenario() -> None:
        source = _source_repo(tmp_path)
        verifier_started = threading.Event()
        request = _episode_request(run_id="stage14-3-final-boundary-run")
        runtime = RepoHarnessRuntime(
            _runtime_options(tmp_path, source, verifier_started=verifier_started)
        )
        gateway = BlockingFirstTurnGateway(final_only=True)
        handle = await runtime.start_episode(request, llm_gateway=gateway)

        await asyncio.wait_for(gateway.first_started.wait(), timeout=1)
        pause_task = asyncio.create_task(handle.request_pause_at_next_turn_boundary(timeout=2))
        gateway.release_first.set()
        pause_outcome = await pause_task

        assert pause_outcome.status == "paused"
        assert pause_outcome.checkpoint is not None
        assert pause_outcome.checkpoint.batch_safe_projection["repo_harness_pause_boundary_kind"] == (
            "final_answer_before_verifier"
        )
        assert verifier_started.is_set() is False

        await handle.resume(pause_outcome.checkpoint)
        result = await handle.wait_result(timeout=2)
        assert verifier_started.is_set() is True
        assert result.status == "failed"

    asyncio.run(scenario())
