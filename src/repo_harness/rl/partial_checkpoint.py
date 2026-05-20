"""Stage 14.2 partial episode checkpoint contract.

The objects in this module describe a partial episode state that may be
persisted for later resume preparation.  They deliberately do not represent a
trainable online RL sample.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal, Mapping

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .async_contracts import compute_generation_record_digest
from .gateway import GenerationRecord
from .training_view import ResponseSpan
from .visibility import (
    FlatScalar,
    validate_batch_extra_fields,
    validate_no_absolute_local_path,
    validate_opaque_ref,
    validate_safe_identifier,
)

CheckpointStatus = Literal[
    "partial",
    "resume_preparation",
    "invalid",
    "tampered",
    "stale",
    "non_trainable",
]
CheckpointKind = Literal["turn_boundary", "diagnostic", "resume_preparation"]
DurableLeaseReleaseState = Literal["active", "released", "expired", "lost", "cleanup_failed", "unknown"]
ToolPairingStatus = Literal["closed", "pending", "duplicate_result", "missing_result", "visibility_failed"]
RewardCheckpointState = Literal[
    "not_started",
    "pending_verifier",
    "final_verifier_running",
    "final_verifier_completed",
    "invalid_reward",
    "cancelled",
    "timeout",
    "stale",
]
StalenessStatus = Literal["fresh", "stale", "unknown"]
VisibilityScanStatus = Literal["passed", "failed", "missing"]
MessageQueueDropStatus = Literal["not_submitted", "not_dropped", "dropped", "unknown"]
CHECKPOINT_EVALUATOR_ONLY_MARKERS = (
    "hidden_verifier",
    "gold_patch",
    "accepted_label",
    "complete_reward_metadata",
    "provider_secret",
    "evaluator_only_logs",
    "ground_truth",
    "reward_extra_info",
    "reward_extra_keys",
    "extra_info",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_digest(value: Any, *, field_name: str = "digest_payload") -> str:
    validate_no_absolute_local_path(_canonical_json(value), field_name=field_name)
    _validate_no_checkpoint_evaluator_only_content(value, field_name=field_name)
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate_no_checkpoint_evaluator_only_content(value: Any, *, field_name: str) -> None:
    text = _canonical_json(value).lower()
    compact = "".join(ch for ch in text if ch.isalnum())
    for marker in CHECKPOINT_EVALUATOR_ONLY_MARKERS:
        normalized = marker.lower()
        compact_marker = "".join(ch for ch in normalized if ch.isalnum())
        if normalized in text or compact_marker in compact:
            raise ValueError(f"{field_name} contains evaluator-only content: {marker}")


def _contains_runtime_private_marker(value: Any) -> bool:
    text = _canonical_json(value).lower()
    compact = "".join(ch for ch in text if ch.isalnum())
    return "runtimeprivate" in compact


def _validate_digest(value: str | None, *, field_name: str, required: bool = True) -> None:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return
    validate_no_absolute_local_path(value, field_name=field_name)
    if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
        raise ValueError(f"{field_name} must be a sha256 digest")


def _validate_optional_opaque_ref(value: str | None, *, field_name: str, required: bool = False) -> None:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return
    validate_opaque_ref(value, field_name=field_name)


def _safe_identifier_fields(model: Any, field_names: list[str]) -> None:
    for field_name in field_names:
        value = getattr(model, field_name)
        if value is not None:
            validate_safe_identifier(str(value), field_name=field_name)


class DurableWriterLeaseFacts(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_durable_writer_lease_v0"
    lease_token: str
    owner_id: str
    owner_kind: Literal["runtime", "ray_actor", "worker", "process", "test"]
    epoch: int = Field(ge=0)
    heartbeat_interval_seconds: float = Field(gt=0)
    acquired_at: datetime
    last_heartbeat_at: datetime
    release_state: DurableLeaseReleaseState = "active"
    release_at: datetime | None = None
    lease_digest: str

    @model_validator(mode="after")
    def validate_lease(self) -> "DurableWriterLeaseFacts":
        _safe_identifier_fields(self, ["lease_token", "owner_id"])
        if self.last_heartbeat_at < self.acquired_at:
            raise ValueError("last_heartbeat_at must be >= acquired_at")
        if self.release_state == "released" and self.release_at is None:
            raise ValueError("released durable lease requires release_at")
        _validate_digest(self.lease_digest, field_name="lease_digest")
        expected = compute_durable_writer_lease_digest(self)
        if self.lease_digest != expected:
            raise ValueError("durable_lease_digest_mismatch")
        return self


class WriterStateFacts(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_writer_state_v0"
    run_directory_writer_active: bool
    worker_may_still_write: bool = False
    tool_may_still_write: bool = False
    verifier_may_still_write: bool = False
    recorder_may_still_write: bool = False
    cleanup_may_still_write: bool = False
    final_audit_write_completed: bool = False

    @property
    def any_writer_may_still_write(self) -> bool:
        return any(
            [
                self.run_directory_writer_active,
                self.worker_may_still_write,
                self.tool_may_still_write,
                self.verifier_may_still_write,
                self.recorder_may_still_write,
                self.cleanup_may_still_write,
            ]
        )

    @model_validator(mode="after")
    def validate_writer_state(self) -> "WriterStateFacts":
        if self.final_audit_write_completed and self.run_directory_writer_active:
            raise ValueError("run directory writer cannot remain active after final audit completion")
        return self


class RecorderCursorFacts(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_recorder_cursor_v0"
    recorder_cursor_ref: str
    recorder_cursor_digest: str
    artifact_manifest_ref: str
    artifact_manifest_digest: str
    transcript_ref: str
    transcript_digest: str
    events_ref: str
    events_digest: str
    finalization_state: Literal["open", "flushed", "finalized", "unknown"] = "flushed"
    last_event_seq: int = Field(ge=0)
    last_artifact_seq: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_cursor(self) -> "RecorderCursorFacts":
        for field_name in ["recorder_cursor_ref", "artifact_manifest_ref", "transcript_ref", "events_ref"]:
            validate_opaque_ref(getattr(self, field_name), field_name=field_name)
        for field_name in [
            "recorder_cursor_digest",
            "artifact_manifest_digest",
            "transcript_digest",
            "events_digest",
        ]:
            _validate_digest(getattr(self, field_name), field_name=field_name)
        if self.finalization_state == "finalized":
            raise ValueError("partial checkpoint recorder cursor cannot claim finalized run state")
        return self


class WorkspaceCheckpointFacts(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_workspace_v0"
    workspace_snapshot_ref: str
    workspace_snapshot_digest: str
    source_snapshot_ref: str
    source_snapshot_digest: str
    workspace_lease_ref: str
    workspace_lease_digest: str
    dependency_environment_ref: str | None = None
    dependency_environment_digest: str | None = None
    workspace_state_ref: str
    workspace_state_digest: str
    patch_base_ref: str
    patch_base_digest: str

    @model_validator(mode="after")
    def validate_workspace(self) -> "WorkspaceCheckpointFacts":
        for field_name in [
            "workspace_snapshot_ref",
            "source_snapshot_ref",
            "workspace_lease_ref",
            "workspace_state_ref",
            "patch_base_ref",
        ]:
            validate_opaque_ref(getattr(self, field_name), field_name=field_name)
        _validate_optional_opaque_ref(self.dependency_environment_ref, field_name="dependency_environment_ref")
        for field_name in [
            "workspace_snapshot_digest",
            "source_snapshot_digest",
            "workspace_lease_digest",
            "workspace_state_digest",
            "patch_base_digest",
        ]:
            _validate_digest(getattr(self, field_name), field_name=field_name)
        _validate_digest(
            self.dependency_environment_digest,
            field_name="dependency_environment_digest",
            required=self.dependency_environment_ref is not None,
        )
        if (self.dependency_environment_ref is None) != (self.dependency_environment_digest is None):
            raise ValueError("dependency environment ref and digest must be provided together")
        return self


class ToolPairingState(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_tool_pairing_v0"
    pending_tool_call_ids: list[str] = Field(default_factory=list)
    completed_tool_call_ids: list[str] = Field(default_factory=list)
    tool_result_refs: dict[str, str] = Field(default_factory=dict)
    tool_result_visibility_digest: str | None = None
    observation_token_projection_digest: str | None = None
    tool_pairing_status: ToolPairingStatus = "closed"

    @model_validator(mode="after")
    def validate_tool_pairing(self) -> "ToolPairingState":
        for tool_call_id in [*self.pending_tool_call_ids, *self.completed_tool_call_ids]:
            validate_safe_identifier(tool_call_id, field_name="tool_call_id")
        if len(set(self.completed_tool_call_ids)) != len(self.completed_tool_call_ids):
            raise ValueError("duplicate completed tool call id")
        for key, value in self.tool_result_refs.items():
            validate_safe_identifier(key, field_name="tool_result_refs.key")
            validate_opaque_ref(value, field_name=f"tool_result_refs.{key}")
        _validate_digest(
            self.tool_result_visibility_digest,
            field_name="tool_result_visibility_digest",
            required=bool(self.tool_result_refs),
        )
        _validate_digest(
            self.observation_token_projection_digest,
            field_name="observation_token_projection_digest",
            required=bool(self.tool_result_refs),
        )
        if self.tool_pairing_status == "closed" and self.pending_tool_call_ids:
            raise ValueError("closed tool pairing cannot contain pending tool calls")
        if self.tool_pairing_status == "closed" and set(self.completed_tool_call_ids) != set(self.tool_result_refs):
            raise ValueError("closed tool pairing requires one tool result per completed tool call")
        return self


class CheckpointTokenProvenance(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_token_provenance_v0"
    prompt_digest: str
    raw_prompt_digest: str | None = None
    tokenizer_digest: str
    chat_template_digest: str
    sampling_params_digest: str
    policy_version_digest: str
    response_ids: list[int] = Field(default_factory=list)
    response_mask: list[Literal[0, 1]] = Field(default_factory=list)
    response_logprobs: list[float] | None = None
    completed_response_spans: list[ResponseSpan] = Field(default_factory=list)
    completed_generation_records: list[GenerationRecord] = Field(default_factory=list)
    response_ids_digest: str
    response_mask_digest: str
    response_logprobs_digest: str | None = None
    response_span_digest: str
    generation_record_digest: str
    trajectory_digest: str

    @model_validator(mode="after")
    def validate_token_provenance(self) -> "CheckpointTokenProvenance":
        for field_name in [
            "prompt_digest",
            "raw_prompt_digest",
            "tokenizer_digest",
            "chat_template_digest",
            "sampling_params_digest",
            "policy_version_digest",
            "response_ids_digest",
            "response_mask_digest",
            "response_logprobs_digest",
            "response_span_digest",
            "generation_record_digest",
            "trajectory_digest",
        ]:
            _validate_digest(getattr(self, field_name), field_name=field_name, required=field_name != "raw_prompt_digest")
        if len(self.response_ids) != len(self.response_mask):
            raise ValueError("response_ids and response_mask must align")
        if self.response_logprobs is not None and len(self.response_logprobs) != len(self.response_ids):
            raise ValueError("response_logprobs must align with response_ids")
        if self.response_logprobs is not None:
            for mask, logprob in zip(self.response_mask, self.response_logprobs):
                if mask == 0 and logprob != 0.0:
                    raise ValueError("response_mask=0 tokens must use response_logprobs=0.0")
        if self.response_ids_digest != compute_response_ids_digest(self.response_ids):
            raise ValueError("response_ids_digest_mismatch")
        if self.response_mask_digest != compute_response_mask_digest(self.response_mask):
            raise ValueError("response_mask_digest_mismatch")
        expected_logprob_digest = compute_response_logprobs_digest(self.response_logprobs)
        if self.response_logprobs_digest != expected_logprob_digest:
            raise ValueError("response_logprobs_digest_mismatch")
        if self.response_span_digest != compute_response_span_digest(self.completed_response_spans):
            raise ValueError("response_span_digest_mismatch")
        if self.generation_record_digest != compute_generation_record_digest(self.completed_generation_records):
            raise ValueError("generation_record_digest_mismatch")
        return self


class CheckpointRewardFinalityFacts(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_reward_finality_v0"
    reward_state: RewardCheckpointState = "not_started"
    reward_job_id: str | None = None
    final_verifier_status: Literal["accepted", "rejected", "error", "timeout", "cancelled", "unknown"] = "unknown"
    reward_score: float | None = None
    reward_finality_digest: str

    @model_validator(mode="after")
    def validate_reward(self) -> "CheckpointRewardFinalityFacts":
        if self.reward_job_id is not None:
            validate_safe_identifier(self.reward_job_id, field_name="reward_job_id")
        _validate_digest(self.reward_finality_digest, field_name="reward_finality_digest")
        if self.reward_state != "final_verifier_completed" and self.reward_score is not None:
            raise ValueError("non-final checkpoint reward cannot carry reward_score")
        if self.reward_state == "final_verifier_completed" and self.reward_score is None:
            raise ValueError("final reward checkpoint requires reward_score")
        if self.reward_state == "final_verifier_completed" and self.final_verifier_status not in {"accepted", "rejected"}:
            raise ValueError("final reward checkpoint requires accepted or rejected verifier status")
        expected = compute_reward_finality_digest(self)
        if self.reward_finality_digest != expected:
            raise ValueError("reward_finality_digest_mismatch")
        return self


class PartialEpisodeCheckpoint(StrictBaseModel):
    schema_version: str = "repo_harness_partial_episode_checkpoint_v0"
    checkpoint_id: str
    checkpoint_kind: CheckpointKind = "turn_boundary"
    checkpoint_status: CheckpointStatus = "partial"
    episode_id: str
    run_id: str
    sample_attempt_id: str
    resume_attempt_id: str | None = None
    task_id: str
    dataset_uid: str | None = None
    dataset_index: int | None = Field(default=None, ge=0)
    rollout_uid: str | None = None
    uid: str | None = None
    policy_version: dict[str, Any] = Field(default_factory=dict)
    global_steps: int = Field(ge=0)
    min_global_steps: int = Field(ge=0)
    max_global_steps: int = Field(ge=0)
    trajectory_param_versions: list[int] = Field(default_factory=list)
    current_param_version_at_checkpoint: int = Field(ge=0)
    staleness_threshold: int | None = Field(default=None, ge=0)
    staleness_status: StalenessStatus = "unknown"
    created_at: datetime
    turn_index: int = Field(ge=0)
    context_revision: int = Field(ge=0)
    online_rl_eligible: bool = False
    invalid_for_training: bool = True
    invalid_for_online_rl: bool = True
    visibility_scan_status: VisibilityScanStatus = "missing"
    visibility_scan_digest: str | None = None
    external_visibility_ledger_ref: str | None = None
    message_queue_drop_status: MessageQueueDropStatus = "not_submitted"
    writer_state: WriterStateFacts
    durable_writer_lease: DurableWriterLeaseFacts
    recorder_cursor: RecorderCursorFacts
    workspace: WorkspaceCheckpointFacts
    tool_pairing: ToolPairingState
    token_provenance: CheckpointTokenProvenance
    reward_finality: CheckpointRewardFinalityFacts
    batch_safe_projection: dict[str, FlatScalar] = Field(default_factory=dict)
    runtime_private_refs: dict[str, str] = Field(default_factory=dict)
    content_digest: str

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "PartialEpisodeCheckpoint":
        _safe_identifier_fields(
            self,
            ["checkpoint_id", "episode_id", "run_id", "sample_attempt_id", "task_id"],
        )
        if self.resume_attempt_id is not None:
            validate_safe_identifier(self.resume_attempt_id, field_name="resume_attempt_id")
        if self.dataset_uid is not None:
            validate_safe_identifier(self.dataset_uid, field_name="dataset_uid")
        if self.rollout_uid is not None:
            validate_safe_identifier(self.rollout_uid, field_name="rollout_uid")
        if self.uid is not None:
            validate_safe_identifier(self.uid, field_name="uid")
        if self.dataset_uid is None and self.dataset_index is None:
            raise ValueError("checkpoint requires dataset_uid or dataset_index")
        if self.rollout_uid is None and self.uid is None:
            raise ValueError("checkpoint requires rollout_uid or uid")
        if not (self.min_global_steps <= self.global_steps <= self.max_global_steps):
            raise ValueError("global_steps must be within min_global_steps and max_global_steps")
        if self.trajectory_param_versions and self.current_param_version_at_checkpoint not in self.trajectory_param_versions:
            raise ValueError("current_param_version_at_checkpoint must appear in trajectory_param_versions")
        validate_no_absolute_local_path(_canonical_json(self.policy_version), field_name="policy_version")
        _validate_no_checkpoint_evaluator_only_content(self.policy_version, field_name="policy_version")
        _validate_digest(self.visibility_scan_digest, field_name="visibility_scan_digest", required=False)
        _validate_optional_opaque_ref(
            self.external_visibility_ledger_ref,
            field_name="external_visibility_ledger_ref",
            required=self.visibility_scan_status == "passed",
        )
        if self.visibility_scan_status == "passed" and self.visibility_scan_digest is None:
            raise ValueError("passed visibility scan requires visibility_scan_digest")
        if self.visibility_scan_status != "passed" and self.checkpoint_status == "resume_preparation":
            raise ValueError("resume_preparation checkpoint requires passed visibility scan")
        if self.online_rl_eligible or not self.invalid_for_training or not self.invalid_for_online_rl:
            raise ValueError("partial checkpoint cannot be marked trainable")
        if self.message_queue_drop_status == "dropped":
            raise ValueError("message queue dropped checkpoint cannot be treated as recoverable")
        validate_batch_extra_fields(self.batch_safe_projection)
        for key, value in self.runtime_private_refs.items():
            validate_safe_identifier(key, field_name="runtime_private_refs.key")
            validate_opaque_ref(value, field_name=f"runtime_private_refs.{key}")
        if self.checkpoint_status == "resume_preparation" and self.writer_state.any_writer_may_still_write:
            raise ValueError("writer_active_checkpoint_cannot_enter_resume_preparation")
        if self.checkpoint_status == "resume_preparation" and self.durable_writer_lease.release_state != "active":
            raise ValueError("resume_preparation checkpoint requires active durable lease")
        if self.reward_finality.reward_state == "final_verifier_completed" and self.checkpoint_status in {
            "partial",
            "resume_preparation",
        }:
            raise ValueError("partial checkpoint cannot claim final reward readiness")
        for key, value in self.batch_safe_projection.items():
            if _contains_runtime_private_marker(key) or _contains_runtime_private_marker(value):
                raise ValueError("runtime-private refs cannot enter batch_safe_projection")
        if self.token_provenance.trajectory_digest != compute_partial_checkpoint_trajectory_digest(self):
            raise ValueError("trajectory_digest_mismatch")
        if self.content_digest != compute_partial_checkpoint_content_digest(self):
            raise ValueError("partial_checkpoint_content_digest_mismatch")
        return self


class PartialCheckpointQueueFacts(StrictBaseModel):
    schema_version: str = "repo_harness_partial_checkpoint_queue_facts_v0"
    checkpoint_id: str
    sample_attempt_id: str
    valid_for_policy_loss: bool = False
    sample_classification: Literal["partial_checkpoint", "resume_preparation", "diagnostic"] = "partial_checkpoint"
    rejection_reason: str
    checkpoint_ref: str
    content_digest: str
    trajectory_digest: str

    @model_validator(mode="after")
    def validate_queue_facts(self) -> "PartialCheckpointQueueFacts":
        validate_safe_identifier(self.checkpoint_id, field_name="checkpoint_id")
        validate_safe_identifier(self.sample_attempt_id, field_name="sample_attempt_id")
        validate_opaque_ref(self.checkpoint_ref, field_name="checkpoint_ref")
        _validate_digest(self.content_digest, field_name="content_digest")
        _validate_digest(self.trajectory_digest, field_name="trajectory_digest")
        if self.valid_for_policy_loss:
            raise ValueError("partial checkpoint queue facts cannot be valid for policy loss")
        return self


def _revalidate_checkpoint(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> PartialEpisodeCheckpoint:
    """Re-run full schema and digest validation even for existing model objects.

    Pydantic ``model_copy(update=...)`` intentionally does not re-run model
    validators.  Public helpers use this function so a mutated in-memory
    checkpoint cannot bypass token, lease, reward or content digest checks.
    """

    if isinstance(checkpoint, PartialEpisodeCheckpoint):
        return PartialEpisodeCheckpoint.model_validate(checkpoint.model_dump(mode="python"))
    return PartialEpisodeCheckpoint.model_validate(checkpoint)


def compute_durable_writer_lease_digest(lease: DurableWriterLeaseFacts | Mapping[str, Any]) -> str:
    if isinstance(lease, DurableWriterLeaseFacts):
        payload = lease.model_dump(mode="json", exclude={"lease_digest"})
    else:
        payload = dict(lease)
        payload.pop("lease_digest", None)
    return _sha256_digest(payload, field_name="durable_writer_lease")


def compute_reward_finality_digest(reward: CheckpointRewardFinalityFacts | Mapping[str, Any]) -> str:
    if isinstance(reward, CheckpointRewardFinalityFacts):
        payload = reward.model_dump(mode="json", exclude={"reward_finality_digest"})
    else:
        payload = dict(reward)
        payload.pop("reward_finality_digest", None)
    return _sha256_digest(payload, field_name="checkpoint_reward_finality")


def compute_response_ids_digest(response_ids: list[int]) -> str:
    return _sha256_digest(response_ids, field_name="response_ids")


def compute_response_mask_digest(response_mask: list[int]) -> str:
    return _sha256_digest(response_mask, field_name="response_mask")


def compute_response_logprobs_digest(response_logprobs: list[float] | None) -> str | None:
    if response_logprobs is None:
        return None
    return _sha256_digest(response_logprobs, field_name="response_logprobs")


def compute_response_span_digest(response_spans: list[ResponseSpan | Mapping[str, Any]]) -> str:
    parsed = [span if isinstance(span, ResponseSpan) else ResponseSpan.model_validate(span) for span in response_spans]
    return _sha256_digest([span.model_dump(mode="json") for span in parsed], field_name="response_spans")


def compute_partial_checkpoint_trajectory_digest(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> str:
    if not isinstance(checkpoint, PartialEpisodeCheckpoint):
        data = dict(checkpoint)
        token = dict(data["token_provenance"])
        payload = {
            "checkpoint_id": data["checkpoint_id"],
            "episode_id": data["episode_id"],
            "run_id": data["run_id"],
            "sample_attempt_id": data["sample_attempt_id"],
            "resume_attempt_id": data.get("resume_attempt_id"),
            "task_id": data["task_id"],
            "dataset_uid": data.get("dataset_uid"),
            "dataset_index": data.get("dataset_index"),
            "rollout_uid": data.get("rollout_uid"),
            "uid": data.get("uid"),
            "policy_version": data.get("policy_version", {}),
            "global_steps": data["global_steps"],
            "min_global_steps": data["min_global_steps"],
            "max_global_steps": data["max_global_steps"],
            "trajectory_param_versions": data.get("trajectory_param_versions", []),
            "current_param_version_at_checkpoint": data["current_param_version_at_checkpoint"],
            "turn_index": data["turn_index"],
            "context_revision": data["context_revision"],
            "prompt_digest": token["prompt_digest"],
            "raw_prompt_digest": token.get("raw_prompt_digest"),
            "tokenizer_digest": token["tokenizer_digest"],
            "chat_template_digest": token["chat_template_digest"],
            "sampling_params_digest": token["sampling_params_digest"],
            "policy_version_digest": token["policy_version_digest"],
            "response_ids": token.get("response_ids", []),
            "response_mask": token.get("response_mask", []),
            "response_logprobs": token.get("response_logprobs"),
            "response_spans": token.get("completed_response_spans", []),
            "generation_records": token.get("completed_generation_records", []),
        }
        return _sha256_digest(payload, field_name="partial_checkpoint_trajectory")
    parsed = checkpoint
    payload = {
        "checkpoint_id": parsed.checkpoint_id,
        "episode_id": parsed.episode_id,
        "run_id": parsed.run_id,
        "sample_attempt_id": parsed.sample_attempt_id,
        "resume_attempt_id": parsed.resume_attempt_id,
        "task_id": parsed.task_id,
        "dataset_uid": parsed.dataset_uid,
        "dataset_index": parsed.dataset_index,
        "rollout_uid": parsed.rollout_uid,
        "uid": parsed.uid,
        "policy_version": parsed.policy_version,
        "global_steps": parsed.global_steps,
        "min_global_steps": parsed.min_global_steps,
        "max_global_steps": parsed.max_global_steps,
        "trajectory_param_versions": parsed.trajectory_param_versions,
        "current_param_version_at_checkpoint": parsed.current_param_version_at_checkpoint,
        "turn_index": parsed.turn_index,
        "context_revision": parsed.context_revision,
        "prompt_digest": parsed.token_provenance.prompt_digest,
        "raw_prompt_digest": parsed.token_provenance.raw_prompt_digest,
        "tokenizer_digest": parsed.token_provenance.tokenizer_digest,
        "chat_template_digest": parsed.token_provenance.chat_template_digest,
        "sampling_params_digest": parsed.token_provenance.sampling_params_digest,
        "policy_version_digest": parsed.token_provenance.policy_version_digest,
        "response_ids": parsed.token_provenance.response_ids,
        "response_mask": parsed.token_provenance.response_mask,
        "response_logprobs": parsed.token_provenance.response_logprobs,
        "response_spans": [
            span.model_dump(mode="json") for span in parsed.token_provenance.completed_response_spans
        ],
        "generation_records": [
            record.model_dump(mode="json") for record in parsed.token_provenance.completed_generation_records
        ],
    }
    return _sha256_digest(payload, field_name="partial_checkpoint_trajectory")


def compute_partial_checkpoint_content_digest(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> str:
    if isinstance(checkpoint, PartialEpisodeCheckpoint):
        payload = checkpoint.model_dump(mode="json", exclude={"content_digest"})
    else:
        payload = dict(checkpoint)
        payload.pop("content_digest", None)
    return _sha256_digest(payload, field_name="partial_checkpoint_content")


def compute_partial_checkpoint_visibility_digest(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> str:
    parsed = _revalidate_checkpoint(checkpoint)
    payload = {
        "checkpoint_id": parsed.checkpoint_id,
        "episode_id": parsed.episode_id,
        "run_id": parsed.run_id,
        "task_id": parsed.task_id,
        "batch_safe_projection": parsed.batch_safe_projection,
        "workspace_snapshot_ref": parsed.workspace.workspace_snapshot_ref,
        "source_snapshot_ref": parsed.workspace.source_snapshot_ref,
        "workspace_lease_ref": parsed.workspace.workspace_lease_ref,
        "dependency_environment_ref": parsed.workspace.dependency_environment_ref,
        "recorder_cursor_ref": parsed.recorder_cursor.recorder_cursor_ref,
        "tool_result_refs": parsed.tool_pairing.tool_result_refs,
    }
    return _sha256_digest(payload, field_name="partial_checkpoint_visibility")


def validate_partial_checkpoint_roundtrip(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> PartialEpisodeCheckpoint:
    parsed = _revalidate_checkpoint(checkpoint)
    dumped = parsed.model_dump(mode="json")
    reparsed = PartialEpisodeCheckpoint.model_validate(dumped)
    if reparsed.content_digest != parsed.content_digest:
        raise ValueError("partial_checkpoint_roundtrip_digest_mismatch")
    return reparsed


def validate_partial_checkpoint_for_resume_preparation(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> PartialEpisodeCheckpoint:
    parsed = _revalidate_checkpoint(checkpoint)
    if parsed.checkpoint_status != "resume_preparation":
        raise ValueError(f"checkpoint_not_resume_preparation:{parsed.checkpoint_status}")
    if parsed.writer_state.any_writer_may_still_write:
        raise ValueError("writer_active_checkpoint_cannot_enter_resume_preparation")
    if parsed.visibility_scan_status != "passed" or not parsed.visibility_scan_digest:
        raise ValueError("checkpoint_missing_visibility_scan")
    if not parsed.external_visibility_ledger_ref:
        raise ValueError("checkpoint_missing_external_visibility_ledger")
    if parsed.message_queue_drop_status != "not_submitted":
        raise ValueError("message_queue_drop_disguised_as_checkpoint")
    if parsed.staleness_status == "stale":
        raise ValueError("stale_checkpoint_cannot_enter_resume_preparation")
    if parsed.tool_pairing.tool_pairing_status != "closed":
        raise ValueError("tool_pairing_not_closed")
    return parsed


def validate_partial_checkpoint_not_trainable(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
) -> PartialEpisodeCheckpoint:
    parsed = _revalidate_checkpoint(checkpoint)
    if parsed.online_rl_eligible or not parsed.invalid_for_training or not parsed.invalid_for_online_rl:
        raise ValueError("partial_checkpoint_forged_trainable_flag")
    if parsed.reward_finality.reward_state == "final_verifier_completed":
        raise ValueError("partial_checkpoint_reward_finality_forged")
    return parsed


def partial_checkpoint_to_queue_facts(
    checkpoint: PartialEpisodeCheckpoint | Mapping[str, Any],
    *,
    checkpoint_ref: str | None = None,
) -> PartialCheckpointQueueFacts:
    parsed = _revalidate_checkpoint(checkpoint)
    validate_partial_checkpoint_not_trainable(parsed)
    classification: Literal["partial_checkpoint", "resume_preparation", "diagnostic"] = (
        "resume_preparation" if parsed.checkpoint_status == "resume_preparation" else "partial_checkpoint"
    )
    return PartialCheckpointQueueFacts(
        checkpoint_id=parsed.checkpoint_id,
        sample_attempt_id=parsed.sample_attempt_id,
        valid_for_policy_loss=False,
        sample_classification=classification,
        rejection_reason=f"partial_checkpoint_not_trainable:{parsed.checkpoint_status}",
        checkpoint_ref=checkpoint_ref or f"rh://partial-checkpoints/{parsed.checkpoint_id}",
        content_digest=parsed.content_digest,
        trajectory_digest=parsed.token_provenance.trajectory_digest,
    )
