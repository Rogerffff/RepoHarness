"""预算终止闭环——批 D-1（I04 处置注入）与批 C（I02 turn 预算）的准入面回归。

批 D-1（2026-09-09）：已批处置（第一组：turn 截断 KEEP_FULL、hard wall DROP_GROUP）由
`bringup.inject_disposition_policy(args)` 在 `ensure_fa_started` 注入 `args.rh2_disposition_policy`；
`owner_cancelled_truncation` / `agent_violation` 未定保持 None（遇到仍 fail-fast）；冲突覆盖 →
StartupCheckError。库层 `DispositionPolicy` / `apply_member_disposition` 保持中立（不带值）。

真实接缝：经 `world` 的真实 miles `DefaultDataBuffer.put` + 复合 group filter，hard wall 成员
（fa_formal 编排本体产出的 present_truncated + hard_wall_timeout）在注入后整组 DROP，不再
DispositionNotInjectedError；policy_horizon 的 KEEP 路径由批 C 产出真实 `max_turns_exhausted` 后验证。
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))
from test_w1b_group_admission import (  # noqa: E402
    BOTH_OK,
    _build_chain,
    _buffer,
    _convert,
    _dispatch_group,
    _entry,
    _miles_args,
)


def test_inject_disposition_policy_sets_expected_and_rejects_conflict():
    from repoharness2.adapters.miles.group_admission import DISPOSITION_POLICY_ARGS_KEY
    from repoharness2.adapters.slime.bringup import (
        DISPOSITION_POLICY_VALUES,
        inject_disposition_policy,
        make_disposition_policy,
    )
    from repoharness2.adapters.slime.generate import StartupCheckError
    from repoharness2.governance.admission import DispositionPolicy

    assert DISPOSITION_POLICY_VALUES == {
        "policy_horizon_truncation": "KEEP_FULL",
        "hard_wall_truncation": "DROP_GROUP",
        "owner_cancelled_truncation": None,
        "agent_violation": None,
    }
    args = Namespace()
    policy = inject_disposition_policy(args)
    assert getattr(args, DISPOSITION_POLICY_ARGS_KEY) is policy
    assert policy.policy_horizon_truncation == "KEEP_FULL" and policy.hard_wall_truncation == "DROP_GROUP"
    assert policy.owner_cancelled_truncation is None and policy.agent_violation is None
    assert inject_disposition_policy(args) is policy  # 幂等：已注入且一致 → 保持

    consistent = Namespace(**{DISPOSITION_POLICY_ARGS_KEY: make_disposition_policy()})
    assert inject_disposition_policy(consistent) is getattr(consistent, DISPOSITION_POLICY_ARGS_KEY)

    conflicting = Namespace(**{DISPOSITION_POLICY_ARGS_KEY: DispositionPolicy(hard_wall_truncation="KEEP_FULL")})
    with pytest.raises(StartupCheckError, match="disposition_policy_conflict"):
        inject_disposition_policy(conflicting)
    wrong_type = Namespace(**{DISPOSITION_POLICY_ARGS_KEY: {"hard_wall_truncation": "DROP_GROUP"}})
    with pytest.raises(StartupCheckError, match="disposition_policy_conflict"):
        inject_disposition_policy(wrong_type)


def test_library_policy_stays_neutral():
    """库层不带值：不注入时四槽位全 None（fail-fast 语义由既有测试覆盖）。"""

    from repoharness2.governance.admission import DispositionPolicy

    p = DispositionPolicy()
    assert (p.policy_horizon_truncation, p.hard_wall_truncation, p.owner_cancelled_truncation, p.agent_violation) == (
        None, None, None, None,
    )


async def test_injected_policy_drops_hard_wall_member_through_real_buffer(world, tmp_path):
    """真实 fa_formal 编排本体产出 hard wall 成员（exit=-1 → present_truncated / hard_wall_timeout）→
    注入后经真实 DefaultDataBuffer.put + group filter 整组 DROP（度量 `drop_admission_truncation_hard_wall_excluded`），
    不再 DispositionNotInjectedError；同一 world 下未注入仍 fail-fast（对照）。"""

    world.install_sglang_stub()
    from repoharness2.adapters.slime.bringup import inject_disposition_policy
    from repoharness2.governance.admission import DispositionNotInjectedError

    chain = _build_chain(world, tmp_path / "a", grading_kinds=BOTH_OK, exit_codes=(0, -1))
    prompt_group, group = await _dispatch_group(world, chain)
    (leaf,) = group[1]
    assert leaf.metadata["rh2_admission"]["outcome"]["termination_kind"] == "hard_wall_timeout"
    assert leaf.metadata["rh2_admission"]["outcome"]["completion_class"] == "present_truncated"

    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    with pytest.raises(DispositionNotInjectedError, match="hard_wall_truncation"):
        await buf.put(_entry(world, prompt_group, group))  # 对照：未注入 → fail-fast

    chain2 = _build_chain(world, tmp_path / "b", grading_kinds=BOTH_OK, exit_codes=(0, -1))
    prompt_group2, group2 = await _dispatch_group(world, chain2)
    args2 = _miles_args(world, chain2)
    inject_disposition_policy(args2)  # 批 D-1：启动注入的同一函数
    buf2, recycled2 = _buffer(world, args2)
    await buf2.put(_entry(world, prompt_group2, group2))
    assert buf2._buffer == [] and recycled2 == []
    assert buf2.get_metrics()["rollout/dynamic_filter/drop_admission_truncation_hard_wall_excluded"] == 1


# ================================================================ 批 C（I02 turn 预算 + I14 rollout 侧停止）

import asyncio  # noqa: E402

from test_f2_2_capability import _fa_cfg, _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    TASK_ID_DENSE,
    FakeRolloutDocker,
    FixtureSlimeSample,
    GradingSubmitStub,
    MockSessionAdapter,
    _Args,
    build_dense_chain,
    dense_leaf_sample,
    dense_turns,
    make_task,
)
from test_w1b_termination_facts_producer import _formal_chain, _steps  # noqa: E402


class _FakeTokenizer:
    def apply_chat_template(self, *a, **kw):
        return [1, 2, 3]

    def decode(self, *a, **kw):
        return "decoded"


class _Hook:
    records: list = []


def _ticking_clock(*values: float):
    seq = list(values)

    def clock() -> float:
        if len(seq) > 1:
            return seq.pop(0)
        return seq[0]

    return clock


class FakeTurnBudget:
    """编排注入点的替身（生产 = registry.subscribe_turn_budget / turn_budget_snapshot）。真实 wire 侧
    的事实产生由下方"真实 vendored adapter app"用例覆盖。"""

    def __init__(self):
        self.state: dict[str, dict] = {}
        self.subs: dict = {}

    def subscribe(self, sid, cb):
        self.subs[sid] = cb
        if self.state.get(sid, {}).get("exhausted"):
            cb(sid)

    def unsubscribe(self, sid):
        self.subs.pop(sid, None)

    def snapshot(self, sid):
        s = self.state.get(sid)
        return dict(s) if s else None

    def exhaust(self, sid, cap=3):
        self.state[sid] = {"cap": cap, "accepted": cap, "exhausted": True, "refused_count": 1, "refused_at_monotonic": 1.0}
        cb = self.subs.get(sid)
        if cb is not None:
            cb(sid)


def _wire_budget(orchestrator, budget: FakeTurnBudget) -> None:
    orchestrator._turn_budget_subscribe = budget.subscribe
    orchestrator._turn_budget_unsubscribe = budget.unsubscribe
    orchestrator._turn_budget_snapshot = budget.snapshot


def _kill_execs(docker) -> list:
    return [c for c in docker.calls if c[0] == "exec" and "pkill -9 -u agent" in c[-1]]


# ---------------------------------------------------------------- 真实 vendored adapter app：cap 事实 + 403 + 等在飞交付


async def test_real_adapter_turn_cap_records_fact_refuses_with_403_after_inflight_delivery(world):
    """经真实 vendored AnthropicAdapter app（真实 _run_turn / 真实 _check_turn_cap 计数与前置条件 /
    真实 record_turn；只替换 SGLang 调用）：cap=3 时第 4 次 POST /v1/messages 得 403
    `rh2_turn_budget_exhausted` + x-should-retry:false（不再是 vendored 429）；registry 快照
    {cap:3, accepted:3, exhausted:True}；订阅回调恰好一次；count_tokens 不计；第 3 次在飞时第 4 次
    到达 → 第 4 次的拒绝在第 3 次交付**之后**返回、无 poison（Codex 计划审查 R3 并发接缝）。"""

    import time

    import slime.agent.adapters.common as slime_common
    from aiohttp.test_utils import TestClient, TestServer
    from slime.agent.adapters.anthropic import AnthropicAdapter

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.session_capability import mint_session_capability

    registry = cw.CaptureRegistry()
    cw.install_turn_budget_wire(registry)  # 与 install_capture_wire 内部同一安装（这里不需要真实 wire 的 SGLang 面）
    cw.install_turn_budget_wire(registry)  # 幂等
    delivered: list[float] = []

    async def canned(prompt_ids, session, body, *, adapter, session_id):
        await asyncio.sleep(0.3)
        delivered.append(time.monotonic())
        return slime_common.TurnRecord(prompt_ids=list(prompt_ids), output_ids=[7, 8], finish_reason="stop", output_log_probs=[0.0, 0.0])

    slime_common.call_sglang_generate = canned
    cap = mint_session_capability("exec_C#p1-aaaa")
    sid = "s-exec_C#p1-aaaa"
    registry.register(sid, _Hook(), physical_attempt_id="exec_C#p1-aaaa", capability_token=cap.token)
    hits: list[str] = []
    registry.subscribe_turn_budget(sid, hits.append)
    adapter = AnthropicAdapter(tokenizer=_FakeTokenizer(), sglang_url="http://unused", max_turns_per_sid=3)
    adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
    adapter.open_session(sid)
    client = TestClient(TestServer(adapter.app))
    await client.start_server()
    body = {"model": "m", "max_tokens": 16, "messages": [{"role": "user", "content": "hi"}]}
    hdr = {"Authorization": f"Bearer {cap.token}", "content-type": "application/json"}
    try:
        r1 = await client.post("/v1/messages", json=body, headers=hdr)
        r2 = await client.post("/v1/messages", json=body, headers=hdr)
        assert (r1.status, r2.status) == (200, 200)
        rc = await client.post("/v1/messages/count_tokens", json=body, headers=hdr)
        assert rc.status in (200, 400, 422, 500)  # 不经 _run_turn：无论怎样都不计入预算
        assert registry.turn_budget_snapshot(sid)["accepted"] == 2 and hits == []
        # 第 3 次在飞（0.3s）时第 4 次到达：第 4 次须等第 3 次交付后才被拒
        t3 = asyncio.create_task(client.post("/v1/messages", json=body, headers=hdr))
        await asyncio.sleep(0.05)
        t4 = asyncio.create_task(client.post("/v1/messages", json=body, headers=hdr))
        r3, r4 = await asyncio.gather(t3, t4)
        t4_done = time.monotonic()
        assert r3.status == 200 and r4.status == 403
        assert r4.headers.get("x-should-retry") == "false"
        assert (await r4.json())["error"]["type"] == "rh2_turn_budget_exhausted"
        assert t4_done >= delivered[-1]  # 拒绝晚于第 3 次交付
        snap = registry.turn_budget_snapshot(sid)
        assert snap["cap"] == 3 and snap["accepted"] == 3 and snap["exhausted"] is True and snap["refused_count"] == 1
        assert hits == [sid]  # 命中通知恰好一次
        assert registry.poison.is_poisoned(sid) is False  # 在飞的第 3 轮没有被断连成 poison
        late: list[str] = []
        registry.subscribe_turn_budget(sid, late.append)  # 命中后订阅 → 立即回调（竞态收口）
        assert late == [sid]
        r5 = await client.post("/v1/messages", json=body, headers=hdr)
        assert r5.status == 403 and registry.turn_budget_snapshot(sid)["refused_count"] == 2
    finally:
        await client.close()
        registry.unregister(sid)
    assert registry.turn_budget_snapshot(sid) is None  # 注销即清理
    with pytest.raises(cw.CaptureWireOwnershipError):
        cw.install_turn_budget_wire(cw.CaptureRegistry())  # 单代归属


# ---------------------------------------------------------------- 编排：cap → CC 自退 → max_turns_exhausted → KEEP


class _CapThenExitDriver:
    """喂完所有轮后"命中 cap"（CC 收到 403），按 CC 行为非零退出。"""

    name = "mock_harness"

    def __init__(self, adapter_ref, budget: FakeTurnBudget, exit_code: int = 1):
        self.adapter_ref, self.budget, self.exit_code = adapter_ref, budget, exit_code
        self.calls: list = []

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        self.calls.append(session_id)
        adapter = self.adapter_ref["adapter"]
        await adapter.run_all_turns()
        self.budget.exhaust(adapter.opened[-1])
        return self.exit_code


async def test_cap_then_cc_exit_is_max_turns_exhausted_present_truncated_and_graded():
    chain = _formal_chain()
    budget = FakeTurnBudget()
    _wire_budget(chain.orchestrator, budget)
    chain.orchestrator._harness_driver = _CapThenExitDriver(chain.adapter_ref, budget, exit_code=1)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert all(not getattr(x, "remove_sample", False) for x in delivered)  # 不是 ABORTED
    assert audit.harness_exit_code == 1
    assert audit.termination_kind_hint == "max_turns_exhausted"
    assert audit.outcome_v2["termination_kind"] == "max_turns_exhausted"
    assert audit.outcome_v2["completion_class"] == "present_truncated"
    assert audit.finalized is not None and chain.grading.calls  # 真实评分照常
    assert audit.termination["turn_budget"]["exhausted"] is True
    assert audit.termination["stop"]["requested_by"] is None  # CC 自退，未强制停止
    assert not any("nonzero" in f.detail for f in audit.failure_records)
    payload = delivered[0].metadata["rh2_admission"]
    assert payload["outcome"]["termination_kind"] == "max_turns_exhausted"


async def test_cap_then_cc_hangs_is_force_stopped_within_grace(monkeypatch):
    """CC 收到 403 后不退出 → 宽限（可控 0.2s）后 rh2 强制停止：kill 脚本经 workspace 执行、验证归零、
    取消 harness task、退出码 = HARNESS_EXIT_STOPPED_BY_RH2；仍是 max_turns_exhausted / present_truncated。"""

    from repoharness2.adapters.slime import generate as generate_mod

    monkeypatch.setattr(generate_mod, "TURN_BUDGET_EXIT_GRACE_SEC", 0.2)
    chain = _formal_chain()
    budget = FakeTurnBudget()
    _wire_budget(chain.orchestrator, budget)
    cancelled = {"seen": False}

    class _CapThenHang(_CapThenExitDriver):
        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            adapter = self.adapter_ref["adapter"]
            await adapter.run_all_turns()
            self.budget.exhaust(adapter.opened[-1])
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled["seen"] = True
                raise

    chain.orchestrator._harness_driver = _CapThenHang(chain.adapter_ref, budget)
    delivered = await asyncio.wait_for(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=10
    )
    audit = chain.orchestrator.audits[0]
    assert cancelled["seen"] is True
    assert audit.harness_exit_code == generate_mod.HARNESS_EXIT_STOPPED_BY_RH2
    stop = audit.termination["stop"]
    assert stop["requested_by"] == "turn_budget" and stop["forced"] is True
    assert stop["kill_verified"] is True and stop["residual_processes"] == 0
    assert stop["grace_seconds"] == 0.2 and stop["harness_exited_within_grace"] is False
    assert len(_kill_execs(chain.docker)) >= 1  # 容器内 pkill 真的经 workspace 执行了
    assert "turn_budget_forced_stop" in _steps(audit)
    assert audit.outcome_v2["termination_kind"] == "max_turns_exhausted"
    assert audit.outcome_v2["completion_class"] == "present_truncated"
    assert all(not getattr(x, "remove_sample", False) for x in delivered)


async def test_cap_then_deadline_during_grace_is_hard_wall_not_keep():
    """Codex 计划审查 R3：cap 命中后 CC 未停、宽限内 episode 期限到点 = 真实 hard wall → 整组不训练；
    cap 事实保留在 termination.turn_budget。"""

    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    budget = FakeTurnBudget()
    _wire_budget(chain.orchestrator, budget)

    class _CapThenHang(_CapThenExitDriver):
        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            adapter = self.adapter_ref["adapter"]
            await adapter.run_all_turns()
            self.budget.exhaust(adapter.opened[-1])
            await asyncio.Event().wait()

    chain.orchestrator._harness_driver = _CapThenHang(chain.adapter_ref, budget)
    # 入口 0；materialize 100；启动前 100；harness 等待 100；宽限剩余 0.1；宽限后已过期
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, 100.0, 899.9, 5000.0)
    await asyncio.wait_for(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=10)
    audit = chain.orchestrator.audits[0]
    assert audit.harness_exit_code == -1
    assert audit.episode_deadline["hit_by"] == "harness_outer"
    assert audit.termination_kind_hint == "hard_wall_timeout"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"  # 不是 max_turns_exhausted
    assert audit.termination["turn_budget"]["exhausted"] is True  # cap 事实保留
    assert audit.termination["stop"]["requested_by"] == "hard_wall" and audit.termination["stop"]["forced"] is True
    assert "hard_wall_forced_stop" in _steps(audit)


async def test_hard_wall_forces_stop_before_drain():
    """I14 rollout 侧：vendored 轮询到点（exit=-1）→ 先杀容器内 agent 进程再 drain（事件顺序）。"""

    chain = build_dense_chain(config=_fa_cfg(), harness_exit_code=-1)
    _stamp_fa_identity(chain.base_sample)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    steps = _steps(audit)
    assert steps.index("hard_wall_forced_stop") < steps.index("session_revoked")
    assert audit.termination["stop"] == {
        "requested_by": "hard_wall", "forced": True, "kill_verified": True, "residual_processes": 0,
        "grace_seconds": None, "harness_exited_within_grace": None,
    }
    assert len(_kill_execs(chain.docker)) >= 1
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"


async def test_cap_does_not_exempt_poison_or_capture_failures():
    """Codex 计划审查 R3：cap 事实只解释由预算拒绝导致的退出——在飞请求断连 poison（client_cancelled）
    仍是 session_poisoned_during_execution → api_failure / missing，不因 cap 而 KEEP。"""

    from repoharness2.adapters.slime.async_worker import SessionPoisonRegistry
    from repoharness2.adapters.slime.generate import RolloutOrchestrator

    registry = SessionPoisonRegistry()
    budget = FakeTurnBudget()
    adapter_ref: dict = {}
    started = asyncio.Event()

    def adapter_factory(hook, session_defaults):
        adapter = MockSessionAdapter(hook, session_defaults, dense_turns(), [dense_leaf_sample()])
        adapter_ref["adapter"] = adapter
        return adapter

    class _CapThenPoisoned:
        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            adapter = adapter_ref["adapter"]
            await adapter.run_all_turns()
            budget.exhaust(adapter.opened[-1])
            started.set()
            await asyncio.Event().wait()

    orch = RolloutOrchestrator(
        config=_fa_cfg(), task_resolver=make_task(TASK_ID_DENSE), adapter_factory=adapter_factory,
        harness_driver=_CapThenPoisoned(), grading_submit=GradingSubmitStub(), docker=FakeRolloutDocker(),
        session_poison_check=registry.is_poisoned, session_poison_subscribe=registry.subscribe,
        session_poison_unsubscribe=registry.unsubscribe, session_poison_reason=registry.reason,
        turn_budget_subscribe=budget.subscribe, turn_budget_unsubscribe=budget.unsubscribe,
        turn_budget_snapshot=budget.snapshot,
    )
    sample = FixtureSlimeSample(index=0)
    _stamp_fa_identity(sample)

    async def poison_after_cap():
        await started.wait()
        (sid,) = registry._subscribers
        registry.poison(sid, "client_cancelled")

    result, _ = await asyncio.gather(orch.generate(_Args(), sample, dict(SAMPLING_PARAMS)), poison_after_cap())
    assert result[0].remove_sample is True
    audit = orch.audits[0]
    assert audit.outcome_v2["termination_kind"] == "api_failure"
    assert audit.outcome_v2["reason_code"] == "session_poisoned_during_execution"
    assert audit.termination["turn_budget"]["exhausted"] is True


# ---------------------------------------------------------------- e2e：真实 miles buffer 上 turn 截断 KEEP_FULL


async def test_turn_truncated_member_keeps_full_through_real_buffer_after_injection(world, tmp_path):
    """真实 fa_formal 编排本体（prepared face + registry）产出 max_turns_exhausted / present_truncated 成员 →
    经真实 DefaultDataBuffer.put + 复合 group filter：注入前 DispositionNotInjectedError(policy_horizon)，
    批 D-1 注入后 KEEP_FULL 进组、可被 get 消费并转换（真实 reward 来自评分）。"""

    world.install_sglang_stub()
    from repoharness2.adapters.slime.bringup import inject_disposition_policy
    from repoharness2.governance.admission import DispositionNotInjectedError

    def _capped_chain(sub):
        chain = _build_chain(world, tmp_path / sub, grading_kinds=BOTH_OK)
        budget = FakeTurnBudget()
        _wire_budget(chain.orchestrator, budget)
        inner = chain.orchestrator._harness_driver
        adapter_ref = inner.adapter_ref

        class _CapOnSecond:
            name = "mock_harness"
            calls = 0

            async def run(self, sandbox, **kw):
                code = await inner.run(sandbox, **kw)
                type(self).calls += 1
                if type(self).calls == 2:  # 第二个成员命中 cap 后 CC 非零退出
                    budget.exhaust(adapter_ref["adapter"].opened[-1])
                    return 1
                return code

        chain.orchestrator._harness_driver = _CapOnSecond()
        return chain

    chain = _capped_chain("a")
    prompt_group, group = await _dispatch_group(world, chain)
    (leaf,) = group[1]
    payload = leaf.metadata["rh2_admission"]["outcome"]
    assert payload["termination_kind"] == "max_turns_exhausted" and payload["completion_class"] == "present_truncated"
    args = _miles_args(world, chain)
    buf, _ = _buffer(world, args)
    with pytest.raises(DispositionNotInjectedError, match="policy_horizon_truncation"):
        await buf.put(_entry(world, prompt_group, group))

    chain2 = _capped_chain("b")
    prompt_group2, group2 = await _dispatch_group(world, chain2)
    args2 = _miles_args(world, chain2)
    inject_disposition_policy(args2)
    buf2, recycled2 = _buffer(world, args2)
    await buf2.put(_entry(world, prompt_group2, group2))
    assert len(buf2._buffer) == 1 and recycled2 == []
    got = await buf2.get(current_version=5)
    assert got.group is group2
    td = _convert(world, args2, got.group)
    assert len(td["raw_reward"]) == 2  # 两个成员都进训练数据，reward 来自真实评分表


# ================================================================ Codex 联合审查 R1：真实分块 HTTP 的 cap 竞态

import json as _json  # noqa: E402
import time as _time  # noqa: E402


class _RaceTokenizer:
    def apply_chat_template(self, *a, **kw):
        return [1, 2, 3]

    def decode(self, *a, **kw):
        return "probe reply"


class _Engine:
    """内存 SGLang 替身：生成阻塞到 release；abort 计数。"""

    def __init__(self):
        self.version = "3"
        self.reset()

    def reset(self):
        self.entered, self.release, self.cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()
        self.calls = 0
        self.aborts = 0


class _EngineResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    async def json(self, **kw):
        return self.payload


class _EngineContext:
    def __init__(self, engine, url, payload):
        self.engine, self.url, self.payload = engine, url, payload

    async def __aenter__(self):
        if self.url.endswith("/abort_request"):
            self.engine.aborts += 1
            return _EngineResponse({})
        self.engine.calls += 1
        self.engine.entered.set()
        try:
            await self.engine.release.wait()
        except asyncio.CancelledError:
            self.engine.cancelled.set()
            raise
        return _EngineResponse({
            "text": "probe reply",
            "meta_info": {
                "id": self.payload["rid"], "finish_reason": {"type": "stop"},
                "weight_version": str(self.engine.version),
                "output_token_logprobs": [[-0.1, 7, None], [-0.1, 8, None]],
            },
        })

    async def __aexit__(self, *a):
        return False


class _EngineSession:
    def __init__(self, engine):
        self.engine = engine

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, url, json=None, headers=None):
        return _EngineContext(self.engine, url, json)


class _EngineAiohttp:
    class ClientError(Exception):
        pass

    def __init__(self, engine):
        self.engine = engine

    def ClientSession(self, **kw):
        return _EngineSession(self.engine)

    def ClientTimeout(self, **kw):
        return None


def _reset_wire_generation(monkeypatch, slime_common) -> None:
    """把 capture wire / turn budget wire 的进程级单代归属重置为"新进程"（同 W3b 启动测试的 fixture）。"""

    monkeypatch.setattr(slime_common, "_rh2_capture_wire_installed", False, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_capture_wire_registry", None, raising=False)
    monkeypatch.setattr(slime_common, "_rh2_turn_budget_wire_registry", None, raising=False)


async def _until(predicate, timeout=2.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.001)


def _split_body_request(client, body_bytes, headers, gate):
    async def partial():
        yield body_bytes[:-1]
        await gate.wait()
        yield body_bytes[-1:]

    return client.post("/v1/messages", data=partial(), headers=headers)


async def _race_case(registry, adapter, engine, name, *, split_bodies: bool, close_on_refusal: bool):
    from aiohttp.test_utils import TestClient, TestServer
    from slime.utils.types import Sample

    from repoharness2.adapters.slime.bringup import make_per_rollout_adapter
    from repoharness2.adapters.slime.generate import GenerationCaptureHook
    from repoharness2.adapters.slime.session_capability import mint_session_capability

    engine.reset()
    paid = f"exec_{name}#p1-aaaa"
    sid = f"s-{paid}"
    cap = mint_session_capability(paid)
    hook = GenerationCaptureHook(
        trajectory_id=f"traj_{name}", model_name="probe", backend_name="sglang", backend_version="probe",
        renderer_cls_name="probe", tokenizer_name="probe", template_hash="sha256:" + "a" * 64,
    )
    per = make_per_rollout_adapter(registry, adapter, hook)
    per.open_session(sid, physical_attempt_id=paid, capability_token=cap.token, deadline_monotonic=_time.monotonic() + 60)
    notified: list[dict] = []
    registry.subscribe_turn_budget(sid, lambda _: notified.append({
        "captures_at_notify": len(hook.records),
        "admitted_inflight_at_notify": len(adapter.inflight.get(sid, ())),
    }))
    client = TestClient(TestServer(adapter.app, handler_cancellation=True))
    await client.start_server()
    body = {"model": "probe", "max_tokens": 16, "stream": True, "messages": [{"role": "user", "content": "probe"}]}
    headers = {"Authorization": f"Bearer {cap.token}", "Content-Type": "application/json"}
    encoded = _json.dumps(body).encode()
    gates = [asyncio.Event(), asyncio.Event()]
    requests: list[asyncio.Task] = []

    async def request(i):
        if split_bodies:
            return await _split_body_request(client, encoded, headers, gates[i])
        return await client.post("/v1/messages", json=body, headers=headers)

    try:
        requests.append(asyncio.create_task(request(0)))
        if split_bodies:
            requests.append(asyncio.create_task(request(1)))
            await _until(lambda: registry._inflight.get(sid, 0) == 2)  # 两个请求头都过了 guard，body 都没收全
            assert registry.turn_budget_snapshot(sid) is None
            gates[0].set()
            await engine.entered.wait()  # 第 1 个已接纳并开始生成
            gates[1].set()  # 第 2 个 body 补齐：修前此刻立即 403 + 通知
        else:
            await engine.entered.wait()
            requests.append(asyncio.create_task(request(1)))
        await asyncio.sleep(0.05)
        early = {
            "refusal_before_generation_release": requests[1].done(),
            "captures": len(hook.records), "notified": list(notified), "engine_calls": engine.calls,
        }
        if close_on_refusal:
            engine.release.set()  # 让已接纳的第 1 轮交付；拒绝只能在其后到达
            refused = await asyncio.wait_for(requests[1], timeout=2)
            assert refused.status == 403
            requests[0].cancel()  # 客户端收到不可重试拒绝后关闭在飞连接——第 1 轮已交付，无可断
            await asyncio.gather(requests[0], return_exceptions=True)
            await asyncio.sleep(0.05)
            statuses = [refused.status]
        else:
            engine.release.set()
            replies = await asyncio.gather(*requests)
            statuses = [r.status for r in replies]
            for r in replies:
                await r.read()
        await _until(lambda: registry._inflight.get(sid, 0) == 0)
        result = {
            "early": early, "statuses": statuses, "captures": len(hook.records),
            "tree_turns": adapter.manager.turn_count(sid), "poison": registry.poison.reason(sid),
            "aborts": engine.aborts, "budget": registry.turn_budget_snapshot(sid), "notified": notified,
        }
        leaves = await per.finish_session(sid, base_sample=Sample(index=0))
        result["leaf_response_tokens"] = [s.tokens[-s.response_length:] for s in leaves]
        return result
    finally:
        engine.release.set()
        for tsk in requests:
            if not tsk.done():
                tsk.cancel()
        await asyncio.gather(*requests, return_exceptions=True)
        await per.drop_session(sid)
        await client.close()


async def test_cap_refusal_waits_for_admitted_inflight_even_when_bodies_race(world, monkeypatch):
    """Codex 联合审查 R1（移植其 cap_body_race_probe 三案）：真实 vendored app + 真实 capture wire /
    proxy / 轨迹树，只替换 SGLang IO。cap=1：两个请求头先后过 guard、body 都没收全（修前判定点在读 body
    之前，两者都在"0 次"时通过），第 1 个补齐 body 开始生成、第 2 个补齐 body → 修前立即 403 + 预算通知
    （在飞第 1 轮未交付），客户端据此关连接则第 1 轮断连成 client_cancelled；修后第 2 个等第 1 轮交付
    再被拒，通知时 captures=1、已接纳在飞=0，关连接也无可断。"""

    world.install_sglang_stub()
    import slime.agent.adapters.common as slime_common
    from slime.agent.adapters.anthropic import AnthropicAdapter

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import build_production_model_call_proxy

    _reset_wire_generation(monkeypatch, slime_common)  # 本测试 = 新进程代（与 W3b 启动测试同约定）
    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    build_production_model_call_proxy(registry, lambda: "3", require_real=False, artifact_sink=None)
    engine = _Engine()
    monkeypatch.setattr(cw, "aiohttp", _EngineAiohttp(engine))
    for name, split, close in (("seq", False, False), ("race_keep", True, False), ("race_close", True, True)):
        adapter = AnthropicAdapter(tokenizer=_RaceTokenizer(), sglang_url="http://fake-engine", max_turns_per_sid=1)
        adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
        r = await _race_case(registry, adapter, engine, name, split_bodies=split, close_on_refusal=close)
        assert r["early"]["refusal_before_generation_release"] is False, (name, r)  # 拒绝不早于已接纳轮的交付
        assert r["early"]["engine_calls"] == 1
        assert r["captures"] == 1 and r["tree_turns"] == 1 and r["poison"] is None and r["aborts"] == 0, (name, r)
        assert r["budget"]["cap"] == 1 and r["budget"]["accepted"] == 1 and r["budget"]["exhausted"] is True
        assert r["notified"] == [{"captures_at_notify": 1, "admitted_inflight_at_notify": 0}], (name, r)
        assert r["leaf_response_tokens"] == [[7, 8]]
        if not close:
            assert r["statuses"] == [200, 403]
        else:
            assert r["statuses"] == [403]


class _HttpCapDriver:
    """真实 HTTP 驱动：第一个成员用分块 body 制造竞态，第二个成员顺序；都在 cap=1 后收到 403 并按 CC 退出。"""

    name = "claude_code"

    def __init__(self, client, registry, engine, holder, *, race_first: bool):
        self.client, self.registry, self.engine, self.holder, self.race_first = client, registry, engine, holder, race_first
        self.rows: list[dict] = []

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        self.engine.reset()
        sid = self.registry.resolve_capability(session_id)
        hook = self.holder["hook"]
        row = {"race": self.race_first and not self.rows}
        self.rows.append(row)
        body = {"model": "probe", "max_tokens": 16, "stream": True, "messages": [{"role": "user", "content": "probe"}]}
        encoded = _json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {session_id}", "Content-Type": "application/json"}
        gates = [asyncio.Event(), asyncio.Event()]
        tasks: list[asyncio.Task] = []

        async def request(n):
            if row["race"]:
                return await _split_body_request(self.client, encoded, headers, gates[n])
            return await self.client.post("/v1/messages", json=body, headers=headers)

        try:
            tasks.append(asyncio.create_task(request(0)))
            if row["race"]:
                tasks.append(asyncio.create_task(request(1)))
                await _until(lambda: self.registry._inflight.get(sid, 0) == 2)
                gates[0].set()
                await self.engine.entered.wait()
                gates[1].set()
                await asyncio.sleep(0.05)
                row["refused_before_delivery"] = tasks[1].done()
                self.engine.release.set()
                refused = await asyncio.wait_for(tasks[1], timeout=2)
                row.update(refusal_status=refused.status, captures_at_refusal=len(hook.records))
                tasks[0].cancel()  # 收到拒绝后关连接：第 1 轮已交付
                await asyncio.gather(tasks[0], return_exceptions=True)
            else:
                await self.engine.entered.wait()
                tasks.append(asyncio.create_task(request(1)))
                await asyncio.sleep(0.03)
                assert not tasks[1].done()
                self.engine.release.set()
                responses = await asyncio.gather(*tasks)
                for response in responses:
                    await response.read()
                row.update(statuses=[r.status for r in responses], captures_at_refusal=len(hook.records))
            return 1
        finally:
            for tsk in tasks:
                if not tsk.done():
                    tsk.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            row.update(captures=len(hook.records), poison=self.registry.poison.reason(sid), aborts=self.engine.aborts)
            self.engine.release.set()


async def test_cap_body_race_group_reaches_real_buffer_as_keep_full(world, tmp_path, monkeypatch):
    """Codex 联合审查 R1（移植其 cap_to_admission_probe）：同一竞态经真实 HTTP → capture → formal 编排 →
    canonicalize → 真实 DefaultDataBuffer：修前第一成员 missing/api_failure、整组补采；修后两成员都是
    max_turns_exhausted / KEEP_FULL，buffer=1，raw_reward=[1.0, 0.0]，每成员训练 token=2。"""

    world.install_sglang_stub()
    import slime.agent.adapters.common as slime_common
    from aiohttp.test_utils import TestClient, TestServer
    from slime.agent.adapters.anthropic import AnthropicAdapter

    from repoharness2.adapters.slime import capture_wire as cw
    from repoharness2.adapters.slime.bringup import (
        bringup_leaf_facts,
        build_production_model_call_proxy,
        inject_disposition_policy,
        make_per_rollout_adapter,
    )

    _reset_wire_generation(monkeypatch, slime_common)
    registry = cw.CaptureRegistry()
    cw.install_capture_wire(registry)
    build_production_model_call_proxy(registry, lambda: "5", require_real=False, artifact_sink=None)
    engine = _Engine()
    engine.version = "5"
    monkeypatch.setattr(cw, "aiohttp", _EngineAiohttp(engine))
    adapter = AnthropicAdapter(tokenizer=_RaceTokenizer(), sglang_url="http://fake-engine", max_turns_per_sid=1)
    adapter.app.middlewares.append(cw.build_session_guard_middleware(registry))
    client = TestClient(TestServer(adapter.app, handler_cancellation=True))
    await client.start_server()
    try:
        chain = _build_chain(world, tmp_path, grading_kinds=BOTH_OK)
        holder: dict = {}
        orch = chain.orchestrator

        def factory(hook, defaults):
            holder["hook"] = hook
            return make_per_rollout_adapter(registry, adapter, hook)

        orch._adapter_factory = factory
        orch._leaf_facts_fn = bringup_leaf_facts
        orch._session_drain_owner = registry.drain_session_plane
        orch._session_poison_check = registry.poison.is_poisoned
        orch._session_poison_subscribe = registry.poison.subscribe
        orch._session_poison_unsubscribe = registry.poison.unsubscribe
        orch._session_poison_reason = registry.poison.reason
        orch._capture_boundary_check = registry.assert_session_clean
        orch._turn_budget_subscribe = registry.subscribe_turn_budget
        orch._turn_budget_unsubscribe = registry.unsubscribe_turn_budget
        orch._turn_budget_snapshot = registry.turn_budget_snapshot
        driver = _HttpCapDriver(client, registry, engine, holder, race_first=True)
        orch._harness_driver = driver
        prompt_group, group = await _dispatch_group(world, chain)
        assert driver.rows[0]["race"] is True and driver.rows[0]["refused_before_delivery"] is False
        assert driver.rows[0]["captures"] == 1 and driver.rows[0]["poison"] is None and driver.rows[0]["aborts"] == 0
        assert [a.outcome_v2["termination_kind"] for a in orch.audits] == ["max_turns_exhausted", "max_turns_exhausted"]
        assert [[s.remove_sample for s in member] for member in group] == [[False], [False]]
        args = _miles_args(world, chain)
        inject_disposition_policy(args)
        buf, recycled = _buffer(world, args)
        await buf.put(_entry(world, prompt_group, group))
        assert len(buf._buffer) == 1 and recycled == []
        got = await buf.get(current_version=5)
        td = _convert(world, args, got.group)
        assert td["raw_reward"] == [1.0, 0.0]
        assert [sum(mask) for mask in td["loss_masks"]] == [2, 2]
    finally:
        await client.close()
