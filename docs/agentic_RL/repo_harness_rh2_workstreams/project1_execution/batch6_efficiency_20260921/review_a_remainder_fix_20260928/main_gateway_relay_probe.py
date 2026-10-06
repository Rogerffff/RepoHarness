"""修后对照：沿用上一轮真实 HTTP / Docker 探针，仅更新预期与输出路径。

无公网/远端；只清理本脚本的随机名字；不改生产源码。
PYTHONPATH=rh2/src rh2/.venv/bin/python <本文件>
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path

from aiohttp import ClientPayloadError, ClientSession, web

from repoharness2.adapters.slime import sandbox_profile as sp
from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway, SupplyGrant

HERE = Path(__file__).resolve().parent


async def release_case(cancel_owner):
    resume = asyncio.Event()

    async def page(_request):
        return web.Response(text='<a href="/files/demo-1.0.tar.gz">demo-1.0.tar.gz</a>', content_type="text/html")

    async def file(request):
        response = web.StreamResponse(headers={"Content-Length": "10"})
        await response.prepare(request)
        await response.write(b"FIRST")
        await resume.wait()
        try:
            await response.write(b"LAST!")
            await response.write_eof()
        except ConnectionError:
            pass
        return response

    upstream = web.Application()
    upstream.router.add_get("/simple/demo/", page)
    upstream.router.add_get("/files/demo-1.0.tar.gz", file)
    runner = web.AppRunner(upstream, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    gateway = PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{runner.addresses[0][1]}/simple/")
    port = await gateway.start("127.0.0.1", 0)
    base = f"http://127.0.0.1:{port}"
    token = gateway.issue(SupplyGrant.build(attempt_id="review", task_id="demo", plane="grading", phase="install"))
    try:
        async with ClientSession() as client:
            async with client.get(base + gateway.index_path(token) + "demo/") as page_response:
                href = re.search(r'href="([^"]+)"', await page_response.text()).group(1)
            async with client.get(base + href) as download:
                assert await download.content.readexactly(5) == b"FIRST"
                releasing = asyncio.create_task(gateway.release(token))
                await asyncio.sleep(0)  # owner 已进入 asyncio.wait，请求取消的收尾尚可交错
                summary = None
                if cancel_owner:
                    assert not releasing.done()
                    releasing.cancel()
                try:
                    summary = await releasing
                    owner_result = "returned"
                except asyncio.CancelledError:
                    owner_result = "CancelledError"
                try:
                    await download.read()
                    client_result = "completed"
                except ClientPayloadError:
                    client_result = "ClientPayloadError"
            await asyncio.sleep(0)
            retry_summary = await gateway.release(token)
            state = gateway._tokens.get(token)
            async with client.get(base + gateway.index_path(token) + "demo/") as later:
                later_status = later.status
            facts = {
                "cancel_owner": cancel_owner, "owner_result": owner_result, "client_result": client_result,
                "summary": summary, "retry_summary": retry_summary,
                "token_count_after_retry": gateway.active_token_count(), "new_request_status": later_status,
                "gateway_totals": gateway.summary()["totals"],
                "state_after_retry": None if state is None else {"state": state.state, "releasing": state.releasing,
                                                                  "inflight": len(state.inflight)},
            }
            if cancel_owner:
                assert owner_result == "CancelledError" and state is None
                assert retry_summary is None and gateway.active_token_count() == 0 and later_status == 404
                assert gateway.summary()["totals"]["tokens_release_interrupted"] == 1
            else:
                assert summary["complete"] and summary["stats"]["bytes"] == 5
                assert state is None and gateway.active_token_count() == 0 and later_status == 404
            return facts
    finally:
        resume.set()
        await gateway.stop()
        await runner.cleanup()


async def relay_collision():
    image = await sp.default_docker_runner("image", "inspect", sp.RELAY_IMAGE_DEFAULT)
    if image.exit_code:
        return {"skipped": "未找到本机镜像或 Docker；未自动拉镜像"}
    run_id = f"codex-owner-{uuid.uuid4().hex[:8]}"
    name = f"rh2-supply-relay-{run_id}"
    profile = sp.RolloutSandboxProfile(model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1234)
    labels = ("--label", f"rh2.run_id={run_id}")
    try:
        first = await sp.start_supply_relay(sp.default_docker_runner, profile, gateway_host="127.0.0.1",
                                             gateway_port=1234, run_id=run_id, labels=labels)
        before = await sp.default_docker_runner("inspect", "-f", "{{.State.Running}}", first.container_name)
        assert before.exit_code == 0 and before.stdout.strip() == "true"
        try:
            await sp.start_supply_relay(sp.default_docker_runner, profile, gateway_host="127.0.0.1",
                                       gateway_port=1234, run_id=run_id, labels=labels)
        except sp.SandboxNetworkError as exc:
            error = {"reason": exc.reason_code, "name_conflict": "already in use" in str(exc)}
        after = await sp.default_docker_runner("inspect", "-f", "{{.State.Running}}", first.container_name)
        facts = {"second_start": error, "first_running_before": True, "first_inspect_exit_after": after.exit_code,
                 "first_stdout_after": after.stdout.strip(), "first_stderr_after": after.stderr.strip()}
        assert error["name_conflict"] and after.exit_code == 0 and after.stdout.strip() == "true"
        return facts
    finally:
        await sp.default_docker_runner("rm", "-f", name)
        left = await sp.default_docker_runner("ps", "-aq", "--filter", f"label=rh2.run_id={run_id}")
        assert left.exit_code == 0 and not left.stdout.strip()


async def main():
    result = {"head": "a31cdcd0", "release": [await release_case(False), await release_case(True)], "relay_collision": await relay_collision()}
    (HERE / "main_gateway_relay_probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


asyncio.run(main())
