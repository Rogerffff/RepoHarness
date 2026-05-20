"""Stage 13.2 fully async queue / trainer bridge helpers.

This module intentionally avoids importing ``verl``, ``ray``, ``torch`` or
``tensordict``.  It only prepares RepoHarness facts for objects shaped like
reference/verl ``RolloutSample`` / ``DataProto`` and validates the handoff
before Ray serialization.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.rl.async_contracts import (
    FormalAsyncOnlineRLSample,
    formal_async_online_rl_sample_from_episode_result,
    validate_formal_async_online_rl_batch,
)
from repo_harness.rl.episode import RepoHarnessEpisodeResult
from repo_harness.rl.visibility import (
    FlatScalar,
    VisibilityContractError,
    validate_batch_extra_fields,
    validate_no_absolute_local_path,
    validate_opaque_ref,
    validate_safe_identifier,
)
from repo_harness.schema_base import StrictBaseModel

from .visibility import (
    VerlVisibilityError,
    validate_fully_async_queue_payload_visibility,
    validate_pre_serialization_rollout_sample_visibility,
)

QueueSampleClassification = Literal["valid", "rejected", "diagnostic"]


class RepoHarnessFullyAsyncQueueFacts(StrictBaseModel):
    """RepoHarness per-sample facts carried through fully async ``non_tensor_batch``."""

    schema_version: str = "repo_harness_verl_fully_async_queue_facts_v0"
    sample_id: str
    sample_attempt_id: str
    episode_id: str
    run_id: str
    task_id: str
    dataset_uid: str | None = None
    dataset_index: int | None = Field(default=None, ge=0)
    rollout_uid: str | None = None
    uid: str | None = None
    global_steps: int = Field(default=0, ge=0)
    min_global_steps: int = Field(default=0, ge=0)
    max_global_steps: int = Field(default=0, ge=0)
    policy_version_digest: str | None = None
    generation_record_digest: str | None = None
    trajectory_digest: str | None = None
    reward_state: str = "invalid_reward"
    reward_score_source: str = "unknown"
    final_verifier_status: str = "unknown"
    reward_job_id: str | None = None
    visibility_scan_status: Literal["passed", "failed", "missing"] = "missing"
    visibility_scan_digest: str | None = None
    final_verifier_ref: str | None = None
    reward_metadata_ref: str | None = None
    audit_manifest_ref: str | None = None
    valid_for_policy_loss: bool = False
    sample_classification: QueueSampleClassification = "diagnostic"
    rejection_reason: str | None = None
    staleness: int | None = Field(default=None, ge=0)
    partial_rollout_supported: bool = False
    partial_rollout_status: str = "not_requested"
    invalid_reason: str | None = None

    @model_validator(mode="after")
    def validate_facts(self) -> "RepoHarnessFullyAsyncQueueFacts":
        for field_name in ["sample_id", "sample_attempt_id", "episode_id", "run_id", "task_id"]:
            validate_safe_identifier(str(getattr(self, field_name)), field_name=field_name)
        if self.dataset_uid is not None:
            validate_safe_identifier(self.dataset_uid, field_name="dataset_uid")
        if self.rollout_uid is not None:
            validate_safe_identifier(self.rollout_uid, field_name="rollout_uid")
        if self.uid is not None:
            validate_safe_identifier(self.uid, field_name="uid")
        if self.reward_job_id is not None:
            validate_safe_identifier(self.reward_job_id, field_name="reward_job_id")
        if self.policy_version_digest is not None:
            validate_no_absolute_local_path(self.policy_version_digest, field_name="policy_version_digest")
        if self.generation_record_digest is not None:
            validate_no_absolute_local_path(self.generation_record_digest, field_name="generation_record_digest")
        if self.trajectory_digest is not None:
            validate_no_absolute_local_path(self.trajectory_digest, field_name="trajectory_digest")
        if self.visibility_scan_digest is not None:
            validate_no_absolute_local_path(self.visibility_scan_digest, field_name="visibility_scan_digest")
        if self.visibility_scan_status == "passed" and not self.visibility_scan_digest:
            raise ValueError("passed visibility scan requires visibility_scan_digest")
        if self.final_verifier_ref is not None:
            validate_opaque_ref(self.final_verifier_ref, field_name="final_verifier_ref")
        if self.reward_metadata_ref is not None:
            validate_opaque_ref(self.reward_metadata_ref, field_name="reward_metadata_ref")
        if self.audit_manifest_ref is not None:
            validate_opaque_ref(self.audit_manifest_ref, field_name="audit_manifest_ref")
        if not (self.min_global_steps <= self.global_steps <= self.max_global_steps):
            raise ValueError("global_steps must be within min_global_steps and max_global_steps")
        if self.valid_for_policy_loss:
            if self.sample_classification != "valid":
                raise ValueError("valid_for_policy_loss requires sample_classification=valid")
            if self.visibility_scan_status != "passed":
                raise ValueError("valid_for_policy_loss requires passed visibility scan")
            if self.rejection_reason is not None or self.invalid_reason is not None:
                raise ValueError("valid_for_policy_loss cannot carry rejection or invalid reason")
            required_fields = {
                "generation_record_digest": self.generation_record_digest,
                "trajectory_digest": self.trajectory_digest,
                "reward_job_id": self.reward_job_id,
                "final_verifier_ref": self.final_verifier_ref,
                "reward_metadata_ref": self.reward_metadata_ref,
            }
            missing = [key for key, value in required_fields.items() if not value]
            if missing:
                raise ValueError(f"valid_for_policy_loss missing required facts: {','.join(sorted(missing))}")
            if self.reward_state != "final_verifier_completed":
                raise ValueError("valid_for_policy_loss requires final reward state")
            if self.reward_score_source != "trusted_final_verifier":
                raise ValueError("valid_for_policy_loss requires trusted final verifier reward")
            if self.final_verifier_status not in {"accepted", "rejected"}:
                raise ValueError("valid_for_policy_loss requires accepted or rejected verifier status")
        elif self.sample_classification == "valid":
            raise ValueError("sample_classification=valid requires valid_for_policy_loss=true")
        try:
            validate_batch_extra_fields(self.to_queue_fields())
        except VisibilityContractError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_queue_fields(self) -> dict[str, FlatScalar]:
        """Project facts to flat ``repo_harness_*`` values for ``non_tensor_batch``."""

        return {
            "repo_harness_sample_id": self.sample_id,
            "repo_harness_sample_attempt_id": self.sample_attempt_id,
            "repo_harness_episode_id": self.episode_id,
            "repo_harness_run_id": self.run_id,
            "repo_harness_task_id": self.task_id,
            "repo_harness_dataset_uid": self.dataset_uid,
            "repo_harness_dataset_index": self.dataset_index,
            "repo_harness_rollout_uid": self.rollout_uid,
            "repo_harness_uid": self.uid,
            "repo_harness_global_steps": self.global_steps,
            "repo_harness_min_global_steps": self.min_global_steps,
            "repo_harness_max_global_steps": self.max_global_steps,
            "repo_harness_policy_version_digest": self.policy_version_digest,
            "repo_harness_generation_record_digest": self.generation_record_digest,
            "repo_harness_trajectory_digest": self.trajectory_digest,
            "repo_harness_reward_state": self.reward_state,
            "repo_harness_reward_score_source": self.reward_score_source,
            "repo_harness_final_verifier_status": self.final_verifier_status,
            "repo_harness_reward_job_id": self.reward_job_id,
            "repo_harness_visibility_scan_status": self.visibility_scan_status,
            "repo_harness_visibility_scan_digest": self.visibility_scan_digest,
            "repo_harness_final_verifier_ref": self.final_verifier_ref,
            "repo_harness_reward_metadata_ref": self.reward_metadata_ref,
            "repo_harness_audit_manifest_ref": self.audit_manifest_ref,
            "repo_harness_valid_for_policy_loss": self.valid_for_policy_loss,
            "repo_harness_sample_classification": self.sample_classification,
            "repo_harness_rejection_reason": self.rejection_reason,
            "repo_harness_staleness": self.staleness,
            "repo_harness_partial_rollout_supported": self.partial_rollout_supported,
            "repo_harness_partial_rollout_status": self.partial_rollout_status,
            "repo_harness_invalid_reason": self.invalid_reason,
        }


class RepoHarnessFullyAsyncSelectionReport(StrictBaseModel):
    """Report for selecting valid RolloutSample objects from a queue payload stream."""

    schema_version: str = "repo_harness_verl_fully_async_selection_report_v0"
    required_samples: int = Field(gt=0)
    observed_queue_samples: int = Field(ge=0)
    valid_sample_count: int = Field(ge=0)
    rejected_sample_count: int = Field(ge=0)
    diagnostic_sample_count: int = Field(ge=0)
    insufficient_valid_samples: bool = False
    insufficient_reason: str | None = None
    selected_sample_ids: list[str] = Field(default_factory=list)
    rejected_reasons: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_report(self) -> "RepoHarnessFullyAsyncSelectionReport":
        if self.valid_sample_count != len(self.selected_sample_ids):
            raise ValueError("valid_sample_count must match selected_sample_ids length")
        if self.insufficient_valid_samples and not self.insufficient_reason:
            raise ValueError("insufficient report requires reason")
        return self


def build_queue_facts_from_episode_result(
    episode_result: RepoHarnessEpisodeResult | Mapping[str, Any],
    *,
    visibility_scan_status: Literal["passed", "failed", "missing"] = "missing",
    visibility_scan_digest: str | None = None,
    current_global_steps: int | None = None,
    staleness_threshold: int | None = None,
    partial_rollout_supported: bool = False,
    partial_rollout_status: str = "not_requested",
) -> RepoHarnessFullyAsyncQueueFacts:
    """Classify an episode result and build queue facts for fully async handoff.

    Classification happens before formal validation.  Rejected or diagnostic
    samples still produce audit facts, but only valid candidates are allowed to
    call the formal async online RL validator.
    """

    result = (
        episode_result
        if isinstance(episode_result, RepoHarnessEpisodeResult)
        else RepoHarnessEpisodeResult.model_validate(episode_result)
    )
    base = _base_fact_values(result, visibility_scan_status, visibility_scan_digest)
    invalid_reason = _pre_formal_rejection_reason(
        result,
        visibility_scan_status=visibility_scan_status,
        current_global_steps=current_global_steps,
        staleness_threshold=staleness_threshold,
        partial_rollout_status=partial_rollout_status,
        partial_rollout_supported=partial_rollout_supported,
    )
    staleness = _compute_staleness(result, current_global_steps=current_global_steps)
    if invalid_reason is not None:
        return RepoHarnessFullyAsyncQueueFacts(
            **base,
            sample_classification="rejected" if result.status not in {"cancelled", "timeout"} else "diagnostic",
            rejection_reason=invalid_reason,
            invalid_reason=invalid_reason,
            staleness=staleness,
            partial_rollout_supported=partial_rollout_supported,
            partial_rollout_status=partial_rollout_status,
        )

    try:
        async_sample = formal_async_online_rl_sample_from_episode_result(
            result,
            visibility_scan_status=visibility_scan_status,
            visibility_scan_digest=visibility_scan_digest,
        )
        validate_formal_async_online_rl_batch([async_sample])
    except ValueError as exc:
        reason = str(exc)
        return RepoHarnessFullyAsyncQueueFacts(
            **base,
            sample_classification="rejected",
            rejection_reason=reason,
            invalid_reason=reason,
            staleness=staleness,
            partial_rollout_supported=partial_rollout_supported,
            partial_rollout_status=partial_rollout_status,
        )

    identity = async_sample.sample_identity
    finality = async_sample.reward_finality
    policy_digest = None
    if identity.policy_version:
        policy_digest = _safe_digest(identity.policy_version)
    return RepoHarnessFullyAsyncQueueFacts(
        sample_id=identity.sample_id,
        sample_attempt_id=identity.sample_attempt_id,
        episode_id=identity.episode_id,
        run_id=identity.run_id,
        task_id=identity.task_id,
        dataset_uid=identity.dataset_uid,
        dataset_index=identity.dataset_index,
        rollout_uid=identity.rollout_uid,
        uid=identity.uid,
        global_steps=identity.global_steps,
        min_global_steps=identity.min_global_steps,
        max_global_steps=identity.max_global_steps,
        policy_version_digest=policy_digest,
        generation_record_digest=identity.generation_record_digest,
        trajectory_digest=identity.trajectory_digest,
        reward_state=finality.reward_state,
        reward_score_source=finality.reward_score_source,
        final_verifier_status=finality.final_verifier_status,
        reward_job_id=identity.reward_job_id,
        visibility_scan_status=visibility_scan_status,
        visibility_scan_digest=visibility_scan_digest,
        final_verifier_ref=finality.final_verifier_ref,
        reward_metadata_ref=finality.reward_metadata_ref,
        audit_manifest_ref=_audit_manifest_ref(result),
        valid_for_policy_loss=True,
        sample_classification="valid",
        staleness=staleness,
        partial_rollout_supported=partial_rollout_supported,
        partial_rollout_status=partial_rollout_status,
    )


def attach_queue_facts_to_rollout_sample(
    rollout_sample: Any,
    facts: RepoHarnessFullyAsyncQueueFacts | Mapping[str, Any],
) -> Any:
    """Attach per-sample facts to ``full_batch.non_tensor_batch`` as batch-sized arrays."""

    parsed = facts if isinstance(facts, RepoHarnessFullyAsyncQueueFacts) else RepoHarnessFullyAsyncQueueFacts.model_validate(facts)
    full_batch = getattr(rollout_sample, "full_batch", None)
    if full_batch is None:
        raise ValueError("rollout_sample_missing_full_batch")
    if getattr(full_batch, "non_tensor_batch", None) is None:
        setattr(full_batch, "non_tensor_batch", {})
    if getattr(full_batch, "meta_info", None) is None:
        setattr(full_batch, "meta_info", {})
    sample_id = getattr(rollout_sample, "sample_id", None)
    if sample_id is None:
        setattr(rollout_sample, "sample_id", parsed.sample_id)
    elif str(sample_id) != parsed.sample_id:
        raise ValueError("rollout_sample_id_mismatch_queue_facts")
    batch_size = _infer_batch_size(full_batch)
    non_tensor_batch = getattr(full_batch, "non_tensor_batch")
    for key, value in parsed.to_queue_fields().items():
        non_tensor_batch[key] = [value for _ in range(batch_size)]
    # reference/verl assemble_batch_from_rollout_samples reads these unprefixed
    # fields directly when computing partial rollout statistics.
    non_tensor_batch["global_steps"] = [parsed.global_steps for _ in range(batch_size)]
    non_tensor_batch["min_global_steps"] = [parsed.min_global_steps for _ in range(batch_size)]
    non_tensor_batch["max_global_steps"] = [parsed.max_global_steps for _ in range(batch_size)]

    rollout_status = getattr(rollout_sample, "rollout_status", None)
    if rollout_status is None:
        rollout_status = {}
        setattr(rollout_sample, "rollout_status", rollout_status)
    rollout_status.update(
        {
            "repo_harness_visibility_scan_status": parsed.visibility_scan_status,
            "repo_harness_visibility_scan_digest": parsed.visibility_scan_digest,
            "repo_harness_valid_for_policy_loss": parsed.valid_for_policy_loss,
            "repo_harness_sample_classification": parsed.sample_classification,
        }
    )
    validate_pre_serialization_rollout_sample_visibility(rollout_sample)
    return rollout_sample


def queue_facts_from_rollout_sample(rollout_sample: Any) -> RepoHarnessFullyAsyncQueueFacts:
    """Extract the first sample's RepoHarness facts from a rollout sample."""

    full_batch = getattr(rollout_sample, "full_batch", None)
    if full_batch is None:
        raise ValueError("rollout_sample_missing_full_batch")
    non_tensor_batch = getattr(full_batch, "non_tensor_batch", {})
    values: dict[str, Any] = {}
    for key in RepoHarnessFullyAsyncQueueFacts.model_fields:
        if key == "schema_version":
            continue
        queue_key = f"repo_harness_{key}"
        if queue_key in non_tensor_batch:
            values[key] = _first_value(non_tensor_batch[queue_key])
    rollout_status = getattr(rollout_sample, "rollout_status", {})
    if isinstance(rollout_status, Mapping):
        for key in ["visibility_scan_status", "visibility_scan_digest", "valid_for_policy_loss", "sample_classification"]:
            queue_key = f"repo_harness_{key}"
            if key not in values and queue_key in rollout_status:
                values[key] = rollout_status[queue_key]
    return RepoHarnessFullyAsyncQueueFacts.model_validate(values)


def serialize_rollout_sample_for_message_queue(
    rollout_sample: Any,
    *,
    visibility_scan_status: str | None = None,
    visibility_scan_digest: str | None = None,
    serializer: Literal["cloudpickle", "pickle"] = "cloudpickle",
) -> bytes:
    """Serialize a scanned rollout sample for the fully async MessageQueue boundary."""

    validate_pre_serialization_rollout_sample_visibility(rollout_sample)
    status = visibility_scan_status or _extract_fact(rollout_sample, "repo_harness_visibility_scan_status")
    digest = visibility_scan_digest or _extract_fact(rollout_sample, "repo_harness_visibility_scan_digest")
    payload = _serializer_module(serializer).dumps(rollout_sample)
    validate_fully_async_queue_payload_visibility(
        payload,
        visibility_scan_status=str(status) if status is not None else None,
        visibility_scan_digest=str(digest) if digest is not None else None,
    )
    return payload


def deserialize_message_queue_payload(
    payload: bytes,
    *,
    visibility_scan_status: str | None = None,
    visibility_scan_digest: str | None = None,
    serializer: Literal["cloudpickle", "pickle"] = "cloudpickle",
) -> Any:
    """Deserialize a queue payload after checking its external scan ledger facts."""

    validate_fully_async_queue_payload_visibility(
        payload,
        visibility_scan_status=visibility_scan_status,
        visibility_scan_digest=visibility_scan_digest,
    )
    restored = _serializer_module(serializer).loads(payload)
    validate_pre_serialization_rollout_sample_visibility(restored)
    _validate_internal_scan_ledger_matches_external(
        restored,
        visibility_scan_status=visibility_scan_status,
        visibility_scan_digest=visibility_scan_digest,
    )
    return restored


def validate_rollout_sample_for_trainer_batch(
    rollout_sample: Any,
    *,
    formal_sample: FormalAsyncOnlineRLSample | Mapping[str, Any] | None = None,
    current_global_steps: int | None = None,
    staleness_threshold: int | None = None,
) -> RepoHarnessFullyAsyncQueueFacts:
    """Validate one queued RolloutSample before it can count toward policy loss."""

    validate_pre_serialization_rollout_sample_visibility(rollout_sample)
    facts = queue_facts_from_rollout_sample(rollout_sample)
    rollout_sample_id = getattr(rollout_sample, "sample_id", None)
    if rollout_sample_id is None or str(rollout_sample_id) != facts.sample_id:
        raise ValueError("rollout_sample_id_mismatch_queue_facts")
    if facts.staleness is not None and staleness_threshold is not None and facts.staleness > staleness_threshold:
        raise ValueError("stale_trajectory")
    if current_global_steps is not None and facts.max_global_steps is not None and staleness_threshold is not None:
        staleness = max(0, current_global_steps - facts.max_global_steps)
        if staleness > staleness_threshold:
            raise ValueError("stale_trajectory")
    if not facts.valid_for_policy_loss:
        raise ValueError(f"rollout_sample_not_valid_for_policy_loss:{facts.rejection_reason or facts.invalid_reason}")
    if facts.sample_classification != "valid":
        raise ValueError(f"rollout_sample_not_valid:{facts.sample_classification}")
    if formal_sample is not None:
        parsed = (
            formal_sample
            if isinstance(formal_sample, FormalAsyncOnlineRLSample)
            else FormalAsyncOnlineRLSample.model_validate(formal_sample)
        )
        validate_formal_async_online_rl_batch([parsed])
        if parsed.sample_identity.sample_id != facts.sample_id:
            raise ValueError("formal_sample_id_mismatch_queue_facts")
        if parsed.sample_identity.trajectory_digest != facts.trajectory_digest:
            raise ValueError("formal_sample_trajectory_digest_mismatch_queue_facts")
    return facts


def select_valid_rollout_samples_for_required_count(
    rollout_samples: Sequence[Any],
    *,
    required_samples: int,
    formal_samples_by_sample_id: Mapping[str, FormalAsyncOnlineRLSample | Mapping[str, Any]] | None = None,
    current_global_steps: int | None = None,
    staleness_threshold: int | None = None,
) -> tuple[list[Any], RepoHarnessFullyAsyncSelectionReport]:
    """Select valid queued samples; invalid queue occupancy never satisfies required_samples."""

    selected: list[Any] = []
    rejected_reasons: dict[str, str] = {}
    rejected_count = 0
    diagnostic_count = 0
    formal_by_id = dict(formal_samples_by_sample_id or {})
    for sample in rollout_samples:
        try:
            facts = queue_facts_from_rollout_sample(sample)
            formal_sample = formal_by_id.get(facts.sample_id)
            validate_rollout_sample_for_trainer_batch(
                sample,
                formal_sample=formal_sample,
                current_global_steps=current_global_steps,
                staleness_threshold=staleness_threshold,
            )
        except ValueError as exc:
            try:
                facts = queue_facts_from_rollout_sample(sample)
                sample_id = facts.sample_id
                if facts.sample_classification == "diagnostic":
                    diagnostic_count += 1
                else:
                    rejected_count += 1
            except Exception:
                sample_id = f"unparseable-{rejected_count + diagnostic_count}"
                rejected_count += 1
            rejected_reasons[sample_id] = str(exc)
            continue
        selected.append(sample)
        if len(selected) >= required_samples:
            break

    insufficient = len(selected) < required_samples
    return selected, RepoHarnessFullyAsyncSelectionReport(
        required_samples=required_samples,
        observed_queue_samples=len(rollout_samples),
        valid_sample_count=len(selected),
        rejected_sample_count=rejected_count,
        diagnostic_sample_count=diagnostic_count,
        insufficient_valid_samples=insufficient,
        insufficient_reason="insufficient_valid_queue_samples" if insufficient else None,
        selected_sample_ids=[queue_facts_from_rollout_sample(sample).sample_id for sample in selected],
        rejected_reasons=rejected_reasons,
    )


def apply_reference_addition_process_compat(full_batch: Any) -> Any:
    """Mirror reference/verl ``addition_process`` metrics movement without importing verl."""

    meta_info = getattr(full_batch, "meta_info", None)
    if not isinstance(meta_info, dict):
        raise ValueError("full_batch_missing_meta_info")
    if "metrics" not in meta_info:
        raise ValueError("missing_reference_metrics")
    metrics = meta_info.pop("metrics")
    if not isinstance(metrics, list):
        raise ValueError("reference_metrics_must_be_list")
    processing_times = []
    tool_calls_times = []
    for item in metrics:
        if not isinstance(item, Mapping):
            raise ValueError("reference_metrics_item_must_be_mapping")
        if "generate_sequences" not in item or "tool_calls" not in item:
            raise ValueError("reference_metrics_missing_generate_sequences_or_tool_calls")
        processing_times.append(item["generate_sequences"])
        tool_calls_times.append(item["tool_calls"])
    if getattr(full_batch, "non_tensor_batch", None) is None:
        setattr(full_batch, "non_tensor_batch", {})
    full_batch.non_tensor_batch["processing_times"] = processing_times
    full_batch.non_tensor_batch["tool_calls_times"] = tool_calls_times
    return full_batch


def _base_fact_values(
    result: RepoHarnessEpisodeResult,
    visibility_scan_status: str,
    visibility_scan_digest: str | None,
) -> dict[str, Any]:
    return {
        "sample_id": result.episode_id,
        "sample_attempt_id": f"{result.episode_id}:attempt-0",
        "episode_id": result.episode_id,
        "run_id": result.run_id,
        "task_id": result.task_id,
        "dataset_uid": result.task_id,
        "rollout_uid": result.run_id,
        "visibility_scan_status": visibility_scan_status,
        "visibility_scan_digest": visibility_scan_digest,
        "audit_manifest_ref": _audit_manifest_ref(result),
        "reward_state": "invalid_reward",
    }


def _pre_formal_rejection_reason(
    result: RepoHarnessEpisodeResult,
    *,
    visibility_scan_status: str,
    current_global_steps: int | None,
    staleness_threshold: int | None,
    partial_rollout_status: str,
    partial_rollout_supported: bool,
) -> str | None:
    if visibility_scan_status != "passed":
        return "visibility_scan_not_passed"
    if partial_rollout_status not in {"not_requested", "complete"}:
        if not partial_rollout_supported:
            return "partial_rollout_unsupported_in_stage13_2"
        return "partial_rollout_not_complete"
    if partial_rollout_status == "complete" and not partial_rollout_supported:
        return "partial_rollout_complete_requires_supported"
    if result.invalid_for_training or result.invalid_for_online_rl:
        return result.status_reason or "episode_marked_invalid_for_training_or_online_rl"
    if result.status in {"invalid", "invalid_task", "infrastructure_error", "cancelled", "timeout", "no_progress"}:
        return result.status_reason or f"episode_status_{result.status}"
    reward_finality_reason = _reward_finality_rejection_reason(result)
    if reward_finality_reason is not None:
        return reward_finality_reason
    staleness = _compute_staleness(result, current_global_steps=current_global_steps)
    if staleness is not None and staleness_threshold is not None and staleness > staleness_threshold:
        return "stale_trajectory"
    return None


def _reward_finality_rejection_reason(result: RepoHarnessEpisodeResult) -> str | None:
    if result.training_view.reward_score is None:
        return "missing_reward_score"
    if result.verifier_summary is None:
        return "missing_final_verifier_outcome"
    accepted = result.verifier_summary.accepted
    verifier_status = result.verifier_summary.status
    if accepted is True:
        if result.status != "succeeded" or verifier_status not in {None, "accepted"}:
            return "episode_status_verifier_outcome_mismatch"
    elif accepted is False:
        if result.status != "failed" or verifier_status not in {None, "rejected"}:
            return "episode_status_verifier_outcome_mismatch"
    else:
        return "missing_final_verifier_outcome"
    final_verifier_ref = None
    if result.verifier_summary is not None:
        final_verifier_ref = result.verifier_summary.summary_ref
    final_verifier_ref = final_verifier_ref or result.training_view.extra_fields.get("repo_harness_final_verifier_ref")
    if not final_verifier_ref:
        return "missing_final_verifier_ref"
    reward_metadata_ref = None
    if result.reward is not None:
        reward_metadata_ref = result.reward.reward_metadata_ref
    reward_metadata_ref = reward_metadata_ref or result.training_view.extra_fields.get("repo_harness_reward_metadata_ref")
    if not reward_metadata_ref:
        return "missing_reward_metadata_ref"
    if result.status not in {"succeeded", "failed"}:
        return f"episode_status_{result.status}"
    return None


def _compute_staleness(result: RepoHarnessEpisodeResult, *, current_global_steps: int | None) -> int | None:
    if current_global_steps is None:
        return None
    max_steps = [
        record.max_global_steps
        for record in result.generation_records
        if record.max_global_steps is not None
    ]
    max_global_steps = max(max_steps) if max_steps else 0
    return max(0, current_global_steps - max_global_steps)


def _audit_manifest_ref(result: RepoHarnessEpisodeResult) -> str | None:
    for key in ["artifacts_manifest", "manifest", "audit_manifest"]:
        value = result.audit_ref.important_artifact_refs.get(key)
        if value:
            return value
    if result.audit_ref.artifacts_manifest_path:
        return None
    return None


def _infer_batch_size(full_batch: Any) -> int:
    try:
        length = len(full_batch)
    except Exception:
        length = None
    if isinstance(length, int) and length > 0:
        return length
    for container_name in ("batch", "non_tensor_batch"):
        container = getattr(full_batch, container_name, {})
        if isinstance(container, Mapping):
            for value in container.values():
                size = _value_length(value)
                if size > 0:
                    return size
    return 1


def _value_length(value: Any) -> int:
    if isinstance(value, (str, bytes)):
        return 1
    shape = getattr(value, "shape", None)
    if shape is not None and len(shape) > 0:
        return int(shape[0])
    if isinstance(value, Sequence):
        return len(value)
    try:
        return len(value)
    except Exception:
        return 1


def _first_value(value: Any) -> Any:
    if isinstance(value, (str, bytes)):
        return value
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, Sequence):
        return value[0] if value else None
    return value


def _iter_flat_values(value: Any) -> list[Any]:
    if isinstance(value, (str, bytes)):
        return [value]
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, Sequence):
        flattened: list[Any] = []
        for item in value:
            flattened.extend(_iter_flat_values(item))
        return flattened
    return [value]


def _extract_fact(rollout_sample: Any, key: str) -> Any:
    rollout_status = getattr(rollout_sample, "rollout_status", None)
    if isinstance(rollout_status, Mapping) and key in rollout_status:
        return rollout_status[key]
    full_batch = getattr(rollout_sample, "full_batch", None)
    if full_batch is not None:
        non_tensor_batch = getattr(full_batch, "non_tensor_batch", {})
        if isinstance(non_tensor_batch, Mapping) and key in non_tensor_batch:
            return _first_value(non_tensor_batch[key])
    return None


def _extract_all_fact_values(rollout_sample: Any, key: str) -> list[Any]:
    values: list[Any] = []
    rollout_status = getattr(rollout_sample, "rollout_status", None)
    if isinstance(rollout_status, Mapping) and key in rollout_status:
        values.append(rollout_status[key])
    full_batch = getattr(rollout_sample, "full_batch", None)
    if full_batch is not None:
        non_tensor_batch = getattr(full_batch, "non_tensor_batch", {})
        if isinstance(non_tensor_batch, Mapping) and key in non_tensor_batch:
            values.extend(_iter_flat_values(non_tensor_batch[key]))
        meta_info = getattr(full_batch, "meta_info", {})
        if isinstance(meta_info, Mapping) and key in meta_info:
            values.extend(_iter_flat_values(meta_info[key]))
    return values


def _validate_internal_scan_ledger_matches_external(
    rollout_sample: Any,
    *,
    visibility_scan_status: str | None,
    visibility_scan_digest: str | None,
) -> None:
    if visibility_scan_status is None:
        raise VerlVisibilityError("missing_visibility_scan_status_after_deserialize")
    if visibility_scan_digest is None:
        raise VerlVisibilityError("missing_visibility_scan_digest_after_deserialize")
    status_values = _extract_all_fact_values(rollout_sample, "repo_harness_visibility_scan_status")
    digest_values = _extract_all_fact_values(rollout_sample, "repo_harness_visibility_scan_digest")
    if not status_values:
        raise VerlVisibilityError("missing_internal_visibility_scan_status_after_deserialize")
    if not digest_values:
        raise VerlVisibilityError("missing_internal_visibility_scan_digest_after_deserialize")
    for value in status_values:
        if str(value) != str(visibility_scan_status):
            raise VerlVisibilityError("visibility_scan_status_mismatch_after_deserialize")
    for value in digest_values:
        if str(value) != str(visibility_scan_digest):
            raise VerlVisibilityError("visibility_scan_digest_mismatch_after_deserialize")


def _serializer_module(serializer: str) -> Any:
    if serializer == "cloudpickle":
        try:
            import cloudpickle  # type: ignore[import-not-found]

            return cloudpickle
        except Exception:
            return pickle
    if serializer == "pickle":
        return pickle
    raise ValueError(f"unknown_serializer:{serializer}")


def _safe_digest(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    validate_no_absolute_local_path(text, field_name="queue_fact_digest_payload")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
