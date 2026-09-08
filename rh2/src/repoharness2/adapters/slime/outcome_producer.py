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
    FAILURE_CATEGORIES_EXECUTION_FACT,
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
#
# 批 A（I05，2026-09-09，第二组 §2 / 06 §2）：本表 = "已归因、局限于单次 execution 的
# task-local 故障"的**穷举**。只有 reason_code 在本表内的 SlimeBindingError 才允许在
# finalize 前收口为 missing/ABORTED（miles 补采）；不在表内的 typed 码与任何非 typed
# 异常由 generate.py 的 except 链按 `pre_finalize_failure_unclassified` run-halt——
# "不可归因/结构性损坏 = typed run-fatal，不补采"。此前未登记的码走 STAGE_FALLBACK
# 并在审计里记 unmapped_failure_code，那条路今后只剩 ValidationError（无 reason_code）
# 与 s1_compat 冻结路径。
FAILURE_CODE_TERMINATION_MAP: dict[str, tuple[TerminationKind, RuntimeFailureCategory]] = {
    # 模型代理面：poison = 不可归因中断（proxy 判定后毒化会话）
    "session_poisoned_during_execution": ("api_failure", "model_proxy_failure"),
    # materialize 面（W3b/W3a 既有 typed 码：镜像 / 容器 / 私有网络 / 工作区 / 基线读取——
    # docker 或任务镜像层面的单次失败）。此前经 STAGE_FALLBACK 归 sandbox_failure，
    # 处置不变，改为显式登记。
    "rollout_image_inspect_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_image_ref_inspect_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_container_start_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_base_untracked_snapshot_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_workspace_write_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_git_sanitize_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_trusted_init_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_egress_network_failed": ("sandbox_failure", "sandbox_crash"),
    "rollout_egress_relay_connect_failed": ("sandbox_failure", "sandbox_crash"),
    "baseline_head_unreadable": ("sandbox_failure", "sandbox_crash"),
    # harness 面。harness_bootstrap_failed（批 A 新增）= 驱动引导（装 CLI / useradd /
    # 写配置 / spawn）时 sandbox exec 失败——单次容器层面故障，不是我方代码矛盾。
    "harness_bootstrap_failed": ("harness_crash", "harness_crash"),
    "nonzero_harness_exit_in_formal_chain": ("harness_crash", "harness_crash"),
    # 身份面：Brief §6 待确认项。今天 stage="identity" 不在 STAGE_FALLBACK 内，缺省归
    # harness_crash；确认前处置不变、只做显式登记。
    "fa_identity_incomplete_in_formal_mode": ("harness_crash", "harness_crash"),
    # capture 关账面：执行本身跑完了（completed），账目不完整 → missing
    "session_plane_drain_unclean": ("completed", "capture_incomplete"),
    "capture_boundary_unclean": ("completed", "capture_incomplete"),
    "no_capture_records": ("completed", "capture_incomplete"),
    "adapter_session_empty": ("completed", "capture_incomplete"),
    # D-FA-6：上下文收缩 = provenance 不可信 → 账目层拒绝
    "context_shrink_detected": ("completed", "capture_incomplete"),
    # Brief §6 待确认项（今天经 STAGE_FALLBACK 归 capture_incomplete；确认前处置不变、显式登记）
    "sampling_mask_tape_missing_in_assembly": ("completed", "capture_incomplete"),
    "frozen_artifact_persist_failed": ("completed", "capture_incomplete"),
    # Brief §6 待确认项（Codex 计划审查 R1：inspect **成功读取**后发现镜像 digest / testbed
    # 血缘与冻结事实不符，是确定性的环境完整性矛盾而非单次运行故障，建议 FATAL）。
    # 今天经 STAGE_FALLBACK 归 sandbox_failure；确认前处置不变、显式登记。
    "rollout_image_digest_mismatch": ("sandbox_failure", "sandbox_crash"),
    "rollout_testbed_lineage_failed": ("sandbox_failure", "sandbox_crash"),
    # B2 exporter 失败族（A-prime 失败表第 1 行：无可信冻结输入 = missing）
    "post_census_failed": ("completed", "capture_incomplete"),
    "post_census_parse_failed": ("completed", "capture_incomplete"),
    "content_fetch_failed": ("completed", "capture_incomplete"),
    "content_fetch_incomplete": ("completed", "capture_incomplete"),
    "content_digest_race": ("completed", "capture_incomplete"),
    # unsupported_object_in_patch：B3 起在 generate 特殊分支收口为
    # present + 永久拒绝（unsafe 行），不再经本表——不留可退回 missing
    # 的旧行（B3 closure oracle 1）
}

# 批 A（I05）：第二组 §1 点名的两个账实矛盾码——"树侧给两条训练分支，却只给一份配套事实"
# = leaf_facts_length_mismatch；"capture 返回引用但没有对应 TurnTape" =
# capture_record_unknown_in_backfill——此前在上表内按 capture_incomplete 收口为 ABORTED，
# 现在**不在**上表 ⇒ generate.py 按 pre_finalize_failure_unclassified run-halt（回归见
# tests/adapters/test_w1b_termination_facts_producer.py 的 5d）。判定只看"是否在上表"，
# 不另设集合。

# 无 reason_code 的异常（finalize 前 ValidationError，Brief §6 待确认项）与 s1_compat 冻结路径
# 按失败阶段兜底（保守：宁可归 infra/missing，不猜 present）。批 A 起 typed 码不再走本表。
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
        or (
            eligibility_report_id is None
            and not (
                failure_category == "grading_infra_failure"
                or (
                    reason_code == "unsafe_artifact_permanent_rejection"
                    and failed_component == "patch_hygiene"
                    and task_resolved is None  # 谓词一致：reward 必不可得
                    and failure_category is None
                )
            )
        )
        # eligibility 豁免 = v2 契约封闭集合（与 is_unsafe_artifact_
        # rejection_shape 谓词一致；schema validator 兜底全形状）
    ):
        completion = "missing"
        failure_category = "capture_incomplete"
        reason_code = reason_code or "present_facts_unavailable"
    if completion == "missing":
        # missing 归因必须属执行事实集合；调用方未给时兜底 capture_incomplete
        # （missing 的两条推导来源之一就是账目不完整）
        # 复核二轮一般 1：归因过滤到执行事实集合——评分归因（grading_
        # infra_failure）不得混进 missing（勘误 2），真实评分故障经
        # failed_component/evidence 保留，不制造内部 ValidationError
        fc = (
            failure_category
            if failure_category in FAILURE_CATEGORIES_EXECUTION_FACT
            else "capture_incomplete"
        )
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
