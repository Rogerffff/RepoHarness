from __future__ import annotations

from types import SimpleNamespace

import pytest

from repo_harness_verl import (
    VerlVisibilityError,
    validate_fully_async_queue_payload_visibility,
    validate_pre_serialization_rollout_sample_visibility,
)


def _rollout_sample(
    *,
    non_tensor_batch: dict[str, object] | None = None,
    meta_info: dict[str, object] | None = None,
    rollout_status: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        full_batch=SimpleNamespace(
            batch={},
            non_tensor_batch={} if non_tensor_batch is None else non_tensor_batch,
            meta_info={} if meta_info is None else meta_info,
        ),
        rollout_status={} if rollout_status is None else rollout_status,
    )


def _visible_rollout_status() -> dict[str, object]:
    return {
        "repo_harness_visibility_scan_status": "passed",
        "repo_harness_visibility_scan_digest": "sha256:visibility",
        "repo_harness_episode_id": "episode-001",
    }


def test_stage13_0_pre_serialization_rollout_sample_visibility_accepts_scanned_payload() -> None:
    sample = _rollout_sample(
        non_tensor_batch={"repo_harness_episode_id": ["episode-001"]},
        rollout_status=_visible_rollout_status(),
    )

    validate_pre_serialization_rollout_sample_visibility(sample)


@pytest.mark.parametrize(
    "sample",
    [
        _rollout_sample(rollout_status={}),
        _rollout_sample(
            non_tensor_batch={"repo_harness_visibility_scan_status": ["missing"]},
            rollout_status={},
        ),
    ],
)
def test_stage13_0_pre_serialization_rollout_sample_visibility_requires_scan_status(
    sample: SimpleNamespace,
) -> None:
    with pytest.raises(VerlVisibilityError, match="visibility_scan_status"):
        validate_pre_serialization_rollout_sample_visibility(sample)


@pytest.mark.parametrize(
    "sample",
    [
        _rollout_sample(
            non_tensor_batch={"reward_model": [{"ground_truth": "answer"}]},
            rollout_status=_visible_rollout_status(),
        ),
        _rollout_sample(
            non_tensor_batch={"safe": [{"reward_extra_info": {"score": 1.0}}]},
            rollout_status=_visible_rollout_status(),
        ),
        _rollout_sample(
            rollout_status={
                **_visible_rollout_status(),
                "details": {"groundTruth": "answer"},
            },
        ),
        _rollout_sample(
            non_tensor_batch={"raw_prompt": [{"role": "user", "content": "/Users/roger/private/task.yaml"}]},
            rollout_status=_visible_rollout_status(),
        ),
    ],
)
def test_stage13_0_pre_serialization_rollout_sample_visibility_rejects_hidden_payloads(
    sample: SimpleNamespace,
) -> None:
    with pytest.raises(VerlVisibilityError):
        validate_pre_serialization_rollout_sample_visibility(sample)


def test_stage13_0_queue_payload_visibility_rejects_serialized_bytes_without_scan_facts() -> None:
    with pytest.raises(VerlVisibilityError, match="missing_visibility_scan_status"):
        validate_fully_async_queue_payload_visibility(b"serialized-rollout-sample")


def test_stage13_0_queue_payload_visibility_accepts_serialized_bytes_with_scan_facts() -> None:
    validate_fully_async_queue_payload_visibility(
        b"serialized-rollout-sample",
        visibility_scan_status="passed",
        visibility_scan_digest="sha256:visibility",
    )


def test_stage13_0_queue_payload_visibility_rejects_unscanned_object_before_ray_serialization() -> None:
    sample = _rollout_sample(rollout_status={})

    with pytest.raises(VerlVisibilityError, match="visibility_scan_status"):
        validate_fully_async_queue_payload_visibility(sample)
