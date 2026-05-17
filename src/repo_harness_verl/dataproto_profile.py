"""Stage 12.5 DataProto padding and token utilization profile helpers."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel


class DataProtoPaddingProfile(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_dataproto_padding_profile_v0"
    batch_size: int = Field(ge=0)
    prompt_length: int = Field(ge=0)
    response_length: int = Field(ge=0)
    actual_prompt_tokens_p50: float = Field(ge=0.0)
    actual_prompt_tokens_p95: float = Field(ge=0.0)
    actual_response_tokens_p50: float = Field(ge=0.0)
    actual_response_tokens_p95: float = Field(ge=0.0)
    padded_token_ratio: float = Field(ge=0.0, le=1.0)
    loss_mask_token_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    response_mask_zero_ratio: float = Field(ge=0.0, le=1.0)
    length_overflow_filtered_sample_count: int = Field(default=0, ge=0)
    diagnostics: list[str] = Field(default_factory=list)


def build_dataproto_padding_profile(
    data_proto: Any,
    *,
    length_overflow_filtered_sample_count: int = 0,
) -> DataProtoPaddingProfile:
    batch = getattr(data_proto, "batch", {})
    prompts = batch.get("prompts", [])
    responses = batch.get("responses", [])
    response_mask = batch.get("response_mask", [])
    attention_mask = batch.get("attention_mask")
    loss_mask = batch.get("loss_mask")

    prompt_shape = _shape(prompts)
    response_shape = _shape(responses)
    batch_size = prompt_shape[0] if prompt_shape else response_shape[0] if response_shape else 0
    prompt_length = prompt_shape[1] if len(prompt_shape) >= 2 else 0
    response_length = response_shape[1] if len(response_shape) >= 2 else 0

    prompt_counts = _prompt_token_counts(attention_mask, batch_size=batch_size, prompt_length=prompt_length)
    response_counts = _row_sums(response_mask)
    total_slots = batch_size * (prompt_length + response_length)
    actual_tokens = sum(prompt_counts) + sum(response_counts)
    padded_ratio = 0.0 if total_slots <= 0 else max(0.0, min(1.0, 1.0 - actual_tokens / total_slots))
    response_slots = batch_size * response_length
    response_zero_ratio = (
        0.0
        if response_slots <= 0
        else max(0.0, min(1.0, 1.0 - (sum(response_counts) / response_slots)))
    )
    loss_ratio = None
    if loss_mask is not None:
        loss_values = _flatten_numeric(loss_mask)
        loss_ratio = None if not loss_values else sum(loss_values) / len(loss_values)

    diagnostics = []
    if attention_mask is None:
        diagnostics.append("attention_mask_unavailable_prompt_counts_assume_full_prompt")

    return DataProtoPaddingProfile(
        batch_size=batch_size,
        prompt_length=prompt_length,
        response_length=response_length,
        actual_prompt_tokens_p50=_percentile(prompt_counts, 50),
        actual_prompt_tokens_p95=_percentile(prompt_counts, 95),
        actual_response_tokens_p50=_percentile(response_counts, 50),
        actual_response_tokens_p95=_percentile(response_counts, 95),
        padded_token_ratio=padded_ratio,
        loss_mask_token_ratio=loss_ratio,
        response_mask_zero_ratio=response_zero_ratio,
        length_overflow_filtered_sample_count=length_overflow_filtered_sample_count,
        diagnostics=diagnostics,
    )


def _shape(value: Any) -> tuple[int, ...]:
    shape = getattr(value, "shape", None)
    if shape is not None:
        return tuple(int(part) for part in shape)
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            return (len(value), len(value[0]))
        return (len(value),)
    return ()


def _prompt_token_counts(attention_mask: Any, *, batch_size: int, prompt_length: int) -> list[float]:
    if batch_size <= 0:
        return []
    if attention_mask is None:
        return [float(prompt_length) for _ in range(batch_size)]
    rows = _rows(attention_mask)
    counts = []
    for row in rows[:batch_size]:
        counts.append(sum(float(value) for value in row[:prompt_length]))
    return counts


def _row_sums(value: Any) -> list[float]:
    return [sum(float(item) for item in row) for row in _rows(value)]


def _rows(value: Any) -> list[list[Any]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            return value
        return [value]
    return []


def _flatten_numeric(value: Any) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        flattened: list[float] = []
        for item in value:
            flattened.extend(_flatten_numeric(item))
        return flattened
    try:
        return [float(value)]
    except (TypeError, ValueError):
        return []


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
