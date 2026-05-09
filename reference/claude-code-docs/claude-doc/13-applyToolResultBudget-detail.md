# 第 13 篇：applyToolResultBudget 详解——工具结果落盘与聚合预算

本篇是 [第 12 篇（上下文压缩管线的执行模型）](12-context-compaction-execution-flow.md) 的展开，专门讲压缩管线第一层 `applyToolResultBudget` 的实现细节。

读完应该能回答：
- 单个工具结果落盘和聚合预算是什么关系？
- 200K 的预算是按"全部历史"算，还是按"每条消息"算？
- 状态冻结（`ContentReplacementState`）为什么存在？它在保护什么？

---

## 1. 两层不同的机制

Claude Code 对工具结果的大小控制分**两层**，它们发生在不同时机、检查不同粒度：

| | 单个工具落盘 (`maybePersistLargeToolResult`) | 聚合预算 (`applyToolResultBudget`) |
|---|---|---|
| **检查对象** | 一个 tool_result block | 一条 wire-level user message 里所有 tool_result block 的总和 |
| **触发时机** | 工具执行完立刻（`processToolResultBlock` 返回之前） | 每轮主循环开头、发给模型之前（[query.ts:379](../../claude-code-typescript-src/query.ts)） |
| **阈值** | 每工具不同，系统上限 50K chars（`DEFAULT_MAX_RESULT_SIZE_CHARS`） | 统一 200K chars（`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS`） |
| **状态管理** | **无状态**——每次独立判断 | **有状态**——`ContentReplacementState` 冻结历史决定，保 prompt cache |
| **替换格式** | `<persisted-output>` 预览（~2KB） | 同上，完全一样 |
| **写入位置** | `<sessionDir>/tool-results/<id>.txt` | 同上，同一个目录 |
| **解决的场景** | 单个 Bash 输出 200K 行日志 | 模型并行调 10 个 Grep，每个 40K，单个没超 50K 但总计 400K |

---

## 2. 单个工具落盘：`maybePersistLargeToolResult`

### 2.1 调用链

```
工具执行完毕
  → processToolResultBlock()          // toolResultStorage.ts:205
    → getPersistenceThreshold()       // 算出这个工具的阈值
    → maybePersistLargeToolResult()   // toolResultStorage.ts:272
```

### 2.2 阈值怎么算

每个工具声明了自己的 `maxResultSizeChars`，系统侧常量如下（[toolLimits.ts](../../claude-code-typescript-src/constants/toolLimits.ts)）：

```
DEFAULT_MAX_RESULT_SIZE_CHARS = 50,000       // 50K chars，系统级上限
MAX_TOOL_RESULT_TOKENS        = 100,000      // 100K tokens
BYTES_PER_TOKEN                = 4           // 1 token ≈ 4 bytes
MAX_TOOL_RESULT_BYTES          = 400,000     // 400KB，最终兜底
```

实际阈值通过 `getPersistenceThreshold` 算（[toolResultStorage.ts:55](../../claude-code-typescript-src/utils/toolResultStorage.ts)）：

1. 工具声明 `maxResultSizeChars = Infinity` → **豁免**（典型如 Read 工具，自己有 `maxTokens` 限制）
2. GrowthBook 远程有覆盖值 → 用远程值
3. 否则 → `Math.min(工具声明值, 50K)`

比如 Bash 声明 30K → 阈值 30K；某工具声明 80K → 被 clamp 到 50K。

### 2.3 落盘做了什么

超阈值后，调用 `persistToolResult` 把原始内容写到 `<sessionDir>/tool-results/<tool_use_id>.txt`（如果是 JSON 结构则写 `.json`），用 `wx` flag 防重复写入。然后消息里替换成：

```
<persisted-output>
Output too large (195.3 KB). Full output saved to: /tmp/.../abc123.txt

Preview (first 2.0 KB):
[前 2000 字节的内容]
...
</persisted-output>
```

模型需要时可以自己用 Read 工具去取文件。

### 2.4 额外细节：空结果处理

如果工具返回空结果（比如静默成功的 shell 命令），`maybePersistLargeToolResult` 会注入占位符：

```
(Bash completed with no output)
```

原因：服务端渲染器在空 `tool_result` 后不会插 `\n\nAssistant:` marker，导致某些模型（比如 capybara）误以为是 turn boundary 而提前结束（[toolResultStorage.ts:280-286](../../claude-code-typescript-src/utils/toolResultStorage.ts) 的注释）。

---

## 3. 聚合预算：`applyToolResultBudget` → `enforceToolResultBudget`

### 3.1 在 query.ts 中的调用

```typescript
// query.ts:379-394
messagesForQuery = await applyToolResultBudget(
  messagesForQuery,
  toolUseContext.contentReplacementState,  // 跨轮次携带的状态
  persistReplacements
    ? records => void recordContentReplacement(records, toolUseContext.agentId)
    : undefined,  // 只有主线程/agent 才持久化替换记录到 transcript
  new Set(
    toolUseContext.options.tools
      .filter(t => !Number.isFinite(t.maxResultSizeChars))
      .map(t => t.name),
  ),  // Read 等 maxResultSizeChars=Infinity 的工具，跳过不处理
)
```

`applyToolResultBudget` 本身是一个薄封装（[toolResultStorage.ts:924](../../claude-code-typescript-src/utils/toolResultStorage.ts)），核心逻辑在 `enforceToolResultBudget`。

### 3.2 预算怎么算——按每条 wire-level user message 独立

**200K 的预算是按"每条 API 层面的 user message"独立检查的，不是把全部历史的工具结果加在一起。**

代码注释（[toolResultStorage.ts:747](../../claude-code-typescript-src/utils/toolResultStorage.ts)）明确写了：

> Messages are evaluated independently — a 150K result in one message and a 150K result in another are both under budget and untouched.

### 3.3 分组逻辑

`collectCandidatesByMessage`（[toolResultStorage.ts:600](../../claude-code-typescript-src/utils/toolResultStorage.ts)）按 **assistant 消息做分隔符**分组：

```
assistant(id=X)     ← 分隔符
  user(tool_result A)  ┐
  user(tool_result B)  ├── 一组，检查 A+B 是否 > 200K
  user(tool_result C)  ┘
assistant(id=Y)     ← 分隔符
  user(tool_result D)  ┐
  user(tool_result E)  ├── 另一组，检查 D+E 是否 > 200K
  user(tool_result F)  ┘
```

为什么按 assistant 分？因为 `normalizeMessagesForAPI` 会把两个 assistant 之间的所有连续 user 消息**合并成一条 wire-level user message** 发给 API。预算必须按同样的规则分组，否则你本地算的是 3 条各 80K 的小消息（都不超 200K），但 API 实际看到的是一条 240K 的合并消息。

注意：`progress` / `attachment` / `system` 等类型的消息**不会**打断分组，因为 `normalizeMessagesForAPI` 会过滤或合并它们，不会在 wire 层面创建新的消息边界。

### 3.4 替换选择

每组内的工具结果候选会经过过滤（跳过已落盘的、空的、包含图片的），然后：

1. 算组内总大小
2. 超过 200K → 按大小降序选，从最大的开始落盘替换，直到剩余 ≤ 200K（[selectFreshToReplace](../../claude-code-typescript-src/utils/toolResultStorage.ts)）

```typescript
const sorted = [...fresh].sort((a, b) => b.size - a.size)
for (const c of sorted) {
  if (remaining <= limit) break
  selected.push(c)
  remaining -= c.size
}
```

### 3.5 具体例子

```
Turn 1: 模型并行调 5 个 Grep，每个返回 45K
  → 一组：5 × 45K = 225K > 200K
  → 挑最大的 1 个落盘（-45K），剩 4 × 45K = 180K < 200K ✅

Turn 2: 模型调 1 个 Bash，返回 30K
  → 一组：30K < 200K
  → 不做任何事 ✅

Turn 3: 模型并行调 8 个 Read，每个返回 25K
  → Read 在 skipToolNames 里（maxResultSizeChars=Infinity），整组跳过 ✅
```

每组之间完全独立。Turn 1 的 180K 和 Turn 2 的 30K **不会**加在一起算。

---

## 4. 两层机制怎么配合

执行顺序：

```
1. 工具执行完 → maybePersistLargeToolResult 拦截单个超大结果
   比如 Bash 返回 200K → 落盘换预览（~2KB）

2. tool_result 进入消息数组

3. 下一轮主循环开头 → applyToolResultBudget 检查聚合大小
   此时单个超大的已经在第 1 步被处理了
   但如果有 5 个各 45K 的结果（单个没超 50K，总计 225K > 200K）
   → 挑最大的落盘，直到总量 ≤ 200K
```

关系是：**单个落盘是"即时拦截"，聚合预算是"回顾补刀"**。

`enforceToolResultBudget` 会跳过已被单个落盘处理过的结果（[toolResultStorage.ts:563](../../claude-code-typescript-src/utils/toolResultStorage.ts)）：

```typescript
if (isContentAlreadyCompacted(block.content)) return []
// ↑ 检查内容是否以 <persisted-output> 开头
```

所以第 1 步已经落盘换预览的那些（~2KB），第 2 步不会重复处理，也几乎不占预算。

---

## 5. 状态冻结保 prompt cache（最精妙的设计）

### 5.1 为什么需要状态

在 query loop **内部**，被替换过的消息通过 `state.messages` 带到下一次迭代，`isContentAlreadyCompacted` 会跳过它们，看起来已经固定了。

但问题出在**跨 `query()` 调用**的场景。`query()` 函数的调用方是 REPL（交互主循环）：

```
用户输入 "帮我改 bug"
  → REPL 调 query(messages=[...所有历史消息...])
    → query loop 内部:
        messagesForQuery = applyToolResultBudget(messages)  // ← 替换在局部变量上
        yield assistantMessage    // ← 原始消息 yield 给 REPL
        yield toolResultMessage   // ← 原始消息 yield 给 REPL
    → query() 结束

用户输入 "继续"
  → REPL 把之前 yield 出来的所有消息收集起来
  → REPL 调 query(messages=[...所有原始消息...])   // ← 注意：这里是原始的！
```

**REPL 存的是 yield 出来的原始消息**，不是 `messagesForQuery` 里被替换过的。所以新的 `query()` 调用拿到的历史 tool_result 还是原始内容。

如果没有状态冻结，第二次 `query()` 可能做出不同的替换决定（比如 GrowthBook 的预算阈值变了），导致发给 API 的消息前缀和上次不一样，**prompt cache 全部失效**。

### 5.2 `ContentReplacementState` 的结构

```typescript
type ContentReplacementState = {
  seenIds: Set<string>              // 所有见过的 tool_use_id
  replacements: Map<string, string> // 被替换过的 id → 精确的替换字符串
}
```

生命周期：一个实例挂在 `toolUseContext` 上，贯穿整个会话，跨 `query()` 调用存活。

### 5.3 三分类决策

每次 `enforceToolResultBudget` 遍历候选时，用 `partitionByPriorDecision`（[toolResultStorage.ts:649](../../claude-code-typescript-src/utils/toolResultStorage.ts)）分成三类：

| 分类 | 条件 | 处理方式 |
|---|---|---|
| **mustReapply** | `replacements.has(id)` = true | 用 Map 里缓存的字符串直接替换，零 I/O，字节级一致 |
| **frozen** | `seenIds.has(id)` = true 且不在 replacements 里 | 跳过，永远不替换（当初没替换，现在改了会破 cache） |
| **fresh** | 都不在 | 可以做新决定：超预算就替换，不超就标记为 seen |

**一旦命运被决定，后续所有轮次必须做同样的决定。**

### 5.4 Resume 场景

用户 `claude --resume` 时，消息从 transcript 加载。替换决定通过 `ContentReplacementRecord` 持久化在 transcript 里：

```typescript
type ContentReplacementRecord = {
  kind: 'tool-result'
  toolUseId: string
  replacement: string  // ← 存的是精确的替换字符串，不是重新生成的
}
```

为什么存精确字符串？因为如果代码更新了预览模板格式（比如 `formatFileSize` 的输出从 `195.3 KB` 变成 `195.31 KB`），重新生成的替换字符串会不一样，又会破 cache。

`reconstructContentReplacementState`（[toolResultStorage.ts:960](../../claude-code-typescript-src/utils/toolResultStorage.ts)）从记录重建状态：把所有历史 candidate 标记为 `seenIds`，把有记录的标记为 `replacements`。

### 5.5 子代理 fork 场景

`agentSummary` 等子代理 fork 主线程上下文时，用 `cloneContentReplacementState`（[toolResultStorage.ts:405](../../claude-code-typescript-src/utils/toolResultStorage.ts)）深拷贝。这样子代理发给 API 的消息前缀和主线程字节级一致，共享 prompt cache。

---

## 6. 速查

| 项目 | 值 |
|---|---|
| 单个工具落盘阈值 | `min(工具声明值, 50K)`，GrowthBook 可覆盖 |
| 聚合预算阈值 | 200K chars（`MAX_TOOL_RESULTS_PER_MESSAGE_CHARS`），GrowthBook flag `tengu_hawthorn_window` 可覆盖 |
| 预算粒度 | 每条 wire-level user message 独立 |
| 分组依据 | assistant 消息做分隔符，连续 user 消息归为一组 |
| 替换策略 | 从最大的开始落盘，直到组内总量 ≤ 预算 |
| 落盘位置 | `<sessionDir>/tool-results/<tool_use_id>.{txt,json}` |
| 预览大小 | 前 2000 字节 |
| 状态载体 | `ContentReplacementState`，挂在 `toolUseContext` 上 |
| 状态用途 | 保 prompt cache 前缀稳定（跨 query() 调用、resume、子代理 fork） |
| 豁免工具 | `maxResultSizeChars = Infinity` 的工具（如 Read），不参与聚合预算 |
| feature flag | `tengu_hawthorn_steeple`（总开关）、`tengu_hawthorn_window`（阈值覆盖）、`tengu_satin_quoll`（单工具阈值覆盖） |
| 源码入口 | [query.ts:379](../../claude-code-typescript-src/query.ts)、[toolResultStorage.ts:924](../../claude-code-typescript-src/utils/toolResultStorage.ts) |
