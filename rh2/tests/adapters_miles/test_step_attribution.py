"""租前完整审查 PR-P0-7 修复验收：sample→optimizer step 归因用真实边界。

审查反例（原文数值）：rollout_ids=[0,0,0,1,1,1,2,3]、global_batch_size=2
（rollout 计数口径）、DP=2 时，rollout 侧调度给 rank0 两个 step 的本地行数是
3 / 1；旧 emitter 用 ``len(local) // num_steps`` 等分成 2 / 2，把 sample 4 从
真实 step0 静默记到 step1——总 ID 各出现一次，duplicate 检查发现不了。

修复 = ``miles.utils.step_attribution.step_local_sample_positions`` 按
DataIterator 的真实 micro-batch 调度（micro_batch_indices + 每 step
num_microbatches，或固定 micro_batch_size 切片）求本 step 的本地样本位置。
本文件用 **真实 build_dp_schedule 输出** 对拍（不是手造调度），并逐 microbatch
复演 DataIterator 的消费次序作独立 oracle。
"""

from __future__ import annotations

from argparse import Namespace

import pytest

pytestmark = pytest.mark.integration_base


def _audit_schedule():
    """审查反例的真实调度：dp_schedule.build_dp_schedule 原样输出。"""
    from miles.utils.dp_schedule import build_dp_schedule

    args = Namespace(
        use_dynamic_batch_size=True,
        max_tokens_per_gpu=200,
        balance_data=False,
        micro_batch_size=None,
    )
    config = {"dp_size": 2, "cp_size": 1, "vpp_size": None, "microbatch_group_size_per_vp_stage": 1}
    rollout_indices = [0, 0, 0, 1, 1, 1, 2, 3]
    total_lengths = [100] * len(rollout_indices)
    return build_dp_schedule(
        args, config, total_lengths, global_batch_size=2, rollout_indices=rollout_indices
    )


def _iterator_oracle(micro_batch_indices, num_microbatches):
    """独立 oracle：逐 microbatch 复演 DataIterator.get_next 的消费次序。"""
    per_step = []
    offset = 0
    for nmb in num_microbatches:
        step_positions = []
        for _ in range(nmb):
            step_positions.extend(micro_batch_indices[offset])
            offset += 1
        per_step.append(sorted(step_positions))
    return per_step


def test_audit_counterexample_variable_fanout_3_1(world):
    """审查 3/1 反例：真实调度下 rank 本地两 step 是 3/1 行；helper 必须给出
    3/1，而旧等分推断给 2/2（显式断言其错误归因）。"""
    from miles.utils.step_attribution import step_local_sample_positions

    partitions, micro_batch_indices, num_microbatches, num_rollouts = _audit_schedule()
    assert num_rollouts == [2, 2] and len(num_microbatches) == 2

    for rank in (0, 1):
        local_n = len(partitions[rank])
        oracle = _iterator_oracle(micro_batch_indices[rank], num_microbatches)
        got = [
            sorted(
                step_local_sample_positions(
                    step_id=sid,
                    num_microbatches=num_microbatches,
                    micro_batch_indices=micro_batch_indices[rank],
                    micro_batch_size=None,
                    num_local_samples=local_n,
                )
            )
            for sid in range(2)
        ]
        assert got == oracle, f"rank{rank}: helper 与 DataIterator 消费次序不一致"
        sizes = [len(x) for x in got]
        assert sizes == [3, 1], f"rank{rank}: 真实 step 行数应为 3/1，got {sizes}"
        # 旧实现的等分推断：4 // 2 = 2/2——把一个 step0 样本错记到 step1。
        equal_split = [local_n // 2, local_n // 2]
        assert sizes != equal_split, "等分推断在 variable fan-out 下就是审查反例本身"
        # 两 step 位置互不相交且并集覆盖整个本地 shard（multiset 检查抓不到的
        # 串账在这里以位置级验证关死）。
        assert set(got[0]).isdisjoint(got[1])
        assert sorted(set(got[0]) | set(got[1])) == list(range(local_n))


def test_global_sample_attribution_matches_partitions(world):
    """把本地位置映射回全局 sample index：每个 step 消费的全局样本 = 该 step
    picked rollouts 的全部样本（rollout 完整性：同 rollout 的样本必须同 step）。"""
    from miles.utils.step_attribution import step_local_sample_positions

    partitions, micro_batch_indices, num_microbatches, _ = _audit_schedule()
    rollout_indices = [0, 0, 0, 1, 1, 1, 2, 3]
    expected_by_step = [
        {i for i, rid in enumerate(rollout_indices) if rid in (0, 1)},
        {i for i, rid in enumerate(rollout_indices) if rid in (2, 3)},
    ]
    for sid, expected in enumerate(expected_by_step):
        got = set()
        for rank in (0, 1):
            positions = step_local_sample_positions(
                step_id=sid,
                num_microbatches=num_microbatches,
                micro_batch_indices=micro_batch_indices[rank],
                micro_batch_size=None,
                num_local_samples=len(partitions[rank]),
            )
            got.update(partitions[rank][p] for p in positions)
        assert got == expected, f"step{sid} 的全局样本归因错误：{sorted(got)} != {sorted(expected)}"


def test_fixed_micro_batch_size_path(world):
    """固定 micro_batch_size 路径：step 边界 = 前序 step 的 size*nmb 累积。"""
    from miles.utils.step_attribution import step_local_sample_positions

    kwargs = dict(micro_batch_indices=None, micro_batch_size=2, num_local_samples=10)
    assert step_local_sample_positions(step_id=0, num_microbatches=[2, 3], **kwargs) == [0, 1, 2, 3]
    assert step_local_sample_positions(step_id=1, num_microbatches=[2, 3], **kwargs) == [4, 5, 6, 7, 8, 9]


def test_inconsistency_raises_instead_of_guessing(world):
    """任何调度不一致必须 ValueError（emitter 记 error 事实），不得回退猜测。"""
    from miles.utils.step_attribution import step_local_sample_positions

    with pytest.raises(ValueError, match="out of range"):
        step_local_sample_positions(
            step_id=2, num_microbatches=[1, 1], micro_batch_indices=[[0], [1]],
            micro_batch_size=None, num_local_samples=2,
        )
    with pytest.raises(ValueError, match="micro-batches"):
        step_local_sample_positions(
            step_id=1, num_microbatches=[1, 2], micro_batch_indices=[[0], [1]],
            micro_batch_size=None, num_local_samples=2,
        )
    with pytest.raises(ValueError, match="outside local shard"):
        step_local_sample_positions(
            step_id=0, num_microbatches=[1], micro_batch_indices=[[0, 5]],
            micro_batch_size=None, num_local_samples=2,
        )
    with pytest.raises(ValueError, match="neither"):
        step_local_sample_positions(
            step_id=0, num_microbatches=[1], micro_batch_indices=None,
            micro_batch_size=None, num_local_samples=2,
        )
