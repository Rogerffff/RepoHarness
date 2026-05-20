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


def test_stage14_1_acceptance_inspector_accepts_multitask_evidence(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert report.passed is True
    assert report.failures == []


def test_stage14_1_acceptance_inspector_rejects_side_channel_in_policy_loss_ledger(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["samples"].append(
        {
            "sample_id": "diagnostic-1",
            "episode_id": "episode-diagnostic",
            "task_id": "stage14_1_diagnostic_side_channel",
            "trajectory_digest": "sha256:diagnostic-trajectory",
            "trainer_step_index": 3,
            "global_steps": 3,
            "consumed_by_policy_loss": True,
            "side_channel_ref": None,
        }
    )
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_side_channel_sample_consumed_in_policy_loss_ledger:diagnostic-1" in report.failures


def test_stage14_1_acceptance_inspector_rejects_unbound_batch_provenance(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    provenance_path = evidence / "stage14_1_batch_provenance_report.json"
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    payload["sample_provenance"][0]["trajectory_digest"] = "sha256:wrong"
    provenance_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_batch_provenance_trajectory_digest_mismatch:sample-0" in report.failures


def test_stage14_1_acceptance_inspector_requires_real_side_channel_sample(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["side_channel_sample_count"] = 0
    summary["formal_validator_rejected_count"] = 1
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")
    side_report = json.loads((evidence / "stage14_1_side_channel_report.json").read_text(encoding="utf-8"))
    side_report["side_channel_sample_count"] = 0
    side_report["samples"] = []
    (evidence / "stage14_1_side_channel_report.json").write_text(
        json.dumps(side_report, sort_keys=True),
        encoding="utf-8",
    )

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_side_channel_sample_count_below_minimum" in report.failures
    assert "stage14_1_side_channel_samples_missing" in report.failures


def test_stage14_1_acceptance_inspector_rejects_running_or_paused_instance_summary(tmp_path: Path) -> None:
    for status in ("running", "paused"):
        evidence = _write_stage14_evidence(tmp_path / status)
        _upgrade_evidence_to_stage14_1(evidence)
        summary_path = evidence / "stage14_acceptance_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["instance_final_status"] = status
        summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

        report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

        assert "instance_final_status_not_stopped_or_exited" in report.failures
        assert "assert_complete_instance_not_stopped_or_exited" in report.failures


def test_stage14_1_acceptance_inspector_rejects_negative_status_rewritten_to_succeeded(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    report_path = evidence / "stage14_1_trainable_negative_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["eligible_samples"][0]["status"] = "succeeded"
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_trainable_negative_status_not_failed:sample-2" in report.failures


def test_stage14_1_acceptance_inspector_rejects_negative_report_identity_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    report_path = evidence / "stage14_1_trainable_negative_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["eligible_samples"][0]["task_id"] = "wrong-task"
    payload["eligible_samples"][0]["run_id"] = "wrong-run"
    payload["eligible_samples"][0]["episode_id"] = "wrong-episode"
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_trainable_negative_task_id_mismatch:sample-2" in report.failures
    assert "stage14_1_trainable_negative_run_id_mismatch:sample-2" in report.failures
    assert "stage14_1_trainable_negative_episode_id_mismatch:sample-2" in report.failures


def test_stage14_1_acceptance_inspector_rejects_negative_consumed_flag_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    report_path = evidence / "stage14_1_trainable_negative_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["eligible_samples"][0]["policy_loss_consumed"] = False
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_trainable_negative_policy_loss_consumed_flag_mismatch:sample-2" in report.failures
    assert "stage14_1_trainable_negative_consumed_flag_count_mismatch" in report.failures


def test_stage14_1_acceptance_inspector_requires_consumed_trainable_negative(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["trainable_negative_consumed_count"] = 0
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")
    report_path = evidence / "stage14_1_trainable_negative_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["trainable_negative_consumed_count"] = 0
    payload["eligible_samples"][0]["policy_loss_consumed"] = False
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_trainable_negative_consumed_count_below_minimum" in report.failures
    assert "stage14_1_trainable_negative_policy_loss_consumed_flag_mismatch:sample-2" in report.failures


def test_stage14_1_acceptance_inspector_rejects_policy_loss_bad_gate_semantics(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["samples"][0]["route"] = "mock"
    payload["samples"][0]["reward_state"] = "pending"
    payload["samples"][0]["gate_decision"] = "rejected"
    payload["samples"][0]["gate_rejection_reason"] = "visibility_rejected"
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_policy_loss_sample_ledger_non_verl_route:sample-0" in report.failures
    assert "stage14_1_policy_loss_sample_ledger_reward_not_final:sample-0" in report.failures
    assert "stage14_1_policy_loss_sample_ledger_gate_not_accepted:sample-0" in report.failures
    assert "stage14_1_policy_loss_sample_ledger_has_rejection_reason:sample-0" in report.failures
    assert "stage14_1_policy_loss_sample_ledger_gate_route_mismatch:sample-0" in report.failures


def test_stage14_1_acceptance_inspector_rejects_policy_loss_gate_identity_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    gate_path = evidence / "stage14_policy_loss_gate_report.json"
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    payload["sample_ledger"][0]["task_id"] = "wrong-task"
    payload["sample_ledger"][0]["episode_id"] = "wrong-episode"
    payload["sample_ledger"][0]["run_id"] = "wrong-run"
    gate_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_policy_loss_sample_ledger_gate_task_id_mismatch:sample-0" in report.failures
    assert "stage14_1_policy_loss_sample_ledger_gate_episode_id_mismatch:sample-0" in report.failures
    assert "stage14_1_policy_loss_sample_ledger_gate_run_id_mismatch:sample-0" in report.failures


def test_stage14_1_acceptance_inspector_rejects_unconsumed_policy_loss_ledger_row(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["samples"].append(
        {
            "sample_id": "sample-rejected",
            "episode_id": "episode-rejected",
            "run_id": "run-rejected",
            "task_id": "task-rejected",
            "trajectory_digest": "sha256:trajectory-rejected",
            "generation_record_digest": "sha256:generation-rejected",
            "visibility_scan_digest": "sha256:visibility-rejected",
            "status": "timeout",
            "reward_state": "pending",
            "route": "mock",
            "staleness": 0,
            "gate_decision": "rejected",
            "gate_rejection_reason": "visibility_rejected",
            "trainer_step_index": 0,
            "global_steps": 0,
            "parameter_version": 0,
            "min_global_steps": 0,
            "max_global_steps": 0,
            "artifact_ref": "rh://stage14/episode-rejected",
            "consumed_by_policy_loss": False,
            "side_channel_ref": "rh://stage14/diagnostic-rejected",
        }
    )
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_policy_loss_sample_ledger_unconsumed_row:sample-rejected" in report.failures


def test_stage14_1_acceptance_inspector_rejects_policy_loss_ledger_missing_artifact_ref(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["samples"][0].pop("artifact_ref")
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_policy_loss_sample_ledger[0]_missing_artifact_ref" in report.failures
    assert "stage14_1_episode_artifact_ref_artifact_ref_mismatch:sample-0" in report.failures


def test_stage14_1_acceptance_inspector_rejects_duplicate_consumed_sample_id(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["samples"][1]["sample_id"] = "sample-0"
    ledger_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_policy_loss_sample_ledger_duplicate_consumed_sample_id" in report.failures


def test_stage14_1_acceptance_inspector_rejects_extra_episode_artifact_ref_sample(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    report_path = evidence / "stage14_1_episode_artifact_ref_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["samples"].append(
        {
            "sample_id": "sample-extra",
            "episode_id": "episode-extra",
            "run_id": "run-extra",
            "task_id": "task-extra",
            "trajectory_digest": "sha256:trajectory-extra",
            "artifact_ref": "rh://stage14/episode-extra",
        }
    )
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_episode_artifact_ref_extra_sample:sample-extra" in report.failures


def test_stage14_1_acceptance_inspector_rejects_duplicate_episode_artifact_ref(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["samples"][1]["artifact_ref"] = "rh://stage14/episode-security"
    ledger_path.write_text(json.dumps(ledger, sort_keys=True), encoding="utf-8")
    report_path = evidence / "stage14_1_episode_artifact_ref_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["samples"][1]["artifact_ref"] = "rh://stage14/episode-security"
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_episode_artifact_ref_duplicate:rh://stage14/episode-security" in report.failures
    assert "stage14_1_episode_artifact_ref_not_resolvable:sample-1" in report.failures


def test_stage14_1_acceptance_inspector_rejects_missing_episode_artifact_ref_target(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    ledger_path = evidence / "stage14_1_policy_loss_sample_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["samples"][0]["artifact_ref"] = "rh://stage14/definitely-missing-run-artifact"
    ledger_path.write_text(json.dumps(ledger, sort_keys=True), encoding="utf-8")
    report_path = evidence / "stage14_1_episode_artifact_ref_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["samples"][0]["artifact_ref"] = "rh://stage14/definitely-missing-run-artifact"
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_episode_artifact_ref_not_resolvable:sample-0" in report.failures


def test_stage14_1_acceptance_inspector_rejects_episode_artifact_ref_run_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    report_path = evidence / "stage14_1_episode_artifact_ref_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["samples"][0]["run_id"] = "wrong-run"
    report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "stage14_1_episode_artifact_ref_run_id_mismatch:sample-0" in report.failures


def test_stage14_1_acceptance_inspector_rejects_missing_episode_artifact_ref_report(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    _upgrade_evidence_to_stage14_1(evidence)
    (evidence / "stage14_1_episode_artifact_ref_report.json").unlink()

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "missing_stage14_1_episode_artifact_ref_report" in report.failures


def test_stage14_1_acceptance_inspector_rejects_unapproved_runtime_private_summary_note(tmp_path: Path) -> None:
    evidence = _write_stage14_evidence(tmp_path)
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["debug_note"] = "see runtime_private/stage14_command_log.raw.jsonl"
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    report = inspect_stage14_fully_async_acceptance_report(evidence, assert_complete=True)

    assert "acceptance_summary_references_unapproved_runtime_private_path" in report.failures
    assert "public_evidence_references_runtime_private_path:stage14_acceptance_summary.json" in report.failures


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
                "task_id": ["task_security_probe", "task_002", "task_stage14_negative_boundary"][index],
                "episode_id": ["episode-security", "episode-config", "episode-negative"][index],
                "run_id": ["run-security", "run-config", "run-negative"][index],
                "trajectory_digest": f"sha256:trajectory-{index}",
                "status": "failed" if index == 2 else "succeeded",
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
        "runtime_private/stage14_command_log.raw.jsonl": {"raw": True},
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
        "runtime_private_manifest.json": {
            "private_files": [
                "runtime_private/stage14_stdout.raw.log",
                "runtime_private/stage14_command_log.raw.jsonl",
            ]
        },
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


def _upgrade_evidence_to_stage14_1(evidence: Path) -> None:
    summary_path = evidence / "stage14_acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(
        {
            "stage": "14.1",
            "unique_real_episode_count": 3,
            "unique_task_id_count": 3,
            "policy_loss_consumed_unique_episode_count": 3,
            "policy_loss_consumed_unique_task_id_count": 3,
            "trainable_negative_eligible_count": 1,
            "trainable_negative_consumed_count": 1,
            "side_channel_sample_count": 1,
            "post_sync_valid_sample_count": 2,
            "post_sync_policy_loss_consumed_sample_count": 2,
            "post_sync_policy_loss_consumed_unique_episode_count": 2,
            "post_sync_final_verifier_rejected_trainable_count": 1,
            "trajectory_param_versions": [0, 1, 2],
            "min_global_steps": [0, 1, 2],
            "max_global_steps": [0, 1, 2],
            "fresh_trainer_batch_tensor_provenance_passed": True,
            "batch_provenance_source": "trainer_hook",
        }
    )
    summary_path.write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")

    samples = [
        {
            "sample_id": "sample-0",
            "episode_id": "episode-security",
            "run_id": "run-security",
            "task_id": "task_security_probe",
            "trajectory_digest": "sha256:trajectory-0",
            "generation_record_digest": "sha256:generation-0",
            "visibility_scan_digest": "sha256:visibility-0",
            "status": "succeeded",
            "reward_state": "final",
            "route": "verl",
            "staleness": 0,
            "gate_decision": "accepted",
            "gate_rejection_reason": None,
            "trainer_step_index": 0,
            "global_steps": 0,
            "parameter_version": 0,
            "min_global_steps": 0,
            "max_global_steps": 0,
            "artifact_ref": "rh://stage14/episode-security",
            "consumed_by_policy_loss": True,
            "side_channel_ref": None,
        },
        {
            "sample_id": "sample-1",
            "episode_id": "episode-config",
            "run_id": "run-config",
            "task_id": "task_002",
            "trajectory_digest": "sha256:trajectory-1",
            "generation_record_digest": "sha256:generation-1",
            "visibility_scan_digest": "sha256:visibility-1",
            "status": "succeeded",
            "reward_state": "final",
            "route": "verl",
            "staleness": 0,
            "gate_decision": "accepted",
            "gate_rejection_reason": None,
            "trainer_step_index": 1,
            "global_steps": 1,
            "parameter_version": 1,
            "min_global_steps": 1,
            "max_global_steps": 1,
            "artifact_ref": "rh://stage14/episode-config",
            "consumed_by_policy_loss": True,
            "side_channel_ref": None,
        },
        {
            "sample_id": "sample-2",
            "episode_id": "episode-negative",
            "run_id": "run-negative",
            "task_id": "task_stage14_negative_boundary",
            "trajectory_digest": "sha256:trajectory-2",
            "generation_record_digest": "sha256:generation-2",
            "visibility_scan_digest": "sha256:visibility-2",
            "status": "failed",
            "reward_state": "final",
            "route": "verl",
            "staleness": 0,
            "gate_decision": "accepted",
            "gate_rejection_reason": None,
            "trainer_step_index": 2,
            "global_steps": 2,
            "parameter_version": 2,
            "min_global_steps": 2,
            "max_global_steps": 2,
            "artifact_ref": "rh://stage14/episode-negative",
            "consumed_by_policy_loss": True,
            "side_channel_ref": None,
        },
    ]
    policy_report_path = evidence / "stage14_policy_loss_gate_report.json"
    policy_report = json.loads(policy_report_path.read_text(encoding="utf-8"))
    for row in policy_report.get("sample_ledger", []):
        if row.get("sample_id") == "sample-2":
            row["status"] = "failed"
    policy_report_path.write_text(json.dumps(policy_report, sort_keys=True) + "\n", encoding="utf-8")
    (evidence / "stage14_1_policy_loss_sample_ledger.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_verl_stage14_1_policy_loss_sample_ledger_v0",
                "samples": samples,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "stage14_1_task_pool_report.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_verl_stage14_1_task_pool_report_v0",
                "task_pool_name": "stage14_1_default_multitask_pool",
                "task_count": 4,
                "unique_task_id_count": 3,
                "entries": [
                    {
                        "task_id": "task_security_probe",
                        "task_category": "accepted_baseline",
                        "repo_fixture_ref": "tests/fixtures/repos/security_probe",
                        "task_ref": "tests/fixtures/tasks/task_security_probe.yaml",
                        "expected_outcome_class": "accepted",
                    },
                    {
                        "task_id": "task_dependency_packaging_smoke",
                        "task_category": "accepted_dependency",
                        "repo_fixture_ref": "tests/fixtures/repos/dependency_packaging_smoke",
                        "task_ref": "tests/fixtures/tasks/task_dependency_packaging_smoke.yaml",
                        "expected_outcome_class": "accepted",
                        "dependency_packages": [
                            {
                                "name": "tomli",
                                "version": "2.0.1",
                                "artifact": "tomli-2.0.1-py3-none-any.whl",
                                "sha256": "939de3e7a6161af0c887ef91b7d41a53e7c5a1ca976325f429cb46ea9bc30ecc",
                            }
                        ],
                    },
                    {
                        "task_id": "task_stage14_negative_boundary",
                        "task_category": "trainable_negative_control",
                        "repo_fixture_ref": "tests/fixtures/repos/stage14_negative_boundary",
                        "task_ref": "tests/fixtures/tasks/task_stage14_negative_boundary.yaml",
                        "expected_outcome_class": "final_verifier_rejected_trainable",
                    },
                    {
                        "task_id": "stage14_1_diagnostic_side_channel",
                        "task_category": "diagnostic_control",
                        "repo_fixture_ref": "side-channel-only",
                        "task_ref": "side-channel-only",
                        "expected_outcome_class": "diagnostic_rejected",
                    },
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "stage14_1_trainable_negative_report.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_verl_stage14_1_trainable_negative_report_v0",
                "trainable_negative_eligible_count": 1,
                "trainable_negative_consumed_count": 1,
                "eligible_samples": [
                    {
                        "sample_id": "sample-2",
                        "attempt_id": "attempt-1",
                        "prompt_digest": "sha256:prompt-negative",
                        "task_id": "task_stage14_negative_boundary",
                        "episode_id": "episode-negative",
                        "run_id": "run-negative",
                        "trajectory_digest": "sha256:trajectory-2",
                        "generation_record_digest": "sha256:generation-2",
                        "visibility_scan_digest": "sha256:visibility-2",
                        "final_verifier_status": "rejected",
                        "reward_state": "final",
                        "reward_score": 0.0,
                        "route": "verl",
                        "status": "failed",
                        "invalid_for_training": False,
                        "invalid_for_online_rl": False,
                        "response_token_count": 8,
                        "response_logprob_count": 8,
                        "policy_loss_consumed": True,
                        "trainer_step_index": 2,
                    }
                ],
                "rejected_non_trainable_failure_samples": [],
                "attempts": [
                    {
                        "run_id": "run-negative",
                        "sample_id": "sample-2",
                        "attempt_id": "attempt-1",
                        "prompt_digest": "sha256:prompt-negative",
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "stage14_1_side_channel_report.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_verl_stage14_1_side_channel_report_v0",
                "side_channel_sample_count": 1,
                "by_reason": {"missing_logprobs": 1},
                "samples": [
                    {
                        "sample_id": "diagnostic-1",
                        "reason": "missing_logprobs",
                        "source": "postprocess",
                        "route": "verl",
                        "would_have_been_policy_loss_valid": False,
                        "policy_loss_queue_inserted": False,
                        "policy_loss_consumed": False,
                        "policy_loss_sample_ledger_ref": None,
                        "diagnostic_ref": "rh://stage14/diagnostic-1",
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "stage14_1_episode_artifact_ref_report.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_verl_stage14_1_episode_artifact_ref_report_v0",
                "samples": [
                    {
                        "sample_id": sample["sample_id"],
                        "episode_id": sample["episode_id"],
                        "run_id": sample["run_id"],
                        "task_id": sample["task_id"],
                        "trajectory_digest": sample["trajectory_digest"],
                        "artifact_ref": sample["artifact_ref"],
                    }
                    for sample in samples
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "stage14_1_batch_provenance_report.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_verl_stage14_1_batch_provenance_report_v0",
                "fresh_trainer_batch_tensor_provenance_passed": True,
                "batch_provenance_source": "trainer_hook",
                "sample_provenance": [
                    {
                        "sample_id": sample["sample_id"],
                        "trainer_step_index": sample["trainer_step_index"],
                        "trajectory_digest": sample["trajectory_digest"],
                        "response_ids_digest": f"sha256:response-ids-{sample['sample_id']}",
                        "response_mask_digest": f"sha256:response-mask-{sample['sample_id']}",
                        "rollout_log_probs_digest": f"sha256:rollout-log-probs-{sample['sample_id']}",
                        "response_ids_shape": [1, 8],
                        "response_mask_shape": [1, 8],
                        "rollout_log_probs_shape": [1, 8],
                    }
                    for sample in samples
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
