# aiohttp 240d 公开开发说明

工作区为 `/testbed`，`python` 指向 `/testbed/.venv/bin/python`（Python 3.9.21）。这是旧版 aiohttp，使用已安装依赖；环境没有外网。

题面的复现使用 mock transport 和已完成的 `asyncio.Future`，通过真实 `ProxyConnector.connect(req)` 观察连接后的 `req.path`，不需要启动外部 HTTP 代理。`ClientRequest` 的公开导入位置为 `aiohttp.client`，具体装配以题面代码为准。

可运行对应公开代理回归：

```bash
cd /testbed
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider \
    --color=no -rfE tests/test_connector.py::ProxyConnectorTests
```

命令会打印旧 asyncio API 的弃用警告；查看测试断言与退出结果。此命令的范围是 mock transport 代理测试，没有验证其它真实 TCP／Unix 客户端和服务端模块。
