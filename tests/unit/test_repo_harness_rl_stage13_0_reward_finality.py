from __future__ import annotations

import pytest

from repo_harness.rl import (
    RewardFinalityFacts,
    SampleIdentity,
    validate_reward_finality_for_policy_loss,
)


def _identity() -> SampleIdentity:
    return SampleIdentity(
        sample_id="sample-1",
        sample_attempt_id="attempt-0",
        episode_id="episode-1",
        run_id="run-1",
        task_id="task-1",
        dataset_index=0,
        uid="uid-1",
        global_steps=2,
        min_global_steps=1,
        max_global_steps=3,
        reward_job_id="reward-job-1",
        generation_record_digest="sha256:generation",
        trajectory_digest="sha256:trajectory",
    )


def _finality(**updates: object) -> RewardFinalityFacts:
    data = {
        "reward_state": "final_verifier_completed",
        "reward_score": 1.0,
        "reward_score_source": "trusted_final_verifier",
        "final_verifier_status": "accepted",
        "verifier_outcome": "accepted",
        "final_verifier_ref": "rh://audit/final-verifier",
        "reward_metadata_ref": "rh://audit/reward-metadata",
        "reward_job_id": "reward-job-1",
        "sample_attempt_id": "attempt-0",
        "trajectory_digest": "sha256:trajectory",
        "generation_record_digest": "sha256:generation",
    }
    data.update(updates)
    return RewardFinalityFacts.model_validate(data)


def test_stage13_0_reward_finality_accepts_trusted_final_verifier_result() -> None:
    finality = validate_reward_finality_for_policy_loss(_finality(), sample_identity=_identity())

    assert finality.final_verifier_status == "accepted"


def test_stage13_0_reward_finality_accepts_trusted_rejected_negative_sample() -> None:
    finality = validate_reward_finality_for_policy_loss(
        _finality(reward_score=0.0, final_verifier_status="rejected", verifier_outcome="rejected"),
        sample_identity=_identity(),
    )

    assert finality.final_verifier_status == "rejected"


def test_stage13_0_reward_finality_rejects_pending_or_provisional_reward() -> None:
    pending = _finality(
        reward_state="pending_verifier",
        reward_score=None,
        reward_score_source="unknown",
        final_verifier_status="unknown",
        invalid_reason="pending",
    )
    with pytest.raises(ValueError, match="reward_not_final"):
        validate_reward_finality_for_policy_loss(pending, sample_identity=_identity())

    provisional = _finality(reward_score_source="provisional")
    with pytest.raises(ValueError, match="reward_score_source_not_trusted"):
        validate_reward_finality_for_policy_loss(provisional, sample_identity=_identity())


def test_stage13_0_reward_finality_rejects_missing_refs_even_with_score() -> None:
    with pytest.raises(ValueError, match="missing_final_verifier_ref"):
        validate_reward_finality_for_policy_loss(_finality(final_verifier_ref=None), sample_identity=_identity())

    with pytest.raises(ValueError, match="missing_reward_metadata_ref"):
        validate_reward_finality_for_policy_loss(_finality(reward_metadata_ref=None), sample_identity=_identity())


def test_stage13_0_reward_finality_rejects_wrong_reward_job_binding() -> None:
    finality = _finality(reward_job_id="wrong-reward-job")

    with pytest.raises(ValueError, match="reward_job_id_mismatch"):
        validate_reward_finality_for_policy_loss(finality, sample_identity=_identity())
