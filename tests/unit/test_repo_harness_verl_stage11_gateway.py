from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from repo_harness.rl import LLMGatewayRequest
from repo_harness_verl import RepoHarnessVerlGatewayError, VerlLLMGateway, token_output_to_llm_gateway_response


@dataclass
class TokenOutputLike:
    token_ids: list[int]
    log_probs: list[float] | None
    stop_reason: str | None = "completed"
    extra_fields: dict[str, Any] = field(default_factory=dict)
    num_preempted: int | None = None
    routed_experts: list[Any] | None = None


class FakeTokenizer:
    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        return " ".join(f"tok{token_id}" for token_id in ids)


class FakeLLMServerClient:
    def __init__(self, output: TokenOutputLike) -> None:
        self.output = output
        self.calls: list[dict[str, Any]] = []
        self.start_server_called = False
        self.stop_server_called = False

    async def generate(
        self,
        request_id: str,
        *,
        prompt_ids: list[int],
        sampling_params: dict[str, Any],
        image_data: list[Any] | None = None,
        video_data: list[Any] | None = None,
        **kwargs: Any,
    ) -> TokenOutputLike:
        self.calls.append(
            {
                "request_id": request_id,
                "prompt_ids": prompt_ids,
                "sampling_params": sampling_params,
                "image_data": image_data,
                "video_data": video_data,
                "kwargs": kwargs,
            }
        )
        return self.output

    def start_server(self) -> None:
        self.start_server_called = True

    def stop_server(self) -> None:
        self.stop_server_called = True


def _request() -> LLMGatewayRequest:
    return LLMGatewayRequest(
        route="verl",
        inference_backend="sglang",
        run_id="run-1",
        task_id="task-1",
        episode_id="episode-1",
        model_call_id="episode-1-turn-0",
        turn=0,
        context_revision=0,
        messages=[{"role": "user", "content": "fix tests"}],
        sampling_params={"temperature": 0.2, "max_tokens": 4},
        sticky_session_id="sticky-episode-1",
    )


def test_stage11_verl_gateway_calls_llm_server_with_sticky_request_id() -> None:
    client = FakeLLMServerClient(
        TokenOutputLike(
            token_ids=[101, 102],
            log_probs=[-0.1, -0.2],
            extra_fields={"global_steps": 5, "min_global_steps": 4, "max_global_steps": 6},
            num_preempted=2,
            routed_experts=["expert-a", "expert-b"],
        )
    )
    gateway = VerlLLMGateway(
        server_manager=client,
        tokenizer=FakeTokenizer(),
        inference_backend="sglang",
        sampling_params={"top_p": 0.9},
        prompt_ids_builder=lambda request: [11, 12, 13],
    )

    response = asyncio.run(gateway.generate_turn(_request()))

    assert client.calls == [
        {
            "request_id": "sticky-episode-1",
            "prompt_ids": [11, 12, 13],
            "sampling_params": {"top_p": 0.9, "temperature": 0.2, "max_tokens": 4},
            "image_data": None,
            "video_data": None,
            "kwargs": {},
        }
    ]
    assert not client.start_server_called
    assert not client.stop_server_called
    assert response.route == "verl"
    assert response.inference_backend == "sglang"
    assert response.prompt_ids == [11, 12, 13]
    assert response.output_token_ids == [101, 102]
    assert response.output_logprobs == [-0.1, -0.2]
    assert response.response_mask == [1, 1]
    assert response.global_steps == 5
    assert response.min_global_steps == 4
    assert response.max_global_steps == 6
    assert response.extra_fields["num_preempted"] == 2
    assert response.routed_experts == ["expert-a", "expert-b"]
    assert response.to_generation_record(turn=0, context_revision=0).output_token_ids == [101, 102]


def test_stage11_token_output_extra_fields_are_recursively_checked() -> None:
    with pytest.raises(RepoHarnessVerlGatewayError, match="forbidden_token_output_extra_fields"):
        token_output_to_llm_gateway_response(
            TokenOutputLike(
                token_ids=[1],
                log_probs=[-0.1],
                extra_fields={"safe": {"rewardExtraInfo": {"score": 1}}},
            ),
            request=_request(),
            prompt_ids=[11],
            tokenizer=FakeTokenizer(),
            inference_backend="sglang",
            duration_ms=0,
        )


@pytest.mark.parametrize(
    "extra_fields",
    [
        {"prompts": {"ground_truth": "answer"}},
        {"responses": {"rewardExtraInfo": {"score": 1}}},
        {"teacher_ids": {"extra_info": "secret"}},
        {"loss_mask": {"ground_truth": "answer"}},
    ],
)
def test_stage11_token_output_extra_fields_rejects_reserved_training_keys(extra_fields: dict[str, Any]) -> None:
    with pytest.raises(RepoHarnessVerlGatewayError, match="forbidden_token_output_extra_fields"):
        token_output_to_llm_gateway_response(
            TokenOutputLike(token_ids=[1], log_probs=[-0.1], extra_fields=extra_fields),
            request=_request(),
            prompt_ids=[11],
            tokenizer=FakeTokenizer(),
            inference_backend="sglang",
            duration_ms=0,
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {"ground_truth": "answer"},
        {"path": "/Users/roger/secret.txt"},
        {"note": "hidden_verifier"},
        {"reward_extra_info": {"score": 1}},
    ],
)
def test_stage12a_token_output_tool_calls_are_recursively_checked(arguments: dict[str, Any]) -> None:
    with pytest.raises(RepoHarnessVerlGatewayError, match="forbidden_repo_harness_tool_calls"):
        token_output_to_llm_gateway_response(
            TokenOutputLike(
                token_ids=[1],
                log_probs=[-0.1],
                extra_fields={
                    "repo_harness_tool_calls": [
                        {
                            "tool_call_id": "unsafe-tool-call",
                            "tool_name": "read_file",
                            "arguments": arguments,
                        }
                    ]
                },
            ),
            request=_request(),
            prompt_ids=[11],
            tokenizer=FakeTokenizer(),
            inference_backend="sglang",
            duration_ms=0,
        )


def test_stage11_missing_logprobs_stays_invalid_for_formal_online_rl() -> None:
    response = token_output_to_llm_gateway_response(
        TokenOutputLike(token_ids=[1], log_probs=None),
        request=_request(),
        prompt_ids=[11],
        tokenizer=FakeTokenizer(),
        inference_backend="sglang",
        duration_ms=0,
    )

    assert response.output_logprobs is None
    assert response.error == {"type": "missing_response_logprobs"}
