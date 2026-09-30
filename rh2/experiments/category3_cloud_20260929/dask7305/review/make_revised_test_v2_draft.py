"""复核者建议的修订测试草案 v2（在作者 v1 上只追加两处实例），私有对照用，不交给求解者。

用法：python make_revised_test_v2_draft.py <base test_shuffle.py> <输出补丁>
base 文件取自镜像 c3keep/dask7305:src 的 /testbed/dask/dataframe/tests/test_shuffle.py
（sha256 b019a81adb92ddca708845b87866517551f7353739563f573707992da1d13b42）。
先在内存里套用作者的 revised_test_v1.patch（用 git apply 到临时目录），再追加两行调用，最后对 base 生成补丁。
"""
import difflib
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "revised_test_v1.patch"
REL = "dask/dataframe/tests/test_shuffle.py"

ANCHOR = '''    _assert_exact_int_divisions([big + 89000000000000001 * k for k in order], "uint64", 4, 4)
'''
ADDED = '''    _assert_exact_int_divisions([big + 89000000000000001 * k for k in order], "uint64", 4, 4)
    # A few distinct neighbouring values (closer than the float64 spacing, so
    # float64 rounds them above the true maximum), and large negative integers only.
    _assert_exact_int_divisions([big + 99 + j % 3 for j in range(300)], "uint64", 3, 5)
    _assert_exact_int_divisions([-big - 997 * k for k in order], "int64", 4, 4)
'''


def main():
    base_file, out = Path(sys.argv[1]), Path(sys.argv[2])
    base = base_file.read_text()
    assert hashlib.sha256(base.encode()).hexdigest().startswith("b019a81adb92"), "unexpected base test file"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / REL
        p.parent.mkdir(parents=True)
        p.write_text(base)
        subprocess.run(["git", "init", "-q", d], check=True)
        subprocess.run(["git", "apply", str(V1)], cwd=d, check=True)
        v1 = p.read_text()
    assert v1.count(ANCHOR) == 1
    v2 = v1.replace(ANCHOR, ADDED)
    diff = "".join(difflib.unified_diff(base.splitlines(True), v2.splitlines(True), f"a/{REL}", f"b/{REL}"))
    data = f"diff --git a/{REL} b/{REL}\n" + diff
    out.write_text(data)
    print(out.name, hashlib.sha256(data.encode()).hexdigest())


if __name__ == "__main__":
    main()
