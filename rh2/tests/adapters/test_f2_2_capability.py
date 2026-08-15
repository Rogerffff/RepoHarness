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

import re
from pathlib import Path

import pytest

from repoharness2.adapters.slime.capture_wire import CaptureRegistry
from repoharness2.adapters.slime.outcome_producer import (
    FAILURE_CODE_TERMINATION_MAP,
    STAGE_FALLBACK_TERMINATION_MAP,
    build_outcome_v2,
    derive_completion,
)
from repoharness2.adapters.slime.session_capability import mint_session_capability
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
    """128-bit 随机、cap- 前缀；同 paid 两次铸造必不同（replay = 新凭证）。"""

    a = mint_session_capability("exec#p1-x")
    b = mint_session_capability("exec#p1-x")
    assert a.token != b.token  # 每次铸造全新
    assert a.token.startswith("cap-") and len(a.token) == 4 + 32  # 128-bit hex
    assert a.physical_attempt_id == "exec#p1-x"
    # fingerprint 机制已删（复核二轮一般 2）：token 不落任何持久面，
    # 无需可落盘的关联指纹——SessionCapability 只剩 token + paid
    assert not hasattr(a, "fingerprint")


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
    internal = "s-exec#p1-g"
    registry.register(
        internal, _Hook(), physical_attempt_id="exec#p1-g", capability_token=cap.token
    )

    async def echo_auth(request):
        # P0-3 核心断言面：handler（= slime）看到的 Authorization 已被
        # 重写为非秘密 internal sid——token 不进入下游
        return web.json_response({"auth": request.headers.get("Authorization")})

    app = web.Application(middlewares=[build_session_guard_middleware(registry)])
    app.router.add_post("/v1/messages", echo_auth)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        hdr = {"Authorization": f"Bearer {cap.token}"}
        r1 = await client.post("/v1/messages", headers=hdr)
        assert r1.status == 200  # 撤销前正常
        assert (await r1.json())["auth"] == f"Bearer {internal}"  # 认证后重写

        # 直接拿 internal sid 当凭证 → 拒绝（internal 不是秘密，不能当钥匙）
        r_fake = await client.post(
            "/v1/messages", headers={"Authorization": f"Bearer {internal}"}
        )
        assert r_fake.status == 403

        registry.revoke(internal)  # 撤销按 internal sid（quiescence 序列）
        r2 = await client.post("/v1/messages", headers=hdr)
        assert r2.status == 403
        assert r2.headers["x-should-retry"] == "false"
        assert (await r2.json())["error"]["type"] == "rh2_session_revoked"
        assert internal in registry.hooks  # drain 窗口：账目仍在场

        registry.unregister(internal)
        assert not registry.is_revoked(internal)  # 会话关闭即失效，集合不涨
        assert registry.resolve_capability(cap.token) is None  # token 映射同清
        r3 = await client.post("/v1/messages", headers=hdr)
        assert r3.status == 403  # unknown 分支兜底
        assert (await r3.json())["error"]["type"] == "rh2_unknown_or_closed_session"
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# 编排链 e2e：quiescence 顺序 + 凭证卫生 + producer
# ---------------------------------------------------------------------------

def _fa_cfg(**over):
    """FA audit-only 探针模式配置（复核四轮：模式显式声明，不再靠 paid 推断）。"""

    from test_slime_generate import dense_config

    return dense_config(execution_mode="fa_audit_only", **over)


def _stamp_fa_identity(sample) -> None:
    sample.metadata = dict(getattr(sample, "metadata", {}) or {})
    sample.metadata.update({
        "rh2_rollout_execution_id": "exec_F22",
        "rh2_prompt_group_id": "pg_F22",
        "rh2_group_index": 5,
        "rh2_member_slot": 2,
        "rh2_physical_attempt_id": "exec_F22#p1-cafe1234",
        "rh2_physical_attempt_seq": 1,
    })


async def test_e2e_formal_path_audit_only_pre_barrier():
    """复核二轮 P0-1/P0-2：完整屏障前，正式路径不评分、不交付——
    abort 形状（collector 拒绝）+ audit-only missing Outcome；持久审计
    全文无 capability 秘密；撤销先于会话面排空。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    audit = chain.orchestrator.audits[0]

    # P0-2：评分从未发生（活动 workspace 不许评）
    assert chain.grading.calls == []
    # P0-1：交付 = abort 形状，collector（_member_ok 语义）拒绝
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))
    from fa_bringup.rollout_entry import _member_ok

    assert all(getattr(x, "remove_sample", False) for x in delivered)
    assert _member_ok(delivered) is False
    assert "formal_chain_audit_only_pre_barrier" in [e.step for e in audit.timeline]

    # 事实拆分（P0-1 一轮）：会话面排空 True；runtime 屏障恒 False
    names = [e.step for e in audit.timeline]
    assert audit.session_plane_drained and audit.runtime_quiescence_confirmed is False
    adapter = chain.adapter_ref["adapter"]
    assert adapter.revoked == adapter.finished  # 同一 internal sid
    assert names.index("session_revoked") < names.index("session_plane_drained")

    # 三层身份：internal sid 非秘密；token 只进 harness
    assert audit.session_id == "s-exec_F22#p1-cafe1234"
    token = chain.driver.calls[0]["session_id"]
    assert token.startswith("cap-") and token != audit.session_id

    # 凭证卫生（P0-3 验收）：完整持久 record 全文扫描无 token
    import tempfile

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    with tempfile.TemporaryDirectory() as td:
        jsonl = Path(td) / "execution_audit.jsonl"
        write_execution_audit_record(None, audit, jsonl)
        record_text = jsonl.read_text(encoding="utf-8")
        assert token not in record_text
        assert "cap-" not in record_text
        assert audit.session_id in record_text

    # audit-only Outcome：missing + 屏障不可用留因；身份完整贯穿（P1-5）
    ov2 = audit.outcome_v2
    assert ov2 is not None
    assert ov2["completion_class"] == "missing"
    assert ov2["reason_code"] == "runtime_barrier_unavailable"
    assert ov2["identity"]["group_index"] == 5
    assert ov2["member_slot"] == 2
    assert len(chain.orchestrator.outcomes) == 1


async def test_e2e_failure_path_produces_missing_outcome():
    """异常收口（harness 崩溃）：termination=harness_crash + completion=
    missing（quiescence 未确认）；S1 兼容路径（无身份）不产 v2。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    chain = build_dense_chain(config=_fa_cfg(), crash=RuntimeError("claude cli exploded"))
    _stamp_fa_identity(chain.base_sample)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    ov2 = chain.orchestrator.audits[0].outcome_v2
    assert ov2 is not None
    assert ov2["completion_class"] == "missing"
    assert ov2["termination_kind"] == "harness_crash"
    assert ov2["failure_category"] == "harness_crash"
    assert ov2["reward_unavailable"] is True

    # s1_compat 模式：完全不产 v2（producer 按模式门控）
    chain2 = build_dense_chain(crash=RuntimeError("boom"))
    await chain2.orchestrator.generate(_Args(), chain2.base_sample, dict(SAMPLING_PARAMS))
    assert chain2.orchestrator.audits[0].outcome_v2 is None


async def test_outcome_terminal_cas_single_write():
    """复核 P0-2：终态 CAS——同一 audit 第二次生产不追加不改写（屏障
    落地恢复交付后，deliver 失败路径靠它保持 Outcome 恒一条）。"""

    from repoharness2.adapters.slime.generate import RolloutAudit, RolloutOrchestrator

    orch = RolloutOrchestrator.__new__(RolloutOrchestrator)  # 只用 producer 面
    orch.outcomes = []
    audit = RolloutAudit(trajectory_id="t", task_id="k")
    audit.physical_attempt_id = "exec_C#p1-abcd0000"
    audit.capture_closed = True
    meta = {
        "rh2_rollout_execution_id": "exec_C", "rh2_prompt_group_id": "pg_C",
        "rh2_group_index": 1, "rh2_member_slot": 0,
        "rh2_physical_attempt_id": "exec_C#p1-abcd0000",
        "rh2_physical_attempt_seq": 1,
    }
    kw = dict(audit=audit, raw_meta=meta, failure_category=None,
              reason_code=None, failed_component=None, task_resolved=None,
              turn_weight_versions=None, current_version_at_finalize=None,
              eligibility_report_id=None)
    orch._produce_outcome_v2(termination_kind="completed", **kw)
    first = audit.outcome_v2
    assert first is not None and len(orch.outcomes) == 1
    # 第二次（如 deliver 失败后的异常收口）尝试改写为 harness_crash → 拒
    orch._produce_outcome_v2(termination_kind="harness_crash", **kw)
    assert audit.outcome_v2 is first  # CAS：未被改写
    assert len(orch.outcomes) == 1


async def test_hard_wall_exit_records_trigger_not_crash():
    """codex F2-2 复核 P1-4：slime exit=-1（时间预算耗尽）→ termination=
    hard_wall_timeout；不走 nonzero 拒绝（不误归 harness_crash），也不
    伪装 completed；completion 由完整性事实推导（屏障未落地 → missing）。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    chain = build_dense_chain(config=_fa_cfg(), harness_exit_code=-1)
    _stamp_fa_identity(chain.base_sample)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.termination_kind_hint == "hard_wall_timeout"
    # 不是 crash：nonzero 拒绝没触发；正式路径屏障前不评分（P0-2——
    # -1 后 setsid 的 CC 进程可能仍在写活动 workspace）
    assert not any(
        f.error_type == "SlimeBindingError" and "nonzero" in f.detail
        for f in audit.failure_records
    )
    assert chain.grading.calls == []
    ov2 = audit.outcome_v2
    assert ov2["termination_kind"] == "hard_wall_timeout"
    assert ov2["completion_class"] == "missing"  # 屏障未落地；处置留 D1b
    assert ov2["reason_code"] == "runtime_barrier_unavailable"


async def test_identity_incomplete_rejected_in_fa_mode():
    """复核四轮：FA 模式（显式声明）身份字段不全 → 结构化拒绝（不产 v2
    不补值不交付）；s1_compat + 局部身份 → 完全不产 v2（模式门控）。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    partial = {
        "rh2_rollout_execution_id": "exec_I",
        "rh2_physical_attempt_id": "exec_I#p1-dead0000",
        "rh2_physical_attempt_seq": 1,
        # 故意缺 rh2_prompt_group_id / rh2_group_index / rh2_member_slot
    }
    chain = build_dense_chain(config=_fa_cfg())
    sample = chain.base_sample
    sample.metadata = dict(getattr(sample, "metadata", {}) or {})
    sample.metadata.update(partial)
    delivered = await chain.orchestrator.generate(_Args(), sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.outcome_v2 is None and chain.orchestrator.outcomes == []
    assert any(f.stage == "identity" for f in audit.failure_records)
    assert all(getattr(x, "remove_sample", False) for x in delivered)

    # s1_compat：同样输入不触发任何 FA 门控，也绝不产 v2
    chain2 = build_dense_chain()
    s2 = chain2.base_sample
    s2.metadata = dict(getattr(s2, "metadata", {}) or {})
    s2.metadata.update(partial)
    await chain2.orchestrator.generate(_Args(), s2, dict(SAMPLING_PARAMS))
    assert chain2.orchestrator.audits[0].outcome_v2 is None
    assert chain2.orchestrator.outcomes == []


async def test_formal_mode_identity_fault_fails_closed_not_open():
    """复核三轮 P0-1：正式模式（显式旗标）+ 身份注入故障（paid=None）
    不得绕过 audit-only 防线——不评分、不交付、abort 形状。修复前的
    fail-open：恰好缺身份反而评分并 finalize。"""

    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        build_dense_chain,
    )

    chain = build_dense_chain(config=_fa_cfg())
    # 不 stamp 任何 FA 身份（模拟身份注入故障）
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS)
    )
    audit = chain.orchestrator.audits[0]
    assert chain.grading.calls == []  # 修复前 = 1（fail-open 实锤位）
    assert audit.finalized is None
    assert all(getattr(x, "remove_sample", False) for x in delivered)
    assert any(
        f.stage == "identity" and "fa_identity_incomplete" in f.detail
        for f in audit.failure_records
    )


def test_fa_formal_startup_gates():
    """复核四轮：fa_formal 组合校验——屏障未注入拒启动；require 旗标
    未开拒启动；P0-1 回归 = 屏障注入后版本契约检查**依然执行**（曾被
    错误缩进进屏障分支而消失）。"""

    from test_slime_generate import _formal_config, build_dense_chain, dense_config

    with pytest.raises(Exception, match="runtime_barrier_capability_missing"):
        build_dense_chain(config=_formal_config(
            policy_version="5", execution_mode="fa_formal"))
    with pytest.raises(Exception, match="fa_formal_requires_real_weight_versions"):
        build_dense_chain(config=dense_config(execution_mode="fa_formal"))

    class _GrantBarrier:
        async def establish(self, *, workspace, audit):
            from repoharness2.adapters.slime.generate import QuiescenceResult

            return QuiescenceResult(confirmed=True)

    from repoharness2.adapters.slime.generate import validate_execution_config

    # P0-1 回归：屏障在场 + 非数值版本 → 版本契约仍然拦截
    with pytest.raises(Exception, match="policy_version_not_numeric"):
        validate_execution_config(
            _formal_config(policy_version="v5", execution_mode="fa_formal"),
            _GrantBarrier(),
        )
    with pytest.raises(Exception, match="context_shrink_rejection_disabled"):
        validate_execution_config(
            _formal_config(policy_version="5", execution_mode="fa_formal",
                           reject_context_shrink=False),
            _GrantBarrier(),
        )


async def test_replay_same_sample_keeps_stable_trajectory():
    """复核三轮 P0-2：同一 Sample 两次 physical attempt——trajectory_id
    恒等于不可变 rh2_rollout_execution_id，不被上一 attempt 的 internal
    sid 污染（修复前 attempt2 trajectory = s-exec_...#p1）。"""

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    chain1 = build_dense_chain()
    s1 = chain1.base_sample
    _stamp_fa_identity(s1)
    s1.metadata["rh2_rollout_execution_id"] = "exec_REPLAY"
    s1.metadata["rh2_physical_attempt_id"] = "exec_REPLAY#p1-a"
    await chain1.orchestrator.generate(_Args(), s1, dict(SAMPLING_PARAMS))
    a1 = chain1.orchestrator.audits[0]

    chain2 = build_dense_chain()
    s1.metadata["rh2_physical_attempt_id"] = "exec_REPLAY#p2-b"
    s1.metadata["rh2_physical_attempt_seq"] = 2
    await chain2.orchestrator.generate(_Args(), s1, dict(SAMPLING_PARAMS))
    a2 = chain2.orchestrator.audits[0]

    assert a1.trajectory_id == a2.trajectory_id == "exec_REPLAY"  # 稳定
    assert a1.session_id != a2.session_id  # 会话身份按 attempt 隔离
    assert a2.session_id == "s-exec_REPLAY#p2-b"


def test_quiescence_failure_reason_codes_bidirectional():
    """复核三轮 P1-1：runtime_quiescence_failure ⟺ 五 reason code 双向
    封闭——任意字符串/None/串门都拒绝。"""

    import pytest as _pytest

    from repoharness2.contracts.fa_runtime import (
        RUNTIME_QUIESCENCE_REASON_CODES,
        ExecutionIdentity,
        RolloutAttemptOutcomeV2,
    )

    def make(fc, rc):
        return RolloutAttemptOutcomeV2(
            outcome_id="o", identity=ExecutionIdentity(
                prompt_group_id="g", group_index=0, rollout_execution_id="e",
                physical_attempt_id="e#p1-x", physical_attempt_seq=1),
            member_slot=0, attempt_number=1, completion_class="missing",
            termination_kind="hard_wall_timeout", failure_category=fc,
            reason_code=rc, recovery_scope="none", task_outcome="unknown",
            reward_unavailable=True)

    for rc in RUNTIME_QUIESCENCE_REASON_CODES:
        make("runtime_quiescence_failure", rc)  # 五码全合法
    with _pytest.raises(ValueError, match="五失败点"):
        make("runtime_quiescence_failure", "totally_unknown_reason")
    with _pytest.raises(ValueError, match="五失败点"):
        make("runtime_quiescence_failure", None)
    with _pytest.raises(ValueError, match="专属"):
        make("capture_incomplete", "active_writer_detected")  # 码不许串门


async def test_audit_only_disposition_in_persisted_record():
    """复核三轮 P1-2：audit-only 收口的持久 disposition =
    audit_only_rejected（不是 unknown_terminal，不污染故障统计口径）。"""

    import json as _json
    import tempfile

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.audit_only is True
    with tempfile.TemporaryDirectory() as td:
        jsonl = Path(td) / "a.jsonl"
        write_execution_audit_record(None, audit, jsonl)
        rec = _json.loads(jsonl.read_text().strip())
    assert rec["disposition"] == "audit_only_rejected"


async def test_fa_formal_with_injected_barrier_end_to_end():
    """复核四轮 P0-3：注入式屏障真实驱动正式链——确认 → 评分交付 +
    present_complete；拒绝 → runtime_quiescence_failure（勘误 3 码）+
    abort 不评分。"""

    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        _formal_config,
        build_dense_chain,
    )

    from repoharness2.adapters.slime.generate import (
        QuiescenceConfirmed,
        QuiescenceRejected,
    )

    class _Barrier:
        def __init__(self, confirmed):
            self.confirmed = confirmed
            self.calls = 0

        frozen = object()  # 冻结副本句柄（评分只许消费它）

        async def establish(self, *, workspace, audit):
            self.calls += 1
            if self.confirmed:
                return QuiescenceConfirmed(
                    frozen_grading_workspace=self.frozen,
                    snapshot_ref="sha256:abc", evidence_refs=("snap_1",))
            return QuiescenceRejected(reason_code="active_writer_detected")

    def _chain(barrier):
        # 版本契约（正交）在正式配置下强制真实 weight_version——mock 轮
        # 显式带版本（dense_turns 默认无版本，会被 assemble 期正确拦截）
        from test_slime_generate import dense_turns

        turns = dense_turns()
        for t in turns:
            t.response["meta_info"]["weight_version"] = "5"
        chain = build_dense_chain(
            config=_formal_config(policy_version="5", execution_mode="fa_formal"),
            runtime_quiescence_barrier=barrier,
            turns=turns,
        )
        return chain, barrier

    ok = _Barrier(confirmed=True)
    chain, _ = _chain(ok)
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(
        _Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert ok.calls == 1 and audit.runtime_quiescence_confirmed is True
    assert chain.grading.calls  # 屏障确认后才评分
    # P0-1 验收：评分消费的是屏障产出的冻结输入，不是原 workspace
    assert chain.grading.calls[0]["workspace"] is ok.frozen
    assert audit.outcome_v2["completion_class"] == "present_complete"
    # 六轮强 P1：屏障 lineage 进成功 Outcome
    assert "snapshot:sha256:abc" in audit.outcome_v2["evidence_refs"]
    assert any(not getattr(x, "remove_sample", False) for x in delivered)

    deny = _Barrier(confirmed=False)
    chain2, _ = _chain(deny)
    _stamp_fa_identity(chain2.base_sample)
    delivered2 = await chain2.orchestrator.generate(
        _Args(), chain2.base_sample, dict(SAMPLING_PARAMS))
    audit2 = chain2.orchestrator.audits[0]
    assert chain2.grading.calls == []  # 拒绝 → 不评分
    assert audit2.outcome_v2["failure_category"] == "runtime_quiescence_failure"
    assert audit2.outcome_v2["reason_code"] == "active_writer_detected"
    assert audit2.outcome_v2["completion_class"] == "missing"
    assert all(getattr(x, "remove_sample", False) for x in delivered2)


def test_quiescence_closed_union_states():
    """复核六轮强 P1：封闭联合类型——确认必带冻结句柄+snapshot lineage+
    证据；拒绝必配五码；矛盾/缺项构造即拒。"""

    from repoharness2.adapters.slime.generate import (
        QuiescenceConfirmed,
        QuiescenceRejected,
    )

    with pytest.raises(ValueError, match="snapshot_ref"):
        QuiescenceConfirmed(frozen_grading_workspace=object(), snapshot_ref="",
                            evidence_refs=("e",))
    with pytest.raises(ValueError, match="evidence_refs"):
        QuiescenceConfirmed(frozen_grading_workspace=object(),
                            snapshot_ref="sha256:x", evidence_refs=())
    with pytest.raises(ValueError, match="冻结 workspace"):
        QuiescenceConfirmed(frozen_grading_workspace=None,
                            snapshot_ref="sha256:x", evidence_refs=("e",))
    with pytest.raises(ValueError, match="五码之一"):
        QuiescenceRejected(reason_code="whatever")
    QuiescenceRejected(reason_code="snapshot_freeze_failed")


async def test_barrier_fatal_exception_escapes_soft_catch():
    """复核六轮 P0-1：屏障异常 → Fatal 从 generate() **逃逸**（不被软
    失败 catch 吞成缺员）；worker 对该异常有既有 run_halt 通道。"""

    from test_slime_generate import (
        SAMPLING_PARAMS,
        _Args,
        _formal_config,
        build_dense_chain,
    )

    from repoharness2.adapters.slime.async_worker import (
        FatalExecutionInfrastructureError,
    )

    class _Boom:
        async def establish(self, *, workspace, audit):
            raise TimeoutError("barrier hung")

    from test_slime_generate import dense_turns

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"  # 版本契约（正交）
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Boom(),
        turns=turns,
    )
    _stamp_fa_identity(chain.base_sample)
    with pytest.raises(FatalExecutionInfrastructureError, match="runtime_barrier_exception"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))


def test_fa_entry_rejects_s1_compat_mode():
    """复核五轮 P0-2：FA 专用入口对 s1_compat（含未配置默认值）拒绝启动
    ——silent downgrade 关闭。"""

    import sys
    from types import SimpleNamespace

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))
    from fa_bringup import rollout_entry

    args = SimpleNamespace(
        rh2_orchestrator=SimpleNamespace(config=SimpleNamespace(execution_mode="s1_compat")),
        rh2_sampling_params={"top_p": 1.0},
    )
    with pytest.raises(rollout_entry.FaEntryError, match="fa_entry_requires_fa_execution_mode"):
        rollout_entry._build_service(args, object())


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
