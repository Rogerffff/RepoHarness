"""#8(iii) 溢出 400 的共用构造与"没装 capture wire 的部署"用的独立安装（A→B 接线交接 §6.1）。

- 构造：与 capture wire 既有用例同一条响应（`test_cc_context_window` 的溢出用例继续断言 capture wire 路径）。
- 独立安装：真实 vendored `AnthropicAdapter` 的 HTTP 应用、**不装 capture wire**（B 的基座探针形态），引擎用替身：
  溢出请求得到 Anthropic 形状的 400、引擎零调用；压缩后的短请求照常 200；未配置窗口（0）不判溢出；重复安装不叠层。
"""

from __future__ import annotations

import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from repoharness2.adapters.slime import prompt_overflow as po


def test_builder_matches_the_capture_wire_response_shape():
    assert po.prompt_overflows(16, 10) and po.prompt_overflows(10, 10) and not po.prompt_overflows(9, 10)
    assert not po.prompt_overflows(10**6, 0)  # 未配置窗口：不判
    err = po.prompt_too_long_error(16, 10)
    assert err.status == 400 and err.content_type == "application/json"
    assert json.loads(err.text) == {"type": "error", "error": {
        "type": "invalid_request_error", "message": "prompt is too long: 16 tokens > 10 maximum"}}


class _Tok:
    """每条消息渲染 8 个 token（与 test_cc_context_window 的替身同口径：2 条消息 = 16 token）。"""

    eos_token = "<|im_end|>"
    eos_token_id = 7

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True, tools=None, **_kw):
        ids = [1] * (8 * len(messages))
        return ids if tokenize else "x" * len(ids)

    def decode(self, ids, skip_special_tokens=False):
        return "ok"


@pytest.fixture
def base_generate(monkeypatch):
    """把 vendored 模块属性换成本测试的替身基底（不依赖此前模块是否装过 capture wire），测试结束还原。"""

    from slime.agent.adapters import common as slime_common
    from slime.agent.trajectory import TurnRecord

    calls: list[int] = []

    async def fake_generate(prompt_ids, session, body, *, adapter, session_id=None):
        calls.append(len(prompt_ids))
        return TurnRecord(prompt_ids=list(prompt_ids), output_ids=[5, 6], finish_reason="stop")

    monkeypatch.setattr(slime_common, "call_sglang_generate", fake_generate)
    return calls


async def test_standalone_install_turns_overflow_into_the_400_without_calling_the_engine(base_generate):
    from slime.agent.adapters.anthropic import AnthropicAdapter

    po.install_overflow_400_wire()
    po.install_overflow_400_wire()  # 幂等：不叠第二层
    assert po.overflow_400_wire_installed()
    adapter = AnthropicAdapter(tokenizer=_Tok(), sglang_url="http://fake-engine")
    adapter.open_session("probe-sid", max_context_tokens=10)
    adapter.open_session("no-window", max_context_tokens=0)
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    try:
        long_body = {"model": "m", "max_tokens": 16, "messages": [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]}
        r = await client.post("/v1/messages", json=long_body, headers={"Authorization": "Bearer probe-sid"})
        assert r.status == 400
        assert await r.json() == po.prompt_too_long_body(16, 10)
        assert base_generate == []  # 引擎零调用
        short_body = {"model": "m", "max_tokens": 16, "messages": [{"role": "user", "content": "summary"}]}
        r2 = await client.post("/v1/messages", json=short_body, headers={"Authorization": "Bearer probe-sid"})
        assert r2.status == 200, await r2.text()
        assert base_generate == [8]
        r3 = await client.post("/v1/messages", json=long_body, headers={"Authorization": "Bearer no-window"})
        assert r3.status == 200 and base_generate == [8, 16]  # 未配置窗口：照常调用
    finally:
        await client.close()
