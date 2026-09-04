# R2E-Gym：SWE 环境合成与混合 verifier

## 论文与定位

- 论文：<https://arxiv.org/abs/2504.07164>
- 官方代码：<https://github.com/R2E-Gym/R2E-Gym>
- 主要归属：环境生成，以及 verifier 区分性诊断；它不是 solver-relative learnability 或在线 curriculum 论文。

## SWE-GEN 环境生产

```text
GitHub commit
→ 规则与 LLM 筛选小范围修复
→ 恢复历史依赖和 Docker 环境
→ 提取或生成 fail-to-pass tests
→ 根据 patch、测试和执行结果反向生成 issue
→ executable task
```

- 完整集 8,135 题；去掉与 SWE-Bench test repo 重叠后为 4,578 题。
- 从 Sonnet-3.5-v2 的成功运行中收集论文所称 3,321 条轨迹，覆盖 2,048 个任务。
- 对 Qwen2.5-Coder 7B/14B/32B 做 full SFT，不是 RL。
- 32B 在论文当时的 SWE-Bench Verified 上从 7.0 提升到 34.4；该绝对 benchmark 数字今天不宜继续作为能力锚点。

环境生成并非全自动：历史依赖恢复是 semi-manual，只覆盖少量 Python repo，增加新 repo 需要维护安装和测试逻辑。

## Hybrid verifier 的关键发现

- execution-based testing agent 生成测试并执行候选 patch；多数问题中少于 20% 的生成测试能区分正确与错误 patch。
- 部分任务 toxic-test rate 可达约 10%，可能错误偏爱坏 patch。
- execution-free 14B verifier 读取完整轨迹与 patch，但会依赖 agent thoughts 等话术特征；只给 patch 时 Best@26 从 42.8 降到 37.6。
- 两类 verifier 各自约在 42–43% 饱和，混合后 Best@26 为 51%。51% 是多 rollout reranking，不是 agent 的 pass@1，也不是在线 RL reward 的受控结果。

## 后续外部审计

Prime 的重新验证只保留 4,522/4,578；原始 R2E 镜像把 grading tests 放在 agent 可读路径，面向在线 RL 时必须隐藏。该例说明“作者发布的可执行任务”仍需二次资格与安全审计。

## 对 RepoHarness 的意义

R2E-Gym 支持 commit + F2P test + backtranslation 的环境生产路线，也建议在四门之外记录：

- candidate-patch distinguishability；
- toxic-test rate；
- gold 与 alternate-correct solution survival；
- verifier disagreement。

但它不能替代 weak/current/strong solver profile，也不能证明任务对当前 GRPO policy 具有有效梯度。
