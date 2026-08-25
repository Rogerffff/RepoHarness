"""faithful DIS 的 miles custom loss 接线（C1′-b delta 第 2 项）。

加载方式：miles `--loss-type custom_loss --custom-loss-function-path
repoharness2.adapters.miles.faithful_dis_loss.faithful_dis_loss_function`
（integration base `miles/backends/training_utils/loss_hub/losses.py`
get_loss_function 的 "custom_loss" 分支 -> load_function 按点路径加载）。
签名 = 该文件 LossFunction Protocol：``(args, batch, logits,
sum_of_sample_mean) -> (loss, metrics)``，loss 是带梯度标量，metrics 是
detached 标量 dict。

语义权威 = `repoharness2.training.faithful_dis`（标量参考,FA-4;本模块
**不改它**,只做 torch 同构实现,ε 与分母语义常量直接 import 同源）::

    L(θ)   = -( Σ_i f(r_i)·Â_i·logπ_θ(a_i) ) / D
    r_i    = exp(logπ_θ(a_i) - logπ_rollout(a_i))
    f(x)   = x  若 1-ε_ℓ < x < 1+ε_h（开区间,log 空间判定防溢出）,否则 0

关键实现决策（与验收条款一一对应）：

- **区间外 ratio 梯度精确为零**：f(r) 权重整体由 detach 后的 log_ratio
  构造（先 detach 再 exp/比较）,区间外权重恒 0——loss 项与 d loss/d logπ_θ
  都**精确**为 0（不是数值近似小,是乘 0）,与标量参考
  `per_token_grad_logp_current = -(f(r_i)·Â_i)/D` 逐位一致。
- **ratio detach**：f(r) 是常数权重（faithful_dis.py 模块注释:RH2 显式
  算法决策,IcePop 族一致）；不 detach 变体必须另立函数名,本函数不留开关。
  ε 同理写死为预注册值（DIS_EPS_LOW/HIGH_PREREGISTERED）,消融另立名字。
- **denominator 语义显式预注册（FA-4 §1）**：``DENOMINATOR_SEMANTICS =
  DENOMINATOR_SEMANTICS_V1 = "provenance_tokens"``——D = 本 microbatch 的
  provenance（loss_mask=1）token 总数,被 DIS 拒绝的 token **留在分母**
  （梯度为零但不重归一化）。选择理由：(1) 与标量参考 v1 预注册同源 import,
  不复制字面量,两处不可能漂移；(2) 与 slime stock TIS 的 rollout_mask_sums
  口径一致,IcePop-style 对照可同分母比较；(3) 若用 accepted_tokens,拒绝率
  波动会反向缩放幸存 token 的梯度,引入与拒绝率耦合的有效学习率漂移。
  第四个入参 sum_of_sample_mean（miles 的 per-sample-mean CP 感知归约器）
  **有意不用**：它实现的是"逐样本均值再平均"口径,与预注册的全局 token
  分母不同——静默复用会改变分母语义。DP 跨卡归约与 execution 级三层归约
  （faithful_dis_loss_by_execution 参考）归硬件段接线,本函数只承诺单
  microbatch 语义,CP>1 直接 fail-closed 拒绝（见下）。
- **current logprob = support-renormalized**（rollout_sampling_mask masked
  路径）：经 miles `get_log_probs_and_entropy(rollout_sampling_mask=...)`
  计算——`build_local_sampling_mask` 产 dense bool mask,`compute_log_probs`
  masked_fill(-inf) 后 log_softmax（integration base logit_processors.py
  247-252 / math_utils._apply_sampling_mask 的同一条消费路径,不自写第二份
  softmax）。温度缩放同路径内完成（args.rollout_temperature）。
- **behavior logprob = batch["rollout_log_probs"]**,provenance =
  support-normalized（T0-B 正式分母列）：上游 sglang_rollout
  `append_sampling_metadata` 用引擎 `output_token_sampling_logprobs` 整体
  替换逐轮 logprob 后落 `Sample.rollout_log_probs`；rh2 capture 链在
  capture_wire `parse_turn_sampling_support` 做同款替换。观察/工具位
  （loss_mask=0）在两条链上都是单例支持集,其 support-normalized logprob
  恒 0。全词表 logprob 只留在 raw_response 诊断列,不进本函数。
- **target∈support 断言在 gather 之前（C2 收口）**：上游三层校验全在
  rollout 侧,loss 层没有——这里是训练端唯一防线（防传输错位/artifact
  损坏）。断言失败抛 FaithfulDisLossError,绝不静默出 -inf/NaN。
- **全零有效 token**：D=0 时 loss = 0*logits.sum()（保 autograd 图,梯度
  精确全零）,metrics 里 dis_zero_grad_step=1（FA-4:跳过 optimizer step
  的信号由训练循环消费,本函数只出信号不做决定）。

fail-closed 面（任一违反即抛错,样本不进梯度）：replay 未开启
（rollout_top_p>=1.0）、缺 rollout_sampling_mask wire 字段、缺
rollout_log_probs、mask 覆盖数!=response 长度、loss_mask 非 0/1、各列
长度不一致、logp/advantage 非有限、CP>1、target∉support。
"""

from __future__ import annotations

import math
from argparse import Namespace
from collections.abc import Callable

import torch
from miles.backends.training_utils.loss_hub.logit_processors import get_log_probs_and_entropy
from miles.backends.training_utils.parallel import get_parallel_state
from miles.backends.training_utils.sampling_mask import get_rollout_sampling_masks
from miles.utils.sampling import top_p_sampling_replay_enabled

from repoharness2.training.faithful_dis import (
    DENOMINATOR_SEMANTICS_V1,
    DIS_EPS_HIGH_PREREGISTERED,
    DIS_EPS_LOW_PREREGISTERED,
)

__all__ = [
    "DENOMINATOR_SEMANTICS",
    "FaithfulDisLossError",
    "faithful_dis_loss_function",
]

# 预注册分母语义（写死,不提供运行时开关；见模块 docstring 的选择理由）。
DENOMINATOR_SEMANTICS = DENOMINATOR_SEMANTICS_V1
assert DENOMINATOR_SEMANTICS == "provenance_tokens"  # 防止上游常量被改后静默漂移

# 信任区间（开区间,log 空间;与标量参考 _trust_bounds + _token_weight 同式）
_LOG_TRUST_LOW = math.log(1.0 - DIS_EPS_LOW_PREREGISTERED)
_LOG_TRUST_HIGH = math.log(1.0 + DIS_EPS_HIGH_PREREGISTERED)


class FaithfulDisLossError(RuntimeError):
    """faithful DIS 训练端 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


def _assert_targets_in_support(sample_index: int, response_tokens: torch.Tensor, mask) -> None:
    """C2：gather 前逐 token 断言 target ∈ 其支持集。

    读 CSR 用 `RolloutSamplingMask._as_tensors()`——与上游
    train_data_conversion 的出账读法同一私有面（升 pin 时若重构,此处
    与上游同批断链,哨兵性质与 governed_buffer 的 `_inner._dynamic_filter`
    自检相同）。
    """

    resp_len = int(response_tokens.numel())
    if len(mask) != resp_len:
        raise FaithfulDisLossError(
            "sampling_mask_length_mismatch",
            f"样本 {sample_index}: mask 覆盖 {len(mask)} 个 token != response 长度 {resp_len}。",
        )
    ids, offsets = mask._as_tensors()
    lengths = (offsets[1:] - offsets[:-1]).to(torch.long)
    row = torch.repeat_interleave(torch.arange(resp_len, dtype=torch.long), lengths)
    hit = torch.zeros(resp_len, dtype=torch.bool)
    hit[row[ids.to(torch.long) == response_tokens.to(torch.long)[row]]] = True
    if not bool(hit.all()):
        bad = int((~hit).nonzero()[0].item())
        raise FaithfulDisLossError(
            "target_not_in_support",
            f"样本 {sample_index}: response 第 {bad} 个 token "
            f"{int(response_tokens[bad])} 不在其采样支持集内——引擎出站有 "
            "force-include 保证,出现此况即传输错位或数据损坏（C2,fail-closed:"
            "拒绝整个 microbatch,不静默产出 -inf logprob）。",
        )


def _cat_column(batch, key: str, response_lengths: list[int], *, detach: bool) -> torch.Tensor:
    """batch 的逐样本 [R] 列 -> 平铺 [ΣR]（长度逐样本核对,fail-closed）。"""

    column = batch.get(key)
    if column is None:
        raise FaithfulDisLossError(
            "batch_column_missing",
            f"faithful DIS 要求 batch 携带 {key}（缺失即上游装配/转换链断账）。",
        )
    tensors = []
    for i, (item, resp_len) in enumerate(zip(column, response_lengths, strict=True)):
        t = torch.as_tensor(item)
        if t.numel() != resp_len:
            raise FaithfulDisLossError(
                "batch_column_length_mismatch",
                f"样本 {i}: {key} 长度 {t.numel()} != response_length {resp_len}。",
            )
        tensors.append(t.detach() if detach else t)
    return torch.cat(tensors, dim=0)


def faithful_dis_loss_function(
    args: Namespace,
    batch,
    logits: torch.Tensor,
    sum_of_sample_mean: Callable[[torch.Tensor], torch.Tensor],
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """faithful DIS loss（miles custom loss 入口;语义见模块 docstring）。"""

    del sum_of_sample_mean  # 有意不用：分母语义预注册为全局 provenance token 数

    parallel_state = get_parallel_state()
    if parallel_state.cp.size != 1:
        raise FaithfulDisLossError(
            "cp_not_supported",
            f"faithful DIS custom loss 尚未接 CP 归约（cp.size={parallel_state.cp.size}）——"
            "分母/座标的 CP 切分语义归硬件段验证,此前 fail-closed。",
        )
    if not top_p_sampling_replay_enabled(args):
        raise FaithfulDisLossError(
            "sampling_replay_disabled",
            f"faithful DIS 要求 sampling-support replay 开启（rollout_top_p="
            f"{getattr(args, 'rollout_top_p', 1.0)} 须 <1.0）——current/behavior 两列都以"
            "支持集归一化为口径,replay 关闭时该口径不存在（T0-B）。",
        )

    response_lengths: list[int] = list(batch["response_lengths"])
    total_lengths: list[int] = list(batch["total_lengths"])
    unconcat_tokens = batch["unconcat_tokens"]

    # wire 字段缺失由 get_rollout_sampling_masks 自身 fail-closed（ValueError）
    sampling_masks = get_rollout_sampling_masks(batch)
    if len(sampling_masks) != len(unconcat_tokens):
        raise FaithfulDisLossError(
            "sampling_mask_batch_mismatch",
            f"mask 条数 {len(sampling_masks)} != 样本数 {len(unconcat_tokens)}。",
        )

    # C2：gather 前逐样本断言 target ∈ support
    for i, (tokens, resp_len, mask) in enumerate(
        zip(unconcat_tokens, response_lengths, sampling_masks, strict=True)
    ):
        response_tokens = tokens[-resp_len:] if resp_len else tokens[0:0]
        _assert_targets_in_support(i, torch.as_tensor(response_tokens), mask)

    # current logprob：support-renormalized（miles masked 消费路径,含温度缩放）
    log_probs_list = get_log_probs_and_entropy(
        logits,
        args=args,
        unconcat_tokens=unconcat_tokens,
        total_lengths=total_lengths,
        response_lengths=response_lengths,
        with_entropy=False,
        max_seq_lens=batch.get("max_seq_lens", None),
        rollout_sampling_mask=sampling_masks,
    )["log_probs"]
    for i, (lp, resp_len) in enumerate(zip(log_probs_list, response_lengths, strict=True)):
        if lp.numel() != resp_len:
            raise FaithfulDisLossError(
                "current_logprob_length_mismatch",
                f"样本 {i}: current logprob 长度 {lp.numel()} != response_length {resp_len}"
                "（CP=1 下应逐位对齐;出现说明并行切分假设被破坏）。",
            )
    current_logp = torch.cat(log_probs_list, dim=0)

    # behavior logprob：Sample.rollout_log_probs（support-normalized,T0-B）
    behavior_logp = _cat_column(batch, "rollout_log_probs", response_lengths, detach=True)
    behavior_logp = behavior_logp.to(current_logp.dtype)
    advantages = _cat_column(batch, "advantages", response_lengths, detach=True)
    advantages = advantages.to(current_logp.dtype)
    loss_masks = _cat_column(batch, "loss_masks", response_lengths, detach=True)
    if not bool(((loss_masks == 0) | (loss_masks == 1)).all()):
        raise FaithfulDisLossError(
            "loss_mask_not_binary",
            "loss_masks 只允许 0/1（provenance 语义;标量参考同禁）。",
        )
    provenance = loss_masks.to(current_logp.dtype)

    # fail-closed：任何非有限输入拒绝整个 microbatch（标量参考对 mask=0 位
    # 同样校验——掩码不豁免数据损坏检查）
    for name, tensor in (
        ("current_logp", current_logp),
        ("behavior_logp", behavior_logp),
        ("advantages", advantages),
    ):
        if not bool(torch.isfinite(tensor).all()):
            raise FaithfulDisLossError(
                "non_finite_input",
                f"{name} 含非有限值——上游事实矛盾（logp 采集/归一化损坏）,fail-closed。",
            )

    # f(r)：detach 后 log 空间判区间,区间外权重精确为 0（梯度也精确为 0）
    log_ratio = (current_logp - behavior_logp).detach()
    in_trust = (log_ratio > _LOG_TRUST_LOW) & (log_ratio < _LOG_TRUST_HIGH)
    ratio_weight = torch.where(in_trust, log_ratio, torch.zeros_like(log_ratio)).exp()
    weight = ratio_weight * in_trust.to(current_logp.dtype) * provenance

    denominator = int(provenance.sum().item())
    accepted = int((in_trust & (loss_masks == 1)).sum().item())
    rejected = denominator - accepted
    zero_grad_step = accepted == 0

    if denominator == 0:
        # 全零有效 token：保图零梯度 + 显式信号（绝不除零/静默 NaN）
        loss = logits.sum() * 0.0
    else:
        loss = -(weight * advantages * current_logp).sum() / denominator

    device = logits.device
    metrics = {
        "loss": loss.clone().detach(),
        "dis_denominator": torch.tensor(float(denominator), device=device),
        "dis_accepted_tokens": torch.tensor(float(accepted), device=device),
        "dis_rejected_tokens": torch.tensor(float(rejected), device=device),
        "dis_zero_grad_step": torch.tensor(1.0 if zero_grad_step else 0.0, device=device),
    }
    return loss, metrics
