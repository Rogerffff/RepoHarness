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
    assert service.failure_records[0][2].startswith("RuntimeError")


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
    """配置缺失 fail-fast：编排本体/采样配方没挂上不许起跑。"""

    class FakeBuffer:
        def get_samples(self, n):
            return []

    with pytest.raises(FaEntryError, match="orchestrator_not_attached"):
        await generate_rollout_async(SimpleNamespace(), 0, FakeBuffer())
    args = SimpleNamespace(rh2_orchestrator=object())
    with pytest.raises(FaEntryError, match="sampling_params_not_attached"):
        await generate_rollout_async(args, 0, FakeBuffer())


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
