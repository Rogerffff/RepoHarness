# Pre-verl Provider Reasoning 长期兼容修复设计

## 1. 文档目的

本文档记录 RepoHarness 在长期同时兼容 DeepSeek 思考模式和 OpenAI reasoning models 时需要补齐的 provider 协议能力。它服务两个目标：

1. 修复 DeepSeek 在思考模式和工具调用组合下的多轮协议问题，避免模型第一次工具调用后，第二次 provider 请求因为缺少 `reasoning_content` 被拒绝。
2. 为 OpenAI reasoning models 建立正确的 Responses API 状态保留路径，避免把 OpenAI 的 reasoning items 错误地等同为 DeepSeek 的 `reasoning_content` 字段。

本文档是后续工程实施设计，不代表当前仓库已经完成这些长期兼容修复。正式 pre-verl 二十三题 baseline 在长期修复完成之前，可以先显式禁用 DeepSeek thinking，并通过 inspect gate 证明正式 baseline 没有进入未兼容的思考模式。

## 2. 官方接口事实

### 2.1 DeepSeek

DeepSeek `/chat/completions` 是无状态接口。服务端不保存历史上下文，调用方必须在每次请求中拼接好之前的消息历史。DeepSeek 官方多轮对话文档给出的基本模式是：第一轮得到 assistant 输出后，把 assistant 输出追加到 `messages`，再追加新的 user 消息，然后发起下一轮请求。

DeepSeek 思考模式的关键事实是：

- `thinking` 默认是 `enabled`。
- 在思考模式下，模型返回的思考内容字段是 `reasoning_content`，它与 `content` 是同级字段。
- 如果两个 user 消息之间没有工具调用，中间 assistant 的 `reasoning_content` 后续可以不回传。
- 如果两个 user 消息之间发生了工具调用，后续请求必须完整回传该区间内相关 assistant messages 的 `reasoning_content`。否则 DeepSeek API 会返回 400 错误。

官方参考：

- [DeepSeek 多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat)
- [DeepSeek 思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode)

### 2.2 OpenAI

OpenAI reasoning models 的长期推荐路径是 Responses API。OpenAI 文档明确建议，在多轮状态处理中优先使用 `previous_response_id`。如果系统以无状态方式运行，或者因为数据保留策略不能依赖服务端状态，就需要把上一轮返回的相关有序 output items 作为下一轮 input 的一部分传回。

OpenAI reasoning models 和工具调用组合时，关键状态不是 DeepSeek 风格的 `reasoning_content` 字符串，而是 Responses API 的 output items，例如：

- `reasoning` output item。
- `function_call` output item。
- `function_call_output` input item。
- assistant `message` output item。

OpenAI 文档还说明，如果在 `store=false` 或零数据保留场景下使用 reasoning items，每一次 Responses API 请求都需要包含 `include: ["reasoning.encrypted_content"]`。这样每一轮返回的 reasoning item 才会带有可供下一轮继续回传的加密内容。

官方参考：

- [OpenAI Using reasoning models](https://developers.openai.com/api/docs/guides/latest-model#using-reasoning-models)
- [OpenAI Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)
- [OpenAI Conversation state](https://developers.openai.com/api/docs/guides/conversation-state#passing-context-from-the-previous-response)
- [OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling)

## 3. 当前 RepoHarness 的兼容缺口

当前 RepoHarness 的 OpenAI-compatible provider 路径把 provider 响应统一解析为 `ModelResponse`，并把 assistant 消息继续追加到 AgentLoop 的 `messages` 中。这个抽象可以处理普通文本和工具调用，但还没有完整保存 provider 私有状态。

当前关键缺口如下：

1. `response_from_provider_payload()` 只读取 provider response 中的 `message.content` 和 `message.tool_calls`，没有保存 DeepSeek `message.reasoning_content`。
2. `AgentLoop` 追加下一轮 assistant message 时，只追加 `content`、`tool_calls`、`model_error_type` 和 `scaffold_phase`，没有携带 provider 私有状态。
3. `_to_chat_message()` 把 RepoHarness 内部 message 转成 provider request message 时，只输出 `role`、`content`、`tool_calls` 和 tool result 字段，无法把 DeepSeek 所需的 `reasoning_content` 回传给 API。
4. OpenAI provider 当前是 Chat Completions 兼容路径，不能表达 Responses API 的 `reasoning` output item、`function_call` output item、`function_call_output` input item、`previous_response_id` 和 `reasoning.encrypted_content`。

一个最小例子可以说明当前 DeepSeek 缺口：

```json
{
  "role": "assistant",
  "content": "我需要先读取文件。",
  "reasoning_content": "任务要求定位 bug，我需要先查看相关源码。",
  "tool_calls": [
    {
      "id": "call_1",
      "type": "function",
      "function": {
        "name": "read_file",
        "arguments": "{\"path\":\"src/example.py\"}"
      }
    }
  ]
}
```

如果下一次请求中只回传下面内容，DeepSeek thinking 模式会认为工具调用链缺少必要思考状态：

```json
{
  "role": "assistant",
  "content": "我需要先读取文件。",
  "tool_calls": [
    {
      "id": "call_1",
      "type": "function",
      "function": {
        "name": "read_file",
        "arguments": "{\"path\":\"src/example.py\"}"
      }
    }
  ]
}
```

长期修复需要保证 RepoHarness 内部能保存第一段消息中的 `reasoning_content`，并在发给 DeepSeek 的后续 provider request 中还原它。

## 4. 设计原则

### 4.1 不把两家 provider 强行统一成同一个字段

DeepSeek 的长期修复重点是 `reasoning_content` 字段回传。OpenAI 的长期修复重点是 Responses API output items 和 response state。两者都属于“provider 私有连续状态”，但不能统一为一个 `reasoning_content` 字符串。

正确抽象应该是：

```text
RepoHarness 标准消息:
  role
  content
  tool_calls

Provider 私有连续状态:
  provider_private.deepseek.state_id
  provider_private.deepseek.reasoning_content_required_for_replay
  provider_private.openai_responses.previous_response_id
  provider_private.openai_responses.ordered_output_items_ref
  provider_private.openai_responses.reasoning_encrypted_content_present
  provider_private.openai_responses.phase_values_preserved
```

### 4.2 provider 私有状态默认不进入普通训练导出，但可以显式进入 reasoning trace 导出

`reasoning_content`、OpenAI `reasoning` output item 和 `reasoning.encrypted_content` 都不应该默认作为普通 assistant 文本进入普通 supervised fine-tuning target，也不应该进入公开简历产物。明文 provider 私有状态只能保存在单独的运行态 `ProviderPrivateStateStore` 中，用于下一轮 provider request 构造。进入 AgentLoop 普通 `messages`、`prepared_messages` artifact、普通 transcript、默认训练导出和公开产物的只能是状态标识、存在性标记、脱敏 artifact 引用和导出策略字段。

这里不能用“DeepSeek 是开源或开放权重模型，所以 reasoning_content 不敏感”作为默认放开依据。RepoHarness 的边界判断不是在判断模型权重是否开放，而是在判断某段内容是否应该成为普通轨迹、训练目标或公开证据。即使模型权重开放，`reasoning_content` 仍然可能包含以下内容：

- 模型从仓库源码、工具输出和错误日志中复制出的项目私有细节。
- 模型对任务的中间假设、错误尝试和不稳定思考路径，不适合作为监督微调的标准答案。
- provider 协议要求回传但不等同于 RepoHarness 标准 assistant answer 的中间状态。
- 将来在 GitHub issue flow、企业仓库或本地私有仓库任务中可能出现的敏感路径、配置、日志片段或用户输入。

因此，正式 baseline、默认 training export 和公开简历产物仍然不能把 DeepSeek `reasoning_content` 明文混入普通 `messages`、`prepared_messages`、普通 transcript 或普通 SFT target。真正需要把 `reasoning_content` 作为训练信号时，应新增一个显式 opt-in 的 `provider_reasoning_trace_training_export`。它可以把 `reasoning_content` 作为专门的 reasoning trace target 导出，但必须独立于正式 baseline、普通 trajectory export 和 public-safe demo，单独标记 `reasoning_trace_training_allowed=true`、`ordinary_sft_target_allowed=false`、`not_public_safe_by_default=true` 和 `requires_explicit_reasoning_export_policy=true`。

导出策略必须保持：

```text
provider_private_state.export_allowed = false
provider_private_state.default_training_payload_allowed = false
provider_private_state.reasoning_trace_training_payload_allowed = explicit_opt_in_only
provider_private_state.public_demo_allowed = false
provider_private_state.live_state_persisted_in_prepared_messages = false
```

### 4.3 AgentLoop 不理解 provider 私有字段语义

AgentLoop 只负责保存和传递 `ModelMessage.metadata.provider_private` 中的安全句柄，例如 `state_id`、`redacted_state_ref`、`reasoning_content_present` 和 `reasoning_content_required_for_replay`。具体哪些字段要发送给 provider，以及如何用 `state_id` 找到明文 live state，由 provider adapter 决定。这样可以避免把 DeepSeek 或 OpenAI 的特殊协议散落到 AgentLoop 状态机里，也避免把明文思考内容写入 `prepared_messages`。

### 4.4 prepared_messages 与 raw_provider_request 必须区分

`prepared_messages` 是 RepoHarness 内部准备好的消息序列。`raw_provider_request` 是真正发给 provider 的请求体。长期修复后，两者都需要可审计：

- `prepared_messages` 可以包含 provider 私有状态的安全摘要、引用或脱敏占位。
- `raw_provider_request` 必须保存脱敏后的实际 provider request 结构，用于证明协议字段确实被带上。
- 原始 reasoning 内容必须被 redaction policy 遮蔽，不能以明文出现在公开 artifact 中。
- 如果需要证明真实 HTTP body 形态，应额外记录脱敏后的 `redacted_http_body_shape_ref`，而不能只根据 SDK body 或 wrapper body 推断。

## 5. DeepSeek 长期修复方案

### 5.1 数据模型扩展

在 `ModelMessage.metadata` 中增加 provider 私有状态句柄约定，不需要把 `reasoning_content` 做成所有 provider 都可见的一等字段，也不能把明文 `reasoning_content` 直接放入普通 message metadata。原因是当前 `ContextManager` 会把 AgentLoop 的 `messages` 原样复制到 `prepared_messages` artifact；如果 metadata 里保存明文思考内容，就会绕过 raw provider artifact 的脱敏策略。

建议结构：

```json
{
  "role": "assistant",
  "content": "我需要读取文件。",
  "tool_calls": [],
  "metadata": {
    "provider_private": {
      "deepseek": {
        "format_version": "repo_harness_deepseek_provider_private_v0",
        "state_id": "provider_private_state_000001",
        "redacted_state_ref": {
          "path": "artifacts/provider_private_state_000001_redacted.json",
          "sha256": "..."
        },
        "reasoning_content_present": true,
        "reasoning_content_required_for_replay": true
      }
    }
  }
}
```

其中：

- 明文 `reasoning_content` 只保存在运行态 `ProviderPrivateStateStore` 中，由 `state_id` 索引。
- `redacted_state_ref` 指向经过 redaction 的 artifact，不能包含明文 reasoning 内容。
- `reasoning_content_required_for_replay` 表示这条 assistant 消息位于一个已经发生过工具调用的 user turn 中，因此后续 DeepSeek request 必须携带该字段。
- `prepared_messages`、普通 transcript、默认 training export 和 public artifact 不得包含 `reasoning_content` 明文字段。显式 opt-in 的 `provider_reasoning_trace_training_export` 可以通过 `state_id` 从运行态 store 或受控 reasoning trace store 中读取明文 reasoning 内容，生成单独的 trainable reasoning trace record。

### 5.2 Provider response 解析

修改 OpenAI-compatible response parser，让 DeepSeek provider 可以捕获 `message.reasoning_content`。

推荐不要让通用 parser 无条件理解所有 provider 私有字段，而是提供 provider-specific hook，例如：

```text
response_from_provider_payload(..., provider_private_parser=parse_deepseek_private_fields)
```

DeepSeek hook 负责：

1. 检查 `choices[0].message.reasoning_content` 是否存在。
2. 如果存在，把明文写入运行态 `ProviderPrivateStateStore`，生成 `state_id` 和脱敏后的 `redacted_state_ref`。
3. 维护一个 provider turn state，记录“从上一条 user message 之后到当前为止”的 `assistant_state_ids_since_last_user` 和 `tool_call_seen_since_last_user`。
4. 如果当前 user turn 内任意 assistant message 发生过 `tool_calls`，则该 user turn 内所有带 `reasoning_content` 的 assistant message 都必须标记 `reasoning_content_required_for_replay=true`，包括“发生工具调用之前的 assistant reasoning”和“工具调用之后、没有新 tool call 的 final assistant reasoning”。
5. 在后续请求进入新的 user turn 时，仍要继续保留上一个发生过工具调用的 user turn 中这些 required reasoning states。
6. 在单独的 `TrajectoryEvent.data` 中记录 `provider_private_state_captured=true`、`state_id`、`redacted_state_ref` 和 replay requirement，但不把这些字段直接塞进当前固定 schema 的 `ModelCallEvent`，也不记录明文内容。

这个范围比“本条 assistant message 自己带有 `tool_calls`”更宽。原因是 DeepSeek 官方规则按两个 user 消息之间的工具调用历史判断：只要该 user turn 中发生过工具调用，这个 user turn 中间 assistant 的 `reasoning_content` 后续都要参与上下文拼接。

### 5.3 AgentLoop 消息传递

当前 AgentLoop 追加下一轮 assistant message 时，需要保留 `response.assistant_message.metadata` 中的安全 provider private 句柄，但必须先经过 sanitizer，确保 metadata 中没有明文 `reasoning_content`、OpenAI reasoning item 明文或 encrypted reasoning content。

目标结构：

```python
safe_metadata = sanitize_provider_private_metadata_for_messages(
    response.assistant_message.metadata
)
messages.append(
    {
        "role": "assistant",
        "content": response.assistant_message.content,
        "tool_calls": [call.model_dump(mode="json") for call in response.tool_calls],
        "metadata": safe_metadata,
        "model_error_type": response.model_error_type,
        "scaffold_phase": current_phase,
    }
)
```

这一步只做安全句柄传递，不判断 DeepSeek 字段含义。明文 live state 不进入 `messages`，只由 provider adapter 在序列化下一轮请求时通过 `state_id` 从运行态 store 读取。

### 5.4 DeepSeek request 构造

当前 `_to_chat_message()` 是 provider-agnostic 函数。长期修复应改成 provider-aware message serializer，至少支持：

```text
to_provider_messages(provider="deepseek", internal_messages=...)
to_provider_messages(provider="openai_chat_completions", internal_messages=...)
to_provider_messages(provider="openai_responses", internal_messages=...)
```

DeepSeek serializer 在处理 assistant message 时：

1. 输出 `role`、`content` 和 `tool_calls`。
2. 如果 `metadata.provider_private.deepseek.state_id` 存在，则从运行态 `ProviderPrivateStateStore` 读取明文 `reasoning_content`，在真实 DeepSeek request message 中额外输出 `reasoning_content`。
3. 如果 `reasoning_content_required_for_replay=true` 但缺少 `state_id`，或者 `state_id` 找不到 live state，直接生成本地 `provider_protocol_error`，不要把必然失败的请求发给 DeepSeek。
4. 写入 raw provider request artifact 时必须经过 redaction，因此 artifact 中只能看到 `reasoning_content: "<REDACTED_REASONING>"`，不能看到明文。

正确请求示例：

```json
{
  "role": "assistant",
  "content": "我需要读取文件。",
  "reasoning_content": "<redacted in artifact, real value in live request>",
  "tool_calls": [
    {
      "id": "call_1",
      "type": "function",
      "function": {
        "name": "read_file",
        "arguments": "{\"path\":\"src/example.py\"}"
      }
    }
  ]
}
```

### 5.5 DeepSeek thinking 配置策略

长期支持完成后，DeepSeek run config 应显式记录 thinking 策略，不能依赖 provider 默认值。

建议配置：

```yaml
model:
  provider: deepseek
  provider_specific_options:
    thinking:
      type: enabled
    reasoning_effort: high
```

如果正式评测不希望开启 thinking，则必须显式写成：

```yaml
model:
  provider: deepseek
  provider_specific_options:
    thinking:
      type: disabled
```

inspect gate 必须拒绝未显式声明 thinking 策略的 DeepSeek 正式评测配置。原因是 DeepSeek 官方默认 thinking 为 enabled，省略字段会让评测行为依赖 provider 默认值，不利于审计和复现。

### 5.6 DeepSeek 脱敏要求

当前 `redact_provider_payload()` 已经会把键名为 `reasoning_content` 的字段替换成 `<REDACTED_REASONING>`。长期修复时需要补齐三类检查：

1. raw provider response artifact 中的 `reasoning_content` 必须脱敏。
2. raw provider request artifact 中回传的 `reasoning_content` 必须脱敏。
3. 默认 training export、public summary、resume bundle 和 public-safe demo 中不得出现真实 `reasoning_content`。只有显式 opt-in 的 reasoning trace training export 可以包含明文 `reasoning_content`。

如果未来确实要导出 DeepSeek 明文思考内容，必须新增独立的 reasoning trace 训练导出模式，例如：

```text
export_mode = provider_reasoning_trace_training_export
record_type = reasoning_augmented_trajectory
includes_provider_reasoning_content = true
ordinary_trajectory_export = false
ordinary_sft_target_allowed = false
reasoning_trace_target_allowed = true
raw_provider_artifact_as_training_source = false
public_demo_allowed = false
formal_baseline_claim_allowed = false
requires_explicit_user_acknowledgement = true
requires_explicit_reasoning_export_policy = true
```

这种导出可以用于训练带 reasoning trace 的模型，也可以用于离线分析“模型思考内容是否有训练价值”或“工具调用前后的 reasoning 稳定性”。但它不能和正式 pre-verl accepted rate、默认 training export、公开简历 evidence bundle 或 public-safe demo 混在一起，也不能直接从 raw provider artifact 读取训练样本。raw provider artifact 仍然只承担协议审计职责，训练样本必须由独立 schema 清洗生成。

## 6. OpenAI 长期修复方案

### 6.1 不在现有 Chat Completions adapter 上硬塞 reasoning items

OpenAI reasoning models 的长期路径应该新增 Responses API provider adapter，而不是把 Responses API 的 output items 硬塞进当前 Chat Completions 兼容结构。

建议新增：

```text
OpenAIResponsesProviderClient
OPENAI_RESPONSES_PROVIDER_VERSION = "repo_harness_openai_responses_provider_v0"
OPENAI_RESPONSES_MESSAGE_FORMAT_VERSION = "repo_harness_openai_responses_items_v0"
```

同时保留现有 `OpenAIProviderClient` 作为 Chat Completions 兼容路径，主要用于历史 V5 provider comparison 和不需要 Responses API 状态的普通调用。

### 6.2 Responses API 请求策略

OpenAI Responses API 长期支持应提供两种状态模式。

第一种是服务端状态模式：

```yaml
model:
  provider: openai
  endpoint_category: openai_responses
  provider_specific_options:
    state_mode: previous_response_id
    store: true
```

这种模式最简单。每轮保存 `response.id`，下一轮请求使用 `previous_response_id`。它适合允许 OpenAI 保存 response object 的场景。

第二种是无状态模式：

```yaml
model:
  provider: openai
  endpoint_category: openai_responses
  provider_specific_options:
    state_mode: manual_output_items
    store: false
    include:
      - reasoning.encrypted_content
```

这种模式适合不能依赖服务端状态的场景。RepoHarness 必须保存上一轮返回的有序 `response.output` slice，并在下一轮请求中按原顺序带回。默认策略是不重建、不筛掉 assistant `message` item、`reasoning` item、`function_call` item、`phase`、`id`、`status` 等 provider 返回字段，只在原始有序 slice 之后追加 RepoHarness 生成的 `function_call_output` item。`manual_output_items + store=false` 或零数据保留模式下，每一次 `responses.create` 请求都必须包含 `include: ["reasoning.encrypted_content"]`，inspect 必须检查所有 raw request，而不能只检查第一轮请求。

### 6.3 Responses API item 模型

建议新增 provider 私有状态结构：

```json
{
  "provider_private": {
    "openai_responses": {
      "format_version": "repo_harness_openai_responses_private_v0",
      "response_id": "resp_...",
      "state_mode": "manual_output_items",
      "ordered_output_items_state_id": "provider_private_state_000010",
      "ordered_output_items_ref": {
        "path": "artifacts/openai_response_output_items_redacted.json",
        "sha256": "..."
      },
      "reasoning_items_present": true,
      "encrypted_reasoning_present": true,
      "phase_values_preserved": true
    }
  }
}
```

不要把 OpenAI `reasoning` item 展开成普通 assistant text。它只应作为 provider 私有状态参与下一轮 request 构造。

### 6.4 Responses API tool calling 映射

RepoHarness 内部工具调用仍然使用统一 `ToolCall` 和 `ToolResult`。OpenAI Responses adapter 负责双向转换：

```text
OpenAI response.output function_call item
  -> RepoHarness ToolCall

RepoHarness ToolResult
  -> OpenAI input function_call_output item
```

一个简化的无状态下一轮 input 应类似。这里的 `reasoning` 和 `function_call` item 代表上一轮 `response.output` 中的有序 item，实际实现不应该根据类型重新拼装一个新列表，而应该保留 provider 返回的 ordered output slice，再追加工具结果：

```json
[
  {
    "type": "reasoning",
    "id": "rs_...",
    "encrypted_content": "..."
  },
  {
    "type": "function_call",
    "id": "fc_...",
    "call_id": "call_1",
    "name": "read_file",
    "arguments": "{\"path\":\"src/example.py\"}"
  },
  {
    "type": "function_call_output",
    "call_id": "call_1",
    "output": "文件内容摘要..."
  }
]
```

如果使用 `previous_response_id`，则可以不手动回传上一轮 output items，但仍然要把本轮工具结果作为 `function_call_output` 提交给下一次 Responses API 调用。

### 6.5 phase 字段

OpenAI 文档建议在长流程和工具密集型 Responses API 工作流中保留 assistant output item 的 `phase` 值。RepoHarness 的 OpenAI Responses adapter 应当：

1. 保存 provider 返回的 `phase`。
2. 手动状态模式下原样回传 `phase`。
3. 在 public artifact 中只记录 `phase` 是否存在和是否保留，不需要暴露 reasoning 内容。

### 6.6 OpenAI 脱敏要求

OpenAI 原始 reasoning tokens 不通过 API 明文暴露，但 Responses API 可能返回 reasoning summary 或 encrypted reasoning content。RepoHarness 应按如下策略处理：

```text
reasoning output item:
  export_allowed = false
  training_payload_allowed = false
  public_demo_allowed = false

reasoning.encrypted_content:
  export_allowed = false
  training_payload_allowed = false
  public_demo_allowed = false
  live_request_replay_allowed = true

reasoning summary:
  default export_allowed = false
  default training_payload_allowed = false
  can_enable_only_with_explicit_policy = true
```

需要扩展 `redact_provider_payload()` 的 reasoning key 判断，覆盖：

- `encrypted_content`
- `reasoning.encrypted_content`
- `summary`，当父节点是 reasoning output item 时
- `reasoning`，仅当它是 response output item 或 provider 私有 reasoning state 时脱敏，不能把请求配置里的 `reasoning.effort`、`reasoning.summary` 开关和值全部遮掉

## 7. 公共实现切分

长期修复建议分四层实施，避免 provider 逻辑污染 AgentLoop。

### 7.1 ProviderPrivateState

新增运行态内部数据结构和 store：

```text
ProviderPrivateState
  state_id
  provider
  format_version
  live_state
  redacted_artifact_ref
  export_allowed
  default_training_payload_allowed
  reasoning_trace_training_payload_allowed
  replay_policy

ProviderPrivateStateStore
  put(state) -> state_id
  get(state_id) -> live_state
  write_redacted_artifact(state_id) -> redacted_artifact_ref
  drop_after_run(run_id)
```

其中 `live_state` 只在当前运行进程中用于下一次 provider request，不写入 `messages`、`prepared_messages`、普通 transcript、默认 training export 或 public artifact。写入 raw provider artifact 时必须使用 redacted 版本。默认训练导出只允许读取 `redacted_artifact_ref` 和策略字段，不允许读取 `live_state`。只有显式启用 `provider_reasoning_trace_training_export` 时，专门的 reasoning trace exporter 才能从运行态 store 或受控 reasoning trace store 读取明文 reasoning 内容，并生成独立 schema 的 trainable record。

### 7.2 ProviderMessageSerializer

新增 provider-aware serializer：

```text
serialize_messages_for_provider(provider, endpoint_category, internal_messages, provider_options)
```

它替代当前单一 `_to_chat_message()` 的职责。这样 DeepSeek 可以输出 `reasoning_content`，OpenAI Chat Completions 可以保持旧格式，OpenAI Responses 可以输出 Responses API items。

### 7.3 ProviderResponseParser

每个 provider adapter 应该拥有自己的 response parser：

```text
parse_deepseek_chat_completion_response()
parse_openai_chat_completion_response()
parse_openai_responses_response()
```

通用部分可以复用工具调用解析、token usage 提取、错误分类和 artifact 写入，但 provider 私有状态捕获不能被通用 parser 吞掉。

### 7.4 ExportPolicy

导出和 public-safe scan 需要新增检查项：

```text
no_deepseek_reasoning_content_in_training_export
no_openai_reasoning_items_in_training_export
no_reasoning_encrypted_content_in_public_artifacts
raw_provider_request_response_redacted
provider_private_state_has_export_policy
```

## 8. 分阶段实施计划

### 阶段 A：正式评测防误用门

目标是先防止正式 baseline 误入未兼容模式。

需要实现：

1. DeepSeek 正式评测 run config 必须显式声明 `provider_specific_options.thinking.type`。
2. 在长期兼容修复完成前，正式 pre-verl baseline 只能使用 `thinking.type=disabled`。
3. inspect gate 拒绝 DeepSeek thinking 未声明、声明为 enabled 但 provider private state 不支持、或者 raw request 中缺少 thinking 配置的运行。
4. inspect gate 必须按当前 DeepSeek adapter 的真实 artifact 形态检查 `body.extra_body.thinking.type=disabled`，同时检查 run config 中的 `provider_specific_options.thinking.type=disabled`。
5. 如果要证明最终 HTTP body，而不是 SDK wrapper body，则需要新增 `redacted_http_body_shape_ref` 或等价字段，记录 `_sdk_body_to_http_body()` 展平后的脱敏结构中存在顶层 `thinking.type=disabled`。

阶段 A 完成后可以继续二十三题正式 baseline，但报告中必须写明：

```text
DeepSeek thinking disabled for formal baseline until provider-private reasoning replay support is implemented.
```

### 阶段 B：DeepSeek thinking enabled 兼容

目标是让 DeepSeek thinking enabled 加工具调用可以稳定多轮运行。

需要实现：

1. 捕获 `reasoning_content`。
2. 在 AgentLoop messages 中只保留 provider 私有状态的安全句柄、脱敏引用和 replay 标记，不保留明文 live state。
3. DeepSeek provider serializer 回传 `reasoning_content`。
4. 本地协议检查发现 required reasoning 缺失时，停止在本地 `provider_protocol_error`，不要发起必然失败的 API 请求。
5. raw request 和 raw response artifact 全部脱敏。
6. provider turn state 能覆盖“同一 user turn 内发生 tool call 后，所有带 `reasoning_content` 的 assistant message 都需要后续回传”的范围。

### 阶段 C：OpenAI Responses adapter

目标是为 OpenAI reasoning models 建立正确的 Responses API 路径。

需要实现：

1. 新增 `OpenAIResponsesProviderClient`。
2. 支持 `previous_response_id` 状态模式。
3. 支持 `manual_output_items` 无状态模式，并保存 ordered `response.output` slice，而不是只保存白名单 item。
4. 支持在 `manual_output_items + store=false` 或零数据保留模式下，每一次 `responses.create` 都带上 `include: ["reasoning.encrypted_content"]`。
5. 支持 Responses API function call item 与 RepoHarness `ToolCall` 的双向转换。
6. 保存并回传 `phase`。
7. 保持 Chat Completions adapter 的历史兼容。

### 阶段 D：审计、导出和回归测试收口

目标是证明修复不会污染训练轨迹和简历展示产物。

需要实现：

1. 新增 provider private state inspect。
2. 扩展 public-safe scan。
3. 扩展 training export audit：默认训练导出必须不包含明文 provider reasoning；显式 reasoning trace 训练导出必须使用独立 schema、独立 export manifest 和独立 public-safe gate。
4. 增加 DeepSeek thinking enabled live smoke。
5. 增加 OpenAI Responses API reasoning function calling live smoke。

## 9. 修复完成后的验证方案

### 9.1 单元测试

DeepSeek 单元测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_deepseek_reasoning_content_replay.py
```

至少覆盖：

1. provider response 中包含 `reasoning_content` 和 `tool_calls` 时，`ProviderPrivateStateStore` 保存明文 live state，`ModelResponse.assistant_message.metadata.provider_private.deepseek` 只保存 `state_id`、脱敏引用和 replay 标记。
2. AgentLoop 追加下一轮 assistant message 时，安全 metadata 不丢失，并且普通 `messages` 和 `prepared_messages` artifact 中没有明文 `reasoning_content`。
3. DeepSeek serializer 在下一轮 request 中输出 `reasoning_content`。
4. `reasoning_content_required_for_replay=true` 但字段缺失时，本地返回 `provider_protocol_error`。
5. raw provider artifacts 中的 `reasoning_content` 被替换为 `<REDACTED_REASONING>`。
6. 同一个 user turn 内，先有 assistant reasoning，后发生 tool call，再有不带 tool call 的 final assistant reasoning 时，该 user turn 内所有 reasoning state 后续都被保留。

OpenAI Responses 单元测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_openai_responses_reasoning_items.py
```

至少覆盖：

1. Responses API `reasoning` item 不进入普通 assistant content。
2. `function_call` item 可以转换为 RepoHarness `ToolCall`。
3. RepoHarness `ToolResult` 可以转换为 `function_call_output` item。
4. `previous_response_id` 模式会保存并使用上一轮 response id。
5. `manual_output_items` 模式会按原顺序回传上一轮 ordered `response.output` slice，并在其后追加 `function_call_output`。
6. `manual_output_items + store=false` 或零数据保留模式下，每一次请求都包含 `include: ["reasoning.encrypted_content"]`。
7. `phase` 在手动状态模式中被原样保留。

### 9.2 集成测试

DeepSeek 集成测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/integration/test_deepseek_thinking_tool_replay.py
```

测试应使用 fake HTTP server 或录制响应构造如下链路：

```text
第 1 次模型响应:
  assistant content + reasoning_content

第 2 次模型响应:
  assistant content + reasoning_content + tool_call

工具执行:
  tool result

第 3 次模型响应:
  assistant content + reasoning_content，但没有 tool_call

后续 provider request:
  必须包含这个 user turn 内第 1、2、3 次 assistant 的 required reasoning_content
```

OpenAI 集成测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/integration/test_openai_responses_reasoning_tool_loop.py
```

测试应覆盖：

```text
response.output:
  reasoning item
  function_call item

RepoHarness:
  执行工具
  生成 function_call_output

下一次 responses.create:
  previous_response_id 模式：带 previous_response_id 和 function_call_output
  manual_output_items 模式：按原顺序带 ordered response.output slice，并在其后追加 function_call_output
```

### 9.3 Live smoke

DeepSeek thinking enabled live smoke：

```bash
PATH=.venv/bin:$PATH repo-harness run-task TASK_DEFINITION \
  --config RUN_CONFIG_WITH_DEEPSEEK_THINKING_ENABLED \
  --run-id deepseek-thinking-tool-replay-smoke-YYYYMMDDTHHMMSSZ \
  --out runs/provider-compat/deepseek-thinking-tool-replay-smoke-YYYYMMDDTHHMMSSZ
```

通过条件：

1. 至少发生两次真实 DeepSeek provider call。
2. 至少发生一次 tool call 和对应 tool result。
3. 第二次 raw provider request 的脱敏 artifact 中存在 `reasoning_content: "<REDACTED_REASONING>"`。
4. 没有出现 `The reasoning_content in the thinking mode must be passed back to the API`。
5. public-safe scan 没有发现明文 `reasoning_content`。

OpenAI Responses live smoke：

```bash
PATH=.venv/bin:$PATH repo-harness run-task TASK_DEFINITION \
  --config RUN_CONFIG_WITH_OPENAI_RESPONSES_REASONING \
  --run-id openai-responses-reasoning-tool-smoke-YYYYMMDDTHHMMSSZ \
  --out runs/provider-compat/openai-responses-reasoning-tool-smoke-YYYYMMDDTHHMMSSZ
```

通过条件：

1. raw provider request 使用 `/v1/responses`，不是 `/v1/chat/completions`。
2. reasoning 模型请求包含 `reasoning.effort`。
3. 工具调用后的下一轮请求包含正确的 response state。
4. `manual_output_items + store=false` 或零数据保留模式下，每一次 raw request 都包含 `include: ["reasoning.encrypted_content"]`。
5. `reasoning` output item 没有进入普通 assistant transcript target。

### 9.4 Pre-verl inspect gate

建议新增：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-provider-reasoning-compatibility RUN_DIR \
  --assert-provider-private-state-roundtrip \
  --assert-raw-artifacts-redacted \
  --assert-training-export-clean \
  --assert-public-artifacts-clean
```

该 inspect 至少检查：

- DeepSeek thinking enabled 运行中，发生过工具调用的 user turn 内，所有带 `reasoning_content` 的 assistant message 都有 provider private reasoning state。
- DeepSeek 后续 raw request 中存在脱敏后的 `reasoning_content` 字段。
- OpenAI Responses 运行中，所有 reasoning items 都以 provider private state 或 response state item 形式保留。
- OpenAI Responses 手动状态模式中，`function_call_output` 之前的 ordered `response.output` slice 没有丢失、筛选或乱序。
- OpenAI Responses `manual_output_items + store=false` 或零数据保留模式下，所有 raw request 都包含 `include: ["reasoning.encrypted_content"]`。
- 默认 training export 不包含 DeepSeek `reasoning_content` 明文。
- 如果启用 `provider_reasoning_trace_training_export`，则必须存在独立 reasoning trace export manifest，且每条包含明文 reasoning 的记录都必须标记 `record_type=reasoning_augmented_trajectory`、`reasoning_trace_target_allowed=true`、`public_demo_allowed=false` 和 `raw_provider_artifact_as_training_source=false`。
- training export 不包含 OpenAI reasoning item、reasoning summary 或 encrypted reasoning content。
- public artifact 不包含真实 API key、真实 reasoning 内容或 evaluator-only verifier 内容。

### 9.5 全量回归

长期修复完成后，至少运行：

```bash
PATH=.venv/bin:$PATH python -m compileall src scripts
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-boundary-index \
  PRE_VERL_BOUNDARY_INDEX \
  --assert-all-formal-runs-bound \
  --assert-command-order \
  --assert-clean-source-origin \
  --assert-run-task-lineage \
  --assert-no-legacy-adapter
```

如果长期修复影响正式二十三题 baseline，必须新建 baseline id，不能把开启 thinking 或切换 OpenAI Responses API 后的结果混入旧 baseline。

## 10. 正式评测口径建议

短期正式 pre-verl baseline 应采用：

```yaml
provider_id: deepseek
model_id: deepseek-v4-pro
provider_specific_options:
  thinking:
    type: disabled
```

这样可以先评测 RepoHarness AgentLoop、工具、final verifier 和环境物化链路，而不让 DeepSeek thinking 协议问题污染正式分数。

长期兼容修复完成后，可以新增单独 baseline 或消融实验：

```text
baseline_id: pre_verl_agentloop_deepseek_v4_pro_patch_focused_react_thinking_enabled_v1
```

这条 baseline 必须单独报告，不得和 `thinking.type=disabled` 的 baseline 合并统计。

OpenAI Responses API 修复完成后，也应该作为单独 provider-axis 或 scaffold comparison 运行：

```text
baseline_id: pre_verl_agentloop_openai_responses_reasoning_patch_focused_react_v1
```

它可以用于比较不同 provider 的工具调用稳定性和协议成本，但不能替代 DeepSeek baseline，也不能把 provider 差异解释成 harness 分数差异。

## 11. 最小完成定义

本文档中的长期兼容修复只有在以下条件全部满足时，才能描述为完成：

1. DeepSeek thinking enabled 加工具调用可以完成至少一个两轮以上的 live smoke，不再因为缺少 `reasoning_content` 返回 400。
2. OpenAI Responses API reasoning 加工具调用可以完成至少一个两轮以上的 live smoke，并且 reasoning items 或 `previous_response_id` 被正确保留。
3. raw provider request 和 response artifact 都经过脱敏。
4. 默认 training export 不包含 provider 私有 reasoning 内容；显式 opt-in 的 `provider_reasoning_trace_training_export` 可以包含 DeepSeek 明文 `reasoning_content`，但必须使用独立 schema、独立 manifest 和独立 claim gate。
5. public-safe scan 不包含 provider 私有 reasoning 内容。
6. 全量测试通过。
7. pre-verl inspect gate 可以机器验证 provider private state roundtrip、tool call/tool result 配对、artifact redaction 和 export clean。

如果只完成 DeepSeek thinking disabled 的正式评测防误用门，只能描述为“正式 baseline 已规避未兼容 thinking 协议”，不能描述为“长期兼容 DeepSeek thinking 和 OpenAI reasoning items 已完成”。
