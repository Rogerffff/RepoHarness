# RepoHarness V3 中文简历项目写法

## 1. 文档定位

本文面向中国大模型企业招聘场景，目标是把 RepoHarness 写成一个有工业界系统复杂度的 Agent Harness 项目，而不是普通代码自动修复示例。本文按照“V3 已经完成最终验收，或者一个月内可以补齐 V3 验收”的投递口径编写。若实际投递时 V3 还没有完全验收，可以使用文末的“阶段性投递版”。

RepoHarness 的简历核心不应该是“做了一个能调用模型改代码的小工具”，而应该是：

```text
面向 agentic training / post-training 的软件工程 Agent Harness 基础设施：把真实或半真实仓库任务转化为可执行、多轮交互、可验证、可恢复、可审计、可导出的训练轨迹。
```

这个表达更贴近大模型企业当前关注的方向：可执行环境、工具调用协议、多轮 rollout、轨迹治理、验证器奖励、失败过滤、数据导出和评测闭环。

## 2. 面向简历的能力映射

简历中不需要直接写清楚设计来自哪些开源项目或哪些技术报告。更好的写法是把背景研究沉淀成系统能力，让面试官看到项目覆盖了真实 Agent Harness 的关键复杂度。

### 2.1 Agent Runtime 复杂性

一个有展示价值的 Coding Agent Harness 不应该只是单次模型调用，而应该具备完整运行时链路。RepoHarness 简历表述中可以突出这些结构：

- `query loop`：多轮模型请求、工具调用、工具结果回填、终止条件、恢复策略和上下文预算控制。
- `tool execution lifecycle`：工具查找、输入 schema 校验、权限检查、前后置 hook、工具执行、结果映射、大输出 artifact 化。
- `tool_use / tool_result pairing`：每个模型工具调用都必须有终态工具结果，恢复、中断和异常路径也不能破坏消息配对。
- `permission boundary`：读、写、执行、网络、破坏性命令分层，不把所有 shell 命令都当成普通工具。
- `context compaction`：长工具输出、长轨迹和上下文预算需要压缩、摘要和 artifact 引用，而不是把所有 stdout 塞回模型。
- `transcript / event separation`：模型可见对话和系统审计事件分离，便于训练导出、回放和问题定位。
- `hook and extension point`：工具执行前后、验证器之后、导出之前可以有可审计扩展点，但不让 hook 破坏工具结果配对和训练污染边界。

对应到简历语言，可以写成：

```text
构建具备 query loop、tool lifecycle、permission boundary、context compaction 和 tool result pairing 的 Agent Harness Runtime，而不是一次性 prompt demo。
```

### 2.2 Agentic Training Infrastructure 能力方向

以下映射适合在简历和面试中展开：

| 能力方向 | RepoHarness 中的对应设计 | 简历关键词 |
| --- | --- | --- |
| Dataset、Sandbox、Scaffold、Verifier 解耦 | TaskAdapter、WorkspaceAdapter、Scaffold Registry、Verifier、Exporter 分层 | agentic RunSpec、Trajectory Manager、scaffold 对比 |
| Executable coding task 与 F2P/P2P verifier | 真实仓库任务、SWE-Bench-like 小子集、FAIL_TO_PASS / PASS_TO_PASS、网络和测试绕过防护 | executable repository task、verifier-aligned reward、reward hacking blocker |
| Rollout service、WAL、execution substrate、trajectory replay / provenance | run directory、events.jsonl、transcript.jsonl、artifact manifest、resume manifest、container execution facts | rollout provenance、turn-level WAL、fault-tolerant rollout |
| Multi-task rollout orchestrator、failure filtering、environment scaling | 可恢复 experiment runner、失败分类、Docker backend、真实仓库和 SWE-Bench-like task adapter | single-machine rollout orchestrator、failure distribution |
| Tool calling、agentic data synthesis、verifiable reward | 工具协议、ToolResult、VerifierResult、reward metadata、训练导出过滤 | tool-use trajectory、verifiable reward、quality filtering |
| 真实 codebase environment、long rollout、code quality metrics | Docker 仓库级环境、长轨迹诊断、context compaction、patch size / tool count / test count 指标 | real-codebase agent harness、long rollout diagnostics |

简历中最有吸引力的总结是：

```text
RepoHarness 把 agentic rollout、executable environment、verifiable reward、trajectory manager 和 failure filtering 这些训练基础设施能力降维实现为单机可运行、可审计、可验收的工程系统。
```

## 3. 推荐项目标题

最推荐：

```text
RepoHarness：面向 Agentic Post-training 的软件工程智能体 Harness 与轨迹数据基础设施
```

更偏系统工程：

```text
RepoHarness：仓库级 Coding Agent Harness、Docker 执行环境与训练轨迹导出系统
```

更偏大模型训练数据：

```text
RepoHarness：面向代码智能体 Rollout 的可执行任务、验证器奖励与训练数据生成框架
```

不建议写：

```text
完整复现某个商业 Coding Agent 产品
完整 SWE-Bench 榜单复现
生产级安全沙箱
自研强化学习训练框架
```

这些说法容易让面试官追问到项目没有覆盖的生产级边界。

## 4. 中文简历主描述

### 4.1 大模型基础设施岗位推荐版本

```text
RepoHarness 是一个面向 agentic training / post-training 的软件工程智能体 Harness。我围绕生产级 Coding Agent Runtime 中常见的 query loop、tool lifecycle、permission boundary、context compaction 和 tool result pairing 设计，并结合 executable environment、rollout provenance、verifiable reward 和 failure filtering 等训练基础设施方向，独立实现了仓库级任务执行、Docker 工作区、工具协议、Agent Loop、轨迹记录、final verifier、reward metadata、训练导出审计和最终机器验收闭环。
```

### 4.2 更适合一页简历的压缩版本

```text
RepoHarness 是一个面向代码智能体 post-training 的仓库级 Agent Harness，支持真实或半真实 repository-level task、Docker 可执行环境、多轮工具调用、轨迹记录、final verifier、可恢复 rollout、failure diagnostics，以及 SFT / RL rollout / preference 数据导出审计，用于把软件工程任务转化为可执行、可验证、可过滤的训练轨迹。
```

### 4.3 强调工业复杂度的版本

```text
RepoHarness 不是简单的代码修复 demo，而是一个训练友好的 Agent Harness Runtime：系统拆分为 task adapter、workspace backend、tool runtime、permission policy、agent scaffold、trajectory store、verifier / reward、experiment runner 和 export audit 多个层次，统一记录模型消息、工具调用、容器执行事实、patch、测试证据、失败原因和训练资格，保证一次仓库级修复过程可以被回放、验收和导出为训练数据。
```

## 5. 技术栈写法

推荐写：

```text
Python 3.11、Pydantic、PyYAML、pytest、Docker、Git、JSONL、CLI、DeepSeek / OpenAI Provider Adapter、Agent Loop、Tool Runtime、Verifier、SFT / RL Rollout / Preference Export
```

如果版面较紧，可以写：

```text
Python、Pydantic、pytest、Docker、Git、JSONL、Agent Harness、Verifier、Training Data Export
```

## 6. 最推荐的简历项目条目

下面这一版适合直接放入中文简历。它默认 V3 已经完成，或者你可以在面试前补齐对应实现和验收。

```text
RepoHarness：面向 Agentic Post-training 的软件工程智能体 Harness 与轨迹数据基础设施 | 独立开发者
技术栈：Python 3.11、Pydantic、pytest、Docker、Git、JSONL、DeepSeek / OpenAI Provider Adapter

- 设计并实现仓库级 Coding Agent Harness，将 task adapter、Docker workspace backend、tool runtime、permission policy、Agent Loop、trajectory store、verifier / reward、experiment runner 和 export audit 解耦，形成 task -> executable workspace -> tools -> rollout -> final verifier -> training export 的完整闭环。
- 实现生产级 Agent Runtime 常见的 query loop、tool execution lifecycle、tool_use / tool_result pairing、permission boundary 和 context compaction 设计，保证多轮工具调用、权限拒绝、中断恢复、长输出截断和异常路径下仍能生成可回放、可审计的轨迹。
- 构建 Docker-based executable repository environment，覆盖 source checkout、setup、agent workspace、工具执行、final patch capture、独立 verification workspace、strict patch replay 和 formal final verifier，并记录 image、platform、mount policy、network policy、timeout、stdout/stderr artifact、cleanup status 等 container execution facts。
- 接入真实 repository-level task 与 SWE-Bench-like 小子集，固定 source hash、base commit、dataset revision、test patch、FAIL_TO_PASS / PASS_TO_PASS、environment spec 和 verifier plan；将官方 SWE-Bench harness 仅作为前置可实现性证明，最终由 RepoHarness 自有 adapter / verifier 生成验收证据。
- 实现训练友好的 rollout provenance 和 failure filtering：分离 transcript.jsonl 与 events.jsonl，记录 tool_call_id、artifact refs、patch diff、verifier result、reward metadata、context revision、interrupted checkpoint、retry / skip decision 和 failure distribution。
- 将 final verifier 作为 evaluation 和 reward 的唯一可信来源，区分 feedback verifier 与 formal final verifier，防止 hidden tests、gold patch、provider raw response、reward metadata、run outcome 或 final verifier hidden result 泄漏回模型上下文或正式训练 payload。
- 支持 SFT、RL rollout、preference 三类训练 JSONL 导出，使用 export_manifest、audit_report、contamination denylist 和 acceptance bundle 绑定 run metadata、tool schema snapshot、source facts、verifier evidence、reward formula version 和 sha256，保证 diagnostic-only、skipped、invalid 样本不会进入正式训练数据。
- 构建机器可复查验收体系，生成 docker phase coverage matrix、experiment resume manifest、context compaction report、failure diagnostics report、acceptance_bundle_manifest 和 v3_acceptance_report；inspect 命令会重新读取 evidence refs 与 sha256，拒绝 summary 与真实证据漂移。
```

## 7. 一页简历压缩版

如果你的简历只能放 4 条项目描述，建议使用下面这一版。

```text
RepoHarness：面向 Agentic Post-training 的软件工程智能体 Harness 与轨迹数据基础设施 | 独立开发者
技术栈：Python、Pydantic、pytest、Docker、Git、JSONL、DeepSeek / OpenAI Provider Adapter

- 构建仓库级 Coding Agent Harness，解耦 task adapter、workspace backend、tool runtime、permission policy、Agent Loop、trajectory store、verifier / reward 和 export audit，形成可执行、可验证、可导出的多轮 rollout 闭环。
- 实现 query loop、tool lifecycle、tool_use / tool_result pairing 和 context compaction，支持工具 schema 校验、权限拒绝、长输出 artifact 化、异常事件记录和轨迹回放，避免把 Agent Harness 简化为单次 prompt 调用。
- 接入 Docker 可执行仓库环境、真实 repository-level task 和 SWE-Bench-like 小子集，固定 source hash、base commit、test patch、FAIL_TO_PASS / PASS_TO_PASS 和 verifier plan，通过独立 verification workspace 执行 strict patch replay final verifier。
- 实现训练数据导出审计和机器验收，支持 SFT / RL rollout / preference JSONL，统一扫描 hidden tests、gold patch、provider raw response、reasoning summary、Authorization marker、本机绝对路径等污染字段，并用 manifest、sha256 和 inspect 命令绑定最终证据。
```

## 8. 更偏大厂招聘关键词的版本

这一版更适合投递大模型公司中的 Agent Infra、Post-training、Data Engine、Evaluation Harness、Coding Agent 方向。

```text
- 以 Dataset-Sandbox-Scaffold-Verifier 解耦为核心设计 RepoHarness 的 RunSpec 和模块边界，使同一任务可以在不同 model provider、scaffold、tool policy、workspace backend 和 verifier policy 下重复 rollout 并进行可比评测。
- 面向 executable coding task 和 F2P/P2P verifier 接入真实仓库任务与 SWE-Bench-like 小子集，记录 base commit、test patch、FAIL_TO_PASS、PASS_TO_PASS、source tree hash 和 final verifier evidence，防止只用本地 toy fixture 伪装仓库级任务。
- 围绕 rollout provenance、fault-tolerant generation 和 failure filtering 实现单机可恢复 experiment runner，记录 run state、checkpoint manifest、retry policy、provider transient failure、Docker backend failure、environment setup failure、parser low confidence 和 deterministic verifier failure。
- 将 tool-use trajectory、artifact、patch、verifier result 和 reward metadata 统一进训练导出链路，使成功、失败和 diagnostic-only 样本都能被结构化过滤和复查。
```

## 9. 面试时可以强调的系统复杂性

面试官如果问“这个项目复杂在哪里”，建议不要只说“接了 Docker”和“能导出 JSONL”。可以按下面几个层次回答。

### 9.1 Agent Runtime 复杂性

```text
系统不是单次调用模型，而是一个完整的 Agent Runtime。模型会产生工具调用，系统要解析工具调用、校验 schema、做权限判断、执行工具、保存大输出 artifact、生成 ToolResult，再把 ToolResult 回填到下一轮模型上下文。这里必须保证 tool_call_id 配对、上下文预算、异常恢复、权限拒绝、工具超时和终止条件都能被记录，否则导出的训练轨迹就是不可信的。
```

### 9.2 训练数据复杂性

```text
训练数据不是把最终答案写成 JSONL 就可以了。RepoHarness 需要区分模型可见内容和 evaluator-only 内容，不能把 gold patch、test patch、hidden tests、FAIL_TO_PASS / PASS_TO_PASS、provider raw response 或 final verifier hidden result 泄漏到 SFT target、RL rollout observation 或 preference target 里。每条样本都要有 training eligibility、invalid reason、audit item 和 artifact ref。
```

### 9.3 Verifier 与 Reward 复杂性

```text
我把 final verifier 作为 evaluation 和 reward 的唯一可信来源，feedback verifier 只作为模型中间反馈。这样可以避免中间测试通过就直接给 reward，也可以避免 bash 里跑 pytest 的输出绕过 verifier policy。RewardMetadata 只引用 final verifier、patch stats、tool stats 和 failure diagnostics，不声称实现新的 RL 算法，但可以直接服务后续 RL rollout 或 preference data。
```

### 9.4 可恢复 Rollout 复杂性

```text
真实仓库任务和真实 provider 都会有超时、依赖失败、环境不稳定、模型输出格式错误等问题，所以 Experiment Runner 必须支持 pending、running、completed、failed、skipped、interrupted 等状态，并记录 checkpoint、resume policy 和 retry decision。这个设计对应工业界报告里的 fault-tolerant rollout service，只是我把它降维成单机可审计版本。
```

### 9.5 工业能力映射

```text
这个项目不是单点功能 demo，而是把工业界 Agent Harness 的共性能力落地成工程闭环：环境解耦、executable task、anti reward hacking、rollout provenance、execution substrate、rollout orchestrator、failure filtering、tool-use trajectory 和 verifiable reward。RepoHarness 的目标是让这些方向真正能跑、能验收、能导出数据。
```

## 10. 如果 V3 尚未完成最终验收的阶段性投递版

如果你现在就要投递，但 V3 还没有全部实现，可以使用下面这版。它把已经完成的可实现性实验写进去，同时把未来一个月内要补齐的部分写成“正在实现”和“按阶段推进”。

```text
RepoHarness：面向 Agentic Post-training 的软件工程智能体 Harness 与轨迹数据基础设施 | 独立开发者
技术栈：Python、Pydantic、pytest、Docker、Git、JSONL、DeepSeek / OpenAI Provider Adapter

- 已完成 V1/V2：实现 task -> workspace -> tools -> Agent Loop -> trajectory -> final verifier -> reward/eval/export 的训练轨迹闭环，支持真实 provider、mock provider、多 scaffold、多 rollout、SFT / RL rollout / preference 导出和 export audit。
- 正在推进 V3：围绕生产级 Agent Runtime 和 agentic training infrastructure 方向，升级 Docker Workspace Backend、真实 repository-level task、SWE-Bench-like 小子集、可恢复 experiment runner、context compaction 和 V3 acceptance bundle。
- 已完成本机 V3 前置可实现性实验：在 Apple Silicon / linux/arm64 Docker Desktop 环境下，固定 `princeton-nlp/SWE-bench_Lite` revision，完成 3 个候选任务的 gold patch evaluation，通过 `pytest-dev__pytest-7220`、`pytest-dev__pytest-8365`、`sympy__sympy-24909`。
- 当前重点补齐 RepoHarness 自有 adapter / verifier / Docker evidence 链路，确保官方 SWE-Bench harness 只作为前置证明，最终验收由 RepoHarness 自己生成 source facts、container execution facts、verifier evidence、export audit 和 v3_acceptance_report。
```

## 11. 可以写和不建议写

可以写：

- Agent Harness Runtime。
- Coding Agent 训练轨迹基础设施。
- Agentic post-training data pipeline。
- Docker-based executable repository environment。
- Repository-level executable task。
- SWE-Bench-like small subset adapter。
- Multi-turn tool-use rollout。
- Verifier-aligned reward metadata。
- Rollout provenance。
- Turn-level WAL。
- Failure filtering。
- Anti reward hacking checks。
- SFT / RL rollout / preference export audit。
- Acceptance bundle 和 inspect 命令机器复查。

不建议写：

- 复现某个商业 Coding Agent 产品。
- 完整 SWE-Bench Lite 榜单复现。
- 生产级安全沙箱。
- 分布式 RL 训练系统。
- 新的强化学习算法。
- 已训练出 Coding Agent。
- 工业级 DSec 或云端多租户隔离。
- 完整 MCP / 插件市场。

## 12. 推荐最终简历版本

如果只能放一个版本，建议使用下面这段。它最适合中国大模型企业的 Agent Infra、Post-training、Evaluation、Data Engine 和 Coding Agent 岗位。

```text
RepoHarness：面向 Agentic Post-training 的软件工程智能体 Harness 与轨迹数据基础设施 | 独立开发者
技术栈：Python 3.11、Pydantic、pytest、Docker、Git、JSONL、DeepSeek / OpenAI Provider Adapter

- 设计并实现仓库级 Coding Agent Harness，解耦 task adapter、Docker workspace backend、tool runtime、permission policy、Agent Loop、trajectory store、verifier / reward、experiment runner 和 export audit，形成可执行、可验证、可恢复、可导出的多轮 rollout 闭环。
- 实现生产级 Agent Runtime 常见的 query loop、tool execution lifecycle、tool_use / tool_result pairing、permission boundary 和 context compaction，保证多轮工具调用、权限拒绝、中断恢复、长输出截断和异常路径下仍能产出可审计轨迹。
- 围绕 Dataset-Sandbox-Scaffold-Verifier 解耦、executable coding task、rollout provenance、failure filtering 和 verifiable reward 等方向，落地为单机可运行的训练轨迹基础设施。
- 接入 Docker 可执行仓库环境、真实 repository-level task 和 SWE-Bench-like 小子集，固定 source hash、base commit、test patch、FAIL_TO_PASS / PASS_TO_PASS 和 verifier plan，通过独立 verification workspace 执行 strict patch replay final verifier。
- 实现 SFT / RL rollout / preference 训练数据导出审计，统一扫描 hidden tests、gold patch、provider raw response、reasoning summary、Authorization marker、本机绝对路径等污染字段，并通过 manifest、sha256、command log、acceptance bundle 和 inspect 命令复查最终证据。
```
