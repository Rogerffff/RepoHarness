"""合成 rollout 数据生成器（J0.5 / J3 用，协议 §4：J1~J3 用合成数据）。

产物格式 = slime 的 --save-debug-rollout-data 落盘格式（锚：
reference/slime/slime/ray/rollout.py:667 `_save_debug_rollout_data`：
``torch.save(dict(rollout_id=..., samples=[sample.to_dict(), ...]), path)``），
供 ``--load-debug-rollout-data`` + ``--debug-train-only`` 直接消费（锚：
reference/slime/slime/ray/rollout.py:636 `_get_rollout_data`，该路径完全不起
SGLang，正好用于 J3 的"合成固定 batch 过 Megatron train step"）。

字段契约（锚：reference/slime/slime/utils/types.py Sample dataclass）：
- ``loss_mask`` 长度 == ``response_length``；
- ``rollout_log_probs`` 长度 == ``response_length``；
- top-p tape：``rollout_top_p_token_offsets`` 长度 == ``response_length + 1``，
  第 i 个 response token 的核集合 = token_ids[offsets[i]:offsets[i+1]]
  （types.py:122-125 注释）；--rollout-top-p 0.95 时 loss 路径强制要求（E2 定案）；
- routing tape：``rollout_routed_experts`` 形状 = (len(tokens)-1, num_layers,
  moe_router_topk)（types.py:352-369 校验），--use-rollout-routing-replay 时消费；
- 同组（n_per_prompt 个）样本 reward 交替 0/1，保证 GRPO 组内非零方差
  （否则 advantage 全 0，量不出真实反传代价）。

用法示例（J3 32k 档）：
  python3 make_synth_rollout.py --out /root/preflight_evidence/j3/synth_32k_{rollout_id}.pt \
      --num-samples 64 --n-per-prompt 4 --total-len 32768 --num-rollouts 2 \
      --num-layers 48 --moe-topk 8 --with-routing-tape --with-top-p-tape
"""

from __future__ import annotations

import argparse
import random


def build_sample_dict(
    index: int,
    group_index: int,
    prompt_len: int,
    response_len: int,
    vocab_size: int,
    num_layers: int,
    moe_topk: int,
    num_experts: int,
    top_p_k: int,
    with_routing_tape: bool,
    with_top_p_tape: bool,
    reward: float,
    rng: random.Random,
):
    import torch

    tokens = [rng.randrange(vocab_size) for _ in range(prompt_len + response_len)]
    sample = {
        "group_index": group_index,
        "index": index,
        "rollout_id": index,  # 默认路径 rollout_id == index（types.py:99-106 注释）
        "prompt": f"synthetic-prompt-{group_index}",
        "tokens": tokens,
        "response": "synthetic-response",
        "response_length": response_len,
        "reward": reward,
        "loss_mask": [1] * response_len,
        "weight_versions": ["0"],
        "rollout_log_probs": [-0.5 - rng.random() for _ in range(response_len)],
        "status": "completed",
        "metadata": {"synthetic": True},
    }
    if with_top_p_tape:
        # 每个 response token 的核集合固定 top_p_k 个 id（含实际采出的 token）。
        ids = []
        offsets = [0]
        for i in range(response_len):
            kept = [tokens[prompt_len + i]] + [rng.randrange(vocab_size) for _ in range(top_p_k - 1)]
            ids.extend(kept)
            offsets.append(len(ids))
        sample["rollout_top_p_token_ids"] = torch.tensor(ids, dtype=torch.int32)
        sample["rollout_top_p_token_offsets"] = torch.tensor(offsets, dtype=torch.int64)
    if with_routing_tape:
        rows = len(tokens) - 1  # types.py:356 expected_rows = len(tokens) - 1
        sample["rollout_routed_experts"] = torch.randint(
            0, num_experts, (rows, num_layers, moe_topk), dtype=torch.int32
        )
    return sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="输出路径模板，须含 {rollout_id} 占位符")
    parser.add_argument("--num-samples", type=int, default=64, help="每个 rollout 的样本条数（协议 J3：64 条）")
    parser.add_argument("--n-per-prompt", type=int, default=4, help="GRPO 组大小（E2 定案 n=4）")
    parser.add_argument("--total-len", type=int, default=32768, help="单条轨迹总 token 数（prompt+response，J3 主轴 B：32k/24k）")
    parser.add_argument("--prompt-len", type=int, default=512)
    parser.add_argument("--num-rollouts", type=int, default=2, help="生成几个 rollout 文件（= 训练 step 数）")
    parser.add_argument("--vocab-size", type=int, default=151936, help="qwen3-30B-A3B.sh --vocab-size")
    parser.add_argument("--num-layers", type=int, default=48, help="qwen3-30B-A3B.sh --num-layers")
    parser.add_argument("--moe-topk", type=int, default=8, help="qwen3-30B-A3B.sh --moe-router-topk")
    parser.add_argument("--num-experts", type=int, default=128, help="qwen3-30B-A3B.sh --num-experts")
    parser.add_argument("--top-p-k", type=int, default=8, help="top-p tape 每 token 核集合大小（合成值）")
    parser.add_argument("--with-routing-tape", action="store_true")
    parser.add_argument("--with-top-p-tape", action="store_true")
    parser.add_argument("--seed", type=int, default=20260708)
    args = parser.parse_args()

    import torch

    assert "{rollout_id}" in args.out, "--out 必须包含 {rollout_id} 占位符（与 --load-debug-rollout-data 模板一致）"
    assert args.num_samples % args.n_per_prompt == 0, "num-samples 必须能被 n-per-prompt 整除（组完整性，data_source.py:206 断言）"
    response_len = args.total_len - args.prompt_len
    assert response_len > 0

    rng = random.Random(args.seed)
    for rollout_id in range(args.num_rollouts):
        samples = []
        for i in range(args.num_samples):
            group = i // args.n_per_prompt
            samples.append(
                build_sample_dict(
                    index=i,
                    group_index=group,
                    prompt_len=args.prompt_len,
                    response_len=response_len,
                    vocab_size=args.vocab_size,
                    num_layers=args.num_layers,
                    moe_topk=args.moe_topk,
                    num_experts=args.num_experts,
                    top_p_k=args.top_p_k,
                    with_routing_tape=args.with_routing_tape,
                    with_top_p_tape=args.with_top_p_tape,
                    reward=float(i % args.n_per_prompt % 2),  # 组内 0/1 交替，非零方差
                    rng=rng,
                )
            )
        path = args.out.format(rollout_id=rollout_id)
        torch.save({"rollout_id": rollout_id, "samples": samples}, path)
        total_tokens = sum(len(s["tokens"]) for s in samples)
        print(f"[make_synth_rollout] wrote {path}: {len(samples)} samples, {total_tokens} tokens")


if __name__ == "__main__":
    main()
