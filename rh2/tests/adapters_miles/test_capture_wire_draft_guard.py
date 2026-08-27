"""F5（delivered draft 泄漏）ownership guard 测试——finding §7.2 验收面。

驱动真实 `rh2_call_sglang_generate` + **真实 ModelCallProxy**（fake aiohttp
短路到内存 fake 引擎；协调器为恒 ACTIVE 替身）。被测不变量：proxy.call 成功
（delivered draft 已挂 `_pending_drafts`）到 registry.stage 接管之间，任何
解析异常（含 mask 解析失败）或并发 unregister 都必须 poison + abandon 该
draft；stage 接管后不得 double-abandon。

验收断言（逐条对照 finding §7.2）：

- pending turn = 0（坏轮不暂存）；
- `unfinalized_deliveries` = 0（draft 不再永久悬挂）；
- non-delivered/abandoned 原因有账（attempts ledger + abandon evidence）；
- unregister 幂等（不 double-abandon、不再计账）；
- 正常响应仍只 finalize 一次（重复 finalize/abandon 拒绝）。

两 base 通用（guard 全在 rh2 侧,不依赖 miles base 特征字段），不打
integration_base 标记——lane A/B 都真实执行。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

NOW = datetime(2026, 8, 27, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# fake HTTP 层（与 test_capture_wire_sampling_mask 同款短路）
# ---------------------------------------------------------------------------


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
        self.on_request = None  # 并发 unregister 注入点（请求在飞时触发）


class _FakeClientSession:
    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self._engine.requests.append({"url": url, "payload": json, "headers": headers})
        if self._engine.on_request is not None:
            self._engine.on_request()
        return _PostCM(_FakeResponse(self._engine.response_payload))


class _FakeAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self._engine = engine

    def ClientTimeout(self, **_kw):  # noqa: N802 - 镜像 aiohttp API 名
        return None

    def ClientSession(self, **_kw):  # noqa: N802
        return _FakeClientSession(self._engine)


class _ActiveCoordinator:
    """恒 ACTIVE 窗口（本文件不测更新窗口路径，proxy 只需能通过发前检查）。"""

    def __init__(self):
        from repoharness2.contracts.fa_runtime import TrainingRuntimeWindow

        self._window = TrainingRuntimeWindow(
            update_epoch=1,
            phase="ACTIVE",
            old_version="6",
            target_version="7",
            active_version="7",
            window_started_at=NOW,
            window_completed_at=NOW + timedelta(seconds=1),
            fencing_token="fence_1",
        )

    def current_window(self):
        return self._window


# ---------------------------------------------------------------------------
# fixtures：module 级 wire 安装（单代 registry）+ 每测试独立 sid/proxy
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def wire(_vendor_slime_world):
    from slime.agent.adapters import common as slime_common

    from repoharness2.adapters.slime import capture_wire as cw

    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)

    engine = _FakeEngine()
    saved_aiohttp = cw.aiohttp
    cw.aiohttp = _FakeAiohttp(engine)
    try:
        yield SimpleNamespace(registry=registry, engine=engine, slime_common=slime_common, cw=cw)
    finally:
        cw.aiohttp = saved_aiohttp


_SID_SEQ = iter(range(10_000))


@pytest.fixture
def sess(wire):
    """每测试独立会话 + **独立真实 ModelCallProxy**（poison/账本互不串扰）。"""

    from repoharness2.adapters.slime.async_worker import ModelCallProxy
    from repoharness2.adapters.slime.generate import GenerationCaptureHook

    async def _no_sleep(_):
        return None

    sid = f"sid-draft-guard-{next(_SID_SEQ)}"
    wire.registry.register(
        sid,
        GenerationCaptureHook(
            trajectory_id=f"traj_{sid}",
            model_name="m",
            backend_name="sglang",
            backend_version="test",
            renderer_cls_name="r",
            tokenizer_name="tok",
            template_hash="sha256:" + "0" * 64,
        ),
    )
    proxy = ModelCallProxy(_ActiveCoordinator(), sleeper=_no_sleep)
    wire.registry.model_call_proxy = proxy
    wire.engine.on_request = None
    yield SimpleNamespace(sid=sid, proxy=proxy)
    wire.registry.model_call_proxy = None
    wire.registry.unregister(sid)


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
        "weight_version": "7",
        "finish_reason": {"type": "stop"},
        "output_token_logprobs": [[-1.2, 7], [-0.9, 3]],
        "output_token_sampling_mask": [[5, 7, 9], [3, 4]],
        "output_token_sampling_logprobs": [-0.2, -0.4],
    }
    meta.update(meta_over)
    meta = {k: v for k, v in meta.items() if v is not None}
    return {"text": "ok", "meta_info": meta}


async def _call(wire, sid, defaults, payload):
    wire.engine.response_payload = payload
    session = wire.slime_common.Session(sampling_defaults=dict(defaults), max_context_tokens=0)
    adapter = SimpleNamespace(
        logger=logging.getLogger("test_capture_wire_draft_guard"),
        max_token_keys=("max_tokens",),
        stop_keys=("stop",),
        sglang_url="http://fake-engine:1",
    )
    return await wire.slime_common.call_sglang_generate(
        [101, 102, 103], session, {}, adapter=adapter, session_id=sid
    )


def _assert_draft_closed(wire, sess, *, abandon_reason_contains: str):
    """finding §7.2 的共同验收：pending=0、unfinalized=0、原因有账。"""

    registry, proxy, sid = wire.registry, sess.proxy, sess.sid
    # pending turn = 0（坏轮从未进 registry.pending）
    assert len(registry.pending.get(sid) or {}) == 0
    # unfinalized_deliveries = 0（draft 已关账,不再永久悬挂）
    assert proxy.unfinalized_deliveries == frozenset()
    # 账本终态：恰好一条 non_delivered_failed 的 abandoned attempt
    abandoned = [
        a for a in proxy.attempts_ledger if a.model_call_attempt_id.endswith("_abandoned")
    ]
    assert len(abandoned) == 1
    assert abandoned[0].delivery_status == "non_delivered_failed"
    assert abandoned[0].evidence_refs  # abandon 原因已留痕
    # abandon evidence 的原因文本可解析（digest 预览里带异常类型；无外部
    # sink 时引用形如 "audit:{attempt_id}_abandon"，内存键为 attempt_id 部分）
    ref = abandoned[0].evidence_refs[0]
    assert ref.startswith("audit:") and ref.endswith("_abandon")
    preview = proxy.audit_artifacts[ref.removeprefix("audit:")]["preview"]
    assert abandon_reason_contains in preview
    # poison：该会话已 fail-closed
    assert registry.poison.is_poisoned(sid)


def _assert_unregister_idempotent(wire, sess):
    """unregister 幂等：不 double-abandon、不再计账。"""

    registry = wire.registry
    dropped_before = registry.stats["dropped_uncommitted"]
    failures_before = registry.stats.get("abandon_evidence_failures", 0)
    registry.unregister(sess.sid)
    registry.unregister(sess.sid)  # 二次调用 = no-op
    assert registry.stats["dropped_uncommitted"] == dropped_before
    assert registry.stats.get("abandon_evidence_failures", 0) == failures_before
    assert sess.proxy.unfinalized_deliveries == frozenset()


# ---------------------------------------------------------------------------
# 1：mask 缺失 / malformed —— 解析异常路径
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("meta_over", "reason_code"),
    [
        # 引擎根本没返回 mask（missing）
        (
            {"output_token_sampling_mask": None, "output_token_sampling_logprobs": None},
            "sampling_mask_missing_in_response",
        ),
        # mask 行数与输出 token 数不齐（malformed）
        ({"output_token_sampling_mask": [[5, 7]]}, "sampling_mask_length_mismatch"),
    ],
)
async def test_mask_failure_abandons_draft(wire, sess, meta_over, reason_code):
    from repoharness2.adapters.miles.sampling_mask_assembly import SamplingMaskAssemblyError

    with pytest.raises(SamplingMaskAssemblyError) as exc:
        await _call(wire, sess.sid, _mask_defaults(), _ok_payload(**meta_over))
    assert exc.value.reason_code == reason_code

    _assert_draft_closed(
        wire, sess, abandon_reason_contains="pre_stage_failure:SamplingMaskAssemblyError"
    )
    _assert_unregister_idempotent(wire, sess)


# ---------------------------------------------------------------------------
# 2：非 mask 的解析异常（guard 是统一的,不只护 mask 分支）
# ---------------------------------------------------------------------------


async def test_malformed_logprob_pairs_abandon_draft(wire, sess):
    payload = _ok_payload(output_token_logprobs=[7, 3])  # 裸 int,不是 [logprob, id] 对
    with pytest.raises(TypeError):
        await _call(wire, sess.sid, _mask_defaults(return_sampling_mask=None), payload)

    _assert_draft_closed(wire, sess, abandon_reason_contains="pre_stage_failure:TypeError")
    _assert_unregister_idempotent(wire, sess)


# ---------------------------------------------------------------------------
# 3：并发 unregister —— proxy 交付后、stage 接管前会话被摘除
# ---------------------------------------------------------------------------


async def test_concurrent_unregister_abandons_draft(wire, sess):
    from repoharness2.adapters.slime.capture_wire import CaptureWireOwnershipError

    # 请求在飞（proxy.call 内部 send）时 unregister——stage 时会话已不在，
    # unregister 的 leftover 扫尾看不到该 draft（从未 stage），只能靠 guard。
    wire.engine.on_request = lambda: wire.registry.unregister(sess.sid)

    with pytest.raises(CaptureWireOwnershipError):
        await _call(wire, sess.sid, _mask_defaults(), _ok_payload())

    _assert_draft_closed(
        wire, sess, abandon_reason_contains="pre_stage_failure:CaptureWireOwnershipError"
    )
    _assert_unregister_idempotent(wire, sess)


# ---------------------------------------------------------------------------
# 4：正常响应回归 —— 只 finalize 一次,guard 不介入
# ---------------------------------------------------------------------------


async def test_normal_response_finalizes_exactly_once(wire, sess):
    record = await _call(wire, sess.sid, _mask_defaults(), _ok_payload())
    assert record.output_ids == [7, 3]

    registry, proxy = wire.registry, sess.proxy
    # stage 已接管：draft 仍未 finalize（finalize 属于 commit 时刻）,不被 guard 关闭
    assert len(proxy.unfinalized_deliveries) == 1
    turn = registry.single_pending_turn(sess.sid)
    assert not registry.poison.is_poisoned(sess.sid)

    capture_ref = registry.commit(sess.sid)
    assert capture_ref  # 真实 GenerationCaptureRecord.record_id

    assert proxy.unfinalized_deliveries == frozenset()
    delivered = [a for a in proxy.attempts_ledger if a.delivery_status == "delivered"]
    assert len(delivered) == 1
    assert delivered[0].capture_record_ref == capture_ref

    # 只 finalize 一次：重复 finalize / 事后 abandon 都拒绝（幂等违规显式抛）
    with pytest.raises(ValueError):
        turn.proxy_result.finalize_delivered(capture_ref)
    with pytest.raises(ValueError):
        turn.proxy_result.abandon_delivered("late_abandon_must_fail")
    delivered_after = [a for a in proxy.attempts_ledger if a.delivery_status == "delivered"]
    assert len(delivered_after) == 1
    assert not registry.poison.is_poisoned(sess.sid)
