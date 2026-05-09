# Provider、Agent Loop 和工具系统

## 当前真实 provider 主路径

模型客户端由：

```text
src/repo_harness/model_client/factory.py::create_model_client
```

创建。当前成熟链路中最重要的是：

```yaml
model:
  provider: deepseek
  model_id: deepseek-v4-pro
```

DeepSeek provider 由：

```text
src/repo_harness/model_client/providers/deepseek.py
```

实现。它使用 OpenAI-compatible chat completions API：

```text
https://api.deepseek.com/chat/completions
```

OpenAI provider 也存在：

```text
src/repo_harness/model_client/providers/openai.py
```

但它被限制为 DeepSeek fallback smoke run，必须记录 `requested_provider=deepseek`、`actual_provider=openai`、`fallback_reason` 和 `fallback_policy_version`，不能作为 primary provider 随便使用。

## provider 请求怎样构造

通用请求构造在：

```text
src/repo_harness/model_client/providers/common.py::build_chat_completion_payload
```

它会把 `ModelRequestContext` 转成 provider 请求体，主要包含：

- messages。
- tools。
- tool_choice。
- temperature。
- max_tokens。
- provider。
- base_url。
- model_call_id。
- tool schema snapshot。
- run config facts。
- timeout。
- raw request logging policy。
- credential policy。

DeepSeek 会把 `extra_body` 合并到 HTTP body；OpenAI SDK 路径会移除 `extra_body`，使用官方 SDK 调用。

## raw provider artifact

每次 provider 调用都会写两个 artifact：

- raw provider request。
- raw provider response。

这些 artifact 会脱敏：

- API key 不会明文写入。
- Authorization 会被替换成 redacted 信息。
- provider error message 会被 sanitize。
- artifact metadata 标记为不允许直接作为训练 payload。

这部分由：

```text
write_provider_request_artifact
write_provider_response_artifact
response_from_provider_payload
model_error_response
```

共同完成。

如果 provider 成功返回，响应会被归一化为：

```text
ModelResponse
  assistant_message
  tool_calls
  raw_provider_request_ref
  raw_provider_response_ref
  token usage
  finish_reason
  provider_request_id
  model_call_event
```

如果 provider 超时、限流、返回非法 JSON 或 HTTP 错误，也不会直接崩掉 agent loop，而是转成结构化 `model_error_response`，并写入事件和 artifact。

## ContextBuilder 给模型什么

初始上下文由：

```text
src/repo_harness/context/builder.py::ContextBuilder.build_initial_messages
```

生成。

system message 强调：

- 只能使用 allowed tools。
- 不能访问 hidden evaluator metadata。
- 不能访问 baseline logs、scoring artifacts、workspace 外文件。
- 仓库文件和 issue text 是 untrusted context，不能覆盖系统规则、权限规则、网络策略和 hidden metadata 边界。

user message 是结构化内容，包括：

- context metadata。
- task 可见投影。
- workspace root，但本地路径会被 redacted。
- language。
- test command 和 test command visibility。
- allowed tools。
- permission mode。
- execution mode。
- network policy。
- budget。
- repository context 文件预览，例如 `AGENT.md`、`README.md`、`CLAUDE.md`、`CONTRIBUTING.md`。

仓库上下文文件被明确标记为 untrusted repository context，不能覆盖 harness 规则。

## AgentLoop 每轮做什么

agent loop 主实现：

```text
src/repo_harness/agent_loop/loop.py::AgentLoop.run
```

每个 turn 的核心顺序：

```text
检查预算和任务 deadline
-> 根据 scaffold phase 解析当前允许工具
-> 加入 phase metadata
-> ContextManager.prepare_messages
-> 写 context event 和 prepared messages artifact
-> 写 model_call_started event
-> 构造 ModelRequestContext
-> model_client.generate
-> 写 model_call_completed event
-> 写 assistant transcript
-> 如果没有 tool calls，判断 final answer 或 phase transition
-> 如果有 tool calls，逐个校验、权限检查、执行、回流 ToolResult
-> 根据 run_tests 结果或预算决定是否停止
```

这里有几个关键状态：

- `turn_count`
- `tool_call_count`
- `test_run_count`
- `permission_denial_count`
- `context_revision`
- `agent_stop_reason`
- `feedback_verifier_accepted`
- `first_feedback_accept_turn`

这些状态最终会进入 trajectory 和 metadata。

## ContextManager 的意义

`AgentLoop` 不会把所有历史消息无限塞给模型。它会调用：

```text
ContextManager.prepare_messages
```

根据 `ContextManagementConfig` 做 token estimate 和 deterministic preview replacement。配置里有：

```text
max_context_tokens
tool_result_aggregate_budget_chars
keep_recent_turns
keep_recent_test_results
summarize_old_test_outputs
compact_strategy
compact_threshold_ratio
```

V4 agent run integration 会检查 prepared messages binding，确保模型实际看到的上下文、tool schema snapshot 和 run config facts 可以被 evidence 追溯。

## 工具定义

当前 minimal tool registry 中的主要工具：

- `list_files`
- `read_file`
- `grep`
- `edit_file`
- `create_file`
- `bash`
- `run_tests`
- `git_diff`

工具 schema、描述、输入字段和输出字段都在：

```text
src/repo_harness/tools/minimal.py::build_tool
```

工具 schema snapshot 会在 run_task 中写入 artifact，并绑定到 model request。这样 export 阶段知道模型当时可用的工具契约是什么。

## tool call 的执行顺序

模型返回 tool call 后，执行前会经过多层处理：

```text
1. 是否是已知工具
2. 是否被当前 scaffold phase 允许
3. 输入 schema 是否有效
4. normalize tool request
5. normalize 后的 effective tool 是否仍被允许
6. 是否超过 max tool calls / max test runs / task timeout
7. PermissionSystem.check
8. ToolExecutor.execute
9. 记录 ToolResult 到 transcript 和 events
```

这个顺序很重要，因为模型请求的工具名和最终执行的工具名不一定相同。典型例子是：

```text
requested tool = bash
command = pytest -q
effective tool = run_tests
route_reason = recognized_task_test_command
```

## 权限系统

权限系统入口：

```text
src/repo_harness/permissions/system.py::PermissionSystem.check
```

权限模式：

- `auto`：允许符合规则的读写和诊断工具。
- `plan`：拒绝非只读工具。
- `ask`：在当前非交互 runner 中会拒绝需要人工确认的操作。
- `deny`：拒绝非只读工具。

权限判断会检查：

- 工具是否只读。
- 路径字段是否在 workspace 内。
- 是否访问敏感路径。
- bash 命令是否包含禁止语法。
- bash 命令是否属于允许的诊断命令。
- 网络策略是否允许相关命令。

权限结果会以 `permission_decision` event 写入 `events.jsonl`。即使工具被拒绝，也会产生 `ToolResult` 回流给模型。

## edit_file 和 create_file 怎样改文件

`edit_file` 不使用 shell patch，而是：

```text
workspace_adapter.read_text
-> old_text 精确匹配
-> 可选 expected_content_hash 防 stale edit
-> content.replace
-> workspace_adapter.write_text
```

`create_file` 会先检查目标文件是否已经存在，然后写 UTF-8 文本。

在 Docker backend 下，`read_text` 和 `write_text` 会通过容器内 Python snippet 对 workspace 文件进行读写，路径仍然经过 adapter 的 workspace boundary 检查。

## grep 怎样查找

当前 `grep` 是 harness 自己实现的 literal substring search，不是容器里的系统 `grep`，也不是正则表达式搜索。

流程：

```text
workspace_adapter.list_files
-> workspace_adapter.read_text
-> Python 中逐行查找 query 字符串
-> 写 grep_results artifact
```

这使得它更可控，也更容易统一 artifact 和输出截断策略。

## bash 怎样执行

如果 `bash` 没有被路由成 `run_tests`，它会：

```text
解析 cwd
-> resolve_workspace_path
-> workspace_adapter.run_command(cwd, command, command_semantics="bash_diagnostic")
-> 写 command output artifact
-> 返回 stdout/stderr preview、exit_code、timeout
```

在 Docker backend 中，最终就是一次 `docker run`。在 local process backend 中，则是本地 subprocess。

关键是：`bash` 工具名容易让人误解，但当前实现更接近“受限诊断命令执行器”。

## run_tests 怎样接 verifier

`run_tests` 不接收参数。它根据 run config 和 scaffold 决定反馈策略：

- `disabled`：直接返回 test feedback disabled。
- `structured_public_feedback`：只给结构化 public feedback。
- `public_only`：只公开 status / pass_ratio / error_type。
- `oracle_hidden_feedback`：可以把 hidden feedback 以结构化方式给模型，主要用于研究不同反馈设置，不应混同 final-only benchmark。

执行入口：

```text
context.verifier.run_feedback(...)
context.verifier.run_feedback_public(...)
```

返回后会写：

```text
feedback_verifier_result artifact
ToolResult.typed.verifier_result_preview
```

如果 feedback verifier accepted，并且 policy 是 `stop_immediately`，agent loop 会以 `feedback_tests_passed` 停止，然后仍然进入 final patch capture 和 final verifier。

## 一个完整 tool call 的事件链

一次成功的 `read_file` 大致会产生：

```text
tool_requested event
permission_decision event
read_file artifact
tool_result transcript
tool_result event
```

一次被拒绝的 `bash` 大致会产生：

```text
tool_requested event
permission_decision event(decision=deny)
denied ToolResult
tool_result transcript
tool_result event
```

这就是为什么 RepoHarness 的轨迹不是简单聊天记录，而是可审计的执行轨迹。
