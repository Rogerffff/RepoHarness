# 第 14 篇：Snip Compact — 模型驱动的智能裁剪

> 在 [第 12 篇](12-context-compaction-execution-flow.md) 我把 Snip 简称为"消息级削减"，这个描述太机械化了。实际它是一套完全不同的设计：把"哪些消息可以丢"的决策**外包给模型自己**。

## 关于阅读顺序的回答

你先问的是：**按管线顺序（applyToolResultBudget → Snip → Microcompact → Context Collapse → AutoCompact → Reactive）了解 compact 是正确的吗？**

回答：**正确**，但 Snip 这一篇有两个特殊点要先讲清楚，否则容易看完产生错误的心理模型：

1. **Snip 是 ant-only（Anthropic 内部）feature**。源码快照（外部构建）里 `services/compact/snipCompact.ts`、`services/compact/snipProjection.ts`、`tools/SnipTool/` 三个目录全部被 dead code elimination 删除了。**普通用户跑的 claude code 里这套机制根本不存在**。
2. **Snip 的设计哲学和其他层不同**。其他层（applyToolResultBudget / Microcompact / AutoCompact）是「系统按规则压缩」，Snip 是「模型主动决策」。看完 Snip 再去看 Microcompact 反而能对比出"机械 vs 智能"两条思路的取舍。

所以学习价值仍然在——理解 Snip 是理解"为什么纯算法压缩有时不够"的最好教材。

> **方法论提醒**：本篇的源码定位都是从外围调用点（`query.ts`、`utils/messages.ts`、`QueryEngine.ts`）逆向推断的。SnipTool 主体不在快照里，所以涉及 snip 工具内部实现（比如它用什么算法选择保留哪些消息）的部分，是基于注释和接口的合理推断，不是直接读到代码。

---

## 1. 一句话定义

> **Snip = 一个模型可以主动调用的工具 + 给 user 消息加 ID 标签 + 本地保留 / API 投影的双视图。**

四个组件缺一不可：

```
┌─────────────────────────────────────────────────────────────┐
│ 组件 1: [id:xxx] 标签注入                                    │
│   每个发给 API 的 user 消息附加 6 字符短 ID                  │
│   utils/messages.ts:1620 appendMessageTagToUserMessage      │
├─────────────────────────────────────────────────────────────┤
│ 组件 2: SnipTool（模型可调用的工具）                         │
│   tools/SnipTool/  ← 源码已被 DCE 删除                       │
│   模型传入要保留的 ID 列表，被裁剪的消息打"snipped"标记      │
├─────────────────────────────────────────────────────────────┤
│ 组件 3: snipCompact (主体逻辑)                               │
│   services/compact/snipCompact.ts  ← 已被 DCE 删除           │
│   导出 snipCompactIfNeeded、isSnipRuntimeEnabled、           │
│        SNIP_NUDGE_TEXT                                       │
├─────────────────────────────────────────────────────────────┤
│ 组件 4: snipProjection（API 投影）                           │
│   services/compact/snipProjection.ts  ← 已被 DCE 删除        │
│   导出 projectSnippedView、isSnipBoundaryMessage             │
│   把"被 snip 但本地保留的"消息从 API 视图过滤掉              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 与 Microcompact 的本质差异（先看这个对比再读细节）

| 维度 | Snip | Microcompact |
|---|---|---|
| **决策方** | 模型自己（调用 SnipTool）| 系统自动 |
| **触发逻辑** | 模型判断「这条不重要了」| 时间 ≥ 60 分钟 OR 工具数 > 阈值 |
| **裁剪粒度** | 整条消息（含 assistant、tool_use 链）| 单个 tool_result 块的内容 |
| **影响范围** | 任意消息 | 只限 8 类工具的结果 |
| **本地副本** | ✓ REPL 保留完整 scrollback | ✗ time-based 真改本地；cached 不改 |
| **是工具？** | ✓ 模型显式调用 | ✗ 在主循环里隐式跑 |
| **兼容 cache？** | 投影方式不影响主消息体 | cached 路径专门为兼容 cache 设计 |
| **存在范围** | ant-only（外部构建里没有）| 所有用户 |

**一句话区分**：Microcompact 是「机械工」，看到旧 Read 结果就清；Snip 是「智能工」，让模型说「上面那段调试 X bug 的对话已经做完了，可以丢」。

---

## 3. 工作流程（具体例子）

### 3.1 全流程图

```
────────────────────────────────────────────────────────────────
轮次 N，模型回复完毕，user 输入下一个问题
────────────────────────────────────────────────────────────────
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ 主循环：normalizeMessagesForAPI       │
       │ 给每条非 isMeta user 消息附加         │
       │ [id:abc123] 标签                     │
       │ utils/messages.ts:2345-2363          │
       └──────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ snipCompactIfNeeded(messages)        │
       │ query.ts:403                         │
       │ - 重放上一次模型决定的 snip 操作      │
       │ - 计算 tokensFreed（用于 autocompact）│
       │ - 不删本地消息，只更新投影状态        │
       └──────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ 后续 microcompact、autocompact 都基于 │
       │ projectSnippedView 后的视图工作       │
       └──────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ 调用模型 API                          │
       │ 模型看到 [id:abc123] [id:def456] 等   │
       │ 标签                                  │
       └──────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ 模型决定：「id 为 abc123 / def456 /   │
       │ ghi789 的内容已经过时，调用 snip」    │
       │ → tool_use: SnipTool                 │
       │ → input: { keep_after: "xyz999" }    │
       │   或 { remove_ids: [...] }            │
       └──────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ SnipTool.call() 执行：                │
       │ - 在 mutableMessages 上标记被 snip    │
       │   的消息（不删除）                    │
       │ - 写入 snip boundary 系统消息         │
       │ - 返回成功                            │
       └──────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────┐
       │ 下一轮主循环                          │
       │ - REPL：projectSnippedView 把已 snip   │
       │   的消息从 API 视图过滤掉              │
       │   本地仍可滚动看                      │
       │ - SDK：snipReplay 直接 truncate       │
       │   mutableMessages（无 UI 不需保留）   │
       └──────────────────────────────────────┘
```

### 3.2 一个具体场景

```
轮次 5（已积累 60K tokens）
────────────────────────────────────────────
[id:001] 用户：帮我看看 auth.ts 的 bug
[id:002] 助手：调用 Read("auth.ts") → 返回 1500 行
[id:003] 助手：发现第 47 行 token 验证有问题
[id:004] 用户：先修一下，然后写个测试
[id:005] 助手：调用 FileEdit → 修复
[id:006] 助手：调用 Write("auth.test.ts") → 创建测试
[id:007] 用户：跑一下测试
[id:008] 助手：调用 Bash("npm test") → 全部通过
[id:009] 用户：好，现在帮我看 user.ts，里面也有类似问题
                                       ▲
                                       │
        模型看到 [id:001]-[id:008] 的工作已经完成
        决定：调用 snip 把它们从 API 视图移除
                                       │
                                       ▼
模型 tool_use:
  SnipTool({ keep_from_id: "009", reason: "auth bug 已修复并测试通过" })

────────────────────────────────────────────
下一轮主循环（轮次 6）
────────────────────────────────────────────
本地 mutableMessages（REPL 上下滚动可见）：
  [id:001]...[id:009] 全部保留
  + system: snip boundary

发给 API 的视图（projectSnippedView 投影后）：
  [id:009] 用户：好，现在帮我看 user.ts，里面也有类似问题
  + system: "注：之前的 auth.ts 调试已 snip 掉"

API 看到的 token 数 = 60K → 8K
```

注意三个关键点：
1. **本地完整保留**——用户随时滚动可以看到 auth 调试过程
2. **API 视图收缩**——模型不再被 60K 旧上下文干扰
3. **决策由模型做**——不是系统按规则裁剪，是模型说"我认为这部分已经完成"

---

## 4. [id:xxx] 标签注入机制

### 4.1 ID 怎么生成

[utils/messages.ts:200-205](../../claude-code-typescript-src/utils/messages.ts#L200-L205)：

```typescript
export function deriveShortMessageId(uuid: string): string {
  // Take first 10 hex chars from the UUID (skipping dashes)
  const hex = uuid.replace(/-/g, '').slice(0, 10)
  // Convert to base36 for shorter representation, take 6 chars
  return parseInt(hex, 16).toString(36).slice(0, 6)
}
```

**例子**：消息 UUID 是 `f47ac10b-58cc-4372-a567-0e02b2c3d479`：
1. 去掉横线、取前 10 位：`f47ac10b58`
2. 解析为整数：`1051040732504`
3. 转 base36：`db4mwc8`
4. 取前 6 位：**`db4mwc`**

最终在消息末尾追加 `\n[id:db4mwc]`。**确定性的**（同一 UUID 永远得到同一 ID），所以模型在不同轮看到的标签稳定，可以可靠引用。

### 4.2 何时注入

[utils/messages.ts:2345-2363](../../claude-code-typescript-src/utils/messages.ts#L2345-L2363)：

```typescript
// Append message ID tags for snip tool visibility (after all merging,
// so tags always match the surviving message's messageId field).
// Skip in test mode — tags change message content hashes, breaking
// VCR fixture lookup. Gate must match SnipTool.isEnabled() — don't
// inject [id:] tags when the tool isn't available (confuses the model
// and wastes tokens on every non-meta user message for every ant).
if (feature('HISTORY_SNIP') && process.env.NODE_ENV !== 'test') {
  const { isSnipRuntimeEnabled } =
    require('../services/compact/snipCompact.js') as ...
  if (isSnipRuntimeEnabled()) {
    for (let i = 0; i < sanitized.length; i++) {
      if (sanitized[i]!.type === 'user') {
        sanitized[i] = appendMessageTagToUserMessage(
          sanitized[i] as UserMessage,
        )
      }
    }
  }
}
```

注入有**双重 gate**：

| Gate | 类型 | 作用 |
|---|---|---|
| `feature('HISTORY_SNIP')` | 构建时（dead code elimination）| 外部构建时整个 if 块被删 |
| `isSnipRuntimeEnabled()` | 运行时（GrowthBook 之类）| 即使构建带了 snip，没启用也不注入 |

为什么要双重 gate？注释里写了：「不要在 SnipTool 不可用时注入 [id:] 标签——会困惑模型并在每条 user 消息上浪费 token」。这是一个**对外部模型的友好设计**：如果模型看到了 `[id:xxx]` 但又没有 SnipTool 可调用，它会困惑（这些标签是干什么用的？），同时每条消息都白白多 ~10 tokens。

### 4.3 只改 API 副本，不改本地

[utils/messages.ts:1615-1618](../../claude-code-typescript-src/utils/messages.ts#L1615-L1618)：

```typescript
/**
 * Appends a [id:...] message ID tag to the last text block of a user message.
 * Only mutates the API-bound copy, not the stored message.
 * This lets Claude reference message IDs when calling the snip tool.
 */
```

`normalizeMessagesForAPI` 是发送前的最后一步，输入是本地消息，输出是 API 副本。注入只在副本上发生。这个分层很关键——保证：
- REPL scrollback 永远不会显示给用户看到 `[id:db4mwc]` 这种系统标签
- 本地消息持久化（resume）也不会被污染

---

## 5. 双视图机制：本地保留 vs API 投影

### 5.1 投影函数

[utils/messages.ts:4630-4655](../../claude-code-typescript-src/utils/messages.ts#L4630-L4655)：

```typescript
/**
 * Returns messages from the last compact boundary onward (including the boundary).
 * If no boundary exists, returns all messages.
 *
 * Also filters snipped messages by default (when HISTORY_SNIP is enabled) —
 * the REPL keeps full history for UI scrollback, so model-facing paths need
 * both compact-slice AND snip-filter applied. Pass `{ includeSnipped: true }`
 * to opt out (e.g., REPL.tsx fullscreen compact handler which preserves
 * snipped messages in scrollback).
 */
export function getMessagesAfterCompactBoundary<T>(
  messages: T[],
  options?: { includeSnipped?: boolean },
): T[] {
  const boundaryIndex = findLastCompactBoundaryIndex(messages)
  const sliced = boundaryIndex === -1 ? messages : messages.slice(boundaryIndex)
  if (!options?.includeSnipped && feature('HISTORY_SNIP')) {
    const { projectSnippedView } = require('../services/compact/snipProjection.js')
    return projectSnippedView(sliced as Message[]) as T[]
  }
  return sliced
}
```

注释里点出了核心思想：**「REPL 保留完整历史以便 UI 滚动，所以面向模型的路径需要同时应用 compact-slice 和 snip-filter」**。

### 5.2 两个视图的对照

| 视图 | 谁用 | 包含被 snip 的消息？ |
|---|---|---|
| **本地 mutableMessages** | REPL 渲染、resume 持久化、命令历史 | ✓ 完整保留 |
| **API 投影**（`projectSnippedView`） | 模型请求、token 计数、压缩判断 | ✗ 过滤掉 |

调用时机：
- 默认（`includeSnipped: false`）：模型路径
- 显式 `includeSnipped: true`：REPL 全屏 compact handler 用，因为它要展示完整历史

### 5.3 SDK / 无界面 模式的差异（snipReplay）

[QueryEngine.ts:158-172](../../claude-code-typescript-src/QueryEngine.ts#L158-L172)：

```typescript
/**
 * Snip-boundary handler: receives each yielded system message plus the
 * current mutableMessages store. Returns undefined if the message is not a
 * snip boundary; otherwise returns the replayed snip result. Injected by
 * ask() when HISTORY_SNIP is enabled so feature-gated strings stay inside
 * the gated module (keeps QueryEngine free of excluded strings and testable
 * despite feature() returning false under bun test). SDK-only: the REPL
 * keeps full history for UI scrollback and projects on demand via
 * projectSnippedView; QueryEngine truncates here to bound memory in long
 * headless sessions (no UI to preserve).
 */
snipReplay?: (
  yieldedSystemMsg: Message,
  store: Message[],
) => { messages: Message[]; executed: boolean } | undefined
```

[QueryEngine.ts:898-915](../../claude-code-typescript-src/QueryEngine.ts#L898-L915)：

```typescript
case 'system': {
  // Snip boundary: replay on our store to remove zombie messages and
  // stale markers. The yielded boundary is a signal, not data to push —
  // the replay produces its own equivalent boundary.
  const snipResult = this.config.snipReplay?.(message, this.mutableMessages)
  if (snipResult !== undefined) {
    if (snipResult.executed) {
      this.mutableMessages.length = 0
      this.mutableMessages.push(...snipResult.messages)  // ← 直接 truncate
    }
    break
  }
  ...
}
```

**SDK 模式的不同**：

```
REPL 模式：
  mutableMessages: [全部消息保留]
                  ↓ 投影函数
  API 视图: [snip 过的版本]

SDK 模式（无 UI）：
  yielded snip boundary 触发 snipReplay
                  ↓ 直接覆写
  mutableMessages: [snip 过的版本]
  API 视图 = mutableMessages
```

为什么要这样？注释解释：「无 UI 要保留，长期 headless 会话里 mutableMessages 永远不收缩 = 内存泄漏」。SDK 模式下没人会回滚看历史，**保留完整历史就是纯内存浪费**。

### 5.4 注入方式：依赖注入而非直接 import

注意 `snipReplay` 是 `QueryEngine.config` 上的可选回调，**不是 QueryEngine 自己引用 snipModule**：

[QueryEngine.ts:1276-1284](../../claude-code-typescript-src/QueryEngine.ts#L1276-L1284)：

```typescript
...(feature('HISTORY_SNIP')
  ? {
      snipReplay: (yielded: Message, store: Message[]) => {
        if (!snipProjection!.isSnipBoundaryMessage(yielded)) return undefined
        return snipModule!.snipCompactIfNeeded(store, { force: true })
      },
    }
  : {}),
```

调用方在外面注入回调。注释解释为什么：「让 feature-gated 字符串留在 gated 模块里——保持 QueryEngine 没有被 excluded-strings 检查捕获的 marker，并在 bun test 下（feature() 返回 false）也能测试」。

这是一个很巧妙的解耦：QueryEngine 自身不知道 snip 存在，只接收一个"如果你看到 system 消息，先问一下这个回调要不要做点啥"的 hook。外部构建里这个回调始终是 undefined，QueryEngine 无感知。

---

## 6. 在主循环里的执行：`snipCompactIfNeeded`

[query.ts:400-410](../../claude-code-typescript-src/query.ts#L400-L410)：

```typescript
let snipTokensFreed = 0
if (feature('HISTORY_SNIP')) {
  queryCheckpoint('query_snip_start')
  const snipResult = snipModule!.snipCompactIfNeeded(messagesForQuery)
  messagesForQuery = snipResult.messages
  snipTokensFreed = snipResult.tokensFreed
  if (snipResult.boundaryMessage) {
    yield snipResult.boundaryMessage
  }
  queryCheckpoint('query_snip_end')
}
```

返回三个字段：

| 字段 | 含义 |
|---|---|
| `messages` | 处理后的消息数组（应用了投影） |
| `tokensFreed` | 这次操作释放了多少 token（关键，下面单独讲） |
| `boundaryMessage?` | 可选的 snip boundary 系统消息（yield 给 SDK 触发 snipReplay） |

### 6.1 它什么时候真"做事"

每轮都被调用，但大部分时候是 no-op。真做事的两种情况：

1. **上一轮模型调用了 SnipTool**——这一轮 `snipCompactIfNeeded` 重放那次决策，应用到当前消息数组
2. **`{ force: true }` 强制模式**——`/force-snip` 命令或 SDK snipReplay 触发，强制重新执行投影

**这就是为什么注释说 Snip 和 Microcompact "are not mutually exclusive"**（[query.ts:396](../../claude-code-typescript-src/query.ts#L396)）：它们各自在自己的判断标准下独立工作，没有 if-else 关系。

---

## 7. 与 AutoCompact 的协作：`tokensFreed` 的关键作用

### 7.1 为什么要传这个数

[query.ts:466](../../claude-code-typescript-src/query.ts#L466)：

```typescript
const { compactionResult, consecutiveFailures } = await deps.autocompact(
  messagesForQuery,
  toolUseContext,
  { ... },
  querySource,
  tracking,
  snipTokensFreed,  // ← 传给 autocompact
)
```

[query.ts:597-600](../../claude-code-typescript-src/query.ts#L597-L600) 的注释解释根因：

```
Same staleness applies to snip: subtract snipTokensFreed (otherwise we'd
falsely block in the window where snip brought us under autocompact threshold
but the stale usage is still above blocking limit — before this PR that
window never existed because autocompact always fired on the stale count).
```

### 7.2 用具体数字理解

```
场景：上下文 200K Sonnet，autocompact 阈值 167K

轮次 N（snip 之前）：
  protected-tail assistant.usage.input_tokens = 170K   ← API 报告
  本地消息总计 token                          = 170K   ← 一致

模型调用 SnipTool，标记 30K 消息为 snipped

轮次 N+1：
  本地 mutableMessages 仍 = 170K（保留）
  projectSnippedView 后    = 140K（投影）
  发给 API 的 token        = 140K
  
  但 protected-tail assistant.usage 还停留在 170K（snip 不会修改 assistant
  消息的 usage 字段，那是 API 历史响应的快照）

如果 autocompact 用 tokenCountWithEstimation（读 protected-tail）：
  读到 170K > 167K 阈值 → 触发 LLM 摘要！
  但实际只有 140K，根本不需要压缩 → 浪费 ~$0.05

修正后：
  170K - snipTokensFreed(30K) = 140K
  140K < 167K → 不触发 ✓
```

**核心问题**：`tokenCountWithEstimation` 读的是上一次 API 响应里的 usage 字段（快），不是真重新算 token（慢）。但 snip 是本地操作，不会让 API 响应里的 usage 缩小。所以必须显式传 `snipTokensFreed` 让阈值检查得到真实数。

### 7.3 同一修正还用在 blocking 检查

[query.ts:637-640](../../claude-code-typescript-src/query.ts#L637-L640)：

```typescript
const { isAtBlockingLimit } = calculateTokenWarningState(
  tokenCountWithEstimation(messagesForQuery) - snipTokensFreed,
  toolUseContext.options.mainLoopModel,
)
```

不修正的话同样的 false-positive：snip 已经把上下文降到安全区，但 blocking limit 检查仍读 stale 数据 → 错误地拒绝下一轮。

---

## 8. SNIP_NUDGE_TEXT：温和地引导模型

[utils/messages.ts:4148-4159](../../claude-code-typescript-src/utils/messages.ts#L4148-L4159)：

```typescript
case 'context_efficiency': {
  if (feature('HISTORY_SNIP')) {
    const { SNIP_NUDGE_TEXT } = require('../services/compact/snipCompact.js')
    return wrapMessagesInSystemReminder([
      createUserMessage({
        content: SNIP_NUDGE_TEXT,
        isMeta: true,
      }),
    ])
  }
  return []
}
```

`SNIP_NUDGE_TEXT` 的具体内容看不到（在 DCE 删除的模块里），但从注释和 attachment 名 `context_efficiency` 推断，大致是：

```
（推测内容）
当前对话已经积累了较多内容。如果之前完成的工作和现在的任务不相关，
你可以使用 snip 工具裁剪它们以提升上下文效率。
```

注入条件应该是「上下文增长到某个比例但还没到 autocompact 阈值」，作为温和的预警。这是**软性引导**：系统不强制做什么，只是提醒模型「有这个工具可用」。

---

## 9. 其他相关机制

### 9.1 静默吸收（不在 transcript 里显式渲染）

[utils/collapseReadSearch.ts:177-193](../../claude-code-typescript-src/utils/collapseReadSearch.ts#L177-L193)：

```typescript
// Meta-operations absorbed silently: Snip (context cleanup) and ToolSearch
// (lazy tool schema loading). Neither should break a collapse group or
// contribute to its count, but both stay visible in verbose mode.
if (
  (feature('HISTORY_SNIP') && toolName === SNIP_TOOL_NAME) ||
  (isFullscreenEnvEnabled() && toolName === TOOL_SEARCH_TOOL_NAME)
) {
  return {
    isCollapsible: true,
    isAbsorbedSilently: true,
    ...
  }
}
```

意思是：在 transcript 里渲染时，snip 调用被视为"元操作"——不打断"这个 turn 是 5 次 Read"的折叠分组，也不被计入。但 verbose 模式下仍可见。

### 9.2 isMeta 合并保护

[utils/messages.ts:2411-2438](../../claude-code-typescript-src/utils/messages.ts#L2411-L2438)：

```typescript
export function mergeUserMessages(a: UserMessage, b: UserMessage): UserMessage {
  ...
  if (feature('HISTORY_SNIP')) {
    const { isSnipRuntimeEnabled } = require(...)
    if (isSnipRuntimeEnabled()) {
      return {
        ...a,
        isMeta: a.isMeta && b.isMeta ? (true as const) : undefined,
        // 只有 a 和 b 都是 meta，结果才是 meta
      }
    }
  }
  ...
}
```

注释解释：「合并消息只有所有操作数都是 meta 时结果才是 meta。任何真实 user 内容都不能被错误标记为 isMeta（否则不会注入 [id:] 标签，被视为用户不可见内容）」。

这是个细节但很关键——**isMeta 是不注入 [id:] 标签的依据**（见 [messages.ts:1621-1623](../../claude-code-typescript-src/utils/messages.ts#L1621-L1623)）。如果合并把真消息错标为 meta，那条消息就没有 ID，模型无法 snip 它 → 永远占着上下文。

### 9.3 用户手动触发：/force-snip 命令

[commands.ts:83-84](../../claude-code-typescript-src/commands.ts#L83-L84)：

```typescript
const forceSnip = feature('HISTORY_SNIP')
  ? require('./commands/force-snip.js').default
```

让用户主动触发——比如对话明显冗长但模型迟迟不主动 snip 时，用户可以介入。

---

## 10. 关键不变量

| 不变量 | 为什么重要 | 在哪里维护 |
|---|---|---|
| `[id:]` 标签只在 API 副本上 | 防止污染本地 / scrollback / 持久化 | `appendMessageTagToUserMessage` 只在 `normalizeMessagesForAPI` 调 |
| `isSnipRuntimeEnabled()` 与 `SnipTool.isEnabled()` 必须同步 | 不要给模型看 ID 但又没工具用 | gate 逻辑写在 messages.ts:2348-2350 注释 |
| 合并消息 `isMeta` 是 AND 而非 OR | 真用户内容必须被注入 [id:] | `mergeUserMessages` 内特殊处理 |
| `tokensFreed` 必须传到所有 token 检查点 | 否则 staleness false-positive | autocompact 和 blocking 都要用 |
| 投影只删 API 视图，不删本地 | REPL scrollback 完整 | `getMessagesAfterCompactBoundary` 默认 `includeSnipped: false` |
| SDK 模式 truncate mutableMessages | 防长会话内存泄漏 | `snipReplay` 回调注入 |

---

## 11. 速查

| 项目 | 值/位置 |
|---|---|
| 是否默认启用 | ✗（feature gate `HISTORY_SNIP` + 运行时 `isSnipRuntimeEnabled`，外部构建里不存在）|
| 调用位置 | [query.ts:401-410](../../claude-code-typescript-src/query.ts#L401-L410) |
| 主体模块（已 DCE）| `services/compact/snipCompact.ts` |
| 投影模块（已 DCE）| `services/compact/snipProjection.ts` |
| 工具实现（已 DCE）| `tools/SnipTool/` |
| ID 算法 | UUID 前 10 hex → base36 → 取 6 字符 |
| ID 注入位置 | [utils/messages.ts:1620](../../claude-code-typescript-src/utils/messages.ts#L1620) |
| 双 gate | 构建 `feature('HISTORY_SNIP')` + 运行时 `isSnipRuntimeEnabled()` |
| 协作 token | `snipTokensFreed` 传给 autocompact ([query.ts:466](../../claude-code-typescript-src/query.ts#L466)) 和 blocking ([query.ts:638](../../claude-code-typescript-src/query.ts#L638)) |
| REPL 行为 | mutableMessages 完整保留，每次发 API 时投影 |
| SDK 行为 | snipReplay 回调直接 truncate mutableMessages |
| 用户可见命令 | `/force-snip`（强制立即 snip）|
| 软引导 | `SNIP_NUDGE_TEXT` 通过 `context_efficiency` attachment 注入 |
| 静默吸收 | snip 调用在 transcript 折叠中不计数 |

---

## 12. 阅读顺序回应

回到开头的问题：

**Q：按管线顺序了解 compact 是正确的吗？**

A：**正确**。但读完 Snip 这一篇你可以做一次心理模型校准：

```
读 Snip 之前的隐含假设：
  「压缩 = 系统按规则自动裁剪」

读 Snip 之后的更准确认知：
  「压缩有两种范式 —— 算法驱动 & 模型驱动。
   Snip 是后者唯一的代表，其他所有层都是前者。」
```

这个区分会帮你后面读 Microcompact / AutoCompact / Reactive 时建立正确预期：**它们都不是 Snip 那种"让模型决定丢什么"，而是机械按规则跑**。

下一步建议读 [Microcompact 详解（待写）](15-microcompact-detail.md)——刚好用 Snip 的"模型驱动"作为对照，理解 Microcompact 的"机械按 8 类工具白名单清旧结果"是另一种取舍。

---

## 附录：源码限制声明

本篇的关键模块（`snipCompact.ts`、`snipProjection.ts`、`SnipTool/`）在源码快照里被 dead code elimination 完全删除。本文的内部实现描述（如 `snipCompactIfNeeded` 的具体重放逻辑、SnipTool 的输入 schema、`projectSnippedView` 的过滤算法）都是从外围调用点（`query.ts`、`QueryEngine.ts`、`utils/messages.ts`、`utils/collapseReadSearch.ts`、`commands.ts`、`tools.ts`）的引用方式和注释逆向推断的合理设计，不是直接读到代码。

如果未来源码快照恢复了 Snip 模块，建议核对以下推断点：

- [ ] SnipTool 的 input schema（`keep_from_id` / `remove_ids` / 其他形式）
- [ ] `snipCompactIfNeeded` 在非强制模式下的"何时真做事"判断
- [ ] `projectSnippedView` 是按消息 ID 过滤还是按其他标记
- [ ] `tokensFreed` 是真算每次释放还是累计差值
- [ ] `SNIP_NUDGE_TEXT` 的具体内容
- [ ] `isSnipRuntimeEnabled()` 的判断条件（GrowthBook flag？环境变量？）
