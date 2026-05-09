# 第 15 篇：Microcompact — 旧工具结果的机械清理

> 第 14 篇 Snip 是「让模型决定丢什么」。本篇 Microcompact 走的是相反路线：**白名单 + 时间 / 数量阈值的纯机械裁剪**，不问模型意见。
>
> 对 SWE agent 训练用的 RepoHarness 来说，这一篇是**最值得直接借鉴**的一层——它的设计不依赖 Anthropic 服务端的特殊能力，是个普适的"轻量上下文管理"模板。

---

## 0. 给 RepoHarness 读者的导读

如果你的目标是给训练用 harness 加一层轻量上下文压缩：

- ✅ **直接参考的是 time-based 路径**——只用本地状态、占位字符串替换、token 计数。所有生产级 SWE agent harness 都能搬。
- ❌ **不要复刻 cached MC 路径**——它依赖 Anthropic 私有的 `cache_edits` API 和 `cache_reference` 头，外部无法调用。
- ❌ **不要复刻 API context management 路径**——它依赖 `context_management` 请求字段和 `CONTEXT_MANAGEMENT_BETA_HEADER`，同样是 Anthropic 私有。

但**了解三条路径的存在很有价值**——它告诉你「客户端清理」「客户端跟踪+服务端编辑」「服务端自治理」这三种取舍各自适用什么场景，对你设计自己的压缩策略有参考意义。

---

## 1. 一句话定义

> **Microcompact = 在每轮主循环开始前，把 8 类指定工具的旧结果清掉，机械按"时间"或"累计数量"阈值触发，不调 LLM。**

四个关键约束：

1. **白名单**：只清这 8 类工具的结果。模型自己的回复、user 文本、其他工具不动。
2. **机械触发**：看时间或工具数量，**不看 token 总数**。这点和 AutoCompact 完全不同。
3. **零成本**：不调任何 LLM。最贵的操作是遍历消息数组。
4. **三选一**（可能全 no-op）：time-based / cached MC / API context management 互斥。每轮选一种或都不做。

源码主体：[services/compact/microCompact.ts](../../claude-code-typescript-src/services/compact/microCompact.ts)（530 行）+ [services/compact/timeBasedMCConfig.ts](../../claude-code-typescript-src/services/compact/timeBasedMCConfig.ts)（43 行）+ [services/compact/apiMicrocompact.ts](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts)（154 行）。

---

## 2. 三条路径的全貌（修正：第 12 篇里我说的"两条路径"不全）

| 路径 | 谁触发 | 谁删 | 状态在哪 | 影响 prompt cache？| 普通用户可见？|
|---|---|---|---|---|---|
| **Time-based** | 客户端 | 客户端改本地消息内容 | 消息数组本身 | 让 cache 失效（但反正 1 小时已过期）| ✓（feature flag 默认关）|
| **Cached MC** | 客户端 | 服务端通过 `cache_edits` 块 | `cachedMCState` module 单例 + 服务端 cache | 不失效（专为兼容 cache 设计）| ✗ ant-only |
| **API context management** | 客户端声明策略 | 服务端按策略执行 | 完全在服务端 | 服务端管理 | ✗ ant-only |

调度逻辑（[microCompact.ts:253-293](../../claude-code-typescript-src/services/compact/microCompact.ts#L253-L293)）：

```typescript
export async function microcompactMessages(messages, toolUseContext, querySource) {
  clearCompactWarningSuppression()

  // 1. 优先 time-based：cache 已冷的话立刻清，简单粗暴
  const timeBasedResult = maybeTimeBasedMicrocompact(messages, querySource)
  if (timeBasedResult) {
    return timeBasedResult       // ← 短路返回，不再走其他路径
  }

  // 2. cache 还热？走 cached MC（ant-only）
  if (feature('CACHED_MICROCOMPACT')) {
    const mod = await getCachedMCModule()
    if (mod.isCachedMicrocompactEnabled() &&
        mod.isModelSupportedForCacheEditing(model) &&
        isMainThreadSource(querySource)) {
      return await cachedMicrocompactPath(messages, querySource)
    }
  }

  // 3. 都不行：no-op，让 autocompact 处理压力
  return { messages }
}
```

注意：**API context management（第三条）的入口不在 `microcompactMessages` 里**，它在 [services/api/claude.ts:1633](../../claude-code-typescript-src/services/api/claude.ts#L1633) 通过 `getAPIContextManagement()` 注入到 API 请求 body。和前两条相互独立、可以同时启用，因为它压根不在 microcompact 调度里。

我后面把它当作"第三种 microcompact 范式"讲，因为 [apiMicrocompact.ts:15](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts#L15) 自己注释 "Match client-side microcompact token values"，是同一思路的服务端实现。

---

## 3. 共享设施：`COMPACTABLE_TOOLS` 白名单

[microCompact.ts:41-50](../../claude-code-typescript-src/services/compact/microCompact.ts#L41-L50)：

```typescript
const COMPACTABLE_TOOLS = new Set<string>([
  FILE_READ_TOOL_NAME,
  ...SHELL_TOOL_NAMES,        // bash 等
  GREP_TOOL_NAME,
  GLOB_TOOL_NAME,
  WEB_SEARCH_TOOL_NAME,
  WEB_FETCH_TOOL_NAME,
  FILE_EDIT_TOOL_NAME,
  FILE_WRITE_TOOL_NAME,
])
```

### 3.1 为什么是这 8 个

挑选标准是「**结果在对话后期可重新获取或不再需要**」：

| 工具 | 为什么可压缩 |
|---|---|
| FileRead | 文件还在磁盘，需要时再读一次 |
| Bash / Shell | 命令是一次性的；如果输出还需要可重跑（虽然慢）|
| Grep | 同上，搜索可重跑 |
| Glob | 文件列表可重新枚举 |
| WebSearch | 搜索结果旧了反而可能误导 |
| WebFetch | 页面内容可重新抓 |
| FileEdit | 编辑结果是文件本身，可 Read 看 |
| FileWrite | 写入结果是文件本身，可 Read 看 |

**反例（不在白名单里）**：

| 工具 | 为什么不能压缩 |
|---|---|
| TodoWrite | 工具结果就是当前 todo 状态本身，丢了模型不知道任务进展 |
| AgentTool | 子代理的输出是模型推理产物，重做成本高 |
| AskUserQuestion | 用户的回答没法"重新获取" |
| 自定义 MCP 工具 | 行为未知，盲目清可能丢失关键状态 |

注意 API 路径的白名单略不同。[apiMicrocompact.ts:19-32](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts#L19-L32) 把白名单分成两组：

```typescript
const TOOLS_CLEARABLE_RESULTS = [
  ...SHELL_TOOL_NAMES, GLOB_TOOL_NAME, GREP_TOOL_NAME,
  FILE_READ_TOOL_NAME, WEB_FETCH_TOOL_NAME, WEB_SEARCH_TOOL_NAME,
]

const TOOLS_CLEARABLE_USES = [   // 注意是反向语义：这些不被清！
  FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME, NOTEBOOK_EDIT_TOOL_NAME,
]
```

差异：API 路径里 FileEdit / FileWrite / NotebookEdit **不被清**，而 client-side 路径**清**。原因猜测：API 服务端清的是整个 tool_use（包括输入参数 `{ file_path, old_str, new_str }`），这些参数本身就有信息量；client-side 只清 tool_result（"编辑成功"占位字符串价值不高）。两者不是同一回事。

### 3.2 收集白名单内的工具 ID

[microCompact.ts:226-241](../../claude-code-typescript-src/services/compact/microCompact.ts#L226-L241)：

```typescript
function collectCompactableToolIds(messages: Message[]): string[] {
  const ids: string[] = []
  for (const message of messages) {
    if (message.type === 'assistant' && Array.isArray(message.message.content)) {
      for (const block of message.message.content) {
        if (block.type === 'tool_use' && COMPACTABLE_TOOLS.has(block.name)) {
          ids.push(block.id)        // ← 用 tool_use.id 作为关联键
        }
      }
    }
  }
  return ids
}
```

关键：**用 `tool_use.id` 串联 assistant 的 tool_use 和 user 的 tool_result**。这是 Claude API 的天然契约——每个 tool_use 块带 id，对应的 tool_result 块带 `tool_use_id` 引用。

---

## 4. 路径一：Time-based 微压缩（详解 + 例子）

### 4.1 配置

[timeBasedMCConfig.ts:18-34](../../claude-code-typescript-src/services/compact/timeBasedMCConfig.ts#L18-L34)：

```typescript
export type TimeBasedMCConfig = {
  enabled: boolean
  /** 触发：距上次 assistant 消息超过这个分钟数。
   *  60 是安全选择：服务端 1h cache TTL 一定已过期，
   *  我们不会强行制造一个本来就不会发生的 cache miss。 */
  gapThresholdMinutes: number
  /** 保留最近 N 个工具结果，更早的清掉。 */
  keepRecent: number
}

const TIME_BASED_MC_CONFIG_DEFAULTS: TimeBasedMCConfig = {
  enabled: false,
  gapThresholdMinutes: 60,
  keepRecent: 5,
}
```

实际配置通过 GrowthBook 的 feature flag `tengu_slate_heron` 远端下发。默认关闭。

### 4.2 触发判断

[microCompact.ts:422-444](../../claude-code-typescript-src/services/compact/microCompact.ts#L422-L444)：

```typescript
export function evaluateTimeBasedTrigger(messages, querySource) {
  const config = getTimeBasedMCConfig()

  // 必须有显式的主线程 querySource。undefined 不行——分析-only 调用
  // （/context, /compact 内部调用的 microcompactMessages）不应触发。
  if (!config.enabled || !querySource || !isMainThreadSource(querySource)) {
    return null
  }

  const lastAssistant = messages.findLast(m => m.type === 'assistant')
  if (!lastAssistant) {
    return null
  }

  const gapMinutes =
    (Date.now() - new Date(lastAssistant.timestamp).getTime()) / 60_000

  if (!Number.isFinite(gapMinutes) || gapMinutes < config.gapThresholdMinutes) {
    return null
  }

  return { gapMinutes, config }
}
```

四重保护，全过才触发：

1. **配置启用**：`config.enabled === true`
2. **有 querySource 且是主线程**：分析工具调用（如 `/context`）传 `undefined` 不会触发，避免假动作
3. **历史里有 assistant 消息**：第一轮自然不触发
4. **真过了阈值**：默认 60 分钟

注释里的细节：「`isMainThreadSource` 把 undefined 当主线程（为了 cached-MC 向后兼容），但 `/context`、`/compact`、`analyzeContext` 等分析路径会传 undefined，所以这里**显式要求 querySource 非 undefined**，强行排除分析调用」。这是个加强约束。

### 4.3 执行：清理 + 替换占位符

[microCompact.ts:446-530](../../claude-code-typescript-src/services/compact/microCompact.ts#L446-L530)：

```typescript
function maybeTimeBasedMicrocompact(messages, querySource) {
  const trigger = evaluateTimeBasedTrigger(messages, querySource)
  if (!trigger) return null
  const { gapMinutes, config } = trigger

  const compactableIds = collectCompactableToolIds(messages)

  // Floor at 1: slice(-0) 返回完整数组（反直觉地保留所有），
  // 而清空所有工具结果会让模型完全失去工作上下文。两者都没意义。
  const keepRecent = Math.max(1, config.keepRecent)
  const keepSet = new Set(compactableIds.slice(-keepRecent))     // 最后 N 个
  const clearSet = new Set(compactableIds.filter(id => !keepSet.has(id)))

  if (clearSet.size === 0) return null

  let tokensSaved = 0
  const result = messages.map(message => {
    if (message.type !== 'user' || !Array.isArray(message.message.content)) {
      return message
    }
    let touched = false
    const newContent = message.message.content.map(block => {
      if (block.type === 'tool_result' &&
          clearSet.has(block.tool_use_id) &&
          block.content !== TIME_BASED_MC_CLEARED_MESSAGE) {  // 幂等
        tokensSaved += calculateToolResultTokens(block)
        touched = true
        return { ...block, content: TIME_BASED_MC_CLEARED_MESSAGE }
      }
      return block
    })
    if (!touched) return message
    return { ...message, message: { ...message.message, content: newContent } }
  })

  if (tokensSaved === 0) return null   // 防御：万一 clearSet 不空但内容已是占位符

  // ... logEvent + suppressCompactWarning + resetMicrocompactState ...
  return { messages: result }
}
```

占位符常量（[microCompact.ts:36](../../claude-code-typescript-src/services/compact/microCompact.ts#L36)）：

```typescript
export const TIME_BASED_MC_CLEARED_MESSAGE = '[Old tool result content cleared]'
```

### 4.4 一个具体例子（30 个 tool_result，gap = 75 分钟）

```
当前消息状态（按时间顺序）：
  [user]      初始问题
  [assistant] tool_use(Read auth.ts)             id=u_001
  [user]      tool_result u_001 → "1500 行..."
  [assistant] tool_use(Bash npm test)             id=u_002
  [user]      tool_result u_002 → "通过 ..."
  ... (中间 26 个 tool_use/tool_result 对) ...
  [assistant] tool_use(Read final.ts)             id=u_029
  [user]      tool_result u_029 → "..."
  [assistant] tool_use(Edit final.ts)             id=u_030
  [user]      tool_result u_030 → "..."
  [assistant] "看完了，明天继续"  ← 上一次 assistant 在 75 分钟前

  [user]      "我们继续吧" ← 用户现在发的，触发新一轮

evaluateTimeBasedTrigger:
  - config.enabled = true
  - querySource = 'repl_main_thread'
  - lastAssistant.timestamp = 75 分钟前
  - 75 >= 60 ✓ → 触发

collectCompactableToolIds:
  → [u_001, u_002, ..., u_030]   (30 个)

keepRecent = 5
keepSet  = {u_026, u_027, u_028, u_029, u_030}
clearSet = {u_001 .. u_025}                       (25 个被清)

遍历消息：
  把 25 条 tool_result 的 content 替换为
  '[Old tool result content cleared]'

假设每个 tool_result 平均 4000 tokens：
  tokensSaved = 25 × 4000 = 100,000 tokens
  
压缩后消息：
  [user]      初始问题
  [assistant] tool_use(Read auth.ts)               id=u_001
  [user]      tool_result u_001 → '[Old ...cleared]'    ← 内容清了
  ...
  [assistant] tool_use(Bash test)                  id=u_026
  [user]      tool_result u_026 → "..." (完整)        ← 保留
  ...
  [user]      "我们继续吧"
```

注意：

- **tool_use 块完全不动**——保留 id 和参数，否则配对断裂
- **只 tool_result 的 content 字段变成占位符**——结构不变
- **保留最近 5 个**——而不是最早 5 个，因为最近的最有可能正在用
- **幂等**：第二次跑（如果有人立刻又调）`block.content !== TIME_BASED_MC_CLEARED_MESSAGE` 检查会跳过

### 4.5 副作用：reset cached MC 状态 + 通知 cache break detector

[microCompact.ts:511-527](../../claude-code-typescript-src/services/compact/microCompact.ts#L511-L527)：

```typescript
suppressCompactWarning()
// Cached-MC state (module-level) 持有先前轮次注册的 tool ID。
// 我们刚刚清掉了一些这些工具的内容 AND 通过修改 prompt 内容
// 让服务端 cache 失效。如果 cached-MC 下一轮带着 stale state 跑，
// 它会试图 cache_edit 服务端不存在的工具。所以必须 reset。
resetMicrocompactState()

// 我们刚改了 prompt 内容——下一次响应的 cache read 会偏低，
// 但这是我们干的，不是真"cache break"。告诉 detector 预期会有 drop。
if (feature('PROMPT_CACHE_BREAK_DETECTION') && querySource) {
  notifyCacheDeletion(querySource)
}
```

两个关键的"清场"动作：

1. **重置 cached MC 模块状态**（防止下一轮 cached MC 删服务端不存在的工具）
2. **通知 cache break 监控**（prompt cache 命中率监控不会误报这次为故障）

---

## 5. 路径二：Cached MC（依赖 Anthropic 服务端的私有能力）

> 源码 `services/compact/cachedMicrocompact.ts` 在快照里被 dead-code-elimination 删除，本节内容是从外围调用点逆向推断。

### 5.1 设计思路

time-based 路径有个明显代价：**改了本地消息 → 服务端 prompt cache 失效 → 下一轮 prefix 全部重传**。如果 cache 还热着（最近交互），这个代价不值得。

cached MC 解决这个：**不动本地消息，发一个 `cache_edits` 指令告诉服务端"请把 cached prefix 里这些 tool_use_id 对应的内容删掉"**。服务端在 cache 层面做编辑，cache key 不变，下一轮还是 cache hit。

### 5.2 触发与跳过

[microCompact.ts:276-286](../../claude-code-typescript-src/services/compact/microCompact.ts#L276-L286)：

```typescript
if (feature('CACHED_MICROCOMPACT')) {
  const mod = await getCachedMCModule()
  const model = toolUseContext?.options.mainLoopModel ?? getMainLoopModel()
  if (
    mod.isCachedMicrocompactEnabled() &&
    mod.isModelSupportedForCacheEditing(model) &&
    isMainThreadSource(querySource)         // ← 关键：仅主线程
  ) {
    return await cachedMicrocompactPath(messages, querySource)
  }
}
```

**仅主线程**这一条很重要。注释解释了根因（[microCompact.ts:272-275](../../claude-code-typescript-src/services/compact/microCompact.ts#L272-L275)）：

> 只对主线程跑 cached MC，防止 forked agents（session_memory、prompt_suggestion 等）把它们的 tool_results 注册到全局 `cachedMCState` —— 那会导致主线程试图删除自己对话里**根本不存在的工具**。

`cachedMCState` 是 module-level 的全局单例（同一进程所有 fork 共享）。fork 子代理的工具调用如果污染这个状态，主线程下一轮拿到一个混乱的 tool ID 列表。

### 5.3 注册 + 决定要删什么

[microCompact.ts:305-339](../../claude-code-typescript-src/services/compact/microCompact.ts#L305-L339)：

```typescript
async function cachedMicrocompactPath(messages, querySource) {
  const mod = await getCachedMCModule()
  const state = ensureCachedMCState()
  const config = mod.getCachedMCConfig()      // GrowthBook 配置：triggerThreshold + keepRecent

  const compactableToolIds = new Set(collectCompactableToolIds(messages))

  // 第二趟：按 user 消息分组注册 tool_result
  for (const message of messages) {
    if (message.type === 'user' && Array.isArray(message.message.content)) {
      const groupIds: string[] = []
      for (const block of message.message.content) {
        if (block.type === 'tool_result' &&
            compactableToolIds.has(block.tool_use_id) &&
            !state.registeredTools.has(block.tool_use_id)) {
          mod.registerToolResult(state, block.tool_use_id)
          groupIds.push(block.tool_use_id)
        }
      }
      mod.registerToolMessage(state, groupIds)   // 一次注册一组（同消息内的多个 tool_result）
    }
  }

  const toolsToDelete = mod.getToolResultsToDelete(state)
  // 内部逻辑（推断）：
  //   if (state.toolOrder.length > config.triggerThreshold) {
  //     return state.toolOrder.slice(0, -config.keepRecent)
  //   } else return []

  if (toolsToDelete.length > 0) {
    const cacheEdits = mod.createCacheEditsBlock(state, toolsToDelete)
    if (cacheEdits) {
      pendingCacheEdits = cacheEdits   // ← 排队，由 API 层消费
    }
    // ... 日志 ...
  }
  ...
}
```

**机制要点**：

1. **基于工具数量触发**（不是时间）：累计 tool_result 数 > triggerThreshold → 触发
2. **按 user 消息分组**：同一个 user 消息可能含多个 tool_result（并行工具调用），作为一组一起删
3. **本地消息不动**：返回 `{ messages: messages, ... }`，cache_edits 通过 `pendingCacheEdits` 排队给 API 层

### 5.4 cache_edits 块怎么发出去

[microCompact.ts:88-94](../../claude-code-typescript-src/services/compact/microCompact.ts#L88-L94)：

```typescript
export function consumePendingCacheEdits(): CacheEditsBlock | null {
  const edits = pendingCacheEdits
  pendingCacheEdits = null
  return edits
}
```

API 层在 [services/api/claude.ts:1701-1709](../../claude-code-typescript-src/services/api/claude.ts#L1701-L1709) 消费：

```typescript
return {
  ...
  messages: addCacheBreakpoints(
    messagesForAPI,
    enablePromptCaching,
    options.querySource,
    useCachedMC,
    consumedCacheEdits,        // ← 这里
    consumedPinnedEdits,
    options.skipCacheWrite,
  ),
  ...
}
```

`useCachedMC` 的判断（[claude.ts:1675-1678](../../claude-code-typescript-src/services/api/claude.ts#L1675-L1678)）：

```typescript
const useCachedMC =
  cachedMCEnabled &&
  getAPIProvider() === 'firstParty' &&        // ← 仅 Anthropic 直连，Bedrock/Vertex 都不行
  options.querySource === 'repl_main_thread'
```

需要**特殊 beta header `cacheEditingBetaHeader`** 才能用，是 ant-only API 能力。

### 5.5 baseline 计算（精确反馈）

[microCompact.ts:374-394](../../claude-code-typescript-src/services/compact/microCompact.ts#L374-L394)：

```typescript
// API 返回的 cache_deleted_input_tokens 是累计值（sticky），
// 需要减去上次 baseline 才是这次的 delta
const lastAsst = messages.findLast(m => m.type === 'assistant')
const baseline = lastAsst?.type === 'assistant'
  ? (lastAsst.message.usage as ...).cache_deleted_input_tokens ?? 0
  : 0

return {
  messages,
  compactionInfo: {
    pendingCacheEdits: {
      trigger: 'auto',
      deletedToolIds: toolsToDelete,
      baselineCacheDeletedTokens: baseline,    // ← 用于精确算这次省了多少
    },
  },
}
```

为什么要 baseline？因为服务端报告的 `cache_deleted_input_tokens` 是**整个会话累计值**（sticky）。这次操作真实释放了 N tokens = `本次响应.cache_deleted - baseline`。这个差值用于精确计算 boundary message 的统计、logEvent 的精确数据。

---

## 6. 路径三：API Context Management（服务端自治理）

源码完整保留：[services/compact/apiMicrocompact.ts](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts)（154 行）。

### 6.1 思路

cached MC 还是「客户端跟踪 + 客户端发指令删除」。这条路径更激进：**完全把决策交给服务端，客户端只声明 strategy**。

```typescript
// 服务端实现的策略（对应 ContextEditStrategy）
{
  type: 'clear_tool_uses_20250919',
  trigger: { type: 'input_tokens', value: 180_000 },        // ≥ 180K 触发
  clear_at_least: { type: 'input_tokens', value: 140_000 }, // 至少清 140K
  clear_tool_inputs: ['bash', 'read', 'grep', ...],         // 这些工具的 input 也清
}
```

服务端看到 `input_tokens >= 180K` 就触发，自己挑工具清，目标降到 ~40K。客户端不需要跟踪任何状态。

### 6.2 完整接口

[apiMicrocompact.ts:34-61](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts#L34-L61)：

```typescript
export type ContextEditStrategy =
  | {
      type: 'clear_tool_uses_20250919'
      trigger?: { type: 'input_tokens', value: number }
      keep?: { type: 'tool_uses', value: number }
      clear_tool_inputs?: boolean | string[]
      exclude_tools?: string[]
      clear_at_least?: { type: 'input_tokens', value: number }
    }
  | {
      type: 'clear_thinking_20251015'
      keep: { type: 'thinking_turns', value: number } | 'all'
    }

export type ContextManagementConfig = {
  edits: ContextEditStrategy[]
}
```

两种策略：

| 策略类型 | 作用 |
|---|---|
| `clear_tool_uses_20250919` | 清旧 tool_use（按 trigger 阈值触发，clear_at_least 是最小释放量）|
| `clear_thinking_20251015` | 清旧 thinking 块（保留最后 N 轮的思考）|

### 6.3 默认值

[apiMicrocompact.ts:14-17](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts#L14-L17)：

```typescript
const DEFAULT_MAX_INPUT_TOKENS = 180_000   // 触发阈值，对齐 client-side warning
const DEFAULT_TARGET_INPUT_TOKENS = 40_000 // 目标保留量
```

环境变量可覆盖：`API_MAX_INPUT_TOKENS`、`API_TARGET_INPUT_TOKENS`。

### 6.4 触发逻辑

[apiMicrocompact.ts:64-153](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts#L64-L153)：

```typescript
export function getAPIContextManagement(options): ContextManagementConfig | undefined {
  const strategies: ContextEditStrategy[] = []

  // thinking 清理（任何 ant 用户都可以）
  if (hasThinking && !isRedactThinkingActive) {
    strategies.push({
      type: 'clear_thinking_20251015',
      keep: clearAllThinking ? { type: 'thinking_turns', value: 1 } : 'all',
    })
  }

  // tool 清理仅 ant-only
  if (process.env.USER_TYPE !== 'ant') {
    return strategies.length > 0 ? { edits: strategies } : undefined
  }

  // 通过环境变量启用具体策略
  const useClearToolResults = isEnvTruthy(process.env.USE_API_CLEAR_TOOL_RESULTS)
  const useClearToolUses    = isEnvTruthy(process.env.USE_API_CLEAR_TOOL_USES)

  if (useClearToolResults) {
    strategies.push({
      type: 'clear_tool_uses_20250919',
      trigger: { type: 'input_tokens', value: triggerThreshold },
      clear_at_least: { type: 'input_tokens', value: triggerThreshold - keepTarget },
      clear_tool_inputs: TOOLS_CLEARABLE_RESULTS,
    })
  }

  if (useClearToolUses) {
    strategies.push({
      type: 'clear_tool_uses_20250919',
      trigger: { type: 'input_tokens', value: triggerThreshold },
      clear_at_least: { type: 'input_tokens', value: triggerThreshold - keepTarget },
      exclude_tools: TOOLS_CLEARABLE_USES,    // ← 注意：exclude 而非 include
    })
  }

  return strategies.length > 0 ? { edits: strategies } : undefined
}
```

差异：

- `useClearToolResults` 用 `clear_tool_inputs: [bash, read, ...]` —— **指定要清的工具白名单**
- `useClearToolUses` 用 `exclude_tools: [edit, write, notebookEdit]` —— **指定要保留的工具黑名单**，其他全清

后者更激进：除了 Edit/Write/NotebookEdit 之外的所有工具都被清，包括 input 参数。前者更保守：只清你白名单里的。

### 6.5 thinking 清理的微妙逻辑

[apiMicrocompact.ts:82-87](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts#L82-L87)：

```typescript
if (hasThinking && !isRedactThinkingActive) {
  strategies.push({
    type: 'clear_thinking_20251015',
    keep: clearAllThinking ? { type: 'thinking_turns', value: 1 } : 'all',
  })
}
```

注释解释：

> 当 `clearAllThinking` 设为 true（≥1h 空闲 = cache miss），保留最后 1 个 thinking turn —— API schema 要求 value >= 1，**不发这条 edit 会回退到模型默认（通常是 'all'），那不会清任何东西**。

也就是：「想清干净」≠「不发 strategy」。要发 `keep: 1` 才是真清，发 `'all'` 是显式保留。这是一个容易踩的坑。

### 6.6 注入到 API 请求

[services/api/claude.ts:1718-1722](../../claude-code-typescript-src/services/api/claude.ts#L1718-L1722)：

```typescript
...(contextManagement &&
  useBetas &&
  betasParams.includes(CONTEXT_MANAGEMENT_BETA_HEADER) && {
    context_management: contextManagement,
  }),
```

需要 `CONTEXT_MANAGEMENT_BETA_HEADER` beta header 才生效。

---

## 7. 三条路径的协作 / 互斥

### 7.1 `microcompactMessages` 内的互斥（time-based vs cached）

如果 time-based 触发，**短路返回**（[microCompact.ts:268-270](../../claude-code-typescript-src/services/compact/microCompact.ts#L268-L270)），cached MC 这一轮不跑。原因（[microCompact.ts:265-266](../../claude-code-typescript-src/services/compact/microCompact.ts#L265-L266)）：

> Cached MC (cache-editing) is skipped when this fires: editing assumes a warm cache, and we just established it's cold.

cached MC 的存在前提是 cache 还热。time-based 触发本身就意味着 cache 已经凉了，再走 cached MC 没意义。

### 7.2 API context management 与前两者无关

它在 API 层独立注入，不参与 microcompact 调度。**理论上可以同时启用 time-based + API context management**，各管各的：

- time-based 在客户端清旧 tool_result 内容
- API context management 在服务端按总 input_tokens 清旧 tool_use

但实操中，因为 API context management 是 ant-only feature，普通用户不会碰它。

---

## 8. 关键不变量

| 不变量 | 为什么重要 |
|---|---|
| **不破坏 tool_use ↔ tool_result 配对** | 所有路径只动 tool_result.content，tool_use 和 tool_result 块本身保留 |
| **不动主线程之外的 querySource** | forked agents（session_memory 等）共享 module state，污染会让主线程崩 |
| **time-based 触发后必 reset cached MC state** | 否则下一轮 cached MC 试图删服务端不存在的工具 |
| **替换占位符前检查幂等** | `block.content !== TIME_BASED_MC_CLEARED_MESSAGE` 防止 tokensSaved 误算 |
| **keepRecent 必须 ≥ 1** | `Math.max(1, config.keepRecent)`，否则 `slice(-0)` 返回完整数组（JS 反直觉行为）|
| **cached MC 仅 firstParty + repl_main_thread** | Bedrock/Vertex 不支持 cache_edits beta；非主线程会污染状态 |
| **通知 cache break detector** | 防止"我们主动清了 cache"被监控误报为故障 |

---

## 9. 面向 RepoHarness 的实战要点

> 你做的 RepoHarness 是 SWE agent 训练的 harness 设施，下面是从 microcompact 里能直接借鉴的设计。

### 9.1 适合借鉴的：time-based 路径的核心思路

可以在你的 harness 里实现一个「轻量上下文清理器」：

```python
# 伪代码示意，给 SWE harness 用
COMPACTABLE_TOOLS = {'read_file', 'run_bash', 'grep', 'glob', 'web_fetch'}

def compact_old_tool_results(messages, *, keep_recent=5, threshold_minutes=60):
    # 1. 时间检查（或者：累计工具数检查）
    last_assistant = next((m for m in reversed(messages) if m.role == 'assistant'), None)
    if not last_assistant or (now() - last_assistant.timestamp).minutes < threshold_minutes:
        return messages, 0

    # 2. 收集白名单内的 tool_use ID
    compactable_ids = [
        block.id for m in messages if m.role == 'assistant'
        for block in m.content if block.type == 'tool_use' and block.name in COMPACTABLE_TOOLS
    ]
    
    # 3. 保留最近 N 个
    keep_set = set(compactable_ids[-max(1, keep_recent):])
    clear_set = set(compactable_ids) - keep_set
    
    # 4. 替换 tool_result 内容
    tokens_saved = 0
    for m in messages:
        if m.role == 'user':
            for block in m.content:
                if block.type == 'tool_result' and block.tool_use_id in clear_set:
                    if block.content != PLACEHOLDER:
                        tokens_saved += estimate_tokens(block.content)
                        block.content = PLACEHOLDER
    
    return messages, tokens_saved
```

### 9.2 几个关键设计选择（从源码学到的）

**白名单选择**：你的训练 harness 里的 SWE 工具大概是 `view_file / edit_file / run_tests / grep / find` 这类。判断标准是「**结果在后期可重新获取，或不可逆地变成了文件状态本身**」：

- ✅ `view_file` 可清（文件还在）
- ✅ `run_tests` 可清（可重跑或看 output 文件）
- ❌ `submit_solution` 不能清（最终决策行为）
- ❌ `record_bug_hypothesis` 不能清（推理产物）

**保留最近 N 个**：源码默认 5。SWE agent 任务里建议**调高到 10-15**，因为 SWE 任务通常需要在多个文件间穿梭，最近读过的文件大概率还要再读。

**触发阈值的选择**：源码用「时间」是因为 cache TTL 是 1 小时。**SWE 训练 harness 没有 prompt cache 的强约束，按"累计工具数"或"累计 token"触发都可以**。比如「累计 tool_result > 30 时触发」更直接。

**占位符设计**：源码用 `[Old tool result content cleared]`。这个字符串有几个特点值得借鉴：

- 短（10-12 token）
- 明确说明「这里有过内容，现在清了」（不是空字符串，避免模型困惑）
- 不暗示具体是什么工具的结果（保持简单）

如果你想更激进地节省 token，可以试试 `[cleared]` —— 但要测试模型是否还能理解这是什么意思。

**幂等检查**：必须有。否则同一 tool_result 被反复"清理"会导致 tokens_saved 误算，触发不该有的操作。

### 9.3 不要做的事

**不要试图清 model 的回复或 user 的文本**。MicroCompact 严格只动 tool_result 的 content。原因：

- 模型回复里有推理链、决策依据，丢了会让对话错乱
- user 文本是任务定义，丢了 task 都没了

**不要按"token 总数"触发 microcompact**。这是 AutoCompact 的工作。Microcompact 用「时间 / 数量」这种结构性触发，目的是平滑曲线（每轮清一点点），不是应急止血。

**不要在 forked / sub-agent 里跑客户端 microcompact**。除非你的 harness 里 sub-agent 用完全独立的状态。否则就像 cached MC 的注释警告的那样，全局状态污染会让主任务崩。

**不要在分析路径里跑**（比如你的 harness 有"统计当前消息 token 分布"的工具）。源码里通过「显式要求 querySource 非 undefined」防御这个。

### 9.4 与训练数据收集的交互

如果你的 harness 要为训练收集 trajectory：

- **保留**完整的原始 `tool_result.content`（在做 microcompact 之前）
- 训练时如果想模拟 microcompact 后的状态，按相同算法重新执行
- **不要保存压缩后的版本**当训练数据，否则模型学到的是「读到 `[cleared]` 占位符就停止」

具体做法可以是：保存原始消息 + 一个「压缩日志」（每次压缩做了什么），需要模拟时回放即可。

---

## 10. 速查

| 项目 | 值/位置 |
|---|---|
| 主体源码 | [services/compact/microCompact.ts](../../claude-code-typescript-src/services/compact/microCompact.ts) |
| Time-based 配置 | [services/compact/timeBasedMCConfig.ts](../../claude-code-typescript-src/services/compact/timeBasedMCConfig.ts) |
| API context management | [services/compact/apiMicrocompact.ts](../../claude-code-typescript-src/services/compact/apiMicrocompact.ts) |
| Cached MC（已 DCE）| `services/compact/cachedMicrocompact.ts` |
| 调用入口 | [query.ts:414](../../claude-code-typescript-src/query.ts#L414) `deps.microcompact()` |
| 占位符常量 | `'[Old tool result content cleared]'` |
| 白名单工具数（client）| 8（Read / Bash / Grep / Glob / WebSearch / WebFetch / FileEdit / FileWrite）|
| 白名单工具数（API clearable_results）| 6（不含 Edit / Write）|
| Time-based gap 阈值 | 60 分钟（默认，对齐 cache TTL）|
| Time-based 保留 | 5 个最近 |
| API trigger 阈值 | 180,000 input_tokens |
| API target | 40,000 input_tokens |
| 触发顺序 | time-based → cached MC → no-op |
| API context management 调用点 | [services/api/claude.ts:1633](../../claude-code-typescript-src/services/api/claude.ts#L1633) |
| 必需的 beta header | `cacheEditingBetaHeader`（cached MC）/ `CONTEXT_MANAGEMENT_BETA_HEADER`（API）|
| 仅主线程？ | ✓（time-based 严格要求，cached MC 也限制，API 路径无此限制）|
| 仅 firstParty？ | cached MC 是；time-based / API 都不是 |
| 调 LLM？ | ✗ 三条路径都不调 |

---

## 11. 学到这里你应该回答的问题

读完本篇你应该能回答：

1. **为什么 microcompact 要按时间或数量触发，而不是按总 token？**
   答：那是 AutoCompact 的工作。Microcompact 是平滑预防措施，每轮做一点小事，不是应急止血。

2. **为什么 COMPACTABLE_TOOLS 只有 8 个，不是所有工具？**
   答：白名单挑选标准是「结果可重新获取或不再需要」。其他工具（如 TodoWrite、AgentTool）的结果是不可重做的状态信息，不能清。

3. **为什么 time-based 触发后要 reset cached MC state？**
   答：cached MC 的状态记录了"哪些 tool_id 在服务端 cache 里"。time-based 改了本地消息让 cache 失效，cached MC state 立刻 stale，下一轮会试图删服务端不存在的工具。

4. **如果在 forked agent 里调 cached MC 会怎样？**
   答：fork 共享主进程的 module-level `cachedMCState`。fork 的工具调用注册到这个全局状态后，主线程下一轮会看到不属于自己对话的 tool_use_id，试图删除它们 → 删除失败或行为混乱。

5. **为什么 keepRecent 要 `Math.max(1, ...)`？**
   答：JS 的 `arr.slice(-0)` 反直觉地返回完整数组（因为 -0 === 0）。如果配置里 keepRecent 设成 0，本意是"全清"，实际变成"全留"。floor 在 1 既防御这个 bug，也保证模型至少有一个最近工具结果作为锚点。

如果以上都能回答，就可以进入第 16 篇 AutoCompact 详解。
