"""FA-1 生产接线薄壳测试（codex 轮次 6 严重 1 的修复验证）。

`fa_bringup.rollout_entry` 是 slime `--rollout-function-path` 的真实入口——
本文件用假件（fake buffer / fake orchestrator）驱动它的全部编排逻辑：
组供给 → 逐 execution 分派 → 交付聚合 → 整组弃置账目 → 收满批次返回；
外加场景 21（eval fail-fast）与配置缺失 fail-fast。GPU 侧只剩
"slime 真把它当入口调用"这一件事（FA-5 首检项）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))
_SLIME_ROOT = Path(__file__).resolve().parents[3] / "reference" / "slime"
if _SLIME_ROOT.exists():
    sys.path.insert(0, str(_SLIME_ROOT))

from fa_bringup.rollout_entry import (  # noqa: E402
    FaEntryError,
    FaRolloutService,
    generate_rollout_async,
)
from repoharness2.adapters.slime.generate import parse_bool_env_flag  # noqa: E402


class FakeSample:
    def __init__(self, name: str, remove: bool = False) -> None:
        self.name = name
        self.remove_sample = remove
        # 生产 slime Sample 有 metadata dict（F2-1a 身份注入的落点）——
        # fixture 同形，否则 FA 入口按 P1-4 fail-closed 拒绝
        self.metadata: dict = {}

    def __repr__(self) -> str:  # pragma: no cover - 调试便利
        return f"FakeSample({self.name}, remove={self.remove_sample})"


def _group_source_from(groups: list[list[FakeSample]]):
    backlog = list(groups)

    def source():
        return backlog.pop(0) if backlog else None

    return source


async def test_service_collects_full_groups_in_order():
    """基线：两组各 2 成员全部成功 → 返回 2 个平铺组，无弃置。"""

    groups = [
        [FakeSample("g1_m0"), FakeSample("g1_m1")],
        [FakeSample("g2_m0"), FakeSample("g2_m1")],
    ]

    async def execute(member: FakeSample):
        return [FakeSample(f"{member.name}_leaf")]

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=2,
        rollout_batch_size=2,
        concurrency=4,
        drain_timeout_seconds=1.0,
    )
    batches = await service.collect_batch()
    assert len(batches) == 2
    assert all(len(group) == 2 for group in batches)  # 每组 2 个成员的叶链平铺
    assert service.failure_records == []


async def test_service_drops_group_on_member_failure_and_keeps_collecting():
    """成员失败（异常）→ 整组显式弃置记账，worker 持续供新组补足批次
    （首版不补采语义：弃的是组，训练批用新组填）。"""

    groups = [
        [FakeSample("bad_m0"), FakeSample("bad_m1")],
        [FakeSample("ok1_m0"), FakeSample("ok1_m1")],
        [FakeSample("ok2_m0"), FakeSample("ok2_m1")],
    ]

    async def execute(member: FakeSample):
        if member.name.startswith("bad_m0"):
            raise RuntimeError("sandbox died")
        return [FakeSample(f"{member.name}_leaf")]

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=2,
        rollout_batch_size=2,
        concurrency=2,
        drain_timeout_seconds=1.0,
    )
    batches = await service.collect_batch()
    assert len(batches) == 2  # 坏组被跳过，两个好组成批
    assert len(service.failure_records) == 1
    # P1-4：失败记录带 paid（worker 对每次 dispatch 铸造，含失败的这次）
    _grp, _exec, _paid, _err = service.failure_records[0]
    assert _paid and _paid.startswith(_exec + "#p")  # 非 None 且属该 execution
    assert _err.startswith("RuntimeError")


async def test_service_drops_group_on_abort_shaped_delivery():
    """orchestrator 把失败收口成 abort 形状（remove_sample=True）而非抛异常
    ——interim 聚合器同样按整组弃置处理。"""

    groups = [
        [FakeSample("g1_m0"), FakeSample("g1_m1")],
        [FakeSample("g2_m0"), FakeSample("g2_m1")],
    ]

    async def execute(member: FakeSample):
        if member.name == "g1_m1":
            return [FakeSample(f"{member.name}_abort", remove=True)]  # abort 形状
        return [FakeSample(f"{member.name}_leaf")]

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=2,
        rollout_batch_size=1,
        concurrency=2,
        drain_timeout_seconds=1.0,
    )
    batches = await service.collect_batch()
    assert len(batches) == 1
    assert all("g2" in leaf.name for leaf in batches[0])  # g1 整组弃置


async def test_service_source_exhaustion_raises_instead_of_spinning():
    """任务源枯竭且批次未满 → FaEntryError（绝不空转等一个永远不来的组）。"""

    groups = [[FakeSample("only_m0")]]

    async def execute(member: FakeSample):
        return [FakeSample(f"{member.name}_leaf")]

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=1,
        rollout_batch_size=3,  # 永远收不满
        concurrency=2,
        drain_timeout_seconds=0.2,
        starvation_timeout_seconds=0.1,
    )
    import asyncio

    with pytest.raises(FaEntryError, match="batch_starved"):
        await asyncio.wait_for(service.collect_batch(), timeout=5)


async def test_entry_eval_fails_fast_scenario_21():
    """05 计划验收场景 21：eval 进入 FA 路径 → 显式拒绝，指向标准路径。"""

    with pytest.raises(FaEntryError, match="eval_not_supported_in_fa_path"):
        await generate_rollout_async(SimpleNamespace(), 0, data_buffer=None, evaluation=True)


async def test_entry_requires_orchestrator_and_sampling_params():
    """配置缺失 fail-fast（_build_service 直测）+ 入口会先尝试 glue 引导。"""

    from fa_bringup import rollout_entry

    class FakeBuffer:
        def get_samples(self, n):
            return []

    with pytest.raises(FaEntryError, match="orchestrator_not_attached"):
        rollout_entry._build_service(SimpleNamespace(), FakeBuffer())
    args = SimpleNamespace(rh2_orchestrator=object())
    with pytest.raises(FaEntryError, match="sampling_params_not_attached"):
        rollout_entry._build_service(args, FakeBuffer())

    # 入口层：缺挂载 → 先走 glue 引导（打桩验证确实被调用）
    calls: list[str] = []

    async def fake_bootstrap(a, b):
        calls.append("bootstrap")
        raise FaEntryError("glue_bootstrap_unavailable", "stub")

    original = rollout_entry._bootstrap_via_glue
    rollout_entry._bootstrap_via_glue = fake_bootstrap
    try:
        with pytest.raises(FaEntryError, match="glue_bootstrap_unavailable"):
            await generate_rollout_async(SimpleNamespace(), 0, FakeBuffer())
    finally:
        rollout_entry._bootstrap_via_glue = original
    assert calls == ["bootstrap"]


def test_sync_entry_returns_samples_not_coroutine():
    """codex 轮次 7 P0-1：注册路径必须是同步函数——返回值是样本列表，
    不是 coroutine（slime call_rollout_fn 不 await）。"""

    import fa_bringup.rollout_entry as entry

    class FakeService:
        async def collect_batch(self):
            return [["sample"]]

    original = entry._SERVICE
    entry._SERVICE = FakeService()
    try:
        result = entry.generate_rollout(SimpleNamespace(), 0, data_buffer=None)
    finally:
        entry._SERVICE = original
    assert result == [["sample"]]  # 已解包，不是 coroutine


def test_sync_entry_against_real_slime_call_rollout_fn():
    """真 slime 契约测试：用 slime 自己的 call_rollout_fn 调我们的同步入口，
    产物必须是 RolloutFnTrainOutput 且 samples 已解包（codex 探针的回归）。"""

    slime_base = pytest.importorskip(
        "slime.rollout.base_types", reason="需要 reference/slime + torch dev 依赖"
    )
    import fa_bringup.rollout_entry as entry

    class FakeService:
        async def collect_batch(self):
            return [["s1"], ["s2"]]

    original = entry._SERVICE
    entry._SERVICE = FakeService()
    try:
        output = slime_base.call_rollout_fn(
            entry.generate_rollout, SimpleNamespace(), 0, None, evaluation=False
        )
    finally:
        entry._SERVICE = original
    assert isinstance(output, slime_base.RolloutFnTrainOutput)
    import inspect

    assert not inspect.iscoroutine(output.samples)
    assert output.samples == [["s1"], ["s2"]]


async def test_persistent_service_no_prefetch_loss():
    """codex 轮次 7 P0-3 探针回归：batch_size=1、concurrency=8、5 个组——
    第一批返回 1 组，其余预取结果**不丢**，后续批次全部取回。"""

    groups = [[FakeSample(f"g{i}_m0")] for i in range(5)]

    async def execute(member: FakeSample):
        return [FakeSample(f"{member.name}_leaf")]

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=1,
        rollout_batch_size=1,
        concurrency=8,
        drain_timeout_seconds=1.0,
        starvation_timeout_seconds=5.0,
    )
    collected: list[list] = []
    for _ in range(5):
        batch = await service.collect_batch()
        collected.extend(batch)
    await service.shutdown()
    names = sorted(leaf.name for group in collected for leaf in group)
    assert names == sorted(f"g{i}_m0_leaf" for i in range(5))  # 零丢失
    assert service.failure_records == []


async def test_collector_drops_do_not_leak_buckets():
    """codex 轮次 7 一般项：失败组不滞留 _buckets（1000 组探针的回归）。"""

    from fa_bringup.rollout_entry import _InterimGroupCollector
    from repoharness2.adapters.slime.async_worker import ExecutionTaskSpec

    collector = _InterimGroupCollector(2)
    for i in range(100):
        spec = ExecutionTaskSpec(
            rollout_execution_id=f"g{i}_m0", prompt_group_id=f"g{i}", member_slot=0
        )
        collector.add_failure(spec, "boom")
    assert collector.open_group_count == 0  # 弃置即删桶
    assert len(collector.dropped_groups) == 100
    # 迟到成员只计数，不复活组
    late = ExecutionTaskSpec(
        rollout_execution_id="g0_m1", prompt_group_id="g0", member_slot=1
    )
    assert collector.add_delivery(late, [FakeSample("late")]) is None
    assert collector.late_deliveries_ignored == 1


def test_parse_bool_env_flag_strict():
    """codex 轮次 6：正式防线开关只认 '0'/'1'——拼写错误必须炸，不许静默关防线。"""

    from repoharness2.adapters.slime.generate import SlimeBindingError

    assert parse_bool_env_flag("X", None) is False
    assert parse_bool_env_flag("X", None, default=True) is True
    assert parse_bool_env_flag("X", "") is False
    assert parse_bool_env_flag("X", "1") is True
    assert parse_bool_env_flag("X", "0") is False
    for bad in ("true", "True", "yes", "2", " 1"):
        with pytest.raises(SlimeBindingError, match="invalid_bool_env_flag"):
            parse_bool_env_flag("RH2_REQUIRE_REAL_WEIGHT_VERSIONS", bad)


async def test_worker_crash_not_silently_restarted():
    """codex 轮次 8 P0-5：worker 以 WorkerHalted 崩溃后，下一批不得静默重启
    ——必须传播原异常（sink/任务源故障后训练不得继续）。"""

    from repoharness2.adapters.slime.async_worker import WorkerHalted

    groups = [[FakeSample("g1_m0")], [FakeSample("g2_m0")]]
    call = {"n": 0}

    async def execute(member: FakeSample):
        call["n"] += 1
        return [FakeSample(f"{member.name}_leaf")]

    def bad_sink(spec, exc):
        raise ValueError("sink broken")

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=1,
        rollout_batch_size=1,
        concurrency=1,
        drain_timeout_seconds=0.5,
    )
    # 注入坏 sink：手动构造 worker 让第一批就 halt
    import asyncio as _a

    from repoharness2.adapters.slime.async_worker import (
        BoundedDeliveryQueue,
        ContinuousExecutionWorker,
    )

    async def crashing_execute(spec):
        raise RuntimeError("boom")

    service._queue = BoundedDeliveryQueue(maxsize=8)
    from fa_bringup.rollout_entry import _InterimGroupCollector

    service._collector = _InterimGroupCollector(1)
    service._worker = ContinuousExecutionWorker(
        task_source=service._task_source,
        execute_fn=crashing_execute,
        delivery_queue=service._queue,
        failure_sink=bad_sink,
        concurrency=1,
        drain_timeout_seconds=0.5,
    )
    service._stop = _a.Event()
    service._worker_task = _a.create_task(service._worker.run(service._stop))
    # 等 worker 崩溃
    with pytest.raises(WorkerHalted):
        await _a.wait_for(service._worker_task, timeout=5)
    # 下一批调用必须传播故障，不静默重启
    with pytest.raises(WorkerHalted):
        await service.collect_batch()


async def test_execute_stamps_identity_into_member_metadata():
    """F2-1a：service 在执行前把 dispatch 铸造的身份戳进 member.metadata
    （rh2_* 键）——orchestrator 由此读入 audit 并登记 sid→paid。replay
    同组第二次执行会得到不同 paid（worker dispatch 铸造语义）。"""

    groups = [[FakeSample("g1_m0"), FakeSample("g1_m1")]]
    seen_meta: list[dict] = []

    async def execute(member):
        seen_meta.append(dict(member.metadata))
        return [FakeSample(f"{member.name}_leaf")]

    service = FaRolloutService(
        group_source=_group_source_from(groups),
        execute_member=execute,
        group_size=2,
        rollout_batch_size=1,
        concurrency=2,
        drain_timeout_seconds=1.0,
    )
    await service.collect_batch()
    await service.shutdown()
    assert len(seen_meta) == 2
    for meta in seen_meta:
        assert meta["rh2_prompt_group_id"]  # 组身份在场
        assert meta["rh2_physical_attempt_id"].startswith(
            meta["rh2_rollout_execution_id"] + "#p"
        )
        assert meta["rh2_physical_attempt_seq"] == 1  # 首次 dispatch
    # 两个成员各自独立的 execution 身份
    assert seen_meta[0]["rh2_rollout_execution_id"] != seen_meta[1]["rh2_rollout_execution_id"]
