"""capture.py 的 fail-closed 单测：GenerationCaptureRecord（A4）关键非法组合。"""

import pytest
from contract_samples import valid_capture_record
from pydantic import ValidationError

from repoharness2.contracts import GenerationCaptureRecord


def test_top_p_ids_without_offsets_rejected():
    payload = valid_capture_record()
    payload["top_p_token_offsets_ref"] = None
    with pytest.raises(ValidationError, match="成对"):
        GenerationCaptureRecord.model_validate(payload)


def test_complete_capture_missing_logprobs_rejected():
    payload = valid_capture_record()
    payload["logprobs_ref"] = None
    with pytest.raises(ValidationError, match="logprobs_ref"):
        GenerationCaptureRecord.model_validate(payload)


def test_silent_top_p_downgrade_cannot_claim_complete():
    """U-H 回归点：请求了 top-p tape 但响应没带 -> 禁止自称 complete。"""

    payload = valid_capture_record()
    payload["top_p_token_ids_ref"] = None
    payload["top_p_token_offsets_ref"] = None
    with pytest.raises(ValidationError, match="静默忽略"):
        GenerationCaptureRecord.model_validate(payload)


def test_silent_routing_downgrade_cannot_claim_complete():
    payload = valid_capture_record()
    payload["routed_experts_ref"] = None
    with pytest.raises(ValidationError, match="routed_experts_ref"):
        GenerationCaptureRecord.model_validate(payload)


def test_partial_capture_with_missing_tape_is_representable():
    """同样的缺 tape 事实，如实标 partial + mismatch 则合法（事实要可记录）。"""

    payload = valid_capture_record()
    payload["top_p_token_ids_ref"] = None
    payload["top_p_token_offsets_ref"] = None
    payload["routed_experts_ref"] = None
    payload["capture_status"] = "partial"
    payload["alignment_status"] = "mismatch"
    record = GenerationCaptureRecord.model_validate(payload)
    assert record.capture_status == "partial"


def test_complete_requires_aligned_status():
    payload = valid_capture_record()
    payload["alignment_status"] = "not_checked"
    with pytest.raises(ValidationError, match="aligned"):
        GenerationCaptureRecord.model_validate(payload)


def test_partial_cannot_claim_aligned():
    payload = valid_capture_record()
    payload["capture_status"] = "partial"
    with pytest.raises(ValidationError, match="矛盾"):
        GenerationCaptureRecord.model_validate(payload)


def test_prompt_identity_required():
    payload = valid_capture_record()
    payload["prompt_token_ids_ref"] = None
    payload["prompt_token_ids_sha256"] = None
    with pytest.raises(ValidationError, match="prompt_token_ids"):
        GenerationCaptureRecord.model_validate(payload)


def test_meta_info_identity_required():
    payload = valid_capture_record()
    payload["raw_meta_info_digest"] = None
    with pytest.raises(ValidationError, match="raw_meta_info"):
        GenerationCaptureRecord.model_validate(payload)


def test_unknown_backend_name_rejected():
    payload = valid_capture_record()
    payload["backend_name"] = "mystery_engine"
    with pytest.raises(ValidationError):
        GenerationCaptureRecord.model_validate(payload)


def test_dense_request_without_routing_is_complete():
    """dense 模型：不请求 routing（return_routed_experts=False）时无 tape 也可 complete。"""

    payload = valid_capture_record()
    payload["sampling_params"]["return_routed_experts"] = False
    payload["routed_experts_ref"] = None
    record = GenerationCaptureRecord.model_validate(payload)
    assert record.capture_status == "complete"
