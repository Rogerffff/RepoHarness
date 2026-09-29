"""在容器 /testbed 内运行：把 base 版 test_patches.py 的三个同名测试替换为 revised_tests.py 中的版本，
并在文件头补 `import copy`。随后由调用方 `git diff` 生成版本化 test_patch。"""
import ast
import sys
from pathlib import Path

target = Path("conans/test/unittests/tools/files/test_patches.py")
src = target.read_text()
new = Path(sys.argv[1]).read_text()
tree = ast.parse(src)
names = {"test_single_patch_description", "test_multiple_no_version", "test_multiple_with_version"}
lines = src.splitlines(keepends=True)
spans = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in names:
        start = min([d.lineno for d in node.decorator_list] + [node.lineno]) - 1
        spans.append((start, node.end_lineno))
assert len(spans) == 3, spans
for start, end in sorted(spans, reverse=True):
    del lines[start:end]
body = "".join(lines).rstrip() + "\n\n\n" + new.split("\n", 2)[2].lstrip("\n")
assert body.startswith("import os\n")
body = "import copy\n" + body
target.write_text(body)
