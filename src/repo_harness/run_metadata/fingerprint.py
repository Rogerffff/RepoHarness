"""本地执行环境和源码快照指纹。"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from repo_harness.run_metadata.schemas import (
    EnvironmentFingerprint,
    ExecutionModeFacts,
    SourceCheckoutFacts,
    WorkspaceBackendFacts,
    WorkspaceExecutionFacts,
)
from repo_harness.schema_base import stable_hash
from repo_harness.tasks import TaskDefinition
from repo_harness.tasks.command_policy import COMMAND_POLICY_VERSION
from repo_harness.tasks.environment import compute_environment_spec_hash
from repo_harness.trajectory import ArtifactRef
from repo_harness.workspace import DependencyState
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

def build_local_environment_fingerprint(
    *,
    task_definition: TaskDefinition,
    source_checkout: str | Path,
    dependency_state: DependencyState,
    command_timeout_sec: int,
    network_policy: str,
    dependency_state_ref: ArtifactRef | None = None,
    setup_artifact_hash: str = "none",
    shell_command_policy_version: str = COMMAND_POLICY_VERSION,
    source_checkout_facts: SourceCheckoutFacts | None = None,
) -> EnvironmentFingerprint:
    source_tree_hash = compute_source_tree_hash(source_checkout)
    if source_checkout_facts is None:
        source_facts = SourceCheckoutFacts(
            source_kind=task_definition.source_kind,
            source_type="fixture_path",
            base_commit=task_definition.base_commit,
            synthetic_base_id=None if task_definition.base_commit else f"{task_definition.id}_synthetic_base",
            source_archive_sha256=task_definition.source_archive_sha256,
            source_tree_hash=source_tree_hash,
            checkout_path_status="redacted",
            decontamination_status=task_definition.decontamination.status,
        )
    else:
        source_facts = source_checkout_facts.model_copy(
            update={"source_tree_hash": source_tree_hash}
        )
    execution_mode = ExecutionModeFacts(
        requested_execution_mode="local_process",
        resolved_execution_mode="local_process",
        execution_mode_status="active",
    )
    backend = WorkspaceBackendFacts(
        backend="local_process",
        backend_version="repo_harness_local_workspace_adapter_v0",
        execution_mode=execution_mode,
        network_policy=network_policy,
        isolation_claims=["task_level_workspace_boundary", "command_policy_checks"],
    )
    lockfile_hashes = {
        item.path: item.sha256
        for item in task_definition.environment.lockfile_hashes
    }
    environment_spec_hash = compute_environment_spec_hash(
        environment=task_definition.environment,
        source_checkout_facts=source_facts,
        dependency_state_strategy=dependency_state.strategy,
        execution_mode="local_process",
        setup_artifact_hash=setup_artifact_hash,
    )
    workspace_execution = WorkspaceExecutionFacts(
        workspace_backend=backend,
        source_checkout=source_facts,
        python_version=sys.version.split()[0],
        operating_system=platform.platform(),
        command_timeout_sec=command_timeout_sec,
        shell_command_policy_version=shell_command_policy_version,
        environment_spec_hash=environment_spec_hash,
        dependency_state_ref=dependency_state_ref,
        setup_artifact_hash=setup_artifact_hash,
    )
    return EnvironmentFingerprint(
        fingerprint_id=stable_hash(
            {
                "run_source_tree_hash": source_tree_hash,
                "environment_spec_hash": environment_spec_hash,
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
            }
        )[:16],
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        package_manager=task_definition.environment.package_manager,
        lockfile_hashes=lockfile_hashes,
        environment_spec_hash=environment_spec_hash,
        workspace_execution=workspace_execution,
    )
