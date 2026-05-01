"""Task Adapter：读取、校验和规范化任务定义。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import TaskValidationError
from repo_harness.tasks.command_policy import (
    validate_setup_command,
    validate_test_command,
)
from repo_harness.tasks.schemas import (
    FixtureRepositorySource,
    LocalArchiveSource,
    LocalRepositorySource,
    PublicSnapshotSource,
    RunnableTask,
    TaskDefinition,
    VerifierConfig,
)


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

        normalized_definition = self._normalize_repo_source(definition, resolved_task_path)
        repo_path_for_command_checks = self._command_validation_repo_path(normalized_definition)
        self._validate_commands(normalized_definition, repo_path_for_command_checks)
        verifier_config = normalized_definition.to_verifier_config()
        runnable = RunnableTask.from_definition(normalized_definition)
        return LoadedTask(
            definition=normalized_definition,
            runnable_task=runnable,
            verifier_config=verifier_config,
            task_path=resolved_task_path,
        )

    def _normalize_repo_source(self, definition: TaskDefinition, task_path: Path) -> TaskDefinition:
        if definition.repo_source_spec is None:
            repo_path = self._resolve_repo_path(definition.repo, task_path)
            source_spec = FixtureRepositorySource(
                path=repo_path.as_posix(),
                base_commit=definition.base_commit,
                synthetic_base_id=None if definition.base_commit else f"{definition.id}_synthetic_base",
            )
            return definition.model_copy(
                update={
                    "repo": repo_path.as_posix(),
                    "repo_source_spec": source_spec,
                }
            )

        source = definition.repo_source_spec
        if isinstance(source, LocalArchiveSource):
            archive_path = _resolve_relative_path(source.archive_path, task_path)
            normalized = source.model_copy(update={"archive_path": archive_path.as_posix()})
            return definition.model_copy(
                update={
                    "repo": archive_path.as_posix(),
                    "repo_source_spec": normalized,
                    "source_archive_sha256": source.archive_sha256,
                    "base_commit": source.base_commit or definition.base_commit,
                }
            )
        if isinstance(source, LocalRepositorySource):
            source_path = _resolve_relative_path(source.source_path, task_path)
            normalized = source.model_copy(update={"source_path": source_path.as_posix()})
            return definition.model_copy(
                update={
                    "repo": source_path.as_posix(),
                    "repo_source_spec": normalized,
                    "base_commit": source.base_commit or source.current_commit or definition.base_commit,
                }
            )
        if isinstance(source, PublicSnapshotSource):
            updates: dict[str, Any] = {}
            if source.archive_path is not None:
                archive_path = _resolve_relative_path(source.archive_path, task_path)
                updates["archive_path"] = archive_path.as_posix()
                repo = archive_path.as_posix()
            else:
                repo = source.remote_url
            normalized = source.model_copy(update=updates)
            return definition.model_copy(
                update={
                    "repo": repo,
                    "repo_source_spec": normalized,
                    "source_archive_sha256": source.archive_sha256,
                    "base_commit": source.commit_sha,
                }
            )
        raise TaskValidationError(f"不支持的 repo_source_spec 类型：{type(source).__name__}")

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

    def _validate_commands(self, definition: TaskDefinition, repo_path: Path | None) -> None:
        validate_test_command(definition.test_command)
        validate_setup_command(definition.setup_command, repo_path)

    def _command_validation_repo_path(self, definition: TaskDefinition) -> Path | None:
        source = definition.repo_source_spec
        if isinstance(source, (FixtureRepositorySource, LocalRepositorySource)):
            return Path(definition.repo)
        if isinstance(source, (LocalArchiveSource, PublicSnapshotSource)):
            return None
        return Path(definition.repo)


def load_task(task_path: str | Path) -> LoadedTask:
    return TaskAdapter().load(task_path)


def _resolve_relative_path(path: str, task_path: Path) -> Path:
    raw = Path(path)
    candidate = raw if raw.is_absolute() else (task_path.parent / raw)
    resolved = candidate.resolve()
    if not resolved.exists():
        raise TaskValidationError(f"repo source path 不存在：{resolved}")
    return resolved
