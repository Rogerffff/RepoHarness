# Agent Loop And Message Protocol

## Agent Loop 目标

Agent Loop 是 RepoHarness 的核心。它负责让模型在任务上下文中多轮行动：读取仓库、搜索代码、修改文件、运行测试、读取反馈、继续修复，直到完成任务或触发终止条件。

## 核心流程

未来实现应遵循这个最小流程：

```python
while turn < max_turns:
    response = call_model(messages, tools)
    recorder.record_assistant_message(response)

    if response.has_no_tool_calls():
        terminate("final_answer")
        break

    tool_results = run_tools(response.tool_calls)
    messages.extend(to_tool_result_messages(tool_results))
    recorder.record_tool_results(tool_results)

    if last_tool_was_run_tests and last_verifier_result.accepted:
        terminate("tests_passed")
        break

final_verifier_result = run_final_verifier(workspace)
recorder.record_verifier_result(final_verifier_result)
```

这个流程参考 Claude Code 的 `query()`：工具不是旁路副作用，工具结果必须进入下一轮模型上下文。最终验收 verifier 必须在 agent 停止后基于最终工作区重新运行一次，避免模型上下文中的旧测试结果和最终文件状态不一致。

## 消息协议

第一版消息协议设计为：

- system message：定义 agent 角色、工具使用规则、输出约束和安全边界。
- user task message：包含 issue statement、任务说明、当前仓库信息和测试目标。
- assistant message：模型的自然语言推理或 tool call 请求。
- tool call：模型请求执行工具的结构化动作。
- tool result：工具返回的观察结果，必须可进入下一轮模型上下文。
- verifier result：测试和验证器输出，可以作为 tool result 或独立事件进入 trajectory。
- termination summary：运行结束原因、最终 patch、verifier 结果和关键 metrics。

## Verifier 触发策略

RepoHarness 需要区分三类 verifier 使用场景：

1. baseline verifier：正式 agent 运行前执行，用来确认任务环境可运行、记录初始失败测试和初始通过测试。
2. feedback verifier：由 `run_tests` 工具触发，作为 agent 中间反馈进入下一轮模型上下文。它使用同一套 verifier parser 和结果 schema，但事件类型应标记为 `verifier_feedback`。
3. final verifier：agent 停止后强制执行，作为离线评测、reward metadata 和训练导出的最终依据。它使用同一套测试配置和解析器，但事件类型应标记为 `verifier_final`。

`bash` 可以运行普通命令，但不应该替代 `run_tests` 的评测语义。只有 `run_tests` 和 final verifier 产生的结构化 `VerifierResult` 才能用于 success rate、reward metadata 和 fail-to-pass / pass-to-pass 统计。

## Agent Loop 状态

每次运行至少维护：

- `run_id`
- `task_id`
- `turn_count`
- `tool_call_count`
- `messages`
- `workspace_state`
- `last_verifier_result`
- `termination_reason`
- `token_usage`
- `started_at`
- `ended_at`

状态必须可以写入 events，并能支持后续 session resume 设计。

## 终止原因

标准终止原因：

- `final_answer`
- `tests_passed`
- `max_turns`
- `max_tool_calls`
- `timeout`
- `permission_denied`
- `tool_error`
- `invalid_tool_call`
- `context_limit`
- `manual_stop`

这些终止原因既用于评测统计，也用于面试中的失败模式分析。

`tests_passed` 只能表示中间 feedback verifier 已经接受当前工作区。最终 metrics 仍然必须以 final verifier 为准。如果 final verifier 发现回归，最终运行应记录 `regression_detected` 或对应 verifier error type，而不是只相信早先的 `tests_passed`。

## 错误恢复设计

无效工具名：返回 tool error 给模型，记录 `invalid_tool_call`，允许模型在预算内重试。

schema 校验失败：返回参数错误和期望 schema 摘要，不执行工具。

工具超时：返回 timeout observation，并记录工具持续时间。

bash 命令失败：保留 exit code、stdout 摘要、stderr 摘要和失败类型，让模型继续修复。

测试失败：不是 runtime error，而是正常 environment feedback，应进入 verifier result。

上下文过长：触发上下文策略，例如压缩旧工具结果或终止为 `context_limit`。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-code-ai-core-codex/02-dialogue-engine-and-context.md`
- `reference/claude-code-docs/claude-code-ai-core-codex/06-end-to-end-ai-sequences.md`
- `reference/claude-code-typescript-src/query.ts`
- `reference/claude-code-typescript-src/QueryEngine.ts`

借鉴点是 `QueryEngine` 管长期会话，`query()` 管一轮执行。RepoHarness 也应该把会话宿主和 turn-level loop 分开。
