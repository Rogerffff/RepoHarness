# Shared Contract 02：LLMGateway

本文档定义 RepoHarness 内部模型调用与 verl、OpenAI、DeepSeek、本地 vLLM、SGLang 或未来 slime 后端之间的共享契约。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0
scope: planning_only_not_current_implementation
```

## 1. 设计目标

RepoHarness 当前已有 `ModelClient.generate(...)`，但它主要面向 provider text / tool call 路径，不直接保存在线强化学习需要的 token-in-token-out 事实。

接入 verl 后，RepoHarness 需要新增 `LLMGateway`，原因是：

1. RepoHarness 的 agent loop 不应该直接依赖 verl 的 `LLMServerClient`。
2. verl online training 需要直接消费 token ids、log probabilities、mask 和 policy version 等信息。
3. 未来可能切换到 slime、本地 vLLM、SGLang 或 provider teacher 数据生成，不能把 verl 写死在 harness 内部。

建议目标接口：

```text
LLMGateway.generate_turn(request: LLMGatewayRequest) -> LLMGatewayResponse
```

实现上第一版可以是 async 接口；如果 RepoHarness 内部仍有同步 agent loop，可以先通过 adapter 包装，但 contract 应该面向 async 未来演进。

## 2. LLMGatewayRequest

```text
LLMGatewayRequest
  schema_version
  contract_version
  route
  run_id
  task_id
  episode_id
  model_call_id
  turn
  context_revision
  messages
  tools
  sampling_params
  provider_options
  tokenizer_policy
  sticky_session_id
  timeout_seconds
  budget_state
  recorder_policy
  visibility_policy
  tracing
```

### 2.1 route

第一版 route 值：

```text
route:
  verl
  openai
  deepseek
  local_vllm
  local_sglang
  replay
  mock
```

约束：

- `route=verl` 时必须通过 `VerlLLMGateway` 包装 verl 的 `LLMServerClient`。
- `route=verl` 内部的真实推理后端用 `inference_backend=sglang|vllm` 表示，不再把 `verl_llm_server_client` 或 `sglang` 作为 route 名称。
- RepoHarness core 只能依赖 `LLMGateway` 抽象，不能直接 import verl runtime 对象。
- provider route 可以通过现有 `ModelClient` adapter 暂时兼容。
- canonical fixture 和 schema 必须拒绝未登记 route，避免不同文档、不同 adapter 之间漂移。

### 2.2 messages 与 tools

```text
messages:
  RepoHarness 已准备好的模型可见 messages。

tools:
  当前 scaffold 允许的工具 schema。
```

约束：

- `messages` 必须已经经过 RepoHarness visibility policy。
- final verifier hidden output、reward metadata、gold patch 和 evaluator-only logs 不允许进入 `messages`。
- `tools` 必须来自当前 scaffold 和 permission policy 解析后的允许工具集合。

### 2.3 sampling_params

```text
sampling_params:
  temperature
  top_p
  top_k
  max_tokens 或 max_new_tokens
  logprobs
  stop
  repetition_penalty
  reasoning_effort
  thinking_mode
```

约束：

- verl adapter 阶段应尽量沿用 verl `AgentLoopWorker.generate_sequences(...)` 传入的 `sampling_params`。
- `logprobs` 在正式在线训练中应开启；调试路径可以允许缺失，但必须显式记录。
- `max_tokens` 必须受 `EpisodeRequest.budgets.max_output_tokens` 限制。
- `reasoning_effort` 或 `thinking_mode` 必须受 `EpisodeRequest.budgets` 和 `run_mode` 约束，训练 rollout 不能默认沿用 full-audit 的高成本 thinking 配置。
- route=verl 时还必须满足 verl rollout server 的长度约束：`prompt_ids` 不能超过 `rollout.prompt_length` 可接受范围，生成后的 `response_ids` 不能超过 `rollout.response_length`，底层 vLLM / SGLang server 还会根据 `max_model_len` 限制 `max_tokens` 或 `max_new_tokens`。

### 2.4 tokenizer_policy

```text
tokenizer_policy:
  tokenizer_source
  chat_template_source
  prompt_tokenization_owner
  token_roundtrip_allowed
```

第一版建议：

```text
tokenizer_source:
  verl_tokenizer_when_route_verl

prompt_tokenization_owner:
  verl_agent_loop_or_gateway_backend

token_roundtrip_allowed:
  false_for_training_path
```

解释：

- route=verl 时，prompt ids 应由 verl tokenizer / processor / chat template 产生，避免 text round-trip 破坏 token 对齐。
- 多轮工具调用时，不能在 episode 末尾拿最终 transcript 重新套 chat template 再分词来伪造训练 token。每次模型调用都应记录当时真实发送给 rollout server 的 prompt ids 和模型返回的 output token ids。
- 如果 provider route 暂时无法提供 token ids，也必须在 response 中标记 `token_source=provider_unavailable` 或 `token_source=re_tokenized_debug_only`，不能伪装成训练可用 token。
- 正式 online PPO / GRPO 路径第一版只允许 `route=verl`。OpenAI、DeepSeek 或其他 provider route 可以服务评测、teacher data generation、SFT export、preference data 或 offline diagnostic replay；除非明确证明 token provenance 和 log probability 满足正式训练要求，否则默认 `invalid_for_online_rl=true`。

### 2.5 sticky_session_id

verl 的 `LLMServerClient` 有 sticky session load balancing。多轮同一 episode 应使用稳定的 `sticky_session_id`：

```text
sticky_session_id:
  建议使用 episode_id 或 run_id。
```

这样同一条多轮 rollout 更容易命中推理后端的 prefix cache。

## 3. LLMGatewayResponse

```text
LLMGatewayResponse
  schema_version
  contract_version
  route
  inference_backend
  model_call_id
  assistant_message
  tool_calls
  prompt_ids
  output_token_ids
  output_logprobs
  response_mask
  stop_reason
  token_source
  policy_version
  routed_experts
  usage
  provider_request_id
  raw_request_ref
  raw_response_ref
  model_call_event_ref
  duration_ms
  error
  extra_fields
```

### 3.1 token 字段

```text
prompt_ids:
  本轮模型输入 token ids。

output_token_ids:
  本轮模型生成 token ids。

output_logprobs:
  与 output_token_ids 对齐的 log probability。

response_mask:
  对本轮 output_token_ids 全部填 1。
```

注意：工具 observation token 不应该由单次 `LLMGatewayResponse` 直接生成。工具 observation 会在 episode 级 `TrainingView` 中作为环境 observation token 拼入 `response_ids`，并对应 `response_mask=0`。

### 3.2 assistant_message 与 tool_calls

RepoHarness 仍然需要 assistant text 和 tool calls 来驱动现有 agent loop：

```text
assistant_message:
  role=assistant
  content
  metadata

tool_calls:
  从模型输出解析出的工具调用。
```

route=verl 时，第一版固定 RepoHarness tool call parser 为权威 tool semantics，避免训练路径和评测路径的工具语义不一致。

约束：

- `LLMGatewayResponse.output_token_ids` 必须保留模型原始生成 token。
- `assistant_message` 和 `tool_calls` 可以是 parser 后的结构化结果，但不能反过来用于构造正式训练 token。
- 如果 parser 修复 malformed tool call，必须记录原始 output token ids、parser id、parser repair type、repair 是否进入模型可见 observation，以及该段 response mask 是否仍然为 `1`。

### 3.3 policy_version

```text
policy_version:
  global_steps
  min_global_steps
  max_global_steps
  checkpoint_ref
```

第一版普通 agent loop 可以允许为空；fully async 阶段必须记录，用于分析 staleness。

命名约束：

- 对齐 verl `TokenOutput.extra_fields` 中使用的复数字段名：`global_steps`、`min_global_steps`、`max_global_steps`。
- 如果 RepoHarness 内部需要更通用的 `policy_version` 对象，也必须保留原始 verl 字段到该对象的映射，不能在 adapter 和 runtime 两边分别发明单数 / 复数字段。

### 3.4 recorder 策略

`LLMGatewayResponse` 可以携带 raw request / raw response artifact ref，但 `training_fast` 不要求总是保存完整明文。

规则：

- `full_audit` 可以保存完整 redacted raw provider request / response。
- `training_fast` 默认只保存 hash、token ids、必要 text、model call event 和抽样 artifact。
- 明文 reasoning trace 默认不进入 `training_fast`。

## 4. VerlLLMGateway 约束

`VerlLLMGateway` 的职责：

```text
RepoHarness prepared messages
  -> verl tokenizer / chat template
  -> prompt_ids
  -> LLMServerClient.generate(...)
  -> TokenOutput
  -> LLMGatewayResponse
```

它必须复用 verl 的：

- `LLMServerClient`
- sticky-session load balancer
- vLLM 或 SGLang server
- token ids
- log probabilities
- routed experts 和 extra fields，如果存在
- `TokenOutput.extra_fields` 中可能出现的参数版本信息，例如 fully async 路径中的 `global_steps`、`min_global_steps`、`max_global_steps`

它不应该：

- 自己启动 verl server。
- 自己管理 Ray worker group。
- 自己同步模型权重。
- 绕过 verl server manager 直接访问底层 vLLM / SGLang 对象。

## 5. 与现有 ModelClient 的关系

现有 `ModelClient` 可以作为 `LLMGateway` 的一个兼容 backend：

```text
ExistingModelClientGateway
  -> ModelClient.generate(...)
  -> LLMGatewayResponse
```

但必须明确：

- provider backend 可能没有真实 token ids 和 logprobs。
- provider backend 适合 evaluation、teacher data generation、debug 和 replay。
- 正式 verl online RL 路径应以 `VerlLLMGateway` 的 token-in-token-out 记录为准。

## 6. 第一版不变量

1. RepoHarness agent loop 只能依赖 `LLMGateway`，不能在核心路径直接依赖 verl。
2. route=verl 时，prompt ids 和 output token ids 必须来自 verl tokenizer / server 返回。
3. `output_logprobs` 如果缺失，必须显式记录缺失原因，不能假装训练可用。
4. 同一条 episode 的多轮请求应使用稳定 sticky session id。
5. raw provider response、明文 reasoning trace 和 evaluator-only metadata 不能默认进入 `training_fast` artifact。
6. tool observation 不是模型生成 token，不能在 gateway response 中标记为生成 token。
7. 不允许通过最终文本重新分词来构造正式训练 token；正式训练 token 必须来自真实 rollout generation 路径。
