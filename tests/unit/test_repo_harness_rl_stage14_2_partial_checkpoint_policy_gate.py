from __future__ import annotations

import pytest
from pydantic import ValidationError

from repo_harness.rl.async_contracts import validate_formal_async_online_rl_batch
from repo_harness.rl.partial_checkpoint import (
    PartialEpisodeCheckpoint,
    partial_checkpoint_to_queue_facts,
    validate_partial_checkpoint_for_resume_preparation,
    validate_partial_checkpoint_not_trainable,
)
from repo_harness.rl.training_view import FormalOnlineRLSample, validate_formal_online_rl_batch
from repo_harness_verl import RepoHarnessFullyAsyncQueueFacts

from stage14_2_checkpoint_helpers import build_stage14_2_checkpoint_payload


def test_stage14_2_rejects_forged_trainable_flags() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["online_rl_eligible"] = True
    payload["invalid_for_training"] = False
    payload["invalid_for_online_rl"] = False

    with pytest.raises(ValueError, match="partial checkpoint cannot be marked trainable"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_reward_finality_forged_on_partial_checkpoint() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["reward_finality"]["reward_state"] = "final_verifier_completed"
    payload["reward_finality"]["final_verifier_status"] = "accepted"
    payload["reward_finality"]["reward_score"] = 1.0

    with pytest.raises(ValueError, match="reward_finality_digest_mismatch|partial checkpoint cannot claim final reward"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_partial_checkpoint_cannot_enter_formal_online_rl_sample_path() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())

    with pytest.raises(ValueError, match="partial checkpoint cannot be marked trainable|partial_checkpoint_forged_trainable_flag"):
        validate_partial_checkpoint_not_trainable(
            checkpoint.model_copy(update={"online_rl_eligible": True, "invalid_for_training": False})
        )


def test_stage14_2_partial_checkpoint_queue_facts_are_diagnostic_not_valid() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())

    queue_facts = partial_checkpoint_to_queue_facts(checkpoint)

    assert queue_facts.valid_for_policy_loss is False
    assert queue_facts.sample_classification == "partial_checkpoint"
    assert queue_facts.rejection_reason.startswith("partial_checkpoint_not_trainable")


def test_stage14_2_resume_preparation_still_not_policy_loss_valid() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(
        build_stage14_2_checkpoint_payload(checkpoint_status="resume_preparation")
    )

    validate_partial_checkpoint_for_resume_preparation(checkpoint)
    queue_facts = partial_checkpoint_to_queue_facts(checkpoint)

    assert queue_facts.valid_for_policy_loss is False
    assert queue_facts.sample_classification == "resume_preparation"


def test_stage14_2_formal_online_rl_sample_is_not_constructed_from_checkpoint() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())

    with pytest.raises(ValidationError):
        FormalOnlineRLSample.model_validate(checkpoint)


def test_stage14_2_checkpoint_dict_is_rejected_by_formal_batch_gates() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())
    checkpoint_payload = checkpoint.model_dump(mode="python")

    with pytest.raises((ValueError, ValidationError)):
        validate_formal_online_rl_batch([checkpoint_payload])
    with pytest.raises((ValueError, ValidationError)):
        validate_formal_async_online_rl_batch([checkpoint_payload])


def test_stage14_2_checkpoint_queue_facts_do_not_match_fully_async_valid_facts_shape() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())
    checkpoint_queue_facts = partial_checkpoint_to_queue_facts(checkpoint)

    with pytest.raises(ValidationError):
        RepoHarnessFullyAsyncQueueFacts.model_validate(checkpoint_queue_facts.model_dump(mode="python"))
