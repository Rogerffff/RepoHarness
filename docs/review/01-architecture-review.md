# Architecture Review

## 总体评价

RepoHarness 的设计文档整体方向清晰，已经形成了比较完整的训练友好型软件工程智能体运行框架。核心闭环 `task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export` 是成立的，文档也正确地区分了任务适配、工作区、工具、权限、智能体循环、验证器、轨迹存储和训练导出等模块。

整体架构最强的地方是边界意识比较好：文档多次强调第一版只做单机、本地或 Docker 执行、批量评测、轨迹记录和训练导出，不声称生产级安全沙箱、企业权限系统、远程多代理平台或完整强化学习算法。这种克制是正确的，也让项目更适合作为可以实现的设计，而不是过度膨胀的系统蓝图。

对 Claude Code 的参考方式总体准确且不过度。文档主要借鉴统一 agent loop、工具能力契约、权限判断、工具结果回流、子代理复用同一循环、transcript 和 diagnostics 等架构不变量，没有把 Claude Code 的用户界面、企业权限、MCP、复杂 hooks、远程执行和产品遥测照搬进 RepoHarness。这个取舍是合理的。

## 主要问题

### 1. 总体架构图过于线性，不能充分表达控制流和数据流

`02-system-architecture.md` 中的线性结构有助于快速理解，但容易造成误解。实际运行中，`Agent Loop` 会多次调用 `Tool System`，`Tool System` 会在每次调用前触发 `Permission System`，`bash` 和 `run_tests` 又会进入 `Workspace / Sandbox Adapter` 执行。`Verifier` 既可能作为最终验收阶段运行，也可能在多轮修复中以测试反馈形式进入 agent loop。`Trajectory Store` 也不是最后才运行，而是贯穿每个消息、工具调用、权限决策和验证结果。

建议把线性图改成“控制平面、执行平面、数据平面”的结构，否则后续实现者可能把这些模块写成一次性流水线，而不是可重入、可记录、可恢复的运行时系统。

### 2. Tool System、Permission System、Workspace / Sandbox Adapter 的边界还需要更精确

当前文档中，`Tool System` 负责工具执行，`Workspace / Sandbox Adapter` 也负责执行命令，`Permission System` 又出现在工具执行管线内部。这个方向是合理的，但职责边界还不够精确。

建议明确：

- `Tool System` 负责把模型请求转成标准工具调用，并进行输入校验、结果格式化、输出截断和事件记录。
- `Permission System` 只负责做允许、拒绝、询问、规则命中的决策，不直接执行命令或修改文件。
- `Workspace / Sandbox Adapter` 负责实际文件系统和进程执行边界，例如路径解析、工作区挂载、命令运行、超时、中断和 diff 捕获。
- 具体工具，例如 `bash`、`write_file`、`apply_patch`，应该调用 `Workspace / Sandbox Adapter`，而不是自己绕过执行边界。

### 3. Verifier 与 `run_tests` 工具的关系需要补强

文档已经强调训练奖励和离线评测必须共用同一套 verifier，这是非常正确的。但目前 `run_tests` 工具、`bash` 测试命令和最终 `Verifier / Reward` 的边界还不够清楚。

建议设计为：`run_tests` 调用 verifier 的轻量执行路径，最终评测调用 verifier 的最终验收路径，两者共享解析器、测试配置和结果 schema，但事件类型和使用场景不同。最终验收 verifier 应在 agent 停止后重新运行一次，避免模型上下文中的测试结果与最终工作区状态不一致。

### 4. 数据流已经有骨架，但缺少完整的端到端对象流转说明

每篇文档都提到了对象，例如 task、workspace、tool result、verifier result、events、metrics、export metadata，但还缺少一张完整的数据流表。

建议增加一个端到端数据流章节，按顺序说明 `TaskDefinition`、`RunnableTask`、`RunWorkspace`、`ToolCall`、`PermissionDecision`、`ToolResult`、`VerifierResult`、`TrajectoryStore` 和 `TrainingExporter` 的流转。

### 5. 任务准备流程和正式运行流程之间的状态切换还不够明确

`06-task-dataset-and-environment-adapters.md` 提到环境准备包括 dependency setup、baseline tests、确认测试命令可执行、记录初始失败测试和通过测试。这很重要，但文档没有说明这些准备结果如何进入正式运行。

建议补充 `BaselineResult`，并说明 baseline 失败、依赖安装失败、测试命令不可运行时，任务进入 `invalid` 或 `flaky` 状态，不产生训练轨迹。正式运行必须从干净 workspace 或已记录的 baseline workspace snapshot 开始，避免 setup 阶段副作用污染 agent 轨迹。

### 6. 权限模式命名需要进一步澄清

当前第一版权限模式包括 `plan`、`ask`、`auto`、`deny`。其中 `deny` 容易与单次权限决策的 `deny` 混淆。建议将其表达为非交互拒绝风险操作的模式，而不是所有操作都拒绝。

同时需要说明批量评测默认不应该使用需要人工确认的 `ask` 模式，否则 evaluation runner 会卡住。

### 7. Event schema 对非工具事件不够友好

`08-trajectory-store-and-training-export.md` 中每条事件至少包含 `tool_name`、`tool_input`、`tool_output_preview`、`exit_code` 等字段。但很多事件并不是工具事件，例如 run started、model call started、verifier completed、termination、export completed、context truncated。

建议把事件 schema 改成基础字段加按类型扩展：通用字段、工具事件字段、权限事件字段、verifier 事件字段、终止事件字段分开定义。

## 建议修改

1. 在 `02-system-architecture.md` 增加非线性架构图，表达 `Agent Loop`、`Tool System`、`Permission System`、`Workspace / Sandbox Adapter`、`Verifier` 和 `Trajectory Store` 的循环关系。
2. 增加模块所有权表，明确每个模块拥有的数据、禁止访问的数据、调用的下游模块和产出的事件类型。
3. 在 `03-agent-loop-and-message-protocol.md` 中补充 verifier 的触发策略：中间测试反馈、最终验收、停止条件、失败后继续修复之间的关系。
4. 在 `04-tool-system-and-orchestration.md` 和 `05-workspace-sandbox-and-permissions.md` 中统一命令执行边界，明确所有文件写入和命令执行最终都必须经过 workspace 或 sandbox adapter。
5. 在 `06-task-dataset-and-environment-adapters.md` 中补充 baseline 结果对象，以及 baseline 如何传递给 verifier 和正式运行。
6. 在 `08-trajectory-store-and-training-export.md` 中把 event schema 改成按事件类型扩展的结构，避免所有事件都被迫带工具字段。
7. 在 `07-verifier-reward-and-evaluation.md` 中补充 reward metadata 的输入字段来源，例如 cost、turn count、tool call count、patch size、test run count 和 timeout penalty 如何从 events 与 verifier result 计算。
8. 对 Claude Code 参考章节增加统一说明：RepoHarness 只借鉴架构模式和运行时不变量，不要求保留 TypeScript 文件名、产品模式名称或 Claude Code 的交互功能。

## 必须保留的优点

1. 必须保留“工具结果回流到下一轮模型上下文”这个不变量。这是 agent loop 能够利用环境反馈持续修复的核心。
2. 必须保留“训练奖励和离线评测共用同一套 verifier”的原则。这是 RepoHarness 区别于普通 coding agent demo 的关键价值。
3. 必须保留 permission 和 sandbox 的区分。文档当前没有夸大 Docker execution mode 的安全性，这一点非常重要。
4. 必须保留 transcript 和 events 分离的设计。transcript 面向对话重放，events 面向统计、诊断和训练导出，这个边界是正确的。
5. 必须保留第一版范围克制：单机、本地或 Docker、JSONL、批量评测、训练导出接口，而不是直接承诺远程多代理、企业权限、插件市场或大规模 rollout 集群。
6. 必须保留对 Claude Code 的“参考但不复刻”态度。当前文档借鉴的是统一循环、工具契约、权限管线、上下文治理和子代理复用 loop 等架构思想，没有过度复制产品功能。
7. 必须保留 scaffold 可替换的设计。single-shot patch、simple ReAct、planner-coder-verifier 在同一任务、同一工具、同一 verifier 下对比，是后续实验设计中非常有价值的结构。
