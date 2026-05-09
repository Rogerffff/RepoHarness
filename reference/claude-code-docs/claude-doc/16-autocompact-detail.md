# 第 16 篇：AutoCompact — 9 段摘要、Session Memory 优先、熔断保护

> 这是整套压缩系统里**最复杂、最贵、也最关键**的一层。前面几层（applyToolResultBudget / Snip / Microcompact / Context Collapse）都是「机会主义」，AutoCompact 是「应急止血」——上下文真满了，必须压。
>
> 对 RepoHarness 来说，这一篇核心借鉴价值是 **9 段摘要 prompt 模板** 和 **fork agent 共享 prompt cache 的范式**。其他细节（熔断器事故数据、PTL 重试、cache 监控集成）是工业级生产经验，不一定都要复刻，但读完会知道生产系统会踩到什么坑。

---

## 0. 一句话定义 + 关键数字

> **AutoCompact = 当 token 数达到阈值时，fork 一个共享 prompt cache 的子代理，让它读完整对话，按 9 段结构化模板写出摘要，替换历史。**

| 项目 | 值 | 来源 |
|---|---|---|
| 触发阈值（200K 模型）| 167,000 tokens | `getAutoCompactThreshold()` |
| 阻塞硬限 | 177,000 tokens | `MANUAL_COMPACT_BUFFER_TOKENS = 3,000` |
| 摘要输出预留 | 20,000 tokens | `MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20,000` |
| AutoCompact 缓冲 | 13,000 tokens | `AUTOCOMPACT_BUFFER_TOKENS = 13,000` |
| 警告级缓冲 | 20,000 tokens | `WARNING_THRESHOLD_BUFFER_TOKENS = 20,000` |
| 熔断阈值 | 连续 3 次失败 | `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` |
| PTL 重试上限 | 3 次 | `MAX_PTL_RETRIES = 3` |
| Post-compact 文件恢复上限 | 5 个 | `POST_COMPACT_MAX_FILES_TO_RESTORE = 5` |
| Post-compact 文件 token 预算 | 50K（单文件 ≤ 5K）| `POST_COMPACT_TOKEN_BUDGET = 50_000` |
| Post-compact 技能 token 预算 | 25K（单技能 ≤ 5K）| `POST_COMPACT_SKILLS_TOKEN_BUDGET = 25_000` |

---

## 1. 完整调用链

```
query.ts:454
  └─→ deps.autocompact()
        └─→ autoCompactIfNeeded()  [autoCompact.ts:241]
              ├─→ DISABLE_COMPACT 环境变量检查
              ├─→ 熔断器检查（consecutiveFailures >= 3 → 跳过）
              ├─→ shouldAutoCompact()  [autoCompact.ts:160]
              │     ├─ querySource 递归保护
              │     ├─ isAutoCompactEnabled()
              │     ├─ reactive-only 模式抑制
              │     ├─ context-collapse 模式抑制
              │     └─ token >= 阈值？
              │
              ├─→ trySessionMemoryCompaction()  [优先]
              │     └─ 找到 session memory 笔记 → 直接当摘要 → 0 LLM 成本
              │
              └─→ compactConversation()  [compact.ts:387]  [回退]
                    ├─ PreCompact hooks
                    ├─ getCompactPrompt()  → 9 段 prompt
                    ├─ streamCompactSummary 循环
                    │     ├─ runForkedAgent (共享 prompt cache, 优先)
                    │     └─ 普通 streaming (fallback)
                    │     └─ PTL 时 truncateHeadForPTLRetry，最多 3 次
                    ├─ formatCompactSummary  剥离 <analysis>
                    ├─ 清 readFileState + loadedNestedMemoryPaths
                    ├─ 并行生成附件
                    │     ├─ createPostCompactFileAttachments (≤5 文件)
                    │     ├─ createAsyncAgentAttachmentsIfNeeded
                    │     ├─ createPlanAttachmentIfNeeded
                    │     ├─ createPlanModeAttachmentIfNeeded
                    │     ├─ createSkillAttachmentIfNeeded
                    │     ├─ getDeferredToolsDeltaAttachment
                    │     ├─ getAgentListingDeltaAttachment
                    │     └─ getMcpInstructionsDeltaAttachment
                    ├─ SessionStart hooks
                    └─ 组装 boundaryMarker + summaryMessages + attachments + hookResults

  └─→ runPostCompactCleanup()  [postCompactCleanup.ts:31]
        └─ 清 8 类缓存（见第 12 篇）

  └─→ notifyCompaction()  [防止 cache break detector 误报]
```

---

## 2. shouldAutoCompact 的 5 重 guard

[autoCompact.ts:160-239](../../claude-code-typescript-src/services/compact/autoCompact.ts#L160-L239)，按顺序：

### 2.1 querySource 递归保护

```typescript
// session_memory and compact are forked agents that would deadlock.
if (querySource === 'session_memory' || querySource === 'compact') {
  return false
}
// marble_origami is the ctx-agent — if ITS context blows up and
// autocompact fires, runPostCompactCleanup calls resetContextCollapse()
// which destroys the MAIN thread's committed log.
if (feature('CONTEXT_COLLAPSE')) {
  if (querySource === 'marble_origami') {
    return false
  }
}
```

3 个 querySource 必须排除：

| querySource | 为什么不能压缩 |
|---|---|
| `session_memory` | 会话记忆提取自身就是 fork 子代理，递归 |
| `compact` | autocompact 自己产生的 fork 子代理，递归 |
| `marble_origami` | context-collapse 的 ctx-agent；它的 cleanup 会清主线程共享状态 |

### 2.2 全局开关

```typescript
if (!isAutoCompactEnabled()) return false
```

[autoCompact.ts:147-158](../../claude-code-typescript-src/services/compact/autoCompact.ts#L147-L158)：

```typescript
export function isAutoCompactEnabled(): boolean {
  if (isEnvTruthy(process.env.DISABLE_COMPACT)) return false
  if (isEnvTruthy(process.env.DISABLE_AUTO_COMPACT)) return false   // 仅禁自动，保留手动
  return getGlobalConfig().autoCompactEnabled
}
```

两个环境变量：
- `DISABLE_COMPACT`：全部禁用（连 `/compact` 都不能用）
- `DISABLE_AUTO_COMPACT`：只禁自动触发，保留手动 `/compact`

### 2.3 reactive-only 模式抑制

```typescript
if (feature('REACTIVE_COMPACT')) {
  if (getFeatureValue_CACHED_MAY_BE_STALE('tengu_cobalt_raccoon', false)) {
    return false
  }
}
```

`tengu_cobalt_raccoon` 是个 GrowthBook 实验：**禁主动压缩，让反应式压缩（PTL）兜底**。验证"等到 API 真报错再压缩 vs 提前预防性压缩"哪个更好。

### 2.4 context-collapse 模式抑制

```typescript
if (feature('CONTEXT_COLLAPSE')) {
  const { isContextCollapseEnabled } = require('../contextCollapse/index.js')
  if (isContextCollapseEnabled()) {
    return false
  }
}
```

注释里的核心理由（[autoCompact.ts:201-209](../../claude-code-typescript-src/services/compact/autoCompact.ts#L201-L209)）：

> Context-collapse 启用时它接管整个上下文管理 —— 90% 启动 commit / 95% 阻塞 spawn 的流程负责剩余空间问题。AutoCompact 在 effective-13K（~93% effective）触发，正好夹在 collapse 的 commit-start (90%) 和 blocking (95%) 之间，**会和 collapse 抢资源且通常赢**，毁掉 collapse 即将保存的细粒度上下文。

如果你的 harness 决定用「分层压缩」策略，要避免不同层在阈值上互相打架。

### 2.5 真正的阈值检查

```typescript
const tokenCount = tokenCountWithEstimation(messages) - snipTokensFreed
const threshold = getAutoCompactThreshold(model)
const { isAboveAutoCompactThreshold } = calculateTokenWarningState(tokenCount, model)
return isAboveAutoCompactThreshold
```

注意 `- snipTokensFreed`——前面第 14 篇讲过，snip 释放的 token 不在 protected-tail 的 usage 字段里反映，必须显式减掉。

---

## 3. 阈值数学（200K Sonnet 具体例子）

[autoCompact.ts:33-49, 72-91, 93-145](../../claude-code-typescript-src/services/compact/autoCompact.ts#L33-L145)：

```
contextWindow                     = 200,000   原始模型上下文
- MAX_OUTPUT_TOKENS_FOR_SUMMARY  = 20,000    留给摘要输出
─────────────────────────────────────────
有效窗口 effectiveContextWindow   = 180,000

- AUTOCOMPACT_BUFFER_TOKENS      = 13,000
─────────────────────────────────────────
触发阈值 autoCompactThreshold    = 167,000   达到就触发

- WARNING_THRESHOLD_BUFFER       = 20,000
─────────────────────────────────────────
警告阈值 warningThreshold        = 147,000   黄/红警告

效果窗口 - MANUAL_COMPACT_BUFFER  = 177,000   阻塞硬限（如果 autocompact 关闭）
```

> 注释 [autoCompact.ts:28-29](../../claude-code-typescript-src/services/compact/autoCompact.ts#L28-L29) 解释 `MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000` 是**根据生产数据 p99.99 的摘要输出长度（17,387 tokens）选的**。这是真实统计驱动的常数，不是拍脑袋。

调试用的环境变量：

- `CLAUDE_CODE_AUTO_COMPACT_WINDOW`：覆盖 contextWindow 的下限（用更小窗口测试）
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`：按百分比覆盖阈值
- `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE`：覆盖阻塞硬限

---

## 4. 熔断器（生产事故催生）

[autoCompact.ts:67-70](../../claude-code-typescript-src/services/compact/autoCompact.ts#L67-L70)：

```typescript
// Stop trying autocompact after this many consecutive failures.
// BQ 2026-03-10: 1,279 sessions had 50+ consecutive failures (up to 3,272)
// in a single session, wasting ~250K API calls/day globally.
const MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3
```

**这是一个真实事故的产物**：1279 个会话连续失败 ≥50 次，单会话最多 3272 次，全球每天浪费 25 万次 API 调用。事故发生在 2026-03-10。

熔断逻辑（[autoCompact.ts:260-265, 334-349](../../claude-code-typescript-src/services/compact/autoCompact.ts#L260-L349)）：

```typescript
// 检查
if (tracking?.consecutiveFailures !== undefined &&
    tracking.consecutiveFailures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES) {
  return { wasCompacted: false }
}

// 失败计数
catch (error) {
  const prevFailures = tracking?.consecutiveFailures ?? 0
  const nextFailures = prevFailures + 1
  if (nextFailures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES) {
    logForDebugging(`autocompact: circuit breaker tripped...`, { level: 'warn' })
  }
  return { wasCompacted: false, consecutiveFailures: nextFailures }
}

// 成功重置
return {
  wasCompacted: true,
  compactionResult,
  consecutiveFailures: 0,        // ← 成功就清零
}
```

**RepoHarness 借鉴**：任何会重复触发 LLM 调用的逻辑都该有熔断保护。规则：

1. 设一个低位阈值（3 次足够，5 次就太多）
2. 失败计数累加，成功立刻清零（不要"指数退避"——指数退避适合临时网络故障，熔断保护是为了防系统性失败）
3. 触发熔断后**完全停**而不是降级——因为系统性失败说明前提就错了，降级也救不回来

---

## 5. Session Memory 优先策略（重要！）

[autoCompact.ts:287-310](../../claude-code-typescript-src/services/compact/autoCompact.ts#L287-L310)：

```typescript
// EXPERIMENT: Try session memory compaction first
const sessionMemoryResult = await trySessionMemoryCompaction(
  messages,
  toolUseContext.agentId,
  recompactionInfo.autoCompactThreshold,
)
if (sessionMemoryResult) {
  setLastSummarizedMessageId(undefined)
  runPostCompactCleanup(querySource)
  if (feature('PROMPT_CACHE_BREAK_DETECTION')) {
    notifyCompaction(querySource ?? 'compact', toolUseContext.agentId)
  }
  markPostCompaction()
  return {
    wasCompacted: true,
    compactionResult: sessionMemoryResult,
  }
}
```

**思路**：会话记忆系统已经在后台持续写笔记。压缩时先看「现成的笔记够不够当摘要」——如果够，直接拿来替换历史，**0 LLM 成本**。

只有 `trySessionMemoryCompaction` 返回 null（笔记不存在 / 太旧 / 不够覆盖）才走传统路径调 LLM 摘要。Session Memory 自身会单独写一篇详解。

**RepoHarness 借鉴**：如果你的 harness 在后台持续提取轨迹笔记/状态摘要，压缩时**先复用已有产物**再考虑临时生成。区分「持续低频积累」和「应急高频触发」两种摘要工具。

---

## 6. compactConversation 主流程（7 步）

[compact.ts:387-770](../../claude-code-typescript-src/services/compact/compact.ts#L387-L770)：

### 6.1 PreCompact hooks（用户钩子介入）

```typescript
const hookResult = await executePreCompactHooks(
  { trigger: isAutoCompact ? 'auto' : 'manual', customInstructions: ... },
  context.abortController.signal,
)
customInstructions = mergeHookInstructions(customInstructions, hookResult.newCustomInstructions)
```

用户可以在配置里挂 hook 改变压缩 prompt。比如插入一段「关注 TypeScript 代码改动，记录修复过的 bug」的额外指令。

### 6.2 摘要生成（streamCompactSummary 循环）

```typescript
let messagesToSummarize = messages
let ptlAttempts = 0
for (;;) {
  summaryResponse = await streamCompactSummary({ messages: messagesToSummarize, ... })
  summary = getAssistantMessageText(summaryResponse)
  if (!summary?.startsWith(PROMPT_TOO_LONG_ERROR_MESSAGE)) break

  // CC-1180: compact 请求自身 PTL 了，按 round 丢最旧重试
  ptlAttempts++
  const truncated = ptlAttempts <= MAX_PTL_RETRIES
    ? truncateHeadForPTLRetry(messagesToSummarize, summaryResponse)
    : null
  if (!truncated) {
    throw new Error(ERROR_MESSAGE_PROMPT_TOO_LONG)
  }
  messagesToSummarize = truncated
  retryCacheSafeParams = { ...retryCacheSafeParams, forkContextMessages: truncated }
}
```

**事故案例 CC-1180**：摘要请求自身可能也超长（比如对话本身就过 200K，加上 prompt 模板就更超）。`truncateHeadForPTLRetry` 按 API round 分组丢最旧的重试，最多 3 次。详见后续 Reactive Compact 篇。

### 6.3 清缓存

```typescript
const preCompactReadFileState = cacheToObject(context.readFileState)  // 先备份
context.readFileState.clear()
context.loadedNestedMemoryPaths?.clear()
```

注意先**备份**。备份用于第 4 步生成文件附件——不读过的文件不重建，读过的才需要恢复。

### 6.4 并行生成附件

```typescript
const [fileAttachments, asyncAgentAttachments] = await Promise.all([
  createPostCompactFileAttachments(preCompactReadFileState, context, POST_COMPACT_MAX_FILES_TO_RESTORE),
  createAsyncAgentAttachmentsIfNeeded(context),
])
```

文件恢复策略（[compact.ts:122-130](../../claude-code-typescript-src/services/compact/compact.ts#L122-L130)）：

```typescript
export const POST_COMPACT_MAX_FILES_TO_RESTORE = 5
export const POST_COMPACT_TOKEN_BUDGET = 50_000
export const POST_COMPACT_MAX_TOKENS_PER_FILE = 5_000

export const POST_COMPACT_MAX_TOKENS_PER_SKILL = 5_000
export const POST_COMPACT_SKILLS_TOKEN_BUDGET = 25_000
```

只恢复**最多 5 个**文件，每个**≤5K tokens**，总预算**50K tokens**。挑选规则（[compact.ts:1610](../../claude-code-typescript-src/services/compact/compact.ts#L1610)）是按 readFileState 里的访问顺序，最近读的优先。

### 6.5 加附件层

```typescript
const planAttachment = createPlanAttachmentIfNeeded(context.agentId)
const planModeAttachment = await createPlanModeAttachmentIfNeeded(context)
const skillAttachment = createSkillAttachmentIfNeeded(context.agentId)

// 重新注入 delta 附件（empty history → diff against nothing → announce all）
for (const att of getDeferredToolsDeltaAttachment(...)) { push }
for (const att of getAgentListingDeltaAttachment(...)) { push }
for (const att of getMcpInstructionsDeltaAttachment(...)) { push }
```

注意第二组 delta 附件——**压缩吃掉了之前的 delta 通知**，所以要从空状态重新告诉模型当前可用的工具/代理/MCP 服务器。

### 6.6 SessionStart hooks

```typescript
const hookMessages = await processSessionStartHooks('compact', { model: ... })
```

跑 SessionStart hook 是因为压缩之后逻辑上等价于「新会话开始」，模型需要重新初始化。

### 6.7 组装最终消息

```typescript
const boundaryMarker = createCompactBoundaryMessage(
  isAutoCompact ? 'auto' : 'manual',
  preCompactTokenCount ?? 0,
  messages.at(-1)?.uuid,
)

const summaryMessages = [createUserMessage({
  content: getCompactUserSummaryMessage(summary, suppressFollowUpQuestions, transcriptPath),
  isCompactSummary: true,
  isVisibleInTranscriptOnly: true,    // ← 不发给模型，只在 transcript 里渲染
})]

// 用第 12 篇讲的 buildPostCompactMessages 组装：
//   [boundaryMarker, ...summaryMessages, ...attachments, ...hookResults]
```

边界标记是个**系统消息**，被 `normalizeMessagesForAPI` 过滤掉不发给 API。它的价值在 resume 时——loader 通过它定位「以上为压缩前内容」的边界。

---

## 7. streamCompactSummary 双路径

[compact.ts:1136-1255](../../claude-code-typescript-src/services/compact/compact.ts#L1136-L1255)。

### 7.1 优先路径：runForkedAgent + 共享 prompt cache

```typescript
const promptCacheSharingEnabled = getFeatureValue_CACHED_MAY_BE_STALE(
  'tengu_compact_cache_prefix',
  true,    // ← 默认开
)

if (promptCacheSharingEnabled) {
  try {
    // DO NOT set maxOutputTokens here. The fork piggybacks on the main
    // thread's prompt cache by sending identical cache-key params (system,
    // tools, model, messages prefix, thinking config). Setting maxOutputTokens
    // would clamp budget_tokens, creating a thinking config mismatch that
    // invalidates the cache.
    const result = await runForkedAgent({
      promptMessages: [summaryRequest],
      cacheSafeParams,           // ← 重要：与主对话用相同的 cache 键参数
      canUseTool: createCompactCanUseTool(),
      querySource: 'compact',
      forkLabel: 'compact',
      maxTurns: 1,               // ← 单轮强制，否则模型可能调工具
      skipCacheWrite: true,
      overrides: { abortController: context.abortController },  // 用户 ESC 可中断
    })
    ...
  } catch (error) {
    // 失败 → 降级到 streaming fallback
  }
}
```

**核心思想**：fork 子代理用和主对话**完全相同的 cache 键参数**（system prompt、tools schema、model、messages 前缀、thinking config）。Anthropic 服务端识别为同一个 cache key → cache hit → 几乎不付钱读对话历史，**只为输出 17K tokens 的摘要付钱**。

注释里强调"千万别设 maxOutputTokens"——会让 thinking budget 被 clamp，导致 thinking config 和主对话不一致，cache key 失配，整个优化失效。

实验数据（[compact.ts:431-434](../../claude-code-typescript-src/services/compact/compact.ts#L431-L434)）：

> 实验（Jan 2026）确认：关闭 cache sharing 路径 98% cache miss，占 fleet cache_creation ~0.76%（~38B tok/day），主要集中在 ephemeral envs（CCR/GHA/SDK）和 3P 提供商（GB cache 冷或不可用）。GB gate 保留作为 kill-switch。

每天节省 380 亿 tokens 的 cache_creation 成本。

### 7.2 Fallback：普通 streaming

```typescript
const retryEnabled = getFeatureValue_CACHED_MAY_BE_STALE(
  'tengu_compact_streaming_retry',
  false,
)
const maxAttempts = retryEnabled ? MAX_COMPACT_STREAMING_RETRIES : 1
```

forked agent 失败时降级。这条路径不享受 cache sharing，但允许设置 `maxOutputTokensOverride`（因为不需要保 cache key 不变）。

### 7.3 Keep-alive 防 WebSocket idle timeout

```typescript
const activityInterval = isSessionActivityTrackingActive()
  ? setInterval(
      (statusSetter) => {
        sendSessionActivitySignal()              // PUT /worker heartbeat
        statusSetter?.('compacting')             // 重发 SDK 状态
      },
      30_000,                                     // 每 30s
      context.setSDKStatus,
    )
  : undefined
```

压缩 API 调用通常 5-10+ 秒，期间没别的消息流动，远程会话的 WebSocket 服务端可能因 idle 关闭连接。用 30s 心跳 + 重发 'compacting' 状态保持连接活跃。

**RepoHarness 借鉴**：如果你的 harness 是分布式的（远程 agent + 本地控制器），任何 ≥30s 的同步操作都该有 heartbeat 机制。

---

## 8. 9 段摘要 Prompt 详解

源码 [services/compact/prompt.ts](../../claude-code-typescript-src/services/compact/prompt.ts)。三个 prompt 模板：

| 名称 | 何时用 | 9 段第 8/9 节叫什么 |
|---|---|---|
| `BASE_COMPACT_PROMPT` | 默认（全量摘要替换历史）| Current Work + Optional Next Step |
| `PARTIAL_COMPACT_PROMPT` | 部分摘要（保留最近若干轮）| 同上 |
| `PARTIAL_COMPACT_UP_TO_PROMPT` | 摘要在前、保留消息在后的拼接 | Work Completed + Context for Continuing Work |

### 8.1 共用结构

```typescript
NO_TOOLS_PREAMBLE
  + 主体 prompt（BASE / PARTIAL_FROM / PARTIAL_UP_TO）
  + customInstructions（可选）
  + NO_TOOLS_TRAILER
```

`NO_TOOLS_PREAMBLE`（[prompt.ts:19-26](../../claude-code-typescript-src/services/compact/prompt.ts#L19-L26)）：

```text
CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.

- Do NOT use Read, Bash, Grep, Glob, Edit, Write, or ANY other tool.
- You already have all the context you need in the conversation above.
- Tool calls will be REJECTED and will waste your only turn — you will fail the task.
- Your entire response must be plain text: an <analysis> block followed by a <summary> block.
```

注释解释为什么这么"凶"：fork 路径继承父对话的完整工具集（cache key 必须一致），Sonnet 4.6+ 的 adaptive-thinking 模型有时会尝试调工具尽管被弱化了禁令。`maxTurns: 1` 下被拒的工具调用 = 没有 text 输出 → 落入 streaming fallback（4.6 上 2.79%，4.5 上 0.01%）。把禁令前置 + 明确说"会失败"，能减少这种浪费。

`NO_TOOLS_TRAILER`（[prompt.ts:269-272](../../claude-code-typescript-src/services/compact/prompt.ts#L269-L272)）：

```text
REMINDER: Do NOT call any tools. Respond with plain text only — 
an <analysis> block followed by a <summary> block. 
Tool calls will be rejected and you will fail the task.
```

前后夹击，确保模型不会忘。

### 8.2 BASE_COMPACT_PROMPT 9 段（中文翻译核心段）

[prompt.ts:61-77](../../claude-code-typescript-src/services/compact/prompt.ts#L61-L77)：

```
你的任务是为目前为止的对话生成一份详细摘要，
重点关注用户的明确请求和你之前的操作。
摘要应充分捕获技术细节、代码模式和架构决策——
让继续开发工作不丢失上下文。

[详细分析指令：见 8.3]

摘要包含 9 个部分：

1. Primary Request and Intent（主要请求与意图）
   详细记录用户的所有显式请求和意图

2. Key Technical Concepts（关键技术概念）
   列出讨论过的所有重要技术、框架、概念

3. Files and Code Sections（文件与代码片段）
   枚举具体文件和代码段（看过/改过/创建过的）。
   特别关注最近的消息，包含完整代码片段，
   并说明这个文件读取或编辑为什么重要

4. Errors and fixes（错误与修复）
   列出所有遇到的错误及其修复方式。
   特别关注用户反馈，尤其当用户明确要求"换个做法"时

5. Problem Solving（问题解决）
   记录已解决的问题和正在排查的工作

6. All user messages（所有用户消息）
   列出所有非工具结果的用户消息——
   理解用户反馈和意图变化的关键

7. Pending Tasks（待办任务）
   用户明确要求但尚未完成的工作

8. Current Work（当前工作）
   精确描述摘要前最后在做什么。
   特别关注最近的 user 和 assistant 消息，
   包含文件名和代码片段

9. Optional Next Step（可选下一步）
   下一步应该做什么。
   重要：必须直接对应用户最近的显式请求，
   并附原文引用避免任务漂移。
   如果上一个任务已完成，
   除非下一步明确对齐用户请求，否则不要列出。
```

### 8.3 `<analysis>` 草稿纸

[prompt.ts:31-44](../../claude-code-typescript-src/services/compact/prompt.ts#L31-L44)：

```text
在给出最终摘要前，把分析过程包在 <analysis> 标签里组织你的思路：

1. 按时间顺序分析对话的每个段落，每段都要识别：
   - 用户的显式请求和意图
   - 你处理这些请求的方式
   - 关键决策、技术概念和代码模式
   - 具体细节如：
     - 文件名
     - 完整代码片段
     - 函数签名
     - 文件编辑
   - 你遇到的错误及如何修复
   - 特别关注用户的具体反馈，尤其当用户告诉你"换个做法"
2. 双重检查技术准确性和完整性，每个必要元素都要充分覆盖
```

`<analysis>` 是**草稿纸**——通过让模型先在草稿里展开思考，最终的 `<summary>` 质量更高。但草稿对下一轮没有信息价值，只会浪费 token。所以 `formatCompactSummary` 把它剥离掉。

### 8.4 formatCompactSummary 剥离逻辑

[prompt.ts:311-336](../../claude-code-typescript-src/services/compact/prompt.ts#L311-L336)：

```typescript
export function formatCompactSummary(summary: string): string {
  let formattedSummary = summary

  // 剥离 <analysis>...</analysis> 草稿纸
  formattedSummary = formattedSummary.replace(/<analysis>[\s\S]*?<\/analysis>/, '')

  // 提取 <summary>...</summary> 内容，换成 "Summary:\n..." 标题
  const summaryMatch = formattedSummary.match(/<summary>([\s\S]*?)<\/summary>/)
  if (summaryMatch) {
    const content = summaryMatch[1] || ''
    formattedSummary = formattedSummary.replace(
      /<summary>[\s\S]*?<\/summary>/,
      `Summary:\n${content.trim()}`,
    )
  }

  // 清理多余空行
  formattedSummary = formattedSummary.replace(/\n\n+/g, '\n\n')

  return formattedSummary.trim()
}
```

**输入示例**：

```text
<analysis>
我先看了用户的所有请求。第 1 轮要求修复 auth.ts 的 token 验证 bug...
（300 行内部思考）
</analysis>

<summary>
1. Primary Request and Intent:
   用户要求修复 auth.ts 的 token 验证 bug 并加单元测试...
2. Key Technical Concepts:
   - JWT
   - Express middleware
...
</summary>
```

**输出**：

```text
Summary:
1. Primary Request and Intent:
   用户要求修复 auth.ts 的 token 验证 bug 并加单元测试...
2. Key Technical Concepts:
   - JWT
   - Express middleware
...
```

300 行 `<analysis>` 直接没了，节省 ~3-5K tokens 进入下一轮上下文。

### 8.5 partial 摘要的方向（from / up_to）

[prompt.ts:204-267](../../claude-code-typescript-src/services/compact/prompt.ts#L204-L267)：

| 方向 | 摘要位置 | 第 8 节 | 第 9 节 |
|---|---|---|---|
| `from`（默认）| 后部分被摘要，前部分保留 | Current Work | Optional Next Step |
| `up_to` | 前部分被摘要，后部分保留 | Work Completed | Context for Continuing Work |

「up_to」用于「summary 在前 + kept 在后」的场景——摘要给模型当 cache hit 用，新消息接在后面继续。第 9 节叫"Context for Continuing Work"是因为读者顺序是「先看摘要、再看新消息」，需要的是「能让人接着读懂的背景」。

---

## 9. Post-Compact 重建（5 类附件 + delta 重新注入）

第 12 篇画过总图，这里看具体逻辑。

### 9.1 文件附件（最重要）

[compact.ts:1415-1466](../../claude-code-typescript-src/services/compact/compact.ts#L1415-L1466)：

```typescript
export async function createPostCompactFileAttachments(
  preCompactReadFileState,    // 压缩前备份的 readFileState
  context,
  maxFiles = POST_COMPACT_MAX_FILES_TO_RESTORE,    // 5
): Promise<AttachmentMessage[]> {
  // 按访问时间逆序，挑最近的 5 个
  // 每个截断到 5K tokens
  // 总预算 50K tokens
  // shouldExcludeFromPostCompactRestore: 跳过 .lock / 二进制 / 隐藏文件等
}
```

策略：

1. 收集 readFileState 里所有访问过的文件
2. 按最近访问时间排序，取最近 5 个
3. 每个文件重新读一遍（**注意**：可能内容已变，会读最新的）
4. 单文件超 5K tokens 截断
5. 总预算超 50K tokens 提前停

**为什么是 5 个？**——这是工程取舍：太少模型会重新调 Read，太多浪费上下文。生产数据应该是验证过的甜点。

### 9.2 计划附件

```typescript
const planAttachment = createPlanAttachmentIfNeeded(context.agentId)
const planModeAttachment = await createPlanModeAttachmentIfNeeded(context)
```

两个：
- `createPlanAttachmentIfNeeded`：如果当前有持久化计划文件（plan mode 产物）
- `createPlanModeAttachmentIfNeeded`：如果**当前还在 plan mode**，重新注入 plan mode 系统指令

### 9.3 技能附件

```typescript
const skillAttachment = createSkillAttachmentIfNeeded(context.agentId)
```

调用过的 skill 内容。**注意**：[compact.ts:524-529](../../claude-code-typescript-src/services/compact/compact.ts#L524-L529) 故意**不**调 `resetSentSkillNames()`。原因：

> 重新注入完整的 skill_listing（~4K tokens）post-compact 是纯粹的 cache_creation，收益不大。模型仍然有 SkillTool 的 schema，invoked_skills 附件已经保留了用过的 skill 内容，动态新增由 skillChangeDetector / cacheUtils 处理。

### 9.4 Delta 附件重新注入

```typescript
// 压缩吃掉了之前的 delta 通知。从空状态重新发，等于"全量重新公告"
for (const att of getDeferredToolsDeltaAttachment(
  context.options.tools, context.options.mainLoopModel,
  [],                          // ← 空的 prior history → 全量
  { callSite: 'compact_full' },
)) { ... }
```

3 类 delta：

- `getDeferredToolsDeltaAttachment`：延迟工具发现的当前状态（哪些 tool schema 已加载）
- `getAgentListingDeltaAttachment`：可用代理清单
- `getMcpInstructionsDeltaAttachment`：MCP 服务器指令

### 9.5 SessionStart hooks

```typescript
const hookMessages = await processSessionStartHooks('compact', {
  model: context.options.mainLoopModel,
})
```

**逻辑等价于会话重启**——所以会跑 SessionStart hooks。比如用户配置的「会话开始时打印当前 git status」之类的 hook 会在 post-compact 重新跑一次。

---

## 10. 关键不变量

| 不变量 | 实现 / 出处 |
|---|---|
| **递归保护**：fork 子代理不能再触发 autocompact | shouldAutoCompact 里 querySource 三种排除 |
| **熔断保护**：连续 3 次失败停止 | tracking.consecutiveFailures + MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES |
| **共享 cache 必须保 key 不变** | runForkedAgent 时不能设 maxOutputTokens（否则 clamp thinking budget）|
| **maxTurns: 1** | fork 子代理只能输出一次，避免无限循环和工具调用 |
| **`<analysis>` 必须剥离** | formatCompactSummary 强制去除草稿纸 |
| **PTL 重试上限 3 次** | MAX_PTL_RETRIES = 3，超过抛 ERROR_MESSAGE_PROMPT_TOO_LONG |
| **boundaryMarker 是系统消息** | 不发给 API，只用于 transcript 渲染和 resume 定位 |
| **summaryMessages 是 isVisibleInTranscriptOnly** | 摘要本身在 transcript 里给用户看，但 API 视图里也参与（compact_boundary 上游）|
| **延迟 SessionStart hook** | 在边界标记之后跑，逻辑等价于"重启会话" |
| **runPostCompactCleanup 必须跑** | 否则 microcompact / context-collapse / readFileCache 等模块状态 stale |
| **notifyCompaction 必须发** | 否则 cache break detector 把 post-compact 的 cache miss 误报为故障 |
| **markPostCompaction 状态** | 让下一轮的 blocking 检查知道"刚刚压缩过，跳过 stale 检查" |

---

## 11. 面向 RepoHarness 的实战要点

### 11.1 直接借鉴：9 段摘要 prompt 模板

这是整篇里**最值钱**的部分。SWE agent 训练做轨迹压缩、生成 episode summary、阶段性检查点都能用。

**怎么改造给 SWE harness 用**：

```
1. Primary Request and Intent
   → 改成：Task description（任务定义）

2. Key Technical Concepts
   → 改成：Codebase context（涉及的模块/类/函数清单）

3. Files and Code Sections
   → 直接保留（SWE 任务里这一段最重要）

4. Errors and fixes
   → 改成：Failed attempts and reasons（失败尝试 + 原因）
   → 这一段对 RL 训练特别有价值，模型可以学到"哪些路径不通"

5. Problem Solving
   → 改成：Solution approach（解决方案路线）

6. All user messages
   → 改成：Task constraints from user（用户给的额外约束）

7. Pending Tasks
   → 改成：Remaining subtasks（剩余子任务）

8. Current Work
   → 直接保留

9. Optional Next Step
   → 改成：Hypothesized next action（推测的下一步行动）
   → 训练时可以对比这个推测和实际下一步的吻合度
```

**`<analysis>` 草稿纸的设计模式**也要照搬——给模型一个"草稿空间"显著提升结构化输出质量，但训练数据里只保留正式 summary。

### 11.2 直接借鉴：fork agent 共享 prompt cache 范式

如果你的 harness 用 Anthropic API：

- 摘要 fork 的 system prompt / tools / messages 前缀 / model 必须和主对话**字节级一致**
- 不要为 fork 单独设 maxOutputTokens / temperature / thinking budget
- 用 `runForkedAgent` 风格的封装，把 cacheSafeParams 抽出来作为可复用对象

每天能省的 cache_creation 成本量级（生产数据 38B tokens/day）值得为这个细节付出工程投入。

### 11.3 直接借鉴：熔断器设计

任何「会重复触发昂贵操作的逻辑」都该有：

```python
# 伪代码
class CircuitBreaker:
    def __init__(self, max_failures=3):
        self.failures = 0
        self.max = max_failures
    
    def should_attempt(self):
        return self.failures < self.max
    
    def record_success(self):
        self.failures = 0       # 立刻清零，不要"指数退避后慢慢回升"
    
    def record_failure(self):
        self.failures += 1
```

阈值取 3 是经验值——少于 3 次失败可能是临时问题（值得重试），多于 3 次说明系统性失败（重试无意义）。

### 11.4 直接借鉴：post-compact 文件附件策略

SWE harness 在压缩 trajectory 后，模型仍需要继续工作。「最近读过的 5 个文件 + 单文件 5K + 总 50K」的分配可以直接用。

但 SWE 任务有个特殊点——**目标文件集合相对固定**（任务给定的 repo 里就那么几个文件），所以可以更激进：

```
SWE harness 适配：
- 替换为「任务相关的所有文件」（可能不止 5 个）
- 但每个文件用 ast/structural summary 而不是原始代码（节省 80% token）
- 完整代码留到模型主动 Read 时再读
```

### 11.5 间接借鉴：阈值结构

200K → 180K → 167K → 147K 这个四级阈值的间隔结构（20K / 13K / 20K）值得理解：

```
最外层（contextWindow → effective）：留给输出
中间层（effective → autocompact）：触发压缩的提前量
警告层（autocompact → warning）：提示用户/agent 注意上下文
```

不是平均切，是**根据"输出预算 + 操作时间窗"反推**。RepoHarness 设计自己的阈值可以问：

- 输出预算多大？（17K p99.99 是 Claude 的，你的 agent 输出有多长？）
- 触发到完成压缩需要多久？这段时间还要继续生成多少 token？
- 警告要给操作者多少反应时间？

### 11.6 不要直接复刻

| 内容 | 原因 |
|---|---|
| Session Memory 优先 + 回退 | Session Memory 自身是个独立系统，不为压缩存在；只有完整有 SM 系统才能用这个优化 |
| `tengu_compact_cache_prefix` 的 GrowthBook 切流 | 是生产 A/B 实验的工程基础设施，训练 harness 用不上 |
| WebSocket keep-alive | 仅在分布式 + 长连接场景需要 |
| Anthropic 私有的 cache_edits / cache_reference | API 私有能力 |

---

## 12. 速查

| 项目 | 值 / 位置 |
|---|---|
| 主流程 | [services/compact/autoCompact.ts](../../claude-code-typescript-src/services/compact/autoCompact.ts) `autoCompactIfNeeded` |
| 摘要生成 | [services/compact/compact.ts](../../claude-code-typescript-src/services/compact/compact.ts) `compactConversation` |
| 9 段 prompt | [services/compact/prompt.ts](../../claude-code-typescript-src/services/compact/prompt.ts) |
| 触发阈值（200K）| 167K（= 180K - 13K）|
| 阻塞硬限 | 177K（= 180K - 3K）|
| 摘要输出预算 | 20K（基于 p99.99 = 17,387 tokens）|
| 熔断阈值 | 3 次连续失败 |
| PTL 重试 | 最多 3 次 |
| Post-compact 文件 | 最多 5 个，单文件 5K，总 50K |
| Post-compact 技能 | 单技能 5K，总 25K |
| Cache sharing 默认 | 开（GrowthBook `tengu_compact_cache_prefix` = true）|
| Fork 子代理 querySource | `'compact'`（递归保护）|
| 失败时 | `wasCompacted: false, consecutiveFailures: ++` |
| 成功时 | `wasCompacted: true, consecutiveFailures: 0` |
| Keep-alive 间隔 | 30 秒 |
| 系统边界标记 type | `'compact_boundary'`（subtype）|
| 摘要消息 flag | `isCompactSummary: true, isVisibleInTranscriptOnly: true` |
| Delta 附件类型 | deferredTools / agentListing / mcpInstructions |
| Hooks | PreCompact + SessionStart（'compact' source）|
| 调试环境变量 | `DISABLE_COMPACT` / `DISABLE_AUTO_COMPACT` / `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` / `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` |

---

## 13. 学到这里你应该回答的问题

1. **为什么 AutoCompact 触发阈值是 167K 而不是 180K？**
   答：181K-200K 中的 13K 是缓冲，留给"触发到摘要完成期间继续生成的输出 + 不确定的 token 估算误差"。167K 时触发，等摘要做完可能已经 175K，仍在 180K 有效窗口内。

2. **为什么 Session Memory Compact 优先于传统 AutoCompact？**
   答：Session Memory 已经在后台持续写笔记（异步、低成本），有现成产物时直接复用 = 0 LLM 成本。只有现成笔记不够（太旧 / 不存在 / 不覆盖）才付费做完整摘要。

3. **为什么 fork 子代理不能设 maxOutputTokens？**
   答：会 clamp `budget_tokens = Math.min(budget, maxOutputTokens-1)`，让 thinking config 和主对话不一致，cache key 失配，整个 cache sharing 优化失效。

4. **`<analysis>` 标签为什么要剥离？**
   答：它是模型的"草稿纸"——通过让模型先展开思考再写正式摘要，质量显著提升，但草稿对下一轮上下文没有信息价值（只会重复 `<summary>` 里更精炼的内容），3-5K tokens 浪费。

5. **Post-compact 为什么要重新注入 deferred tools / agent listing / MCP delta？**
   答：这些 delta 通知是"增量公告"性质——上一次告诉模型"新增工具 X"，这条通知在压缩时被吃掉了。从空 prior history 重新发，等价于"全量公告所有当前可用工具"，模型重新对齐当前能力。

6. **熔断器为什么是 3 次而不是 5 次或 10 次？**
   答：经验值。生产数据显示连续 ≥3 次失败几乎都是系统性问题（上下文真的不可恢复地超限），重试无意义。3 次足够区分"临时网络抖动" vs "真不行了"。

如果以上都答得上，下一篇可以进 Reactive Compact（PTL 兜底）或 Session Memory（详解上面提到的"优先策略"）。
