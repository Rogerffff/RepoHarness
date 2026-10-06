# aiohttp 6183 公开开发说明

工作区为 `/testbed`，`python` 指向 `/testbed/.venv/bin/python`（Python 3.9.21）。当前仓库是旧版 aiohttp，使用已安装依赖即可；环境没有外网。

题面两段示例可分开运行，避免第一段断言失败后看不到第二段的结果。每个独立脚本都可以使用下面的导入；第二段也需定义 `payload = b'data'`：

```python
import zlib
from unittest import mock
from aiohttp import protocol
```

第一段读取实际 `transport.write()` 参数，第二段解析线上 chunked 字节并解压载荷。合法响应末尾的零长度终止块仍需保留；具体要求以题面为准。

相关公开回归使用 protocol 测试文件：

```bash
cd /testbed
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider \
    --color=no -rfE tests/test_http_protocol.py
```

这条命令实跑会打印旧 asyncio API 的弃用警告；应查看测试断言与退出结果。其它客户端／服务端模块未在这条开发路径中验证。
