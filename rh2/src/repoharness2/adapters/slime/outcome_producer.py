"""F2-2：正式链 Outcome v2 producer——按完整性事实构造执行结果记录。

定位（05 计划 F2-1b 完成口径 + F2-2 起验收）：F2-1b 只交付了 schema 与
crosswalk；本模块是**生产 finalize → Outcome v2 的接线起点**。orchestrator
在每次 execution 收口时（成功路径与异常路径都）调用 `build_outcome_v2`，
由**事实**推导 completion——不是由调用方直接指定 completion（防"先射箭
再画靶"）。

completion 推导（决策包 D1a，勘误 2）：

    termination ∈ 基础设施族            → missing
    quiescence 未确认 ∨ capture 未关账  → missing（capture_incomplete）
    termination = completed             → present_complete
    termination ∈ horizon/看门狗/控制面 → present_truncated

勘误 2 通道：评分基建故障（reward 不可得）**不改 completion**——
task_outcome=unknown + reward_unavailable=True + grading_infra_failure。

矛盾组合兜底（codex F2-1b 二轮非阻塞项）：schema 在 termination×failure
完整交叉表拍板前不禁止所有可疑组合，producer 层先行保证——本模块的
映射表 + 推导函数是全部构造入口，属性测试穷举其输入域证明产物全部
过 v2 validator 且无"completed + harness_crash + missing"这类明显矛盾。

S1 兼容：metadata 无四层身份（physical_attempt_id/seq）时**不产 v2**
（v2 强制四层身份，宁缺毋伪造）——返回 None，调用方留审计注记。
"""

from __future__ import annotations

from typing import Literal

from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_INFRA,
    TERMINATION_KINDS_NORMAL,
    ExecutionIdentity,
    RolloutAttemptOutcomeV2,
    RuntimeFailureCategory,
    TerminationKind,
)

__all__ = [
    "FAILURE_CODE_TERMINATION_MAP",
    "STAGE_FALLBACK_TERMINATION_MAP",
    "build_outcome_v2",
    "derive_completion",
]

# SlimeBindingError code → (termination_kind, failure_category)。
# 键 = generate.py 实际抛出的错误码（穷举当前存在的收口路径；新增错误码
# 走 STAGE_FALLBACK 兜底并在审计里可见 reason_code=unmapped_failure_code）。
FAILURE_CODE_TERMINATION_MAP: dict[str, tuple[TerminationKind, RuntimeFailureCategory]] = {
    # 模型代理面：poison = 不可归因中断（proxy 判定后毒化会话）
    "session_poisoned_during_execution": ("api_failure", "model_proxy_failure"),
    # harness 面
    "nonzero_harness_exit_in_formal_chain": ("harness_crash", "harness_crash"),
    # capture 关账面：执行本身跑完了（completed），账目不完整 → missing
    "capture_boundary_unclean": ("completed", "capture_incomplete"),
    "no_capture_records": ("completed", "capture_incomplete"),
    "adapter_session_empty": ("completed", "capture_incomplete"),
    "leaf_facts_length_mismatch": ("completed", "capture_incomplete"),
    "capture_record_unknown_in_backfill": ("completed", "capture_incomplete"),
    # D-FA-6：上下文收缩 = provenance 不可信 → 账目层拒绝
    "context_shrink_detected": ("completed", "capture_incomplete"),
}

# 未知错误码按失败阶段兜底（保守：宁可归 infra/missing，不猜 present）。
STAGE_FALLBACK_TERMINATION_MAP: dict[str, tuple[TerminationKind, RuntimeFailureCategory]] = {
    "materialize": ("sandbox_failure", "sandbox_crash"),
    "harness_run": ("harness_crash", "harness_crash"),
    "assemble": ("completed", "capture_incomplete"),
    "finalize": ("completed", "capture_incomplete"),
    "deliver": ("completed", "capture_incomplete"),
}


def derive_completion(
    *,
    termination_kind: TerminationKind,
    quiescence_confirmed: bool,
    capture_closed: bool,
) -> Literal["present_complete", "present_truncated", "missing"]:
    """完整性事实 → completion（D1a 推导关系；评分事实不参与——勘误 2）。"""

    if termination_kind in TERMINATION_KINDS_INFRA:
        return "missing"
    if not (quiescence_confirmed and capture_closed):
        return "missing"
    if termination_kind in TERMINATION_KINDS_NORMAL:
        return "present_complete"
    return "present_truncated"


def build_outcome_v2(
    *,
    outcome_id: str,
    prompt_group_id: str | None,
    group_index: int,
    rollout_execution_id: str,
    physical_attempt_id: str | None,
    physical_attempt_seq: int | None,
    member_slot: int | None,
    termination_kind: TerminationKind,
    quiescence_confirmed: bool,
    capture_closed: bool,
    failure_category: RuntimeFailureCategory | None = None,
    reason_code: str | None = None,
    failed_component: str | None = None,
    task_resolved: bool | None = None,
    turn_weight_versions: list[str] | None = None,
    intra_execution_version_span: int | None = None,
    current_version_at_finalize: str | None = None,
    eligibility_report_id: str | None = None,
    evidence_refs: list[str] | None = None,
) -> RolloutAttemptOutcomeV2 | None:
    """由事实构造 v2；S1 兼容路径（无四层身份）返回 None。

    task_resolved：评分结局（True=resolved / False=unresolved / None=
    评分不可得——勘误 2：completion 不因此改写，reward_unavailable=True）。
    """

    if physical_attempt_id is None or physical_attempt_seq is None:
        return None  # v2 强制四层身份——S1 兼容路径宁缺毋伪造
    completion = derive_completion(
        termination_kind=termination_kind,
        quiescence_confirmed=quiescence_confirmed,
        capture_closed=capture_closed,
    )
    # present_* 要求完整事实链（逐轮版本 + finalize 版本 + 资格回链——v1
    # 起的 present 语义）。运行事实齐但 present 级字段缺 = 收口死在
    # finalize/deliver 中途，账目仍不完整 ⇒ missing（D1a"事实未完整产生"；
    # 与勘误 2 不冲突：评分不可得但字段齐的 failed_to_grade 路径照走
    # present + reward_unavailable）。
    if completion != "missing" and (
        not turn_weight_versions
        or current_version_at_finalize is None
        or eligibility_report_id is None
    ):
        completion = "missing"
        failure_category = "capture_incomplete"
        reason_code = reason_code or "present_facts_unavailable"
    if completion == "missing":
        # missing 归因必须属执行事实集合；调用方未给时兜底 capture_incomplete
        # （missing 的两条推导来源之一就是账目不完整）
        fc = failure_category or "capture_incomplete"
        task_outcome: Literal["resolved", "unresolved", "unknown"] = "unknown"
        reward_unavailable = True
    else:
        # present_*：执行没失败——失败归因只保留勘误 2 通道
        # （grading_infra_failure 且仅当评分确实不可得），其余不进 present 记录
        if task_resolved is None:
            fc = failure_category if failure_category == "grading_infra_failure" else None
            task_outcome = "unknown"
            reward_unavailable = True
        else:
            fc = None
            task_outcome = "resolved" if task_resolved else "unresolved"
            reward_unavailable = False
    return RolloutAttemptOutcomeV2(
        outcome_id=outcome_id,
        identity=ExecutionIdentity(
            prompt_group_id=prompt_group_id or rollout_execution_id,
            group_index=group_index,
            rollout_execution_id=rollout_execution_id,
            physical_attempt_id=physical_attempt_id,
            physical_attempt_seq=physical_attempt_seq,
        ),
        member_slot=member_slot if member_slot is not None else 0,
        attempt_number=1,  # 首版禁用重新采样（v1 同款语义）
        completion_class=completion,
        termination_kind=termination_kind,
        failure_category=fc,
        reason_code=reason_code,
        failed_component=failed_component,
        recovery_scope="none",
        task_outcome=task_outcome,
        reward_unavailable=reward_unavailable,
        turn_weight_versions=list(turn_weight_versions or []),
        intra_execution_version_span=intra_execution_version_span,
        current_version_at_finalize=current_version_at_finalize,
        eligibility_report_id=eligibility_report_id,
        evidence_refs=list(evidence_refs or []),
    )
