"""C1′-b delta 测试 (a)：capture_wire 的 sampling-support mask 捕获接线。

驱动真实 `rh2_call_sglang_generate`（vendor slime 世界 + install_capture_wire）,
HTTP 层用 fake aiohttp 短路到内存 fake 引擎——断言四件事：

1. 请求旗标顶层化：会话默认键 `return_sampling_mask` 被 pop 出
   sampling_params、以顶层 `return_sampling_mask: true` 进请求体
   （sglang-miles wire 约定,对照 miles/rollout/sglang_rollout.py payload 注入）;
2. 前置校验拒绝分支 fail-closed：不可忠实 replay 的请求**不发 HTTP**;
3. 响应解析：output_token_sampling_mask/_logprobs 校验（长度、逐 token
   sampled∈support）,TurnRecord logprob 列切换为 support-normalized 值
   （T0-B 正式分母列）,全词表列留 raw_response;
4. capture_params 生效值补记（return_sampling_mask/top_k）。
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base


class _FakeResponse:
    def __init__(self, payload):
        self.status = 200
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return ""


class _PostCM:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class _FakeEngine:
    def __init__(self):
        self.requests: list[dict] = []
        self.response_payload: dict | None = None


class _FakeClientSession:
    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self._engine.requests.append({"url": url, "payload": json, "headers": headers})
        return _PostCM(_FakeResponse(self._engine.response_payload))


class _FakeAiohttp:
    """rh2_call_sglang_generate 内引用的 aiohttp 符号面（happy path 用到的三个）。"""

    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self._engine = engine

    def ClientTimeout(self, **_kw):  # noqa: N802 - 镜像 aiohttp API 名
        return None

    def ClientSession(self, **_kw):  # noqa: N802
        return _FakeClientSession(self._engine)


SID = "sid-mask-test"


@pytest.fixture(scope="module")
def wire(_vendor_slime_world):
    from slime.agent.adapters import common as slime_common

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    registry = cw.CaptureRegistry()
    registry.hooks[SID] = GenerationCaptureHook(
        trajectory_id="traj_mask",
        model_name="m",
        backend_name="sglang",
        backend_version="test",
        renderer_cls_name="r",
        tokenizer_name="tok",
        template_hash="h",
    )
    cw.install_capture_wire(registry)

    engine = _FakeEngine()
    saved_aiohttp = cw.aiohttp
    cw.aiohttp = _FakeAiohttp(engine)
    try:
        yield SimpleNamespace(
            registry=registry, engine=engine, slime_common=slime_common, cw=cw
        )
    finally:
        cw.aiohttp = saved_aiohttp
        # vendor slime 模块随 _vendor_slime_world teardown 整体摘除,monkeypatch
        # 不需要单独还原（下个 world 重新 import 得到干净 slime_common）。


def _mask_defaults(**over):
    defaults = {
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 32,
        "return_sampling_mask": True,
    }
    defaults.update(over)
    return {k: v for k, v in defaults.items() if v is not None}


def _ok_payload(**meta_over):
    meta = {
        "id": "rid-fake",
        "weight_version": "w7",
        "finish_reason": {"type": "stop"},
        "output_token_logprobs": [[-1.2, 7], [-0.9, 3]],  # 全词表列（诊断）
        "output_token_sampling_mask": [[5, 7, 9], [3, 4]],
        "output_token_sampling_logprobs": [-0.2, -0.4],  # support-normalized 列
    }
    meta.update(meta_over)
    meta = {k: v for k, v in meta.items() if v is not None}
    return {"text": "ok", "meta_info": meta}


async def _call(wire, defaults, body=None, payload=None):
    wire.engine.response_payload = payload if payload is not None else _ok_payload()
    session = wire.slime_common.Session(
        sampling_defaults=dict(defaults), max_context_tokens=0
    )
    adapter = SimpleNamespace(
        logger=logging.getLogger("test_capture_wire_sampling_mask"),
        max_token_keys=("max_tokens",),
        stop_keys=("stop",),
        sglang_url="http://fake-engine:1",
    )
    return await wire.slime_common.call_sglang_generate(
        [101, 102, 103], session, body or {}, adapter=adapter, session_id=SID
    )


def _pop_staged(wire):
    slot = wire.registry.pending.get(SID) or {}
    assert len(slot) == 1, f"期望恰好 1 条暂存,得到 {len(slot)}"
    return slot.pop(next(iter(slot)))


# ---------------------------------------------------------------------------
# 1+3+4：happy path——旗标顶层化 / logprob 列切换 / capture_params 补记
# ---------------------------------------------------------------------------


async def test_flag_toplevel_logprob_swap_and_capture_params(wire):
    record = await _call(wire, _mask_defaults())

    req = wire.engine.requests[-1]
    payload = req["payload"]
    assert payload["return_sampling_mask"] is True  # 顶层旗标（sglang-miles wire）
    sp = payload["sampling_params"]
    assert "return_sampling_mask" not in sp  # 会话默认键已被 pop,不进 sampling_params
    assert sp["top_k"] == 32 and sp["top_p"] == 0.8 and sp["temperature"] == 0.7

    # TurnRecord logprob 列 = support-normalized（T0-B 正式分母列）,非全词表列
    assert record.output_ids == [7, 3]
    assert record.output_log_probs == [-0.2, -0.4]

    staged = _pop_staged(wire)
    assert staged.capture_params["return_sampling_mask"] is True
    assert staged.capture_params["top_k"] == 32
    assert staged.capture_params["top_p"] == 0.8
    # 全词表列原样留在 raw_response（诊断列,不被 mask 解析改写）
    assert staged.raw_response["meta_info"]["output_token_logprobs"] == [[-1.2, 7], [-0.9, 3]]
    assert staged.raw_response["meta_info"]["output_token_sampling_logprobs"] == [-0.2, -0.4]
    assert staged.weight_version == "w7"


async def test_without_flag_keeps_full_vocab_logprobs(wire):
    record = await _call(wire, _mask_defaults(return_sampling_mask=None))

    payload = wire.engine.requests[-1]["payload"]
    assert "return_sampling_mask" not in payload
    assert record.output_log_probs == [-1.2, -0.9]  # 全词表列原语义,不切换

    staged = _pop_staged(wire)
    assert staged.capture_params["return_sampling_mask"] is False
    assert staged.capture_params["top_k"] == 32  # 生效值照记（与旗标无关）


# ---------------------------------------------------------------------------
# 2：前置校验拒绝分支——不发 HTTP、不暂存
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("defaults_over", "body", "reason_code"),
    [
        ({"top_k": None}, None, "sampling_mask_param_missing"),
        ({"top_p": 1.0}, None, "sampling_mask_top_p_invalid"),
        ({"top_k": 0}, None, "sampling_mask_top_k_unbounded"),
        # body 覆盖温度 != 会话配置温度 -> replay 分布漂移,拒绝
        ({}, {"temperature": 0.5}, "sampling_mask_temperature_mismatch"),
        # body 放大 top_k 超过会话配置上界 -> 拒绝（上游 request<=configured 同款）
        ({}, {"top_k": 64}, "sampling_mask_top_k_exceeds_configured"),
        ({"frequency_penalty": 0.5}, None, "sampling_mask_unsupported_logit_param"),
    ],
)
async def test_precheck_rejects_before_http(wire, defaults_over, body, reason_code):
    from repoharness2.adapters.miles.sampling_mask_assembly import SamplingMaskAssemblyError

    requests_before = len(wire.engine.requests)
    staged_before = wire.registry.stats["staged"]
    with pytest.raises(SamplingMaskAssemblyError) as exc:
        await _call(wire, _mask_defaults(**defaults_over), body=body)
    assert exc.value.reason_code == reason_code
    assert len(wire.engine.requests) == requests_before  # 请求根本没发出去
    assert wire.registry.stats["staged"] == staged_before


# ---------------------------------------------------------------------------
# 3：响应解析 fail-closed 分支
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("meta_over", "reason_code"),
    [
        # 引擎不是 sglang-miles 构建（stock 静默忽略形态）
        (
            {"output_token_sampling_mask": None, "output_token_sampling_logprobs": None},
            "sampling_mask_missing_in_response",
        ),
        ({"output_token_sampling_logprobs": [-0.2]}, "sampling_logprob_length_mismatch"),
        ({"output_token_sampling_mask": [[5, 7]]}, "sampling_mask_length_mismatch"),
        # sampled token 7 不在支持集 [5, 9] 内——传输错位/数据损坏
        ({"output_token_sampling_mask": [[5, 9], [3, 4]]}, "turn_sampled_not_in_support"),
        ({"output_token_sampling_mask": [[5, 7], []]}, "turn_support_empty"),
    ],
)
async def test_response_parse_fail_closed(wire, meta_over, reason_code):
    from repoharness2.adapters.miles.sampling_mask_assembly import SamplingMaskAssemblyError

    staged_before = wire.registry.stats["staged"]
    with pytest.raises(SamplingMaskAssemblyError) as exc:
        await _call(wire, _mask_defaults(), payload=_ok_payload(**meta_over))
    assert exc.value.reason_code == reason_code
    assert wire.registry.stats["staged"] == staged_before  # 坏轮不暂存


async def test_abort_with_zero_output_exempted(wire):
    payload = _ok_payload(
        finish_reason={"type": "abort"},
        output_token_logprobs=[],
        output_token_sampling_mask=None,
        output_token_sampling_logprobs=None,
    )
    record = await _call(wire, _mask_defaults(), payload=payload)
    assert record.output_ids == [] and record.output_log_probs == []
    assert record.finish_reason == "abort"
    _pop_staged(wire)  # 空轮照常暂存（abort 事实也要落账）
