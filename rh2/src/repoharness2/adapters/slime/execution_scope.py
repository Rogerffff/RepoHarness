"""执行 scope 的终止动作（批 C，I14 rollout 侧）：杀容器内 agent 用户的全部进程并有界验证归零。

两个调用方共用同一动作与判据，不各写一份：
- `quiescence_barrier.DockerQuiescenceBarrier.establish` 的 ①（冻结前终止 execution scope）；
- `generate.RolloutOrchestrator` 在 turn 预算命中后 CC 未在宽限内自行退出、或 hard wall 到点时的
  **先停止再 drain**（批 C：vendored done-marker 轮询到点不杀进程，期限取消只回收宿主 CLI，
  容器内 CC 若不停会继续发请求、继续写工作区）。

数值属实现细节非预注册阈值（有界重试总计约 5s）。
"""

from __future__ import annotations

import asyncio
from typing import Any

__all__ = [
    "COUNT_SCRIPT",
    "KILL_SCRIPT",
    "KILL_VERIFY_ATTEMPTS",
    "KILL_VERIFY_INTERVAL_SECONDS",
    "terminate_agent_processes",
]

KILL_SCRIPT = "pkill -9 -u agent >/dev/null 2>&1; true"
COUNT_SCRIPT = "ps -o pid= -u agent 2>/dev/null | wc -l"
KILL_VERIFY_ATTEMPTS = 10
KILL_VERIFY_INTERVAL_SECONDS = 0.5


async def terminate_agent_processes(
    workspace: Any,
    *,
    attempts: int = KILL_VERIFY_ATTEMPTS,
    interval: float = KILL_VERIFY_INTERVAL_SECONDS,
) -> int:
    """`pkill -9 -u agent` 然后按 `ps -u agent | wc -l` 有界验证。返回残留进程数：0 = 已验证归零；
    >0 = 验证窗口结束仍有残留；-1 = 计数不可读（exec 失败 / 输出不是整数）。不抛异常。"""

    await workspace.run_bash(KILL_SCRIPT)
    residual = -1
    for _ in range(attempts):
        result = await workspace.run_bash(COUNT_SCRIPT)
        if getattr(result, "exit_code", 1) == 0:
            try:
                residual = int((getattr(result, "stdout", "") or "").strip() or "0")
            except ValueError:
                residual = -1
            if residual == 0:
                break
        await asyncio.sleep(interval)
    return residual
