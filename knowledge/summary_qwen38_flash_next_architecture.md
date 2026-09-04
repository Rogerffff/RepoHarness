# 《On the Design of Qwen3.8-Next Architecture》阅读摘要

## 论文信息

- 来源：Qwen Team，2026-08-26，GitHub `QwenLM/Qwen3.8-Flash-Next` 仓库内 `tech_report.pdf`（非 arXiv，正文 23 页）。
- 对象：**Qwen3.8-Flash-Next**——125B 总参、**6B activated** 的稀疏 MoE，外加 51B 参数的 n-gram 嵌入表（放在加速器外、host memory 预取）。
- 定位：**架构 + 预训练设计消融 + 训练稳定性报告**。没有 post-training/RL 配方章节；§4 只评 base 模型。

## 核心问题

用 1/3 的激活参数、1/3 的训练 token、约 1/9 的训练 FLOPs，保住上一代 397B-A17B 旗舰（Qwen3.7-Plus）的质量。方法论主张：每个架构改动都沿三根轴同时评（loss+下游基准 / 训练+prefill+decode 成本 / 最优超参与训练稳定性），因为三根轴经常不一致。

## 方法（四个架构组件 + 优化器）

1. **GDN 混合注意力**：3 层 Gated DeltaNet（线性代价的定长循环态，erase-and-write 式 delta 更新）+ 每 4 层 1 层全注意力；消融显示 GDN 混合在 9 项基准中 8 项超全注意力 Transformer（28 层 25B-A3B、400B@4K + 80B@32K 设置）。
2. **QSA（Qwen Sparse Attention）**：continued-pretraining（256K 序列）阶段把全注意力层换成 QSA——压缩轻量 indexer（MQA、块内均池化、partial RoPE、块因果打分）选 top-k 微块。训练分两段：先把 teacher 注意力分布（max-pool 到块级）KL 蒸馏进 indexer，再稀疏训练。1M 上下文时 kernel 级 prefill 7.6×、decode 4.9× 于稠密注意力。
3. **Gated Residual（GR）**：残差流加宽为 4 分支、elementwise 门控读写。机理分析（Fig.7）：GR 把跨层信息重新分配给少数长程路径（相邻层 +0.96、长程 +0.91、中程 −3.21 份额）。FP8 残差态可行（门控约束了幅值）。
4. **n-gram 嵌入层**：放 Layer 2 单层即够（多层无一致收益）；固定参数预算下 10×词表（25%）是 loss 最优但**下游收益饱和**。
5. **Muon 优化器**：NS 8 步 + Polar Express 系数；只用于真正做线性映射的二维权重（router/低秩 GR 投影/嵌入用 AdamW）；fused 参数必须先拆再正交化（否则混淆无关子块的奇异方向）；分布式实现 Canzona（arXiv 2602.06079）+ CUDA graph。
6. **超参 scaling law 重拟合**：新架构+Muon 把最优 batch 与 LR 都推大；**batch-size warmup 不再必要**（ramp 比恒定 batch 多花 18.8% optimizer 步且 loss 更差）。

## 实验结果（带数字）

- Base 对比（Tab.11，14 基准）：Flash-Next-Base 对 Qwen3.8-27B-Base **14/14 全胜**；对 397B 的 Qwen3.7-Plus-Base **8/14 胜**（如 MMLU-Pro 73.23 vs 70.90、BBH 90.87 vs 89.41、SWEBench-Pretrain 50.99 vs 49.24）。
- 稳定性压力测试（28 层 MoE，恒定 2×/4× 最优 LR）：4× 下 AdamW 每 10k 步 183 次 loss spike、213 次越过 clip 阈值；**Muon+GR 零 loss spike、从不触 clip**。单变量隔离：开 GatedNorm 把 spike 率 32.0→3.2/10k。生产 run 前 276B token：GR 使梯度范数 1000 步窗口标准差低 4.3-4.7×。全程未用 qk-clip / SwiGLU-clip。

## 重要限制

- **没有 post-training/agentic 内容**：无 RL/SFT 配方、无工具使用/长程任务评测；后训练只以"影响架构决策的现象"形式出现。
- 架构消融承认不能隔离单组件因果（混合设计的整体对比）。
- n-gram 嵌入的多种参数效率策略（token 归一化压缩、非均匀分配、频率分区）在其训练配方下都无一致收益（诚实负结果）。

## 对 RepoHarness 的意义

这是一份"底座约束"类报告（对应材料束 I / pro 文档 §7.1），核心价值是**三个"预训练指标会骗人"的实证 + 一句点题**：

1. **NoPE 变体预训练无差异，post-training 后"无终止生成"率显著更高**（§2.1.1）——预训练架构选择直接改变后训练的终止行为。对我们：终止语义（TerminationKind 五族、episode timeout 分类）不只是 harness 层问题，底座就能引入系统性差异；换底座时终止行为要重新标定。
2. **稀疏化 GR 读取：预训练 loss/基准几乎不变，post-training 后质量明显退化**（§2.2）——原文明说"this as a case where pre-training metrics alone would have led to the wrong decision"。
3. **n-gram 词表放大：loss 单调降但下游饱和**——loss 与能力解耦的又一例。
4. 结论点题：**"a cheaper mid-scale probe that reliably predicts post-training ordering would make the design space far more searchable"**——Qwen 自己把"能预测 post-training 排序的廉价中尺度探针"列为最紧瓶颈。这与我们"训练完整性短跑"、评测三层架构（外部pro模型调查2 的内部辨识层）在同一条问题线上，可作为简历叙事的行业对标（连基座团队都缺 post-training 预测性探针）。
5. 前瞻负担提示：GDN 混合 + QSA 这类底座若成为未来开源主流（DSA 已在 DeepSeek V3.2 出现），我们的训推一致性机制（tape/logprob 对拍）将面对"线性注意力循环态 + 稀疏 index 选择"两类新的不确定源——vLLM RFC #48305 已把 DSA index 列为 RL 一致性问题，QSA 属同类。
6. 边界：本报告**不能**用于推断 Qwen3.8 系的 agentic post-training 配方（那部分至今未披露）；SWEBench-Pretrain 是预训练阶段变体基准，与 agent 态 SWE-bench 不可比。
