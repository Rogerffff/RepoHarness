"""N1（第 2 组 §4 / I15-I20 观测）：编排 finally 段的 `attempt_cost_snapshot` 事件。

真实 formal 编排（Docker / 评分为替身），只把事件发射函数换成捕获器：
- present / aborted / fatal 三种终局各一条快照，字段与 audit 一致；
- token 口径 = capture 记录的 response_token_count 之和（真实 tape 计数），不是 response_length；
  未到装配阶段（引导崩溃）的 token 事实为 None，不填 0；
- 对照（Codex 计划审查 R4）：快照已发、随后 audit sink 失败 → 快照只是当时事实，汇总不把它算成消费成功；
- 发射失败不改 delivered / receipt。
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_slime_generate import (  # noqa: E402
    FROZEN_IMG_DIGEST,
    SAMPLING_PARAMS,
    TASK_ID_DENSE,
    FakeFinalizationStore,
    FakeRolloutDocker,
    _Args,
    make_task,
)
from test_w1b_termination_facts_producer import _formal_chain, _steps  # noqa: E402

from repoharness2.adapters.slime import generate as generate_mod  # noqa: E402
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.generate import SlimeBindingError  # noqa: E402


def _capture(monkeypatch):
    events: list[dict] = []

    def emit(kind, **fields):
        events.append({"event": kind, "run_id": "r1", **fields})
        return True

    monkeypatch.setattr(generate_mod, "_emit_rh2_event", emit)
    return events


async def test_present_member_snapshot_uses_capture_token_counts(monkeypatch):
    events = _capture(monkeypatch)
    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (snap,) = [e for e in events if e["event"] == "attempt_cost_snapshot"]
    records = chain.adapter_ref["adapter"].hook.records
    assert snap["physical_attempt_id"] == audit.physical_attempt_id and snap["task_id"] == audit.task_id
    assert snap["rh2_prompt_group_id"] == "pg_F22" and snap["rh2_group_index"] == 5 and snap["rh2_member_slot"] == 2
    assert snap["disposition_hint"] == "present" and snap["completion_class"].startswith("present")
    assert snap["capture_record_count"] == len(records) >= 1
    assert snap["captured_output_tokens"] == sum(r.response_token_count for r in records)  # 真实 tape 计数
    assert "response_length" not in snap  # 不用含工具输出的 response 区域长度冒充生成量
    assert snap["elapsed_seconds"] >= 0 and isinstance(snap["lifecycle_segments_seconds"], dict)
    assert snap["grading_outcome"] in ("resolved", "unresolved")
    assert snap["receipt_disposition"] == "delivery_prepared" and snap["receipt_id"] == store.receipts[0].receipt_id
    assert "attempt_cost_snapshot_emitted" in _steps(audit)
    assert all(not getattr(x, "remove_sample", False) for x in delivered)


async def test_aborted_member_snapshot_keeps_unknown_tokens_as_null(monkeypatch):
    events = _capture(monkeypatch)
    chain = _formal_chain(FakeFinalizationStore(), crash=SlimeBindingError("harness_bootstrap_failed", "cli exploded"))
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (snap,) = [e for e in events if e["event"] == "attempt_cost_snapshot"]
    assert snap["disposition_hint"] == "aborted" and snap["reason_code"] == "harness_bootstrap_failed"
    assert snap["completion_class"] == "missing"
    assert snap["captured_output_tokens"] is None and snap["capture_record_count"] is None  # 未知不填 0
    assert snap["receipt_disposition"] == "aborted"
    assert all(getattr(x, "remove_sample", False) for x in delivered)


async def test_fatal_snapshot_is_emitted_before_the_exception_propagates(monkeypatch):
    events = _capture(monkeypatch)
    docker = FakeRolloutDocker(repo_digests=("fake/img@sha256:" + "2" * 64,))
    task = make_task(TASK_ID_DENSE, image_manifest_digest=FROZEN_IMG_DIGEST)
    chain = _formal_chain(FakeFinalizationStore(), docker=docker, task=task)
    with pytest.raises(FatalExecutionInfrastructureError, match="rollout_image_digest_mismatch"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (snap,) = [e for e in events if e["event"] == "attempt_cost_snapshot"]
    assert snap["disposition_hint"] == "fatal" and snap["termination_kind"] is None
    assert snap["last_failure"]["stage"] == "materialize"
    assert snap["receipt_disposition"] == "fatal_run_halt"
    assert snap["captured_output_tokens"] is None


async def test_snapshot_before_audit_sink_failure_is_not_counted_as_consumed(monkeypatch):
    """Codex 计划审查 R4：finally 中间的快照不是权威终态——之后 audit sink 失败会变成 run-fatal、样本不交付；
    汇总只认 buffer 终局事件，这条快照记为 unmatched。"""

    events = _capture(monkeypatch)
    chain = _formal_chain(FakeFinalizationStore())

    def broken_sink(audit):
        raise OSError("audit store unavailable")

    chain.orchestrator._audit_sink = broken_sink
    with pytest.raises(FatalExecutionInfrastructureError, match="execution_audit_write_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (snap,) = [e for e in events if e["event"] == "attempt_cost_snapshot"]
    assert snap["disposition_hint"] == "present"  # 快照发出时的事实
    assert not [e for e in events if e["event"] in ("group_consumed", "group_filtered")]  # 没有 buffer 终局
    # 汇总侧的对应断言（无终局事件的快照记 unmatched，不进 consumed 桶）在 miles 通道的
    # tests/adapters_miles/test_w4_drop_event_summary.py（本通道不能 import repoharness2.adapters.miles）。
    assert chain.orchestrator.audits[0].outcome_v2 is not None  # 快照当时确实是 present 事实


async def test_emit_failure_does_not_change_delivery_or_receipt(monkeypatch):
    def boom(kind, **fields):
        raise RuntimeError("event sink exploded")

    monkeypatch.setattr(generate_mod, "_emit_rh2_event", boom)
    store = FakeFinalizationStore()
    chain = _formal_chain(store)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert any(s.startswith("attempt_cost_snapshot_failed:RuntimeError") for s in _steps(audit))
    assert store.receipts[0].attempt_disposition == "delivery_prepared"
    assert all(not getattr(x, "remove_sample", False) for x in delivered)


def test_emit_helper_is_a_noop_without_event_log(monkeypatch):
    monkeypatch.delenv("MILES_RH2_EVENT_DIR", raising=False)
    assert generate_mod._emit_rh2_event("attempt_cost_snapshot", physical_attempt_id="x") is False


@pytest.mark.parametrize("field", ["time_budget_seconds"])
def test_task_replace_keeps_snapshot_fixture_valid(field):
    # 夹具自检：dataclasses.replace 可用于本文件的 task 变体（与 F1 测试同一写法）
    task = make_task(TASK_ID_DENSE)
    assert dataclasses.replace(task, **{field: 1.0}).time_budget_seconds == 1.0
