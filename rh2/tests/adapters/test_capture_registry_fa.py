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

from s1_7a_bringup.capture_wire import (  # noqa: E402
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

    def on_generate_response(self, *, prompt_token_ids, sampling_params, response) -> None:
        self.calls.append({"prompt": list(prompt_token_ids), "response": response})


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
    assert proxy.state.startswith("finalized:capture:sid_A:rid_1")  # 真实 request_id
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


def test_concurrent_stage_overlap_fails_closed():
    """codex 轮次 9 P0-2：并发同 session 暂存重叠 fail-closed——slime 的
    record_turn 按完成序到达，FIFO 弹最旧会把 A 的 token 记到 B 名下（串账
    比丢数据更危险）。request 级归属是 FA-2 第一验收项；落地前：poison +
    两轮 abandon + 抛 CapturePendingOverlapError。"""

    registry = CaptureRegistry()
    hook = FakeHook()
    registry.register("sid_C", hook)
    p1, p2 = FakeProxyResult("a1"), FakeProxyResult("a2")
    registry.stage("sid_C", _turn("rid_1", version="1", proxy=p1))
    with pytest.raises(CapturePendingOverlapError):
        registry.stage("sid_C", _turn("rid_2", version="2", proxy=p2))
    assert registry.stats["concurrent_overlap_seen"] == 1
    assert registry.poison.is_poisoned("sid_C")  # session 中毒
    # 两轮都不可信（完成序未知）：全部 abandon，不做归属猜测
    assert p1.state.startswith("abandoned:capture_pending_overlap")
    assert p2.state.startswith("abandoned:capture_pending_overlap")
    registry.commit("sid_C")
    assert len(hook.calls) == 0  # 什么都没进树
    assert registry.pending["sid_C"] == []  # 无残留


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


def test_unregister_releases_poison_to_archive():
    """轮次 10 P0-4 接线：CaptureRegistry.unregister = 清理 ACK ->
    poison.release（active -> 有界归档，仍可查）。"""

    registry = CaptureRegistry()
    registry.register("sid_G", FakeHook())
    registry.poison.poison("sid_G", "bad")
    assert "sid_G" in registry.poison._active
    registry.unregister("sid_G")
    assert "sid_G" not in registry.poison._active  # 已释放
    assert registry.poison.is_poisoned("sid_G")  # 归档仍拒绝
