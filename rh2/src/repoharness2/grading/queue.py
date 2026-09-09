"""有界评分队列（P11 + F5 用户收紧版：默认并发 4、队列 8，全部可配置）。

为什么必须有界：评分吞吐 < rollout 完成速率时，无界队列会把积压变成
静默的内存增长与无限延迟。本队列的语义（S1 最小版）：

  - 并发 worker 数 = concurrency（默认 4）：同时进行的评分动作上限；
  - 等待队列容量 = queue_size（默认 8 = 2x 并发，A9/F5）；
  - 队列打满时的策略 = block_submitter：submit() 在 put 处阻塞提交方，
    等价于反压 rollout 准入（P11 列出的三种处理里最保守的一种，
    defer 评分 / 降级 audit_only 留给 S2 之后按数据决定）；
  - 每次打满都产出一条 BackpressureEvent 事实记录——reason_code 直接可写进
    EligibilityReport.reason_codes，event 本身是 gate 的 evidence 来源；
    同时该次评分的 GradingTimingRecord.backpressure_triggered=True。

排队等待计时口径：从 submit() 被调用（含被反压阻塞的时间）到 worker 取出
条目开始评分为止，写进 GradingTimingRecord.queue_wait_seconds（F5 五类计时
之外的资源事实，"实测稳定后再把并发 4 升 8"的决策输入）。
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import AwareDatetime, Field

from collections.abc import Callable

from repoharness2.contracts import GradingReport, NonEmptyStr, StrictModel
from repoharness2.grading.manager import (
    BaselineIntegrityError,
    GradingEnvSpec,
    SWEGradingManager,
    WorkspaceRunner,
)

# EligibilityReport.reason_codes 直接可用的理由码（SafeIdentifier 形态）。
BACKPRESSURE_REASON_CODE = "grading_backpressure_queue_full"


class BackpressureEvent(StrictModel):
    """一次"评分队列打满"的事实记录（P11 反压观测点）。

    消费方：EligibilityGate（S1-5）把 reason_code 写进相关轨迹的
    EligibilityReport；F5 吞吐画像统计打满频率决定是否升并发。
    注册方式（S1-9 定案，codex#5）：经 `repoharness2.registry.FULL_SCHEMA_REGISTRY`
    在 CLI 层聚合注册（依赖方向保持 grading -> contracts 不反转），
    `inspect-rh2-artifact` 可直接校验本对象的 JSON 工件。
    """

    schema_id: Literal["rh2.grading_backpressure_event.v1"] = Field(
        default="rh2.grading_backpressure_event.v1", description="schema 判别字段。"
    )
    event_id: NonEmptyStr = Field(description="事件 id（EligibilityReport.evidence_refs 可指向它）。")
    trajectory_id: NonEmptyStr = Field(description="被反压的评分请求所属轨迹 id。")
    task_id: NonEmptyStr = Field(description="任务 id。")
    queue_capacity: int = Field(gt=0, description="等待队列容量（默认 8，F5）。")
    queue_depth: int = Field(ge=0, description="事件发生瞬间的队列深度（打满时 == capacity）。")
    active_grading_count: int = Field(ge=0, description="事件发生瞬间正在评分中的请求数。")
    concurrency_limit: int = Field(gt=0, description="评分并发上限（默认 4，F5）。")
    policy_applied: Literal["block_submitter"] = Field(
        default="block_submitter",
        description="S1 最小反压策略：阻塞提交方（= 反压 rollout 准入）。",
    )
    reason_code: Literal["grading_backpressure_queue_full"] = Field(
        default=BACKPRESSURE_REASON_CODE,
        description="EligibilityReport.reason_codes 可直接使用的理由码。",
    )
    occurred_at_utc: AwareDatetime = Field(description="事件时间（必须带时区）。")


@dataclass(frozen=True)
class GradingQueueConfig:
    """F5 用户收紧版默认值：并发 4、队列 8（2x），全部可配置。"""

    concurrency: int = 4
    queue_size: int = 8

    def __post_init__(self) -> None:
        if self.concurrency <= 0:
            raise ValueError(f"concurrency 必须为正，得到 {self.concurrency}")
        if self.queue_size <= 0:
            raise ValueError(f"queue_size 必须为正，得到 {self.queue_size}")


@dataclass
class _QueueItem:
    trajectory_id: str
    workspace: WorkspaceRunner | None
    spec: GradingEnvSpec
    frozen_delta: object | None  # B4：FA formal 冻结 delta 源
    future: asyncio.Future
    submitted_monotonic: float
    depth_at_enqueue: int
    backpressure: bool
    deadline_monotonic: float | None = None  # N2a：评分工作期限（编排提交时建立，含排队）


class GradingQueue:
    """有界评分队列：把 grade 请求分派给固定数量的 worker（asyncio 任务）。

    用法（async with 或手动 start/close）::

        queue = GradingQueue(manager)          # 默认并发 4 / 队列 8
        async with queue:
            report = await queue.submit(
                trajectory_id="traj_1", workspace=ws, spec=spec)

    故障域（P1 的队列侧）：单条评分抛异常只影响该条的 future，
    worker 与队列继续运行。
    """

    def __init__(
        self,
        manager: SWEGradingManager,
        config: GradingQueueConfig | None = None,
        *,
        fatal_sink: Callable[[BaseException], None] | None = None,
    ) -> None:
        self.manager = manager
        self.config = config or GradingQueueConfig()
        self._queue: asyncio.Queue[_QueueItem] = asyncio.Queue(maxsize=self.config.queue_size)
        self._workers: list[asyncio.Task] = []
        self._active = 0
        self.max_active_seen = 0  # F5 观测：实际并发峰值
        self.events: list[BackpressureEvent] = []  # P11 反压事实（gate/画像消费）
        # 批 D-2（Codex 联合审查 R5）：scope / 完整性级致命异常的**独立接收者**——提交者已取消（future
        # 已 done）时 worker 仍要把它交给服务（bringup 传 notify_run_fatal；未传时懒取进程级入口）。
        self._fatal_sink = fatal_sink
        self.out_of_band_fatals: list[BaseException] = []
        self._closing = False

    @property
    def backpressure_count(self) -> int:
        """W3a 计时验收项"评分队列打满次数"：submit() 时队列已满的次数（= 反压事件条数）。"""

        return len(self.events)

    @property
    def active_grading_count(self) -> int:
        return self._active

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    # ------------------------------------------------------------------ 生命周期
    async def start(self) -> None:
        if self._workers:
            raise RuntimeError("GradingQueue 已经启动")
        self._workers = [
            asyncio.create_task(self._worker_loop(), name=f"grading-worker-{i}")
            for i in range(self.config.concurrency)
        ]

    async def close(self, *, drain: bool = True) -> None:
        """关闭队列。drain=True 时先等在途/排队请求全部完成再撤 worker。"""

        # R5-F1（Codex 修后复核）：drain 阶段 worker 必须继续消费已接收的积压——关闭标志只能在排空之后、
        # 撤 worker 之前置位（先置位 = worker 做完手头一条就退出，剩余条目无人 task_done，join 永远等不到，
        # 生产关停步耗满 grading_drain 再走强制关闭）。drain=False 仍立即置位：被取消的 worker 若在
        # grade() 收口时被 ScopeError 替换掉 CancelledError，处理完那条后按标志退出，不再回到 queue.get()。
        if drain and self._workers:
            await self._queue.join()
        self._closing = True
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def __aenter__(self) -> "GradingQueue":
        await self.start()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------ 提交
    async def submit(
        self,
        *,
        trajectory_id: str,
        workspace: WorkspaceRunner | None,
        spec: GradingEnvSpec,
        frozen_delta=None,  # B4：FA formal 冻结 delta 源（透传 manager.grade）
        deadline_monotonic: float | None = None,  # N2a：评分工作期限（含排队 / 反压等待）
    ) -> GradingReport:
        """提交一条评分请求并等待其 GradingReport。

        队列打满时本调用会阻塞（block_submitter 策略）并先产出
        BackpressureEvent——调用方（rollout 编排）被反压是设计行为。
        """

        if not self._workers:
            raise RuntimeError("GradingQueue 未启动（先 await start() 或用 async with）")
        depth = self._queue.qsize()
        backpressure = self._queue.full()
        if backpressure:
            self.events.append(
                BackpressureEvent(
                    event_id=f"bp_{uuid.uuid4().hex[:8]}",
                    trajectory_id=trajectory_id,
                    task_id=spec.task_id,
                    queue_capacity=self.config.queue_size,
                    queue_depth=depth,
                    active_grading_count=self._active,
                    concurrency_limit=self.config.concurrency,
                    occurred_at_utc=datetime.now(timezone.utc),
                )
            )
        item = _QueueItem(
            trajectory_id=trajectory_id,
            workspace=workspace,
            spec=spec,
            frozen_delta=frozen_delta,
            future=asyncio.get_running_loop().create_future(),
            submitted_monotonic=time.monotonic(),  # 等待计时含反压阻塞段
            depth_at_enqueue=depth,
            backpressure=backpressure,
            deadline_monotonic=deadline_monotonic,
        )
        await self._queue.put(item)
        return await item.future

    # ------------------------------------------------------------------ worker
    def _deliver_fatal_out_of_band(self, exc: BaseException) -> None:
        """R5：提交者已不在（future 已取消 / 已 done）时，致命事实仍须到达服务。"""

        self.out_of_band_fatals.append(exc)
        sink = self._fatal_sink
        if sink is None:
            try:
                from repoharness2.adapters.slime.bringup import notify_run_fatal  # 延迟 import：避免环

                sink = notify_run_fatal
            except Exception:  # noqa: BLE001 —— 无 bringup 的测试面：只留账
                return
        try:
            sink(exc)
        except Exception:  # noqa: BLE001 —— 通知失败不炸 worker（账已留）
            pass

    async def _worker_loop(self) -> None:
        while not self._closing:
            item = await self._queue.get()
            queue_wait = time.monotonic() - item.submitted_monotonic
            self._active += 1
            self.max_active_seen = max(self.max_active_seen, self._active)
            try:
                report = await self.manager.grade(
                    trajectory_id=item.trajectory_id,
                    workspace=item.workspace,
                    spec=item.spec,
                    frozen_delta=getattr(item, "frozen_delta", None),
                    queue_wait_seconds=queue_wait,
                    queue_depth_at_enqueue=item.depth_at_enqueue,
                    backpressure_triggered=item.backpressure,
                    deadline_monotonic=item.deadline_monotonic,
                )
                if not item.future.done():
                    item.future.set_result(report)
            except Exception as exc:  # noqa: BLE001 单条失败不炸队列（故障域隔离）
                if not item.future.done():
                    item.future.set_exception(exc)  # 提交者在等：由它转 fatal / 记 failed_to_grade
                elif isinstance(exc, BaselineIntegrityError):
                    # R5：提交者已取消（stop/halt 路径）而 grader 收口后仍抛 scope / 完整性级致命异常——
                    # 不能因 future 已 done 就丢掉；普通 task-local 评分故障仍按原隔离语义（只影响该条）。
                    self._deliver_fatal_out_of_band(exc)
            finally:
                self._active -= 1
                self._queue.task_done()
            # R5：close(drain=False) 的取消可能被 grade() finally 抛出的 ScopeError 替换（上面按普通异常
            # 处理了）——处理完本条后按关闭标志退出，不再 while True 回到 queue.get() 让 close 挂住。
