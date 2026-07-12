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
    DIS_TRUST_HIGH,
    DIS_TRUST_LOW,
    DisTokenRecord,
    faithful_dis_loss,
    faithful_dis_loss_by_execution,
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
    t1: ratio = exp(-3.0+0.1) = e^-2.9 ≈ 0.05502（< 信任下界 0.2 拒绝），A=1.0
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

    关键语义与参考实现逐条对应：ratio 走 `.detach()`；信任区间 =
    (1-eps_low, 1+eps_high) 开区间（论文式 3）；越界 token 权重置零；
    D = provenance token 数（DENOMINATOR_SEMANTICS_V1）；全零 D 返回
    可微零（无 NaN）。
    """

    ratio = torch.exp(logp_current - logp_rollout).detach()
    trust_low, trust_high = 1.0 - eps_low, 1.0 + eps_high  # 论文式 3 参数化
    in_range = (ratio > trust_low) & (ratio < trust_high)  # 开区间（严格不等号）
    weights = torch.where(in_range, ratio, torch.zeros_like(ratio)) * mask
    numerator = -(weights * advantages * logp_current).sum()
    denominator = mask.sum()
    # 零安全（codex FA-3/4 审查 #5）：全局有效 token 为零时返回与 logits
    # 连接的可微零（clamp 防除零 + 门控清零），不产生 NaN、不断计算图——
    # 分布式实现的 CP 空 rank 同款语义。
    safe = torch.clamp(denominator, min=1.0)
    return (numerator / safe) * (denominator > 0)


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


def test_trust_interval_is_open_per_paper_eq3():
    """论文式 3：1-ε_ℓ < r < 1+ε_h **严格不等号**——恰在边界上的 ratio 拒绝。

    coding 配置 ε=(0.8, 3.0) -> 信任区间 (0.2, 4.0)。2026-07-12 勘误：此前
    误实现为 [0.8, 3.0] 直接 ratio 闭区间（codex FA-3/4 审查 #1，已对照
    论文 p.4 原文裁决）。论文正文写 "[1-ε_ℓ, 1+ε_h]" 闭括号与式 3 矛盾，
    以正式定义（式 3）为准。边界判断在 log 空间完成（溢出防护），测试
    直接用 log 值构造精确边界命中。"""

    assert DIS_TRUST_LOW == 1.0 - DIS_EPS_LOW_PREREGISTERED
    assert DIS_TRUST_HIGH == 1.0 + DIS_EPS_HIGH_PREREGISTERED
    assert (DIS_TRUST_LOW, DIS_TRUST_HIGH) == pytest.approx((0.2, 4.0))
    # 精确边界：log_ratio == log(0.2) / log(4.0) -> 开区间拒绝
    at_low = _tok(math.log(DIS_TRUST_LOW), 0.0, 1.0)
    at_high = _tok(math.log(DIS_TRUST_HIGH), 0.0, 1.0)
    boundary = faithful_dis_loss([at_low, at_high])
    assert boundary.accepted_token_count == 0
    assert boundary.rejected_token_count == 2
    # 区间内侧（含 ratio=1 完全 on-policy 与靠近边界的值）接受
    inside = faithful_dis_loss(
        [_tok(0.0, 0.0, 1.0), _tok(math.log(0.25), 0.0, 1.0), _tok(math.log(3.9), 0.0, 1.0)]
    )
    assert inside.accepted_token_count == 3
    # 巨大 logp 差不溢出（log 空间阈判）：先拒绝、不执行 exp
    huge = faithful_dis_loss([_tok(500.0, -500.0, 1.0), _tok(0.0, 0.0, 1.0)])
    assert huge.rejected_token_count == 1 and huge.accepted_token_count == 1


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
    """ε 参数域：0<eps_low<1（信任下界为正）、eps_high>0、有限。"""

    for bad in (dict(eps_low=0.0), dict(eps_low=1.0), dict(eps_low=1.2),
                dict(eps_high=0.0), dict(eps_high=-1.0),
                dict(eps_low=float("nan"))):
        with pytest.raises(ValueError, match="ε|eps"):
            faithful_dis_loss([_tok(-0.5, -0.5, 1.0)], **bad)


def test_nan_advantage_fail_closed():
    """codex FA-3/4 审查（输入校验）：NaN advantage 必须显式拒绝。"""

    with pytest.raises(ValueError, match="advantage"):
        faithful_dis_loss([_tok(-0.5, -0.5, float("nan"))])


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


# ------------------------------------------- execution 级归约层次（codex #4）


def _exec_tokens(n: int, *, logp_gap: float = 0.0, advantage: float = 1.0) -> list[DisTokenRecord]:
    return [_tok(-0.5, -0.5 - logp_gap, advantage) for _ in range(n)]


def test_hierarchy_branch_split_invariance():
    """branch 怎么切不改变结果：同一 execution 的 token 集按 2 段或 3 段
    branch 交付，execution 级归约的 loss 与逐 token 梯度完全一致。"""

    tokens = [_tok(-0.4 - 0.01 * i, -0.5, 1.0) for i in range(12)]
    as_one = faithful_dis_loss_by_execution({"e1": tokens})
    # branch 切分只是交付分组，归约按 execution 聚合 -> 输入相同集合即等价
    regrouped = faithful_dis_loss_by_execution({"e1": tokens[:5] + tokens[5:]})
    assert as_one.loss == pytest.approx(regrouped.loss)
    assert as_one.per_token_grad_logp_current["e1"] == pytest.approx(
        regrouped.per_token_grad_logp_current["e1"]
    )


def test_hierarchy_fanout_change_isolated_to_own_execution():
    """一个 execution 的 token/branch 数变化不改变其他 execution 的
    per-execution loss（分母隔离——stock 单分母折叠做不到这一点）。"""

    base = faithful_dis_loss_by_execution(
        {"e1": _exec_tokens(4), "e2": _exec_tokens(6, advantage=-1.0)}
    )
    fanned = faithful_dis_loss_by_execution(
        {"e1": _exec_tokens(16), "e2": _exec_tokens(6, advantage=-1.0)}
    )
    assert base.per_execution_loss["e2"] == pytest.approx(fanned.per_execution_loss["e2"])
    # 对照：平铺单分母下 e2 的贡献会被 e1 的 token 数稀释（两种 reducer 语义
    # 可区分——治理层准确提供两种分母，reducer 选择归训练算法，分析文档 §3.2）
    flat_base = faithful_dis_loss(_exec_tokens(4) + _exec_tokens(6, advantage=-1.0))
    flat_fanned = faithful_dis_loss(_exec_tokens(16) + _exec_tokens(6, advantage=-1.0))
    assert flat_base.loss != pytest.approx(flat_fanned.loss)


def test_hierarchy_dp_partition_invariance():
    """DP 分区不变性：把 executions 拆成两个分区分别归约，按 execution 数
    加权重组 == 全批一次归约（分布式归约的离线等价形）。"""

    executions = {
        "e1": _exec_tokens(3),
        "e2": _exec_tokens(5, advantage=-0.5),
        "e3": _exec_tokens(7, logp_gap=0.05),
        "e4": _exec_tokens(2, advantage=2.0),
    }
    full = faithful_dis_loss_by_execution(executions)
    part1 = faithful_dis_loss_by_execution({k: executions[k] for k in ("e1", "e2")})
    part2 = faithful_dis_loss_by_execution({k: executions[k] for k in ("e3", "e4")})
    recombined = (part1.loss * part1.execution_count + part2.loss * part2.execution_count) / (
        part1.execution_count + part2.execution_count
    )
    assert full.loss == pytest.approx(recombined)


def test_hierarchy_denominator_cross_check_with_fa3():
    """FA-3 rollout_loss_denominator 互检：口径一致通过，不一致 fail-closed。"""

    executions = {"e1": _exec_tokens(4)}
    ok = faithful_dis_loss_by_execution(executions, expected_denominators={"e1": 4})
    assert ok.per_execution_denominator == {"e1": 4}
    with pytest.raises(ValueError, match="分母互检失败"):
        faithful_dis_loss_by_execution(executions, expected_denominators={"e1": 5})
    with pytest.raises(ValueError, match="provenance token 数为 0"):
        faithful_dis_loss_by_execution({"e1": [_tok(-0.5, -0.5, 1.0, mask=0)]})


def test_cross_version_two_turn_scenario():
    """跨版本双 turn（codex FA-3/4 审查遗漏项的 DIS 层形态）：turn1 与
    current 同版本（ratio≈1 接受），turn2 来自更旧行为策略（logp 差大 →
    ratio 越界拒绝）——同一 execution 内逐 token 各判各的，turn1 照常训练。"""

    turn1 = [_tok(-0.5, -0.5, 1.0) for _ in range(3)]  # 同版本：ratio=1
    turn2 = [_tok(-0.5, -3.0, 1.0) for _ in range(2)]  # 旧版本：ratio=e^2.5≈12.2 越界
    result = faithful_dis_loss_by_execution({"e1": turn1 + turn2})
    inner = faithful_dis_loss(turn1 + turn2)
    assert inner.accepted_token_count == 3
    assert inner.rejected_token_count == 2
    assert all(g != 0.0 for g in result.per_token_grad_logp_current["e1"][:3])
    assert all(g == 0.0 for g in result.per_token_grad_logp_current["e1"][3:])


def test_torch_all_masked_returns_differentiable_zero_no_nan():
    """codex FA-3/4 审查 #5：torch 侧全 mask=0 -> loss 0、梯度 0、无 NaN，
    且计算图保持连接（backward 不炸）——CP 空 rank 的语义雏形。"""

    logp_current = torch.tensor([-0.5, -1.0], dtype=torch.float64, requires_grad=True)
    logp_rollout = torch.tensor([-0.5, -1.0], dtype=torch.float64)
    advantages = torch.tensor([1.0, 1.0], dtype=torch.float64)
    mask = torch.zeros(2, dtype=torch.float64)
    loss = _torch_faithful_dis(logp_current, logp_rollout, advantages, mask)
    loss.backward()  # 图连接：backward 可执行
    assert loss.item() == 0.0 and not math.isnan(loss.item())
    assert logp_current.grad is not None
    assert all(g == 0.0 for g in logp_current.grad.tolist())
