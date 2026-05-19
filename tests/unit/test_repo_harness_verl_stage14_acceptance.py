from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from repo_harness_verl.stage14_acceptance import (
    STAGE14_CANONICAL_EVIDENCE_ITEMS,
    inspect_stage14_fully_async_acceptance,
    inspect_stage14_fully_async_acceptance_report,
    validate_stage14_evidence_tarball,
)


def test_stage14_acceptance_inspector_accepts_complete_sanitized_evidence(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert report.passed is True
    assert report.failures == []
    payload = json.loads(inspect_stage14_fully_async_acceptance(evidence, assert_complete=True))
    assert payload["passed"] is True


def test_stage14_acceptance_inspector_rejects_missing_canonical_file(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_parameter_sync_report.json").unlink()

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert report.passed is False
    assert any("stage14_parameter_sync_report.json" in failure for failure in report.failures)


def test_stage14_acceptance_inspector_rejects_policy_loss_invalid_sample(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_policy_loss_gate_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["invalid_consumed_sample_count"] = 1
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "policy_loss_gate_invalid_consumed_not_zero" in report.failures


def test_stage14_acceptance_inspector_rejects_public_path_leak(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_stdout.sanitized.log").write_text(
        "workspace leaked: /workspace/RepoHarness/runs/example\n",
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert any("public_evidence_path_or_secret_leak:stage14_stdout.sanitized.log" in failure for failure in report.failures)


def test_stage14_acceptance_inspector_rejects_public_runtime_private_ref(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_resource_cleanup_report.json").write_text(
        json.dumps({"raw_log": "runtime_private/stage14_stdout.raw.log"}),
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "public_evidence_references_runtime_private_path:stage14_resource_cleanup_report.json" in report.failures


def test_stage14_acceptance_inspector_requires_dirty_patch_manifest_entries(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path, remote_git_status_short=" M reference/verl/verl/trainer.py")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "dirty_worktree_without_patch_manifest_files" in report.failures


def test_stage14_acceptance_inspector_accepts_registered_dirty_patch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path, remote_git_status_short=" M reference/verl/verl/trainer.py")
    patch_manifest_path = evidence / "stage14_remote_patch_manifest.json"
    patch_manifest = {
        "files": [
            {
                "path": "reference/verl/verl/trainer.py",
                "sha256": "sha256:trainer-patch",
                "purpose": "trainer batch provenance hook",
                "git_status_code": "M",
                "enabled_by_command_or_import": "PYTHONPATH=src:reference/verl",
                "rollback_or_cleanup_note": "discard remote patch before reuse",
                "public_or_private": "public",
            }
        ]
    }
    patch_manifest_path.write_text(json.dumps(patch_manifest, sort_keys=True), encoding="utf-8")
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["remote_patch_manifest_sha256"] = _sha256_file(patch_manifest_path)
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert report.failures == []


def test_stage14_acceptance_inspector_rejects_dirty_patch_status_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path, remote_git_status_short=" M reference/verl/verl/trainer.py")
    patch_manifest_path = evidence / "stage14_remote_patch_manifest.json"
    patch_manifest = {
        "files": [
            {
                "path": "reference/verl/verl/trainer.py",
                "sha256": "sha256:trainer-patch",
                "purpose": "trainer batch provenance hook",
                "git_status_code": "??",
                "enabled_by_command_or_import": "PYTHONPATH=src:reference/verl",
                "rollback_or_cleanup_note": "discard remote patch before reuse",
                "public_or_private": "public",
            }
        ]
    }
    patch_manifest_path.write_text(json.dumps(patch_manifest, sort_keys=True), encoding="utf-8")
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["remote_patch_manifest_sha256"] = _sha256_file(patch_manifest_path)
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "dirty_worktree_git_status_code_mismatch:reference/verl/verl/trainer.py" in report.failures


def test_stage14_acceptance_inspector_rejects_zero_trainer_progress(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["completed_trainer_step_count"] = 0
    summary["current_param_version"] = 0
    summary["valid_sample_count"] = 0
    summary["post_sync_valid_sample_count"] = 0
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "completed_trainer_step_count_below_stage14_minimum" in report.failures
    assert "current_param_version_below_stage14_minimum" in report.failures
    assert "valid_sample_count_below_stage14_minimum" in report.failures
    assert "post_sync_valid_sample_count_below_stage14_minimum" in report.failures


def test_stage14_acceptance_inspector_rejects_stdout_fatal_pattern(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_stdout.sanitized.log").write_text(
        "Traceback: RepoHarnessVerlAdapterError\n",
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_stdout_contains_fatal_pattern:RepoHarnessVerlAdapterError" in report.failures
    assert "stage14_stdout_contains_fatal_pattern:Traceback" in report.failures


def test_stage14_acceptance_inspector_rejects_patch_manifest_sha_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["remote_patch_manifest_sha256"] = "sha256:" + "0" * 64
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "remote_patch_manifest_sha256_mismatch" in report.failures


def test_stage14_acceptance_inspector_rejects_training_profile_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    profile_path = evidence / "stage14_training_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["model_id"] = "Qwen/Qwen2.5-Coder-7B-Instruct"
    profile["training_strategy"] = "lora"
    profile["lora_rank"] = 8
    profile_path.write_text(json.dumps(profile, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "summary_profile_mismatch:model_id" in report.failures
    assert "summary_profile_training_strategy_full_mode_mismatch" in report.failures


def test_stage14_acceptance_inspector_rejects_hydra_override_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_hydra_overrides.json").write_text(
        json.dumps(
            [
                "actor_rollout_ref.model.path=Qwen/Qwen2.5-Coder-7B-Instruct",
                "actor_rollout_ref.rollout.name=sglang",
                "async_training.require_batches=1",
                "actor_rollout_ref.model.lora_rank=0",
                "actor_rollout_ref.rollout.checkpoint_engine.backend=nccl",
            ],
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "summary_hydra_mismatch:model_id" in report.failures
    assert "stage14_hydra_overrides_nixl_weight_sync_requires_nixl_backend" in report.failures


def test_stage14_acceptance_inspector_rejects_environment_matrix_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    environment_path = evidence / "stage14_environment_matrix.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    environment["checkpoint_engine_backend"] = "nccl"
    environment_path.write_text(json.dumps(environment, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "profile_environment_matrix_mismatch:checkpoint_engine_backend" in report.failures


def test_stage14_acceptance_inspector_rejects_policy_loss_consumed_step_without_completed_step(
    tmp_path: Path,
) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_policy_loss_gate_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["sample_ledger"].append(
        {
            "sample_id": "sample-extra",
            "trajectory_digest": "sha256:trajectory-extra",
            "status": "succeeded",
            "reward_state": "final",
            "route": "verl",
            "generation_record_digest": "sha256:generation-extra",
            "visibility_scan_digest": "sha256:visibility-extra",
            "staleness": 0,
            "gate_decision": "accepted",
            "gate_rejection_reason": None,
            "side_channel_ref": None,
            "trainer_step_index": 99,
            "consumed_by_policy_loss": True,
        }
    )
    payload["consumed_sample_count"] += 1
    payload["accepted_for_policy_loss_count"] += 1
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "policy_loss_gate_consumed_step_not_completed:99" in report.failures


def test_stage14_acceptance_inspector_rejects_thin_batch_provenance_report(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_batch_provenance_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload.pop("response_ids_digest")
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "batch_provenance_missing_field:response_ids_digest" in report.failures


def test_stage14_acceptance_inspector_rejects_unregistered_public_helper(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    helper = evidence / "scripts" / "stage14_runtime.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("print('runtime helper')\n", encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "public_runtime_helper_missing_from_patch_manifest:scripts/stage14_runtime.py" in report.failures


def test_stage14_acceptance_inspector_rejects_public_pycache(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    pycache = evidence / "scripts" / "__pycache__" / "stage14_runtime.cpython-312.pyc"
    pycache.parent.mkdir(parents=True)
    pycache.write_bytes(b"pyc")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "public_evidence_pycache_not_allowed:scripts/__pycache__/stage14_runtime.cpython-312.pyc" in report.failures


def test_stage14_acceptance_inspector_rejects_policy_loss_ledger_missing_step(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_policy_loss_gate_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["sample_ledger"] = payload["sample_ledger"][:1]
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "policy_loss_gate_missing_valid_sample_for_completed_trainer_step" in report.failures


def test_stage14_acceptance_inspector_rejects_unfiltered_stale_ledger(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_staleness_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["sample_ledger"][1].pop("filtered_as_stale", None)
    payload["sample_ledger"][1]["gate_decision"] = "diagnostic"
    payload["sample_ledger"][1]["gate_rejection_reason"] = "other"
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stale_sample_missing_filtered_ledger_mark:sample-stale" in report.failures


def test_stage14_acceptance_inspector_rejects_trainer_steps_report_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_trainer_steps_report.json").write_text(
        json.dumps({"completed_trainer_step_count": 0, "steps": []}),
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "trainer_steps_completed_count_mismatch" in report.failures
    assert "trainer_steps_report_steps_below_completed_count" in report.failures


def test_stage14_acceptance_inspector_rejects_trainer_step_without_required_samples(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_trainer_steps_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    for row in payload["steps"]:
        row["consumed_valid_sample_count"] = 0
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "trainer_steps_report_step_below_required_samples:0" in report.failures
    assert "trainer_steps_report_step_below_required_samples:1" in report.failures
    assert "trainer_steps_report_step_below_required_samples:2" in report.failures


def test_stage14_acceptance_inspector_rejects_invalid_canonical_content(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_train.parquet").write_text("not parquet", encoding="utf-8")
    (evidence / "stage14_val.parquet").write_text("not parquet", encoding="utf-8")
    (evidence / "run_stage14_fully_async_smoke.sh").write_text("echo no shebang\n", encoding="utf-8")
    (evidence / "repo_harness_agent_loop_config.yaml").write_text("- name: wrong\n", encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_train.parquet_missing_parquet_magic" in report.failures
    assert "stage14_val.parquet_missing_parquet_magic" in report.failures
    assert "run_stage14_fully_async_smoke_missing_shebang" in report.failures
    assert "repo_harness_agent_loop_config_missing_name" in report.failures
    assert "repo_harness_agent_loop_config_missing_target" in report.failures


def test_stage14_acceptance_inspector_rejects_policy_loss_step_below_required_samples(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["required_samples"] = 2
    summary["message_queue_consumed_sample_count"] = 6
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")
    report_path = evidence / "stage14_policy_loss_gate_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["required_samples"] = 2
    payload["accepted_for_policy_loss_count"] = 6
    payload["consumed_sample_count"] = 6
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "policy_loss_gate_step_below_required_samples:0" in report.failures
    assert "policy_loss_gate_consumed_count_mismatch_ledger" in report.failures


def test_stage14_acceptance_inspector_rejects_policy_loss_step_index_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    report_path = evidence / "stage14_policy_loss_gate_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    for row in payload["sample_ledger"]:
        row["trainer_step_index"] += 1
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "policy_loss_gate_missing_valid_sample_for_completed_trainer_step" in report.failures
    assert "policy_loss_gate_step_below_required_samples:0" in report.failures


def test_stage14_acceptance_inspector_rejects_staleness_summary_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    (evidence / "stage14_staleness_report.json").write_text(
        json.dumps({"sample_ledger": []}),
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "staleness_report_stale_count_mismatch" in report.failures
    assert "staleness_report_filtered_stale_count_mismatch" in report.failures


def test_stage14_acceptance_inspector_rejects_staleness_max_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["max_observed_staleness"] = 0
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "staleness_report_max_observed_staleness_mismatch" in report.failures


def test_stage14_acceptance_inspector_requires_max_observed_staleness(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    staleness_report_path = evidence / "stage14_staleness_report.json"
    staleness_report = json.loads(staleness_report_path.read_text(encoding="utf-8"))
    staleness_report["sample_ledger"] = [
        {"sample_id": "sample-1", "staleness": 0, "consumed_by_policy_loss": True}
    ]
    staleness_report_path.write_text(json.dumps(staleness_report, sort_keys=True), encoding="utf-8")
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["stale_sample_count"] = 0
    summary["filtered_stale_sample_count"] = 0
    summary.pop("max_observed_staleness")
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "acceptance_summary_missing_field:max_observed_staleness" in report.failures
    assert "max_observed_staleness_must_be_number" in report.failures


def test_stage14_acceptance_inspector_accepts_safe_tarball(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path / "source")
    tar_path = tmp_path / "stage14_evidence.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        for path in evidence.rglob("*"):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(evidence).as_posix())

    report = inspect_stage14_fully_async_acceptance_report(tar_path, assert_complete=True)

    assert report.passed is True


def test_stage14_tarball_safety_rejects_traversal_and_links(tmp_path: Path) -> None:
    tar_path = tmp_path / "unsafe.tar.gz"
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(target, arcname="../escape.txt")
        link_info = tarfile.TarInfo("link")
        link_info.type = tarfile.SYMTYPE
        link_info.linkname = "/etc/passwd"
        tar.addfile(link_info)

    failures = validate_stage14_evidence_tarball(tar_path)

    assert any("path_traversal_tar_entry_not_allowed" in failure for failure in failures)
    assert any("tar_link_entry_not_allowed" in failure for failure in failures)


def test_stage14_tarball_safety_rejects_internal_parent_segment(tmp_path: Path) -> None:
    tar_path = tmp_path / "unsafe_internal_parent.tar.gz"
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(target, arcname="safe/../normalized.txt")

    failures = validate_stage14_evidence_tarball(tar_path)

    assert any("path_traversal_tar_entry_not_allowed" in failure for failure in failures)


def test_stage14_tarball_safety_rejects_special_entries_and_size(tmp_path: Path) -> None:
    tar_path = tmp_path / "unsafe_special.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        hardlink = tarfile.TarInfo("hardlink")
        hardlink.type = tarfile.LNKTYPE
        hardlink.linkname = "target"
        tar.addfile(hardlink)
        fifo = tarfile.TarInfo("fifo")
        fifo.type = tarfile.FIFOTYPE
        tar.addfile(fifo)
        large = tarfile.TarInfo("large.txt")
        large.size = 2
        tar.addfile(large, fileobj=io.BytesIO(b"xx"))

    failures = validate_stage14_evidence_tarball(
        tar_path,
        max_single_file_bytes=1,
        max_total_bytes=10,
    )

    assert any("tar_link_entry_not_allowed" in failure for failure in failures)
    assert any("tar_special_entry_not_allowed" in failure for failure in failures)
    assert any("tar_file_too_large:large.txt" == failure for failure in failures)


def _write_stage14_evidence(
    root: Path,
    *,
    repo_git_status_short: str = "",
    remote_git_status_short: str = "",
) -> Path:
    evidence = root / "stage14"
    evidence.mkdir(parents=True)
    stdout = evidence / "stage14_stdout.sanitized.log"
    stdout.write_text("stage14 smoke complete\n", encoding="utf-8")
    patch_manifest = evidence / "stage14_remote_patch_manifest.json"
    patch_manifest.write_text(json.dumps({"files": []}, sort_keys=True), encoding="utf-8")

    mapping = {item: item for item in STAGE14_CANONICAL_EVIDENCE_ITEMS}
    summary = {
        "schema_version": "repo_harness_verl_stage14_acceptance_summary_v0",
        "stage": "14.0",
        "acceptance_passed": True,
        "created_at": "2026-05-19T00:00:00Z",
        "repo_harness_commit": "abc123",
        "repo_harness_git_status_short": repo_git_status_short,
        "remote_git_status_short": remote_git_status_short,
        "required_samples": 1,
        "verl_commit_or_package_version": "reference-verl",
        "remote_patch_manifest_sha256": _sha256_file(patch_manifest),
        "training_profile_name": "dev_smoke_2x96gb_small_full_sync",
        "image": "verlai/verl:sgl056.latest",
        "instance_id": "stage14-local-fixture",
        "gpu_count": 2,
        "gpu_memory_gb_per_device": 96,
        "inference_backend": "sglang",
        "training_strategy": "full",
        "weight_sync_strategy": "nixl_cuda",
        "model_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "model_revision": "main",
        "tokenizer_revision": "main",
        "chat_template_digest": "sha256:chat-template",
        "fixture_manifest_sha256": "sha256:fixture",
        "remote_command_exit_code": 0,
        "completed_trainer_step_count": 3,
        "parameter_sync_count": 2,
        "current_param_version": 2,
        "valid_sample_count": 3,
        "final_verifier_rejected_trainable_count": 1,
        "formal_validator_rejected_count": 1,
        "diagnostic_sample_count": 1,
        "policy_loss_gate_passed": True,
        "policy_loss_gate_mode": "source_gate",
        "policy_loss_queue_invalid_sample_count": 0,
        "message_queue_produced_sample_count": 3,
        "message_queue_consumed_sample_count": 3,
        "message_queue_dropped_sample_count": 0,
        "post_sync_valid_sample_count": 1,
        "staleness_threshold": 1,
        "stale_sample_count": 1,
        "filtered_stale_sample_count": 1,
        "max_observed_staleness": 2,
        "trainer_batch_logprob_provenance_passed": True,
        "trainer_batch_digest": "sha256:trainer-batch",
        "visibility_scan_passed": True,
        "path_leak_scan_passed": True,
        "resource_cleanup_passed": True,
        "stdout_sha256": _sha256_file(stdout),
        "evidence_tarball_sha256": "sha256:not-built-for-unit-test",
        "instance_final_status": "exited",
        "canonical_evidence_map": mapping,
        "known_scope_notes": [],
    }

    policy_report = {
        "policy_loss_gate_mode": "source_gate",
        "policy_loss_gate_passed": True,
        "produced_sample_count": 3,
        "accepted_for_policy_loss_count": 3,
        "rejected_sample_count": 1,
        "side_channel_sample_count": 1,
        "consumed_sample_count": 3,
        "invalid_consumed_sample_count": 0,
        "required_samples": 1,
        "sample_ledger": [
            {
                "sample_id": f"sample-{index}",
                "trajectory_digest": f"sha256:trajectory-{index}",
                "status": "succeeded",
                "reward_state": "final",
                "route": "verl",
                "generation_record_digest": f"sha256:generation-{index}",
                "visibility_scan_digest": f"sha256:visibility-{index}",
                "staleness": 0,
                "gate_decision": "accepted",
                "gate_rejection_reason": None,
                "side_channel_ref": None,
                "trainer_step_index": index,
                "consumed_by_policy_loss": True,
            }
            for index in range(3)
        ],
    }
    staleness_report = {
        "sample_ledger": [
            {"sample_id": "sample-1", "staleness": 0, "consumed_by_policy_loss": True},
            {
                "sample_id": "sample-stale",
                "staleness": 2,
                "consumed_by_policy_loss": False,
                "filtered_as_stale": True,
                "gate_decision": "filtered_stale",
                "gate_rejection_reason": "stale_trajectory",
            },
        ]
    }

    special_payloads = {
        "stage14_acceptance_summary.json": summary,
        "stage14_environment_matrix.json": {
            "schema_version": "repo_harness_stage14_environment_matrix_v0",
            "execution_profile": "dev_smoke_2x96gb_small_full_sync",
            "gpu_count": 2,
            "gpu_memory_gb_per_device": 96,
            "image": "verlai/verl:sgl056.latest",
            "instance_id": "stage14-local-fixture",
            "inference_backend": "sglang",
            "checkpoint_engine_backend": "nixl",
            "python": "3.12.3",
        },
        "stage14_training_profile.json": {
            "schema_version": "repo_harness_verl_stage14_remote_smoke_profile_v0",
            "profile_name": "dev_smoke_2x96gb_small_full_sync",
            "gpu_count": 2,
            "gpu_memory_gb_per_device": 96,
            "model_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
            "inference_backend": "sglang",
            "training_strategy": "full",
            "weight_sync_strategy": "nixl_cuda",
            "required_samples": 1,
            "staleness_threshold": 1,
            "checkpoint_engine_backend": "nixl",
            "checkpoint_engine_device": "cuda",
            "lora_rank": 0,
            "lora_target_modules": [],
            "lora_merge": False,
        },
        "stage14_policy_loss_gate_report.json": policy_report,
        "stage14_staleness_report.json": staleness_report,
        "stage14_batch_provenance_report.json": {
            "schema_version": "repo_harness_verl_stage14_batch_provenance_report_v0",
            "trainer_batch_logprob_provenance_passed": True,
            "trainer_batch_digest": "sha256:trainer-batch",
            "response_ids_digest": "sha256:response-ids",
            "response_mask_digest": "sha256:response-mask",
            "rollout_log_probs_digest": "sha256:rollout-log-probs",
            "response_ids_shape": [3, 8],
            "response_mask_shape": [3, 8],
            "rollout_log_probs_shape": [3, 8],
        },
        "stage14_trainer_steps_report.json": {
            "completed_trainer_step_count": 3,
            "steps": [
                {
                    "trainer_step_index": index,
                    "trainer_batch_digest": f"sha256:trainer-batch-{index}",
                    "consumed_valid_sample_count": 1,
                    "current_param_version": 2 if index == 2 else index,
                }
                for index in range(3)
            ],
        },
        "runtime_private_manifest.json": {"private_files": ["runtime_private/stage14_stdout.raw.log"]},
        "stage14_remote_patch_manifest.json": {"files": []},
    }
    for item in STAGE14_CANONICAL_EVIDENCE_ITEMS:
        path = evidence / item
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if item in {"stage14_train.parquet", "stage14_val.parquet"}:
            path.write_bytes(b"PAR1stage14-fixturePAR1")
        elif item == "run_stage14_fully_async_smoke.sh":
            path.write_text(
                "#!/usr/bin/env bash\n"
                "python -m verl.experimental.fully_async_policy.fully_async_main \\\n"
                "  actor_rollout_ref.rollout.agent.agent_loop_config_path=repo_harness_agent_loop_config.yaml\n"
                "repo-harness inspect-stage14-fully-async-acceptance evidence --assert-complete\n",
                encoding="utf-8",
            )
        elif item == "repo_harness_agent_loop_config.yaml":
            path.write_text(
                "- name: repo_harness\n"
                "  _target_: repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop\n",
                encoding="utf-8",
            )
        else:
            payload = special_payloads.get(item, {"ok": True, "item": item})
            path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "stage14_acceptance_summary.json").write_text(
        json.dumps(summary, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
