"""gate 七维判定的 fail-closed 测试：逐维翻转、强制降级、账实互检。"""

from __future__ import annotations

from typing import Any

import pytest
from contract_samples import (
    valid_eligibility_facts,
    valid_grading_report,
    valid_trajectory_projection,
)
from governance_samples import (
    executed_finding_payload,
    infra_grading_payload,
    infra_reward_facts,
    numeric_backend_handshake,
    run_finalize,
    tampered_hygiene_grading_payload,
)
from pydantic import ValidationError

from repoharness2.contracts import (
    EligibilityFacts,
    EligibilityReport,
    compute_facts_digest,
)
from repoharness2.governance import GroupRepairSignal

_DIMENSIONS = (
    "token_provenance",
    "logprob_alignment",
    "loss_mask_integrity",
    "reward_scope",
    "security_and_leakage",
    "clean_grading",
    "policy_staleness",
)


def _variant_kwargs(dimension: str) -> tuple[dict[str, Any], str, str]:
    """构造"只让指定维度失败"的 finalize 输入。

    返回 (run_finalize 的 kwargs, 期望理由码, 期望资格档)。
    """

    if dimension == "token_provenance":
        # 分支回链 cap_0001，但捕获记录清单为空 -> 引用解析失败
        return {"captures": []}, "capture_record_missing", "offline_or_sft_candidate"
    if dimension == "logprob_alignment":
        projection = valid_trajectory_projection()
        projection["branches"][0]["logprob_alignment_status"] = "missing"
        projection["branches"][0]["logprob_provenance"] = None
        return {"projection": projection}, "logprob_missing", "offline_or_sft_candidate"
    if dimension == "loss_mask_integrity":
        # 实际 mask=1 共 16 token，申报 17 -> 账目被凭空放大
        projection = valid_trajectory_projection()
        projection["reward_facts"]["rollout_loss_denominator"] = 17
        return {"projection": projection}, "loss_denominator_mismatch", "audit_only_or_rejected"
    if dimension == "reward_scope":
        projection = valid_trajectory_projection()
        projection["reward_facts"]["credit_assignment_strategy"] = "unknown"
        return {"projection": projection}, "credit_assignment_unknown", "audit_only_or_rejected"
    if dimension == "security_and_leakage":
        return (
            {"findings": [executed_finding_payload()]},
            "anti_cheat_executed_test_tampering",
            "audit_only_or_rejected",
        )
    if dimension == "clean_grading":
        # 同容器评分旧形态（A7：replayed_on_clean_checkout=False 即降级）
        grading = valid_grading_report()
        grading["patch_hygiene"]["replayed_on_clean_checkout"] = False
        return {"grading": grading}, "not_replayed_on_clean_checkout", "audit_only_or_rejected"
    if dimension == "policy_staleness":
        # B-1：第七维只判"版本事实可用且合法"——seen 含比 current(120) 更新的版本 = 未来版本
        handshake = numeric_backend_handshake(weight_versions_seen=["119", "121"])
        handshake["accepted"] = True  # 后端物理接收救不回资格（S1-1b）
        return {"handshake": handshake}, "staleness_facts_invalid", "offline_or_sft_candidate"
    raise AssertionError(f"未覆盖的维度 {dimension}")


@pytest.mark.parametrize("dimension", _DIMENSIONS)
async def test_any_single_dimension_failure_degrades(dimension: str):
    """七维逐个翻转：任一维失败即降级，其余六维不受牵连，理由码逐维可审计。"""

    kwargs, expected_reason, expected_class = _variant_kwargs(dimension)
    final = await run_finalize(**kwargs)
    report = final.eligibility_report

    fact = getattr(report.facts, dimension)
    assert fact.ok is False
    assert expected_reason in fact.reason_codes
    for other in _DIMENSIONS:
        if other != dimension:
            assert getattr(report.facts, other).ok, f"{other} 不应被 {dimension} 的翻转牵连"

    assert report.eligibility_class == expected_class
    assert report.eligibility_class != "online_policy_loss_eligible"
    assert expected_reason in report.reason_codes

    signal = final.group_repair_signal
    assert signal.degraded is True
    assert signal.failed_dimensions == [dimension]


async def test_security_failure_forces_audit_only_gate_layer():
    """gate 层：security 维失败 -> 结论必为 audit_only_or_rejected（地板 + schema 双保险之一）。"""

    final = await run_finalize(findings=[executed_finding_payload()])
    report = final.eligibility_report
    assert report.facts.security_and_leakage.ok is False
    assert report.eligibility_class == "audit_only_or_rejected"
    assert "finding_exec_0001" in report.facts.security_and_leakage.evidence_refs


def test_security_failure_forces_audit_only_schema_layer():
    """schema 层复证：security 失败 + 非 audit 结论的报告不可表示（双保险之二）。

    即使未来某个 gate 实现忘了地板规则，手工构造这样的报告也会在
    EligibilityReport 校验器处被拒收。
    """

    facts = valid_eligibility_facts()
    facts["security_and_leakage"] = {
        "ok": False,
        "reason_codes": ["anti_cheat_executed_test_tampering"],
        "evidence_refs": [],
    }
    digest = compute_facts_digest(EligibilityFacts.model_validate(facts))
    payload = {
        "schema_id": "rh2.eligibility_report.v1",
        "report_id": "elig_bad",
        "trajectory_id": "traj_0001",
        "gate_version": "rh2.gate.s1.v1",
        "facts": facts,
        "facts_digest": digest,
        "eligibility_class": "offline_or_sft_candidate",  # 非 audit：必须被拒
        "reason_codes": ["anti_cheat_executed_test_tampering"],
        "derived_view_report_ref": "elig_bad",
        "derived_view_class": "offline_or_sft_candidate",
        "created_at_utc": "2026-07-07T09:30:25Z",
    }
    with pytest.raises(ValidationError, match="audit_only_or_rejected"):
        EligibilityReport.model_validate(payload)


async def test_infra_failure_linkage_downgrade_plus_reward_none():
    """infra_failure 样本：reward=None 联动 + 双维失败 + 资格落 audit（P4 红线）。"""

    final = await run_finalize(
        grading=infra_grading_payload(),
        projection={**valid_trajectory_projection(), "reward_facts": infra_reward_facts()},
    )
    report = final.eligibility_report

    # reward=None 联动：评分报告与投影两侧都没有数值 reward
    assert final.grading_report.reward is None
    assert final.projection.reward_facts.raw_reward is None
    # reward_scope 维：scope=none 即失败
    assert report.facts.reward_scope.ok is False
    assert "reward_scope_none" in report.facts.reward_scope.reason_codes
    # clean_grading 维：infra 族归因即失败
    assert report.facts.clean_grading.ok is False
    assert "grading_infra_failure" in report.facts.clean_grading.reason_codes
    # 资格降级出训练面
    assert report.eligibility_class == "audit_only_or_rejected"
    assert final.group_repair_signal.degraded is True
    assert final.group_repair_signal.failed_dimensions == ["reward_scope", "clean_grading"]


async def test_infra_masquerading_as_reward_zero_caught_by_cross_check():
    """跨对象互检：infra 评分（reward=None）配申报 raw_reward=0.0 的投影——
    两个对象各自 schema 合法，gate 对账拒绝（infra 伪装成负样本的经典形态）。"""

    projection = valid_trajectory_projection()
    projection["reward_facts"]["raw_reward"] = 0.0
    projection["reward_facts"]["reward_event_refs"] = ["rpt_grading_0002"]
    final = await run_finalize(grading=infra_grading_payload(), projection=projection)
    fact = final.eligibility_report.facts.reward_scope
    assert fact.ok is False
    assert "reward_value_mismatch" in fact.reason_codes
    assert final.eligibility_report.eligibility_class == "audit_only_or_rejected"


async def test_hygiene_tampering_fails_security_and_clean_grading():
    """patch 篡改测试文件（S1-4 剥离重放形态）：clean_grading 与 security 双维失败
    （§16.1 条 7 的篡改检查并入 security 维，schema 强制 audit 档）。"""

    projection = valid_trajectory_projection()
    projection["reward_facts"]["raw_reward"] = 0.0  # 封顶后的 tests_failed -> 0.0
    final = await run_finalize(
        grading=tampered_hygiene_grading_payload(), projection=projection
    )
    report = final.eligibility_report

    assert "hygiene_rejected_test_tampering" in report.facts.clean_grading.reason_codes
    assert "patch_test_tampering" in report.facts.security_and_leakage.reason_codes
    assert report.eligibility_class == "audit_only_or_rejected"
    assert final.group_repair_signal.failed_dimensions == [
        "security_and_leakage",
        "clean_grading",
    ]


async def test_all_seven_dimensions_can_fail_together():
    """极端形态：七维同时失败 -> audit 档，failed_dimensions 按固定顺序列全七维。"""

    projection = valid_trajectory_projection()
    projection["branches"][0]["logprob_alignment_status"] = "missing"
    projection["branches"][0]["logprob_provenance"] = None
    reward = infra_reward_facts()
    reward["credit_assignment_strategy"] = "unknown"
    reward["rollout_loss_denominator"] = 17  # 实际 16
    projection["reward_facts"] = reward
    handshake = numeric_backend_handshake(weight_versions_seen=["step_x"])  # 非法版本

    final = await run_finalize(
        projection=projection,
        grading=infra_grading_payload(),
        captures=[],
        findings=[executed_finding_payload()],
        handshake=handshake,
    )
    report = final.eligibility_report
    assert report.eligibility_class == "audit_only_or_rejected"
    assert final.group_repair_signal.failed_dimensions == list(_DIMENSIONS)
    assert final.group_repair_signal.degraded is True


async def test_no_group_ppo_shape_signal_has_none_group_id():
    """算法无关：trace_level 单条 rollout（PPO 形态）无组 id，信号 group_id=None。"""

    projection = valid_trajectory_projection()
    projection["reward_facts"] = {
        "reward_scope": "trace_level",
        "raw_reward": 1.0,
        "components": {},
        "reward_event_refs": ["rpt_grading_0001"],
        "credit_assignment_strategy": "direct_trace_reward",
        "group_id": None,
        "parent_rollout_id": None,
        "segment_index": None,
        "segment_count": 1,
        "rollout_loss_denominator": None,
    }
    final = await run_finalize(projection=projection)
    signal = final.group_repair_signal
    assert signal.group_id is None
    assert signal.parent_rollout_id is None
    assert signal.degraded is False


async def test_attempted_blocked_finding_does_not_fail_security():
    """attempted_blocked（拦截成功）不扣 security 维——"此路不通"是合法训练信号；
    但 finding 在 evidence 里留痕。"""

    finding = executed_finding_payload()
    finding["enforcement"] = "attempted_blocked"
    finding["detection_layer"] = "online_interception"
    finding["anti_hack_event_ref"] = "antihack_0001"
    final = await run_finalize(findings=[finding])
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is True
    assert "attempted_blocked:finding_exec_0001" in fact.evidence_refs
    assert final.eligibility_report.eligibility_class == "online_policy_loss_eligible"  # A3：无封顶


async def test_facts_digest_tampering_rejected_on_revalidation():
    """facts_digest 互检：gate 产出的报告被篡改任一维事实后，重新校验即拒收。"""

    final = await run_finalize()
    payload = final.eligibility_report.model_dump(mode="json")
    payload["facts"]["logprob_alignment"] = {
        "ok": False,
        "reason_codes": ["logprob_missing"],
        "evidence_refs": [],
    }
    with pytest.raises(ValidationError, match="facts_digest"):
        EligibilityReport.model_validate(payload)


async def test_facts_digest_field_tampering_rejected():
    """直接改 digest 字段同样拒收（事实与结论都不许事后改动）。"""

    final = await run_finalize()
    payload = final.eligibility_report.model_dump(mode="json")
    payload["facts_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="facts_digest"):
        EligibilityReport.model_validate(payload)


# ---------------------------------------------------------------------------
# GroupRepairSignal 自身的 fail-closed 校验
# ---------------------------------------------------------------------------


def _signal_payload() -> dict[str, Any]:
    return {
        "trajectory_id": "traj_0001",
        "group_id": "group_task42",
        "parent_rollout_id": "rollout_7",
        "report_ref": "elig_test_0001",
        "eligibility_class": "audit_only_or_rejected",
        "degraded": True,
        "failed_dimensions": ["clean_grading"],
        "reason_codes": ["grading_infra_failure"],
    }


def test_group_repair_signal_degraded_must_match_failed_dimensions():
    payload = _signal_payload()
    payload["failed_dimensions"] = []
    with pytest.raises(ValidationError, match="账实不符"):
        GroupRepairSignal.model_validate(payload)


def test_group_repair_signal_rejects_unknown_dimension_name():
    payload = _signal_payload()
    payload["failed_dimensions"] = ["not_a_dimension"]
    with pytest.raises(ValidationError, match="未知维度名"):
        GroupRepairSignal.model_validate(payload)


def test_group_repair_signal_rejects_out_of_order_dimensions():
    payload = _signal_payload()
    payload["failed_dimensions"] = ["clean_grading", "security_and_leakage"]  # 顺序颠倒
    with pytest.raises(ValidationError, match="固定顺序"):
        GroupRepairSignal.model_validate(payload)


# ---------------------------------------------------------------------------
# staleness 分布记账（preflight §8 H-1：只记录不准入）
# ---------------------------------------------------------------------------


async def test_staleness_distribution_recorded_not_admitted():
    """H-1 正例：projection.handshake 的分布（长度+跨度）进 policy_staleness evidence。

    关键断言"只记录不准入"：max_lag=2（版本跨了两步）也**不**构成维度失败——
    准入界的设计留给升级档位；本维 ok 只由 BackendHandshake 的版本事实是否合法决定。
    """
    projection = valid_trajectory_projection()
    projection["handshake"] = {"weight_versions": ["1", "1", "3"], "max_lag": 2}
    final = await run_finalize(projection=projection)
    fact = final.eligibility_report.facts.policy_staleness
    assert fact.ok is True  # 分布不改变判定（BackendHandshake 阈值内）
    assert "weight_versions_count:3" in fact.evidence_refs
    assert "weight_versions_max_lag:2" in fact.evidence_refs


async def test_staleness_distribution_absence_recorded_honestly():
    """H-1 反例：投影未记账（handshake=None）-> evidence 如实记 unrecorded，
    维度判定照旧只看 BackendHandshake（不因缺分布而额外降级，也不因此放行）。"""
    final = await run_finalize()  # valid_trajectory_projection 无 handshake 字段
    fact = final.eligibility_report.facts.policy_staleness
    assert fact.ok is True
    assert "weight_versions_unrecorded" in fact.evidence_refs

    # BackendHandshake 缺席时维度照常 fail-closed，分布 evidence 仍在场
    degraded = await run_finalize(handshake=None)
    fact = degraded.eligibility_report.facts.policy_staleness
    assert fact.ok is False
    assert "staleness_facts_missing" in fact.reason_codes
    assert "weight_versions_unrecorded" in fact.evidence_refs


def test_group_repair_signal_audit_class_requires_degraded():
    payload = _signal_payload()
    payload["degraded"] = False
    payload["failed_dimensions"] = []
    payload["reason_codes"] = ["s1_default_ceiling_offline"]
    # eligibility_class 仍是 audit_only_or_rejected
    with pytest.raises(ValidationError, match="audit"):
        GroupRepairSignal.model_validate(payload)


def test_group_repair_signal_degraded_cannot_be_online():
    payload = _signal_payload()
    payload["eligibility_class"] = "online_policy_loss_eligible"
    with pytest.raises(ValidationError, match="online"):
        GroupRepairSignal.model_validate(payload)


def test_group_repair_signal_degraded_requires_reason_codes():
    payload = _signal_payload()
    payload["reason_codes"] = []
    with pytest.raises(ValidationError, match="reason_codes"):
        GroupRepairSignal.model_validate(payload)
