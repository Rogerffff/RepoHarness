from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Any

from repo_harness_verl.stage15_acceptance import (
    STAGE15_CANONICAL_EVIDENCE_ITEMS,
    inspect_stage15_partial_rollout_acceptance,
    inspect_stage15_partial_rollout_acceptance_report,
    validate_stage15_evidence_tarball,
)


def test_stage15_acceptance_inspector_accepts_complete_evidence(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert report.passed is True
    assert report.failures == []
    payload = json.loads(inspect_stage15_partial_rollout_acceptance(evidence, assert_complete=True))
    assert payload["passed"] is True


def test_stage15_acceptance_inspector_rejects_missing_canonical_file(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    (evidence / "stage15_parameter_sync_report.json").unlink()

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert any("stage15_parameter_sync_report.json" in failure for failure in report.failures)


def test_stage15_acceptance_inspector_rejects_partial_checkpoint_in_policy_loss(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    _update_json(evidence / "stage15_acceptance_summary.json", partial_policy_loss_consumed_sample_count=1)
    _update_json(evidence / "stage15_partial_checkpoint_report.json", policy_loss_consumed_partial_count=1)
    policy = _load_json(evidence / "stage15_policy_loss_gate_report.json")
    policy["partial_consumed_sample_count"] = 1
    _write_json(evidence / "stage15_policy_loss_gate_report.json", policy)

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert "partial_policy_loss_consumed_sample_count_not_zero" in report.failures
    assert "policy_loss_gate_partial_consumed_not_zero" in report.failures


def test_stage15_acceptance_inspector_rejects_missing_post_train_sync(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    _update_json(evidence / "stage15_acceptance_summary.json", post_train_parameter_sync_count=0)
    _update_json(evidence / "stage15_parameter_sync_report.json", post_train_parameter_sync_count=0)

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert "post_train_parameter_sync_count_below_stage15_minimum" in report.failures
    assert "parameter_sync_report_post_train_sync_below_minimum" in report.failures


def test_stage15_acceptance_inspector_rejects_duplicate_policy_loss_sample(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    report_path = evidence / "stage15_policy_loss_gate_report.json"
    payload = _load_json(report_path)
    payload["sample_ledger"][1]["policy_loss_consumed_sample_id"] = payload["sample_ledger"][0][
        "policy_loss_consumed_sample_id"
    ]
    _write_json(report_path, payload)

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert "policy_loss_gate_duplicate_consumed_sample_id" in report.failures


def test_stage15_acceptance_inspector_rejects_missing_logprob_consumed(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    _update_json(evidence / "stage15_acceptance_summary.json", missing_logprob_policy_loss_consumed_sample_count=1)

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert "missing_logprob_policy_loss_consumed_sample_count_not_zero" in report.failures


def test_stage15_acceptance_inspector_rejects_profile_or_hydra_mismatch(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    _update_json(evidence / "stage15_training_profile.json", training_strategy="lora")
    overrides = json.loads((evidence / "stage15_hydra_overrides.json").read_text(encoding="utf-8"))
    overrides.remove("async_training.partial_rollout=True")
    (evidence / "stage15_hydra_overrides.json").write_text(json.dumps(overrides, sort_keys=True), encoding="utf-8")

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert "summary_profile_mismatch:training_strategy" in report.failures
    assert "stage15_hydra_overrides_missing:async_training.partial_rollout=True" in report.failures


def test_stage15_acceptance_inspector_rejects_public_path_leak(tmp_path: Path) -> None:
    evidence = _write_stage15_evidence(tmp_path)
    (evidence / "stage15_command_log.sanitized.jsonl").write_text(
        '{"cmd": "cd /workspace/RepoHarness && run"}\n',
        encoding="utf-8",
    )

    report = inspect_stage15_partial_rollout_acceptance_report(evidence, assert_complete=True)

    assert any("public_evidence_path_or_secret_leak:stage15_command_log.sanitized.jsonl" in failure for failure in report.failures)


def test_stage15_acceptance_tarball_safety_rejects_path_traversal(tmp_path: Path) -> None:
    tarball = tmp_path / "bad.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        payload = b"bad"
        info = tarfile.TarInfo("../bad.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    failures = validate_stage15_evidence_tarball(tarball)

    assert "path_traversal_tar_entry_not_allowed:../bad.txt" in failures


def _write_stage15_evidence(tmp_path: Path) -> Path:
    evidence = tmp_path / "stage15-evidence"
    evidence.mkdir()
    (evidence / "runtime_private").mkdir()

    summary: dict[str, Any] = {
        "schema_version": "repo_harness_verl_stage15_acceptance_summary_v0",
        "acceptance_passed": True,
        "training_profile_name": "dev_smoke_2x96gb_small_full_sync_partial_rollout",
        "partial_rollout_enabled": True,
        "native_partial_rollout_enabled": True,
        "native_abort_resume_observed": True,
        "native_abort_signal_visible_to_repo_harness": False,
        "controlled_turn_boundary_trigger_used": True,
        "repo_harness_checkpoint_generated_by_controlled_trigger": True,
        "partial_checkpoint_count": 2,
        "resume_attempt_count": 2,
        "resumed_terminal_episode_count": 2,
        "resumed_valid_sample_count": 2,
        "resumed_policy_loss_consumed_sample_count": 2,
        "resumed_policy_loss_consumed_unique_checkpoint_count": 2,
        "resumed_policy_loss_consumed_unique_resume_attempt_count": 2,
        "partial_policy_loss_consumed_sample_count": 0,
        "pending_reward_policy_loss_consumed_sample_count": 0,
        "stale_policy_loss_consumed_sample_count": 0,
        "diagnostic_policy_loss_consumed_sample_count": 0,
        "completed_trainer_step_count": 3,
        "parameter_sync_count": 2,
        "initial_parameter_sync_count": 1,
        "post_train_parameter_sync_count": 1,
        "post_train_parameter_sync_after_step": 2,
        "current_param_version": 2,
        "post_sync_resumed_valid_sample_count": 1,
        "message_queue_produced_sample_count": 3,
        "message_queue_consumed_sample_count": 3,
        "message_queue_dropped_sample_count": 0,
        "side_channel_sample_count": 1,
        "policy_loss_queue_invalid_sample_count": 0,
        "visibility_rejected_policy_loss_consumed_sample_count": 0,
        "missing_logprob_policy_loss_consumed_sample_count": 0,
        "non_verl_route_policy_loss_consumed_sample_count": 0,
        "timeout_policy_loss_consumed_sample_count": 0,
        "cancelled_policy_loss_consumed_sample_count": 0,
        "resume_timeout_policy_loss_consumed_sample_count": 0,
        "trainer_batch_logprob_provenance_passed": True,
        "visibility_scan_passed": True,
        "path_leak_scan_passed": True,
        "resource_cleanup_passed": True,
        "instance_final_status": "stopped",
        "public_path_leak_scan_passed": True,
        "runtime_private_evidence_present": True,
        "required_samples": 1,
        "model_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "inference_backend": "sglang",
        "training_strategy": "full",
        "weight_sync_strategy": "nixl_cuda",
    }

    profile = {
        "profile_name": summary["training_profile_name"],
        "model_id": summary["model_id"],
        "inference_backend": summary["inference_backend"],
        "training_strategy": summary["training_strategy"],
        "weight_sync_strategy": summary["weight_sync_strategy"],
    }
    overrides = [
        "actor_rollout_ref.hybrid_engine=False",
        "actor_rollout_ref.rollout.mode=async",
        "actor_rollout_ref.rollout.multi_turn.enable=True",
        "actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness",
        "actor_rollout_ref.rollout.agent.agent_loop_config_path=repo_harness_agent_loop_config.yaml",
        "actor_rollout_ref.rollout.calculate_log_probs=True",
        "actor_rollout_ref.actor.use_rollout_log_probs=True",
        "actor_rollout_ref.rollout.checkpoint_engine.backend=nixl",
        "async_training.partial_rollout=True",
        "async_training.require_batches=1",
        "critic.enable=False",
        "reward.reward_model.enable=False",
        "algorithm.rollout_correction.bypass_mode=True",
        "trainer.n_gpus_per_node=1",
        "rollout.n_gpus_per_node=1",
    ]
    environment = {
        "checkpoint_engine_backend": "nixl",
        "rollout_backend": "sglang",
    }
    partial_report = {
        "partial_rollout_enabled": True,
        "native_partial_rollout_enabled": True,
        "native_abort_resume_observed": True,
        "native_abort_signal_visible_to_repo_harness": False,
        "controlled_turn_boundary_trigger_used": True,
        "repo_harness_checkpoint_generated_by_controlled_trigger": True,
        "partial_checkpoint_count": 2,
        "policy_loss_consumed_partial_count": 0,
        "checkpoints": [
            _checkpoint("checkpoint-1"),
            _checkpoint("checkpoint-2"),
        ],
    }
    resume_report = {
        "resume_attempt_count": 2,
        "resumed_terminal_episode_count": 2,
        "resumed_valid_sample_count": 2,
        "resumed_policy_loss_consumed_sample_count": 2,
        "resume_attempts": [
            _resume_attempt("resume-1", "checkpoint-1"),
            _resume_attempt("resume-2", "checkpoint-2"),
        ],
    }
    policy_report = {
        "accepted_for_policy_loss_count": 3,
        "consumed_sample_count": 3,
        "invalid_consumed_sample_count": 0,
        "partial_consumed_sample_count": 0,
        "pending_reward_consumed_sample_count": 0,
        "stale_consumed_sample_count": 0,
        "diagnostic_consumed_sample_count": 0,
        "sample_ledger": [
            _policy_sample("sample-1", "checkpoint-1", "resume-1", 0, post_sync=False),
            _policy_sample("sample-2", "checkpoint-2", "resume-2", 1, post_sync=True),
            _policy_sample("sample-3", "checkpoint-2", "resume-2", 2, post_sync=True),
        ],
    }
    trainer_report = {
        "completed_trainer_step_count": 3,
        "steps": [
            {"trainer_step": 0, "consumed_valid_sample_count": 1},
            {"trainer_step": 1, "consumed_valid_sample_count": 1},
            {"trainer_step": 2, "consumed_valid_sample_count": 1},
        ],
    }
    parameter_sync_report = {
        "initial_parameter_sync_count": 1,
        "post_train_parameter_sync_count": 1,
        "post_train_parameter_sync_after_step": 2,
        "current_param_version": 2,
        "post_sync_resumed_valid_sample_count": 1,
    }
    message_report = {
        "message_queue_produced_sample_count": 3,
        "message_queue_consumed_sample_count": 3,
        "message_queue_dropped_sample_count": 0,
    }
    side_report = {
        "side_channel_sample_count": 1,
        "samples": [{"sample_id": "diagnostic-1", "policy_loss_consumed": False}],
    }
    staleness_report = {"stale_policy_loss_consumed_sample_count": 0}
    batch_report = {
        "trainer_batch_logprob_provenance_passed": True,
        "response_ids_digest": "sha256:response-ids",
        "response_mask_digest": "sha256:response-mask",
        "rollout_log_probs_digest": "sha256:logprobs",
        "response_ids_shape": [3, 8],
        "response_mask_shape": [3, 8],
        "rollout_log_probs_shape": [3, 8],
    }
    patch_manifest = {"patch_required": False, "files": [], "reason": "no_remote_patch_or_helper_used"}
    lifecycle = {"resource_cleanup_passed": True}

    payloads: dict[str, Any] = {
        "stage15_training_profile.json": profile,
        "stage15_hydra_overrides.json": overrides,
        "stage15_environment_matrix.json": environment,
        "stage15_partial_checkpoint_report.json": partial_report,
        "stage15_resume_scheduler_report.json": resume_report,
        "stage15_policy_loss_gate_report.json": policy_report,
        "stage15_trainer_steps_report.json": trainer_report,
        "stage15_parameter_sync_report.json": parameter_sync_report,
        "stage15_message_queue_report.json": message_report,
        "stage15_side_channel_report.json": side_report,
        "stage15_staleness_report.json": staleness_report,
        "stage15_visibility_report.json": {"visibility_scan_passed": True},
        "stage15_batch_provenance_report.json": batch_report,
        "stage15_remote_patch_manifest.json": patch_manifest,
        "stage15_resource_lifecycle_report.json": lifecycle,
        "stage15_path_leak_scan_report.json": {"path_leak_scan_passed": True},
        "stage15_fixture_manifest.json": {"fixtures": []},
        "stage15_fixture_sha256_report.json": {"fixtures": []},
    }
    for filename, payload in payloads.items():
        _write_json(evidence / filename, payload)
    (evidence / "stage15_command_log.sanitized.jsonl").write_text('{"command": "sanitized"}\n', encoding="utf-8")
    (evidence / "runtime_private" / "stage15_command_log.raw.jsonl").write_text(
        '{"command": "raw"}\n',
        encoding="utf-8",
    )

    canonical_map = {name: name for name in STAGE15_CANONICAL_EVIDENCE_ITEMS}
    _write_json(evidence / "stage15_canonical_evidence_map.json", {"items": canonical_map})
    summary["training_profile_sha256"] = _sha256_file(evidence / "stage15_training_profile.json")
    summary["hydra_overrides_sha256"] = _sha256_file(evidence / "stage15_hydra_overrides.json")
    summary["fixture_manifest_sha256"] = _sha256_file(evidence / "stage15_fixture_manifest.json")
    summary["remote_patch_manifest_sha256"] = _sha256_file(evidence / "stage15_remote_patch_manifest.json")
    summary["evidence_tarball_sha256"] = "sha256:not-yet-packed"
    _write_json(evidence / "stage15_acceptance_summary.json", summary)
    return evidence


def _checkpoint(checkpoint_id: str) -> dict[str, Any]:
    return {
        "checkpoint_id": checkpoint_id,
        "content_digest": f"sha256:{checkpoint_id}-content",
        "trajectory_digest": f"sha256:{checkpoint_id}-trajectory",
        "generation_record_digest": f"sha256:{checkpoint_id}-generation",
        "visibility_scan_digest": f"sha256:{checkpoint_id}-visibility",
        "policy_loss_consumed": False,
    }


def _resume_attempt(attempt_id: str, checkpoint_id: str) -> dict[str, Any]:
    return {
        "resume_attempt_id": attempt_id,
        "source_partial_checkpoint_id": checkpoint_id,
        "terminal_status": "succeeded",
        "policy_loss_consumed": True,
    }


def _policy_sample(sample_id: str, checkpoint_id: str, resume_attempt_id: str, step: int, *, post_sync: bool) -> dict[str, Any]:
    global_step = step
    parameter_version = 2 if post_sync else 1
    return {
        "policy_loss_consumed_sample_id": sample_id,
        "sample_id": sample_id,
        "route": "verl",
        "reward_state": "final",
        "partial_rollout_status": "complete",
        "source_partial_checkpoint_id": checkpoint_id,
        "resume_attempt_id": resume_attempt_id,
        "trainer_step": step,
        "global_step": global_step,
        "parameter_version": parameter_version,
        "min_global_steps": global_step,
        "max_global_steps": global_step,
        "response_ids_digest": f"sha256:{sample_id}-ids",
        "response_mask_digest": f"sha256:{sample_id}-mask",
        "rollout_log_probs_digest": f"sha256:{sample_id}-logprobs",
        "consumed_by_policy_loss": True,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _update_json(path: Path, **updates: Any) -> None:
    payload = _load_json(path)
    payload.update(updates)
    _write_json(path, payload)


def _sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
