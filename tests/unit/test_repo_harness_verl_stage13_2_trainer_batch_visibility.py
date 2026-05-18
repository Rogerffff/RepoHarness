from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness_verl import (
    VerlVisibilityError,
    apply_reference_addition_process_compat,
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    validate_dataproto_shapes,
    validate_dataproto_visibility,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_result() -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["episode_id"] = "stage13-2-trainer-episode"
    payload["run_id"] = "stage13-2-trainer-run"
    payload["task_id"] = "stage13-2-trainer-task"
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
            batch={
                "prompts": [[11, 12]],
                "responses": [[21, 22]],
                "response_mask": [[1, 1]],
                "input_ids": [[11, 12, 21, 22]],
                "attention_mask": [[1, 1, 1, 1]],
                "rollout_log_probs": [[-0.1, -0.2]],
                "rm_scores": [[1.0, 1.0]],
            },
            non_tensor_batch={},
            meta_info={"metrics": [{"generate_sequences": 0.25, "tool_calls": 0.05}]},
        ),
        sample_id="stage13-2-trainer-episode",
        epoch=0,
        rollout_status={},
    )


def test_stage13_2_trainer_batch_visibility_after_reference_metrics_transfer() -> None:
    facts = build_queue_facts_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(), facts)

    full_batch = apply_reference_addition_process_compat(sample.full_batch)

    assert "metrics" not in full_batch.meta_info
    assert full_batch.non_tensor_batch["processing_times"] == [0.25]
    assert full_batch.non_tensor_batch["tool_calls_times"] == [0.05]
    validate_dataproto_shapes(full_batch, batch_size=1, prompt_length=2, response_length=2)
    validate_dataproto_visibility(full_batch)


def test_stage13_2_trainer_batch_visibility_rejects_fully_async_meta_path_leak() -> None:
    sample = _rollout_sample()
    sample.full_batch.meta_info["fully_async/repo_harness_run_dir"] = "/Users/roger/private/run"

    with pytest.raises(VerlVisibilityError):
        validate_dataproto_visibility(sample.full_batch)
