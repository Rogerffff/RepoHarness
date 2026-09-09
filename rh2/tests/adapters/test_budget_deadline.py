"""批 B（I03，2026-09-09；第一组已批"墙钟从资源占用起表、排队计入、到点整组不训练"）：
统一 episode 期限的强制与收口。

被测事实（rh2/src/repoharness2/adapters/slime/generate.py / bringup.py / docker_sandbox.py）：
- 期限在 `_generate_attempt` 入口起表（deadline = clock() + task.time_budget_seconds）；
- materialize 受期限约束：到点取消该阶段，阶段自己按名字回收容器、拆私网（Codex 计划审查 R2：
  到期取消必须收口持有资源）→ `episode_deadline_in_materialize`（hard_wall_timeout / missing）；
- 准备阶段吃光预算 → 不开会话、不启动 CC → `episode_deadline_before_launch`；
- harness 运行受期限约束：到点取消 harness task，按 vendored EXIT_TIME_BUDGET_EXCEEDED 语义
  继续收口，`hit_by=harness_outer`；驱动回填 launch_attempted=False（引导吃光预算 / 引导途中被取消）→
  `episode_deadline_in_bootstrap`，不走 drain / 装配；
- proxy 因 `episode_deadline_exhausted` 中毒并取消 harness → `episode_deadline_during_model_call`
  （termination=hard_wall_timeout，不再是 api_failure）；
- 停止 / drain / 清理 / 评分不在期限内：harness 正常结束后即使期限已过也照常评分交付；
- `docker_sandbox._run` 在外层取消时 kill + wait 宿主 CLI 子进程（Codex R2 探针缺口）；
- 真实 `ClaudeCodeDriver.run` 的引导步骤超时与剩余预算取 min，引导吃光预算不启动 CC 并回填事实；
- per-rollout adapter 的 open_session(deadline_monotonic=…) 把期限显式写进 registry。

时钟：编排接受可注入 `clock`；用"按调用次序给值"的假钟让"到点"瞬间发生，不真等秒数。调用次序 =
入口起表 → materialize 剩余 → harness 启动前剩余 → harness 等待剩余 → harness 结束后剩余。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_capture_registry_fa import FakeHook  # noqa: E402
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

from repoharness2.adapters.slime import docker_sandbox  # noqa: E402
from repoharness2.adapters.slime.async_worker import SessionPoisonRegistry  # noqa: E402
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver, make_per_rollout_adapter  # noqa: E402
from repoharness2.adapters.slime.capture_wire import CaptureRegistry  # noqa: E402
from repoharness2.adapters.slime.generate import (  # noqa: E402
    HARNESS_EXIT_TIME_BUDGET_EXCEEDED,
    HARNESS_LAUNCH_FACTS,
    RolloutOrchestrator,
    SlimeBindingError,
)
from repoharness2.adapters.slime.outcome_producer import FAILURE_CODE_TERMINATION_MAP  # noqa: E402

BUDGET = 900  # make_task 的 time_budget_seconds（不是 RolloutTaskSpec 的 1800 缺省）


def _ticking_clock(*values: float):
    """按调用次序返回给定值，用尽后驻留最后一个。"""

    seq = list(values)

    def clock() -> float:
        if len(seq) > 1:
            return seq.pop(0)
        return seq[0]

    return clock


# ---------------------------------------------------------------- 映射表：期限码都是 hard_wall


def test_deadline_codes_are_attributed_hard_wall_missing():
    for code in (
        "episode_deadline_in_materialize",
        "episode_deadline_before_launch",
        "episode_deadline_in_bootstrap",
        "episode_deadline_during_model_call",
    ):
        assert FAILURE_CODE_TERMINATION_MAP[code] == ("hard_wall_timeout", "capture_incomplete")


# ---------------------------------------------------------------- materialize 到点：取消 + 回收


async def test_materialize_deadline_cancels_and_reclaims_container_and_network():
    chain = _formal_chain()  # fa_formal + profile：materialize 先建私网再 docker run
    entered = asyncio.Event()
    original_docker = chain.orchestrator._docker

    async def blocking_docker(*args, input_bytes=None):
        if args[0] == "run":
            entered.set()
            await asyncio.Event().wait()  # 永不返回，只能被取消（模拟 docker run 卡住）
        return await original_docker(*args, input_bytes=input_bytes)

    chain.orchestrator._docker = blocking_docker
    # 入口起表 t=0（deadline=900）；materialize 剩余 0.1s（让阶段真的开始并卡在 run）；之后过期
    chain.orchestrator._clock = _ticking_clock(0.0, BUDGET - 0.1, 5000.0)
    (aborted,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert entered.is_set() and aborted.remove_sample is True
    assert audit.episode_deadline["hit_by"] == "materialize"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert audit.outcome_v2["completion_class"] == "missing"
    assert audit.outcome_v2["reason_code"] == "episode_deadline_in_materialize"
    assert audit.outcome_v2["failure_category"] == "capture_incomplete"
    # 持有资源已收口：容器按名字 rm -f、私网拆除；harness 从未启动
    assert chain.docker.removed == [audit.lease.container_id]
    assert chain.docker.profile_fake.networks == {}
    assert audit.lease_released is True
    assert "materialize_cancelled_reclaimed" in _steps(audit)
    assert chain.driver.calls == []
    assert "cleanup_completed" in _steps(audit)
    assert chain.orchestrator.cleanup_quarantine == []


# ---------------------------------------------------------------- 准备阶段吃光预算：不启动 CC


async def test_budget_exhausted_before_launch_skips_session_and_harness():
    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    # 入口 t=0（deadline=900）；materialize 剩余 800；harness 启动前剩余 -4100
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 5000.0)
    (aborted,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert aborted.remove_sample is True
    assert chain.driver.calls == []  # CC 未启动
    assert chain.adapter_ref["adapter"].opened == []  # 会话未开
    assert audit.episode_deadline["hit_by"] == "before_launch"
    assert audit.episode_deadline["remaining_at_harness_start"] < 0
    assert audit.termination_kind_hint == "hard_wall_timeout"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert audit.outcome_v2["reason_code"] == "episode_deadline_before_launch"
    assert len(chain.docker.removed) == 1 and "cleanup_completed" in _steps(audit)


# ---------------------------------------------------------------- harness 运行到点：取消 harness task


class _HangingLaunchedDriver:
    """先喂完所有轮（模拟 CC 已启动并交互），再挂起等待取消。"""

    name = "mock_harness"

    def __init__(self, adapter_ref):
        self.adapter_ref = adapter_ref
        self.cancelled = False
        self.calls: list[dict] = []

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        self.calls.append({"time_budget_sec": time_budget_sec})
        HARNESS_LAUNCH_FACTS.get()["launch_attempted"] = True  # 进入上游 run；launched 保持未确认
        await self.adapter_ref["adapter"].run_all_turns()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


async def test_harness_outer_deadline_cancels_task_and_closes_as_hard_wall():
    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    driver = _HangingLaunchedDriver(chain.adapter_ref)
    chain.orchestrator._harness_driver = driver
    # 入口 t=0（deadline=900）；materialize 剩余 800；启动前剩余 800（vendored 兼容秒 = 800）；harness 等待剩余 0.1；之后过期
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, BUDGET - 0.1, 5000.0)
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert driver.cancelled is True
    assert driver.calls == [{"time_budget_sec": 800}]
    assert audit.harness_exit_code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED
    assert audit.episode_deadline["hit_by"] == "harness_outer"
    assert audit.episode_deadline["harness_launch_attempted"] is True
    assert audit.episode_deadline["harness_launched"] is None  # 未确认，不据此推导
    assert audit.episode_deadline["remaining_at_harness_exit"] < 0
    assert "episode_deadline_harness_cancelled" in _steps(audit)
    assert audit.termination_kind_hint == "hard_wall_timeout"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert audit.outcome_v2["completion_class"] == "missing"  # audit-only：屏障未落地
    assert "cleanup_completed" in _steps(audit) and len(chain.docker.removed) == 1


class _BootstrapStarvedDriver:
    """模拟真实驱动：引导吃光预算，CC 从未启动，回填 launch_attempted=False 并返回 -1
    （真实驱动经真实接缝的版本见 test_real_driver_cancelled_during_install_*）。"""

    name = "claude_code"
    calls: list = []

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        facts = HARNESS_LAUNCH_FACTS.get()
        facts.update(launch_attempted=False, launched=False, bootstrap_seconds=12.5, remaining_at_launch=-0.5)
        return HARNESS_EXIT_TIME_BUDGET_EXCEEDED


async def test_bootstrap_exhaustion_from_driver_facts_skips_drain_and_assembly():
    chain = build_dense_chain(config=_fa_cfg())
    _stamp_fa_identity(chain.base_sample)
    chain.orchestrator._harness_driver = _BootstrapStarvedDriver()
    (aborted,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert aborted.remove_sample is True
    assert audit.episode_deadline["hit_by"] == "bootstrap"
    assert audit.episode_deadline["harness_launch_attempted"] is False
    assert audit.episode_deadline["bootstrap_seconds"] == 12.5
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert audit.outcome_v2["reason_code"] == "episode_deadline_in_bootstrap"
    assert chain.adapter_ref["adapter"].finished == []  # 没有任何轮：不 drain / 不装配
    assert "cleanup_completed" in _steps(audit) and len(chain.docker.removed) == 1


# ---------------------------------------------------------------- proxy 因期限中毒：hard_wall 而非 api_failure


async def test_proxy_episode_deadline_poison_closes_as_hard_wall_not_api_failure():
    registry = SessionPoisonRegistry()
    started = asyncio.Event()
    adapter_ref: dict[str, MockSessionAdapter] = {}

    class PoisonedMidRunDriver:
        async def run(self, *args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()  # 只能被 poison 取消
            except asyncio.CancelledError:
                raise

    def adapter_factory(hook, session_defaults):
        adapter = MockSessionAdapter(hook, session_defaults, dense_turns(), [dense_leaf_sample()])
        adapter_ref["adapter"] = adapter
        return adapter

    docker = FakeRolloutDocker()
    orch = RolloutOrchestrator(
        config=_fa_cfg(),
        task_resolver=make_task(TASK_ID_DENSE),
        adapter_factory=adapter_factory,
        harness_driver=PoisonedMidRunDriver(),
        grading_submit=GradingSubmitStub(),
        docker=docker,
        session_poison_check=registry.is_poisoned,
        session_poison_subscribe=registry.subscribe,
        session_poison_unsubscribe=registry.unsubscribe,
        session_poison_reason=registry.reason,
    )
    sample = FixtureSlimeSample(index=0)
    _stamp_fa_identity(sample)

    async def poison_with_deadline_reason():
        await started.wait()
        (sid,) = registry._subscribers
        registry.poison(sid, "episode_deadline_exhausted")  # proxy 排队/发送中到点的真实原因码

    result, _ = await asyncio.gather(
        orch.generate(_Args(), sample, dict(SAMPLING_PARAMS)), poison_with_deadline_reason()
    )
    (aborted,) = result
    assert aborted.remove_sample is True
    audit = orch.audits[0]
    (failure,) = [f for f in audit.failure_records if f.stage == "harness_run"]
    assert "episode_deadline_during_model_call" in failure.detail
    assert audit.episode_deadline["hit_by"] == "proxy"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"  # 不是 api_failure
    assert audit.outcome_v2["failure_category"] == "capture_incomplete"
    assert audit.outcome_v2["completion_class"] == "missing"
    assert registry._subscribers == {} and len(docker.removed) == 1


async def test_other_poison_reasons_stay_api_failure():
    """对照：非期限原因的 poison 仍是 session_poisoned_during_execution → api_failure。"""

    registry = SessionPoisonRegistry()
    started = asyncio.Event()
    adapter_ref: dict[str, MockSessionAdapter] = {}

    class Driver:
        async def run(self, *args, **kwargs):
            started.set()
            await asyncio.Event().wait()

    def adapter_factory(hook, session_defaults):
        adapter = MockSessionAdapter(hook, session_defaults, dense_turns(), [dense_leaf_sample()])
        adapter_ref["adapter"] = adapter
        return adapter

    orch = RolloutOrchestrator(
        config=_fa_cfg(), task_resolver=make_task(TASK_ID_DENSE), adapter_factory=adapter_factory,
        harness_driver=Driver(), grading_submit=GradingSubmitStub(), docker=FakeRolloutDocker(),
        session_poison_check=registry.is_poisoned, session_poison_subscribe=registry.subscribe,
        session_poison_unsubscribe=registry.unsubscribe, session_poison_reason=registry.reason,
    )
    sample = FixtureSlimeSample(index=0)
    _stamp_fa_identity(sample)

    async def poison_other():
        await started.wait()
        (sid,) = registry._subscribers
        registry.poison(sid, "unattributable_model_call")

    await asyncio.gather(orch.generate(_Args(), sample, dict(SAMPLING_PARAMS)), poison_other())
    audit = orch.audits[0]
    assert audit.outcome_v2["termination_kind"] == "api_failure"
    assert audit.outcome_v2["reason_code"] == "session_poisoned_during_execution"
    assert audit.episode_deadline["hit_by"] == "none"


# ---------------------------------------------------------------- 期限不覆盖评分 / 清理


async def test_grading_and_cleanup_run_even_after_deadline_passed():
    chain = _formal_chain()
    # 入口 t=0；materialize / 启动前 / harness 等待都在预算内；harness 结束后时钟已越过期限
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, 100.0, 5000.0)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert audit.finalized is not None and chain.grading.calls  # 照常评分交付
    assert all(not getattr(x, "remove_sample", False) for x in delivered)
    assert audit.episode_deadline["remaining_at_harness_exit"] < 0  # 只是观测，不触发 hard wall
    assert audit.episode_deadline["hit_by"] == "none"
    assert audit.outcome_v2["termination_kind"] == "completed"
    assert audit.episode_deadline["budget_seconds"] == BUDGET
    assert "cleanup_completed" in _steps(audit)


# ---------------------------------------------------------------- docker_sandbox._run：取消时回收子进程


async def test_docker_sandbox_run_kills_and_waits_cli_on_cancel(monkeypatch):
    class FakeProc:
        returncode = None

        def __init__(self):
            self.killed = False
            self.waited = False
            self._block = asyncio.Event()

        async def communicate(self, input=None):
            await self._block.wait()
            return b"", b""

        def kill(self):
            self.killed = True
            self.returncode = -9
            self._block.set()

        async def wait(self):
            self.waited = True
            return self.returncode

    proc = FakeProc()

    async def fake_exec(*args, **kwargs):
        return proc

    monkeypatch.setattr(docker_sandbox.asyncio, "create_subprocess_exec", fake_exec)
    task = asyncio.create_task(docker_sandbox._run("exec", "c", "bash", "-c", "sleep 999"))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert proc.killed and proc.waited  # Codex R2 探针修前：kill_called=False, wait_called=False


# ---------------------------------------------------------------- 真实驱动：引导受剩余预算约束


async def test_driver_bootstrap_starved_returns_budget_exceeded_without_launching(monkeypatch):
    from slime.agent.harness import ClaudeCodeHarness

    async def install(self, sb, **kwargs):
        return None

    async def slow_run(*args, input_bytes=None, timeout=None):
        # 模拟 chown -R 很慢：按传入 timeout 到点返回 124（DockerSandbox.exec 会抛 SandboxExecError）
        await asyncio.sleep(min(2.0, float(timeout)))
        return 124, "", f"docker exec timeout after {timeout}s"

    async def must_not_launch(self, *a, **k):
        raise AssertionError("CC 不应启动")

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(docker_sandbox, "_run", slow_run)
    monkeypatch.setattr(ClaudeCodeHarness, "launch_and_wait", must_not_launch)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        code = await ClaudeCodeDriver().run(
            type("S", (), {"container_name": "c"})(), workdir="/testbed", session_id="tok",
            adapter_url="http://relay:1", time_budget_sec=1, prompt="p",
        )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED
    assert facts["launch_attempted"] is False and facts["launched"] is False
    assert facts["remaining_at_launch"] <= 0.05
    assert "bootstrap_exec_error" in facts  # useradd 超时 = 期限收缩所致，不算引导故障


async def test_driver_launches_with_remaining_budget_when_bootstrap_is_fast(monkeypatch):
    from slime.agent.harness import ClaudeCodeHarness

    async def install(self, sb, **kwargs):
        return None

    async def fast_run(*args, input_bytes=None, timeout=None):
        return 0, "", ""

    seen: dict = {}

    async def launch(self, sb, ctx, prompt, time_budget_sec):
        seen["time_budget_sec"] = time_budget_sec
        return 0

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(docker_sandbox, "_run", fast_run)
    monkeypatch.setattr(ClaudeCodeHarness, "launch_and_wait", launch)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        code = await ClaudeCodeDriver().run(
            type("S", (), {"container_name": "c"})(), workdir="/testbed", session_id="tok",
            adapter_url="http://relay:1", time_budget_sec=100, prompt="p",
        )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert code == 0 and facts["launch_attempted"] is True and facts["launched"] is None
    assert 0 < facts["remaining_at_launch"] <= 100
    assert seen["time_budget_sec"] in (99, 100)  # = max(1, int(剩余))


async def test_driver_bootstrap_failure_with_budget_left_is_still_bootstrap_failed(monkeypatch):
    """对照：期限没到时引导步骤失败仍是已归因 harness_bootstrap_failed（批 A 语义不变）。"""

    async def install(self, sb, **kwargs):
        return None

    async def failing_run(*args, input_bytes=None, timeout=None):
        return 1, "", "useradd: cannot lock /etc/passwd"

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(docker_sandbox, "_run", failing_run)
    with pytest.raises(SlimeBindingError, match=r"^\[harness_bootstrap_failed\]"):
        await ClaudeCodeDriver().run(
            type("S", (), {"container_name": "c"})(), workdir="/testbed", session_id="tok",
            adapter_url="http://relay:1", time_budget_sec=600, prompt="p",
        )


# ---------------------------------------------------------------- registry：期限显式下传


def test_per_rollout_adapter_passes_deadline_into_registry():
    registry = CaptureRegistry()

    class Shared:
        def open_session(self, sid, *, sampling_defaults=None, max_context_tokens=0):
            pass

    adapter = make_per_rollout_adapter(registry, Shared(), FakeHook())
    assert registry.session_deadline("sid_D") is None  # 无默认、未显式设定 → 不起表
    adapter.open_session("sid_D", physical_attempt_id="exec_D#p1-a", deadline_monotonic=4242.0)
    assert registry.session_deadline("sid_D") == 4242.0
    registry.unregister("sid_D")
    assert registry.session_deadline("sid_D") is None


# ================================================================ Codex 批 B 审查 R1/R2/R3 的真实接缝回归


async def test_census_blocked_past_deadline_is_cancelled_and_cleaned_without_owner(monkeypatch):
    """R1：HEAD / 基线 census 与物化同在一个期限内。真实 formal 入口、真实物化（CPU 替身 docker），
    只把 census 换成阻塞 IO，预算 1s：过墙后自动取消、不启动 CC、记 hard wall、容器自行清理，
    不需要 owner 再取消（修前：执行一直 pending、census 不取消、容器不删、hit_by=none）。"""

    import dataclasses

    from repoharness2.adapters.slime import baseline_census

    chain = _formal_chain()
    chain.orchestrator._task_resolver = dataclasses.replace(chain.orchestrator._task_resolver, time_budget_seconds=1)
    entered, cancelled = asyncio.Event(), asyncio.Event()

    async def blocking_census(*args, **kwargs):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(baseline_census, "generate_baseline_manifest", blocking_census)
    (aborted,) = await asyncio.wait_for(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=5
    )
    audit = chain.orchestrator.audits[0]
    assert entered.is_set() and cancelled.is_set()
    assert aborted.remove_sample is True
    assert audit.episode_deadline["hit_by"] == "materialize"
    assert audit.outcome_v2["reason_code"] == "episode_deadline_in_materialize"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert chain.driver.calls == []  # CC 未启动
    assert chain.docker.removed == [audit.lease.container_id] and audit.lease_released is True
    assert chain.docker.profile_fake.networks == {}
    assert "step2_workspace_materialized" in _steps(audit) and "cleanup_completed" in _steps(audit)


class _BlockedProcess:
    def __init__(self):
        self.entered = asyncio.Event()
        self.returncode = None
        self.kill_calls = 0
        self.wait_calls = 0

    async def communicate(self, input=None):
        self.entered.set()
        await asyncio.Event().wait()

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9

    async def wait(self):
        self.wait_calls += 1
        return self.returncode


async def test_manager_run_docker_kills_and_waits_cli_on_cancel(monkeypatch):
    """R2a：物化 / 评分默认 Docker 通道 `grading.manager.run_docker`（`generate.run_docker is manager.run_docker`）
    被取消时回收宿主 CLI 子进程（修前 kill/wait 均为 0，只有驱动的 `docker_sandbox._run` 做了）。"""

    from repoharness2.adapters.slime import generate as generate_mod
    from repoharness2.grading import manager

    assert generate_mod.run_docker is manager.run_docker
    proc = _BlockedProcess()

    async def spawn(*args, **kwargs):
        assert args[0] == "docker"
        return proc

    monkeypatch.setattr(manager.asyncio, "create_subprocess_exec", spawn)
    pending = asyncio.create_task(manager.run_docker("image", "inspect", "review-image"))
    await asyncio.wait_for(proc.entered.wait(), timeout=1)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(pending, timeout=1)
    assert proc.kill_calls == 1 and proc.wait_calls == 1


def _short_remaining_clock():
    return _ticking_clock(0.0, BUDGET - 0.05, 5000.0)


@pytest.mark.parametrize("stage", ["create", "connect", "run"])
async def test_deadline_during_materialize_io_reclaims_network_slot_and_container(stage):
    """R2b：从真实 formal 入口、真实 runner/helper，只让 Docker IO 在操作已生效、响应未返回时阻塞：
    建网中 / relay 接入中 / docker run 中被期限取消 → 网络删除、登记清空、地址池槽位归还、
    容器（若已建）按名字回收、无 cleanup 失败记录（修前：网络与槽位残留、登记漏清）。"""

    chain = _formal_chain()
    orch = chain.orchestrator
    original_docker = orch._docker
    entered = asyncio.Event()

    async def block_after_effect(*args, input_bytes=None):
        result = await original_docker(*args, input_bytes=input_bytes)
        if (stage in ("create", "connect") and args[:2] == ("network", stage)) or (stage == "run" and args[0] == "run"):
            entered.set()
            await asyncio.Event().wait()
        return result

    orch._docker = block_after_effect
    orch._clock = _short_remaining_clock()
    delivered = await asyncio.wait_for(orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=5)
    audit = orch.audits[-1]
    fake = chain.docker.profile_fake
    assert entered.is_set() and all(s.remove_sample for s in delivered)
    assert audit.outcome_v2["reason_code"] == "episode_deadline_in_materialize"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert fake.networks == {} and len(fake.removed_networks) == 1
    assert orch._attempt_networks == {}
    assert orch._egress_pool._in_use == set()  # 槽位归还
    assert audit.cleanup_failures == []
    run_calls = sum(args[0] == "run" for args in chain.docker.calls)
    if stage == "run":
        assert run_calls == 1 and chain.docker.removed == [audit.lease.container_id]
    else:
        assert run_calls == 0 and chain.docker.removed == []
    assert "cleanup_completed" in _steps(audit)


async def test_deadline_during_network_create_keeps_slot_when_rm_fails_and_records_it():
    """R2b 反例：取消后按预选名字 rm 失败（网络仍可能存在）→ 槽位**不**归还（标记占用）、cleanup_failures
    留痕、`egress_network_remove_failed` 事件；不盲目归还可能仍被占用的地址。"""

    chain = _formal_chain()
    orch = chain.orchestrator
    original_docker = orch._docker
    chain.docker.profile_fake.network_rm_fail_for = {"*"}

    async def block_after_effect(*args, input_bytes=None):
        result = await original_docker(*args, input_bytes=input_bytes)
        if args[:2] == ("network", "create"):
            await asyncio.Event().wait()
        return result

    orch._docker = block_after_effect
    orch._clock = _short_remaining_clock()
    await asyncio.wait_for(orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=5)
    audit = orch.audits[-1]
    assert len(chain.docker.profile_fake.networks) == 1  # daemon 里仍在（rm 失败）
    assert len(orch._egress_pool._in_use) == 1  # 槽位保持占用
    assert [f.step for f in audit.cleanup_failures] == ["remove_egress_network"]
    assert "network_rm_after_cancel" in audit.cleanup_failures[0].detail
    assert "egress_network_remove_failed" in _steps(audit)


async def test_real_driver_cancelled_during_install_is_known_not_launched(monkeypatch):
    """R3(1)：真实 ClaudeCodeDriver 在安装 CLI 时被编排的绝对期限取消 → 回填 launch_attempted=False →
    编排按 `episode_deadline_in_bootstrap` 收口、hit_by=bootstrap、不 drain / 不装配（修前：facts 为空、
    hit_by=harness_outer、drain 与 finish_session 各跑一次、以 no_capture_records 结束）。"""

    chain = _formal_chain()
    chain.orchestrator._harness_driver = ClaudeCodeDriver()
    entered = asyncio.Event()
    drain_calls: list = []
    original_drain = chain.orchestrator._session_drain_owner

    async def drain(sid):
        drain_calls.append(sid)
        return await original_drain(sid)

    chain.orchestrator._session_drain_owner = drain

    async def install(self, sb, **kwargs):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    # 入口 t=0；materialize 剩余 800；启动前剩余 800；harness 等待剩余 0.1 → 取消安装
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, BUDGET - 0.1, 5000.0)
    (aborted,) = await asyncio.wait_for(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=5
    )
    audit = chain.orchestrator.audits[0]
    assert entered.is_set() and aborted.remove_sample is True
    assert audit.episode_deadline["harness_launch_attempted"] is False
    assert audit.episode_deadline["harness_launched"] is False
    assert audit.episode_deadline["hit_by"] == "bootstrap"
    assert audit.outcome_v2["reason_code"] == "episode_deadline_in_bootstrap"
    assert audit.outcome_v2["termination_kind"] == "hard_wall_timeout"
    assert drain_calls == [] and chain.adapter_ref["adapter"].finished == []
    assert "cleanup_completed" in _steps(audit) and len(chain.docker.removed) == 1


async def test_fatal_raised_while_cancelling_bootstrap_propagates_as_fatal(monkeypatch):
    """§4：取消收口期间抛出的基建级致命错误不得被 `_settle_cancelled_stage` 吸收成次生记录。"""

    from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError

    chain = _formal_chain()
    chain.orchestrator._harness_driver = ClaudeCodeDriver()
    notified: list = []
    chain.orchestrator._notify_fatal_halt = notified.append

    async def install(self, sb, **kwargs):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise FatalExecutionInfrastructureError("probe_cancel_cleanup_fatal", "取消时的明确致命错误") from None

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, BUDGET - 0.1, 5000.0)
    with pytest.raises(FatalExecutionInfrastructureError, match="probe_cancel_cleanup_fatal"):
        await asyncio.wait_for(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=5)
    assert [n.reason_code for n in notified] == ["probe_cancel_cleanup_fatal"]
    assert "cleanup_completed" in _steps(chain.orchestrator.audits[0])


async def test_driver_fractional_budget_timeout_is_deadline_not_bootstrap_failure(monkeypatch):
    """R3(3)：预算 600s、安装花 0.3s → chown 的 timeout = 599.7（浮点，不取整）；到点时按"该步骤的
    timeout 由期限决定"判定为墙钟到点（返回 -1、launch_attempted=False），不是 harness_bootstrap_failed
    （修前：timeout 取整为 599，剩 0.7s 时被判成引导故障）。"""

    from types import SimpleNamespace

    from repoharness2.adapters.slime import bringup

    now = [0.0]
    seen: list[float] = []

    async def install(self, sb, **kwargs):
        now[0] += 0.3

    async def run(*args, timeout=None, **kwargs):
        seen.append(timeout)
        now[0] += timeout
        return 124, "", "按收到的 timeout 到点"

    monkeypatch.setattr(bringup, "time", SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(docker_sandbox, "_run", run)
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        code = await ClaudeCodeDriver().run(
            SimpleNamespace(container_name="cpu"), workdir="/testbed", session_id="s",
            adapter_url="http://cpu", time_budget_sec=600, prompt="p",
        )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert code == HARNESS_EXIT_TIME_BUDGET_EXCEEDED
    assert seen == [pytest.approx(599.7)]
    assert facts["launch_attempted"] is False and facts["bootstrap_deadline_reason"] == "bootstrap_step_timed_out_at_deadline"


# ================================================================ 批 D-2（I14 grading 侧）：终止失败穿队列 → run-fatal


async def test_grading_scope_termination_failure_is_run_fatal_with_cleanup(monkeypatch):
    """评分容器有界收口后仍运行 / 无法确认 → manager 抛 GradingScopeTerminationError（穿队列）→ 编排转
    FatalExecutionInfrastructureError（grading_scope_termination_failed）、通知 halt、failure_record
    stage=grading_cleanup；rollout 侧 finally 清理照常。不是 failed_to_grade 成员损耗。"""

    from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError
    from repoharness2.grading.manager import GradingScopeTerminationError

    chain = _formal_chain()
    notified: list = []
    chain.orchestrator._notify_fatal_halt = notified.append

    async def stuck_grader(**kw):
        raise GradingScopeTerminationError("grading_scope_termination_failed", "评分容器 x 在有界收口后状态仍为 running")

    chain.orchestrator._grading_submit = stuck_grader
    with pytest.raises(FatalExecutionInfrastructureError, match="grading_scope_termination_failed"):
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    assert [n.reason_code for n in notified] == ["grading_scope_termination_failed"]
    assert any(f.stage == "grading_cleanup" and f.error_type == "grading_scope_termination_failed" for f in audit.failure_records)
    assert "grading_scope_termination_failed" in _steps(audit)
    assert "cleanup_completed" in _steps(audit)


# ================================================================ Codex 联合审查 R2/R3：停止边界有界、停止事实与墙钟优先级


class _Budget:
    def __init__(self):
        self.states: dict = {}
        self.callbacks: dict = {}

    def subscribe(self, sid, cb):
        self.callbacks[sid] = cb

    def unsubscribe(self, sid):
        self.callbacks.pop(sid, None)

    def snapshot(self, sid):
        return self.states.get(sid)

    def exhaust(self, sid):
        self.states[sid] = {"cap": 3, "accepted": 3, "exhausted": True, "refused_count": 1}
        self.callbacks[sid](sid)


def _stop_chain(monkeypatch, *, kind: str, stop_timeout: float = 30.0):
    """真实 formal 编排 + 真实 DockerQuiescenceBarrier；只替换 Docker IO 与预算事件；可控时钟。
    kind 控制 kill / count 的时钟推进（Codex stop_deadline_probe 的形状）。"""

    from repoharness2.adapters.slime import generate as generate_mod
    from repoharness2.adapters.slime import quiescence_barrier
    from repoharness2.adapters.slime.quiescence_barrier import DockerQuiescenceBarrier

    chain = _formal_chain(barrier=DockerQuiescenceBarrier())
    orch, now, budget = chain.orchestrator, [0.0], _Budget()
    orch._clock = lambda: now[0]
    orch._turn_budget_subscribe = budget.subscribe
    orch._turn_budget_unsubscribe = budget.unsubscribe
    orch._turn_budget_snapshot = budget.snapshot
    monkeypatch.setattr(generate_mod, "TURN_BUDGET_EXIT_GRACE_SEC", 0.005)
    monkeypatch.setattr(generate_mod, "EXECUTION_SCOPE_STOP_TIMEOUT_SEC", stop_timeout)
    monkeypatch.setattr(quiescence_barrier, "_STOP_TOTAL_TIMEOUT_SECONDS", stop_timeout)
    facts = {"stop_entered": asyncio.Event(), "kill_effect_at": [], "confirmation_at": [], "driver_tasks": [],
             "driver_cancelled": asyncio.Event()}
    original_docker = orch._docker

    async def io(*args, input_bytes=None):
        if args[0] == "exec" and "pkill -9 -u agent" in args[-1]:
            first = not facts["stop_entered"].is_set()
            facts["stop_entered"].set()
            if kind.startswith("hang"):
                await asyncio.Event().wait()  # kill 通道持续挂起：强停与屏障 ① 各由自己的总预算收口
            if kind == "kill_effect_after_wall" and first:
                now[0] = 901.0  # kill 尚未实际生效，墙钟已过；agent 仍活着
            facts["kill_effect_at"].append(now[0])
        if args[0] == "exec" and "ps -o pid= -u agent" in args[-1]:
            if kind == "confirmation_after_wall":
                now[0] = 901.0  # 进程已在墙前停止，只是计数回包晚
            facts["confirmation_at"].append(now[0])
        return await original_docker(*args, input_bytes=input_bytes)

    class Driver:
        name = "cpu_stop_probe"

        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            facts["driver_tasks"].append(asyncio.current_task())
            adapter = chain.adapter_ref["adapter"]
            await adapter.run_all_turns()
            now[0] = 899.5
            if kind == "hang_hard_wall":
                now[0] = 900.1
                return -1
            budget.exhaust(adapter.opened[-1])
            try:
                await asyncio.Event().wait()
            finally:
                facts["driver_cancelled"].set()

    orch._docker = io
    orch._harness_driver = Driver()
    return chain, now, facts


@pytest.mark.parametrize(
    ("kind", "expected_kind", "expected_exit", "kill_before_deadline"),
    [
        ("stop_before_wall", "max_turns_exhausted", -2, True),
        ("kill_effect_after_wall", "hard_wall_timeout", -1, False),
        ("confirmation_after_wall", "max_turns_exhausted", -2, True),
    ],
)
async def test_stop_facts_decide_keep_vs_hard_wall(monkeypatch, kind, expected_kind, expected_exit, kill_before_deadline):
    """R3 三案（Codex stop_deadline_probe）：墙前停 → KEEP（max_turns）；kill 在墙后才生效 → 到点时执行仍在
    进行 = hard wall（DROP，cap 事实保留）；墙前已停、只是归零确认晚 → 仍 KEEP。判据 = kill 命令返回时刻
    是否 ≤ 期限，不是"最后一次看时间是否已过"。"""

    from repoharness2.adapters.slime import generate as generate_mod

    chain, now, facts = _stop_chain(monkeypatch, kind=kind)
    delivered = await asyncio.wait_for(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=10
    )
    audit = chain.orchestrator.audits[0]
    stop = audit.termination["stop"]
    assert audit.runtime_quiescence_confirmed is True and chain.grading.calls  # 真实屏障通过、评分一次
    assert audit.harness_exit_code == expected_exit
    assert audit.outcome_v2["termination_kind"] == expected_kind
    assert audit.outcome_v2["completion_class"] == "present_truncated"
    assert audit.termination["turn_budget"]["exhausted"] is True  # cap 事实保留
    assert stop["kill_returned_before_deadline"] is kill_before_deadline
    assert stop["stop_timed_out"] is False and stop["kill_verified"] is True
    if kind == "confirmation_after_wall":
        assert stop["confirmed_at_monotonic"] == 901.0 and stop["kill_returned_at_monotonic"] == 899.5
    if expected_kind == "hard_wall_timeout":
        assert audit.episode_deadline["hit_by"] == "harness_outer"
        assert stop["requested_by"] == "hard_wall" and "hard_wall_after_forced_stop" in _steps(audit)
        assert facts["kill_effect_at"][0] == 901.0  # 首次 kill（预算强停）在墙后才生效；屏障复核的 kill 在其后
    else:
        assert stop["requested_by"] == "turn_budget"
    assert all(not getattr(x, "remove_sample", False) for x in delivered)
    assert audit.harness_exit_code != generate_mod.HARNESS_EXIT_TIME_BUDGET_EXCEEDED or expected_exit == -1


@pytest.mark.parametrize("kind", ["hang_turn_stop", "hang_hard_wall"])
async def test_forced_stop_io_hang_is_bounded_by_stop_budget(monkeypatch, kind):
    """R2：kill 通道挂起时强停在 EXECUTION_SCOPE_STOP_TIMEOUT_SEC 内返回（未确认 → 屏障 ① 同样按其总预算
    fail-closed → missing），generate 自行结束、drain 与清理照常，不需要外部取消（修前永久 pending）。"""

    chain, now, facts = _stop_chain(monkeypatch, kind=kind, stop_timeout=0.2)
    started = asyncio.get_running_loop().time()
    delivered = await asyncio.wait_for(
        chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=10
    )
    elapsed = asyncio.get_running_loop().time() - started
    audit = chain.orchestrator.audits[0]
    stop = audit.termination["stop"]
    assert facts["stop_entered"].is_set()
    assert stop["forced"] is True and stop["stop_timed_out"] is True and stop["kill_returned_at_monotonic"] is None
    assert stop["kill_verified"] is False and stop["residual_processes"] == -1
    assert elapsed < 5.0
    assert audit.runtime_quiescence_confirmed is False  # 未确认停止 → 屏障 fail-closed，不评分
    assert chain.grading.calls == [] and all(getattr(x, "remove_sample", False) for x in delivered)
    assert "cleanup_completed" in _steps(audit) and len(chain.docker.removed) == 1
    assert all(t.done() for t in facts["driver_tasks"])


async def test_parent_cancel_during_forced_stop_settles_harness_task(monkeypatch):
    """R2 附带：强停 await 期间父任务（编排）被取消 → 仍持有的 harness task 先被取消并 settle，再传播。"""

    chain, now, facts = _stop_chain(monkeypatch, kind="hang_turn_stop", stop_timeout=30.0)
    running = asyncio.create_task(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
    await asyncio.wait_for(facts["stop_entered"].wait(), timeout=5)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(running, timeout=5)
    assert facts["driver_cancelled"].is_set()
    assert all(t.done() for t in facts["driver_tasks"])  # 修前：harness task 仍 pending，需探针单独收掉
