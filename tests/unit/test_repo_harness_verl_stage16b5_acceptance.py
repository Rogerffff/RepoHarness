from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Any

from repo_harness_verl.stage16b5_acceptance import (
    STAGE16B5_CANONICAL_EVIDENCE_ITEMS,
    inspect_stage16b5_docker_backend_acceptance,
    inspect_stage16b5_docker_backend_acceptance_report,
    validate_stage16b5_evidence_tarball,
)


def test_stage16b5_acceptance_inspector_accepts_complete_evidence(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert report.passed is True
    assert report.failures == []
    payload = json.loads(inspect_stage16b5_docker_backend_acceptance(evidence, assert_complete=True))
    assert payload["passed"] is True


def test_stage16b5_acceptance_rejects_missing_canonical_file(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    (evidence / "stage16b5_container_cleanup_report.json").unlink()

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "missing_canonical_evidence:stage16b5_container_cleanup_report.json" in report.failures


def test_stage16b5_acceptance_rejects_running_instance_status(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    _update_json(evidence / "stage16b5_acceptance_summary.json", instance_final_status="running")

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "assert_complete_instance_not_stopped_paused_exited_or_terminated" in report.failures


def test_stage16b5_acceptance_rejects_missing_docker_gpu_probe(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    _update_json(evidence / "stage16b5_acceptance_summary.json", container_nvidia_smi_status="failed")
    _update_json(evidence / "stage16b5_docker_preflight_report.json", container_nvidia_smi_status="failed")

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "summary_container_nvidia_smi_status_not_passed" in report.failures
    assert "preflight_container_nvidia_smi_not_passed" in report.failures


def test_stage16b5_acceptance_rejects_local_process_candidate(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    _update_json(evidence / "stage16b5_training_eligibility_report.json", local_process_policy_loss_candidate_count=1)

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "training_eligibility_local_process_candidate_not_zero" in report.failures


def test_stage16b5_acceptance_rejects_missing_formal_token_provenance(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    smoke = _load_json(evidence / "stage16b5_docker_diagnostic_smoke_report.json")
    smoke["sample"].pop("generation_records_count")
    smoke["sample"].pop("response_logprobs_count")
    smoke["sample"]["token_provenance_passed"] = False
    _write_json(evidence / "stage16b5_docker_diagnostic_smoke_report.json", smoke)
    _update_json(
        evidence / "stage16b5_formal_online_rl_gate_report.json",
        generation_records_count=0,
        token_provenance_passed=False,
    )

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "diagnostic_smoke_sample_generation_records_count_below_minimum" in report.failures
    assert "diagnostic_smoke_sample_response_logprobs_count_mismatch" in report.failures
    assert "diagnostic_smoke_sample_token_provenance_not_passed" in report.failures
    assert "formal_gate_report_generation_records_count_below_minimum" in report.failures
    assert "formal_gate_report_token_provenance_not_passed" in report.failures


def test_stage16b5_acceptance_rejects_running_raw_run_status(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    diagnostic_run = evidence / "runtime_private" / "diagnostic_run"
    diagnostic_run.mkdir()
    _write_json(
        diagnostic_run / "run_status.json",
        {"schema_version": "repo_harness_schema_v0", "run_id": "stage16b5", "status": "RUNNING"},
    )

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert (
        "runtime_private_run_status_still_running:runtime_private/diagnostic_run/run_status.json"
        in report.failures
    )


def test_stage16b5_acceptance_rejects_smoke_and_formal_gate_digest_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    smoke = _load_json(evidence / "stage16b5_docker_diagnostic_smoke_report.json")
    smoke["sample"]["generation_record_digest"] = "sha256:different-generation-record"
    smoke["sample"]["formal_sample_digest"] = "sha256:different-formal-sample"
    _write_json(evidence / "stage16b5_docker_diagnostic_smoke_report.json", smoke)

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "formal_gate_report_generation_record_digest_mismatch_smoke_sample" in report.failures
    assert "formal_gate_report_formal_sample_digest_mismatch_smoke_sample" in report.failures


def test_stage16b5_acceptance_rejects_missing_remote_reproducibility_metadata(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    _update_json(evidence / "stage16b5_acceptance_summary.json", remote_backend_provider="")
    _update_json(evidence / "stage16b5_docker_preflight_report.json", preflight_image_digest="")

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "summary_missing_remote_reproducibility_field:remote_backend_provider" in report.failures
    assert "preflight_missing_remote_reproducibility_field:preflight_image_digest" in report.failures


def test_stage16b5_acceptance_rejects_shared_dependency_report_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    _update_json(
        evidence / "stage16b5_shared_dependency_guard_report.json",
        shared_dependency_guard_passed=False,
        dependency_mutation_rejected_count=0,
    )

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert "shared_dependency_guard_report_not_passed" in report.failures
    assert "shared_dependency_guard_report_rejected_count_below_minimum" in report.failures


def test_stage16b5_acceptance_rejects_public_path_leak(tmp_path: Path) -> None:
    evidence = _write_stage16b5_evidence(tmp_path)
    (evidence / "stage16b5_command_log.sanitized.jsonl").write_text(
        '{"command": "cd /root/RepoHarness && docker ps"}\n',
        encoding="utf-8",
    )

    report = inspect_stage16b5_docker_backend_acceptance_report(evidence, assert_complete=True)

    assert any(
        failure.startswith("public_evidence_path_or_secret_leak:stage16b5_command_log.sanitized.jsonl")
        for failure in report.failures
    )


def test_stage16b5_acceptance_tarball_safety_rejects_path_traversal(tmp_path: Path) -> None:
    tarball = tmp_path / "bad.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        payload = b"bad"
        info = tarfile.TarInfo("../bad.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    failures = validate_stage16b5_evidence_tarball(tarball)

    assert "path_traversal_tar_entry_not_allowed:../bad.txt" in failures


def _write_stage16b5_evidence(tmp_path: Path) -> Path:
    evidence = tmp_path / "stage16b5-evidence"
    evidence.mkdir()
    (evidence / "runtime_private").mkdir()

    summary: dict[str, Any] = {
        "schema_version": "repo_harness_verl_stage16b5_acceptance_summary_v0",
        "stage": "16B.5",
        "acceptance_passed": True,
        "training_profile_name": "remote_docker_capable_training_backend",
        "diagnostic_session_backend": "docker_persistent_container",
        "remote_docker_backend_preflight_passed": True,
        "remote_docker_diagnostic_profile_verified": True,
        "docker_daemon_available": True,
        "docker_server_version": "29.2.1",
        "remote_backend_provider": "spheron",
        "remote_instance_id": "stage16b5-unit-instance",
        "gpu_model": "NVIDIA A100-SXM4-40GB",
        "driver_version": "580.126.09",
        "cuda_version": "13.0",
        "docker_version": "29.2.1",
        "nvidia_container_toolkit_version": "available",
        "base_os": "Ubuntu 22.04 LTS",
        "preflight_image": "nvidia/cuda:12.8.0-base-ubuntu22.04",
        "preflight_image_digest": "sha256:12242992c121f6cab0ca11bccbaaf757db893b3065d7db74b933e59f321b2cf4",
        "nvidia_container_toolkit_available": True,
        "docker_gpus_all_status": "passed",
        "container_nvidia_smi_status": "passed",
        "container_nvidia_smi_passed": True,
        "repo_harness_docker_diagnostic_session_passed": True,
        "valid_docker_diagnostic_sample_count": 1,
        "invalid_docker_diagnostic_sample_count": 3,
        "formal_online_rl_candidate_count": 1,
        "formal_online_rl_gate_passed": True,
        "training_eligibility_gate_passed": True,
        "shared_dependency_guard_passed": True,
        "dependency_mutation_rejected_count": 1,
        "hidden_path_rejected_count": 1,
        "background_process_invalidated_count": 1,
        "path_leak_scan_passed": True,
        "public_path_leak_scan_passed": True,
        "runtime_private_evidence_present": True,
        "resource_cleanup_passed": True,
        "container_cleanup_passed": True,
        "background_process_cleanup_passed": True,
        "workspace_projection_sync_passed": True,
        "run_dir_mount_absent": True,
        "git_hidden_from_diagnostic_projection": True,
        "negative_cases_passed": True,
        "instance_final_status": "stopped",
    }
    preflight = {
        "schema_version": "repo_harness_verl_stage16b5_docker_preflight_report_v0",
        "root_access": True,
        "docker_daemon_available": True,
        "docker_server_version": "29.2.1",
        "remote_backend_provider": "spheron",
        "remote_instance_id": "stage16b5-unit-instance",
        "gpu_model": "NVIDIA A100-SXM4-40GB",
        "driver_version": "580.126.09",
        "cuda_version": "13.0",
        "docker_version": "29.2.1",
        "nvidia_container_toolkit_version": "available",
        "base_os": "Ubuntu 22.04 LTS",
        "preflight_image": "nvidia/cuda:12.8.0-base-ubuntu22.04",
        "preflight_image_digest": "sha256:12242992c121f6cab0ca11bccbaaf757db893b3065d7db74b933e59f321b2cf4",
        "docker_gpus_all_status": "passed",
        "container_nvidia_smi_status": "passed",
        "gpu_count": 1,
    }
    smoke = {
        "schema_version": "repo_harness_verl_stage16b5_docker_diagnostic_smoke_report_v0",
        "repo_harness_docker_diagnostic_session_passed": True,
        "diagnostic_session_backend": "docker_persistent_container",
        "run_dir_mount_enabled": False,
        "git_visible_in_projection": False,
        "workspace_projection_sync_status": "completed",
        "valid_docker_diagnostic_sample_count": 1,
        "sample": {
            "sample_id": "stage16b5-sample-0",
            "sample_destination": "formal_online_rl_candidate",
            "invalid_for_training": False,
            "invalid_for_online_rl": False,
            "route": "verl",
            "generation_records_count": 1,
            "response_ids_count": 2,
            "response_logprobs_count": 2,
            "response_spans_count": 1,
            "token_provenance_passed": True,
            "final_verifier_status": "accepted",
            "reward_boundary_passed": True,
            "generation_record_digest": "sha256:generation-record-digest",
            "formal_sample_digest": "sha256:formal-sample-digest",
        },
    }
    cleanup = {
        "schema_version": "repo_harness_verl_stage16b5_container_cleanup_report_v0",
        "container_cleanup_status": "completed",
        "container_cleanup_passed": True,
        "background_process_cleanup_passed": True,
        "orphan_container_cleanup_passed": True,
        "no_session_owned_container_left_running": True,
    }
    formal_gate = {
        "schema_version": "repo_harness_verl_stage16b5_formal_online_rl_gate_report_v0",
        "formal_online_rl_gate_passed": True,
        "accepted_candidate_count": 1,
        "invalid_candidate_accepted_count": 0,
        "route": "verl",
        "generation_records_count": 1,
        "response_ids_count": 2,
        "response_logprobs_count": 2,
        "response_spans_count": 1,
        "token_provenance_passed": True,
        "final_verifier_status": "accepted",
        "reward_boundary_passed": True,
        "generation_record_digest": "sha256:generation-record-digest",
        "formal_sample_digest": "sha256:formal-sample-digest",
        "accepted_sample_id": "stage16b5-sample-0",
    }
    eligibility = {
        "schema_version": "repo_harness_verl_stage16b5_training_eligibility_report_v0",
        "training_eligibility_gate_passed": True,
        "eligible_terminal_sample_count": 1,
        "cleanup_failed_policy_loss_candidate_count": 0,
        "session_invalidated_policy_loss_candidate_count": 0,
        "local_process_policy_loss_candidate_count": 0,
    }
    negative = {
        "schema_version": "repo_harness_verl_stage16b5_negative_cases_report_v0",
        "negative_cases_passed": True,
        "dependency_mutation_rejected_count": 1,
        "hidden_path_rejected_count": 1,
        "background_process_invalidated_count": 1,
        "negative_policy_loss_candidate_count": 0,
    }
    reports: dict[str, dict[str, Any]] = {
        "stage16b5_docker_preflight_report.json": preflight,
        "stage16b5_docker_diagnostic_smoke_report.json": smoke,
        "stage16b5_container_cleanup_report.json": cleanup,
        "stage16b5_formal_online_rl_gate_report.json": formal_gate,
        "stage16b5_training_eligibility_report.json": eligibility,
        "stage16b5_negative_cases_report.json": negative,
        "stage16b5_path_redaction_report.json": {
            "schema_version": "repo_harness_verl_stage16b5_path_redaction_report_v0",
            "path_leak_scan_passed": True,
            "public_path_leak_scan_passed": True,
        },
        "stage16b5_shared_dependency_guard_report.json": {
            "schema_version": "repo_harness_verl_stage16b5_shared_dependency_guard_report_v0",
            "shared_dependency_guard_passed": True,
            "dependency_mutation_rejected_count": 1,
        },
        "stage16b5_concurrency_isolation_report.json": {
            "schema_version": "repo_harness_verl_stage16b5_concurrency_isolation_report_v0",
            "concurrency_isolation_passed": True,
            "cross_session_workspace_leak_count": 0,
        },
        "stage16b5_remote_patch_manifest.json": {
            "schema_version": "repo_harness_verl_stage16b5_remote_patch_manifest_v0",
            "files": [],
        },
        "fixture_manifest.json": {
            "schema_version": "repo_harness_verl_stage16b5_fixture_manifest_v0",
            "fixtures": ["docker_diagnostic_smoke_repo"],
        },
        "fixture_sha256_report.json": {
            "schema_version": "repo_harness_verl_stage16b5_fixture_sha256_report_v0",
            "files": [],
        },
        "stage16b5_canonical_evidence_map.json": {
            "schema_version": "repo_harness_verl_stage16b5_canonical_evidence_map_v0",
            "items": {item: item for item in STAGE16B5_CANONICAL_EVIDENCE_ITEMS},
        },
    }
    for relative, payload in reports.items():
        _write_json(evidence / relative, payload)
    (evidence / "stage16b5_command_log.sanitized.jsonl").write_text(
        '{"name":"docker_gpus_all","returncode":0,"stdout_tail":"<sanitized>"}\n',
        encoding="utf-8",
    )
    (evidence / "runtime_private" / "stage16b5_command_log.raw.jsonl").write_text(
        '{"name":"docker_gpus_all","returncode":0}\n',
        encoding="utf-8",
    )
    _write_json(
        evidence / "runtime_private" / "raw_container_logs_manifest.json",
        {
            "schema_version": "repo_harness_verl_stage16b5_raw_container_logs_manifest_v0",
            "logs": [],
        },
    )
    summary.update(
        {
            "remote_patch_manifest_sha256": _sha256(evidence / "stage16b5_remote_patch_manifest.json"),
            "fixture_manifest_sha256": _sha256(evidence / "fixture_manifest.json"),
            "fixture_sha256_report_sha256": _sha256(evidence / "fixture_sha256_report.json"),
        }
    )
    _write_json(evidence / "stage16b5_acceptance_summary.json", summary)
    return evidence


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _update_json(path: Path, **updates: Any) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(updates)
    _write_json(path, payload)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
