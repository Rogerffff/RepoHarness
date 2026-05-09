# Pre-verl Claude Code 参考差距复核

本文记录 RepoHarness 在接入强化学习训练框架之前，对照 `reference/claude-code-typescript-src/` 下 Claude Code TypeScript 参考实现后，仍然可能存在的 agent harness 差距。

本文的目标不是要求 RepoHarness 复制 Claude Code 的产品界面、交互体验、账号体系或者完整插件生态。RepoHarness 的目标仍然是产生可执行、可审计、可导出的软件工程智能体训练轨迹。因此，本文只关注会影响正式测评可靠性、训练轨迹质量、工具可用性、上下文完整性、权限可审计性和批量运行稳定性的差距。

## 1. 本轮复核依据

### 1.1 RepoHarness 侧依据

- `docs/00-reading-guide.md` 到 `docs/12-resume-narrative-and-demo-artifacts.md`
- `docs/v1/` 到 `docs/v5/` 中的 scope、implementation plan、walkthrough、final acceptance 和 review 文档
- `docs/resume/pre-verl-verifier-agent-evaluation-plan.md`
- `docs/resume/pre-verl-agentloop-evaluation-execution-plan.md`
- `docs/resume/pre-verl-agentloop-harness-hardening-implementation-plan.md`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/context/manager.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/permissions/system.py`
- `src/repo_harness/model_client/providers/common.py`
- `src/repo_harness/model_client/providers/deepseek.py`
- `src/repo_harness/model_client/providers/openai.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/export/exporter.py`

### 1.2 Claude Code 参考侧依据

用户提到的 `reference/claude-code-typescript-src/AGENT.md` 在当前仓库中对应为 `reference/claude-code-typescript-src/AGENTS.md`。该文件是 Claude Code TypeScript 参考源码导航，正文标题仍使用 “AGENT.md - Claude Code TypeScript 源码导航”。

重点参考文件包括：

- `reference/claude-code-typescript-src/AGENTS.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/QueryEngine.ts`
- `reference/claude-code-typescript-src/Tool.ts`
- `reference/claude-code-typescript-src/services/api/withRetry.ts`
- `reference/claude-code-typescript-src/services/tools/toolExecution.ts`
- `reference/claude-code-typescript-src/services/tools/toolOrchestration.ts`
- `reference/claude-code-typescript-src/services/tools/toolHooks.ts`
- `reference/claude-code-typescript-src/tools.ts`
- `reference/claude-code-typescript-src/tools/ToolSearchTool/ToolSearchTool.ts`
- `reference/claude-code-typescript-src/utils/toolSchemaCache.ts`
- `reference/claude-code-typescript-src/tools/AgentTool/runAgent.ts`
- `reference/claude-code-typescript-src/context.ts`
- `reference/claude-code-typescript-src/utils/conversationRecovery.ts`
- `reference/claude-code-typescript-src/utils/sessionRestore.ts`
- `reference/claude-code-typescript-src/utils/sessionStorage.ts`
- `reference/claude-code-typescript-src/services/lsp/LSPDiagnosticRegistry.ts`
- `reference/claude-code-typescript-src/query/tokenBudget.ts`

## 2. 本文刻意不重复的已知问题

`docs/resume/pre-verl-agentloop-harness-hardening-implementation-plan.md` 已经覆盖并正在安排修复的问题，本文不重复提出。主要包括：

- `bash` 工具说明、拒绝原因、统一命令策略、`safe_argv` 绑定、非 formal hardening smoke 和 formal baseline 中 `bash.enabled=false` 的冻结记录。
- `grep` 的正则表达式模式、分页、截断恢复、结果统计和替代工具提示。
- `read_file` 的行号、文件哈希、截断恢复、可复制原文边界和 hidden path 禁读。
- `edit_file` 的 `expected_content_hash`、重复匹配保护、行号前缀误复制恢复和写入边界。
- 统一工具输出限制、`list_files` 分页和噪声控制、`git_diff` 变更文件摘要和截断恢复。
- `read_file`、`grep`、`list_files`、`git_diff` 的符号链接策略一致性。
- 上下文替换的可恢复信息，尤其是大工具结果被 artifact 替换后，模型如何继续读取。
- tool call 和 tool result 配对从记录项升级为 formal hard gate。
- transcript 中 assistant text 和 tool calls 同时保留，避免只保留 preview。
- raw provider request / response 的字段级脱敏、prepared messages 与 provider body 等价检查、model-visible context inspect。
- hidden test patch、hidden selector、gold patch、final verifier 原始输出等 evaluator-only 材料不得进入模型可见上下文或默认训练导出。
- empty patch、预算耗尽、provider 问题、环境问题和 final verifier rejected 的失败归因区分。
- pre-verl TaskDefinition、final verifier boundary、formal budget freeze 和 smoke gate。

本文后续条目只列出上述计划之外的新增差距，或者虽然与上述计划相邻但属于不同层次的问题。

## 3. 总体结论

当前 RepoHarness 已经有清晰的 task -> workspace -> tools -> agent loop -> trajectory -> verifier -> reward / eval / export 主链路，并且 V5 已经形成 core acceptance 证据。对照 Claude Code 参考实现后，本轮新增差距集中在六类：

1. 真实 provider 长跑韧性不足：缺少统一 retry、fallback、输出截断恢复和 malformed tool call 修复回合。
2. 预算和运行时状态仍偏“声明式”：有字段和文档要求，但缺少每轮 token、cost、继续运行原因、停止原因的行为级审计。
3. 工具系统的产品级协议不完整：工具声明中已有只读和并发安全标记，但 runtime 没有并发调度；工具契约也缺少 per-input capability、hook、tool result context modifier 和 interruption semantics。
4. 上下文和会话能力较浅：缺少 git 状态、层级项目说明、任意中断点 resume、文件历史和编辑归因。
5. 批量运行稳定性还需要从单 run 证据扩展到全局 provider 配额、故障注入验收和统一取消清理。
6. 未来扩展边界尚未产品化：MCP、延迟工具发现、子代理 sidechain、LSP 诊断和 prompt injection 诊断都还不适合直接纳入当前 formal baseline，但需要在文档中明确为后续方向，避免被误认为已经实现。

如果目标是在正式二十三题 pre-verl agent loop 测评前降低“把 Harness 问题误判成模型能力不足”的风险，最建议优先处理或者至少显式冻结的条目是：Provider retry、Provider 输出截断恢复、malformed tool call 修复回合、当前权限裁决顺序和禁用项冻结、`run-task` primary provider 入口一致性、成本和 token 预算决策记录、Provider 故障注入 smoke。其他条目可以作为 formal 报告中的 known limitations 或 post-pre-verl hardening backlog。

## 4. 优先级总表

| 编号 | 差距 | 优先级 | 是否建议正式 pre-verl 测评前处理 | 简要原因 |
| --- | --- | --- | --- | --- |
| G1 | Provider 可重试错误没有统一退避重试 | P1 | 建议处理 | 限流、网络抖动和五百类服务端错误会直接污染 accepted rate。 |
| G2 | Provider 输出达到 `max_output_tokens` 后没有继续生成或单独归因 | P1 | 建议处理 | 长补丁或长解释被截断时会被误记为普通 `context_limit` 或 `model_error`。 |
| G3 | malformed provider tool call 缺少模型可见修复回合 | P1 | 建议处理 | 偶发 JSON 或工具调用格式错误本可恢复，现在会直接终止整题。 |
| G4 | 通用权限决策需要冻结当前裁决顺序，完整多来源裁决链尚未实现 | P2，formal freeze 部分为 P1 | 建议显式冻结 | 当前不需要复制完整企业权限系统，但必须让当前规则顺序、禁用项和拒绝原因可审计。 |
| G5 | `repo-harness run-task` 的 primary provider 入口与 V5 专用 provider matrix 存在断层 | P1 | 建议处理 | formal pre-verl 计划要求走正式 `run-task`，不能依赖旁路矩阵代码。 |
| G6 | token / cost 预算有字段但缺少行为级决策记录 | P2，若做 budget comparison 则升为 P1 | 建议至少记录 | 预算对 accepted rate 影响很大，成本字段不能长期停留在默认值。 |
| G7 | 只读工具声明了并发安全，但 Agent Loop 串行执行 | P2 | 可以延后 | 影响 wall clock 和 timeout 风险，但改并发会增加事件顺序复杂度。 |
| G8 | 缺少 streaming 或长耗时阶段 liveness / progress 事件 | P2 | 建议记录型处理 | 长 provider call 或长工具调用期间难以区分正常等待、卡死和 provider 慢。 |
| G9 | 没有 no-progress 检测和重复失败诊断 | P2 | 建议先 diagnostic-only | 可减少无效循环，但自动停止策略需要谨慎。 |
| G10 | 工具契约缺少 per-input capability、interruption semantics 和 tool result context modifier | P2 | 可以延后 | 当前小工具集勉强可用，但扩展工具后会影响安全、并发和可复现性。 |
| G11 | 工具生命周期 hook 还只是快照或禁用事实，不是统一执行协议 | P2 | 可以延后，但要显式禁用 | formal baseline 可以禁用 hook，但未来插入审计器或任务专用策略需要统一协议。 |
| G12 | 任意中断点 durable session resume 不完整 | P2 | 可以延后 | 批量长跑和训练轨迹生产会需要，二十三题单机顺序运行可以先规避。 |
| G13 | 模型初始上下文缺少 git 状态、脏工作区摘要、层级项目说明和 `AGENTS.md` 识别 | P2 | 建议轻量处理 | 这会影响模型定位项目规则和审计起始状态。 |
| G14 | 延迟工具发现、动态工具池和 schema 缓存策略尚未产品化 | P2 | 可以延后 | 固定小工具集已有 schema snapshot 基础，但扩展 MCP 或 scaffold-specific tools 前必须补齐。 |
| G15 | 文件历史和编辑归因快照不足 | P2 | 可以延后 | 不一定影响 accepted rate，但会降低过程奖励、偏好对和失败复盘价值。 |
| G16 | `run_batch` 与 V4 rollout queue / resource lock 没有统一到 formal pre-verl runner | P2 到 P3 | 可以延后或明确顺序执行 | 大规模评测时会影响资源、重试和 structured skip 的一致性。 |
| G17 | Prompt injection 和 instruction conflict 只有文本边界，没有诊断闭环 | P3 | 不建议阻塞当前测评 | 当前任务不是对抗性指令评测，但后续真实仓库采集需要。 |
| G18 | 缺少符号级代码检索和 LSP / lint 异步诊断协议 | P3 | 不建议阻塞当前测评 | 可提升复杂仓库效率，但引入后必须冻结版本和交付规则。 |
| G19 | MCP / plugin / skill 运行时工具源没有纳入 formal tool protocol | P3 | 不建议阻塞当前测评 | 当前 baseline 使用内置工具即可；扩展生态前需要审计边界。 |
| G20 | 模型可调用子代理和 sidechain transcript 缺失 | P3 | 不建议阻塞当前测评 | 多代理会显著扩大可见性、归因和训练导出边界。 |
| G21 | provider comparison 聚合报告缺少统一协议族维度 | P2 到 P3 | 建议在 provider comparison 前记录 | 当前已有 provider message format 和部分冻结字段，但跨 provider 比较还需要协议族、工具协议和 usage metadata 维度。 |
| G22 | 批量级 provider quota、rate limit 和 circuit breaker 不完整 | P2，若并行正式运行则升为 P1 | 顺序运行可延后，并行运行前建议处理 | 单 run retry 不足以处理二十三题或更大批量运行时的全局限流和预算放大。 |
| G23 | Provider 故障注入 smoke 不完整 | P1 | 建议处理 | G1 到 G3 如果没有确定性故障注入，就很难证明恢复逻辑真的可用。 |
| G24 | Provider、工具、命令和 final verifier 的取消与清理传播不统一 | P2 | 可以延后或作为 known limitation | 长任务或批量运行被中断时，缺少统一 abort / cleanup 证据会影响恢复和归因。 |

## 5. 详细发现

### G1. Provider 可重试错误没有统一退避重试

Claude Code 参考实现中，`services/api/withRetry.ts` 对 429、529、部分五百类错误、连接重置、OAuth 凭证刷新和 fallback model 都有明确的 retry / fallback 状态机。`QueryEngine.ts` 还会把 API retry 作为结构化系统消息输出，包含 attempt 和 retry delay。

RepoHarness 目前已经有若干与 retry 相关的字段：`src/repo_harness/model_client/schemas.py` 中有 `ModelRequestContext.retry_policy` 和 `ModelCallEvent.retry_count`；`src/repo_harness/model_client/providers/deepseek.py` 与 `src/repo_harness/model_client/providers/openai.py` 会把 429、500、503、504、timeout 等错误标为 `retryable=True`。但是 `src/repo_harness/agent_loop/loop.py` 调用 `model_client.generate()` 后，如果 `response.model_error_type` 非空，就直接把 agent 停止原因为 `model_error`。这些 `retryable=True` 信息没有进入统一退避重试控制器。

评测影响：正式二十三题中，临时网络错误、provider 限流和短暂服务端错误会被算成单题失败或 provider failure。这样得到的 accepted rate 会把基础设施波动混入模型能力，尤其是在真实 provider 成本较高、每题只运行一次时影响很大。

建议：在正式 pre-verl 测评前实现轻量统一 retry。第一版可以只覆盖 `rate_limited`、`provider_timeout`、`provider_error` 且 `retryable=true` 的错误，最多重试 2 到 3 次，使用指数退避和上限延迟。每次 attempt 都必须写入独立 request / response artifact、attempt index、delay、最终 `retry_count` 和最终 terminal reason。不要把 fallback provider 的成功混入 primary provider accepted rate；fallback 只能作为独立状态或 diagnostic evidence。

### G2. Provider 输出达到 `max_output_tokens` 后没有继续生成或单独归因

Claude Code 的 `query.ts` 中有 `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT`，并且在 hitting max output tokens 时会尝试提高输出上限或发送 continuation 类恢复消息。它把“输入上下文太长”和“输出 token 上限被打满”当成不同问题处理。

RepoHarness 在 `src/repo_harness/model_client/providers/common.py` 中把 provider response 的 `finish_reason == "length"` 直接转为 `model_error_type="context_limit"`。随后 `src/repo_harness/agent_loop/loop.py` 遇到 `model_error_type` 就终止。这里没有区分输入 prompt 太长、输出太长、patch 太长和 provider 特定的 response truncation。

评测影响：模型可能已经完成大部分修复，只是最后补丁或总结被输出上限截断。当前归因会把它记成 `model_error` 或 `context_limit`，既不利于模型可恢复，也不利于分析是否应该调大 `max_output_tokens`。

建议：把 `finish_reason=length` 归因为独立的 `output_token_limit_reached` 或 `max_output_tokens_exhausted`。第一版可以在 policy 冻结条件下允许一次 continuation attempt，或者在不继续生成时也必须在报告中把它从输入上下文超限中分离出来。`max_output_tokens` 本身已经属于 formal budget freeze 范围；本条新增要求是 continuation 是否启用、最大 continuation 次数和 continuation prompt hash 必须成为额外可审计字段。

### G3. Malformed provider tool call 缺少模型可见修复回合

Claude Code 的工具执行链会把不少可恢复协议错误转成模型可见 observation，让模型有机会重新发出合法工具调用。例如 deferred tool 未加载时会提示先调用 ToolSearch；部分 hook 或权限结果也会说明“可以重试”。

RepoHarness 在 `src/repo_harness/model_client/providers/common.py` 的 tool call parsing 中，如果 provider 返回的工具调用参数不是合法 JSON、缺少函数名或协议结构异常，会产生 `model_error_type="tool_call_parse_failure"` 或 `provider_protocol_error`。`AgentLoop` 之后把它当作 terminal model error，而不是构造一个模型可见的协议错误 tool result 或 assistant repair turn。这个方向与既有 message protocol 设计中“可恢复协议错误尽量回流给模型”的目标一致，但尚未进入当前 hardening plan 的正式实施项。

评测影响：真实 provider 偶发输出格式问题时，本来可以通过“请重新发出合法 JSON 工具调用”的一轮恢复继续任务。当前会直接损失整题，尤其对复杂工具 schema 和长上下文更敏感。

建议：正式 pre-verl 前至少支持一次 malformed tool call 修复回合。恢复 observation 应该明确说明哪个 tool call id、哪个字段、什么错误、应该如何重新调用。恢复回合必须写入 transcript 和 raw provider artifacts，并且如果恢复失败，需要把最终失败归因为 `tool_call_parse_failure_unrecovered`，而不是普通 `model_error`。

### G4. 通用权限决策需要冻结当前裁决顺序，完整多来源裁决链尚未实现

Claude Code 的 `services/tools/toolHooks.ts` 和 `toolExecution.ts` 会合并工具自身权限、hook 决策、deny / ask / allow 规则、自动分类器和用户权限模式，并且强调 hook allow 不能绕过更高优先级的 deny / ask 规则。权限结果包含来源、是否来自 hook、是否可重试和是否向模型展示。

RepoHarness 的 `src/repo_harness/permissions/system.py` 已经有 `PermissionContext`、`PermissionDecision`、`matched_rule`、workspace boundary、敏感路径、bash safety、read-only auto allow、plan / ask / deny 模式等逻辑。`PermissionDecision` 也已经记录 `policy_version`、`matched_rule`、`reason`、`non_interactive_resolution` 等字段。现有硬化计划重点处理 bash 策略，本条关注所有工具的通用权限治理。

当前差距不是要求 RepoHarness 变成完整企业权限系统，也不是要求复制 Claude Code 的用户交互权限流程。真正需要补齐的是：formal run 必须能说明当前这些固定代码路径的裁决顺序是什么、哪些扩展能力被禁用、拒绝原因是否模型可见、相同输入是否会得到相同决策。完整的 hook allow / deny / ask 多来源优先级链可以放到 post-pre-verl。

评测影响：当后续加入 hook、MCP、符号检索、诊断工具、子代理或仓库专用策略后，同一个模型动作为什么被允许、拒绝、要求改用其他工具，会变得难以解释。训练导出中也无法稳定回答“模型是否因为权限策略失败，而不是因为不会修复”。

建议：正式 pre-verl 前先增加轻量 `permission_policy_manifest`，显式记录当前裁决顺序、`permission_policy_version`、`hooks.enabled=false`、`mcp.enabled=false`、non-interactive resolution、模型可见 recovery hint 和 policy hash。每次 tool call 至少记录 matched rule、拒绝或允许原因、是否来自只读自动允许、是否来自敏感路径或 workspace boundary。完整多来源 priority chain、hook allow 不能绕过 deny / ask 的合并规则、工具自身动态权限和 classifier 可以作为 post-pre-verl 扩展。

### G5. `repo-harness run-task` 的 primary provider 入口与 V5 专用 provider matrix 存在断层

Claude Code 的核心 query loop 是统一入口：命令行、软件开发工具包、子代理和工具调用最终都围绕同一套模型调用、工具回流、权限和上下文状态机运行。

RepoHarness 的正式 pre-verl 执行计划明确要求废弃旧 pilot 路径，走 `repo-harness run-task` 和正式 AgentLoop。然而 `src/repo_harness/evaluation/runner.py` 当前对 `model.provider=openai` 仍有 primary provider 限制，只允许作为 DeepSeek fallback smoke run。与此同时，`src/repo_harness/v5_run_matrix.py` 已经有 OpenAI / DeepSeek provider-axis 相关路径和 V5 专用矩阵证据。

评测影响：如果正式 pre-verl 二十三题使用 `run-task`，而 V5 provider matrix 使用另一套入口，就可能出现“矩阵能跑、正式单题入口不能跑”或者“单题入口和矩阵入口的 provider 归一化、成本预算、raw artifact、failure taxonomy 不一致”。这会削弱 provider comparison 和正式 accepted rate 的可信度。

建议：在正式 pre-verl 前统一 provider registry 和 `run-task` provider allowlist。DeepSeek、OpenAI 等 primary provider 应通过同一个 AgentLoop、同一个 final verifier adapter、同一个 provider raw artifact 绑定和同一个 failure taxonomy。V5 专用矩阵代码应该是调度层和报告层，不应该成为绕过正式运行入口的 provider runtime。

### G6. Token / cost 预算有字段但缺少行为级决策记录

Claude Code 的 `query/tokenBudget.ts` 和 `QueryEngine.ts` 会根据 token 使用量、预算、最大花费和继续运行策略决定是否继续，并把超预算结果作为结构化 outcome。

RepoHarness 的 `src/repo_harness/budget/schemas.py` 有 `max_cost` 和 `BudgetState.cost`，`src/repo_harness/agent_loop/loop.py` 会累加 input / output tokens。但是当前主 AgentLoop 没有根据 provider、model 和 token usage 更新 `BudgetState.cost`；`src/repo_harness/evaluation/metrics.py` 中的 cost estimate 默认也容易停留在 0 或外部估算。`_budget_stop_reason` 虽然检查 `max_cost`，但如果 cost 不更新，该检查无法真实生效。现有 hardening plan 已经覆盖 formal budget freeze 和预算耗尽失败归因，本条新增关注的是 runtime 是否真的做了每轮预算决策。

评测影响：budget comparison 对 accepted rate 影响非常大。如果 cost budget 只是报告字段，而不是 runtime decision，就无法严格说明某个 run 是因为预算耗尽、provider 元数据不可用、人工外部预算限制，还是模型确实失败。`docs/resume/pre-verl-verifier-agent-evaluation-plan.md` 已经要求 provider 不返回 token 或 cost metadata 时必须写成 `unavailable_provider_metadata`，不能填猜测值冒充真实返回值。

建议：在正式测评前至少增加 per-turn budget decision trace。每轮模型调用后记录 token source、cost source、cost availability、estimated 或 provider-returned 标记、是否接近预算、为什么允许下一轮、为什么停止。如果暂时不实现真实美元成本计算，必须把 `max_cost` enforcement 标为 disabled 或 unavailable，不能让 `cost=0` 看起来像真实低成本。

### G7. 只读工具声明了并发安全，但 Agent Loop 串行执行

Claude Code 的 `services/tools/toolOrchestration.ts` 会把连续的 concurrency-safe 工具调用分批，并发执行后再按原始 tool call 顺序提交 context modifier。`Tool.ts` 中 `isConcurrencySafe(input)` 是 per-input 方法，不是单纯静态标记。

RepoHarness 的 `src/repo_harness/tools/minimal.py` 中，`read_file`、`grep`、`list_files`、`git_diff` 等只读工具已经标记 `is_concurrency_safe=True`。但是 `src/repo_harness/agent_loop/loop.py` 对 `response.tool_calls` 逐个循环执行，实际 runtime 没有使用这个标记。

评测影响：模型一次请求多个文件读取或多个搜索时，串行执行会增加 wall clock 时间。对于 timeout 较紧的正式任务，这可能把“工具调度较慢”伪装成“模型没有及时完成”。不过并发会增加事件顺序、artifact 顺序和调试复杂度，因此不宜仓促改动。

建议：短期在 formal manifest 中明确记录 `tool_execution_mode=serial`，不要让 `is_concurrency_safe=True` 被误解成 runtime 已并发。后续实现只读工具并发时，必须保证 transcript 中 tool result 顺序仍按原始 tool call 顺序稳定提交，context modifier 延后提交，artifact 引用可复现。

### G8. 缺少 streaming 或长耗时阶段 liveness / progress 事件

Claude Code 的 `query.ts` 和 `QueryEngine.ts` 使用 streaming 模型调用，能在模型生成、工具执行、API retry、fallback 和中断恢复中持续产生状态事件。即使没有产品界面，这些事件也能帮助判断运行是否卡住。

RepoHarness 当前 provider client 基本是非 streaming 的 `generate()` 调用。长时间真实 provider call、长命令、长 Docker-based executable repository environment 操作期间，trajectory 中通常只在阶段完成后出现结果。没有 time-to-first-token、provider stream event count、heartbeat、last activity 或阶段级 progress 事件。

评测影响：正式批量运行时，如果某个任务等待很久，很难区分 provider 慢、网络卡住、工具进程未返回、Docker-based executable repository environment 卡住，还是 agent loop 逻辑死锁。失败归因会依赖外部日志，而不是 harness 自身 evidence。

建议：不必为了 pre-verl 立即实现完整 streaming，但建议增加 liveness events。至少记录 `phase_started`、`last_activity_at`、provider call elapsed、tool call elapsed、retry wait started / ended、heartbeat interval 和 timeout owner。未来如果接入 streaming provider，需要把流式半成品和最终 assistant message 的提交规则写清楚，避免半截输出进入训练样本。

### G9. 没有 no-progress 检测和重复失败诊断

Claude Code 的 query loop 有多种停止、恢复和 hook retry 限制，避免在同一类错误中无限循环。RepoHarness 文档和 `src/repo_harness/agent_loop/schemas.py` 已经出现 `no_progress` stop reason，相关设计也提到重复失败诊断；差距在于 `src/repo_harness/agent_loop/loop.py` 当前没有把重复工具失败、重复 diff hash、重复 permission denied、重复 schema error 或无效编辑循环检测接入运行时。

评测影响：模型可能在同一类错误上消耗大量轮次，最后只表现为 `max_turns`、`max_tool_calls` 或 `task_timeout`。这会低估有产品级循环防护时的完成率，也会让失败复盘不够明确。

建议：第一版不要直接硬停止，可以先 diagnostic-only。每轮记录 diff hash、工具错误 fingerprint、permission denial fingerprint、schema error fingerprint、最近 N 轮是否产生文件变化、是否重复读取同一大文件或重复无效 edit。正式报告中增加 `no_progress_suspected_count`，但不要在没有充分回归测试前把它计入 terminal stop reason。

### G10. 工具契约缺少 per-input capability、interruption semantics 和 tool result context modifier

Claude Code 的工具协议同时包含两类能力。第一类是 `Tool.ts` 上的 per-input capability 方法和元数据，例如 `isConcurrencySafe(input)`、`isReadOnly(input)`、`isDestructive(input)`、`interruptBehavior`、`requiresUserInteraction`、`isOpenWorld`、`inputsEquivalent`、`preparePermissionMatcher`、`backfillObservableInput`、`maxResultSizeChars`。第二类是工具执行结果或工具执行更新携带的 `contextModifier`，用于在工具完成后按确定顺序修改后续上下文。这些能力都会影响调度、权限、UI 之外的 runtime 行为和可审计性。

RepoHarness 当前 `ToolDefinition` 已有名称、描述、输入 schema、静态 `is_read_only` 和静态 `is_concurrency_safe`。这对当前最小工具集足够简单，但它不能表达“同一个工具在不同输入下是否只读”“某个工具是否会打开外部世界”“被中断时应该继续、取消还是等待清理”“工具结果是否要修改后续上下文”等细节。

评测影响：当后续增加 `bash` diagnostic、symbol search、lint feedback、MCP 工具或子代理时，静态工具标记会变得过粗。错误的并发安全判断可能导致状态污染；错误的只读判断可能导致权限过宽；没有 tool result context modifier 协议会使动态上下文注入变成临时全局状态，破坏轨迹可复现性。

建议：保持当前 formal baseline 简单，但为 V6 或 post-pre-verl 设计 `ResolvedToolCapability`。每次 tool call 都应记录基于具体 input 解析出的 `read_only`、`concurrency_safe`、`destructive`、`open_world`、`requires_user_interaction`、`interrupt_behavior`、`max_result_chars` 和 `capability_policy_hash`。

### G11. 工具生命周期 hook 还不是统一执行协议

Claude Code 的 `services/tools/toolHooks.ts` 和 `toolExecution.ts` 会在同一条工具执行链中运行 `PreToolUse`、`PostToolUse`、`PostToolUseFailure`，并允许 hook 阻断、补充上下文、要求重试或记录失败。hook 的结果再进入权限和工具结果协议。

RepoHarness V4 已经有 hook policy snapshot 或 hooks disabled 相关审计事实，但当前 runtime 更接近“记录 hook 被禁用或策略冻结”，而不是可插拔的前后置 hook 执行协议。

评测影响：如果后续想加入 secret scan、仓库专用 lint、训练数据标签器、额外安全检查或实验性 feedback tool，只能改工具本体或 agent loop 主逻辑。这样不同 baseline 的工具行为容易混在一起，难以审计“这是工具本身行为”还是“hook 注入行为”。

建议：当前 formal final-only baseline 可以继续禁用 hook，但必须显式记录禁用状态。未来启用 hook 时，hook 输入、输出、阻断原因、模型可见文本、是否允许重试、artifact 引用和 policy hash 都必须进入 tool lifecycle trace。

### G12. 任意中断点 durable session resume 不完整

Claude Code 的 `QueryEngine.ts` 会在模型调用前持久化用户消息；`conversationRecovery.ts` 能识别中断 turn 并注入继续消息；`sessionRestore.ts` 和 `sessionStorage.ts` 能恢复 file history、sidechain transcript、context collapse state 等状态。

RepoHarness V4 已经覆盖 batch resume、checkpoint state 和禁止继承 evaluator-only context 的审计边界。但是这不等于产品级“任意中断点恢复同一条 agent loop”。例如 provider 请求已经发出但未返回、工具调用完成但 tool result 尚未写入、context replacement state 已更新但 prepared messages artifact 尚未绑定，这些细粒度中断点是否可恢复，还没有形成统一协议。

评测影响：长 rollout 或真实 provider 批量运行中，如果机器重启、进程被 kill、provider timeout 或 Docker-based executable repository environment 异常退出，可能出现缺 turn、重复工具执行、artifact 不完整或同一 run 无法继续的问题。训练轨迹生产越长，这个问题越明显。

建议：正式二十三题可以先用外部运行器规避任意中断恢复，把失败记为 structured terminal outcome。但 post-pre-verl 应设计 durable turn commit protocol：进入 provider 前、provider 返回后、每个 tool requested、tool result persisted、context revision persisted、final verifier started / finished 都有可恢复边界。

### G13. 模型初始上下文缺少 git 状态、脏工作区摘要、层级项目说明和 `AGENTS.md` 识别

Claude Code 的 `context.ts` 会注入 git status snapshot、当前 branch、main branch、最近 commits、当前日期和项目 memory。子代理还会根据需要减少或重建 git context。`AGENTS.md` 识别则主要来自 RepoHarness / Codex 工作流中的项目说明文件惯例，而不是 Claude Code 参考实现本身的核心约定。

RepoHarness 的 `src/repo_harness/context/builder.py` 当前读取根目录 `AGENT.md`、`README.md`、`CLAUDE.md`、`CONTRIBUTING.md`，每个有长度限制，并将它们标记为 untrusted repository context。这里有几个差距：

1. 当前文件名列表包含 `AGENT.md`，但 RepoHarness / Codex 工作流中的项目说明文件更常见的是 `AGENTS.md`。
2. 只读取仓库根目录说明，没有按目录层级查找更靠近目标文件的说明。
3. 没有向模型提供起始 git status、当前 branch、source tree hash、是否已有用户改动、哪些文件属于 generated 或 evaluator-only。
4. 没有把“哪些项目说明被注入、哈希是什么、截断到了哪里、适用哪些路径”写成独立可 inspect 的上下文索引。

评测影响：真实仓库中测试命令、编码规范、生成文件规则和模块边界经常写在子目录说明里。模型拿不到这些信息会影响修复质量。另一方面，如果不把起始脏工作区状态告诉模型和审计器，后续很难区分模型改动、setup 改动和用户已有改动。

建议：正式 pre-verl 前可以做轻量修复：加入 `AGENTS.md` 识别；注入简洁 git/source snapshot；记录 repo context index artifact，包含文件路径、sha256、截断信息、适用范围和 untrusted boundary。完整层级 instruction resolution 可以延后，但不要把根目录读取误认为完整项目记忆。

### G14. 延迟工具发现、动态工具池和 schema 缓存策略尚未产品化

Claude Code 的 `tools.ts` 会稳定组装内置工具和 MCP 工具；`ToolSearchTool.ts` 支持 deferred tools；`utils/toolSchemaCache.ts` 会缓存工具 schema 渲染，避免 feature flag 或 MCP 状态变化破坏提示词缓存和可复现性。

RepoHarness 当前固定小工具集是合理选择，并且已经有 tool schema snapshot、tool schema hash、allowed tools 和 export audit 相关基础。这个固定工具集场景已经被现有 hardening plan 进一步覆盖，本文不把“固定工具集每轮 schema 绑定”重复列为新增缺口。

真正的新增差距出现在未来扩展场景：如果引入 MCP、插件、scaffold-specific tools、diagnostic tools 或 deferred tools，仅记录最终 allowed tools 不够。需要知道哪些工具一开始可见，哪些工具通过工具搜索发现，哪些工具被动态加载，schema 渲染何时被缓存，feature flag 或 connector 状态变化是否导致工具面漂移。

评测影响：工具顺序、描述、schema 或可见性的一点漂移都可能改变模型行为。固定小工具集下这个风险已经较低；但动态工具面一旦打开，如果没有 deferred tool manifest 和 tool search trace，后续无法复现“模型当时为什么知道或不知道某个工具”。

建议：当前 formal baseline 可以继续固定工具集，并复用现有 tool schema snapshot 机制。未来加入 deferred tools 时，应新增 `deferred_tool_manifest`、`tool_search_result_trace`、`selected_tool_schema_hash`、动态工具加载事件和 schema cache invalidation 事件，并把工具搜索本身作为模型可见 tool result 导出。

### G15. 文件历史和编辑归因快照不足

Claude Code 的 session restore、file history 和 FileEditTool 相关代码会维护文件编辑历史、诊断重置和恢复信息。它不仅关心最终 patch，也关心不同阶段对文件状态的影响。

RepoHarness 已经有 final patch、tool results、artifact manifest 和 git diff。硬化计划也会加强 `edit_file` 的哈希和重复替换保护。但是当前仍然缺少“每个用户消息、每个 scaffold phase 或每个 tool call 对应的文件历史快照”和“哪一轮引入了哪部分 diff”的一等审计对象。

评测影响：训练数据审计时，如果只能看到最终 patch 和零散 tool result，就难以回答“这处错误改动是哪一轮引入的”“某次失败编辑是否被后续修正”“planner_coder_verifier 中哪个阶段贡献了有效修改”。这会削弱过程奖励、偏好对构建和失败复盘质量。

建议：post-pre-verl 增加 `file_history_snapshot` 或 `edit_attribution_index`。最小字段包括 file path、pre hash、post hash、tool_call_id、turn_id、scaffold phase、diff hunk summary、是否后续被覆盖、是否进入最终 patch。

### G16. `run_batch` 与 V4 rollout queue / resource lock 没有统一到 formal pre-verl runner

Claude Code 的 QueryEngine 和后台任务机制会围绕生命周期、abort、状态输出和资源清理运行。RepoHarness V4 已经实现过 rollout queue、resource lock、resume 和 acceptance evidence，但 `src/repo_harness/evaluation/runner.py` 的 `run_batch` 仍然偏顺序执行；V5 / pre-verl 的矩阵调度也存在专用代码路径。

评测影响：二十三题或更大规模正式评测如果依赖外部脚本并行，资源锁、provider rate limit、cost budget、structured skip、retry 和 artifact 命名可能分散在多个地方。这样会降低批量运行证据的一致性。

建议：如果当前 pre-verl 正式评测选择顺序执行，应在 formal report 中明确 `batch_execution_mode=sequential`，并说明 V4 rollout queue 不在本轮评测范围内。如果要并行执行，则应复用 V4 resource lock / queue 机制，而不是让脚本自行并发调用 `run-task`。

### G17. Prompt injection 和 instruction conflict 只有文本边界，没有诊断闭环

Claude Code 会把项目 memory、工具权限、系统提示和用户输入放在明确的层级中处理。RepoHarness 当前在 `src/repo_harness/context/builder.py` 中已经把仓库文件和 issue text 标为 untrusted context，并说明它们不能覆盖系统安全规则。

差距在于：RepoHarness 目前主要依赖提示词文字来建立边界，没有结构化 prompt injection / instruction conflict 检测、风险报告、对抗性 fixture 或违规响应统计。硬化计划覆盖的是 hidden material 反向匹配和 evaluator-only 泄漏，本条关注的是仓库文本本身诱导模型忽略系统规则、调用禁用工具、输出隐藏材料或污染训练样本。

评测影响：当前 SWE-Bench-like formal baseline 不一定包含恶意仓库说明，因此这不是本轮阻塞项。但如果未来采集真实 issue、PR、README 和仓库 agent 指令作为训练数据，就需要知道模型是否被不可信文本诱导。

建议：作为 diagnostic-only 后续任务集推进。新增 `repo_context_instruction_boundary_report`，记录注入文件、哈希、截断、boundary text、潜在冲突语句和模型是否遵守高优先级规则。不要在当前 pre-verl formal baseline 仓促加入会改变模型上下文的大型过滤器。

### G18. 缺少符号级代码检索和 LSP / lint 异步诊断协议

Claude Code 参考实现中有 LSP diagnostics registry，能对语言服务器诊断做跨 turn 去重、限量、排序，并作为附件交付给模型。它还具备更丰富的代码导航产品能力。

RepoHarness 当前主要依赖 `list_files`、`grep`、`read_file`、`edit_file`、`git_diff` 和 final verifier。硬化计划会显著改善这些基础工具，但没有覆盖 symbol-aware retrieval，例如定义跳转、引用搜索、类 / 函数索引、类型检查诊断和 lint daemon。

评测影响：在大仓库或强类型语言任务中，模型可能花很多轮用文本搜索定位符号和调用链。缺少公共静态诊断时，模型也可能直到 final verifier 才发现类型错误。需要注意的是，如果启用 LSP 或 lint feedback，它会改变模型可见信息，必须冻结版本、触发时机和截断规则。

建议：不要把它作为当前 formal pre-verl 的阻塞项。后续可以增加只读 `symbol_search`、`definition_lookup` 或 `diagnostics` 工具，并且把工具版本、索引来源、诊断命令、截断规则、是否模型可见写入 formal manifest。

### G19. MCP / plugin / skill 运行时工具源没有纳入 formal tool protocol

Claude Code 通过 MCP、插件、skills 和工具搜索扩展工具面，并且围绕权限、schema、缓存和工具可见性做了大量 runtime 处理。

RepoHarness 当前 V4 / V5 文档会记录 MCP 或 hooks disabled 的审计事实，但 runtime 主链路仍以 built-in minimal tools 为主。这对当前可评测、可导出训练轨迹的目标是合理的：固定小工具集比开放生态更容易保证分母清晰。

评测影响：如果未来希望用仓库专用检查器、外部知识库、包管理器服务或 issue 平台作为工具源，当前没有一套 connector manifest、secret boundary、schema snapshot、tool result artifact 和训练导出策略。直接把这些能力接入会破坏现有可复现性。

建议：当前 formal baseline 明确 `mcp.enabled=false`、`plugin_tools.enabled=false`、`skill_tools.enabled=false`。后续扩展时必须把 connector identity、tool schema hash、secret redaction policy、permission policy、tool result visibility 和 export allowlist 作为一等字段。

### G20. 模型可调用子代理和 sidechain transcript 缺失

Claude Code 的 `tools/AgentTool/runAgent.ts` 会创建独立子代理，拥有独立 agent id、工具池、权限上下文、sidechain transcript、metadata，并在 finally 中清理 MCP、hooks、file state cache 和后台任务。

RepoHarness 的 `docs/09-agent-scaffolds-and-multi-agent.md` 已经清楚说明，早期版本主要是顺序式多角色 scaffold，不是后台多代理系统。`src/repo_harness/scaffolds/planner_coder_verifier.py` 也更像单一 AgentLoop 内的阶段策略，而不是模型可调用的独立 subagent tool。

评测影响：复杂任务中，产品级 agent 可以委托搜索、审查或并行定位。RepoHarness 当前无法导出 nested trajectory，也无法对 planner、coder、verifier 或子代理分别做 reward attribution。对当前单代理 SWE-Bench-like baseline 来说，这不是硬阻塞；对未来多代理训练数据来说，这是重要缺口。

建议：不要在当前 pre-verl 前引入真实子代理。后续如果实现，必须先定义 parent / child transcript 边界、sidechain artifact visibility、permission inheritance、workspace isolation、cost attribution、reward attribution 和 final export schema。

### G21. Provider comparison 聚合报告缺少统一协议族维度

Claude Code 参考实现主要围绕 Anthropic Messages streaming、thinking、prompt cache、tool use block 和 fallback 状态机设计。RepoHarness 当前真实 provider 主要走 OpenAI-compatible Chat Completions 风格适配，并在 DeepSeek 上处理 `reasoning_content` 等 provider 私有状态。

RepoHarness 已经有 `provider_message_format` 和部分 provider-specific freeze 字段，现有 hardening plan 也要求绑定 provider、model、provider-specific options、DeepSeek thinking policy 和 OpenAI API mode。因此，本条不是说当前完全没有 provider 协议审计基础。

真正的差距在 provider comparison 聚合层：Chat Completions、OpenAI Responses API、Anthropic Messages、DeepSeek reasoning replay 的工具调用格式、streaming 行为、缓存字段、usage metadata 和错误类型都不完全相同。如果比较报告没有统一的 protocol family、tool-call protocol 和 usage metadata source 维度，就容易把协议差异误判成模型能力差异。

评测影响：如果比较不同 provider family，却没有把 protocol family、tool-call compatibility、thinking / reasoning visibility、prompt cache、streaming capability 和 token usage source 作为受控变量，就可能把协议差异误判成模型能力差异。

建议：在 provider comparison 前，为每个 run 记录 `provider_protocol_family`、`tool_call_protocol_version`、`streaming_enabled`、`reasoning_trace_policy`、`prompt_cache_policy`、`usage_metadata_source` 和 `native_error_mapping_version`。如果某些 provider 只能通过兼容协议运行，报告中应说明这是 protocol-compatible comparison，而不是完整原生产品能力对比。

### G22. 批量级 provider quota、rate limit 和 circuit breaker 不完整

Claude Code 的 provider retry 逻辑不仅处理单次请求，还会把 429、529、fallback、长 retry-after、持续重试提示和模型切换纳入会话状态。对 RepoHarness 来说，正式测评还多了一个批量运行维度：同一批二十三题或更多任务可能共享同一个 provider 账号、同一个成本预算和同一个 rate limit。

G1 只覆盖单个 provider call 的 retry；G16 只覆盖 batch runner 与 rollout queue 的关系。当前仍然缺少全局 provider 调用账本，例如每个 provider family 的并发上限、短时间内连续 429 / 500 的熔断、剩余真实调用预算、重试排队、structured skip 原因、是否允许继续启动新任务。

评测影响：如果多个 run 同时遇到限流并各自 retry，可能把一个可控的 provider 限流放大成系统性失败，甚至消耗过多预算。最终报告可能只看到多个 provider error，而看不到这是全局 quota 或 rate limit policy 没有统一治理。

建议：如果正式 pre-verl 采用顺序执行，可以把本条作为 known limitation，并在报告中写明没有并行 provider 压力。如果采用并行或半并行执行，应增加 `provider_quota_ledger`，记录 provider family、active calls、retry queue、rate-limit event、circuit breaker state、remaining call budget、remaining cost budget 和 structured skip reason。

### G23. Provider 故障注入 smoke 不完整

Claude Code 的 retry、fallback 和恢复逻辑可以通过专门路径和 mock limit 场景触发。RepoHarness 如果要实现 G1 到 G3，也需要确定性验证，而不能等真实 provider 随机出现故障。

当前文档已有建议 inspect，但还需要明确 smoke 场景：fake / mock provider 应能稳定构造 429、timeout、五百类错误、`finish_reason=length`、malformed tool call JSON、缺失 tool function name、invalid response 和 retryable / non-retryable error。每个 smoke 应证明恢复逻辑、terminal reason、artifact 绑定和统计归因都符合预期。

评测影响：没有故障注入 smoke 时，retry 和恢复逻辑可能只在 happy path 通过测试。正式二十三题中一旦遇到真实故障，才发现 attempt artifact 缺失、retry_count 不更新、恢复回合没有进入 transcript，届时结果已经无法作为可靠评测证据。

建议：正式 pre-verl 前新增 non-formal provider failure injection smoke，并把通过结果作为 readiness 前置条件。它不计入模型 accepted rate，只证明 Harness 能正确处理 provider 故障、输出截断和工具调用协议异常。

### G24. Provider、工具、命令和 final verifier 的取消与清理传播不统一

Claude Code 的 `ToolUseContext` 和子代理实现围绕 AbortController、signal、后台任务清理和 finally cleanup 设计。即使不考虑界面交互，统一取消传播对长任务、批量运行和恢复都很重要。

RepoHarness 的工具执行上下文中已有类似 `abort_signal` 的字段，但主链路还没有形成统一取消协议：provider call、工具执行、Docker-based executable repository environment 命令、final verifier、后台进程和 artifact 写入之间，是否能在 task timeout、用户中断、quota 熔断或进程退出时按同一个规则停止和清理，目前不是一等审计对象。

评测影响：长任务被中断时，可能出现 provider 仍在请求、命令仍在执行、final verifier 部分写入、workspace 临时状态未清理或 run 被错误标记为普通失败。对于批量训练轨迹生产，这会造成重复执行、资源泄漏和失败归因不准确。

建议：当前 formal pre-verl 可以先把取消传播能力作为 known limitation。如果后续要支持并行长跑或可恢复队列，应定义 `abort_reason`、`abort_requested_at`、`abort_acknowledged_by_provider`、`abort_acknowledged_by_tool`、`command_killed`、`verifier_cancelled`、`cleanup_status` 和最终 terminal reason，并为超时和用户中断分别测试。

## 6. 推荐排期

### 6.1 正式 pre-verl 测评前建议完成或冻结

1. G1：Provider retry / backoff / attempt artifact。
2. G2：输出 token 上限恢复或独立 terminal reason。
3. G3：malformed tool call 的一次模型可见修复回合。
4. G4：轻量 permission policy manifest，显式冻结当前裁决顺序和禁用项。
5. G5：统一 `run-task` 与 V5 provider matrix 的 primary provider runtime。
6. G6：per-turn token / cost / budget decision trace；如果 cost 无法可靠获得，明确标为 unavailable。
7. G13 的轻量部分：加入 `AGENTS.md` 识别、git/source snapshot 和 repo context index。
8. G23：Provider failure injection smoke，用 fake / mock provider 覆盖 retry、截断和 malformed tool call。

### 6.2 正式 pre-verl 测评中建议作为 known limitations 报告

1. G7：工具执行是 serial，即使只读工具声明 concurrency-safe。
2. G8：没有完整 streaming，但如果补了 liveness event，需要报告其粒度。
3. G9：no-progress 仅诊断，不自动终止。
4. G10：工具 capability 仍是静态简化模型。
5. G11：hook 明确禁用，不参与 formal baseline。
6. G12：不支持任意中断点 durable resume，只支持 structured terminal outcome 或外部重跑。
7. G16：如果批量测评顺序执行，应明确 V4 rollout queue 不在本轮范围内。
8. G21：provider comparison 按协议族和 metadata 可用性分区解释。
9. G22：如果顺序运行，应说明没有全局 provider quota / circuit breaker；如果并行运行，则需要先实现。
10. G24：取消和清理传播不是本轮正式能力，超时或中断只按 structured terminal outcome 报告。

### 6.3 不建议阻塞当前 pre-verl 测评的后续方向

1. G14：延迟工具发现、MCP 工具 schema 缓存和动态工具池刷新。
2. G15：文件历史和编辑归因索引。
3. G17：prompt injection 和 instruction conflict diagnostic task set。
4. G18：符号级检索、LSP 和 lint 异步诊断工具。
5. G19：MCP / plugin / skill 工具源。
6. G20：模型可调用子代理和 sidechain transcript。

## 7. 建议的验收检查点

如果后续把本文中的 P1 条目纳入实现计划，建议新增或扩展以下 inspect：

1. `inspect-provider-retry-trace RUN_DIR --assert-attempts-bound`
   - 检查 retryable provider error 是否进入 bounded retry。
   - 检查每次 attempt 是否有 request / response artifact。
   - 检查 fallback success 没有混入 primary provider accepted rate。

2. `inspect-output-token-recovery RUN_DIR --assert-terminal-reason-specific`
   - 检查 `finish_reason=length` 没有被误归因为输入 `context_limit`。
   - 检查 continuation policy、次数、prompt hash 和最终结果。

3. `inspect-tool-call-repair RUN_DIR --assert-malformed-tool-call-recoverable`
   - 检查 malformed tool call 是否产生模型可见恢复 observation。
   - 检查恢复失败时 terminal reason 是具体的 unrecovered parse failure。

4. `inspect-permission-decision-chain RUN_DIR --assert-policy-bound`
   - 检查每次 tool call 有 permission policy hash、当前裁决顺序、matched rule、是否来自只读自动允许、拒绝原因和 model-visible recovery hint。

5. `inspect-run-task-provider-entrypoints RUN_DIR --assert-primary-provider-unified`
   - 检查 formal run 是否来自 `repo-harness run-task`。
   - 检查 provider registry、raw artifact、failure taxonomy 和 final verifier adapter 是否与 V5 matrix 入口一致。

6. `inspect-budget-decision-trace RUN_DIR --assert-budget-source-explicit`
   - 检查每轮 token / cost / continuation / stop decision。
   - 检查 unavailable provider metadata 没有被伪装成真实 cost。

7. `inspect-repo-context-index RUN_DIR --assert-instruction-boundary`
   - 检查 `AGENTS.md`、`CLAUDE.md`、`README.md`、`CONTRIBUTING.md` 等文件的注入边界、哈希、截断和适用范围。
   - 检查 git/source snapshot 是否与 run source tree hash 绑定。

8. `run-provider-failure-injection-smoke --scenario retryable_429,timeout,length,malformed_tool_call`
   - 用 fake / mock provider 稳定触发 retryable error、non-retryable error、输出截断和非法 tool call。
   - 检查恢复逻辑、terminal reason、retry_count、attempt artifact 和 transcript 回流。

9. `inspect-provider-quota-ledger RUN_DIR --assert-quota-decisions-bound`
   - 如果正式运行启用并行或半并行，检查 provider family、active calls、retry queue、circuit breaker state、remaining budget 和 structured skip reason。
   - 如果正式运行明确顺序执行，检查报告是否写明本轮没有启用全局 provider quota / circuit breaker。

10. `inspect-abort-propagation-trace RUN_DIR --assert-cleanup-bound`
    - 检查 task timeout、用户中断或 quota 熔断时，provider、工具、命令、final verifier 和 artifact writer 是否有统一 terminal reason 与 cleanup status。

这些 inspect 不要求一次性全部实现。建议先把 G1 到 G6 和 G23 变成 formal readiness gate，把 G7 到 G22、G24 按 known limitations 或 post-pre-verl backlog 记录在正式报告中。
