"""handshake.py 的 fail-closed 单测：staleness 派生互检与组信号账目。

S1-1b 追加 accepted 语义定案测试：accepted 仅表示后端物理接收，
可训练性唯一权威是 EligibilityReport（policy_staleness 维度）。
"""

import pytest
from contract_samples import (
    valid_backend_handshake,
    valid_eligibility_facts,
    valid_eligibility_report,
    valid_group_signal,
)
from pydantic import ValidationError

from repoharness2.contracts import (
    BackendHandshake,
    EligibilityFacts,
    EligibilityReport,
    GroupSignal,
    compute_facts_digest,
)


def test_staleness_derived_view_mismatch_rejected():
    """staleness_steps=6 > threshold=4 却声明 within=True -> 账实不符拒收。"""

    payload = valid_backend_handshake()
    payload["staleness_steps"] = 6
    payload["staleness_within_threshold"] = True
    with pytest.raises(ValidationError, match="派生视图互检"):
        BackendHandshake.model_validate(payload)


def test_stale_but_honest_handshake_valid():
    payload = valid_backend_handshake()
    payload["staleness_steps"] = 6
    payload["staleness_within_threshold"] = False
    payload["accepted"] = False
    payload["backend_rejection_reason"] = "staleness_exceeded"
    handshake = BackendHandshake.model_validate(payload)
    assert handshake.accepted is False


def test_accepted_with_rejection_reason_rejected():
    payload = valid_backend_handshake()
    payload["backend_rejection_reason"] = "capacity_backpressure"
    with pytest.raises(ValidationError, match="不得携带"):
        BackendHandshake.model_validate(payload)


def test_rejection_without_reason_rejected():
    payload = valid_backend_handshake()
    payload["accepted"] = False
    with pytest.raises(ValidationError, match="拒收不可无因"):
        BackendHandshake.model_validate(payload)


def test_other_reason_requires_note():
    payload = valid_backend_handshake()
    payload["accepted"] = False
    payload["backend_rejection_reason"] = "other"
    with pytest.raises(ValidationError, match="rejection_note"):
        BackendHandshake.model_validate(payload)


def test_empty_weight_versions_rejected():
    payload = valid_backend_handshake()
    payload["weight_versions_seen"] = []
    with pytest.raises(ValidationError):
        BackendHandshake.model_validate(payload)


def test_group_accounting_overflow_rejected():
    """delivered 3 + degraded 2 > expected 4：组账目不平必须拒收。"""

    payload = valid_group_signal()
    payload["degraded_sample_count"] = 2
    with pytest.raises(ValidationError, match="组账目不平"):
        GroupSignal.model_validate(payload)


def test_degrade_must_be_visible_before_assembly():
    payload = valid_group_signal()
    payload["degrade_visible_before_assembly"] = False
    with pytest.raises(ValidationError, match="组装配前"):
        GroupSignal.model_validate(payload)


def test_ppo_single_sample_handshake_without_group_signal():
    """算法无关原则：num_samples=1 的 PPO 形态没有组信号也必须一等可用。"""

    payload = valid_backend_handshake()
    payload["group_signal"] = None
    handshake = BackendHandshake.model_validate(payload)
    assert handshake.group_signal is None


def test_accepted_is_physical_receipt_not_trainability():
    """accepted 语义定案（S1-1b）：accepted=True 仅是后端物理接收，不构成资格背书。

    两步证明：
    1. "staleness 超阈值但后端照收"（accepted=True + within=False）是合法握手
       ——接收过期样本是后端的算法自由（H10），契约不阻拦；
    2. 资格判定路径只消费 staleness 事实：policy_staleness 维度失败时，
       EligibilityReport 的 online 档照样不可表示，accepted=True 救不回来。
    """

    payload = valid_backend_handshake()
    payload["staleness_steps"] = 6  # 超过阈值 4
    payload["staleness_within_threshold"] = False
    payload["accepted"] = True
    handshake = BackendHandshake.model_validate(payload)
    assert handshake.accepted and not handshake.staleness_within_threshold

    facts = valid_eligibility_facts()
    facts["policy_staleness"] = {
        "ok": False,
        "reason_codes": ["staleness_exceeded"],
        "evidence_refs": [handshake.handshake_id],  # 事实来源正是上面那次"已接收"的握手
    }
    report = valid_eligibility_report()
    report["facts"] = facts
    report["facts_digest"] = compute_facts_digest(EligibilityFacts.model_validate(facts))
    report["eligibility_class"] = "online_policy_loss_eligible"
    report["derived_view_class"] = "online_policy_loss_eligible"
    report["reason_codes"] = []
    with pytest.raises(ValidationError, match="policy_staleness"):
        EligibilityReport.model_validate(report)
