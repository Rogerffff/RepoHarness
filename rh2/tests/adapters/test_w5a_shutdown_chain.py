"""W5a 关停链验收（普通 lane，不需要 vendor slime）。

对应 06 计划 W5a 行验收项：
- 正常关闭：全部组件关闭 + 幂等（同一报告对象、组件不二次 stop）；
- 异常关闭：run-fatal 通道触发关停链，首因保留，慢组件超时记次生、后续步照跑；
- 关闭后禁 submit：task_resolve / grading_submit / BringupService.get / HTTP guard /
  registry.register / grading manager 各拒绝点 typed（ServiceClosedError）；
- flush 失败仍清理：事件文件、报告文件、资源闭包文件全部不可写时 cleanup 步照做；
- 有界超时真触发：慢 close 替身 sleep 远超上界，链在上界内继续；
- 在飞执行取消：真实 RolloutOrchestrator（fa_formal）被取消后 receipt 先于容器清理
  落盘（B5 顺序不变），关停只记 owner_cancelled/missing 事实、不做 disposition；
- SIGTERM 真触发关停链，关停后恢复默认信号处置。
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    TASK_ID_DENSE,
    FakeFinalizationStore,
    MockClaudeCodeDriver,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
    make_task,
)

from repoharness2.adapters.slime import bringup  # noqa: E402
from repoharness2.adapters.slime.async_worker import (  # noqa: E402
    FatalExecutionInfrastructureError,
    fatal_halt_notifier,
)
from repoharness2.adapters.slime.capture_wire import (  # noqa: E402
    CaptureRegistry,
    build_session_guard_middleware,
)
from repoharness2.adapters.slime.generate import QuiescenceConfirmed, RolloutOrchestrator  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    ExecResult,
    GradingManagerConfig,
    SWEGradingManager,
    _ContainerRecord,
)
from repoharness2.grading.queue import GradingQueue, GradingQueueConfig  # noqa: E402
from repoharness2.shutdown import (  # noqa: E402
    CANCELLED_EXECUTION_TERMINATION_KIND,
    LifecycleState,
    ServiceClosedError,
    ShutdownStep,
    ShutdownTimeouts,
    Skipped,
    close_inflight_executions,
    run_shutdown_chain,
)

FAST = ShutdownTimeouts(
    inflight_grace=0.05,
    inflight_cancel_wait=3.0,
    grading_drain=2.0,
    grading_manager=2.0,
    capture_sessions=2.0,
    adapter_http=2.0,
    container_residue=1.0,
    resource_closure=10.0,
    evidence=1.0,
)


# ---------------------------------------------------------------------------
# 替身
# ---------------------------------------------------------------------------


class _FakeDockerRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.removed: list[str] = []

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        if args[0] == "rm":
            self.removed.append(args[-1])
        return ExecResult(0, "", "")


class _FakeThread:
    def __init__(self) -> None:
        self.alive = True

    def is_alive(self) -> bool:
        return self.alive


class _FakeAppHandle:
    """AppHandle 形状（thread/stop）；stop_delay 模拟阻塞的 runner.cleanup。"""

    def __init__(self, *, stop_delay: float = 0.0) -> None:
        self.thread = _FakeThread()
        self.stop_calls = 0
        self.stop_delay = stop_delay
        self.port = 0

    def stop(self) -> None:
        self.stop_calls += 1
        if self.stop_delay:
            time.sleep(self.stop_delay)
        self.thread.alive = False


class _FakeSharedAdapter:
    def __init__(self, *, drop_delay: float = 0.0) -> None:
        self.dropped: list[str] = []
        self.drop_delay = drop_delay

    async def drop_session(self, sid: str, *, wait_timeout: float = 5.0) -> None:
        if self.drop_delay:
            await asyncio.sleep(self.drop_delay)
        self.dropped.append(sid)


class _FrozenWs:
    def __init__(self, underlying: Any) -> None:
        self._u = underlying

    async def run_bash(self, script: str):
        return await self._u.run_bash(script)


class _Barrier:
    async def establish(self, *, workspace, audit):
        return QuiescenceConfirmed(
            frozen_grading_workspace=_FrozenWs(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",)
        )


class _BlockingDriver(MockClaudeCodeDriver):
    """harness 替身：进入后挂起直到被取消（模拟关停时刻仍在跑的 CC）。"""

    def __init__(self, adapter_ref: dict[str, Any]) -> None:
        super().__init__(adapter_ref)
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt) -> int:
        self.entered.set()
        await self.release.wait()
        await self.adapter_ref["adapter"].run_all_turns()
        return 0


def _record(name: str) -> _ContainerRecord:
    return _ContainerRecord(
        name=name, trajectory_id="traj", created_epoch=time.time(), created_monotonic=time.monotonic()
    )


def _assemble_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    timeouts: ShutdownTimeouts = FAST,
    adapter: Any = None,
    app_handle: Any = None,
    orchestrator: Any = None,
    profile_args: Any = None,
) -> tuple[Any, _FakeDockerRunner]:
    """按 BringupService.__init__ 的属性面装配一个不起 tokenizer/adapter 线程的服务
    对象（__init__ 只是组件构造；关停链读的属性在这里逐个给出）。"""

    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(bringup, "ARTIFACT_DIR", artifact_dir)
    service = object.__new__(bringup.BringupService)
    # codex Wave3 §9.4：owner loop = 装配本服务的那个 loop（生产里 = miles 共享后台 loop）。
    # 真实 __init__ 第一件事就是绑它；`object.__new__` 装配必须自己补上，否则 run-fatal 派发
    # 会退回"就地执行"，双 loop 反例就测不到东西。
    service._owner_loop = None
    service._bind_owner_loop()
    service.shutdown_timeouts = timeouts
    service.lifecycle = LifecycleState()
    service.lifecycle.on_fatal = service._on_run_fatal
    service._close_task = None
    service.shutdown_report = None
    service._fatals_during_close = []
    service._closing_report = None
    service._pending_late_facts = []
    service._deferred_residues = []
    service._uninstall_signal_shutdown = None
    service._profile_args = profile_args or SimpleNamespace(
        rollout_batch_size=2,
        n_samples_per_prompt=2,
        num_rollout=3,
        rollout_max_response_len=1024,
        async_max_concurrent_samples=None,
    )
    service.registry = CaptureRegistry()
    service.adapter = adapter or _FakeSharedAdapter()
    service.app_handle = app_handle or _FakeAppHandle()
    docker = _FakeDockerRunner()
    service.grading_manager = SWEGradingManager(
        GradingManagerConfig(), docker=docker, stop_requested=service._grading_stop_requested  # R4：与生产接线一致
    )
    service.grading_queue = GradingQueue(
        service.grading_manager, GradingQueueConfig(concurrency=1, queue_size=2)
    )
    service._queue_started = False
    service.events_path = artifact_dir / "bringup_events.jsonl"
    service.orchestrator = orchestrator
    service.engine_sampling_mask = False
    service.max_context_len = 0
    service.prepared_face = None
    service.attempt_assignments = None
    service.task_specs = {}
    service.inject_marker = artifact_dir / "infra_injection_fired.marker"
    return service, docker


# ---------------------------------------------------------------------------
# 1. 通用执行器：有界超时、首因、次生、evidence 不阻断
# ---------------------------------------------------------------------------


async def test_chain_bounded_timeout_first_cause_and_continuation():
    ran: list[str] = []

    async def ok():
        ran.append("ok")
        return {"x": 1}

    async def slow():  # 慢 close 替身：远超上界
        await asyncio.sleep(10)

    async def boom():
        raise RuntimeError("component exploded")

    async def evidence_boom():
        raise OSError("disk full")

    async def last():
        ran.append("last")

    steps = [
        ShutdownStep("ok", ok, 1.0),
        ShutdownStep("slow", slow, 0.2),
        ShutdownStep("boom", boom, 1.0),
        ShutdownStep("evidence", evidence_boom, 1.0, kind="evidence"),
        ShutdownStep("last", last, 1.0),
    ]
    t0 = time.monotonic()
    report = await run_shutdown_chain(steps, reason="t", trigger="owner_close")
    assert time.monotonic() - t0 < 2.0  # 有界：slow 在 0.2s 上界被截断
    assert ran == ["ok", "last"]  # 失败/超时之后的步骤照跑
    assert {s.name: s.status for s in report.steps} == {
        "ok": "ok", "slow": "timeout", "boom": "failed", "evidence": "failed", "last": "ok",
    }
    assert report.step("slow").seconds < 1.0
    assert report.step("ok").facts == {"x": 1}
    assert report.first_cause_origin == "step:slow"  # 无触发异常：第一个失败步是首因
    assert len(report.secondary_failures) == 2
    assert report.secondary_failures[0].startswith("step:boom")
    assert report.secondary_failures[1].startswith("step:evidence")
    assert report.evidence_failures == [report.secondary_failures[1]]
    assert not report.ok and not report.cleanup_clean

    # 触发异常在场：它才是首因，步失败全部次生
    fatal = FatalExecutionInfrastructureError("audit_store_down", "disk gone")
    report2 = await run_shutdown_chain(steps, reason="t", trigger="run_fatal", first_cause=fatal)
    assert report2.first_cause_origin == "trigger"
    assert "FatalExecutionInfrastructureError(audit_store_down)" in report2.first_cause
    assert report2.secondary_failures[0].startswith("step:slow")
    assert len(report2.secondary_failures) == 3


async def test_chain_evidence_failure_does_not_block_cleanup_and_skips_are_not_failures():
    cleaned: list[str] = []

    async def evidence_fail():
        raise OSError("events file unwritable")

    async def cleanup():
        cleaned.append("containers")

    async def skip():
        return Skipped("queue never started")

    report = await run_shutdown_chain(
        [
            ShutdownStep("evidence_begin", evidence_fail, 1.0, kind="evidence"),
            ShutdownStep("cleanup", cleanup, 1.0),
            ShutdownStep("skip", skip, 1.0),
        ],
        reason="t",
        trigger="owner_close",
    )
    assert cleaned == ["containers"]
    assert report.cleanup_clean and report.residue_free
    assert not report.ok  # evidence 写失败 = 资格作业失败（就绪稿 §2.6），但清理已做
    assert report.evidence_failures and report.first_cause_origin == "step:evidence_begin"
    assert report.step("skip").status == "skipped"


def test_shutdown_timeouts_from_env():
    t = ShutdownTimeouts.from_env({"RH2_SHUTDOWN_INFLIGHT_GRACE_SEC": "3", "RH2_SHUTDOWN_EVIDENCE_SEC": "0.5"})
    assert t.inflight_grace == 3.0 and t.evidence == 0.5 and t.grading_drain == 60.0
    with pytest.raises(ValueError):
        ShutdownTimeouts.from_env({"RH2_SHUTDOWN_INFLIGHT_GRACE_SEC": "fast"})
    with pytest.raises(ValueError):
        ShutdownTimeouts.from_env({"RH2_SHUTDOWN_ADAPTER_HTTP_SEC": "-1"})


# ---------------------------------------------------------------------------
# 2. LifecycleState：门 + 在飞表 + run-fatal 通道
# ---------------------------------------------------------------------------


async def test_lifecycle_state_gates_and_inflight_table():
    state = LifecycleState()

    async def execution(meta):
        fact = state.enter_execution(meta, task_id="tid")
        assert fact.physical_attempt_id == "p1" and fact.rollout_execution_id == "e1" and fact.task_id == "tid"
        await asyncio.sleep(0.05)
        assert state.exit_execution() is fact

    t = asyncio.create_task(execution({"rh2_physical_attempt_id": "p1", "rh2_rollout_execution_id": "e1"}))
    await asyncio.sleep(0)
    assert state.inflight_count == 1
    await t
    assert state.inflight_count == 0

    state.stop_intake()
    with pytest.raises(ServiceClosedError) as ei:
        state.enter_execution({})
    assert ei.value.face == "task_resolve"
    assert ei.value.reason_code == "task_resolve_rejected_service_closed"
    state.require_grading_open()  # 评分面独立：停收新执行时仍开（在飞执行要交评分）
    state.close_grading()
    with pytest.raises(ServiceClosedError) as ei2:
        state.require_grading_open()
    assert ei2.value.reason_code == "grading_submit_rejected_service_closed"
    assert state.rejected_after_close == {"task_resolve": 1, "grading_submit": 1}


async def test_fatal_channel_reaches_lifecycle_notifier_and_chains_previous():
    state = LifecycleState()
    seen: list[BaseException] = []
    state.on_fatal = seen.append
    previous_calls: list[BaseException] = []

    async def body():
        fatal_halt_notifier.set(previous_calls.append)  # 模拟 worker 已装的通知器
        state.enter_execution({"rh2_physical_attempt_id": "p1"})
        state.enter_execution({"rh2_physical_attempt_id": "p1"})  # 同 task 再进：不叠链
        exc = FatalExecutionInfrastructureError("audit_down", "x")
        RolloutOrchestrator._notify_fatal_halt(exc)  # generate.py 的既有 Fatal 分支调用点
        return exc

    exc = await asyncio.create_task(body())
    assert seen == [exc] and previous_calls == [exc] and state.fatal_seen == [exc]


# ---------------------------------------------------------------------------
# 3. 在飞执行：先等、后取消、再等；真实 orchestrator 取消 = receipt 先于 cleanup
# ---------------------------------------------------------------------------


async def test_inflight_grace_lets_execution_finish_without_cancel():
    state = LifecycleState()

    async def quick():
        state.enter_execution({})
        await asyncio.sleep(0.05)
        state.exit_execution()

    t = asyncio.create_task(quick())
    await asyncio.sleep(0)
    facts = await close_inflight_executions(state, grace_seconds=2.0, cancel_wait_seconds=1.0)
    assert facts == {
        "inflight_at_shutdown": 1, "finished_in_grace": 1, "cancelled": [], "unfinished_after_cancel_wait": [],
    }
    assert t.done() and not t.cancelled()


async def test_inflight_unfinished_after_cancel_wait_is_reported_as_residue():
    state = LifecycleState()
    started = asyncio.Event()

    async def stubborn():
        state.enter_execution({"rh2_physical_attempt_id": "p-stubborn"})
        started.set()
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            await asyncio.sleep(30)  # 吞掉取消：模拟卡死的清理

    t = asyncio.create_task(stubborn())
    await started.wait()
    t0 = time.monotonic()
    facts = await close_inflight_executions(state, grace_seconds=0.05, cancel_wait_seconds=0.1)
    assert time.monotonic() - t0 < 1.0
    [u] = facts["unfinished_after_cancel_wait"]
    assert u["physical_attempt_id"] == "p-stubborn" and u["finished_after_cancel"] is False
    assert facts["cancelled"] == [u]
    t.cancel()
    await asyncio.gather(t, return_exceptions=True)


async def test_inflight_cancel_persists_receipt_before_cleanup_and_records_owner_cancelled():
    state = LifecycleState()
    store = FakeFinalizationStore()
    turns = dense_turns()
    for turn in turns:
        turn.response["meta_info"]["weight_version"] = "5"
    task_spec = make_task(TASK_ID_DENSE)

    def resolver(sample):  # = BringupService._resolve_task 的登记形状
        state.enter_execution(getattr(sample, "metadata", None), task_id=task_spec.task_id)
        return task_spec

    chain = build_dense_chain(
        config=_formal_config(execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(),
        turns=turns,
        finalization_store=store,
        task=resolver,
    )
    _stamp_fa_identity(chain.base_sample)
    driver = _BlockingDriver(chain.adapter_ref)
    chain.orchestrator._harness_driver = driver
    orig_docker = chain.orchestrator._docker

    async def logging_docker(*args, **kw):
        if args and args[0] == "rm":
            store.call_order.append("docker_rm")
        return await orig_docker(*args, **kw)

    chain.orchestrator._docker = logging_docker

    run = asyncio.create_task(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
    await asyncio.wait_for(driver.entered.wait(), 5)
    assert state.inflight_count == 1

    facts = await close_inflight_executions(state, grace_seconds=0.05, cancel_wait_seconds=5.0)
    assert run.done() and run.cancelled()
    assert facts["inflight_at_shutdown"] == 1 and facts["finished_in_grace"] == 0
    [fact] = facts["cancelled"]
    assert fact["termination_kind"] == CANCELLED_EXECUTION_TERMINATION_KIND == "owner_cancelled"
    assert fact["completion_class"] == "missing"
    assert fact["finished_after_cancel"] is True
    assert fact["physical_attempt_id"] == "exec_F22#p1-cafe1234"
    assert fact["rollout_execution_id"] == "exec_F22"
    assert facts["unfinished_after_cancel_wait"] == []
    # 事实里没有任何处置词根（A5 归 C，关停只记事实）
    assert not any(any(w in key for w in ("disposition", "keep", "drop", "admission")) for key in fact)
    # B5 顺序不变：取消路径 receipt（disposition=cancelled）先持久化，容器再清理
    order = store.call_order
    assert order.index("persist_receipt") < order.index("docker_rm")
    [receipt] = store.receipts
    assert receipt.attempt_disposition == "cancelled" and receipt.terminal_reason_code == "cancelled"
    assert receipt.outcome_v2 is None  # 关停取消不产 Outcome v2
    assert chain.docker.removed  # 容器确实清了
    assert chain.adapter_ref["adapter"].dropped  # 会话确实 drop 了


# ---------------------------------------------------------------------------
# 4. BringupService.close：正常 / 幂等 / 关闭后禁 submit / 各组件真关
# ---------------------------------------------------------------------------


async def test_bringup_close_normal_closes_all_components_and_is_idempotent(tmp_path, monkeypatch):
    service, docker = _assemble_service(tmp_path, monkeypatch)
    await service.grading_queue.start()
    service._queue_started = True
    service.grading_manager._records.append(_record("rh2-grading-open-1"))
    service.registry.register("s-stale", object())  # audit sink 没走到的异常路径残留的 session
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    monkeypatch.setattr(bringup.BringupService, "_startup_state", "RUNNING")
    monkeypatch.setattr(bringup, "_SERVICE_LOCK", asyncio.Lock())

    report = await service.close(reason="test_normal")
    assert report.ok, report.to_dict()
    assert report.trigger == "owner_close" and report.first_cause is None
    assert all(s.status in ("ok", "skipped") for s in report.steps)
    assert [s.name for s in report.steps] == [
        "intake_stop", "evidence_begin", "inflight_executions", "grading_queue", "grading_manager",
        "capture_sessions", "capture_registry_close", "adapter_http", "container_residue",
        "egress_runtime",  # W3b：attempt 网络 + relay 清理（s1_compat 下如实 skipped）
        "resource_closure",
    ]
    # 组件真关
    assert service.grading_queue._workers == []
    assert service.grading_manager.closed and docker.removed == ["rh2-grading-open-1"]
    assert service.adapter.dropped == ["s-stale"] and "s-stale" not in service.registry.hooks
    assert service.registry.closed
    assert service.app_handle.stop_calls == 1 and not service.app_handle.thread.is_alive()
    assert service.lifecycle.closed and not service.lifecycle.accepting and not service.lifecycle.grading_open
    assert bringup.BringupService._startup_state == "CLOSED"
    # evidence
    events = [json.loads(line) for line in service.events_path.read_text(encoding="utf-8").splitlines()]
    assert [e["event"] for e in events] == ["shutdown_started", "shutdown_completed"]
    written = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert written["ok"] is True and written["schema_id"] == "rh2.shutdown_report.v1"
    closure = json.loads((bringup.ARTIFACT_DIR / "resource_closure.json").read_text(encoding="utf-8"))
    assert closure["memory_estimate"]["status"] == "unbounded_or_unknown"
    assert closure["memory_estimate"]["estimate_bytes"] > 0
    assert closure["growth_collections"]["grading_manager_records"]["length"] == 1
    # 幂等：同一报告对象，组件不二次 stop
    report2 = await service.close(reason="again")
    assert report2 is report and service.app_handle.stop_calls == 1
    assert (await bringup.close_bringup_service()) is report
    # 关闭后禁 submit：任务面 / 评分面 / 单例入口
    with pytest.raises(ServiceClosedError) as ei:
        service._resolve_task(SimpleNamespace(metadata={"instance_id": "x"}))
    assert ei.value.reason_code == "task_resolve_rejected_service_closed"
    with pytest.raises(ServiceClosedError) as ei2:
        await service._grading_submit(trajectory_id="t", workspace=None, spec=SimpleNamespace(task_id="x"))
    assert ei2.value.reason_code == "grading_submit_rejected_service_closed"
    with pytest.raises(ServiceClosedError) as ei3:
        await bringup.BringupService.get(SimpleNamespace())
    assert ei3.value.face == "bringup_get"
    assert service.lifecycle.rejected_after_close == {"task_resolve": 1, "grading_submit": 1}


async def test_registry_closed_rejects_register_and_http_guard():
    registry = CaptureRegistry()
    registry.register("s-1", object())
    assert registry.close() == 1  # 关闭时刻仍注册的 hook 数（残留事实）
    with pytest.raises(ServiceClosedError) as ei:
        registry.register("s-2", object())
    assert ei.value.face == "capture_register"
    guard = build_session_guard_middleware(registry)
    called: list[Any] = []

    async def handler(request):
        called.append(request)
        return "unreachable"

    resp = await guard(SimpleNamespace(path="/v1/messages", headers={"Authorization": "Bearer s-1"}), handler)
    assert resp.status == 403 and called == []
    assert "rh2_service_closed" in resp.text and resp.headers["x-should-retry"] == "false"
    assert await guard(SimpleNamespace(path="/healthz", headers={}), handler) == "unreachable"


async def test_grading_manager_close_gcs_records_and_rejects_grade():
    docker = _FakeDockerRunner()
    manager = SWEGradingManager(GradingManagerConfig(), docker=docker)
    manager._records.append(_record("rh2-grading-a"))
    facts = await manager.close()
    assert facts["containers_removed"] == ["rh2-grading-a"] and facts["containers_open"] == []
    assert manager.closed and docker.removed == ["rh2-grading-a"]
    with pytest.raises(ServiceClosedError) as ei:
        await manager.grade(trajectory_id="t", workspace=None, spec=SimpleNamespace(task_id="x"))
    assert ei.value.face == "grading_manager_grade"
    assert (await manager.close())["containers_removed"] == []  # 幂等


async def test_close_bringup_service_without_instance_returns_none(monkeypatch):
    monkeypatch.setattr(bringup.BringupService, "_instance", None)
    assert await bringup.close_bringup_service() is None


# ---------------------------------------------------------------------------
# 5. 负例：flush 失败仍清理；异常关闭首因保留 + 慢组件超时次生
# ---------------------------------------------------------------------------


async def test_bringup_close_evidence_failures_do_not_block_cleanup(tmp_path, monkeypatch):
    service, docker = _assemble_service(tmp_path, monkeypatch)
    service.events_path.mkdir()  # 目录：append 必失败
    (bringup.ARTIFACT_DIR / "shutdown_report.json").mkdir()  # 原子 replace 到目录必失败
    (bringup.ARTIFACT_DIR / "resource_closure.json").mkdir()
    service.grading_manager._records.append(_record("rh2-grading-open-2"))
    service.registry.register("s-left", object())

    report = await service.close(reason="flush_negative")
    assert not report.ok
    assert report.cleanup_clean and report.residue_free  # 清理一步没少
    assert docker.removed == ["rh2-grading-open-2"]
    assert service.adapter.dropped == ["s-left"] and service.registry.closed
    assert service.app_handle.stop_calls == 1 and service.grading_manager.closed
    origins = {f.split(": ", 1)[0] for f in report.evidence_failures}
    assert origins == {
        "step:evidence_begin", "step:resource_closure", "evidence:shutdown_report", "evidence:shutdown_completed_event",
    }
    assert report.first_cause_origin == "step:evidence_begin"
    assert report.step("resource_closure").status == "failed"
    assert service.shutdown_report is report and service.lifecycle.closed


async def test_bringup_close_fatal_first_cause_kept_slow_component_timeout_secondary(tmp_path, monkeypatch):
    slow_adapter = _FakeSharedAdapter(drop_delay=30.0)  # 慢 close 替身
    timeouts = ShutdownTimeouts(
        inflight_grace=0.05, inflight_cancel_wait=2.0, grading_drain=1.0, grading_manager=1.0,
        capture_sessions=0.3, adapter_http=1.0, container_residue=1.0, resource_closure=10.0, evidence=1.0,
    )
    service, docker = _assemble_service(tmp_path, monkeypatch, adapter=slow_adapter, timeouts=timeouts)
    service.registry.register("s-stuck", object())
    fatal = FatalExecutionInfrastructureError("audit_store_down", "disk gone")

    async def failing_execution():  # run-fatal 通道：从执行 task 内部通知（generate.py 的调用形状）
        service.lifecycle.enter_execution({"rh2_physical_attempt_id": "p-fatal"})
        RolloutOrchestrator._notify_fatal_halt(fatal)
        raise fatal

    task = asyncio.create_task(failing_execution())
    await asyncio.gather(task, return_exceptions=True)
    assert service._close_task is not None  # 通知器已调度关停链，无需外部 close 调用

    t0 = time.monotonic()
    report = await service.close()
    assert time.monotonic() - t0 < 5.0  # 有界：慢 drop 在 0.3s 上界被截断
    assert report.trigger == "run_fatal" and report.reason == "run_fatal:audit_store_down"
    assert report.first_cause_origin == "trigger" and "audit_store_down" in report.first_cause
    step = report.step("capture_sessions")
    assert step.status == "timeout" and step.seconds < 1.5
    assert any(s.startswith("step:capture_sessions") for s in report.secondary_failures)
    # 拆步的意义：drop 超时不影响 registry 关闭；后续步照跑
    assert report.step("capture_registry_close").status == "ok" and service.registry.closed
    assert "s-stuck" not in service.registry.hooks  # 超时取消后 finally 仍注销
    assert report.step("adapter_http").status == "ok" and service.app_handle.stop_calls == 1
    assert not report.ok and service.lifecycle.fatal_seen == [fatal]
    assert service.shutdown_report is report


# ---------------------------------------------------------------------------
# 5b. codex W5a 复核 #3：两条假绿路径 + 执行外 fatal 的进程级通知入口
# ---------------------------------------------------------------------------


async def test_completed_event_write_failure_is_reflected_in_disk_report(tmp_path, monkeypatch):
    """假绿 (a)：此前先落盘报告再写完成事件——事件写失败只留在内存报告，磁盘报告仍 ok。
    现在磁盘报告最后生成，必须带上该失败且 ok=false。"""

    service, _docker = _assemble_service(tmp_path, monkeypatch)
    original = service._append_event

    def flaky_append(event):
        if event.get("event") == "shutdown_completed":
            raise OSError("events file vanished between begin and completed")
        return original(event)

    service._append_event = flaky_append
    report = await service.close(reason="completed_event_negative")
    assert not report.ok
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False
    assert any(f.startswith("evidence:shutdown_completed_event") for f in disk["evidence_failures"])
    assert disk["first_cause_origin"] == "evidence:shutdown_completed_event"
    assert disk["first_cause"] == report.first_cause
    # 清理本身没少
    assert report.cleanup_clean and service.registry.closed and service.app_handle.stop_calls == 1


async def test_run_fatal_during_close_lands_in_final_report(tmp_path, monkeypatch):
    """假绿 (b)：关停进行中到达的 run-fatal 此前被 `_on_run_fatal` 直接 return 丢掉，最终
    报告可能 ok=true/first_cause=None。现在：首因为空则成为首因，否则记次生；磁盘报告一致。"""

    slow_adapter = _FakeSharedAdapter(drop_delay=0.4)  # 让 capture_sessions 步停留 0.4s
    service, _docker = _assemble_service(tmp_path, monkeypatch, adapter=slow_adapter)
    service.registry.register("s-slow", object())
    close_task = asyncio.create_task(service.close(reason="normal_dispose"))
    await asyncio.sleep(0.1)
    assert service._close_task is not None and not service._close_task.done()  # 关停进行中
    fatal = FatalExecutionInfrastructureError("audit_store_down", "arrived mid-shutdown")
    service._on_run_fatal(fatal)  # 执行内通知器 / notify_run_fatal 最终都走这里
    second = FatalExecutionInfrastructureError("outcome_producer_failed", "second mid-shutdown")
    service._on_run_fatal(second)
    report = await close_task
    assert not report.ok
    assert report.first_cause_origin == "run_fatal_during_shutdown"
    assert "audit_store_down" in report.first_cause
    assert any("outcome_producer_failed" in s for s in report.secondary_failures)
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["first_cause"] == report.first_cause
    assert disk["first_cause_origin"] == "run_fatal_during_shutdown"
    # 报告定稿之后到达的 fatal：不再改动报告，只留 fatal_seen（进程已在退出）
    late = FatalExecutionInfrastructureError("late", "after report")
    service._on_run_fatal(late)
    assert report.first_cause == disk["first_cause"] and not any("late" in s for s in report.secondary_failures)


async def test_notify_run_fatal_triggers_close_chain_from_outside_execution(tmp_path, monkeypatch):
    """复合 group filter 在 miles buffer.put() 内抛的 fatal 不经过 generate.py 的
    `_notify_fatal_halt`：进程级入口 `notify_run_fatal` 必须触发同一条关停链（首因 = 该 fatal）。"""

    service, _docker = _assemble_service(tmp_path, monkeypatch)
    monkeypatch.setattr(bringup.BringupService, "_instance", service)

    class FakeGroupAdmissionFatal(RuntimeError):  # 形状 = group_admission.GroupAdmissionFatal（reason_code 属性）
        def __init__(self, reason_code: str, message: str) -> None:
            self.reason_code = reason_code
            super().__init__(f"{reason_code}: {message}")

    fatal = FakeGroupAdmissionFatal("identity_missing", "交付样本缺六字段身份")
    assert bringup.notify_run_fatal(fatal) is True
    assert service._close_task is not None  # 已调度关停链
    report = await service.close()
    assert report.trigger == "run_fatal" and report.reason == "run_fatal:identity_missing"
    assert report.first_cause_origin == "trigger" and "identity_missing" in report.first_cause
    assert service.lifecycle.fatal_seen == [fatal]
    monkeypatch.setattr(bringup.BringupService, "_instance", None)
    assert bringup.notify_run_fatal(fatal) is False  # 无服务：调用方照常 raise，无可关


async def test_close_bringup_service_forwards_first_cause_from_miles_dispose(tmp_path, monkeypatch):
    """miles `RolloutManager.dispose()` 把 rollout fn aclose 报告里的 worker_exception 作为
    first_cause 传入：trigger 记 run_fatal、首因 = 该异常。"""

    service, _docker = _assemble_service(tmp_path, monkeypatch)
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    worker_exc = RuntimeError("group_admission_fatal: identity_missing")
    report = await bringup.close_bringup_service(reason="rollout_manager_dispose", first_cause=worker_exc)
    assert report is not None and report.trigger == "run_fatal" and report.reason == "rollout_manager_dispose"
    assert report.first_cause_origin == "trigger" and "identity_missing" in report.first_cause and not report.ok


# ---------------------------------------------------------------------------
# 5c. patch 0013：后到的关停事实不被幂等 close 冻结（进行中 → pending 吸收；已完成 → 合并重写）
# ---------------------------------------------------------------------------

_LATE_RESIDUE = {
    "unfinished_executions": [
        {"source": "miles_rollout_fn", "reason": "active_group_unfinished_after_deadline", "sample_indices": [0, 1], "prompt_id": "pg0"}
    ],
    "rollout_fn_shutdown_failure": {"schema_id": "rh2.rollout_fn_shutdown_failure.v1", "kind": "rollout_fn_shutdown_incomplete", "problems": [{"kind": "active_groups_unfinished", "count": 1}]},
}


def _assert_late_facts_landed(disk: dict, report, early_first_cause: str, driver_cause: str):
    assert disk["first_cause"] == report.first_cause == early_first_cause  # 原首因保留
    assert disk["first_cause_origin"] == "trigger"
    assert f"late_primary(driver_error): {driver_cause}" in disk["secondary_failures"]  # 后到首因按规则记次生
    assert any(s.startswith("secondary: shutdown_failure:") for s in disk["secondary_failures"])
    assert not any("worker_fatal" in s for s in disk["secondary_failures"])  # 与首因逐字相同的 worker_fatal 不重复
    [row] = disk["residue"]["unfinished_executions"]
    assert row["reason"] == "active_group_unfinished_after_deadline" and row["sample_indices"] == [0, 1]
    assert disk["residue"]["rollout_fn_shutdown_failure"]["kind"] == "rollout_fn_shutdown_incomplete"
    assert disk["residue_free"] is False and disk["ok"] is False
    assert disk["residue"] == report.residue and disk["secondary_failures"] == report.secondary_failures


async def test_late_facts_during_close_are_absorbed_before_disk_report(tmp_path, monkeypatch):
    """时序 1：filter fatal 经 notify_run_fatal 提前触发 close，close 进行中 dispose 才带来
    driver/worker 双因 + 未完成组 → pending，落盘前吸收；磁盘报告 == 内存报告。"""

    slow_adapter = _FakeSharedAdapter(drop_delay=0.5)  # 让 close 停在 capture_sessions 步
    service, _docker = _assemble_service(tmp_path, monkeypatch, adapter=slow_adapter)
    service.registry.register("s-slow", object())
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    fatal = FatalExecutionInfrastructureError("identity_missing", "filter fatal in put()")
    assert bringup.notify_run_fatal(fatal) is True  # 提前 close 已开始
    await asyncio.sleep(0.1)
    assert service._close_task is not None and service.shutdown_report is None  # 进行中
    early_first_cause = "FatalExecutionInfrastructureError(identity_missing): identity_missing: filter fatal in put()"
    driver_cause = "RuntimeError: trainer failure"
    report = await bringup.close_bringup_service(
        reason="rollout_manager_dispose",
        trigger="driver_error",
        first_cause=driver_cause,
        secondary_causes=[f"worker_fatal: {early_first_cause}", "shutdown_failure: {\"kind\": \"rollout_fn_shutdown_incomplete\"}"],
        external_residue=_LATE_RESIDUE,
    )
    assert report is service.shutdown_report
    assert [m["phase"] for m in report.late_merges] == ["initial", "during_close"]
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    _assert_late_facts_landed(disk, report, early_first_cause, driver_cause)
    assert service.app_handle.stop_calls == 1  # cleanup 仍只执行一次


async def test_late_facts_after_close_amend_and_rewrite_disk_report(tmp_path, monkeypatch):
    """时序 2：close 已完成、报告已落盘（ok=false 只因 filter fatal、无残留）→ 后到事实并入同一
    报告并原子重写同一路径；ok/residue_free 重算；cleanup 不再执行。"""

    service, _docker = _assemble_service(tmp_path, monkeypatch)
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    fatal = FatalExecutionInfrastructureError("identity_missing", "filter fatal in put()")
    assert bringup.notify_run_fatal(fatal) is True
    first = await service.close()
    disk0 = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk0["residue_free"] is True and disk0["secondary_failures"] == [] and disk0["late_merges"][0]["phase"] == "initial"
    early_first_cause = disk0["first_cause"]
    driver_cause = "RuntimeError: trainer failure"
    report = await bringup.close_bringup_service(
        reason="rollout_manager_dispose",
        trigger="driver_error",
        first_cause=driver_cause,
        secondary_causes=[f"worker_fatal: {early_first_cause}", "shutdown_failure: {\"kind\": \"rollout_fn_shutdown_incomplete\"}"],
        external_residue=_LATE_RESIDUE,
    )
    assert report is first  # 同一 ShutdownReport 对象
    assert [m["phase"] for m in report.late_merges] == ["initial", "after_close"]
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    _assert_late_facts_landed(disk, report, early_first_cause, driver_cause)
    assert not (bringup.ARTIFACT_DIR / "shutdown_report.json.tmp").exists()  # 原子重写无残留 tmp
    assert service.app_handle.stop_calls == 1  # cleanup 没有第二次
    # 再来一次完全相同的后到事实：逐字重复不叠加
    again = await bringup.close_bringup_service(
        reason="rollout_manager_dispose", trigger="driver_error", first_cause=driver_cause,
        secondary_causes=[f"worker_fatal: {early_first_cause}"], external_residue=_LATE_RESIDUE,
    )
    assert again is first and len(report.residue["unfinished_executions"]) == 1
    assert report.secondary_failures.count(f"late_primary(driver_error): {driver_cause}") == 1


# ---------------------------------------------------------------------------
# 6. SIGTERM 真触发
# ---------------------------------------------------------------------------


async def test_sigterm_triggers_shutdown_chain(tmp_path, monkeypatch):
    if threading.current_thread() is not threading.main_thread():
        pytest.skip("loop.add_signal_handler 只在主线程可用")
    service, docker = _assemble_service(tmp_path, monkeypatch)
    service.install_sigterm_shutdown()
    service.install_sigterm_shutdown()  # 幂等
    assert signal.getsignal(signal.SIGTERM) not in (signal.SIG_DFL, signal.SIG_IGN)
    try:
        os.kill(os.getpid(), signal.SIGTERM)
        for _ in range(500):
            if service._close_task is not None:
                break
            await asyncio.sleep(0.01)
        assert service._close_task is not None, "SIGTERM 没有触发关停链"
        report = await service.close()
        assert report.trigger == "signal" and report.reason == "signal:SIGTERM"
        assert report.ok, report.to_dict()
        assert service.app_handle.stop_calls == 1
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_DFL  # 关停完成后恢复默认处置
        assert service._uninstall_signal_shutdown is None
    finally:
        if service._uninstall_signal_shutdown is not None:
            service._uninstall_signal_shutdown()


async def test_late_secondary_dedupe_is_exact_entry_equality_during_close(tmp_path, monkeypatch):
    """codex 复核 P1（去重反例，时序 1：close 进行中）：已记 "optimizer timeout after all-reduce"
    时，后到的独立 "timeout" 不得被子串判断吞掉；逐字相同的重复仍只记一次。"""

    slow_adapter = _FakeSharedAdapter(drop_delay=0.5)
    service, _docker = _assemble_service(tmp_path, monkeypatch, adapter=slow_adapter)
    service.registry.register("s-slow", object())
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    assert bringup.notify_run_fatal(FatalExecutionInfrastructureError("identity_missing", "filter fatal")) is True
    await asyncio.sleep(0.1)
    assert service._close_task is not None and service.shutdown_report is None
    report = await bringup.close_bringup_service(
        reason="rollout_manager_dispose",
        trigger="driver_error",
        first_cause="RuntimeError: trainer failure",
        secondary_causes=["optimizer timeout after all-reduce", "timeout", "timeout"],
    )
    assert report.secondary_failures.count("secondary: optimizer timeout after all-reduce") == 1
    assert report.secondary_failures.count("secondary: timeout") == 1
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["secondary_failures"] == report.secondary_failures


async def test_late_secondary_dedupe_is_exact_entry_equality_after_close(tmp_path, monkeypatch):
    """codex 复核 P1（去重反例，时序 2：close 已完成后的 amendment 重写）：同一包含关系反例。"""

    service, _docker = _assemble_service(tmp_path, monkeypatch)
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    first = await service.close(secondary_causes=["optimizer timeout after all-reduce"])
    assert "secondary: optimizer timeout after all-reduce" in first.secondary_failures
    report = await bringup.close_bringup_service(
        reason="rollout_manager_dispose",
        trigger="driver_error",
        first_cause="RuntimeError: trainer failure",
        secondary_causes=["timeout", "optimizer timeout after all-reduce"],
    )
    assert report is first
    assert report.secondary_failures.count("secondary: timeout") == 1
    assert report.secondary_failures.count("secondary: optimizer timeout after all-reduce") == 1
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["secondary_failures"] == report.secondary_failures



# ---------------------------------------------------------------------------
# codex Wave3 §9.4：run-fatal 必须被调度到 **owner loop**，不是发起通知的那个 loop
#
# 真实拓扑（两个 loop、两个线程）：
#   miles 共享后台 AsyncLoopThread ──> BringupService / rollout worker / grading queue（owner）
#   slime `run_app_in_thread`（vendored，不可改）──> 独立 aiohttp adapter loop
#     └─ HTTP handler → capture_wire `_send_once` → abort partial/undeliverable
#          → bringup.notify_run_fatal（**本组反例不替换它**）
#
# 修复前 `_on_run_fatal` 用 `asyncio.get_running_loop()`，关停链会被建在 adapter loop 上：
# 它随后要等 owner loop 上的在飞执行 task / grading queue，直接撞
# "Future attached to a different loop"，而 abort 却已被记成 notified=true。
# ---------------------------------------------------------------------------


class _LoopThread:
    """一个专属线程 + 专属 event loop（miles 后台 loop 与 adapter loop 的最小同形替身）。"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.loop = asyncio.new_event_loop()
        self.errors: list[dict[str, Any]] = []
        self.loop.set_exception_handler(lambda _loop, ctx: self.errors.append(ctx))
        self._ready = threading.Event()
        self.thread = threading.Thread(target=self._run, name=name, daemon=True)

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon(self._ready.set)
        self.loop.run_forever()

    def start(self) -> "_LoopThread":
        self.thread.start()
        assert self._ready.wait(5), f"{self.name} 未在 5s 内就绪"
        return self

    def run(self, coro, timeout: float = 30.0):
        """从**别的**线程把协程交给本 loop 跑完（asyncio.run_coroutine_threadsafe）。"""

        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def stop(self) -> None:
        if self.loop.is_closed():
            return
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        self.loop.close()


def _real_undeliverable_abort(rid: str):
    """真实 `MilesRouterWorkerClient.broadcast_abort` 的 undeliverable 结果（不是手搓 dataclass）：
    router 地址指向无人监听的端口 → 实时列表拿不到，又没有启动核对集合 → 目标集合为空。"""

    from repoharness2.adapters.slime.engine_router_client import MilesRouterWorkerClient

    client = MilesRouterWorkerClient(
        "http://127.0.0.1:1", list_timeout_seconds=0.3, abort_timeout_seconds=0.3
    )
    return client.broadcast_abort(rid)


async def _escalate_like_capture_wire(registry, rid: str) -> bool:
    """capture_wire `_abort_rid` 的 unproven 分支逐句同形（三行都是生产函数）。"""

    from repoharness2.adapters.slime.capture_wire import escalate_abort_unproven
    from repoharness2.adapters.slime.engine_router_client import AbortDeliveryUnprovenError

    result = await _real_undeliverable_abort(rid)
    registry.note_abort_result(result)
    assert result.proven is False and result.outcome == "undeliverable"
    return escalate_abort_unproven(registry, AbortDeliveryUnprovenError(result))


def test_run_fatal_from_adapter_loop_schedules_shutdown_on_owner_loop(tmp_path, monkeypatch):
    """反例：abort undeliverable 在 **adapter loop / adapter 线程**上升级 run-fatal。

    断言：关停 task 属于 owner loop（不是发起方 loop）；关停报告 trigger=run_fatal、ok=false；
    两个 loop 都没有 cross-loop 异常；关停进行中到达的第二个 fatal 也在 owner loop 上并入同一份报告。
    """

    owner = _LoopThread("rh2-owner-loop").start()
    adapter = _LoopThread("rh2-adapter-loop").start()
    try:
        async def _assemble():
            # adapter_http 步 stop_delay=0.6s：给"关停进行中"留一个确定的窗口（上界 FAST=2.0s）
            service, _docker = _assemble_service(
                tmp_path, monkeypatch, app_handle=_FakeAppHandle(stop_delay=0.6)
            )
            return service

        service = owner.run(_assemble())
        assert service._owner_loop is owner.loop and owner.loop is not adapter.loop
        monkeypatch.setattr(bringup.BringupService, "_instance", service)

        # ① adapter loop 上跑真实 abort → 真实 escalate → 真实 notify_run_fatal（无替身）
        notified = adapter.run(_escalate_like_capture_wire(service.registry, "rid-ghost-1"))
        assert notified is True
        assert service.registry.stats["abort_unproven_fatal"] == 1
        assert service.registry.stats["abort_unproven_unnotified"] == 0  # 派回成功才算已通知

        # ② 关停 task 必须建在 owner loop 上（修复前这里是 adapter loop）
        async def _wait_for_close_task():
            for _ in range(500):
                if service._close_task is not None:
                    return service._close_task
                await asyncio.sleep(0.01)
            raise AssertionError("owner loop 上没有出现关停 task")

        close_task = owner.run(_wait_for_close_task())
        assert close_task.get_loop() is owner.loop
        assert close_task.get_loop() is not adapter.loop

        # ③ 关停进行中，adapter loop 再来一个 fatal：也必须派回 owner loop 合并（W5a 后到事实路径）
        async def _wait_until_closing():
            for _ in range(500):
                if service._closing_report is not None:
                    return True
                await asyncio.sleep(0.01)
            raise AssertionError("关停链没有进入进行中状态")

        assert owner.run(_wait_until_closing()) is True
        assert adapter.run(_escalate_like_capture_wire(service.registry, "rid-ghost-2")) is True

        report = owner.run(asyncio.wait_for(asyncio.shield(close_task), 30))
        assert report.trigger == "run_fatal" and report.reason == "run_fatal:abort_undeliverable"
        assert report.ok is False
        assert report.first_cause_origin == "trigger"
        assert "AbortDeliveryUnprovenError(abort_undeliverable)" in report.first_cause
        assert "rid-ghost-1" in report.first_cause
        # 第二个 fatal 在 owner loop 上并入同一份报告（次生，不是丢弃）
        merged = [s for s in report.secondary_failures if s.startswith("run_fatal_during_shutdown")]
        assert len(merged) == 1 and "rid-ghost-2" in merged[0]
        assert [type(e).__name__ for e in service.lifecycle.fatal_seen] == [
            "AbortDeliveryUnprovenError", "AbortDeliveryUnprovenError",
        ]
        assert service.registry.stats["abort_unproven_unnotified"] == 0
        # 无 cross-loop 异常：两个 loop 的 exception handler 都没被调用，关停各步也没有失败
        assert owner.errors == [] and adapter.errors == []
        assert [s.name for s in report.steps if s.status == "failed"] == []
        disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
        assert disk["trigger"] == "run_fatal" and disk["ok"] is False
    finally:
        adapter.stop()
        owner.stop()


def test_run_fatal_is_not_reported_notified_when_owner_loop_is_gone(tmp_path, monkeypatch):
    """反例：owner loop 已经关掉，从 adapter 线程通知 → **不得**返回"通知成功"。

    capture_wire 侧必须如实记 `abort_unproven_unnotified`（否则 abort 未证明到达这件事会被
    "已通知，等关停链处理"掩盖，而实际上没有任何关停链被调度）。"""

    owner = _LoopThread("rh2-owner-loop-dead").start()
    adapter = _LoopThread("rh2-adapter-loop-2").start()
    try:
        async def _assemble():
            service, _docker = _assemble_service(tmp_path, monkeypatch)
            return service

        service = owner.run(_assemble())
        monkeypatch.setattr(bringup.BringupService, "_instance", service)
        owner.stop()  # owner loop 关闭（run 已结束/进程正在退出）
        assert service._owner_loop.is_closed()

        notified = adapter.run(_escalate_like_capture_wire(service.registry, "rid-ghost-3"))
        assert notified is False  # 没送到就不能报"已通知"
        assert service._close_task is None  # 也没有在 adapter loop 上偷偷建关停链
        assert service.registry.stats["abort_unproven_fatal"] == 1
        assert service.registry.stats["abort_unproven_unnotified"] == 1
        assert adapter.errors == []
    finally:
        adapter.stop()
        owner.stop()


@pytest.mark.parametrize("cancel_submitters", [False, True])
async def test_grading_queue_step_drains_backlog_within_timeout(tmp_path, monkeypatch, cancel_submitters):
    """R5-F1（Codex 修后复核）：真实关停链 grading_queue 步——一个 worker、两条已接收请求（一条在评、一条排队），
    drain 阶段必须把第二条也评完再撤 worker，`drained_within_timeout=True`（修前：worker 做完第一条即退出，
    第二条无人消费，步耗满 grading_drain 后 False 再走 close(drain=False)）。提交者仍在 / 已被服务取消两案。"""

    from dataclasses import replace

    entered, release = asyncio.Event(), asyncio.Event()
    calls: list[str] = []

    class Manager:
        async def grade(self, **kwargs):
            calls.append(kwargs["trajectory_id"])
            if len(calls) == 1:
                entered.set()
                await release.wait()
            return f"report:{kwargs['trajectory_id']}"

    service, _docker = _assemble_service(tmp_path, monkeypatch, timeouts=replace(FAST, grading_drain=1.0))
    queue = GradingQueue(Manager(), GradingQueueConfig(concurrency=1, queue_size=2))
    await queue.start()
    service.grading_queue = queue
    service._queue_started = True
    spec = SimpleNamespace(task_id="task")
    first = asyncio.create_task(queue.submit(trajectory_id="first", workspace=None, spec=spec))
    await asyncio.wait_for(entered.wait(), 1)
    second = asyncio.create_task(queue.submit(trajectory_id="second", workspace=None, spec=spec))
    while queue.queue_depth != 1:
        await asyncio.sleep(0)
    if cancel_submitters:
        first.cancel()
        second.cancel()
        await asyncio.gather(first, second, return_exceptions=True)
    step = next(s for s in service._build_shutdown_steps() if s.name == "grading_queue")
    closing = asyncio.create_task(step.run())
    await asyncio.sleep(0.02)
    assert not closing.done() and queue._closing is False and not queue._workers[0].done()  # drain 中：worker 仍在
    release.set()
    facts = await asyncio.wait_for(closing, 2)
    assert facts["drained_within_timeout"] is True
    assert calls == ["first", "second"] and queue.queue_depth == 0 and queue._workers == []
    if not cancel_submitters:
        assert await second == "report:second"


# ---------------------------------------------------------------------------
# I13（第 2 组 §3，owner 2026-09-09 已批）：execution_closure 事实与等待类残留的解消
# ---------------------------------------------------------------------------


def _audit(*, container: str | None, released: bool, failures: tuple[str, ...] = (), records_complete: bool = True):
    return SimpleNamespace(
        lease=SimpleNamespace(container_id=container) if container else None,
        lease_released=released,
        failure_records=[SimpleNamespace(error_type=code) for code in failures],
        # R3：必要记录**已写完**的正向事实（真实 audit 只在 finally 走到末尾时置 True）
        necessary_records_complete=records_complete,
        physical_attempt_id=f"{container or 'attempt'}#p1",
    )


async def test_execution_closure_complete_lets_verified_wait_residue_resolve(tmp_path, monkeypatch):
    """miles 侧只剩等待类快照：rh2 自己的 ok 仍 False（严格口径），但 execution_closure 完整 →
    `ok_if_wait_residue_resolved`；owner 复查后 `resolve_external_wait_residue` 把快照移到
    resolved_wait_timeouts，磁盘报告原子重写，ok 变 True。"""

    orchestrator = SimpleNamespace(audits=[_audit(container="c1", released=True)], cleanup_quarantine=[])
    service, _docker = _assemble_service(tmp_path, monkeypatch, orchestrator=orchestrator)
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    report = await service.close(reason="rollout_manager_dispose", trigger="owner_close", external_residue=_LATE_RESIDUE)
    assert report.ok is False and report.residue_free is False
    assert report.execution_closure["complete"] is True and report.execution_closure["attempts_audited"] == 1
    assert report.residue_free_excluding_external_wait is True and report.ok_if_wait_residue_resolved is True
    disk0 = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk0["ok"] is False and disk0["ok_if_wait_residue_resolved"] is True and disk0["resolved_wait_timeouts"] == []
    final_state = {"all_settled": True, "active_groups": [{"state": "cancelled"}], "late_group_exceptions": []}
    resolved = bringup.resolve_external_wait_residue(final_state)  # 进程级入口 = miles 侧调用形状
    assert resolved is report and report.ok is True and report.residue_free is True
    (entry,) = report.resolved_wait_timeouts
    assert entry["rows"][0]["source"] == "miles_rollout_fn" and entry["final_state"] == final_state
    assert entry["rollout_fn_shutdown_failure"]["kind"] == "rollout_fn_shutdown_incomplete"
    assert report.residue["unfinished_executions"] == [] and report.residue["rollout_fn_shutdown_failure"] is None
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is True and disk["residue_free"] is True
    assert disk["resolved_wait_timeouts"][0]["rows"][0]["prompt_id"] == "pg0"
    assert disk["residue"]["rollout_fn_shutdown_failure"] is None and disk["first_cause"] is None
    assert not (bringup.ARTIFACT_DIR / "shutdown_report.json.tmp").exists()
    assert service.app_handle.stop_calls == 1  # 解消不重跑 cleanup
    assert bringup.resolve_external_wait_residue(final_state) is None  # 再调一次：没有可移的快照


async def test_wait_residue_resolution_keeps_rh2_own_unfinished_execution_as_residue(tmp_path, monkeypatch):
    """rh2 自己的未完成执行（source 不是 miles_rollout_fn）不算等待类快照：不可解消。"""

    service, _docker = _assemble_service(tmp_path, monkeypatch)
    residue = {
        "unfinished_executions": [
            *_LATE_RESIDUE["unfinished_executions"],
            {"source": "rh2_inflight", "reason": "unfinished_after_cancel_wait", "trajectory_id": "t1"},
        ],
        "rollout_fn_shutdown_failure": _LATE_RESIDUE["rollout_fn_shutdown_failure"],
    }
    report = await service.close(reason="rollout_manager_dispose", trigger="owner_close", external_residue=residue)
    assert report.residue_free_excluding_external_wait is False and report.ok_if_wait_residue_resolved is False
    assert service.resolve_external_wait_residue({"all_settled": True}) is None and report.ok is False


@pytest.mark.parametrize(
    "orchestrator",
    [
        SimpleNamespace(audits=[_audit(container="c1", released=False)], cleanup_quarantine=[]),  # 容器未确认释放
        SimpleNamespace(
            audits=[_audit(container="c1", released=True, failures=("finalization_receipt_write_failed",))],
            cleanup_quarantine=[],
        ),  # 必要记录写失败
        SimpleNamespace(
            audits=[_audit(container="c1", released=True, failures=("audit_sink_failed_secondary",))],
            cleanup_quarantine=[],
        ),  # audit 落盘失败
        SimpleNamespace(
            audits=[_audit(container="c1", released=True, records_complete=False)],
            cleanup_quarantine=[],
        ),  # R3：没有写失败记录，但 finally 没走到 audit sink（第二次取消打断）——正向事实缺失同样不完整
    ],
)
async def test_missing_closure_evidence_keeps_wait_residue_unresolved(tmp_path, monkeypatch, orchestrator):
    service, _docker = _assemble_service(tmp_path, monkeypatch, orchestrator=orchestrator)
    report = await service.close(reason="rollout_manager_dispose", trigger="owner_close", external_residue=_LATE_RESIDUE)
    assert report.cleanup_clean is True and report.residue_free_excluding_external_wait is True  # 只差 closure 证据
    assert report.execution_closure["complete"] is False and report.ok_if_wait_residue_resolved is False
    if not orchestrator.audits[0].necessary_records_complete:
        assert report.execution_closure["attempts_records_incomplete"] == 1
        assert report.execution_closure["attempts_records_incomplete_ids"] == ["c1#p1"]
    assert service.resolve_external_wait_residue({"all_settled": True}) is None
    assert report.ok is False and report.resolved_wait_timeouts == []
    disk = json.loads((bringup.ARTIFACT_DIR / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["execution_closure"]["complete"] is False


async def test_evidence_failure_or_first_cause_keeps_wait_residue_unresolved(tmp_path, monkeypatch):
    service, _docker = _assemble_service(tmp_path, monkeypatch)
    report = await service.close(
        reason="rollout_manager_dispose", trigger="run_fatal", first_cause="RuntimeError: worker exploded",
        external_residue=_LATE_RESIDUE,
    )
    assert report.execution_closure["complete"] is False and report.execution_closure["first_cause"] is not None
    assert report.ok_if_wait_residue_resolved is False and service.resolve_external_wait_residue({}) is None
    assert report.first_cause is not None and report.ok is False


@pytest.mark.parametrize("slow_network", [False, True])
async def test_second_cancel_inside_finally_leaves_necessary_records_incomplete(tmp_path, monkeypatch, slow_network):
    """R3（Codex 第 2 组剩余集成审查）真实控制流：formal 编排、真实 finally、真实关停链。
    第一次取消（= miles 侧 aclose 的组取消）让 finally 开始：receipt 已持久化 → 容器 rm → 私网清理 await；
    slow_network=True 时该 await 挂 0.8s，关停链在飞步 grace 后**第二次取消**落在这里——成员 task 结束、
    audit sink 从未执行、也没有任何"写失败"记录。此时 execution_closure 必须判"记录未完成"，等待类残留不可解消；
    对照（网络清理立刻完成）：finally 走到末尾，audit 写出，closure 完整。"""

    from dataclasses import replace

    service, _docker = _assemble_service(
        tmp_path, monkeypatch, timeouts=replace(FAST, inflight_grace=0.05, inflight_cancel_wait=2.0)
    )
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    store = FakeFinalizationStore()
    task_spec = make_task(TASK_ID_DENSE)

    def resolver(sample):
        service.lifecycle.enter_execution(getattr(sample, "metadata", None), task_id=task_spec.task_id)
        return task_spec

    turns = dense_turns()
    for turn in turns:
        turn.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(execution_mode="fa_formal"), runtime_quiescence_barrier=_Barrier(), turns=turns,
        finalization_store=store, task=resolver, audit_sink=service._write_execution_audit,
    )
    _stamp_fa_identity(chain.base_sample)
    service.orchestrator = chain.orchestrator
    service.egress_relay = chain.orchestrator._egress_relay
    driver = _BlockingDriver(chain.adapter_ref)
    chain.orchestrator._harness_driver = driver
    orig_docker = chain.orchestrator._docker
    network_cancelled = asyncio.Event()

    async def docker(*args, **kw):
        if len(args) >= 2 and args[:2] == ("network", "disconnect") and slow_network:
            try:
                await asyncio.sleep(0.8)
            except asyncio.CancelledError:
                network_cancelled.set()
                raise
        return await orig_docker(*args, **kw)

    chain.orchestrator._docker = docker
    monkeypatch.setattr(bringup, "_sandbox_docker", lambda: docker)
    run = asyncio.create_task(chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)))
    await asyncio.wait_for(driver.entered.wait(), 5)
    run.cancel()  # 第一次取消：finally 开始（receipt → 容器 rm → 私网清理）
    await asyncio.sleep(0.1)
    report = await service.close(reason="rollout_manager_dispose", trigger="owner_close", external_residue=_LATE_RESIDUE)
    await asyncio.gather(run, return_exceptions=True)
    (audit,) = chain.orchestrator.audits
    assert len(store.receipts) == 1 and audit.lease_released is True  # 两种情形 receipt 都已持久化、容器都已释放
    closure = report.execution_closure
    audit_written = (bringup.ARTIFACT_DIR / "fa_execution_audit.jsonl").exists()
    if slow_network:
        assert network_cancelled.is_set() and audit_written is False  # 第二次取消打断了 finally，sink 没执行
        assert not any(f.error_type in ("audit_sink_failed_secondary", "finalization_receipt_write_failed") for f in audit.failure_records)
        assert audit.necessary_records_complete is False
        assert closure["complete"] is False and closure["attempts_records_incomplete"] == 1
        assert closure["record_write_failures"] == 0  # 正是 R3：没有写失败记录 ≠ 已写完
        assert report.ok_if_wait_residue_resolved is False and service.resolve_external_wait_residue({"all_settled": True}) is None
        assert report.ok is False
    else:
        assert audit_written is True and audit.necessary_records_complete is True
        assert closure["complete"] is True and closure["attempts_records_incomplete"] == 0
        assert report.ok_if_wait_residue_resolved is True

