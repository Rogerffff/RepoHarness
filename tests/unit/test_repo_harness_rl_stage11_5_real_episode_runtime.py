import asyncio
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessEpisodeResult,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
    ResourceConcurrencyPolicy,
    ResourceLeaseManager,
    validate_training_view_for_online_rl,
)
from repo_harness.rl.gateway import LLMGatewayRequest
from repo_harness.verifier import VerifierResult


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
DEFAULT_LOGPROBS = object()


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
    (source / "README.md").write_text("stage 11.5 tiny repo\n", encoding="utf-8")
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
    route: str = "verl",
    resource_lease_manager: ResourceLeaseManager | None = None,
    tool_observation_token_projector=True,
    real_episode_final_verifier_factory=None,
) -> RepoHarnessRuntimeOptions:
    def verifier_factory(context):
        def verify() -> VerifierResult:
            fixed_file = context.workspace_path / "fixed.txt"
            return _verifier_result(
                accepted=fixed_file.exists() and fixed_file.read_text(encoding="utf-8") == "done\n"
            )

        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=tmp_path / f"runs_{route}",
        real_episode_source_resolver=lambda _request: source,
        real_episode_final_verifier_factory=real_episode_final_verifier_factory or verifier_factory,
        resource_lease_manager=resource_lease_manager,
        tool_observation_token_projector=(
            (lambda _content: [77_001, 77_002])
            if tool_observation_token_projector is True
            else tool_observation_token_projector
        ),
    )


def _tool_response(
    *,
    route: str = "verl",
    inference_backend: str | None = "sglang",
    output_logprobs: list[float] | None | object = DEFAULT_LOGPROBS,
) -> LLMGatewayResponse:
    logprobs = [-0.11] if output_logprobs is DEFAULT_LOGPROBS else output_logprobs
    return LLMGatewayResponse(
        route=route,  # type: ignore[arg-type]
        inference_backend=inference_backend,  # type: ignore[arg-type]
        model_call_id="stage11-5-call-0",
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
        output_logprobs=logprobs,  # type: ignore[arg-type]
        response_mask=[1],
        stop_reason="tool_calls",
        usage={"input_tokens": 1, "output_tokens": 1},
        provider_request_id="provider-call-0",
    )


def _final_response(
    *,
    route: str = "verl",
    inference_backend: str | None = "sglang",
    output_logprobs: list[float] | None | object = DEFAULT_LOGPROBS,
) -> LLMGatewayResponse:
    logprobs = [-0.22] if output_logprobs is DEFAULT_LOGPROBS else output_logprobs
    return LLMGatewayResponse(
        route=route,  # type: ignore[arg-type]
        inference_backend=inference_backend,  # type: ignore[arg-type]
        model_call_id="stage11-5-call-1",
        assistant_message={
            "role": "assistant",
            "content": "Final answer text is intentionally unrelated to token ids.",
        },
        tool_calls=[],
        prompt_ids=[102],
        output_token_ids=[92_001],
        output_logprobs=logprobs,  # type: ignore[arg-type]
        response_mask=[1],
        stop_reason="stop",
        usage={"input_tokens": 1, "output_tokens": 1},
        provider_request_id="provider-call-1",
    )


def test_stage11_5_real_episode_runs_agent_loop_and_builds_training_view_from_collector(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is False
    assert len(gateway.requests) == 2
    assert result.generation_records[0].output_token_ids == [91_001]
    assert result.generation_records[1].output_token_ids == [92_001]
    assert result.training_view.response_ids == [91_001, 77_001, 77_002, 92_001]
    assert result.training_view.response_mask == [1, 0, 0, 1]
    assert result.training_view.response_logprobs == [-0.11, 0.0, 0.0, -0.22]
    assert [span.source_type for span in result.training_view.response_spans] == [
        "assistant_generation",
        "tool_observation",
        "assistant_generation",
    ]
    assert result.training_view.reward_score is not None
    validate_training_view_for_online_rl(result.training_view, require_explicit_eligibility=True)
    assert result.resource_summary is not None
    assert result.resource_summary.execution_mode == "real_episode"
    assert result.resource_summary.workspace_backend == "local_process"
    assert "/Users/" not in json.dumps(result.training_view.extra_fields, sort_keys=True)
    artifact_manifest = json.loads(
        (tmp_path / "runs_verl" / request.run_id / "artifacts.json").read_text(encoding="utf-8")
    )
    artifact_kinds = {artifact["kind"] for artifact in artifact_manifest["artifacts"]}
    assert "final_verifier" in artifact_kinds
    assert "reward_metadata" in artifact_kinds
    run_status = json.loads(
        (tmp_path / "runs_verl" / request.run_id / "run_status.json").read_text(encoding="utf-8")
    )
    assert run_status["status"] == "FINALIZED"
    summary = (tmp_path / "runs_verl" / request.run_id / "summary.md").read_text(encoding="utf-8")
    assert "runtime_execution_mode: real_episode" in summary
    assert "status: succeeded" in summary


def test_stage11_5_real_episode_success_with_mock_route_is_diagnostic_only(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request(llm_gateway_route="mock", inference_backend=None)
    gateway = FakeLLMGateway(
        [
            _tool_response(route="mock", inference_backend=None),
            _final_response(route="mock", inference_backend=None),
        ]
    )
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source, route="mock"))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "non_verl_route_invalid_for_online_rl"
    assert result.training_view.reward_score is not None
    with pytest.raises(ValueError, match="non_verl_route_invalid_for_online_rl"):
        validate_training_view_for_online_rl(result.training_view, require_explicit_eligibility=True)


def test_stage11_5_real_episode_rejected_verifier_finalizes_run_status(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)

    def verifier_factory(_context):
        def verify() -> VerifierResult:
            return _verifier_result(accepted=False)

        return verify

    request = _episode_request()
    gateway = FakeLLMGateway([_final_response()])
    runtime = RepoHarnessRuntime(
        _runtime_options(
            tmp_path,
            source,
            real_episode_final_verifier_factory=verifier_factory,
        )
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "failed"
    run_dir = tmp_path / "runs_verl" / request.run_id
    run_status = json.loads((run_dir / "run_status.json").read_text(encoding="utf-8"))
    assert run_status["status"] == "FINALIZED"
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "status: failed" in summary


def test_stage11_5_real_episode_missing_logprobs_is_rejected_by_formal_gate(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response(output_logprobs=None)])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "missing_response_logprobs"
    assert result.training_view.response_logprobs is None
    with pytest.raises(ValueError, match="missing_response_logprobs_in_formal_batch"):
        validate_training_view_for_online_rl(result.training_view, require_explicit_eligibility=True)


def test_stage11_5_real_episode_diagnostic_route_can_exceed_rollout_length_without_crash(
    tmp_path: Path,
) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request(
        llm_gateway_route="mock",
        inference_backend=None,
        budgets={**_episode_request().budgets.model_dump(mode="json"), "max_output_tokens": 2},
    )
    long_response = _final_response(
        route="mock",
        inference_backend=None,
        output_logprobs=None,
    ).model_copy(update={"output_token_ids": [92_001, 92_002, 92_003]})
    gateway = FakeLLMGateway([long_response])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source, route="mock"))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status in {"failed", "succeeded"}
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert len(result.training_view.response_ids) > 2
    assert result.training_view.rollout_limits.response_length == len(result.training_view.response_ids)


def test_stage11_5_real_episode_response_route_mismatch_is_structured_invalid_result(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_final_response(route="openai", inference_backend=None)])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "infrastructure_error"
    assert result.status_reason == "gateway_route_mismatch"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.training_view.extra_fields["repo_harness_llm_gateway_route"] == "openai"
    assert result.training_view.extra_fields["repo_harness_requested_llm_gateway_route"] == "verl"


def test_stage11_5_real_episode_gateway_error_maps_to_episode_status(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    error_response = _final_response()
    error_response = error_response.model_copy(update={"error": {"error_type": "provider_timeout"}})
    gateway = FakeLLMGateway([error_response])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "timeout"
    assert result.status_reason == "provider_timeout"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True


def test_stage11_5_real_episode_response_overflow_is_structured_invalid(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request(
        budgets={**_episode_request().budgets.model_dump(mode="json"), "max_output_tokens": 2}
    )
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "invalid"
    assert result.status_reason == "response_length_exceeded"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.budget_consumption is not None
    assert result.budget_consumption.actual_response_length == 4


def test_stage11_5_real_episode_prompt_overflow_is_structured_invalid(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request(
        budgets={**_episode_request().budgets.model_dump(mode="json"), "max_prompt_tokens": 1}
    )
    prompt_overflow_response = _final_response().model_copy(update={"prompt_ids": [101, 102]})
    gateway = FakeLLMGateway([prompt_overflow_response])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "invalid"
    assert result.status_reason == "prompt_length_exceeded"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True


def test_stage11_5_real_episode_multiturn_mixed_route_returns_structured_result(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response(route="openai", inference_backend=None)])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "infrastructure_error"
    assert result.status_reason == "gateway_route_mismatch"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.training_view.extra_fields["repo_harness_llm_gateway_route"] == "mixed"


def test_stage11_5_episode_schema_rejects_mixed_generation_routes_without_explicit_route(
    tmp_path: Path,
) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
    valid_result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))
    payload = valid_result.model_dump(mode="json")
    payload["training_view"]["extra_fields"].pop("repo_harness_llm_gateway_route")
    payload["generation_records"][1]["gateway_route"] = "openai"
    payload["generation_records"][1]["inference_backend"] = None

    with pytest.raises(ValueError, match="generation_records_invalid_for_online_rl"):
        RepoHarnessEpisodeResult.model_validate(payload)


def test_stage11_5_episode_schema_rejects_forged_training_view_tokens(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
    valid_result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))
    payload = valid_result.model_dump(mode="json")
    payload["training_view"]["response_ids"][0] = 999

    with pytest.raises(ValueError, match="assistant_generation_tokens_mismatch_generation_records"):
        RepoHarnessEpisodeResult.model_validate(payload)


def test_stage11_5_episode_schema_rejects_duplicate_assistant_generation_span(
    tmp_path: Path,
) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
    valid_result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))
    payload = valid_result.model_dump(mode="json")
    duplicate_tokens = list(payload["generation_records"][0]["output_token_ids"])
    duplicate_logprobs = list(payload["generation_records"][0]["output_logprobs"])
    insert_at = len(payload["training_view"]["response_ids"])
    payload["training_view"]["response_ids"].extend(duplicate_tokens)
    payload["training_view"]["response_mask"].extend([1 for _ in duplicate_tokens])
    payload["training_view"]["response_logprobs"].extend(duplicate_logprobs)
    payload["training_view"]["response_spans"].append(
        {
            **payload["training_view"]["response_spans"][0],
            "start": insert_at,
            "end": insert_at + len(duplicate_tokens),
        }
    )

    with pytest.raises(ValueError, match="assistant_generation_span_count_mismatch_generation_records"):
        RepoHarnessEpisodeResult.model_validate(payload)


def test_stage11_5_episode_schema_rejects_reordered_assistant_generation_spans(
    tmp_path: Path,
) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
    valid_result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))
    payload = valid_result.model_dump(mode="json")
    assistant_spans = [
        span
        for span in payload["training_view"]["response_spans"]
        if span["source_type"] == "assistant_generation"
    ]
    first_span, second_span = assistant_spans
    first_ids = payload["generation_records"][0]["output_token_ids"]
    second_ids = payload["generation_records"][1]["output_token_ids"]
    first_logprobs = payload["generation_records"][0]["output_logprobs"]
    second_logprobs = payload["generation_records"][1]["output_logprobs"]
    payload["training_view"]["response_ids"] = second_ids + first_ids
    payload["training_view"]["response_mask"] = [1 for _ in payload["training_view"]["response_ids"]]
    payload["training_view"]["response_logprobs"] = second_logprobs + first_logprobs
    payload["training_view"]["response_spans"] = [
        {**second_span, "start": 0, "end": len(second_ids)},
        {**first_span, "start": len(second_ids), "end": len(second_ids) + len(first_ids)},
    ]

    with pytest.raises(ValueError, match="assistant_generation_span_order_mismatch_generation_records"):
        RepoHarnessEpisodeResult.model_validate(payload)


def test_stage11_5_real_episode_default_tool_observation_projector_is_diagnostic_only(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    request = _episode_request()
    gateway = FakeLLMGateway([_tool_response(), _final_response()])
    runtime = RepoHarnessRuntime(
        _runtime_options(tmp_path, source, tool_observation_token_projector=None)
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "tool_observation_tokenizer_unavailable"
    with pytest.raises(ValueError, match="ineligible_for_online_rl"):
        validate_training_view_for_online_rl(result.training_view, require_explicit_eligibility=True)


class BlockingGateway:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        self.started.set()
        await asyncio.to_thread(self.release.wait)
        return _final_response()


def test_stage11_5_real_episode_timeout_holds_leases_until_agent_thread_finishes(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    resource_manager = ResourceLeaseManager(
        ResourceConcurrencyPolicy(max_concurrent_episodes=2, max_workspace_leases=2)
    )
    request = _episode_request(
        budgets={**_episode_request().budgets.model_dump(mode="json"), "max_wall_seconds": 0.01}
    )
    blocking_gateway = BlockingGateway()
    runtime = RepoHarnessRuntime(
        _runtime_options(tmp_path, source, resource_lease_manager=resource_manager)
    )

    async def scenario():
        first = asyncio.create_task(runtime.run_episode(request, llm_gateway=blocking_gateway))
        assert await asyncio.to_thread(blocking_gateway.started.wait, 1.0)
        await asyncio.sleep(0.05)
        assert not first.done()
        retry = await runtime.run_episode(request, llm_gateway=FakeLLMGateway([_final_response()]))
        blocking_gateway.release.set()
        first_result = await first
        return first_result, retry

    first_result, retry = asyncio.run(scenario())

    assert retry.status == "infrastructure_error"
    assert retry.status_reason == "run_directory_lock_conflict"
    assert first_result.status == "timeout"
    assert first_result.status_reason == "episode_timeout"
    assert any(
        diagnostic.code == "real_episode_thread_wait_after_timeout"
        for diagnostic in first_result.audit_diagnostics
    )
    run_status = json.loads(
        (tmp_path / "runs_verl" / request.run_id / "run_status.json").read_text(encoding="utf-8")
    )
    assert run_status["status"] == "FINALIZED"
    summary = (tmp_path / "runs_verl" / request.run_id / "summary.md").read_text(encoding="utf-8")
    assert "status: timeout" in summary
    assert "status_reason: episode_timeout" in summary


def test_stage11_5_real_episode_cancellation_holds_leases_until_agent_thread_finishes(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    resource_manager = ResourceLeaseManager(
        ResourceConcurrencyPolicy(max_concurrent_episodes=2, max_workspace_leases=2)
    )
    request = _episode_request()
    blocking_gateway = BlockingGateway()
    runtime = RepoHarnessRuntime(
        _runtime_options(tmp_path, source, resource_lease_manager=resource_manager)
    )

    async def scenario():
        first = asyncio.create_task(runtime.run_episode(request, llm_gateway=blocking_gateway))
        assert await asyncio.to_thread(blocking_gateway.started.wait, 1.0)
        first.cancel()
        await asyncio.sleep(0.05)
        assert not first.done()
        retry = await runtime.run_episode(request, llm_gateway=FakeLLMGateway([_final_response()]))
        blocking_gateway.release.set()
        first_result = await first
        return first_result, retry

    first_result, retry = asyncio.run(scenario())

    assert retry.status == "infrastructure_error"
    assert retry.status_reason == "run_directory_lock_conflict"
    assert first_result.status == "cancelled"
    assert first_result.status_reason == "runtime_cancelled"
    assert any(
        diagnostic.code == "real_episode_thread_wait_after_cancelled"
        for diagnostic in first_result.audit_diagnostics
    )
    run_status = json.loads(
        (tmp_path / "runs_verl" / request.run_id / "run_status.json").read_text(encoding="utf-8")
    )
    assert run_status["status"] == "FINALIZED"
    summary = (tmp_path / "runs_verl" / request.run_id / "summary.md").read_text(encoding="utf-8")
    assert "status: cancelled" in summary
    assert "status_reason: runtime_cancelled" in summary


def test_stage11_5_final_verifier_timeout_holds_leases_until_verifier_thread_finishes(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
    resource_manager = ResourceLeaseManager(
        ResourceConcurrencyPolicy(max_concurrent_episodes=2, max_workspace_leases=2)
    )
    verifier_started = threading.Event()
    verifier_release = threading.Event()

    def verifier_factory(context):
        def verify() -> VerifierResult:
            verifier_started.set()
            verifier_release.wait()
            return _verifier_result(accepted=True)

        return verify

    request = _episode_request(
        budgets={**_episode_request().budgets.model_dump(mode="json"), "max_verifier_seconds": 0.01}
    )
    runtime = RepoHarnessRuntime(
        _runtime_options(
            tmp_path,
            source,
            resource_lease_manager=resource_manager,
            real_episode_final_verifier_factory=verifier_factory,
        )
    )

    async def scenario():
        first = asyncio.create_task(runtime.run_episode(request, llm_gateway=FakeLLMGateway([_final_response()])))
        assert await asyncio.to_thread(verifier_started.wait, 1.0)
        await asyncio.sleep(0.05)
        assert not first.done()
        retry = await runtime.run_episode(request, llm_gateway=FakeLLMGateway([_final_response()]))
        verifier_release.set()
        first_result = await first
        return first_result, retry

    first_result, retry = asyncio.run(scenario())

    assert retry.status == "infrastructure_error"
    assert retry.status_reason == "run_directory_lock_conflict"
    assert first_result.status == "timeout"
    assert first_result.status_reason == "execution_timeout"
    assert first_result.verifier_summary is not None
    assert first_result.verifier_summary.status == "execution_timeout"
    run_status = json.loads(
        (tmp_path / "runs_verl" / request.run_id / "run_status.json").read_text(encoding="utf-8")
    )
    assert run_status["status"] == "FINALIZED"
    summary = (tmp_path / "runs_verl" / request.run_id / "summary.md").read_text(encoding="utf-8")
    assert "status: timeout" in summary
    assert "status_reason: execution_timeout" in summary


def test_stage11_5_route_limiter_runs_on_runtime_event_loop_from_worker_thread(tmp_path: Path) -> None:
    source = _source_repo(tmp_path)
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
    runtime = RepoHarnessRuntime(
        _runtime_options(tmp_path, source, resource_lease_manager=resource_manager)
    )
    first_request = _episode_request(run_id="stage11-5-route-run-a", episode_id="stage11-5-route-episode-a")
    second_request = _episode_request(run_id="stage11-5-route-run-b", episode_id="stage11-5-route-episode-b")
    blocking_gateway = BlockingGateway()

    async def scenario():
        first = asyncio.create_task(runtime.run_episode(first_request, llm_gateway=blocking_gateway))
        assert await asyncio.to_thread(blocking_gateway.started.wait, 1.0)
        second = asyncio.create_task(runtime.run_episode(second_request, llm_gateway=FakeLLMGateway([_final_response()])))
        await asyncio.sleep(0.05)
        assert not second.done()
        blocking_gateway.release.set()
        second_result = await asyncio.wait_for(second, timeout=1.0)
        first_result = await asyncio.wait_for(first, timeout=1.0)
        return first_result, second_result

    first_result, second_result = asyncio.run(scenario())

    assert first_result.status in {"failed", "succeeded"}
    assert second_result.status in {"failed", "succeeded"}
    assert resource_manager.policy.max_gateway_route_concurrency_by_route["verl"] == 1


def test_stage11_5_unsupported_runtime_execution_mode_returns_structured_result() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_final_response()])
    runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(execution_mode="unsupported"))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "infrastructure_error"
    assert result.status_reason == "unsupported_runtime_execution_mode"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert gateway.requests == []
