"""#1/#2 实施审查：真实宿主子进程 + 既有正式编排夹具；不调用模型或 Docker。

输出事实，不把当前错误结果写成维护测试的正确 oracle。正式编排的 capture、
停止屏障、grader 仍是既有替身。短写的 OS 限额仅设在独立子进程内。
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

REPO = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path[:0] = [str(REPO / p) for p in ("rh2/src", "rh2/tests", "rh2/tests/adapters")]
sys.dont_write_bytecode = True

import pytest
from repoharness2.adapters.slime import bringup
from repoharness2.adapters.slime import docker_sandbox as ds
from repoharness2.adapters.slime.generate import (
    HARNESS_LAUNCH_FACTS,
    SlimeBindingError,
)
from test_slime_generate import SAMPLING_PARAMS, _Args
from test_w3b_sandbox_profile import _formal_chain


async def collect_script(script: str, directory: Path, *, deadline: float = 3):
    return await ds.run_host_collected(
        [sys.executable, "-u", "-c", script],
        stdout_path=directory / "stdout", stderr_path=directory / "stderr", deadline_seconds=deadline,
    )


async def formal_case(label: str, rc: int, *, cap: bool = False, typed: bool = False, log_facts: bool = False):
    chain = _formal_chain(harness_exit_code=rc)
    if cap:
        chain.orchestrator._turn_budget_snapshot = lambda sid: {
            "cap": 3, "accepted": 3, "exhausted": True, "refused_count": 1,
        }
    original_driver = chain.orchestrator._harness_driver
    with tempfile.TemporaryDirectory(prefix="rh2-review-audit-") as directory:
        root = Path(directory)

        class Driver:
            name = "mock_harness"

            async def run(self, sandbox, **kwargs):
                result = await original_driver.run(sandbox, **kwargs)
                if log_facts:
                    out, err = root / "trajectory.jsonl", root / "stderr.log"
                    out.write_text("already received\n")
                    err.write_text("")
                    HARNESS_LAUNCH_FACTS.get()["harness_log"] = {
                        "stdout_path": str(out), "stderr_path": str(err),
                        "stdout_bytes": out.stat().st_size, "log_complete": not typed,
                        "client_exit_kind": "docker_cli_error" if typed else "container_process_exit",
                    }
                if typed:
                    raise SlimeBindingError("harness_exec_connection_lost", "injected host connection loss")
                return result

        chain.orchestrator._harness_driver = Driver()
        delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
        audit = chain.orchestrator.audits[0]
        record_path = root / "audit.jsonl"
        bringup.write_execution_audit_record(None, audit, record_path)
        record = json.loads(record_path.read_text().splitlines()[-1])
        outcome = audit.outcome_v2 or {}
        return {
            "case": label, "input_exit_code": rc,
            "reject_on_nonzero": chain.orchestrator.config.reject_on_nonzero_harness_exit,
            "completion_class": outcome.get("completion_class"), "termination_kind": outcome.get("termination_kind"),
            "reward": delivered[0].reward, "remove_sample": getattr(delivered[0], "remove_sample", None),
            "grading_calls": len(chain.grading.calls),
            "persisted_harness_log_present": record.get("harness_log") is not None,
            "harness_paths_indexed": sum(p.name in ("trajectory.jsonl", "stderr.log") for p in audit.artifact_paths),
            "failure_details": [f.detail for f in audit.failure_records],
        }


async def cancelled_launch(*, outer_deadline: bool = False):
    """实际 launch→collector 取消；只短路 bootstrap 并把 docker 命令换成本机 Python。"""
    from slime.agent import sandbox
    from slime.agent.harness import ClaudeCodeHarness

    with tempfile.TemporaryDirectory(prefix="rh2-review-cancel-") as directory, pytest.MonkeyPatch.context() as mp:
        root = Path(directory)
        mp.setattr(sandbox, "ensure_agent_user", AsyncMock())
        mp.setattr(ClaudeCodeHarness, "write_config", AsyncMock())
        mp.setattr(ds, "host_exec_argv", lambda **kwargs: [
            sys.executable, "-u", "-c", "import time; print('prefix', flush=True); time.sleep(30)",
        ])
        facts = {}
        token = HARNESS_LAUNCH_FACTS.set(facts)
        task = asyncio.create_task(bringup.launch_claude_code(
            type("Sandbox", (), {"container_name": "fixture"})(), workdir="/testbed",
            session_id="review-token", adapter_url="http://unused", prompt="unused", time_budget_sec=60,
            env_injections={}, harness_log_dir=str(root),
        ))
        out = root / "trajectory.jsonl"
        try:
            for _ in range(300):
                if out.exists() and out.stat().st_size:
                    break
                if task.done():
                    await task
                await asyncio.sleep(0.01)
            assert out.exists() and out.stat().st_size, "producer did not reach collection"
            cancelled = False
            deadline_rc = None
            hit_by = None
            if outer_deadline:
                chain = _formal_chain()
                chain.orchestrator._clock = time.monotonic
                audit = SimpleNamespace(
                    episode_deadline_monotonic=time.monotonic() + 0.1,
                    episode_deadline={"hit_by": "none"}, mark=lambda _: None, failure_records=[],
                )
                deadline_rc = await asyncio.wait_for(chain.orchestrator._await_harness_within_deadline(
                    task, audit=audit, launch_facts=facts,
                ), 3)
                hit_by = audit.episode_deadline["hit_by"]
            else:
                task.cancel()
                try:
                    await asyncio.wait_for(task, 3)
                except asyncio.CancelledError:
                    cancelled = True
            return {
                "cancel_propagated": cancelled, "partial_file_bytes": out.stat().st_size,
                "outer_deadline_rc": deadline_rc, "hit_by": hit_by,
                "harness_log_in_launch_facts": "harness_log" in facts,
                "pending_pumps": sum("pump" in str(t.get_coro()) for t in asyncio.all_tasks() if not t.done()),
            }
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            HARNESS_LAUNCH_FACTS.reset(token)


async def short_write_child():
    import resource

    # 隔离子进程的真实文件大小限制，既不改父进程限额，也不耗尽磁盘。
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    with tempfile.TemporaryDirectory(prefix="rh2-review-shortwrite-") as directory:
        root = Path(directory)
        run = await collect_script("import sys; sys.stdout.buffer.write(b'x' * 8192)", root)
        return {
            "input_bytes": 8192, "actual_file_bytes": (root / "stdout").stat().st_size,
            "reported_bytes": run.stdout_bytes, "log_complete": run.log_complete,
            "partial_reason": run.log_partial_reason, "exit_code": run.exit_code,
        }


async def main():
    signals = {}
    with tempfile.TemporaryDirectory(prefix="rh2-review-signals-") as directory:
        for name in ("SIGHUP", "SIGINT", "SIGTERM", "SIGKILL"):
            root = Path(directory) / name
            run = await collect_script(f"import os,signal; os.kill(os.getpid(), signal.{name})", root)
            signals[name] = {
                "exit_code": run.exit_code, "client_exit_code": run.client_exit_code,
                "client_exit_kind": run.client_exit_kind, "log_complete": run.log_complete,
            }
        timeout = await collect_script("import time; print('prefix'); time.sleep(10)", Path(directory) / "timeout", deadline=0.15)
    cases = [
        await formal_case("normal_zero", 0),
        await formal_case("container_130", 130),
        await formal_case("host_SIGINT_current", signals["SIGINT"]["exit_code"]),
        await formal_case("host_SIGTERM_cap_current", signals["SIGTERM"]["exit_code"], cap=True),
        await formal_case("typed_loss_control", -2, typed=True),
        await formal_case("typed_loss_cap_control", -15, cap=True, typed=True),
        await formal_case("normal_audit_control", 0, log_facts=True),
        await formal_case("typed_loss_audit", 125, typed=True, log_facts=True),
    ]
    child = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-B", str(Path(__file__).resolve()), "--short-write-child"],
        capture_output=True, text=True, timeout=10, check=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    result = {
        "host_signals": signals, "formal_chain": cases, "cancelled_launch": await cancelled_launch(),
        "outer_deadline_launch": await cancelled_launch(outer_deadline=True),
        "owner_timeout_control": {"exit_code": timeout.exit_code, "client_exit_kind": timeout.client_exit_kind,
                                  "partial_reason": timeout.log_partial_reason},
        "short_write": json.loads(child.stdout),
    }
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    Path(__file__).with_suffix(".json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    if "--short-write-child" in sys.argv:
        print(json.dumps(asyncio.run(short_write_child())))
    else:
        asyncio.run(main())
