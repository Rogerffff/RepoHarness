# V4 深度学习计划

## 学习目标

这轮学习不再解决“RepoHarness 是什么”这种基础问题，而是解决下面这些更接近实现和面试追问的问题：

- 一个 SWE-Bench-like 任务怎样从 dataset instance 变成 RepoHarness 的 `TaskDefinition`？
- 一个真实 GitHub PR / issue 任务怎样冻结源码、issue、base commit、验证器和证据边界？
- `repo-harness run-task` 启动后，`run_task` 每一步实际创建了哪些对象和目录？
- Docker backend 怎样把宿主机上的 run directory 映射进容器，并且让模型工具只在 agent workspace 内操作？
- agent 调用 `bash` 时，为什么它不是任意 shell？命令怎样被权限系统过滤、怎样被 Docker 执行、输出怎样写入 artifact？
- `pytest` 是在哪里执行的？中间反馈 verifier 和最终 formal verifier 有什么区别？
- 真实 provider 请求怎样被构造、脱敏、落盘、归一化成 `ModelResponse`？
- final patch 怎样从 agent workspace 捕获，并在干净 verification workspace 中重放？
- reward、trajectory export、preference pair 和 V4 acceptance 是怎样基于 evidence 绑定的？

## 学习方式

建议按照“先跑通 mental execution，再钻模块”的顺序学习。

第一遍不要逐行读所有源码，而是拿一条真实链路作为主线：

```text
冻结任务 -> 加载 run config 和 task -> materialize source
-> 创建 Docker workspace -> baseline verifier
-> 构造模型上下文 -> provider 调用
-> 工具调用和权限检查 -> agent 修改文件
-> 捕获 final patch -> clean final verifier
-> reward / metrics / metadata -> export / audit / acceptance
```

第二遍再把每个阶段拆到具体模块：

```text
任务构造：v4_implementation_inputs.py / v4_task_freeze.py / v3_swebench_like.py
运行编排：evaluation/runner.py
工作区：workspace/materialization.py / workspace/docker_adapter.py
模型：model_client/factory.py / model_client/providers/*.py
上下文：context/builder.py / context/manager.py
工具：tools/minimal.py / permissions/system.py
验证：verifier/runner.py / verifier/acceptance.py / v3_agent_runtime.py
导出：training_export.py / export/exporter.py / export/audit.py / export/pairing.py
验收：v4_agent_run.py / v4_export_quality.py / v4_acceptance.py
```

## 阶段一：先掌握 V4 当前架构，不回顾旧版本

目标：用当前 V4 的语言描述系统，而不是历史版本语言。

你需要能说清楚：

- V4 的任务来源包括 GitHub PR / issue 构造任务，以及 public SWE-Bench-like diagnostic pool。
- 正式运行已经可以使用真实 provider，例如 DeepSeek OpenAI-compatible chat completions。
- 正式运行已经可以使用 Docker-based executable repository environment。
- V4 不只是 run-task，还包括 task freeze、rollout orchestration、tool lifecycle audit、agent run integration、export quality audit、cards 和 acceptance。
- 历史 V4 acceptance 产物存在，但当前学习和引用 V4 状态时，应以修复后重新生成的 `runs/v4-final-rerun-20260504T194758Z/` acceptance evidence 和文档同步后的 acceptance bundle 为准。

对应文档：`01-v4-runtime-architecture.md`

## 阶段二：看懂任务怎样变成可执行仓库

目标：你要能解释“任务不是一段 prompt，而是一个带源码、环境、验证器和可见性边界的 frozen object”。

重点文件：

- `src/repo_harness/tasks/schemas.py`
- `src/repo_harness/tasks/adapter.py`
- `src/repo_harness/workspace/materialization.py`
- `src/repo_harness/v3_swebench_like.py`
- `src/repo_harness/v4_implementation_inputs.py`
- `src/repo_harness/v4_task_freeze.py`

需要掌握：

- `TaskDefinition` 是磁盘上的任务定义 schema。
- `RunnableTask` 是运行时使用的规范化对象。
- `repo_source_spec` 可以是 fixture、本地仓库、本地 archive、public snapshot archive。
- V4 PR / issue 任务要求 issue / PR provenance、base commit、source archive、baseline verifier、post-patch verifier、flaky probe、license 和 use boundary evidence。
- SWE-Bench-like 任务会把隐藏 test patch、fail-to-pass selector、pass-to-pass selector 放在 evaluator-only 侧，不进入模型上下文。

对应文档：`02-task-construction-swe-and-pr.md`

## 阶段三：看懂 Docker 环境和命令执行

目标：回答“这个 harness 到底怎样跑 bash 命令、pytest 和 git diff”。

重点文件：

- `src/repo_harness/workspace/backend_factory.py`
- `src/repo_harness/workspace/protocol.py`
- `src/repo_harness/workspace/docker_adapter.py`
- `src/repo_harness/workspace/schemas.py`
- `src/repo_harness/tasks/command_policy.py`
- `src/repo_harness/permissions/system.py`

需要掌握：

- `create_workspace_adapter` 根据 `runtime.execution_mode` 创建 local process 或 Docker adapter，不做静默 fallback。
- Docker backend 会生成或复用镜像，记录 `docker_backend_facts.json`。
- run directory 被只读挂载到容器的 `/repo-harness-run`。
- workspace 子目录被读写挂载，容器中的工作目录对应宿主机 `runs/.../workspaces/...`。
- 每条容器命令都会写 `container_execution_facts/<command_id>.json`，并追加 trajectory event。
- `bash` 工具不是任意 shell；权限系统会拦截管道、重定向、命令拼接、网络命令、删除命令和敏感路径访问。

对应文档：`03-docker-environment-and-command-execution.md`

## 阶段四：看懂 provider、agent loop 和工具生命周期

目标：回答“真实模型是怎样被调用的，模型返回的 tool call 怎样变成一次文件读写或命令执行”。

重点文件：

- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/model_client/providers/common.py`
- `src/repo_harness/model_client/providers/deepseek.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/permissions/system.py`

需要掌握：

- `ContextBuilder` 会给模型 system message、任务可见投影、仓库上下文预览、工具列表、预算和执行模式。
- `AgentLoop` 每一轮会进行 context compaction、模型调用、tool call 校验、权限判断、工具执行、工具结果回流。
- DeepSeek provider 走 OpenAI-compatible chat completions；请求和响应会以脱敏 raw provider artifact 保存。
- ToolExecutor 中 `bash` 可被识别为 test command 并路由成 `run_tests`。
- `run_tests` 不执行任意命令，而是调用 `PytestVerifier.run_feedback` 或 `run_feedback_public`。

对应文档：`04-provider-agent-loop-tools.md`

## 阶段五：看懂 final verifier、reward、export 和 acceptance

目标：回答“为什么这个轨迹可以作为训练或评测样本，而不是只有一段模型对话”。

重点文件：

- `src/repo_harness/workspace/docker_adapter.py`
- `src/repo_harness/verifier/runner.py`
- `src/repo_harness/verifier/acceptance.py`
- `src/repo_harness/v3_agent_runtime.py`
- `src/repo_harness/reward/calculator.py`
- `src/repo_harness/run_metadata/writer.py`
- `src/repo_harness/export/exporter.py`
- `src/repo_harness/export/audit.py`
- `src/repo_harness/export/pairing.py`
- `src/repo_harness/v4_export_quality.py`
- `src/repo_harness/v4_acceptance.py`

需要掌握：

- final patch 从 agent workspace 相对 agent start snapshot 捕获。
- formal final verifier 在干净 verification workspace 中重放 final patch。
- SWE-Bench-like final verifier 会使用 evaluator-only verifier workspace、verifier patch reference 和 selector plan；在 agent loop final 阶段，代码路径主要是复制冻结的 baseline verifier workspace、应用模型 final patch，然后运行 fail-to-pass / pass-to-pass 命令。
- `VerifierResult.accepted` 来自 acceptance policy，而不是简单看命令退出码。
- reward、metrics、run metadata 都绑定 final verifier、patch stats、trajectory event 和 run config facts。
- export quality audit 会检查污染风险、测试过拟合风险、patch quality、reward allowlist、preference pair 可训练性。
- V4 acceptance 现在要求独立 regression evidence，不能把 task freeze 或 task validity evidence 复用成 regression evidence。

对应文档：`05-final-verifier-reward-export-acceptance.md`

## 面试表达建议

当对方问“你这个项目用了什么技术栈”时，不建议只回答 Python、Docker、Pytest、Pydantic。更准确的回答方式是：

```text
项目主体是 Python 3.11+，用 Pydantic 定义强 schema，PyYAML 读取任务和运行配置。
执行层抽象为 WorkspaceAdapter，目前支持 local process 和 Docker backend；
Docker backend 用 Docker CLI 创建容器，挂载 run directory 和 workspace，记录 container execution facts。
模型层使用 provider abstraction，DeepSeek 通过 OpenAI-compatible chat completions 接入，OpenAI provider 作为受限 fallback；
每次 raw request / response 都写成脱敏 artifact。
工具层是 schema 化 tool contract，模型 tool call 经过输入校验、权限策略、workspace boundary 检查，再由 adapter 执行。
验证层以 Pytest 为当前 parser 和 verifier 主路径，并对 SWE-Bench-like 任务维护 hidden final verifier plan。
训练数据层把 transcript、events、artifacts、final verifier、reward metadata 和 export audit 绑定起来，保证轨迹可审计。
```

这个回答比“用了 Docker 跑任务、接了真实模型”更经得住追问。
