import asyncio
from unittest import mock
import aiohttp
from aiohttp.client import ClientRequest
loop = asyncio.new_event_loop()
lm = mock.Mock()
done = asyncio.Future(loop=loop)
done.set_result((mock.Mock(), mock.Mock()))
lm.create_connection.return_value = done
proxy = aiohttp.ProxyConnector("http://proxy.example.com", loop=lm)
bad = 0
cases = [
    ("http://localhost:1234/path", "http://localhost:1234/path", "localhost", 1234),
    ("http://www.python.org:8080/some/path", "http://www.python.org:8080/some/path", "www.python.org", 8080),
    ("http://localhost:8080/path?q=1", "http://localhost:8080/path?q=1", "localhost", 8080),
    ("http://www.python.org", "http://www.python.org/", "www.python.org", 80),
]
for url, want_path, want_host, want_port in cases:
    req = ClientRequest("GET", url)
    loop.run_until_complete(proxy.connect(req))
    got = (req.path, req.host, req.port)
    ok = got == (want_path, want_host, want_port)
    bad += not ok
    print("OK " if ok else "BAD", url, "->", got)
direct = aiohttp.TCPConnector(loop=lm)
lm.create_connection.reset_mock()
loop.run_until_complete(direct.connect(ClientRequest("GET", "http://localhost:1234/path")))
target = lm.create_connection.call_args[0][1:3]
ok = target == ("localhost", 1234)
bad += not ok
print("OK " if ok else "BAD", "direct TCPConnector target", target)
raise SystemExit(1 if bad else 0)
