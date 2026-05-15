import json
from pathlib import Path
from typing import Any


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
SPAN_REQUIRED_FIELDS = {
    "start",
    "end",
    "source_type",
    "model_call_id",
    "tool_call_id",
    "artifact_ref",
    "response_mask_value",
    "logprob_policy",
    "policy_version",
    "global_steps",
    "min_global_steps",
    "max_global_steps",
}
INCLUDED_SPAN_TYPES = {"assistant_generation", "tool_observation", "environment_observation"}
EXCLUDED_SPAN_TYPES = {"padding_excluded", "truncated_excluded"}


def _load_json(name: str) -> Any:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _training_view(payload: dict[str, Any]) -> dict[str, Any]:
    return payload["training_view"] if "training_view" in payload else payload


def _assert_training_view_shape(view: dict[str, Any], *, expect_valid_for_training: bool) -> None:
    prompt_ids = view["prompt_ids"]
    response_ids = view["response_ids"]
    response_mask = view["response_mask"]
    response_logprobs = view["response_logprobs"]
    limits = view.get("rollout_limits", {"prompt_length": 10**9, "response_length": 10**9})

    assert len(prompt_ids) <= limits["prompt_length"]
    assert len(response_ids) == len(response_mask)
    assert response_logprobs is not None
    assert len(response_logprobs) == len(response_ids)

    if expect_valid_for_training:
        assert response_ids
        assert len(response_ids) <= limits["response_length"]

    for mask, logprob in zip(response_mask, response_logprobs):
        if mask == 0:
            assert logprob == 0.0
        else:
            assert mask == 1


def _assert_response_spans_cover_included_tokens(view: dict[str, Any]) -> None:
    response_ids = view["response_ids"]
    response_mask = view["response_mask"]
    spans = view["response_spans"]
    covered: set[int] = set()

    for span in spans:
        assert SPAN_REQUIRED_FIELDS.issubset(span)
        assert span["source_type"] in INCLUDED_SPAN_TYPES | EXCLUDED_SPAN_TYPES
        assert 0 <= span["start"] <= span["end"] <= len(response_ids)
        assert span["min_global_steps"] <= span["global_steps"] <= span["max_global_steps"]

        if span["source_type"] in EXCLUDED_SPAN_TYPES:
            assert span["start"] == span["end"]
            assert span["response_mask_value"] is None
            continue

        expected_mask = 1 if span["source_type"] == "assistant_generation" else 0
        assert span["response_mask_value"] == expected_mask
        for index in range(span["start"], span["end"]):
            covered.add(index)
            assert response_mask[index] == expected_mask

    assert covered == set(range(len(response_ids)))


def test_stage0h_valid_training_views_obey_token_mask_and_logprob_shape_rules() -> None:
    for fixture_name in [
        "canonical_training_view.json",
        "canonical_episode_result.json",
        "canonical_multiturn_tool_episode_result.json",
    ]:
        view = _training_view(_load_json(fixture_name))
        _assert_training_view_shape(view, expect_valid_for_training=True)
        _assert_response_spans_cover_included_tokens(view)


def test_stage0h_multiturn_fixture_tracks_tool_environment_and_excluded_spans() -> None:
    view = _load_json("canonical_multiturn_tool_episode_result.json")["training_view"]
    source_types = {span["source_type"] for span in view["response_spans"]}

    assert "assistant_generation" in source_types
    assert "tool_observation" in source_types
    assert "environment_observation" in source_types
    assert "padding_excluded" in source_types
    assert "truncated_excluded" in source_types

    model_call_ids = {record["model_call_id"] for record in _load_json("canonical_multiturn_tool_episode_result.json")["generation_records"]}
    span_model_call_ids = {
        span["model_call_id"]
        for span in view["response_spans"]
        if span["source_type"] == "assistant_generation"
    }
    assert span_model_call_ids == model_call_ids


def test_stage0h_response_overflow_fixture_is_invalid_and_not_silently_truncated() -> None:
    payload = _load_json("canonical_response_overflow_invalid_result.json")
    view = payload["training_view"]

    assert payload["invalid_for_training"] is True
    assert payload["invalid_for_online_rl"] is True
    assert payload["status_reason"] == "response_length_exceeded"
    assert payload["budget_consumption"]["stop_reason"] == "response_length_exceeded"
    assert len(view["response_ids"]) > view["rollout_limits"]["response_length"]
    assert payload["audit_diagnostics"][0]["code"] == "response_length_exceeded"


def test_stage0h_empty_response_with_reward_is_blocked_before_training() -> None:
    payload = _load_json("canonical_empty_response_invalid_result.json")
    view = payload["training_view"]

    assert payload["attempted_reward_score"] == 1.0
    assert payload["invalid_for_training"] is True
    assert payload["status_reason"] == "empty_response_with_reward_blocked"
    assert view["response_ids"] == []
    assert view["reward_score"] is None
    assert view["extra_fields"]["repo_harness_invalid_for_training"] is True


def test_stage0h_mixed_logprob_formal_batch_is_rejected() -> None:
    batch = _load_json("canonical_mixed_logprob_batch_rejected.json")
    samples = batch["samples"]

    assert batch["formal_online_rl_batch"] is True
    assert batch["expected_status"] == "rejected"
    assert batch["expected_rejection_reason"] == "mixed_response_logprobs_in_formal_batch"
    assert any(sample["response_logprobs"] is None for sample in samples)
    assert any(sample["response_logprobs"] is not None for sample in samples)
    missing = [sample for sample in samples if sample["response_logprobs"] is None]
    assert all(sample["invalid_for_training"] is True for sample in missing)
