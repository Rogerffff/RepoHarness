"""联合审查独立 CPU 探针：真实 manager → queue → generate 的停止及致命传播。

保留评分/队列/编排生产函数；Docker IO、模型交互使用既有 CPU fixture。
不启动真实 Docker、CC、API 或 GPU。
"""

from __future__ import annotations

import asyncio
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))
sys.path.insert(0, str(ROOT / "rh2/tests/grading"))

from grading_fixtures import FakeDocker, make_fixture_spec
from test_slime_generate import SAMPLING_PARAMS, _Args
from test_w1b_termination_facts_producer import _formal_chain

from repoharness2.adapters.slime.bringup import BringupService
from repoharness2.adapters.slime.sandbox_profile import GRADER_TRUSTED_SETUP_ATTEST_PATH
from repoharness2.grading.manager import ExecResult, GradingManagerConfig, SWEGradingManager
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig
from repoharness2.shutdown.chain import LifecycleState


class _GraderIO:
    def __init__(self, profile_fake, mode):
        self.fake = FakeDocker(base_commit="a" * 40, kill_stops=False)
        self.profile_fake = profile_fake
        self.mode = mode
        self.calls = []
        self.rm_calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.eval_entered = asyncio.Event()
        self.eval_release = asyncio.Event()
        self.eval_calls = 0
        self.after_probe = False

    async def __call__(self, *args, input_bytes=None):
        self.calls.append(args)
        if args[0] == "rm":
            self.rm_calls += 1
            if self.mode == "rm_raises":
                raise OSError("docker transport spawn failed during cleanup")
            if self.mode == "block_rm" and self.rm_calls == 1:
                self.entered.set()
                await self.release.wait()
            if self.mode in ("normal", "test_timeout_rm_ok") or (self.mode == "second_rm_ok" and self.rm_calls == 2):
                return await self.fake(*args, input_bytes=input_bytes)
            return ExecResult(1, "", "daemon failed to remove container")
        if args[0] == "inspect" and "{{.State.Running}}" in args:
            if self.mode == "block_inspect" and not self.entered.is_set():
                self.entered.set()
                await self.release.wait()
            if self.mode == "unknown":
                return ExecResult(1, "", "Cannot connect to the Docker daemon")
            if self.mode == "unknown_socket":
                return ExecResult(1, "", "error during connect: dial unix /var/run/docker.sock: connect: no such file or directory")
            if self.mode == "absent":
                return ExecResult(1, "", f"Error: No such object: {args[-1]}")
            if self.mode == "stopped":
                return ExecResult(0, "false\n", "")
            return ExecResult(0, "true\n", "")
        if args[0] == "kill":
            if self.mode == "block_kill":
                self.entered.set()
                await self.release.wait()
            return await self.fake(*args, input_bytes=input_bytes)
        if args[0] == "exec" and args[-1].startswith(f"cat {GRADER_TRUSTED_SETUP_ATTEST_PATH}"):
            return ExecResult(0, "RH2_SETUP_OK=1\nRH2_SETUP_APPLY_RC=0\nRH2_SETUP_EXPECTED_TEST_FILES=1\nRH2_SETUP_TEST_FILES=1\nRH2_SETUP_ABSENT_TEST_FILES=0\nRH2_SETUP_IRREGULAR_TEST_FILES=\n", "")
        if args[0] == "exec" and args[-1].startswith("bash ") and ".trusted_setup " in args[-1]:
            return ExecResult(0, "trusted setup complete\n", "")
        if args[0] == "exec" and args[-1].startswith("bash ") and "2>&1" in args[-1]:
            self.eval_calls += 1
            self.eval_entered.set()
            if self.mode in ("cancel_submitter", "cancel_worker") or self.mode.startswith("test_timeout"):
                await self.eval_release.wait()
        handled = self.profile_fake.dispatch(args, input_bytes)
        if handled is not None:
            return handled
        return await self.fake(*args, input_bytes=input_bytes)


async def case(mode):
    chain = _formal_chain()
    task = chain.orchestrator._task_resolver
    spec = make_fixture_spec(
        task.base_commit, task.image, checkout_mode="image_embedded",
        task_id=task.task_id,
        **({"test_timeout_seconds": 0.03} if mode.startswith("test_timeout") else {}),
    )
    chain.orchestrator._task_resolver = replace(task, grading_spec=spec)
    io = _GraderIO(chain.docker.profile_fake, mode)
    manager = SWEGradingManager(
        GradingManagerConfig(cleanup_timeout_seconds=1, sandbox_profile=chain.docker.profile_fake.grader_profile),
        docker=io,
    )
    queue = GradingQueue(manager, GradingQueueConfig(concurrency=1, queue_size=1))
    await queue.start()
    service = SimpleNamespace(lifecycle=LifecycleState(), grading_queue=queue)

    async def submit(**kwargs):
        return await BringupService._grading_submit(service, **kwargs)

    notices = []
    chain.orchestrator._grading_submit = submit
    chain.orchestrator._notify_fatal_halt = notices.append
    running = asyncio.create_task(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
    output = {"case": mode}
    closing = None
    if mode.startswith("block_"):
        await asyncio.wait_for(io.entered.wait(), timeout=2)
        started = time.monotonic()
        await asyncio.sleep(1.05)
        output.update(
            cleanup_config_seconds=manager.config.cleanup_timeout_seconds,
            observed_wait_seconds=round(time.monotonic() - started, 3),
            pending_after_cleanup_budget=not running.done(),
            grading_worker_active=queue.active_grading_count,
            fatal_notices_before_release=len(notices),
        )
        io.release.set()
    if mode == "cancel_submitter":
        await asyncio.wait_for(io.eval_entered.wait(), timeout=2)
        running.cancel()
        try:
            await asyncio.wait_for(running, timeout=2)
        except asyncio.CancelledError:
            pass
        output["generate_cancelled"] = running.cancelled()
        output["grader_active_after_generate_cancel"] = queue.active_grading_count
        io.eval_release.set()
        await asyncio.wait_for(queue._queue.join(), timeout=2)
        output["queue_worker_alive_after_scope_failure"] = not queue._workers[0].done()
    else:
        if mode == "cancel_worker":
            await asyncio.wait_for(io.eval_entered.wait(), timeout=2)
            closing = asyncio.create_task(queue.close(drain=False))
        try:
            delivered = await asyncio.wait_for(running, timeout=3)
            output["returned_samples"] = len(delivered)
            output["removed_sample_count"] = sum(s.remove_sample for s in delivered)
            output["returned_rewards"] = [
                "NaN" if isinstance(s.reward, float) and math.isnan(s.reward) else s.reward for s in delivered
            ]
        except Exception as exc:
            output["exception_type"] = type(exc).__name__
            output["reason_code"] = getattr(exc, "reason_code", None)
            output["exception_detail"] = str(exc)[:200]
    if closing is not None:
        await asyncio.sleep(0.05)
        output["queue_close_pending_after_grade_unwound"] = not closing.done()
        output["queue_worker_alive_after_close_cancel"] = not queue._workers[0].done()
        closing.cancel()
        try:
            await closing
        except asyncio.CancelledError:
            pass
    audit = chain.orchestrator.audits[-1]
    output.update(
        eval_calls=io.eval_calls,
        rm_calls=io.rm_calls,
        kill_calls=sum(c[0] == "kill" for c in io.calls),
        fatal_notices=[n.reason_code for n in notices],
        cleanup_failures=manager.cleanup_failures,
        grading_container_records=len(manager.container_records),
        grading_containers_unremoved=sum(not r.removed for r in manager.container_records),
        rollout_cleanup_completed="cleanup_completed" in [e.step for e in audit.timeline],
        rollout_containers_removed=len(chain.docker.removed),
        outcome_termination=None if audit.outcome_v2 is None else audit.outcome_v2["termination_kind"],
        grading_report_outcome=None if audit.finalized is None else audit.finalized.grading_report.outcome,
        grading_failure_detail=None if audit.finalized is None else audit.finalized.grading_report.infra_failure_detail,
    )
    await queue.close(drain=False)
    return output


async def main():
    modes = (
        "normal", "stopped", "absent", "second_rm_ok", "running", "unknown",
        "unknown_socket", "rm_raises", "block_rm", "block_inspect", "block_kill", "cancel_submitter",
        "test_timeout_rm_ok", "test_timeout_running", "cancel_worker",
    )
    results = []
    for mode in modes:
        result = await case(mode)
        assert result["eval_calls"] > 0, result
        if mode.startswith("block_"):
            assert result["pending_after_cleanup_budget"] and not result["fatal_notices_before_release"], result
        if mode in ("running", "unknown", "test_timeout_running") or mode.startswith("block_"):
            assert result["reason_code"] == "grading_scope_termination_failed", result
        if mode == "unknown_socket":
            assert result["returned_samples"] == 1 and not result["fatal_notices"], result
            assert any(":absent" in f for f in result["cleanup_failures"]), result
        if mode == "cancel_submitter":
            assert not result["fatal_notices"] and result["queue_worker_alive_after_scope_failure"], result
            assert any("container_scope_termination_failed" in f for f in result["cleanup_failures"]), result
        if mode == "cancel_worker":
            assert result["queue_close_pending_after_grade_unwound"], result
        if mode == "test_timeout_rm_ok":
            assert result["grading_report_outcome"] == "failed_to_grade", result
            assert result["grading_containers_unremoved"] == 0, result
        results.append(result)
    print(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    asyncio.run(main())
