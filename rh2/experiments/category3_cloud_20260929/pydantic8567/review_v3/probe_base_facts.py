"""Quick base facts (no candidate): metadata order for Field defaults, StrictBool + PV, docs ordering example."""
import warnings
from typing_extensions import Annotated
from pydantic import BaseModel, Field, PlainValidator, PlainSerializer, StrictBool, PositiveInt
from pydantic.functional_validators import AfterValidator


def show(label, fn):
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            r = fn()
        print(f'{label}: {r!r}' + (f'  [warnings: {len(w)}]' if w else ''))
    except Exception as e:
        print(f'{label}: EXC {type(e).__name__}: {str(e).splitlines()[0][:120]}')


class M1(BaseModel):
    a: Annotated[int, PlainValidator(lambda v: int(v))] = Field(gt=0)
    b: Annotated[bool, PlainValidator(lambda v: bool(int(v)))] = Field(strict=True)
    c: Annotated[int, PlainSerializer(str), Field(ge=0), PlainValidator(lambda v: int(v))]

print('metadata a:', M1.model_fields['a'].metadata)
print('metadata b:', M1.model_fields['b'].metadata)
print('metadata c:', M1.model_fields['c'].metadata)
show('M1(a=-5,b="1",c=-3)', lambda: M1(a=-5, b='1', c=-3).model_dump())


def mk_strict():
    class S(BaseModel):
        z: Annotated[StrictBool, PlainValidator(lambda v: bool(int(v)))]
    return S(z='1').z
show('StrictBool+PV', mk_strict)


def mk_pos():
    class P(BaseModel):
        z: Annotated[PositiveInt, PlainValidator(lambda v: int(v))]
    return P(z='-5').z
show('PositiveInt+PV(-5)', mk_pos)
