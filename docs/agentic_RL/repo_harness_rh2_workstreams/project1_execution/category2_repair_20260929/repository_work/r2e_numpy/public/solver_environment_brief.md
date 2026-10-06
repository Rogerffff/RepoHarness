# NumPy 公开开发说明

工作目录是 `/testbed`。`python` 应指向 `/testbed/.venv/bin/python`，版本为 Python 3.7.9；NumPy 从 `/testbed/numpy` 导入。工作树已有编译产物，无需重新安装包。环境不联网，pip 可能不可用。

在 `/testbed` 中运行命令；如果从其它目录启动 Python，需显式设置 `PYTHONPATH=/testbed`。用 `python -m pytest` 跑测试，避免裸 `pytest` 因导入路径不同而收集失败。可以先确认解释器、包来源和打印选项：

```bash
python -c 'import sys, numpy as np; print(sys.executable, sys.version); print(np.__version__, np.__file__); print(np.get_printoptions())'
```

公开问题复现：

```bash
python -c 'import numpy as np; a = np.ma.arange(2000); a[1:50] = np.ma.masked; print(repr(a))'
```

相关公开回归测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider numpy/ma/tests/test_core.py numpy/ma/tests/test_subclassing.py -k 'str_repr or print or subclass_repr or subclass_str'
```

修改非测试源码；不要修改仓库测试文件。上述命令用于开发验证，任务要求以公开题面为准。
