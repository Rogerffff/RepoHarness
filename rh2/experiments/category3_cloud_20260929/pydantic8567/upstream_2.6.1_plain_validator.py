# 上游佐证（不是公开依据）：PyPI pydantic 2.6.1 wheel 中 PlainValidator.__get_pydantic_core_schema__ 原文。
# wheel sha256 0b6a909df3192245cb736509a92ff69e4fef76116feffec68e93a567347bae6f；同一方法在 2.6.4、2.7.0、2.8.0 wheel 中逐字相同；2.6.0 与 gold 相同；2.10.0 起改写但保留同一 catch。
# changelog（2.6.1 METADATA）：Fix unsupported types bug with `PlainValidator` (#8710)。

    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Note that for some valid uses of PlainValidator, it is not possible to generate a core schema for the
        # source_type, so calling `handler(source_type)` will error, which prevents us from generating a proper
        # serialization schema. To work around this for use cases that will not involve serialization, we simply
        # catch any PydanticSchemaGenerationError that may be raised while attempting to build the serialization schema
        # and abort any attempts to handle special serialization.
        from pydantic import PydanticSchemaGenerationError

        try:
            schema = handler(source_type)
            serialization = core_schema.wrap_serializer_function_ser_schema(function=lambda v, h: h(v), schema=schema)
        except PydanticSchemaGenerationError:
            serialization = None

        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(
                func, field_name=handler.field_name, serialization=serialization
            )
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func, serialization=serialization)

