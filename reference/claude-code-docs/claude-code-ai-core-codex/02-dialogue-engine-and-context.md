# 对话引擎与上下文装配

## 这篇解决什么问题

这篇要回答的是 Claude Code 最核心的问题：

1. 用户输入是怎样变成一次模型请求的？
2. system prompt、user context、system context 是怎样拼起来的？
3. 模型发出 `tool_use` 之后，结果又是怎样回流成下一轮消息的？

如果只看一篇来理解 Claude Code 的“AI 引擎”本体，这篇最接近那个核心。

## 核心类型与职责

本篇最重要的类型是下面这些：

| 类型 | 作用 |
| --- | --- |
| `QueryParams` | `query()` 单次执行循环的输入 |
| `QueryEngineConfig` | `QueryEngine` 的会话级配置 |
| `Message` | Claude Code 的统一消息模型 |
| `ToolUseContext` | query 与工具共享的运行时上下文 |
| `ContentBlockParam` | 最终发给模型 API 的块级内容 |

从职责上看：

- `QueryEngine` 更像“会话宿主”
- `query()` 更像“turn 执行引擎”
- `processUserInput()` 更像“输入预处理器”
- `fetchSystemPromptParts()` 更像“缓存前缀构造器”

## 关键源码

- `src/QueryEngine.ts`
- `src/query.ts`
- `src/utils/queryContext.ts`
- `src/utils/processUserInput/processUserInput.ts`
- `src/utils/messages.ts`
- `src/services/tools/toolExecution.ts`
- `src/services/tools/toolOrchestration.ts`
- `src/services/tools/StreamingToolExecutor.ts`

## 先分清 `QueryEngine` 和 `query()`

这两个名字很容易混。

### `QueryEngine`

`QueryEngine` 解决的是“长期会话管理”：

- 维护 `mutableMessages`
- 维护 `readFileState`
- 记录累计 usage
- 追踪 permission denials
- 接住 SDK/headless 语义，例如 replay、structured output、orphaned permission

它的典型入口是 `submitMessage()`。

### `query()`

`query()` 解决的是“这一轮怎么跑完”：

- 当前消息如何整理成模型输入
- 模型流式输出如何处理
- tool_use 如何执行
- tool_result 如何回流
- 什么时候继续下一轮
- 什么时候 compact / stop / terminate

一句话总结：

- `QueryEngine` 管 session
- `query()` 管 turn

## system prompt 是怎么拼出来的

`QueryEngine.submitMessage()` 里会先调用 `fetchSystemPromptParts()`。

这个函数返回三块内容：

- `defaultSystemPrompt`
- `userContext`
- `systemContext`

它被单独放进 `src/utils/queryContext.ts`，一个重要原因是要避免高层依赖形成循环。

### 为什么它只返回 parts，而不是直接返回完整 prompt

因为 Claude Code 想把“可缓存前缀”与“调用时可变部分”拆开。

这个设计很关键：

- `defaultSystemPrompt`
- `userContext`
- `systemContext`

这些通常比具体的一次用户输入稳定得多，因此它们适合被当成 cache-safe prefix。

之后 `QueryEngine` 再把这些 parts 组装成最终 `systemPrompt`：

1. 默认 system prompt 或 custom system prompt
2. 可选的 memory mechanics prompt
3. append system prompt

这就是为什么 `fetchSystemPromptParts()` 和真正的最终 prompt 组装是分开的。

## 用户输入如何进入对话系统

`QueryEngine.submitMessage()` 并不是直接把文本塞给模型，而是先交给 `processUserInput()`。

`processUserInput()` 会做几类事情：

1. 识别 slash command / 普通文本 / 特殊输入模式
2. 附加 attachments
3. 运行 `UserPromptSubmit` hooks
4. 决定这次输入是否真的要触发 query

它的返回结构很重要：

- `messages`
- `shouldQuery`
- `allowedTools`
- `model`
- `resultText`

这意味着用户输入处理的产物不只是“字符串”，而是：

- 新消息
- 本轮的工具约束
- 可选的模型覆盖
- 可选的“这其实是本地命令，不需要进模型”

这就是为什么 Claude Code 的 slash command 能和正常对话共存于同一套消息与 query 框架。

## 控制流分步讲解

先给出本篇最重要的一条主链：

`用户输入 -> processUserInput() -> fetchSystemPromptParts() -> QueryEngine / REPL -> query() -> 模型输出 -> tool_use / text -> tool_result 回流 -> 下一轮`

## 一次普通 turn 的主链

下面是从用户输入到模型响应的标准路径。

### 第 1 步：用户输入变成内部消息

`processUserInput()` 输出的 `messagesFromUserInput` 会被 push 进 `mutableMessages`。

如果这次输入只是本地命令，`shouldQuery` 会是 `false`，这次 turn 到此结束。

如果 `shouldQuery` 是 `true`，才继续进入模型循环。

### 第 2 步：生成 system init 与上下文

在 headless/SDK 路径下，`QueryEngine` 会先发出一条 system init message，告诉外部：

- 当前模型
- 当前工具
- 当前命令
- 当前 skills / plugins / MCP clients
- 当前 permission mode

这不是给模型看的，而是给外部宿主看的。

### 第 3 步：进入 `query()`

`query()` 的入参就是 `QueryParams`。里面最关键的字段是：

- `messages`
- `systemPrompt`
- `userContext`
- `systemContext`
- `canUseTool`
- `toolUseContext`

到了这一步，Claude Code 认为“一次对话循环所需的宿主条件已经齐了”。

### 第 4 步：把消息整理成真正的 API 请求

在 `query()` 内部，消息会经历几层处理：

1. `getMessagesAfterCompactBoundary()` 取当前有效消息窗口
2. `applyToolResultBudget()` 控制 tool result 体积
3. `prependUserContext(messagesForQuery, userContext)`
4. `appendSystemContext(...)` 或将 system context 合入 system prompt 路径
5. `normalizeMessagesForAPI(...)`

这里的核心思想是：

Claude Code 内部的消息模型比最终 API 消息更丰富，因此在真正发请求前必须做一次归一化。

## 模型输出如何进入工具执行

`query()` 会调用模型 API，并流式接收 assistant output。

如果输出里有 `tool_use` block，就会进入工具执行链。

这里分成两种执行模式：

### 模式 1：`StreamingToolExecutor`

如果当前 gate 允许 streaming tool execution，就会边流边执行工具。

它的设计目标是：

- tool_use 一出现就尽快启动
- 可并发的工具并发执行
- 结果仍按原始 tool_use 顺序回吐
- 如果 streaming fallback，能够丢弃已失效的执行结果

`StreamingToolExecutor` 会跟踪每个工具的状态：

- `queued`
- `executing`
- `completed`
- `yielded`

并根据 `isConcurrencySafe()` 决定能否与其他工具并发。

### 模式 2：`runTools()`

如果不走 streaming executor，就会在 assistant 消息完整出来之后调用 `runTools()`。

`runTools()` 的关键逻辑是：

- 先把 tool_use blocks 按 concurrency-safe 与否分批
- 可并发批次并发执行
- 不可并发批次串行执行
- 将 context modifier 按原始顺序回放，避免并发执行打乱上下文状态

这说明 Claude Code 不是简单地“拿到工具调用就全并发”，而是把并发能力做成每个工具自己的声明。

## tool result 如何回流成下一轮消息

这是 Claude Code 最关键的一环。

工具执行完成后，`toolExecution.ts` 会把工具输出转成 `tool_result` 对应的用户消息。

之后在 `query()` 里会发生两件事：

1. `yield update.message`，把结果发给外部观察者
2. `normalizeMessagesForAPI([update.message], tools)`，把它重新变成可供模型下一轮读取的消息

也就是说，tool result 既是“用户可见输出”，又是“下一轮模型上下文的一部分”。

这就是 Claude Code 的真正 agentic loop：

`assistant -> tool_use -> tool_result -> assistant`

## 为什么这套消息设计对 prompt cache 友好

源码里有很多细节都在保护 prompt cache 稳定性。

最有代表性的几个点：

### 1. `backfillObservableInput()` 只改观察者看到的输入

`Tool.backfillObservableInput()` 的用途，是给 SDK stream、hooks、transcript、权限系统补一些派生字段。

但它不会直接改原始 API-bound input。

原因很简单：

原始 input 一旦被改写，就可能让后续 prompt 前缀发生字节级变化，从而破坏缓存命中。

### 2. `fetchSystemPromptParts()` 把稳定前缀拆出来

system prompt、user context、system context 被拆成可重建的 parts，本质也是为了尽量稳定 cache key prefix。

### 3. tool result 体积被预算系统约束

`applyToolResultBudget()` 会在进入下一轮前限制大 tool result 的影响范围，避免一次超大输出把后续上下文拖得过长。

### 4. compact boundary 是显式的

Claude Code 不是随便删历史，而是通过 compact boundary 明确表示“之前的上下文已经被摘要化”。

这使得后续恢复、resume、headless truncation 都能保持语义一致。

## `QueryEngine` 在 headless 模式下额外做了什么

相比直接调用 `query()`，`QueryEngine` 还要额外处理这些问题：

- 维护累计 usage
- 维护 session transcript
- 处理 replayable user messages
- 处理 structured output enforcement
- 处理 orphaned permission
- 在 SDK 模式下产出 system init / result / error 等消息

因此它并不是一个简单 wrapper，而是 headless 会话的“主控器”。

## 关键设计权衡

### 1. 把“输入预处理”从“模型执行”里分离

`processUserInput()` 独立出来后，slash command、attachments、hooks 就不会把 `query()` 变成一个巨型入口函数。

### 2. 用统一消息模型承载一切

Claude Code 的 slash command、本地命令输出、tool_result、hook message、assistant reply 最终都汇入统一的消息流。

代价是 message model 会比较复杂。

收益是所有能力都可以共享同一个 agentic loop。

### 3. `QueryEngine` 与 `query()` 分离

这样 interactive 与 headless 可以共享 turn 逻辑，但又不强迫 REPL 也采用完整的 SDK 宿主对象。

### 4. 工具结果既面向用户，也面向下一轮模型

这是 agentic system 的核心设计。Claude Code 不是把工具当成旁路副作用，而是把工具结果重新喂回模型本身。

## 易错点与误解

### 误解 1：`processUserInput()` 只是字符串预处理

不是。它会决定本轮是否需要 query，还会影响 allowed tools、model override、attachments 和 hooks。

### 误解 2：`QueryEngine` 就是 agent loop

不准确。真正的 loop 在 `query()`。

### 误解 3：tool result 只是展示给用户看

不对。tool result 会被重新标准化并回流到下一轮模型上下文。

### 误解 4：并发工具执行是全局统一策略

不是。Claude Code 把并发安全声明下放到每个工具。

## 快照缺口说明

本篇主链所依赖的关键文件在当前快照中都能看到，没有出现阻断理解的核心缺口。

但需要注意：

- 某些 feature-gated 分支可能在当前构建中默认关闭
- 某些 helper 依赖的外围系统仍有大量动态 import，本文只覆盖主链行为

## 继续阅读建议

下一篇看 [03-tools-permissions-and-plan-mode.md](./03-tools-permissions-and-plan-mode.md)。那篇会把这篇里频繁出现但尚未展开的两个核心对象讲透：

- `Tool`
- `ToolPermissionContext`
