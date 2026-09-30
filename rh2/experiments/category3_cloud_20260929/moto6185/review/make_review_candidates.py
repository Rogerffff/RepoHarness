"""复核者自造候选（moto-6185，私有，不交给求解者）。

用法：python make_review_candidates.py --base <base 的 moto/dynamodb/models/table.py> --out candidates/
base 文件可从原镜像取出：docker cp <容器>:/testbed/moto/dynamodb/models/table.py <路径>
（base 提交 dc460a32…，blob 1be96141…）。每个候选只改这一个文件，输出标准 unified diff。

候选（性质按公开要求判断，不以 gold 为答案）：
- rv_swallow_attr   错误：逐个顶层属性校验，非主键属性的 SerializationException 一律吞掉。
                    同一个嵌套 map 里，名为 S 的成员排在前面时，后面成员的 N 整数错误不再报出并被存入。
- rv_depth4         错误：阈值型部分修复，只把第 0、2、4 层字典的键当属性名（最多两层嵌套 map）。
- rv_scalar_s       错误：gold 写法，再把“S 的值里还有结构”当畸形而报错；名为 S、值为 map 的属性仍被拒。
- rv_top_or_null    错误（示例字面值）：只放过顶层的 S 与值为 NULL 的 S。
- rv_break_after_s  错误（依赖顺序）：奇偶写法，遇到名为 S 的属性校验完就 break，同层后面的属性不再校验。
- rv_tagparent      错误：gold 思路的修正版，“父键不是类型标签”时才当 AttributeValue 层；属性名恰为
                    类型标签（如名为 S 的属性）时，其畸形的 S→dict 值不再报 SerializationException。
- rv_shape_key      与 gold 同类（主路径正确，gold 缺口 2 同样存在）：按根属性名判断是否主键；非主键处 S 的值
                    “像 AttributeValue”（单键且为已知类型标签）时当属性名。用来查 v2 是否误拒 gold 式写法。
- rv_dynamotype     合理（与 gold、ctx、parity 机制都不同）：用 moto 自己的 DynamoType 解析每个属性值，
                    再按类型递归（含 M 与 L）；S 的值不是字符串即报 SerializationException。
"""
import argparse
import difflib
from pathlib import Path

REL = "moto/dynamodb/models/table.py"

BASE_METHOD = '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
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

BASE_CALL = '''        self._validate_item_types(item_attrs)
        self._validate_key_sizes(item_attrs)
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

CANDIDATES = {}

# 1. 吞错：逐属性 try/except
CANDIDATES["rv_swallow_attr"] = [(BASE_CALL, '''        for attr_name, attr_value in item_attrs.items():
            try:
                self._validate_item_types({attr_name: attr_value})
            except SerializationException:
                # 'S' can also be the name of an attribute or of a nested map member,
                # so only a malformed key attribute is a definite error here
                if attr_name in self.table_key_attrs:
                    raise
        self._validate_key_sizes(item_attrs)
''')]

# 2. 阈值：最多两层嵌套 map
CANDIDATES["rv_depth4"] = [(BASE_METHOD, '''    def _validate_item_types(self, item_attrs: Dict[str, Any], depth: int = 0) -> None:
        # Attribute names live at the top level and inside nested maps (up to two levels deep)
        names_level = depth in (0, 2, 4)
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, depth + 1)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S" and not names_level:
''' + S_CHECKS)]

# 3. 值形态子集：gold 写法 + “S 的值里还有结构即畸形”
CANDIDATES["rv_scalar_s"] = [(BASE_METHOD, '''    def _validate_item_types(
        self, item_attrs: Dict[str, Any], attr: Optional[str] = None
    ) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, attr=key)
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
                    # A key attribute of type S can never hold a dictionary. Elsewhere 'S' may be the
                    # name of an attribute holding an AttributeValue such as {"NULL": True}; but a
                    # dictionary that holds yet another structure is still a malformed string value
                    if (attr and attr in self.table_key_attrs) or any(
                        type(v) == dict for v in value.values()
                    ):
                        raise SerializationException(
                            "Start of structure or map found where not expected"
                        )
''')]

# 4. 示例字面值：顶层 S 或值为 NULL 的 S
CANDIDATES["rv_top_or_null"] = [(BASE_METHOD, '''    def _validate_item_types(
        self, item_attrs: Dict[str, Any], top_level: bool = True
    ) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, top_level=False)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S":
                if top_level or value == {"NULL": True}:
                    # An attribute that is called 'S' (at the top, or holding None)
                    continue
''' + S_CHECKS)]

# 5. 依赖顺序：名为 S 的属性处理完就 break
CANDIDATES["rv_break_after_s"] = [(BASE_METHOD, '''    def _validate_item_types(self, item_attrs: Dict[str, Any], depth: int = 0) -> None:
        # Even depths hold attribute names, odd depths hold type descriptors
        is_type_level = depth % 2 == 1
        for key, value in item_attrs.items():
            if key == "S" and not is_type_level:
                # An attribute called 'S': validate its value, and we are done with this level
                if type(value) == dict:
                    self._validate_item_types(value, depth + 1)
                break
            if type(value) == dict:
                self._validate_item_types(value, depth + 1)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S":
''' + S_CHECKS)]

# 5b. gold 思路的“修正版”：父键不是类型标签时，这一层才是 AttributeValue
#     属性名恰好等于类型标签（S、M、N…）时，它的值被误当成属性名层，畸形的 S→dict 不再报错
CANDIDATES["rv_tagparent"] = [(BASE_METHOD, '''    TYPE_DESCRIPTORS = {"S", "N", "B", "SS", "NS", "BS", "M", "L", "NULL", "BOOL"}

    def _validate_item_types(
        self, item_attrs: Dict[str, Any], parent: Optional[str] = None
    ) -> None:
        # A dictionary directly below an attribute name is an AttributeValue, whose keys are type
        # descriptors. The item itself, and the value of a map ('M'), hold attribute names instead
        type_level = parent is not None and parent not in self.TYPE_DESCRIPTORS
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(value, parent=key)
            elif type(value) == int and key == "N":
                raise InvalidConversion
            if key == "S" and type_level:
''' + S_CHECKS)]

# 6. 与 gold 同类：根属性名 + 值形态启发式（完整类型标签集）
CANDIDATES["rv_shape_key"] = [(BASE_METHOD, '''    ATTRIBUTE_VALUE_TYPES = {"S", "N", "B", "SS", "NS", "BS", "M", "L", "NULL", "BOOL"}

    def _validate_item_types(
        self, item_attrs: Dict[str, Any], root_attr: Optional[str] = None
    ) -> None:
        for key, value in item_attrs.items():
            if type(value) == dict:
                self._validate_item_types(
                    value, root_attr=key if root_attr is None else root_attr
                )
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
                    # 'S' may also be the name of an attribute: then its value is an AttributeValue
                    looks_like_attribute_value = (
                        len(value) == 1 and list(value)[0] in self.ATTRIBUTE_VALUE_TYPES
                    )
                    if root_attr in self.table_key_attrs or not looks_like_attribute_value:
                        raise SerializationException(
                            "Start of structure or map found where not expected"
                        )
''')]

# 7. 合理：DynamoType 解析后按类型递归
CANDIDATES["rv_dynamotype"] = [(BASE_METHOD, '''    def _validate_item_types(self, item_attrs: Dict[str, Any]) -> None:
        # Only the attribute *values* carry types; an attribute (or map member) may be called anything,
        # including 'S'. Parse every value the way the model stores it, and check it recursively.
        for attribute_value in item_attrs.values():
            if type(attribute_value) == dict:
                self._validate_dynamo_type(DynamoType(attribute_value))

    def _validate_dynamo_type(self, dynamo_type: DynamoType) -> None:
        if dynamo_type.type == "S" and not isinstance(dynamo_type.value, str):
            # This scenario is usually caught by boto3, but the user can disable parameter validation
            # Which is why we need to catch it 'server-side' as well
            if type(dynamo_type.value) == int:
                raise SerializationException("NUMBER_VALUE cannot be converted to String")
            raise SerializationException(
                "Start of structure or map found where not expected"
            )
        if dynamo_type.type == "N" and type(dynamo_type.value) == int:
            raise InvalidConversion
        if dynamo_type.is_map():
            for member in dynamo_type.value.values():
                self._validate_dynamo_type(member)
        elif dynamo_type.is_list():
            for element in dynamo_type.value:
                self._validate_dynamo_type(element)
''')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    base = Path(ns.base).read_text()
    assert base.count(BASE_METHOD) == 1 and base.count(BASE_CALL) == 1
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, edits in CANDIDATES.items():
        new = base
        for old, repl in edits:
            assert new.count(old) == 1, (name, old[:60])
            new = new.replace(old, repl)
        diff = difflib.unified_diff(
            base.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{REL}", tofile=f"b/{REL}", n=3)
        text = f"diff --git a/{REL} b/{REL}\n" + "".join(diff)
        (out / f"{name}.patch").write_text(text)
        print(name, len(text))


if __name__ == "__main__":
    main()
