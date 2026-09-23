"""批 C 独立 CPU 探针：真实分块 HTTP 请求体跨过 cap 守卫的竞态。

真实 vendored Anthropic app、proxy、capture stage/commit、轨迹树与 handler 取消；
只用本机 aiohttp 测试端口，SGLang 通道为显式内存替身，不使用模型 API / Docker / CC。
在 rh2 下用 uv run python <本脚本相对路径> 运行。
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
spec = importlib.util.spec_from_file_location("cap_probe_world", ROOT / "rh2/tests/adapters_miles/conftest.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
fixtures._install_ray_stub()
fixtures.install_sglang_stub()

from aiohttp.test_utils import TestClient, TestServer
from slime.agent.adapters.anthropic import AnthropicAdapter
from slime.utils.types import Sample

from repoharness2.adapters.slime import capture_wire as cw
from repoharness2.adapters.slime.bringup import build_production_model_call_proxy, make_per_rollout_adapter
from repoharness2.adapters.slime.generate import GenerationCaptureHook
from repoharness2.adapters.slime.session_capability import mint_session_capability


class Tokenizer:
    def apply_chat_template(self, *args, **kwargs):
        return [1, 2, 3]

    def decode(self, *args, **kwargs):
        return "probe reply"


class Engine:
    def reset(self):
        self.entered, self.release, self.cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()
        self.calls = 0
        self.aborts = 0


class EngineResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    async def json(self, **kwargs):
        return self.payload


class EngineContext:
    def __init__(self, engine, url, payload):
        self.engine, self.url, self.payload = engine, url, payload

    async def __aenter__(self):
        if self.url.endswith("/abort_request"):
            self.engine.aborts += 1
            return EngineResponse({})
        self.engine.calls += 1
        self.engine.entered.set()
        try:
            await self.engine.release.wait()
        except asyncio.CancelledError:
            self.engine.cancelled.set()
            raise
        return EngineResponse({
            "text": "probe reply",
            "meta_info": {
                "id": self.payload["rid"], "finish_reason": {"type": "stop"},
                "weight_version": str(getattr(self.engine, "version", "3")),
                "output_token_logprobs": [[-0.1, 7, None], [-0.1, 8, None]],
            },
        })

    async def __aexit__(self, *args):
        return False


class EngineSession:
    def __init__(self, engine):
        self.engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def post(self, url, json=None, headers=None):
        return EngineContext(self.engine, url, json)


class EngineAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self.engine = engine

    def ClientSession(self, **kwargs):
        return EngineSession(self.engine)

    def ClientTimeout(self, **kwargs):
        return None


async def until(predicate, timeout=2):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.001)


async def case(registry, adapter, engine, name, *, split_bodies, close_on_refusal):
    engine.reset()
    paid = f"exec_{name}#p1-aaaa"
    sid = f"s-{paid}"
    cap = mint_session_capability(paid)
    hook = GenerationCaptureHook(
        trajectory_id=f"traj_{name}", model_name="probe", backend_name="sglang", backend_version="probe",
        renderer_cls_name="probe", tokenizer_name="probe", template_hash="sha256:" + "a" * 64,
    )
    per = make_per_rollout_adapter(registry, adapter, hook)
    per.open_session(sid, physical_attempt_id=paid, capability_token=cap.token,
                     deadline_monotonic=time.monotonic() + 60)
    notifications = []
    registry.subscribe_turn_budget(sid, lambda _: notifications.append({
        "captures_at_notify": len(hook.records), "turns_at_notify": adapter.manager.turn_count(sid),
        "inflight_at_notify": registry._inflight.get(sid, 0),
    }))
    client = TestClient(TestServer(adapter.app, handler_cancellation=True))
    await client.start_server()
    body = {"model": "probe", "max_tokens": 16, "stream": True,
            "messages": [{"role": "user", "content": "probe"}]}
    headers = {"Authorization": f"Bearer {cap.token}", "Content-Type": "application/json"}
    gates = [asyncio.Event(), asyncio.Event()]
    encoded = json.dumps(body).encode()

    async def partial_body(gate):
        yield encoded[:-1]
        await gate.wait()
        yield encoded[-1:]

    async def request(index):
        if split_bodies:
            return await client.post("/v1/messages", data=partial_body(gates[index]), headers=headers)
        return await client.post("/v1/messages", json=body, headers=headers)

    requests = []
    try:
        requests.append(asyncio.create_task(request(0)))
        if split_bodies:
            requests.append(asyncio.create_task(request(1)))
            await until(lambda: registry._inflight.get(sid, 0) == 2)
            assert registry.turn_budget_snapshot(sid) is None
            gates[0].set()
            await engine.entered.wait()
            gates[1].set()
        else:
            await engine.entered.wait()
            requests.append(asyncio.create_task(request(1)))
        await asyncio.sleep(0.04)
        refusal_before_generation_release = requests[1].done()
        early = dict(
            refusal_before_generation_release=refusal_before_generation_release,
            capture_count=len(hook.records), tree_turns=adapter.manager.turn_count(sid),
            notified=list(notifications), engine_calls=engine.calls,
        )
        statuses = []
        if close_on_refusal:
            refused = await asyncio.wait_for(requests[1], timeout=1)
            statuses.append(refused.status)
            assert refused.status == 403
            requests[0].cancel()  # 模拟客户端收到预算拒绝后退出，关闭在飞 HTTP 请求
            await asyncio.gather(requests[0], return_exceptions=True)
            await until(lambda: registry.poison.is_poisoned(sid))
        else:
            engine.release.set()
            replies = await asyncio.gather(*requests)
            statuses = [r.status for r in replies]
            for reply in replies:
                await reply.read()
            await until(lambda: registry._inflight.get(sid, 0) == 0)
        result = dict(case=name, early=early, statuses=statuses,
                      captures=len(hook.records), tree_turns=adapter.manager.turn_count(sid),
                      capture_status=[r.capture_status for r in hook.records],
                      poison=registry.poison.reason(sid), abort_requests=engine.aborts,
                      budget=registry.turn_budget_snapshot(sid))
        if not close_on_refusal:
            leaves = await per.finish_session(sid, base_sample=Sample(index=0))
            result["leaf_count"] = len(leaves)
            result["leaf_response_tokens"] = [s.tokens[-s.response_length:] for s in leaves]
            result["capture_bindings"] = len(registry.turn_identity_bindings(sid))
        return result
    finally:
        engine.release.set()
        for request_task in requests:
            if not request_task.done():
                request_task.cancel()
        await asyncio.gather(*requests, return_exceptions=True)
        await per.drop_session(sid)
        await client.close()


async def main():
    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    build_production_model_call_proxy(registry, lambda: "3", require_real=False, artifact_sink=None)
    engine = Engine()
    cw.aiohttp = EngineAiohttp(engine)
    for name, split_bodies, close_on_refusal in [
        ("sequential_control", False, False),
        ("split_body_race_keep_client_alive", True, False),
        ("split_body_race_close_client", True, True),
    ]:
        # 新 app，仍使用同一进程 registry，遵守 capture wire 的单代所有权。
        adapter = AnthropicAdapter(tokenizer=Tokenizer(), sglang_url="http://fake-engine",
                                   max_turns_per_sid=1)
        adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
        observed = await case(registry, adapter, engine, name,
                              split_bodies=split_bodies, close_on_refusal=close_on_refusal)
        assert observed["early"]["refusal_before_generation_release"] is split_bodies
        if close_on_refusal:
            assert observed["captures"] == observed["tree_turns"] == 0
            assert observed["poison"] == "client_cancelled" and observed["abort_requests"] == 1
        else:
            assert observed["statuses"] == [200, 403] and observed["captures"] == 1
            assert observed["capture_status"] == ["complete"] and observed["poison"] is None
            assert observed["leaf_response_tokens"] == [[7, 8]] and observed["capture_bindings"] == 1
        print(json.dumps(observed, ensure_ascii=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
