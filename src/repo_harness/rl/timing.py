"""训练 episode 的 timing 和 resource schema。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel

from .visibility import CONTRACT_VERSION, validate_no_absolute_local_path

TIMING_BUCKET_POLICY = "exclusive_runtime_facade_v1"
MIN_EXPLAINED_RATIO = 0.95
EXCLUSIVE_TIMING_BUCKET_FIELDS = (
    "queue_wait_seconds",
    "workspace_materialization_seconds",
    "docker_setup_seconds",
    "dependency_restore_seconds",
    "baseline_verifier_seconds",
    "agent_loop_seconds",
    "model_call_seconds",
    "context_prepare_seconds",
    "tool_seconds",
    "verifier_seconds",
    "final_verifier_seconds",
    "reward_compute_seconds",
    "artifact_write_seconds",
    "cleanup_seconds",
)


class TimingSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_timing_summary_v0"
    contract_version: str = CONTRACT_VERSION
    rollout_wall_seconds: float = Field(default=0.0, ge=0.0)
    queue_wait_seconds: float = Field(default=0.0, ge=0.0)
    workspace_materialization_seconds: float = Field(default=0.0, ge=0.0)
    docker_setup_seconds: float = Field(default=0.0, ge=0.0)
    dependency_restore_seconds: float = Field(default=0.0, ge=0.0)
    baseline_verifier_seconds: float = Field(default=0.0, ge=0.0)
    agent_loop_seconds: float = Field(default=0.0, ge=0.0)
    model_call_seconds: float = Field(default=0.0, ge=0.0)
    provider_reported_model_call_seconds: float = Field(default=0.0, ge=0.0)
    context_prepare_seconds: float = Field(default=0.0, ge=0.0)
    tool_seconds: float = Field(default=0.0, ge=0.0)
    verifier_seconds: float = Field(default=0.0, ge=0.0)
    final_verifier_seconds: float = Field(default=0.0, ge=0.0)
    reward_compute_seconds: float = Field(default=0.0, ge=0.0)
    artifact_write_seconds: float = Field(default=0.0, ge=0.0)
    cleanup_seconds: float = Field(default=0.0, ge=0.0)
    timing_explained_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    timing_unattributed_seconds: float = Field(default=0.0, ge=0.0)
    timing_bucket_policy: str = TIMING_BUCKET_POLICY
    timing_diagnostics: list[str] = Field(default_factory=list)
    model_call_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    verifier_call_count: int = Field(default=0, ge=0)
    artifact_count: int = Field(default=0, ge=0)
    artifact_bytes_written: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_low_explained_ratio_has_audit_context(self) -> "TimingSummary":
        if self.timing_explained_ratio is None or self.timing_explained_ratio >= MIN_EXPLAINED_RATIO:
            return self
        if self.timing_unattributed_seconds <= 0.0:
            raise ValueError(
                "timing_explained_ratio below 0.95 requires positive timing_unattributed_seconds"
            )
        if not self.timing_diagnostics:
            raise ValueError("timing_explained_ratio below 0.95 requires timing_diagnostics")
        return self


class ResourceSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_resource_summary_v0"
    contract_version: str = CONTRACT_VERSION
    execution_mode: str | None = None
    workspace_backend: str | None = None
    worker_id: str | None = None
    host_id: str | None = None
    snapshot_key: str | None = None
    snapshot_cache_hit: bool | None = None
    snapshot_restore_strategy: str | None = None
    dependency_state_key: str | None = None
    dependency_cache_hit: bool | None = None
    baseline_cache_hit: bool | None = None
    container_reuse_hit: bool | None = None
    docker_image_ref: str | None = None
    docker_image_id: str | None = None
    docker_image_digest: str | None = None
    docker_volume_ids: list[str] = Field(default_factory=list)
    docker_resource_limits_effective: dict[str, Any] = Field(default_factory=dict)
    cpu_limit: str | int | float | None = None
    memory_limit: str | int | float | None = None
    disk_limit: str | int | float | None = None
    inference_route: str | None = None
    inference_backend: str | None = None
    inference_concurrency_slot: str | int | None = None
    dependency_cache_key: str | None = None
    network_policy: str | None = None
    permission_policy_ref: str | None = None
    workspace_path: str | None = None
    run_dir: str | None = None
    concurrency_group: str | None = None
    lease_id: str | None = None
    verifier_worker_pool_id: str | None = None
    verifier_worker_id: str | None = None
    queue_wait_seconds_by_resource: dict[str, float] = Field(default_factory=dict)
    cleanup_status: str | None = None

    def model_post_init(self, __context: Any) -> None:
        for field_name in [
            "execution_mode",
            "workspace_backend",
            "worker_id",
            "host_id",
            "snapshot_key",
            "snapshot_restore_strategy",
            "dependency_state_key",
            "docker_image_ref",
            "docker_image_id",
            "docker_image_digest",
            "inference_route",
            "inference_backend",
            "dependency_cache_key",
            "network_policy",
            "permission_policy_ref",
            "workspace_path",
            "run_dir",
            "concurrency_group",
            "lease_id",
            "verifier_worker_pool_id",
            "verifier_worker_id",
            "cleanup_status",
        ]:
            value = getattr(self, field_name)
            if isinstance(value, str) and value:
                validate_no_absolute_local_path(value, field_name=field_name)
        for index, volume_id in enumerate(self.docker_volume_ids):
            validate_no_absolute_local_path(volume_id, field_name=f"docker_volume_ids[{index}]")
        for resource_name in self.queue_wait_seconds_by_resource:
            validate_no_absolute_local_path(resource_name, field_name="queue_wait_seconds_by_resource")


def build_timing_summary(
    *,
    rollout_wall_seconds: float,
    queue_wait_seconds: float = 0.0,
    workspace_materialization_seconds: float = 0.0,
    docker_setup_seconds: float = 0.0,
    dependency_restore_seconds: float = 0.0,
    baseline_verifier_seconds: float = 0.0,
    agent_loop_seconds: float = 0.0,
    model_call_seconds: float = 0.0,
    provider_reported_model_call_seconds: float = 0.0,
    context_prepare_seconds: float = 0.0,
    tool_seconds: float = 0.0,
    verifier_seconds: float = 0.0,
    final_verifier_seconds: float = 0.0,
    reward_compute_seconds: float = 0.0,
    artifact_write_seconds: float = 0.0,
    cleanup_seconds: float = 0.0,
    model_call_count: int = 0,
    tool_call_count: int = 0,
    verifier_call_count: int = 0,
    artifact_count: int = 0,
    artifact_bytes_written: int = 0,
    timing_bucket_policy: str = TIMING_BUCKET_POLICY,
    timing_diagnostics: list[str] | None = None,
) -> TimingSummary:
    """Build a TimingSummary from mutually exclusive timing buckets.

    ``agent_loop_seconds`` is expected to be residual agent-loop overhead. The
    helper intentionally keeps provider-reported model duration separate from
    the outer wall-clock attribution because provider metadata may be rounded,
    delayed, or measured in a different process.
    """

    bucket_values = {
        "queue_wait_seconds": queue_wait_seconds,
        "workspace_materialization_seconds": workspace_materialization_seconds,
        "docker_setup_seconds": docker_setup_seconds,
        "dependency_restore_seconds": dependency_restore_seconds,
        "baseline_verifier_seconds": baseline_verifier_seconds,
        "agent_loop_seconds": agent_loop_seconds,
        "model_call_seconds": model_call_seconds,
        "context_prepare_seconds": context_prepare_seconds,
        "tool_seconds": tool_seconds,
        "verifier_seconds": verifier_seconds,
        "final_verifier_seconds": final_verifier_seconds,
        "reward_compute_seconds": reward_compute_seconds,
        "artifact_write_seconds": artifact_write_seconds,
        "cleanup_seconds": cleanup_seconds,
    }
    explained_seconds = sum(bucket_values.values())
    ratio = _explained_ratio(rollout_wall_seconds, explained_seconds)
    unattributed_seconds = max(0.0, rollout_wall_seconds - explained_seconds)
    diagnostics = list(timing_diagnostics or [])
    if ratio < MIN_EXPLAINED_RATIO:
        diagnostics.append(
            "timing_unattributed_seconds="
            f"{unattributed_seconds:.6f} left unexplained by exclusive timing buckets"
        )
    if explained_seconds > rollout_wall_seconds and rollout_wall_seconds > 0:
        diagnostics.append(
            "exclusive timing buckets exceed rollout_wall_seconds; "
            "review bucket boundaries for double counting"
        )
    return TimingSummary(
        rollout_wall_seconds=rollout_wall_seconds,
        queue_wait_seconds=queue_wait_seconds,
        workspace_materialization_seconds=workspace_materialization_seconds,
        docker_setup_seconds=docker_setup_seconds,
        dependency_restore_seconds=dependency_restore_seconds,
        baseline_verifier_seconds=baseline_verifier_seconds,
        agent_loop_seconds=agent_loop_seconds,
        model_call_seconds=model_call_seconds,
        provider_reported_model_call_seconds=provider_reported_model_call_seconds,
        context_prepare_seconds=context_prepare_seconds,
        tool_seconds=tool_seconds,
        verifier_seconds=verifier_seconds,
        final_verifier_seconds=final_verifier_seconds,
        reward_compute_seconds=reward_compute_seconds,
        artifact_write_seconds=artifact_write_seconds,
        cleanup_seconds=cleanup_seconds,
        timing_explained_ratio=ratio,
        timing_unattributed_seconds=unattributed_seconds,
        timing_bucket_policy=timing_bucket_policy,
        timing_diagnostics=diagnostics,
        model_call_count=model_call_count,
        tool_call_count=tool_call_count,
        verifier_call_count=verifier_call_count,
        artifact_count=artifact_count,
        artifact_bytes_written=artifact_bytes_written,
    )


def summarize_timing_from_run_dir(
    run_dir: str | Path,
    *,
    rollout_wall_seconds: float | None = None,
) -> TimingSummary:
    """Summarize timing facts from a recorder run directory.

    This helper is intentionally tolerant: missing files yield zero-valued
    buckets, while malformed lines are ignored so a partially written run can
    still produce an audit summary for diagnosis.
    """

    root = Path(run_dir)
    events = _read_jsonl(root / "events.jsonl")
    event_buckets = _event_timing_buckets(events)
    artifact_count, artifact_bytes = _artifact_manifest_stats(root / "artifacts.json")
    inferred_wall_seconds = rollout_wall_seconds
    if inferred_wall_seconds is None:
        inferred_wall_seconds = sum(event_buckets[field] for field in EXCLUSIVE_TIMING_BUCKET_FIELDS)
    return build_timing_summary(
        rollout_wall_seconds=inferred_wall_seconds,
        artifact_count=artifact_count,
        artifact_bytes_written=artifact_bytes,
        **event_buckets,
    )


def _explained_ratio(rollout_wall_seconds: float, explained_seconds: float) -> float:
    if rollout_wall_seconds <= 0:
        return 1.0
    return min(1.0, explained_seconds / rollout_wall_seconds)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _event_timing_buckets(events: list[Mapping[str, Any]]) -> dict[str, float | int]:
    seconds_by_field: dict[str, float] = {field: 0.0 for field in EXCLUSIVE_TIMING_BUCKET_FIELDS}
    model_call_count = 0
    tool_call_count = 0
    verifier_call_count = 0
    for event in events:
        duration_ms = event.get("duration_ms")
        if not isinstance(duration_ms, int | float):
            continue
        duration_seconds = max(0.0, float(duration_ms) / 1000.0)
        event_type = str(event.get("event_type", ""))
        if _matches_any(event_type, ("queue_wait", "queued")):
            seconds_by_field["queue_wait_seconds"] += duration_seconds
        elif _matches_any(event_type, ("workspace_materialization", "materialize_workspace")):
            seconds_by_field["workspace_materialization_seconds"] += duration_seconds
        elif _matches_any(event_type, ("docker_setup", "container_setup")):
            seconds_by_field["docker_setup_seconds"] += duration_seconds
        elif _matches_any(event_type, ("dependency_restore", "dependency_install")):
            seconds_by_field["dependency_restore_seconds"] += duration_seconds
        elif _matches_any(event_type, ("baseline_verifier", "baseline_verify")):
            seconds_by_field["baseline_verifier_seconds"] += duration_seconds
            verifier_call_count += 1
        elif _matches_any(event_type, ("model_call", "llm_gateway")):
            seconds_by_field["model_call_seconds"] += duration_seconds
            model_call_count += 1
        elif _matches_any(event_type, ("context_prepare", "prepared_messages")):
            seconds_by_field["context_prepare_seconds"] += duration_seconds
        elif _matches_any(event_type, ("tool_call", "tool_execution", "workspace_command")):
            seconds_by_field["tool_seconds"] += duration_seconds
            tool_call_count += 1
        elif _matches_any(event_type, ("final_verifier", "final_verify")):
            seconds_by_field["final_verifier_seconds"] += duration_seconds
            verifier_call_count += 1
        elif _matches_any(event_type, ("verifier", "verify")):
            seconds_by_field["verifier_seconds"] += duration_seconds
            verifier_call_count += 1
        elif _matches_any(event_type, ("reward_compute", "reward")):
            seconds_by_field["reward_compute_seconds"] += duration_seconds
        elif _matches_any(event_type, ("artifact_write", "artifact_created")):
            seconds_by_field["artifact_write_seconds"] += duration_seconds
        elif _matches_any(event_type, ("cleanup", "teardown")):
            seconds_by_field["cleanup_seconds"] += duration_seconds
        elif _matches_any(event_type, ("agent_loop", "runtime_overhead")):
            seconds_by_field["agent_loop_seconds"] += duration_seconds
    return {
        **seconds_by_field,
        "model_call_count": model_call_count,
        "tool_call_count": tool_call_count,
        "verifier_call_count": verifier_call_count,
    }


def _artifact_manifest_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0, 0
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(artifacts, list):
        return 0, 0
    count = 0
    size = 0
    for item in artifacts:
        if not isinstance(item, Mapping):
            continue
        count += 1
        size_bytes = item.get("size_bytes")
        if isinstance(size_bytes, int):
            size += max(0, size_bytes)
    return count, size


def _matches_any(value: str, markers: tuple[str, ...]) -> bool:
    return any(marker in value for marker in markers)
