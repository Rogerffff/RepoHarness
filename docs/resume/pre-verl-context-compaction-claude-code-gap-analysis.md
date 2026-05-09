# Pre-verl 上下文压缩 Claude Code 对照分析与 RepoHarness 实施方案

更新时间：2026-05-09

本文是 `docs/resume/pre-verl-verifier-agent-evaluation-plan.md` 的上下文压缩专项补充，目标是在接入强化学习训练框架之前，回答一个具体问题：RepoHarness 当前作为软件工程智能体 Harness，已经能产生可执行、可审计、可导出的训练轨迹；但和 `reference/claude-code-typescript-src/` 下 Claude Code 参考实现相比，它的上下文压缩、会话记忆、压缩后恢复和长任务连续推理能力还缺什么，以及应该如何分阶段补齐。

本文不讨论 `grep` 搜索效率、工具命名、工具返回值排序等工具系统问题；这些问题已经由 `docs/resume/pre-verl-tool-system-claude-code-improvement-plan.md` 等文档覆盖。本文只关注上下文压缩相关能力。

说明：用户提到的参考入口是 `reference/claude-code-typescript-src/AGENT.md`，当前仓库中实际可读入口是 `reference/claude-code-typescript-src/AGENTS.md`。

## 1. 总结结论

RepoHarness 当前上下文管理已经具备一个重要基础：它能在每次模型调用前生成 `prepared_messages`，能把旧工具结果确定性替换成带 artifact 引用、sha256、恢复提示和头尾预览的模型可见文本，能记录 `context_revision`、`model_input_hash`、`content_replacement_state` 和 `context_prepared` 事件。这种实现非常适合评测、审计和训练导出，因为它能回答“某一轮模型调用实际看见了什么”。

但是，它仍然不是 Claude Code 类型的多层上下文压缩系统。当前实现更接近“确定性工具结果替换”，缺少以下关键层次：

1. 缺少由大语言模型或子智能体生成的结构化语义摘要，无法自动总结当前任务目标、已经尝试过的路径、失败原因、关键文件、当前补丁状态、测试结果和下一步动作。
2. 缺少后台 Session Memory（会话记忆）抽取机制，不能在长任务过程中持续维护一份短小、可复用、面向当前任务的工作记忆。
3. 缺少 prompt too long（提示过长）或 provider context limit（模型服务上下文上限）后的 reactive compact（反应式压缩）恢复链路，当前主要是在发送请求前超限就停止。
4. 缺少 post-compact rehydration（压缩后重新挂载工作状态），不会在摘要后自动重新注入计划、最近文件读取状态、当前 diff、关键文件片段、工具能力变化和诊断状态。
5. 缺少 compact boundary（压缩边界）作为一等事件，导致 resume（继续运行）、训练导出、上下文质量诊断不能像 Claude Code 那样围绕压缩边界重建会话。
6. 缺少“信息质量下降”的模型可见提醒。targeted smoke 中已经出现大量旧工具结果被替换，但因为 provider-ready token 数仍低于最大窗口，所以没有触发上下文 warning；模型没有被明确告知“旧观察已经折叠，请基于摘要和当前工作集收敛行动”。

因此，下一步最值得做的不是简单增大 `max_context_tokens`，也不是继续缩短工具输出预览，而是为 RepoHarness 增加“确定性替换 + 语义压缩 + 会话记忆 + 反应式恢复 + 压缩边界审计”的分层机制。长远看，这和 Claude Code 的能力方向一致；短期看，它能更准确地区分模型能力不足和 Harness 上下文管理不足。

## 2. 证据范围

本轮复核使用了四类材料。

第一类是 Claude Code 参考源码：

- `reference/claude-code-typescript-src/AGENTS.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/services/compact/autoCompact.ts`
- `reference/claude-code-typescript-src/services/compact/compact.ts`
- `reference/claude-code-typescript-src/services/compact/microCompact.ts`
- `reference/claude-code-typescript-src/services/compact/apiMicrocompact.ts`
- `reference/claude-code-typescript-src/services/compact/sessionMemoryCompact.ts`
- `reference/claude-code-typescript-src/services/compact/prompt.ts`
- `reference/claude-code-typescript-src/services/compact/grouping.ts`
- `reference/claude-code-typescript-src/services/compact/postCompactCleanup.ts`
- `reference/claude-code-typescript-src/services/SessionMemory/sessionMemory.ts`
- `reference/claude-code-typescript-src/services/SessionMemory/sessionMemoryUtils.ts`
- `reference/claude-code-typescript-src/services/SessionMemory/prompts.ts`
- `reference/claude-code-typescript-src/utils/messages.ts`
- `reference/claude-code-typescript-src/utils/sessionStorage.ts`

第二类是 Claude Code 介绍文档：

- `reference/claude-code-docs/claude-doc/10-context-memory-session.md`

第三类是 RepoHarness 当前实现：

- `src/repo_harness/context/manager.py`
- `src/repo_harness/context/schemas.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/trajectory/recorder.py`
- `src/repo_harness/trajectory/schemas.py`
- `src/repo_harness/model_client/providers/common.py`
- `src/repo_harness/run_metadata/writer.py`
- `docs/10-context-session-and-failure-diagnostics.md`
- `docs/v3/implementation-log/09-stage-09-context-compaction-and-long-rollout-diagnostics.md`
- `docs/resume/pre-verl-targeted-smoke-claude-code-remediation-plan.md`

第四类是当前测评产物：

- 23 条 formal run：`runs/pre-verl-agentloop-formal-deepseek-pro-23-preparedstatefix-20260508T041000Z/`
- 最新 targeted smoke：`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-capability-guidance-20260508T133407Z/`

## 3. Claude Code 的上下文压缩实现

Claude Code 的实现不是单个“压缩函数”，而是一个在主查询循环中分层执行的上下文生命周期系统。`AGENTS.md` 对 `query.ts` 的定位很关键：它是模型调用、工具循环、自动压缩、恢复、停止钩子和预算处理的核心状态机。也就是说，上下文压缩不是离线清理历史，而是每次模型调用前后都可能参与决策的运行时机制。

### 3.1 主循环中的压缩流水线

从 `query.ts` 可以看出，请求进入模型前大致会经过这些层次：

1. 取最后一次 compact boundary 之后的消息，避免把已经摘要过的历史再次原样送入模型。
2. 应用工具结果预算和历史片段裁剪，例如 history snip（历史裁剪）。
3. 执行 microcompact（微压缩），清理旧工具结果或通过 provider 侧 cache edit（缓存编辑）降低上下文占用。
4. 可选执行 context collapse（上下文折叠）。当前参考源码中该能力部分通过动态导入和功能开关出现，外部快照不一定包含完整实现，因此只能确认主循环为它保留了入口。
5. 判断是否需要 auto compact（自动压缩）。自动压缩会先尝试 Session Memory compact；不满足条件时回退到传统 LLM compact。
6. 发送模型调用。
7. 如果 provider 返回 prompt too long 这类可恢复错误，则尝试通过上下文折叠或反应式压缩恢复，再决定是否向用户暴露错误。

这个顺序非常重要。Claude Code 不是等到模型报错才压缩，也不是只靠一个固定 token 阈值裁掉旧消息。它先用低成本、局部、可重复的方式压缩工具结果，再在必要时用语义摘要重建会话。

### 3.2 AutoCompact：阈值、缓冲和熔断

`services/compact/autoCompact.ts` 体现了自动压缩的运行时边界：

- 它会为压缩摘要输出保留最多 `20000` 个 token。
- 自动压缩触发前还会留出 `13000` 个 token 的缓冲。
- warning 和 error 也有单独缓冲，避免模型请求刚好贴近窗口上限。
- 连续自动压缩失败达到 `3` 次后会熔断，避免在坏状态中反复压缩、反复失败。
- `querySource` 为 `session_memory` 或 `compact` 时会避免递归触发压缩，防止“压缩摘要时又触发压缩摘要”。
- 进入自动压缩后会先尝试 `trySessionMemoryCompaction`；如果 Session Memory 不可用、为空、过期、无法定位安全边界或者压缩后仍过大，就回退到传统 `compactConversation`。

对 RepoHarness 来说，这里的核心不是照搬具体数值，而是迁移三个原则：压缩要预留输出空间，要有失败熔断，要避免压缩子流程递归触发自身。

### 3.3 MicroCompact：工具结果的低成本压缩

`services/compact/microCompact.ts` 和 `services/compact/apiMicrocompact.ts` 负责比 LLM 摘要更轻量的上下文治理：

- 时间触发的 microcompact 会把较旧工具结果替换成固定占位文本，例如旧工具结果内容已经清理，同时保留最近至少一个结果。
- cached microcompact（缓存微压缩）不直接修改本地消息，而是在 provider 请求层生成 cache edits，等模型返回后再记录实际删除效果。
- API context management 可以告诉模型服务清理旧工具调用、工具结果或 thinking（思考）内容，默认策略还会设置目标输入 token 范围。

这和 RepoHarness 当前的确定性工具结果替换最接近。但是 Claude Code 把它放在更大的流水线里：microcompact 只是低成本第一层，不承担“理解当前任务状态”的责任。

### 3.4 LLM Compact：结构化摘要，不是自由散文

`services/compact/compact.ts` 和 `services/compact/prompt.ts` 体现传统压缩流程：

- 压缩前会去掉图片、文档和部分重复注入的附件，把它们替换成可解释占位文本。
- 摘要生成使用无工具的提示词，要求模型先分析再输出 summary（摘要）。
- 摘要结构要求覆盖用户原始请求、关键技术概念、文件和代码片段、错误与修复、问题解决过程、所有用户消息、待办事项、当前工作和下一步。
- 压缩结果会构造成模型可见的用户消息，告诉模型这是从之前上下文耗尽的对话继续而来。
- 自动压缩场景下，注入消息还会要求模型继续执行任务，不要向用户询问是否继续，也不要解释摘要本身。

这里最值得 RepoHarness 学的是“摘要格式是契约”。如果摘要只是自然语言回忆录，训练导出和后续调试都会很难判断摘要是否遗漏关键事实。RepoHarness 需要固定字段、固定证据来源和固定审计记录。

### 3.5 Session Memory：后台抽取的工作记忆

`services/SessionMemory/sessionMemory.ts`、`sessionMemoryUtils.ts`、`prompts.ts` 和 `services/compact/sessionMemoryCompact.ts` 显示，Claude Code 的 Session Memory 不是用户手写记忆，也不是完整 transcript，而是当前会话的工作状态摘要：

- 默认在会话达到约 `10000` token 后初始化记忆，之后每增加约 `5000` token 或达到一定工具调用节奏时更新。
- 抽取通常在模型采样之后的钩子中发生，只在主线程和功能开关允许时执行。
- 抽取使用隔离上下文运行 forked agent（分叉智能体），通过固定提示词更新会话记忆文件。
- 记忆模板包含 Session Title、Current State、Task specification、Files and Functions、Workflow、Errors & Corrections、Codebase and System Documentation、Learnings、Key results、Worklog 等部分。
- 使用 Session Memory compact 时，会计算最近消息保留边界，避免切断 tool_use 和 tool_result 配对，也避免切断共享同一个消息 id 的 thinking block。
- 如果 Session Memory 为空、过期、无法定位 last summarized message id，或者压缩后仍超过阈值，就回退到传统 LLM compact。

这说明 Claude Code 同时维护两种摘要：一种是实时后台更新的 Session Memory，另一种是触发压缩时生成或注入的 compact summary。前者更像持续维护的工作记忆，后者更像上下文窗口整理后的模型可见续跑说明。

### 3.6 Post-Compact Rehydration：压缩后重建工作状态

`compact.ts` 的 `buildPostCompactMessages` 和相关附件生成逻辑说明，压缩不是简单“历史变成摘要”。压缩后 Claude Code 会重新挂载多个动态上下文：

- compact boundary message（压缩边界消息）
- summary messages（摘要消息）
- messages to keep（必须保留的最近原始消息）
- 最近文件读取状态
- 当前计划文件和 plan mode（计划模式）状态
- 异步子代理状态
- 已调用技能和技能附件
- deferred tools（延迟工具）和工具定义变化
- MCP（模型上下文协议）相关说明变化
- session start hook（会话启动钩子）结果

这对 RepoHarness 非常关键。SWE Lite 任务不是聊天任务，模型需要恢复的是“工程工作状态”：看过哪些文件、当前补丁改了什么、哪些测试失败、哪些路径已经证明无效、下一步应该做什么。只把旧输出换成 preview 不能提供这种状态重建。

### 3.7 Compact Boundary 与 Resume

Claude Code 通过 `utils/messages.ts` 创建 compact boundary 和 microcompact boundary，通过 `utils/sessionStorage.ts` 在加载大型 transcript 时跳过压缩前内容、恢复 preserved segment（保留片段）、修复父子链和上下文折叠状态。

这说明压缩边界在 Claude Code 中是一等会话结构，不只是日志注释。它至少承担三件事：

1. 告诉模型从哪里开始看压缩后的连续上下文。
2. 告诉恢复逻辑哪些原始消息已经被摘要替代，哪些尾部消息必须保留。
3. 告诉审计和调试工具如何把 compact summary、原始 transcript 和 provider-ready messages 对齐。

RepoHarness 当前有 `context_revision` 和 `prepared_messages_ref`，这是很好的基础；但还需要把语义压缩边界作为更明确的数据结构引入。

### 3.8 现有介绍文档需要修正的地方

`reference/claude-code-docs/claude-doc/10-context-memory-session.md` 大体方向是有价值的，但本轮源码核对发现它有一些需要谨慎使用的地方：

- 文档中的部分路径带有 `src/` 前缀，而当前参考源码路径实际位于 `reference/claude-code-typescript-src/services/...`。
- 文档提到的若干 feature-gated（功能开关控制）模块，在当前外部源码快照中只看到动态导入或引用，无法完整检查实现细节。
- “microcompact 每次接口调用前执行”容易误导。更准确的说法是：每次请求前都会检查是否需要 microcompact，真正执行还受功能开关、模型支持、线程来源和时间间隔影响。
- cached microcompact 不是直接删除本地 transcript，而是生成 provider 请求层的 cache edits，并在响应后记录实际效果。
- Session Memory 不是 auto compact 的无条件替代方案；它需要满足功能开关、非空记忆、可定位安全边界、抽取完成或超时等待等条件。
- 文档对压缩后附件说明偏少，而源码中重新注入计划、技能、子代理、工具定义变化和会话钩子结果是重要能力。
- 恢复会话不只是读取 JSONL 文件，还包括压缩边界、父子链、保留片段、被中断工具调用和动态状态恢复。

因此，RepoHarness 后续设计应直接以源码中的行为不变量为准，而不是只依赖该介绍文档。

## 4. RepoHarness 当前上下文压缩实现

RepoHarness 当前实现的核心在 `src/repo_harness/context/manager.py`。

每次模型调用前，`AgentLoop` 会调用 `ContextManager.prepare_messages`，生成一次新的 `context_revision`，并写出：

- `prepared_messages` artifact，记录本轮 provider-ready messages。
- `content_replacement_state` artifact，记录所有已见工具结果及其替换状态。
- `model_input_hash`，绑定本轮模型输入。
- `provider_body_char_estimate` 和 `provider_ready_token_estimate`，用于预算判断。
- `context_prepared` event，记录 token 估算、替换信息和工具调用 / 工具结果配对校验结果。

当前 `ContextManagementConfig` 默认值包括：

- `max_context_tokens = 120000`
- `tool_result_aggregate_budget_chars = 40000`
- `keep_recent_turns = 6`
- `keep_recent_test_results = 2`
- `compact_threshold_ratio = 0.85`
- `compact_strategy = "deterministic_preview_replacement"`

当前压缩对象主要是 tool role message（工具结果消息）。非工具消息通常保留。旧工具结果如果超过聚合字符预算，或者内部估算达到阈值，就会被替换成如下类型的模型可见文本：

```text
[tool result replaced]
tool_result_id: ...
tool_name: ...
artifact_id: ...
sha256: ...
reason: tool_result_aggregate_budget_exceeded
normalized_arguments_sha256: ...
key_arguments: ...
recovery_call: ...
recovery_hint: ...
head:
...
tail:
...
```

这个设计的优点非常明确：

- 替换是确定性的，第一次替换后后续轮次复用同一段 replacement preview。
- 原始工具结果保留在 artifact 中，可以审计和导出。
- 替换文本给出恢复调用提示，模型可以重新读取相关文件或重新执行工具。
- 每轮都有 provider-ready 输入 artifact，可以复盘模型实际可见内容。
- 替换后会校验 tool call / tool result 配对，避免破坏 API 协议。

但是，它的能力边界也同样明确：

- 它只压缩工具结果，不会语义总结旧的 assistant reasoning（助手推理）、用户约束、计划变化、失败路径和当前补丁状态。
- 它不会生成“当前任务状态摘要”，模型仍然需要自己从多个 replacement preview 和最近消息中重建上下文。
- 它不会在大量 replacement 发生时自动注入“信息质量下降”的模型可见提示。
- 它没有 compact boundary 作为显式会话结构，只有 context revision 和 artifact 引用。
- 它没有后台 Session Memory，也没有在长任务中持续维护工作记忆。
- 它没有 provider 报错后的 reactive compact 重试链路。

`docs/10-context-session-and-failure-diagnostics.md` 对这个边界其实已经写得很清楚：第一版 `ContextManager` 的目标是“可实现、可复盘、可导出训练数据”，不是完整的 LLM auto compact、session memory compact 或 context collapse。当前 targeted smoke 说明，这个第一版已经到了需要升级的时候。

## 5. Targeted Smoke 暴露的上下文问题

最新 targeted smoke 目录为：

`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-tool-capability-guidance-20260508T133407Z/`

该轮配置较宽：

- `max_context_tokens = 180000`
- `compact_threshold_ratio = 0.85`
- `tool_result_aggregate_budget_chars = 40000`
- `max_turns = 48`
- `max_tool_calls = 96`
- `max_output_tokens = 8192`

5 条 targeted smoke 的结果为：

| 任务 | 停止原因 | 结果 | 轮数 | 工具调用数 |
| --- | --- | --- | ---: | ---: |
| `001_sqlfluff_1625` | `timeout` | `inconclusive` | 19 | 23 |
| `014_astroid_1333` | `max_turns` | `inconclusive` | 48 | 59 |
| `015_astroid_1196` | `final_answer` | `failed` | 24 | 30 |
| `017_astroid_1268` | `final_answer` | `success` | 8 | 11 |
| `020_pydicom_1413` | `final_answer` | `success` | 48 | 54 |

其中最能说明上下文问题的是 `014_astroid_1333` 和 `020_pydicom_1413`。

### 5.1 `014_astroid_1333`：没有爆窗口，但旧观察大量被替换

`014_astroid_1333` 到第 48 轮时：

- `context_prepared` 事件共有 48 次。
- `provider_ready_token_estimate = 62296`，远低于 `180000`，所以没有触发 context warning，也没有触发 context limit。
- `internal_token_estimate_before = 210146`，说明原始消息内部估算已经很大。
- `internal_token_estimate_after = 176558`。
- `tokens_before = 96367`，`tokens_after = 62296`。
- `effective_budget_reason = "internal_estimate_at_or_above_90_percent_threshold"`。
- `effective_tool_result_aggregate_budget_chars = 10000`。
- `replacement_preview_total_chars = 55807`。
- `content_replacement_state` 中 58 条工具结果记录里有 51 条已经 `replaced = true`。
- 事件中只有 `context_prepared`，没有 `context_warning_injected` 或 `budget_exhausted`。

这说明当前系统已经在大幅折叠旧工具结果，但模型没有收到“历史细节已经折叠”的语义提示。它只能看到很多 replacement preview，而不是看到一份清晰的当前工作状态摘要。

### 5.2 `020_pydicom_1413`：成功了，但上下文压力同样存在

`020_pydicom_1413` 到第 48 轮时：

- `provider_ready_token_estimate = 58660`，同样远低于 `180000`。
- `internal_token_estimate_before = 192775`。
- `internal_token_estimate_after = 166214`。
- `tokens_before = 85433`，`tokens_after = 58660`。
- `effective_budget_reason = "internal_estimate_at_or_above_90_percent_threshold"`。
- `effective_tool_result_aggregate_budget_chars = 10000`。
- `replacement_preview_total_chars = 41916`。
- `content_replacement_state` 中 54 条工具结果记录里有 43 条已经 `replaced = true`。
- 事件中同样没有 `context_warning_injected` 或 `budget_exhausted`。

这条任务最终成功，所以不能简单说“替换导致失败”。更准确的判断是：当前确定性替换足以避免一部分 context limit，但还没有把折叠后的历史转化成更有用的语义工作记忆。成功任务也在消耗大量轮数，说明上下文质量和收敛效率仍有提升空间。

### 5.3 23 条 formal run 的信号

23 条 formal run 目录为：

`runs/pre-verl-agentloop-formal-deepseek-pro-23-preparedstatefix-20260508T041000Z/`

该轮结果为：

- `success`: 6
- `failed`: 7
- `inconclusive`: 6
- `invalid_task`: 4
- `final_answer`: 13
- `max_turns`: 6
- `skipped_invalid_baseline`: 4

6 条 `max_turns` 任务是：

- `001_sqlfluff_1625`
- `003_sqlfluff_1733`
- `014_astroid_1333`
- `015_astroid_1196`
- `017_astroid_1268`
- `020_pydicom_1413`

这组数据不能单独证明上下文压缩是失败主因，因为工具能力、搜索质量、模型策略和任务难度都会影响结果。但结合 targeted smoke，可以得出一个更稳妥的判断：RepoHarness 已经能审计上下文，但它还不能像 Claude Code 那样在长任务中主动维护“当前工作记忆”和“压缩后的行动连续性”。这会让 `max_turns` 和长轮次成功同时出现，也会让评测很难判断失败到底是模型能力不足还是 Harness 没有提供足够清晰的连续上下文。

## 6. 主要差距清单

| 差距 | Claude Code 参考实现 | RepoHarness 当前实现 | 对 SWE Lite 测评的影响 |
| --- | --- | --- | --- |
| 分层压缩流水线 | 工具结果预算、microcompact、context collapse、auto compact、Session Memory、prompt-too-long recovery 组合执行 | 主要是确定性工具结果替换 | 能省 token，但不能主动维护语义连续性 |
| 语义摘要 | LLM compact 使用固定结构总结任务、文件、错误、待办、下一步 | 无自动语义摘要 | 模型需要从零散 replacement preview 中自行恢复任务状态 |
| 会话记忆 | 后台 Session Memory 周期性抽取并可优先用于压缩 | 无后台抽取；working state 主要依赖模型主动更新 | 长任务中关键发现容易散落在旧消息里 |
| 压缩边界 | compact boundary 是恢复、摘要和保留片段的会话结构 | 主要是 `context_revision` 和 artifact 引用 | resume 和导出能审计输入，但缺少语义边界 |
| 压缩后重建 | 摘要后重新挂载计划、最近文件、技能、工具定义、子代理和钩子结果 | 主要保留最近消息和 replacement recovery hint | 压缩后模型仍需要重新探索工作集 |
| 反应式恢复 | prompt too long 后可尝试压缩并重试 | 发送前超限通常停止为 `context_limit`；provider 错误分类存在，但缺少完整恢复链 | context limit 更容易成为终态失败，而不是一次可恢复事件 |
| 信息质量 warning | warning 与压缩、缓存、错误恢复共同作用 | 只有接近 `max_context_tokens` 的 warning | 大量替换但窗口未满时，模型不知道历史细节已经退化 |
| 训练导出语义 | compact summary、边界和 transcript 共同形成可恢复记录 | prepared messages 可审计，但语义摘要层不存在 | 轨迹可导出，但难以学习“压缩后继续任务”的行为 |

## 7. 在 RepoHarness 中实现多层上下文压缩的方案

建议按阶段实施，不要一次性复制 Claude Code 的所有功能。RepoHarness 的目标是训练轨迹可执行、可审计、可导出，因此每个阶段都要先保证证据结构、污染边界和 inspect 命令，再扩大自动化能力。

### 7.1 阶段 0：冻结当前确定性替换为 L0 层

先把当前能力明确命名为 L0 deterministic tool-result replacement（第 0 层确定性工具结果替换），不要把它和语义压缩混在一起。

建议补齐：

1. 在 run metadata 中显式记录 `context_compaction_layers_enabled`，例如 `["l0_tool_result_replacement"]`。
2. 在 `context_prepared` 事件中增加 `replaced_tool_result_count`、`seen_tool_result_count`、`replacement_ratio` 和 `replacement_preview_total_chars` 的扁平字段，方便快速分析。
3. 在 transcript 记录或 `model_call_started` 事件中更直接绑定 `context_revision`，避免复盘者只看 transcript 时无法知道某轮实际输入。
4. 增加 `inspect-model-visible-context` 类型的检查命令，输入 run dir 和 context revision，输出该轮模型实际看见的 system、user、assistant、tool 消息摘要和 sha256。
5. 明确 `provider_ready_token_estimate` 是 provider body 字符数除以 4 的估算，不是 provider 原生 tokenizer；不要把它解释成精确 token。

这个阶段不改变模型行为，只让现有上下文证据更容易复盘。

### 7.2 阶段 1：增加“信息质量下降”提示

当前 warning 只在 provider-ready token 达到 80% 或 90% 时触发。targeted smoke 表明，另一个重要信号是 replacement ratio（替换比例）和 replacement preview 规模。

建议增加一个新的模型可见、不可训练控制消息：

```json
{
  "repo_harness_control_message": {
    "type": "context_quality_warning",
    "trainable": false,
    "reason": "many_old_tool_results_replaced",
    "replaced_tool_result_count": 51,
    "seen_tool_result_count": 58,
    "instruction": "较早工具结果已经被折叠为可恢复预览。请基于最近消息、当前 diff、已读文件路径和明确失败路径收敛下一步行动；如确需旧细节，请按 recovery_call 重新读取最小范围。"
  }
}
```

触发条件可以先保守设置：

- `replacement_ratio >= 0.5`，并且至少 12 条工具结果已替换。
- 或 `replacement_preview_total_chars >= 30000`。
- 或内部估算已经超过 `max_context_tokens * 0.9`，即使 provider-ready 估算仍较低。

这一步不需要 LLM 摘要，但可以立刻缓解“窗口没爆、历史已折叠、模型却不知道”的问题。

### 7.3 阶段 2：实现 L1 语义压缩

L1 semantic compact（第 1 层语义压缩）是最关键的能力。它应在当前确定性替换之外，生成一份结构化、模型可见、可审计的工作状态摘要。

建议新增 schema：

```text
SemanticCompactionState:
  schema_version
  run_id
  compaction_id
  source_context_revision
  target_context_revision
  trigger_reason
  source_message_ids
  source_message_hashes
  kept_message_ids
  summarized_message_ids
  summary_artifact_ref
  summary_hash
  summary_model
  summary_prompt_version
  hidden_material_policy
  contamination_scan_status
  trainable: false

CompactionBoundaryRecord:
  boundary_id
  parent_context_revision
  child_context_revision
  compacted_message_count
  preserved_recent_message_count
  preserved_tool_pair_policy
  model_visible_summary_ref
  prepared_messages_ref_after_boundary

WorkingMemorySnapshot:
  task_goal
  user_constraints
  current_hypothesis
  files_read
  symbols_or_functions
  edits_made
  tests_run
  failures_and_corrections
  dead_ends
  next_actions
```

触发条件建议：

- `provider_ready_token_estimate >= max_context_tokens * 0.7`。
- 或 `internal_token_estimate_before >= max_context_tokens * 0.9`。
- 或 `replacement_ratio >= 0.6` 且任务仍未进入补丁阶段。
- 或出现 provider context limit 错误。
- 或 no-progress 诊断显示连续多轮只读、空搜索或重复搜索。

摘要输入边界必须严格：

- 只能使用当前模型已经可见的 transcript、公开 task description、公开工具结果、当前 diff 和公开 budget 状态。
- 不能读取 hidden test patch、gold patch、final verifier 原始输出、reward、accepted outcome 或 evaluator-only selector。
- 如果工具 artifact 是 evaluator-only 或 redacted，只能引用 redaction 状态和 artifact id，不能摘要其内容。

摘要输出应使用固定结构，建议包含：

```text
1. 当前任务目标
2. 用户和 Harness 明确约束
3. 已确认的仓库事实
4. 已读文件和关键符号
5. 已尝试路径和失败原因
6. 当前补丁状态
7. 已运行测试和可见结果
8. 仍不确定的问题
9. 下一步最小行动计划
10. 如需恢复旧细节，应重新读取的最小文件范围
```

压缩后的 provider-ready messages 应按固定顺序构造：

1. 原 system message 和必要的工具协议说明。
2. compact boundary control message，标明这是一次 Harness 生成的上下文压缩边界。
3. semantic summary user message，`trainable = false`。
4. 最近若干轮原始消息，例如最近 6 轮或最近 10000 token，必须保持 tool call / tool result 成对。
5. 当前 diff 摘要、已修改文件列表和最近一次测试结果。
6. 如有 no-progress 诊断，加入一条短的模型可见纠偏提示。

注意：语义压缩摘要本身可以模型可见，但训练导出时默认应标记为不可训练。它是 Harness 生成的辅助观察，不是人类用户自然指令，也不是模型应该模仿生成的答案。

### 7.4 阶段 3：实现 L2 Session Memory

Session Memory 不应做成跨任务长期记忆。RepoHarness 的评测目标要求任务之间隔离，因此这里的 Session Memory 应只存在于单个 run 目录中，服务于当前任务。

建议路径：

```text
run_dir/session_memory/session_memory.md
run_dir/session_memory/session_memory_state.json
```

建议触发策略：

- 初始抽取：模型可见上下文累计达到约 10000 token 后。
- 更新抽取：每增加约 5000 token、每 3 到 5 次工具调用、或者每次补丁后测试失败时。
- 抽取时机：模型返回之后、下一轮模型调用之前。
- 抽取执行：使用独立 summarizer provider 或同一 provider 的低成本模型；禁止工具调用；只输入模型可见材料。

建议 Session Memory 模板：

```text
# Session Title
# Current State
# Task Specification
# Files And Symbols
# Workflow
# Errors And Corrections
# Tests And Feedback
# Current Patch
# Dead Ends
# Next Actions
# Worklog
```

自动压缩时优先使用 Session Memory：

1. 如果 Session Memory 存在、未过期、覆盖了 last summarized message id，并且压缩后仍低于阈值，就用它构造 compact summary。
2. 如果 Session Memory 不存在、为空、过期或压缩后仍过大，就回退到 L1 语义压缩。
3. 如果 L1 语义压缩失败，最多重试一次；连续失败后停止自动压缩并记录熔断事件。

### 7.5 阶段 4：实现 reactive compact

当前 RepoHarness 已经能把 provider context limit 类错误分类为 `context_limit`，但还缺少“先压缩再重试”的恢复链路。

建议在 provider request 失败后增加：

1. 如果错误分类为 `context_limit`，并且本轮尚未执行 emergency compact（紧急压缩），触发 L1 语义压缩。
2. 保留最近 API round，不能切断 tool call / tool result 配对。
3. 重新生成 `prepared_messages`、`model_input_hash` 和 provider body。
4. 记录 `reactive_compaction_attempted` 事件，包括原错误、触发原因、压缩前后 token 估算、摘要 artifact、是否重试成功。
5. 如果仍超限或 provider 再次拒绝，停止为 `context_limit`，并在 run metadata 中标明 `compaction_applied_but_insufficient_context_limit = true`。
6. 设置最多 1 到 2 次 emergency compact，避免失败循环。

这样可以把“上下文超限”从直接终态失败变成一次可恢复事件。即使最终失败，也能清晰说明失败是“压缩后仍然超限”，而不是没有尝试恢复。

### 7.6 阶段 5：实现 compact boundary resume 和导出绑定

当 L1 / L2 开始改变模型可见历史时，resume 和 training export 必须同步升级。

建议新增检查：

- `inspect-context-compaction-boundary <run_dir> --context-revision N`
- `inspect-model-visible-context <run_dir> --context-revision N`
- `inspect-session-memory <run_dir> --assert-public-input-only`
- `inspect-context-export <export_dir> --assert-prepared-message-binding`

训练导出应遵守：

- 每个训练样本绑定当时的 `prepared_messages_ref`，不能统一使用最终压缩后的 transcript。
- compact summary 和 context warning 默认 `trainable = false`，但可以作为 observation 进入模型输入。
- 原始被压缩内容保留在 run artifact 中，但默认不进入训练输出。
- 摘要生成过程的输入、输出、prompt version、model id、hash 和污染扫描状态必须可审计。
- 任何 hidden verifier、gold patch、hidden selector、final accepted outcome 都不能进入摘要输入。

resume 应遵守：

- 从最近一个 compact boundary 之后恢复模型可见消息。
- 恢复 `ContentReplacementState`，保证旧工具结果替换文本稳定。
- 恢复 `SessionMemoryState`，但要校验其 source hashes 是否与 transcript 一致。
- 恢复当前 workspace diff、已修改文件列表和最近测试结果。
- 如果 compact boundary 或 session memory 校验失败，应降级为普通 run-level continuation，而不是静默使用不可信摘要。

## 8. 建议落地顺序

推荐按以下顺序推进：

1. **先做 inspect 和指标字段。** 增加 replacement ratio、context quality warning 触发证据、model-visible context inspect。这一步风险最低，可以立刻提高评测解释力。
2. **再做模型可见 context quality warning。** 当大量旧工具结果被替换时，给模型明确、短小、不可训练的行动收敛提示。
3. **实现 L1 semantic compact 的最小版本。** 只在 targeted smoke 或长任务中打开，用固定摘要结构和严格可见性边界验证效果。
4. **把 L1 接入 reactive compact。** provider context limit 后先压缩再重试，失败再停止。
5. **实现 L2 Session Memory。** 在 L1 稳定后再做后台抽取，避免一开始就引入难以审计的隐式记忆。
6. **升级 resume 和 export。** 让 compact boundary 成为 transcript、prepared messages、training export 和 run metadata 之间的共同锚点。

如果只能先做一个阶段，优先做 L1 semantic compact。因为 targeted smoke 暴露的核心问题不是“完全没有 token 空间”，而是“旧观察已经被折叠，但折叠后的语义状态没有被重建”。

## 9. 验收标准

新增上下文压缩能力不能只靠主观观察验收，建议至少满足以下标准。

### 9.1 单元测试

- 压缩后 tool call / tool result 仍严格成对。
- 压缩边界不能落在 assistant tool_use 和对应 tool_result 中间。
- 摘要输入不包含 evaluator-only artifact、hidden test patch、gold patch、final verifier 原始输出或 accepted outcome。
- `ContentReplacementState` 在压缩前后保持稳定，已经替换的工具结果不会生成不同 replacement preview。
- L1 摘要 artifact 的 source hashes 能和源消息对齐。
- 连续压缩失败会触发熔断，不会无限递归。

### 9.2 集成测试

- 构造一个长工具输出任务，确认 L0 替换先发生，随后 L1 semantic compact 在阈值下触发。
- 构造一个 provider context limit 假错误，确认 reactive compact 会重试一次，并记录压缩前后 token 估算。
- 构造一个大量替换但未接近 `max_context_tokens` 的任务，确认会注入 `context_quality_warning`。
- 构造一个包含 hidden artifact 的任务，确认摘要只引用 redaction 状态，不读取隐藏内容。
- 构造一个 resume 场景，确认从 compact boundary 恢复后的 prepared messages hash 可复现。

### 9.3 Targeted Smoke 验收

至少复跑：

- `001_sqlfluff_1625`
- `014_astroid_1333`
- `015_astroid_1196`
- `017_astroid_1268`
- `020_pydicom_1413`

重点观察：

- `014_astroid_1333` 不应在 48 轮中只出现大量替换而没有模型可见上下文质量提示。
- `020_pydicom_1413` 即使成功，也应显示是否通过 L1 summary 或 context quality warning 减少了重复探索。
- 如果仍然 `max_turns`，run metadata 应能区分模型策略失败、工具事实失败、上下文压缩不足和任务本身难度。
- 如果出现 context limit，应能看到 reactive compact 是否尝试、是否成功、失败原因是什么。

### 9.4 Formal 23 验收

23 条 formal run 报告中应新增上下文字段：

- 每条任务最大 provider-ready token 估算。
- 每条任务最大 internal token 估算。
- L0 replacement 次数和最高 replacement ratio。
- L1 semantic compact 次数。
- L2 session memory 更新次数。
- context quality warning 次数。
- reactive compact 尝试次数和成功次数。
- context failure owner：`model_strategy`、`tool_fact_quality`、`context_quality_degraded`、`context_limit_after_compaction`、`environment_or_task_invalid`。

这些字段能帮助简历展示结果更可信：不是只报 success rate（成功率），而是能说明 Harness 如何把模型失败、工具失败、上下文失败和任务无效分开。

## 10. 与项目边界的关系

实现这些能力时，需要保持 RepoHarness 的项目定位：

- RepoHarness 仍然是面向软件工程智能体训练和评测的 Harness，目标是可执行、可审计、可导出的训练轨迹。
- 参考 Claude Code 是为了借鉴架构不变量，例如 query loop、tool contract、permission boundary、context compaction、session recovery 和 transcript diagnostics；不要把 Claude Code TypeScript 参考源码描述成 RepoHarness 的运行依赖。
- Docker execution mode 只能描述为 Docker-based executable repository environment，不能描述成生产级安全沙箱。
- Session Memory 在评测中应是 run-local（单次运行本地）的工作记忆，不应跨任务携带模型不可见经验。
- 摘要和记忆必须只来自模型可见材料和公开运行状态，不能成为隐藏 verifier 或 gold patch 的泄漏通道。

## 11. 最终建议

当前 RepoHarness 已经解决了“上下文可审计”的第一层问题，但还没有解决“上下文被压缩后，模型是否仍然拥有足够清晰的工程工作状态”这个更难的问题。Claude Code 的实现说明，成熟的 agent harness 不会只依赖单次 token 裁剪，而是把上下文治理拆成微压缩、语义摘要、会话记忆、压缩后重建、错误恢复和会话恢复多层。

在接入强化学习训练框架之前，建议把上下文压缩作为独立里程碑推进。最小可交付目标是：在现有 L0 确定性工具结果替换之上，新增 L1 结构化语义压缩、context quality warning 和 reactive compact，并用 targeted smoke 证明它能减少“窗口没爆但历史语义断裂”的长任务失败模式。等 L1 稳定后，再实现 L2 Session Memory 和 compact boundary resume。

这条路线既不破坏 RepoHarness 当前最强的审计能力，也能逐步接近 Claude Code 产品级上下文管理的关键能力。对于后续简历展示，它能把结果从“我跑了 23 条 SWE Lite 任务”提升为“我能解释每条任务中模型、工具、上下文和 verifier 各自造成了什么影响，并能证明 Harness 自身没有把上下文管理问题误算成模型能力问题”。
