"""FA-1 故障注入测试：worker 账目守恒 / 队列反压 / 资源限额 / proxy 边界 / 重试。

验收对应（05 计划 FA-1）：task 异常不泄漏（N1）、queue 满反压不停摆（N2）、
更新窗口 abort → proxy 内部重生成且 non-delivered 留痕（场景 19）、不可
归因中断 → 正确缺员（场景 20，守卫三条件逐条负测试）、旧 token 悬挂负
测试、重试白名单语义。fan-out 交付形状对 slime 真函数的单测在
test_dp_schedule_differential.py（dynamic_filter）与 FA-1 的 GPU 侧
（`_key`，import 链需 sglang）。
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
    ResourceLimits,
    RetrySpec,
    UnattributableModelCallError,
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
        self.reads = 0

    def current_window(self) -> TrainingRuntimeWindow:
        self.reads += 1
        window = self._windows[min(self._cursor, len(self._windows) - 1)]
        self._cursor += 1
        return window


def _window(
    *, epoch: int, phase: str, active: str, target: str | None = None, fence: str | None = None
) -> TrainingRuntimeWindow:
    return TrainingRuntimeWindow(
        update_epoch=epoch,
        phase=phase,  # type: ignore[arg-type]
        old_version=str(int(target or active) - 1),
        target_version=target or active,
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


# ------------------------------------------------------------ proxy：场景 19


async def test_proxy_regenerates_within_update_window_scenario_19():
    """场景 19：attempt_1 被更新窗口 abort（正常 JSON finish_reason=abort）→
    等版本前进 → attempt_2 交付；CC 只见最终响应；半截输出只在审计面。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=3, phase="UPDATING", active="2", target="3"),  # 发起前
            _window(epoch=3, phase="UPDATING", active="2", target="3"),  # 失败时（重叠 ✓）
            _window(epoch=3, phase="ACTIVE", active="3"),  # 等待后：版本前进 ✓
            _window(epoch=3, phase="ACTIVE", active="3"),  # attempt_2 发起前
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)
    calls: list[int] = []

    async def send(attempt: int) -> dict:
        calls.append(attempt)
        if attempt == 1:
            return _abort_response(partial_tokens=[7, 8, 9])  # 旧版本半截输出
        return _ok_response(tokens=[11, 12], version="3")

    result = await proxy.call("turn_5", send, capture_record_ref=lambda a: f"cap_t5_a{a}")

    assert calls == [1, 2]
    assert result.delivered_attempt_number == 2
    # CC 交付面 = attempt_2 的完整响应（旧 token 悬挂负测试：7/8/9 不在交付面）
    delivered_tokens = [p[1] for p in result.response["meta_info"]["output_token_logprobs"]]
    assert delivered_tokens == [11, 12]
    # 账目：aborted attempt 带窗口双凭据；delivered attempt 带新版本 provenance
    kinds = [a.delivery_status for a in result.attempts]
    assert kinds == ["non_delivered_aborted", "delivered"]
    aborted, delivered = result.attempts
    assert aborted.abort_update_epoch == 3 and aborted.abort_fencing_token == "fence_3"
    assert aborted.capture_record_ref is None  # 半截输出绝不回链训练面
    assert delivered.weight_version == "3" and delivered.capture_record_ref == "cap_t5_a2"
    # 半截输出留在审计面
    assert "turn_5_a1" in proxy.audit_artifacts


async def test_proxy_dangling_tokens_never_reach_delivery():
    """旧 token 悬挂负测试（升级设计缺口①最坏组合）：连续两次 abort 后第三次
    交付——交付面只含最后一次的 token，前两次的半截输出全部只在审计面。"""

    windows = [_window(epoch=e, phase=p, active=a, target=t)
               for e, p, a, t in [
                   (1, "UPDATING", "0", "1"), (1, "UPDATING", "0", "1"),
                   (1, "ACTIVE", "1", None), (2, "UPDATING", "1", "2"),
                   (2, "UPDATING", "1", "2"), (2, "ACTIVE", "2", None),
                   (2, "ACTIVE", "2", None)]]
    proxy = ModelCallProxy(FakeCoordinator(windows), sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        if attempt <= 2:
            return _abort_response(partial_tokens=[100 + attempt])
        return _ok_response(tokens=[42], version="2")

    result = await proxy.call("turn_9", send, capture_record_ref=lambda a: f"cap_{a}")
    assert [p[1] for p in result.response["meta_info"]["output_token_logprobs"]] == [42]
    assert len(proxy.audit_artifacts) == 2  # 两次半截输出都只留审计
    assert [a.delivery_status for a in result.attempts] == [
        "non_delivered_aborted", "non_delivered_aborted", "delivered",
    ]


async def test_proxy_unattributable_outside_window_scenario_20():
    """场景 20：中断与任何更新窗口不重叠（协议全程 ACTIVE、epoch 不动）→
    不可归因，禁止内部重生成，一次都不重试。"""

    coordinator = FakeCoordinator([_window(epoch=5, phase="ACTIVE", active="7")])
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)
    calls: list[int] = []

    async def send(attempt: int) -> dict:
        calls.append(attempt)
        raise ConnectionError("pipe broke")

    with pytest.raises(UnattributableModelCallError, match="no_overlapping_update_window"):
        await proxy.call("turn_1", send, capture_record_ref=lambda a: "cap")
    assert calls == [1]  # 负测试：不得透明重试
    assert proxy.attempts_ledger[-1].delivery_status == "non_delivered_failed"


async def test_proxy_guard_version_must_advance():
    """守卫 3 负测试：abort 归因成立但等待期版本永不前进 → 超时缺员。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=2, phase="UPDATING", active="1", target="2"),
            _window(epoch=2, phase="UPDATING", active="1", target="2"),
            _window(epoch=2, phase="UPDATING", active="1", target="2"),
        ]
    )
    clock_values = iter([0.0, 0.0, 100.0])  # 第二次轮询即超时
    proxy = ModelCallProxy(
        coordinator,
        sleeper=_no_sleep,
        wait_timeout_seconds=50.0,
        clock=lambda: next(clock_values, 200.0),
    )

    async def send(attempt: int) -> dict:
        return _abort_response(partial_tokens=[])

    with pytest.raises(UnattributableModelCallError, match="version_did_not_advance"):
        await proxy.call("turn_2", send, capture_record_ref=lambda a: "cap")


async def test_proxy_guard_fencing_token_mismatch():
    """守卫负测试：版本前进了但 fencing 与观测 abort 窗口不一致（同 epoch）→
    陈旧窗口误归因防线触发。"""

    coordinator = FakeCoordinator(
        [
            _window(epoch=4, phase="UPDATING", active="3", target="4", fence="fence_4"),
            _window(epoch=4, phase="UPDATING", active="3", target="4", fence="fence_4"),
            _window(epoch=4, phase="ACTIVE", active="4", fence="fence_STALE"),
        ]
    )
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        return _abort_response(partial_tokens=[])

    with pytest.raises(UnattributableModelCallError, match="fencing_token_mismatch"):
        await proxy.call("turn_3", send, capture_record_ref=lambda a: "cap")


async def test_proxy_max_regenerations_cap():
    """重生成上限：每次都撞新窗口 abort → 超上限按不可归因缺员（更新风暴防线）。"""

    windows: list[TrainingRuntimeWindow] = []
    for epoch in range(1, 12):
        windows += [
            _window(epoch=epoch, phase="UPDATING", active=str(epoch - 1), target=str(epoch)),
            _window(epoch=epoch, phase="UPDATING", active=str(epoch - 1), target=str(epoch)),
            _window(epoch=epoch, phase="ACTIVE", active=str(epoch)),
        ]
    proxy = ModelCallProxy(
        FakeCoordinator(windows), sleeper=_no_sleep, max_regenerations=3
    )

    async def send(attempt: int) -> dict:
        return _abort_response(partial_tokens=[])

    with pytest.raises(UnattributableModelCallError, match="max_regenerations_exceeded"):
        await proxy.call("turn_4", send, capture_record_ref=lambda a: "cap")
    aborted = [a for a in proxy.attempts_ledger if a.delivery_status == "non_delivered_aborted"]
    assert len(aborted) == 4  # 首次 + 3 次重生成全部留痕


async def test_proxy_delivered_without_version_is_unattributable():
    """delivered 必须带 weight_version（契约强制）——缺失按不可归因处置。"""

    coordinator = FakeCoordinator([_window(epoch=1, phase="ACTIVE", active="1")])
    proxy = ModelCallProxy(coordinator, sleeper=_no_sleep)

    async def send(attempt: int) -> dict:
        response = _ok_response(tokens=[1], version="1")
        del response["meta_info"]["weight_version"]
        return response

    with pytest.raises(UnattributableModelCallError, match="missing_weight_version"):
        await proxy.call("turn_6", send, capture_record_ref=lambda a: "cap")


# ------------------------------------------------------- worker：N1/N2 修复


def _specs(n: int) -> list[ExecutionTaskSpec]:
    return [
        ExecutionTaskSpec(
            rollout_execution_id=f"exec_{i}",
            prompt_group_id=f"pg_{i % 3}",
            member_slot=i % 4,
        )
        for i in range(n)
    ]


async def test_worker_ledger_conservation_with_injected_crashes():
    """N1 验收：注入 30% 崩溃任务——dispatched == delivered + failed，
    每个失败都经 failure_sink 落账，无一静默消失。"""

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
    assert len(failures) == 7  # exec_0,3,6,9,12,15,18
    assert worker.counters.delivered == 13 == delivery.qsize()


async def test_worker_backpressure_keeps_loop_alive_n2():
    """N2 验收：交付队列容量 1、消费者迟迟不取——worker 不悬挂在 put，
    反压计数增长、top-up 暂停传导；消费恢复后全部交付，账目守恒。"""

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
        # 先饿一会制造反压，再逐个消费
        for _ in range(200):
            await asyncio.sleep(0)
        while len(consumed) < len(specs):
            item = await delivery.get()
            consumed.append(item[1])
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), slow_consumer()), timeout=10)
    assert worker.ledger_balanced()
    assert len(consumed) == len(specs)
    assert delivery.backpressure_events > 0  # 反压真实发生过
    assert worker.counters.delivery_backpressure > 0
    assert worker.counters.topup_paused_by_backpressure > 0  # 传导到生产侧


async def test_worker_respects_concurrency_limit():
    specs = _specs(12)
    queue: list[ExecutionTaskSpec] = list(specs)
    gauge = {"now": 0, "peak": 0}

    async def execute(spec: ExecutionTaskSpec):
        gauge["now"] += 1
        gauge["peak"] = max(gauge["peak"], gauge["now"])
        await asyncio.sleep(0.001)
        gauge["now"] -= 1
        return spec.rollout_execution_id

    delivery = BoundedDeliveryQueue(maxsize=32)
    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=delivery,
        failure_sink=lambda s, e: None,
        concurrency=3,
    )
    stop = asyncio.Event()

    async def stopper():
        while worker.counters.delivered < len(specs):
            await asyncio.sleep(0)
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), stopper()), timeout=10)
    assert gauge["peak"] <= 3


async def test_worker_failure_sink_exception_does_not_kill_worker():
    """sink 自身异常不允许炸 worker（兜底的兜底）。"""

    specs = _specs(4)
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

    async def stopper():
        while worker.counters.failed < len(specs):
            await asyncio.sleep(0)
        stop.set()

    await asyncio.wait_for(asyncio.gather(worker.run(stop), stopper()), timeout=10)
    assert worker.counters.failed == 4


# --------------------------------------------------------------- 资源限额


async def test_resource_limits_isolated_per_class():
    """codex #9：sandbox 打满不阻塞 model_call 的获取（分类隔离）。"""

    limits = ResourceLimits({"sandbox": 1, "model_call": 2})
    acquired: list[str] = []

    async def hold_sandbox():
        async with limits.acquire("sandbox"):
            acquired.append("sandbox_1")
            await asyncio.sleep(0.02)

    async def try_model_call():
        await asyncio.sleep(0.005)  # sandbox 已被占用时
        async with limits.acquire("model_call"):
            acquired.append("model_call_while_sandbox_full")

    await asyncio.wait_for(asyncio.gather(hold_sandbox(), try_model_call()), timeout=5)
    assert "model_call_while_sandbox_full" in acquired
    assert limits.backpressure_counts["model_call"] == 0  # 未被 sandbox 饿死


async def test_resource_limits_backpressure_counted():
    limits = ResourceLimits({"sandbox": 1})
    order: list[int] = []

    async def user(i: int):
        async with limits.acquire("sandbox"):
            order.append(i)
            await asyncio.sleep(0.005)

    await asyncio.wait_for(asyncio.gather(user(1), user(2)), timeout=5)
    assert limits.backpressure_counts["sandbox"] >= 1
    assert limits.in_use["sandbox"] == 0  # 全部归还
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
        "docker_image_pull",
        flaky,
        ledger=ledger,
        rng=random.Random(7),
        sleeper=fake_sleep,
    )
    assert result == "done" and attempts["n"] == 3
    assert len(delays) == 2
    assert 0.0 <= delays[0] <= 0.5 and 0.0 <= delays[1] <= 1.0  # full jitter 封顶
    assert [r.succeeded for r in ledger] == [False, False, True]


async def test_retry_non_whitelisted_runs_once():
    """讨论稿 §4 硬规则：不在白名单 = 不自动重试（一次失败原样抛）。"""

    attempts = {"n": 0}

    async def harness_run():
        attempts["n"] += 1
        raise RuntimeError("harness died")

    with pytest.raises(RuntimeError, match="harness died"):
        await retry_local_operation("whole_harness_rerun", harness_run)
    assert attempts["n"] == 1


async def test_retry_grading_stage_single_full_retry():
    attempts = {"n": 0}

    async def grading():
        attempts["n"] += 1
        raise TimeoutError("grading container died")

    with pytest.raises(TimeoutError):
        await retry_local_operation("grading_stage", grading, sleeper=_no_sleep)
    assert attempts["n"] == 2  # 首次 + 恰一次完整重试


async def test_retry_custom_spec_exhaustion_recorded():
    ledger: list = []

    async def always_fail():
        raise OSError("disk")

    with pytest.raises(OSError):
        await retry_local_operation(
            "artifact_atomic_write",
            always_fail,
            whitelist={"artifact_atomic_write": RetrySpec(2, 0.1, 0.2)},
            ledger=ledger,
            sleeper=_no_sleep,
        )
    assert len(ledger) == 2 and all(not r.succeeded for r in ledger)
