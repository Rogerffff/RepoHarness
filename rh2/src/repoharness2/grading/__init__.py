"""repoharness2.grading：SWEGradingManager 最小版（S1-4，框架无关层）。

组成：

- manager.py  评分本体：cleaned patch 导出（A7 条 1/3/4）→ fresh 容器
              clean checkout（P6/P9）→ 重放 → 官方 eval → envpack parser →
              GradingReport（三分归因 + infra 族 reward=None + F5 计时）。
              prepare（P2 预热）/ grade / gc（P1 记账回收）+ startup 孤儿清扫。
- queue.py    有界评分队列（P11）：默认并发 4 / 队列 8（F5 用户收紧版），
              反压事件 + 排队等待计时。

**硬约束（与 envpack 同纪律，单测钉死）**：本包 import 时不得引入
verifiers / swebench——manager 同时服务 verifiers 薄壳与 S1-6 slime 绑定。
"""

from repoharness2.grading.manager import (
    DEFAULT_SWE_FORBIDDEN_GLOBS,
    DEFAULT_SWE_TEST_GLOBS,
    EXPORT_PATCH_SCRIPT,
    UNPARSEABLE_SEGMENT_LABEL,
    CleanedPatch,
    ExecResult,
    GradingEnvSpec,
    GradingInfraError,
    GradingManagerConfig,
    HostWorkspace,
    HygieneRules,
    PatchSegment,
    SWEGradingManager,
    WorkspaceExportError,
    WorkspaceRunner,
    build_swe_grading_spec,
    clean_patch,
    export_cleaned_patch,
    patch_touched_paths,
    run_docker,
    split_patch_segments,
)
from repoharness2.grading.queue import (
    BACKPRESSURE_REASON_CODE,
    BackpressureEvent,
    GradingQueue,
    GradingQueueConfig,
)

__all__ = [
    "BACKPRESSURE_REASON_CODE",
    "DEFAULT_SWE_FORBIDDEN_GLOBS",
    "DEFAULT_SWE_TEST_GLOBS",
    "EXPORT_PATCH_SCRIPT",
    "UNPARSEABLE_SEGMENT_LABEL",
    "BackpressureEvent",
    "CleanedPatch",
    "ExecResult",
    "GradingEnvSpec",
    "GradingInfraError",
    "GradingManagerConfig",
    "GradingQueue",
    "GradingQueueConfig",
    "HostWorkspace",
    "HygieneRules",
    "PatchSegment",
    "SWEGradingManager",
    "WorkspaceExportError",
    "WorkspaceRunner",
    "build_swe_grading_spec",
    "clean_patch",
    "export_cleaned_patch",
    "patch_touched_paths",
    "run_docker",
    "split_patch_segments",
]
