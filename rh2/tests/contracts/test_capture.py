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


# ---------------------------------------------------------------------------
# S1-1b：计数-引用互检 与 failed 三联（失败原因必填、meta_info 豁免）
# ---------------------------------------------------------------------------


def valid_failed_capture() -> dict:
    """capture_status=failed 的合法形态：有失败原因，无生成事实，meta_info 可缺。"""

    payload = valid_capture_record()
    payload["capture_status"] = "failed"
    payload["capture_failure_reason"] = "request_timeout"
    payload["alignment_status"] = "not_checked"
    payload["response_token_count"] = 0
    payload["response_token_ids_ref"] = None
    payload["raw_meta_info_digest"] = None  # 请求失败，根本没拿到 meta_info
    payload["logprobs_ref"] = None
    payload["top_p_token_ids_ref"] = None
    payload["top_p_token_offsets_ref"] = None
    payload["routed_experts_ref"] = None
    return payload


def test_token_count_without_ids_ref_rejected_even_when_partial():
    """S1-1b 回归：声称生成 16 token 却无 ids 引用——partial 也不豁免（修复前可通过）。"""

    payload = valid_capture_record()
    payload["response_token_ids_ref"] = None
    payload["capture_status"] = "partial"
    payload["alignment_status"] = "mismatch"
    with pytest.raises(ValidationError, match="response_token_ids_ref 必填"):
        GenerationCaptureRecord.model_validate(payload)


def test_failed_capture_valid_shape_passes():
    record = GenerationCaptureRecord.model_validate(valid_failed_capture())
    assert record.capture_failure_reason == "request_timeout"
    assert record.raw_meta_info_ref is None and record.raw_meta_info_digest is None


def test_failed_capture_without_reason_rejected():
    """失败不可无因：capture_status=failed 时 capture_failure_reason 必填。"""

    payload = valid_failed_capture()
    payload["capture_failure_reason"] = None
    with pytest.raises(ValidationError, match="capture_failure_reason"):
        GenerationCaptureRecord.model_validate(payload)


def test_non_failed_capture_with_failure_reason_rejected():
    """互斥方向：complete 携带失败原因自相矛盾。"""

    payload = valid_capture_record()
    payload["capture_failure_reason"] = "request_timeout"
    with pytest.raises(ValidationError, match="不得携带 capture_failure_reason"):
        GenerationCaptureRecord.model_validate(payload)


def test_meta_info_exemption_only_for_failed():
    """meta_info 豁免只给 failed：partial 仍必须给 digest 或 ref 之一。"""

    payload = valid_capture_record()
    payload["capture_status"] = "partial"
    payload["alignment_status"] = "mismatch"
    payload["top_p_token_ids_ref"] = None
    payload["top_p_token_offsets_ref"] = None
    payload["raw_meta_info_digest"] = None
    with pytest.raises(ValidationError, match="raw_meta_info"):
        GenerationCaptureRecord.model_validate(payload)
