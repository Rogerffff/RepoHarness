"""工作区与命令执行结果 schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.trajectory import ArtifactRef


class ExecutionResult(StrictBaseModel):
    schema_version: str = "repo_harness_execution_result_v0"
    exit_code: int | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""
    output_artifact_ref: ArtifactRef | None = None
    duration_ms: int = Field(default=0, ge=0)
    timeout: bool = False
    command_semantics: str = "generic"
    exit_code_interpretation: str = "unknown"


class DependencyState(StrictBaseModel):
    schema_version: str = "repo_harness_dependency_state_v0"
    strategy: Literal["none", "rerun_setup", "copy_declared_paths", "docker_image_layer"] = "none"
    cache_key: str | None = None
    artifact_ref: ArtifactRef | None = None
    restored_paths: list[str] = Field(default_factory=list)
    excluded_diff_paths: list[str] = Field(default_factory=list)
    created_after_setup_command: bool = False
    excludes_baseline_side_effects: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunWorkspace(StrictBaseModel):
    schema_version: str = "repo_harness_run_workspace_v0"
    run_id: str
    workspace_path: str
    repo_base_commit: str | None = None
    execution_mode: str = "local_process"
    artifact_dir: str
    dependency_state: DependencyState
    dependency_state_ref: ArtifactRef | None = None
    agent_start_snapshot: str | None = None
    agent_diff_base: str | None = None
