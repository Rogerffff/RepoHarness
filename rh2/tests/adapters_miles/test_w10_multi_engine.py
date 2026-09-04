"""W10（决策包 D2+B v2 B-5b，owner 2026-09-04 拍板）：两个假 engine + 假 MilesRouter 的本地反例。

被测事实链（全部是生产代码，替身只有 HTTP 两端）::

    真实 capture wire `rh2_call_sglang_generate`（install_capture_wire 后的模块级替换体）
      -> 真 aiohttp 客户端 -> FakeMilesRouter（真 aiohttp server，镜像 miles/router/router.py 的
         逐请求最小负载选路、不读 X-SMG-Routing-Key）-> FakeEngine ×2（真 aiohttp server，
         /generate 挂起直到 rid 被 abort；/abort_request 只终止自己持有的 rid，不认识的 rid 忽略并 200）
    cancel -> wire except 分支 -> registry.engine_abort（bringup 接线的
      `MilesRouterWorkerClient.broadcast_abort`：router /list_workers 全部 worker 广播同一 rid）

五个反例/正例与 B-5b 逐条对应：分发到不同 engine；rid abort 到达持有者（广播后非持有者忽略）
——并附"旧路径经 router 单发会错发"的反例；权重发布到全部 engine（miles 侧 publish 路径
源码事实 + patch 0015 的 engine actor 逐台收敛核对，fake actor handle 驱动）；版本不从任意
worker 猜（bringup 的 current 版本只来自引擎一手回包的观测，两台 engine 都没收到探测）；
单 engine 配置仍正常。另含 W4 接缝（staleness 阈值记录镜像）与 launch.sh 单 engine 硬约束
删除的锚点。

codex Wave3 F3 P1（§9 组）：投递结果三分 delivered / partial / undeliverable——实时列表取不到时
对启动核对集合广播（不再经 router 单发）；partial / undeliverable / abort 机制自身异常 → 经
`bringup.notify_run_fatal` 升级 typed run-fatal（本 attempt 归因不变）；无 BringupService 时留账
+ 打印，不静默。
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace

import aiohttp
import pytest
from aiohttp import web

REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCH_SH = REPO_ROOT / "rh2" / "experiments" / "miles_gpu_spike" / "launch.sh"
BRINGUP_PY = REPO_ROOT / "rh2" / "src" / "repoharness2" / "adapters" / "slime" / "bringup.py"


async def _serve(app: web.Application) -> tuple[web.AppRunner, str]:
    """起一个真 aiohttp server 并返回 (runner, base_url)。

    有意不用 aiohttp.test_utils.TestServer：它强制 `handler_cancellation=True`（test_utils.py
    `_make_runner(handler_cancellation=True)`），客户端断连会取消 handler——而生产的 MilesRouter
    （uvicorn + httpx）与 SGLang HTTP server 在 rh2 断连后**不**取消：router 的代理请求继续挂在
    engine 上、engine 里的 rid 继续占槽位直到自然完成或被 abort。这正是 abort 必须精确到达持有者
    的原因，替身必须保留这一行为（AppRunner 缺省 handler_cancellation=False）。"""

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001 - aiohttp 未暴露已分配端口的公开属性
    return runner, f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------------------
# 替身：SGLang engine 与 MilesRouter（都是真 HTTP server）
# ---------------------------------------------------------------------------


class FakeEngine:
    """SGLang engine 的最小替身：/generate 挂起直到该 rid 被 abort 或显式放行（模拟"客户端
    断连后请求仍占 engine 槽位"）；/abort_request 只终止自己持有的 rid，不认识的 rid 记
    ignored 并返回 200（SGLang 对未知 rid 静默无操作）；/model_info 记录版本探测命中。"""

    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version
        self.inflight: dict[str, asyncio.Event] = {}
        self.generate_rids: list[str] = []
        self.abort_seen: list[str] = []
        self.abort_ignored: list[str] = []
        self.aborted: list[str] = []
        self.version_probes: list[str] = []
        self.abort_status = 200  # 故障注入：≠200 时 /abort_request 直接返回该状态、不处理
        self.app = web.Application()
        self.app.router.add_post("/generate", self._generate)
        self.app.router.add_post("/abort_request", self._abort)
        self.app.router.add_get("/model_info", self._model_info)
        self.app.router.add_get("/get_weight_version", self._deprecated)
        self.app.router.add_get("/health", self._health)
        self.runner: web.AppRunner | None = None
        self.url = ""

    async def start(self) -> None:
        self.runner, self.url = await _serve(self.app)

    async def close(self) -> None:
        self.release_all()
        if self.runner is not None:
            await self.runner.cleanup()

    async def _generate(self, request: web.Request) -> web.Response:
        payload = await request.json()
        rid = payload["rid"]
        event = asyncio.Event()
        self.inflight[rid] = event
        self.generate_rids.append(rid)
        try:
            await event.wait()
        finally:
            self.inflight.pop(rid, None)
        finish = "abort" if rid in self.aborted else "stop"
        pairs = [] if finish == "abort" else [[-0.5, 11], [-0.25, 12]]
        return web.json_response(
            {
                "text": "ok",
                "meta_info": {
                    "id": rid,
                    "weight_version": self.version,
                    "finish_reason": {"type": finish},
                    "output_token_logprobs": pairs,
                },
            }
        )

    async def _abort(self, request: web.Request) -> web.Response:
        payload = await request.json()
        if self.abort_status != 200:
            self.abort_seen.append(payload.get("rid"))
            return web.json_response({"error": "injected"}, status=self.abort_status)
        if payload.get("abort_all"):
            for rid, event in list(self.inflight.items()):
                self.aborted.append(rid)
                event.set()
            return web.json_response({})
        rid = payload.get("rid")
        self.abort_seen.append(rid)
        event = self.inflight.get(rid)
        if event is None:
            self.abort_ignored.append(rid)
        else:
            self.aborted.append(rid)
            event.set()
        return web.json_response({})

    async def _model_info(self, request: web.Request) -> web.Response:
        self.version_probes.append("/model_info")
        return web.json_response({"model_path": "fake", "weight_version": self.version})

    async def _deprecated(self, request: web.Request) -> web.Response:
        self.version_probes.append("/get_weight_version")
        return web.json_response({"detail": "deprecated"}, status=404)

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    def release_all(self) -> None:
        for event in list(self.inflight.values()):
            event.set()

    async def wait_until(self, predicate, timeout: float = 5.0) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while not predicate():
            if loop.time() > deadline:
                raise AssertionError(f"engine {self.name}: 等待条件超时")
            await asyncio.sleep(0.01)


class FakeMilesRouter:
    """镜像 integration tree `miles/router/router.py` 的选路语义：显式路由只有 POST /add_worker、
    GET /list_workers；其余一切路径 catch-all 代理到 `min(worker_request_counts)`（dict 插入序
    平局取先注册者），请求进入 +1、返回 -1（do_proxy / _use_url / _finish_url）；不读任何业务
    header（X-SMG-Routing-Key 是死字节）。客户端断连不取消代理中的请求（与 uvicorn+httpx 的
    实际行为一致——rh2 cancel 后 router 侧计数仍挂在持有者上）。"""

    def __init__(self) -> None:
        self.worker_request_counts: dict[str, int] = {}
        self.proxied: list[tuple[str, str]] = []  # (path, 选中的 worker)
        self.list_workers_delay = 0.0  # 故障注入：/list_workers 挂起秒数（模拟 router 控制面卡死）
        self.list_workers_status = 200  # 故障注入：≠200 时 /list_workers 返回该状态
        self.list_workers_calls = 0
        self.app = web.Application()
        self.app.router.add_post("/add_worker", self._add_worker)
        self.app.router.add_get("/list_workers", self._list_workers)
        self.app.router.add_route("*", "/{path:.*}", self._proxy)
        self.runner: web.AppRunner | None = None
        self.url = ""

    async def start(self) -> None:
        self.runner, self.url = await _serve(self.app)

    async def close(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()

    async def _add_worker(self, request: web.Request) -> web.Response:
        url = request.query.get("url") or request.query.get("worker_url")
        if url not in self.worker_request_counts:
            self.worker_request_counts[url] = 0
        return web.json_response({"status": "success", "worker_urls": self.worker_request_counts})

    async def _list_workers(self, request: web.Request) -> web.Response:
        self.list_workers_calls += 1
        if self.list_workers_delay:
            await asyncio.sleep(self.list_workers_delay)
        if self.list_workers_status != 200:
            return web.json_response({"error": "injected"}, status=self.list_workers_status)
        return web.json_response({"urls": list(self.worker_request_counts)})

    async def _proxy(self, request: web.Request) -> web.Response:
        path = request.match_info["path"]
        worker = min(self.worker_request_counts, key=self.worker_request_counts.get)
        self.worker_request_counts[worker] += 1
        self.proxied.append((path, worker))
        body = await request.read()
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ("content-length", "transfer-encoding", "host")
        }
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.request(request.method, f"{worker}/{path}", data=body, headers=headers) as r:
                    content = await r.read()
                    return web.Response(body=content, status=r.status, content_type="application/json")
        finally:
            self.worker_request_counts[worker] -= 1


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def wire(_vendor_slime_world):
    from slime.agent.adapters import common as slime_common

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)

    def make_hook(sid: str):
        # 真实 hook（commit 时按 contracts 构造 GenerationCaptureRecord，字段须合法形态）
        return GenerationCaptureHook(
            trajectory_id=f"traj_{sid}",
            model_name="Qwen/Qwen3-4B",
            backend_name="sglang",
            backend_version="sglang-test",
            renderer_cls_name="Qwen3Renderer",
            tokenizer_name="Qwen/Qwen3-4B",
            template_hash="sha256:" + "0" * 64,
        )

    return SimpleNamespace(registry=registry, slime_common=slime_common, cw=cw, make_hook=make_hook)


async def _start_cluster(wire, engines: list[FakeEngine]):
    router = FakeMilesRouter()
    for engine in engines:
        await engine.start()
    await router.start()
    async with aiohttp.ClientSession() as sess:
        for engine in engines:  # engine 自注册（sglang_engine._init_normal 的 POST /add_worker 同形）
            async with sess.post(f"{router.url}/add_worker", params={"url": engine.url}) as r:
                assert r.status == 200
    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient

    client = MilesRouterWorkerClient(router.url)
    wire.registry.engine_abort = client.broadcast_abort  # bringup.__init__ 的同一接线
    return SimpleNamespace(engines=engines, router=router, client=client)


async def _stop_cluster(wire, cluster) -> None:
    wire.registry.engine_abort = None
    for engine in cluster.engines:
        await engine.close()
    await cluster.router.close()


@pytest.fixture
async def cluster(wire):
    c = await _start_cluster(wire, [FakeEngine("A", "7"), FakeEngine("B", "9")])
    c.a, c.b = c.engines
    try:
        yield c
    finally:
        await _stop_cluster(wire, c)


@pytest.fixture
async def single_engine_cluster(wire):
    c = await _start_cluster(wire, [FakeEngine("only", "7")])
    c.only = c.engines[0]
    try:
        yield c
    finally:
        await _stop_cluster(wire, c)


class _Sessions:
    """按 sid 登记/注销 capture hook（真 registry.register/unregister）。"""

    def __init__(self, wire) -> None:
        self.wire = wire
        self.sids: list[str] = []

    def open(self, sid: str) -> str:
        self.wire.registry.register(sid, self.wire.make_hook(sid))
        self.sids.append(sid)
        return sid

    def close_all(self) -> None:
        for sid in self.sids:
            self.wire.registry.unregister(sid)
        self.sids.clear()


@pytest.fixture
def sessions(wire):
    s = _Sessions(wire)
    try:
        yield s
    finally:
        s.close_all()


async def _generate(wire, router_url: str, sid: str):
    session = wire.slime_common.Session(
        sampling_defaults={"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 8}, max_context_tokens=0
    )
    adapter = SimpleNamespace(
        logger=logging.getLogger("test_w10_multi_engine"),
        max_token_keys=("max_tokens",),
        stop_keys=("stop",),
        sglang_url=router_url,
    )
    return await wire.slime_common.call_sglang_generate([101, 102, 103], session, {}, adapter=adapter, session_id=sid)


def _stats(wire) -> dict[str, int]:
    return dict(wire.registry.stats)


# ---------------------------------------------------------------------------
# 1. 分发：并发请求经 router 落到不同 engine
# ---------------------------------------------------------------------------


async def test_router_dispatches_concurrent_generates_to_different_engines(wire, cluster, sessions):
    sid1, sid2 = sessions.open("sid-dispatch-1"), sessions.open("sid-dispatch-2")
    t1 = asyncio.create_task(_generate(wire, cluster.router.url, sid1))
    await cluster.a.wait_until(lambda: len(cluster.a.inflight) == 1)  # 先注册者先中（计数平局）
    t2 = asyncio.create_task(_generate(wire, cluster.router.url, sid2))
    await cluster.b.wait_until(lambda: len(cluster.b.inflight) == 1)  # A 已占 1 → 最小负载是 B
    assert len(cluster.a.inflight) == 1 and len(cluster.b.inflight) == 1
    cluster.a.release_all()
    cluster.b.release_all()
    r1, r2 = await asyncio.gather(t1, t2)
    assert r1.output_ids == [11, 12] and r2.output_ids == [11, 12]
    assert [p for p, _ in cluster.router.proxied] == ["generate", "generate"]
    assert [w for _, w in cluster.router.proxied] == [cluster.a.url, cluster.b.url]
    # 两条各自暂存了一轮（不同 rid 键，互不覆盖）
    assert len(wire.registry.pending[sid1]) == 1 and len(wire.registry.pending[sid2]) == 1


# ---------------------------------------------------------------------------
# 2. abort 广播到达持有者；非持有者忽略；router 本身没收到 abort
# ---------------------------------------------------------------------------


async def test_abort_broadcast_reaches_holding_engine_and_other_engine_ignores(wire, cluster, sessions):
    sid = sessions.open("sid-abort-broadcast")
    before = _stats(wire)
    task = asyncio.create_task(_generate(wire, cluster.router.url, sid))
    await cluster.a.wait_until(lambda: len(cluster.a.inflight) == 1)
    rid = cluster.a.generate_rids[-1]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await cluster.a.wait_until(lambda: rid in cluster.a.aborted)

    assert cluster.a.abort_seen == [rid] and cluster.a.aborted == [rid]  # 持有者终止
    assert cluster.b.abort_seen == [rid] and cluster.b.abort_ignored == [rid]  # 非持有者收到同一 rid 并忽略
    assert cluster.a.inflight == {}  # 槽位真正释放
    assert not any(p == "abort_request" for p, _ in cluster.router.proxied)  # 广播绕过 router
    after = _stats(wire)
    assert after["abort_requested"] - before["abort_requested"] == 1
    assert after["abort_broadcast"] - before["abort_broadcast"] == 1
    assert after["abort_router_single_send"] == before["abort_router_single_send"]
    assert after["abort_delivery_failed"] == before["abort_delivery_failed"]
    last = wire.registry.abort_results[-1]
    assert last["outcome"] == "delivered" and last["proven"] is True and last["rid"] == rid
    assert last["targets_source"] == "router_list" and last["list_error"] is None
    assert last["targets"] == [cluster.a.url, cluster.b.url] == last["delivered"]
    assert after["abort_unproven_fatal"] == before["abort_unproven_fatal"]  # 到达已证明，不升级
    assert wire.registry.pending.get(sid, {}) == {}  # 被取消的请求不留暂存


# ---------------------------------------------------------------------------
# 3. 反例：旧路径经 router 单发——最小负载把 abort 发给不持有 rid 的 engine
# ---------------------------------------------------------------------------


async def test_counterexample_single_send_via_router_misses_the_holder(wire, cluster, sessions):
    wire.registry.engine_abort = None  # 未接线 = W10 之前的 stock 形状
    sid = sessions.open("sid-abort-single-send")
    before = _stats(wire)
    task = asyncio.create_task(_generate(wire, cluster.router.url, sid))
    await cluster.a.wait_until(lambda: len(cluster.a.inflight) == 1)
    rid = cluster.a.generate_rids[-1]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await cluster.b.wait_until(lambda: rid in cluster.b.abort_seen)

    # A 仍持有该 rid（router 侧 A 的计数仍为 1），最小负载把 abort 送到了 B：B 忽略，A 永远没收到
    assert cluster.b.abort_ignored == [rid]
    assert cluster.a.abort_seen == []
    assert rid in cluster.a.inflight
    assert ("abort_request", cluster.b.url) in cluster.router.proxied
    after = _stats(wire)
    assert after["abort_router_single_send"] - before["abort_router_single_send"] == 1
    assert after["abort_broadcast"] == before["abort_broadcast"]
    last = wire.registry.abort_results[-1]
    assert last["outcome"] == "router_single_send" and last["list_error"] == "engine_abort_not_wired"
    assert last["proven"] is None  # 单发路径无法证明到达——这就是它只能留在无 bringup 测试面的原因
    cluster.a.release_all()  # 清理：否则 A 的挂起请求只能等 server close


# ---------------------------------------------------------------------------
# 4. 单 engine 配置仍正常
# ---------------------------------------------------------------------------


async def test_single_engine_pool_still_works_with_broadcast(wire, single_engine_cluster, sessions):
    c = single_engine_cluster
    assert await c.client.list_workers() == [c.only.url]
    sid = sessions.open("sid-single")
    done = asyncio.create_task(_generate(wire, c.router.url, sid))
    await c.only.wait_until(lambda: len(c.only.inflight) == 1)
    c.only.release_all()
    record = await done
    assert record.output_ids == [11, 12]

    task = asyncio.create_task(_generate(wire, c.router.url, sid))
    await c.only.wait_until(lambda: len(c.only.inflight) == 1)
    rid = c.only.generate_rids[-1]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await c.only.wait_until(lambda: rid in c.only.aborted)
    assert c.only.abort_seen == [rid] and c.only.abort_ignored == []
    last = wire.registry.abort_results[-1]
    assert last["outcome"] == "delivered" and last["targets"] == [c.only.url] and last["proven"] is True


# ---------------------------------------------------------------------------
# 9. codex Wave3 F3 P1：控制面异常下的投递语义——核对集合回退、三分结果、run-fatal 升级
# ---------------------------------------------------------------------------


class _FatalRecorder:
    """`bringup.notify_run_fatal` 的替身：记录被升级的异常并返回 True（"本进程有 BringupService"）。

    边界（codex Wave3 §9.4）：本替身只证明"wire 在什么条件下调用了升级通道、带什么 typed 异常"，
    **不能**用来证明关停链跑在哪个 event loop 上——它把真实的 owner-loop 派发整条换掉了。
    run-fatal 的 loop 归属由 `tests/adapters/test_w5a_shutdown_chain.py` 的
    `test_run_fatal_from_adapter_loop_schedules_shutdown_on_owner_loop`（真实双线程/双 loop，
    不替换 `notify_run_fatal`）与 `test_run_fatal_is_not_reported_notified_when_owner_loop_is_gone` 证明。
    """

    def __init__(self) -> None:
        self.calls: list[BaseException] = []

    def __call__(self, exc: BaseException) -> bool:
        self.calls.append(exc)
        return True


@pytest.fixture
def fatal_recorder(monkeypatch):
    import repoharness2.adapters.slime.bringup as bringup

    rec = _FatalRecorder()
    monkeypatch.setattr(bringup, "notify_run_fatal", rec)
    return rec


async def _cancel_inflight_on(wire, cluster, engine: FakeEngine, sid: str) -> str:
    """起一条经 router 的 generate，等它落在 ``engine`` 上，然后 cancel（触发 wire 的 abort 分支）。"""

    task = asyncio.create_task(_generate(wire, cluster.router.url, sid))
    await engine.wait_until(lambda: len(engine.inflight) == 1)
    rid = engine.generate_rids[-1]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    return rid


async def test_worker_list_timeout_broadcasts_to_verified_set_not_router_single_send(
    wire, cluster, sessions, fatal_recorder
):
    """反例 ④-1：router `/list_workers` 卡死。此前的行为是退回经 router 单发（最小负载 → 非持有者 B）。
    现在：对启动核对集合广播，持有者 A 终止；router 没有收到任何 abort；不升级 fatal。"""

    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient

    client = MilesRouterWorkerClient(
        cluster.router.url, verified_workers=[cluster.a.url, cluster.b.url], list_timeout_seconds=0.2
    )
    wire.registry.engine_abort = client.broadcast_abort
    cluster.router.list_workers_delay = 1.0  # 超过 client 的列表超时（0.2s）
    sid = sessions.open("sid-list-timeout")
    before = _stats(wire)
    rid = await _cancel_inflight_on(wire, cluster, cluster.a, sid)
    await cluster.a.wait_until(lambda: rid in cluster.a.aborted)

    assert cluster.a.aborted == [rid] and cluster.b.abort_ignored == [rid]
    assert not any(p == "abort_request" for p, _ in cluster.router.proxied)  # 没有经 router 单发
    after = _stats(wire)
    assert after["abort_router_single_send"] == before["abort_router_single_send"]
    assert after["abort_delivery_failed"] == before["abort_delivery_failed"]
    assert after["abort_unproven_fatal"] == before["abort_unproven_fatal"]
    assert fatal_recorder.calls == []
    last = wire.registry.abort_results[-1]
    assert last["outcome"] == "delivered" and last["targets_source"] == "verified_set"
    assert last["targets"] == [cluster.a.url, cluster.b.url] == last["delivered"]
    assert last["list_error"] and "Timeout" in last["list_error"]


@pytest.mark.parametrize("list_fault", ["timeout", "http_500"])
async def test_verified_set_unavailable_is_run_fatal_not_silent(wire, cluster, sessions, fatal_recorder, list_fault):
    """反例 ④-2：实时列表不可用且没有核对集合 → undeliverable → typed run-fatal（不单发、不静默）；
    本 attempt 仍以 CancelledError 归因。"""

    from repoharness2.adapters.slime.engine_router_client import AbortDeliveryUnprovenError, MilesRouterWorkerClient

    client = MilesRouterWorkerClient(cluster.router.url, list_timeout_seconds=0.2)  # 无核对集合
    wire.registry.engine_abort = client.broadcast_abort
    if list_fault == "timeout":
        cluster.router.list_workers_delay = 1.0
    else:
        cluster.router.list_workers_status = 500
    sid = sessions.open(f"sid-undeliverable-{list_fault}")
    before = _stats(wire)
    rid = await _cancel_inflight_on(wire, cluster, cluster.a, sid)

    assert len(fatal_recorder.calls) == 1
    exc = fatal_recorder.calls[0]
    assert isinstance(exc, AbortDeliveryUnprovenError) and exc.reason_code == "abort_undeliverable"
    assert exc.result.outcome == "undeliverable" and exc.result.targets_source == "none"
    assert exc.result.targets == () and exc.result.list_error
    assert cluster.a.abort_seen == [] and cluster.b.abort_seen == []  # 没有任何单发
    assert rid in cluster.a.inflight  # 持有者仍占槽位——这正是必须停 run 的原因
    assert not any(p == "abort_request" for p, _ in cluster.router.proxied)
    after = _stats(wire)
    assert after["abort_router_single_send"] == before["abort_router_single_send"]
    assert after["abort_delivery_failed"] - before["abort_delivery_failed"] == 1
    assert after["abort_unproven_fatal"] - before["abort_unproven_fatal"] == 1
    assert after["abort_unproven_unnotified"] == before["abort_unproven_unnotified"]
    fatal_row = wire.registry.abort_results[-1]
    assert fatal_row["outcome"] == "run_fatal" and fatal_row["reason_code"] == "abort_undeliverable"
    assert fatal_row["notified"] is True
    cluster.a.release_all()


@pytest.mark.parametrize(
    ("fail_a", "fail_b", "expect_outcome", "expect_reason"),
    [
        (False, True, "partial", "abort_delivery_partial"),  # 持有者 A 收到了，但 B 投递失败：仍不能证明
        (True, False, "partial", "abort_delivery_partial"),  # 持有者 A 投递失败，B 收到（忽略）
        (True, True, "undeliverable", "abort_undeliverable"),  # 全部失败
    ],
)
async def test_partial_or_total_delivery_failure_is_run_fatal(
    wire, cluster, sessions, fatal_recorder, fail_a, fail_b, expect_outcome, expect_reason
):
    """反例 ④-3：部分/全部 worker 投递失败 → 不当成功，升级 run-fatal（reason_code 区分 partial/undeliverable）。"""

    from repoharness2.adapters.slime.engine_router_client import AbortDeliveryUnprovenError

    if fail_a:
        cluster.a.abort_status = 500
    if fail_b:
        cluster.b.abort_status = 500
    sid = sessions.open(f"sid-fail-{int(fail_a)}{int(fail_b)}")
    before = _stats(wire)
    rid = await _cancel_inflight_on(wire, cluster, cluster.a, sid)
    await cluster.b.wait_until(lambda: rid in cluster.b.abort_seen)
    await cluster.a.wait_until(lambda: rid in cluster.a.abort_seen)

    assert len(fatal_recorder.calls) == 1
    exc = fatal_recorder.calls[0]
    assert isinstance(exc, AbortDeliveryUnprovenError) and exc.reason_code == expect_reason
    assert exc.result.outcome == expect_outcome and exc.result.proven is False
    expected_failed = {u for u, f in ((cluster.a.url, fail_a), (cluster.b.url, fail_b)) if f}
    assert set(exc.result.failed) == expected_failed
    assert set(exc.result.delivered) == {cluster.a.url, cluster.b.url} - expected_failed
    after = _stats(wire)
    assert after["abort_broadcast"] - before["abort_broadcast"] == 1
    assert after["abort_delivery_failed"] - before["abort_delivery_failed"] == 1
    assert after["abort_unproven_fatal"] - before["abort_unproven_fatal"] == 1
    assert after["abort_router_single_send"] == before["abort_router_single_send"]
    cluster.a.release_all()


async def test_unproven_without_bringup_service_is_recorded_and_printed(wire, cluster, sessions, capsys):
    """本进程没有 BringupService（真实 `notify_run_fatal` 返回 False）：不静默——留账 + 打印。"""

    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient

    client = MilesRouterWorkerClient(cluster.router.url, list_timeout_seconds=0.2)
    wire.registry.engine_abort = client.broadcast_abort
    cluster.router.list_workers_status = 503
    sid = sessions.open("sid-unnotified")
    before = _stats(wire)
    await _cancel_inflight_on(wire, cluster, cluster.a, sid)

    after = _stats(wire)
    assert after["abort_unproven_fatal"] - before["abort_unproven_fatal"] == 1
    assert after["abort_unproven_unnotified"] - before["abort_unproven_unnotified"] == 1
    row = wire.registry.abort_results[-1]
    assert row["outcome"] == "run_fatal" and row["notified"] is False and row["reason_code"] == "abort_undeliverable"
    out = capsys.readouterr().out
    assert "abort 不能证明到达" in out and "abort_undeliverable" in out
    cluster.a.release_all()


async def test_abort_path_exception_is_escalated_not_swallowed(wire, cluster, sessions, fatal_recorder):
    """abort 机制自身抛异常（不该发生）：此前 `except Exception: pass` 静默；现在按 undeliverable 升级。"""

    from repoharness2.adapters.slime.engine_router_client import AbortDeliveryUnprovenError

    async def broken(rid: str):
        raise RuntimeError("router client exploded")

    wire.registry.engine_abort = broken
    sid = sessions.open("sid-abort-exception")
    before = _stats(wire)
    await _cancel_inflight_on(wire, cluster, cluster.a, sid)

    assert len(fatal_recorder.calls) == 1
    exc = fatal_recorder.calls[0]
    assert isinstance(exc, AbortDeliveryUnprovenError) and exc.reason_code == "abort_undeliverable"
    assert "router client exploded" in str(exc) and exc.result.list_error.startswith("abort_path_exception")
    after = _stats(wire)
    assert after["abort_unproven_fatal"] - before["abort_unproven_fatal"] == 1
    cluster.a.release_all()


async def test_single_engine_verified_set_with_router_list_failure_still_delivers(
    wire, single_engine_cluster, sessions, fatal_recorder
):
    """③ 单 engine profile：核对集合恰一个 worker；实时列表失败时对它广播即到达，不升级。"""

    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient

    c = single_engine_cluster
    client = MilesRouterWorkerClient(c.router.url, list_timeout_seconds=0.2)
    assert client.set_verified_workers([c.only.url + "/"]) == (c.only.url,)
    wire.registry.engine_abort = client.broadcast_abort
    c.router.list_workers_status = 500
    sid = sessions.open("sid-single-verified")
    rid = await _cancel_inflight_on(wire, c, c.only, sid)
    await c.only.wait_until(lambda: rid in c.only.aborted)
    assert fatal_recorder.calls == []
    last = wire.registry.abort_results[-1]
    assert last["outcome"] == "delivered" and last["targets_source"] == "verified_set"
    assert last["targets"] == [c.only.url]


async def test_verified_worker_missing_from_router_list_is_still_targeted(wire, sessions, fatal_recorder):
    """核对集合里的 worker 缺席于 router 实时列表（router 重启后只剩部分注册）：并集投递、记 drift。"""

    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient

    a, b = FakeEngine("A", "7"), FakeEngine("B", "9")
    c = await _start_cluster(wire, [a])  # router 只知道 A
    await b.start()
    try:
        client = MilesRouterWorkerClient(c.router.url, verified_workers=[a.url, b.url])
        wire.registry.engine_abort = client.broadcast_abort
        assert await client.list_workers() == [a.url]
        targets, source, list_error, drift = await client.resolve_targets()
        assert targets == [a.url, b.url] and source == "router_list+verified_set" and drift == [b.url]
        assert list_error is None
        sid = sessions.open("sid-drift")
        rid = await _cancel_inflight_on(wire, c, a, sid)
        await b.wait_until(lambda: rid in b.abort_seen)
        assert a.aborted == [rid] and b.abort_ignored == [rid]
        assert fatal_recorder.calls == []
        last = wire.registry.abort_results[-1]
        assert last["outcome"] == "delivered" and last["drift_missing_from_router"] == [b.url]
    finally:
        await b.close()
        await _stop_cluster(wire, c)


def test_set_verified_workers_normalizes_and_classify_outcome_three_way():
    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient, classify_outcome

    client = MilesRouterWorkerClient("http://router:1/", verified_workers=["http://a:1@0", "http://a:1@1", "http://b:2/"])
    assert client.router_url == "http://router:1"
    assert client.verified_workers == ("http://a:1", "http://b:2")
    assert client.set_verified_workers([]) == ()
    assert classify_outcome([], [], {}) == "undeliverable"
    assert classify_outcome(["a"], [], {"a": "boom"}) == "undeliverable"
    assert classify_outcome(["a", "b"], ["a"], {"b": "boom"}) == "partial"
    assert classify_outcome(["a", "b"], ["a", "b"], {}) == "delivered"


# ---------------------------------------------------------------------------
# 5. 版本不从任意 worker 猜：current 只来自引擎一手回包的观测，没有任何探测请求
# ---------------------------------------------------------------------------


async def test_current_version_is_observed_from_engine_replies_not_probed_from_any_worker(
    wire, cluster, sessions
):
    import repoharness2.adapters.slime.bringup as bringup

    class _Carrier:  # 绑定 BringupService 真实方法体的最小载体（完整构造需要 tokenizer 缓存）
        _observed_current_version = bringup.BringupService._observed_current_version

    carrier = _Carrier()
    carrier.registry = wire.registry
    carrier.policy_version = "step_0"
    carrier.sglang_url = cluster.router.url  # 即使给了 router 地址也不许去问

    sid_a, sid_b = sessions.open("sid-version-a"), sessions.open("sid-version-b")
    # 尚无任何观测：回退启动探针值
    assert carrier._observed_current_version() == "step_0"
    t1 = asyncio.create_task(_generate(wire, cluster.router.url, sid_a))
    await cluster.a.wait_until(lambda: len(cluster.a.inflight) == 1)
    t2 = asyncio.create_task(_generate(wire, cluster.router.url, sid_b))
    await cluster.b.wait_until(lambda: len(cluster.b.inflight) == 1)
    cluster.a.release_all()
    cluster.b.release_all()
    await asyncio.gather(t1, t2)
    # 提交暂存轮 → registry.weight_versions 记下各 engine 在回包里报的版本（A=7、B=9）
    assert wire.registry.commit(sid_a) and wire.registry.commit(sid_b)
    assert wire.registry.snapshot_weight_versions()[sid_a] == ["7"]
    assert wire.registry.snapshot_weight_versions()[sid_b] == ["9"]

    assert carrier._observed_current_version() == "9"  # 观测上界 = 引擎报过的最大版本
    # 两台 engine 与 router 都没有收到任何版本探测（/model_info 或 /get_weight_version）
    assert cluster.a.version_probes == [] and cluster.b.version_probes == []
    assert all(p == "generate" for p, _ in cluster.router.proxied)


def test_bringup_has_no_router_version_probe_left(wire):
    import repoharness2.adapters.slime.bringup as bringup

    assert not hasattr(bringup.BringupService, "_latest_engine_version")
    assert not hasattr(bringup.BringupService, "_registry_max_version")
    code = bringup.BringupService._observed_current_version.__code__
    # 代码对象钉死：不 import requests、不拼任何端点路径、只读 registry 快照与 policy_version
    assert "requests" not in code.co_names
    assert not any(isinstance(c, str) and c.startswith("/") for c in code.co_consts)
    assert {"snapshot_weight_versions", "policy_version"} <= set(code.co_names)
    source = BRINGUP_PY.read_text(encoding="utf-8")
    assert "import requests" not in source
    # abort 广播接线在 __init__（registry.engine_abort = router_workers.broadcast_abort）
    assert "self.registry.engine_abort = self.router_workers.broadcast_abort" in source
    assert "current_policy_version_provider=self._observed_current_version" in source


# ---------------------------------------------------------------------------
# 6. 权重发布到全部 engine（miles 侧：publish 路径源码事实 + patch 0015 逐台收敛核对）
# ---------------------------------------------------------------------------


class _FakeActorHandle:
    """SGLangEngine actor handle 的最小替身：`get_weight_version.remote()` 返回 awaitable。"""

    def __init__(self, version=None, *, error: BaseException | None = None, delay: float = 0.0) -> None:
        self._version = version
        self._error = error
        self._delay = delay
        self.calls = 0
        self.get_weight_version = SimpleNamespace(remote=self._remote)

    async def _remote(self):
        self.calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error
        return self._version


def _read_events(event_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(event_dir.glob("rh2_events_*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return rows


@pytest.mark.integration_base
async def test_publish_convergence_check_queries_every_engine_actor(world, monkeypatch, tmp_path):
    from miles.utils import rh2_engine_versions as ev

    monkeypatch.setenv("MILES_RH2_EVENT_DIR", str(tmp_path))
    handles = [_FakeActorHandle("8"), _FakeActorHandle(8)]  # 第二台回 int：按 str 比较
    report = await ev.verify_engine_weight_versions(handles, expected=8, timeout=1.0)
    assert report.converged and report.versions == ("8", "8") and report.errors == (None, None)
    assert [h.calls for h in handles] == [1, 1]  # 每台恰好问一次，不经 router
    events = [e for e in _read_events(tmp_path) if e["event"] == ev.ENGINE_VERSIONS_EVENT]
    assert len(events) == 1
    assert events[0]["expected"] == "8" and events[0]["versions"] == ["8", "8"] and events[0]["converged"] is True
    assert events[0]["num_engines"] == 2


@pytest.mark.integration_base
@pytest.mark.parametrize(
    ("handles_spec", "expect_versions", "expect_error_engine"),
    [
        ("mismatch", ("8", "7"), None),  # 一台没收到发布：版本不一致
        ("unreachable", ("8", None), 1),  # 一台 actor 查询抛错：不可达
        ("timeout", ("8", None), 1),  # 一台超时：不可达
    ],
)
async def test_publish_convergence_mismatch_or_dead_engine_stops_the_run(
    world, monkeypatch, tmp_path, handles_spec, expect_versions, expect_error_engine
):
    from miles.utils import rh2_engine_versions as ev

    monkeypatch.setenv("MILES_RH2_EVENT_DIR", str(tmp_path))
    if handles_spec == "mismatch":
        handles = [_FakeActorHandle("8"), _FakeActorHandle("7")]
    elif handles_spec == "unreachable":
        handles = [_FakeActorHandle("8"), _FakeActorHandle(error=RuntimeError("actor died"))]
    else:
        handles = [_FakeActorHandle("8"), _FakeActorHandle("8", delay=1.0)]
    with pytest.raises(ev.EngineWeightVersionMismatch) as exc:
        await ev.verify_engine_weight_versions(handles, expected="8", timeout=0.05)
    report = exc.value.report
    assert report.versions == expect_versions and not report.converged
    if expect_error_engine is not None:
        assert report.errors[expect_error_engine] is not None
        assert report.errors[1 - expect_error_engine] is None
    # 事件在抛错**之前**落盘（不一致的事实必须留证）
    events = [e for e in _read_events(tmp_path) if e["event"] == ev.ENGINE_VERSIONS_EVENT]
    assert len(events) == 1 and events[0]["converged"] is False
    assert events[0]["versions"] == list(expect_versions)


@pytest.mark.integration_base
def test_engine_version_timeout_env_knob(world, monkeypatch):
    from miles.utils import rh2_engine_versions as ev

    monkeypatch.delenv(ev.ENGINE_VERSION_TIMEOUT_ENV, raising=False)
    assert ev.engine_version_timeout_sec() == ev.DEFAULT_ENGINE_VERSION_TIMEOUT_SEC
    monkeypatch.setenv(ev.ENGINE_VERSION_TIMEOUT_ENV, "12.5")
    assert ev.engine_version_timeout_sec() == 12.5
    monkeypatch.setenv(ev.ENGINE_VERSION_TIMEOUT_ENV, "0")
    with pytest.raises(ValueError):
        ev.engine_version_timeout_sec()


@pytest.mark.integration_base
def test_miles_publish_paths_iterate_all_updatable_engines(world):
    """源码事实锚定（integration tree）：pause/update_weight_version/continue 都对
    `self.rollout_engines` 全量迭代；该列表 = 可更新 server 的全部 node-0 engine actor handle；
    patch 0015 把 set_weight_version 改为 async 并对同一批 engine 逐台核对版本。"""

    root = world.miles_root / "miles"
    mixin = (root / "backends/megatron_utils/update_weight/update_weight_from_distributed/mixin.py").read_text()
    tensor = (root / "backends/megatron_utils/update_weight/update_weight_from_tensor.py").read_text()
    for src in (mixin, tensor):
        assert "ray.get([engine.pause_generation.remote(mode=mode) for engine in self.rollout_engines])" in src
        assert "ray.get([engine.continue_generation.remote() for engine in self.rollout_engines])" in src
    assert "engine.update_weight_version.remote(weight_version=str(self.weight_version))" in mixin
    assert "for engine in self.rollout_engines" in mixin

    manager = (root / "ray/rollout/rollout_manager.py").read_text()
    assert "rollout_engines=[e.actor_handle for e in srv.engines]" in manager
    assert "async def set_weight_version(self, weight_version: int):" in manager
    assert "await self._verify_engine_weight_versions(weight_version)" in manager
    assert "handles = [e.actor_handle for e in srv.engines if e.is_allocated]" in manager
    assert "if srv is None or self.args.indep_dp:" in manager  # indep_dp 下副本版本可合法不同
    assert "verify_engine_weight_versions(handles, expected=weight_version)" in manager
    server = (root / "ray/rollout/rollout_server.py").read_text()
    assert "return [e for g in self.server_groups for e in g.engines]" in server


@pytest.mark.integration_base
def test_worker_base_urls_mirror_miles_semantics(world):
    from repoharness2.adapters.slime.engine_router_client import worker_base_urls

    src = (world.miles_root / "miles/utils/http_utils.py").read_text()
    assert 'base, sep, rank = url.rpartition("@")' in src and "if sep and rank.isdigit():" in src
    assert worker_base_urls(["http://a:1@0", "http://a:1@1", "http://b:2", "http://c:3@x"]) == [
        "http://a:1",
        "http://b:2",
        "http://c:3@x",
    ]


# ---------------------------------------------------------------------------
# 7. W4 接缝：staleness 阈值记录镜像
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (SimpleNamespace(), None),
        (SimpleNamespace(max_weight_staleness=None), None),
        (SimpleNamespace(max_weight_staleness=0), 0),
        (SimpleNamespace(max_weight_staleness=2), 2),
    ],
)
def test_staleness_threshold_mirror_from_args(wire, args, expected):
    from repoharness2.adapters.slime.bringup import staleness_threshold_mirror_from_args

    assert staleness_threshold_mirror_from_args(args) == expected


@pytest.mark.parametrize("bad", [-1, True, "2", 1.5])
def test_staleness_threshold_mirror_rejects_illegal_values(wire, bad):
    from repoharness2.adapters.slime.bringup import staleness_threshold_mirror_from_args

    with pytest.raises(RuntimeError, match="max-weight-staleness"):
        staleness_threshold_mirror_from_args(SimpleNamespace(max_weight_staleness=bad))


def test_bringup_config_carries_staleness_mirror(wire):
    source = BRINGUP_PY.read_text(encoding="utf-8")
    assert "self.staleness_threshold_mirror = staleness_threshold_mirror_from_args(args)" in source
    assert "staleness_threshold=self.staleness_threshold_mirror," in source


# ---------------------------------------------------------------------------
# 8. launch.sh：单 engine 硬约束已删，只留整除/资源合法性
# ---------------------------------------------------------------------------


def test_launch_script_has_no_single_engine_hard_constraint():
    subprocess.run(["bash", "-n", str(LAUNCH_SH)], check=True)
    text = LAUNCH_SH.read_text(encoding="utf-8")
    assert '[ "$ENGINE_COUNT" -eq 1 ]' not in text
    assert "覆盖位已移除" not in text
    assert 'ROLLOUT_GPUS_PER_ENGINE="${RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE:-2}"' in text
    assert "$((ROLLOUT_GPUS % ROLLOUT_GPUS_PER_ENGINE)) -eq 0" in text
    assert '[ "$ROLLOUT_GPUS_PER_ENGINE" -le "$ROLLOUT_GPUS" ]' in text
    assert "--rollout-num-gpus-per-engine \"$ROLLOUT_GPUS_PER_ENGINE\"" in text
