# 工具、权限与 Plan Mode

## 这篇解决什么问题

Claude Code 的模型之所以“能做事”，不是因为它直接操作文件系统，而是因为它通过 `Tool` 抽象调用外部能力。

这篇要讲清 5 件事：

1. `Tool` 在 Claude Code 中到底是什么
2. 工具列表是如何被注册、过滤、合并并暴露给模型的
3. `tool_use` 是怎样真正被执行的
4. 权限判定到底按什么顺序发生
5. plan mode 为什么本质上是权限模式，而不是独立 planner

## 核心类型与职责

本篇重点类型如下：

| 类型 | 作用 |
| --- | --- |
| `Tool` | 一个模型可调用能力的统一接口 |
| `ToolUseContext` | 工具运行时拿到的上下文对象 |
| `ToolPermissionContext` | 权限模式、allow/deny/ask 规则与工作目录限制 |
| `PermissionResult` | 单个工具实现返回的权限结论 |
| `Command` | 与 tool 不同，command 是用户入口，不是模型入口 |

最重要的文件职责如下：

| 文件 | 角色 |
| --- | --- |
| `src/Tool.ts` | 定义 `Tool` 接口与 `buildTool()` |
| `src/tools.ts` | 内建工具注册与工具池组装 |
| `src/services/tools/toolExecution.ts` | 单个 tool_use 的执行逻辑 |
| `src/services/tools/toolOrchestration.ts` | 批量 tool_use 的编排 |
| `src/services/tools/StreamingToolExecutor.ts` | 流式工具执行 |
| `src/utils/permissions/permissions.ts` | 核心权限判定顺序 |
| `src/utils/permissions/permissionSetup.ts` | 会话启动时的权限上下文构造 |
| `src/tools/EnterPlanModeTool/*` / `ExitPlanModeTool/*` | plan mode 进出逻辑 |

## 关键源码

- `src/Tool.ts`
- `src/tools.ts`
- `src/services/tools/toolExecution.ts`
- `src/services/tools/toolOrchestration.ts`
- `src/services/tools/StreamingToolExecutor.ts`
- `src/utils/permissions/permissions.ts`
- `src/utils/permissions/permissionSetup.ts`
- `src/utils/sandbox/sandbox-adapter.ts`
- `src/tools/EnterPlanModeTool/EnterPlanModeTool.ts`
- `src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts`

## `Tool` 不是函数清单，而是能力契约

`src/Tool.ts` 里的 `Tool` 接口很宽，但它表达得非常清楚：

一个工具不是只有 `call()`。

它至少同时承担这些职责：

- 向模型描述自己：`prompt()`
- 定义输入输出模式：`inputSchema`, `outputSchema`
- 声明自己的安全属性：`isReadOnly()`, `isConcurrencySafe()`, `isDestructive()`
- 决定工具特定的权限逻辑：`checkPermissions()`
- 决定如何把结果映射回 `tool_result`
- 决定如何在 UI/SDK/transcript 中被观察

也就是说，Claude Code 里的工具既是：

- 模型可见对象
- 执行时对象
- 安全决策对象
- 观察层对象

## `buildTool()` 的默认值为什么重要

`buildTool()` 的设计体现了 Claude Code 很强的 fail-closed 倾向。

它提供的默认值是：

- `isEnabled -> true`
- `isConcurrencySafe -> false`
- `isReadOnly -> false`
- `isDestructive -> false`
- `checkPermissions -> allow`

其中最关键的是：

- 默认不并发
- 默认不视为只读

这意味着一个工具如果没有明确声明自己“安全可并发”或“只读”，系统会按更保守的方式处理它。

这对 agentic 执行非常重要，因为：

- 并发错误会导致上下文污染
- 错误地把写操作当作只读会导致安全漏洞

## 工具是怎样注册并暴露给模型的

### 第 1 层：`getAllBaseTools()`

`src/tools.ts` 里的 `getAllBaseTools()` 是内建工具全集的 source of truth。

这里会把这些能力放进同一个列表：

- `BashTool`
- `FileReadTool`
- `FileEditTool`
- `AgentTool`
- `SkillTool`
- `TodoWriteTool`
- `AskUserQuestionTool`
- 各种 task / plan / MCP 相关工具

### 第 2 层：`getTools(permissionContext)`

然后 `getTools()` 会根据当前权限模式裁剪这份列表。

它会处理几件事：

- simple mode 只保留极少数工具
- deny rules 会在模型看到工具之前就把某些工具剔除
- REPL mode 可能隐藏某些 primitive tools
- `isEnabled()` 会在当前运行时再次判定

注意，这一步非常关键：某些工具不是“模型调用时被拒绝”，而是“模型从一开始就看不到”。

### 第 3 层：`assembleToolPool(permissionContext, mcpTools)`

再下一层，内建工具与 MCP tools 会被合并成完整工具池。

这里有两个核心设计：

1. built-in 和 MCP tool 分区排序
2. built-in 在同名冲突时优先

排序的理由不是美观，而是 prompt cache 稳定性。源码明确说明了，要让 built-ins 保持连续前缀，避免 MCP 工具插入中间导致缓存前缀失稳。

## 模型如何看到工具

Claude Code 并不是把一个“工具名列表”给模型，而是把完整的 tool schema 给模型。

其中最重要的模型侧描述来自：

- `tool.name`
- `tool.prompt()`
- `tool.inputSchema`

要特别注意：

`Tool.prompt()` 不是 UI 文案，而是模型真正理解这个工具用途的说明文字。

因此一个工具的 prompt 质量，直接决定模型是否会：

- 选对这个工具
- 用对这个工具
- 给出合理参数

## 控制流分步讲解

从模型视角看，工具主链可以压成下面几步：

1. `getAllBaseTools()` 注册内建工具全集。
2. `getTools(permissionContext)` 根据 mode 与 deny rules 做第一轮过滤。
3. `assembleToolPool()` 合并 MCP tools，得到真正暴露给模型的工具池。
4. 模型读取 tool schema，并发出 `tool_use`。
5. `toolExecution.ts` 负责校验、hooks、权限判定与真正执行。
6. 结果映射成 `tool_result`，再进入下一轮消息。
7. 若当前在 plan mode，同一条链继续成立，只是权限语义不同。

## 单个 `tool_use` 是怎样执行的

真正执行一个 tool_use 的核心在 `src/services/tools/toolExecution.ts`。

可以把它理解成这条流水线：

1. 根据名字找到 tool definition
2. 校验 schema
3. 运行 pre-tool hooks
4. 调用统一权限入口 `canUseTool`
5. 真正执行 tool
6. 将结果映射成 `tool_result`
7. 运行 post-tool hooks
8. 把结果封装成下一轮消息

这个执行器还负责很多“模型系统常见但容易被忽略”的问题：

- telemetry
- abort / interrupt
- tool error 分类
- MCP tool 特殊处理
- tool result 持久化与超大输出落盘

所以 `toolExecution.ts` 更像是“工具调用 runtime”，而不是薄薄一层 adapter。

## 为什么有两套工具执行器

Claude Code 同时保留了：

- `StreamingToolExecutor`
- `runTools()` + `toolOrchestration.ts`

原因不是重复实现，而是两个场景的目标不同。

### `StreamingToolExecutor`

适合“assistant 正在流式输出时，tool_use 已经出现”的场景。

它的目标是：

- 尽早启动工具
- 并发执行并发安全工具
- 保证结果按原始顺序吐回
- 在 streaming fallback 时丢弃失效结果

### `runTools()`

适合“已经拿到完整 tool_use 列表，再统一执行”的场景。

它会先按 `isConcurrencySafe()` 分批：

- 连续的 concurrency-safe 调用可以并发
- 非 concurrency-safe 的调用强制串行

然后在并发完成后，再按原顺序回放 context modifiers。

这说明 Claude Code 对工具并发的设计原则是：

能并发，但只能在工具自己明确声明安全时并发。

## 权限判定的核心顺序

`src/utils/permissions/permissions.ts` 中的 `hasPermissionsToUseToolInner()` 是整套权限系统最值得读的函数之一。

它的顺序可以概括为：

1. 整个工具是否被 deny
2. 整个工具是否被 ask
3. 让工具自身执行 `checkPermissions()`
4. 工具自身是否明确 deny
5. 是否属于必须人工交互的 ask
6. 内容级 ask 规则是否命中
7. safety check 是否命中
8. 当前 mode 是否允许直接 bypass
9. 整个工具是否 always allow
10. 若仍是 `passthrough`，最后转成 `ask`

这个顺序反映了一个很重要的思想：

Claude Code 不把权限系统完全外包给工具，也不把权限系统完全写死在框架里，而是让两者叠加。

### 框架层负责什么

- 统一的 allow / deny / ask 规则
- mode 语义
- bypass 与 auto 的总体策略
- safety check 的兜底

### 工具层负责什么

- 工具特定的内容级权限逻辑
- 工具特定的规则解释
- 是否需要交互

## sandbox 与 permission 不是一回事

这点非常容易混淆。

### permission

permission 回答的问题是：

“这次 tool_use 在逻辑上是否被允许执行？”

### sandbox

sandbox 回答的问题是：

“即使允许执行，它应该在什么隔离条件下执行？”

比如 Bash/PowerShell：

- permission 可能允许它运行
- 但 sandbox 仍然会限制文件系统和网络

所以更准确地说：

permission 决定能不能做
sandbox 决定能在什么边界里做

## Plan Mode 的本质

很多人看到 `EnterPlanModeTool` / `ExitPlanModeTool` 会以为 Claude Code 有一个完全独立的 planner runtime。

源码显示并不是这样。

plan mode 的本质更接近：

- 一种特殊的 permission mode
- 加上一个 plan 文件抽象

进入 plan mode 时，系统会：

- 记录 `prePlanMode`
- 切换 `toolPermissionContext.mode`
- 某些场景下保留 auto 语义
- 对危险规则做裁剪

退出 plan mode 时，再恢复先前模式。

也就是说，plan mode 并不是另一套 query loop，而是：

“同一套 query/tool loop，在更保守的权限语义下运行”

## 工具过滤其实有很多层

如果只盯着 `getTools()`，会误以为工具可见性只在注册时决定。

实际上至少有这些层：

1. `getAllBaseTools()` 注册内建工具
2. `getTools()` 根据 mode 和 deny rule 做第一次过滤
3. `assembleToolPool()` 合并 MCP tools
4. coordinator / agent filter 再做一轮裁剪
5. slash command 的 `allowedTools` 可对单次执行进一步收缩
6. 运行时 `canUseTool` 再做最终判定

所以一个工具“存在于源码中”并不意味着：

- 模型一定能看到它
- 当前 agent 一定能用它
- 当前这一轮 command 一定能用它

## 关键设计权衡

### 1. 工具抽象做得很厚

代价是接口复杂。

收益是：

- 模型描述
- 执行行为
- 权限策略
- 观察层表现

都能在同一个抽象里对齐。

### 2. 默认保守，声明放开

并发、只读、危险性都默认按保守值处理，这很适合 agentic system。

### 3. plan mode 不另起炉灶

如果 plan mode 也有一套独立执行器，系统复杂度会飙升。Claude Code 选择复用 query/tool loop，只改变权限语义。

### 4. 先过滤再暴露

很多 deny 发生在模型看到工具之前，这比“让模型先看到再频繁被拒绝”更稳定，也更省 token。

## 易错点与误解

### 误解 1：tool schema 只是技术细节

不是。tool schema 就是模型如何理解执行面的语言。

### 误解 2：工具权限只看全局设置

不对。它是全局规则、mode、工具特定逻辑、内容级规则和 safety check 的叠加。

### 误解 3：plan mode 会自动禁止所有写操作

并不准确。plan mode 主要改变权限语义，不是简单删除编辑工具。

### 误解 4：MCP tool 和 built-in tool 只是来源不同

也不完全对。它们在合并、命名、过滤、resource 支持和 policy 上都有额外差异。

## 快照缺口说明

本篇主链相关文件在当前快照中都可读，没有阻断级缺口。

但要注意：

- 某些工具是否启用受 feature flags 与环境变量影响
- 某些 MCP 相关工具行为依赖运行时 server 能力，静态阅读只能看到宿主侧逻辑

## 继续阅读建议

下一篇看 [04-agenttool-tasks-and-remote-execution.md](./04-agenttool-tasks-and-remote-execution.md)。因为当你理解了工具与权限之后，就能更容易看懂 Claude Code 为什么把多 agent 设计成：

- `AgentTool` 负责编排
- `runAgent()` 负责真正执行
- `Task` 系统负责托管长期运行状态
