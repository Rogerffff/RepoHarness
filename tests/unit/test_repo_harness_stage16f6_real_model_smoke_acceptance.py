from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.evaluation.stage16f6_smoke import (
    Stage16F6SmokeError,
    inspect_stage16f6_real_model_smoke,
)

from stage16f6_test_helpers import refresh_evidence_map, read_json, write_json, write_valid_stage16f6_evidence


def test_stage16f6_inspector_accepts_valid_public_evidence(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)

    payload = json.loads(inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True))

    assert payload["passed"] is True
    assert payload["real_model_case_count"] == 3
    assert payload["completed_real_model_episode_count"] == 3
    assert payload["policy_loss_candidate_count"] == 0


def test_stage16f6_cli_accepts_valid_public_evidence(tmp_path: Path, capsys) -> None:
    write_valid_stage16f6_evidence(tmp_path)

    exit_code = main(["inspect-stage16f6-real-model-smoke", str(tmp_path), "--assert-complete"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True


def test_stage16f6_inspector_rejects_summary_count_tamper(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    summary_path = tmp_path / "stage16f6_acceptance_summary.json"
    summary = read_json(summary_path)
    summary["real_model_case_count"] = 999
    write_json(summary_path, summary)

    with pytest.raises(Stage16F6SmokeError, match="acceptance_summary_field_mismatch:real_model_case_count"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_rejects_canonical_map_sha_tamper(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    map_path = tmp_path / "stage16f6_canonical_evidence_map.json"
    payload = read_json(map_path)
    payload["items"][0]["sha256"] = "0" * 64
    write_json(map_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="canonical_evidence_map_sha256_mismatch"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_rejects_unknown_public_evidence_file(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    (tmp_path / "extra_public_report.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(Stage16F6SmokeError, match="unknown_public_evidence_file:extra_public_report.json"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_requires_run_episode_task_invocation_count(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    report_path = tmp_path / "stage16f6_real_model_run_report.json"
    report = read_json(report_path)
    report["run_episode_task_invocation_count"] = 0
    write_json(report_path, report)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="run_episode_task_invocation_count_mismatch"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_requires_case_manifest_run_episode_task_entrypoint(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    manifest_path = tmp_path / "stage16f6_case_manifest.json"
    manifest = read_json(manifest_path)
    manifest["cases"][0]["entrypoint"] = "run_task"
    write_json(manifest_path, manifest)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="case_manifest_entrypoint_not_run_episode_task:case-001"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_rejects_public_secret_marker(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    report_path = tmp_path / "stage16f6_test_report.json"
    report = read_json(report_path)
    report["bad"] = "provider_secret"
    write_json(report_path, report)

    with pytest.raises(Stage16F6SmokeError, match="path_or_secret_leak"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_rejects_patch_projection_digest_mismatch(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    report_path = tmp_path / "stage16f6_patch_hygiene_report.json"
    report = read_json(report_path)
    report["case_patch_hygiene_results"][0]["final_patch_sha256"] = "0" * 64
    report["case_patch_hygiene_results"][0]["cleaned_patch_sha256"] = "0" * 64
    write_json(report_path, report)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="patch_projection_digest_mismatch:case-001:final_patch_sha256"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_rejects_projection_validation_errors(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    report_path = tmp_path / "stage16f6_projection_validation_report.json"
    report = read_json(report_path)
    report["case_projection_results"][0]["projection_validation_errors"] = ["final.patch missing"]
    write_json(report_path, report)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="projection_validation_errors_nonempty:case-001"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_requires_projection_validation_errors_field(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    report_path = tmp_path / "stage16f6_projection_validation_report.json"
    report = read_json(report_path)
    report["case_projection_results"][0].pop("projection_validation_errors")
    write_json(report_path, report)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="projection_validation_errors_nonempty:case-001"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_inspector_rejects_runtime_private_projection_artifact_tamper(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    manifest = read_json(tmp_path / "runtime_private" / "runtime_private_manifest.json")
    final_patch_item = next(item for item in manifest["items"] if item["artifact_kind"] == "final-patch")
    artifact_path = tmp_path / final_patch_item["relative_path"]
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tampered")

    with pytest.raises(Stage16F6SmokeError, match="runtime_private_artifact_sha256_mismatch"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)
