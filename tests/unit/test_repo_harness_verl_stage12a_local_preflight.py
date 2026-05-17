from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import LLMGatewayRequest, TrainingView
from repo_harness_verl import (
    VerlLLMGateway,
    training_view_to_agent_loop_output,
    validate_transfer_queue_field_visibility,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _require_real_verl():
    pytest.importorskip("torch")
    pytest.importorskip("verl.experimental.agent_loop.agent_loop")
    pytest.importorskip("verl.workers.rollout.replica")
    pytest.importorskip("verl.workers.rollout.llm_server")


class FakeTokenizer:
    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        return " ".join(f"tok{token_id}" for token_id in ids)


class FakeLLMServerClient:
    def __init__(self, token_output: Any) -> None:
        self.token_output = token_output
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
    ) -> Any:
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
        return self.token_output


def test_stage12a_ordinary_repo_harness_import_does_not_eager_import_verl_heavy_modules() -> None:
    script = """
import sys
import repo_harness.rl
import repo_harness_verl
heavy = sorted(name for name in ["verl", "torch", "ray", "tensordict"] if name in sys.modules)
if heavy:
    raise SystemExit(f"ordinary import loaded heavy modules: {heavy}")
print("ordinary_import_ok")
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ordinary_import_ok" in result.stdout


def test_stage12a_real_reference_verl_cpu_interfaces_import_without_cuda() -> None:
    _require_real_verl()
    import torch
    from verl.experimental.agent_loop.agent_loop import (
        AgentLoopBase,
        AgentLoopMetrics,
        AgentLoopOutput,
        AgentLoopWorker,
    )
    from verl.workers.rollout.llm_server import LLMServerClient
    from verl.workers.rollout.replica import TokenOutput

    assert torch.cuda.is_available() is False
    assert AgentLoopOutput.__name__ == "AgentLoopOutput"
    assert AgentLoopMetrics.__name__ == "AgentLoopMetrics"
    assert AgentLoopBase.__name__ == "AgentLoopBase"
    assert AgentLoopWorker.__name__ == "AgentLoopWorker"
    assert TokenOutput.__name__ == "TokenOutput"
    assert LLMServerClient.__name__ == "LLMServerClient"


def test_stage12a_real_agent_loop_output_as_dict_uses_cpu_tensors() -> None:
    _require_real_verl()
    import torch

    payload = _load_json("canonical_training_view.json")
    payload["online_rl_eligible"] = True
    payload["extra_fields"] = {**payload["extra_fields"], "repo_harness_llm_gateway_route": "verl"}
    output = training_view_to_agent_loop_output(
        TrainingView.model_validate(payload),
        generation_records=_load_json("canonical_episode_result.json")["generation_records"],
        rollout_prompt_length=16,
        rollout_response_length=12,
    )

    field = output.as_dict()

    validate_transfer_queue_field_visibility(field)
    assert field["prompts"].device.type == "cpu"
    assert field["responses"].device.type == "cpu"
    assert field["response_mask"].device.type == "cpu"
    assert field["rollout_log_probs"].device.type == "cpu"
    assert field["rm_scores"].device.type == "cpu"
    assert torch.cuda.is_available() is False


def test_stage12a_verl_gateway_accepts_real_token_output_shape() -> None:
    _require_real_verl()
    from verl.workers.rollout.replica import TokenOutput

    token_output = TokenOutput(
        token_ids=[701, 702],
        log_probs=[-0.71, -0.72],
        extra_fields={
            "global_steps": 12,
            "min_global_steps": 12,
            "max_global_steps": 12,
            "repo_harness_tool_calls": [
                {
                    "tool_call_id": "stage12a-local-tool-call",
                    "tool_name": "read_file",
                    "arguments": {"path": "calculator.py"},
                }
            ],
        },
    )
    client = FakeLLMServerClient(token_output)
    gateway = VerlLLMGateway(
        server_manager=client,
        tokenizer=FakeTokenizer(),
        inference_backend="sglang",
        sampling_params={"max_new_tokens": 2},
        prompt_ids_builder=lambda _request: [101, 102],
    )

    import asyncio

    response = asyncio.run(
        gateway.generate_turn(
            LLMGatewayRequest(
                route="verl",
                inference_backend="sglang",
                run_id="stage12a-run",
                task_id="stage12a-task",
                episode_id="stage12a-episode",
                model_call_id="stage12a-call-0",
                turn=0,
                context_revision=0,
                messages=[{"role": "user", "content": "visible task"}],
                tools=[],
                sampling_params={},
            )
        )
    )

    assert client.calls[0]["request_id"] == "stage12a-episode"
    assert response.route == "verl"
    assert response.inference_backend == "sglang"
    assert response.output_token_ids == [701, 702]
    assert response.output_logprobs == [-0.71, -0.72]
    assert response.response_mask == [1, 1]
    assert response.tool_calls == [
        {
            "tool_call_id": "stage12a-local-tool-call",
            "tool_name": "read_file",
            "arguments": {"path": "calculator.py"},
        }
    ]
    assert "repo_harness_tool_calls" not in response.extra_fields
