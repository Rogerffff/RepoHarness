"""timing.py 的 fail-closed 单测：F5 五类计时 + 资源画像。"""

import pytest
from contract_samples import valid_timing_record
from pydantic import ValidationError

from repoharness2.contracts import GradingTimingRecord


def test_negative_seconds_rejected():
    payload = valid_timing_record()
    payload["test_seconds"] = -0.1
    with pytest.raises(ValidationError):
        GradingTimingRecord.model_validate(payload)


def test_total_less_than_test_seconds_rejected():
    payload = valid_timing_record()
    payload["total_grading_seconds"] = 40.0  # < test_seconds 41.7
    with pytest.raises(ValidationError, match="不得小于"):
        GradingTimingRecord.model_validate(payload)


def test_missing_container_peak_rejected():
    """F5 明确要求记录容器峰值：字段必填，不给"忘了测"留位置。"""

    payload = valid_timing_record()
    del payload["container_peak_memory_mb"]
    with pytest.raises(ValidationError, match="container_peak_memory_mb"):
        GradingTimingRecord.model_validate(payload)


def test_missing_queue_wait_rejected():
    payload = valid_timing_record()
    del payload["queue_wait_seconds"]
    with pytest.raises(ValidationError, match="queue_wait_seconds"):
        GradingTimingRecord.model_validate(payload)


def test_backpressure_event_representable():
    payload = valid_timing_record()
    payload["backpressure_triggered"] = True
    payload["queue_depth_at_enqueue"] = 8  # 队列打满（F5 首版队列上限 8）
    record = GradingTimingRecord.model_validate(payload)
    assert record.backpressure_triggered is True
