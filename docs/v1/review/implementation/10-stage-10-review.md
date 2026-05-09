# Stage 10 Read-Only Review

## Scope

本次审查针对 Stage 10: Agent Loop And Scaffold 的当前实现，重点对照：

- `docs/v1/implementation-plan.md`
- `docs/11-object-model-config-and-data-flow.md`
- `docs/03-agent-loop-and-message-protocol.md`

审查方式为 sub agent 只读审查；sub agent 没有直接修改仓库文件。

## Findings

### P1: 同一轮多个工具调用在提前停止时可能缺少配对 ToolResult

审查指出：当模型在同一轮返回多个 tool call，而 Agent Loop 因 `max_tool_calls`、`max_test_runs` 或 `feedback_tests_passed` 提前停止时，当前正在处理的工具调用可能有 ToolResult，但后续已经出现在 assistant message 中的 tool call 可能没有对应 ToolResult。

处理结果：

- 已修复。
- Agent Loop 现在在预算耗尽或 feedback 测试通过导致停止时，会为同一 assistant message 中尚未执行的后续 tool call 生成 `ToolResult(status="interrupted")`。
- 对这些后续 tool call 同时写入 `tool_requested` 事件和 `tool_interrupted` 事件，保证事件日志和 transcript 都可以审计 tool call / tool result 配对关系。
- 新增单元测试覆盖 `max_tool_calls` 和 `feedback_tests_passed` 两条提前停止路径。

### P2: ContextManager 的 token_estimate 应该基于压缩后的 prepared messages

审查指出：如果 `PreparedMessages.token_estimate` 使用原始 messages 长度，Agent Loop 可能在 ContextManager 已经完成替换和压缩后仍错误触发 `context_limit`。

处理结果：

- 已修复。
- `PreparedMessages.token_estimate` 现在基于 `prepared_messages` 估算，并与 `context_prepared` event 中的 `tokens_after` 保持一致。
- 新增单元断言确认 `token_estimate == tokens_after`，并确认大型工具输出替换后 `tokens_after < tokens_before`。

### P2: simple_react final answer 校验过于宽松

审查指出：final answer 校验不能只检查非空内容和 `finish_reason == "stop"`，还应遵守 scaffold 是否允许无工具最终回答，并拒绝拒答、上下文恢复提示和明显的工具调用或半 JSON 内容。

处理结果：

- 已修复。
- `SimpleReactScaffold.is_valid_final_answer()` 现在会检查 `allows_final_answer_without_tool`，并拒绝空内容、非 stop finish reason、拒答类文本、上下文恢复类文本、JSON-like 开头文本和工具调用形态文本。
- 新增单元测试覆盖 JSON-like final answer 被拒绝的路径。

## Residual Risk

- Stage 10 仍然只实现第一版 `simple_react` scaffold，不实现真实模型 continuation、fallback provider 或复杂 scaffold 状态机。
- wall-clock timeout、artifact byte budget 和 cost budget 的执行级中断仍属于后续增强范围；本阶段只保证已解析 tool call 的配对不变量。
