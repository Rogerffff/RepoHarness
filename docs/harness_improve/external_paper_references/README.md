# Agentic RL 外部技术报告与参考代码索引

本文持续记录 RepoHarness 重定位阶段使用的外部 paper、网页短报告、技术报告和参考代码库，以及它们的本地组织方式、阅读重点和后续用途。它不是论文综述终稿，而是一个面向后续架构设计和代码实现的资料入口。

## 1. 文件组织原则

本次新增资料统一放在：

```text
docs/harness_improve/external_paper_references/
  README.md
  manifest.json
  infra_mapping_for_repoharness_rl_serving.md
  pdfs/
```

已有文件暂不移动，避免打断现有文档引用：

```text
docs/harness_improve/2605.24220v1.pdf
docs/harness_improve/main_20260602_2.pdf
docs/harness_improve/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf
```

后续新增外部报告默认放入 `external_paper_references/pdfs/`，再更新 `manifest.json` 和本文索引。若以后需要彻底整理，可以单独做一次“迁移并修正引用”的文档整理任务，不在本次下载任务中移动旧文件。

外部网页短报告和参考代码库不放入 `pdfs/`。它们直接在本文登记 URL 或 `reference/` 路径，并标明它们对 RepoHarness 的参考价值。原因是 RepoHarness 的设计判断不只来自论文，也来自真实训练框架、真实智能体运行时和真实开源模型发布说明。

## 2. 第一批报告清单

| 编号 | 报告 | 本地文件 | RepoHarness 阅读重点 |
| --- | --- | --- | --- |
| R0 | Polar / ProRL-Agent-Server 论文 | `docs/harness_improve/2605.24220v1.pdf` | Rollout-as-a-service、gateway、model API capture、Trace / Trajectory、prefix merging、reward attribution、外部黑盒 harness 如何低侵入进入 RL。 |
| R1 | Microsoft MAI-Thinking-1 | `docs/harness_improve/main_20260602_2.pdf` | 环境生产流水线、hill-climbing machine、agentic climb、SEE 等价沙箱、empty patch / golden patch 验证、评分隔离、训练基础设施。 |
| R2 | NVIDIA Nemotron 3 Ultra | `docs/harness_improve/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf` | SFT -> RLVR -> MOPD recipe、多环境 RLVR、specialized teachers、teacher logprobs、MoE routing replay、失败归因、sandbox / tool calling 故障。 |
| R3 | Qwen3-Coder-Next Technical Report | `docs/harness_improve/external_paper_references/pdfs/R3_qwen3_coder_next_2603.00729.pdf` | coding-agent 数据、verifiable coding tasks、executable environments、SWE / Terminal-Bench 训练与评测、agentic training 对 RepoHarness taskset / environment 设计的启发。 |
| R4 | MiniMax-M2 Series | `docs/harness_improve/external_paper_references/pdfs/R4_minimax_m2_series_2605.26494.pdf` | Forge、agent-driven data pipeline、verifiable trajectories、executable workspace、artifact-aligned reward、windowed-FIFO、prefix-tree merging、training / inference / agent 解耦。 |
| R5 | GLM-5: from Vibe Coding to Agentic Engineering | `docs/harness_improve/external_paper_references/pdfs/R5_glm5_agentic_engineering_2602.15763.pdf` | 异步 agent RL、generation / training 解耦、slime 相关异步训练基础设施、多环境 agentic RL、从 vibe coding 到 agentic engineering 的定位。 |
| R5b | GLM-5.2: Built for Long-Horizon Tasks | `docs/harness_improve/external_paper_references/pdfs/R5b_glm5_2_blog_zai.pdf`；来源：`https://z.ai/blog/glm-5.2`；辅助入口：`https://github.com/zai-org/GLM-5` 和 `https://docs.z.ai/guides/llm/glm-5.2` | GLM-5.2 网页短报告的本地 PDF 快照。重点关注长程工程任务、slime 的多种 rollout 形态、critic-PPO、CompactionRL、并行 OPD、anti-hack，以及 serving / rollout 配置复用。它不是完整可复现训练配方，具体算法需和 R14/R15 交叉核验。 |
| R5c | GLM-5.3: Frontier Coding with Emergent Cyber Capabilities | 官方博客：`https://z.ai/blog/glm-5.3`（2026-08-14，URL 登记，未制作本地 PDF） | GLM-5.3 沿用 GLM-5.2 base model，官方将增益归因于扩大 post-training。重点关注：从真实工作模式合成长程可执行环境；judge agent 验证任务可解性；verifier 不接触 reference solution，并用 solver trajectory 查找 reward shortcut；`oracle / no-op / unsolved-state` 三类检查；继续使用 `SAO + compaction`；slime 的 Megatron / SGLang / data-buffer 单数据流；top-p mask、top-k / full-vocabulary OPD、R3-style 与 full numerical alignment；面向长尾 rollout 的 router/slime 联合调度和 workload-aware prefill/decode、并发参数选择。博客声称 logprob 差达到 `1e-7` 量级、长程 coding RL 吞吐提升超过 `2.3x`，但没有给出完整实验配置，必须视为官方报告值并结合 slime 代码和本项目实测核验。 |
| R6a | DeepSeek-V3.2 | `docs/harness_improve/external_paper_references/pdfs/R6_deepseek_v3_2_2512.02556.pdf` | agentic task synthesis、large-scale tool-use data generation、scalable RL protocol、DeepSeek Sparse Attention、长上下文与 agent 性能结合。 |
| R6b | DeepSeek-V4 | `docs/harness_improve/external_paper_references/pdfs/R6_deepseek_v4_pro_DeepSeek_V4.pdf` | million-token context、agentic coding、OPD / distillation / sandbox 相关线索、DSec 类 sandbox 基础设施参考。 |
| R7a | Kimi K2 | `docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_2507.20534.pdf` | large-scale agentic data synthesis、joint RL、agentic intelligence、SWE-Bench / Tau2 / ACEBench 等 agentic benchmark 结果。 |
| R7b | Kimi K2.5 | `docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_5_2602.02276.pdf` | Visual Agentic Intelligence、Agent Swarm、parallel agent orchestration、PARL、子 agent 创建和任务委托。 |
| R8 | MiniMax-M1 | `docs/harness_improve/external_paper_references/pdfs/R8_minimax_m1_2506.13585.pdf` | 1M context、Lightning Attention、CISPO、test-time compute、sandbox-based SWE RL、长上下文 reasoning RL 到 agent RL 的过渡。 |
| R9 | Composer 2 Technical Report | `docs/harness_improve/external_paper_references/pdfs/2603.24477v2.pdf` | Cursor Research 的 agentic software engineering 模型报告。重点关注真实 Cursor harness 中训练、减少 train-test mismatch、等价工具和结构、真实大代码库任务、异步强化学习、大规模端到端编码性能，以及产品级 coding agent 如何把 deployed harness 直接纳入训练。 |
| R10 | Let It Flow: Agentic Crafting on Rock and Roll | `docs/harness_improve/external_paper_references/pdfs/R10_let_it_flow_roll_rock_rome_2512.24873.pdf` | 阿里 ALE 生态总报告。重点关注 ROLL 训练框架、ROCK 沙箱环境管理、iFlow CLI agent runtime、Terminal-Bench-Pro、ROME 模型、Agent Native Mode、ModelProxyService、训练和部署 harness 一致性。 |
| R11 | RollArt: Disaggregated Multi-Task Agentic RL Training at Scale | `docs/harness_improve/external_paper_references/pdfs/R11_rollart_disaggregated_agentic_rl_2512.22560.pdf` | 多任务 agentic RL 系统论文。重点关注轨迹级异步 rollout、LLMProxy、EnvManager、SampleBuffer、serverless reward、硬件亲和调度、bounded-staleness 权重同步、长尾环境和失败环境处理。 |
| R12 | ROLL framework technical report | `docs/harness_improve/external_paper_references/pdfs/R12_roll_framework_2506.06122.pdf` | ROLL 训练框架技术报告。重点关注 Ray 多角色分布式架构、Parallel Worker、Rollout Scheduler、Environment Worker、Reward Worker、AutoDeviceMapping、vLLM / SGLang / Megatron / FSDP2 集成和 agentic pipeline。 |
| R13 | Kimi K3: Open Frontier Intelligence | `docs/harness_improve/external_paper_references/pdfs/k3_tech_report.pdf` | SFT 冷启动、九个 RL expert 与 MOPD、固定 `K` 的 partial rollout、跨迭代暂停恢复、reasoning-effort token budget、统一可组合 harness、AET verifier 隔离、AgentENV 和 rollout auto-throttling。注意 K3 未披露 PPO / GRPO / DIS 公式，partial rollout 也不是 wall-clock 截断评分。 |
| R14 | CompactionRL | `docs/harness_improve/external_paper_references/pdfs/2607.05378v1.pdf` | context compaction 作为可训练策略、summary / execution segment、token-level loss normalization、cross-trajectory GAE，以及长轨迹切段后 reward 和 loss 分母如何保持一致。 |
| R15 | Single-Rollout Asynchronous Optimization（SAO） | `docs/harness_improve/external_paper_references/pdfs/2607.07508v1.pdf` | 用 single-rollout sampling 解除异步训练中的同题组等待，结合 critic、Skip-Observation GAE 和 double-sided token clipping 处理 credit assignment 与 off-policy。它是 GRPO 之后的算法候选，不是当前首训链的开箱即用替代。 |

### 2.0.1 环境层专项批次 E1-E8（2026-09-02，`env_discovery_20260902`）

下面这批 PDF 是环境层第二阶段调查（`env_discovery_20260902/`）的承重来源，每篇配套一份 `knowledge/` 单篇精读。它们聚焦环境生产、资格化、第二可验证域和能力整合，不改变 R0-R15 的主线定位。

| 编号 | 报告 | 本地文件 | 配套精读 | RepoHarness 阅读重点 |
| --- | --- | --- | --- | --- |
| E1 | The Interplay of Harness Design and Post-Training in LLM Agents（2606.25447） | `pdfs/E1_harness_interplay_2606.25447.pdf` | `knowledge/summary_harness_interplay_posttraining.md` | harness 信息量差距 post-training 抹不平、harness 必须训练时就位、ALFWorld 24 组受控配置、约 1800 H200-hours、单环境局限。B 线（多 harness）最直接受控证据。 |
| E2 | CalibForge: Adversarial Solver Calibration（2608.06352） | `pdfs/E2_calibforge_solver_calibration_2608.06352.pdf` | `knowledge/summary_calibforge_solver_calibration.md`（另有旧版 `summary_calibforge.md`） | solver-relative 校准 single/multi/contrastive 四档、5431 任务、匹配 1300 消融、64×H20 全参 SFT（非 RL）、solver-style leakage 风险。A 线 learnability 探针参照。 |
| E3 | Envs-FORGE: 合成动作策略（2608.14312） | `pdfs/E3_envs_forge_2608.14312.pdf` | `knowledge/summary_envs_forge_synthesis_policy.md` | verifier 通过率→逐 seed 六动作 MILP 合成策略、同步改写五件套、Qwen3.5-35B tb-core +9.2、DataArc-SynData-Toolkit 开源。E-Wave4 生成式合成最新参照。 |
| E4 | Endless Terminals（2601.16443） | `pdfs/E4_endless_terminals_2601.16443.pdf` | `knowledge/summary_endless_terminals.md` | 四段全自动管线（描述→容器+precondition→completion→pass@16 可解性过滤）产 3255 terminal 任务、vanilla PPO 10.7%→53.3%、TB2.0 迁移有限。域 2 terminal 供给侧参照。 |
| E5 | SWE-smith（2504.21798，NeurIPS 2025 D&B Spotlight） | `pdfs/E5_swe_smith_2504.21798.pdf` | `knowledge/summary_swe_smith.md` | 128 仓五策略注入 breaking 变更产 50137 实例、环境仅 295GB（约逐任务建环境 1/500）、SWE-agent-LM-32B 40.2%。E-Wave4 成本最低的注入式扩容路线。 |
| E6 | Surge 办公 RL 跨域迁移（2608.01604） | `pdfs/E6_surge_office_rl_2608.01604.pdf` | `knowledge/summary_surge_office_rl_transfer.md` | 363 个零 SWE 办公 MCP 任务 SFT+GSPO、SWE-Bench Pro pass@1 +5.8pp 跨域迁移、无等预算对照。"第二域投入不是零和"直接证据。 |
| E7 | MOPD: Multi-Teacher On-Policy Distillation（2606.30406） | `pdfs/E7_mopd_multi_teacher_2606.30406.pdf` | `knowledge/summary_mopd_multi_teacher_opd.md` | student 自采样 + 按域路由冻结 teacher 逐 token reverse-KL、同源约束（KL 0.04 vs 异源 0.19、异源 top-k 约 18 步发散）、Qwen3-30B-A3B 同底座、MiMo 309B 小回退。C 线 OPD/MOPD 核心。 |
| E8 | ECHO: 改进 Endless Terminals 管线（2605.24517） | `pdfs/E8_echo_terminal_synthesis_2605.24517.pdf` | —（见 `env_discovery_20260902/analysis/external_env_increment` 更正注） | 用改进的 Endless Terminals 管线再产 6170 terminal 任务。登记它是为纠正外部增量分析里"6170 任务"曾误引为 2602.21193（实为 NVIDIA Nemotron-Terminal，SFT 路线）。 |
| E9 | Qwen3.8-Flash-Next 架构报告（2026-08-26，GitHub PDF 非 arXiv） | `pdfs/E9_qwen3.8_flash_next_tech_report.pdf` | `knowledge/summary_qwen38_flash_next_architecture.md` | 125B-A6B + 51B 外置 n-gram 表；GDN 混合 + QSA 稀疏注意力 + Gated Residual + Muon。**无 post-training 配方**；对我们的价值 = 三个"预训练指标会骗人"实证（NoPE 后训练无终止生成率升高 / 稀疏 GR 读后训练退化 / n-gram loss 降但下游饱和）+ 结论自陈最紧瓶颈是"能预测 post-training 排序的廉价探针"；GDN+QSA 类底座对训推一致性（tape/logprob）的前瞻负担。 |
| E10 | Intern-S2-Preview（上海 AI Lab，2608.13505，2026-08-20） | `pdfs/E10_intern_s2_preview_2608.13505.pdf` | `knowledge/summary_intern_s2_preview.md` | 2026-08 窗口内唯一"agentic RL + OPD 全链路"完整报告：SFT → 可扩展多任务 RL → **黑盒/白盒 agentic RL** → on-policy distillation，接多 agent 框架与沙箱环境。黑/白盒分工对口 B 线，OPD 段对口 C 线。 |
| E11 | NVIDIA Nemotron-Cascade 2（2603.19220，v2 2026-03-22） | `pdfs/E11_nemotron_cascade2_2603.19220.pdf` | `knowledge/summary_nemotron_cascade2.md` | **30B-A3B MoE + GRPO 严格 on-policy + 多域 OPD——与本项目规模/算法/蒸馏三重精确命中**。Cascade RL 分域配方与训练预算披露。窗口外（3 月）定向补录。 |
| E12 | MiniMax-M3 技术报告（2606.13392，2026-06-11） | `pdfs/E12_minimax_m3_2606.13392.pdf` | —（未精读） | 补录：库内此前只有 M1/M2 系。含 SWE-bench Pro 59 与 Long-Horizon-Terminal-Bench 结果。 |
| E13 | MiMo-V2-Flash 技术报告（2601.02780，2025-12） | `pdfs/E13_mimo_v2_flash_2601.02780.pdf` | —（未精读） | 补录：**MOPD 术语出处**，此前只经 pro 分析文档与证据矩阵间接引用、PDF 未镜像。与 E7（MOPD 算法论文）配对。routing replay / partial rollout / stale-aware TIS / git hacking 能力回退。 |

## 2.1 参考代码库清单

下面这些 `reference/` 仓库不是论文，但和上述报告同等重要。它们用于校验高层设计是否能落到真实代码结构、训练框架、推理服务、工具运行时和环境抽象上。多数仓库已经有 `AGENTS.md` 或 `CLAUDE.md` 快速导览；后续阅读时应优先打开这些导览，再进入源码细节。

| 参考仓库 | 本地路径 | 快速导览 | RepoHarness 阅读重点 |
| --- | --- | --- | --- |
| Polar / ProRL-Agent-Server | `reference/ProRL-Agent-Server/` | `reference/ProRL-Agent-Server/AGENTS.md`、`reference/ProRL-Agent-Server/CLAUDE.md` | rollout server、gateway node、model API proxy、runtime、黑盒 harness capture、trajectory builder、slime bridge。用于理解黑盒 harness 如何通过模型 API 边界捕获训练轨迹。 |
| verl | `reference/verl/` | `reference/verl/AGENTS.md`、`reference/verl/CLAUDE.md` | HybridFlow、DataProto、RayPPOTrainer、AgentLoop、FullyAsyncRollouter、MessageQueue、vLLM / SGLang rollout、staleness 和训练后端消费契约。用于近期 RepoHarness trainer-native 接入。 |
| slime | `reference/slime/` | `reference/slime/AGENTS.md`、`reference/slime/CLAUDE.md`、`reference/slime/AGENT.md` | 训练后端 + agentic rollout substrate + coding-agent 黑盒训练参考。重点看 SGLang-native rollout、Megatron 训练、`custom_generate`、`Sample` fan-out、`TrajectoryManager`、Claude Code / Codex harness、SGLang token capture、OPD、top-p replay、权重同步、partial rollout 和 fully async worker。它不替代 RepoHarness 的 Environment / TaskSet / Rubric / training eligibility / artifact governance。 |
| PrimeIntellect verifiers | `reference/verifiers/` | `reference/verifiers/AGENTS.md`、`reference/verifiers/CLAUDE.md` | Taskset / Harness / Env / Task / State / User / Sandbox / Artifact / Rubric ownership，以及 BYO harness / environment composition。用于 RepoHarness taskset、environment、rollout、trainer 解耦。 |
| PrimeIntellect prime-rl | `reference/prime-rl/` | `reference/prime-rl/AGENTS.md`、`reference/prime-rl/CLAUDE.md`、`reference/prime-rl/AGENT.md` | PrimeIntellect 的大规模异步强化学习训练框架，和 verifiers / renderers / research-environments 组成完整训练栈。重点看 Orchestrator、EnvServer / EnvClient 接入、TrainClient / renderer token faithful rollout、Trace 到 TrainingSample 的转换、advantage / loss routing、rollout filter、TrainingBatch transport、WeightWatcher 权重同步、policy staleness 和 vLLM inference pool。用于对照 verl、slime、ROLL 这些训练后端如何消费环境服务产出的轨迹。 |
| PrimeIntellect research-environments | `reference/research-environments/` | `reference/research-environments/AGENTS.md`、`reference/research-environments/CLAUDE.md` | 可安装研究环境、SWE tasksets、OpenCode harness、ComposableEnv、sandbox、rubric / verifier、artifact 组织方式。用于任务环境生产和组合式环境设计。 |
| PrimeIntellect renderers | `reference/renderers/` | `reference/renderers/AGENTS.md`、`reference/renderers/CLAUDE.md` | token-faithful renderer、render_ids、parse_response、bridge_to_next_turn、tool call / thinking / multimodal token 对齐。用于避免 retokenization drift 和训练 token provenance 断裂。 |
| mini-swe-agent | `reference/mini-swe-agent/` | `reference/mini-swe-agent/README.md`、`reference/mini-swe-agent/docs/` | 极简 bash-only 软件工程智能体基线。用于对照“最小可用 agent harness”边界，避免 RepoHarness 过早复杂化，也用于评估结构化工具和 bash 工具之间的取舍。 |
| Claude Code TypeScript 参考源码 | `reference/claude-code-typescript-src/` | `reference/claude-code-typescript-src/AGENTS.md`、`reference/claude-code-typescript-src/CLAUDE.md` | 真实开发代理的工具编排、权限、hook、MCP、任务、压缩、会话和产品态 agent loop。用于理解白盒 harness 应如何控制工具和权限。 |
| OpenAI Codex 参考源码 | `reference/codex/` | `reference/codex/AGENTS.md` | 终端执行、受控补丁、统一事件协议、沙箱审批、app-server、SDK 和工具路由。用于理解真实 coding agent 的事件审计、权限和可恢复运行时。 |
| Alibaba ROLL | `reference/ROLL/` | `reference/ROLL/CLAUDE.md`、`reference/ROLL/README.md`、`reference/ROLL/docs_roll/docs/Overview.mdx` | 阿里大规模 RL 训练框架。重点看 agentic pipeline、RolloutScheduler、GroupQueue、Environment Worker、Reward Worker、Reward Scheduler、LLM proxy、device_mapping、rollout dump/mock、vLLM / SGLang / Megatron / FSDP2 接入。 |
| Alibaba ROCK | `reference/ROCK/` | `reference/ROCK/CLAUDE.md`、`reference/ROCK/README.md`、`reference/ROCK/examples/install-agents/README.md` | 沙箱环境管理和 agent 执行服务。重点看 Admin / Worker / Rocklet / EnvHub、Sandbox SDK、GEM API、sandbox lifecycle、agent install/run、ModelService、OpenAI-compatible proxy record/replay、网络和 runtime 隔离。 |
| iFlow CLI | `reference/iflow-cli/` | `reference/iflow-cli/README.md`、`reference/iflow-cli/docs_cn/` | 真实 terminal agent runtime 参考。重点看权限模式、Sub Agent、Task 工具、上下文压缩、hooks、workflow、checkpoint 和 OpenAI-compatible API 配置。注意该仓库声明 iFlow CLI 于 2026-04-17 停止服务，因此只作为设计参考，不建议作为长期依赖。 |
| Terminal-Bench-Pro | `reference/terminal-bench-pro/` | `reference/terminal-bench-pro/README.md`、各 task 的 `instruction.md` / `task.toml` / `tests/` | 终端环境 benchmark 和任务包参考。重点看 400 个任务、公开 / 私有拆分、8 个领域、任务 metadata、环境资源声明、verifier timeout、测试布局和 Harbor / Terminal-Bench 2.0 格式兼容。 |
| AgentENV | `reference/AgentEnv/` | `reference/AgentEnv/CLAUDE.md`、`reference/AgentEnv/docs/src/` | K3 使用的 Firecracker microVM 环境运行时。重点看 pause / resume、incremental snapshot、同节点 fork、持久化 artifact、生命周期指标和 E2B 兼容 API。它不拥有 hidden verifier、command policy、token capture、eligibility 或 artifact visibility；当前控制面认证和 domain 网络策略也不足以替代 RepoHarness SWE-Safety。slime 接入还需要 image-to-template 映射或薄 create adapter，不能只改 `E2B_API_URL`。 |

## 2.2 统一训练配方证据矩阵

跨报告比较模型、数据、harness、预算、终止、组统计、reward、loss、异步、
staleness、硬件规模和可复现性的统一入口：

```text
docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md
```

该矩阵明确区分“报告精确披露”“官方代码事实”“工程推断”和“未披露”。
需要判断训练参数或终止语义时，应先查矩阵，再回到原始 PDF / 代码位置；
不要从本文的阅读重点反推外部团队使用了某个未公开算法或默认参数。

### 2.2.1 已有本地二次分析入口

下面这些文件是对一手报告或代码的项目内分析，不是新增的一手技术报告。单独
列出它们是为了避免后续只看到原始 PDF，却遗漏已经完成的源码核验和边界分析：

| 主题 | 本地分析 | 对应一手来源 |
| --- | --- | --- |
| Kimi K3 与 AgentENV | `docs/harness_improve/external_paper_references/k3_agentenv_relevance_notes.md` | R13、`reference/AgentEnv/` |
| SA-SWE horizon masking | `docs/harness_improve/external_paper_references/sa_swe_horizon_masking_analysis.md` | SA-SWE / SkyRL-Agent 论文与代码 |
| GLM-5.2 Agentic RL 摘录 | `docs/harness_improve/external_paper_references/pdfs/glm5.2_blog_RL.md` | R5b |
| SAO、CompactionRL 与当前 PPO / GRPO / DIS 关系 | `docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md` | R14、R15 |

## 2.3 在线专项论文、模型卡和代码

以下来源本轮没有全部镜像成 PDF，但已经按统一字段登记进训练配方证据矩阵。
它们优先使用论文、官方模型卡和官方仓库，不使用第三方文章作为训练事实的
唯一依据。

| 来源 | 官方入口 | 主要用途 |
| --- | --- | --- |
| SA-SWE / SkyRL-Agent | `https://arxiv.org/abs/2511.16108`、`https://github.com/NovaSky-AI/SkyRL` | Qwen3-32B、R2E-Gym、`n=8`、32K / 50 turns、LOO，以及“horizon 保留组 reward / advantage、屏蔽自身梯度”的主要成功配方锚点。 |
| DeepSWE | `https://huggingface.co/agentica-org/DeepSWE-Preview` | direct RL、R2E-Gym、Compact Filtering、二元 verifier reward 和 20 分钟 generation timeout 参考；训练代码公开不完整。 |
| R2E-Gym | `https://arxiv.org/abs/2504.07164`、`https://github.com/R2E-Gym/R2E-Gym` | executable SWE environment、RFT/SFT 轨迹生产、任务和环境数据源；不是在线 GRPO 配方。 |
| SWE-Gym | `https://arxiv.org/abs/2412.21139` | 2438 个真实 SWE 任务、rejection-sampling fine-tuning 与有限自产数据实验。 |
| Scale-SWE | `https://arxiv.org/abs/2602.09892` | Qwen3-30B-A3B 的大规模 coding SFT、长 context 与 teacher trajectory 证据；不是 RL。 |
| SETA | `https://arxiv.org/abs/2607.10891`、`https://github.com/camel-ai/seta` | terminal GRPO、部分测试 reward、异步/staleness 和超时配置；当前仓库 main 与论文组语义存在冲突，需按版本核验。 |
| Endless Terminals | `https://arxiv.org/abs/2601.16443`、`https://github.com/kanishkg/endless-terminals` | shell-only terminal PPO + critic 的可执行对照；环境和任务短于真实 Claude Code SWE。 |
| AgentRL | `https://arxiv.org/abs/2510.04206`、`https://github.com/THUDM/AgentRL` | 多任务 fully async、ready queue、group-aware buffer、权重传输与跨策略数据参考。 |
| OpenClaw-RL SWE-RL | `https://arxiv.org/abs/2603.10165`、`https://github.com/Gen-Verse/OpenClaw-RL/tree/main/swe-rl` | slime + Mini-SWE-Agent + 远程容器的最新工程接线；尚无足够公开结果证明其为成功 SWE 配方。 |
| DAPO / Dr.GRPO / RLOO | `https://arxiv.org/abs/2503.14476`、`https://arxiv.org/abs/2503.20783`、`https://arxiv.org/abs/2402.14740` | overlong shaping、固定 token denominator、LOO 的同策略 i.i.d. 前提；用于准确命名当前算法。 |
| SWE-rebench V2 | `https://arxiv.org/abs/2602.23866` | 32K+ 多语言 executable tasks 与更大候选集的环境生产参考，归数据流水线，不是首训 trainer 配方。 |
| Long-Horizon-Terminal-Bench | `https://arxiv.org/abs/2607.08964` | 分钟到小时级 terminal 任务、细粒度 partial credit 与真实 wall-clock / token 分布参考，适合后续长程评测和预算校准。 |

## 2.4 ROLL 生态辅助网页和模型卡

下面这些资料不是本地 PDF 或代码仓库，但应该和 R10-R12 一起阅读：

| 资料 | URL | RepoHarness 阅读重点 |
| --- | --- | --- |
| ROLL 团队页面 | `https://wwxfromtju.github.io/roll_team.html` | 团队和项目谱系入口，用于追踪 ROLL / ROCK / ROME / Terminal-Bench-Pro 后续更新。 |
| The Bitter Lesson Behind Building Agentic RL in Terminal Environments | `https://www.notion.so/The-Bitter-Lesson-Behind-Building-Agentic-RL-in-Terminal-Environments-2eaddd45837f80c9ad2ed6a15ef3c1a1?pvs=21` | ROME / ALE 的博客入口。重点关注 terminal environment 中 agentic RL 的工程经验、环境构建和训练部署一致性。 |
| iFlow-ROME 模型卡 | `https://huggingface.co/FutureLivingLab/iFlow-ROME` | ROME-30B-A3B 模型发布说明。重点关注 ALE full-stack infrastructure、IPA、Terminal-Bench 2.0、SWE-bench Verified 和生产级安全声明。 |

## 2.5 在线登记增补（2026-09-02，方向发现与环境层两轮调查产出）

以下来源按 URL 登记，未制作本地 PDF。承重结论所在的本地分析见
`direction_discovery_20260818/` 与 `env_discovery_20260902/`。

| 资料 | URL | 日期 | RepoHarness 阅读重点 |
| --- | --- | --- | --- |
| Prime Intellect: Multi-Agent Systems | `https://www.primeintellect.ai/blog/multi-agent-systems` | 2026-08-07 | Agent（`run(task)->Trace`）/ Env（`run(task,agents)`）两抽象、四类环境（Agentic Judging / Proposer-Solver / Kuhn-Poker / **User-Sim 冻结用户策略训助手**）、Hierarchical GRPO、角色条件优势估计 RAE。随 verifiers 0.3.0 / prime-rl 0.8.0 发布。**只有代码无训练曲线（C 级）**——多智能体维持远期定位的依据。 |
| verifiers releases | `https://github.com/PrimeIntellect-ai/verifiers/releases` | 持续 | v0.2.0(07-10) v1 API / v0.2.1(07-20) Claude Code 外部 harness + OpenEnv / v0.3.0(08-07) 多智能体 + 沙箱网络隔离 / v0.3.1(08-24) 拦截改写 + 训练原生 episode artifacts。升级影响面见 `env_discovery_20260902/analysis/verifiers_v031_primerl_v090_impact_20260902.md`（结论：升级=T0，首训冻结期不升）。 |
| prime-rl releases | `https://github.com/PrimeIntellect-ai/prime-rl/releases` | 持续 | v0.8.0(08-07) Hierarchical GRPO + RAE；**v0.9.0(08-25) composable curricula + task sampling + admission gates**（`AdvRangeGate` 极薄，与我们七维 EligibilityGate 正交互补：他们判"值不值得学"，我们判"有没有资格进 loss"）。硬依赖 verifiers>=0.3.1。 |
| Prime Intellect: Environments Hub / scaling program | `https://www.primeintellect.ai/blog/environments`、`https://www.primeintellect.ai/blog/scaling-environments-program` | 2025-08-27 / 2025-10 | 环境分发平台（`prime env install org/name@ver`，第三方目录记 2500+ 环境）；质控 = 两档悬赏 + 人审，**无公开自动化资格化流水线**。 |
| HF delta-weight-sync | `https://huggingface.co/blog/delta-weight-sync` | 2026-05-27 | RL 学习率下 bf16 相邻步约 99% 权重位不变 → 稀疏同步 30-130x。P3 实测我们权重同步仅占 step ~0.8%（瓶颈是 rollout），**当前非瓶颈，备查**；拓扑/规模变化后再评估。 |
| Nemotron-SFT-SWE-v3.5 数据集 | `https://huggingface.co/datasets/nvidia/Nemotron-SFT-SWE-v3.5` | 2026-06-20 | 5115 条 OpenCode harness 生成的多文件 SWE 轨迹，CC BY 4.0 可商用。warm-start/SFT 候选；本身是"另一个 harness 的轨迹"，与多 harness 方向有交集。（注：官方数据卡确实存在——修正 codex 综合报告中"尚未核验到"的表述。） |
| DeepSeek-V4-Pro-0813 接口敏感性事件 | `https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813`、Zhihu Frontier 线程 `https://x.com/ZhihuFrontier/status/2088872677692076431` | 2026-08-13 | 官方 Code Agent 分数注明 "DeepSeek Harness Minimal mode"；社区分析认为核心是**接口敏感性**（特殊 token 原生 tool-call 协议在其他 harness 用普通消息模拟时激活不了）而非单纯记住 harness（mini-swe-agent 下仍 63%±6）。B 线动机案例：问题一半在 harness 多样性，一半在 chat template / tool 协议层 train-deploy 对齐。 |
| 蚂蚁 AEnvironment | `https://github.com/inclusionAI/AEnvironment` | 2026 | "Everything as Environment"：扩展 MCP 的统一环境接口 + AReaL 集成，内置 TAU2 / Mini Terminal / TerminalBench，K8s 部署。配套：Ling 3.0 Flash 自称 10,000+ 交互式训练环境。 |
| 字节 Seed + 清华 AIR CUDA-Agent | `https://arxiv.org/abs/2602.24286`、`https://github.com/BytedTsinghua-SIA/CUDA-Agent` | 2026-02 / 08-17 开源 | 训练数据 + 专家 SKILL.md + CUDA 开发环境整套开源，KernelBench 超 torch.compile 2.11x。"环境+技能包整体开源"的生产范式参照。 |
| MiniMax M2.1 后训练博客 | `https://www.minimax.io/news/post-training-experience-and-insights-for-agent-models` | 2026-01-22 | 按 PR 建 Docker 环境、10+ 语言、**10,000+ runnable PRs / 140,000+ 任务**、F2P/P2P 校验、应用开发三层 reward（执行/交互/视觉）。环境生产硬数字。 |
| OpenEnv | `https://github.com/meta-pytorch/OpenEnv` | 2026-06 起 PyTorch 基金会 | 环境发布/部署/消费互操作层（HTTP/WS + Docker），TRL/verl/TorchForge/SkyRL 已接入，仍自标实验阶段。互操作标准观察项。 |
| Harbor / Harbor Hub | `https://github.com/harbor-framework/harbor`、`https://hub.harborframework.com` | 2026-01 起 | 统一任务格式（Terminal-Bench 系）；Hub 定位 "tasks for training and evaluation"。**miles 官方带 Harbor 集成（`harbor-miles-v0.20.0` 分支）**——我们域 2 terminal 的候选载体，两种接入形态审计见 `env_discovery_20260902/analysis/harbor_miles_integration_audit_20260902.md`。 |
| SWE-rebench 经验谈 + Nebius 基建 | `https://www.sean-weldon.com/blog/2026-06-08-swe-rebench-lessons-from-evaluating-coding-agents-ibragim-badertdinov-nebius`、`https://nebius.com/blog/posts/infrastructure-behind-swe-rebench` | 2026-06-08 / 2025-11-07 | 环境生产真实成本对标锚：**153K 候选→21K 过执行验证（≈14% 存活）、人工核验 ~1 人日/任务**；reward hacking 实录（git 历史/GitHub 网页/curl 抓答案→剥离未来 git history，与 W3b 正向能力事实清单对上）；时间切分 = 唯一可靠去污染。 |
| **Meta Muse Glimmer 30B**（无 arXiv） | `https://research.meta.ai/blog/introducing-muse-glimmer-open-agentic-model`、`https://huggingface.co/meta-models/Muse-Glimmer-30B` | 2026-08-10 | **与本项目同量级（30B）的开源 agent 模型对照物**，Apache 2.0：预训练自 Muse Spark logit 蒸馏、中期 agent 数据、后训练 SFT + OPD 与 RL 混合多域；SWE-bench Pro 51.2 / MCP-Atlas / τ3-Bench。博客+模型卡级证据（精读见 `knowledge/summary_muse_glimmer_30b.md`）。 |
| Thinking Machines Inkling / Inkling-Small 模型卡 | `https://thinkingmachines.ai/model-card/inkling/` | 2026-07-15 / Small 权重 08-02 | 975B-A41B / 276B-A12B；模型卡披露大规模异步 RL（30M+ rollouts、合成+人造环境、开源模型合成数据 SFT 起步）。OPD 方法源头团队的首个模型，等正式报告再升级。 |
| 腾讯 Hy4-preview 模型卡 | `https://huggingface.co/tencent/Hy4-preview` | 2026-08-28 | 770B-A49B、1M ctx、Apache 2.0；架构细节多（Gated DSA + IndexCache、iHC、原生 MTP 层），自评超 GLM-5.3/K3；**无后训练细节**，模型卡级。 |
| Ling-3.0-flash / Tiny 模型卡 | `https://huggingface.co/inclusionAI/Ling-3.0-flash` | 2026-07-23 官宣 / 08-06 开权重 | 124B-A5.1B（35 层 KDA + 7 层 Gated MLA）；自称用 **10,000+ 交互训练环境**训 Coding/DeepResearch agent（与 AEnvironment 条目互证）；无论文。 |
| Kimi K2.5 论文 08-07 更新版 | `https://arxiv.org/abs/2602.02276` | 2026-08-07 (vN) | 已入库 R7b 的更新版（含 Agent Swarm 增补），需要时 diff 新版即可。 |
| QwenLM 新仓库观察项 | `https://github.com/QwenLM/E-CommerceBench`、`https://github.com/QwenLM/Qwen-MM-Plugins` | 2026-08-26 / 07-29 | E-CommerceBench（电商 agent 基准，暂空壳）；Qwen-MM-Plugins（"让任意 agent harness 多模态化"——与多 harness 议题相关的观察项）。 |

**已确认无增量的检索负结果（2026-09-03 核，避免重复搜索）**：Qwen3.8-Max/27B 仍无技术报告；DeepSeek V4-Pro 无新配套（库内 R6b 即官方 V4 正式报告，来自 V4-Pro HF repo 托管 PDF，非 4 月 preview——已核 manifest source_url）；Kimi K3 后无新披露；GLM-5.4 确认跳号、5.5 未发布；Composer 3 未发布（仅 leak）；Seed2.1（06-23）后字节无新报告；StepFun/快手/美团/百度/Cohere/Ai2/IBM 窗口内无相关披露；AReaL v1.0 为 03-04。

### 2.5.1 本地大型调研粘贴文档登记

这两份是外部 Pro 会话的完整原始输出，信息密度高但尚未拆条消化，登记入口避免遗忘：

| 文档 | 位置 | 内容 | 状态 |
| --- | --- | --- | --- |
| 外部pro探索回答粘贴.md | `pdfs/外部pro探索回答粘贴.md`（5214 行） | 五轮探索合集：①中国团队后训练路线（截止 2026-07-27，A/B/C 证据分级 + 材料束 A~J）②伴生证据审计（MOPD 集群四层结构 + 材料束 1~7）③ **Kimi K3 逐节深拆**（§十 白盒可组合 harness、§十一 知识图谱任务生产、§九 MOPD 逐 token 公式）④全球 Coding Agent 评测审计（SWE-bench Verified 弃用 2026-02-23、SWE-Bench Pro 撤回 2026-07-08）⑤全球 RL infra 生态审计（异步五档、可复现四档） | 未拆条进证据矩阵；`git status` 曾为 untracked，随本批登记纳入 |
| 外部pro模型调查2.md | `../../agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro模型调查2.md`（818 行） | 前沿模型 benchmark 图谱（截止 2026-09-01）：测评重心迁移八类、S_obs=F(M,H,T,C,B,E,V,J,R) 分解、P0/P1 能力优先级、三层评测架构（公共可比/内部辨识六轴/能力保持）、Eval Manifest 字段清单、两个测评研究候选 | ⚠️ 位于 tmp/（gitignored 只读参考区）；若要正式引用建议移出 tmp/ 并入库（owner 定） |

### 2.5.2 仓库外 harness 审读材料指针

仓库外 `external_harness_reference_workspace`（2026-08-15 审读）：Pi、DeepSeek Harness、Codex、Cordis 论文四份固定 SHA 的中文源码导读（各仓库内 `HARNESS_GUIDE.zh-CN.md`，总入口 `HARNESS_STUDY_GUIDE.zh-CN.md`），另有 prime-agent（未写导读）。B 线（多 harness）真实 harness 语义差异审计的现成素材。该工作区不随本仓库分发；需要复核时应按资料索引中的上游 URL 和固定 SHA 重新取得。注意其结论以各自 pin 的 SHA 为事实边界。

## 3. 按主题组织的阅读路线

### 3.1 RepoHarness 目标架构核心

优先读：

```text
R0 Polar
R1 MAI-Thinking-1
R2 Nemotron 3 Ultra
R4 MiniMax-M2
R5 GLM-5
R5b GLM-5.2
R5c GLM-5.3
R9 Composer 2
R10 Let It Flow
R11 RollArt
R12 ROLL framework
R13 Kimi K3
R14 CompactionRL
R15 SAO
reference/prime-rl/
```

关注问题：

```text
1. 环境、rollout、trajectory、trainer 的边界如何分开？
2. 长程 agent rollout 如何异步生成、缓存、过滤和训练？
3. token provenance、loss mask、logprob、reward attribution 如何进入训练样本？
4. 训练框架拥有多少运行时协调职责，环境服务应该拥有多少？
```

### 3.2 环境生产和质量过滤

优先读：

```text
R1 MAI-Thinking-1
R3 Qwen3-Coder-Next
R4 MiniMax-M2
R5c GLM-5.3
R6a DeepSeek-V3.2
R9 Composer 2
R10 Let It Flow
R13 Kimi K3
reference/ROCK/
reference/terminal-bench-pro/
```

关注问题：

```text
1. 任务如何从真实仓库、PR、issue、synthetic task 或 benchmark item 生产出来？
2. executable workspace 如何冻结？
3. empty patch、golden patch、determinism、reward profile 如何成为环境包前置门槛？
4. TaskQualityEvaluator 应该在离线生产阶段做什么，不应该进入运行时核心？
```

配套子文档：

```text
docs/harness_improve/environment_production_and_quality_pipeline_design.md
```

### 3.3 反作弊、安全与评分隔离

优先读：

```text
R1 MAI-Thinking-1
R2 Nemotron 3 Ultra
R5c GLM-5.3
R6a DeepSeek-V3.2
R6b DeepSeek-V4
R10 Let It Flow
R13 Kimi K3
reference/ROCK/
reference/AgentEnv/
```

关注问题：

```text
1. future git object、remote refs、GitHub raw / Pages 下载如何被阻断？
2. hidden verifier 如何只在评分时可见？
3. scoring checkout、test reset、test monkeypatch detection 如何进入 fail-closed 规则？
4. sandbox / tool calling 失败如何被结构化归因？
```

### 3.4 Warm-start、离线数据和过程惩罚

优先读：

```text
R2 Nemotron 3 Ultra
R4 MiniMax-M2
R8 MiniMax-M1
R14 CompactionRL
R15 SAO
```

关注问题：

```text
1. raw rollout 为什么不能直接变成 SFT 数据？
2. malformed tool call、invalid reasoning format、重复越权动作如何作为 process penalty？
3. unfinished trajectory 应该如何屏蔽 loss 或降级为离线分析？
4. SFTCandidateFilter 和 TrajectoryHeuristicAnalyzer 的启发式目录应该如何独立演进？
```

配套子文档：

```text
docs/agentic_RL/training_design/warm_start_offline_data_filtering_design.md
```

### 3.5 多 agent、视觉 agent 和未来扩展

优先读：

```text
R7a Kimi K2
R7b Kimi K2.5
R8 MiniMax-M1
R13 Kimi K3
```

关注问题：

```text
1. Visual Agentic Intelligence 对 RepoHarness 当前纯文本 SWE 任务有什么远期启发？
2. Agent Swarm / PARL 是否需要新的 UserSim、Permission 和 artifact visibility 设计？
3. 多 agent 并行执行是否需要新的 group identity、sub-agent lineage 和 delegation artifact？
4. 这些未来扩展是否可以通过 backend_tensors、ArtifactSpec 和 TrainingEligibilityReport 渐进接入？
```

### 3.6 LLM serving、rollout 和训练基础设施映射

优先读：

```text
R2 NVIDIA Nemotron 3 Ultra
R4 MiniMax-M2
R5 GLM-5
R5b GLM-5.2
R5c GLM-5.3
R11 RollArt
R12 ROLL framework
R13 Kimi K3
R14 CompactionRL
R15 SAO
reference/prime-rl/
reference/AgentEnv/
本次粘贴的 LLM serving、低精度、MTP 和长上下文基础讲义
```

关注问题：

```text
1. 长上下文、prefill、decode、KV cache 和 prefix cache 如何影响 agent rollout 吞吐？
2. low precision、FP8 KV cache、logprob precision 和 teacher logits 会如何影响训练信号可信度？
3. MTP / speculative decoding 是训练框架和推理服务能力，还是 RepoHarness 应该自研的能力？
4. verl、slime、prime-rl、vLLM、SGLang 已经承担了哪些训练运行时和推理服务职责？
5. RepoHarness 应该在 CompletionRecord、TrainingRuntimeRecord、backend_tensors 和 adapter 中记录哪些运行期事实？
```

配套子文档：

```text
docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md
```

### 3.7 真实产品级 coding agent 和开源模型基线

优先读：

```text
R5 GLM-5
R5b GLM-5.2
R5c GLM-5.3
R9 Composer 2
R10 Let It Flow
reference/claude-code-typescript-src/
reference/codex/
reference/mini-swe-agent/
reference/slime/
reference/ROLL/
reference/ROCK/
reference/iflow-cli/
```

关注问题：

```text
1. 真实产品级 coding agent 是否直接在部署 harness 或等价 harness 中训练？
2. 工具、权限、shell、文件编辑、长程任务和用户交互如何进入训练环境？
3. 当前开源最强长程编码模型暴露了哪些能力和基础设施需求？
4. 极简 bash-only baseline 能解决什么，不能解决什么？
5. RepoHarness 自己的白盒 harness 应该保留哪些控制权，哪些能力应交给训练框架或推理服务？
```

### 3.8 ROLL / ROCK / ROME 生态专项路线

优先读：

```text
R10 Let It Flow
R11 RollArt
R12 ROLL framework
reference/ROLL/
reference/ROCK/
reference/iflow-cli/
reference/terminal-bench-pro/
```

关注问题：

```text
1. ROLL、ROCK、iFlow CLI 和 Terminal-Bench-Pro 如何分别承担训练、环境、agent runtime 和 benchmark 职责？
2. Agent Native Mode 为什么把上下文管理留在真实 CLI harness 内，而把模型调用交给 ModelProxyService 捕获？
3. ROCK 的 Admin / Worker / Rocklet / EnvHub / ModelService 对 RepoHarness 的 sandbox service 和黑盒 harness 支持有什么启发？
4. RollArt 的轨迹级异步、LLMProxy、EnvManager、SampleBuffer、serverless reward 和 bounded staleness，哪些应该成为 RepoHarness 与训练后端的握手字段，哪些应该继续由 verl、slime 或 ROLL 这类训练框架拥有？
5. Terminal-Bench-Pro 的公开 / 私有拆分、领域覆盖、任务 metadata、verifier timeout 和环境资源声明，如何进入 RepoHarness 的环境生产与质量流水线？
```

配套分析文档：

```text
docs/harness_improve/external_paper_references/roll_ecosystem_reference_intake_analysis.md
```

### 3.9 训练配方、终止语义和算法选择专项路线

优先读：

```text
agentic_rl_training_recipe_evidence_matrix.md
R2 Nemotron 3 Ultra
R5 GLM-5
R5b GLM-5.2
R5c GLM-5.3
R9 Composer 2
R11 RollArt
R13 Kimi K3
R14 CompactionRL
R15 SAO
docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md
```

关注问题：

```text
1. context / turn / token / wall-clock / grading / staleness budget 是否被正确拆开？
2. 一条轨迹是否进入同题组统计、自身是否产生梯度、artifact 是否保留，是否为三个独立决定？
3. fixed-n、冗余派发、整组动态替换、partial resume、single-rollout PPO 分别解决什么问题？
4. 哪些数值来自成功论文配方，哪些只是框架默认、示例脚本或评测配置？
5. 当前 Qwen3-Coder-30B-A3B + Claude Code + slime 组合有哪些直接证据，哪些仍需 RH2 自己验证？
```

## 4. 当前主设计文档中的吸收方式

主设计文档 `docs/harness_improve/repo_harness_repositioning_after_polar.md` 已按三类标准吸收这些报告：

```text
1. ownership 边界：
   双拓扑、EnvironmentPackage / TaskPack / EnvConfig、UserSimRunner、
   PermissionGate、TrainingEligibilityGate、训练后端与 RepoHarness 运行时边界。

2. 运行期契约：
   CompletionRecord、TrainTrace、TrajectoryArtifact、TrainingRuntimeRecord、
   EnvironmentValidationReport、AntiCheatSpec、FailureRecord、TokenPenaltySpan。

3. fail-closed 规则：
   token provenance、logprob alignment、loss mask、reward attribution、
   clean grading、hidden verifier isolation、anti-cheat、environment validation、
   staleness、backend tensor validation。
```

没有进入主设计文档的内容，不表示不重要，而是放在子文档中独立演进。例如 PR 筛选策略、LLM rewrite prompt、SFT 过滤启发式、process penalty 权重、具体通过率阈值，都不应该冻结在主架构文档里。

LLM serving、rollout 和训练基础设施相关内容，单独沉淀在 `infra_mapping_for_repoharness_rl_serving.md`。这份文档的结论是：RepoHarness 不应该自研 vLLM、SGLang、Megatron、verl 或 slime 已经拥有的推理内核、KV cache、低精度、MTP、权重同步和分布式训练队列；RepoHarness 应该把这些系统产生的 token、logprob、sampling 参数、权重版本、staleness、precision、teacher tensor 和后端消费状态记录成可审计契约。

参考代码库的吸收方式与论文不同。论文主要给出系统方向、实验结论和训练 recipe；`reference/` 仓库用于校验这些方向在真实代码里的 ownership、数据结构、运行时边界和失败模式。例如，Polar 证明黑盒 harness 可以通过 model proxy 捕获轨迹，verifiers / research-environments 证明 Taskset / Harness / Env 可以解耦，renderers 证明 token-faithful rendering 需要独立抽象，verl、slime 和 prime-rl 证明训练运行时协调应归属训练框架，Claude Code / Codex / mini-swe-agent 则给出真实开发代理和极简 baseline 的工具边界对照。

ROLL 生态新增的价值主要不是改变上述主定位，而是补强三个以前相对薄的参考面：第一，ROCK 把 sandbox lifecycle、环境注册、agent 安装、网络代理和 OpenAI-compatible model proxy record/replay 做成环境服务，能作为 RepoHarness 长期 `Runtime / Execution Plane` 的服务化参照；第二，RollArt 把 agentic RL 的异步问题细化到轨迹级 EnvManager、LLMProxy、SampleBuffer、serverless reward 和 bounded-staleness 权重同步，能校准 `Training Runtime Coordination Plane` 的字段和责任边界；第三，Agent Native Mode 证明真实 CLI harness 可以保留自己的上下文管理，训练系统只在模型边界代理和记录，这和 RepoHarness 同时支持白盒 native harness 与黑盒 harness 训练的方向一致。
