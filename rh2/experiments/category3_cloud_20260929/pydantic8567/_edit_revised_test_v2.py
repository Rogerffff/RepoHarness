# 在原 test_patch 应用后的 tests/test_validators.py 上改（R-c 草案 v2，测试 ID 不变；v2 = v1 + 第 1b 项）：
# 1) 题面示例：核内部验证值、Python 与 JSON 的精确输出（T2a）；
# 1b) 同一注解类型不作模型字段直接使用（TypeAdapter + List 嵌套，文档 validators.md 的用法）（T2c，路径子集）；
# 2) 非示例实例：另一类型与 serializer（文档 FancyInt，when_used='json'）、带 info 的 PlainValidator、三项元数据（T2c）；
# 3) 回归：PlainValidator 接管 pydantic 无 schema 的普通类（默认配置），类能建成、验证函数生效、Python dump 原样返回（G1→S1）。
from pathlib import Path

p = Path("tests/test_validators.py")
s = p.read_text()

old_import = "    ValidatorFunctionWrapHandler,\n    errors,\n"
assert s.count(old_import) == 1
s = s.replace(old_import, "    ValidatorFunctionWrapHandler,\n    WithJsonSchema,\n    errors,\n")

old_tail = '''    blah = Blah(foo='0', bar='1')
    data = blah.model_dump()
    assert isinstance(data['foo'], ser_type)
    assert isinstance(data['bar'], ser_type)
'''
assert s.endswith(old_tail), s[-300:]
s = s[: -len(old_tail)] + old_tail + '''
    # Whatever its position, the serializer is used, in python and in JSON mode; validation is unchanged.
    assert blah.foo is False
    assert blah.bar is True
    assert data == {'foo': '0', 'bar': '1'}
    assert blah.model_dump_json() == '{"foo":"0","bar":"1"}'

    # The annotated type also works outside a model field, e.g. for the items of a list.
    ta = TypeAdapter(List[Annotated[bool, serializer, validator]])
    assert ta.validate_python(['0', '1']) == [False, True]
    assert ta.dump_json([False, True]) == b'["0","1"]'

    # Same with another type and serializer (`when_used='json'`), a validator taking `info`,
    # and a JSON schema given for the plain validator.
    class Other(BaseModel):
        x: Annotated[
            int,
            PlainSerializer(lambda x: f'{x:,}', return_type=str, when_used='json'),
            PlainValidator(lambda v, info: int(v)),
            WithJsonSchema({'type': 'integer'}, mode='validation'),
        ]

    other = Other(x='1234')
    assert other.x == 1234
    assert other.model_dump() == {'x': 1234}
    assert other.model_dump_json() == '{"x":"1,234"}'

    # A plain validator replaces the inner validation logic, so it keeps working for a type
    # pydantic cannot generate a schema for.
    class Unsupported:
        pass

    class WithUnsupported(BaseModel):
        u: Annotated[Unsupported, PlainValidator(lambda v: Unsupported())]

    m = WithUnsupported(u='abc')
    assert isinstance(m.u, Unsupported)
    assert isinstance(m.model_dump()['u'], Unsupported)
'''
p.write_text(s)
print("ok revised v2")
