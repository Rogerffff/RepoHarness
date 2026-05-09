# RepoHarness 系统学习路线

## 0. 文档定位

这份文档是 `docs/project_tut_for_me/` 的主学习入口。它不是新的项目设计文档，也不是 V5 验收结论；它的作用是把 RepoHarness 这个项目按照“能真正看懂底层实现”的顺序拆成一套教学路线。

当前学习目标不是只记住几句项目介绍，而是逐步回答这些问题：

- RepoHarness 为什么是面向 agentic training 的软件工程智能体 Harness，而不是普通的代码智能体演示。
- 一个任务如何从任务定义、真实或半真实仓库来源、可见性边界和验证器配置，变成一个可以执行的运行对象。
- `repo-harness run-task` 如何把任务、工作区、模型、工具、轨迹、验证器、奖励元数据和训练导出串成完整闭环。
- Docker-based executable repository environment 如何执行命令、隔离工作区路径、保存命令事实和支持 final verifier。
- 模型可见内容、工具结果、隐藏验证证据、reward metadata 和训练导出字段之间的边界如何防止泄漏。
- V1 到 V5 每一版具体补了什么能力，为什么 V5 的重点是面试级结果包，而不是重新做一个更大的产品版本。

你已经看完了 `session-notes/01-run-task-architecture.md`，所以后续不再从“命令怎么运行”这种单点开始，而是把它放回完整系统链路中理解。

## 0.1 当前学习偏好

根据你当前的反馈，后续讲解采用下面的优先级：

1. 优先深入代码实现，而不是重复高层架构。架构部分只快速校准模块边界，尽快进入源码级函数调用、字段含义和真实运行产物。
2. 重点关注真实 provider 模型、SWE-Bench-like 数据和 GitHub PR / issue 数据作为输入时，如何被 RepoHarness 转换成可运行任务、可执行工作区、模型上下文、验证器计划和训练导出样本。
3. Python、Pydantic、pytest 和 Docker 按“项目代码里实际怎么用”的方式讲解。不会先单独讲一大段通用教程，而是在读到对应实现时解释，例如 Pydantic model validation、pytest 命令解析、Docker container execution facts、workspace path boundary 等。

因此后续讲解应默认采用“代码优先”的节奏：

```text
快速复盘模块边界
-> 读 schema 和 adapter
-> 读真实输入 freeze / materialization
-> 读 run_task 主编排
-> 读 Docker workspace 和 pytest verifier
-> 读 provider client 和 agent loop
-> 读 trajectory / export / acceptance evidence
```

## 1. 当前材料处理原则

现有 `docs/project_tut_for_me/` 目录里的材料不建议整批删除。它们的问题主要是组织混乱，而不是全部无效。

建议这样理解现有文件：

- `README.md`：作为目录索引使用，但需要以这份 `00-learning-plan.md` 作为新的主学习路线。
- `00-v4-deep-dive-plan.md`：保留为 V4 深挖计划，但它只覆盖 V4，不覆盖完整项目学习路线。
- `01-v4-runtime-architecture.md` 到 `05-final-verifier-reward-export-acceptance.md`：保留为 V4 主讲义，适合在学习到 V4 时阅读。
- `session-notes/01-run-task-architecture.md`：保留为一次真实 run-task 的详细实录，不再作为全项目第一入口。
- `session-notes/02` 到 `session-notes/05`：当前更像课堂摘要，可以作为补充，不作为主线。
- `代码阅读QA.md`：保留为局部概念问答，例如 Python、Pydantic、上下文管理器和 RunRecorder。
- `99-next-questions.md`：保留为后续追问清单。

后续如果要整理目录，建议把正式教程、实战 walkthrough、问答和待办清单分开，但当前为了不影响正在进行的 V5 开发，不做大规模移动或删除。

## 2. 学习总策略

最适合这个项目的学习方式是“三遍法”。

第一遍：建立完整地图。

只看关键文档和主链路代码，不追求每个辅助函数都读完。目标是能画出：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

第二遍：纵向追踪一次真实运行。

从 `repo-harness run-task` 的入口开始，跟着一个 run directory 里的 `task.yaml`、`baseline.json`、`transcript.jsonl`、`events.jsonl`、`final.patch`、`verifier.json`、`reward.json` 和 `run_metadata.json`，看每个文件由哪段代码写出。

第三遍：横向拆模块。

按任务、工作区、工具、模型、上下文、验证器、轨迹、导出、验收这些模块分别深挖。这个阶段才适合逐个文件读实现细节和测试。

## 3. 推荐学习顺序

### 第 0 章：项目定位和边界

目标：先弄清楚 RepoHarness 是什么、不是什麼，以及它为什么对 agentic training 有意义。

必读文档：

- `AGENTS.md`
- `docs/00-reading-guide.md`
- `docs/01-project-positioning-and-requirements.md`
- `docs/13-agentic-technical-report-reading-map.md`

你需要能讲清楚：

- RepoHarness 的核心目标是生产可执行、可审计、可导出的软件工程智能体训练轨迹。
- 它不是 Claude Code、Cursor、OpenHands、SWE-agent 或官方 SWE-Bench harness 的复刻。
- Docker execution mode 只能描述为 Docker-based executable repository environment，不能说成生产级安全沙箱。
- 当前 V4 已通过修复后最终验收；V5 正在实施，不应提前说成最终验收完成。

### 第 1 章：系统架构和对象流

目标：建立模块所有权和对象流，不急着读每一行代码。

必读文档：

- `docs/02-system-architecture.md`
- `docs/11-object-model-config-and-data-flow.md`

重点代码：

- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/workspace/schemas.py`
- `src/repo_harness/trajectory/schemas.py`

你需要能讲清楚：

- `RunConfig` 控制怎么运行。
- `TaskDefinition` 定义要解决什么任务。
- `RunnableTask` 是运行时任务投影。
- `RunWorkspace` 表示 agent 操作的工作区。
- `VerifierResult` 和 `RewardMetadata` 决定评测和训练信号。
- `TranscriptRecord`、`TrajectoryEvent` 和 `ArtifactRef` 让一次运行可审计。

### 第 2 章：单任务运行主链路

目标：把你已经读过的 `run-task` 架构放回完整代码主线。

主读材料：

- `docs/project_tut_for_me/session-notes/01-run-task-architecture.md`
- `docs/project_tut_for_me/01-v4-runtime-architecture.md`

重点代码：

- `src/repo_harness/cli/main.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/run_metadata/writer.py`
- `src/repo_harness/evaluation/metrics.py`
- `src/repo_harness/evaluation/outcome_policy.py`

学习路径：

1. 从 `repo-harness run-task` 在 CLI 中如何解析参数开始。
2. 进入 `run_task()`，按顺序看：加载配置、加载任务、创建 workspace adapter、baseline verifier、创建 agent workspace、构造初始消息、运行 agent loop、捕获 final patch、运行 final verifier、写 reward、metrics 和 run metadata。
3. 对照 run directory 里的文件，理解每个产物由哪一步生成。

你需要能讲清楚：

- baseline verifier 为什么在 agent run 前执行。
- final patch 为什么必须在 final verifier 前冻结。
- final verifier 为什么要用 strict patch replay。
- `run_outcome` 不是 agent 自己说成功，而是由 baseline、final verifier 和停止原因共同派生。

### 第 3 章：任务定义、任务适配和任务冻结

目标：理解“任务不是一句提示词”，而是源码、环境、验证器、可见性和证据边界的组合。

必读文档：

- `docs/06-task-dataset-and-environment-adapters.md`
- `docs/project_tut_for_me/02-task-construction-swe-and-pr.md`
- `docs/v4/scope-and-roadmap.md`
- `docs/v4/implementation-plan.md` 中 task freeze 相关章节

重点代码：

- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/tasks/adapter.py`
- `src/repo_harness/workspace/materialization.py`
- `src/repo_harness/v3_swebench_like.py`
- `src/repo_harness/v4_implementation_inputs.py`
- `src/repo_harness/v4_task_freeze.py`
- `src/repo_harness/v5_task_set.py`

你需要能讲清楚：

- `TaskAdapter.load()` 只做读取、校验、规范化和静态命令检查，不运行模型，也不运行 baseline。
- GitHub PR / issue 任务和 SWE-Bench-like 任务都必须固定源码、base commit、验证器计划和 evaluator-only evidence。
- `adapter_visible_task_input_manifest` 和 `evaluator_only_evidence_manifest` 的边界是什么。
- raw PR diff、gold patch、hidden test selector、official harness report 和 reward 字段为什么不能进入模型可见输入。

### 第 4 章：工作区、Docker 后端和命令执行

目标：看懂 RepoHarness 怎样真实执行命令，而不是只在内存里模拟。

必读文档：

- `docs/05-workspace-sandbox-and-permissions.md`
- `docs/project_tut_for_me/03-docker-environment-and-command-execution.md`

重点代码：

- `src/repo_harness/workspace/backend_factory.py`
- `src/repo_harness/workspace/adapter.py`
- `src/repo_harness/workspace/docker_adapter.py`
- `src/repo_harness/workspace/materialization.py`
- `src/repo_harness/tasks/command_policy.py`
- `src/repo_harness/permissions/system.py`

你需要能讲清楚：

- `source_checkout`、`setup_workspace`、`agent_workspace` 和 `verification_workspace` 分别解决什么问题。
- 依赖状态为什么可以用 `DependencyState` 描述，而不是把 baseline 的副作用直接带入 agent run。
- Docker 后端如何记录 `docker_backend_facts.json`、`container_execution_facts/` 和 phase coverage。
- 所有命令执行最终都应该通过 workspace adapter，而不是工具层自己绕过边界执行。
- permission 是是否允许工具调用的决策，Docker 是命令执行环境，这两个边界不能混为一谈。

### 第 5 章：上下文构造、模型调用和 provider 抽象

目标：理解哪些内容进入模型，真实 provider 请求如何被规范化和记录。

必读文档：

- `docs/03-agent-loop-and-message-protocol.md`
- `docs/10-context-session-and-failure-diagnostics.md`
- `docs/project_tut_for_me/04-provider-agent-loop-tools.md`

重点代码：

- `src/repo_harness/context/builder.py`
- `src/repo_harness/context/manager.py`
- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/model_client/schemas.py`
- `src/repo_harness/model_client/providers/common.py`
- `src/repo_harness/model_client/providers/deepseek.py`
- `src/repo_harness/model_client/providers/openai.py`
- `src/repo_harness/model_client/redaction.py`

你需要能讲清楚：

- `ContextBuilder.build_initial_messages()` 如何把任务可见视图、工具列表、预算和仓库上下文放进初始消息。
- `ContextManager.prepare_messages()` 为什么要生成 `PreparedMessages`、`model_input_hash` 和 context event。
- provider raw request / response 为什么只能作为脱敏 artifact 保存，不能进入训练样本。
- DeepSeek 作为主要真实 provider，OpenAI 在当前配置中主要作为受限 fallback 或 V5 中待明确的 provider gate 对象。

### 第 6 章：Agent Loop、工具协议和 scaffold

目标：真正看懂 agent 是怎样一轮一轮行动的。

必读文档：

- `docs/03-agent-loop-and-message-protocol.md`
- `docs/04-tool-system-and-orchestration.md`
- `docs/09-agent-scaffolds-and-multi-agent.md`

重点代码：

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/agent_loop/schemas.py`
- `src/repo_harness/tools/schemas.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/scaffolds/registry.py`
- `src/repo_harness/scaffolds/simple_react.py`
- `src/repo_harness/scaffolds/single_shot_patch.py`
- `src/repo_harness/scaffolds/planner_coder_verifier.py`

你需要能讲清楚：

- 每轮 loop 如何检查预算、准备上下文、调用模型、处理 tool call、执行工具和回填 tool result。
- 未知工具、schema 错误、权限拒绝、工具执行错误都必须转成结构化 `ToolResult` 回到消息轨迹。
- `bash` 为什么不是任意 shell，为什么识别到测试命令时可能被路由为 `run_tests`。
- scaffold 如何限制工具集合、阶段流转和停止条件。

### 第 7 章：Verifier、reward metadata 和 outcome policy

目标：理解为什么最终成败必须由 verifier 决定，而不是模型自报成功。

必读文档：

- `docs/07-verifier-reward-and-evaluation.md`
- `docs/project_tut_for_me/05-final-verifier-reward-export-acceptance.md`

重点代码：

- `src/repo_harness/verifier/runner.py`
- `src/repo_harness/verifier/acceptance.py`
- `src/repo_harness/verifier/pytest_parser.py`
- `src/repo_harness/reward/calculator.py`
- `src/repo_harness/evaluation/outcome_policy.py`
- `src/repo_harness/v3_agent_runtime.py`

你需要能讲清楚：

- baseline、feedback 和 final verifier 的职责不同。
- `fail_to_pass_tests` 和 `pass_to_pass_tests` 分别验证修复目标和回归保护。
- `VerifierResult.accepted` 来自 acceptance policy，不只是测试命令退出码。
- reward metadata 是训练候选信号和审计字段，不等于项目已经训练出一个模型。
- final verifier 是 accepted、rejected、inconclusive 和 regression 的权威来源。

### 第 8 章：Trajectory store 和训练导出

目标：理解 RepoHarness 如何把一次智能体运行变成训练数据候选。

必读文档：

- `docs/08-trajectory-store-and-training-export.md`
- `docs/v4/evidence/export-quality/` 下的 manifest 和 audit 报告

重点代码：

- `src/repo_harness/trajectory/recorder.py`
- `src/repo_harness/trajectory/inspect.py`
- `src/repo_harness/export/exporter.py`
- `src/repo_harness/export/audit.py`
- `src/repo_harness/export/pairing.py`
- `src/repo_harness/export/schemas.py`
- `src/repo_harness/v4_export_quality.py`
- `src/repo_harness/v5_export_pack.py`

你需要能讲清楚：

- `transcript.jsonl` 记录模型可见对话和工具观察。
- `events.jsonl` 记录模型调用、权限决策、工具执行、验证器、预算和运行结束事件。
- `artifacts.json` 绑定 artifact 的路径、哈希、大小和保留策略。
- SFT、reinforcement learning rollout、preference pair 和 failure dataset 的数据来源不同。
- trainable、diagnostic-only、blocked、mock / replay 和 stress records 不能混成一个统计分母。

### 第 9 章：V1 到 V4 的版本演进

目标：理解项目不是一次性写成，而是通过多个可验收阶段逐渐补齐能力。

推荐阅读：

- `docs/v1/README.md`
- `docs/v1/walkthrough.md`
- `docs/v1/final-acceptance.md`
- `docs/v2/scope-and-roadmap.md`
- `docs/v2/final-acceptance.md`
- `docs/v3/scope-and-roadmap.md`
- `docs/v3/walkthrough.md`
- `docs/v3/final-acceptance.md`
- `docs/v4/scope-and-roadmap.md`
- `docs/v4/final-acceptance.md`
- `docs/v4/walkthrough.md`

版本理解方式：

- V1：micro-repo 最小闭环，重点是跑通任务、工具、agent loop、verifier、reward 和导出。
- V2：扩展 provider、run metadata、多 rollout、scaffold 和导出审计。
- V3：引入真实 repository-level task、Docker backend、固定 SWE-Bench-like 小子集、context compaction、resume、export audit 和 acceptance bundle。
- V4：补强 task freeze、rollout orchestration、tool lifecycle audit、agent run integration、export quality、cards 和最终验收机器证据。

当前 V4 结论必须以这些路径为准：

```text
runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json
runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json
runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json
runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl
```

### 第 10 章：V5 当前范围和结果包设计

目标：理解 V5 为什么是“面试级结果包”，而不是随意增加功能。

必读文档：

- `docs/v5/scope-and-roadmap.md`
- `docs/v5/implementation-plan.md`
- `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md`
- `docs/v5/review/scope-review.md`
- `docs/v5/implementation-log/`
- `docs/v5/review/implementation/`

重点代码：

- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v5_task_set.py`
- `src/repo_harness/v5_provider_gate.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_export_pack.py`

你需要能讲清楚：

- V5 分为 `core_acceptance` 和 `resume_ready_acceptance`。
- `core_acceptance` 证明 V5 工程闭环、证据完整性、任务冻结、最小真实运行、训练导出和 acceptance bundle 成立。
- `resume_ready_acceptance` 额外要求多真实 provider、真实可比较 preference pair、share-safe demo bundle 和 canonical demo walkthrough。
- 如果 claim gate 阻断了某些声明，就不能在简历或文档里使用对应强表述，例如 `multi-provider agent runs` 或 `preference export completed`。
- 当前 V5 正在实施，学习时可以阅读 V5 文档和源码，但不应该把 V5 说成最终验收已完成。

## 4. 每章学习时的固定检查问题

每读完一章，都建议用下面这些问题自查：

1. 这一章解决了核心闭环里的哪一个箭头？
2. 这一章的输入对象、输出对象和关键 artifact 是什么？
3. 哪些内容模型可见，哪些内容只允许 evaluator、audit 或 export 使用？
4. 这一章的权威代码入口是哪一个函数或类？
5. 这一章有哪些不能夸大的边界？
6. 如果面试官追问“这个结论怎么证明”，应该指向哪个 path、sha256、command log 或 inspect 命令？

## 5. 建议后续整理目录

当前不强制移动文件。等 V5 开发节奏稳定后，可以把 `docs/project_tut_for_me/` 整理成下面的结构：

```text
docs/project_tut_for_me/
  README.md
  00-learning-plan.md
  tutorial/
    01-runtime-architecture.md
    02-task-construction.md
    03-docker-command-execution.md
    04-provider-agent-loop-tools.md
    05-final-verifier-reward-export-acceptance.md
  walkthroughs/
    01-run-task-realrepo-local-buggy-calculator.md
    02-task-freeze-evidence-reading.md
    03-final-verifier-and-export-evidence-reading.md
  qa/
    code-reading-qa.md
  backlog/
    next-questions.md
```

整理后的原则是：

- `tutorial/` 放正式主线讲义。
- `walkthroughs/` 放真实运行目录和证据产物纵向追踪。
- `qa/` 放局部概念问答。
- `backlog/` 放下一轮问题。

## 6. 如果需要我继续讲解，建议从哪里开始

下一轮最适合采用“源码优先”的顺序。架构只用几分钟校准，然后直接读代码。

第一轮建议按下面的文件顺序讲：

```text
src/repo_harness/tasks/schemas.py
src/repo_harness/tasks/adapter.py
src/repo_harness/v3_swebench_like.py
src/repo_harness/v4_implementation_inputs.py
src/repo_harness/v4_task_freeze.py
src/repo_harness/workspace/materialization.py
src/repo_harness/evaluation/runner.py
src/repo_harness/workspace/schemas.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/verifier/runner.py
src/repo_harness/model_client/factory.py
src/repo_harness/model_client/providers/deepseek.py
src/repo_harness/model_client/providers/openai.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/tools/minimal.py
src/repo_harness/trajectory/schemas.py
src/repo_harness/trajectory/recorder.py
```

这一轮的讲解目标不是逐行翻译代码，而是边读边建立对象流：哪个对象从哪里来，字段如何被 Pydantic 校验，真实输入如何被过滤成模型可见字段，什么时候写入 run directory，哪些字段能进入模型上下文，哪些字段只能进入验收和审计。

第一轮尤其要重点回答：

- `TaskDefinition` 和 `RunnableTask` 每个关键字段是什么意思，Pydantic 怎样校验它们。
- SWE-Bench-like 输入和 GitHub PR / issue 输入分别在哪里冻结，哪些字段属于 adapter-visible，哪些字段属于 evaluator-only。
- `run_task()` 如何把 task、config、workspace、provider、tool、verifier 和 recorder 串起来。
- Docker 后端如何把宿主机路径映射成容器路径，如何执行命令，如何保存 `container_execution_facts`。
- pytest verifier 如何解析 test command、如何分别运行 fail-to-pass 和 pass-to-pass 测试。
- DeepSeek / OpenAI provider 请求如何构造、脱敏、落盘，并变成 `ModelResponse`。
- agent loop 如何把 tool call、permission decision、tool result 和 transcript 绑定起来。

当前已经确认的讲解方式：

1. 优先深入代码实现，真实 provider、SWE-Bench-like 数据和 GitHub PR / issue 输入链路优先。
2. 讲到源码级别的函数调用、字段含义和运行产物，不只停留在架构图。
3. Python、Pydantic、pytest 和 Docker 都按 RepoHarness 代码里的实际用法讲清楚，遇到相关实现时补足底层知识。
