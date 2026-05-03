"""Reward metadata schema。"""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    ACCEPTANCE_POLICY_VERSION,
    CORE_FAILURE_DIAGNOSTICS_SCHEMA_VERSION,
    REWARD_VERSION,
)
from repo_harness.trajectory import ArtifactRef


class RewardMetadata(StrictBaseModel):
    schema_version: str = "repo_harness_reward_metadata_v0"
    reward_version: str = REWARD_VERSION
    final_reward: float = Field(ge=0.0, le=1.0)
    formula: str
    components: dict[str, float] = Field(default_factory=dict)
    sources: dict[str, Any] = Field(default_factory=dict)
    invalid_for_training: bool = False
    invalid_reason: str | None = None
    acceptance_policy_version: str = ACCEPTANCE_POLICY_VERSION
    reward_clip_range: tuple[float, float] = (0.0, 1.0)

    @model_validator(mode="after")
    def invalid_samples_need_reason(self) -> "RewardMetadata":
        if self.invalid_for_training and not self.invalid_reason:
            raise ValueError("invalid_for_training=true 时必须提供 invalid_reason。")
        return self


class CoreFailureDiagnostics(StrictBaseModel):
    schema_version: str = CORE_FAILURE_DIAGNOSTICS_SCHEMA_VERSION
    diagnostic_id: str
    run_id: str
    failure_category: str
    failure_type: str
    source_component: str
    blocks_training: bool
    diagnostic_only: bool = True
    patch_size: int = Field(default=0, ge=0)
    files_changed: list[str] = Field(default_factory=list)
    tool_call_count: int = Field(default=0, ge=0)
    test_run_count: int = Field(default=0, ge=0)
    invalid_tool_call_count: int = Field(default=0, ge=0)
    permission_violation_count: int = Field(default=0, ge=0)
    regression_detected: bool = False
    environment_failure_category: str = "none"
    environment_unstable: bool = False
    docker_backend_failure: bool = False
    container_timeout: bool = False
    source_materialization_failed: bool = False
    dependency_setup_failed: bool = False
    parser_low_confidence: bool = False
    public_tests_pass_hidden_tests_fail: bool = False
    unfinished_trajectory: bool = False
    no_patch_generated: bool = False
    no_progress: bool = False
    repeated_tool_call_loop: bool = False
    context_limit_failure: bool = False
    provider_transient: bool = False
    deterministic_verifier_failure: bool = False
    reward_hacking_suspected: bool = False
    model_visible_summary: str | None = None
    hidden_details_ref: ArtifactRef | None = None
    reward_metadata_visible_to_model: bool = False
    run_outcome_visible_to_model: bool = False
    hidden_failure_details_visible_to_model: bool = False

    @model_validator(mode="after")
    def hidden_reward_facts_are_not_model_visible(self) -> "CoreFailureDiagnostics":
        if self.reward_metadata_visible_to_model:
            raise ValueError("reward metadata 不能进入模型可见诊断。")
        if self.run_outcome_visible_to_model:
            raise ValueError("run outcome 不能进入模型可见诊断。")
        if self.hidden_failure_details_visible_to_model:
            raise ValueError("hidden failure diagnostics 不能进入模型可见内容。")
        if self.blocks_training and not self.diagnostic_only:
            raise ValueError("阻断训练的 core failure diagnostics 必须是 diagnostic_only。")
        return self
