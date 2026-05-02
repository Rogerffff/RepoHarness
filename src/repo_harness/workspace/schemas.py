"""工作区与命令执行结果 schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    CONTAINER_EXECUTION_FACTS_SCHEMA_VERSION,
    DOCKER_BACKEND_FACTS_SCHEMA_VERSION,
)
from repo_harness.trajectory import ArtifactRef

SHA256_PATTERN = r"^[0-9a-f]{64}$"


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


class DockerBackendFacts(StrictBaseModel):
    schema_version: str = DOCKER_BACKEND_FACTS_SCHEMA_VERSION
    backend: Literal["docker"] = "docker"
    backend_version: str = "repo_harness_docker_backend_v3_v0"
    docker_context: str
    docker_cli_version: str | None = None
    docker_server_version: str | None = None
    docker_desktop_version: str | None = None
    server_platform: str
    server_architecture: str
    requested_container_platform: Literal["linux/amd64", "linux/arm64"]
    image_ref: str
    image_id: str = Field(pattern=SHA256_PATTERN)
    image_platform: str
    build_mode: Literal["pulled", "local_build", "prebuilt", "unknown"]
    cross_architecture_emulation: bool
    network_policy: str
    mount_policy: str
    timeout_sec: int = Field(gt=0)
    cleanup_policy: str
    cleanup_status: Literal["not_started", "completed", "failed", "skipped"]
    unavailable_reason: str | None = None


class ContainerExecutionFacts(StrictBaseModel):
    schema_version: str = CONTAINER_EXECUTION_FACTS_SCHEMA_VERSION
    command_id: str
    container_id: str | None = None
    image_id: str = Field(pattern=SHA256_PATTERN)
    requested_container_platform: Literal["linux/amd64", "linux/arm64"]
    container_uname_m: str
    command: list[str]
    workdir: str
    exit_code: int | None = None
    timeout: bool = False
    duration_ms: int = Field(ge=0)
    network_policy: str
    mount_policy: str
    cleanup_status: Literal["not_started", "completed", "failed", "skipped"]
    stdout_ref: ArtifactRef | None = None
    stderr_ref: ArtifactRef | None = None


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
