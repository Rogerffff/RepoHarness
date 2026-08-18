"""F2-3 批 1 验收：typed session-plane drain receipt。

- 正式链 e2e：receipt 在 drain+边界断言后签发，内嵌 finalization receipt
  （ref 一致），屏障证据链带回链；
- 契约第二道锁：脏账目（pending/draft 残留、poison 不清白）构造即拒；
- registry 账目：guard 撤销后 403 计数进 drain_snapshot；
- 正式链缺注入 fail-closed；s1_compat 零变化。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
)

from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402
from repoharness2.contracts.finalization import SessionDrainReceiptV1  # noqa: E402


class _FrozenWs:
    def __init__(self, underlying):
        self._u = underlying

    async def run_bash(self, script):
        return await self._u.run_bash(script)


class _Barrier:
    async def establish(self, *, workspace, audit):
        return QuiescenceConfirmed(
            frozen_grading_workspace=_FrozenWs(workspace),
            snapshot_ref="sha256:abc", evidence_refs=("s",))


def _formal_chain(**kwargs):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns, **kwargs)
    _stamp_fa_identity(chain.base_sample)
    return chain


async def test_drain_receipt_issued_embedded_and_referenced():
    chain = _formal_chain()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    dr = audit.session_drain_receipt
    assert dr is not None
    assert dr.session_id == audit.session_id
    assert dr.physical_attempt_id == audit.physical_attempt_id  # 严格相等
    assert dr.revoke_enforced is True
    assert dr.pending_turns_after_drain == 0
    assert dr.unfinalized_drafts_after_drain == 0
    assert dr.poison_clean is True
    assert dr.capture_record_count > 0  # A4：冻结时刻捕获事实非空
    assert dr.weight_versions_seen == ["5"]
    # finalization receipt 内嵌 + ref 一致
    fin = chain.finalization.receipts[0]
    assert fin.drain_receipt == dr
    assert fin.drain_receipt_ref == dr.receipt_id
    # 屏障证据回链（Outcome evidence_refs）
    assert f"drain_receipt:{dr.receipt_id}" in audit.outcome_v2["evidence_refs"]
    # 时序：receipt 在会话面排空之后、屏障确认之前签发
    steps = [e.step for e in audit.timeline]
    assert steps.index("session_plane_drained") < steps.index(
        "session_drain_receipt_issued"
    )


def test_dirty_drain_receipt_construction_rejected():
    """第二道锁：脏账目不许出 receipt（流程本该在边界断言先炸）。"""

    from datetime import datetime, timezone

    common = dict(
        receipt_id="drain_x", session_id="s-x", trajectory_id="t",
        task_id="k", physical_attempt_id="e#p1-x", revoke_enforced=True,
        capture_record_count=1,
        drained_at_utc=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="revoke"):  # 批1复核：撤销未执行即拒
        SessionDrainReceiptV1(**{**common, "revoke_enforced": False},
                              pending_turns_after_drain=0,
                              unfinalized_drafts_after_drain=0, poison_clean=True)
    with pytest.raises(ValueError):  # 负计数拒绝（ge=0）
        SessionDrainReceiptV1(**common, pending_turns_after_drain=-1,
                              unfinalized_drafts_after_drain=0, poison_clean=True)
    with pytest.raises(ValueError, match="pending"):
        SessionDrainReceiptV1(**common, pending_turns_after_drain=1,
                              unfinalized_drafts_after_drain=0, poison_clean=True)
    with pytest.raises(ValueError, match="draft"):
        SessionDrainReceiptV1(**common, pending_turns_after_drain=0,
                              unfinalized_drafts_after_drain=2, poison_clean=True)
    with pytest.raises(ValueError, match="poison"):
        SessionDrainReceiptV1(**common, pending_turns_after_drain=0,
                              unfinalized_drafts_after_drain=0, poison_clean=False)


def test_registry_counts_late_requests_after_revoke():
    """guard 撤销分支计数 → drain_snapshot 暴露（撤销真实生效证据）。"""

    from repoharness2.adapters.slime.capture_wire import CaptureRegistry

    registry = CaptureRegistry()

    class _Hook:
        records: list = []

    registry.register("s-late", _Hook(), physical_attempt_id="exec_1#p1-aaaa")
    registry.revoke("s-late")
    registry.note_revoked_rejection("s-late")
    registry.note_revoked_rejection("s-late")
    snap = registry.drain_snapshot("s-late")
    assert snap["revoke_enforced"] is True
    assert snap["late_requests_rejected_after_revoke"] == 2
    assert snap["pending_turns"] == 0
    assert snap["poison_clean"] is True
    assert snap["physical_attempt_id"] == "exec_1#p1-aaaa"
    registry.unregister("s-late")
    assert registry.revoked_rejections.get("s-late") is None  # 清账


async def test_guard_rejects_and_counts_revoked_request(aiohttp_client=None):
    """guard middleware 撤销分支端到端：403 + x-should-retry:false + 计数。"""

    aiohttp_web = pytest.importorskip("aiohttp.web")
    from aiohttp.test_utils import TestClient, TestServer

    from repoharness2.adapters.slime.capture_wire import (
        CaptureRegistry,
        build_session_guard_middleware,
    )

    registry = CaptureRegistry()

    class _Hook:
        records: list = []

    registry.register("s-guard", _Hook())
    registry.revoke("s-guard")

    async def ok(request):
        return aiohttp_web.json_response({"ok": True})

    app = aiohttp_web.Application(middlewares=[build_session_guard_middleware(registry)])
    app.router.add_post("/v1/messages", ok)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        resp = await client.post(
            "/v1/messages", headers={"Authorization": "Bearer s-guard"}, json={}
        )
        assert resp.status == 403
        body = await resp.json()
        assert body["error"]["type"] == "rh2_session_revoked"
        assert resp.headers["x-should-retry"] == "false"
    finally:
        await client.close()
    assert registry.drain_snapshot("s-guard")[
        "late_requests_rejected_after_revoke"
    ] == 1


async def test_missing_drain_owner_is_fatal_run_halt():
    """批 2a：owner 缺注入 = 部署级契约损坏 → Fatal（不再 abort 缺员）。"""

    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )

    chain = _formal_chain()
    chain.orchestrator._session_drain_owner = None
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="session_drain_owner_missing"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert chain.orchestrator.audits[0].session_drain_receipt is None


async def test_drain_owner_exception_and_bad_type_are_fatal():
    """owner 抛异常 / 返回非 typed 结果 → Fatal（内部事实源损坏）。"""

    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )

    chain = _formal_chain()

    async def _raiser(sid):
        raise OSError("owner exploded")

    chain.orchestrator._session_drain_owner = _raiser
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="session_drain_owner_failed"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))

    chain2 = _formal_chain()

    async def _dict_owner(sid):
        return {"pending_turns": 0}  # dict 时代形状：契约违约

    chain2.orchestrator._session_drain_owner = _dict_owner
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="session_drain_owner_contract_violation"):
        await chain2.orchestrator.generate(
            _Args(), chain2.base_sample, dict(SAMPLING_PARAMS))


async def test_drain_owner_paid_mismatch_is_fatal():
    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    chain = _formal_chain()

    async def _wrong(sid):
        return SessionPlaneDrainResult(
            physical_attempt_id="exec_other#p9-zzzz", revoke_enforced=True,
            inflight_at_drain_start=0, inflight_zero_confirmed=True,
            pending_turns=0, unfinalized_drafts=0, poison_clean=True,
            late_requests_rejected_after_revoke=0, turn_seq_high_water=1,
            weight_versions_seen=["5"], drain_owner="fake")

    chain.orchestrator._session_drain_owner = _wrong
    with pytest.raises(FatalExecutionInfrastructureError,
                       match="session_drain_attempt_mismatch"):
        await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))


async def test_dirty_drain_result_is_member_level_failure():
    """类型正确但事实不干净（inflight 未归零）→ 单 execution 收口
    （abort 缺员，不 run-halt、不冒充干净）。"""

    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    chain = _formal_chain()

    async def _dirty(sid):
        return SessionPlaneDrainResult(
            physical_attempt_id=sid.removeprefix("s-"), revoke_enforced=True,
            inflight_at_drain_start=2, inflight_zero_confirmed=False,
            pending_turns=0, unfinalized_drafts=0, poison_clean=True,
            late_requests_rejected_after_revoke=0, turn_seq_high_water=1,
            weight_versions_seen=["5"], drain_owner="fake")

    chain.orchestrator._session_drain_owner = _dirty
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    audit = chain.orchestrator.audits[0]
    assert audit.session_drain_receipt is None
    assert audit.outcome_v2["reason_code"] == "session_plane_drain_unclean"


async def test_real_adapter_loop_interleaving_no_request_after_drain():
    """批 2 核心证明（真双线程）：adapter loop 上慢请求在飞时 drain owner
    等 inflight 归零才返回；drain 返回后新请求 403、不触达内层 handler
    （SGLang 替身零命中）。"""

    import asyncio
    import threading

    import aiohttp
    from aiohttp import web as aiohttp_web
    from aiohttp.test_utils import TestServer

    from repoharness2.adapters.slime.capture_wire import (
        CaptureRegistry,
        build_session_guard_middleware,
        make_threadsafe_session_drain_owner,
    )

    registry = CaptureRegistry()

    class _Hook:
        records: list = []

    registry.register("s-ix", _Hook(), physical_attempt_id="exec_ix#p1-aaaa")
    reached_after_drain = []
    in_handler = asyncio.Event()  # 在 adapter loop 上创建/等待

    loop_holder: dict = {}
    server_ready = threading.Event()
    drained_flag = threading.Event()

    async def handler(request):
        in_handler.set()
        await asyncio.sleep(0.3)  # 慢请求：drain 必须等它
        if drained_flag.is_set():
            reached_after_drain.append("late-inner")  # 不该发生（在飞的允许完成）
        return aiohttp_web.json_response({"ok": True})

    def adapter_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop

        async def _serve():
            app = aiohttp_web.Application(
                middlewares=[build_session_guard_middleware(registry)])
            app.router.add_post("/v1/messages", handler)
            server = TestServer(app)
            await server.start_server()
            loop_holder["port"] = server.port
            server_ready.set()
            await asyncio.sleep(30)  # 挂住直到测试结束取消

        try:
            loop.run_until_complete(_serve())
        except RuntimeError:
            pass

    t = threading.Thread(target=adapter_thread, daemon=True)
    t.start()
    assert server_ready.wait(5)
    port = loop_holder["port"]
    owner = make_threadsafe_session_drain_owner(registry, loop_holder["loop"])

    async with aiohttp.ClientSession() as client:
        slow = asyncio.create_task(client.post(
            f"http://127.0.0.1:{port}/v1/messages",
            headers={"Authorization": "Bearer s-ix"}, json={}))
        # 等慢请求真正进入 handler（inflight >= 1）
        for _ in range(100):
            if registry._inflight.get("s-ix"):
                break
            await asyncio.sleep(0.01)
        assert registry._inflight.get("s-ix") == 1
        result = await owner("s-ix")  # 必须等 inflight 归零
        drained_flag.set()
        assert result.inflight_at_drain_start == 1
        assert result.inflight_zero_confirmed is True
        assert result.pending_turns == 0
        assert registry._inflight.get("s-ix") is None  # 真归零
        resp_slow = await slow
        assert resp_slow.status == 200  # 在飞请求被允许完成（等待而非砍杀）
        late = await client.post(
            f"http://127.0.0.1:{port}/v1/messages",
            headers={"Authorization": "Bearer s-ix"}, json={})
        assert late.status == 403  # drain 后新请求拒之门外
        body = await late.json()
        assert body["error"]["type"] == "rh2_session_revoked"
    assert reached_after_drain == []  # drain 返回后无新请求触达内层
    assert registry.drain_snapshot("s-ix")[
        "late_requests_rejected_after_revoke"] == 1
    loop_holder["loop"].call_soon_threadsafe(
        lambda: [t.cancel() for t in asyncio.all_tasks(loop_holder["loop"])])


async def test_contract_violation_reaches_worker_halted():
    """codex 批 2 首验收 e2e：owner 契约违约 → Fatal → WorkerHalted
    （绝不伪装成 dropped group/batch_starved）。"""

    import asyncio

    from repoharness2.adapters.slime.async_worker import (
        BoundedDeliveryQueue,
        ContinuousExecutionWorker,
        ExecutionTaskSpec,
        WorkerHalted,
    )

    chain = _formal_chain()

    async def _raiser(sid):
        raise OSError("owner exploded")

    chain.orchestrator._session_drain_owner = _raiser
    specs = [ExecutionTaskSpec(
        rollout_execution_id="exec_drain_1", prompt_group_id="g", member_slot=0)]
    queue = list(specs)
    failures: list = []

    async def execute(spec):
        return await chain.orchestrator.generate(
            _Args(), chain.base_sample, dict(SAMPLING_PARAMS))

    worker = ContinuousExecutionWorker(
        task_source=lambda: queue.pop(0) if queue else None,
        execute_fn=execute,
        delivery_queue=BoundedDeliveryQueue(maxsize=8),
        failure_sink=lambda spec, exc: failures.append(type(exc).__name__),
        concurrency=1,
    )
    stop = asyncio.Event()
    with pytest.raises(WorkerHalted, match="session_drain_owner_failed"):
        await asyncio.wait_for(worker.run(stop), timeout=10)
