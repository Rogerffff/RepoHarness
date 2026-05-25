from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.evaluation.episode_projection import (
    ProjectionValidationError,
    validate_run_episode_compat_projection,
)
from repo_harness.evaluation.episode_runner import run_episode_task
from repo_harness.schema_base import stable_hash


def _run_mock_episode(tmp_path: Path) -> Path:
    return run_episode_task(
        "tests/fixtures/tasks/task_001.yaml",
        config_path="tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml",
        output_dir=tmp_path / "runs",
        run_id="stage16f3_projection_mock",
        gateway_route="mock",
        assert_projection_complete=True,
    )


def test_stage16f3_projection_inspector_rejects_digest_tamper(tmp_path: Path) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    metrics_path = projection_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["run_outcome"] = "tampered"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ProjectionValidationError, match="projection_file_digest_mismatch:metrics.json"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_public_path_leak_even_with_matching_digest(
    tmp_path: Path,
) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    task_projection_path = projection_dir / "task_projection.json"
    manifest_path = projection_dir / "compat_projection_manifest.json"

    task_projection = json.loads(task_projection_path.read_text(encoding="utf-8"))
    task_projection["issue_statement"] = "debug path /Users/roger/private"
    task_projection_path.write_text(
        json.dumps(task_projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projection_file_digests"]["task_projection.json"] = stable_hash(task_projection)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ProjectionValidationError, match="path_or_secret_leak"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_missing_binding_field(tmp_path: Path) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    manifest_path = projection_dir / "compat_projection_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("resolved_verifier_plan_digest")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ProjectionValidationError, match="missing_manifest_field:resolved_verifier_plan_digest"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_missing_required_projection_file_and_digest(
    tmp_path: Path,
) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    route_path = projection_dir / "provider_route_qualification.json"
    manifest_path = projection_dir / "compat_projection_manifest.json"

    route_path.unlink()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projection_file_digests"].pop("provider_route_qualification.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = validate_run_episode_compat_projection(projection_dir, assert_complete=False)
    assert report["projection_complete"] is False
    assert "missing_projection_file_digest:provider_route_qualification.json" in report["errors"]
    assert "missing_projection_file:provider_route_qualification.json" in report["errors"]
    with pytest.raises(ProjectionValidationError, match="missing_projection_file_digest"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_includes_and_binds_final_patch_artifacts(tmp_path: Path) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    manifest = json.loads((projection_dir / "compat_projection_manifest.json").read_text(encoding="utf-8"))
    hygiene_report = json.loads(
        (projection_dir / "final_patch_hygiene_report.json").read_text(encoding="utf-8")
    )

    for filename in ("final.patch", "final.diff", "final_patch_hygiene_report.json"):
        assert (projection_dir / filename).exists()
        assert filename in manifest["projection_file_digests"]
    assert (projection_dir / "final.patch").read_text(encoding="utf-8") == (
        run_dir / "final.patch"
    ).read_text(encoding="utf-8")
    assert hygiene_report["cleaned_patch_sha256"] == manifest["final_patch_sha256"]
    assert hygiene_report["cleaned_diff_sha256"] == manifest["final_diff_sha256"]
    assert hygiene_report["projection_sanitization_status"] == "private_audit_fields_removed"
    for forbidden_key in (
        "raw_patch_sha256",
        "raw_diff_sha256",
        "raw_patch_ref",
        "raw_diff_ref",
        "raw_patch_nonempty",
        "raw_patch_visibility",
        "final_patch_ref",
        "final_diff_ref",
    ):
        assert forbidden_key not in hygiene_report


def test_stage16f3_projection_inspector_rejects_source_final_patch_tamper(tmp_path: Path) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    (run_dir / "final.patch").write_text("provider_secret leaked\n", encoding="utf-8")

    report = validate_run_episode_compat_projection(projection_dir, assert_complete=False)
    assert report["projection_complete"] is False
    assert "source_patch_artifact_mismatch:final.patch" in report["errors"]
    with pytest.raises(ProjectionValidationError, match="source_patch_artifact_mismatch:final.patch"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_compat_final_patch_leak(
    tmp_path: Path,
) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    patch_path = projection_dir / "final.patch"
    manifest_path = projection_dir / "compat_projection_manifest.json"

    patch_text = "provider_secret leaked\n"
    patch_path.write_text(patch_text, encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projection_file_digests"]["final.patch"] = stable_hash(patch_text)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ProjectionValidationError, match="path_or_secret_leak:final.patch:provider_secret"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_final_patch_hygiene_mismatch(
    tmp_path: Path,
) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    hygiene_path = projection_dir / "final_patch_hygiene_report.json"
    manifest_path = projection_dir / "compat_projection_manifest.json"

    hygiene_report = json.loads(hygiene_path.read_text(encoding="utf-8"))
    hygiene_report["cleaned_patch_sha256"] = "0" * 64
    hygiene_path.write_text(
        json.dumps(hygiene_report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projection_file_digests"]["final_patch_hygiene_report.json"] = stable_hash(hygiene_report)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ProjectionValidationError,
        match="final_patch_hygiene_cleaned_patch_sha256_mismatch",
    ):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_raw_patch_hygiene_fields(
    tmp_path: Path,
) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    hygiene_path = projection_dir / "final_patch_hygiene_report.json"
    manifest_path = projection_dir / "compat_projection_manifest.json"

    hygiene_report = json.loads(hygiene_path.read_text(encoding="utf-8"))
    hygiene_report["raw_patch_ref"] = {"kind": "raw_final_patch", "relative_path": "artifacts/raw.patch"}
    hygiene_path.write_text(
        json.dumps(hygiene_report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["projection_file_digests"]["final_patch_hygiene_report.json"] = stable_hash(hygiene_report)
    manifest["final_patch_hygiene_report_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ProjectionValidationError, match="forbidden_public_patch_hygiene_key:raw_patch_ref"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)


def test_stage16f3_projection_inspector_rejects_non_verl_policy_loss_tamper(tmp_path: Path) -> None:
    run_dir = _run_mock_episode(tmp_path)
    projection_dir = run_dir / "compat_projection"
    route_path = projection_dir / "provider_route_qualification.json"
    status_path = projection_dir / "compat_projection_status.json"
    manifest_path = projection_dir / "compat_projection_manifest.json"

    route_report = json.loads(route_path.read_text(encoding="utf-8"))
    route_report["policy_loss_candidate"] = True
    route_path.write_text(
        json.dumps(route_report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    status_report = json.loads(status_path.read_text(encoding="utf-8"))
    status_report["policy_loss_candidate"] = True
    status_path.write_text(
        json.dumps(status_report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["policy_loss_candidate"] = True
    manifest["projection_file_digests"]["provider_route_qualification.json"] = stable_hash(route_report)
    manifest["projection_file_digests"]["compat_projection_status.json"] = stable_hash(status_report)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ProjectionValidationError, match="non_verl_route_marked_policy_loss_candidate"):
        validate_run_episode_compat_projection(projection_dir, assert_complete=True)
