# 第 4 篇：工具系统架构

> Claude Code 源码深度教学系列 — 核心重点篇

## 目录

1. [概述：工具系统在 Claude Code 中的角色](#1-概述工具系统在-claude-code-中的角色)
2. [Tool 泛型接口设计](#2-tool-泛型接口设计)
3. [ToolDef + buildTool() 工厂模式](#3-tooldef--buildtool-工厂模式)
4. [工具注册与发现完整流程](#4-工具注册与发现完整流程)
5. [核心工具逐个详解](#5-核心工具逐个详解)
6. [工具执行管线](#6-工具执行管线)
7. [ToolUseContext 详解](#7-toolusecontext-详解)
8. [设计模式总结](#8-设计模式总结)

---

## 1. 概述：工具系统在 Claude Code 中的角色

Claude Code 的核心能力来自一套精心设计的**工具系统 (Tool System)**。当 Claude 模型决定执行操作时——无论是读取文件、运行 shell 命令、搜索代码还是调用外部 API——都通过工具系统完成。这套系统是整个 CLI 应用的"手和脚"，它桥接了 AI 模型的思考与真实世界的操作。

从架构视角看，工具系统承担了以下核心职责：

- **统一抽象**：所有操作（Bash 执行、文件读写、网络请求、MCP 协议调用等）都实现同一个 `Tool` 接口，模型无需关心底层差异
- **权限控制**：每次工具调用都经过多层权限检查（validateInput → checkPermissions → canUseTool → hooks），确保安全
- **并发编排**：只读工具可并行执行，写入工具串行执行，通过 `isConcurrencySafe` / `isReadOnly` 语义声明来自动调度
- **延迟加载**：通过 `shouldDefer` / `alwaysLoad` 机制，将不常用工具的 schema 从初始 prompt 中移除，降低 token 消耗
- **流式执行**：通过 `StreamingToolExecutor` 在模型输出 tool_use block 时即时开始执行，而非等待所有工具调用完成
- **渲染分离**：工具的执行逻辑与 UI 渲染完全解耦，每个工具自定义其在终端中的显示方式

工具系统的主要源码分布：

| 文件/目录 | 职责 |
|-----------|------|
| `src/Tool.ts` | Tool 接口定义、ToolDef 类型、buildTool() 工厂函数 |
| `src/tools.ts` | 工具注册表、getTools()、assembleToolPool() |
| `src/tools/*/` | 各具体工具实现（每个工具一个目录） |
| `src/services/tools/toolOrchestration.ts` | 批次划分与并发调度 |
| `src/services/tools/StreamingToolExecutor.ts` | 流式工具执行器 |
| `src/services/tools/toolExecution.ts` | 单个工具的权限检查 + 执行流程 |
| `src/services/tools/toolHooks.ts` | Pre/Post tool use hooks |

---

## 2. Tool 泛型接口设计

### 2.1 核心类型签名

`Tool` 接口是整个工具系统的基石，定义在 `src/Tool.ts` 中。它是一个泛型接口，包含三个类型参数：

```typescript
// src/Tool.ts
export type Tool<
  Input extends AnyObject = AnyObject,    // 输入 schema（Zod 类型）
  Output = unknown,                        // 输出数据类型
  P extends ToolProgressData = ToolProgressData, // 进度事件类型
> = {
  // ... 所有方法和属性
}
```

- **`Input`**：基于 Zod 的输入验证 schema，必须是 object 类型。模型传入的 JSON 参数会先经过这个 schema 验证
- **`Output`**：工具执行后返回的数据类型，用于类型安全地在渲染层消费
- **`P`**：进度事件的类型，用于长时间运行的工具（如 Bash 命令）向 UI 报告进度

`Tools` 是工具数组的别名，在整个代码库中统一使用：

```typescript
// 使用 readonly 数组，确保工具列表在传递过程中不会被意外修改
export type Tools = readonly Tool[]
```

### 2.2 call() — 工具执行入口

`call()` 是每个工具最核心的方法，负责实际执行操作：

```typescript
call(
  args: z.infer<Input>,           // 经过 Zod 验证的输入参数
  context: ToolUseContext,         // 执行上下文（包含 abort、状态、选项等）
  canUseTool: CanUseToolFn,        // 权限检查回调（子工具调用时使用）
  parentMessage: AssistantMessage, // 触发此工具调用的助手消息
  onProgress?: ToolCallProgress<P>, // 可选的进度回调函数
): Promise<ToolResult<Output>>
```

**关键设计点**：

1. **AbortController 支持**：`context.abortController` 让工具可以响应用户取消操作。例如 BashTool 会将 abort signal 传递给子进程
2. **进度回调**：长时间运行的工具通过 `onProgress` 向 UI 推送进度事件。进度事件经 `Stream` 封装后与最终结果合并到同一个 async iterable 中
3. **ToolResult 返回值**：不仅包含数据，还可以携带 `newMessages`（注入到对话中的额外消息）和 `contextModifier`（修改后续工具的执行上下文）

```typescript
// ToolResult 类型——工具执行的返回值
export type ToolResult<T> = {
  data: T                          // 工具输出数据
  newMessages?: (                  // 可选：注入到对话历史的额外消息
    | UserMessage
    | AssistantMessage
    | AttachmentMessage
    | SystemMessage
  )[]
  // contextModifier 仅对非并发安全的工具生效
  contextModifier?: (context: ToolUseContext) => ToolUseContext
  /** MCP 协议元数据，透传给 SDK 消费者 */
  mcpMeta?: {
    _meta?: Record<string, unknown>
    structuredContent?: Record<string, unknown>
  }
}
```

`contextModifier` 的设计非常精妙：工具可以在执行后修改上下文，影响后续工具的行为。但为了避免并发竞态问题，**只有非并发安全（串行执行）的工具的 contextModifier 才会被应用**。

### 2.3 inputSchema 与 outputSchema

每个工具通过 Zod schema 定义其输入和输出格式：

```typescript
readonly inputSchema: Input          // Zod schema，用于验证模型传入的参数
readonly inputJSONSchema?: ToolInputJSONSchema  // 可选：MCP 工具的原始 JSON Schema
outputSchema?: z.ZodType<unknown>    // 可选：输出的 Zod schema
```

**inputSchema** 有两个用途：

1. **API 层**：转换为 JSON Schema 发送给模型，让模型知道工具接受什么参数
2. **运行时**：在工具执行前验证输入，确保类型安全

大多数工具使用 `lazySchema()` 延迟初始化 schema，避免模块加载时的循环依赖：

```typescript
// src/tools/GlobTool/GlobTool.ts — 典型的 schema 定义方式
const inputSchema = lazySchema(() =>
  z.strictObject({
    pattern: z.string().describe('The glob pattern to match files against'),
    path: z.string().optional().describe(
      'The directory to search in. If not specified, the current working directory will be used.'
    ),
  }),
)
```

`z.strictObject` 用于严格模式——拒绝未知字段。每个字段的 `.describe()` 会被转换为 JSON Schema 的 description，直接呈现给模型。

### 2.4 checkPermissions() — 权限检查

```typescript
checkPermissions(
  input: z.infer<Input>,
  context: ToolUseContext,
): Promise<PermissionResult>
```

这是工具级别的权限检查方法。在 `validateInput()` 通过之后、`call()` 执行之前被调用。返回值 `PermissionResult` 是一个联合类型：

- `{ behavior: 'allow', updatedInput }` — 允许执行，可以修改 input（例如规范化路径）
- `{ behavior: 'deny', message }` — 拒绝执行，附带原因说明
- `{ behavior: 'passthrough', message }` — 交由通用权限系统处理（用于 MCP 工具等）
- `{ behavior: 'ask', message }` — 需要用户交互确认

不同工具有不同的权限策略：

```typescript
// FileEditTool — 检查写入权限（路径级别）
async checkPermissions(input, context): Promise<PermissionDecision> {
  const appState = context.getAppState()
  return checkWritePermissionForTool(
    FileEditTool, input, appState.toolPermissionContext,
  )
}

// GlobTool — 检查读取权限
async checkPermissions(input, context): Promise<PermissionDecision> {
  const appState = context.getAppState()
  return checkReadPermissionForTool(
    GlobTool, input, appState.toolPermissionContext,
  )
}

// TodoWriteTool — 无需权限检查
async checkPermissions(input) {
  return { behavior: 'allow', updatedInput: input }
}

// MCPTool — 透传给通用权限系统
async checkPermissions(): Promise<PermissionResult> {
  return { behavior: 'passthrough', message: 'MCPTool requires permission.' }
}
```

### 2.5 isReadOnly() 与 isConcurrencySafe()

这两个方法是工具编排系统的核心语义声明：

```typescript
isReadOnly(input: z.infer<Input>): boolean       // 本次调用是否只读
isConcurrencySafe(input: z.infer<Input>): boolean // 本次调用是否可安全并发
```

**关键点**：这两个方法接收 `input` 参数，意味着**同一个工具的不同调用可能有不同的并发性**。典型案例是 BashTool：

```typescript
// src/tools/BashTool/BashTool.tsx
isConcurrencySafe(input) {
  // BashTool 的并发安全性取决于命令是否只读
  return this.isReadOnly?.(input) ?? false;
},
isReadOnly(input) {
  // 根据命令内容判断：ls、cat、grep 等是只读的
  // git push、rm 等不是只读的
  const compoundCommandHasCd = commandHasAnyCd(input.command);
  const result = checkReadOnlyConstraints(input, compoundCommandHasCd);
  return result.behavior === 'allow';
},
```

而 GlobTool 和 GrepTool 则始终是只读和并发安全的：

```typescript
// src/tools/GlobTool/GlobTool.ts
isConcurrencySafe() { return true },
isReadOnly() { return true },
```

编排系统基于这些声明来决定：并发安全的工具可以同时执行（提高效率），非并发安全的工具必须串行执行（保证正确性）。

### 2.6 prompt() — 系统提示

```typescript
prompt(options: {
  getToolPermissionContext: () => Promise<ToolPermissionContext>
  tools: Tools
  agents: AgentDefinition[]
  allowedAgentTypes?: string[]
}): Promise<string>
```

返回一段文字，会被嵌入到发送给模型的系统提示中，告诉模型如何使用这个工具。例如 BashTool 的 prompt 包含了详细的 shell 使用指南、Git 操作规范、安全注意事项等。

### 2.7 shouldDefer 与 alwaysLoad — 延迟加载

```typescript
readonly shouldDefer?: boolean   // 为 true 时，工具 schema 不包含在初始 prompt 中
readonly alwaysLoad?: boolean    // 为 true 时，即使启用了 ToolSearch 也始终加载
```

当工具数量超过阈值时，Claude Code 启用 **ToolSearch** 机制。被标记为 `shouldDefer: true` 的工具（如 WebFetchTool、TodoWriteTool）不会在初始请求中包含完整 schema，而是通过 `defer_loading: true` 告诉 API 服务器只保留工具名。模型需要先调用 ToolSearchTool 来"发现"这些工具，之后才能使用。

```typescript
// WebFetchTool — 标记为延迟加载
export const WebFetchTool = buildTool({
  name: WEB_FETCH_TOOL_NAME,
  shouldDefer: true,
  // ...
})
```

`alwaysLoad` 是反向标记，用于确保某些关键工具即使在 ToolSearch 模式下也始终可用，不需要额外的搜索步骤。

### 2.8 渲染方法族

Tool 接口定义了一整套渲染方法，实现了执行逻辑与 UI 呈现的完全分离：

```typescript
// 渲染工具调用消息（模型发起调用时显示）
// input 是 Partial 类型——因为流式传输时参数可能尚未完整
renderToolUseMessage(
  input: Partial<z.infer<Input>>,
  options: { theme: ThemeName; verbose: boolean; commands?: Command[] },
): React.ReactNode

// 渲染工具结果消息（工具执行完成后显示）
renderToolResultMessage?(
  content: Output,
  progressMessagesForMessage: ProgressMessage<P>[],
  options: { style?: 'condensed'; theme: ThemeName; verbose: boolean; ... },
): React.ReactNode

// 渲染执行进度（工具正在运行时的实时显示）
renderToolUseProgressMessage?(
  progressMessagesForMessage: ProgressMessage<P>[],
  options: { tools: Tools; verbose: boolean; terminalSize?: {...}; ... },
): React.ReactNode

// 渲染拒绝消息（用户拒绝权限时显示）
renderToolUseRejectedMessage?(input, options): React.ReactNode

// 渲染错误消息（工具执行出错时显示）
renderToolUseErrorMessage?(result, options): React.ReactNode

// 分组渲染（多个并行的同类型工具一起显示）
renderGroupedToolUse?(toolUses, options): React.ReactNode | null
```

每个渲染方法都是可选的（除 `renderToolUseMessage` 外），未实现时使用默认 fallback。这让简单工具（如 TodoWriteTool）可以完全不关心渲染，而复杂工具（如 BashTool）可以精细控制每个状态的显示。

### 2.9 其他重要方法

```typescript
// 工具是否启用
isEnabled(): boolean

// 工具是否是破坏性操作（删除、覆盖等）
isDestructive?(input): boolean

// 用户中断行为：'cancel' 停止工具并丢弃结果，'block' 继续运行
interruptBehavior?(): 'cancel' | 'block'

// 判断是否为搜索/读取命令（用于 UI 折叠显示）
isSearchOrReadCommand?(input): { isSearch: boolean; isRead: boolean; isList?: boolean }

// 获取工具操作的文件路径（用于文件级权限检查）
getPath?(input): string

// 为 hook 的 if 条件准备匹配器
preparePermissionMatcher?(input): Promise<(pattern: string) => boolean>

// 输入验证（在权限检查之前执行）
validateInput?(input, context): Promise<ValidationResult>

// 将工具输入转换为安全分类器的输入格式
toAutoClassifierInput(input): unknown

// 将工具结果映射为 API 的 ToolResultBlockParam 格式
mapToolResultToToolResultBlockParam(content, toolUseID): ToolResultBlockParam

// 大结果存储阈值
maxResultSizeChars: number

// 为 ToolSearch 提供的关键词提示
searchHint?: string
```

`maxResultSizeChars` 控制工具结果的存储行为：当结果超过此阈值时，内容会被持久化到磁盘文件，模型只收到预览和文件路径，避免 context 膨胀。

---

## 3. ToolDef + buildTool() 工厂模式

### 3.1 ToolDef — 简化的工具定义

直接实现完整的 `Tool` 接口需要提供所有方法，哪怕很多工具的实现是相同的（如 `isEnabled() { return true }`）。`ToolDef` 类型让这些通用方法变成可选的：

```typescript
// src/Tool.ts

// 可以有默认值的方法
type DefaultableToolKeys =
  | 'isEnabled'
  | 'isConcurrencySafe'
  | 'isReadOnly'
  | 'isDestructive'
  | 'checkPermissions'
  | 'toAutoClassifierInput'
  | 'userFacingName'

// ToolDef = Tool 但 defaultable 的方法是可选的
export type ToolDef<Input, Output, P> =
  Omit<Tool<Input, Output, P>, DefaultableToolKeys> &
  Partial<Pick<Tool<Input, Output, P>, DefaultableToolKeys>>
```

### 3.2 buildTool() — 默认值填充

`buildTool()` 是所有工具定义的统一入口，它将 `ToolDef` 转换为完整的 `Tool`：

```typescript
// src/Tool.ts

// 安全的默认值——fail-closed 策略
const TOOL_DEFAULTS = {
  isEnabled: () => true,                    // 默认启用
  isConcurrencySafe: (_input?) => false,    // 默认不安全（保守策略）
  isReadOnly: (_input?) => false,           // 默认假设有写入（保守策略）
  isDestructive: (_input?) => false,        // 默认非破坏性
  checkPermissions: (input, _ctx?) =>       // 默认允许（交由通用权限系统处理）
    Promise.resolve({ behavior: 'allow', updatedInput: input }),
  toAutoClassifierInput: (_input?) => '',   // 默认跳过分类器
  userFacingName: (_input?) => '',          // 默认空名称
}

export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,              // 先铺默认值
    userFacingName: () => def.name, // userFacingName 默认返回工具名
    ...def,                         // 用户定义覆盖默认值
  } as BuiltTool<D>
}
```

**设计原则——fail-closed**：
- `isConcurrencySafe` 默认 `false`：不确定时假设不安全，串行执行
- `isReadOnly` 默认 `false`：不确定时假设有写入
- `checkPermissions` 默认 `allow`：但这只是工具级别的默认，通用权限系统仍会检查

这意味着一个最简工具定义只需要提供 `name`、`inputSchema`、`call()`、`prompt()` 等少量必要方法。其他一切都有合理的默认行为。

### 3.3 类型推断魔法

`buildTool` 使用了精心设计的泛型类型 `BuiltTool<D>` 来确保类型安全：

```typescript
// D 从调用处推断具体类型
type BuiltTool<D> = Omit<D, DefaultableToolKeys> & {
  [K in DefaultableToolKeys]-?: K extends keyof D
    ? undefined extends D[K]
      ? ToolDefaults[K]   // 如果 D 中是可选的，用默认值类型
      : D[K]              // 如果 D 中是必需的，用 D 的类型
    : ToolDefaults[K]     // 如果 D 中没有，用默认值类型
}
```

这保证了 `buildTool` 的返回值类型精确反映了实际运行时的形状——用户定义的方法保留原始类型，省略的方法使用默认值的类型。所有 60+ 个工具都通过 `buildTool` 创建，通过零类型错误证明了类型系统的正确性。

---

## 4. 工具注册与发现完整流程

### 4.1 getAllBaseTools() — 全量工具注册表

`getAllBaseTools()` 是所有工具的**源头**，定义在 `src/tools.ts` 中。它返回当前环境下所有可能可用的工具：

```typescript
// src/tools.ts — 全量工具注册表（简化）
export function getAllBaseTools(): Tools {
  return [
    AgentTool,          // 子 agent 工具
    TaskOutputTool,     // 任务输出工具
    BashTool,           // Shell 命令执行
    // 当内置搜索工具可用时，不注册 Glob/Grep
    ...(hasEmbeddedSearchTools() ? [] : [GlobTool, GrepTool]),
    ExitPlanModeV2Tool, // 退出计划模式
    FileReadTool,       // 文件读取
    FileEditTool,       // 文件编辑
    FileWriteTool,      // 文件写入
    NotebookEditTool,   // Jupyter 笔记本编辑
    WebFetchTool,       // 网页内容获取
    TodoWriteTool,      // 任务追踪
    WebSearchTool,      // 网络搜索
    TaskStopTool,       // 停止后台任务
    AskUserQuestionTool,// 向用户提问
    SkillTool,          // 技能执行
    EnterPlanModeTool,  // 进入计划模式
    // 条件工具——根据环境变量和 feature flag 决定是否包含
    ...(process.env.USER_TYPE === 'ant' ? [ConfigTool, TungstenTool] : []),
    ...(isTodoV2Enabled()
      ? [TaskCreateTool, TaskGetTool, TaskUpdateTool, TaskListTool] : []),
    ...(isWorktreeModeEnabled() ? [EnterWorktreeTool, ExitWorktreeTool] : []),
    getSendMessageTool(),
    ...(isAgentSwarmsEnabled() ? [getTeamCreateTool(), getTeamDeleteTool()] : []),
    // ToolSearch 工具——仅在优化模式下启用
    ...(isToolSearchEnabledOptimistic() ? [ToolSearchTool] : []),
    // 更多条件工具...
    ListMcpResourcesTool,
    ReadMcpResourceTool,
  ]
}
```

**设计要点**：

1. **条件注册**：工具通过 `feature()` flag、环境变量、runtime check 来决定是否出现在列表中。例如 `process.env.USER_TYPE === 'ant'` 控制内部工具的可见性
2. **embedded 搜索替换**：当 Ant 原生构建内嵌了 bfs/ugrep 时，shell 中的 find/grep 已被别名替换，此时不需要独立的 GlobTool/GrepTool
3. **延迟 require**：使用 `require()` 而非 `import` 来打破循环依赖，如 `getTeamCreateTool()`
4. **Dead code elimination**：通过 `feature()` from `bun:bundle` 实现构建时的条件编译，不满足条件的工具代码会被完全移除

### 4.2 getTools() — 模式感知的工具过滤

`getTools()` 在 `getAllBaseTools()` 基础上应用权限过滤和模式选择：

```typescript
// src/tools.ts
export const getTools = (permissionContext: ToolPermissionContext): Tools => {
  // === Simple 模式：最精简的工具集 ===
  if (isEnvTruthy(process.env.CLAUDE_CODE_SIMPLE)) {
    // 仅 Bash + Read + Edit
    const simpleTools: Tool[] = [BashTool, FileReadTool, FileEditTool]
    // Coordinator 模式下额外添加 AgentTool 和 TaskStopTool
    if (feature('COORDINATOR_MODE') && coordinatorModeModule?.isCoordinatorMode()) {
      simpleTools.push(AgentTool, TaskStopTool, getSendMessageTool())
    }
    return filterToolsByDenyRules(simpleTools, permissionContext)
  }

  // === Full 模式：完整工具集 ===
  // 过滤掉特殊工具（它们在别处条件添加）
  const specialTools = new Set([
    ListMcpResourcesTool.name, ReadMcpResourceTool.name, SYNTHETIC_OUTPUT_TOOL_NAME,
  ])
  const tools = getAllBaseTools().filter(tool => !specialTools.has(tool.name))

  // 应用 deny 规则过滤
  let allowedTools = filterToolsByDenyRules(tools, permissionContext)

  // === REPL 模式：隐藏被 REPL 包装的原始工具 ===
  if (isReplModeEnabled()) {
    const replEnabled = allowedTools.some(tool =>
      toolMatchesName(tool, REPL_TOOL_NAME),
    )
    if (replEnabled) {
      // Bash/Read/Edit 等工具由 REPL VM 内部使用，不直接暴露给模型
      allowedTools = allowedTools.filter(tool => !REPL_ONLY_TOOLS.has(tool.name))
    }
  }

  // 最终 isEnabled() 检查
  const isEnabled = allowedTools.map(_ => _.isEnabled())
  return allowedTools.filter((_, i) => isEnabled[i])
}
```

三种模式的工具集差异：

| 模式 | 环境变量 | 可用工具 |
|------|---------|---------|
| **Simple** | `CLAUDE_CODE_SIMPLE=1` | Bash, FileRead, FileEdit（最小集） |
| **REPL** | REPL 模式启用 | REPL 工具包装了底层原语，直接工具被隐藏 |
| **Full** | 默认 | 全量工具（经 deny rules 和 isEnabled 过滤） |

### 4.3 filterToolsByDenyRules() — deny 规则过滤

```typescript
// src/tools.ts
export function filterToolsByDenyRules<T extends { name: string; mcpInfo?: {...} }>(
  tools: readonly T[],
  permissionContext: ToolPermissionContext,
): T[] {
  // 过滤掉被 deny 规则完全禁用的工具
  // 支持工具名精确匹配和 MCP 服务器前缀匹配
  // 例如 deny 规则 "mcp__server" 会移除该服务器的所有工具
  return tools.filter(tool => !getDenyRuleForTool(permissionContext, tool))
}
```

这确保了在模型看到工具列表之前，被管理员 deny 的工具已经完全不可见。

### 4.4 assembleToolPool() — 合并 MCP 工具

`assembleToolPool()` 是最终的工具池组装函数，将内置工具与 MCP 工具合并：

```typescript
// src/tools.ts
export function assembleToolPool(
  permissionContext: ToolPermissionContext,
  mcpTools: Tools,
): Tools {
  const builtInTools = getTools(permissionContext)
  const allowedMcpTools = filterToolsByDenyRules(mcpTools, permissionContext)

  // 排序策略：内置工具作为前缀，MCP 工具作为后缀
  // 目的：保持 prompt cache 稳定性
  // API 服务器在最后一个内置工具之后放置 cache 断点
  // 如果 MCP 工具混入内置工具区间，会使所有下游 cache key 失效
  const byName = (a: Tool, b: Tool) => a.name.localeCompare(b.name)
  return uniqBy(
    [...builtInTools].sort(byName)       // 内置工具按名称排序
      .concat(allowedMcpTools.sort(byName)), // MCP 工具按名称排序，追加在后
    'name',  // 按 name 去重——内置工具优先（出现在前面）
  )
}
```

**Prompt Cache 稳定性**是一个精妙的设计考虑：API 服务器为工具定义设置了缓存断点。如果工具顺序不稳定（MCP 工具每次连接后位置变化），缓存会频繁失效，增加延迟和成本。因此采用分区排序策略：内置工具始终在前，MCP 工具始终在后，各自内部按名称排序。

---

## 5. 核心工具逐个详解

### 5.1 BashTool — Shell 命令执行

**文件位置**：`src/tools/BashTool/BashTool.tsx`

BashTool 是最复杂的工具，负责在用户系统上执行 shell 命令。

**输入 Schema**：

```typescript
// 完整输入（包含内部字段）
const fullInputSchema = lazySchema(() => z.strictObject({
  command: z.string().describe('The command to execute'),
  timeout: semanticNumber(z.number().optional())
    .describe(`Optional timeout in milliseconds (max ${getMaxTimeoutMs()})`),
  description: z.string().optional()
    .describe('Clear, concise description of what this command does'),
  run_in_background: semanticBoolean(z.boolean().optional())
    .describe('Set to true to run this command in the background.'),
  dangerouslyDisableSandbox: semanticBoolean(z.boolean().optional())
    .describe('Override sandbox mode'),
  _simulatedSedEdit: z.object({...}).optional()  // 内部字段，不暴露给模型
}))

// 模型可见的 schema 会 omit 掉内部字段
const inputSchema = lazySchema(() =>
  isBackgroundTasksDisabled
    ? fullInputSchema().omit({ run_in_background: true, _simulatedSedEdit: true })
    : fullInputSchema().omit({ _simulatedSedEdit: true })
)
```

**输出 Schema**：

```typescript
const outputSchema = lazySchema(() => z.object({
  stdout: z.string(),                    // 标准输出
  stderr: z.string(),                    // 标准错误
  interrupted: z.boolean(),              // 是否被中断
  isImage: z.boolean().optional(),       // 输出是否为图像
  backgroundTaskId: z.string().optional(), // 后台任务 ID
  persistedOutputPath: z.string().optional(), // 大输出的持久化路径
  // ... 更多元数据字段
}))
```

**关键特性**：

1. **命令语义分析**：BashTool 解析命令来判断是否只读（`isReadOnly`），是否为搜索/读取命令（`isSearchOrReadCommand`）。例如 `ls`、`cat`、`grep` 被归类为只读可并发：

```typescript
// 搜索命令——用于 UI 折叠显示
const BASH_SEARCH_COMMANDS = new Set([
  'find', 'grep', 'rg', 'ag', 'ack', 'locate', 'which', 'whereis'
])
// 读取命令
const BASH_READ_COMMANDS = new Set([
  'cat', 'head', 'tail', 'less', 'more', 'wc', 'stat', 'file', 'jq', 'awk', ...
])
// 目录列表命令
const BASH_LIST_COMMANDS = new Set(['ls', 'tree', 'du'])
```

2. **沙箱执行**：通过 `shouldUseSandbox()` 决定是否在沙箱中运行命令，保护系统安全
3. **后台任务**：支持 `run_in_background` 参数将长时间运行的命令转为后台任务
4. **sed 编辑检测**：自动检测 `sed -i` 类型的命令，在权限对话框中显示预览 diff
5. **进度报告**：长时间运行的命令会通过 `BashProgress` 实时报告 stdout/stderr 输出
6. **权限匹配器**：解析复合命令为子命令列表，每个子命令独立匹配权限规则：

```typescript
async preparePermissionMatcher({ command }) {
  const parsed = await parseForSecurity(command);
  if (parsed.kind !== 'simple') return () => true; // 复杂命令 fail-safe
  const subcommands = parsed.commands.map(c => c.argv.join(' '));
  return pattern => {
    // "ls && git push" 中的 "git push" 会匹配 "Bash(git *)" 规则
    return subcommands.some(cmd => matchWildcardPattern(pattern, cmd));
  };
},
```

### 5.2 FileEditTool — 文件编辑

**文件位置**：`src/tools/FileEditTool/FileEditTool.ts`

FileEditTool 执行精确的字符串替换编辑。

**输入**：

```typescript
// src/tools/FileEditTool/types.ts（通过 lazySchema 定义）
{
  file_path: string,     // 文件的绝对路径
  old_string: string,    // 要替换的原始文本
  new_string: string,    // 替换后的新文本
  replace_all?: boolean, // 是否替换所有匹配项（默认 false）
}
```

**关键逻辑**：

1. **唯一性检查**：默认情况下 `old_string` 在文件中必须是唯一的。如果有多个匹配且 `replace_all` 为 false，工具会报错，要求提供更多上下文或使用 `replace_all`
2. **文件修改时间验证**：通过 `readFileState` 缓存检查文件是否在上次读取后被外部修改。如果被修改，报 `FILE_UNEXPECTEDLY_MODIFIED_ERROR` 错误，迫使模型重新读取文件
3. **Git diff 追踪**：编辑后自动获取 git diff，用于 UI 渲染
4. **文件历史**：支持通过文件历史记录进行 undo
5. **LSP 通知**：编辑后通知 LSP 服务器和 VS Code SDK

```typescript
// 权限检查——使用文件系统写入权限
async checkPermissions(input, context): Promise<PermissionDecision> {
  const appState = context.getAppState()
  return checkWritePermissionForTool(
    FileEditTool, input, appState.toolPermissionContext,
  )
},
```

`inputsEquivalent` 方法允许判断两次编辑是否等价（用于推测执行优化）：

```typescript
inputsEquivalent: areFileEditsInputsEquivalent,
```

### 5.3 FileReadTool — 文件读取

**文件位置**：`src/tools/FileReadTool/FileReadTool.ts`

FileReadTool 是模型获取文件内容的主要方式，支持多种文件格式。

**输入**：

```typescript
{
  file_path: string,    // 文件的绝对路径
  offset?: number,      // 起始行号（大文件分段读取）
  limit?: number,       // 读取行数
  pages?: string,       // PDF 页码范围（如 "1-5"）
}
```

**输出**（discriminated union）：

```typescript
// 文本文件
{ type: 'text', file: { filePath, content, numLines, startLine, totalLines } }
// 图片文件
{ type: 'image', file: { base64, type, originalSize, dimensions } }
// Jupyter 笔记本
{ type: 'notebook', file: { filePath, cells } }
// PDF 文件
{ type: 'pdf', file: { filePath, base64, originalSize } }
```

**关键特性**：

1. **Token 限制**：通过 `fileReadingLimits.maxTokens` 限制单次读取的 token 数，超出时要求使用 offset/limit 分段读取
2. **设备文件保护**：阻止读取 `/dev/zero`、`/dev/random` 等会导致进程挂起的设备文件
3. **图片自动处理**：检测图片格式并自动压缩/缩放，通过 base64 编码传递给模型
4. **PDF 支持**：支持读取 PDF 文件，大 PDF 强制使用页码范围参数
5. **文件状态缓存**：读取后更新 `readFileState`，供 FileEditTool 检测并发修改
6. **`maxResultSizeChars: Infinity`**：FileReadTool 的结果永不持久化到磁盘，因为持久化会导致循环读取问题

```typescript
// 并发安全 + 只读
isConcurrencySafe() { return true },
isReadOnly() { return true },
```

### 5.4 FileWriteTool — 文件写入

**文件位置**：`src/tools/FileWriteTool/FileWriteTool.ts`

FileWriteTool 用于创建新文件或完全覆盖现有文件。

**输入**：

```typescript
{
  file_path: string,  // 文件的绝对路径
  content: string,    // 要写入的完整内容
}
```

**输出**：

```typescript
{
  type: 'create' | 'update',  // 是新建还是更新
  filePath: string,
  content: string,
  structuredPatch: Hunk[],     // diff patch
  originalFile: string | null, // 原始内容（新文件为 null）
  gitDiff?: GitDiff,
}
```

FileWriteTool 与 FileEditTool 的区别：FileEditTool 做精确替换（适合小改动），FileWriteTool 做整体覆盖（适合创建新文件或大规模重写）。权限系统对两者的处理一致——都需要文件写入权限。

### 5.5 GlobTool — 文件模式搜索

**文件位置**：`src/tools/GlobTool/GlobTool.ts`

GlobTool 根据 glob 模式搜索文件，相当于 `find` 命令但更快。

**输入**：

```typescript
{
  pattern: string,     // glob 模式，如 "**/*.ts"
  path?: string,       // 搜索目录，默认为当前工作目录
}
```

**输出**：

```typescript
{
  durationMs: number,       // 搜索耗时
  numFiles: number,         // 找到的文件数
  filenames: string[],      // 文件路径数组
  truncated: boolean,       // 结果是否被截断
}
```

```typescript
// 标记为并发安全 + 只读
isConcurrencySafe() { return true },
isReadOnly() { return true },
```

GlobTool 有路径验证逻辑：检查搜索路径是否存在，是否为目录，并拒绝 UNC 路径（防止 NTLM 凭证泄露）。

### 5.6 GrepTool — 内容正则搜索

**文件位置**：`src/tools/GrepTool/GrepTool.ts`

GrepTool 基于 ripgrep (rg) 实现，提供极快的正则搜索。

**输入**（丰富的参数设计）：

```typescript
{
  pattern: string,         // 正则表达式模式
  path?: string,           // 搜索路径
  glob?: string,           // 文件过滤 glob
  output_mode?: 'content' | 'files_with_matches' | 'count',
  '-B'?: number,           // 前置上下文行数
  '-A'?: number,           // 后置上下文行数
  '-C'?: number,           // 双向上下文行数
  context?: number,        // -C 的别名
  '-n'?: boolean,          // 显示行号
  '-i'?: boolean,          // 忽略大小写
  type?: string,           // 文件类型过滤
  head_limit?: number,     // 结果限制（默认 250）
  offset?: number,         // 分页偏移
  multiline?: boolean,     // 多行匹配模式
}
```

**关键设计**：

1. **默认限制 250 条**：防止无界搜索导致 context 膨胀。模型可以传 `head_limit: 0` 来解除限制（但 prompt 中会提示"use sparingly"）
2. **分页支持**：通过 `offset` + `head_limit` 实现搜索结果分页
3. **VCS 目录排除**：自动排除 `.git`、`.svn`、`.hg` 等版本控制目录
4. **`semanticNumber` / `semanticBoolean`**：处理模型可能传入字符串类型的布尔值/数字（如 `"true"` 而非 `true`），增强鲁棒性

```typescript
// 自动排除的 VCS 目录
const VCS_DIRECTORIES_TO_EXCLUDE = [
  '.git', '.svn', '.hg', '.bzr', '.jj', '.sl',
] as const
```

### 5.7 WebFetchTool — 网页内容获取

**文件位置**：`src/tools/WebFetchTool/WebFetchTool.ts`

WebFetchTool 获取 URL 内容并转换为 Markdown 格式。

**输入**：

```typescript
{
  url: string,     // 要获取的 URL
  prompt: string,  // 对获取内容的处理指令
}
```

**输出**：

```typescript
{
  bytes: number,       // 内容大小
  code: number,        // HTTP 状态码
  codeText: string,    // HTTP 状态文本
  result: string,      // 处理后的内容
  durationMs: number,  // 耗时
  url: string,         // 实际获取的 URL
}
```

**关键特性**：

1. **shouldDefer: true**：默认延迟加载，模型需要通过 ToolSearch 发现
2. **预批准域名**：某些域名（如文档站点）无需用户确认即可访问
3. **并发安全 + 只读**
4. **权限基于域名**：权限规则以 `domain:hostname` 格式存储，允许一次性批准整个域名

```typescript
// 权限检查——预批准域名直接放行
async checkPermissions(input, context): Promise<PermissionDecision> {
  try {
    const { url } = input as { url: string }
    const parsedUrl = new URL(url)
    if (isPreapprovedHost(parsedUrl.hostname, parsedUrl.pathname)) {
      return { behavior: 'allow', updatedInput: input,
        decisionReason: { type: 'other', reason: 'Preapproved host' } }
    }
  } catch { /* 解析失败则走正常权限流程 */ }
  // ... 正常权限检查
}
```

### 5.8 WebSearchTool — 网络搜索

**文件位置**：`src/tools/WebSearchTool/WebSearchTool.ts`

WebSearchTool 利用 Anthropic API 的内置 web_search 工具进行搜索。

**输入**：

```typescript
{
  query: string,                // 搜索查询
  allowed_domains?: string[],   // 限制搜索域名
  blocked_domains?: string[],   // 排除搜索域名
}
```

**特殊之处**：WebSearchTool 不直接执行搜索，而是构造一个带有 `web_search_20250305` 工具的 API 请求，让 Claude 模型在子请求中使用搜索能力：

```typescript
function makeToolSchema(input: Input): BetaWebSearchTool20250305 {
  return {
    type: 'web_search_20250305',
    name: 'web_search',
    allowed_domains: input.allowed_domains,
    blocked_domains: input.blocked_domains,
  }
}
```

### 5.9 AgentTool — 子 Agent（简述）

**文件位置**：`src/tools/AgentTool/AgentTool.tsx`

AgentTool 是 Claude Code 的多 agent 能力的核心，允许主 agent 创建子 agent 来并行处理子任务。它是整个代码库中最复杂的工具之一，将在第 6 篇中详细讨论。

核心概念：
- **子 agent**：一个完整的 Claude 对话循环，有自己的 tool pool、token 预算和 abort controller
- **后台任务**：长时间运行的 agent 可以转为后台任务，主线程继续执行
- **fork 模式**：通过 git worktree 创建代码副本，让子 agent 在隔离环境中工作
- **远程执行**：支持将任务 teleport 到远程机器执行

### 5.10 SkillTool — 技能执行

**文件位置**：`src/tools/SkillTool/SkillTool.ts`

SkillTool 执行预定义的"技能"——本质上是参数化的 prompt 模板。技能可以来自本地文件系统（`commands/` 目录）或 MCP 服务器。

```typescript
// 获取所有可用命令（本地 + MCP 技能）
async function getAllCommands(context: ToolUseContext): Promise<Command[]> {
  const mcpSkills = context.getAppState().mcp.commands.filter(
    cmd => cmd.type === 'prompt' && cmd.loadedFrom === 'mcp',
  )
  if (mcpSkills.length === 0) return getCommands(getProjectRoot())
  const localCommands = await getCommands(getProjectRoot())
  return uniqBy([...localCommands, ...mcpSkills], 'name')
}
```

SkillTool 在内部创建一个子 agent（通过 `runAgent`），在隔离的上下文中执行技能定义的 prompt，有独立的 token 预算。

### 5.11 MCPTool — MCP 协议桥接

**文件位置**：`src/tools/MCPTool/MCPTool.ts`

MCPTool 是所有 MCP (Model Context Protocol) 工具的模板。它定义了基础结构，但大部分属性会在 `mcpClient.ts` 中被覆盖：

```typescript
export const MCPTool = buildTool({
  isMcp: true,
  name: 'mcp',           // 被 mcpClient.ts 覆盖为 "mcp__server__tool"
  async description() { return DESCRIPTION },  // 被覆盖
  async prompt() { return PROMPT },            // 被覆盖
  async call() { return { data: '' } },        // 被覆盖
  userFacingName: () => 'mcp',                 // 被覆盖

  // 通用 schema——允许任意 object 输入
  get inputSchema() { return inputSchema() },  // z.object({}).passthrough()

  // MCP 工具的权限统一走 passthrough
  async checkPermissions(): Promise<PermissionResult> {
    return { behavior: 'passthrough', message: 'MCPTool requires permission.' }
  },
  // ...
} satisfies ToolDef<InputSchema, Output>)
```

MCP 工具的创建流程：MCP 客户端连接服务器后，为每个远端工具克隆 MCPTool 模板，覆盖 `name`、`description`、`call`、`inputJSONSchema` 等属性，形成一个独立的 Tool 对象。这些工具通过 `mcpInfo` 字段保留原始的服务器名和工具名。

### 5.12 TodoWriteTool — 任务追踪

**文件位置**：`src/tools/TodoWriteTool/TodoWriteTool.ts`

TodoWriteTool 管理会话级别的任务列表，让模型在执行复杂任务时追踪进度。

```typescript
export const TodoWriteTool = buildTool({
  name: TODO_WRITE_TOOL_NAME,
  shouldDefer: true,      // 延迟加载
  strict: true,           // 严格 schema
  isEnabled() { return !isTodoV2Enabled() },  // v2 启用时禁用 v1

  async call({ todos }, context) {
    const appState = context.getAppState()
    const todoKey = context.agentId ?? getSessionId()
    const oldTodos = appState.todos[todoKey] ?? []
    const allDone = todos.every(_ => _.status === 'completed')
    const newTodos = allDone ? [] : todos

    // 更新应用状态中的 todo 列表
    context.setAppState(prev => ({
      ...prev,
      todos: { ...prev.todos, [todoKey]: newTodos },
    }))

    return { data: { oldTodos, newTodos: todos, verificationNudgeNeeded } }
  },

  // 无需权限
  async checkPermissions(input) {
    return { behavior: 'allow', updatedInput: input }
  },

  // 不渲染到聊天流中（由 todo 面板显示）
  renderToolUseMessage() { return null },
})
```

**设计亮点**：
- 按 `agentId` 或 `sessionId` 存储，子 agent 有独立的 todo 列表
- 全部完成时自动清空列表
- 检测验证步骤缺失：当 3+ 个任务一次性完成且没有验证步骤时，提醒模型发起验证

### 5.13 ToolSearchTool — 延迟工具发现

**文件位置**：`src/tools/ToolSearchTool/ToolSearchTool.ts`

ToolSearchTool 让模型在运行时按需发现和加载被延迟的工具。

**输入**：

```typescript
{
  query: string,       // 搜索查询，支持 "select:ToolName" 精确选择
  max_results?: number, // 最大结果数（默认 5）
}
```

**搜索策略**：

1. **精确选择**：`"select:WebFetch,TodoWrite"` 直接按名称加载指定工具
2. **关键词搜索**：解析工具名（CamelCase 拆分、MCP `__` 拆分）和 `searchHint`，计算匹配分数
3. **描述搜索**：异步获取工具的 prompt 描述，用于深度匹配（结果被 memoize 缓存）

```typescript
// 工具名解析——将 CamelCase 和 mcp__server__tool 拆分为搜索词
function parseToolName(name: string): { parts: string[]; full: string; isMcp: boolean } {
  if (name.startsWith('mcp__')) {
    const parts = name.replace(/^mcp__/, '').split('__').flatMap(p => p.split('_'))
    return { parts, full: ..., isMcp: true }
  }
  // CamelCase 拆分
  const parts = name.replace(/([a-z])([A-Z])/g, '$1 $2').split(/[\s_]+/)
  return { parts, full: name.toLowerCase(), isMcp: false }
}
```

**输出**包含匹配的工具名列表。这些工具名会被 `claude.ts` 的 schema 过滤逻辑识别，在下一轮 API 请求中发送完整的工具 schema（去除 `defer_loading`），使模型可以正常调用它们。

---

## 6. 工具执行管线

### 6.1 toolOrchestration.ts — 批次划分

工具编排系统位于 `src/services/tools/toolOrchestration.ts`。当模型返回一个或多个 tool_use block 时，编排器决定执行顺序和并发策略。

#### 分区算法

`partitionToolCalls()` 将工具调用序列划分为批次：

```typescript
// src/services/tools/toolOrchestration.ts
function partitionToolCalls(
  toolUseMessages: ToolUseBlock[],
  toolUseContext: ToolUseContext,
): Batch[] {
  return toolUseMessages.reduce((acc: Batch[], toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)
    const parsedInput = tool?.inputSchema.safeParse(toolUse.input)

    // 安全判断：解析失败或判断抛异常时，保守地视为非并发安全
    const isConcurrencySafe = parsedInput?.success
      ? (() => {
          try { return Boolean(tool?.isConcurrencySafe(parsedInput.data)) }
          catch { return false }
        })()
      : false

    // 连续的并发安全工具合并为一个批次
    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1]!.blocks.push(toolUse)
    } else {
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }
    return acc
  }, [])
}
```

分区规则：
- 连续的并发安全工具（`isConcurrencySafe` 为 true）合并为一个**并发批次**
- 非并发安全的工具各自独立为一个**串行批次**（单个工具）
- 并发/串行批次交替出现时，按顺序依次执行

示例：假设模型调用了 `[Grep, Glob, FileEdit, Grep, Glob]`，分区结果为：

```
Batch 1 (concurrent): [Grep, Glob]    — 并行执行
Batch 2 (serial):     [FileEdit]      — 单独串行执行
Batch 3 (concurrent): [Grep, Glob]    — 并行执行
```

#### 并发执行

```typescript
// 并发批次——使用 all() 工具函数并发执行
async function* runToolsConcurrently(
  toolUseMessages: ToolUseBlock[],
  assistantMessages: AssistantMessage[],
  canUseTool: CanUseToolFn,
  toolUseContext: ToolUseContext,
): AsyncGenerator<MessageUpdateLazy, void> {
  yield* all(
    toolUseMessages.map(async function* (toolUse) {
      // 每个工具独立执行
      yield* runToolUse(toolUse, assistantMessage, canUseTool, toolUseContext)
    }),
    getMaxToolUseConcurrency(), // 最大并发数，默认 10，可通过环境变量配置
  )
}
```

**并发限制**：通过 `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` 环境变量控制，默认 10。

#### 串行执行

```typescript
async function* runToolsSerially(
  toolUseMessages: ToolUseBlock[],
  assistantMessages: AssistantMessage[],
  canUseTool: CanUseToolFn,
  toolUseContext: ToolUseContext,
): AsyncGenerator<MessageUpdate, void> {
  let currentContext = toolUseContext
  for (const toolUse of toolUseMessages) {
    for await (const update of runToolUse(toolUse, ...)) {
      if (update.contextModifier) {
        // 串行执行时，contextModifier 会更新后续工具的上下文
        currentContext = update.contextModifier.modifyContext(currentContext)
      }
      yield { message: update.message, newContext: currentContext }
    }
  }
}
```

### 6.2 StreamingToolExecutor — 流式执行器

`StreamingToolExecutor`（`src/services/tools/StreamingToolExecutor.ts`）是一个更高级的执行器，支持在模型**流式输出**过程中即时开始执行工具——不需要等待所有 tool_use block 完成解析。

#### 核心状态机

每个工具经历以下状态转换：

```
queued → executing → completed → yielded
```

```typescript
type ToolStatus = 'queued' | 'executing' | 'completed' | 'yielded'

type TrackedTool = {
  id: string
  block: ToolUseBlock
  status: ToolStatus
  isConcurrencySafe: boolean
  promise?: Promise<void>
  results?: Message[]
  pendingProgress: Message[]           // 进度消息立即传递
  contextModifiers?: Array<(context: ToolUseContext) => ToolUseContext>
}
```

#### 并发控制

```typescript
private canExecuteTool(isConcurrencySafe: boolean): boolean {
  const executingTools = this.tools.filter(t => t.status === 'executing')
  return (
    executingTools.length === 0 ||  // 没有正在执行的工具——可以开始
    (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe))
    // 自己和所有正在执行的都是并发安全的——可以加入
  )
}
```

规则：
- 如果没有工具在执行，任何工具都可以开始
- 如果有并发安全的工具在执行，只有并发安全的新工具才能加入
- 如果有非并发安全的工具在执行，所有新工具都必须等待

#### Bash 错误级联

StreamingToolExecutor 实现了精妙的错误处理——当 Bash 工具出错时，取消所有并发的兄弟工具：

```typescript
// Bash 错误级联——只有 Bash 错误会取消兄弟工具
if (isErrorResult && tool.block.name === BASH_TOOL_NAME) {
  this.hasErrored = true
  this.erroredToolDescription = this.getToolDescription(tool)
  // 通过 siblingAbortController 中止所有兄弟子进程
  this.siblingAbortController.abort('sibling_error')
}
```

**为什么只有 Bash 错误级联？** Bash 命令通常有隐式依赖链（`mkdir` 失败后续命令无意义），而 Read、WebFetch 等工具是独立的，一个失败不应影响其他。

#### 进度消息的特殊处理

进度消息不经过结果缓冲，而是立即传递给 UI：

```typescript
if (update.message.type === 'progress') {
  tool.pendingProgress.push(update.message)
  // 唤醒等待中的消费者
  if (this.progressAvailableResolve) {
    this.progressAvailableResolve()
    this.progressAvailableResolve = undefined
  }
}
```

消费端通过 `Promise.race` 同时等待工具完成和进度可用：

```typescript
async *getRemainingResults(): AsyncGenerator<MessageUpdate, void> {
  while (this.hasUnfinishedTools()) {
    // 先 yield 已完成的结果和进度
    for (const result of this.getCompletedResults()) { yield result }

    // 等待任何工具完成 OR 进度可用
    const progressPromise = new Promise<void>(resolve => {
      this.progressAvailableResolve = resolve
    })
    await Promise.race([...executingPromises, progressPromise])
  }
}
```

### 6.3 toolExecution.ts — 单工具执行流程

`runToolUse()` 是单个工具从接收到完成的完整流程：

```typescript
// src/services/tools/toolExecution.ts (简化)
export async function* runToolUse(
  toolUse: ToolUseBlock,
  assistantMessage: AssistantMessage,
  canUseTool: CanUseToolFn,
  toolUseContext: ToolUseContext,
): AsyncGenerator<MessageUpdateLazy, void> {
  // 1. 查找工具定义
  let tool = findToolByName(toolUseContext.options.tools, toolName)
  if (!tool) {
    // 尝试通过别名查找（向后兼容已重命名的工具）
    const fallbackTool = findToolByName(getAllBaseTools(), toolName)
    if (fallbackTool?.aliases?.includes(toolName)) tool = fallbackTool
  }

  // 2. 工具不存在——返回错误
  if (!tool) {
    yield { message: createUserMessage({
      content: [{ type: 'tool_result', content: 'Error: No such tool available', is_error: true }],
    }) }
    return
  }

  // 3. 检查 abort 信号
  if (toolUseContext.abortController.signal.aborted) {
    yield { message: cancelMessage }
    return
  }

  // 4. 权限检查 + 执行
  yield* streamedCheckPermissionsAndCallTool(tool, toolUseID, input, ...)
}
```

`streamedCheckPermissionsAndCallTool` 内部使用 `Stream` 将进度事件和最终结果合并为单一的 async iterable。完整流程：

```
validateInput() → checkPermissions() → canUseTool() → Pre-hooks → call() → Post-hooks
     ↓                   ↓                  ↓             ↓          ↓
  错误提示           权限弹窗          UI 确认       Hook 拦截    执行工具
```

### 6.4 工具结果格式化与 API 回传

工具执行完成后，结果通过 `mapToolResultToToolResultBlockParam()` 转换为 API 可接受的格式：

```typescript
// 每个工具自定义结果映射
mapToolResultToToolResultBlockParam(content: Output, toolUseID: string): ToolResultBlockParam
```

对于大结果，`processToolResultBlock()` 和 `processPreMappedToolResultBlock()` 会检查结果大小，超过 `maxResultSizeChars` 阈值时将完整结果持久化到 `~/.claude/tool-results/` 目录，模型只收到预览：

```
[Tool result too large — full output saved to /path/to/result.txt (15234 bytes)]
<preview>
前 N 个字符的预览...
</preview>
```

---

## 7. ToolUseContext 详解

`ToolUseContext` 是贯穿整个工具执行管线的上下文对象，包含了工具运行所需的一切信息。定义在 `src/Tool.ts` 中。

### 7.1 核心选项

```typescript
options: {
  commands: Command[]           // 可用的 slash 命令列表
  debug: boolean                // 调试模式
  mainLoopModel: string         // 主循环使用的模型名称
  tools: Tools                  // 当前可用的工具列表
  verbose: boolean              // 详细输出模式
  thinkingConfig: ThinkingConfig // 思考配置（extended thinking）
  mcpClients: MCPServerConnection[] // MCP 服务器连接
  mcpResources: Record<string, ServerResource[]> // MCP 资源
  isNonInteractiveSession: boolean  // 是否为非交互式会话（SDK/print 模式）
  agentDefinitions: AgentDefinitionsResult // 可用的 agent 定义
  maxBudgetUsd?: number         // 最大预算限制
  customSystemPrompt?: string   // 自定义系统提示
  appendSystemPrompt?: string   // 追加系统提示
  refreshTools?: () => Tools    // 动态刷新工具列表（MCP 连接变化时）
}
```

### 7.2 生命周期控制

```typescript
abortController: AbortController   // 取消信号——用户按 ESC、超时等
messages: Message[]                 // 当前对话历史
```

`abortController` 是层级化的：主线程有顶层 controller，每个工具执行创建子 controller（通过 `createChildAbortController`）。子 controller 被中止不会影响父级，但父级中止会级联到所有子级。

### 7.3 状态管理

```typescript
readFileState: FileStateCache       // 文件读取状态缓存（内容+时间戳）
getAppState(): AppState             // 获取应用状态
setAppState(f: (prev) => AppState): void  // 更新应用状态
setAppStateForTasks?: (f) => void   // 特殊：子 agent 也能更新的根状态
```

`readFileState` 是一个 LRU 缓存，记录每个文件最近的读取内容和修改时间。FileEditTool 用它来检测并发修改——如果文件的当前修改时间与缓存不匹配，说明文件被外部修改，编辑会被拒绝。

`setAppState` 和 `setAppStateForTasks` 的区别很重要：对于 async 子 agent，`setAppState` 是 no-op（防止竞态），但 `setAppStateForTasks` 始终有效（用于后台任务注册等基础设施操作）。

### 7.4 UI 交互

```typescript
setToolJSX?: SetToolJSXFn          // 设置工具的自定义 JSX 渲染
addNotification?: (notif) => void  // 添加通知
appendSystemMessage?: (msg) => void // 追加系统消息到 UI
sendOSNotification?: (opts) => void // 发送 OS 级通知
setStreamMode?: (mode: SpinnerMode) => void // 设置进度 spinner 模式
```

### 7.5 进度追踪

```typescript
setInProgressToolUseIDs: (f: (prev: Set<string>) => Set<string>) => void
setHasInterruptibleToolInProgress?: (v: boolean) => void
setResponseLength: (f: (prev: number) => number) => void
```

`setInProgressToolUseIDs` 在工具开始执行时添加 ID，完成时移除。UI 层通过这个 Set 来显示当前正在运行的工具。

`setHasInterruptibleToolInProgress` 告诉 UI 是否有可中断的工具在运行——只有所有正在执行的工具都是 `interruptBehavior: 'cancel'` 时才为 true，此时用户按 ESC 可以取消。

### 7.6 Agent 相关

```typescript
agentId?: AgentId          // 子 agent 的 ID（主线程为 undefined）
agentType?: string         // 子 agent 的类型名称
queryTracking?: QueryChainTracking  // 查询链追踪（chainId + depth）
toolUseId?: string         // 当前工具调用的 ID
```

### 7.7 文件和内存追踪

```typescript
updateFileHistoryState: (updater) => void    // 更新文件编辑历史（undo 支持）
updateAttributionState: (updater) => void    // 更新 commit 归属追踪
nestedMemoryAttachmentTriggers?: Set<string> // CLAUDE.md 注入触发器
loadedNestedMemoryPaths?: Set<string>        // 已加载的 CLAUDE.md 路径（防重复）
dynamicSkillDirTriggers?: Set<string>        // 动态技能目录触发器
```

### 7.8 权限相关

```typescript
toolDecisions?: Map<string, {      // 工具决策缓存
  source: string
  decision: 'accept' | 'reject'
  timestamp: number
}>
requireCanUseTool?: boolean        // 强制调用 canUseTool（用于推测执行的路径重写）
localDenialTracking?: DenialTrackingState  // 本地拒绝追踪（子 agent 用）
requestPrompt?: (sourceName, toolInputSummary?) =>
  (request: PromptRequest) => Promise<PromptResponse>  // 交互式提示回调
```

### 7.9 大结果管理

```typescript
contentReplacementState?: ContentReplacementState  // 工具结果预算管理
fileReadingLimits?: { maxTokens?: number; maxSizeBytes?: number }  // 文件读取限制
globLimits?: { maxResults?: number }  // Glob 结果限制
```

`contentReplacementState` 管理全局的工具结果预算。当对话中的工具结果总量过大时，旧结果会被替换为摘要，保持 context 在合理范围内。

---

## 8. 设计模式总结

### 8.1 声明式工具定义

工具通过声明式接口定义行为特征（`isReadOnly`、`isConcurrencySafe`、`shouldDefer`），编排系统自动推导执行策略。工具本身不需要关心执行顺序或并发控制。

### 8.2 Fail-Closed 默认策略

所有安全相关的默认值都是保守的：
- 默认不并发安全 → 串行执行（安全但慢）
- 默认非只读 → 需要权限检查
- 默认 `checkPermissions` 返回 allow → 但这只跳过了工具级检查，通用权限系统仍然生效

只有工具显式声明了安全特性，系统才会解锁优化（并发执行、跳过权限等）。

### 8.3 分层权限模型

权限检查按层级递进：

```
validateInput()              — 输入格式和语义验证
   ↓
checkPermissions()           — 工具级权限（路径、域名等）
   ↓
canUseTool()                 — 通用权限系统（mode、rules、hooks）
   ↓
PreToolUse hooks             — 用户自定义的前置钩子
   ↓
call()                       — 实际执行
   ↓
PostToolUse hooks            — 用户自定义的后置钩子
```

每一层都可以拒绝执行，实现了**纵深防御**。

### 8.4 类型驱动的工厂模式

`buildTool()` 工厂函数配合 TypeScript 的泛型推断，实现了：
- 简化工具定义（省略通用方法）
- 类型安全（输入/输出类型在整个管线中传播）
- 集中管理默认行为

### 8.5 渲染与逻辑分离

每个工具目录通常包含：
- `*Tool.ts` — 逻辑定义（schema、call、permissions）
- `UI.tsx` — 渲染函数（React 组件）
- `prompt.ts` — 系统提示文本
- `constants.ts` — 常量定义

这种分离使得修改 UI 不影响逻辑，修改逻辑不影响 UI。

### 8.6 流式优先架构

整个工具系统围绕 `AsyncGenerator` 构建：
- `runToolUse()` 是 generator，逐步 yield 进度和结果
- `runTools()` 和 `runToolsConcurrently()` 是 generator
- `StreamingToolExecutor` 通过 `getRemainingResults()` 返回 async generator

这让 UI 可以在工具执行的同时实时更新，提供流畅的用户体验。

### 8.7 延迟加载与 Token 优化

通过 `shouldDefer` / `alwaysLoad` + `ToolSearchTool` 机制，工具系统在工具数量增长时保持 token 效率：
- 常用工具始终加载（模型第一轮就能使用）
- 不常用工具延迟加载（通过搜索发现后再使用）
- MCP 工具天然支持 `alwaysLoad` 标记（通过 `_meta['anthropic/alwaysLoad']`）

### 8.8 Prompt Cache 稳定性

工具排序策略（内置工具按名排序在前，MCP 工具按名排序在后）确保了 API 请求中工具定义的顺序稳定，最大化利用服务器端的 prompt cache，减少重复计算开销。

---

> 本篇详细剖析了 Claude Code 工具系统的完整架构——从接口设计到工具注册，从权限检查到并发编排，从流式执行到结果回传。工具系统是 Claude Code 将 AI 能力映射到真实操作的核心桥梁，其设计体现了**安全优先**（fail-closed 默认值、多层权限）、**性能优化**（并发调度、延迟加载、流式执行）和**可扩展性**（统一接口、MCP 桥接）的工程哲学。
>
> 下一篇将深入探讨权限与安全系统的细节实现。
