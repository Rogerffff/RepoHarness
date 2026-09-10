"""C1′-b delta 测试 (d)：faithful DIS custom loss（miles 接线形态,R6-ext B4/B5/B6 修订）。

对拍权威 = `repoharness2.training.faithful_dis` 的
``faithful_dis_loss_by_execution``（标量参考,不动;B4 后归约层次 = branch
分子 → execution provenance 分母 → batch execution 等权）。用例数据风格沿
`tests/training/test_faithful_dis.py`：小 vocab、手工指定信任区间内/外的
log-ratio、逐位断言。

归约对拍口径（单 microbatch 情形）：被测函数把逐 token 分子交给 miles
``sum_of_sample_mean``（``rollout_mask_sums`` 作 per-execution 分母）,返回
的是 execution **部分和** Σ_e loss_e;÷N_exec 的 execution 等权在 miles
dispatcher 层（``num_rollouts`` 缩放）——因此这里断言
``loss == Σ per_execution_loss``、逐 token 梯度 = 权威梯度 × N_exec。完整
dispatcher/megatron 缩放链的对拍见 test_train_seam_metamorphic.py。

覆盖面：
- 与 by_execution 权威同输入一致（loss 标量 + 经链式法则展开的逐 logits 行梯度）;
- 区间外 token 梯度**精确**为零（backward 后逐位 == 0 断言,非 allclose）;
- target∉support 即炸（C2,gather 前;B5:检查在 CPU 侧完成,加速器张量照常工作）;
- denominator 语义按预注册断言（provenance_tokens,与标量权威常量同源）;
- accepted=0 → **零贡献 microbatch,不抛异常**（F2,取代 B6 fail-stop）：
  记 dis_zero_contribution_microbatch=1,返回带 autograd 图的精确零 loss,
  backward 后逐位梯度精确为零;全局零信号判定归 miles train_one_step 的
  optimizer-step 边界（见 test_train_seam_metamorphic.py 的 F2 区段）;
- fail-closed 面：replay 关闭/calculate_per_token_loss/缺 wire 字段/缺
  rollout_log_probs/缺或矛盾 rollout_mask_sums/非有限输入/loss_mask 非 0/1/
  mask 长度错位——数据损坏类**不因 F2 降级**,仍然 fail-stop。

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
    """fail-closed 用例专用：所有拒绝路径必须在调用 reducer 之前抛出。"""
    raise AssertionError("fail-closed 路径不应触达 sum_of_sample_mean")


def _mk_reducer(torch, batch, *, calculate_per_token_loss=False):
    """真 reducer：miles dispatcher 同款构造（denominators=rollout_mask_sums）。"""
    from miles.backends.training_utils.cp_utils import get_sum_of_sample_mean

    return get_sum_of_sample_mean(
        list(batch["total_lengths"]),
        list(batch["response_lengths"]),
        batch["loss_masks"],
        calculate_per_token_loss,
        "thd",
        batch.get("max_seq_lens", None),
        denominators=batch.get("rollout_mask_sums", None),
    )


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
        # 两样本各自成 execution（e0/e1）;单 microbatch 内 sibling 都在场,
        # rollout_mask_sums = 各 execution 的 provenance 总数（3/3）
        "rollout_mask_sums": torch.tensor([3.0, 3.0], dtype=torch.float32),
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


def _execution_reference(dis, current_list, batch):
    """标量权威：faithful_dis_loss_by_execution（每样本一个 execution e{i}）。"""
    from repoharness2.training.faithful_dis import (
        DisTokenRecord,
        faithful_dis_loss_by_execution,
    )

    executions = {}
    for i, (current, behavior, adv, mask) in enumerate(
        zip(current_list, batch["rollout_log_probs"], batch["advantages"], batch["loss_masks"])
    ):
        executions[f"e{i}"] = [
            DisTokenRecord(logp_current=c, logp_rollout=b, advantage=a, provenance_mask=int(m))
            for c, b, a, m in zip(current.tolist(), behavior.tolist(), adv.tolist(), mask.tolist())
        ]
    return executions, faithful_dis_loss_by_execution(executions)


# ---------------------------------------------------------------------------
# 与 by_execution 权威一致 + denominator 预注册
# ---------------------------------------------------------------------------


def test_denominator_semantics_preregistered(dis):
    from repoharness2.training.faithful_dis import DENOMINATOR_SEMANTICS_V1

    assert dis.module.DENOMINATOR_SEMANTICS == "provenance_tokens"
    assert dis.module.DENOMINATOR_SEMANTICS is DENOMINATOR_SEMANTICS_V1  # 同源,非复制


def test_loss_matches_execution_reference(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    current_list = _fill_behavior_from_current(torch, dis, args, batch, logits)
    _, ref = _execution_reference(dis, current_list, batch)

    loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )

    # 单 microbatch：函数返回 execution 部分和 Σ_e loss_e;权威 loss = Σ/N
    partial_sum = sum(ref.per_execution_loss.values())
    assert loss.item() == pytest.approx(partial_sum, rel=1e-9)
    assert loss.item() == pytest.approx(ref.loss * ref.execution_count, rel=1e-9)
    assert ref.per_execution_denominator == {"e0": 3, "e1": 3}  # provenance 分母预注册数值
    assert metrics["dis_microbatch_provenance_tokens"].item() == 6
    assert metrics["dis_accepted_tokens"].item() == 3
    assert metrics["dis_rejected_tokens"].item() == 3
    assert metrics["dis_zero_contribution_microbatch"].item() == 0.0  # 正常批不计零贡献
    assert metrics["loss"].item() == pytest.approx(partial_sum, rel=1e-9)


def test_per_token_grads_match_execution_reference_and_rejected_exactly_zero(dis):
    """逐位梯度对拍：dL/dlogits 行 = g_p·(onehot − softmax_masked),g_p 取权威
    per_token_grad × N_exec（÷N_exec 的 execution 等权在 dispatcher 层）;
    区间外/mask=0 行 **精确** == 0。"""

    torch = dis.torch
    args = _mk_args()
    batch, logits_data = _mk_case(torch)
    logits = logits_data.clone().requires_grad_(True)
    current_list = _fill_behavior_from_current(torch, dis, args, batch, logits_data)
    _, ref = _execution_reference(dis, current_list, batch)

    loss, _ = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    loss.backward()
    grad = logits.grad[0]  # [T, V]

    # thd/cp=1 行座标：样本 i 的 response 位 p -> 行 cum_total + total_i - resp_i - 1 + p
    supports_all = [_S0_SUPPORTS, _S1_SUPPORTS]
    n_exec = ref.execution_count
    cum = 0
    rejected_rows = 0
    for i, (tokens, total, resp) in enumerate(
        zip(batch["unconcat_tokens"], batch["total_lengths"], batch["response_lengths"])
    ):
        base_row = cum + total - resp - 1
        for p in range(resp):
            row = base_row + p
            g_p = ref.per_token_grad_logp_current[f"e{i}"][p] * n_exec
            target = int(tokens[total - resp + p])
            support = torch.zeros(VOCAB, dtype=torch.bool)
            support[torch.tensor(supports_all[i][p])] = True
            masked = logits_data[0, row].masked_fill(~support, float("-inf"))
            probs = torch.softmax(masked, dim=-1)
            onehot = torch.zeros(VOCAB, dtype=torch.float64)
            onehot[target] = 1.0
            expected = g_p * (onehot - probs)
            assert torch.allclose(grad[row], expected, atol=1e-12), f"样本{i} 位{p}"
            # 用例里 advantage 全非零 -> 权威逐 token 梯度为 0 ⟺ f(r)=0 或 mask=0
            if g_p == 0.0:
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
# F2：accepted=0 = 零贡献 microbatch（不抛异常;带 autograd 图的精确零 loss）
# ---------------------------------------------------------------------------


def test_zero_provenance_batch_yields_connected_zero_loss(dis):
    """全 microbatch loss_mask=0：accepted=0 → 零贡献指标 + 零 loss 继续。

    注意 rollout_mask_sums 保持原值（execution 分母来自整 rollout 的
    sibling 总和,本 microbatch 恰好不含 provenance 位是合法切片形态）。
    """
    torch = dis.torch
    args = _mk_args()
    batch, logits_data = _mk_case(torch)
    logits = logits_data.clone().requires_grad_(True)
    _fill_behavior_from_current(torch, dis, args, batch, logits_data)
    batch["loss_masks"] = [torch.zeros_like(m) for m in batch["loss_masks"]]

    loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    assert loss.item() == 0.0
    assert loss.grad_fn is not None  # autograd 图连接:megatron backward 照常可调
    assert metrics["dis_accepted_tokens"].item() == 0
    assert metrics["dis_zero_contribution_microbatch"].item() == 1.0
    loss.backward()
    assert logits.grad is not None
    assert bool((logits.grad == 0.0).all())  # 贡献精确为零(乘 0),不是数值近似小


def test_all_rejected_batch_yields_connected_zero_loss(dis):
    """provenance>0 但全部落在信任区间外：accepted=0 → 零贡献继续（F2 主场景,
    原 B6 fail-stop 的翻转——per-microbatch 全拒不再有权威停机,全局判定在
    train_one_step 的 optimizer-step 边界）。"""
    torch = dis.torch
    args = _mk_args()
    batch, logits_data = _mk_case(torch)
    logits = logits_data.clone().requires_grad_(True)
    _fill_behavior_from_current(torch, dis, args, batch, logits_data)
    # behavior 整体 -10：log_ratio 全部 ≈ +10,远超信任上界 log(1+ε_h)
    batch["rollout_log_probs"] = [b - 10.0 for b in batch["rollout_log_probs"]]

    loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    assert loss.item() == 0.0
    assert loss.grad_fn is not None
    assert metrics["dis_microbatch_provenance_tokens"].item() == 6
    assert metrics["dis_accepted_tokens"].item() == 0
    assert metrics["dis_rejected_tokens"].item() == 6
    assert metrics["dis_zero_contribution_microbatch"].item() == 1.0
    loss.backward()
    assert bool((logits.grad == 0.0).all())


def test_accepted_token_with_zero_advantage_no_gradient(dis):
    """F2 规格 §7 用例 C 的指标级对拍（seam 级 SKIPPED 判定在
    test_train_seam_metamorphic.py::test_f2_case_c_*）：advantage=[-1,0,+1],
    非零 advantage 的 token 全部落在信任区间外,仅 advantage=0 的 token 在
    区间内——dis_accepted_tokens==1 > 0,但 loss 与逐位梯度**精确**为零,
    且不算零贡献 microbatch（accepted>0）。这就是"accepted>0 不能证明存在
    梯度"的反例:全局判定必须看真实累计梯度,不能用 accepted 计数做代理。"""
    torch = dis.torch
    from miles.backends.training_utils.loss_hub.logit_processors import (
        get_log_probs_and_entropy,
    )
    from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

    args = _mk_args()
    supports = [[8, 3], [9, 2], [10, 11, 12]]  # 全部多元素支持集（排除单例干扰）
    ids, offsets = _csr(supports)
    tokens = torch.tensor([1, 2, 8, 9, 10], dtype=torch.long)
    g = torch.Generator().manual_seed(11)
    logits_data = torch.randn(1, 5, VOCAB, generator=g, dtype=torch.float64)
    batch = {
        "unconcat_tokens": [tokens],
        "total_lengths": [5],
        "response_lengths": [3],
        "loss_masks": [torch.tensor([1, 1, 1], dtype=torch.long)],
        "advantages": [torch.tensor([-1.0, 0.0, 1.0], dtype=torch.float64)],
        "rollout_sampling_mask_ids": [ids],
        "rollout_sampling_mask_offsets": [offsets],
        "rollout_mask_sums": torch.tensor([3.0], dtype=torch.float32),
    }
    with torch.no_grad():
        current = get_log_probs_and_entropy(
            logits_data,
            args=args,
            unconcat_tokens=[tokens],
            total_lengths=[5],
            response_lengths=[3],
            with_entropy=False,
            rollout_sampling_mask=get_rollout_sampling_masks(batch),
        )["log_probs"][0]
    # 信任区间 (0.2,4.0) 开区间 ⇔ log 界约 (-1.609,1.386)：out-high/in/out-low
    batch["rollout_log_probs"] = [current - torch.tensor([2.0, 0.0, -2.0], dtype=torch.float64)]

    logits = logits_data.clone().requires_grad_(True)
    loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    assert metrics["dis_accepted_tokens"].item() == 1  # accepted > 0
    assert metrics["dis_zero_contribution_microbatch"].item() == 0.0
    # N4（I17 纯观测）：这正是"接受 ≠ 候选信号"的形态——全部多元素支持集,唯一被接受的位 advantage=0
    assert metrics["dis_nonsingleton_provenance_tokens"].item() == 3
    assert metrics["dis_singleton_accepted_tokens"].item() == 0
    assert metrics["dis_candidate_signal_tokens"].item() == 0
    assert metrics["dis_zero_advantage_accepted_tokens"].item() == 1
    assert loss.item() == 0.0  # 但真实训练信号为零
    loss.backward()
    assert bool((logits.grad == 0.0).all())  # 逐位精确零梯度


# ---------------------------------------------------------------------------
# N4（I17/I20 纯观测,第 2 组剩余 Brief;§4.1 已批）：接受再拆开看——单例 / 候选信号 / 两侧拒绝 / 支持集分桶
# ---------------------------------------------------------------------------


def test_dis_observation_metrics_hand_computed(dis):
    """固定两样本形状的手算口径（动作位 = loss_mask=1）：
    s0: 支持集大小 [3,2,1,2]、mask [1,1,0,1]、log-ratio [in, out-high, (观察位), out-low]
    s1: 支持集大小 [2,1,3]、mask [1,1,1]、log-ratio [in, in, out-high]、advantage 全非零
    → provenance 6 = 非单例 5 + 单例 1;accepted 3 = 候选信号 2（s0 位 0、s1 位 0）+ 单例接受 1（s1 位 1）
      + 零优势接受 0;rejected 3 = 低侧 1（s0 位 3）+ 高侧 2（s0 位 1、s1 位 2）;分桶 1:1、2–3:5。"""
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    _loss, metrics = dis.module.faithful_dis_loss_function(args, batch, logits, _mk_reducer(torch, batch))
    m = {k: v.item() for k, v in metrics.items()}
    assert m["dis_nonsingleton_provenance_tokens"] == 5
    assert m["dis_singleton_accepted_tokens"] == 1
    assert m["dis_candidate_signal_tokens"] == 2
    assert m["dis_zero_advantage_accepted_tokens"] == 0
    assert m["dis_rejected_low_tokens"] == 1 and m["dis_rejected_high_tokens"] == 2
    assert (m["dis_support_size_1"], m["dis_support_size_2_3"], m["dis_support_size_4_7"],
            m["dis_support_size_8_15"], m["dis_support_size_16_plus"]) == (1, 5, 0, 0, 0)
    # 口径守恒：三分接受 = accepted;两侧拒绝 = rejected;分桶之和 = provenance;非单例 + 单例桶 = provenance
    assert (m["dis_candidate_signal_tokens"] + m["dis_singleton_accepted_tokens"]
            + m["dis_zero_advantage_accepted_tokens"]) == m["dis_accepted_tokens"] == 3
    assert m["dis_rejected_low_tokens"] + m["dis_rejected_high_tokens"] == m["dis_rejected_tokens"] == 3
    assert sum(m[k] for k in ("dis_support_size_1", "dis_support_size_2_3", "dis_support_size_4_7",
                              "dis_support_size_8_15", "dis_support_size_16_plus")) == m["dis_microbatch_provenance_tokens"] == 6
    assert m["dis_nonsingleton_provenance_tokens"] + m["dis_support_size_1"] == 6
    # 既有 oracle 不变（loss / 计数口径未被观测改动）
    assert (m["dis_microbatch_provenance_tokens"], m["dis_accepted_tokens"], m["dis_rejected_tokens"]) == (6, 3, 3)
    assert m["dis_zero_contribution_microbatch"] == 0.0


def test_support_size_buckets_partition_provenance_tokens(dis):
    """桶边界 1 / 2–3 / 4–7 / 8–15 / ≥16 各取边界值：支持集大小 [1,2,3,4,7,8,15,16]（VOCAB=17 内可构造）,
    behavior=current（全部在信任区间内 → 全部接受）,只有大小 2 的位 advantage=0。"""
    torch = dis.torch
    from miles.backends.training_utils.loss_hub.logit_processors import get_log_probs_and_entropy
    from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks

    def sup(target, size):
        return [target] + [i for i in range(VOCAB) if i != target][: size - 1]

    sizes = [1, 2, 3, 4, 7, 8, 15, 16]
    targets = [4, 5, 7, 8, 9, 10, 11, 12]
    supports = [sup(tgt, n) for tgt, n in zip(targets, sizes, strict=True)]
    assert [len(s) for s in supports] == sizes and all(len(set(s)) == len(s) for s in supports)
    ids, offsets = _csr(supports)
    tokens = torch.tensor([1, 2, *targets], dtype=torch.long)
    args = _mk_args()
    g = torch.Generator().manual_seed(5)
    logits_data = torch.randn(1, 10, VOCAB, generator=g, dtype=torch.float64)
    adv = [1.0, 0.0, -0.5, 0.7, 1.1, -0.2, 0.3, 0.9]  # 位 1（大小 2）优势为零
    batch = {
        "unconcat_tokens": [tokens],
        "total_lengths": [10],
        "response_lengths": [8],
        "loss_masks": [torch.ones(8, dtype=torch.long)],
        "advantages": [torch.tensor(adv, dtype=torch.float64)],
        "rollout_sampling_mask_ids": [ids],
        "rollout_sampling_mask_offsets": [offsets],
        "rollout_mask_sums": torch.tensor([8.0], dtype=torch.float32),
    }
    with torch.no_grad():
        current = get_log_probs_and_entropy(
            logits_data, args=args, unconcat_tokens=[tokens], total_lengths=[10], response_lengths=[8],
            with_entropy=False, rollout_sampling_mask=get_rollout_sampling_masks(batch),
        )["log_probs"][0]
    batch["rollout_log_probs"] = [current.clone()]  # log-ratio 恒 0 → 全部接受
    _loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits_data.clone().requires_grad_(True), _mk_reducer(torch, batch)
    )
    m = {k: v.item() for k, v in metrics.items()}
    assert (m["dis_microbatch_provenance_tokens"], m["dis_accepted_tokens"], m["dis_rejected_tokens"]) == (8, 8, 0)
    assert (m["dis_support_size_1"], m["dis_support_size_2_3"], m["dis_support_size_4_7"],
            m["dis_support_size_8_15"], m["dis_support_size_16_plus"]) == (1, 2, 2, 2, 1)
    assert m["dis_nonsingleton_provenance_tokens"] == 7
    assert m["dis_singleton_accepted_tokens"] == 1  # 大小 1 的位：接受但必然无梯度
    assert m["dis_zero_advantage_accepted_tokens"] == 1  # 大小 2 的位：优势为零
    assert m["dis_candidate_signal_tokens"] == 6
    assert m["dis_rejected_low_tokens"] == 0 and m["dis_rejected_high_tokens"] == 0


def test_observation_metrics_do_no_host_scalar_reads(dis):
    """R7（Codex 集成审查）：观测辅助函数不得 .item()（GPU 上每次都是一次设备同步）——计数留在设备上，
    由既有 metrics 汇合统一读取。这里记录 Tensor.item 的调用者帧，要求没有一次来自观测函数。"""
    import sys as _sys

    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    callers: list[str] = []
    original_item = torch.Tensor.item

    def tracked_item(self, *a, **kw):
        callers.append(_sys._getframe(1).f_code.co_name)
        return original_item(self, *a, **kw)

    torch.Tensor.item = tracked_item
    try:
        _loss, metrics = dis.module.faithful_dis_loss_function(args, batch, logits, _mk_reducer(torch, batch))
    finally:
        torch.Tensor.item = original_item
    assert not any(name in ("_count", "_dis_observation_metrics") for name in callers), callers
    assert metrics["dis_candidate_signal_tokens"].dtype == torch.float32 and metrics["dis_candidate_signal_tokens"].item() == 2.0


# ---------------------------------------------------------------------------
# fail-closed 面
# ---------------------------------------------------------------------------


def test_rollout_mask_sums_missing_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    del batch["rollout_mask_sums"]
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "rollout_mask_sums_missing"


def test_rollout_mask_sums_inconsistent_rejected(dis):
    """execution 分母 < 本样本自身 provenance 数 = 账目矛盾。"""
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    batch["rollout_mask_sums"] = torch.tensor([2.0, 3.0], dtype=torch.float32)  # s0 自身有 3
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "rollout_mask_sums_inconsistent"


def test_rollout_mask_sums_zero_provenance_rejected(dis):
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    batch["loss_masks"][0] = torch.zeros_like(batch["loss_masks"][0])
    batch["rollout_mask_sums"] = torch.tensor([0.0, 3.0], dtype=torch.float32)
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "execution_zero_provenance"


def test_calculate_per_token_loss_rejected(dis):
    torch = dis.torch
    args = _mk_args(calculate_per_token_loss=True)
    batch, logits = _mk_case(torch)
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "per_token_loss_not_supported"


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


def test_experimental_ft_trainer_locked_fail_closed(dis, monkeypatch):
    """B6 半收口：实验 FT trainer 旗标开启时整体拒绝（fail-stop 会被其
    catch+retry(30)/部分失败继续的语义吞掉,见 faithful_dis_loss docstring）。

    旗标与 miles placement_group 选型同源：MILES_EXPERIMENTAL_FT_TRAINER
    经 enable_experimental_ft_trainer() 读取（"1"/"true"/"on"/"yes" 均真）。
    """
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    monkeypatch.setenv("MILES_EXPERIMENTAL_FT_TRAINER", "1")
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "experimental_ft_trainer_locked"

    # 旗标关掉（缺省态）同一 batch 正常出 loss——锁只针对 FT trainer
    monkeypatch.delenv("MILES_EXPERIMENTAL_FT_TRAINER")
    loss, _metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    assert bool(torch.isfinite(loss))


def test_cp1_shaped_batch_under_cp2_rejected_before_reducer(dis):
    """W9 后的语义继承（原 test_cp_not_supported_fail_closed,oracle 改动按 T1 报告,
    见 miles_spike/wave1/w9_report.md）：cp.size=2 声明下送入 CP=1 形态的 batch
    不再有笼统的 cp_not_supported,但仍在触达 reducer 之前拒绝（缺 get_batch 的
    本 rank token 流,无法证明 logits 布局是本 rank 分片）——绝不按 CP=1 口径静默
    计算。CP=2 的真实切分语义见 test_w9_cp_faithful_dis.py。"""
    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    dis.mk_state(cp_size=2)
    try:
        with pytest.raises(dis.module.FaithfulDisLossError) as exc:
            dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
        assert exc.value.reason_code == "cp_token_stream_missing"
    finally:
        dis.mk_state(cp_size=1)


# ---------------------------------------------------------------------------
# B5：target∈support 检查的设备形状（CSR 恒在 CPU,tokens 在加速器上）
# ---------------------------------------------------------------------------


def _mps_available():
    import torch

    return torch.backends.mps.is_available()


def test_assert_targets_in_support_accepts_cpu_and_accelerator(dis):
    """单元级：合法 target 通过、损坏 target 抛结构化错——CPU 与（若可用）MPS
    两种 response-token 设备都走同一条 CPU 侧检查路径。"""
    torch = dis.torch
    from miles.utils.sampling_mask import RolloutSamplingMask

    ids, offsets = _csr(_S0_SUPPORTS)
    mask = RolloutSamplingMask(ids=ids, offsets=offsets)
    good = torch.tensor([4, 5, 6, 7], dtype=torch.long)
    bad = torch.tensor([4, 3, 6, 7], dtype=torch.long)  # 位 1 的 target 3 ∉ 支持集 {5,2}

    devices = ["cpu"] + (["mps"] if _mps_available() else [])
    for device in devices:
        dis.module._assert_targets_in_support(0, good.to(device), mask)  # 不抛
        with pytest.raises(dis.module.FaithfulDisLossError) as exc:
            dis.module._assert_targets_in_support(0, bad.to(device), mask)
        assert exc.value.reason_code == "target_not_in_support", device


@pytest.mark.skipif(not _mps_available(), reason="需要 MPS 设备复现跨设备布局")
def test_full_loss_on_accelerator_device_layout(dis):
    """加速器形状（B5 验收）：批内张量列在 MPS（真实 GPU 链路中 get_rollout_data
    已把各列搬上训练设备）,sampling mask wire 仍是 CPU CSR——合法 target 出有限
    loss+可反传;损坏 target 抛结构化 target_not_in_support。MPS 无 float64,用
    float32（数值口径不参与断言,只验设备布局与错误路径）。"""
    torch = dis.torch
    args = _mk_args()
    batch, logits64 = _mk_case(torch)
    current_list = _fill_behavior_from_current(torch, dis, args, batch, logits64)
    del current_list

    device = torch.device("mps")
    logits = logits64.to(device=device, dtype=torch.float32).requires_grad_(True)
    batch["unconcat_tokens"] = [t.to(device) for t in batch["unconcat_tokens"]]
    for key in ("loss_masks", "advantages", "rollout_log_probs"):
        batch[key] = [torch.as_tensor(v).to(device=device, dtype=torch.float32) for v in batch[key]]
    batch["loss_masks"] = [m.to(torch.int32) for m in batch["loss_masks"]]
    batch["rollout_mask_sums"] = batch["rollout_mask_sums"].to(device)

    loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    assert loss.device.type == "mps"
    assert bool(torch.isfinite(loss).item())
    loss.backward()
    assert logits.grad is not None and bool(torch.isfinite(logits.grad).all())

    # 损坏 s0 位 1 的支持集 -> 结构化 fail-closed（跨设备不再是 RuntimeError）
    bad_supports = [list(s) for s in _S0_SUPPORTS]
    bad_supports[1] = [2, 3]
    ids, offsets = _csr(bad_supports)
    batch["rollout_sampling_mask_ids"][0] = ids
    batch["rollout_sampling_mask_offsets"][0] = offsets
    with pytest.raises(dis.module.FaithfulDisLossError) as exc:
        dis.module.faithful_dis_loss_function(args, batch, logits, _boom_reducer)
    assert exc.value.reason_code == "target_not_in_support"


# ---------------------------------------------------------------------------
# 租前完整审查 PR-P0-8：逐样本 accepted-token 事实（正控归因事件）
# ---------------------------------------------------------------------------


@pytest.mark.integration_base
def test_sample_dis_accounting_event_per_sample_counts(dis, tmp_path, monkeypatch):
    """loss 在事件层开启且 batch 携带 sample_indices 时，发射逐样本
    sample_dis_accounting：accepted = in_trust ∧ provenance 逐样本切片计数。
    固定数据的预期：s0 只有位 0 是 in-trust 且 mask=1（位 2 in 但 mask=0）
    → accepted=1/provenance=3；s1 位 0、1 in → accepted=2/provenance=3。
    与 step 级 metrics（accepted 总数 3）构成同一事实的两个粒度。"""
    import json

    from miles.utils import rh2_event_log

    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    # 聚焦修复批 #1：fan-out 两叶可共享 sample_index，(index, leaf_ordinal)
    # 才是唯一叶身份——entries 必须逐样本携带 leaf_ordinal（wire 列缺失时为
    # None，judge 侧 fail-closed）。这里模拟同 index 双叶（41,0)/(41,1)。
    batch["sample_indices"] = [41, 41]
    batch["leaf_ordinals"] = [0, 1]
    events_dir = tmp_path / "events"
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(events_dir))

    _loss, metrics = dis.module.faithful_dis_loss_function(
        args, batch, logits, _mk_reducer(torch, batch)
    )
    assert metrics["dis_accepted_tokens"].item() == 3

    [path] = list(events_dir.glob("rh2_events_*.jsonl"))
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    [event] = [r for r in rows if r["event"] == "sample_dis_accounting"]
    assert event["entries"] == [
        {"sample_index": 41, "leaf_ordinal": 0, "accepted_tokens": 1, "provenance_tokens": 3},
        {"sample_index": 41, "leaf_ordinal": 1, "accepted_tokens": 2, "provenance_tokens": 3},
    ]


@pytest.mark.integration_base
def test_sample_dis_accounting_silent_without_sample_indices(dis, tmp_path, monkeypatch):
    """batch 无 sample_indices（旧树/单元构造）时不发射、不影响 loss 数值。"""
    from miles.utils import rh2_event_log

    torch = dis.torch
    args = _mk_args()
    batch, logits = _mk_case(torch)
    _fill_behavior_from_current(torch, dis, args, batch, logits)
    events_dir = tmp_path / "events"
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(events_dir))
    dis.module.faithful_dis_loss_function(args, batch, logits, _mk_reducer(torch, batch))
    assert not events_dir.exists() or not list(events_dir.glob("rh2_events_*.jsonl"))
