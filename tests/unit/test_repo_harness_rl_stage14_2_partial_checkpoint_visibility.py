from __future__ import annotations

import pytest

from repo_harness.rl.partial_checkpoint import PartialEpisodeCheckpoint

from stage14_2_checkpoint_helpers import build_stage14_2_checkpoint_payload


def test_stage14_2_rejects_absolute_workspace_path() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["workspace"]["workspace_snapshot_ref"] = "/workspace/private/snapshot"

    with pytest.raises(ValueError, match="absolute local path|opaque rh://"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_hidden_verifier_marker_in_policy_version() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["policy_version"] = {"hidden_verifier": "secret"}

    with pytest.raises(ValueError, match="evaluator-only content"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_runtime_private_ref_in_batch_projection() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["batch_safe_projection"] = {
        "repo_harness_runtime_private_ref": "rh://runtime-private/writer-lease-0"
    }

    with pytest.raises(ValueError, match="runtime-private refs cannot enter batch_safe_projection"):
        PartialEpisodeCheckpoint.model_validate(payload)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("repo_harness_ref", "rh://runtime_private/writer-lease-0"),
        ("repo_harness_ref", "rh://Runtime-Private/writer-lease-0"),
        ("repo_harness_runtime-private_ref", "rh://partial-checkpoints/checkpoint-0"),
    ],
)
def test_stage14_2_rejects_runtime_private_projection_marker_variants(key: str, value: str) -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["batch_safe_projection"] = {key: value}

    with pytest.raises(ValueError, match="runtime-private refs cannot enter batch_safe_projection"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_rejects_nested_reward_metadata_in_runtime_fields() -> None:
    payload = build_stage14_2_checkpoint_payload()
    payload["policy_version"] = {"safe": {"reward_extra_info": "secret"}}

    with pytest.raises(ValueError, match="evaluator-only content"):
        PartialEpisodeCheckpoint.model_validate(payload)


def test_stage14_2_accepts_runtime_private_opaque_ref_inside_checkpoint_only() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(
        build_stage14_2_checkpoint_payload(runtime_private_refs={"writer_lease": "rh://runtime-private/writer-lease-0"})
    )

    assert checkpoint.runtime_private_refs["writer_lease"] == "rh://runtime-private/writer-lease-0"
    assert "writer_lease" not in checkpoint.batch_safe_projection
