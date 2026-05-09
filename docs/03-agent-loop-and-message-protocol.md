# Agent Loop And Message Protocol

## Agent Loop 目标

Agent Loop 是 RepoHarness 的核心。它负责让模型在任务上下文中多轮行动：读取仓库、搜索代码、修改文件、运行测试、读取反馈、继续修复，直到完成任务或触发终止条件。

## 核心流程

未来实现应遵循这个最小流程：

```python
messages = context_builder.build_initial_messages(
    task=task,
    workspace=workspace,
    run_config=run_config,
    resolved_verifier_plan=resolved_verifier_plan,
    scaffold=scaffold,
)
budget_state = budget_manager.start_run(run_config)
tool_pairing_state = ToolPairingState()

while budget_manager.can_start_turn(budget_state):
    prepared_messages = context_manager.prepare_messages(
        messages=messages,
        budget_state=budget_state,
        tool_pairing_state=tool_pairing_state,
    )
    recorder.record_context_event(prepared_messages.context_event)

    response = model_client.generate(
        prepared_messages=prepared_messages,
        tools=tools,
        model_config=run_config.model,
        retry_policy=run_config.model.retry_policy,
    )
    recorder.record_assistant_message(response)
    recorder.record_model_call(response.model_call_event)

    if response.model_error_type:
        recovery = handle_model_error(response, budget_state, context_manager)
        recorder.record_model_error(recovery.event)
        if recovery.action in ["retry", "compact_and_retry", "fallback_model"]:
            continue
        stop_agent_loop(recovery.agent_stop_reason)
        break

    parse_result = tool_call_parser.parse(response)
    if parse_result.error:
        recorder.record_tool_call_parse_failed(parse_result.event)
        if parse_result.can_send_model_visible_error and budget_manager.can_retry_protocol_error(budget_state):
            messages.extend(parse_result.to_protocol_error_messages())
            continue
        stop_agent_loop("invalid_tool_call")
        break

    if parse_result.has_no_tool_calls():
        if is_valid_final_answer(response, scaffold, budget_state):
            stop_agent_loop("final_answer")
            break
        recovery = handle_non_final_no_tool_response(response, budget_state)
        recorder.record_model_error(recovery.event)
        if recovery.action in ["continue_generation", "retry", "compact_and_retry"]:
            continue
        stop_agent_loop(recovery.agent_stop_reason)
        break

    budget_manager.check_before_tools(parse_result.tool_calls, budget_state)
    tool_results = run_tools(parse_result.tool_calls, budget_state)
    messages.extend(to_tool_result_messages(tool_results))
    recorder.record_tool_results(tool_results)
    tool_pairing_state.mark_completed(parse_result.tool_calls, tool_results)
    budget_manager.update_after_tools(tool_results, budget_state)

    if last_tool_was_run_tests and last_verifier_result.accepted:
        stop_agent_loop("feedback_tests_passed")
        break

# 以下 post-loop 阶段由 Eval Runner 编排，
# 不属于 Agent Loop 内部状态机。
final_patch, final_diff = recorder.freeze_final_patch(agent_start_snapshot, workspace)
final_verifier_result = run_final_verifier(
    final_patch=final_patch,
    resolved_verifier_plan=resolved_verifier_plan,
    dependency_state=workspace.dependency_state,
    mode=run_config.evaluation.final_verifier_mode,
)
recorder.record_verifier_result(final_verifier_result)
run_outcome = derive_run_outcome(agent_stop_reason, final_verifier_result)
```

这个流程参考 Claude Code 的 `query()`：工具不是旁路副作用，工具结果必须进入下一轮模型上下文。Agent Loop 停止后，Eval Runner 必须先从 `agent_start_snapshot` 冻结 `final.patch` 和 `final.diff`，正式 final verifier 再在独立 verification workspace 中恢复合法依赖、应用 `final.patch` 并运行验证，也就是 `final_verifier_mode = "strict_patch_replay"`。快速调试模式可以在 agent run workspace 上直接验收，但必须记录 `final_verifier_mode`，不能作为正式评测口径。

## Model Client 与 Context Builder

Agent Loop 不应该直接绑定某个模型供应商的原始协议。第一版应定义一个最小 `ModelClient` 契约：

```text
ModelClient.generate(prepared_messages, tools, model_config, retry_policy) -> ModelResponse
```

Agent Loop 应把完整 `PreparedMessages` 传给 Model Client，而不是只传其中的 messages 列表。这样 Model Client 才能把 `context_revision`、`prepared_messages_ref`、`model_input_hash` 和 provider-specific formatting 信息写入 `ModelCallEvent`，并生成完整的 `raw_provider_request_ref`。

`ModelResponse` 至少包含：

- `assistant_message`：标准化后的 assistant message，可进入 transcript。
- `tool_calls`：由 `ToolCallParser` 标准化后的工具调用列表。
- `raw_provider_request_ref`：本轮 provider-ready request body 的 `ArtifactRef`，用于复盘真实发送给模型的 messages、tools 和 provider-specific formatting。
- `raw_provider_response_ref`：原始供应商响应的 `ArtifactRef`，用于调试和协议解析审计，不作为训练导出的默认模型目标。
- `token_usage`：输入、输出、缓存命中和估算成本。
- `finish_reason`：供应商或标准化后的停止原因。
- `model_error_type`：`rate_limited`、`auth_error`、`context_limit`、`invalid_response`、`provider_error` 等。
- `provider_request_id`：供应商请求标识，方便排查。
- `model_call_event`：模型调用事件摘要，包含模型、token、耗时、错误类型、重试次数、`context_revision`、`model_input_hash`、`prepared_messages_ref`、`provider_message_format` 和 `tool_schema_hash`。

`ToolCallParser` 负责把不同供应商的工具调用格式统一成 RepoHarness 的 `ToolCall`。训练导出默认使用标准化后的 message 和 tool call；原始响应只作为可追溯 artifact 保存。

`raw_provider_request_ref` 和 `raw_provider_response_ref` 都必须引用 `artifacts.json` 中的 `ArtifactRef`，而不是裸路径字符串。这样 provider-ready 输入、原始响应、hash、脱敏状态和保留策略都在同一套 artifact manifest 中审计。

`prepared_messages_ref` 和 `raw_provider_request_ref` 不是同一个概念。`prepared_messages_ref` 指 Context Manager 生成的 provider-ready messages artifact，主要用于复盘模型实际看到的消息序列；`raw_provider_request_ref` 指 Model Client 最终发送给供应商的完整 request body，除了 messages 之外还应包含 tools schema、model config、采样参数、streaming 设置和 provider-specific formatting。`ModelCallEvent.context_revision`、`prepared_messages_ref`、`model_input_hash`、`provider_message_format` 和 `tool_schema_hash` 必须直接来自 `PreparedMessages` 与 Model Client 构造的 provider request，不能依赖隐式全局状态。

### Provider Reasoning 与隐藏思考内容

不同模型供应商可能返回普通 assistant 文本、工具调用、reasoning token usage、reasoning summary、provider-specific thinking block 或原始响应中的内部字段。RepoHarness 第一版必须保守处理：

- transcript 默认只保存模型可见 assistant 文本、工具调用和工具结果，不把隐藏 chain-of-thought 当作普通 assistant message。
- 如果供应商只返回 reasoning token usage，不返回 reasoning 内容，只记录用量和成本，不伪造推理文本。
- 如果供应商返回 reasoning summary，必须记录 `reasoning_summary_provider`、`export_allowed` 和 artifact redaction 状态；默认不把它作为监督微调目标。
- provider 原始响应可以通过 `raw_provider_response_ref` 保存为 artifact，但进入训练导出前必须经过 redaction policy 和 export policy。
- 任何 provider-specific thinking block 默认 `model_visible = false`、`trainable = false`，除非未来明确取得授权、格式稳定并在 export policy 中显式允许。

这条策略的目的不是丢弃调试信息，而是避免把供应商隐藏推理、内部字段或不稳定协议内容混入 SFT / RL 训练样本。

`ToolCallParser` 失败也必须进入协议，而不能只作为日志丢掉。常见失败包括 malformed tool call、重复 `tool_call_id`、缺失 `tool_call_id`、部分流式 JSON、fallback 后残留的半截工具块和 provider 返回的工具参数类型不匹配。第一版应记录 `tool_call_parse_failed` 或 `invalid_model_tool_call` 事件，字段至少包含 `provider_request_id`、`raw_provider_response_ref`、`parser_id`、`parser_version`、`parse_error_type`、`recoverable` 和 `model_visible_error_created`。如果已经能识别出合法 `tool_call_id`，应尽量补齐合成 `ToolResult(status = "error", error_type = "tool_call_parse_failed")`；如果无法形成合法 tool call，则记录模型响应错误事件，并在预算允许时给模型一条协议错误 observation 让其重试，或停止为 `agent_stop_reason = "invalid_tool_call"`。

初始上下文必须由 `ContextBuilder` 统一构造，而不是由每个 scaffold 临时拼接 prompt：

```text
ContextBuilder.build_initial_messages(task, workspace, run_config, resolved_verifier_plan, scaffold) -> list[ModelMessage]
```

`ContextBuilder` 至少负责：

- 注入 issue statement、仓库根目录、语言、测试命令和允许工具。
- 注入 `ResolvedVerifierPlan` 中允许模型看到的测试目标摘要，例如公开的测试命令说明或模型可见的 expected files；不能注入隐藏 fail-to-pass / pass-to-pass 细节、baseline 原始日志或 reward-only 字段。
- 注入执行模式、权限模式、预算和当前日期。
- 可选注入 `README`、`AGENT.md`、`CLAUDE.md`、`CONTRIBUTING.md` 等项目说明文件的摘要或路径。
- 记录 `prompt_template_version`、`context_builder_version` 和上下文截断策略。
- 区分 `agent_visible_context` 和 `evaluator_only_metadata`。`gold_patch`、隐藏测试、奖励元数据、baseline 原始验证细节默认不能进入模型上下文，也不能通过普通工具输出泄漏给模型。

V4 对 reward 字段的边界更细：`reward scalar` 和 `reward label` 禁止进入模型可见文本、prompt、action、observation、assistant target、SFT target 和 preference target；它们只能出现在非模型可见、字段路径受 allowlist 约束的 structured reward、RewardMetadata、reward audit report 或 audit-only metadata 中。实现和导出审计必须同时检查 visibility 与字段路径，不能只检查文本中是否出现关键词。

仓库内的 `README`、`AGENT.md`、`CLAUDE.md`、`CONTRIBUTING.md` 和 issue 文本都应被视为任务上下文，而不是高优先级系统指令。Context Builder 注入这些内容时必须标明来源，例如“以下内容来自仓库文件”，并明确它不能覆盖系统安全规则、权限规则、隐藏 evaluator metadata、网络策略和 workspace boundary。未来进入真实仓库前，可以增加 prompt injection 诊断事件或过滤策略；第一版至少不能让仓库文件内容改写 Harness 的系统级边界。

初始上下文构造之后，每次模型调用前还需要 `ContextManager` 准备消息：

```text
ContextManager.prepare_messages(messages, budget_state, tool_pairing_state) -> PreparedMessages
```

它负责根据当前预算和协议状态执行工具输出截断、旧测试输出摘要、recent turns 保留、上下文压缩、消息规范化和 provider-specific formatting。每次准备都应记录 `context_revision`、`truncation_policy`、`compaction_event`、`tokens_before` 和 `tokens_after`。上下文压缩后仍必须保持 tool call / tool result 配对，不得留下只有工具请求、没有工具结果的消息片段；否则 session resume、训练导出和 provider API 调用都会变得不可重放。

## 消息协议

第一版消息协议设计为：

- system message：定义 agent 角色、工具使用规则、输出约束和安全边界。
- user task message：包含 issue statement、任务说明、当前仓库信息和测试目标。
- assistant message：模型的自然语言推理或 tool call 请求。
- tool call：模型请求执行工具的结构化动作。
- tool result：工具返回的观察结果，必须可进入下一轮模型上下文。
- verifier result：测试和验证器输出。只有模型主动调用 `run_tests` 产生的 feedback verifier result 可以作为 model-visible tool result 进入下一轮上下文；baseline verifier 和正式 final verifier 只能进入 events、artifact、reward 证据链和 summary，不能作为后续模型 observation。
- termination summary：agent 停止原因、final verifier 状态、最终 run outcome、最终 patch 和关键 metrics。

## Tool Call 与 Tool Result 配对不变量

每个 assistant message 中出现的 `ToolCall` 都必须产生一个对应的 `ToolResult`，并且该结果必须回流到下一轮模型上下文。transcript 中不得出现孤立 tool call。

异常场景也必须生成合成 tool result：

- 未知工具名：`ToolResult(status = "error", error_type = "unknown_tool")`。
- schema 校验失败：`ToolResult(status = "error", error_type = "schema_validation_failed")`。
- 工具级输入校验失败：`ToolResult(status = "error", error_type = "input_validation_failed")`。
- 权限拒绝：`ToolResult(status = "denied", error_type = "permission_denied")`。
- 工具超时：`ToolResult(status = "timeout", error_type = "tool_timeout")`。
- 工具执行异常：`ToolResult(status = "error", error_type = "tool_error")`。
- agent 被手动中断或全局 timeout 中断时，已发出但未完成的 tool call 必须补齐 `ToolResult(status = "interrupted", error_type = "manual_stop" 或 "timeout")`。

这条不变量服务三个目标：下一轮模型请求不会因为消息协议不完整而失败；session resume 可以重放到一致状态；训练导出不会把只有动作、没有观察的半截轨迹误当成完整样本。

注意，这条不变量从“已经成功解析出的 `ToolCall`”开始生效。解析失败的模型响应不能静默跳过，也不能伪装成正常 final answer。实现应记录 `tool_call_parse_failed` / `invalid_model_tool_call` 事件，并根据是否能恢复出合法 `tool_call_id` 决定是否补合成 `ToolResult`。无法恢复合法工具调用时，应把原始响应保存为 artifact，并通过模型可见协议错误消息、retry、fallback 或 `invalid_tool_call` 终止路径处理。

## Verifier 触发策略

RepoHarness 需要区分三类 verifier 使用场景：

1. baseline verifier：正式 agent 运行前执行，用来确认任务环境可运行、记录初始失败测试和初始通过测试。
2. feedback verifier：由 `run_tests` 工具触发，作为 agent 中间反馈进入下一轮模型上下文。它使用同一套 verifier parser 和结果 schema，但事件类型应标记为 `verifier_feedback`。
3. final verifier：agent 停止后强制执行，作为离线评测、reward metadata 和训练导出的最终依据。它使用同一套测试配置和解析器，但事件类型应标记为 `verifier_final`。

`bash` 可以运行普通命令，但不应该替代 `run_tests` 的评测语义。只有 `run_tests` 和 final verifier 产生的结构化 `VerifierResult` 才能用于 success rate、reward metadata 和 fail-to-pass / pass-to-pass 统计。

三类 verifier 的可见性必须分开：

- baseline verifier：只进入 `BaselineResult`、events、artifact 和任务质量门控，不进入正式 agent messages。
- feedback verifier：由模型调用 `run_tests` 触发，可以作为 tool result observation 回流模型上下文，也可以用于中间诊断和预算统计。
- formal final verifier：只进入 final verifier artifact、reward metadata、metrics、summary 和训练过滤，不进入模型后续上下文。即使快速调试模式在 agent run workspace 上直接运行 final verifier，也不能把它作为普通 tool observation 导出到训练轨迹中。

## BudgetManager 控制点

Agent Loop 不应只靠 `max_turns` 退出。第一版应在这些位置检查 `BudgetManager`：

- 模型调用前：检查总 wall clock timeout、最大轮数、上下文 token 预算、模型费用预算和是否允许 fallback / retry。
- 模型调用后：更新 token usage、cost、retry count 和 context budget。
- 工具执行前：检查 `max_tool_calls`、单工具 timeout、写工具预算、bash 命令预算和并发批次大小。
- `bash` 路由到 `run_tests` 前：检查 `max_test_runs`，避免模型通过 bash 绕过测试次数预算。
- feedback verifier 和 final verifier 前：检查 verifier timeout、任务总 timeout 和是否还能记录完整 artifact。
- run 结束时：把预算耗尽原因写入 events 和 metrics，参与 `agent_stop_reason` 与 `run_outcome` 派生。

预算耗尽应产生确定性的停止原因，例如 `max_turns`、`max_tool_calls`、`max_test_runs`、`timeout`、`context_limit` 或 `max_cost`。如果预算在工具执行中耗尽，已发出但未完成的工具调用仍必须补齐 interrupted tool result。

## Agent Loop 状态

每次运行至少维护：

- `run_id`
- `task_id`
- `turn_count`
- `tool_call_count`
- `messages`
- `workspace_state`
- `last_verifier_result`
- `budget_state`
- `tool_pairing_state`
- `context_revision`
- `last_model_error`
- `last_tool_parse_error`
- `agent_stop_reason`
- `token_usage`
- `started_at`
- `ended_at`

Agent Loop 运行态必须可以写入 events，并能支持后续 session resume 设计。`final_verifier_status`、`run_outcome` 和 `final_verifier_mode` 属于 Eval Runner 在 Agent Loop 停止后的 run 级汇总状态，应写入 `RunSummary`、`MetricsRecord` 和相关 events，而不是作为 Agent Loop 内部状态机的控制字段。

## Agent Stop Reason、Final Verifier Status 和 Run Outcome

RepoHarness 必须区分三层结论，不能只用一个 `termination_reason` 表达所有含义：

`agent_stop_reason` 只描述 agent loop 为什么停止：

- `final_answer`
- `feedback_tests_passed`
- `max_turns`
- `max_tool_calls`
- `max_test_runs`
- `max_cost`
- `timeout`
- `permission_denied`
- `tool_error`
- `invalid_tool_call`
- `context_limit`
- `model_error`
- `no_progress`
- `manual_stop`

`final_verifier_status` 只描述 agent 停止后 final verifier 的结果：

- `accepted`
- `failed`
- `timeout`
- `error`
- `skipped`

`run_outcome` 是面向评测、训练导出和报告的最终结论：

- `success`
- `failed`
- `invalid_task`
- `flaky_task`
- `interrupted`
- `inconclusive`

例如，一个 run 可以因为 `agent_stop_reason = "feedback_tests_passed"` 停止，但 final verifier 发现 pass-to-pass regression，此时应记录 `final_verifier_status = "failed"`，`run_outcome = "failed"`，并把失败类型标记为 `regression_detected`。

这些字段都用于评测统计和面试中的失败模式分析，但用途不同：agent stop reason 用于分析 agent 行为，final verifier status 用于验证最终工作区，run outcome 用于成功率、训练过滤和简历报告口径。

`feedback_tests_passed` 只能表示中间 feedback verifier 已经接受当前工作区。最终 metrics 仍然必须以 final verifier 为准。如果 final verifier 发现回归，最终运行应记录 `regression_detected` 或对应 verifier error type，而不是只相信早先的 feedback result。

没有 tool call 不应自动等于 `final_answer`。实现必须同时检查：

- `finish_reason` 是否表示正常停止，而不是 `max_output_tokens`、content filter、provider error 或 streaming interrupted。
- `assistant_message` 是否是有效最终答复，而不是空响应、拒答、半截 JSON 或上下文恢复提示。
- `model_error_type` 是否为空。
- scaffold 是否允许无工具最终答复。
- 是否触发 continuation、retry、context compaction、fallback model 或 stop hook。

只有存在有效 assistant final message，并且没有任何恢复动作需要继续执行时，才能设置 `agent_stop_reason = "final_answer"`。

### Run Outcome 派生表

`run_outcome` 应由确定性规则派生，不能由不同模块自由解释。第一版建议规则如下，靠前规则优先级更高：

| 条件 | `run_outcome` | 说明 |
| --- | --- | --- |
| baseline status 为 `invalid` | `invalid_task` | 不进入正式 agent run，也不计为模型失败。 |
| baseline status 为 `flaky` | `flaky_task` | 默认不进入训练轨迹，可进入诊断集合。 |
| final verifier status 为 `accepted` | `success` | 即使 agent stop reason 是 `timeout` 或 `max_turns`，只要最终 patch 被接受，评测成功率仍按成功统计，同时保留 stop reason。 |
| final verifier status 为 `failed` | `failed` | 包括 assertion failure 和 pass-to-pass regression。 |
| final verifier status 为 `timeout` 且没有可解析测试结果 | `inconclusive` | 若项目配置选择把 final timeout 计为失败，必须在 metrics 中记录该策略版本。 |
| final verifier status 为 `error` | `inconclusive` | 例如 verifier parser 崩溃、执行环境异常或 strict patch replay 阶段 `patch_apply_failed`。 |
| manual stop 且未运行 final verifier | `interrupted` | 不作为成功或失败训练样本。 |

这张表用于 metrics、训练过滤和简历报告口径。实现中可以增加细分字段，但不能把 `agent_stop_reason`、`final_verifier_status` 和 `run_outcome` 再合并成一个字段。

## 错误恢复设计

无效工具名：返回 tool error 给模型，记录 `invalid_tool_call`，允许模型在预算内重试。

schema 校验失败：返回参数错误和期望 schema 摘要，不执行工具。

ToolCallParser 失败：记录 `tool_call_parse_failed` 或 `invalid_model_tool_call` 事件。能恢复出合法 `tool_call_id` 时补合成 `ToolResult`；不能恢复时保存原始响应 artifact，并按预算选择模型可见协议错误、retry、fallback 或停止为 `invalid_tool_call`。

模型 transient error：例如 rate limit、临时网络错误或 5xx provider error，应按 `retry_policy` 做有限重试，并把每次重试写入 `ModelCallEvent`。重试耗尽后停止为 `model_error` 或按配置进入 fallback model。

模型 auth / permission error：通常不可重试，应记录 `model_error_type = "auth_error"` 或等价类型，停止为 `model_error`，不生成训练样本。

上下文过长：先触发 `ContextManager` 压缩、摘要或丢弃非关键旧观察；压缩后仍必须保持 tool call / tool result 配对。压缩失败或仍超出预算时，停止为 `context_limit`。

max output tokens：不应直接当作 final answer。实现可以按 scaffold 和 provider 能力触发 continuation；如果 continuation 不可用或多次失败，应记录 `model_error_type = "max_output_tokens"`，并停止为 `model_error` 或 `context_limit`。

fallback model：如果从主模型切换到 fallback 模型，必须记录 fallback 原因、原模型响应 artifact、fallback model id、策略版本和新的 `ModelCallEvent`。fallback 不能留下未配对 tool call；切换前如已有可识别 tool call，必须先补齐合成 tool result 或终止当前 turn。

工具超时：返回 timeout observation，并记录工具持续时间。

bash 命令失败：保留 exit code、stdout 摘要、stderr 摘要和失败类型，让模型继续修复。

测试失败：不是 runtime error，而是正常 environment feedback，应进入 verifier result。

预算耗尽：在模型调用前、工具执行前、测试路由前和 verifier 运行前都要检查。不同预算耗尽应分别记录 `max_turns`、`max_tool_calls`、`max_test_runs`、`timeout`、`context_limit` 或 `max_cost`，不能统一写成普通 tool error。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-code-ai-core-codex/02-dialogue-engine-and-context.md`
- `reference/claude-code-docs/claude-code-ai-core-codex/06-end-to-end-ai-sequences.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/QueryEngine.ts`
- `reference/claude-code-typescript-src/services/api/claude.ts`
- `reference/claude-code-typescript-src/services/tools/toolExecution.ts`

借鉴点是 `QueryEngine` 管长期会话，`query()` 管一轮执行。RepoHarness 也应该把会话宿主和 turn-level loop 分开。
