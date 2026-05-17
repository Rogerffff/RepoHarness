"""Stage 12.5 inference-server metric inventory and profile helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel


CANONICAL_INFERENCE_METRICS = (
    "inference_server_queue_wait_seconds",
    "prefill_seconds",
    "decode_seconds",
    "prefix_cache_hit_rate",
    "kv_cache_eviction_count",
    "num_preempted",
    "tokens_per_second",
    "gpu_utilization",
    "batched_token_count",
)


class InferenceMetricSourceInventory(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_inference_metric_source_inventory_v0"
    backend_name: str
    backend_version: str | None = None
    server_address: str | None = None
    metrics_endpoint_checked: bool = False
    raw_metric_names_matched: dict[str, list[str]] = Field(default_factory=dict)
    canonical_metric_mapping: dict[str, str | None] = Field(default_factory=dict)
    unsupported_diagnostics: list[str] = Field(default_factory=list)


class InferenceServerProfile(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_inference_server_profile_v0"
    backend_name: str
    backend_version: str | None = None
    metric_source: str
    inference_server_queue_wait_seconds_p50: float | None = Field(default=None, ge=0.0)
    inference_server_queue_wait_seconds_p95: float | None = Field(default=None, ge=0.0)
    prefill_seconds_p50: float | None = Field(default=None, ge=0.0)
    prefill_seconds_p95: float | None = Field(default=None, ge=0.0)
    decode_seconds_p50: float | None = Field(default=None, ge=0.0)
    decode_seconds_p95: float | None = Field(default=None, ge=0.0)
    prefix_cache_hit_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    kv_cache_eviction_count: float | None = Field(default=None, ge=0.0)
    num_preempted: float | None = Field(default=None, ge=0.0)
    tokens_per_second: float | None = Field(default=None, ge=0.0)
    gpu_utilization_p50: float | None = Field(default=None, ge=0.0)
    gpu_utilization_p95: float | None = Field(default=None, ge=0.0)
    batched_token_count_p50: float | None = Field(default=None, ge=0.0)
    batched_token_count_p95: float | None = Field(default=None, ge=0.0)
    unsupported_diagnostics: list[str] = Field(default_factory=list)
    metric_name_mapping: dict[str, str | None] = Field(default_factory=dict)


def build_inference_metric_source_inventory(
    *,
    backend_name: str,
    backend_version: str | None = None,
    server_address: str | None = None,
    raw_prometheus_text: str | None = None,
) -> InferenceMetricSourceInventory:
    metrics = _parse_prometheus_text(raw_prometheus_text or "")
    mapping: dict[str, str | None] = {}
    matched: dict[str, list[str]] = {}
    unsupported: list[str] = []
    for canonical in CANONICAL_INFERENCE_METRICS:
        candidates = _candidate_metric_names(canonical, metrics)
        matched[canonical] = candidates
        mapping[canonical] = candidates[0] if candidates else None
        if not candidates:
            unsupported.append(_unsupported_diagnostic(canonical))
    if backend_name == "sglang" and "num_preempted" in unsupported:
        # SGLang TokenOutput currently does not project num_preempted in this reference tree.
        pass
    return InferenceMetricSourceInventory(
        backend_name=backend_name,
        backend_version=backend_version,
        server_address=server_address,
        metrics_endpoint_checked=raw_prometheus_text is not None,
        raw_metric_names_matched=matched,
        canonical_metric_mapping=mapping,
        unsupported_diagnostics=unsupported,
    )


def build_inference_server_profile(
    *,
    inventory: InferenceMetricSourceInventory,
    raw_prometheus_text: str | None = None,
    client_generate_records: Sequence[Mapping[str, Any]] | None = None,
) -> InferenceServerProfile:
    metrics = _parse_prometheus_text(raw_prometheus_text or "")
    records = list(client_generate_records or [])
    mapping = inventory.canonical_metric_mapping
    unsupported = list(inventory.unsupported_diagnostics)

    queue_values = _values_for(mapping.get("inference_server_queue_wait_seconds"), metrics)
    prefill_values = _values_for(mapping.get("prefill_seconds"), metrics)
    decode_values = _values_for(mapping.get("decode_seconds"), metrics)
    gpu_values = _values_for(mapping.get("gpu_utilization"), metrics)
    batched_values = _values_for(mapping.get("batched_token_count"), metrics)
    tokens_per_second = _last_value(mapping.get("tokens_per_second"), metrics)
    if tokens_per_second is None:
        tokens_per_second = _client_side_tokens_per_second(records)
        if tokens_per_second is not None and "tokens_per_second_backend_metric_unavailable" not in unsupported:
            unsupported.append("tokens_per_second_backend_metric_unavailable")

    prefix_cache_hit_rate = _prefix_cache_hit_rate(mapping.get("prefix_cache_hit_rate"), metrics)
    kv_cache_eviction_count = _last_value(mapping.get("kv_cache_eviction_count"), metrics)
    num_preempted = _last_value(mapping.get("num_preempted"), metrics)
    if num_preempted is None:
        preemptions = [record.get("num_preempted") for record in records if record.get("num_preempted") is not None]
        if preemptions:
            num_preempted = float(sum(float(value) for value in preemptions))

    return InferenceServerProfile(
        backend_name=inventory.backend_name,
        backend_version=inventory.backend_version,
        metric_source="prometheus" if raw_prometheus_text else "client_side_estimate",
        inference_server_queue_wait_seconds_p50=_percentile(queue_values, 50),
        inference_server_queue_wait_seconds_p95=_percentile(queue_values, 95),
        prefill_seconds_p50=_percentile(prefill_values, 50),
        prefill_seconds_p95=_percentile(prefill_values, 95),
        decode_seconds_p50=_percentile(decode_values, 50),
        decode_seconds_p95=_percentile(decode_values, 95),
        prefix_cache_hit_rate=prefix_cache_hit_rate,
        kv_cache_eviction_count=kv_cache_eviction_count,
        num_preempted=num_preempted,
        tokens_per_second=tokens_per_second,
        gpu_utilization_p50=_percentile(gpu_values, 50),
        gpu_utilization_p95=_percentile(gpu_values, 95),
        batched_token_count_p50=_percentile(batched_values, 50),
        batched_token_count_p95=_percentile(batched_values, 95),
        unsupported_diagnostics=unsupported,
        metric_name_mapping=dict(mapping),
    )


def _parse_prometheus_text(text: str) -> dict[str, list[float]]:
    metrics: dict[str, list[float]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        raw_name = parts[0].split("{", 1)[0]
        try:
            value = float(parts[1])
        except ValueError:
            continue
        metrics.setdefault(raw_name, []).append(value)
    return metrics


def _candidate_metric_names(canonical: str, metrics: Mapping[str, list[float]]) -> list[str]:
    keyword_sets = {
        "inference_server_queue_wait_seconds": ("queue", "wait", "pending", "waiting"),
        "prefill_seconds": ("prefill", "ttft", "time_to_first_token"),
        "decode_seconds": ("decode", "inter_token", "tpot"),
        "prefix_cache_hit_rate": ("prefix_cache", "radix_cache", "cache_hit"),
        "kv_cache_eviction_count": ("kv_cache", "evict", "eviction"),
        "num_preempted": ("preempt", "preempted"),
        "tokens_per_second": ("tokens_per_second", "token_throughput", "generation_throughput"),
        "gpu_utilization": ("gpu_utilization", "gpu_util", "dcgm"),
        "batched_token_count": ("batched_token", "running_token", "num_batched_tokens"),
    }
    keywords = keyword_sets[canonical]
    matches = []
    for name in metrics:
        lower = name.lower()
        if any(keyword in lower for keyword in keywords):
            matches.append(name)
    return sorted(matches)


def _unsupported_diagnostic(canonical: str) -> str:
    return {
        "inference_server_queue_wait_seconds": "server_queue_wait_metric_unavailable",
        "prefill_seconds": "prefill_metric_unavailable",
        "decode_seconds": "decode_metric_unavailable",
        "prefix_cache_hit_rate": "prefix_cache_hit_rate_unavailable",
        "kv_cache_eviction_count": "kv_cache_eviction_metric_unavailable",
        "num_preempted": "num_preempted_metric_unavailable",
        "tokens_per_second": "tokens_per_second_backend_metric_unavailable",
        "gpu_utilization": "gpu_utilization_metric_unavailable",
        "batched_token_count": "batched_token_count_metric_unavailable",
    }[canonical]


def _values_for(metric_name: str | None, metrics: Mapping[str, list[float]]) -> list[float]:
    if metric_name is None:
        return []
    return list(metrics.get(metric_name, []))


def _last_value(metric_name: str | None, metrics: Mapping[str, list[float]]) -> float | None:
    values = _values_for(metric_name, metrics)
    return values[-1] if values else None


def _prefix_cache_hit_rate(metric_name: str | None, metrics: Mapping[str, list[float]]) -> float | None:
    if metric_name is not None:
        values = metrics.get(metric_name, [])
        if values:
            value = values[-1]
            if 0.0 <= value <= 1.0:
                return value
    hit = sum(value for name, values in metrics.items() if "cache_hit" in name.lower() for value in values)
    miss = sum(value for name, values in metrics.items() if "cache_miss" in name.lower() for value in values)
    if hit + miss <= 0:
        return None
    return hit / (hit + miss)


def _client_side_tokens_per_second(records: Sequence[Mapping[str, Any]]) -> float | None:
    token_count = 0
    seconds = 0.0
    for record in records:
        output_tokens = record.get("output_token_count")
        if output_tokens is None and isinstance(record.get("output_token_ids"), list):
            output_tokens = len(record["output_token_ids"])
        duration_ms = record.get("duration_ms")
        if output_tokens is not None:
            token_count += int(output_tokens)
        if duration_ms is not None:
            seconds += float(duration_ms) / 1000.0
    if token_count <= 0 or seconds <= 0:
        return None
    return token_count / seconds


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
