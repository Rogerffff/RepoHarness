"""Stage 13 fully async 前置 contract schema 和校验 helper。"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Literal, Mapping

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .gateway import GenerationRecord
from .training_view import (
    FormalOnlineRLSample,
    TrainingView,
    formal_online_rl_sample_from_training_view,
    validate_formal_online_rl_batch,
)
from .visibility import (
    FlatScalar,
    validate_no_absolute_local_path,
    validate_no_forbidden_model_visible_content,
    validate_opaque_ref,
    validate_safe_identifier,
)

AsyncEpisodeStatus = Literal[
    "created",
    "queued",
    "running",
    "paused",
    "cancelling",
    "cancelled",
    "timeout",
    "failed",
    "final_verifier_running",
    "final_verifier_completed",
    "reward_finalized",
    "cleanup_running",
    "completed",
    "orphaned",
]

RewardState = Literal[
    "pending_verifier",
    "final_verifier_running",
    "final_verifier_completed",
    "invalid_reward",
    "cancelled",
    "timeout",
    "stale",
    "rejected_by_visibility",
]

RewardScoreSource = Literal[
    "trusted_final_verifier",
    "provisional",
    "provider_reported",
    "heuristic",
    "unknown",
]

FinalVerifierStatus = Literal["accepted", "rejected", "error", "timeout", "cancelled", "unknown"]

ASYNC_DIGEST_EVALUATOR_ONLY_MARKERS = (
    "ground_truth",
    "reward_extra_info",
    "reward_extra_keys",
    "extra_info",
)


def _normalize_async_marker(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _validate_async_digest_visible_content(value: Any, *, field_name: str) -> None:
    validate_no_forbidden_model_visible_content(value, field_name=field_name)
    payload = _canonical_json(value)
    normalized = _normalize_async_marker(payload)
    compact = normalized.replace("_", "")
    for marker in ASYNC_DIGEST_EVALUATOR_ONLY_MARKERS:
        normalized_marker = _normalize_async_marker(marker)
        compact_marker = normalized_marker.replace("_", "")
        if normalized_marker in normalized or compact_marker in compact:
            raise ValueError(f"{field_name} contains evaluator-only content: {marker}")


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_digest(data: Any) -> str:
    payload = _canonical_json(data)
    validate_no_absolute_local_path(payload, field_name="digest_payload")
    _validate_async_digest_visible_content(data, field_name="digest_payload")
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _generation_record_digest_payload(record: GenerationRecord) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "model_call_id": record.model_call_id,
        "turn": record.turn,
        "context_revision": record.context_revision,
        "prompt_ids": record.prompt_ids,
        "output_token_ids": record.output_token_ids,
        "output_logprobs": record.output_logprobs,
        "gateway_route": record.gateway_route,
        "inference_backend": record.inference_backend,
        "policy_version": record.policy_version,
        "global_steps": record.global_steps,
        "min_global_steps": record.min_global_steps,
        "max_global_steps": record.max_global_steps,
    }


def compute_generation_record_digest(records: list[GenerationRecord | Mapping[str, Any]]) -> str:
    """计算 generation records 的稳定摘要，不包含本机路径或 evaluator-only 字段。"""

    parsed = [record if isinstance(record, GenerationRecord) else GenerationRecord.model_validate(record) for record in records]
    return _sha256_digest([_generation_record_digest_payload(record) for record in parsed])


def compute_training_view_trajectory_digest(
    training_view: TrainingView | Mapping[str, Any],
    *,
    generation_records: list[GenerationRecord | Mapping[str, Any]],
    sample_attempt_id: str,
    episode_id: str,
    run_id: str,
    prompt_digest: str | None = None,
    context_revision: int | None = None,
    raw_prompt_digest: str | None = None,
    task_id: str | None = None,
    dataset_uid: str | None = None,
    dataset_index: int | None = None,
    rollout_uid: str | None = None,
    uid: str | None = None,
    global_steps: int | None = None,
    min_global_steps: int | None = None,
    max_global_steps: int | None = None,
    policy_version: Mapping[str, Any] | None = None,
    reward_job_id: str | None = None,
) -> str:
    """计算 fully async reward 绑定使用的 trajectory digest。

    这里刻意包含 prompt token 或 prompt digest，避免相同 response token 被绑定到不同上下文。
    """

    view = training_view if isinstance(training_view, TrainingView) else TrainingView.model_validate(training_view)
    if prompt_digest is not None:
        validate_no_absolute_local_path(prompt_digest, field_name="prompt_digest")
    if raw_prompt_digest is not None:
        validate_no_absolute_local_path(raw_prompt_digest, field_name="raw_prompt_digest")
    payload = {
        "episode_id": episode_id,
        "run_id": run_id,
        "sample_attempt_id": sample_attempt_id,
        "task_id": task_id,
        "dataset_uid": dataset_uid,
        "dataset_index": dataset_index,
        "rollout_uid": rollout_uid,
        "uid": uid,
        "global_steps": global_steps,
        "min_global_steps": min_global_steps,
        "max_global_steps": max_global_steps,
        "policy_version": dict(policy_version or {}),
        "reward_job_id": reward_job_id,
        "prompt_ids": view.prompt_ids,
        "prompt_digest": prompt_digest,
        "context_revision": context_revision,
        "raw_prompt_digest": raw_prompt_digest,
        "response_ids": view.response_ids,
        "response_mask": view.response_mask,
        "response_logprobs": view.response_logprobs,
        "response_spans": [span.model_dump(mode="json") for span in view.response_spans],
        "generation_records": [
            _generation_record_digest_payload(
                record if isinstance(record, GenerationRecord) else GenerationRecord.model_validate(record)
            )
            for record in generation_records
        ],
    }
    return _sha256_digest(payload)


def compute_formal_sample_trajectory_digest(
    sample: FormalOnlineRLSample | Mapping[str, Any],
    *,
    sample_identity: SampleIdentity | Mapping[str, Any],
) -> str:
    """根据当前 formal online RL sample 内容重新计算 reward 绑定摘要。"""

    parsed_sample = sample if isinstance(sample, FormalOnlineRLSample) else FormalOnlineRLSample.model_validate(sample)
    identity = (
        sample_identity
        if isinstance(sample_identity, SampleIdentity)
        else SampleIdentity.model_validate(sample_identity)
    )
    payload = {
        "episode_id": identity.episode_id,
        "run_id": identity.run_id,
        "sample_attempt_id": identity.sample_attempt_id,
        "task_id": identity.task_id,
        "dataset_uid": identity.dataset_uid,
        "dataset_index": identity.dataset_index,
        "rollout_uid": identity.rollout_uid,
        "uid": identity.uid,
        "global_steps": identity.global_steps,
        "min_global_steps": identity.min_global_steps,
        "max_global_steps": identity.max_global_steps,
        "policy_version": identity.policy_version,
        "reward_job_id": identity.reward_job_id,
        "prompt_ids": parsed_sample.prompt_ids,
        "prompt_digest": identity.prompt_digest,
        "context_revision": identity.context_revision,
        "raw_prompt_digest": identity.raw_prompt_digest,
        "response_ids": parsed_sample.response_ids,
        "response_mask": parsed_sample.response_mask,
        "response_logprobs": parsed_sample.response_logprobs,
        "response_spans": [span.model_dump(mode="json") for span in parsed_sample.response_spans],
        "generation_records": [
            _generation_record_digest_payload(record) for record in parsed_sample.generation_records
        ],
    }
    return _sha256_digest(payload)


class ResumeCapability(StrictBaseModel):
    schema_version: str = "repo_harness_async_resume_capability_v0"
    resume_supported: bool = False
    resume_status: str = "unsupported_in_stage13_1"
    resume_ref: str | None = None

    @model_validator(mode="after")
    def validate_resume(self) -> "ResumeCapability":
        if self.resume_ref is not None:
            validate_opaque_ref(self.resume_ref, field_name="resume_ref")
        if not self.resume_supported and self.resume_status == "supported":
            raise ValueError("unsupported resume capability cannot use resume_status=supported")
        return self


class SampleIdentity(StrictBaseModel):
    schema_version: str = "repo_harness_async_sample_identity_v0"
    sample_id: str
    sample_attempt_id: str
    episode_id: str
    run_id: str
    task_id: str
    dataset_uid: str | None = None
    dataset_index: int | None = Field(default=None, ge=0)
    rollout_uid: str | None = None
    uid: str | None = None
    session_id: str | int | None = None
    global_steps: int = Field(ge=0)
    min_global_steps: int = Field(ge=0)
    max_global_steps: int = Field(ge=0)
    policy_version: dict[str, Any] = Field(default_factory=dict)
    reward_job_id: str | None = None
    prompt_digest: str | None = None
    context_revision: int | None = Field(default=None, ge=0)
    raw_prompt_digest: str | None = None
    generation_record_digest: str
    trajectory_digest: str

    @model_validator(mode="after")
    def validate_identity(self) -> "SampleIdentity":
        for field_name in ["sample_id", "sample_attempt_id", "episode_id", "run_id", "task_id"]:
            validate_safe_identifier(str(getattr(self, field_name)), field_name=field_name)
        if self.dataset_uid is not None:
            validate_safe_identifier(self.dataset_uid, field_name="dataset_uid")
        if self.rollout_uid is not None:
            validate_safe_identifier(self.rollout_uid, field_name="rollout_uid")
        if self.uid is not None:
            validate_safe_identifier(self.uid, field_name="uid")
        if isinstance(self.session_id, str):
            validate_safe_identifier(self.session_id, field_name="session_id")
        if self.reward_job_id is not None:
            validate_safe_identifier(self.reward_job_id, field_name="reward_job_id")
        if self.prompt_digest is not None:
            validate_no_absolute_local_path(self.prompt_digest, field_name="prompt_digest")
        if self.raw_prompt_digest is not None:
            validate_no_absolute_local_path(self.raw_prompt_digest, field_name="raw_prompt_digest")
        validate_no_absolute_local_path(_canonical_json(self.policy_version), field_name="policy_version")
        _validate_async_digest_visible_content(self.policy_version, field_name="policy_version")
        if self.dataset_uid is None and self.dataset_index is None:
            raise ValueError("sample identity requires dataset_uid or dataset_index")
        if self.rollout_uid is None and self.uid is None:
            raise ValueError("sample identity requires rollout_uid or uid")
        if not (self.min_global_steps <= self.global_steps <= self.max_global_steps):
            raise ValueError("global_steps must be within min_global_steps and max_global_steps")
        validate_no_absolute_local_path(self.generation_record_digest, field_name="generation_record_digest")
        validate_no_absolute_local_path(self.trajectory_digest, field_name="trajectory_digest")
        return self


class RewardFinalityFacts(StrictBaseModel):
    schema_version: str = "repo_harness_async_reward_finality_facts_v0"
    reward_state: RewardState
    reward_score: float | None = None
    reward_score_source: RewardScoreSource = "unknown"
    final_verifier_status: FinalVerifierStatus = "unknown"
    verifier_outcome: str | None = None
    final_verifier_ref: str | None = None
    reward_metadata_ref: str | None = None
    reward_job_id: str | None = None
    sample_attempt_id: str
    trajectory_digest: str
    generation_record_digest: str
    finalized_at: datetime | None = None
    invalid_reason: str | None = None
    derived_from_sync_episode: bool = False

    @model_validator(mode="after")
    def validate_finality(self) -> "RewardFinalityFacts":
        validate_safe_identifier(self.sample_attempt_id, field_name="sample_attempt_id")
        validate_no_absolute_local_path(self.trajectory_digest, field_name="trajectory_digest")
        validate_no_absolute_local_path(self.generation_record_digest, field_name="generation_record_digest")
        if self.final_verifier_ref is not None:
            validate_opaque_ref(self.final_verifier_ref, field_name="final_verifier_ref")
        if self.reward_metadata_ref is not None:
            validate_opaque_ref(self.reward_metadata_ref, field_name="reward_metadata_ref")
        if self.reward_job_id is not None:
            validate_safe_identifier(self.reward_job_id, field_name="reward_job_id")
        if self.reward_state != "final_verifier_completed" and self.invalid_reason is None:
            if self.reward_state in {"invalid_reward", "cancelled", "timeout", "stale", "rejected_by_visibility"}:
                raise ValueError("non-final reward state requires invalid_reason")
        return self


class RewardBindingFacts(StrictBaseModel):
    schema_version: str = "repo_harness_async_reward_binding_facts_v0"
    sample_identity: SampleIdentity
    reward_finality: RewardFinalityFacts

    @model_validator(mode="after")
    def validate_binding(self) -> "RewardBindingFacts":
        validate_sample_identity_binding(self.sample_identity, self.reward_finality)
        return self


class AsyncBatchEligibilityFacts(StrictBaseModel):
    schema_version: str = "repo_harness_async_batch_eligibility_facts_v0"
    sample_identity: SampleIdentity
    reward_finality: RewardFinalityFacts
    visibility_scan_status: Literal["passed", "failed", "missing"] = "missing"
    visibility_scan_digest: str | None = None

    @model_validator(mode="after")
    def validate_eligibility(self) -> "AsyncBatchEligibilityFacts":
        if self.visibility_scan_digest is not None:
            validate_no_absolute_local_path(self.visibility_scan_digest, field_name="visibility_scan_digest")
        validate_sample_identity_binding(self.sample_identity, self.reward_finality)
        return self


class AsyncEpisodeSnapshot(StrictBaseModel):
    schema_version: str = "repo_harness_async_episode_snapshot_v0"
    episode_id: str
    run_id: str
    task_id: str
    sample_attempt_id: str
    async_status: AsyncEpisodeStatus
    episode_status: str | None = None
    resource_lease_refs: dict[str, str] = Field(default_factory=dict)
    audit_refs: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resume: ResumeCapability = Field(default_factory=ResumeCapability)
    cancel_requested: bool = False
    cleanup_status: str | None = None
    orphan_diagnostics: list[str] = Field(default_factory=list)
    final_audit_write_completed: bool = False
    run_directory_writer_active: bool = False
    verifier_worker_may_still_access_workspace: bool = False
    workspace_lease_safely_released: bool = False

    @model_validator(mode="after")
    def validate_snapshot(self) -> "AsyncEpisodeSnapshot":
        for field_name in ["episode_id", "run_id", "task_id", "sample_attempt_id"]:
            validate_safe_identifier(str(getattr(self, field_name)), field_name=field_name)
        for key, value in {**self.resource_lease_refs, **self.audit_refs}.items():
            validate_opaque_ref(value, field_name=key)
        if self.verifier_worker_may_still_access_workspace and self.workspace_lease_safely_released:
            raise ValueError("workspace lease cannot be safely released while verifier may still access workspace")
        if self.run_directory_writer_active and self.final_audit_write_completed:
            raise ValueError("run directory writer cannot remain active after final audit completion")
        writer_not_yet_required_statuses = {"created", "queued", "orphaned"}
        if (
            not self.final_audit_write_completed
            and not self.run_directory_writer_active
            and self.async_status not in writer_not_yet_required_statuses
        ):
            raise ValueError("run directory writer must remain active until final audit completion")
        if self.async_status == "orphaned" and not self.orphan_diagnostics:
            raise ValueError("orphaned async episode requires orphan diagnostics")
        return self


class AsyncEpisodeHandleRef(StrictBaseModel):
    schema_version: str = "repo_harness_async_episode_handle_ref_v0"
    episode_id: str
    run_id: str
    sample_attempt_id: str
    handle_ref: str

    @model_validator(mode="after")
    def validate_handle_ref(self) -> "AsyncEpisodeHandleRef":
        validate_safe_identifier(self.episode_id, field_name="episode_id")
        validate_safe_identifier(self.run_id, field_name="run_id")
        validate_safe_identifier(self.sample_attempt_id, field_name="sample_attempt_id")
        validate_opaque_ref(self.handle_ref, field_name="handle_ref")
        return self


class AsyncEpisodeLifecycleFacts(StrictBaseModel):
    schema_version: str = "repo_harness_async_episode_lifecycle_facts_v0"
    snapshots: list[AsyncEpisodeSnapshot] = Field(default_factory=list)
    cleanup_deadline_seconds: float | None = Field(default=None, ge=0)
    recorder_lock_timeout_seconds: float | None = Field(default=None, ge=0)
    hidden_runtime_directory_cleanup_status: str | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> "AsyncEpisodeLifecycleFacts":
        if self.snapshots:
            ids = {snapshot.sample_attempt_id for snapshot in self.snapshots}
            if len(ids) > 1:
                raise ValueError("lifecycle facts must describe one sample_attempt_id")
        return self


class FormalAsyncOnlineRLSample(StrictBaseModel):
    schema_version: str = "repo_harness_formal_async_online_rl_sample_v0"
    sample: FormalOnlineRLSample
    sample_identity: SampleIdentity
    reward_finality: RewardFinalityFacts
    visibility_scan_status: Literal["passed", "failed", "missing"] = "missing"
    visibility_scan_digest: str | None = None

    @model_validator(mode="after")
    def validate_async_sample(self) -> "FormalAsyncOnlineRLSample":
        if self.visibility_scan_digest is not None:
            validate_no_absolute_local_path(self.visibility_scan_digest, field_name="visibility_scan_digest")
        validate_sample_identity_binding(self.sample_identity, self.reward_finality)
        return self


def validate_sample_identity_binding(
    sample_identity: SampleIdentity | Mapping[str, Any],
    reward_finality: RewardFinalityFacts | Mapping[str, Any],
) -> None:
    identity = (
        sample_identity if isinstance(sample_identity, SampleIdentity) else SampleIdentity.model_validate(sample_identity)
    )
    finality = (
        reward_finality
        if isinstance(reward_finality, RewardFinalityFacts)
        else RewardFinalityFacts.model_validate(reward_finality)
    )
    if identity.sample_attempt_id != finality.sample_attempt_id:
        raise ValueError("sample_attempt_id_mismatch")
    if identity.reward_job_id is None:
        raise ValueError("sample_identity_missing_reward_job_id")
    if finality.reward_job_id is None:
        raise ValueError("missing_reward_job_id")
    if identity.reward_job_id != finality.reward_job_id:
        raise ValueError("reward_job_id_mismatch")
    if identity.generation_record_digest != finality.generation_record_digest:
        raise ValueError("generation_record_digest_mismatch")
    if identity.trajectory_digest != finality.trajectory_digest:
        raise ValueError("trajectory_digest_mismatch")


def validate_late_reward_binding(
    sample_identity: SampleIdentity | Mapping[str, Any],
    reward_finality: RewardFinalityFacts | Mapping[str, Any],
) -> None:
    validate_sample_identity_binding(sample_identity, reward_finality)


def validate_reward_finality_for_policy_loss(
    reward_finality: RewardFinalityFacts | Mapping[str, Any],
    *,
    sample_identity: SampleIdentity | Mapping[str, Any] | None = None,
) -> RewardFinalityFacts:
    finality = (
        reward_finality
        if isinstance(reward_finality, RewardFinalityFacts)
        else RewardFinalityFacts.model_validate(reward_finality)
    )
    if sample_identity is not None:
        validate_sample_identity_binding(sample_identity, finality)
    if finality.reward_state != "final_verifier_completed":
        raise ValueError(f"reward_not_final:{finality.reward_state}")
    if finality.reward_score is None:
        raise ValueError("missing_reward_score")
    if finality.reward_score_source != "trusted_final_verifier":
        raise ValueError("reward_score_source_not_trusted_final_verifier")
    if finality.final_verifier_status not in {"accepted", "rejected"}:
        raise ValueError("final_verifier_status_not_trainable")
    if not finality.final_verifier_ref:
        raise ValueError("missing_final_verifier_ref")
    if not finality.reward_metadata_ref:
        raise ValueError("missing_reward_metadata_ref")
    if not finality.reward_job_id:
        raise ValueError("missing_reward_job_id")
    return finality


def formal_async_online_rl_sample_from_episode_result(
    episode_result: Any,
    *,
    sample_identity: SampleIdentity | Mapping[str, Any] | None = None,
    reward_finality: RewardFinalityFacts | Mapping[str, Any] | None = None,
    visibility_scan_status: Literal["passed", "failed", "missing"] = "missing",
    visibility_scan_digest: str | None = None,
) -> FormalAsyncOnlineRLSample:
    """从终态 episode result 构造 fully async formal batch 样本。"""

    from .episode import RepoHarnessEpisodeResult

    result = (
        episode_result
        if isinstance(episode_result, RepoHarnessEpisodeResult)
        else RepoHarnessEpisodeResult.model_validate(episode_result)
    )
    if result.training_view.online_rl_eligible is not True:
        raise ValueError("training_view_missing_online_rl_eligibility")
    identity = (
        sample_identity
        if isinstance(sample_identity, SampleIdentity)
        else SampleIdentity.model_validate(sample_identity or _derive_sample_identity_from_result(result))
    )
    finality = (
        reward_finality
        if isinstance(reward_finality, RewardFinalityFacts)
        else RewardFinalityFacts.model_validate(reward_finality or _derive_reward_finality_from_result(result, identity))
    )
    sample = formal_online_rl_sample_from_training_view(
        result.training_view,
        generation_records=result.generation_records,
        sample_id=identity.sample_id,
        invalid_for_training=result.invalid_for_training,
        invalid_for_online_rl=result.invalid_for_online_rl,
        invalid_reason=result.status_reason,
    )
    return FormalAsyncOnlineRLSample(
        sample=sample,
        sample_identity=identity,
        reward_finality=finality,
        visibility_scan_status=visibility_scan_status,
        visibility_scan_digest=visibility_scan_digest,
    )


def _validate_async_sample_matches_current_payload(sample: FormalAsyncOnlineRLSample) -> None:
    generation_record_digest = compute_generation_record_digest(sample.sample.generation_records)
    if generation_record_digest != sample.sample_identity.generation_record_digest:
        raise ValueError("generation_record_digest_mismatch_current_sample")
    trajectory_digest = compute_formal_sample_trajectory_digest(
        sample.sample,
        sample_identity=sample.sample_identity,
    )
    if trajectory_digest != sample.sample_identity.trajectory_digest:
        raise ValueError("trajectory_digest_mismatch_current_sample")


def validate_formal_async_online_rl_batch(
    samples: list[FormalAsyncOnlineRLSample | Mapping[str, Any]],
) -> list[FormalAsyncOnlineRLSample]:
    parsed = [
        FormalAsyncOnlineRLSample.model_validate(sample.model_dump(mode="python"))
        if isinstance(sample, FormalAsyncOnlineRLSample)
        else FormalAsyncOnlineRLSample.model_validate(sample)
        for sample in samples
    ]
    validate_formal_online_rl_batch([sample.sample for sample in parsed])
    for sample in parsed:
        _validate_async_sample_matches_current_payload(sample)
        validate_reward_finality_for_policy_loss(sample.reward_finality, sample_identity=sample.sample_identity)
        if sample.visibility_scan_status != "passed":
            raise ValueError("visibility_scan_not_passed")
    return parsed


def _derive_sample_identity_from_result(result: Any) -> dict[str, Any]:
    generation_digest = compute_generation_record_digest(result.generation_records)
    sample_attempt_id = f"{result.episode_id}:attempt-0"
    reward_job_id = f"sync:{result.run_id}:{sample_attempt_id}"
    min_steps = [
        record.min_global_steps
        for record in result.generation_records
        if record.min_global_steps is not None
    ]
    max_steps = [
        record.max_global_steps
        for record in result.generation_records
        if record.max_global_steps is not None
    ]
    global_steps = [
        record.global_steps
        for record in result.generation_records
        if record.global_steps is not None
    ]
    global_step = min(global_steps) if global_steps else 0
    min_global_step = min(min_steps) if min_steps else 0
    max_global_step = max(max_steps) if max_steps else 0
    policy_version = result.generation_records[0].policy_version if result.generation_records else {}
    trajectory_digest = compute_training_view_trajectory_digest(
        result.training_view,
        generation_records=result.generation_records,
        sample_attempt_id=sample_attempt_id,
        episode_id=result.episode_id,
        run_id=result.run_id,
        task_id=result.task_id,
        dataset_uid=result.task_id,
        rollout_uid=result.run_id,
        global_steps=global_step,
        min_global_steps=min_global_step,
        max_global_steps=max_global_step,
        policy_version=policy_version,
        reward_job_id=reward_job_id,
    )
    return {
        "sample_id": result.episode_id,
        "sample_attempt_id": sample_attempt_id,
        "episode_id": result.episode_id,
        "run_id": result.run_id,
        "task_id": result.task_id,
        "dataset_uid": result.task_id,
        "rollout_uid": result.run_id,
        "global_steps": global_step,
        "min_global_steps": min_global_step,
        "max_global_steps": max_global_step,
        "policy_version": policy_version,
        "reward_job_id": reward_job_id,
        "generation_record_digest": generation_digest,
        "trajectory_digest": trajectory_digest,
    }


def _derive_reward_finality_from_result(result: Any, identity: SampleIdentity) -> dict[str, Any]:
    final_verifier_ref = None
    if result.verifier_summary is not None:
        final_verifier_ref = result.verifier_summary.summary_ref
    final_verifier_ref = final_verifier_ref or result.training_view.extra_fields.get("repo_harness_final_verifier_ref")

    reward_metadata_ref = None
    if result.reward is not None:
        reward_metadata_ref = result.reward.reward_metadata_ref
    reward_metadata_ref = reward_metadata_ref or result.training_view.extra_fields.get("repo_harness_reward_metadata_ref")

    accepted = result.verifier_summary.accepted if result.verifier_summary is not None else None
    final_status = "accepted" if accepted is True else "rejected" if accepted is False else "unknown"
    return {
        "reward_state": "final_verifier_completed" if result.status in {"succeeded", "failed"} else "invalid_reward",
        "reward_score": result.training_view.reward_score,
        "reward_score_source": "trusted_final_verifier" if final_verifier_ref and reward_metadata_ref else "unknown",
        "final_verifier_status": final_status,
        "verifier_outcome": final_status,
        "final_verifier_ref": final_verifier_ref,
        "reward_metadata_ref": reward_metadata_ref,
        "reward_job_id": identity.reward_job_id or f"sync:{result.run_id}:{identity.sample_attempt_id}",
        "sample_attempt_id": identity.sample_attempt_id,
        "trajectory_digest": identity.trajectory_digest,
        "generation_record_digest": identity.generation_record_digest,
        "invalid_reason": None if result.status in {"succeeded", "failed"} else result.status_reason,
        "derived_from_sync_episode": True,
    }
