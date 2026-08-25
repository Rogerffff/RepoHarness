"""C4（本轮扩大版）CPU 纵切：canonicalize 输出 -> miles DefaultDataBuffer
put/get -> postprocess_rollout_data -> convert_samples_to_train_data。

覆盖：COMPLETED / TRUNCATED（metadata 升级路径）/ ABORTED（整组过滤）/
remove_sample（loss mask 清零）/ nested fan-out（sibling 共享 rollout_id、
branch 不增加 rollout 计数）。

纵切终点说明：train conversion（convert_samples_to_train_data）在 CPU 可达
（rh2 venv + conftest 的 ray 最小 stub），因此终点没有停在 postprocess。
更下游的 split_train_data_by_dp / object store 属于分布式面，归 C1/硬件段。
"""

from __future__ import annotations


def _canonicalized_group(world):
    """4 个 execution 的 prompt group（形状 = rh2 统一包裹 list[Sample]）：

    - execution 0：COMPLETED，reward 1.0
    - execution 1：COMPLETED + metadata truncated=True -> miles TRUNCATED
    - execution 2：fan-out 3 分支共享 rollout_id=42
    - execution 3：COMPLETED + remove_sample=True（训练侧 loss mask 应清零）
    """

    inputs = [world.mk_miles_input(index=i, group_index=0) for i in range(4)]
    vendor_outputs = [
        [world.mk_vendor_sample(index=0, group_index=0, reward=1.0)],
        [world.mk_vendor_sample(index=1, group_index=0, truncated=True, reward=0.0)],
        [world.mk_vendor_sample(index=2, group_index=0, rollout_id=42, reward=1.0) for _ in range(3)],
        [world.mk_vendor_sample(index=3, group_index=0, reward=0.0, remove_sample=True)],
    ]
    group = [
        world.canonicalize_group(vend, miles_input_sample=inputs[i])
        for i, vend in enumerate(vendor_outputs)
    ]
    return inputs, group


async def test_vertical_buffer_postprocess_train_conversion(world):
    from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data
    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DataBufferInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args()
    inputs, group = _canonicalized_group(world)

    # -- buffer put/get：canonicalize 后的组按 miles 语义原样通过 --------
    recycled = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))
    await buf.put(DataBufferInput(prompt_group=inputs, group=group))
    got = await buf.get(current_version=8)
    assert got.group is group
    assert recycled == []
    metrics = buf.get_metrics()  # B1 症状 2 的对偶：metrics 全程可算
    assert metrics["rollout/fully_async/aborted_groups_filtered"] == 0
    assert metrics["rollout/fully_async/avg_staleness"] == 1.0  # 8 - 7

    # -- postprocess：validate + flatten；compact 组不做 GBS trim ----------
    data, metadata = postprocess_rollout_data(args, [got.group], train_parallel_config=None)
    assert len(data) == 6  # 3 单样本 + 3 fan-out 分支
    assert all(isinstance(s, world.MS) for s in data)  # B1 症状 3 的对偶
    assert metadata == {}
    # branch 不增加 rollout 计数：6 行只有 4 个 rollout（B4 验收项）
    rollout_ids = [s.rollout_id if s.rollout_id is not None else s.index for s in data]
    assert rollout_ids == [0, 1, 42, 42, 42, 3]
    assert len(set(rollout_ids)) == 4

    # -- train conversion ---------------------------------------------------
    td = convert_samples_to_train_data(args, data, metadata, None, None)

    # TRUNCATED 列来自 miles status（canonicalize 的 metadata 升级路径生效）
    assert td["truncated"] == [0, 1, 0, 0, 0, 0]

    # remove_sample：execution 3 的 loss mask 被清零，其余保持 vendor mask
    assert td["loss_masks"][5] == [0, 0, 0]
    assert td["loss_masks"][0] == [1, 0, 1]

    # fan-out sibling 的 rollout_mask_sums = 整条 rollout 的 mask 总和（2*3=6）；
    # remove_sample 行的 mask 在该统计之前已清零（train conversion 源码顺序），
    # 因此 execution 3 的 rollout mask 总和是 0 而不是 2。
    assert td["rollout_mask_sums"] == [2, 2, 6, 6, 6, 0]

    # reward 归一化按 rollout 去重后广播：sibling 三行拿同一个归一化值
    assert td["rewards"][2] == td["rewards"][3] == td["rewards"][4]
    # raw reward 原样保留
    assert td["raw_reward"] == [1.0, 0.0, 1.0, 1.0, 1.0, 0.0]

    # 逐 token 事实透传
    assert td["rollout_log_probs"][0] == [-0.1, 0.0, -0.25]
    assert td["weight_versions"] == [["7"]] * 6
    assert td["response_lengths"] == [3] * 6


async def test_vertical_aborted_group_filtered_and_recycled(world):
    """ABORTED 覆盖：rh2 abort 收口形状（miles 直通分支产物）整组在 put
    被过滤并回收 prompt——canonicalize 后 miles 的 abort 准入语义真实生效。"""

    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DataBufferInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args()
    recycled = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))

    # execution 0 正常；execution 1 是 abort 收口（输入样本原地改写 + 直通）
    inp0 = world.mk_miles_input(index=0)
    inp1 = world.mk_miles_input(index=1)
    inp1.tokens = [0, 0]
    inp1.response_length = 1
    inp1.loss_mask = [0]
    inp1.rollout_log_probs = [0.0]
    inp1.reward = 0.0
    inp1.remove_sample = True
    inp1.status = world.MS.Status.ABORTED
    inp1.metadata = {"abort_reason": "rh2_gate_degraded"}
    inp1.session_id = "sid-1"

    group = [
        world.canonicalize_group([world.mk_vendor_sample(index=0)], miles_input_sample=inp0),
        world.canonicalize_group([inp1], miles_input_sample=inp1),
    ]
    await buf.put(DataBufferInput(prompt_group=[inp0, inp1], group=group))
    assert recycled == [[inp0, inp1]]
    assert buf.get_metrics()["rollout/fully_async/aborted_groups_filtered"] == 1


async def test_vertical_staleness_get_filter_on_canonicalized_groups(world):
    """canonicalize 携带的 weight_versions 支撑 miles get 侧 staleness 过滤
    （oldest_weight_version 属性链在 miles Sample 上真实可用）。"""

    from miles.rollout.fully_async_data_buffer import (
        DataBufferConstructorInput,
        DataBufferInput,
        DefaultDataBuffer,
    )

    args = world.mk_miles_args(max_weight_staleness=2)
    recycled = []
    buf = DefaultDataBuffer(DataBufferConstructorInput(args=args, unused_handler_fn=recycled.append))

    def one_group(index, versions):
        inp = world.mk_miles_input(index=index)
        return [inp], [
            world.canonicalize_group(
                [world.mk_vendor_sample(index=index, versions=versions)],
                miles_input_sample=inp,
            )
        ]

    stale_prompts, stale_group = one_group(0, versions=("3",))
    fresh_prompts, fresh_group = one_group(1, versions=("9",))
    await buf.put(DataBufferInput(prompt_group=stale_prompts, group=stale_group))
    await buf.put(DataBufferInput(prompt_group=fresh_prompts, group=fresh_group))

    out = await buf.get(current_version=10)  # stale: 10-3=7 > 2 被滤；fresh: 1 通过
    assert out.group is fresh_group
    assert recycled == [stale_prompts]
