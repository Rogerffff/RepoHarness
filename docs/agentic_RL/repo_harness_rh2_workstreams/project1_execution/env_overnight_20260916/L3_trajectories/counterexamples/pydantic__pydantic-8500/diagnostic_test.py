# -*- coding: utf-8 -*-
"""L3 反例：pydantic__pydantic-8500 —— 官方用例没有覆盖题面原例。

题面原例（`public_bundles_v0.jsonl` 的 problem_statement）：

    class MyModel(BaseModel):
        a: str              # 必填，construct 时不给
        b: str | None = None

    m = MyModel.model_construct()
    m.a = 'a'
    m.b = 'b'
    m.model_dump()          # 题面说应为 {'a': 'a', 'b': 'b'}，实际是 {'b': 'b', 'a': 'a'}

官方 test_patch 换了一个**不同的**场景：

    class MyModel(BaseModel):
        a: str = 'a'        # 有默认
        b: str              # 必填，construct 时给了
    MyModel.model_construct(b='b').model_dump_json() == '{"a":"a","b":"b"}'

两者的字段角色（谁必填、谁有默认）和赋值时机（construct 时 vs construct 之后）都不同。
`model_construct` 的修复只改构造循环里的字典写入顺序，管不到"构造后再赋值"这条路径：
缺失的必填字段 `a` 在构造时根本不会进 `__dict__`，之后 `m.a = 'a'` 只能追加到末尾。

因此预期是：**base / gold / candidate 三种状态下，题面原例全部 FAIL**；
只有官方那个换过场景的用例在 gold / candidate 上 PASS。

这不是"候选没做好"，而是**任务的验收面与题面要求不是同一件事**：
按题面把问题解决掉并不能拿分，按官方用例拿分也不代表题面问题被解决。

参考：`solvability_review_20260909/01_failure_cases.md` 的"追加交叉核验：pydantic__pydantic-8500"；
轨迹实测 `stream.jsonl:6073-6074`（原例仍返回 b,a）、`:6808-6809`（逐步打印 __dict__）。

写法注意：**必须比较键的顺序**，不能用 dict 相等——`{'a':1,'b':2} == {'b':2,'a':1}` 为真。
"""
import pytest
from pydantic import BaseModel, Field
from typing import Optional


# --------------------------------------------------------------------------
# 1. 题面原例：construct 后逐个赋值
# --------------------------------------------------------------------------
def test_problem_statement_example_dump_order():
    """题面要求的顺序 a,b。base / gold / candidate 预期都 FAIL（实际 b,a）。"""
    class MyModel(BaseModel):
        a: str
        b: Optional[str] = None

    m = MyModel.model_construct()
    m.a = "a"
    m.b = "b"
    assert list(m.model_dump().keys()) == ["a", "b"], (
        "题面原例未被修复：实际顺序 %r" % (list(m.model_dump().keys()),)
    )


def test_problem_statement_example_json_order():
    """同一场景的 JSON 序列化顺序。与上一条一起，排除 dump 与 dump_json 走不同路径的可能。"""
    class MyModel(BaseModel):
        a: str
        b: Optional[str] = None

    m = MyModel.model_construct()
    m.a = "a"
    m.b = "b"
    assert m.model_dump_json() == '{"a":"a","b":"b"}', (
        "题面原例的 JSON 顺序未被修复：实际 %s" % m.model_dump_json()
    )


def test_problem_statement_example_intermediate_state():
    """把中间状态摊开，便于在日志里直接看出"缺失必填字段不进 __dict__"。

    这条不是 pass/fail 判据，是把 `stream.jsonl:6808-6809` 的观察固化成可复核输出；
    断言只锁"construct 后不含 a"这一条已知的既有行为。
    """
    class MyModel(BaseModel):
        a: str
        b: Optional[str] = None

    m = MyModel.model_construct()
    keys_after_construct = list(m.__dict__.keys())
    m.a = "a"
    keys_after_set_a = list(m.__dict__.keys())
    print("after construct:", keys_after_construct, " after m.a='a':", keys_after_set_a)
    assert "a" not in keys_after_construct, (
        "行为变了：缺失的必填字段 a 现在出现在 construct 结果里 %r" % (keys_after_construct,)
    )


# --------------------------------------------------------------------------
# 2. 官方 F2P 的场景（换过角色）：base FAIL，gold / candidate PASS
# --------------------------------------------------------------------------
def test_official_scenario_retain_order_of_fields():
    """官方 tests/test_construction.py::test_retain_order_of_fields 的同款断言。"""
    class MyModel(BaseModel):
        a: str = "a"
        b: str

    m = MyModel.model_construct(b="b")
    assert m.model_dump_json() == '{"a":"a","b":"b"}'


def test_official_scenario_with_default_factory():
    """把官方场景换成 default_factory，检查修复是否只对字面默认值生效。

    base 预期 FAIL（默认值被挪到末尾），gold / candidate 预期 PASS。
    """
    class MyModel(BaseModel):
        a: str = Field(default_factory=lambda: "a")
        b: str

    m = MyModel.model_construct(b="b")
    assert list(m.model_dump().keys()) == ["a", "b"]


def test_official_scenario_with_alias():
    """带 alias 的字段也应按声明顺序落位。base FAIL，gold / candidate PASS。"""
    class MyModel(BaseModel):
        a: str = "a"
        b: str = Field(alias="b_alias")

    m = MyModel.model_construct(b_alias="b")
    assert list(m.model_dump().keys()) == ["a", "b"]


# --------------------------------------------------------------------------
# 3. 护栏：修复不得改变 model_construct 的其它既有公开行为
#     base / gold / candidate 三态都应 PASS；任一状态 FAIL 说明引入了回归。
# --------------------------------------------------------------------------
def test_model_construct_still_allows_missing_required_field():
    """model_construct 的既有契约：允许缺失必填字段，且不给它塞占位值。"""
    class MyModel(BaseModel):
        a: str
        b: Optional[str] = None

    m = MyModel.model_construct()
    assert "a" not in m.__dict__
    with pytest.raises(AttributeError):
        _ = m.a


def test_model_fields_set_excludes_defaults():
    """`model_fields_set` 只含显式提供的字段，不含被填入的默认值。"""
    class MyModel(BaseModel):
        a: str = "a"
        b: str

    m = MyModel.model_construct(b="b")
    assert m.model_fields_set == {"b"}


def test_model_fields_set_respects_explicit_argument():
    """显式传 `_fields_set` 时以它为准。"""
    class MyModel(BaseModel):
        a: str = "a"
        b: str

    m = MyModel.model_construct(_fields_set={"a"}, b="b")
    assert m.model_fields_set == {"a"}


def test_model_fields_set_with_alias():
    """通过 alias 提供的值应记入 model_fields_set（记的是字段名）。"""
    class MyModel(BaseModel):
        a: str = "a"
        b: str = Field(alias="b_alias")

    m = MyModel.model_construct(b_alias="b")
    assert m.model_fields_set == {"b"}
