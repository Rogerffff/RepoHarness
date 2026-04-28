# Claude Code 源码深度教学 -- 第 1 篇：架构总览与核心设计哲学

## 1. 概述

Claude Code 是 Anthropic 官方发布的 CLI 编程助手，允许用户在终端中与 Claude 模型进行多轮对话、执行代码编辑、运行命令、搜索代码库等操作。它不是一个简单的 API 封装，而是一个拥有 **1884 个源文件、512K 行代码** 的大型 TypeScript 工程，包含：

- **交互式终端 UI**：基于 React + Ink 的富文本终端界面
- **Agentic 工具系统**：30+ 内置工具，支持 MCP 协议扩展
- **多层权限模型**：从默认询问到完全绕过的 6 种权限模式
- **流式对话引擎**：基于 async generator 的对话循环，支持流式工具执行
- **插件与技能体系**：可扩展的插件系统和技能发现机制
- **多种运行模式**：交互式 REPL、无头模式（`-p`/`--print`）、Agent SDK、远程会话、SSH 等

## 2. 整体架构图

```
                         +-----------------------+
                         |   CLI 入口 (cli.tsx)   |
                         |  快速路径分发 + 子命令  |
                         +-----------+-----------+
                                     |
                         +-----------v-----------+
                         |  主编排器 (main.tsx)    |
                         |  Commander 解析 + 初始化 |
                         +-----------+-----------+
                                     |
                    +----------------+----------------+
                    |                                  |
          +---------v---------+             +----------v----------+
          | 交互模式 (REPL)    |             | 无头模式 (print.ts)  |
          | React/Ink 终端 UI  |             | 纯流式输出           |
          +---------+---------+             +----------+----------+
                    |                                  |
                    +----------------+----------------+
                                     |
                         +-----------v-----------+
                         |   对话循环 (query.ts)   |
                         |  async generator 驱动   |
                         +-----------+-----------+
                                     |
                    +----------------+----------------+
                    |                                  |
          +---------v---------+             +----------v----------+
          | API 调用层          |             | 工具编排层            |
          | (claude.ts)        |             | (toolOrchestration) |
          | 流式 SSE 消息       |             | 并发/串行执行         |
          +---------+---------+             +----------+----------+
                    |                                  |
                    |                     +------------+------------+
                    |                     |            |             |
                    |               +-----v----+ +----v-----+ +----v-----+
                    |               | BashTool | | EditTool | | MCP Tool |
                    |               +----------+ +----------+ +----------+
                    |
          +---------v---------+
          |  Anthropic API     |
          |  (Messages Beta)   |
          +--------------------+

  横切关注点:
  ┌─────────────────────────────────────────────────────┐
  │  bootstrap/state.ts  -- 全局单例状态                  │
  │  context.ts          -- 系统上下文 (git, CLAUDE.md)   │
  │  permissions/         -- 多层权限检查                  │
  │  services/analytics/  -- 遥测与分析                    │
  │  utils/hooks/         -- 生命周期钩子                  │
  │  state/store.ts       -- 响应式状态管理                │
  └─────────────────────────────────────────────────────┘
```

## 3. 核心设计哲学

### 3.1 流式异步生成器驱动对话循环

Claude Code 的对话核心是 `query()` 函数（`src/query.ts`），它是一个 **async generator**，通过 `yield` 逐条向上层产出消息事件，形成从 API 到 UI 的单向流式数据管道。

```typescript
// src/query.ts -- 对话循环的核心签名
export async function* query(
  params: QueryParams,
): AsyncGenerator<
  | StreamEvent        // 流式事件（API 开始/结束等）
  | RequestStartEvent  // 请求开始标记
  | Message            // 助手消息、用户消息、工具结果
  | TombstoneMessage   // 废弃消息标记（fallback 时清理）
  | ToolUseSummaryMessage,
  Terminal             // 返回值：终止原因
> {
  // ...
  const terminal = yield* queryLoop(params, consumedCommandUuids)
  return terminal
}
```

`queryLoop` 内部是一个 `while (true)` 无限循环，每次迭代：

1. 对消息序列执行 **snip/microcompact/autocompact** 压缩
2. 调用 `deps.callModel()` 发起流式 API 请求
3. 通过 `for await` 迭代流式响应，逐消息 `yield`
4. 收集 `tool_use` 块，交由工具编排层执行
5. 将工具结果追加到消息列表，进入下一轮循环
6. 当模型无 `tool_use` 输出时，循环终止

这种设计的优势在于：**消费者（UI 或 SDK）只需 `for await` 迭代 generator，无需关心内部的多轮工具调用和错误恢复逻辑。**

### 3.2 多层权限模型保障安全

权限系统是 Claude Code 最重要的安全机制之一，定义在 `src/utils/permissions/` 目录下。系统支持 6 种权限模式：

| 模式 | 含义 | 典型场景 |
|------|------|---------|
| `default` | 每次工具调用都询问用户 | 首次使用 |
| `plan` | 只读模式，禁止写操作 | 代码审查 |
| `acceptEdits` | 自动接受文件编辑 | 信任的开发流程 |
| `auto` | AI 分类器自动判断是否安全 | 高级用户 |
| `bypassPermissions` | 绕过所有权限检查 | CI/CD 环境 |
| `dontAsk` | 静默拒绝不安全操作 | 无头模式 |

权限检查的核心流程（简化）：

```
工具调用请求
  │
  ├─> 1. 检查 alwaysDeny 规则 ──匹配──> 拒绝
  │
  ├─> 2. 检查 alwaysAllow 规则 ──匹配──> 放行
  │
  ├─> 3. 根据 PermissionMode 判断
  │     ├─ plan: 只读工具放行，写工具拒绝
  │     ├─ auto: 调用分类器判断
  │     ├─ bypassPermissions: 放行
  │     └─ default: 弹出 UI 询问用户
  │
  └─> 4. 执行 PreToolUse/PostToolUse 钩子
```

每个工具自身还声明了安全属性（`src/Tool.ts`）：

```typescript
// src/Tool.ts -- 工具安全属性声明
export type Tool<Input, Output, P> = {
  isReadOnly(input: z.infer<Input>): boolean       // 是否只读
  isDestructive?(input: z.infer<Input>): boolean    // 是否不可逆（删除/覆盖）
  isConcurrencySafe(input: z.infer<Input>): boolean // 是否可并发执行
  validateInput?(input, context): Promise<ValidationResult> // 输入校验
  // ...
}
```

### 3.3 插件化工具系统

工具系统的设计遵循 **注册-发现-调度** 三段式：

**注册**（`src/tools.ts`）：`getAllBaseTools()` 返回所有内置工具的静态列表，每个工具是实现了 `Tool` 接口的对象。

```typescript
// src/tools.ts -- 工具注册表（摘录）
export function getAllBaseTools(): Tools {
  return [
    AgentTool,      // 子代理工具
    BashTool,       // Shell 命令执行
    FileReadTool,   // 文件读取
    FileEditTool,   // 文件编辑
    FileWriteTool,  // 文件写入
    GlobTool,       // 文件搜索
    GrepTool,       // 内容搜索
    WebFetchTool,   // HTTP 请求
    WebSearchTool,  // 网页搜索
    SkillTool,      // 技能调用
    // ... 30+ 工具
  ]
}
```

**发现**：工具列表会经过三层过滤：
1. `filterToolsByDenyRules` -- 移除被权限规则禁止的工具
2. `isEnabled()` 检查 -- 各工具根据运行环境自行判断是否可用
3. MCP 工具合并 -- `assembleToolPool()` 将内置工具和 MCP 协议工具合并去重

**调度**（`src/services/tools/toolOrchestration.ts`）：工具调用支持智能并发。只读工具（如 Grep、FileRead）可并发执行，写工具串行执行：

```typescript
// src/services/tools/toolOrchestration.ts -- 工具编排
export async function* runTools(toolUseMessages, assistantMessages, canUseTool, toolUseContext) {
  for (const { isConcurrencySafe, blocks } of partitionToolCalls(toolUseMessages, toolUseContext)) {
    if (isConcurrencySafe) {
      // 只读工具并发执行，最大并发数默认 10
      for await (const update of runToolsConcurrently(blocks, ...)) { yield update }
    } else {
      // 写工具串行执行
      for await (const update of runToolsSerially(blocks, ...)) { yield update }
    }
  }
}
```

### 3.4 React 终端 UI

Claude Code 使用 **React + Ink** 构建终端 UI，这是一个将 React 组件模型映射到终端输出的框架。核心渲染入口在 `src/ink.ts`：

```typescript
// src/ink.ts -- 终端渲染入口
export async function createRoot(options?: RenderOptions): Promise<Root> {
  const root = await inkCreateRoot(options)
  return {
    ...root,
    render: node => root.render(withTheme(node)), // 自动注入主题
  }
}
```

REPL 界面是一个标准 React 组件树（`src/screens/REPL.tsx`），使用 React hooks 管理状态：

```
App (src/components/App.tsx)
 └── REPL (src/screens/REPL.tsx)
      ├── PromptInput          -- 用户输入框
      ├── VirtualMessageList   -- 虚拟滚动消息列表
      ├── Spinner              -- 加载动画
      ├── PermissionRequest    -- 权限确认对话框
      ├── CostThresholdDialog  -- 费用阈值提醒
      └── MessageSelector      -- 消息选择器（编辑/重试）
```

## 4. 技术栈概览

| 层级 | 技术 | 说明 |
|------|------|------|
| 运行时 | Bun | 打包与运行，提供 `feature()` 编译时 Feature Gate |
| 语言 | TypeScript (strict) | 全量类型检查 |
| UI 框架 | React 19 + Ink | 终端组件化渲染 |
| CLI 框架 | Commander.js | 命令行参数解析 |
| API SDK | @anthropic-ai/sdk | Claude Messages API (Beta) |
| Schema 校验 | Zod v4 | 工具输入/输出 schema |
| 状态管理 | 自研 Store（发布-订阅） | 轻量级响应式状态 |
| 遥测 | OpenTelemetry | 指标/日志/追踪（延迟加载） |
| 扩展协议 | MCP (Model Context Protocol) | 第三方工具集成 |
| A/B 测试 | GrowthBook | Feature flag 与实验 |

## 5. 模块依赖关系详解

源码根目录下的核心模块及其职责：

```
src/
├── entrypoints/        # 入口点：cli.tsx(CLI), init.ts(初始化), agentSdkTypes.ts(SDK 类型)
├── bootstrap/          # 启动态：state.ts(全局可变单例状态)
├── main.tsx            # 主编排器：Commander 命令定义、参数解析、模式分发
├── query.ts            # 对话引擎：async generator 驱动的多轮循环
├── query/              # 对话子模块：config, deps, tokenBudget, stopHooks
├── Tool.ts             # 工具类型定义：Tool 接口、ToolUseContext、权限类型
├── tools.ts            # 工具注册表：getAllBaseTools(), getTools(), assembleToolPool()
├── tools/              # 30+ 具体工具实现，每个工具一个目录
├── context.ts          # 上下文构建：git 状态、CLAUDE.md 内容、系统日期
├── commands.ts         # 斜杠命令注册（/help, /clear, /compact 等）
├── commands/           # 具体命令实现
├── screens/            # UI 屏幕：REPL.tsx 是主屏幕
├── components/         # UI 组件：PromptInput, Spinner, PermissionRequest 等
├── ink/                # Ink 定制层：终端渲染、虚拟滚动、键绑定
├── hooks/              # React hooks：useCanUseTool, useLogMessages 等
├── state/              # 状态管理：store.ts(发布-订阅), AppState 定义
├── services/
│   ├── api/            # API 调用层：claude.ts(模型调用), withRetry(重试)
│   ├── compact/        # 上下文压缩：autoCompact, reactiveCompact, snipCompact
│   ├── mcp/            # MCP 客户端：配置解析、工具发现、资源管理
│   ├── analytics/      # 分析：GrowthBook, firstPartyEventLogger
│   ├── tools/          # 工具运行时：toolOrchestration(编排), toolExecution(执行)
│   └── lsp/            # LSP 集成
├── plugins/            # 插件系统
├── skills/             # 技能系统
├── utils/
│   ├── permissions/    # 权限模型核心
│   ├── model/          # 模型选择、能力检测
│   ├── settings/       # 多层配置系统 (MDM, remote, local, project)
│   ├── hooks/          # 生命周期钩子 (PreToolUse, PostToolUse, SessionStart)
│   └── ...             # 100+ 工具函数模块
├── types/              # 全局类型定义：message.ts, permissions.ts, hooks.ts
├── constants/          # 常量与提示词：prompts.ts, tools.ts
└── migrations/         # 配置迁移脚本
```

关键依赖方向（不可反向引用）：

```
entrypoints/cli.tsx ──> main.tsx ──> query.ts ──> services/api/claude.ts
                                       │
                                       └──> services/tools/toolOrchestration.ts ──> Tool.ts
                                                                                      │
bootstrap/state.ts <── 所有模块（全局单例，叶节点）                                       │
                                                                                      v
                                                                              tools/*Tool.ts
```

## 6. Feature Gate 与条件编译机制

Claude Code 使用 Bun 的 `feature()` 函数实现**编译时死代码消除**（Dead Code Elimination）。这是一个极其重要的架构设计，使同一份源码可以产出功能不同的构建产物。

```typescript
// bun:bundle 提供的编译时函数
import { feature } from 'bun:bundle'

// 编译时求值：external 构建中 feature('COORDINATOR_MODE') === false
// 整个 require() 及其依赖模块在打包时被完全移除
const coordinatorModeModule = feature('COORDINATOR_MODE')
  ? require('./coordinator/coordinatorMode.js')
  : null
```

**关键约束**：`feature()` 必须出现在 `if`/三元表达式的条件位置，Bun 才能识别并做 DCE。以下是源码中常见的 feature gate：

| Feature Flag | 功能 | 目标构建 |
|-------------|------|---------|
| `COORDINATOR_MODE` | 多代理协调器 | 内部构建 |
| `KAIROS` | 助手模式 (长期运行) | 内部构建 |
| `BRIDGE_MODE` | 远程控制桥接 | 内部构建 |
| `BG_SESSIONS` | 后台会话管理 | 内部构建 |
| `DAEMON` | 守护进程模式 | 内部构建 |
| `SSH_REMOTE` | SSH 远程执行 | 内部构建 |
| `REACTIVE_COMPACT` | 响应式上下文压缩 | 渐进发布 |
| `CONTEXT_COLLAPSE` | 上下文折叠 | 渐进发布 |
| `TRANSCRIPT_CLASSIFIER` | 自动模式分类器 | 渐进发布 |
| `HISTORY_SNIP` | 历史消息裁剪 | 渐进发布 |

除了 `feature()` 编译时门控，还有两种运行时门控：

1. **`process.env.USER_TYPE`** -- 区分内部用户（`ant`）和外部用户（`external`），用于条件加载内部专用工具（如 `REPLTool`, `TungstenTool`）
2. **GrowthBook Feature Flags** -- 运行时 A/B 测试和渐进发布，通过 `getFeatureValue_CACHED_MAY_BE_STALE()` 读取

## 7. 从用户输入到模型响应的完整数据流

以用户在交互模式下输入一条消息为例，完整的数据流经过以下 10 步：

### 第 1 步：终端输入捕获

用户在 `PromptInput` 组件中输入文本并按 Enter。`REPL.tsx` 中的事件处理器接收输入，创建 `UserMessage`。

```
[键盘事件] → PromptInput (React 组件) → REPL.onSubmit()
```

### 第 2 步：上下文构建

REPL 准备对话所需的上下文：
- **系统提示词**：从 `src/constants/prompts.ts` 获取，包含工具使用规则
- **用户上下文**（`context.ts` 的 `getUserContext()`）：CLAUDE.md 内存文件内容、当前日期
- **系统上下文**（`context.ts` 的 `getSystemContext()`）：git 状态（分支、diff、最近提交）

### 第 3 步：消息队列与历史管理

用户消息被追加到消息列表 `messages[]`。如果有排队的斜杠命令（如 `/compact`），会优先处理。

### 第 4 步：进入对话循环

REPL 调用 `query()` 函数（`src/query.ts`），传入完整参数：

```typescript
// 简化的调用
for await (const event of query({
  messages,
  systemPrompt,
  userContext,
  systemContext,
  canUseTool,        // 权限检查回调
  toolUseContext,     // 工具执行上下文
  querySource: 'repl_main_thread',
})) {
  // 处理每个产出的事件...
}
```

### 第 5 步：上下文压缩（按需）

在发送 API 请求前，`queryLoop` 会执行多级上下文压缩：

1. **Snip Compact** -- 裁剪历史中的冗长工具结果
2. **Microcompact** -- 缓存感知的微压缩
3. **Context Collapse** -- 折叠已读区域
4. **Auto Compact** -- 当 token 数接近窗口限制时，调用模型生成摘要

### 第 6 步：API 请求构建与发送

`deps.callModel()`（实际调用 `src/services/api/claude.ts`）负责：
- 将消息序列标准化为 API 格式（`normalizeMessagesForAPI`）
- 注入用户上下文到首条用户消息（`prependUserContext`）
- 构建工具 schema（`toolToAPISchema`）
- 通过 Anthropic SDK 发起流式请求

### 第 7 步：流式响应接收

API 返回 SSE 流，`claude.ts` 将其转化为 `AsyncGenerator<Message>`，产出 `AssistantMessage` 序列。`queryLoop` 内的 `for await` 逐消息接收，检查是否需要 withhold（延迟产出，等待错误恢复判断）。

### 第 8 步：工具调用执行

如果助手消息包含 `tool_use` 块，工具编排层介入：

```
tool_use 块列表
  │
  ├─> partitionToolCalls() -- 按并发安全性分组
  │
  ├─> 并发安全组 ──> runToolsConcurrently() ──> 最多 10 并发
  │
  └─> 非并发安全组 ──> runToolsSerially() ──> 逐个执行
        │
        └─> 每个工具: validateInput → canUseTool(权限) → tool.call() → 产出结果
```

工具结果作为 `UserMessage`（包含 `tool_result` 块）被追加到消息列表。

### 第 9 步：循环继续或终止

- 如果有工具调用结果，循环回到第 5 步（`continue`），带着新的消息列表再次调用 API
- 如果助手消息无 `tool_use`（纯文本回复），检查 stop hooks，然后 `return { reason: 'end_turn' }`
- 如果遇到 `max_output_tokens`，尝试恢复（最多 3 次）

### 第 10 步：UI 渲染更新

REPL 通过 `for await` 接收 `query()` 产出的每个事件，更新 React 状态，触发重渲染：
- `AssistantMessage` → 渲染 Markdown 文本
- `StreamEvent` → 更新 Spinner 状态
- `ProgressMessage` → 显示工具执行进度
- 工具 JSX → 在消息流中内嵌渲染（如权限确认对话框）

## 8. 关键设计模式总结

### 模式 1：Memoized Lazy Initialization

大量模块使用 `lodash/memoize` 实现惰性单次初始化，避免重复计算：

```typescript
// src/context.ts
export const getSystemContext = memoize(async () => {
  const gitStatus = await getGitStatus()
  return { ...(gitStatus && { gitStatus }) }
})
```

### 模式 2：响应式状态 Store

自研的微型状态管理（`src/state/store.ts`），35 行代码实现发布-订阅模式：

```typescript
// src/state/store.ts -- 完整实现
export function createStore<T>(initialState: T, onChange?: OnChange<T>): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()
  return {
    getState: () => state,
    setState: (updater) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return  // 引用相等则跳过
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
```

### 模式 3：延迟加载削减启动开销

OpenTelemetry (~400KB)、gRPC (~700KB) 等重型依赖通过 `import()` 动态加载，仅在实际需要时才引入：

```typescript
// src/entrypoints/init.ts -- 延迟加载遥测
async function setMeterState(): Promise<void> {
  // 延迟加载 ~400KB 的 OpenTelemetry + protobuf
  const { initializeTelemetry } = await import('../utils/telemetry/instrumentation.js')
  const meter = await initializeTelemetry()
  // ...
}
```

### 模式 4：全局可变单例 + 函数式访问器

`bootstrap/state.ts` 定义了一个大型 `State` 对象作为全局可变单例，通过导出的 getter/setter 函数访问。这个设计的注释中明确写道 "DO NOT ADD MORE STATE HERE"，体现了对全局状态扩散的克制：

```typescript
// src/bootstrap/state.ts（头部注释）
// DO NOT ADD MORE STATE HERE - BE JUDICIOUS WITH GLOBAL STATE
```

### 模式 5：编译时功能裁剪

通过 `feature()` 在构建时移除整个功能模块及其依赖树，使外部发布版本的体积和攻击面大幅减小。这是 Claude Code 支持内部/外部双轨发布的关键机制。

---

> **下一篇预告**：第 2 篇将深入分析 `query.ts` 对话循环的完整实现，包括自动压缩策略、token 预算管理、错误恢复机制和流式工具执行的并发模型。
