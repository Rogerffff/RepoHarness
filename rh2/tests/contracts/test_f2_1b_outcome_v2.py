"""F2-1b 验收：Outcome v2 契约语义 + v1→v2 crosswalk 穷举 + 双版本读取
+ 正式链只产 v2 守卫。

钉住的语义（05 计划 F2-1b 节 + 决策包 D1a/勘误 2/聚焦复核 4）：
completion 三值事实层；termination 五族集合等式；三层分离钉子；
勘误 2（评分故障不倒写 completion）；permanent_rejection 永不默认映射
missing；无证据不捏造。
"""

from __future__ import annotations

from typing import get_args

import pytest

from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_CONTROL,
    TERMINATION_KINDS_INFRA,
    TERMINATION_KINDS_NORMAL,
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    ExecutionIdentity,
    RolloutAttemptOutcome,
    RolloutAttemptOutcomeV2,
    TerminationKind,
)
from repoharness2.contracts.outcome_crosswalk import (
    V1TerminationEvidence,
    crosswalk_v1_to_v2,
    read_rollout_attempt_outcome,
)


def _identity() -> ExecutionIdentity:
    return ExecutionIdentity(prompt_group_id="g", group_index=0, rollout_execution_id="exec_1")


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


def _v1(**over) -> RolloutAttemptOutcome:
    base = dict(
        outcome_id="v1o", identity=_identity(), member_slot=0, attempt_number=1,
        completion_class="present", task_outcome="unresolved", recovery_scope="none",
        turn_weight_versions=["1"], intra_execution_version_span=0,
        current_version_at_finalize="1", eligibility_report_id="er",
    )
    base.update(over)
    return RolloutAttemptOutcome(**base)


# ---------------------------------------------------------------------------
# termination 五族：集合等式（D4 风格）
# ---------------------------------------------------------------------------

def test_termination_families_partition_exactly():
    families = [
        TERMINATION_KINDS_POLICY_HORIZON, TERMINATION_KINDS_WATCHDOG,
        TERMINATION_KINDS_CONTROL, TERMINATION_KINDS_INFRA, TERMINATION_KINDS_NORMAL,
    ]
    assert frozenset().union(*families) == frozenset(get_args(TerminationKind))
    assert sum(len(f) for f in families) == len(get_args(TerminationKind))  # 两两不交


# ---------------------------------------------------------------------------
# v2 validator 语义
# ---------------------------------------------------------------------------

def test_present_complete_requires_completed_termination():
    with pytest.raises(ValueError, match="present_complete 只能来自"):
        _v2(termination_kind="hard_wall_timeout")


def test_present_truncated_families():
    # horizon / 看门狗 / 控制面合法
    for tk in ["task_token_budget_exhausted", "hard_wall_timeout", "owner_cancelled"]:
        if tk == "owner_cancelled":
            # 控制面取消默认不产生 reward → unknown + reward_unavailable
            _v2(completion_class="present_truncated", termination_kind=tk,
                task_outcome="unknown", reward_unavailable=True)
        else:
            _v2(completion_class="present_truncated", termination_kind=tk)
    # 正常终止不是截断
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
    # 正确构造：missing + 归因
    _v2(completion_class="missing", termination_kind="sandbox_failure",
        failure_category="sandbox_crash", task_outcome="unknown",
        reward_unavailable=True, turn_weight_versions=[],
        intra_execution_version_span=None, current_version_at_finalize=None,
        eligibility_report_id=None)


def test_three_layer_pin_for_regeneration_exhausted():
    with pytest.raises(ValueError, match="三层齐备"):
        _v2(completion_class="missing", termination_kind="model_call_regeneration_exhausted",
            failure_category="model_proxy_failure", task_outcome="unknown",
            reward_unavailable=True, turn_weight_versions=[],
            intra_execution_version_span=None, current_version_at_finalize=None,
            eligibility_report_id=None)  # 缺 reason_code
    _v2(completion_class="missing", termination_kind="model_call_regeneration_exhausted",
        failure_category="model_proxy_failure", reason_code="max_regenerations_exceeded",
        task_outcome="unknown", reward_unavailable=True, turn_weight_versions=[],
        intra_execution_version_span=None, current_version_at_finalize=None,
        eligibility_report_id=None)


def test_erratum2_grading_failure_does_not_rewrite_completion():
    """勘误 2：评分基建故障 → reward 不可用，completion 保持 present_*。"""

    rec = _v2(task_outcome="unknown", reward_unavailable=True,
              failure_category="grading_infra_failure")
    assert rec.completion_class == "present_complete"  # 未被倒写成 missing
    # 反向：评分故障却声称 reward 可用 → 拒绝
    with pytest.raises(ValueError, match="grading_infra_failure"):
        _v2(failure_category="grading_infra_failure")
    # present_* 不允许其他失败归因（执行没失败）
    with pytest.raises(ValueError, match="present_\\* 只允许"):
        _v2(failure_category="sandbox_crash")


def test_reward_unavailable_iff_unknown():
    with pytest.raises(ValueError, match="task_outcome=unknown"):
        _v2(task_outcome="unknown")  # unknown 但未标 reward_unavailable
    with pytest.raises(ValueError, match="task_outcome=unknown"):
        _v2(reward_unavailable=True)  # 标了不可用却给出结局


def test_missing_requires_attribution():
    with pytest.raises(ValueError, match="missing 必须携带 failure_category"):
        _v2(completion_class="missing", termination_kind="harness_crash",
            task_outcome="unknown", reward_unavailable=True, turn_weight_versions=[],
            intra_execution_version_span=None, current_version_at_finalize=None,
            eligibility_report_id=None)


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
    """每个 (v1 类别, 证据) 组合都有确定结果；规则名集合与文档表等式。"""

    all_kinds = list(get_args(TerminationKind))
    seen_rules = set()
    for cc in ["present", "missing_after_local_retry", "permanent_rejection"]:
        for tk in [None, *all_kinds]:
            ev = None if tk is None else V1TerminationEvidence(
                termination_kind=tk, evidence_refs=["audit_x"])
            res = crosswalk_v1_to_v2(_make_v1(cc), ev)
            seen_rules.add(res.rule)
            # 硬不变量：migrated ⟺ v2 在场
            assert (res.status == "migrated") == (res.v2 is not None), (cc, tk)
            # 聚焦复核 4：permanent_rejection 任何路径都不产出 missing
            if cc == "permanent_rejection" and res.v2 is not None:
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
        assert res.v2 is None


def test_crosswalk_present_with_evidence():
    ev_done = V1TerminationEvidence(termination_kind="completed", evidence_refs=["a1"])
    res = crosswalk_v1_to_v2(_v1(), ev_done)
    assert res.status == "migrated"
    assert res.v2.completion_class == "present_complete"
    assert res.v2.task_outcome == "unresolved"  # 评分结局照搬
    assert not res.v2.reward_unavailable
    assert "a1" in res.v2.evidence_refs  # 重建依据并入

    ev_cut = V1TerminationEvidence(termination_kind="max_turns_exhausted")
    assert crosswalk_v1_to_v2(_v1(), ev_cut).v2.completion_class == "present_truncated"


def test_crosswalk_rejection_migrates_with_verdict_not_missing():
    """permanent_rejection + 可重建证据 → present_* + verdict 传递；
    归因（security_violation）留在审计面，不进 v2 事实层。"""

    ev = V1TerminationEvidence(termination_kind="completed")
    res = crosswalk_v1_to_v2(_make_v1("permanent_rejection"), ev)
    assert res.status == "migrated"
    assert res.v2.completion_class == "present_complete"
    assert res.v2.failure_category is None  # 事实层：执行没失败
    assert res.v2.reward_unavailable and res.v2.task_outcome == "unknown"
    assert res.legacy_admission_verdict == "permanent_rejection"
    assert res.legacy_failure_category == "security_violation"


def test_crosswalk_rejection_without_present_facts_unmappable():
    v1 = _v1(completion_class="permanent_rejection", task_outcome="unknown",
             failure_category="security_violation", turn_weight_versions=[],
             intra_execution_version_span=None, current_version_at_finalize=None,
             eligibility_report_id=None)
    res = crosswalk_v1_to_v2(v1, V1TerminationEvidence(termination_kind="completed"))
    assert res.status == "legacy_unmappable"
    assert res.rule == "rejection_facts_incomplete"


def test_crosswalk_missing_three_layer_contradiction():
    v1 = _make_v1("missing_after_local_retry")  # failure_category=sandbox_crash
    ev = V1TerminationEvidence(termination_kind="model_call_regeneration_exhausted")
    res = crosswalk_v1_to_v2(v1, ev)
    assert res.status == "legacy_unmappable"
    assert res.rule == "missing_three_layer_contradiction"


# ---------------------------------------------------------------------------
# 双版本读取 + 正式链只产 v2
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


def test_formal_chain_produces_v2_only():
    """守卫：src 生产代码不得构造 v1（RolloutAttemptOutcome(）——v1 只在
    契约定义/registry/crosswalk 读迁面出现。文本扫描同 F2-0 迁移守卫法。"""

    from pathlib import Path

    import repoharness2

    src_root = Path(repoharness2.__file__).parent
    allowed = {
        src_root / "contracts" / "fa_runtime.py",       # v1 定义（冻结）
        src_root / "contracts" / "outcome_crosswalk.py",  # 读迁面
        src_root / "registry.py",                        # schema 注册
    }
    offenders = []
    for py in src_root.rglob("*.py"):
        if py in allowed:
            continue
        text = py.read_text(encoding="utf-8")
        if "RolloutAttemptOutcome(" in text.replace("RolloutAttemptOutcomeV2(", ""):
            offenders.append(str(py))
    assert not offenders, f"生产代码构造了 v1 Outcome（正式链只产 v2）：{offenders}"
