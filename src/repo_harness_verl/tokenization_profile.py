"""Stage 12.5 tokenization and prompt build profile helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel


class TokenizationProfile(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage12_5_tokenization_profile_v0"
    sample_count: int = Field(ge=0)
    prompt_build_seconds_p50: float | None = Field(default=None, ge=0.0)
    prompt_build_seconds_p95: float | None = Field(default=None, ge=0.0)
    chat_template_seconds_p50: float | None = Field(default=None, ge=0.0)
    chat_template_seconds_p95: float | None = Field(default=None, ge=0.0)
    tokenize_seconds_p50: float | None = Field(default=None, ge=0.0)
    tokenize_seconds_p95: float | None = Field(default=None, ge=0.0)
    prompt_tokens_p50: float | None = Field(default=None, ge=0.0)
    prompt_tokens_p95: float | None = Field(default=None, ge=0.0)
    stable_prefix_cache_candidate_count: int = Field(default=0, ge=0)
    diagnostics: list[str] = Field(default_factory=list)


def build_tokenization_profile(records: Sequence[Mapping[str, Any]]) -> TokenizationProfile:
    prompt_build = _seconds_values(records, "prompt_build_ms", "prompt_build_seconds")
    chat_template = _seconds_values(records, "chat_template_ms", "chat_template_seconds")
    tokenize = _seconds_values(records, "tokenize_ms", "tokenize_seconds")
    prompt_tokens = _numeric_values(records, "prompt_token_count", "prompt_tokens")
    prefix_hashes = [str(record["prompt_prefix_hash"]) for record in records if record.get("prompt_prefix_hash")]
    diagnostics = []
    if not tokenize:
        diagnostics.append("tokenize_timing_unavailable")
    if not chat_template:
        diagnostics.append("chat_template_timing_unavailable")
    return TokenizationProfile(
        sample_count=len(records),
        prompt_build_seconds_p50=_percentile(prompt_build, 50),
        prompt_build_seconds_p95=_percentile(prompt_build, 95),
        chat_template_seconds_p50=_percentile(chat_template, 50),
        chat_template_seconds_p95=_percentile(chat_template, 95),
        tokenize_seconds_p50=_percentile(tokenize, 50),
        tokenize_seconds_p95=_percentile(tokenize, 95),
        prompt_tokens_p50=_percentile(prompt_tokens, 50),
        prompt_tokens_p95=_percentile(prompt_tokens, 95),
        stable_prefix_cache_candidate_count=len(prefix_hashes) - len(set(prefix_hashes)),
        diagnostics=diagnostics,
    )


def _seconds_values(records: Sequence[Mapping[str, Any]], ms_key: str, seconds_key: str) -> list[float]:
    values: list[float] = []
    for record in records:
        if isinstance(record.get(ms_key), int | float):
            values.append(max(0.0, float(record[ms_key]) / 1000.0))
        elif isinstance(record.get(seconds_key), int | float):
            values.append(max(0.0, float(record[seconds_key])))
    return values


def _numeric_values(records: Sequence[Mapping[str, Any]], *keys: str) -> list[float]:
    values: list[float] = []
    for record in records:
        for key in keys:
            value = record.get(key)
            if isinstance(value, int | float):
                values.append(max(0.0, float(value)))
                break
    return values


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
