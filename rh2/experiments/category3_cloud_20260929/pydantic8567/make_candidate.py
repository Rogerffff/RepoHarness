"""pydantic-8567 候选构造（私有，不交给求解者）。在 /testbed 的 base 源码上按候选名做逐字替换。

用法（容器内，工作目录 /testbed）：python /in/make_candidate.py <候选名>
正对照：c3_serpass（本页替代正对照，待他人核实）、upstream261（上游 2.6.1 #8710 写法）、c3_reorder（改在注解排序处，查误拒）。
错误候选：gold 之外的 n_* 都是为检验测试强度构造的退化或部分修复，不是合理实现。
"""
import sys
from pathlib import Path

FV = Path("pydantic/functional_validators.py")
GS = Path("pydantic/_internal/_generate_schema.py")
FS = Path("pydantic/functional_serializers.py")

BASE_PLAIN = '''    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(func, field_name=handler.field_name)
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func)
'''

# 两个分支都把 serialization 传下去（gold 与多数候选共用的尾部）
TAIL_BOTH = '''        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(
                func, field_name=handler.field_name, serialization=serialization
            )
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func, serialization=serialization)
'''

HEAD = '''    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
'''

PLAIN = {
    # 本页替代正对照：只沿用内层注解已经设定的 serialization；源类型无 schema 时不需要它，保持 base 行为
    "c3_serpass": HEAD + '''        # A plain validator replaces the inner validation logic, but a serializer set by the inner annotations
        # (e.g. a `PlainSerializer` placed before this validator) must still be used. The inner schema is only
        # generated to find that serializer: types pydantic cannot generate a schema for stay usable here.
        from .errors import PydanticSchemaGenerationError

        try:
            serialization = handler(source_type).get('serialization')
        except PydanticSchemaGenerationError:
            serialization = None
''' + TAIL_BOTH,
    # 上游 2.6.1（#8710）PlainValidator.__get_pydantic_core_schema__ 方法体逐字（见 upstream_2.6.1_plain_validator.py）
    "upstream261": HEAD + '''        # Note that for some valid uses of PlainValidator, it is not possible to generate a core schema for the
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

''' + TAIL_BOTH,
    # 固定结果（§4 第 3 步退化方向）：不看用户的 serializer，一律 str(v)
    "n_const_str": HEAD + '''        serialization = core_schema.plain_serializer_function_ser_schema(str)
''' + TAIL_BOTH,
    # 模式子集：只在 python 模式委托内层序列化，JSON 模式按推断输出原值
    "n_python_only": HEAD + '''        schema = handler(source_type)
        serialization = core_schema.wrap_serializer_function_ser_schema(
            function=lambda v, h, info: h(v) if info.mode == 'python' else v, schema=schema, info_arg=True
        )
''' + TAIL_BOTH,
    # 示例字面值：只在源类型为 bool（题面示例）时走 gold 逻辑
    "n_bool_only": HEAD + '''        serialization = None
        if source_type is bool:
            schema = handler(source_type)
            serialization = core_schema.wrap_serializer_function_ser_schema(function=lambda v, h: h(v), schema=schema)
''' + TAIL_BOTH,
    # 路径子集：只改 no-info 分支（题面示例的 lambda 不带 info）
    "n_noinfo_only": HEAD + '''        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(func, field_name=handler.field_name)
        else:
            schema = handler(source_type)
            serialization = core_schema.wrap_serializer_function_ser_schema(function=lambda v, h: h(v), schema=schema)
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func, serialization=serialization)
''',
    # 吞掉错误：内层 schema 生成失败时退成 any_schema，类能建成，但 plain 验证函数被静默丢掉
    "n_swallow_to_any": HEAD + '''        from .errors import PydanticSchemaGenerationError

        try:
            schema = handler(source_type)
        except PydanticSchemaGenerationError:
            return core_schema.any_schema()
        serialization = core_schema.wrap_serializer_function_ser_schema(function=lambda v, h: h(v), schema=schema)
''' + TAIL_BOTH,
    # 形态子集：取出内层 plain serializer 的函数重新包装，丢掉 when_used 等选项
    "n_when_used_lost": HEAD + '''        from .errors import PydanticSchemaGenerationError

        try:
            inner = handler(source_type).get('serialization')
        except PydanticSchemaGenerationError:
            inner = None
        serialization = None
        if inner is not None and inner['type'] == 'function-plain':
            serialization = core_schema.plain_serializer_function_ser_schema(
                inner['function'], info_arg=inner.get('info_arg'), return_schema=inner.get('return_schema')
            )
''' + TAIL_BOTH,
    # 依赖执行顺序：PlainValidator 不调 handler，而是取“最近一次建过的 PlainSerializer”的序列化（全局登记）
    "n_order_registry": HEAD + '''        from .functional_serializers import _LAST_SERIALIZATION

        serialization = _LAST_SERIALIZATION[0]
''' + TAIL_BOTH,
}

GS_ANCHOR = '''        res = self._get_prepare_pydantic_annotations_for_known_type(source_type, tuple(annotations))
        if res is not None:
            source_type, annotations = res

        pydantic_js_annotation_functions: list[GetJsonSchemaFunction] = []
'''

REORDER_HELPER = '''

def _move_serializers_after_plain_validator(annotations: list[Any]) -> list[Any]:
    """A `PlainValidator` replaces the inner schema, so annotated serializers placed before it would be dropped.

    Move them right after the (last) plain validator, keeping their relative order.
    """
    from ..functional_serializers import PlainSerializer, WrapSerializer
    from ..functional_validators import PlainValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    last = plain[-1]
    before = annotations[:last]
    moved = [a for a in before if isinstance(a, (PlainSerializer, WrapSerializer))]
    if not moved:
        return annotations
    kept = [a for a in before if not isinstance(a, (PlainSerializer, WrapSerializer))]
    return kept + [annotations[last]] + moved + annotations[last + 1 :]
'''

REORDER_CALL = {
    # 查误拒用的合理替代：在注解排序处把 PlainValidator 之前的 serializer 移到它之后
    "c3_reorder": "            source_type, annotations = res\n        annotations = _move_serializers_after_plain_validator(annotations)\n",
    # 阈值/规模子集：只在 Annotated 元数据恰为两项（题面形态）时交换
    "n_two_items": ("            source_type, annotations = res\n"
                    "        if len(annotations) == 2:\n"
                    "            annotations = _move_serializers_after_plain_validator(annotations)\n"),
}


def sub(path: Path, old: str, new: str) -> None:
    s = path.read_text()
    assert s.count(old) == 1, (path, old[:80])
    path.write_text(s.replace(old, new))


name = sys.argv[1]
if name in PLAIN:
    sub(FV, BASE_PLAIN, PLAIN[name])
    if name == "n_order_registry":
        sub(FS, '''from .annotated_handlers import GetCoreSchemaHandler
''', '''from .annotated_handlers import GetCoreSchemaHandler

_LAST_SERIALIZATION: list = [None]
''')
        sub(FS, '''            return_schema=return_schema,
            when_used=self.when_used,
        )
        return schema


@dataclasses.dataclass(**_internal_dataclass.slots_true, frozen=True)
class WrapSerializer:''', '''            return_schema=return_schema,
            when_used=self.when_used,
        )
        _LAST_SERIALIZATION[0] = schema['serialization']
        return schema


@dataclasses.dataclass(**_internal_dataclass.slots_true, frozen=True)
class WrapSerializer:''')
elif name in REORDER_CALL:
    sub(GS, "            source_type, annotations = res\n\n        pydantic_js_annotation_functions: list[GetJsonSchemaFunction] = []\n",
        REORDER_CALL[name] + "\n        pydantic_js_annotation_functions: list[GetJsonSchemaFunction] = []\n")
    s = GS.read_text()
    anchor = "\n\ndef apply_validators("
    assert s.count(anchor) == 1
    GS.write_text(s.replace(anchor, REORDER_HELPER + anchor))
else:
    raise SystemExit(f"unknown candidate {name}")
print("ok", name)
