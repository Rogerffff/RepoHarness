"""公开复现（E06，只据公开题面）：aiohttp 240da100 —— ProxyConnector 把请求 URL 的端口从 req.path 里丢掉。

题面示例原样试一次（先试 `from aiohttp import ProxyConnector, ClientRequest`；要连 proxy.example.com，沙箱无网络，
预期连不上，打印异常）；再做最小等价调用：把父类 TCPConnector._create_connection 换成返回假 transport/protocol 的协程
（不出网），其余照题面。判定：req.path 丢了 ':1234' → REPRO_OBSERVED=1。
"""
import asyncio
import os
import sys
from unittest import mock

try:
    import aiohttp
    IMPORT = "direct"
except ImportError as exc:
    sys.path.insert(0, os.getcwd())
    IMPORT = f"cwd_fallback({type(exc).__name__})"
    import aiohttp
from aiohttp import ProxyConnector
from aiohttp import connector as connector_mod

print("REPRO_IMPORT=" + IMPORT, aiohttp.__file__, aiohttp.__version__)
try:
    from aiohttp import ClientRequest
    print("literal import: ok")
except ImportError as exc:
    print("literal import:", type(exc).__name__, exc)
    from aiohttp.client import ClientRequest


def attempt(fake_parent):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    connector = ProxyConnector('http://proxy.example.com', loop=loop)
    req = ClientRequest('GET', 'http://localhost:1234/path', loop=loop)
    try:
        if fake_parent:
            async def fake(self, proxy_req, **kwargs):
                return mock.Mock(), mock.Mock()
            with mock.patch.object(connector_mod.TCPConnector, '_create_connection', fake):
                loop.run_until_complete(asyncio.wait_for(connector._create_connection(req), 20))
        else:
            loop.run_until_complete(asyncio.wait_for(connector._create_connection(req), 20))
        return req.path, None
    except Exception as exc:
        return req.path, f"{type(exc).__name__}: {exc}"[:160]
    finally:
        loop.close()


print("literal example (real network path):", attempt(False))
path, err = attempt(True)
print("offline equivalent: req.path =", repr(path), "error =", err)
if err is None and path == 'http://localhost/path':
    print("REPRO_OBSERVED=1 (port dropped; expected 'http://localhost:1234/path')")
else:
    print("REPRO_OBSERVED=0 reason=path=%r err=%r" % (path, err))
