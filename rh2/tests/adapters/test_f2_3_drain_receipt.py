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


async def test_formal_chain_without_snapshot_source_fails_closed():
    """真实执行链路（批 1 复核测试问题修正）：缺注入跑到 drain 点必须
    fail-closed 收口（abort + 归因），不产 receipt、不评分。"""

    chain = _formal_chain()
    chain.orchestrator._drain_snapshot_source = None  # 拔掉注入
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    audit = chain.orchestrator.audits[0]
    assert audit.session_drain_receipt is None
    assert chain.grading.calls == []  # 不评分
    assert audit.outcome_v2["reason_code"] == "drain_snapshot_source_missing"
    assert any("drain_snapshot_source_missing" in f.detail
               for f in audit.failure_records)


async def test_incomplete_snapshot_fails_closed():
    """严格读数：关键键缺失 ≠ 干净——fail-closed（批 1 复核 P1-2）。"""

    chain = _formal_chain()

    def _broken(sid):
        return {"pending_turns": 0}  # 缺 poison_clean 等关键键

    chain.orchestrator._drain_snapshot_source = _broken
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    audit = chain.orchestrator.audits[0]
    assert audit.session_drain_receipt is None
    assert audit.outcome_v2["reason_code"] == "drain_snapshot_incomplete"


def test_finalization_receipt_identity_cross_check():
    """内嵌 drain receipt 与 finalization receipt 的身份/引用互检。"""

    from datetime import datetime, timezone

    from repoharness2.contracts.finalization import FinalizationReceiptV1

    dr = SessionDrainReceiptV1(
        receipt_id="drain_e_p1", session_id="s-e", trajectory_id="t",
        task_id="k", physical_attempt_id="e#p1-x", revoke_enforced=True,
        pending_turns_after_drain=0, unfinalized_drafts_after_drain=0,
        poison_clean=True, capture_record_count=1,
        drained_at_utc=datetime.now(timezone.utc),
    )
    common = dict(
        receipt_id="rcpt_e_p1", task_id="k", trajectory_id="t",
        session_id="s-e", physical_attempt_id="e#p1-x",
        attempt_disposition="delivery_prepared",
        started_epoch_seconds=1.0,
        finalized_at_utc=datetime.now(timezone.utc),
    )
    ok = FinalizationReceiptV1(**common, drain_receipt=dr,
                               drain_receipt_ref=dr.receipt_id)
    assert ok.drain_receipt_ref == "drain_e_p1"
    with pytest.raises(ValueError, match="receipt_id"):  # ref 与内嵌不符
        FinalizationReceiptV1(**common, drain_receipt=dr,
                              drain_receipt_ref="drain_other")
    with pytest.raises(ValueError, match="悬空"):  # ref 在场但内嵌缺失
        FinalizationReceiptV1(**common, drain_receipt=None,
                              drain_receipt_ref="drain_e_p1")
    with pytest.raises(ValueError, match="trajectory_id"):  # 身份分家
        FinalizationReceiptV1(**{**common, "trajectory_id": "other"},
                              drain_receipt=dr, drain_receipt_ref=dr.receipt_id)


async def test_s1_compat_no_drain_receipt():
    chain = build_dense_chain()  # s1 默认
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert chain.orchestrator.audits[0].session_drain_receipt is None


# ------------------------------------------- 批 1 复核二轮（P1-1/2）
async def test_snapshot_missing_paid_fails_closed():
    """快照缺 physical_attempt_id → fail-closed（不回填 audit 身份洗白）。"""

    chain = _formal_chain()
    base = dict(pending_turns=0, unfinalized_drafts=0, poison_clean=True,
                revoke_enforced=True, late_requests_rejected_after_revoke=0,
                turn_seq_high_water=2, weight_versions_seen=["5"])

    chain.orchestrator._drain_snapshot_source = lambda sid: dict(base)  # 缺 paid
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    audit = chain.orchestrator.audits[0]
    assert audit.session_drain_receipt is None
    assert audit.outcome_v2["reason_code"] == "drain_snapshot_incomplete"


async def test_snapshot_wrong_paid_fails_closed():
    """快照身份 ≠ audit 身份 → 两份事实分家，fail-closed。"""

    chain = _formal_chain()

    def _wrong(sid):
        return dict(pending_turns=0, unfinalized_drafts=0, poison_clean=True,
                    revoke_enforced=True, late_requests_rejected_after_revoke=0,
                    turn_seq_high_water=2, weight_versions_seen=["5"],
                    physical_attempt_id="exec_other#p9-zzzz")

    chain.orchestrator._drain_snapshot_source = _wrong
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    audit = chain.orchestrator.audits[0]
    assert audit.session_drain_receipt is None
    assert audit.outcome_v2["reason_code"] == "drain_snapshot_attempt_mismatch"


async def test_snapshot_wrong_types_fail_closed():
    """codex 注入原样反测：字符串 bool/浮点计数/字符串 list 不再被
    bool()/int()/list() 洗成干净事实。"""

    chain = _formal_chain()

    def _coerced(sid):
        return {
            "revoke_enforced": "false",
            "poison_clean": "false",
            "pending_turns": 0.9,
            "unfinalized_drafts": 0.2,
            "late_requests_rejected_after_revoke": 0,
            "turn_seq_high_water": 2,
            "weight_versions_seen": "5",
            "physical_attempt_id": sid.removeprefix("s-"),
        }

    chain.orchestrator._drain_snapshot_source = _coerced
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    audit = chain.orchestrator.audits[0]
    assert audit.session_drain_receipt is None
    assert audit.outcome_v2["reason_code"] == "drain_snapshot_invalid_type"


def test_fa_success_receipt_requires_drain_proof():
    """复核二轮 P1-2：paid 在场 + delivery_prepared 而无 drain receipt =
    无排空证据的成功，构造即拒；aborted/无 paid 不受影响。"""

    from datetime import datetime, timezone

    from repoharness2.contracts.finalization import FinalizationReceiptV1

    common = dict(
        receipt_id="rcpt_x", task_id="k", trajectory_id="t",
        started_epoch_seconds=1.0, finalized_at_utc=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="drain_receipt"):
        FinalizationReceiptV1(**common, physical_attempt_id="e#p1-x",
                              attempt_disposition="delivery_prepared")
    FinalizationReceiptV1(**common, physical_attempt_id="e#p1-x",
                          attempt_disposition="aborted")  # drain 前终止合法
    FinalizationReceiptV1(**common, physical_attempt_id=None,
                          attempt_disposition="delivery_prepared")  # S1 无 fa 身份
