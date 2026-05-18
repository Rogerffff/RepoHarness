from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness_verl import (
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    select_valid_rollout_samples_for_required_count,
    validate_rollout_sample_for_trainer_batch,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_result(suffix: str) -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["episode_id"] = f"stage13-2-stale-episode-{suffix}"
    payload["run_id"] = f"stage13-2-stale-run-{suffix}"
    payload["task_id"] = f"stage13-2-stale-task-{suffix}"
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_episode_id": payload["episode_id"],
        "repo_harness_run_id": payload["run_id"],
        "repo_harness_task_id": payload["task_id"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return RepoHarnessEpisodeResult.model_validate(payload)


def _rollout_sample() -> SimpleNamespace:
    return SimpleNamespace(
        full_batch=SimpleNamespace(
            batch={"responses": [[1, 2]], "response_mask": [[1, 1]]},
            non_tensor_batch={},
            meta_info={"metrics": [{"generate_sequences": 0.1, "tool_calls": 0.0}]},
        ),
        sample_id=None,
        epoch=0,
        rollout_status={},
    )


def test_stage13_2_partial_rollout_is_rejected_before_refill_selection() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result("partial"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
        partial_rollout_status="partial",
        partial_rollout_supported=False,
    )

    assert facts.valid_for_policy_loss is False
    assert facts.rejection_reason == "partial_rollout_unsupported_in_stage13_2"


def test_stage13_2_stale_sample_does_not_count_toward_required_queue_samples() -> None:
    valid_facts = build_queue_facts_from_episode_result(
        _episode_result("valid"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    stale_facts = build_queue_facts_from_episode_result(
        _episode_result("stale"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
        current_global_steps=100,
        staleness_threshold=2,
    )
    valid_sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), valid_facts)
    stale_sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), stale_facts)

    selected, report = select_valid_rollout_samples_for_required_count(
        [stale_sample, valid_sample],
        required_samples=2,
        staleness_threshold=2,
    )

    assert selected == [valid_sample]
    assert report.valid_sample_count == 1
    assert report.insufficient_valid_samples is True
    assert report.rejected_reasons[stale_facts.sample_id] == "stale_trajectory"


def test_stage13_2_trainer_gate_rejects_current_global_step_staleness() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result("late-stale"),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), facts)

    with pytest.raises(ValueError, match="stale_trajectory"):
        validate_rollout_sample_for_trainer_batch(
            sample,
            current_global_steps=100,
            staleness_threshold=2,
        )
