# Agentic RL 外部技术报告第一批资料索引

本文记录 RepoHarness 重定位阶段第一批外部 paper、网页短报告、技术报告和参考代码库的本地组织方式、阅读重点和后续用途。它不是论文综述终稿，而是一个面向后续架构设计和代码实现的资料入口。

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
| R5b | GLM-5.2: Built for Long-Horizon Tasks | `https://z.ai/blog/glm-5.2`；辅助入口：`https://github.com/zai-org/GLM-5` 和 `https://docs.z.ai/guides/llm/glm-5.2` | 当前智谱最新网页短报告。尚未有完整技术报告，但 GLM-5.2 代表当前开源长程编码模型的重要水平，应作为“开源 frontier coding agent model”参考。重点关注 1M 上下文、长程工程任务、thinking effort、IndexShare、MTP speculative decoding、SGLang / vLLM 部署，以及其背后 GLM-5 / slime 异步强化学习基础设施。 |
| R6a | DeepSeek-V3.2 | `docs/harness_improve/external_paper_references/pdfs/R6_deepseek_v3_2_2512.02556.pdf` | agentic task synthesis、large-scale tool-use data generation、scalable RL protocol、DeepSeek Sparse Attention、长上下文与 agent 性能结合。 |
| R6b | DeepSeek-V4 | `docs/harness_improve/external_paper_references/pdfs/R6_deepseek_v4_pro_DeepSeek_V4.pdf` | million-token context、agentic coding、OPD / distillation / sandbox 相关线索、DSec 类 sandbox 基础设施参考。 |
| R7a | Kimi K2 | `docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_2507.20534.pdf` | large-scale agentic data synthesis、joint RL、agentic intelligence、SWE-Bench / Tau2 / ACEBench 等 agentic benchmark 结果。 |
| R7b | Kimi K2.5 | `docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_5_2602.02276.pdf` | Visual Agentic Intelligence、Agent Swarm、parallel agent orchestration、PARL、子 agent 创建和任务委托。 |
| R8 | MiniMax-M1 | `docs/harness_improve/external_paper_references/pdfs/R8_minimax_m1_2506.13585.pdf` | 1M context、Lightning Attention、CISPO、test-time compute、sandbox-based SWE RL、长上下文 reasoning RL 到 agent RL 的过渡。 |
| R9 | Composer 2 Technical Report | `docs/harness_improve/external_paper_references/pdfs/2603.24477v2.pdf` | Cursor Research 的 agentic software engineering 模型报告。重点关注真实 Cursor harness 中训练、减少 train-test mismatch、等价工具和结构、真实大代码库任务、异步强化学习、大规模端到端编码性能，以及产品级 coding agent 如何把 deployed harness 直接纳入训练。 |
| R10 | Let It Flow: Agentic Crafting on Rock and Roll | `docs/harness_improve/external_paper_references/pdfs/R10_let_it_flow_roll_rock_rome_2512.24873.pdf` | 阿里 ALE 生态总报告。重点关注 ROLL 训练框架、ROCK 沙箱环境管理、iFlow CLI agent runtime、Terminal-Bench-Pro、ROME 模型、Agent Native Mode、ModelProxyService、训练和部署 harness 一致性。 |
| R11 | RollArt: Disaggregated Multi-Task Agentic RL Training at Scale | `docs/harness_improve/external_paper_references/pdfs/R11_rollart_disaggregated_agentic_rl_2512.22560.pdf` | 多任务 agentic RL 系统论文。重点关注轨迹级异步 rollout、LLMProxy、EnvManager、SampleBuffer、serverless reward、硬件亲和调度、bounded-staleness 权重同步、长尾环境和失败环境处理。 |
| R12 | ROLL framework technical report | `docs/harness_improve/external_paper_references/pdfs/R12_roll_framework_2506.06122.pdf` | ROLL 训练框架技术报告。重点关注 Ray 多角色分布式架构、Parallel Worker、Rollout Scheduler、Environment Worker、Reward Worker、AutoDeviceMapping、vLLM / SGLang / Megatron / FSDP2 集成和 agentic pipeline。 |

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

## 2.2 ROLL 生态辅助网页和模型卡

下面这些资料不是本地 PDF 或代码仓库，但应该和 R10-R12 一起阅读：

| 资料 | URL | RepoHarness 阅读重点 |
| --- | --- | --- |
| ROLL 团队页面 | `https://wwxfromtju.github.io/roll_team.html` | 团队和项目谱系入口，用于追踪 ROLL / ROCK / ROME / Terminal-Bench-Pro 后续更新。 |
| The Bitter Lesson Behind Building Agentic RL in Terminal Environments | `https://www.notion.so/The-Bitter-Lesson-Behind-Building-Agentic-RL-in-Terminal-Environments-2eaddd45837f80c9ad2ed6a15ef3c1a1?pvs=21` | ROME / ALE 的博客入口。重点关注 terminal environment 中 agentic RL 的工程经验、环境构建和训练部署一致性。 |
| iFlow-ROME 模型卡 | `https://huggingface.co/FutureLivingLab/iFlow-ROME` | ROME-30B-A3B 模型发布说明。重点关注 ALE full-stack infrastructure、IPA、Terminal-Bench 2.0、SWE-bench Verified 和生产级安全声明。 |

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
R9 Composer 2
R10 Let It Flow
R11 RollArt
R12 ROLL framework
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
R6a DeepSeek-V3.2
R9 Composer 2
R10 Let It Flow
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
R6a DeepSeek-V3.2
R6b DeepSeek-V4
R10 Let It Flow
reference/ROCK/
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
R11 RollArt
R12 ROLL framework
reference/prime-rl/
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
