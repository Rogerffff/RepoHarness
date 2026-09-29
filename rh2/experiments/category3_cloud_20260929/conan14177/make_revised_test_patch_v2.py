"""在容器 /testbed 内运行：把 revised_tests_v2.py 的辅助代码插到 base 版 test_multiple_no_version 之前，
并原位替换 test_multiple_no_version / test_multiple_with_version；test_single_patch_description 不动。"""
import ast
import sys
from pathlib import Path

target = Path("conans/test/unittests/tools/files/test_patches.py")
src = target.read_text()
new = Path(sys.argv[1]).read_text()
parts = {}
for chunk in new.split("# ---- ")[1:]:
    title, body = chunk.split(" ----\n", 1)
    parts[title] = body.strip("\n") + "\n"
tree = ast.parse(src)
lines = src.splitlines(keepends=True)
spans = {n.name: (n.lineno - 1, n.end_lineno) for n in tree.body if isinstance(n, ast.FunctionDef)}
for name in ("test_multiple_with_version", "test_multiple_no_version"):  # 先替换靠后的
    start, end = spans[name]
    replacement = parts[name]
    if name == "test_multiple_no_version":
        replacement = parts["helpers"] + "\n\n" + replacement
    lines[start:end] = [replacement]
body = "".join(lines)
assert body.startswith("import os\n")
target.write_text("import copy\n" + body)
