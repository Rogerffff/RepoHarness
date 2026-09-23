"""基座探针修复 #2（2026-09-23；Codex 实施复核 IR1–IR3 修订 2026-09-24）：harness 输出的宿主收集。

修复前 vendored `run_agent` 把 CC 的 stream-json 写进 `{workdir}/.harness/trajectory.jsonl`（agent 属主可读，
`git status` 可见），退出码写在 agent 可写的 `/tmp/.run.done`。首版用宿主 `docker exec` CLI 收集，把 CLI 返回码当作
容器内进程的退出码——Codex IR1 用真实 Docker 证明客户端被 SIGINT/SIGTERM 时 CLI 返回 0 而 exec 仍在跑。现在走
Engine API：exec create（拿 exec ID）→ start（hijack 帧流写宿主文件）→ 同一 exec 的 inspect 才是可信终态。

本文件用一个**假 daemon**（unix socket 上的最小 HTTP）钉住收集器的终态判定、失败分类、取消 / 期限收口、
事实交出（IR2）、短写（IR3），以及启动函数、真实 driver、编排与落盘的接线。真实 daemon 的对照见
`test_startup_fix_2_engine_exec_docker.py`。
"""

from __future__ import annotations

import asyncio
import errno
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from repoharness2.adapters.slime import bringup
from repoharness2.adapters.slime import docker_sandbox as ds
from repoharness2.adapters.slime.generate import (
    HARNESS_EXIT_TIME_BUDGET_EXCEEDED,
    HARNESS_LAUNCH_FACTS,
    SlimeBindingError,
)
from repoharness2.adapters.slime.outcome_producer import FAILURE_CODE_TERMINATION_MAP

from test_budget_deadline import BUDGET, _ticking_clock
from test_f2_2_capability import _fa_cfg, _stamp_fa_identity
from test_slime_generate import SAMPLING_PARAMS, FakeFinalizationStore, _Args, build_dense_chain
from test_w1b_termination_facts_producer import _formal_chain, _steps


# ---------------------------------------------------------------------------
# 假 daemon：unix socket 上的最小 Engine API（exec create / start / inspect）
# ---------------------------------------------------------------------------


def frame(stream_type: int, payload: bytes) -> bytes:
    return bytes([stream_type, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload


class FakeEngine:
    """剧本式假 daemon。`frames`: [(type, bytes, delay_s)]；`end`: "close" | "hold"（等客户端断开）；
    `inspect`: 逐次应答的状态列表（用尽后驻留最后一个；元素 None = 404）；`mode`: "upgrade" | "chunked200"。"""

    def __init__(self, tmp_path: Path, *, frames=(), end="close", inspect=({"Running": False, "ExitCode": 0, "Pid": 7},),
                 mode="upgrade", create_status=201, start_behavior="stream", inspect_delay=0.0, create_truncated=False):
        self.start_behavior = start_behavior  # stream | hang（永不应答）| reset（收到请求即断开）
        self.inspect_delay = inspect_delay
        self.create_truncated = create_truncated  # create 回一个被截断的 chunked 响应体
        # AF_UNIX 路径上限约 104 字节：pytest 的 tmp_path 在 macOS 上太长，socket 放短目录（tmp_path 只放日志）
        self._sock_dir = tempfile.mkdtemp(prefix="rh2eng", dir="/tmp")
        self.socket_path = str(Path(self._sock_dir) / "e.sock")
        self.frames = list(frames)
        self.end = end
        self.inspect = list(inspect)
        self.mode = mode
        self.create_status = create_status
        self.create_bodies: list[dict] = []
        self.inspect_calls = 0
        self.client_closed = asyncio.Event()
        self._server = None

    async def __aenter__(self):
        self._server = await asyncio.start_unix_server(self._handle, path=self.socket_path)
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()
        shutil.rmtree(self._sock_dir, ignore_errors=True)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            status_line = await reader.readline()
            method, path, _ = status_line.decode().split(maxsplit=2)
            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                k, _, v = line.decode().partition(":")
                headers[k.strip().lower()] = v.strip()
            body = await reader.readexactly(int(headers.get("content-length", "0")))
            if method == "POST" and path.endswith("/exec") and "/containers/" in path:
                self.create_bodies.append(json.loads(body))
                payload = json.dumps({"Id": "exec-fake-1"}).encode() if self.create_status == 201 else b'{"message":"No such container"}'
                if self.create_truncated:
                    writer.write(b"HTTP/1.1 201 Created\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n5\r\n{\"Id\r\n")
                    await writer.drain()
                    return  # 没有终止 chunk 就关连接
                writer.write(f"HTTP/1.1 {self.create_status} X\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload)
                await writer.drain()
            elif method == "POST" and path.endswith("/start"):
                if self.start_behavior == "hang":
                    await reader.read()  # 永不应答，直到客户端放弃
                    return
                if self.start_behavior == "reset":
                    writer.transport.abort()
                    return
                if self.mode == "upgrade":
                    writer.write(b"HTTP/1.1 101 UPGRADED\r\nContent-Type: application/vnd.docker.multiplexed-stream\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n")
                else:
                    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/vnd.docker.raw-stream\r\nTransfer-Encoding: chunked\r\n\r\n")
                await writer.drain()
                for stream_type, payload, delay in self.frames:
                    if delay:
                        await asyncio.sleep(delay)
                    data = frame(stream_type, payload)
                    if self.mode == "chunked200":  # 一帧拆成两个 chunk：chunk 边界不等于帧边界
                        half = len(data) // 2
                        data = f"{half:x}\r\n".encode() + data[:half] + b"\r\n" + f"{len(data) - half:x}\r\n".encode() + data[half:] + b"\r\n"
                    writer.write(data)
                    await writer.drain()
                if self.end == "close":
                    if self.mode == "chunked200":
                        writer.write(b"0\r\n\r\n")
                        await writer.drain()
                else:
                    try:
                        await reader.read()  # 等客户端断开
                    except (ConnectionError, OSError):
                        pass
                    self.client_closed.set()
            elif method == "GET" and path.endswith("/json"):
                state = self.inspect[min(self.inspect_calls, len(self.inspect) - 1)]
                self.inspect_calls += 1
                if self.inspect_delay:
                    await asyncio.sleep(self.inspect_delay)
                if state is None:
                    payload = b'{"message":"No such exec instance"}'
                    writer.write(f"HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload)
                else:
                    payload = json.dumps({"ID": "exec-fake-1", **state}).encode()
                    writer.write(f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload)
                await writer.drain()
            else:
                writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            pass
        finally:
            writer.close()


def _collect(engine: FakeEngine, tmp_path: Path, **kw):
    kw.setdefault("deadline_seconds", 10)
    kw.setdefault("settle_seconds", 0.6)
    return ds.run_exec_collected(
        container_name="c1", user="agent", workdir="/testbed", env={"HOME": "/home/agent", "BASH_ENV": "/rh2/bash_env"},
        cmd="exec claude", stdout_path=tmp_path / "h" / "trajectory.jsonl", stderr_path=tmp_path / "h" / "stderr.log",
        socket_path=engine.socket_path, **kw,
    )


# ---------------------------------------------------------------------------
# 收集器：终态、分类、收口
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["upgrade", "chunked200"])
async def test_collector_streams_frames_to_host_files_and_trusts_the_inspected_exit_code(tmp_path, mode):
    lines = [(1, ('{"type":"x","i":%d}\n' % i).encode(), 0) for i in range(300)] + [(2, b"warn\n", 0)]
    async with FakeEngine(tmp_path, frames=lines, inspect=({"Running": False, "ExitCode": 3, "Pid": 9},), mode=mode) as eng:
        run = await _collect(eng, tmp_path)
    text = (tmp_path / "h" / "trajectory.jsonl").read_text()
    assert run.exec_state == "exited" and run.exit_code == 3 and run.exec_id == "exec-fake-1"
    assert run.log_complete and run.log_partial_reason is None
    assert text.count("\n") == 300 and json.loads(text.splitlines()[-1])["i"] == 299
    assert run.stdout_bytes == len(text.encode()) == (tmp_path / "h" / "trajectory.jsonl").stat().st_size
    assert (tmp_path / "h" / "stderr.log").read_text() == "warn\n" and run.stderr_bytes == 5 and run.stderr_tail == "warn\n"
    assert run.inspect == {"Running": False, "ExitCode": 3, "Pid": 9}
    body = eng.create_bodies[0]
    assert body["User"] == "agent" and body["WorkingDir"] == "/testbed" and body["Cmd"] == ["bash", "-c", "exec claude"]
    assert sorted(body["Env"]) == ["BASH_ENV=/rh2/bash_env", "HOME=/home/agent"] and body["AttachStdin"] is False and body["Tty"] is False


async def test_collector_waits_for_the_daemon_to_settle_the_terminal_state(tmp_path):
    """流 EOF 后 inspect 可能还短暂 Running=true：有界轮询，拿到 Running=false 才算终态。"""
    seq = ({"Running": True, "ExitCode": None, "Pid": 1}, {"Running": True, "ExitCode": None, "Pid": 1}, {"Running": False, "ExitCode": 5, "Pid": 1})
    async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], inspect=seq) as eng:
        run = await _collect(eng, tmp_path, settle_seconds=3.0)
    assert run.exec_state == "exited" and run.exit_code == 5 and run.log_complete and eng.inspect_calls == 3


async def test_stream_end_while_exec_still_running_is_not_a_completion(tmp_path):
    """IR1：连接结束 ≠ 执行结束。同一 exec 的 inspect 仍 Running → 不给退出码、标 partial，由调用方 typed 收口。"""
    async with FakeEngine(tmp_path, frames=[(1, b"partial\n", 0)], inspect=({"Running": True, "ExitCode": None, "Pid": 1},)) as eng:
        run = await _collect(eng, tmp_path, settle_seconds=0.5)
    assert run.exec_state == "exec_running_after_stream_end" and run.exit_code is None
    assert run.log_complete is False and run.log_partial_reason == "exec_running_after_stream_end"
    assert run.stdout_bytes == 8 and (tmp_path / "h" / "trajectory.jsonl").read_text() == "partial\n"  # 已收部分保留
    assert eng.inspect_calls >= 2  # 轮询到 settle 上限


@pytest.mark.parametrize(
    ("inspect", "state"),
    [
        ((None,), "inspect_failed"),  # 404：exec 记录已不在（daemon 重启等）
        (({"Running": False, "ExitCode": None, "Pid": 1},), "inspect_failed"),  # 终态无退出码
        (({"Running": False, "ExitCode": -1, "Pid": 1},), "inspect_failed"),  # 负码不透传成 RH2 内部码
        (({"Running": False, "ExitCode": True, "Pid": 1},), "inspect_failed"),
        (({"Running": False, "ExitCode": 256, "Pid": 1},), "inspect_failed"),  # 越界（对抗验证 D5）
        (({"Running": False, "ExitCode": 127, "Pid": 0},), "exec_never_started"),  # OCI 启动失败：Pid=0（D6）
    ],
)
async def test_unusable_terminal_state_is_never_turned_into_an_exit_code(tmp_path, inspect, state):
    async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], inspect=inspect) as eng:
        run = await _collect(eng, tmp_path, settle_seconds=0.4)
    assert run.exec_state == state and run.log_complete is False and run.log_partial_reason == state
    assert run.exit_code == (127 if state == "exec_never_started" else None)  # 从未启动保留 daemon 合成码供诊断


async def test_time_budget_closes_the_connection_and_returns_the_budget_code_without_waiting(tmp_path):
    async with FakeEngine(tmp_path, frames=[(1, b"started\n", 0)], end="hold", inspect=({"Running": True, "ExitCode": None, "Pid": 3},)) as eng:
        progress: dict = {}
        run = await _collect(eng, tmp_path, deadline_seconds=0.5, time_budget_exit_code=-1, progress=progress)
        await asyncio.wait_for(eng.client_closed.wait(), 2)  # 本次连接已关；容器内进程归既有屏障
    assert run.exec_state == "time_budget" and run.exit_code == -1 and run.log_partial_reason == "time_budget" and not run.log_complete
    assert run.inspect == {"Running": True, "ExitCode": None, "Pid": 3}  # 只记一次有界事实，不等退出
    assert (tmp_path / "h" / "trajectory.jsonl").read_text() == "started\n" and progress["exec_state"] == "time_budget"
    assert progress["stdout_bytes"] == 8 and progress["stdout_path"].endswith("trajectory.jsonl")


async def test_outer_cancellation_propagates_and_hands_over_the_facts(tmp_path):
    """IR2：取消原样传播，但 progress 里已有路径、实际字节与 partial 原因。"""
    async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0), (1, b"y\n", 0.05)], end="hold") as eng:
        progress: dict = {}
        task = asyncio.create_task(_collect(eng, tmp_path, deadline_seconds=30, progress=progress))
        await asyncio.sleep(0.4)
        assert progress["exec_state"] == "streaming" and progress["stdout_bytes"] == 4  # 进行中的事实实时可见
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(eng.client_closed.wait(), 2)
    assert progress["exec_state"] == "cancelled" and progress["log_partial_reason"] == "cancelled" and progress["log_complete"] is False
    assert progress["stdout_bytes"] == 4 and (tmp_path / "h" / "trajectory.jsonl").read_text() == "x\ny\n"


async def test_connection_reset_mid_stream_is_a_stream_end_not_a_completion(tmp_path):
    """daemon 侧连接被重置（abort）：读取错误按流结束处理、记 stream_error，终态仍由 inspect 决定 → 仍 Running 即 typed。"""

    class ResettingEngine(FakeEngine):
        async def _handle(self, reader, writer):
            status_line = await reader.readline()
            if b"/start" in status_line:
                while (await reader.readline()) not in (b"\r\n", b"\n", b""):
                    pass
                await reader.readexactly(int(json.dumps({"Detach": False, "Tty": False}).encode().__len__()))
                writer.write(b"HTTP/1.1 101 UPGRADED\r\nContent-Type: application/vnd.docker.multiplexed-stream\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n")
                writer.write(frame(1, b"half\n") + b"\x01\x00\x00\x00\x00\x00\x00\x10trunc")  # 一帧完整 + 一帧被截断
                await writer.drain()
                writer.transport.abort()  # RST / 直接断开
                return
            # 其余路由交给父类（需要把已读的状态行还回去：直接重放解析）
            self._pending_status = status_line
            await self._handle_rest(reader, writer, status_line)

        async def _handle_rest(self, reader, writer, status_line):
            method, path, _ = status_line.decode().split(maxsplit=2)
            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                k, _, v = line.decode().partition(":")
                headers[k.strip().lower()] = v.strip()
            body = await reader.readexactly(int(headers.get("content-length", "0")))
            if method == "POST":
                self.create_bodies.append(json.loads(body))
                payload = json.dumps({"Id": "exec-fake-1"}).encode()
                writer.write(f"HTTP/1.1 201 Created\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload)
            else:
                self.inspect_calls += 1
                payload = json.dumps({"ID": "exec-fake-1", "Running": True, "ExitCode": None, "Pid": 1}).encode()
                writer.write(f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload)
            await writer.drain()
            writer.close()

    async with ResettingEngine(tmp_path) as eng:
        run = await _collect(eng, tmp_path, settle_seconds=0.4)
    assert run.exec_state == "exec_running_after_stream_end" and run.exit_code is None
    assert (tmp_path / "h" / "trajectory.jsonl").read_bytes() == b"half\n" and run.stdout_bytes == 5  # 截断帧不落盘
    assert run.log_partial_reason == "exec_running_after_stream_end"


@pytest.mark.parametrize("behavior", ["hang", "reset"])
async def test_exec_start_timeout_or_reset_is_an_engine_api_error(tmp_path, monkeypatch, behavior):
    """对抗验证 D1：起流阶段的超时 / 断连要和 create 阶段一样是 EngineApiError（→ driver 归因 bootstrap 失败），
    不能原样抛 TimeoutError / ConnectionResetError 让编排整 run 停机。"""
    monkeypatch.setattr(ds, "_ENGINE_REQUEST_TIMEOUT", 0.5)
    async with FakeEngine(tmp_path, start_behavior=behavior) as eng:
        progress: dict = {}
        with pytest.raises(ds.EngineApiError, match="/start"):
            await _collect(eng, tmp_path, progress=progress)
    assert progress["exec_state"] == "start_failed" and progress["exec_id"] == "exec-fake-1" and progress["exit_code"] is None


async def test_truncated_chunked_create_response_is_an_engine_api_error(tmp_path):
    async with FakeEngine(tmp_path, create_truncated=True) as eng:
        with pytest.raises(ds.EngineApiError, match="exec_create|IncompleteReadError"):
            await _collect(eng, tmp_path)


async def test_cancel_during_the_post_deadline_inspect_leaves_no_budget_code(tmp_path):
    """对抗验证 D3：期限到点后的那次有界 inspect 里被外层取消 → cancelled 且 exit_code=None（不是 -1）。"""
    async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], end="hold", inspect_delay=3.0) as eng:
        progress: dict = {}
        task = asyncio.create_task(_collect(eng, tmp_path, deadline_seconds=0.3, progress=progress))
        await asyncio.sleep(0.9)  # 期限已过，正在等 inspect
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert progress["exec_state"] == "cancelled" and progress["exit_code"] is None and progress["log_partial_reason"] == "cancelled"


async def test_each_attempt_starts_its_log_files_from_empty(tmp_path):
    """对抗验证 D7：同一目录再跑一次不能追加到上次的日志。"""
    (tmp_path / "h").mkdir()
    (tmp_path / "h" / "trajectory.jsonl").write_bytes(b"OLD ATTEMPT\n" * 100)
    async with FakeEngine(tmp_path, frames=[(1, b"new\n", 0)]) as eng:
        run = await _collect(eng, tmp_path)
    assert (tmp_path / "h" / "trajectory.jsonl").read_bytes() == b"new\n" and run.stdout_bytes == 4 and run.log_complete


async def test_settle_bound_is_read_at_call_time(tmp_path, monkeypatch):
    """对抗验证 D12：打补丁的模块常量要真的生效（默认值不能在定义时绑定）。"""
    import time as _time

    monkeypatch.setattr(ds, "_EXEC_SETTLE_SECONDS", 0.3)
    async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], inspect=({"Running": True, "ExitCode": None, "Pid": 1},)) as eng:
        started = _time.monotonic()
        run = await _collect(eng, tmp_path, settle_seconds=None)
    assert run.exec_state == "exec_running_after_stream_end" and _time.monotonic() - started < 2.0


async def test_exec_create_failure_is_an_engine_api_error_before_anything_ran(tmp_path):
    async with FakeEngine(tmp_path, create_status=404) as eng:
        progress: dict = {}
        with pytest.raises(ds.EngineApiError, match="exec_create"):
            await _collect(eng, tmp_path, progress=progress)
    assert progress["exec_state"] == "start_failed" and progress["exec_id"] is None and progress["exit_code"] is None


async def test_unreachable_socket_is_an_engine_api_error(tmp_path):
    with pytest.raises(ds.EngineApiError, match="containers/c1/exec: FileNotFoundError"):
        await ds.run_exec_collected(
            container_name="c1", user="agent", workdir="/t", env={}, cmd="true", stdout_path=tmp_path / "o", stderr_path=tmp_path / "e",
            deadline_seconds=5, socket_path=f"/tmp/rh2-missing-{os.getpid()}.sock",  # 短路径：两个平台都是 ENOENT
        )


def test_docker_socket_path_prefers_docker_host_unix(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///tmp/x.sock")
    assert ds.docker_socket_path() == "/tmp/x.sock"
    monkeypatch.setenv("DOCKER_HOST", "tcp://1.2.3.4:2375")
    with pytest.raises(ds.EngineApiError):
        ds.docker_socket_path()


# ---------------------------------------------------------------------------
# IR3：短写 / 写失败按实际写入计数，只标 partial
# ---------------------------------------------------------------------------


class _CappedFile:
    """最多接受 cap 字节：先短写，再 0 字节（RLIMIT_FSIZE 忽略 SIGXFSZ 时的形态）。"""

    def __init__(self, cap: int):
        self.cap, self.written, self.closed = cap, bytearray(), False

    def write(self, view):
        room = self.cap - len(self.written)
        take = min(room, len(view))
        self.written.extend(bytes(view[:take]))
        return take

    def close(self):
        self.closed = True


async def test_short_write_is_reported_as_partial_with_actual_bytes_and_exit_code_kept(tmp_path, monkeypatch):
    real_open = ds._open_log
    capped = _CappedFile(4096)

    def open_log(path: Path):
        return capped if path.name == "trajectory.jsonl" else real_open(path)

    monkeypatch.setattr(ds, "_open_log", open_log)
    frames = [(1, b"a" * 8192, 0), (1, b"b" * 100, 0), (2, b"e\n", 0)]
    async with FakeEngine(tmp_path, frames=frames, inspect=({"Running": False, "ExitCode": 0, "Pid": 1},)) as eng:
        run = await _collect(eng, tmp_path)
    assert run.exec_state == "exited" and run.exit_code == 0  # 退出码仍可信
    assert run.stdout_bytes == 4096 == len(capped.written) and capped.closed
    assert run.log_complete is False and run.log_partial_reason.startswith("write_error:stdout:write:")
    assert (tmp_path / "h" / "stderr.log").read_text() == "e\n" and run.stderr_bytes == 2  # 另一路照常


async def test_open_failure_keeps_draining_and_marks_partial(tmp_path, monkeypatch):
    real_open = ds._open_log

    def failing_open(path: Path):
        if path.name == "trajectory.jsonl":
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_open(path)

    monkeypatch.setattr(ds, "_open_log", failing_open)
    async with FakeEngine(tmp_path, frames=[(1, b"data\n", 0), (2, b"e\n", 0)]) as eng:
        run = await _collect(eng, tmp_path)
    assert run.exec_state == "exited" and run.exit_code == 0 and run.stdout_bytes == 0
    assert run.log_complete is False and run.log_partial_reason.startswith("write_error:stdout:open")
    assert not (tmp_path / "h" / "trajectory.jsonl").exists() and (tmp_path / "h" / "stderr.log").read_text() == "e\n"


def test_log_sink_under_a_real_file_size_limit_counts_only_what_landed(tmp_path):
    """真实 OS 限额（RLIMIT_FSIZE=4096，忽略 SIGXFSZ；只限子进程）：8192 B 落 4096 B → 标 partial、计 4096。"""
    script = textwrap.dedent(f"""
        import json, resource, signal, sys
        from pathlib import Path
        sys.path.insert(0, {str(Path(ds.__file__).resolve().parents[3])!r})
        from repoharness2.adapters.slime.docker_sandbox import _LogSink
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))
        sink = _LogSink(Path({str(tmp_path / "limited.log")!r}), "stdout")
        sink.open(); sink.write(b"x" * 8192); sink.write(b"y" * 10); sink.close()
        print(json.dumps({{"bytes": sink.bytes, "error": sink.error}}))
    """)
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-500:]
    facts = json.loads(out.stdout.strip().splitlines()[-1])
    assert facts["bytes"] == 4096 == (tmp_path / "limited.log").stat().st_size
    assert facts["error"] and facts["error"].startswith("stdout:write:")


# ---------------------------------------------------------------------------
# 启动函数：接线、事实交出、typed 码
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
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")


def _launch(sb, tmp_path, **kw):
    kw.setdefault("time_budget_sec", 30)
    kw.setdefault("env_injections", {"BASH_ENV": "/rh2/bash_env", "HOME": "/home/agent"})
    kw.setdefault("harness_log_dir", str(tmp_path / "harness"))
    return bringup.launch_claude_code(sb, workdir="/testbed", session_id="tok", adapter_url="http://relay:18001", prompt="fix it", **kw)


async def test_launch_claude_code_execs_through_the_engine_api_and_leaves_no_in_container_launcher(monkeypatch, tmp_path):
    _patch_bootstrap(monkeypatch)
    sb = _Sandbox()
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        async with FakeEngine(tmp_path, frames=[(1, b'{"type":"result"}\n', 0)]) as eng:
            monkeypatch.setenv("DOCKER_HOST", f"unix://{eng.socket_path}")
            code = await _launch(sb, tmp_path)
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert code == 0
    body = eng.create_bodies[0]
    assert body["User"] == "agent" and body["WorkingDir"] == "/testbed"
    env = dict(e.split("=", 1) for e in body["Env"])
    assert env["BASH_ENV"] == "/rh2/bash_env" and env["HOME"] == "/home/agent" and env["ANTHROPIC_AUTH_TOKEN"] == "tok"
    assert body["Cmd"][:2] == ["bash", "-c"] and body["Cmd"][2].startswith("exec /usr/local/bin/claude -p 'fix it' --permission-mode bypassPermissions")
    assert (tmp_path / "harness").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "harness" / "trajectory.jsonl").read_text() == '{"type":"result"}\n'
    assert sb.execs == []  # 容器内没有 launcher / done 标记 / .harness（bootstrap 已替身，其余一次 exec 都没有）
    assert facts["harness_log"]["exec_state"] == "exited" and facts["harness_log"]["log_complete"] is True


async def test_launch_time_budget_and_typed_connection_loss(monkeypatch, tmp_path):
    _patch_bootstrap(monkeypatch)
    async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], end="hold", inspect=({"Running": True, "ExitCode": None, "Pid": 1},)) as eng:
        monkeypatch.setenv("DOCKER_HOST", f"unix://{eng.socket_path}")
        code = await _launch(_Sandbox(), tmp_path, time_budget_sec=1, harness_log_dir=str(tmp_path / "h1"))
    assert code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED == -1  # 与旧 exec_and_wait 同码，编排按 hard wall 收口

    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        async with FakeEngine(tmp_path / "b", frames=[(1, b"x\n", 0)], inspect=({"Running": True, "ExitCode": None, "Pid": 1},)) as eng:
            (tmp_path / "b").mkdir(exist_ok=True)
            monkeypatch.setenv("DOCKER_HOST", f"unix://{eng.socket_path}")
            monkeypatch.setattr(ds, "_EXEC_SETTLE_SECONDS", 0.4)
            with pytest.raises(SlimeBindingError, match=r"^\[harness_exec_connection_lost\]"):
                await _launch(_Sandbox(), tmp_path, harness_log_dir=str(tmp_path / "h2"))
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    log = facts["harness_log"]
    assert log["exec_state"] == "exec_running_after_stream_end" and log["stdout_bytes"] == 2  # 事实先落，再抛
    assert FAILURE_CODE_TERMINATION_MAP["harness_exec_connection_lost"] == ("harness_crash", "harness_crash")


async def test_launch_cancellation_leaves_facts_behind(monkeypatch, tmp_path):
    _patch_bootstrap(monkeypatch)
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], end="hold") as eng:
            monkeypatch.setenv("DOCKER_HOST", f"unix://{eng.socket_path}")
            task = asyncio.create_task(_launch(_Sandbox(), tmp_path))
            await asyncio.sleep(0.4)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert facts["harness_log"]["exec_state"] == "cancelled" and facts["harness_log"]["stdout_bytes"] == 2


@pytest.mark.parametrize("case", ["create_404", "start_hang", "start_reset", "never_started"])
async def test_spawn_failures_are_bootstrap_failures_through_the_real_driver(monkeypatch, tmp_path, case):
    """spawn 阶段的四种失败（建 exec 被拒 / 起流超时 / 起流断连 / OCI 没起来）经真实 ClaudeCodeDriver.run 都归因
    harness_bootstrap_failed（task-local），不是未分类的整 run 停机（对抗验证 D1 / D6）。"""
    from repoharness2.adapters.slime.bringup import ClaudeCodeDriver

    async def install(self, sb, **kwargs):
        return None

    async def fast_run(*args, input_bytes=None, timeout=None):
        return 0, "", ""

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(ds, "_run", fast_run)
    monkeypatch.setattr(ds, "_ENGINE_REQUEST_TIMEOUT", 0.5)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    kw = {"create_404": {"create_status": 404}, "start_hang": {"start_behavior": "hang"}, "start_reset": {"start_behavior": "reset"},
          "never_started": {"frames": [(1, b"OCI runtime exec failed: chdir to cwd\n", 0)], "inspect": ({"Running": False, "ExitCode": 127, "Pid": 0},)}}[case]
    async with FakeEngine(tmp_path, **kw) as eng:
        monkeypatch.setenv("DOCKER_HOST", f"unix://{eng.socket_path}")
        with pytest.raises(SlimeBindingError, match=r"^\[harness_bootstrap_failed\]") as ei:
            await ClaudeCodeDriver().run(type("S", (), {"container_name": "c"})(), workdir="/testbed", session_id="tok",
                                         adapter_url="http://relay:1", time_budget_sec=100, prompt="p")
    if case == "never_started":
        assert "OCI runtime exec failed" in str(ei.value)  # daemon 的错误文本随归因一起可诊断


async def test_typed_connection_lost_survives_the_real_driver(monkeypatch, tmp_path):
    from repoharness2.adapters.slime.bringup import ClaudeCodeDriver

    async def install(self, sb, **kwargs):
        return None

    async def fast_run(*args, input_bytes=None, timeout=None):
        return 0, "", ""

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(ds, "_run", fast_run)
    monkeypatch.setattr(ds, "_EXEC_SETTLE_SECONDS", 0.4)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        async with FakeEngine(tmp_path, frames=[(1, b"x\n", 0)], inspect=({"Running": True, "ExitCode": None, "Pid": 1},)) as eng:
            monkeypatch.setenv("DOCKER_HOST", f"unix://{eng.socket_path}")
            with pytest.raises(SlimeBindingError, match=r"^\[harness_exec_connection_lost\]"):
                await ClaudeCodeDriver().run(type("S", (), {"container_name": "c"})(), workdir="/testbed", session_id="tok",
                                             adapter_url="http://relay:1", time_budget_sec=100, prompt="p")
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert facts["launch_attempted"] is True and facts["harness_log"]["exec_state"] == "exec_running_after_stream_end"


# ---------------------------------------------------------------------------
# 编排与落盘（IR2）：正常 / typed / 期限取消 都能从 audit 与落盘 JSON 回读
# ---------------------------------------------------------------------------


class _FactsDriver:
    """替身驱动：像真实 launch_claude_code 一样先把 progress 挂到 launch facts，再按剧本结束。"""

    name = "mock_harness"

    def __init__(self, inner, *, outcome: str, log_dir: Path):
        self.inner, self.outcome, self.log_dir = inner, outcome, log_dir

    async def run(self, sandbox, **kwargs):
        facts = HARNESS_LAUNCH_FACTS.get()
        facts["launch_attempted"] = True
        progress = {"exec_id": "e1", "exec_state": "streaming", "stdout_path": str(self.log_dir / "trajectory.jsonl"),
                    "stderr_path": str(self.log_dir / "stderr.log"), "stdout_bytes": 7, "stderr_bytes": 0,
                    "log_complete": False, "log_partial_reason": None}
        facts["harness_log"] = progress
        if self.outcome == "typed":
            progress.update(exec_state="exec_running_after_stream_end", log_partial_reason="exec_running_after_stream_end")
            raise SlimeBindingError("harness_exec_connection_lost", "流结束但 exec 仍在跑")
        if self.outcome == "hang":
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                progress.update(exec_state="cancelled", log_partial_reason="cancelled")
                raise
        progress.update(exec_state="exited", exit_code=0, log_complete=True)
        return await self.inner.run(sandbox, **kwargs)


def _persisted(audit, tmp_path: Path) -> dict:
    bringup.write_execution_audit_record(None, audit, tmp_path / "audit.jsonl")
    return json.loads((tmp_path / "audit.jsonl").read_text().splitlines()[-1])


async def test_normal_path_copies_facts_into_audit_and_artifact_list(tmp_path):
    chain = build_dense_chain()
    chain.orchestrator._harness_driver = _FactsDriver(chain.orchestrator._harness_driver, outcome="normal", log_dir=tmp_path / "h")
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.harness_log["exec_state"] == "exited" and audit.harness_exit_code == 0
    assert {Path(tmp_path / "h" / "trajectory.jsonl"), Path(tmp_path / "h" / "stderr.log")} <= set(audit.artifact_paths)
    record = _persisted(audit, tmp_path)
    assert record["harness_log"]["stdout_path"] == str(tmp_path / "h" / "trajectory.jsonl") and record["harness_log"]["log_complete"] is True


async def test_typed_connection_loss_keeps_partial_log_facts_in_persisted_audit(tmp_path):
    chain = build_dense_chain()
    chain.orchestrator._harness_driver = _FactsDriver(chain.orchestrator._harness_driver, outcome="typed", log_dir=tmp_path / "h")
    (out,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert out.remove_sample is True and any("harness_exec_connection_lost" in f.detail for f in audit.failure_records)
    assert audit.harness_log["exec_state"] == "exec_running_after_stream_end" and audit.harness_log["stdout_bytes"] == 7
    assert Path(tmp_path / "h" / "trajectory.jsonl") in audit.artifact_paths
    record = _persisted(audit, tmp_path)
    assert record["harness_log"]["log_partial_reason"] == "exec_running_after_stream_end"


async def test_outer_deadline_cancellation_keeps_partial_log_facts(tmp_path):
    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    chain.orchestrator._harness_driver = _FactsDriver(chain.orchestrator._harness_driver, outcome="hang", log_dir=tmp_path / "h")
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, BUDGET - 0.1, 5000.0)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.harness_exit_code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED and audit.episode_deadline["hit_by"] == "harness_outer"
    assert audit.harness_log["exec_state"] == "cancelled" and audit.harness_log["stdout_bytes"] == 7
    assert _persisted(audit, tmp_path)["harness_log"]["log_partial_reason"] == "cancelled"


class _AlwaysExhausted:
    """cap 事实替身：不论 sid，收口时快照都说预算已耗尽（typed 故障不得因 cap 豁免）。"""

    def subscribe(self, sid, cb):
        pass

    def unsubscribe(self, sid):
        pass

    def snapshot(self, sid):
        return {"cap": 3, "accepted": 3, "exhausted": True, "refused_count": 1, "refused_at_monotonic": 1.0}


@pytest.mark.parametrize("cap", [False, True])
async def test_formal_chain_never_grades_or_delivers_a_lost_execution(tmp_path, cap):
    chain = _formal_chain(FakeFinalizationStore())
    chain.orchestrator._harness_driver = _FactsDriver(chain.orchestrator._harness_driver, outcome="typed", log_dir=tmp_path / "h")
    if cap:
        budget = _AlwaysExhausted()
        chain.orchestrator._turn_budget_subscribe = budget.subscribe
        chain.orchestrator._turn_budget_unsubscribe = budget.unsubscribe
        chain.orchestrator._turn_budget_snapshot = budget.snapshot
    (out,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert out.status == "aborted" and out.remove_sample is True
    assert audit.outcome_v2["reason_code"] == "harness_exec_connection_lost" and audit.outcome_v2["completion_class"] == "missing"
    assert chain.grading.calls == []  # 未评分
    assert audit.termination["turn_budget"] == (None if not cap else {"cap": 3, "accepted": 3, "exhausted": True, "refused_count": 1, "refused_at_monotonic": 1.0})
    assert "cleanup_completed" in _steps(audit)


def test_harness_log_dir_is_per_execution_and_per_physical_attempt(tmp_path):
    """对抗验证 D7：execution id 跨 retry 恒等，日志目录再按 physical attempt 分开。"""
    from types import SimpleNamespace

    chain = build_dense_chain(artifact_dir=tmp_path)
    orch = chain.orchestrator
    assert orch._harness_log_dir(SimpleNamespace(trajectory_id="miles_g1_m2", physical_attempt_id="pa:7/x")).endswith(
        "miles_g1_m2/harness/pa-7-x")  # _sanitize_for_name 把 : / 换成 -
    assert orch._harness_log_dir(SimpleNamespace(trajectory_id="miles_g1_m2", physical_attempt_id=None)).endswith("miles_g1_m2/harness")


def test_vendored_run_agent_and_cli_client_are_no_longer_on_the_claude_code_path():
    import inspect

    src = inspect.getsource(bringup.launch_claude_code)
    assert "run_exec_collected" in src and "run_agent(" not in src and "create_subprocess_exec" not in src
    assert not hasattr(ds, "run_host_collected") and not hasattr(ds, "classify_client_exit")
    assert os.environ.get("DOCKER_HOST", "").startswith("unix://") or True  # 环境无关
