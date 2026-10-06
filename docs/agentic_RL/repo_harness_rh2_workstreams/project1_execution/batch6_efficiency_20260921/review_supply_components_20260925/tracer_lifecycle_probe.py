"""CPU / localhost-only component probe for 69ea494f.

Real gateway + fake local HTTP upstream; real relay helper + fake DockerRunner.
No Docker, public upstream, production network, or production file mutation.
Run with rh2/.venv/bin/python. Evidence is written beside this script.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS

from aiohttp import ClientPayloadError, ClientSession, ClientTimeout, web

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
SRC = ROOT / "rh2/src/repoharness2/adapters/slime"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gw = load("tracer_pkg_gateway", SRC / "pkg_index_gateway.py")
sp = load("tracer_sandbox_profile", SRC / "sandbox_profile.py")


async def gateway_case(action):
    continue_file = asyncio.Event()
    upstream_done = asyncio.Event()

    async def simple(_request):
        return web.Response(text='<a href="/files/demo-1.0.tar.gz">demo-1.0.tar.gz</a>', content_type="text/html")

    async def file(request):
        response = web.StreamResponse(headers={"Content-Length": "10"})
        await response.prepare(request)
        await response.write(b"HEAD!")
        try:
            await continue_file.wait()
            await response.write(b"TAIL!")
            await response.write_eof()
        except (ConnectionError, RuntimeError):
            pass
        finally:
            upstream_done.set()
        return response

    app = web.Application()
    app.router.add_get("/simple/demo/", simple)
    app.router.add_get("/files/demo-1.0.tar.gz", file)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    upstream_port = runner.addresses[0][1]
    log = HERE / f"tracer_gateway_{action}.jsonl"
    log.write_text("")
    gateway = gw.PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{upstream_port}/simple/", log_path=log)
    gateway_port = await gateway.start("127.0.0.1", 0)
    base = f"http://127.0.0.1:{gateway_port}"
    token = gateway.issue(gw.SupplyGrant.build(attempt_id=f"probe-{action}", task_id="demo", plane="grading", phase="install"))
    try:
        async with ClientSession(timeout=ClientTimeout(total=5)) as client:
            async with client.get(base + gateway.index_path(token) + "demo/") as page:
                href = re.search(r'href="([^"]+)"', await page.text()).group(1)
            async with client.get(base + href) as response:
                first = await response.content.readexactly(5)
                summary_at_release = None
                if action == "release":
                    summary_at_release = gateway.release(token)
                else:
                    assert gateway.withdraw(token)
                async with client.get(base + href) as later:
                    later_status = later.status
                    await later.read()
                tail_task = asyncio.create_task(response.read())
                await asyncio.sleep(0.2)
                still_open_while_upstream_paused = not tail_task.done()
                continue_file.set()
                try:
                    tail = await tail_task
                    outcome = "complete"
                except ClientPayloadError:
                    tail = b""
                    outcome = "ClientPayloadError"
                await upstream_done.wait()
                if action == "withdraw":
                    summary_at_release = gateway.release(token)
            rows = [json.loads(line) for line in log.read_text().splitlines()]
            facts = {
                "action": action,
                "future_request_status": later_status,
                "still_open_200ms_after_action_while_upstream_paused": still_open_while_upstream_paused,
                "inflight_outcome": outcome,
                "inflight_delivered_bytes": len(first + tail),
                "active_tokens_after_release": gateway.active_token_count(),
                "release_summary": summary_at_release,
                "logged_file_decisions": [r["decision"] for r in rows if r["kind"] == "file"],
                "logged_attempt_file_bytes": sum(r.get("bytes", 0) for r in rows if r["kind"] == "file"),
            }
            if action == "release":
                assert later_status == 404 and outcome == "complete" and first + tail == b"HEAD!TAIL!"
                assert summary_at_release["stats"].get("bytes", 0) == 0
                assert facts["logged_attempt_file_bytes"] == 10
            else:
                assert later_status == 403 and outcome == "ClientPayloadError"
                assert "withdrawn_mid_stream" in facts["logged_file_decisions"]
            return facts
    finally:
        continue_file.set()
        await gateway.stop()
        await runner.cleanup()


class RelayFake:
    def __init__(self, cancel):
        self.cancel = cancel
        self.probe_entered = asyncio.Event()
        self.calls = []
        self.alive = False

    async def __call__(self, *args):
        self.calls.append(args[0])
        if args[0] == "run":
            self.alive = True
            return sp._Exec(0, "fake-cid\n", "")
        if args[0] == "exec":
            self.probe_entered.set()
            if self.cancel:
                await asyncio.Event().wait()
            return sp._Exec(1, "", "not listening")
        if args[0] == "rm":
            self.alive = False
            return sp._Exec(0, "", "")
        raise AssertionError(args)


async def relay_case(cancel):
    docker = RelayFake(cancel)
    task = asyncio.create_task(sp.start_supply_relay(
        docker, NS(relay_image="python@sha256:" + "a" * 64), gateway_host="127.0.0.1", gateway_port=1234,
        run_id="tracer-lifecycle", ready_timeout=0.0))
    await docker.probe_entered.wait()
    if cancel:
        task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        failure = "CancelledError"
    except sp.SandboxNetworkError as exc:
        failure = exc.reason_code
    facts = {"case": "cancel_during_ready" if cancel else "not_ready_control", "error": failure,
             "docker_commands": docker.calls, "fake_container_left_alive": docker.alive}
    assert docker.alive is cancel
    assert ("rm" in docker.calls) is (not cancel)
    return facts


async def main():
    result = {
        "scope": "components only; gateway is not wired into production bringup/manager",
        "gateway": [await gateway_case("release"), await gateway_case("withdraw")],
        "relay": [await relay_case(True), await relay_case(False)],
    }
    (HERE / "tracer_lifecycle_probe.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


asyncio.run(main())
