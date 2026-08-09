"""F2-1b：RolloutAttemptOutcome v1→v2 crosswalk 与双版本读取。

定位（05 计划 F2-1b 节 + 决策包聚焦复核 4）：

- **正式链只生产 v2**——本模块只服务两件事：读历史 v1 账目（双版本
  读取）、把 v1 迁移成 v2 供统一消费（能迁则迁，不能迁标
  legacy_unmappable 留在审计面）。
- **迁移不捏造事实**。v1 的 `present` 分不出 present_complete /
  present_truncated（v1 时代没有 termination_kind 记录）；v1 的
  `permanent_rejection` 混合了执行事实与准入判定。两者都需要调用方
  提供**从原始 evidence（audit/timeline）重建的终止证据**才能迁移；
  没有证据 → legacy_unmappable（v1 记录仍可经双版本读取原样使用，
  只是不得进入 v2 消费链）。
- **permanent_rejection 永不默认映射成 missing**（聚焦复核 4 钉死）：
  它的语义是"事实完整 + 禁止训练"——映射成 missing 会把"完整但被禁"
  伪造成"没产生"，抹掉安全事件的存在性。可迁移时落为 present_*，
  "禁止训练"以 `legacy_admission_verdict` 随结果传递（准入判定不进
  v2 事实层——正式链由 PromptGroupAdmissionReport 承载）。

规则表穷举（v1.completion_class × 证据）——测试以集合等式验证全覆盖：

    present             + 无证据            → legacy_unmappable
    present             + completed         → migrated present_complete
    present             + horizon/看门狗/控制面 → migrated present_truncated
    present             + infra 族          → legacy_unmappable（证据矛盾：
                                              infra ⇒ missing，与 v1 present 冲突）
    missing_after_local_retry + 无证据       → legacy_unmappable（v2 必填
                                              termination_kind，不许猜）
    missing_after_local_retry + 任意族       → migrated missing（任何终止后
                                              账目都可能不完整；三层钉子矛盾除外）
    permanent_rejection + 无证据            → legacy_unmappable
    permanent_rejection + completed         → migrated present_complete + verdict
    permanent_rejection + horizon/看门狗/控制面 → migrated present_truncated + verdict
    permanent_rejection + infra 族          → legacy_unmappable（infra ⇒ 事实
                                              不完整，与"事实完整才可能被永久拒绝"矛盾）

present 族迁移还要求 v1 记录携带完整 present 事实字段
（turn_weight_versions/current_version_at_finalize/eligibility_report_id
——v1 present 的 validator 本就保证；permanent_rejection 记录若缺失 =
"无法由原始 evidence 重建" → legacy_unmappable）。
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import Field

from ._base import NonEmptyStr, StrictModel
from .fa_runtime import (
    TERMINATION_KINDS_CONTROL,
    TERMINATION_KINDS_INFRA,
    TERMINATION_KINDS_NORMAL,
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    RolloutAttemptOutcome,
    RolloutAttemptOutcomeV2,
    TerminationKind,
)

__all__ = [
    "OutcomeCrosswalkResult",
    "V1TerminationEvidence",
    "crosswalk_v1_to_v2",
    "read_rollout_attempt_outcome",
]

_TRUNCATION_KINDS = (
    TERMINATION_KINDS_POLICY_HORIZON | TERMINATION_KINDS_WATCHDOG | TERMINATION_KINDS_CONTROL
)


class V1TerminationEvidence(StrictModel):
    """从原始 evidence 重建的终止证据（调用方从 audit/timeline 读出）。

    termination_kind 必须是重建出的**事实**，不是猜测——没有证据就不要
    构造本对象（传 None 走 legacy_unmappable）。
    """

    termination_kind: TerminationKind = Field(description="重建出的终止 trigger。")
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="重建依据（audit record / timeline 等引用）。"
    )


class OutcomeCrosswalkResult(StrictModel):
    """crosswalk 结果：migrated（携带 v2）或 legacy_unmappable（审计面保留 v1）。"""

    status: Literal["migrated", "legacy_unmappable"] = Field(description="迁移结果。")
    v1_outcome_id: NonEmptyStr = Field(description="源 v1 记录 id（审计回链）。")
    rule: NonEmptyStr = Field(description="命中的规则名（穷举表行，测试锚点）。")
    v2: RolloutAttemptOutcomeV2 | None = Field(
        default=None, description="迁移产物（status=migrated 时必在，否则必空）。"
    )
    legacy_admission_verdict: Literal["permanent_rejection"] | None = Field(
        default=None,
        description=(
            "v1 永久拒绝的准入判定传递（审计信息，不进 v2 事实层）——"
            "消费方必须继续视为禁止训练。"
        ),
    )
    legacy_failure_category: NonEmptyStr | None = Field(
        default=None,
        description="v1 permanent_rejection 携带的原始归因（security_violation 等），审计保留。",
    )
    reason: NonEmptyStr = Field(description="人读说明（为何迁移成功/失败）。")


def _result(
    v1: RolloutAttemptOutcome,
    *,
    status: Literal["migrated", "legacy_unmappable"],
    rule: str,
    reason: str,
    v2: RolloutAttemptOutcomeV2 | None = None,
    verdict: Literal["permanent_rejection"] | None = None,
    legacy_fc: str | None = None,
) -> OutcomeCrosswalkResult:
    return OutcomeCrosswalkResult(
        status=status, v1_outcome_id=v1.outcome_id, rule=rule, reason=reason,
        v2=v2, legacy_admission_verdict=verdict, legacy_failure_category=legacy_fc,
    )


def _build_present_v2(
    v1: RolloutAttemptOutcome,
    evidence: V1TerminationEvidence,
    completion: Literal["present_complete", "present_truncated"],
    *,
    banned: bool,
) -> RolloutAttemptOutcomeV2:
    # permanent_rejection 源记录：task_outcome=unknown（v1 validator 强制），
    # v2 侧对应 reward_unavailable=True；present 源记录照搬评分结局。
    reward_unavailable = v1.task_outcome == "unknown"
    return RolloutAttemptOutcomeV2(
        outcome_id=f"{v1.outcome_id}::v2migrated",
        identity=v1.identity,
        member_slot=v1.member_slot,
        attempt_number=v1.attempt_number,
        completion_class=completion,
        termination_kind=evidence.termination_kind,
        # 事实层：执行没有失败；banned 源的归因（security_violation 等）
        # 是准入判定材料，随 OutcomeCrosswalkResult.legacy_failure_category
        # 走审计面，不进 v2
        failure_category=None,
        reason_code=None,
        failed_component=None if banned else v1.failed_component,
        recovery_scope=v1.recovery_scope,
        task_outcome=v1.task_outcome,
        reward_unavailable=reward_unavailable,
        turn_weight_versions=list(v1.turn_weight_versions),
        intra_execution_version_span=v1.intra_execution_version_span,
        current_version_at_finalize=v1.current_version_at_finalize,
        eligibility_report_id=v1.eligibility_report_id,
        evidence_refs=[*v1.evidence_refs, *evidence.evidence_refs],
    )


def crosswalk_v1_to_v2(
    v1: RolloutAttemptOutcome,
    evidence: V1TerminationEvidence | None = None,
) -> OutcomeCrosswalkResult:
    """把一条 v1 记录迁移为 v2；证据不足或矛盾时 legacy_unmappable。

    穷举规则表见模块 docstring；每个返回都带 `rule` 锚点供集合等式测试。
    """

    cc = v1.completion_class

    if cc == "present":
        if evidence is None:
            return _result(
                v1, status="legacy_unmappable", rule="present_no_evidence",
                reason="v1 present 区分不出 complete/truncated，无终止证据不得捏造。",
            )
        tk = evidence.termination_kind
        if tk in TERMINATION_KINDS_NORMAL:
            return _result(
                v1, status="migrated", rule="present_completed",
                reason="正常终止 + v1 present 事实完整 → present_complete。",
                v2=_build_present_v2(v1, evidence, "present_complete", banned=False),
            )
        if tk in _TRUNCATION_KINDS:
            return _result(
                v1, status="migrated", rule="present_truncated",
                reason=f"{tk} 截断 + v1 present 事实完整 → present_truncated。",
                v2=_build_present_v2(v1, evidence, "present_truncated", banned=False),
            )
        return _result(  # infra 族
            v1, status="legacy_unmappable", rule="present_infra_contradiction",
            reason=f"证据矛盾：{tk} 属基础设施族（⇒missing），与 v1 present 冲突。",
        )

    if cc == "missing_after_local_retry":
        if evidence is None:
            return _result(
                v1, status="legacy_unmappable", rule="missing_no_evidence",
                reason="v2 必填 termination_kind；v1 failure_category 到终止 trigger "
                       "的映射有歧义，不猜。",
            )
        tk = evidence.termination_kind
        if tk == "model_call_regeneration_exhausted" and (
            v1.failure_category != "model_proxy_failure"
        ):
            return _result(
                v1, status="legacy_unmappable", rule="missing_three_layer_contradiction",
                reason="重生成耗尽要求 failure_category=model_proxy_failure"
                       f"（v1 记录为 {v1.failure_category}），三层钉子矛盾。",
            )
        v2 = RolloutAttemptOutcomeV2(
            outcome_id=f"{v1.outcome_id}::v2migrated",
            identity=v1.identity,
            member_slot=v1.member_slot,
            attempt_number=v1.attempt_number,
            completion_class="missing",
            termination_kind=tk,
            failure_category=v1.failure_category,
            reason_code=(
                "max_regenerations_exceeded"
                if tk == "model_call_regeneration_exhausted" else None
            ),
            failed_component=v1.failed_component,
            recovery_scope=v1.recovery_scope,
            task_outcome="unknown",
            reward_unavailable=True,
            turn_weight_versions=list(v1.turn_weight_versions),
            intra_execution_version_span=v1.intra_execution_version_span,
            current_version_at_finalize=v1.current_version_at_finalize,
            evidence_refs=[*v1.evidence_refs, *evidence.evidence_refs],
        )
        return _result(
            v1, status="migrated", rule="missing_migrated",
            reason="缺员照迁（任何终止族之后账目都可能不完整）。", v2=v2,
        )

    # cc == "permanent_rejection"
    if evidence is None:
        return _result(
            v1, status="legacy_unmappable", rule="rejection_no_evidence",
            reason="permanent_rejection 禁止默认映射（尤其不得映射成 missing）；"
                   "无终止证据无法重建事实层。",
            verdict="permanent_rejection", legacy_fc=v1.failure_category,
        )
    tk = evidence.termination_kind
    if tk in TERMINATION_KINDS_INFRA:
        return _result(
            v1, status="legacy_unmappable", rule="rejection_infra_contradiction",
            reason=f"证据矛盾：{tk} ⇒ 事实不完整，而永久拒绝以事实完整为前提。",
            verdict="permanent_rejection", legacy_fc=v1.failure_category,
        )
    present_fields_ok = (
        bool(v1.turn_weight_versions)
        and v1.current_version_at_finalize is not None
        and v1.eligibility_report_id is not None
    )
    if not present_fields_ok:
        return _result(
            v1, status="legacy_unmappable", rule="rejection_facts_incomplete",
            reason="v1 记录缺 present 级事实字段（版本序列/finalize 版本/资格引用），"
                   "无法由原始 evidence 重建 present_*。",
            verdict="permanent_rejection", legacy_fc=v1.failure_category,
        )
    completion = (
        "present_complete" if tk in TERMINATION_KINDS_NORMAL else "present_truncated"
    )
    return _result(
        v1, status="migrated", rule=f"rejection_{completion}",
        reason="事实完整可重建 → 迁 present_*；禁止训练判定经 "
               "legacy_admission_verdict 传递（不进 v2 事实层）。",
        v2=_build_present_v2(v1, evidence, completion, banned=True),
        verdict="permanent_rejection", legacy_fc=v1.failure_category,
    )


def read_rollout_attempt_outcome(
    payload: dict,
) -> RolloutAttemptOutcome | RolloutAttemptOutcomeV2:
    """双版本读取：按 schema_id 分发 v1/v2；未知版本 fail-closed。"""

    schema_id = payload.get("schema_id")
    if schema_id == "rh2.fa.rollout_attempt_outcome.v1":
        return RolloutAttemptOutcome.model_validate(payload)
    if schema_id == "rh2.fa.rollout_attempt_outcome.v2":
        return RolloutAttemptOutcomeV2.model_validate(payload)
    raise ValueError(f"未知 rollout_attempt_outcome 版本：{schema_id!r}。")


# 穷举表自检锚点：TerminationKind 全集 = 五族并集且两两不交（D4 风格；
# 枚举加值而五族漏编时导入即炸，不等测试跑）。
_ALL_KINDS = frozenset(get_args(TerminationKind))
_FAMILIES = (
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    TERMINATION_KINDS_CONTROL,
    TERMINATION_KINDS_INFRA,
    TERMINATION_KINDS_NORMAL,
)
assert frozenset().union(*_FAMILIES) == _ALL_KINDS, "termination 五族并集 != 全集"
assert sum(len(f) for f in _FAMILIES) == len(_ALL_KINDS), "termination 五族存在交叠"
