# 第 3 篇：对话循环与查询引擎

## 1. 概述：对话循环在 Claude Code 中的核心地位

Claude Code 的本质是一个**无限循环的 AI 代理**——用户提出指令，模型思考并调用工具，工具返回结果，模型继续思考……直到任务完成或被用户打断。这个循环就是整个系统的心脏。

从架构上看，对话循环横跨四层：

```
REPL.tsx (UI 入口层)
    ↓ handlePromptSubmit
QueryEngine.ts (SDK 桥接层)
    ↓ submitMessage
query.ts (核心循环层)
    ↓ deps.callModel
claude.ts (API 通信层)
    ↓ withRetry → Anthropic SDK
```

每一层各司其职：REPL 负责用户交互和 React 渲染；QueryEngine 负责会话状态管理和 SDK 兼容输出；query.ts 驱动工具调用与续接决策；claude.ts 封装流式 API 通信和错误恢复。

理解这四层的数据流和控制流，就理解了 Claude Code 95% 的运行时行为。

---

## 2. REPL.tsx 交互入口：Hook 驱动架构

### 2.1 文件概览

`src/screens/REPL.tsx` 是 Claude Code 的交互主屏幕，一个约 4000+ 行的 React/Ink 组件。它使用 React Compiler (`react/compiler-runtime`) 优化渲染，通过数十个自定义 Hook 管理各个方面：

```typescript
// src/screens/REPL.tsx 顶部的 Hook 导入体现了架构复杂度
import { useApiKeyVerification } from '../hooks/useApiKeyVerification.js'
import { useCanUseTool } from '../hooks/useCanUseTool.js'
import { useMainLoopModel } from '../hooks/useMainLoopModel.js'
import { useMergedTools } from '../hooks/useMergedTools.js'
import { useQueueProcessor } from '../hooks/useQueueProcessor.js'
import { useAssistantHistory } from '../hooks/useAssistantHistory.js'
// ... 还有数十个 Hook
```

REPL 从不直接调用 API。它只做两件事：收集用户输入，以及消费 `query()` 生成器的产出来更新 UI。

### 2.2 handlePromptSubmit 流程

当用户按下 Enter 键提交一条消息，入口是 `handlePromptSubmit`（定义在 `src/utils/handlePromptSubmit.ts`）：

```typescript
// src/utils/handlePromptSubmit.ts
export type HandlePromptSubmitParams = BaseExecutionParams & {
  input?: string
  mode?: PromptInputMode
  pastedContents?: Record<number, PastedContent>
  helpers: PromptInputHelpers
  onInputChange: (value: string) => void
  // ...
}
```

`handlePromptSubmit` 的核心工作：

1. **输入预处理**：展开粘贴引用 (`expandPastedTextRefs`)、解析引用 (`parseReferences`)
2. **模式路由**：判断输入是普通 prompt、slash 命令还是队列命令
3. **创建 AbortController**：每次提交创建新的中断控制器
4. **调用 `processUserInput`**：转换输入为 Message 数组，处理 slash 命令副作用
5. **启动查询**：通过 `onQuery` 回调触发 `query()` 异步生成器

这里有一个重要的设计决策——**所有查询都通过 `QueryGuard` 门控**。QueryGuard 确保同一时刻只有一个查询在运行，防止并发竞态：

```typescript
// 在 executeUserInput 中
if (!queryGuard.tryAcquire()) {
  // 查询正在运行，排队等待
  enqueue(queuedCommand)
  return
}
```

### 2.3 从 REPL 到 query() 的桥梁

REPL 通过 `for await` 消费 `query()` 生成器：

```typescript
// REPL.tsx 中的核心消费循环（简化）
for await (const message of query({
  messages,
  systemPrompt,
  userContext,
  systemContext,
  canUseTool,
  toolUseContext,
  querySource: getQuerySourceForREPL(),
})) {
  // handleMessageFromStream 处理每种消息类型
  handleMessageFromStream(message, {
    onAssistantMessage: (msg) => { /* 更新 UI */ },
    onToolResult: (msg) => { /* 显示工具执行结果 */ },
    onStreamEvent: (evt) => { /* 更新流式打字效果 */ },
    // ...
  })
}
```

消息通过流式 `yield` 从 query.ts 逐一传递，REPL 实时渲染——这就是用户看到 Claude "逐字打出" 回复的原因。

---

## 3. query() 异步生成器详解

### 3.1 为什么选择 async generator

`query()` 的签名是：

```typescript
// src/query.ts
export async function* query(
  params: QueryParams,
): AsyncGenerator<
  | StreamEvent        // API 流式事件（content_block_delta 等）
  | RequestStartEvent  // 每次 API 请求开始的标记
  | Message            // 完整的消息（assistant/user/system/attachment）
  | TombstoneMessage   // 墓碑消息（标记需要删除的消息）
  | ToolUseSummaryMessage, // 工具使用摘要
  Terminal             // 返回值：终止原因
>
```

选择 async generator 而非 callback 或 Observable 有三个核心理由：

1. **背压控制**：消费者（REPL/SDK）通过 `for await` 按需拉取，天然实现流控。如果 UI 渲染慢了，流自动暂停。
2. **协作式取消**：`yield` 点是自然的检查中断的位置。结合 AbortController，可以在任意 yield 处响应用户 ESC。
3. **状态机天然表达**：`while (true)` + `yield` + `continue`/`return` 清晰地表达了"循环中的多种退出/续接路径"，比传统回调嵌套可读性高得多。

### 3.2 QueryParams 输入参数

```typescript
// src/query.ts
export type QueryParams = {
  messages: Message[]              // 当前对话历史
  systemPrompt: SystemPrompt       // 系统提示词数组
  userContext: { [k: string]: string }   // 用户上下文（注入到首条 user 消息前）
  systemContext: { [k: string]: string } // 系统上下文（附加到 system prompt 后）
  canUseTool: CanUseToolFn         // 权限判定函数
  toolUseContext: ToolUseContext    // 工具执行上下文（包含 tools、abortController 等）
  fallbackModel?: string           // 后备模型（529 过载时降级）
  querySource: QuerySource         // 查询来源标识
  maxOutputTokensOverride?: number // 输出 token 上限覆盖
  maxTurns?: number                // 最大轮次限制
  skipCacheWrite?: boolean         // 跳过缓存写入
  taskBudget?: { total: number }   // API 侧 token 预算
  deps?: QueryDeps                 // 依赖注入（测试用）
}
```

`querySource` 是一个重要的标识符，它决定了重试策略、缓存行为和遥测分类：

- `'repl_main_thread'`：REPL 主线程查询
- `'sdk'`：SDK/headless 查询
- `'agent:custom'` / `'agent:default'`：子代理查询
- `'compact'`：自动压缩查询
- `'auto_mode'`：安全分类器查询

### 3.3 状态机设计

`queryLoop` 内部维护一个显式的 `State` 结构体：

```typescript
// src/query.ts 第 204 行
type State = {
  messages: Message[]                    // 当前消息数组
  toolUseContext: ToolUseContext          // 工具上下文（可能跨迭代更新）
  autoCompactTracking: AutoCompactTrackingState | undefined
                                          // 自动压缩的跟踪状态
  maxOutputTokensRecoveryCount: number   // max_output_tokens 恢复尝试次数
  hasAttemptedReactiveCompact: boolean   // 是否已尝试反应式压缩
  maxOutputTokensOverride: number | undefined  // 临时的输出上限覆盖
  pendingToolUseSummary: Promise<ToolUseSummaryMessage | null> | undefined
                                          // 上一轮的工具摘要（异步，与下次 API 调用并行）
  stopHookActive: boolean | undefined    // stop hook 是否激活
  turnCount: number                      // 当前轮次计数
  transition: Continue | undefined       // 上一次迭代为何 continue
}
```

这个设计的巧妙之处在于：**每个 `continue` 站点通过重新构造完整的 `State` 对象来"原子性地"更新状态**，而不是零散地修改多个变量：

```typescript
// src/query.ts 第 1715 行 - 工具调用后的续接
const next: State = {
  messages: [...messagesForQuery, ...assistantMessages, ...toolResults],
  toolUseContext: toolUseContextWithQueryTracking,
  autoCompactTracking: tracking,
  turnCount: nextTurnCount,
  maxOutputTokensRecoveryCount: 0,
  hasAttemptedReactiveCompact: false,
  pendingToolUseSummary: nextPendingToolUseSummary,
  maxOutputTokensOverride: undefined,
  stopHookActive,
  transition: { reason: 'next_turn' },
}
state = next
// while(true) 的下一轮迭代开始
```

`transition` 字段记录了为什么循环继续，它使得测试可以断言恢复路径是否触发，无需检查消息内容。所有可能的 transition 原因包括：

| transition.reason | 含义 |
|---|---|
| `'next_turn'` | 正常的工具调用续接 |
| `'max_output_tokens_recovery'` | 输出截断后的恢复 |
| `'max_output_tokens_escalate'` | 从 8K 升级到 64K |
| `'reactive_compact_retry'` | 反应式压缩后重试 |
| `'collapse_drain_retry'` | 上下文折叠后重试 |
| `'stop_hook_blocking'` | stop hook 返回阻塞错误 |
| `'token_budget_continuation'` | token 预算续接 |

### 3.4 事件流类型详解

`query()` 生成器 yield 的值有五种类型：

**StreamEvent**：API 流式事件的透传包装。允许 UI 层实时渲染打字效果：
```typescript
// 从 claude.ts yield，透传到 REPL
yield {
  type: 'stream_event',
  event: part,  // BetaRawMessageStreamEvent（来自 Anthropic SDK）
  ...(part.type === 'message_start' ? { ttftMs } : undefined),
}
```

**RequestStartEvent**：每轮 API 调用前发出的信号，让 UI 显示"思考中..."：
```typescript
yield { type: 'stream_request_start' }
```

**Message**：完整的消息对象，包括 `AssistantMessage`（模型回复）、`UserMessage`（工具结果、恢复消息）、`SystemMessage`（压缩边界、告警）、`AttachmentMessage`（附件）：
```typescript
// 工具结果作为 UserMessage yield
yield createUserMessage({
  content: [{ type: 'tool_result', content: result, tool_use_id: toolUse.id }],
  toolUseResult: result,
  sourceToolAssistantUUID: assistantMessage.uuid,
})
```

**TombstoneMessage**：模型后备触发时，标记需要从 UI 和 transcript 中删除的孤立消息：
```typescript
// 流式后备时清除孤立的 thinking blocks
for (const msg of assistantMessages) {
  yield { type: 'tombstone' as const, message: msg }
}
```

**ToolUseSummaryMessage**：异步生成的工具使用摘要（由 Haiku 模型生成），用于移动端 UI 显示简洁描述。

---

## 4. queryLoop 完整流程逐步解析

### 4.1 循环入口与初始化

```typescript
// src/query.ts 第 241 行
async function* queryLoop(params, consumedCommandUuids) {
  const { systemPrompt, userContext, systemContext, canUseTool, ... } = params
  const deps = params.deps ?? productionDeps()

  let state: State = {
    messages: params.messages,
    toolUseContext: params.toolUseContext,
    // ...初始值
    turnCount: 1,
    transition: undefined,
  }

  // 快照不可变配置
  const config = buildQueryConfig()

  // 启动记忆预取（异步，不阻塞）
  using pendingMemoryPrefetch = startRelevantMemoryPrefetch(
    state.messages,
    state.toolUseContext,
  )

  while (true) {
    // 每轮迭代从 state 解构
    let { toolUseContext } = state
    const { messages, turnCount, ... } = state
    // ...
  }
}
```

注意 `using` 关键字——这是 TC39 的 Explicit Resource Management 提案。`pendingMemoryPrefetch` 在生成器退出时（无论正常返回、抛出错误还是被 `.return()` 关闭）自动调用 `[Symbol.dispose]()` 做清理和遥测。

### 4.2 消息预处理管线

每轮迭代开始时，消息经历一系列预处理：

```
原始 messages
    ↓ getMessagesAfterCompactBoundary()  // 取压缩边界后的消息
    ↓ applyToolResultBudget()            // 裁剪超大工具结果
    ↓ snipCompactIfNeeded()              // 历史裁剪（feature gate）
    ↓ microcompactMessages()             // 微压缩（删除旧的详细工具输出）
    ↓ applyCollapsesIfNeeded()           // 上下文折叠（feature gate）
    ↓ autoCompactIfNeeded()              // 自动压缩（当 token 数接近上限）
    ↓ messagesForQuery                   // 最终送入 API 的消息
```

这个管线的设计原则是**渐进式瘦身**：每个阶段只在需要时触发，尽量保留更多上下文细节。

**自动压缩**是最重要的阶段。当 token 数接近模型上下文窗口时，它会调用一个独立的 API 请求来总结历史对话：

```typescript
// src/query.ts 第 454 行
const { compactionResult, consecutiveFailures } = await deps.autocompact(
  messagesForQuery,
  toolUseContext,
  {
    systemPrompt,
    userContext,
    systemContext,
    toolUseContext,
    forkContextMessages: messagesForQuery,
  },
  querySource,
  tracking,
  snipTokensFreed,
)

if (compactionResult) {
  // 压缩成功：用压缩后的消息替换
  const postCompactMessages = buildPostCompactMessages(compactionResult)
  for (const message of postCompactMessages) {
    yield message  // 通知 UI 更新
  }
  messagesForQuery = postCompactMessages
}
```

### 4.3 系统提示构建

系统提示由多个来源组合：

```typescript
// src/query.ts 第 449 行
const fullSystemPrompt = asSystemPrompt(
  appendSystemContext(systemPrompt, systemContext),
)
```

在 claude.ts 层面，系统提示被进一步增强：

```typescript
// src/services/api/claude.ts 第 1358 行
systemPrompt = asSystemPrompt(
  [
    getAttributionHeader(fingerprint),     // 归属标头（fingerprint）
    getCLISyspromptPrefix({                // CLI 系统提示前缀
      isNonInteractive: options.isNonInteractiveSession,
      hasAppendSystemPrompt: options.hasAppendSystemPrompt,
    }),
    ...systemPrompt,                       // 用户/默认系统提示
    ...(advisorModel ? [ADVISOR_TOOL_INSTRUCTIONS] : []),  // Advisor 指令
    ...(injectChromeHere ? [CHROME_TOOL_SEARCH_INSTRUCTIONS] : []),
  ].filter(Boolean),
)
```

### 4.4 API 调用触发

准备就绪后，通过依赖注入的 `deps.callModel` 发起流式调用：

```typescript
// src/query.ts 第 659 行
for await (const message of deps.callModel({
  messages: prependUserContext(messagesForQuery, userContext),
  systemPrompt: fullSystemPrompt,
  thinkingConfig: toolUseContext.options.thinkingConfig,
  tools: toolUseContext.options.tools,
  signal: toolUseContext.abortController.signal,
  options: {
    model: currentModel,
    toolChoice: undefined,        // 不强制工具选择
    querySource,
    fallbackModel,
    maxOutputTokensOverride,
    // ... 大量配置
  },
})) {
  // 流式处理每个消息
}
```

`prependUserContext` 将 git status、CLAUDE.md 内容等用户上下文注入到第一条 user 消息前面。

### 4.5 流式响应处理

claude.ts 的 `queryModel` 函数处理 Anthropic API 的 Server-Sent Events 流。每个流式事件按类型分发：

#### message_start

```typescript
// src/services/api/claude.ts 第 1980 行
case 'message_start': {
  partialMessage = part.message    // 缓存部分消息（usage、model 等元数据）
  ttftMs = Date.now() - start      // 记录首 token 延迟（TTFB）
  usage = updateUsage(usage, part.message?.usage)
  break
}
```

`message_start` 是流的第一个事件，包含初始 usage（input_tokens 等）但 output_tokens 为 0。

#### content_block_start

```typescript
// src/services/api/claude.ts 第 1996 行
case 'content_block_start':
  switch (part.content_block.type) {
    case 'tool_use':
      // 初始化工具调用块，input 设为空字符串待累积
      contentBlocks[part.index] = {
        ...part.content_block,
        input: '',  // JSON 字符串，后续通过 input_json_delta 累积
      }
      break
    case 'text':
      contentBlocks[part.index] = {
        ...part.content_block,
        text: '',   // 文本内容，后续通过 text_delta 累积
      }
      break
    case 'thinking':
      contentBlocks[part.index] = {
        ...part.content_block,
        thinking: '',    // 思考内容
        signature: '',   // 思考签名（用于验证完整性）
      }
      break
    // server_tool_use、redacted_thinking 等类似处理
  }
  break
```

每种内容块类型初始化时将累积字段设为空字符串。注释中提到一个 SDK 的 bug：SDK 有时在 `content_block_start` 中包含文本，又在 `content_block_delta` 中重复，因此这里忽略 start 中的文本。

#### content_block_delta

```typescript
// src/services/api/claude.ts 第 2053 行
case 'content_block_delta': {
  const contentBlock = contentBlocks[part.index]
  switch (delta.type) {
    case 'input_json_delta':
      // 工具调用的 JSON 输入逐块累积
      contentBlock.input += delta.partial_json
      break
    case 'text_delta':
      // 文本逐块累积
      contentBlock.text += delta.text
      break
    case 'thinking_delta':
      // 思考内容逐块累积
      contentBlock.thinking += delta.thinking
      break
    case 'signature_delta':
      // 签名一次性设置
      contentBlock.signature = delta.signature
      break
  }
  break
}
```

Delta 是最频繁的事件类型。Claude Code 选择原始的 `Stream` 而不是 SDK 的 `BetaMessageStream`，以避免 SDK 在每个 `input_json_delta` 上做 O(n^2) 的 partial JSON 解析。

#### content_block_stop

```typescript
// src/services/api/claude.ts 第 2171 行
case 'content_block_stop': {
  const contentBlock = contentBlocks[part.index]
  // 将累积的内容块包装为完整的 AssistantMessage
  const m: AssistantMessage = {
    message: {
      ...partialMessage,
      content: normalizeContentFromAPI(
        [contentBlock] as BetaContentBlock[],
        tools,
        options.agentId,
      ),
    },
    requestId: streamRequestId ?? undefined,
    type: 'assistant',
    uuid: randomUUID(),
    timestamp: new Date().toISOString(),
  }
  newMessages.push(m)
  yield m  // 立即 yield 给 query.ts
  break
}
```

**关键设计**：每个 content block 完成时立即 yield 一个 `AssistantMessage`。这意味着一次 API 响应可能 yield 多条 AssistantMessage（一条文本 + 一条工具调用）。query.ts 收集所有这些到 `assistantMessages` 数组。

#### message_delta

```typescript
// src/services/api/claude.ts 第 2213 行
case 'message_delta': {
  usage = updateUsage(usage, part.usage)
  stopReason = part.delta.stop_reason

  // 直接变异最后一条消息的 usage 和 stop_reason
  // 重要：使用直接属性修改，不用对象替换
  // 因为 transcript 写入队列持有 message.message 的引用
  const lastMsg = newMessages.at(-1)
  if (lastMsg) {
    lastMsg.message.usage = usage
    lastMsg.message.stop_reason = stopReason
  }

  // 计算并累加费用
  const costUSDForPart = calculateUSDCost(resolvedModel, usage)
  costUSD += addToTotalSessionCost(costUSDForPart, usage, options.model)

  // 处理各种停止原因
  if (stopReason === 'max_tokens') {
    yield createAssistantAPIErrorMessage({
      content: `...exceeded the ${maxOutputTokens} output token maximum...`,
      apiError: 'max_output_tokens',
    })
  }

  if (stopReason === 'model_context_window_exceeded') {
    yield createAssistantAPIErrorMessage({
      content: '...context window limit...',
      apiError: 'max_output_tokens',  // 复用 max_output_tokens 恢复路径
    })
  }
  break
}
```

注意 `message_delta` 中的直接属性变异（mutation）——这是有意为之的。transcript 写入是异步的（100ms flush interval），如果使用对象展开 `{ ...lastMsg.message, usage }` 创建新对象，写入队列持有的旧引用就会丢失最终值。

### 4.6 工具调用检测与分发

回到 query.ts，流式循环消费完毕后：

```typescript
// src/query.ts 第 826 行
if (message.type === 'assistant') {
  assistantMessages.push(message)

  // 检测是否包含工具调用
  const msgToolUseBlocks = message.message.content.filter(
    content => content.type === 'tool_use',
  ) as ToolUseBlock[]

  if (msgToolUseBlocks.length > 0) {
    toolUseBlocks.push(...msgToolUseBlocks)
    needsFollowUp = true  // 标记需要续接
  }

  // 流式工具执行：在流式过程中就开始执行工具
  if (streamingToolExecutor && !toolUseContext.abortController.signal.aborted) {
    for (const toolBlock of msgToolUseBlocks) {
      streamingToolExecutor.addTool(toolBlock, message)
    }
  }
}
```

**流式工具执行** (`StreamingToolExecutor`) 是一个性能优化：当模型输出包含多个 tool_use 块时，第一个块的工具可以在模型还在输出第二个块时就开始执行。这极大降低了多工具调用场景的端到端延迟。

流式循环结束后，收集所有工具结果：

```typescript
// src/query.ts 第 1380 行
const toolUpdates = streamingToolExecutor
  ? streamingToolExecutor.getRemainingResults()   // 获取剩余结果
  : runTools(toolUseBlocks, assistantMessages, canUseTool, toolUseContext)
                                                   // 或传统的串行执行

for await (const update of toolUpdates) {
  if (update.message) {
    yield update.message       // yield 工具结果给 UI
    toolResults.push(...)      // 收集用于下一轮
  }
  if (update.newContext) {
    updatedToolUseContext = { ...update.newContext, queryTracking }
  }
}
```

### 4.7 续接决策逻辑

工具执行完毕后，query.ts 根据多个条件决定是继续循环还是退出：

#### 路径 1: needsFollowUp = false（无工具调用 → 可能完成）

```
模型没有调用工具 → 检查是否有错误
                → 检查 stop hooks
                → 检查 token budget
                → return { reason: 'completed' }
```

在这个路径中，需要处理多种特殊情况：

**prompt-too-long 恢复**：如果 API 返回 413（提示太长），先尝试 context collapse drain，再尝试 reactive compact：

```typescript
// src/query.ts 第 1085 行
if (isWithheld413) {
  // 第一步：排空上下文折叠队列
  if (feature('CONTEXT_COLLAPSE') && contextCollapse) {
    const drained = contextCollapse.recoverFromOverflow(messagesForQuery, querySource)
    if (drained.committed > 0) {
      state = { ...state, transition: { reason: 'collapse_drain_retry' } }
      continue  // 重试
    }
  }
}

// 第二步：反应式压缩
if (isWithheld413 && reactiveCompact) {
  const compacted = await reactiveCompact.tryReactiveCompact({ ... })
  if (compacted) {
    state = { ...state, transition: { reason: 'reactive_compact_retry' } }
    continue
  }
  // 无法恢复 → yield 错误并退出
  yield lastMessage
  return { reason: 'prompt_too_long' }
}
```

**max_output_tokens 恢复**：两阶段策略

```typescript
// 阶段 1：从默认 8K 升级到 64K（一次性）
if (capEnabled && maxOutputTokensOverride === undefined) {
  state = { ...state,
    maxOutputTokensOverride: ESCALATED_MAX_TOKENS, // 64K
    transition: { reason: 'max_output_tokens_escalate' },
  }
  continue
}

// 阶段 2：多轮恢复（最多 3 次）
if (maxOutputTokensRecoveryCount < MAX_OUTPUT_TOKENS_RECOVERY_LIMIT) {
  const recoveryMessage = createUserMessage({
    content: 'Output token limit hit. Resume directly — no apology, no recap...',
    isMeta: true,
  })
  state = { ...state,
    messages: [...messagesForQuery, ...assistantMessages, recoveryMessage],
    maxOutputTokensRecoveryCount: maxOutputTokensRecoveryCount + 1,
    transition: { reason: 'max_output_tokens_recovery' },
  }
  continue
}
```

**Stop hooks**：模型完成后执行 hook（在 `src/query/stopHooks.ts`），hook 可以返回阻塞错误或阻止续接：

```typescript
const stopHookResult = yield* handleStopHooks(
  messagesForQuery, assistantMessages,
  systemPrompt, userContext, systemContext,
  toolUseContext, querySource, stopHookActive,
)

if (stopHookResult.preventContinuation) {
  return { reason: 'stop_hook_prevented' }
}

if (stopHookResult.blockingErrors.length > 0) {
  state = { ...state,
    messages: [...messagesForQuery, ...assistantMessages, ...stopHookResult.blockingErrors],
    transition: { reason: 'stop_hook_blocking' },
  }
  continue
}
```

**Token budget**：当启用了 token 预算（500K+ 自动续接），检查是否应该继续：

```typescript
if (feature('TOKEN_BUDGET')) {
  const decision = checkTokenBudget(
    budgetTracker!, toolUseContext.agentId,
    getCurrentTurnTokenBudget(), getTurnOutputTokens(),
  )
  if (decision.action === 'continue') {
    // 注入续接消息
    state = { ...state,
      messages: [...messages, createUserMessage({ content: decision.nudgeMessage })],
      transition: { reason: 'token_budget_continuation' },
    }
    continue
  }
}
```

#### 路径 2: needsFollowUp = true（有工具调用 → 续接）

```
有工具调用 → 执行工具 → 收集附件 → 检查中断 → 检查 maxTurns → continue
```

```typescript
// src/query.ts 第 1704 行
if (maxTurns && nextTurnCount > maxTurns) {
  yield createAttachmentMessage({ type: 'max_turns_reached', maxTurns, turnCount: nextTurnCount })
  return { reason: 'max_turns', turnCount: nextTurnCount }
}

// 正常续接
const next: State = {
  messages: [...messagesForQuery, ...assistantMessages, ...toolResults],
  toolUseContext: toolUseContextWithQueryTracking,
  autoCompactTracking: tracking,
  turnCount: nextTurnCount,
  maxOutputTokensRecoveryCount: 0,       // 重置恢复计数
  hasAttemptedReactiveCompact: false,     // 重置压缩标记
  pendingToolUseSummary: nextPendingToolUseSummary,
  maxOutputTokensOverride: undefined,    // 清除 token 覆盖
  stopHookActive,
  transition: { reason: 'next_turn' },
}
state = next
// while(true) 继续下一轮
```

#### 路径 3: 中断

```
abortController.signal.aborted → 清理 → return { reason: 'aborted_streaming' | 'aborted_tools' }
```

中断检查在两个位置：流式循环后和工具执行后。当使用流式工具执行时，中断后仍需消费 `getRemainingResults()` 来生成合成的 `tool_result` 块，确保 API 消息格式合法：

```typescript
// src/query.ts 第 1015 行
if (toolUseContext.abortController.signal.aborted) {
  if (streamingToolExecutor) {
    // 消费剩余结果以生成合成 tool_results
    for await (const update of streamingToolExecutor.getRemainingResults()) {
      if (update.message) yield update.message
    }
  } else {
    yield* yieldMissingToolResultBlocks(assistantMessages, 'Interrupted by user')
  }
  return { reason: 'aborted_streaming' }
}
```

---

## 5. API 层 claude.ts 深度解析

`src/services/api/claude.ts` 是整个系统中最大的单文件（约 2800+ 行），封装了与 Anthropic API 的全部交互。

### 5.1 消息规范化 normalizeMessagesForAPI

在发送前，消息需要转换为 API 格式：

```typescript
// src/services/api/claude.ts 第 1266 行
let messagesForAPI = normalizeMessagesForAPI(messages, filteredTools)
```

`normalizeMessagesForAPI`（定义在 `src/utils/messages.ts`）执行多项转换：
- 过滤掉 system 消息（只保留 user/assistant）
- 合并相邻的同角色消息
- 将内部 Message 类型转为 API 的 `MessageParam` 格式
- 处理 attachment 消息（转为 tool_result）
- 确保 tool_use/tool_result 配对完整

之后还有额外的修复步骤：

```typescript
// 修复 tool_use/tool_result 配对不匹配（跨会话恢复时可能出现）
messagesForAPI = ensureToolResultPairing(messagesForAPI)

// 移除超出 API 限制的媒体项（最多 100 个）
messagesForAPI = stripExcessMediaItems(messagesForAPI, API_MAX_MEDIA_PER_REQUEST)
```

### 5.2 系统提示组装

系统提示在 `queryModel` 中最终组装：

```typescript
// src/services/api/claude.ts 第 1358 行
systemPrompt = asSystemPrompt([
  getAttributionHeader(fingerprint),        // 指纹归属
  getCLISyspromptPrefix({...}),             // CLI 识别前缀
  ...systemPrompt,                          // 核心提示词
  ...(advisorModel ? [ADVISOR_TOOL_INSTRUCTIONS] : []),
  ...(injectChromeHere ? [CHROME_TOOL_SEARCH_INSTRUCTIONS] : []),
].filter(Boolean))
```

然后转为 API 的 `system` 参数格式，加入缓存控制：

```typescript
const system = buildSystemPromptBlocks(systemPrompt, enablePromptCaching, {
  skipGlobalCacheForSystemPrompt: needsToolBasedCacheMarker,
  querySource: options.querySource,
})
```

### 5.3 工具 Schema 序列化

工具定义通过 `toolToAPISchema` 转为 API 格式：

```typescript
// src/services/api/claude.ts 第 1235 行
const toolSchemas = await Promise.all(
  filteredTools.map(tool =>
    toolToAPISchema(tool, {
      getToolPermissionContext: options.getToolPermissionContext,
      tools,              // 传完整列表，让 ToolSearchTool 列出所有可用工具
      agents: options.agents,
      model: options.model,
      deferLoading: willDefer(tool),  // 延迟加载标记
    }),
  ),
)
```

**动态工具加载** 是一个重要优化。当工具数量很多时（MCP 服务器可能注册几十个工具），不需要在每次请求中包含所有工具的完整 schema。通过 `defer_loading` 标记，只有模型通过 `ToolSearchTool` 主动发现的工具才会被加载完整 schema：

```typescript
// 只包含非延迟工具 + 已被发现的延迟工具
filteredTools = tools.filter(tool => {
  if (!deferredToolNames.has(tool.name)) return true   // 非延迟工具总是包含
  if (toolMatchesName(tool, TOOL_SEARCH_TOOL_NAME)) return true  // 搜索工具本身
  return discoveredToolNames.has(tool.name)  // 已被发现的工具
})
```

### 5.4 Beta Header 管理

Claude Code 使用多个 Beta Header 来启用实验性 API 功能。每个 header 都有特定含义：

```typescript
// src/constants/betas.ts 中定义的 Beta 头
CONTEXT_1M_BETA_HEADER       // 1M 上下文窗口
CONTEXT_MANAGEMENT_BETA_HEADER  // API 侧上下文管理（微压缩）
EFFORT_BETA_HEADER           // 精力控制（low/medium/high）
FAST_MODE_BETA_HEADER        // 快速模式（降低延迟，可能降低质量）
PROMPT_CACHING_SCOPE_BETA_HEADER  // 全局缓存作用域
REDACT_THINKING_BETA_HEADER  // 思考内容脱敏
STRUCTURED_OUTPUTS_BETA_HEADER  // 结构化输出（JSON Schema）
TASK_BUDGETS_BETA_HEADER     // 任务预算
AFK_MODE_BETA_HEADER         // 离开模式（自动操作时使用）
ADVISOR_BETA_HEADER          // Advisor 工具（服务端工具）
```

为了避免缓存失效，Beta Header 使用**粘性锁定**（sticky latch）机制：

```typescript
// src/services/api/claude.ts 第 1405 行
// 粘性锁定：一旦首次发送某个 header，整个会话期间持续发送
// 防止中途切换导致服务端缓存 key 变化，浪费 ~50-70K token 的缓存

let afkHeaderLatched = getAfkModeHeaderLatched() === true
if (!afkHeaderLatched && shouldLatch) {
  afkHeaderLatched = true
  setAfkModeHeaderLatched(true)  // 写入 bootstrap state
}
```

### 5.5 请求参数构建

所有参数在 `paramsFromContext` 闭包中组装：

```typescript
// src/services/api/claude.ts 第 1538 行
const paramsFromContext = (retryContext: RetryContext) => {
  // 1. 组装 Beta 数组
  const betasParams = [...betas]

  // 2. 配置 output_config（effort、task_budget、structured output）
  const outputConfig: BetaOutputConfig = { ... }
  configureEffortParams(effort, outputConfig, extraBodyParams, betasParams, options.model)
  configureTaskBudgetParams(options.taskBudget, outputConfig, betasParams)

  // 3. 确定 max_output_tokens
  const maxOutputTokens =
    retryContext?.maxTokensOverride ||
    options.maxOutputTokensOverride ||
    getMaxOutputTokensForModel(options.model)

  // 4. 配置 thinking
  let thinking = undefined
  if (hasThinking && modelSupportsThinking(options.model)) {
    if (modelSupportsAdaptiveThinking(options.model)) {
      thinking = { type: 'adaptive' }    // 适应性思考（无预算限制）
    } else {
      thinking = { type: 'enabled', budget_tokens: thinkingBudget }
    }
  }

  // 5. 配置快速模式
  let speed: 'fast' | undefined
  if (isFastModeForRetry) speed = 'fast'

  // 6. 返回完整参数
  return {
    model: normalizeModelStringForAPI(options.model),
    messages: addCacheBreakpoints(messagesForAPI, enablePromptCaching, ...),
    system,
    tools: allTools,
    tool_choice: options.toolChoice,
    ...(useBetas && { betas: betasParams }),
    metadata: getAPIMetadata(),
    max_tokens: maxOutputTokens,
    thinking,
    ...(temperature !== undefined && { temperature }),
    ...extraBodyParams,
    ...(Object.keys(outputConfig).length > 0 && { output_config: outputConfig }),
    ...(speed !== undefined && { speed }),
  }
}
```

### 5.6 用量追踪与成本计算

用量在流式处理过程中累积：

```typescript
// message_start 事件中初始化 usage
usage = updateUsage(usage, part.message?.usage)

// message_delta 事件中更新（包含最终的 output_tokens）
usage = updateUsage(usage, part.usage)

// 计算并累加美元成本
const costUSDForPart = calculateUSDCost(resolvedModel, usage)
costUSD += addToTotalSessionCost(costUSDForPart, usage, options.model)
```

`updateUsage` 和 `accumulateUsage` 是两个不同的函数：
- `updateUsage`：取最新值（用于单个请求内的 usage 跟踪）
- `accumulateUsage`：累加（用于跨请求的总量统计）

### 5.7 错误分类

claude.ts 将 API 错误分为几大类：

- **认证错误** (401/403)：触发 OAuth 刷新或 API Key 重新获取
- **速率限制** (429)：触发退避重试或快速模式降级
- **过载** (529)：连续 3 次后触发模型后备
- **提示太长** (400 invalid_request)：触发压缩恢复
- **上下文溢出** (400 context overflow)：调整 max_tokens 重试
- **用户中断** (APIUserAbortError)：立即退出
- **连接超时**：降级到非流式模式

流式失败的后备逻辑特别精妙——当流式连接出错时，自动切换到非流式请求：

```typescript
// src/services/api/claude.ts 第 2551 行（在 streaming catch 块中）
const result = yield* executeNonStreamingRequest(
  { model: options.model, source: options.querySource },
  {
    model: options.model,
    fallbackModel: options.fallbackModel,
    thinkingConfig,
    signal,
    initialConsecutive529Errors: is529Error(streamingError) ? 1 : 0,
  },
  paramsFromContext,
  // ...
)
```

---

## 6. 重试机制 withRetry.ts

`src/services/api/withRetry.ts` 实现了一个功能丰富的重试生成器。

### 6.1 核心签名

```typescript
// src/services/api/withRetry.ts 第 170 行
export async function* withRetry<T>(
  getClient: () => Promise<Anthropic>,
  operation: (client: Anthropic, attempt: number, context: RetryContext) => Promise<T>,
  options: RetryOptions,
): AsyncGenerator<SystemAPIErrorMessage, T>
```

它是一个 async generator，在重试等待期间 yield `SystemAPIErrorMessage` 让 UI 显示"正在重试..."。最终返回操作结果 `T`。

### 6.2 指数退避

```typescript
// src/services/api/withRetry.ts 第 530 行
export function getRetryDelay(
  attempt: number,
  retryAfterHeader?: string | null,
  maxDelayMs = 32000,
): number {
  // 优先使用 Retry-After 头
  if (retryAfterHeader) {
    const seconds = parseInt(retryAfterHeader, 10)
    if (!isNaN(seconds)) return seconds * 1000
  }

  // 指数退避 + 抖动
  const baseDelay = Math.min(
    BASE_DELAY_MS * Math.pow(2, attempt - 1),  // 500, 1000, 2000, 4000, ...
    maxDelayMs,                                  // 上限 32s
  )
  const jitter = Math.random() * 0.25 * baseDelay  // 25% 随机抖动
  return baseDelay + jitter
}
```

### 6.3 529 过载与备用模型

连续 3 次 529 错误后触发模型降级：

```typescript
// src/services/api/withRetry.ts 第 327 行
if (is529Error(error)) {
  consecutive529Errors++
  if (consecutive529Errors >= MAX_529_RETRIES) {  // MAX_529_RETRIES = 3
    if (options.fallbackModel) {
      // 抛出特殊错误，query.ts 捕获后切换模型
      throw new FallbackTriggeredError(options.model, options.fallbackModel)
    }

    // 外部用户无后备模型时，给出友好错误
    if (process.env.USER_TYPE === 'external') {
      throw new CannotRetryError(
        new Error(REPEATED_529_ERROR_MESSAGE),
        retryContext,
      )
    }
  }
}
```

### 6.4 快速模式降级

快速模式遇到限流时有精细的降级策略：

```typescript
// src/services/api/withRetry.ts 第 267 行
if (wasFastModeActive && error.status === 429 || is529Error(error)) {
  // 检查是否因为 overage 被拒绝（永久禁用）
  const overageReason = error.headers?.get('anthropic-ratelimit-unified-overage-disabled-reason')
  if (overageReason) {
    handleFastModeOverageRejection(overageReason)
    retryContext.fastMode = false
    continue
  }

  const retryAfterMs = getRetryAfterMs(error)
  if (retryAfterMs !== null && retryAfterMs < SHORT_RETRY_THRESHOLD_MS) {
    // 短等待：保持快速模式（保留缓存）
    await sleep(retryAfterMs, options.signal)
    continue
  }

  // 长等待：进入冷却（切回标准模式）
  triggerFastModeCooldown(Date.now() + cooldownMs, cooldownReason)
  retryContext.fastMode = false
  continue
}
```

### 6.5 持久重试模式

用于无人值守会话（CI/CD 等），在 429/529 错误时无限重试：

```typescript
// src/services/api/withRetry.ts 第 477 行
if (persistent) {
  // 分块睡眠，每 30s yield 心跳保持会话活跃
  let remaining = delayMs
  while (remaining > 0) {
    if (options.signal?.aborted) throw new APIUserAbortError()
    yield createSystemAPIErrorMessage(error, remaining, reportedAttempt, maxRetries)
    const chunk = Math.min(remaining, HEARTBEAT_INTERVAL_MS)  // 30s
    await sleep(chunk, options.signal)
    remaining -= chunk
  }
  // 钳制 attempt 计数器，防止 for 循环终止
  if (attempt >= maxRetries) attempt = maxRetries
}
```

### 6.6 仅前台查询重试 529

一个重要的优化——后台查询（摘要、标题、建议等）遇到 529 直接失败，不重试：

```typescript
// src/services/api/withRetry.ts 第 62 行
const FOREGROUND_529_RETRY_SOURCES = new Set<QuerySource>([
  'repl_main_thread',
  'sdk',
  'agent:custom', 'agent:default', 'agent:builtin',
  'compact',
  'auto_mode',
  // ... 其他前台来源
])

// 后台查询直接放弃
if (is529Error(error) && !shouldRetry529(options.querySource)) {
  throw new CannotRetryError(error, retryContext)
}
```

---

## 7. QueryEngine.ts：SDK 桥接层设计

### 7.1 设计定位

`QueryEngine` 是连接 SDK/headless 世界和 query.ts 核心循环的桥梁：

```typescript
// src/QueryEngine.ts 第 184 行
/**
 * QueryEngine owns the query lifecycle and session state for a conversation.
 * It extracts the core logic from ask() into a standalone class that can be
 * used by both the headless/SDK path and (in a future phase) the REPL.
 *
 * One QueryEngine per conversation. Each submitMessage() call starts a new
 * turn within the same conversation.
 */
export class QueryEngine {
  private config: QueryEngineConfig
  private mutableMessages: Message[]          // 可变消息存储
  private abortController: AbortController    // 中断控制器
  private permissionDenials: SDKPermissionDenial[]  // 权限拒绝记录
  private totalUsage: NonNullableUsage        // 累计用量
  private readFileState: FileStateCache       // 文件状态缓存
  private discoveredSkillNames = new Set<string>()   // 技能发现追踪
  private loadedNestedMemoryPaths = new Set<string>() // 嵌套记忆路径
}
```

### 7.2 submitMessage 流程

`submitMessage` 是 QueryEngine 的核心方法，也是一个 async generator：

```typescript
// src/QueryEngine.ts 第 209 行
async *submitMessage(
  prompt: string | ContentBlockParam[],
  options?: { uuid?: string; isMeta?: boolean },
): AsyncGenerator<SDKMessage, void, unknown>
```

它做了以下工作：

1. **准备系统提示**：调用 `fetchSystemPromptParts` 获取默认提示、CLAUDE.md、git status 等
2. **处理用户输入**：通过 `processUserInput` 解析 slash 命令、附件等
3. **持久化用户消息**：在 API 调用前就写入 transcript（防止进程被杀时丢失）
4. **发起 query()**：将内部消息类型转换为 SDK 兼容的 `SDKMessage`
5. **消费生成器**：在 `for await` 循环中逐一处理 query() 的 yield

转换过程中，QueryEngine 将内部的丰富消息类型映射到 SDK 的扁平类型：

```typescript
// src/QueryEngine.ts 第 757 行（简化）
switch (message.type) {
  case 'tombstone':
    break  // SDK 不需要墓碑消息
  case 'assistant':
    this.mutableMessages.push(message)
    yield* normalizeMessage(message)  // 转为 SDKMessage
    break
  case 'stream_event':
    if (message.event.type === 'message_start') {
      currentMessageUsage = EMPTY_USAGE  // 重置单消息用量
    }
    if (message.event.type === 'message_delta') {
      // 更新用量和停止原因
      this.totalUsage = accumulateUsage(this.totalUsage, ...)
    }
    break
  // ...
}
```

### 7.3 QueryEngineConfig

```typescript
// src/QueryEngine.ts 第 130 行
export type QueryEngineConfig = {
  cwd: string                      // 工作目录
  tools: Tools                     // 可用工具列表
  commands: Command[]              // 可用命令列表
  mcpClients: MCPServerConnection[]  // MCP 服务器连接
  agents: AgentDefinition[]        // 代理定义
  canUseTool: CanUseToolFn         // 权限判定
  getAppState: () => AppState      // 状态读取
  setAppState: (f) => void         // 状态更新
  initialMessages?: Message[]      // 初始消息（恢复会话用）
  readFileCache: FileStateCache    // 文件读取缓存
  customSystemPrompt?: string      // 自定义系统提示
  appendSystemPrompt?: string      // 追加系统提示
  userSpecifiedModel?: string      // 用户指定模型
  fallbackModel?: string           // 后备模型
  thinkingConfig?: ThinkingConfig  // 思考配置
  maxTurns?: number                // 最大轮次
  maxBudgetUsd?: number            // 最大预算（美元）
  taskBudget?: { total: number }   // 任务预算
  jsonSchema?: Record<string, unknown>  // JSON Schema（结构化输出）
  verbose?: boolean                // 详细模式
  replayUserMessages?: boolean     // 回放用户消息
  includePartialMessages?: boolean // 包含部分消息
  snipReplay?: (msg, store) => ... // 历史裁剪回调
  // ...
}
```

这个配置体现了 QueryEngine 的"桥梁"角色——它同时持有 UI 层的关注（verbose、replayUserMessages）和核心层的关注（tools、systemPrompt）。

---

## 8. QueryConfig 与 QueryDeps 依赖注入模式

### 8.1 QueryConfig：不可变快照

```typescript
// src/query/config.ts
export type QueryConfig = {
  sessionId: SessionId
  gates: {
    streamingToolExecution: boolean  // 流式工具执行开关
    emitToolUseSummaries: boolean    // 工具摘要开关
    isAnt: boolean                   // 是否 Anthropic 内部用户
    fastModeEnabled: boolean         // 快速模式全局开关
  }
}

export function buildQueryConfig(): QueryConfig {
  return {
    sessionId: getSessionId(),
    gates: {
      streamingToolExecution: checkStatsigFeatureGate_CACHED_MAY_BE_STALE(
        'tengu_streaming_tool_execution2',
      ),
      emitToolUseSummaries: isEnvTruthy(
        process.env.CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES,
      ),
      isAnt: process.env.USER_TYPE === 'ant',
      fastModeEnabled: !isEnvTruthy(process.env.CLAUDE_CODE_DISABLE_FAST_MODE),
    },
  }
}
```

设计要点：
- **一次快照**：在 `queryLoop` 入口调用一次 `buildQueryConfig()`，整个循环使用同一份配置
- **CACHED_MAY_BE_STALE**：Statsig 特征门控本身就承认可能过时，快照不会引入额外的不一致
- **排除 feature() 门控**：`feature()` 是编译时常量（bun:bundle 的 tree-shaking 边界），不能被快照替代

### 8.2 QueryDeps：I/O 依赖注入

```typescript
// src/query/deps.ts
export type QueryDeps = {
  callModel: typeof queryModelWithStreaming  // API 调用
  microcompact: typeof microcompactMessages // 微压缩
  autocompact: typeof autoCompactIfNeeded   // 自动压缩
  uuid: () => string                        // UUID 生成
}

export function productionDeps(): QueryDeps {
  return {
    callModel: queryModelWithStreaming,
    microcompact: microcompactMessages,
    autocompact: autoCompactIfNeeded,
    uuid: randomUUID,
  }
}
```

这是一个精简但高效的 DI 模式：
- **类型安全**：使用 `typeof fn` 自动同步签名
- **最小范围**：只注入 4 个最常被 mock 的依赖
- **零成本默认**：`params.deps ?? productionDeps()` 让生产代码无感

使用示例：

```typescript
// 测试中
const fakeDeps: QueryDeps = {
  callModel: async function* () { yield fakeMessage },
  microcompact: async (msgs) => ({ messages: msgs }),
  autocompact: async () => ({ compactionResult: null }),
  uuid: () => 'test-uuid',
}

query({ ...params, deps: fakeDeps })
```

相比原来的 6-8 个测试文件中各自 `spyOn(module, 'functionName')` 的模式，这大幅减少了样板代码。

---

## 9. 设计模式与架构决策总结

### 9.1 Async Generator 贯穿全栈

从 `withRetry` 到 `queryModel` 到 `queryLoop` 到 `query` 到 `QueryEngine.submitMessage`——整个调用链都是 async generator。这不是偶然，而是深思熟虑的选择：

- **`withRetry`** yield 重试等待消息，return API 响应
- **`queryModel`** yield 流式事件和 AssistantMessage，通过 `yield*` 代理 withRetry
- **`queryLoop`** yield 所有消息类型，return Terminal（终止原因）
- **`query`** 包装 queryLoop，追加命令生命周期通知
- **`submitMessage`** yield SDKMessage，进行类型转换

`yield*` 的使用让代理生成器能透明传递值，同时在"之间"插入横切关注点。

### 9.2 Withheld Message 模式

一个反复出现的模式：某些错误消息被"扣留"（withheld），不立即 yield 给消费者：

```typescript
let withheld = false
if (reactiveCompact?.isWithheldPromptTooLong(message)) withheld = true
if (isWithheldMaxOutputTokens(message)) withheld = true
if (!withheld) yield yieldMessage
```

这解决了一个关键的竞态问题：SDK 消费者（如 Claude Desktop）收到 `error` 类型消息后会终止会话。如果先 yield 错误再尝试恢复，恢复代码还在运行但没人在监听了。扣留模式确保只有恢复彻底失败后才暴露错误。

### 9.3 Feature Gate 与条件导入

```typescript
// bun:bundle 编译时常量
const reactiveCompact = feature('REACTIVE_COMPACT')
  ? (require('./services/compact/reactiveCompact.js') as typeof import('...'))
  : null

// 使用时
if (reactiveCompact?.isWithheldPromptTooLong(message)) { ... }
```

这不是普通的运行时特征开关，而是**编译时 tree-shaking 边界**。Bun 的 bundler 在 `feature()` 为 false 时会完全删除 false 分支和对应的 `require()`，从最终二进制中移除未启用特性的所有代码。这就是为什么 `feature()` 只能出现在 `if` 条件或三元表达式中。

### 9.4 Token 经济学驱动的缓存策略

几乎所有设计决策都有缓存考量：

- **Beta Header 粘性锁定**：防止中途切换 header 导致服务端缓存失效（浪费 ~50-70K tokens）
- **消息缓存断点** (`addCacheBreakpoints`)：在最近的用户/助手消息上标记 `cache_control`，让前面的不变部分被缓存
- **全局缓存作用域** (`scope: 'global'`)：让不同会话共享系统提示缓存
- **1h TTL 缓存**：符合条件的用户（内部 + 订阅者）获得 1 小时 TTL，大幅降低成本
- **工具 Schema 排除延迟加载**：`defer_loading` 工具从缓存检测哈希中排除，避免工具发现导致虚假的缓存失效

### 9.5 多层恢复机制

面对各种故障，系统有分层的恢复策略：

```
prompt-too-long:
  1. 上下文折叠排空 (collapse drain)
  2. 反应式压缩 (reactive compact)
  3. 放弃并报错

max_output_tokens:
  1. 升级输出上限 (8K → 64K)
  2. 多轮恢复 (最多 3 次，注入续接指令)
  3. 放弃并报错

流式失败:
  1. 降级到非流式模式
  2. withRetry 指数退避
  3. 模型后备 (529 × 3 → fallback model)

认证失败:
  1. OAuth token 刷新
  2. 重新获取客户端
  3. 报错
```

### 9.6 遥测无处不在

几乎每个决策点都有 `logEvent` 调用，事件名以 `tengu_` 为前缀。这使得工程团队可以：

- 追踪真实用户的恢复路径触发频率 (`tengu_max_tokens_escalate`)
- 监控流式稳定性 (`tengu_streaming_stall`, `tengu_streaming_idle_timeout`)
- 分析缓存效率 (`tengu_api_after_normalize`)
- 调试生产问题 (`tengu_query_error`, `tengu_api_retry`)

### 9.7 思考规则

代码中的注释用"巫师规则"的方式记录了 thinking block 的三条不变量：

```typescript
/**
 * The rules of thinking are lengthy and fortuitous...
 *
 * 1. 包含 thinking/redacted_thinking 的消息必须属于 max_thinking_length > 0 的查询
 * 2. thinking block 不能是消息中的最后一个块
 * 3. thinking block 必须在整个助手轨迹期间保持不变
 *    （单轮，或如果该轮包含 tool_use 则包括后续的 tool_result 和下一个助手消息）
 */
```

违反这些规则会导致 API 400 错误（"thinking blocks cannot be modified"），这是代码中多处小心处理签名块（signature blocks）的原因。

---

## 总结

Claude Code 的对话循环是一个精心设计的多层异步管道：

1. **REPL.tsx** 通过 React Hooks 管理 UI 状态，将用户输入路由到查询系统
2. **QueryEngine** 维护会话状态，进行 SDK 类型转换，管理 transcript 持久化
3. **query.ts** 驱动核心 while(true) 循环，处理工具调用、上下文压缩、多路恢复
4. **claude.ts** 封装 API 通信细节——流式解析、缓存控制、参数组装
5. **withRetry.ts** 提供弹性的重试策略——指数退避、模型降级、持久重试

这五层通过 async generator 的 `yield`/`yield*` 链条串联，形成了一个高效、可恢复、可测试的 AI 代理运行时。理解了这条链路，就理解了 Claude Code 在按下 Enter 后发生的一切。
