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

W1b 第一集成切片（F5）接线：producer = `adapters/slime/generate.py` 在 finalization
receipt 持久化成功之后立刻 `termination_facts_payload(receipt)`（内部走
`derive_termination_facts`，fail-closed），把 `TerminationFactsPayloadV1` 以
`rh2_termination_facts` 键盖到本次交付的全部样本 metadata 上（`stamp_termination_facts`）。
消费侧（第二段的复合 filter）用 `resolve_termination_facts(sample.metadata)` 取回并与
样本自身的 attempt/execution 身份逐字核对；`assert_payload_dereferences` 钉死"一个事实
只能解引用到唯一 receipt/outcome"。载荷字段全部是派生事实，**无任何 disposition/
admission/reward/mask 字段**（导入期断言）。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from repoharness2.contracts._base import NonEmptyStr, StrictModel
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
        # 4) 账实一致（二轮复核 + 快速复核修正为严格对称）：receipt 与 outcome
        #    各自携带的 eligibility 引用必须**逐字相等**（含双方都为 None）。
        #    生产链两者同源（generate.py 的 receipt 与 outcome 都取
        #    audit.finalized.eligibility_report.report_id，或同为 None），任何
        #    不对称都是账实矛盾——不区分方向。
        rer, oer = receipt.eligibility_report_id, outcome.eligibility_report_id
        if rer != oer:
            raise TerminationFactsError(
                f"{pa}: receipt.eligibility_report_id={rer!r} 与 outcome."
                f"eligibility_report_id={oer!r} 不一致——账实矛盾，fail-closed。"
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
        """底层权威对象的**深拷贝**（二轮复核：frozen 只挡字段重赋值，直接
        交出共享对象会让调用方改其嵌套 list 反向污染 receipt）；引用其
        outcome_id/eligibility_report_id 等即是 F5 要求的 exact ref。"""
        return self._receipt.outcome_v2.model_copy(deep=True)  # type: ignore[union-attr]

    @property
    def outcome_id(self) -> str:
        return self._receipt.outcome_v2.outcome_id  # type: ignore[union-attr]

    @property
    def receipt_id(self) -> str:
        return self._receipt.receipt_id

    # --------------------------------------------------------- 终止事实（派生）
    @property
    def termination_kind(self) -> TerminationKind:
        return self._receipt.outcome_v2.termination_kind  # type: ignore[union-attr]

    @property
    def triggered_by_policy_horizon(self) -> bool:
        return self.termination_kind in TERMINATION_KINDS_POLICY_HORIZON

    @property
    def triggered_by_hard_wall(self) -> bool:
        return self.termination_kind in TERMINATION_KINDS_WATCHDOG

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


# ---------------------------------------------------------------------------
# W1b 第一集成切片（F5）：交付面的中立事实载荷 + producer / consumer 边界
# ---------------------------------------------------------------------------

# 交付样本 metadata 上的落点键（系统保留前缀 rh2_；值 = TerminationFactsPayloadV1 的 JSON dump）。
TERMINATION_FACTS_METADATA_KEY = "rh2_termination_facts"
# 与 generate.py / adapters/miles/identity.py 逐字一致的两个身份键（envpack 不 import adapters，字面量钉死）。
_ATTEMPT_ID_KEY = "rh2_physical_attempt_id"
_EXECUTION_ID_KEY = "rh2_rollout_execution_id"

# 中立性词根黑名单（W2a 纪律）：载荷字段名不许含任何处置/准入/奖励/mask/训练语义。
_NON_NEUTRAL_ROOTS = ("disposition", "admission", "reward", "mask", "train", "penal", "sample", "keep", "drop")


class TerminationFactsPayloadV1(StrictModel):
    """交付面载荷：`TerminationFactsView` 的可序列化投影。

    全部字段派生自 receipt/outcome（构造只经 `termination_facts_payload`），没有任何可独立
    注入的处置字段；以 physical_attempt_id 为键，receipt_id/outcome_id 为解引用锚。
    """

    schema_id: Literal["rh2.termination_facts_payload.v1"] = Field(default="rh2.termination_facts_payload.v1")
    physical_attempt_id: NonEmptyStr
    rollout_execution_id: NonEmptyStr = Field(
        description="receipt.trajectory_id（= 六字段身份的 rh2_rollout_execution_id）。"
    )
    task_id: NonEmptyStr
    receipt_id: NonEmptyStr
    outcome_id: NonEmptyStr
    termination_kind: TerminationKind
    triggered_by_policy_horizon: bool
    triggered_by_hard_wall: bool
    execution_scope_quiescent: bool
    canonical_frozen_patch_formed: bool
    fresh_grading_complete: bool
    grading_report_id: str | None = None
    eligibility_report_id: str | None = None

    @model_validator(mode="after")
    def _check_derivation_consistency(self) -> "TerminationFactsPayloadV1":
        # 派生关系在模型层不可矛盾（与 W2a 原 TerminationFactsV1 的 validator 同义务）。
        if self.triggered_by_policy_horizon != (self.termination_kind in TERMINATION_KINDS_POLICY_HORIZON):
            raise ValueError("triggered_by_policy_horizon 与 termination_kind 五族划分矛盾")
        if self.triggered_by_hard_wall != (self.termination_kind in TERMINATION_KINDS_WATCHDOG):
            raise ValueError("triggered_by_hard_wall 与 termination_kind 五族划分矛盾")
        if self.fresh_grading_complete != (self.grading_report_id is not None):
            raise ValueError("fresh_grading_complete 与 grading_report_id 在场性矛盾")
        return self


assert not any(
    root in name for name in TerminationFactsPayloadV1.model_fields for root in _NON_NEUTRAL_ROOTS
), "TerminationFactsPayloadV1 字段名带处置/准入词根——载荷中立性被破坏"


def termination_facts_payload(receipt: FinalizationReceiptV1) -> TerminationFactsPayloadV1:
    """producer 唯一入口：receipt → 只读视图（fail-closed 派生）→ 可序列化载荷。"""

    facts = derive_termination_facts(receipt)
    return TerminationFactsPayloadV1(
        physical_attempt_id=facts.physical_attempt_id,
        rollout_execution_id=facts.trajectory_id,
        task_id=facts.task_id,
        receipt_id=facts.receipt_id,
        outcome_id=facts.outcome_id,
        termination_kind=facts.termination_kind,
        triggered_by_policy_horizon=facts.triggered_by_policy_horizon,
        triggered_by_hard_wall=facts.triggered_by_hard_wall,
        execution_scope_quiescent=facts.execution_scope_quiescent,
        canonical_frozen_patch_formed=facts.canonical_frozen_patch_formed,
        fresh_grading_complete=facts.fresh_grading_complete,
        grading_report_id=facts.grading_report_id,
        eligibility_report_id=facts.eligibility_report_id,
    )


def assert_payload_dereferences(payload: TerminationFactsPayloadV1, receipt: FinalizationReceiptV1) -> None:
    """一个 termination 事实只能解引用到唯一 outcome/receipt：四个锚必须逐字相等。"""

    if receipt.outcome_v2 is None:
        raise TerminationFactsError(f"{receipt.receipt_id}: receipt 无 outcome_v2——载荷无法解引用到 outcome，fail-closed。")
    pairs = (
        ("physical_attempt_id", payload.physical_attempt_id, receipt.physical_attempt_id),
        ("receipt_id", payload.receipt_id, receipt.receipt_id),
        ("outcome_id", payload.outcome_id, receipt.outcome_v2.outcome_id),
        ("rollout_execution_id", payload.rollout_execution_id, receipt.trajectory_id),
    )
    for label, mine, theirs in pairs:
        if mine != theirs:
            raise TerminationFactsError(
                f"载荷 {label}={mine!r} 与 receipt 的 {theirs!r} 不一致——事实解引用到别的 attempt/receipt，fail-closed。"
            )


def stamp_termination_facts(output: Any, payload: TerminationFactsPayloadV1) -> None:
    """producer 落点：把载荷盖到本次交付的全部叶（list 递归，形状不改）。

    规则：
    - 叶上已带六字段身份时，attempt/execution 必须与载荷一致（错 attempt / 错 trajectory 拒绝）；
    - 叶上已带**不同**载荷：唯一放行的情形是"同一样本对象的上一次 attempt 留下的历史"
      （miles reset_for_retry 保留 metadata；识别依据 = 叶自身 attempt 身份已经是本次 attempt，
      而旧载荷的 attempt 是别的 id）——其余一律视为 fan-out 叶伪造/串入别的 attempt，拒绝。
    """

    if isinstance(output, list):
        for item in output:
            stamp_termination_facts(item, payload)
        return
    meta = getattr(output, "metadata", None)
    if not isinstance(meta, dict):
        raise TerminationFactsError(
            f"交付样本 metadata 不是 dict（得到 {type(meta).__name__}）——事实载荷无处安放，fail-closed。"
        )
    own_attempt = meta.get(_ATTEMPT_ID_KEY)
    if own_attempt is not None and own_attempt != payload.physical_attempt_id:
        raise TerminationFactsError(
            f"交付叶 attempt {own_attempt!r} 与事实载荷 attempt {payload.physical_attempt_id!r} 不一致——错 attempt，fail-closed。"
        )
    own_execution = meta.get(_EXECUTION_ID_KEY)
    if own_execution is not None and own_execution != payload.rollout_execution_id:
        raise TerminationFactsError(
            f"交付叶 execution {own_execution!r} 与事实载荷 execution {payload.rollout_execution_id!r} 不一致"
            "——错 trajectory，fail-closed。"
        )
    new = payload.model_dump(mode="json")
    existing = meta.get(TERMINATION_FACTS_METADATA_KEY)
    if existing is not None and existing != new:
        stale_retry_history = (
            isinstance(existing, Mapping)
            and own_attempt == payload.physical_attempt_id
            and existing.get("physical_attempt_id") != payload.physical_attempt_id
        )
        if not stale_retry_history:
            raise TerminationFactsError(
                "交付叶已带不同的 termination 事实载荷——fan-out 叶伪造/串入别的 attempt 的事实，fail-closed。"
            )
    meta[TERMINATION_FACTS_METADATA_KEY] = new


def resolve_termination_facts(sample_metadata: Any) -> TerminationFactsPayloadV1:
    """consumer 侧 join：从样本 metadata 解出载荷，并与样本自身 attempt/execution 身份逐字核对。

    拒绝面（F5 五类反例）：同题 n=8 sibling 的事实、同 member 旧 retry attempt 的事实、
    fan-out 叶各自声称的不同 attempt、错 attempt、错 trajectory——都在 attempt/execution
    两个比对上 fail-closed。
    """

    if not isinstance(sample_metadata, Mapping):
        raise TerminationFactsError("样本 metadata 不是 Mapping——无 termination 事实可 join，fail-closed。")
    raw = sample_metadata.get(TERMINATION_FACTS_METADATA_KEY)
    if raw is None:
        raise TerminationFactsError(
            f"样本没有 termination 事实载荷（{TERMINATION_FACTS_METADATA_KEY} 缺失）——不可 join，fail-closed。"
        )
    try:
        payload = TerminationFactsPayloadV1.model_validate(raw)
    except ValidationError as exc:
        raise TerminationFactsError(f"termination 事实载荷非法：{exc}") from exc
    attempt = sample_metadata.get(_ATTEMPT_ID_KEY)
    if not attempt:
        raise TerminationFactsError("样本没有 rh2_physical_attempt_id——事实无法归属到样本自身的 attempt，fail-closed。")
    if attempt != payload.physical_attempt_id:
        raise TerminationFactsError(
            f"样本 attempt {attempt!r} 与载荷 attempt {payload.physical_attempt_id!r} 不一致"
            "——同题 sibling / 旧 retry attempt / 错 attempt 的事实，拒绝 join。"
        )
    execution = sample_metadata.get(_EXECUTION_ID_KEY)
    if not execution:
        raise TerminationFactsError("样本没有 rh2_rollout_execution_id——事实无法归属到样本自身的 trajectory，fail-closed。")
    if execution != payload.rollout_execution_id:
        raise TerminationFactsError(
            f"样本 execution {execution!r} 与载荷 execution {payload.rollout_execution_id!r} 不一致——错 trajectory，拒绝 join。"
        )
    return payload


__all__ = [
    "TERMINATION_FACTS_METADATA_KEY",
    "TerminationFactsError",
    "TerminationFactsPayloadV1",
    "TerminationFactsView",
    "assert_payload_dereferences",
    "derive_termination_facts",
    "resolve_termination_facts",
    "stamp_termination_facts",
    "termination_facts_payload",
]
