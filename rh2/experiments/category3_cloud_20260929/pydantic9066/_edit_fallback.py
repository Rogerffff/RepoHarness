# 替代正对照：原本能编码的默认值走原路径（字节级不变）；只有 to_jsonable_python 抛序列化错误时，
# 才用该值自身类型的 TypeAdapter（不传 config，避免 BaseModel/dataclass/TypedDict 的 type-adapter-config-unused）
# 以 JSON 模式导出；导出也失败则抛回原错误，由 default_schema 照旧警告并排除默认值。
from pathlib import Path
p = Path("pydantic/json_schema.py")
s = p.read_text()
old = '''        config = self._config
        return pydantic_core.to_jsonable_python(
            dft,
            timedelta_mode=config.ser_json_timedelta,
            bytes_mode=config.ser_json_bytes,
        )
'''
assert s.count(old) == 1
new = '''        config = self._config
        try:
            return pydantic_core.to_jsonable_python(
                dft,
                timedelta_mode=config.ser_json_timedelta,
                bytes_mode=config.ser_json_bytes,
            )
        except pydantic_core.PydanticSerializationError as exc:
            # Values such as `ipaddress` objects are not handled by the generic serializer, but
            # pydantic knows how to serialize them via a schema for their own type.
            from .type_adapter import TypeAdapter

            try:
                encoded = TypeAdapter(type(dft)).dump_python(dft, mode='json')
            except (PydanticSchemaGenerationError, PydanticUserError, pydantic_core.PydanticSerializationError):
                raise exc from None
            return pydantic_core.to_jsonable_python(
                encoded,
                timedelta_mode=config.ser_json_timedelta,
                bytes_mode=config.ser_json_bytes,
            )
'''
s = s.replace(old, new)
old_imp = "from .errors import PydanticInvalidForJsonSchema, PydanticUserError\n"
assert s.count(old_imp) == 1
s = s.replace(old_imp, "from .errors import PydanticInvalidForJsonSchema, PydanticSchemaGenerationError, PydanticUserError\n")
p.write_text(s)
