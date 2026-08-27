"""F4（R3 routing tape adapter）CPU 纵切测试。

覆盖 finding §6.4 的本地验收面：

1. rh2 产生点三形态（torch tensor / 嵌套 list / flat list，对照 generate.py
   `_shape_routing_experts`）均转换为 **owned contiguous numpy.int32**，
   形状精确 `(len(tokens)-1, moe_num_layers, moe_router_topk)`；
2. 少行/多行/错 layer/topk/非整数/超 int32 值域/ragged/未知形态/期望配置
   缺失全部 fail-closed（reason_code 逐一断言）；
3. canonicalize 产物通过 miles `Sample.validate()`；
4. 真实到达 `convert_samples_to_train_data`，dtype/shape 逐值不变；
5. R3-off（slime 侧字段 None）回归：miles 侧保持 None，旧路径零改变。

两 base 通用：`rollout_routed_experts` 是 pin 与 integration base 共有的
一等字段（canonicalize._MILES_FIELDS_PIN 已含），故本文件不打
integration_base 标记——lane A/B 都真实执行。
"""

from __future__ import annotations

import numpy as np
import pytest

# 形状常量：mk_vendor_sample 的 tokens 有 5 个 -> rows = len(tokens)-1 = 4
ROWS, LAYERS, TOPK = 4, 2, 3
FLAT = list(range(100, 100 + ROWS * LAYERS * TOPK))  # 24 个互不相同的 expert id


def _nested(flat=FLAT, rows=ROWS, layers=LAYERS, topk=TOPK):
    """generate.py `_shape_routing_experts` 无 torch 回退分支的等价嵌套形状。"""

    per_token = layers * topk
    out = []
    for r in range(rows):
        row = flat[r * per_token : (r + 1) * per_token]
        out.append([row[layer * topk : (layer + 1) * topk] for layer in range(layers)])
    return out


def _tensor(flat=FLAT, rows=ROWS, layers=LAYERS, topk=TOPK):
    """generate.py `_shape_routing_experts` torch 分支的同款构造。"""

    import torch

    return torch.tensor(list(flat), dtype=torch.int32).reshape(rows, layers, topk)


def _canon(world, tape, *, layers=LAYERS, topk=TOPK, **vendor_over):
    vend = world.mk_vendor_sample(rollout_routed_experts=tape, **vendor_over)
    return world.canonicalize_sample(
        vend,
        miles_input_sample=world.mk_miles_input(),
        moe_num_layers=layers,
        moe_router_topk=topk,
    )


def _assert_contract_array(arr):
    """miles 契约（types.py 字段注释 + train conversion int32 wire dtype）。"""

    assert isinstance(arr, np.ndarray)
    assert arr.dtype == np.int32
    assert arr.shape == (ROWS, LAYERS, TOPK)
    assert arr.flags["C_CONTIGUOUS"]
    assert arr.flags["OWNDATA"]  # owned：不与 torch tensor / 输入 list 共享内存
    assert arr.reshape(-1).tolist() == FLAT


# ---------------------------------------------------------------------------
# 1+3：三形态转换 + validate()
# ---------------------------------------------------------------------------


def test_tensor_form_converted_owned_int32(world):
    tensor = _tensor()
    out = _canon(world, tensor)
    _assert_contract_array(out.rollout_routed_experts)
    out.validate()  # miles 自身的行数断言（len(tokens)-1）也过

    # owned 语义的实测面：改写源 tensor，miles 侧数组不动
    tensor[0, 0, 0] = -999
    assert out.rollout_routed_experts[0, 0, 0] == FLAT[0]


def test_nested_list_form_converted(world):
    out = _canon(world, _nested())
    _assert_contract_array(out.rollout_routed_experts)
    out.validate()


def test_flat_list_form_converted(world):
    out = _canon(world, list(FLAT))
    _assert_contract_array(out.rollout_routed_experts)
    out.validate()


def test_forms_metamorphic_equal(world):
    """三形态携带同一 tape 时产物逐值相同（形态只是运输差异，不是语义差异）。"""

    a = _canon(world, _tensor()).rollout_routed_experts
    b = _canon(world, _nested()).rollout_routed_experts
    c = _canon(world, list(FLAT)).rollout_routed_experts
    assert np.array_equal(a, b) and np.array_equal(b, c)


# ---------------------------------------------------------------------------
# 2：fail-closed 分支（逐 reason_code）
# ---------------------------------------------------------------------------


def _flat_for(rows=ROWS, layers=LAYERS, topk=TOPK):
    return list(range(rows * layers * topk))


@pytest.mark.parametrize(
    ("tape_factory", "reason_code"),
    [
        # 少行 / 多行（嵌套形态，layers/topk 正确）
        (lambda: _nested(_flat_for(rows=ROWS - 1), rows=ROWS - 1), "routed_experts_rows_mismatch"),
        (lambda: _nested(_flat_for(rows=ROWS + 1), rows=ROWS + 1), "routed_experts_rows_mismatch"),
        # 错 layers / 错 topk
        (
            lambda: _nested(_flat_for(layers=LAYERS + 1), layers=LAYERS + 1),
            "routed_experts_shape_mismatch",
        ),
        (
            lambda: _nested(_flat_for(topk=TOPK + 1), topk=TOPK + 1),
            "routed_experts_shape_mismatch",
        ),
        # flat 元素数不对
        (lambda: _flat_for()[:-1], "routed_experts_numel_mismatch"),
        (lambda: _flat_for() + [0], "routed_experts_numel_mismatch"),
        # 非整数：float / bool（list 与 torch 两侧）
        (lambda: [float(x) for x in FLAT], "routed_experts_not_integer"),
        (lambda: [True] * (ROWS * LAYERS * TOPK), "routed_experts_not_integer"),
        (lambda: _tensor().float(), "routed_experts_not_integer"),
        # ragged（numpy 拒绝构成规则数组）
        (lambda: [[[1, 2, 3], [4, 5]], [[6, 7, 8]]], "routed_experts_malformed"),
        # 混型（int+str 被 numpy 拉成字符串数组 -> 非整数 dtype 拒绝）
        (lambda: [1, "x", 3], "routed_experts_not_integer"),
        # 超 int32 值域（int64 承载但收窄有损）
        (lambda: [2**31] + _flat_for()[1:], "routed_experts_out_of_int32_range"),
        # 未知形态：dict / str / 甚至"正确的" numpy 数组（非产生点形态，宁炸不猜）
        (lambda: {"rows": 4}, "routed_experts_unknown_form"),
        (lambda: "not-a-tape", "routed_experts_unknown_form"),
        (
            lambda: np.zeros((ROWS, LAYERS, TOPK), dtype=np.int32),
            "routed_experts_unknown_form",
        ),
        # 2 维张量：既非 flat 也非 (rows, layers, topk)
        (lambda: _nested()[0], "routed_experts_unknown_form"),
    ],
)
def test_fail_closed_forms(world, tape_factory, reason_code):
    with pytest.raises(world.CanonicalizationError, match=reason_code):
        _canon(world, tape_factory())


def test_config_missing_fail_closed(world):
    """tape 在场而 moe_num_layers/moe_router_topk 期望缺失 = 拒绝（generate_fn
    未从 orchestrator config 透传时不允许静默猜形状）。"""

    vend = world.mk_vendor_sample(rollout_routed_experts=list(FLAT))
    with pytest.raises(world.CanonicalizationError, match="routed_experts_config_missing"):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


@pytest.mark.parametrize(("layers", "topk"), [(0, TOPK), (LAYERS, 0), (-1, TOPK)])
def test_config_invalid_fail_closed(world, layers, topk):
    with pytest.raises(world.CanonicalizationError, match="routed_experts_config_invalid"):
        _canon(world, list(FLAT), layers=layers, topk=topk)


def test_tokens_too_short_fail_closed(world):
    """len(tokens)-1 <= 0：不存在合法 routing 行（tape 却在场 = 事实矛盾）。"""

    with pytest.raises(world.CanonicalizationError, match="routed_experts_rows_mismatch"):
        _canon(
            world,
            list(FLAT),
            tokens=[10],
            response_length=0,
            loss_mask=[],
            rollout_log_probs=[],
        )


# ---------------------------------------------------------------------------
# 4：真实到达 convert_samples_to_train_data（dtype/shape 逐值不变）
# ---------------------------------------------------------------------------


async def test_vertical_train_conversion_preserves_tape(world):
    from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data
    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DataBufferInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args()
    inputs = [world.mk_miles_input(index=i) for i in range(4)]
    # 三形态混编（tensor / 嵌套 / flat / tensor），4 行恰好整除
    # global_batch_size=4——postprocess 的 GBS trim 分支不吃掉样本
    tapes = [_tensor(), _nested(), list(FLAT), _tensor()]
    group = [
        world.canonicalize_group(
            [world.mk_vendor_sample(index=i, rollout_routed_experts=tapes[i])],
            miles_input_sample=inputs[i],
            moe_num_layers=LAYERS,
            moe_router_topk=TOPK,
        )
        for i in range(4)
    ]

    recycled = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))
    await buf.put(DataBufferInput(prompt_group=inputs, group=group))
    got = await buf.get(current_version=8)
    assert got.group is group and recycled == []

    data, metadata = postprocess_rollout_data(args, [got.group], train_parallel_config=None)
    assert len(data) == 4

    td = convert_samples_to_train_data(args, data, metadata, None, None)
    converted = td["rollout_routed_experts"]
    assert len(converted) == 4
    for arr in converted:
        _assert_contract_array(arr)  # dtype/shape/逐值均未被搬运链改写
    # 逐对象同一性：train conversion 不复制（miles 源码是逐样本引用透传），
    # 因此 canonicalize 产出的 owned 数组就是训练侧拿到的那份。
    for i in range(4):
        assert converted[i] is group[i][0].rollout_routed_experts


# ---------------------------------------------------------------------------
# 5：R3-off 回归——字段保持 None，旧路径零改变
# ---------------------------------------------------------------------------


def test_r3_off_stays_none(world):
    out = world.canonicalize_sample(
        world.mk_vendor_sample(), miles_input_sample=world.mk_miles_input()
    )
    assert out.rollout_routed_experts is None
    out.validate()


def test_r3_off_with_config_present_stays_none(world):
    """只配 moe 期望、不带 tape（R3-off 但模型是 MoE）：不无中生有。"""

    out = world.canonicalize_sample(
        world.mk_vendor_sample(),
        miles_input_sample=world.mk_miles_input(),
        moe_num_layers=LAYERS,
        moe_router_topk=TOPK,
    )
    assert out.rollout_routed_experts is None
