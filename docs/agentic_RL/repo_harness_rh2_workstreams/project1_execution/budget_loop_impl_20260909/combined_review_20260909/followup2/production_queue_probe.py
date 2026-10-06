"""R5-F1 第二次窄复核：复用上轮两个积压反例及三个真实取消 fatal 对照。"""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "followup"))
import production_followup_probe as old
old.HERE = HERE  # 仅让复用 helper 的临时目录落本轮目录；不执行旧 main、不改旧工件。
from repoharness2.adapters.slime import bringup
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig


async def drain_case(*, cancel_submitters=False):
    # 上轮 drain_case 的最小副本：只改 _closing 的同步点与成功结果断言。
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    class Manager:
        async def grade(self, **kwargs):
            calls.append(kwargs["trajectory_id"])
            if len(calls) == 1:
                entered.set()
                await release.wait()
            return "report"

    queue = GradingQueue(Manager(), GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    spec = SimpleNamespace(task_id="task")
    first = asyncio.create_task(queue.submit(trajectory_id="first", workspace=None, spec=spec))
    await entered.wait()
    second = asyncio.create_task(queue.submit(trajectory_id="second", workspace=None, spec=spec))
    while queue.queue_depth != 1:
        await asyncio.sleep(0)
    if cancel_submitters:
        first.cancel()
        second.cancel()
        await asyncio.gather(first, second, return_exceptions=True)
    service = object.__new__(bringup.BringupService)
    service.lifecycle = old.old.LifecycleState()
    service.shutdown_timeouts = replace(old.FAST, grading_drain=0.2)
    service.grading_queue = queue
    service._queue_started = True
    step = next(step for step in service._build_shutdown_steps() if step.name == "grading_queue")
    started = time.monotonic()
    closing = asyncio.create_task(step.run())
    # 修后 _closing 只在 drain 完成后才为真，不能再用它作为释放当前评分的同步点。
    while service.lifecycle.grading_open:
        await asyncio.sleep(0)
    await asyncio.sleep(0.01)
    assert not closing.done() and not queue._closing and not queue._workers[0].done()
    release.set()
    with contextlib.suppress(asyncio.CancelledError):
        await first
    facts = await asyncio.wait_for(closing, 1)
    if not cancel_submitters:
        assert await second == "report"
    output = {"case": "drain_cancelled_backlog" if cancel_submitters else "drain_accepted_backlog",
              "step_facts": facts, "elapsed_seconds": round(time.monotonic() - started, 3),
              "manager_calls": calls, "second_still_pending": not second.done(),
              "remaining_queue_depth": queue.queue_depth, "worker_list_cleared": not queue._workers}
    assert facts["drained_within_timeout"] is True and calls == ["first", "second"], output
    assert queue.queue_depth == 0 and not queue._workers and second.done(), output
    assert output["elapsed_seconds"] < 0.15, output
    return output


async def main():
    rows = [await drain_case(), await drain_case(cancel_submitters=True)]
    with contextlib.redirect_stdout(io.StringIO()):
        for mode in ["cancel_submitter", "cancel_submitter_during_close", "cancel_worker"]:
            row = await old.pipeline_case(mode)
            assert row["eval_calls"] > 0 and row["rollout_cleanup_completed"], row
            assert row["service_fatals"] == ["grading_scope_termination_failed"], row
            assert row["shutdown_scope_failure_occurrences"] == 1, row
            assert len(row["out_of_band_fatals"]) == (1 if mode.startswith("cancel_submitter") else 0), row
            if mode == "cancel_worker":
                assert row["queue_close_completed"] and row["original_workers_done"] and row["worker_list_cleared"], row
            rows.append(row)
    result = json.dumps(rows, ensure_ascii=False, indent=2)
    (HERE / "production_queue_result.json").write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
