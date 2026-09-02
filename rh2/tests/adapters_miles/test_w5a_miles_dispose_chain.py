"""W5a（codex 复核 #1 / patch 0011）：miles 生产退出链——**真实双 event-loop 拓扑**重放。

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
    service._uninstall_signal_shutdown = None
    service._profile_args = SimpleNamespace(
        rollout_batch_size=2, n_samples_per_prompt=2, num_rollout=1, rollout_max_response_len=64,
        async_data_buffer_capacity_factor=2.0,
    )
    service.registry = CaptureRegistry()
    service.adapter = SimpleNamespace(drop_session=None)
    service.app_handle = None
    service.grading_manager = SWEGradingManager(GradingManagerConfig(), docker=None)
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
# ① 正常 worker：owner loop 上的整体关停从调用方 loop 近 0s 完成，无外部 timer
# ---------------------------------------------------------------------------


async def test_dual_loop_normal_dispose_completes_without_external_timer(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

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
    assert "timed_out" not in report and report["errors"] == []
    fn_report = report["rollout_fn"]
    assert fn_report["worker_state"] == "cancelled" and fn_report["active_groups_cancelled"] == 2
    assert fn_report["active_groups_unfinished"] == 0 and fn_report["deadline_exceeded"] is False
    assert fn_report["buffer_closed"] is True and fn_report["deadline_seconds"] == 60.0  # 默认期限
    assert report["trigger"] == "owner_close" and report["first_cause"] is None
    assert report["rh2"]["ok"] is True  # rh2 关停链在 owner loop 上真实跑完
    assert service.shutdown_report is not None and service._close_task.get_loop() is owner.loop  # rh2 链在 owner loop
    with pytest.raises(far.RolloutFnClosed):  # drain waiter 被唤醒并 typed 退出（经 run().result() 传回调用方线程）
        await drain
    assert source.served == 2
    assert json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))["ok"] is True



# ---------------------------------------------------------------------------
# ② 取消不响应的 active group：到期放弃、unfinished=1、buffer 仍关、RH2 链仍执行
# ---------------------------------------------------------------------------


async def test_dual_loop_stubborn_active_group_is_abandoned_after_deadline(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

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
    assert report["rh2"] is not None and service.shutdown_report is not None  # RH2 链仍执行（兜底容器/会话）
    assert (tmp / "shutdown_report.json").is_file()
    with pytest.raises(far.RolloutFnClosed):
        await drain
    # 被放弃的 task 仍在 owner loop 上：测试结束前收掉
    for task in stubborn_tasks:
        assert not task.done()
        owner.loop.call_soon_threadsafe(task.cancel)
    await asyncio.sleep(0.05)


async def test_dispose_on_owner_loop_total_timeout_is_bounded(world, monkeypatch):
    """整体闭包超时：不抛、记 timed_out、调用方继续原有 dispose。"""

    from miles.utils.rh2_shutdown import dispose_on_owner_loop

    class _HangingFn:
        async def aclose(self, deadline_seconds=None):
            await asyncio.sleep(3600)

    monkeypatch.setattr(sys.modules["repoharness2.adapters.slime.bringup"].BringupService, "_instance", None)
    t0 = time.monotonic()
    report = await dispose_on_owner_loop(_HangingFn(), timeout_seconds=0.2)
    assert time.monotonic() - t0 < 1.0
    assert report["timed_out"] is True and report["timeout_seconds"] == 0.2


# ---------------------------------------------------------------------------
# ③ owner loop 上阻塞在 put/get 的 waiter：被 DataBufferClosed 唤醒
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
# ④ filter fatal：worker 以 GroupAdmissionFatal 结束 → 首因进 rh2 磁盘报告
# ---------------------------------------------------------------------------


async def test_dual_loop_filter_fatal_becomes_first_cause_in_rh2_disk_report(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop
    from w5a_dispose_helpers import FakeGroupAdmissionFatal

    async def instant_generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        await asyncio.sleep(0)
        return world.mk_gov_finished_group(prompt_group)

    args = _args(world, dynamic_sampling_filter_path="w5a_dispose_helpers.raising_admission_filter")
    far, fn, _source = _build_fn(world, monkeypatch, generate=instant_generate, args=args)
    service, tmp = _assemble_rh2_service(monkeypatch)

    with pytest.raises(FakeGroupAdmissionFatal) as drain_exc:  # 经 run().result() 传回调用方线程
        await _drain_like_production(fn)
    assert drain_exc.value.reason_code == "identity_missing"

    report = await dispose_on_owner_loop(fn, driver_cause="RuntimeError: driver saw the fatal", timeout_seconds=10.0)
    assert report["rollout_fn"]["worker_state"] == "failed"
    assert report["trigger"] == "run_fatal"  # worker 自己的 fatal 比 driver cause 更精确，优先
    assert "FakeGroupAdmissionFatal(identity_missing)" in report["first_cause"]
    assert report["rh2"]["ok"] is False
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["trigger"] == "run_fatal"
    assert disk["first_cause_origin"] == "trigger" and "identity_missing" in disk["first_cause"]
    assert service.shutdown_report.first_cause == disk["first_cause"]


# ---------------------------------------------------------------------------
# ⑤ driver cause：worker 健康 + 训练侧异常 → 报告 ok=false、first_cause = driver cause
# ---------------------------------------------------------------------------


async def test_dual_loop_driver_cause_reaches_rh2_report_when_worker_is_healthy(world, monkeypatch):
    from miles.utils.rh2_shutdown import dispose_on_owner_loop

    generate, entered, _ = _blocking_generate_factory(world)
    far, fn, _source = _build_fn(world, monkeypatch, generate=generate, args=_args(world))
    service, tmp = _assemble_rh2_service(monkeypatch)
    drain = asyncio.create_task(_drain_like_production(fn))
    await asyncio.to_thread(entered.wait, 5.0)

    cause = "RuntimeError: actor_model.train exploded at rollout_id=3"
    report = await dispose_on_owner_loop(fn, driver_cause=cause, timeout_seconds=10.0)
    assert report["rollout_fn"]["worker_state"] == "cancelled" and report["rollout_fn"]["worker_exception"] is None
    assert report["trigger"] == "driver_error" and report["first_cause"] == cause
    assert report["rh2"]["ok"] is False and report["rh2"]["first_cause"] == cause
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["ok"] is False and disk["first_cause"] == cause and disk["trigger"] == "driver_error"
    with pytest.raises(far.RolloutFnClosed):
        await drain


# ---------------------------------------------------------------------------
# ⑥ 源码事实：dispose 投回 owner loop + driver_cause；train_async 的 try 紧随 RolloutManager 创建
# ---------------------------------------------------------------------------


def test_dispose_owner_loop_and_train_async_try_placement_source_facts(world):
    rm = (world.miles_root / "miles" / "ray" / "rollout" / "rollout_manager.py").read_text(encoding="utf-8")
    assert "    async def dispose(self, driver_cause=None):" in rm
    body = rm[rm.index("    async def dispose(self, driver_cause=None):"):]
    body = body[: body.index("    # -------------------------- data generation")]
    i_post = body.index("await dispose_on_owner_loop(self.generate_rollout, driver_cause=driver_cause")
    i_orig = body.index('getattr(self.data_source, "close", None)')
    assert i_post < i_orig  # 先投回 owner loop 关 rollout fn + rh2，再原有 dispose
    assert "await aclose()" not in body and "await close_bringup_service(" not in body  # 不再在 actor loop 上直接 await

    helper = (world.miles_root / "miles" / "utils" / "rh2_shutdown.py").read_text(encoding="utf-8")
    assert "asyncio.run_coroutine_threadsafe(" in helper and "asyncio.wrap_future(" in helper
    assert "get_async_loop()" in helper and "asyncio.wait_for(" in helper

    ta = (world.miles_root / "train_async.py").read_text(encoding="utf-8")
    i_create = ta.index('rollout_manager, num_rollout_per_epoch = create_rollout_manager(args, pgs["rollout"])')
    i_try = ta.index("    try:\n", i_create)
    between = ta[i_create + len('rollout_manager, num_rollout_per_epoch = create_rollout_manager(args, pgs["rollout"])'):i_try]
    assert all(line.strip() == "" or line.strip().startswith("#") for line in between.splitlines())  # try 紧随其后
    assert ta.index("await create_training_models(") > i_try  # 模型初始化在 try 内
    assert ta.index("await actor_model.update_weights()") > i_try  # 首次权重发布在 try 内
    i_drain = ta.index("        await eval_dispatcher.drain()")
    i_finally = ta.index("    finally:\n        driver_exc = sys.exc_info()[1]")
    i_dispose = ta.index("            await rollout_manager.dispose.remote(driver_cause=driver_cause)")
    assert i_try < i_drain < i_finally < i_dispose
    assert ta.count("rollout_manager.dispose.remote(") == 1

    far_src = (world.miles_root / "miles" / "rollout" / "fully_async_rollout.py").read_text(encoding="utf-8")
    assert "async def aclose(self, deadline_seconds: float | None = None) -> dict:" in far_src
    assert "DEFAULT_SHUTDOWN_DEADLINE_SEC = 60.0" in far_src and "RH2_MILES_SHUTDOWN_DEADLINE_SEC" in far_src
    aclose_body = far_src[far_src.index("async def aclose(") : far_src.index("    @property\n    def closed")]
    assert aclose_body.index("finally:") < aclose_body.index("await aclose()")  # buffer 关闭在 finally
    buf_src = (world.miles_root / "miles" / "rollout" / "fully_async_data_buffer.py").read_text(encoding="utf-8")
    assert "class DataBufferClosed" in buf_src and "async def aclose(self) -> None:" in buf_src
