"""anti_hack.py 的 fail-closed 单测：拦截事件必须留全两侧存证。"""

import pytest
from contract_samples import valid_anti_hack_event
from pydantic import ValidationError

from repoharness2.contracts import AntiHackEvent


def test_missing_dummy_observation_ref_rejected():
    payload = valid_anti_hack_event()
    del payload["dummy_observation_ref"]
    with pytest.raises(ValidationError, match="dummy_observation_ref"):
        AntiHackEvent.model_validate(payload)


def test_missing_blocked_tool_call_ref_rejected():
    payload = valid_anti_hack_event()
    del payload["blocked_tool_call_ref"]
    with pytest.raises(ValidationError, match="blocked_tool_call_ref"):
        AntiHackEvent.model_validate(payload)


def test_unknown_channel_rejected():
    payload = valid_anti_hack_event()
    payload["channel"] = "carrier_pigeon"
    with pytest.raises(ValidationError):
        AntiHackEvent.model_validate(payload)


def test_interrupted_rollout_is_representable_fact():
    """拦截意外中断轨迹是需要审计的异常事实：允许表示，gate 侧关注。"""

    payload = valid_anti_hack_event()
    payload["rollout_continued"] = False
    event = AntiHackEvent.model_validate(payload)
    assert event.rollout_continued is False
