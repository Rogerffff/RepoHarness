from __future__ import annotations

import copy
from typing import Any

from repo_harness.rl.partial_checkpoint import (
    compute_durable_writer_lease_digest,
    compute_partial_checkpoint_content_digest,
    compute_partial_checkpoint_trajectory_digest,
    compute_response_ids_digest,
    compute_response_logprobs_digest,
    compute_response_mask_digest,
    compute_response_span_digest,
    compute_reward_finality_digest,
)
from repo_harness.rl.async_contracts import compute_generation_record_digest


def build_stage14_2_checkpoint_payload(**overrides: Any) -> dict[str, Any]:
    generation_record = {
        "schema_version": "repo_harness_verl_generation_record_v0",
        "turn": 0,
        "model_call_id": "model-call-0",
        "context_revision": 1,
        "prompt_ids": [101, 102, 103],
        "output_token_ids": [201, 202],
        "output_logprobs": [-0.1, -0.2],
        "stop_reason": "tool_calls",
        "gateway_route": "verl",
        "inference_backend": "sglang",
        "policy_version": {"name": "stage14-policy", "version": 0},
        "global_steps": 0,
        "min_global_steps": 0,
        "max_global_steps": 0,
    }
    response_span = {
        "schema_version": "repo_harness_verl_response_span_v0",
        "start": 0,
        "end": 2,
        "source_type": "assistant_generation",
        "model_call_id": "model-call-0",
        "tool_call_id": None,
        "artifact_ref": "rh://artifacts/model-call-0",
        "response_mask_value": 1,
        "logprob_policy": "policy",
        "policy_version": {"name": "stage14-policy", "version": 0},
        "global_steps": 0,
        "min_global_steps": 0,
        "max_global_steps": 0,
    }
    lease = {
        "schema_version": "repo_harness_partial_checkpoint_durable_writer_lease_v0",
        "lease_token": "lease-token-0",
        "owner_id": "runtime-0",
        "owner_kind": "runtime",
        "epoch": 1,
        "heartbeat_interval_seconds": 5.0,
        "acquired_at": "2026-05-20T00:00:00Z",
        "last_heartbeat_at": "2026-05-20T00:00:05Z",
        "release_state": "active",
        "release_at": None,
        "lease_digest": "sha256:placeholder",
    }
    lease["lease_digest"] = compute_durable_writer_lease_digest(lease)
    reward = {
        "schema_version": "repo_harness_partial_checkpoint_reward_finality_v0",
        "reward_state": "pending_verifier",
        "reward_job_id": "reward-job-0",
        "final_verifier_status": "unknown",
        "reward_score": None,
        "reward_finality_digest": "sha256:placeholder",
    }
    reward["reward_finality_digest"] = compute_reward_finality_digest(reward)
    token = {
        "schema_version": "repo_harness_partial_checkpoint_token_provenance_v0",
        "prompt_digest": "sha256:" + "1" * 64,
        "raw_prompt_digest": "sha256:" + "2" * 64,
        "tokenizer_digest": "sha256:" + "3" * 64,
        "chat_template_digest": "sha256:" + "4" * 64,
        "sampling_params_digest": "sha256:" + "5" * 64,
        "policy_version_digest": "sha256:" + "6" * 64,
        "response_ids": [201, 202],
        "response_mask": [1, 1],
        "response_logprobs": [-0.1, -0.2],
        "completed_response_spans": [response_span],
        "completed_generation_records": [generation_record],
        "response_ids_digest": compute_response_ids_digest([201, 202]),
        "response_mask_digest": compute_response_mask_digest([1, 1]),
        "response_logprobs_digest": compute_response_logprobs_digest([-0.1, -0.2]),
        "response_span_digest": compute_response_span_digest([response_span]),
        "generation_record_digest": compute_generation_record_digest([generation_record]),
        "trajectory_digest": "sha256:placeholder",
    }
    payload = {
        "schema_version": "repo_harness_partial_episode_checkpoint_v0",
        "checkpoint_id": "checkpoint-0",
        "checkpoint_kind": "turn_boundary",
        "checkpoint_status": "partial",
        "episode_id": "episode-0",
        "run_id": "run-0",
        "sample_attempt_id": "episode-0:attempt-0",
        "resume_attempt_id": None,
        "task_id": "task-0",
        "dataset_uid": "dataset-0",
        "dataset_index": 0,
        "rollout_uid": "rollout-0",
        "uid": "uid-0",
        "policy_version": {"name": "stage14-policy", "version": 0},
        "global_steps": 0,
        "min_global_steps": 0,
        "max_global_steps": 0,
        "trajectory_param_versions": [0],
        "current_param_version_at_checkpoint": 0,
        "staleness_threshold": 1,
        "staleness_status": "fresh",
        "created_at": "2026-05-20T00:00:06Z",
        "turn_index": 1,
        "context_revision": 1,
        "online_rl_eligible": False,
        "invalid_for_training": True,
        "invalid_for_online_rl": True,
        "visibility_scan_status": "passed",
        "visibility_scan_digest": "sha256:" + "7" * 64,
        "external_visibility_ledger_ref": "rh://visibility-ledgers/checkpoint-0",
        "message_queue_drop_status": "not_submitted",
        "writer_state": {
            "schema_version": "repo_harness_partial_checkpoint_writer_state_v0",
            "run_directory_writer_active": False,
            "worker_may_still_write": False,
            "tool_may_still_write": False,
            "verifier_may_still_write": False,
            "recorder_may_still_write": False,
            "cleanup_may_still_write": False,
            "final_audit_write_completed": False,
        },
        "durable_writer_lease": lease,
        "recorder_cursor": {
            "schema_version": "repo_harness_partial_checkpoint_recorder_cursor_v0",
            "recorder_cursor_ref": "rh://recorders/cursor-0",
            "recorder_cursor_digest": "sha256:" + "8" * 64,
            "artifact_manifest_ref": "rh://artifacts/manifest-0",
            "artifact_manifest_digest": "sha256:" + "9" * 64,
            "transcript_ref": "rh://transcripts/transcript-0",
            "transcript_digest": "sha256:" + "a" * 64,
            "events_ref": "rh://events/events-0",
            "events_digest": "sha256:" + "b" * 64,
            "finalization_state": "flushed",
            "last_event_seq": 3,
            "last_artifact_seq": 2,
        },
        "workspace": {
            "schema_version": "repo_harness_partial_checkpoint_workspace_v0",
            "workspace_snapshot_ref": "rh://workspace-snapshots/snapshot-0",
            "workspace_snapshot_digest": "sha256:" + "c" * 64,
            "source_snapshot_ref": "rh://source-snapshots/source-0",
            "source_snapshot_digest": "sha256:" + "d" * 64,
            "workspace_lease_ref": "rh://workspace-leases/lease-0",
            "workspace_lease_digest": "sha256:" + "e" * 64,
            "dependency_environment_ref": "rh://dependency-envs/env-0",
            "dependency_environment_digest": "sha256:" + "f" * 64,
            "workspace_state_ref": "rh://workspace-states/state-0",
            "workspace_state_digest": "sha256:" + "0" * 64,
            "patch_base_ref": "rh://patch-bases/base-0",
            "patch_base_digest": "sha256:" + "1" * 64,
        },
        "tool_pairing": {
            "schema_version": "repo_harness_partial_checkpoint_tool_pairing_v0",
            "pending_tool_call_ids": [],
            "completed_tool_call_ids": ["tool-call-0"],
            "tool_result_refs": {"tool-call-0": "rh://tool-results/tool-call-0"},
            "tool_result_visibility_digest": "sha256:" + "2" * 64,
            "observation_token_projection_digest": "sha256:" + "3" * 64,
            "tool_pairing_status": "closed",
        },
        "token_provenance": token,
        "reward_finality": reward,
        "batch_safe_projection": {
            "repo_harness_checkpoint_ref": "rh://partial-checkpoints/checkpoint-0",
            "repo_harness_checkpoint_status": "partial",
        },
        "runtime_private_refs": {"writer_lease": "rh://runtime-private/writer-lease-0"},
        "content_digest": "sha256:placeholder",
    }
    _deep_update(payload, overrides)
    payload["token_provenance"]["trajectory_digest"] = compute_partial_checkpoint_trajectory_digest(payload)
    payload["content_digest"] = compute_partial_checkpoint_content_digest(payload)
    return payload


def tampered_stage14_2_payload(**updates: Any) -> dict[str, Any]:
    payload = build_stage14_2_checkpoint_payload()
    _deep_update(payload, copy.deepcopy(updates))
    return payload


def _deep_update(payload: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            _deep_update(payload[key], value)
        else:
            payload[key] = value
