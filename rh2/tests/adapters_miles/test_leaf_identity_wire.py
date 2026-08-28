"""租前聚焦修复批 #1/#3 的 miles 侧接线验收（integration base 专属）。

#1 leaf 唯一身份：slime fan-out 的多个叶继承同一 `Sample.index`
（vendor trajectory.py `to_sample(index=base_sample.index)`，canonicalize
原样保留并强制一致），纯 sample_index 不是叶身份。miles 侧新增薄身份
(sample_index, leaf_ordinal)：

- `compute_leaf_ordinals`：按 run key（rollout_id，None 回退 index）在扁平
  样本顺序上数出现序号；
- `convert_samples_to_train_data` 产出 `leaf_ordinals` wire 列（与
  `sample_indices` 行对齐），`ROLLOUT_DATA_VALUE_SPEC` 与 `_package_shards`
  切分清单同步——dp 分片后 trainer 侧仍拿到逐行对齐的叶身份；
- rollout 侧 `rollout_manager._emit_rollout_evidence` 用**同一函数、同一扁平
  顺序**给 rollout_group 事件盖 leaf_ordinals（两侧身份逐行一致的根据）。

#3 SGLang identity：`SGLangEngine.init()`（broadcast 与 RDT 两种传输模式都
创建的 actor）发 `sglang_engine` identity；`SGLangServerActor`（仅 RDT）保留
原 `sglang_server`。sglang 模块 CPU 环境不可导，用源码锚点钉住发射位置在
模式分派之前（broadcast 可达）。

rollout_id/group_index 的分组语义（GRPO 分组、rollout_mask_sums）不动——
测试同时锚定 fan-out 叶共享 reward/rollout_id 的原有事实。
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration_base


def _mk_leaf(world, *, index: int, rollout_id: int, ordinal_hint: int, reward: float):
    """构造一个进入训练批形态的 miles 叶样本（fan-out 叶共享 index/rollout_id）。"""
    s = world.MS(
        index=index,
        group_index=0,
        rollout_id=rollout_id,
        prompt="p",
        tokens=[10, 11, 12, 13, 14 + ordinal_hint],
        response="resp",
        response_length=3,
        loss_mask=[1, 0, 1],
        reward=reward,
    )
    s.status = world.MS.Status.COMPLETED
    return s


def _fanout_batch(world):
    """4 个 run：run1 双叶 fan-out（共享 index=1/rollout_id=1、共享 reward），
    其余单叶。扁平顺序 = [r0, r1叶0, r1叶1, r2, r3]。"""
    leaves = [
        _mk_leaf(world, index=0, rollout_id=0, ordinal_hint=0, reward=1.0),
        _mk_leaf(world, index=1, rollout_id=1, ordinal_hint=0, reward=0.0),
        _mk_leaf(world, index=1, rollout_id=1, ordinal_hint=1, reward=0.0),
        _mk_leaf(world, index=2, rollout_id=2, ordinal_hint=0, reward=1.0),
        _mk_leaf(world, index=3, rollout_id=3, ordinal_hint=0, reward=0.0),
    ]
    return leaves


def test_compute_leaf_ordinals_counts_per_run(world):
    from miles.ray.rollout.train_data_conversion import compute_leaf_ordinals

    assert compute_leaf_ordinals([0, 1, 1, 2, 1, 3]) == [0, 0, 1, 0, 2, 0]
    assert compute_leaf_ordinals([]) == []


def test_convert_emits_aligned_leaf_ordinals_and_keeps_grouping(world):
    """convert 产出 leaf_ordinals 与 sample_indices 行对齐；fan-out 双叶
    (index, ordinal) = (1,0)/(1,1) 唯一；rollout_ids/rollout_mask_sums 的
    分组语义不变（sibling 叶共享 rollout_id，mask 总和按整 run 计）。"""
    from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data

    args = world.mk_miles_args()
    td = convert_samples_to_train_data(args, _fanout_batch(world), {}, None, None)
    assert td["sample_indices"] == [0, 1, 1, 2, 3]
    assert td["leaf_ordinals"] == [0, 0, 1, 0, 0]
    assert td["rollout_ids"] == [0, 1, 1, 2, 3]
    # 分组语义不动：run1 两叶各 2 个 mask=1 token，整 run 总和 4。
    assert td["rollout_mask_sums"] == [2, 4, 4, 2, 2]


def test_leaf_ordinals_survive_dp_split(world):
    """dp 分片后每 shard 的 leaf_ordinals 仍与该 shard 的 sample_indices
    逐行对齐（trainer 侧 train_step_consumed/replay_fill 的身份来源）。"""
    from miles.ray.rollout.train_data_conversion import (
        ROLLOUT_DATA_VALUE_SPEC,
        convert_samples_to_train_data,
        split_train_data_by_dp_raw,
    )

    assert "leaf_ordinals" in ROLLOUT_DATA_VALUE_SPEC  # wire spec 同步
    args = world.mk_miles_args(balance_data=False)
    td = convert_samples_to_train_data(args, _fanout_batch(world), {}, None, None)
    shards = split_train_data_by_dp_raw(args, td, dp_size=2)
    seen = []
    for shard in shards:
        assert len(shard["leaf_ordinals"]) == len(shard["sample_indices"])
        seen.extend(zip(shard["sample_indices"], shard["leaf_ordinals"]))
    # 两分片并起来恰好是全部 5 个叶身份（无缺失/重复）
    assert sorted(seen) == [(0, 0), (1, 0), (1, 1), (2, 0), (3, 0)]


def test_rollout_group_event_uses_same_ordinal_rule(world):
    """rollout 侧证据与 trainer wire 的身份一致性锚点：rollout_manager 的
    _emit_rollout_evidence 必须用同一 compute_leaf_ordinals、同一 run key
    （rollout_id 回退 index）在扁平顺序上盖 leaf_ordinals。emitter 依赖
    ray/sglang 不可在 CPU 环境实例化，锚定源码接线。"""
    src = (Path(world.miles_root) / "miles" / "ray" / "rollout" / "rollout_manager.py").read_text()
    assert "compute_leaf_ordinals" in src
    assert "leaf_ordinals=leaf_ordinals" in src
    assert "s.rollout_id if s.rollout_id is not None else s.index" in src


def test_trainer_side_emitters_carry_leaf_identity(world):
    """trainer 侧发射点接线锚点（megatron 不可导，源码钉死）：
    - model.py：get_batch 透传 leaf_ordinals；train_step_consumed 事件按消费
      position 切 leaf_ordinals；train_step 事件带 num_rollouts（scheduler
      精确步进 oracle，聚焦修复批 #2）；
    - actor.py：replay_fill 事件带 sample_indices+leaf_ordinals（leaf→digest
      精确联结）；logprob_compare 透传 leaf_ordinals。"""
    backends = Path(world.miles_root) / "miles" / "backends" / "megatron_utils"
    model_src = (backends / "model.py").read_text()
    assert '"leaf_ordinals",' in model_src  # get_batch keys
    assert "[int(leaf_ordinals[p]) for p in positions]" in model_src
    assert "num_rollouts=int(num_rollouts)" in model_src
    actor_src = (backends / "actor.py").read_text()
    assert 'sample_indices=rollout_data.get("sample_indices")' in actor_src
    assert 'leaf_ordinals=rollout_data.get("leaf_ordinals")' in actor_src


def test_sglang_engine_identity_emitted_in_both_transfer_modes(world):
    """聚焦修复批 #3：sglang_server identity 只在 RDT 分支的 SGLangServerActor
    里发（broadcast 启动不创建它——thresholds 要求该角色时真实 G1 确定性
    假红）。修复 = SGLangEngine.init() 在传输模式分派（_init_external/
    _init_normal）**之前**发 sglang_engine identity；不改传输模式。"""
    src = (
        Path(world.miles_root) / "miles" / "backends" / "sglang_utils" / "sglang_engine.py"
    ).read_text()
    emit_pos = src.find('rh2_event_log.assert_and_emit_identity("sglang_engine")')
    assert emit_pos != -1, "SGLangEngine 必须发 sglang_engine identity"
    dispatch_pos = src.find("if self.args.rollout_external:")
    assert dispatch_pos != -1 and emit_pos < dispatch_pos, (
        "identity 发射必须位于传输模式分派之前（broadcast/RDT/external 全部可达）"
    )
    server_actor_src = (
        Path(world.miles_root) / "miles" / "ray" / "rollout" / "sglang_server_actor.py"
    ).read_text()
    assert 'assert_and_emit_identity("sglang_server")' in server_actor_src  # RDT 角色保留
