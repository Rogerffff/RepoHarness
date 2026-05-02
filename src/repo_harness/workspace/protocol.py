"""Workspace Adapter 的第二版最小协议。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from repo_harness.errors import RepoHarnessError
from repo_harness.schema_base import StrictBaseModel
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.workspace.schemas import DependencyState, ExecutionResult, RunWorkspace


class WorkspaceBackend(str, Enum):
    """可配置的工作区执行后端。"""

    local_process = "local_process"
    docker = "docker"

class WorkspaceBackendError(RepoHarnessError):
    """工作区后端不可用或拒绝执行时使用的明确错误。"""


class WorkspacePaths(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_paths_v2_v0"
    run_dir: str
    workspaces_dir: str
    source_checkout: str | None = None
    setup_workspace: str | None = None
    agent_workspace: str | None = None
    verification_workspace: str | None = None


class WorkspaceCommandResult(StrictBaseModel):
    schema_version: str = "repo_harness_workspace_command_result_v2_v0"
    exit_code: int | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""
    output_artifact_ref: ArtifactRef | None = None
    duration_ms: int = Field(default=0, ge=0)
    timeout: bool = False
    execution_backend: WorkspaceBackend = WorkspaceBackend.local_process
    execution_id: str | None = None
    command_semantics: str = "generic"
    exit_code_interpretation: str = "unknown"


@runtime_checkable
class WorkspaceAdapter(Protocol):
    """工作区生命周期和命令执行后端必须实现的最小契约。"""

    backend: WorkspaceBackend

    def create_source_checkout(self, task: object) -> Path:
        ...

    def create_setup_workspace(self, source_checkout: str | Path) -> Path:
        ...

    def capture_dependency_state(self, **kwargs: object) -> DependencyState:
        ...

    def create_agent_workspace(
        self,
        *,
        task: object,
        source_checkout: str | Path,
        dependency_state: DependencyState,
        setup_command: str | None = None,
        recorder: RunRecorder,
    ) -> RunWorkspace:
        ...

    def create_verification_workspace(
        self,
        *,
        source_checkout: str | Path,
        dependency_state: DependencyState,
        final_patch_path: str | Path,
        setup_command: str | None = None,
        recorder: RunRecorder,
    ) -> str | Path:
        ...

    def restore_dependency_state(
        self,
        workspace_path: str | Path,
        dependency_state: DependencyState,
        setup_command: str | None,
        recorder: RunRecorder | None = None,
    ) -> None:
        ...

    def run_command(
        self,
        workspace_path: str | Path,
        command: str | list[str],
        *,
        timeout_sec: float | None = None,
        recorder: RunRecorder | None = None,
        command_semantics: str = "generic",
        allow_shell: bool = False,
    ) -> ExecutionResult:
        ...

    def resolve_workspace_path(
        self,
        workspace_path: str | Path,
        requested_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        ...

    def read_text(self, workspace_path: str | Path, requested_path: str | Path) -> str:
        ...

    def write_text(self, workspace_path: str | Path, requested_path: str | Path, content: str) -> None:
        ...

    def list_files(
        self,
        workspace_path: str | Path,
        root: str | Path = ".",
        *,
        pattern: str | None = None,
    ) -> list[str]:
        ...

    def apply_patch(
        self,
        workspace_path: str | Path,
        patch_path: str | Path,
        *,
        recorder: RunRecorder | None = None,
        command_semantics: str = "git_apply",
    ) -> ExecutionResult:
        ...

    def capture_final_patch(self, run_workspace: RunWorkspace, *, recorder: RunRecorder) -> Any:
        ...

    def cleanup_workspaces(self) -> None:
        ...

    def is_sensitive_relative_path(self, relative_path: str | Path) -> bool:
        ...
