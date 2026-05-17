from __future__ import annotations

from types import SimpleNamespace

import pytest

from repo_harness_verl import (
    VerlVisibilityError,
    validate_dataproto_visibility,
    validate_transfer_queue_field_visibility,
)


@pytest.mark.parametrize(
    "field",
    [
        {"reward_model": {"ground_truth": "answer"}},
        {"safe": {"reward_extra_info": {"score": 1}}},
        {"safe": {"nested": "hidden_verifier"}},
        {"raw_prompt": [{"role": "user", "content": "/Users/roger/private/task.yaml"}]},
    ],
)
def test_stage12_5_transferqueue_visibility_rejects_nested_evaluator_only_payloads(
    field: dict[str, object],
) -> None:
    with pytest.raises(VerlVisibilityError):
        validate_transfer_queue_field_visibility(field)


def test_stage12_5_transferqueue_visibility_accepts_repo_harness_opaque_refs() -> None:
    validate_transfer_queue_field_visibility(
        {
            "extra_fields": {
                "repo_harness_episode_id": "episode-001",
                "repo_harness_audit_manifest_ref": "rh://audit/episode-001/manifest",
                "repo_harness_invalid_for_online_rl": False,
            },
            "raw_prompt": [{"role": "user", "content": "visible user request"}],
        }
    )


def test_stage12_5_dataproto_visibility_rejects_nested_evaluator_only_payload_after_batch_concat() -> None:
    data_proto = SimpleNamespace(
        batch={},
        non_tensor_batch={"safe_dataset_column": [{"visible": "ok"}, {"reward_model": {"groundTruth": "answer"}}]},
        meta_info={},
    )

    with pytest.raises(VerlVisibilityError, match="groundTruth"):
        validate_dataproto_visibility(data_proto)
