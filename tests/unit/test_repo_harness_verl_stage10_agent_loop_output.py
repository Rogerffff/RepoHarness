import json
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import RepoHarnessEpisodeResult, TrainingView
from repo_harness_verl import (
    VerlConversionError,
    episode_result_to_agent_loop_output,
    project_generation_records_route,
    training_view_to_agent_loop_output,
)

from verl_reference_stubs import install_reference_verl_stubs


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _formal_training_view_payload() -> dict[str, Any]:
    payload = _load_json("canonical_training_view.json")
    payload["extra_fields"] = {**payload["extra_fields"], "repo_harness_llm_gateway_route": "verl"}
    payload["online_rl_eligible"] = True
    return payload


def test_stage10_canonical_training_view_is_not_implicitly_formal_online_rl(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    view = TrainingView.model_validate(_load_json("canonical_training_view.json"))

    with pytest.raises(VerlConversionError, match="missing_llm_gateway_route_for_online_rl"):
        training_view_to_agent_loop_output(view)


def test_stage10_training_view_converts_to_real_reference_agent_loop_output(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    view = TrainingView.model_validate(_formal_training_view_payload())

    output = training_view_to_agent_loop_output(view, rollout_prompt_length=16, rollout_response_length=12)

    assert output.__class__.__name__ == "AgentLoopOutput"
    assert output.prompt_ids == view.prompt_ids
    assert output.response_ids == view.response_ids
    assert output.response_mask == view.response_mask
    assert output.response_logprobs == view.response_logprobs
    assert output.reward_score == view.reward_score
    assert output.metrics.generate_sequences == 2
    assert output.metrics.tool_calls == 1
    assert "raw_prompt" not in output.extra_fields

    as_dict = output.as_dict()
    assert as_dict["prompts"].shape == (4,)
    assert as_dict["responses"].shape == (5,)
    assert as_dict["response_mask"].shape == (5,)
    assert as_dict["rollout_log_probs"].shape == (5,)
    assert as_dict["rm_scores"].tolist()[-1] == view.reward_score
    assert as_dict["extra_fields"]["repo_harness_llm_gateway_route"] == "verl"


def test_stage10_episode_result_projects_route_only_when_all_generation_records_are_verl(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    payload = _load_json("canonical_episode_result.json")
    payload["training_view"]["online_rl_eligible"] = True
    result = RepoHarnessEpisodeResult.model_validate(payload)

    output = episode_result_to_agent_loop_output(result)

    assert output.extra_fields["repo_harness_llm_gateway_route"] == "verl"


def test_stage10_generation_record_route_projection_rejects_empty_or_mixed_routes() -> None:
    payload = _load_json("canonical_episode_result.json")
    records = payload["generation_records"]

    assert project_generation_records_route(records) == "verl"

    with pytest.raises(VerlConversionError, match="missing_generation_records"):
        project_generation_records_route([])

    records[1] = {**records[1], "gateway_route": "openai", "inference_backend": None}
    with pytest.raises(VerlConversionError, match="generation_records_route_must_all_be_verl"):
        project_generation_records_route(records)


def test_stage10_formal_converter_rejects_ineligible_missing_logprob_and_extra_metric(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    payload = _formal_training_view_payload()
    payload["online_rl_eligible"] = False

    with pytest.raises(VerlConversionError, match="training_view_marked_ineligible"):
        training_view_to_agent_loop_output(payload)

    payload = _formal_training_view_payload()
    payload["response_logprobs"] = None
    with pytest.raises(VerlConversionError, match="missing_response_logprobs"):
        training_view_to_agent_loop_output(payload)

    payload = _formal_training_view_payload()
    payload["verl_metrics"] = {**payload["verl_metrics"], "repo_harness_wall_seconds": 1.0}
    with pytest.raises(VerlConversionError, match="unsupported_verl_agent_loop_metrics"):
        training_view_to_agent_loop_output(payload)


def test_stage10_converter_rejects_forbidden_agent_loop_extra_field(monkeypatch) -> None:
    install_reference_verl_stubs(monkeypatch)
    payload = _formal_training_view_payload()
    payload["extra_fields"]["repo_harness_extra_unknown"] = "value"
    view = TrainingView.model_validate(payload)

    with pytest.raises(VerlConversionError, match="unsupported_agent_loop_extra_fields"):
        training_view_to_agent_loop_output(view)
