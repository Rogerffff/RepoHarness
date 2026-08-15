"""FA-1 生产接线薄壳：slime `--rollout-function-path` 的 FA 入口。

用法（GPU 机器，FA-5 冒烟）::

    --rollout-function-path fa_bringup.rollout_entry.generate_rollout

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

**持久化语义（codex 轮次 7 P0-3 修复）**：worker/queue/collector 由
service 持有并**跨 collect_batch 调用保温**——batch k 期间多执行的成员
留在交付队列/聚合器里，batch k+1 直接消费，预取零丢失；这才是
fully async 的"训练时后台继续生成"。停机走显式 `shutdown()`。

**同步外壳（codex 轮次 7 P0-1 修复）**：slime `call_rollout_fn` 是同步
调用不 await——注册路径必须用 `generate_rollout`（同步），它内部用
slime 的 `run()`（惰性 import，处理已运行 loop）驱动异步本体。
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

__all__ = ["FaRolloutService", "FaEntryError", "generate_rollout", "generate_rollout_async"]


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
        self._dropped_ids: set[str] = set()  # 迟到成员按已弃置组忽略（只计数）
        self.dropped_groups: list[_DroppedGroup] = []
        self.late_deliveries_ignored = 0

    def _bucket(self, prompt_group_id: str) -> _GroupBucket:
        return self._buckets.setdefault(prompt_group_id, _GroupBucket(expected=self._expected))

    def add_delivery(
        self, spec: ExecutionTaskSpec, result: Sequence[Any]
    ) -> list[Any] | None:
        """记入一次交付；组收齐（全员可用）时返回平铺的组样本列表。"""

        if spec.prompt_group_id in self._dropped_ids:
            self.late_deliveries_ignored += 1  # 组已弃置，迟到成员只计数
            return None
        bucket = self._bucket(spec.prompt_group_id)
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
        if spec.prompt_group_id in self._dropped_ids:
            self.late_deliveries_ignored += 1
            return
        bucket = self._bucket(spec.prompt_group_id)
        bucket.failed = True
        bucket.failure_reason = f"member {spec.rollout_execution_id} failed: {error}"
        self._drop(spec.prompt_group_id, bucket)

    def _drop(self, prompt_group_id: str, bucket: _GroupBucket) -> None:
        """弃置即删桶（codex 轮次 7：失败桶滞留 = 内存泄漏，探针 1000 组复现）。"""

        self.dropped_groups.append(
            _DroppedGroup(
                prompt_group_id=prompt_group_id,
                reason=bucket.failure_reason,
                member_execution_ids=tuple(sorted(bucket.deliveries)),
            )
        )
        self._buckets.pop(prompt_group_id, None)
        self._dropped_ids.add(prompt_group_id)

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
        self.failure_records: list[tuple[str, str, str | None, str]] = []  # (group, execution, paid, error)
        # 持久运行时（跨 collect_batch 保温，codex 轮次 7 P0-3）
        self._queue: BoundedDeliveryQueue | None = None
        self._collector: _InterimGroupCollector | None = None
        self._worker: ContinuousExecutionWorker | None = None
        self._worker_task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._completed_backlog: list[list[Any]] = []

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
    async def _ensure_worker(self) -> None:
        if self._worker_task is not None and not self._worker_task.done():
            return
        if self._worker_task is not None and self._worker_task.done():
            # P0-5（codex 轮次 8）：旧 worker 已结束——**先传播它的异常**，
            # 绝不静默覆盖重启。WorkerHalted（sink/任务源故障）到这里必须炸给
            # 启动方："故障后训练不得继续"是硬规则；重启只能走显式
            # recovery API（本版不提供——需要人工裁决 unrecorded_failures）。
            self._worker_task.result()  # 无异常 = worker 正常退出（stop 后）
            raise FaEntryError(
                "worker_already_exited",
                "上一次 worker 已退出（无异常）——服务已 shutdown，不自动重启；"
                "重启需显式新建 FaRolloutService 或 recovery API。",
            )
        self._queue = self._queue or BoundedDeliveryQueue(maxsize=self._queue_maxsize)
        self._collector = self._collector or _InterimGroupCollector(self._group_size)

        def failure_sink(spec: ExecutionTaskSpec, exc: BaseException) -> None:
            # F2-1a 复核 P1-4：worker failure record 也带 physical_attempt_id
            self.failure_records.append(
                (
                    spec.prompt_group_id,
                    spec.rollout_execution_id,
                    spec.physical_attempt_id,
                    f"{type(exc).__name__}: {exc}",
                )
            )
            assert self._collector is not None
            self._collector.add_failure(spec, f"{type(exc).__name__}: {exc}")

        async def execute(spec: ExecutionTaskSpec) -> Sequence[Any]:
            # F2-1a：把 dispatch 时铸造的身份戳进 member metadata（鸭子类型：
            # slime Sample 有 metadata dict；假件同形）——orchestrator 从
            # metadata 读入 audit 并登记 sid→paid 映射
            payload = spec.payload
            meta = getattr(payload, "metadata", None)
            # P1-4：FA 路径要求 metadata 可写——否则身份无处安放，结构化失败
            # （不 fail-open 静默跳过，否则后续全链 paid=None 又难归因）
            if not isinstance(meta, dict):
                raise FaEntryError(
                    "member_metadata_not_writable",
                    f"member {spec.rollout_execution_id} 的 metadata 不是 dict"
                    f"（得到 {type(meta).__name__}）——FA 身份无法注入。",
                )
            # 系统字段**覆盖**旧值（复用 Sample 可能带陈旧 group/execution 身份，
            # setdefault 会保留脏值）
            meta["rh2_rollout_execution_id"] = spec.rollout_execution_id
            meta["rh2_prompt_group_id"] = spec.prompt_group_id
            # F2-2 复核 P1-5：group_index 贯穿到 Outcome（producer 不许伪造 0）
            meta["rh2_group_index"] = int(getattr(payload, "group_index", 0) or 0)
            meta["rh2_member_slot"] = spec.member_slot
            if spec.physical_attempt_id is not None:
                meta["rh2_physical_attempt_id"] = spec.physical_attempt_id
                meta["rh2_physical_attempt_seq"] = spec.physical_attempt_seq
            return await self._execute_member(payload)

        self._worker = ContinuousExecutionWorker(
            task_source=self._task_source,
            execute_fn=execute,
            delivery_queue=self._queue,
            failure_sink=failure_sink,
            concurrency=self._concurrency,
            drain_timeout_seconds=self._drain_timeout,
            execution_limits=self._limits,
        )
        self._stop = asyncio.Event()
        self._worker_task = asyncio.create_task(self._worker.run(self._stop))

    async def collect_batch(self) -> list[list[Any]]:
        """从持久运行时收满 rollout_batch_size 个完整组返回。

        worker **不停**（fully async 保温）：本批多出的完整组进
        `_completed_backlog` 供下批直接消费；在途执行继续跑。停机走
        `shutdown()`（drain 协议 + 账目守恒由 worker 保证）。
        """

        await self._ensure_worker()
        assert self._queue is not None and self._collector is not None
        assert self._worker is not None and self._worker_task is not None
        completed: list[list[Any]] = []
        # 先吃上批结余（预取零丢失的另一半）
        while self._completed_backlog and len(completed) < self._rollout_batch_size:
            completed.append(self._completed_backlog.pop(0))
        import time as _time

        last_progress = _time.monotonic()
        while len(completed) < self._rollout_batch_size:
            if self._worker_task.done():
                self._worker_task.result()  # WorkerHalted/异常原样抛给启动方
                raise FaEntryError(
                    "worker_exited_prematurely",
                    "worker 在收满批次前退出——任务源枯竭或配置错误。",
                )
            try:
                spec, result = await asyncio.wait_for(self._queue.get(), timeout=0.05)
            except asyncio.TimeoutError:
                # 饥饿收口：任务源枯竭（backlog 空 + 在途清零）且长时间无交付
                idle = _time.monotonic() - last_progress
                counters = self._worker.counters
                drained = (
                    not self._member_backlog
                    and counters.dispatched == counters.delivered + counters.failed
                )
                if drained and idle >= self._starvation_timeout:
                    raise FaEntryError(
                        "batch_starved",
                        f"收满前任务源枯竭：completed={len(completed)}/"
                        f"{self._rollout_batch_size}，弃置组 "
                        f"{len(self._collector.dropped_groups)} 个，空转 {idle:.1f}s。",
                    )
                continue
            last_progress = _time.monotonic()
            group = self._collector.add_delivery(spec, result)
            if group is not None:
                if len(completed) < self._rollout_batch_size:
                    completed.append(group)
                else:  # pragma: no cover - 防御（循环条件已挡）
                    self._completed_backlog.append(group)
        return completed

    async def shutdown(self) -> None:
        """显式停机：stop + drain（worker 的 drain 协议接管账目）。"""

        if self._worker_task is None:
            return
        self._stop.set()
        try:
            await asyncio.wait_for(self._worker_task, timeout=self._drain_timeout + 5)
        except asyncio.TimeoutError:  # pragma: no cover - drain 协议兜底的兜底
            self._worker_task.cancel()
        finally:
            self._worker_task = None


_SERVICE: FaRolloutService | None = None


async def _bootstrap_via_glue(args: Any, data_buffer: Any) -> None:
    """orchestrator/采样配方未挂载时经 glue 引导（codex 轮次 7 P0-2）。

    旧 custom_generate 路径在第一条 rollout 时才挂 `args.rh2_orchestrator`
    ——FA 入口绕过它，必须自己触发同一套 BringupService 启动。惰性 import
    （glue 依赖 aiohttp/capture_wire，本地假件测试不走本函数）。
    """

    try:
        from repoharness2.adapters.slime import bringup as glue  # noqa: PLC0415 —— F2-0 后的正式启动面
    except ImportError as exc:  # pragma: no cover - 生产环境必有
        raise FaEntryError(
            "glue_bootstrap_unavailable",
            f"args.rh2_orchestrator 缺失且 repoharness2.adapters.slime.bringup 不可导入（{exc}）——"
            "检查 PYTHONPATH 与启动顺序。",
        ) from exc
    await glue.ensure_fa_started(args)


def _build_service(args: Any, data_buffer: Any) -> FaRolloutService:
    orchestrator = getattr(args, "rh2_orchestrator", None)
    if orchestrator is not None:
        _mode = getattr(getattr(orchestrator, "config", None), "execution_mode", "s1_compat")
        if _mode not in ("fa_audit_only", "fa_formal"):
            # 复核五轮 P0-2：FA 专用入口禁止 silent downgrade——忘配
            # RH2_EXECUTION_MODE 时绝不能以 s1_compat 评分交付训练样本
            raise FaEntryError(
                "fa_entry_requires_fa_execution_mode",
                f"FA 入口要求 execution_mode ∈ {{fa_audit_only, fa_formal}}"
                f"（得到 {_mode!r}）——设置 RH2_EXECUTION_MODE 后重启。",
            )
    if orchestrator is None:
        raise FaEntryError(
            "orchestrator_not_attached",
            "args.rh2_orchestrator 缺失——FA 入口复用 S1 glue 的编排本体挂点"
            "（ensure_fa_started 引导后仍缺失 = 启动面损坏）。",
        )
    sampling_params = getattr(args, "rh2_sampling_params", None)
    if sampling_params is None:
        raise FaEntryError(
            "sampling_params_not_attached",
            "args.rh2_sampling_params 缺失——FA 入口不猜测采样参数（top-p tape "
            "语义依赖显式配方），由 glue.ensure_fa_started 从 args 构造。",
        )

    def group_source() -> Sequence[Any] | None:
        groups = data_buffer.get_samples(1)
        if not groups:
            return None
        (group,) = groups
        return group

    async def execute_member(member: Any) -> Sequence[Any]:
        return await orchestrator.generate(args, member, dict(sampling_params))

    # 轮次 13 P0-4：本对象只供 worker 的 **sandbox** 类（绑 AsyncLoopThread
    # 的 event loop）。model_call 限额的真实 owner 是 glue 的 adapter 线程
    #（BringupService.model_call_limits，env RH2_FA_LIMIT_MODEL_CALL）；评分
    # 并发的 owner 是 GradingQueueConfig（env RH2_FA_LIMIT_GRADING）。此前
    # 这里的 model_call/grading_container 键是无消费者的假配置，已删。
    limits = ResourceLimits(
        {"sandbox": int(getattr(args, "rh2_fa_limit_sandbox", 16))}
    )
    return FaRolloutService(
        group_source=group_source,
        execute_member=execute_member,
        group_size=int(getattr(args, "n_samples_per_prompt", 1)),
        rollout_batch_size=int(getattr(args, "rollout_batch_size", 1)),
        concurrency=int(getattr(args, "rh2_fa_concurrency", 8)),
        queue_maxsize=int(getattr(args, "rh2_fa_queue_maxsize", 256)),
        drain_timeout_seconds=float(getattr(args, "rh2_fa_drain_timeout_seconds", 30.0)),
        starvation_timeout_seconds=float(
            getattr(args, "rh2_fa_starvation_timeout_seconds", 600.0)
        ),
        limits=limits,
    )


async def generate_rollout_async(
    args: Any, rollout_id: int, data_buffer: Any, evaluation: bool = False
) -> list[list[Any]]:
    """FA 入口的异步本体（进程内服务单例，跨 batch 保温）。"""

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
        if getattr(args, "rh2_orchestrator", None) is None or getattr(
            args, "rh2_sampling_params", None
        ) is None:
            await _bootstrap_via_glue(args, data_buffer)
        _SERVICE = _build_service(args, data_buffer)
    return await _SERVICE.collect_batch()


def generate_rollout(
    args: Any, rollout_id: int, data_buffer: Any, evaluation: bool = False
) -> list[list[Any]]:
    """slime `call_rollout_fn` 的**同步**入口（codex 轮次 7 P0-1：
    call_rollout_fn 不 await，async def 会把 coroutine 当返回值）。

    注册路径用本函数；异步本体由 slime 的 `run()`（处理已运行 loop 的
    场景）驱动，slime 不可导入时回退 asyncio.run（本地测试）。
    """

    coro = generate_rollout_async(args, rollout_id, data_buffer, evaluation=evaluation)
    try:
        from slime.utils.async_utils import run as slime_run  # noqa: PLC0415
    except ImportError:
        return asyncio.run(coro)
    return slime_run(coro)
