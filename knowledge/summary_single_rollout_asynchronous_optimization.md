# 《Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning》阅读摘要

## 论文信息

- 标题：Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning
- arXiv：2607.07508v1，2026-07-08 提交
- 本地论文：`docs/harness_improve/external_paper_references/pdfs/2607.07508v1.pdf`
- 官方页面：<https://arxiv.org/abs/2607.07508>

## 核心问题

长周期 agent rollout 的完成时间差异很大。GRPO 必须等待同一个 prompt 的一组 rollout 全部完成后，才能计算组内相对优势；快样本因此等待慢样本，并在等待期间变得更加陈旧。SAO 改为每个 prompt 只采一个 rollout，并用 value model 估计 token 级 advantage，从结构上取消同 prompt 组等待。

## SAO 的四个关键组成

1. **Single-rollout sampling**：每个 prompt 的 group size 为 1，不依赖同题多样本的组均值和标准差。
2. **Direct Double-Sided Importance Sampling（DIS）**：直接使用当前训练策略和 rollout 行为策略的 token logprob 比值；比值落在双边阈值外的 token 完全不参与梯度，而不是仅把比值截到边界。
3. **更快且受约束的 value model 更新**：每次 policy 更新前做两次 critic 更新；训练 critic 时冻结 attention 参数，只更新 MoE projection，以减小 value model 梯度不稳定。
4. **Skip-Observation token-level GAE**：不在外部 observation token 上估计 value；从当前 action 的最后一个 token 直接桥接到下一 action 的第一个 token，避免把环境反馈误当作模型生成状态。

论文还强调 value model 冷启动是主要瓶颈，需要专门的 value pretraining，而不是临时增加一个随机初始化 value head 就开始训练。

## 关键实验结果

- 基座：Qwen3-30B-A3B-Thinking-2507。
- batch size 128，SAO group size 1；GRPO 对照为 16 prompts × 8 rollouts。
- 最大上下文 128k；SWE-Bench Verified 使用 OpenHands，最多 300 turns。
- SWE-Bench Verified：基座 23.0，GRPO+DIS 27.0，SAO 29.8。
- GRPO+DIS 在早期与 SAO 接近；论文报告大约 400 步后差距才明显。
- 标准 GRPO 在约 160 步发生性能崩溃，GRPO+DIS 保持稳定。

## 不能过度外推的地方

- 这是刚发布的 v1 论文，论文没有公开一套可直接运行的 SAO 代码和完整资源配置。
- 论文规模为 128k、300 turns、batch 128；不能直接证明 32k、30~50 步、8 卡的小规模 RepoHarness 首训一定应改用 SAO。
- SAO 依赖可靠的 rollout token logprobs 和经过预训练的 value model。value model 的数据、初始化和训练质量是新增实验变量。
- 论文自己的 limitation 也明确指出，结论未必直接迁移到更小模型、较短 rollout 或密集奖励环境。

## 对 RepoHarness 的直接启发

- DIS 可以先独立用于 GRPO，不需要等待完整 SAO；这是风险最低、论文证据最直接的增量实验。
- 现有 TrajectoryProjection 已保存 token identity、rollout logprobs、loss mask、行为策略版本和 action/observation 边界，因此具备实现 DIS 与 Skip-Observation GAE 的数据基础。
- 一次 rollout 产生多条分支不自动否定 GRPO。正确做法是先按独立 rollout execution 计算组内 advantage，再向同一 execution 的 branches 广播，并按 execution 级 token denominator 聚合 loss。
- 如果正式开启 compaction、上下文扩至 64k/128k、或全异步导致组等待和 policy staleness 显著增加，PPO/SAO 的结构优势会明显增强。
