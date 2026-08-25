"""Rh2GovernedBuffer：实现 miles DataBuffer ABC 的治理 buffer（C3 落点）。

来源：P0-2 spike 原型升级为生产意图实现。走 miles 官方扩展点
`--custom-async-data-buffer-path repoharness2.adapters.miles.governed_buffer.Rh2GovernedBuffer`
加载；内部包一个**真** `DefaultDataBuffer`（存储、容量背压、abort 拒收、
staleness 过滤全部走 miles 真代码），外层只做治理记账。不改 miles 任何代码。

治理对象注入：miles 对自定义 buffer 的构造签名固定为
`buffer_cls(DataBufferConstructorInput)`（fully_async_rollout.py:82-85），
治理对象走不了构造参数，只能挂在 args 上——`args.rh2_governance` 持一个
`Rh2GovernanceConfig`（与 rh2 现链 `args.rh2_orchestrator` 同一注入模式），
缺失即 fail-closed 拒绝构造。

C3 修复（R4 finding：dynamic-filter drop 会被误记 ADMITTED）：
miles `DefaultDataBuffer.put` 里 dynamic filter drop 直接 `return`，既不进
buffer 也不走 unused_handler（fully_async_data_buffer.py:131-134）——外层
按"unused 回调没发生"推断准入就会把被 drop 的组记成 ADMITTED，违反
"ADMITTED 必真实在 buffer"不变量。修复：

- dynamic filter 的 verdict **只在本层执行一次**（自调 miles 官方
  `call_dynamic_filter`，语义顺序与 DefaultDataBuffer.put 相同：
  abort 拒收 -> dynamic filter -> 容量背压）；
- inner DefaultDataBuffer 构造时 `dynamic_sampling_filter_path=None`，
  构造后自检 inner 确实未装载 filter（防 miles 语义漂移）；
- verdict 为 drop 时逐 attempt 记 REJECTED_FILTERED 终态 + drop reason
  metrics（本层自持 MetricGatherer，口径与 miles 一致）。与 miles 语义
  一致：drop 不回收 prompt（无可用梯度信号）。

P0-2 固定的两个 miles 真实行为在本层的接法：

1. put 在容量背压等待中被 cancel 时，组在 miles 侧无痕消失（不进 buffer、
   不走 unused_handler，s6c 测试固定）——本层在 inner.put 的
   CancelledError 路径记 CRASHED_BEFORE_PUT(kind="put_backpressure_cancelled")
   后原样重抛，账不丢；
2. `DefaultDataBuffer` 的存量在私有属性 `_buffer` 里，ABC 契约面没有枚举/
   快照方法——本层维护影子清单 `_inventory`（ADMITTED 在飞组），
   `audit_inventory()` 供崩溃后盘点。

版本前进隐式 ACK 已删除（R5-ext B2）：本层 get 只登记 reservation
（HANDED_OFF + lease），没有任何按 current_version 推进终态的路径；
FINALIZED 一律由账本的 `after_train_success(batch_id)` 显式回执驱动
（见 attempt_ledger.py）。get 后消费方崩溃靠 lease 超时 `reap_expired()`
收回重新入队。
"""

from __future__ import annotations

import asyncio
import copy
import time
from collections.abc import Callable
from dataclasses import dataclass

from miles.rollout.filter_hub.base_types import MetricGatherer, call_dynamic_filter
from miles.rollout.fully_async_data_buffer import (
    DataBuffer,
    DataBufferConstructorInput,
    DataBufferInput,
    DefaultDataBuffer,
    Group,
    iter_samples,
)
from miles.utils.misc import load_function
from miles.utils.types import Sample

from repoharness2.adapters.miles.attempt_ledger import (
    ATTEMPT_KEY,
    DISPATCHED,
    IN_INVENTORY,
    IN_RESERVATION,
    Rh2AttemptLedger,
)


class GovernedBufferError(RuntimeError):
    """治理 buffer 装配/一致性错误（fail-closed）。"""


@dataclass
class Rh2GovernanceConfig:
    """经 `args.rh2_governance` 注入治理对象（见模块 docstring）。

    lease_seconds：get 交出的组多久未收到训练回执可被 `reap_expired()`
    收回重新入队（消费方崩溃兜底）。clock 可注入以便测试用假时钟。
    """

    ledger: Rh2AttemptLedger
    lease_seconds: float = 600.0
    clock: Callable[[], float] = time.monotonic


@dataclass
class _Reservation:
    entry: DataBufferInput
    deadline: float
    version: int | None = None


def attempt_of(group: Group) -> str:
    """从组内样本 metadata 取 physical_attempt_id（组内必须一致且非空）。"""

    ids = {s.metadata.get(ATTEMPT_KEY) for s in iter_samples(group)}
    if len(ids) != 1 or None in ids:
        raise GovernedBufferError(f"组内 attempt id 缺失或不一致：{ids}——dispatch 盖章未覆盖该组")
    (aid,) = ids
    return aid


class Rh2GovernedBuffer(DataBuffer):
    """miles DataBuffer ABC 实现；内部持真 DefaultDataBuffer，外层挂治理账。"""

    def __init__(self, input: DataBufferConstructorInput):
        args = input.args
        governance = getattr(args, "rh2_governance", None)
        if not isinstance(governance, Rh2GovernanceConfig):
            raise GovernedBufferError(
                "args.rh2_governance 缺失或不是 Rh2GovernanceConfig——治理 buffer 必须由 rh2 "
                "编排层注入账本后使用（miles 构造签名固定，治理对象只能挂在 args 上）"
            )
        self._args = args
        self._ledger = governance.ledger
        self._clock = governance.clock
        self._lease_seconds = governance.lease_seconds

        # C3：dynamic filter 的唯一 verdict 执行点在本层（miles 官方 call_dynamic_filter）。
        self._dynamic_filter = load_function(args.dynamic_sampling_filter_path)
        self._metric_gatherer = MetricGatherer()

        # inner 用去掉 filter 的 args 副本构造；unused_handler 包一层观察窗
        # （拒收/回收只能从回调观察到，put 返回 None——P0-2 固定的 ABC 事实）。
        self._downstream_unused = input.unused_handler_fn
        self._recycle_watch: list[list[Sample]] = []
        inner_args = copy.copy(args)
        inner_args.dynamic_sampling_filter_path = None
        self._inner = DefaultDataBuffer(
            DataBufferConstructorInput(args=inner_args, unused_handler_fn=self._on_inner_unused)
        )
        if self._inner._dynamic_filter is not None:  # noqa: SLF001 —— 装配自检：
            # 若 miles 改变了 DefaultDataBuffer 的 filter 装载方式，这里当场炸，
            # 防止 verdict 双跑（本层一次 + inner 一次）悄悄回归。
            raise GovernedBufferError("inner DefaultDataBuffer 仍装载 dynamic filter——C3 单点 verdict 被破坏")

        self._inventory: dict[str, DataBufferInput] = {}  # ADMITTED 影子清单
        self._reservations: dict[str, _Reservation] = {}  # HANDED_OFF 未回执
        self._ledger.bind_buffer(presence_probe=self._presence_of, release=self._release_presence)

    # ------------------------------------------------------- 账本绑定回调

    def _presence_of(self, aid: str) -> str | None:
        if aid in self._inventory:
            return IN_INVENTORY
        if aid in self._reservations:
            return IN_RESERVATION
        return None

    def _release_presence(self, aid: str) -> None:
        self._inventory.pop(aid, None)
        self._reservations.pop(aid, None)

    def _on_inner_unused(self, prompt_group: list[Sample]) -> None:
        self._recycle_watch.append(prompt_group)
        self._downstream_unused(prompt_group)  # miles 原语义保留（retry 回收 / drop 丢弃）

    # ------------------------------------------------------- DataBuffer ABC

    async def put(self, input: DataBufferInput) -> None:
        aid = attempt_of(input.group)
        # 晚响应/越权 put 拦截：只有"当前有效且状态还是 DISPATCHED"的 attempt
        # 才允许首次入队；其余（已撤销重派的旧结果、重复 put）只留痕不入账，
        # 完全不触碰 inner——旧结果不得混入新账。
        if self._ledger.state(aid) != DISPATCHED or not self._ledger.is_current(aid):
            self._ledger.record_late_discard(aid)
            return

        # 语义顺序与 miles DefaultDataBuffer.put 相同（abort -> filter -> 背压）。
        # 1/3 abort 拒收：交给 inner 真代码判（回收回调是唯一观察面）。
        if any(s.status == Sample.Status.ABORTED for s in iter_samples(input.group)):
            watch = len(self._recycle_watch)
            await self._inner.put(input)  # inner 的 abort 分支在容量等待之前，不会阻塞
            if len(self._recycle_watch) == watch:
                raise GovernedBufferError(f"{aid}: 组含 ABORTED 但 inner 未拒收——miles abort 语义漂移")
            self._ledger.reject_recycled(aid, reason="aborted")
            return

        # 2/3 dynamic filter：C3——verdict 只在本层执行一次，逐 attempt 记账。
        verdict = call_dynamic_filter(self._dynamic_filter, self._args, input.group)
        if not verdict.keep:
            self._metric_gatherer.on_dynamic_filter_drop(reason=verdict.reason)
            self._ledger.reject_filtered(aid, reason=verdict.reason)
            return  # 与 miles 相同：drop 不回收（无梯度信号），显式终态代替无痕消失

        # 3/3 容量背压（inner 真 Condition）：等待中被 cancel 时 miles 侧组会
        # 无痕消失（P0-2 s6c 固定），本层先记账再重抛。
        try:
            await self._inner.put(input)
        except asyncio.CancelledError:
            self._ledger.mark_crashed_before_put(aid, kind="put_backpressure_cancelled")
            raise
        self._inventory[aid] = input  # 先登记物理位置，再转账（账本前置核对 presence）
        self._ledger.admit(aid)

    async def get(self, current_version: int | None = None, **context) -> DataBufferInput:
        watch = len(self._recycle_watch)
        entry = await self._inner.get(current_version=current_version)
        # inner get 内被 staleness 淘汰的组 -> RETIRED（回收回调是唯一观察面；
        # 账本终态 release 会同步弹出影子清单）。
        for stale_pg in self._recycle_watch[watch:]:
            self._ledger.retire(attempt_of(stale_pg), reason="stale_on_get")

        aid = attempt_of(entry.group)
        if aid not in self._inventory:
            raise GovernedBufferError(f"{aid}: inner 交出了影子清单外的组——账实不符")
        del self._inventory[aid]
        deadline = self._clock() + self._lease_seconds
        self._reservations[aid] = _Reservation(entry=entry, deadline=deadline, version=current_version)
        self._ledger.hand_off(aid, version=current_version, lease_deadline=deadline)
        return entry

    def get_metrics(self) -> dict[str, float]:
        metrics = {
            **self._inner.get_metrics(),
            **self._metric_gatherer.collect(),  # C3 drop reason 计数（口径与 miles 一致）
            "rh2/governed_buffer/in_flight_admitted": float(len(self._inventory)),
            "rh2/governed_buffer/handed_off_unreceipted": float(len(self._reservations)),
            "rh2/governed_buffer/duplicate_receipt": float(self._ledger.duplicate_receipt_count),
            "rh2/governed_buffer/late_discard": float(self._ledger.late_discard_count),
        }
        self._metric_gatherer = MetricGatherer()  # 窗口计数器随 get_metrics 重置（miles 约定）
        return metrics

    # ------------------------------------------- rh2 扩展面（ABC 之外）

    def audit_inventory(self) -> list[tuple[str, str]]:
        """盘点 ADMITTED 未取走的在飞组：[(attempt_id, prompt_id)]，可与账本对账。"""

        return sorted(
            (aid, self._ledger._record(aid).prompt_id)  # noqa: SLF001 —— 同包审计用途
            for aid in self._inventory
        )

    def handed_off_unreceipted(self) -> list[str]:
        """当前已交给训练、尚无 after_train_success 回执的 attempt。"""

        return sorted(self._reservations)

    async def reap_expired(self) -> list[str]:
        """lease 超时的 reservation 收回并重新入队（消费方崩溃兜底）。

        注意：重新入队走 inner.put（再过一遍真容量背压）；若 buffer 已满会
        在此等待，调用方（rh2 编排层的周期任务）需自行决定超时策略。
        """

        now = self._clock()
        expired = [aid for aid, r in self._reservations.items() if r.deadline <= now]
        for aid in expired:
            reservation = self._reservations.pop(aid)
            await self._inner.put(reservation.entry)
            self._inventory[aid] = reservation.entry  # 先登记物理位置再转账（同 put）
            self._ledger.reclaim(aid, now=now)
        return expired
