"""W5a：资源闭包一次性取数（内存估计 + 随 attempt 增长集合盘点 + fsync 延迟）。

口径（codex W5a 复核 #7）：`memory_estimate` 是估计不是上界——状态恒为
`unbounded_or_unknown`，并列出未被约束的来源；不加 attempt cap。
"""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest

from repoharness2.shutdown import (
    GROWING_COLLECTIONS,
    MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES,
    MemoryEstimateInputs,
    collect_growth_facts,
    estimate_memory,
    measure_fsync_latency,
    resource_closure_facts,
    write_resource_closure_facts,
)

BASE = MemoryEstimateInputs(
    max_concurrent_executions=8,
    grading_concurrency=4,
    model_call_limit=32,
    max_turns_per_execution=25,
    max_new_tokens_per_turn=4096,
    max_context_tokens=32768,
    top_k_support=64,
    planned_attempts=1000,
    buffer_capacity_groups=4,
    samples_per_group=8,
)


def test_memory_estimate_is_explicit_unbounded_or_unknown_and_lists_unconstrained_sources():
    est = estimate_memory(BASE)
    assert est["status"] == "unbounded_or_unknown"
    assert "upper_bound_bytes" not in est  # 旧口径字段不再出现
    assert est["estimate_bytes"] == (
        est["live_total_bytes"] + est["process_bounded_bytes"] + est["buffer_bytes"] + est["retained_planned_bytes"]
    )
    assert est["live_total_bytes"] == 8 * est["live_per_execution_bytes"] + 4 * est["coefficients"]["per_grading_live_bytes"]
    assert est["buffer_bytes"] == 4 * 8 * est["coefficients"]["per_buffered_sample_bytes"]  # 已完成 buffer 计入
    assert est["retained_planned_bytes"] == 1000 * est["coefficients"]["per_attempt_retained_bytes"]
    assert est["inputs"] == dataclasses.asdict(BASE)
    assert est["unconstrained_sources"] == list(MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES)
    assert any(src.startswith("attempt_total_no_cap") for src in est["unconstrained_sources"])
    assert any(src.startswith("completed_groups_in_buffer") for src in est["unconstrained_sources"])
    assert est["unbounded_collections"] == sorted(
        name for name, (_o, _a, bounded, _n) in GROWING_COLLECTIONS.items() if not bounded
    )
    assert "orchestrator_audits" in est["unbounded_collections"]  # generate.py 只 append 不裁剪


def test_memory_estimate_terms_are_monotonic_in_their_inputs():
    est = estimate_memory(BASE)
    more_conc = estimate_memory(dataclasses.replace(BASE, max_concurrent_executions=16))
    assert more_conc["estimate_bytes"] > est["estimate_bytes"]
    assert more_conc["retained_planned_bytes"] == est["retained_planned_bytes"]  # 并发不影响计划累积项
    more_planned = estimate_memory(dataclasses.replace(BASE, planned_attempts=5000))
    assert more_planned["retained_planned_bytes"] == 5 * est["retained_planned_bytes"]
    no_buffer = estimate_memory(dataclasses.replace(BASE, buffer_capacity_groups=0))
    assert no_buffer["buffer_bytes"] == 0 and no_buffer["status"] == "unbounded_or_unknown"  # 未知仍是估计
    unknown_ctx = estimate_memory(dataclasses.replace(BASE, max_context_tokens=0))
    assert unknown_ctx["coefficients"]["context_tokens_assumed"] == 4096 * 25  # 未知上下文按 tokens×turns 估


def test_memory_inputs_validation_rejects_non_ints_and_bad_ranges():
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, top_k_support=0)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, max_concurrent_executions=0)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, grading_concurrency=-1)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, samples_per_group=0)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, max_new_tokens_per_turn=4096.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, model_call_limit=True)  # type: ignore[arg-type]
    assert estimate_memory(dataclasses.replace(BASE, planned_attempts=0))["retained_planned_bytes"] == 0  # 0 = 计划未知合法


def test_fsync_latency_single_measurement_real_disk(tmp_path):
    result = measure_fsync_latency(tmp_path, samples=4, payload_bytes=128)
    assert result["samples"] == 4 and len(result["per_op_ms"]) == 4
    assert 0.0 <= result["p50_ms"] <= result["p95_ms"] <= result["p99_ms"] <= result["max_ms"]
    assert result["fsync_only_p50_ms"] <= result["fsync_only_max_ms"] <= result["max_ms"] + 1e-6
    probe_dir = tmp_path / ".fsync_probe"
    assert probe_dir.is_dir() and list(probe_dir.iterdir()) == []  # 探针文件用完即删
    with pytest.raises(ValueError):
        measure_fsync_latency(tmp_path, samples=0)


def test_growth_facts_cover_every_registered_collection():
    orchestrator = SimpleNamespace(audits=[1, 2], outcomes=[], cleanup_quarantine=["c"])
    manager = SimpleNamespace(_records=[1], leases=[1], cleanup_failures=[])
    queue = SimpleNamespace(events=[])
    registry = SimpleNamespace(hooks={"s": 1}, model_call_proxy=None, poison=SimpleNamespace(_archived={}))
    facts = collect_growth_facts(orchestrator=orchestrator, grading_manager=manager, grading_queue=queue, registry=registry)
    assert set(facts) == set(GROWING_COLLECTIONS)
    assert facts["orchestrator_audits"]["length"] == 2 and facts["orchestrator_audits"]["bounded"] is False
    assert facts["orchestrator_cleanup_quarantine"]["length"] == 1
    assert facts["registry_hooks"]["length"] == 1 and facts["registry_hooks"]["bounded"] is True
    assert facts["proxy_audit_artifacts"]["length"] is None  # proxy 缺席如实 None
    assert facts["poison_archive"]["length"] == 0
    nothing = collect_growth_facts()
    assert all(v["length"] is None for v in nothing.values())


def test_resource_closure_facts_written_atomically(tmp_path):
    facts = resource_closure_facts(phase="startup", memory_inputs=None, fsync_dir=tmp_path, growth=None, fsync_samples=2)
    path = write_resource_closure_facts(tmp_path / "resource_closure.json", facts)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema_id"] == "rh2.resource_closure_facts.v2" and loaded["phase"] == "startup"
    assert "memory_upper_bound" not in loaded
    assert loaded["memory_estimate"]["status"] == "unavailable"  # 输入不全 = 如实，不猜
    assert loaded["memory_estimate"]["unconstrained_sources"] == list(MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES)
    assert loaded["fsync_latency"]["samples"] == 2
    assert loaded["peak_rss_bytes"] is None or loaded["peak_rss_bytes"] > 0
    assert not (tmp_path / "resource_closure.json.tmp").exists()
    full = resource_closure_facts(phase="shutdown", memory_inputs=BASE, fsync_dir=None, growth={"x": {"length": 1}})
    assert full["memory_estimate"]["status"] == "unbounded_or_unknown"
    assert full["memory_estimate"]["estimate_bytes"] > 0 and full["fsync_latency"]["status"] == "unavailable"
