"""Task Adapter：读取、校验和规范化任务定义。"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import TaskValidationError
from repo_harness.tasks.schemas import RunnableTask, TaskDefinition, VerifierConfig


class LoadedTask:
    """Task Adapter 的输出对象。"""

    def __init__(
        self,
        *,
        definition: TaskDefinition,
        runnable_task: RunnableTask,
        verifier_config: VerifierConfig,
        task_path: Path,
    ) -> None:
        self.definition = definition
        self.runnable_task = runnable_task
        self.verifier_config = verifier_config
        self.task_path = task_path


class TaskAdapter:
    """只负责任务定义读取、静态校验和规范化。"""

    def load(self, task_path: str | Path) -> LoadedTask:
        resolved_task_path = Path(task_path).resolve()
        try:
            raw: Any = yaml.safe_load(resolved_task_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise TaskValidationError(f"无法读取任务定义：{resolved_task_path}") from exc
        if not isinstance(raw, dict):
            raise TaskValidationError("任务定义 YAML 顶层必须是 mapping。")
        try:
            definition = TaskDefinition.model_validate(raw)
        except ValidationError as exc:
            raise TaskValidationError(str(exc)) from exc

        repo_path = self._resolve_repo_path(definition.repo, resolved_task_path)
        normalized_definition = definition.model_copy(update={"repo": repo_path.as_posix()})
        self._validate_commands(normalized_definition, repo_path)
        verifier_config = normalized_definition.to_verifier_config()
        runnable = RunnableTask.from_definition(normalized_definition)
        return LoadedTask(
            definition=normalized_definition,
            runnable_task=runnable,
            verifier_config=verifier_config,
            task_path=resolved_task_path,
        )

    def _resolve_repo_path(self, repo: str, task_path: Path) -> Path:
        raw_path = Path(repo)
        candidate = raw_path if raw_path.is_absolute() else (task_path.parent / raw_path)
        resolved = candidate.resolve()
        fixture_root = self._fixture_repo_root(task_path)
        try:
            resolved.relative_to(fixture_root)
        except ValueError as exc:
            raise TaskValidationError(
                f"任务 repo 必须位于 fixture 根目录 {fixture_root} 内：{repo}"
            ) from exc
        if not resolved.exists() or not resolved.is_dir():
            raise TaskValidationError(f"任务 repo 不存在或不是目录：{resolved}")
        return resolved

    def _fixture_repo_root(self, task_path: Path) -> Path:
        for parent in [task_path.parent, *task_path.parents]:
            if parent.name == "fixtures":
                candidate = parent / "repos"
                if candidate.exists() and candidate.is_dir():
                    return candidate.resolve()
        raise TaskValidationError(f"无法从任务路径定位 fixture repos 根目录：{task_path}")

    def _validate_commands(self, definition: TaskDefinition, repo_path: Path) -> None:
        _validate_test_command(definition.test_command)
        _validate_setup_command(definition.setup_command, repo_path)


def load_task(task_path: str | Path) -> LoadedTask:
    return TaskAdapter().load(task_path)


_FORBIDDEN_SHELL_FRAGMENTS = ["|", ">", "<", "&&", "||", ";", "`", "$", "\n", "&"]
_PYTHON_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def _validate_test_command(command: str) -> None:
    parts = _split_static_command(command, field_name="test_command")
    if parts[0] == "pytest":
        _reject_unsafe_command_args(parts[1:], field_name="test_command")
        return
    if parts[:3] == ["python", "-m", "pytest"]:
        _reject_unsafe_command_args(parts[3:], field_name="test_command")
        return
    raise TaskValidationError(
        "test_command 第一版只允许 pytest 或 python -m pytest 形式。"
    )


def _validate_setup_command(command: str | None, repo_path: Path) -> None:
    if command is None or not command.strip():
        return
    parts = _split_static_command(command, field_name="setup_command")
    if parts[:2] == ["python", "-m"] and len(parts) >= 3:
        module = parts[2]
        if not _PYTHON_MODULE_RE.fullmatch(module):
            raise TaskValidationError("setup_command 包含不安全的 Python module 名称。")
        _reject_unsafe_command_args(parts[3:], field_name="setup_command")
        return
    if len(parts) >= 2 and parts[0] == "python" and parts[1].endswith(".py"):
        _reject_unsafe_command_args(parts[1:], field_name="setup_command")
        script_path = _resolve_command_path(repo_path, parts[1], field_name="setup_command")
        if not script_path.exists() or not script_path.is_file():
            raise TaskValidationError(f"setup_command 脚本不存在：{parts[1]}")
        return
    raise TaskValidationError(
        "setup_command 第一版只允许 python -m <module> 或 python <script.py> 形式。"
    )


def _split_static_command(command: str, *, field_name: str) -> list[str]:
    if any(fragment in command for fragment in _FORBIDDEN_SHELL_FRAGMENTS):
        raise TaskValidationError(f"{field_name} 包含不支持的 shell 语法。")
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise TaskValidationError(f"{field_name} 无法解析：{exc}") from exc
    if not parts:
        raise TaskValidationError(f"{field_name} 不能为空。")
    return parts


def _reject_unsafe_command_args(args: list[str], *, field_name: str) -> None:
    for arg in args:
        if any(fragment in arg for fragment in _FORBIDDEN_SHELL_FRAGMENTS):
            raise TaskValidationError(f"{field_name} 包含不支持的 shell 语法。")
        if arg.startswith("-"):
            continue
        if arg in {".", ":", "::"}:
            continue
        path_candidate = Path(arg.split("::", 1)[0])
        if path_candidate.is_absolute() or ".." in path_candidate.parts:
            raise TaskValidationError(f"{field_name} 参数路径不能是绝对路径或包含 ..。")


def _resolve_command_path(repo_path: Path, requested_path: str, *, field_name: str) -> Path:
    raw = Path(requested_path)
    if raw.is_absolute() or ".." in raw.parts:
        raise TaskValidationError(f"{field_name} 脚本路径不能是绝对路径或包含 ..。")
    resolved = (repo_path / raw).resolve()
    try:
        resolved.relative_to(repo_path.resolve())
    except ValueError as exc:
        raise TaskValidationError(f"{field_name} 脚本路径越过 repo 边界。") from exc
    return resolved
