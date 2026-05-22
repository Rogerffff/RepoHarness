"""Docker workspace backend for V3 repository-level runs."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from repo_harness.config import DockerRuntimeConfig
from repo_harness.errors import WorkspaceError
from repo_harness.tasks import RunnableTask
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.workspace.adapter import (
    DEFAULT_EXCLUDED_DIFF_PATHS,
    PatchCapture,
    _binary_files_from_numstat,
    _copy_tree,
    _count_diff_lines,
    _is_sensitive_relative_path,
    _is_text_file,
    _prepare_command,
    _preview,
    _symlink_files_from_summary,
)
from repo_harness.workspace.backend_status import build_workspace_backend_status
from repo_harness.workspace.materialization import SourceCheckout, materialize_source
from repo_harness.workspace.protocol import WorkspaceBackend
from repo_harness.workspace.schemas import (
    ContainerExecutionFacts,
    DependencyState,
    DockerBackendFacts,
    ExecutionResult,
    RunWorkspace,
)

CONTAINER_RUN_ROOT = PurePosixPath("/repo-harness-run")
EFFECTIVE_DOCKER_MOUNT_POLICY = "run_dir_read_only_workspace_read_write"
REQUIRED_DOCKER_PHASES = [
    "source_checkout",
    "setup",
    "agent_tool",
    "run_tests",
    "final_patch_capture",
    "verification_workspace_creation",
    "verifier_patch_apply",
    "test_patch_apply",
    "model_final_patch_apply",
    "fail_to_pass_test_execution",
    "pass_to_pass_test_execution",
    "final_verifier",
]
SUPPORTING_DOCKER_PHASE = "supporting_execution"
PHASE_NOT_APPLICABLE_REASONS = {
    "verifier_patch_apply": "no verifier patch is configured for this task",
    "test_patch_apply": "no test patch is configured for this task",
}
PRE_VERL_FINAL_VERIFIER_NOT_EXECUTED_PHASE_REASON = (
    "pre-verl final verifier was not executed for this terminal outcome"
)
SEMANTICS_TO_PHASE = {
    "source_checkout": "source_checkout",
    "setup": "setup",
    "file_read": "agent_tool",
    "file_write": "agent_tool",
    "agent_tool": "agent_tool",
    "agent_tool_search": "agent_tool",
    "agent_tool_file_discovery": "agent_tool",
    "bash_diagnostic": "agent_tool",
    "execute_bash": "agent_tool",
    "git_diff": "agent_tool",
    "run_tests": "run_tests",
    "verifier_feedback": "run_tests",
    "final_patch_capture": "final_patch_capture",
    "verification_workspace_creation": "verification_workspace_creation",
    "pre_verl_verification_workspace_creation": "verification_workspace_creation",
    "verifier_patch_apply": "verifier_patch_apply",
    "test_patch_apply": "test_patch_apply",
    "pre_verl_hidden_test_patch_apply": "test_patch_apply",
    "model_final_patch_apply": "model_final_patch_apply",
    "pre_verl_model_final_patch_apply": "model_final_patch_apply",
    "fail_to_pass_test_execution": "fail_to_pass_test_execution",
    "pre_verl_fail_to_pass_test_execution": "fail_to_pass_test_execution",
    "pass_to_pass_test_execution": "pass_to_pass_test_execution",
    "pre_verl_pass_to_pass_test_execution": "pass_to_pass_test_execution",
    "verifier_final": "final_verifier",
}
DEFAULT_DOCKERFILE_TEMPLATE = """\
FROM {base_image}
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir pytest mpmath
WORKDIR /workspace
"""
RG_RESOURCE_ERROR_PATTERNS = (
    "os error 11",
    "resource temporarily unavailable",
    "failed to spawn worker thread",
    "could not spawn worker thread",
)
RG_EXCLUDED_GLOBS = (
    "!.git/**",
    "!.hg/**",
    "!.svn/**",
    "!.bzr/**",
    "!__pycache__/**",
    "!.pytest_cache/**",
    "!.mypy_cache/**",
    "!.ruff_cache/**",
    "!.tox/**",
    "!.venv/**",
    "!.pre_verl_venv/**",
    "!venv/**",
    "!node_modules/**",
    "!build/**",
    "!dist/**",
    "!.aws/**",
    "!.ssh/**",
    "!.gnupg/**",
    "!.env",
    "!.env.*",
    "!**/.env",
    "!**/.env.*",
    "!.npmrc",
    "!**/.npmrc",
    "!.pypirc",
    "!**/.pypirc",
    "!.netrc",
    "!**/.netrc",
    "!pip.conf",
    "!**/pip.conf",
    "!pip.ini",
    "!**/pip.ini",
    "!credentials",
    "!credentials.*",
    "!*credentials*.json",
    "!**/credentials",
    "!**/credentials.*",
    "!**/*credentials*.json",
    "!token",
    "!token.*",
    "!**/token",
    "!**/token.*",
    "!secret",
    "!secret.*",
    "!secrets.json",
    "!**/secret",
    "!**/secret.*",
    "!**/secrets.json",
    "!id_rsa",
    "!id_dsa",
    "!id_ecdsa",
    "!id_ed25519",
    "!**/id_rsa",
    "!**/id_dsa",
    "!**/id_ecdsa",
    "!**/id_ed25519",
    "!*.pem",
    "!*.key",
    "!*.p12",
    "!*.pfx",
    "!*.crt",
    "!*.cer",
    "!**/*.pem",
    "!**/*.key",
    "!**/*.p12",
    "!**/*.pfx",
    "!**/*.crt",
    "!**/*.cer",
)


@dataclass(frozen=True)
class DockerEnvironment:
    docker_path: str
    docker_context: str
    docker_cli_version: str | None
    docker_server_version: str
    docker_desktop_version: str | None
    server_platform: str
    server_architecture: str
    mem_total_bytes: int


@dataclass(frozen=True)
class DockerCommandOutput:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timeout: bool
    container_name: str
    cleanup_status: str
    facts_ref: str
    output_artifact_ref: ArtifactRef | None = None
    stdout_ref: ArtifactRef | None = None
    stderr_ref: ArtifactRef | None = None


class DockerWorkspaceAdapter:
    """Workspace backend that executes commands in Docker containers.

    Stage 2 intentionally uses a bounded bind mount of the run directory. Source
    materialization and artifact persistence stay on the host, while every
    command execution goes through ``docker run`` with an explicit platform,
    network policy, mount policy, timeout and cleanup fact.
    """

    backend = WorkspaceBackend.docker

    def __init__(
        self,
        *,
        run_id: str,
        run_dir: str | Path,
        docker_config: DockerRuntimeConfig,
        default_command_timeout_sec: float = 120,
        keep_workspace: bool = True,
    ) -> None:
        self.run_id = run_id
        self.run_dir = Path(run_dir).resolve()
        self.workspaces_dir = self.run_dir / "workspaces"
        self.default_command_timeout_sec = default_command_timeout_sec
        self.keep_workspace = keep_workspace
        self.config = docker_config
        self.image_ref = docker_config.image_ref
        self.network_policy = docker_config.network_policy
        self.configured_mount_policy = docker_config.mount_policy
        self.mount_policy = EFFECTIVE_DOCKER_MOUNT_POLICY
        self.cleanup_policy = docker_config.cleanup_policy
        self.facts_dir = self.run_dir / "container_execution_facts"
        self.last_source_checkout: SourceCheckout | None = None
        self._command_counter = 0
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.facts_dir.mkdir(parents=True, exist_ok=True)
        self.environment = inspect_docker_environment()
        self.requested_container_platform = (
            docker_config.requested_container_platform
            or _platform_for_server_architecture(self.environment.server_architecture)
        )
        build_mode = self._ensure_image()
        self.image_id, self.image_platform = self._inspect_image()
        probe = self._execute_in_container(
            ["uname", "-m"],
            workspace_path=self.run_dir,
            timeout_sec=30,
            command_semantics="docker_backend_probe",
            recorder=None,
        )
        self.container_uname_m = probe.stdout.strip().splitlines()[0] if probe.stdout.strip() else "unknown"
        rg_probe = self._probe_ripgrep()
        if (
            self.config.require_ripgrep_for_docker_search
            and not rg_probe["rg_available"]
            and self.config.build_if_missing
            and build_mode == "prebuilt"
        ):
            self._build_image()
            build_mode = "local_build"
            self.image_id, self.image_platform = self._inspect_image()
            probe = self._execute_in_container(
                ["uname", "-m"],
                workspace_path=self.run_dir,
                timeout_sec=30,
                command_semantics="docker_backend_probe",
                recorder=None,
            )
            self.container_uname_m = (
                probe.stdout.strip().splitlines()[0] if probe.stdout.strip() else "unknown"
            )
            rg_probe = self._probe_ripgrep()
        if self.config.require_ripgrep_for_docker_search and not rg_probe["rg_available"]:
            raise WorkspaceError(
                "Docker search backend requires ripgrep, but rg probe failed: "
                + (rg_probe.get("rg_version") or f"exit_code={rg_probe.get('rg_probe_exit_code')}")
            )
        self.backend_facts = DockerBackendFacts(
            docker_context=self.environment.docker_context,
            docker_cli_version=self.environment.docker_cli_version,
            docker_server_version=self.environment.docker_server_version,
            docker_desktop_version=self.environment.docker_desktop_version,
            server_platform=self.environment.server_platform,
            server_architecture=self.environment.server_architecture,
            requested_container_platform=self.requested_container_platform,
            image_ref=self.image_ref,
            image_id=self.image_id,
            image_platform=self.image_platform,
            build_mode=build_mode,
            cross_architecture_emulation=_platform_architecture(self.requested_container_platform)
            != _normalize_architecture(self.environment.server_architecture),
            network_policy=self.network_policy,
            mount_policy=self.mount_policy,
            timeout_sec=int(default_command_timeout_sec),
            cleanup_policy=self.cleanup_policy,
            cleanup_status="completed",
            rg_available=bool(rg_probe["rg_available"]),
            rg_path=rg_probe.get("rg_path"),
            rg_version=rg_probe.get("rg_version"),
            rg_probe_exit_code=rg_probe.get("rg_probe_exit_code"),
            search_backend_default="ripgrep" if rg_probe["rg_available"] else "unavailable",
            require_ripgrep_for_docker_search=self.config.require_ripgrep_for_docker_search,
            allow_degraded_python_search_fallback=self.config.allow_degraded_python_search_fallback,
        )
        self._write_json(self.run_dir / "docker_backend_facts.json", self.backend_facts.model_dump(mode="json"))

    def create_source_checkout(self, task: RunnableTask) -> Path:
        source_path = self.workspaces_dir / "source_checkout"
        checkout = materialize_source(task, source_path)
        self.last_source_checkout = checkout
        return checkout.root

    def create_setup_workspace(self, source_checkout: str | Path) -> Path:
        setup_path = self.workspaces_dir / "setup_workspace"
        _copy_tree(self._host_path(source_checkout), setup_path)
        return setup_path

    def capture_dependency_state(
        self,
        *,
        strategy: str = "none",
        excluded_diff_paths: list[str] | None = None,
    ) -> DependencyState:
        if strategy not in {"none", "rerun_setup"}:
            raise WorkspaceError(f"DockerWorkspaceAdapter 不支持 dependency strategy：{strategy}")
        return DependencyState(
            strategy=strategy,
            cache_key=f"{self.run_id}:docker:{strategy}",
            excluded_diff_paths=excluded_diff_paths or list(DEFAULT_EXCLUDED_DIFF_PATHS),
            created_after_setup_command=True,
            excludes_baseline_side_effects=True,
            metadata={
                "workspace_backend": "docker",
                "image_ref": self.image_ref,
                "requested_container_platform": self.requested_container_platform,
            },
        )

    def create_agent_workspace(
        self,
        *,
        task: RunnableTask,
        source_checkout: str | Path,
        dependency_state: DependencyState,
        setup_command: str | None = None,
        setup_timeout_sec: float | None = None,
        recorder: RunRecorder,
    ) -> RunWorkspace:
        workspace_path = self.workspaces_dir / "agent_workspace"
        _copy_tree(self._host_path(source_checkout), workspace_path)
        self.restore_dependency_state(
            workspace_path,
            dependency_state,
            setup_command,
            setup_timeout_sec=setup_timeout_sec,
            recorder=recorder,
        )
        agent_start_snapshot = self.create_agent_start_snapshot(
            workspace_path, dependency_state.excluded_diff_paths, recorder
        )
        return RunWorkspace(
            run_id=self.run_id,
            workspace_path=self._container_path(workspace_path).as_posix(),
            repo_base_commit=task.base_commit,
            execution_mode="docker",
            artifact_dir=(self.run_dir / "artifacts").as_posix(),
            dependency_state=dependency_state,
            agent_start_snapshot=agent_start_snapshot,
            agent_diff_base=agent_start_snapshot,
        )

    def create_verification_workspace(
        self,
        *,
        source_checkout: str | Path,
        dependency_state: DependencyState,
        final_patch_path: str | Path,
        setup_command: str | None = None,
        setup_timeout_sec: float | None = None,
        recorder: RunRecorder,
    ) -> str:
        verification_path = self.workspaces_dir / "verification_workspace"
        _copy_tree(self._host_path(source_checkout), verification_path)
        self.restore_dependency_state(
            verification_path,
            dependency_state,
            setup_command,
            setup_timeout_sec=setup_timeout_sec,
            recorder=recorder,
        )
        self._execute_in_container(
            ["python", "-c", "pass"],
            workspace_path=verification_path,
            timeout_sec=30,
            command_semantics="verification_workspace_creation",
            recorder=recorder,
        )
        self.create_agent_start_snapshot(verification_path, dependency_state.excluded_diff_paths, recorder)
        result = self.apply_patch(
            verification_path,
            final_patch_path,
            recorder=recorder,
            command_semantics="model_final_patch_apply",
        )
        if result.exit_code != 0 or result.timeout:
            raise WorkspaceError(f"final.patch 无法应用：{result.stderr_preview or result.stdout_preview}")
        return self._container_path(verification_path).as_posix()

    def restore_dependency_state(
        self,
        workspace_path: str | Path,
        dependency_state: DependencyState,
        setup_command: str | None,
        setup_timeout_sec: float | None = None,
        recorder: RunRecorder | None = None,
    ) -> None:
        if dependency_state.strategy == "none":
            return
        if dependency_state.strategy == "rerun_setup":
            if not setup_command:
                raise WorkspaceError("dependency_state=rerun_setup 需要 setup_command。")
            result = self.run_command(
                workspace_path,
                setup_command,
                timeout_sec=setup_timeout_sec,
                recorder=recorder,
                allow_shell=_requires_shell_command(setup_command),
            )
            if result.exit_code != 0 or result.timeout:
                raise WorkspaceError(f"rerun_setup 失败：{result.stderr_preview or result.stdout_preview}")
            return
        raise WorkspaceError(f"不支持的 dependency strategy：{dependency_state.strategy}")

    def create_agent_start_snapshot(
        self,
        workspace_path: str | Path,
        excluded_diff_paths: list[str] | None = None,
        recorder: RunRecorder | None = None,
    ) -> str:
        workspace = self._host_path(workspace_path)
        self._ensure_git_baseline(
            workspace, excluded_diff_paths or list(DEFAULT_EXCLUDED_DIFF_PATHS), recorder
        )
        result = self._run_git(workspace, ["rev-parse", "HEAD"], recorder=recorder)
        if result.exit_code != 0:
            raise WorkspaceError(result.stderr.strip() or "无法读取 agent_start_snapshot。")
        return result.stdout.strip()

    def capture_final_patch(self, run_workspace: RunWorkspace, *, recorder: RunRecorder) -> PatchCapture:
        workspace = self._host_path(run_workspace.workspace_path)
        base = run_workspace.agent_diff_base or run_workspace.agent_start_snapshot
        if not base:
            raise WorkspaceError("RunWorkspace 缺少 agent_start_snapshot，无法冻结 final.patch。")
        self._refresh_intent_to_add(workspace, recorder)
        patch_text = self._run_git_checked(
            workspace,
            ["diff", "--binary", base],
            recorder=recorder,
            command_semantics="final_patch_capture",
        )
        diff_text = self._run_git_checked(
            workspace,
            ["diff", base],
            recorder=recorder,
            command_semantics="final_patch_capture",
        )
        patch_path = self.run_dir / "final.patch"
        diff_path = self.run_dir / "final.diff"
        patch_path.write_text(patch_text, encoding="utf-8")
        diff_path.write_text(diff_text, encoding="utf-8")
        patch_ref = recorder.write_artifact("final_patch", patch_text, {"suffix": ".patch"})
        diff_ref = recorder.write_artifact("final_diff", diff_text, {"suffix": ".diff"})
        added, removed = _count_diff_lines(diff_text)
        patch_stats = self._collect_patch_stats(workspace, base, added, removed, recorder)
        return PatchCapture(
            patch_path=patch_path,
            diff_path=diff_path,
            patch_artifact_ref=patch_ref,
            diff_artifact_ref=diff_ref,
            patch_text=patch_text,
            diff_text=diff_text,
            added_lines=added,
            removed_lines=removed,
            patch_stats=patch_stats,
        )

    def apply_patch(
        self,
        workspace_path: str | Path,
        patch_path: str | Path,
        *,
        recorder: RunRecorder | None = None,
        command_semantics: str = "git_apply",
    ) -> ExecutionResult:
        host_patch = self._host_path(patch_path, must_be_workspace=False)
        patch_text = host_patch.read_text(encoding="utf-8")
        if not patch_text.strip():
            return ExecutionResult(exit_code=0, command_semantics="git_apply", execution_backend="docker")
        if recorder is None:
            raise WorkspaceError("apply_patch 必须提供 RunRecorder 以保存命令输出 artifact。")
        return self.run_command(
            workspace_path,
            ["git", "apply", "--whitespace=nowarn", self._container_path(host_patch).as_posix()],
            recorder=recorder,
            command_semantics=command_semantics,
        )

    def resolve_workspace_path(
        self,
        workspace_path: str | Path,
        requested_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        workspace = self._host_path(workspace_path)
        raw_path = Path(str(requested_path))
        if str(requested_path).startswith(CONTAINER_RUN_ROOT.as_posix()):
            candidate = self._host_path(requested_path)
        else:
            candidate = raw_path if raw_path.is_absolute() else workspace / raw_path
        if must_exist:
            resolved = candidate.resolve()
        else:
            resolved_parent = candidate.parent.resolve()
            resolved = resolved_parent / candidate.name
        try:
            resolved.relative_to(workspace)
        except ValueError as exc:
            raise WorkspaceError(f"路径越过 workspace 边界：{requested_path}") from exc
        relative = resolved.relative_to(workspace)
        if self.is_sensitive_relative_path(relative):
            raise WorkspaceError(f"拒绝访问敏感路径：{relative}")
        if must_exist and not resolved.exists():
            raise WorkspaceError(f"路径不存在：{requested_path}")
        if resolved.exists() and resolved.is_symlink():
            target = resolved.resolve()
            try:
                target.relative_to(workspace)
            except ValueError as exc:
                raise WorkspaceError(f"符号链接指向 workspace 外部：{requested_path}") from exc
        return resolved

    def is_sensitive_relative_path(self, relative_path: str | Path) -> bool:
        return _is_sensitive_relative_path(Path(relative_path))

    def list_files(
        self,
        workspace_path: str | Path,
        root: str | Path = ".",
        *,
        pattern: str | None = None,
    ) -> list[str]:
        root_path = self.resolve_workspace_path(workspace_path, root, must_exist=True)
        workspace = self._host_path(workspace_path)
        match_all = pattern in {None, "", "**/*"}
        backend_facts = getattr(self, "backend_facts", None)
        if backend_facts is not None and backend_facts.rg_available:
            try:
                root_arg = root_path.relative_to(workspace).as_posix()
            except ValueError as exc:
                raise WorkspaceError(f"文件发现 root 越过 workspace 边界：{root}") from exc
            command = ["rg", "--files", "--hidden"]
            for excluded in RG_EXCLUDED_GLOBS:
                command.extend(["--glob", excluded])
            if not match_all and pattern is not None:
                command.extend(["--glob", str(pattern)])
            command.append(root_arg or ".")
            output = self._execute_in_container(
                command,
                workspace_path=workspace_path,
                timeout_sec=self.default_command_timeout_sec,
                command_semantics="agent_tool_file_discovery",
                recorder=None,
            )
            if output.exit_code not in {0, 1} or output.timeout:
                raise WorkspaceError(output.stderr or output.stdout or f"无法列出文件：{root}")
            return [
                rel
                for rel in sorted(line.strip() for line in output.stdout.splitlines() if line.strip())
                if not self.is_sensitive_relative_path(rel)
            ]
        output = self._execute_in_container(
            [
                "python",
                "-c",
                (
                    "from pathlib import Path; import json, sys; "
                    "workspace=Path(sys.argv[1]); root=Path(sys.argv[2]); "
                    "paths=root.rglob('*') if root.is_dir() else [root]; "
                    "out=[]; "
                    "\nfor path in sorted(paths):\n"
                    "    parts=path.parts\n"
                    "    if not path.is_file() or '.git' in parts or '__pycache__' in parts:\n"
                    "        continue\n"
                    "    out.append(path.relative_to(workspace).as_posix())\n"
                    "print(json.dumps(out, sort_keys=True))"
                ),
                self._container_path(self._host_path(workspace_path)).as_posix(),
                self._container_path(root_path).as_posix(),
            ],
            workspace_path=workspace_path,
            timeout_sec=self.default_command_timeout_sec,
            command_semantics="agent_tool",
            recorder=None,
        )
        if output.exit_code != 0 or output.timeout:
            raise WorkspaceError(output.stderr or output.stdout or f"无法列出文件：{root}")
        try:
            raw_files = json.loads(output.stdout.strip() or "[]")
        except json.JSONDecodeError as exc:
            raise WorkspaceError("Docker list_files 返回了非 JSON 输出。") from exc
        if not isinstance(raw_files, list):
            raise WorkspaceError("Docker list_files 返回值必须是列表。")
        files = []
        for rel in raw_files:
            if not isinstance(rel, str):
                continue
            if self.is_sensitive_relative_path(rel):
                continue
            if match_all or fnmatch.fnmatch(rel, str(pattern)):
                files.append(rel)
        return files

    def read_text(self, workspace_path: str | Path, requested_path: str | Path) -> str:
        path = self.resolve_workspace_path(workspace_path, requested_path, must_exist=True)
        output = self._execute_in_container(
            [
                "python",
                "-c",
                (
                    "from pathlib import Path; import sys; "
                    "sys.stdout.write(Path(sys.argv[1]).read_text(encoding='utf-8'))"
                ),
                self._container_path(path).as_posix(),
            ],
            workspace_path=workspace_path,
            timeout_sec=self.default_command_timeout_sec,
            command_semantics="file_read",
            recorder=None,
        )
        if output.exit_code != 0 or output.timeout:
            raise WorkspaceError(output.stderr or output.stdout or f"无法读取文件：{requested_path}")
        return output.stdout

    def search_text(
        self,
        workspace_path: str | Path,
        *,
        root: str | Path = ".",
        query: str,
        mode: str = "literal",
        glob: str | None = None,
        output_mode: str = "content",
        offset: int = 0,
        max_matches: int = 200,
        context_lines: int = 0,
        timeout_sec: float | None = None,
        recorder: RunRecorder | None = None,
    ) -> dict[str, Any]:
        if mode not in {"literal", "regex"}:
            raise WorkspaceError("grep mode must be literal or regex.")
        if output_mode not in {"content", "files_with_matches", "count"}:
            raise WorkspaceError("grep output_mode must be content, files_with_matches, or count.")
        if not self.backend_facts.rg_available:
            if self.config.allow_degraded_python_search_fallback:
                raise WorkspaceError("python_fallback_requested_but_not_implemented_for_docker_search")
            raise WorkspaceError("Docker grep requires ripgrep; rg is unavailable.")

        workspace = self._host_path(workspace_path)
        root_path = self.resolve_workspace_path(workspace_path, root, must_exist=True)
        try:
            root_arg = root_path.relative_to(workspace).as_posix()
        except ValueError as exc:
            raise WorkspaceError(f"搜索 root 越过 workspace 边界：{root}") from exc
        if root_arg == "":
            root_arg = "."
        root_kind = "file" if root_path.is_file() else ("directory" if root_path.is_dir() else "other")

        command = self._ripgrep_command(
            query=query,
            mode=mode,
            glob=glob,
            output_mode=output_mode,
            root_arg=root_arg,
            context_lines=context_lines,
            single_thread=False,
        )
        output = self._execute_in_container(
            command,
            workspace_path=workspace_path,
            timeout_sec=timeout_sec or self.default_command_timeout_sec,
            command_semantics="agent_tool_search",
            recorder=recorder,
        )
        search_backend = "ripgrep"
        fallback_reason = None
        duration_ms = output.duration_ms
        if _rg_resource_limited(output.stderr, output.stdout):
            retry_command = self._ripgrep_command(
                query=query,
                mode=mode,
                glob=glob,
                output_mode=output_mode,
                root_arg=root_arg,
                context_lines=context_lines,
                single_thread=True,
            )
            retry = self._execute_in_container(
                retry_command,
                workspace_path=workspace_path,
                timeout_sec=timeout_sec or self.default_command_timeout_sec,
                command_semantics="agent_tool_search",
                recorder=recorder,
            )
            output = retry
            duration_ms += retry.duration_ms
            search_backend = "ripgrep_single_thread_retry"
            fallback_reason = "ripgrep_resource_limited_single_thread_retry"

        payload = _parse_ripgrep_json_output(
            stdout=output.stdout,
            stderr=output.stderr,
            exit_code=output.exit_code,
            timeout=output.timeout,
            output_mode=output_mode,
            offset=offset,
            max_matches=max_matches,
        )
        rg_completed = (
            payload.get("rg_exit_code") in {0, 1}
            and not bool(payload.get("rg_timeout"))
            and int(payload.get("parse_error_count") or 0) == 0
        )
        payload.update(
            {
                "root_kind": root_kind,
                "candidate_fact_source": "ripgrep_summary_only",
                "candidate_count_reliable": False,
            }
        )
        if root_kind == "file":
            payload["candidate_file_count"] = 1
            payload["candidate_fact_source"] = "root_is_file"
            payload["candidate_count_reliable"] = True
            if rg_completed:
                payload["scanned_candidate_file_count"] = 1
                payload["scanned_file_count"] = max(int(payload.get("scanned_file_count") or 0), 1)
                payload["searched_file_count"] = max(int(payload.get("searched_file_count") or 0), 1)
                payload["scanned_file_limit"] = max(int(payload.get("scanned_file_limit") or 0), 1)
                payload["unscanned_file_count"] = 0
                if int(payload.get("total_match_count") or 0) == 0:
                    payload["scan_complete_reason"] = "complete_no_match_all_visible_candidates_read"
        elif (
            root_kind == "directory"
            and rg_completed
            and int(payload.get("total_match_count") or 0) == 0
            and int(payload.get("candidate_file_count") or 0) == 0
        ):
            try:
                candidate_files = self.list_files(workspace_path, root=root, pattern=glob)
            except WorkspaceError as exc:
                payload["candidate_fact_error"] = str(exc)[:240]
            else:
                candidate_file_count = len(candidate_files)
                payload["candidate_file_count"] = candidate_file_count
                payload["scanned_candidate_file_count"] = candidate_file_count
                payload["scanned_file_count"] = candidate_file_count
                payload["searched_file_count"] = candidate_file_count
                payload["scanned_file_limit"] = max(
                    int(payload.get("scanned_file_limit") or 0),
                    candidate_file_count,
                )
                payload["unscanned_file_count"] = 0
                payload["candidate_fact_source"] = "workspace_adapter_list_files"
                payload["candidate_count_reliable"] = True
        payload.update(
            {
                "engine": "ripgrep",
                "search_backend": search_backend,
                "fallback_reason": fallback_reason,
                "execution_duration_ms": duration_ms,
                "container_execution_facts_ref": output.facts_ref,
                "root": root_arg,
                "glob": glob,
            }
        )
        return payload

    def write_text(self, workspace_path: str | Path, requested_path: str | Path, content: str) -> None:
        path = self.resolve_workspace_path(workspace_path, requested_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        inputs_dir = self.run_dir / "docker_file_inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        input_path = inputs_dir / f"write_{self._command_counter + 1:06d}.txt"
        input_path.write_text(content, encoding="utf-8")
        output = self._execute_in_container(
            [
                "python",
                "-c",
                (
                    "from pathlib import Path; import sys; "
                    "Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True); "
                    "Path(sys.argv[1]).write_bytes(Path(sys.argv[2]).read_bytes())"
                ),
                self._container_path(path).as_posix(),
                self._container_path(input_path).as_posix(),
            ],
            workspace_path=workspace_path,
            timeout_sec=self.default_command_timeout_sec,
            command_semantics="file_write",
            recorder=None,
        )
        if output.exit_code != 0 or output.timeout:
            raise WorkspaceError(output.stderr or output.stdout or f"无法写入文件：{requested_path}")

    def run_command(
        self,
        workspace_path: str | Path,
        command: str | list[str],
        *,
        timeout_sec: float | None = None,
        recorder: RunRecorder | None = None,
        command_semantics: str = "generic",
        allow_shell: bool = False,
        artifact_metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        if recorder is None:
            raise WorkspaceError("run_command 必须提供 RunRecorder 以保存 stdout/stderr artifact。")
        command_args, command_display, use_shell = _prepare_command(command, allow_shell=allow_shell)
        if use_shell:
            command_args = ["sh", "-lc", str(command_args)]
        output = self._execute_in_container(
            list(command_args) if isinstance(command_args, list) else [str(command_args)],
            workspace_path=workspace_path,
            timeout_sec=timeout_sec,
            command_semantics=command_semantics,
            recorder=recorder,
            command_display=command_display,
            artifact_metadata=artifact_metadata,
        )
        return ExecutionResult(
            exit_code=output.exit_code,
            stdout_preview=_preview(output.stdout),
            stderr_preview=_preview(output.stderr),
            output_artifact_ref=output.output_artifact_ref,
            stdout_ref=output.stdout_ref,
            stderr_ref=output.stderr_ref,
            duration_ms=output.duration_ms,
            timeout=output.timeout,
            command_semantics=command_semantics,
            exit_code_interpretation="timeout" if output.timeout else "process_exit_code",
            execution_backend="docker",
            execution_id=output.container_name,
            container_execution_facts_ref=output.facts_ref,
        )

    def cleanup_workspaces(self) -> None:
        if self.keep_workspace:
            return
        if self.workspaces_dir.exists():
            shutil.rmtree(self.workspaces_dir)

    def write_backend_status(
        self,
        *,
        evaluation_concurrency: int,
        swebench_like_effective_max_workers: int,
    ) -> None:
        status = build_workspace_backend_status(
            mode="docker_backend",
            docker_available=True,
            docker_available_reason="docker_server_responded",
            docker_context=self.environment.docker_context,
            docker_server_platform=self.environment.server_platform,
            docker_server_architecture=self.environment.server_architecture,
            docker_mem_total_bytes=self.environment.mem_total_bytes,
            evaluation_concurrency=evaluation_concurrency,
            swebench_like_effective_max_workers=swebench_like_effective_max_workers,
            requested_container_platform=self.requested_container_platform,
            container_uname_m=self.container_uname_m,
            image_id=self.image_id,
            image_platform=self.image_platform,
            build_mode=self.backend_facts.build_mode,
            network_policy=self.network_policy,
            mount_policy=self.mount_policy,
            command_timeout_sec=int(self.default_command_timeout_sec),
            cleanup_policy=self.cleanup_policy,
            cleanup_status=self.backend_facts.cleanup_status,
            docker_backend_facts_ref="docker_backend_facts.json",
            container_execution_facts_refs=self.container_execution_facts_refs(),
            container_execution_manifest_ref="container_execution_facts/manifest.json",
            docker_phase_coverage_matrix_ref="docker_phase_coverage_matrix.json",
        )
        self._write_container_execution_manifest()
        self._write_docker_phase_coverage_matrix()
        payload = status.model_dump(mode="json")
        self._write_json(self.run_dir / "docker_backend_status.json", payload)
        self._write_json(self.run_dir / "docker_stage_status.json", payload)

    def container_execution_facts_refs(self) -> list[str]:
        return [
            path.relative_to(self.run_dir).as_posix()
            for path in sorted(self.facts_dir.glob("*.json"))
            if path.name != "manifest.json"
        ]

    def _probe_ripgrep(self) -> dict[str, Any]:
        output = self._execute_in_container(
            ["sh", "-lc", "command -v rg && rg --version | head -1"],
            workspace_path=self.run_dir,
            timeout_sec=30,
            command_semantics="docker_backend_probe",
            recorder=None,
        )
        lines = [line.strip() for line in output.stdout.splitlines() if line.strip()]
        return {
            "rg_available": output.exit_code == 0 and bool(lines),
            "rg_path": lines[0] if output.exit_code == 0 and lines else None,
            "rg_version": lines[1] if output.exit_code == 0 and len(lines) > 1 else (output.stderr.strip() or None),
            "rg_probe_exit_code": output.exit_code,
        }

    def _ripgrep_command(
        self,
        *,
        query: str,
        mode: str,
        glob: str | None,
        output_mode: str,
        root_arg: str,
        context_lines: int,
        single_thread: bool,
    ) -> list[str]:
        command = [
            "rg",
            "--json",
            "--hidden",
            "--color",
            "never",
            "--line-number",
        ]
        if single_thread:
            command.extend(["-j", "1"])
        if mode == "literal":
            command.append("-F")
        if output_mode == "files_with_matches":
            command.extend(["-m", "1"])
        elif output_mode == "content" and context_lines > 0:
            command.extend(["-C", str(max(0, min(context_lines, 20)))])
        for excluded in RG_EXCLUDED_GLOBS:
            command.extend(["--glob", excluded])
        if glob:
            command.extend(["--glob", glob])
        command.extend(["--", query, root_arg])
        return command

    def _ensure_image(self) -> str:
        if self._image_exists():
            return "prebuilt"
        if not self.config.build_if_missing:
            raise WorkspaceError(f"Docker image is missing and build_if_missing=false: {self.image_ref}")
        self._build_image()
        return "local_build"

    def _build_image(self) -> None:
        process = subprocess.run(
            [
                self.environment.docker_path,
                "build",
                "--platform",
                self.requested_container_platform,
                "-t",
                self.image_ref,
                "-",
            ],
            input=_dockerfile_for_base_image(self.config.build_base_image),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=600,
        )
        if process.returncode != 0:
            raise WorkspaceError(
                "Docker backend image build failed: "
                + (process.stderr.strip() or process.stdout.strip())
            )

    def _image_exists(self) -> bool:
        result = subprocess.run(
            [
                self.environment.docker_path,
                "image",
                "inspect",
                self.image_ref,
                "--format",
                "{{.Os}}/{{.Architecture}}",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            return False
        image_platform = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        return image_platform == self.requested_container_platform

    def _inspect_image(self) -> tuple[str, str]:
        result = subprocess.run(
            [
                self.environment.docker_path,
                "image",
                "inspect",
                self.image_ref,
                "--format",
                "{{.Id}}|{{.Os}}/{{.Architecture}}",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise WorkspaceError(result.stderr.strip() or f"无法 inspect Docker image: {self.image_ref}")
        raw_id, platform = result.stdout.strip().split("|", 1)
        image_id = raw_id.removeprefix("sha256:")
        return image_id, platform

    def _execute_in_container(
        self,
        command: list[str],
        *,
        workspace_path: str | Path,
        timeout_sec: float | None,
        command_semantics: str,
        recorder: RunRecorder | None,
        command_display: str | None = None,
        artifact_metadata: dict[str, Any] | None = None,
    ) -> DockerCommandOutput:
        self._command_counter += 1
        command_id = f"{self.run_id}_container_{self._command_counter:06d}"
        container_name = _safe_container_name(command_id)
        host_workspace = self._host_path(workspace_path, must_be_workspace=False)
        container_workdir = self._container_path(host_workspace).as_posix()
        timeout = timeout_sec if timeout_sec is not None else self.default_command_timeout_sec
        docker_command = [
            self.environment.docker_path,
            "run",
            "--rm",
            "--name",
            container_name,
            "--platform",
            self.requested_container_platform,
            "--network",
            _docker_network_mode(self.network_policy),
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "GIT_CONFIG_COUNT=1",
            "-e",
            "GIT_CONFIG_KEY_0=safe.directory",
            "-e",
            "GIT_CONFIG_VALUE_0=*",
            "-v",
            f"{self.run_dir.as_posix()}:{CONTAINER_RUN_ROOT.as_posix()}:ro",
            *self._workspace_mount_args(host_workspace),
            "-w",
            container_workdir,
            self.image_ref,
            *command,
        ]
        started = time.monotonic()
        timed_out = False
        cleanup_status = "completed"
        try:
            process = subprocess.run(
                docker_command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            stdout = process.stdout
            stderr = process.stderr
            exit_code: int | None = process.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            exit_code = None
            cleanup = subprocess.run(
                [self.environment.docker_path, "rm", "-f", container_name],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=15,
            )
            cleanup_status = "completed" if cleanup.returncode == 0 else "failed"
        duration_ms = int((time.monotonic() - started) * 1000)
        output_metadata = {"retention_policy": "keep", **(artifact_metadata or {})}
        stdout_ref: ArtifactRef | None = None
        stderr_ref: ArtifactRef | None = None
        output_artifact_ref: ArtifactRef | None = None
        if recorder is not None:
            stdout_ref = recorder.write_artifact("command_stdout", stdout, output_metadata)
            stderr_ref = recorder.write_artifact("command_stderr", stderr, output_metadata)
            display = command_display or " ".join(shlex.quote(part) for part in command)
            output_artifact_ref = recorder.write_artifact(
                "command_output",
                f"$ {display}\n\n[stdout]\n{stdout}\n\n[stderr]\n{stderr}",
                output_metadata,
            )
        facts = ContainerExecutionFacts(
            command_id=command_id,
            container_id=container_name,
            image_id=self.image_id,
            requested_container_platform=self.requested_container_platform,
            container_uname_m=getattr(self, "container_uname_m", "unknown"),
            command=command,
            command_semantics=command_semantics,
            workdir=container_workdir,
            exit_code=exit_code,
            timeout=timed_out,
            duration_ms=duration_ms,
            network_policy=self.network_policy,
            mount_policy=self.mount_policy,
            cleanup_status=cleanup_status,
            output_artifact_ref=output_artifact_ref,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            stdout_preview=_preview(stdout),
            stderr_preview=_preview(stderr),
            captured_output_empty=not bool(stdout or stderr),
        )
        facts_path = self.facts_dir / f"{command_id}.json"
        self._write_json(facts_path, facts.model_dump(mode="json"))
        if recorder is not None:
            recorder.append_event(
                {
                    "event_id": recorder.next_event_id("container"),
                    "timestamp": _timestamp(),
                    "run_id": recorder.run_id,
                    "task_id": recorder.task_id,
                    "event_type": "container_command_completed",
                    "severity": "warning" if timed_out or exit_code not in {0, None} else "info",
                    "duration_ms": duration_ms,
                    "data": {
                        "command_semantics": command_semantics,
                        "container_execution_facts_ref": facts_path.relative_to(self.run_dir).as_posix(),
                        "execution_backend": "docker",
                        "exit_code": exit_code,
                        "timeout": timed_out,
                        "output_artifact_ref": output_artifact_ref.model_dump(mode="json")
                        if output_artifact_ref
                        else None,
                        "stdout_ref": stdout_ref.model_dump(mode="json") if stdout_ref else None,
                        "stderr_ref": stderr_ref.model_dump(mode="json") if stderr_ref else None,
                        "captured_output_empty": not bool(stdout or stderr),
                    },
                }
            )
        return DockerCommandOutput(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timeout=timed_out,
            container_name=container_name,
            cleanup_status=cleanup_status,
            facts_ref=facts_path.relative_to(self.run_dir).as_posix(),
            output_artifact_ref=output_artifact_ref,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
        )

    def _workspace_mount_args(self, host_workspace: Path) -> list[str]:
        try:
            host_workspace.resolve().relative_to(self.workspaces_dir.resolve())
        except ValueError:
            return []
        return [
            "-v",
            f"{host_workspace.as_posix()}:{self._container_path(host_workspace).as_posix()}:rw",
        ]

    def _ensure_git_baseline(
        self, workspace: Path, excluded_diff_paths: list[str], recorder: RunRecorder | None = None
    ) -> None:
        self._assert_workspace_under_run_dir(workspace)
        if not (workspace / ".git").exists():
            self._run_git_checked(workspace, ["init"], recorder=recorder)
        self._run_git_checked(
            workspace, ["config", "user.email", "repo-harness@example.invalid"], recorder=recorder
        )
        self._run_git_checked(
            workspace, ["config", "user.name", "RepoHarness"], recorder=recorder
        )
        exclude_file = workspace / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
        additions = "\n".join(dict.fromkeys([*excluded_diff_paths, *DEFAULT_EXCLUDED_DIFF_PATHS]))
        exclude_file.write_text(f"{existing.rstrip()}\n{additions}\n", encoding="utf-8")
        self._run_git_checked(workspace, ["add", "-A"], recorder=recorder)
        commit_result = self._run_git(
            workspace, ["commit", "-m", "repo harness agent start snapshot"], recorder=recorder
        )
        if commit_result.exit_code != 0 and "nothing to commit" not in commit_result.stdout.lower():
            if "nothing to commit" not in commit_result.stderr.lower():
                raise WorkspaceError(commit_result.stderr.strip() or commit_result.stdout.strip())

    def _refresh_intent_to_add(self, workspace: Path, recorder: RunRecorder | None = None) -> None:
        self._run_git_checked(workspace, ["add", "-N", "."], recorder=recorder)

    def _run_git(
        self,
        workspace: Path,
        args: list[str],
        *,
        recorder: RunRecorder | None = None,
        command_semantics: str = "git",
    ) -> DockerCommandOutput:
        self._assert_workspace_under_run_dir(workspace)
        return self._execute_in_container(
            ["git", *args],
            workspace_path=workspace,
            timeout_sec=self.default_command_timeout_sec,
            command_semantics=command_semantics,
            recorder=recorder,
        )

    def _run_git_checked(
        self,
        workspace: Path,
        args: list[str],
        *,
        recorder: RunRecorder | None = None,
        command_semantics: str = "git",
    ) -> str:
        result = self._run_git(workspace, args, recorder=recorder, command_semantics=command_semantics)
        if result.exit_code != 0:
            raise WorkspaceError(result.stderr.strip() or result.stdout.strip())
        return result.stdout

    def _collect_patch_stats(
        self,
        workspace: Path,
        base: str,
        added_lines: int,
        removed_lines: int,
        recorder: RunRecorder | None,
    ) -> dict[str, object]:
        status_text = self._run_git_checked(
            workspace, ["diff", "--name-status", base], recorder=recorder, command_semantics="final_patch_capture"
        )
        numstat_text = self._run_git_checked(
            workspace, ["diff", "--numstat", base], recorder=recorder, command_semantics="final_patch_capture"
        )
        summary_text = self._run_git_checked(
            workspace, ["diff", "--summary", base], recorder=recorder, command_semantics="final_patch_capture"
        )
        added_files: list[str] = []
        modified_files: list[str] = []
        deleted_files: list[str] = []
        renamed_files: list[dict[str, str]] = []
        changed_files: list[str] = []
        for line in status_text.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]
            if status.startswith("R") and len(parts) >= 3:
                old_path, new_path = parts[1], parts[2]
                renamed_files.append({"old_path": old_path, "new_path": new_path})
                changed_files.append(new_path)
                continue
            if len(parts) < 2:
                continue
            path = parts[-1]
            changed_files.append(path)
            if status == "A":
                added_files.append(path)
            elif status == "D":
                deleted_files.append(path)
            else:
                modified_files.append(path)
        binary_files = _binary_files_from_numstat(numstat_text)
        symlink_files = _symlink_files_from_summary(summary_text)
        for path in changed_files:
            candidate = workspace / path
            if candidate.exists() and candidate.is_symlink() and path not in symlink_files:
                symlink_files.append(path)
        untracked_text_files = [
            path
            for path in added_files
            if path not in binary_files
            and path not in symlink_files
            and _is_text_file(workspace / path)
        ]
        return {
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "changed_files": changed_files,
            "added_files": added_files,
            "modified_files": modified_files,
            "deleted_files": deleted_files,
            "renamed_files": renamed_files,
            "untracked_text_files": untracked_text_files,
            "binary_files": binary_files,
            "symlink_files": symlink_files,
        }

    def _assert_workspace_under_run_dir(self, workspace: Path) -> None:
        if not workspace.exists() or not workspace.is_dir():
            raise WorkspaceError(f"命令工作目录不存在：{workspace}")
        resolved_workspace = workspace.resolve()
        try:
            resolved_workspace.relative_to(self.workspaces_dir.resolve())
        except ValueError as exc:
            raise WorkspaceError(f"工作目录不在 run directory 的 workspaces 下：{workspace}") from exc

    def _host_path(self, path: str | Path, *, must_be_workspace: bool = True) -> Path:
        raw = str(path)
        if raw.startswith(CONTAINER_RUN_ROOT.as_posix()):
            rel = PurePosixPath(raw).relative_to(CONTAINER_RUN_ROOT)
            host = (self.run_dir / Path(rel.as_posix())).resolve()
        else:
            host = Path(path).resolve()
        try:
            host.relative_to(self.run_dir)
        except ValueError as exc:
            raise WorkspaceError(f"Docker backend path escapes run directory: {path}") from exc
        if must_be_workspace:
            self._assert_workspace_under_run_dir(host)
        return host

    def _container_path(self, host_path: str | Path) -> PurePosixPath:
        host = Path(host_path).resolve()
        try:
            rel = host.relative_to(self.run_dir)
        except ValueError as exc:
            raise WorkspaceError(f"path is outside Docker run mount: {host_path}") from exc
        return CONTAINER_RUN_ROOT / PurePosixPath(rel.as_posix())

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_container_execution_manifest(self) -> None:
        entries = []
        for ref in self.container_execution_facts_refs():
            payload = json.loads((self.run_dir / ref).read_text(encoding="utf-8"))
            entries.append(
                {
                    "command_id": payload["command_id"],
                    "facts_ref": ref,
                    "command_semantics": payload.get("command_semantics", "generic"),
                    "phase": SEMANTICS_TO_PHASE.get(payload.get("command_semantics", "generic")),
                    "exit_code": payload.get("exit_code"),
                    "timeout": payload.get("timeout", False),
                    "cleanup_status": payload.get("cleanup_status"),
                }
            )
        self._write_json(
            self.run_dir / "container_execution_facts" / "manifest.json",
            {
                "schema_version": "repo_harness_container_execution_manifest_v3_v0",
                "run_id": self.run_id,
                "entry_count": len(entries),
                "entries": entries,
            },
        )

    def _write_docker_phase_coverage_matrix(self) -> None:
        manifest_path = self.run_dir / "container_execution_facts" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        phase_not_applicable_reasons = dict(PHASE_NOT_APPLICABLE_REASONS)
        boundary_path = self.run_dir / "final_verifier_boundary.json"
        if boundary_path.exists():
            try:
                boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                boundary = {}
            if boundary.get("final_verifier_status") == "not_executed":
                for phase in {
                    "run_tests",
                    "test_patch_apply",
                    "model_final_patch_apply",
                    "fail_to_pass_test_execution",
                    "pass_to_pass_test_execution",
                    "final_verifier",
                }:
                    phase_not_applicable_reasons[phase] = PRE_VERL_FINAL_VERIFIER_NOT_EXECUTED_PHASE_REASON
        by_phase: dict[str, list[dict[str, Any]]] = {phase: [] for phase in REQUIRED_DOCKER_PHASES}
        supporting_entries: list[dict[str, Any]] = []
        for entry in manifest["entries"]:
            phase = entry.get("phase")
            if phase in by_phase:
                by_phase[phase].append(entry)
            else:
                supporting_entries.append(entry)
        final_test_entries = [
            *by_phase["fail_to_pass_test_execution"],
            *by_phase["pass_to_pass_test_execution"],
        ]
        if final_test_entries:
            if not by_phase["run_tests"]:
                by_phase["run_tests"] = final_test_entries
            if not by_phase["final_verifier"]:
                by_phase["final_verifier"] = final_test_entries
        phases = []
        for phase in REQUIRED_DOCKER_PHASES:
            entries = by_phase[phase]
            if entries:
                phases.append(
                    {
                        "phase": phase,
                        "status": "passed",
                        "facts_refs": [entry["facts_ref"] for entry in entries],
                        "command_semantics": sorted({entry["command_semantics"] for entry in entries}),
                    }
                )
            else:
                reason = phase_not_applicable_reasons.get(phase)
                phases.append(
                    {
                        "phase": phase,
                        "status": "not_applicable" if reason else "missing",
                        "facts_refs": [],
                        "structured_reason": reason,
                    }
                )
        if supporting_entries:
            phases.append(
                {
                    "phase": SUPPORTING_DOCKER_PHASE,
                    "status": "passed",
                    "facts_refs": [entry["facts_ref"] for entry in supporting_entries],
                    "command_semantics": sorted({entry["command_semantics"] for entry in supporting_entries}),
                    "structured_reason": "supporting container executions outside required V3 phase matrix",
                }
            )
        self._write_json(
            self.run_dir / "docker_phase_coverage_matrix.json",
            {
                "schema_version": "repo_harness_docker_phase_coverage_matrix_v3_v0",
                "run_id": self.run_id,
                "container_execution_manifest_ref": "container_execution_facts/manifest.json",
                "required_phases": REQUIRED_DOCKER_PHASES,
                "phases": phases,
            },
        )


def inspect_docker_environment() -> DockerEnvironment:
    docker_path = shutil.which("docker")
    if docker_path is None:
        raise WorkspaceError("Docker backend requested but docker CLI was not found.")
    server = _docker_json([docker_path, "version", "--format", "{{json .Server}}"])
    context = _docker_text([docker_path, "context", "show"])
    cli_version = _docker_text([docker_path, "version", "--format", "{{.Client.Version}}"], required=False)
    mem_total = int(_docker_text([docker_path, "info", "--format", "{{json .MemTotal}}"]))
    return DockerEnvironment(
        docker_path=docker_path,
        docker_context=context,
        docker_cli_version=cli_version or None,
        docker_server_version=str(server["Version"]),
        docker_desktop_version=server.get("Platform", {}).get("Name"),
        server_platform=str(server["Os"]),
        server_architecture=str(server["Arch"]),
        mem_total_bytes=mem_total,
    )


def _docker_json(command: list[str]) -> dict[str, Any]:
    text = _docker_text(command)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"Docker command did not return JSON: {shlex.join(command)}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceError(f"Docker command JSON was not an object: {shlex.join(command)}")
    return payload


def _docker_text(command: list[str], *, required: bool = True) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if required:
            raise WorkspaceError(f"Docker command failed: {shlex.join(command)}") from exc
        return ""
    if result.returncode != 0:
        if required:
            raise WorkspaceError(result.stderr.strip() or result.stdout.strip())
        return ""
    return result.stdout.strip()


def _platform_for_server_architecture(architecture: str) -> str:
    normalized = _normalize_architecture(architecture)
    if normalized == "arm64":
        return "linux/arm64"
    return "linux/amd64"


def _platform_architecture(platform: str) -> str:
    return _normalize_architecture(platform.rsplit("/", 1)[-1])


def _normalize_architecture(architecture: str) -> str:
    if architecture in {"aarch64", "arm64"}:
        return "arm64"
    if architecture in {"x86_64", "amd64"}:
        return "amd64"
    return architecture


def _docker_network_mode(policy: str) -> str:
    return "none" if policy in {"deny", "deny_agent_run", "none"} else "bridge"


def _dockerfile_for_base_image(base_image: str) -> str:
    if not base_image or any(char in base_image for char in "\r\n"):
        raise WorkspaceError("Docker build_base_image 必须是单行非空 image ref。")
    return DEFAULT_DOCKERFILE_TEMPLATE.format(base_image=base_image)


def _parse_ripgrep_json_output(
    *,
    stdout: str,
    stderr: str,
    exit_code: int | None,
    timeout: bool,
    output_mode: str,
    offset: int,
    max_matches: int,
) -> dict[str, Any]:
    rendered_matches: list[str] = []
    matched_files: set[str] = set()
    per_file_counts: dict[str, int] = {}
    parse_error_samples: list[dict[str, str]] = []
    summary_stats: dict[str, Any] = {}
    match_event_count = 0
    hidden_paths: set[str] = set()

    for raw_line in stdout.splitlines():
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            if len(parse_error_samples) < 5:
                parse_error_samples.append({"line": raw_line[:240], "error": "invalid_json_line"})
            continue
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        if event_type == "match":
            path = _rg_event_path(data)
            line_number = data.get("line_number")
            line_text = _rg_event_line_text(data)
            if path is None or not isinstance(line_number, int):
                continue
            if _is_sensitive_relative_path(Path(path)):
                hidden_paths.add(path)
                continue
            matched_files.add(path)
            submatches = data.get("submatches")
            match_increments = len(submatches) if isinstance(submatches, list) and submatches else 1
            per_file_counts[path] = per_file_counts.get(path, 0) + match_increments
            match_event_count += match_increments
            rendered_matches.append(f"{path}:{line_number}:>{line_text.rstrip()}")
        elif event_type == "context" and output_mode == "content":
            path = _rg_event_path(data)
            line_number = data.get("line_number")
            line_text = _rg_event_line_text(data)
            if path is not None and isinstance(line_number, int):
                if _is_sensitive_relative_path(Path(path)):
                    hidden_paths.add(path)
                    continue
                rendered_matches.append(f"{path}:{line_number}: {line_text.rstrip()}")
        elif event_type == "summary":
            stats = data.get("stats")
            if isinstance(stats, dict):
                summary_stats = stats

    parse_error_count = len(parse_error_samples)
    if output_mode == "files_with_matches":
        result_items = sorted(matched_files)
        total_match_count = len(result_items)
    elif output_mode == "count":
        result_items = [f"{path}:{per_file_counts[path]}" for path in sorted(per_file_counts)]
        total_match_count = sum(per_file_counts.values())
    else:
        result_items = rendered_matches
        total_match_count = match_event_count

    page = result_items[offset : offset + max_matches]
    next_offset = offset + len(page) if offset + len(page) < len(result_items) else None
    rg_completed = exit_code in {0, 1} and not timeout and parse_error_count == 0
    read_error_count = 0 if rg_completed else 1
    read_error_samples = []
    if read_error_count:
        read_error_samples.append(
            {
                "path": "<ripgrep>",
                "reason": (
                    "timeout"
                    if timeout
                    else (stderr.strip() or f"ripgrep exited with code {exit_code}")[:240]
                ),
            }
        )
    scanned_file_count = int(summary_stats.get("searches") or 0)
    scan_complete = rg_completed
    if timeout:
        scan_complete_reason = "ripgrep_timeout"
    elif parse_error_count:
        scan_complete_reason = "parse_error_detected"
    elif exit_code not in {0, 1}:
        scan_complete_reason = "ripgrep_error"
    elif next_offset is not None:
        scan_complete_reason = "result_page_truncated"
    elif total_match_count == 0:
        scan_complete_reason = "complete_no_match_all_visible_candidates_read"
    else:
        scan_complete_reason = "complete_all_visible_candidates_read"

    return {
        "matches": page,
        "files_with_matches": sorted(matched_files),
        "page_files_with_matches": sorted({item.split(":", 1)[0] for item in page})
        if output_mode != "files_with_matches"
        else page,
        "total_match_count": total_match_count,
        "candidate_file_count": scanned_file_count,
        "scanned_candidate_file_count": scanned_file_count,
        "scanned_file_count": scanned_file_count,
        "searched_file_count": scanned_file_count,
        "scanned_file_limit": scanned_file_count,
        "unscanned_file_count": 0,
        "scan_limit_reached": False,
        "scan_complete": scan_complete,
        "scan_complete_reason": scan_complete_reason,
        "result_limit_reached": next_offset is not None,
        "matched_file_count": len(matched_files),
        "hidden_path_count": len(hidden_paths),
        "skipped_hidden_count": len(hidden_paths),
        "skipped_hidden_path_count": len(hidden_paths),
        "symlink_outside_workspace_count": 0,
        "skipped_symlink_count": 0,
        "workspace_boundary_or_missing_count": 0,
        "read_error_count": read_error_count,
        "read_error_samples": read_error_samples,
        "visibility_error_count": 0,
        "visibility_error_samples": [],
        "backend_mismatch_detected": False,
        "truncated": bool(next_offset is not None or not scan_complete),
        "next_offset": next_offset,
        "output_mode": output_mode,
        "rg_exit_code": exit_code,
        "rg_timeout": timeout,
        "rg_stderr_preview": stderr[:500],
        "rg_summary_stats": summary_stats,
        "parse_error_count": parse_error_count,
        "parse_error_samples": parse_error_samples,
    }


def _rg_event_path(data: dict[str, Any]) -> str | None:
    path = data.get("path")
    if isinstance(path, dict):
        text = path.get("text")
        if isinstance(text, str):
            return text
    return None


def _rg_event_line_text(data: dict[str, Any]) -> str:
    lines = data.get("lines")
    if isinstance(lines, dict):
        text = lines.get("text")
        if isinstance(text, str):
            return text
    return ""


def _rg_resource_limited(stderr: str, stdout: str) -> bool:
    combined = f"{stderr}\n{stdout}".lower()
    return any(pattern in combined for pattern in RG_RESOURCE_ERROR_PATTERNS)


def _safe_container_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "-", value)
    return safe[:120].strip("-") or "repo-harness-container"


def _requires_shell_command(command: str | list[str]) -> bool:
    if not isinstance(command, str):
        return False
    stripped = command.strip()
    if not stripped:
        return False
    if any(marker in stripped for marker in ("&&", "||", ";", "|", "\n", "$(", "`")):
        return True
    if stripped.startswith((". ", "source ", "export ", "cd ")):
        return True
    try:
        first = shlex.split(stripped)[0]
    except ValueError:
        return True
    if "=" not in first:
        return False
    name = first.split("=", 1)[0]
    return bool(name) and (name[0].isalpha() or name[0] == "_") and all(
        char.isalnum() or char == "_" for char in name
    )


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
