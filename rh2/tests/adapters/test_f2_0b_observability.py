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
    audit.mark("materialize_started", owner_role="orchestrator")
    audit.mark("model_send_started", owner_role="proxy")
    dicts = audit.timeline_dicts()
    # clock_domain = 进程实例（同进程各线程同一 domain，可互减）——两事件
    # 同 domain（codex P1-2 纠正：不按线程拆 domain）
    assert dicts[0]["clock_domain_id"] == dicts[1]["clock_domain_id"]
    assert dicts[0]["clock_domain_id"].startswith("proc-")
    assert dicts[0]["physical_attempt_id"] == "e#p1-x"  # 自动带
    assert dicts[0]["owner_role"] == "orchestrator" and dicts[1]["owner_role"] == "proxy"
    assert dicts[1]["monotonic_ts"] >= dicts[0]["monotonic_ts"]  # 原始 monotonic 单调


def test_server_timing_whitelist_extraction():
    """项 4：只摘白名单数值键；非数值/非白名单/bool 全滤掉；全缺返回 None。"""

    meta = {
        "id": "rid", "weight_version": "7",  # 非白名单，不收
        "queue_time": 0.012, "e2e_latency": 1.5, "decode_throughput": 42,
        "cached_tokens": 128, "finish_reason": {"type": "stop"},  # dict，不收
        "some_flag": True,  # bool 排除（bool 是 int 子类，显式滤）
    }
    st = _extract_server_timing(meta)
    assert st is not None
    assert st.queue_time == 0.012 and st.e2e_latency == 1.5
    assert st.decode_throughput == 42.0 and st.cached_tokens == 128
    assert st.prompt_tokens is None  # 未提供
    assert _extract_server_timing({"id": "x"}) is None  # 全缺 → None
    # 引擎返回负值 → 该遥测整体丢弃（不阻断 capture，宁缺毋污染）
    assert _extract_server_timing({"queue_time": -7.0}) is None


def test_capture_record_accepts_server_timing():
    """项 4 契约：GenerationCaptureRecord 接受 optional server_timing。"""

    assert "server_timing" in GenerationCaptureRecord.model_fields


def test_model_call_attempt_interval_fields_optional():
    """项 3：ModelCallAttempt 三个区间字段 optional（字段本切片加，proxy
    填值随 F2-3）；默认 None，非负校验。"""

    import pytest

    a = ModelCallAttempt(
        logical_turn_id="s/t1", model_call_attempt_id="s/t1_a1",
        attempt_number=1, delivery_status="non_delivered_failed",
    )
    assert a.wait_active_interval is None and a.send_interval is None
    assert a.limiter_wait_interval is None  # P1-3：四段之一
    b = ModelCallAttempt(
        logical_turn_id="s/t1", model_call_attempt_id="s/t1_a2",
        attempt_number=2, delivery_status="non_delivered_failed",
        timing_clock_domain="proc-1",
        wait_active_interval=(10.0, 10.5), send_interval=(11.0, 12.2),
    )
    assert b.wait_active_interval == (10.0, 10.5)  # 原始区间可重建时间线
    # end < start 非法
    with pytest.raises(ValueError, match="非法区间"):
        ModelCallAttempt(
            logical_turn_id="s/t1", model_call_attempt_id="s/t1_a3",
            attempt_number=3, delivery_status="non_delivered_failed",
            send_interval=(12.0, 11.0),
        )


def test_audit_records_raw_dual_clock_not_chargeable():
    """项 2：audit 持有 non_chargeable_intervals 原始区间字段，V0 不派生
    chargeable——审计记录只出 wall_* + 原始区间（在 bringup 写入时）。"""

    audit = RolloutAudit(trajectory_id="t", task_id="k")
    assert audit.non_chargeable_intervals == []  # 原始区间容器
    # V0 不提供 chargeable 派生方法（防误用）
    assert not hasattr(audit, "chargeable_execution_seconds")


def test_server_timing_flows_through_real_capture_hook():
    """项 4 端到端（codex F2-0b P1-4）：真实 GenerationCaptureHook 的
    _record 确实调用 _extract_server_timing 并把结果放进 record.server_
    timing；污染键挡在契约外、负值触发整体丢弃（宁缺毋污染）。"""

    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    def _hook():
        return GenerationCaptureHook(
            trajectory_id="traj_st", model_name="Qwen/Qwen3-4B",
            backend_name="sglang", backend_version="0.5.13",
            renderer_cls_name="Qwen3Renderer", tokenizer_name="Qwen/Qwen3-4B",
            template_hash="sha256:" + "a" * 64,
        )

    params = {
        "temperature": 1.0, "top_p": 0.95, "max_new_tokens": 16,
        "return_top_p_token_ids": False, "return_routed_experts": False,
    }

    def _resp(meta_extra: dict) -> dict:
        return {
            "text": "ok",
            "meta_info": {
                "id": "rid_st",
                "finish_reason": {"type": "stop"},
                "output_token_logprobs": [[-0.1, 2000, None]],
                **meta_extra,
            },
        }

    # 干净白名单计时 + 污染键：只白名单进记录
    h = _hook()
    h.on_generate_response(
        prompt_token_ids=[10, 11, 12], sampling_params=params,
        response=_resp({"queue_time": 0.03, "e2e_latency": 2.1,
                        "hidden_verifier_secret_channel": 99.0}),
    )
    st = h.records[0].server_timing
    assert st is not None and st.queue_time == 0.03 and st.e2e_latency == 2.1
    assert "hidden_verifier_secret_channel" not in st.model_dump(exclude_none=True)

    # 负值 → 整体丢弃遥测（capture 不受阻，record 建立但 server_timing=None）
    h2 = _hook()
    h2.on_generate_response(
        prompt_token_ids=[10, 11, 12], sampling_params=params,
        response=_resp({"queue_time": 0.03, "decode_throughput": -5.0}),
    )
    assert h2.records[0].server_timing is None
    # 无任何计时键 → None
    h3 = _hook()
    h3.on_generate_response(
        prompt_token_ids=[10, 11, 12], sampling_params=params,
        response=_resp({}),
    )
    assert h3.records[0].server_timing is None
