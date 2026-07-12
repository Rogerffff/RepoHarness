"""FA-4 对拍部分：faithful DIS 的参考实现（公式 + 解析梯度 + 指标）。

出处：05 计划 FA-4。本模块是**数值参考层**——纯 Python 标量实现论文语义的
faithful DIS（SAO 论文 `docs/harness_improve/external_paper_references/pdfs/
2607.07508v1.pdf` 的 `GRPO (w/ DIS)` 目标），作为最终 Megatron custom loss
接线（FA-4 后半，GPU 环境）的逐 token 对拍权威。torch 侧同构实现见
`tests/training/test_faithful_dis.py` 的三方对拍（参考 vs 解析梯度 vs
torch autograd vs 有限差分）。

公式（预注册；per-token）::

    ratio_i  = exp(logp_current_i - logp_rollout_i)        # 视为常数（detach）
    w_i      = ratio_i        若 eps_low <= ratio_i <= eps_high
             = 0              否则（越界 token 梯度必须精确为零）
    loss     = - (1/D) * Σ_i  m_i * w_i * A_i * logp_current_i
    dL/dlogp_current_i = - m_i * w_i * A_i / D              # w_i detach 后的解析梯度

其中 m_i = provenance loss mask（不可变历史事实，FA-0 已定：算法掩码
不得改写它）；A_i = advantage（GRPO 组归一化产物，本模块不关心其来源）。

**denominator 语义预注册（D_SEMANTICS_V1）**：D = Σ_i m_i，即 provenance
mask 的 token 总数——被 DIS 拒绝的 token **留在分母中**（梯度贡献为零但
不重新归一化）。理由：与 slime stock TIS 路径的 `rollout_mask_sums` 口径
一致（codex 轮次 3 #7 核实：stock 把超界 token 分子清零、分母不变），
使 IcePop-style 近似对照可以同分母比较；"仅按接受 token 归一化"
（accepted_tokens）作为第二实现保留用于消融，**正式链用哪个由 FA-4 接线
时对照论文原文最终定死并回写本注释**——两种实现都在，防止接插件时无意
改变有效学习率。

ε 区间预注册：eps_low=0.8 / eps_high=3.0（codex 轮次 3 引 SAO 论文
coding-agent 配置；FA-4 接线时对照原文复核后定死——见 05 计划 §5）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DIS_EPS_HIGH_PREREGISTERED",
    "DIS_EPS_LOW_PREREGISTERED",
    "DenominatorSemantics",
    "DisLossResult",
    "DisTokenRecord",
    "faithful_dis_loss",
    "reject_ratio_by_length_bucket",
]

DIS_EPS_LOW_PREREGISTERED = 0.8
DIS_EPS_HIGH_PREREGISTERED = 3.0

DenominatorSemantics = Literal["provenance_tokens", "accepted_tokens"]
DENOMINATOR_SEMANTICS_V1: DenominatorSemantics = "provenance_tokens"


@dataclass(frozen=True)
class DisTokenRecord:
    """一个 token 的 DIS 输入事实。"""

    logp_current: float  # 当前训练策略下该 token 的 logprob（trainer forward 产物）
    logp_rollout: float  # rollout 行为策略记录的 logprob（token-faithful 采集）
    advantage: float
    provenance_mask: int  # 0/1（LossMaskSpan 语义；算法掩码不得改写它）


@dataclass(frozen=True)
class DisLossResult:
    loss: float
    per_token_weight: tuple[float, ...]  # w_i（含 mask=0 与被拒 token 的 0）
    per_token_grad_logp_current: tuple[float, ...]  # 解析梯度 dL/dlogp_current_i
    denominator: int
    accepted_token_count: int  # m_i=1 且 ratio 在区间内
    rejected_token_count: int  # m_i=1 但 ratio 越界（算法拒绝，provenance 不变）
    zero_grad_step: bool  # 全零有效 token（FA-4：跳过 optimizer step 的信号）


def faithful_dis_loss(
    tokens: list[DisTokenRecord],
    *,
    eps_low: float = DIS_EPS_LOW_PREREGISTERED,
    eps_high: float = DIS_EPS_HIGH_PREREGISTERED,
    denominator_semantics: DenominatorSemantics = DENOMINATOR_SEMANTICS_V1,
) -> DisLossResult:
    """faithful DIS 的参考 loss + 解析梯度（逐 token）。

    fail-closed：logp 非有限、mask 非 0/1、eps 区间非法都直接抛错——
    参考实现的职责是把语义钉死，不是容错。
    """

    if not tokens:
        raise ValueError("faithful_dis_loss: 空 token 列表。")
    if not (0.0 < eps_low <= 1.0 <= eps_high) or not math.isfinite(eps_low + eps_high):
        raise ValueError(
            f"eps 区间非法：[{eps_low}, {eps_high}]——须 0 < eps_low <= 1 <= eps_high"
            "（ratio=1 即完全 on-policy，必须在信任区间内）。"
        )

    weights: list[float] = []
    accepted = 0
    rejected = 0
    provenance_count = 0
    for i, tok in enumerate(tokens):
        if tok.provenance_mask not in (0, 1):
            raise ValueError(f"token {i}: provenance_mask={tok.provenance_mask} 非 0/1。")
        if not (math.isfinite(tok.logp_current) and math.isfinite(tok.logp_rollout)):
            raise ValueError(f"token {i}: logp 非有限值。")
        if tok.provenance_mask == 0:
            weights.append(0.0)
            continue
        provenance_count += 1
        ratio = math.exp(tok.logp_current - tok.logp_rollout)
        if eps_low <= ratio <= eps_high:
            weights.append(ratio)
            accepted += 1
        else:
            weights.append(0.0)
            rejected += 1

    if denominator_semantics == "provenance_tokens":
        denominator = provenance_count
    elif denominator_semantics == "accepted_tokens":
        denominator = accepted
    else:  # pragma: no cover - Literal 已限定
        raise ValueError(f"未知 denominator 语义：{denominator_semantics}")

    if denominator == 0:
        # 全零有效 token：loss/梯度全零 + 显式信号（FA-4：跳过 optimizer step，
        # 计数并告警；绝不除零、绝不静默产出 NaN）。
        return DisLossResult(
            loss=0.0,
            per_token_weight=tuple(weights),
            per_token_grad_logp_current=tuple(0.0 for _ in tokens),
            denominator=0,
            accepted_token_count=0,
            rejected_token_count=rejected,
            zero_grad_step=True,
        )

    loss = -sum(
        w * tok.advantage * tok.logp_current for w, tok in zip(weights, tokens)
    ) / denominator
    grads = tuple(-(w * tok.advantage) / denominator for w, tok in zip(weights, tokens))
    return DisLossResult(
        loss=loss,
        per_token_weight=tuple(weights),
        per_token_grad_logp_current=grads,
        denominator=denominator,
        accepted_token_count=accepted,
        rejected_token_count=rejected,
        zero_grad_step=accepted == 0,
    )


def reject_ratio_by_length_bucket(
    trajectories: list[list[DisTokenRecord]],
    *,
    bucket_edges: tuple[int, ...] = (2048, 8192, 32768),
    eps_low: float = DIS_EPS_LOW_PREREGISTERED,
    eps_high: float = DIS_EPS_HIGH_PREREGISTERED,
) -> dict[str, tuple[int, int]]:
    """按轨迹长度分桶的 DIS 拒绝率原始计数（FA-4 指标：长度相关拒绝偏差监测）。

    返回 {bucket_label: (rejected, provenance_total)}——比率由消费方算，
    这里只出原始计数（避免小桶除零与精度争议）。桶边界按轨迹 provenance
    token 总数划分，默认边界为预注册值（FA-5 校准）。
    """

    labels = []
    lo = 0
    for edge in bucket_edges:
        labels.append(f"({lo},{edge}]")
        lo = edge
    labels.append(f"({lo},inf)")

    counts: dict[str, list[int]] = {label: [0, 0] for label in labels}
    for trajectory in trajectories:
        provenance = [t for t in trajectory if t.provenance_mask == 1]
        length = len(provenance)
        bucket = labels[-1]
        lo = 0
        for edge, label in zip(bucket_edges, labels):
            if lo < length <= edge:
                bucket = label
                break
            lo = edge
        rejected = sum(
            1
            for t in provenance
            if not (eps_low <= math.exp(t.logp_current - t.logp_rollout) <= eps_high)
        )
        counts[bucket][0] += rejected
        counts[bucket][1] += length
    return {label: (r, total) for label, (r, total) in counts.items()}
