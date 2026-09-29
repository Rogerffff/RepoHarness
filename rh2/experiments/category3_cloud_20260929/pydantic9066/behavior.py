"""私有行为矩阵：各类默认值在 model_json_schema 中的 default 与警告。每项独立捕获异常。"""
import dataclasses
import datetime
import enum
import json
import uuid
import warnings
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Network, IPv6Address
from pathlib import PurePosixPath
from typing import List

from typing_extensions import TypedDict

import pydantic
from pydantic import BaseModel, ConfigDict
from pydantic.networks import IPvAnyAddress


@dataclasses.dataclass
class StdDC:
    x: int


@pydantic.dataclasses.dataclass
class PydDC:
    y: int


class Inner(BaseModel):
    z: int


class TD(TypedDict):
    k: int


class Color(enum.Enum):
    RED = "red"


class Opaque:
    def __repr__(self):
        return "Opaque()"


CASES = {
    "issue_ipv4_ipvany": (IPvAnyAddress, IPv4Address("127.0.0.1"), {}),
    "ipv6_ipvany": (IPvAnyAddress, IPv6Address("::1"), {}),
    "ipv4_plain_type": (IPv4Address, IPv4Address("10.0.0.1"), {}),
    "ipv4_network": (IPv4Network, IPv4Network("10.0.0.0/8"), {}),
    "list_of_ip": (List[IPvAnyAddress], [IPv4Address("127.0.0.1")], {}),
    "stdlib_dataclass_default": (StdDC, StdDC(1), {}),
    "pydantic_dataclass_default": (PydDC, PydDC(2), {}),
    "basemodel_instance_default": (Inner, Inner(z=3), {}),
    "typeddict_default": (TD, {"k": 4}, {}),
    "enum_default": (Color, Color.RED, {}),
    "datetime_default": (datetime.datetime, datetime.datetime(2024, 1, 2, 3, 4, 5), {}),
    "decimal_default": (Decimal, Decimal("1.5"), {}),
    "uuid_default": (uuid.UUID, uuid.UUID(int=1), {}),
    "path_default": (PurePosixPath, PurePosixPath("/a/b"), {}),
    "timedelta_float_config": (datetime.timedelta, datetime.timedelta(hours=1), {"ser_json_timedelta": "float"}),
    "bytes_base64_config": (bytes, b"hi", {"ser_json_bytes": "base64"}),
    "stdlib_dataclass_with_config": (StdDC, StdDC(5), {"ser_json_timedelta": "float"}),
    "opaque_nonserializable": (object, Opaque(), {"arbitrary_types_allowed": True}),
}
out = {}
for name, (tp, default, cfg) in CASES.items():
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Model = type("Model", (BaseModel,), {"__annotations__": {"field": tp}, "field": default,
                                                  "model_config": ConfigDict(**cfg)})
            schema = Model.model_json_schema()
        prop = schema["properties"]["field"]
        out[name] = {"default": prop.get("default", "<absent>"), "warnings": [str(x.message)[:90] for x in w]}
    except Exception as e:  # noqa: BLE001
        out[name] = {"exception": f"{type(e).__name__}: {str(e)[:160]}", "code": getattr(e, "code", None)}
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
