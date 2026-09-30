"""v3 聚焦复核：在 base 上逐字替换生成复核者候选补丁（在容器 /testbed 内运行，输出 git diff）。

用法（容器内）：python make_candidates.py <输出目录>
每个候选先 `git checkout -- pydantic tests` 复位，再做逐字替换，最后 `git diff` 存为 <名字>.patch。

合理实现（ok_*，与 gold、upstream261、c3_reorder、rv_condwrap 机制都不同）：
- ok_serdig：PV 内生成内层 schema，沿 function-before/after/wrap 的 `schema` 链找第一个 `serialization` 直接沿用；生成失败则不设。
- ok_wrapshim：PV 生成内层 schema 时，改用“从不调用 handler 的 wrap 验证器”包住内层 schema：验证只跑 PV 函数，
  序列化自然沿用内层 schema；内层生成失败则退回原来的 plain 验证器。
- ok_up210：按上游 2.10 的写法回移：内层 schema 顶层有 `serialization` 就直接用，否则用 wrap serializer 委托内层；
  生成失败则不设（2.6 无 json_schema_input_type，省略该参数）。
- ok_pv_first_keep_sers：把最后一个 PV 挪到最内层，但只保留其左侧的 serializer（按原顺序放在 PV 紧外层），
  其余左侧元数据本来就被 PV 取代、从不求值，直接丢掉（语义与 c3_reorder 相同，写法是“PV 挪到最内层”）。
- ok_post_attach：在 `_apply_annotations` 生成完整 schema 后，若最后一个 PV 左侧有 PlainSerializer/WrapSerializer、
  且外层（沿 function-before/after/wrap 往里看）没有 `serialization`，再把这些 serializer 依次套到最外层。

首轮复核候选的重建：
- rv_before_sem_rebuilt：按首轮 review.md §1 的描述重建：内层 schema 能生成时 PV 退化为 before 语义（先跑函数再跑内层验证）。

错误候选（bad_*）：
- bad_swap_adjacent：只在 serializer 紧挨 PV 左侧时两者互换（非紧挨时不处理）。
- bad_swap_nearest：把最后一个 PV 与其左侧最近的 serializer 互换（两者之间的元数据被换到 PV 外层）。
- bad_pv_before_first_ser：把最后一个 PV 挪到其左侧第一个 serializer 之前（夹在中间的元数据被挪到 PV 外层）。
- bad_pv_first_skip_validators：把 PV 挪到最内层，并丢掉原本在其左侧的 Before/After/Wrap/Plain 验证器（约束等其它元数据保留并包在 PV 外面）。
- bad_pv_first_skip_after：把 PV 挪到最内层，只丢掉其左侧的 AfterValidator。
- bad_nonvalidators_after_pv：把 PV 左侧所有“非验证器”元数据（serializer、约束、WithJsonSchema 等）挪到 PV 紧后。
- bad_pv_first_if_only_sers：只有当 PV 左侧全是 serializer 时才把 PV 挪到最内层；左侧还有别的元数据
  （验证器、约束）时不处理，serializer 仍被丢弃（保守的部分修复）。
- bad_rewrap_noinfo：从注解里取出 PV 左侧的 PlainSerializer，生成完 schema 后按“无 info 参数”重建序列化（丢掉 info_arg）。
"""
import subprocess
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
FV = Path('/testbed/pydantic/functional_validators.py')
GS = Path('/testbed/pydantic/_internal/_generate_schema.py')

PV_OLD = """    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(func, field_name=handler.field_name)
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func)
"""

PV_TAIL_WITH_SER = """        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(
                func, field_name=handler.field_name, serialization=serialization
            )
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func, serialization=serialization)
"""

PV_NEW = {
    'ok_serdig': """    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # The plain validator replaces the inner validation, but a serializer set by the inner annotations
        # (for instance a `PlainSerializer` placed before this validator) is still used: look for it through
        # the validator functions wrapping the inner schema.
        from .errors import PydanticSchemaGenerationError

        serialization = None
        try:
            inner: Any = handler(source_type)
        except PydanticSchemaGenerationError:
            inner = None
        while isinstance(inner, dict):
            if 'serialization' in inner:
                serialization = inner['serialization']
                break
            if inner.get('type') in ('function-before', 'function-after', 'function-wrap'):
                inner = inner.get('schema')
            else:
                inner = None
"""
    + PV_TAIL_WITH_SER,
    'ok_wrapshim': """    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Validate with the plain function only (the inner validator is never called), while serialization
        # follows the inner schema, so that serializers from the inner annotations are kept.
        from .errors import PydanticSchemaGenerationError

        try:
            inner = handler(source_type)
        except PydanticSchemaGenerationError:
            inner = None
        info_arg = _inspect_validator(self.func, 'plain')
        if inner is not None:
            if info_arg:
                with_info = cast(core_schema.WithInfoValidatorFunction, self.func)
                return core_schema.with_info_wrap_validator_function(
                    lambda v, _handler, info: with_info(v, info), inner, field_name=handler.field_name
                )
            no_info = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_wrap_validator_function(lambda v, _handler: no_info(v), inner)
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(func, field_name=handler.field_name)
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func)
""",
    'ok_up210': """    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Backport of the pydantic 2.10 approach: reuse the inner serialization if there is one at the top level,
        # otherwise delegate serialization to the inner schema; types without a schema keep working without it.
        from .errors import PydanticSchemaGenerationError

        try:
            schema = handler(source_type)
            serialization = schema.get(
                'serialization',
                core_schema.wrap_serializer_function_ser_schema(
                    function=lambda v, h: h(v),
                    schema=schema,
                    return_schema=handler.generate_schema(source_type),
                ),
            )
        except PydanticSchemaGenerationError:
            serialization = None
"""
    + PV_TAIL_WITH_SER,
    'rv_before_sem_rebuilt': """    def __get_pydantic_core_schema__(self, source_type: Any, handler: _GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # (rebuild of the first review's rv_before_sem) when the inner schema can be generated, run the function
        # first and then the inner validation (before-validator semantics); otherwise keep the plain validator.
        from .errors import PydanticSchemaGenerationError

        try:
            inner = handler(source_type)
        except PydanticSchemaGenerationError:
            inner = None
        info_arg = _inspect_validator(self.func, 'plain')
        if inner is not None:
            if info_arg:
                with_info = cast(core_schema.WithInfoValidatorFunction, self.func)
                return core_schema.with_info_before_validator_function(with_info, inner, field_name=handler.field_name)
            no_info = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_before_validator_function(no_info, inner)
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(func, field_name=handler.field_name)
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(func)
""",
}

GS_ANCHOR = """        res = self._get_prepare_pydantic_annotations_for_known_type(source_type, tuple(annotations))
        if res is not None:
            source_type, annotations = res
"""
GS_FUNC_ANCHOR = """def apply_validators(
    schema: core_schema.CoreSchema,"""

REORDER_HELPERS = {
    'bad_swap_adjacent': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Swap a serializer placed right before a plain validator with it."""
    from ..functional_serializers import PlainSerializer, WrapSerializer
    from ..functional_validators import PlainValidator

    annotations = list(annotations)
    for i in range(len(annotations) - 1):
        if isinstance(annotations[i], (PlainSerializer, WrapSerializer)) and isinstance(
            annotations[i + 1], PlainValidator
        ):
            annotations[i], annotations[i + 1] = annotations[i + 1], annotations[i]
    return annotations


''',
    'bad_swap_nearest': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Swap the last plain validator with the nearest serializer on its left."""
    from ..functional_serializers import PlainSerializer, WrapSerializer
    from ..functional_validators import PlainValidator

    annotations = list(annotations)
    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    for j in range(i - 1, -1, -1):
        if isinstance(annotations[j], (PlainSerializer, WrapSerializer)):
            annotations[i], annotations[j] = annotations[j], annotations[i]
            break
    return annotations


''',
    'bad_pv_before_first_ser': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Move the last plain validator right before the first serializer on its left."""
    from ..functional_serializers import PlainSerializer, WrapSerializer
    from ..functional_validators import PlainValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    sers = [j for j in range(i) if isinstance(annotations[j], (PlainSerializer, WrapSerializer))]
    if not sers:
        return annotations
    j = sers[0]
    return annotations[:j] + [annotations[i]] + annotations[j:i] + annotations[i + 1 :]


''',
    'bad_pv_first_skip_validators': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Put the last plain validator innermost; validators on its left are replaced by it, so drop them."""
    from ..functional_validators import AfterValidator, BeforeValidator, PlainValidator, WrapValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    validators = (AfterValidator, BeforeValidator, PlainValidator, WrapValidator)
    kept = [a for a in annotations[:i] if not isinstance(a, validators)]
    return [annotations[i]] + kept + annotations[i + 1 :]


''',
    'bad_pv_first_skip_after': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Put the last plain validator innermost; drop the after validators on its left."""
    from ..functional_validators import AfterValidator, PlainValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    kept = [a for a in annotations[:i] if not isinstance(a, AfterValidator)]
    return [annotations[i]] + kept + annotations[i + 1 :]


''',
    'bad_nonvalidators_after_pv': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """A plain validator drops everything on its left: move the non-validator metadata right after it."""
    from ..functional_validators import AfterValidator, BeforeValidator, PlainValidator, WrapValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    validators = (AfterValidator, BeforeValidator, PlainValidator, WrapValidator)
    before = annotations[:i]
    moved = [a for a in before if not isinstance(a, validators)]
    if not moved:
        return annotations
    kept = [a for a in before if isinstance(a, validators)]
    return kept + [annotations[i]] + moved + annotations[i + 1 :]


''',
    'bad_pv_first_if_only_sers': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Put the last plain validator innermost, but only when everything on its left is a serializer."""
    from ..functional_serializers import PlainSerializer, WrapSerializer
    from ..functional_validators import PlainValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    before = annotations[:i]
    if not before or not all(isinstance(a, (PlainSerializer, WrapSerializer)) for a in before):
        return annotations
    return [annotations[i]] + before + annotations[i + 1 :]


''',
    'ok_pv_first_keep_sers': '''def _c3rv_reorder(annotations: list[Any]) -> list[Any]:
    """Put the last plain validator innermost. Everything else on its left is replaced by it (never evaluated),
    except the serializers, which are kept (in order) right outside it."""
    from ..functional_serializers import PlainSerializer, WrapSerializer
    from ..functional_validators import PlainValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations
    i = plain[-1]
    sers = [a for a in annotations[:i] if isinstance(a, (PlainSerializer, WrapSerializer))]
    return [annotations[i]] + sers + annotations[i + 1 :]


''',
}

POST_OLD = """        schema = get_inner_schema(source_type)
        if pydantic_js_annotation_functions:
"""
POST_NEW = """        schema = get_inner_schema(source_type)
        schema = self._c3rv_reattach_serializers(source_type, annotations, schema)
        if pydantic_js_annotation_functions:
"""
METHOD_ANCHOR = """    def _apply_single_annotation(self, schema: core_schema.CoreSchema, metadata: Any) -> core_schema.CoreSchema:
"""
POST_METHOD = '''    def _c3rv_reattach_serializers(
        self, source_type: Any, annotations: list[Any], schema: core_schema.CoreSchema
    ) -> core_schema.CoreSchema:
        """A plain validator does not call the inner schema, so serializers placed before it are dropped:
        apply them on top of the final schema, unless an outer serializer is already set."""
        from ..functional_serializers import PlainSerializer, WrapSerializer
        from ..functional_validators import PlainValidator

        plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
        if not plain:
            return schema
        outer: Any = schema
        while isinstance(outer, dict):
            if 'serialization' in outer:
                return schema
            outer = outer.get('schema') if outer.get('type') in ('function-before', 'function-after', 'function-wrap') else None
        dropped = [a for a in annotations[: plain[-1]] if isinstance(a, (PlainSerializer, WrapSerializer))]
        for ser in dropped:
            current = schema
            schema = ser.__get_pydantic_core_schema__(
                source_type, CallbackGetCoreSchemaHandler(lambda _source, s=current: s, self, ref_mode='unpack')
            )
        return schema

'''

REWRAP_ANCHOR_OLD = GS_ANCHOR
REWRAP_ANCHOR_NEW = GS_ANCHOR + """        annotations, c3rv_dropped = _c3rv_split_plain_serializers(annotations)
"""
REWRAP_POST_NEW = """        schema = get_inner_schema(source_type)
        for c3rv_ser in c3rv_dropped:
            schema['serialization'] = core_schema.plain_serializer_function_ser_schema(
                c3rv_ser.func, when_used=c3rv_ser.when_used
            )
        if pydantic_js_annotation_functions:
"""
REWRAP_HELPER = '''def _c3rv_split_plain_serializers(annotations: list[Any]) -> tuple[list[Any], list[Any]]:
    """Take out the plain serializers placed before the last plain validator (they would be dropped by it)."""
    from ..functional_serializers import PlainSerializer
    from ..functional_validators import PlainValidator

    plain = [i for i, a in enumerate(annotations) if isinstance(a, PlainValidator)]
    if not plain:
        return annotations, []
    i = plain[-1]
    dropped = [a for a in annotations[:i] if isinstance(a, PlainSerializer)]
    kept = [a for a in annotations[:i] if not isinstance(a, PlainSerializer)]
    return kept + annotations[i:], dropped


'''


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, cwd='/testbed', check=True, capture_output=True, text=True).stdout


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert text.count(old) == 1, (path, old[:60], text.count(old))
    path.write_text(text.replace(old, new))


def build(name: str) -> None:
    sh('git checkout -- pydantic tests')
    if name in PV_NEW:
        replace_once(FV, PV_OLD, PV_NEW[name])
    elif name in REORDER_HELPERS:
        replace_once(GS, GS_ANCHOR, GS_ANCHOR + '        annotations = _c3rv_reorder(annotations)\n')
        replace_once(GS, GS_FUNC_ANCHOR, REORDER_HELPERS[name] + GS_FUNC_ANCHOR)
    elif name == 'ok_post_attach':
        replace_once(GS, POST_OLD, POST_NEW)
        replace_once(GS, METHOD_ANCHOR, POST_METHOD + METHOD_ANCHOR)
    elif name == 'bad_rewrap_noinfo':
        replace_once(GS, REWRAP_ANCHOR_OLD, REWRAP_ANCHOR_NEW)
        replace_once(GS, POST_OLD, REWRAP_POST_NEW)
        replace_once(GS, GS_FUNC_ANCHOR, REWRAP_HELPER + GS_FUNC_ANCHOR)
    else:
        raise SystemExit(f'unknown candidate {name}')
    diff = sh('git diff -- pydantic')
    (OUT / f'{name}.patch').write_text(diff)
    sh('git checkout -- pydantic tests')
    # the patch must apply on a clean tree
    subprocess.run(['git', 'apply', '--check', str(OUT / f'{name}.patch')], cwd='/testbed', check=True)
    print(name, len(diff.splitlines()), 'lines')


NAMES = list(PV_NEW) + ['ok_post_attach'] + list(REORDER_HELPERS) + ['bad_rewrap_noinfo']
for n in NAMES:
    build(n)
