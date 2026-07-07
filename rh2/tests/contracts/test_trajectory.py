"""trajectory.py 的 fail-closed 单测：投影层关键非法组合逐一拒收。

覆盖执行计划点名的非法样例："routing alignment 缺失但 tensor 存在"，
以及 tape 形状、loss mask 语义（H4）、reward 组信号（§16.11）等。
S1-1b 追加：R5（raw_reward NaN/inf）、R6（segment_count 与 branches 互检）、
N-3（mask=0 reason 与 source_type 互检）、N-4（kept_token_count 下界）。
"""

import pytest
from contract_samples import (
    valid_branch,
    valid_reward_facts,
    valid_routing,
    valid_sampling_mask,
    valid_trajectory_projection,
)
from pydantic import ValidationError

from repoharness2.contracts import (
    BranchProjection,
    CompactedSubTraceLineage,
    LossMaskSpan,
    RewardFacts,
    RoutingTensorRef,
    SamplingMaskRef,
    TrajectoryProjection,
)

# ---------------------------------------------------------------------------
# RoutingTensorRef：对齐约定必须显式且行数精确
# ---------------------------------------------------------------------------


def test_routing_tensor_without_alignment_rejected():
    """点名非法样例：tensor 在场但 alignment 缺失 -> 必填字段缺失直接拒收。"""

    payload = valid_routing()
    del payload["alignment"]
    with pytest.raises(ValidationError, match="alignment"):
        RoutingTensorRef.model_validate(payload)


def test_dense_declaration_with_tensor_rejected():
    payload = valid_routing()
    payload["alignment"] = "not_applicable_dense_model"
    with pytest.raises(ValidationError, match="not_applicable_dense_model"):
        RoutingTensorRef.model_validate(payload)


def test_dense_declaration_without_tensor_passes():
    ref = RoutingTensorRef.model_validate({"alignment": "not_applicable_dense_model"})
    assert ref.tensor_ref is None


def test_sglang_row_convention_enforced():
    """SGLang 行数 = prompt-1+gen（15-1+16=30）；vLLM 的 31 行必须被拒。"""

    payload = valid_routing()
    payload["num_rows"] = 31  # prompt+gen，vLLM 约定，对 SGLang 是错的
    with pytest.raises(ValidationError, match="期望 30 行"):
        RoutingTensorRef.model_validate(payload)


def test_vllm_row_convention_enforced():
    payload = valid_routing()
    payload["alignment"] = "vllm_prompt_plus_gen"
    payload["prompt_token_count"] = 13
    payload["generated_token_count"] = 8
    payload["num_rows"] = 21  # S0-5 探针实测：13+8=21
    assert RoutingTensorRef.model_validate(payload).num_rows == 21
    payload["num_rows"] = 20  # SGLang 公式的值，对 vLLM 是错的
    with pytest.raises(ValidationError, match="期望 21 行"):
        RoutingTensorRef.model_validate(payload)


def test_engine_alignment_missing_tensor_fields_rejected():
    payload = valid_routing()
    payload["tensor_ref"] = None
    with pytest.raises(ValidationError, match="缺失"):
        RoutingTensorRef.model_validate(payload)


# ---------------------------------------------------------------------------
# SamplingMaskRef：top-p tape 与 top_p 值互锁
# ---------------------------------------------------------------------------


def test_top_p_below_one_without_tape_rejected():
    """E2 硬依赖：top_p=0.95 缺 tape（stock SGLang 静默降级形态）不可表示。"""

    payload = valid_sampling_mask()
    payload["token_ids_ref"] = None
    payload["offsets_ref"] = None
    with pytest.raises(ValidationError, match="缺失"):
        SamplingMaskRef.model_validate(payload)


def test_offsets_length_must_be_response_plus_one():
    payload = valid_sampling_mask()
    payload["offsets_len"] = 16  # 生成 16 token 时应为 17
    with pytest.raises(ValidationError, match="response_token_count \\+ 1"):
        SamplingMaskRef.model_validate(payload)


def test_not_applicable_requires_top_p_exactly_one():
    payload = {"mask_kind": "not_applicable_top_p_1", "top_p": 0.95}
    with pytest.raises(ValidationError, match="恰为 1.0"):
        SamplingMaskRef.model_validate(payload)


def test_top_p_one_with_kept_kind_rejected():
    payload = valid_sampling_mask()
    payload["top_p"] = 1.0
    with pytest.raises(ValidationError, match="top_p < 1.0"):
        SamplingMaskRef.model_validate(payload)


def test_n4_kept_token_count_below_response_count_rejected():
    """N-4：每个 response token 的核集合至少 1 个 -> kept 总数不可能低于 token 数。"""

    payload = valid_sampling_mask()
    payload["kept_token_count"] = 10  # 16 个 response token 至少保留 16
    with pytest.raises(ValidationError, match="kept_token_count"):
        SamplingMaskRef.model_validate(payload)


def test_n4_kept_token_count_exact_lower_bound_passes():
    """下界取等合法：每 token 核集合恰好 1 个（top_p 截断极限形态）。"""

    payload = valid_sampling_mask()
    payload["kept_token_count"] = 16
    assert SamplingMaskRef.model_validate(payload).kept_token_count == 16


# ---------------------------------------------------------------------------
# LossMaskSpan / BranchProjection：H4 语义
# ---------------------------------------------------------------------------


def test_mask_one_with_context_reason_rejected():
    with pytest.raises(ValidationError, match="sampled_assistant_trainable"):
        LossMaskSpan.model_validate(
            {"start": 15, "end": 31, "mask": 1, "reason": "tool_or_env_context"}
        )


def test_mask_zero_with_trainable_reason_rejected():
    with pytest.raises(ValidationError, match="矛盾"):
        LossMaskSpan.model_validate(
            {"start": 15, "end": 31, "mask": 0, "reason": "sampled_assistant_trainable"}
        )


def test_token_spans_with_gap_rejected():
    payload = valid_branch()
    payload["token_spans"] = [
        {"start": 0, "end": 14, "source_type": "prompt_context"},  # 缺 [14,15)
        {"start": 15, "end": 31, "source_type": "sampled_assistant"},
    ]
    with pytest.raises(ValidationError, match="无缝平铺"):
        BranchProjection.model_validate(payload)


def test_loss_mask_spans_must_cover_response_exactly():
    payload = valid_branch()
    payload["loss_mask_spans"] = [
        {"start": 15, "end": 30, "mask": 1, "reason": "sampled_assistant_trainable"},
    ]  # 少 [30,31)
    with pytest.raises(ValidationError, match="覆盖不完整"):
        BranchProjection.model_validate(payload)


def test_trainable_span_outside_sampled_region_rejected():
    """mask=1 落在 tool_result 区间上：H4 的核心拒收路径。"""

    payload = valid_branch()
    payload["token_spans"] = [
        {"start": 0, "end": 15, "source_type": "prompt_context"},
        {"start": 15, "end": 23, "source_type": "sampled_assistant"},
        {"start": 23, "end": 31, "source_type": "tool_result"},
    ]
    payload["loss_mask_spans"] = [
        {"start": 15, "end": 31, "mask": 1, "reason": "sampled_assistant_trainable"},
    ]
    with pytest.raises(ValidationError, match="sampled_assistant"):
        BranchProjection.model_validate(payload)


def test_trainable_tokens_require_capture_refs():
    payload = valid_branch()
    payload["capture_record_refs"] = []
    with pytest.raises(ValidationError, match="capture_record_refs"):
        BranchProjection.model_validate(payload)


def test_n3_mask_zero_context_reason_on_sampled_source_rejected():
    """N-3：sampled_assistant 源上的 mask=0 不得标 prompt_context 类理由——
    采样 token 不参训必须留下降级理由，标成普通上下文等于抹掉降级事实。"""

    payload = valid_branch()
    payload["loss_mask_spans"] = [
        {"start": 15, "end": 23, "mask": 1, "reason": "sampled_assistant_trainable"},
        {"start": 23, "end": 31, "mask": 0, "reason": "tool_or_env_context"},  # [23,31) 实为采样段
    ]
    with pytest.raises(ValidationError, match="降级类"):
        BranchProjection.model_validate(payload)


def test_n3_mask_zero_downgrade_reason_on_sampled_source_passes():
    """同一形状换成降级理由即合法：漂移降级是采样段 mask=0 的正当故事。"""

    payload = valid_branch()
    payload["loss_mask_spans"] = [
        {"start": 15, "end": 23, "mask": 1, "reason": "sampled_assistant_trainable"},
        {"start": 23, "end": 31, "mask": 0, "reason": "retokenization_drift_downgraded"},
    ]
    branch = BranchProjection.model_validate(payload)
    assert branch.loss_mask_spans[1].reason == "retokenization_drift_downgraded"


def test_n3_mask_zero_context_reason_on_tool_source_still_valid():
    """反向对照：真在 tool_result 源上的 mask=0 标 tool_or_env_context 不受影响。"""

    payload = valid_branch()
    payload["token_spans"] = [
        {"start": 0, "end": 15, "source_type": "prompt_context"},
        {"start": 15, "end": 23, "source_type": "sampled_assistant"},
        {"start": 23, "end": 31, "source_type": "tool_result"},
    ]
    payload["loss_mask_spans"] = [
        {"start": 15, "end": 23, "mask": 1, "reason": "sampled_assistant_trainable"},
        {"start": 23, "end": 31, "mask": 0, "reason": "tool_or_env_context"},
    ]
    branch = BranchProjection.model_validate(payload)
    assert branch.loss_mask_spans[1].mask == 0


def test_aligned_logprob_requires_provenance():
    payload = valid_branch()
    payload["logprob_provenance"] = None
    with pytest.raises(ValidationError, match="logprob_provenance"):
        BranchProjection.model_validate(payload)


def test_branch_and_routing_token_counts_cross_checked():
    payload = valid_branch()
    payload["routing"]["prompt_token_count"] = 14
    payload["routing"]["num_rows"] = 29  # 14-1+16，公式自洽但与分支 15 不符
    with pytest.raises(ValidationError, match="prompt_token_count"):
        BranchProjection.model_validate(payload)


def test_branch_and_sampling_mask_counts_cross_checked():
    payload = valid_branch()
    payload["sampling_mask"]["response_token_count"] = 15
    payload["sampling_mask"]["offsets_len"] = 16  # tape 自洽但与分支 16 不符
    with pytest.raises(ValidationError, match="response_token_count"):
        BranchProjection.model_validate(payload)


# ---------------------------------------------------------------------------
# CompactedSubTraceLineage / RewardFacts / TrajectoryProjection
# ---------------------------------------------------------------------------


def test_lineage_replay_prefix_must_be_masked():
    with pytest.raises(ValidationError, match="replay_prefix_loss_masked"):
        CompactedSubTraceLineage.model_validate(
            {
                "parent_trajectory_id": "traj_0001",
                "parent_branch_id": "b0",
                "compaction_event_id": "compact_1",
                "fork_point_token_index": 20,
                "compaction_kind": "context_compaction",
                "replay_prefix_loss_masked": False,
            }
        )


def test_group_reward_without_denominator_rejected():
    payload = valid_reward_facts()
    payload["rollout_loss_denominator"] = None
    with pytest.raises(ValidationError, match="rollout_loss_denominator"):
        RewardFacts.model_validate(payload)


def test_scope_none_with_zero_reward_rejected():
    """infra 场景的 RewardFacts：scope=none 时禁止携带 0.0（防伪装负样本）。"""

    payload = {
        "reward_scope": "none",
        "raw_reward": 0.0,
        "credit_assignment_strategy": "debug_only_no_policy_loss",
    }
    with pytest.raises(ValidationError, match="raw_reward 必须为 None"):
        RewardFacts.model_validate(payload)


def test_trace_level_reward_requires_event_refs():
    payload = {
        "reward_scope": "trace_level",
        "raw_reward": 0.0,
        "reward_event_refs": [],
        "credit_assignment_strategy": "direct_trace_reward",
    }
    with pytest.raises(ValidationError, match="reward_event_refs"):
        RewardFacts.model_validate(payload)


def test_r5_raw_reward_nan_rejected():
    """R5：raw_reward=NaN 会穿过所有数值比较校验，基类 allow_inf_nan=False 必须拦。"""

    payload = valid_reward_facts()
    payload["raw_reward"] = float("nan")
    with pytest.raises(ValidationError):
        RewardFacts.model_validate(payload)


def test_r5_raw_reward_inf_rejected():
    payload = valid_reward_facts()
    payload["raw_reward"] = float("inf")
    with pytest.raises(ValidationError):
        RewardFacts.model_validate(payload)


def test_duplicate_branch_ids_rejected():
    payload = valid_trajectory_projection()
    payload["branches"] = [valid_branch(), valid_branch()]  # 两个 b0
    with pytest.raises(ValidationError, match="唯一"):
        TrajectoryProjection.model_validate(payload)


# ---------------------------------------------------------------------------
# fan-out 建模定案（S1-1b）：单投影多 branches 为权威，segment_count 互检
# ---------------------------------------------------------------------------


def _two_branch_projection() -> dict:
    """两分支投影底座：compaction fan-out 的两个分段作为同一投影的 branches。"""

    payload = valid_trajectory_projection()
    second = valid_branch()
    second["branch_id"] = "b1"
    payload["branches"] = [valid_branch(), second]
    return payload


def test_r6_segment_count_mismatch_with_branches_rejected():
    """R6：branches=2 却申报 segment_count=5——fan-out 账目对不上必须拒收。"""

    payload = _two_branch_projection()
    payload["reward_facts"]["segment_count"] = 5
    with pytest.raises(ValidationError, match="segment_count"):
        TrajectoryProjection.model_validate(payload)


def test_fanout_two_branches_with_matching_segment_count_passes():
    """正例：一个 rollout 拆两段 -> 单投影 2 branches + segment_count=2。"""

    payload = _two_branch_projection()
    payload["reward_facts"]["segment_count"] = 2
    projection = TrajectoryProjection.model_validate(payload)
    assert len(projection.branches) == projection.reward_facts.segment_count == 2


def test_multi_branch_without_segment_count_rejected():
    """多分支投影不申报 segment_count：fan-out 账目缺失，防重复放大无从核对。"""

    payload = _two_branch_projection()
    payload["reward_facts"] = {
        "reward_scope": "trace_level",
        "raw_reward": 1.0,
        "reward_event_refs": ["rpt_grading_0001"],
        "credit_assignment_strategy": "direct_trace_reward",
    }
    with pytest.raises(ValidationError, match="segment_count"):
        TrajectoryProjection.model_validate(payload)


def test_single_branch_without_segment_count_passes():
    """单分支 + 不申报 segment_count 合法：无 fan-out 时隐含分段数为 1。"""

    payload = valid_trajectory_projection()
    payload["reward_facts"] = {
        "reward_scope": "trace_level",
        "raw_reward": 1.0,
        "reward_event_refs": ["rpt_grading_0001"],
        "credit_assignment_strategy": "direct_trace_reward",
    }
    projection = TrajectoryProjection.model_validate(payload)
    assert projection.reward_facts.segment_count is None


def test_naive_datetime_rejected():
    """created_at_utc 必须带时区（AwareDatetime）：无时区时间戳无法核对时间线。"""

    payload = valid_trajectory_projection()
    payload["created_at_utc"] = "2026-07-07T09:30:25"  # 无时区
    with pytest.raises(ValidationError):
        TrajectoryProjection.model_validate(payload)


def test_nested_unknown_field_rejected():
    """extra=forbid 必须递归生效：往嵌套的 routing 里塞未知字段同样拒收。"""

    payload = valid_trajectory_projection()
    payload["branches"][0]["routing"]["smuggled"] = 1
    with pytest.raises(ValidationError, match="smuggled"):
        TrajectoryProjection.model_validate(payload)
