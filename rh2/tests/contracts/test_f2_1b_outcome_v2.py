"""F2-1b 验收：Outcome v2 契约语义 + v1→v2 crosswalk 穷举 + 双版本读取
+ src 无 v1 构造点守卫。

钉住的语义（05 计划 F2-1b 节 + 决策包 D1a/勘误 2/聚焦复核 4 + codex
F2-1b 审查三 P1）：completion 三值事实层；termination 五族集合等式；
failure category 三分封闭集合（13×3 矩阵）；三层分离钉子；勘误 2
（评分故障不倒写 completion）；v2 强制四层身份；permanent_rejection
永不映射 missing 且迁移产物 audit-only；无证据/无引用不捏造；
migrated_v2 fail-closed（不宣称训练资格）。
"""

from __future__ import annotations

from typing import get_args

import pytest

from repoharness2.contracts.fa_runtime import (
    FAILURE_CATEGORIES_ADMISSION_CONTROL,
    FAILURE_CATEGORIES_EXECUTION_FACT,
    FAILURE_CATEGORIES_GRADING,
    TERMINATION_KINDS_CONTROL,
    TERMINATION_KINDS_INFRA,
    TERMINATION_KINDS_NORMAL,
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    ExecutionIdentity,
    RolloutAttemptOutcome,
    RolloutAttemptOutcomeV2,
    RuntimeFailureCategory,
    TerminationKind,
)
from repoharness2.contracts.outcome_crosswalk import (
    OutcomeCrosswalkResult,
    V1TerminationEvidence,
    crosswalk_v1_to_v2,
    migrated_v2,
    read_rollout_attempt_outcome,
)


def _identity(**over) -> ExecutionIdentity:
    base = dict(
        prompt_group_id="g", group_index=0, rollout_execution_id="exec_1",
        physical_attempt_id="exec_1#p1-aaaa1111", physical_attempt_seq=1,
    )
    base.update(over)
    return ExecutionIdentity(**base)


def _v2(**over) -> RolloutAttemptOutcomeV2:
    base = dict(
        outcome_id="o", identity=_identity(), member_slot=0, attempt_number=1,
        completion_class="present_complete", termination_kind="completed",
        task_outcome="unresolved", recovery_scope="none",
        turn_weight_versions=["1"], intra_execution_version_span=0,
        current_version_at_finalize="1", eligibility_report_id="er",
    )
    base.update(over)
    return RolloutAttemptOutcomeV2(**base)


def _v2_missing_kwargs(**over) -> dict:
    base = dict(
        completion_class="missing", termination_kind="harness_crash",
        failure_category="harness_crash", task_outcome="unknown",
        reward_unavailable=True, turn_weight_versions=[],
        intra_execution_version_span=None, current_version_at_finalize=None,
        eligibility_report_id=None,
    )
    base.update(over)
    return base


def _v1(**over) -> RolloutAttemptOutcome:
    base = dict(
        outcome_id="v1o", identity=_identity(), member_slot=0, attempt_number=1,
        completion_class="present", task_outcome="unresolved", recovery_scope="none",
        turn_weight_versions=["1"], intra_execution_version_span=0,
        current_version_at_finalize="1", eligibility_report_id="er",
    )
    base.update(over)
    return RolloutAttemptOutcome(**base)


def _ev(tk: str, **over) -> V1TerminationEvidence:
    base = dict(termination_kind=tk, evidence_refs=["audit_x"])
    base.update(over)
    return V1TerminationEvidence(**base)


# ---------------------------------------------------------------------------
# 集合等式（D4 风格）：termination 五族 + failure category 三分
# ---------------------------------------------------------------------------

def test_termination_families_partition_exactly():
    families = [
        TERMINATION_KINDS_POLICY_HORIZON, TERMINATION_KINDS_WATCHDOG,
        TERMINATION_KINDS_CONTROL, TERMINATION_KINDS_INFRA, TERMINATION_KINDS_NORMAL,
    ]
    assert frozenset().union(*families) == frozenset(get_args(TerminationKind))
    assert sum(len(f) for f in families) == len(get_args(TerminationKind))  # 两两不交


def test_failure_category_partition_exactly():
    families = [
        FAILURE_CATEGORIES_EXECUTION_FACT, FAILURE_CATEGORIES_GRADING,
        FAILURE_CATEGORIES_ADMISSION_CONTROL,
    ]
    assert frozenset().union(*families) == frozenset(get_args(RuntimeFailureCategory))
    assert sum(len(f) for f in families) == len(get_args(RuntimeFailureCategory))


# ---------------------------------------------------------------------------
# v2 validator 语义
# ---------------------------------------------------------------------------

def test_present_complete_requires_completed_termination():
    with pytest.raises(ValueError, match="present_complete 只能来自"):
        _v2(termination_kind="hard_wall_timeout")


def test_present_truncated_families():
    for tk in ["task_token_budget_exhausted", "hard_wall_timeout", "owner_cancelled"]:
        if tk == "owner_cancelled":
            # 控制面取消默认不产生 reward → unknown + reward_unavailable
            _v2(completion_class="present_truncated", termination_kind=tk,
                task_outcome="unknown", reward_unavailable=True)
        else:
            _v2(completion_class="present_truncated", termination_kind=tk)
    with pytest.raises(ValueError, match="present_truncated 只允许"):
        _v2(completion_class="present_truncated", termination_kind="completed")


def test_infra_termination_forces_missing():
    """D1a：infra 族 ⇒ missing——由前两条规则蕴含，对两个 present 类别
    逐一验证 infra 全族都被拒。"""

    for tk in TERMINATION_KINDS_INFRA:
        with pytest.raises(ValueError):
            _v2(termination_kind=tk)  # present_complete
        with pytest.raises(ValueError):
            _v2(completion_class="present_truncated", termination_kind=tk)
    _v2(**_v2_missing_kwargs(termination_kind="sandbox_failure",
                             failure_category="sandbox_crash"))


def test_three_layer_pin_for_regeneration_exhausted():
    with pytest.raises(ValueError, match="三层齐备"):
        _v2(**_v2_missing_kwargs(
            termination_kind="model_call_regeneration_exhausted",
            failure_category="model_proxy_failure"))  # 缺 reason_code
    _v2(**_v2_missing_kwargs(
        termination_kind="model_call_regeneration_exhausted",
        failure_category="model_proxy_failure",
        reason_code="max_regenerations_exceeded"))


def test_failure_category_completion_matrix_13x3():
    """codex F2-1b P1-1 验收：13 categories × 3 completion classes 显式
    期望矩阵——封闭集合外的组合一律拒绝（评分/准入/控制面归因不得
    倒写 completion）。"""

    for fc in get_args(RuntimeFailureCategory):
        # missing：只有执行事实集合合法
        kwargs = _v2_missing_kwargs(failure_category=fc)
        if fc in FAILURE_CATEGORIES_EXECUTION_FACT:
            _v2(**kwargs)
        else:
            with pytest.raises(ValueError, match="执行事实集合"):
                _v2(**kwargs)
        # present_complete / present_truncated：只有 grading_infra_failure 合法
        for cc in ["present_complete", "present_truncated"]:
            tk = "completed" if cc == "present_complete" else "hard_wall_timeout"
            kwargs = dict(completion_class=cc, termination_kind=tk,
                          failure_category=fc, task_outcome="unknown",
                          reward_unavailable=True)
            if fc in FAILURE_CATEGORIES_GRADING:
                _v2(**kwargs)
            else:
                with pytest.raises(ValueError):
                    _v2(**kwargs)


def test_erratum2_counterexample_rejected():
    """codex 反例：missing + termination=completed + grading_infra_failure
    （评分故障倒写 completion）必须无法构造。"""

    with pytest.raises(ValueError, match="执行事实集合"):
        _v2(**_v2_missing_kwargs(termination_kind="completed",
                                 failure_category="grading_infra_failure"))
    with pytest.raises(ValueError, match="执行事实集合"):
        _v2(**_v2_missing_kwargs(failure_category="staleness_exceeded"))


def test_erratum2_grading_failure_does_not_rewrite_completion():
    rec = _v2(task_outcome="unknown", reward_unavailable=True,
              failure_category="grading_infra_failure")
    assert rec.completion_class == "present_complete"  # 未被倒写成 missing
    with pytest.raises(ValueError, match="grading_infra_failure"):
        _v2(failure_category="grading_infra_failure")  # 故障却声称 reward 可用
    with pytest.raises(ValueError, match="present_\\* 只允许"):
        _v2(failure_category="sandbox_crash")


def test_reward_unavailable_iff_unknown():
    with pytest.raises(ValueError, match="task_outcome=unknown"):
        _v2(task_outcome="unknown")
    with pytest.raises(ValueError, match="task_outcome=unknown"):
        _v2(reward_unavailable=True)


def test_v2_requires_four_layer_identity():
    """codex F2-1b P1-2 验收：无 physical_attempt_id / branch 视角的
    identity 都不能构成正式 execution 级 Outcome v2。"""

    with pytest.raises(ValueError, match="physical_attempt_id"):
        _v2(identity=_identity(physical_attempt_id=None, physical_attempt_seq=None))
    with pytest.raises(ValueError, match="branch_id 必须为 None"):
        _v2(identity=_identity(branch_id="leaf_3"))


# ---------------------------------------------------------------------------
# crosswalk：穷举规则表（3 v1 类别 × {无证据} ∪ 13 TerminationKind = 42 组合）
# ---------------------------------------------------------------------------

def _make_v1(cc: str) -> RolloutAttemptOutcome:
    if cc == "present":
        return _v1()
    if cc == "missing_after_local_retry":
        return _v1(completion_class=cc, task_outcome="unknown",
                   failure_category="sandbox_crash", turn_weight_versions=[],
                   intra_execution_version_span=None, current_version_at_finalize=None,
                   eligibility_report_id=None)
    return _v1(completion_class="permanent_rejection", task_outcome="unknown",
               failure_category="security_violation")


def test_crosswalk_exhaustive_rule_table():
    """每个 (v1 类别, 证据) 组合都有确定结果；规则名集合与文档表等式；
    migrated_v2 对 permanent_rejection 的一切路径 fail-closed。"""

    all_kinds = list(get_args(TerminationKind))
    seen_rules = set()
    for cc in ["present", "missing_after_local_retry", "permanent_rejection"]:
        for tk in [None, *all_kinds]:
            res = crosswalk_v1_to_v2(_make_v1(cc), None if tk is None else _ev(tk))
            seen_rules.add(res.rule)
            # 硬不变量：v2 在场 ⟺ 两种 migrated 状态（validator 也强制）
            assert (res.status != "legacy_unmappable") == (res.v2 is not None), (cc, tk)
            # 聚焦复核 4 + P1-3：permanent_rejection 不产 missing、
            # 干净提取口拿不到（只能 audit-only 或 unmappable）
            if cc == "permanent_rejection":
                assert res.status != "migrated", (cc, tk)
                assert migrated_v2(res) is None, (cc, tk)
                if res.v2 is not None:
                    assert res.v2.completion_class != "missing", (cc, tk)
                    assert res.legacy_admission_verdict == "permanent_rejection"
    assert seen_rules == {
        "present_no_evidence", "present_completed", "present_truncated",
        "present_infra_contradiction",
        "missing_no_evidence", "missing_migrated",
        "missing_three_layer_contradiction",
        "rejection_no_evidence", "rejection_infra_contradiction",
        "rejection_present_complete", "rejection_present_truncated",
    }


def test_crosswalk_no_evidence_never_fabricates():
    for cc in ["present", "missing_after_local_retry", "permanent_rejection"]:
        res = crosswalk_v1_to_v2(_make_v1(cc), None)
        assert res.status == "legacy_unmappable"
        assert res.v2 is None and migrated_v2(res) is None


def test_crosswalk_present_with_evidence():
    res = crosswalk_v1_to_v2(_v1(), _ev("completed", evidence_refs=["a1"]))
    assert res.status == "migrated"
    assert res.v2.completion_class == "present_complete"
    assert res.v2.task_outcome == "unresolved"  # 评分结局照搬
    assert not res.v2.reward_unavailable
    assert "a1" in res.v2.evidence_refs  # 重建依据并入
    assert migrated_v2(res) is res.v2  # 干净迁移可训练

    res2 = crosswalk_v1_to_v2(_v1(), _ev("max_turns_exhausted"))
    assert res2.v2.completion_class == "present_truncated"


def test_crosswalk_rejection_is_audit_only_and_fail_closed():
    """codex F2-1b P1-3 验收：永久拒绝迁移产物 = migrated_audit_only；
    只看 status/v2 的消费者拿不到"干净 migrated"，migrated_v2 返回 None
    ——忽略 verdict 也不可能把被禁轨迹送进训练。"""

    res = crosswalk_v1_to_v2(_make_v1("permanent_rejection"), _ev("completed"))
    assert res.status == "migrated_audit_only"  # 不是 "migrated"
    assert res.v2.completion_class == "present_complete"
    assert res.v2.failure_category is None  # 事实层：执行没失败
    assert res.v2.reward_unavailable and res.v2.task_outcome == "unknown"
    assert res.legacy_admission_verdict == "permanent_rejection"
    assert res.legacy_failure_category == "security_violation"
    assert migrated_v2(res) is None  # fail-closed 提取口


def test_crosswalk_rejection_without_present_facts_unmappable():
    v1 = _v1(completion_class="permanent_rejection", task_outcome="unknown",
             failure_category="security_violation", turn_weight_versions=[],
             intra_execution_version_span=None, current_version_at_finalize=None,
             eligibility_report_id=None)
    res = crosswalk_v1_to_v2(v1, _ev("completed"))
    assert res.status == "legacy_unmappable"
    assert res.rule == "rejection_facts_incomplete"


def test_crosswalk_missing_three_layer_contradiction():
    res = crosswalk_v1_to_v2(
        _make_v1("missing_after_local_retry"),  # failure_category=sandbox_crash
        _ev("model_call_regeneration_exhausted"))
    assert res.status == "legacy_unmappable"
    assert res.rule == "missing_three_layer_contradiction"


def test_crosswalk_missing_admission_category_not_migrated():
    """P1-1 迁移面：v1 缺员带准入/控制面归因（staleness 等）→ 不迁移，
    防完整成员被算成缺员。"""

    v1 = _v1(completion_class="missing_after_local_retry", task_outcome="unknown",
             failure_category="staleness_exceeded", turn_weight_versions=[],
             intra_execution_version_span=None, current_version_at_finalize=None,
             eligibility_report_id=None)
    res = crosswalk_v1_to_v2(v1, _ev("harness_crash"))
    assert res.status == "legacy_unmappable"
    assert res.rule == "missing_category_not_execution"


def test_crosswalk_identity_gates():
    """codex F2-1b P1-2 验收：branch 视角 → 不迁移；v1 无 paid 且证据
    未补 → 不迁移；证据补齐 paid → 迁移产物带完整四层身份。"""

    # branch 视角
    v1b = _v1(identity=_identity(branch_id="leaf_1"))
    res = crosswalk_v1_to_v2(v1b, _ev("completed"))
    assert res.status == "legacy_unmappable"
    assert res.rule == "identity_not_execution_level"

    # 无 paid、证据不补
    v1n = _v1(identity=_identity(physical_attempt_id=None, physical_attempt_seq=None))
    res2 = crosswalk_v1_to_v2(v1n, _ev("completed"))
    assert res2.status == "legacy_unmappable"
    assert res2.rule == "identity_unrebuildable"

    # 证据补齐（审计重建）
    ev = _ev("completed", physical_attempt_id="exec_1#p1-bbbb2222",
             physical_attempt_seq=1)
    res3 = crosswalk_v1_to_v2(v1n, ev)
    assert res3.status == "migrated"
    assert res3.v2.identity.physical_attempt_id == "exec_1#p1-bbbb2222"
    assert res3.v2.identity.physical_attempt_seq == 1


def test_migrated_v2_is_not_a_trainability_claim():
    """codex F2-1b 二轮 P1：missing 的成功迁移也会经 migrated_v2 提取出
    ——接口只过滤 audit-only 维；返回对象可以是 missing、可以无
    eligibility 引用。训练资格权威在 Eligibility/Admission 联合 Gate，
    本测试钉住"提取成功 ≠ 可训练"的语义边界。"""

    res = crosswalk_v1_to_v2(_make_v1("missing_after_local_retry"), _ev("harness_crash"))
    got = migrated_v2(res)
    assert got is not None and got.completion_class == "missing"
    assert got.eligibility_report_id is None  # 明示：这不是训练资格证明


def test_identity_evidence_conflict_fails_closed():
    """codex F2-1b 二轮 P1：v1 与证据都带 paid 且不一致 → 不得静默取舍，
    legacy_unmappable；完全一致则照常迁移。"""

    ev_conflict = _ev("completed", physical_attempt_id="DIFFERENT-PAID",
                      physical_attempt_seq=9)
    res = crosswalk_v1_to_v2(_v1(), ev_conflict)
    assert res.status == "legacy_unmappable"
    assert res.rule == "identity_evidence_conflict"

    # seq 单独不一致同样冲突
    ev_seq = _ev("completed", physical_attempt_id="exec_1#p1-aaaa1111",
                 physical_attempt_seq=2)
    assert crosswalk_v1_to_v2(_v1(), ev_seq).rule == "identity_evidence_conflict"

    # 完全一致 → 正常迁移
    ev_same = _ev("completed", physical_attempt_id="exec_1#p1-aaaa1111",
                  physical_attempt_seq=1)
    assert crosswalk_v1_to_v2(_v1(), ev_same).status == "migrated"


def test_evidence_and_result_fail_closed():
    """codex F2-1b P1-3 验收：空引用证据 / 状态-载荷矛盾的结果都无法构造。"""

    with pytest.raises(ValueError):
        V1TerminationEvidence(termination_kind="completed", evidence_refs=[])
    with pytest.raises(ValueError, match="v2 在场性矛盾"):
        OutcomeCrosswalkResult(status="migrated", v1_outcome_id="x",
                               rule="r", reason="y", v2=None)
    with pytest.raises(ValueError, match="v2 在场性矛盾"):
        OutcomeCrosswalkResult(status="legacy_unmappable", v1_outcome_id="x",
                               rule="r", reason="y", v2=_v2())
    with pytest.raises(ValueError, match="migrated_audit_only 必须携带"):
        OutcomeCrosswalkResult(status="migrated_audit_only", v1_outcome_id="x",
                               rule="r", reason="y", v2=_v2())
    with pytest.raises(ValueError, match="不得携带 admission verdict"):
        OutcomeCrosswalkResult(status="migrated", v1_outcome_id="x", rule="r",
                               reason="y", v2=_v2(),
                               legacy_admission_verdict="permanent_rejection")


# ---------------------------------------------------------------------------
# 双版本读取 + src 无 v1 构造点守卫
# ---------------------------------------------------------------------------

def test_dual_version_read_round_trip():
    v1 = _v1()
    v2 = _v2()
    got1 = read_rollout_attempt_outcome(v1.model_dump(mode="json"))
    got2 = read_rollout_attempt_outcome(v2.model_dump(mode="json"))
    assert isinstance(got1, RolloutAttemptOutcome) and got1 == v1
    assert isinstance(got2, RolloutAttemptOutcomeV2) and got2 == v2
    with pytest.raises(ValueError, match="未知 rollout_attempt_outcome 版本"):
        read_rollout_attempt_outcome({"schema_id": "rh2.fa.rollout_attempt_outcome.v3"})


def test_src_has_no_v1_construction_sites():
    """静态守卫：src 生产代码没有 v1 构造点（producer 未接线前防倒退）。

    注意口径（codex F2-1b 完成项）：本测试只证明"当前源码不构造 v1"，
    **不证明**"正式链已生产 v2"——真实 producer/持久化/assembler 消费
    测试钉在 F2-2 起的切片验收（05 计划）。
    """

    from pathlib import Path

    import repoharness2

    src_root = Path(repoharness2.__file__).parent
    allowed = {
        src_root / "contracts" / "fa_runtime.py",         # v1 定义（冻结）
        src_root / "contracts" / "outcome_crosswalk.py",  # 读迁面
        src_root / "registry.py",                          # schema 注册
    }
    offenders = []
    for py in src_root.rglob("*.py"):
        if py in allowed:
            continue
        text = py.read_text(encoding="utf-8")
        if "RolloutAttemptOutcome(" in text.replace("RolloutAttemptOutcomeV2(", ""):
            offenders.append(str(py))
    assert not offenders, f"生产代码出现 v1 Outcome 构造点：{offenders}"
