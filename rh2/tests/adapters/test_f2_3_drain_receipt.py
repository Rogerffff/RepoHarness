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
    assert dr.physical_attempt_id == audit.physical_attempt_id or dr.physical_attempt_id
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
        task_id="k", revoke_enforced=True, capture_record_count=1,
        drained_at_utc=datetime.now(timezone.utc),
    )
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


async def test_formal_chain_without_snapshot_source_fails_closed():
    from test_slime_generate import (
        TASK_ID_DENSE,
        FakeFinalizationStore,
        GradingSubmitStub,
        make_task,
    )

    from repoharness2.adapters.slime.generate import RolloutOrchestrator

    orch = RolloutOrchestrator(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        task_resolver=make_task(TASK_ID_DENSE),
        adapter_factory=lambda hook, defaults: None,
        harness_driver=object(),
        grading_submit=GradingSubmitStub(),
        runtime_quiescence_barrier=_Barrier(),
        finalization_store=FakeFinalizationStore(),
        drain_snapshot_source=None,  # 缺注入
    )
    assert orch._drain_snapshot_source is None  # 构造允许，执行期 fail-closed


async def test_s1_compat_no_drain_receipt():
    chain = build_dense_chain()  # s1 默认
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert chain.orchestrator.audits[0].session_drain_receipt is None
