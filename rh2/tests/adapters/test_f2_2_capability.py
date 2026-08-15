"""F2-2 验收：每 physical attempt 的 session capability + Runtime quiescence
（会话面）+ Outcome v2 producer 接线。

钉死的验收（05 计划 F2-2 节，codex F2-1a 终核提出）：真实 slime 在
finish/drop 后把 sid 永久留在 `closed` 集合且 turn counter 不清——必须
显式证明：① 稳定 SID 复用会收 503（问题存在性）；② 旧 capability 被拒；
③ 新 attempt 用新 capability，不受旧 closed 状态与 turn counter 影响；
④ 新请求正常通过。

证明分两层（本地 venv 无 torch，slime 不可 import——FA-0 既有模式）：
源码级断言钉住 reference/slime 的 closed/turn-count 语义；忠实本地复刻
（_SlimeSessionReplica，逐行对应被钉住的语义）上跑行为验收。
"""

from __future__ import annotations

import json
import re
from pathlib import Path


from repoharness2.adapters.slime.capture_wire import CaptureRegistry
from repoharness2.adapters.slime.outcome_producer import (
    FAILURE_CODE_TERMINATION_MAP,
    STAGE_FALLBACK_TERMINATION_MAP,
    build_outcome_v2,
    derive_completion,
)
from repoharness2.adapters.slime.session_capability import (
    capability_fingerprint,
    mint_session_capability,
)
from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_INFRA,
    TERMINATION_KINDS_NORMAL,
)

_SLIME_COMMON = (
    Path(__file__).resolve().parents[3]
    / "reference" / "slime" / "slime" / "agent" / "adapters" / "common.py"
)


class _Hook:
    def on_generate_response(self, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# capability 铸造
# ---------------------------------------------------------------------------

def test_capability_minting_shape_and_uniqueness():
    """128-bit 随机、cap- 前缀；同 paid 两次铸造必不同（replay = 新凭证）；
    fingerprint 确定、可落盘、不等于 token。"""

    a = mint_session_capability("exec#p1-x")
    b = mint_session_capability("exec#p1-x")
    assert a.token != b.token  # 每次铸造全新
    assert a.token.startswith("cap-") and len(a.token) == 4 + 32  # 128-bit hex
    assert a.fingerprint.startswith("capfp-") and a.fingerprint != a.token
    assert a.fingerprint == capability_fingerprint(a.token)  # 确定性回链
    assert a.physical_attempt_id == "exec#p1-x"


# ---------------------------------------------------------------------------
# 层 1：slime 源码语义钉住（closed 永久 + turn counter 不清）
# ---------------------------------------------------------------------------

def test_slime_source_closed_set_and_turn_counter_semantics():
    """钉住被复刻的四条语义；slime 升级改动任一条时本测试先红。"""

    src = _SLIME_COMMON.read_text(encoding="utf-8")
    # ① shutdown（finish/drop 的公共路径）把 sid 加进 closed
    assert "self.closed.add(sid)" in src
    # ② open_session 不清 closed（只查 store 重复）
    open_body = src.split("def open_session", 1)[1].split("async def", 1)[0]
    assert "closed" not in open_body, "slime open_session 开始清理 closed——复刻与验收前提失效"
    # ③ 请求路径对 closed 中的 sid 回 503
    assert re.search(r"if sid in self\.closed:.*?\n.*?\n.*?status=503", src)
    # ④ turn counter 只增不清：除初始化外无任何 pop/del/clear
    assert "self._sid_turn_count: dict[str, int] = {}" in src
    body = src.replace("self._sid_turn_count: dict[str, int] = {}", "")
    assert "_sid_turn_count.pop" not in body and "del self._sid_turn_count" not in body
    assert "_sid_turn_count.clear" not in body


class _SlimeSessionReplica:
    """reference/slime BaseAdapter 会话语义的忠实复刻（上面测试逐条钉住）：
    store 去重 / shutdown 永久 closed / 请求先查 closed 再查 turn cap。"""

    def __init__(self, max_turns_per_sid: int | None = None):
        self.store: dict[str, object] = {}
        self.closed: set[str] = set()
        self._sid_turn_count: dict[str, int] = {}
        self.max_turns_per_sid = max_turns_per_sid

    def open_session(self, sid: str) -> None:
        if sid in self.store:
            raise ValueError(f"session_id {sid!r} already exists")
        self.store[sid] = object()

    def request(self, sid: str) -> int:
        """_run_turn 的守卫段：503（closed）/ 429（turn cap）/ 200。"""

        if sid in self.closed:
            return 503
        cap = self.max_turns_per_sid
        if cap is not None:
            prior = self._sid_turn_count.get(sid, 0)
            if prior >= cap:
                return 429
            self._sid_turn_count[sid] = prior + 1
        return 200

    def finish_session(self, sid: str) -> None:
        self.closed.add(sid)  # shutdown_session 语义
        self.store.pop(sid, None)


# ---------------------------------------------------------------------------
# 层 2：钉死验收四条（复刻上跑）
# ---------------------------------------------------------------------------

def test_stable_sid_replay_hits_closed_set_503():
    """① 问题存在性：稳定 SID 复用——第二次 attempt 能 open（store 已 pop）
    但每条请求都 503（closed 永久）。这就是 F2-2 要消灭的故障形态。"""

    slime = _SlimeSessionReplica()
    stable_sid = "rh2-task-0-0"  # S1 时代：task/index 稳定派生
    slime.open_session(stable_sid)
    assert slime.request(stable_sid) == 200
    slime.finish_session(stable_sid)

    slime.open_session(stable_sid)  # replay：open 竟然成功（store 已清）……
    assert slime.request(stable_sid) == 503  # ……但请求全灭（closed 永久）


def test_per_attempt_capability_immune_to_closed_and_turn_state():
    """②③④ 主验收：attempt1 凭证用到 turn cap 上限并 finish；attempt2 新
    凭证 open 畅通、turn 计数从零起、请求正常；旧凭证同时被拒。"""

    slime = _SlimeSessionReplica(max_turns_per_sid=3)
    cap1 = mint_session_capability("exec_R#p1-aaaa")
    slime.open_session(cap1.token)
    assert [slime.request(cap1.token) for _ in range(4)] == [200, 200, 200, 429]
    slime.finish_session(cap1.token)  # attempt1 结束：token1 进 closed，计数=3

    cap2 = mint_session_capability("exec_R#p2-bbbb")  # replay：新铸凭证
    assert cap2.token != cap1.token
    slime.open_session(cap2.token)  # ③ 不受旧 closed 影响
    assert slime.request(cap2.token) == 200  # ④ 新请求正常，turn 计数全新
    assert slime._sid_turn_count[cap2.token] == 1  # 不继承 attempt1 的 3
    assert slime.request(cap1.token) == 503  # ② 旧 capability 被拒


# ---------------------------------------------------------------------------
# rh2 侧：guard 撤销（quiescence 第一步）
# ---------------------------------------------------------------------------

async def test_guard_rejects_revoked_capability():
    """revoke 后 guard 立即 403（reason=session_revoked，x-should-retry:false）；
    hook 仍注册（drain 窗口）；unregister 后 revoked 清理、按 unknown 拒。"""

    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    from repoharness2.adapters.slime.capture_wire import build_session_guard_middleware

    registry = CaptureRegistry()
    cap = mint_session_capability("exec#p1-g")
    registry.register(cap.token, _Hook(), physical_attempt_id="exec#p1-g")

    async def ok(request):
        return web.json_response({"ok": True})

    app = web.Application(middlewares=[build_session_guard_middleware(registry)])
    app.router.add_post("/v1/messages", ok)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        hdr = {"Authorization": f"Bearer {cap.token}"}
        r1 = await client.post("/v1/messages", headers=hdr)
        assert r1.status == 200  # 撤销前正常

        registry.revoke(cap.token)
        r2 = await client.post("/v1/messages", headers=hdr)
        assert r2.status == 403
        assert r2.headers["x-should-retry"] == "false"
        assert (await r2.json())["error"]["type"] == "rh2_session_revoked"
        assert cap.token in registry.hooks  # drain 窗口：账目仍在场

        registry.unregister(cap.token)
        assert not registry.is_revoked(cap.token)  # 会话关闭即失效，集合不涨
        r3 = await client.post("/v1/messages", headers=hdr)
        assert r3.status == 403  # unknown 分支兜底
        assert (await r3.json())["error"]["type"] == "rh2_unknown_or_closed_session"
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# 编排链 e2e：quiescence 顺序 + 凭证卫生 + producer
# ---------------------------------------------------------------------------

def _stamp_fa_identity(sample) -> None:
    sample.metadata = dict(getattr(sample, "metadata", {}) or {})
    sample.metadata.update({
        "rh2_rollout_execution_id": "exec_F22",
        "rh2_prompt_group_id": "pg_F22",
        "rh2_member_slot": 2,
        "rh2_physical_attempt_id": "exec_F22#p1-cafe1234",
        "rh2_physical_attempt_seq": 1,
    })


async def test_e2e_quiescence_order_capability_hygiene_and_outcome():
    """真实编排链（dense fixture）：撤销事件先于静止确认；audit JSON 全文
    不含 capability 秘密（只有指纹）；成功收口产出 present_complete v2；
    交付样本 session_id 已 scrub 回稳定键。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    chain = build_dense_chain()
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    audit = chain.orchestrator.audits[0]

    # quiescence 顺序：revoke（若 adapter 支持）→ …… → 静止确认 → 关账
    names = [e.step for e in audit.timeline]
    assert "quiescence_confirmed" in names
    assert audit.quiescence_confirmed and audit.capture_closed
    adapter = chain.adapter_ref["adapter"]
    # 撤销必须真实发生且先于 drain（finish）与静止确认——mock 记录三者顺序
    assert adapter.revoked == adapter.finished  # 同一 capability token
    assert names.index("session_revoked") < names.index("quiescence_confirmed")

    # 凭证卫生：audit 可序列化面无 cap- 秘密；session_id 是指纹
    assert audit.session_id.startswith("capfp-")
    audit_text = json.dumps(
        {
            "session_id": audit.session_id,
            "timeline": [e.step for e in audit.timeline],
            "outcome_v2": audit.outcome_v2,
        },
        ensure_ascii=False,
    )
    assert "cap-" not in audit_text

    # producer：成功收口 → present_complete + 评分结局 + 完整四层身份
    assert audit.outcome_v2 is not None
    ov2 = audit.outcome_v2
    assert ov2["completion_class"] == "present_complete"
    assert ov2["termination_kind"] == "completed"
    assert ov2["identity"]["physical_attempt_id"] == "exec_F22#p1-cafe1234"
    assert ov2["identity"]["branch_id"] is None
    assert ov2["task_outcome"] in ("resolved", "unresolved")
    assert chain.orchestrator.outcomes[0].member_slot == 2

    # 交付样本 scrub：稳定键，不带凭证
    for s in delivered:
        sid = getattr(s, "session_id", None)
        if sid is not None:
            assert not str(sid).startswith("cap-")


async def test_e2e_failure_path_produces_missing_outcome():
    """异常收口（harness 崩溃）：termination=harness_crash + completion=
    missing（quiescence 未确认）；S1 兼容路径（无身份）不产 v2。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    chain = build_dense_chain(crash=RuntimeError("claude cli exploded"))
    _stamp_fa_identity(chain.base_sample)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    ov2 = chain.orchestrator.audits[0].outcome_v2
    assert ov2 is not None
    assert ov2["completion_class"] == "missing"
    assert ov2["termination_kind"] == "harness_crash"
    assert ov2["failure_category"] == "harness_crash"
    assert ov2["reward_unavailable"] is True

    # S1 兼容：无四层身份 → 不产 v2（宁缺毋伪造）
    chain2 = build_dense_chain(crash=RuntimeError("boom"))
    await chain2.orchestrator.generate(_Args(), chain2.base_sample, dict(SAMPLING_PARAMS))
    assert chain2.orchestrator.audits[0].outcome_v2 is None


# ---------------------------------------------------------------------------
# producer 映射表：全域无矛盾组合（codex F2-1b 二轮非阻塞项的 F2-2 兑现）
# ---------------------------------------------------------------------------

def test_derive_completion_total_and_consistent():
    """13 termination × quiescence × capture 全组合：infra ⇒ missing；
    账目不齐 ⇒ missing；completed+齐 ⇒ present_complete；其余 ⇒ truncated。"""

    from typing import get_args

    from repoharness2.contracts.fa_runtime import TerminationKind

    for tk in get_args(TerminationKind):
        for q in (True, False):
            for c in (True, False):
                got = derive_completion(
                    termination_kind=tk, quiescence_confirmed=q, capture_closed=c
                )
                if tk in TERMINATION_KINDS_INFRA:
                    assert got == "missing"
                elif not (q and c):
                    assert got == "missing"
                elif tk in TERMINATION_KINDS_NORMAL:
                    assert got == "present_complete"
                else:
                    assert got == "present_truncated"


def test_producer_mapping_tables_yield_valid_v2_everywhere():
    """映射表全条目 × 事实组合 → 产物全部过 v2 validator（validator 抛错
    即矛盾组合，测试直接红）——生产路径不可能构造明显矛盾记录。"""

    entries = list(FAILURE_CODE_TERMINATION_MAP.values()) + list(
        STAGE_FALLBACK_TERMINATION_MAP.values()
    )
    built = 0
    for term_kind, fail_cat in entries:
        for q in (True, False):
            for c in (True, False):
                outcome = build_outcome_v2(
                    outcome_id="ov2_t",
                    prompt_group_id="pg",
                    group_index=0,
                    rollout_execution_id="exec_T",
                    physical_attempt_id="exec_T#p1-abcd",
                    physical_attempt_seq=1,
                    member_slot=0,
                    termination_kind=term_kind,
                    quiescence_confirmed=q,
                    capture_closed=c,
                    failure_category=fail_cat,
                    reason_code="mapped_code",
                    failed_component="stage",
                    task_resolved=None,
                )
                assert outcome is not None  # validator 全过 = 无矛盾
                built += 1
                # missing 时归因必属执行事实集合（validator 已强制，这里
                # 断言推导本身没把评分/准入归因带进 missing）
                if outcome.completion_class == "missing":
                    assert outcome.failure_category != "grading_infra_failure"
    assert built == len(entries) * 4


def test_producer_erratum2_grading_failure_keeps_present():
    """勘误 2 e2e 面：评分不可得（task_resolved=None + grading_infra_failure）
    且执行事实完整 → completion 保持 present_complete，reward 不可用。"""

    outcome = build_outcome_v2(
        outcome_id="ov2_g", prompt_group_id="pg", group_index=0,
        rollout_execution_id="exec_G", physical_attempt_id="exec_G#p1-ffff",
        physical_attempt_seq=1, member_slot=0,
        termination_kind="completed", quiescence_confirmed=True, capture_closed=True,
        failure_category="grading_infra_failure", task_resolved=None,
        turn_weight_versions=["7"], intra_execution_version_span=0,
        current_version_at_finalize="7", eligibility_report_id="er_g",
    )
    assert outcome.completion_class == "present_complete"  # 不被倒写
    assert outcome.reward_unavailable and outcome.task_outcome == "unknown"
    assert outcome.failure_category == "grading_infra_failure"


def test_producer_no_identity_returns_none():
    assert build_outcome_v2(
        outcome_id="o", prompt_group_id=None, group_index=0,
        rollout_execution_id="e", physical_attempt_id=None, physical_attempt_seq=None,
        member_slot=None, termination_kind="completed",
        quiescence_confirmed=True, capture_closed=True,
    ) is None
