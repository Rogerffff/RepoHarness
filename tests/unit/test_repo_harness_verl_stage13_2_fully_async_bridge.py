from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness.rl.async_contracts import formal_async_online_rl_sample_from_episode_result
from repo_harness_verl import (
    RepoHarnessFullyAsyncQueueFacts,
    apply_reference_addition_process_compat,
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    queue_facts_from_rollout_sample,
    select_valid_rollout_samples_for_required_count,
    validate_rollout_sample_for_trainer_batch,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_payload(suffix: str = "valid") -> dict[str, Any]:
    payload = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["episode_id"] = f"stage13-2-episode-{suffix}"
    payload["run_id"] = f"stage13-2-run-{suffix}"
    payload["task_id"] = f"stage13-2-task-{suffix}"
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_episode_id": payload["episode_id"],
        "repo_harness_run_id": payload["run_id"],
        "repo_harness_task_id": payload["task_id"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return payload


def _episode_result(suffix: str = "valid") -> RepoHarnessEpisodeResult:
    return RepoHarnessEpisodeResult.model_validate(_episode_payload(suffix))


def _rollout_sample(batch_size: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        full_batch=SimpleNamespace(
            batch={
                "responses": [[11, 12] for _ in range(batch_size)],
                "response_mask": [[1, 1] for _ in range(batch_size)],
            },
            non_tensor_batch={},
            meta_info={
                "metrics": [
                    {"generate_sequences": 0.1 + index, "tool_calls": 0.01 + index}
                    for index in range(batch_size)
                ]
            },
        ),
        sample_id=None,
        epoch=0,
        rollout_status={},
    )


def test_stage13_2_queue_facts_accept_valid_episode_result() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    assert facts.valid_for_policy_loss is True
    assert facts.sample_classification == "valid"
    assert facts.reward_state == "final_verifier_completed"
    assert facts.reward_score_source == "trusted_final_verifier"
    assert facts.final_verifier_status == "accepted"
    assert facts.final_verifier_ref == "rh://audit/stage0h-success/final-verifier"
    assert facts.reward_metadata_ref == "rh://audit/stage0h-success/reward-metadata"


def test_stage13_2_queue_facts_keeps_trusted_verifier_rejected_negative_sample_valid() -> None:
    payload = _episode_payload("trusted-negative")
    payload["status"] = "failed"
    payload["status_reason"] = "final_verifier_rejected"
    payload["training_view"]["reward_score"] = 0.0
    payload["reward"]["score"] = 0.0
    payload["verifier_summary"]["accepted"] = False
    payload["verifier_summary"]["status"] = "rejected"
    result = RepoHarnessEpisodeResult.model_validate(payload)

    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    assert facts.valid_for_policy_loss is True
    assert facts.sample_classification == "valid"
    assert facts.final_verifier_status == "rejected"


def test_stage13_2_queue_facts_classifies_invalid_before_formal_validator() -> None:
    payload = _episode_payload("missing-logprobs")
    payload["invalid_for_training"] = True
    payload["invalid_for_online_rl"] = True
    payload["status_reason"] = "missing_response_logprobs"
    payload["training_view"]["online_rl_eligible"] = False
    payload["training_view"]["response_logprobs"] = None
    payload["training_view"]["extra_fields"]["repo_harness_invalid_for_training"] = True
    payload["training_view"]["extra_fields"]["repo_harness_invalid_for_online_rl"] = True
    payload["training_view"]["extra_fields"]["repo_harness_invalid_reason"] = "missing_response_logprobs"
    result = RepoHarnessEpisodeResult.model_validate(payload)

    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    assert facts.valid_for_policy_loss is False
    assert facts.sample_classification == "rejected"
    assert facts.rejection_reason == "missing_response_logprobs"


def test_stage13_2_queue_facts_classifies_missing_reward_finality_before_formal_validator() -> None:
    payload = _episode_payload("missing-reward-ref")
    payload["reward"]["reward_metadata_ref"] = None
    payload["training_view"]["extra_fields"].pop("repo_harness_reward_metadata_ref", None)
    result = RepoHarnessEpisodeResult.model_validate(payload)

    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    assert facts.valid_for_policy_loss is False
    assert facts.sample_classification == "rejected"
    assert facts.rejection_reason == "missing_reward_metadata_ref"


def test_stage13_2_queue_facts_classifies_missing_verifier_outcome_before_formal_validator() -> None:
    payload = _episode_payload("missing-verifier-outcome")
    payload["verifier_summary"]["accepted"] = None
    payload["verifier_summary"]["status"] = None
    result = RepoHarnessEpisodeResult.model_validate(payload)

    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    assert facts.valid_for_policy_loss is False
    assert facts.sample_classification == "rejected"
    assert facts.rejection_reason == "missing_final_verifier_outcome"


def test_stage13_2_queue_facts_classifies_status_verifier_mismatch_before_formal_validator() -> None:
    payload = _episode_payload("verifier-mismatch")
    payload["verifier_summary"]["accepted"] = False
    payload["verifier_summary"]["status"] = "rejected"
    payload["training_view"]["reward_score"] = 0.0
    payload["reward"]["score"] = 0.0
    result = RepoHarnessEpisodeResult.model_validate(payload)

    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    assert facts.valid_for_policy_loss is False
    assert facts.sample_classification == "rejected"
    assert facts.rejection_reason == "episode_status_verifier_outcome_mismatch"


def test_stage13_2_queue_facts_rejects_stale_candidate_before_formal_batch() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result("stale"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
        current_global_steps=100,
        staleness_threshold=2,
    )

    assert facts.valid_for_policy_loss is False
    assert facts.sample_classification == "rejected"
    assert facts.rejection_reason == "stale_trajectory"
    assert facts.staleness == 90


def test_stage13_2_queue_facts_requires_digest_when_visibility_scan_passed() -> None:
    with pytest.raises(ValueError, match="visibility_scan_digest"):
        build_queue_facts_from_episode_result(
            _episode_result("missing-visibility-digest"),
            visibility_scan_status="passed",
            visibility_scan_digest=None,
        )


def test_stage13_2_attach_queue_facts_writes_batch_sized_non_tensor_arrays() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result("arrays"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(batch_size=2), facts)

    values = sample.full_batch.non_tensor_batch["repo_harness_episode_id"]
    assert values == [facts.episode_id, facts.episode_id]
    assert isinstance(values, list)
    assert sample.full_batch.non_tensor_batch["min_global_steps"] == [facts.min_global_steps, facts.min_global_steps]
    assert sample.full_batch.non_tensor_batch["max_global_steps"] == [facts.max_global_steps, facts.max_global_steps]
    assert sample.rollout_status["repo_harness_visibility_scan_status"] == "passed"
    assert "repo_harness_final_verifier_ref" not in sample.rollout_status

    extracted = queue_facts_from_rollout_sample(sample)
    assert extracted == facts


def test_stage13_2_attach_queue_facts_rejects_top_level_sample_id_mismatch() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result("sample-id-mismatch"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    sample = _rollout_sample()
    sample.sample_id = "different-rollout-sample-id"

    with pytest.raises(ValueError, match="rollout_sample_id_mismatch"):
        attach_queue_facts_to_rollout_sample(sample, facts)


def test_stage13_2_rollout_sample_trainer_gate_rejects_invalid_queue_occupancy() -> None:
    valid = build_queue_facts_from_episode_result(
        _episode_result("select-valid"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    rejected = RepoHarnessFullyAsyncQueueFacts(
        sample_id="stage13-2-rejected",
        sample_attempt_id="stage13-2-rejected:attempt-0",
        episode_id="stage13-2-rejected",
        run_id="stage13-2-run-rejected",
        task_id="stage13-2-task-rejected",
        dataset_uid="stage13-2-task-rejected",
        rollout_uid="stage13-2-run-rejected",
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
        sample_classification="rejected",
        rejection_reason="model_format_failure",
        invalid_reason="model_format_failure",
    )
    valid_sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), valid)
    rejected_sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), rejected)

    selected, report = select_valid_rollout_samples_for_required_count(
        [rejected_sample, valid_sample],
        required_samples=2,
    )

    assert selected == [valid_sample]
    assert report.valid_sample_count == 1
    assert report.insufficient_valid_samples is True
    assert report.rejected_reasons["stage13-2-rejected"].startswith("rollout_sample_not_valid")


def test_stage13_2_rollout_sample_trainer_gate_can_bind_formal_sample() -> None:
    result = _episode_result("formal-bind")
    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), facts)
    formal = formal_async_online_rl_sample_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )

    parsed = validate_rollout_sample_for_trainer_batch(sample, formal_sample=formal)

    assert parsed.valid_for_policy_loss is True


def test_stage13_2_rollout_sample_trainer_gate_rejects_top_level_sample_id_mismatch() -> None:
    result = _episode_result("trainer-sample-id-mismatch")
    facts = build_queue_facts_from_episode_result(
        result,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), facts)
    sample.sample_id = "different-rollout-sample-id"

    with pytest.raises(ValueError, match="rollout_sample_id_mismatch"):
        validate_rollout_sample_for_trainer_batch(sample)


def test_stage13_2_reference_addition_process_compat_pops_metrics_into_non_tensor_batch() -> None:
    full_batch = _rollout_sample(batch_size=2).full_batch

    processed = apply_reference_addition_process_compat(full_batch)

    assert "metrics" not in processed.meta_info
    assert processed.non_tensor_batch["processing_times"] == [0.1, 1.1]
    assert processed.non_tensor_batch["tool_calls_times"] == [0.01, 1.01]


@pytest.mark.parametrize(
    "meta_info",
    [
        {},
        {"metrics": [{"generate_sequences": 0.1}]},
        {"metrics": "not-a-list"},
    ],
)
def test_stage13_2_reference_addition_process_compat_rejects_fake_metrics(meta_info: dict[str, Any]) -> None:
    full_batch = _rollout_sample().full_batch
    full_batch.meta_info = meta_info

    with pytest.raises(ValueError):
        apply_reference_addition_process_compat(full_batch)
