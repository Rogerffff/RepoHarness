"""按基线 moto/dynamodb/models/table.py 生成 moto-6185 的候选补丁（私有，不交给求解者）。

用法：python make_candidates.py --base <基线 table.py> --out <目录>
每个候选只替换 `_validate_item_types`（swallow 另改 put_item 的调用处），输出 <名字>.patch（git apply 格式）。

候选说明：
- ctx：结构化校验。属性名层与 AttributeValue 层分开，M 的成员重新当属性名；保留 S/N 的旧错误。合理实现，与 gold 不同。
- ctx_list：ctx，并对 L 的元素做同样的 AttributeValue 校验。合理实现。
- parity：按深度奇偶区分（偶数层是属性名，奇数层是类型标签）。合理实现，与 gold 不同。
- top_only：只放过顶层属性名 S（题面例 1），嵌套仍报错。部分修复。
- siblings：认为“只有一个键的 dict 才是 AttributeValue”，有兄弟键时 S 才算属性名。数据形态子集。
- depth2：只把顶层和第一层 map 的键当属性名，更深的 map 仍按类型标签处理。规模子集。
- null_only：只在属性 S 的值为 NULL（题面示例字面值）时放过。示例字面值。
- shape：S 的值“看起来像 AttributeValue”（单键且键是类型标签）时当作属性名。数据形态启发式。
- rootkey：只在顶层属性是表主键时检查 S→dict（gold 递归参数若传根属性名的写法）。非主键的 S 类型错误被放过。
- swallow：put_item 里捕获 SerializationException，改为只校验主键属性后继续。吞掉错误。
"""
import argparse
import difflib
from pathlib import Path

REL = "moto/dynamodb/models/table.py"
BASE_FUNC = '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S":
                # This scenario is usually caught by boto3, but the user can disable parameter validation
                # Which is why we need to catch it 'server-side' as well
                if type(value) == int:
                    raise SerializationException(
                        "NUMBER_VALUE cannot be converted to String"
                    )
                if type(value) == dict:
                    raise SerializationException(
                        "Start of structure or map found where not expected"
                    )
'''

S_CHECKS = '''                # This scenario is usually caught by boto3, but the user can disable parameter validation
                # Which is why we need to catch it 'server-side' as well
                if type(value) == int:
                    raise SerializationException(
                        "NUMBER_VALUE cannot be converted to String"
                    )
                if type(value) == dict:
                    raise SerializationException(
                        "Start of structure or map found where not expected"
                    )
'''

CTX_HEAD = '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
        # item_attrs maps attribute *names* to AttributeValues. A name can be anything,
        # including "S", so only the AttributeValues themselves are type-checked.
        for attr_value in item_attrs.values():
            if type(attr_value) == dict:
                self._validate_attribute_value(attr_value)

    def _validate_attribute_value(self, attr_value: Dict[str, Any]) -> None:
        for type_tag, value in attr_value.items():
            if type_tag == "M" and type(value) == dict:
                # The members of a map are attribute names again
                self._validate_item_types(value)
'''
CTX_LIST = '''            elif type_tag == "L" and type(value) == list:
                for element in value:
                    if type(element) == dict:
                        self._validate_attribute_value(element)
'''
CTX_TAIL = '''            elif type_tag == "N" and type(value) == int:
                raise InvalidConversion
            elif type_tag == "S":
''' + S_CHECKS

CANDIDATES = {
    "ctx": CTX_HEAD + CTX_TAIL,
    "ctx_list": CTX_HEAD + CTX_LIST + CTX_TAIL,
    "parity": '''    def _validate_item_types(self, item_attrs: Dict[str, Any], depth: int = 0) -> None:
        # Even depths hold attribute names (the item itself and the members of every map),
        # odd depths hold the type descriptor of an AttributeValue.
        is_type_level = depth % 2 == 1
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, depth + 1)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S" and is_type_level:
''' + S_CHECKS,
    "top_only": '''    def _validate_item_types(
        self, item_attrs: Dict[str, Any], top_level: bool = True
    ) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, top_level=False)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            # Top-level keys are attribute names, so an attribute called "S" is fine there
            if key == "S" and not top_level:
''' + S_CHECKS,
    "siblings": '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            # An AttributeValue has exactly one type key; in a dict with several keys,
            # "S" is just an attribute name
            if key == "S" and len(item_attrs) == 1:
''' + S_CHECKS,
    "depth2": '''    def _validate_item_types(self, item_attrs: Dict[str, Any], depth: int = 0) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, depth + 1)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            # Attribute names live at the top level and inside a top-level map
            if key == "S" and depth not in (0, 2):
''' + S_CHECKS,
    "null_only": '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S":
                if value == {"NULL": True}:
                    # An attribute that is called "S" and holds None
                    continue
''' + S_CHECKS,
    "shape": '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
        type_tags = {"S", "N", "B", "SS", "NS", "BS", "M", "L", "NULL", "BOOL"}
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S":
                # This scenario is usually caught by boto3, but the user can disable parameter validation
                # Which is why we need to catch it 'server-side' as well
                if type(value) == int:
                    raise SerializationException(
                        "NUMBER_VALUE cannot be converted to String"
                    )
                # If the value looks like an AttributeValue, "S" is an attribute name
                if type(value) == dict and not (
                    len(value) == 1 and list(value)[0] in type_tags
                ):
                    raise SerializationException(
                        "Start of structure or map found where not expected"
                    )
''',
    "rootkey": '''    def _validate_item_types(
        self, item_attrs: Dict[str, Any], attr: Optional[str] = None
    ) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, attr=key if attr is None else attr)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S":
                # This scenario is usually caught by boto3, but the user can disable parameter validation
                # Which is why we need to catch it 'server-side' as well
                if type(value) == int:
                    raise SerializationException(
                        "NUMBER_VALUE cannot be converted to String"
                    )
                # Only the key attributes are checked strictly; elsewhere "S" may be an attribute name
                if attr and attr in self.table_key_attrs and type(value) == dict:
                    raise SerializationException(
                        "Start of structure or map found where not expected"
                    )
''',
}

SWALLOW_OLD = "        self._validate_item_types(item_attrs)\n        self._validate_key_sizes(item_attrs)\n"
SWALLOW_NEW = '''        try:
            self._validate_item_types(item_attrs)
        except SerializationException:
            # "S" may be an attribute name rather than a type descriptor;
            # only insist on well-formed key attributes
            self._validate_item_types(
                {k: v for k, v in item_attrs.items() if k in self.table_key_attrs}
            )
        self._validate_key_sizes(item_attrs)
'''

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True)
ap.add_argument("--out", required=True)
ns = ap.parse_args()
base = Path(ns.base).read_text()
assert base.count(BASE_FUNC) == 1
out = Path(ns.out)
out.mkdir(parents=True, exist_ok=True)
variants = {name: base.replace(BASE_FUNC, body) for name, body in CANDIDATES.items()}
assert base.count(SWALLOW_OLD) == 1
variants["swallow"] = base.replace(SWALLOW_OLD, SWALLOW_NEW)
for name, text in variants.items():
    assert text != base, name
    diff = difflib.unified_diff(base.splitlines(keepends=True), text.splitlines(keepends=True),
                                fromfile="a/" + REL, tofile="b/" + REL)
    (out / f"{name}.patch").write_text(f"diff --git a/{REL} b/{REL}\n" + "".join(diff))
    print(name)
