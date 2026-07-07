"""EligibilityReport：训练资格三档 + 七维事实 sidecar（设计文档 2 §5.6 载体定案）。

载体规则（§5.6"载体与执行位置"）：

1. 权威载体是本模块的 typed sidecar `EligibilityReport`，与 Trace/Sample 以
   trajectory_id 同键存储——不塞 Trace.info，不改任何框架的 wire schema。
2. 宿主对象（Trace.info / Sample.metadata）只允许写两个白名单派生视图键：
   `eligibility_report_ref` 与 `training_eligibility_class`。本报告用
   `derived_view_report_ref` / `derived_view_class` 两个字段声明派生视图
   **应该**是什么，inspector 互检派生视图与 sidecar，不一致即 fail-closed
   （继承 R2"原始事实层 + 派生视图 + 互检"规则）。

七维事实：重定位文档 §16.1 列了 8 条硬门槛，本契约把第 5 条（hidden verifier
未泄漏）与第 7 条（权限与篡改检查）合并为 security_and_leakage 一维（两者同属
反作弊/泄漏安全面，且都由 findings/anti_hack/投影扫描供事实），得到 S1 计划口径的
"七维事实合取"。映射关系：

  1. token_provenance     <- §16.1 条 1（token 出处完整）
  2. logprob_alignment    <- §16.1 条 2（逐 token logprob 对齐）
  3. loss_mask_integrity  <- §16.1 条 3（loss mask 可解释，H4）
  4. reward_scope         <- §16.1 条 4（reward 作用域清楚，§16.11）
  5. security_and_leakage <- §16.1 条 5 + 条 7（泄漏 / 权限 / 篡改，executed 级）
  6. clean_grading        <- §16.1 条 6（clean checkout 重放评分成立）
  7. policy_staleness     <- §16.1 条 8（staleness 在阈值内，事实来自 handshake）
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import (
    NonEmptyStr,
    SafeIdentifier,
    Sha256Digest,
    StrictModel,
    canonical_json_digest,
)

TrainingEligibilityClass = Literal[
    "online_policy_loss_eligible",  # 七维全过，可进 online policy loss
    "offline_or_sft_candidate",  # 有 warm-start/SFT/分析价值，但不够 online 门槛（S1 全程的上限档）
    "audit_only_or_rejected",  # 只可审计或直接丢弃，禁止进入任何训练
]


class DimensionFact(StrictModel):
    """单个资格维度的事实结论（gate 只消费 facts，自己不生产事实）。

    fail-closed 行为：ok=False 必须携带至少一个 reason_code——
    "无理由的失败"不可表示，保证每次降级都可审计、可复盘。
    """

    ok: bool = Field(description="该维度是否通过。")
    reason_codes: list[SafeIdentifier] = Field(
        default_factory=list,
        description="失败/降级理由码（安全标识符，如 logprob_missing、staleness_exceeded）。ok=False 时必填。",
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list,
        description="支撑该结论的 evidence 引用（GradingReport.report_id、finding_id、扫描报告等）。",
    )

    @model_validator(mode="after")
    def _check_reason_on_failure(self) -> "DimensionFact":
        if not self.ok and not self.reason_codes:
            raise ValueError(
                "维度失败（ok=False）时 reason_codes 不得为空（fail-closed：无理由的失败不可审计）。"
            )
        return self


class EligibilityFacts(StrictModel):
    """七维资格事实的集合（gate 合取的输入，`facts_digest` 的计算对象）。"""

    token_provenance: DimensionFact = Field(
        description="维度 1：response token 全部来自行为策略真实采样（capture 链路完整可回链）。"
    )
    logprob_alignment: DimensionFact = Field(
        description="维度 2：逐 token logprob 与采样 token 对齐（缺失/错位即失败）。"
    )
    loss_mask_integrity: DimensionFact = Field(
        description="维度 3：loss mask 语义成立（H4：mask=1 仅覆盖 sampled ∧ role 允许的 token）。"
    )
    reward_scope: DimensionFact = Field(
        description="维度 4：reward 作用域与信用分配明确（scope=unknown/矛盾即失败，§16.11）。"
    )
    security_and_leakage: DimensionFact = Field(
        description=(
            "维度 5：安全与泄漏（§16.1 条 5+7 合并）。executed 级泄漏/篡改/权限违规即失败；"
            "attempted_blocked（拦截成功）不扣本维——agent 学到\"此路不通\"是合法训练信号。"
        )
    )
    clean_grading: DimensionFact = Field(
        description="维度 6：评分来自 clean checkout 重放 cleaned patch（infra_failure/hygiene 拒绝即失败）。"
    )
    policy_staleness: DimensionFact = Field(
        description="维度 7：policy staleness 在阈值内（事实来自 BackendHandshake）。"
    )

    def all_ok(self) -> bool:
        """七维是否全部通过（gate 的合取语义）。"""

        return all(
            fact.ok
            for fact in (
                self.token_provenance,
                self.logprob_alignment,
                self.loss_mask_integrity,
                self.reward_scope,
                self.security_and_leakage,
                self.clean_grading,
                self.policy_staleness,
            )
        )


def compute_facts_digest(facts: EligibilityFacts) -> str:
    """对七维事实计算规范化 digest（EligibilityReport.facts_digest 的唯一算法）。

    inspector 用同一函数重算比对——digest 对不上说明事实或结论被事后改动，fail-closed。
    """

    return canonical_json_digest(facts.model_dump(mode="json"))


class EligibilityReport(StrictModel):
    """训练资格报告 sidecar（gate 的唯一输出载体，样本进任何训练后端 adapter 前必经）。

    创建者：TrainingEligibilityGate（S1-5，wrapper 是唯一入口）。
    消费者：slime 绑定（决定样本去留与组修复信号）、离线导出 adapter、
    inspect-rh2-artifact、parity 校验。

    fail-closed 校验清单：
    1. facts_digest 必须等于 compute_facts_digest(facts) 的重算值；
    2. eligibility_class=online_policy_loss_eligible 要求七维全部 ok；
    3. security_and_leakage 失败时结论必须是 audit_only_or_rejected
       （executed 级泄漏内容已进模型上下文，连 SFT 候选都会污染——从严取舍）；
    4. 结论不是 online 档时 reason_codes 必须非空（包括 S1 的默认封顶：
       全过也要写 s1_default_ceiling_offline 这类理由码，显式可审计）；
    5. 派生视图字段必须与本报告自身一致（report_ref==report_id，class==结论）。
    """

    schema_id: Literal["rh2.eligibility_report.v1"] = Field(
        default="rh2.eligibility_report.v1", description="schema 判别字段。"
    )
    report_id: NonEmptyStr = Field(description="报告 id（宿主派生视图 eligibility_report_ref 指向它）。")
    trajectory_id: NonEmptyStr = Field(description="被评估轨迹 id（与 sidecar 同键存储）。")
    branch_id: NonEmptyStr | None = Field(
        default=None, description="被评估分支 id（None 表示整条轨迹级结论）。"
    )
    gate_version: NonEmptyStr = Field(
        description="gate 实现版本（§16.11 eligibility_gate_version；升级 gate 必须换版本号）。"
    )
    facts: EligibilityFacts = Field(description="七维事实（原始事实层）。")
    facts_digest: Sha256Digest = Field(
        description="facts 的规范化 digest（compute_facts_digest 计算，inspector 重算比对）。"
    )
    eligibility_class: TrainingEligibilityClass = Field(description="三档资格结论。")
    reason_codes: list[SafeIdentifier] = Field(
        default_factory=list,
        description="结论级理由码。非 online 结论必须至少一条（含 S1 默认封顶的显式声明）。",
    )
    derived_view_report_ref: NonEmptyStr = Field(
        description="宿主对象派生视图应写入的 eligibility_report_ref 值（必须 == report_id，互检用）。"
    )
    derived_view_class: TrainingEligibilityClass = Field(
        description="宿主对象派生视图应写入的 training_eligibility_class 值（必须 == eligibility_class，互检用）。"
    )
    created_at_utc: AwareDatetime = Field(description="报告生成时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_report_contract(self) -> "EligibilityReport":
        # 1. digest 重算互检
        expected_digest = compute_facts_digest(self.facts)
        if self.facts_digest != expected_digest:
            raise ValueError(
                f"facts_digest 与重算值不符：声明 {self.facts_digest}，重算 {expected_digest}"
                "（事实或 digest 被改动过，fail-closed 拒收）。"
            )
        # 2. online 档要求七维全过
        if self.eligibility_class == "online_policy_loss_eligible" and not self.facts.all_ok():
            failed = [
                name
                for name, fact in (
                    ("token_provenance", self.facts.token_provenance),
                    ("logprob_alignment", self.facts.logprob_alignment),
                    ("loss_mask_integrity", self.facts.loss_mask_integrity),
                    ("reward_scope", self.facts.reward_scope),
                    ("security_and_leakage", self.facts.security_and_leakage),
                    ("clean_grading", self.facts.clean_grading),
                    ("policy_staleness", self.facts.policy_staleness),
                )
                if not fact.ok
            ]
            raise ValueError(
                f"eligibility_class=online_policy_loss_eligible 但以下维度未通过：{failed}"
                "（七维合取：任一失败即降级）。"
            )
        # 3. executed 级安全失败必须落 audit 档
        if not self.facts.security_and_leakage.ok and self.eligibility_class != "audit_only_or_rejected":
            raise ValueError(
                "security_and_leakage 失败时结论必须是 audit_only_or_rejected："
                "executed 级泄漏内容已进入模型上下文，作为 SFT/离线候选同样会污染数据（从严）。"
            )
        # 4. 非 online 结论必须给理由
        if self.eligibility_class != "online_policy_loss_eligible" and not self.reason_codes:
            raise ValueError(
                "非 online 档结论必须携带 reason_codes（例如 S1 默认封顶要写 "
                "s1_default_ceiling_offline），降级不可无理由。"
            )
        # 5. 派生视图互检
        if self.derived_view_report_ref != self.report_id:
            raise ValueError(
                f"derived_view_report_ref({self.derived_view_report_ref}) 必须等于 "
                f"report_id({self.report_id})（派生视图与 sidecar 互检）。"
            )
        if self.derived_view_class != self.eligibility_class:
            raise ValueError(
                f"derived_view_class({self.derived_view_class}) 必须等于 "
                f"eligibility_class({self.eligibility_class})（派生视图与 sidecar 互检）。"
            )
        return self

    @classmethod
    def finalize(
        cls,
        *,
        report_id: str,
        trajectory_id: str,
        gate_version: str,
        facts: EligibilityFacts,
        eligibility_class: TrainingEligibilityClass,
        reason_codes: list[str],
        created_at_utc: object,
        branch_id: str | None = None,
    ) -> "EligibilityReport":
        """gate 侧的便捷构造器：自动计算 facts_digest 并填好派生视图字段。

        注意：这只是省去手工抄写自证字段；校验器仍会独立重算 digest，
        绕过本方法手工构造的对象接受完全相同的检查。
        """

        return cls(
            report_id=report_id,
            trajectory_id=trajectory_id,
            branch_id=branch_id,
            gate_version=gate_version,
            facts=facts,
            facts_digest=compute_facts_digest(facts),
            eligibility_class=eligibility_class,
            reason_codes=reason_codes,
            derived_view_report_ref=report_id,
            derived_view_class=eligibility_class,
            created_at_utc=created_at_utc,
        )
