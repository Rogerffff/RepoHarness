# 第 17 篇：Reactive Compact — PTL 兜底与错误恢复管线

> 前面 13-16 篇讲的是「**预防性压缩**」（applyToolResultBudget / Snip / Microcompact / Context Collapse / AutoCompact）——它们都在 API 调用**之前**根据各种信号决定要不要压缩。
>
> Reactive Compact 是「**事后兜底**」——只有当 API 真的抛出 `prompt_too_long`（PTL）或 413 媒体错误后才介入。它存在的理由是承认一个事实：**客户端的 token 估算永远会有偏差**，预防性压缩做得再好也无法 100% 保证 API 不报错。
>
> 对 RepoHarness 来说，这一篇的核心借鉴价值是 **"永远要有错误兜底"** 这个设计哲学，以及具体的两个工程模式：**withholding（错误扣留）+ 按 round 切分**。

---

## 0. 一句话定义 + 关键数字

> **Reactive Compact = 当 API 返回 PTL/413 错误时，把错误从流中"扣留"不立刻给用户看，按 API round 分组从头丢弃旧消息，调摘要 LLM，恢复后重试。失败再重试最多 3 次，全失败才把错误真正 yield 出去。**

| 项目 | 值 / 出处 |
|---|---|
| 触发事件 | `prompt_too_long` 或 413 媒体大小错误 |
| 检测函数 | `isPromptTooLongMessage` / `isMediaSizeErrorMessage` |
| Token gap 解析 | `parsePromptTooLongTokenCounts` 解析 `"137500 tokens > 135000 maximum"` |
| 分组算法 | `groupMessagesByApiRound`（按 assistant message.id 切分）|
| Proactive PTL 重试上限 | 3 次 |
| Reactive PTL 重试 | 1 次（每次工具调用 turn 只跑一次）|
| Token gap 不可解析时的兜底 | 丢 20% 组 |
| 媒体错误恢复 | `stripImagesFromMessages` 把 image/document 替换为 `'[image]'` / `'[document]'` 占位 |
| Feature gate | `feature('REACTIVE_COMPACT')`（ant-only）|

---

## 1. 它为什么存在：客户端估算的固有偏差

第 16 篇讲过 AutoCompact 的阈值是 167K（200K Sonnet）。问题是：**这个 167K 是客户端用 `tokenCountWithEstimation` 算出来的，不是 API 真实的输入 tokens 数**。

两者的偏差来源：

| 偏差源 | 量级 |
|---|---|
| Tokenizer 估算误差（粗略 = `chars / 4 * 4/3`）| ±5-15% |
| System prompt 实际包含的 cache breaker、动态字段 | ±2-5K |
| Tools schema 在 API 端的精确编码 | ±1-3K |
| Beta header / context_management 字段开销 | ±1K |
| Cache breakpoints 增加的元数据 | ±2K |
| 浮动的 thinking budget 配置 | ±1K |

最坏情况叠加 → 客户端估算 165K，API 实际 200K+，触发 PTL。Reactive Compact 就是为这种情况存在的。

**对 RepoHarness 来说**，自己实现的 token 估算大概率比 Anthropic 的内部估算更粗，**预防性 + 反应式**两条路都必须有，仅靠预防压不住。

---

## 2. 完整调用链（最复杂的一条）

```
正常流程：
query.ts:454 → autocompact          (预防性压缩)
query.ts:659 → callModel
              ↓
              └─→ API 抛出 prompt_too_long / 413
              ↓
query.ts:799-822 流处理时 isWithheldPromptTooLong / isWithheldMediaSizeError → withheld = true
              ↓                                          (流式分支不立即 yield 错误)
              └─→ 流结束，主循环检查 lastMessage
              ↓
query.ts:1085-1118  isWithheld413
                ├─→ feature('CONTEXT_COLLAPSE') ?
                │     └─→ contextCollapse.recoverFromOverflow
                │           └─→ drain 已暂存 collapse → 成功就 retry
                │           └─→ 失败 → 继续到下一步
                ├─→ reactiveCompact.tryReactiveCompact
                │     ├─→ 摘要 + 重试
                │     └─→ 成功：用 postCompactMessages 替换 messagesForQuery，重新进主循环
                │     └─→ 失败（hasAttempted = true 或多次失败）：返回 null
                └─→ 都失败：yield lastMessage（让用户/SDK 看到错误），return
```

注意 **3 重 fallback** 的次序：

1. **Context Collapse drain**（最优先，最便宜）——只是排空已经准备好的 collapse 操作
2. **Reactive Compact**（要调 LLM）——真做摘要
3. **Surface error**（最后手段）——告诉用户/SDK 真不行了

---

## 3. Withholding（错误扣留）机制

[query.ts:799-822](../../claude-code-typescript-src/query.ts#L799-L822)：

```typescript
let withheld = false
if (feature('CONTEXT_COLLAPSE')) {
  if (contextCollapse?.isWithheldPromptTooLong(message, isPromptTooLongMessage, querySource)) {
    withheld = true
  }
}
if (reactiveCompact?.isWithheldPromptTooLong(message)) {
  withheld = true
}
if (mediaRecoveryEnabled && reactiveCompact?.isWithheldMediaSizeError(message)) {
  withheld = true
}
if (isWithheldMaxOutputTokens(message)) {
  withheld = true
}
if (!withheld) {
  yield yieldMessage      // ← 不被 withhold 的消息正常 yield
}
// 但被 withhold 的也会进入 assistantMessages 数组供后续恢复检查使用
if (message.type === 'assistant') {
  assistantMessages.push(message)
  ...
}
```

### 设计意图（[query.ts:166-179](../../claude-code-typescript-src/query.ts#L166-L179) 注释）

> If so, the streaming loop should withhold it from SDK callers until we know whether the recovery loop can continue. **Yielding early leaks an intermediate error to SDK callers** (e.g. cowork/desktop) that terminate the session on any `error` field — the recovery loop keeps running but nobody is listening.

如果错误被立刻 yield，SDK / 上游消费者会**误以为会话已经结束**，关闭 socket、清理状态、报告失败。但底层恢复逻辑可能还在跑——结果是恢复成功了，但已经没人在听。

**withholding 的关键约束**：扣留检查和恢复检查必须**用同一组判断条件**，否则会出现"扣留了但没人恢复"的状态——错误丢失。

代码里特地用了 `mediaRecoveryEnabled` 这个 hoisted 变量（[query.ts:626-627](../../claude-code-typescript-src/query.ts#L626-L627)）就是为了保证这点：扣留期间 GrowthBook flag 可能翻转（5-30s 流式时间窗），如果扣留时拿到 true、恢复时拿到 false，错误就消失了。

### 对 RepoHarness 的借鉴

任何**异步流式 + 错误恢复**的代码都该用 withholding 模式：

```python
# ❌ 反例：错误立刻 propagate
async for chunk in stream:
    if is_recoverable_error(chunk):
        try:
            recovered = await try_recover(chunk)
            yield recovered
        except RecoveryFailed:
            raise  # 错误 propagate
    else:
        yield chunk

# ✅ 正例：错误扣留，恢复或最终 surface
withheld_error = None
async for chunk in stream:
    if is_recoverable_error(chunk):
        withheld_error = chunk
        # 不 yield，继续消费流
    else:
        yield chunk

# 流结束后再决定
if withheld_error:
    recovered = await try_recover(withheld_error)
    if recovered:
        yield recovered
    else:
        yield withheld_error  # 真不行才 surface
```

---

## 4. groupMessagesByApiRound（按 round 而非 turn 切分）

[services/compact/grouping.ts](../../claude-code-typescript-src/services/compact/grouping.ts)：

```typescript
export function groupMessagesByApiRound(messages: Message[]): Message[][] {
  const groups: Message[][] = []
  let current: Message[] = []
  let lastAssistantId: string | undefined

  for (const msg of messages) {
    if (
      msg.type === 'assistant' &&
      msg.message.id !== lastAssistantId &&
      current.length > 0
    ) {
      groups.push(current)
      current = [msg]
    } else {
      current.push(msg)
    }
    if (msg.type === 'assistant') {
      lastAssistantId = msg.message.id
    }
  }
  if (current.length > 0) groups.push(current)
  return groups
}
```

### 关键概念：API round vs turn

```
Turn（用户视角）：一次"用户问 → agent 完成任务"算一轮
API round（API 视角）：一次"messages 发出 → assistant 响应回来"算一轮

一个 turn 里可能有多个 round：
  user: "修 auth.ts 的 bug"             ← turn 开始
  assistant: tool_use(Read auth.ts)     ← round 1 的 assistant
  user: tool_result                     ← round 1 的 user response
  assistant: tool_use(Edit auth.ts)     ← round 2 的 assistant
  user: tool_result                     ← round 2 的 user response  
  assistant: "修好了"                    ← round 3 的 assistant
                                        ← turn 结束
```

### 为什么按 round 切而不是按 turn

注释里说得很明白（[grouping.ts:14-21](../../claude-code-typescript-src/services/compact/grouping.ts#L14-L21)）：

> Replaces the prior human-turn grouping (boundaries only at real user prompts) with finer-grained API-round grouping, allowing reactive compact to operate on **single-prompt agentic sessions (SDK/CCR/eval callers)** where the entire workload is one human turn.

SWE agent 任务的典型形态：

```
user: "Fix issue #42 in this repo"     ← 唯一一次 user input
assistant: tool_use(Read README.md)
user: tool_result
assistant: tool_use(Grep "TODO")
user: tool_result
... (200 多个工具调用) ...
assistant: tool_use(Edit ...)
user: tool_result
assistant: "Done"
```

**整个任务只有 1 个 turn 但有 200+ rounds**。如果按 turn 分组，所有消息都在同一组，没法切。按 round 分组才有切分空间。

**对 RepoHarness 的借鉴**：SWE training 任务是 single-turn 的极端形态，做轨迹切分必须按 round 而不是 turn。

### 切分点的"配对安全"保证

注释里还有一个巧妙的设计（[grouping.ts:32-42](../../claude-code-typescript-src/services/compact/grouping.ts#L32-L42)）：

> 在格式良好的对话里，**API 契约保证每个 tool_use 都在下一个 assistant turn 之前被解决**——所以 lastAssistantId 单独足够当边界。追踪 unresolved tool_use IDs 只在对话格式不良（resume-from-partial-batch / max_tokens truncation）时才有用——而这种情况下追踪反而会让边界永远关闭，把所有后续 round 合成一个 group。

也就是说：**正常对话里，按 assistant id 切分天然就保证了 tool_use ↔ tool_result 配对完整**。这是 API 契约层面的不变量，不需要在切分代码里再做配对检查。

如果对话格式不良（hash 中断、resume）有 dangling tool_use，怎么办？答案是不在切分这一步处理，**让下游摘要 fork 的 `ensureToolResultPairing` 在 API 调用时修补**（[claude.ts:1136](../../claude-code-typescript-src/services/api/claude.ts#L1136)）。这是关注点分离：切分只管切，配对让 API 边界处理。

---

## 5. truncateHeadForPTLRetry（具体的丢弃算法）

[compact.ts:243-291](../../claude-code-typescript-src/services/compact/compact.ts#L243-L291)：

### 5.1 接口

```typescript
export function truncateHeadForPTLRetry(
  messages: Message[],
  ptlResponse: AssistantMessage,
): Message[] | null
```

输入：当前 messages + 出错的 PTL 响应（用于解析 token gap）
输出：截断后的新 messages，或 null（不能再截）

### 5.2 算法步骤

```typescript
// 1. 剥离上一次重试留下的合成 marker（防止它变成 group 0 让算法卡死）
const input = (messages[0] is PTL_RETRY_MARKER) ? messages.slice(1) : messages

// 2. 按 API round 分组
const groups = groupMessagesByApiRound(input)
if (groups.length < 2) return null     // 单组没法切

// 3. 解析 token gap
const tokenGap = getPromptTooLongTokenGap(ptlResponse)
//   parse "prompt is too long: 137500 tokens > 135000 maximum"
//   → gap = 137500 - 135000 = 2500

// 4. 计算丢几组
let dropCount: number
if (tokenGap !== undefined) {
  // 精确模式：累加最早的若干组直到覆盖 gap
  let acc = 0
  dropCount = 0
  for (const g of groups) {
    acc += roughTokenCountEstimationForMessages(g)
    dropCount++
    if (acc >= tokenGap) break
  }
} else {
  // Vertex/Bedrock 错误格式不一致，gap 解析失败
  // 兜底：丢 20% 的组
  dropCount = Math.max(1, Math.floor(groups.length * 0.2))
}

// 5. 至少留 1 组（不然没东西可摘要）
dropCount = Math.min(dropCount, groups.length - 1)
if (dropCount < 1) return null

// 6. 切片
const sliced = groups.slice(dropCount).flat()

// 7. 修补：被丢掉的 group 0 包含 system preamble，剩下的 groups 都以 assistant 起头
//    但 API 不接受 assistant-first 的 messages
//    → 在前面塞一个合成 user 消息
if (sliced[0]?.type === 'assistant') {
  return [
    createUserMessage({ content: PTL_RETRY_MARKER, isMeta: true }),
    ...sliced,
  ]
}
return sliced
```

### 5.3 一个具体例子

```
PTL 错误："prompt is too long: 215000 tokens > 200000 maximum"
→ gap = 15000

当前 messages 分组（按 round）：
  Group 0: [system preamble, user prompt]               ~12K tokens
  Group 1: [asst tool_use, user tool_result]            ~8K tokens
  Group 2: [asst tool_use, user tool_result]            ~3K tokens
  Group 3: [asst tool_use, user tool_result(big!)]      ~95K tokens
  Group 4: [asst tool_use, user tool_result]            ~5K tokens
  ... (Groups 5-30) ...
  Group 30: [asst tool_use(latest), user tool_result]   ~6K tokens

精确模式累加：
  acc = 0, drop = 0
  +Group 0: acc = 12K, drop = 1, 12K < 15K, 继续
  +Group 1: acc = 20K, drop = 2, 20K >= 15K, break
  
最终 dropCount = 2

sliced = groups[2:]  ← 从 Group 2 开始
       = [Group 2, Group 3, Group 4, ..., Group 30]

Group 2 第一条是 assistant → 前面加合成 user marker：
  [
    {role: user, isMeta: true, content: '[earlier conversation truncated for compaction retry]'},
    ...Group 2 ~ 30
  ]
```

### 5.4 PTL_RETRY_MARKER 的二次去除

注意算法第 1 步「剥离上一次重试留下的合成 marker」：

```typescript
const input = (messages[0] is PTL_RETRY_MARKER) ? messages.slice(1) : messages
```

为什么要这步？因为**重试可能多次**。第一次重试在头部插了 marker，第二次重试又要丢组——如果把 marker 当成 group 0 直接丢了，下次再进来又要插一个新的——20% 兜底模式会卡死（每次只丢 marker 不实质丢内容）。

每次进入重试，先把上一次的 marker 剥掉，重新分组再算丢几组，最后再插新 marker。

---

## 6. 媒体错误（413）的特殊路径

PTL 错误是上下文太长，按 round 切就能解决。**413 媒体大小错误是单条消息里的图像太大**，切再多组都没用——必须把图像本身处理掉。

### 6.1 检测

[services/api/errors.ts:133-149](../../claude-code-typescript-src/services/api/errors.ts#L133-L149)：

```typescript
export function isMediaSizeError(raw: string): boolean {
  return (
    (raw.includes('image exceeds') && raw.includes('maximum')) ||
    (raw.includes('image dimensions exceed') && raw.includes('many-image')) ||
    /maximum of \d+ PDF pages/.test(raw)
  )
}
```

3 种媒体错误模式：

1. 单图像超大：`"image exceeds <size> maximum"`
2. 图像总数超量：`"image dimensions exceed many-image"`
3. PDF 页数过多：`"maximum of N PDF pages"`

### 6.2 修复：剥离图像

[compact.ts:145-200](../../claude-code-typescript-src/services/compact/compact.ts#L145-L200) 的 `stripImagesFromMessages`：

```typescript
export function stripImagesFromMessages(messages: Message[]): Message[] {
  return messages.map(message => {
    if (message.type !== 'user') return message
    
    const newContent = content.flatMap(block => {
      if (block.type === 'image')    return [{ type: 'text', text: '[image]' }]
      if (block.type === 'document') return [{ type: 'text', text: '[document]' }]
      
      // 也处理嵌套在 tool_result 内的 image/document
      if (block.type === 'tool_result' && Array.isArray(block.content)) {
        const newToolContent = block.content.map(item => {
          if (item.type === 'image')    return { type: 'text', text: '[image]' }
          if (item.type === 'document') return { type: 'text', text: '[document]' }
          return item
        })
        return [{ ...block, content: newToolContent }]
      }
      return [block]
    })
    ...
  })
}
```

策略很直接：**所有 image/document 块替换为 `'[image]'` / `'[document]'` 文本占位符**。模型从此看不到真实媒体，但还知道"这里曾经有一张图"，可以基于这个继续推理。

### 6.3 为什么和 PTL 路径分开

[query.ts:1075-1077](../../claude-code-typescript-src/query.ts#L1075-L1077)：

> Unlike PTL, **media errors skip the collapse drain** — collapse doesn't strip images.

Context Collapse 是把消息折叠成摘要，不会处理图像。413 必须走 reactive compact 的 strip-retry 路径。

---

## 7. 一次重试上限：避免死循环

[query.ts:1119-1175](../../claude-code-typescript-src/query.ts#L1119-L1175)：

```typescript
if ((isWithheld413 || isWithheldMedia) && reactiveCompact) {
  const compacted = await reactiveCompact.tryReactiveCompact({
    hasAttempted: hasAttemptedReactiveCompact,    // ← 已经试过没？
    ...
  })

  if (compacted) {
    const next: State = {
      ...
      hasAttemptedReactiveCompact: true,           // ← 标记已试过
      transition: { reason: 'reactive_compact_retry' },
    }
    state = next
    continue
  }

  // No recovery — surface the withheld error and exit. Do NOT fall
  // through to stop hooks: the model never produced a valid response,
  // so hooks have nothing meaningful to evaluate. Running stop hooks
  // on prompt-too-long creates a death spiral: error → hook blocking
  // → retry → error → … (the hook injects more tokens each cycle).
  yield lastMessage
  return { reason: isWithheldMedia ? 'image_error' : 'prompt_too_long' }
}
```

### `hasAttemptedReactiveCompact` 标记的作用

每个工具调用 turn 只允许一次 reactive compact：

- 第一次 PTL → tryReactiveCompact，成功就重试
- 重试如果还 PTL → `hasAttempted` 已经是 true，tryReactiveCompact 直接返回 null
- 错误 surface 给用户

为什么不允许多次？因为如果第一次 reactive compact 后还 PTL，说明被保留的尾部消息本身就超长（比如刚 Read 了一个 50K token 的文件），再 reactive compact 也救不回来——继续重试只是徒劳浪费 LLM 调用。

### 关键不变量：错误 surface 时不跑 stop hooks

注释里说得明白：

> **Running stop hooks on prompt-too-long creates a death spiral: error → hook blocking → retry → error → …** (the hook injects more tokens each cycle).

如果让 stop hooks 跑，hooks 可能会：

1. 看到 error 想"我来注入一段恢复指令"
2. 注入更多 user 消息
3. 重试时上下文更长 → 又 PTL
4. 又触发 hooks → 注入更多 → 死循环

**所以 PTL 路径必须强制跳过 stop hooks 直接退出**。这是非常容易踩的坑——任何带"出错时调 hook"的设计都要考虑这种死循环。

---

## 8. 与 AutoCompact 的协作（preempt 互斥）

[query.ts:608-635](../../claude-code-typescript-src/query.ts#L608-L635) 这段最绕：

```typescript
// 当 reactiveCompact 启用 + autoCompact 启用时，跳过 blocking limit 检查
const collapseOwnsIt = feature('CONTEXT_COLLAPSE') && 
                       contextCollapse?.isContextCollapseEnabled() && 
                       isAutoCompactEnabled()

const mediaRecoveryEnabled = reactiveCompact?.isReactiveCompactEnabled() ?? false

if (
  !compactionResult &&
  querySource !== 'compact' &&
  querySource !== 'session_memory' &&
  !(reactiveCompact?.isReactiveCompactEnabled() && isAutoCompactEnabled()) &&
  !collapseOwnsIt
) {
  // Pre-empt: token 检查 → blocking limit → synthetic error
  if (isAtBlockingLimit) {
    yield createAssistantAPIErrorMessage({...})
    return
  }
}
```

**逻辑**：

- 默认情况：客户端在调 API 前先做 blocking limit 检查（177K），超了**主动**抛 PTL（合成错误）
- 如果 reactiveCompact 开了：**不做主动检查**，直接调 API，让真实 API 抛 PTL，再让 reactive compact 兜底
- 如果 contextCollapse 开了：同上

这种设计的精髓：**preempt 是为了对付 reactive compact 不存在的场景**（外部构建里没有 reactive compact，所以要主动抛错避免无效调用）。如果 reactive 兜底机制可用，**让真实 API 错误进来更好**——它带着精确的 token gap 信息，能精确指导 reactive compact 该丢多少。

---

## 9. 关键不变量

| 不变量 | 实现 / 出处 |
|---|---|
| **withholding 检查和恢复检查必须同步** | mediaRecoveryEnabled 等 hoisted 变量保证一次 turn 内 flag 不翻 |
| **PTL 时跳过 stop hooks** | 防止 hook 注入死循环 |
| **每个工具 turn 只一次 reactive compact** | hasAttemptedReactiveCompact 标记 |
| **dropCount 至少留 1 组** | `Math.min(dropCount, groups.length - 1)` |
| **dropCount 至少 1** | gap 极小时也要丢 |
| **Group 0 被丢后必须补合成 user** | API 不接受 assistant-first messages |
| **多次重试时剥离上一次的 marker** | 否则 marker 变成新 group 0 影响计数 |
| **按 API round 而非 turn 切分** | 支持 single-turn agentic 任务 |
| **media error 不走 collapse drain** | collapse 不处理图像 |
| **API round 切分天然保证 tool 配对** | 由 API 契约保证（lastAssistantId 边界），dangling 由下游 ensureToolResultPairing 修 |

---

## 10. 面向 RepoHarness 的实战要点

### 10.1 核心借鉴点：**永远要有 PTL 兜底**

这是整篇里最重要的一句话。SWE agent 的训练 trajectory 经常很长（几十到几百 tool 调用），客户端 token 估算的偏差累积下来 5-15% 是常态。即使你的预防压缩（autocompact）做得很好，**仍然会有 trajectory 在最末端的某个 tool_result 突然超限触发 PTL**。

没有兜底机制 = 这条 trajectory 直接死在 PTL，前面的工作全废，训练数据丢失。

### 10.2 推荐的最小兜底实现

```python
import re

PTL_RETRY_MARKER = "[earlier conversation truncated for retry]"

def parse_ptl_gap(error_message: str) -> int | None:
    """从 'prompt is too long: 215000 tokens > 200000 maximum' 解析 gap。"""
    m = re.search(r'(\d+)\s*tokens?\s*>\s*(\d+)', error_message, re.IGNORECASE)
    if not m:
        return None
    actual, limit = int(m.group(1)), int(m.group(2))
    return actual - limit if actual > limit else None


def group_by_api_round(messages: list[dict]) -> list[list[dict]]:
    """按 assistant id 切分（每次 API 响应是一组）。"""
    groups, current = [], []
    last_id = None
    for msg in messages:
        msg_id = msg.get("id") if msg["role"] == "assistant" else None
        if msg["role"] == "assistant" and msg_id != last_id and current:
            groups.append(current)
            current = [msg]
        else:
            current.append(msg)
        if msg["role"] == "assistant":
            last_id = msg_id
    if current:
        groups.append(current)
    return groups


def truncate_head_for_ptl_retry(messages: list[dict], ptl_error: str) -> list[dict] | None:
    """从 messages 头部丢若干 round，覆盖 PTL gap。"""
    # 剥离上一次重试的 marker
    if messages and messages[0].get("content") == PTL_RETRY_MARKER:
        messages = messages[1:]
    
    groups = group_by_api_round(messages)
    if len(groups) < 2:
        return None
    
    gap = parse_ptl_gap(ptl_error)
    if gap:
        # 累加最早的若干 group 直到覆盖 gap
        acc, drop = 0, 0
        for g in groups:
            acc += sum(estimate_tokens(m) for m in g)
            drop += 1
            if acc >= gap:
                break
    else:
        drop = max(1, len(groups) // 5)
    
    drop = min(drop, len(groups) - 1)
    if drop < 1:
        return None
    
    sliced = [m for g in groups[drop:] for m in g]
    if sliced and sliced[0]["role"] == "assistant":
        sliced = [{"role": "user", "content": PTL_RETRY_MARKER}, *sliced]
    return sliced


def safe_call_model(messages, system, tools, model_client, *, max_retries=3):
    """带 PTL 兜底的 LLM 调用。"""
    attempts = 0
    while attempts <= max_retries:
        try:
            return model_client.complete(
                model="...",
                system=system,
                messages=messages,
                tools=tools,
            )
        except PromptTooLongError as e:
            attempts += 1
            if attempts > max_retries:
                raise
            
            truncated = truncate_head_for_ptl_retry(messages, str(e))
            if truncated is None:
                raise   # 没法继续切，真的没救了
            messages = truncated
            
        except MediaSizeError:
            # 单独处理图像
            messages = strip_images(messages)
            attempts += 1
            if attempts > max_retries:
                raise


def strip_images(messages: list[dict]) -> list[dict]:
    """把消息里的 image/document 块替换为占位符。"""
    out = []
    for msg in messages:
        if msg["role"] != "user" or not isinstance(msg.get("content"), list):
            out.append(msg)
            continue
        new_content = []
        for block in msg["content"]:
            if block.get("type") == "image":
                new_content.append({"type": "text", "text": "[image]"})
            elif block.get("type") == "document":
                new_content.append({"type": "text", "text": "[document]"})
            elif block.get("type") == "tool_result" and isinstance(block.get("content"), list):
                # 嵌套处理
                inner = []
                for item in block["content"]:
                    if item.get("type") == "image":
                        inner.append({"type": "text", "text": "[image]"})
                    elif item.get("type") == "document":
                        inner.append({"type": "text", "text": "[document]"})
                    else:
                        inner.append(item)
                new_content.append({**block, "content": inner})
            else:
                new_content.append(block)
        out.append({**msg, "content": new_content})
    return out
```

约 100 行。这是 RepoHarness 必备的"PTL 急救包"。

### 10.3 与你之前的 AutoCompact 实现集成

记得第 16 篇我建议的混合压缩（早期摘要 + 最近保留）？把 reactive 兜底加上去：

```python
def safe_compact_and_call(messages, system, tools, model_client):
    # 1. 预防：autocompact（混合模式）
    if estimate_tokens(messages) >= AUTOCOMPACT_THRESHOLD:
        messages, _ = autocompact_with_keep_recent(messages, model_client)
    
    # 2. 调 API + PTL 兜底
    try:
        return safe_call_model(messages, system, tools, model_client, max_retries=3)
    except (PromptTooLongError, MediaSizeError) as e:
        # 兜底耗尽：记录 trajectory 到失败队列，但不要 crash 整个训练
        logger.error(f"PTL recovery exhausted: {e}")
        save_failed_trajectory(messages, error=str(e))
        return None  # 让上层决定怎么处理
```

### 10.4 不要复刻的部分

| 不要做 | 原因 |
|---|---|
| Withholding 流处理 | RepoHarness 大概率不需要支持 SDK callers，错误立刻处理就行 |
| Context Collapse drain 优先 | 你没有 collapse 系统 |
| `hasAttemptedReactiveCompact` 状态机 | 简单的 retry 计数足够 |
| 跳过 stop hooks 防死循环 | 你没有 stop hooks 系统 |
| `mediaRecoveryEnabled` hoisted gate | 你没有 GrowthBook 之类的运行时 flag 翻转 |

### 10.5 SWE harness 特有的注意点

1. **trajectory 收集时记录 PTL 事件**——这是有价值的训练信号（"哪些工具组合最容易触发 PTL"）
2. **bigfile tool_result 是常见 PTL 触发点**——可以在工具层面就限制单次输出，比 reactive 兜底更早
3. **media 错误在代码任务里少见，可以先不实现**——除非任务需要看截图/PDF
4. **保存失败的 trajectory**：reactive compact 失败的 trajectory 也是数据，不要丢

---

## 11. 速查

| 项目 | 值 / 位置 |
|---|---|
| 模块（DCE 删除）| `services/compact/reactiveCompact.ts` |
| 主调用入口 | [query.ts:1119](../../claude-code-typescript-src/query.ts#L1119) `reactiveCompact.tryReactiveCompact` |
| Withholding 检测 | [query.ts:799-822](../../claude-code-typescript-src/query.ts#L799-L822) |
| 切分算法 | [services/compact/grouping.ts](../../claude-code-typescript-src/services/compact/grouping.ts) `groupMessagesByApiRound` |
| 头部截断 | [services/compact/compact.ts:243](../../claude-code-typescript-src/services/compact/compact.ts#L243) `truncateHeadForPTLRetry` |
| 媒体剥离 | [services/compact/compact.ts:145](../../claude-code-typescript-src/services/compact/compact.ts#L145) `stripImagesFromMessages` |
| PTL 检测 | [services/api/errors.ts:64](../../claude-code-typescript-src/services/api/errors.ts#L64) `isPromptTooLongMessage` |
| Token gap 解析 | [services/api/errors.ts:104](../../claude-code-typescript-src/services/api/errors.ts#L104) `getPromptTooLongTokenGap` |
| 媒体错误检测 | [services/api/errors.ts:133](../../claude-code-typescript-src/services/api/errors.ts#L133) `isMediaSizeError` |
| 重试上限 | 3 次（proactive 路径）/ 1 次（reactive 路径，每 turn）|
| Token gap 解析失败兜底 | 丢 20% 组 |
| 合成 marker | `'[earlier conversation truncated for compaction retry]'` |
| 媒体占位符 | `'[image]'` / `'[document]'` |
| 错误后跳过 stop hooks | 必须，否则死循环 |
| Group 0 含 system preamble | 丢 group 0 后必须补 user marker |

---

## 12. 学到这里你应该回答的问题

1. **为什么 Reactive Compact 必须存在？AutoCompact 不就够了？**
   答：客户端 token 估算与 API 实际计算有 5-15% 偏差（tokenizer 误差 + cache breakpoints 元数据 + thinking budget 浮动等）。AutoCompact 阈值再保守，最坏情况下仍会偶发 PTL。Reactive 是承认"预防不可能 100% 准确"后的兜底。

2. **withholding 机制为什么必要？**
   答：API 错误如果立刻 yield 给 SDK callers，会触发它们的 session 关闭逻辑（因为有 `error` 字段）。即使底层恢复成功了，也没人在听。Withhold 期间内部恢复，恢复成功就装作什么都没发生过，失败再 surface。

3. **为什么按 API round 而不是 turn 切分？**
   答：SWE agent 等 single-prompt 工作负载里，整个长 trajectory 只有 1 个 turn 但有几十上百个 round。按 turn 切的话所有消息都在一组，没有切分空间。

4. **为什么 Group 0 被丢后要插一个合成 user 消息？**
   答：Group 0 包含 system preamble 和最初 user prompt。丢掉后 sliced 的第一条是 assistant，但 API 要求 messages 必须以 user 起头（assistant-first sequence is rejected）。

5. **PTL_RETRY_MARKER 为什么每次重试要先剥离再重新插？**
   答：上一次重试时插的 marker 是 isMeta user 消息，单独成一组（group 0）。如果不剥离，下一次 truncate 算法会把它当成正常 group 0 处理——20% 兜底模式只丢 marker（很小），实际 token 没释放，retry 又会 PTL，死循环。

6. **为什么 PTL 错误时要跳过 stop hooks？**
   答：stop hooks 可能注入额外 user 消息（比如"现在请总结你做了什么"）。这些注入的 token 让上下文变长，retry 时又 PTL，又触发 hooks 注入更多——指数增长的死循环。

如果以上都答得上，整套压缩系统的设计哲学你已经吃透了。下一步可以进 Session Memory 或者 AutoMem（跨会话记忆）。
