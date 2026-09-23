"""批 B 独立 CPU 探针：额度取消、跨 loop 期限、引导整数截断。

只调用真实 Python 控制流；Docker / CC / 网络请求全部由明确替身隔离。
运行：在 rh2 下执行 uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/
project1_execution/budget_loop_impl_20260909/batch_b_review/queue_deadline_probe.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from test_async_worker import FakeCoordinator, _ok_response, _window
from test_capture_registry_fa import FakeHook

from repoharness2.adapters.slime.async_worker import (
    ModelCallProxy, ResourceLimits, SessionPoisonRegistry, UnattributableModelCallError,
)
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver
from repoharness2.adapters.slime.capture_wire import CaptureRegistry
from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS, SlimeBindingError


def proxy_for(limits=None, *, phase="ACTIVE", attempt_timeout=None):
    return ModelCallProxy(
        FakeCoordinator([_window(epoch=1, phase=phase, active="1", target="1" if phase == "ACTIVE" else "2")]),
        limits=limits, attempt_timeout_seconds=attempt_timeout,
    )


async def queue_case(mode):
    limits, poison, sent = ResourceLimits({"model_call": 1}), SessionPoisonRegistry(), []
    proxy = proxy_for(limits)
    held = limits.acquire("model_call")
    await held.__aenter__()

    async def send(n):
        sent.append(n)
        return _ok_response([1], "1")

    start = time.monotonic()
    task = asyncio.create_task(proxy.call(
        "paid", "t1", send, session_id="sid", poison_registry=poison,
        deadline_monotonic=start + (0.035 if mode == "deadline" else 10),
        min_attempt_budget_seconds=0,
    ))
    await asyncio.sleep(0.015)
    if mode == "cancel":
        task.cancel("external_stop")
    reason = None
    try:
        await task
    except UnattributableModelCallError as exc:
        reason = exc.reason_code
    except asyncio.CancelledError:
        reason = "CancelledError"
    elapsed = time.monotonic() - start
    await held.__aexit__(None, None, None)
    assert not sent and limits.in_use["model_call"] == 0
    assert limits._semaphores["model_call"]._value == 1
    return dict(mode=mode, reason=reason, poison=poison.reason("sid"), elapsed=round(elapsed, 4),
                queue_wait=proxy.queue_wait_seconds_total("paid"), capacity_restored=True)


async def cancel_acquire_races():
    counts = {}
    for release_first in (False, True):
        for _ in range(25):
            limits = ResourceLimits({"model_call": 1})
            proxy = proxy_for(limits)
            held = limits.acquire("model_call")
            await held.__aenter__()
            task = asyncio.create_task(proxy._send(
                lambda n: asyncio.sleep(0.1), 1, time.monotonic() + 1,
                execution_scope="paid", min_attempt_budget_seconds=0,
            ))
            while not limits._semaphores["model_call"]._waiters:
                await asyncio.sleep(0)
            if release_first:
                await held.__aexit__(None, None, None)
                await asyncio.sleep(0)  # 让获取 task 有机会先完成，再取消外层
                task.cancel()
            else:
                task.cancel()
                await held.__aexit__(None, None, None)
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert limits.in_use["model_call"] == 0
            assert limits._semaphores["model_call"]._value == 1
            counts[str(release_first)] = counts.get(str(release_first), 0) + 1
    return dict(cases=counts, capacity_restored=True)


async def active_wait_case():
    proxy, poison = proxy_for(phase="PAUSING"), SessionPoisonRegistry()
    sent = []

    async def send(n):
        sent.append(n)
        return _ok_response([1], "1")

    deadline = time.monotonic() + 0.035
    try:
        await proxy.call("paid", "t1", send, poison_registry=poison,
                         deadline_monotonic=deadline, min_attempt_budget_seconds=0)
    except UnattributableModelCallError as exc:
        assert not sent
        return dict(reason=exc.reason_code, expired=time.monotonic() >= deadline,
                    poison=poison.reason("paid"))
    raise AssertionError("应在 ACTIVE 等待期间结束")


async def cross_loop_case():
    registry = CaptureRegistry()
    deadline = time.monotonic() + 0.075
    registry.register("sid", FakeHook(), deadline_monotonic=deadline)
    await asyncio.sleep(0.015)  # 首调之前已经占用的时间

    async def adapter_side():
        seen = registry.session_deadline("sid")
        limits = ResourceLimits({"model_call": 1})
        proxy = proxy_for(limits)
        held = limits.acquire("model_call")
        await held.__aenter__()
        try:
            await proxy.call("paid", "t1", lambda n: asyncio.sleep(0),
                             deadline_monotonic=seen, min_attempt_budget_seconds=0)
        except UnattributableModelCallError as exc:
            return dict(same_deadline=seen == deadline, reason=exc.reason_code,
                        remaining_at_end=round(deadline - time.monotonic(), 4))
        finally:
            await held.__aexit__(None, None, None)
        raise AssertionError("不应得到额度")

    result = await asyncio.to_thread(lambda: asyncio.run(adapter_side()))
    registry.unregister("sid")
    assert result["same_deadline"] and result["reason"] == "episode_deadline_exhausted"
    assert registry.session_deadline("sid") is None
    return result


async def driver_floor_case():
    calls = []

    async def install(*args, **kwargs):
        pass

    async def bounded_failure(*args, input_bytes=None, timeout=None):
        calls.append(timeout)
        await asyncio.sleep(timeout)
        return 124, "", "探针：按驱动传入的 timeout 等满后结束"

    facts = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    start = time.monotonic()
    try:
        with patch.object(ClaudeCodeDriver, "_install_native_cli", install), patch(
            "repoharness2.adapters.slime.docker_sandbox._run", bounded_failure
        ):
            try:
                code = await ClaudeCodeDriver().run(
                    type("Sandbox", (), {"container_name": "probe-no-docker"})(),
                    workdir="/testbed", session_id="sid", adapter_url="http://unused",
                    time_budget_sec=2, prompt="probe",
                )
                result = dict(exit_code=code)
            except SlimeBindingError as exc:
                result = dict(error_code=exc.reason_code)
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    result.update(timeouts=calls, elapsed=round(time.monotonic() - start, 4), facts=facts)
    return result


async def main():
    for name, fn in [
        ("queue_deadline", lambda: queue_case("deadline")),
        ("queue_external_cancel", lambda: queue_case("cancel")),
        ("cancel_acquire_races", cancel_acquire_races),
        ("active_wait_deadline", active_wait_case),
        ("cross_loop_deadline", cross_loop_case),
        ("driver_floor_timeout", driver_floor_case),
    ]:
        print(json.dumps({"case": name, "observed": await fn()}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
