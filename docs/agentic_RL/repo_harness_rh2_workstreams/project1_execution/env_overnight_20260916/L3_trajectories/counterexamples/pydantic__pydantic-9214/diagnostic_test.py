# -*- coding: utf-8 -*-
"""L3 反例：pydantic__pydantic-9214 —— 两种"描述来源优先级"解释的最小矩阵。

## 分歧点是什么

题面要求：`RootModel` 的 `root: int = Field(description='abc')` 应让
`model_json_schema()` 里出现 `description: 'abc'`。题面给的 workaround 是"把描述写成
model 的 docstring"，而且**两处描述恰好都是 'abc'**，所以题面无法区分两者冲突时谁优先。

  解释 A（Field 优先 / 候选走的路）：既然是 Field 上写的描述，它应该赢。
        实现落点：`GenerateJsonSchema.model_schema` 读 root field 的 description，
        在 `_update_class_schema` 里直接 `schema_to_update['description'] = description`。
        由于 docstring 是更早的 `modify_model_json_schema` 写进去的，这一步会**覆盖** docstring。
  解释 B（docstring 优先 / gold 与既有行为）：docstring 先写、Field 只做 fallback。
        实现落点：`_generate_schema.modify_model_json_schema` 在已有 docstring 分支后加 elif。

判定依据只出现在 `hints_text`（`s2/raw/swe_gym_lite_full_f70b1a29.jsonl:190`，维护者明说
"为了向后兼容，两者同时存在时用 docstring"），**不在 agent 可见的 prompt 里**。

## 为什么这是 P2P 而不是新要求

base 上"只有 docstring"就会输出 docstring；官方新增的
`test_model_with_both_docstring_and_field_description` 把这条既有行为固定下来，
所以它被列进 P2P（54 条之一）。候选打破的是**已经存在的输出**，不是一条凭空新增的要求。

参考：`solvability_review_20260909/01_failure_cases.md` §3；轨迹 `stream.jsonl:370`
（模型已读到 `_generate_schema.py:229-231` 的 docstring 分支）、`:4331`（thinking 明确识别
出优先级冲突并承认"无显式规范"）、`:12393`（`error_max_turns`，最后没跑成 pytest）。
"""
import pytest
from pydantic import BaseModel, Field, RootModel


# ==========================================================================
# 四格矩阵：描述来源 × 是否冲突
# ==========================================================================
def test_matrix_1_no_description_at_all():
    """既无 docstring 也无 Field description → schema 里不应有 description。三态都 PASS。"""
    class AModel(RootModel):
        root: int

    schema = AModel.model_json_schema()
    assert "description" not in schema, "凭空多出 description：%r" % (schema,)
    assert schema == {"title": "AModel", "type": "integer"}


def test_matrix_2_only_field_description():
    """只有 Field(description='abc') → 题面要求的目标。base FAIL，gold PASS，candidate PASS。

    这条等价于官方 F2P `tests/test_root_model.py::test_model_with_field_description`。
    """
    class AModel(RootModel):
        root: int = Field(description="abc")

    assert AModel.model_json_schema() == {
        "title": "AModel",
        "type": "integer",
        "description": "abc",
    }


def test_matrix_3_only_docstring():
    """只有 docstring → 沿用 base 的既有行为。三态都 PASS。"""
    class AModel(RootModel):
        """More detailed description"""

        root: int

    assert AModel.model_json_schema() == {
        "title": "AModel",
        "type": "integer",
        "description": "More detailed description",
    }


def test_matrix_4_both_present_and_different__docstring_wins():
    """两者都有且不同 → 既有行为（docstring）应保留。

    base PASS、gold PASS、candidate **FAIL**（候选返回 'abc'）。
    等价于官方 P2P `tests/test_root_model.py::test_model_with_both_docstring_and_field_description`。
    """
    class AModel(RootModel):
        """More detailed description"""

        root: int = Field(description="abc")

    assert AModel.model_json_schema() == {
        "title": "AModel",
        "type": "integer",
        "description": "More detailed description",
    }


def test_matrix_4b_both_present__which_source_wins():
    """把第 4 格换成"只报告谁赢"，不预设答案，便于在三态日志里直接读出分歧。

    断言只锁一件两种解释都同意的事：description 必须是这两个来源之一，不能凭空变成别的。
    """
    class AModel(RootModel):
        """DOCSTRING_SOURCE"""

        root: int = Field(description="FIELD_SOURCE")

    got = AModel.model_json_schema().get("description")
    print("description winner:", got)
    assert got in ("DOCSTRING_SOURCE", "FIELD_SOURCE"), "description 变成了第三种值：%r" % (got,)


# ==========================================================================
# 护栏：修复不得波及非 RootModel、嵌套引用与 json_schema_extra 分支
# ==========================================================================
def test_guard_plain_basemodel_docstring_unaffected():
    """普通 BaseModel 的 docstring → 仍写进 model 级 description。三态都 PASS。"""
    class AModel(BaseModel):
        """Plain model docstring"""

        x: int

    schema = AModel.model_json_schema()
    assert schema["description"] == "Plain model docstring"


def test_guard_plain_basemodel_field_description_stays_on_property():
    """普通 BaseModel 上 Field 的 description 属于**属性级**，不应升到 model 级。三态都 PASS。

    这条保证"把 root field 的 description 提到 model 级"这个改动没有泄漏到普通模型。
    """
    class AModel(BaseModel):
        x: int = Field(description="field level")

    schema = AModel.model_json_schema()
    assert schema["properties"]["x"]["description"] == "field level"
    assert "description" not in schema, "属性级描述被提升到了 model 级：%r" % (schema,)


def test_guard_nested_root_model_description_lands_on_definition():
    """RootModel 作为别的模型的字段时（走 `$ref`/`$defs` 路径），description 应落在定义上。

    base FAIL（没有 description），gold PASS，candidate **需实测**：
    候选写的是 `_update_class_schema` 里 `$ref` 解析后的 `schema_to_update`，
    理论上也应落在 `$defs` 里，但这是两条不同的实现路径，值得单独固定下来。
    """
    class Inner(RootModel):
        root: int = Field(description="inner desc")

    class Outer(BaseModel):
        inner: Inner

    schema = Outer.model_json_schema()
    defs = schema.get("$defs", {})
    assert "Inner" in defs, "没有生成 Inner 定义：%r" % (schema,)
    assert defs["Inner"].get("description") == "inner desc", (
        "嵌套 RootModel 的 description 没落在定义上：%r" % (defs["Inner"],)
    )


def test_guard_root_field_json_schema_extra_still_applies():
    """root field 的 `json_schema_extra` 仍然生效。三态都 PASS。

    候选改写了这段分支（把 `cls.model_fields['root']` 提成局部变量），需要确认没改坏。
    """
    class AModel(RootModel):
        root: int = Field(json_schema_extra={"examples": [1, 2]})

    schema = AModel.model_json_schema()
    assert schema.get("examples") == [1, 2]


def test_guard_both_json_schema_extra_sources_still_raise():
    """model_config 与 root field 同时设 json_schema_extra 仍应报 ValueError。三态都 PASS。"""
    class AModel(RootModel):
        model_config = {"json_schema_extra": {"a": 1}}
        root: int = Field(json_schema_extra={"b": 2})

    with pytest.raises(ValueError, match="must not be set simultaneously"):
        AModel.model_json_schema()


def test_guard_json_schema_extra_can_still_override_description():
    """`json_schema_extra` 在最后 update，应能覆盖任何来源的 description。三态都 PASS。

    这条界定了候选改动的插入位置：description 必须写在 json_schema_extra 之前。
    """
    class AModel(RootModel):
        """docstring desc"""

        root: int = Field(json_schema_extra={"description": "extra desc"})

    assert AModel.model_json_schema().get("description") == "extra desc"
