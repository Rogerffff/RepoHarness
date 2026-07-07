"""handshake.py 的 fail-closed 单测：staleness 派生互检与组信号账目。"""

import pytest
from contract_samples import valid_backend_handshake, valid_group_signal
from pydantic import ValidationError

from repoharness2.contracts import BackendHandshake, GroupSignal


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
