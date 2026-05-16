from __future__ import annotations

import asyncio
from types import SimpleNamespace
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import RepoHarnessRuntime
from repo_harness_verl import (
    VerlVisibilityError,
    validate_dataproto_shapes,
    validate_dataproto_visibility,
    validate_postprocessed_extra_fields,
    validate_transfer_queue_field_visibility,
)

from test_repo_harness_verl_stage12a_real_episode_smoke import (
    ConfigWrap,
    FakeTokenizer,
    QueueingFakeLLMServerClient,
    _require_real_verl,
    _runtime_options,
    _sample_kwargs,
    _trainer_config,
    _verl_token_outputs,
)


async def _noop_async(*args: Any, **kwargs: Any) -> None:
    return None


def _build_worker() -> Any:
    from verl.experimental.agent_loop.agent_loop import AgentLoopWorker

    worker = AgentLoopWorker.__new__(AgentLoopWorker)
    worker.tokenizer = FakeTokenizer()
    worker.rollout_config = SimpleNamespace(prompt_length=96, response_length=32)
    worker.processor = None
    worker.reward_loop_worker_handles = None
    worker.distillation_enabled = False
    worker._compute_score = _noop_async
    worker._compute_teacher_logprobs = _noop_async
    return worker


def _agent_loop_output(tmp_path: Path) -> Any:
    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop
    from verl.workers.rollout.replica import TokenOutput

    fake_server = QueueingFakeLLMServerClient(TokenOutput, _verl_token_outputs())
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=_trainer_config(),
        server_manager=fake_server,
        tokenizer=FakeTokenizer(),
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap({"apply_chat_template_kwargs": {}}),
        runtime=RepoHarnessRuntime(_runtime_options(tmp_path)),
        inference_backend="sglang",
    )
    return asyncio.run(loop.run({"max_new_tokens": 16, "temperature": 0.0}, **_sample_kwargs()))


def test_stage12a_real_agent_loop_output_passes_transfer_queue_visibility(tmp_path: Path) -> None:
    _require_real_verl()
    output = _agent_loop_output(tmp_path)
    field = output.as_dict()
    field.update({"raw_prompt": _sample_kwargs()["raw_prompt"]})

    validate_transfer_queue_field_visibility(field)

    bad_field = dict(field)
    bad_field["visible_dataset_field"] = {"reward_model": {"ground_truth": "answer"}}
    with pytest.raises(VerlVisibilityError, match="forbidden_transfer_queue_field"):
        validate_transfer_queue_field_visibility(bad_field)


def test_stage12a_real_agent_loop_postprocess_and_dataproto_visibility(tmp_path: Path) -> None:
    _require_real_verl()
    output = _agent_loop_output(tmp_path)
    worker = _build_worker()

    internal = asyncio.run(
        worker._agent_loop_postprocess(
            output,
            validate=False,
            raw_prompt=_sample_kwargs()["raw_prompt"],
        )
    )
    validate_postprocessed_extra_fields(internal.extra_fields)

    data_proto = worker._postprocess([internal], input_non_tensor_batch=None, validate=False)
    validate_dataproto_shapes(data_proto, batch_size=1, prompt_length=96, response_length=32)
    validate_dataproto_visibility(data_proto)
    assert data_proto.batch["rollout_log_probs"].shape == (1, 32)
    assert data_proto.batch["rm_scores"].shape == (1, 32)
    assert data_proto.non_tensor_batch["repo_harness_llm_gateway_route"].tolist() == ["verl"]
    assert data_proto.non_tensor_batch["raw_prompt"].tolist()[0][0]["role"] == "user"
    assert "repo_harness_tool_calls" not in data_proto.non_tensor_batch

    data_proto.non_tensor_batch["reward_model"] = [{"groundTruth": "answer"}]
    with pytest.raises(VerlVisibilityError, match="forbidden_transfer_queue_field"):
        validate_dataproto_visibility(data_proto)


def test_stage12a_postprocess_rejects_hidden_raw_prompt(tmp_path: Path) -> None:
    _require_real_verl()
    output = _agent_loop_output(tmp_path)
    worker = _build_worker()

    internal = asyncio.run(
        worker._agent_loop_postprocess(
            output,
            validate=False,
            raw_prompt=[{"role": "user", "content": "hidden_verifier must stay evaluator-only"}],
        )
    )

    with pytest.raises(VerlVisibilityError, match="hidden_verifier"):
        validate_postprocessed_extra_fields(internal.extra_fields)
