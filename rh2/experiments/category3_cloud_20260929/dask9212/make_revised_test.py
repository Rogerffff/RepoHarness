"""生成 dask__dask-9212 的修订测试草案 v1（R-c）与 --materials JSON（私有，不交给求解者）。

用法：python make_revised_test.py <base 源码目录> <输出目录>
base 目录里需要镜像内 base 提交的 dask/tests/test_base.py 原件（git show HEAD:dask/tests/test_base.py）。
做法：先按原 test_patch 的两处新增得到“原版测试文件”，再只改 test_tokenize_enum 的函数体，
最后对 base 原件做 unified diff。测试 ID、参数化、F2P／P2P 分组与评分命令都不变。
"""
import difflib
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REL = "dask/tests/test_base.py"
IID = "dask__dask-9212"

IMPORT_OLD = "from concurrent.futures import Executor\nfrom operator import add, mul\n"
IMPORT_NEW = "from concurrent.futures import Executor\nfrom enum import Enum, Flag, IntEnum, IntFlag\nfrom operator import add, mul\n"

ANCHOR = '''    assert tokenize(a) != tokenize(c)


ADataClass = dataclasses.make_dataclass("ADataClass", [("a", int)])
'''

ORIGINAL_TEST = '''    assert tokenize(a) != tokenize(c)


@pytest.mark.parametrize("enum_type", [Enum, IntEnum, IntFlag, Flag])
def test_tokenize_enum(enum_type):
    class Color(enum_type):
        RED = 1
        BLUE = 2

    assert tokenize(Color.RED) == tokenize(Color.RED)
    assert tokenize(Color.RED) != tokenize(Color.BLUE)


ADataClass = dataclasses.make_dataclass("ADataClass", [("a", int)])
'''

REVISED_TEST = '''    assert tokenize(a) != tokenize(c)


@pytest.mark.parametrize("enum_type", [Enum, IntEnum, IntFlag, Flag])
def test_tokenize_enum(enum_type):
    class Color(enum_type):
        RED = 1
        BLUE = 2

    assert tokenize(Color.RED) == tokenize(Color.RED)
    assert tokenize(Color.RED) != tokenize(Color.BLUE)

    # Members of another Enum class are different values, even when they have
    # the same member name and value.
    class Light(enum_type):
        RED = 1
        BLUE = 2

    assert tokenize(Light.RED) == tokenize(Light.RED)
    assert tokenize(Color.RED) != tokenize(Light.RED)

    if issubclass(enum_type, Flag):
        # Combined flags are values of the Flag class too.
        assert tokenize(Color.RED | Color.BLUE) == tokenize(Color.BLUE | Color.RED)
        assert tokenize(Color.RED | Color.BLUE) != tokenize(Color(0))


ADataClass = dataclasses.make_dataclass("ADataClass", [("a", int)])
'''


def patch_for(base, new):
    diff = difflib.unified_diff(base.splitlines(keepends=True), new.splitlines(keepends=True),
                                fromfile=f"a/{REL}", tofile=f"b/{REL}")
    return f"diff --git a/{REL} b/{REL}\n" + "".join(diff)


def main():
    base_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    base = (base_dir / REL).read_text()
    for old in (IMPORT_OLD, ANCHOR):
        assert base.count(old) == 1, old[:60]
    original = base.replace(IMPORT_OLD, IMPORT_NEW).replace(ANCHOR, ORIGINAL_TEST)
    revised = base.replace(IMPORT_OLD, IMPORT_NEW).replace(ANCHOR, REVISED_TEST)
    orig_patch = (out_dir / "original_test.patch").read_text()
    rev_patch = patch_for(base, revised)
    # 自检：base + ingest 原 test_patch 必须逐字等于这里重建的原版；base + 修订补丁必须逐字等于修订版
    with tempfile.TemporaryDirectory() as tmp:
        for patch, expect in ((orig_patch, original), (rev_patch, revised)):
            (Path(tmp) / REL).parent.mkdir(parents=True, exist_ok=True)
            (Path(tmp) / REL).write_text(base)
            subprocess.run(["git", "apply", "-"], input=patch, text=True, cwd=tmp, check=True)
            assert (Path(tmp) / REL).read_text() == expect
    (out_dir / "revised_test_v1.patch").write_text(rev_patch)
    materials = {
        "version": "c3-dask9212-enum-distinct-v1",
        "tasks": {IID: {
            "original_patch_sha256": hashlib.sha256(orig_patch.encode()).hexdigest(),
            "test_patch": rev_patch,
            "revised_patch_sha256": hashlib.sha256(rev_patch.encode()).hexdigest(),
            "reason": (
                "S1 via v1 section 4 step 4 (and T2c for the distinctness half of the requirement): the original "
                "test only compares two members of one local class Color (the issue example), so candidates that "
                "hash the member value only (w_value) or drop the value (w_noval; on Python 3.10 every combined "
                "Flag value has name None) score 1 in formal grading while merging different Enum members into one "
                "task key (pure delayed / Delayed operators / map_blocks return the wrong result). R-c, same test "
                "id and F2P/P2P groups: in the same parametrized test add (1) a second local class Light with the "
                "same member names and values, asserting Light.RED is stable and differs from Color.RED; (2) for "
                "Flag kinds, combined flags are stable and RED|BLUE differs from Color(0). Public basis: tokenize "
                "builds keys from argument values; docs/source/custom-collections.rst asks for a value 'fully "
                "representative of the object' and states 'tokens for different objects aren't equal'. Not asserted "
                "(registered T3): same short class name in different modules, cross-process stability of complex "
                "values, __dask_tokenize__ on Enum subclasses."),
            "positive_control": ("gold (unchanged upstream fix); reasonable non-gold controls alt_modqual, "
                                 "alt_hookfirst, alt_up2024, alt_pickle, alt_docs (author-written, to be verified by others)"),
        }},
    }
    (out_dir / "materials_revised_v1.json").write_text(json.dumps(materials, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"revised_patch_sha256": materials["tasks"][IID]["revised_patch_sha256"],
                      "original_patch_sha256": materials["tasks"][IID]["original_patch_sha256"]}))


if __name__ == "__main__":
    main()
