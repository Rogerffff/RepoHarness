"""R2/R4/R5 窄复核；只替换 Docker/模型 IO，保留真实评分与服务接收路径。

不修改旧探针；其 _GraderIO 只作为 CPU IO 替身复用。所有临时工件在本目录内。
"""
from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io as stdio
import json
import math
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
OLD_PATH = HERE.parent / "production_scope_probe.py"
old_spec = importlib.util.spec_from_file_location("old_scope_io", OLD_PATH)
old = importlib.util.module_from_spec(old_spec)
old_spec.loader.exec_module(old)

import pytest
from test_w5a_shutdown_chain import FAST, _assemble_service
from repoharness2.adapters.slime import bringup
from repoharness2.grading import manager as manager_module
from repoharness2.grading.manager import (
    ExecResult, GradingManagerConfig, GradingScopeTerminationError,
    SWEGradingManager, _ContainerRecord,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig


class FollowupIO(old._GraderIO):
    def __init__(self, profile_fake, mode):
        super().__init__(profile_fake, "cancel_submitter" if mode == "cancel_submitter_during_close" else mode)
        self.cancelled_io = []

    async def __call__(self, *args, input_bytes=None):
        try:
            if args[0] == "inspect" and "{{.State.Running}}" in args:
                if self.mode == "malformed_success":
                    self.calls.append(args)
                    return ExecResult(0, "unexpected-output\n", "")
                if self.mode == "other_container_absent":
                    self.calls.append(args)
                    return ExecResult(1, "", "Error: No such object: unrelated-container")
            if self.mode == "block_second_rm" and args[0] == "rm" and self.rm_calls == 1:
                self.calls.append(args)
                self.rm_calls += 1
                self.entered.set()
                await self.release.wait()
                return ExecResult(1, "", "still not removed")
            return await super().__call__(*args, input_bytes=input_bytes)
        except asyncio.CancelledError:
            self.cancelled_io.append(args[0])
            raise


async def pipeline_case(mode):
    chain = old._formal_chain()
    task = chain.orchestrator._task_resolver
    spec = old.make_fixture_spec(
        task.base_commit, task.image, checkout_mode="image_embedded", task_id=task.task_id,
        **({"test_timeout_seconds": 0.03} if mode.startswith("test_timeout") else {}),
    )
    chain.orchestrator._task_resolver = replace(task, grading_spec=spec)
    docker = FollowupIO(chain.docker.profile_fake, mode)
    manager = SWEGradingManager(
        GradingManagerConfig(cleanup_timeout_seconds=1, sandbox_profile=chain.docker.profile_fake.grader_profile),
        docker=docker,
    )
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1), fatal_sink=bringup.notify_run_fatal)
    await queue.start()
    with tempfile.TemporaryDirectory(prefix="scope-", dir=HERE) as temp, pytest.MonkeyPatch.context() as mp:
        service, _ = _assemble_service(Path(temp), mp, orchestrator=chain.orchestrator)
        service.grading_manager = manager
        service.grading_queue = queue
        service._queue_started = True
        mp.setattr(bringup.BringupService, "_instance", service)
        # 保留真实 _run_close/报告归集，只运行与本切片相关的真实关停步骤。
        original_steps = service._build_shutdown_steps
        service._build_shutdown_steps = lambda: [
            step for step in original_steps()
            if step.name in {"intake_stop", "inflight_executions", "grading_queue", "grading_manager", "container_residue"}
        ]
        chain.orchestrator._grading_submit = service._grading_submit

        async def run():
            service.lifecycle.enter_execution(getattr(chain.base_sample, "metadata", None), task_id=task.task_id)
            try:
                return await chain.orchestrator.generate(old._Args(), chain.base_sample, dict(old.SAMPLING_PARAMS))
            finally:
                service.lifecycle.exit_execution()

        running = asyncio.create_task(run())
        output = {"case": mode}
        closing = None
        io_started = None
        if mode.startswith("block_"):
            await asyncio.wait_for(docker.entered.wait(), 2)
            io_started = time.monotonic()
        if mode in ("cancel_submitter", "cancel_submitter_during_close", "cancel_worker"):
            await asyncio.wait_for(docker.eval_entered.wait(), 2)
            if mode == "cancel_worker":
                workers = list(queue._workers)
                closing = asyncio.create_task(queue.close(drain=False))
            else:
                running.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await running
                output["generate_cancelled"] = running.cancelled()
                if mode == "cancel_submitter_during_close":
                    closing = asyncio.create_task(service.close(reason="owner_close"))
                    while service._closing_report is None:
                        await asyncio.sleep(0)
                docker.eval_release.set()
                await asyncio.wait_for(queue._queue.join(), 2)
        if not running.cancelled():
            try:
                delivered = await asyncio.wait_for(running, 3)
                output["returned_rewards"] = [
                    "NaN" if isinstance(s.reward, float) and math.isnan(s.reward) else s.reward for s in delivered
                ]
            except Exception as exc:
                output["exception_type"] = type(exc).__name__
                output["reason_code"] = getattr(exc, "reason_code", None)
        if io_started is not None:
            output["cleanup_wait_observed_seconds"] = round(time.monotonic() - io_started, 3)
            output["probe_released_blocked_io"] = docker.release.is_set()
        if mode == "cancel_worker":
            await asyncio.wait_for(closing, 2)
            output["queue_close_completed"] = closing.done()
            output["original_workers_done"] = all(worker.done() for worker in workers)
            output["worker_list_cleared"] = not queue._workers
        # 用真实服务接收者与真实关停报告验证 sink，避免仅检查 list.append 替身。
        report = await asyncio.wait_for(service.close(reason="probe_end"), 4)
        if closing is not None:
            await closing
        audit = chain.orchestrator.audits[-1]
        output.update(
            eval_calls=docker.eval_calls,
            cancelled_io=docker.cancelled_io,
            service_fatals=[getattr(exc, "reason_code", None) for exc in service.lifecycle.fatal_seen],
            service_fatal_types=[type(exc).__name__ for exc in service.lifecycle.fatal_seen],
            out_of_band_fatals=[getattr(exc, "reason_code", None) for exc in queue.out_of_band_fatals],
            shutdown_trigger=report.trigger,
            shutdown_first_cause=report.first_cause,
            shutdown_first_cause_origin=report.first_cause_origin,
            shutdown_secondary_failures=report.secondary_failures,
            shutdown_ok=report.ok,
            shutdown_scope_failure_occurrences=sum(
                "grading_scope_termination_failed" in (s or "")
                for s in [report.first_cause, *report.secondary_failures]
            ),
            grading_report_outcome=None if audit.finalized is None else audit.finalized.grading_report.outcome,
            rollout_cleanup_completed="cleanup_completed" in [event.step for event in audit.timeline],
            cleanup_failures=manager.cleanup_failures,
            grading_containers_unremoved=sum(not record.removed for record in manager.container_records),
        )
        return output


async def runner_total_deadline_case():
    """真实默认 run_docker 被 wait_for 取消后先 kill/wait；前段耗时不会重置 kill 的剩余量。"""
    procs = []
    started = time.monotonic()

    class Proc:
        def __init__(self, args):
            self.args = args
            self.returncode = 1
            self.kill_count = self.wait_count = 0

        async def communicate(self, input=None):
            if self.args[0] == "rm":
                await asyncio.sleep(0.025)
                return b"", b"remove failed"
            if self.args[0] == "inspect":
                await asyncio.sleep(0.025)
                self.returncode = 0
                return b"true\n", b""
            await asyncio.Event().wait()

        def kill(self):
            self.kill_count += 1

        async def wait(self):
            self.wait_count += 1
            self.returncode = -9
            return -9

    async def create(program, *args, **kwargs):
        assert program == "docker"
        proc = Proc(args)
        procs.append(proc)
        return proc

    manager = SWEGradingManager(GradingManagerConfig(cleanup_timeout_seconds=0.1))
    record = _ContainerRecord("scope-probe", "trajectory", time.time(), time.monotonic())
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(manager_module.asyncio, "create_subprocess_exec", create)
        try:
            await asyncio.wait_for(manager._close_container_scope(record), 1)
        except GradingScopeTerminationError as exc:
            code = exc.reason_code
        else:
            raise AssertionError("scope should remain unknown")
    return {
        "case": "default_runner_total_deadline", "reason_code": code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "configured_total_seconds": 0.1,
        "processes": [{"command": p.args[0], "kill": p.kill_count, "wait": p.wait_count} for p in procs],
        "cleanup_failures": manager.cleanup_failures,
    }


async def drain_case(*, cancel_submitters=False):
    """真实 queue 与 BringupService grading_queue 步；两个已接受请求、一个 worker。"""
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
        # 实际服务先关闭在飞执行：await future 的两个提交者消失，已入队 item 仍存在。
        first.cancel()
        second.cancel()
        await asyncio.gather(first, second, return_exceptions=True)
    service = object.__new__(bringup.BringupService)
    service.lifecycle = old.LifecycleState()
    service.shutdown_timeouts = replace(FAST, grading_drain=0.2)
    service.grading_queue = queue
    service._queue_started = True
    step = next(step for step in service._build_shutdown_steps() if step.name == "grading_queue")
    started = time.monotonic()
    closing = asyncio.create_task(step.run())
    while not queue._closing:
        await asyncio.sleep(0)
    release.set()
    with contextlib.suppress(asyncio.CancelledError):
        await first
    await asyncio.sleep(0.03)
    before_fallback = {"close_pending": not closing.done(), "second_pending": not second.done(),
                       "queue_depth": queue.queue_depth, "workers_all_done": all(w.done() for w in queue._workers)}
    facts = await asyncio.wait_for(closing, 1)
    output = {"case": "drain_cancelled_backlog" if cancel_submitters else "drain_accepted_backlog",
              "before_fallback": before_fallback,
              "step_facts": facts, "elapsed_seconds": round(time.monotonic() - started, 3),
              "manager_calls": calls, "second_still_pending": not second.done(),
              "remaining_queue_depth": queue.queue_depth, "worker_list_cleared": not queue._workers}
    second.cancel()
    await asyncio.gather(second, return_exceptions=True)
    return output


async def main():
    modes = ["normal", "stopped", "absent", "second_rm_ok", "running", "unknown_socket",
             "malformed_success", "other_container_absent", "block_rm", "block_inspect", "block_kill",
             "block_second_rm", "test_timeout_rm_ok", "test_timeout_running", "cancel_submitter",
             "cancel_submitter_during_close", "cancel_worker"]
    results = []
    # 服务真实 _run_close 的日志只作捕获，不混入 JSON。
    with contextlib.redirect_stdout(stdio.StringIO()):
        for mode in modes:
            row = await pipeline_case(mode)
            assert row["eval_calls"] > 0 and row["rollout_cleanup_completed"], row
            fatal = mode not in {"normal", "stopped", "absent", "second_rm_ok", "test_timeout_rm_ok"}
            assert row["service_fatals"] == (["grading_scope_termination_failed"] if fatal else []), row
            assert row["shutdown_scope_failure_occurrences"] == (1 if fatal else 0), row
            assert len(row["out_of_band_fatals"]) == (1 if mode.startswith("cancel_submitter") else 0), row
            if mode.startswith("block_"):
                assert row["cleanup_wait_observed_seconds"] < 1.5 and not row["probe_released_blocked_io"], row
                assert row["cancelled_io"], row
            if mode == "cancel_worker":
                assert row["queue_close_completed"] and row["original_workers_done"] and row["worker_list_cleared"], row
            results.append(row)
    runner = await runner_total_deadline_case()
    assert 0.09 <= runner["elapsed_seconds"] < 0.16, runner
    assert runner["processes"] == [
        {"command": "rm", "kill": 0, "wait": 0}, {"command": "inspect", "kill": 0, "wait": 0},
        {"command": "kill", "kill": 1, "wait": 1}], runner
    results.append(runner)
    drain = await drain_case()
    # 这是本次修复新增的反例，不是建议固化成正确行为的维护 oracle。
    assert drain["manager_calls"] == ["first"] and drain["second_still_pending"], drain
    assert drain["step_facts"]["drained_within_timeout"] is False and drain["worker_list_cleared"], drain
    results.append(drain)
    cancelled_drain = await drain_case(cancel_submitters=True)
    assert cancelled_drain["manager_calls"] == ["first"] and cancelled_drain["remaining_queue_depth"] == 1, cancelled_drain
    assert cancelled_drain["step_facts"]["drained_within_timeout"] is False, cancelled_drain
    results.append(cancelled_drain)
    text = json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False)
    (HERE / "production_followup_probe_result.json").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
