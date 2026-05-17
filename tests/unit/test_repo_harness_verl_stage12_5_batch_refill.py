from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness_verl import Stage125RefillPolicy, classify_episode_result_for_refill, select_valid_training_views


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _load_episode_payload() -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))


def _formal_episode_payload(suffix: str) -> dict[str, Any]:
    payload = _load_episode_payload()
    payload["episode_id"] = f"stage12-5-episode-{suffix}"
    payload["run_id"] = f"stage12-5-run-{suffix}"
    payload["task_id"] = f"stage12-5-task-{suffix}"
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_episode_id": payload["episode_id"],
        "repo_harness_run_id": payload["run_id"],
        "repo_harness_task_id": payload["task_id"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return payload


def _missing_logprobs_payload() -> dict[str, Any]:
    payload = _formal_episode_payload("missing-logprobs")
    payload["invalid_for_training"] = True
    payload["invalid_for_online_rl"] = True
    payload["status_reason"] = "missing_response_logprobs"
    payload["training_view"]["online_rl_eligible"] = False
    payload["training_view"]["response_logprobs"] = None
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_invalid_for_training": True,
        "repo_harness_invalid_for_online_rl": True,
        "repo_harness_invalid_reason": "missing_response_logprobs",
    }
    return payload


def _mock_route_payload() -> dict[str, Any]:
    payload = _formal_episode_payload("mock-route")
    payload["invalid_for_online_rl"] = True
    payload["status_reason"] = "non_verl_route_invalid_for_online_rl"
    payload["training_view"]["online_rl_eligible"] = False
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_llm_gateway_route": "mock",
        "repo_harness_invalid_for_online_rl": True,
        "repo_harness_invalid_reason": "non_verl_route_invalid_for_online_rl",
    }
    for record in payload["generation_records"]:
        record["gateway_route"] = "mock"
        record["inference_backend"] = None
    return payload


def test_stage12_5_refill_classifies_formal_online_rl_sample_as_valid() -> None:
    result = RepoHarnessEpisodeResult.model_validate(_formal_episode_payload("valid"))

    classification = classify_episode_result_for_refill(result)

    assert classification.sample_class == "valid_trainable_sample"
    assert classification.formal_online_rl_valid is True


def test_stage12_5_refill_filters_invalid_samples_before_batch_collection() -> None:
    candidates = [_missing_logprobs_payload(), _mock_route_payload(), _formal_episode_payload("valid")]
    policy = Stage125RefillPolicy(target_valid_sample_count=2, max_attempts=4)

    views, report = select_valid_training_views(candidates, policy=policy)

    assert len(views) == 1
    assert views[0].extra_fields["repo_harness_episode_id"] == "stage12-5-episode-valid"
    assert report.valid_sample_count == 1
    assert report.invalid_sample_count == 2
    assert report.insufficient_valid_batch is True
    assert report.insufficient_reason == "candidate_pool_exhausted"
    assert [item.sample_class for item in report.classifications] == [
        "missing_logprobs",
        "mixed_route",
        "valid_trainable_sample",
    ]


def test_stage12_5_refill_deduplicates_task_ids_when_requested() -> None:
    first = _formal_episode_payload("first")
    second = _formal_episode_payload("second")
    second["task_id"] = first["task_id"]
    second["training_view"]["extra_fields"]["repo_harness_task_id"] = first["task_id"]
    policy = Stage125RefillPolicy(target_valid_sample_count=2, max_attempts=2, deduplicate_task_ids=True)

    _, report = select_valid_training_views([first, second], policy=policy)

    assert report.valid_sample_count == 1
    assert report.classifications[1].sample_class == "model_format_failure"
    assert report.classifications[1].reason == "duplicate_task_filtered"


def test_stage12_5_refill_respects_episode_top_level_invalid_flags() -> None:
    invalid = _formal_episode_payload("top-level-invalid")
    invalid["invalid_for_online_rl"] = True
    invalid["status_reason"] = "top_level_invalid_for_online_rl_probe"
    policy = Stage125RefillPolicy(target_valid_sample_count=1, max_attempts=1)

    views, report = select_valid_training_views([invalid], policy=policy)

    assert views == []
    assert report.valid_sample_count == 0
    assert report.classifications[0].formal_online_rl_valid is False
    assert report.classifications[0].reason == "top_level_invalid_for_online_rl_probe"


def test_stage12_5_refill_keeps_trusted_verifier_rejected_negative_sample() -> None:
    failed = _formal_episode_payload("trusted-negative")
    failed["status"] = "failed"
    failed["status_reason"] = "final_verifier_rejected"
    failed["training_view"]["reward_score"] = 0.0
    failed["reward"]["score"] = 0.0
    failed["verifier_summary"]["accepted"] = False
    failed["verifier_summary"]["status"] = "rejected"
    policy = Stage125RefillPolicy(target_valid_sample_count=1, max_attempts=1)

    views, report = select_valid_training_views([failed], policy=policy)

    assert len(views) == 1
    assert report.valid_sample_count == 1
    assert report.classifications[0].sample_class == "valid_verifier_rejected_negative_sample"
    assert report.classifications[0].formal_online_rl_valid is True


def test_stage12_5_refill_rejects_inconsistent_failed_negative_sample() -> None:
    failed = _formal_episode_payload("inconsistent-negative")
    failed["status"] = "failed"
    failed["status_reason"] = "final_verifier_rejected"
    failed["training_view"]["reward_score"] = 0.0
    failed["reward"]["score"] = 0.0
    failed["verifier_summary"]["accepted"] = True
    failed["verifier_summary"]["status"] = "accepted"
    policy = Stage125RefillPolicy(target_valid_sample_count=1, max_attempts=1)

    views, report = select_valid_training_views([failed], policy=policy)

    assert views == []
    assert report.valid_sample_count == 0
    assert report.classifications[0].sample_class == "verifier_rejected"
    assert report.classifications[0].reason == "untrusted_or_inconsistent_final_verifier_rejected"
    assert report.classifications[0].formal_online_rl_valid is False


def test_stage12_5_refill_selection_is_bound_to_candidate_position_not_duplicate_episode_id() -> None:
    invalid = _missing_logprobs_payload()
    valid = _formal_episode_payload("same-id")
    valid["episode_id"] = invalid["episode_id"]
    valid["training_view"]["extra_fields"]["repo_harness_episode_id"] = invalid["episode_id"]
    policy = Stage125RefillPolicy(target_valid_sample_count=1, max_attempts=2)

    views, report = select_valid_training_views([invalid, valid], policy=policy)

    assert [item.sample_class for item in report.classifications] == [
        "missing_logprobs",
        "valid_trainable_sample",
    ]
    assert len(views) == 1
    assert views[0].online_rl_eligible is True
    assert views[0].response_logprobs is not None
