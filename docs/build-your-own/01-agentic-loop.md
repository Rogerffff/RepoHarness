# 第 1 章 Agentic Loop：让一次 LLM 调用变成一个 Agent

## 本章解决什么问题

你已经跑通了 [toy_agent_deepseek.py](toy_agent_deepseek.py)——一段 250 行的最小 agent loop，包含 5 步核心、tool_calls 配对、reasoning_content 保留、trace 记录。看 [run-20260429-155742.md](runs/run-20260429-155742.md) 你能清楚看到：每一轮模型先 emit `tool_calls`，Harness 跑完工具后用 `role:"tool"` + `tool_call_id` 配对回灌，模型在下一轮看到结果继续推理或终止。

**这套 5 步循环就是 agent 的全部本质。** 但 Claude Code 的 [query.ts](../../reference/claude-code-typescript-src/query.ts) 有 1700+ 行——差距在哪？这一章干两件事：

1. **精读 query.ts**：把 1700 行拆成 8 层骨架，每一层都告诉你"它解决了什么 happy path 没考虑到的问题"。
2. **对你的 toy_agent 做 4 层加固**：取消（Ctrl+C）/ Token 预算 / 重试 / Event 记录。每个 patch 都是可直接 apply 的 ~30 行。

读完你会拥有：一个能跑可中断、有预算保护、能重试 API 错误、能 emit 结构化事件的 agent loop——这是 **RepoHarness 中 agent loop 子模块的最小可用雏形**，**不是 RepoHarness v1**。RepoHarness v1 还需要 Task Adapter（Ch9）/ Workspace Adapter（Ch9）/ 完整四模式权限（Ch4）/ `run_tests` feedback verifier（Ch10）/ final verifier（Ch10）/ trajectory 目录契约（Ch11）/ 训练导出字段（Ch11）才算齐——后面 10 章会一层层加上去。

---

## 核心概念（5 个）

| 术语 | 一句话定义 |
|---|---|
| **Turn / Iteration** | `while(true)` 的一次循环。一个 turn = 一次模型调用 + 0 或多次工具执行 + 一次 tool_result 灌回。Claude Code 用 `turnCount` 追踪。 |
| **Streaming** | 两层：(a) **响应流式**——模型边出 token 边回；(b) **工具流式执行**——StreamingToolExecutor 在解析到一个完整 tool_use 块时**立即**启动该工具，不等整段响应结束。 |
| **Cancellation** | 用户 Ctrl+C / 超时 / 上层 abort 时，所有正在跑的工具 + 未消费的 stream + 即将发起的 API 调用都要立即停止。Claude Code 用 `AbortController` 树形传递信号。 |
| **Recovery（多级回退）** | API 调用失败时（5xx/429/413/max-output-tokens）**不直接抛给用户**——先尝试若干自动恢复路径（重试 / 压缩 / 降低 max_tokens），都失败才 surface。 |
| **Message Normalization** | 内部消息（progress / attachment / tool summary）必须在送给模型前转成 Anthropic API 协议要求的 `user`-role + tool_result blocks。这步如果错了，下次调模型直接 400。 |

---

## Claude Code 怎么做的：query.ts 的 8 层骨架

`query.ts` 的入口函数有两个：[query()](../../reference/claude-code-typescript-src/query.ts) 在 219 行，[queryLoop()](../../reference/claude-code-typescript-src/query.ts) 在 241 行。前者是个 thin wrapper，后者是真循环（307 行起 `while(true)`，一直到 1728 行结束）。

为什么是 generator（`async function*`）？看 219 行返回类型：

```typescript
AsyncGenerator<
  | StreamEvent
  | RequestStartEvent
  | Message
  | TombstoneMessage
  | ToolUseSummaryMessage,
  Terminal  // ← 终止时的最终值
>
```

它边跑边 `yield` 各种事件给消费者（REPL / SDK / 测试 harness）。这意味着**一个 query 的中间状态可以被外部观察、暂停、取消**。这是 RepoHarness 的 trajectory recorder 能 hook 进 agent loop 的根本机制。

### 第 1 层：状态收敛（行 268-291）

happy path 你的 toy_agent 只在循环里维护一个 `messages` 数组。生产级 agent loop **每轮迭代之间要保留** 9 项状态：

```typescript
let state: State = {
  messages: ...,                       // 消息历史
  toolUseContext: ...,                 // 工具执行上下文（abort signal、metadata）
  maxOutputTokensOverride: ...,        // 这一轮临时降低的 max_tokens（用于恢复）
  autoCompactTracking: ...,            // 自动压缩追踪
  stopHookActive: ...,                 // stop hook 是否正在跑
  maxOutputTokensRecoveryCount: 0,     // max-output 恢复重试次数
  hasAttemptedReactiveCompact: false,  // 这轮是否已经做过 reactive compact
  turnCount: 1,
  pendingToolUseSummary: ...,          // 上一轮 batch 的工具摘要（异步）
  transition: ...,                     // 这轮是从哪个恢复路径过来的
}
```

关键设计：所有 `continue` 跳回循环顶部时**只赋值一个 state 对象**，不是 9 个变量分别赋值。这看起来工程化过头，但实际上 query.ts 里有 **7 个不同的 continue 点**——分别对应 snip / microcompact / autocompact / collapse / collapse_drain_retry / reactive_compact_retry / max_output_retry。如果不收敛，每个 continue 点都要重复同样的赋值，丢一个字段就是 bug。

**为什么这是真问题，不是过度工程**——看一个具体反例：

```python
# ❌ 反例：9 个独立变量，3 个 continue 点
messages = init_messages
maxOutputTokensOverride = None
hasAttemptedReactiveCompact = False
maxOutputTokensRecoveryCount = 0
turnCount = 1
# ...

while True:
    # ... 跑一轮 ...
    
    if need_collapse_drain:
        messages = drained.messages
        maxOutputTokensOverride = None              # 必须清，下一轮用默认 token
        # 漏了：hasAttemptedReactiveCompact 该不该重置？
        # 漏了：maxOutputTokensRecoveryCount 该不该清零？
        # 漏了：turnCount 要不要 +1？collapse 算一轮吗？
        continue
    
    if need_reactive_compact:
        messages = compacted.messages
        hasAttemptedReactiveCompact = True          # 这个记得设
        maxOutputTokensOverride = None              # 这个记得清
        # 漏了：maxOutputTokensRecoveryCount...
        # 漏了：autoCompactTracking 该不该清？
        continue
    
    if need_max_output_retry:
        maxOutputTokensOverride = 16384             # 升级
        maxOutputTokensRecoveryCount += 1
        # 漏了：messages 没动，对吗？
        # 漏了：hasAttemptedReactiveCompact 维持原值？
        continue
```

每个 continue 点都要在脑里"重新决定" 9 个字段各自要不要改、清成什么。**7 个 continue 点 × 9 个字段 = 63 处显式决策**，漏一处就是 bug——比如 collapse 之后没清 `maxOutputTokensOverride`，下一轮模型只有 8192 输出窗口，又被截断，又触发恢复，进入死循环。

收敛后的写法（query.ts 的真实做法）：

```python
# ✅ 正例：单一 state dict，每个 continue 点显式重建完整 state
state = State(messages=..., maxOutputTokensOverride=None, ...)  # 9 个字段

while True:
    # 顶部解构（只读）
    messages, maxOutputTokensOverride, ... = state.messages, state.maxOutputTokensOverride, ...
    
    if need_collapse_drain:
        # 必须把 9 个字段都列一遍——类型系统/dataclass 强制保证不漏
        state = State(
            messages=drained.messages,
            maxOutputTokensOverride=None,
            autoCompactTracking=tracking,
            hasAttemptedReactiveCompact=hasAttemptedReactiveCompact,  # 显式保留
            maxOutputTokensRecoveryCount=maxOutputTokensRecoveryCount,
            turnCount=turnCount,
            transition=Transition('collapse_drain_retry', committed=drained.committed),
            # ... 其余 2 个字段
        )
        continue
```

`continue` 点显式重建整个 state，看起来啰嗦，但**类型/dataclass 在编译期或 lint 期就报 missing field**，比"漏一个字段，运行时死循环"好定位 100 倍。这是 query.ts 用 `state = next` 这种"全替换"风格的唯一原因。

#### 把 `if need_collapse_drain:` 这个例子彻底拆开看

上面的 `if need_collapse_drain:` 是**伪代码条件**。它对应 query.ts:1085-1117 的真实判断——同时满足 4 个条件才走这条恢复路径：

| 条件 | 含义 |
|---|---|
| `isWithheld413` | 上一轮 stream 触发了 413（prompt too long），错误已被 withhold |
| `feature('CONTEXT_COLLAPSE')` | 编译期开启了上下文压缩功能 |
| `contextCollapse` 实例存在 | 有个 collapse 管理器在跑 |
| `state.transition?.reason !== 'collapse_drain_retry'` | **核心防死循环**——这次循环**不是**已经从 collapse drain 来的（如果是，说明 collapse drain 救不回来，跳过这一层进 reactive compact） |

**"collapse drain"这个动作本身在干嘛**——可以这样想象。Claude Code 一直在后台维护一个"待压缩队列"（staged collapses）：

```
              (整个对话过程中：)
              ┌────────────────────────────────────────┐
              │ contextCollapse 后台维护的"待压缩队列"      │
              │                                         │
              │  staged[0] = (messages[5..15], 总结A)    │  ← 旧消息已生成总结
              │  staged[1] = (messages[20..40], 总结B)   │     但还没真的替换
              │  staged[2] = (messages[60..80], 总结C)   │     进 messages
              └────────────────────────────────────────┘
```

总结是**早就生成好的**（运行时 staged，不临场调 LLM）。这就是为什么图里说 collapse drain 是"cheap, granular"——它的"成本"只是几次数组替换操作，毫秒级。

**collapse drain 的动作 = 把队列里所有 staged collapse 一次性提交**，把对应原始消息段替换成总结：

```
before drain:
  messages = [m0, m1, m2, m3, m4, m5..m14, m15, m16..m19, m20..m40, m41..m59, m60..m80, m81..m200]
                                  └ staged 总结A ┘            └ staged 总结B ┘  └ staged 总结C ┘
  cumulative tokens: 195k

after drain:
  messages = [m0..m4, "<<总结A>>", m15..m19, "<<总结B>>", m41..m59, "<<总结C>>", m81..m200]
  cumulative tokens: ~100k
```

`drained.committed` 就是**实际提交了多少个 staged collapse**——上面例子是 3。如果队列空（committed = 0），collapse drain 救不了，fall through 到下一级 reactive compact（要临场调 Haiku 总结，几秒 + API 费）。

**逐字段拆 State 重建**——每个赋值都是一次**显式设计决策**：

| 字段 | 决策 | 为什么 |
|---|---|---|
| `messages=drained.messages` | **改** | drain 的全部目的就是改它 |
| `maxOutputTokensOverride=None` | **清** | 上一轮可能为应付输出截断升过 max_tokens；现在换了 messages，必须重新评估 |
| `autoCompactTracking=tracking` | **保留** | 自动压缩的统计信息（触发了多少次、什么时候触发的）跨多次恢复延续 |
| `hasAttemptedReactiveCompact=...` | **显式保留** | collapse drain ≠ reactive compact，不影响"是否做过 reactive compact"这个 flag |
| `maxOutputTokensRecoveryCount=...` | **显式保留** | 输出 token 的恢复计数，与"输入压缩"无关，要保留 |
| `turnCount=turnCount` | **显式保留** | drain 算"同一轮的 retry"，不是新 turn |
| `transition=Transition('collapse_drain_retry', ...)` | **改** | **核心防死循环字段**——记录这次循环是从 collapse drain 来的，让顶部判断 `state.transition?.reason !== 'collapse_drain_retry'` 能挡住下一轮再走同一条路 |
| `pendingToolUseSummary=None` | **清** | 上一轮没成功，相关异步任务作废 |
| `stopHookActive=None` | **清** | 同上 |

**这就是为什么"全字段重列"是必须的**：9 个字段每一个都是不同设计意图，没有任何一个能"靠默认值搞定"。如果你写成增量赋值：

```python
# ❌ 增量赋值的 bug：
state.messages = drained.messages
state.transition = Transition('collapse_drain_retry')
continue
# maxOutputTokensOverride 还是上一轮升过的值（比如 32768），
# 新一轮模型在压缩后的 messages 上又升级 max_tokens，输出截断又触发 max-output-tokens
# 恢复，恢复完输入又涨大，下一轮又 413，又走 collapse drain ……死循环
```

dataclass 的全字段重列让"这个 collapse drain 之后 maxOutputTokensOverride 该怎么处理？"变成一个**显式问题**，强迫你回答。增量赋值让这个问题变成**默认沉默地维持原值**——这就是 production bug 的来源。

**给你 toy_agent 的启示**：你现在状态只有 messages 一个变量。等加上 cancellation flag、token 累计、retry 次数后，**也要收敛成一个 dict 或 dataclass**。哪怕只有 3 个字段、2 个 continue 点也建议这么做——agent loop 长大的速度比你想的快。

### 第 2 层：循环顶部（行 307）

```typescript
while (true) {
  // 顶部 destructure 当前 state（只读）
  let { toolUseContext } = state
  const { messages, autoCompactTracking, ... } = state
  ...
}
```

每次迭代第一件事是 destructure 出当前 state——这样循环体内用 `messages` 这种 bare name 而不是 `state.messages`，可读性回归 happy path 风格。这是上一层"状态收敛"的代价补偿。

### 第 3 层：流式模型调用（行 659-960）

300 行的流式 try-catch 包装，做了三件事：

1. **打开 SSE 流**：每收到一个 chunk，把 content blocks 累积到 `assistantMessages`
2. **解析 tool_use 块**：每发现一个完整的 tool_use 块，根据策略**立刻**塞给 `streamingToolExecutor`（行 563-568，工具开始在后台跑）
3. **特殊错误"扣下"机制**（withholding）：prompt-too-long (HTTP 413) 和 max-output-tokens 错误**不**立即抛——而是把错误塞进 `lastMessage` 的 `isApiErrorMessage` 字段，让恢复层处理（见第 6 层）

**withholding 的具体 trace** 看一遍就懂：

```
Turn 5: 模型已写到 messages[150]，约 195k tokens（接近 200k 上限）
   │
   ├─ 调 stream API
   │     └─ API 返回 HTTP 413: "prompt too long"
   │
   ├─ 普通做法（throw）：
   │     except ApiError → 用户看到红色错误 → 任务失败 → 整个 trajectory 报废
   │
   └─ Claude Code 的 withholding 做法：
         1. 把 413 包成 AssistantMessage{
                type: "assistant",
                isApiErrorMessage: true,
                content: <prompt-too-long 错误对象>
            }
         2. push 进 assistantMessages（注意：push 进的是错误消息，不是真响应）
         3. 设 needsFollowUp = false（没产出有效 tool_use，循环不该继续工具执行）
         4. 跳过 stream 的剩余处理，落到 query.ts:1062 的 `if (!needsFollowUp)` 分支
         5. 在那个分支检测 lastMessage.isApiErrorMessage && isPromptTooLongMessage(lastMessage)
         6. → 触发第 5 层的 collapse drain（详见第 5 层）
         7. 用户毫无感觉，下一秒 messages 已经被压缩，retry 通过
```

整个过程里 **错误从未离开 query.ts 的内部状态机**——上层（REPL / SDK）拿到的是完整的恢复后响应，不是"413 然后又重试"两个事件。这是把生产级稳健性藏在 agent loop 内部、不污染消费者 API 的关键技巧。

为什么 streaming + concurrent tool execution 这么重要？想想这个场景：

- 模型流出 5 秒，期间产生 3 个 tool_use 块（在第 1/3/5 秒）
- 同步版本：等 stream 全部结束（第 5 秒）→ 串行跑 3 个工具（每个 2 秒）→ 共 5+6=11 秒
- 流式版本：第 1 秒就开始跑工具 1，第 3 秒开始跑工具 2，第 5 秒 stream 结束时工具 1 已跑完 → 共 5+max(2,2,2)=7 秒

这是 30%+ 的延迟节省。第 2 章会详细讲流式工具执行；本章只让你知道**这个"流式 + 并发"是 query.ts 1700 行里最值得理解的设计**。

### 第 4 层：needsFollowUp 决策（行 558 / 1062）

```typescript
let needsFollowUp = false        // 行 558：默认这轮没工具调用
...
// 在 stream loop 里：
if (toolUseBlock found) {
  needsFollowUp = true           // 行 834
}
...
if (!needsFollowUp) {
  // 没有 tool_use → 模型说完了 → 进入 stop hooks + Terminal 路径
} else {
  // 有 tool_use → 跑工具，下轮继续
}
```

**这一行就是"agent 是否要继续"的总开关**——和你 toy_agent 里 `if not tool_calls: break` 是同一个语义。Claude Code 把它放在 1062 行是因为前面 1000 行都在处理流式 + 错误恢复；happy path 里它就是这一个 bool。

### 第 5 层：错误恢复——prompt-too-long 的三级退路（行 1085-1183）

happy path 没有这一段。生产环境里这是必需的，因为长会话**必然**会遇到 prompt-too-long：

```
                          stream 失败
                              │
                  ┌───────────┴───────────┐
                  │ isWithheld413 ?        │
                  └───────────┬───────────┘
                              │ yes
                  ┌───────────▼───────────┐
                  │ ① collapse drain       │  把已 staged 的上下文压缩
                  │   (cheap, granular)   │  提交，retry 同一个 query
                  └───────────┬───────────┘
                              │ failed
                  ┌───────────▼───────────┐
                  │ ② reactive compact     │  用 Haiku 整段总结历史
                  │   (full summary)      │  retry 同一个 query
                  └───────────┬───────────┘
                              │ failed
                  ┌───────────▼───────────┐
                  │ ③ surface error        │  yield error message
                  │   return Terminal     │  return { reason: 'prompt_too_long' }
                  └───────────────────────┘
```

每一层都是**单次尝试**——如果 collapse drain 之后再 413，就直接进 reactive compact，不会无限套娃。这避免了"修复尝试本身把 context 又撑爆"的死循环。

**具体 trace**（数字是接近真实分布的示例）：

```
Turn 5 开始：messages = 150 条，~195k tokens（接近 200k 上限）
   │
   stream API 返回 HTTP 413
   │
   ↓ withhold（见上一节）
   │
   ↓ 落到 collapse drain
   ① collapse drain（cheap，只压"已 staged 待提交"的旧消息）
       before:  messages[5..130] 是 125 条原始 tool_call/tool_result 对
                cumulative tokens: 195k
       after:   messages[5..130] = 1 条
                "<<collapsed: 125 messages, 90k tokens summarized>>"
                cumulative tokens: 195k - 90k + 200 ≈ 105k
       retry → ✓ 200k 上限够用，过了
       continue → 回 while(true) 顶部
   │
   （如果 collapse drain 没救回来——比如 staged 队列空、压完还是 195k）
   │
   ↓ reactive compact
   ② reactive compact（expensive，整段 Haiku 总结）
       before:  messages[0..149] = 全部 150 条
       after:   messages = [
                  system,
                  "<<auto-compacted summary by Haiku: 250 words>>",
                  最后 5 条原始消息（保留近期上下文）
                ]
                cumulative tokens: ~3k
       retry → ✓
   │
   （如果 reactive compact 也没救回来——hasAttemptedReactiveCompact 已经 true）
   │
   ↓ ③ surface error
   yield AssistantMessage{isApiErrorMessage: true, ...}
   return Terminal { reason: 'prompt_too_long' }
```

每一步都对应 query.ts 里一个 `continue` 点（`collapse_drain_retry` / `reactive_compact_retry`），借助前面"状态收敛"的设计，state 里的 `transition` 字段记录这次循环是从哪个恢复路径过来的，避免无限循环。

**注意：这只是 prompt-too-long（输入 token 超限）的恢复路径。**Claude Code 还有针对 **max-output-tokens（输出 token 用完）**的另一类恢复，对应 query.ts 行 1188-1251 一带——它是"输出预算"层面的回退，机制不同：

- **触发**：响应到达 `max_output_tokens` 上限时被截断（finish_reason 是 max_tokens 而不是 stop / tool_use）
- **恢复策略**：用 `maxOutputTokensOverride` 在状态里记录"这一轮临时升 max_tokens"，retry 同一个 query；`maxOutputTokensRecoveryCount` 限制升级次数（避免无限上调）
- **与 prompt-too-long 的差别**：PTL 是"输入太多→压缩历史"；max-output-tokens 是"模型话没说完→给更大输出窗口"。两条路径在 query.ts 里各自独立，互不调用

具体数值 trace：

```
Turn 7：默认 max_output_tokens = 8192
   stream API 返回响应：finish_reason="max_tokens"（被截断），content 不完整
   │
   ↓ recovery 触发
   maxOutputTokensOverride = 16384
   maxOutputTokensRecoveryCount = 1
   continue → 回 while(true) 顶部，retry 同一个 query
   │
Turn 7 retry 1：max_output_tokens = 16384
   stream API 返回：finish_reason="max_tokens"  ← 还是被截断
   │
   maxOutputTokensOverride = 32768
   maxOutputTokensRecoveryCount = 2
   continue
   │
Turn 7 retry 2：max_output_tokens = 32768
   stream API 返回：finish_reason="end_turn" ✓ 完整说完
   │
   maxOutputTokensRecoveryCount 重置为 0
   进入正常 needsFollowUp 流程
```

`maxOutputTokensRecoveryCount` 一般有上限（比如 3 次），到顶就 `return Terminal { reason: 'max_output_tokens' }`——避免某些任务（比如让模型生成 100k 行代码）无限升级。

本章不展开 max-output-tokens 恢复的完整代码（Ch1 主线已经够长），但记住它和 PTL 是**输出预算**和**输入预算**的两类不同恢复，分别在 query.ts 不同区段独立运行。Ch5 压缩章会一并讲。

**给你 toy_agent 的启示**：第一版你不需要做 prompt-too-long 恢复（Ch5 压缩章再做），也不需要 max-output-tokens 升级，但**应该现在就做** retry-with-backoff 处理 5xx/429（Patch 3）。

### 第 6 层：工具执行（行 1366-1409）

```typescript
// 选择 executor：流式（已经跑了一部分）或 batch（一次性跑完）
const toolUpdates = streamingToolExecutor
  ? streamingToolExecutor.getRemainingResults()
  : runTools(toolUseBlocks, assistantMessages, canUseTool, toolUseContext)

for await (const update of toolUpdates) {
  if (update.message) {
    yield update.message    // 把工具进度/结果 yield 给消费者
    
    toolResults.push(
      ...normalizeMessagesForAPI(   // ← 关键：转成 API 协议
        [update.message],
        toolUseContext.options.tools,
      ).filter(_ => _.type === 'user'),  // ← 只保留 user-role 的 tool_result
    )
  }
}
```

`normalizeMessagesForAPI` 这步是为什么内部 ProgressMessage、AttachmentMessage、ToolUseSummaryMessage 这些消息类型都能在送回模型时被正确转成 `{role: "user", content: [{type: "tool_result", tool_use_id, content}]}`。**消息类型在内部丰富，在 API 边界统一**——这是 Claude Code 处理工具结果的核心模式。

**具体 before/after 看一遍就懂**——同一个工具调用产生的内部消息流，转出 Anthropic API 协议的过程：

```jsonc
// 内部消息流（一次 BashTool 调用产生 3 条 progress + 1 条 final）：
[
  {
    "type": "progress",
    "tool_use_id": "toolu_01ABC",
    "content": "[bash] starting: pytest tests/ -v"
  },
  {
    "type": "progress",
    "tool_use_id": "toolu_01ABC",
    "content": "[bash] running... 5s elapsed"
  },
  {
    "type": "progress",
    "tool_use_id": "toolu_01ABC",
    "content": "[bash] running... 10s elapsed"
  },
  {
    "type": "tool_result",
    "tool_use_id": "toolu_01ABC",
    "content": "5 passed, 2 failed in 12.3s\n..."
  }
]
```

```jsonc
// normalizeMessagesForAPI 转换后（送给模型的最终格式）：
// 注意：3 条 progress 被丢弃（它们只用于 UI 实时显示），
// 只有最终 tool_result 进入 API；多个工具的结果会合并到一条 user message。
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01ABC",
      "content": "5 passed, 2 failed in 12.3s\n..."
    }
    // 如果同一轮还有其他工具，它们的 tool_result 也合并到这个 content 数组里
  ]
}
```

关键规则总结：
- **progress 消息丢弃**——它们只是 UI 实时进度，模型不需要看（也看不懂"5s elapsed"）
- **tool_result 合并到一条 user message**——同一轮多个工具调用的结果放在同一个 `content` 数组里，不拆成多条 user 消息
- **`tool_use_id` 必须配对**——assistant 那条消息里有几个 `tool_use` 块，user message 里就要有几个 `tool_result` 块，`tool_use_id` 一一对应。漏一个、多一个都会 400

你 toy_agent 的 DeepSeek 版本走 OpenAI 协议（`role:"tool"` + `tool_call_id` 一对一一条消息），所以**没遇到这个 merge 问题**。如果将来 RepoHarness 要支持 Anthropic provider，这一步 merge 是必做的。

### 第 7 层：Terminal 返回原因（行 1175 等多处）

`return Terminal { reason }` 的 reason 至少有：

| reason | 含义 |
|---|---|
| `completed` | 模型说完了（没新 tool_use） |
| `prompt_too_long` | 多级恢复都失败 |
| `image_error` | 媒体超大且 reactive compact 救不回 |
| `max_turns` | 超过 maxTurns 上限 |
| `max_tokens_per_turn` | 单轮超过 token 预算 |
| `max_output_tokens` | output 端 token 用完且重试无效 |
| `aborted` | 用户取消 |

**为什么这么多 reason 很重要？**——因为消费者（REPL / SDK / RepoHarness）需要根据 reason 决定下一步动作：completed 就显示结果；aborted 要清理 workspace；max_turns 在 RepoHarness 里直接保留为 `agent_stop_reason="max_turns"`（不要笼统映射成 "exhaustion"——RepoHarness 设计明确保留 `max_turns` / `max_tool_calls` / `timeout` / `context_limit` 等具体预算类型，统计 / 诊断时这些区分非常重要）。**笼统的"成功 / 失败"不够用**。

### 第 8 层：取消（散布在整个文件）

`AbortController` 沿着工具调用 / 子 agent 树形传递。你能看到大量这种检查：

```typescript
if (toolUseContext.abortController.signal.aborted) {
  return { reason: 'aborted' }
}
```

关键模式：**不轮询**，而是在每个"耗时操作的边界"显式检查（API 调用前 / stream chunk 边界 / 工具执行前后 / hook 执行前后）。

---

## 最小复刻：把你的 toy_agent 加固成"小型生产版"

下面 4 个 patch 增量地升级 [toy_agent_deepseek.py](toy_agent_deepseek.py)。每个 patch 独立、可单独应用。**全部 apply 后约 350 行，仍是单文件可跑。**

> **代码状态说明**：以下 patch 的核心控制流（cancellation flag、状态字典、event emitter 接口）作者用 mock-stub 走过一遍消息流；与 DeepSeek 协议字段（`tool_calls.id` / `role:"tool"` / `usage.prompt_tokens`）的对接复用了你 toy_agent 已验证的写法。但**未对真实 DeepSeek 端做完整集成测试**——如果你 apply 后报字段名错误，请按你 toy_agent 里实际看到的 JSON 结构微调。

### Patch 1：Ctrl+C 取消

放在文件顶部（导入区下面）：

```python
import signal
import threading

# 进程级取消事件。signal handler 只能做最少的事（set flag），
# 真正的清理在 agent_loop 里做。
CANCEL_EVENT = threading.Event()

def _install_sigint_handler() -> None:
    def handler(signum, frame):  # noqa: ARG001
        CANCEL_EVENT.set()
        # 第二次 Ctrl+C 直接退出（防卡死）
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGINT, handler)

_install_sigint_handler()
```

在 `agent_loop` 的 `for turn in range(max_turns):` 循环里，**两个检查点**：

```python
for turn in range(max_turns):
    # —— 检查点 A：每轮顶部
    if CANCEL_EVENT.is_set():
        final_answer = "[cancelled by user before turn]"
        tr.heading(2, "Cancelled"); tr.text(final_answer)
        break

    resp = call_deepseek(messages)
    ...

    # —— 检查点 B：跑工具前（API 已经花了 token，但工具执行可能更慢）
    if CANCEL_EVENT.is_set():
        final_answer = "[cancelled by user during turn]"
        break

    for tc in tool_calls:
        ...
```

**别在 hot loop 里轮询**——只在 turn 边界和 tool batch 边界检查就够了。

### Patch 2：Token 预算 + 累计追踪

把 max_turns 这种"轮数限制"升级成"双保险"：

```python
TOKEN_BUDGET = int(os.environ.get("DEEPSEEK_TOKEN_BUDGET", "200000"))

def agent_loop(user_msg, max_turns=30, trace_path=None):
    ...
    total_input = 0
    total_output = 0
    total_cached = 0  # DeepSeek 单独统计 prompt_cache_hit_tokens
    
    for turn in range(max_turns):
        ...
        resp = call_deepseek(messages)
        usage = resp.get("usage", {})
        total_input += usage.get("prompt_tokens", 0)
        total_output += usage.get("completion_tokens", 0)
        total_cached += usage.get("prompt_cache_hit_tokens", 0)
        
        # —— 预算检查：billable = input + output - cached
        billable = total_input + total_output - total_cached
        if billable > TOKEN_BUDGET:
            final_answer = (
                f"[token budget exceeded: billable={billable} "
                f"(input={total_input}, output={total_output}, "
                f"cached={total_cached}) > budget={TOKEN_BUDGET}]"
            )
            tr.heading(2, "Budget exceeded"); tr.kv(
                input=total_input, output=total_output,
                cached=total_cached, billable=billable, budget=TOKEN_BUDGET,
            )
            break
        ...
    
    # 最后 trace 写一遍累计
    tr.hr(); tr.heading(2, "Token accounting")
    tr.kv(total_input=total_input, total_output=total_output,
          total_cached=total_cached,
          billable=total_input + total_output - total_cached)
    return final_answer, trace_path
```

**为什么减去 cached？**——你 [trace 文件](runs/run-20260429-155742.md) 里 `prompt_cache_hit_tokens: 384`，意味着 384 token 走的是缓存费率（DeepSeek 是约 1/10 价格）。批量评测算成本时这是关键差。

### Patch 3：API 重试

把 `call_deepseek` 包一层：

```python
import time

def call_deepseek_with_retry(messages, max_retries=3):
    """对 5xx / 429 做指数退避重试；4xx（除 429）和其他错误立即抛。"""
    last_err = None
    for attempt in range(max_retries):
        if CANCEL_EVENT.is_set():
            raise RuntimeError("cancelled before retry")
        try:
            return call_deepseek(messages)
        except RuntimeError as e:
            msg = str(e)
            # 解析 "DeepSeek HTTP NNN: ..." 里的状态码
            m = re.search(r"HTTP (\d+):", msg)
            if not m:
                raise  # 非 HTTP 错误（如网络断），直接抛
            status = int(m.group(1))
            if status >= 500 or status == 429:
                wait = 2 ** attempt + 0.1 * attempt  # 1s, 2s, 4s
                print(f"  [retry] HTTP {status}, sleeping {wait}s "
                      f"(attempt {attempt + 1}/{max_retries})",
                      file=sys.stderr, flush=True)
                last_err = e
                time.sleep(wait)
                continue
            raise  # 4xx（非 429）通常是 API 协议错，重试也没用
    raise RuntimeError(f"max retries exhausted: {last_err}")

# 在 agent_loop 里把 call_deepseek(messages) 改成 call_deepseek_with_retry(messages)
```

**不重试的错误**：401/403（权限）、400（消息协议错——你 toy_agent 已经踩过的"少传 reasoning_content 就 400"）。这种错误重试只会浪费 token。

### Patch 4：结构化事件（trajectory 雏形）

你的 trace 文件已经是 markdown 形式的 trajectory；这个 patch 增加**机器可读的 JSONL events**——这是后续训练数据导出（Ch11）的原料。

```python
import time as _time

class EventEmitter:
    """Append-only JSONL events。每个 event 是一行 JSON。"""
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.f = path.open("a", encoding="utf-8")
    def emit(self, kind, **payload):
        try:
            self.f.write(json.dumps({
                "ts": _time.time(),
                "kind": kind,
                **payload,
            }, ensure_ascii=False) + "\n")
            self.f.flush()
        except Exception as e:
            # 关键不变量：trajectory 记录失败 ≠ 任务失败
            print(f"  [emitter error swallowed] {e}", file=sys.stderr)
    def close(self):
        self.f.close()

# 在 agent_loop 里：
def agent_loop(user_msg, max_turns=30, trace_path=None):
    ...
    events_path = trace_path.with_suffix(".events.jsonl")
    em = EventEmitter(events_path)
    em.emit("run_start", model=MODEL, workspace=str(WORKSPACE_ROOT),
            user_msg=user_msg)
    try:
        for turn in range(max_turns):
            em.emit("turn_start", turn=turn + 1)
            resp = call_deepseek_with_retry(messages)
            choice = resp["choices"][0]; msg = choice["message"]
            em.emit("model_response",
                    turn=turn + 1,
                    finish_reason=choice.get("finish_reason"),
                    has_tool_calls=bool(msg.get("tool_calls")),
                    usage=resp.get("usage", {}))
            ...
            for tc in tool_calls:
                em.emit("tool_call",
                        turn=turn + 1,
                        tool_name=tc["function"]["name"],
                        tool_call_id=tc["id"],
                        arguments_raw=tc["function"]["arguments"])
                output = handler(args)  # 已有
                em.emit("tool_result",
                        turn=turn + 1,
                        tool_call_id=tc["id"],
                        output_size=len(output),
                        is_error=output.startswith("ERROR:"))
        em.emit("run_end", outcome="completed", final_answer_size=len(final_answer))
    except Exception as e:
        em.emit("run_end", outcome="error", error=repr(e))
        raise
    finally:
        em.close()
        tr.close()
```

跑一次后查看 `runs/run-XXX.events.jsonl`：每行一个事件，外部脚本能 grep / pandas 直接读。**这就是 trajectory store 的最小骨架**（Ch11 会扩展成 transcript + events + meta + diff 四件套）。

---

## 我们故意没做的事

| 没做 | 在哪一章 | 为什么这一章不做 |
|---|---|---|
| 流式 SSE 解析 | Ch8 | DeepSeek 也支持 stream，但加这一段会让循环复杂度翻倍。先把同步版的可中断、可恢复、可记录做透。 |
| Streaming tool execution | Ch2 | 工具执行的并行调度需要先讲清单工具的接口（Ch2 的主题）。 |
| Prompt-too-long 恢复 | Ch5 | 需要 compaction 抽象，本章不展开。 |
| Stop hooks | Ch4 | 需要 hook 系统，本章不展开。 |
| AbortController 树形传递 | Ch6 | 子 agent 才会出现"父 abort 传到子"的场景。本章用 process-wide flag 够了。 |

---

## → RepoHarness 对照（docs/03）

精读 [docs/03-agent-loop-and-message-protocol.md](../03-agent-loop-and-message-protocol.md) 后挑出 4 个核心点：

### 1. Agent loop 的"运行控制"和"最终评测"必须分开

docs/03 给出的伪代码：

```python
while turn < max_turns:
    response = call_model(messages, tools)
    recorder.record_assistant_message(response)
    if response.has_no_tool_calls():
        terminate("final_answer"); break
    tool_results = run_tools(response.tool_calls)
    messages.extend(to_tool_result_messages(tool_results))
    recorder.record_tool_results(tool_results)
    if last_tool_was_run_tests and last_verifier_result.accepted:
        stop_agent_loop("feedback_tests_passed"); break

# ── agent 已停 ──
final_verifier_result = run_final_verifier(workspace)   # ← 不是停止条件
recorder.record_verifier_result(final_verifier_result)
run_outcome = derive_run_outcome(agent_stop_reason, final_verifier_result)
```

注意三件事的字段拆分：

- `agent_stop_reason`：agent loop 自己以为为什么停（`final_answer` / `feedback_tests_passed` / `max_turns` / `error`）
- `final_verifier_status`：在 agent 停止后的最终 workspace 上重跑 verifier 的结果
- `run_outcome`：综合两者得出的"这次运行算不算成功"

**为什么必须拆**？想象一个 bug 场景：模型在第 5 轮调用 `run_tests`，verifier 说 accepted，agent 停了；但其实第 5 轮**之后**模型还可以再改文件——只是没跑。如果你只看 `agent_stop_reason="feedback_tests_passed"`，会以为成功了；但 `final_verifier` 在最终 workspace 上重跑时可能因为别的原因失败。**训练数据里把这种"agent 自以为成功，verifier 不认"的样本标对，是 reward signal 质量的关键。**

### 2. recorder 是 agent loop 的并行投影

注意 docs/03 的伪代码里**每个关键节点都有 `recorder.record_*`**。这就是你 Patch 4 的 `EventEmitter` 在做的事，但 RepoHarness 里它是**强契约**：

- recorder 的写入失败**不能**影响 agent loop 主流程（数据收集失败 ≠ 任务失败，所以你 patch 里的 `try/except + swallow` 写法是对的）
- recorder 必须**在每个状态变化的边界**写入（不是每秒一次轮询，而是事件驱动）
- recorder 不能反向影响 messages 内容（只读投影）

### 3. 消息协议的 4 类（system / user task / assistant / tool_result）

docs/03 把消息类型简化成 4 种。对照 Claude Code，少了什么？

| Claude Code 内部消息类型 | RepoHarness 是否需要 |
|---|---|
| `assistant` (含 tool_use) | ✓ |
| `user` (含 tool_result) | ✓ |
| `system` | ✓ |
| `SDKCompactBoundaryMessage` | △ 需要，但作为 events 记录而不是 message 类型（compact 摘要本身是 system 注入） |
| `TombstoneMessage`（消息被作废） | ✗ 训练数据里不应有"作废过的消息"——要么记录历史完整、要么不记录，不要中间态 |
| `ToolUseSummaryMessage`（工具执行摘要） | ✗ Claude Code 用 Haiku 生成 UI 摘要，RepoHarness 不需要 UI |
| `progress` / `attachment` | ✗ 这些是 UI 渲染需要的，trajectory 不记录 |

**简化的代价**：你失去了 Claude Code 那种"一条消息可以 yield 多次进度更新"的能力。**简化的收益**：trajectory schema 稳定，导出训练数据时不需要决定"progress 消息算不算训练 step"。

### 4. 中间 verifier 反馈 vs 最终 verifier

docs/03 提到一个细微点：**`run_tests` 工具的输出可以作为 feedback verifier**——模型每次跑测试看到的 fail/pass 都进 messages，用来指导下一步。它和 final verifier 的关系不是"互斥"而是"分工"：

- **feedback verifier** 决定 agent 行为（看反馈继续修 / 调整策略 / 停止）。它的输出**也会**进 events.jsonl，并可作为 reward metadata 的**辅助字段**——比如 feedback verifier 调用次数、各次失败类型、累计测试耗时等可以用作成本惩罚 / 行为分析 / 诊断
- **final verifier** 决定**最终成功判定**和**核心 reward 分数来源**——fail-to-pass / pass-to-pass 比例、accepted bool、final_verifier_status，这些只能由 agent 停止后在最终 workspace 上跑的 final verifier 决定

为什么这样分？因为模型在 agent loop 里跑测试频率可能很高，每次都算一次"成功"会让核心 reward 信号噪声很大；但完全丢掉这些信息又损失了诊断价值。**两类数据流分开记录、分开消费**：feedback 给模型看（导引行为）+ 进 metadata（辅助分析），final 给训练系统看（决定成败 + 主 reward）。

---

## 常见坑

1. **assistant message 必须原样保留 `tool_calls` 和 `reasoning_content`**——你 toy_agent 已经在第 264-274 行踩过了。教训：**模型给你的 assistant message 不要做任何裁剪**，拿到什么字段就 push 回什么字段。
2. **`role:"tool"` (DeepSeek/OpenAI) vs `user` + tool_result blocks (Anthropic) 协议差异**——这是协议层差异。如果你的 RepoHarness 要支持多 provider，必须有一层 message normalization（对应 Claude Code 的 `normalizeMessagesForAPI`）。
3. **取消检查不要放在 hot loop**——在 turn 边界和 tool batch 边界检查就够了。每个工具调用前后再检查一次也行。**别**每 100ms polling，浪费 CPU。
4. **重试不要重试协议错误**——4xx（除 429）大概率是你消息构造错了，重试只会一直 400。
5. **trajectory 写入失败必须 swallow**——这是软不变量：数据丢失 ≠ 任务失败。这条在 Patch 4 的 try/except 里。
6. **不要在 agent loop 里跑 final verifier 或计算最终 run_outcome**——feedback verifier（通过 `run_tests` 工具触发）**可以**在 agent loop 内出现，把结构化测试结果作为 tool_result 回灌给模型，这是设计内的事；但 **final verifier 必须在 agent 停止之后、workspace 已稳定的状态下跑**，且只有它能产出 `final_verifier_status` 和 `run_outcome`。把这两类混在一起会让"agent 自以为成功 vs verifier 认为成功"无法区分（见 RepoHarness 对照第 1 / 4 点）。

---

## 验证你已经掌握

读完本章你应该能口头回答：

- [ ] query.ts 里的 `state` 对象为什么要把 9 个字段收敛？解决了什么问题？
- [ ] `needsFollowUp` 这个 flag 在 query.ts 哪一行决定循环是否继续？
- [ ] StreamingToolExecutor 比同步版工具执行能省多少时间？为什么省？
- [ ] prompt-too-long 的三级恢复路径是什么？为什么每级只单次尝试？
- [ ] RepoHarness 为什么要把 `agent_stop_reason` / `final_verifier_status` / `run_outcome` 拆成三个字段？
- [ ] 4 个 patch 应用到 toy_agent 后，新增了哪些字段进 events.jsonl？

---

## 下一章预告

**第 2 章 Tool System**：把你 toy_agent 里的单个 `read_file` 工具扩展成完整的 Read / Edit / Write / Bash / Grep 工具集。重点：

- Tool 接口的 12+ 个字段为什么都需要（不只是 4 件套）
- `isReadOnly / isConcurrencySafe` 怎么驱动并行调度（让你的 agent 一轮跑 3 个 read 而不串行）
- Bash 工具的流式输出（async generator 模式）+ 超时控制
- `normalizeMessagesForAPI` 的内部消息→ API 协议转换
- RepoHarness 对照（docs/04）：`run_tests` 工具的特殊性——为什么它不能走普通 bash 路径
