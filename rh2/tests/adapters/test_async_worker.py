"""FA-1 故障注入测试（含 follow-up，codex 轮次 6 全项）。

覆盖：worker 账目守恒 + sink 失败 durable fallback/halt + 取消/源故障/关闭
协议；proxy 场景 19/20 + 守卫负测试（含 target_version 反例）+ 全局 attempt
身份 + capture 两阶段事务 + attempt 超时 + audit 有界；资源限额真实接线；
重试白名单 + 永久错误短路。
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

import pytest

from repoharness2.adapters.slime.async_worker import (
    BoundedDeliveryQueue,
    ContinuousExecutionWorker,
    ExecutionTaskSpec,
    ModelCallProxy,
    NonRetryableError,
    ResourceLimits,
    RetrySpec,
    UnattributableModelCallError,
    WorkerHalted,
    retry_local_operation,
)
from repoharness2.contracts.fa_runtime import TrainingRuntimeWindow

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


# ---------------------------------------------------------------- 测试基元


class FakeCoordinator:
    """协调器协议替身：按脚本给出窗口序列（消费一次前进一步，末项驻留）。"""

    def __init__(self, windows: list[TrainingRuntimeWindow]) -> None:
        self._windows = windows
        self._cursor = 0

    def current_window(self) -> TrainingRuntimeWindow:
        window = self._windows[min(self._cursor, len(self._windows) - 1)]
        self._cursor += 1
        return window


def _window(
    *,
    epoch: int,
    phase: str,
    active: str,
    target: str | None = None,
    old: str | None = None,
    fence: str | None = None,
) -> TrainingRuntimeWindow:
    resolved_target = target or active
    return TrainingRuntimeWindow(
        update_epoch=epoch,
        phase=phase,  # type: ignore[arg-type]
        old_version=old if old is not None else str(int(resolved_target) - 1),
        target_version=resolved_target,
        active_version=active,
        window_started_at=NOW,
        window_completed_at=(NOW + timedelta(seconds=5)) if phase == "ACTIVE" else None,
        fencing_token=fence or f"fence_{epoch}",
    )


def _ok_response(tokens: list[int], version: str) -> dict:
    return {
        "text": "ok",
        "meta_info": {
            "id": "rid",
            "finish_reason": {"type": "stop"},
            "weight_version": version,
            "output_token_logprobs": [[-0.1, t, None] for t in tokens],
        },
    }


def _abort_response(partial_tokens: list[int]) -> dict:
    return {
        "text": "aborted",
        "meta_info": {
            "id": "rid",
            "finish_reason": {"type": "abort"},
            "output_token_logprobs": [[-0.1, t, None] for t in partial_tokens],
        },
    }


async def _no_sleep(_: float) -> None:
    await asyncio.sleep(0)


def _specs(n: int) -> list[ExecutionTaskSpec]:
    return [
        ExecutionTaskSpec(
            rollout_execution_id=f"exec_{i}",
            prompt_group_id=f"pg_{i % 3}",
            member_slot=i % 4,
        )
        for i in range(n)
    ]


# ------------------------------------------------------------ proxy：场景 19


async def test_proxy_regenerates_within_update_window_scenario_19():
    """场景 19：attempt_1 被更新窗口 abort → 等版本达 target → attempt_2 交付
    （两阶段：capture 持久化后 finalize）；半截输出只在审计面。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=2, phase="ACTIVE", active="2"),  # attempt_1 发前
            _window(epoch=2, phase="ACTIVE", active="2"),  # attempt_1 发起时
            _window(epoch=3, phase="UPDATING", active="2", target="3"),  # 失败时：窗口开启
            _window(epoch=3, phase="ACTIVE", active="3"),  # 等待：达 target
            _window(epoch=3, phase="ACTIVE", active="3"),  # attempt_2 发前
            _window(epoch=3, phase="ACTIVE", active="3"),  # attempt_2 发起时
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)
    calls: list[int] = []

    async def send(attempt: int) -> dict:
        calls.append(attempt)
        if attempt == 1:
            return _abort_response(partial_tokens=[7, 8, 9])
        return _ok_response(tokens=[11, 12], version="3")

    result = await proxy.call("exec_A", "turn_5", send)

    assert calls == [1, 2]
    assert result.delivered_attempt_number == 2
    delivered_tokens = [p[1] for p in result.response["meta_info"]["output_token_logprobs"]]
    assert delivered_tokens == [11, 12]  # 旧 token 7/8/9 不在交付面
    # 两阶段事务：finalize 前 delivered 不入账、pending 可见
    assert [a.delivery_status for a in result.attempts] == ["non_delivered_aborted"]
    assert result.draft.attempt_id in proxy.unfinalized_deliveries
    finalized = result.finalize_delivered("cap_t5_a2")
    assert finalized.weight_version == "3" and finalized.capture_record_ref == "cap_t5_a2"
    assert [a.delivery_status for a in result.attempts] == [
        "non_delivered_aborted", "delivered",
    ]
    assert result.draft.attempt_id not in proxy.unfinalized_deliveries
    aborted = result.attempts[0]
    assert aborted.abort_update_epoch == 3 and aborted.abort_fencing_token == "fence_3"
    assert aborted.capture_record_ref is None
    # 半截输出有界留痕（digest+预览），evidence 引用真实存在
    assert "exec_A/turn_5_a1" in proxy.audit_artifacts
    assert proxy.audit_artifacts["exec_A/turn_5_a1"]["sha256"]


async def test_proxy_attempt_identity_globally_unique_across_rollouts():
    """codex 轮次 6 严重 4：并发 rollout 的同名 turn 不得冲突——attempt id
    含 execution scope，账目与审计条目各自独立。"""

    class AdvancingCoordinator:
        """每次读 epoch/版本单调 +1（全 ACTIVE）：任意并发交错下，
        失败读相对发起读必然 epoch 前进 → 重叠判定成立；等待读版本
        必然 >= abort target → 立即放行。对交错顺序完全不敏感。"""

        def __init__(self) -> None:
            self.reads = 0

        def current_window(self) -> TrainingRuntimeWindow:
            self.reads += 1
            v = str(self.reads)
            return _window(epoch=self.reads, phase="ACTIVE", active=v, old=str(self.reads - 1) or "0")

    proxy = ModelCallProxy(AdvancingCoordinator(), sleeper=_no_sleep)

    async def send_for(scope: str):
        async def send(attempt: int) -> dict:
            if attempt == 1:
                return _abort_response([1])
            return _ok_response([2], version="99")

        return await proxy.call(scope, "turn_0", send)

    result_a, result_b = await asyncio.gather(send_for("exec_A"), send_for("exec_B"))
    ids = {result_a.draft.attempt_id, result_b.draft.attempt_id}
    assert ids == {"exec_A/turn_0_a2", "exec_B/turn_0_a2"}
    assert "exec_A/turn_0_a1" in proxy.audit_artifacts
    assert "exec_B/turn_0_a1" in proxy.audit_artifacts  # 不互相覆盖
    with pytest.raises(ValueError, match="execution_scope"):
        await proxy.call("", "turn_0", send_for)


async def test_proxy_finalize_is_transactional():
    """严重 5：未 finalize 的交付在对账面可见；重复 finalize 拒绝。"""

    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]), sleeper=_no_sleep
    )

    async def send(attempt: int) -> dict:
        return _ok_response([1], version="1")

    result = await proxy.call("exec_C", "turn_1", send)
    assert proxy.unfinalized_deliveries == {result.draft.attempt_id}
    result.finalize_delivered("cap_1")
    assert proxy.unfinalized_deliveries == frozenset()
    with pytest.raises(ValueError, match="finalize"):
        result.finalize_delivered("cap_dup")


async def test_proxy_unattributable_outside_window_scenario_20():
    coordinator = FakeCoordinator([_window(epoch=5, phase="ACTIVE", active="7")])
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)
    calls: list[int] = []

    async def send(attempt: int) -> dict:
        calls.append(attempt)
        raise ConnectionError("pipe broke")

    with pytest.raises(UnattributableModelCallError, match="no_overlapping_update_window"):
        await proxy.call("exec_D", "turn_1", send)
    assert calls == [1]
    failed = proxy.attempts_ledger[-1]
    assert failed.delivery_status == "non_delivered_failed"
    # 悬空 evidence 修复：failed attempt 的 evidence 引用真实存在
    for ref in failed.evidence_refs:
        assert ref.removeprefix("audit:") in proxy.audit_artifacts


async def test_proxy_recovery_must_reach_abort_target_version():
    """codex 轮次 6 严重 6 反例：调用前 active=3，abort 窗口 target=5，
    恢复 ACTIVE active=4（更晚 epoch）——版本没到 target，必须拒绝。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=6, phase="ACTIVE", active="3"),  # 发前
            _window(epoch=6, phase="ACTIVE", active="3"),  # 发起时
            _window(epoch=7, phase="UPDATING", active="3", target="5", old="3"),  # 失败时
            _window(epoch=8, phase="ACTIVE", active="4", old="3"),  # 恢复：4 < target 5
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="version_regressed_across_epochs"):
        await proxy.call("exec_E", "turn_2", send)


async def test_proxy_recovery_accepts_target_reached_via_later_epoch():
    """正例：更晚 epoch 把版本推到/推过 abort target → 放行重生成。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=6, phase="ACTIVE", active="3"),  # 发前
            _window(epoch=6, phase="ACTIVE", active="3"),  # 发起时
            _window(epoch=7, phase="UPDATING", active="3", target="5", old="3"),  # 失败时
            _window(epoch=8, phase="ACTIVE", active="6", old="5"),  # 恢复：6 >= 5
            _window(epoch=8, phase="ACTIVE", active="6", old="5"),  # attempt_2 发前
            _window(epoch=8, phase="ACTIVE", active="6", old="5"),  # attempt_2 发起时
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        if attempt == 1:
            return _abort_response([])
        return _ok_response([1], version="6")

    result = await proxy.call("exec_F", "turn_3", send)
    assert result.draft.weight_version == "6"


async def test_proxy_guard_version_stall_times_out():
    coordinator = FakeCoordinator(
        [_window(epoch=1, phase="ACTIVE", active="1")] * 2
        + [_window(epoch=2, phase="UPDATING", active="1", target="2")] * 4
    )
    clock_values = iter([0.0, 0.0, 0.0, 100.0])
    proxy = ModelCallProxy(
        coordinator,
        sleeper=_no_sleep,
        wait_timeout_seconds=50.0,
        clock=lambda: next(clock_values, 200.0),
    )

    async def send(attempt: int) -> dict:
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="version_did_not_advance"):
        await proxy.call("exec_G", "turn_2", send)


async def test_proxy_guard_fencing_mismatch_same_epoch():
    coordinator = FakeCoordinator(
        [
            _window(epoch=3, phase="ACTIVE", active="3"),  # 发前
            _window(epoch=3, phase="ACTIVE", active="3"),  # 发起时
            _window(epoch=4, phase="UPDATING", active="3", target="4", fence="fence_4"),
            _window(epoch=4, phase="ACTIVE", active="4", fence="fence_STALE"),
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="fencing_token_mismatch"):
        await proxy.call("exec_H", "turn_3", send)


async def test_proxy_non_numeric_recovery_version_rejected():
    coordinator = FakeCoordinator(
        [
            _window(epoch=1, phase="ACTIVE", active="1"),  # 发前
            _window(epoch=1, phase="ACTIVE", active="1"),  # 发起时
            _window(epoch=2, phase="UPDATING", active="1", target="2"),  # 失败时
            TrainingRuntimeWindow(
                update_epoch=2,
                phase="ACTIVE",
                old_version="1",
                target_version="ckpt_x",
                active_version="ckpt_x",
                window_started_at=NOW,
                window_completed_at=NOW + timedelta(seconds=1),
                fencing_token="fence_2",
            ),
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="non_numeric_version_in_window"):
        await proxy.call("exec_I", "turn_4", send)


async def test_proxy_max_regenerations_cap():
    class AdvancingCoordinator:
        def __init__(self) -> None:
            self.reads = 0

        def current_window(self) -> TrainingRuntimeWindow:
            self.reads += 1
            return _window(epoch=self.reads, phase="ACTIVE", active=str(self.reads))

    proxy = ModelCallProxy(AdvancingCoordinator(), sleeper=_no_sleep, max_regenerations=3)

    async def send(attempt: int) -> dict:
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="max_regenerations_exceeded"):
        await proxy.call("exec_J", "turn_4", send)
    aborted = [a for a in proxy.attempts_ledger if a.delivery_status == "non_delivered_aborted"]
    assert len(aborted) == 4


async def test_proxy_delivered_without_version_unattributable_with_evidence():
    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]), sleeper=_no_sleep
    )

    async def send(attempt: int) -> dict:
        response = _ok_response([1], version="1")
        del response["meta_info"]["weight_version"]
        return response

    with pytest.raises(UnattributableModelCallError, match="missing_weight_version"):
        await proxy.call("exec_K", "turn_6", send)
    # 悬空 evidence 修复：该分支现在也先留痕再落账
    assert "exec_K/turn_6_a1" in proxy.audit_artifacts


async def test_proxy_attempt_timeout_treated_as_interruption():
    """attempt 超时（模型请求永久挂起）→ 按中断归因；ACTIVE 稳态下不可归因。"""

    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]),
        sleeper=_no_sleep,
        attempt_timeout_seconds=0.01,
    )

    async def hang_forever(attempt: int) -> dict:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    with pytest.raises(UnattributableModelCallError, match="no_overlapping_update_window"):
        await proxy.call("exec_L", "turn_7", hang_forever)


async def test_proxy_audit_artifacts_bounded():
    """audit 内存有界：超过上限按 FIFO 淘汰并计数（长训练不涨爆）。"""

    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=5, phase="ACTIVE", active="7")]),
        sleeper=_no_sleep,
        max_audit_artifacts=2,
    )

    async def send(attempt: int) -> dict:
        raise ConnectionError("boom")

    for turn in range(3):
        with pytest.raises(UnattributableModelCallError):
            await proxy.call("exec_M", f"turn_{turn}", send)
    live = [k for k, v in proxy.audit_artifacts.items() if not v.get("tombstone")]
    assert len(live) <= 2  # 活跃条目有界
    assert proxy.audit_evictions >= 1
    # 悬空修复：所有 audit: 引用（含被淘汰的）仍可解析——tombstone 保 digest
    for attempt in proxy.attempts_ledger:
        for ref in attempt.evidence_refs:
            if ref.startswith("audit:"):
                assert ref.removeprefix("audit:") in proxy.audit_artifacts


async def test_proxy_model_call_resource_limit_enforced():
    """限额接线：model_call 限 1 → 两个并发调用峰值并发 = 1。"""

    limits = ResourceLimits({"model_call": 1})
    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]),
        sleeper=_no_sleep,
        limits=limits,
    )
    gauge = {"now": 0, "peak": 0}

    async def send(attempt: int) -> dict:
        gauge["now"] += 1
        gauge["peak"] = max(gauge["peak"], gauge["now"])
        await asyncio.sleep(0.005)
        gauge["now"] -= 1
        return _ok_response([1], version="1")

    await asyncio.gather(
        proxy.call("exec_N1", "turn_0", send), proxy.call("exec_N2", "turn_0", send)
    )
    assert gauge["peak"] == 1
    assert limits.backpressure_counts["model_call"] >= 1


# ------------------------------------------------------- worker：N1/N2 修复


async def test_worker_ledger_conservation_with_injected_crashes():
    specs = _specs(20)
    queue: list[ExecutionTaskSpec] = list(specs)
    failures: list[tuple[str, str]] = []

    async def execute(spec: ExecutionTaskSpec):
        await asyncio.sleep(0)
        if int(spec.rollout_execution_id.split("_")[1]) % 3 == 0:
            raise RuntimeError(f"injected crash {spec.rollout_execution_id}")
        return {"exec": spec.rollout_execution_id}

    delivery = BoundedDeliveryQueue(maxsize=64)
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=delivery,
        failure_sink=lambda spec, exc: failures.append(
            (spec.rollout_execution_id, type(exc).__name__)
        ),
        concurrency=4,
        sleeper=_no_sleep,
    )
    stop = asyncio.Event()

    async def stopper():
        while worker.counters.delivered + worker.counters.failed < len(specs):
            await asyncio.sleep(0)
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), stopper()), timeout=10)
    assert worker.counters.dispatched == len(specs)
    assert worker.ledger_balanced()
    assert len(failures) == 7
    assert worker.counters.delivered == 13 == delivery.qsize()


async def test_worker_sink_failure_goes_to_durable_fallback_and_halts():
    """codex 轮次 6 严重 2：sink 失败 → durable fallback 留痕 + run-halt，
    绝不出现"账平但无记录"。"""

    specs = _specs(6)
    queue: list[ExecutionTaskSpec] = list(specs)

    async def execute(spec: ExecutionTaskSpec):
        raise RuntimeError("boom")

    def bad_sink(spec, exc):
        raise ValueError("sink itself broken")

    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=8),
        failure_sink=bad_sink,
        concurrency=2,
        sleeper=_no_sleep,
    )
    stop = asyncio.Event()
    with pytest.raises(WorkerHalted, match="failure_sink_failed"):
        await asyncio.wait_for(worker.run(stop), timeout=10)
    assert worker.counters.sink_failures > 0
    assert len(worker.unrecorded_failures) == worker.counters.sink_failures
    assert worker.ledger_balanced()
    # halt 后停止取新任务：不会把 6 个全烧完（首轮 2 个在途 + 可能一轮补位）
    assert worker.counters.dispatched < len(specs)


async def test_worker_task_source_failure_halts_after_drain():
    """严重 3：task_source 抛异常 → 在途照常收尾，然后 WorkerHalted。"""

    calls = {"n": 0}

    def broken_source():
        calls["n"] += 1
        if calls["n"] <= 2:
            return _specs(2)[calls["n"] - 1]
        raise OSError("source db down")

    done: list[str] = []

    async def execute(spec: ExecutionTaskSpec):
        await asyncio.sleep(0)
        done.append(spec.rollout_execution_id)
        return spec.rollout_execution_id

    worker = ContinuousExecutionWorker(
        task_source=broken_source,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=8),
        failure_sink=lambda s, e: None,
        concurrency=4,
        sleeper=_no_sleep,
    )
    with pytest.raises(WorkerHalted, match="task_source_failed"):
        await asyncio.wait_for(worker.run(asyncio.Event()), timeout=10)
    assert sorted(done) == ["exec_0", "exec_1"]  # 在途两个全部收尾
    assert worker.counters.delivered == 2
    assert worker.ledger_balanced()


async def test_worker_execution_cancellation_accounted_as_failure():
    """严重 3：execution task 被取消 → 按失败落账，worker 本体不退出。"""

    specs = _specs(3)
    queue: list[ExecutionTaskSpec] = list(specs)
    failures: list[str] = []

    async def execute(spec: ExecutionTaskSpec):
        if spec.rollout_execution_id == "exec_1":
            raise asyncio.CancelledError()  # 等价于任务被外部取消的终态
        return spec.rollout_execution_id

    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=8),
        failure_sink=lambda s, e: failures.append(type(e).__name__),
        concurrency=2,
        sleeper=_no_sleep,
    )
    stop = asyncio.Event()

    async def stopper():
        while worker.counters.delivered + worker.counters.failed < 3:
            await asyncio.sleep(0)
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), stopper()), timeout=10)
    assert worker.counters.failed == 1 and "CancelledError" in failures
    assert worker.ledger_balanced()


async def test_worker_own_cancellation_drains_and_accounts():
    """严重 3：worker 自身被取消 → 在途任务取消并逐个落账，账目守恒。"""

    started = asyncio.Event()

    async def execute(spec: ExecutionTaskSpec):
        started.set()
        await asyncio.Event().wait()  # 永久挂起，等被取消

    queue: list[ExecutionTaskSpec] = _specs(2)
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=8),
        failure_sink=lambda s, e: None,
        concurrency=2,
        sleeper=_no_sleep,
    )
    run_task = asyncio.create_task(worker.run(asyncio.Event()))
    await asyncio.wait_for(started.wait(), timeout=5)
    await asyncio.sleep(0.01)  # 让两个任务都进 in_flight
    run_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(run_task, timeout=5)
    assert worker.counters.dispatched == 2
    assert worker.ledger_balanced()  # 取消路径也不漏账


async def test_worker_shutdown_deadline_with_dead_consumer():
    """严重 3：stop 后消费者死亡 + 队列满 → drain 超时把未投样本显式弃置
    记账退出，绝不永久等待。"""

    specs = _specs(4)
    queue: list[ExecutionTaskSpec] = list(specs)

    async def execute(spec: ExecutionTaskSpec):
        await asyncio.sleep(0)
        return spec.rollout_execution_id

    clock = {"t": 0.0}

    def fake_clock() -> float:
        clock["t"] += 0.01
        return clock["t"]

    delivery = BoundedDeliveryQueue(maxsize=1)  # 消费者永不取 -> 只装得下 1 个
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=delivery,
        failure_sink=lambda s, e: None,
        concurrency=4,
        max_pending_out=8,
        drain_timeout_seconds=0.05,
        sleeper=_no_sleep,
        clock=fake_clock,
    )
    stop = asyncio.Event()

    async def stop_after_dispatch():
        # codex 轮次 7：必须先真实分派与投递（旧版 stop 先置位 -> dispatched=0
        # 空验证）。等 4 个全部执行完、1 个进队后再宣告消费者死亡。
        while worker.counters.dispatched < 4 or worker.counters.delivered < 1:
            await asyncio.sleep(0)
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), stop_after_dispatch()), timeout=10)
    assert worker.counters.dispatched == 4
    assert worker.counters.delivered == 1  # 队列容量 1
    assert worker.counters.abandoned == 3  # 其余显式弃置，绝不静默等死
    assert worker.ledger_balanced()
    assert len(worker.abandoned_deliveries) == worker.counters.abandoned


async def test_worker_backpressure_keeps_loop_alive_n2():
    specs = _specs(6)
    queue: list[ExecutionTaskSpec] = list(specs)

    async def execute(spec: ExecutionTaskSpec):
        await asyncio.sleep(0)
        return spec.rollout_execution_id

    delivery = BoundedDeliveryQueue(maxsize=1)
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=delivery,
        failure_sink=lambda spec, exc: None,
        concurrency=2,
        max_pending_out=1,
        sleeper=_no_sleep,
    )
    stop = asyncio.Event()
    consumed: list[str] = []

    async def slow_consumer():
        for _ in range(200):
            await asyncio.sleep(0)
        while len(consumed) < len(specs):
            item = await delivery.get()
            consumed.append(item[1])
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), slow_consumer()), timeout=10)
    assert worker.ledger_balanced()
    assert len(consumed) == len(specs)
    assert delivery.backpressure_events > 0
    assert worker.counters.delivery_backpressure > 0
    assert worker.counters.topup_paused_by_backpressure > 0


async def test_worker_respects_concurrency_and_execution_limits():
    """并发上限 + 资源限额真实接线：sandbox 限 1 < concurrency 4 → 有效并发 1。"""

    specs = _specs(6)
    queue: list[ExecutionTaskSpec] = list(specs)
    gauge = {"now": 0, "peak": 0}

    async def execute(spec: ExecutionTaskSpec):
        gauge["now"] += 1
        gauge["peak"] = max(gauge["peak"], gauge["now"])
        await asyncio.sleep(0.001)
        gauge["now"] -= 1
        return spec.rollout_execution_id

    limits = ResourceLimits({"sandbox": 1})
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=32),
        failure_sink=lambda s, e: None,
        concurrency=4,
        execution_limits=limits,
    )
    stop = asyncio.Event()

    async def stopper():
        while worker.counters.delivered < len(specs):
            await asyncio.sleep(0)
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), stopper()), timeout=10)
    assert gauge["peak"] == 1  # 限额生效（不是摆设）
    assert limits.backpressure_counts["sandbox"] > 0


def test_worker_parameter_validation():
    common = dict(
        task_source=lambda: None,
        execute_fn=None,
        delivery_queue=BoundedDeliveryQueue(maxsize=1),
        failure_sink=lambda s, e: None,
    )
    with pytest.raises(ValueError, match="concurrency"):
        ContinuousExecutionWorker(concurrency=0, **common)
    with pytest.raises(ValueError, match="max_pending_out"):
        ContinuousExecutionWorker(concurrency=1, max_pending_out=0, **common)
    with pytest.raises(ValueError, match="maxsize"):
        BoundedDeliveryQueue(maxsize=0)


# --------------------------------------------------------------- 资源限额


async def test_resource_limits_isolated_per_class():
    limits = ResourceLimits({"sandbox": 1, "model_call": 2})
    acquired: list[str] = []

    async def hold_sandbox():
        async with limits.acquire("sandbox"):
            acquired.append("sandbox_1")
            await asyncio.sleep(0.02)

    async def try_model_call():
        await asyncio.sleep(0.005)
        async with limits.acquire("model_call"):
            acquired.append("model_call_while_sandbox_full")

    await asyncio.wait_for(asyncio.gather(hold_sandbox(), try_model_call()), timeout=5)
    assert "model_call_while_sandbox_full" in acquired
    assert limits.backpressure_counts["model_call"] == 0
    with pytest.raises(ValueError, match="未知资源类"):
        ResourceLimits({"gpu": 1})


# --------------------------------------------------------------- 重试白名单


async def test_retry_whitelisted_operation_with_full_jitter():
    attempts = {"n": 0}

    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("transient")
        return "done"

    delays: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    ledger: list = []
    result = await retry_local_operation(
        "docker_image_pull", flaky, ledger=ledger, rng=random.Random(7), sleeper=fake_sleep
    )
    assert result == "done" and attempts["n"] == 3
    assert len(delays) == 2
    assert 0.0 <= delays[0] <= 0.5 and 0.0 <= delays[1] <= 1.0
    assert [r.succeeded for r in ledger] == [False, False, True]


async def test_retry_non_whitelisted_runs_once():
    attempts = {"n": 0}

    async def harness_run():
        attempts["n"] += 1
        raise RuntimeError("harness died")

    with pytest.raises(RuntimeError, match="harness died"):
        await retry_local_operation("whole_harness_rerun", harness_run)
    assert attempts["n"] == 1


async def test_retry_permanent_errors_short_circuit():
    """codex 轮次 6：永久错误（NonRetryableError / retryable 判负）不烧预算。"""

    attempts = {"n": 0}

    async def auth_fail():
        attempts["n"] += 1
        raise NonRetryableError("credential rejected")

    with pytest.raises(NonRetryableError):
        await retry_local_operation("docker_image_pull", auth_fail, sleeper=_no_sleep)
    assert attempts["n"] == 1

    attempts["n"] = 0

    async def digest_mismatch():
        attempts["n"] += 1
        raise ValueError("digest mismatch")

    with pytest.raises(ValueError):
        await retry_local_operation(
            "docker_image_pull",
            digest_mismatch,
            sleeper=_no_sleep,
            retryable=lambda exc: not isinstance(exc, ValueError),
        )
    assert attempts["n"] == 1


async def test_retry_grading_stage_single_full_retry():
    attempts = {"n": 0}

    async def grading():
        attempts["n"] += 1
        raise TimeoutError("grading container died")

    with pytest.raises(TimeoutError):
        await retry_local_operation("grading_stage", grading, sleeper=_no_sleep)
    assert attempts["n"] == 2


def test_retry_spec_validation():
    with pytest.raises(ValueError, match="max_attempts"):
        RetrySpec(0)
    with pytest.raises(ValueError, match="delay"):
        RetrySpec(3, base_delay_seconds=0.0)
    with pytest.raises(ValueError, match="delay"):
        RetrySpec(3, base_delay_seconds=9.0, max_delay_seconds=8.0)


# ----------------------------------------- 轮次 7：poison / deadline / 发前等待


from repoharness2.adapters.slime.async_worker import (  # noqa: E402
    SessionPoisonRegistry,
    SessionPoisonedError,
    StaticActiveCoordinator,
)


async def test_poisoned_session_rejected_fast():
    """session 中毒后同 session 一切调用快速拒绝（CC 5xx 退避重试的截断点）。"""

    registry = SessionPoisonRegistry()
    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]), sleeper=_no_sleep
    )
    calls: list[int] = []

    async def send(attempt: int) -> dict:
        calls.append(attempt)
        raise ConnectionError("boom")

    with pytest.raises(UnattributableModelCallError):
        await proxy.call(
            "exec_P", "turn_0", send, session_id="sid_P", poison_registry=registry
        )
    assert registry.is_poisoned("sid_P")  # 不可归因 -> 自动中毒
    with pytest.raises(SessionPoisonedError):
        await proxy.call(
            "exec_P", "turn_1", send, session_id="sid_P", poison_registry=registry
        )
    assert calls == [1]  # 第二轮一次都没发出去


async def test_episode_deadline_exhausted_poisons_and_refuses():
    """episode 预算不足一次重生成 -> 不再尝试 + poison + 缺员（codex 实测
    CC 会退避重试，deadline 必须从 episode 传到 proxy）。"""

    registry = SessionPoisonRegistry()
    clock = {"t": 100.0}
    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]),
        sleeper=_no_sleep,
        clock=lambda: clock["t"],
    )
    calls: list[int] = []

    async def send(attempt: int) -> dict:
        calls.append(attempt)
        return _ok_response([1], version="1")

    with pytest.raises(UnattributableModelCallError, match="episode_deadline_exhausted"):
        await proxy.call(
            "exec_Q",
            "turn_0",
            send,
            session_id="sid_Q",
            poison_registry=registry,
            deadline_monotonic=102.0,  # 剩 2s < min_attempt_budget 5s
        )
    assert calls == []  # 一次都不发
    assert registry.is_poisoned("sid_Q")


async def test_presend_waits_for_active_window():
    """发前 ACTIVE 等待：窗口更新中不发注定被 abort 的请求，恢复后才发。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=2, phase="UPDATING", active="1", target="2"),  # 发前：更新中
            _window(epoch=2, phase="UPDATING", active="1", target="2"),  # 等待…
            _window(epoch=2, phase="ACTIVE", active="2"),  # 恢复
            _window(epoch=2, phase="ACTIVE", active="2"),  # 发起时
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)
    observed: list[int] = []

    async def send(attempt: int) -> dict:
        observed.append(coordinator._cursor)  # 发出时协调器已消费到 ACTIVE 之后
        return _ok_response([1], version="2")

    result = await proxy.call("exec_R", "turn_0", send)
    assert result.draft.weight_version == "2"
    assert observed and observed[0] >= 3  # 确实等过了 UPDATING 窗口


async def test_client_cancellation_propagates_and_poisons():
    """CC 取消 HTTP 请求：CancelledError 原样传播（aiohttp 链），但先落账
    + poison——取消后的 CC 重试不得复活 session。"""

    registry = SessionPoisonRegistry()
    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]), sleeper=_no_sleep
    )

    async def send(attempt: int) -> dict:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await proxy.call(
            "exec_S", "turn_0", send, session_id="sid_S", poison_registry=registry
        )
    assert registry.is_poisoned("sid_S")
    assert proxy.attempts_ledger[-1].delivery_status == "non_delivered_failed"


async def test_abandon_delivered_closes_draft():
    """unfinalized draft 的显式出口：capture 未持久化 -> abandon 落账。"""

    proxy = ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")]), sleeper=_no_sleep
    )

    async def send(attempt: int) -> dict:
        return _ok_response([1], version="1")

    result = await proxy.call("exec_T", "turn_0", send)
    assert proxy.unfinalized_deliveries
    attempt = result.abandon_delivered("capture flush failed")
    assert attempt.delivery_status == "non_delivered_failed"
    assert proxy.unfinalized_deliveries == frozenset()
    with pytest.raises(ValueError, match="finalize"):
        result.finalize_delivered("cap_late")  # abandon 后不可再 finalize


def test_static_active_coordinator_conservative_window():
    """协调器缺席期的保守替身：永远 ACTIVE（任何中断不可归因）+ 版本来自
    注入 provider。"""

    coordinator = StaticActiveCoordinator(lambda: "7")
    window = coordinator.current_window()
    assert window.phase == "ACTIVE"
    assert window.active_version == window.target_version == "7"
    non_numeric = StaticActiveCoordinator(lambda: "ckpt_a").current_window()
    assert non_numeric.old_version == "ckpt_a_prev"


async def test_all_unattributable_terminations_poison():
    """codex 轮次 8 P0-3：发前等待超时/版本恢复超时/fencing 不符/版本回退
    等分支都必须统一 poison（此前只有部分分支 poison）。"""

    registry = SessionPoisonRegistry()

    # 版本恢复超时（守卫 3 超时）
    coord = FakeCoordinator(
        [_window(epoch=1, phase="ACTIVE", active="1")] * 2
        + [_window(epoch=2, phase="UPDATING", active="1", target="2")] * 4
    )
    clock_values = iter([0.0, 0.0, 0.0, 100.0])
    proxy = ModelCallProxy(
        coord, sleeper=_no_sleep, wait_timeout_seconds=50.0,
        clock=lambda: next(clock_values, 200.0),
    )

    async def send(attempt: int) -> dict:
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="version_did_not_advance"):
        await proxy.call("exec_U", "turn_0", send, session_id="sid_U", poison_registry=registry)
    assert registry.is_poisoned("sid_U")  # 此前该分支漏 poison


async def test_recovery_wait_respects_episode_deadline():
    """codex 轮次 9 P0-1（修正轮次 8 假阳性测试）：版本恢复等待必须受 episode
    绝对 deadline 约束。旧测试 deadline=3 < min_attempt_budget=5，在**发送前**
    就以预算不足退出，从未进入恢复等待分支——本版断言：send 真被调用一次、
    失败原因是 version_did_not_advance、失败时钟不超过 episode deadline。"""

    registry = SessionPoisonRegistry()
    coord = FakeCoordinator(
        [_window(epoch=1, phase="ACTIVE", active="1")] * 2
        + [_window(epoch=2, phase="UPDATING", active="1", target="2")] * 50
    )
    # 时钟推进 0.5s/次；episode deadline=20s，wait_timeout=500s（独立等待会
    # 跑到 500s）——修复后必须在 20s 内以恢复等待超时失败
    clock = {"t": 0.0}

    def tick() -> float:
        clock["t"] += 0.5
        return clock["t"]

    proxy = ModelCallProxy(
        coord, sleeper=_no_sleep, wait_timeout_seconds=500.0, clock=tick
    )
    sends: list[int] = []

    async def send(attempt: int) -> dict:
        sends.append(attempt)
        return _abort_response([])

    with pytest.raises(UnattributableModelCallError, match="version_did_not_advance"):
        await proxy.call(
            "exec_V", "turn_0", send,
            session_id="sid_V", poison_registry=registry,
            deadline_monotonic=20.0,
        )
    assert sends == [1]  # 真发出过一次（进入了 abort→恢复等待分支）
    assert clock["t"] <= 20.0 + 1.0  # 失败发生在 episode deadline 附近，不是 500s
    assert registry.is_poisoned("sid_V")


# ----------------------------------------- 轮次 10：跨线程拓扑 / poison 生命周期


async def test_poison_from_real_thread_cancels_harness_in_owner_loop():
    """codex 轮次 10 P0-1：生产拓扑 = Ray actor loop 持 task + adapter **线程**
    发 poison。Task.cancel 非跨线程安全——owner 必须经 call_soon_threadsafe。
    本测试从真 threading.Thread 调 poison()，断言 owner loop 中的 task 收到
    CancelledError。"""

    import threading

    registry = SessionPoisonRegistry()
    owner_loop = asyncio.get_running_loop()
    cancelled = asyncio.Event()

    async def hanging_harness():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    task = asyncio.ensure_future(hanging_harness())
    await asyncio.sleep(0)  # 让协程真正启动

    def cancel_from_any_thread(_sid: str, _reason: str) -> None:
        owner_loop.call_soon_threadsafe(task.cancel)  # 生产 orchestrator 同款

    registry.subscribe("sid_T10", cancel_from_any_thread)
    thread = threading.Thread(
        target=registry.poison, args=("sid_T10", "unattributable"), name="fake-adapter"
    )
    thread.start()
    thread.join(timeout=5)
    await asyncio.wait_for(cancelled.wait(), timeout=5)  # 修复前此处永久挂起
    with pytest.raises(asyncio.CancelledError):
        await task
    assert registry.notify_failures == 0


def test_active_poison_never_evicted_archived_bounded():
    """codex 轮次 10 P0-4：active poison 绝不被容量淘汰（无 termination ACK
    前淘汰 = 中毒 session 复活）；release（清理 ACK）后归档，归档有界。"""

    registry = SessionPoisonRegistry(max_archived=2)
    registry.poison("sid_A", "bad_a")  # active，永不淘汰
    for i in range(10):
        registry.poison(f"sid_b{i}", "bad")
    assert registry.is_poisoned("sid_A")  # 修复前 max_entries=1 时这里 False
    # release 生命周期：active -> archived（仍可查），归档满 2 个后最旧被淘汰
    for i in range(10):
        registry.release(f"sid_b{i}")
    assert registry.is_poisoned("sid_b9") and registry.is_poisoned("sid_b8")
    assert not registry.is_poisoned("sid_b0")  # 已淘汰（归档摘要有界）
    assert registry.archived_evictions == 8
    assert registry.is_poisoned("sid_A")  # active 全程健在
    registry.release("sid_A")
    assert registry.is_poisoned("sid_A")  # 归档后仍拒绝（audit 面）


def test_registry_check_subscribe_race_window_closed():
    """codex 轮次 10 P0-3：check-then-subscribe 与 poison-then-extract 原子化
    ——两线程交错高频跑不丢通知（丢通知 = harness 永不被取消）。"""

    import threading

    for _ in range(200):
        registry = SessionPoisonRegistry()
        fired = threading.Event()
        barrier = threading.Barrier(2)

        def do_subscribe():
            barrier.wait()
            registry.subscribe("sid_R", lambda _s, _r: fired.set())

        def do_poison():
            barrier.wait()
            registry.poison("sid_R", "bad")

        t1 = threading.Thread(target=do_subscribe)
        t2 = threading.Thread(target=do_poison)
        t1.start(); t2.start(); t1.join(5); t2.join(5)
        assert fired.wait(timeout=5)  # 无论交错顺序，回调必达
