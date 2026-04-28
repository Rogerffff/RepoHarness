# 第 10 篇：上下文管理、记忆与会话

## 1. 概述：为什么需要上下文管理

大语言模型的上下文窗口是有限资源。Claude Code 的一次交互式会话往往包含数十轮对话、数百次工具调用，产生的 token 总量很容易超出模型的上下文上限。如果不加管理，要么请求被 API 拒绝（`prompt_too_long`），要么缓存命中率急剧下降导致成本飙升。

Claude Code 围绕这个核心问题构建了一套多层次的上下文生命周期管理体系：

- **Microcompact（微压缩）**：每次请求前，轻量清理旧工具结果，延缓上下文增长
- **AutoCompact（自动压缩）**：上下文接近阈值时，自动将整段对话总结为摘要
- **Session Memory（会话记忆）**：后台持续提取对话笔记，用于替代传统压缩
- **Memory System（记忆系统）**：跨会话持久化关键信息
- **Speculation（推测执行）**：在用户思考时预先执行可能的后续操作

---

## 2. 上下文压缩策略

### 2.1 AutoCompact（自动压缩）

AutoCompact 是最核心的压缩机制。当上下文 token 数接近阈值时，系统 fork 一个子 agent，让它阅读完整对话并生成结构化摘要，然后用摘要替换原始消息。

**阈值计算**（`src/services/compact/autoCompact.ts`）：

```typescript
// 有效上下文窗口 = 模型上下文窗口 - 预留给摘要输出的 token
export function getEffectiveContextWindowSize(model: string): number {
  const reservedTokensForSummary = Math.min(
    getMaxOutputTokensForModel(model),
    MAX_OUTPUT_TOKENS_FOR_SUMMARY, // 20,000 tokens
  )
  return contextWindow - reservedTokensForSummary
}

// 自动压缩阈值 = 有效窗口 - 缓冲区（13,000 tokens）
export function getAutoCompactThreshold(model: string): number {
  return getEffectiveContextWindowSize(model) - AUTOCOMPACT_BUFFER_TOKENS
}
```

**熔断机制**：如果连续 3 次压缩失败（例如上下文已经不可恢复地超限），系统会停止重试，避免在每个 turn 都发起注定失败的 API 调用。这是从实际生产数据中发现的问题——曾有会话连续失败 3,272 次，每天浪费约 25 万次 API 调用。

**压缩 Prompt**（`src/services/compact/prompt.ts`）要求模型生成包含 9 个部分的结构化摘要：主要意图、技术概念、文件与代码、错误修复、问题解决、用户消息、待办任务、当前工作、下一步。`<analysis>` 标签充当"草稿纸"——提升摘要质量但在最终输出中被 `formatCompactSummary()` 剥离。

### 2.2 Microcompact（微压缩）

Microcompact 是一种轻量级的"预请求"清理，在每次 API 调用前执行，不需要额外的 LLM 调用。

**核心思路**：旧的工具调用结果（`FileRead`、`Bash`、`Grep` 等）在对话后期价值递减，可以安全清除其内容。

系统提供两条路径（`src/services/compact/microCompact.ts`）：

1. **Time-based Microcompact**：当距上次 assistant 消息超过一定时间（说明 API 缓存已过期），直接清除旧工具结果内容，替换为 `[Old tool result content cleared]`。保留最近 N 个工具结果。

2. **Cached Microcompact**：利用 API 的 `cache_edits` 能力，在不破坏缓存前缀的前提下删除旧工具结果。这是性能最优的路径——不修改本地消息内容，仅通过 API 层的 `cache_reference` 和 `cache_edits` 指令操作。

```typescript
// 只对这些"可压缩"的工具进行清理
const COMPACTABLE_TOOLS = new Set<string>([
  FILE_READ_TOOL_NAME,
  ...SHELL_TOOL_NAMES,  // Bash 等
  GREP_TOOL_NAME,
  GLOB_TOOL_NAME,
  WEB_SEARCH_TOOL_NAME,
  WEB_FETCH_TOOL_NAME,
  FILE_EDIT_TOOL_NAME,
  FILE_WRITE_TOOL_NAME,
])
```

### 2.3 Snip Compact

Snip 是一种更激进的策略（`feature('HISTORY_SNIP')`），在消息被发送到 API 之前，在 `normalizeMessagesForAPI` 中给用户消息附加标签。它配合 `snipCompact` 模块工作，可以在消息级别进行更细粒度的裁剪。当 Snip 释放了 token 时，这个释放量会传递给 `shouldAutoCompact` 以避免不必要的 AutoCompact 触发。

### 2.4 Reactive Compact（被动压缩）

Reactive Compact 是 AutoCompact 的"后备方案"。当 API 返回 `prompt_too_long` 错误时触发——此时上下文已经超限，必须立即压缩。

与主动的 AutoCompact 不同，Reactive Compact：
- 按 **API round 边界** 分组消息（`groupMessagesByApiRound`），而非按用户 turn
- 在压缩请求本身也遇到 `prompt_too_long` 时，会逐步丢弃最旧的消息组重试（`truncateHeadForPTLRetry`）
- 最多重试 3 次，每次丢弃足以覆盖 token 缺口的消息组

```typescript
// 按 API 轮次分组——以 assistant 的 message.id 变化为边界
export function groupMessagesByApiRound(messages: Message[]): Message[][] {
  // 同一个 API 响应的流式 chunk 共享同一个 id，
  // 只有真正新的轮次才会触发分组边界
  for (const msg of messages) {
    if (msg.type === 'assistant' &&
        msg.message.id !== lastAssistantId &&
        current.length > 0) {
      groups.push(current)
      current = [msg]
    } else {
      current.push(msg)
    }
  }
}
```

### 2.5 API Context Management

对于支持服务端上下文管理的 API（`src/services/compact/apiMicrocompact.ts`），Claude Code 还可以将清理策略下发给 API 侧执行：

```typescript
// 两种服务端策略
type ContextEditStrategy =
  | { type: 'clear_tool_uses_20250919', ... }  // 清除旧工具调用
  | { type: 'clear_thinking_20251015', ... }   // 清除旧 thinking 块
```

---

## 3. 压缩触发条件与边界检测

`calculateTokenWarningState` 函数（`autoCompact.ts`）将上下文使用划分为四个级别：

| 级别 | 含义 | 动作 |
|------|------|------|
| `isAboveWarningThreshold` | 剩余缓冲 < 20K tokens | 显示黄色警告 |
| `isAboveErrorThreshold` | 剩余缓冲 < 20K tokens | 显示红色警告 |
| `isAboveAutoCompactThreshold` | 超过自动压缩阈值 | 触发 AutoCompact |
| `isAtBlockingLimit` | 剩余缓冲 < 3K tokens | 阻塞，强制手动 /compact |

**递归保护**：`shouldAutoCompact` 显式排除来自 `session_memory`、`compact`、`marble_origami`（context-collapse agent）等子 agent 的请求，防止压缩的压缩进入死循环。

---

## 4. 附件构建（Post-Compact Attachments）

压缩后，原始上下文中的增量信息会丢失。系统通过"附件"机制重新注入关键上下文（`src/utils/attachments.ts`）：

- **文件增量附件**（`generateFileAttachment`）：重新读取压缩前正在编辑的关键文件
- **Deferred Tools 增量**（`getDeferredToolsDeltaAttachment`）：对比压缩前后已发现的工具，补充新工具的 schema
- **MCP 指令增量**（`getMcpInstructionsDeltaAttachment`）：补充 MCP 服务器提供的指令
- **Agent Listing 增量**（`getAgentListingDeltaAttachment`）：补充子 agent 列表
- **Plan 附件**（`createPlanAttachmentIfNeeded`）：恢复当前执行计划

压缩后的消息按以下顺序组装：

```typescript
// compact.ts - buildPostCompactMessages
[boundaryMarker, ...summaryMessages, ...messagesToKeep, ...attachments, ...hookResults]
```

---

## 5. 记忆系统（Memory System）

Claude Code 的记忆分为 6 种类型（`src/utils/memory/types.ts`）：

```typescript
export const MEMORY_TYPE_VALUES = [
  'User',      // 用户级 (~/.claude/CLAUDE.md)
  'Project',   // 项目级 (CLAUDE.md, .claude/CLAUDE.md, .claude/rules/*.md)
  'Local',     // 本地私有 (CLAUDE.local.md)
  'Managed',   // 管理员级 (/etc/claude-code/CLAUDE.md)
  'AutoMem',   // 自动记忆 (~/.claude/projects/<path>/memory/)
  'TeamMem',   // 团队记忆 (feature-gated)
] as const
```

### 5.1 CLAUDE.md 加载机制

`src/utils/claudemd.ts` 实现了完整的内存文件发现与加载流程：

**加载优先级**（从低到高）：
1. Managed memory (`/etc/claude-code/CLAUDE.md`) — 全局管理员指令
2. User memory (`~/.claude/CLAUDE.md`) — 用户全局指令
3. Project memory（从根目录到 cwd 逐级搜索）— 项目指令
4. Local memory (`CLAUDE.local.md`) — 私有本地指令

后加载的文件优先级更高，因为模型对后面出现的内容关注度更高。

**`@include` 指令**：CLAUDE.md 文件支持 `@path` 语法引用其他文件，实现模块化配置。支持 `@./relative`、`@~/home`、`@/absolute` 三种路径格式。循环引用会被检测并跳过。

**缓存策略**：`getUserContext` 使用 `memoize` 缓存，在会话期间只加载一次。压缩后通过 `resetGetMemoryFilesCache` 清除缓存，确保下一轮获取最新内容。

### 5.2 AutoMem（自动记忆目录）

AutoMem 是基于文件系统的持久记忆（`src/memdir/`）：

**目录结构**：
```
~/.claude/projects/<sanitized-git-root>/memory/
├── MEMORY.md          # 索引文件（加载到系统提示中）
├── user_role.md       # 各种记忆文件
├── feedback_testing.md
└── ...
```

**记忆分类**（`src/memdir/memoryTypes.ts`）采用 4 类型分类法：
- **user**：用户角色、偏好、知识背景
- **feedback**：用户对工作方式的反馈（包含正面和负面）
- **project**：项目进展、目标、时间线
- **reference**：外部系统的指针（如 Linear 项目、Grafana 面板）

**关键设计原则**："不保存可从当前项目状态推导出的信息"——代码模式、架构、git 历史等应该通过工具查询，不应写入记忆。

**智能召回**（`src/memdir/findRelevantMemories.ts`）：并非所有记忆都注入每次请求。系统扫描记忆文件的 frontmatter（name/description），然后用 Sonnet 模型选择最相关的 5 个文件注入当前对话。

---

## 6. 自动记忆提取（Extract Memories）

`src/services/extractMemories/extractMemories.ts` 实现了后台记忆提取 agent。它在每轮主 query loop 结束时触发，使用 `runForkedAgent` 共享父对话的 prompt cache。

**触发条件**：
- 只在主 agent（非子 agent）上运行
- 可配置每 N 个 eligible turn 运行一次（`tengu_bramble_lintel`）
- 如果主 agent 本身已经写了记忆文件，则跳过（互斥机制）

**权限沙箱**：提取 agent 只能：
- 读取任意文件（`FileRead`、`Grep`、`Glob`）
- 执行只读 Bash 命令
- 在 memory 目录内写入文件（`FileEdit`、`FileWrite`）

**尾随执行**（Trailing Run）：如果提取运行期间又有新的 turn 完成，系统会暂存最新上下文，等当前提取完成后执行一次"尾随提取"，只处理两次调用之间的增量消息。

---

## 7. Session Memory（会话记忆）

Session Memory（`src/services/SessionMemory/`）是介于上下文压缩和持久记忆之间的机制——它维护一个 markdown 文件，持续记录当前会话的笔记。

**初始化与触发**（`sessionMemory.ts`）：

```typescript
// 会话记忆配置
export const DEFAULT_SESSION_MEMORY_CONFIG = {
  minimumMessageTokensToInit: 10000,    // 初始化阈值：上下文达到 10K tokens
  minimumTokensBetweenUpdate: 5000,     // 更新间隔：增长 5K tokens
  toolCallsBetweenUpdates: 3,           // 更新间隔：至少 3 次工具调用
}
```

触发逻辑：`token 增长达到阈值 AND (工具调用达标 OR 上一轮无工具调用)`。

**Session Memory Compaction**（`sessionMemoryCompact.ts`）：这是 Session Memory 的核心价值——当 AutoCompact 触发时，优先使用 Session Memory 内容作为摘要，而非再调用一次 LLM。这大幅降低了压缩成本。

保留消息的计算策略：
- 从 `lastSummarizedMessageId` 开始，向前扩展
- 至少保留 10K tokens 和 5 条含文本的消息
- 不超过 40K tokens 上限
- 确保不切断 `tool_use` / `tool_result` 配对

---

## 8. 会话持久化

### 8.1 JSONL 格式

会话消息以 JSONL 格式存储在 `~/.claude/projects/<path>/<sessionId>.jsonl`（`src/utils/sessionStorage.ts`）。每条消息作为独立的 JSON 行追加写入，支持流式记录和断点恢复。

子 agent 的对话记录在独立文件中：`<sessionId>/subagents/agent-<agentId>.jsonl`。

### 8.2 Resume 机制

`--resume` 参数可以恢复之前的会话。系统通过 `loadTranscriptFile` 读取 JSONL 文件重建消息链。压缩边界（`SystemCompactBoundaryMessage`）中包含 `preservedSegment` 元数据，帮助加载器正确链接保留的消息段。

### 8.3 History（命令历史）

`src/history.ts` 管理用户输入历史，存储在 `~/.claude/history.jsonl`。支持：
- 粘贴内容的智能存储（小内容内联，大内容哈希引用到 paste store）
- 按项目和会话分组
- 当前会话优先的历史排序
- 撤销最近一条历史（Esc 中断时）

---

## 9. Speculation（推测执行）

`src/services/PromptSuggestion/speculation.ts` 实现了推测执行——在用户思考下一步输入时，系统预测可能的操作并提前执行。

**工作原理**：
1. 在上一轮响应完成后，`generateSuggestion` 生成下一步建议
2. 如果建议被接受，`runForkedAgent` 在 overlay 文件系统上执行
3. 写操作被隔离到临时目录（`getClaudeTempDir()/speculation/<pid>/<id>/`）
4. 用户确认后，overlay 中的文件被 `copyOverlayToMain` 复制到真实文件系统

**安全边界**：
- 写操作限制在 overlay 目录内
- 最多执行 20 轮 / 100 条消息
- 遇到需要权限确认的 Bash 命令或 `cd` 时停止
- thinking 块和失败的工具调用会在注入时被剥离

---

## 10. 设计模式总结

### 分层压缩（Layered Compaction）

```
请求到达
  → Microcompact（轻量清理旧工具结果，无 LLM 调用）
    → Snip（消息级裁剪）
      → AutoCompact（达到阈值时，LLM 生成摘要）
        → Reactive Compact（API 拒绝时，紧急压缩）
```

每一层都是上一层的安全网，成本从低到高递增。

### Forked Agent 模式

Session Memory 提取、Auto Memory 提取、Compact 摘要生成都使用 `runForkedAgent` 模式——fork 主对话的完整上下文（共享 prompt cache），在沙箱化的权限下执行独立任务。这是 Claude Code 最核心的"后台智能"模式。

### 熔断与降级

- AutoCompact 连续失败 3 次后熔断
- Session Memory Compaction 失败时降级回传统 Compact
- Microcompact 在缓存过期时降级到直接清除

### 缓存感知

每次压缩/清理操作都通过 `notifyCompaction` / `notifyCacheDeletion` 通知缓存检测系统，防止合法的缓存读取下降被误报为"缓存中断"。

### 上下文状态的原子性

压缩后通过 `runPostCompactCleanup`（`src/services/compact/postCompactCleanup.ts`）统一清理所有相关缓存：microcompact 状态、context-collapse 状态、CLAUDE.md 缓存、分类器审批、推测检查、tracing 状态、会话消息缓存等。确保压缩后的系统状态与新对话一致。
