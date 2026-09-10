"""W5a（codex 复核 #1 / patch 0011 / patch 0012）：miles 生产退出链——**真实双 event-loop 拓扑**重放，
以及"关停残留必须上提成 run 失败"的 verdict 语义。

生产拓扑：`RolloutManager._get_rollout_data` → `asyncio.to_thread(call_rollout_function, …)` →
`async_utils.run` 把协程投到全局后台 `AsyncLoopThread`（owner loop）。FullyAsyncRolloutFn、worker、
DefaultDataBuffer、RH2 BringupService 全在 owner loop；Ray actor 自己的 loop 只是调用方。本文件
用 miles 真实 `get_async_loop()` 作 owner loop、pytest 的 loop 作调用方（模拟 actor loop），
按生产调用方式驱动：drain 走 `to_thread(call_rollout_function)`，dispose 走
`miles.utils.rh2_shutdown.dispose_on_owner_loop`（= RolloutManager.dispose 的实现）。

integration_base 专属（pin 树没有这些接口）。只替换两个引擎面模块（GenerateState /
generate_and_rm_group）；FullyAsyncRolloutFn / DefaultDataBuffer / scheduler / compatibility /
async_utils / rh2_shutdown / rh2 关停链全部真实。RolloutManager 与 train_async 本体（Ray/sglang
import）用源码事实钉死。
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


class _StubGenerateState:
    """FullyAsyncRolloutFn.__init__ 的 GenerateState 替身（真实版加载 tokenizer/引擎并发面）。"""

    def __init__(self, args):
        self.args = args
        self.sampling_params = {"temperature": 1.0}
        self.aborted = False


class _DataSource:
    def __init__(self, world, n: int):
        self.world = world
        self.n = n
        self.served = 0

    def get_samples(self, count: int):
        groups = []
        for _ in range(count):
            groups.append(self.world.mk_gov_prompt_group(f"pg{self.served}", n=self.n))
            self.served += 1
        return groups

    def add_samples(self, groups):
        pass


def _args(world, **over):
    return world.mk_miles_args(
        rollout_submission_granularity="group",
        async_unused_samples_handler="drop",
        rollout_sample_filter_path=None,
        custom_async_data_buffer_path=None,
        async_max_concurrent_samples=None,
        rollout_global_dataset=True,
        rollout_batch_size=2,
        n_samples_per_prompt=2,
        **over,
    )


def _install_engine_face_stubs(monkeypatch, *, generate):
    """fully_async_rollout 模块级 import 的两个**引擎面**模块（inference_rollout_common /
    inference_rollout_eval）在 rh2 venv 不可导（pybase64/pylatexenc/megatron 链）；用只含
    被引用符号的 stub 顶替——与 conftest 的 ray/sglang stub 同一性质（环境噪音，不复刻行为）。"""

    import types

    common = types.ModuleType("miles.rollout.inference_rollout.inference_rollout_common")
    common.__rh2_test_stub__ = True
    common.GenerateState = _StubGenerateState
    common.generate_and_rm_group = generate
    evalmod = types.ModuleType("miles.rollout.inference_rollout.inference_rollout_eval")
    evalmod.__rh2_test_stub__ = True

    async def run_eval_datasets(*a, **k):  # 本测试不走 eval
        raise AssertionError("eval 面不在本测试范围")

    evalmod.run_eval_datasets = run_eval_datasets
    monkeypatch.setitem(sys.modules, common.__name__, common)
    monkeypatch.setitem(sys.modules, evalmod.__name__, evalmod)


def _build_fn(world, monkeypatch, *, generate, args):
    world.install_sglang_stub()
    _install_engine_face_stubs(monkeypatch, generate=generate)
    import miles.rollout.fully_async_rollout as far
    from miles.rollout.base_types import RolloutFnConstructorInput

    monkeypatch.setattr(far, "GenerateState", _StubGenerateState)
    monkeypatch.setattr(far, "generate_and_rm_group", generate)
    source = _DataSource(world, args.n_samples_per_prompt)
    fn = far.FullyAsyncRolloutFn(RolloutFnConstructorInput(args=args, data_source=source))
    return far, fn, source


def _owner_loop():
    """miles 的全局后台 loop（生产里 call_rollout_function → run() 投递的目标）。"""

    from miles.utils.async_utils import get_async_loop

    return get_async_loop()


async def _drain_like_production(fn, rollout_id: int = 0):
    """= RolloutManager._get_rollout_data 的调用形状：to_thread(call_rollout_function) → run(coro)。"""

    from miles.rollout.base_types import RolloutFnTrainInput
    from miles.rollout.inference_rollout.compatibility import call_rollout_function

    return await asyncio.to_thread(
        call_rollout_function, fn, RolloutFnTrainInput(rollout_id=rollout_id, weight_version=1)
    )


async def _wait_until(pred, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not pred():
        assert time.monotonic() < deadline, "条件未在超时内成立"
        await asyncio.sleep(0.01)


def _assemble_rh2_service(monkeypatch) -> tuple:
    """按 BringupService.__init__ 的属性面装配一个不起 tokenizer/adapter 线程的服务（关停链
    读的属性逐个给出）；注册为单例，让 close_bringup_service 在 owner loop 上真实跑关停链。"""

    import repoharness2.adapters.slime.bringup as bringup
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry
    from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager
    from repoharness2.grading.queue import GradingQueue, GradingQueueConfig
    from repoharness2.shutdown import LifecycleState, ShutdownTimeouts

    tmp = Path(tempfile.mkdtemp(prefix="w5a-dual-loop-"))
    monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp)
    service = object.__new__(bringup.BringupService)
    service.shutdown_timeouts = ShutdownTimeouts(
        inflight_grace=0.05, inflight_cancel_wait=1.0, grading_drain=1.0, grading_manager=1.0,
        capture_sessions=1.0, adapter_http=1.0, container_residue=1.0, resource_closure=10.0, evidence=1.0,
    )
    service.lifecycle = LifecycleState()
    service.lifecycle.on_fatal = service._on_run_fatal
    service._close_task = None
    service.shutdown_report = None
    service._fatals_during_close = []
    service._closing_report = None
    service._pending_late_facts = []
    service._deferred_residues = []
    service._uninstall_signal_shutdown = None
    service._profile_args = SimpleNamespace(
        rollout_batch_size=2, n_samples_per_prompt=2, num_rollout=1, rollout_max_response_len=64,
        async_data_buffer_capacity_factor=2.0,
    )
    service.registry = CaptureRegistry()
    service.adapter = SimpleNamespace(drop_session=None)
    service.app_handle = None
    service.grading_manager = SWEGradingManager(
        GradingManagerConfig(), docker=None, stop_requested=service._grading_stop_requested  # R4：与生产接线一致
    )
    service.grading_queue = GradingQueue(service.grading_manager, GradingQueueConfig(concurrency=1, queue_size=1))
    service._queue_started = False
    service.events_path = tmp / "bringup_events.jsonl"
    service.orchestrator = None
    service.engine_sampling_mask = False
    service.max_context_len = 0
    monkeypatch.setattr(bringup.BringupService, "_instance", service)
    monkeypatch.setattr(bringup.BringupService, "_startup_state", "RUNNING")
    return service, tmp


def _blocking_generate_factory(world, *, stubborn_first: bool = False):
    """generate_and_rm_group 替身：进入即计数，然后挂起直到被取消。stubborn_first=True 时第一个
    组吞掉取消再挂起（模拟 HTTP/SGLang/session cleanup 不响应取消的真实 adapter 路径）。"""

    entered = threading.Event()
    count = [0]
    stubborn_tasks: list[asyncio.Task] = []

    async def generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        count[0] += 1
        if count[0] == 2:
            entered.set()
        if stubborn_first and count[0] == 1:
            stubborn_tasks.append(asyncio.current_task())
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                await asyncio.sleep(3600)  # 吞掉取消：永远不结束
        await asyncio.sleep(3600)
        return world.mk_gov_finished_group(prompt_group)

    return generate, entered, stubborn_tasks


# ---------------------------------------------------------------------------
# ⑥ 正常取消：整体关停从调用方 loop 近 0s 完成、无外部 timer、verdict ok=true
# ---------------------------------------------------------------------------


async def test_dual_loop_normal_dispose_completes_without_external_timer(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop, raise_if_shutdown_failed

    generate, entered, _ = _blocking_generate_factory(world)
    far, fn, source = _build_fn(world, monkeypatch, generate=generate, args=_args(world))
    service, tmp = _assemble_rh2_service(monkeypatch)
    owner = _owner_loop()

    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)
    assert entered.is_set()
    assert fn._worker is not None and fn._worker.get_loop() is owner.loop  # worker 真在 owner loop
    assert asyncio.get_running_loop() is not owner.loop  # 调用方 = 另一个 loop（模拟 actor loop）

    t0 = time.monotonic()
    report = await dispose_on_owner_loop(fn, driver_cause=None, timeout_seconds=10.0)
    elapsed = time.monotonic() - t0
    assert elapsed < 1.5, f"dispose 用了 {elapsed:.3f}s（应近 0s：跨线程 Future 经 wrap_future 唤醒调用方 loop）"
    assert report["ok"] is True and report["cleanup_ok"] is True and report["timed_out"] is False
    assert report["errors"] == [] and report["shutdown_failure"] is None and report["secondary_causes"] == []
    fn_report = report["rollout_fn"]
    assert fn_report["worker_state"] == "cancelled" and fn_report["active_groups_cancelled"] == 2
    assert fn_report["active_groups_unfinished"] == 0 and fn_report["deadline_exceeded"] is False
    assert fn_report["buffer_closed"] is True and fn_report["deadline_seconds"] == 60.0  # 默认期限
    assert report["trigger"] == "owner_close" and report["primary_cause"] is None
    assert report["rh2"]["ok"] is True and report["rh2"]["cleanup_ok"] is True  # rh2 关停链在 owner loop 上真实跑完
    assert service.shutdown_report is not None and service._close_task.get_loop() is owner.loop
    assert raise_if_shutdown_failed(report, driver_cause=None, evidence_dir=tmp) is None  # 正常路径不落标记、不抛
    assert not (tmp / "shutdown_failure.json").exists()
    with pytest.raises(far.RolloutFnClosed):  # drain waiter 被唤醒并 typed 退出（经 run().result() 传回调用方线程）
        await drain
    assert source.served == 2
    assert json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))["ok"] is True


# ---------------------------------------------------------------------------
# ① 取消不响应的 active group：到期放弃 → typed 关停失败 → 最终报告 ok=false + 具体残留
# ---------------------------------------------------------------------------


async def test_dual_loop_stubborn_active_group_fails_final_report_with_concrete_residue(world, monkeypatch):
    from miles.utils.rh2_shutdown import ShutdownFailure, dispose_on_owner_loop, raise_if_shutdown_failed

    generate, entered, stubborn_tasks = _blocking_generate_factory(world, stubborn_first=True)
    args = _args(world, rh2_shutdown_deadline_sec=0.5)  # args 覆盖期限
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)
    owner = _owner_loop()

    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)
    t0 = time.monotonic()
    report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
    elapsed = time.monotonic() - t0
    assert 0.4 <= elapsed < 3.0, elapsed  # 有界：期限 0.5s 后放弃，不再等
    fn_report = report["rollout_fn"]
    assert fn_report["deadline_seconds"] == 0.5 and fn_report["deadline_exceeded"] is True
    assert fn_report["active_groups_cancelled"] == 2 and fn_report["active_groups_unfinished"] == 1
    assert fn_report["worker_state"] == "cancelled" and fn_report["buffer_closed"] is True  # finally 里仍关 buffer
    # 残留必须上提：typed 关停失败 = 首因（无其它首因），最终报告 ok=false
    assert report["ok"] is False and report["cleanup_ok"] is False
    failure = report["shutdown_failure"]
    assert failure["schema_id"] == "rh2.rollout_fn_shutdown_failure.v1"
    assert failure["kind"] == "rollout_fn_shutdown_incomplete"
    [problem] = failure["problems"]
    assert problem["kind"] == "active_groups_unfinished" and problem["count"] == 1
    assert problem["groups"][0]["sample_indices"] == [0, 1] and problem["groups"][0]["prompt_id"] == "pg0"
    assert report["trigger"] == "shutdown_failure" and report["primary_cause"].startswith("shutdown_failure:")
    assert report["rh2"]["ok"] is False
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["trigger"] == "shutdown_failure" and disk["first_cause_origin"] == "trigger"
    assert "active_groups_unfinished" in disk["first_cause"]
    [row] = disk["residue"]["unfinished_executions"]  # 具体残留：组标识 + 原因
    assert row["source"] == "miles_rollout_fn" and row["reason"] == "active_group_unfinished_after_deadline"
    assert row["sample_indices"] == [0, 1] and row["prompt_id"] == "pg0"
    assert disk["residue"]["rollout_fn_shutdown_failure"]["kind"] == "rollout_fn_shutdown_incomplete"
    assert disk["residue_free"] is False
    # driver 侧：无 driver 异常 → run 非成功退出（typed）+ 标记文件
    with pytest.raises(ShutdownFailure) as exc:
        raise_if_shutdown_failed(report, driver_cause=None, evidence_dir=tmp)
    assert exc.value.verdict is report and "shutdown_failure" in str(exc.value)
    marker = json.loads((tmp / "shutdown_failure.json").read_text(encoding="utf-8"))
    assert marker["driver_cause"] is None and marker["verdict"]["ok"] is False
    with pytest.raises(far.RolloutFnClosed):
        await drain
    for task in stubborn_tasks:  # 被放弃的 task 仍在 owner loop 上：测试结束前收掉
        assert not task.done()
        owner.loop.call_soon_threadsafe(task.cancel)
    await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# ② worker 到期未结束 → 同上（worker_unfinished 残留）
# ---------------------------------------------------------------------------


async def test_dual_loop_worker_unfinished_fails_final_report(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

    generate, entered, _ = _blocking_generate_factory(world)
    args = _args(world, rh2_shutdown_deadline_sec=0.3)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)
    owner = _owner_loop()
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)

    async def _make_stubborn_worker():  # owner loop 上一个吞掉取消的 task，顶替 worker 句柄
        async def stubborn():
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                await asyncio.sleep(3600)

        return asyncio.create_task(stubborn())

    real_worker = fn._worker
    stubborn = await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(_make_stubborn_worker(), owner.loop))
    fn._worker = stubborn
    try:
        report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
        fn_report = report["rollout_fn"]
        assert fn_report["worker_state"] == "unfinished" and fn_report["worker_unfinished"] is True
        assert fn_report["deadline_exceeded"] is True and fn_report["buffer_closed"] is True
        assert report["ok"] is False and report["trigger"] == "shutdown_failure"
        kinds = [p["kind"] for p in report["shutdown_failure"]["problems"]]
        assert "worker_unfinished" in kinds
        disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
        assert disk["ok"] is False
        assert any(r["reason"] == "worker_unfinished_after_deadline" for r in disk["residue"]["unfinished_executions"])
        with pytest.raises((far.RolloutFnClosed, Exception)):
            await drain
    finally:
        for task in (stubborn, real_worker):
            owner.loop.call_soon_threadsafe(task.cancel)
        await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# ③ buffer 关闭失败（close_error / buffer_not_closed）→ 同上
# ---------------------------------------------------------------------------


async def test_dual_loop_buffer_close_error_fails_final_report(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

    generate, entered, _ = _blocking_generate_factory(world)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=_args(world))
    service, tmp = _assemble_rh2_service(monkeypatch)
    owner = _owner_loop()
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)

    real_aclose = type(fn._output).aclose

    async def failing_aclose():
        raise OSError("buffer close exploded (test)")

    fn._output.aclose = failing_aclose  # 实例属性覆盖：aclose 抛错
    try:
        report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
        fn_report = report["rollout_fn"]
        assert fn_report["buffer_closed"] is False and "buffer close exploded" in fn_report["close_error"]
        assert report["ok"] is False and report["trigger"] == "shutdown_failure"
        kinds = {p["kind"] for p in report["shutdown_failure"]["problems"]}
        assert {"close_error", "buffer_not_closed"} <= kinds
        disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
        assert disk["ok"] is False and disk["residue"]["rollout_fn_shutdown_failure"]["kind"] == "rollout_fn_shutdown_incomplete"
    finally:
        # 真正关 buffer 唤醒 drain（否则它永远挂在 owner loop 上）
        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(real_aclose(fn._output), owner.loop))
        with pytest.raises((far.RolloutFnClosed, Exception)):
            await drain


# ---------------------------------------------------------------------------
# ④ 正常路径整体 dispose 超时 / 闭包错误 → run 非成功退出（typed ShutdownFailure）
# ---------------------------------------------------------------------------


async def test_dispose_timeout_or_closure_error_makes_run_exit_non_success(world, monkeypatch, tmp_path):
    from miles.utils.rh2_shutdown import ShutdownFailure, dispose_on_owner_loop, raise_if_shutdown_failed

    monkeypatch.setattr(sys.modules["repoharness2.adapters.slime.bringup"].BringupService, "_instance", None)

    class _HangingFn:
        async def aclose(self, deadline_seconds=None):
            await asyncio.sleep(3600)

    t0 = time.monotonic()
    verdict = await dispose_on_owner_loop(_HangingFn(), timeout_seconds=0.2)
    assert time.monotonic() - t0 < 1.0
    assert verdict["ok"] is False and verdict["timed_out"] is True and verdict["errors"]
    with pytest.raises(ShutdownFailure) as exc:  # 无 driver 异常：typed 非成功退出
        raise_if_shutdown_failed(verdict, driver_cause=None, evidence_dir=tmp_path / "ev-timeout")
    assert exc.value.verdict["timed_out"] is True
    marker = json.loads((tmp_path / "ev-timeout" / "shutdown_failure.json").read_text(encoding="utf-8"))
    assert marker["verdict"]["timed_out"] is True and marker["driver_cause"] is None

    class _RaisingFn:
        async def aclose(self, deadline_seconds=None):
            raise RuntimeError("aclose blew up (test)")

    verdict2 = await dispose_on_owner_loop(_RaisingFn(), timeout_seconds=5.0)
    assert verdict2["ok"] is False and verdict2["errors"] and verdict2["timed_out"] is False
    assert verdict2["shutdown_failure"]["problems"][0]["kind"] == "aclose_raised"
    assert verdict2["trigger"] == "shutdown_failure"
    with pytest.raises(ShutdownFailure):
        raise_if_shutdown_failed(verdict2, driver_cause=None, evidence_dir=tmp_path / "ev-error")
    assert (tmp_path / "ev-error" / "shutdown_failure.json").is_file()


# ---------------------------------------------------------------------------
# ⑤ 已有训练异常 + cleanup failure → 仍抛原异常（不改写），cleanup failure 作为 secondary 持久化 + 标记文件
# ---------------------------------------------------------------------------


async def test_dual_loop_driver_error_plus_cleanup_failure_keeps_driver_primary(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop, raise_if_shutdown_failed

    generate, entered, stubborn_tasks = _blocking_generate_factory(world, stubborn_first=True)
    args = _args(world, rh2_shutdown_deadline_sec=0.3)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)
    owner = _owner_loop()
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)

    cause = "RuntimeError: actor_model.train exploded at rollout_id=3"
    report = await dispose_on_owner_loop(fn, driver_cause=cause, timeout_seconds=10.0)
    assert report["ok"] is False and report["trigger"] == "driver_error" and report["primary_cause"] == cause
    assert report["shutdown_failure"] is not None
    [secondary] = report["secondary_causes"]
    assert secondary.startswith("shutdown_failure:") and "active_groups_unfinished" in secondary
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["first_cause"] == cause and disk["trigger"] == "driver_error" and disk["ok"] is False
    assert any("active_groups_unfinished" in s for s in disk["secondary_failures"])  # secondary 持久化
    assert disk["residue"]["unfinished_executions"][0]["reason"] == "active_group_unfinished_after_deadline"
    # driver 异常在途：不抛新异常（原异常由 finally 外层继续传播），落标记文件
    marker_path = raise_if_shutdown_failed(report, driver_cause=cause, evidence_dir=tmp)
    assert marker_path is not None and marker_path.name == "shutdown_failure.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["driver_cause"] == cause and marker["verdict"]["secondary_causes"] == [secondary]
    with pytest.raises(far.RolloutFnClosed):
        await drain
    for task in stubborn_tasks:
        owner.loop.call_soon_threadsafe(task.cancel)
    await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# ⑦ driver 异常与 worker fatal 同时：driver primary、worker secondary、同源去重
# ---------------------------------------------------------------------------


def _filter_fatal_fn(world, monkeypatch):
    async def instant_generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        await asyncio.sleep(0)
        return world.mk_gov_finished_group(prompt_group)

    args = _args(world, dynamic_sampling_filter_path="w5a_dispose_helpers.raising_admission_filter")
    return _build_fn(world, monkeypatch, generate=instant_generate, args=args)


async def test_dual_loop_worker_fatal_alone_is_primary_first_cause(world, monkeypatch):
    """filter fatal（真实 DefaultDataBuffer.put() 内抛）→ worker failed → 无 driver 异常时它是首因。"""

    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from w5a_dispose_helpers import FakeGroupAdmissionFatal

    far, fn, _source = _filter_fatal_fn(world, monkeypatch)
    service, tmp = _assemble_rh2_service(monkeypatch)
    with pytest.raises(FakeGroupAdmissionFatal) as drain_exc:  # 经 run().result() 传回调用方线程
        await _drain_like_production(fn)
    assert drain_exc.value.reason_code == "identity_missing"

    report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
    assert report["rollout_fn"]["worker_state"] == "failed" and report["shutdown_failure"] is None
    assert report["trigger"] == "run_fatal" and "FakeGroupAdmissionFatal(identity_missing)" in report["primary_cause"]
    assert report["ok"] is False and report["secondary_causes"] == []
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["trigger"] == "run_fatal" and "identity_missing" in disk["first_cause"]


async def test_dual_loop_driver_and_worker_fatal_same_origin_deduplicated(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from w5a_dispose_helpers import FakeGroupAdmissionFatal

    far, fn, _source = _filter_fatal_fn(world, monkeypatch)
    service, tmp = _assemble_rh2_service(monkeypatch)
    with pytest.raises(FakeGroupAdmissionFatal) as drain_exc:
        await _drain_like_production(fn)
    # train_async finally 的格式：driver 看到的就是 worker fatal 的传播 → 同源
    driver_cause = f"{type(drain_exc.value).__name__}: {str(drain_exc.value)[:400]}"

    report = await dispose_on_owner_loop(fn, driver_cause=driver_cause, timeout_seconds=10.0)
    assert report["trigger"] == "driver_error" and report["primary_cause"] == driver_cause  # driver = primary
    assert report["worker_fatal_same_origin"] is True and report["secondary_causes"] == []  # 同源只记一次
    assert "FakeGroupAdmissionFatal(identity_missing)" in report["rollout_fn"]["worker_exception"]  # 事实仍保留
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["first_cause"] == driver_cause and disk["secondary_failures"] == [] and disk["ok"] is False


async def test_dual_loop_driver_and_unrelated_worker_fatal_both_kept(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from w5a_dispose_helpers import FakeGroupAdmissionFatal

    far, fn, _source = _filter_fatal_fn(world, monkeypatch)
    service, tmp = _assemble_rh2_service(monkeypatch)
    with pytest.raises(FakeGroupAdmissionFatal):
        await _drain_like_production(fn)
    driver_cause = "ValueError: checkpoint save failed (independent of the worker)"

    report = await dispose_on_owner_loop(fn, driver_cause=driver_cause, timeout_seconds=10.0)
    assert report["trigger"] == "driver_error" and report["primary_cause"] == driver_cause
    assert report["worker_fatal_same_origin"] is False
    [secondary] = report["secondary_causes"]
    assert secondary.startswith("worker_fatal: FakeGroupAdmissionFatal(identity_missing)")
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["first_cause"] == driver_cause and any("worker_fatal" in s for s in disk["secondary_failures"])


# ---------------------------------------------------------------------------
# patch 0013：真实 rh2_group_admission_filter → notify_run_fatal → 提前 close → dispose 后到事实
# ---------------------------------------------------------------------------


def _real_filter_stubborn_fn(world, monkeypatch, *, deadline: float):
    """真实复合 group filter（无六字段身份 → GroupAdmissionFatal → notify_run_fatal）；第一个组瞬间完成
    触发 filter fatal（worker 以它结束），第二个组吞掉取消（dispose 时到期成为未完成残留）。"""

    from repoharness2.adapters.miles.group_admission import GROUP_ADMISSION_FILTER_PATH

    count = [0]
    stubborn_tasks: list[asyncio.Task] = []

    async def generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        count[0] += 1
        if count[0] == 1:
            await asyncio.sleep(0)
            return world.mk_gov_finished_group(prompt_group)
        stubborn_tasks.append(asyncio.current_task())
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await asyncio.sleep(3600)

    args = _args(world, dynamic_sampling_filter_path=GROUP_ADMISSION_FILTER_PATH, rh2_shutdown_deadline_sec=deadline)
    far, fn, source = _build_fn(world, monkeypatch, generate=generate, args=args)
    return far, fn, stubborn_tasks


def _assert_disk_matches_verdict(disk: dict, verdict: dict, *, driver_cause: str):
    rh2 = verdict["rh2"]
    assert disk["first_cause"] == rh2["first_cause"] and "GroupAdmissionFatal" in disk["first_cause"]  # 原首因 = 提前触发的 filter fatal
    assert disk["first_cause_origin"] == "trigger"
    assert f"late_primary(driver_error): {driver_cause}" in disk["secondary_failures"]  # driver 异常并入次生
    assert any(s.startswith("secondary: shutdown_failure:") and "active_groups_unfinished" in s for s in disk["secondary_failures"])
    assert disk["secondary_failures"] == rh2["secondary_failures"]
    [row] = disk["residue"]["unfinished_executions"]  # 具体残留
    assert row["reason"] == "active_group_unfinished_after_deadline" and row["sample_indices"] == [0, 1]
    assert disk["residue"]["rollout_fn_shutdown_failure"]["kind"] == "rollout_fn_shutdown_incomplete"
    assert disk["residue"] == rh2["residue"]
    assert disk["ok"] is False and disk["residue_free"] is False and verdict["ok"] is False
    assert verdict["secondary_causes"] and verdict["primary_cause"] == driver_cause


async def test_dual_loop_real_filter_fatal_then_dispose_while_close_in_progress(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    far, fn, stubborn_tasks = _real_filter_stubborn_fn(world, monkeypatch, deadline=0.3)
    service, tmp = _assemble_rh2_service(monkeypatch)
    service.adapter = _SlowAdapter(1.0)  # 提前 close 会停在 capture_sessions 步 ~1s
    service.registry.register("s-slow", object())
    owner = _owner_loop()

    with pytest.raises(GroupAdmissionFatal) as drain_exc:  # 真实 filter 在 put() 内抛 → worker 以它结束
        await _drain_like_production(fn)
    assert service._close_task is not None and service._close_task.get_loop() is owner.loop  # notify 已提前触发 close
    assert service.shutdown_report is None  # 仍在进行中
    driver_cause = "RuntimeError: trainer failure (independent)"
    verdict = await dispose_on_owner_loop(fn, driver_cause=driver_cause, timeout_seconds=10.0)
    assert verdict["rollout_fn"]["active_groups_unfinished"] == 1 and verdict["worker_fatal_same_origin"] is False
    report = service.shutdown_report
    assert report is not None and [m["phase"] for m in report.late_merges] == ["initial", "during_close"]
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    _assert_disk_matches_verdict(disk, verdict, driver_cause=driver_cause)
    assert drain_exc.value.reason_code in disk["first_cause"]
    for task in stubborn_tasks:
        owner.loop.call_soon_threadsafe(task.cancel)
    await asyncio.sleep(0.05)


async def test_dual_loop_real_filter_fatal_then_dispose_after_close_completed(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal

    far, fn, stubborn_tasks = _real_filter_stubborn_fn(world, monkeypatch, deadline=0.3)
    service, tmp = _assemble_rh2_service(monkeypatch)
    owner = _owner_loop()

    with pytest.raises(GroupAdmissionFatal):
        await _drain_like_production(fn)
    await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(service.close(), owner.loop))  # 等提前 close 完成
    disk0 = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk0["residue_free"] is True and disk0["secondary_failures"] == []  # 提前报告：只有 filter fatal
    driver_cause = "RuntimeError: trainer failure (independent)"
    verdict = await dispose_on_owner_loop(fn, driver_cause=driver_cause, timeout_seconds=10.0)
    report = service.shutdown_report
    assert [m["phase"] for m in report.late_merges] == ["initial", "after_close"]
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))  # 已原子重写
    _assert_disk_matches_verdict(disk, verdict, driver_cause=driver_cause)
    assert not (tmp / "shutdown_report.json.tmp").exists()
    for task in stubborn_tasks:
        owner.loop.call_soon_threadsafe(task.cancel)
    await asyncio.sleep(0.05)


class _SlowAdapter:
    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.dropped: list[str] = []

    async def drop_session(self, sid: str, *, wait_timeout: float = 5.0) -> None:
        await asyncio.sleep(self.delay)
        self.dropped.append(sid)


# ---------------------------------------------------------------------------
# patch 0013：同源判定 = 与 train_async 序列化格式严格全等；子串/空消息不再猜
# ---------------------------------------------------------------------------


def test_same_origin_requires_exact_serialization_match(world):
    from miles.utils.rh2_shutdown import _same_origin, serialize_driver_cause

    worker = RuntimeError("timeout")
    assert _same_origin(worker, "RuntimeError: optimizer timeout after all-reduce") is False  # 子串不算同源
    assert _same_origin(RuntimeError(""), "RuntimeError: anything") is False  # 空消息不匹配任意同类
    assert _same_origin(worker, serialize_driver_cause(worker)) is True  # 真同源：严格全等
    assert _same_origin(worker, "RuntimeError: timeout ") is False  # 多一个空格也不是
    assert serialize_driver_cause(ValueError("x" * 500)) == "ValueError: " + "x" * 400


async def test_dual_loop_substring_driver_cause_keeps_worker_as_secondary(world, monkeypatch):
    """反例：driver 串包含 worker 消息为子串但不全等 → 两条原因都保留（宁可重复不静默删）。"""

    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from w5a_dispose_helpers import FakeGroupAdmissionFatal

    far, fn, _source = _filter_fatal_fn(world, monkeypatch)
    service, tmp = _assemble_rh2_service(monkeypatch)
    with pytest.raises(FakeGroupAdmissionFatal) as drain_exc:
        await _drain_like_production(fn)
    driver_cause = f"FakeGroupAdmissionFatal: {drain_exc.value} (wrapped by the trainer)"  # 子串包含，非全等

    report = await dispose_on_owner_loop(fn, driver_cause=driver_cause, timeout_seconds=10.0)
    assert report["worker_fatal_same_origin"] is False
    [secondary] = report["secondary_causes"]
    assert secondary.startswith("worker_fatal: FakeGroupAdmissionFatal(identity_missing)")
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["first_cause"] == driver_cause and any("worker_fatal" in s for s in disk["secondary_failures"])


# ---------------------------------------------------------------------------
# owner loop 上阻塞在 put/get 的 waiter：被 DataBufferClosed 唤醒；整体超时有界
# ---------------------------------------------------------------------------


async def test_dual_loop_buffer_waiters_wake_with_typed_error(world):
    world.install_sglang_stub()
    from miles.rollout.fully_async_data_buffer import (
        DataBufferClosed,
        DataBufferConstructorInput,
        DefaultDataBuffer,
    )

    owner = _owner_loop()
    args = world.mk_miles_args(async_data_buffer_capacity_factor=0.5, rollout_batch_size=2)  # 容量 1 组
    full = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=lambda pg: None))
    empty = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=lambda pg: None))
    pg = world.mk_gov_prompt_group("a")

    def post(coro):
        return asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, owner.loop))

    await post(full.put(world.mk_entry(pg, world.mk_gov_finished_group(pg))))
    put_waiter = post(full.put(world.mk_entry(pg, world.mk_gov_finished_group(pg))))
    get_waiter = post(empty.get(current_version=1))
    await asyncio.sleep(0.1)
    assert not put_waiter.done() and not get_waiter.done()  # 真的阻塞在 owner loop 的 _cond.wait()

    await post(full.aclose())
    await post(empty.aclose())
    with pytest.raises(DataBufferClosed) as put_exc:
        await put_waiter
    with pytest.raises(DataBufferClosed) as get_exc:
        await get_waiter
    assert put_exc.value.op == "put" and get_exc.value.op == "get"
    with pytest.raises(DataBufferClosed):  # 关闭后 buffer 内已有的组也不再交出
        await post(full.get(current_version=1))
    await post(full.aclose())  # 幂等


# ---------------------------------------------------------------------------
# 源码事实：dispose 投回 owner loop 并返回 verdict；train_async try 紧随创建、finally 走 raise_if_shutdown_failed
# ---------------------------------------------------------------------------


def test_dispose_owner_loop_and_train_async_try_placement_source_facts(world):
    rm = (world.miles_root / "miles" / "ray" / "rollout" / "rollout_manager.py").read_text(encoding="utf-8")
    assert "    async def dispose(self, driver_cause=None):" in rm
    body = rm[rm.index("    async def dispose(self, driver_cause=None):"):]
    body = body[: body.index("    # -------------------------- data generation")]
    i_post = body.index("await dispose_on_owner_loop(self.generate_rollout, driver_cause=driver_cause")
    i_orig = body.index('getattr(self.data_source, "close", None)')
    i_return = body.index("        return verdict")
    assert i_post < i_orig < i_return  # 先投回 owner loop 关 rollout fn + rh2，再原有 dispose，最后返回 verdict
    assert "await aclose()" not in body and "await close_bringup_service(" not in body  # 不在 actor loop 上直接 await

    helper = (world.miles_root / "miles" / "utils" / "rh2_shutdown.py").read_text(encoding="utf-8")
    assert "asyncio.run_coroutine_threadsafe(" in helper and "asyncio.wrap_future(" in helper
    assert "get_async_loop()" in helper and "asyncio.wait_for(" in helper
    assert "class ShutdownFailure" in helper and "def raise_if_shutdown_failed" in helper

    ta = (world.miles_root / "train_async.py").read_text(encoding="utf-8")
    i_create = ta.index('rollout_manager, num_rollout_per_epoch = create_rollout_manager(args, pgs["rollout"])')
    i_try = ta.index("    try:\n", i_create)
    between = ta[i_create + len('rollout_manager, num_rollout_per_epoch = create_rollout_manager(args, pgs["rollout"])'):i_try]
    assert all(line.strip() == "" or line.strip().startswith("#") for line in between.splitlines())  # try 紧随其后
    assert ta.index("await create_training_models(") > i_try  # 模型初始化在 try 内
    assert ta.index("await actor_model.update_weights()") > i_try  # 首次权重发布在 try 内
    i_drain = ta.index("        await eval_dispatcher.drain()")
    i_finally = ta.index("    finally:\n        driver_exc = sys.exc_info()[1]")
    i_dispose = ta.index("            verdict = await rollout_manager.dispose.remote(driver_cause=driver_cause)")
    i_policy = ta.index("        raise_if_shutdown_failed(verdict, driver_cause=driver_cause)")
    assert i_try < i_drain < i_finally < i_dispose < i_policy
    assert ta.count("rollout_manager.dispose.remote(") == 1
    assert "from miles.utils.rh2_shutdown import raise_if_shutdown_failed" in ta

    far_src = (world.miles_root / "miles" / "rollout" / "fully_async_rollout.py").read_text(encoding="utf-8")
    assert "async def aclose(self, deadline_seconds: float | None = None) -> dict:" in far_src
    assert "DEFAULT_SHUTDOWN_DEADLINE_SEC = 60.0" in far_src and "RH2_MILES_SHUTDOWN_DEADLINE_SEC" in far_src
    assert "task.rh2_group_facts = _group_facts(prompt_group)" in far_src
    aclose_body = far_src[far_src.index("async def aclose(") : far_src.index("    @property\n    def closed")]
    assert aclose_body.index("finally:") < aclose_body.index("await aclose()")  # buffer 关闭在 finally
    buf_src = (world.miles_root / "miles" / "rollout" / "fully_async_data_buffer.py").read_text(encoding="utf-8")
    assert "class DataBufferClosed" in buf_src and "async def aclose(self) -> None:" in buf_src


# ---------------------------------------------------------------------------
# I13（第 2 组 §3，owner 2026-09-09 已批；Codex 计划审查 R2）：中间等待超时、最终安全收口 → 成功；
# 晚到异常 → 仍失败。成功例走真实 fork verdict + rh2 报告合成（resolve_external_wait_residue 重写磁盘报告）。
# ---------------------------------------------------------------------------


def _late_settling_generate_factory(world, *, settle_delay: float, late_exception: bool = False):
    """generate_and_rm_group 替身：挂起直到被取消；收到取消后再花 settle_delay 秒收口（模拟 adapter 侧
    session cleanup），然后结束（late_exception=True 时以 RuntimeError 结束 = 晚到异常）。"""

    entered = threading.Event()
    count = [0]

    async def generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        count[0] += 1
        if count[0] == 2:
            entered.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await asyncio.sleep(settle_delay)
            if late_exception:
                raise RuntimeError("late boom after cancel")
            raise

    return generate, entered


async def test_dual_loop_wait_timeout_then_safe_completion_is_ok(world, monkeypatch):
    """取消等待 0.2s 到期时组 task 还在收口（首次快照 = 超时）；再过 0.1s 它们安全结束；rh2 关停链
    execution_closure 完整 → 复查通过：最终 verdict ok=true，等待快照保留为 resolved_wait_timeouts，
    rh2 磁盘报告被重写为 ok=true，不写 marker。"""

    from miles.utils.rh2_shutdown import dispose_on_owner_loop, raise_if_shutdown_failed

    generate, entered = _late_settling_generate_factory(world, settle_delay=0.3)
    args = _args(world, rh2_shutdown_deadline_sec=0.2)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)
    t0 = time.monotonic()
    report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
    elapsed = time.monotonic() - t0
    assert elapsed < 3.0, elapsed
    fn_report = report["rollout_fn"]
    assert fn_report["deadline_exceeded"] is True and fn_report["active_groups_unfinished"] >= 1  # 首次快照：超时
    assert report["ok"] is True and report["cleanup_ok"] is True, report
    assert report["primary_cause"] is None and report["trigger"] == "owner_close" and report["errors"] == []
    failure = report["shutdown_failure"]
    assert failure["kind"] == "rollout_fn_shutdown_incomplete" and failure["resolved_by_final_closure"] is True
    assert failure["final_state"]["all_settled"] is True and failure["final_state"]["late_group_exceptions"] == []
    assert all(g["state"] == "cancelled" for g in failure["final_state"]["active_groups"])
    assert report["resolved_wait_timeouts"] is failure
    rh2 = report["rh2"]
    assert rh2["ok"] is True and rh2["cleanup_ok"] is True and rh2["wait_residue_resolved"] is True
    assert rh2["execution_closure"]["complete"] is True and rh2["residue"]["rollout_fn_shutdown_failure"] is None
    assert rh2["resolved_wait_timeouts"][0]["rows"][0]["source"] == "miles_rollout_fn"
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is True and disk["residue_free"] is True and disk["first_cause"] is None
    assert disk["trigger"] == "owner_close" and disk["resolved_wait_timeouts"][0]["final_state"]["all_settled"] is True
    assert raise_if_shutdown_failed(report, driver_cause=None, evidence_dir=tmp) is None
    assert not (tmp / "shutdown_failure.json").exists()
    with pytest.raises(far.RolloutFnClosed):
        await drain


async def test_dual_loop_late_exception_after_wait_timeout_keeps_the_run_failed(world, monkeypatch):
    """同形态但组 task 在期限后以异常结束 = 晚到异常，不是安全收口：verdict 仍 false，首因为等待失败，
    rh2 报告晚到并入同一首因（trigger 升级为 shutdown_failure）。"""

    from miles.utils.rh2_shutdown import ShutdownFailure, dispose_on_owner_loop, raise_if_shutdown_failed

    generate, entered = _late_settling_generate_factory(world, settle_delay=0.3, late_exception=True)
    args = _args(world, rh2_shutdown_deadline_sec=0.2)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)
    report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
    failure = report["shutdown_failure"]
    assert report["ok"] is False and failure["resolved_by_final_closure"] is False
    assert failure["final_state"]["all_settled"] is True
    assert failure["final_state"]["late_group_exceptions"] and "late boom" in failure["final_state"]["late_group_exceptions"][0]
    assert report["trigger"] == "shutdown_failure" and report["primary_cause"].startswith("shutdown_failure:")
    assert report["resolved_wait_timeouts"] is None and report["rh2"]["wait_residue_resolved"] is False
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["trigger"] == "shutdown_failure" and "active_groups_unfinished" in disk["first_cause"]
    assert disk["resolved_wait_timeouts"] == [] and disk["residue"]["rollout_fn_shutdown_failure"] is not None
    with pytest.raises(ShutdownFailure):
        raise_if_shutdown_failed(report, driver_cause=None, evidence_dir=tmp)
    with pytest.raises(far.RolloutFnClosed):
        await drain


async def test_dual_loop_safe_completion_without_closure_evidence_stays_failed(world, monkeypatch):
    """同形态、task 也安全结束，但 rh2 侧拿不到"rollout 容器已确认释放"的证据（一个 attempt 的 lease 未记
    释放）→ execution_closure 不完整，等待快照不解消：verdict 仍 false，首因为等待失败。"""

    from miles.utils.rh2_shutdown import ShutdownFailure, dispose_on_owner_loop, raise_if_shutdown_failed

    generate, entered = _late_settling_generate_factory(world, settle_delay=0.3)
    args = _args(world, rh2_shutdown_deadline_sec=0.2)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)
    service.orchestrator = SimpleNamespace(
        audits=[SimpleNamespace(lease=SimpleNamespace(container_id="rh2-c1"), lease_released=False, failure_records=[])],
        cleanup_quarantine=[],
    )
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)
    report = await dispose_on_owner_loop(fn, timeout_seconds=10.0)
    failure = report["shutdown_failure"]
    assert failure["final_state"]["all_settled"] is True and failure["final_state"]["late_group_exceptions"] == []
    assert report["ok"] is False and failure["resolved_by_final_closure"] is False
    closure = report["rh2"]["execution_closure"]
    assert closure["complete"] is False and closure["rollout_containers_unreleased"] == ["rh2-c1"]
    assert report["trigger"] == "shutdown_failure" and report["resolved_wait_timeouts"] is None
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["ok_if_wait_residue_resolved"] is False and disk["resolved_wait_timeouts"] == []
    with pytest.raises(ShutdownFailure):
        raise_if_shutdown_failed(report, driver_cause=None, evidence_dir=tmp)
    with pytest.raises(far.RolloutFnClosed):
        await drain
