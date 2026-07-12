"""FA-3 离线部分：batch schedule 准入预检 + 层次化 GRPO 归一化 + 三视图展平。

出处：05 计划 FA-3（原 S2-0b 问题 A~E 迁入）。本模块是**纯函数层**——不碰
队列/事务/lease（那些是 FA-3 接线部分，依赖 FA-2 的 assembler 运行时）。

三个职责，对应问题 A/B、E、C：

1. ``predict_batch_schedule``：镜像 slime ``slime/utils/dp_schedule.py::
   build_dp_schedule``（pin e848052a）的**准入相关语义**，在不起 slime 的
   情况下判出 A 类（rollout 数不足）与 B 类（microbatch 对齐失败）失败。
   镜像的忠实性由差分测试保证（同一输入喂本预测器与 slime 真函数，
   成功/失败类别、step 数、每 rank microbatch 数三项必须一致）——差分
   测试是本模块的**正确性权威**，改本模块必须先过差分。
2. ``normalize_rewards_by_group``：问题 E 的层次化优势归一化（group_index
   键控，advantage 按唯一 RolloutExecution 计算后广播给 branches，
   rollout 级 loss 分母），替代 slime stock ``_post_process_rewards`` 的
   reshape-by-shape 逻辑（J5 gbs20 保留 36≠32 时折叠单组的实锤缺陷）。
3. ``flatten_delivery`` / ``rebuild_group_view``：问题 C 的交付边界三视图
   （内部三层结构 ↔ 平铺 list + 身份 sidecar 无损回链）。

预检失败的记账归属（FA-0 已定）：结论进批次级 BatchAdmissionReport /
`BackendHandshake.backend_rejection_reason`，**不碰 eligibility**。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "BatchAdmissionError",
    "BatchSchedulePrediction",
    "BranchDelivery",
    "GroupNormalizationResult",
    "PackingArgs",
    "ScheduleVerdict",
    "TrainParallelConfig",
    "flatten_delivery",
    "normalize_rewards_by_group",
    "predict_batch_schedule",
    "rebuild_group_view",
]


class BatchAdmissionError(ValueError):
    """输入事实不合法（与"预检判负"不同——判负是合法输入的合法结论）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


# ---------------------------------------------------------------------------
# 1. batch schedule 预检（问题 A/B）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainParallelConfig:
    """`build_dp_schedule` 的 train_parallel_config 同构镜像。"""

    dp_size: int
    cp_size: int = 1
    vpp_size: int = 1
    microbatch_group_size_per_vp_stage: int = 1

    @property
    def align_to(self) -> int:
        """microbatch 数的对齐模数（dp_schedule.py:124 同式）。"""

        mb_group = self.microbatch_group_size_per_vp_stage if self.vpp_size > 1 else 1
        return self.dp_size * mb_group


@dataclass(frozen=True)
class PackingArgs:
    """`build_dp_schedule` 的 args 依赖面镜像（P3 配置：flops/balance 均关）。"""

    use_dynamic_batch_size: bool = True
    max_tokens_per_gpu: int | None = None
    micro_batch_size: int | None = None
    # balance_by_flops / balance_data 影响的是 mbs 内容分布，不影响
    # 准入判定（K 与断言路径）；P3/首训配置均为 False，预检镜像按 False
    # 语义实现，差分测试同口径（开启它们属于未镜像面，fail-closed 拒绝）。
    balance_by_flops: bool = False
    balance_data: bool = False


ScheduleVerdict = Literal[
    "ok",
    "insufficient_rollout_count",  # A 类：唯一 rollout 数 < global_batch_size
    "step_samples_below_dp_size",  # 某 step 样本数 < dp_size（build_dp_schedule 同名断言）
    "microbatch_alignment_failed",  # B 类：对齐后所需 K 超过可拆分上限 / 静态模数不合
]


@dataclass(frozen=True)
class BatchSchedulePrediction:
    verdict: ScheduleVerdict
    reason: str
    align_to: int
    num_unique_rollouts: int
    num_steps: int  # 判负时为 0 或已能确定的 step 数
    num_microbatches_per_rank: tuple[int, ...] = ()  # verdict=ok 时逐 step

    @property
    def admitted(self) -> bool:
        return self.verdict == "ok"


def _first_fit_pack_mirror(lengths: list[int], max_per_bin: int) -> list[list[int]]:
    """slime `seqlen_balancing.first_fit_pack` 的逐行镜像（差分测试守护）。"""

    bins: list[list[int]] = []
    bin_sums: list[int] = []
    for idx, length in enumerate(lengths):
        for j in range(len(bins)):
            if bin_sums[j] + length <= max_per_bin:
                bins[j].append(idx)
                bin_sums[j] += length
                break
        else:
            bins.append([idx])
            bin_sums.append(length)
    return bins


def predict_batch_schedule(
    total_lengths: list[int],
    rollout_indices: list[int],
    *,
    global_batch_size: int,
    parallel: TrainParallelConfig,
    packing: PackingArgs,
) -> BatchSchedulePrediction:
    """在不起 slime 的情况下预判 `build_dp_schedule` 的准入结论。

    输入语义与真函数逐项对应：`total_lengths[i]` = 第 i 个训练样本的 token
    数；`rollout_indices[i]` = 该样本所属 RolloutExecution 的 id
    （fan-out 的多个 branch 共享同一 id——**branch 不增加 rollout 数**，
    三层身份模型的 batch 计数口径）。

    判定逻辑镜像 dp_schedule.py（pin e848052a）：

    - A 类：唯一 rollout 数 // global_batch_size < 1（:139 断言）；
    - 逐 step：样本数 < dp_size（:151 断言）；
    - B 类动态路径：对齐目标 target_K = round_up(K0, align_to)（K0 =
      first-fit 装箱数），最大可拆分上限 = 该 step 样本数——
      target_K > 样本数即 `expand_bins_by_splitting` 后仍不足（:171 断言，
      P3 J5 gbs16 的 "could only produce 23 mbs; need 24" 即此形态）；
    - B 类静态路径：K0 % align_to != 0 直接 AssertionError（:177）。
    """

    if len(total_lengths) != len(rollout_indices):
        raise BatchAdmissionError(
            "lengths_rollout_indices_mismatch",
            f"total_lengths({len(total_lengths)}) 与 rollout_indices({len(rollout_indices)}) 不等长。",
        )
    if any(length <= 0 for length in total_lengths):
        raise BatchAdmissionError("non_positive_sample_length", "样本 token 数必须为正。")
    if global_batch_size < 1:
        raise BatchAdmissionError("invalid_global_batch_size", "global_batch_size 必须 >= 1。")
    if packing.balance_by_flops or packing.balance_data:
        raise BatchAdmissionError(
            "unmirrored_packing_mode",
            "balance_by_flops/balance_data 未镜像（P3/首训配置均关闭）——"
            "开启前必须先扩展预检器并重过差分测试，fail-closed。",
        )
    if packing.use_dynamic_batch_size:
        if packing.max_tokens_per_gpu is None:
            raise BatchAdmissionError(
                "max_tokens_per_gpu_missing", "动态装箱要求 max_tokens_per_gpu（真函数同断言）。"
            )
    elif packing.micro_batch_size is None:
        raise BatchAdmissionError(
            "micro_batch_size_missing", "静态装箱要求 micro_batch_size（真函数同断言）。"
        )

    align_to = parallel.align_to

    # rollout 分组（保持首次出现顺序——真函数 :131-135 同语义）
    rollout_to_samples: dict[int, list[int]] = {}
    for pos, rid in enumerate(rollout_indices):
        rollout_to_samples.setdefault(rid, []).append(pos)
    rollout_ids = list(rollout_to_samples.keys())
    num_rollouts = len(rollout_ids)

    num_steps = num_rollouts // global_batch_size
    if num_steps < 1:
        return BatchSchedulePrediction(
            verdict="insufficient_rollout_count",
            reason=(
                f"num_rollouts ({num_rollouts}) < global_batch_size ({global_batch_size})"
                "——A 类失败（P3 formal J4 形态）。branch 不计入 rollout 数。"
            ),
            align_to=align_to,
            num_unique_rollouts=num_rollouts,
            num_steps=0,
        )

    per_rank: list[int] = []
    for step_i in range(num_steps):
        step_rollouts = rollout_ids[step_i * global_batch_size : (step_i + 1) * global_batch_size]
        sample_positions = [pos for rid in step_rollouts for pos in rollout_to_samples[rid]]
        step_lengths = [total_lengths[i] for i in sample_positions]
        if len(sample_positions) < parallel.dp_size:
            return BatchSchedulePrediction(
                verdict="step_samples_below_dp_size",
                reason=(
                    f"step {step_i}: {len(sample_positions)} samples < dp_size "
                    f"{parallel.dp_size}（每 rank 至少 1 个样本）。"
                ),
                align_to=align_to,
                num_unique_rollouts=num_rollouts,
                num_steps=num_steps,
            )
        if packing.use_dynamic_batch_size:
            max_per_bin = packing.max_tokens_per_gpu * parallel.cp_size
            k0 = len(_first_fit_pack_mirror(step_lengths, max_per_bin))
            target_k = max(math.ceil(k0 / align_to) * align_to, align_to)
            if target_k > len(sample_positions):
                return BatchSchedulePrediction(
                    verdict="microbatch_alignment_failed",
                    reason=(
                        f"step {step_i}: could only produce {len(sample_positions)} mbs "
                        f"after maximal splitting; need {target_k}（B 类失败，"
                        f"P3 J5 gbs16 形态；K0={k0}, align_to={align_to}）。"
                    ),
                    align_to=align_to,
                    num_unique_rollouts=num_rollouts,
                    num_steps=num_steps,
                )
            k = target_k if k0 % align_to != 0 else k0
        else:
            n = len(sample_positions)
            k0 = math.ceil(n / packing.micro_batch_size)
            if k0 % align_to != 0:
                return BatchSchedulePrediction(
                    verdict="microbatch_alignment_failed",
                    reason=(
                        f"step {step_i}: static num_mbs ({k0}) 不是 align_to({align_to}) 的"
                        "倍数（静态路径不允许拆分，真函数直接 AssertionError）。"
                    ),
                    align_to=align_to,
                    num_unique_rollouts=num_rollouts,
                    num_steps=num_steps,
                )
            k = k0
        per_rank.append(k // parallel.dp_size)

    return BatchSchedulePrediction(
        verdict="ok",
        reason="schedule admissible",
        align_to=align_to,
        num_unique_rollouts=num_rollouts,
        num_steps=num_steps,
        num_microbatches_per_rank=tuple(per_rank),
    )


# ---------------------------------------------------------------------------
# 2. 层次化 GRPO 归一化（问题 E）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchDelivery:
    """一条交付 branch 的归一化输入（三层身份 + reward/token 事实）。"""

    group_index: int
    rollout_execution_id: str
    branch_id: str
    reward: float
    trainable_token_count: int


@dataclass(frozen=True)
class GroupNormalizationResult:
    """归一化产物：branch 级 advantage + rollout 级分母（顺序与输入一致）。"""

    branch_advantages: tuple[float, ...]
    rollout_loss_denominators: tuple[int, ...]  # 逐 branch：其所属 execution 的分母
    execution_advantages: dict[str, float] = field(default_factory=dict)
    group_execution_counts: dict[int, int] = field(default_factory=dict)


def normalize_rewards_by_group(
    branches: list[BranchDelivery],
    *,
    std_normalization: bool = False,
    std_epsilon: float = 1e-6,
) -> GroupNormalizationResult:
    """问题 E：group_index 键控的层次化优势归一化。

    五条不变量（05 计划 FA-3 验收，属性测试逐条钉）：

    1. 同 prompt group 内先按**唯一 RolloutExecution** 计算 reward/advantage
       （reward 是执行级事实——D-FA-7 广播语义下同 execution 的所有 branch
       必须携带相同 reward，不一致即输入矛盾 fail-closed）；
    2. 一个 execution 的 branch 数变化不得改变**其他** execution 的 advantage；
    3. 同一 execution 的 advantage 广播给它的全部 branches；
    4. branch 对 loss 的总贡献按 rollout 级分母聚合（分母 = 该 execution
       全部 branch 的 trainable token 数之和），不随 branch 数放大；
    5. 缺员组处置（整组补采/整组拒绝）在 assembler 层（本函数不做隐式
       可变 n 修正——组内有几个 execution 就按几个归一化，调用方负责
       只喂完整组）。

    对照：slime stock `_post_process_rewards` 按形状 reshape，保留样本数
    偏离名义值时 `view(-1, total)` 折叠单组（J5 gbs20 实锤）；本实现与
    `reference/slime/slime/rollout/_fanout_test_helpers.py::
    grpo_normalize_by_group_index` 原型同语义。
    """

    if not branches:
        raise BatchAdmissionError("empty_delivery", "归一化输入为空。")

    # execution 级事实收集 + 广播一致性校验（不变量 1 的输入面）
    execution_reward: dict[str, float] = {}
    execution_group: dict[str, int] = {}
    execution_token_sum: dict[str, int] = {}
    for branch in branches:
        if branch.trainable_token_count < 0:
            raise BatchAdmissionError("negative_token_count", f"{branch.branch_id} token 数为负。")
        eid = branch.rollout_execution_id
        if eid in execution_reward:
            if execution_reward[eid] != branch.reward:
                raise BatchAdmissionError(
                    "broadcast_reward_mismatch",
                    f"execution {eid} 的 branch 间 reward 不一致"
                    f"（{execution_reward[eid]} vs {branch.reward}）——违反 D-FA-7 广播语义。",
                )
            if execution_group[eid] != branch.group_index:
                raise BatchAdmissionError(
                    "execution_group_conflict",
                    f"execution {eid} 出现在两个 group（{execution_group[eid]} vs "
                    f"{branch.group_index}）——三层身份矛盾。",
                )
        else:
            execution_reward[eid] = branch.reward
            execution_group[eid] = branch.group_index
            execution_token_sum[eid] = 0
        execution_token_sum[eid] += branch.trainable_token_count

    # group -> executions（不变量 1：按唯一 execution 计算组统计）
    group_to_executions: dict[int, list[str]] = {}
    for eid, gid in execution_group.items():
        group_to_executions.setdefault(gid, []).append(eid)

    execution_advantage: dict[str, float] = {}
    for gid, eids in group_to_executions.items():
        rewards = [execution_reward[eid] for eid in eids]
        mean = sum(rewards) / len(rewards)
        if std_normalization:
            variance = sum((r - mean) ** 2 for r in rewards) / len(rewards)
            denom = math.sqrt(variance) + std_epsilon
            for eid in eids:
                execution_advantage[eid] = (execution_reward[eid] - mean) / denom
        else:
            for eid in eids:
                execution_advantage[eid] = execution_reward[eid] - mean

    return GroupNormalizationResult(
        branch_advantages=tuple(
            execution_advantage[b.rollout_execution_id] for b in branches
        ),
        rollout_loss_denominators=tuple(
            execution_token_sum[b.rollout_execution_id] for b in branches
        ),
        execution_advantages=execution_advantage,
        group_execution_counts={gid: len(eids) for gid, eids in group_to_executions.items()},
    )


# ---------------------------------------------------------------------------
# 3. 交付边界三视图（问题 C 的纯函数半区；队列接线归 FA-1/FA-2）
# ---------------------------------------------------------------------------


def flatten_delivery(
    groups: dict[int, dict[str, list[BranchDelivery]]],
) -> list[BranchDelivery]:
    """内部三层结构（group -> execution -> branches）→ 平铺 list。

    身份 sidecar 就是 BranchDelivery 自身的三层字段——平铺不丢失任何身份；
    `rebuild_group_view` 可无损还原（round-trip 测试钉死）。顺序确定性：
    按 group_index、execution 首次插入顺序、branch 列表顺序。
    """

    flat: list[BranchDelivery] = []
    for gid in sorted(groups):
        for eid, branch_list in groups[gid].items():
            for branch in branch_list:
                if branch.group_index != gid or branch.rollout_execution_id != eid:
                    raise BatchAdmissionError(
                        "identity_sidecar_mismatch",
                        f"branch {branch.branch_id} 的身份字段与所在结构位置不一致"
                        f"（{branch.group_index}/{branch.rollout_execution_id} vs {gid}/{eid}）。",
                    )
                flat.append(branch)
    return flat


def rebuild_group_view(
    flat: list[BranchDelivery],
) -> dict[int, dict[str, list[BranchDelivery]]]:
    """平铺 list → 三层结构（凭身份字段无损回链）。"""

    groups: dict[int, dict[str, list[BranchDelivery]]] = {}
    for branch in flat:
        groups.setdefault(branch.group_index, {}).setdefault(
            branch.rollout_execution_id, []
        ).append(branch)
    return groups
