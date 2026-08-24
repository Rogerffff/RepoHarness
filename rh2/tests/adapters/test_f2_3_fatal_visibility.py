"""F2-3 联合终核 P1-1 回归（独立文件）。"""

from __future__ import annotations

import asyncio

import pytest

from repoharness2.adapters.slime.async_worker import (
    BoundedDeliveryQueue,
    ContinuousExecutionWorker,
    ExecutionTaskSpec,
    FatalExecutionInfrastructureError,
    WorkerHalted,
)


async def test_fatal_visible_before_cleanup_completes():
    """F2-3 联合终核 P1-1：Fatal 在进入异步 cleanup 前经 task-local
    notifier 同步置 halt——cleanup 窗口内 halt_reason 已可见（好组无法
    在窗口内交付），cleanup 结束后 WorkerHalted 同因。"""

    from repoharness2.adapters.slime.async_worker import fatal_halt_notifier

    cleanup_blocker = asyncio.Event()
    entered_cleanup = asyncio.Event()

    async def execute(spec):
        # 镜像 generate 的新行为：catch 中先同步通知，再走异步 finally
        try:
            raise FatalExecutionInfrastructureError("probe_fatal", "注入")
        except FatalExecutionInfrastructureError as exc:
            notifier = fatal_halt_notifier.get()
            assert notifier is not None  # _guarded_execute 已安装
            notifier(exc)
            entered_cleanup.set()
            await cleanup_blocker.wait()  # 模拟 drop_session/容器清理窗口
            raise

    specs = [ExecutionTaskSpec(rollout_execution_id="exec_f", prompt_group_id="g",
                               member_slot=0)]
    queue = list(specs)
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=4),
        failure_sink=lambda spec, exc: None,
        concurrency=1,
    )
    stop = asyncio.Event()
    run_task = asyncio.create_task(worker.run(stop))
    await asyncio.wait_for(entered_cleanup.wait(), timeout=5)
    # cleanup 仍阻塞中：halt 已对三门可见（P1-1 的窗口关闭证明）
    assert worker.halt_reason == "fatal_infrastructure:probe_fatal"
    cleanup_blocker.set()
    with pytest.raises(WorkerHalted, match="probe_fatal"):
        await asyncio.wait_for(run_task, timeout=10)
