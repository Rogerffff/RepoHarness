"""W2a termination 事实的只读派生视图（Wave1 复核 F5 后的形态）。

历史：本模块初版是独立的 `TerminationFactsV1` 记录——自带 task/digest 锚与
一组可由任意调用方填写的布尔事实。Wave1 复核（F5）指出两个结构问题并经
核实成立：

1. **缺 attempt 身份**：只带 task_id + environment_package_digest，同题 n=8
   的成员、同 member 的多次 retry 共享这两个值——W1b 无法把终止事实唯一
   归属到一次 physical execution；
2. **重复事实 owner**：capture/quiescence/patch/grading 完成状态在既有权威
   对象里已经存在（`RolloutAttemptOutcomeV2` 带 termination_kind/completion
   事实层，`FinalizationReceiptV1` 带 physical_attempt_id、frozen_patch/
   grading/eligibility 引用、quiescence 与时间事实）——再开一个可独立填写
   的记录 = 第二事实 owner，调用方可以构造互相矛盾的布尔值。

修复采用 codex 建议的首选方案：**删除独立事实 owner**。本模块现在只提供
`derive_termination_facts(receipt)`——从既有 `FinalizationReceiptV1`（内嵌
`RolloutAttemptOutcomeV2`）派生一个**只读**视图，所有"事实"都是对权威对象
的派生属性，没有任何可独立注入的存储字段。A5 的"批准前边界"不变：这里
仍然只有事实，没有 disposition/admission/reward/mask 语义。

刻意不提供的东西（与 F5 修复清单一致）：

- **capture_closed**：capture 闭合事实的 owner 是 eligibility 事实层
  （EligibilityFacts.token_provenance 维）与 execution audit——不在这里
  复制第三份；W1b 从 EligibilityReport 读。
- **粗粒度时长**：receipt 的 `started_epoch_seconds`/`finalized_at_utc` 是
  wall-clock，只用于关联排序；时长正确性由 attempt 级 monotonic timeline
  （execution audit）承担，本视图不给出任何 duration 结论。
- **environment_package_digest**：receipt 不携带它；join 消费方拿本视图的
  task_id 走 `TrustedTaskController.verify_environment_package_digest`
  对锚（digest 贯穿纪律不变，只是不在这里复制）。

生产 producer（谁在何时调 derive）归 W1b 第一集成切片；本轮只收窄接口。
"""

from __future__ import annotations

from datetime import datetime

from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    RolloutAttemptOutcomeV2,
    TerminationKind,
)
from repoharness2.contracts.finalization import FinalizationReceiptV1


class TerminationFactsError(ValueError):
    """派生输入不满足唯一归属约束（缺 attempt 身份 / 缺 outcome 权威 /
    receipt 与 outcome 身份错接）时 fail-closed。"""


class TerminationFactsView:
    """一次 physical attempt 的终止事实只读视图（无独立存储，全部派生）。

    不可变性：`__slots__` 只存对 receipt 的引用，无公开 setter；底层
    `FinalizationReceiptV1`/`RolloutAttemptOutcomeV2` 本身是 frozen
    StrictModel。构造只经 `derive_termination_facts`。
    """

    __slots__ = ("_receipt",)

    def __init__(self, receipt: FinalizationReceiptV1) -> None:
        # 唯一归属校验（F5 验收面）：
        # 1) receipt 必须带 physical_attempt_id（终止事实必须锚到一次物理执行）；
        # 2) receipt 必须内嵌 outcome_v2（termination_kind 的唯一权威）；
        # 3) 两者的 attempt 身份必须逐字一致（错 attempt 的 receipt/outcome
        #    拼装在此拒绝，不产出可用视图）。
        pa = receipt.physical_attempt_id
        if not isinstance(pa, str) or not pa:
            raise TerminationFactsError(
                "receipt 缺 physical_attempt_id——终止事实必须唯一归属到一次"
                "物理执行，fail-closed。"
            )
        outcome = receipt.outcome_v2
        if outcome is None:
            raise TerminationFactsError(
                f"{pa}: receipt 未内嵌 outcome_v2——termination_kind 的权威"
                "缺失，不得由调用方另行填写，fail-closed。"
            )
        opa = outcome.identity.physical_attempt_id
        if opa != pa:
            raise TerminationFactsError(
                f"receipt.physical_attempt_id={pa!r} 与 outcome.identity."
                f"physical_attempt_id={opa!r} 不一致——错 attempt 的事实拼装，"
                "fail-closed。"
            )
        self._receipt = receipt

    # ------------------------------------------------------------- 身份锚
    @property
    def physical_attempt_id(self) -> str:
        return self._receipt.physical_attempt_id  # type: ignore[return-value]

    @property
    def task_id(self) -> str:
        return self._receipt.task_id

    @property
    def trajectory_id(self) -> str:
        return self._receipt.trajectory_id

    @property
    def outcome(self) -> RolloutAttemptOutcomeV2:
        """底层权威对象（frozen）；引用其 outcome_id/eligibility_report_id
        等即是 F5 要求的 exact ref。"""
        return self._receipt.outcome_v2  # type: ignore[return-value]

    @property
    def receipt_id(self) -> str:
        return self._receipt.receipt_id

    # --------------------------------------------------------- 终止事实（派生）
    @property
    def termination_kind(self) -> TerminationKind:
        return self.outcome.termination_kind

    @property
    def triggered_by_policy_horizon(self) -> bool:
        return self.outcome.termination_kind in TERMINATION_KINDS_POLICY_HORIZON

    @property
    def triggered_by_hard_wall(self) -> bool:
        return self.outcome.termination_kind in TERMINATION_KINDS_WATCHDOG

    @property
    def execution_scope_quiescent(self) -> bool:
        return self._receipt.runtime_quiescence_confirmed

    @property
    def canonical_frozen_patch_formed(self) -> bool:
        return self._receipt.frozen_patch_digest is not None

    @property
    def fresh_grading_complete(self) -> bool:
        return self._receipt.grading_report_id is not None

    @property
    def grading_report_id(self) -> str | None:
        return self._receipt.grading_report_id

    @property
    def eligibility_report_id(self) -> str | None:
        return self._receipt.eligibility_report_id

    # ------------------------------------------------- wall-clock（仅关联用）
    @property
    def started_epoch_seconds(self) -> float:
        """wall-clock 起点，只用于跨记录关联/排序——不承担时长正确性
        （monotonic 时长归 execution audit timeline）。"""
        return self._receipt.started_epoch_seconds

    @property
    def finalized_at_utc(self) -> datetime:
        """wall-clock 终点，同上只用于关联。"""
        return self._receipt.finalized_at_utc


def derive_termination_facts(receipt: FinalizationReceiptV1) -> TerminationFactsView:
    """唯一构造入口：从既有 finalization 权威派生只读终止事实视图。"""

    return TerminationFactsView(receipt)


__all__ = [
    "TerminationFactsError",
    "TerminationFactsView",
    "derive_termination_facts",
]
