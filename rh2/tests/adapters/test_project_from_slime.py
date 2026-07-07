"""S1-3 project_from_slime 单测：正例两组 fixture 全字段过契约校验，反例逐一拒收。

反例覆盖执行计划点名清单：routing 行数差一拒收、可训练 token 缺 capture 回链
拒收、两叶链但申报 segment_count=1 拒收、tape 请求了没返回时拒绝产出投影
（reason_code 即机器可读降级标注，对齐 capture 层 complete 禁令）。
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest
from fixtures import dense_4b, moe_30b_compaction
from fixtures.common import (
    SHA_TEMPLATE,
    b64_int32,
    capture_record_dict,
    degrade_capture_to_partial,
    routing_flat,
)

from repoharness2.adapters.slime import (
    SlimeBranchAnnotation,
    SlimeProjectionError,
    assert_renderer_class,
    decode_int32_tape,
)
from repoharness2.contracts import TrajectoryProjection


def _raises_reason(reason_code: str):
    """pytest.raises 包装：断言 SlimeProjectionError 且 reason_code 精确匹配。"""

    return pytest.raises(SlimeProjectionError, match=rf"^\[{reason_code}\]")


# ---------------------------------------------------------------------------
# 正例：fixture (a) 30B MoE + compaction 两叶链
# ---------------------------------------------------------------------------


def test_moe_fixture_projects_with_probe_shapes():
    inputs = moe_30b_compaction.build()
    projection = inputs.project()

    assert isinstance(projection, TrajectoryProjection)
    assert projection.source_framework == "slime"
    assert projection.source_object_ref == "slime_rollout_7"
    assert projection.trajectory_id == moe_30b_compaction.TRAJECTORY_ID
    assert projection.renderer_cls_name == "Qwen3Renderer"
    assert projection.tokenizer_name == "Qwen/Qwen3-30B-A3B"
    assert projection.chat_template_hash == SHA_TEMPLATE

    b0, b1 = projection.branches
    # b0 = uh_probe_result.json 原形状：15/16、offsets 17、routing [30,48,8]
    assert (b0.prompt_token_count, b0.response_token_count) == (15, 16)
    assert b0.sampling_mask.offsets_len == 17
    assert b0.sampling_mask.kept_token_count == 57
    assert b0.routing.alignment == "sglang_prompt_minus1_plus_gen"
    assert (b0.routing.num_rows, b0.routing.num_layers, b0.routing.router_topk) == (30, 48, 8)
    assert b0.capture_record_refs == ["cap_t1"]
    assert b0.lineage is None

    # b1 = compaction 续写叶链：22/27、offsets 28、routing 48 行
    assert (b1.prompt_token_count, b1.response_token_count) == (22, 27)
    assert b1.sampling_mask.offsets_len == 28
    assert b1.sampling_mask.kept_token_count == 71
    assert b1.routing.num_rows == 48
    assert b1.lineage is not None
    assert b1.lineage.compaction_kind == "context_compaction"
    assert b1.lineage.parent_branch_id == "b0"
    assert b1.capture_record_refs == ["cap_t2", "cap_t3"]


def test_moe_fixture_fanout_accounting_and_reward_facts():
    projection = moe_30b_compaction.build().project()
    facts = projection.reward_facts
    assert facts.segment_count == 2 == len(projection.branches)
    # rollout_loss_denominator = 全分支 mask=1 token 总数：16 + (12+9) = 37
    assert facts.rollout_loss_denominator == 37
    assert facts.reward_scope == "group_level"
    assert facts.raw_reward == 1.0
    assert facts.parent_rollout_id == "rollout_7"


def test_moe_fixture_h4_span_mapping():
    projection = moe_30b_compaction.build().project()
    b1 = projection.branches[1]
    spans = [(s.start, s.end, s.source_type) for s in b1.token_spans]
    assert spans == [
        (0, 22, "prompt_context"),
        (22, 34, "sampled_assistant"),
        (34, 40, "tool_result"),
        (40, 49, "sampled_assistant"),
    ]
    mask_spans = [(s.start, s.end, s.mask, s.reason) for s in b1.loss_mask_spans]
    assert mask_spans == [
        (22, 34, 1, "sampled_assistant_trainable"),
        (34, 40, 0, "tool_or_env_context"),
        (40, 49, 1, "sampled_assistant_trainable"),
    ]


def test_moe_fixture_logprob_provenance_from_capture_and_kwargs():
    projection = moe_30b_compaction.build().project()
    for branch in projection.branches:
        assert branch.logprob_alignment_status == "aligned_per_token"
        provenance = branch.logprob_provenance
        assert provenance is not None
        assert provenance.engine_name == "sglang"
        assert provenance.engine_version == "0.5.9"
        assert provenance.precision == "bfloat16"
        assert provenance.sampling_backend == "pytorch"
        assert provenance.weight_version == "default"


def test_moe_fixture_multi_turn_tape_row_conservation():
    """多轮合并 tape 行数守恒（S1-1 New-Unknown 的 fixture 级验证）。

    slime 把 sample 级 routing tape 校验为 rows = len(tokens)-1；分支级公式
    prompt-1+response 只依赖 total，因此二者恒等：22-1+27 = 49-1 = 48。
    """

    inputs = moe_30b_compaction.build()
    projection = inputs.project()
    b1 = projection.branches[1]
    sample_b = inputs.samples[1]
    assert b1.routing.num_rows == len(sample_b.tokens) - 1 == 22 - 1 + 27 == 48


def test_moe_fixture_round_trips_through_schema():
    projection = moe_30b_compaction.build().project()
    reparsed = TrajectoryProjection.model_validate(projection.model_dump(mode="json"))
    assert reparsed == projection


def test_moe_artifact_store_payloads_match_refs():
    store: dict[str, bytes] = {}
    projection = moe_30b_compaction.build().project(artifact_store=store)
    b0 = projection.branches[0]
    for ref in (b0.routing.tensor_ref, b0.sampling_mask.token_ids_ref, b0.sampling_mask.offsets_ref):
        assert ref is not None
        payload = store[ref.ref_id]
        assert ref.byte_size == len(payload)
        assert ref.sha256 == "sha256:" + hashlib.sha256(payload).hexdigest()
    # routing tape 字节数 = 30 行 x 48 层 x 8 专家 x 4 字节
    assert b0.routing.tensor_ref.byte_size == 30 * 48 * 8 * 4


def test_base64_and_decoded_list_payloads_produce_identical_refs():
    """唯一解码点等价性：base64 wire 形态与解码后 list/嵌套 list 产同一 digest。"""

    base = moe_30b_compaction.build().project()

    inputs = moe_30b_compaction.build()
    flat = routing_flat(30, 48, 8)
    nested = [
        [flat[r * 48 * 8 + layer * 8 : r * 48 * 8 + layer * 8 + 8] for layer in range(48)]
        for r in range(30)
    ]
    offsets = list(moe_30b_compaction.topp_offsets(moe_30b_compaction.KEPT_PER_TOKEN_A))
    inputs.samples[0] = dataclasses.replace(
        inputs.samples[0],
        rollout_top_p_token_ids=list(range(100000, 100057)),
        rollout_top_p_token_offsets=offsets,
        rollout_routed_experts=nested,
    )
    alt = inputs.project()
    assert alt.branches[0].routing.tensor_ref == base.branches[0].routing.tensor_ref
    assert alt.branches[0].sampling_mask.token_ids_ref == base.branches[0].sampling_mask.token_ids_ref


# ---------------------------------------------------------------------------
# 正例：fixture (b) 4B dense（无 routing，top_p=0.95 照带 tape）
# ---------------------------------------------------------------------------


def test_dense_fixture_routing_not_applicable_but_top_p_tape_present():
    projection = dense_4b.build().project()
    assert len(projection.branches) == 1
    branch = projection.branches[0]
    routing = branch.routing
    assert routing.alignment == "not_applicable_dense_model"
    assert routing.tensor_ref is None and routing.num_rows is None
    # A2：dense 只是没有 routing，top-p tape 照样在场并被消费
    assert branch.sampling_mask.mask_kind == "top_p_kept_token_ids"
    assert branch.sampling_mask.top_p == 0.95
    assert branch.sampling_mask.offsets_len == 24
    assert branch.sampling_mask.kept_token_count == 54
    assert projection.reward_facts.segment_count == 1
    assert projection.reward_facts.rollout_loss_denominator == 18


def test_dense_fixture_default_mask0_maps_to_tool_result():
    branch = dense_4b.build().project().branches[0]
    spans = [(s.start, s.end, s.source_type) for s in branch.token_spans]
    assert spans == [
        (0, 12, "prompt_context"),
        (12, 22, "sampled_assistant"),
        (22, 27, "tool_result"),
        (27, 35, "sampled_assistant"),
    ]
    assert (22, 27, 0, "tool_or_env_context") in [
        (s.start, s.end, s.mask, s.reason) for s in branch.loss_mask_spans
    ]


def test_dense_top_p_1_explicit_not_applicable_path():
    """bring-up 应急形态（top_p=1.0）：sampling mask 必须显式 not_applicable_top_p_1。"""

    inputs = dense_4b.build()
    inputs.capture_dicts = [
        capture_record_dict(
            record_id=d["record_id"],
            turn_id=d["turn_id"],
            trajectory_id=dense_4b.TRAJECTORY_ID,
            model_name=dense_4b.MODEL,
            prompt_token_count=d["prompt_token_count"],
            response_token_count=d["response_token_count"],
            top_p=1.0,
            return_top_p_token_ids=False,
            return_routed_experts=False,
            tokenizer_name=dense_4b.MODEL,
        )
        for d in inputs.capture_dicts
    ]
    inputs.samples[0] = dataclasses.replace(
        inputs.samples[0], rollout_top_p_token_ids=None, rollout_top_p_token_offsets=None
    )
    branch = inputs.project().branches[0]
    assert branch.sampling_mask.mask_kind == "not_applicable_top_p_1"
    assert branch.sampling_mask.top_p == 1.0
    assert branch.sampling_mask.token_ids_ref is None


def test_replayed_sibling_context_run_mapping():
    """兄弟叶链重放段：mask=0 + 注释 replayed_assistant_context 的显式映射（N-3 正向）。"""

    inputs = dense_4b.build()
    inputs.samples[0] = dataclasses.replace(
        inputs.samples[0],
        loss_mask=[0] * dense_4b.GEN_1 + [0] * dense_4b.TOOL + [1] * dense_4b.GEN_2,
        rollout_log_probs=[0.0] * (dense_4b.GEN_1 + dense_4b.TOOL)
        + [-(i + 1) * 0.075 for i in range(dense_4b.GEN_2)],
    )
    inputs.annotations = [
        SlimeBranchAnnotation(
            branch_id="b0",
            capture_record_ids=["cap_d1", "cap_d2"],
            context_runs=[{"start": 12, "end": 22, "kind": "replayed_assistant_context"}],
        )
    ]
    branch = inputs.project().branches[0]
    assert (12, 22, "replayed_assistant_context") in [
        (s.start, s.end, s.source_type) for s in branch.token_spans
    ]
    assert (12, 22, 0, "replayed_sibling_response") in [
        (s.start, s.end, s.mask, s.reason) for s in branch.loss_mask_spans
    ]
    assert inputs.project().reward_facts.rollout_loss_denominator == dense_4b.GEN_2


# ---------------------------------------------------------------------------
# 反例：执行计划点名清单
# ---------------------------------------------------------------------------


def test_routing_rows_off_by_one_rejected_not_repaired():
    """routing 行数差一必须报错（29 或 31 行 vs 期望 30 行），绝不静默修正。"""

    for rows in (29, 31):
        inputs = moe_30b_compaction.build()
        inputs.samples[0] = dataclasses.replace(
            inputs.samples[0],
            rollout_routed_experts=b64_int32(routing_flat(rows, 48, 8)),
        )
        with _raises_reason("routing_rows_mismatch") as exc_info:
            inputs.project()
        assert "期望 30 行" in str(exc_info.value)
        assert f"实际 {rows} 行" in str(exc_info.value)


def test_trainable_tokens_without_capture_backlink_rejected():
    inputs = moe_30b_compaction.build()
    inputs.annotations = [
        SlimeBranchAnnotation(branch_id="b0", capture_record_ids=[]),
        inputs.annotations[1],
    ]
    with _raises_reason("capture_backlink_missing"):
        inputs.project()


def test_unknown_capture_record_ref_rejected():
    inputs = moe_30b_compaction.build()
    inputs.annotations = [
        SlimeBranchAnnotation(branch_id="b0", capture_record_ids=["cap_nonexistent"]),
        inputs.annotations[1],
    ]
    with _raises_reason("capture_record_unknown"):
        inputs.project()


def test_two_leaf_chains_but_declared_segment_count_one_rejected():
    inputs = moe_30b_compaction.build()
    with _raises_reason("segment_count_mismatch"):
        inputs.project(declared_segment_count=1)
    # 申报对了（=2）就照常通过
    assert inputs.project(declared_segment_count=2).reward_facts.segment_count == 2


def test_top_p_tape_requested_but_missing_rejected():
    """请求了 top-p tape 但 Sample 没带：投影拒绝产出（对齐 capture 层 complete 禁令）。"""

    inputs = moe_30b_compaction.build()
    inputs.capture_dicts[0] = degrade_capture_to_partial(inputs.capture_dicts[0])
    inputs.samples[0] = dataclasses.replace(
        inputs.samples[0], rollout_top_p_token_ids=None, rollout_top_p_token_offsets=None
    )
    with _raises_reason("top_p_tape_requested_but_missing") as exc_info:
        inputs.project()
    assert exc_info.value.reason_code == "top_p_tape_requested_but_missing"


def test_routing_tape_requested_but_missing_rejected():
    inputs = moe_30b_compaction.build()
    inputs.samples[0] = dataclasses.replace(inputs.samples[0], rollout_routed_experts=None)
    with _raises_reason("routing_tape_requested_but_missing"):
        inputs.project()


def test_partial_capture_record_cannot_back_trainable_branch():
    """tape 都在，但回链的 capture 记录是 partial：同样拒收（complete 禁令的兜底面）。"""

    inputs = moe_30b_compaction.build()
    inputs.capture_dicts[0] = degrade_capture_to_partial(
        inputs.capture_dicts[0], drop_top_p_tape=False
    )
    with _raises_reason("capture_record_not_complete"):
        inputs.project()


def test_top_p_offsets_length_off_by_one_rejected():
    inputs = moe_30b_compaction.build()
    offsets = moe_30b_compaction.topp_offsets(moe_30b_compaction.KEPT_PER_TOKEN_A)
    inputs.samples[0] = dataclasses.replace(
        inputs.samples[0], rollout_top_p_token_offsets=offsets + [offsets[-1]]  # 长 18
    )
    with _raises_reason("top_p_offsets_length_mismatch"):
        inputs.project()


def test_top_p_ids_offsets_sum_mismatch_rejected():
    inputs = moe_30b_compaction.build()
    offsets = moe_30b_compaction.topp_offsets(moe_30b_compaction.KEPT_PER_TOKEN_A)
    offsets[-1] = 56  # ids 共 57 个，账目对不上
    inputs.samples[0] = dataclasses.replace(inputs.samples[0], rollout_top_p_token_offsets=offsets)
    with _raises_reason("top_p_ids_offsets_mismatch"):
        inputs.project()


def test_zero_width_top_p_span_on_trainable_token_rejected():
    """零宽核集合只许出现在 mask=0 的 pad 位；mask=1 采样 token 上零宽即拒收。"""

    inputs = moe_30b_compaction.build()
    offsets = moe_30b_compaction.topp_offsets(moe_30b_compaction.KEPT_PER_TOKEN_A)
    offsets[1] = 0  # 第 0 个 token（mask=1）核集合变零宽
    inputs.samples[0] = dataclasses.replace(inputs.samples[0], rollout_top_p_token_offsets=offsets)
    with _raises_reason("top_p_empty_span_for_trainable_token"):
        inputs.project()


def test_unexpected_top_p_tape_at_top_p_1_rejected():
    inputs = dense_4b.build()
    inputs.capture_dicts = [
        capture_record_dict(
            record_id=d["record_id"],
            turn_id=d["turn_id"],
            trajectory_id=dense_4b.TRAJECTORY_ID,
            model_name=dense_4b.MODEL,
            prompt_token_count=d["prompt_token_count"],
            response_token_count=d["response_token_count"],
            top_p=1.0,
            return_top_p_token_ids=False,
            return_routed_experts=False,
            tokenizer_name=dense_4b.MODEL,
        )
        for d in inputs.capture_dicts
    ]
    with _raises_reason("unexpected_top_p_tape"):
        inputs.project()  # sample 仍带 tape，与 top_p=1.0 矛盾


def test_context_run_covering_trainable_token_rejected():
    inputs = dense_4b.build()
    inputs.annotations = [
        SlimeBranchAnnotation(
            branch_id="b0",
            capture_record_ids=["cap_d1", "cap_d2"],
            context_runs=[{"start": 12, "end": 14, "kind": "tool_result"}],  # [12,14) 是 mask=1
        )
    ]
    with _raises_reason("context_run_covers_trainable_token"):
        inputs.project()


def test_loss_mask_length_mismatch_rejected():
    inputs = dense_4b.build()
    inputs.samples[0] = dataclasses.replace(inputs.samples[0], loss_mask=[1] * 22)
    with _raises_reason("loss_mask_length_mismatch"):
        inputs.project()


def test_mixed_rollout_ids_rejected():
    inputs = moe_30b_compaction.build()
    inputs.samples[1] = dataclasses.replace(inputs.samples[1], rollout_id=8)
    with _raises_reason("mixed_rollout_ids"):
        inputs.project()


def test_aborted_sample_rejected():
    inputs = dense_4b.build()
    inputs.samples[0] = dataclasses.replace(inputs.samples[0], status="aborted")
    with _raises_reason("sample_status_not_projectable"):
        inputs.project()


# ---------------------------------------------------------------------------
# U-G renderer 守门
# ---------------------------------------------------------------------------


def test_assert_renderer_class_accepts_matching_instance_and_name():
    qwen3_renderer = type("Qwen3Renderer", (), {})()
    assert assert_renderer_class(qwen3_renderer, "Qwen3Renderer") == "Qwen3Renderer"
    assert assert_renderer_class("Qwen3Renderer", "Qwen3Renderer") == "Qwen3Renderer"


def test_assert_renderer_class_catches_silent_default_renderer_downgrade():
    default_renderer = type("DefaultRenderer", (), {})()
    with _raises_reason("renderer_class_mismatch") as exc_info:
        assert_renderer_class(default_renderer, "Qwen3Renderer")
    assert "DefaultRenderer" in str(exc_info.value)
    assert "Qwen3Renderer" in str(exc_info.value)


def test_projection_level_renderer_expectation_guard():
    inputs = moe_30b_compaction.build()
    ok = inputs.project(expected_renderer_cls_name="Qwen3Renderer")
    assert ok.renderer_cls_name == "Qwen3Renderer"
    with _raises_reason("renderer_class_mismatch"):
        inputs.project(expected_renderer_cls_name="Qwen25Renderer")


# ---------------------------------------------------------------------------
# 解码器细部
# ---------------------------------------------------------------------------


def test_decode_int32_tape_forms_equivalent():
    values = [0, 1, 127, -1, 2**31 - 1]
    encoded = b64_int32(values)
    assert decode_int32_tape(encoded, field_name="t") == values
    assert decode_int32_tape(values, field_name="t") == values
    assert decode_int32_tape([[0, 1], [127, -1], [2**31 - 1]], field_name="t") == values


def test_decode_int32_tape_rejects_bad_payloads():
    with _raises_reason("tape_base64_invalid"):
        decode_int32_tape("!!!not-base64!!!", field_name="t")
    with _raises_reason("tape_bytes_not_int32"):
        decode_int32_tape(b"\x01\x02\x03", field_name="t")
    with _raises_reason("tape_element_not_int"):
        decode_int32_tape([1, "x"], field_name="t")
    with _raises_reason("tape_payload_missing"):
        decode_int32_tape(None, field_name="t")
