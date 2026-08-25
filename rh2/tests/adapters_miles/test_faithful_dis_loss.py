"""C1′-b delta 测试 (d)：faithful DIS custom loss（miles 接线形态）。

对拍权威 = `repoharness2.training.faithful_dis`（标量参考,不动）。用例数据
风格沿 `tests/training/test_faithful_dis.py`：小 vocab、手工指定信任区间
内/外的 log-ratio、逐位断言。

覆盖面：
- 与标量参考同输入逐位一致（loss 标量 + 经链式法则展开的逐 logits 行梯度）;
- 区间外 token 梯度**精确**为零（backward 后逐位 == 0 断言,非 allclose）;
- target∉support 即炸（C2,gather 前）;
- denominator 语义按预注册断言（provenance_tokens,与标量权威常量同源）;
- 全零有效 token 保图零梯度 + zero_grad_step 信号;
- fail-closed 面：replay 关闭/缺 wire 字段/缺 rollout_log_probs/非有限输入/
  loss_mask 非 0/1/mask 长度错位。

单进程 CPU 形态：ParallelState 全 trivial group（上游 loss_test_utils
make_parallel_state 同款）,true_on_policy_mode=True 走全词表 log_softmax
路径（无 megatron 依赖）。
"""

from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

VOCAB = 17


def _boom_reducer(_t):
    raise AssertionError("sum_of_sample_mean 不应被调用——分母语义是预注册的全局 token 数")


@pytest.fixture()
def dis(world):
    """被测模块 + 单进程 ParallelState（trivial groups,上游 fast 测试同款）。"""

    import torch

    from miles.backends.training_utils.parallel import ParallelState, set_parallel_state
    from miles.utils.ft_utils.process_group_utils import GroupInfo

    from repoharness2.adapters.miles import faithful_dis_loss as module

    def trivial() -> GroupInfo:
        return GroupInfo(rank=0, size=1, group=None)

    def mk_state(cp_size: int = 1) -> ParallelState:
        cp = GroupInfo(rank=0, size=cp_size, group=None)
        state = ParallelState(
            intra_dp=trivial(),
            intra_dp_cp=trivial(),
            cp=cp,
            tp=trivial(),
            pp=trivial(),
            ep=trivial(),
            etp=trivial(),
            indep_dp=trivial(),
            is_pp_last_stage=True,
        )
        set_parallel_state(state)
        return state

    mk_state()
    return SimpleNamespace(module=module, torch=torch, mk_state=mk_state)


def _mk_args(**over):
    base = dict(
        qkv_format="thd",
        rollout_temperature=1.0,
        true_on_policy_mode=True,
        log_probs_chunk_size=-1,
        allgather_cp=False,
        rollout_top_p=0.8,
        rollout_top_k=VOCAB,
        vocab_size=VOCAB,
        bf16=False,
        fp16=False,
    )
    base.update(over)
    return Namespace(**base)


# 固定两样本形状（手工数据,不依赖随机支持集）：
#   s0: prompt [1,2,3], resp [4,5,6,7], loss_mask [1,1,0,1]（位 2 = 观察位单例）
#   s1: prompt [1,2],   resp [8,9,10],  loss_mask [1,1,1]
_S0_SUPPORTS = [[4, 9, 10], [5, 2], [6], [7, 8]]
_S1_SUPPORTS = [[8, 3], [9], [10, 11, 12]]
# 逐 token 目标 log-ratio（信任区间 (0.2,4.0) 开区间 -> log 界约 (-1.609,1.386)）：
# s0: in / out-high / (观察位,in 但 mask=0) / out-low;s1: in / in / out-high
_S0_TARGET_LOG_RATIO = [0.0, 1.5, 0.3, -2.0]
_S1_TARGET_LOG_RATIO = [0.5, -1.0, 2.0]
_S0_ADV = [1.0, -0.5, 2.0, 0.7]
_S1_ADV = [0.3, -1.2, 0.9]


def _csr(supports):
    ids: list[int] = []
    offsets = [0]
    for support in supports:
        ids.extend(support)
        offsets.append(len(ids))
    return ids, offsets


def _mk_case(torch, *, seed=7):
    g = torch.Generator().manual_seed(seed)
    tokens0 = torch.tensor([1, 2, 3, 4, 5, 6, 7], dtype=torch.long)
    tokens1 = torch.tensor([1, 2, 8, 9, 10], dtype=torch.long)
    total_lengths = [7, 5]
    response_lengths = [4, 3]
    logits = torch.randn(1, sum(total_lengths), VOCAB, generator=g, dtype=torch.float64)
    ids0, offsets0 = _csr(_S0_SUPPORTS)
    ids1, offsets1 = _csr(_S1_SUPPORTS)
    batch = {
        "unconcat_tokens": [tokens0, tokens1],
        "total_lengths": total_lengths,
        "response_lengths": response_lengths,
        "loss_masks": [
            torch.tensor([1, 1, 0, 1], dtype=torch.long),
            torch.tensor([1, 1, 1], dtype=torch.long),
        ],
        "advantages": [
            torch.tensor(_S0_ADV, dtype=torch.float64),
            torch.tensor(_S1_ADV, dtype=torch.float64),
        ],
        "rollout_sampling_mask_ids": [ids0, ids1],
        "rollout_sampling_mask_offsets": [offsets0, offsets1],
    }
    return batch, logits


def _fill_behavior_from_current(torch, dis, args, batch, logits):
    """behavior = current − 目标 log-ratio（先用被测同路径 no_grad 算 current）。"""

    from miles.backends.training_utils.loss_hub.logit_processors import (
        get_log_probs_and_entropy,
    )
    from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

    with torch.no_grad():
        current = get_log_probs_and_entropy(
            logits,
            args=args,
            unconcat_tokens=batch["unconcat_tokens"],
            total_lengths=batch["total_lengths"],
            response_lengths=batch["response_lengths"],
            with_entropy=False,
            rollout_sampling_mask=get_rollout_sampling_masks(batch),
        )["log_probs"]
    targets = [
        torch.tensor(_S0_TARGET_LOG_RATIO, dtype=torch.float64),
        torch.tensor(_S1_TARGET_LOG_RATIO, dtype=torch.float64),
    ]
    batch["rollout_log_probs"] = [c - t for c, t in zip(current, targets)]
    return [c.clone() for c in current]


def _scalar_reference(dis, current_list, batch):
    from repoharness2.training.faithful_dis import DisTokenRecord, faithful_dis_loss

    records = []
    for current, behavior, adv, mask in zip(
        current_list, batch["rollout_log_probs"], batch["advantages"], batch["loss_masks"]
    ):
        for c, b, a, m in zip(
            current.tolist(), behavior.tolist(), adv.tolist(), mask.tolist()
        ):
            records.append(
                DisTokenRecord(
                    logp_current=c, logp_rollout=b, advantage=a, provenance_mask=int(m)
                )
            )
    return records, faithful_dis_loss(records)


# ---------------------------------------------------------------------------
# 与标量参考逐位一致 + denominator 预注册
# ---------------------------------------------------------------------------


def test_denominator_semantics_preregistered(dis):
    from repoharness2.training.faithful_dis import DENOMINATOR_SEMANTICS_V1

    assert dis.module.DENOMINATOR_SEMANTICS == "provenance_tokens"
    assert dis.module.DENOMINATOR_SEMANTICS is DENOMINATOR_SEMANTICS_V1  # 同源,非复制


def test_loss_matches_scalar_reference(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    current_list = _fill_behavior_from_current(torch, dis, args, batch, logits)
    _, ref = _scalar_reference(dis, current_list, batch)

    loss, metrics = dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)

    assert loss.item() == pytest.approx(ref.loss, rel=1e-9)
    # denominator = provenance token 数（6）而非 accepted 数（3）——预注册数值断言
    assert metrics["dis_denominator"].item() == ref.denominator == 6
    assert metrics["dis_accepted_tokens"].item() == ref.accepted_token_count == 3
    assert metrics["dis_rejected_tokens"].item() == ref.rejected_token_count == 3
    assert metrics["dis_zero_grad_step"].item() == 0.0
    assert metrics["loss"].item() == pytest.approx(ref.loss, rel=1e-9)


def test_per_token_grads_match_scalar_reference_and_rejected_exactly_zero(dis):
    """逐位梯度对拍：dL/dlogits 行 = g_p·(onehot − softmax_masked),g_p 取标量
    参考 per_token_grad_logp_current;区间外/mask=0 行 **精确** == 0。"""

    torch = dis.torch
    args = _mk_args()
    batch, logits_data = _mk_case(torch)
    logits = logits_data.clone().requires_grad_(True)
    current_list = _fill_behavior_from_current(torch, dis, args, batch, logits_data)
    records, ref = _scalar_reference(dis, current_list, batch)

    loss, _ = dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    loss.backward()
    grad = logits.grad[0]  # [T, V]

    # thd/cp=1 行座标：样本 i 的 response 位 p -> 行 cum_total + total_i - resp_i - 1 + p
    supports_all = [_S0_SUPPORTS, _S1_SUPPORTS]
    flat = 0
    cum = 0
    rejected_rows = 0
    for i, (tokens, total, resp) in enumerate(
        zip(batch["unconcat_tokens"], batch["total_lengths"], batch["response_lengths"])
    ):
        base_row = cum + total - resp - 1
        for p in range(resp):
            row = base_row + p
            g_p = ref.per_token_grad_logp_current[flat]
            target = int(tokens[total - resp + p])
            support = torch.zeros(VOCAB, dtype=torch.bool)
            support[torch.tensor(supports_all[i][p])] = True
            masked = logits_data[0, row].masked_fill(~support, float("-inf"))
            probs = torch.softmax(masked, dim=-1)
            onehot = torch.zeros(VOCAB, dtype=torch.float64)
            onehot[target] = 1.0
            expected = g_p * (onehot - probs)
            assert torch.allclose(grad[row], expected, atol=1e-12), f"样本{i} 位{p}"
            if ref.per_token_weight[flat] == 0.0:
                # 区间外 / mask=0：整行梯度精确为零（乘 0,不是数值近似小）
                assert bool((grad[row] == 0.0).all()), f"样本{i} 位{p} 应精确零梯度"
                rejected_rows += 1
            elif len(supports_all[i][p]) > 1:
                assert bool(grad[row].abs().sum() > 0)
            else:
                # 单例支持集（s1 位 1）：renormalized logprob 恒为常数 0,对
                # logits 的梯度**恰为零**（onehot == softmax_masked）——被
                # 接受不代表有梯度,这是 support-renorm 语义的正确行为
                assert bool((grad[row] == 0.0).all())
            flat += 1
        # prompt 行不进 loss,梯度应全零
        for row in range(cum, base_row):
            assert bool((grad[row] == 0.0).all())
        cum += total
    assert rejected_rows == 4  # 3 个区间外 provenance 位 + 1 个观察位


# ---------------------------------------------------------------------------
# C2：target∈support gather 前断言
# ---------------------------------------------------------------------------


def test_target_not_in_support_raises_before_gather(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    # 破坏 s0 位 1 的支持集：把 target 5 换掉（模拟传输错位/artifact 损坏）
    bad_supports = [list(s) for s in _S0_SUPPORTS]
    bad_supports[1] = [2, 3]
    ids, offsets = _csr(bad_supports)
    batch["rollout_sampling_mask_ids"][0] = ids
    batch["rollout_sampling_mask_offsets"][0] = offsets

    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "target_not_in_support"


# ---------------------------------------------------------------------------
# 全零有效 token / fail-closed 面
# ---------------------------------------------------------------------------


def test_zero_denominator_keeps_graph_and_signals(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits_data = _mk_case(torch)
    logits = logits_data.clone().requires_grad_(True)
    _fill_behavior_from_current(torch, dis, args, batch, logits_data)
    batch["loss_masks"] = [torch.zeros_like(m) for m in batch["loss_masks"]]

    loss, metrics = dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert loss.item() == 0.0
    loss.backward()  # 保图：backward 可走,梯度精确全零
    assert bool((logits.grad == 0.0).all())
    assert metrics["dis_denominator"].item() == 0.0
    assert metrics["dis_zero_grad_step"].item() == 1.0


def test_replay_disabled_rejected(dis):
    torch = dis.torch
    args = _mk_args(rollout_top_p=1.0)
    batch, logits = _mk_case(torch)
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "sampling_replay_disabled"


def test_missing_wire_fields_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    del batch["rollout_sampling_mask_ids"]
    with pytest.raises(ValueError):  # miles get_rollout_sampling_masks 自身 fail-closed
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)


def test_missing_rollout_log_probs_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)  # 不填 rollout_log_probs
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "batch_column_missing"


def test_non_finite_behavior_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    batch["rollout_log_probs"][0][1] = float("inf")
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "non_finite_input"


def test_loss_mask_not_binary_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    batch["loss_masks"][0] = torch.tensor([1, 2, 0, 1], dtype=torch.long)
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "loss_mask_not_binary"


def test_mask_length_mismatch_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    ids, offsets = _csr(_S0_SUPPORTS[:3])  # 只盖 3 个 token,response 是 4
    batch["rollout_sampling_mask_ids"][0] = ids
    batch["rollout_sampling_mask_offsets"][0] = offsets
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "sampling_mask_length_mismatch"


def test_cp_not_supported_fail_closed(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    dis.mk_state(cp_size=2)
    try:
        with pytest.raises(dis.module.FaithfulDisLossError) as exc:
            dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
        assert exc.value.reason_code == "cp_not_supported"
    finally:
        dis.mk_state(cp_size=1)
