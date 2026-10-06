# coveragepy 公开开发环境

工作目录为 `/testbed`。`python` 使用 `/testbed/.venv/bin/python`（Python 3.7），从当前工作树 `/testbed/coverage/__init__.py` 导入。环境已有 pytest 4.6.6。可直接执行题面示例。

解释器和导入位置可用以下命令核对：

```bash
python -c 'import sys, coverage; print(sys.executable); print(coverage.__file__)'
```

相关公开回归可执行：

```bash
python -m pytest -o addopts="" tests/test_api.py tests/test_data.py tests/test_oddball.py
```

`-o addopts=""` 清除项目默认的并行／覆盖率选项。这份说明只提供环境和公开命令，不限定实现方式。
