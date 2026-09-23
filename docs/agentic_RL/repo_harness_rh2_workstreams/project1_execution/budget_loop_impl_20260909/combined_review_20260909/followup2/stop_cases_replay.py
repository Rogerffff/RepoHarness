"""R2/R3 定向复核：真实 formal 编排、停止 helper、屏障、处置函数；仅替换 Docker IO。

旧探针保留不改。这里把 kill 返回与进程实际停止拆开，额外检查墙后观测到正进程数的情况。
本机 CPU 运行；不启动 Docker、CC、推理服务。模拟钟只驱动 episode 事实；IO 超时仍用真实事件循环。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stop_deadline_probe as old

from repoharness2.adapters.slime import quiescence_barrier
from repoharness2.adapters.slime.bringup import make_disposition_policy
from repoharness2.governance.admission import AdmissionPayloadV1, decide_member_disposition
from repoharness2.grading.manager import ExecResult


async def one_case(kind: str) -> dict:
    chain = old._formal_chain(barrier=old.DockerQuiescenceBarrier())
    orch, now, budget = chain.orchestrator, [0.0], old.Budget()
    orch._clock = lambda: now[0]
    orch._turn_budget_subscribe = budget.subscribe
    orch._turn_budget_unsubscribe = budget.unsubscribe
    orch._turn_budget_snapshot = budget.snapshot
    notices, events, drivers = [], [], []
    orch._notify_fatal_halt = notices.append
    original_docker = orch._docker
    count_reads = 0
    kills = 0
    stop_entered = asyncio.Event()

    async def io(*args, input_bytes=None):
        nonlocal count_reads, kills
        if args[0] == "exec" and "pkill -9 -u agent" in args[-1]:
            kills += 1
            stop_entered.set()
            if kind.startswith("hang_"):
                events.append({"kind": "kill_hang", "at": now[0]})
                await asyncio.Event().wait()
            if kills == 1:
                if kind == "kill_effect_after_wall":
                    now[0] = 901.0
                if kind == "kill_reply_late_but_effect_before_wall":
                    events.append({"kind": "actual_stop", "at": now[0]})
                    now[0] = 901.0
                elif kind not in ("kill_failed_alive_after_wall", "kill_ok_positive_count_after_wall"):
                    events.append({"kind": "actual_stop", "at": now[0]})
                code = 1 if kind == "kill_failed_alive_after_wall" else 0
                events.append({"kind": "kill_return", "at": now[0], "exit_code": code})
                if code:
                    # docker exec 本身失败：真实 _DockerWorkspace.run_bash 原样返回 ExecResult。
                    return ExecResult(code, "", "Error response from daemon: exec failed")
                return ExecResult(0, "pkill_status=0\n", "")
            else:
                events.append({"kind": "barrier_kill", "at": now[0]})
        if args[0] == "exec" and "ps -o pid= -u agent" in args[-1]:
            count_reads += 1
            query_started_at = now[0]
            if kind in ("kill_failed_alive_after_wall", "kill_ok_positive_count_after_wall"):
                if count_reads <= 2:
                    now[0] = 900.1 if count_reads == 1 else 900.2
                    events.append({"kind": "count", "at": now[0], "query_started_at": query_started_at, "residual": 1})
                    return ExecResult(0, "1\n", "")
                if count_reads == 3:
                    now[0] = 901.0
                    events.append({"kind": "actual_stop", "at": now[0]})
            if kind == "confirmation_after_wall":
                now[0] = 901.0
            events.append({"kind": "count", "at": now[0], "query_started_at": query_started_at, "residual": 0})
            return ExecResult(0, "0\n", "")
        return await original_docker(*args, input_bytes=input_bytes)

    class Driver:
        name = "cpu_stop_facts_followup"

        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            drivers.append(asyncio.current_task())
            adapter = chain.adapter_ref["adapter"]
            await adapter.run_all_turns()
            now[0] = 899.5
            if kind == "hang_hard_wall":
                now[0] = 900.1
                return -1
            budget.exhaust(adapter.opened[-1])
            await asyncio.Event().wait()

    orch._docker, orch._harness_driver = io, Driver()
    started = asyncio.get_running_loop().time()
    with (
        patch.object(old.generate_mod, "TURN_BUDGET_EXIT_GRACE_SEC", 0.005),
        patch.object(old.generate_mod, "EXECUTION_SCOPE_STOP_TIMEOUT_SEC", 0.08),
        patch.object(quiescence_barrier, "_STOP_TOTAL_TIMEOUT_SECONDS", 0.08),
    ):
        # 正常正进程数的两案需要允许 helper 的 0.5 秒间隔；挂起案专用短 IO 总预算。
        if not kind.startswith("hang_"):
            with patch.object(old.generate_mod, "EXECUTION_SCOPE_STOP_TIMEOUT_SEC", 2.0):
                delivered = await asyncio.wait_for(orch.generate(old._Args(), chain.base_sample, dict(old.SAMPLING_PARAMS)), 5)
        else:
            delivered = await asyncio.wait_for(orch.generate(old._Args(), chain.base_sample, dict(old.SAMPLING_PARAMS)), 5)
    audit = orch.audits[-1]
    result = {
        "case": kind,
        "episode_deadline": audit.episode_deadline_monotonic,
        "events": events,
        "termination": audit.outcome_v2["termination_kind"],
        "completion": audit.outcome_v2["completion_class"],
        "stop": audit.termination["stop"],
        "barrier_passed": audit.runtime_quiescence_confirmed,
        "grading_calls": len(chain.grading.calls),
        "remove_samples": [s.remove_sample for s in delivered],
        "cleaned": "cleanup_completed" in old._steps(audit),
        "harness_tasks_settled": all(t.done() for t in drivers),
        "halt_notifications": len(notices),
        "elapsed_seconds": round(asyncio.get_running_loop().time() - started, 3),
    }
    if kind.startswith("hang_"):
        assert result["stop"]["stop_timed_out"] and not result["barrier_passed"]
        assert result["grading_calls"] == 0 and all(result["remove_samples"])
    else:
        # formal 夹具不经 miles 的样本身份盖章；这里只验证真实载荷的处置纯函数，不冒充整组 buffer 实验。
        verdicts = [decide_member_disposition(AdmissionPayloadV1.model_validate(s.metadata["rh2_admission"]), policy=make_disposition_policy()) for s in delivered]
        result["member_verdicts"] = [{"verdict": v.verdict, "reason": v.reason_code} for v in verdicts]
        assert result["barrier_passed"] and result["grading_calls"] == 1
        expected = "hard_wall_timeout" if kind in ("kill_effect_after_wall", "kill_reply_late_but_effect_before_wall", "kill_failed_alive_after_wall", "kill_ok_positive_count_after_wall") else "max_turns_exhausted"
        assert result["termination"] == expected
        expected_verdict = "DROP_GROUP" if expected == "hard_wall_timeout" else "KEEP_FULL"
        assert all(v.verdict == expected_verdict for v in verdicts)
        if "positive_count" in kind or kind == "kill_failed_alive_after_wall":
            assert any(e["kind"] == "count" and e["query_started_at"] > 900 and e["residual"] > 0 for e in events)
            assert expected_verdict == "DROP_GROUP"  # 本轮：旧强反例应被丢弃。
    assert result["cleaned"] and result["harness_tasks_settled"]
    return result


async def main():
    for kind in (
        "stop_before_wall", "kill_effect_after_wall", "confirmation_after_wall",
        "kill_failed_alive_after_wall", "kill_ok_positive_count_after_wall",
        "kill_reply_late_but_effect_before_wall", "hang_turn_stop", "hang_hard_wall",
    ):
        print(json.dumps(await one_case(kind), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
