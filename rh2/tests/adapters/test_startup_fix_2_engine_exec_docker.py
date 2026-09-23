"""基座探针修复 #2 / Codex IR1：Engine API exec 收集器对**真实 daemon** 的对照（@pytest.mark.docker，daemon 或
`python:3.12-slim` 不在本机即 skip；不拉镜像）。

钉住的事实（2026-09-24，本机 Docker 29.4.1 与验证机 29.8.1 原型一致）：
- 退出码只来自同一 exec 的 inspect：自然退出 0 / 3、`kill -INT $$` 的 130、容器被 kill 时的 137；
- 300 KB 输出逐帧落盘、字节数与文件大小一致；
- 期限到点：关本次连接、返回预算码、inspect 事实 Running=true，容器内进程**仍在**（归既有屏障，不是收集器的事）；
- 外层取消：CancelledError 原样传播、事实交出、已收部分保留；
- exec create 的 User / WorkingDir / Env 在容器内生效。
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path

import pytest

from repoharness2.adapters.slime import docker_sandbox as ds

IMAGE = os.environ.get("RH2_EXEC_TEST_IMAGE", "python:3.12-slim")  # 验证机上可指到已在场的 SWE-Gym 镜像


def _sh(*args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)


DOCKER_AVAILABLE = _sh("docker", "info", timeout=30).returncode == 0
IMAGE_PRESENT = DOCKER_AVAILABLE and _sh("docker", "image", "inspect", IMAGE, timeout=30).returncode == 0

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason="本机 docker daemon 不可用"),
    pytest.mark.skipif(not IMAGE_PRESENT, reason=f"本机没有 {IMAGE}（测试不拉镜像）"),
]


@pytest.fixture(scope="module")
def container():
    name = f"rh2-exec-test-{uuid.uuid4().hex[:8]}"
    run = _sh("docker", "run", "-d", "--init", "--name", name, IMAGE, "sleep", "600")
    assert run.returncode == 0, run.stderr
    try:
        yield name
    finally:
        _sh("docker", "rm", "-f", name)


def _procs(container: str) -> str:
    """容器内进程的 cmdline 列表（slim 镜像没有 ps）。"""
    return _sh("docker", "exec", container, "bash", "-c",
               "for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null; echo; done").stdout


def _kill_matching(container: str, needle: str) -> None:
    _sh("docker", "exec", container, "bash", "-c",
        f"for p in /proc/[0-9]*; do tr '\\0' ' ' < $p/cmdline 2>/dev/null | grep -q '{needle}' && kill -9 ${{p#/proc/}}; done; true")


def _collect(container: str, tmp_path: Path, cmd: str, **kw):
    kw.setdefault("deadline_seconds", 30)
    kw.setdefault("user", "root")
    kw.setdefault("env", {"RH2_PROBE": "1", "HOME": "/root"})
    kw.setdefault("workdir", "/tmp")
    return ds.run_exec_collected(container_name=container, cmd=cmd, stdout_path=tmp_path / "out", stderr_path=tmp_path / "err", **kw)


async def test_exit_codes_come_from_the_inspected_exec(container, tmp_path):
    run = await _collect(container, tmp_path, "echo out; echo err >&2; exit 3")
    assert run.exec_state == "exited" and run.exit_code == 3 and run.log_complete and run.inspect["Running"] is False
    assert (tmp_path / "out").read_bytes() == b"out\n" and (tmp_path / "err").read_bytes() == b"err\n"
    assert run.stdout_bytes == 4 and run.stderr_bytes == 4 and run.stderr_tail == "err\n"
    run = await _collect(container, tmp_path / "b", "kill -INT $$")
    assert run.exec_state == "exited" and run.exit_code == 130
    run = await _collect(container, tmp_path / "c", "true")
    assert run.exec_state == "exited" and run.exit_code == 0 and run.log_complete


async def test_large_output_is_streamed_completely(container, tmp_path):
    run = await _collect(container, tmp_path, "head -c 300000 /dev/zero | tr '\\0' x; echo; echo e >&2")
    assert run.exec_state == "exited" and run.exit_code == 0 and run.log_complete
    assert run.stdout_bytes == 300001 == (tmp_path / "out").stat().st_size and run.stderr_bytes == 2


async def test_user_workdir_and_env_from_exec_create_take_effect(container, tmp_path):
    run = await _collect(container, tmp_path, "echo UID=$(id -u) PWD=$PWD HOME=$HOME X=$RH2_PROBE",
                         user="nobody", workdir="/usr", env={"HOME": "/nonexistent", "RH2_PROBE": "42"})
    assert run.exit_code == 0 and (tmp_path / "out").read_text().strip() == "UID=65534 PWD=/usr HOME=/nonexistent X=42"


async def test_time_budget_returns_budget_code_and_leaves_the_process_to_the_barrier(container, tmp_path):
    needle = f"sleep 37{uuid.uuid4().hex[:4]}"  # 唯一化：`sleep 37abcd` 会立刻出错——用 bash 变量保持 sleep 参数合法
    tag = needle.split()[1]
    progress: dict = {}
    run = await _collect(container, tmp_path, f"echo started; RH2_TAG={tag} exec sleep 37", deadline_seconds=1.5,
                         time_budget_exit_code=-1, progress=progress)
    assert run.exec_state == "time_budget" and run.exit_code == -1 and run.log_partial_reason == "time_budget"
    assert run.inspect["Running"] is True and (tmp_path / "out").read_bytes() == b"started\n"
    assert progress["exec_state"] == "time_budget" and progress["stdout_bytes"] == 8
    try:
        assert "sleep 37" in _procs(container)  # 收集器不终止容器内进程
    finally:
        _kill_matching(container, "sleep 37")
    await asyncio.sleep(0.5)
    st, _h, payload = await ds.engine_request("GET", f"{ds._ENGINE_API}/exec/{run.exec_id}/json")
    assert st == 200 and b'"Running":false' in payload.replace(b" ", b"")  # 屏障杀掉后 daemon 记下终态


async def test_outer_cancellation_propagates_and_keeps_the_partial_log(container, tmp_path):
    progress: dict = {}
    task = asyncio.create_task(_collect(container, tmp_path, "echo partial; exec sleep 38", deadline_seconds=30, progress=progress))
    await asyncio.sleep(1.0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    try:
        assert progress["exec_state"] == "cancelled" and progress["log_partial_reason"] == "cancelled"
        assert progress["stdout_bytes"] == 8 and (tmp_path / "out").read_bytes() == b"partial\n"
    finally:
        _kill_matching(container, "sleep 38")


async def test_container_killed_mid_exec_reports_the_signal_exit_code(tmp_path):
    name = f"rh2-exec-test-kill-{uuid.uuid4().hex[:8]}"
    assert _sh("docker", "run", "-d", "--init", "--name", name, IMAGE, "sleep", "600").returncode == 0
    try:
        async def killer():
            await asyncio.sleep(1.0)
            _sh("docker", "kill", "--signal", "KILL", name)

        k = asyncio.create_task(killer())
        run = await _collect(name, tmp_path, "echo a; exec sleep 40", deadline_seconds=30)
        await k
        assert run.exec_state == "exited" and run.exit_code == 137 and run.log_partial_reason is None
        assert (tmp_path / "out").read_bytes() == b"a\n"
    finally:
        _sh("docker", "rm", "-f", name)


async def test_oci_start_failure_is_never_started_not_an_exit(container, tmp_path):
    """对抗验证 D6：工作目录不存在 → daemon 合成 126/127、Pid=0、错误文本进 stdout；不是 CC 的退出。"""
    run = await _collect(container, tmp_path, "true", workdir="/no/such/dir")
    assert run.exec_state == "exec_never_started" and run.inspect["Pid"] == 0 and run.exit_code in (126, 127)
    assert run.log_complete is False and "no/such/dir" in run.stdout_tail


async def test_missing_container_is_an_engine_api_error(tmp_path):
    with pytest.raises(ds.EngineApiError, match="exec_create"):
        await _collect(f"rh2-no-such-{uuid.uuid4().hex[:6]}", tmp_path, "true")
