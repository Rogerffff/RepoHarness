"""工作区适配器模块。"""

from repo_harness.workspace.adapter import LocalWorkspaceAdapter, PatchCapture
from repo_harness.workspace.backend_factory import create_workspace_adapter
from repo_harness.workspace.backend_status import (
    DockerStageStatus,
    WorkspaceBackendTestStatus,
    build_workspace_backend_status,
    inspect_workspace_backend_status,
    load_workspace_backend_status,
    write_workspace_backend_status,
)
from repo_harness.workspace.docker_adapter import DockerWorkspaceAdapter, inspect_docker_environment
from repo_harness.workspace.materialization import SourceCheckout, materialize_source
from repo_harness.workspace.protocol import (
    WorkspaceAdapter,
    WorkspaceBackend,
    WorkspaceBackendError,
    WorkspaceCommandResult,
    WorkspacePaths,
)
from repo_harness.workspace.reuse import (
    RESOURCE_CLEANUP_COMPLETED,
    RESOURCE_CLEANUP_FAILED,
    RESOURCE_CLEANUP_NOT_STARTED,
    RESOURCE_CLEANUP_SKIPPED,
    WORKSPACE_REUSE_POLICY_VERSION,
    WorkspaceLease,
    WorkspaceLeaseHandle,
    WorkspaceReusePolicy,
    WorkspaceSnapshotFacts,
    WorkspaceSnapshotKey,
    WorkspaceSnapshotManager,
    WorkspaceSnapshotResult,
    build_workspace_snapshot_key,
    copy_declared_dependency_paths,
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
    "DockerWorkspaceAdapter",
    "ExecutionResult",
    "LocalWorkspaceAdapter",
    "PatchCapture",
    "RunWorkspace",
    "RESOURCE_CLEANUP_COMPLETED",
    "RESOURCE_CLEANUP_FAILED",
    "RESOURCE_CLEANUP_NOT_STARTED",
    "RESOURCE_CLEANUP_SKIPPED",
    "SourceCheckout",
    "WORKSPACE_REUSE_POLICY_VERSION",
    "DockerStageStatus",
    "WorkspaceAdapter",
    "WorkspaceBackend",
    "WorkspaceBackendError",
    "WorkspaceBackendTestStatus",
    "WorkspaceCommandResult",
    "WorkspaceLease",
    "WorkspaceLeaseHandle",
    "WorkspacePaths",
    "WorkspaceReusePolicy",
    "WorkspaceSnapshotFacts",
    "WorkspaceSnapshotKey",
    "WorkspaceSnapshotManager",
    "WorkspaceSnapshotResult",
    "build_workspace_backend_status",
    "build_workspace_snapshot_key",
    "copy_declared_dependency_paths",
    "create_workspace_adapter",
    "inspect_docker_environment",
    "inspect_workspace_backend_status",
    "load_workspace_backend_status",
    "materialize_source",
    "write_workspace_backend_status",
]
