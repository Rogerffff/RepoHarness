# 第 4 章：真实 provider、AgentLoop 和工具调用

## 本章链路图

```text
ContextBuilder.build_initial_messages
-> ContextManager.prepare_messages
-> ModelRequestContext
-> DeepSeekProviderClient.generate
-> raw provider request artifact
-> DeepSeek chat completions HTTP request
-> raw provider response artifact
-> response_from_provider_payload
-> AgentLoop tool call handling
-> ToolExecutor.normalize / validate_input
-> PermissionSystem.check
-> ToolExecutor.execute
-> ToolResult 回流模型上下文
```

## 本章实际运行或查看的命令

```bash
find runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/artifacts \
  -maxdepth 1 -type f | sort | rg 'raw_deepseek_provider_request|raw_deepseek_provider_response|prepared_messages|tool_schema_snapshot|feedback_verifier_result'

jq '.body | {model, temperature, max_tokens, tool_count: (.tools|length), message_count: (.messages|length), tool_choice}' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/artifacts/tutorial_realrepo_docker_artifact_000016_raw_deepseek_provider_request.json

jq '{status, finish_reason: .response.choices[0].finish_reason, tool_calls: (.response.choices[0].message.tool_calls // [] | length), usage: .response.usage}' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/artifacts/tutorial_realrepo_docker_artifact_000017_raw_deepseek_provider_response.json

jq -r 'select(.event_type=="permission_decision") | [.turn, .data.tool_name, .data.decision, .data.reason] | @tsv' \
  runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/events.jsonl
```

真实复跑结果：

- provider：`deepseek`
- model：`deepseek-v4-pro`
- 第一轮 provider request：`message_count=2`，`tool_count=8`，`tool_choice=auto`。
- 第一轮 provider response：`finish_reason=tool_calls`，返回 1 个 tool call。
- 本次工具调用序列：`list_files`、`read_file`、`read_file`、`edit_file`、`run_tests`、`read_file`。
- permission decision 全部为 `allow`，没有 permission denial。
- feedback verifier artifact 显示 public feedback accepted，`pass_ratio=1.0`。

## 源码入口和对象流

关键入口：

- `src/repo_harness/context/builder.py:25`：构造初始模型上下文。
- `src/repo_harness/context/manager.py:24`：准备消息、上下文修订和压缩。
- `src/repo_harness/model_client/providers/common.py:54`：构造 chat completions payload。
- `src/repo_harness/model_client/providers/common.py:100`：写 raw provider request artifact。
- `src/repo_harness/model_client/providers/common.py:142`：provider response 归一化为 `ModelResponse`。
- `src/repo_harness/model_client/providers/deepseek.py:41`：DeepSeek provider client。
- `src/repo_harness/model_client/providers/deepseek.py:67`：DeepSeek generate。
- `src/repo_harness/model_client/providers/deepseek.py:122`：HTTP POST 到 OpenAI-compatible endpoint。
- `src/repo_harness/agent_loop/loop.py:26`：`AgentLoop`。
- `src/repo_harness/agent_loop/loop.py:47`：多轮 agent loop。
- `src/repo_harness/tools/minimal.py:310`：工具请求 normalize。
- `src/repo_harness/tools/minimal.py:376`：`bash` test command 可路由为 `run_tests`。
- `src/repo_harness/tools/minimal.py:576`：`run_tests` 调 verifier feedback。

关键理解：

- raw provider request / response 会脱敏落盘，不直接作为训练 payload。
- tool schema snapshot 绑定了模型当时可用的工具集合。
- `AgentLoop` 每轮都写 model call event、assistant transcript、tool requested event、permission decision、tool result。
- `bash -> run_tests` 是 normalize 层的路由能力；本次 tutorial run 中模型直接调用了 `run_tests`，所以没有触发该路由，但代码路径存在。

## 面试追问与推荐回答

问：真实 provider 接入只是调 API 吗？

答：不是。RepoHarness 会把模型输入构造成 `ModelRequestContext`，绑定 tool schema snapshot、run config facts、预算和 provider options；请求和响应会脱敏写入 artifact；provider 错误会转成结构化 `ModelResponse`，而不是让 agent loop 直接崩溃。

问：工具调用怎样保证可审计？

答：每个 tool call 会经历输入校验、normalize、scaffold phase 检查、权限决策、执行和 ToolResult 回流。每一步都有 transcript、events 或 artifact 记录。

问：为什么 `run_tests` 不接受任意命令？

答：`run_tests` 是受控 verifier feedback 通道，它读取已解析的 verifier plan 和 feedback policy。任意命令执行属于受限 `bash` 诊断路径，不能混同 formal verifier。
