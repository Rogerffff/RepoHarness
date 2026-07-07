"""TrainingEligibilityGate（S1-5）：七维事实合取 -> 三档资格 + 组修复信号。

职责边界（eligibility.py 是宪法，本模块是执行者不是重定义者）：

- gate **只消费上游事实、不生产事实**：capture 完成度来自
  `GenerationCaptureRecord`（步骤 4）、span/账目结论来自 `TrajectoryProjection`
  （步骤 7，schema 校验已在构造时执行）、评分与 hygiene 来自 `GradingReport`
  （步骤 6）、staleness 来自 `BackendHandshake`（步骤 9 的事实回填）、
  泄漏扫描来自 `projection_scan.ProjectionScanResult`、反作弊来自
  `AntiCheatFinding`、反压来自 `grading.queue.BackpressureEvent`；
- gate 补的是 schema 看不见的**跨对象一致性**（例如投影申报 raw_reward=0.0
  而评分报告 reward=None 的"infra 伪装成负样本"形态，单个对象各自合法，
  对起账来才露馅）；
- 结论装配交给 `EligibilityReport.finalize()`，digest 重算 / online 合取 /
  security 强制 audit / 派生视图互检这五连锁由 schema 校验器再执行一遍
  （gate 层与 schema 层双保险）。

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

from collections.abc import Sequence
from datetime import datetime

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
from repoharness2.governance.projection_scan import ProjectionScanResult
from repoharness2.grading.queue import BackpressureEvent

__all__ = [
    "GATE_VERSION",
    "S1_TIER_CAP",
    "S1_CEILING_REASON_CODE",
    "GateInputError",
    "GroupRepairSignal",
    "GateOutcome",
]

# gate 实现版本（§16.11 eligibility_gate_version）：改判定逻辑必须升版本号，
# 让两份不同逻辑产出的 EligibilityReport 永远可区分。
GATE_VERSION = "rh2.gate.s1.v1"

# S1 全程资格封顶（fail-closed 上限）：S2 的安全加固（非 root / cap-drop /
# seccomp / 全量 anti-cheat 过滤）尚未完成，在那之前**任何**样本——包括
# 七维全过的完美样本——最高只发 offline_or_sft_candidate，不发
# online_policy_loss_eligible。解除方式：S2 安全验收通过后由验收流程
# 显式修改本常量（并升 GATE_VERSION），不允许任何运行期开关绕过。
S1_TIER_CAP: TrainingEligibilityClass = "offline_or_sft_candidate"

# 封顶生效时写入 reason_codes 的显式理由码（eligibility.py 校验器要求
# 非 online 结论必须有理由——"静默降级"不可表示）。
S1_CEILING_REASON_CODE = "s1_default_ceiling_offline"

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
    - `degraded` 按**七维事实**判定（任一维 ok=False 即 True），**不含**
      S1 封顶——封顶是政策上限不是样本缺陷；若把封顶也算降级，S1 期间
      每组全员"degraded"，组修复会把所有组整组丢弃，S1-7a 的 debug
      training step 一个样本都拿不到。具体数值例：n=4 的组里 1 条 infra
      失败、3 条七维全过（被封顶为 offline），正确账目是 degraded=1、
      可交付=3，而不是 degraded=4；
    - `group_id=None` 表示非组式算法形态（PPO 单条 rollout，算法无关原则），
      此时降级即单样本剔除，无组账目可修。

    fail-closed 校验：degraded 与 failed_dimensions 账实相符；audit 档
    必然 degraded（security/账目级失败才会落 audit）；online 档必然不
    degraded（七维合取）；降级必须有理由码。
    """

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
        description="最终三档结论（含 S1 封顶后的值，与 EligibilityReport 一致）。"
    )
    degraded: bool = Field(
        description="七维任一失败即 True（按事实判定，不含 S1 封顶——见类 docstring）。"
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
    scan_result: ProjectionScanResult,
    findings: Sequence[AntiCheatFinding],
) -> DimensionFact:
    """维度 5：安全与泄漏（§16.1 条 5+7 合并，executed 级即失败）。

    三类事实源：
    1. AntiCheatFinding：enforcement=executed 即失败；attempted_blocked
       （拦截成功）不扣分——agent 学到"此路不通"是合法训练信号，但留痕；
    2. patch hygiene 的 executed 级篡改事实：test_files_modified /
       forbidden_path_touched 说明篡改/污染已落盘在最终 patch 里
       （eligibility schema 对本维的定义明说"泄漏/权限/**篡改**"，
       findings 缺席时 hygiene 是同一事实的评分期证据）；
    3. public projection 扫描：marker 命中即失败。

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
    if not scan_result.clean:
        reasons.append("public_projection_marker_hit")
    evidence.extend(scan_result.evidence_refs())
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


def _dim_policy_staleness(handshake: BackendHandshake | None) -> DimensionFact:
    """维度 7：policy staleness 在阈值内（事实来自 BackendHandshake）。

    - handshake 缺席即失败（fail-closed：没有 staleness 事实就当超阈值处理）；
    - 刻意**不读** handshake.accepted——S1-1b 定案：accepted 仅表示后端物理
      接收，不构成资格背书（后端有权按 H10 接收过期样本，但资格照降）。
    """

    if handshake is None:
        return DimensionFact(
            ok=False, reason_codes=["staleness_facts_missing"], evidence_refs=[]
        )
    evidence = [
        handshake.handshake_id,
        f"staleness:{handshake.staleness_steps}/{handshake.staleness_threshold}",
    ]
    if not handshake.staleness_within_threshold:
        return DimensionFact(
            ok=False, reason_codes=["staleness_exceeded"], evidence_refs=evidence
        )
    return DimensionFact(ok=True, reason_codes=[], evidence_refs=evidence)


# ---------------------------------------------------------------------------
# 输入接线校验与主判定
# ---------------------------------------------------------------------------


def _check_wiring(
    *,
    projection: TrajectoryProjection,
    grading_report: GradingReport,
    capture_records: Sequence[GenerationCaptureRecord],
    scan_result: ProjectionScanResult,
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
    if scan_result.trajectory_id != traj:
        raise GateInputError(
            f"ProjectionScanResult.trajectory_id({scan_result.trajectory_id}) 与投影({traj}) 不一致。"
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
    scan_result: ProjectionScanResult,
    findings: Sequence[AntiCheatFinding] = (),
    handshake: BackendHandshake | None = None,
    backpressure_events: Sequence[BackpressureEvent] = (),
    report_id: str,
    created_at_utc: datetime,
) -> GateOutcome:
    """七维合取判定（模块私有：唯一合法调用方是 wrapper.finalize_rollout）。

    返回 GateOutcome：EligibilityReport（权威载体）+ GroupRepairSignal
    （一等暴露的组修复信号，S1-6 在组装配前转发后端）。
    """

    records_by_id = _check_wiring(
        projection=projection,
        grading_report=grading_report,
        capture_records=capture_records,
        scan_result=scan_result,
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
        security_and_leakage=_dim_security_and_leakage(grading_report, scan_result, findings),
        clean_grading=_dim_clean_grading(grading_report, own_backpressure),
        policy_staleness=_dim_policy_staleness(handshake),
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

    # 七维合取 -> 事实档位（merit）：全过 = online；有失败 = 各失败维地板取最严。
    if failed:
        merit: TrainingEligibilityClass = min(
            (_DIMENSION_DEGRADE_FLOOR[name] for name, _ in failed),
            key=lambda cls: _CLASS_SEVERITY[cls],
        )
    else:
        merit = "online_policy_loss_eligible"

    # S1 封顶：事实档位再好也不越过 S1_TIER_CAP（封顶只降不升——audit 不会被"抬"到 offline）。
    if _CLASS_SEVERITY[merit] > _CLASS_SEVERITY[S1_TIER_CAP]:
        final: TrainingEligibilityClass = S1_TIER_CAP
        cap_applied = True
    else:
        final = merit
        cap_applied = False

    reason_codes: list[str] = []
    for _, fact in failed:
        reason_codes.extend(fact.reason_codes)
    if cap_applied:
        reason_codes.append(S1_CEILING_REASON_CODE)
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
