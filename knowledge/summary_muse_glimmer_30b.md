# 《Meta Muse Glimmer 30B》阅读摘要

## 论文信息

- 无论文/arXiv。来源：Meta 官方博客（2026-08-10 发布）+ Hugging Face 模型卡 `meta-models/Muse-Glimmer-30B`（本摘要 2026-09-02 抓取）
- 本地论文：无
- 官方页面：<https://research.meta.ai/blog/introducing-muse-glimmer-open-agentic-model>；<https://huggingface.co/meta-models/Muse-Glimmer-30B>
- 来源类型与证据等级：厂商博客 + 模型卡（宣传性一手材料，无技术报告）。披露完整度：主张级——训练管线只有一句话级描述，无公式、无数据量、无超参；评测数字为自报且大多未说明 harness 与指标口径；博客中的对比表是图片，本次未能核读其中其他模型的数字。

## 核心问题

（产品定位而非研究问题）面向本地/单卡运行的开源 agentic 模型：30B、Apache 2.0、多模态输入（text + image、输出 text）。架构（模型卡）：Dense Causal Transformer，总参约 29.6B（含约 1.8B 的 ViT-G/14 perception encoder），不是 MoE；52 层、hidden 6656、GQA 32 query/2 KV 头、[Local,Local,Local,Global] 注意力模式 + 2048 sliding window、RoPE θ=500,000 仅 local 层；context 131,072+；vocab 202,048；知识截止 2026-01-04。

## Muse Glimmer 的训练方法（主张级）

- 预训练：自更大的 Muse Spark 做 logit 蒸馏——博客原话 "trained Muse Glimmer on Muse Spark's outputs using logit distillation, leveraging a similar data mix as the teacher"。Muse Spark 规格与训练 token 数未能核实。
- 中期训练（mid-training）："longer-context, more agent-heavy data with richer reasoning traces, alongside organic data"。数量与构成未披露。
- 后训练：博客称 "supervised fine-tuning with a mix of on-policy distillation and reinforcement learning"，覆盖 general/reasoning/coding/agentic 四域；OPD 的 teacher、RL 算法与环境、域配比全部未披露。模型卡另列 Safety SFT 与 Safety RL（safety-specific reward）。

## 实验设置与结果（模型卡自报数字）

- 编码/SWE：SWE-Bench Pro 51.2、SWE-Bench Verified 76.0、TerminalBench 2.1 51.7（注明用 terminus2）、SciCode 43.6。
- Agentic：MCP Atlas (Public) 75.5、DeepSearch QA 74.6、τ3-Banking 23.5（τ3 只报 Banking 一个域，指标口径未说明）、WildClawBench 47.6、OSWorld-Verified 65.9、SkillsBench (with skills) 44.3、Gaia2 43.3。
- 通用/多模态：AIME 2026 94.7、GPQA Diamond (AA) 83.5、IFBench 77.0、MMMU Pro 74、ScreenSpot Pro 75.4、Charxiv Reasoning 78.8、AA-LCR 80.0、Beam128K 65.1。
- 评测 harness 说明：除 TerminalBench 2.1 注明 terminus2 外基本缺失（模型卡只说另见评测报告）；博客提到与 OpenClaw 等 agentic orchestration 搭配使用。
- 博客正文只点名 DeepSearch QA、MCP-Atlas、τ-Bench 与 SWE-Bench 四类基准且不带数字（数字在图片表中）；上面的具体数值全部取自模型卡文本，两处来源在基准命名上一致。
- 发布物与许可：BF16 全量权重、两个 4-bit 量化（面向 24/32GB 显存）、DFlash speculative decoding drafter head、冻结的 perception encoder；Apache 2.0；是否放出 base 或中间 checkpoint 模型卡未提及，未能核实。附"不满 18 岁不得下载使用"条款。

## 重要限制

- 无技术报告：预训练蒸馏、OPD、RL 的全部细节停在一句话，不可复现，不能当配方参考。
- 评测口径缺失（采样次数、pass@k、工具配置），自报数字与其他模型的可比性弱；τ3-Banking 23.5 与其余 agentic 高分之间的落差没有解释。
- dense 架构推理成本高于同总参 MoE；总参含 1.8B 视觉编码器，与纯文本 30B 模型直接比分时口径并不对齐（文本侧约 27.8B）。

## 对 RepoHarness 的意义

- 同量级开源对照物：与我们的 Qwen3-30B-A3B 同属"30B 档"，其 SWE-Bench Pro 51.2 / SWE-Bench Verified 76.0 / TerminalBench 2.1 51.7 可当结果上限锚。但它是 dense 30B，每 token 激活算力约为我们 A3B 的十倍，对比时必须注明这不是同推理成本的比较。
- 路线佐证而非配方：它主张"大 teacher logit 蒸馏预训练 + SFT/OPD/RL 混合后训练"能在 30B 档做出强 agentic 模型，方向上支持我们 C 线 OPD，但零细节；C 线设计证据仍应取自 Intern-S2-Preview 与 Nemotron-Cascade 2 两篇。
- 可操作用途：Apache 2.0 权重可下载，适合当 B 线多 harness 评测的外部对照模型（在我们的 harness 面上跑），或 SWE 环境的 sanity 对照；TerminalBench 2.1 用 terminus2 的口径与我们计划中的 terminal 线评测可直接对表。
- 警示：τ3-Banking 仅 23.5 提示其多轮工具型域偏弱；把它当基线时应按域拆开看，不要用单一均分。
