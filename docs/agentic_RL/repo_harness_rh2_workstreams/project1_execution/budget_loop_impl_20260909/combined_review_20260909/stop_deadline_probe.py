"""C 停止路径的 CPU 反例及对照；不调用 Docker / CC / 推理服务。

真实入口：formal generate → 预算等待 → 真实 execution_scope → 真实屏障 → 评分/交付。
替身：既有 formal fixture 的模型轨迹、评分与 Docker IO；预算事件为注入点替身。
时钟由可变值控制；kill 何时实际生效与确认回包何时到达分别记录，避免把晚清理误判为墙钟。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from test_slime_generate import SAMPLING_PARAMS, _Args
from test_w1b_termination_facts_producer import _formal_chain, _steps

from repoharness2.adapters.slime import generate as generate_mod
from repoharness2.adapters.slime.quiescence_barrier import DockerQuiescenceBarrier


class Budget:
    def __init__(self):
        self.states, self.callbacks = {}, {}

    def subscribe(self, sid, callback):
        self.callbacks[sid] = callback

    def unsubscribe(self, sid):
        self.callbacks.pop(sid, None)

    def snapshot(self, sid):
        return self.states.get(sid)

    def exhaust(self, sid):
        self.states[sid] = {"cap": 3, "accepted": 3, "exhausted": True, "refused_count": 1}
        self.callbacks[sid](sid)


async def one_case(kind: str) -> dict:
    chain = _formal_chain(barrier=DockerQuiescenceBarrier())
    orch, now, budget = chain.orchestrator, [0.0], Budget()
    orch._clock = lambda: now[0]
    orch._turn_budget_subscribe = budget.subscribe
    orch._turn_budget_unsubscribe = budget.unsubscribe
    orch._turn_budget_snapshot = budget.snapshot
    notices = []
    orch._notify_fatal_halt = notices.append
    stop_entered, driver_cancelled = asyncio.Event(), asyncio.Event()
    kill_effect_at, confirmation_at = [], []
    drain_calls, active_driver = [], []
    original_docker, original_drain = orch._docker, orch._session_drain_owner

    async def io(*args, input_bytes=None):
        if args[0] == "exec" and "pkill -9 -u agent" in args[-1] and not stop_entered.is_set():
            stop_entered.set()
            if kind.startswith("hang"):
                await asyncio.Event().wait()
            if kind == "kill_effect_after_wall":
                # 这一段模拟 Docker 操作尚未实际生效；agent 仍活着，墙钟确实跨过。
                now[0] = 901.0
            kill_effect_at.append(now[0])
        if args[0] == "exec" and "ps -o pid= -u agent" in args[-1]:
            if kind == "confirmation_after_wall":
                # 反证对照：进程已在墙钟前停止，仅查询回包晚，不能据时间戳补造 hard wall。
                now[0] = 901.0
            confirmation_at.append(now[0])
        return await original_docker(*args, input_bytes=input_bytes)

    async def drain(sid):
        drain_calls.append(sid)
        return await original_drain(sid)

    class Driver:
        name = "cpu_stop_probe"

        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            active_driver.append(asyncio.current_task())
            adapter = chain.adapter_ref["adapter"]
            await adapter.run_all_turns()
            now[0] = 899.5
            if kind == "hang_hard_wall":
                now[0] = 900.1
                return -1
            budget.exhaust(adapter.opened[-1])
            try:
                await asyncio.Event().wait()
            finally:
                driver_cancelled.set()

    orch._docker, orch._session_drain_owner, orch._harness_driver = io, drain, Driver()
    with patch.object(generate_mod, "TURN_BUDGET_EXIT_GRACE_SEC", 0.005):
        running = asyncio.create_task(orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
        await asyncio.wait_for(stop_entered.wait(), timeout=2)
        if kind.startswith("hang"):
            now[0] = 901.0
            done, _ = await asyncio.wait({running}, timeout=0.08)
            audit = orch.audits[-1]
            result = {
                "case": kind,
                "episode_deadline": audit.episode_deadline_monotonic,
                "probe_now": now[0],
                "pending_after_deadline": running not in done,
                "drain_calls_before_probe_cancel": len(drain_calls),
                "halt_notifications_before_probe_cancel": len(notices),
                "removed_before_probe_cancel": len(chain.docker.removed),
            }
            # 只为不让审查探针自身悬挂而取消；它不是代码拥有的期限保护。
            running.cancel()
            try:
                await asyncio.wait_for(running, timeout=2)
            except asyncio.CancelledError:
                pass
            result["harness_pending_after_parent_cancel"] = any(not t.done() for t in active_driver)
            for task in active_driver:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            result["removed_after_probe_cancel"] = len(chain.docker.removed)
            assert result["pending_after_deadline"] and result["drain_calls_before_probe_cancel"] == 0
            assert result["halt_notifications_before_probe_cancel"] == 0
            return result
        delivered = await asyncio.wait_for(running, timeout=3)
        audit = orch.audits[-1]
        result = {
            "case": kind,
            "episode_deadline": audit.episode_deadline_monotonic,
            "kill_effect_at": kill_effect_at,
            "zero_process_confirmation_at": confirmation_at,
            "harness_exit_code": audit.harness_exit_code,
            "remaining_at_harness_exit": audit.episode_deadline["remaining_at_harness_exit"],
            "deadline_hit_by": audit.episode_deadline["hit_by"],
            "termination": audit.outcome_v2["termination_kind"],
            "completion": audit.outcome_v2["completion_class"],
            "delivered_remove_sample": [s.remove_sample for s in delivered],
            "grading_calls": len(chain.grading.calls),
            "real_runtime_barrier_passed": audit.runtime_quiescence_confirmed,
            "stop": audit.termination["stop"],
            "cleaned": "cleanup_completed" in _steps(audit),
        }
        assert result["real_runtime_barrier_passed"] and result["grading_calls"] == 1
        assert result["termination"] == "max_turns_exhausted"
        assert not any(result["delivered_remove_sample"])
        return result


async def main():
    results = []
    for kind in ("stop_before_wall", "kill_effect_after_wall", "confirmation_after_wall", "hang_turn_stop", "hang_hard_wall"):
        results.append(await one_case(kind))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
