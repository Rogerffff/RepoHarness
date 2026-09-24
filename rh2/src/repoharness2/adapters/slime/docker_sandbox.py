"""slime `slime.agent.sandbox.Sandbox` 协议的 docker 实现（S1-7a 真实接线）。

设计约束（A5 所有权握手的延续）：本类**不创建也不销毁容器**——rollout 容器的
生命周期归 `RolloutOrchestrator`（Q1 建 / Q7 清理），本类只是把"已存在的
rollout 容器"适配成 slime harness 期望的 Sandbox 形状（exec / write_file /
read_file / 异步上下文管理为 no-op）。这样 slime ClaudeCodeHarness 可以原样
跑在 rh2 物化的容器里，而容器清理责任不发生转移。

接口形状逐一对照 slime/agent/sandbox.py：
- exec(cmd, *, user, env, timeout, check, idempotent) -> (exit_code, stdout, stderr)
  （idempotent 是 E2B 传输层参数，docker exec 天然同步，接受并忽略）
- write_file(path, str|bytes|Path, *, user)：经 `docker exec -i ... cat > path`
  流式写入，随后 chown 给目标用户（E2B files.write 的 user 语义等价物）
- read_file(path, *, user)：失败返回 ""（对照 E2BSandbox.read_file 的吞错行为，
  slime exec_and_wait 靠它读 out_file tail，不能抛）
"""

from __future__ import annotations

import asyncio
import errno
import json
import os
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_DOCKER_BIN = "docker"


class SandboxExecError(RuntimeError):
    """`DockerSandbox` 的一次容器操作（exec check=True / write_file）失败。

    批 A（I05，Codex 批 A 审查 R1）：这是**唯一**能证明"来源 = 容器内命令 / 文件写入的单次
    失败"的类型——harness 驱动只把它转换成 task-local 的 `harness_bootstrap_failed`；其它
    RuntimeError（我方代码不变量、vendored 内部错误）不再被改名，原样上抛给编排层按未归因
    异常 run-halt。仍是 RuntimeError 子类，既有按 RuntimeError 捕获的调用方不受影响。
    """

    def __init__(self, op: str, exit_code: int, detail: str) -> None:
        self.op = op
        self.exit_code = exit_code
        super().__init__(f"{op} failed (exit={exit_code}): {detail}")


async def _run(*args: str, input_bytes: bytes | None = None, timeout: float | None = None):
    proc = await asyncio.create_subprocess_exec(
        _DOCKER_BIN,
        *args,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_bytes), timeout=timeout)
    except (TimeoutError, asyncio.TimeoutError):
        _kill_quietly(proc)
        await proc.wait()
        return 124, "", f"docker exec timeout after {timeout}s"
    except asyncio.CancelledError:
        # 批 B（I03；Codex R2 探针：此前外层取消时 kill/wait 均未调用，docker CLI 子进程
        # 孤儿化）。episode 期限 / 关停取消到达时先回收本进程的子进程再传播取消。
        # 注意：杀的是宿主侧 CLI，容器内命令不因此停止——容器本身由编排层按名字回收。
        _kill_quietly(proc)
        await proc.wait()
        raise
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def _kill_quietly(proc: asyncio.subprocess.Process) -> None:
    try:
        proc.kill()
    except ProcessLookupError:  # 已退出
        pass


class DockerSandbox:
    """把一个已存在的 docker 容器适配成 slime Sandbox 协议。"""

    def __init__(self, container_name: str) -> None:
        self.container_name = container_name
        self.sandbox_id = container_name

    async def __aenter__(self) -> "DockerSandbox":
        return self  # 容器生命周期归编排层（Q1/Q7），这里不做任何事

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def exec(
        self,
        cmd: str,
        *,
        user: str = "root",
        env: dict[str, str] | None = None,
        timeout: int = 120,
        check: bool = False,
        idempotent: bool = True,  # noqa: ARG002 - E2B 传输层参数，docker 下无意义
    ) -> tuple[int, str, str]:
        args = ["exec", "-u", user]
        for key, value in (env or {}).items():
            args += ["-e", f"{key}={value}"]
        args += [self.container_name, "bash", "-c", cmd]
        code, out, err = await _run(*args, timeout=float(timeout))
        if check and code != 0:
            raise SandboxExecError("docker exec", code, f"{cmd[:120]}\n{err[:400]}")
        return code, out, err

    async def write_file(self, sandbox_path: str, content, *, user: str = "root") -> None:
        if isinstance(content, Path):
            payload = content.read_bytes()
        elif isinstance(content, bytes):
            payload = content
        else:
            payload = str(content).encode()
        quoted = shlex.quote(sandbox_path)
        script = f"mkdir -p $(dirname {quoted}) && cat > {quoted}"
        if user != "root":
            script += f" && chown {shlex.quote(user)}:{shlex.quote(user)} {quoted}"
        code, _out, err = await _run(
            "exec", "-i", self.container_name, "bash", "-c", script, input_bytes=payload, timeout=600.0
        )
        if code != 0:
            raise SandboxExecError("sandbox write_file", code, f"{sandbox_path}: {err[:400]}")

    async def read_file(self, sandbox_path: str, *, user: str = "root") -> str:
        code, out, _err = await _run(
            "exec", "-u", user, self.container_name, "cat", sandbox_path, timeout=120.0
        )
        return out if code == 0 else ""


# ---------------------------------------------------------------------------
# #2（基座探针修复，2026-09-23；IR1 修订 2026-09-24）：harness 输出的宿主收集——Engine API 直连
# ---------------------------------------------------------------------------
#
# 此前 vendored `run_agent` 在容器里以 agent 身份 `setsid` 启动 launcher，把 CC 的 stream-json 重定向到
# `{workdir}/.harness/trajectory.jsonl`（agent 属主、可读；`git status` 里可见），退出码由 launcher 写进
# agent 可写的 `/tmp/.run.done`。B 线探针里模型 grep 到了自己的轨迹文件（当"参考解"反复读）。
#
# 首版（提交 B）用宿主 `docker exec` CLI 子进程收集，把 CLI 返回码当作容器内进程的退出码。Codex 实施复核
# IR1 用真实 Docker 29.4.1 / 29.8.1 证明：宿主 CLI 客户端被 SIGINT / SIGTERM 终止时 CLI 返回 **0** 而容器内
# 进程仍在跑——CLI 返回值不是"本次执行已结束"的事实。现在改为**局部直连 Engine API**（unix socket，裸 HTTP）：
#   exec create（拿到 exec ID）→ exec start（`Upgrade: tcp` hijack，多路复用帧流增量写宿主文件）
#   → 流结束后用**同一 exec ID** inspect：`Running=false` + `ExitCode` 才是可信终态。
# 流结束而 exec 仍在跑（连接丢失）或拿不到终态 → 调用方抛 typed `harness_exec_connection_lost`。
# 退出码只来自 daemon（0..255），没有宿主子进程，也就没有 -1/-2 这类与 RH2 内部码碰撞的负返回值。
# 期限到点：关掉本次连接、返回 time_budget 码；容器内 CC 由既有 execution_scope 屏障与容器清理终止（owner 语义不变）。
#
# 失败分两类（Codex SR2）：① 只是宿主诊断文件写失败（含短写，IR3）——继续排空、退出码仍可信，记 partial；
# ② 执行连接 / 终态失去——typed 收口。取消 / 异常时已知路径、实际写入字节与 partial 原因经 `progress` 交出（IR2）。

_ENGINE_API = "/v1.44"  # Docker 25+ 的 daemon 都接受（29.x min 1.40）
_STDERR_TAIL_BYTES = 4096
_EXEC_SETTLE_SECONDS = 10.0  # 流 EOF 后等 daemon 记下终态的上限（正常情况几十毫秒内）
_EXEC_SETTLE_STEP = 0.2
_TIME_BUDGET_INSPECT_SECONDS = 2.0  # 期限到点只记一次有界 inspect 事实，不等容器退出
_ENGINE_REQUEST_TIMEOUT = 30.0


class EngineApiError(RuntimeError):
    """与 daemon 的一次 Engine API 交互失败（连不上 socket / 非预期状态码 / 响应形状）。"""

    def __init__(self, op: str, detail: str) -> None:
        super().__init__(f"engine api {op}: {detail}")
        self.op = op
        self.detail = detail


_SOCKET_PATH_CACHE: dict[str, str] = {}


def _socket_from_cli_context() -> str | None:
    """与 CLI（建容器、`DockerSandbox.exec` 走的路径）保持同一 daemon：读当前 context 的 docker endpoint。
    CLI 不在 / 出错 / 非 unix endpoint 时返回 None（对抗验证 D9：只看 DOCKER_HOST 会与非默认 context 的 CLI 分家）。"""

    try:
        out = subprocess.run(
            [_DOCKER_BIN, "context", "inspect", "--format", '{{(index .Endpoints "docker").Host}}'],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    host = out.stdout.strip() if out.returncode == 0 else ""
    return host[len("unix://"):] if host.startswith("unix://") else None


def docker_socket_path() -> str:
    """daemon 的 unix socket：`DOCKER_HOST=unix://…` 优先；否则按 CLI 当前 context 的 endpoint（进程内缓存）；
    再退到 /var/run/docker.sock 与 Docker Desktop 的用户 socket。"""

    host = os.environ.get("DOCKER_HOST", "")
    if host.startswith("unix://"):
        return host[len("unix://"):]
    if host:
        raise EngineApiError("socket", f"只支持 unix socket 形式的 DOCKER_HOST，得到 {host!r}")
    key = os.environ.get("DOCKER_CONTEXT", "") + "|" + os.environ.get("DOCKER_CONFIG", "")
    cached = _SOCKET_PATH_CACHE.get(key)
    if cached:
        return cached
    resolved = _socket_from_cli_context()
    if resolved is None:
        resolved = "/var/run/docker.sock"
        for candidate in ("/var/run/docker.sock", os.path.expanduser("~/.docker/run/docker.sock")):
            if os.path.exists(candidate):
                resolved = candidate
                break
    _SOCKET_PATH_CACHE[key] = resolved
    return resolved


async def _read_http_head(reader: asyncio.StreamReader) -> tuple[int, dict[str, str]]:
    status_line = await reader.readline()
    if not status_line:
        raise ConnectionError("daemon 未返回状态行（连接被关闭）")  # 由调用方连同操作名包成 EngineApiError
    parts = status_line.decode(errors="replace").split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError(f"非 HTTP 状态行 {status_line[:80]!r}")
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        key, _, value = line.decode(errors="replace").partition(":")
        headers[key.strip().lower()] = value.strip()
    return int(parts[1]), headers


async def _read_http_body(reader: asyncio.StreamReader, headers: dict[str, str]) -> bytes:
    if "content-length" in headers:
        return await reader.readexactly(int(headers["content-length"]))
    if headers.get("transfer-encoding", "").lower() == "chunked":
        out = bytearray()
        while True:
            size_line = await reader.readline()
            if not size_line:
                raise asyncio.IncompleteReadError(bytes(out), None)  # 终止 chunk 之前就 EOF：响应被截断
            size = int(size_line.split(b";")[0].strip() or b"0", 16)
            if size == 0:
                while (await reader.readline()) not in (b"\r\n", b"\n", b""):  # trailer
                    pass
                return bytes(out)
            out.extend(await reader.readexactly(size))
            await reader.readline()  # chunk 末尾 CRLF
    return await reader.read()


async def engine_request(
    method: str, path: str, body: Any = None, *, socket_path: str | None = None,
    timeout: float | None = None,
) -> tuple[int, dict[str, str], bytes]:
    """一次普通 Engine API 请求（`Connection: close`），返回 (status, headers, payload)。`timeout` 是**整次**请求
    （连接 + 发送 + 读完响应）的上限（对抗验证 D4：分阶段计时会让"2 s"变成最坏 8 s）。"""

    bound = _ENGINE_REQUEST_TIMEOUT if timeout is None else timeout
    sock = socket_path or docker_socket_path()
    op = f"{method} {path}"
    try:
        return await asyncio.wait_for(_engine_request_once(sock, method, path, body), bound)
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise EngineApiError(op, f"timeout after {bound}s") from exc
    except (OSError, asyncio.IncompleteReadError, ValueError) as exc:
        raise EngineApiError(op, f"{type(exc).__name__}: {exc}") from exc


async def _engine_request_once(sock: str, method: str, path: str, body: Any) -> tuple[int, dict[str, str], bytes]:
    data = json.dumps(body).encode() if body is not None else b""
    head = [f"{method} {path} HTTP/1.1", "Host: docker", f"Content-Length: {len(data)}", "Connection: close"]
    if body is not None:
        head.append("Content-Type: application/json")
    reader, writer = await asyncio.open_unix_connection(sock)
    try:
        writer.write(("\r\n".join(head) + "\r\n\r\n").encode() + data)
        await writer.drain()
        status, headers = await _read_http_head(reader)
        payload = await _read_http_body(reader, headers)
        return status, headers, payload
    finally:
        writer.close()


async def engine_hijack(
    method: str, path: str, body: Any, *, socket_path: str | None = None, timeout: float | None = None,
) -> tuple[int, dict[str, str], asyncio.StreamReader, asyncio.StreamWriter]:
    """带 `Upgrade: tcp` 的请求（exec start）：101 后连接就是原始帧流；个别 daemon 不升级而回 200 + chunked，
    帧流在 chunk 体里——两种都交给调用方按 headers 处理。返回的 writer 由调用方关闭。"""

    bound = _ENGINE_REQUEST_TIMEOUT if timeout is None else timeout
    sock = socket_path or docker_socket_path()
    op = f"{method} {path}"
    data = json.dumps(body).encode()
    head = [
        f"{method} {path} HTTP/1.1", "Host: docker", f"Content-Length: {len(data)}", "Content-Type: application/json",
        "Connection: Upgrade", "Upgrade: tcp",
    ]
    writer: asyncio.StreamWriter | None = None

    async def open_and_upgrade() -> tuple[int, dict[str, str], asyncio.StreamReader, asyncio.StreamWriter]:
        nonlocal writer
        reader, writer = await asyncio.open_unix_connection(sock)
        writer.write(("\r\n".join(head) + "\r\n\r\n").encode() + data)
        await writer.drain()
        status, headers = await _read_http_head(reader)
        if status not in (101, 200):
            payload = await _read_http_body(reader, headers)
            raise EngineApiError(op, f"HTTP {status}: {payload[:300]!r}")
        return status, headers, reader, writer

    try:
        return await asyncio.wait_for(open_and_upgrade(), bound)
    except BaseException as exc:
        if writer is not None:
            writer.close()
        # 起流阶段的超时 / 断连 / 畸形响应与 engine_request 同样包成 EngineApiError（对抗验证 D1：原样抛出会被
        # 编排当成未分类程序错误而整 run 停机，而同一故障发生在 create 阶段只作废本条）
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
            raise EngineApiError(op, f"timeout after {bound}s") from exc
        if isinstance(exc, (OSError, asyncio.IncompleteReadError, ValueError)):
            raise EngineApiError(op, f"{type(exc).__name__}: {exc}") from exc
        raise


class _FrameSource:
    """把 hijack 流解成 (stream_type, payload) 帧：8 字节头 = type(1) + pad(3) + 大端长度(4)。
    200 + chunked 时先解 chunk 再解帧。EOF 返回 None。

    只有**帧边界上**的 EOF（raw：缓冲为空时读到 EOF；chunked：读到终止块）才是干净结束；帧头 / payload 中途 EOF、
    chunked 没有终止块、chunk 大小非法、连接层错误都记进 `error`——终态仍由 inspect 决定，但日志不能标完整
    （Codex IR 复核 F2：执行完成事实与日志完整性是两个事实）。"""

    def __init__(self, reader: asyncio.StreamReader, *, chunked: bool) -> None:
        self._reader = reader
        self._chunked = chunked
        self._buf = bytearray()
        self._eof = False
        self.error: str | None = None

    def _end(self, error: str | None) -> bool:
        self._eof = True
        if error and self.error is None:
            self.error = error
        return False

    async def _fill(self, need: int, *, what: str) -> bool:
        try:
            return await self._fill_inner(need, what)
        except asyncio.IncompleteReadError:
            return self._end(f"eof_inside_{what}")
        except OSError as exc:  # ConnectionResetError 等 daemon 侧断连
            return self._end(f"{type(exc).__name__}: {exc}")
        except ValueError as exc:  # 畸形 chunk 大小
            return self._end(f"bad_chunk_size: {exc}")

    async def _fill_inner(self, need: int, what: str) -> bool:
        while len(self._buf) < need:
            if self._eof:
                return False
            if self._chunked:
                size_line = await self._reader.readline()
                if not size_line:
                    return self._end("chunked_eof_without_terminator")
                size = int(size_line.split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    # 终止块：只有恰好落在帧边界（缓冲为空、正等下一帧头）才是干净结束
                    return self._end(None if (what == "frame_header" and not self._buf) else f"eof_inside_{what}")
                self._buf.extend(await self._reader.readexactly(size))
                await self._reader.readline()
            else:
                data = await self._reader.read(65536)
                if not data:
                    return self._end(None if (what == "frame_header" and not self._buf) else f"eof_inside_{what}")
                self._buf.extend(data)
        return True

    async def next_frame(self) -> tuple[int, bytes] | None:
        if not await self._fill(8, what="frame_header"):
            return None
        stream_type, size = self._buf[0], int.from_bytes(self._buf[4:8], "big")
        del self._buf[:8]
        if not await self._fill(size, what="frame_payload"):
            return None  # 帧被截断：已记 error；终态由 inspect 决定
        payload = bytes(self._buf[:size])
        del self._buf[:size]
        return stream_type, payload


class _LogSink:
    """一路输出的宿主文件：无缓冲追加写；按**实际写入**计数（IR3：短写不再被记成完整）。
    写失败 / 短写：留痕、关闭句柄、停止写本文件——退出码仍可信，日志标 partial。"""

    def __init__(self, path: Path, key: str) -> None:
        self.path = path
        self.key = key
        self.bytes = 0
        self.error: str | None = None
        self._fh: Any = None

    def open(self) -> None:
        try:
            self._fh = _open_log(self.path)
        except OSError as exc:
            self.error = f"{self.key}:open:{exc}"

    def write(self, data: bytes) -> None:
        if self._fh is None:
            return
        view = memoryview(data)
        try:
            while len(view):
                written = self._fh.write(view)
                if not written:  # 0 字节：文件大小上限等——按短写收口
                    raise OSError(errno.EFBIG, "short write (0 bytes accepted)")
                self.bytes += written
                view = view[written:]
        except OSError as exc:
            self.error = f"{self.key}:write:{exc}"
            self.close()

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            finally:
                self._fh = None


def _open_log(path: Path):
    """本次尝试的日志从空文件开始（"wb"）：目录按 execution + physical attempt 区分，追加模式会把重派发的两次
    尝试混进同一文件而事实只计本次字节（对抗验证 D7）。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("wb", buffering=0)


@dataclass
class ExecCollectedRun:
    """一次 Engine API exec 收集的执行事实。exit_code 只在 exec_state=exited（daemon 记录的 0..255）
    或 time_budget（调用方约定的预算码）时非 None。"""

    exec_id: str | None
    exit_code: int | None
    exec_state: str  # start_failed | streaming | exited | exec_never_started | time_budget | exec_running_after_stream_end | inspect_failed | stream_error | cancelled
    stdout_path: str
    stderr_path: str
    stdout_bytes: int  # 实际写入宿主文件的字节
    stderr_bytes: int
    log_complete: bool  # exited 且流干净结束（帧边界 EOF）且两路都无写失败
    log_partial_reason: str | None  # time_budget | cancelled | write_error:<...> | stream_error:<...> | <exec_state>
    stderr_tail: str
    seconds: float
    inspect: dict[str, Any] | None = None  # 最后一次 exec inspect 的 Running / ExitCode / Pid
    stream_error: str | None = None  # 流在连接层出错而结束（reset 等）；终态仍以 inspect 为准
    stdout_tail: str = ""  # stdout 末尾（≤ 512 B）：exec 从未启动时 daemon 把 OCI 错误文本写在这里

    def facts(self) -> dict[str, Any]:
        return asdict(self)


async def _inspect_exec(exec_id: str, *, socket_path: str | None, timeout: float) -> dict[str, Any] | None:
    try:
        status, _headers, payload = await engine_request(
            "GET", f"{_ENGINE_API}/exec/{exec_id}/json", socket_path=socket_path, timeout=timeout,
        )
        if status != 200:
            return None
        doc = json.loads(payload)
        return {"Running": doc.get("Running"), "ExitCode": doc.get("ExitCode"), "Pid": doc.get("Pid")}
    except (EngineApiError, ValueError):
        return None


async def _await_exec_terminal(
    exec_id: str, *, socket_path: str | None, settle_seconds: float,
) -> dict[str, Any] | None:
    """流 EOF 之后：轮询同一 exec 的 inspect 直到 Running=false（正常几十毫秒内）；每次 inspect 只给剩余时间，
    整段大约以 settle 为界（经验上限，不是严格总时长）；超过后返回最后一次观测（可能仍 Running=true = 连接丢失）；
    一次都没拿到返回 None。"""

    deadline = time.monotonic() + settle_seconds
    last: dict[str, Any] | None = None
    while True:
        remaining = deadline - time.monotonic()
        state = await _inspect_exec(
            exec_id, socket_path=socket_path, timeout=max(0.05, min(remaining, _ENGINE_REQUEST_TIMEOUT)),
        )
        if state is not None:
            last = state
            if state.get("Running") is False:
                return state
        if time.monotonic() >= deadline:
            return last
        await asyncio.sleep(min(_EXEC_SETTLE_STEP, max(0.0, deadline - time.monotonic())))


async def run_exec_collected(
    *, container_name: str, user: str, workdir: str, env: dict[str, str], cmd: str,
    stdout_path: Path | str, stderr_path: Path | str, deadline_seconds: float,
    time_budget_exit_code: int = -1, progress: dict[str, Any] | None = None, socket_path: str | None = None,
    settle_seconds: float | None = None,
) -> ExecCollectedRun:
    """在容器里以 `user` 身份、`workdir`、`env` 起 `bash -c <cmd>`（Engine API exec），两路输出增量写到宿主
    文件，流结束后用同一 exec 的 inspect 取可信终态。

    - 连接、帧读取、文件句柄都归本次调用；正常结束按 inspect 收口；期限到点关连接返回 time_budget 码；
      外层取消关连接后原样传播（容器内进程归既有 owner，这里不另造停止生命周期）。
    - `progress`（可选）在开始、每帧与收口时同步更新为当前事实：取消 / 异常时调用方仍拿得到路径、
      实际字节与 partial 原因（IR2）。
    - Engine API 建 exec / 起流失败抛 EngineApiError（尚未开始执行）；其它未知异常不包。
    """

    started = time.monotonic()
    settle = _EXEC_SETTLE_SECONDS if settle_seconds is None else settle_seconds  # 调用时取模块常量（可被测试打补丁）
    out_path, err_path = Path(stdout_path), Path(stderr_path)
    run = ExecCollectedRun(
        exec_id=None, exit_code=None, exec_state="start_failed", stdout_path=str(out_path), stderr_path=str(err_path),
        stdout_bytes=0, stderr_bytes=0, log_complete=False, log_partial_reason=None, stderr_tail="", seconds=0.0,
    )
    sinks = {1: _LogSink(out_path, "stdout"), 2: _LogSink(err_path, "stderr")}
    tail = bytearray()
    out_tail = bytearray()

    def publish() -> None:
        run.seconds = round(time.monotonic() - started, 3)
        if progress is not None:
            progress.update(run.facts())

    writer: asyncio.StreamWriter | None = None
    try:
        status, _headers, payload = await engine_request(
            "POST", f"{_ENGINE_API}/containers/{container_name}/exec",
            {
                "AttachStdin": False, "AttachStdout": True, "AttachStderr": True, "Tty": False,
                "User": user, "WorkingDir": workdir, "Env": [f"{k}={v}" for k, v in env.items()],
                "Cmd": ["bash", "-c", cmd],
            },
            socket_path=socket_path,
        )
        if status != 201:
            raise EngineApiError("exec_create", f"HTTP {status}: {payload[:300]!r}")
        try:
            run.exec_id = json.loads(payload)["Id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise EngineApiError("exec_create", f"响应无 Id：{payload[:200]!r}") from exc
        status, headers, reader, writer = await engine_hijack(
            "POST", f"{_ENGINE_API}/exec/{run.exec_id}/start", {"Detach": False, "Tty": False}, socket_path=socket_path,
        )
        for sink in sinks.values():
            sink.open()
        source = _FrameSource(reader, chunked=headers.get("transfer-encoding", "").lower() == "chunked")
        run.exec_state = "streaming"
        publish()

        async def pump() -> None:
            while True:
                frame = await source.next_frame()
                if frame is None:
                    return
                stream_type, data = frame
                if stream_type == 2:
                    tail.extend(data)
                    if len(tail) > _STDERR_TAIL_BYTES:
                        del tail[:-_STDERR_TAIL_BYTES]
                elif stream_type == 1:
                    out_tail.extend(data[-512:])
                    if len(out_tail) > 512:
                        del out_tail[:-512]
                sink = sinks.get(stream_type)
                if sink is not None:
                    sink.write(data)
                    run.stdout_bytes, run.stderr_bytes = sinks[1].bytes, sinks[2].bytes
                    if progress is not None:
                        progress["stdout_bytes"], progress["stderr_bytes"] = run.stdout_bytes, run.stderr_bytes

        time_budget_hit = False
        try:
            await asyncio.wait_for(pump(), timeout=deadline_seconds)
        except (TimeoutError, asyncio.TimeoutError):
            time_budget_hit = True
        writer.close()
        writer = None
        run.stream_error = source.error
        write_errors = [sink.error for sink in sinks.values() if sink.error]
        if time_budget_hit:
            run.exec_state, run.exit_code = "time_budget", time_budget_exit_code
            run.log_complete, run.log_partial_reason = False, "time_budget"
            run.inspect = await _inspect_exec(run.exec_id, socket_path=socket_path, timeout=_TIME_BUDGET_INSPECT_SECONDS)
            return run
        state = await _await_exec_terminal(run.exec_id, socket_path=socket_path, settle_seconds=settle)
        run.inspect = state
        code = state.get("ExitCode") if state else None
        if state is None:
            run.exec_state = "inspect_failed"
        elif state.get("Running") is not False:
            run.exec_state = "exec_running_after_stream_end"
        elif not isinstance(code, int) or isinstance(code, bool) or not (0 <= code <= 255):
            run.exec_state = "inspect_failed"  # 无码 / 负码 / 越界：不透传成退出码（含 RH2 内部 -1/-2）
        elif state.get("Pid") == 0 and code != 0:
            # OCI 启动失败（工作目录不在、bash 不在 PATH…）：daemon 合成 126/127、Pid 保持 0、错误文本进 stdout——
            # 进程从未启动，不是 CC 的退出（对抗验证 D6）
            run.exec_state, run.exit_code = "exec_never_started", int(code)
        else:
            run.exec_state, run.exit_code = "exited", int(code)
        if run.exec_state != "exited":
            run.log_partial_reason = run.exec_state
        else:
            reasons = []
            if run.stream_error:
                reasons.append(f"stream_error:{run.stream_error}")  # 坏流 + 可信终态：退出码保留，日志标 partial（F2）
            if write_errors:
                reasons.append("write_error:" + ";".join(write_errors))
            run.log_partial_reason = ";".join(reasons) or None
        run.log_complete = run.exec_state == "exited" and not write_errors and not run.stream_error
        return run
    except asyncio.CancelledError:
        # 外层取消（hard wall / poison / 关停 / cap 强停）：关本次连接后传播；容器内进程归既有 owner。
        # 期限后的那次 inspect 里被取消也归这里：不留下带预算码的 cancelled（对抗验证 D3）
        run.exec_state, run.exit_code, run.log_complete, run.log_partial_reason = "cancelled", None, False, "cancelled"
        raise
    except EngineApiError:
        raise  # 建 exec / 起流失败：exec_state 仍是 start_failed
    except Exception as exc:  # 未知程序错误：不包、不吞（批 A fail-fast），只把事实记全再传播
        if run.exec_state == "streaming":
            run.exec_state, run.exit_code = "stream_error", None
            run.log_partial_reason = f"stream_error:{type(exc).__name__}"
        raise
    finally:
        if writer is not None:
            writer.close()
        for sink in sinks.values():
            sink.close()
        run.stderr_tail = bytes(tail).decode(errors="replace")
        run.stdout_tail = bytes(out_tail).decode(errors="replace")
        publish()
