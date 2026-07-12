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

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from ._base import NonEmptyStr, StrictModel
from .trajectory import derive_weight_version_max_lag

__all__ = [
    "CompletionClass",
    "ExecutionIdentity",
    "ModelCallAttempt",
    "ModelCallDeliveryStatus",
    "RecoveryScope",
    "RolloutAttemptOutcome",
    "RuntimeFailureCategory",
    "TaskOutcome",
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
