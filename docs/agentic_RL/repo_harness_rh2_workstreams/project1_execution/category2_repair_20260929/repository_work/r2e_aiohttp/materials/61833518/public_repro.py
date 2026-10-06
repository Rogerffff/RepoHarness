import zlib
from unittest import mock
from aiohttp import protocol

payload = b'data'
compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
compressed_data = compressor.compress(payload) + compressor.flush()

# 检查传给 write() 的实际字节，而不是 mock.call 对象本身的真值。
transport = mock.Mock()
msg = protocol.Response(transport, 200)
msg.add_headers(('content-length', str(len(compressed_data))))
msg.add_chunking_filter(2)
msg.add_compression_filter('deflate')
msg.send_headers()
msg.write(payload)
msg.write_eof()
chunks = [call.args[0] for call in transport.write.call_args_list]
assert all(chunks), chunks

# HTTP/1.1 chunked 路径：终止块应在末尾，解压后仍有完整载荷。
transport = mock.Mock()
msg = protocol.Response(transport, 200)
msg.add_compression_filter('deflate')
msg.send_headers()
msg.write(payload)
msg.write_eof()
wire = b''.join(call.args[0] for call in transport.write.call_args_list)
headers, rest = wire.split(b'\r\n\r\n', 1)
assert b'transfer-encoding: chunked' in headers.lower()
data = []
while True:
    line, separator, rest = rest.partition(b'\r\n')
    assert separator, 'missing chunk size'
    size = int(line, 16)
    if size == 0:
        assert rest == b'\r\n', 'data after the terminating chunk'
        break
    assert len(rest) >= size + 2 and rest[size:size + 2] == b'\r\n'
    data.append(rest[:size])
    rest = rest[size + 2:]
assert zlib.decompress(b''.join(data), -zlib.MAX_WBITS) == payload
