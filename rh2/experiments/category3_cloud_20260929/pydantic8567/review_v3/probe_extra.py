"""v3 聚焦复核的补充行为项（不套测试补丁）：题面布局 `[serializer, PlainValidator]` 左侧再有约束（常见来源：
`= Field(gt=...)` 默认值、`StrictBool`/`PositiveInt` 这类带约束的别名），以及 PV 字段的 JSON Schema（旧行为）。
输出格式同 probe_matrix.py。
"""
import json
import warnings

from typing_extensions import Annotated

from pydantic import BaseModel, Field, PlainSerializer, PositiveInt, StrictBool, TypeAdapter
from pydantic.functional_validators import PlainValidator

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


hashser = PlainSerializer(lambda v: f'#{v}')


@case('S24_field_default_gt_then_ser_pv')
def _():
    class M(BaseModel):
        x: Annotated[int, hashser, PlainValidator(lambda v: int(v))] = Field(gt=0)

    m = M(x='-5')
    return [M.model_fields['x'].metadata[0].__class__.__name__, m.x, m.model_dump(), m.model_dump_json()]


@case('S25_strictbool_ser_pv')
def _():
    class M(BaseModel):
        z: Annotated[StrictBool, PlainSerializer(lambda x: str(int(x)), return_type=str), PlainValidator(lambda x: bool(int(x)))]

    m = M(z='1')
    return [m.z, m.model_dump(), m.model_dump_json()]


@case('S26_positiveint_ser_pv')
def _():
    class M(BaseModel):
        z: Annotated[PositiveInt, hashser, PlainValidator(lambda v: int(v))]

    m = M(z='-5')
    return [m.z, m.model_dump()]


@case('S27_pv_json_schema_validation_mode')
def _():
    return TypeAdapter(Annotated[int, PlainValidator(lambda v: int(v))]).json_schema()


for r in RESULTS:
    print('RH2PROBE ' + json.dumps(r, default=repr, ensure_ascii=False))
