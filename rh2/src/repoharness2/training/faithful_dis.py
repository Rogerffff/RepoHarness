"""FA-4 对拍部分：faithful DIS 的参考实现（公式 + 解析梯度 + 归约层次 + 指标）。

出处：05 计划 FA-4。本模块是**数值参考层**——纯 Python 标量实现 SAO 论文
（`docs/harness_improve/external_paper_references/pdfs/2607.07508v1.pdf`）
§3.1 的 DIS 目标，作为最终 Megatron custom loss 接线（FA-4 后半，GPU 环境）
的逐 token 对拍权威。torch 侧同构实现见 `tests/training/test_faithful_dis.py`。

公式（论文 p.4 原文核实，2026-07-12 勘误——此前误读为直接 ratio 边界闭区间，
codex FA-3/4 审查纠正）::

    L(θ)   = Ê_t[ f(r_t; ε_ℓ, ε_h) · Â_t · log π_θ(a_t|s_t) ]     (论文式 1)
    r_t    = exp(log π_θ − log π_rollout)                          (论文式 2)
    f(x)   = x   若 1 − ε_ℓ < x < 1 + ε_h，否则 0                  (论文式 3)

    coding agent 配置 ε_low=0.8, ε_high=3.0 → 信任区间 (0.2, 4.0)；
    TIR math 配置 ε_low=0.3, ε_high=5.0 → (0.7, 6.0)（论文 §4.1，留档对照）。

**区间口径注**：论文正文写 "[1−ε_ℓ, 1+ε_h]"（闭括号）而式 3 用严格不等号
——以正式定义（式 3，开区间）为准；边界是零测度事件，语义差异只在对拍
测试可见，预注册跟公式走并留此注。

**detach 是 RH2 显式算法决策**（论文未写 stop-gradient）：f(r_t) 依赖 θ，
若不阻断梯度会引入 f'(r)·∂r/∂θ·Â·logπ 项。本参考与 IcePop 族实现一致，
把 f(r) 视为常数权重（torch 侧 `ratio.detach()`）；接线时若要消融
"不 detach" 变体必须另立名字，不得混用。

**溢出防护**：阈值判断在 log-ratio 空间完成（log(0.2) < Δlogp < log(4.0)），
只对已确认在区间内的值执行 exp——有限但巨大的 logp 差不会溢出。

**denominator 语义预注册（v1 = provenance_tokens）**：D = provenance mask
的 token 总数，被 DIS 拒绝的 token 留在分母（梯度为零但不重归一化）——
与 slime stock TIS 的 `rollout_mask_sums` 口径一致，使 IcePop-style 对照
可同分母比较；`accepted_tokens` 第二档保留用于消融。**接线时对照实测最终
定死并回写本注释。**

**归约层次（codex FA-3/4 审查 #4）**：`faithful_dis_loss` 是单分母的平铺
参考（对应"全局 token mean"reducer）；`faithful_dis_loss_by_execution`
实现三层归约——branch 分子 → RolloutExecution 共享分母（消费 FA-3 的
rollout_loss_denominator 口径）→ batch 按 execution 等权平均。branch 怎么
切不改变结果（split invariance 测试钉死），DP 分区按 execution 数加权可
无损重组（partition invariance 测试钉死）。CP/VPP 维度的分布式归约留接线
期在真实并行环境验证。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DIS_EPS_HIGH_PREREGISTERED",
    "DIS_EPS_LOW_PREREGISTERED",
    "DIS_TRUST_HIGH",
    "DIS_TRUST_LOW",
    "DenominatorSemantics",
    "DisLossResult",
    "DisTokenRecord",
    "ExecutionDisResult",
    "faithful_dis_loss",
    "faithful_dis_loss_by_execution",
    "reject_ratio_by_length_bucket",
]

# 论文 §4.1 coding agent 配置（参数化 = 式 3 的 ε_ℓ/ε_h，不是直接 ratio 边界）
DIS_EPS_LOW_PREREGISTERED = 0.8
DIS_EPS_HIGH_PREREGISTERED = 3.0
DIS_TRUST_LOW = 1.0 - DIS_EPS_LOW_PREREGISTERED  # 0.2（开）
DIS_TRUST_HIGH = 1.0 + DIS_EPS_HIGH_PREREGISTERED  # 4.0（开）

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
    per_token_weight: tuple[float, ...]  # f(r_i)（含 mask=0 与被拒 token 的 0）
    per_token_grad_logp_current: tuple[float, ...]  # 解析梯度 dL/dlogp_current_i
    denominator: int
    accepted_token_count: int  # m_i=1 且 ratio 在信任区间内
    rejected_token_count: int  # m_i=1 但 ratio 越界（算法拒绝，provenance 不变）
    zero_grad_step: bool  # 全零有效 token（FA-4：跳过 optimizer step 的信号）


def _trust_bounds(eps_low: float, eps_high: float) -> tuple[float, float]:
    if not (0.0 < eps_low < 1.0) or not (eps_high > 0.0):
        raise ValueError(
            f"ε 参数非法：eps_low={eps_low}, eps_high={eps_high}——须 0<eps_low<1 且 "
            "eps_high>0（信任区间 (1-eps_low, 1+eps_high) 才是包含 1 的正区间）。"
        )
    if not math.isfinite(eps_low + eps_high):
        raise ValueError("ε 参数必须有限。")
    return 1.0 - eps_low, 1.0 + eps_high


def _token_weight(
    tok: DisTokenRecord, index: int, log_low: float, log_high: float
) -> float | None:
    """区间内返回 f(r)=r，越界返回 None；判断在 log 空间（溢出防护）。"""

    if tok.provenance_mask not in (0, 1):
        raise ValueError(f"token {index}: provenance_mask={tok.provenance_mask} 非 0/1。")
    if not (math.isfinite(tok.logp_current) and math.isfinite(tok.logp_rollout)):
        raise ValueError(f"token {index}: logp 非有限值。")
    if not math.isfinite(tok.advantage):
        raise ValueError(f"token {index}: advantage 非有限值（上游归一化事实矛盾）。")
    log_ratio = tok.logp_current - tok.logp_rollout
    if log_low < log_ratio < log_high:  # 式 3：严格不等号（开区间）
        return math.exp(log_ratio)
    return None


def faithful_dis_loss(
    tokens: list[DisTokenRecord],
    *,
    eps_low: float = DIS_EPS_LOW_PREREGISTERED,
    eps_high: float = DIS_EPS_HIGH_PREREGISTERED,
    denominator_semantics: DenominatorSemantics = DENOMINATOR_SEMANTICS_V1,
) -> DisLossResult:
    """faithful DIS 的平铺参考 loss + 解析梯度（单分母，"全局 token mean"口径）。

    fail-closed：logp/advantage 非有限、mask 非 0/1、ε 参数非法都直接抛错——
    参考实现的职责是把语义钉死，不是容错。
    """

    if not tokens:
        raise ValueError("faithful_dis_loss: 空 token 列表。")
    trust_low, trust_high = _trust_bounds(eps_low, eps_high)
    log_low, log_high = math.log(trust_low), math.log(trust_high)

    weights: list[float] = []
    accepted = 0
    rejected = 0
    provenance_count = 0
    for i, tok in enumerate(tokens):
        if tok.provenance_mask == 0:
            # mask 有效性仍要校验（fail-closed 不因掩码豁免）
            _token_weight(tok, i, log_low, log_high)
            weights.append(0.0)
            continue
        provenance_count += 1
        weight = _token_weight(tok, i, log_low, log_high)
        if weight is not None:
            weights.append(weight)
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


@dataclass(frozen=True)
class ExecutionDisResult:
    """三层归约的产物（branch 分子 → execution 分母 → batch execution 均值）。"""

    loss: float
    per_execution_loss: dict[str, float]
    per_execution_denominator: dict[str, int]
    # 逐 execution、逐 token 的解析梯度（顺序与输入 token 列表一致）
    per_token_grad_logp_current: dict[str, tuple[float, ...]]
    execution_count: int
    zero_grad_step: bool


def faithful_dis_loss_by_execution(
    executions: dict[str, list[DisTokenRecord]],
    *,
    eps_low: float = DIS_EPS_LOW_PREREGISTERED,
    eps_high: float = DIS_EPS_HIGH_PREREGISTERED,
    expected_denominators: dict[str, int] | None = None,
) -> ExecutionDisResult:
    """execution 级归约参考（codex FA-3/4 审查 #4 的层次证明对象）。

    语义::

        loss_e   = -(Σ_{i∈e} f(r_i)·A_i·logp_i) / D_e     D_e = e 的 provenance token 数
        loss     = (Σ_e loss_e) / N_exec                   （execution 等权平均）
        dL/dlogp_i = -(f(r_i)·A_i) / (D_e(i) · N_exec)

    branch 怎么切不进公式——同一 execution 的 token 集不变则结果不变
    （split invariance）；某 execution 的 branch/token 变化不影响其他
    execution 的 per-execution loss（分母隔离）。

    ``expected_denominators``：FA-3 `normalize_rewards_by_group` 产出的
    rollout_loss_denominator 口径互检——两边都是"该 execution 的可训练
    token 总数"，不一致即上游账目矛盾，fail-closed。
    """

    if not executions:
        raise ValueError("faithful_dis_loss_by_execution: 空 execution 集。")
    per_loss: dict[str, float] = {}
    per_denominator: dict[str, int] = {}
    per_grads: dict[str, tuple[float, ...]] = {}
    n_exec = len(executions)
    any_accepted = False
    for eid, tokens in executions.items():
        result = faithful_dis_loss(
            tokens,
            eps_low=eps_low,
            eps_high=eps_high,
            denominator_semantics="provenance_tokens",
        )
        if result.denominator == 0:
            raise ValueError(
                f"execution {eid} 的 provenance token 数为 0——上游（FA-3 归一化）"
                "已拒绝零 token execution，出现在这里是账目矛盾。"
            )
        if expected_denominators is not None:
            expected = expected_denominators.get(eid)
            if expected != result.denominator:
                raise ValueError(
                    f"execution {eid} 分母互检失败：FA-3 口径 {expected} != "
                    f"DIS provenance 口径 {result.denominator}。"
                )
        per_loss[eid] = result.loss
        per_denominator[eid] = result.denominator
        per_grads[eid] = tuple(g / n_exec for g in result.per_token_grad_logp_current)
        if result.accepted_token_count > 0:
            any_accepted = True
    total_loss = sum(per_loss.values()) / n_exec
    return ExecutionDisResult(
        loss=total_loss,
        per_execution_loss=per_loss,
        per_execution_denominator=per_denominator,
        per_token_grad_logp_current=per_grads,
        execution_count=n_exec,
        zero_grad_step=not any_accepted,
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

    trust_low, trust_high = _trust_bounds(eps_low, eps_high)
    log_low, log_high = math.log(trust_low), math.log(trust_high)
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
            for i, t in enumerate(provenance)
            if _token_weight(t, i, log_low, log_high) is None
        )
        counts[bucket][0] += rejected
        counts[bucket][1] += length
    return {label: (r, total) for label, (r, total) in counts.items()}
