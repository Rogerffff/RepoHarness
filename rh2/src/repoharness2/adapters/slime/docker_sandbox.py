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
import re
import shlex
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
# #2（基座探针修复，2026-09-23）：harness 输出的宿主收集
# ---------------------------------------------------------------------------
#
# 此前 vendored `run_agent` 在容器里以 agent 身份 `setsid` 启动 launcher，把 CC 的 stream-json 重定向到
# `{workdir}/.harness/trajectory.jsonl`（agent 属主、可读；`git status` 里可见），退出码由 launcher 写进
# agent 可写的 `/tmp/.run.done`。B 线探针里模型 grep 到了自己的轨迹文件（当"参考解"反复读）。
# 现在：宿主以 `docker exec -u agent` 直接接管 CC 的 stdout / stderr，增量写到宿主文件（容器内没有副本，
# agent 读不到）；退出码来自 docker CLI 的返回（daemon 报告，不可伪造）；容器内不再有 launcher 与 done 标记。
# "分离 + 轮询"是 E2B 网关会切断长流的设计，本地 Docker CLI 没有这个限制。
#
# 失败分两类（Codex SR2）：① 只是宿主诊断文件写失败——继续排空管道、退出码仍可信，记 partial；
# ② docker CLI 自身异常（连接丢失等）——失去可信的结束事实，由调用方抛 typed `harness_exec_connection_lost`。

_DOCKER_CLI_EXIT_CODES = (125, 126, 127)  # docker CLI 自身 / OCI 层错误码（不是容器内进程的退出码）
_DOCKER_CLI_ERROR_RE = re.compile(
    r"^(Error response from daemon|error during connect|Cannot connect to the Docker daemon|"
    r"OCI runtime exec failed|unexpected EOF|context canceled|rpc error)",
    re.IGNORECASE,
)
_STDERR_TAIL_BYTES = 4096
_PUMP_DRAIN_TIMEOUT_SEC = 30.0


@dataclass
class HostCollectedRun:
    """一次宿主收集的执行事实。exit_code = 容器内进程退出码（或时间预算标记）；client_* = docker CLI 的。"""

    exit_code: int
    client_exit_code: int | None
    client_exit_kind: str  # container_process_exit | docker_cli_error | time_budget
    stdout_path: str
    stderr_path: str
    stdout_bytes: int
    stderr_bytes: int
    log_complete: bool  # 两路都读到 EOF 且无写失败
    log_partial_reason: str | None  # time_budget | write_error:<...> | pump_drain_timeout
    stderr_tail: str
    seconds: float

    def facts(self) -> dict[str, Any]:
        return asdict(self)


def classify_client_exit(rc: int, stderr_tail: str) -> str:
    """docker CLI 退出码 + stderr 尾部 → 事实类别。125/126/127 是 CLI / OCI 层码；其它非零若 stderr 最后一行
    是 docker 客户端的错误形态也归 CLI 错误（启发式，尾部原文一并记录供人核）；否则就是容器内进程的退出码。"""

    if rc in _DOCKER_CLI_EXIT_CODES:
        return "docker_cli_error"
    if rc != 0:
        lines = [line for line in stderr_tail.splitlines() if line.strip()]
        if lines and _DOCKER_CLI_ERROR_RE.match(lines[-1].strip()):
            return "docker_cli_error"
    return "container_process_exit"


def host_exec_argv(*, container_name: str, user: str, workdir: str, env: dict[str, str], cmd: str) -> list[str]:
    """`docker exec -u <user> -w <workdir> -e K=V … <container> bash -c <cmd>`：HOME 等随 exec env 在 bash 启动前就位。"""

    argv = [_DOCKER_BIN, "exec", "-u", user, "-w", workdir]
    for key, value in env.items():
        argv += ["-e", f"{key}={value}"]
    argv += [container_name, "bash", "-c", cmd]
    return argv


def _open_log(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("ab", buffering=0)


async def run_host_collected(
    argv: list[str], *, stdout_path: Path | str, stderr_path: Path | str, deadline_seconds: float,
    time_budget_exit_code: int = -1, chunk_size: int = 65536,
) -> HostCollectedRun:
    """宿主起 `argv`（正常是 docker exec），两路输出增量写到宿主文件，等进程退出。

    - 客户端进程、两路读取任务、文件句柄都归本次调用：正常结束排空尾部；期限到点杀客户端（容器内进程
      由既有 execution_scope 屏障与容器清理终止，不在这里另造停止生命周期）；外层取消回收后原样传播。
    - 写文件失败（磁盘）：记 write_error、关闭句柄、继续排空管道——退出码仍可信，`log_complete=False`。
    - 每块写是小的同步写，占用事件循环的时间由测量说话（Brief §4 撤回"不阻塞"的绝对保证）。
    """

    started = time.monotonic()
    out_path, err_path = Path(stdout_path), Path(stderr_path)
    proc = await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    counts = {"stdout": 0, "stderr": 0}
    write_error: list[str] = []
    tail = bytearray()

    async def pump(stream, path: Path, key: str, keep_tail: bool) -> None:
        fh = None
        try:
            try:
                fh = _open_log(path)
            except OSError as exc:
                write_error.append(f"{key}:open:{exc}")
            while True:
                data = await stream.read(chunk_size)
                if not data:
                    break
                if keep_tail:
                    tail.extend(data)
                    if len(tail) > _STDERR_TAIL_BYTES:
                        del tail[:-_STDERR_TAIL_BYTES]
                if fh is not None:
                    try:
                        fh.write(data)
                        counts[key] += len(data)
                    except OSError as exc:  # 磁盘故障：留痕、停止写、继续排空
                        write_error.append(f"{key}:write:{exc}")
                        fh.close()
                        fh = None
        finally:
            if fh is not None:
                fh.close()

    pumps = [
        asyncio.create_task(pump(proc.stdout, out_path, "stdout", False)),
        asyncio.create_task(pump(proc.stderr, err_path, "stderr", True)),
    ]
    time_budget_hit = False
    drained = False
    try:
        try:
            await asyncio.wait_for(proc.wait(), timeout=deadline_seconds)
        except (TimeoutError, asyncio.TimeoutError):
            time_budget_hit = True
            _kill_quietly(proc)
            await proc.wait()
        done, pending = await asyncio.wait(pumps, timeout=_PUMP_DRAIN_TIMEOUT_SEC)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pumps, return_exceptions=True)
        drained = not pending
    except asyncio.CancelledError:
        # 外层取消（hard wall / poison / 关停）：回收宿主客户端与读取任务后传播；容器内进程归既有 owner
        _kill_quietly(proc)
        for task in pumps:
            task.cancel()
        await asyncio.gather(*pumps, return_exceptions=True)
        await proc.wait()
        raise
    rc = proc.returncode if proc.returncode is not None else 0
    stderr_text = bytes(tail).decode(errors="replace")
    if time_budget_hit:
        kind, exit_code, partial = "time_budget", time_budget_exit_code, "time_budget"
    else:
        kind, exit_code = classify_client_exit(rc, stderr_text), rc
        partial = f"write_error:{';'.join(write_error)}" if write_error else (None if drained else "pump_drain_timeout")
    return HostCollectedRun(
        exit_code=exit_code, client_exit_code=rc, client_exit_kind=kind,
        stdout_path=str(out_path), stderr_path=str(err_path),
        stdout_bytes=counts["stdout"], stderr_bytes=counts["stderr"],
        log_complete=(not time_budget_hit) and drained and not write_error, log_partial_reason=partial,
        stderr_tail=stderr_text, seconds=round(time.monotonic() - started, 3),
    )
