from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from repo_harness.rl.partial_checkpoint import (
    PartialEpisodeCheckpoint,
    compute_partial_checkpoint_content_digest,
    compute_partial_checkpoint_trajectory_digest,
    compute_partial_checkpoint_visibility_digest,
    partial_checkpoint_to_queue_facts,
    validate_partial_checkpoint_for_resume_preparation,
    validate_partial_checkpoint_roundtrip,
)

from stage14_2_checkpoint_helpers import build_stage14_2_checkpoint_payload

FIXTURE_DIR = Path("tests/fixtures/repo_harness_verl/stage14_2")


def test_stage14_2_partial_checkpoint_roundtrip_and_digest_stability() -> None:
    payload = build_stage14_2_checkpoint_payload()

    checkpoint = PartialEpisodeCheckpoint.model_validate(payload)
    roundtripped = validate_partial_checkpoint_roundtrip(checkpoint)

    assert roundtripped.model_dump(mode="json") == checkpoint.model_dump(mode="json")
    assert compute_partial_checkpoint_content_digest(roundtripped) == checkpoint.content_digest
    assert compute_partial_checkpoint_trajectory_digest(roundtripped) == checkpoint.token_provenance.trajectory_digest


def test_stage14_2_partial_checkpoint_json_roundtrip() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())

    reparsed = PartialEpisodeCheckpoint.model_validate_json(checkpoint.model_dump_json())

    assert reparsed.checkpoint_id == "checkpoint-0"
    assert reparsed.content_digest == checkpoint.content_digest


def test_stage14_2_partial_checkpoint_visibility_digest_uses_batch_safe_projection() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())

    digest = compute_partial_checkpoint_visibility_digest(checkpoint)

    assert digest.startswith("sha256:")


def test_stage14_2_partial_checkpoint_queue_facts_are_never_policy_loss_valid() -> None:
    checkpoint = PartialEpisodeCheckpoint.model_validate(build_stage14_2_checkpoint_payload())

    facts = partial_checkpoint_to_queue_facts(checkpoint)

    assert facts.valid_for_policy_loss is False
    assert facts.sample_classification == "partial_checkpoint"
    assert facts.rejection_reason == "partial_checkpoint_not_trainable:partial"
    assert facts.content_digest == checkpoint.content_digest


def test_stage14_2_partial_checkpoint_schema_does_not_import_verl() -> None:
    import sys

    import repo_harness.rl.partial_checkpoint  # noqa: F401

    assert "verl" not in sys.modules
    assert "torch" not in sys.modules
    assert "ray" not in sys.modules


def test_stage14_2_partial_checkpoint_canonical_payload_is_json_serializable() -> None:
    payload = build_stage14_2_checkpoint_payload()

    encoded = json.dumps(payload, sort_keys=True)

    assert "runtime_private" in encoded
    assert "/workspace/" not in encoded


def test_stage14_2_canonical_fixture_roundtrips_through_schema() -> None:
    payload = json.loads((FIXTURE_DIR / "canonical_partial_checkpoint.json").read_text())
    report = json.loads((FIXTURE_DIR / "canonical_partial_checkpoint_roundtrip_report.json").read_text())
    visibility_report = json.loads((FIXTURE_DIR / "canonical_partial_checkpoint_visibility_report.json").read_text())

    checkpoint = PartialEpisodeCheckpoint.model_validate(payload)
    reparsed = validate_partial_checkpoint_roundtrip(checkpoint)

    assert reparsed.model_dump(mode="json") == checkpoint.model_dump(mode="json")
    assert report["roundtrip_valid"] is True
    assert report["content_digest"] == checkpoint.content_digest
    assert visibility_report["visibility_scan_status"] == "passed"
    assert visibility_report["visibility_digest"] == compute_partial_checkpoint_visibility_digest(checkpoint)


def test_stage14_2_public_projection_fixture_excludes_runtime_private_refs() -> None:
    public_projection = json.loads((FIXTURE_DIR / "canonical_partial_checkpoint_public_projection.json").read_text())
    encoded = json.dumps(public_projection, sort_keys=True)

    assert public_projection["schema_version"] == "repo_harness_stage14_2_public_projection_v0"
    assert public_projection["checkpoint_ref"] == "rh://partial-checkpoints/checkpoint-0"
    assert "runtime_private" not in encoded
    assert "runtime-private" not in encoded


def test_stage14_2_fixture_sha256_manifest_matches_files() -> None:
    manifest = json.loads((FIXTURE_DIR / "sha256_manifest.json").read_text())

    assert "sha256_manifest.json" not in manifest
    for relative_path, expected_digest in manifest.items():
        actual_digest = hashlib.sha256((FIXTURE_DIR / relative_path).read_bytes()).hexdigest()
        assert actual_digest == expected_digest, relative_path


@pytest.mark.parametrize("fixture_path", sorted(FIXTURE_DIR.glob("invalid_*.json")), ids=lambda path: path.name)
def test_stage14_2_invalid_fixtures_are_rejected(fixture_path: Path) -> None:
    payload = json.loads(fixture_path.read_text())
    expected_rejection_code = payload.pop("expected_rejection_code")

    if expected_rejection_code == "stale_checkpoint_cannot_enter_resume_preparation":
        checkpoint = PartialEpisodeCheckpoint.model_validate(payload)
        with pytest.raises(ValueError, match=expected_rejection_code):
            validate_partial_checkpoint_for_resume_preparation(checkpoint)
        return

    expected_message = expected_rejection_code
    if expected_rejection_code.endswith(" is required"):
        expected_message = f"{expected_rejection_code}|Field required"

    with pytest.raises((ValueError, ValidationError), match=expected_message):
        PartialEpisodeCheckpoint.model_validate(payload)
