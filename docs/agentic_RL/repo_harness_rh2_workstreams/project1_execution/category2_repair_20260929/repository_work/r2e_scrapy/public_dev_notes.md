# Scrapy 开发环境说明

在 `/testbed` 工作，使用仓库现成的虚拟环境解释器 `.venv/bin/python`。先确认 Scrapy 从当前仓库导入：

```bash
cd /testbed
.venv/bin/python -c 'import sys, scrapy; print(sys.executable); print(scrapy.__version__, scrapy.__file__)'
```

题面复现中的生成器应写在一个 `.py` 文件中，再用 `.venv/bin/python` 执行。相关实现会读取函数源码；直接在 `python -c` 或交互解释器中定义生成器，可能另行触发源码不可读取的错误。

仓库已有的相关公开测试可这样执行：

```bash
cd /testbed
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -rA tests/test_utils_misc/test_return_with_argument_inside_generator.py
```

测试初始化会尝试 DNS 查询，并可能在 `tests/keys/` 下生成本地测试证书。这些动作来自现有公开测试代码；网络受限时查询可能稍有等待。
