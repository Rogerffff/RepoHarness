"""第二版 run metadata 和不可变配置事实 schema。"""

from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath
from typing import Any, ClassVar, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    ENVIRONMENT_FINGERPRINT_VERSION,
    POLICY_SNAPSHOT_SCHEMA_VERSION,
    RUN_METADATA_SCHEMA_VERSION,
    TOOL_CONTRACT_SNAPSHOT_SCHEMA_VERSION,
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
    budget_or_timeout_failure = "budget_or_timeout_failure"
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
    task_timeout_before_provider_call = "task_timeout_before_provider_call"
    context_limit = "context_limit"
    auto_compact_failed_preflight = "auto_compact_failed_preflight"
    reactive_compact_failed = "reactive_compact_failed"
    context_limit_after_reactive_compact = "context_limit_after_reactive_compact"
    environment_setup_failed = "environment_setup_failed"
    baseline_quality_failed = "baseline_quality_failed"
    final_verifier_failed = "final_verifier_failed"
    final_verifier_not_executed = "final_verifier_not_executed"
    final_verifier_environment_error = "final_verifier_environment_error"
    task_timeout_before_final_verifier = "task_timeout_before_final_verifier"
    budget_exhausted_empty_patch = "budget_exhausted_empty_patch"
    search_backend_false_fact_suspected = "search_backend_false_fact_suspected"
    no_nudge_empty_patch = "no_nudge_empty_patch"
    nudge_ignored_empty_patch = "nudge_ignored_empty_patch"
    compaction_applied_but_insufficient_context_limit = (
        "compaction_applied_but_insufficient_context_limit"
    )
    final_only_no_intermediate_feedback = "final_only_no_intermediate_feedback"
    model_wrong_fix_after_late_edit = "model_wrong_fix_after_late_edit"
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
    source_type: str | None = None
    remote_url: str | None = None
    mirror_source: str | None = None
    base_commit: str | None = None
    resolved_commit: str | None = None
    synthetic_base_id: str | None = None
    source_archive_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    mirror_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    source_tree_hash: str
    checkout_path_status: Literal["recorded", "redacted", "unknown"] = "unknown"
    decontamination_status: str | None = None
    decontamination_metadata_ref: ArtifactRef | None = None
    current_commit: str | None = None
    working_tree_clean: bool | None = None
    dirty_snapshot_allowed: bool = False
    remotes_stripped: bool | None = None
    branches_stripped: bool | None = None
    tags_stripped: bool | None = None
    materialization_policy_version: str = "repo_harness_source_materialization_v0"
    materialization_command_facts: dict[str, Any] = Field(default_factory=dict)

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
    tool_order: list[str] = Field(default_factory=list)
    tool_parser_version: str
    tool_result_format_version: str
    tools: list[ToolSchemaEntry] = Field(default_factory=list)
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
    tool_order: list[str] = Field(default_factory=list)
    tool_parser_version: str
    tool_result_format_version: str
    tool_policy_version: str
    require_read_before_edit: bool = False
    tool_policy_config: dict[str, Any] = Field(default_factory=dict)


class PermissionPolicySnapshot(StrictBaseModel):
    schema_version: str = POLICY_SNAPSHOT_SCHEMA_VERSION
    snapshot_kind: Literal["permission_policy"] = "permission_policy"
    policy_version: str
    snapshot_id: str
    policy_sha256: str = Field(pattern=SHA256_PATTERN)
    mode: str
    rules_ref: ArtifactRef | None = None


class HookPolicySnapshot(StrictBaseModel):
    schema_version: str = POLICY_SNAPSHOT_SCHEMA_VERSION
    snapshot_kind: Literal["hook_policy"] = "hook_policy"
    policy_version: str = "repo_harness_hook_policy_v3_v0"
    snapshot_id: str
    hooks_enabled: bool = False
    hook_generated_observation_model_visible: bool = False
    disabled_reason: str | None = "v3_core_hooks_disabled"

    @model_validator(mode="after")
    def hook_observations_are_not_visible_when_disabled(self) -> "HookPolicySnapshot":
        if not self.hooks_enabled and self.hook_generated_observation_model_visible:
            raise ValueError("hooks disabled 时不能有 hook-generated model-visible observation。")
        return self


class MCPPolicySnapshot(StrictBaseModel):
    schema_version: str = POLICY_SNAPSHOT_SCHEMA_VERSION
    snapshot_kind: Literal["mcp_policy"] = "mcp_policy"
    policy_version: str = "repo_harness_mcp_policy_v3_v0"
    snapshot_id: str
    mcp_enabled: bool = False
    external_tool_surface_frozen: bool = True
    dynamic_tool_discovery_allowed: bool = False

    @model_validator(mode="after")
    def dynamic_mcp_tools_are_not_allowed(self) -> "MCPPolicySnapshot":
        if self.dynamic_tool_discovery_allowed:
            raise ValueError("V3 核心不允许 dynamic MCP tool discovery。")
        return self


class ToolContractSnapshot(StrictBaseModel):
    schema_version: str = TOOL_CONTRACT_SNAPSHOT_SCHEMA_VERSION
    snapshot_id: str
    tool_contract_version: str = "repo_harness_tool_contract_v3_v0"
    tool_schema_refs: list[ArtifactRef] = Field(default_factory=list)
    tool_schema_sha256: str = Field(pattern=SHA256_PATTERN)
    tool_result_pairing_policy: str = "all_tool_calls_receive_tool_results"
    large_output_artifact_policy: str = "artifact_ref_with_preview"
    tool_call_id_policy: str = "stable_unique_per_call"
    tool_contract_visibility: Literal["model_visible_schema_only", "audit_only"] = (
        "model_visible_schema_only"
    )
    permission_policy_snapshot_ref: ArtifactRef
    hook_policy_snapshot_ref: ArtifactRef
    mcp_policy_snapshot_ref: ArtifactRef


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
    requested_provider: str | None = None
    actual_provider: str | None = None
    fallback_reason: str | None = None
    fallback_policy_version: str | None = None
    provider_base_url: str | None = None
    provider_endpoint_category: str | None = None
    credential_source: str | None = None
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
    feedback_policy_resolution: dict[str, Any] = Field(default_factory=dict)
    hidden_feedback_visible_to_model: bool
    swe_bench_like_final_only: bool = False
    tool_protocol: ToolProtocolFacts
    permission_policy_manifest_ref: ArtifactRef | None = None
    source_snapshot_ref: ArtifactRef | None = None
    repo_context_index_ref: ArtifactRef | None = None
    provider_axis_scope: str | None = None
    baseline_source: str | None = None
    forbidden_scaffold_ids: list[str] = Field(default_factory=list)
    search_fact_policy_version: str = "repo_harness_search_fact_trust_v1"
    repository_action_index_policy_version: str = "repo_harness_repository_action_index_v1"
    convergence_nudge_policy_version: str = "repo_harness_convergence_nudge_v2"
    context_warning_policy_version: str = "repo_harness_context_warning_v1"
    context_replacement_runtime_policy_version: str = (
        "deterministic_tool_result_replacement_runtime_v1"
    )
    provider_ready_token_estimator_version: str = "provider_body_char4_token_estimator_v1"
    context_threshold_decision_source: str = "provider_ready_token_estimate"
    compact_threshold_ratio_runtime_effect: str = (
        "connected_to_tool_result_replacement_budget_v1"
    )
    context_policy_snapshot_version: str = "repo_harness_context_policy_snapshot_v1"
    context_policy_snapshot_hash: str | None = Field(default=None, pattern=SHA256_PATTERN)
    context_policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    context_budget_policy: str = "model_window_with_optional_cap"
    tool_result_compact_policy: str = "claude_code_fresh_only_v1"
    microcompact_policy: str = "count_based_tool_result_clear_v1"
    auto_compact_enabled: bool = True
    reactive_compact_policy: str = "provider_verified_reactive"
    harness_control_message_export_policy: str = (
        "exclude_harness_generated_untrainable_control_messages_v1"
    )
    tool_call_repair_policy_version: str = "malformed_tool_call_repair_v0"
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
    provider_request_timeout_sec: int | None = Field(default=None, gt=0)
    provider_timeout_grace_sec: int = Field(default=2, ge=0)
    min_provider_request_timeout_sec: int = Field(default=5, gt=0)
    provider_timeout_policy: str = "task_deadline_clamped_provider_request_v0"
    command_timeout_sec: int = Field(gt=0)
    context_budget_tokens: int = Field(gt=0)
    model_context_window_tokens: int | None = Field(default=None, gt=0)
    model_context_window_resolution: str | None = None
    effective_context_budget_tokens: int | None = Field(default=None, gt=0)
    hard_context_limit_tokens: int | None = Field(default=None, gt=0)
    main_output_reserve_tokens: int | None = Field(default=None, ge=0)
    estimator_safety_margin_tokens: int | None = Field(default=None, ge=0)
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
    tool_protocol: ToolProtocolFacts
    run_status: Literal["completed", "skipped", "failed", "interrupted"]
    agent_stop_reason: str | None = None
    run_outcome: str
    reward_status: Literal["present", "missing", "not_applicable", "invalid"]
    final_verifier_status: Literal[
        "accepted",
        "failed",
        "rejected",
        "not_executed",
        "timeout",
        "error",
        "skipped",
    ]
    final_verifier_mode: str | None = None
    source_checkout: SourceCheckoutFacts | None = None
    environment_spec_hash: str | None = Field(default=None, pattern=SHA256_PATTERN)
    scaffold_id: str | None = None
    scaffold_version: str | None = None
    scaffold_facts: dict[str, Any] = Field(default_factory=dict)
    feedback_policy_resolution: dict[str, Any] = Field(default_factory=dict)
    test_feedback_policy: str | None = None
    feedback_tests_passed_policy: str | None = None
    hidden_feedback_visible_to_model: bool | None = None
    metrics_summary: dict[str, Any] = Field(default_factory=dict)
    tool_call_summary: dict[str, Any] = Field(default_factory=dict)
    model_call_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_manifest_status: Literal["ok", "missing", "invalid"]
    failure_diagnostics: list[FailureDiagnostics] = Field(default_factory=list)
    export_readiness: ExportReadinessFacts
