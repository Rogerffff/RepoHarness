# Seeded Discovery 中性资料包

生成日期：2026-08-18

这是一份**导航资料包**，不是对方向的推荐顺序。条目出现在这里只说明它曾被项目收集，
不说明它的结论已经复现，也不说明它适合单节点 8×96GB。

请使用官方 URL、固定 revision 和原始论文进行复核。项目内的摘要、证据矩阵和旧 Pro
回答都只是二次线索。

## 1. 现有论文与技术报告入口

表中以 `pdfs/` 开头的本地路径，均相对于
`docs/harness_improve/external_paper_references/`。

| ID | 标题 | 官方或原始入口 | 本地副本 |
| --- | --- | --- | --- |
| R0 | Polar / ProRL-Agent-Server | https://arxiv.org/abs/2605.24220 | `docs/harness_improve/2605.24220v1.pdf` |
| R1 | Microsoft MAI-Thinking-1 | https://microsoft.ai/pdf/mai-thinking-1.pdf | `docs/harness_improve/main_20260602_2.pdf` |
| R2 | NVIDIA Nemotron 3 Ultra Technical Report | https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf | `docs/harness_improve/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf` |
| R3 | Qwen3-Coder-Next Technical Report | https://arxiv.org/abs/2603.00729 | `pdfs/R3_qwen3_coder_next_2603.00729.pdf` |
| R4 | The MiniMax-M2 Series | https://arxiv.org/abs/2605.26494 | `pdfs/R4_minimax_m2_series_2605.26494.pdf` |
| R5 | GLM-5: from Vibe Coding to Agentic Engineering | https://arxiv.org/abs/2602.15763 | `pdfs/R5_glm5_agentic_engineering_2602.15763.pdf` |
| R5b | GLM-5.2: Built for Long-Horizon Tasks | https://z.ai/blog/glm-5.2 | `pdfs/R5b_glm5_2_blog_zai.pdf` |
| R5c | GLM-5.3: Frontier Coding with Emergent Cyber Capabilities | https://z.ai/blog/glm-5.3 | 未镜像 |
| R6a | DeepSeek-V3.2 | https://arxiv.org/abs/2512.02556 | `pdfs/R6_deepseek_v3_2_2512.02556.pdf` |
| R6b | DeepSeek-V4 Technical Report | https://arxiv.org/abs/2606.19348；官方发布导航：https://www.deepseek.com/en/transparency/ | `pdfs/R6_deepseek_v4_pro_DeepSeek_V4.pdf` |
| R7a | Kimi K2: Open Agentic Intelligence | https://arxiv.org/abs/2507.20534 | `pdfs/R7_kimi_k2_2507.20534.pdf` |
| R7b | Kimi K2.5: Visual Agentic Intelligence | https://arxiv.org/abs/2602.02276 | `pdfs/R7_kimi_k2_5_2602.02276.pdf` |
| R8 | MiniMax-M1 | https://arxiv.org/abs/2506.13585 | `pdfs/R8_minimax_m1_2506.13585.pdf` |
| R9 | Composer 2 Technical Report | https://arxiv.org/abs/2603.24477 | `pdfs/2603.24477v2.pdf` |
| R10 | Let It Flow / ROME | https://arxiv.org/abs/2512.24873 | `pdfs/R10_let_it_flow_roll_rock_rome_2512.24873.pdf` |
| R11 | RollArt | https://arxiv.org/abs/2512.22560 | `pdfs/R11_rollart_disaggregated_agentic_rl_2512.22560.pdf` |
| R12 | ROLL framework technical report | https://arxiv.org/abs/2506.06122 | `pdfs/R12_roll_framework_2506.06122.pdf` |
| R13 | Kimi K3: Open Frontier Intelligence | https://arxiv.org/abs/2607.24653 | `pdfs/k3_tech_report.pdf` |
| R14 | CompactionRL | https://arxiv.org/abs/2607.05378 | `pdfs/2607.05378v1.pdf` |
| R15 | Single-Rollout Asynchronous Optimization | https://arxiv.org/abs/2607.07508 | `pdfs/2607.07508v1.pdf` |

## 2. 额外已收集的论文、网页和数据线索

| 条目 | 入口 |
| --- | --- |
| MOPD: Multi-Teacher On-Policy Distillation for Capability Integration in LLM Post-Training | https://arxiv.org/abs/2606.30406 |
| Harness-aware post-training | https://arxiv.org/abs/2606.25447 |
| Turn-level curriculum for on-policy distillation | https://arxiv.org/abs/2604.24005 |
| User simulator human study | https://arxiv.org/abs/2605.09808 |
| Prime Intellect: Scaling Agentic RL | https://www.primeintellect.ai/blog/scaling-agentic-rl |
| Prime Intellect: Multi-Agent Systems | https://www.primeintellect.ai/blog/multi-agent-systems |
| Prime Intellect: verifiers v1 | https://www.primeintellect.ai/blog/verifiers-v1 |
| Hugging Face: Delta Weight Sync | https://huggingface.co/blog/delta-weight-sync |
| NVIDIA Nemotron-SFT-SWE-v3.5 | https://huggingface.co/datasets/nvidia/Nemotron-SFT-SWE-v3.5 |
| SA-SWE / SkyRL-Agent | https://arxiv.org/abs/2511.16108 |
| R2E-Gym | https://arxiv.org/abs/2504.07164 |
| SWE-Gym | https://arxiv.org/abs/2412.21139 |
| Scale-SWE | https://arxiv.org/abs/2602.09892 |
| SETA | https://arxiv.org/abs/2607.10891 |
| Endless Terminals | https://arxiv.org/abs/2601.16443 |
| AgentRL | https://arxiv.org/abs/2510.04206 |
| OpenClaw-RL SWE-RL | https://arxiv.org/abs/2603.10165 |
| Long-Horizon-Terminal-Bench | https://arxiv.org/abs/2607.08964 |

## 3. 开源代码与环境项目起点

以下 revision 是本地参考库当前指向的 commit，不保证就是上游最新版本。查看实际能力时应
同时检查上游当前 release/branch，并明确实际引用的 revision。

| 项目 | 官方仓库 | 本地参考 revision |
| --- | --- | --- |
| slime | https://github.com/THUDM/slime | `e848052a65092ec49e4dd2b5d44d0787c3a327a4` |
| verl | https://github.com/verl-project/verl | `ba8cfb6d585b2f0a13f7cc84aac761955d9cc3e1` |
| PrimeIntellect verifiers | https://github.com/PrimeIntellect-ai/verifiers | `5885ab9c54152e707af2a11797aa52c3eb1752da` |
| PrimeIntellect prime-rl | https://github.com/PrimeIntellect-ai/prime-rl | `df2acf4874af8be0300e06a4f45e65a78c305229` |
| PrimeIntellect research-environments | https://github.com/PrimeIntellect-ai/research-environments | `3093d72a3b8b3720f46d58a9bedab84b96019ed9` |
| ROLL | https://github.com/alibaba/ROLL | `c7e37935708760d00b8997029869340470986a47` |
| ROCK | https://github.com/alibaba/ROCK | `8c5e3c3da51373314f8b0b5aaa5a25c04345b5fa` |
| AgentEnv | https://github.com/kvcache-ai/AgentEnv | `6296bc4be7ad79eb3a278eb5264ef011c341adf5` |
| ProRL-Agent-Server | https://github.com/NVIDIA-NeMo/ProRL-Agent-Server | `f0e8343a7870abf6ec2366890f685881ceab92cb` |
| OpenAI Codex | https://github.com/openai/codex | `61cbf3574eca870df6fa7f49648ec7e001901b5a` |
| DeepSeek Harness | https://github.com/deepseek-ai/deepseek-harness | `47f943859bef60e4160492346772ded9b24f765a` |
| PI coding agent / harness | https://github.com/earendil-works/pi | `b1efcf7d7c5d7394fbb12ede0174e04d39ee7004` |
| Prime Agent | https://github.com/PrimeIntellect-ai/prime-agent | `b9a4461149419156599d60174dddf15458e2b9ee` |
| NVIDIA NeMo RL | https://github.com/NVIDIA-NeMo/RL | 请核验当前 release |
| NVIDIA Nemotron recipes | https://github.com/NVIDIA-NeMo/Nemotron | 请核验当前 release |
| NVIDIA Data Designer | https://github.com/NVIDIA-NeMo/DataDesigner | 请核验当前 release |
| SkyRL | https://github.com/NovaSky-AI/SkyRL | 请核验论文对应 revision |
| R2E-Gym | https://github.com/R2E-Gym/R2E-Gym | 请核验论文对应 revision |
| OpenClaw-RL | https://github.com/Gen-Verse/OpenClaw-RL | 请核验论文对应 revision |

代码库中存在某个类、参数或示例，只能证明“代码表面存在”。如果要声称已有模型完成训练或
该机制有能力收益，必须另外找到训练记录、报告或受控实验。

`OpenCode` 是 owner 另一个关注的白盒 harness 线索；旧 `sst/opencode` 入口当前会导向
`https://github.com/anomalyco/opencode`，但本资料包没有冻结其 commit 和 license 状态。请先核实当前
官方身份、release/commit 和授权，再把它当作开源实现证据。

## 4. 项目内二次线索

以下文件可用来找参考文献，不能代替一手资料：

| 文件 | 使用限制 |
| --- | --- |
| `docs/harness_improve/external_paper_references/README.md` | 资料索引，不是综述终稿；其第 4 节的旧主设计文档引用已过时。 |
| `docs/harness_improve/external_paper_references/manifest.json` | 用于本地副本 digest 和 URL 定位；个别旧项没有官方 URL。 |
| `docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md` | 项目内证据矩阵；对承重事实必须回到原始论文或代码。 |
| `docs/harness_improve/external_paper_references/pdfs/外部pro探索回答粘贴.md` | 至少五份历史 Pro 报告的拼接，旧检索截止日为 2026-07-27；只用作线索库，不引用其结论。 |

首次 Seeded Discovery 已经可以只使用本资料包中的官方链接。不建议一开始上传全部 PDF
和整份旧 Pro 报告，否则容易让旧分类占满上下文。
