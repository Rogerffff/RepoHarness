"""FA-4 对拍部分：faithful DIS 参考实现的三方对拍与语义钉死。

对拍三方（05 计划 FA-4 + codex 轮次 3 #7 清单）：

1. **手算**：固定小张量的 loss/梯度逐位等于手推值；
2. **有限差分**：解析梯度 == 冻结权重下的数值微分（检验的是 detach 语义
   ——ratio 对 logp_current 的依赖路径不参与梯度）；
3. **torch autograd**：同构 torch 实现（`ratio.detach()`）的 loss 与
   per-token 梯度逐位等于参考实现——这套 harness 就是未来 Megatron
   custom loss 接线的对拍权威。

逐条钉死的语义：loss 正负号；ratio detach；越界 token 梯度**精确为零**
（== 0.0，不是近似）；denominator 两档语义的差异可观测；区间边界闭区间；
全零有效 token 的显式信号；provenance mask 不被算法掩码改写（输入不可变）。
"""

from __future__ import annotations

import math
import random

import pytest

from repoharness2.training.faithful_dis import (
    DIS_EPS_HIGH_PREREGISTERED,
    DIS_EPS_LOW_PREREGISTERED,
    DisTokenRecord,
    faithful_dis_loss,
    reject_ratio_by_length_bucket,
)


def _tok(logp_cur: float, logp_roll: float, advantage: float, mask: int = 1) -> DisTokenRecord:
    return DisTokenRecord(
        logp_current=logp_cur, logp_rollout=logp_roll, advantage=advantage, provenance_mask=mask
    )


# ----------------------------------------------------------------- 手算对拍


def test_hand_computed_case_exact():
    """三 token 手算：接受/拒绝/mask0 各一。

    t0: ratio = exp(-0.5+0.6) = e^0.1 ≈ 1.10517（区间内），A=2.0
    t1: ratio = exp(-3.0+0.1) = e^-2.9 ≈ 0.05502（< 0.8 拒绝），A=1.0
    t2: mask=0（不进 D、不进 loss）
    D = provenance tokens = 2
    loss = -(w0*A0*logp0)/D = -(1.10517*2.0*(-0.5))/2 = +0.55259
    dL/dlogp0 = -(w0*A0)/D = -1.10517
    dL/dlogp1 = 0（精确）
    """

    tokens = [_tok(-0.5, -0.6, 2.0), _tok(-3.0, -0.1, 1.0), _tok(-0.2, -0.2, 5.0, mask=0)]
    result = faithful_dis_loss(tokens)
    w0 = math.exp(0.1)
    assert result.per_token_weight == pytest.approx((w0, 0.0, 0.0))
    assert result.loss == pytest.approx(-(w0 * 2.0 * -0.5) / 2)
    assert result.per_token_grad_logp_current[0] == pytest.approx(-(w0 * 2.0) / 2)
    assert result.per_token_grad_logp_current[1] == 0.0  # 精确零，不是近似
    assert result.per_token_grad_logp_current[2] == 0.0
    assert result.denominator == 2
    assert result.accepted_token_count == 1
    assert result.rejected_token_count == 1
    assert result.zero_grad_step is False


def test_loss_sign_convention():
    """正 advantage + 接受 token：dL/dlogp < 0（梯度下降会抬高该 token 的
    logp——强化正优势行为，符号约定正确）。"""

    result = faithful_dis_loss([_tok(-0.5, -0.5, 1.0)])
    assert result.per_token_grad_logp_current[0] < 0
    negative = faithful_dis_loss([_tok(-0.5, -0.5, -1.0)])
    assert negative.per_token_grad_logp_current[0] > 0


# ------------------------------------------------------------- 有限差分对拍


def test_finite_difference_matches_analytic_under_detach_semantics():
    """冻结权重的数值微分 == 解析梯度（检验 detach：扰动 logp_current 时
    ratio/w 保持基点值——若实现忘了 detach，此测试会在接受 token 上失配）。"""

    rng = random.Random(20260712)
    tokens = [
        _tok(rng.uniform(-3, -0.05), rng.uniform(-3, -0.05), rng.uniform(-2, 2), rng.choice([0, 1]))
        for _ in range(24)
    ]
    base = faithful_dis_loss(tokens)
    eps = 1e-7
    for i in range(len(tokens)):
        # 冻结权重：用基点 w 重算扰动 loss（detach 语义的数值化）
        def frozen_loss(delta: float) -> float:
            total = 0.0
            for j, tok in enumerate(tokens):
                logp = tok.logp_current + (delta if j == i else 0.0)
                total += base.per_token_weight[j] * tok.advantage * logp
            return -total / base.denominator

        numeric = (frozen_loss(eps) - frozen_loss(-eps)) / (2 * eps)
        assert numeric == pytest.approx(base.per_token_grad_logp_current[i], abs=1e-6), i


# --------------------------------------------------------------- torch 对拍

torch = pytest.importorskip("torch", reason="torch 侧对拍需要 dev 依赖")


def _torch_faithful_dis(
    logp_current: "torch.Tensor",
    logp_rollout: "torch.Tensor",
    advantages: "torch.Tensor",
    mask: "torch.Tensor",
    *,
    eps_low: float = DIS_EPS_LOW_PREREGISTERED,
    eps_high: float = DIS_EPS_HIGH_PREREGISTERED,
) -> "torch.Tensor":
    """torch 同构实现（未来 Megatron custom loss 的形状雏形）。

    关键语义与参考实现逐条对应：ratio 走 `.detach()`；越界 token 权重置零；
    D = provenance token 数（DENOMINATOR_SEMANTICS_V1）。
    """

    ratio = torch.exp(logp_current - logp_rollout).detach()
    in_range = (ratio >= eps_low) & (ratio <= eps_high)
    weights = torch.where(in_range, ratio, torch.zeros_like(ratio)) * mask
    denominator = mask.sum()
    return -(weights * advantages * logp_current).sum() / denominator


def test_torch_parity_loss_and_per_token_grads():
    """torch autograd 的 loss 与逐 token 梯度 == 参考实现（1e-9 容差）。"""

    rng = random.Random(42)
    tokens = [
        _tok(rng.uniform(-4, -0.01), rng.uniform(-4, -0.01), rng.uniform(-2, 2), rng.choice([0, 1, 1]))
        for _ in range(64)
    ]
    reference = faithful_dis_loss(tokens)

    logp_current = torch.tensor([t.logp_current for t in tokens], dtype=torch.float64, requires_grad=True)
    logp_rollout = torch.tensor([t.logp_rollout for t in tokens], dtype=torch.float64)
    advantages = torch.tensor([t.advantage for t in tokens], dtype=torch.float64)
    mask = torch.tensor([float(t.provenance_mask) for t in tokens], dtype=torch.float64)

    loss = _torch_faithful_dis(logp_current, logp_rollout, advantages, mask)
    loss.backward()

    assert loss.item() == pytest.approx(reference.loss, abs=1e-9)
    for i, grad in enumerate(logp_current.grad.tolist()):
        assert grad == pytest.approx(reference.per_token_grad_logp_current[i], abs=1e-9), i


def test_torch_out_of_range_grads_exactly_zero():
    """torch 侧同样要求越界 token 梯度精确为零（不是小量）。"""

    logp_current = torch.tensor([-5.0, -0.5], dtype=torch.float64, requires_grad=True)
    logp_rollout = torch.tensor([-0.1, -0.5], dtype=torch.float64)  # t0 ratio e^-4.9 越界
    advantages = torch.tensor([3.0, 1.0], dtype=torch.float64)
    mask = torch.ones(2, dtype=torch.float64)
    loss = _torch_faithful_dis(logp_current, logp_rollout, advantages, mask)
    loss.backward()
    assert logp_current.grad[0].item() == 0.0
    assert logp_current.grad[1].item() != 0.0


# --------------------------------------------------------- 语义边界与信号


def test_interval_boundaries_are_closed():
    """ratio 恰等于 eps_low/eps_high：接受（闭区间语义）。

    边界值取"实际计算出的 ratio"本身（exp(log(x)) 的浮点回环会差 1ulp，
    直接用预注册常数做 logp 构造会假失败——这里测的是闭区间语义，
    不是浮点回环）。"""

    low_ratio = math.exp(-0.75 - (-0.52))  # ≈0.7945
    high_ratio = math.exp(-0.10 - (-1.19))  # ≈2.9743
    tokens = [_tok(-0.75, -0.52, 1.0), _tok(-0.10, -1.19, 1.0)]
    result = faithful_dis_loss(tokens, eps_low=low_ratio, eps_high=high_ratio)
    assert result.accepted_token_count == 2  # 两端都恰在边界上，闭区间接受
    assert result.per_token_weight == pytest.approx((low_ratio, high_ratio))
    # 越过边界 1ulp 级别即拒绝
    import math as _m
    result2 = faithful_dis_loss(
        tokens,
        eps_low=_m.nextafter(low_ratio, 1.0),
        eps_high=_m.nextafter(high_ratio, 0.0),
    )
    assert result2.accepted_token_count == 0


def test_denominator_semantics_differ_observably():
    """provenance_tokens（预注册 v1）vs accepted_tokens：被拒 token 留不留
    分母直接改变有效学习率——两档必须可区分且各自自洽。"""

    tokens = [_tok(-0.5, -0.5, 1.0), _tok(-4.0, -0.1, 1.0)]  # 1 接受 1 拒绝
    v1 = faithful_dis_loss(tokens, denominator_semantics="provenance_tokens")
    v2 = faithful_dis_loss(tokens, denominator_semantics="accepted_tokens")
    assert v1.denominator == 2 and v2.denominator == 1
    assert v2.loss == pytest.approx(v1.loss * 2)
    assert v2.per_token_grad_logp_current[0] == pytest.approx(
        v1.per_token_grad_logp_current[0] * 2
    )


def test_zero_valid_token_step_signals_skip_without_nan():
    """全拒绝 -> zero_grad_step=True、loss=0、无除零/NaN（FA-4：跳 step 信号）。"""

    tokens = [_tok(-6.0, -0.1, 1.0), _tok(-0.2, -0.2, 1.0, mask=0)]
    result = faithful_dis_loss(tokens)
    assert result.zero_grad_step is True
    assert result.loss == 0.0
    assert all(g == 0.0 for g in result.per_token_grad_logp_current)
    all_masked = faithful_dis_loss([_tok(-0.2, -0.2, 1.0, mask=0)])
    assert all_masked.zero_grad_step is True and all_masked.denominator == 0


def test_provenance_mask_is_not_rewritten():
    """算法掩码不改写 provenance（FA-0 分离约定）：输入 dataclass 冻结，
    拒绝只体现在 per_token_weight/计数上。"""

    tok = _tok(-6.0, -0.1, 1.0)
    result = faithful_dis_loss([tok, _tok(-0.5, -0.5, 1.0)])
    assert tok.provenance_mask == 1  # frozen dataclass，物理不可写
    assert result.rejected_token_count == 1
    assert result.denominator == 2  # 被拒 token 仍在 provenance 分母中（v1 语义）


def test_eps_interval_validation():
    with pytest.raises(ValueError, match="eps"):
        faithful_dis_loss([_tok(-0.5, -0.5, 1.0)], eps_low=0.0)
    with pytest.raises(ValueError, match="eps"):
        faithful_dis_loss([_tok(-0.5, -0.5, 1.0)], eps_low=1.2, eps_high=3.0)
    with pytest.raises(ValueError, match="eps"):
        faithful_dis_loss([_tok(-0.5, -0.5, 1.0)], eps_high=0.9)


# ----------------------------------------------------------------- 指标 helper


def test_reject_ratio_by_length_bucket_counts():
    short_traj = [_tok(-6.0, -0.1, 1.0)] * 4  # 4 token 全拒
    long_traj = [_tok(-0.5, -0.5, 1.0)] * 3000  # 3000 token 全接受
    counts = reject_ratio_by_length_bucket(
        [short_traj, long_traj], bucket_edges=(2048, 8192, 32768)
    )
    assert counts["(0,2048]"] == (4, 4)
    assert counts["(2048,8192]"] == (0, 3000)
    assert counts["(8192,32768]"] == (0, 0)
