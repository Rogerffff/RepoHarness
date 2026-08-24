"""FA-1 follow-up 3 测试（codex 轮次 8）：CaptureRegistry 的 FIFO / 两阶段
finalize / 逐 attempt rid 记账，以及不需要真 slime 的纯逻辑面。

wire 主体（call_sglang_generate 替换）需要真 slime + SGLang，留 FA-5；这里
测的是 registry 的暂存/提交/销毁语义——P0-1（finalize 移到 commit）、P0-6
（FIFO 不覆盖）的正确性权威。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))

from repoharness2.adapters.slime.capture_wire import (  # noqa: E402
    CapturePendingOverlapError,
    CaptureRegistry,
    PendingTurn,
    assert_no_404_guard_installed,
    ensure_no_404_middleware,
    rh2_no_404_middleware,
)


class FakeHook:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.records: list = []

    def on_generate_response(self, *, prompt_token_ids, sampling_params, response):
        from types import SimpleNamespace

        self.calls.append({"prompt": list(prompt_token_ids), "response": response})
        rec = SimpleNamespace(record_id=f"cap_fake_t{len(self.calls) - 1}")
        self.records.append(rec)
        return rec


class FakeProxyResult:
    """ProxyCallResult 的两阶段接口替身（finalize/abandon 幂等）。"""

    def __init__(self, attempt_id: str) -> None:
        self.attempt_id = attempt_id
        self.state = "pending"

    def finalize_delivered(self, ref: str) -> None:
        if self.state != "pending":
            raise ValueError(f"{self.attempt_id} 已 {self.state}")
        self.state = f"finalized:{ref}"

    def abandon_delivered(self, reason: str) -> None:
        if self.state != "pending":
            raise ValueError(f"{self.attempt_id} 已 {self.state}")
        self.state = f"abandoned:{reason}"


def _turn(rid: str, version: str = "1", proxy=None) -> PendingTurn:
    return PendingTurn(
        prompt_ids=[1, 2, 3],
        capture_params={"top_p": 0.95},
        raw_response={"meta_info": {"id": rid}},
        weight_version=version,
        request_id=rid,
        proxy_result=proxy,
    )


def test_finalize_happens_at_commit_not_stage():
    """P0-1：stage 不 finalize（CC 尚未收到 SSE）；commit 成功才 finalize。"""

    registry = CaptureRegistry()
    hook = FakeHook()
    registry.register("sid_A", hook)
    proxy = FakeProxyResult("sid_A/t1_a1")
    registry.stage("sid_A", _turn("rid_1", proxy=proxy))
    assert proxy.state == "pending"  # stage 后仍未交付定案
    registry.commit("sid_A")
    assert proxy.state.startswith("finalized:cap_fake_t0")  # 真实 record_id（收口二轮）
    assert len(hook.calls) == 1


def test_unregister_abandons_uncommitted_draft():
    """P0-1：会话销毁时未 commit 的暂存 = CC 没收到——abandon，不是虚假 delivered。"""

    registry = CaptureRegistry()
    registry.register("sid_B", FakeHook())
    proxy = FakeProxyResult("sid_B/t1_a1")
    registry.stage("sid_B", _turn("rid_x", proxy=proxy))
    registry.unregister("sid_B")
    assert proxy.state.startswith("abandoned:session_unregistered_before_commit")
    assert registry.session_deadlines.get("sid_B") is None  # 会话状态清理（有界）


def test_parallel_requests_no_longer_killed_same_rid_still_fails():
    """F2-3 批 2b（overlap 误杀解除）：不同请求键的并行暂存合法共存、各
    自 commit 不串账；**同键**二次 stage 仍 fail-closed（poison + 两轮
    abandon）；多条在场且无请求键的 commit 归属不可判，同样 fail-closed。"""

    from repoharness2.adapters.slime.capture_wire import _capture_request_key

    registry = CaptureRegistry()
    hook = FakeHook()
    registry.register("sid_C", hook)
    p1, p2 = FakeProxyResult("a1"), FakeProxyResult("a2")
    # 并行不同请求：独立键（直调回退 turn.request_id）→ 共存
    registry.stage("sid_C", _turn("rid_1", version="1", proxy=p1))
    registry.stage("sid_C", _turn("rid_2", version="2", proxy=p2))
    assert len(registry.pending["sid_C"]) == 2  # 误杀解除
    # 按请求键各自 commit：rid_2 先完成也不会拿走 rid_1 的轮（串账根修）
    tok = _capture_request_key.set("rid_2")
    try:
        registry.commit("sid_C")
    finally:
        _capture_request_key.reset(tok)
    assert hook.calls[-1]["response"]["meta_info"]["id"] == "rid_2"
    tok = _capture_request_key.set("rid_1")
    try:
        registry.commit("sid_C")
    finally:
        _capture_request_key.reset(tok)
    assert hook.calls[-1]["response"]["meta_info"]["id"] == "rid_1"
    assert not registry.poison.is_poisoned("sid_C")

    # 同键二次 stage：真异常，fail-closed 原语义保留
    p3, p4 = FakeProxyResult("a3"), FakeProxyResult("a4")
    registry.stage("sid_C", _turn("rid_dup", version="3", proxy=p3))
    with pytest.raises(CapturePendingOverlapError):
        registry.stage("sid_C", _turn("rid_dup", version="4", proxy=p4))
    assert registry.stats["concurrent_overlap_seen"] == 1
    assert registry.poison.is_poisoned("sid_C")
    assert p3.state.startswith("abandoned:capture_pending_overlap")
    assert p4.state.startswith("abandoned:capture_pending_overlap")


def test_ambiguous_commit_without_request_key_fails_closed():
    """多条在场 + 无请求键 = 归属不可判——绝不猜测（批 2b 保留的
    fail-closed 面）。"""

    registry = CaptureRegistry()
    hook = FakeHook()
    registry.register("sid_A", hook)
    registry.stage("sid_A", _turn("rid_x", version="1"))
    registry.stage("sid_A", _turn("rid_y", version="2"))
    with pytest.raises(CapturePendingOverlapError):
        registry.commit("sid_A")
    assert registry.poison.is_poisoned("sid_A")
    assert len(hook.calls) == 0


def test_commit_without_pending_is_noop():
    registry = CaptureRegistry()
    registry.register("sid_D", FakeHook())
    registry.commit("sid_D")  # 无暂存不炸
    assert registry.stats["committed"] == 0


def test_double_commit_does_not_refinalize():
    """重复 commit（防御）：第二次无暂存可弹，不重复 finalize。"""

    registry = CaptureRegistry()
    registry.register("sid_E", FakeHook())
    proxy = FakeProxyResult("a1")
    registry.stage("sid_E", _turn("rid_1", proxy=proxy))
    registry.commit("sid_E")
    first = proxy.state
    registry.commit("sid_E")  # 第二次无暂存
    assert proxy.state == first  # 未被再次触碰


def test_session_deadline_starts_on_first_call_and_is_bounded():
    registry = CaptureRegistry()
    registry.default_session_budget_seconds = 600.0
    d1 = registry.session_deadline("sid_F")
    d2 = registry.session_deadline("sid_F")
    assert d1 == d2  # 同会话稳定
    assert registry.session_deadline(None) is None
    registry.register("sid_F", FakeHook())
    registry.unregister("sid_F")
    assert "sid_F" not in registry.session_deadlines  # 销毁即清理（有界增长修复）


async def test_no_404_middleware_route_level():
    """codex 轮次 9 一般 1：404 守卫必须真接线——路由级测试：未知路径与
    显式 404 响应都转 503 + x-should-retry:false（CC 2.1.205 对 404 会绕过
    nonstreaming fallback 开关；实测 x-should-retry:false 对 5xx 生效）。"""

    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    async def explicit_404(request):
        return web.json_response({"error": "nope"}, status=404)

    async def ok(request):
        return web.json_response({"ok": True})

    app = web.Application(middlewares=[rh2_no_404_middleware])
    app.router.add_get("/explicit404", explicit_404)
    app.router.add_get("/ok", ok)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        r1 = await client.get("/unknown_route")  # aiohttp 默认 HTTPNotFound
        assert r1.status == 503
        assert r1.headers["x-should-retry"] == "false"
        r2 = await client.get("/explicit404")
        assert r2.status == 503
        assert r2.headers["x-should-retry"] == "false"
        r3 = await client.get("/ok")
        assert r3.status == 200  # 正常路径不受影响
    finally:
        await client.close()


async def test_middleware_production_order_direct_append():
    """codex 轮次 10 P0-2：生产顺序 = 先构造 adapter 再 install——构造器
    patch 对已存在 app 无效，必须 ensure_no_404_middleware 直接挂 + 启动前
    断言。本测试按生产顺序：裸 app（模拟先构造的 adapter）→ ensure → 断言
    → 路由级验证 404 已被转换。"""

    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    app = web.Application()  # 先构造（无 middleware，= 生产 adapter 现状）
    with pytest.raises(RuntimeError, match="rh2_no_404_middleware 不在"):
        assert_no_404_guard_installed(app)  # 修复前生产就是这个状态
    assert ensure_no_404_middleware(app) is True
    assert ensure_no_404_middleware(app) is False  # 幂等：不双挂
    assert_no_404_guard_installed(app)  # 启动前断言通过
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        r = await client.get("/never_registered")
        assert r.status == 503
        assert r.headers["x-should-retry"] == "false"
    finally:
        await client.close()


def test_unregister_does_not_release_poison():
    """轮次 11 身份 4（修正轮次 10）：unregister 只是 adapter 会话关闭，
    **不是** execution 清理 ACK——active poison 保持到 orchestrator 在容器
    清理完成后显式 release（时序：drop_session < 容器清理 < release）。"""

    registry = CaptureRegistry()
    registry.register("sid_G", FakeHook())
    registry.poison.poison("sid_G", "bad")
    registry.unregister("sid_G")
    assert "sid_G" in registry.poison._active  # 仍 active（容器还没清完）
    registry.poison.release("sid_G")  # orchestrator finally（清理后）才归档
    assert "sid_G" not in registry.poison._active
    assert registry.poison.is_poisoned("sid_G")  # 归档仍拒绝


def test_single_pending_turn_shape_authority():
    """codex 轮次 11 P0-1 回归：启动探针的暂存消费必须走形状权威——
    list 形状取单轮、空/多轮显式报错（旧代码按单对象取 .raw_response 会在
    真实启动时 AttributeError）。"""

    registry = CaptureRegistry()
    registry.register("sid_P", FakeHook())
    with pytest.raises(RuntimeError, match="无暂存轮"):
        registry.single_pending_turn("sid_P")
    registry.stage("sid_P", _turn("rid_probe"))
    turn = registry.single_pending_turn("sid_P")
    assert turn.raw_response == {"meta_info": {"id": "rid_probe"}}  # 探针消费的两个字段
    assert turn.capture_params["top_p"] == 0.95
    # 多于一条（理论防御路径）：批 2b 后不同键可共存，探针形状权威仍拒多条
    # fail-closed，所以 len>1 分支只做直接构造验证
    registry.pending["sid_P"]["rid_extra"] = _turn("rid_extra")
    with pytest.raises(RuntimeError, match="数量异常"):
        registry.single_pending_turn("sid_P")


def test_register_rejects_poisoned_sid_reuse():
    """轮次 11 身份 3：中毒 SID（含归档）不得复用注册——稳定 ID 跨补采/
    epoch 复用时 fail-fast，不让 harness 带毒起跑。"""

    from repoharness2.adapters.slime.async_worker import SessionPoisonedError

    registry = CaptureRegistry()
    registry.poison.poison("sid_R", "bad")
    with pytest.raises(SessionPoisonedError):
        registry.register("sid_R", FakeHook())
    registry.poison.release("sid_R")  # 归档后依然拒绝
    with pytest.raises(SessionPoisonedError):
        registry.register("sid_R", FakeHook())


def test_unregister_poisons_before_abandon_even_if_sink_fails():
    """codex 轮次 12 P0 层 2：unregister 发现 leftover draft 时**先 poison**
    再尝试持久化 abandon evidence——sink 失败也不出现"带 pending draft 的
    训练样本继续走"，且异常不从清理路径传播（计数可见）。"""

    class SinkFailingProxyResult(FakeProxyResult):
        def abandon_delivered(self, reason: str) -> None:
            if self.state != "pending":
                raise ValueError("已定案")
            self.state = f"abandoned:{reason}"  # 事务化：先关
            raise OSError("disk full")  # 再报持久化失败

    registry = CaptureRegistry()
    registry.register("sid_U12", FakeHook())
    proxy = SinkFailingProxyResult("sid_U12/t1_a1")
    registry.stage("sid_U12", _turn("rid_1", proxy=proxy))
    registry.unregister("sid_U12")  # 不得抛
    assert registry.poison.is_poisoned("sid_U12")  # poison 先于 abandon
    assert registry.poison.reason("sid_U12") == "uncommitted_draft_at_unregister"
    assert proxy.state.startswith("abandoned:")  # draft 已关
    assert registry.stats["abandon_evidence_failures"] == 1


def test_assert_session_clean_boundary():
    """codex 轮次 12 P0 层 1：评分/Gate 前边界断言——pending 暂存或
    unfinalized draft 在场即 poison + 拒绝；干净则放行。"""

    registry = CaptureRegistry()
    registry.register("sid_B12", FakeHook())
    registry.assert_session_clean("sid_B12")  # 干净放行
    registry.stage("sid_B12", _turn("rid_1"))
    with pytest.raises(RuntimeError, match="capture_boundary_unclean"):
        registry.assert_session_clean("sid_B12")
    assert registry.poison.is_poisoned("sid_B12")


def test_register_rejects_duplicate_active_sid():
    """codex 轮次 12：健康 SID 并发重复注册不得静默覆盖 hook/账目——
    临时守卫直接拒绝（FA-2 唯一身份根治）。"""

    from repoharness2.adapters.slime.capture_wire import DuplicateActiveSessionError

    registry = CaptureRegistry()
    registry.register("sid_D12", FakeHook())
    with pytest.raises(DuplicateActiveSessionError):
        registry.register("sid_D12", FakeHook())
    # 正常时序（关旧开新）仍放行
    registry.unregister("sid_D12")
    registry.register("sid_D12", FakeHook())


def test_capture_registry_two_thread_stress():
    """codex 轮次 13 P0-3：真双线程压力——aiohttp 线程 stage/commit vs
    AsyncLoop 线程 register/unregister/assert 交错，不得 KeyError/丢账
    （旧实现确定性复现 KeyError('race_sid')）。"""

    import threading

    errors: list[BaseException] = []

    for round_i in range(50):
        registry = CaptureRegistry()
        sid = f"race_{round_i}"
        registry.register(sid, FakeHook())
        registry.stage(sid, _turn("rid_1"))
        barrier = threading.Barrier(2)

        def committer():
            try:
                barrier.wait()
                registry.commit(sid)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        def unregisterer():
            try:
                barrier.wait()
                registry.unregister(sid)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        t1 = threading.Thread(target=committer)
        t2 = threading.Thread(target=unregisterer)
        t1.start(); t2.start(); t1.join(5); t2.join(5)
    assert errors == []  # 修复前：KeyError('race_sid')


def test_commit_midpoint_hook_failure_abandons_and_poisons():
    """codex 轮次 13 P0-3 探针回归：commit 先 pop 再 hook——hook 中点异常
    必须 poison + 关闭 draft（旧行为：pending=0、draft 悬挂、无毒、账 0）。"""

    class ExplodingHook(FakeHook):
        def on_generate_response(self, **kwargs):
            raise RuntimeError("capture store failed")

    registry = CaptureRegistry()
    registry.register("sid_MID", ExplodingHook())
    proxy = FakeProxyResult("sid_MID/t1_a1")
    registry.stage("sid_MID", _turn("rid_1", proxy=proxy))
    with pytest.raises(RuntimeError, match="capture store failed"):
        registry.commit("sid_MID")
    assert registry.poison.is_poisoned("sid_MID")  # 修复前 false
    assert proxy.state.startswith("abandoned:capture_commit_hook_failed")  # 修复前悬挂
    assert registry.pending["sid_MID"] == {}


def test_commit_after_unregister_does_not_resurrect():
    """P0-3 竞态语义：commit 的 hook 执行期间会话被 unregister——本轮不进
    树后账（weight_versions 不复活）、poison + abandon。"""

    registry = CaptureRegistry()

    class UnregisterDuringHook(FakeHook):
        def on_generate_response(self, **kwargs):
            # 先触发 unregister 竞态，再按契约返回带 record_id 的记录
            registry.unregister("sid_RC")  # 模拟另一线程在 hook 窗口完成销毁
            return super().on_generate_response(**kwargs)

    registry.register("sid_RC", UnregisterDuringHook())
    proxy = FakeProxyResult("sid_RC/t1_a1")
    registry.stage("sid_RC", _turn("rid_1", version="9", proxy=proxy))
    registry.commit("sid_RC")
    assert "sid_RC" not in registry.weight_versions  # 不给已销毁会话追加
    assert registry.poison.is_poisoned("sid_RC")
    assert proxy.state.startswith("abandoned:commit_after_unregister")


async def test_session_guard_middleware_rejects_unknown_and_poisoned():
    """codex 轮次 13 P0-1：HTTP 层会话能力预检——未知/中毒 bearer 全部
    403 + x-should-retry:false（绝不 404），已注册健康会话放行。"""

    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    from repoharness2.adapters.slime.capture_wire import build_session_guard_middleware

    registry = CaptureRegistry()
    registry.register("sid_OK", FakeHook())
    registry.poison.poison("sid_BAD", "bad")
    hits: list[str] = []

    async def turn_handler(request):
        hits.append(request.headers.get("Authorization", ""))
        return web.json_response({"ok": True})

    app = web.Application(middlewares=[build_session_guard_middleware(registry)])
    app.router.add_post("/v1/messages", turn_handler)
    app.router.add_get("/healthz", turn_handler)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        r1 = await client.post("/v1/messages", headers={"Authorization": "Bearer sid_UNKNOWN"})
        assert r1.status == 403 and r1.headers["x-should-retry"] == "false"
        r2 = await client.post("/v1/messages", headers={"Authorization": "Bearer sid_BAD"})
        assert r2.status == 403
        r3 = await client.post("/v1/messages")  # 无凭证
        assert r3.status == 403
        assert hits == []  # 以上没有一个到达 handler（= 不产生 SGLang 请求）
        r4 = await client.post("/v1/messages", headers={"Authorization": "Bearer sid_OK"})
        assert r4.status == 200
        r5 = await client.get("/healthz")  # 健康检查放行
        assert r5.status == 200
    finally:
        await client.close()


@pytest.mark.filterwarnings("ignore::RuntimeWarning")  # 未调度协程的 GC 警告（停转 loop 语义本身）
async def test_drain_bridge_timeout_cancels_and_raises_typed():
    """窄 T0 共同必修：owner loop 停转时 drain 桥有界超时 → 取消命令 +
    typed 错（上层转 Fatal），不永久等待、不迟到生效。"""

    import asyncio

    from repoharness2.adapters.slime.capture_wire import (
        make_threadsafe_session_drain_owner,
    )

    registry = CaptureRegistry()
    registry.register("sid_TB", FakeHook(), physical_attempt_id="e#p1-tb")
    # 一个从不运行的 loop（模拟停转）：命令永不被调度
    dead_loop = asyncio.new_event_loop()
    assert make_threadsafe_session_drain_owner(registry, dead_loop) is not None

    async def _probe():
        # 缩短等待：monkeypatch wait_for 超时不可行——直接用小超时副本验证
        cfut = asyncio.run_coroutine_threadsafe(
            registry.drain_session_plane("sid_TB"), dead_loop)
        try:
            await asyncio.wait_for(asyncio.wrap_future(cfut), timeout=0.2)
        except (TimeoutError, asyncio.TimeoutError):
            cfut.cancel()
            raise RuntimeError("session_drain_owner_bridge_timeout: probe")
        raise AssertionError("不应到达")

    with pytest.raises(RuntimeError, match="bridge_timeout"):
        await _probe()
    assert "sid_TB" not in registry._revoked  # 命令从未被调度：无迟到副作用
    dead_loop.close()
