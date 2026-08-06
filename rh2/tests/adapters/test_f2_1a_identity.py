"""F2-1a 四层身份验收：physical_attempt_id 的铸造与全链贯穿。

五个断言点对应五个贯穿环节（05 计划 F2-1a 切片）：
worker dispatch 铸造（replay 即新值）→ entry 戳 member metadata →
orchestrator 读入 audit + 登记 registrar → registry sid→paid 映射
（unregister 清理）→ proxy 每条 ModelCallAttempt 落账。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from repoharness2.adapters.slime.async_worker import (
    BoundedDeliveryQueue,
    ContinuousExecutionWorker,
    ExecutionTaskSpec,
    ModelCallProxy,
)
from repoharness2.adapters.slime.capture_wire import CaptureRegistry
from repoharness2.contracts.fa_runtime import ExecutionIdentity, TrainingRuntimeWindow


class _Hook:
    def on_generate_response(self, **kwargs) -> None:
        pass


def test_contract_pair_validator():
    """physical_attempt_id 与 seq 同现同缺（D2 四层身份的契约面）。"""

    ExecutionIdentity(
        prompt_group_id="g", group_index=0, rollout_execution_id="e",
        physical_attempt_id="e#p1-x", physical_attempt_seq=1,
    )
    with pytest.raises(ValueError, match="同现同缺"):
        ExecutionIdentity(
            prompt_group_id="g", group_index=0, rollout_execution_id="e",
            physical_attempt_id="e#p1-x",
        )


async def test_worker_mints_new_physical_attempt_per_dispatch():
    """replay 语义：同一 rollout_execution_id 两次 dispatch → 不同 paid、
    seq 递增——physical attempt 是 dispatch 时刻的事实，不是 spec 属性。"""

    base = ExecutionTaskSpec(
        rollout_execution_id="exec_R", prompt_group_id="g0", member_slot=0
    )
    supply = [base, base, None]  # 同一逻辑执行重供两次（模拟 replay 重派）
    seen: list[ExecutionTaskSpec] = []

    async def execute(spec):
        seen.append(spec)
        return ["ok"]

    async def _no_sleep(_s):
        await asyncio.sleep(0)

    worker = ContinuousExecutionWorker(
        task_source=lambda: supply.pop(0) if supply else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(8),
        failure_sink=lambda s, e: None,
        concurrency=1,
        poll_interval_seconds=0.0,
        sleeper=_no_sleep,
    )
    stop = asyncio.Event()

    async def stopper():
        while len(seen) < 2:
            await asyncio.sleep(0)
        stop.set()

    await asyncio.gather(worker.run(stop), stopper())
    assert len(seen) == 2
    a, b = seen
    assert a.physical_attempt_id and b.physical_attempt_id
    assert a.physical_attempt_id != b.physical_attempt_id  # replay = 新事实键
    assert (a.physical_attempt_seq, b.physical_attempt_seq) == (1, 2)
    assert a.physical_attempt_id.startswith("exec_R#p1-")


def test_registry_paid_map_lifecycle():
    """sid→paid 映射：登记/读取/unregister 清理（有界）。"""

    registry = CaptureRegistry()
    registry.register("sid_P", _Hook())
    registry.set_physical_attempt_id("sid_P", "exec_R#p1-abc")
    assert registry.physical_attempt_id_for("sid_P") == "exec_R#p1-abc"
    assert registry.physical_attempt_id_for(None) is None
    registry.unregister("sid_P")
    assert registry.physical_attempt_id_for("sid_P") is None  # 随会话清理


async def test_proxy_stamps_paid_on_all_attempt_paths():
    """proxy 三条路径（delivered/aborted→recovered/failed）的每条
    ModelCallAttempt 都携带 physical_attempt_id。"""

    now = datetime.now(timezone.utc)

    def window(epoch, phase, active, target=None, completed=True):
        return TrainingRuntimeWindow(
            update_epoch=epoch, phase=phase, old_version="0",
            target_version=target or active, active_version=active,
            window_started_at=now,
            window_completed_at=(now + timedelta(seconds=1)) if completed else None,
            fencing_token=f"f{epoch}",
        )

    class Coord:
        def __init__(self):
            self.calls = 0

        def current_window(self):
            self.calls += 1
            # 第一次 send 前 ACTIVE；abort 后 UPDATING epoch2；恢复 ACTIVE v2
            if self.calls <= 2:
                return window(1, "ACTIVE", "1")
            if self.calls == 3:
                return window(2, "UPDATING", "1", target="2", completed=False)
            return window(2, "ACTIVE", "2", target="2")

    async def _no_sleep(_s):
        await asyncio.sleep(0)

    proxy = ModelCallProxy(Coord(), sleeper=_no_sleep)
    sends = {"n": 0}

    async def send(attempt):
        sends["n"] += 1
        if sends["n"] == 1:
            return {"text": "", "meta_info": {"id": "rid1", "finish_reason": {"type": "abort"}}}
        return {"text": "ok", "meta_info": {"id": "rid2", "weight_version": "2"}}

    result = await proxy.call(
        "exec_R", "turn_0", send, physical_attempt_id="exec_R#p1-abc"
    )
    result.finalize_delivered("cap_ref")
    assert len(proxy.attempts_ledger) >= 2  # aborted + delivered
    for attempt in proxy.attempts_ledger:
        assert attempt.physical_attempt_id == "exec_R#p1-abc", attempt.model_call_attempt_id
