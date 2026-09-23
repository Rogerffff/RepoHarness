"""R1 窄复核：保留旧探针，复用其真实 HTTP/capture 动作检查路由安装顺序和新增 wrapper。

只用 CPU、本机 aiohttp 和内存 SGLang IO 替身；不调用 Docker / CC / 模型 API。
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cap_body_race_probe as old


def adapter(cap):
    return old.AnthropicAdapter(tokenizer=old.Tokenizer(), sglang_url="http://fake-engine", max_turns_per_sid=cap)


def route_handler(app):
    return next(r.handler for r in app.router.routes() if r.method == "POST" and r.resource.canonical == "/v1/messages")


async def new_wrapper_case(registry, shared, engine, name, *, cap, total, cancel_waiter=False, poison_admitted=False):
    engine.reset()
    paid, sid = f"exec_{name}#p1-aaaa", f"s-exec_{name}#p1-aaaa"
    capability = old.mint_session_capability(paid)
    hook = old.GenerationCaptureHook(
        trajectory_id=f"traj_{name}", model_name="probe", backend_name="sglang", backend_version="probe",
        renderer_cls_name="probe", tokenizer_name="probe", template_hash="sha256:" + "a" * 64,
    )
    per = old.make_per_rollout_adapter(registry, shared, hook)
    per.open_session(sid, physical_attempt_id=paid, capability_token=capability.token,
                     deadline_monotonic=time.monotonic() + 60)
    notices = []
    registry.subscribe_turn_budget(sid, lambda _: notices.append({
        "captures": len(hook.records), "admitted_inflight": len(shared.inflight.get(sid, ())),
    }))
    client = old.TestClient(old.TestServer(shared.app, handler_cancellation=True))
    await client.start_server()
    body = {"model": "probe", "max_tokens": 16, "stream": True,
            "messages": [{"role": "user", "content": "probe"}]}
    headers = {"Authorization": f"Bearer {capability.token}", "Content-Type": "application/json"}
    requests = []
    try:
        # 全部请求 body 已就绪；已接纳的 cap 个请求必须能够同时进入生成。
        requests = [asyncio.create_task(client.post("/v1/messages", json=body, headers=headers)) for _ in range(total)]
        await old.until(lambda: engine.calls == cap and registry._inflight.get(sid, 0) == total)
        early = {"engine_calls": engine.calls, "admitted_inflight": len(shared.inflight[sid]),
                 "waiting_responses_done": sum(t.done() for t in requests[cap:]), "notices": len(notices)}
        assert early == {"engine_calls": cap, "admitted_inflight": cap,
                         "waiting_responses_done": 0, "notices": 0}
        # 真实 capability 重写在 wrapper 读 body 之前完成；裸 internal sid 仍立即拒绝。
        forbidden = await asyncio.wait_for(client.post("/v1/messages", json=body,
                               headers={"Authorization": f"Bearer {sid}"}), timeout=1)
        assert forbidden.status == 403
        assert (await forbidden.json())["error"]["type"] == "rh2_unknown_or_closed_session"
        if cancel_waiter:
            requests[-1].cancel()
            await asyncio.gather(requests[-1], return_exceptions=True)
            await old.until(lambda: registry._inflight.get(sid, 0) == total - 1)
            assert not engine.cancelled.is_set() and not registry.poison.is_poisoned(sid)
        if poison_admitted:
            requests[0].cancel()
            await asyncio.gather(requests[0], return_exceptions=True)
            await old.until(lambda: registry.poison.is_poisoned(sid))
        else:
            engine.release.set()
        done = await asyncio.wait_for(asyncio.gather(*requests, return_exceptions=True), timeout=2)
        statuses = []
        for response in done:
            if isinstance(response, BaseException):
                statuses.append(type(response).__name__)
            else:
                statuses.append(response.status)
                await response.read()
        await old.until(lambda: registry._inflight.get(sid, 0) == 0)
        # 已认证在途请求收口后，撤销对新的请求仍生效，不多发一轮。
        registry.revoke(sid)
        late = await client.post("/v1/messages", json=body, headers=headers)
        late_error = (await late.json())["error"]["type"]
        assert late.status == 403 and late_error == (
            "rh2_session_poisoned" if poison_admitted else "rh2_session_revoked"
        )
        observed = dict(case=name, early=early, statuses=statuses, captures=len(hook.records),
                        capture_status=[r.capture_status for r in hook.records],
                        poison=registry.poison.reason(sid), abort_requests=engine.aborts,
                        notifications=notices, late_error=late_error,
                        accepted=registry.turn_budget_snapshot(sid)["accepted"])
        if poison_admitted:
            assert observed["captures"] == 0 and observed["poison"] == "client_cancelled"
            assert observed["abort_requests"] == 1
        else:
            assert observed["captures"] == cap and observed["poison"] is None
            assert all(n["captures"] == cap and n["admitted_inflight"] == 0 for n in notices)
        assert observed["accepted"] == cap
        return observed
    finally:
        engine.release.set()
        for task in requests:
            if not task.done():
                task.cancel()
        await asyncio.gather(*requests, return_exceptions=True)
        await per.drop_session(sid)
        await client.close()


async def main():
    registry = old.cw.CaptureRegistry()
    # 生产 bringup.py:1069–1077 的实际顺序：先构造路由，再安装 wire。
    production_seq, production_race = adapter(1), adapter(1)
    before_handler = route_handler(production_seq.app)
    old.cw.install_capture_wire(registry)
    old.build_production_model_call_proxy(registry, lambda: "3", require_real=False, artifact_sink=None)
    engine = old.Engine()
    old.cw.aiohttp = old.EngineAiohttp(engine)
    for app in (production_seq.app, production_race.app):
        old.cw.ensure_no_404_middleware(app)
        app.middlewares.append(old.cw.build_session_guard_middleware(registry))
    route_fact = {"case": "production_route_binding", "route_handler": before_handler.__func__.__name__,
                  "current_class_method": production_seq._run_turn.__func__.__name__,
                  "same_function": before_handler.__func__ is production_seq._run_turn.__func__}
    assert route_fact["same_function"] is False
    print(json.dumps(route_fact, ensure_ascii=False))
    seq = await old.case(registry, production_seq, engine, "production_seq", split_bodies=False, close_on_refusal=False)
    assert seq["early"]["refusal_before_generation_release"] is True
    print(json.dumps(seq, ensure_ascii=False))
    race = await old.case(registry, production_race, engine, "production_race", split_bodies=True, close_on_refusal=True)
    assert race["captures"] == 0 and race["poison"] == "client_cancelled" and race["abort_requests"] == 1
    print(json.dumps(race, ensure_ascii=False))
    after = adapter(1)
    after.app.middlewares.append(old.cw.build_session_guard_middleware(registry))
    fixed = await old.case(registry, after, engine, "post_install_body_race", split_bodies=True, close_on_refusal=False)
    assert fixed["early"]["refusal_before_generation_release"] is False
    assert fixed["captures"] == 1 and fixed["poison"] is None
    print(json.dumps(fixed, ensure_ascii=False))
    for name, cap, total, cancelled, poisoned in [
        ("parallel_admitted_multiple_refusals", 3, 5, False, False),
        ("one_waiter_cancelled", 1, 3, True, False),
        ("admitted_cancel_preserves_poison", 1, 2, False, True),
    ]:
        current = adapter(cap)
        current.app.middlewares.append(old.cw.build_session_guard_middleware(registry))
        result = await new_wrapper_case(registry, current, engine, name, cap=cap, total=total,
                                        cancel_waiter=cancelled, poison_admitted=poisoned)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
