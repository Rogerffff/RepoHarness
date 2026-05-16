from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from verl_reference_stubs import install_reference_verl_stubs


@dataclass
class TokenOutputLike:
    token_ids: list[int]
    log_probs: list[float] | None
    stop_reason: str | None = "completed"
    extra_fields: dict[str, Any] = field(default_factory=dict)
    num_preempted: int | None = None
    routed_experts: list[Any] | None = None


class FakeLLMServerClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
        return TokenOutputLike(
            token_ids=[201, 202],
            log_probs=[-0.11, -0.22],
            extra_fields={"global_steps": 9, "min_global_steps": 9, "max_global_steps": 9},
            routed_experts=["expert-a"],
        )


class FakeTokenizer:
    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        return " ".join(f"tok{token_id}" for token_id in ids)


class ConfigWrap:
    def __init__(self, config: Any) -> None:
        self.config = config


def _trainer_config() -> ConfigWrap:
    rollout = SimpleNamespace(name="sglang", prompt_length=16, response_length=8)
    return ConfigWrap(config=SimpleNamespace(actor_rollout_ref=SimpleNamespace(rollout=rollout)))


def _kwargs() -> dict[str, Any]:
    return {
        "raw_prompt": [{"role": "user", "content": "fix tests"}],
        "agent_name": "repo_harness",
        "task_id": "task-1",
        "repo_harness_task_ref": {"task_ref": "rh://task/task-1"},
        "uid": "uid-1",
        "index": 0,
        "session_id": 1,
        "global_steps": 9,
    }


def _install_stubs(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "repo_harness_verl.agent_loop", raising=False)


def test_stage11_agent_loop_registers_with_reference_verl(monkeypatch) -> None:
    _install_stubs(monkeypatch)

    import repo_harness_verl.agent_loop  # noqa: F401
    from verl.experimental.agent_loop.agent_loop import _agent_loop_registry

    assert _agent_loop_registry["repo_harness"]["_target_"] == (
        "repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop"
    )


def test_stage11_agent_loop_runs_runtime_gateway_and_returns_agent_loop_output(monkeypatch) -> None:
    _install_stubs(monkeypatch)

    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop

    server = FakeLLMServerClient()
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=_trainer_config(),
        server_manager=server,
        tokenizer=FakeTokenizer(),
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap(config={"apply_chat_template_kwargs": {}}),
    )
    loop._build_prompt_ids_for_gateway_request = lambda request: [31, 32, 33]  # type: ignore[method-assign]

    output = asyncio.run(loop.run({"max_tokens": 3, "temperature": 0.1}, **_kwargs()))

    assert output.__class__.__name__ == "AgentLoopOutput"
    assert output.prompt_ids == [31, 32, 33]
    assert output.response_ids == [201, 202]
    assert output.response_logprobs == [-0.11, -0.22]
    assert output.response_mask == [1, 1]
    assert output.reward_score == 1.0
    assert output.extra_fields["repo_harness_llm_gateway_route"] == "verl"
    assert output.extra_fields["repo_harness_status"] == "succeeded"
    assert "raw_prompt" not in output.extra_fields
    assert server.calls[0]["request_id"] == "task-1-uid-1-s1-i0-g9"
    assert server.calls[0]["prompt_ids"] == [31, 32, 33]


def test_stage11_agent_loop_rejects_hidden_kwargs(monkeypatch) -> None:
    _install_stubs(monkeypatch)

    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop
    from repo_harness_verl.errors import RepoHarnessVerlRequestMappingError

    loop = RepoHarnessVerlAgentLoop(
        trainer_config=_trainer_config(),
        server_manager=FakeLLMServerClient(),
        tokenizer=FakeTokenizer(),
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap(config={"apply_chat_template_kwargs": {}}),
    )
    payload = _kwargs()
    payload["ground_truth"] = "answer"

    with pytest.raises(RepoHarnessVerlRequestMappingError):
        asyncio.run(loop.run({"max_tokens": 3}, **payload))
