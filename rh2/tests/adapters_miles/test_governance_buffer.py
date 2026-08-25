"""治理账本 + 治理 buffer 的故障注入测试（P0-2 的 13 场景迁移升级 + C3）。

被测对象从 spike 原型（scratchpad/test_miles_spike_p02_faults.py 内联类）
升级为生产实现：`repoharness2.adapters.miles.attempt_ledger.Rh2AttemptLedger`
与 `repoharness2.adapters.miles.governed_buffer.Rh2GovernedBuffer`（实现
miles DataBuffer ABC，内部包真 DefaultDataBuffer）。构造走 miles 真实装配
形状（DataBufferConstructorInput + args.rh2_governance 注入，见 conftest
`mk_governed_buffer`）。

与原型的关键差异（详见各测试）：
- FINALIZED 只能由显式 `after_train_success(batch_id)` 回执驱动——原型的
  buf.finalize(aid) 与版本前进隐式 ACK（auto_ack/_ack_older_than）已删除，
  回执/预取顺序测试在 test_governance_receipts_lifecycle.py；
- dynamic filter drop 由本层单点 verdict 逐 attempt 记 REJECTED_FILTERED
  （C3，修 R4 finding"drop 被误记 ADMITTED"）；
- "ADMITTED 必真实在 buffer/reservation"不变量由账本内部强制（presence
  探针前置核对 + 对账兜底），不再是测试自觉。

场景编号沿用 P0-2（s1~s6c），便于与 spike-log 对照。
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

STOCK_NONZERO_STD_FILTER = "miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std"


# =====================================================================
# 场景 1：put 前 crash（cancel / 异常）
# =====================================================================


@pytest.mark.parametrize("fail_mode", ["cancelled", "exception"])
async def test_s1_crash_before_put(world, fail_mode):
    """生产 task 在 put 之前死掉（cancel 或异常）时——
    (a) 组不出现在 buffer（真 DefaultDataBuffer 空，get 一直挂起）；
    (b) 账目是 CRASHED_BEFORE_PUT，与 ADMITTED/FINALIZED 可区分（能审计出
        "从未提交"而不是"提交后丢失"）；
    (c) 同一 prompt 可重派：dispatch 重盖章新 attempt id，旧账不受影响，
        重派后走完 put→get→seal→显式回执，训练账恰好 1 笔（新 attempt）。
    """

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    pg = world.mk_gov_prompt_group("p1")
    gate = asyncio.Event()

    task = asyncio.create_task(
        world.run_attempt(ledger, buf, pg, gate, fail="exception" if fail_mode == "exception" else None)
    )
    await asyncio.sleep(0.01)  # 让 task 跑到 gate.wait()（生成在飞）
    aid1 = pg[0].metadata[world.ATTEMPT_KEY]
    assert ledger.state(aid1) == S.DISPATCHED

    if fail_mode == "cancelled":
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        gate.set()
        with pytest.raises(RuntimeError):
            await task

    # (a) buffer 空：盘点为空，且真 get 挂起（0.05s 内不完成）
    assert buf.audit_inventory() == []
    hung_get = asyncio.create_task(buf.get(current_version=1))
    await asyncio.sleep(0.05)
    assert not hung_get.done()
    hung_get.cancel()
    with pytest.raises(asyncio.CancelledError):
        await hung_get

    # (b) 账目区分"从未提交"
    assert ledger.state(aid1) == S.CRASHED_BEFORE_PUT
    assert ledger.attempts_in_state(S.ADMITTED) == []

    # (c) 重派同一 prompt：新 attempt 正常入账（显式回执驱动 FINALIZED）
    gate2 = asyncio.Event()
    gate2.set()
    aid2 = await world.run_attempt(ledger, buf, pg, gate2)
    assert aid2 != aid1
    entry = await buf.get(current_version=1)
    assert world.governed_buffer_mod.attempt_of(entry.group) == aid2
    assert ledger.seal_batch("b-s1") == [aid2]
    assert ledger.after_train_success("b-s1") == [aid2]
    assert ledger.trained_attempts == [aid2]
    ledger.assert_books_balanced()


# =====================================================================
# 场景 2：put 后 get 前 crash（消费者未取，生产侧/循环已崩）
# =====================================================================


async def test_s2_inflight_inventory_enumerable_after_crash(world):
    """组已 put 进 buffer 但训练侧从未 get 时（模拟 driver/worker 在两者
    之间崩溃），在飞组清单可枚举、可与账本对账。

    附带固定 miles 真实现事实：DefaultDataBuffer 的存量在私有属性
    _buffer（list）里，ABC 契约面没有枚举/快照方法——盘点面由治理 buffer
    的影子清单（audit_inventory）提供。
    """

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    gate = asyncio.Event()
    gate.set()
    pg_a, pg_b = world.mk_gov_prompt_group("pa"), world.mk_gov_prompt_group("pb")
    aid_a = await world.run_attempt(ledger, buf, pg_a, gate)
    aid_b = await world.run_attempt(ledger, buf, pg_b, gate)

    # 此刻模拟崩溃：没有任何 get 发生。盘点：
    assert buf.audit_inventory() == sorted([(aid_a, "pa"), (aid_b, "pb")])
    assert set(ledger.attempts_in_state(S.ADMITTED)) == {aid_a, aid_b}
    assert ledger.trained_attempts == []  # 未取走的组绝不在训练账里

    # miles 真实现事实：存量确实在 DefaultDataBuffer._buffer（私有属性）
    assert len(buf._inner._buffer) == 2  # noqa: SLF001 —— 取证，非契约用法
    attempt_of = world.governed_buffer_mod.attempt_of
    assert {attempt_of(e.group) for e in buf._inner._buffer} == {aid_a, aid_b}  # noqa: SLF001
    ledger.assert_books_balanced()


# =====================================================================
# 场景 3：重复回执（重试/竞态）—— 幂等留痕
# =====================================================================


async def test_s3_duplicate_receipt_is_idempotent_noop(world):
    """同一 batch 的训练成功回执被投递两次（at-least-once 回执可能重投）——
    第一次入账，第二次是 no-op：训练账仍恰好 1 份，但账本留痕
    （DUPLICATE_RECEIPT_NOOP + duplicate_receipt_count），事后可审计出
    发生过重复回执。exactly-once 由 receipt 层保证，与 miles 无关。

    与原型差异：原型的 buf.finalize(aid) 面已删除，入账入口统一为
    ledger.after_train_success(batch_id)。
    """

    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    gate = asyncio.Event()
    gate.set()
    pg = world.mk_gov_prompt_group("p3")
    aid = await world.run_attempt(ledger, buf, pg, gate)
    await buf.get(current_version=1)
    ledger.seal_batch("b-s3")

    assert ledger.after_train_success("b-s3") == [aid]  # 第一次：入账
    assert ledger.after_train_success("b-s3") == []  # 第二次：no-op
    assert ledger.trained_attempts == [aid]  # 无双重训练账目
    assert ledger.duplicate_receipt_count == 1
    assert ("DUPLICATE_RECEIPT_NOOP", {"batch_id": "b-s3"}) in ledger.history(aid)  # 留痕
    assert buf.get_metrics()["rh2/governed_buffer/duplicate_receipt"] == 1.0
    ledger.assert_books_balanced()


# =====================================================================
# 场景 4：撤销后晚响应
# =====================================================================


async def test_s4_late_result_after_retirement_not_admitted(world):
    """组 A1 已被治理撤销（RETIRED），同一 prompt 已重派为 A2 并完成入账；
    之后 A1 的旧结果才姗姗来迟——
    (a) 旧结果在治理层 put 即被拦截，完全不触碰 miles buffer；
    (b) 训练账只有 A2 一笔，A1 留 LATE_RESULT_DISCARDED 痕；
    (c) 区分依据 = metadata 里的 physical_attempt_id，每次 dispatch 重盖章。

    附带固定 miles 真行为：Sample.reset_for_retry() 保留 metadata（含旧
    attempt id）——"重新盖章"必须发生在 dispatch 时刻（账本 dispatch 无条件
    覆写），不能指望回收路径清除身份。
    """

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    pg = world.mk_gov_prompt_group("p4")

    aid1 = ledger.dispatch(pg)
    late_group = world.mk_gov_finished_group(pg)  # A1 结果已生成但尚未 put（在网络/队列里晚到）

    # 治理判定：A1 撤销 + 回收 prompt（真 miles 回收语义：reset_for_retry）
    ledger.retire(aid1, reason="stale_abort")
    for s in pg:
        s.reset_for_retry()
    assert pg[0].metadata[world.ATTEMPT_KEY] == aid1  # miles 事实：metadata 存活 → 必须重盖章

    # 重派 A2 并正常走完（显式回执）
    aid2 = ledger.dispatch(pg)
    assert pg[0].metadata[world.ATTEMPT_KEY] == aid2  # dispatch 重盖章
    group2 = world.mk_gov_finished_group(pg)
    await buf.put(world.mk_entry(pg, group2))
    entry = await buf.get(current_version=1)
    assert world.governed_buffer_mod.attempt_of(entry.group) == aid2
    ledger.seal_batch("b-s4")
    ledger.after_train_success("b-s4")

    # A1 旧结果此刻才到达
    await buf.put(world.mk_entry(pg, late_group))
    assert buf.audit_inventory() == []  # (a) 未进治理面
    assert len(buf._inner._buffer) == 0  # noqa: SLF001 —— (a) miles 真 buffer 也未被触碰
    assert ledger.trained_attempts == [aid2]  # (b) 不混入新账
    assert ledger.late_discard_count == 1
    assert ("LATE_RESULT_DISCARDED", {"state": S.RETIRED}) in ledger.history(aid1)
    ledger.assert_books_balanced()


async def test_s4b_stale_recycle_on_get_is_retired_in_ledger(world):
    """撤销判定也可以由 miles 真 get 的 staleness 过滤触发——治理层通过
    包装 unused_handler 观察回收回调，把对应 attempt 记 RETIRED；之后该
    attempt 的晚响应同样被拦截。rh2 不重写 staleness 过滤，真
    DefaultDataBuffer 的拒收路径被外层完整记账。"""

    S = world.ledger_states
    buf, ledger, _clock, recycled = world.mk_governed_buffer(max_weight_staleness=2)
    pg_old, pg_new = world.mk_gov_prompt_group("p4old"), world.mk_gov_prompt_group("p4new")

    aid_old = ledger.dispatch(pg_old)
    stale_group = world.mk_gov_finished_group(pg_old, versions=(3, 3))
    await buf.put(world.mk_entry(pg_old, stale_group))
    aid_new = ledger.dispatch(pg_new)
    fresh_group = world.mk_gov_finished_group(pg_new, versions=(9, 9))
    await buf.put(world.mk_entry(pg_new, fresh_group))

    entry = await buf.get(current_version=10)  # miles 真 staleness 过滤：10-3=7 > 2 回收 old
    assert world.governed_buffer_mod.attempt_of(entry.group) == aid_new
    assert ledger.state(aid_old) == S.RETIRED
    assert recycled == [pg_old]  # 真 unused_handler 回调发生过（下游回收面保留）

    # old 的重复/晚到结果再 put → 拦截
    await buf.put(world.mk_entry(pg_old, stale_group))
    assert ledger.late_discard_count == 1
    ledger.seal_batch("b-s4b")
    ledger.after_train_success("b-s4b")
    assert ledger.trained_attempts == [aid_new]
    ledger.assert_books_balanced()


# =====================================================================
# 场景 5：get 后消费方崩溃（取走未确认）→ lease 收回
# =====================================================================


async def test_s5_lease_reclaim_after_consumer_crash(world):
    """miles 的 get 是"取走即消费"（pop 后 buffer 不再知道这组的存在）。
    治理层在 get 里包 reservation：取走 = HANDED_OFF + lease 截止时间；
    消费方崩溃（永不回执）→ lease 超时 → reap 把组重新 put 回真 buffer，
    可被再次 get；全程账本无重复入账。

    与原型差异：消费成功确认只剩两条路——显式 after_train_success 回执
    （正路）与 lease 超时收回（兜底）；版本前进隐式 ack（原型第三条路）
    已删除（R5-ext B2 证伪，反测试见 receipts 测试文件）。
    """

    S = world.ledger_states
    buf, ledger, clock, _recycled = world.mk_governed_buffer(lease=10.0)
    gate = asyncio.Event()
    gate.set()
    pg = world.mk_gov_prompt_group("p5")
    aid = await world.run_attempt(ledger, buf, pg, gate)

    entry1 = await buf.get(current_version=5)
    assert ledger.state(aid) == S.HANDED_OFF
    # —— 消费方在此崩溃：不回执也没有任何通知（miles 语义下 buffer 一无所知）——

    clock.advance(5.0)
    assert await buf.reap_expired() == []  # lease 未到期：不收回
    clock.advance(6.0)
    assert await buf.reap_expired() == [aid]  # 超时收回
    assert ledger.state(aid) == S.ADMITTED  # 回到可再取状态，历史留 reclaimed_at 痕
    assert any(k == S.ADMITTED and "reclaimed_at" in info for k, info in ledger.history(aid))

    entry2 = await buf.get(current_version=6)  # 再次取走同一组
    assert entry2 is entry1  # 同一 DataBufferInput 对象（组数据未复制未丢失）
    ledger.seal_batch("b-s5")
    assert ledger.after_train_success("b-s5") == [aid]
    assert ledger.trained_attempts == [aid]  # 收回-重取不产生双账
    ledger.assert_books_balanced()


# =====================================================================
# C3：dynamic filter 单点 verdict + 逐 attempt 记账（修 R4 finding）
# =====================================================================


async def test_c3_dynamic_drop_per_attempt_accounting(world):
    """C3 验收探针（spike-log 待办原文）：被 filter 拒的 attempt 进显式
    拒绝终态（REJECTED_FILTERED）、不在 inventory、inner buffer 空、总账
    守恒。filter 用 miles stock check_reward_nonzero_std（真函数），drop
    reason 计入 metrics（口径与 miles MetricGatherer 一致）。

    R4 finding 回放：原型经 unused_handler 计数判准入，而 miles 的
    dynamic-filter drop 直接 return 不走回调（fully_async_data_buffer.py:
    131-134）——原型会把被 drop 的组误记 ADMITTED。生产实现 verdict 移到
    本层单点执行，误记路径不复存在。
    """

    S = world.ledger_states
    buf, ledger, _clock, recycled = world.mk_governed_buffer(
        dynamic_sampling_filter_path=STOCK_NONZERO_STD_FILTER
    )

    # drop 路径：全同 reward → 零方差 → stock filter 拒
    pg_drop = world.mk_gov_prompt_group("pdrop")
    aid_drop = ledger.dispatch(pg_drop)
    await buf.put(world.mk_entry(pg_drop, world.mk_gov_finished_group(pg_drop, rewards=(0.5, 0.5))))

    assert ledger.state(aid_drop) == S.REJECTED_FILTERED  # 显式拒绝终态，非无痕消失
    assert buf.audit_inventory() == []  # 不在 inventory
    assert len(buf._inner._buffer) == 0  # noqa: SLF001 —— inner buffer 空
    assert recycled == []  # 与 miles 语义一致：drop 不回收（无梯度信号）
    assert any(k == S.REJECTED_FILTERED and info.get("reason") == "zero_std_0.5"
               for k, info in ledger.history(aid_drop))

    # keep 路径继续正常（reward 0.0/1.0 方差非零）
    pg_keep = world.mk_gov_prompt_group("pkeep")
    aid_keep = ledger.dispatch(pg_keep)
    await buf.put(world.mk_entry(pg_keep, world.mk_gov_finished_group(pg_keep)))
    assert ledger.state(aid_keep) == S.ADMITTED
    assert buf.audit_inventory() == [(aid_keep, "pkeep")]

    # drop reason 进 metrics（本层自持 MetricGatherer，key 口径与 miles 相同）
    metrics = buf.get_metrics()
    assert metrics["rollout/dynamic_filter/drop_zero_std_0.5"] == 1

    # 总账守恒：dispatch 2 笔 = REJECTED_FILTERED 1 + ADMITTED 1，无悬空
    assert ledger.attempts_in_state(S.REJECTED_FILTERED) == [aid_drop]
    assert ledger.attempts_in_state(S.ADMITTED) == [aid_keep]
    assert ledger.attempts_in_state(S.DISPATCHED) == []
    ledger.assert_books_balanced()


async def test_c3_verdict_executed_exactly_once_inner_filter_disabled(world):
    """C3 的"只执行一次"探针：inner DefaultDataBuffer 构造时 filter 已置空
    （dynamic_sampling_filter_path=None），verdict 唯一执行点在治理层——
    用计数 filter（经 miles function_registry 官方注入面）证明一次 put
    恰好一次调用（若 inner 也装载会是两次）。"""

    from miles.utils.misc import function_registry

    calls: list[int] = []

    def counting_filter(args, samples, **kwargs):
        calls.append(len(samples))
        return True  # legacy bool 形态，call_dynamic_filter 会包成 DynamicFilterOutput

    with function_registry.temporary("rh2_c3_counting_filter", counting_filter):
        buf, ledger, _clock, _recycled = world.mk_governed_buffer(
            dynamic_sampling_filter_path="rh2_c3_counting_filter"
        )
        assert buf._inner._dynamic_filter is None  # noqa: SLF001 —— inner filter 已关
        assert buf._dynamic_filter is counting_filter  # noqa: SLF001 —— verdict 归本层

        pg = world.mk_gov_prompt_group("ponce")
        ledger.dispatch(pg)
        await buf.put(world.mk_entry(pg, world.mk_gov_finished_group(pg)))
        assert calls == [2]  # 恰好一次 verdict（组内 2 样本）
        ledger.assert_books_balanced()


# =====================================================================
# 治理 put 的背压 cancel 记账路径（P0-2 s6c 缺口的生产接法）
# =====================================================================


async def test_governed_put_backpressure_cancel_is_accounted(world):
    """P0-2 s6c 固定过：put 在容量背压等待中被 cancel 时，组在 miles 侧
    无痕消失（不进 buffer、不走 unused_handler）。生产治理层在 inner.put
    的 CancelledError 路径记 CRASHED_BEFORE_PUT(kind=
    "put_backpressure_cancelled") 后原样重抛——账不丢，buffer 状态健康。"""

    S = world.ledger_states
    buf, ledger, _clock, recycled = world.mk_governed_buffer(
        async_data_buffer_capacity_factor=0.5, rollout_batch_size=2  # 容量 = 1
    )
    pg1, pg2 = world.mk_gov_prompt_group("g1"), world.mk_gov_prompt_group("g2")
    ledger.dispatch(pg1)
    await buf.put(world.mk_entry(pg1, world.mk_gov_finished_group(pg1)))  # 占满容量
    aid2 = ledger.dispatch(pg2)
    blocked = asyncio.create_task(buf.put(world.mk_entry(pg2, world.mk_gov_finished_group(pg2))))
    await asyncio.sleep(0.02)
    assert not blocked.done()  # 真背压：put 阻塞中

    blocked.cancel()
    with pytest.raises(asyncio.CancelledError):
        await blocked

    # 记账路径命中：不是无痕消失
    assert ledger.state(aid2) == S.CRASHED_BEFORE_PUT
    assert any(k == S.CRASHED_BEFORE_PUT and info.get("kind") == "put_backpressure_cancelled"
               for k, info in ledger.history(aid2))
    assert recycled == []  # miles 事实不变：无回收回调
    ledger.assert_books_balanced()

    # buffer 健康：get 取回 g1 后，重派 g2 可正常入队
    await asyncio.wait_for(buf.get(current_version=1), timeout=1)
    aid2b = ledger.dispatch(pg2)
    await asyncio.wait_for(buf.put(world.mk_entry(pg2, world.mk_gov_finished_group(pg2))), timeout=1)
    assert ledger.state(aid2b) == S.ADMITTED


# =====================================================================
# 不变量：ADMITTED/HANDED_OFF 必真实在 buffer/reservation（账本内部强制）
# =====================================================================


async def test_ledger_enforces_presence_invariant(world):
    """不变量 (a)：进入 ADMITTED 前物理位置必须已在影子清单——绕过治理
    buffer 直接调 ledger.admit 当场被拒（转移不发生）；事后账实被篡改则由
    assert_books_balanced 对账兜底。"""

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    pg = world.mk_gov_prompt_group("pinv")
    aid = ledger.dispatch(pg)

    with pytest.raises(world.LedgerError, match="账实不符"):
        ledger.admit(aid)  # 未经过 buffer put，物理位置不存在
    assert ledger.state(aid) == S.DISPATCHED  # 前置核对：非法转移未落账

    await buf.put(world.mk_entry(pg, world.mk_gov_finished_group(pg)))
    assert ledger.state(aid) == S.ADMITTED
    ledger.assert_books_balanced()

    buf._inventory.pop(aid)  # noqa: SLF001 —— 模拟账实被篡改/丢失
    with pytest.raises(world.LedgerError, match="物理位置"):
        ledger.assert_books_balanced()


# =====================================================================
# 场景 6：背压下 cancel —— 对 miles 真 DefaultDataBuffer 直接测（事实固定）
# =====================================================================


def _mk_default_buffer(world, recycled: list, capacity_factor: float = 0.5):
    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer

    args = world.mk_miles_args(async_data_buffer_capacity_factor=capacity_factor, rollout_batch_size=2)
    return DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))


def _mk_tagged_entry(world, tag: str):
    pg = world.mk_gov_prompt_group(tag)
    pg[0].metadata[world.ATTEMPT_KEY] = tag  # 仅测 miles 真件，直接用 tag 当身份
    return world.mk_entry(pg, world.mk_gov_finished_group(pg))


async def test_s6_cancel_blocked_put_condition_stays_healthy(world):
    """miles 真代码行为：容量满时 put 阻塞在 asyncio.Condition.wait()；
    cancel 该 put——(a) Condition/锁不腐坏，后续 put/get 全部正常；
    (b) 容量账不腐坏；(c) FIFO 顺序保持。"""

    recycled: list = []
    buf = _mk_default_buffer(world, recycled)  # 容量 = 1

    e1, e2, e3 = (_mk_tagged_entry(world, t) for t in ("g1", "g2", "g3"))
    await buf.put(e1)  # 占满容量
    blocked = asyncio.create_task(buf.put(e2))
    await asyncio.sleep(0.02)
    assert not blocked.done()  # 真背压：put 阻塞中

    blocked.cancel()
    with pytest.raises(asyncio.CancelledError):
        await blocked

    # (a)(b) cancel 后 buffer 状态健康：get 取回 g1，随后 put g3 立即成功
    out1 = await asyncio.wait_for(buf.get(current_version=None), timeout=1)
    assert out1 is e1
    await asyncio.wait_for(buf.put(e3), timeout=1)
    out3 = await asyncio.wait_for(buf.get(current_version=None), timeout=1)
    assert out3 is e3
    assert len(buf._buffer) == 0  # noqa: SLF001


async def test_s6b_cancel_one_waiter_does_not_starve_the_other(world):
    """两个 put 都阻塞在满员等待，cancel 其中一个后，一次 get 腾出的名额
    必须唤醒幸存的那个（notify_all 语义，无 lost-wakeup）。治理层收回/重放
    会造成并发 put，单个 put 被 cancel 不得饿死其它生产者。"""

    recycled: list = []
    buf = _mk_default_buffer(world, recycled)  # 容量 = 1
    entries = [_mk_tagged_entry(world, f"w{i}") for i in range(3)]

    await buf.put(entries[0])
    waiter_a = asyncio.create_task(buf.put(entries[1]))
    waiter_b = asyncio.create_task(buf.put(entries[2]))
    await asyncio.sleep(0.02)
    assert not waiter_a.done() and not waiter_b.done()

    waiter_a.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter_a

    await asyncio.wait_for(buf.get(current_version=None), timeout=1)  # 腾出 1 个名额
    await asyncio.wait_for(waiter_b, timeout=1)  # 幸存 waiter 被唤醒并完成
    out = await asyncio.wait_for(buf.get(current_version=None), timeout=1)
    assert out is entries[2]


async def test_s6c_cancelled_put_loses_group_without_recycle(world):
    """固定 miles 真实行为（rh2 迁移必须记住的账目缺口）：put 在背压等待中
    被 cancel 时，这个组既不进 buffer、也不走 unused_handler——组直接消失，
    miles 侧无任何账目痕迹。该缺口的生产接法（治理层 CancelledError 记账）
    见 test_governed_put_backpressure_cancel_is_accounted。"""

    recycled: list = []
    buf = _mk_default_buffer(world, recycled)  # 容量 = 1
    e1, e2 = _mk_tagged_entry(world, "h1"), _mk_tagged_entry(world, "h2")
    await buf.put(e1)
    blocked = asyncio.create_task(buf.put(e2))
    await asyncio.sleep(0.02)
    blocked.cancel()
    with pytest.raises(asyncio.CancelledError):
        await blocked

    assert recycled == []  # 事实：没有回收回调 —— 组无痕消失
    assert len(buf._buffer) == 1  # noqa: SLF001 —— 只剩 h1；h2 不在任何 miles 可见状态里


# =====================================================================
# ABC / driver 契约面事实断言（供报告引用，不是行为测试）
# =====================================================================


def test_abc_surface_facts(world):
    """固定 miles 契约面的四条事实（P0-2 判定"ABC 面够不够"的证据，迁移
    自原型并保持有效）：
    (1) DataBuffer.get 的扩展面是 **context（kwargs 任意扩展）；
    (2) fully-async driver 实际只传 current_version 一个 kwarg；
    (3) DataBuffer.put 返回 None——没有准入回执，外层只能靠包装
        unused_handler 回调做拒收关联（dynamic-filter drop 连回调都没有，
        这正是 C3 把 verdict 移到治理层的原因）；
    (4) driver 每训练步在 _drain 末尾调一次 get_metrics——这是 ABC 面上
        唯一的"步边界"信号，且发生在训练执行之前（drain 完成时），
        **不能当训练成功回执用**（与 B2 的显式回执设计互为印证）。
    """

    from miles.rollout.fully_async_data_buffer import DataBuffer

    # (1) get 签名
    params = inspect.signature(DataBuffer.get).parameters
    assert [p.kind for p in params.values()] == [
        inspect.Parameter.POSITIONAL_OR_KEYWORD,  # self
        inspect.Parameter.VAR_KEYWORD,  # **context
    ]
    # (3) put 无返回值注解（None）
    assert inspect.signature(DataBuffer.put).return_annotation in (None, "None")

    # (2)(4) driver 源码事实。直接读文件文本断言（fully_async_rollout 的
    # import 链经 generate_utils 拉 sglang/pybase64 等重依赖，CPU venv 不装；
    # 与 train_async 预取顺序测试同一取证模式）。
    repo_root = world.rh2_src.parents[1]
    driver_src = (repo_root / "reference" / "miles" / "miles" / "rollout" / "fully_async_rollout.py").read_text(
        encoding="utf-8"
    )
    assert "self._output.get(current_version=current_version)" in driver_src
    # (4) get_metrics 在 _drain 的 return 语句里（drain 结束 = 批组装完，训练还没开始）
    assert "return RolloutFnTrainOutput(samples=data, metrics=self._output.get_metrics())" in driver_src


async def test_abc_put_returns_none_on_both_paths(world):
    """事实 (3) 的行为版：准入与拒收两条路径 put 都返回 None——调用方从
    返回值上无法区分组是否被收下。"""

    recycled: list = []
    buf = _mk_default_buffer(world, recycled, capacity_factor=2.0)
    entry_ok = _mk_tagged_entry(world, "r1")
    assert await buf.put(entry_ok) is None  # 准入

    entry_bad = _mk_tagged_entry(world, "r2")
    entry_bad.group[0].status = world.MS.Status.ABORTED
    assert await buf.put(entry_bad) is None  # 拒收
    assert recycled == [entry_bad.prompt_group]  # 拒收只能从 handler 回调观察到
