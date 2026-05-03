"""评测质量门控和运行时 verifier plan schema。"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    ACCEPTANCE_POLICY_VERSION,
    EXPERIMENT_RESUME_MANIFEST_SCHEMA_VERSION,
    EXPERIMENT_SCHEMA_VERSION,
    RUN_CHECKPOINT_SCHEMA_VERSION,
)
from repo_harness.config.schemas import DockerRuntimeConfig, SweBenchLikeConfig
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
    execution_mode: Literal["local_process", "docker"] = "local_process"
    docker_backend: DockerRuntimeConfig = Field(default_factory=DockerRuntimeConfig)
    swebench_like: SweBenchLikeConfig = Field(default_factory=SweBenchLikeConfig)
    test_feedback_policy: Literal[
        "disabled", "public_only", "structured_public_feedback", "oracle_hidden_feedback"
    ] | None = None
    feedback_tests_passed_policy: Literal[
        "stop_immediately", "require_model_final", "continue"
    ] | None = None
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
        if self.model_provider not in {"replay", "fake", "mock", "deepseek"}:
            raise ValueError("Stage 11 ExperimentConfig 只支持 replay、fake、mock 或 deepseek provider；openai 只允许作为 DeepSeek fallback smoke run。")
        if self.scaffold_id not in {
            "simple_react",
            "patch_focused_react",
            "single_shot_patch",
            "planner_coder_verifier",
        }:
            raise ValueError(
                "Stage 09 ExperimentConfig 只支持 simple_react、patch_focused_react、"
                "single_shot_patch 或 planner_coder_verifier scaffold。"
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
            object.__setattr__(self, "generate_preference_export", True)
        if self.swebench_like.max_workers is None:
            object.__setattr__(
                self,
                "swebench_like",
                self.swebench_like.model_copy(
                    update={
                        "max_workers": 1,
                        "effective_max_workers": 1,
                        "max_workers_resolution": "experiment_runner_serial_default",
                    }
                ),
            )
        elif self.swebench_like.max_workers != 1:
            object.__setattr__(
                self,
                "swebench_like",
                self.swebench_like.model_copy(
                    update={
                        "max_workers": 1,
                        "effective_max_workers": 1,
                        "max_workers_resolution": "experiment_runner_v3_stage1_serial_cap",
                    }
                ),
            )
        return self


class RunCheckpoint(StrictBaseModel):
    schema_version: str = RUN_CHECKPOINT_SCHEMA_VERSION
    checkpoint_id: str | None = None
    run_id: str
    checkpoint_type: Literal[
        "created",
        "baseline_completed",
        "agent_loop_started",
        "agent_loop_completed",
        "final_patch_frozen",
        "final_verifier_completed",
        "export_completed",
        "interrupted",
    ] = "created"
    created_at: str | None = None
    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
        "skipped",
        "interrupted",
        "crashed",
    ]
    run_config_facts_ref: ArtifactRef | None = None
    event_offset: int = Field(default=0, ge=0)
    transcript_offset: int = Field(default=0, ge=0)
    artifact_manifest_ref: ArtifactRef | None = None
    workspace_snapshot_ref: ArtifactRef | None = None
    final_patch_ref: ArtifactRef | None = None
    run_metadata_ref: ArtifactRef | None = None
    interrupted_or_crash_facts_ref: ArtifactRef | None = None
    resume_eligibility: Literal[
        "eligible",
        "not_needed",
        "not_recoverable",
        "not_evaluated",
    ] = "not_evaluated"

    @model_validator(mode="after")
    def validate_final_metadata_timing(self) -> "RunCheckpoint":
        if self.run_metadata_ref is not None and self.status not in {"completed", "failed"}:
            raise ValueError("run_metadata_ref 只能在最终 metadata 已写入后出现。")
        if self.status in {"interrupted", "crashed"} and self.run_metadata_ref is not None:
            raise ValueError("interrupted / crashed checkpoint 不能要求最终 run_metadata.json。")
        return self


class ExperimentResumeRunEntry(StrictBaseModel):
    schema_version: str = "repo_harness_experiment_resume_run_entry_v3_v0"
    run_id: str
    task_id: str
    rollout_index: int = Field(ge=0)
    model_alias: str
    scaffold_id: str
    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
        "skipped",
        "interrupted",
        "crashed",
    ]
    attempt: int = Field(default=1, ge=1)
    run_dir: str
    last_checkpoint_ref: ArtifactRef | None = None
    failure_category: Literal[
        "none",
        "provider_transient",
        "docker_infrastructure",
        "environment_setup",
        "deterministic_verifier",
        "task_quality",
        "permission",
        "tool_protocol",
        "context_limit",
        "interrupted",
        "unknown",
    ] = "none"
    failure_type: str | None = None
    retryable: bool = False
    resume_action: Literal[
        "none",
        "skip_completed",
        "continue_pending",
        "continue_interrupted_as_new_run",
        "retry_failed",
        "not_recoverable",
        "structured_skip",
    ] = "none"
    parent_run_id: str | None = None
    continuation_reason: str | None = None
    resume_from: str | None = None


class ExperimentResumeManifest(StrictBaseModel):
    schema_version: str = EXPERIMENT_RESUME_MANIFEST_SCHEMA_VERSION
    experiment_id: str
    config_hash: str | None = None
    resume_policy_version: str = "repo_harness_resume_policy_v3_v0"
    retry_policy: str = "pending_and_interrupted_only_v0"
    max_parallel_runs: int = Field(default=1, ge=1)
    generated_at: str | None = None
    updated_at: str | None = None
    docker_backend_facts_ref: ArtifactRef | None = None
    runs: list[ExperimentResumeRunEntry] = Field(default_factory=list)
    state_distribution: dict[str, int] = Field(default_factory=dict)
    failure_distribution: dict[str, int] = Field(default_factory=dict)
    completed_run_refs: list[ArtifactRef] = Field(default_factory=list)
    pending_run_specs: list[dict[str, Any]] = Field(default_factory=list)
    interrupted_run_refs: list[ArtifactRef] = Field(default_factory=list)
    run_checkpoints: list[RunCheckpoint] = Field(default_factory=list)
    completed_run_ids: list[str] = Field(default_factory=list)
    pending_run_ids: list[str] = Field(default_factory=list)
    interrupted_run_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def listed_ids_match_checkpoints(self) -> "ExperimentResumeManifest":
        by_status = {
            status: {
                checkpoint.run_id
                for checkpoint in self.run_checkpoints
                if checkpoint.status == status
            }
            for status in {"completed", "pending", "interrupted"}
        }
        completed = by_status["completed"]
        pending = by_status["pending"]
        interrupted = by_status["interrupted"]
        if set(self.completed_run_ids) != completed:
            raise ValueError("completed_run_ids 必须和 completed checkpoints 一致。")
        if set(self.pending_run_ids) != pending:
            raise ValueError("pending_run_ids 必须和 pending checkpoints 一致。")
        if set(self.interrupted_run_ids) != interrupted:
            raise ValueError("interrupted_run_ids 必须和 interrupted checkpoints 一致。")
        return self


class ExperimentMinimums(StrictBaseModel):
    schema_version: str = "repo_harness_experiment_minimums_v2_v0"
    min_total_runs: int = Field(default=1, ge=0)
    min_task_count: int = Field(default=0, ge=0)
    min_recorded_runs: int = Field(default=1, ge=0)
    min_agent_loop_runs: int = Field(default=0, ge=0)
    min_formal_final_verifier_runs: int = Field(default=0, ge=0)
    min_success_count: int = Field(default=0, ge=0)
    min_structured_skipped_runs: int = Field(default=0, ge=0)
    require_experiment_manifest: bool = True
    require_aggregate_metrics: bool = True
    require_failure_records: bool = False
    require_no_all_skipped_success: bool = False
    require_export_audit_clean: bool = False
