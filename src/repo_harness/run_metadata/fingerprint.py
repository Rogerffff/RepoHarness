"""本地执行环境和源码快照指纹。"""

from __future__ import annotations

import hashlib
import json
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
from repo_harness.trajectory import ArtifactRef
from repo_harness.workspace import DependencyState

EXCLUDED_TREE_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}


def compute_file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_source_tree_hash(root: str | Path) -> str:
    """对 source checkout 生成稳定 hash，排除 Git、缓存和运行产物目录。"""

    root_path = Path(root)
    entries: list[dict[str, str]] = []
    for path in sorted(root_path.rglob("*")):
        relative = path.relative_to(root_path)
        if _is_excluded(relative):
            continue
        if path.is_dir():
            continue
        if path.is_symlink():
            entries.append(
                {
                    "path": relative.as_posix(),
                    "kind": "symlink",
                    "target": str(path.readlink()),
                }
            )
            continue
        if path.is_file():
            entries.append(
                {
                    "path": relative.as_posix(),
                    "kind": "file",
                    "sha256": compute_file_sha256(path),
                }
            )
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_local_environment_fingerprint(
    *,
    task_definition: TaskDefinition,
    source_checkout: str | Path,
    dependency_state: DependencyState,
    command_timeout_sec: int,
    network_policy: str,
    dependency_state_ref: ArtifactRef | None = None,
    setup_artifact_hash: str = "none",
    shell_command_policy_version: str = "repo_harness_shell_policy_v0",
) -> EnvironmentFingerprint:
    source_tree_hash = compute_source_tree_hash(source_checkout)
    source_facts = SourceCheckoutFacts(
        source_kind=task_definition.source_kind,
        base_commit=task_definition.base_commit,
        synthetic_base_id=None if task_definition.base_commit else f"{task_definition.id}_synthetic_base",
        source_archive_sha256=task_definition.source_archive_sha256,
        source_tree_hash=source_tree_hash,
        checkout_path_status="redacted",
        decontamination_status=task_definition.decontamination.status,
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
    environment_spec_hash = stable_hash(
        {
            "environment": task_definition.environment.model_dump(mode="json"),
            "dependency_state_strategy": dependency_state.strategy,
            "source_tree_hash": source_tree_hash,
            "execution_mode": "local_process",
        }
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


def _is_excluded(relative: Path) -> bool:
    return any(part in EXCLUDED_TREE_PARTS for part in relative.parts)
