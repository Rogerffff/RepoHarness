import asyncio
import json
from types import SimpleNamespace
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import TrainingView
from repo_harness_verl import (
    VerlVisibilityError,
    training_view_to_agent_loop_output,
    validate_dataproto_shapes,
    validate_dataproto_visibility,
)

from verl_reference_stubs import FakeTokenizer, RolloutConfig, install_reference_verl_stubs


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _formal_training_view_payload(episode_suffix: str) -> dict[str, Any]:
    payload = _load_json("canonical_training_view.json")
    payload["online_rl_eligible"] = True
    payload["extra_fields"] = {
        **payload["extra_fields"],
        "repo_harness_episode_id": f"stage10-episode-{episode_suffix}",
        "repo_harness_run_id": f"stage10-run-{episode_suffix}",
        "repo_harness_llm_gateway_route": "verl",
    }
    return payload


def _canonical_generation_records() -> list[dict[str, Any]]:
    return _load_json("canonical_episode_result.json")["generation_records"]


def _formal_agent_loop_output(episode_suffix: str) -> Any:
    return training_view_to_agent_loop_output(
        TrainingView.model_validate(_formal_training_view_payload(episode_suffix)),
        generation_records=_canonical_generation_records(),
    )


async def _noop_async(*args, **kwargs) -> None:
    return None


def _build_worker(monkeypatch):
    install_reference_verl_stubs(monkeypatch)
    from verl.experimental.agent_loop.agent_loop import AgentLoopWorker

    worker = AgentLoopWorker.__new__(AgentLoopWorker)
    worker.tokenizer = FakeTokenizer()
    worker.rollout_config = RolloutConfig(prompt_length=16, response_length=12)
    worker.processor = None
    worker.reward_loop_worker_handles = None
    worker.distillation_enabled = False
    worker._compute_score = _noop_async
    worker._compute_teacher_logprobs = _noop_async
    return worker


def test_stage10_postprocess_builds_dataproto_shapes_and_visibility(monkeypatch) -> None:
    worker = _build_worker(monkeypatch)
    outputs = [_formal_agent_loop_output("a"), _formal_agent_loop_output("b")]

    internals = [
        asyncio.run(
            worker._agent_loop_postprocess(
                output,
                validate=False,
                raw_prompt=[{"role": "user", "content": f"visible prompt {index}"}],
            )
        )
        for index, output in enumerate(outputs)
    ]
    data_proto = worker._postprocess(internals, input_non_tensor_batch=None, validate=False)

    validate_dataproto_shapes(data_proto, batch_size=2, prompt_length=16, response_length=12)
    validate_dataproto_visibility(data_proto)
    assert data_proto.batch["rollout_log_probs"].shape == (2, 12)
    assert data_proto.batch["rm_scores"].shape == (2, 12)
    assert data_proto.non_tensor_batch["repo_harness_llm_gateway_route"].tolist() == ["verl", "verl"]
    assert data_proto.non_tensor_batch["raw_prompt"].tolist()[0][0]["role"] == "user"
    assert "metrics" in data_proto.meta_info


def test_stage10_dataproto_visibility_rejects_hidden_non_tensor_value(monkeypatch) -> None:
    worker = _build_worker(monkeypatch)
    output = _formal_agent_loop_output("hidden")
    internal = asyncio.run(
        worker._agent_loop_postprocess(
            output,
            validate=False,
            raw_prompt=[{"role": "user", "content": "visible"}],
        )
    )
    data_proto = worker._postprocess([internal], input_non_tensor_batch=None, validate=False)
    data_proto.non_tensor_batch["repo_harness_hidden_verifier"] = ["secret"]

    with pytest.raises(VerlVisibilityError, match="hidden_verifier"):
        validate_dataproto_visibility(data_proto)


@pytest.mark.parametrize(
    "non_tensor_batch",
    [
        {"reward_model": [{"ground_truth": "answer"}]},
        {"safe": [{"reward_extra_info": {"score": 1}}]},
        {"safe": [{"groundTruth": "answer"}]},
        {"safe": [{"nested": {"completeRewardMetadata": "secret"}}]},
    ],
)
def test_stage10_dataproto_visibility_rejects_nested_reward_metadata(non_tensor_batch: dict[str, object]) -> None:
    data_proto = SimpleNamespace(batch={}, non_tensor_batch=non_tensor_batch, meta_info={})

    with pytest.raises(VerlVisibilityError, match="forbidden_transfer_queue_field"):
        validate_dataproto_visibility(data_proto)
