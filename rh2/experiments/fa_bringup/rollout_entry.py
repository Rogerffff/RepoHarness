"""FA-1 生产接线薄壳：slime `--rollout-function-path` 的 FA 入口。

用法（GPU 机器，FA-5 冒烟）::

    --rollout-function-path fa_bringup.rollout_entry.generate_rollout_async

职责（codex FA-1 审查严重 1 的修复——生产路径现在就接通，不留到 FA-5
第一次发现接口没接上）：把 FA-1 运行时组件（ContinuousExecutionWorker /
BoundedDeliveryQueue / ResourceLimits）组装成 slime rollout 函数形状——
从 data_buffer 取组、逐 RolloutExecution 分派给 `args.rh2_orchestrator.
generate`、收集交付、按组聚合返回 `list[list[Sample]]`。

**零 slime import**：Sample 对象来自 data_buffer、由 orchestrator 加工，
本模块全程鸭子类型（`group_index`/`index`/`remove_sample` 属性面）——
本地假件测试即可覆盖全部编排逻辑；GPU 侧只验证 slime 真把本函数当
rollout 入口调用（FA-5 首个检查项）。

**FA-2 接缝（显式 interim，不冻结接口）**：`_InterimGroupCollector` 是
PromptGroupAssembler + QualifiedPromptGroupQueue 落地前的**过渡聚合器**
——按组收齐成员、任一成员失败整组显式弃置（记 `dropped_groups`，绝不
静默）、收满 `rollout_batch_size` 个完整组返回。FA-2 交付后本类整体替换
为 assembler 消费（worker→queue 的交付形状 `(ExecutionTaskSpec, result)`
保持——codex 建议不冻结的是 assembler 侧接口，不是 worker 输出）。

场景 21（05 计划验收）：`evaluation=True` 进入本路径 **fail-fast**——
持续 worker 拓扑不服务评测（D-FA-4：before/after 走标准路径）。注意
S1 的 batch-sync custom_generate 路径**支持** eval 占位形状（E10 定案），
拒绝只发生在 FA 入口，两条路径语义不同是设计而非遗漏。
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from repoharness2.adapters.slime.async_worker import (
    BoundedDeliveryQueue,
    ContinuousExecutionWorker,
    ExecutionTaskSpec,
    ResourceLimits,
)

__all__ = ["FaRolloutService", "FaEntryError", "generate_rollout_async"]


class FaEntryError(RuntimeError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


def _member_ok(result: Sequence[Any]) -> bool:
    """一次执行的交付是否可用：至少一条非 remove_sample 的叶链。

    orchestrator 把失败收口成 abort 形状（remove_sample=True）而不是抛异常，
    所以成员失败大多以这种形态到达——interim 聚合器按"整组弃置 + 显式
    记账"处置（首版不补采，worker 持续供新组）。
    """

    return any(not getattr(sample, "remove_sample", False) for sample in result)


@dataclass
class _DroppedGroup:
    prompt_group_id: str
    reason: str
    member_execution_ids: tuple[str, ...]


@dataclass
class _GroupBucket:
    expected: int
    deliveries: dict[str, list[Any]] = field(default_factory=dict)  # execution_id -> 叶链列表
    failed: bool = False
    failure_reason: str = ""


class _InterimGroupCollector:
    """FA-2 前的过渡组聚合器（显式弃置账目；不做任何补采/修复）。"""

    def __init__(self, expected_group_size: int) -> None:
        if expected_group_size < 1:
            raise FaEntryError("invalid_group_size", "expected_group_size 必须 >= 1。")
        self._expected = expected_group_size
        self._buckets: dict[str, _GroupBucket] = {}
        self.dropped_groups: list[_DroppedGroup] = []

    def _bucket(self, prompt_group_id: str) -> _GroupBucket:
        return self._buckets.setdefault(prompt_group_id, _GroupBucket(expected=self._expected))

    def add_delivery(
        self, spec: ExecutionTaskSpec, result: Sequence[Any]
    ) -> list[Any] | None:
        """记入一次交付；组收齐（全员可用）时返回平铺的组样本列表。"""

        bucket = self._bucket(spec.prompt_group_id)
        if bucket.failed:
            return None  # 组已废，后到成员只进弃置账（flush 时统一记）
        if not _member_ok(result):
            bucket.failed = True
            bucket.failure_reason = f"member {spec.rollout_execution_id} delivered abort shape"
            self._drop(spec.prompt_group_id, bucket)
            return None
        bucket.deliveries[spec.rollout_execution_id] = list(result)
        if len(bucket.deliveries) == bucket.expected:
            del self._buckets[spec.prompt_group_id]
            flat: list[Any] = []
            for execution_id in sorted(bucket.deliveries):
                flat.extend(bucket.deliveries[execution_id])
            return flat
        return None

    def add_failure(self, spec: ExecutionTaskSpec, error: str) -> None:
        bucket = self._bucket(spec.prompt_group_id)
        if not bucket.failed:
            bucket.failed = True
            bucket.failure_reason = f"member {spec.rollout_execution_id} failed: {error}"
            self._drop(spec.prompt_group_id, bucket)

    def _drop(self, prompt_group_id: str, bucket: _GroupBucket) -> None:
        self.dropped_groups.append(
            _DroppedGroup(
                prompt_group_id=prompt_group_id,
                reason=bucket.failure_reason,
                member_execution_ids=tuple(sorted(bucket.deliveries)),
            )
        )

    @property
    def open_group_count(self) -> int:
        return len(self._buckets)


class FaRolloutService:
    """FA rollout 入口的编排本体（进程内单例由 `generate_rollout_async` 持有）。

    可注入面（本地测试用假件替换）：`group_source`（从 data_buffer 取下一个
    组的可调用，返回成员 Sample 列表或 None）、`execute_member`（一次
    RolloutExecution：member Sample -> 叶链列表，生产实现 =
    `args.rh2_orchestrator.generate`）。
    """

    def __init__(
        self,
        *,
        group_source: Callable[[], Sequence[Any] | None],
        execute_member: Callable[[Any], Awaitable[Sequence[Any]]],
        group_size: int,
        rollout_batch_size: int,
        concurrency: int = 8,
        queue_maxsize: int = 256,
        drain_timeout_seconds: float = 30.0,
        starvation_timeout_seconds: float = 600.0,
        limits: ResourceLimits | None = None,
    ) -> None:
        if rollout_batch_size < 1:
            raise FaEntryError("invalid_rollout_batch_size", "rollout_batch_size 必须 >= 1。")
        self._group_source = group_source
        self._execute_member = execute_member
        self._group_size = group_size
        self._rollout_batch_size = rollout_batch_size
        self._concurrency = concurrency
        self._queue_maxsize = queue_maxsize
        self._drain_timeout = drain_timeout_seconds
        self._starvation_timeout = starvation_timeout_seconds
        self._limits = limits
        self._member_backlog: deque[ExecutionTaskSpec] = deque()
        self._group_seq = 0
        self.failure_records: list[tuple[str, str, str]] = []  # (group, execution, error)

    # ------------------------------------------------------------- 任务供给
    def _task_source(self) -> ExecutionTaskSpec | None:
        if not self._member_backlog:
            members = self._group_source()
            if not members:
                return None
            self._group_seq += 1
            group_id = f"fa_g{self._group_seq}"
            for slot, member in enumerate(members):
                self._member_backlog.append(
                    ExecutionTaskSpec(
                        rollout_execution_id=f"{group_id}_m{slot}",
                        prompt_group_id=group_id,
                        member_slot=slot,
                        payload=member,
                    )
                )
        return self._member_backlog.popleft() if self._member_backlog else None

    # ------------------------------------------------------------- 主收集
    async def collect_batch(self) -> list[list[Any]]:
        """收满 rollout_batch_size 个完整组后停 worker 并返回（interim 语义）。"""

        queue = BoundedDeliveryQueue(maxsize=self._queue_maxsize)
        collector = _InterimGroupCollector(self._group_size)
        stop = asyncio.Event()

        def failure_sink(spec: ExecutionTaskSpec, exc: BaseException) -> None:
            self.failure_records.append(
                (spec.prompt_group_id, spec.rollout_execution_id, f"{type(exc).__name__}: {exc}")
            )
            collector.add_failure(spec, f"{type(exc).__name__}: {exc}")

        async def execute(spec: ExecutionTaskSpec) -> Sequence[Any]:
            return await self._execute_member(spec.payload)

        worker = ContinuousExecutionWorker(
            task_source=self._task_source,
            execute_fn=execute,
            delivery_queue=queue,
            failure_sink=failure_sink,
            concurrency=self._concurrency,
            drain_timeout_seconds=self._drain_timeout,
            execution_limits=self._limits,
        )
        completed: list[list[Any]] = []
        worker_task = asyncio.create_task(worker.run(stop))
        import time as _time

        last_progress = _time.monotonic()
        try:
            while len(completed) < self._rollout_batch_size:
                if worker_task.done():
                    # worker 提前退出（halt/异常）——把原因抛给启动方，绝不空转
                    worker_task.result()
                    raise FaEntryError(
                        "worker_exited_prematurely",
                        "worker 在收满批次前正常退出——任务源枯竭或配置错误。",
                    )
                try:
                    spec, result = await asyncio.wait_for(queue.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    # 饥饿收口：任务源枯竭（backlog 空 + 在途清零）且长时间无
                    # 交付 → 显式报错，绝不空转等一个永远不来的组
                    idle = _time.monotonic() - last_progress
                    counters = worker.counters
                    drained = (
                        not self._member_backlog
                        and counters.dispatched == counters.delivered + counters.failed
                    )
                    if drained and idle >= self._starvation_timeout:
                        raise FaEntryError(
                            "batch_starved",
                            f"收满前任务源枯竭：completed={len(completed)}/"
                            f"{self._rollout_batch_size}，弃置组 "
                            f"{len(collector.dropped_groups)} 个，空转 {idle:.1f}s。",
                        )
                    continue
                last_progress = _time.monotonic()
                group = collector.add_delivery(spec, result)
                if group is not None:
                    completed.append(group)
        finally:
            stop.set()
            try:
                await asyncio.wait_for(worker_task, timeout=self._drain_timeout + 5)
            except asyncio.TimeoutError:  # pragma: no cover - drain 协议兜底的兜底
                worker_task.cancel()
        return completed


_SERVICE: FaRolloutService | None = None


def _build_service(args: Any, data_buffer: Any) -> FaRolloutService:
    orchestrator = getattr(args, "rh2_orchestrator", None)
    if orchestrator is None:
        raise FaEntryError(
            "orchestrator_not_attached",
            "args.rh2_orchestrator 缺失——FA 入口复用 S1 glue 的编排本体挂点"
            "（BringupService 启动时挂上），检查启动顺序。",
        )
    sampling_params = getattr(args, "rh2_sampling_params", None)
    if sampling_params is None:
        raise FaEntryError(
            "sampling_params_not_attached",
            "args.rh2_sampling_params 缺失——FA 入口不猜测采样参数（top-p tape "
            "语义依赖显式配方），由 glue 启动时挂上。",
        )

    def group_source() -> Sequence[Any] | None:
        groups = data_buffer.get_samples(1)
        if not groups:
            return None
        (group,) = groups
        return group

    async def execute_member(member: Any) -> Sequence[Any]:
        return await orchestrator.generate(args, member, dict(sampling_params))

    return FaRolloutService(
        group_source=group_source,
        execute_member=execute_member,
        group_size=int(getattr(args, "n_samples_per_prompt", 1)),
        rollout_batch_size=int(getattr(args, "rollout_batch_size", 1)),
        concurrency=int(getattr(args, "rh2_fa_concurrency", 8)),
        queue_maxsize=int(getattr(args, "rh2_fa_queue_maxsize", 256)),
        drain_timeout_seconds=float(getattr(args, "rh2_fa_drain_timeout_seconds", 30.0)),
    )


async def generate_rollout_async(
    args: Any, rollout_id: int, data_buffer: Any, evaluation: bool = False
) -> list[list[Any]]:
    """slime rollout 函数形状的 FA 入口（进程内服务单例）。"""

    if evaluation:
        # 05 计划验收场景 21：eval 不走 FA 持续 worker 路径——fail-fast，
        # 错误信息指向标准路径（D-FA-4：before/after，worker 停止后执行）。
        raise FaEntryError(
            "eval_not_supported_in_fa_path",
            "evaluation=True 进入了 FA rollout 入口——持续 worker 拓扑不服务评测；"
            "before/after 评测走标准（非 FA）rollout 路径（05 计划 D-FA-4）。",
        )
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = _build_service(args, data_buffer)
    return await _SERVICE.collect_batch()
