# Agentic Technical Report Reading Map For RepoHarness

## 0. 这篇文档的使用方式

这篇文档服务于当前 RepoHarness 项目，而不是做泛泛的论文综述。

当前项目目标是快速实现一个面向 LLM agentic training、agentic reinforcement learning、post-training 的轻量级软件工程 agent harness。项目现有设计文档已经把目标拆成这些模块：

- `docs/03-agent-loop-and-message-protocol.md`：agent loop、消息协议、工具结果回填。
- `docs/04-tool-system-and-orchestration.md`：工具契约、工具执行、工具输出截断、并发编排。
- `docs/05-workspace-sandbox-and-permissions.md`：workspace、Docker-based executable repository environment、permission、sandbox 边界。
- `docs/06-task-dataset-and-environment-adapters.md`：任务适配、baseline gate、fail-to-pass、pass-to-pass。
- `docs/07-verifier-reward-and-evaluation.md`：verifier、reward metadata、批量评测。
- `docs/08-trajectory-store-and-training-export.md`：transcript、events、patch、训练数据导出。
- `docs/09-agent-scaffolds-and-multi-agent.md`：single-shot、ReAct、planner-coder-verifier、多角色 scaffold。
- `docs/10-context-session-and-failure-diagnostics.md`：上下文管理、resume、失败诊断。

因此，技术报告的阅读标准是：它是否能直接指导这些模块的设计和实现。

我保留 `REPORT_READING_PRIORITY_ORDER.md` 中的 P0、P0.5、P1、P2 层级，但在同一层级内部按照 RepoHarness 项目的直接价值重新排序。换句话说：原始优先级文件决定“先读哪一批”，本文件决定“为了这个项目，批内先抓哪些内容”。

## 1. 第一阶段必须读：直接决定 RepoHarness 架构的报告

第一阶段的目标是让项目从“设计文档和 Python 骨架”变成“最小可运行闭环”。最小闭环是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward metadata -> export
```

### 1.1 `kimi-k2`

原始优先级：P0 已完成样板。

为什么必须读：

Kimi K2 是当前本地资料中最完整的 agentic training 样板。它覆盖 agentic data synthesis、tool calling protocol、verifiable rewards、self-critique rubric reward、RL infrastructure、agentic evaluation 和 safety limitation。它最适合作为 RepoHarness 的“训练数据闭环”参考。

必须读的内容：

- `3.1.1 Large-Scale Agentic Data Synthesis for Tool Use Learning`：重点读 tool repository、synthetic tools、agent diversification、rubric-based task generation、multi-turn trajectory generation、tool execution environment、quality filtering、hybrid real execution environment。
- `3.2.1 Verifiable Rewards Gym`：重点读哪些任务适合自动 verifier 或 rule-based reward，尤其 coding、software engineering、instruction verification、faithfulness to retrieved contexts。
- `3.2.2 Self-Critique Rubric Reward`：重点读开放任务如何用 rubric、critic、pairwise evaluation 做 reward。
- `3.2.3 RL Algorithm`：只需要掌握对同一问题采样多个响应、组内 reward baseline、budget control、pretraining loss 稳定器，不需要把它包装成 RepoHarness 的算法贡献。
- `3.3 RL Infrastructure`：重点读 colocated training/inference、engine switching、agentic rollout、partial rollout、Gym-like interface。
- `Appendix B Token Template of Tool Calling`：重点读工具调用如何被编码成稳定的模型输入输出协议。

对应到 RepoHarness：

- `docs/04` 的工具契约和 tool result 回填，可以参考 Kimi K2 的 tool calling protocol。
- `docs/06` 的任务和环境，可以参考 Kimi K2 的 tool repository、rubric-based task、hybrid execution environment。
- `docs/07` 的 verifier/reward，可以参考 Verifiable Rewards Gym 和 self-critique rubric reward。
- `docs/08` 的 trajectory/export，可以参考 multi-turn trajectory generation 和 filtering。

项目实现时的转化：

- 给每个任务定义 `rubric` 或 `verifier_config`，不要只有自然语言 issue。
- 训练导出中保留完整 action-observation trajectory，而不是只保留 final patch。
- reward metadata 必须说明 reward 来源：unit tests、rule-based check、LLM judge、rubric judge 或 mixed reward。

### 1.2 `deepseek-v4`

原始优先级：P0。

为什么必须读：

DeepSeek V4 是本地报告里最适合补“工业级 agent harness、rollout service、tool protocol、sandbox、long-horizon evaluation”的资料。它比 Kimi K2 更接近系统工程视角，尤其是 DSec、rollout service、million-token RL framework、code/search/white-collar agent evaluation。

必须读的内容：

- `5.1 Specialist Training`：重点读 specialist training、GRPO、easy-to-verify 和 hard-to-verify RL tasks、generative reward model。
- `Tool-call schema` 和 `interleaved thinking`：重点读 `|DSML|` token、XML-style invocation、thinking management、quick instruction。
- `5.1.2 On-Policy Distillation`：重点读 OPD objective、student on-policy trajectories、full-vocabulary logit distillation。
- `5.2.3 Rollout Service`：重点读 preemptible/fault-tolerant generation service、token-granular write-ahead logging、KV cache save/resume。
- `5.2.4 Million-token RL Framework`：重点读 metadata 与 per-token fields 分离、global shuffling/packing、shared-memory data loader。
- `5.2.5 DSec`：重点读 DSec components、API gateway、execution substrates、trajectory log/replay/provenance。
- `5.3` 和 `5.4`：重点读 code agent harness、search agent harness、white-collar tasks、agentic search 与 RAG search 的区别。

对应到 RepoHarness：

- `docs/03` 可以参考 interleaved thinking 和 tool-result turn 的处理。
- `docs/04` 可以参考 tool-call schema 和 quick instruction，但不要照搬成唯一协议。
- `docs/05` 可以参考 DSec 的分层思路，但 RepoHarness 第一版只能保守表述为 Docker-based executable repository environment。
- `docs/08` 可以参考 token-granular logging、trajectory replay、provenance 思想。
- `docs/10` 可以参考 KV cache resume、long context、context management。

项目实现时的转化：

- ToolResult 必须带 `tool_call_id`、`status`、`duration_ms`、`truncated`、`artifact_refs`，方便 replay 和 provenance。
- 运行目录必须能保存 `transcript.jsonl`、`events.jsonl`、`final.diff`、`verifier.json`。
- 只说“容器化执行环境、路径边界、命令超时、日志审计原型”，不要声称实现了 DSec 级安全沙箱。

### 1.3 `glm-5`

原始优先级：P0。

为什么必须读：

GLM-5 对 RepoHarness 最有价值的地方是系统架构语言。它明确讨论从 Reasoning RL 到 Agentic RL 再到 General RL，讨论 asynchronous reinforcement learning、rollout orchestrator、server-based multi-task training、environment scaling、SWE/terminal/search/slide environments、context management。它非常适合支撑简历中的“agentic training infrastructure”叙事。

必须读的内容：

- `Section 3 Post-Training`：重点读 SFT、Reasoning RL、Agentic RL、General RL、On-Policy Cross-Stage Distillation、slime。
- `3.6 RL Training Infrastructure: slime`：重点读 free-form rollouts、server-based execution、tool invocation、environment feedback、verifier-guided branching。
- `4.1 Asynchronous RL for Agentic Tasks`：重点读 training 与 inference 解耦、Multi-Task Rollout Orchestrator、per-task rollout/reward microservices、统一 message-list 表示。
- `4.1.2 Optimizing asynchronous stability`：重点读 TITO、direct double-sided importance sampling、dropping off-policy/noisy samples、DP-aware routing。
- `4.2 Environment Scaling for Agents`：重点读 SWE environments、terminal environments、search environments、context management、slide generation。
- `6.2 Real-World Agentic Engineering Tasks`：重点读 frontend/backend/long-horizon engineering/evolving SWE tasks。

对应到 RepoHarness：

- `docs/02` 的 control plane、execution plane、data plane，可以用 GLM-5 的 orchestrator/microservice 思路加强。
- `docs/06` 的 task adapter，可以参考 issue-PR pairs、RepoLaunch、F2P/P2P extraction、Dockerized terminal tasks。
- `docs/07` 的 verifier/reward，可以参考 per-task reward microservices 和 environment collapse sample filtering。
- `docs/10` 的 failure diagnostics，可以参考 noisy samples、sandbox failure reason、context management。

项目实现时的转化：

- 把每类任务环境设计成可注册 adapter：`swe`, `terminal`, `search`。
- 在 events 中记录 failure reason，区分 model failure 和 environment collapse。
- 把 trajectory 统一成 message-list 或 action-observation list，方便后续训练导出。

### 1.4 `qwen3-coder-next`

原始优先级：P0。

为什么必须读：

Qwen3-Coder-Next 是最直接的 coding agent training 报告之一。它强调 verifiable coding tasks、executable environments、GitHub pull request mining、synthetic executable tasks、large-scale rollout collection、environment feedback RL、多种 tool chat templates、多 scaffold 泛化、reward hacking blocker。它几乎可以直接映射到 RepoHarness 的任务构造、工具协议、评测和安全边界。

必须读的内容：

- `Creating Executable Environments from GitHub PRs`：重点读 PR decomposition、buggy state、fix、test patch、environment-building agent、Docker environment、verification script。
- `Synthesizing Issues`：重点读 controlled bug injection、test failure/reversion validation、natural-language issue generation、exclude bug-triggering test files。
- `MegaFlow`：重点读 agent rollout、evaluation、post-processing 三阶段。
- `Multi-turn Agentic Coding`：重点读 SWE-agent、Mini-SWE-agent、OpenHands、Claude Code 等多框架生成轨迹。
- `Filtering with Verification`：重点读 user simulator、compiler outputs、runtime errors、environment state changes。
- `Data and Tool Calling`：重点读多种 tool chat templates、XML/JSON/Python-style/tool response wrapping、format-invariant tool-use behavior。
- `Multi-turn agentic RL`：重点读 final task completion reward、unfinished trajectory penalty、turn-level tool-format penalty。
- `Reinforced Reward Hacking Blocker`：重点读 GitHub future commit leakage、remote/network command blocking。

对应到 RepoHarness：

- `docs/04` 的 tool schema 与 tool format 泛化，应参考多模板训练思想，但实现时先支持一种稳定 JSON 或 XML 协议。
- `docs/06` 的 task adapter，应参考 GitHub PR mining、buggy state、test patch、Docker verifier。
- `docs/07` 的 reward，应加入 `unfinished_trajectory_penalty`、`invalid_tool_call_penalty`、`regression_penalty`。
- `docs/05` 的 permission，应加入对 `git clone`、`git remote add`、`curl`、`wget` 等 reward hacking 风险命令的规则。

项目实现时的转化：

- 第一版任务可以先手工构造 micro-repo tasks，但 schema 要预留 GitHub PR adapter 字段：`base_commit`、`gold_patch`、`fail_to_pass_tests`、`pass_to_pass_tests`。
- `bash` 中识别测试命令后应路由到 `run_tests`，防止普通命令结果混入 reward。
- 对工具调用格式错误做结构化计数，进入 metrics 和 reward metadata。

### 1.5 `kat-coder-v2`

原始优先级：P0。

为什么必须读：

KAT-Coder-V2 的 KwaiEnv 是 RepoHarness 最值得直接参考的环境抽象之一。它强调 datasets、sandboxes、scaffolds、verifiers 解耦，支持多 scaffold、多 sandbox、大规模 trajectory collection、RL engine 输出。它还能帮助你把项目讲成“训练友好的 harness”，而不是一个普通 coding agent demo。

必须读的内容：

- `KwaiEnv: Infrastructure for Agentic Code Intelligence`：重点读 dataset、sandbox、scaffold、verifier 解耦。
- `Trajectory Manager`：重点读通过代理拦截 LLM requests、记录 I/O、tool-call sequences、token metadata。
- `SWE Expert / AutoBuilder Pipeline`：重点读 issue-PR mapping、dependency resolution、build/test script generation、F2P/P2P verification。
- `Code Comprehension Pipeline`：重点读 repository exploration、code locating、call-chain tracing、enhancement planning、code review。
- `Agentic Scaling`：重点读 `DRL = <E, Ttools, Sagent, Itask, Vverifier>` 这类抽象。
- `Tree Training`：只需理解复杂 scaffold 会产生树状轨迹，第一版 RepoHarness 不必实现。
- `On-Policy Distillation`：只需理解统一模型吸收各专家能力，不需要在项目里实现。

对应到 RepoHarness：

- `docs/02` 的模块所有权表可以吸收 KwaiEnv 的 separation of concerns。
- `docs/09` 的 scaffold 对比，应参考多 scaffold evaluation，而不是只跑一个 ReAct。
- `docs/08` 的 trajectory，可以加入 `scaffold_id`、`tool_policy`、`verifier_id`、`environment_id`。

项目实现时的转化：

- 每个 run 都应记录：模型、scaffold、dataset/task、workspace mode、verifier。
- 同一个 task 应该能在 `single_shot`、`simple_react`、`planner_coder_verifier` 下重复运行，方便对比。

### 1.6 `cursor-composer-2`

原始优先级：P0。

为什么必须读：

Cursor Composer 2 是最贴近真实产品级 coding agent 的报告。它明确说模型在与部署一致的 Cursor harness 中训练和评测，包含真实 codebase environment、isolated container、tools、long rollouts、reward、CursorBench、Anyrun、snapshotting、production backend shadow deployment。这对你“参考产品级 agent 源码快速写 harness”的目标非常重要。

必须读的内容：

- Agent 定义：environment、codebase、isolated container、task prompt、actions、tool calls、final environment state、reward。
- Tools：read/edit files、shell、grep/semantic search、web search、system message、tool call format、recent file information。
- Continued pretraining 与 asynchronous reinforcement learning 的分工。
- Long rollouts、overlong rollout masking、length penalty、tool-call behavior rewards。
- `CursorBench`：重点读真实用户 session、less-specified prompts、大 codebase、多文件修改、code quality、interruption evaluation。
- `RL infrastructure`：重点读 training、environments、inference、verifier 四个 decoupled services。
- `Anyrun`：重点读 stateful codebase environments、snapshot/fork、controlled egress、tool library、production harness fidelity。

对应到 RepoHarness：

- `docs/03` 的 agent loop 可以直接用 Cursor 的 action/tool-call/environment state 定义作概念锚点。
- `docs/05` 的 workspace/sandbox 可以参考 isolated container、egress control、snapshot/fork，但第一版只做本地或 Docker 执行。
- `docs/07` 的评测应加入 code quality、interruption、efficiency 等行为指标。
- `docs/12` 的简历叙事可以借鉴“same harness for training and deployment”的表述，但不能声称你的项目已经达到产品一致性。

项目实现时的转化：

- Demo 不应只跑 SWE-Bench 风格的窄任务，也应准备几个“描述不完整、需要探索代码库”的 micro-repo task。
- metrics 里加入 average turns、average tool calls、test run count、patch size、run cost proxy。

### 1.7 `kimi-k1-5`

原始优先级：P0。

为什么必须读：

Kimi K1.5 不是完整 agent harness 蓝图，但它是 long-context reinforcement learning scaling、partial rollout、code execution sandbox、test-case generation 的重要前置材料。RepoHarness 第一版不做大规模 RL，但需要借它理解长轨迹为什么要做 partial rollout、sandbox、repeat detection、rollout worker。

必须读的内容：

- Long-CoT RL scaling：理解长输出和长轨迹为什么会拖慢 rollout。
- Policy optimization：只需掌握 online mirror descent、sampling strategy 的高层作用。
- Test case generation for coding：重点读自动生成测试用例、过滤、作为 reward 的方式。
- RL infrastructure：重点读 rollout workers、central master、partial rollout、replay buffer。
- Code execution service / sandbox：重点读 consistent、repeatable evaluation、multi-stage assessment。
- Long2short：只需理解成本控制，不必作为第一版项目重点。

对应到 RepoHarness：

- `docs/07` 的 verifier/reward 可以参考自动测试用例和 execution feedback。
- `docs/08` 的 trajectory store 可以为未来 partial rollout 预留 checkpoint 或 per-turn patch。
- `docs/10` 的 resume 应保守：第一版只从 final workspace 继续，不声称任意 turn 恢复。

### 1.8 `longcat-flash-thinking-2601`

原始优先级：P0。

为什么必须读：

LongCat-Flash-Thinking-2601 对 RepoHarness 的最大价值是“多环境 agentic RL scaling”。它把 agentic capability 解释为在多样环境中的可迁移能力，并强调 executable and verifiable environments、10,000+ environments、DORA、multi-turn rollout、noise-aware training。

必须读的内容：

- Agentic mid-training：structured agentic trajectories、text-driven synthesis、environment-grounded synthesis。
- Environment construction：tool schema、tool code、tool tests、database state、tool dependency graph。
- Agentic coding environment：executable code sandbox、search/file read/write/code editing/shell execution 统一接口。
- Verifiability-preserving environment expansion：重点读如何增加环境复杂度但保持 supervision signal 可靠。
- DORA：重点读 fully streaming asynchronous pipeline、multi-version generation、large-scale environment execution。
- Noise-aware training：重点读环境崩溃、工具失败、真实环境不完美如何进入训练策略。

对应到 RepoHarness：

- `docs/06` 的 environment adapter 可以借鉴 tool dependency graph 和 verifiability-preserving expansion。
- `docs/07` 的 reward 必须区分模型错误和环境噪声。
- `docs/10` 的 failure diagnostics 应包含 `environment_collapse` 或 `environment_unstable` 这类字段。

### 1.9 `tongyi-deepresearch`

原始优先级：P0。

为什么必须读：

Tongyi DeepResearch 虽然不是 coding agent，但它对 long-horizon search agent、automatic data synthesis、customized environments、context management、agentic RL 很有参考价值。如果 RepoHarness 第二阶段扩展 search environment 或 research agent，这篇必须读。

必须读的内容：

- Design principles：agentic mid-training + agentic post-training 的分工。
- Synthetic data：research-level question synthesis、agentic behavior data generation、data flywheel。
- Environment taxonomy：Prior World Environment、Simulated Environment、Real-world Environment。
- Rollout formalization：thought-action-observation triplets。
- Context Management Mode：长程工具调用中的摘要状态。
- Post-training：data synthesis、SFT cold start、agentic RL。
- Unified sandbox：Search、Visit、Python Interpreter、Google Scholar、File Parser 的稳定工具接口。
- On-policy asynchronous rollout framework：模型推理服务器、工具调用服务器、centralized interaction service。

对应到 RepoHarness：

- `docs/03` 可以参考 ReAct trajectory 的形式化。
- `docs/04` 可以参考 search/visit/python/file parser 工具族。
- `docs/08` 可以参考 thought-action-observation 与 context summary 数据。
- `docs/10` 可以参考 context management mode。

### 1.10 `qwen3`

原始优先级：P0。

为什么必须读：

Qwen3 是 post-training 基础读物。它没有公开完整 harness，但它清楚解释 Long-CoT Cold Start、Reasoning RL、Thinking Mode Fusion、General RL、Strong-to-Weak Distillation、ToolUse evaluation。它帮助你在面试中把“agentic RL”和“普通 reasoning RL / SFT / distillation”区分清楚。

必须读的内容：

- `4.1 Long-CoT Cold Start`：重点读 verified answers、code-based test cases、query/response filtering。
- `4.2 Reasoning RL`：重点读 query-verifier pairs、GRPO、large batch、high rollouts、off-policy、entropy control。
- `4.3 Thinking Mode Fusion`：重点读 `/think`、`/no_think`、empty think block、多轮模式切换、thinking budget。
- `4.4 General RL`：重点读 Agent Ability、designated interfaces、multi-turn interaction、real environment execution feedback。
- Three reward types：rule-based reward、model-based reward with reference answer、model-based reward without reference answer。
- `4.5 Strong-to-Weak Distillation`：重点读 off-policy 与 on-policy distillation 的分工。
- `Table 22`：重点读 ThinkFollow、ToolUse、Stage 2 到 Stage 4 的变化。

对应到 RepoHarness：

- `docs/07` 的 reward metadata 可以采用“reward type”字段。
- `docs/03` 的 mode 和 budget 可以吸收 thinking budget，但不要把 thinking budget 变成你的核心贡献。
- `docs/12` 的面试叙事中要说明：RepoHarness 服务 agentic RL 数据闭环，不提出新的 RL 算法。

### 1.11 `deepseek-r1`

原始优先级：P0。

为什么必须读：

DeepSeek R1 是 RLVR、GRPO、verifiable reward、cold start、distillation 的基础读物。它不是完整 agent harness 蓝图，但你应聘 agentic RL / post-training 方向时必须能解释它和 agentic training 的关系。

必须读的内容：

- R1-Zero：重点读 rule-based reward、没有 SFT cold start 时的能力涌现和问题。
- R1 pipeline：重点读 cold-start data、reasoning-oriented RL、rejection sampling、SFT、final RL。
- GRPO：只需掌握 group relative advantage、无需 value model 的高层机制。
- Verifiable rewards：重点读数学和代码任务如何用自动 verifier。
- Distillation：重点读强模型轨迹如何蒸馏到小模型。
- Reward hacking / language mixing / readability limits：重点读 RL 的边界。

对应到 RepoHarness：

- `docs/07` 的 reward prototype 必须说是 verifier-aligned metadata，不是新算法。
- `docs/08` 的 SFT/RL export 可以参考成功轨迹、部分成功轨迹和失败轨迹的分层导出。

## 2. 第一阶段后半：根据项目范围选择的 P0 报告

### 2.1 `ui-tars-2`

适合什么时候读：

如果 RepoHarness 只做 repository-level software engineering，UI-TARS-2 可以排在 coding/search harness 之后。如果你希望项目展示 GUI、computer use、browser automation 或 Playwright 验证能力，就必须提前读。

必须读的内容：

- Formal agent formulation：history、memory、environment、thought、action、observation。
- All-in-One GUI Sandbox：GUI operations、file system、terminal、MCP tool invocation、shared filesystem。
- Data flywheel：CT、SFT、RL、RFT 的迭代数据流。
- Multi-turn RL：RLVR、domain-specific tasks、stateful environments、streaming updates。
- Reward design：deterministic reward、VLM/ORM reward、format reward、length penalty。
- Evaluation：OSWorld、WindowsAgentArena、AndroidWorld、Online-Mind2Web、TerminalBench、SWE-Bench。

对应到 RepoHarness：

- `docs/05` 可以借鉴 shared file system 和 sandbox API，但第一版不实现 GUI VM。
- `docs/07` 可以借鉴 deterministic vs model-based reward 的分类。
- `docs/10` 可以借鉴 stateful environment 和 long-lived state。

### 2.2 `kimi-k2-5`

适合什么时候读：

当你准备实现 `planner-coder-verifier` 之外的 sub-agent delegation 或 parallel research/coding scaffold 时再重点读。第一版不必实现 Agent Swarm，但需要知道它如何定义 parallel agent reinforcement learning。

必须读的内容：

- Agent Swarm：dynamic task decomposition、subagent instantiation、parallel subtask scheduling。
- PARL：orchestrator 可训练，subagents 冻结为 environment observations。
- PARL reward：parallel instantiation reward、sub-agent finish rate、task-level outcome。
- Critical steps：用 critical path 衡量并行 agent 的时间成本。
- Unified Agentic RL Environment：Gym-like interface、Toolset、Judge、sandbox、subtask rollouts。
- Agent Swarm configuration：`create_subagent`、`assign_task`、step limits、sub-agent toolset。

对应到 RepoHarness：

- `docs/09` 的 multi-agent 边界：第一版只做顺序式多角色 scaffold，不做真实后台 subagents。
- `docs/10` 的 context management：Agent Swarm 可被理解成主动的上下文分解和并行探索。

### 2.3 `kimi-researcher`

适合什么时候读：

当你准备把 RepoHarness 从 coding tasks 扩展到 research/search tasks 时读。它偏产品和 workflow，但能补 tool harness 的现实形态。

必须读的内容：

- parallel internal search。
- text browser。
- code tool / Python tool。
- research workflow。
- long-horizon information synthesis。
- 多 agent 或多分支 research 的任务拆分方式。

对应到 RepoHarness：

- `docs/04` 的 search/open/find/python 工具族。
- `docs/09` 的 parallel research scaffold。
- `docs/10` 的 context compaction 与 research summary。

### 2.4 `deepseek-v3-2`

适合什么时候读：

作为 DeepSeek V4 的背景补读，不应早于 DeepSeek V4。

必须读的内容：

- scalable RL framework。
- agentic task synthesis。
- large-scale agentic tasks。
- 与 V4 的 post-training / infrastructure 延续关系。

对应到 RepoHarness：

- 主要用于补充 `docs/02` 和 `docs/06` 的任务合成与大规模 RL 背景。

## 3. 第二阶段补读：项目雏形出来后增强系统深度

### 3.1 `minimax-m1`

原始优先级：P0.5。

必须读的内容：

- CISPO、GRPO、DAPO 对比：用于理解 RL scaling 算法差异，不需要在 RepoHarness 中实现。
- RL data and reward：verifiable 和 non-verifiable tasks 的混合。
- Software Engineering environments：SWE-bench style real-world software engineering environments、execution-based rewards、sandboxed workflow。
- GenRM 与 reward hacking：长度偏置、在线监控、reward recalibration。
- Long-context RL：从 40K 到 80K 的扩展策略。

项目价值：

用于加强 `docs/07` 的 reward metadata 和 reward hacking 边界，也能帮助你解释为什么 RepoHarness 只做 verifier-aligned reward metadata，不声称提出 RL 算法。

### 3.2 `minimax-m2-1`

原始优先级：P0.5。

必须读的内容：

- SWE scaling：10,000+ runnable PRs、140,000+ variable tasks。
- Multi-scaffold rejection sampling。
- Runnable Docker environments。
- SWE-Test task inversion：让模型写测试用例。
- Agent-as-a-Verifier：execution、interaction、visual 三层验证。
- Context Management for search agents。

项目价值：

用于扩展 `docs/06` 的任务构造和 `docs/07` 的 Agent-as-a-Verifier。第一版可先实现 unit-test verifier，第二版再考虑 Playwright 或 agent-based verifier。

### 3.3 `step-3-5-flash`

原始优先级：P0.5。

必须读的内容：

- verifiable reward 与 non-verifiable reward 的统一 post-training recipe。
- GenRM。
- Agent Reward。
- Session-Router、Kubernetes、Tmux。
- scalable code agent infrastructure。

项目价值：

适合补强 `docs/02` 的 control plane / execution plane 和 `docs/07` 的 reward 分类。若实现 CLI runner，可以参考 Session-Router / Tmux 的任务会话思想。

### 3.4 `seed1-8`

原始优先级：P0.5。

必须读的内容：

- generalized real-world agency。
- search、code execution、GUI interaction 的统一 agentic interface。
- agentic search、agentic coding、tool use、GUI operation evaluation。
- AInstein-SWE-Bench、U-Artifacts、WideSearch、MM-BrowseComp 等 real-world benchmark 设计。
- appendix 中 scientific research coding task 的完整 agent response summary。

项目价值：

适合把 RepoHarness 从“软件工程 agent harness”扩展到“search/code/GUI 统一任务接口”。第一版只需吸收 evaluation taxonomy，不必实现 GUI。

### 3.5 `seed2-0`

原始优先级：P0.5。

必须读的内容：

- real-world complexity。
- long-horizon tasks。
- scientific research、complex software development、autonomous documentation learning。
- agent systems 难以构建 workflow 和长期积累经验的分析。

项目价值：

主要用于 `docs/12` 的项目叙事和未来方向，不是第一版实现蓝图。

## 4. 安全、权限和产品边界补读

这些报告不一定教你如何训练 agentic model，但非常适合补充“产品级 agent harness 的安全边界、权限边界、prompt injection、sandbox、评测风险”。当你的 RepoHarness 已经能跑小规模任务后，应把这些内容补进 README 和设计边界。

### 4.1 `openai-codex`

原始优先级：P1。

必须读的内容：

- Codex runs in cloud container with no internet access。
- container preloaded with code、dependencies、tooling。
- model trajectory begins after setup。
- read/edit files、execute commands、tests、linters、type checkers。
- test-until-pass training behavior。
- network sandboxing、filesystem sandboxing。
- prompt injection evaluation tailored to coding environment。
- environment perturbations and synthetic environment generation for difficult coding constraints。

项目价值：

直接支撑 `docs/05` 的 permission/sandbox 保守表述，和 `docs/10` 的 prompt injection / impossible task / failure diagnostics。

### 4.2 `openai-gpt-5-codex`、`openai-gpt-5-1-codex-max`、`openai-gpt-5-2-codex`、`openai-gpt-5-3-codex`

原始优先级：P1。

必须读的内容：

- coding RL on real-world coding tasks。
- agent sandbox：cloud isolated container、local macOS Seatbelt、Linux seccomp/landlock。
- configurable network access、allowlist、denylist。
- tool use、environment、approval boundary。
- prompt injection and malicious coding safety。
- coding benchmark and product benchmark limitations。

项目价值：

用于把 RepoHarness 的 `permission_mode`、`execution_mode`、`network_policy`、`approval_boundary` 写得更专业。第一版不要声称达到这些系统卡中的安全强度。

### 4.3 `openai-gpt-5-5`

原始优先级：P1 暂缓。

当前处理：

本地 `source_url.txt` 标记为 “No primary public technical report verified yet”。在没有官方 primary technical report 前，不应作为必须阅读对象，也不应在项目文档中引用它来支撑训练方法。

### 4.4 `anthropic-claude-sonnet-opus-4x`

原始优先级：P1。

必须读的内容：

- OSWorld-Verified、WebArena、WebArena-Verified、tau-bench、MCP-Atlas 等 agentic evaluation。
- reward hacking and overly agentic actions。
- realistic agentic coding scenarios：instruction following、safety、verification、efficiency、adaptability、honesty。
- malicious computer use and sandboxed environment。
- prompt injection risk in coding、computer use、browser use environments。
- multi-agent BrowseComp 和 DeepSearchQA 设置。
- permission fatigue、overly agentic GUI actions。

项目价值：

用于 `docs/10` 的 failure diagnostics 和 `docs/12` 的面试案例。特别要吸收“验证、诚实、效率、适应性”这些行为评测维度。

### 4.5 `xai-grok-4`、`xai-grok-4-1`、`xai-grok-4-fast`

原始优先级：P1。

必须读的内容：

- tool-use RL。
- code interpreter、web browsing。
- model-based graders。
- AgentHarm、AgentDojo、prompt injection、refusal/misuse eval。
- safety boundary 和 misuse evaluation。

项目价值：

用于补充 `docs/07` 的 model-based grader 和 `docs/10` 的 prompt injection / misuse / refusal 边界。不是第一版 coding harness 的核心实现来源。

### 4.6 `google-gemini-3`、`google-gemini-3-1-pro`

原始优先级：P1。

必须读的内容：

- agentic coding。
- long-context。
- Terminal-Bench、SWE-Bench、Antigravity。
- agentic tool-use evaluation。
- prompt injection safety。
- 1M context 和 long-horizon planning。

项目价值：

用于补充评测 taxonomy 和 long-context / agentic coding 的产品侧边界。它更像 model card，不是训练 harness 公开方案。

## 5. 专项补读：reward、retrieval、formal verifier、小模型 agent

### 5.1 `skywork-reward-v2`

原始优先级：P2。

必须读的内容：

- reward model training。
- SynPref-40M。
- preference data。
- style bias resistance。
- judge evaluation。

项目价值：

如果 RepoHarness 后续要做 LLM judge、preference pair export、reward model benchmark，再读它。第一版只做 unit-test verifier 和 reward metadata 时可以延后。

### 5.2 `chroma-context-1`

原始优先级：P2。

必须读的内容：

- retrieval as subagent。
- context construction。
- context compression。
- agentic search / retrieval sub-agent。

项目价值：

用于 `docs/10` 的 context/session 扩展。如果第一版 coding tasks 只用 `grep`、`list_files` 和 `read_file`，可以暂缓。

### 5.3 `cognition-swe-grep`

原始优先级：P2。

必须读的内容：

- RL for multi-turn code context retrieval。
- fast search harness。
- coding agent context retrieval 子模块。

项目价值：

如果你要把 RepoHarness 做成“检索能力也可训练和评测”的项目，这篇很有价值。第一版可以先用 ripgrep 工具，不需要复现 retrieval RL。

### 5.4 `cognition-swe-1-6`

原始优先级：P2。

必须读的内容：

- SWE agent 产品材料。
- RL infrastructure。
- real software engineering agent。
- eval/harness boundary。

项目价值：

用于产品叙事和 benchmark 边界补充，不是第一版实现必读。

### 5.5 `cognition-kevin-32b`

原始优先级：P2。

必须读的内容：

- CUDA kernel agent。
- self-refinement。
- execution feedback。
- multi-turn RL。

项目价值：

作为 specialized agent case study。除非你想展示“verifier feedback 对特定工程领域的训练价值”，否则延后。

### 5.6 `microsoft-rstar2-agent`

原始优先级：P1。

必须读的内容：

- 小模型 Python tool environment。
- GRPO-RoC。
- multi-stage RL。
- tool execution feedback。
- high-throughput environment。

项目价值：

适合补充“小模型也可以通过环境反馈和工具执行训练 agentic 能力”的叙事。对第一版 software engineering harness 不是最核心。

### 5.7 `microsoft-phi-4-reasoning`

原始优先级：P1 背景。

必须读的内容：

- outcome-based RL。
- reasoning distillation。
- reasoning post-training 与 agentic training 的边界。

项目价值：

用于理论背景。不要把它当成 agent harness 设计来源。

### 5.8 `nvidia-nemotron-cascade-2`、`nvidia-nemotron-3`

原始优先级：P1。

必须读的内容：

- Cascade RL。
- multi-domain on-policy distillation。
- agentic capability。
- open-weight / open-data / recipe。
- long-context、agentic reasoning recipe。

项目价值：

用于补充 open model post-training recipe 和 distillation 叙事。第一版 RepoHarness 不需要依赖它们。

### 5.9 `longcat-flash-prover`

原始优先级：P2。

必须读的内容：

- Lean4 tool-integrated RL。
- verifier。
- Hybrid-Experts Iteration。
- HisPO。
- reward hacking 防护。

项目价值：

如果未来扩展 formal reasoning / theorem proving environment，再读。第一版 coding harness 只需知道 formal verifier 是 verifier family 的一种。

## 6. 按 RepoHarness 模块反向索引该读哪些报告

### 6.1 Agent loop 与消息协议

优先读：

1. `cursor-composer-2`：agent、environment、actions、tool calls、reward 的形式化。
2. `tongyi-deepresearch`：thought-action-observation triplets。
3. `ui-tars-2`：history、memory、environment、action、observation。
4. `kimi-k2`：multi-turn trajectory generation。
5. `deepseek-v4`：interleaved thinking 和 tool-result turns。

实现落点：

- tool result 必须回填到下一轮模型上下文。
- final verifier 必须在 agent 停止后重新运行。
- `agent_stop_reason`、`final_verifier_status`、`run_outcome` 必须分开。

### 6.2 工具系统和工具协议

优先读：

1. `qwen3-coder-next`：多种 tool chat templates 和 format-invariant tool use。
2. `deepseek-v4`：DSML、XML-style invocation、quick instruction。
3. `kimi-k2`：tool calling token template。
4. `openai-codex` 和 `openai-gpt-5-codex`：coding agent 工具边界。
5. `cursor-composer-2`：真实产品工具集。

实现落点：

- 第一版 ReAct 类模型可见工具清单应是 `list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`bash`、`run_tests`、`git_diff`；`apply_patch` 默认作为 Workspace Adapter 内部能力或 single-shot patch scaffold 的处理能力。
- `run_tests` 不应只是普通 bash，它要产生结构化 `VerifierResult`。
- 工具调用格式错误要进入 events 和 reward metadata。

### 6.3 Workspace、sandbox、permission

优先读：

1. `deepseek-v4`：DSec。
2. `openai-codex` 和 GPT-5-Codex 系列：network sandboxing、filesystem sandboxing、approval boundary。
3. `qwen3-coder-next`：reward hacking blocker、GitHub future commit leakage。
4. `kat-coder-v2`：KwaiEnv sandbox orchestration。
5. `kimi-k1-5`：code execution sandbox。
6. `cursor-composer-2`：Anyrun、snapshot/fork、controlled egress。

实现落点：

- permission 和 sandbox 必须分开。
- 第一版只写 Docker-based executable repository environment，不写生产级安全沙箱。
- 默认拒绝或强约束 `rm -rf`、`sudo`、`ssh`、`scp`、`curl | sh`、workspace 外写入。
- 对 `git clone`、`git remote add`、`curl`、`wget` 这类可能泄露 benchmark 答案或未来 commit 的命令做风险标记。

### 6.4 Task adapter 与 environment construction

优先读：

1. `qwen3-coder-next`：GitHub PR mining、runnable environments、synthetic executable tasks。
2. `glm-5`：SWE/terminal/search/slide environments。
3. `kat-coder-v2`：AutoBuilder、F2P/P2P、Docker image + build scripts。
4. `minimax-m2-1`：runnable PRs、variable tasks、SWE-Test。
5. `cursor-composer-2`：CursorBench。
6. `longcat-flash-thinking-2601`：tool dependency graph、environment expansion。

实现落点：

- 每个 task 必须有 `id`、`task_version`、`source_kind`、`repo`、`issue`、`test_command`、`timeouts` 和 `environment`。
- 后续预留 `base_commit`、`gold_patch`、`fail_to_pass_tests`、`pass_to_pass_tests`。
- baseline gate 必须先判断 task 是 valid、invalid 还是 flaky。

### 6.5 Verifier、reward、evaluation

优先读：

1. `deepseek-r1`：RLVR、GRPO、verifiable rewards。
2. `kimi-k2`：Verifiable Rewards Gym、self-critique rubric reward。
3. `qwen3`：General RL 三类 reward。
4. `qwen3-coder-next`：execution reward、tool-format penalty、unfinished trajectory penalty、reward hacking blocker。
5. `glm-5`：per-task reward microservices、environment collapse filtering。
6. `minimax-m1`：GenRM、length bias、reward recalibration。
7. `skywork-reward-v2`：reward model 专项。

实现落点：

- reward 应保存为 `RewardMetadata`，不是只保存一个浮点数。
- reward 来源必须可追溯到 final verifier、events、diff、tool-call statistics。
- `run_tests` 是 feedback verifier，final verifier 才是最终评测和训练导出的默认依据。

### 6.6 Trajectory store 与 training export

优先读：

1. `kimi-k2`：multi-turn trajectory generation 与 filtering。
2. `glm-5`：统一 message-list 表示、TITO、trajectory standardization。
3. `kat-coder-v2`：Trajectory Manager。
4. `cursor-composer-2`：long rollouts、self-summarizations、snapshotting。
5. `deepseek-v4`：trajectory log/replay/provenance。
6. `longcat-flash-thinking-2601`：large-scale multi-environment trajectories。

实现落点：

- `transcript.jsonl` 面向对话重放。
- `events.jsonl` 面向统计、reward、diagnostics、export。
- 训练导出至少支持 SFT JSONL、RL rollout JSONL、preference pair JSONL。

### 6.7 Scaffold 与 multi-agent

优先读：

1. `kat-coder-v2`：multi-scaffold training、Claude Code / OpenCode / Kilo Code 等 scaffold 泛化。
2. `qwen3-coder-next`：cross-scaffold transfer、tool format robustness。
3. `kimi-k2-5`：Agent Swarm、PARL、critical steps。
4. `anthropic-claude-sonnet-opus-4x`：multi-agent BrowseComp / DeepSearchQA。
5. `cursor-composer-2`：真实 Cursor harness。

实现落点：

- 第一版实现 `single_shot_patch`、`simple_react`、`planner_coder_verifier`。
- 不实现真实远程多代理，不做后台 subagent cluster。
- 所有 scaffold 共用同一套工具、workspace、verifier、trajectory store。

### 6.8 Context、session、failure diagnostics

优先读：

1. `glm-5`：search context management、keep-recent、discard-all、hybrid context management。
2. `deepseek-v4`：million-token framework、agentic search、white-collar tasks。
3. `cursor-composer-2`：self-summarization、long rollout checkpointing。
4. `tongyi-deepresearch`：Context Management Mode。
5. `kimi-k2-5`：Agent Swarm as proactive context management。
6. `anthropic-claude-sonnet-opus-4x`：overly agentic behavior、honesty、verification、prompt injection。

实现落点：

- 工具输出必须截断，完整输出落盘。
- old test output 应摘要化。
- failure type 应包含 dependency、test timeout、assertion failure、permission denied、invalid tool call、context limit、patch apply failed、no progress、regression detected。

## 7. 最小阅读计划

如果只有三天时间，按这个顺序读：

1. `kimi-k2`：只读 3.1.1、3.2.1、3.2.2、3.3、Appendix B。
2. `deepseek-v4`：只读 5.1、5.2.3、5.2.4、5.2.5、5.3 code/search agent、5.4 real-world tasks。
3. `glm-5`：只读 3.3、3.6、4.1、4.2、6.2。
4. `qwen3-coder-next`：只读 GitHub PR executable environments、tool templates、multi-turn agentic RL、reward hacking blocker。
5. `kat-coder-v2`：只读 KwaiEnv、AutoBuilder、Trajectory Manager、多 scaffold。
6. `cursor-composer-2`：只读 agent definition、CursorBench、Anyrun、RL infrastructure。

如果有一周时间，加读：

7. `deepseek-r1`：GRPO、RLVR、R1 pipeline、distillation。
8. `qwen3`：Long-CoT Cold Start、Reasoning RL、General RL、Table 22。
9. `kimi-k1-5`：partial rollout、code execution sandbox、test case generation。
10. `longcat-flash-thinking-2601`：environment scaling、DORA、noise-aware training。
11. `tongyi-deepresearch`：search agent、context management、unified sandbox。

如果项目进入第二阶段，加读：

12. `ui-tars-2`：GUI/computer-use sandbox、多轮 RL、OSWorld。
13. `kimi-k2-5`：Agent Swarm、PARL、critical steps。
14. `openai-codex` 和 GPT-5-Codex 系列：sandbox、permission、prompt injection。
15. `anthropic-claude-sonnet-opus-4x`：agentic safety、overly agentic actions、multi-agent eval。

## 8. 对简历项目最有价值的实现顺序

读报告时要同步把内容转成实现任务。推荐顺序如下：

1. 实现最小 task schema 和 micro-repo fixtures。
2. 实现 workspace adapter：复制仓库、初始化 Git、执行命令、捕获 diff。
3. 实现工具系统：`list_files`、`read_file`、`grep`、`edit_file`、`create_file`、`bash`、`run_tests`、`git_diff`，并把 patch apply 保留为内部能力或 single-shot patch scaffold 能力。
4. 实现 permission system：`plan`、`ask`、`auto`、`deny` 四种模式。
5. 实现 agent loop：模型输出 tool call，工具结果回填，预算和终止条件。
6. 实现 baseline verifier、feedback verifier、final verifier。
7. 实现 reward metadata。
8. 实现 trajectory store：`transcript.jsonl` 和 `events.jsonl` 分离。
9. 实现 training exporter：SFT、RL rollout、preference pair 三类 JSONL。
10. 实现 evaluation runner：跑 20 到 50 个任务。
11. 实现 scaffold 对比：single-shot、simple ReAct、planner-coder-verifier。
12. 产出 demo artifact 包：task、transcript、events、final diff、verifier、metrics、summary、export samples。

## 9. 需要保守表述的边界

这些边界必须写进 README、设计文档和简历叙事中：

- RepoHarness 第一版是 lightweight harness，不是生产级安全沙箱。
- Docker execution mode 只能写成 Docker-based executable repository environment。
- reward 是 verifier-aligned reward metadata，不是新的 reinforcement learning 算法。
- public benchmark 不等于训练数据。
- model card / system card 不等于训练 recipe。
- tool schema 不等于完整 tool harness。
- `openai-gpt-5-5` 当前没有已核验 primary public technical report，不作为引用来源。
- 内部 benchmark、in-house harness、unreleased sandbox 的细节不能由工程常识补写。

## 10. 一句话结论

为了这个项目，最核心的阅读主线不是“哪家模型分数最高”，而是：

```text
Kimi K2 的 agentic data/reward 闭环
-> DeepSeek V4 的 rollout/sandbox/tool protocol
-> GLM-5 的 async agentic RL 和 environment scaling
-> Qwen3-Coder-Next / KAT-Coder-V2 / Cursor Composer 2 的真实 coding agent harness
-> OpenAI / Anthropic / Google / xAI system cards 的安全边界和产品评测
```

读完这些内容后，RepoHarness 的简历叙事应该聚焦在：

> 设计并实现一个训练友好的 repository-level software engineering agent harness，统一任务适配、工具执行、权限边界、可执行环境、verifier-aligned reward metadata、trajectory logging、evaluation runner 和 SFT / RL rollout / preference pair 数据导出。
