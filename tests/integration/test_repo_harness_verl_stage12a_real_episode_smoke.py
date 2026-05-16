from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_harness.rl import (
    FakeLLMGateway,
    LLMGatewayResponse,
    RepoHarnessEpisodeRequest,
    RepoHarnessRuntime,
    RepoHarnessRuntimeOptions,
    validate_training_view_for_online_rl,
)
from repo_harness.verifier import VerifierResult


REPO_ROOT = Path(__file__).resolve().parents[2]
BUGGY_CALCULATOR_SOURCE = REPO_ROOT / "tests" / "fixtures" / "repos" / "buggy_calculator"

OLD_DIVIDE = """def divide(left: int, right: int) -> float:
    return left / right
"""

NEW_DIVIDE = """def divide(left: int, right: int) -> float:
    if right == 0:
        raise ValueError("division by zero")
    return left / right
"""


class ConfigWrap:
    def __init__(self, config: Any) -> None:
        self.config = config


class FakeTokenizer:
    pad_token_id = 0

    def __init__(self) -> None:
        self.padding_side = "right"

    def apply_chat_template(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        add_generation_prompt: bool = False,
        tokenize: bool = True,
        return_dict: bool = False,
        **kwargs: Any,
    ) -> list[int] | str:
        ids = [11]
        for message in messages:
            ids.extend([len(str(message.get("role", ""))) + 1, len(str(message.get("content", ""))) % 97 + 1])
        if tools:
            ids.append(80 + len(tools))
        if add_generation_prompt:
            ids.append(99)
        return ids if tokenize else " ".join(str(item) for item in ids)

    def decode(self, ids: Any, skip_special_tokens: bool = True) -> str:
        return " ".join(f"tok{token_id}" for token_id in _to_list(ids))

    def pad(
        self,
        inputs: dict[str, list[int]],
        *,
        padding: str,
        max_length: int,
        return_tensors: str,
        return_attention_mask: bool,
    ) -> dict[str, Any]:
        import torch

        ids = list(inputs["input_ids"])
        pad_size = max_length - len(ids)
        if pad_size < 0:
            raise ValueError("input longer than max_length")
        if self.padding_side == "left":
            padded = [self.pad_token_id] * pad_size + ids
            attention = [0] * pad_size + [1] * len(ids)
        else:
            padded = ids + [self.pad_token_id] * pad_size
            attention = [1] * len(ids) + [0] * pad_size
        output = {"input_ids": torch.tensor(padded, dtype=torch.int64)}
        if return_attention_mask:
            output["attention_mask"] = torch.tensor(attention, dtype=torch.int64)
        return output


class QueueingFakeLLMServerClient:
    def __init__(self, token_output_cls: type[Any], outputs: list[dict[str, Any]]) -> None:
        self.token_output_cls = token_output_cls
        self.outputs = list(outputs)
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
                "prompt_ids": list(prompt_ids),
                "sampling_params": dict(sampling_params),
                "image_data": image_data,
                "video_data": video_data,
                "kwargs": kwargs,
            }
        )
        if not self.outputs:
            raise AssertionError("fake LLMServerClient output queue exhausted")
        return self.token_output_cls(**self.outputs.pop(0))


def _to_list(value: Any) -> list[Any]:
    if hasattr(value, "tolist"):
        maybe_list = value.tolist()
        return maybe_list if isinstance(maybe_list, list) else [maybe_list]
    return list(value)


def _require_real_verl():
    pytest.importorskip("torch")
    pytest.importorskip("verl.experimental.agent_loop.agent_loop")
    pytest.importorskip("verl.workers.rollout.replica")


def _trainer_config() -> ConfigWrap:
    rollout = SimpleNamespace(name="sglang", prompt_length=96, response_length=32)
    return ConfigWrap(SimpleNamespace(actor_rollout_ref=SimpleNamespace(rollout=rollout)))


def _sample_kwargs(*, task_id: str = "stage12a-buggy-calculator", uid: str = "uid-stage12a") -> dict[str, Any]:
    return {
        "raw_prompt": [
            {
                "role": "user",
                "content": (
                    "Update calculator.divide so division by zero raises ValueError with message "
                    "'division by zero'."
                ),
            }
        ],
        "agent_name": "repo_harness",
        "task_id": task_id,
        "repo_harness_task_ref": {"task_ref": f"rh://task/{task_id}"},
        "repo_harness_run_mode": "training_fast",
        "uid": uid,
        "index": 0,
        "session_id": 1,
        "global_steps": 12,
    }


def _verifier_result_from_pytest(workspace_path: Path) -> VerifierResult:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
        check=False,
    )
    accepted = completed.returncode == 0
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=1.0,
        command=f"{sys.executable} -m pytest -q",
        accepted=accepted,
        pass_ratio=1.0 if accepted else 0.0,
        fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
        pass_to_pass={"passed": 2 if accepted else 0, "total": 2},
        exit_code=completed.returncode,
        error_type=None if accepted else "test_command_error",
    )


def _runtime_options(tmp_path: Path, *, resource_lease_manager: Any = None) -> RepoHarnessRuntimeOptions:
    def verifier_factory(context: Any):
        def verify() -> VerifierResult:
            return _verifier_result_from_pytest(context.workspace_path)

        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=tmp_path / "stage12a_runs",
        real_episode_source_resolver=lambda _request: BUGGY_CALCULATOR_SOURCE,
        real_episode_final_verifier_factory=verifier_factory,
        resource_lease_manager=resource_lease_manager,
        tool_observation_token_projector=lambda _content: [77_001, 77_002],
    )


def _verl_token_outputs() -> list[dict[str, Any]]:
    return [
        {
            "token_ids": [50_001],
            "log_probs": [-0.51],
            "stop_reason": "tool_calls",
            "extra_fields": {
                "global_steps": 12,
                "min_global_steps": 12,
                "max_global_steps": 12,
                "repo_harness_tool_calls": [
                    {
                        "tool_call_id": "stage12a-read-calculator",
                        "tool_name": "read_file",
                        "arguments": {"path": "calculator.py"},
                    }
                ],
            },
        },
        {
            "token_ids": [50_002],
            "log_probs": [-0.52],
            "stop_reason": "tool_calls",
            "extra_fields": {
                "global_steps": 12,
                "min_global_steps": 12,
                "max_global_steps": 12,
                "repo_harness_tool_calls": [
                    {
                        "tool_call_id": "stage12a-edit-calculator",
                        "tool_name": "edit_file",
                        "arguments": {
                            "path": "calculator.py",
                            "old_text": OLD_DIVIDE,
                            "new_text": NEW_DIVIDE,
                        },
                    }
                ],
            },
        },
        {
            "token_ids": [50_003],
            "log_probs": [-0.53],
            "stop_reason": "stop",
            "extra_fields": {"global_steps": 12, "min_global_steps": 12, "max_global_steps": 12},
        },
    ]


def _mock_gateway_responses() -> list[LLMGatewayResponse]:
    return [
        LLMGatewayResponse(
            route="mock",
            inference_backend=None,
            model_call_id="stage12a-mock-call-0",
            assistant_message={"role": "assistant", "content": "read calculator"},
            tool_calls=[
                {
                    "tool_call_id": "stage12a-mock-read",
                    "tool_name": "read_file",
                    "arguments": {"path": "calculator.py"},
                }
            ],
            prompt_ids=[101],
            output_token_ids=[60_001],
            output_logprobs=[-0.61],
            response_mask=[1],
            stop_reason="tool_calls",
            usage={"input_tokens": 1, "output_tokens": 1},
        ),
        LLMGatewayResponse(
            route="mock",
            inference_backend=None,
            model_call_id="stage12a-mock-call-1",
            assistant_message={"role": "assistant", "content": "edit calculator"},
            tool_calls=[
                {
                    "tool_call_id": "stage12a-mock-edit",
                    "tool_name": "edit_file",
                    "arguments": {"path": "calculator.py", "old_text": OLD_DIVIDE, "new_text": NEW_DIVIDE},
                }
            ],
            prompt_ids=[102],
            output_token_ids=[60_002],
            output_logprobs=[-0.62],
            response_mask=[1],
            stop_reason="tool_calls",
            usage={"input_tokens": 1, "output_tokens": 1},
        ),
        LLMGatewayResponse(
            route="mock",
            inference_backend=None,
            model_call_id="stage12a-mock-call-2",
            assistant_message={"role": "assistant", "content": "final"},
            tool_calls=[],
            prompt_ids=[103],
            output_token_ids=[60_003],
            output_logprobs=[-0.63],
            response_mask=[1],
            stop_reason="stop",
            usage={"input_tokens": 1, "output_tokens": 1},
        ),
    ]


def _mock_request() -> RepoHarnessEpisodeRequest:
    return RepoHarnessEpisodeRequest(
        episode_id="stage12a-mock-episode",
        run_id="stage12a-mock-run",
        task_id="stage12a-mock-task",
        llm_gateway_route="mock",
        inference_backend=None,
        raw_prompt=_sample_kwargs()["raw_prompt"],
        task_ref={"task_ref": "rh://task/stage12a-mock-task"},
        run_mode="training_fast",
        budgets={
            "max_turns": 6,
            "max_model_calls": 6,
            "max_tool_calls": 6,
            "max_output_tokens": 32,
            "max_prompt_tokens": 128,
            "max_artifact_bytes": 2_000_000,
        },
    )


def test_stage12a_real_episode_runtime_smoke_with_mock_route_is_diagnostic_only(tmp_path: Path) -> None:
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path))
    result = asyncio.run(runtime.run_episode(_mock_request(), llm_gateway=FakeLLMGateway(_mock_gateway_responses())))

    assert result.status == "succeeded"
    assert result.invalid_for_training is False
    assert result.invalid_for_online_rl is True
    assert result.status_reason == "non_verl_route_invalid_for_online_rl"
    assert result.training_view.reward_score is not None
    assert result.training_view.extra_fields["repo_harness_llm_gateway_route"] == "mock"
    assert result.resource_summary is not None
    assert result.resource_summary.execution_mode == "real_episode"
    assert result.resource_summary.workspace_backend == "local_process"
    assert result.timing_summary is not None
    assert result.timing_summary.tool_call_count >= 2
    assert result.verifier_summary is not None
    assert result.verifier_summary.status == "accepted"
    assert result.reward is not None
    assert result.reward.score == 1.0
    assert result.generation_records[0].gateway_route == "mock"
    assert [span.source_type for span in result.training_view.response_spans].count("tool_observation") >= 2
    with pytest.raises(ValueError, match="non_verl_route_invalid_for_online_rl"):
        validate_training_view_for_online_rl(result.training_view, require_explicit_eligibility=True)


def test_stage12a_repo_harness_verl_agent_loop_real_episode_smoke(tmp_path: Path) -> None:
    _require_real_verl()
    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop
    from verl.workers.rollout.replica import TokenOutput

    fake_server = QueueingFakeLLMServerClient(TokenOutput, _verl_token_outputs())
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path))
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=_trainer_config(),
        server_manager=fake_server,
        tokenizer=FakeTokenizer(),
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap({"apply_chat_template_kwargs": {}}),
        runtime=runtime,
        inference_backend="sglang",
    )

    output = asyncio.run(loop.run({"max_new_tokens": 16, "temperature": 0.0}, **_sample_kwargs()))

    assert output.__class__.__name__ == "AgentLoopOutput"
    assert output.response_ids == [50_001, 77_001, 77_002, 50_002, 77_001, 77_002, 50_003]
    assert output.response_mask == [1, 0, 0, 1, 0, 0, 1]
    assert output.response_logprobs == [-0.51, 0.0, 0.0, -0.52, 0.0, 0.0, -0.53]
    assert output.reward_score == 1.0
    assert output.extra_fields["repo_harness_llm_gateway_route"] == "verl"
    assert output.extra_fields["repo_harness_status"] == "succeeded"
    assert "raw_prompt" not in output.extra_fields
    assert "repo_harness_tool_calls" not in output.extra_fields
    assert len(fake_server.calls) == 3
    assert fake_server.calls[0]["request_id"] == "stage12a-buggy-calculator-uid-stage12a-s1-i0-g12"
    assert fake_server.calls[0]["sampling_params"]["max_new_tokens"] == 16
    assert fake_server.calls[0]["sampling_params"]["max_output_tokens"] == 16

    run_dirs = list((tmp_path / "stage12a_runs").iterdir())
    assert len(run_dirs) == 1
    manifest = json.loads((run_dirs[0] / "artifacts.json").read_text(encoding="utf-8"))
    artifact_kinds = {artifact["kind"] for artifact in manifest["artifacts"]}
    assert {"assistant_message", "read_file", "final_verifier", "reward_metadata"}.issubset(artifact_kinds)
    assert "ValueError" not in (BUGGY_CALCULATOR_SOURCE / "calculator.py").read_text(encoding="utf-8")
