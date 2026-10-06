"""R1 第二次窄复核：每案从干净子进程的真实 BringupService 进入真实 HTTP 端口。

复用上轮 HTTP 请求动作；仅把 TestClient 传输换成真实服务端口，模型生成和 abort IO 用内存替身。
不调用 async_start、Docker、CC 或模型 API；旧探针不修改。
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "followup"))
import cap_body_race_probe as body_probe
import cap_wrapper_followup_probe as cap_probe
sys.path.insert(0, str(body_probe.ROOT / "rh2/tests/adapters"))

import aiohttp
import pytest
from slime.agent.adapters import common as slime_common
from slime.agent.adapters import anthropic as anthropic_module
from test_w3b_bringup_sandbox_runtime import _service
from repoharness2.adapters.slime import bringup
from repoharness2.adapters.slime.engine_router_client import AbortBroadcastResult


class ThreadEvent:
    """仅替身 IO 的跨线程释放信号；避免把 asyncio.Event 绑定到错误的 loop。"""
    def __init__(self):
        self.event = threading.Event()

    def set(self):
        self.event.set()

    def is_set(self):
        return self.event.is_set()

    async def wait(self):
        while not self.event.is_set():
            await asyncio.sleep(0.001)


class Engine(body_probe.Engine):
    def reset(self):
        self.entered, self.release, self.cancelled = ThreadEvent(), ThreadEvent(), ThreadEvent()
        self.calls = self.aborts = 0


async def child(case):
    # 不依赖 fixture 重置来声称干净：构造服务前实际类方法必须尚未包装。
    before = slime_common.BaseAdapter._run_turn
    assert before.__name__ == "_run_turn"
    assert getattr(slime_common, "_rh2_capture_wire_registry", None) is None
    assert getattr(slime_common, "_rh2_turn_budget_wire_registry", None) is None
    cap = 3 if case == "parallel_multiple_refusals" else 1
    with tempfile.TemporaryDirectory(prefix="route-", dir=HERE) as temp, pytest.MonkeyPatch.context() as mp:
        mp.setattr(bringup, "MAX_TURNS_PER_SID", cap)
        if case == "startup_rejects_stale_route":
            def stale_registration(adapter, app):
                app.router.add_post("/v1/messages", before.__get__(adapter))
                app.router.add_post("/v1/messages/count_tokens", anthropic_module._count_tokens)

            mp.setattr(anthropic_module.AnthropicAdapter, "_register_routes", stale_registration)
            try:
                _service(mp, Path(temp), mode="fa_audit_only", docker=None)
            except bringup.StartupCheckError as exc:
                assert exc.reason_code == "turn_budget_wire_not_bound_to_route"
                return {"case": case, "preconstruct_method": before.__name__,
                        "reason_code": exc.reason_code, "detail": str(exc),
                        "adapter_threads_started": sum(t.name == "rh2-anthropic-adapter" for t in threading.enumerate())}
            raise AssertionError("启动核对未拒绝明确绑定旧 handler 的 app")

        _, service = _service(mp, Path(temp), mode="fa_audit_only", docker=None)
        try:
            route = next(r for r in service.adapter.app.router.routes()
                         if r.method == "POST" and r.resource.canonical == "/v1/messages")
            facts = {"case": case, "entry": "BringupService.__init__ → real HTTP thread",
                     "preconstruct_method": before.__name__, "route_handler": route.handler.__func__.__name__,
                     "route_uses_current_method": route.handler.__func__ is slime_common.BaseAdapter._run_turn,
                     "route_bound_to_service_adapter": route.handler.__self__ is service.adapter,
                     "real_http_thread_constructed": service.app_handle.port > 0,
                     "vendor_module": str(Path(slime_common.__file__).relative_to(body_probe.ROOT)), "cap": cap}
            assert facts["route_uses_current_method"] and facts["route_bound_to_service_adapter"]
            body_probe.cw.assert_turn_pipeline_bound_to_routes(service.adapter)
            # async_start 的同一生产工厂；本探针不启动其 Docker/API 检查。
            body_probe.build_production_model_call_proxy(service.registry, lambda: "3", require_real=False, artifact_sink=None)
            engine = Engine()
            engine.reset()
            mp.setattr(body_probe.cw, "aiohttp", body_probe.EngineAiohttp(engine))

            async def abort_io(rid):
                engine.aborts += 1
                return AbortBroadcastResult(rid, "delivered", "verified_set", ("memory-engine",), ("memory-engine",), {})

            service.registry.engine_abort = abort_io

            class RealClient:
                def __init__(self, app):
                    assert app is service.adapter.app
                    self.http = None

                async def start_server(self):
                    self.http = aiohttp.ClientSession()

                async def post(self, path, **kwargs):
                    return await self.http.post(f"http://127.0.0.1:{service.app_handle.port}{path}", **kwargs)

                async def close(self):
                    await self.http.close()

            assert cap_probe.old is body_probe
            mp.setattr(body_probe, "TestServer", lambda app, **kwargs: app)
            mp.setattr(body_probe, "TestClient", RealClient)
            if case in {"sequential_inflight", "split_body_race"}:
                observation = await body_probe.case(service.registry, service.adapter, engine, case,
                                                     split_bodies=case == "split_body_race", close_on_refusal=False)
                assert not observation["early"]["refusal_before_generation_release"]
                assert observation["early"]["notified"] == []
                assert observation["statuses"] == [200, 403] and observation["captures"] == 1
                assert observation["capture_status"] == ["complete"] and observation["poison"] is None
                assert observation["leaf_response_tokens"] == [[7, 8]] and observation["capture_bindings"] == 1
            else:
                total = 5 if cap == 3 else 3 if case == "waiter_cancelled" else 2
                observation = await cap_probe.new_wrapper_case(
                    service.registry, service.adapter, engine, case, cap=cap, total=total,
                    cancel_waiter=case == "waiter_cancelled", poison_admitted=case == "admitted_cancel_poison",
                )
            facts["http_observation"] = observation
        finally:
            service.app_handle.stop()
        facts["http_thread_stopped"] = not service.app_handle.thread.is_alive()
        assert facts["http_thread_stopped"]
        return facts


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--case":
        print(json.dumps(asyncio.run(child(sys.argv[2])), ensure_ascii=False))
        return
    rows = []
    for case in ["sequential_inflight", "split_body_race", "parallel_multiple_refusals",
                 "waiter_cancelled", "admitted_cancel_poison", "startup_rejects_stale_route"]:
        done = subprocess.run([sys.executable, "-B", __file__, "--case", case], capture_output=True, text=True, timeout=40)
        if done.returncode:
            print(done.stdout)
            print(done.stderr, file=sys.stderr)
            raise SystemExit(done.returncode)
        row = json.loads(done.stdout.strip().splitlines()[-1])
        if case == "startup_rejects_stale_route":
            assert row["adapter_threads_started"] == 0
        rows.append(row)
    result = json.dumps(rows, ensure_ascii=False, indent=2)
    (HERE / "production_route_result.json").write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    main()
