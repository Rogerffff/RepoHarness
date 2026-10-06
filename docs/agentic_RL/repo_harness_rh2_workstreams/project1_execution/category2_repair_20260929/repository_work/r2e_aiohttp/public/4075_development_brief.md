# aiohttp 4075 公开开发说明

工作区为 `/testbed`，`python` 指向 `/testbed/.venv/bin/python`（Python 3.9.21），aiohttp 从当前仓库导入。环境没有外网，使用已安装的依赖即可。修复范围以题面和仓库公开代码为准。

题面的两个函数使用 Python 请求解析器。可按下面方式创建 `parser`，把题面中的函数分别放入两个独立脚本运行，避免第一个异常遮住第二个结果：

```python
import asyncio
from unittest import mock
from aiohttp import http_parser

loop = asyncio.new_event_loop()
try:
    parser = http_parser.HttpRequestParserPy(mock.Mock(), loop, 2**16)
    # 在这里调用题面的 test_invalid_header(parser)
    # 或单独调用 test_malformed_status_line(parser)。
finally:
    loop.close()
```

可使用下面的公开解析器回归命令。它先检查当前环境是否能导入 C 扩展；无法导入时，沿公开测试已有条件跳过依赖该扩展的检查。`dev_mode` 参数不在本环境这条开发路径内。

```bash
cd /testbed
if python -c "import aiohttp._http_parser" 2>/dev/null; then
    echo 'C parser importable'
else
    export AIOHTTP_NO_EXTENSIONS=1
    echo 'C parser not importable; using the Python parser test path'
fi
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider \
    -o addopts="" -m "not dev_mode" -q -rfEs tests/test_http_parser.py
```

这份说明提供已验证的运行方法；测试范围仍按你实际执行的命令和输出记录。
