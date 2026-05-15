import asyncio
import json
from pathlib import Path

import pytest

from repo_harness.rl import (
    FormalOnlineRLSample,
    LLMGatewayRequest,
    MockLLMGateway,
    RepoHarnessEpisodeResult,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    UnsupportedRouteLLMGateway,
    build_llm_gateway_for_route,
    validate_formal_online_rl_batch,
    validate_training_view_for_online_rl,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _gateway_request(*, route: str = "mock", inference_backend: str | None = None) -> LLMGatewayRequest:
    return LLMGatewayRequest(
        route=route,  # type: ignore[arg-type]
        inference_backend=inference_backend,  # type: ignore[arg-type]
        run_id="stage5-route-run",
        task_id="stage5-route-task",
        episode_id="stage5-route-episode",
        model_call_id="stage5-route-call-0",
        turn=0,
        context_revision=0,
        messages=[{"role": "user", "content": "fix the test"}],
        tools=[],
        sampling_params={"temperature": 0.0},
        provider_options={"provider": route, "model_id": "stage5-model"},
        tokenizer_policy={},
        recorder_policy={},
        visibility_policy={},
    )


def _episode_request(**updates: object) -> RepoHarnessEpisodeRequest:
    payload = json.loads((FIXTURE_ROOT / "canonical_episode_request.json").read_text(encoding="utf-8"))
    for key, value in updates.items():
        payload[key] = value
    return RepoHarnessEpisodeRequest.model_validate(payload)


def test_stage5_mock_gateway_returns_deterministic_training_tokens() -> None:
    gateway = MockLLMGateway()
    request = _gateway_request()

    response = asyncio.run(gateway.generate_turn(request))

    assert response.route == "mock"
    assert response.inference_backend is None
    assert response.model_call_id == "stage5-route-call-0"
    assert response.output_token_ids
    assert response.output_logprobs is not None
    assert len(response.output_token_ids) == len(response.output_logprobs) == len(response.response_mask)
    assert set(response.response_mask) == {1}
    assert response.token_source == "mock_gateway"


def test_stage5_mock_route_is_diagnostic_not_formal_online_rl_sample() -> None:
    request = _episode_request(llm_gateway_route="mock", inference_backend=None)
    runtime = RepoHarnessRuntime()

    result = asyncio.run(runtime.run_episode(request, llm_gateway=MockLLMGateway()))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "non_verl_route_invalid_for_online_rl"
    assert result.training_view.extra_fields["repo_harness_llm_gateway_route"] == "mock"
    with pytest.raises(ValueError, match="non_verl_route_invalid_for_online_rl"):
        validate_training_view_for_online_rl(result.training_view)


def test_stage5_formal_online_rl_batch_rejects_every_non_verl_route() -> None:
    sample = FormalOnlineRLSample(
        sample_id="mock-sample",
        route="mock",
        prompt_ids=[1],
        response_ids=[2],
        response_mask=[1],
        response_logprobs=[-0.1],
        reward_score=1.0,
    )

    with pytest.raises(ValueError, match="non_verl_route_invalid_for_online_rl"):
        validate_formal_online_rl_batch([sample])


def test_stage5_formal_online_rl_helpers_require_explicit_verl_route() -> None:
    request = _episode_request()
    runtime = RepoHarnessRuntime()
    result = asyncio.run(runtime.run_episode(request, llm_gateway=MockLLMGateway()))
    view = result.training_view.model_copy(
        update={
            "online_rl_eligible": True,
            "extra_fields": {
                key: value
                for key, value in result.training_view.extra_fields.items()
                if key != "repo_harness_llm_gateway_route"
            },
        }
    )

    with pytest.raises(ValueError, match="missing_llm_gateway_route_for_online_rl"):
        validate_training_view_for_online_rl(view)
    with pytest.raises(ValueError, match="missing_llm_gateway_route_for_online_rl"):
        validate_formal_online_rl_batch([view])

    with pytest.raises(ValueError, match="route"):
        validate_formal_online_rl_batch(
            [
                {
                    "prompt_ids": [1],
                    "response_ids": [2],
                    "response_mask": [1],
                    "response_logprobs": [-0.1],
                    "reward_score": 1.0,
                }
            ]
        )


def test_stage5_episode_result_rejects_training_route_generation_record_mismatch() -> None:
    payload = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["training_view"]["extra_fields"]["repo_harness_llm_gateway_route"] = "verl"
    payload["generation_records"][0]["gateway_route"] = "mock"

    with pytest.raises(ValueError, match="gateway_route_mismatch_between_training_view_and_generation_records"):
        RepoHarnessEpisodeResult.model_validate(payload)


def test_stage5_route_builder_returns_mock_gateway_without_provider_client() -> None:
    gateway = build_llm_gateway_for_route("mock")

    assert isinstance(gateway, MockLLMGateway)


def test_stage5_route_builder_returns_structured_unsupported_gateway_without_fallback() -> None:
    gateway = build_llm_gateway_for_route("local_vllm")
    request = _gateway_request(route="local_vllm", inference_backend="vllm")

    response = asyncio.run(gateway.generate_turn(request))

    assert response.route == "local_vllm"
    assert response.inference_backend == "vllm"
    assert response.output_token_ids == []
    assert response.output_logprobs is None
    assert response.error == {"error_type": "unsupported_route", "route": "local_vllm"}
    assert response.token_source == "provider_unavailable"


@pytest.mark.parametrize(
    ("route", "inference_backend"),
    [
        ("verl", "sglang"),
        ("local_vllm", "vllm"),
        ("local_sglang", "sglang"),
    ],
)
def test_stage5_unimplemented_routes_do_not_fallback_to_legacy_model_client(
    tmp_path: Path,
    route: str,
    inference_backend: str,
) -> None:
    gateway = build_llm_gateway_for_route(
        route,
        model_client=object(),  # type: ignore[arg-type]
        run_dir_root=tmp_path,
    )
    request = _gateway_request(route=route, inference_backend=inference_backend)

    response = asyncio.run(gateway.generate_turn(request))

    assert isinstance(gateway, UnsupportedRouteLLMGateway)
    assert response.route == route
    assert response.error == {"error_type": "unsupported_route", "route": route}
    assert response.output_token_ids == []
