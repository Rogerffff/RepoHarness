from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from repo_harness.rl import FormalOnlineRLSample, RepoHarnessEpisodeResult, validate_formal_online_rl_batch


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _canonical_episode_payload() -> dict[str, Any]:
    payload = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return payload


def _formal_sample_from_canonical() -> FormalOnlineRLSample:
    result = RepoHarnessEpisodeResult.model_validate(_canonical_episode_payload())
    return FormalOnlineRLSample(
        sample_id=result.episode_id,
        route="verl",
        prompt_ids=result.training_view.prompt_ids,
        response_ids=result.training_view.response_ids,
        response_mask=result.training_view.response_mask,
        response_logprobs=result.training_view.response_logprobs,
        response_spans=result.training_view.response_spans,
        generation_records=result.generation_records,
        reward_score=result.training_view.reward_score,
    )


def test_stage12_5_formal_batch_rejects_standalone_sample_without_token_provenance() -> None:
    sample = FormalOnlineRLSample(
        sample_id="no-provenance",
        route="verl",
        prompt_ids=[1],
        response_ids=[2],
        response_mask=[1],
        response_logprobs=[-0.1],
        reward_score=1.0,
    )

    with pytest.raises(ValueError, match="missing_generation_records_for_formal_online_rl_sample"):
        validate_formal_online_rl_batch([sample])


def test_stage12_5_trainable_episode_result_requires_generation_records() -> None:
    payload = _canonical_episode_payload()
    payload["generation_records"] = []

    with pytest.raises(ValidationError, match="missing_generation_records_for_formal_online_rl_sample"):
        RepoHarnessEpisodeResult.model_validate(payload)


def test_stage12_5_formal_batch_accepts_generation_record_backed_sample() -> None:
    parsed = validate_formal_online_rl_batch([_formal_sample_from_canonical()])

    assert parsed[0].sample_id == "stage0h-episode-success"


def test_stage12_5_formal_batch_rejects_forged_response_tokens() -> None:
    sample = _formal_sample_from_canonical()
    forged_ids = list(sample.response_ids)
    forged_ids[0] = 999
    forged = sample.model_copy(update={"response_ids": forged_ids})

    with pytest.raises(ValueError, match="assistant_generation_tokens_mismatch_generation_records"):
        validate_formal_online_rl_batch([forged])


def test_stage12_5_formal_batch_rejects_forged_response_logprobs() -> None:
    sample = _formal_sample_from_canonical()
    forged_logprobs = list(sample.response_logprobs or [])
    forged_logprobs[0] = -9.9
    forged = sample.model_copy(update={"response_logprobs": forged_logprobs})

    with pytest.raises(ValueError, match="assistant_generation_logprobs_mismatch_generation_records"):
        validate_formal_online_rl_batch([forged])


def test_stage12_5_formal_batch_rejects_excluded_only_zero_width_provenance() -> None:
    sample = _formal_sample_from_canonical()
    excluded_span = sample.response_spans[0].model_copy(
        update={
            "start": 0,
            "end": 0,
            "source_type": "padding_excluded",
            "model_call_id": None,
            "response_mask_value": None,
        }
    )
    empty_record = sample.generation_records[0].model_copy(
        update={
            "output_token_ids": [],
            "output_logprobs": [],
        }
    )
    forged = sample.model_copy(update={"response_spans": [excluded_span], "generation_records": [empty_record]})

    with pytest.raises(ValueError, match="response_spans must explain every response token"):
        validate_formal_online_rl_batch([forged])


def test_stage12_5_formal_batch_revalidates_model_copy_response_span_gaps() -> None:
    sample = _formal_sample_from_canonical()
    assistant_only = [
        span
        for span in sample.response_spans
        if span.source_type == "assistant_generation"
    ]
    forged = sample.model_copy(update={"response_spans": assistant_only})

    with pytest.raises(ValueError, match="response_spans must explain every response token"):
        validate_formal_online_rl_batch([forged])
