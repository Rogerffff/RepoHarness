"""eligibility.py 的 fail-closed 单测：三档结论与七维事实的互锁。"""

import pytest
from contract_samples import valid_eligibility_facts, valid_eligibility_report
from pydantic import ValidationError

from repoharness2.contracts import (
    DimensionFact,
    EligibilityFacts,
    EligibilityReport,
    compute_facts_digest,
)


def test_online_class_with_failed_dimension_rejected():
    """任一维度失败即不得授予 online 档（七维合取）。"""

    payload = valid_eligibility_report()
    payload["facts"] = valid_eligibility_facts(all_ok=False)  # logprob 维失败
    payload["facts_digest"] = compute_facts_digest(
        EligibilityFacts.model_validate(payload["facts"])
    )
    payload["eligibility_class"] = "online_policy_loss_eligible"
    payload["derived_view_class"] = "online_policy_loss_eligible"
    payload["reason_codes"] = []
    with pytest.raises(ValidationError, match="logprob_alignment"):
        EligibilityReport.model_validate(payload)


def test_facts_digest_mismatch_rejected():
    payload = valid_eligibility_report()
    payload["facts_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="facts_digest"):
        EligibilityReport.model_validate(payload)


def test_security_failure_forces_audit_only():
    """executed 级泄漏（security 维失败）时结论必须 audit_only_or_rejected（从严）。"""

    payload = valid_eligibility_report()
    facts = valid_eligibility_facts()
    facts["security_and_leakage"] = {
        "ok": False,
        "reason_codes": ["executed_hidden_asset_leak"],
        "evidence_refs": ["finding_0009"],
    }
    payload["facts"] = facts
    payload["facts_digest"] = compute_facts_digest(EligibilityFacts.model_validate(facts))
    payload["eligibility_class"] = "offline_or_sft_candidate"  # 不够严 -> 拒收
    payload["derived_view_class"] = "offline_or_sft_candidate"
    payload["reason_codes"] = ["executed_hidden_asset_leak"]
    with pytest.raises(ValidationError, match="audit_only_or_rejected"):
        EligibilityReport.model_validate(payload)

    payload["eligibility_class"] = "audit_only_or_rejected"
    payload["derived_view_class"] = "audit_only_or_rejected"
    report = EligibilityReport.model_validate(payload)
    assert report.eligibility_class == "audit_only_or_rejected"


def test_failed_dimension_without_reason_codes_rejected():
    with pytest.raises(ValidationError, match="reason_codes"):
        DimensionFact.model_validate({"ok": False, "reason_codes": [], "evidence_refs": []})


def test_downgrade_without_reason_codes_rejected():
    """S1 默认封顶也必须写理由码（如 s1_default_ceiling_offline），不许静默降级。"""

    payload = valid_eligibility_report()
    payload["reason_codes"] = []
    with pytest.raises(ValidationError, match="reason_codes"):
        EligibilityReport.model_validate(payload)


def test_derived_view_ref_mismatch_rejected():
    payload = valid_eligibility_report()
    payload["derived_view_report_ref"] = "elig_9999"
    with pytest.raises(ValidationError, match="derived_view_report_ref"):
        EligibilityReport.model_validate(payload)


def test_derived_view_class_mismatch_rejected():
    payload = valid_eligibility_report()
    payload["derived_view_class"] = "online_policy_loss_eligible"
    with pytest.raises(ValidationError, match="derived_view_class"):
        EligibilityReport.model_validate(payload)


def test_all_ok_facts_can_reach_online_class():
    payload = valid_eligibility_report()
    payload["eligibility_class"] = "online_policy_loss_eligible"
    payload["derived_view_class"] = "online_policy_loss_eligible"
    payload["reason_codes"] = []
    report = EligibilityReport.model_validate(payload)
    assert report.facts.all_ok()


def test_finalize_helper_produces_valid_report():
    facts = EligibilityFacts.model_validate(valid_eligibility_facts())
    report = EligibilityReport.finalize(
        report_id="elig_0002",
        trajectory_id="traj_0001",
        gate_version="gate_s1_v1",
        facts=facts,
        eligibility_class="offline_or_sft_candidate",
        reason_codes=["s1_default_ceiling_offline"],
        created_at_utc="2026-07-07T09:30:25Z",
    )
    assert report.facts_digest == compute_facts_digest(facts)
    assert report.derived_view_report_ref == report.report_id
