"""决策包 §8 切片 3：#8(ii)(iii)(iv)——CC 窗口 / 压缩窗口 / 输出预留 / Read 上限按作业配置逐 execution 注入；
RH2 capture wire 真正溢出时回 Anthropic 形状的 400 "prompt is too long"（不伪造采样、不留 pending、不进 capture、不 poison）。
数值都是测试参数（4096 / 512 / 2000 / 10），不是正式训练配置。真实 CC 的压缩行为由真机验收记录在 Brief。
"""

from __future__ import annotations

import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from repoharness2.adapters.slime import capture_wire as cw
from repoharness2.adapters.slime import cc_launch_conditions as cc
from repoharness2.adapters.slime.generate import SlimeBindingConfig

from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain, dense_config


def test_context_env_maps_job_config_and_is_empty_without_a_window():
    assert cc.cc_context_env(max_context_len=0, max_new_tokens=512, file_read_max_output_tokens=2000) == {}
    env = cc.cc_context_env(max_context_len=4096, max_new_tokens=512, file_read_max_output_tokens=2000)
    assert env == {
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "4096", "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "4096",
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "512", "CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS": "2000",
    }
    assert cc.cc_context_env(max_context_len=4096, max_new_tokens=None, file_read_max_output_tokens=None) == {
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "4096", "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "4096"}
    assert cc.cc_compaction_margin(max_context_len=32768, max_new_tokens=4096) == 32768 - 4096 - 13000
    assert cc.cc_compaction_margin(max_context_len=0, max_new_tokens=None) is None
    assert SlimeBindingConfig.__dataclass_fields__["cc_file_read_max_output_tokens"].default is None


async def test_launch_spec_injects_window_env_per_execution_when_configured():
    chain = build_dense_chain(config=dense_config(max_context_len=4096, cc_file_read_max_output_tokens=2000))
    await chain.orchestrator.generate(_Args(), chain.base_sample, {**SAMPLING_PARAMS, "max_new_tokens": 512})
    inj = chain.orchestrator.audits[0].launch_spec.env_injections
    assert inj["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "4096" and inj["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "4096"
    assert inj["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "512" and inj["CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS"] == "2000"
    assert inj["BASH_ENV"] == "/rh2/bash_env"  # #1 的注入仍在
    chain0 = build_dense_chain()
    await chain0.orchestrator.generate(_Args(), chain0.base_sample, dict(SAMPLING_PARAMS))
    inj0 = chain0.orchestrator.audits[0].launch_spec.env_injections
    assert not any(k.startswith("CLAUDE_CODE_") for k in inj0)  # 未配置窗口：不注入


@pytest.fixture(autouse=True)
def _fresh_wire_generation(monkeypatch):
    """capture / turn-budget wire 是进程级单代归属：按既有测试的做法（test_w3b_bringup_sandbox_runtime）把归属
    重置成"新进程"，monkeypatch 在测试后恢复前一代的归属记录。"""
    from slime.agent.adapters import common as slime_common

    monkeypatch.setattr(slime_common, "_rh2_capture_wire_installed", False, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_registry", None, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_turn_budget_wire_registry", None, raising=False)


# ---------------------------------------------------------------------------
# 溢出 → 400：真实 vendored adapter app + 真实 capture wire + 假引擎（同 tests/adapters_miles/test_b2_mask_chain 的替身形状）
# ---------------------------------------------------------------------------


class _Tok:
    """prompt 长度 = 消息数 × 8（可控地跨过 max_context_tokens=10）；decode 回 XML tool_call 或文本。"""

    def apply_chat_template(self, messages, tools=None, tokenize=True, add_generation_prompt=True, **_kw):
        return [1] * (8 * len(messages))

    def decode(self, ids, **_kw):
        return "summary text"


class _Resp:
    def __init__(self, payload):
        self.status, self._p = 200, payload

    async def json(self, content_type=None):
        return self._p

    async def text(self):
        return json.dumps(self._p)


class _CM:
    def __init__(self, r):
        self._r = r

    async def __aenter__(self):
        return self._r

    async def __aexit__(self, *e):
        return False


class _Engine:
    def __init__(self):
        self.calls = 0

    def post(self, url, json=None, headers=None):
        self.calls += 1
        return _CM(_Resp({"text": "summary text", "meta_info": {"id": "r1", "weight_version": "1", "finish_reason": {"type": "stop"},
                                                              "output_token_logprobs": [[-0.1, 5, None], [-0.1, 6, None]]}}))


class _FakeAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self._e = engine

    def ClientTimeout(self, **_k):  # noqa: N802
        return None

    def ClientSession(self, **_k):  # noqa: N802
        eng = self._e

        class S:
            async def __aenter__(self_):
                return self_

            async def __aexit__(self_, *e):
                return False

            def post(self_, url, json=None, headers=None):
                return eng.post(url, json=json, headers=headers)

        return S()


def _real_hook():
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    return GenerationCaptureHook(trajectory_id="exec_OV", model_name="m", backend_name="sglang", backend_version="v",
                                 renderer_cls_name="r", tokenizer_name="t", template_hash="sha256:" + "0" * 64)


async def test_overflow_returns_prompt_too_long_400_without_fake_sampling_or_pending(monkeypatch):
    from slime.agent.adapters.anthropic import AnthropicAdapter

    from repoharness2.adapters.slime.session_capability import mint_session_capability

    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    engine = _Engine()
    monkeypatch.setattr(cw, "aiohttp", _FakeAiohttp(engine))
    adapter = AnthropicAdapter(tokenizer=_Tok(), sglang_url="http://fake-engine", max_turns_per_sid=5)
    adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
    cap = mint_session_capability("exec_OV#p1-aaaa")
    sid = "s-exec_OV#p1-aaaa"
    hook = _real_hook()
    registry.register(sid, hook, physical_attempt_id="exec_OV#p1-aaaa", capability_token=cap.token)
    adapter.open_session(sid, max_context_tokens=10)  # 测试参数：2 条消息 = 16 token 就溢出
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    hdr = {"Authorization": f"Bearer {cap.token}", "content-type": "application/json"}
    try:
        long_body = {"model": "m", "max_tokens": 16, "messages": [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]}
        r = await client.post("/v1/messages", json=long_body, headers=hdr)
        assert r.status == 400
        err = await r.json()
        assert err["type"] == "error" and err["error"]["type"] == "invalid_request_error"
        assert err["error"]["message"] == "prompt is too long: 16 tokens > 10 maximum"
        assert engine.calls == 0 and hook.records == []  # 没调引擎、没伪造采样、没进 capture
        assert adapter.inflight.get(sid, set()) == set() and not registry.poison.is_poisoned(sid)
        assert registry.stats.get("prompt_too_long") == 1
        # 压缩后的短请求照常成功：会话没有被 400 破坏
        short_body = {"model": "m", "max_tokens": 16, "messages": [{"role": "user", "content": "summary"}]}
        r2 = await client.post("/v1/messages", json=short_body, headers=hdr)
        assert r2.status == 200, await r2.text()
        assert engine.calls == 1 and len(hook.records) == 1
        snap = registry.turn_budget_snapshot(sid)
        assert snap is None or snap["accepted"] == 2  # 溢出请求按 vendored 既有行为计入接纳数（已被接纳的模型请求）
    finally:
        await client.close()
        drain = await registry.drain_session_plane(sid)
        assert drain.pending_turns == 0 and drain.unfinalized_drafts == 0  # 溢出没有留下 pending
        registry.unregister(sid)
    with pytest.raises(cw.CaptureWireOwnershipError):
        cw.install_capture_wire(cw.CaptureRegistry())
