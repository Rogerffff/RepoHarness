"""RunConfig schema。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field

from repo_harness.errors import ConfigError
from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    CONTEXT_BUILDER_VERSION,
    CONTEXT_POLICY_VERSION,
    EXPORT_POLICY_VERSION,
    PERMISSION_POLICY_VERSION,
    PROMPT_TEMPLATE_VERSION,
    RUN_SCHEMA_VERSION,
    TOKEN_ESTIMATOR_VERSION,
    TOOL_POLICY_VERSION,
)


class ModelConfig(StrictBaseModel):
    schema_version: str = "repo_harness_model_config_v0"
    provider: str = "replay"
    model_id: str = "replay-script-v0"
    replay_script_path: str | None = None
    temperature: float = Field(default=0.0, ge=0.0)
    max_output_tokens: int = Field(default=4096, gt=0)
    retry_policy: str = "none"
    credential_policy: str = "env_only"
    provider_request_logging: str = "redact_secrets"


class RuntimeConfig(StrictBaseModel):
    schema_version: str = "repo_harness_runtime_config_v0"
    scaffold_id: str = "simple_react"
    execution_mode: Literal["local_process", "docker"] = "local_process"
    permission_mode: Literal["plan", "ask", "auto", "deny"] = "auto"
    max_turns: int = Field(default=20, gt=0)
    max_tool_calls: int = Field(default=80, ge=0)
    max_test_runs: int = Field(default=6, ge=0)
    no_progress_patience: int = Field(default=3, ge=0)
    task_timeout_sec: int = Field(default=900, gt=0)
    seed: int | None = 42


class WorkspaceConfig(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_config_v0"
    output_dir: str = "runs"
    keep_workspace: bool = True
    default_command_timeout_sec: int = Field(default=120, gt=0)
    max_tool_output_chars: int = Field(default=12000, gt=0)
    max_artifact_bytes: int | None = Field(default=None, gt=0)
    network_policy: str = "deny_agent_run"


class ContextManagementConfig(StrictBaseModel):
    schema_version: str = "repo_harness_context_management_config_v0"
    max_context_tokens: int = Field(default=120000, gt=0)
    tool_result_aggregate_budget_chars: int = Field(default=40000, gt=0)
    keep_recent_turns: int = Field(default=6, ge=0)
    keep_recent_test_results: int = Field(default=2, ge=0)
    summarize_old_test_outputs: bool = True
    compact_strategy: str = "deterministic_preview_replacement"
    compact_threshold_ratio: float = Field(default=0.85, gt=0.0, le=1.0)
    context_policy_version: str = CONTEXT_POLICY_VERSION
    token_estimator: str = TOKEN_ESTIMATOR_VERSION


class EvaluationConfig(StrictBaseModel):
    schema_version: str = "repo_harness_evaluation_config_v0"
    concurrency: int = Field(default=1, gt=0)
    rerun_final_verifier: bool = True
    final_verifier_mode: Literal["strict_patch_replay", "agent_workspace_debug"] = "strict_patch_replay"
    fail_on_invalid_task: bool = False


class VersionConfig(StrictBaseModel):
    schema_version: str = RUN_SCHEMA_VERSION
    prompt_template_version: str = PROMPT_TEMPLATE_VERSION
    context_builder_version: str = CONTEXT_BUILDER_VERSION
    tool_policy_version: str = TOOL_POLICY_VERSION
    permission_policy_version: str = PERMISSION_POLICY_VERSION
    export_policy_version: str = EXPORT_POLICY_VERSION


class LoggingConfig(StrictBaseModel):
    schema_version: str = "repo_harness_logging_config_v0"
    level: str = "info"
    write_transcript: bool = True
    write_events: bool = True


class RunConfig(StrictBaseModel):
    schema_version: str = RUN_SCHEMA_VERSION
    run_id_prefix: str = "local_eval"
    tasks: list[str] = Field(default_factory=list)
    model: ModelConfig = Field(default_factory=ModelConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    context_management: ContextManagementConfig = Field(default_factory=ContextManagementConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    versions: VersionConfig = Field(default_factory=VersionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def ensure_batch_safe(self) -> None:
        """批量评测不能使用需要人工确认的 ask 模式。"""

        if self.runtime.permission_mode == "ask":
            raise ConfigError("批量评测不能使用 permission_mode=ask，请改为 auto 或 deny。")

    def with_output_dir(self, output_dir: str | Path | None) -> "RunConfig":
        if output_dir is None:
            return self
        return self.model_copy(
            update={"workspace": self.workspace.model_copy(update={"output_dir": str(output_dir)})}
        )
