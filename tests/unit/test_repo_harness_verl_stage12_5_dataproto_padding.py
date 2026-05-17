from __future__ import annotations

from types import SimpleNamespace

from repo_harness_verl import build_dataproto_padding_profile


def test_stage12_5_dataproto_padding_profile_measures_effective_token_utilization() -> None:
    data_proto = SimpleNamespace(
        batch={
            "prompts": [[11, 12, 0, 0], [21, 22, 23, 0]],
            "responses": [[31, 32, 0], [41, 0, 0]],
            "response_mask": [[1, 1, 0], [1, 0, 0]],
            "attention_mask": [[1, 1, 0, 0, 1, 1, 0], [1, 1, 1, 0, 1, 0, 0]],
            "loss_mask": [[0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 1, 0, 0]],
        }
    )

    profile = build_dataproto_padding_profile(data_proto, length_overflow_filtered_sample_count=2)

    assert profile.batch_size == 2
    assert profile.prompt_length == 4
    assert profile.response_length == 3
    assert profile.actual_prompt_tokens_p50 == 2.5
    assert profile.actual_response_tokens_p50 == 1.5
    assert round(profile.padded_token_ratio, 4) == round(1.0 - 8 / 14, 4)
    assert round(profile.loss_mask_token_ratio or 0.0, 4) == round(3 / 14, 4)
    assert round(profile.response_mask_zero_ratio, 4) == round(3 / 6, 4)
    assert profile.length_overflow_filtered_sample_count == 2
    assert profile.diagnostics == []


def test_stage12_5_dataproto_padding_profile_records_missing_attention_mask_diagnostic() -> None:
    data_proto = SimpleNamespace(
        batch={
            "prompts": [[11, 12, 0, 0]],
            "responses": [[31, 0]],
            "response_mask": [[1, 0]],
        }
    )

    profile = build_dataproto_padding_profile(data_proto)

    assert profile.actual_prompt_tokens_p50 == 4.0
    assert profile.diagnostics == ["attention_mask_unavailable_prompt_counts_assume_full_prompt"]
