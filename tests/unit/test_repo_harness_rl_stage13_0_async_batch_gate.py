from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import (
    RepoHarnessEpisodeResult,
    RewardFinalityFacts,
    formal_async_online_rl_sample_from_episode_result,
    validate_formal_async_online_rl_batch,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_result() -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text())
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return RepoHarnessEpisodeResult.model_validate(payload)


def test_stage13_0_formal_async_batch_accepts_final_sync_episode_projection() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    parsed = validate_formal_async_online_rl_batch([sample])

    assert parsed[0].reward_finality.reward_score_source == "trusted_final_verifier"


def test_stage13_0_formal_async_batch_rejects_pending_reward() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(_episode_result())
    pending = RewardFinalityFacts(
        reward_state="pending_verifier",
        reward_score=None,
        reward_score_source="unknown",
        final_verifier_status="unknown",
        final_verifier_ref=None,
        reward_metadata_ref=None,
        reward_job_id=sample.sample_identity.reward_job_id,
        sample_attempt_id=sample.sample_identity.sample_attempt_id,
        trajectory_digest=sample.sample_identity.trajectory_digest,
        generation_record_digest=sample.sample_identity.generation_record_digest,
        invalid_reason="pending",
    )
    sample = sample.model_copy(update={"reward_finality": pending})

    with pytest.raises(ValueError, match="reward_not_final"):
        validate_formal_async_online_rl_batch([sample])


def test_stage13_0_formal_async_batch_rejects_missing_visibility_scan() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="missing",
    )

    with pytest.raises(ValueError, match="visibility_scan_not_passed"):
        validate_formal_async_online_rl_batch([sample])


def test_stage13_0_formal_async_batch_rejects_missing_generation_records() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    forged = sample.model_copy(update={"sample": sample.sample.model_copy(update={"generation_records": []})})

    with pytest.raises(ValueError, match="missing_generation_records"):
        validate_formal_async_online_rl_batch([forged])


def test_stage13_0_formal_async_batch_rejects_forged_response_tokens() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    response_ids = [*sample.sample.response_ids]
    response_ids[0] = response_ids[0] + 1
    forged = sample.model_copy(update={"sample": sample.sample.model_copy(update={"response_ids": response_ids})})

    with pytest.raises(ValueError, match="tokens_mismatch"):
        validate_formal_async_online_rl_batch([forged])


def test_stage13_0_formal_async_batch_rejects_forged_prompt_digest_mismatch() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    forged_sample = sample.sample.model_copy(update={"prompt_ids": [999, *sample.sample.prompt_ids]})
    forged = sample.model_copy(update={"sample": forged_sample})

    with pytest.raises(ValueError, match="trajectory_digest_mismatch_current_sample"):
        validate_formal_async_online_rl_batch([forged])


def test_stage13_0_formal_async_batch_rejects_forged_generation_record_prompt_ids() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    records = [*sample.sample.generation_records]
    records[0] = records[0].model_copy(update={"prompt_ids": [999, *records[0].prompt_ids]})
    forged = sample.model_copy(update={"sample": sample.sample.model_copy(update={"generation_records": records})})

    with pytest.raises(ValueError, match="generation_record_digest_mismatch_current_sample"):
        validate_formal_async_online_rl_batch([forged])


def test_stage13_0_formal_async_batch_rejects_forged_generation_record_policy_version() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    records = [*sample.sample.generation_records]
    records[0] = records[0].model_copy(update={"policy_version": {"policy": "forged"}})
    forged = sample.model_copy(update={"sample": sample.sample.model_copy(update={"generation_records": records})})

    with pytest.raises(ValueError, match="generation_record_digest_mismatch_current_sample"):
        validate_formal_async_online_rl_batch([forged])


def test_stage13_0_formal_async_batch_rejects_forged_generation_record_schema_version() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    records = [*sample.sample.generation_records]
    records[0] = records[0].model_copy(update={"schema_version": "forged_generation_record_schema"})
    forged = sample.model_copy(update={"sample": sample.sample.model_copy(update={"generation_records": records})})

    with pytest.raises(ValueError, match="generation_record_digest_mismatch_current_sample"):
        validate_formal_async_online_rl_batch([forged])


@pytest.mark.parametrize(
    "policy_version",
    [
        {"ground_truth": "secret"},
        {"reward_extra_info": {"score": 1.0}},
        {"nested": {"hidden_verifier": "do not show"}},
    ],
)
def test_stage13_0_formal_async_batch_rejects_hidden_policy_version_markers(
    policy_version: dict[str, object],
) -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    identity = sample.sample_identity.model_copy(update={"policy_version": policy_version})
    finality = sample.reward_finality.model_copy(
        update={
            "sample_attempt_id": identity.sample_attempt_id,
            "reward_job_id": identity.reward_job_id,
            "generation_record_digest": identity.generation_record_digest,
            "trajectory_digest": identity.trajectory_digest,
        }
    )
    forged = sample.model_copy(update={"sample_identity": identity, "reward_finality": finality})

    with pytest.raises(ValueError, match="evaluator-only content"):
        validate_formal_async_online_rl_batch([forged])


def test_stage13_0_formal_async_batch_rejects_generation_record_hidden_policy_version() -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    records = [*sample.sample.generation_records]
    records[0] = records[0].model_copy(update={"policy_version": {"ground_truth": "secret"}})
    forged = sample.model_copy(update={"sample": sample.sample.model_copy(update={"generation_records": records})})

    with pytest.raises(ValueError, match="evaluator-only content"):
        validate_formal_async_online_rl_batch([forged])


@pytest.mark.parametrize(
    "identity_updates",
    [
        {"task_id": "forged-task"},
        {"dataset_uid": "forged-dataset"},
        {"rollout_uid": "forged-rollout"},
        {"policy_version": {"policy": "forged"}},
        {"global_steps": 1, "min_global_steps": 1, "max_global_steps": 1},
    ],
)
def test_stage13_0_formal_async_batch_rejects_forged_sample_identity_facts(
    identity_updates: dict[str, object],
) -> None:
    sample = formal_async_online_rl_sample_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
    )
    identity = sample.sample_identity.model_copy(update=identity_updates)
    finality = sample.reward_finality.model_copy(
        update={
            "sample_attempt_id": identity.sample_attempt_id,
            "reward_job_id": identity.reward_job_id,
            "generation_record_digest": identity.generation_record_digest,
            "trajectory_digest": identity.trajectory_digest,
        }
    )
    forged = sample.model_copy(update={"sample_identity": identity, "reward_finality": finality})

    with pytest.raises(ValueError, match="trajectory_digest_mismatch_current_sample"):
        validate_formal_async_online_rl_batch([forged])
