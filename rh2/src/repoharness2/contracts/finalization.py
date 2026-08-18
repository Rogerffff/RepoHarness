"""B5：per-attempt finalization receipt（A-prime T0 第 7 条落地）。

定位：一次物理 attempt 走到 finalize 之后的**耐久终局记录**。cleanup 只
允许发生在 receipt 原子持久化成功之后（"receipt 前 cleanup 不发生"）；
cleanup 的结果作为**独立追加记录**落盘（CleanupResultAppendV1，单独
文件），绝不改写 receipt 本体（"追加不覆盖首因"）。

F2-4 复用面（erratum-4 v1：RolloutManager-only 恢复）：崩溃重启后读
receipt 即可裁定每个 attempt 的终局——
- attempt_disposition + handed_off：HANDED_OFF 且无 trainer ACK →
  uncertain_trained（F2-4 语义，本契约只提供事实）；
- outcome_v2 verbatim：completion/termination/reason/reward_unavailable
  的唯一事实层，恢复端不需要再加载 audit JSONL；
- frozen_patch_digest / baseline_manifest_digest：指向 content-addressed
  artifact body（B5 在 receipt 之前持久化——评分产物在 workspace 清理后
  仍可审计/复评）；
- drain_receipt_ref：F2-3 typed drain receipt 占位（当前恒 None——
  fa_formal 开闸前置之一，落地后填引用）。

校验哲学（有意从宽）：receipt 是 finally 段的**证据记录器**，不是语义
执法者——outcome_v2 在生产时已过 RolloutAttemptOutcomeV2 全量校验，此处
再做跨字段强校验只会在最坏时刻（清理前落盘）制造新的失败面。只锁类型
与枚举。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from repoharness2.contracts._base import NonEmptyStr, Sha256Digest, StrictModel

__all__ = [
    "AttemptDisposition",
    "CleanupFailureFact",
    "CleanupResultAppendV1",
    "FinalizationReceiptV1",
]

# attempt 终局四分：
# - delivered：generate 正常返回，样本（或降级信号）已交给 slime 例程
#   （handed_off 区分真样本 vs 降级转发）；
# - aborted：软失败收口（abort 形状返回，样本剔除；归因见 outcome_v2）；
# - fatal_run_halt：FatalExecutionInfrastructureError 在途（worker 将
#   run-halt；receipt 在异常传播前落盘）；
# - cancelled：asyncio 取消在途（受控拆除，事实按当时所知记录）。
AttemptDisposition = Literal["delivered", "aborted", "fatal_run_halt", "cancelled"]


class FinalizationReceiptV1(StrictModel):
    schema_version: Literal["finalization_receipt_v1"] = "finalization_receipt_v1"
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
    outcome_v2: dict[str, Any] | None = Field(
        default=None,
        description="RolloutAttemptOutcomeV2 dict 原样嵌入（生产时已过全量"
        "校验；S1 兼容路径为 None）。",
    )
    frozen_patch_digest: Sha256Digest | None = None
    baseline_manifest_digest: Sha256Digest | None = None
    artifact_bodies_persisted: bool = Field(
        default=False,
        description="frozen patch + baseline manifest 本体是否已在 receipt "
        "之前 content-addressed 持久化（digest 引用是否可解引用）。",
    )
    grading_report_id: str | None = None
    grading_outcome: str | None = None
    eligibility_report_id: str | None = None
    handed_off: bool = Field(
        default=False,
        description="真实样本已交付 slime（step9_samples_delivered）。F2-4："
        "handed_off 且无 trainer ACK → uncertain_trained。",
    )
    delivered_sample_count: int = 0
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

    schema_version: Literal["cleanup_result_append_v1"] = "cleanup_result_append_v1"
    receipt_id: NonEmptyStr
    cleanup_failures: list[CleanupFailureFact] = Field(default_factory=list)
    quarantined_container: str | None = None
    lease_released: bool = False
    poison_released: bool = False
    completed_at_utc: datetime
