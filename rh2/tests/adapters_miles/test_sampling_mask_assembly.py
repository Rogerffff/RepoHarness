"""C1′-b delta 测试 (b)：sampling_mask_assembly——请求校验/响应解析/跨轮装配。

覆盖面：
- validate_sampling_mask_request：ok 路径生效值、缺参/越界/温度漂移/penalty
  拒绝分支（逐 reason_code 断言,语义对照上游 should_return_sampling_mask）;
- parse_turn_sampling_support：fake meta_info 的解析、长度对齐、sampled∈support
  逐 token 校验、abort 零输出豁免;
- assemble_leaf_sampling_mask：多轮 + 观察位单例 + 跨轮拼接 offsets 重基、
  掉落轮跳过、与 p03 已证的零宽→单例等价语义一致性断言（单例支持集
  renormalized logprob 恰为 0）;
- AssembledSamplingMask 不变量与 attach_assembled_mask 边界。

按 C1′-b 验收口径,本文件整体标 integration_base（默认 pin base skip;
integration base 全量跑）。模块本身不依赖 miles 符号,但归属 miles delta
测试账,统一走 skip 闸。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration_base


@pytest.fixture()
def sma(world):
    """被测模块（惰性 import:conftest 禁止测试模块级 import adapters.miles）。"""

    from repoharness2.adapters.miles import sampling_mask_assembly as module

    return module


def _base_params(**over):
    params = {
        "top_p": 0.8,
        "top_k": 32,
        "temperature": 0.7,
        "max_new_tokens": 128,
    }
    params.update(over)
    return {k: v for k, v in params.items() if v is not None}


# ---------------------------------------------------------------------------
# 1. 请求前置校验
# ---------------------------------------------------------------------------


def test_validate_request_ok_returns_effective_values(sma):
    effective = sma.validate_sampling_mask_request(_base_params(), expected_temperature=0.7)
    assert effective == {"top_p": 0.8, "top_k": 32, "temperature": 0.7}


@pytest.mark.parametrize("missing", ["top_p", "top_k", "temperature"])
def test_validate_request_missing_param_rejected(sma, missing):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.validate_sampling_mask_request(
            _base_params(**{missing: None}), expected_temperature=0.7
        )
    assert exc.value.reason_code == "sampling_mask_param_missing"


@pytest.mark.parametrize("top_p", [1.0, 0.0, 1.5, -0.1])
def test_validate_request_top_p_out_of_open_interval_rejected(sma, top_p):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.validate_sampling_mask_request(_base_params(top_p=top_p), expected_temperature=0.7)
    assert exc.value.reason_code == "sampling_mask_top_p_invalid"


@pytest.mark.parametrize("top_k", [0, -5, True, 2.0, "32"])
def test_validate_request_top_k_not_finite_positive_int_rejected(sma, top_k):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.validate_sampling_mask_request(_base_params(top_k=top_k), expected_temperature=0.7)
    assert exc.value.reason_code == "sampling_mask_top_k_unbounded"


def test_validate_request_top_k_exceeds_configured_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.validate_sampling_mask_request(
            _base_params(top_k=64), expected_temperature=0.7, configured_top_k=32
        )
    assert exc.value.reason_code == "sampling_mask_top_k_exceeds_configured"
    # 等于/小于上界合法;None = 未配置上界,只查有限正性（T0-A）
    sma.validate_sampling_mask_request(
        _base_params(top_k=32), expected_temperature=0.7, configured_top_k=32
    )
    sma.validate_sampling_mask_request(
        _base_params(top_k=10**6), expected_temperature=0.7, configured_top_k=None
    )


def test_validate_request_temperature_mismatch_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.validate_sampling_mask_request(
            _base_params(temperature=0.5), expected_temperature=0.7
        )
    assert exc.value.reason_code == "sampling_mask_temperature_mismatch"


@pytest.mark.parametrize(
    ("name", "bad_value"),
    [
        ("frequency_penalty", 0.5),
        ("presence_penalty", -0.1),
        ("repetition_penalty", 1.2),
        ("logit_bias", {"7": 2.0}),
        ("custom_logit_processor", "some.path"),
    ],
)
def test_validate_request_unsupported_logit_param_rejected(sma, name, bad_value):
    params = _base_params()
    params[name] = bad_value
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.validate_sampling_mask_request(params, expected_temperature=0.7)
    assert exc.value.reason_code == "sampling_mask_unsupported_logit_param"


def test_validate_request_neutral_logit_params_accepted(sma):
    params = _base_params(
        frequency_penalty=0.0,
        presence_penalty=0,
        repetition_penalty=1.0,
        logit_bias={},
        custom_logit_processor=None,
    )
    effective = sma.validate_sampling_mask_request(params, expected_temperature=0.7)
    assert effective["top_k"] == 32


# ---------------------------------------------------------------------------
# 2. 响应解析校验（fake meta_info）
# ---------------------------------------------------------------------------


def _meta(**over):
    meta = {
        "id": "rid-1",
        "finish_reason": {"type": "stop"},
        "output_token_sampling_mask": [[5, 7, 9], [3, 4]],
        "output_token_sampling_logprobs": [-0.2, -0.4],
    }
    meta.update(over)
    return {k: v for k, v in meta.items() if v is not None}


def test_parse_ok_returns_supports_and_normalized_logprobs(sma):
    turn, logprobs = sma.parse_turn_sampling_support([7, 3], _meta())
    assert turn.output_ids == (7, 3)
    assert turn.supports == ((5, 7, 9), (3, 4))
    assert turn.response_token_count == 2
    assert logprobs == [-0.2, -0.4]


@pytest.mark.parametrize(
    "kill", ["output_token_sampling_mask", "output_token_sampling_logprobs"]
)
def test_parse_missing_field_rejected(sma, kill):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.parse_turn_sampling_support([7, 3], _meta(**{kill: None}))
    assert exc.value.reason_code == "sampling_mask_missing_in_response"


def test_parse_abort_with_zero_output_exempted(sma):
    meta = {
        "id": "rid-1",
        "finish_reason": {"type": "abort"},
    }
    turn, logprobs = sma.parse_turn_sampling_support([], meta)
    assert turn.output_ids == () and turn.supports == () and logprobs == []


def test_parse_abort_with_output_tokens_still_fails_closed(sma):
    meta = {"id": "rid-1", "finish_reason": {"type": "abort"}}
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.parse_turn_sampling_support([7], meta)
    assert exc.value.reason_code == "sampling_mask_missing_in_response"


def test_parse_logprob_length_mismatch_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.parse_turn_sampling_support(
            [7, 3], _meta(output_token_sampling_logprobs=[-0.2])
        )
    assert exc.value.reason_code == "sampling_logprob_length_mismatch"


def test_parse_support_count_mismatch_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.parse_turn_sampling_support([7, 3], _meta(output_token_sampling_mask=[[5, 7]]))
    assert exc.value.reason_code == "sampling_mask_length_mismatch"


def test_parse_empty_support_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.parse_turn_sampling_support([7, 3], _meta(output_token_sampling_mask=[[5, 7], []]))
    assert exc.value.reason_code == "turn_support_empty"


def test_parse_sampled_not_in_support_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.parse_turn_sampling_support(
            [7, 3], _meta(output_token_sampling_mask=[[5, 9], [3, 4]])
        )
    assert exc.value.reason_code == "turn_sampled_not_in_support"


# ---------------------------------------------------------------------------
# 3. 跨轮装配
# ---------------------------------------------------------------------------


def _turn(sma, output_ids, supports):
    return sma.TurnSupport(output_ids=tuple(output_ids), supports=tuple(tuple(s) for s in supports))


def test_assemble_multi_turn_singleton_and_offsets_rebase(sma):
    # 叶链形状：轮1 采样 [11,12,13] -> 工具观察 [90,91]（mask=0）-> 轮2 采样 [21,22]
    response = [11, 12, 13, 90, 91, 21, 22]
    loss_mask = [1, 1, 1, 0, 0, 1, 1]
    turns = [
        _turn(sma, [11, 12, 13], [[11, 5], [12], [13, 6, 7]]),
        _turn(sma, [21, 22], [[21, 8], [22]]),
    ]
    assembled = sma.assemble_leaf_sampling_mask(response, loss_mask, turns)

    # 逐位支持集：采样位 = 引擎支持集;观察位 = 单例 {该 token}
    assert assembled.support_at(0) == (11, 5)
    assert assembled.support_at(1) == (12,)
    assert assembled.support_at(2) == (13, 6, 7)
    assert assembled.support_at(3) == (90,)  # 观察位单例
    assert assembled.support_at(4) == (91,)
    assert assembled.support_at(5) == (21, 8)
    assert assembled.support_at(6) == (22,)
    # 跨轮拼接 offsets 重基（CSR 前缀和,= 上游 concatenate 语义）
    assert assembled.ids == (11, 5, 12, 13, 6, 7, 90, 91, 21, 8, 22)
    assert assembled.offsets == (0, 2, 3, 6, 7, 8, 10, 11)
    assert assembled.response_token_count == 7
    assert assembled.sampled_token_count == 5
    assert assembled.singleton_token_count == 2
    # sampler_support 硬下界：无零宽 span,kept >= response（契约层同款）
    assert assembled.offsets[-1] == len(assembled.ids) >= assembled.response_token_count


def test_assemble_two_turns_tiling_one_run(sma):
    # 相邻两轮之间无工具 token:两轮平铺同一个 mask=1 段（S1-7a 形态 2）
    response = [11, 12, 21, 22]
    loss_mask = [1, 1, 1, 1]
    turns = [
        _turn(sma, [11, 12], [[11], [12, 3]]),
        _turn(sma, [21, 22], [[21], [22]]),
    ]
    assembled = sma.assemble_leaf_sampling_mask(response, loss_mask, turns)
    assert assembled.sampled_token_count == 4
    assert assembled.singleton_token_count == 0
    assert assembled.offsets == (0, 1, 3, 4, 5)


def test_assemble_dropped_turn_becomes_context_singletons(sma):
    # REALIGN 掉落轮：轮 1 响应整段降为 mask=0 上下文——它的 tape 不参与合并,
    # 其 token 按观察位单例补齐（S1-7a 形态 1）
    response = [31, 32, 21, 22]
    loss_mask = [0, 0, 1, 1]
    turns = [
        _turn(sma, [31, 32], [[31, 1], [32, 2]]),  # 掉落轮（无 mask=1 段可锚定）
        _turn(sma, [21, 22], [[21], [22, 9]]),
    ]
    assembled = sma.assemble_leaf_sampling_mask(response, loss_mask, turns)
    assert assembled.support_at(0) == (31,)  # 单例,不是掉落轮的引擎支持集
    assert assembled.support_at(1) == (32,)
    assert assembled.support_at(2) == (21,)
    assert assembled.support_at(3) == (22, 9)
    assert assembled.sampled_token_count == 2
    assert assembled.singleton_token_count == 2


def test_singleton_equals_slime_zero_width_semantics_logprob_zero(sma):
    """p03 定案候选 (b) 的一致性断言：观察位单例支持集 renormalized logprob
    恰为 0（= slime 零宽 span/force-keep 语义的精确等价物,P0-3 三口径已证;
    这里用 miles 训练侧同款 masked_fill+log_softmax 数值复算单点事实）。"""

    torch = pytest.importorskip("torch")

    response = [11, 90]
    loss_mask = [1, 0]
    turns = [_turn(sma, [11], [[11, 5]])]
    assembled = sma.assemble_leaf_sampling_mask(response, loss_mask, turns)
    assert assembled.support_at(1) == (90,)

    vocab = 100
    logits = torch.randn(vocab, dtype=torch.float64)
    support = torch.zeros(vocab, dtype=torch.bool)
    for t in assembled.support_at(1):
        support[t] = True
    renorm = torch.log_softmax(logits.masked_fill(~support, float("-inf")), dim=-1)
    assert renorm[90].item() == 0.0  # 单例:log softmax 单元素恰为 0,精确值


def test_assemble_length_mismatch_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.assemble_leaf_sampling_mask([1, 2], [1], [])
    assert exc.value.reason_code == "response_loss_mask_length_mismatch"


def test_assemble_non_binary_loss_mask_rejected(sma):
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.assemble_leaf_sampling_mask([1, 2], [1, 2], [])
    assert exc.value.reason_code == "loss_mask_not_binary"


def test_assemble_untileable_run_rejected(sma):
    # mask=1 段 token 与所有轮 output_ids 都对不上 -> 锚定失败当场炸
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.assemble_leaf_sampling_mask(
            [11, 12], [1, 1], [_turn(sma, [99], [[99]])]
        )
    assert exc.value.reason_code == "turns_vs_runs_mismatch"


# ---------------------------------------------------------------------------
# 4. AssembledSamplingMask 不变量 + attach
# ---------------------------------------------------------------------------


def test_assembled_invariants_rejections(sma):
    mk = sma.AssembledSamplingMask
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        mk(ids=(1,), offsets=(0, 1, 1), response_token_count=1, sampled_token_count=1, singleton_token_count=0)
    assert exc.value.reason_code == "assembled_offsets_length"
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        mk(ids=(1,), offsets=(0, 2), response_token_count=1, sampled_token_count=1, singleton_token_count=0)
    assert exc.value.reason_code == "assembled_offsets_bounds"
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        mk(ids=(1,), offsets=(0, 0, 1), response_token_count=2, sampled_token_count=2, singleton_token_count=0)
    assert exc.value.reason_code == "assembled_zero_width_span"
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        mk(ids=(1, 2), offsets=(0, 1, 2), response_token_count=2, sampled_token_count=2, singleton_token_count=1)
    assert exc.value.reason_code == "assembled_position_accounting"
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        mk(ids=(2**31,), offsets=(0, 1), response_token_count=1, sampled_token_count=1, singleton_token_count=0)
    assert exc.value.reason_code == "assembled_id_out_of_int32"


def test_attach_assembled_mask_length_gate(sma, world):
    sample = world.mk_vendor_sample()  # response_length=3
    assembled = sma.assemble_leaf_sampling_mask([12, 13, 14], [1, 0, 1], [
        _turn(sma, [12], [[12]]),
        _turn(sma, [14], [[14, 6]]),
    ])
    sma.attach_assembled_mask(sample, assembled)
    assert getattr(sample, sma.ATTACHED_MASK_ATTR) is assembled

    short = sma.assemble_leaf_sampling_mask([12], [1], [_turn(sma, [12], [[12]])])
    with pytest.raises(sma.SamplingMaskAssemblyError) as exc:
        sma.attach_assembled_mask(world.mk_vendor_sample(), short)
    assert exc.value.reason_code == "attached_mask_length_mismatch"
