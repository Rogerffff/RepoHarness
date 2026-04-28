# System Architecture

## 总体架构

RepoHarness 的目标架构是分层的训练友好 Harness。下面的图不是一次性流水线，而是一个可重入的运行时闭环：

```text
Control Plane
  CLI / Eval Runner
    -> Task Adapter
    -> Agent Loop
    -> Scaffold

Execution Plane
  Agent Loop
    -> Tool System
    -> Permission System
    -> Workspace / Sandbox Adapter
    -> Verifier
    -> Agent Loop

Data Plane
  Trajectory Store observes:
    messages, tool calls, permission decisions, workspace events,
    verifier results, termination summaries, metrics
  Training Exporter reads:
    normalized task, transcript, events, final diff, verifier result,
    reward metadata, run metadata
```

每一层必须可独立测试和替换，避免把任务数据、工具执行、模型调用、评测逻辑和训练导出写成一个大脚本。

文档中的 sandbox 指执行边界设计，不等同于加固的生产级安全沙箱。Docker execution mode 只应被描述为 Docker-based executable repository environment。

## 核心模块职责

CLI 与配置层负责读取任务列表、模型配置、运行参数、权限模式和输出目录。它不直接执行工具，也不直接解析测试结果。

Task Adapter 负责把自建任务、issue-style fixture tasks、未来 SWE-Bench Lite 子集或未来 GitHub Issue / Pull Request 数据转换成统一任务对象。

Workspace / Sandbox Adapter 负责创建任务工作区、复制仓库、执行命令、保存 diff 和清理环境。

Agent Loop 负责维护消息、调用模型、解析工具调用、回填工具结果、控制终止条件。

Tool System 负责定义工具契约、输入校验、工具执行、输出截断和 tool result 格式化。

Permission System 负责判断一次工具调用是否允许执行，和 workspace/sandbox 边界分层。

Verifier / Reward 负责运行测试、解析结果、生成评测指标和 reward metadata。

Trajectory Store 负责保存 transcript、events、final patch、verifier result、metrics 和 summary。

Training Exporter 负责把轨迹转换为 SFT、reinforcement learning rollout 或 preference pair 数据。

## 模块所有权表

| 模块 | 拥有的数据 | 不应该直接负责 | 可以调用的下游 | 必须记录的事件 |
| --- | --- | --- | --- | --- |
| CLI / Eval Runner | `RunConfig`、任务列表、输出目录、预算 | 具体工具执行、测试解析 | Task Adapter、Agent Loop、Trajectory Store | run started、run finished、export requested |
| Task Adapter | `TaskDefinition`、`RunnableTask`、verifier 配置 | 模型调用、reward 公式 | Workspace Adapter、Verifier baseline path | task loaded、task invalid、baseline completed |
| Workspace / Sandbox Adapter | `RunWorkspace`、路径边界、命令执行、diff 捕获 | 权限策略、模型消息 | Permission System 的决策结果、底层执行环境 | workspace created、command executed、diff captured |
| Agent Loop | `AgentLoopState`、messages、终止原因 | 文件系统边界、测试解析 | Model Client、Tool System、Verifier feedback path | model call、assistant message、termination |
| Tool System | `Tool` definition、`ToolCall`、`ToolResult` | 直接绕过 workspace 写文件或执行命令 | Permission System、Workspace Adapter、Verifier feedback path | tool requested、tool completed、tool failed |
| Permission System | `PermissionDecision`、规则命中原因 | 执行命令、修改文件 | 无，或者读取只读策略配置 | permission allowed、permission denied、permission requires ask |
| Verifier / Reward | `VerifierResult`、`RewardMetadata`、metrics | 任意工具编排、模型重试策略 | Workspace Adapter 的命令执行能力 | verifier started、verifier completed、reward computed |
| Trajectory Store | transcript、events、artifacts index | 推断业务决策、修改 workspace | 文件系统写入 run directory | artifact written、event appended |
| Training Exporter | `ExportRecord`、export metadata | 重新评测任务、改写原始轨迹 | Trajectory Store、Verifier result | export started、export completed、record skipped |

所有文件写入、patch 应用和进程执行最终必须经过 Workspace / Sandbox Adapter。Tool System 可以决定“调用哪个工具”和“如何格式化结果”，但不应该自己实现另一套路径边界、命令超时或 diff 捕获逻辑。

## 端到端对象流

完整数据流在 `11-object-model-config-and-data-flow.md` 中集中定义。系统架构层面应保持以下顺序：

1. `TaskDefinition` 从 YAML 或 JSON 进入 Task Adapter。
2. Task Adapter 输出 `RunnableTask`、`VerifierConfig` 和可选的 `BaselineResult`。
3. Workspace Adapter 创建 `RunWorkspace`，保存 baseline 状态或干净起点。
4. Agent Loop 根据 `RunnableTask`、`RunConfig` 和 scaffold 构造初始 messages。
5. 模型输出 `ToolCall` 或 final answer。
6. Tool System 校验 `ToolCall`，请求 `PermissionDecision`。
7. Workspace Adapter 在允许的执行边界内完成文件或命令操作。
8. `ToolResult` 回流到 messages，并写入 transcript 和 events。
9. `run_tests` 可以触发 verifier 的中间反馈路径；agent 停止后必须触发最终验收路径。
10. `VerifierResult` 和 `RewardMetadata` 进入 trajectory、metrics 和 export metadata。
11. Trajectory Store 保存 patch、diff、events、summary 和 verifier 输出。
12. Training Exporter 从完整 run artifacts 生成 SFT、reinforcement learning rollout 或 preference pair 数据。

## 关键不变量

- 工具结果必须作为 tool result 回流到下一轮模型上下文。
- 所有写操作必须限制在任务工作区内。
- 训练奖励和离线评测必须共用同一套 verifier。
- 轨迹记录不能依赖终端界面或人工观察。
- 只读工具可以并发，写工具和测试命令默认串行。
- 未声明并发安全的工具默认不并发。
- verifier 输出必须既能被人读懂，也能被训练导出模块消费。
- 任何 sandbox 表述都必须保守，不声称生产级安全隔离。

## 与 Claude Code 的关系

RepoHarness 借鉴 Claude Code 的架构分层，而不是复制产品代码。重要参考点包括：

- `query()` 风格的统一 agent loop。
- `QueryEngine` 与 turn 执行循环分离。
- `Tool` 是能力契约，不是函数列表。
- 工具执行经过 schema 校验、权限判断、执行、结果回流。
- permission 与 sandbox 是不同边界。
- 子代理复用同一套 query loop。
- transcript、events 和 diagnostics 是长期任务的基础设施。

对应参考资料在 `reference/claude-code-docs/` 和本地忽略的 `reference/claude-code-typescript-src/` 中。

RepoHarness 只借鉴架构模式和运行时不变量，不要求保留 TypeScript 文件名、产品模式名称或 Claude Code 的交互功能。参考源码是设计资料，不是未来 Python 实现的复制目标。

## 第一版边界

第一版设计面向单机、本地或 Docker 执行、JSONL 轨迹、批量评测和训练导出。远程执行、插件化扩展、复杂多代理、企业权限和大规模异步 rollout 只预留接口，不作为第一版实现目标。
