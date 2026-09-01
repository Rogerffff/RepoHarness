"""W1b 第二段 A3：S1_TIER_CAP 整体删除 + security 维改为"正向 sandbox 能力事实在场且无违规"。

验收（06 计划 A3 / §3 W1b 行）：security 维缺能力事实 = 非 online（fail-closed）；
findings=() 不再构成"安全"；cap 删除与语义切换同批（本文件与 test_wrapper_finalize 的
删除断言互为正反）。
"""

from __future__ import annotations

import pytest
from governance_samples import executed_finding_payload, run_finalize, valid_sandbox_capability_facts
from pydantic import ValidationError

from repoharness2.governance import (
    GATE_VERSION,
    REQUIRED_SANDBOX_CAPABILITIES,
    GateInputError,
    SandboxCapabilityFacts,
)


async def test_capability_facts_present_all_ok_is_online_with_evidence():
    final = await run_finalize()
    report = final.eligibility_report
    assert report.gate_version == GATE_VERSION == "rh2.gate.w1b.v2"
    assert report.eligibility_class == "online_policy_loss_eligible"
    fact = report.facts.security_and_leakage
    assert fact.ok and "sandbox_capability_facts:lease_0001" in fact.evidence_refs
    assert "sandbox_probe_0001" in fact.evidence_refs


async def test_missing_capability_facts_is_not_online_even_with_no_findings():
    """A3 时序防护：W3b 未产出事实前，formal 样本自然非 online——findings=() 不是假过窗口。"""

    final = await run_finalize(sandbox_capability_facts=None, findings=())
    report = final.eligibility_report
    fact = report.facts.security_and_leakage
    assert fact.ok is False and fact.reason_codes == ["sandbox_capability_facts_missing"]
    assert "sandbox_capability_facts:absent" in fact.evidence_refs
    assert report.eligibility_class == "audit_only_or_rejected"  # schema：security 失败强制 audit
    assert final.group_repair_signal.degraded is True
    assert final.group_repair_signal.failed_dimensions == ["security_and_leakage"]


@pytest.mark.parametrize("missing_name", list(REQUIRED_SANDBOX_CAPABILITIES))
async def test_each_required_capability_unverified_fails_dimension(missing_name: str):
    facts = valid_sandbox_capability_facts(
        verified_capabilities=[n for n in REQUIRED_SANDBOX_CAPABILITIES if n != missing_name]
    )
    final = await run_finalize(sandbox_capability_facts=facts)
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is False and fact.reason_codes == [f"sandbox_capability_unverified_{missing_name}"]
    assert final.eligibility_report.eligibility_class == "audit_only_or_rejected"


async def test_violation_fails_dimension_even_when_all_verified():
    facts = valid_sandbox_capability_facts(violations=["network_egress_observed"])
    final = await run_finalize(sandbox_capability_facts=facts)
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is False and fact.reason_codes == ["sandbox_capability_violation_network_egress_observed"]


async def test_executed_finding_still_fails_with_facts_present():
    final = await run_finalize(findings=[executed_finding_payload()])
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is False and "anti_cheat_executed_test_tampering" in fact.reason_codes


async def test_not_required_path_records_evidence_and_keeps_old_semantics():
    """s1_compat 冻结路径显式声明不要求能力事实：本维保持旧语义，evidence 如实记 not_required。"""

    final = await run_finalize(sandbox_capability_facts=None, sandbox_capability_facts_required=False)
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is True and "sandbox_capability_facts:not_required" in fact.evidence_refs
    assert final.eligibility_report.eligibility_class == "online_policy_loss_eligible"


async def test_foreign_capability_facts_are_wiring_errors():
    facts = valid_sandbox_capability_facts(trajectory_id="traj_9999")
    with pytest.raises(GateInputError, match="traj_9999"):
        await run_finalize(sandbox_capability_facts=facts)


def test_capability_facts_model_rejects_duplicates_and_overlap():
    with pytest.raises(ValidationError, match="重复"):
        SandboxCapabilityFacts.model_validate(
            valid_sandbox_capability_facts(verified_capabilities=["non_root_user", "non_root_user"])
        )
    with pytest.raises(ValidationError, match="矛盾"):
        SandboxCapabilityFacts.model_validate(
            valid_sandbox_capability_facts(violations=["non_root_user"])
        )
    assert len(set(REQUIRED_SANDBOX_CAPABILITIES)) == len(REQUIRED_SANDBOX_CAPABILITIES) == 9
