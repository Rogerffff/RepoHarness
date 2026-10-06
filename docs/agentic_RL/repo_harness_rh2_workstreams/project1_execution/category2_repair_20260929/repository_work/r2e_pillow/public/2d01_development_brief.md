# Pillow 2d01：公开开发条件与命令

使用工作树 `/testbed` 中已激活的 `python`，解释器应来自 `/testbed/.venv`，`PIL` 应从 `/testbed/src/PIL` 导入。可以先核对当前 Python、PIL、C 扩展和 libtiff：

```bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "import sys, PIL, pytest; from PIL import Image, TiffImagePlugin, features; print(sys.executable, sys.version.split()[0]); print('PIL', PIL.__version__, PIL.__file__); print('TiffImagePlugin', TiffImagePlugin.__file__); print('core', Image.core.__file__); print('libtiff', features.check('libtiff'), features.version('libtiff')); print('pytest', pytest.__version__)"
```

公开 TIFF 测试中的两处 `pytest.warns(None)` 使用了旧 pytest API。以下命令在 `Tests` 包内创建临时兼容副本，以标准库记录警告，保留全部原断言；其他公开测试按原路径运行，结束后删除临时副本并核原文件没有变化。它不更换依赖或修改原公开测试。

```bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
"""运行公开 TIFF 测试的临时兼容副本，保留“不产生警告”的原断言。"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import tempfile


def compatible_source(source):
    tree = ast.parse(source)
    matches = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "pytest"
                and child.func.attr == "warns"
                and len(child.args) == 1
                and isinstance(child.args[0], ast.Constant)
                and child.args[0].value is None
                and not child.keywords
            ):
                matches.append(node.name)
    if sorted(matches) != ["test_closed_file", "test_context_manager"]:
        raise ValueError("公开测试的兼容点已变化，需先重新核对")

    old = "        with pytest.warns(None) as record:\n"
    new = (
        "        with warnings.catch_warnings(record=True) as record:\n"
        '            warnings.simplefilter("always")\n'
    )
    if source.count(old) != 2 or source.count("import os\n") != 1:
        raise ValueError("公开测试原文与兼容方案不符")
    revised = source.replace("import os\n", "import os\nimport warnings\n", 1)
    revised = revised.replace(old, new)
    ast.parse(revised)
    return revised


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--testbed", type=Path, default=Path.cwd())
    args = parser.parse_args()
    testbed = args.testbed.resolve()
    original_path = testbed / "Tests/test_file_tiff.py"
    original = original_path.read_bytes()
    revised = compatible_source(original.decode("utf-8"))
    print(json.dumps({
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "compatible_copy_sha256": hashlib.sha256(revised.encode()).hexdigest(),
        "compatibility_points": ["test_closed_file", "test_context_manager"],
        "original_assertions_preserved": True,
        "scope": "public_development_only",
    }))
    if args.check_only:
        return 0
    if Path.cwd().resolve() != testbed:
        raise ValueError("请在工作树根目录运行，保证公开图片与配置按原路径加载")

    import pytest

    temporary_path = None
    try:
        # 保持 Tests 包、公开 helper 和 conftest 的加载方式；原文件不改。
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=testbed / "Tests",
            prefix="test_file_tiff_compat_", suffix=".py", delete=False,
        ) as temporary:
            temporary.write(revised)
            temporary_path = Path(temporary.name)
        return int(pytest.main([
            "-q", "-p", "no:cacheprovider", str(temporary_path),
            "Tests/test_file_tiff_metadata.py",
            "Tests/test_file_libtiff.py::TestFileLibTiff::test_write_metadata",
        ]))
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if original_path.read_bytes() != original:
            raise RuntimeError("原公开测试文件发生变化，不能按本次兼容验收收口")


if __name__ == "__main__":
    raise SystemExit(main())

PY
```

也可单独运行原公开 metadata 入口：

```bash
python -m pytest -p no:cacheprovider Tests/test_file_tiff_metadata.py
python -m pytest -p no:cacheprovider Tests/test_file_libtiff.py::TestFileLibTiff::test_write_metadata
```

题面原例可分别使用 `Image.new("L", ...)` 和 `Image.new("1", ...)`，保存时传入 `tiffinfo={262: 0}`，再通过 `Image.open` 观察标签。测试图片和输出可以写入 `/tmp`。
