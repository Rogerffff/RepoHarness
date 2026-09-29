"""L7 判别用例 · pydantic__pydantic-6043

唯一的 F2P 只断言顶层 properties 的 key 顺序，所以"只对顶层 properties 排一次序"就满分。
gold 是递归排序整个 schema，并且对 generate_definitions() 的出口也排序。

三态预期：base 失败、gold 通过、fake 失败（嵌套 $defs 与 generate_definitions 出口都没排）。
"""
from pydantic import BaseModel


class _Inner(BaseModel):
    z: int
    a: int


class _Outer(BaseModel):
    y: _Inner
    b: int


def test_l7_nested_defs_properties_are_sorted():
    schema = _Outer.model_json_schema()
    inner = schema["$defs"]["_Inner"]
    assert list(inner["properties"].keys()) == ["a", "z"]


def test_l7_generate_definitions_output_is_sorted():
    from pydantic.json_schema import GenerateJsonSchema

    _, definitions = GenerateJsonSchema().generate_definitions(
        [(_Inner, "validation", _Inner.__pydantic_core_schema__)]
    )
    inner = next(iter(definitions.values()))
    assert list(inner["properties"].keys()) == ["a", "z"]
