"""F2-2b：Runtime 静止屏障的真实实现（D1a 屏障序列的容器面）。

序列（决策包 D1a，orchestrator 已先完成会话面：revoke → drain →
poison/边界断言 → capture 关账；本屏障接管其余步骤）：

    ① 终止 execution scope：杀灭容器内全部 agent 用户进程（CC 的
       setsid 后台进程一并覆盖——按用户杀，不按进程树杀），有界重试
       验证进程数归零；超时 → execution_scope_termination_timeout。
    ② 写入归零确认：进程归零后对 workspace 做**双读数字指纹**
       （git status --porcelain + git diff 的 sha256，间隔一个让步点）；
       两读不一致 → active_writer_detected。会话面未排空（迟到模型
       请求可能仍在写）→ late_model_request_detected。
    ③ 冻结：以稳定指纹为 snapshot_ref 出具 FrozenWorkspace——评分链
       只拿到该封装；评分完成后 orchestrator 调 verify_integrity()
       复核指纹，漂移 → snapshot_integrity_mismatch（评分结果作废，
       execution 按 missing 收口）。

冻结语义说明（实现口径，写进验收）：v1 的"不可变"由三件事共同构成
——写者集合已证空（①）、静止已双读证实（②）、评分后完整性复核（③）。
不做物理 cp 副本：写者为零时副本不增加保证，评分后复核才是端到端的
不可变证明；若后续审查要求物理副本，可在本类内加而不动调用面。

失败路径全部返回 QuiescenceRejected（勘误 3 五码）+ 证据；本类不抛
业务异常（未知异常由 orchestrator 按 D4 run_halt 处理）。
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from repoharness2.adapters.slime.generate import (
    QuiescenceConfirmed,
    QuiescenceRejected,
)

__all__ = ["DockerQuiescenceBarrier", "FrozenWorkspace"]

# 进程终止验证的有界重试（总计约 5s；数值属实现细节非预注册阈值）
_KILL_VERIFY_ATTEMPTS = 10
_KILL_VERIFY_INTERVAL_SECONDS = 0.5

_KILL_SCRIPT = "pkill -9 -u agent >/dev/null 2>&1; true"
_COUNT_SCRIPT = "ps -o pid= -u agent 2>/dev/null | wc -l"


def _digest_script(workdir: str) -> str:
    # status + diff 一起进指纹：未跟踪文件的增删也要被看见
    return (
        f"cd {workdir} && git status --porcelain 2>/dev/null; "
        f"git -C {workdir} diff 2>/dev/null"
    )


class FrozenWorkspace:
    """冻结副本封装：评分链唯一合法输入（QuiescenceConfirmed 的载体）。

    run_bash 委托底层容器（写者集合已证空）；verify_integrity() 在评分
    之后复核 snapshot 指纹——漂移即冻结失效。
    """

    def __init__(self, underlying: Any, workdir: str, snapshot_ref: str) -> None:
        self._underlying = underlying
        self._workdir = workdir
        self.snapshot_ref = snapshot_ref

    async def run_bash(self, script: str) -> Any:
        return await self._underlying.run_bash(script)

    async def verify_integrity(self) -> bool:
        result = await self._underlying.run_bash(_digest_script(self._workdir))
        if getattr(result, "exit_code", 1) != 0:
            return False
        digest = hashlib.sha256(result.stdout.encode("utf-8")).hexdigest()
        return f"sha256:{digest}" == self.snapshot_ref


class DockerQuiescenceBarrier:
    """RuntimeQuiescenceBarrier 的容器实现（bringup 在 fa_formal 注入）。"""

    def __init__(self, workdir: str = "/testbed") -> None:
        self._workdir = workdir

    async def establish(
        self, *, workspace: Any, audit: Any
    ) -> QuiescenceConfirmed | QuiescenceRejected:
        # ② 前提：会话面必须已排空（orchestrator 序列保证；不成立说明
        # 迟到模型请求仍可能在写——fail-closed）
        if not getattr(audit, "session_plane_drained", False):
            return QuiescenceRejected(
                reason_code="late_model_request_detected",
                evidence_refs=("audit:session_plane_drained=false",),
            )
        # ① 终止 execution scope + 有界验证进程归零
        await workspace.run_bash(_KILL_SCRIPT)
        residual = -1
        for _ in range(_KILL_VERIFY_ATTEMPTS):
            result = await workspace.run_bash(_COUNT_SCRIPT)
            if getattr(result, "exit_code", 1) == 0:
                try:
                    residual = int(result.stdout.strip() or "0")
                except ValueError:
                    residual = -1
                if residual == 0:
                    break
            await asyncio.sleep(_KILL_VERIFY_INTERVAL_SECONDS)
        if residual != 0:
            return QuiescenceRejected(
                reason_code="execution_scope_termination_timeout",
                evidence_refs=(f"residual_agent_processes:{residual}",),
            )
        # ② 双读指纹：静止证实
        first = await workspace.run_bash(_digest_script(self._workdir))
        if getattr(first, "exit_code", 1) != 0:
            return QuiescenceRejected(
                reason_code="snapshot_freeze_failed",
                evidence_refs=(f"digest_read_1_exit:{first.exit_code}",),
            )
        await asyncio.sleep(0)  # 让步点：给潜在写者一个暴露窗口
        second = await workspace.run_bash(_digest_script(self._workdir))
        if getattr(second, "exit_code", 1) != 0:
            return QuiescenceRejected(
                reason_code="snapshot_freeze_failed",
                evidence_refs=(f"digest_read_2_exit:{second.exit_code}",),
            )
        if first.stdout != second.stdout:
            return QuiescenceRejected(
                reason_code="active_writer_detected",
                evidence_refs=("workspace_digest_changed_between_reads",),
            )
        # ③ 冻结出具
        digest = hashlib.sha256(second.stdout.encode("utf-8")).hexdigest()
        snapshot_ref = f"sha256:{digest}"
        return QuiescenceConfirmed(
            frozen_grading_workspace=FrozenWorkspace(
                workspace, self._workdir, snapshot_ref
            ),
            snapshot_ref=snapshot_ref,
            evidence_refs=(
                "agent_processes_zero",
                "workspace_digest_stable_double_read",
            ),
        )
