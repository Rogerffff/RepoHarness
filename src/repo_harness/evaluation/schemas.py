"""评测质量门控和运行时 verifier plan schema。"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import ACCEPTANCE_POLICY_VERSION, EXPERIMENT_SCHEMA_VERSION
from repo_harness.export.schemas import CompareScope
from repo_harness.tasks import VerifierConfig
from repo_harness.trajectory import ArtifactRef
from repo_harness.workspace import DependencyState


class TestFeedbackPolicy(str, Enum):
    """模型可见测试反馈策略。"""

    disabled = "disabled"
    public_only = "public_only"
    structured_public_feedback = "structured_public_feedback"
    oracle_hidden_feedback = "oracle_hidden_feedback"


class FeedbackTestsPassedPolicy(str, Enum):
    """feedback verifier accepted 后 Agent Loop 的可配置停止策略。"""

    stop_immediately = "stop_immediately"
    require_model_final = "require_model_final"
    continue_ = "continue"


ResolvedFeedbackTestsPassedPolicy = Literal[
    "stop_immediately", "require_model_final", "continue", "not_applicable"
]


class FeedbackPolicyConfig(StrictBaseModel):
    schema_version: str = "repo_harness_feedback_policy_config_v2_v0"
    test_feedback_policy: TestFeedbackPolicy
    feedback_tests_passed_policy: FeedbackTestsPassedPolicy


class ResolvedFeedbackPolicyFacts(StrictBaseModel):
    schema_version: str = "repo_harness_resolved_feedback_policy_facts_v2_v0"
    scaffold_default_test_feedback_policy: TestFeedbackPolicy
    scaffold_default_feedback_tests_passed_policy: FeedbackTestsPassedPolicy
    runtime_test_feedback_policy: TestFeedbackPolicy | None = None
    runtime_feedback_tests_passed_policy: FeedbackTestsPassedPolicy | None = None
    resolved_test_feedback_policy: TestFeedbackPolicy
    resolved_feedback_tests_passed_policy: ResolvedFeedbackTestsPassedPolicy
    hidden_feedback_visible_to_model: bool
    swe_bench_like_final_only: bool = False

    @model_validator(mode="after")
    def validate_feedback_visibility(self) -> "ResolvedFeedbackPolicyFacts":
        if (
            self.resolved_test_feedback_policy == TestFeedbackPolicy.oracle_hidden_feedback
            and self.swe_bench_like_final_only
        ):
            raise ValueError("SWE-Bench-like final-only task 不能使用 oracle_hidden_feedback。")
        if self.resolved_test_feedback_policy == TestFeedbackPolicy.disabled:
            if self.resolved_feedback_tests_passed_policy != "not_applicable":
                raise ValueError("disabled 测试反馈策略必须解析为 not_applicable。")
            if self.hidden_feedback_visible_to_model:
                raise ValueError("disabled 测试反馈策略不能向模型暴露隐藏反馈。")
        if self.hidden_feedback_visible_to_model and (
            self.resolved_test_feedback_policy != TestFeedbackPolicy.oracle_hidden_feedback
        ):
            raise ValueError("只有 oracle_hidden_feedback 可以向模型暴露隐藏反馈。")
        return self


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


class ExperimentRunSpec(StrictBaseModel):
    schema_version: str = "repo_harness_experiment_run_spec_v2_v0"
    task_path: str
    rollout_index: int = Field(ge=0)
    model_alias: str
    scaffold_id: str
    run_id_suffix: str | None = None


class ExperimentConfig(StrictBaseModel):
    schema_version: str = EXPERIMENT_SCHEMA_VERSION
    experiment_id: str
    tasks: list[str] = Field(min_length=1)
    rollout_count: int = Field(gt=0)
    model_provider: str = "replay"
    model_alias: str = "replay"
    model_id: str = "replay-script-v0"
    replay_script_path: str | None = None
    scaffold_id: str = "simple_react"
    permission_mode: Literal["plan", "ask", "auto", "deny"] = "auto"
    execution_mode: Literal["local_process"] = "local_process"
    output_dir: str = "runs"
    run_id_template: str = "{experiment_id}_{task_id}_{model_alias}_{scaffold_id}_r{rollout_index:03d}"
    compare_scope: CompareScope = Field(default_factory=CompareScope)
    generate_aggregate_report: bool = True
    auto_export_preference: bool = False
    max_turns: int = Field(default=8, gt=0)
    max_tool_calls: int = Field(default=20, ge=0)
    max_test_runs: int = Field(default=4, ge=0)
    task_timeout_sec: int = Field(default=120, gt=0)
    command_timeout_sec: int = Field(default=60, gt=0)
    max_output_tokens: int = Field(default=4096, gt=0)
    temperature: float = Field(default=0.0, ge=0.0)
    seed: int | None = 42
    keep_workspace: bool = True
    fail_on_invalid_task: bool = False
    generate_preference_export: bool = False

    @model_validator(mode="after")
    def validate_stage06_scope(self) -> "ExperimentConfig":
        if self.model_provider not in {"replay", "fake"}:
            raise ValueError("Stage 07 ExperimentConfig 只支持 replay 或 fake provider。")
        if self.scaffold_id not in {"simple_react", "single_shot_patch", "planner_coder_verifier"}:
            raise ValueError(
                "Stage 09 ExperimentConfig 只支持 simple_react、single_shot_patch "
                "或 planner_coder_verifier scaffold。"
            )
        if self.permission_mode == "ask":
            raise ValueError("Stage 07 ExperimentConfig 不能使用 permission_mode=ask。")
        required_tokens = ["{task_id}", "{model_alias}", "{scaffold_id}", "{rollout_index"]
        missing = [token for token in required_tokens if token not in self.run_id_template]
        if missing:
            raise ValueError(
                "Stage 07 run_id_template 必须包含 task_id、model_alias、scaffold_id 和 rollout_index。"
            )
        if self.auto_export_preference:
            self.generate_preference_export = True
        return self


class ExperimentMinimums(StrictBaseModel):
    schema_version: str = "repo_harness_experiment_minimums_v2_v0"
    min_total_runs: int = Field(default=1, ge=0)
    min_recorded_runs: int = Field(default=1, ge=0)
    require_experiment_manifest: bool = True
    require_aggregate_metrics: bool = True
    require_failure_records: bool = False
    require_no_all_skipped_success: bool = False
