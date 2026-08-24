"""F2-3 联合终核回归（二轮改真实生产链）：

1. RolloutOrchestrator.generate → drain owner Fatal → **generate 侧真实
   notifier 接线**在异步 cleanup（drop_session 阻塞中）前置 halt →
   cleanup 未结束时 worker.halt_reason 已可见 → 同因 WorkerHalted。
   （旧测试手工复刻 notifier 调用——误删 generate 真实接线仍会过，已换。）
2. drain 命令准入/过期与首次 revoke 共 registry._lock 临界区的线性化
   不变量：调用方收到 expired 判决 ⇒ 永不 revoke。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    MockSessionAdapter,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
)

from repoharness2.adapters.slime.async_worker import (  # noqa: E402
    BoundedDeliveryQueue,
    ContinuousExecutionWorker,
    ExecutionTaskSpec,
    WorkerHalted,
)
from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402


class _FrozenWs:
    def __init__(self, underlying):
        self._u = underlying

    async def run_bash(self, script):
        return await self._u.run_bash(script)


class _Barrier:
    async def establish(self, *, workspace, audit):
        return QuiescenceConfirmed(
            frozen_grading_workspace=_FrozenWs(workspace),
            snapshot_ref="sha256:abc", evidence_refs=("s",))


async def test_fatal_visible_before_cleanup_via_real_generate_chain():
    """真实链：generate 内 drain owner 抛 Fatal → generate 的 notifier
    接线（非测试复刻）在 drop_session 阻塞期间已置 halt。"""

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns)
    _stamp_fa_identity(chain.base_sample)

    async def _fatal_owner(sid):
        raise OSError("owner exploded")  # → session_drain_owner_failed Fatal

    chain.orchestrator._session_drain_owner = _fatal_owner

    cleanup_blocker = asyncio.Event()
    entered_cleanup = asyncio.Event()
    orig_drop = MockSessionAdapter.drop_session

    async def blocking_drop(self, sid, **kw):
        entered_cleanup.set()
        await cleanup_blocker.wait()  # 模拟慢 cleanup 窗口
        return await orig_drop(self, sid, **kw)

    MockSessionAdapter.drop_session = blocking_drop
    specs = [ExecutionTaskSpec(rollout_execution_id="exec_fv",
                               prompt_group_id="g", member_slot=0)]
    queue = list(specs)

    async def execute(spec):
        return await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))

    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=4),
        failure_sink=lambda spec, exc: None,
        concurrency=1,
    )
    stop = asyncio.Event()
    run_task = asyncio.create_task(worker.run(stop))
    try:
        await asyncio.wait_for(entered_cleanup.wait(), timeout=10)
        # cleanup 仍阻塞：真实接线已置 halt（好组此刻无法交付 trainer）
        assert worker.halt_reason == "fatal_infrastructure:session_drain_owner_failed"
    finally:
        cleanup_blocker.set()
        MockSessionAdapter.drop_session = orig_drop
    with pytest.raises(WorkerHalted, match="session_drain_owner_failed"):
        await asyncio.wait_for(run_task, timeout=10)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
async def test_drain_admit_expire_share_registry_lock_linearization():
    """二轮 P1-1 验收：锁住真实 registry._lock 跨过 timeout 再释放——
    不变量 = 判决与副作用一致；调用方收到 expired ⇒ 永不 revoke。"""

    import threading

    from repoharness2.adapters.slime.capture_wire import (
        CaptureRegistry,
        make_threadsafe_session_drain_owner,
    )

    class _Hook:
        records: list = []

    # 情形 A（确定性 timeout 赢）：停转 loop——命令未被调度，expire 无
    # 竞争拿锁 → EXPIRED；恢复 loop 后准入被拒，永不 revoke。
    registry = CaptureRegistry()
    registry.register("s-lin", _Hook(), physical_attempt_id="e#p1-lin")
    stalled = asyncio.new_event_loop()
    owner = make_threadsafe_session_drain_owner(registry, stalled,
                                                timeout_seconds=0.2)
    with pytest.raises(RuntimeError, match="bridge_timeout:expired"):
        await owner("s-lin")
    def run_briefly(loop):
        asyncio.set_event_loop(loop)
        loop.call_later(0.1, loop.stop)
        loop.run_forever()
    t = threading.Thread(target=run_briefly, args=(stalled,), daemon=True)
    t.start(); t.join(timeout=5)
    assert not t.is_alive()
    assert not registry.is_revoked("s-lin")  # expired ⇒ 永不 revoke
    stalled.close()

    # 情形 B（竞态窗口，codex 复现形）：owner 命令在真实 _lock 上阻塞跨过
    # timeout；释放后同锁排他定局——判决与副作用必须一致，绝无
    # "收到 expired 判决之后才首次 revoke"。
    registry2 = CaptureRegistry()
    registry2.register("s-race", _Hook(), physical_attempt_id="e#p1-race")
    live = asyncio.new_event_loop()
    ready = threading.Event()

    def live_thread():
        asyncio.set_event_loop(live)
        live.call_soon(ready.set)
        live.run_forever()

    lt = threading.Thread(target=live_thread, daemon=True)
    lt.start()
    assert ready.wait(5)
    owner2 = make_threadsafe_session_drain_owner(registry2, live,
                                                 timeout_seconds=0.2)

    # 第三方**独立线程**持锁跨过 timeout（不能在 loop 线程持锁——expire
    # 在 loop 线程上同步等锁会自死锁，首版即因此挂死）
    import time as _time

    def holder():
        registry2._lock.acquire()
        _time.sleep(0.6)  # 跨过 0.2s timeout
        registry2._lock.release()

    ht = threading.Thread(target=holder, daemon=True)
    ht.start()
    await asyncio.sleep(0.05)  # 让 holder 先拿到锁
    task = asyncio.create_task(owner2("s-race"))
    with pytest.raises(RuntimeError, match="bridge_timeout") as exc_info:
        await asyncio.wait_for(task, timeout=10)
    ht.join(timeout=5)
    assert not ht.is_alive()
    await asyncio.sleep(0.2)  # 给迟到调度一个暴露窗口
    verdict_expired = "bridge_timeout:expired" in str(exc_info.value)
    # 线性化不变量：expired ⇔ 从未 revoke；admitted_but_timed_out ⇔ 已 revoke
    assert verdict_expired == (not registry2.is_revoked("s-race"))
    live.call_soon_threadsafe(live.stop)
    lt.join(timeout=5)
    assert not lt.is_alive()
    live.close()
