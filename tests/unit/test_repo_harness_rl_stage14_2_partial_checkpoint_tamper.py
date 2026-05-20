from __future__ import annotations

import pytest

from repo_harness.rl.partial_checkpoint import (
    PartialEpisodeCheckpoint,
    compute_partial_checkpoint_visibility_digest,
    partial_checkpoint_to_queue_facts,
    validate_partial_checkpoint_for_resume_preparation,
    validate_partial_checkpoint_not_trainable,
)

from stage14_2_checkpoint_helpers import build_stage14_2_checkpoint_payload


def test_stage14_2_rejects_token_reorder() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["token_provenance"]["response_ids"] = [202, 201]

    with pytest.raises(ValueError, match="response_ids_digest_mismatch"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_logprob_reorder() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["token_provenance"]["response_logprobs"] = [-0.2, -0.1]

    with pytest.raises(ValueError, match="response_logprobs_digest_mismatch"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_non_binary_response_mask() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["token_provenance"]["response_mask"] = [2, 1]

    with pytest.raises(ValueError, match="Input should be 0 or 1"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_response_span_reorder_or_rewrite() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["token_provenance"]["completed_response_spans"][0]["end"] = 1

    with pytest.raises(ValueError, match="response_span_digest_mismatch"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_generation_record_policy_version_tamper() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["token_provenance"]["completed_generation_records"][0]["policy_version"]["version"] = 1

    with pytest.raises(ValueError, match="generation_record_digest_mismatch"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_durable_lease_token_mismatch() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["durable_writer_lease"]["lease_token"] = "lease-token-tampered"

    with pytest.raises(ValueError, match="durable_lease_digest_mismatch"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_reward_job_id_mismatch() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["reward_finality"]["reward_job_id"] = "reward-job-tampered"

    with pytest.raises(ValueError, match="reward_finality_digest_mismatch"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_stale_disguised_as_fresh_for_resume_preparation() -> None:
    payload = build_stage14_2_checkpoint_payload(
        checkpoint_status="resume_preparation",
        staleness_status="stale",
    )
    checkpoint = PartialEpisodeCheckpoint.model_validate(payload)

    with pytest.raises(ValueError, match="stale_checkpoint_cannot_enter_resume_preparation"):
        validate_partial_checkpoint_for_resume_preparation(checkpoint)


def test_stage14_2_rejects_missing_external_visibility_ledger() -> None:
    payload = build_stage14_2_checkpoint_payload(external_visibility_ledger_ref=None)

    with pytest.raises(ValueError, match="external_visibility_ledger_ref is required"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_message_queue_drop_disguised_as_checkpoint() -> None:
    payload = build_stage14_2_checkpoint_payload(message_queue_drop_status="dropped")

    with pytest.raises(ValueError, match="message queue dropped checkpoint"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_partial_disguised_as_complete() -> None:
    payload = build_stage14_2_checkpoint_payload(checkpoint_status="complete_for_policy_loss")

    with pytest.raises(ValueError, match="Input should be"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_writer_active_resume_preparation() -> None:
    payload = build_stage14_2_checkpoint_payload(
        checkpoint_status="resume_preparation",
        writer_state={"run_directory_writer_active": True},
    )

    with pytest.raises(ValueError, match="writer_active_checkpoint_cannot_enter_resume_preparation"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_helpers_revalidate_model_copy_token_tamper_for_resume() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(
        build_stage14_2_checkpoint_payload(checkpoint_status="resume_preparation")
    )
    tampered = checkpoint.model_copy(
        update={
            "token_provenance": checkpoint.token_provenance.model_copy(
                update={"response_ids": [999, 202]}
            )
        }
    )

    with pytest.raises(ValueError, match="response_ids_digest_mismatch"):
        validate_partial_checkpoint_for_resume_preparation(tampered)


def test_stage14_2_helpers_revalidate_model_copy_token_tamper_for_queue_facts() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())
    tampered = checkpoint.model_copy(
        update={
            "token_provenance": checkpoint.token_provenance.model_copy(
                update={"response_ids": [999, 202]}
            )
        }
    )

    with pytest.raises(ValueError, match="response_ids_digest_mismatch"):
        partial_checkpoint_to_queue_facts(tampered)


def test_stage14_2_helpers_revalidate_model_copy_generation_record_tamper() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())
    tampered_record = checkpoint.token_provenance.completed_generation_records[0].model_copy(
        update={"policy_version": {"name": "stage14-policy", "version": 999}}
    )
    tampered = checkpoint.model_copy(
        update={
            "token_provenance": checkpoint.token_provenance.model_copy(
                update={"completed_generation_records": [tampered_record]}
            )
        }
    )

    with pytest.raises(ValueError, match="generation_record_digest_mismatch"):
        validate_partial_checkpoint_not_trainable(tampered)


def test_stage14_2_visibility_digest_helper_revalidates_model_copy_tamper() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())
    tampered = checkpoint.model_copy(
        update={
            "token_provenance": checkpoint.token_provenance.model_copy(
                update={"response_ids": [999, 202]}
            )
        }
    )

    with pytest.raises(ValueError, match="response_ids_digest_mismatch"):
        compute_partial_checkpoint_visibility_digest(tampered)
