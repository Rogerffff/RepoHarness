# 在原 test_patch 应用后的文件上改：test_default_value_encoding 追加标准库 dataclass 默认实例的 schema 回归检查。
from pathlib import Path
p = Path("tests/test_json_schema.py")
s = p.read_text()
assert s.startswith("import json\n")
s = "import dataclasses\n" + s
old = '''    schema = Model.model_json_schema()
    assert schema == expected_schema
'''
assert s.endswith(old), s[-200:]
s = s[: -len(old)] + '''    schema = Model.model_json_schema()
    assert schema == expected_schema

    # Encoding such defaults must keep working for defaults that were already JSON serializable,
    # e.g. a standard library dataclass instance (documented BaseModel + stdlib dataclass usage)
    @dataclasses.dataclass
    class Point:
        x: int

    class WithDataclassDefault(BaseModel):
        point: Point = Point(1)

    assert WithDataclassDefault.model_json_schema()['properties']['point']['default'] == {'x': 1}
'''
p.write_text(s)
