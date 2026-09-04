# 《CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents》阅读摘要

## 论文信息

- arXiv：2607.05378v1，2026-07-06 提交
- 本地论文：`docs/harness_improve/external_paper_references/pdfs/2607.05378v1.pdf`
- 官方页面：<https://arxiv.org/abs/2607.05378>

## 核心问题

长周期 agent 的上下文耗尽后，普通做法是把历史总结成较短文本，再从 summary 和少量最近交互继续执行。推理时启用 compaction 并不代表模型会生成对后续执行真正有用的 summary。summary 会决定后续策略能看到哪些文件路径、错误、已完成操作、当前工作状态与下一步，因此它本身也是需要训练的策略动作。

## CompactionRL 的方法

1. 在剩余上下文低于阈值时，让同一个可训练 policy 根据固定总结指令生成 summary。
2. 重建上下文时保留 system prompt、包含 summary 的 resume user message 和最近两个完整 assistant-observation 原子步骤。
3. 一次完整 rollout 被分成 execution segments 与 summary segments；两类 segment 都使用最终任务 reward，不设计单独 summary reward。
4. summary 原始生成 token 参与训练；重建上下文中复制的 summary、最近历史、工具 observation 和模板文本都只能作为 mask=0 上下文。
5. 使用全局 token-level loss normalization，避免每个 segment 各自平均导致 compaction 次数多的 rollout 被额外放大。
6. 使用 cross-trajectory GAE：先在 segment 内计算 local GAE，再按后续 segment 的 trainable token 数量修正折扣，使早期 action/summary 不会因为切段而错误地“靠近”最终 reward。

cross-trajectory GAE 是近似方法，不是跨 segment 完整串行 bootstrap。论文也明确将这一点列为限制。

## 实验设置与结果

- 模型：GLM-4.7-Flash 30B-A3B、GLM-4.5-Air 106B-A30B。
- 每个 critic 从同一模型 checkpoint 初始化，并先做 50 steps value pretraining。
- global batch 128、group size 1；每 batch 两次 value update、一次 policy update。
- 30B 使用 64k peak context，106B 使用 80k；单次 response 上限 10,240 tokens；最多三次 compaction，相当于最多四个上下文窗口。
- 训练数据为 SWE-Dev，训练框架为 slime；评测使用 Terminus-KIRA + Harbor。
- 30B：SWE-bench Verified compacted evaluation 从 50.5 提升到 56.0；Terminal-Bench 2.0 从 13.4 提升到 20.2。
- 106B：对应结果从 59.8 提升到 66.8，以及从 21.4 提升到 24.5。
- 去掉 token-level loss 后，106B 的 66.8/24.5 降到 60.0/21.3；去掉 cross-trajectory GAE 后降到 63.0/22.5。

## 重要限制

- 收益主要出现在启用 compaction 的评测面；关闭 compaction 的 single-window 评测并不稳定受益，30B 的 SWE 指标甚至下降。
- 论文只在 coding/terminal agent 上验证，SWE 结果使用随机 200 题和两次评测均值。
- 公开 slime 主分支没有专门的 CompactionRL 配方和 cross-trajectory GAE 实现。

## 对 RepoHarness 的意义

- 近期 32k GRPO 基线仍应关闭 compaction；这篇论文不要求立即改首训算法。
- 长期打开 compaction 时，不能只把多叶链当普通 fan-out。必须记录 execution/summary segment 类型、顺序、trainable token 数、触发点、重建上下文和 summary capture provenance。
- 当前 `CompactedSubTraceLineage`、`replay_prefix_loss_masked`、token source spans 和 rollout-level denominator 已有正确基础，但还缺 canonical compaction event 与 cross-segment advantage 所需的位置账目。
- SAO 与 CompactionRL 互补：SAO 解决 single-rollout 异步、off-policy 和 observation 跨越；CompactionRL 解决 summary joint training、segment length weighting 和 compaction boundary credit assignment。
