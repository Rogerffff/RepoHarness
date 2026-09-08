#!/usr/bin/env python3
"""NeMo RL 阅读笔记的独立 CPU 语义探针，不是上游测试套件。

需要 Python >=3.10 和 PyTorch；不需要网络、GPU、Ray 或 NeMo 安装。
脚本独立实现所读源码涉及的小型归约、布局与反例，不导入 NeMo，也不执行
其模型内核。通过只说明这些例子的代数与张量行为符合预期，不证明分布式
训练正确，也不代表取得了性能提升。

来源固定：NVIDIA-NeMo/RL@13182a5f24a47856aa9191f651510d0df249c9c0。
相关路径：algorithms/utils.py；algorithms/loss/{loss_functions,wrapper}.py；
distributed/batched_data_dict.py；data_plane/preshard.py；models/megatron/train.py。
"""
from __future__ import annotations
import argparse
import json
import math
import platform
from pathlib import Path
from typing import Callable
import torch

EPS = 1e-8
DTYPE = torch.float64
SOURCE_COMMIT = "13182a5f24a47856aa9191f651510d0df249c9c0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(a: torch.Tensor, b: torch.Tensor, tolerance: float = 1e-12) -> None:
    torch.testing.assert_close(a, b, rtol=tolerance, atol=tolerance)


def masked_mean(values: torch.Tensor, mask: torch.Tensor,
                denominator: torch.Tensor | None = None,
                dim: int | None = None) -> torch.Tensor:
    """沿用来源的归约定义：分母加 EPS，不是 clamp(min=1)。"""
    n = mask.sum(dim=dim) if denominator is None else denominator
    return (values * mask).sum(dim=dim) / (n + EPS)


def value_and_grad(fn: Callable[[torch.Tensor], torch.Tensor],
                   initial: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    x = initial.clone().requires_grad_(True)
    y = fn(x)
    (g,) = torch.autograd.grad(y, x)
    return y.detach(), g.detach()


def probe_global_token_reduction() -> dict:
    x = torch.tensor([[1., 2., 3., 4.], [5., 6., 7., 8.],
                      [9., 10., 11., 12.], [13., 14., 15., 16.]], dtype=DTYPE)
    masks = torch.tensor([[1., 0., 0., 0.], [1., 1., 1., 0.],
                          [0., 0., 0., 0.], [1., 0., 1., 0.]], dtype=DTYPE)
    denominator = masks.sum()
    ref, ref_grad = value_and_grad(lambda z: masked_mean(z, masks, denominator), x)
    partitions = [[[0, 1, 2, 3]], [[2, 0], [3], [1]], [[0], [1], [2], [3]]]
    errors = []
    for partition in partitions:
        out, grad = value_and_grad(
            lambda z: sum(masked_mean(z[ids], masks[ids], denominator)
                          for ids in partition), x)
        close(out, ref); close(grad, ref_grad)
        errors.append(float((grad - ref_grad).abs().max()))
    wrong, _ = value_and_grad(
        lambda z: (masked_mean(z[[0]], masks[[0]]) +
                   masked_mean(z[[1, 2, 3]], masks[[1, 2, 3]])) / 2, x)
    require(abs(float(wrong - ref)) > .1, "负对照未产生预期差异")
    return {"global_mean": float(ref), "partition_gradient_max_errors": errors,
            "incorrect_mean_of_local_means": float(wrong), "valid_tokens": 6}


def probe_sequence_vs_token() -> dict:
    x = torch.tensor([[1., 0., 0.], [3., 3., 3.]], dtype=DTYPE)
    t = torch.tensor([[1., 0., 0.], [1., 1., 1.]], dtype=DTYPE)
    s = torch.ones(2, dtype=DTYPE)
    token = masked_mean(x, t)
    seq = masked_mean(masked_mean(x, t, dim=-1), s)
    require(abs(float(token - seq)) > .4, "两种目标应当不同")
    return {"token_objective": float(token), "sequence_objective": float(seq),
            "interpretation": "这是两种不同的声明目标，不是舍入误差。"}


def probe_permutation_contract() -> dict:
    original = torch.tensor([10, 20, 30, 40])
    forward = [2, 0, 3, 1]  # 新位置 → 旧位置；特意选择不等于其逆置换的例子
    inverse = [0] * len(forward)
    for new_pos, old_pos in enumerate(forward):
        inverse[old_pos] = new_pos
    reordered = original[forward]
    # BatchedDataDict.reorder_data 会在内部对传入置换取 argsort。
    restore = lambda arg: reordered[torch.argsort(torch.tensor(arg))]
    require(torch.equal(restore(forward), original), "正向置换契约不成立")
    require(not torch.equal(restore(inverse), original), "负对照未产生预期差异")
    return {"original": original.tolist(), "forward": forward, "inverse": inverse,
            "restored_with_forward": restore(forward).tolist(),
            "inverse_passed_to_inverse_applying_API": restore(inverse).tolist(),
            "scope": "针对 preshard 返回值/文档契约；已检查的 TQ 调用丢弃该返回值。"}


def probe_dynamic_coordination() -> dict:
    # 两个 rank 行数相同，但独立规划会得到不同 microbatch 数。
    lengths_by_rank = [[2, 2, 2, 2], [2, 2, 7, 7]]
    budget = 10
    def schedule(lengths: list[int]) -> list[list[int]]:
        batches: list[list[int]] = []; current: list[int] = []; maximum = 0
        for pos, length in enumerate(lengths):
            require(0 < length <= budget, "行长度不满足预算约束")
            proposed = max(maximum, length)
            if current and (len(current) + 1) * proposed > budget:
                batches.append(current); current = []; maximum = 0
            current.append(pos); maximum = max(maximum, length)
        if current: batches.append(current)
        return batches
    local = [schedule(x) for x in lengths_by_rank]
    coordinated = schedule([max(x) for x in zip(*lengths_by_rank)])
    require(len(local[0]) != len(local[1]), "负对照未产生预期差异")
    for rows in coordinated:
        for rank_lengths in lengths_by_rank:
            require(len(rows) * max(rank_lengths[i] for i in rows) <= budget,
                    "协调方案超过 token 容量")
    return {"independent_microbatch_counts": [len(x) for x in local],
            "coordinated_rows": coordinated,
            "coordinated_microbatch_counts": [len(coordinated)] * 2,
            "scope": "独立示意规划器，未调用 NeMo shard_by_batch_size。"}


def probe_cp_layout() -> dict:
    sequences = [list(range(10, 15)), list(range(20, 29)), [30]]
    cp = 2; align = 2 * cp
    shards: list[list[tuple[int, int]]] = [[] for _ in range(cp)]
    physical_lengths = []
    for sample, seq in enumerate(sequences):
        padded = math.ceil(len(seq) / align) * align
        physical_lengths.append(padded)
        width = padded // (2 * cp)
        tags = [(sample, p) if p < len(seq) else (-1, -1) for p in range(padded)]
        for rank in range(cp):
            chunks = [rank, 2 * cp - rank - 1]
            for c in chunks:
                shards[rank].extend(tags[c * width:(c + 1) * width])
    actual = [tag for shard in shards for tag in shard if tag[0] != -1]
    expected = [(sample, p) for sample, seq in enumerate(sequences) for p in range(len(seq))]
    require(sorted(actual) == sorted(expected), "token 身份缺失或重复")
    require(len(shards[0]) == len(shards[1]), "CP 本地物理长度不同")
    return {"real_lengths": list(map(len, sequences)), "padded_lengths": physical_lengths,
            "rank_local_physical_tokens": list(map(len, shards)),
            "real_token_identity_count": len(actual),
            "scope": "只验证 token 身份往返，不执行 CP attention 或通信内核。"}


def probe_packed_boundary() -> dict:
    packed = torch.tensor([[10, 11, 12, 20, 21]])
    cu = torch.tensor([0, 3, 5])
    naive = packed.roll(-1, dims=1)
    safe = naive.clone(); safe[:, cu[1:] - 1] = 0
    require(naive[0, 2].item() == 20 and safe[0, 2].item() == 0,
            "边界反例不成立")
    require(safe[0, -1].item() == 0, "未移除尾部环绕目标")
    return {"global_roll": naive.tolist(), "boundary_safe_roll": safe.tolist(),
            "scope": "逐段移位示意；真实 loss 还必须排除无效目标位置。"}


def probe_scaling_algebra() -> dict:
    numerator = 12.; denominator = 6.; dp = 4; cp = 2; micro = 3
    local_loss = numerator / denominator
    megatron_after = local_loss / cp * (micro / cp) * (cp / micro)
    require(abs(megatron_after * cp - local_loss) < 1e-12, "CP fanout 代数核算不成立")
    results = []
    for fanout in (1, cp):
        scaled = local_loss * dp * cp / fanout
        after_average_and_fanout = scaled / (dp * cp) * fanout
        require(abs(after_average_and_fanout - local_loss) < 1e-12,
                "FSDP 平均补偿不成立")
        results.append({"cp_loss_fanout": fanout, "recovered": after_average_and_fanout})
    return {"megatron_replica_local": megatron_after,
            "after_CP_loss_fanout": megatron_after * cp,
            "automodel_cases": results,
            "scope": "标量缩放核算，不是分布式 autograd 或 reducer 实测。"}


def probe_optional_positive_nll() -> dict:
    logprobs = torch.tensor([[-1., 0., 0.], [-3., -3., -3.]], dtype=DTYPE)
    mask = torch.tensor([[1., 0., 0.], [1., 1., 1.]], dtype=DTYPE)
    # 单独检查可选 NLL 项：两条样本的 reward 都为正。
    # 源码在每次 loss 调用内部计算 correct_valid_toks。
    joint, joint_grad = value_and_grad(lambda z: masked_mean(-z, mask, mask.sum()), logprobs)
    per_seq, per_seq_grad = value_and_grad(
        lambda z: sum(masked_mean(-z[i:i+1], mask[i:i+1], mask[i:i+1].sum())
                      for i in range(2)), logprobs)
    require(abs(float(joint - per_seq)) > 1., "负对照未产生预期差异")
    require(not torch.allclose(joint_grad, per_seq_grad), "两种划分的梯度应当不同")
    return {"one_invocation_aux_loss": float(joint),
            "per_sequence_invocations_aux_loss": float(per_seq),
            "one_invocation_gradient": joint_grad.tolist(),
            "per_sequence_gradient": per_seq_grad.tolist(),
            "scope": "复现可选 NLL 的局部归约；默认关闭；未运行完整 NeMo forward。"}


def probe_zero_mask_and_nan() -> dict:
    zero = torch.zeros(3, dtype=DTYPE)
    finite = masked_mean(torch.tensor([1., 2., 3.], dtype=DTYPE), zero)
    nan_result = masked_mean(torch.tensor([float('nan'), 2., 3.], dtype=DTYPE), zero)
    require(float(finite) == 0., "有限值输入全部屏蔽时应返回零")
    require(bool(torch.isnan(nan_result)), "乘零 mask 不会消除 NaN")
    return {"finite_all_masked_result": float(finite), "NaN_survives_zero_mask": True,
            "scope": "说明有限值前提，不主张真实 NeMo 作业已经产生 NaN。"}


def probe_budget_and_metadata_width() -> dict:
    lengths = [65, 65]; align = 64; cap = 192
    padded = [math.ceil(x / align) * align for x in lengths]
    require(sum(lengths) <= cap < sum(padded), "padding 预算反例不成立")
    n = 512; width = 32768
    return {"raw_total": sum(lengths), "aligned_total": sum(padded), "capacity": cap,
            "int64_skeleton_example_shape": [n, width],
            "dense_storage_bytes": n * width * 8,
            "dense_storage_MiB": n * width * 8 / 2**20,
            "scope": "计算得到的分配大小，不是实测生产内存峰值或瓶颈。"}


PROBES = [probe_global_token_reduction, probe_sequence_vs_token,
          probe_permutation_contract, probe_dynamic_coordination, probe_cp_layout,
          probe_packed_boundary, probe_scaling_algebra, probe_optional_positive_nll,
          probe_zero_mask_and_nan, probe_budget_and_metadata_width]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    torch.set_num_threads(1)
    output = {"source_commit": SOURCE_COMMIT, "python": platform.python_version(),
              "torch": torch.__version__, "cuda_available": torch.cuda.is_available(),
              "execution_kind": "独立 CPU 语义探针；未导入上游测试套件",
              "results": []}
    for probe in PROBES:
        result = probe()
        output['results'].append({"name": probe.__name__, "status": "PASS", **result})
    output['passed'] = len(PROBES)
    text = json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
    print(text)

if __name__ == '__main__':
    main()
