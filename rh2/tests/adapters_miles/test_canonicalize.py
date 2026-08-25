"""canonicalize_sample / canonicalize_group 单测（miles 迁移 C0，规格 = R5 §3.3）。

注意：按 conftest 约定，slime/miles/repoharness2.adapters.miles 一律经
`world` fixture 取用，不在模块级 import（避免污染同会话其他测试目录）。
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 动机回归：两侧枚举互不相等（B1 崩溃链的根因事实）
# ---------------------------------------------------------------------------


def test_enum_inequality_regression(world):
    """slime 与 miles 的 Status 是两个不同的 Enum 类，值相同也互不相等。
    canonicalize 因此必须按字符串值重建，绝不能复制枚举对象。"""

    assert world.SS.Status.ABORTED != world.MS.Status.ABORTED
    assert world.SS.Status.COMPLETED != world.MS.Status.COMPLETED
    # 字符串值两侧一致（映射表的前提事实）
    assert world.SS.Status.ABORTED.value == world.MS.Status.ABORTED.value == "aborted"


# ---------------------------------------------------------------------------
# status 往返
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["COMPLETED", "ABORTED", "FAILED"])
def test_status_roundtrip_by_value(world, name):
    inp = world.mk_miles_input()
    vend = world.mk_vendor_sample(status=getattr(world.SS.Status, name))
    out = world.canonicalize_sample(vend, miles_input_sample=inp)
    assert isinstance(out, world.MS)
    # 身份级断言：必须是 miles 枚举成员本体（enum 不等性回归的对偶面）
    assert out.status is getattr(world.MS.Status, name)


def test_status_truncated_direct(world):
    out = world.canonicalize_sample(
        world.mk_vendor_sample(status=world.SS.Status.TRUNCATED),
        miles_input_sample=world.mk_miles_input(),
    )
    assert out.status is world.MS.Status.TRUNCATED


def test_pending_rejected(world):
    """vendor 输出必须是终态；PENDING 说明生成从未发生，fail-closed。"""

    with pytest.raises(world.CanonicalizationError, match="status_unmappable"):
        world.canonicalize_sample(
            world.mk_vendor_sample(status=world.SS.Status.PENDING),
            miles_input_sample=world.mk_miles_input(),
        )


# ---------------------------------------------------------------------------
# truncated metadata -> Status.TRUNCATED 显式映射
# ---------------------------------------------------------------------------


def test_truncated_metadata_upgrades_completed(world):
    """vendor to_sample 硬编码 COMPLETED、截断事实只在 metadata['truncated']；
    canonicalize 必须恢复成 miles TRUNCATED（miles buffer/训练列只看 status）。"""

    out = world.canonicalize_sample(
        world.mk_vendor_sample(truncated=True),
        miles_input_sample=world.mk_miles_input(),
    )
    assert out.status is world.MS.Status.TRUNCATED
    assert out.metadata["truncated"] is True  # metadata 原样保留


def test_truncated_false_stays_completed(world):
    out = world.canonicalize_sample(
        world.mk_vendor_sample(truncated=False),
        miles_input_sample=world.mk_miles_input(),
    )
    assert out.status is world.MS.Status.COMPLETED


def test_truncated_does_not_override_aborted(world):
    """中止语义优先：ABORTED + truncated flag 不得被改写成 TRUNCATED
    （否则 miles buffer 的 abort 过滤会放行一个中止样本）。"""

    out = world.canonicalize_sample(
        world.mk_vendor_sample(status=world.SS.Status.ABORTED, truncated=True),
        miles_input_sample=world.mk_miles_input(),
    )
    assert out.status is world.MS.Status.ABORTED


def test_truncated_flag_non_bool_rejected(world):
    with pytest.raises(world.CanonicalizationError, match="truncated_flag_not_bool"):
        world.canonicalize_sample(
            world.mk_vendor_sample(truncated="yes"),
            miles_input_sample=world.mk_miles_input(),
        )


# ---------------------------------------------------------------------------
# 字段复制 + miles 输入侧字段保留
# ---------------------------------------------------------------------------


def test_vendor_fields_copied_and_input_fields_preserved(world):
    from miles.utils.types import AdapterRef, RewardSpec

    inp = world.mk_miles_input(index=3, group_index=1)
    inp.adapter = AdapterRef(name="lora-a", slot=2)
    inp.reward_spec = RewardSpec(rm_type="custom", custom_rm_path="x.y.rm")
    inp.generate_function_path = "a.b.c"
    inp.multimodal_inputs = {"image": ["ref"]}

    vend = world.mk_vendor_sample(index=3, group_index=1, rollout_id=7, reward=0.5)
    out = world.canonicalize_sample(vend, miles_input_sample=inp)

    # vendor 输出复制面
    assert out.tokens == vend.tokens and out.tokens is not vend.tokens  # 浅拷贝
    assert out.response == "resp"
    assert out.response_length == 3
    assert out.loss_mask == [1, 0, 1] and out.loss_mask is not vend.loss_mask
    assert out.rollout_log_probs == vend.rollout_log_probs
    assert out.reward == 0.5
    assert out.weight_versions == ["7"]
    assert out.rollout_id == 7
    assert (out.group_index, out.index) == (1, 3)
    assert out.prompt == "prompt"
    assert out.metadata == vend.metadata and out.metadata is not vend.metadata
    assert out.remove_sample is False
    # miles 属性面可用（B1 症状 2 的对偶断言）
    assert out.oldest_weight_version == 7

    # miles 输入侧保留面
    assert out.adapter is inp.adapter
    assert out.reward_spec is inp.reward_spec
    assert out.routing_key == inp.routing_key
    assert out.generate_function_path == "a.b.c"
    assert out.multimodal_inputs is inp.multimodal_inputs


def test_identity_mismatch_rejected(world):
    """输出样本 index/group_index 必须与本次 generate 的输入一致（防串组）。"""

    with pytest.raises(world.CanonicalizationError, match="identity_mismatch"):
        world.canonicalize_sample(
            world.mk_vendor_sample(index=9),
            miles_input_sample=world.mk_miles_input(index=3),
        )


# ---------------------------------------------------------------------------
# fail-closed：未知字段 / slime 独有字段
# ---------------------------------------------------------------------------


def test_unknown_extra_attr_rejected(world):
    vend = world.mk_vendor_sample()
    vend.surprise_field = 1  # dataclass 外的 setattr 属性
    with pytest.raises(world.CanonicalizationError, match="unknown_sample_attrs"):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


@pytest.mark.parametrize(
    "field,value",
    [
        ("custom_rm_path", "x.y.rm"),
        ("multimodal_train_inputs", {"pixel_values": []}),
        ("multimodal_train_input_id", "mm-1"),
        ("apply_chat_template_kwargs", {"enable_thinking": True}),
        ("generate_function_path", "a.b.c"),
        ("rollout_routed_experts", [1, 2, 3]),
    ],
)
def test_slime_only_fields_rejected(world, field, value):
    vend = world.mk_vendor_sample()
    setattr(vend, field, value)
    with pytest.raises(world.CanonicalizationError, match=f"slime_field_rejected:{field}"):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


def test_top_p_tape_rejected_reserved_for_sampling_mask(world):
    """sampling-mask 一等字段预留位：top-p tape 出现时 fail-closed 而不是
    静默丢弃（接线归 C1，见 canonicalize.py docstring）。"""

    vend = world.mk_vendor_sample()
    vend.rollout_top_p_token_ids = [10, 11]
    vend.rollout_top_p_token_offsets = [0, 1, 2, 2]
    with pytest.raises(
        world.CanonicalizationError, match="slime_field_rejected:rollout_top_p_token_ids"
    ):
        world.canonicalize_sample(vend, miles_input_sample=world.mk_miles_input())


def test_non_sample_output_rejected(world):
    with pytest.raises(world.CanonicalizationError, match="unexpected_output_type"):
        world.canonicalize_sample({"not": "a sample"}, miles_input_sample=world.mk_miles_input())


# ---------------------------------------------------------------------------
# miles 直通分支（rh2 abort/eval 收口路径把输入样本原地改写后返回）
# ---------------------------------------------------------------------------


def test_miles_passthrough_abort_shape(world):
    """abort 收口形状（generate.py `_abort_result`）：miles 输入样本本体被
    原地改写 + setattr session_id。canonicalize 校验后原对象返回并剥除
    session_id。"""

    inp = world.mk_miles_input(index=2)
    # 复刻 _abort_result 的改写面
    inp.tokens = [0, 0]
    inp.response = ""
    inp.response_length = 1
    inp.loss_mask = [0]
    inp.rollout_log_probs = [0.0]
    inp.reward = 0.0
    inp.remove_sample = True
    inp.status = world.MS.Status.ABORTED
    inp.metadata = {"abort_reason": "rh2_gate_degraded", "instance_id": "task-1"}
    inp.session_id = "rh2-task-1-2-0"  # rh2 编排层 setattr（非 miles 字段）

    out = world.canonicalize_sample(inp, miles_input_sample=inp)
    assert out is inp  # 原对象直通
    assert out.status is world.MS.Status.ABORTED
    assert "session_id" not in out.__dict__  # 已剥除
    assert out.remove_sample is True


def test_miles_passthrough_unknown_extra_rejected(world):
    inp = world.mk_miles_input()
    inp.status = world.MS.Status.COMPLETED
    inp.rollout_top_p_token_ids = []  # miles Sample 没有该字段——必须拒绝
    with pytest.raises(world.CanonicalizationError, match="unknown_sample_attrs"):
        world.canonicalize_sample(inp, miles_input_sample=inp)


# ---------------------------------------------------------------------------
# 递归组 / 嵌套 fan-out
# ---------------------------------------------------------------------------


def test_group_nested_fanout_shares_rollout_id(world):
    """嵌套 fan-out：branch sibling 共享 rollout_id，结构原样保留。"""

    inp = world.mk_miles_input(index=1)
    fanout = [world.mk_vendor_sample(index=1, rollout_id=42) for _ in range(3)]
    out = world.canonicalize_group(fanout, miles_input_sample=inp)
    assert isinstance(out, list) and len(out) == 3
    assert all(isinstance(s, world.MS) for s in out)
    assert {s.rollout_id for s in out} == {42}
    assert all(s.status is world.MS.Status.COMPLETED for s in out)


def test_group_recursive_nested_structure(world):
    """更深嵌套（list[list[Sample]]）也逐层保形转换。"""

    inp = world.mk_miles_input(index=0)
    nested = [
        [world.mk_vendor_sample(index=0, rollout_id=5)],
        [world.mk_vendor_sample(index=0, rollout_id=6) for _ in range(2)],
    ]
    out = world.canonicalize_group(nested, miles_input_sample=inp)
    assert [len(x) for x in out] == [1, 2]
    assert out[1][0].rollout_id == out[1][1].rollout_id == 6
    assert all(isinstance(s, world.MS) for grp in out for s in grp)


def test_group_empty_list_rejected(world):
    with pytest.raises(world.CanonicalizationError, match="empty_output_list"):
        world.canonicalize_group([], miles_input_sample=world.mk_miles_input())


# ---------------------------------------------------------------------------
# 模块级 schema 守卫（允许集显式列出的可执行形态）
# ---------------------------------------------------------------------------


def test_field_allowlists_match_live_dataclasses(world):
    from repoharness2.adapters.miles import canonicalize as canon

    assert frozenset(world.SS.__dataclass_fields__) == canon._SLIME_FIELDS_EXPECTED
    assert frozenset(world.MS.__dataclass_fields__) == canon._MILES_FIELDS_EXPECTED
