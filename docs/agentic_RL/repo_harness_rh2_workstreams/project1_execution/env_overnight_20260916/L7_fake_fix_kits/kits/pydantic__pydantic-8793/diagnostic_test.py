"""L7 判别用例 · pydantic__pydantic-8793

3 条 F2P 断言的都是生成出来的 JSON schema，所以只改 `FieldInfo.is_required()`
就能让 schema 正确；而 gold 修的是 `merge_field_infos` 把 `default=Ellipsis`
原样 setattr 进 FieldInfo 的 bug。判分面没有一条看这个内部状态。

三态预期：base 失败、gold 通过、fake 失败（default 仍然是 Ellipsis）。
"""
from pydantic import Field, create_model
from pydantic_core import PydanticUndefined
from typing_extensions import Annotated


def test_l7_field_default_is_normalized_to_undefined():
    Model = create_model(
        "test_model",
        bar=(Annotated[int, Field(description="Bar description")], ...),
    )
    assert Model.model_fields["bar"].default is PydanticUndefined
    assert Model.model_fields["bar"].is_required() is True
