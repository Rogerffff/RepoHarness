"""F2-0b Observability V0 验收：V0 唯一可执行清单四项。

原则（决策包 v4 D1a②）：只记录，不用新计时改变 termination/reward/
admission/gradient；不派生 chargeable_execution_seconds；不导出
trajectory.jsonl。
"""

from __future__ import annotations

from repoharness2.adapters.slime.generate import (
    RolloutAudit,
    _extract_server_timing,
)
from repoharness2.contracts.capture import GenerationCaptureRecord  # noqa: F401
from repoharness2.contracts.fa_runtime import ModelCallAttempt


def test_timeline_events_carry_three_fields():
    """项 1：每个 timeline 事件带 clock_domain_id/owner_role/
    physical_attempt_id；physical_attempt_id 自动取 audit 自身。"""

    audit = RolloutAudit(trajectory_id="t", task_id="k", physical_attempt_id="e#p1-x")
    audit.mark("materialize_started")
    audit.mark("model_send_started", clock_domain_id="adapter_loop", owner_role="proxy")
    dicts = audit.timeline_dicts()
    assert dicts[0]["clock_domain_id"] == "orchestrator_loop"  # 默认域
    assert dicts[0]["physical_attempt_id"] == "e#p1-x"  # 自动带
    assert dicts[1]["clock_domain_id"] == "adapter_loop"  # proxy 域
    assert dicts[1]["owner_role"] == "proxy"


def test_server_timing_whitelist_extraction():
    """项 4：只摘白名单数值键；非数值/非白名单/bool 全滤掉；全缺返回 None。"""

    meta = {
        "id": "rid", "weight_version": "7",  # 非白名单，不收
        "queue_time": 0.012, "e2e_latency": 1.5, "decode_throughput": 42,
        "cached_tokens": 128, "finish_reason": {"type": "stop"},  # dict，不收
        "some_flag": True,  # bool 排除（bool 是 int 子类，显式滤）
    }
    st = _extract_server_timing(meta)
    assert st == {
        "queue_time": 0.012, "e2e_latency": 1.5,
        "decode_throughput": 42.0, "cached_tokens": 128.0,
    }
    assert _extract_server_timing({"id": "x"}) is None  # 全缺 → None


def test_capture_record_accepts_server_timing():
    """项 4 契约：GenerationCaptureRecord 接受 optional server_timing。"""

    assert "server_timing" in GenerationCaptureRecord.model_fields


def test_model_call_attempt_interval_fields_optional():
    """项 3：ModelCallAttempt 三个区间字段 optional（字段本切片加，proxy
    填值随 F2-3）；默认 None，非负校验。"""

    a = ModelCallAttempt(
        logical_turn_id="s/t1", model_call_attempt_id="s/t1_a1",
        attempt_number=1, delivery_status="non_delivered_failed",
    )
    assert a.wait_active_seconds is None and a.send_seconds is None
    b = ModelCallAttempt(
        logical_turn_id="s/t1", model_call_attempt_id="s/t1_a2",
        attempt_number=2, delivery_status="non_delivered_failed",
        wait_active_seconds=0.5, send_seconds=1.2,
    )
    assert b.wait_active_seconds == 0.5


def test_audit_records_raw_dual_clock_not_chargeable():
    """项 2：audit 持有 non_chargeable_intervals 原始区间字段，V0 不派生
    chargeable——审计记录只出 wall_* + 原始区间（在 bringup 写入时）。"""

    audit = RolloutAudit(trajectory_id="t", task_id="k")
    assert audit.non_chargeable_intervals == []  # 原始区间容器
    # V0 不提供 chargeable 派生方法（防误用）
    assert not hasattr(audit, "chargeable_execution_seconds")
