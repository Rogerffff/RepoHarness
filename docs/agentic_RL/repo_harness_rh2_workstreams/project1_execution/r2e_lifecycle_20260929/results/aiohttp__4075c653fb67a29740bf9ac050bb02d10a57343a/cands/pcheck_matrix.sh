#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 /testbed/.venv/bin/python - <<'EOF'
import asyncio
from unittest import mock

import aiohttp.http_parser as hp

CASES = [  # (name, parser kind, raw bytes)
    ("ex_hdr_name_ff", "req", b"POST / HTTP/1.1\r\n\xc3\xbfoo: bar\r\n\r\n"),
    ("hdr_name_cyr_o", "req", b"POST / HTTP/1.1\r\nf\xd0\xbeo: bar\r\n\r\n"),
    ("hdr_name_raw_e9", "req", b"POST / HTTP/1.1\r\nf\xe9o: bar\r\n\r\n"),
    ("hdr_name_slash", "req", b"POST / HTTP/1.1\r\nFo/o: bar\r\n\r\n"),
    ("ex_reqline_lf_ff", "req", b"GET\n/path\x0cHTTP/1.1\r\n\r\n"),
    ("reqline_ff_sep", "req", b"GET /path\x0cHTTP/1.1\r\n\r\n"),
    ("reqline_vt_sep", "req", b"GET\x0b/path HTTP/1.1\r\n\r\n"),
    ("reqline_tab_sep", "req", b"GET\t/path HTTP/1.1\r\n\r\n"),
    ("target_lf", "req", b"GET /pa\nth HTTP/1.1\r\n\r\n"),
    ("target_ff", "req", b"GET /pa\x0cth HTTP/1.1\r\n\r\n"),
    ("target_cr", "req", b"GET /pa\rth HTTP/1.1\r\n\r\n"),
    ("target_tab", "req", b"GET /pa\tth HTTP/1.1\r\n\r\n"),
    ("target_ctl01", "req", b"GET /pa\x01th HTTP/1.1\r\n\r\n"),
    ("version_ff", "req", b"GET /path HTTP/1\x0c1\r\n\r\n"),
    ("double_sp", "req", b"GET  /path HTTP/1.1\r\n\r\n"),
    ("keep_plain", "req", b"GET /path HTTP/1.1\r\n\r\n"),
    ("keep_utf8_value", "req", b"GET /path HTTP/1.1\r\nx-test:\xd1\x82\xd0\xb5\xd1\x81\xd1\x82\r\n\r\n"),
    ("keep_utf8_path", "req", b"GET /\xd0\xbf\xd1\x83\xd1\x82\xd1\x8c HTTP/1.1\r\n\r\n"),
    ("keep_nonascii_uri", "req", b"GET \xff HTTP/1.1\r\n\r\n"),
    ("keep_getpath", "req", b"getpath \r\n\r\n"),
    ("resp_nonascii_name", "resp", b"HTTP/1.1 200 OK\r\n\xc3\xbfoo: bar\r\n\r\n"),
    ("resp_no_reason", "resp", b"HTTP/1.1 200\r\n\r\n"),
]

loop = asyncio.new_event_loop()
for name, kind, data in CASES:
    cls = hp.HttpRequestParserPy if kind == "req" else hp.HttpResponseParserPy
    p = cls(mock.Mock(), loop, 2**16, max_line_size=8190, max_headers=32768, max_field_size=8190)
    try:
        msgs = p.feed_data(data)[0]
        out = "ACCEPT " + ascii([(getattr(m, "method", None), getattr(m, "path", None), list(m.headers.items())) for m, _ in msgs])
    except Exception as e:
        out = type(e).__name__ + " " + ascii(str(e))[:90]
    print(name.ljust(20), out)
loop.close()
EOF
echo RH2_CMD_RC=$?
