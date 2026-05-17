from __future__ import annotations

from repo_harness_verl import build_inference_metric_source_inventory, build_inference_server_profile


PROMETHEUS_TEXT = """
# HELP sglang_scheduler_queue_wait_seconds queue wait
sglang_scheduler_queue_wait_seconds 0.10
sglang_scheduler_queue_wait_seconds 0.30
sglang_prefill_seconds 0.20
sglang_decode_seconds 0.40
sglang_prefix_cache_hit_total 8
sglang_prefix_cache_miss_total 2
sglang_kv_cache_eviction_total 1
sglang_generation_tokens_per_second 120
dcgm_gpu_utilization 75
sglang_num_batched_tokens 1024
sglang_num_preempted_total 0
"""


def test_stage12_5_inference_metric_inventory_maps_known_prometheus_metrics() -> None:
    inventory = build_inference_metric_source_inventory(
        backend_name="sglang",
        backend_version="0.5.6",
        server_address="http://127.0.0.1:30000/metrics",
        raw_prometheus_text=PROMETHEUS_TEXT,
    )

    assert inventory.metrics_endpoint_checked is True
    assert inventory.canonical_metric_mapping["inference_server_queue_wait_seconds"] == (
        "sglang_scheduler_queue_wait_seconds"
    )
    assert inventory.canonical_metric_mapping["tokens_per_second"] == "sglang_generation_tokens_per_second"
    assert inventory.unsupported_diagnostics == []


def test_stage12_5_inference_profile_uses_backend_metrics_when_available() -> None:
    inventory = build_inference_metric_source_inventory(backend_name="sglang", raw_prometheus_text=PROMETHEUS_TEXT)

    profile = build_inference_server_profile(inventory=inventory, raw_prometheus_text=PROMETHEUS_TEXT)

    assert profile.metric_source == "prometheus"
    assert profile.inference_server_queue_wait_seconds_p50 == 0.2
    assert profile.inference_server_queue_wait_seconds_p95 == 0.29
    assert profile.prefill_seconds_p50 == 0.2
    assert profile.decode_seconds_p50 == 0.4
    assert profile.prefix_cache_hit_rate == 0.8
    assert profile.tokens_per_second == 120
    assert profile.num_preempted == 0


def test_stage12_5_inference_profile_records_unsupported_diagnostics_and_client_fallback() -> None:
    inventory = build_inference_metric_source_inventory(backend_name="vllm", raw_prometheus_text="")
    profile = build_inference_server_profile(
        inventory=inventory,
        client_generate_records=[
            {"output_token_ids": [1, 2, 3], "duration_ms": 1500},
            {"output_token_count": 2, "duration_ms": 500},
        ],
    )

    assert profile.metric_source == "client_side_estimate"
    assert round(profile.tokens_per_second or 0.0, 4) == round(5 / 2.0, 4)
    assert "server_queue_wait_metric_unavailable" in profile.unsupported_diagnostics
    assert "tokens_per_second_backend_metric_unavailable" in profile.unsupported_diagnostics
