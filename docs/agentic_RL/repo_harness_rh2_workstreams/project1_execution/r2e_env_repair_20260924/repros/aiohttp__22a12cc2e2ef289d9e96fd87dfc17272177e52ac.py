"""公开复现（E06，只据公开题面）：aiohttp 22a12cc2 —— HTTPS 连接指定服务器指纹时，指纹不符不抛 ServerFingerprintMismatch。

题面示例要连 https://example.com（沙箱无网络），且 fingerprint='incorrect_fingerprint' 在此版本因长度非法直接 ValueError。
所以 (1) 原样构造题面的 TCPConnector，打印结果；(2) 最小等价调用：127.0.0.1 起 TLS 服务（证书用 venv 已装的测试依赖
trustme 现生成，仓库 tests/conftest.py 也用它——这是对"标准库 + 本仓库包"规则的说明性例外），客户端
TCPConnector(ssl=Fingerprint(不匹配的 32 字节)) 直连 GET。推断依据：题面只说 "HTTPS connections with specified server
fingerprints"，没提代理或别的连接路径。判定：直连请求成功、不抛 ServerFingerprintMismatch → REPRO_OBSERVED=1。
"""
import asyncio
import os
import ssl
import sys

try:
    import aiohttp
    IMPORT = "direct"
except ImportError as exc:
    sys.path.insert(0, os.getcwd())
    IMPORT = f"cwd_fallback({type(exc).__name__})"
    import aiohttp
import trustme

print("REPRO_IMPORT=" + IMPORT, aiohttp.__file__, aiohttp.__version__)


async def handle(reader, writer):
    try:
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()


async def main():
    try:
        aiohttp.TCPConnector(fingerprint="incorrect_fingerprint")
        print("literal: TCPConnector(fingerprint='incorrect_fingerprint') accepted")
    except Exception as exc:
        print("literal:", type(exc).__name__, exc)
    server_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    trustme.CA().issue_cert("127.0.0.1").configure_cert(server_ctx)
    srv = await asyncio.start_server(handle, "127.0.0.1", 0, ssl=server_ctx)
    port = srv.sockets[0].getsockname()[1]
    wrong = aiohttp.Fingerprint(b"\x00" * 32)
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=wrong)) as session:
            async with session.get(f"https://127.0.0.1:{port}/") as resp:
                print("direct: no exception, status", resp.status, await resp.text())
                return "REPRO_OBSERVED=1 (direct HTTPS with a mismatching fingerprint succeeded)"
    except aiohttp.ServerFingerprintMismatch as exc:
        print("direct: ServerFingerprintMismatch", exc)
        return "REPRO_OBSERVED=0 reason=direct HTTPS already raises ServerFingerprintMismatch on base"
    finally:
        srv.close()


print(asyncio.run(asyncio.wait_for(main(), 60)))
