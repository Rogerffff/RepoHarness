"""公开复现（E06，只据公开题面）：aiohttp 4075c653 —— HTTP 解析器不拒绝含非法字符的头部与畸形请求行。

题面两段示例依赖测试夹具 parser；最小等价调用：直接构造纯 Python 解析器 HttpRequestParserPy，喂题面给出的两段数据。
第一段按题面意图用文本 "\\xffoo: bar" 编码（题面把 bytes 嵌进 f-string 的写法是笔误，按字面会变成 "b'...'" 文本）。
另打印默认 HttpRequestParser 是 C 扩展还是纯 Python。判定：任一段没抛题面要求的异常类型 → REPRO_OBSERVED=1。
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
from aiohttp import http_exceptions
from aiohttp.http_parser import HttpRequestParser, HttpRequestParserPy

print("REPRO_IMPORT=" + IMPORT, aiohttp.__file__, aiohttp.__version__)
print("default HttpRequestParser:", HttpRequestParser.__module__,
      "(pure Python)" if HttpRequestParser is HttpRequestParserPy else "(C extension)")
loop = asyncio.new_event_loop()
cases = [
    ("invalid_header", "POST / HTTP/1.1\r\n\xffoo: bar\r\n\r\n".encode(), http_exceptions.BadHttpMessage),
    ("malformed_status_line", b"GET\n/path\x0cHTTP/1.1\r\n\r\n", http_exceptions.BadStatusLine),
]
missing = []
for name, data, want in cases:
    parser = HttpRequestParserPy(mock.Mock(), loop, 2 ** 16, max_line_size=8190, max_field_size=8190)
    try:
        messages, upgraded, tail = parser.feed_data(data)
        print(f"{name}: no exception; parsed {len(messages)} message(s): {[m[0][:3] for m in messages]!r}"[:220])
        missing.append(name)
    except Exception as exc:
        ok = isinstance(exc, want)
        print(f"{name}: raised {type(exc).__name__} (wanted {want.__name__}: {'yes' if ok else 'no'}) {exc!r}"[:220])
        if not ok:
            missing.append(name)
loop.close()
if missing:
    print("REPRO_OBSERVED=1 (not rejected as required: %s)" % missing)
else:
    print("REPRO_OBSERVED=0 reason=both inputs rejected with the required exception type")
