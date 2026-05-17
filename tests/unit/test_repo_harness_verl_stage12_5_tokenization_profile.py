from __future__ import annotations

import pytest

from repo_harness_verl import build_tokenization_profile


def test_stage12_5_tokenization_profile_measures_prompt_build_template_and_tokenize() -> None:
    profile = build_tokenization_profile(
        [
            {
                "prompt_build_ms": 10,
                "chat_template_ms": 5,
                "tokenize_ms": 20,
                "prompt_token_count": 100,
                "prompt_prefix_hash": "stable",
            },
            {
                "prompt_build_ms": 30,
                "chat_template_ms": 15,
                "tokenize_ms": 40,
                "prompt_token_count": 200,
                "prompt_prefix_hash": "stable",
            },
        ]
    )

    assert profile.prompt_build_seconds_p50 == 0.02
    assert profile.chat_template_seconds_p95 == pytest.approx(0.0145)
    assert profile.tokenize_seconds_p50 == 0.03
    assert profile.prompt_tokens_p50 == 150.0
    assert profile.stable_prefix_cache_candidate_count == 1
    assert profile.diagnostics == []


def test_stage12_5_tokenization_profile_records_missing_timing_diagnostics() -> None:
    profile = build_tokenization_profile([{"prompt_token_count": 42}])

    assert "tokenize_timing_unavailable" in profile.diagnostics
    assert "chat_template_timing_unavailable" in profile.diagnostics
