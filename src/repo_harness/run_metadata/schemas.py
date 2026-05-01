"""第二版 run metadata 和不可变配置事实 schema。"""

from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath
from typing import Any, ClassVar, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    ENVIRONMENT_FINGERPRINT_VERSION,
    RUN_METADATA_SCHEMA_VERSION,
    TOOL_SCHEMA_SNAPSHOT_VERSION,
)
from repo_harness.trajectory import ArtifactRef

SHA256_PATTERN = r"^[0-9a-f]{64}$"


class RunMetadataSource(str, Enum):
    """run metadata 的读取来源。"""

    v2 = "v2"
    legacy_inferred = "legacy_inferred"
    legacy_missing = "legacy_missing"
    missing = "missing"


class FailureCategory(str, Enum):
    """失败所属的系统边界。"""

    model_failure = "model_failure"
    environment_failure = "environment_failure"
    provider_failure = "provider_failure"
    tool_protocol_failure = "tool_protocol_failure"
    permission_failure = "permission_failure"
    task_quality_failure = "task_quality_failure"
    unknown_failure = "unknown_failure"


class FailureType(str, Enum):
    """第二版统一失败类型。"""

    malformed_tool_call = "malformed_tool_call"
    tool_timeout = "tool_timeout"
    tool_schema_invalid = "tool_schema_invalid"
    permission_denied_unrecovered = "permission_denied_unrecovered"
    no_patch_generated = "no_patch_generated"
    provider_auth_error = "provider_auth_error"
    provider_rate_limit = "provider_rate_limit"
    provider_timeout = "provider_timeout"
    context_limit = "context_limit"
    environment_setup_failed = "environment_setup_failed"
    baseline_quality_failed = "baseline_quality_failed"
    final_verifier_failed = "final_verifier_failed"
    reward_hacking_suspected = "reward_hacking_suspected"
    unknown_failure = "unknown_failure"


class _RelativeFactRef(StrictBaseModel):
    """run directory 根目录事实文件引用，不是普通 artifact 引用。"""

    schema_version: str = "repo_harness_fact_file_ref_v2_v0"
    relative_path: str
    sha256: str = Field(pattern=SHA256_PATTERN)

    expected_relative_path: ClassVar[str | None] = None

    @model_validator(mode="after")
    def validate_relative_path(self) -> "_RelativeFactRef":
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("事实文件引用必须使用 run directory 内的安全相对路径。")
        if self.expected_relative_path and self.relative_path != self.expected_relative_path:
            raise ValueError(f"事实文件引用必须指向 {self.expected_relative_path}。")
        return self


class RunConfigFactsRef(_RelativeFactRef):
    """Agent Loop 前写入的不可变配置事实引用。"""

    schema_version: Literal["repo_harness_run_config_facts_ref_v2_v0"] = (
        "repo_harness_run_config_facts_ref_v2_v0"
    )
    kind: Literal["run_config_facts"] = "run_config_facts"
    relative_path: str = "run_config_facts.json"
    expected_relative_path: ClassVar[str | None] = "run_config_facts.json"


class RunMetadataRef(_RelativeFactRef):
    """run 完成后写入的最终运行事实引用。"""

    schema_version: Literal["repo_harness_run_metadata_ref_v2_v0"] = (
        "repo_harness_run_metadata_ref_v2_v0"
    )
    kind: Literal["run_metadata"] = "run_metadata"
    relative_path: str = "run_metadata.json"
    expected_relative_path: ClassVar[str | None] = "run_metadata.json"


class ExecutionModeFacts(StrictBaseModel):
    schema_version: str = "repo_harness_execution_mode_facts_v2_v0"
    requested_execution_mode: Literal["local_process", "docker"]
    resolved_execution_mode: Literal["local_process", "docker"]
    execution_mode_status: Literal["active", "rejected", "not_available"]
    reason: str | None = None


class WorkspaceBackendFacts(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_backend_facts_v2_v0"
    backend: Literal["local_process", "docker"]
    backend_version: str
    execution_mode: ExecutionModeFacts
    network_policy: str
    isolation_claims: list[str] = Field(default_factory=list)


class SourceCheckoutFacts(StrictBaseModel):
    schema_version: str = "repo_harness_source_checkout_facts_v2_v0"
    source_kind: str
    base_commit: str | None = None
    synthetic_base_id: str | None = None
    source_archive_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    source_tree_hash: str
    checkout_path_status: Literal["recorded", "redacted", "unknown"] = "unknown"
    decontamination_status: str | None = None
    decontamination_metadata_ref: ArtifactRef | None = None

    @model_validator(mode="after")
    def require_base_identity(self) -> "SourceCheckoutFacts":
        if not self.base_commit and not self.synthetic_base_id:
            raise ValueError("SourceCheckoutFacts 必须记录 base_commit 或 synthetic_base_id。")
        return self


class WorkspaceExecutionFacts(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_execution_facts_v2_v0"
    workspace_backend: WorkspaceBackendFacts
    source_checkout: SourceCheckoutFacts
    python_version: str
    operating_system: str
    command_timeout_sec: int = Field(gt=0)
    shell_command_policy_version: str
    environment_spec_hash: str = Field(pattern=SHA256_PATTERN)
    dependency_state_ref: ArtifactRef | None = None
    setup_artifact_hash: str | Literal["none", "unknown", "missing"] = "none"


class EnvironmentFingerprint(StrictBaseModel):
    schema_version: str = ENVIRONMENT_FINGERPRINT_VERSION
    fingerprint_id: str
    python_version: str
    platform: str
    package_manager: str | None = None
    package_manager_version: str | None = None
    lockfile_hashes: dict[str, str] = Field(default_factory=dict)
    environment_spec_hash: str = Field(pattern=SHA256_PATTERN)
    workspace_execution: WorkspaceExecutionFacts


class ToolSchemaEntry(StrictBaseModel):
    schema_version: str = "repo_harness_tool_schema_entry_v2_v0"
    name: str
    tool_version: str
    model_visible_description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tool_result_format_version: str
    read_only: bool
    destructive: bool
    permission_required: bool
    max_output_chars: int = Field(gt=0)


class ToolSchemaSnapshot(StrictBaseModel):
    schema_version: str = TOOL_SCHEMA_SNAPSHOT_VERSION
    snapshot_id: str
    tool_order: list[str] = Field(min_length=1)
    tool_parser_version: str
    tool_result_format_version: str
    tools: list[ToolSchemaEntry] = Field(min_length=1)
    snapshot_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_tool_order(self) -> "ToolSchemaSnapshot":
        tool_names = [tool.name for tool in self.tools]
        if self.tool_order != tool_names:
            raise ValueError("tool_order 必须和 tools 的稳定顺序一致。")
        return self


class ToolProtocolFacts(StrictBaseModel):
    schema_version: str = "repo_harness_tool_protocol_facts_v2_v0"
    tool_schema_snapshot_ref: ArtifactRef
    tool_schema_snapshot_sha256: str = Field(pattern=SHA256_PATTERN)
    tool_order: list[str] = Field(min_length=1)
    tool_parser_version: str
    tool_result_format_version: str
    tool_policy_version: str


class FailureDiagnostics(StrictBaseModel):
    schema_version: str = "repo_harness_failure_diagnostics_v2_v0"
    failure_category: FailureCategory
    failure_type: FailureType
    recoverable: bool
    source_component: str
    message: str
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def unknown(
        cls,
        *,
        source_component: str,
        message: str = "未分类失败。",
    ) -> "FailureDiagnostics":
        return cls(
            failure_category=FailureCategory.unknown_failure,
            failure_type=FailureType.unknown_failure,
            recoverable=False,
            source_component=source_component,
            message=message,
        )


class RunConfigFacts(StrictBaseModel):
    schema_version: str = "repo_harness_run_config_facts_v2_v0"
    run_metadata_schema_version: str = RUN_METADATA_SCHEMA_VERSION
    run_id: str
    task_id: str
    task_version: str
    dataset_name: str
    source_kind: str
    base_commit: str | None = None
    source_archive_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    provider: str
    model_id: str
    temperature: float = Field(ge=0.0)
    seed: int | None = None
    max_output_tokens: int = Field(gt=0)
    retry_policy: str
    credential_policy: str
    provider_request_logging_policy: str
    scaffold_id: str
    scaffold_version: str
    allowed_tools_policy: str
    phase_policy: str
    stop_policy: str
    test_feedback_policy: Literal[
        "disabled", "public_only", "structured_public_feedback", "oracle_hidden_feedback"
    ]
    feedback_tests_passed_policy: Literal[
        "stop_immediately", "require_model_final", "continue", "not_applicable"
    ]
    hidden_feedback_visible_to_model: bool
    swe_bench_like_final_only: bool = False
    tool_protocol: ToolProtocolFacts
    context_builder_version: str
    context_policy_version: str
    prompt_template_version: str
    token_estimator_version: str
    permission_mode: str
    permission_policy_version: str
    network_policy: str
    shell_command_policy_version: str
    verifier_name: str
    verifier_version: str
    final_verifier_mode: str
    reward_formula_version: str
    outcome_policy_version: str
    max_turns: int = Field(gt=0)
    max_tool_calls: int = Field(ge=0)
    max_test_runs: int = Field(ge=0)
    task_timeout_sec: int = Field(gt=0)
    command_timeout_sec: int = Field(gt=0)
    context_budget_tokens: int = Field(gt=0)
    artifact_budget_bytes: int | None = Field(default=None, gt=0)
    environment_fingerprint: EnvironmentFingerprint

    @model_validator(mode="after")
    def validate_feedback_policy_facts(self) -> "RunConfigFacts":
        if self.test_feedback_policy == "disabled":
            if self.feedback_tests_passed_policy != "not_applicable":
                raise ValueError(
                    "test_feedback_policy=disabled 时，feedback_tests_passed_policy 必须解析为 not_applicable。"
                )
            if self.hidden_feedback_visible_to_model:
                raise ValueError("disabled 测试反馈策略不能向模型暴露隐藏反馈。")
        elif self.feedback_tests_passed_policy == "not_applicable":
            raise ValueError("not_applicable 只能用于 disabled 测试反馈策略的解析后事实。")
        if self.test_feedback_policy == "oracle_hidden_feedback" and self.swe_bench_like_final_only:
            raise ValueError("SWE-Bench-like final-only task 不能使用 oracle_hidden_feedback。")
        if self.hidden_feedback_visible_to_model and self.test_feedback_policy != "oracle_hidden_feedback":
            raise ValueError("只有 oracle_hidden_feedback 可以向模型暴露隐藏反馈。")
        return self


class ExportReadinessFacts(StrictBaseModel):
    schema_version: str = "repo_harness_export_readiness_facts_v2_v0"
    has_final_patch: bool
    has_formal_final_verifier: bool
    has_reward_metadata: bool
    clean_transcript: bool
    clean_artifact_manifest: bool
    training_export_ready: bool
    blocking_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_blockers(self) -> "ExportReadinessFacts":
        if not self.training_export_ready and not self.blocking_reasons:
            raise ValueError("training_export_ready=false 时必须记录 blocking_reasons。")
        return self


class RunMetadata(StrictBaseModel):
    schema_version: str = RUN_METADATA_SCHEMA_VERSION
    metadata_source: RunMetadataSource = RunMetadataSource.v2
    run_id: str
    task_id: str | None = None
    run_config_facts_ref: RunConfigFactsRef
    run_status: Literal["completed", "skipped", "failed", "interrupted"]
    agent_stop_reason: str | None = None
    run_outcome: str
    reward_status: Literal["present", "missing", "not_applicable", "invalid"]
    final_verifier_status: Literal["accepted", "failed", "timeout", "error", "skipped"]
    final_verifier_mode: str | None = None
    metrics_summary: dict[str, Any] = Field(default_factory=dict)
    tool_call_summary: dict[str, Any] = Field(default_factory=dict)
    model_call_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_manifest_status: Literal["ok", "missing", "invalid"]
    failure_diagnostics: list[FailureDiagnostics] = Field(default_factory=list)
    export_readiness: ExportReadinessFacts
