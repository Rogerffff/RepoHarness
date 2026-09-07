# 来源与候选完整目录

导出日期：2026-09-07。使用方式与边界见 [交接说明](00_HANDOFF.md)。各篇正文完整保留；本地链接转为仓库引用文字，页内导航转为文字；需要原图/代码时请访问官方来源。


---

## 文档 1 / 1：SOURCE_CATALOG.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/SOURCE_CATALOG.md`

# 资料目录与旧稿复用盘点

盘点日期：2026-09-07。用途是安排精读，不是声称下列资料已经完成事实核验。原始目录盘点、旧稿质量盘点与五份项目设计对话的遗漏线索由三名独立 GPT-6 Astra / high 子 agent 并行完成，主线程合并。

**同日完成更新**：R1、R3、N01、E2、N11、N13 已交付 7 份精读笔记并完成独立审查；优先查 成品索引〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/README.md`〕，质量范围见 第一组检查〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH1_QUALITY_REVIEW_20260907.md`〕。下方“本轮仅核标题/未重验”等盘点措辞只适用于尚未更新的来源，不覆盖这些已完成项。

**第二组完成更新**：R2、R13、R4/N10、E10、E5、O03 的七份笔记及六份独立审查已交付，主线程检查完成，见 执行记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH2_RUN.md`〕、质量检查〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH2_QUALITY_REVIEW_20260907.md`〕。两批累计 14 份笔记；对应条目以下方新稿为后续维护入口。

**第三组仅保留为候选，未启动**：用户将由外部 Pro 复查两批、重排并在外部继续阅读；本地不继续派发。R15、R14、O01、N07、N08、E7 的来源、版本、页数、旧稿与逐任务提示已准备，见 任务 13–18〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH3_PLAN.md`〕。本次是来源/目录核验，不是全文精读。O01 的正式论文名为 SkyRL-Agent，SA-SWE-32B 是模型名；E13 本地 PDF 为 v2、31 页，另排独立任务，未验证所谓术语首创性。

范围：manifest 的 32 份 PDF 全部存在；原始索引另外包含 GLM-5.3 与 34 行在线入口；另补已有笔记但未登记的 RLVE。下方新增候选 17 行中也有与这些入口同源或重叠的项目。**行数不是独立论文数，多个 URL 也不一定代表多篇论文。**

本轮只联网核了新增 KAT、SSR、Socratic-SWE、SDPO、OPSD 的 arXiv 标题/摘要；没有完成这些论文全文核验。其余入口以本地已记录的 URL 为线索，正式阅读时再核有效性、标题和版本。在线作者博客/社区讨论不自动视为一手训练证据。

编号：R / E 沿用原索引；O01–O34 对应已有 README 的在线入口，O35 为 RLVE；N 为本轮补充候选。编号只用于查找。A/B/C 的顺序见 派工计划〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/README.md`〕。

## 1. 本地 PDF：32 篇

| 编号 | 标题与顺序 | 原文入口 | 既有笔记与复用状态 |
| --- | --- | --- | --- |
| R0 | Polar / ProRL-Agent-Server paper<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/2605.24220v1.pdf`〕<br>旧索引恢复候选：<https://arxiv.org/abs/2605.24220>（未核远端版本） | 仅综合摘要<br>docs/harness_improve/repo_harness_repositioning_after_polar.md〔仓库引用：`docs/harness_improve/repo_harness_repositioning_after_polar.md`〕<br>docs/harness_improve/repositioning_design_review.md〔仓库引用：`docs/harness_improve/repositioning_design_review.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕<br>docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md〔仓库引用：`docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md`〕 |
| R1 | Microsoft MAI-Thinking-1<br>A · 任务 01，已完成 | 本地 PDF〔仓库引用：`docs/harness_improve/main_20260602_2.pdf`〕<br>本地/在线文件版本区别见新稿 §1 | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R1_mai_thinking_1.md`〕<br>旧综合稿仍保留：repositioning_design_review〔仓库引用：`docs/harness_improve/repositioning_design_review.md`〕、配方矩阵〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R2 | NVIDIA Nemotron 3 Ultra Technical Report<br>A · 已完成任务 07 | 本地 PDF〔仓库引用：`docs/harness_improve/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf`〕<br>官方原文：<https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf>（版本及访问核验见新稿 §1） | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R2_nemotron_3_ultra.md`〕<br>旧综合稿保留<br>docs/harness_improve/repositioning_design_review.md〔仓库引用：`docs/harness_improve/repositioning_design_review.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R3 | Qwen3-Coder-Next Technical Report<br>A · 任务 02，已完成 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R3_qwen3_coder_next_2603.00729.pdf`〕<br><https://arxiv.org/pdf/2603.00729> | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md`〕<br>旧综合稿：配方矩阵〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R4 | The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence<br>A · 已完成任务 09 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R4_minimax_m2_series_2605.26494.pdf`〕<br><https://arxiv.org/pdf/2605.26494> | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R4_minimax_m2_series.md`〕<br>旧综合稿保留<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R5 | GLM-5: from Vibe Coding to Agentic Engineering<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R5_glm5_agentic_engineering_2602.15763.pdf`〕<br><https://arxiv.org/pdf/2602.15763> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R5b | GLM-5.2: Built for Long-Horizon Tasks<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R5b_glm5_2_blog_zai.pdf`〕<br><https://z.ai/blog/glm-5.2> | 仅综合摘要<br>docs/harness_improve/external_paper_references/pdfs/glm5.2_blog_RL.md〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/glm5.2_blog_RL.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R6a | DeepSeek-V3.2: Pushing the Frontier of Open Large Language Models<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R6_deepseek_v3_2_2512.02556.pdf`〕<br><https://arxiv.org/pdf/2512.02556> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R6b | DeepSeek-V4 Technical Report<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R6_deepseek_v4_pro_DeepSeek_V4.pdf`〕<br><https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/resolve/main/DeepSeek_V4.pdf> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R7a | Kimi K2: Open Agentic Intelligence<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_2507.20534.pdf`〕<br><https://arxiv.org/pdf/2507.20534> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R7b | Kimi K2.5: Visual Agentic Intelligence<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_5_2602.02276.pdf`〕<br><https://arxiv.org/pdf/2602.02276> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R8 | MiniMax-M1: Scaling Test-Time Compute Efficiently with Lightning Attention<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R8_minimax_m1_2506.13585.pdf`〕<br><https://arxiv.org/pdf/2506.13585> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R9 | Composer 2 Technical Report<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/2603.24477v2.pdf`〕<br><https://arxiv.org/pdf/2603.24477> | 仅综合摘要<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R10 | Let It Flow: Agentic Crafting on Rock and Roll, Building the ROME Model within an Open Agentic Learning Ecosystem<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R10_let_it_flow_roll_rock_rome_2512.24873.pdf`〕<br><https://arxiv.org/pdf/2512.24873> | 仅综合摘要<br>docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md〔仓库引用：`docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R11 | RollArt: Disaggregated Multi-Task Agentic RL Training at Scale<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R11_rollart_disaggregated_agentic_rl_2512.22560.pdf`〕<br><https://arxiv.org/pdf/2512.22560> | 仅综合摘要<br>docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md〔仓库引用：`docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R12 | Reinforcement Learning Optimization for Large-Scale Learning: An Efficient and User-Friendly Scaling Library<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R12_roll_framework_2506.06122.pdf`〕<br><https://arxiv.org/pdf/2506.06122> | 仅综合摘要<br>docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md〔仓库引用：`docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R13 | Kimi K3: Open Frontier Intelligence<br>A · 已完成任务 08 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/k3_tech_report.pdf`〕<br><https://arxiv.org/pdf/2607.24653> | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R13_kimi_k3.md`〕<br>旧专题/综合稿保留<br>docs/harness_improve/external_paper_references/k3_agentenv_relevance_notes.md〔仓库引用：`docs/harness_improve/external_paper_references/k3_agentenv_relevance_notes.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R14 | CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/2607.05378v1.pdf`〕<br><https://arxiv.org/pdf/2607.05378> | 需补原文证据<br>knowledge/summary_compaction_rl.md〔仓库引用：`knowledge/summary_compaction_rl.md`〕<br>docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md〔仓库引用：`docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| R15 | Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/2607.07508v1.pdf`〕<br><https://arxiv.org/pdf/2607.07508> | 需补原文证据<br>knowledge/summary_single_rollout_asynchronous_optimization.md〔仓库引用：`knowledge/summary_single_rollout_asynchronous_optimization.md`〕<br>docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md〔仓库引用：`docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md`〕<br>docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| E1 | The Interplay of Harness Design and Post-Training in LLM Agents<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E1_harness_interplay_2606.25447.pdf`〕<br><https://arxiv.org/pdf/2606.25447> | 需补原文证据<br>knowledge/summary_harness_interplay_posttraining.md〔仓库引用：`knowledge/summary_harness_interplay_posttraining.md`〕 |
| E2 | CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks<br>A · 任务 04，已完成 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E2_calibforge_solver_calibration_2608.06352.pdf`〕<br><https://arxiv.org/pdf/2608.06352> | 两稿合并升级，精读及审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md`〕<br>旧稿：summary_calibforge〔仓库引用：`knowledge/summary_calibforge.md`〕、solver_calibration〔仓库引用：`knowledge/summary_calibforge_solver_calibration.md`〕 |
| E3 | Envs-FORGE: Verifier-Pass-Rate-Guided Synthesis Policy for Executable Environments<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E3_envs_forge_2608.14312.pdf`〕<br><https://arxiv.org/pdf/2608.14312> | 需补原文证据<br>knowledge/summary_envs_forge_synthesis_policy.md〔仓库引用：`knowledge/summary_envs_forge_synthesis_policy.md`〕 |
| E4 | Endless Terminals: Procedurally Generated Containerized Terminal Tasks for RL<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E4_endless_terminals_2601.16443.pdf`〕<br><https://arxiv.org/pdf/2601.16443> | 需补原文证据<br>knowledge/summary_endless_terminals.md〔仓库引用：`knowledge/summary_endless_terminals.md`〕 |
| E5 | SWE-smith: Scaling Data for Software Engineering Agents<br>A · 已完成任务 11 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E5_swe_smith_2504.21798.pdf`〕<br><https://arxiv.org/pdf/2504.21798> | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E5_swe_smith.md`〕<br>旧稿保留<br>knowledge/summary_swe_smith.md〔仓库引用：`knowledge/summary_swe_smith.md`〕 |
| E6 | Surge AI: Cross-Domain Transfer from Office-Tool RL to Coding (SWE-Bench Pro)<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E6_surge_office_rl_2608.01604.pdf`〕<br><https://arxiv.org/pdf/2608.01604> | 需补原文证据<br>knowledge/summary_surge_office_rl_transfer.md〔仓库引用：`knowledge/summary_surge_office_rl_transfer.md`〕 |
| E7 | MOPD: Multi-Teacher On-Policy Distillation for Capability Integration in LLM Post-Training<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E7_mopd_multi_teacher_2606.30406.pdf`〕<br><https://arxiv.org/pdf/2606.30406> | 需补原文证据<br>knowledge/summary_mopd_multi_teacher_opd.md〔仓库引用：`knowledge/summary_mopd_multi_teacher_opd.md`〕 |
| E8 | ECHO: Modified Endless Terminals Pipeline (6170 additional terminal tasks)<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E8_echo_terminal_synthesis_2605.24517.pdf`〕<br><https://arxiv.org/pdf/2605.24517> | 仅综合摘要<br>docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/external_env_increment_20260902.md〔仓库引用：`docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/external_env_increment_20260902.md`〕 |
| E9 | On the Design of Qwen3.8-Next Architecture: Evaluation, Efficiency, and Training Stability (Qwen3.8-Flash-Next)<br>C · 背景/备查 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E9_qwen3.8_flash_next_tech_report.pdf`〕<br><https://github.com/QwenLM/Qwen3.8-Flash-Next/blob/main/tech_report.pdf> | 可复用但需更新项目映射<br>knowledge/summary_qwen38_flash_next_architecture.md〔仓库引用：`knowledge/summary_qwen38_flash_next_architecture.md`〕 |
| E10 | Intern-S2-Preview: Scientific Agentic Foundation Model<br>A · 已完成任务 10 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E10_intern_s2_preview_2608.13505.pdf`〕<br><https://arxiv.org/pdf/2608.13505> | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E10_intern_s2_preview.md`〕<br>旧稿保留<br>knowledge/summary_intern_s2_preview.md〔仓库引用：`knowledge/summary_intern_s2_preview.md`〕 |
| E11 | NVIDIA Nemotron-Cascade 2: 30B-A3B MoE, SFT -> Cascade RL (strict on-policy GRPO) -> multi-domain OPD<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E11_nemotron_cascade2_2603.19220.pdf`〕<br><https://arxiv.org/pdf/2603.19220> | 需补原文证据<br>knowledge/summary_nemotron_cascade2.md〔仓库引用：`knowledge/summary_nemotron_cascade2.md`〕 |
| E12 | MiniMax-M3 Technical Report<br>B · 后续重点 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E12_minimax_m3_2606.13392.pdf`〕<br><https://arxiv.org/pdf/2606.13392> | 未找到<br>未找到独立稿指针 |
| E13 | MiMo-V2-Flash Technical Report<br>B · 后续独立任务 | 本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E13_mimo_v2_flash_2601.02780.pdf`〕<br><https://arxiv.org/pdf/2601.02780v2> | 未找到独立稿；本地 v2、31 页已核，见 第三组关联安排〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH3_PLAN.md`〕；术语首创性未核 |

这些标题沿用原始登记的识别名称，部分含解释性副标题（例如 E8）。正式笔记必须从原文恢复正式标题，不能照抄索引标题作为已核论文元数据。

## 2. 已登记的在线入口与 RLVE

GLM-5.3 沿用 R5c。在线入口中的独立文章须各自成文；论文加配套代码可以一篇笔记解释。版本页和团队页是导航，不要求为每页写一份“精读”。

| 编号 | 标题与顺序 | 原始 URL | 复用/同源说明 |
| --- | --- | --- | --- |
| R5c | GLM-5.3: Frontier Coding with Emergent Cyber Capabilities<br>B · 后续重点 | <https://z.ai/blog/glm-5.3> | docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 |
| O01 | SkyRL-Agent: Efficient RL Training for Multi-turn LLM Agent<br>模型：SA-SWE-32B<br>B · 任务 15，已准备 | <https://arxiv.org/abs/2511.16108v1><br><https://github.com/NovaSky-AI/SkyRL> | horizon 专题〔仓库引用：`docs/harness_improve/external_paper_references/sa_swe_horizon_masking_analysis.md`〕；整篇精读准备〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH3_PLAN.md`〕 |
| O02 | DeepSWE<br>C · 背景/备查 | <https://huggingface.co/agentica-org/DeepSWE-Preview> | Agentica 模型，区别于 N15 的 Datacurve benchmark。<br>未找到独立稿指针 |
| O03 | R2E-Gym<br>A · 已完成任务 12 | <https://arxiv.org/abs/2504.07164><br><https://github.com/R2E-Gym/R2E-Gym> | 精读及独立审查完成〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/O03_r2e_gym.md`〕<br>旧稿保留：knowledge/summary_r2e_gym.md〔仓库引用：`knowledge/summary_r2e_gym.md`〕 |
| O04 | SWE-Gym<br>B · 后续重点 | <https://arxiv.org/abs/2412.21139> | 未找到独立稿指针 |
| O05 | Scale-SWE<br>B · 后续重点 | <https://arxiv.org/abs/2602.09892> | 未找到独立稿指针 |
| O06 | SETA<br>C · 背景/备查 | <https://arxiv.org/abs/2607.10891><br><https://github.com/camel-ai/seta> | 未找到独立稿指针 |
| O07 | Endless Terminals<br>B · 后续重点 | <https://arxiv.org/abs/2601.16443><br><https://github.com/kanishkg/endless-terminals> | 与 E4 同一论文；不另开任务。<br>已有独立摘要，笔记见 E4 |
| O08 | AgentRL<br>C · 背景/备查 | <https://arxiv.org/abs/2510.04206><br><https://github.com/THUDM/AgentRL> | 未找到独立稿指针 |
| O09 | OpenClaw-RL SWE-RL<br>C · 背景/备查 | <https://arxiv.org/abs/2603.10165><br><https://github.com/Gen-Verse/OpenClaw-RL/tree/main/swe-rl> | 未找到独立稿指针 |
| O10 | DAPO / Dr.GRPO / RLOO<br>C · 背景/备查 | <https://arxiv.org/abs/2503.14476><br><https://arxiv.org/abs/2503.20783><br><https://arxiv.org/abs/2402.14740> | 此行包含三篇论文，正式产出必须拆成三个文件。<br>未找到独立稿指针 |
| O11 | SWE-rebench V2<br>B · 后续重点 | <https://arxiv.org/abs/2602.23866> | 未找到独立稿指针 |
| O12 | Long-Horizon-Terminal-Bench<br>B · 后续重点 | <https://arxiv.org/abs/2607.08964> | 未找到独立稿指针 |
| O13 | ROLL 团队页面<br>C · 背景/备查 | <https://wwxfromtju.github.io/roll_team.html> | 未找到独立稿指针 |
| O14 | The Bitter Lesson Behind Building Agentic RL in Terminal Environments<br>C · 背景/备查 | <https://www.notion.so/The-Bitter-Lesson-Behind-Building-Agentic-RL-in-Terminal-Environments-2eaddd45837f80c9ad2ed6a15ef3c1a1?pvs=21> | 未找到独立稿指针 |
| O15 | iFlow-ROME 模型卡<br>C · 背景/备查 | <https://huggingface.co/FutureLivingLab/iFlow-ROME> | 未找到独立稿指针 |
| O16 | Prime Intellect: Multi-Agent Systems<br>C · 背景/备查 | <https://www.primeintellect.ai/blog/multi-agent-systems> | 未找到独立稿指针 |
| O17 | verifiers releases<br>C · 背景/备查 | <https://github.com/PrimeIntellect-ai/verifiers/releases> | release 导航；并入对应代码版本专题。<br>verifiers / prime-rl 版本影响分析〔仓库引用：`docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/verifiers_v031_primerl_v090_impact_20260902.md`〕 |
| O18 | prime-rl releases<br>C · 背景/备查 | <https://github.com/PrimeIntellect-ai/prime-rl/releases> | release 导航；并入对应代码版本专题。<br>verifiers / prime-rl 版本影响分析〔仓库引用：`docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/verifiers_v031_primerl_v090_impact_20260902.md`〕 |
| O19 | Prime Intellect: Environments Hub / scaling program<br>B · 后续重点 | <https://www.primeintellect.ai/blog/environments><br><https://www.primeintellect.ai/blog/scaling-environments-program> | 未找到独立稿指针 |
| O20 | HF delta-weight-sync<br>C · 背景/备查 | <https://huggingface.co/blog/delta-weight-sync> | 未找到独立稿指针 |
| O21 | Nemotron-SFT-SWE-v3.5 数据集<br>B · 后续重点 | <https://huggingface.co/datasets/nvidia/Nemotron-SFT-SWE-v3.5> | 未找到独立稿指针 |
| O22 | DeepSeek-V4-Pro-0813 接口敏感性事件<br>C · 背景/备查 | <https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813><br><https://x.com/ZhihuFrontier/status/2088872677692076431> | 未找到独立稿指针 |
| O23 | 蚂蚁 AEnvironment<br>B · 后续重点 | <https://github.com/inclusionAI/AEnvironment> | 未找到独立稿指针 |
| O24 | 字节 Seed + 清华 AIR CUDA-Agent<br>C · 背景/备查 | <https://arxiv.org/abs/2602.24286><br><https://github.com/BytedTsinghua-SIA/CUDA-Agent> | 未找到独立稿指针 |
| O25 | MiniMax M2.1 后训练博客<br>B · 后续重点 | <https://www.minimax.io/news/post-training-experience-and-insights-for-agent-models> | 未找到独立稿指针 |
| O26 | OpenEnv<br>B · 后续重点 | <https://github.com/meta-pytorch/OpenEnv> | 未找到独立稿指针 |
| O27 | Harbor / Harbor Hub<br>B · 后续重点 | <https://github.com/harbor-framework/harbor><br><https://hub.harborframework.com> | Harbor–miles 接入审计〔仓库引用：`docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/harbor_miles_integration_audit_20260902.md`〕 |
| O28 | SWE-rebench 经验谈 + Nebius 基建<br>B · 后续重点 | <https://www.sean-weldon.com/blog/2026-06-08-swe-rebench-lessons-from-evaluating-coding-agents-ibragim-badertdinov-nebius><br><https://nebius.com/blog/posts/infrastructure-behind-swe-rebench> | 未找到独立稿指针 |
| O29 | Meta Muse Glimmer 30B（无 arXiv）<br>C · 背景/备查 | <https://research.meta.ai/blog/introducing-muse-glimmer-open-agentic-model><br><https://huggingface.co/meta-models/Muse-Glimmer-30B> | knowledge/summary_muse_glimmer_30b.md〔仓库引用：`knowledge/summary_muse_glimmer_30b.md`〕 |
| O30 | Thinking Machines Inkling / Inkling-Small 模型卡<br>C · 背景/备查 | <https://thinkingmachines.ai/model-card/inkling/> | 未找到独立稿指针 |
| O31 | 腾讯 Hy4-preview 模型卡<br>C · 背景/备查 | <https://huggingface.co/tencent/Hy4-preview> | 未找到独立稿指针 |
| O32 | Ling-3.0-flash / Tiny 模型卡<br>C · 背景/备查 | <https://huggingface.co/inclusionAI/Ling-3.0-flash> | 未找到独立稿指针 |
| O33 | Kimi K2.5 论文 08-07 更新版<br>C · 背景/备查 | <https://arxiv.org/abs/2602.02276> | R7b 的版本更新线索；不另算论文，本地是否新版待核。<br>未找到独立稿指针 |
| O34 | QwenLM 新仓库观察项<br>C · 背景/备查 | <https://github.com/QwenLM/E-CommerceBench><br><https://github.com/QwenLM/Qwen-MM-Plugins> | 未找到独立稿指针 |
| O35 | RLVE：使用自适应可验证环境扩展语言模型强化学习<br>C · 背景/备查 | <https://arxiv.org/abs/2511.07317><br><https://github.com/Zhiyuan-Zeng/RLVE> | README/manifest 未登记，但已有受跟踪摘要；与 N05 同源。<br>knowledge/summary_rlve.md〔仓库引用：`knowledge/summary_rlve.md`〕 |

## 3. 新增或需要单独登记的候选

以下“阅读问题”来自已有调研线索，不是本轮已核全文结论。读者要到原文判断线索是否成立。N04/N10/N11 等与已知生态有交集，缺的是独立来源与阅读产物，不代表之前完全没研究过该技术。

### N01 KAT-Coder-V2.5 Technical Report

- 顺序：A · 任务 03
- 入口：<https://arxiv.org/abs/2607.05471>
- 核验范围：已完成正式报告及文末技术表精读、独立审查和修订，见 N01 成品〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md`〕。
- 要回答：最贴近项目一的完整新增报告：真实仓库、AutoBuilder、F2P/P2P、near-miss 轨迹、harness randomization、actor-critic PPO、MOPD。重点区分白盒/黑盒训练事实与未隔离的 harness 多样性消融。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:619`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1025`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro模型调查1.md:130`
- 组织：独立逐篇文档；与 Qwen3-Coder-Next、Intern-S2 建交叉引用。

### N02 Toward Training Superintelligent Software Agents through Self-Play SWE-RL（SSR）

- 顺序：C · 背景/备查
- 入口：<https://arxiv.org/abs/2512.18552v3>
- 核验范围：本轮已核 arXiv 标题与摘要。
- 要回答：真实仓库中联合 bug 注入与修复；需精读任务定义、退化题型、无用难题与计算匹配，不能仅凭自博弈名词宣称持续进步。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1023`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1425`
- 组织：独立逐篇文档；与 SWE-smith/Socratic-SWE 归同一任务供给系列。

### N03 Socratic-SWE: Self-Evolving Coding Agents via Trace-Derived Agent Skills

- 顺序：B · 后续重点
- 入口：<https://arxiv.org/abs/2606.07412v1>
- 核验范围：本轮已核 arXiv 标题与摘要。
- 要回答：直接对应历史轨迹→失败模式/技能→新任务→执行验证→更新训练的闭环；核查 solver-gradient alignment 的实际成本与贡献归因。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1024`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1426`
- 组织：独立逐篇文档；不与 SSR 混成一份摘要。

### N04 Prime Intellect 环境资格化与 taskset/harness 分解官方系列

- 顺序：B · 后续重点
- 入口：<https://www.primeintellect.ai/blog/scaling-agentic-rl>；<https://www.primeintellect.ai/blog/verifiers-v1>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：model-free validate、gold-pass/no-op-fail、flakiness、artifact visibility 与隔离评分的边界；代码可用性和训练消融应分别记录。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:623`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:647`；`reference/verifiers/`；`reference/research-environments/`
- 组织：每篇原始文章独立成文；同一来源的代码可以附在对应篇，多个 release / issue 可作版本化专题。

### N05 RLVE: Scaling Up Reinforcement Learning for Language Models with Adaptive Verifiable Environments

- 顺序：C · 背景/备查；与 O35 同源，不重复派工。
- 入口：<https://arxiv.org/abs/2511.07317>；<https://github.com/Zhiyuan-Zeng/RLVE>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：自适应难度、环境数量、held-out 环境消融；提醒其合成推理环境并非真实 SWE，不能直推任务通过率≈50%最优。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:639`；`knowledge/summary_rlve.md`
- 组织：独立逐篇文档，但先审核并扩展已有 summary，避免重复劳动。

### N06 Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops

- 顺序：B · 后续重点
- 入口：<https://arxiv.org/abs/2606.08960>；<https://github.com/few-sh/harden-v0>；<https://github.com/few-sh/terminal-wrench>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：最贴近 verifier 生产质量的对抗修补参照：必须保留 raw hardening 负结果、合法解误杀与 attack/solver 隔离证据。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro2.md:458`
- 组织：论文独立文档；代码与 BenchJack（https://github.com/benchjack/benchjack）作配套附录，不另起工具宣传笔记。

### N07 Reinforcement Learning via Self-Distillation（SDPO）

- 顺序：B · 后续重点
- 入口：<https://arxiv.org/abs/2601.20802v2>
- 核验范围：本轮已核 arXiv 标题与摘要。
- 要回答：反馈条件化自身预测→逐 token 监督；准确区分丰富反馈、自教师、外部 teacher、SFT 和 binary RL。先读清目标再决定长程 SWE 是否适用。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md:161`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1191`
- 组织：独立逐篇文档；与 OPSD/E7 MOPD 构成术语比较表，禁止合称一种算法。

### N08 Self-Distilled Reasoner: On-Policy Self-Distillation for Large Language Models（OPSD）

- 顺序：B · 后续重点
- 入口：<https://arxiv.org/abs/2601.18734v3>
- 核验范围：本轮已核 arXiv 标题与摘要。
- 要回答：特权上下文自教师、teacher/student 采样分布及目标差异；原文主要数学证据，迁移到 SWE 仍待实验。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md:161`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1430`；`reference/prime-rl/src/prime_rl/orchestrator/algo/opsd.py`
- 组织：独立逐篇文档；本地同名算法代码是否对应此论文需另核，不能凭文件名认定。

### N09 多轮 hindsight distillation 论文（原引用未给正式标题）

- 顺序：C · 背景/备查
- 入口：<https://arxiv.org/html/2605.19447v1>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：反馈内容与介入位置改变效果；防止“完整日志给 teacher 一定更好”的错误推断。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1211`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:1431`
- 组织：先恢复正式标题再决定独立逐篇文档；可先作为 SDPO/OPSD 比较附录。

### N10 MiniMax Forge 官方框架与算法技术说明

- 状态：任务 09 完成；独立精读正文〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N10_minimax_forge.md`〕，与 R4 分篇，共用 审查记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/09_R4_N10_review.md`〕
- 入口：<https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm>
- 核验范围：已读官方 HTML 全文、四幅技术图及配套 R4；来源抓取和版本记录见正文 §1。
- 要回答：Windowed FIFO 的吞吐/样本分布权衡与长尾偏差；直接服务有效样本消费/GPU-hour 指标。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md:109`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md:588`；`docs/harness_improve/external_paper_references/pdfs/R4_minimax_m2_series_2605.26494.pdf`
- 组织：每篇原始文章独立成文；同一来源的代码可以附在对应篇，多个 release / issue 可作版本化专题。

### N11 miles agentic rollout/TITO 与当前官方实践

- 顺序：A · 任务 05
- 入口：<https://github.com/radixark/miles>；<https://miles.radixark.com/docs/user-guide/agentic-rollout>
- 核验范围：已完成官方两篇文档、配套关键源码和当前 rh2 采用边界的版本化专题，见 N11 成品〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕。上游 U、集成 I、在线 W 的版本区别见该稿 §1；未做 GPU 实验或最新源码整树审查。
- 要回答：实际推理 token 的 session 运输、REALIGN 与 adapter 采用边界；以本项目 pin 对照上游机制，避免只看新文档就假设当前 adapter 已实现。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md:32`；`reference/miles/docs/user-guide/agentic-rollout.md`；`reference/miles/docs/user-guide/fully-async.md`；`reference/miles-rh2-integration/`
- 组织：合并成版本化官方实践文档；README 仅在 Harbor 条目提到 miles，未建完整参考条目。

### N12 训推一致性与异步静默错误：官方 issue/commit 案例系列

- 顺序：C · 背景/备查
- 入口：<https://github.com/vllm-project/vllm/issues/48305>；<https://github.com/vllm-project/vllm/issues/42259>；<https://github.com/allenai/open-instruct/issues/1473>；<https://github.com/THUDM/slime/commit/7e02052ee454736228464f2f167b0e889c44f10c>；<https://github.com/THUDM/slime/commit/c1dd9ab2422326f97590577ddd7fe3c934dc0c20>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：logprob 语义/数值漂移、completed-group 丢弃、reward/sample DP 错配。问题报告不等于当前仍存在；复核 commit 和生产入口，重在故障证据而非泛平台对比。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:695`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro2.md:579`；`reference/slime/`
- 组织：合并为工程案例系列，每个案例独立版本、复现条件、修复界限；不为每条 issue 创建线程。

### N13 OpenAI coding evaluation 两次质量审计

- 顺序：A · 任务 06
- 入口：<https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/>；<https://openai.com/index/separating-signal-from-noise-coding-evaluations/>
- 核验范围：两篇官方全文、图表和全部交互案例已精读并独立审查，分别见 N13a Verified〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13a_swe_verified_audit.md`〕、N13b signal/noise〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13b_coding_eval_signal_noise.md`〕。
- 要回答：任务质量、污染、测试与题意不一致怎样改变指标解释；对接本项目 held-out、置信区间和 benchmark 降级。不要把某公司停止报告等同于原 benchmark 被全球撤回。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro2.md:609`；`docs/harness_improve/external_paper_references/pdfs/外部pro探索回答粘贴.md`
- 组织：每篇原始文章独立成文；同一来源的代码可以附在对应篇，多个 release / issue 可作版本化专题。

### N14 Terminal-Bench 版本维护：2.1 修补与 4.0 预算协议

- 顺序：B · 后续重点
- 入口：<https://www.tbench.ai/news/terminal-bench-2-1>；<https://github.com/harbor-framework/terminal-bench-2/pull/53>；<https://www.tbench.ai/news/terminal-bench-4-0>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：版本变化会改变任务、资源、timeout 和分数；4.0 的长时预算必须另算，历史 PR 展示修补不等于已经合并。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:775`；`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md:179`；`reference/terminal-bench-pro/`
- 组织：每篇原始文章独立成文；同一来源的代码可以附在对应篇，多个 release / issue 可作版本化专题。

### N15 DeepSWE 评测运行入口（Datacurve；非 Agentica 模型）

- 顺序：B · 后续重点
- 入口：<https://deepswe.datacurve.ai/run>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：复原任务来源、运行方式、版本、成本和 verifier 协议；必须区分 DeepSWE benchmark 与同名 Agentica DeepSWE-Preview 模型。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md:179`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro模型调查1.md:153`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro模型调查2.md`
- 组织：合并成 benchmark 运行协议页；已有 DeepSWE 模型条目不能覆盖此评测入口。

### N16 Harness-Bench: Measuring the Impact of Agent Harnesses on LLM-Based Agents

- 顺序：B · 后续重点
- 入口：<https://arxiv.org/abs/2605.27922>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：固定模型跨 harness 的差异与失败类别；其评测关联不等于具体 harness 机制的因果效果，更不能直接证明多 harness 训练收益。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:615`；`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro模型调查1.md:215`
- 组织：独立逐篇文档；与 E1 Harness Interplay、KAT、Qwen3-Coder-Next 成互证组。

### N17 Natural Emergent Misalignment from Reward Hacking in Production RL 与部分复现

- 顺序：C · 背景/备查
- 入口：<https://arxiv.org/abs/2511.18397>；<https://www.lesswrong.com/posts/2ANCyejqxfqK2obEj/some-natural-emergent-misalignment-from-reward-hacking-in>
- 核验范围：URL 提取自指定本地引用，本轮未联网重验；正式精读前核验。
- 要回答：直接 production coding RL 的 reward hacking 案例；原始训练发现和 AISI 部分复现需分开，不能夸大为普适结论。
- 本地线索：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md:671`
- 组织：以原论文为独立文档，部分复现单列补充章节并核作者身份。

## 4. 旧笔记逐份复用清单

下表列出 18 份逐篇摘要/论文专题、17 个来源；不包含表后另列的综合分析和工程专题。其中 `knowledge/` 16 份均受 Git 跟踪，40–79 行，共 732 行。另有 K3 长文嵌入原始粘贴，单独列在表后。下面的状态是本轮对本地笔记可用性的判断，不是对论文质量的评级。

| 旧稿 | 当前判断 | 主要补充/纠正 |
| --- | --- | --- |
| knowledge/summary_calibforge.md〔仓库引用：`knowledge/summary_calibforge.md`〕 | 需补原文证据 | 双份旧摘要有明确 v1、64×H20 与 API 总成本未公开；保留四态映射，但后续 benchmark 审计主张缺出处。 |
| knowledge/summary_calibforge_solver_calibration.md〔仓库引用：`knowledge/summary_calibforge_solver_calibration.md`〕 | 需补原文证据 | 方法/消融/SFT/成本约束/外推边界齐全；缺页节表定位，仍误写无本地 PDF；与旧稿互补。 |
| knowledge/summary_compaction_rl.md〔仓库引用：`knowledge/summary_compaction_rl.md`〕 | 需补原文证据 | 有版本、本地 PDF、方法结果局限；缺页节表和完整资源栏；首训关闭 compaction 及 FA lineage 映射需按 C 包复核。 |
| knowledge/summary_endless_terminals.md〔仓库引用：`knowledge/summary_endless_terminals.md`〕 | 需补原文证据 | 有 v3 日期、四段管线、PPO、GPU/时长及外部迁移局限；无页节表；ECHO 勘误可复用但仍须按源重新绑证据。 |
| knowledge/summary_envs_forge_synthesis_policy.md〔仓库引用：`knowledge/summary_envs_forge_synthesis_policy.md`〕 | 需补原文证据 | 六动作 MILP、100 环境、token 成本、2×H800 与无 solver-off 消融均有；缺原文锚点，仍误写无 PDF；不得把一次性校准说成在线课程。 |
| knowledge/summary_harness_interplay_posttraining.md〔仓库引用：`knowledge/summary_harness_interplay_posttraining.md`〕 | 需补原文证据 | 有版本、24 配置、1800 H200-hours 和 ALFWorld 外推边界；仅 Limitations 泛定位，缺关键表/图/页。 |
| knowledge/summary_intern_s2_preview.md〔仓库引用：`knowledge/summary_intern_s2_preview.md`〕 | 需补原文证据 | 逐阶段细节丰富，区分并行 expert 与串行、white/black-box、OPD、未披露算力；已映射 miles；但密集算法/数值完全缺页节表锚点。 |
| knowledge/summary_mopd_multi_teacher_opd.md〔仓库引用：`knowledge/summary_mopd_multi_teacher_opd.md`〕 | 需补原文证据 | 目标、同源约束、Qwen 同底座和 miles OPD 路径可复用；仍误写无 PDF；无版本/页节表及硬件/墙钟成本；“只改 advantage 即可”需收敛为待验证工程推论。 |
| knowledge/summary_muse_glimmer_30b.md〔仓库引用：`knowledge/summary_muse_glimmer_30b.md`〕 | 需补原文证据 | 明确仅官方博客/模型卡、无论文与配方，不应排成论文精读；缺存档/版本锚；结果上限锚和激活算力十倍是推论，不能当同预算因果比较。 |
| knowledge/summary_nemotron_cascade2.md〔仓库引用：`knowledge/summary_nemotron_cascade2.md`〕 | 需补原文证据 | SFT/RL/MOPD/数据/预算未知/正文附录冲突均有，复用价值高；没有页节表锚点；同规模≠同底座，严格 on-policy 不足以证明 faithful DIS 必要性。 |
| knowledge/summary_qwen38_flash_next_architecture.md〔仓库引用：`knowledge/summary_qwen38_flash_next_architecture.md`〕 | 可复用但需更新项目映射 | 明确架构报告无后训练配方；有 §2.1.1/§2.2/§4 与原文短引文；需 pin GitHub PDF commit/hash、表图锚点，并更新 Terminination/底座前瞻映射。 |
| knowledge/summary_r2e_gym.md〔仓库引用：`knowledge/summary_r2e_gym.md`〕 | 需补原文证据 | 短稿覆盖 SWE-GEN、hybrid verifier、Prime 审计和边界；无版本/页节表/成本，外部审计缺独立来源链接。 |
| knowledge/summary_rlve.md〔仓库引用：`knowledge/summary_rlve.md`〕 | 需补原文证据 | 环境控制器、实验、H100-hours、局限与 fully-async 映射可用；无版本和页节表；当前项目不建 controller/checkpoint lineage 平台，映射需降为长期候选。 |
| knowledge/summary_single_rollout_asynchronous_optimization.md〔仓库引用：`knowledge/summary_single_rollout_asynchronous_optimization.md`〕 | 需补原文证据 | 有 v1、本地 PDF、四机制、结果、资源不可复现边界；缺页节表/算力明细，32k 首训判断和“DIS 可先实现”应改成现状映射。 |
| knowledge/summary_surge_office_rl_transfer.md〔仓库引用：`knowledge/summary_surge_office_rl_transfer.md`〕 | 需补原文证据 | 方法/363 任务/GSPO/迁移结果及等预算缺失齐全；无页节表/资源总成本；“并行投入有正外部性”仍需保持单实验范围。 |
| knowledge/summary_swe_smith.md〔仓库引用：`knowledge/summary_swe_smith.md`〕 | 需补原文证据 | 有 v2、五策略、50,137 题、295GB、$1360+20h、SFT 非 RL 边界；缺页节表；跨论文“成本低一个量级”未统一成本口径。 |
| docs/harness_improve/external_paper_references/k3_agentenv_relevance_notes.md〔仓库引用：`docs/harness_improve/external_paper_references/k3_agentenv_relevance_notes.md`〕 | 可复用但需更新项目映射 | 首轮相关性筛选，非完整精读；§4/§5/AgentENV 局部证据可用。针对 05/FA-2A 的恢复/平台建议过时；须与 06 最小冷恢复、不建 WAL/no true-resume 首训边界重映射。 |
| docs/harness_improve/external_paper_references/sa_swe_horizon_masking_analysis.md〔仓库引用：`docs/harness_improve/external_paper_references/sa_swe_horizon_masking_analysis.md`〕 | 可复用但需更新项目映射 | draft 专题精读；原文 v1 §4.2 引文、代码 commit/位置、我方事实与 E3 推论分层、数值反例均好。只覆盖 horizon/loss/组语义，不是整篇读完；FA/batch-admission 映射需迁 miles，训练资源还缺。 |

K3 嵌入长文：`docs/harness_improve/external_paper_references/pdfs/外部pro探索回答粘贴.md` 第 2184–3904 行附近，约 1720 行。必须复用其已做的拆解，同时先回原文核算法披露/继承的分歧；这份模型回答不代替一手证据。

其他可复用综合资料与工程专题：

- docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕：配方和缺披露字段骨架，保留事实/代码/博客/推断区分。
- docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md〔仓库引用：`docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md`〕：跨系统职责分解；项目映射须更新。
- docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md〔仓库引用：`docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md`〕：ROLL / ROCK / ROME 入口。
- docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md〔仓库引用：`docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md`〕：SAO、DIS、GRPO、PPO 的本项目专题，不能用我方设计代替论文披露。

- Harbor–miles 接入审计〔仓库引用：`docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/harbor_miles_integration_audit_20260902.md`〕：N11 / O27 可复用的接口与版本分析。
- verifiers / prime-rl 版本影响分析〔仓库引用：`docs/harness_improve/external_paper_references/env_discovery_20260902/analysis/verifiers_v031_primerl_v090_impact_20260902.md`〕：N04 / O17 / O18 可复用的工程专题。

## 5. 暂存而不立即扩充队列

- **CurateEvo / CoEvolve / CLAP**：失败驱动策展的近邻材料；优先读更直接 SWE 的 Socratic-SWE，不为近邻立即增开三篇。 <https://arxiv.org/abs/2607.06140>；<https://arxiv.org/abs/2604.15840>；<https://arxiv.org/abs/2607.01846>
- **RLVE 邻近生成环境 RACES / EvoEnv**：只有项目选择合成环境演化实验才升级。 <https://arxiv.org/abs/2606.12373>；<https://arxiv.org/abs/2605.14392>
- **M2PO / RolloutPipe / DORA / StaleFlow**：异步方法旁证；首轮读 SAO/Forge/miles 与当前 faithful DIS 更直接，避免建立框架百科。 <https://arxiv.org/abs/2510.01161>；<https://arxiv.org/abs/2606.26997>；<https://arxiv.org/abs/2604.26256>；<https://arxiv.org/abs/2601.12784>
- **TRACE / VerMem / ACM / BENCH2ROBUST / agent abstain / GUI / 长期世界模型**：归项目二认知控制、故障策略或更远方向，本轮不排正式精读。
- **LinkedIn gpt-oss agentic RL 与 async RL landscape**：前者可作行业系统案例备查；后者为综述入口而非所有技术结论的一手证据，不能替代所引论文或代码。 <https://huggingface.co/blog/LinkedIn/gpt-oss-agentic-rl>；<https://huggingface.co/blog/async-rl-training-landscape>

## 6. 索引维护问题

- R0/R1/R2 的 `source_url=local_existing` 可从旧索引恢复候选 URL。R1 有不止一个历史 URL，正式阅读选择实际可访问、版本对应的官方入口。
- manifest 顶部更新时间早于 E9–E13 登记日期；README 小节名仍写 E1–E8。这里只记录，不把元数据整理扩成重新下载/哈希工程。
- GLM-5.3 在 README，未在 PDF manifest；没有 PDF 的在线入口不必强行伪装成 PDF 记录。
- manifest 某些 `knowledge_note` 字段带分号后的说明，不应直接把整个字符串当文件路径。
- 部分旧对话只残留工具 citation 标记，没有可解析 URL；恢复不到一手来源时明确保留未知，不以标题猜链接。
- 后续精读完成后，主线程在本目录 README 增加成品链接并更新对应条目的状态。目录/模板/旧稿不是已完成的新笔记。
