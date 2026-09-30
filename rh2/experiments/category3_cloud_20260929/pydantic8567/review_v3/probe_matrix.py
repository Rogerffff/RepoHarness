"""v3 聚焦复核的私有行为矩阵（不套测试补丁，在已套候选补丁的 /testbed 上运行）。

每项单独捕获异常与警告，输出一行 JSON：{"id": ..., "got": ..., "warn": n}。期望值按公开要求写在
summarize.py 里（题面、`docs/concepts/validators.md`、`PlainValidator` docstring、base 行为），不以 gold 为答案。
"""
import json
import sys
import warnings
from typing import List, Optional

from typing_extensions import Annotated

from pydantic import (
    BaseModel,
    Field,
    PlainSerializer,
    PositiveInt,
    StrictBool,
    TypeAdapter,
    WithJsonSchema,
    WrapSerializer,
)
from pydantic.functional_validators import AfterValidator, BeforeValidator, PlainValidator, WrapValidator

RESULTS = []


def case(cid):
    def deco(fn):
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                got = fn()
            RESULTS.append({'id': cid, 'got': got, 'warn': len(w)})
        except BaseException as e:  # noqa: BLE001
            RESULTS.append({'id': cid, 'got': f'EXC {type(e).__name__}: {str(e).splitlines()[0][:100] if str(e) else ""}', 'warn': 0})
        return fn

    return deco


ser = PlainSerializer(lambda x: str(int(x)), return_type=str)
val = PlainValidator(lambda x: bool(int(x)))


@case('S01_issue_example')
def _():
    BWrong = Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str), PlainValidator(lambda x: bool(int(x)))]
    BRight = Annotated[bool, PlainValidator(lambda x: bool(int(x))), PlainSerializer(lambda x: str(int(x)), return_type=str)]

    class Blah(BaseModel):
        x: BRight
        y: BWrong

    b = Blah(x=0, y=1)
    return [b.x, b.y, b.model_dump(), b.model_dump(mode='json'), b.model_dump_json()]


@case('S02_docs_validator_ordering')
def _():
    # docs/concepts/validators.md:137-263, field y only (x has no plain validator)
    logs = []

    def mk(label):
        def v(value, info):
            logs.append(label)
            return value

        return v

    def mkw(label):
        def v(value, handler, info):
            logs.append(f'{label}: pre')
            r = handler(value)
            logs.append(f'{label}: post')
            return r

        return v

    class A(BaseModel):
        y: Annotated[
            str,
            BeforeValidator(mk('before-1')),
            AfterValidator(mk('after-1')),
            WrapValidator(mkw('wrap-1')),
            BeforeValidator(mk('before-2')),
            AfterValidator(mk('after-2')),
            WrapValidator(mkw('wrap-2')),
            PlainValidator(mk('plain')),
            BeforeValidator(mk('before-3')),
            AfterValidator(mk('after-3')),
            WrapValidator(mkw('wrap-3')),
            BeforeValidator(mk('before-4')),
            AfterValidator(mk('after-4')),
            WrapValidator(mkw('wrap-4')),
        ]

    A(y='def')
    return logs


@case('S03_strictbool_pv')
def _():
    class M(BaseModel):
        z: Annotated[StrictBool, PlainValidator(lambda v: bool(int(v)))]

    return M(z='1').z


@case('S04_positiveint_pv_minus5')
def _():
    class M(BaseModel):
        z: Annotated[PositiveInt, PlainValidator(lambda v: int(v))]

    return M(z='-5').z


@case('S05_field_default_gt_pv_minus5')
def _():
    class M(BaseModel):
        z: Annotated[int, PlainValidator(lambda v: int(v))] = Field(gt=0)

    return M(z='-5').z


@case('S06_field_default_strict_pv')
def _():
    class M(BaseModel):
        z: Annotated[bool, PlainValidator(lambda v: bool(int(v)))] = Field(strict=True)

    return M(z='1').z


@case('S07_field_default_maxlen_pv')
def _():
    class M(BaseModel):
        z: Annotated[str, PlainValidator(lambda v: v)] = Field(max_length=3)

    return M(z='abcdef').z


def _boom(v):
    raise RuntimeError('inner validator called')


def _boom_wrap(v, handler):
    raise RuntimeError('inner wrap validator called')


@case('S08v_A08_between_after_validation')
def _():
    class M(BaseModel):
        z: Annotated[int, PlainSerializer(lambda v: f'#{v}'), AfterValidator(_boom), PlainValidator(lambda v: int(v))]

    return M(z='7').z


@case('S08s_A08_between_after_dump')
def _():
    class M(BaseModel):
        z: Annotated[int, PlainSerializer(lambda v: f'#{v}'), AfterValidator(lambda v: v), PlainValidator(lambda v: int(v))]

    m = M(z='7')
    return [m.model_dump(), m.model_dump_json()]


@case('S09_before_left_of_ser_pv')
def _():
    class M(BaseModel):
        z: Annotated[bool, BeforeValidator(_boom), ser, val]

    m = M(z='1')
    return [m.z, m.model_dump()]


@case('S10_wrap_left_of_ser_pv')
def _():
    class M(BaseModel):
        z: Annotated[bool, WrapValidator(_boom_wrap), ser, val]

    m = M(z='1')
    return [m.z, m.model_dump()]


@case('S10b_after_left_of_ser_pv_v3shape')
def _():
    class M(BaseModel):
        z: Annotated[bool, AfterValidator(_boom), ser, val]

    m = M(z='1')
    return [m.z, m.model_dump()]


@case('S11_ser_withjsonschema_pv')
def _():
    class M(BaseModel):
        z: Annotated[bool, ser, WithJsonSchema({'type': 'integer'}), val]

    m = M(z='1')
    return [m.z, m.model_dump(), m.model_dump_json()]


@case('S12_ser_field_ge_pv')
def _():
    class M(BaseModel):
        c: Annotated[int, PlainSerializer(lambda v: f'#{v}'), Field(ge=0), PlainValidator(lambda v: int(v))]

    m = M(c='-3')
    return [m.c, m.model_dump()]


@case('S13v_nested_alias_ser_after_then_pv')
def _():
    def must_be_true(v):
        assert v is True, 'must be true'
        return v

    Alias = Annotated[bool, ser, AfterValidator(must_be_true)]

    class M(BaseModel):
        z: Annotated[Alias, val]

    m = M(z='0')
    return m.z


@case('S13s_nested_alias_ser_after_then_pv_dump')
def _():
    Alias = Annotated[bool, ser, AfterValidator(lambda v: v)]

    class M(BaseModel):
        z: Annotated[Alias, val]

    m = M(z='0')
    return [m.model_dump(), m.model_dump_json()]


@case('S14_info_serializer_before_pv')
def _():
    class M(BaseModel):
        z: Annotated[int, PlainSerializer(lambda v, info: f'{v}:{info.mode}'), PlainValidator(lambda v: int(v))]

    m = M(z='5')
    return [m.model_dump(), m.model_dump_json()]


@case('S15_unknown_type_pv')
def _():
    class Unsupported:
        pass

    class M(BaseModel):
        u: Annotated[Unsupported, PlainValidator(lambda v: Unsupported())]

    m = M(u='abc')
    return [type(m.u).__name__, type(m.model_dump()['u']).__name__]


@case('S16_both_sides_serializers')
def _():
    class M(BaseModel):
        z: Annotated[bool, PlainSerializer(lambda v: 'A'), val, PlainSerializer(lambda v: 'B')]

    return M(z='1').model_dump()


@case('S17_typeadapter_list')
def _():
    ta = TypeAdapter(List[Annotated[bool, ser, val]])
    return [ta.validate_python(['0', '1']), ta.dump_json([False, True]).decode()]


@case('S18_when_used_json_before_pv')
def _():
    class M(BaseModel):
        x: Annotated[int, PlainSerializer(lambda x: f'{x:,}', return_type=str, when_used='json'), PlainValidator(lambda v, info: int(v))]

    m = M(x='1234')
    return [m.model_dump(), m.model_dump_json()]


@case('S19_wrapserializer_before_pv')
def _():
    class M(BaseModel):
        z: Annotated[bool, WrapSerializer(lambda v, h: f'w{int(v)}'), val]

    return M(z='1').model_dump()


@case('S20_short_circuit')
def _():
    class M(BaseModel):
        z: Annotated[int, PlainValidator(lambda v: v)]

    return M(z='abc').z


@case('S21_optional')
def _():
    class M(BaseModel):
        z: Optional[Annotated[bool, ser, val]] = None

    return [M().model_dump(), M(z='1').model_dump()]


@case('S22_strictbool_after_ser_pv_v3fix_shape')
def _():
    class M(BaseModel):
        z: Annotated[StrictBool, AfterValidator(_boom), ser, val]

    m = M(z='1')
    return [m.z, m.model_dump()]


@case('S23_ser_strict_pv_between_nonwrapping')
def _():
    from pydantic import Strict

    class M(BaseModel):
        z: Annotated[bool, ser, Strict(), val]

    m = M(z='1')
    return [m.z, m.model_dump()]


for r in RESULTS:
    print('RH2PROBE ' + json.dumps(r, default=repr, ensure_ascii=False))
sys.stdout.flush()
