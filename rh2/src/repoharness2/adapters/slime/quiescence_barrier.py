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
    ③ 冻结：以稳定指纹为 snapshot_ref 出具 FrozenWorkspace——exporter
       从它导出 FrozenPatchArtifact；artifact 持久化成功后 orchestrator
       **立即释放 rollout 容器**（W3a / 决策包 D2-1 状态所有权转移）。

冻结语义说明（W3a 起的实现口径）：v1 的"不可变"由三件事共同构成
——写者集合已证空（①）、静止已双读证实（②）、exporter 对每个变更文件
做"抓取内容 digest == census digest"一致性检查并把 artifact 以 digest
绑定持久化（B2/B5）。旧的"评分后回读原 workspace 复核指纹
（verify_integrity）才承认 reward"主链依赖已按 D2-1 删除：评分时容器早已
不存在，冻结产物本身就是唯一权威。`FrozenWorkspace.verify_integrity()`
仅保留为方法（调试探针），正式链不调用它，也不再发出
snapshot_integrity_mismatch / integrity_recheck_failed。

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

# 进程终止动作与有界验证（批 C 起与编排的"先停止再 drain"共用 execution_scope 模块；
# 这里保留同名别名供既有引用）
from repoharness2.adapters.slime import execution_scope as _scope  # noqa: E402
from repoharness2.adapters.slime.execution_scope import terminate_agent_processes  # noqa: E402

_KILL_VERIFY_ATTEMPTS = _scope.KILL_VERIFY_ATTEMPTS
_KILL_VERIFY_INTERVAL_SECONDS = _scope.KILL_VERIFY_INTERVAL_SECONDS
_KILL_SCRIPT = _scope.KILL_SCRIPT
_COUNT_SCRIPT = _scope.COUNT_SCRIPT
# 屏障 ① 的总截止点（Codex 联合审查 R2：次数上限不是时间上界；超时 = 未确认 → fail-closed）
_STOP_TOTAL_TIMEOUT_SECONDS = 30.0


def _digest_script(workdir: str) -> str:
    # status + diff 一起进指纹：未跟踪文件的增删也要被看见
    return (
        f"cd {workdir} && git status --porcelain 2>/dev/null; "
        f"git -C {workdir} diff 2>/dev/null"
    )


class FrozenWorkspace:
    """冻结副本封装：exporter 的唯一合法输入（QuiescenceConfirmed 的载体）。

    run_bash 委托底层容器（写者集合已证空）；verify_integrity() 复核 snapshot
    指纹——**调试探针**，W3a 起正式链不调用（容器在评分前已释放，见模块
    docstring），保留只为本地排障与单元测试。
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
        # ① 终止 execution scope + 有界验证进程归零（批 C：与编排的强制停止共用同一动作；
        # 编排已先停过时这里是幂等复核）
        stop = await terminate_agent_processes(
            workspace, attempts=_KILL_VERIFY_ATTEMPTS, interval=_KILL_VERIFY_INTERVAL_SECONDS,
            total_timeout=_STOP_TOTAL_TIMEOUT_SECONDS,
        )
        residual = stop.residual
        if residual != 0:
            return QuiescenceRejected(
                reason_code="execution_scope_termination_timeout",
                evidence_refs=(
                    f"residual_agent_processes:{residual}",
                    f"stop_timed_out:{str(stop.timed_out).lower()}",
                ),
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
