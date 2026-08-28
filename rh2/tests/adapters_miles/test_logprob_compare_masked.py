"""租前完整审查 PR-P0-8（logprob 面）修复验收：masked_compare_entries。

旧 emitter 的两个假绿口子在此关死：

1. 长度错位被 ``min(cur, beh)`` 截断吞掉——现在 length_mismatch 是一等事实
   （judge 一票 FAIL），diff 只作诊断。
2. 均值混入 loss_mask=0 的 observation/tool token——大量零差 token 稀释真正
   训练 token 的误差。现在只统计 loss_mask==1 位。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration_base


def _entries(world, **over):
    import torch

    from miles.utils.logprob_compare import masked_compare_entries

    kwargs = dict(
        sample_indices=[7],
        log_probs=[torch.tensor([-1.0, -2.0, -3.0, -4.0])],
        behavior_log_probs=[torch.tensor([-1.0, -2.5, -3.0, -4.0])],
        loss_masks=[torch.tensor([1, 0, 1, 1])],
        weight_versions=[["3"]],
        current_version=3,
    )
    kwargs.update(over)
    return masked_compare_entries(**kwargs)


def test_mean_counts_only_loss_mask_tokens(world):
    """位 1 差 0.5 但 mask=0：均值必须为 0（只看 mask=1 的位 0/2/3）。混入
    mask=0 位的旧口径会得到 0.125 的稀释值。"""
    [e] = _entries(world)
    assert e["sample_index"] == 7
    assert e["same_version"] is True
    assert e["length_mismatch"] is False
    assert e["num_tokens"] == 3
    assert e["total_tokens"] == 4
    assert e["mean_abs_diff"] == 0.0


def test_masked_diff_detected(world):
    import torch

    [e] = _entries(world, behavior_log_probs=[torch.tensor([-1.2, -2.0, -3.0, -4.0])])
    assert e["mean_abs_diff"] == pytest.approx(0.2 / 3, abs=1e-6)


def test_length_mismatch_is_first_class_fact(world):
    """behavior 少一位：旧实现截断共同前缀、length_mismatch 丢弃；现在必须
    length_mismatch=True（diff 仍在共同前缀掩码位上给出诊断值）。"""
    import torch

    [e] = _entries(world, behavior_log_probs=[torch.tensor([-1.0, -2.0, -3.0])])
    assert e["length_mismatch"] is True
    assert e["num_tokens"] == 2  # 共同前缀内 mask=1 的位（0、2）
    assert e["mean_abs_diff"] == 0.0


def test_missing_loss_mask_is_alignment_break_not_fallback(world):
    """loss mask 缺席不得回退成全 token 均值——记 length_mismatch=True、
    num_tokens=0，judge 按对齐破坏处理。"""
    [e] = _entries(world, loss_masks=None)
    assert e["length_mismatch"] is True
    assert e["num_tokens"] == 0
    assert e["mean_abs_diff"] is None


def test_all_masked_out_yields_no_mean(world):
    import torch

    [e] = _entries(world, loss_masks=[torch.tensor([0, 0, 0, 0])])
    assert e["num_tokens"] == 0
    assert e["mean_abs_diff"] is None
    assert e["length_mismatch"] is False


def test_version_semantics(world):
    [e] = _entries(world, weight_versions=[["2", "3"]])
    assert e["same_version"] is False  # 逐 turn 版本必须全部等于 current
    [e] = _entries(world, weight_versions=None)
    assert e["same_version"] is False
