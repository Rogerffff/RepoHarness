"""B5：per-attempt finalization receipt（A-prime T0 第 7/9 条落地）。

定位：一次物理 attempt 走到 finalize 之后的**耐久终局记录**（OUTCOME
DURABLE）。cleanup 只允许发生在 receipt 原子持久化成功之后（"receipt 前
cleanup 不发生"）；cleanup 的结果作为**独立追加记录**落盘
（CleanupResultAppendV1，单独文件），绝不改写 receipt 本体（"追加不
覆盖首因"）。

**receipt 不是 trainer handoff 证明**（B5 复核 P0 定界）：receipt 在
generate() 的 finally 段写入——此刻结果还没有离开 orchestrator（后面
还有 worker queue、PromptGroup 组装、collect_batch 三道关，任何一道都
可能把样本拦下）。因此 disposition 的成功值叫 **delivery_prepared**
（样本已备好交回 slime 例程），受 receipt 语义约束**不存在**
"handed_off/已进训练"字段；训练侧 HANDED_OFF 事实只能由 F2-5/F2-6 在
batch 真正交给 trainer 时另行记录。F2-4 恢复端据此的正确读法：
delivery_prepared 且无 F2-5/F2-6 交付记录 = 样本**未**进训练（不是
uncertain_trained）。

F2-4 复用面（erratum-4 v1：RolloutManager-only 恢复）：
- attempt_disposition + outcome_v2（typed 嵌入，构造期复跑 Outcome v2
  全量不变量）：completion/termination/reason/reward_unavailable 的唯一
  事实层，恢复端不需要再加载 audit JSONL；
- frozen_patch_digest / baseline_manifest_digest：指向 per-attempt
  immutable 目录里的 artifact 本体（T0 第 9 条：不建全局 CAS；本体在
  receipt 之前持久化，unsafe 拒绝也保留——evidence 与准入是两回事）；
- drain_receipt_ref：F2-3 typed drain receipt 占位（当前恒 None——
  fa_formal 开闸前置之一，落地后填引用）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from repoharness2.contracts._base import NonEmptyStr, Sha256Digest, StrictModel
from repoharness2.contracts.fa_runtime import RolloutAttemptOutcomeV2

__all__ = [
    "AttemptDisposition",
    "CleanupFailureFact",
    "CleanupResultAppendV1",
    "FinalizationReceiptV1",
]

# attempt 终局四分：
# - delivery_prepared：generate 正常收口，样本（或降级/abort 形状）已
#   备好交回 slime 例程——**不是** trainer handoff（见模块 docstring）；
# - aborted：软失败收口（abort 形状返回，样本剔除；归因见 outcome_v2）；
# - fatal_run_halt：FatalExecutionInfrastructureError 在途（worker 将
#   run-halt；receipt 在异常传播前落盘）；
# - cancelled：asyncio 取消在途（受控拆除，事实按当时所知记录）。
AttemptDisposition = Literal[
    "delivery_prepared", "aborted", "fatal_run_halt", "cancelled"
]


class FinalizationReceiptV1(StrictModel):
    schema_id: Literal["rh2.fa.finalization_receipt.v1"] = Field(
        default="rh2.fa.finalization_receipt.v1", description="schema 身份。"
    )
    receipt_id: NonEmptyStr = Field(description="确定性 id（物理 attempt 唯一）。")
    task_id: NonEmptyStr
    trajectory_id: NonEmptyStr
    session_id: str | None = Field(default=None, description="稳定会话键（非凭证）。")
    physical_attempt_id: str | None = Field(
        default=None, description="F2-1a 物理身份；S1 兼容路径为 None。"
    )
    attempt_disposition: AttemptDisposition
    abort_reason: str | None = Field(
        default=None,
        description="aborted 时的归因摘要（outcome_v2.reason_code 或最后一条"
        "failure_record 的 error_type；outcome_v2 才是权威归因）。",
    )
    outcome_v2: RolloutAttemptOutcomeV2 | None = Field(
        default=None,
        description="Outcome v2 typed 嵌入（构造期复跑全量不变量；受体不再"
        "接受任意 dict）。S1 兼容路径为 None。",
    )
    frozen_patch_digest: Sha256Digest | None = None
    baseline_manifest_digest: Sha256Digest | None = None
    artifact_bodies_persisted: bool = Field(
        default=False,
        description="frozen patch + baseline manifest 本体是否已在 receipt "
        "之前持久化到 per-attempt immutable 目录（digest 引用可解引用）。",
    )
    grading_report_id: str | None = None
    grading_outcome: str | None = None
    eligibility_report_id: str | None = None
    delivered_sample_count: int = Field(
        default=0,
        description="备好交回 slime 的样本条数（delivery_prepared 语义的"
        "载荷大小；不代表进入训练）。",
    )
    runtime_quiescence_confirmed: bool = False
    drain_receipt_ref: str | None = Field(
        default=None, description="F2-3 typed drain receipt 引用（未落地恒 None）。"
    )
    started_epoch_seconds: float
    finalized_at_utc: datetime


class CleanupFailureFact(StrictModel):
    lease_id: str
    step: NonEmptyStr
    detail: str


class CleanupResultAppendV1(StrictModel):
    """cleanup 结束后的追加记录（独立文件，永不改写 receipt）。"""

    schema_id: Literal["rh2.fa.cleanup_result_append.v1"] = Field(
        default="rh2.fa.cleanup_result_append.v1", description="schema 身份。"
    )
    receipt_id: NonEmptyStr
    cleanup_failures: list[CleanupFailureFact] = Field(default_factory=list)
    quarantined_container: str | None = None
    lease_released: bool = False
    poison_released: bool = False
    completed_at_utc: datetime
