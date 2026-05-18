from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repo_harness.rl import (
    RepoHarnessEpisodeResult,
    SampleIdentity,
    compute_generation_record_digest,
    compute_training_view_trajectory_digest,
    validate_late_reward_binding,
)
from repo_harness.rl.async_contracts import RewardFinalityFacts


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_result() -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text())
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return RepoHarnessEpisodeResult.model_validate(payload)


def _identity(result: RepoHarnessEpisodeResult, *, attempt: str = "attempt-0") -> SampleIdentity:
    generation_digest = compute_generation_record_digest(result.generation_records)
    trajectory_digest = compute_training_view_trajectory_digest(
        result.training_view,
        generation_records=result.generation_records,
        sample_attempt_id=attempt,
        episode_id=result.episode_id,
        run_id=result.run_id,
    )
    return SampleIdentity(
        sample_id=result.episode_id,
        sample_attempt_id=attempt,
        episode_id=result.episode_id,
        run_id=result.run_id,
        task_id=result.task_id,
        dataset_uid=result.task_id,
        rollout_uid=result.run_id,
        global_steps=0,
        min_global_steps=0,
        max_global_steps=0,
        reward_job_id=f"reward-job-{attempt}",
        generation_record_digest=generation_digest,
        trajectory_digest=trajectory_digest,
    )


def test_stage13_0_sample_identity_requires_dataset_and_rollout_identity() -> None:
    result = _episode_result()
    generation_digest = compute_generation_record_digest(result.generation_records)

    with pytest.raises(ValueError, match="dataset_uid or dataset_index"):
        SampleIdentity(
            sample_id=result.episode_id,
            sample_attempt_id="attempt-0",
            episode_id=result.episode_id,
            run_id=result.run_id,
            task_id=result.task_id,
            rollout_uid=result.run_id,
            global_steps=0,
            min_global_steps=0,
            max_global_steps=0,
            reward_job_id="reward-job-attempt-0",
            generation_record_digest=generation_digest,
            trajectory_digest="sha256:test",
        )

    with pytest.raises(ValueError, match="rollout_uid or uid"):
        SampleIdentity(
            sample_id=result.episode_id,
            sample_attempt_id="attempt-0",
            episode_id=result.episode_id,
            run_id=result.run_id,
            task_id=result.task_id,
            dataset_uid=result.task_id,
            global_steps=0,
            min_global_steps=0,
            max_global_steps=0,
            reward_job_id="reward-job-attempt-0",
            generation_record_digest=generation_digest,
            trajectory_digest="sha256:test",
        )


def test_stage13_0_trajectory_digest_includes_prompt_facts() -> None:
    result = _episode_result()
    digest_a = compute_training_view_trajectory_digest(
        result.training_view,
        generation_records=result.generation_records,
        sample_attempt_id="attempt-0",
        episode_id=result.episode_id,
        run_id=result.run_id,
    )
    changed_view = result.training_view.model_copy(update={"prompt_ids": [999, *result.training_view.prompt_ids]})
    digest_b = compute_training_view_trajectory_digest(
        changed_view,
        generation_records=result.generation_records,
        sample_attempt_id="attempt-0",
        episode_id=result.episode_id,
        run_id=result.run_id,
    )

    assert digest_a != digest_b


def test_stage13_0_late_reward_binding_rejects_wrong_attempt_or_digest() -> None:
    result = _episode_result()
    identity = _identity(result, attempt="attempt-0")
    finality = RewardFinalityFacts(
        reward_state="final_verifier_completed",
        reward_score=1.0,
        reward_score_source="trusted_final_verifier",
        final_verifier_status="accepted",
        verifier_outcome="accepted",
        final_verifier_ref="rh://audit/final-verifier",
        reward_metadata_ref="rh://audit/reward-metadata",
        reward_job_id=identity.reward_job_id,
        sample_attempt_id="attempt-1",
        trajectory_digest=identity.trajectory_digest,
        generation_record_digest=identity.generation_record_digest,
    )

    with pytest.raises(ValueError, match="sample_attempt_id_mismatch"):
        validate_late_reward_binding(identity, finality)

    mismatched = finality.model_copy(
        update={
            "sample_attempt_id": identity.sample_attempt_id,
            "trajectory_digest": "sha256:wrong",
        }
    )
    with pytest.raises(ValueError, match="trajectory_digest_mismatch"):
        validate_late_reward_binding(identity, mismatched)


def test_stage13_0_late_reward_binding_rejects_wrong_reward_job_id() -> None:
    result = _episode_result()
    identity = _identity(result, attempt="attempt-0")
    finality = RewardFinalityFacts(
        reward_state="final_verifier_completed",
        reward_score=1.0,
        reward_score_source="trusted_final_verifier",
        final_verifier_status="accepted",
        verifier_outcome="accepted",
        final_verifier_ref="rh://audit/final-verifier",
        reward_metadata_ref="rh://audit/reward-metadata",
        reward_job_id="wrong-reward-job",
        sample_attempt_id=identity.sample_attempt_id,
        trajectory_digest=identity.trajectory_digest,
        generation_record_digest=identity.generation_record_digest,
    )

    with pytest.raises(ValueError, match="reward_job_id_mismatch"):
        validate_late_reward_binding(identity, finality)
