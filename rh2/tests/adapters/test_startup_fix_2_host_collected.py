"""基座探针修复 #2（2026-09-23）：harness 轨迹文件对 agent 可读 → 改为宿主收集。

修复前 vendored `run_agent` 把 CC 的 stream-json 写进 `{workdir}/.harness/trajectory.jsonl`（agent 属主可读，
`git status` 可见），退出码写在 agent 可写的 `/tmp/.run.done`。现在 `launch_claude_code` 用宿主 `docker exec -u agent`
直接收 CC 的 stdout / stderr 到宿主文件；退出码来自 docker CLI；容器内没有 launcher / done 标记 / `.harness`。
本文件钉住收集器的收口与失败分类（Codex SR2）、启动函数的接线与 typed 码、audit 落盘（SR4）。
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import textwrap
import time
import uuid

import pytest

from repoharness2.adapters.slime import bringup  # noqa: E402
from repoharness2.adapters.slime import docker_sandbox as ds  # noqa: E402
from repoharness2.adapters.slime.generate import (  # noqa: E402
    HARNESS_EXIT_TIME_BUDGET_EXCEEDED,
    HARNESS_LAUNCH_FACTS,
    SlimeBindingError,
)
from repoharness2.adapters.slime.outcome_producer import FAILURE_CODE_TERMINATION_MAP  # noqa: E402

from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain  # noqa: E402


def _py(script: str) -> list[str]:
    return [sys.executable, "-u", "-c", textwrap.dedent(script)]


# ---------------------------------------------------------------------------
# 收集器（真实子进程；docker 由本地进程替身）
# ---------------------------------------------------------------------------


async def test_collector_streams_both_channels_to_host_files_and_reports_complete(tmp_path):
    argv = _py('''
        import sys
        for i in range(2000):
            sys.stdout.write('{"type":"x","i":%d}\\n' % i)
        sys.stderr.write("warn\\n")
        sys.exit(0)
    ''')
    run = await ds.run_host_collected(
        argv, stdout_path=tmp_path / "h" / "trajectory.jsonl", stderr_path=tmp_path / "h" / "stderr.log", deadline_seconds=30,
    )
    lines = (tmp_path / "h" / "trajectory.jsonl").read_text().splitlines()
    assert run.exit_code == 0 and run.client_exit_kind == "container_process_exit" and run.log_complete
    assert len(lines) == 2000 and json.loads(lines[-1])["i"] == 1999 and run.stdout_bytes == sum(len(ln) + 1 for ln in lines)
    assert (tmp_path / "h" / "stderr.log").read_text() == "warn\n" and run.stderr_bytes == 5
    assert run.log_partial_reason is None and run.seconds >= 0


async def test_collector_nonzero_exit_is_the_container_process_code(tmp_path):
    run = await ds.run_host_collected(
        _py("import sys; print('partial'); sys.stderr.write('Traceback...\\nValueError: x\\n'); sys.exit(3)"),
        stdout_path=tmp_path / "t.jsonl", stderr_path=tmp_path / "e.log", deadline_seconds=30,
    )
    assert run.exit_code == 3 and run.client_exit_code == 3 and run.client_exit_kind == "container_process_exit"
    assert run.log_complete and "ValueError" in run.stderr_tail


async def test_collector_time_budget_kills_client_and_keeps_partial_log(tmp_path):
    marker = f"RH2TB{uuid.uuid4().hex[:8]}"
    argv = _py(f'''
        import time
        print("started", flush=True)
        time.sleep(30)  # {marker}
    ''')
    started = time.monotonic()
    run = await ds.run_host_collected(
        argv, stdout_path=tmp_path / "t.jsonl", stderr_path=tmp_path / "e.log", deadline_seconds=0.5, time_budget_exit_code=-1,
    )
    assert run.exit_code == -1 and run.client_exit_kind == "time_budget" and not run.log_complete
    assert run.log_partial_reason == "time_budget" and (tmp_path / "t.jsonl").read_text() == "started\n"
    assert time.monotonic() - started < 10
    assert subprocess.run(["pgrep", "-f", marker], capture_output=True).returncode == 1  # 宿主客户端已被杀


async def test_collector_outer_cancellation_kills_client_and_propagates(tmp_path):
    marker = f"RH2CX{uuid.uuid4().hex[:8]}"
    argv = _py(f"import time; print('x', flush=True); time.sleep(30)  # {marker}")
    task = asyncio.create_task(ds.run_host_collected(
        argv, stdout_path=tmp_path / "t.jsonl", stderr_path=tmp_path / "e.log", deadline_seconds=60,
    ))
    await asyncio.sleep(0.5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (tmp_path / "t.jsonl").read_text() == "x\n"  # 已收到的部分保留
    assert subprocess.run(["pgrep", "-f", marker], capture_output=True).returncode == 1


async def test_collector_log_write_failure_keeps_exit_fact_and_marks_partial(tmp_path, monkeypatch):
    real_open = ds._open_log

    def failing_open(path):
        if path.name == "trajectory.jsonl":
            raise OSError(28, "No space left on device")
        return real_open(path)

    monkeypatch.setattr(ds, "_open_log", failing_open)
    run = await ds.run_host_collected(
        _py("import sys; print('data'); sys.stderr.write('e\\n'); sys.exit(0)"),
        stdout_path=tmp_path / "trajectory.jsonl", stderr_path=tmp_path / "stderr.log", deadline_seconds=30,
    )
    # ① 类：只是诊断文件写失败——退出码仍可信、管道排空、stderr 照常；标 partial 与原因
    assert run.exit_code == 0 and run.client_exit_kind == "container_process_exit"
    assert run.log_complete is False and run.log_partial_reason.startswith("write_error:stdout:open")
    assert (tmp_path / "stderr.log").read_text() == "e\n" and not (tmp_path / "trajectory.jsonl").exists()


@pytest.mark.parametrize(
    ("rc", "tail", "kind"),
    [
        (0, "", "container_process_exit"),
        (1, "Traceback (most recent call last):\nValueError: x", "container_process_exit"),
        (137, "", "container_process_exit"),  # 容器内进程被 SIGKILL：仍是进程退出事实
        (125, "", "docker_cli_error"),
        (126, "", "docker_cli_error"),
        (1, "Error response from daemon: No such container: rollout-x", "docker_cli_error"),
        (1, 'error during connect: Get "http://x": EOF', "docker_cli_error"),
        (1, "some app log\nCannot connect to the Docker daemon at unix:///var/run/docker.sock", "docker_cli_error"),
    ],
)
def test_classify_client_exit(rc, tail, kind):
    assert ds.classify_client_exit(rc, tail) == kind


def test_host_exec_argv_puts_home_and_workdir_before_bash_starts():
    argv = ds.host_exec_argv(
        container_name="c1", user="agent", workdir="/testbed",
        env={"HOME": "/home/agent", "BASH_ENV": "/rh2/bash_env"}, cmd="exec /usr/local/bin/claude -p x",
    )
    assert argv == ["docker", "exec", "-u", "agent", "-w", "/testbed", "-e", "HOME=/home/agent", "-e", "BASH_ENV=/rh2/bash_env",
                    "c1", "bash", "-c", "exec /usr/local/bin/claude -p x"]


# ---------------------------------------------------------------------------
# 启动函数：接线、事实、typed 码
# ---------------------------------------------------------------------------


class _Sandbox:
    container_name = "rollout-fake"

    def __init__(self):
        self.execs: list[str] = []

    async def exec(self, cmd, *, user="root", env=None, timeout=120, check=False, idempotent=True):
        self.execs.append(cmd)
        return 0, "", ""

    async def write_file(self, path, content, *, user="root"):
        self.execs.append(f"write:{path}")


def _patch_bootstrap(monkeypatch):
    from slime.agent import sandbox as slime_sandbox
    from slime.agent.harness import ClaudeCodeHarness

    async def fake_ensure(sb, workdir):
        return None

    async def fake_write_config(self, sb, ctx):
        return None

    monkeypatch.setattr(slime_sandbox, "ensure_agent_user", fake_ensure)
    monkeypatch.setattr(ClaudeCodeHarness, "write_config", fake_write_config)


def _fake_collect(result_kind: str, exit_code: int, seen: dict):
    async def fake(argv, *, stdout_path, stderr_path, deadline_seconds, time_budget_exit_code=-1, chunk_size=65536):
        seen.update({"argv": list(argv), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "deadline": deadline_seconds})
        return ds.HostCollectedRun(
            exit_code=exit_code, client_exit_code=125 if result_kind == "docker_cli_error" else exit_code,
            client_exit_kind=result_kind, stdout_path=str(stdout_path), stderr_path=str(stderr_path),
            stdout_bytes=42, stderr_bytes=0, log_complete=result_kind == "container_process_exit",
            log_partial_reason=None if result_kind == "container_process_exit" else result_kind,
            stderr_tail="Error response from daemon: x" if result_kind == "docker_cli_error" else "", seconds=0.2,
        )
    return fake


async def test_launch_claude_code_collects_on_host_and_leaves_no_in_container_launcher(monkeypatch, tmp_path):
    _patch_bootstrap(monkeypatch)
    seen: dict = {}
    monkeypatch.setattr(ds, "run_host_collected", _fake_collect("container_process_exit", 0, seen))
    sb = _Sandbox()
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        code = await bringup.launch_claude_code(
            sb, workdir="/testbed", session_id="tok", adapter_url="http://relay:18001", prompt="fix it", time_budget_sec=120,
            env_injections={"BASH_ENV": "/rh2/bash_env", "HOME": "/home/agent"}, harness_log_dir=str(tmp_path / "harness"),
        )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert code == 0
    argv = seen["argv"]
    assert argv[:6] == ["docker", "exec", "-u", "agent", "-w", "/testbed"] and "-e" in argv
    assert "BASH_ENV=/rh2/bash_env" in argv and "HOME=/home/agent" in argv and "ANTHROPIC_AUTH_TOKEN=tok" in argv
    assert argv[-2] == "-c" and argv[-1].startswith("exec /usr/local/bin/claude -p 'fix it' --permission-mode bypassPermissions")
    assert seen["stdout_path"] == str(tmp_path / "harness" / "trajectory.jsonl") and seen["deadline"] == 120.0
    assert (tmp_path / "harness").stat().st_mode & 0o777 == 0o700
    # 容器内不再有 launcher / done 标记 / .harness（bootstrap 已替身，其余 exec 一次都没有）
    assert not any(".harness" in e or "/tmp/.run" in e for e in sb.execs) and sb.execs == []
    assert facts["harness_log"]["stdout_bytes"] == 42 and facts["harness_log"]["log_complete"] is True


async def test_launch_claude_code_time_budget_and_connection_lost(monkeypatch, tmp_path):
    _patch_bootstrap(monkeypatch)
    monkeypatch.setattr(ds, "run_host_collected", _fake_collect("time_budget", -1, {}))
    code = await bringup.launch_claude_code(
        _Sandbox(), workdir="/testbed", session_id="tok", adapter_url="http://relay:1", prompt="p", time_budget_sec=5,
        env_injections={}, harness_log_dir=str(tmp_path / "h1"),
    )
    assert code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED == -1  # 与旧 exec_and_wait 同码，编排按 hard wall 收口
    monkeypatch.setattr(ds, "run_host_collected", _fake_collect("docker_cli_error", 125, {}))
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        with pytest.raises(SlimeBindingError, match="harness_exec_connection_lost"):
            await bringup.launch_claude_code(
                _Sandbox(), workdir="/testbed", session_id="tok", adapter_url="http://relay:1", prompt="p", time_budget_sec=5,
                env_injections={}, harness_log_dir=str(tmp_path / "h2"),
            )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert facts["harness_log"]["client_exit_kind"] == "docker_cli_error"  # 事实先落，再抛
    assert FAILURE_CODE_TERMINATION_MAP["harness_exec_connection_lost"] == ("harness_crash", "harness_crash")


async def test_launch_claude_code_without_log_dir_still_collects_to_a_host_temp_dir(monkeypatch):
    _patch_bootstrap(monkeypatch)
    seen: dict = {}
    monkeypatch.setattr(ds, "run_host_collected", _fake_collect("container_process_exit", 0, seen))
    await bringup.launch_claude_code(
        _Sandbox(), workdir="/testbed", session_id="tok", adapter_url="http://relay:1", prompt="p", time_budget_sec=5, env_injections={},
    )
    assert "rh2-harness-" in seen["stdout_path"] and seen["stdout_path"].endswith("trajectory.jsonl")


# ---------------------------------------------------------------------------
# 编排与落盘
# ---------------------------------------------------------------------------


async def test_execution_audit_record_persists_harness_log_block(tmp_path):
    chain = build_dense_chain()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.harness_log is None  # 替身驱动没有收集事实
    audit.harness_log = {"stdout_path": "/x/harness/trajectory.jsonl", "log_complete": True, "client_exit_kind": "container_process_exit"}
    bringup.write_execution_audit_record(None, audit, tmp_path / "audit.jsonl")
    record = json.loads((tmp_path / "audit.jsonl").read_text().splitlines()[-1])
    assert record["harness_log"]["stdout_path"] == "/x/harness/trajectory.jsonl" and record["activation_check"] is None


async def test_orchestrator_copies_collector_facts_into_audit_and_artifact_list(tmp_path):
    """驱动经 HARNESS_LAUNCH_FACTS 交出的宿主收集事实 → audit.harness_log；两份宿主文件进 artifact_paths。"""
    from pathlib import Path

    chain = build_dense_chain()
    inner = chain.orchestrator._harness_driver

    class Driver:
        name = "mock_harness"

        async def run(self, sandbox, **kwargs):
            facts = HARNESS_LAUNCH_FACTS.get()
            facts["harness_log"] = {"stdout_path": str(tmp_path / "h" / "trajectory.jsonl"), "stderr_path": str(tmp_path / "h" / "stderr.log"),
                                    "log_complete": True, "client_exit_kind": "container_process_exit"}
            return await inner.run(sandbox, **kwargs)

    chain.orchestrator._harness_driver = Driver()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.harness_log["client_exit_kind"] == "container_process_exit" and audit.harness_exit_code == 0
    assert {Path(tmp_path / "h" / "trajectory.jsonl"), Path(tmp_path / "h" / "stderr.log")} <= set(audit.artifact_paths)


def test_vendored_run_agent_is_no_longer_on_the_claude_code_path():
    import inspect

    src = inspect.getsource(bringup.launch_claude_code)
    assert "run_host_collected" in src and "run_agent(" not in src


async def test_typed_connection_lost_survives_the_real_driver_and_time_budget_returns_minus_one(monkeypatch):
    """经真实 `ClaudeCodeDriver.run`（引导用 fast exec 替身、只替换宿主收集器）：② 类失败保持 typed 码，不被
    `except SandboxExecError` 包成 harness_bootstrap_failed；时间预算路径返回 -1 交编排按 hard wall 收口。"""
    from repoharness2.adapters.slime.bringup import ClaudeCodeDriver

    async def install(self, sb, **kwargs):
        return None

    async def fast_run(*args, input_bytes=None, timeout=None):
        return 0, "", ""

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(ds, "_run", fast_run)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    sandbox = type("S", (), {"container_name": "c"})()

    monkeypatch.setattr(ds, "run_host_collected", _fake_collect("docker_cli_error", 125, {}))
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        with pytest.raises(SlimeBindingError, match=r"^\[harness_exec_connection_lost\]"):
            await ClaudeCodeDriver().run(
                sandbox, workdir="/testbed", session_id="tok", adapter_url="http://relay:1", time_budget_sec=100, prompt="p",
                env_injections={"BASH_ENV": "/rh2/bash_env"},
            )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert facts["launch_attempted"] is True and facts["harness_log"]["client_exit_kind"] == "docker_cli_error"

    monkeypatch.setattr(ds, "run_host_collected", _fake_collect("time_budget", -1, {}))
    code = await ClaudeCodeDriver().run(
        sandbox, workdir="/testbed", session_id="tok", adapter_url="http://relay:1", time_budget_sec=100, prompt="p",
    )
    assert code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED
