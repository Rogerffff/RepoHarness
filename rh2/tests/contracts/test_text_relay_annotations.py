"""文本中继显式降级标注（S1-8）的契约测试。

verifiers EvalClient 是文本一比一转发：没有 token ids、没有采样参数捕获、
没有 routing 事实。S1-8 给三处契约加了显式"未捕获"值——
SamplingMaskKind/RoutingAlignment 的 not_captured_text_relay 与
LossMaskReason 的 token_capture_unavailable_downgraded。本文件钉住它们的
fail-closed 语义：未捕获状态必须可表示（否则投影层只能伪造 top_p=1.0 /
dense 声明），但绝不允许与任何"捕获到了"的字段共存。
"""

import pytest
from contract_samples import valid_branch
from pydantic import ValidationError

from repoharness2.contracts import (
    BranchProjection,
    LossMaskSpan,
    RoutingTensorRef,
    SamplingMaskRef,
)

# ---------------------------------------------------------------------------
# SamplingMaskRef：not_captured_text_relay <=> top_p=None 且无 tape 字段
# ---------------------------------------------------------------------------


def test_not_captured_relay_sampling_mask_valid():
    ref = SamplingMaskRef(mask_kind="not_captured_text_relay", top_p=None)
    assert ref.top_p is None and ref.token_ids_ref is None


def test_not_captured_relay_rejects_fabricated_top_p():
    """采样发生在 provider 侧、参数未捕获——携带任何 top_p 数值都是伪造。"""

    with pytest.raises(ValidationError, match="top_p 为 None"):
        SamplingMaskRef(mask_kind="not_captured_text_relay", top_p=0.95)


def test_not_captured_relay_rejects_tape_fields():
    with pytest.raises(ValidationError, match="不得携带 tape 字段"):
        SamplingMaskRef(
            mask_kind="not_captured_text_relay",
            top_p=None,
            token_ids_ref={"ref_id": "smuggled_ids"},
            offsets_ref={"ref_id": "smuggled_offsets"},
        )


@pytest.mark.parametrize("kind", ["top_p_kept_token_ids", "not_applicable_top_p_1"])
def test_captured_kinds_require_numeric_top_p(kind):
    """top_p=None 只属于 not_captured_text_relay；捕获路径缺数值即拒收。"""

    with pytest.raises(ValidationError, match="top_p 数值必填"):
        SamplingMaskRef(mask_kind=kind, top_p=None)


# ---------------------------------------------------------------------------
# RoutingTensorRef：not_captured_text_relay 与 tensor 字段互斥
# ---------------------------------------------------------------------------


def test_not_captured_relay_routing_valid():
    ref = RoutingTensorRef(alignment="not_captured_text_relay")
    assert ref.tensor_ref is None


def test_not_captured_relay_routing_rejects_tensor_fields():
    with pytest.raises(ValidationError, match="不得携带 routing 张量字段"):
        RoutingTensorRef(
            alignment="not_captured_text_relay",
            tensor_ref={"ref_id": "smuggled_tape"},
        )


# ---------------------------------------------------------------------------
# LossMaskReason：token_capture_unavailable_downgraded 的两端锁
# ---------------------------------------------------------------------------


def test_relay_downgrade_reason_only_pairs_with_mask0():
    span = LossMaskSpan(start=15, end=31, mask=0, reason="token_capture_unavailable_downgraded")
    assert span.mask == 0
    with pytest.raises(ValidationError, match="sampled_assistant_trainable"):
        LossMaskSpan(start=15, end=31, mask=1, reason="token_capture_unavailable_downgraded")


def _relay_branch(reason: str) -> dict:
    """文本中继形态的分支：sampled_assistant 段 mask=0，理由由参数注入。"""

    branch = valid_branch()
    branch["loss_mask_spans"] = [{"start": 15, "end": 31, "mask": 0, "reason": reason}]
    branch["logprob_alignment_status"] = "missing"
    branch["logprob_provenance"] = None
    branch["routing"] = {"alignment": "not_captured_text_relay"}
    branch["sampling_mask"] = {"mask_kind": "not_captured_text_relay", "top_p": None}
    branch["capture_record_refs"] = []  # 无 mask=1 -> 允许无回链（schema 链自洽）
    return branch


def test_branch_accepts_relay_downgrade_on_sampled_span():
    """采样文本 + 无 token 捕获的诚实表示：source=sampled_assistant、mask=0、降级理由。"""

    branch = BranchProjection.model_validate(_relay_branch("token_capture_unavailable_downgraded"))
    assert branch.sampling_mask.mask_kind == "not_captured_text_relay"
    assert all(span.mask == 0 for span in branch.loss_mask_spans)


def test_branch_still_rejects_context_reason_on_sampled_span():
    """N-3 不放松：采样段的 mask=0 不许标成普通上下文（伪装降级事实）。"""

    with pytest.raises(ValidationError, match="降级类"):
        BranchProjection.model_validate(_relay_branch("tool_or_env_context"))
