# Shared Contract 03：Training View 与 Audit Ref

本文档定义 RepoHarness episode 结果如何同时服务 verl 训练器和 RepoHarness 审计系统。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0
scope: planning_only_not_current_implementation
```

## 1. 为什么必须拆分

RepoHarness 的完整轨迹包含 transcript、events、artifact、命令输出、工具结果、验证器结果、reward metadata 和导出审计证据。它适合复查和数据治理，但不适合直接塞进 verl batch。

verl 训练器需要的是紧凑的训练视图：

```text
prompt_ids
response_ids
response_mask
response_logprobs
reward_score
num_turns
metrics
extra_fields
```

因此，episode result 必须拆成：

```text
training_view:
  给 verl 训练器消费。

audit_ref:
  给人、导出系统、debug 系统和样本筛选系统反查完整证据。
```

## 2. TrainingView

```text
TrainingView
  schema_version
  contract_version
  prompt_ids
  response_ids
  response_mask
  response_logprobs
  response_spans
  reward_score
  num_turns
  verl_metrics
  repo_harness_metrics_ref
  extra_fields
```

### 2.1 prompt_ids

`prompt_ids` 表示 episode 的初始 prompt token ids。

第一版普通 verl agent loop 与 verl `AgentLoopOutput` 保持一致：

```text
prompt_ids:
  list[int]
```

要求：

- route=verl 时必须来自 verl tokenizer / processor / chat template。
- prompt 内容必须是模型可见内容。
- 不能包含 hidden verifier result、gold patch、reward metadata 或 accepted label。

### 2.2 response_ids

`response_ids` 包含 episode 过程中拼接到 response 区域的 token。

verl 当前 `AgentLoopOutput` 文档说明：

```text
response_ids:
  包含 LLM generated token 和 tool response token。
```

RepoHarness 第一版应按这个语义构造：

- assistant 生成 token 进入 `response_ids`。
- 如果把工具 observation token 拼入训练序列，也进入 `response_ids`。
- padding 不在未 padding 的 `TrainingView.response_ids` 中出现；padding 由 verl worker 后处理。

### 2.3 response_mask

`response_mask` 与 `response_ids` 等长。

```text
1:
  模型生成 token。

0:
  工具 observation token、环境 observation token、非训练 token。
```

关键约束：

- tool observation 不是 assistant 生成 token，必须是 `0`。
- final verifier hidden output 不应该进入 response_ids；如果因为某种 debug 原因引用，也必须是 audit artifact，不进入训练序列。
- reward metadata 不能进入 response_ids。

### 2.4 response_logprobs

```text
response_logprobs:
  Optional[list[float]]
```

要求：

- 如果存在，长度应与 `response_ids` 对齐。
- 模型生成 token 应使用 rollout server 返回的 log probability。
- 工具 observation token 可以按 verl ToolAgentLoop 的方式填 `0.0`。
- 正式 PPO / GRPO batch 中所有样本都必须有 `response_logprobs`。不允许同一个 batch 中一部分样本有 log probability、另一部分样本没有。
- `response_mask=0` 的工具 observation token、环境 observation token 和 padding token，对应 `response_logprobs` 必须填 `0.0`。
- 调试阶段可以允许 `response_logprobs=None`，但这类样本只能用于 Mac 本地 debug smoke 或离线诊断，不能进入正式 PPO / GRPO policy loss。
- fully async 阶段如果同一条 trajectory 跨越多个参数版本，必须记录每段 token 对应的参数版本，或至少记录 `min_global_steps`、`max_global_steps` 和 trajectory parameter version summary。

### 2.5 response_spans

`response_spans` 用来解释 `response_ids` 中每个连续片段的来源，防止后续只能看到一串 token 和 mask，却不知道哪一段来自 assistant 生成、哪一段来自工具 observation、哪一段因为超长被排除。

```text
ResponseSpan
  start
  end
  source_type
  model_call_id
  tool_call_id
  artifact_ref
  response_mask_value
  logprob_policy
  policy_version
  global_steps
  min_global_steps
  max_global_steps
```

`source_type` 第一版取值：

```text
assistant_generation
tool_observation
environment_observation
padding_excluded
truncated_excluded
```

约束：

- `start` 和 `end` 使用未 padding 的 `response_ids` 下标区间，左闭右开。
- `assistant_generation` span 的 `response_mask_value` 必须是 `1`。
- `tool_observation` 和 `environment_observation` span 的 `response_mask_value` 必须是 `0`。
- 被排除或截断的片段不能静默消失，必须通过 `padding_excluded`、`truncated_excluded` 或 audit diagnostics 解释。
- route=verl 时，model call span 必须能关联到对应 `GenerationRecord`，并保留 `global_steps`、`min_global_steps`、`max_global_steps`。

### 2.6 reward_score

```text
reward_score:
  float | None
```

第一版语义：

- 对应 RepoHarness `RewardMetadata.final_reward`。
- verl `AgentLoopOutput.as_dict()` 会把 reward 放到最后一个 response token 对应的 `rm_scores[-1]`。
- 如果 episode 因基础设施错误无效，应通过 `invalid_for_training` 和 diagnostics 阻断，而不是伪装成模型负样本。

### 2.7 verl_metrics 与 RepoHarness metrics 的边界

verl 当前 `AgentLoopOutput.metrics` 使用的是 `AgentLoopMetrics`，字段较窄：

```text
verl_metrics:
  generate_sequences
  tool_calls
  compute_score
  num_preempted
```

因此第一版 contract 明确拆分：

```text
TrainingView.verl_metrics:
  只承载能直接转换成 verl AgentLoopMetrics 的字段。

TrainingView.repo_harness_metrics_ref:
  指向 RepoHarness 详细 metrics / timing / resource artifact。

extra_fields.repo_harness_timing_summary_ref:
  指向 timing summary。

audit_ref.timing_summary_path:
  指向完整 timing summary 文件。
```

RepoHarness 详细 metrics 至少应覆盖：

```text
repo_harness_metrics:
  rollout_wall_seconds
  model_call_seconds
  tool_seconds
  verifier_seconds
  artifact_write_seconds
  context_prepare_seconds
  docker_setup_seconds
  num_model_calls
  num_tool_calls
  num_verifier_calls
  no_progress_triggered
  invalid_for_training
```

这些详细字段不能悄悄丢失。如果不能放入 verl 原生 `AgentLoopMetrics`，必须通过 `repo_harness_metrics_ref`、`repo_harness_timing_summary_ref`、`repo_harness_resource_summary_ref` 或结构化 `AuditRef` 保留。

### 2.8 extra_fields

`extra_fields` 只放短小、稳定、可传播的引用和非敏感字段。

建议字段：

```text
extra_fields:
  repo_harness_episode_id
  repo_harness_run_id
  repo_harness_task_id
  repo_harness_audit_manifest_ref
  repo_harness_reward_metadata_ref
  repo_harness_final_verifier_ref
  repo_harness_patch_ref
  repo_harness_timing_summary_ref
  repo_harness_resource_summary_ref
  repo_harness_metrics_ref
  repo_harness_status
  repo_harness_invalid_for_training
  repo_harness_invalid_reason
  repo_harness_invalid_for_online_rl
```

这些字段必须是 namespaced flat scalar，也就是带 `repo_harness_*` 前缀，值只能是字符串、数字、布尔值或 `None`。完整结构化 `AuditRef` 保留在 `RepoHarnessEpisodeResult.audit_ref` 和 audit artifact 中，不作为嵌套对象进入 `AgentLoopOutput.extra_fields` 或 verl `DataProto.non_tensor_batch`。

禁止字段：

- raw hidden verifier output。
- gold patch。
- 完整 reward metadata 文本。
- evaluator-only test selector 明文。
- provider secret、credential、完整 raw request header。
- 绝对 `run_dir`、final verifier 本地绝对路径、reward metadata 本地绝对路径或可被模型工具直接读取的本地路径。

### 2.9 verl postprocess 后的 raw_prompt 例外

当前 verl `AgentLoopWorker._agent_loop_postprocess(...)` 会无条件执行：

```text
output.extra_fields["raw_prompt"] = kwargs["raw_prompt"]
```

因此 shared contract 对 `raw_prompt` 单独设定规则：

- `raw_prompt` 必须只包含模型可见 prompt。
- `raw_prompt` 不能包含 hidden verifier、reward metadata、gold patch、accepted label、baseline evaluator-only logs 或 provider secret。
- adapter 的 visibility test 不能只检查 `TrainingView.extra_fields`，还必须检查经过 verl postprocess 后的最终 `AgentLoopOutput.extra_fields`。
- 如果后续导出路径不希望传播明文 prompt，必须在导出或日志边界把 `raw_prompt` 替换为 hash、长度、preview 或 artifact reference；不能在 dataset non-tensor fields 里放隐藏内容再指望后处理清理。

## 3. GenerationRecord

为了从 RepoHarness 多轮模型调用构造 verl 训练视图，建议 episode result 保留 `generation_records`。

```text
GenerationRecord
  turn
  model_call_id
  context_revision
  prompt_ids
  output_token_ids
  output_logprobs
  stop_reason
  model_input_hash
  provider_request_projection_hash
  gateway_route
  inference_backend
  policy_version
  global_steps
  min_global_steps
  max_global_steps
  assistant_message_ref
  raw_response_ref
```

用途：

- 调试 token 和 mask 对齐。
- 支持后续 chunk-level credit assignment。
- 支持 fully async 中的 policy version / staleness 分析。
- 支持从完整 audit trajectory 反查每次模型调用。
- 支持检查 prompt ids 是否来自真实 generation 路径，而不是从最终 transcript 重新分词得到。

硬性要求：

```text
GenerationRecord.prompt_ids
  必须等于当轮传给 LLMServerClient.generate(...) 的 prompt_ids。

GenerationRecord.output_token_ids
  必须等于当轮 TokenOutput.token_ids。
```

这条要求用于防止实现方在 episode 结束后用最终 transcript 重新分词来构造正式训练 token。

## 4. AuditRef

`AuditRef` 是训练视图回指完整 RepoHarness 证据的稳定引用。

```text
AuditRef
  schema_version
  contract_version
  run_id
  episode_id
  task_id
  run_dir
  transcript_path
  events_path
  artifacts_manifest_path
  run_status_path
  run_summary_path
  run_metadata_path
  reward_metadata_path
  final_verifier_path
  patch_path
  timing_summary_path
  trajectory_store_facts_path
  export_audit_path
  important_artifact_refs
```

路径可以是相对 run directory 的路径，也可以是对象存储 URI。第一版本地开发建议使用相对路径，便于 acceptance bundle 和 inspect 命令复核。

当前 RepoHarness 已经有类似模式：先产出 run facts，再产出 audit report，最后把 audit report ref 写回 manifest 或 summary。shared contracts 后续实现时可以沿用“事实文件 + 审计文件 + 稳定引用”的结构，而不是把所有审计内容直接塞进训练样本。

重要边界：

- `AuditRef` 是 RepoHarness 内部和离线审计工具使用的结构化对象，不等同于 verl batch 中可传播的 `extra_fields`。
- audit artifact 必须位于模型 workspace 之外，默认不能被模型工具访问。
- 进入 `AgentLoopOutput.extra_fields` 的只能是 opaque reference，也就是不能被模型工具直接解析成本地路径的非透明引用标识。
- 工具层必须拒绝模型通过 `read_file`、`grep`、`read_tool_result_artifact` 或等价工具读取 run directory、reward metadata、final verifier artifact、hidden selector、hidden test patch、gold patch 和 evaluator-only raw output。

## 5. 可见性规则

| 数据内容 | TrainingView | AuditRef 指向的审计视图 | 原因 |
| --- | --- | --- | --- |
| 模型可见初始 prompt | 是 | 是 | 训练和复查都需要。 |
| assistant 生成 token | 是，`response_mask=1` | 是 | 这是训练目标。 |
| 工具 observation | 可以进入 `response_ids`，但 `response_mask=0` | 是 | 它是环境观察，不是模型生成内容。 |
| final verifier hidden output | 否 | 是 | 防止 reward channel 泄漏。 |
| reward scalar | 是，作为 `reward_score` | 是 | 训练需要标量，审计需要来源。 |
| reward metadata 完整文本 | 否 | 是 | 训练视图只保留引用。 |
| gold patch | 否 | 如果任务数据治理允许，可 evaluator-only 保存 | 不能泄漏给模型。 |
| raw provider response | training_fast 默认否或抽样 | 是或抽样 | 需要控制 artifact 体积。 |
| 明文 reasoning trace | training_fast 默认否 | full_audit 可按策略保存 | 在线训练不应默认写入巨大 trace。 |
| `repo_harness_*` opaque refs | 是，作为 flat scalar | 是 | 训练器用于过滤、日志和离线回查，但模型不可见。 |
| 绝对 run directory 路径 | 否 | 是 | 不能让模型通过工具读取 evaluator-only artifact。 |

## 6. 第一版不变量

1. `len(prompt_ids) <= rollout.prompt_length`。
2. `0 < len(response_ids) <= rollout.response_length`，除非 `invalid_for_training=true`。
3. `len(response_ids) == len(response_mask)`。
4. 正式 PPO / GRPO batch 中所有样本都必须有 `response_logprobs`。
5. `len(response_logprobs) == len(response_ids)`。
6. 所有 `response_mask=0` 的 token 对应 `response_logprobs=0.0`。
7. `response_ids` 为空但 `reward_score` 非空的样本必须在进入 verl 前被拦截。
8. 如果超过 `rollout.prompt_length` 或 `rollout.response_length`，第一版不允许静默截断后继续训练；必须写入 `status_reason`、`budget_consumption.stop_reason` 和 audit diagnostics，并默认标记 `invalid_for_training=true`。
9. 所有 assistant 生成 token 的 `response_mask` 必须是 `1`。
10. 所有工具 observation token 的 `response_mask` 必须是 `0`。
11. `reward_score` 必须能通过 `audit_ref.reward_metadata_path` 或 opaque reward metadata ref 反查来源。
12. `training_fast` 不能删除 `audit_ref`，只能减少 artifact 明文内容或采用压缩、抽样、hash 引用。
13. `AuditRef` 不能指向并发 episode 共享的可变文件。
14. `AuditRef` 必须足以找到 transcript、events、artifact manifest、reward metadata、final verifier 和 patch；否则样本不能进入训练。
15. verl postprocess 后的 `extra_fields.raw_prompt` 必须通过 visibility 检查；它只能是模型可见 prompt，不能包含隐藏评测或 reward 信息。
16. `TrainingView.verl_metrics` 和 RepoHarness 详细 timing/resource metrics 必须分开保存，不能把不兼容字段硬塞进 verl `AgentLoopMetrics` 后静默丢弃。
17. `AgentLoopOutput.extra_fields` 只允许 namespaced flat scalar 和 opaque refs，不允许嵌套 `audit_ref` 对象或本地绝对路径。
