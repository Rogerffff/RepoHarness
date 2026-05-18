from __future__ import annotations

import json
import pickle
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness_verl import (
    VerlVisibilityError,
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    deserialize_message_queue_payload,
    queue_facts_from_rollout_sample,
    serialize_rollout_sample_for_message_queue,
    validate_fully_async_queue_payload_visibility,
    validate_pre_serialization_rollout_sample_visibility,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_result() -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["episode_id"] = "stage13-2-message-episode"
    payload["run_id"] = "stage13-2-message-run"
    payload["task_id"] = "stage13-2-message-task"
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_episode_id": payload["episode_id"],
        "repo_harness_run_id": payload["run_id"],
        "repo_harness_task_id": payload["task_id"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return RepoHarnessEpisodeResult.model_validate(payload)


def _rollout_sample(batch_size: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        full_batch=SimpleNamespace(
            batch={
                "responses": [[1, 2] for _ in range(batch_size)],
                "response_mask": [[1, 1] for _ in range(batch_size)],
            },
            non_tensor_batch={},
            meta_info={
                "metrics": [
                    {"generate_sequences": 0.1 + index, "tool_calls": 0.0}
                    for index in range(batch_size)
                ]
            },
        ),
        sample_id="stage13-2-message-episode",
        epoch=0,
        rollout_status={},
    )


def _scanned_sample() -> SimpleNamespace:
    facts = build_queue_facts_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    return attach_queue_facts_to_rollout_sample(_rollout_sample(), facts)


def _scanned_batch_sample(batch_size: int = 2) -> SimpleNamespace:
    facts = build_queue_facts_from_episode_result(
        _episode_result(),
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )
    return attach_queue_facts_to_rollout_sample(_rollout_sample(batch_size=batch_size), facts)


def test_stage13_2_message_queue_serialization_requires_visibility_scan() -> None:
    with pytest.raises(VerlVisibilityError, match="visibility_scan_status"):
        validate_pre_serialization_rollout_sample_visibility(_rollout_sample())

    with pytest.raises(VerlVisibilityError, match="missing_visibility_scan_status"):
        validate_fully_async_queue_payload_visibility(b"opaque-payload")


def test_stage13_2_message_queue_serializes_scanned_rollout_sample() -> None:
    sample = _scanned_sample()

    payload = serialize_rollout_sample_for_message_queue(sample, serializer="pickle")
    restored = deserialize_message_queue_payload(
        payload,
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
        serializer="pickle",
    )

    assert isinstance(payload, bytes)
    assert queue_facts_from_rollout_sample(restored).sample_id == "stage13-2-message-episode"


def test_stage13_2_message_queue_deserialize_requires_external_scan_ledger_facts() -> None:
    payload = pickle.dumps(_rollout_sample())

    with pytest.raises(VerlVisibilityError, match="missing_visibility_scan_status"):
        deserialize_message_queue_payload(payload, serializer="pickle")


def test_stage13_2_message_queue_deserialize_rechecks_restored_rollout_sample_visibility() -> None:
    forged = _rollout_sample()
    forged.rollout_status = {
        "repo_harness_visibility_scan_status": "passed",
        "repo_harness_visibility_scan_digest": "sha256:visibility",
    }
    forged.full_batch.non_tensor_batch["reward_model"] = [{"ground_truth": "answer"}]
    payload = pickle.dumps(forged)

    with pytest.raises(VerlVisibilityError):
        deserialize_message_queue_payload(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest="sha256:visibility",
            serializer="pickle",
        )


def test_stage13_2_message_queue_deserialize_rejects_scan_digest_mismatch() -> None:
    payload = serialize_rollout_sample_for_message_queue(_scanned_sample(), serializer="pickle")

    with pytest.raises(VerlVisibilityError, match="visibility_scan_digest_mismatch"):
        deserialize_message_queue_payload(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest="sha256:forged",
            serializer="pickle",
        )


def test_stage13_2_message_queue_deserialize_rejects_internal_scan_source_mismatch() -> None:
    forged = _scanned_sample()
    forged.rollout_status["repo_harness_visibility_scan_digest"] = "sha256:outer-ledger"
    payload = pickle.dumps(forged)

    with pytest.raises(VerlVisibilityError, match="visibility_scan_digest_mismatch"):
        deserialize_message_queue_payload(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest="sha256:outer-ledger",
            serializer="pickle",
        )


def test_stage13_2_message_queue_deserialize_rejects_second_row_scan_digest_mismatch() -> None:
    forged = _scanned_batch_sample(batch_size=2)
    forged.full_batch.non_tensor_batch["repo_harness_visibility_scan_digest"][1] = "sha256:forged"
    payload = pickle.dumps(forged)

    with pytest.raises(VerlVisibilityError, match="visibility_scan_digest_mismatch"):
        deserialize_message_queue_payload(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest="sha256:visibility",
            serializer="pickle",
        )


def test_stage13_2_message_queue_pre_serialization_rejects_hidden_non_tensor_payload() -> None:
    sample = _scanned_sample()
    sample.full_batch.non_tensor_batch["reward_model"] = [{"ground_truth": "answer"}]

    with pytest.raises(VerlVisibilityError):
        serialize_rollout_sample_for_message_queue(sample, serializer="pickle")


def test_stage13_2_message_queue_pre_serialization_rejects_hidden_rollout_status_payload() -> None:
    sample = _scanned_sample()
    sample.rollout_status["debug"] = {"reward_extra_info": {"score": 1.0}}

    with pytest.raises(VerlVisibilityError):
        serialize_rollout_sample_for_message_queue(sample, serializer="pickle")
