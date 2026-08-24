"""F2-3 批 2a 复核收尾：真实 AnthropicAdapter + TrajectoryManager 的
drain-before-freeze CPU 回归（把 codex 的手工交错探针固化进 oracle）。

不变量：owner drain（adapter loop 上 revoke + rh2 inflight 归零）先于
finish_session（冻结/弹树）——真实 HTTP turn 在飞时 owner 必须等待；
冻结后树被恰好消费一次（无残留）；迟到请求 403；线程干净退出。
reference/slime 缺席时 skip（同 contract_slime_async 口径）。
"""

from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path

import pytest

_SLIME_ROOT = Path(__file__).resolve().parents[3] / "reference" / "slime"

pytestmark = pytest.mark.skipif(
    not _SLIME_ROOT.exists(), reason="reference/slime 不在本地，无真实被测物"
)

if _SLIME_ROOT.exists():  # pragma: no branch
    sys.path.insert(0, str(_SLIME_ROOT))

from repoharness2.adapters.slime.capture_wire import (  # noqa: E402
    CaptureRegistry,
    build_session_guard_middleware,
    make_threadsafe_session_drain_owner,
)


class _FakeTokenizer:
    def apply_chat_template(self, *a, **kw):
        return [1, 2, 3]

    def decode(self, *a, **kw):
        return "decoded"


async def test_real_adapter_drain_before_freeze_invariant():
    import slime.agent.adapters.common as slime_common
    from aiohttp.test_utils import TestServer
    from slime.agent.adapters.anthropic import AnthropicAdapter
    from slime.utils.types import Sample

    import aiohttp

    sid = "s-exec_real#p1-aaaa"
    registry = CaptureRegistry()

    class _Hook:
        records: list = []

    registry.register(sid, _Hook(), physical_attempt_id="exec_real#p1-aaaa")

    # canned 慢引擎：真实 _run_turn/record_turn 全走，只有 SGLang 调用被替身
    orig_call = slime_common.call_sglang_generate

    async def slow_canned(prompt_ids, session, body, *, adapter, session_id):
        await asyncio.sleep(0.3)
        return slime_common.TurnRecord(
            prompt_ids=list(prompt_ids),
            output_ids=[7, 8],
            finish_reason="stop",
            output_log_probs=[0.0, 0.0],
        )

    slime_common.call_sglang_generate = slow_canned

    adapter = AnthropicAdapter(tokenizer=_FakeTokenizer(), sglang_url="http://unused")
    adapter.app.middlewares.append(build_session_guard_middleware(registry))
    adapter.open_session(sid)

    loop_holder: dict = {}
    server_ready = threading.Event()

    def adapter_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop
        stop_event = asyncio.Event()
        loop_holder["stop"] = stop_event

        async def _serve():
            server = TestServer(adapter.app)
            await server.start_server()
            loop_holder["port"] = server.port
            server_ready.set()
            await stop_event.wait()
            await server.close()

        loop.run_until_complete(_serve())
        loop.close()

    t = threading.Thread(target=adapter_thread, daemon=True)
    t.start()
    assert server_ready.wait(5)
    port = loop_holder["port"]
    owner = make_threadsafe_session_drain_owner(registry, loop_holder["loop"])
    body = {
        "model": "m",
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "hi"}],
    }

    try:
        async with aiohttp.ClientSession() as client:
            slow = asyncio.create_task(client.post(
                f"http://127.0.0.1:{port}/v1/messages",
                headers={"Authorization": f"Bearer {sid}"}, json=body))
            for _ in range(200):  # 等真实 turn 进入在飞（rh2 计数可见）
                if registry._inflight.get(sid):
                    break
                await asyncio.sleep(0.01)
            assert registry._inflight.get(sid) == 1
            result = await owner(sid)  # 必须等真实 HTTP turn 完成
            assert result.inflight_at_drain_start == 1
            assert result.inflight_zero_confirmed is True
            assert result.pending_turns == 0 and result.poison_clean is True
            resp = await slow
            assert resp.status == 200  # 在飞 turn 被等待完成（非砍杀）

            # drain 干净之后才冻结：树恰好被消费一次
            samples = await adapter.finish_session(
                sid, base_sample=Sample(index=0, prompt="p"), reward=0.0)
            assert len(samples) == 1  # 真实 record_turn 的树恰好一条
            again = adapter.manager.get_trajectory(
                sid, base_sample=Sample(index=0, prompt="p"), reward=0.0,
                extra_metadata=None, max_sample_tokens=0)
            assert again == []  # 冻结后无残留树（弹树恰好一次）

            late = await client.post(
                f"http://127.0.0.1:{port}/v1/messages",
                headers={"Authorization": f"Bearer {sid}"}, json=body)
            assert late.status == 403  # 撤销后迟到请求拒之门外
            late_body = await late.json()
            assert late_body["error"]["type"] == "rh2_session_revoked"
        assert registry._inflight.get(sid) is None  # 退账干净
        assert registry.drain_snapshot(sid)[
            "late_requests_rejected_after_revoke"] == 1
    finally:
        slime_common.call_sglang_generate = orig_call
        loop_holder["loop"].call_soon_threadsafe(loop_holder["stop"].set)
        t.join(timeout=5)
    assert not t.is_alive()  # server 线程干净退出


class _RecProxy:
    def __init__(self):
        self.finalized = None
        self.abandoned = None

    def finalize_delivered(self, ref):
        self.finalized = ref

    def abandon_delivered(self, reason):
        self.abandoned = reason


class _RecHook:
    """返回带真实 record_id 的替身（P1 引用断言用）。"""

    def __init__(self):
        self.calls = []
        self.records = []

    def on_generate_response(self, *, prompt_token_ids, sampling_params, response):
        from types import SimpleNamespace

        self.calls.append(response["meta_info"]["marker"])
        rec = SimpleNamespace(record_id=f"cap_real_t{len(self.calls) - 1}")
        self.records.append(rec)  # 引用必须可解析回真实记录（收口二轮）
        return rec


async def _run_capture_chain(markers_cfg, requests):
    """真实 AnthropicAdapter + 包装 record_turn + 真实 stage/commit 链。

    markers_cfg: marker -> (sleep_s, do_stage, proxy|None)
    requests: [(marker, ...)]；返回 (registry, hook, proxies)
    """

    import aiohttp
    import slime.agent.adapters.common as slime_common
    from aiohttp.test_utils import TestServer
    from slime.agent.adapters.anthropic import AnthropicAdapter
    from slime.agent.trajectory import TrajectoryManager

    from repoharness2.adapters.slime.capture_wire import PendingTurn

    sid = "s-exec_cc#p1-bbbb"
    registry = CaptureRegistry()
    hook = _RecHook()
    registry.register(sid, hook, physical_attempt_id="exec_cc#p1-bbbb")

    orig_call = slime_common.call_sglang_generate

    async def staged_canned(prompt_ids, session, body, *, adapter, session_id):
        marker = body["messages"][0]["content"]
        sleep_s, do_stage, proxy = markers_cfg[marker]
        if do_stage:
            registry.stage(session_id, PendingTurn(
                prompt_ids=list(prompt_ids), capture_params={"top_p": 1.0},
                raw_response={"meta_info": {"marker": marker}},
                weight_version="7", request_id=f"rid_{marker}",
                proxy_result=proxy))
        await asyncio.sleep(sleep_s)
        return slime_common.TurnRecord(
            prompt_ids=list(prompt_ids), output_ids=[7],
            finish_reason="length" if not do_stage else "stop",
            output_log_probs=[0.0])

    slime_common.call_sglang_generate = staged_canned
    orig_record = TrajectoryManager.record_turn

    def wrapped_record(self, sid_, *a, **kw):
        out = orig_record(self, sid_, *a, **kw)
        registry.commit(sid_)  # 同请求 task 内（ContextVar 键在场）
        return out

    TrajectoryManager.record_turn = wrapped_record
    adapter = AnthropicAdapter(tokenizer=_FakeTokenizer(), sglang_url="http://x")
    adapter.app.middlewares.append(build_session_guard_middleware(registry))
    adapter.open_session(sid)

    loop_holder: dict = {}
    server_ready = threading.Event()

    def adapter_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop
        stop_event = asyncio.Event()
        loop_holder["stop"] = stop_event

        async def _serve():
            server = TestServer(adapter.app)
            await server.start_server()
            loop_holder["port"] = server.port
            server_ready.set()
            await stop_event.wait()
            await server.close()

        loop.run_until_complete(_serve())
        loop.close()

    t = threading.Thread(target=adapter_thread, daemon=True)
    t.start()
    assert server_ready.wait(5)
    port = loop_holder["port"]
    try:
        async with aiohttp.ClientSession() as client:
            async def post(marker):
                return await client.post(
                    f"http://127.0.0.1:{port}/v1/messages",
                    headers={"Authorization": f"Bearer {sid}"},
                    json={"model": "m", "max_tokens": 8,
                          "messages": [{"role": "user", "content": marker}]})

            resps = await asyncio.gather(*[post(m) for m, in requests])
            assert all(r.status == 200 for r in resps)
    finally:
        slime_common.call_sglang_generate = orig_call
        TrajectoryManager.record_turn = orig_record
        loop_holder["loop"].call_soon_threadsafe(loop_holder["stop"].set)
        t.join(timeout=5)
    return registry, hook, sid


async def test_out_of_order_completion_capture_matches_each_turn():
    """收口回归 1：同 SID 两请求乱序完成——各按请求键 commit，capture 与
    各自 turn 一一对应（先完成的先进树但绝不拿错轮）。"""

    pa, pb = _RecProxy(), _RecProxy()
    registry, hook, sid = await _run_capture_chain(
        {"r_slow": (0.35, True, pa), "r_fast": (0.1, True, pb)},
        [("r_slow",), ("r_fast",)])
    assert hook.calls == ["r_fast", "r_slow"]  # 完成序进树，且各归其轮
    assert pb.finalized == "cap_real_t0" and pa.finalized == "cap_real_t1"
    resolvable = {r.record_id for r in hook.records}
    assert {pa.finalized, pb.finalized} <= resolvable  # 引用可解析（非字符串巧合）
    assert registry.stats["committed"] == 2
    assert not registry.poison.is_poisoned(sid)
    assert registry.pending[sid] == {}


async def test_commit_without_stage_never_steals_pending():
    """收口回归 2（P0 复现型）：A 已 stage 在飞，B 走 max-context 短路
    （无 stage）先 record_turn——B 的 commit 不得消费/finalize A。"""

    pa = _RecProxy()
    registry, hook, sid = await _run_capture_chain(
        {"a_slow": (0.4, True, pa), "b_len": (0.05, False, None)},
        [("a_slow",), ("b_len",)])
    assert hook.calls == ["a_slow"]  # 只有 A 进 capture（B 无 stage）
    assert pa.finalized == "cap_real_t0"  # A 由自己的 commit finalize（P1 真实引用）
    assert registry.stats["commit_without_stage"] == 1  # B 落账后返回
    assert registry.stats["committed"] == 1
    assert not registry.poison.is_poisoned(sid)  # 不误毒
    assert registry.pending[sid] == {}


def test_hook_without_record_id_never_finalizes():
    """收口二轮 P1 负例：hook 返回 None/无 record_id → 走 hook-failure
    事务路径（poison + abandon + 抛错），绝不产出 delivered attempt。"""

    from repoharness2.adapters.slime.capture_wire import CaptureRegistry, PendingTurn

    registry = CaptureRegistry()

    class _BadHook:
        records: list = []

        def on_generate_response(self, **kw):
            return None  # 违约：无记录

    registry.register("s-bad", _BadHook())
    proxy = _RecProxy()
    registry.stage("s-bad", PendingTurn(
        prompt_ids=[1], capture_params={}, raw_response={"meta_info": {}},
        weight_version=None, request_id="rid_bad", proxy_result=proxy))
    with pytest.raises(RuntimeError, match="capture_hook_returned_no_record_id"):
        registry.commit("s-bad")
    assert proxy.finalized is None  # 绝不 finalize
    assert proxy.abandoned == "capture_commit_hook_failed"
    assert registry.poison.is_poisoned("s-bad")
