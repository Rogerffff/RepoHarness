"""FA-0 契约：三层身份、执行结果、训练运行时协调协议、模型调用账目。

出处：`docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md`
FA-0 第 1/2/3b/3c 条；机制论证见 `fully_async_rollout_pipeline_design_discussion.md`
§5/§7（codex，2026-07-12）。本模块只定义**持久化事实的形状**，异步协调器的
运行时状态机（PromptGroupState）按讨论稿 §5.2 定案保持进程内 dataclass，
不在此注册公共 schema。

三层身份模型（问题 C/D/E 的公共基座，实现不得混用）::

    PromptGroup       同一任务 prompt 的 n 次采样（prompt_group_id / group_index）
                      —— GRPO reward/advantage 归一化的单位
    RolloutExecution  一次独立 harness 执行（rollout_execution_id）
                      —— slime build_dp_schedule 计 global_batch_size 的单位
    Branch            一次执行因 compaction/subagent/REALIGN 分叉产生的叶链
                      —— 多 branch 共享 rollout_execution_id，loss 按 rollout 聚合

固定反例（P3 实测，`preflight/remote_evidence_20260708/bringup_selected/
j4_formal_20260708T160749Z` 本地可复核）：group_index=5 只有一次有效执行
index=22，却 fan-out 出 8 个 branch——这 8 个 branch 既不是 8 次独立 GRPO
采样，也不能用来凑 global_batch_size。

provenance 与 algorithmic 两类 token 选择事实的分离（FA-0 第 4 条，
faithful DIS 的前置约定）::

    provenance_loss_mask（= trajectory.LossMaskSpan）
      回答 token 是否由模型真实采样、角色是否允许进入 policy loss；
      属于 TrajectoryProjection 的不可变历史事实。
    algorithmic mask / importance_weight（dis_mask 等）
      回答本次 trainer step 中 current/rollout ratio 是否在 DIS 信任区间；
      属于训练后端针对某个 policy step 的算法决定，逐 step 变化。
    算法掩码**不得改写** LossMaskSpan；正确实现保留原始 mask、额外产生
    step-local 张量并记录拒绝率/有效 token 数等指标（FA-4）。
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import AwareDatetime, Field, model_validator

from ._base import NonEmptyStr, StrictModel
from .trajectory import derive_weight_version_max_lag

__all__ = [
    "CompletionClass",
    "CompletionClassV2",
    "ExecutionIdentity",
    "ModelCallAttempt",
    "ModelCallDeliveryStatus",
    "RecoveryScope",
    "RolloutAttemptOutcome",
    "RolloutAttemptOutcomeV2",
    "RuntimeFailureCategory",
    "TaskOutcome",
    "TerminationKind",
    "TERMINATION_KINDS_CONTROL",
    "TERMINATION_KINDS_INFRA",
    "TERMINATION_KINDS_NORMAL",
    "TERMINATION_KINDS_POLICY_HORIZON",
    "TERMINATION_KINDS_WATCHDOG",
    "FAILURE_CATEGORIES_EXECUTION_FACT",
    "RUNTIME_QUIESCENCE_REASON_CODES",
    "FAILURE_CATEGORIES_GRADING",
    "FAILURE_CATEGORIES_ADMISSION_CONTROL",
    "TrainingRuntimePhase",
    "TrainingRuntimeWindow",
]


# 执行期故障归因（FA-0 follow-up，codex FA-0 审查严重 3）：GradingFailureCategory
# 只有四种**评分**结果，覆盖不了 rollout 生命周期的故障面——组终结/重试/熔断
# （FA-2）需要独立枚举。评分基建故障映射为 grading_infra_failure，原
# GradingReport 经 evidence_refs 回链（评分枚举不统治整个生命周期）。
RuntimeFailureCategory = Literal[
    "model_proxy_failure",  # 模型代理/adapter 层失败
    "inference_service_failure",  # SGLang/推理服务失败（非更新窗口 abort 的不可归因中断）
    "sandbox_crash",  # rollout 沙箱异常死亡
    "harness_crash",  # 黑盒 harness 进程崩溃
    "worker_crash",  # 异步 worker/task 层崩溃（N1 面）
    "grading_infra_failure",  # 评分基建故障（GradingReport 的 infra 族，经 evidence 回链）
    "capture_incomplete",  # capture 记录缺失/不完整（no_capture_records 等）
    "token_alignment_failure",  # token 锚定/对齐失败
    "staleness_exceeded",  # 版本跨度/新鲜度超预注册上限
    "security_violation",  # executed 级安全事件（组级永久拒绝的归因）
    "identity_conflict",  # 镜像 digest/base commit/bundle 血缘矛盾（task quarantine 归因）
    "contract_violation",  # schema/账目对账矛盾（run halt 归因）
    "cleanup_failure",  # 清理失败（资源泄漏风险）
    # T0 2026-08-15（pre-formal 原地修订，v2 无正式外部资产时批准）：
    # Runtime 静止屏障**已真实执行但失败**——"屏障尚未实现"由启动闸门
    # 表达，不用本值（不进每 rollout 故障统计）。reason_code 细分：
    # execution_scope_termination_timeout / active_writer_detected /
    # late_model_request_detected / snapshot_freeze_failed /
    # snapshot_integrity_mismatch
    "runtime_quiescence_failure",
]


class ExecutionIdentity(StrictModel):
    """三层身份的一次绑定（一条 branch 视角的完整身份链）。

    branch_id 为 None 表示"整次执行"视角（例如 RolloutAttemptOutcome 级
    的账目——执行还没有或不需要落到具体叶链）。
    """

    schema_id: Literal["rh2.fa.execution_identity.v1"] = Field(
        default="rh2.fa.execution_identity.v1", description="schema 判别字段。"
    )
    prompt_group_id: NonEmptyStr = Field(
        description="PromptGroup id（同一 prompt 的 n 次采样共享；GRPO 归一化单位）。"
    )
    group_index: int = Field(
        ge=0, description="slime data source 赋予的组序号（group_index，示例：5）。"
    )
    rollout_execution_id: NonEmptyStr = Field(
        description="一次独立 harness 执行的 id（build_dp_schedule 计数单位，示例：exec_22）。"
    )
    branch_id: NonEmptyStr | None = Field(
        default=None,
        description="叶链 id（多 branch 共享同一 rollout_execution_id）；执行级账目可为 None。",
    )
    parent_rollout_id: NonEmptyStr | None = Field(
        default=None,
        description="跨 rollout 的 GRPO 同题兄弟组标识（与 RewardFacts.parent_rollout_id 同义）。",
    )
    # F2-1a（D2 批准的四层身份，T1 可选字段——按已批设计新增，v1 消费者不受影响）：
    # physical_attempt_id = 每次实际重放都不同的事实键（artifact/审计归属）；
    # rollout_execution_id 跨 replay 稳定（逻辑执行/去重键）。
    physical_attempt_id: NonEmptyStr | None = Field(
        default=None, description="本次物理重放身份（worker 每次 dispatch 铸造；replay 即新值）。"
    )
    physical_attempt_seq: int | None = Field(
        default=None, ge=1, description="同一逻辑执行内的物理重放序号（1 起）。"
    )

    @model_validator(mode="after")
    def _physical_attempt_pair(self) -> "ExecutionIdentity":
        if (self.physical_attempt_id is None) != (self.physical_attempt_seq is None):
            raise ValueError("physical_attempt_id 与 physical_attempt_seq 必须同现同缺。")
        return self


CompletionClass = Literal[
    "present",  # 在场成员：capture/评分/投影事实完整（含可信 reward=0 负样本）
    "missing_after_local_retry",  # 局部重试后仍缺失：当前组不能 ready，不重新采样该成员
    "permanent_rejection",  # 永久拒绝：executed 级安全事件/身份矛盾等，整组不得进在线训练
]

TaskOutcome = Literal["resolved", "unresolved", "unknown"]

RecoveryScope = Literal["none", "local_stage_retry", "task_quarantine", "run_halt"]


class RolloutAttemptOutcome(StrictModel):
    """一次 RolloutExecution 结束后的**唯一**执行结果记录（讨论稿 §5.1）。

    设计约束（codex 轮次 3 #5/#6，2026-07-12）：

    - completion_class 用 `present` 而不是 "present_trainable"——本对象只记录
      在场事实并**引用** eligibility_report_id；在线训练资格的唯一权威仍是
      EligibilityReport，这里绝不复制其结论。
    - 版本事实**不是单值**：一次执行可跨多个 weight_version（fully async 下
      每轮模型调用各有版本）。`turn_weight_versions` 按轮次序保存原始序列，
      `intra_execution_version_span` 是派生视图（互检，不可手填任意值）。
    - `current_version_at_consume` / `worst_token_lag` 在 finalize 时刻**必须为
      None**——它们是 batch 消费时刻（FA-3 assembler）才存在的事实，由消费方
      另行落账（本对象冻结后不回写）。

    可信负样本口径：`present + task_outcome=unresolved`（reward=0 出自评分），
    **绝不是缺员**——见讨论稿 §2.1。
    """

    schema_id: Literal["rh2.fa.rollout_attempt_outcome.v1"] = Field(
        default="rh2.fa.rollout_attempt_outcome.v1", description="schema 判别字段。"
    )
    outcome_id: NonEmptyStr = Field(description="本记录唯一 id。")
    identity: ExecutionIdentity = Field(
        description="执行身份（branch_id 通常为 None——这是执行级账目）。"
    )
    member_slot: int = Field(ge=0, description="在 PromptGroup 内占用的成员槽位（0..n-1）。")
    attempt_number: int = Field(
        ge=1, description="第几次 attempt（首次=1；局部重试不增加，重新采样才增加——首版禁用后者）。"
    )
    completion_class: CompletionClass = Field(description="执行完成类别（三值）。")
    task_outcome: TaskOutcome = Field(
        description="任务结局（present 时必须是 resolved/unresolved；缺失/拒绝时用 unknown）。"
    )
    failure_category: RuntimeFailureCategory | None = Field(
        default=None, description="执行期失败归因（completion_class=present 时必须为 None）。"
    )
    failed_component: NonEmptyStr | None = Field(
        default=None, description="失败组件（如 grading_container / model_proxy / sandbox）。"
    )
    recovery_scope: RecoveryScope = Field(
        description="已采取/判定的恢复范围（fail-closed：none 表示无恢复动作）。"
    )
    turn_weight_versions: list[NonEmptyStr] = Field(
        default_factory=list,
        description=(
            "逐轮真实 weight_version 序列（按轮次序，保留重复；来源 = 引擎 "
            "meta_info.weight_version 经 turn tape 透传）。present 时至少 1 条。"
        ),
    )
    intra_execution_version_span: int | None = Field(
        default=None,
        ge=0,
        description=(
            "执行内版本跨度（max-min；派生视图，须与 derive_weight_version_max_lag "
            "重算一致；含非数值版本时必须为 None）。"
        ),
    )
    current_version_at_finalize: NonEmptyStr | None = Field(
        default=None,
        description="finalize 时刻的 current policy version（引擎实测；present 时必填）。",
    )
    current_version_at_consume: NonEmptyStr | None = Field(
        default=None,
        description="批次消费时刻的 current version——finalize 冻结时必须为 None（FA-3 另行落账）。",
    )
    worst_token_lag: int | None = Field(
        default=None,
        ge=0,
        description="消费时刻的最坏 token 版本滞后——finalize 冻结时必须为 None（FA-3 另行落账）。",
    )
    eligibility_report_id: NonEmptyStr | None = Field(
        default=None,
        description="EligibilityReport 引用（present 时必填；资格权威在报告本体，此处只引用）。",
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="证据引用（audit/失败记录/capture 等）。"
    )

    @model_validator(mode="after")
    def _check_class_consistency(self) -> "RolloutAttemptOutcome":
        if self.completion_class == "present":
            if self.task_outcome == "unknown":
                raise ValueError("present 成员的 task_outcome 不允许 unknown（评分事实必须在场）。")
            if self.failure_category is not None:
                raise ValueError("present 成员不允许携带 failure_category（在场≠失败）。")
            if self.eligibility_report_id is None:
                raise ValueError(
                    "present 成员必须引用 eligibility_report_id（资格权威在 EligibilityReport，"
                    "本记录不复制结论但必须可回链）。"
                )
            if not self.turn_weight_versions:
                raise ValueError("present 成员必须携带至少 1 条逐轮 weight_version。")
            if self.current_version_at_finalize is None:
                raise ValueError(
                    "present 成员必须携带 current_version_at_finalize"
                    "（staleness 计算基准；字段说明即契约，codex FA-0 审查修正）。"
                )
        else:
            if self.task_outcome != "unknown":
                raise ValueError(
                    f"{self.completion_class} 的 task_outcome 必须是 unknown"
                    "（评分事实不完整时不得声称任务结局）。"
                )
            if self.completion_class == "missing_after_local_retry" and self.failure_category is None:
                raise ValueError("missing_after_local_retry 必须携带 failure_category 归因。")
        expected_span = derive_weight_version_max_lag(self.turn_weight_versions or [])
        if self.turn_weight_versions and self.intra_execution_version_span != expected_span:
            raise ValueError(
                f"intra_execution_version_span({self.intra_execution_version_span}) 与重算不符："
                f"turn_weight_versions={list(self.turn_weight_versions)} => 应为 {expected_span}。"
            )
        if self.current_version_at_consume is not None or self.worst_token_lag is not None:
            raise ValueError(
                "current_version_at_consume / worst_token_lag 是消费时刻事实，"
                "finalize 冻结记录中必须为 None（FA-3 assembler 另行落账）。"
            )
        return self


# ---------------------------------------------------------------------------
# F2-1b：Outcome v2（FA-2A 决策包 D1a 批准语义；v1 冻结不原地改）
# ---------------------------------------------------------------------------

# termination_kind 五族（决策包 D1a 第 1 条逐字枚举；D4 风格集合等式测试
# 保证五族两两不交且并集 = TerminationKind 全集）。
TerminationKind = Literal[
    # 策略 horizon 族（可复现，截断有效的候选）
    "task_token_budget_exhausted",
    "max_turns_exhausted",
    "context_limit_reached",
    # 看门狗族（仅 termination trigger，completion 由事实推导——五审 4.2）
    "hard_wall_timeout",
    # 控制面族
    "owner_cancelled",
    # 基础设施族（⇒ completion=missing，reward=None，进 fault domain 计数）
    "inference_timeout",
    "sandbox_rpc_timeout",
    "update_wait_timeout",
    "harness_crash",
    "api_failure",
    "sandbox_failure",
    "model_call_regeneration_exhausted",
    # 正常族
    "completed",
]

TERMINATION_KINDS_POLICY_HORIZON = frozenset(
    {"task_token_budget_exhausted", "max_turns_exhausted", "context_limit_reached"}
)
TERMINATION_KINDS_WATCHDOG = frozenset({"hard_wall_timeout"})
TERMINATION_KINDS_CONTROL = frozenset({"owner_cancelled"})
TERMINATION_KINDS_INFRA = frozenset(
    {
        "inference_timeout",
        "sandbox_rpc_timeout",
        "update_wait_timeout",
        "harness_crash",
        "api_failure",
        "sandbox_failure",
        "model_call_regeneration_exhausted",
    }
)
TERMINATION_KINDS_NORMAL = frozenset({"completed"})

# failure category 三分封闭集合（F2-1b codex 审查 P1-1，D4 风格）：
# RuntimeFailureCategory 是整个生命周期的归因池，但 finalize Outcome v2
# 只许出现前两类——第三类是准入/控制/审计时刻的判定，混进执行归因会把
# 完整成员倒写成缺员（例：staleness 是消费时刻 present_but_not_admissible
# 的理由，不是"执行未产生"）。分区等式由导入自检 + 13×3 矩阵测试保证。
FAILURE_CATEGORIES_EXECUTION_FACT = frozenset({
    # missing 的合法归因：执行事实未完整产生的原因
    "model_proxy_failure",
    "inference_service_failure",
    "sandbox_crash",
    "harness_crash",
    "worker_crash",
    "capture_incomplete",
    "token_alignment_failure",
    "runtime_quiescence_failure",  # T0 2026-08-15：屏障执行失败 ⇒ missing 合法归因
})
FAILURE_CATEGORIES_GRADING = frozenset({
    # present_* 的唯一合法归因（勘误 2 受控通道：评分故障只动 reward）
    "grading_infra_failure",
})
FAILURE_CATEGORIES_ADMISSION_CONTROL = frozenset({
    # 准入/控制/审计判定——不得进入 finalize Outcome v2 的任何 completion
    "staleness_exceeded",   # 消费时刻准入（present_but_not_admissible）
    "security_violation",   # 准入永久拒绝材料（AdmissionReport/审计面）
    "identity_conflict",    # task quarantine 控制面归因
    "contract_violation",   # run halt 控制面归因
    "cleanup_failure",      # 执行事实冻结之后的运维故障
})

# 分区导入自检（D4 风格）：三集合并集 = RuntimeFailureCategory 全集且
# 两两不交——枚举加值而三分漏编时导入即炸，不等测试跑。
_FC_FAMILIES = (
    FAILURE_CATEGORIES_EXECUTION_FACT,
    FAILURE_CATEGORIES_GRADING,
    FAILURE_CATEGORIES_ADMISSION_CONTROL,
)
assert frozenset().union(*_FC_FAMILIES) == frozenset(get_args(RuntimeFailureCategory)), \
    "failure category 三分并集 != 全集"
assert sum(len(f) for f in _FC_FAMILIES) == len(get_args(RuntimeFailureCategory)), \
    "failure category 三分存在交叠"

# completion 三值事实层（决策包 D1a 推导关系）：只由 runtime/capture/
# quiescence/snapshot 完整性决定（勘误 2：评分事实不参与 completion）。
# v1 的 permanent_rejection 是**准入判定**不是 completion 事实，v2 不再
# 作为 completion 取值——由 PromptGroupAdmissionReport（FA-2）承载。
CompletionClassV2 = Literal["present_complete", "present_truncated", "missing"]

# 勘误 3 配套（F2-2 复核三轮 P1-1）：runtime_quiescence_failure 的合法
# reason_code 封闭集合——屏障五个失败点，双向绑定（该类别必配其一；
# 这些码也只属于该类别）。
RUNTIME_QUIESCENCE_REASON_CODES = frozenset({
    "execution_scope_termination_timeout",
    "active_writer_detected",
    "late_model_request_detected",
    "snapshot_freeze_failed",
    "snapshot_integrity_mismatch",
})


class RolloutAttemptOutcomeV2(StrictModel):
    """Outcome v2：终止事实与处置分离后的执行结果记录（F2-1b）。

    与 v1 的语义差（六审 2 + 勘误 2，新增 v2 不原地改 v1）：

    - completion_class 换为三值**事实层**枚举——present_complete /
      present_truncated / missing；v1 的 permanent_rejection（准入判定）
      不在此层。
    - 新增 termination_kind（五族）+ reason_code：终止 trigger、故障域、
      具体原因三层分离（D-FA-3：重生成耗尽 = termination_kind=
      model_call_regeneration_exhausted + failure_category=
      model_proxy_failure + reason_code=max_regenerations_exceeded）。
    - 勘误 2 硬化：评分基建故障只令 reward 不可用（reward_unavailable=
      True + task_outcome=unknown），**不倒写** completion——v1 里
      "present 必须有评分结局"的约束在 v2 放开为该受控通道。
    - 版本事实/消费时刻字段/资格引用等约束与 v1 相同（span 互检、
      consume 时刻必须 None、present_* 必须可回链 eligibility）。
    """

    schema_id: Literal["rh2.fa.rollout_attempt_outcome.v2"] = Field(
        default="rh2.fa.rollout_attempt_outcome.v2", description="schema 判别字段。"
    )
    outcome_id: NonEmptyStr = Field(description="本记录唯一 id。")
    identity: ExecutionIdentity = Field(
        description="执行身份（branch_id 通常为 None——这是执行级账目）。"
    )
    member_slot: int = Field(ge=0, description="在 PromptGroup 内占用的成员槽位（0..n-1）。")
    attempt_number: int = Field(
        ge=1, description="第几次 attempt（首次=1；局部重试不增加，重新采样才增加——首版禁用后者）。"
    )
    completion_class: CompletionClassV2 = Field(
        description="事实层完成类别（present_complete/present_truncated/missing）。"
    )
    termination_kind: TerminationKind = Field(
        description="终止 trigger（五族；触发者身份不决定事实完整性——五审 4.2）。"
    )
    failure_category: RuntimeFailureCategory | None = Field(
        default=None,
        description=(
            "故障域归因（三层分离第二层）。missing 必填；present_* 只允许 "
            "None 或 grading_infra_failure（勘误 2 受控通道）。"
        ),
    )
    reason_code: NonEmptyStr | None = Field(
        default=None,
        description="具体原因码（三层分离第三层；如 max_regenerations_exceeded）。",
    )
    failed_component: NonEmptyStr | None = Field(
        default=None, description="失败组件（如 grading_container / model_proxy / sandbox）。"
    )
    recovery_scope: RecoveryScope = Field(
        description="已采取/判定的恢复范围（fail-closed：none 表示无恢复动作）。"
    )
    task_outcome: TaskOutcome = Field(
        description="任务结局（reward 可用时 resolved/unresolved；不可用时 unknown）。"
    )
    reward_unavailable: bool = Field(
        default=False,
        description=(
            "reward 不可用标记（⟺ task_outcome=unknown）。present_* 时为 True "
            "表示评分故障/未评分——completion 事实不因此改写（勘误 2）。"
        ),
    )
    turn_weight_versions: list[NonEmptyStr] = Field(
        default_factory=list,
        description="逐轮真实 weight_version 序列（同 v1：按轮次序，保留重复）。",
    )
    intra_execution_version_span: int | None = Field(
        default=None, ge=0,
        description="执行内版本跨度（派生视图，须与重算一致；同 v1）。",
    )
    current_version_at_finalize: NonEmptyStr | None = Field(
        default=None, description="finalize 时刻 current policy version（present_* 必填）。"
    )
    current_version_at_consume: NonEmptyStr | None = Field(
        default=None, description="消费时刻事实——finalize 冻结时必须为 None（同 v1）。"
    )
    worst_token_lag: int | None = Field(
        default=None, ge=0,
        description="消费时刻最坏 token 滞后——finalize 冻结时必须为 None（同 v1）。",
    )
    eligibility_report_id: NonEmptyStr | None = Field(
        default=None, description="EligibilityReport 引用（present_* 必填；权威在报告本体）。"
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="证据引用（audit/失败记录/capture/评分报告等）。"
    )

    @model_validator(mode="after")
    def _check_v2_consistency(self) -> "RolloutAttemptOutcomeV2":
        cc, tk = self.completion_class, self.termination_kind
        # --- completion ⟷ termination 一致性（D1a 推导关系的契约面）---
        if cc == "present_complete" and tk != "completed":
            raise ValueError(
                f"present_complete 只能来自 termination_kind=completed（得到 {tk}）——"
                "非正常终止的完整轨迹是 present_truncated。"
            )
        if cc == "present_truncated" and tk not in (
            TERMINATION_KINDS_POLICY_HORIZON
            | TERMINATION_KINDS_WATCHDOG
            | TERMINATION_KINDS_CONTROL
        ):
            raise ValueError(
                f"present_truncated 只允许 horizon/看门狗/控制面终止（得到 {tk}）。"
            )
        # D1a"基础设施族 ⇒ missing"由上两条规则蕴含（infra ∉ {completed} ∪
        # 截断族），不再重复分支——穷举测试验证该推导
        # --- 三层分离钉子（D-FA-3）---
        if tk == "model_call_regeneration_exhausted" and (
            self.failure_category != "model_proxy_failure"
            or self.reason_code != "max_regenerations_exceeded"
        ):
            raise ValueError(
                "model_call_regeneration_exhausted 必须三层齐备："
                "failure_category=model_proxy_failure + "
                "reason_code=max_regenerations_exceeded。"
            )
        # --- failure_category 归属（三分封闭集合，P1-1）---
        if cc == "missing" and self.failure_category not in FAILURE_CATEGORIES_EXECUTION_FACT:
            raise ValueError(
                f"missing 的 failure_category 必须属于执行事实集合"
                f"（得到 {self.failure_category}）——评分/准入/控制面归因"
                "不得倒写 completion（勘误 2 + 消费时刻判定分离）。"
            )
        if cc != "missing" and self.failure_category not in (None, "grading_infra_failure"):
            raise ValueError(
                f"present_* 只允许 failure_category ∈ {{None, grading_infra_failure}}"
                f"（得到 {self.failure_category}）——执行没失败，失败归因属 missing。"
            )
        # --- 四层身份强制（P1-2，D2/F2-1a）：v2 是正式 execution 级账目 ---
        if self.identity.physical_attempt_id is None:
            raise ValueError(
                "Outcome v2 必须携带 physical_attempt_id（crash replay 的两次"
                "物理 attempt 否则不可区分——D2 四层身份）。"
            )
        if self.identity.branch_id is not None:
            raise ValueError(
                "Outcome v2 是 execution 级账目，identity.branch_id 必须为 None"
                "（branch 聚合在投影层，不在执行结果层）。"
            )
        # --- 勘误 3（P1-1）：runtime_quiescence_failure ⟺ 五 reason code ---
        if self.failure_category == "runtime_quiescence_failure" and (
            self.reason_code not in RUNTIME_QUIESCENCE_REASON_CODES
        ):
            raise ValueError(
                f"runtime_quiescence_failure 的 reason_code 必须属于屏障五失败点"
                f"（得到 {self.reason_code!r}）——勘误 3 封闭集合。"
            )
        if (
            self.reason_code in RUNTIME_QUIESCENCE_REASON_CODES
            and self.failure_category != "runtime_quiescence_failure"
        ):
            raise ValueError(
                f"reason_code={self.reason_code!r} 专属 runtime_quiescence_failure"
                f"（得到 failure_category={self.failure_category}）。"
            )
        # --- 勘误 2：reward 可用性 ⟺ task_outcome，completion 不参与 ---
        if (self.task_outcome == "unknown") != self.reward_unavailable:
            raise ValueError(
                "task_outcome=unknown ⟺ reward_unavailable=True（reward 不可用时"
                "不得声称任务结局；可用时必须给出结局）。"
            )
        if cc == "missing" and self.task_outcome != "unknown":
            raise ValueError("missing 的 task_outcome 必须 unknown（评分事实不完整）。")
        if self.failure_category == "grading_infra_failure" and not self.reward_unavailable:
            raise ValueError("grading_infra_failure ⇒ reward_unavailable=True（勘误 2）。")
        # --- present_* 事实完整性要求（同 v1 present）---
        if cc != "missing":
            if not self.turn_weight_versions:
                raise ValueError("present_* 必须携带至少 1 条逐轮 weight_version。")
            if self.current_version_at_finalize is None:
                raise ValueError("present_* 必须携带 current_version_at_finalize。")
            if self.eligibility_report_id is None and not self.reward_unavailable:
                raise ValueError(
                    "present_* 必须引用 eligibility_report_id（例外：reward_"
                    "unavailable=True 时资格链未运行——A-prime 失败表 unsafe/"
                    "评分不可得两行的 present 事实不伪造资格引用；pre-formal "
                    "原地修订 2026-08-17）。"
                )
        # --- 版本派生互检 + 消费时刻冻结（同 v1）---
        expected_span = derive_weight_version_max_lag(self.turn_weight_versions or [])
        if self.turn_weight_versions and self.intra_execution_version_span != expected_span:
            raise ValueError(
                f"intra_execution_version_span({self.intra_execution_version_span}) 与重算不符："
                f"应为 {expected_span}。"
            )
        if self.current_version_at_consume is not None or self.worst_token_lag is not None:
            raise ValueError(
                "current_version_at_consume / worst_token_lag 是消费时刻事实，"
                "finalize 冻结记录中必须为 None。"
            )
        return self


TrainingRuntimePhase = Literal["ACTIVE", "PAUSING", "UPDATING", "RESUMING"]


class TrainingRuntimeWindow(StrictModel):
    """一次权重更新窗口的协调协议事实（FA-0 3b，codex 轮次 3 #2）。

    权重更新、RolloutManager、model proxy 与 trainer 位于不同 Ray actor/线程，
    "更新窗口"必须是显式传播的协议对象，不能依赖进程内内存事件。proxy 判定
    "更新窗口 abort"（D-FA-3 守卫条件）**只信本协议**：

    - 失败时间落在 [window_started_at, window_completed_at or now]；
    - fencing_token 与 proxy 已知的最新窗口一致（防陈旧窗口误判）；
    - 恢复后 active_version == target_version（版本确实前进了）。

    phase 语义：ACTIVE = 窗口已完成、引擎在 target_version 上正常服务；
    PAUSING/UPDATING/RESUMING = 窗口进行中（window_completed_at 必须为 None）。
    """

    schema_id: Literal["rh2.fa.training_runtime_window.v1"] = Field(
        default="rh2.fa.training_runtime_window.v1", description="schema 判别字段。"
    )
    update_epoch: int = Field(ge=0, description="第几次权重更新（单调递增计数器）。")
    phase: TrainingRuntimePhase = Field(description="窗口阶段。")
    old_version: NonEmptyStr = Field(description="更新前引擎版本。")
    target_version: NonEmptyStr = Field(description="更新目标版本。")
    active_version: NonEmptyStr = Field(
        description="当前引擎实际服务版本（ACTIVE 时必须 == target_version）。"
    )
    window_started_at: AwareDatetime = Field(description="窗口开始时刻（pause 发起，带时区）。")
    window_completed_at: AwareDatetime | None = Field(
        default=None, description="窗口完成时刻（continue 返回后；进行中为 None）。"
    )
    fencing_token: NonEmptyStr = Field(
        description="防陈旧窗口的 fencing token（每个窗口唯一，消费方比对最新值）。"
    )

    @model_validator(mode="after")
    def _check_phase_consistency(self) -> "TrainingRuntimeWindow":
        if self.old_version == self.target_version:
            raise ValueError(
                f"target_version({self.target_version}) == old_version——权重更新窗口"
                "必须使版本前进，无前进的窗口是事实矛盾（codex FA-0 审查修正）。"
            )
        if self.phase == "ACTIVE":
            if self.window_completed_at is None:
                raise ValueError("phase=ACTIVE 表示窗口已完成，window_completed_at 必填。")
            if self.active_version != self.target_version:
                raise ValueError(
                    f"phase=ACTIVE 时 active_version({self.active_version}) 必须等于 "
                    f"target_version({self.target_version})——版本没有前进不能宣布 ACTIVE。"
                )
        else:
            if self.window_completed_at is not None:
                raise ValueError(f"phase={self.phase} 表示窗口进行中，window_completed_at 必须为 None。")
        if self.window_completed_at is not None and self.window_completed_at < self.window_started_at:
            raise ValueError("window_completed_at 早于 window_started_at（时钟事实矛盾）。")
        return self


ModelCallDeliveryStatus = Literal[
    "delivered",  # 完整响应已交付 harness
    "non_delivered_aborted",  # 被权重更新窗口 abort，从未交付（proxy 内部重生成的前一 attempt）
    "non_delivered_failed",  # 其他原因未交付（不可归因中断走缺员分支）
]


class ModelCallAttempt(StrictModel):
    """一次模型调用 attempt 的账目（FA-0 3c；D-FA-3 proxy 内部重生成的留痕单位）。

    同一逻辑轮（logical_turn_id）可有多个 attempt：更新窗口 abort 的
    attempt_1 记 non_delivered_aborted，attempt_2 成功记 delivered——
    **只有 delivered 的 attempt 才允许有 capture 记录进入训练面**；
    non-delivered 的半截输出是 mask 无关物，只留审计。
    """

    schema_id: Literal["rh2.fa.model_call_attempt.v1"] = Field(
        default="rh2.fa.model_call_attempt.v1", description="schema 判别字段。"
    )
    physical_attempt_id: NonEmptyStr | None = Field(
        default=None,
        description="F2-1a：所属物理重放身份（wire 经 registry 的 sid→paid 映射填入；可选）。",
    )
    logical_turn_id: NonEmptyStr = Field(
        description="逻辑轮 id（同一 harness 轮的多个 attempt 共享；示例：turn_7）。"
    )
    model_call_attempt_id: NonEmptyStr = Field(description="attempt 唯一 id。")
    attempt_number: int = Field(ge=1, description="同一逻辑轮内第几次 attempt。")
    delivery_status: ModelCallDeliveryStatus = Field(description="交付状态（三值）。")
    capture_record_ref: NonEmptyStr | None = Field(
        default=None,
        description="capture 记录引用（delivered 时必填；non-delivered 的审计物另走 evidence_refs）。",
    )
    abort_update_epoch: int | None = Field(
        default=None,
        ge=0,
        description="导致 abort 的更新窗口 update_epoch（non_delivered_aborted 时必填）。",
    )
    abort_fencing_token: NonEmptyStr | None = Field(
        default=None,
        description=(
            "导致 abort 的窗口 fencing_token（non_delivered_aborted 时必填）——"
            "证明 abort 确实与该次更新窗口重叠，防止陈旧窗口误归因（codex FA-0 审查）。"
        ),
    )
    weight_version: NonEmptyStr | None = Field(
        default=None, description="本 attempt 实际使用的引擎版本（delivered 时必填）。"
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="审计证据（含 non-delivered 半截输出的留痕引用）。"
    )
    # F2-0b Observability V0（optional **原始区间**，只记录不改判定）：proxy
    # 侧四段等待/发送的成对 monotonic start/end + clock_domain（codex F2-0b
    # P1-3：存原始区间而非派生 duration——才能合并重叠 non-chargeable 区间、
    # 校验同 clock domain、重建时间线；四段 = ACTIVE 等待/限流等待/权重恢复
    # 等待/发送）。填值随 F2-3 request 归属重写同批（本切片只加形状）。
    timing_clock_domain: NonEmptyStr | None = Field(
        default=None, description="上述区间所属进程级 clock domain（同 domain 才可减）。"
    )
    wait_active_interval: tuple[float, float] | None = Field(
        default=None, description="发前 ACTIVE 等待 (start,end) monotonic。"
    )
    limiter_wait_interval: tuple[float, float] | None = Field(
        default=None, description="model_call 限流等待 (start,end) monotonic。"
    )
    wait_version_interval: tuple[float, float] | None = Field(
        default=None, description="abort 后版本恢复等待 (start,end) monotonic。"
    )
    send_interval: tuple[float, float] | None = Field(
        default=None, description="send_fn 往返 (start,end) monotonic。"
    )

    @model_validator(mode="after")
    def _check_timing_intervals(self) -> "ModelCallAttempt":
        interval_names = (
            "wait_active_interval", "limiter_wait_interval",
            "wait_version_interval", "send_interval",
        )
        any_interval = False
        for name in interval_names:
            iv = getattr(self, name)
            if iv is not None:
                any_interval = True
                if iv[1] < iv[0]:
                    raise ValueError(f"{name} end < start（非法区间）。")
        # F2-0b 复核 P1-A：区间 ⟺ clock domain **双向一致**——脱离 domain 的
        # 区间违反"同 clock domain 才允许相减"核心不变量（F2-3 若填入这种
        # 记录将无法安全合并 non_chargeable_intervals）
        if any_interval and self.timing_clock_domain is None:
            raise ValueError("存在计时区间但 timing_clock_domain 缺失（区间必须锚定时钟域）。")
        if not any_interval and self.timing_clock_domain is not None:
            raise ValueError("timing_clock_domain 存在但无任何区间（悬空时钟域声明）。")
        return self

    @model_validator(mode="after")
    def _check_delivery_consistency(self) -> "ModelCallAttempt":
        if self.delivery_status == "delivered":
            if self.capture_record_ref is None:
                raise ValueError("delivered 的 attempt 必须回链 capture 记录。")
            if self.weight_version is None:
                raise ValueError(
                    "delivered 的 attempt 必须携带 weight_version"
                    "（交付即 provenance 事实，缺失让 DIS 无法归因）。"
                )
        if self.delivery_status != "delivered" and self.capture_record_ref is not None:
            raise ValueError(
                "non-delivered 的 attempt 不得回链 capture 记录"
                "（半截输出是审计物，不是训练面事实——防止误入投影）。"
            )
        if self.delivery_status == "non_delivered_aborted" and (
            self.abort_update_epoch is None or self.abort_fencing_token is None
        ):
            raise ValueError(
                "non_delivered_aborted 必须同时记录 abort_update_epoch 与 abort_fencing_token"
                "（窗口归因的双凭据）。"
            )
        return self
