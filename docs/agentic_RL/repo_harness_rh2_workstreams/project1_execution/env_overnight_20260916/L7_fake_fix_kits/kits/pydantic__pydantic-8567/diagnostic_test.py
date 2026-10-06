"""L7 判别用例 · pydantic__pydantic-8567

F2P 只断言 `isinstance(data['foo'], str)`，所以"给 PlainValidator 挂一个无条件 str()"
在类型上就满足了。gold 的语义是把 PlainSerializer 的结果接回来，值应当是 '0'/'1'。

三态预期：base 失败（序列化结果是 bool，不是 str）、gold 通过、fake 失败（值是 'True'/'False'）。
"""
from pydantic import BaseModel, PlainSerializer, PlainValidator
from typing_extensions import Annotated


def test_l7_plain_serializer_value_is_used():
    serializer = PlainSerializer(lambda x: str(int(x)), return_type=str)
    validator = PlainValidator(lambda x: bool(int(x)))

    class Blah(BaseModel):
        foo: Annotated[bool, validator, serializer]
        bar: Annotated[bool, serializer, validator]

    data = Blah(foo="0", bar="1").model_dump()
    assert data["foo"] == "0", data
    assert data["bar"] == "1", data
