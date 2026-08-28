"""F2 全局零信号语义——seam 之外的三块验收（规格 = tmp/F2修复建议.md 与
codex 零信号建议 §5-§7;seam 级用例 A~F 与 momentum 主验收在
test_train_seam_metamorphic.py 的 F2 区段）：

1. **规格 §7 用例 B 的 filter 半场**（双 lane,不标 integration_base）：
   reward 全相等的组在 miles stock `DefaultDataBuffer.put` 处被
   `check_reward_nonzero_std` 丢弃,不进训练 buffer;方差非零的组正常入队。
   丢弃组不走 unused_handler 回收（无梯度信号,补采由 fully-async 持续
   producer 自然完成——生产接线 = launch 参数
   `--dynamic-sampling-filter-path
   miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std`,
   见 rh2/experiments/miles_gpu_spike/launch_args.md）。

2. **TrainRolloutReport 单元语义**（integration_base）：miles train() 的
   富返回值（rh2-integration-v2 commit 620aa6924）——str 子类,值 =
   rollout 级 outcome,既有 `== TrainStepOutcome.X` 比较不破;携带
   applied_optimizer_steps/skipped_zero_signal_steps/weights_dirty;
   pickle（Ray 传输机制）后属性完整。weights_dirty 只在"全部 step 都是
   zero-signal skip"时为 False（可证明权重未变）,其余一律 True（保守,
   维持历史 publish 行为）。

3. **源码事实锚定**（integration_base,与运行时 import 同一 checkout）：
   miles model.py 的零信号判定位于"归约完成后、optimizer.step 之前";
   train_async.py 的 publish 门控存在（weights_dirty OR 累计 + 全 skip
   不调 update_weights,版本不增,commit 51e3cd969）。miles 侧若重构掉
   这些接线,这里当场红。
"""

from __future__ import annotations

import pickle

import pytest

STOCK_NONZERO_STD_FILTER = "miles.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std"


# ---------------------------------------------------------------------------
# 1. 规格 §7 用例 B（filter 半场）：stock buffer 丢弃零方差 reward 组
# ---------------------------------------------------------------------------


async def test_case_b_equal_reward_group_dropped_by_stock_dynamic_filter(world):
    """reward 全相等 → 零方差 → stock filter 丢弃,不进训练 buffer;方差非零
    正常入队并可取。丢弃不回收 prompt（与 miles 语义一致:该组无梯度信号,
    重训同一陈旧组没有意义,持续 producer 会继续生产新组补足 batch）。"""
    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args(dynamic_sampling_filter_path=STOCK_NONZERO_STD_FILTER)
    recycled: list = []
    buf = DefaultDataBuffer(
        DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append)
    )

    # drop 路径：全同 reward（GRPO group advantage 必然全 0）
    pg_drop = world.mk_gov_prompt_group("pz")
    await buf.put(world.mk_entry(pg_drop, world.mk_gov_finished_group(pg_drop, rewards=(0.5, 0.5))))
    assert buf._buffer == []  # noqa: SLF001 —— 不进训练 buffer
    assert recycled == []  # 不回收（drop,非 retry）
    assert buf.get_metrics()["rollout/dynamic_filter/drop_zero_std_0.5"] == 1

    # keep 路径：reward 0.0/1.0 方差非零,正常入队、正常取出
    pg_keep = world.mk_gov_prompt_group("pk")
    entry = world.mk_entry(pg_keep, world.mk_gov_finished_group(pg_keep))
    await buf.put(entry)
    assert len(buf._buffer) == 1  # noqa: SLF001
    assert await buf.get(current_version=7) is entry


# ---------------------------------------------------------------------------
# 2. TrainRolloutReport 单元语义（miles 富返回值,str 兼容 + pickle）
# ---------------------------------------------------------------------------


@pytest.mark.integration_base
def test_train_rollout_report_outcome_value_and_weights_dirty(world):
    from miles.backends.megatron_utils.ft.types import TrainRolloutReport, TrainStepOutcome

    N, S, D = (
        TrainStepOutcome.NORMAL,
        TrainStepOutcome.SKIPPED_ZERO_SIGNAL,
        TrainStepOutcome.DISCARDED_SHOULD_RETRY,
    )

    # 混合（一步 applied + 一步 skip）：rollout 级必须是 NORMAL 且 dirty——
    # 这正是"不能只看最后一步 outcome"的规格条款（64 samples/GBS 32 两步）
    mixed = TrainRolloutReport.from_step_outcomes([N, S])
    assert mixed == TrainStepOutcome.NORMAL  # 既有 actor.py 比较语义不破
    assert mixed.applied_optimizer_steps == 1
    assert mixed.skipped_zero_signal_steps == 1
    assert mixed.weights_dirty is True

    # 全 skip：唯一 weights_dirty=False 的情形（权重可证明未变）
    all_skip = TrainRolloutReport.from_step_outcomes([S, S])
    assert all_skip == TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    assert all_skip != TrainStepOutcome.NORMAL
    assert all_skip.applied_optimizer_steps == 0
    assert all_skip.skipped_zero_signal_steps == 2
    assert all_skip.weights_dirty is False

    # 全 normal / discarded / 空列表：一律保守 dirty=True
    assert TrainRolloutReport.from_step_outcomes([N]).weights_dirty is True
    discarded = TrainRolloutReport.from_step_outcomes([D])
    assert discarded == TrainStepOutcome.DISCARDED_SHOULD_RETRY
    assert discarded.weights_dirty is True
    assert TrainRolloutReport.from_step_outcomes([]).weights_dirty is True


@pytest.mark.integration_base
def test_train_rollout_report_survives_pickle_with_attributes(world):
    """Ray 把 train() 返回值从 trainer actor 传回 driver 走 pickle 族序列化;
    str 子类的值与属性都必须原样到达（driver 端 _any_weights_dirty 读
    weights_dirty 属性做 publish 门控）。"""
    from miles.backends.megatron_utils.ft.types import TrainRolloutReport, TrainStepOutcome

    report = TrainRolloutReport.from_step_outcomes(
        [TrainStepOutcome.SKIPPED_ZERO_SIGNAL, TrainStepOutcome.SKIPPED_ZERO_SIGNAL]
    )
    for proto in (2, pickle.HIGHEST_PROTOCOL):
        restored = pickle.loads(pickle.dumps(report, protocol=proto))
        assert restored == TrainStepOutcome.SKIPPED_ZERO_SIGNAL
        assert restored.weights_dirty is False
        assert restored.applied_optimizer_steps == 0
        assert restored.skipped_zero_signal_steps == 2


@pytest.mark.integration_base
def test_driver_gate_helper_semantics(world):
    """driver 侧 _any_weights_dirty 的保守面：只有全 rank 显式
    weights_dirty=False 才判"未脏";缺属性（debug 路径旧返回值）与空结果
    （critic-only 轮）都算脏——历史 publish 行为仅在可证明全 skip 时改变。

    train_async.py 是启动脚本,模块级 import 拉 ray/placement_group（CPU 下
    stub 不全,整模块 exec 不可行）——用 ast 只抽取生产函数定义本体执行,
    函数不存在或被改名时 StopIteration 当场红（仍是"测生产源码"而非复刻）。"""
    import ast

    from miles.backends.megatron_utils.ft.types import TrainRolloutReport, TrainStepOutcome

    src = (world.miles_root / "train_async.py").read_text()
    tree = ast.parse(src)
    fn_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_any_weights_dirty"
    )
    namespace: dict = {}
    exec(  # noqa: S102 —— 编译的是仓内生产源码的单个函数定义
        compile(ast.Module(body=[fn_node], type_ignores=[]), str(world.miles_root / "train_async.py"), "exec"),
        namespace,
    )
    any_weights_dirty = namespace["_any_weights_dirty"]

    S = TrainStepOutcome.SKIPPED_ZERO_SIGNAL
    clean = TrainRolloutReport.from_step_outcomes([S])
    dirty = TrainRolloutReport.from_step_outcomes([TrainStepOutcome.NORMAL])

    assert any_weights_dirty([clean, clean]) is False  # 全 rank 全 skip:不 publish
    assert any_weights_dirty([clean, dirty]) is True  # 任一 rank 脏:publish
    assert any_weights_dirty([TrainStepOutcome.NORMAL]) is True  # 旧式裸 outcome:保守
    assert any_weights_dirty(None) is True  # critic-only 轮:保守
    assert any_weights_dirty([]) is True


# ---------------------------------------------------------------------------
# 3. 源码事实锚定（与运行时 import 同一 checkout;重构即红）
# ---------------------------------------------------------------------------


@pytest.mark.integration_base
def test_model_zero_signal_seam_position_source_anchor(world):
    """train_one_step 的零信号判定必须位于"全部归约完成之后、optimizer.step
    之前"（规格四处接线第 3 处）。文本位置锚定：scan 调用出现在
    forward_backward 归约与 indep-dp 归约之后、optimizer.step() 之前;同时
    锚定 found-inf 分支的 SKIPPED 守卫（零梯度有限时 grad_norm==0 会把
    valid_step 翻回 True,少了守卫 skip 会被静默撤销）。"""
    src = (world.miles_root / "miles" / "backends" / "megatron_utils" / "model.py").read_text()

    # 锚点更新（租前审查 P1-2,T2 补锚）：scan 与 allreduce 拆成两行以便给
    # scan 单独计时（zero_signal_scan_seconds）,语义位置不变——scan 仍在全部
    # 归约之后、optimizer.step 之前,且 allreduce 紧随 scan 消费其结果。
    scan_pos = src.index("local_any_nonzero, local_all_finite = _scan_reduced_grads(model)")
    sync_pos = src.index("_sync_grad_signal_flags(local_any_nonzero, local_all_finite)")
    assert scan_pos < sync_pos
    assert src.index("losses_reduced = forward_backward_func(") < scan_pos
    assert src.index("allreduce_grads_and_losses_across_replicas(") < scan_pos
    assert sync_pos < src.index("update_successful, grad_norm, num_zeros_in_grad = optimizer.step()")
    # skip 后不 step/不 scheduler：valid_step=False + found-inf 分支守卫
    assert "outcome = TrainStepOutcome.SKIPPED_ZERO_SIGNAL" in src
    assert 'and outcome != TrainStepOutcome.SKIPPED_ZERO_SIGNAL' in src
    # 精确零判定,无 epsilon（防"误杀正常小梯度"的边界被静默加回来）
    assert "(grad != 0).any()" in src
    # 熔断可配 + train() 聚合返回富报告
    assert "max_consecutive_zero_signal_steps" in src
    assert "TrainRolloutReport.from_step_outcomes(step_outcomes)" in src


@pytest.mark.integration_base
def test_train_async_publish_gate_source_anchor(world):
    """train_async.py 的 publish 门控（规格四处接线第 4 处）：weights_dirty
    在 publish interval 内做 OR 累计;只有 dirty 才 sync+update_weights
    （weight_version 才会增）;publish 后复位。"""
    src = (world.miles_root / "train_async.py").read_text()

    or_pos = src.index("weights_dirty_since_publish |= _any_weights_dirty(actor_train_results)")
    gate_pos = src.index("if weights_dirty_since_publish:")
    update_pos = src.index("await actor_model.update_weights(rollout_id=rollout_id)")
    # 注意首个 "weights_dirty_since_publish = False" 是 loop 前的初始化行,
    # 复位锚定必须从 update 调用之后搜索
    reset_pos = src.index("weights_dirty_since_publish = False", update_pos)
    assert or_pos < gate_pos < update_pos < reset_pos
    # update_weights 调用必须在门控分支内（缩进深于门控行本身）
    gate_indent = len(src[: gate_pos].rsplit("\n", 1)[-1])
    update_indent = len(src[: update_pos].rsplit("\n", 1)[-1])
    assert update_indent > gate_indent
