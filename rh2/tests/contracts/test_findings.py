"""findings.py 的 fail-closed 单测：attempted|executed 语义与证据回链。"""

import pytest
from contract_samples import valid_anti_cheat_finding, valid_quality_finding
from pydantic import ValidationError

from repoharness2.contracts import AntiCheatFinding, TrajectoryQualityFinding


def test_attempted_blocked_requires_anti_hack_event_ref():
    """没有拦截事件存证的 attempted 不可表示（防 executed 伪装成 attempted）。"""

    payload = valid_anti_cheat_finding()
    payload["anti_hack_event_ref"] = None
    with pytest.raises(ValidationError, match="anti_hack_event_ref"):
        AntiCheatFinding.model_validate(payload)


def test_executed_finding_without_event_ref_is_valid():
    payload = valid_anti_cheat_finding()
    payload["enforcement"] = "executed"
    payload["anti_hack_event_ref"] = None
    payload["detection_layer"] = "post_hoc_scan"
    finding = AntiCheatFinding.model_validate(payload)
    assert finding.enforcement == "executed"


def test_judge_precision_only_for_judge_layer():
    payload = valid_anti_cheat_finding()
    payload["judge_precision"] = 0.9  # detection_layer 是 online_interception
    with pytest.raises(ValidationError, match="llm_judge_review"):
        AntiCheatFinding.model_validate(payload)


def test_judge_precision_out_of_range_rejected():
    payload = valid_anti_cheat_finding()
    payload["detection_layer"] = "llm_judge_review"
    payload["judge_precision"] = 1.5
    with pytest.raises(ValidationError):
        AntiCheatFinding.model_validate(payload)


def test_unknown_category_rejected():
    payload = valid_anti_cheat_finding()
    payload["category"] = "creative_hacking"
    with pytest.raises(ValidationError):
        AntiCheatFinding.model_validate(payload)


def test_quality_finding_valid_and_strict():
    finding = TrajectoryQualityFinding.model_validate(valid_quality_finding())
    assert finding.severity == "warning"
    payload = valid_quality_finding()
    payload["severity"] = "catastrophic"  # 词表外
    with pytest.raises(ValidationError):
        TrajectoryQualityFinding.model_validate(payload)
