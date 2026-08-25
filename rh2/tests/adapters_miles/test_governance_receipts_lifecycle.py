"""C7：显式训练回执（B2 修复）+ close/dispose seam（B5 修复）的测试。

覆盖四块：
1. FINALIZED 只能由显式 after_train_success(batch_id) 回执驱动；版本前进
   不触发 finalize 的**反测试**（构造 R5-ext §4.1 的 batch B 场景）；
2. miles train_async 预取真顺序的源码事实固定 + 连续 drain 两批的 CPU
   调度测试（按真顺序驱动治理件）；
3. UNCERTAIN_TRAINED 崩溃窗口（train 成功但回执未持久化）——at-least-once
   语义，不伪造 FINALIZED，迟到回执不翻转终态；
4. Rh2RolloutLifecycle.shutdown()：停新 submission → cancel 并 await 在飞
   task → 三类分别记账 → 幂等。
"""

from __future__ import annotations

import asyncio

import pytest


# =====================================================================
# 1. 显式回执驱动 FINALIZED（B2 修复面）
# =====================================================================


async def test_finalized_only_via_explicit_receipt(world):
    """FINALIZED 的唯一入口是 after_train_success：drain（get）与 seal 都
    不入训练账；回执落账后 via 痕可审计。同时固定"原型隐式路径已删除"：
    生产 buffer 上没有 finalize/_ack_older_than 面。"""

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    gate = asyncio.Event()
    gate.set()
    pg = world.mk_gov_prompt_group("pr1")
    aid = await world.run_attempt(ledger, buf, pg, gate)

    await buf.get(current_version=3)
    assert ledger.state(aid) == S.HANDED_OFF
    ledger.seal_batch("b1")
    assert ledger.state(aid) == S.HANDED_OFF  # seal 只定格成员，不入账
    assert ledger.trained_attempts == []

    assert ledger.after_train_success("b1") == [aid]
    assert ledger.state(aid) == S.FINALIZED
    assert any(k == S.FINALIZED and info.get("via") == "after_train_success" and info.get("batch_id") == "b1"
               for k, info in ledger.history(aid))
    assert buf.handed_off_unreceipted() == []  # 回执后 reservation 由账本 release 清空
    ledger.assert_books_balanced()

    # 原型的隐式 ACK 面已整体删除（回归绊线）：
    assert not hasattr(buf, "finalize")
    assert not hasattr(buf, "_ack_older_than")
    assert not hasattr(ledger, "finalize")


async def test_version_advance_does_not_finalize(world):
    """反测试（R5-ext B2 / blockers §4.1 的 batch B 场景）：

        batch B 在 version=5 时已被 drain 并 HANDED_OFF，但尚未训练；
        权重更新到 version=6；
        下一轮先开始 drain batch C —— batch C 的 get(current_version=6) 发生。

    P0-2 原型的 _ack_older_than 会在这一步把 batch B 提前 FINALIZED；
    生产实现必须保持 B 仍 HANDED_OFF（版本前进只说明 rollout engine 的
    权重状态变化，不证明任何具体 batch 已被 optimizer 消费）。"""

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    gate = asyncio.Event()
    gate.set()

    # batch B：version=5 时 drain 并 seal
    pg_b = world.mk_gov_prompt_group("pB")
    aid_b = await world.run_attempt(ledger, buf, pg_b, gate)
    await buf.get(current_version=5)
    ledger.seal_batch("batch-B")
    assert ledger.state(aid_b) == S.HANDED_OFF

    # 权重更新到 6 后，batch C 的 get(current_version=6) 到来
    pg_c = world.mk_gov_prompt_group("pC")
    aid_c = await world.run_attempt(ledger, buf, pg_c, gate)
    await buf.get(current_version=6)  # ← 原型在此把 B 误 finalize

    assert ledger.state(aid_b) == S.HANDED_OFF  # B 仍未入账：版本前进不是回执
    assert ledger.trained_attempts == []
    assert set(buf.handed_off_unreceipted()) == {aid_b, aid_c}

    # 只有显式回执才推进 B；C 不受影响
    assert ledger.after_train_success("batch-B") == [aid_b]
    assert ledger.state(aid_b) == S.FINALIZED
    assert ledger.state(aid_c) == S.HANDED_OFF
    ledger.seal_batch("batch-C")
    ledger.after_train_success("batch-C")
    ledger.assert_books_balanced()


async def test_receipt_surface_fail_closed(world):
    """回执面的 fail-closed：未知 batch 的回执/uncertain 标记直接拒绝；
    空 seal、重复 seal 是调用序错误。"""

    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    gate = asyncio.Event()
    gate.set()

    with pytest.raises(world.LedgerError, match="未知 batch"):
        ledger.after_train_success("no-such-batch")
    with pytest.raises(world.LedgerError, match="未知 batch"):
        ledger.mark_uncertain_trained("no-such-batch")
    with pytest.raises(world.LedgerError, match="没有可归属"):
        ledger.seal_batch("empty-batch")  # 无 HANDED_OFF 成员

    aid = await world.run_attempt(ledger, buf, world.mk_gov_prompt_group("pf"), gate)
    await buf.get(current_version=1)
    ledger.seal_batch("bf")
    with pytest.raises(world.LedgerError, match="已 seal 过"):
        ledger.seal_batch("bf")
    ledger.after_train_success("bf")
    assert ledger.trained_attempts == [aid]


# =====================================================================
# 2. miles train_async 预取真顺序（源码事实 + 连续 drain 两批调度测试）
# =====================================================================


def test_train_async_prefetch_true_order_source_facts(world):
    """固定 reference/miles/train_async.py:73-111 的真顺序（B2 证据源）：

    ① 73 行：进循环前就发起 generate(start_rollout_id)（batch 0 的 drain）；
    ② 76-78 行：循环第 N 轮先 await 上一次发起的 generate（batch N 完成）；
    ③ 80-81 行：**随即发起 generate(N+1)**——batch N+1 的 drain 在
       train(N) 之前启动；
    ④ 92 行：await actor_model.train(N)——训练在预取之后；
    ⑤ 107-111 行：update_weights 之前先 await 在飞的 generate(N+1)——
       所以 batch N+1 是在**旧版本**下完成 drain（HANDED_OFF），权重版本
       随后才前进；train(N+1) 要到下一轮循环才执行。

    推论：存在真实窗口——get(version=V+1)（batch N+2 的 drain）已发生，
    而 batch N+1 仍 HANDED_OFF 未训练。版本前进因此不能当训练回执。"""

    src = (world.miles_root / "train_async.py").read_text(encoding="utf-8")

    i_prefetch_head = src.index("rollout_data_next_future = rollout_manager.generate.remote(args.start_rollout_id)")
    i_await_curr = src.index("rollout_data_curr_ref = await rollout_data_next_future")
    i_prefetch_next = src.index("rollout_data_next_future = rollout_manager.generate.remote(rollout_id + 1)")
    i_train = src.index("await actor_model.train(rollout_id, rollout_data_curr_ref)")
    i_sync_before_update = src.index(
        "rollout_data_curr_ref = (await x) if (x := rollout_data_next_future) is not None else None"
    )
    i_update_weights = src.index("await actor_model.update_weights(rollout_id=rollout_id)")

    # ①②③④：预取在训练之前
    assert i_prefetch_head < i_await_curr < i_prefetch_next < i_train
    # ⑤：权重更新前先等 drain 完成——版本前进时上一批必然已 HANDED_OFF 而未必已训练
    assert i_train < i_sync_before_update < i_update_weights


async def test_two_batch_drain_follows_prefetch_order(world):
    """连续 drain 两批的 CPU 调度测试，按 train_async 真顺序驱动治理件
    （顺序依据见 test_train_async_prefetch_true_order_source_facts）：

        drain(batch0)@v5 → seal → drain(batch1)@v5（预取，train(batch0)
        之前发起）→ seal → train(batch0) 回执 → 权重 v5→v6 →
        drain(batch2) 首个 get@v6 → 此刻 batch1 仍 HANDED_OFF 未入账 →
        train(batch1) 回执。

    断言账本在每一步只反映"事实已训练"，不被预取/版本前进带偏。"""

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer(rollout_batch_size=2)
    gate = asyncio.Event()
    gate.set()

    async def produce(tag: str) -> str:
        return await world.run_attempt(ledger, buf, world.mk_gov_prompt_group(tag), gate)

    # batch0 的两组在 v5 drain（每步内所有 get 用同一 weight_version）
    b0 = [await produce("b0-x"), await produce("b0-y")]
    await buf.get(current_version=5)
    await buf.get(current_version=5)
    assert ledger.seal_batch("batch0") == b0

    # 预取：train(batch0) 尚未发生，batch1 已在 v5 drain（train_async ③⑤）
    b1 = [await produce("b1-x"), await produce("b1-y")]
    await buf.get(current_version=5)
    await buf.get(current_version=5)
    assert ledger.seal_batch("batch1") == b1
    assert ledger.trained_attempts == []  # 两批都 drain 完，训练账仍为空

    # train(batch0) 成功 → 显式回执（train_async ④：训练在预取之后）
    assert ledger.after_train_success("batch0") == b0
    assert [ledger.state(a) for a in b0] == [S.FINALIZED, S.FINALIZED]
    assert [ledger.state(a) for a in b1] == [S.HANDED_OFF, S.HANDED_OFF]

    # 权重 v5→v6（train_async ⑤：batch1 在旧版本下已 HANDED_OFF）；
    # batch2 的首个 get@v6 到来——batch1 必须仍不被入账
    await produce("b2-x")
    await buf.get(current_version=6)
    assert [ledger.state(a) for a in b1] == [S.HANDED_OFF, S.HANDED_OFF]
    assert set(ledger.trained_attempts) == set(b0)

    # train(batch1) 回执后才入账
    assert ledger.after_train_success("batch1") == b1
    assert set(ledger.trained_attempts) == set(b0) | set(b1)
    ledger.seal_batch("batch2")
    ledger.after_train_success("batch2")
    ledger.assert_books_balanced()


# =====================================================================
# 3. UNCERTAIN_TRAINED 崩溃窗口（决策包 v4 at-least-once）
# =====================================================================


async def test_uncertain_trained_window(world):
    """崩溃窗口：optimizer 已成功但回执未持久化时进程崩溃。恢复侧对该
    batch 调 mark_uncertain_trained——落 UNCERTAIN_TRAINED 终态：
    (a) 不伪造 FINALIZED（训练账为空）；
    (b) reservation 被账本 release 清空（账实一致）；
    (c) 迟到的回执重放只留 RECEIPT_IGNORED_TERMINAL 痕，终态不翻转——
        at-least-once 语义，不承诺 exactly-once。"""

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    gate = asyncio.Event()
    gate.set()
    pg = world.mk_gov_prompt_group("pu")
    aid = await world.run_attempt(ledger, buf, pg, gate)
    await buf.get(current_version=4)
    ledger.seal_batch("bu")

    # —— 此刻 train 成功，但进程在 after_train_success 持久化前崩溃 ——
    # 恢复侧无法证明训练是否入账，唯一诚实的记法：
    assert ledger.mark_uncertain_trained("bu") == [aid]
    assert ledger.state(aid) == S.UNCERTAIN_TRAINED
    assert ledger.trained_attempts == []  # (a) 绝不伪造 FINALIZED
    assert buf.handed_off_unreceipted() == []  # (b) 账实一致
    assert buf.audit_inventory() == []

    # (c) 回执重放（at-least-once 投递）到达——终态不翻转，只留痕
    assert ledger.after_train_success("bu") == []
    assert ledger.state(aid) == S.UNCERTAIN_TRAINED
    assert ("RECEIPT_IGNORED_TERMINAL", {"batch_id": "bu", "state": S.UNCERTAIN_TRAINED}) in ledger.history(aid)
    ledger.assert_books_balanced()


# =====================================================================
# 4. Rh2RolloutLifecycle.shutdown()（B5 修复面）
# =====================================================================


async def _naked_producer(ledger, pg):
    """无 CancelledError 记账分支的生产 task——模拟"在 dispatch 与 put 之间
    被关停打断且自身没有兜底"的最坏情况，账由 shutdown 扫尾补记。"""

    ledger.dispatch(pg)
    await asyncio.Event().wait()  # 永不完成


async def test_shutdown_accounts_three_categories(world):
    """shutdown 的三类记账（模块 docstring 第 3 步）：
    - 未入 buffer（DISPATCHED）→ CRASHED_BEFORE_PUT(kind="shutdown")；
    - buffer 内（ADMITTED）→ RETIRED(reason="shutdown")；
    - 已 handed-off 未回执（HANDED_OFF）→ UNCERTAIN_TRAINED——关停时无法
      证明 drain 出去的批是否已训练，不伪造 FINALIZED。
    task 层已自记的 crash（run_attempt 的 CancelledError 分支）不被双记。"""

    S = world.ledger_states
    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    lifecycle = world.Rh2RolloutLifecycle(ledger)
    gate_open = asyncio.Event()
    gate_open.set()
    gate_stuck = asyncio.Event()  # 永不放行

    # ① 未入 buffer：一个裸生产 task（无自记账）+ 一个 run_attempt（有自记账）
    pg_naked = world.mk_gov_prompt_group("sd-naked")
    lifecycle.spawn(_naked_producer(ledger, pg_naked))
    pg_self = world.mk_gov_prompt_group("sd-self")
    lifecycle.spawn(world.run_attempt(ledger, buf, pg_self, gate_stuck))
    await asyncio.sleep(0.01)  # 两个 task 都跑到挂起点
    aid_naked = pg_naked[0].metadata[world.ATTEMPT_KEY]
    aid_self = pg_self[0].metadata[world.ATTEMPT_KEY]

    # ③ 已 handed-off：先入队先取走（FIFO），无回执
    pg_hand = world.mk_gov_prompt_group("sd-hand")
    aid_hand = await world.run_attempt(ledger, buf, pg_hand, gate_open)
    await buf.get(current_version=2)

    # ② buffer 内：入队后不取
    pg_buf = world.mk_gov_prompt_group("sd-buf")
    aid_buf = await world.run_attempt(ledger, buf, pg_buf, gate_open)

    closed_hooks: list[str] = []

    async def close_adapter():
        closed_hooks.append("adapter")

    lifecycle.register_close_hook(close_adapter)

    report = await lifecycle.shutdown()

    # 三类账各归各位
    assert ledger.state(aid_naked) == S.CRASHED_BEFORE_PUT
    assert ledger.state(aid_self) == S.CRASHED_BEFORE_PUT  # task 自记（kind="cancelled"）
    assert ledger.state(aid_buf) == S.RETIRED
    assert ledger.state(aid_hand) == S.UNCERTAIN_TRAINED
    # 报告只含扫尾补记的那笔 crash——task 自记的不双记
    assert report["crashed_before_put"] == [aid_naked]
    assert report["retired_in_buffer"] == [aid_buf]
    assert report["uncertain_trained"] == [aid_hand]
    assert report["cancelled_tasks"] == 2
    assert report["close_hook_errors"] == []
    assert closed_hooks == ["adapter"]
    # 自记的 crash 只有一次转移痕（无 DUPLICATE_CRASH_MARK 之外的双记）
    assert sum(1 for k, _ in ledger.history(aid_self) if k == S.CRASHED_BEFORE_PUT) == 1
    # 账实一致：终态占位全部被 release 清空
    assert buf.audit_inventory() == []
    assert buf.handed_off_unreceipted() == []
    assert ledger.trained_attempts == []
    ledger.assert_books_balanced()


async def test_shutdown_is_idempotent_and_refuses_new_work(world):
    """幂等（模块 docstring 第 4 步）：第二次 shutdown 返回第一次的报告
    对象，不产生新转移、close hook 不重跑、无新错误；关闭后 spawn 与
    register_close_hook 均被拒绝。"""

    buf, ledger, _clock, _recycled = world.mk_governed_buffer()
    lifecycle = world.Rh2RolloutLifecycle(ledger)
    gate = asyncio.Event()
    gate.set()
    aid = await world.run_attempt(ledger, buf, world.mk_gov_prompt_group("idem"), gate)

    hook_calls: list[int] = []

    async def hook():
        hook_calls.append(1)

    lifecycle.register_close_hook(hook)

    report1 = await lifecycle.shutdown()
    history_len = len(ledger.history(aid))

    report2 = await lifecycle.shutdown()  # 二次调用：无新错误
    assert report2 is report1  # 同一份报告
    assert len(ledger.history(aid)) == history_len  # 无新转移
    assert hook_calls == [1]  # close hook 只跑一次

    assert not lifecycle.accepting
    with pytest.raises(world.LifecycleClosedError):
        lifecycle.spawn(_naked_producer(ledger, world.mk_gov_prompt_group("late")))
    with pytest.raises(world.LifecycleClosedError):
        lifecycle.register_close_hook(hook)
    ledger.assert_books_balanced()
