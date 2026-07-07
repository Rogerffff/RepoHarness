"""TrainingExportRecord（S1-8）fail-closed 单测：资格门 schema 层锁死 + 账目互锁。

最重要的一条：audit_only_or_rejected 在 training_eligibility_class 的 Literal 里
**不可表示**——"导出 audit 档样本"不是被 if 拦住，而是根本写不出合法记录。
"""

import pytest
from contract_samples import (
    VALID_SAMPLE_FACTORIES,
    valid_export_branch_tokens,
    valid_training_export_record,
)
from pydantic import ValidationError

from repoharness2.contracts import SCHEMA_REGISTRY, TrainingExportRecord
from repoharness2.contracts.export import ExportBranchTokens


def test_valid_record_passes_and_registered():
    record = TrainingExportRecord.model_validate(valid_training_export_record())
    assert record.schema_id == "rh2.training_export_record.v1"
    assert SCHEMA_REGISTRY["rh2.training_export_record.v1"] is TrainingExportRecord
    assert VALID_SAMPLE_FACTORIES["rh2.training_export_record.v1"] is valid_training_export_record
    # §2 挂点：导出时 offline_filter_report_ref 为空，离线过滤作业之后才回填
    assert record.offline_filter_report_ref is None


def test_audit_tier_is_unrepresentable():
    """资格门的 schema 层落点：audit 档不是被拒绝，而是不可表示。"""

    payload = valid_training_export_record()
    payload["training_eligibility_class"] = "audit_only_or_rejected"
    with pytest.raises(ValidationError, match="training_eligibility_class"):
        TrainingExportRecord.model_validate(payload)


def test_reward_scope_none_rejected():
    """infra 失败（无 reward）的样本禁止出现在训练导出面（P4 首尾呼应）。"""

    payload = valid_training_export_record()
    payload["reward_facts"] = {
        "reward_scope": "none",
        "raw_reward": None,
        "components": {},
        "reward_event_refs": [],
        "credit_assignment_strategy": "direct_trace_reward",
    }
    with pytest.raises(ValidationError, match="reward_scope=none"):
        TrainingExportRecord.model_validate(payload)


def test_grading_ref_must_be_reward_event_source():
    payload = valid_training_export_record()
    payload["grading_report_ref"] = "rpt_some_other_grading"
    with pytest.raises(ValidationError, match="reward_event_refs"):
        TrainingExportRecord.model_validate(payload)


def test_segment_count_must_match_branch_count():
    payload = valid_training_export_record()
    payload["reward_facts"]["segment_count"] = 2  # 只有 1 个导出分支
    with pytest.raises(ValidationError, match="segment_count"):
        TrainingExportRecord.model_validate(payload)


def test_loss_denominator_must_match_trainable_sum():
    payload = valid_training_export_record()
    payload["reward_facts"]["rollout_loss_denominator"] = 17  # 分支 trainable 合计 16
    with pytest.raises(ValidationError, match="rollout_loss_denominator"):
        TrainingExportRecord.model_validate(payload)


def test_duplicate_branch_ids_rejected():
    payload = valid_training_export_record()
    payload["branches"] = [valid_export_branch_tokens(), valid_export_branch_tokens()]
    payload["reward_facts"]["segment_count"] = 2
    payload["reward_facts"]["rollout_loss_denominator"] = 32
    with pytest.raises(ValidationError, match="branch_id"):
        TrainingExportRecord.model_validate(payload)


def test_offline_filter_report_ref_backfillable():
    """挂点字段可回填（离线过滤跑完后生成带引用的新记录，不改写原始记录）。"""

    payload = valid_training_export_record()
    payload["offline_filter_report_ref"] = "ofr_batch7_0001"
    record = TrainingExportRecord.model_validate(payload)
    assert record.offline_filter_report_ref == "ofr_batch7_0001"


# ---------------------------------------------------------------------------
# ExportBranchTokens：payload 引用与 token 计数互锁
# ---------------------------------------------------------------------------


def test_branch_byte_size_must_match_token_counts():
    """prompt 15 + response 16 -> token_ids 必须恰 124 字节，差 4 字节即拒。"""

    payload = valid_export_branch_tokens()
    payload["token_ids_ref"]["byte_size"] = 120
    with pytest.raises(ValidationError, match="byte_size"):
        ExportBranchTokens.model_validate(payload)


def test_branch_loss_mask_and_logprob_sizes_locked():
    bad_mask = valid_export_branch_tokens()
    bad_mask["loss_mask_ref"]["byte_size"] = 68  # 应为 4*16=64
    with pytest.raises(ValidationError, match="loss_mask_ref"):
        ExportBranchTokens.model_validate(bad_mask)
    bad_lp = valid_export_branch_tokens()
    bad_lp["rollout_logprobs_ref"]["byte_size"] = 64  # 应为 8*16=128
    with pytest.raises(ValidationError, match="rollout_logprobs_ref"):
        ExportBranchTokens.model_validate(bad_lp)


def test_branch_refs_require_digest():
    """导出面引用必须带 sha256（manifest 对账与防篡改的前提）。"""

    payload = valid_export_branch_tokens()
    payload["token_ids_ref"]["sha256"] = None
    with pytest.raises(ValidationError, match="sha256"):
        ExportBranchTokens.model_validate(payload)


def test_branch_trainable_count_bounded_by_response():
    payload = valid_export_branch_tokens()
    payload["trainable_token_count"] = 17  # response 只有 16
    with pytest.raises(ValidationError, match="trainable_token_count"):
        ExportBranchTokens.model_validate(payload)


def test_branch_requires_capture_backlink():
    """§5 条 5：token 来源必须可回链——capture_record_refs 不可为空。"""

    payload = valid_export_branch_tokens()
    payload["capture_record_refs"] = []
    with pytest.raises(ValidationError):
        ExportBranchTokens.model_validate(payload)


def test_text_only_fidelity_not_representable_in_v1():
    """v1 只定义 token_faithful；文本级导出必须先升 schema，不可静默混入。"""

    payload = valid_export_branch_tokens()
    payload["token_fidelity"] = "text_only_degraded"
    with pytest.raises(ValidationError, match="token_fidelity"):
        ExportBranchTokens.model_validate(payload)
