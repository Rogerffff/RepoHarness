"""预算计划的窄反证：只运行替身子进程与本机回环 HTTP，不调用 Docker/GPU。"""

from __future__ import annotations

import asyncio
import json
import types
from unittest.mock import patch

from aiohttp import web

from repoharness2.adapters.slime import docker_sandbox
from repoharness2.adapters.slime.async_worker import (
    ModelCallProxy,
    SessionPoisonRegistry,
    StaticActiveCoordinator,
    UnattributableModelCallError,
)
from repoharness2.adapters.slime.sandbox_profile import _RELAY_SCRIPT


async def probe_deadline_reason() -> dict:
    """按计划在 _send 抛 deadline typed 码，观察真实 proxy.call 的外部结果。"""
    proxy = ModelCallProxy(StaticActiveCoordinator(lambda: "1"))
    poison = SessionPoisonRegistry()

    async def deadline_send(self, send_fn, n, deadline_monotonic=None):
        raise UnattributableModelCallError("episode_deadline_exhausted", "探针模拟排队到点")

    async def never_send(n):
        raise AssertionError("不得发送模型请求")

    proxy._send = types.MethodType(deadline_send, proxy)
    try:
        await proxy.call("deadline-execution", "t1", never_send, poison_registry=poison)
    except UnattributableModelCallError as exc:
        result = {"raised_reason": exc.reason_code, "poison_reason": poison.reason("deadline-execution")}
        assert result["raised_reason"] == "no_overlapping_update_window", result
        return result
    raise AssertionError("缺少预期异常")


async def probe_docker_cli_cancel() -> dict:
    """取消真实 DockerSandbox 通道，但用 FakeProcess 防止启动任何外部进程。"""
    entered = asyncio.Event()

    class FakeProcess:
        returncode = None
        killed = False
        waited = False

        async def communicate(self, input=None):
            entered.set()
            await asyncio.Event().wait()

        def kill(self):
            self.killed = True

        async def wait(self):
            self.waited = True

    proc = FakeProcess()

    async def fake_spawn(*args, **kwargs):
        return proc

    with patch.object(docker_sandbox.asyncio, "create_subprocess_exec", fake_spawn):
        task = asyncio.create_task(docker_sandbox._run("exec", "fake-container", "true", timeout=900))
        await entered.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    result = {"kill_called": proc.killed, "wait_called": proc.waited}
    assert result == {"kill_called": False, "wait_called": False}, result
    return result


async def probe_relay_disconnect() -> dict:
    """使用生产 relay 的原函数，检查回环 HTTP 断连能否取消上游 proxy。"""
    entered = asyncio.Event()
    cancelled = asyncio.Event()
    poison = SessionPoisonRegistry()
    proxy = ModelCallProxy(StaticActiveCoordinator(lambda: "1"))

    async def model_send(n):
        entered.set()
        await asyncio.Event().wait()

    async def handler(request):
        try:
            await proxy.call("relay-execution", "t1", model_send, poison_registry=poison)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return web.Response(text="不可到达")

    app = web.Application()
    app.router.add_post("/v1/messages", handler)
    runner = web.AppRunner(app, handler_cancellation=True)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    upstream_port = site._server.sockets[0].getsockname()[1]
    namespace = {}
    with patch.dict("os.environ", {"RH2_RELAY_MAP": "0:127.0.0.1:1"}):
        exec(_RELAY_SCRIPT.split("async def main():", 1)[0], namespace)
    relay = await asyncio.start_server(
        lambda r, w: namespace["handle"](r, w, ("127.0.0.1", upstream_port)),
        "127.0.0.1",
        0,
    )
    relay_port = relay.sockets[0].getsockname()[1]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", relay_port)
        writer.write(b"POST /v1/messages HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{}")
        await writer.drain()
        await asyncio.wait_for(entered.wait(), 2)
        writer.close()
        await writer.wait_closed()
        await asyncio.wait_for(cancelled.wait(), 2)
        result = {"handler_cancelled": cancelled.is_set(), "poison_reason": poison.reason("relay-execution")}
        assert result == {"handler_cancelled": True, "poison_reason": "client_cancelled"}, result
        return result
    finally:
        relay.close()
        await relay.wait_closed()
        await runner.cleanup()


async def main():
    result = {
        "deadline_reason": await probe_deadline_reason(),
        "docker_cli_cancel": await probe_docker_cli_cancel(),
        "relay_disconnect": await probe_relay_disconnect(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
