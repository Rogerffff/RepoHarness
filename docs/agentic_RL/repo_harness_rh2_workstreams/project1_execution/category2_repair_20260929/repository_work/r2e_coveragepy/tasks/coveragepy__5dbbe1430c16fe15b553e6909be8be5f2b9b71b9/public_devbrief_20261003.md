# coveragepy 公开开发环境

工作目录为 `/testbed`。`python` 使用 `/testbed/.venv/bin/python`（Python 3.7），从 `/testbed/coverage/__init__.py` 导入当前工作树。环境中已有 pytest 4.6.6；离开工作目录后仍应核对实际导入位置。

可按题面直接运行复现示例。需要检查解释器或导入时可执行：

```bash
python -c 'import sys, coverage; print(sys.executable); print(coverage.__file__)'
```

现有公开警告测试可执行：

```bash
python -m pytest -o addopts="" -p no:cacheprovider --color=no -rfE tests/test_api.py tests/test_testing.py -k warn
```

`-o addopts=""` 清除项目默认的并行／覆盖率选项。这份说明只给环境与公开命令，不改变题面目标。
