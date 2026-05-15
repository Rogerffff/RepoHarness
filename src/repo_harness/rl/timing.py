"""训练 episode 的 timing 和 resource schema。"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel

from .visibility import CONTRACT_VERSION, validate_no_absolute_local_path


class TimingSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_timing_summary_v0"
    contract_version: str = CONTRACT_VERSION
    rollout_wall_seconds: float = Field(default=0.0, ge=0.0)
    queue_wait_seconds: float = Field(default=0.0, ge=0.0)
    workspace_materialization_seconds: float = Field(default=0.0, ge=0.0)
    docker_setup_seconds: float = Field(default=0.0, ge=0.0)
    baseline_verifier_seconds: float = Field(default=0.0, ge=0.0)
    agent_loop_seconds: float = Field(default=0.0, ge=0.0)
    model_call_seconds: float = Field(default=0.0, ge=0.0)
    context_prepare_seconds: float = Field(default=0.0, ge=0.0)
    tool_seconds: float = Field(default=0.0, ge=0.0)
    verifier_seconds: float = Field(default=0.0, ge=0.0)
    final_verifier_seconds: float = Field(default=0.0, ge=0.0)
    reward_compute_seconds: float = Field(default=0.0, ge=0.0)
    artifact_write_seconds: float = Field(default=0.0, ge=0.0)
    cleanup_seconds: float = Field(default=0.0, ge=0.0)
    timing_explained_ratio: float | None = Field(default=None, ge=0.0)
    model_call_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    verifier_call_count: int = Field(default=0, ge=0)
    artifact_count: int = Field(default=0, ge=0)
    artifact_bytes_written: int = Field(default=0, ge=0)


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
    docker_image_id: str | None = None
    docker_image_digest: str | None = None
    docker_volume_ids: list[str] = Field(default_factory=list)
    docker_resource_limits_effective: dict[str, Any] = Field(default_factory=dict)
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
        for field_name in ["workspace_path", "run_dir"]:
            value = getattr(self, field_name)
            if value:
                validate_no_absolute_local_path(value, field_name=field_name)
