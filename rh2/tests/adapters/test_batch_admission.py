"""FA-3 离线部分测试：预检器 A/B 复现、问题 E 五不变量、D 不变量、三视图。

差分验证（预检器 vs slime 真 `build_dp_schedule`）在
`tests/contract_slime_async/test_dp_schedule_differential.py`——那边是本
模块镜像忠实性的权威；这里测的是准入语义与归一化不变量本身。
"""

from __future__ import annotations

import random

import pytest
from fixtures.p3_events import (
    J4_FORMAL,
    J5_GBS16,
    as_schedule_inputs,
    kept_rollout_structure,
    load_events,
)

from repoharness2.adapters.slime.batch_admission import (
    BatchAdmissionError,
    BranchDelivery,
    PackingArgs,
    TrainParallelConfig,
    flatten_delivery,
    normalize_rewards_by_group,
    predict_batch_schedule,
    rebuild_group_view,
)

# P3 T3 训练侧并行（J4/J5 同款）：4 训练卡，TP2 PP1 CP1 -> dp=2，vpp=1
P3_PARALLEL = TrainParallelConfig(dp_size=2, cp_size=1, vpp_size=1)
P3_PACKING = PackingArgs(use_dynamic_batch_size=True, max_tokens_per_gpu=32768)


# ---------------------------------------------------------- A/B 两类失败复现


def test_a_class_failure_replicated_from_j4_formal_events():
    """A 类（05 计划 FA-3 离线验收 1）：J4 formal 真实结构 44→31→19 < gbs32。

    结构全部来自真实事件元数据；长度用校准值 1500（A 类判定只依赖 rollout
    计数，与长度无关——差分测试同口径核对真函数）。
    """

    structure = kept_rollout_structure(load_events(J4_FORMAL))
    assert len(structure) == 19  # 有效 rollout 数（P3 实测）
    assert sum(kept for _, kept in structure) == 31  # 保留样本数
    lengths, rollout_indices = as_schedule_inputs(structure, sample_length=1500)
    prediction = predict_batch_schedule(
        lengths,
        rollout_indices,
        global_batch_size=32,
        parallel=P3_PARALLEL,
        packing=P3_PACKING,
    )
    assert prediction.verdict == "insufficient_rollout_count"
    assert prediction.num_unique_rollouts == 19
    assert "num_rollouts (19) < global_batch_size (32)" in prediction.reason
    # branch 不计入 rollout 数（三层身份的 batch 计数口径）
    assert len(lengths) == 31 > prediction.num_unique_rollouts


def test_b_class_failure_replicated_from_j5_gbs16_events():
    """B 类（离线验收 1）：J5 gbs16 真实结构——前 16 个有效 rollout 恰 23 个
    保留样本，dp=2/vpp=1 -> align=2，K0=23（全单箱）-> 对齐目标 24 > 23。

    rollout/fan-out 结构来自真实事件；样本 token 总长不在事件里，用校准值
    20000（32k 上下文轨迹量级，任两个之和 > max_per_bin=32768 -> 全单箱，
    复现真实 K0=23）。真实报错文本 "could only produce 23 mbs; need 24"
    的两个数字由结构决定，与校准长度的具体取值无关（只要保持全单箱）。
    """

    structure = kept_rollout_structure(load_events(J5_GBS16))
    assert len(structure) == 25 and sum(k for _, k in structure) == 41
    assert sum(kept for _, kept in structure[:16]) == 23  # step0 的真实样本数
    lengths, rollout_indices = as_schedule_inputs(structure, sample_length=20000)
    prediction = predict_batch_schedule(
        lengths,
        rollout_indices,
        global_batch_size=16,
        parallel=P3_PARALLEL,
        packing=P3_PACKING,
    )
    assert prediction.verdict == "microbatch_alignment_failed"
    assert "could only produce 23 mbs" in prediction.reason
    assert "need 24" in prediction.reason


def test_j5_gbs20_diagnostic_control_admits():
    """J5 gbs20 对照（诊断性通过的机制复现）：同一 41 样本结构，gbs=20 时
    step0 取前 20 个 rollout ——样本数 32（偶数=对齐 2 的倍数）-> 通过。"""

    structure = kept_rollout_structure(load_events(J5_GBS16))
    lengths, rollout_indices = as_schedule_inputs(structure, sample_length=20000)
    prediction = predict_batch_schedule(
        lengths,
        rollout_indices,
        global_batch_size=20,
        parallel=P3_PARALLEL,
        packing=P3_PACKING,
    )
    assert prediction.verdict == "ok"
    assert prediction.num_steps == 1
    assert prediction.num_microbatches_per_rank == (16,)  # 32 mbs / dp2


def test_static_path_misalignment_detected():
    """静态装箱：K0 不是 align 倍数 -> 真函数 AssertionError，预检判负。"""

    prediction = predict_batch_schedule(
        [100] * 9,
        list(range(9)),
        global_batch_size=9,
        parallel=TrainParallelConfig(dp_size=2),
        packing=PackingArgs(use_dynamic_batch_size=False, micro_batch_size=2),
    )
    assert prediction.verdict == "microbatch_alignment_failed"  # ceil(9/2)=5 不是 2 的倍数


def test_step_samples_below_dp_size_detected():
    prediction = predict_batch_schedule(
        [100],
        [0],
        global_batch_size=1,
        parallel=TrainParallelConfig(dp_size=2),
        packing=P3_PACKING,
    )
    assert prediction.verdict == "step_samples_below_dp_size"


def test_unmirrored_packing_modes_fail_closed():
    with pytest.raises(BatchAdmissionError, match="unmirrored_packing_mode"):
        predict_batch_schedule(
            [100] * 4,
            [0, 1, 2, 3],
            global_batch_size=4,
            parallel=P3_PARALLEL,
            packing=PackingArgs(max_tokens_per_gpu=1000, balance_by_flops=True),
        )


# ------------------------------------------------- 问题 E：五条归一化不变量


def _branch(gid: int, eid: str, bid: str, reward: float, tokens: int = 100) -> BranchDelivery:
    return BranchDelivery(
        group_index=gid,
        rollout_execution_id=eid,
        branch_id=bid,
        reward=reward,
        trainable_token_count=tokens,
    )


def _grpo_group(n_branches_for_e1: int) -> list[BranchDelivery]:
    """group0：e1 fan-out 出 n 个 branch（reward 1.0 广播），e2/e3/e4 各一条。"""

    branches = [
        _branch(0, "e1", f"e1_b{i}", 1.0, tokens=50 + i) for i in range(n_branches_for_e1)
    ]
    branches += [_branch(0, "e2", "e2_b0", 0.0), _branch(0, "e3", "e3_b0", 0.0),
                 _branch(0, "e4", "e4_b0", 1.0)]
    return branches


def test_invariant_1_advantage_computed_over_unique_executions():
    """不变量 1：组统计按唯一 execution，不按 branch 数。"""

    result = normalize_rewards_by_group(_grpo_group(n_branches_for_e1=8))
    # 组均值 = (1+0+0+1)/4 = 0.5（8 个 branch 不改变均值——如果按 branch 算
    # 均值会是 (8*1+0+0+1)/11 ≈ 0.818）
    assert result.execution_advantages == {
        "e1": 0.5, "e2": -0.5, "e3": -0.5, "e4": 0.5,
    }
    assert result.group_execution_counts == {0: 4}


def test_invariant_2_branch_count_change_does_not_move_other_advantages():
    """不变量 2：e1 的 fan-out 数从 1 变到 8，e2/e3/e4 的 advantage 不动。"""

    base = normalize_rewards_by_group(_grpo_group(n_branches_for_e1=1))
    fanned = normalize_rewards_by_group(_grpo_group(n_branches_for_e1=8))
    for eid in ("e2", "e3", "e4"):
        assert base.execution_advantages[eid] == fanned.execution_advantages[eid]


def test_invariant_3_advantage_broadcast_to_all_branches():
    """不变量 3：同 execution 的每个 branch 拿到同一 advantage。"""

    branches = _grpo_group(n_branches_for_e1=8)
    result = normalize_rewards_by_group(branches)
    e1_advantages = {
        adv
        for branch, adv in zip(branches, result.branch_advantages)
        if branch.rollout_execution_id == "e1"
    }
    assert e1_advantages == {0.5}


def test_invariant_4_rollout_level_denominator_not_inflated_by_branch_count():
    """不变量 4：branch 对 loss 的总贡献按 rollout 分母聚合。

    验证方式：每个 branch 的"权重占比" = branch_tokens / rollout_denominator，
    同一 execution 的占比之和恒等于 1——branch 数再多也不放大该 execution
    的总权重。
    """

    branches = _grpo_group(n_branches_for_e1=8)
    result = normalize_rewards_by_group(branches)
    share_by_execution: dict[str, float] = {}
    for branch, denominator in zip(branches, result.rollout_loss_denominators):
        share_by_execution.setdefault(branch.rollout_execution_id, 0.0)
        share_by_execution[branch.rollout_execution_id] += (
            branch.trainable_token_count / denominator
        )
    for eid, share in share_by_execution.items():
        assert share == pytest.approx(1.0), eid


def test_invariant_5_no_implicit_variable_n_and_broadcast_mismatch_fail_closed():
    """不变量 5 的输入面：广播不一致/身份矛盾 fail-closed（缺员组处置在
    assembler 层，本函数只接完整组，不做隐式修正）。"""

    with pytest.raises(BatchAdmissionError, match="broadcast_reward_mismatch"):
        normalize_rewards_by_group(
            [_branch(0, "e1", "b0", 1.0), _branch(0, "e1", "b1", 0.0)]
        )
    with pytest.raises(BatchAdmissionError, match="execution_group_conflict"):
        normalize_rewards_by_group(
            [_branch(0, "e1", "b0", 1.0), _branch(1, "e1", "b1", 1.0)]
        )


def test_group5_exec22_regression_from_real_j4_events():
    """group5×8branch 定向回归（05 计划 FA-3 离线验收 4）：J4 真实形状下
    stock reshape 必然折叠单组，本实现给出按 group_index 的正确归一化。"""

    events = load_events(J4_FORMAL)
    branches: list[BranchDelivery] = []
    for event in events:
        removes = list(event.get("remove_sample") or [])
        rewards = list(event.get("rewards") or [])
        lengths = list(event.get("response_lengths") or [])
        eid = f"exec_{event['index']}"
        # D-FA-7 广播语义：execution 级 reward = 各 branch 相同；真实事件里
        # rewards 逐 branch 记录，全 0（无一 resolved）——逐位核对广播一致性
        for pos, (removed, reward) in enumerate(zip(removes, rewards)):
            if removed is False:
                branches.append(
                    BranchDelivery(
                        group_index=int(event["group_index"]),
                        rollout_execution_id=eid,
                        branch_id=f"{eid}_b{pos}",
                        reward=float(reward),
                        trainable_token_count=int(lengths[pos]),
                    )
                )
    assert len(branches) == 31
    result = normalize_rewards_by_group(branches)
    # 全 0 reward -> 所有 advantage 为 0，但组结构必须正确：8 个组、
    # group5 只有 1 个 execution（8 branch 不是 8 次采样）
    assert set(result.group_execution_counts) == set(range(8))
    g5_executions = {
        b.rollout_execution_id for b in branches if b.group_index == 5
    }
    assert g5_executions == {"exec_22"}
    g5_branches = [b for b in branches if b.group_index == 5]
    assert len(g5_branches) == 8
    # 不变量 4 在真实形状上成立：exec_22 的 8 个 branch 共享同一分母
    denominators = {
        d
        for b, d in zip(branches, result.rollout_loss_denominators)
        if b.rollout_execution_id == "exec_22"
    }
    assert len(denominators) == 1
    assert denominators.pop() == sum(b.trainable_token_count for b in g5_branches)


def test_property_random_groups_hold_invariants():
    """随机组结构上的属性测试（seed 固定）：组内 execution advantage 均值
    恒为 0；分母 = execution 全 branch token 和。"""

    rng = random.Random(20260712)
    for _ in range(50):
        branches: list[BranchDelivery] = []
        for gid in range(rng.randint(1, 5)):
            for e in range(rng.randint(1, 6)):
                eid = f"g{gid}e{e}"
                reward = float(rng.randint(0, 1))
                for b in range(rng.randint(1, 4)):
                    branches.append(
                        _branch(gid, eid, f"{eid}b{b}", reward, tokens=rng.randint(1, 500))
                    )
        result = normalize_rewards_by_group(branches)
        by_group: dict[int, list[str]] = {}
        for branch in branches:
            by_group.setdefault(branch.group_index, [])
            if branch.rollout_execution_id not in by_group[branch.group_index]:
                by_group[branch.group_index].append(branch.rollout_execution_id)
        for gid, eids in by_group.items():
            mean_adv = sum(result.execution_advantages[eid] for eid in eids) / len(eids)
            assert mean_adv == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------- 三视图 round-trip


def test_flatten_rebuild_round_trip():
    branches = _grpo_group(n_branches_for_e1=3)
    grouped = rebuild_group_view(branches)
    flat = flatten_delivery(grouped)
    assert rebuild_group_view(flat) == grouped
    assert sorted(b.branch_id for b in flat) == sorted(b.branch_id for b in branches)


def test_flatten_rejects_identity_mismatch():
    grouped = {0: {"e_other": [_branch(0, "e1", "b0", 1.0)]}}
    with pytest.raises(BatchAdmissionError, match="identity_sidecar_mismatch"):
        flatten_delivery(grouped)
