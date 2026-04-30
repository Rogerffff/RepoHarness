"""评测质量门控和运行时 verifier plan schema。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import ACCEPTANCE_POLICY_VERSION
from repo_harness.tasks import VerifierConfig
from repo_harness.trajectory import ArtifactRef
from repo_harness.workspace import DependencyState


class BaselineResult(StrictBaseModel):
    schema_version: str = "repo_harness_baseline_result_v0"
    task_id: str
    status: Literal["valid", "invalid", "flaky"]
    setup_exit_code: int | None = None
    baseline_exit_code: int | None = None
    baseline_verifier_result_ref: ArtifactRef | None = None
    setup_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    baseline_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    parser_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    baseline_rerun_count: int = Field(default=0, ge=0)
    flaky_policy_version: str = "repo_harness_flaky_policy_v0"
    initial_fail_to_pass_tests: list[str] = Field(default_factory=list)
    initial_pass_to_pass_tests: list[str] = Field(default_factory=list)
    flaky_tests: list[str] = Field(default_factory=list)
    dependency_error: str | None = None
    dependency_state: DependencyState = Field(default_factory=DependencyState)
    setup_workspace_snapshot: str | None = None
    agent_run_start_policy: dict[str, str | bool] = Field(default_factory=dict)

    @property
    def can_enter_agent_run(self) -> bool:
        return self.status == "valid"


class ResolvedVerifierPlan(StrictBaseModel):
    schema_version: str = "repo_harness_resolved_verifier_plan_v0"
    verifier_config: VerifierConfig
    initial_fail_to_pass_tests: list[str] = Field(default_factory=list)
    initial_pass_to_pass_tests: list[str] = Field(default_factory=list)
    flaky_tests: list[str] = Field(default_factory=list)
    parser_confidence: float = Field(ge=0.0, le=1.0)
    acceptance_policy_version: str = ACCEPTANCE_POLICY_VERSION
    resolved_verifier_plan_id: str
