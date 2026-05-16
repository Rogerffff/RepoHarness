import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import TrainingView
from repo_harness_verl import (
    VerlVisibilityError,
    training_view_to_agent_loop_output,
    validate_agent_loop_output_extra_fields,
    validate_postprocessed_extra_fields,
    validate_transfer_queue_field_visibility,
    validate_transfer_queue_kwargs,
)

from verl_reference_stubs import FakeTokenizer, RolloutConfig, install_reference_verl_stubs


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _formal_training_view() -> TrainingView:
    payload = _load_json("canonical_training_view.json")
    payload["extra_fields"] = {**payload["extra_fields"], "repo_harness_llm_gateway_route": "verl"}
    payload["online_rl_eligible"] = True
    return TrainingView.model_validate(payload)


def _build_worker(monkeypatch, *, prompt_length: int = 16, response_length: int = 12):
    install_reference_verl_stubs(monkeypatch)
    from verl.experimental.agent_loop.agent_loop import AgentLoopWorker

    worker = AgentLoopWorker.__new__(AgentLoopWorker)
    worker.tokenizer = FakeTokenizer()
    worker.rollout_config = RolloutConfig(prompt_length=prompt_length, response_length=response_length)
    worker.processor = None
    worker.reward_loop_worker_handles = None
    worker.distillation_enabled = False
    worker._compute_score = _noop_async
    worker._compute_teacher_logprobs = _noop_async
    return worker


async def _noop_async(*args, **kwargs) -> None:
    return None


def test_stage10_converter_extra_fields_do_not_include_raw_prompt(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    output = training_view_to_agent_loop_output(_formal_training_view())

    validate_agent_loop_output_extra_fields(output.extra_fields)
    assert "raw_prompt" not in output.extra_fields


def test_stage10_agent_loop_postprocess_raw_prompt_visibility(monkeypatch) -> None:
    worker = _build_worker(monkeypatch)
    output = training_view_to_agent_loop_output(_formal_training_view())

    internal = asyncio.run(
        worker._agent_loop_postprocess(
            output,
            validate=False,
            raw_prompt=[{"role": "user", "content": "please fix the visible task"}],
        )
    )

    assert internal.extra_fields["raw_prompt"][0]["role"] == "user"
    validate_postprocessed_extra_fields(internal.extra_fields)
    assert internal.prompt_ids.shape == (1, 16)
    assert internal.response_ids.shape == (1, 12)
    assert internal.response_mask.shape == (1, 12)
    assert internal.response_logprobs.shape == (1, 12)


def test_stage10_postprocessed_extra_fields_reject_hidden_raw_prompt(monkeypatch) -> None:
    worker = _build_worker(monkeypatch)
    output = training_view_to_agent_loop_output(_formal_training_view())

    internal = asyncio.run(
        worker._agent_loop_postprocess(
            output,
            validate=False,
            raw_prompt=[{"role": "user", "content": "hidden_verifier must not leak"}],
        )
    )

    with pytest.raises(VerlVisibilityError, match="hidden_verifier"):
        validate_postprocessed_extra_fields(internal.extra_fields)


def test_stage10_transfer_queue_kwargs_are_default_deny_and_protect_reserved_keys() -> None:
    validate_transfer_queue_kwargs({"raw_prompt": [{"role": "user", "content": "visible"}]})

    with pytest.raises(VerlVisibilityError, match="transfer_queue_kwargs_reserved_key: responses"):
        validate_transfer_queue_kwargs({"responses": [1, 2, 3]})

    with pytest.raises(VerlVisibilityError, match="transfer_queue_kwargs_not_allowlisted"):
        validate_transfer_queue_kwargs({"dataset_internal_path": "runs/example"})

    with pytest.raises(VerlVisibilityError, match="gold_patch"):
        validate_transfer_queue_kwargs({"raw_prompt": [{"role": "user", "content": "gold_patch"}]})


@pytest.mark.parametrize(
    "field_name",
    [
        "hidden_verifier",
        "gold_patch",
        "accepted_label",
        "provider_secret",
        "evaluator_only_logs",
        "complete_reward_metadata",
        "reward_extra_info",
        "reward_extra_keys",
        "extra_info",
        "ground_truth",
        "providerSecret",
        "completeRewardMetadata",
    ],
)
def test_stage10_transfer_queue_kwargs_reject_forbidden_field_names_even_if_allowlisted(field_name: str) -> None:
    with pytest.raises(VerlVisibilityError, match="forbidden_transfer_queue_field_name"):
        validate_transfer_queue_kwargs({field_name: "safe_value"}, allowed_keys={field_name})


def test_stage10_transfer_queue_field_checks_top_level_raw_prompt_and_extra_fields(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    output = training_view_to_agent_loop_output(_formal_training_view())
    field = output.as_dict()
    field.update({"raw_prompt": [{"role": "user", "content": "visible"}]})

    validate_transfer_queue_field_visibility(field)

    bad_field = dict(field)
    bad_field["raw_prompt"] = [{"role": "user", "content": "provider_secret"}]
    with pytest.raises(VerlVisibilityError, match="provider_secret"):
        validate_transfer_queue_field_visibility(bad_field)

    bad_field = dict(field)
    bad_field["extra_fields"] = {**field["extra_fields"], "repo_harness_audit_ref": "rh://audit/full"}
    with pytest.raises(VerlVisibilityError, match="forbidden batch extra field"):
        validate_transfer_queue_field_visibility(bad_field)


@pytest.mark.parametrize(
    "field_name",
    [
        "hidden_verifier",
        "gold_patch",
        "accepted_label",
        "provider_secret",
        "evaluator_only_logs",
        "complete_reward_metadata",
        "reward_extra_info",
        "reward_extra_keys",
        "extra_info",
        "ground_truth",
        "acceptedLabel",
        "providerSecret",
    ],
)
def test_stage10_transfer_queue_field_rejects_forbidden_top_level_field_names(
    monkeypatch,
    field_name: str,
) -> None:
    install_reference_verl_stubs(monkeypatch)
    output = training_view_to_agent_loop_output(_formal_training_view())
    field = output.as_dict()
    field[field_name] = "safe_value"

    with pytest.raises(VerlVisibilityError, match="forbidden_transfer_queue_field_name"):
        validate_transfer_queue_field_visibility(field)


@pytest.mark.parametrize(
    "payload",
    [
        {"reward_model": {"ground_truth": "answer"}},
        {"safe": {"reward_extra_info": {"score": 1}}},
        {"safe": {"groundTruth": "answer"}},
        {"safe": {"nested": {"completeRewardMetadata": "secret"}}},
        {"safe": {"nested": "reward_extra_keys"}},
    ],
)
def test_stage10_transfer_queue_field_rejects_nested_forbidden_reward_metadata(payload: dict[str, object]) -> None:
    with pytest.raises(VerlVisibilityError, match="forbidden_transfer_queue_field"):
        validate_transfer_queue_field_visibility({"visible_dataset_field": payload})
