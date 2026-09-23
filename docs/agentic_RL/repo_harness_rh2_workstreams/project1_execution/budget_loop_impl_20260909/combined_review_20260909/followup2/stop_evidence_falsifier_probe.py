"""第二次 R3 窄复核：真实 formal/helper/屏障/准入处置；只替换 Docker IO、观测钟与等待常量。

旧探针不改。本文件只复用旧 CPU formal 夹具，不启动 Docker、CC 或模型服务。
屏障 helper 的包装只让它使用同一观测钟并记录返回值，不改动作、分支或返回对象。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stop_deadline_probe as old

from repoharness2.adapters.slime import execution_scope, quiescence_barrier
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
    notices, events, drivers, barrier_results = [], [], [], []
    orch._notify_fatal_halt = notices.append
    original_docker = orch._docker
    kills = 0
    counts_this_kill = 0
    retry_case = kind.startswith("unproven_")
    barrier_kill_number = 4 if retry_case else 2

    async def io(*args, input_bytes=None):
        nonlocal kills, counts_this_kill
        if args[0] == "exec" and "pkill -9 -u agent" in args[-1]:
            kills += 1
            counts_this_kill = 0
            code = 1 if retry_case and kills <= 3 else 0
            if kills == barrier_kill_number:
                if kind in (
                    "delivered_count_timeout_barrier_alive_after_wall",
                    "delivered_pre_wall_presence_then_barrier_alive_after_wall",
                    "unproven_barrier_zero_after_wall",
                ):
                    now[0] = 900.1
                elif retry_case:
                    now[0] = 899.4
            events.append({"kind": "kill", "number": kills, "returned_at": now[0], "exit_code": code})
            return ExecResult(code, "" if code else "pkill_status=0\n", "probe: exec failed" if code else "")
        if args[0] == "exec" and "ps -o pid= -u agent" in args[-1]:
            counts_this_kill += 1
            issued = now[0]
            residual = 0
            if retry_case and kills <= 3:
                residual = 1
            elif kills == 1 and kind == "delivered_count_timeout_barrier_alive_after_wall":
                now[0] = 900.1
                events.append({"kind": "count_timeout", "issued_at": issued, "wall_passed_at": now[0]})
                await asyncio.Event().wait()
            elif kills == 1 and kind == "delivered_pre_wall_presence_then_barrier_alive_after_wall":
                now[0], residual = 890.0 + counts_this_kill * 0.5, 1
            elif kills == barrier_kill_number and kind.startswith("delivered_"):
                # IO 前提：第一轮投递未覆盖的活进程仍在；例如文档已列出的枚举/fork 竞态残留。
                # 第二次 kill 的返回也只代表命令完成。真正归零由下一个查询确认。
                if counts_this_kill == 1:
                    now[0], residual = 900.2, 1
                else:
                    now[0] = 901.0
            elif kills == barrier_kill_number and kind == "unproven_barrier_zero_after_wall":
                now[0] = 901.0
            elif kills == barrier_kill_number and kind == "unproven_barrier_count_reply_late":
                events.append({"kind": "fixture_actual_zero", "at": 899.5})
                now[0] = 901.0
            elif retry_case and kills == barrier_kill_number:
                now[0] = 899.5
            elif kind == "proven_zero_before_wall_digest_late":
                now[0] = 899.5
            events.append({"kind": "count", "kill_number": kills, "issued_at": issued,
                           "returned_at": now[0], "residual": residual})
            return ExecResult(0, f"{residual}\n", "")
        if args[0] == "exec" and "git status --porcelain" in args[-1] and kills >= barrier_kill_number:
            if kind.endswith("digest_late"):
                now[0] = 901.0
            events.append({"kind": "digest", "returned_at": now[0]})
        return await original_docker(*args, input_bytes=input_bytes)

    async def observed_barrier_stop(workspace, **kwargs):
        result = await execution_scope.terminate_agent_processes(workspace, clock=lambda: now[0], **kwargs)
        barrier_results.append(result.as_dict())
        return result

    async def timed_rollout_stop(workspace, **kwargs):
        if kind == "delivered_pre_wall_presence_then_barrier_alive_after_wall":
            # 保留真实 10 次计数上限，仅去掉真实睡眠；观测钟按每次 0.5 秒推进，覆盖次数耗尽而非 IO 超时。
            kwargs["interval"] = 0
        return await execution_scope.terminate_agent_processes(workspace, **kwargs)

    class Driver:
        name = "cpu_stop_evidence_falsifier"

        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            drivers.append(asyncio.current_task())
            adapter = chain.adapter_ref["adapter"]
            await adapter.run_all_turns()
            now[0] = 850.0 if retry_case else (
                890.0 if kind == "delivered_pre_wall_presence_then_barrier_alive_after_wall" else 899.5
            )
            budget.exhaust(adapter.opened[-1])
            await asyncio.Event().wait()

    orch._docker, orch._harness_driver = io, Driver()
    with (
        patch.object(old.generate_mod, "TURN_BUDGET_EXIT_GRACE_SEC", 0.001),
        patch.object(old.generate_mod, "EXECUTION_SCOPE_STOP_TIMEOUT_SEC", 0.2 if kind ==
                     "delivered_pre_wall_presence_then_barrier_alive_after_wall" else 0.02),
        patch.object(old.generate_mod, "EXECUTION_SCOPE_STOP_RETRY_INTERVAL_SEC", 0.001),
        patch.object(old.generate_mod, "terminate_agent_processes", timed_rollout_stop),
        patch.object(quiescence_barrier, "_STOP_TOTAL_TIMEOUT_SECONDS", 0.2),
        patch.object(quiescence_barrier, "_KILL_VERIFY_INTERVAL_SECONDS", 0.001),
        patch.object(quiescence_barrier, "terminate_agent_processes", observed_barrier_stop),
    ):
        delivered = await asyncio.wait_for(orch.generate(old._Args(), chain.base_sample, dict(old.SAMPLING_PARAMS)), 5)
    audit = orch.audits[-1]
    verdicts = [decide_member_disposition(AdmissionPayloadV1.model_validate(s.metadata["rh2_admission"]),
                                        policy=make_disposition_policy()).verdict for s in delivered]
    result = {"case": kind, "deadline": audit.episode_deadline_monotonic, "events": events,
              "stop": audit.termination["stop"], "barrier_stop": barrier_results,
              "termination": audit.outcome_v2["termination_kind"], "member_verdicts": verdicts,
              "barrier_passed": audit.runtime_quiescence_confirmed, "grading_calls": len(chain.grading.calls),
              "cleaned": "cleanup_completed" in old._steps(audit),
              "harness_tasks_settled": all(t.done() for t in drivers), "halt_notifications": len(notices)}
    assert result["barrier_passed"] and result["grading_calls"] == 1
    assert result["cleaned"] and result["harness_tasks_settled"]
    if kind.startswith("delivered_"):
        assert audit.termination["stop"]["kill_verified"] is False
        assert audit.termination["stop"]["stop_before_deadline"] is True
        assert any(o["issued_at"] > 900 and o["residual"] > 0 for o in barrier_results[0]["observations"])
        assert verdicts == ["KEEP_FULL"]  # 当前错误的复现断言，不是修后期望。
        if kind == "delivered_pre_wall_presence_then_barrier_alive_after_wall":
            assert len(audit.termination["stop"]["observations"]) == 10
            assert audit.termination["stop"]["stop_timed_out"] is False
    elif kind in ("unproven_barrier_zero_before_wall_digest_late", "unproven_barrier_zero_after_wall",
                  "unproven_barrier_count_reply_late"):
        assert verdicts == ["DROP_GROUP"]
        if kind.endswith("digest_late"):
            assert barrier_results[0]["confirmed_at"] == 899.5  # 可信零观测在墙前，只有指纹读取晚。
    else:
        assert verdicts == ["KEEP_FULL"]
    return result


async def main():
    for kind in (
        "delivered_count_timeout_barrier_alive_after_wall",
        "delivered_pre_wall_presence_then_barrier_alive_after_wall",
        "unproven_barrier_zero_before_wall",
        "unproven_barrier_zero_before_wall_digest_late",
        "unproven_barrier_zero_after_wall",
        "unproven_barrier_count_reply_late",
        "proven_zero_before_wall_digest_late",
    ):
        print(json.dumps(await one_case(kind), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
