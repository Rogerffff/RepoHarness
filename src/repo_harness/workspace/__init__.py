"""工作区适配器模块。"""

from repo_harness.workspace.adapter import LocalWorkspaceAdapter, PatchCapture
from repo_harness.workspace.backend_status import (
    DockerStageStatus,
    WorkspaceBackendTestStatus,
    build_workspace_backend_status,
    inspect_workspace_backend_status,
    load_workspace_backend_status,
    write_workspace_backend_status,
)
from repo_harness.workspace.materialization import SourceCheckout, materialize_source
from repo_harness.workspace.protocol import (
    WorkspaceAdapter,
    WorkspaceBackend,
    WorkspaceBackendError,
    WorkspaceCommandResult,
    WorkspacePaths,
)
from repo_harness.workspace.schemas import (
    ContainerExecutionFacts,
    DependencyState,
    DockerBackendFacts,
    ExecutionResult,
    RunWorkspace,
)

__all__ = [
    "ContainerExecutionFacts",
    "DependencyState",
    "DockerBackendFacts",
    "ExecutionResult",
    "LocalWorkspaceAdapter",
    "PatchCapture",
    "RunWorkspace",
    "SourceCheckout",
    "DockerStageStatus",
    "WorkspaceAdapter",
    "WorkspaceBackend",
    "WorkspaceBackendError",
    "WorkspaceBackendTestStatus",
    "WorkspaceCommandResult",
    "WorkspacePaths",
    "build_workspace_backend_status",
    "inspect_workspace_backend_status",
    "load_workspace_backend_status",
    "materialize_source",
    "write_workspace_backend_status",
]
