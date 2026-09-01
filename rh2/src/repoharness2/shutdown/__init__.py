"""rh2 关停链与资源闭包（W5a）。

- `chain`：有界关停执行器 + 任务面关闭状态 + 在飞执行取消（只记事实）+ 信号触发；
- `resource_closure`：内存保守上界 / 随 attempt 增长的集合盘点 / fsync 延迟一次性取数；
- `run_residue`：launch trap 用的 run-label 兜底清理与无残留检查（纯 stdlib，可按文件运行）。

具体组件的关停顺序装配在 `repoharness2.adapters.slime.bringup.BringupService.close`。
"""

from repoharness2.shutdown.chain import (
    CANCELLED_EXECUTION_TERMINATION_KIND,
    CancelledExecutionFact,
    InFlightExecutionFact,
    LifecycleState,
    ServiceClosedError,
    ShutdownReport,
    ShutdownStep,
    ShutdownStepResult,
    ShutdownTimeouts,
    Skipped,
    close_inflight_executions,
    install_signal_shutdown,
    run_shutdown_chain,
)
from repoharness2.shutdown.resource_closure import (
    GROWING_COLLECTIONS,
    MemoryBoundInputs,
    collect_growth_facts,
    estimate_memory_upper_bound,
    measure_fsync_latency,
    resource_closure_facts,
    write_resource_closure_facts,
)

__all__ = [
    "CANCELLED_EXECUTION_TERMINATION_KIND",
    "GROWING_COLLECTIONS",
    "CancelledExecutionFact",
    "InFlightExecutionFact",
    "LifecycleState",
    "MemoryBoundInputs",
    "ServiceClosedError",
    "ShutdownReport",
    "ShutdownStep",
    "ShutdownStepResult",
    "ShutdownTimeouts",
    "Skipped",
    "close_inflight_executions",
    "collect_growth_facts",
    "estimate_memory_upper_bound",
    "install_signal_shutdown",
    "measure_fsync_latency",
    "resource_closure_facts",
    "run_shutdown_chain",
    "write_resource_closure_facts",
]
