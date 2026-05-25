from __future__ import annotations

from pathlib import Path

import pytest

from repo_harness.evaluation.stage16f6_smoke import (
    Stage16F6SmokeError,
    inspect_stage16f6_real_model_smoke,
)

from stage16f6_test_helpers import refresh_evidence_map, read_json, write_json, write_valid_stage16f6_evidence


def test_stage16f6_rejects_missing_docker_optional_report(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    (tmp_path / "stage16f6_docker_optional_report.json").unlink()

    with pytest.raises(Stage16F6SmokeError, match="missing_public_evidence_file:stage16f6_docker_optional_report.json"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_failed_docker_optional_report(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    docker_path = tmp_path / "stage16f6_docker_optional_report.json"
    payload = read_json(docker_path)
    payload["docker_case_status"] = "failed"
    write_json(docker_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="docker_case_status_failed"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_executed_docker_without_image_binding(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    docker_path = tmp_path / "stage16f6_docker_optional_report.json"
    payload = read_json(docker_path)
    payload["docker_case_status"] = "executed"
    payload.pop("selected_image_ref")
    write_json(docker_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="docker_executed_missing_field:selected_image_ref"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_swebench_cached_image_without_full_binding(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    docker_path = tmp_path / "stage16f6_docker_optional_report.json"
    payload = read_json(docker_path)
    payload["swebench_cached_image_used"] = True
    payload.pop("reason_swebench_cached_image_not_used")
    write_json(docker_path, payload)

    with pytest.raises(Stage16F6SmokeError, match="swebench_cached_image_missing_binding:task_manifest_ref"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_swebench_like_image_ref_when_not_declared(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    docker_path = tmp_path / "stage16f6_docker_optional_report.json"
    payload = read_json(docker_path)
    payload["docker_case_status"] = "executed"
    payload["selected_image_ref"] = "sweb.env.py.x86_64.fake:latest"
    payload["swebench_cached_image_used"] = False
    write_json(docker_path, payload)
    summary_path = tmp_path / "stage16f6_acceptance_summary.json"
    summary = read_json(summary_path)
    summary["docker_case_status"] = "executed"
    write_json(summary_path, summary)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="swebench_cached_image_ref_not_declared"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)


def test_stage16f6_rejects_swebench_cached_image_with_invalid_digest_bindings(tmp_path: Path) -> None:
    write_valid_stage16f6_evidence(tmp_path)
    docker_path = tmp_path / "stage16f6_docker_optional_report.json"
    payload = read_json(docker_path)
    payload.update(
        {
            "docker_case_status": "executed",
            "selected_image_ref": "sweb.env.py.x86_64.fake:latest",
            "swebench_cached_image_used": True,
            "task_manifest_ref": "runtime-private:task-manifest:" + "1" * 64,
            "task_manifest_sha256": "not-a-sha",
            "source_snapshot_digest": "not-a-sha",
            "verifier_plan_digest": "not-a-sha",
            "image_digest": "not-a-digest",
            "why_safe_for_stage16f6": "synthetic invalid binding probe",
        }
    )
    payload.pop("reason_swebench_cached_image_not_used", None)
    write_json(docker_path, payload)
    summary_path = tmp_path / "stage16f6_acceptance_summary.json"
    summary = read_json(summary_path)
    summary["docker_case_status"] = "executed"
    write_json(summary_path, summary)
    refresh_evidence_map(tmp_path)

    with pytest.raises(Stage16F6SmokeError, match="swebench_cached_image_invalid_sha256_binding:task_manifest_sha256"):
        inspect_stage16f6_real_model_smoke(tmp_path, assert_complete=True)
