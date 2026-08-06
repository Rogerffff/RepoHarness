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
import shlex
from pathlib import Path

_DOCKER_BIN = "docker"


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
        proc.kill()
        await proc.wait()
        return 124, "", f"docker exec timeout after {timeout}s"
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


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
            raise RuntimeError(f"docker exec failed (exit={code}): {cmd[:120]}\n{err[:400]}")
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
            raise RuntimeError(f"sandbox write_file {sandbox_path} failed: {err[:400]}")

    async def read_file(self, sandbox_path: str, *, user: str = "root") -> str:
        code, out, _err = await _run(
            "exec", "-u", user, self.container_name, "cat", sandbox_path, timeout=120.0
        )
        return out if code == 0 else ""
