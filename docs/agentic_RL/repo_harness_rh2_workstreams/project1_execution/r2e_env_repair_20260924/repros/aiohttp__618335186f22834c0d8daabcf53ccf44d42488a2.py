"""公开复现（E06，只据公开题面）：aiohttp 61833518 —— deflate 压缩 + 分块时写出空块，分块传输下等于提前 EOF。

(A) 照题面示例：content-length + add_chunking_filter(2) + add_compression_filter('deflate')，mock transport，
    看 transport.write 的每次参数是否都非空（题面 `assert all(chunks)`）。
(B) 题面所说"提前 EOF"的后果：不设 content-length（HTTP/1.1 默认分块传输）+ deflate，解析分块正文，
    看零长块（EOF）之后是否还有数据。判定：A 有空写或 B 提前 EOF → REPRO_OBSERVED=1。
"""
import os
import sys
import zlib
from unittest import mock

try:
    import aiohttp
    IMPORT = "direct"
except ImportError as exc:
    sys.path.insert(0, os.getcwd())
    IMPORT = f"cwd_fallback({type(exc).__name__})"
    import aiohttp
from aiohttp import protocol

print("REPRO_IMPORT=" + IMPORT, aiohttp.__file__, aiohttp.__version__)
zc = zlib.compressobj(wbits=-zlib.MAX_WBITS)
compressed_data = zc.compress(b'data') + zc.flush()

transport = mock.Mock()
write = transport.write = mock.Mock()
msg = protocol.Response(transport, 200)
msg.add_headers(('content-length', str(len(compressed_data))))
msg.add_chunking_filter(2)
msg.add_compression_filter('deflate')
msg.send_headers()
msg.write(b'data')
msg.write_eof()
chunks = [c[1][0] for c in write.mock_calls]
empty_a = [i for i, c in enumerate(chunks) if not c]
print("A: %d write() calls %r; empty at %s" % (len(chunks), chunks[1:], empty_a))

transport_b = mock.Mock()
msg_b = protocol.Response(transport_b, 200)
msg_b.add_compression_filter('deflate')
msg_b.send_headers()
msg_b.write(b'data')
msg_b.write_eof()
body = b''.join(c[1][0] for c in transport_b.write.mock_calls).split(b'\r\n\r\n', 1)[1]
sizes, rest = [], body
while rest:
    line, _, rest = rest.partition(b'\r\n')
    sizes.append(int(line, 16))
    rest = rest[sizes[-1] + 2:]
    if sizes[-1] == 0:
        break
early_eof = bool(rest)
print("B: chunked body=%r chunk sizes=%s data_after_zero_chunk=%r" % (body[:60], sizes, rest[:40]))
if empty_a or early_eof:
    print("REPRO_OBSERVED=1 (empty chunk(s) written: %s; chunked stream ends early: %s)" % (bool(empty_a), early_eof))
else:
    print("REPRO_OBSERVED=0 reason=no empty chunk and no early EOF")
