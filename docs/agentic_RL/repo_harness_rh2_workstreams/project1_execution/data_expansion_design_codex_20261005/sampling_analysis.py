#!/usr/bin/env python3
"""有限探针设计的解析计算与固定种子核对；无模型、容器或第三方依赖。

从任意目录运行本脚本，将确定性 JSON 写到同目录 screening_sampling.json。
这里的独立 Bernoulli 是分析假设，不是对 RH2 实际候选独立性的保证。
"""

from itertools import product
import json
import math
from pathlib import Path
import random


def mixed(p, n):
    return 1 - p**n - (1 - p)**n


def stopped_prefix(bits, stages):
    for n in stages:
        k = sum(bits[:n])
        if 0 < k < n or n == stages[-1]:
            return n, k
    raise AssertionError("unreachable")


def adaptive_exact(p, stages):
    """全部 2^G 条路径穷举；阶段末发现成败混合即停止。"""
    result = dict(expected_n=0.0, mixed_probability=0.0,
                  expected_naive_task_rate=0.0, expected_successes=0.0)
    for bits in product((0, 1), repeat=stages[-1]):
        prob = p ** sum(bits) * (1 - p) ** (len(bits) - sum(bits))
        n, k = stopped_prefix(bits, stages)
        result["expected_n"] += prob * n
        result["mixed_probability"] += prob * (0 < k < n)
        result["expected_naive_task_rate"] += prob * k / n
        result["expected_successes"] += prob * k
    result["pooled_rate_same_p_limit"] = result["expected_successes"] / result["expected_n"]
    assert math.isclose(result["mixed_probability"], mixed(p, stages[-1]), abs_tol=1e-12)
    assert math.isclose(result["pooled_rate_same_p_limit"], p, abs_tol=1e-12)
    return result


def adaptive_mc(p, stages, trials=100000):
    rng = random.Random(20261005)
    total_n = total_mixed = 0
    total_rate = 0.0
    for _ in range(trials):
        bits = tuple(int(rng.random() < p) for _ in range(stages[-1]))
        n, k = stopped_prefix(bits, stages)
        total_n += n
        total_mixed += 0 < k < n
        total_rate += k / n
    return dict(trials=trials, seed=20261005, expected_n=total_n / trials,
                mixed_probability=total_mixed / trials,
                expected_naive_task_rate=total_rate / trials)


def main():
    ps = [0.01, 0.05, 0.10, 0.20, 0.50, 0.73, 0.90, 0.95]
    fixed = []
    for p in ps:
        for n in [1, 2, 4, 8]:
            fixed.append(dict(p=p, n=n, mixed_probability=mixed(p, n),
                              no_success_probability=(1 - p)**n,
                              all_success_probability=p**n,
                              expected_mixed_tasks_budget800=(800 // n) * mixed(p, n)))
    adaptive = []
    for p in ps:
        for stages in [(2, 4), (2, 4, 8)]:
            row = dict(p=p, stages=stages, **adaptive_exact(p, stages))
            adaptive.append(row)
    audit = []
    for n in [2, 4, 8, 12, 24, 30, 59, 60, 100, 149, 299]:
        audit.append(dict(independent_units=n,
                          zero_errors_one_sided_95_upper=1 - 0.05 ** (1 / n)))
    error = []
    for epsilon in [0.01, 0.02, 0.05, 0.10]:
        for n in [2, 4, 8]:
            error.append(dict(independent_flip_rate=epsilon, group_size=n,
                              false_mixed_when_truth_homogeneous=mixed(epsilon, n)))
    mixture = []
    for stages in [(2, 4), (2, 4, 8)]:
        rows = [adaptive_exact(p, stages) for p in [0.1, 0.5]]
        mixture.append(dict(ps=[0.1, 0.5], weights=[0.5, 0.5], stages=stages,
                            true_task_average=0.3,
                            naive_task_average=sum(r["expected_naive_task_rate"] for r in rows) / 2,
                            naive_rollout_pooled=sum(r["expected_successes"] for r in rows)
                            / sum(r["expected_n"] for r in rows)))
    result = dict(
        date="2026-10-05",
        status="design_calculation_not_model_measurement",
        design_summary={
            "status": "建议，未替换现行标准或实现",
            "per_task": ["自动事实提取", "公开题义与核心断言短核对", "适用版本的actor开发及noop/gold证据"],
            "risk_or_random_only": ["另造退化候选", "第三人完整深审", "多轮评分稳定性重跑"],
            "probe": "主模型初始两次广覆盖，追加到4/8与新题覆盖竞争；all-same不淘汰题",
            "baseline": "预登记初始固定样本与自适应追加样本分开报告",
            "reward": "现有二元评分与group admission保留；rubric先shadow，不阻塞扩量",
            "noise": "已知核心失效或可利用漏洞不能用总体低误差率豁免；未知残余风险分层抽查",
            "stop": "一轮修订和一次聚焦复核仍不收敛则暂挂该题，继续其它题",
        },
        audit_fields=["task_id", "source_revision", "material_revision", "environment_family",
                      "sampling_stratum", "selection_probability", "selection_reason", "model_revision",
                      "harness_revision", "sampling_config", "valid_attempts", "raw_reward",
                      "semantic_verdict_PASS_FAIL_UNKNOWN", "audit_scope", "root_cause_cluster",
                      "evidence_ref", "cpu_seconds", "model_tokens", "unverified_scope"],
        primary_sources=[
            {"url": "https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/73875d00b30a89ef8cc353a0b60b0e9f9561952d/MiMo_V2_6_technical_report.pdf",
             "sections": "4.2.1 pp.10-11; 4.2.2 p.12; 4.2.6 pp.14-16; 4.3.1-4.3.2 pp.17-19",
             "sha256": "fb81e6e083801b3358f084ed6be953dc23b0d2e434690f4541d5eae03e01e7af",
             "limit": "四次求解/八次评分为作者设计；不是最优次数证明；<2%为确认hack比例"},
            {"url": "https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/rubric_judge.py",
             "sections": "module contract, aggregate_rubric_scores, combine modes",
             "limit": "通用rubric实现不等于报告GAR完整实现；未运行judge"},
            {"url": "https://arxiv.org/html/2504.07164v1", "sections": "2, Appendix A, 4.2, C.3",
             "limit": "R2E-Gym为SFT及推理选优；生成测试和LLM判别也可错误"},
            {"url": "https://www.together.ai/blog/deepswe", "sections": "2.2, 2.3, 6",
             "limit": "特定Qwen3-32B配方，不能泛化数据来源优劣或固定组大小最优"},
            {"url": "https://arxiv.org/html/2504.21798v2", "sections": "4.1, Appendix E/F",
             "limit": "难度/仓库覆盖消融主要是SFT，不直接证明GRPO采样法"},
            {"url": "https://github.com/verl-project/uni-agent#agent-reinforcement-learning",
             "sections": "Agent Reinforcement Learning", "limit": "当前网页声明，不能替代具体recipe和本项目运行验证"},
        ],
        assumptions=["同一模型/checkpoint、harness、材料版本与预算固定",
                     "题内采样条件独立且同分布；真实相关性会降低有效样本量",
                     "固定预算800按轨迹数计，未假定各题token/CPU/墙钟相同",
                     "策略停止规则只用于离线测量，不默认用于训练组构建"],
        formulas={"mixed": "1-p**G-(1-p)**G",
                  "adaptive_2_4_cost": "2+2*(p**2+(1-p)**2)",
                  "adaptive_2_4_8_cost": "2+2*(p**2+(1-p)**2)+4*(p**4+(1-p)**4)",
                  "zero_error_upper95": "1-0.05**(1/n)",
                  "independent_symmetric_noise": "E[R|Z]=epsilon+(1-2*epsilon)*Z"},
        fixed_sampling=fixed,
        adaptive_sampling=adaptive,
        same_mean_counterexample={
            "population_A": {"task_p": 0.73, "mean_pass1": 0.73,
                             "mixed_G4": mixed(0.73, 4)},
            "population_B": {"p1_task_share": 0.73, "p0_task_share": 0.27,
                             "mean_pass1": 0.73, "mixed_G4": 0.0},
            "task_count_example": 200,
            "fixed_G4_rollouts": 800,
            "expected_mixed_A": 200 * mixed(0.73, 4),
            "expected_mixed_B": 0},
        adaptive_mixture_bias=mixture,
        zero_error_bounds=audit,
        reward_noise=error,
        marginal_gain_examples=[
            dict(p=p, fixed_n=n, extra=2,
                 unconditional_new_mixed_probability=(p**n+(1-p)**n)
                 -(p**(n+2)+(1-p)**(n+2)),
                 expected_extra_rollouts_if_extend_only_homogeneous=2*(p**n+(1-p)**n))
            for p in [0.1, 0.2, 0.5] for n in [2, 4, 6]],
        simulation_checks=[dict(p=p, stages=stages,
                                exact=adaptive_exact(p, stages),
                                monte_carlo=adaptive_mc(p, stages))
                           for p in [0.1, 0.5, 0.73] for stages in [(2,4),(2,4,8)]],
        evidence_limits=["计数不是学习收益；要用等token/GPU时的小训练对比选择组大小",
                         "0/n上界要求所抽单位独立、同分布或适当随机设计；审查者仍可能漏检",
                         "跨模型成败分歧不是某一模型的组内优势",
                         "无真实模型、GPU、Docker或grader运行"])
    for row in result["simulation_checks"]:
        for key, tolerance in [("expected_n", 0.04), ("mixed_probability", 0.01),
                               ("expected_naive_task_rate", 0.01)]:
            assert abs(row["exact"][key] - row["monte_carlo"][key]) < tolerance
    path = Path(__file__).with_name("screening_sampling.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": path.name, "fixed_rows": len(fixed),
                      "adaptive_rows": len(adaptive), "mc_checks": 6,
                      "counterexample": result["same_mean_counterexample"],
                      "mixture_bias": mixture}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
