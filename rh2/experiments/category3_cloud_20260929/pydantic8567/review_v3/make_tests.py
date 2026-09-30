"""生成用于私有模拟评分的测试补丁变体（容器 /testbed 内运行）。

用法（容器内）：python make_tests.py <作者 revised_test_v3.patch> <输出目录>

- t_v3：作者 v3 原样（只复制，便于同一目录引用）。
- t_v3s：v3 第 5 项的源类型由 `bool` 改为 `StrictBool`（左侧多一个约束 `Strict()`），import 加 `StrictBool`。
  这是本复核对阻断项给出的修法草案。
- t_v3b：首轮复核非阻断建议 1 的“夹中间”形式：第 5 项改为 `Annotated[bool, serializer, AfterValidator(1/0), validator]`，
  内部值与 dump 都断言（会把 A08 从 T3 升为有断言）。
- t_v3sv2：t_v3s 再加一个单独模型，只断言验证、不 dump 的“夹中间”字段：
  `Annotated[bool, serializer, AfterValidator(1/0), validator]` 只查 `is True`（不把 A08 的序列化升为断言）。
- t_v2：作者 v2 原样（父版本，用于看 v3 新拒了哪些候选）。
- t_v3f：与 t_v3s 等价、不改 import 的写法：第 5 项字段加默认值 `= Field(strict=True)`（元数据为 [Strict, After, ser, PV]）。
- t_v4：本复核建议的合并修订（交第2类时一并修）：t_v3s 的 StrictBool 第 5 项，加 `Between`
  （`[PlainSerializer(v*10), AfterValidator(1/0), PV]`，验证值与 dump 都断言）与 `Both`（PV 两侧都有 serializer 时外层生效）。
- t_v4b03：t_v4 再加 B03（未知类型、serializer 在 PV 前）一项，只作决策数据，不建议采用。
- t_v3sx：t_v3s 再加一个单独模型，serializer 与 PV 之间夹一个不包层的约束：
  `Annotated[bool, serializer, Field(strict=True), validator]`，验证值与 dump 都断言。
"""
import shutil
import subprocess
import sys
from pathlib import Path

V3, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
T = Path('/testbed/tests/test_validators.py')

OLD_BLOCK = """    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # an inner validator is not called, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[bool, AfterValidator(lambda v: 1 / 0), serializer, validator]

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}
"""

NEW_BLOCKS = {
    't_v3s': """    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # neither the inner constraint (`StrictBool`) nor an inner validator applies, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[StrictBool, AfterValidator(lambda v: 1 / 0), serializer, validator]

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}
""",
    't_v3b': """    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # an inner validator is not called, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[bool, serializer, AfterValidator(lambda v: 1 / 0), validator]

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}
""",
    't_v3sv2': """    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # neither the inner constraint (`StrictBool`) nor an inner validator applies, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[StrictBool, AfterValidator(lambda v: 1 / 0), serializer, validator]

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}

    # This also holds for a validator placed between the serializer and the plain validator.
    class Between(BaseModel):
        w: Annotated[bool, serializer, AfterValidator(lambda v: 1 / 0), validator]

    assert Between(w='1').w is True
""",
    't_v3sx': """    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # neither the inner constraint (`StrictBool`) nor an inner validator applies, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[StrictBool, AfterValidator(lambda v: 1 / 0), serializer, validator]

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}

    # Same when a constraint sits between the serializer and the plain validator.
    class Between(BaseModel):
        w: Annotated[bool, serializer, Field(strict=True), validator]

    between = Between(w='1')
    assert between.w is True
    assert between.model_dump() == {'w': '1'}
""",
    't_v3f': """    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # neither the constraint from the field default nor an inner validator applies, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[bool, AfterValidator(lambda v: 1 / 0), serializer, validator] = Field(strict=True)

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}
""",
    't_v4': "    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):\n    # neither the inner constraint (`StrictBool`) nor an inner validator applies, while the serializer is still used.\n    class Replaced(BaseModel):\n        z: Annotated[StrictBool, AfterValidator(lambda v: 1 / 0), serializer, validator]\n\n    replaced = Replaced(z='1')\n    assert replaced.z is True\n    assert replaced.model_dump() == {'z': '1'}\n\n    # The serializer is also used when other metadata sits between it and the plain validator.\n    class Between(BaseModel):\n        w: Annotated[\n            int, PlainSerializer(lambda v: v * 10), AfterValidator(lambda v: 1 / 0), PlainValidator(lambda v: int(v))\n        ]\n\n    between = Between(w='7')\n    assert between.w == 7\n    assert between.model_dump() == {'w': 70}\n\n    # With serializers on both sides of the plain validator, the outer one is used, as without the plain validator.\n    class Both(BaseModel):\n        b: Annotated[bool, PlainSerializer(lambda v: 'inner'), validator, PlainSerializer(lambda v: 'outer')]\n\n    assert Both(b='1').model_dump() == {'b': 'outer'}\n",
    't_v4b03': "    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):\n    # neither the inner constraint (`StrictBool`) nor an inner validator applies, while the serializer is still used.\n    class Replaced(BaseModel):\n        z: Annotated[StrictBool, AfterValidator(lambda v: 1 / 0), serializer, validator]\n\n    replaced = Replaced(z='1')\n    assert replaced.z is True\n    assert replaced.model_dump() == {'z': '1'}\n\n    # The serializer is also used when other metadata sits between it and the plain validator.\n    class Between(BaseModel):\n        w: Annotated[\n            int, PlainSerializer(lambda v: v * 10), AfterValidator(lambda v: 1 / 0), PlainValidator(lambda v: int(v))\n        ]\n\n    between = Between(w='7')\n    assert between.w == 7\n    assert between.model_dump() == {'w': 70}\n\n    # With serializers on both sides of the plain validator, the outer one is used, as without the plain validator.\n    class Both(BaseModel):\n        b: Annotated[bool, PlainSerializer(lambda v: 'inner'), validator, PlainSerializer(lambda v: 'outer')]\n\n    assert Both(b='1').model_dump() == {'b': 'outer'}\n\n    # (decision data only) A serializer placed before the plain validator of a type without a pydantic schema.\n    class Custom(BaseModel):\n        c: Annotated[Unsupported, PlainSerializer(lambda v: 'custom'), PlainValidator(lambda v: Unsupported())]\n\n    assert Custom(c='x').model_dump() == {'c': 'custom'}\n",
}

IMPORT_OLD = """    PydanticUserError,
    TypeAdapter,
"""
IMPORT_NEW = """    PydanticUserError,
    StrictBool,
    TypeAdapter,
"""


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, cwd='/testbed', check=True, capture_output=True, text=True).stdout


shutil.copy(V3, OUT / 't_v3.patch')
shutil.copy(V3.with_name('revised_test_v2.patch'), OUT / 't_v2.patch')
for name, block in NEW_BLOCKS.items():
    sh('git checkout -- tests')
    sh(f'git apply {V3}')
    text = T.read_text()
    assert text.count(OLD_BLOCK) == 1
    text = text.replace(OLD_BLOCK, block)
    if 'StrictBool' in block:
        assert text.count(IMPORT_OLD) == 1
        text = text.replace(IMPORT_OLD, IMPORT_NEW)
    T.write_text(text)
    (OUT / f'{name}.patch').write_text(sh('git diff -- tests/test_validators.py'))
    sh('git checkout -- tests')
    subprocess.run(['git', 'apply', '--check', str(OUT / f'{name}.patch')], cwd='/testbed', check=True)
    print(name, 'ok')
