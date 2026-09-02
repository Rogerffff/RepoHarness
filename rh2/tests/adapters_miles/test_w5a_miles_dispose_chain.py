"""W5a（codex 复核 #1）：miles 生产退出链的窄 commit——FullyAsyncRolloutFn.aclose /
DefaultDataBuffer.aclose / RolloutManager.dispose 顺序 / train_async try-finally。

integration_base 专属（pin 树没有这些接口）。真实 FullyAsyncRolloutFn + 真实 DefaultDataBuffer
+ 真实 scheduler；只替换 GenerateState（需要 tokenizer/引擎）与 generate_and_rm_group
（需要引擎）两个引擎面。RolloutManager 是 Ray actor（import 需要 sglang/ray 全家），其
dispose 顺序与 train_async 的 try/finally 用源码事实钉死（与运行时 import 同一 checkout）。
"""

from __future__ import annotations

import asyncio
import json
import sys
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
    被引用符号的 stub 顶替——与 conftest 的 ray/sglang stub 同一性质（环境噪音，不复刻行为）。
    被测对象 FullyAsyncRolloutFn / DefaultDataBuffer / scheduler 全部真实。"""

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

    # 模块若已被本文件前一个测试导入，模块内绑定的是上一次的 stub 符号：直接改属性
    monkeypatch.setattr(far, "GenerateState", _StubGenerateState)
    monkeypatch.setattr(far, "generate_and_rm_group", generate)
    source = _DataSource(world, args.n_samples_per_prompt)
    fn = far.FullyAsyncRolloutFn(RolloutFnConstructorInput(args=args, data_source=source))
    return far, fn, source


async def _wait_until(pred, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not pred():
        assert time.monotonic() < deadline, "条件未在超时内成立"
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# 1. DefaultDataBuffer.aclose：阻塞在 put/get 的 waiter 以 typed 异常退出
# ---------------------------------------------------------------------------


async def test_buffer_aclose_wakes_put_and_get_waiters_with_typed_error(world):
    from miles.rollout.fully_async_data_buffer import (
        DataBufferClosed,
        DataBufferConstructorInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args(async_data_buffer_capacity_factor=0.5, rollout_batch_size=2)  # 容量 1 组
    full = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=lambda pg: None))
    empty = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=lambda pg: None))
    pg = world.mk_gov_prompt_group("a")
    await full.put(world.mk_entry(pg, world.mk_gov_finished_group(pg)))
    put_waiter = asyncio.create_task(full.put(world.mk_entry(pg, world.mk_gov_finished_group(pg))))
    get_waiter = asyncio.create_task(empty.get(current_version=1))
    await asyncio.sleep(0.05)
    assert not put_waiter.done() and not get_waiter.done()  # 真的阻塞在 _cond.wait()

    await full.aclose()
    await empty.aclose()
    with pytest.raises(DataBufferClosed) as put_exc:
        await put_waiter
    with pytest.raises(DataBufferClosed) as get_exc:
        await get_waiter
    assert put_exc.value.op == "put" and get_exc.value.op == "get"
    assert full.closed and empty.closed
    # 关闭后：已在 buffer 里的组也不再交出（训练不得消费关停后的组）；put 直接拒
    with pytest.raises(DataBufferClosed):
        await full.get(current_version=1)
    with pytest.raises(DataBufferClosed):
        await empty.put(world.mk_entry(pg, world.mk_gov_finished_group(pg)))
    await full.aclose()  # 幂等


# ---------------------------------------------------------------------------
# 2. FullyAsyncRolloutFn.aclose：停新提交 → 取消 worker/active → 唤醒 drain waiter → 关闭后拒绝
# ---------------------------------------------------------------------------


async def test_rollout_fn_aclose_stops_worker_active_groups_and_wakes_drain_waiter(world, monkeypatch):
    world.install_sglang_stub()  # base_types 链模块级拉 sglang 两个符号
    from miles.rollout.base_types import RolloutFnTrainInput

    entered = 0
    release = asyncio.Event()

    async def blocking_generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        nonlocal entered
        entered += 1
        await release.wait()  # 永不放行：模拟关停时刻仍在跑的 rollout
        return world.mk_gov_finished_group(prompt_group)

    far, fn, source = _build_fn(world, monkeypatch, generate=blocking_generate, args=_args(world))
    drain = asyncio.create_task(fn(RolloutFnTrainInput(rollout_id=0, weight_version=1)))
    await _wait_until(lambda: entered == 2)  # batch=2 → 2 个组在飞
    assert fn._worker is not None and not fn._worker.done()
    active = list(fn._active_groups)
    assert len(active) == 2 and all(not t.done() for t in active)
    assert not drain.done()  # drain 阻塞在 buffer.get()

    report = await fn.aclose()
    assert report["worker_state"] == "cancelled" and report["worker_exception"] is None
    assert report["active_groups_cancelled"] == 2 and report["buffer_closed"] is True
    assert fn._worker.done() and fn._worker.cancelled()
    assert all(t.done() and t.cancelled() for t in active)
    assert fn._output.closed
    with pytest.raises(far.RolloutFnClosed) as drain_exc:  # drain waiter 被唤醒并以 typed 异常退出
        await drain
    assert drain_exc.value.op == "get"
    # 关闭后：train / eval 调用与提交都 typed 拒绝；aclose 幂等
    with pytest.raises(far.RolloutFnClosed) as again:
        await fn(RolloutFnTrainInput(rollout_id=1, weight_version=1))
    assert again.value.op == "train"
    with pytest.raises(far.RolloutFnClosed):
        fn._submit_one_group()
    assert source.served == 2  # 关闭后没有再取任何 prompt 组
    assert (await fn.aclose()) is report


async def test_rollout_fn_aclose_preserves_worker_exception_as_first_cause_for_rh2(world, monkeypatch):
    """filter fatal 路径：dynamic filter 在 buffer.put() 内抛 fatal → worker 以该异常结束 →
    drain 报该异常 → aclose 报告 worker_exception 保留它 → close_bringup_service 以它为首因。"""

    world.install_sglang_stub()  # base_types 链模块级拉 sglang 两个符号
    from miles.rollout.base_types import RolloutFnTrainInput
    from w5a_dispose_helpers import FakeGroupAdmissionFatal

    async def instant_generate(state, prompt_group, *, sampling_params, evaluation, sample_done_callback):
        await asyncio.sleep(0)
        return world.mk_gov_finished_group(prompt_group)

    args = _args(world, dynamic_sampling_filter_path="w5a_dispose_helpers.raising_admission_filter")
    far, fn, _source = _build_fn(world, monkeypatch, generate=instant_generate, args=args)
    with pytest.raises(FakeGroupAdmissionFatal) as drain_exc:
        await fn(RolloutFnTrainInput(rollout_id=0, weight_version=1))
    assert drain_exc.value.reason_code == "identity_missing"
    assert fn._worker.done() and not fn._worker.cancelled()

    report = await fn.aclose()
    assert report["worker_state"] == "failed"
    assert report["worker_exception"] is drain_exc.value  # 首因原对象保留
    assert report["buffer_closed"] is True

    # rh2 侧：dispose 把 worker_exception 作为 first_cause 传入关停入口
    import repoharness2.adapters.slime.bringup as bringup
    from repoharness2.adapters.slime.capture_wire import CaptureRegistry
    from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager
    from repoharness2.grading.queue import GradingQueue, GradingQueueConfig
    from repoharness2.shutdown import LifecycleState, ShutdownTimeouts

    import tempfile

    service = object.__new__(bringup.BringupService)
    tmp = Path(tempfile.mkdtemp(prefix="w5a-dispose-"))
    monkeypatch.setattr(bringup, "ARTIFACT_DIR", tmp)
    service.shutdown_timeouts = ShutdownTimeouts(inflight_grace=0.05, inflight_cancel_wait=1.0, grading_drain=1.0,
                                                 grading_manager=1.0, capture_sessions=1.0, adapter_http=1.0,
                                                 container_residue=1.0, resource_closure=10.0, evidence=1.0)
    service.lifecycle = LifecycleState()
    service.lifecycle.on_fatal = service._on_run_fatal
    service._close_task = None
    service.shutdown_report = None
    service._fatals_during_close = []
    service._closing_report = None
    service._uninstall_signal_shutdown = None
    service._profile_args = SimpleNamespace(rollout_batch_size=2, n_samples_per_prompt=2, num_rollout=1,
                                            rollout_max_response_len=64, async_data_buffer_capacity_factor=2.0)
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

    rh2_report = await bringup.close_bringup_service(
        reason="rollout_manager_dispose", first_cause=report["worker_exception"]
    )
    assert rh2_report is not None and rh2_report.trigger == "run_fatal"
    assert rh2_report.first_cause_origin == "trigger" and "identity_missing" in rh2_report.first_cause
    assert not rh2_report.ok
    disk = json.loads((tmp / "shutdown_report.json").read_text(encoding="utf-8"))
    assert disk["first_cause"] == rh2_report.first_cause and disk["ok"] is False
    estimate = json.loads((tmp / "resource_closure.json").read_text(encoding="utf-8"))["memory_estimate"]
    assert estimate["inputs"]["buffer_capacity_groups"] == 4  # capacity_factor 2.0 × batch 2


# ---------------------------------------------------------------------------
# 3. RolloutManager.dispose 顺序 + train_async try/finally（源码事实，与运行时同一 checkout）
# ---------------------------------------------------------------------------


def test_dispose_order_and_train_async_finally_source_facts(world):
    rm = (world.miles_root / "miles" / "ray" / "rollout" / "rollout_manager.py").read_text(encoding="utf-8")
    assert "    async def dispose(self):" in rm
    body = rm[rm.index("    async def dispose(self):"):]
    body = body[: body.index("    # -------------------------- data generation")]
    i_aclose = body.index('getattr(self.generate_rollout, "aclose", None)')
    i_await_aclose = body.index("await aclose()")
    i_rh2 = body.index("await close_bringup_service(")
    i_first_cause = body.index('first_cause=first_cause')
    i_orig = body.index('getattr(self.data_source, "close", None)')
    assert i_aclose < i_await_aclose < i_rh2 < i_orig  # 停 producer → 关 rh2 → 原有 dispose
    assert i_rh2 < i_first_cause < i_orig
    assert body.count("except Exception") >= 2  # 每段吞异常记日志：异常路径也走完

    ta = (world.miles_root / "train_async.py").read_text(encoding="utf-8")
    assert "import sys\n" in ta
    i_try = ta.index("    try:\n        weights_dirty_since_publish = False")
    i_drain = ta.index("        await eval_dispatcher.drain()")
    i_finally = ta.index("    finally:\n        exiting_with_error = sys.exc_info()[0] is not None")
    i_dispose = ta.index("            await rollout_manager.dispose.remote()")
    assert i_try < i_drain < i_finally < i_dispose  # drain 只在正常路径；dispose 在 finally
    assert ta.count("rollout_manager.dispose.remote()") == 1

    far_src = (world.miles_root / "miles" / "rollout" / "fully_async_rollout.py").read_text(encoding="utf-8")
    assert "async def aclose(self) -> dict:" in far_src and "class RolloutFnClosed" in far_src
    buf_src = (world.miles_root / "miles" / "rollout" / "fully_async_data_buffer.py").read_text(encoding="utf-8")
    assert "class DataBufferClosed" in buf_src and "async def aclose(self) -> None:" in buf_src
