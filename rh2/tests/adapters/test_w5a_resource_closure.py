"""W5a：资源闭包一次性取数（内存保守上界 + 随 attempt 增长集合盘点 + fsync 延迟）。"""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest

from repoharness2.shutdown import (
    GROWING_COLLECTIONS,
    MemoryBoundInputs,
    collect_growth_facts,
    estimate_memory_upper_bound,
    measure_fsync_latency,
    resource_closure_facts,
    write_resource_closure_facts,
)

BASE = MemoryBoundInputs(
    max_concurrent_executions=8,
    grading_concurrency=4,
    model_call_limit=32,
    max_turns_per_execution=25,
    max_new_tokens_per_turn=4096,
    max_context_tokens=32768,
    top_k_support=64,
    max_attempts_retained=1000,
)


def test_memory_upper_bound_breakdown_is_explicit_and_monotonic():
    est = estimate_memory_upper_bound(BASE)
    assert est["upper_bound_bytes"] == (
        est["live_total_bytes"] + est["process_bounded_bytes"] + est["retained_total_bytes"]
    )
    assert est["live_total_bytes"] == 8 * est["live_per_execution_bytes"] + 4 * est["coefficients"]["per_grading_live_bytes"]
    assert est["retained_total_bytes"] == 1000 * est["coefficients"]["per_attempt_retained_bytes"]
    assert est["inputs"] == dataclasses.asdict(BASE)
    assert est["unbounded_collections"] == sorted(
        name for name, (_o, _a, bounded, _n) in GROWING_COLLECTIONS.items() if not bounded
    )
    assert "orchestrator_audits" in est["unbounded_collections"]  # generate.py:2279 只 append 不裁剪
    more = estimate_memory_upper_bound(dataclasses.replace(BASE, max_concurrent_executions=16))
    assert more["upper_bound_bytes"] > est["upper_bound_bytes"]
    assert more["retained_total_bytes"] == est["retained_total_bytes"]  # 并发不影响累积项
    longer = estimate_memory_upper_bound(dataclasses.replace(BASE, max_attempts_retained=5000))
    assert longer["retained_total_bytes"] == 5 * est["retained_total_bytes"]
    unknown_ctx = estimate_memory_upper_bound(dataclasses.replace(BASE, max_context_tokens=0))
    assert unknown_ctx["coefficients"]["context_tokens_assumed"] == 4096 * 25  # 未知上下文按 tokens×turns 估


def test_memory_inputs_validation_rejects_non_ints_and_bad_ranges():
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, top_k_support=0)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, max_concurrent_executions=0)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, grading_concurrency=-1)
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, max_new_tokens_per_turn=4096.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        dataclasses.replace(BASE, model_call_limit=True)  # type: ignore[arg-type]


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
    assert loaded["schema_id"] == "rh2.resource_closure_facts.v1" and loaded["phase"] == "startup"
    assert loaded["memory_upper_bound"]["status"] == "unavailable"  # 输入不全 = 如实，不猜
    assert loaded["fsync_latency"]["samples"] == 2
    assert loaded["peak_rss_bytes"] is None or loaded["peak_rss_bytes"] > 0
    assert not (tmp_path / "resource_closure.json.tmp").exists()
    full = resource_closure_facts(phase="shutdown", memory_inputs=BASE, fsync_dir=None, growth={"x": {"length": 1}})
    assert full["memory_upper_bound"]["upper_bound_bytes"] > 0 and full["fsync_latency"]["status"] == "unavailable"
