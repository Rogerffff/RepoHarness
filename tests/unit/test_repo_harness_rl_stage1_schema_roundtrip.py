import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from repo_harness.rl import (
    AuditPathAccessDeniedFixture,
    AuditRef,
    LLMGatewayRequest,
    LLMGatewayResponse,
    MixedLogprobBatchRejectionFixture,
    RepoHarnessEpisodeRequest,
    RepoHarnessEpisodeResult,
    TrainingView,
    validate_formal_online_rl_batch,
    validate_training_view_for_online_rl,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


ROUNDTRIP_CASES = {
    "canonical_episode_request.json": RepoHarnessEpisodeRequest,
    "canonical_episode_result.json": RepoHarnessEpisodeResult,
    "canonical_training_view.json": TrainingView,
    "canonical_audit_ref.json": AuditRef,
    "canonical_llm_gateway_request.json": LLMGatewayRequest,
    "canonical_llm_gateway_response.json": LLMGatewayResponse,
    "canonical_multiturn_tool_episode_result.json": RepoHarnessEpisodeResult,
    "canonical_response_overflow_invalid_result.json": RepoHarnessEpisodeResult,
    "canonical_empty_response_invalid_result.json": RepoHarnessEpisodeResult,
    "canonical_mixed_logprob_batch_rejected.json": MixedLogprobBatchRejectionFixture,
    "canonical_audit_path_access_denied.json": AuditPathAccessDeniedFixture,
}


@pytest.mark.parametrize(("fixture_name", "model_cls"), sorted(ROUNDTRIP_CASES.items()))
def test_stage1_schema_roundtrips_stage0h_fixtures(fixture_name: str, model_cls: type[Any]) -> None:
    payload = _load_json(fixture_name)
    parsed = model_cls.model_validate(payload)

    dumped = parsed.model_dump(mode="json", exclude_unset=True)
    assert dumped == payload
    assert model_cls.model_validate(dumped).model_dump(mode="json", exclude_unset=True) == payload


def test_stage1_training_view_rejects_unknown_fields() -> None:
    payload = _load_json("canonical_training_view.json")
    payload["unexpected_field"] = "must not pass through"

    with pytest.raises(ValidationError, match="unexpected_field"):
        TrainingView.model_validate(payload)


def test_stage1_episode_request_rejects_unknown_route() -> None:
    payload = _load_json("canonical_episode_request.json")
    payload["llm_gateway_route"] = "verl_llm_server_client"

    with pytest.raises(ValidationError, match="llm_gateway_route"):
        RepoHarnessEpisodeRequest.model_validate(payload)


def test_stage1_training_view_online_rl_helper_rejects_invalid_fixture_shapes() -> None:
    overflow = _load_json("canonical_response_overflow_invalid_result.json")["training_view"]
    empty = _load_json("canonical_empty_response_invalid_result.json")["training_view"]

    with pytest.raises(ValueError, match="response_length_exceeded"):
        validate_training_view_for_online_rl(overflow)
    with pytest.raises(ValueError, match="empty_response_with_reward_blocked"):
        validate_training_view_for_online_rl(empty)


@pytest.mark.parametrize(
    ("updates", "expected_reason"),
    [
        ({"online_rl_eligible": False}, "training_view_marked_ineligible_for_online_rl"),
        (
            {"extra_fields": {"repo_harness_invalid_for_online_rl": True}},
            "invalid_for_online_rl",
        ),
        ({"online_rl_eligible": None}, "training_view_missing_online_rl_eligibility"),
    ],
)
def test_stage1_formal_online_rl_batch_rejects_training_view_invalid_flags(
    updates: dict[str, Any],
    expected_reason: str,
) -> None:
    payload = _load_json("canonical_training_view.json")
    payload["extra_fields"] = {**payload["extra_fields"], "repo_harness_llm_gateway_route": "verl"}
    if "extra_fields" in updates:
        payload["extra_fields"] = {**payload["extra_fields"], **updates["extra_fields"]}
    if "online_rl_eligible" in updates:
        payload["online_rl_eligible"] = updates["online_rl_eligible"]
    view = TrainingView.model_validate(payload)

    with pytest.raises(ValueError, match=expected_reason):
        validate_formal_online_rl_batch([view], formal_online_rl_batch=True)


def test_stage1_mixed_logprob_is_batch_level_rejection() -> None:
    fixture = MixedLogprobBatchRejectionFixture.model_validate(_load_json("canonical_mixed_logprob_batch_rejected.json"))

    with pytest.raises(ValueError, match=fixture.expected_rejection_reason):
        validate_formal_online_rl_batch(
            fixture.samples,
            formal_online_rl_batch=fixture.formal_online_rl_batch,
        )

    assert fixture.samples[0].response_logprobs is not None
    assert fixture.samples[1].response_logprobs is None


@pytest.mark.parametrize("status", ["invalid_task", "infrastructure_error"])
def test_stage1_episode_result_accepts_stage2_runtime_boundary_statuses(status: str) -> None:
    payload = _load_json("canonical_episode_result.json")
    payload["status"] = status
    payload["status_reason"] = status
    payload["invalid_for_training"] = True
    payload["invalid_for_online_rl"] = True

    parsed = RepoHarnessEpisodeResult.model_validate(payload)
    assert parsed.status == status
    assert parsed.invalid_for_training is True


@pytest.mark.parametrize("status", ["invalid_task", "infrastructure_error"])
def test_stage1_episode_result_rejects_runtime_boundary_statuses_as_trainable(status: str) -> None:
    payload = _load_json("canonical_episode_result.json")
    payload["status"] = status
    payload["status_reason"] = status

    with pytest.raises(ValidationError, match="invalid_for_training=true"):
        RepoHarnessEpisodeResult.model_validate(payload)
