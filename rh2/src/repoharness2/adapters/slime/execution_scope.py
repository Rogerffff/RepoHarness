"""执行 scope 的终止动作（批 C，I14 rollout 侧）：杀容器内 agent 用户的全部进程并**有界**验证归零。

两个调用方共用同一动作与判据，不各写一份：
- `quiescence_barrier.DockerQuiescenceBarrier.establish` 的 ①（冻结前终止 execution scope）；
- `generate.RolloutOrchestrator` 在 turn 预算命中后 CC 未在宽限内自行退出、或 hard wall 到点时的
  **先停止再 drain**（vendored done-marker 轮询到点不杀进程，期限取消只回收宿主 CLI，容器内 CC 若不停
  会继续发请求、继续写工作区）。

有界（Codex 联合审查 R2）：`total_timeout` 是本函数的总截止点——每个阻塞 await（kill exec、count exec、
间隔 sleep）都拿剩余时间做 `wait_for`；超时即返回 `timed_out=True`（`wait_for` 取消内部调用，默认
Docker runner 在取消路径上 kill+wait 宿主 CLI）。"最多查 N 次、每次间隔 I 秒"只限制次数，不是时间上界，
所以不再单独作为保证。函数不抛业务异常（`CancelledError` 原样传播）。

停止事实（Codex 联合审查 R3）：`kill_returned_at` 是 kill 命令**返回**的时刻（`clock` 域：编排传入自己
的钟）——SIGKILL 已投递的上界；`confirmed_at` 是首次观测到进程归零的时刻。两者分开记录，调用方据此区分
"墙前已停、只是确认晚"与"墙到时仍在执行"，不把"已发出 kill"当成"已停止"，也不把晚确认当成越墙。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "COUNT_SCRIPT",
    "KILL_SCRIPT",
    "KILL_VERIFY_ATTEMPTS",
    "KILL_VERIFY_INTERVAL_SECONDS",
    "ScopeStopResult",
    "terminate_agent_processes",
]

KILL_SCRIPT = "pkill -9 -u agent >/dev/null 2>&1; true"
COUNT_SCRIPT = "ps -o pid= -u agent 2>/dev/null | wc -l"
KILL_VERIFY_ATTEMPTS = 10
KILL_VERIFY_INTERVAL_SECONDS = 0.5


@dataclass
class ScopeStopResult:
    residual: int  # 0 = 已验证归零；>0 = 验证窗口内仍有残留；-1 = 未确认（计数不可读 / IO 超时）
    kill_returned_at: float | None  # kill 命令返回时刻（clock 域）；None = kill 未在预算内返回
    confirmed_at: float | None  # 首次观测到归零的时刻（clock 域）；None = 未确认
    timed_out: bool  # 总预算内没有完成（某次 IO 超时或预算耗尽）
    elapsed_seconds: float

    @property
    def verified(self) -> bool:
        return self.residual == 0


async def terminate_agent_processes(
    workspace: Any,
    *,
    attempts: int = KILL_VERIFY_ATTEMPTS,
    interval: float = KILL_VERIFY_INTERVAL_SECONDS,
    total_timeout: float = 30.0,
    clock: Callable[[], float] = time.monotonic,
) -> ScopeStopResult:
    """`pkill -9 -u agent` 然后按 `ps -u agent | wc -l` 有界验证；`total_timeout` 秒内必定返回。"""

    started = time.monotonic()

    def left() -> float:
        return total_timeout - (time.monotonic() - started)

    result = ScopeStopResult(residual=-1, kill_returned_at=None, confirmed_at=None, timed_out=False, elapsed_seconds=0.0)
    try:
        await asyncio.wait_for(workspace.run_bash(KILL_SCRIPT), timeout=max(0.0, left()))
    except (TimeoutError, asyncio.TimeoutError):
        result.timed_out = True
        result.elapsed_seconds = round(time.monotonic() - started, 3)
        return result
    result.kill_returned_at = clock()
    for _ in range(attempts):
        if left() <= 0:
            result.timed_out = True
            break
        try:
            probe = await asyncio.wait_for(workspace.run_bash(COUNT_SCRIPT), timeout=max(0.0, left()))
        except (TimeoutError, asyncio.TimeoutError):
            result.timed_out = True
            break
        if getattr(probe, "exit_code", 1) == 0:
            try:
                residual = int((getattr(probe, "stdout", "") or "").strip() or "0")
            except ValueError:
                residual = -1
            result.residual = residual
            if residual == 0:
                result.confirmed_at = clock()
                break
        if left() <= 0:
            result.timed_out = True
            break
        await asyncio.sleep(min(interval, max(0.0, left())))
    result.elapsed_seconds = round(time.monotonic() - started, 3)
    return result
