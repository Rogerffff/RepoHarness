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

停止证据（Codex 联合审查 R3 + 修后复核 R3；规则全文见 Brief 批 C"停止证据与判定规则"）：
- `kill_returned_at`：kill exec **返回**的时刻（`clock` 域），无论成败——只是原始观测；
- `kill_delivered_at`：只有 exec 退出 0 且脚本回显的 pkill 状态 ∈ {0, 1}（或未回显：替身 / 旧脚本）才有值——
  **kill 动作完成**的时刻上界（procps：0 = 至少一个匹配进程成功收到信号；1 = 无匹配**或**没有一个能成功发送；
  两者都不单独证明整个 scope 已停）；exec 失败 / 超时 / pkill 出错都不算完成；它是动作记录，不是停止证明；
- `observations`：每次残留计数的发起 / 返回时刻与结果——"发起时刻 ≥ 期限仍见进程"是"期限后仍有进程"的证据，
  最终归零**不能**反过来证明期限前已停；
- `confirmed_at`：首次观测到归零的时刻。
`stop_proven_before(result, deadline)` 把这些观测翻译成三态结论 + 证据码；编排与测试用同一实现。
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "COUNT_SCRIPT",
    "KILL_SCRIPT",
    "KILL_VERIFY_ATTEMPTS",
    "KILL_VERIFY_INTERVAL_SECONDS",
    "ScopeObservation",
    "ScopeStopResult",
    "merge_stop_results",
    "stop_proven_before",
    "terminate_agent_processes",
]

# pkill 自身状态回显到 stdout（0 = 已发信号；1 = 无匹配进程；2/3/127 = pkill 出错 / 不存在）；末尾 `true` 让
# exec 退出码只反映 docker exec 本身是否跑完——exec 非零 = 信号可能根本没投递（Codex 修后复核 R3）。
KILL_SCRIPT = "pkill -9 -u agent >/dev/null 2>&1; echo pkill_status=$?; true"
COUNT_SCRIPT = "ps -o pid= -u agent 2>/dev/null | wc -l"
KILL_VERIFY_ATTEMPTS = 10
KILL_VERIFY_INTERVAL_SECONDS = 0.5
_PKILL_STATUS = re.compile(r"pkill_status=(\d+)")
_PKILL_DELIVERED_STATUSES = frozenset({0, 1})


@dataclass(frozen=True)
class ScopeObservation:
    """一次残留计数查询：发起 / 返回时刻（clock 域）与结果（-1 = 不可读）。"""

    issued_at: float
    returned_at: float
    residual: int

    def as_dict(self) -> dict[str, Any]:
        return {"issued_at": self.issued_at, "returned_at": self.returned_at, "residual": self.residual}


@dataclass
class ScopeStopResult:
    residual: int  # 最后一次可读计数：0 = 已验证归零；>0 = 仍有残留；-1 = 未确认（不可读 / IO 超时）
    kill_returned_at: float | None  # kill exec 返回时刻（clock 域），无论成败；None = 预算内未返回
    kill_exit_code: int | None = None  # kill exec 退出码；None = 未返回
    pkill_status: int | None = None  # 脚本回显的 pkill 自身状态；None = 未回显
    kill_delivered_at: float | None = None  # SIGKILL 已投递的时刻上界；None = 未证明投递
    confirmed_at: float | None = None  # 首次观测到归零的时刻（clock 域）；None = 未确认
    observations: list[ScopeObservation] = field(default_factory=list)
    timed_out: bool = False  # 总预算内没有完成（某次 IO 超时或预算耗尽）
    elapsed_seconds: float = 0.0
    attempts: int = 1  # 合并了几次 terminate_agent_processes 调用（编排重试时 >1）

    @property
    def verified(self) -> bool:
        return self.residual == 0

    def presence_observed_at_or_after(self, t: float) -> bool:
        """有没有一次**发起时刻 ≥ t** 的计数看到残留进程（用发起时刻，排除"早发起、晚回包"的解释）。"""

        return any(o.residual > 0 and o.issued_at >= t for o in self.observations)

    def as_dict(self, *, max_observations: int = 32) -> dict[str, Any]:
        return {
            "residual": self.residual,
            "kill_returned_at": self.kill_returned_at,
            "kill_exit_code": self.kill_exit_code,
            "pkill_status": self.pkill_status,
            "kill_delivered_at": self.kill_delivered_at,
            "confirmed_at": self.confirmed_at,
            "observations": [o.as_dict() for o in self.observations[:max_observations]],
            "observation_count": len(self.observations),
            "timed_out": self.timed_out,
            "elapsed_seconds": self.elapsed_seconds,
            "attempts": self.attempts,
        }


def merge_stop_results(earlier: ScopeStopResult | None, later: ScopeStopResult) -> ScopeStopResult:
    """把编排的多次停止尝试合并成一份证据：投递取第一次成功的，归零取第一次观测到的，计数全部保留，
    kill 返回事实取最近一次真正返回的。"""

    if earlier is None:
        return later
    observations = list(earlier.observations) + list(later.observations)
    readable = [o.residual for o in observations if o.residual >= 0]
    returned = later if later.kill_returned_at is not None else earlier
    return ScopeStopResult(
        residual=readable[-1] if readable else -1,
        kill_returned_at=returned.kill_returned_at,
        kill_exit_code=returned.kill_exit_code,
        pkill_status=returned.pkill_status,
        kill_delivered_at=(
            earlier.kill_delivered_at if earlier.kill_delivered_at is not None else later.kill_delivered_at
        ),
        confirmed_at=earlier.confirmed_at if earlier.confirmed_at is not None else later.confirmed_at,
        observations=observations,
        timed_out=later.timed_out,
        elapsed_seconds=round(earlier.elapsed_seconds + later.elapsed_seconds, 3),
        attempts=earlier.attempts + later.attempts,
    )


def stop_proven_before(result: ScopeStopResult | None, deadline: float | None) -> tuple[bool | None, str]:
    """"执行在 deadline 前已停止"有没有被**证明**（Brief 批 C 停止证据规则）。返回 (三态, 证据码)：

    - True：(A) 控制端在 deadline 前收到一次归零确认（计数返回 0 且返回时刻 ≤ deadline）；或 (B-残)
      kill 动作在 deadline 前完成、之后**收到过**归零确认（只是回包晚于 deadline）、且完成之后没有任何一次
      计数看到进程——这一条是"投递早、确认晚"的边界，是否继续算 KEEP 由 owner 决定（Codex 复核 2 §5）；
    - False：kill exec 失败 / 未返回、完成晚于 deadline、完成后从未收到归零确认（缺观测不是证明）、完成后
      仍观测到进程——"未证明"，调用方在 deadline 已过时按 hard wall 处理；
    - None：没有 deadline（无从比较）。
    """

    if deadline is None:
        return None, "no_deadline"
    if result is None:
        return False, "no_stop_result"
    if result.confirmed_at is not None and result.confirmed_at <= deadline:
        return True, "zero_confirmed_before_deadline"
    if result.kill_delivered_at is None:
        if result.kill_returned_at is None:
            return False, "kill_not_returned"
        return False, "kill_exec_failed"
    if result.kill_delivered_at > deadline:
        return False, "kill_delivered_after_deadline"
    if result.confirmed_at is None:
        # Codex 复核 2 §3.1：COUNT 超时 / 次数耗尽都没拿到归零——没有反证 ≠ 停止证明
        return False, "kill_delivered_but_never_confirmed"
    if result.presence_observed_at_or_after(deadline):
        return False, "presence_observed_after_deadline"
    if result.presence_observed_at_or_after(result.kill_delivered_at):
        # kill 完成之后还看到过进程（不管发起时刻在期限前后）：这次 kill 没有覆盖全部执行
        return False, "presence_observed_after_delivery"
    return True, "kill_delivered_before_deadline_late_zero_confirmation"


async def terminate_agent_processes(
    workspace: Any,
    *,
    attempts: int = KILL_VERIFY_ATTEMPTS,
    interval: float = KILL_VERIFY_INTERVAL_SECONDS,
    total_timeout: float = 30.0,
    clock: Callable[[], float] = time.monotonic,
) -> ScopeStopResult:
    """`pkill -9 -u agent` 然后按 `ps -u agent | wc -l` 有界验证；`total_timeout` 秒内必定返回。

    只记录观测，不下结论：投递 / 归零 / 期限后仍在的判定由 `stop_proven_before` 做。
    """

    started = time.monotonic()

    def left() -> float:
        return total_timeout - (time.monotonic() - started)

    result = ScopeStopResult(residual=-1, kill_returned_at=None)
    try:
        kill = await asyncio.wait_for(workspace.run_bash(KILL_SCRIPT), timeout=max(0.0, left()))
    except (TimeoutError, asyncio.TimeoutError):
        result.timed_out = True
        result.elapsed_seconds = round(time.monotonic() - started, 3)
        return result
    result.kill_returned_at = clock()
    exit_code = getattr(kill, "exit_code", 1)
    result.kill_exit_code = exit_code if isinstance(exit_code, int) else 1
    match = _PKILL_STATUS.search(str(getattr(kill, "stdout", "") or ""))
    result.pkill_status = int(match.group(1)) if match else None
    if result.kill_exit_code == 0 and (
        result.pkill_status is None or result.pkill_status in _PKILL_DELIVERED_STATUSES
    ):
        result.kill_delivered_at = result.kill_returned_at
    for _ in range(attempts):
        if left() <= 0:
            result.timed_out = True
            break
        issued_at = clock()
        try:
            probe = await asyncio.wait_for(workspace.run_bash(COUNT_SCRIPT), timeout=max(0.0, left()))
        except (TimeoutError, asyncio.TimeoutError):
            result.timed_out = True
            break
        returned_at = clock()
        residual = -1
        if getattr(probe, "exit_code", 1) == 0:
            try:
                residual = int((getattr(probe, "stdout", "") or "").strip() or "0")
            except ValueError:
                residual = -1
        result.observations.append(ScopeObservation(issued_at=issued_at, returned_at=returned_at, residual=residual))
        if residual >= 0:
            result.residual = residual
            if residual == 0:
                result.confirmed_at = returned_at
                break
        if left() <= 0:
            result.timed_out = True
            break
        await asyncio.sleep(min(interval, max(0.0, left())))
    result.elapsed_seconds = round(time.monotonic() - started, 3)
    return result
