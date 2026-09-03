"""TrainingEligibilityGate（S1-5）：七维事实合取 -> 三档资格 + 组修复信号。

职责边界（eligibility.py 是宪法，本模块是执行者不是重定义者）：

- gate **只消费上游事实、不生产事实**：capture 完成度来自
  `GenerationCaptureRecord`（步骤 4）、span/账目结论来自 `TrajectoryProjection`
  （步骤 7，schema 校验已在构造时执行）、评分与 hygiene 来自 `GradingReport`
  （步骤 6）、版本事实来自 `BackendHandshake`（步骤 9 的事实回填）、
  反作弊来自 `AntiCheatFinding`、反压来自 `grading.queue.BackpressureEvent`；
- gate 补的是 schema 看不见的**跨对象一致性**（例如投影申报 raw_reward=0.0
  而评分报告 reward=None 的"infra 伪装成负样本"形态，单个对象各自合法，
  对起账来才露馅）；
- 结论装配交给 `EligibilityReport.finalize()`，digest 重算 / online 合取 /
  security 强制 audit / 派生视图互检这五连锁由 schema 校验器再执行一遍
  （gate 层与 schema 层双保险）。

A3（06 计划 §1，D1 已批，2026-09-02 W1b 第二段落地）：**资格只由轨迹事实决定**
——七维全过自然得到 online。此前的 S1 全程封顶（`S1_TIER_CAP` /
`s1_default_ceiling_offline` / cap 应用分支）已整体删除。

Wave3 前置清理批（决策包 D2+B v2，owner 2026-09-04 已批）在此基础上再删三样：

- **D2-2 改判 A3 的实现机制**：W1b 第二段引入的每轨迹 `SandboxCapabilityFacts`
  证明系统（provider / required / `sandbox_capability_facts_missing` /
  `sandbox_capability_unverified_*` / lease 绑定 / `REQUIRED_SANDBOX_CAPABILITIES`
  必需集）整体删除——它把"容器创建器是否正确"变成"每条样本是否带证明"，先跑完
  昂贵 rollout 再 DROP_GROUP，补采还会重复失败。sandbox 合规改由 W3b 在创建期
  强制配置 + 启动前探针保证（不合即不启动/停 run），本 gate 不再逐轨迹消费任何
  sidecar。security 维回到"只判本次轨迹发生了影响 reward 可信的**执行级**事实"，
  `findings=()` 且 hygiene 干净即通过——这是预期，不是假过窗口。旧类型保留为冻结
  历史 schema（`governance/sandbox_capability_facts.py`），不进新 formal 链。
- **D2-4**：`TrajectoryProjection` 的 forbidden marker 扫描不再是 security 维的事实
  输入（`public_projection_marker_hit` 已删）——投影不是模型可见面，扫它测不到真实
  泄漏，只会因 `fail_to_pass_bonus` 这类字段名误报丢整组。真模型可见面
  （envpack 的 PublicTaskBundle / RolloutTaskView）的整树扫描原样保留。
- **B-1 改判 D1-4**：policy_staleness 维不再用 finalize-time 阈值做资格门
  （`staleness_exceeded` 已删）；改为"版本事实可用且合法"（`staleness_facts_missing`
  / `staleness_facts_invalid`），consume-time staleness 的唯一权威是 miles
  `DefaultDataBuffer.get()` + `--max-weight-staleness N`（W4 接线）。

三档结论的降级地板（_DIMENSION_DEGRADE_FLOOR，S1-5 定案）：

  维度失败只说明"不能进 online"，落到哪一档取决于失败摧毁的是什么——
  - token_provenance / logprob_alignment / policy_staleness 只摧毁
    on-policy 可用性（SFT 重新 tokenize、不看 logprob、不在乎新鲜度），
    地板 = offline_or_sft_candidate；
  - loss_mask_integrity（没有可训练 token / loss 账目对不上）、
    reward_scope（reward 缺失或账实不符，无法用于任何筛选）、
    clean_grading（评分结论本身不可信或 hygiene 被拒）、
    security_and_leakage（executed 级泄漏/篡改，schema 层同样锁死）
    摧毁的是样本作为**任何训练数据**的可信度，地板 = audit_only_or_rejected。
  多维失败取最严地板。具体数值例：infra_failure 评分（reward=None）同时
  触发 reward_scope（scope=none）与 clean_grading（grading_infra_failure）
  两维失败，两者地板都是 audit -> 结论 audit_only_or_rejected（P4：
  infra 绝不落 reward=0，样本降级出训练面）。

模块私有化（S1-5 纪律）：`_evaluate` 不进入 public API——S1-6 与一切编排
代码只准调 `governance.wrapper.finalize_rollout`（唯一关口，§5.6 定案 3/4），
tests/governance 的 API 面测试钉住这一点。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts import (
    AntiCheatFinding,
    BackendHandshake,
    DimensionFact,
    EligibilityFacts,
    EligibilityReport,
    GenerationCaptureRecord,
    GradingReport,
    NonEmptyStr,
    SafeIdentifier,
    StrictModel,
    TrainingEligibilityClass,
    TrajectoryProjection,
)
from repoharness2.grading.queue import BackpressureEvent

__all__ = [
    "GATE_VERSION",
    "GateInputError",
    "GroupRepairSignal",
    "GateOutcome",
]

# gate 实现版本（§16.11 eligibility_gate_version）：改判定逻辑必须升版本号，
# 让两份不同逻辑产出的 EligibilityReport 永远可区分。这是**被动版本号**
# （机械升版），不是任何解锁/闸门（06 计划 A3）。
# 版本史：rh2.gate.s1.v1 = S1 封顶时代；rh2.gate.w1b.v2 = A3 落地
# （删 S1_TIER_CAP + security 维要求正向 sandbox 能力事实）；
# rh2.gate.w3pre.v3 = Wave3 前置清理批（删每轨迹能力事实 / 删 projection 扫描
# 资格语义 / policy_staleness 改"版本事实可用且合法"，决策包 D2+B v2）。
GATE_VERSION = "rh2.gate.w3pre.v3"

# 三档严重度：数值越小越受限。min() 取最严。
_CLASS_SEVERITY: dict[TrainingEligibilityClass, int] = {
    "audit_only_or_rejected": 0,
    "offline_or_sft_candidate": 1,
    "online_policy_loss_eligible": 2,
}

# 七维的固定顺序（与 EligibilityFacts 字段序一致，报告与信号的遍历基准）。
_DIMENSION_ORDER: tuple[str, ...] = (
    "token_provenance",
    "logprob_alignment",
    "loss_mask_integrity",
    "reward_scope",
    "security_and_leakage",
    "clean_grading",
    "policy_staleness",
)

# 各维失败的降级地板（模块 docstring 有完整理由；多维失败取最严）。
_DIMENSION_DEGRADE_FLOOR: dict[str, TrainingEligibilityClass] = {
    "token_provenance": "offline_or_sft_candidate",
    "logprob_alignment": "offline_or_sft_candidate",
    "loss_mask_integrity": "audit_only_or_rejected",
    "reward_scope": "audit_only_or_rejected",
    "security_and_leakage": "audit_only_or_rejected",
    "clean_grading": "audit_only_or_rejected",
    "policy_staleness": "offline_or_sft_candidate",
}


class GateInputError(ValueError):
    """gate 输入接线错误（编排 bug，fail loud）。

    与"维度失败降级"严格区分：喂给 gate 一份别的轨迹的 GradingReport
    不是"这条轨迹的事实不好"，而是调用方接错了线——此时产出任何
    EligibilityReport 都会掩盖 bug，唯一正确行为是抛异常让编排当场崩。
    """


class GroupRepairSignal(StrictModel):
    """组修复信号（S1-5 定案的结构化表示，gate 返回值中一等暴露）。

    用途（设计文档 2 §5.2 P4 + §5.6）：降级结论必须在**组装配前**对训练
    后端可见，供后端做组修复（GLM-5 规则：有效样本 > 半组则 pad、否则整组
    丢弃；或从同初始态重采样）。S1-6 编排在拿到 FinalizedRollout 后、把
    样本交给 slime 组装 GRPO 组之前，先把本信号转发后端；后端按组聚合出
    handshake.GroupSignal（delivered/degraded 计数）时，
    `degrade_visible_before_assembly=True` 的事实来源就是这次转发。

    语义要点：
    - `degraded` 按**七维事实**判定（任一维 ok=False 即 True）。A3 之后
      不再有"封顶"这类政策上限：七维全过 = online、degraded=False。具体
      数值例：n=4 的组里 1 条 infra 失败、3 条七维全过，账目是
      degraded=1、可交付=3；
    - `group_id=None` 表示非组式算法形态（PPO 单条 rollout，算法无关原则），
      此时降级即单样本剔除，无组账目可修。

    fail-closed 校验：degraded 与 failed_dimensions 账实相符；audit 档
    必然 degraded（security/账目级失败才会落 audit）；online 档必然不
    degraded（七维合取）；降级必须有理由码。

    S1-9（codex#5）：S1-6/7a 已把本信号按 jsonl sidecar 落盘，故补 schema_id
    并经 `repoharness2.registry.FULL_SCHEMA_REGISTRY` 注册（CLI 层聚合，
    避免 contracts 反向 import governance），`inspect-rh2-artifact` 可校验。
    """

    schema_id: Literal["rh2.group_repair_signal.v1"] = Field(
        default="rh2.group_repair_signal.v1", description="schema 判别字段。"
    )
    trajectory_id: NonEmptyStr = Field(description="被判定轨迹 id。")
    group_id: NonEmptyStr | None = Field(
        default=None,
        description="GRPO 组 id（RewardFacts.group_id 透传）。None = 非组式算法（PPO 单条）。",
    )
    parent_rollout_id: NonEmptyStr | None = Field(
        default=None,
        description="同题兄弟组标识（RewardFacts.parent_rollout_id 透传，跨 rollout 组账目用）。",
    )
    report_ref: NonEmptyStr = Field(
        description="对应 EligibilityReport.report_id（信号可回链到完整判定依据）。"
    )
    eligibility_class: TrainingEligibilityClass = Field(
        description="最终三档结论（与 EligibilityReport 一致）。"
    )
    degraded: bool = Field(
        description="七维任一失败即 True（按事实判定——见类 docstring）。"
    )
    failed_dimensions: list[SafeIdentifier] = Field(
        default_factory=list,
        description="失败维度名列表，按七维固定顺序（token_provenance ... policy_staleness）。",
    )
    reason_codes: list[SafeIdentifier] = Field(
        default_factory=list,
        description="结论级理由码（与 EligibilityReport.reason_codes 一致）。",
    )

    @model_validator(mode="after")
    def _check_signal_contract(self) -> "GroupRepairSignal":
        unknown = [name for name in self.failed_dimensions if name not in _DIMENSION_ORDER]
        if unknown:
            raise ValueError(f"failed_dimensions 含未知维度名 {unknown}（七维之外的名字不可表示）。")
        canonical = [name for name in _DIMENSION_ORDER if name in self.failed_dimensions]
        if list(self.failed_dimensions) != canonical:
            raise ValueError(
                f"failed_dimensions 必须按七维固定顺序排列，期望 {canonical}，"
                f"得到 {list(self.failed_dimensions)}（确定性要求）。"
            )
        if self.degraded != bool(self.failed_dimensions):
            raise ValueError(
                f"degraded({self.degraded}) 与 failed_dimensions({self.failed_dimensions}) "
                "账实不符（降级标志必须由失败维度列表推出）。"
            )
        if self.degraded and not self.reason_codes:
            raise ValueError("degraded=True 时 reason_codes 不得为空（降级不可无理由）。")
        if not self.degraded and self.eligibility_class == "audit_only_or_rejected":
            raise ValueError(
                "eligibility_class=audit_only_or_rejected 必然来自维度失败，"
                "degraded=False 与之矛盾（audit 档不存在'无缺陷'样本）。"
            )
        if self.degraded and self.eligibility_class == "online_policy_loss_eligible":
            raise ValueError(
                "degraded=True 与 online_policy_loss_eligible 矛盾（七维合取：任一失败即出局）。"
            )
        return self


class GateOutcome(StrictModel):
    """gate 的完整返回值：EligibilityReport + 一等暴露的组修复信号。

    为什么不是裸 EligibilityReport：P4 要求降级信号在组装配前对后端可见，
    若信号要靠调用方从报告里自行推导，"推导被遗漏"就成了静默风险；
    作为返回值的一等字段，S1-6 想不转发都得显式无视它。
    """

    report: EligibilityReport = Field(description="资格判定权威载体（typed sidecar）。")
    group_repair_signal: GroupRepairSignal = Field(
        description="组修复信号（S1-6 在组装配前转发训练后端）。"
    )

    @model_validator(mode="after")
    def _check_outcome_consistency(self) -> "GateOutcome":
        signal = self.group_repair_signal
        report = self.report
        if signal.trajectory_id != report.trajectory_id:
            raise ValueError(
                f"信号 trajectory_id({signal.trajectory_id}) 与报告({report.trajectory_id}) 不一致。"
            )
        if signal.report_ref != report.report_id:
            raise ValueError(
                f"signal.report_ref({signal.report_ref}) 必须等于 report_id({report.report_id})。"
            )
        if signal.eligibility_class != report.eligibility_class:
            raise ValueError(
                f"信号结论({signal.eligibility_class}) 与报告结论({report.eligibility_class}) 不一致。"
            )
        if signal.degraded != (not report.facts.all_ok()):
            raise ValueError(
                f"signal.degraded({signal.degraded}) 与七维事实（all_ok="
                f"{report.facts.all_ok()}）不一致（降级标志必须由事实推出）。"
            )
        return self


def _dedup(values: Sequence[str]) -> list[str]:
    """保序去重（reason/evidence 聚合用，保证输出确定性）。"""

    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


# ---------------------------------------------------------------------------
# 七个维度的事实归结（每个函数只消费上游事实，输出 DimensionFact）
# ---------------------------------------------------------------------------


def _dim_token_provenance(
    projection: TrajectoryProjection,
    records_by_id: dict[str, GenerationCaptureRecord],
) -> DimensionFact:
    """维度 1：response token 可回链到完整、对齐的捕获记录。

    schema 已保证"有 mask=1 就有 capture_record_refs"（BranchProjection 校验 4）；
    gate 补的是引用**解析**：被引用的记录必须真的在场，且 capture_status=complete
    （complete 在 capture schema 里蕴含 alignment_status=aligned）。
    """

    reasons: list[str] = []
    evidence: list[str] = []
    for branch in projection.branches:
        for ref in branch.capture_record_refs:
            record = records_by_id.get(ref)
            if record is None:
                reasons.append("capture_record_missing")
                evidence.append(f"branch:{branch.branch_id}:missing_capture:{ref}")
            elif record.capture_status != "complete":
                # 与 S1-3 投影层的拒收理由码同名（capture_record_not_complete），
                # 两层口径一致便于跨层追踪同一形态。
                reasons.append("capture_record_not_complete")
                evidence.append(
                    f"branch:{branch.branch_id}:capture:{ref}:{record.capture_status}"
                )
            else:
                evidence.append(ref)
    return DimensionFact(
        ok=not reasons,
        reason_codes=_dedup(reasons),
        evidence_refs=_dedup(evidence),
    )


def _dim_logprob_alignment(projection: TrajectoryProjection) -> DimensionFact:
    """维度 2：每条分支的逐 token logprob 对齐结论必须是 aligned_per_token。"""

    reasons: list[str] = []
    evidence: list[str] = []
    for branch in projection.branches:
        status = branch.logprob_alignment_status
        evidence.append(f"branch:{branch.branch_id}:logprob:{status}")
        if status == "missing":
            reasons.append("logprob_missing")
        elif status == "partial_or_mismatch":
            reasons.append("logprob_partial_or_mismatch")
    return DimensionFact(ok=not reasons, reason_codes=_dedup(reasons), evidence_refs=evidence)


def _dim_loss_mask_integrity(projection: TrajectoryProjection) -> DimensionFact:
    """维度 3：loss mask 语义成立（span 级不变量由 schema 保证，gate 补账目）。

    - 全轨迹 mask=1 token 总数必须 > 0（零可训练 token 的轨迹没有训练意义）；
    - 若申报了 rollout_loss_denominator（防 fan-out 重复放大的分母），
      必须等于全分支 mask=1 token 的重算总数。具体数值例：单分支
      response 16 token 全部 mask=1，申报 17 即拒（账目被凭空放大 1 个 token）。
    """

    trainable_total = sum(
        span.end - span.start
        for branch in projection.branches
        for span in branch.loss_mask_spans
        if span.mask == 1
    )
    reasons: list[str] = []
    evidence: list[str] = [f"trainable_token_total:{trainable_total}"]
    if trainable_total == 0:
        reasons.append("no_trainable_tokens")
    declared = projection.reward_facts.rollout_loss_denominator
    if declared is not None and declared != trainable_total:
        reasons.append("loss_denominator_mismatch")
        evidence.append(f"declared_loss_denominator:{declared}")
    return DimensionFact(ok=not reasons, reason_codes=_dedup(reasons), evidence_refs=evidence)


def _dim_reward_scope(
    projection: TrajectoryProjection, grading_report: GradingReport
) -> DimensionFact:
    """维度 4：reward 作用域与信用分配明确，且与评分报告账实相符。

    跨对象互检（schema 看不见对面，这里是唯一执行点）：
    - raw_reward 必须与 GradingReport.reward 逐值一致（None 也算一种值）。
      关键反例：infra_failure 报告（reward=None）配上申报 raw_reward=0.0 的
      投影——两个对象各自合法，对账即露馅（infra 伪装成负样本，P4 红线）；
    - 携带 reward 时（scope != none），reward_event_refs 必须引用本次评分
      报告的 report_id（reward 必须有出处，且出处必须是喂进来的这份评分）。
    """

    facts = projection.reward_facts
    reasons: list[str] = []
    evidence: list[str] = [grading_report.report_id]
    if facts.reward_scope == "none":
        reasons.append("reward_scope_none")
    if facts.credit_assignment_strategy == "unknown":
        reasons.append("credit_assignment_unknown")
    if facts.raw_reward != grading_report.reward:
        reasons.append("reward_value_mismatch")
        evidence.append(
            f"raw_reward:{facts.raw_reward}:grading_reward:{grading_report.reward}"
        )
    if facts.reward_scope != "none" and grading_report.report_id not in facts.reward_event_refs:
        reasons.append("reward_event_ref_missing")
    return DimensionFact(ok=not reasons, reason_codes=_dedup(reasons), evidence_refs=_dedup(evidence))


def _dim_security_and_leakage(
    grading_report: GradingReport,
    findings: Sequence[AntiCheatFinding],
) -> DimensionFact:
    """维度 5：安全与泄漏（§16.1 条 5+7 合并）——只判**本次轨迹**发生的、影响
    reward 可信度的**执行级**事实（Wave3 前置清理批，决策包 D2-2/D2-4）。

    两类事实源：
    1. AntiCheatFinding：enforcement=executed 即失败（`anti_cheat_executed_<category>`）；
       attempted_blocked（拦截成功）不扣分——agent 学到"此路不通"是合法训练信号，但留痕；
    2. patch hygiene 的 executed 级篡改事实：test_files_modified /
       forbidden_path_touched 说明篡改/污染已落盘在最终 patch 里
       （eligibility schema 对本维的定义明说"泄漏/权限/**篡改**"，
       findings 缺席时 hygiene 是同一事实的评分期证据）。这两条理由码在
       admission 侧仍是 pending（显式注入 `agent_violation`）；"改测试路径不再自动
       DROP_GROUP、控制面改动不重放"的可信评分投影归 D2-3/W3a，本维不预判。

    **不再消费**（本批删除，理由见模块 docstring）：每轨迹 `SandboxCapabilityFacts`
    sidecar（缺事实/未核实/违规三族理由码）与 `TrajectoryProjection` 的 marker 扫描
    （`public_projection_marker_hit`）。因此 `findings=()` 且 hygiene 干净 ⇒ 本维通过，
    evidence 可以为空——这是"本次轨迹没有执行级违规事实"的如实记录，不是假过窗口
    （sandbox 合规由创建期强制 + 启动前探针在 rollout 之前保证，W3b）。

    本维失败时 schema 层强制结论 audit_only_or_rejected（gate 地板同为
    audit，双保险）。
    """

    reasons: list[str] = []
    evidence: list[str] = []
    for finding in findings:
        if finding.enforcement == "executed":
            reasons.append(f"anti_cheat_executed_{finding.category}")
            evidence.append(finding.finding_id)
        else:
            evidence.append(f"attempted_blocked:{finding.finding_id}")
    hygiene = grading_report.patch_hygiene
    if hygiene is not None:
        if hygiene.test_files_modified:
            reasons.append("patch_test_tampering")
            evidence.append(f"patch_hygiene:{grading_report.report_id}")
        if hygiene.forbidden_path_touched:
            reasons.append("patch_forbidden_contamination")
            evidence.append(f"patch_hygiene:{grading_report.report_id}")
    return DimensionFact(ok=not reasons, reason_codes=_dedup(reasons), evidence_refs=_dedup(evidence))


def _dim_clean_grading(
    grading_report: GradingReport, backpressure_events: Sequence[BackpressureEvent]
) -> DimensionFact:
    """维度 6：评分来自 clean checkout 重放且结论可信。

    - infra 族（infra_failure / test_log_parse_failed）：评分链路自身故障，
      结论不可信，失败（理由码 grading_infra_failure / grading_test_log_parse_failed）；
    - hygiene verdict 非 clean：被拒 patch 的评分结论已被封顶改写，失败；
    - replayed_on_clean_checkout=False：同容器评分旧形态（agent 可能已污染
      工作区），A7 明说 gate 要降级，失败；
    - patch_apply_failed / tests_failed 是正常模型负样本，本维**通过**；
    - 反压事件只是观测事实（评分等了多久），记 evidence 不降级。
    """

    reasons: list[str] = []
    evidence: list[str] = [grading_report.report_id]
    if grading_report.outcome == "failed_to_grade":
        reasons.append(f"grading_{grading_report.failure_category}")
        if grading_report.infra_failure_detail is not None:
            evidence.append(f"infra_detail:{grading_report.infra_failure_detail}")
    hygiene = grading_report.patch_hygiene
    if hygiene is not None:
        if not hygiene.replayed_on_clean_checkout:
            reasons.append("not_replayed_on_clean_checkout")
        if hygiene.verdict != "clean":
            reasons.append(f"hygiene_{hygiene.verdict}")
    for event in backpressure_events:
        evidence.append(event.event_id)
    return DimensionFact(ok=not reasons, reason_codes=_dedup(reasons), evidence_refs=_dedup(evidence))


_DECIMAL_VERSION = re.compile(r"[0-9]+")


def _parse_decimal_version(value: str) -> int | None:
    """权重版本的严格解析：只认 ASCII 十进制数字串（不认符号/空白/其它 Unicode 数字），
    否则返回 None。与 generate.py 正式链 `int(v, 10)` 的口径一致但更严（不吞空白）。"""

    if not isinstance(value, str) or _DECIMAL_VERSION.fullmatch(value) is None:
        return None
    return int(value, 10)


def _dim_policy_staleness(
    handshake: BackendHandshake | None,
    projection: TrajectoryProjection,
    *,
    require_real_weight_versions: bool,
) -> DimensionFact:
    """维度 7：**版本事实可用且合法**（B-1 改判 D1-4，决策包 D2+B v2，owner 2026-09-04 已批）。

    本维**不再**用任何阈值做资格门：consume-time staleness 的唯一权威是 miles
    `DefaultDataBuffer.get()` + `--max-weight-staleness N`（W4 接线），RH2 在 finalize
    时刻只负责把每个可训练轮次的版本 provenance 完整、合法地传递下去：

    1. **可用**：BackendHandshake 在场。缺席 → `staleness_facts_missing`（fail-closed：
       没有版本事实的样本无法参与 consume-time 判定；admission 侧映射 FATAL）。
    2. **合法**（`require_real_weight_versions=True`，与 `SlimeBindingConfig` 同名旗标同义，
       formal 链启动校验强制为 True）：`weight_versions_seen` 非空、`policy_version` 在场
       （两者 schema 已保证，此处再钉一次）、全部可解析为十进制 int、且没有任何 seen 版本
       比 `policy_version`（finalize 时刻 current）更新。违反 → `staleness_facts_invalid`
       （非法/未来版本 = 版本账目矛盾；admission 侧映射 FATAL）。
       只查 `min(seen) <= current` 会放过 seen=[3, 9] / current=5 这种形状，而消费侧 W1b
       叶版本绑定对同一形状已判 FATAL（`leaf_version_ahead_of_finalize`），两处口径须一致，
       故这里按"任一 seen 版本 > current 即未来版本"判。
       `require_real_weight_versions=False`（S1 兼容 / 测试路径）时版本允许是静态哨兵
       （如 `step_0`）：只要求握手在场，evidence 如实记 `weight_versions_contract:legacy_sentinel_allowed`。
       不这样做的话，冻结的 s1_compat 路径（其握手按 S1 契约恒 lag=0、版本为哨兵）会因
       本维失败被 s1_compat 的降级即剔除规则整体剔除——那是改写冻结路径，不是本批范围。

    finalize-time lag（`handshake.staleness_steps`）**只作观测值**写进 evidence
    （`finalize_lag_observed:<n>`），不参与 ok 判定；`staleness_exceeded` 理由码已删除，
    握手里的 `staleness_threshold` 只是 consume-time 阈值的记录用镜像，本维不读它。
    刻意**不读** handshake.accepted——S1-1b 定案：accepted 仅表示后端物理接收，不构成资格背书。

    staleness 分布记账（preflight §8 H-1，S1-9 落地）照旧**只记录不准入**：projection.handshake
    携带 Sample.weight_versions 的原始 list 与派生 max_lag，本维把分布（列表长度 + 版本跨度）
    写进 evidence；缺席也如实记 `weight_versions_unrecorded`（分不清"没混版本"和"没记账"）。
    """

    distribution_evidence: list[str] = []
    wv = projection.handshake
    if wv is None:
        distribution_evidence.append("weight_versions_unrecorded")
    else:
        distribution_evidence.append(f"weight_versions_count:{len(wv.weight_versions)}")
        distribution_evidence.append(
            "weight_versions_max_lag:"
            + ("not_derivable" if wv.max_lag is None else str(wv.max_lag))
        )
    if handshake is None:
        return DimensionFact(
            ok=False,
            reason_codes=["staleness_facts_missing"],
            evidence_refs=distribution_evidence,
        )
    evidence = [
        handshake.handshake_id,
        f"finalize_lag_observed:{handshake.staleness_steps}",
        *distribution_evidence,
    ]
    if not handshake.weight_versions_seen or not handshake.policy_version:
        # schema（min_length=1 / NonEmptyStr）已禁止这种形状；此处只是防御性重申。
        evidence.append("weight_versions_seen:empty")
        return DimensionFact(ok=False, reason_codes=["staleness_facts_missing"], evidence_refs=evidence)
    if not require_real_weight_versions:
        evidence.append("weight_versions_contract:legacy_sentinel_allowed")
        return DimensionFact(ok=True, reason_codes=[], evidence_refs=evidence)
    current = _parse_decimal_version(handshake.policy_version)
    seen = [_parse_decimal_version(v) for v in handshake.weight_versions_seen]
    if current is None or any(v is None for v in seen):
        evidence.append(
            f"weight_versions_not_numeric:policy_version={handshake.policy_version}:"
            f"seen={','.join(handshake.weight_versions_seen)}"
        )
        return DimensionFact(ok=False, reason_codes=["staleness_facts_invalid"], evidence_refs=evidence)
    seen_ints = [v for v in seen if v is not None]
    evidence.append(f"weight_versions_range:{min(seen_ints)}..{max(seen_ints)}:current:{current}")
    if max(seen_ints) > current:
        evidence.append("weight_version_ahead_of_current")
        return DimensionFact(ok=False, reason_codes=["staleness_facts_invalid"], evidence_refs=evidence)
    return DimensionFact(ok=True, reason_codes=[], evidence_refs=evidence)


# ---------------------------------------------------------------------------
# 输入接线校验与主判定
# ---------------------------------------------------------------------------


def _check_wiring(
    *,
    projection: TrajectoryProjection,
    grading_report: GradingReport,
    capture_records: Sequence[GenerationCaptureRecord],
    findings: Sequence[AntiCheatFinding],
    handshake: BackendHandshake | None,
) -> dict[str, GenerationCaptureRecord]:
    """gate 输入的接线一致性检查（不一致 = 编排 bug，抛 GateInputError）。"""

    traj = projection.trajectory_id
    if grading_report.trajectory_id != traj:
        raise GateInputError(
            f"GradingReport.trajectory_id({grading_report.trajectory_id}) 与投影({traj}) 不一致。"
        )
    if grading_report.task_id != projection.task_id:
        raise GateInputError(
            f"GradingReport.task_id({grading_report.task_id}) 与投影({projection.task_id}) 不一致。"
        )
    records_by_id: dict[str, GenerationCaptureRecord] = {}
    for record in capture_records:
        if record.trajectory_id != traj:
            raise GateInputError(
                f"捕获记录 {record.record_id} 属于轨迹 {record.trajectory_id}，与投影({traj}) 不一致。"
            )
        if record.record_id in records_by_id:
            raise GateInputError(f"捕获记录 id 重复：{record.record_id}（证据索引歧义）。")
        records_by_id[record.record_id] = record
    for finding in findings:
        if finding.trajectory_id != traj:
            raise GateInputError(
                f"finding {finding.finding_id} 属于轨迹 {finding.trajectory_id}，与投影({traj}) 不一致。"
            )
    if handshake is not None and handshake.trajectory_id != traj:
        raise GateInputError(
            f"BackendHandshake.trajectory_id({handshake.trajectory_id}) 与投影({traj}) 不一致。"
        )
    return records_by_id


def _evaluate(
    *,
    projection: TrajectoryProjection,
    grading_report: GradingReport,
    capture_records: Sequence[GenerationCaptureRecord],
    findings: Sequence[AntiCheatFinding] = (),
    handshake: BackendHandshake | None = None,
    backpressure_events: Sequence[BackpressureEvent] = (),
    require_real_weight_versions: bool = True,
    report_id: str,
    created_at_utc: datetime,
) -> GateOutcome:
    """七维合取判定（模块私有：唯一合法调用方是 wrapper.finalize_rollout）。

    返回 GateOutcome：EligibilityReport（权威载体）+ GroupRepairSignal
    （一等暴露的组修复信号，S1-6 在组装配前转发后端）。

    `require_real_weight_versions`：policy_staleness 维的版本契约开关（默认 True，
    fail-closed；语义见 `_dim_policy_staleness`）。
    """

    records_by_id = _check_wiring(
        projection=projection,
        grading_report=grading_report,
        capture_records=capture_records,
        findings=findings,
        handshake=handshake,
    )
    # 反压事件是全局观测流（GradingQueue.events 混着所有轨迹），按轨迹过滤，
    # 非本轨迹的事件不属于本样本的事实，直接忽略（不算接线错误）。
    own_backpressure = [
        event for event in backpressure_events if event.trajectory_id == projection.trajectory_id
    ]

    facts = EligibilityFacts(
        token_provenance=_dim_token_provenance(projection, records_by_id),
        logprob_alignment=_dim_logprob_alignment(projection),
        loss_mask_integrity=_dim_loss_mask_integrity(projection),
        reward_scope=_dim_reward_scope(projection, grading_report),
        security_and_leakage=_dim_security_and_leakage(grading_report, findings),
        clean_grading=_dim_clean_grading(grading_report, own_backpressure),
        policy_staleness=_dim_policy_staleness(
            handshake, projection, require_real_weight_versions=require_real_weight_versions
        ),
    )

    failed: list[tuple[str, DimensionFact]] = [
        (name, fact)
        for name, fact in zip(
            _DIMENSION_ORDER,
            (
                facts.token_provenance,
                facts.logprob_alignment,
                facts.loss_mask_integrity,
                facts.reward_scope,
                facts.security_and_leakage,
                facts.clean_grading,
                facts.policy_staleness,
            ),
        )
        if not fact.ok
    ]

    # 七维合取 -> 资格档位：全过 = online（A3：资格只由轨迹事实决定，无封顶）；
    # 有失败 = 各失败维地板取最严。
    if failed:
        final: TrainingEligibilityClass = min(
            (_DIMENSION_DEGRADE_FLOOR[name] for name, _ in failed),
            key=lambda cls: _CLASS_SEVERITY[cls],
        )
    else:
        final = "online_policy_loss_eligible"

    reason_codes: list[str] = []
    for _, fact in failed:
        reason_codes.extend(fact.reason_codes)
    for event in own_backpressure:
        # queue.py 明说该理由码可直接写进 EligibilityReport.reason_codes
        # （观测事实，不构成降级）。
        reason_codes.append(event.reason_code)
    reason_codes = _dedup(reason_codes)

    report = EligibilityReport.finalize(
        report_id=report_id,
        trajectory_id=projection.trajectory_id,
        gate_version=GATE_VERSION,
        facts=facts,
        eligibility_class=final,
        reason_codes=reason_codes,
        created_at_utc=created_at_utc,
    )
    signal = GroupRepairSignal(
        trajectory_id=projection.trajectory_id,
        group_id=projection.reward_facts.group_id,
        parent_rollout_id=projection.reward_facts.parent_rollout_id,
        report_ref=report.report_id,
        eligibility_class=final,
        degraded=bool(failed),
        failed_dimensions=[name for name, _ in failed],
        reason_codes=reason_codes,
    )
    return GateOutcome(report=report, group_repair_signal=signal)
