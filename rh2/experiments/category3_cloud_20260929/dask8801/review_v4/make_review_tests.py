"""dask__dask-8801 v4 聚焦复核：复核者对 v4 测试的两个改动草案（私有诊断材料，不交给求解者）。

用法：python make_review_tests.py <base test_config.py> <v4 test_config.py> <输出目录>

v4rva（针对“点名错误文件”的新候选，最小改动）：
  1) 不可读条目（名为 *.yaml 的子目录）改名为 0.yaml，排在坏文件 a.yaml 之前；
  2) 非映射实例另断言报错不含其后正常文件 b.yaml 的路径。
v4rvb = v4rva + 原因词表把 "mapping" 放宽为 "map"，并加 "object"（针对措辞误拒）。
输出两份测试文件、相对 base 测试文件的补丁，以及 sha256。
"""

import difflib
import hashlib
import json
import sys
from pathlib import Path

base_path, v4_path, out_dir = map(Path, sys.argv[1:4])
out_dir.mkdir(parents=True, exist_ok=True)
BASE = base_path.read_text()
V4 = v4_path.read_text()


def sub(text: str, old: str, new: str, count: int = 1) -> str:
    assert text.count(old) == count, (old[:80], text.count(old))
    return text.replace(old, new)


A = sub(
    V4,
    """    # Entries that cannot be read are still skipped (here a directory named like
    # a config file, which ``open`` cannot read), and files that load as nothing
    # (empty, or fully commented out as written by ``ensure_file(...,
    # comment=True)``) are valid and contribute nothing
    os.mkdir(os.path.join(dir_path, "c.yaml"))
    with open(os.path.join(dir_path, "b.yaml"), mode="wb") as f:
        f.write(b"x: 1\\n")
""",
    """    # Entries that cannot be read are still skipped (here a directory named like
    # a config file and listed before a.yaml, which ``open`` cannot read), and files
    # that load as nothing (empty, or fully commented out as written by
    # ``ensure_file(..., comment=True)``) are valid and contribute nothing
    os.mkdir(os.path.join(dir_path, "0.yaml"))
    other_path = os.path.join(dir_path, "b.yaml")
    with open(other_path, mode="wb") as f:
        f.write(b"x: 1\\n")
""",
)
A = sub(
    A,
    """        # Loading fails with an error that names the offending file (not another
        # file read after it) and says that a mapping of keys to values was
        # expected (or what was found instead), whether the file is found in a
        # directory or given directly
        for paths in ([dir_path], [fil_path]):
            msg = str(_collect_yaml_error(paths))
            assert fil_path in msg
""",
    """        # Loading fails with an error that names the offending file (not an entry
        # listed before it, nor a file read after it) and says that a mapping of
        # keys to values was expected (or what was found instead), whether the file
        # is found in a directory or given directly
        for paths in ([dir_path], [fil_path]):
            msg = str(_collect_yaml_error(paths))
            assert fil_path in msg
            assert other_path not in msg
""",
)
B = sub(
    A,
    """            assert any(w in rest for w in ("dict", "mapping", "key", type_name))""",
    """            assert any(w in rest for w in ("dict", "map", "key", "object", type_name))""",
)

meta = {}
for name, text in (("v4rva", A), ("v4rvb", B)):
    compile(text, name, "exec")
    (out_dir / f"test_config_{name}.py").write_text(text)
    patch = "diff --git a/dask/tests/test_config.py b/dask/tests/test_config.py\n" + "".join(
        difflib.unified_diff(
            BASE.splitlines(keepends=True),
            text.splitlines(keepends=True),
            "a/dask/tests/test_config.py",
            "b/dask/tests/test_config.py",
            n=3,
        )
    )
    (out_dir / f"revised_test_{name}.patch").write_text(patch)
    meta[name] = {
        "test_file_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    }
meta["_v4_test_file_sha256"] = hashlib.sha256(V4.encode()).hexdigest()
(out_dir / "tests_review.json").write_text(json.dumps(meta, indent=1) + "\n")
print(json.dumps(meta, indent=1))
