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
    RepoHarnessRuntimeOptions,
)
from repo_harness.rl.async_runtime import AsyncEpisodeStartError
from repo_harness_verl.fully_async_bridge import build_queue_facts_from_episode_result
from repo_harness.verifier import VerifierResult
from repo_harness_verl.fully_async_bridge import queue_facts_from_rollout_sample
from repo_harness_verl.fully_async_runtime import (
    InMemoryFullyAsyncMessageQueueClient,
    select_valid_samples_from_message_queue,
)
from repo_harness_verl.partial_rollout import (
    DEFAULT_STAGE15_VISIBILITY_DIGEST,
    InMemoryPartialDiagnosticChannel,
    InMemoryPartialResumeQueue,
    PartialResumeQueueEntry,
    RepoHarnessPartialRolloutProducer,
    RepoHarnessResumeScheduler,
    runtime_scope_id,
)
from repo_harness_verl.visibility import (
    validate_agent_loop_output_extra_fields,
    validate_dataproto_visibility,
    validate_transfer_queue_field_visibility,
)


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
    source.mkdir(parents=True)
    (source / "README.md").write_text("stage 15.1 tiny repo\n", encoding="utf-8")
    return source


def _runtime_options(tmp_path: Path, source: Path) -> RepoHarnessRuntimeOptions:
    def verifier_factory(context):
        def verify() -> VerifierResult:
            fixed_file = context.workspace_path / "fixed.txt"
            accepted = fixed_file.exists() and fixed_file.read_text(encoding="utf-8") == "done\n"
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
    def __init__(self) -> None:
        self.requests: list[LLMGatewayRequest] = []
        self.first_started = asyncio.Event()
        self.release_first = asyncio.Event()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            self.first_started.set()
            await self.release_first.wait()
            return _tool_response(request)
        return _final_response(request)


class BlockingSecondTurnGateway(BlockingFirstTurnGateway):
    def __init__(self) -> None:
        super().__init__()
        self.second_started = asyncio.Event()
        self.release_second = asyncio.Event()

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            self.first_started.set()
            await self.release_first.wait()
            return _tool_response(request)
        self.second_started.set()
        await self.release_second.wait()
        return _final_response(request)


async def _produce_partial(
    *,
    tmp_path: Path,
    request: RepoHarnessEpisodeRequest,
    gateway: BlockingFirstTurnGateway,
) -> tuple[RepoHarnessRuntime, InMemoryPartialResumeQueue, InMemoryPartialDiagnosticChannel, Any]:
    source = _source_repo(tmp_path)
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
    resume_queue = InMemoryPartialResumeQueue()
    diagnostics = InMemoryPartialDiagnosticChannel()
    producer = RepoHarnessPartialRolloutProducer(
        runtime=runtime,
        resume_queue=resume_queue,
        diagnostic_channel=diagnostics,
        config={"pause_wait_timeout_seconds": 2.0},
    )
    task = asyncio.create_task(producer.produce_one(request, llm_gateway=gateway))
    await asyncio.wait_for(gateway.first_started.wait(), timeout=1)
    gateway.release_first.set()
    report = await asyncio.wait_for(task, timeout=2)
    return runtime, resume_queue, diagnostics, report


def test_stage15_1_partial_checkpoint_goes_to_resume_queue_not_policy_loss(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-producer-run")
        gateway = BlockingFirstTurnGateway()
        _runtime, resume_queue, _diagnostics, report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )

        assert report.paused_checkpoint_count == 1
        assert report.enqueued_resume_candidate_count == 1
        assert report.policy_loss_enqueued_count == 0
        assert await resume_queue.qsize() == 1
        entry = await resume_queue.get(timeout=0.1)
        assert entry is not None
        assert entry.facts.valid_for_policy_loss is False
        assert entry.facts.partial_rollout_status == "paused_same_process_stage15_1"
        with pytest.raises(Exception):
            validate_transfer_queue_field_visibility(
                {"repo_harness_partial_checkpoint": entry.checkpoint.model_dump(mode="json")}
            )
        await entry.handle.cancel("test_cleanup")
        result = await entry.handle.wait_result(timeout=2)
        assert result.status == "cancelled"

    asyncio.run(scenario())


def test_stage15_1_resume_scheduler_enqueues_only_terminal_valid_sample(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-resume-run")
        gateway = BlockingFirstTurnGateway()
        runtime, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        policy_queue = InMemoryFullyAsyncMessageQueueClient()
        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime,
            resume_queue=resume_queue,
            policy_loss_queue=policy_queue,
            diagnostic_channel=diagnostics,
            config={"resume_wait_timeout_seconds": 2.0},
        )

        resume_report = await scheduler.resume_available(max_items=1)

        assert resume_report.resume_attempt_count == 1
        assert resume_report.resumed_terminal_episode_count == 1
        assert resume_report.resumed_valid_sample_count == 1
        assert resume_report.policy_loss_enqueued_count == 1
        selected, selection_report = await select_valid_samples_from_message_queue(
            policy_queue,
            required_samples=1,
        )
        assert selection_report.valid_sample_count == 1
        facts = queue_facts_from_rollout_sample(selected[0])
        assert facts.valid_for_policy_loss is True
        assert facts.partial_rollout_supported is True
        assert facts.partial_rollout_status == "complete"

    asyncio.run(scenario())


def test_stage15_1_scheduler_rejects_missing_resume_state_store_entry(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-missing-store-run")
        gateway = BlockingFirstTurnGateway()
        runtime, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        entry = await resume_queue.get(timeout=0.1)
        assert entry is not None
        assert entry.handle._state.pause_controller is not None
        entry.handle._state.pause_controller.resume_state_store.clear()
        await resume_queue.put(entry)

        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime,
            resume_queue=resume_queue,
            policy_loss_queue=InMemoryFullyAsyncMessageQueueClient(),
            diagnostic_channel=diagnostics,
        )
        resume_report = await scheduler.resume_available(max_items=1)

        assert resume_report.policy_loss_enqueued_count == 0
        assert resume_report.missing_resume_state_rejected_count == 1
        assert "unsupported_cross_process_resume_in_stage14_3" in next(
            iter(resume_report.diagnostics.values())
        )
        await entry.handle.cancel("test_cleanup_missing_store")
        result = await entry.handle.wait_result(timeout=2)
        assert result.status == "cancelled"

    asyncio.run(scenario())


def test_stage15_1_resume_timeout_cancels_and_does_not_enter_policy_loss(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-resume-timeout-run")
        gateway = BlockingSecondTurnGateway()
        runtime, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        policy_queue = InMemoryFullyAsyncMessageQueueClient()
        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime,
            resume_queue=resume_queue,
            policy_loss_queue=policy_queue,
            diagnostic_channel=diagnostics,
            config={"resume_wait_timeout_seconds": 0.05, "resume_cancel_wait_timeout_seconds": 1.0},
        )

        resume_report = await scheduler.resume_available(max_items=1)

        assert resume_report.resume_timeout_count == 1
        assert resume_report.policy_loss_enqueued_count == 0
        assert resume_report.active_handle_retained_count == 1
        assert request.run_id in scheduler.retained_active_handles
        assert await policy_queue.get_queue_size() == 0

    asyncio.run(scenario())


def test_stage15_1_resume_scheduler_cancellation_records_or_releases_active_handle(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-resume-cancelled-run")
        gateway = BlockingSecondTurnGateway()
        runtime, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        policy_queue = InMemoryFullyAsyncMessageQueueClient()
        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime,
            resume_queue=resume_queue,
            policy_loss_queue=policy_queue,
            diagnostic_channel=diagnostics,
            config={"resume_wait_timeout_seconds": 10.0, "resume_cancel_wait_timeout_seconds": 1.0},
        )
        scheduler_task = asyncio.create_task(scheduler.resume_available(max_items=1))
        await asyncio.wait_for(gateway.second_started.wait(), timeout=1)

        scheduler_task.cancel()
        report = await asyncio.wait_for(scheduler_task, timeout=2)

        assert report.resume_cancelled_count == 1
        assert report.policy_loss_enqueued_count == 0
        assert await policy_queue.get_queue_size() == 0
        assert request.run_id in scheduler.retained_active_handles or report.active_handle_retained_count == 0

    asyncio.run(scenario())


def test_stage15_1_pause_timeout_cancels_without_delayed_checkpoint(tmp_path: Path) -> None:
    async def scenario() -> None:
        source = _source_repo(tmp_path)
        request = _episode_request(run_id="stage15-1-pause-timeout-run")
        runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
        gateway = BlockingFirstTurnGateway()
        resume_queue = InMemoryPartialResumeQueue()
        producer = RepoHarnessPartialRolloutProducer(
            runtime=runtime,
            resume_queue=resume_queue,
            config={"pause_wait_timeout_seconds": 0.01, "pause_cancel_wait_timeout_seconds": 1.0},
        )
        task = asyncio.create_task(producer.produce_one(request, llm_gateway=gateway))
        await asyncio.wait_for(gateway.first_started.wait(), timeout=1)
        report = await asyncio.wait_for(task, timeout=2)

        assert report.pause_timeout_count == 1
        assert report.active_handle_retained_count == 1
        assert request.run_id in producer.retained_active_handles
        assert await resume_queue.qsize() == 0
        retry_gateway = BlockingFirstTurnGateway()
        with pytest.raises(AsyncEpisodeStartError):
            await runtime.start_episode(request, llm_gateway=retry_gateway)

    asyncio.run(scenario())


def test_stage15_1_scheduler_filters_stale_resumed_terminal_sample(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-stale-run")
        gateway = BlockingFirstTurnGateway()
        runtime, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        policy_queue = InMemoryFullyAsyncMessageQueueClient()
        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime,
            resume_queue=resume_queue,
            policy_loss_queue=policy_queue,
            diagnostic_channel=diagnostics,
            config={"current_global_steps": 10, "staleness_threshold": 0},
        )

        resume_report = await scheduler.resume_available(max_items=1)

        assert resume_report.resumed_terminal_episode_count == 1
        assert resume_report.stale_rejected_count == 1
        assert resume_report.policy_loss_enqueued_count == 0
        assert await policy_queue.get_queue_size() == 0

    asyncio.run(scenario())


def test_stage15_1_scheduler_rejects_tampered_resume_queue_facts(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-tamper-run")
        gateway = BlockingFirstTurnGateway()
        runtime, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        entry = await resume_queue.get(timeout=0.1)
        assert entry is not None
        tampered = PartialResumeQueueEntry(
            facts=entry.facts.model_copy(update={"run_id": "forged-run-id"}),
            checkpoint=entry.checkpoint,
            handle=entry.handle,
        )
        await resume_queue.put(tampered)
        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime,
            resume_queue=resume_queue,
            policy_loss_queue=InMemoryFullyAsyncMessageQueueClient(),
            diagnostic_channel=diagnostics,
        )

        resume_report = await scheduler.resume_available(max_items=1)

        assert resume_report.policy_loss_enqueued_count == 0
        assert "partial_resume_queue_facts_mismatch" in next(iter(resume_report.diagnostics.values()))
        await entry.handle.cancel("test_cleanup_tamper")
        result = await entry.handle.wait_result(timeout=2)
        assert result.status == "cancelled"

    asyncio.run(scenario())


def test_stage15_1_scheduler_rejects_handle_from_other_runtime_even_if_facts_claim_current_scope(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-cross-runtime-run")
        gateway = BlockingFirstTurnGateway()
        runtime_a, resume_queue, diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path / "a",
            request=request,
            gateway=gateway,
        )
        runtime_b = RepoHarnessRuntime(_runtime_options(tmp_path / "b", _source_repo(tmp_path / "b")))
        entry = await resume_queue.get(timeout=0.1)
        assert entry is not None
        tampered = PartialResumeQueueEntry(
            facts=entry.facts.model_copy(update={"runtime_scope_id": runtime_scope_id(runtime_b)}),
            checkpoint=entry.checkpoint,
            handle=entry.handle,
        )
        await resume_queue.put(tampered)
        scheduler = RepoHarnessResumeScheduler(
            runtime=runtime_b,
            resume_queue=resume_queue,
            policy_loss_queue=InMemoryFullyAsyncMessageQueueClient(),
            diagnostic_channel=diagnostics,
        )

        resume_report = await scheduler.resume_available(max_items=1)

        assert resume_report.policy_loss_enqueued_count == 0
        assert resume_report.missing_live_handle_rejected_count == 1
        assert "runtime_scope_mismatch_or_missing_live_handle" in next(
            iter(resume_report.diagnostics.values())
        )
        assert await runtime_a.owns_async_episode_handle(entry.handle) is True
        await entry.handle.cancel("test_cleanup_cross_runtime")
        result = await entry.handle.wait_result(timeout=2)
        assert result.status == "cancelled"

    asyncio.run(scenario())


def test_stage15_1_partial_status_never_counts_as_policy_loss_terminal_sample(tmp_path: Path) -> None:
    async def scenario() -> None:
        request = _episode_request(run_id="stage15-1-partial-status-gate-run")
        gateway = BlockingFirstTurnGateway()
        _runtime, resume_queue, _diagnostics, _report = await _produce_partial(
            tmp_path=tmp_path,
            request=request,
            gateway=gateway,
        )
        entry = await resume_queue.get(timeout=0.1)
        assert entry is not None
        resume_outcome = await entry.handle.resume(entry.checkpoint)
        assert resume_outcome.status == "resumed"
        result = await entry.handle.wait_result(timeout=2)

        facts = build_queue_facts_from_episode_result(
            result,
            visibility_scan_status="passed",
            visibility_scan_digest=DEFAULT_STAGE15_VISIBILITY_DIGEST,
            current_global_steps=0,
            partial_rollout_supported=True,
            partial_rollout_status="paused_same_process_stage15_1",
        )

        assert facts.valid_for_policy_loss is False
        assert facts.rejection_reason == "partial_rollout_not_complete"

    asyncio.run(scenario())


def test_stage15_1_transfer_queue_visibility_rejects_runtime_private_refs() -> None:
    forbidden_fields = [
        {"repo_harness_handle_ref": "rh://async/episode/attempt-0"},
        {"repo_harness_partial_checkpoint_ref": "rh://partial-checkpoints/checkpoint-1"},
        {"repo_harness_resume_token": "resume-token-secret"},
        {"repo_harness_recorder_cursor_ref": "rh://recorder-cursors/run-1/cursor"},
        {"repo_harness_workspace_lease_ref": "rh://workspace-leases/lease-1"},
    ]
    for field in forbidden_fields:
        with pytest.raises(Exception):
            validate_transfer_queue_field_visibility(field)


def test_stage15_1_visibility_rejects_runtime_private_refs_across_verl_boundaries() -> None:
    class DataProto:
        def __init__(self) -> None:
            self.non_tensor_batch: dict[str, object] = {}
            self.meta_info: dict[str, object] = {}

    transfer_fields = [
        {"handle_ref": "rh://async/episode/attempt-0"},
        {"partial_checkpoint_ref": "rh://partial-checkpoints/checkpoint-1"},
        {"safe_ref": "rh://runtime-private/writer-lease-0"},
        {"safe_ref": "rh://workspace-leases/lease-1"},
        {"safe_ref": "rh://recorder-cursors/run-1/cursor"},
    ]
    for field in transfer_fields:
        with pytest.raises(Exception):
            validate_transfer_queue_field_visibility(field)

    with pytest.raises(Exception):
        validate_agent_loop_output_extra_fields(
            {"repo_harness_handle_ref": "rh://async/episode/attempt-0"}
        )

    data_proto = DataProto()
    data_proto.non_tensor_batch["handle_ref"] = ["rh://async/episode/attempt-0"]
    with pytest.raises(Exception):
        validate_dataproto_visibility(data_proto)

    data_proto = DataProto()
    data_proto.non_tensor_batch["safe_ref"] = ["rh://workspace-leases/lease-1"]
    with pytest.raises(Exception):
        validate_dataproto_visibility(data_proto)

    data_proto = DataProto()
    data_proto.meta_info["repo_harness_handle_ref"] = "rh://async/episode/attempt-0"
    with pytest.raises(Exception):
        validate_dataproto_visibility(data_proto)
