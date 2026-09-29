"""pydantic-8567 私有行为矩阵（不交给求解者）。每项独立捕获异常与警告，逐行输出 `CASE <id> <json>`。

A 组：题面核心要求（serializer 不因相对 PlainValidator 的位置而失效）及其非示例实例。
B 组：PlainValidator 的既有公开能力与相邻行为（无 serializer、未知类型、with-info、文档示例等）。
用法：python behavior.py [case_id ...]   （不给参数时按固定顺序跑全部）
注意：n_order_registry 候选依赖全局登记，结果与执行顺序有关；单独跑某项请给 case_id。
"""
import json
import sys
import traceback
import warnings
from typing import Any, Callable, List, Optional

import annotated_types
from pydantic_core import core_schema
from typing_extensions import Annotated

import pydantic
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainSerializer,
    PlainValidator,
    TypeAdapter,
    WithJsonSchema,
    WrapSerializer,
    WrapValidator,
    field_validator,
)


def short_exc(e: BaseException) -> dict:
    return {"exc": type(e).__name__, "code": getattr(e, "code", None), "msg": str(e).splitlines()[0][:200]}


def run(fn: Callable[[], Any]) -> dict:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            out = {"ok": fn()}
        except Exception as e:  # noqa: BLE001  每项独立：记录异常类型、code 与首行
            out = short_exc(e)
            out["where"] = traceback.extract_tb(e.__traceback__)[-1].name
    out["warnings"] = [f"{x.category.__name__}: {str(x.message).splitlines()[0][:160]}" for x in w]
    return out


def jsonable(v: Any) -> Any:
    try:
        json.dumps(v)
        return v
    except TypeError:
        return repr(v)


CASES = {}


def case(fn):
    CASES[fn.__name__] = fn
    return fn


def to_str01(x):
    return str(int(x))


# ---------------- A：题面核心要求 ----------------
@case
def A01_issue_example():
    BWrong = Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str), PlainValidator(lambda x: bool(int(x)))]
    BRight = Annotated[bool, PlainValidator(lambda x: bool(int(x))), PlainSerializer(lambda x: str(int(x)), return_type=str)]

    class Blah(BaseModel):
        x: BRight
        y: BWrong

    b = Blah(x=0, y=1)
    return {"internal": [b.x, b.y], "python": b.model_dump(), "json": b.model_dump_json(),
            "json_mode": b.model_dump(mode="json")}


@case
def A02_test_patch_shape():
    serializer = PlainSerializer(lambda x: str(int(x)), return_type=str)
    validator = PlainValidator(lambda x: bool(int(x)))

    class Blah(BaseModel):
        foo: Annotated[bool, validator, serializer]
        bar: Annotated[bool, serializer, validator]

    b = Blah(foo="0", bar="1")
    return {"internal": [b.foo, b.bar], "python": b.model_dump(), "json": b.model_dump_json()}


@case
def A03_type_adapter_wrong_order():
    ta = TypeAdapter(Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str), PlainValidator(lambda x: bool(int(x)))])
    v = ta.validate_python("1")
    return {"internal": v, "python": ta.dump_python(v), "json": ta.dump_json(v).decode()}


@case
def A04_fancyint_info_wrong_order():
    # 文档 serialization.md 的 FancyInt（when_used='json'）放在带 info 的 PlainValidator 之前；单字段模型
    class Other(BaseModel):
        x: Annotated[int, PlainSerializer(lambda x: f"{x:,}", return_type=str, when_used="json"), PlainValidator(lambda v, info: int(v))]

    o = Other(x="1234")
    return {"internal": o.x, "python": o.model_dump(), "json": o.model_dump_json()}


@case
def A05_int_noinfo_wrong_order_single_field():
    class One(BaseModel):
        n: Annotated[int, PlainSerializer(lambda x: x * 2), PlainValidator(lambda v: int(v) + 1)]

    o = One(n="4")
    return {"internal": o.n, "python": o.model_dump(), "json": o.model_dump_json()}


@case
def A06_info_field_name_wrong_order():
    class M(BaseModel):
        f: Annotated[str, PlainSerializer(lambda x: x.upper()), PlainValidator(lambda v, info: f"{info.field_name}:{v}")]

    m = M(f="a")
    return {"internal": m.f, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def A07_three_items_withjsonschema_between():
    class M(BaseModel):
        n: Annotated[int, PlainSerializer(lambda x: f"#{x}", return_type=str), WithJsonSchema({"type": "string"}), PlainValidator(lambda v: int(v))]

    m = M(n="7")
    return {"internal": m.n, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def A08_three_items_validator_between():
    class M(BaseModel):
        n: Annotated[int, PlainSerializer(lambda x: f"#{x}", return_type=str), AfterValidator(lambda v: v * 100), PlainValidator(lambda v: int(v))]

    m = M(n="7")
    return {"internal": m.n, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def A09_wrap_serializer_before():
    class M(BaseModel):
        n: Annotated[int, WrapSerializer(lambda v, nxt: f"<{nxt(v)}>", return_type=str), PlainValidator(lambda v: int(v))]

    m = M(n="3")
    return {"internal": m.n, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def A10_unless_none_optional():
    class M(BaseModel):
        a: Annotated[Optional[int], PlainSerializer(lambda x: x * 2, when_used="unless-none"), PlainValidator(lambda v: v)]
        b: Annotated[Optional[int], PlainSerializer(lambda x: x * 2, when_used="unless-none"), PlainValidator(lambda v: v)]

    m = M(a=None, b=5)
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A11_serializer_after_overrides():
    class M(BaseModel):
        n: Annotated[int, PlainSerializer(lambda x: "inner"), PlainValidator(lambda v: int(v)), PlainSerializer(lambda x: "outer")]

    m = M(n=1)
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A12_return_type_int_from_str():
    class M(BaseModel):
        s: Annotated[str, PlainSerializer(len, return_type=int), PlainValidator(lambda v: str(v))]

    m = M(s="abcd")
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A13_model_source_with_serializer():
    class Sub(BaseModel):
        a: int

    class M(BaseModel):
        s: Annotated[Sub, PlainSerializer(lambda m: m.a * 10), PlainValidator(lambda v: Sub(a=v))]

    m = M(s=3)
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A14_serializer_call_count():
    calls = []

    def ser(v):
        calls.append(v)
        return v

    class M(BaseModel):
        foo: Annotated[bool, PlainSerializer(ser), PlainValidator(lambda v: v)]

    d = M(foo=True).model_dump()
    return {"python": d, "calls": len(calls)}


@case
def A15_list_of_wrong_order_items():
    class M(BaseModel):
        xs: List[Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str), PlainValidator(lambda x: bool(int(x)))]]

    m = M(xs=["0", "1"])
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A16_serializer_inside_type_argument():
    class M(BaseModel):
        xs: Annotated[List[Annotated[int, PlainSerializer(lambda x: f"i{x}")]], PlainValidator(lambda v: [int(i) for i in v])]

    m = M(xs=["1", "2"])
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A17_source_type_own_serializer():
    class Temp:
        def __init__(self, c):
            self.c = c

        @classmethod
        def __get_pydantic_core_schema__(cls, source, handler):
            return core_schema.no_info_plain_validator_function(
                lambda v: v if isinstance(v, cls) else cls(float(v)),
                serialization=core_schema.plain_serializer_function_ser_schema(lambda t: f"{t.c}C"),
            )

    class M(BaseModel):
        t: Annotated[Temp, PlainValidator(lambda v: Temp(float(v) + 1))]

    m = M(t="20")
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def A18_json_schema_issue_model():
    class Blah(BaseModel):
        x: Annotated[bool, PlainValidator(lambda x: bool(int(x))), PlainSerializer(lambda x: str(int(x)), return_type=str)]
        y: Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str), PlainValidator(lambda x: bool(int(x)))]

    out = {}
    for mode in ("validation", "serialization"):
        try:
            out[mode] = Blah.model_json_schema(mode=mode)
        except Exception as e:  # noqa: BLE001
            out[mode] = short_exc(e)
    return out


# ---------------- B：既有公开能力与相邻行为 ----------------
class Custom:
    pass


@case
def B01_custom_plain_validator_default_config():
    class M(BaseModel):
        c: Annotated[Custom, PlainValidator(lambda v: v)]

    obj = Custom()
    m = M(c=obj)
    d = m.model_dump()
    return {"built": True, "same_obj": m.c is obj, "dump_same_obj": d["c"] is obj}


@case
def B02_upstream_test_shape_unsupported():
    class UnsupportedClass:
        pass

    ta = TypeAdapter(Annotated[UnsupportedClass, PlainValidator(lambda _: UnsupportedClass())])
    v = ta.validate_python("abcdefg")
    return {"validated_instance": isinstance(v, UnsupportedClass), "dump_instance": isinstance(ta.dump_python(v), UnsupportedClass)}


@case
def B03_custom_with_serializer_before_default_config():
    class M(BaseModel):
        c: Annotated[Custom, PlainSerializer(lambda v: "custom!"), PlainValidator(lambda v: Custom())]

    m = M(c=1)
    return {"python": jsonable(m.model_dump()), "json": m.model_dump_json()}


@case
def B04_custom_arbitrary_types_allowed():
    class M(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        c: Annotated[Custom, PlainValidator(lambda v: Custom())]

    m = M(c=1)
    return {"is_custom": isinstance(m.c, Custom), "dump_is_custom": isinstance(m.model_dump()["c"], Custom)}


@case
def B05_custom_serializer_before_arbitrary_types():
    class M(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        c: Annotated[Custom, PlainSerializer(lambda v: "custom!"), PlainValidator(lambda v: Custom())]

    m = M(c=1)
    return {"python": jsonable(m.model_dump()), "json": m.model_dump_json()}


@case
def B06_unresolved_forward_ref():
    class M(BaseModel):
        f: Annotated["NotDefinedAnywhere8567", PlainValidator(lambda v: v)]  # noqa: F821

    out = {"complete": M.__pydantic_complete__}
    try:
        out["value"] = M(f=5).f
    except Exception as e:  # noqa: BLE001
        out["instantiate"] = short_exc(e)
    return out


@case
def B07_validator_returns_other_type_no_serializer():
    class M(BaseModel):
        n: Annotated[int, PlainValidator(lambda v: str(v))]

    m = M(n=5)
    return {"internal": m.n, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def B08_validator_returns_subclass_model():
    class Base(BaseModel):
        a: int

    class Sub(Base):
        b: int

    class M(BaseModel):
        s: Annotated[Base, PlainValidator(lambda v: Sub(a=1, b=2))]

    m = M(s=None)
    return {"python": m.model_dump(), "json": m.model_dump_json()}


@case
def B09_plain_int_docstring_example():
    class Model(BaseModel):
        a: Annotated[int, PlainValidator(lambda v: int(v) + 1)]

    m = Model(a="1")
    return {"internal": m.a, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def B10_with_info_field_name_no_serializer():
    class M(BaseModel):
        g: Annotated[str, PlainValidator(lambda v, info: info.field_name)]

    return {"internal": M(g="x").g}


@case
def B11_decorator_plain_field_validator_with_annotated_serializer():
    class M(BaseModel):
        x: Annotated[bool, PlainSerializer(lambda x: str(int(x)), return_type=str)]

        @field_validator("x", mode="plain")
        @classmethod
        def v(cls, value):
            return bool(int(value))

    m = M(x="1")
    return {"internal": m.x, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def B12_docs_validator_ordering():
    logs = []

    def mk(label):
        def f(v, info):
            logs.append(label)
            return v
        return f

    def mkw(label):
        def f(v, handler, info):
            logs.append(f"{label}: pre")
            r = handler(v)
            logs.append(f"{label}: post")
            return r
        return f

    class A(BaseModel):
        y: Annotated[
            str,
            BeforeValidator(mk("before-1")), AfterValidator(mk("after-1")), WrapValidator(mkw("wrap-1")),
            PlainValidator(mk("plain")),
            BeforeValidator(mk("before-3")), AfterValidator(mk("after-3")), WrapValidator(mkw("wrap-3")),
        ]

    a = A(y="def")
    return {"logs": logs, "python": a.model_dump()}


@case
def B13_inner_constraint_replaced():
    class M(BaseModel):
        s: Annotated[str, annotated_types.MaxLen(3), PlainValidator(lambda v: v)]

    m = M(s="abcdef")
    return {"internal": m.s, "python": m.model_dump(), "json": m.model_dump_json()}


@case
def B14_docs_json_schema_withjsonschema():
    MyInt = Annotated[int, PlainValidator(lambda v: int(v) + 1), WithJsonSchema({"type": "integer", "examples": [1, 0, -1]})]

    class Model(BaseModel):
        a: MyInt

    return {"value": Model(a="1").a, "schema": Model.model_json_schema(),
            "ser_schema": Model.model_json_schema(mode="serialization")}


@case
def B15_json_schema_plain_int_no_withjsonschema():
    class Model(BaseModel):
        a: Annotated[int, PlainValidator(lambda v: int(v) + 1)]

    out = {}
    for mode in ("validation", "serialization"):
        try:
            out[mode] = Model.model_json_schema(mode=mode)
        except Exception as e:  # noqa: BLE001
            out[mode] = short_exc(e)
    return out


@case
def B16_custom_json_dump_default_config():
    class M(BaseModel):
        c: Annotated[Custom, PlainValidator(lambda v: Custom())]

    m = M(c=1)
    return {"json": m.model_dump_json()}


@case
def B17_callable_source_type():
    class M(BaseModel):
        f: Annotated[Callable[[], int], PlainValidator(lambda v: v)]

    fn = lambda: 1  # noqa: E731
    m = M(f=fn)
    return {"same": m.f is fn, "dump_same": m.model_dump()["f"] is fn}


# ---------------- v3 追加（09-29 独立复核之后）：PV 左侧元数据、TypedDict ----------------
@case
def A19_replaced_left_validator():
    # 修订 v3 第 5 项的形态：PV 左侧的 AfterValidator 不运行，serializer 仍生效
    ser = PlainSerializer(lambda x: str(int(x)), return_type=str)

    class Replaced(BaseModel):
        z: Annotated[bool, AfterValidator(lambda v: 1 / 0), ser, PlainValidator(lambda x: bool(int(x)))]

    r = Replaced(z="1")
    return {"internal": r.z, "python": r.model_dump(), "json": r.model_dump_json()}


@case
def B18_strictbool_source_pv():
    from pydantic import StrictBool

    class M(BaseModel):
        b: Annotated[StrictBool, PlainValidator(lambda v: bool(int(v)))]

    return {"internal": M(b="1").b}


@case
def B19_positiveint_source_pv():
    from pydantic import PositiveInt

    class M(BaseModel):
        n: Annotated[PositiveInt, PlainValidator(lambda v: int(v))]

    return {"internal": M(n=-5).n}


@case
def B20_gt_constraint_left_of_pv():
    class M(BaseModel):
        n: Annotated[int, annotated_types.Gt(0), PlainValidator(lambda v: int(v))]

    return {"internal": M(n="-5").n}


@case
def B21_typing_typeddict_source_pv():
    import typing

    if not hasattr(typing, "TypedDict"):
        return {"skipped": "no typing.TypedDict"}

    class TD(typing.TypedDict):
        a: int

    class M(BaseModel):
        t: Annotated[TD, PlainValidator(lambda v: v)]

    return {"internal": M(t={"a": 1}).t}


if __name__ == "__main__":
    print("pydantic", pydantic.VERSION, "file", pydantic.__file__)
    names = sys.argv[1:] or list(CASES)
    for n in names:
        print("CASE", n, json.dumps(run(CASES[n]), ensure_ascii=False, sort_keys=True, default=repr))
