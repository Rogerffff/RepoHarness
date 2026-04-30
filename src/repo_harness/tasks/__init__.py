"""任务定义和任务适配器模块。"""

from repo_harness.tasks.adapter import LoadedTask, TaskAdapter, load_task
from repo_harness.tasks.schemas import (
    DecontaminationMetadata,
    EnvironmentSpec,
    LockfileHash,
    MutationRule,
    RunnableTask,
    TaskDefinition,
    TaskTimeouts,
    VerifierConfig,
    VisibilityPolicy,
)

__all__ = [
    "DecontaminationMetadata",
    "EnvironmentSpec",
    "LoadedTask",
    "LockfileHash",
    "MutationRule",
    "RunnableTask",
    "TaskAdapter",
    "TaskDefinition",
    "TaskTimeouts",
    "VerifierConfig",
    "VisibilityPolicy",
    "load_task",
]
