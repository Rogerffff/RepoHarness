"""Workspace backend factory."""

from __future__ import annotations

from pathlib import Path

from repo_harness.config import RunConfig
from repo_harness.workspace.adapter import LocalWorkspaceAdapter
from repo_harness.workspace.docker_adapter import DockerWorkspaceAdapter
from repo_harness.workspace.protocol import WorkspaceAdapter


class DockerBackendInitializationError(RuntimeError):
    """Docker backend failed before an adapter could persist normal status."""

    def __init__(self, message: str, *, structured_failure_reason: str) -> None:
        super().__init__(message)
        self.structured_failure_reason = structured_failure_reason


def create_workspace_adapter(
    *,
    config: RunConfig,
    run_id: str,
    run_dir: str | Path,
) -> WorkspaceAdapter:
    """Create the configured workspace backend without silent fallback."""

    if config.runtime.execution_mode == "local_process":
        return LocalWorkspaceAdapter(
            run_id=run_id,
            run_dir=run_dir,
            default_command_timeout_sec=config.workspace.default_command_timeout_sec,
            keep_workspace=config.workspace.keep_workspace,
        )
    if config.runtime.execution_mode == "docker":
        try:
            return DockerWorkspaceAdapter(
                run_id=run_id,
                run_dir=run_dir,
                docker_config=config.runtime.docker_backend,
                default_command_timeout_sec=config.workspace.default_command_timeout_sec,
                keep_workspace=config.workspace.keep_workspace,
            )
        except Exception as exc:
            reason = type(exc).__name__
            message = str(exc)
            if "build_if_missing=false" in message:
                reason = "docker_image_missing"
            elif "docker CLI" in message:
                reason = "docker_cli_missing"
            elif "Docker command" in message or "Docker backend requested" in message:
                reason = "docker_unavailable"
            raise DockerBackendInitializationError(
                message,
                structured_failure_reason=reason,
            ) from exc
    raise ValueError(f"Unsupported execution mode: {config.runtime.execution_mode}")
