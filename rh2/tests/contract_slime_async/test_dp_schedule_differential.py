"""FA-3 差分验证：预检器 vs slime 真 `build_dp_schedule`（离线验收 2）。

codex 轮次 2 #4 的要求：不仅"模拟"约束，同一输入必须同时喂 RepoHarness
预测器和 slime 的真实纯 Python 函数，**成功/失败类别、step 数、每 rank
microbatch 数三项一致**。本文件是 `batch_admission.predict_batch_schedule`
镜像忠实性的权威——预检器改动必须先过这里。

真函数导入：`slime/utils/dp_schedule.py` 模块自述纯 Python、CPU-only 可
测（不需要 torch）；reference/slime 缺席时 skip（同表面契约测试口径）。

另含 dynamic_filter 真调用测试（离线验收 5 的 dynamic_filter 半区，需要
torch dev 依赖）：P3 崩溃形状（嵌套 list[list[Sample]]）复现 + 我方平铺
交付形状通过。`_key` 真调用因 import 链穿 sglang_rollout（需 sglang/ray）
留 FA-1 环境，源码 pin 见 test_fully_async_surface.py。
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SLIME_ROOT = Path(__file__).resolve().parents[3] / "reference" / "slime"

pytestmark = pytest.mark.skipif(
    not _SLIME_ROOT.exists(), reason="reference/slime 不在本地，差分无被测物"
)

if _SLIME_ROOT.exists():  # pragma: no branch
    sys.path.insert(0, str(_SLIME_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))  # fixtures 包

from fixtures.p3_events import (  # noqa: E402  (依赖 tests/adapters/fixtures 路径)
    J4_FORMAL,
    J5_GBS16,
    as_schedule_inputs,
    kept_rollout_structure,
    load_events,
)

from repoharness2.adapters.slime.batch_admission import (  # noqa: E402
    PackingArgs,
    TrainParallelConfig,
    predict_batch_schedule,
)


def _real_schedule(lengths, rollout_indices, *, gbs, parallel, packing):
    """调用 slime 真函数；返回 ("ok", num_microbatches) 或 ("fail", 断言文本)。"""

    from slime.utils.dp_schedule import build_dp_schedule

    args = SimpleNamespace(
        use_dynamic_batch_size=packing.use_dynamic_batch_size,
        max_tokens_per_gpu=packing.max_tokens_per_gpu,
        micro_batch_size=packing.micro_batch_size,
        balance_by_flops=packing.balance_by_flops,
        balance_data=packing.balance_data,
    )
    config = {
        "dp_size": parallel.dp_size,
        "cp_size": parallel.cp_size,
        "vpp_size": parallel.vpp_size,
        "microbatch_group_size_per_vp_stage": parallel.microbatch_group_size_per_vp_stage,
    }
    try:
        _, _, num_microbatches, _ = build_dp_schedule(
            args, config, lengths, global_batch_size=gbs, rollout_indices=rollout_indices
        )
    except AssertionError as exc:
        return "fail", str(exc)
    return "ok", num_microbatches


def _differential(lengths, rollout_indices, *, gbs, parallel, packing):
    prediction = predict_batch_schedule(
        lengths, rollout_indices, global_batch_size=gbs, parallel=parallel, packing=packing
    )
    real_kind, real_payload = _real_schedule(
        lengths, rollout_indices, gbs=gbs, parallel=parallel, packing=packing
    )
    if prediction.admitted:
        assert real_kind == "ok", (
            f"预检判可、真函数判负：{real_payload}\n prediction={prediction}"
        )
        assert list(prediction.num_microbatches_per_rank) == list(real_payload), (
            f"每 rank mbs 数不一致：predict={prediction.num_microbatches_per_rank} "
            f"real={real_payload}"
        )
        assert prediction.num_steps == len(real_payload)
    else:
        assert real_kind == "fail", (
            f"预检判负（{prediction.verdict}）、真函数判可：{real_payload}"
        )
    return prediction, (real_kind, real_payload)


P3_PARALLEL = TrainParallelConfig(dp_size=2, cp_size=1, vpp_size=1)
P3_PACKING = PackingArgs(use_dynamic_batch_size=True, max_tokens_per_gpu=32768)


def test_differential_on_j4_formal_a_class():
    """A 类夹具（真实结构）：两侧同判负，真函数报错文本含同一对数字。"""

    structure = kept_rollout_structure(load_events(J4_FORMAL))
    lengths, rollout_indices = as_schedule_inputs(structure, sample_length=1500)
    prediction, (kind, text) = _differential(
        lengths, rollout_indices, gbs=32, parallel=P3_PARALLEL, packing=P3_PACKING
    )
    assert prediction.verdict == "insufficient_rollout_count"
    assert kind == "fail" and "num_rollouts (19) < global_batch_size (32)" in text


def test_differential_on_j5_gbs16_b_class():
    """B 类夹具（真实结构 + 校准长度）：真函数报错含真实数字 23/24。"""

    structure = kept_rollout_structure(load_events(J5_GBS16))
    lengths, rollout_indices = as_schedule_inputs(structure, sample_length=20000)
    prediction, (kind, text) = _differential(
        lengths, rollout_indices, gbs=16, parallel=P3_PARALLEL, packing=P3_PACKING
    )
    assert prediction.verdict == "microbatch_alignment_failed"
    assert kind == "fail" and "could only produce 23 mbs" in text and "need 24" in text


def test_differential_on_j5_gbs20_admits_with_equal_mbs():
    structure = kept_rollout_structure(load_events(J5_GBS16))
    lengths, rollout_indices = as_schedule_inputs(structure, sample_length=20000)
    prediction, _ = _differential(
        lengths, rollout_indices, gbs=20, parallel=P3_PARALLEL, packing=P3_PACKING
    )
    assert prediction.admitted


def test_differential_randomized_sweep():
    """随机扫（seed 固定，200 例）：动态/静态、多 dp/vpp、含 fan-out 重复
    rollout id——三项一致性全程成立。"""

    rng = random.Random(20260712)
    checked_ok = checked_fail = 0
    for _ in range(200):
        num_rollouts = rng.randint(1, 24)
        lengths: list[int] = []
        rollout_indices: list[int] = []
        for rid in range(num_rollouts):
            for _ in range(rng.randint(1, 3)):  # fan-out 1..3
                lengths.append(rng.randint(200, 30000))
                rollout_indices.append(rid)
        parallel = TrainParallelConfig(
            dp_size=rng.choice([1, 2, 4]),
            cp_size=rng.choice([1, 2]),
            vpp_size=rng.choice([1, 2]),
            microbatch_group_size_per_vp_stage=rng.choice([1, 2]),
        )
        if rng.random() < 0.7:
            packing = PackingArgs(
                use_dynamic_batch_size=True,
                max_tokens_per_gpu=rng.choice([8192, 16384, 32768]),
            )
        else:
            packing = PackingArgs(
                use_dynamic_batch_size=False, micro_batch_size=rng.choice([1, 2, 4])
            )
        gbs = rng.randint(1, 32)
        prediction, _ = _differential(
            lengths, rollout_indices, gbs=gbs, parallel=parallel, packing=packing
        )
        if prediction.admitted:
            checked_ok += 1
        else:
            checked_fail += 1
    # 扫描必须两类结果都覆盖到，否则测试面是偏的
    assert checked_ok >= 20 and checked_fail >= 20, (checked_ok, checked_fail)


# ------------------------------------------------ dynamic_filter 真调用半区

torch = pytest.importorskip("torch", reason="dynamic_filter 真调用需要 torch dev 依赖")


def _make_sample(reward: float):
    from slime.utils.types import Sample

    sample = Sample(prompt="p", tokens=[1, 2], response_length=1)
    sample.reward = reward
    return sample


def test_dynamic_filter_crashes_on_nested_fanout_shape_p3_pin():
    """P3 J4 崩溃复现（真函数）：嵌套 list[list[Sample]] 让
    check_reward_nonzero_std 撞 'list' object has no attribute
    'get_reward_value'——这是 FA-1 三视图交付边界要消灭的形状。"""

    from slime.rollout.filter_hub.dynamic_sampling_filters import check_reward_nonzero_std

    nested = [[_make_sample(1.0), _make_sample(0.0)]]  # 组外层未剥离
    args = SimpleNamespace(reward_key=None)
    with pytest.raises(AttributeError, match="get_reward_value"):
        check_reward_nonzero_std(args, nested)


def test_dynamic_filter_accepts_flat_delivery_shape():
    """我方平铺交付形状（组内展开为 list[Sample]）：真函数正常判定。"""

    from slime.rollout.filter_hub.dynamic_sampling_filters import check_reward_nonzero_std

    args = SimpleNamespace(reward_key=None)
    mixed = [_make_sample(1.0), _make_sample(0.0)]
    uniform = [_make_sample(1.0), _make_sample(1.0)]
    out_mixed = check_reward_nonzero_std(args, mixed)
    out_uniform = check_reward_nonzero_std(args, uniform)
    # keep 是 torch.BoolTensor（真函数实现细节），显式收敛为 Python bool
    assert bool(out_mixed.keep) is True  # 非零方差组保留
    assert bool(out_uniform.keep) is False  # 零方差组丢弃
