# Stage 10: Agent Loop And Scaffold

## Scope

本阶段实现了：

- `BudgetManager.from_run_config()`，把 RunConfig 中的 runtime、workspace、context 和 model 预算汇总为运行时预算对象。
- Agent Loop 预算控制：
  - `max_turns`
  - `max_tool_calls`
  - `max_test_runs`
  - `context_limit`
- Agent Loop 停止原因：
  - `final_answer`
  - `feedback_tests_passed`
  - `max_turns`
  - `max_tool_calls`
  - `max_test_runs`
  - `context_limit`
  - `model_error`
- 工具预算耗尽时，为已解析 tool call 生成 `ToolResult(status=interrupted)`，保持 tool call / tool result 配对。
- 同一轮 assistant message 中多个 tool call 被提前停止时，为尚未执行的后续 tool call 同步记录 `tool_requested` 和 `tool_interrupted`，避免 transcript 和 events 中出现未配对工具调用。
- `run_tests` feedback verifier 接受时，Agent Loop 可以停止为 `feedback_tests_passed`，但最终 success 仍由 Eval Runner 后续 final verifier 派生。
- final answer 有效性检查：无工具响应必须是 scaffold 允许的正常 stop、assistant content 非空，并且不能是拒答、上下文恢复提示、JSON-like 工具调用内容或半 JSON 内容，否则停止为 `model_error`。
- `simple_react` scaffold：
  - 只提供 prompt fragment、允许工具和 final answer 策略。
  - 不直接拼初始 messages。
- Eval Runner 创建 BudgetManager 并传入 Agent Loop；final patch、final verifier、reward、metrics 和 summary 仍由 Eval Runner 编排。

本阶段明确不实现：

- 不实现真实模型 retry、fallback model 或 provider-specific continuation。
- 不实现全局 wall-clock timeout 和 artifact byte budget 的完整中断执行。
- 不把 `feedback_tests_passed` 直接等价为 `run_outcome = success`。
- 不把 final verifier、reward 或 metrics 放进 Agent Loop。

## Design References

- `docs/14-v1-implementation-plan.md`
- `docs/03-agent-loop-and-message-protocol.md`
- `docs/11-object-model-config-and-data-flow.md`

## Files Changed

- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/budget/schemas.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/context/manager.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/scaffolds/__init__.py`
- `src/repo_harness/scaffolds/simple_react.py`
- `tests/unit/test_agent_loop_protocol.py`
- `tests/unit/test_context_manager.py`
- `tests/integration/test_agent_loop_replay.py`
- `docs/review/v1-implementation/10-stage-10-review.md`

## Verification

运行的命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_agent_loop_protocol.py tests/unit/test_context_manager.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_agent_loop_protocol.py tests/integration/test_agent_loop_replay.py
PATH=.venv/bin:$PATH python -m pytest
git diff --check
```

结果：

- 通过。
- 审查修复相关单元测试通过 13 个测试。
- 阶段十指定测试收集并通过 14 个测试。
- 全量测试收集并通过 138 个测试。
- `git diff --check` 未发现空白错误。

## Review

审查方式：

- 主实现 agent 自查。
- sub agent 只读审查，审查记录保存到 `docs/review/v1-implementation/10-stage-10-review.md`。

关键审查意见：

- 同一轮多个 tool call 在 `max_tool_calls`、`max_test_runs` 或 `feedback_tests_passed` 提前停止时，必须补齐后续 tool call 的 interrupted ToolResult。
- `PreparedMessages.token_estimate` 必须基于压缩后的 prepared messages，而不是原始 messages。
- `simple_react` 的 final answer 校验不能只检查非空和 `finish_reason = stop`，需要拒绝拒答、上下文恢复提示和 JSON-like 工具调用内容。

处理结果：

- 已为后续未执行工具调用写入 `tool_requested` 和 `ToolResult(status="interrupted")`，并新增配对测试。
- 已确认 `ContextManager` 的 `token_estimate` 基于 `prepared_messages`，并新增断言覆盖。
- 已收紧 `simple_react` final answer 校验，并新增 JSON-like final answer 负例。

## Known Limitations

- BudgetManager 目前覆盖第一版验收所需预算项；wall-clock timeout、artifact byte budget 和 cost budget 的执行级中断会在后续增强。
- `simple_react` 是第一版唯一硬性 scaffold；`single_shot_patch` 和 `planner_coder_verifier` 仍然只作为后续预留方向。
- Agent Loop 仍使用 Fake/Replay ModelClient 验证协议，不接真实模型供应商。

## Commit

- Commit: `stage 10: implement agent loop scaffold`
- Commit message: `stage 10: implement agent loop scaffold`
