"""决策包 §8 切片 2：#8(i) `/v1/messages/count_tokens` 回真实计数（T1）。

经真实 vendored AnthropicAdapter app（真实路由 / 真实 session guard / 真实 turn 预算 wire）：先安装后构造，
计数 = 与生成同一路径（fold → translate → apply_chat_template）的渲染长度；不建轮、不进 capture、不计预算；
错误形状与启动核对。真实 tokenizer 与真实 CC 的 Read 截断由真机验收记录在 Brief。
"""

from __future__ import annotations

import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from repoharness2.adapters.slime import capture_wire as cw
from repoharness2.adapters.slime import count_tokens_wire as ctw

@pytest.fixture(autouse=True)
def _fresh_wire_generation(monkeypatch):
    """capture / turn-budget wire 是进程级单代归属：按既有测试的做法（test_w3b_bringup_sandbox_runtime）把归属
    重置成"新进程"，monkeypatch 在测试后恢复前一代的归属记录。"""
    from slime.agent.adapters import common as slime_common

    monkeypatch.setattr(slime_common, "_rh2_capture_wire_installed", False, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_registry", None, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_turn_budget_wire_registry", None, raising=False)



class _CountingTokenizer:
    """确定性：每条消息 1 + len(content)//16 个 token；tools 每个 3 个；生成提示 1 个。记录看到的消息供断言。"""

    def __init__(self):
        self.calls: list[dict] = []

    def apply_chat_template(self, messages, tools=None, tokenize=True, add_generation_prompt=True, **_kw):
        self.calls.append({"messages": json.loads(json.dumps(messages)), "tools": tools, "gen": add_generation_prompt})
        n = sum(1 + len(json.dumps(m.get("content", ""))) // 16 for m in messages) + 3 * len(tools or []) + (1 if add_generation_prompt else 0)
        return [1] * n

    def decode(self, ids, **_kw):
        return "decoded"


class _RaisingTokenizer(_CountingTokenizer):
    def apply_chat_template(self, *a, **kw):
        raise ValueError("System message must be at the beginning.")


def _build(tokenizer, *, install=True):
    from slime.agent.adapters.anthropic import AnthropicAdapter

    if install:
        ctw.install_count_tokens_wire()
    adapter = AnthropicAdapter(tokenizer=tokenizer, sglang_url="http://unused", max_turns_per_sid=3)
    return adapter


BODY = {
    "model": "slime-actor", "max_tokens": 16,
    "system": [{"type": "text", "text": "You are CC."}],
    "tools": [{"name": "Bash", "description": "run", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}}}],
    "messages": [
        {"role": "user", "content": [{"type": "text", "text": "read the file"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "cat big.py"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "x" * 2000}]},
        {"role": "system", "content": "reminder in the middle"},  # CC 的会话中 system → vendored fold 成 <system-reminder>
    ],
}


async def test_count_tokens_uses_the_generation_render_path_and_touches_no_turn_state():
    tok = _CountingTokenizer()
    adapter = _build(tok)
    ctw.bind_count_tokens_adapter(adapter)
    registry = cw.CaptureRegistry()
    cw.install_turn_budget_wire(registry)
    adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
    from repoharness2.adapters.slime.session_capability import mint_session_capability

    cap = mint_session_capability("exec_CT#p1-aaaa")
    sid = "s-exec_CT#p1-aaaa"

    class _Hook:
        records: list = []

    registry.register(sid, _Hook(), physical_attempt_id="exec_CT#p1-aaaa", capability_token=cap.token)
    adapter.open_session(sid)
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    try:
        hdr = {"Authorization": f"Bearer {cap.token}", "content-type": "application/json"}
        r = await client.post("/v1/messages/count_tokens", json=json.loads(json.dumps(BODY)), headers=hdr)
        assert r.status == 200
        n = (await r.json())["input_tokens"]
        # 与生成同一路径独立复算：fold → translate → 渲染
        from slime.agent.adapters.common import _render_token_ids

        body = json.loads(json.dumps(BODY))
        adapter._preprocess_body(body)
        translated, tools = adapter._translate(body)
        assert n == len(_render_token_ids(translated, tok, tools=tools, add_generation_prompt=True)) > 3
        seen = tok.calls[0]
        assert [m["role"] for m in seen["messages"]] == ["system", "user", "assistant", "tool", "user"]  # fold 后的形状
        assert "<system-reminder>" in json.dumps(seen["messages"][-1]) and seen["tools"] and seen["gen"] is True
        # 不建轮、不计预算、不进 capture
        assert registry.turn_budget_snapshot(sid) is None or registry.turn_budget_snapshot(sid)["accepted"] == 0
        assert _Hook.records == [] and adapter.inflight.get(sid, set()) == set()
        assert not registry.poison.is_poisoned(sid)
    finally:
        await client.close()
        registry.unregister(sid)


async def test_count_tokens_reports_template_rejections_as_400_and_bad_json_as_400():
    adapter = _build(_RaisingTokenizer())
    ctw.bind_count_tokens_adapter(adapter)
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    try:
        r = await client.post("/v1/messages/count_tokens", json=BODY)
        assert r.status == 400 and "System message must be at the beginning" in (await r.json())["error"]["message"]
        r = await client.post("/v1/messages/count_tokens", data=b"{not json", headers={"content-type": "application/json"})
        assert r.status == 400
    finally:
        await client.close()


async def test_unbound_adapter_is_a_clear_500_not_a_silent_zero():
    adapter = _build(_CountingTokenizer())  # 安装了但没 bind
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    try:
        r = await client.post("/v1/messages/count_tokens", json=BODY)
        assert r.status == 500 and "unbound" in (await r.json())["error"]["message"]
    finally:
        await client.close()


def test_startup_assertion_catches_construct_before_install(monkeypatch):
    import slime.agent.adapters.anthropic as anthropic_mod

    original = anthropic_mod._count_tokens
    vendored = getattr(anthropic_mod, "_rh2_vendored_count_tokens_for_test", None)
    # 还原成 vendored 的恒 0 handler 再构造：路由绑的是它 → 启动核对必须拒绝
    async def zero(request):
        await request.read()
        return anthropic_mod.web.json_response({"input_tokens": 0})

    monkeypatch.setattr(anthropic_mod, "_count_tokens", zero)
    adapter = _build(_CountingTokenizer(), install=False)
    with pytest.raises(RuntimeError, match="不是 rh2_count_tokens"):
        ctw.bind_count_tokens_adapter(adapter)
    monkeypatch.setattr(anthropic_mod, "_count_tokens", original)
    del vendored
    # 装了但没 bind：同样拒绝
    adapter2 = _build(_CountingTokenizer())
    with pytest.raises(RuntimeError, match="未绑定"):
        ctw.assert_count_tokens_bound(adapter2.app)
    ctw.install_count_tokens_wire()  # 幂等
    assert anthropic_mod._count_tokens is ctw.rh2_count_tokens
