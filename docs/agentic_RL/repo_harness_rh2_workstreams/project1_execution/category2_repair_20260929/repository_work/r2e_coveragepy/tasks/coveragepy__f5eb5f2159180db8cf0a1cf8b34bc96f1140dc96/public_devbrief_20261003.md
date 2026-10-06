# coveragepy 公开开发环境

工作目录为 `/testbed`。`python` 使用 `/testbed/.venv/bin/python`（Python 3.7），从当前工作树 `/testbed/coverage/__init__.py` 导入。环境已有 pytest 4.6.6。

```bash
python -c 'import sys, coverage; print(sys.executable); print(coverage.__file__)'
python -m pytest -o addopts="" -p no:cacheprovider --color=no -rfE tests/test_json.py
```

`-o addopts=""` 清除项目默认的并行／覆盖率选项。仓库原公开 JSON 测试按修改前的完整字典比较输出；增加题面所述字段后，需结合题面核对这些公开预期是否需要同步。这份说明不提供修法或私有评分要求。
