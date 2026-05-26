import asyncio
import json
from pathlib import Path
from typing import Any

from repo_harness.model_client.schemas import ModelProviderOptions, ModelRequestContext
from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayModelClientAdapter,
    LLMGatewayRequest,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
    map_episode_status,
    validate_training_view_for_online_rl,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.trajectory import ArtifactRef


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
SHA = "a" * 64
DEFAULT_LOGPROBS = object()


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _episode_request(**updates: Any) -> RepoHarnessEpisodeRequest:
    payload = _load_json("canonical_episode_request.json")
    for key, value in updates.items():
        payload[key] = value
    return RepoHarnessEpisodeRequest.model_validate(payload)


def _gateway_response(
    *,
    route: str = "verl",
    inference_backend: str | None = "sglang",
    model_call_id: str = "stage0h-episode-success-turn-0",
    output_token_ids: list[int] | None = None,
    output_logprobs: list[float] | None | object = DEFAULT_LOGPROBS,
) -> LLMGatewayResponse:
    tokens = [501, 502] if output_token_ids is None else output_token_ids
    if output_logprobs is DEFAULT_LOGPROBS and tokens:
        logprobs: list[float] | None = [-0.1 for _ in tokens]
    else:
        logprobs = output_logprobs  # type: ignore[assignment]
    return LLMGatewayResponse(
        route=route,  # type: ignore[arg-type]
        inference_backend=inference_backend,  # type: ignore[arg-type]
        model_call_id=model_call_id,
        assistant_message={"role": "assistant", "content": "patched"},
        prompt_ids=[101, 102],
        output_token_ids=tokens,
        output_logprobs=logprobs,
        response_mask=[1 for _ in tokens],
        stop_reason="stop",
        duration_ms=5,
        usage={"input_tokens": 2, "output_tokens": len(tokens)},
    )


def test_stage2_runtime_minimal_episode_uses_gateway_and_builds_training_view() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is False
    assert result.training_view.response_ids == [501, 502]
    assert result.training_view.response_mask == [1, 1]
    assert result.training_view.response_logprobs == [-0.1, -0.1]
    assert result.generation_records[0].model_call_id == "stage0h-episode-success-turn-0"
    assert gateway.requests
    assert gateway.requests[0].messages == request.raw_prompt
    assert gateway.requests[0].route == "verl"
    validate_training_view_for_online_rl(result.training_view)


def test_stage2_runtime_options_paths_do_not_leak_into_batch_fields() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            config_path="/Users/roger/private/config.yaml",
            output_dir="/Users/roger/private/runs",
            project_root="/Users/roger/private/project",
        )
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    serialized_extra = json.dumps(result.training_view.extra_fields, sort_keys=True)
    assert "/Users/" not in serialized_extra
    assert result.audit_ref.run_dir == f"runs/{request.run_id}"
    assert not result.audit_ref.run_dir.startswith("/")


def test_stage2_runtime_can_require_explicit_task_path_resolution() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(require_resolved_task_path=True))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "invalid_task"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "invalid_task"
    assert gateway.requests == []


def test_stage2_runtime_task_path_resolver_satisfies_runner_input_boundary() -> None:
    request = _episode_request()
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            require_resolved_task_path=True,
            task_path_resolver=lambda episode: f"tasks/{episode.task_id}.json",
        )
    )

    resolved = runtime.resolve_runner_inputs(request)

    assert resolved.task_path == "tasks/stage0h-task-success.json"


def test_stage2_runtime_rejects_absolute_task_path_from_episode_request() -> None:
    payload = _load_json("canonical_episode_request.json")
    payload["task_ref"]["task_path"] = "/Users/roger/private/task.yaml"
    request = RepoHarnessEpisodeRequest.model_validate(payload)
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "invalid_task"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "invalid_task"
    assert gateway.requests == []


def test_stage2_runtime_status_mapping_table() -> None:
    assert map_episode_status(final_verifier_status="accepted") == "succeeded"
    assert map_episode_status(final_verifier_status="rejected") == "failed"
    assert map_episode_status(agent_stop_reason="no_progress") == "no_progress"
    assert map_episode_status(timeout=True, final_verifier_status="accepted") == "timeout"
    assert map_episode_status(provider_error_type="provider_timeout") == "timeout"
    assert map_episode_status(provider_error_type="provider_timeout_or_transport_error") == "timeout"
    assert map_episode_status(agent_stop_reason="task_timeout") == "timeout"
    assert map_episode_status(agent_stop_reason="tool_timeout") == "timeout"
    assert map_episode_status(baseline_status="invalid") == "invalid_task"
    assert map_episode_status(infrastructure_error=True, final_verifier_status="accepted") == "infrastructure_error"
    assert map_episode_status(cancelled=True, final_verifier_status="accepted") == "cancelled"


class SlowGateway:
    def __init__(self) -> None:
        self.requests: list[LLMGatewayRequest] = []

    async def generate_turn(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        self.requests.append(request)
        await asyncio.sleep(60)
        return _gateway_response()


def test_stage2_runtime_timeout_returns_invalid_result_and_runs_cleanup() -> None:
    cleanup_calls: list[str] = []
    request = _episode_request(budgets={**_load_json("canonical_episode_request.json")["budgets"], "max_wall_seconds": 0.01})
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(cleanup_callback=lambda: cleanup_calls.append("cleanup"))
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=SlowGateway()))

    assert result.status == "timeout"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.resource_summary is not None
    assert result.resource_summary.cleanup_status == "completed"
    assert cleanup_calls == ["cleanup"]


def test_stage2_runtime_cancellation_returns_cancelled_result_and_runs_cleanup() -> None:
    cleanup_calls: list[str] = []
    request = _episode_request()
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(cleanup_callback=lambda: cleanup_calls.append("cleanup"))
    )

    async def scenario():
        task = asyncio.create_task(runtime.run_episode(request, llm_gateway=SlowGateway()))
        await asyncio.sleep(0)
        task.cancel()
        return await task

    result = asyncio.run(scenario())

    assert result.status == "cancelled"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.resource_summary is not None
    assert result.resource_summary.cleanup_status == "completed"
    assert cleanup_calls == ["cleanup"]


def test_stage2_runtime_cleanup_failure_preserves_primary_status() -> None:
    request = _episode_request(budgets={**_load_json("canonical_episode_request.json")["budgets"], "max_wall_seconds": 0.01})

    def fail_cleanup() -> None:
        raise RuntimeError("cleanup boom")

    runtime = RepoHarnessRuntime(RepoHarnessRuntimeOptions(cleanup_callback=fail_cleanup))

    result = asyncio.run(runtime.run_episode(request, llm_gateway=SlowGateway()))

    assert result.status == "timeout"
    assert result.resource_summary is not None
    assert result.resource_summary.cleanup_status == "failed"
    assert any(diagnostic.code == "cleanup_failed" for diagnostic in result.audit_diagnostics)


def test_stage2_runtime_missing_logprobs_is_diagnostic_not_online_rl_sample() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response(output_logprobs=None)])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "missing_response_logprobs"
    assert result.training_view.response_logprobs is None


def test_stage2_runtime_provider_route_defaults_to_invalid_for_online_rl() -> None:
    request = _episode_request(llm_gateway_route="openai", inference_backend=None)
    gateway = FakeLLMGateway([_gateway_response(route="openai", inference_backend=None)])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "provider_route_invalid_for_online_rl"


def test_stage2_runtime_rejects_response_route_mismatch_before_online_rl() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response(route="openai", inference_backend=None)])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "infrastructure_error"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "gateway_route_mismatch"


def test_stage2_runtime_failed_episode_keeps_failed_batch_status() -> None:
    request = _episode_request()
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(minimal_final_verifier_status="rejected")
    )

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "failed"
    assert result.invalid_for_training is False
    assert result.training_view.reward_score == 0.0
    assert result.training_view.extra_fields["repo_harness_status"] == "failed"


def test_stage2_runtime_prompt_overflow_returns_structured_invalid_result() -> None:
    request = _episode_request(
        budgets={**_load_json("canonical_episode_request.json")["budgets"], "max_prompt_tokens": 1}
    )
    gateway = FakeLLMGateway([_gateway_response()])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "invalid"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "prompt_length_exceeded"
    assert result.budget_consumption is not None
    assert result.budget_consumption.stop_reason == "prompt_length_exceeded"
    assert any(diagnostic.code == "prompt_length_exceeded" for diagnostic in result.audit_diagnostics)


def test_stage2_runtime_response_overflow_records_budget_consumption_and_diagnostics() -> None:
    request = _episode_request(
        budgets={**_load_json("canonical_episode_request.json")["budgets"], "max_output_tokens": 1}
    )
    gateway = FakeLLMGateway([_gateway_response(output_token_ids=[501, 502, 503])])
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=gateway))

    assert result.status == "invalid"
    assert result.invalid_for_training is True
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "response_length_exceeded"
    assert result.budget_consumption is not None
    assert result.budget_consumption.stop_reason == "response_length_exceeded"
    assert result.budget_consumption.rollout_response_length == 1
    assert result.budget_consumption.actual_response_length == 3
    assert any(diagnostic.code == "response_length_exceeded" for diagnostic in result.audit_diagnostics)


def test_stage2_gateway_model_client_adapter_calls_gateway() -> None:
    gateway = FakeLLMGateway(
        [
            _gateway_response(
                route="mock",
                inference_backend=None,
                model_call_id="model-call-adapter",
            )
        ]
    )
    adapter = LLMGatewayModelClientAdapter(
        llm_gateway=gateway,
        episode_id="episode-adapter",
        route="mock",
    )
    request = _model_request_context()

    response = adapter.generate(request, recorder=None)

    assert gateway.requests
    assert gateway.requests[0].messages == request.prepared_messages
    assert gateway.requests[0].model_call_id == "model-call-adapter"
    assert response.assistant_message.content == "patched"
    assert response.model_call_event is not None
    assert response.model_call_event.provider == "mock"
    assert response.token_usage == {"input_tokens": 2, "output_tokens": 2}


def test_stage2_gateway_model_client_adapter_preserves_structured_error_type() -> None:
    gateway = FakeLLMGateway(
        [
            _gateway_response(
                route="mock",
                inference_backend=None,
                model_call_id="model-call-adapter",
            ).model_copy(
                update={
                    "assistant_message": {
                        "role": "assistant",
                        "content": "deepseek provider returned structured error: tool_call_parse_failure",
                    },
                    "error": {"model_error_type": "tool_call_parse_failure"},
                }
            )
        ]
    )
    adapter = LLMGatewayModelClientAdapter(
        llm_gateway=gateway,
        episode_id="episode-adapter",
        route="mock",
    )
    request = _model_request_context()

    response = adapter.generate(request, recorder=None)

    assert response.model_error_type == "tool_call_parse_failure"
    assert response.terminal_error_type == "tool_call_parse_failure"
    assert response.model_call_event is not None
    assert response.model_call_event.model_error_type == "tool_call_parse_failure"
    assert response.model_call_event.terminal_error_type == "tool_call_parse_failure"


def test_stage2_gateway_model_client_adapter_preserves_provider_timeout_error() -> None:
    gateway = FakeLLMGateway(
        [
            _gateway_response(
                route="mock",
                inference_backend=None,
                model_call_id="model-call-adapter",
            ).model_copy(update={"error": {"model_error_type": "provider_timeout"}})
        ]
    )
    adapter = LLMGatewayModelClientAdapter(
        llm_gateway=gateway,
        episode_id="episode-adapter",
        route="mock",
    )

    response = adapter.generate(_model_request_context(), recorder=None)

    assert response.model_error_type == "provider_timeout"
    assert response.terminal_error_type == "provider_timeout"
    assert response.model_call_event is not None
    assert response.model_call_event.model_error_type == "provider_timeout"
    assert response.model_call_event.terminal_error_type == "provider_timeout"


def test_stage2_gateway_model_client_adapter_falls_back_for_unknown_gateway_error() -> None:
    gateway = FakeLLMGateway(
        [
            _gateway_response(
                route="mock",
                inference_backend=None,
                model_call_id="model-call-adapter",
            ).model_copy(update={"error": {"message": "unknown gateway failure"}})
        ]
    )
    adapter = LLMGatewayModelClientAdapter(
        llm_gateway=gateway,
        episode_id="episode-adapter",
        route="mock",
    )

    response = adapter.generate(_model_request_context(), recorder=None)

    assert response.model_error_type == "gateway_response_error"
    assert response.terminal_error_type == "gateway_response_error"
    assert response.model_call_event is not None
    assert response.model_call_event.model_error_type == "gateway_response_error"
    assert response.model_call_event.terminal_error_type == "gateway_response_error"


def _artifact_ref(relative_path: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=relative_path.replace("/", "-"),
        relative_path=relative_path,
        kind="json",
        sha256=SHA,
        size_bytes=1,
    )


def _model_request_context() -> ModelRequestContext:
    return ModelRequestContext(
        run_id="run-adapter",
        task_id="task-adapter",
        turn=0,
        model_call_id="model-call-adapter",
        prepared_messages=[{"role": "user", "content": "fix it"}],
        prepared_messages_ref=_artifact_ref("prepared_messages.json"),
        model_input_hash=SHA,
        context_revision=0,
        provider_message_format="chat",
        context_truncation_facts={},
        omitted_context_facts={},
        generation_config={"temperature": 0.0},
        provider_model_settings={},
        allowed_tool_definitions=[],
        tool_schema_snapshot_ref=_artifact_ref("tool_schema.json"),
        provider_options=ModelProviderOptions(provider="mock", model_id="mock-model"),
        scaffold_id="default",
        scaffold_phase="agent_loop",
        run_config_facts_ref=RunConfigFactsRef(sha256=SHA),
        budget_state={},
        request_timeout_seconds=30,
        raw_request_logging_policy="disabled",
        credential_policy=ModelProviderOptions(provider="mock", model_id="mock-model").credential_policy,
        retry_policy="none",
    )
