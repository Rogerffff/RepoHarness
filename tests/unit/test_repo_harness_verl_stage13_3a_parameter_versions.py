from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness_verl import (
    FakeParameterClock,
    attach_queue_facts_to_rollout_sample,
    build_fake_trainer_step_report,
    build_queue_facts_from_episode_result,
    select_valid_rollout_samples_for_required_count,
    validate_rollout_sample_for_trainer_batch,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
VISIBILITY_DIGEST = "sha256:stage13-3a-visibility"


def _episode_result(suffix: str) -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["episode_id"] = f"stage13-3a-version-episode-{suffix}"
    payload["run_id"] = f"stage13-3a-version-run-{suffix}"
    payload["task_id"] = f"stage13-3a-version-task-{suffix}"
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


def test_stage13_3a_fresh_and_stale_samples_use_global_step_window() -> None:
    fresh_facts = build_queue_facts_from_episode_result(
        _episode_result("fresh"),
        visibility_scan_status="passed",
        visibility_scan_digest=VISIBILITY_DIGEST,
        current_global_steps=10,
        staleness_threshold=2,
    )
    stale_facts = build_queue_facts_from_episode_result(
        _episode_result("stale"),
        visibility_scan_status="passed",
        visibility_scan_digest=VISIBILITY_DIGEST,
        current_global_steps=100,
        staleness_threshold=2,
    )

    assert fresh_facts.valid_for_policy_loss is True
    assert fresh_facts.staleness == 0
    assert stale_facts.valid_for_policy_loss is False
    assert stale_facts.rejection_reason == "stale_trajectory"
    assert stale_facts.staleness == 90


def test_stage13_3a_fake_parameter_clock_reports_post_sync_like_transition() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result("post-sync"),
        visibility_scan_status="passed",
        visibility_scan_digest=VISIBILITY_DIGEST,
        current_global_steps=10,
        staleness_threshold=2,
    )
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), facts)
    parsed = validate_rollout_sample_for_trainer_batch(
        sample,
        current_global_steps=10,
        staleness_threshold=2,
    )
    assert parsed.max_global_steps == 10
    assert sample.full_batch.non_tensor_batch["max_global_steps"] == [10]

    selected, selection_report = select_valid_rollout_samples_for_required_count([sample], required_samples=1)
    assert selected == [sample]

    step_report = build_fake_trainer_step_report(
        selection_report,
        parameter_clock=FakeParameterClock(
            current_global_steps=1,
            current_param_version=0,
            trigger_parameter_sync_step=2,
        ),
    )

    assert step_report.real_policy_loss_executed is False
    assert step_report.fake_selection_step_executed is True
    assert step_report.current_param_version == 0
    assert step_report.next_param_version == 1
    assert step_report.next_global_steps == 2
