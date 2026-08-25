"""rh2 attempt receipt 账本（miles 迁移治理件，C3/C7 的共享地基）。

来源：P0-2 spike 原型（scratchpad/test_miles_spike_p02_faults.py 的
Rh2AttemptLedger）升级为生产意图实现。每次派发（dispatch）产生一个新的
physical_attempt_id 写进样本 metadata，全生命周期在本账本留痕。

状态机（每个 attempt 走且只走一条路到终态）：

    DISPATCHED --put 前 crash/cancel----> CRASHED_BEFORE_PUT   （终态）
    DISPATCHED --put 被 miles abort 拒收-> REJECTED_RECYCLED    （终态，prompt 已回收）
    DISPATCHED --dynamic filter drop----> REJECTED_FILTERED    （终态，C3：不回收，无梯度信号）
    DISPATCHED --put 成功---------------> ADMITTED             （必真实在 buffer 影子清单）
    ADMITTED   --get 取走---------------> HANDED_OFF           （必真实在 reservation，带 lease）
    HANDED_OFF --lease 超时收回---------> ADMITTED             （留 reclaimed_at 痕，出 batch）
    HANDED_OFF --after_train_success----> FINALIZED            （终态，唯一入口，见下）
    HANDED_OFF --回执窗口崩溃/关停------> UNCERTAIN_TRAINED    （终态，见下）
    DISPATCHED/ADMITTED/HANDED_OFF --撤销-> RETIRED            （终态，晚到结果只留痕不入账）

两条从 P0-2 原型显式删除/收紧的语义：

1. **删除"版本前进隐式 ACK"**（R5-ext B2 证伪）：miles `train_async.py:79-81`
   在训练当前批之前就发起下一轮 generate/drain，get 看到更高的
   current_version 只说明权重状态前进，不证明任何具体 batch 已被 optimizer
   消费。因此 FINALIZED 的唯一入口是显式回执 `after_train_success(batch_id)`
   ——由 rh2 自有训练入口在 `await actor_model.train(...)` 成功返回后调用。
   本账本没有任何按版本号推进终态的路径（原型的 auto_ack/_ack_older_than
   已整体移除）。

2. **崩溃窗口落 UNCERTAIN_TRAINED**：optimizer 已成功但回执尚未持久化时
   进程崩溃，恢复侧对该 batch 调 `mark_uncertain_trained(batch_id)`——绝不
   伪造 FINALIZED。与决策包 v4 的 at-least-once 语义一致（fa2a_decision_
   package.md:375-407）：rollout 执行 at-least-once，optimizer step
   exactly-once 首版不承诺。UNCERTAIN_TRAINED 是终态；之后回执才姗姗来迟
   也只留 RECEIPT_IGNORED_TERMINAL 痕，不翻转终态。

不变量（账本内部强制，非调用方自觉）：

- "ADMITTED 必真实在 buffer 影子清单、HANDED_OFF 必真实在 reservation"——
  治理 buffer 通过 `bind_buffer()` 注册 presence 探针后，任何进入这两个
  状态的转移都会当场核对物理位置，不符即抛 `LedgerError`；
  `assert_books_balanced()` 再做全量对账。
- FINALIZED 集合 == 训练入账集合（trained_attempts），由同一次
  after_train_success 原子写入；重复回执是留痕 no-op。
- 终态 attempt 的物理占位（inventory/reservation）由账本经 release 回调
  统一清除——调用方忘记清理不会造成账实不符。

miles 真实行为依赖（P0-2 固定的事实）：`Sample.reset_for_retry()` 保留
metadata（含旧 attempt id），所以重新盖章必须发生在 dispatch 时刻，本模块
的 dispatch 无条件覆写 `metadata["physical_attempt_id"]`。

本模块零 miles/slime import（纯 Python），CPU 任意环境可导。
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

ATTEMPT_KEY = "physical_attempt_id"
PROMPT_KEY = "prompt_id"

# -- 状态常量（字符串即接口，测试与审计直接比对） --------------------------
DISPATCHED = "DISPATCHED"
ADMITTED = "ADMITTED"
HANDED_OFF = "HANDED_OFF"
FINALIZED = "FINALIZED"
CRASHED_BEFORE_PUT = "CRASHED_BEFORE_PUT"
REJECTED_RECYCLED = "REJECTED_RECYCLED"
REJECTED_FILTERED = "REJECTED_FILTERED"
RETIRED = "RETIRED"
UNCERTAIN_TRAINED = "UNCERTAIN_TRAINED"

TERMINAL_STATES = frozenset(
    {FINALIZED, CRASHED_BEFORE_PUT, REJECTED_RECYCLED, REJECTED_FILTERED, RETIRED, UNCERTAIN_TRAINED}
)

# presence 探针的返回值（物理位置枚举）：None = 不在任何治理容器里。
IN_INVENTORY = "inventory"
IN_RESERVATION = "reservation"


class LedgerError(RuntimeError):
    """账本状态机/不变量违规（fail-closed：触发即说明调用序错误或账实不符）。"""


@dataclass
class AttemptRecord:
    attempt_id: str
    prompt_id: str
    state: str
    batch_id: str | None = None
    history: list[tuple[str, dict[str, Any]]] = field(default_factory=list)


class Rh2AttemptLedger:
    """receipt 账本：每次派发一个新 physical_attempt_id，全生命周期留痕。

    「不丢账」的定义：任一 dispatch 过的 attempt，任意时刻恰好处于一个状态；
    FINALIZED 集合 == trained_attempts 集合，二者由同一次 after_train_success
    原子写入——不存在"训练了但没账"或"记了账但没训练"（后者被
    UNCERTAIN_TRAINED 显式区分）的路径。
    """

    def __init__(self) -> None:
        self._records: dict[str, AttemptRecord] = {}
        self._current: dict[str, str] = {}  # prompt_id -> 当前有效 attempt_id
        self._seq = itertools.count()
        self._batches: dict[str, list[str]] = {}  # batch_id -> attempt_ids（seal 顺序）
        self._presence_probe: Callable[[str], str | None] | None = None
        self._release: Callable[[str], None] | None = None
        self.trained_attempts: list[str] = []
        self.duplicate_receipt_count = 0
        self.late_discard_count = 0

    # ------------------------------------------------------------- buffer 绑定

    def bind_buffer(
        self,
        *,
        presence_probe: Callable[[str], str | None],
        release: Callable[[str], None],
    ) -> None:
        """治理 buffer 在构造时注册物理位置探针与占位清除回调。

        presence_probe(aid) -> "inventory" | "reservation" | None；
        release(aid)：把 aid 从 inventory/reservation 全部弹出（进入终态时
        由账本调用，保证账实一致不依赖调用方自觉）。
        """

        if self._presence_probe is not None:
            raise LedgerError("账本已绑定治理 buffer；重复绑定说明两个 buffer 在抢同一账本")
        self._presence_probe = presence_probe
        self._release = release

    # ------------------------------------------------------------------ 派发

    def dispatch(self, prompt_group: Sequence[Any], *, prompt_id: str | None = None) -> str:
        """派发一个新 attempt：生成新 id 并**无条件重盖章**到组内每个样本。

        重盖章的原因（P0-2 固定的 miles 事实）：`Sample.reset_for_retry()`
        保留 metadata，回收路径不会清除旧 attempt id——身份必须在派发时刻
        由本方法覆写，不能指望回收方。
        """

        if not prompt_group:
            raise LedgerError("dispatch 收到空 prompt_group——无身份可盖章")
        pid = prompt_id if prompt_id is not None else prompt_group[0].metadata.get(PROMPT_KEY)
        if pid is None:
            raise LedgerError(
                "dispatch 缺 prompt 身份：显式传 prompt_id，或在样本 metadata['prompt_id'] 预置"
            )
        pid = str(pid)
        aid = f"{pid}#a{next(self._seq)}"
        for s in prompt_group:
            s.metadata[ATTEMPT_KEY] = aid  # 每次派发都重盖章（覆盖旧 attempt id）
        rec = AttemptRecord(attempt_id=aid, prompt_id=pid, state=DISPATCHED)
        rec.history.append((DISPATCHED, {}))
        self._records[aid] = rec
        self._current[pid] = aid
        return aid

    # ------------------------------------------------------------------ 查询

    def _record(self, aid: str) -> AttemptRecord:
        rec = self._records.get(aid)
        if rec is None:
            raise LedgerError(f"未知 attempt {aid!r}——出现了未经 dispatch 盖章的组")
        return rec

    def state(self, aid: str) -> str:
        return self._record(aid).state

    def is_current(self, aid: str) -> bool:
        rec = self._record(aid)
        return self._current.get(rec.prompt_id) == aid

    def history(self, aid: str) -> tuple[tuple[str, dict[str, Any]], ...]:
        return tuple(self._record(aid).history)

    def batch_of(self, aid: str) -> str | None:
        return self._record(aid).batch_id

    def attempts_in_state(self, state: str) -> list[str]:
        return [aid for aid, rec in self._records.items() if rec.state == state]

    def batch_members(self, batch_id: str) -> tuple[str, ...]:
        members = self._batches.get(batch_id)
        if members is None:
            raise LedgerError(f"未知 batch {batch_id!r}")
        return tuple(members)

    # ------------------------------------------------------------- 状态机内核

    def _transition(self, aid: str, allowed: frozenset[str] | set[str], to: str, **info: Any) -> None:
        rec = self._record(aid)
        if rec.state not in allowed:
            raise LedgerError(f"{aid}: 非法转移 {rec.state} -> {to}（允许来源 {sorted(allowed)}）")
        # 不变量前置核对：进入 ADMITTED/HANDED_OFF 前物理位置必须已就位
        # （治理 buffer 先登记 inventory/reservation，再调账本）。
        if to == ADMITTED:
            self._assert_presence(aid, expected=IN_INVENTORY, entering=to)
        elif to == HANDED_OFF:
            self._assert_presence(aid, expected=IN_RESERVATION, entering=to)
        rec.history.append((to, info))
        rec.state = to
        if to in TERMINAL_STATES and self._release is not None:
            # 终态统一清除物理占位：账本负责账实一致，不依赖调用方收尾。
            self._release(aid)

    def _assert_presence(self, aid: str, *, expected: str | None, entering: str) -> None:
        if self._presence_probe is None:
            return
        actual = self._presence_probe(aid)
        if actual != expected:
            raise LedgerError(
                f"{aid}: 进入 {entering} 要求物理位置 {expected!r}，实际 {actual!r}——"
                "账实不符（不变量：ADMITTED 必在 buffer 影子清单 / HANDED_OFF 必在 reservation）"
            )

    # ------------------------------------------------------------- 生命周期事件

    def mark_crashed_before_put(self, aid: str, kind: str) -> bool:
        """put 之前失败（cancel/异常/关停扫尾）。幂等：重复标记只留痕。

        幂等的原因：同一 attempt 的失败可能被两层同时观察到——治理 buffer
        的 put 在背压等待中吃到 CancelledError 会记账（governed_buffer.put），
        rollout function 层的生产 task 的 CancelledError 分支也会记账；
        谁先到谁转移，后到者留 DUPLICATE_CRASH_MARK 痕。
        """

        rec = self._record(aid)
        if rec.state == CRASHED_BEFORE_PUT:
            rec.history.append(("DUPLICATE_CRASH_MARK", {"kind": kind}))
            return False
        self._transition(aid, {DISPATCHED}, CRASHED_BEFORE_PUT, kind=kind)
        return True

    def admit(self, aid: str) -> None:
        self._transition(aid, {DISPATCHED}, ADMITTED)

    def reject_recycled(self, aid: str, reason: str) -> None:
        """miles put 入口拒收（abort 过滤），prompt 已交 unused_handler 回收。"""

        self._transition(aid, {DISPATCHED}, REJECTED_RECYCLED, reason=reason)

    def reject_filtered(self, aid: str, reason: str | None) -> None:
        """dynamic filter drop（C3）：显式拒绝终态。与 miles 语义一致，drop
        不回收 prompt（无可用梯度信号，fully_async_data_buffer.py:131-134
        的 "Dropped, not recycled"），只逐 attempt 记账。"""

        self._transition(aid, {DISPATCHED}, REJECTED_FILTERED, reason=reason)

    def hand_off(self, aid: str, *, version: int | None, lease_deadline: float) -> None:
        self._transition(aid, {ADMITTED}, HANDED_OFF, version=version, lease_deadline=lease_deadline)

    def reclaim(self, aid: str, *, now: float) -> None:
        """lease 超时收回：回到 ADMITTED 可再次 hand_off；若已 seal 进 batch
        则同时移出 batch（该 batch 之后的回执不覆盖这个 attempt）。"""

        rec = self._record(aid)
        if rec.state == HANDED_OFF and rec.batch_id is not None:
            self._batches[rec.batch_id].remove(aid)
            rec.history.append(("BATCH_UNASSIGNED_ON_RECLAIM", {"batch_id": rec.batch_id}))
            rec.batch_id = None
        self._transition(aid, {HANDED_OFF}, ADMITTED, reclaimed_at=now)

    def retire(self, aid: str, reason: str) -> None:
        """治理撤销（staleness 淘汰 / 晚响应 fencing / 关停清场）。"""

        rec = self._record(aid)
        if rec.state == HANDED_OFF and rec.batch_id is not None:
            self._batches[rec.batch_id].remove(aid)
            rec.history.append(("BATCH_UNASSIGNED_ON_RETIRE", {"batch_id": rec.batch_id}))
            rec.batch_id = None
        self._transition(aid, {DISPATCHED, ADMITTED, HANDED_OFF}, RETIRED, reason=reason)
        if self._current.get(rec.prompt_id) == aid:
            del self._current[rec.prompt_id]

    def record_late_discard(self, aid: str) -> None:
        """晚到/越权的 put 被治理 buffer 拦截时留痕（不改变状态）。"""

        rec = self._record(aid)
        if rec.state == DISPATCHED and self._current.get(rec.prompt_id) == aid:
            raise LedgerError(f"{aid}: 当前有效且尚未入 buffer 的 attempt 不允许按晚响应丢弃")
        rec.history.append(("LATE_RESULT_DISCARDED", {"state": rec.state}))
        self.late_discard_count += 1

    # --------------------------------------------------------- 训练回执（C7）

    def seal_batch(self, batch_id: str, attempt_ids: Sequence[str] | None = None) -> list[str]:
        """把一次 drain 组装出的训练批定格为 batch：成员 = 当前 HANDED_OFF
        且未归属任何 batch 的 attempt（或显式给出的 attempt_ids）。

        由 rh2 rollout function 层在一次 drain 完成后调用；batch_id 必须唯一。
        """

        if batch_id in self._batches:
            raise LedgerError(f"batch {batch_id!r} 已 seal 过——batch id 必须唯一")
        if attempt_ids is None:
            members = [
                aid for aid, rec in self._records.items() if rec.state == HANDED_OFF and rec.batch_id is None
            ]
        else:
            members = list(attempt_ids)
        if not members:
            raise LedgerError(f"seal_batch({batch_id!r}) 没有可归属的 HANDED_OFF attempt——调用序错误")
        for aid in members:
            rec = self._record(aid)
            if rec.state != HANDED_OFF or rec.batch_id is not None:
                raise LedgerError(
                    f"{aid}: 不能 seal 进 {batch_id!r}（state={rec.state}, batch={rec.batch_id!r}）"
                )
            rec.batch_id = batch_id
            rec.history.append(("SEALED_INTO_BATCH", {"batch_id": batch_id}))
        self._batches[batch_id] = list(members)
        return members

    def after_train_success(self, batch_id: str) -> list[str]:
        """**FINALIZED 的唯一入口**：显式训练成功回执。

        由 rh2 自有训练入口在 `await actor_model.train(...)` 成功返回后调用。
        版本前进、get_metrics 步边界、下一批 drain 的发生都**不是**训练成功
        的证据（R5-ext B2；miles train_async 预取在训练前发起）。

        幂等（at-least-once 回执可能重投递）：已 FINALIZED 的成员留
        DUPLICATE_RECEIPT_NOOP 痕并计数；已进其他终态（RETIRED/
        UNCERTAIN_TRAINED）的成员留 RECEIPT_IGNORED_TERMINAL 痕，终态不翻转。
        返回本次新入账的 attempt 列表。
        """

        members = self._batches.get(batch_id)
        if members is None:
            raise LedgerError(f"未知 batch {batch_id!r} 的训练回执——回执必须对应 seal 过的 batch")
        newly: list[str] = []
        for aid in list(members):
            rec = self._record(aid)
            if rec.state == HANDED_OFF:
                self._transition(aid, {HANDED_OFF}, FINALIZED, via="after_train_success", batch_id=batch_id)
                self.trained_attempts.append(aid)
                newly.append(aid)
            elif rec.state == FINALIZED:
                rec.history.append(("DUPLICATE_RECEIPT_NOOP", {"batch_id": batch_id}))
                self.duplicate_receipt_count += 1
            else:
                rec.history.append(("RECEIPT_IGNORED_TERMINAL", {"batch_id": batch_id, "state": rec.state}))
        return newly

    def mark_uncertain_trained(self, batch_id: str, *, reason: str = "receipt_window_crash") -> list[str]:
        """崩溃窗口记账：batch 的训练可能已成功但回执未持久化（决策包 v4
        at-least-once 语义）。把仍在 HANDED_OFF 的成员落 UNCERTAIN_TRAINED
        终态——不伪造 FINALIZED，也不声称未训练。"""

        members = self._batches.get(batch_id)
        if members is None:
            raise LedgerError(f"未知 batch {batch_id!r} 不能标记 uncertain_trained")
        moved: list[str] = []
        for aid in list(members):
            if self._record(aid).state == HANDED_OFF:
                self._transition(aid, {HANDED_OFF}, UNCERTAIN_TRAINED, reason=reason, batch_id=batch_id)
                moved.append(aid)
        return moved

    def mark_uncertain_attempt(self, aid: str, *, reason: str) -> None:
        """单 attempt 版（供关停 seam 使用）：HANDED_OFF 且拿不到回执的组
        一律落 UNCERTAIN_TRAINED——关停时无法证明 drain 出去的批是否已训练。"""

        self._transition(aid, {HANDED_OFF}, UNCERTAIN_TRAINED, reason=reason)

    # ------------------------------------------------------------------ 对账

    def assert_books_balanced(self) -> None:
        """总账检查：无双计、无悬空、账实一致、batch 成员账一致。"""

        if len(self.trained_attempts) != len(set(self.trained_attempts)):
            raise LedgerError("训练入账出现重复 attempt")
        if set(self.trained_attempts) != set(self.attempts_in_state(FINALIZED)):
            raise LedgerError("FINALIZED 集合与训练入账集合不一致")
        for rec in self._records.values():
            finalizes = [h for h in rec.history if h[0] == FINALIZED]
            if len(finalizes) > 1:
                raise LedgerError(f"{rec.attempt_id} 被 finalize 入账多次")
            if self._presence_probe is not None:
                expected = {ADMITTED: IN_INVENTORY, HANDED_OFF: IN_RESERVATION}.get(rec.state)
                actual = self._presence_probe(rec.attempt_id)
                if actual != expected:
                    raise LedgerError(
                        f"{rec.attempt_id}: 账面 {rec.state} 但物理位置 {actual!r}（期望 {expected!r}）"
                    )
        for batch_id, members in self._batches.items():
            for aid in members:
                if self._record(aid).batch_id != batch_id:
                    raise LedgerError(f"{aid}: batch 成员账不一致（{batch_id!r}）")
