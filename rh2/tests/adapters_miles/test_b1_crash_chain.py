"""B1 崩溃链回归（spike-log R5-ext B1 / blockers §3）。

证明两件事：

(i) vendor 输出形态的 **slime** Sample 不经 canonicalize 直接进 miles
    DefaultDataBuffer，会复现 R5 §3.1 的三个症状（文档化断言——这些断言
    固定的是"错误行为确实存在"，一旦 miles 升级让症状消失，断言会失败，
    提醒重新评估 canonicalize 边界是否仍必要）：
    1. ABORTED 漏过滤（slime 枚举 != miles 枚举，abort 过滤失效，组混进 buffer）；
    2. get_metrics 因 slime Sample 缺 `oldest_weight_version` 抛 AttributeError；
    3. validate_compact_rollout_ids 因 isinstance(miles Sample) 断言炸。

(ii) 同一批数据经 canonicalize 后全部正常：ABORTED 组被过滤回收、
     get_metrics 正常、validate 通过。
"""

from __future__ import annotations

import pytest


def _mk_buffer(world, recycled):
    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DefaultDataBuffer,
    )

    return DefaultDataBuffer(
        DataBufferConstructorInput(args=world.mk_miles_args(), unused_handler_fn=recycled.append)
    )


def _slime_group_with_aborted_branch(world):
    """vendor 输出形态：execution 0 正常，execution 1 是含 ABORTED 的 fan-out 分支。"""

    return [
        [world.mk_vendor_sample(index=0)],
        [
            world.mk_vendor_sample(index=1, rollout_id=42),
            world.mk_vendor_sample(index=1, rollout_id=42, status=world.SS.Status.ABORTED),
        ],
    ]


async def test_symptom_1_and_2_aborted_leak_then_metrics_crash(world):
    """症状 1：slime ABORTED 漏过滤混进 buffer；症状 2：get_metrics 随即
    AttributeError。（未修复行为的文档化固定）"""

    from miles.rollout.fully_async_data_buffer import DataBufferInput

    recycled = []
    buf = _mk_buffer(world, recycled)
    prompt_group = [world.mk_miles_input(index=0), world.mk_miles_input(index=1)]

    await buf.put(DataBufferInput(prompt_group=prompt_group, group=_slime_group_with_aborted_branch(world)))

    # 症状 1：本应整组被拒并回收 prompt——实际漏过滤，组混进 buffer。
    assert recycled == [], "ABORTED 组被回收了？miles 行为变了，重审 canonicalize 边界"
    assert len(buf._buffer) == 1  # 私有属性：仅为文档化取证
    assert buf._metric_aborted_groups == 0

    # 症状 2：metrics 汇报访问 slime Sample 没有的 oldest_weight_version。
    with pytest.raises(AttributeError, match="oldest_weight_version"):
        buf.get_metrics()


def test_symptom_3_validate_compact_rollout_ids_asserts(world):
    """症状 3：slime Sample 不是 miles Sample，节点类型断言直接炸。"""

    from miles.ray.rollout.rollout_data_conversion import validate_compact_rollout_ids

    with pytest.raises(AssertionError, match="unexpected rollout output node type: Sample"):
        validate_compact_rollout_ids([_slime_group_with_aborted_branch(world)])


async def test_canonicalized_same_data_all_symptoms_gone(world):
    """(ii) 同数据经 canonicalize 后：abort 过滤生效、metrics 正常、validate 通过。"""

    from miles.ray.rollout.rollout_data_conversion import validate_compact_rollout_ids
    from miles.rollout.fully_async_data_buffer import DataBufferInput

    inputs = [world.mk_miles_input(index=0), world.mk_miles_input(index=1)]
    raw = _slime_group_with_aborted_branch(world)
    group = [
        world.canonicalize_group(execution, miles_input_sample=inputs[i])
        for i, execution in enumerate(raw)
    ]

    # 症状 3 消失：validate 通过（sibling 共享 rollout_id 的形状也一并核过）
    validate_compact_rollout_ids([group])

    recycled = []
    buf = _mk_buffer(world, recycled)
    await buf.put(DataBufferInput(prompt_group=inputs, group=group))

    # 症状 1 消失：含 ABORTED 分支的组整组被拒，prompt 回收
    assert recycled == [inputs]
    assert len(buf._buffer) == 0

    # 症状 2 消失：metrics 正常汇报 abort 过滤计数
    metrics = buf.get_metrics()
    assert metrics["rollout/fully_async/aborted_groups_filtered"] == 1

    # 无 ABORTED 的组正常入 buffer / 取出
    clean_inp = world.mk_miles_input(index=2)
    clean = world.canonicalize_group(
        [world.mk_vendor_sample(index=2)], miles_input_sample=clean_inp
    )
    await buf.put(DataBufferInput(prompt_group=[clean_inp], group=[clean]))
    out = await buf.get(current_version=8)
    assert out.group[0][0] is clean[0]
    assert buf.get_metrics()["rollout/fully_async/aborted_groups_filtered"] == 0  # 窗口已重置
