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
