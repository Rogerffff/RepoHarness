# -*- coding: utf-8 -*-
"""L3 反例：pydantic__pydantic-5706 —— 候选把 Python 侧 `Sequence` 改成 list 路线。

断言写的是 **base（未打任何补丁）的既有公开行为**，不是 gold 的新行为。
因此三种工作区状态下的预期是：

    base      -> 全部通过（这些断言就是从 base 的 tests/test_types.py 抄过来的）
    gold      -> 全部通过（gold 用 json_or_python_schema，Python 侧保留原语义）
    candidate -> 至少 4 组失败（tuple/deque 容器类型、range 被拒、generator 被接受）

官方 F2P 只有 tests/test_json_schema.py 的两个 Sequence 参数，执行面不含
tests/test_types.py / tests/test_edge_cases.py，所以官方全绿不代表这些行为没被改。

证据出处（base 源码，commit 70e7e99ca1861ad71520cc8fcf1a2fb913abbc10）：
  tests/test_types.py:1876-1891  test_sequence_success 的参数化表
  tests/test_types.py:2010-2027  test_sequence_generator_fails
  tests/test_edge_cases.py:2503  test_sequences_str（错误契约 sequence_str）
候选改动：pydantic/_internal/_std_types_schema.py 的 SEQUENCE_ORIGIN_MAP
          新增 `collections.abc.Sequence: list`（candidate.src_only.diff）。

本文件只用 pydantic 公开 API（BaseModel / ValidationError），不 import 内部模块，
因此 base / gold / candidate 三种状态下都能收集（collect）成功。
"""
from collections import deque
from typing import Sequence, Set, Tuple

import pytest
from pydantic import BaseModel, ValidationError


def _model(annotation):
    class Model(BaseModel):
        v: annotation

    return Model


# --------------------------------------------------------------------------
# 1. 容器类型保留：base 要求 tuple 进 tuple 出、deque 进 deque 出
#    候选实测：两者都变成 list
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param([1, 2, 3], [1, 2, 3], id="list_in_list_out"),
        pytest.param((1, 2, 3), (1, 2, 3), id="tuple_in_tuple_out"),
        pytest.param(deque((1, 2, 3)), deque((1, 2, 3)), id="deque_in_deque_out"),
    ],
)
def test_sequence_int_preserves_container_type(value, expected):
    """base: `Sequence[int]` 保留输入容器类型；候选把 tuple/deque 转成 list。"""
    got = _model(Sequence[int])(v=value).v
    assert got == expected
    assert type(got) is type(expected), (
        "容器类型被改变：期望 %s，实际 %s" % (type(expected).__name__, type(got).__name__)
    )


def test_sequence_tuple_of_tuples_preserves_outer_tuple():
    """base: Sequence[Tuple[int, str]] 的外层 tuple 也应保留。"""
    value = ((1, "a"), (2, "b"), (3, "c"))
    got = _model(Sequence[Tuple[int, str]])(v=value).v
    assert got == value
    assert type(got) is tuple, "外层容器从 tuple 变成了 %s" % type(got).__name__


def test_sequence_of_sets_accepts_list_of_sets():
    """base: Sequence[Set[int]] 接受 list-of-set，结果仍是 list。"""
    value = [{1, 2}, {3, 4}, {5, 6}]
    got = _model(Sequence[Set[int]])(v=value).v
    assert got == value
    assert type(got) is list


# --------------------------------------------------------------------------
# 2. 输入接受范围：base 接受 range；候选用 list schema 后 range 被 list_type 拒绝
# --------------------------------------------------------------------------
def test_sequence_int_accepts_range():
    """base: Sequence[int] 接受 range(5)，结果是 [0,1,2,3,4]。"""
    got = _model(Sequence[int])(v=range(5)).v
    assert got == [0, 1, 2, 3, 4]


# --------------------------------------------------------------------------
# 3. 输入拒绝范围：base 拒绝 generator，错误类型 is_instance_of
#    候选实测：generator 反而被接受，返回 [1, 2, 3]
# --------------------------------------------------------------------------
def test_sequence_int_rejects_generator():
    """base: generator 不是 Sequence，应报 is_instance_of。"""
    model = _model(Sequence[int])
    gen = (i for i in [1, 2, 3])
    with pytest.raises(ValidationError) as exc_info:
        model(v=gen)
    errors = exc_info.value.errors(include_url=False)
    assert [e["type"] for e in errors] == ["is_instance_of"], (
        "generator 的拒绝理由变了（或根本没被拒绝）：%r" % (errors,)
    )


def test_sequence_int_rejects_generator_value_level():
    """与上一条互补：即使不比较错误类型，也不允许 generator 通过校验。

    这条刻意不绑定错误字符串，用来区分"错误文案变了"和"接受集合变了"。
    """
    model = _model(Sequence[int])
    gen = (i for i in [1, 2, 3])
    try:
        got = model(v=gen).v
    except ValidationError:
        return  # 被拒绝 = base 行为
    pytest.fail("generator 被接受了，值为 %r（base 与 gold 都应拒绝）" % (got,))


# --------------------------------------------------------------------------
# 4. 错误契约：base 对 Sequence[str] 传 str 报 sequence_str
#    候选走 list 路线后变成 list_type（对应 test_edge_cases.py::test_sequences_str）
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "item_type,payload",
    [
        pytest.param(str, "1bc", id="Sequence_str"),
        pytest.param(bytes, b"1bc", id="Sequence_bytes"),
    ],
)
def test_sequence_str_error_contract(item_type, payload):
    """base: 直接传 str/bytes 给 Sequence[str]/Sequence[bytes] 报 sequence_str。

    与 base tests/test_edge_cases.py::test_sequences_str 的输入完全一致。
    """
    model = _model(Sequence[item_type])
    # 正向：拆开成两段的 list 应通过
    ok = [payload[:1], payload[1:]]
    assert model(v=ok).v == ok
    with pytest.raises(ValidationError) as exc_info:
        model(v=payload)
    types = [e["type"] for e in exc_info.value.errors(include_url=False)]
    assert types == ["sequence_str"], "错误契约从 sequence_str 变成 %r" % (types,)


# --------------------------------------------------------------------------
# 5. 正向对照：题面要求的 JSON 行为（gold 与 candidate 都应满足，base 不满足）
#    放在同一文件里，便于一次跑完区分"候选修好了什么"和"候选弄坏了什么"。
# --------------------------------------------------------------------------
def test_json_schema_for_sequence_int_is_array():
    """题面目标：Sequence[int] 的 JSON Schema 应是 integer array。

    base 预期 FAIL（抛 PydanticInvalidForJsonSchema），gold / candidate 预期 PASS。
    """
    model = _model(Sequence[int])
    schema = model.model_json_schema()
    assert schema["properties"]["v"] == {"title": "V", "type": "array", "items": {"type": "integer"}}


def test_validate_json_for_sequence_int_succeeds():
    """题面目标：model_validate_json 对 JSON 数组应成功。base FAIL，gold / candidate PASS。"""
    model = _model(Sequence[int])
    assert model.model_validate_json('{"v": [1, 2, 3]}')
