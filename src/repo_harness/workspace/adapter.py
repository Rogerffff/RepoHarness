"""本地进程 Workspace Adapter。"""

from __future__ import annotations

import os
import fnmatch
import shlex
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from repo_harness.errors import WorkspaceError
from repo_harness.tasks import RunnableTask
from repo_harness.trajectory import ArtifactRef, RunRecorder
from repo_harness.workspace.materialization import SourceCheckout, materialize_source
from repo_harness.workspace.protocol import WorkspaceBackend
from repo_harness.workspace.schemas import DependencyState, ExecutionResult, RunWorkspace

DEFAULT_EXCLUDED_DIFF_PATHS = [
    ".pytest_cache/",
    ".coverage",
    "coverage/",
    "dist/",
    "build/",
    "node_modules/",
    ".mypy_cache/",
    "__pycache__/",
    "*.pyc",
    ".env",
    ".env.*",
    "*.env",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".aws/",
    ".config/gh/",
    ".config/gcloud/",
    ".ssh/",
    ".gnupg/",
    "pip.conf",
    "pip.ini",
    ".pip/pip.conf",
    "credentials",
    "credentials.json",
    "*credentials*.json",
    "token",
    "token.*",
    "secret",
    "secret.*",
    "secrets.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*.cer",
]

SENSITIVE_NAMES = {
    ".git",
    ".env",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "pip.conf",
    "pip.ini",
    "credentials",
    "credentials.json",
    "token",
    "token.json",
    "token.txt",
    "secret",
    "secret.json",
    "secret.txt",
    "secrets.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SENSITIVE_DIRS = {".aws", ".ssh", ".gnupg"}

SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".crt", ".cer"}

SENSITIVE_RELATIVE_PARTS = {
    (".aws", "credentials"),
    (".config", "gh", "hosts.yml"),
    (".config", "gh", "config.yml"),
    (".config", "gcloud", "application_default_credentials.json"),
    (".pip", "pip.conf"),
}


@dataclass(frozen=True)
class PatchCapture:
    patch_path: Path
    diff_path: Path
    patch_artifact_ref: ArtifactRef
    diff_artifact_ref: ArtifactRef
    patch_text: str
    diff_text: str
    added_lines: int
    removed_lines: int
    patch_stats: dict[str, object]


class LocalWorkspaceAdapter:
    """本地进程工作区生命周期和执行边界。"""

    backend = WorkspaceBackend.local_process

    def __init__(
        self,
        *,
        run_id: str,
        run_dir: str | Path,
        default_command_timeout_sec: float = 120,
        keep_workspace: bool = True,
    ) -> None:
        self.run_id = run_id
        self.run_dir = Path(run_dir)
        self.workspaces_dir = self.run_dir / "workspaces"
        self.default_command_timeout_sec = default_command_timeout_sec
        self.keep_workspace = keep_workspace
        self.last_source_checkout: SourceCheckout | None = None
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

    def create_source_checkout(self, task: RunnableTask) -> Path:
        source_path = self.workspaces_dir / "source_checkout"
        checkout = materialize_source(task, source_path)
        self.last_source_checkout = checkout
        return checkout.root

    def create_setup_workspace(self, source_checkout: str | Path) -> Path:
        setup_path = self.workspaces_dir / "setup_workspace"
        _copy_tree(Path(source_checkout), setup_path)
        return setup_path

    def capture_dependency_state(
        self,
        *,
        strategy: str = "none",
        excluded_diff_paths: list[str] | None = None,
    ) -> DependencyState:
        if strategy not in {"none", "rerun_setup"}:
            raise WorkspaceError(f"第一版 Workspace Adapter 不支持 dependency strategy：{strategy}")
        return DependencyState(
            strategy=strategy,
            cache_key=f"{self.run_id}:{strategy}",
            excluded_diff_paths=excluded_diff_paths or list(DEFAULT_EXCLUDED_DIFF_PATHS),
            created_after_setup_command=True,
            excludes_baseline_side_effects=True,
        )

    def create_agent_workspace(
        self,
        *,
        task: RunnableTask,
        source_checkout: str | Path,
        dependency_state: DependencyState,
        setup_command: str | None = None,
        recorder: RunRecorder,
    ) -> RunWorkspace:
        workspace_path = self.workspaces_dir / "agent_workspace"
        _copy_tree(Path(source_checkout), workspace_path)
        self.restore_dependency_state(workspace_path, dependency_state, setup_command, recorder)
        agent_start_snapshot = self.create_agent_start_snapshot(
            workspace_path, dependency_state.excluded_diff_paths, recorder
        )
        return RunWorkspace(
            run_id=self.run_id,
            workspace_path=workspace_path.as_posix(),
            repo_base_commit=task.base_commit,
            execution_mode="local_process",
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
        recorder: RunRecorder,
    ) -> Path:
        verification_path = self.workspaces_dir / "verification_workspace"
        _copy_tree(Path(source_checkout), verification_path)
        self.restore_dependency_state(verification_path, dependency_state, setup_command, recorder)
        self.create_agent_start_snapshot(verification_path, dependency_state.excluded_diff_paths, recorder)
        result = self.apply_patch(verification_path, final_patch_path, recorder=recorder)
        if result.exit_code != 0 or result.timeout:
            raise WorkspaceError(f"final.patch 无法应用：{result.stderr_preview or result.stdout_preview}")
        return verification_path

    def restore_dependency_state(
        self,
        workspace_path: str | Path,
        dependency_state: DependencyState,
        setup_command: str | None,
        recorder: RunRecorder | None = None,
    ) -> None:
        if dependency_state.strategy == "none":
            return
        if dependency_state.strategy == "rerun_setup":
            if not setup_command:
                raise WorkspaceError("dependency_state=rerun_setup 需要 setup_command。")
            result = self.run_command(workspace_path, setup_command, recorder=recorder)
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
        workspace = Path(workspace_path)
        self._ensure_git_baseline(
            workspace, excluded_diff_paths or list(DEFAULT_EXCLUDED_DIFF_PATHS), recorder
        )
        result = self._run_git(workspace, ["rev-parse", "HEAD"], recorder=recorder)
        if result.returncode != 0:
            raise WorkspaceError(result.stderr.strip() or "无法读取 agent_start_snapshot。")
        return result.stdout.strip()

    def capture_final_patch(self, run_workspace: RunWorkspace, *, recorder: RunRecorder) -> PatchCapture:
        workspace = Path(run_workspace.workspace_path)
        base = run_workspace.agent_diff_base or run_workspace.agent_start_snapshot
        if not base:
            raise WorkspaceError("RunWorkspace 缺少 agent_start_snapshot，无法冻结 final.patch。")
        self._refresh_intent_to_add(workspace, recorder)
        patch_text = self._run_git_checked(workspace, ["diff", "--binary", base], recorder=recorder)
        diff_text = self._run_git_checked(workspace, ["diff", base], recorder=recorder)
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
    ) -> ExecutionResult:
        patch_text = Path(patch_path).read_text(encoding="utf-8")
        if not patch_text.strip():
            return ExecutionResult(exit_code=0, command_semantics="git_apply")
        if recorder is None:
            raise WorkspaceError("apply_patch 必须提供 RunRecorder 以保存命令输出 artifact。")
        return self.run_command(
            workspace_path,
            ["git", "apply", "--whitespace=nowarn", str(Path(patch_path).resolve())],
            recorder=recorder,
            command_semantics="git_apply",
        )

    def resolve_workspace_path(
        self,
        workspace_path: str | Path,
        requested_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        workspace = Path(workspace_path).resolve()
        self._assert_workspace_under_run_dir(workspace)
        raw_path = Path(requested_path)
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
        _reject_sensitive_path(resolved.relative_to(workspace))
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
        workspace = Path(workspace_path).resolve()
        match_all = pattern in {None, "", "**/*"}
        files: list[str] = []
        paths = root_path.rglob("*") if root_path.is_dir() else [root_path]
        for path in sorted(paths):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(workspace).as_posix()
            if self.is_sensitive_relative_path(rel):
                continue
            if match_all or fnmatch.fnmatch(rel, str(pattern)):
                files.append(rel)
        return files

    def read_text(self, workspace_path: str | Path, requested_path: str | Path) -> str:
        path = self.resolve_workspace_path(workspace_path, requested_path, must_exist=True)
        return path.read_text(encoding="utf-8")

    def write_text(self, workspace_path: str | Path, requested_path: str | Path, content: str) -> None:
        path = self.resolve_workspace_path(workspace_path, requested_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

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
        workspace = Path(workspace_path).resolve()
        self._assert_workspace_under_run_dir(workspace)
        if recorder is None:
            raise WorkspaceError("run_command 必须提供 RunRecorder 以保存 stdout/stderr artifact。")
        command_args, command_display, use_shell = _prepare_command(command, allow_shell=allow_shell)
        started = time.monotonic()
        timeout = timeout_sec if timeout_sec is not None else self.default_command_timeout_sec
        process = subprocess.Popen(
            command_args,
            cwd=workspace,
            shell=use_shell,
            env=_command_env(),
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
        duration_ms = int((time.monotonic() - started) * 1000)
        artifact_ref = recorder.write_artifact(
            "command_output",
            f"$ {command_display}\n\n[stdout]\n{stdout}\n\n[stderr]\n{stderr}",
            {"retention_policy": "keep"},
        )
        return ExecutionResult(
            exit_code=process.returncode,
            stdout_preview=_preview(stdout),
            stderr_preview=_preview(stderr),
            output_artifact_ref=artifact_ref,
            duration_ms=duration_ms,
            timeout=timed_out,
            command_semantics=command_semantics,
            exit_code_interpretation="timeout" if timed_out else "process_exit_code",
        )

    def cleanup_workspaces(self) -> None:
        if self.keep_workspace:
            return
        if self.workspaces_dir.exists():
            shutil.rmtree(self.workspaces_dir)

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
        if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout.lower():
            if "nothing to commit" not in commit_result.stderr.lower():
                raise WorkspaceError(commit_result.stderr.strip() or commit_result.stdout.strip())

    def _refresh_intent_to_add(self, workspace: Path, recorder: RunRecorder | None = None) -> None:
        self._run_git_checked(workspace, ["add", "-N", "."], recorder=recorder)

    def _assert_workspace_under_run_dir(self, workspace: Path) -> None:
        if not workspace.exists() or not workspace.is_dir():
            raise WorkspaceError(f"命令工作目录不存在：{workspace}")
        resolved_workspace = workspace.resolve()
        try:
            resolved_workspace.relative_to(self.workspaces_dir.resolve())
        except ValueError as exc:
            raise WorkspaceError(f"工作目录不在 run directory 的 workspaces 下：{workspace}") from exc

    def _run_git(
        self,
        workspace: Path,
        args: list[str],
        *,
        recorder: RunRecorder | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self._assert_workspace_under_run_dir(workspace)
        command = ["git", *args]
        try:
            result = subprocess.run(
                command,
                cwd=workspace,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.default_command_timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            if recorder is not None:
                recorder.write_artifact(
                    "git_command_output",
                    f"$ {shlex.join(command)}\n\n[stdout]\n{stdout}\n\n[stderr]\n{stderr}",
                    {"retention_policy": "keep"},
                )
            raise WorkspaceError(f"git 命令超时：{shlex.join(command)}") from exc
        if recorder is not None:
            recorder.write_artifact(
                "git_command_output",
                f"$ {shlex.join(command)}\n\n[stdout]\n{result.stdout}\n\n[stderr]\n{result.stderr}",
                {"retention_policy": "keep"},
            )
        return result

    def _run_git_checked(
        self,
        workspace: Path,
        args: list[str],
        *,
        recorder: RunRecorder | None = None,
    ) -> str:
        result = self._run_git(workspace, args, recorder=recorder)
        if result.returncode != 0:
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
            workspace, ["diff", "--name-status", base], recorder=recorder
        )
        numstat_text = self._run_git_checked(
            workspace, ["diff", "--numstat", base], recorder=recorder
        )
        summary_text = self._run_git_checked(
            workspace, ["diff", "--summary", base], recorder=recorder
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


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise WorkspaceError(f"工作区已存在：{destination}")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"),
    )


def _prepare_command(command: str | list[str], *, allow_shell: bool) -> tuple[str | list[str], str, bool]:
    if isinstance(command, list):
        if not command:
            raise WorkspaceError("命令不能为空。")
        return command, shlex.join(command), False
    if allow_shell:
        return command, command, True
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise WorkspaceError(f"无法解析命令参数：{exc}") from exc
    if not parts:
        raise WorkspaceError("命令不能为空。")
    return parts, shlex.join(parts), False


def _reject_sensitive_path(relative_path: Path) -> None:
    if _is_sensitive_relative_path(relative_path):
        raise WorkspaceError(f"拒绝访问敏感路径：{relative_path}")


def _is_sensitive_relative_path(relative_path: Path) -> bool:
    parts = tuple(part.lower() for part in relative_path.parts)
    for sensitive_parts in SENSITIVE_RELATIVE_PARTS:
        for index in range(0, len(parts) - len(sensitive_parts) + 1):
            if parts[index : index + len(sensitive_parts)] == sensitive_parts:
                return True
    for part in parts:
        if part in SENSITIVE_DIRS:
            return True
        if part in SENSITIVE_NAMES or part.startswith(".env"):
            return True
        if "id_rsa" in part or "id_ed25519" in part:
            return True
    if relative_path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return False


def _count_diff_lines(diff_text: str) -> tuple[int, int]:
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def _binary_files_from_numstat(numstat_text: str) -> list[str]:
    binary_files: list[str] = []
    for line in numstat_text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0] == "-" and parts[1] == "-":
            binary_files.append(parts[-1])
    return binary_files


def _symlink_files_from_summary(summary_text: str) -> list[str]:
    symlink_files: list[str] = []
    for line in summary_text.splitlines():
        if "mode 120000" not in line:
            continue
        parts = line.split()
        if parts:
            symlink_files.append(parts[-1])
    return symlink_files


def _is_text_file(path: Path) -> bool:
    if not path.exists() or not path.is_file() or path.is_symlink():
        return False
    try:
        with path.open("r", encoding="utf-8") as file:
            file.read(4096)
    except UnicodeDecodeError:
        return False
    return True


def _preview(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[truncated]"


def _command_env() -> dict[str, str]:
    source_env = os.environ
    env = {
        key: source_env[key]
        for key in ("TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE")
        if key in source_env
    }
    python_bin_dir = str(Path(sys.executable).parent)
    env["PATH"] = f"{python_bin_dir}{os.pathsep}{source_env.get('PATH', '')}"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONNOUSERSITE"] = "1"
    return env
