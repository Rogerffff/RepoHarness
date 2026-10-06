import asyncio
from unittest import mock
from aiohttp import ProxyConnector
from aiohttp.client import ClientRequest

loop = asyncio.new_event_loop()
transport, protocol = mock.Mock(), mock.Mock()
connected = loop.create_future()
connected.set_result((transport, protocol))
transport_loop = mock.Mock()
transport_loop.create_connection.return_value = connected
connector = ProxyConnector('http://proxy.example.com', loop=transport_loop)
try:
    req = ClientRequest('GET', 'http://localhost:1234/path', loop=loop)
    loop.run_until_complete(connector.connect(req))
    print(req.path)
    assert req.path == 'http://localhost:1234/path'
finally:
    connector.close()
    loop.close()
