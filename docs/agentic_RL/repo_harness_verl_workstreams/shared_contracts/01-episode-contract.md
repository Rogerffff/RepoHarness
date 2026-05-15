# Shared Contract 01：Episode Request / Episode Result

本文档定义 RepoHarness 接入 verl 的分阶段实现过程中共同使用的 episode 级接口契约。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0
scope: planning_only_not_current_implementation
```

## 1. 设计目标

`RepoHarnessEpisodeRequest` 和 `RepoHarnessEpisodeResult` 是整个顺序开发路线的中心边界：

```text
前置 Harness runtime 和 training_fast 阶段
  -> 接收 RepoHarnessEpisodeRequest
  -> 更快、更稳定地产出 RepoHarnessEpisodeResult
  -> 保证 audit_ref、reward、timing 和状态字段完整

后续 verl adapter 阶段
  -> 从 verl non-tensor sample 构造 RepoHarnessEpisodeRequest
  -> 调用 RepoHarnessRuntime.run_episode(...)
  -> 消费 RepoHarnessEpisodeResult.training_view
  -> 返回 AgentLoopOutput
```

第一版不要把当前 CLI 级 `run_task(...)` 直接暴露给 verl。`run_task(...)` 目前包含配置加载、任务加载、workspace 创建、baseline、agent loop、final verifier、reward、summary 写入等完整命令行编排，适合作为现有评测入口，但不适合作为 Ray worker 内部的可组合 episode runtime。

建议后续从 `src/repo_harness/evaluation/runner.py` 中逐步抽出：

```text
RepoHarnessRuntime.run_episode(request: RepoHarnessEpisodeRequest) -> RepoHarnessEpisodeResult
```

## 2. 当前实现依据

RepoHarness 当前相关事实：

- 当前 agent loop 位于 `src/repo_harness/agent_loop/loop.py`，核心入口是同步 `AgentLoop.run(...)`。
- 当前工具执行上下文位于 `src/repo_harness/tools/minimal.py`，`ToolExecutionContext` 已经通过 workspace facade、artifact writer、verifier feedback facade 和 resolved verifier plan 限制工具可访问边界。
- 当前模型调用协议位于 `src/repo_harness/model_client/protocol.py`，核心接口是同步 `ModelClient.generate(...)`。
- 当前 CLI 级评测编排位于 `src/repo_harness/evaluation/runner.py` 的 `run_task(...)`。
- 当前 task adapter 位于 `src/repo_harness/tasks/adapter.py`，负责把任务定义转换为 `LoadedTask`、`RunnableTask` 和 `VerifierConfig`。
- 当前 workspace 协议位于 `src/repo_harness/workspace/protocol.py`，后端工厂位于 `src/repo_harness/workspace/backend_factory.py`。
- 当前 trajectory 写入由 `src/repo_harness/trajectory/recorder.py` 的 `RunRecorder` 负责。
- 当前 reward schema 位于 `src/repo_harness/reward/schemas.py`，核心字段是 `RewardMetadata.final_reward` 和 `invalid_for_training`。
- 当前 verifier result schema 位于 `src/repo_harness/verifier/schemas.py`。
- 当前 export audit 位于 `src/repo_harness/export/audit.py`，已有 hidden / reward-only 字段不能进入训练数据的审计边界。

verl 当前相关事实：

- 自定义 agent loop 需要继承 `reference/verl/verl/experimental/agent_loop/agent_loop.py` 中的 `AgentLoopBase`。
- `AgentLoopBase.run(...)` 是异步函数，签名是 `async def run(self, sampling_params: dict[str, Any], **kwargs) -> AgentLoopOutput`。
- `kwargs` 来自 verl dataset 的 non-tensor fields。
- `AgentLoopOutput` 包含 `prompt_ids`、`response_ids`、`response_mask`、`response_logprobs`、`reward_score`、`num_turns`、`metrics` 和 `extra_fields`。

## 3. RepoHarnessEpisodeRequest

`RepoHarnessEpisodeRequest` 描述“一条训练或评测 episode 应该如何运行”。第一版字段建议如下。

```text
RepoHarnessEpisodeRequest
  schema_version
  contract_version
  episode_id
  run_id
  task_ref
  initial_context
  agent_policy
  run_mode
  llm_gateway_route
  budgets
  workspace_policy
  recorder_policy
  verifier_policy
  visibility_policy
  seed
  tags
  extra
```

### 3.1 标识字段

```text
schema_version:
  建议值：repo_harness_episode_request_v0

contract_version:
  建议值：repo_harness_verl_shared_contracts_v0

episode_id:
  单条 episode 的全局唯一标识。
  在 verl 里可以由训练 step、sample index、rollout_n 和 task_id 组合生成。

run_id:
  RepoHarness run directory 使用的唯一标识。
  必须保证并发运行时不会多个 episode 写入同一个 run directory。
```

### 3.2 task_ref

`task_ref` 只放任务定位和模型可见任务输入所需的引用，不放隐藏答案。

```text
task_ref:
  task_id
  task_path
  dataset_name
  dataset_split
  dataset_revision
  repo_ref
  base_commit
  environment_id
  source_archive_ref
  task_freeze_ref
  verifier_plan_ref
```

禁止放入 `task_ref` 的内容：

- gold patch。
- hidden test output。
- final verifier hidden result。
- reward scalar。
- accepted / failed 标签。
- baseline evaluator-only 细节。

这些内容只能留在 RepoHarness audit artifacts 中，通过 `audit_ref` 反查。

### 3.3 initial_context

`initial_context` 描述模型第一轮可以看到什么。

```text
initial_context:
  raw_prompt
  initial_messages
  system_prompt_policy
  model_visible_context_refs
  context_builder_policy
```

要求：

- `raw_prompt` 或 `initial_messages` 必须和 verl tokenizer 生成的 `prompt_ids` 可追溯对应。
- 如果使用已有 `ContextBuilder` 构造初始上下文，必须记录 context policy 和可见 artifact reference。
- hidden verifier 细节不能进入 `initial_context`。
- 当前 verl postprocess 会把 `kwargs["raw_prompt"]` 写入最终 `AgentLoopOutput.extra_fields["raw_prompt"]`。因此 `raw_prompt` 必须只包含模型可见 prompt，不能夹带 hidden verifier、reward metadata、gold patch 或 evaluator-only 事实；如果后续导出或日志不希望携带明文 prompt，必须在导出边界转为 hash 或 artifact reference。

### 3.4 agent_policy

`agent_policy` 固定这一条 episode 的 agent 语义，防止不同开发阶段各自使用不同默认 scaffold、工具集合或上下文策略。

```text
agent_policy:
  scaffold_id
  scaffold_version
  prompt_template_version
  context_policy_version
  tool_policy_ref
  allowed_tools_ref
  permission_policy_ref
  feedback_policy
  test_feedback_policy
  hidden_feedback_visible_to_model
  max_test_runs
```

要求：

- `scaffold_id` 和 `scaffold_version` 决定 agent loop 的基本行动协议。
- `tool_policy_ref` 和 `allowed_tools_ref` 必须能反查实际可用工具集合，不能让 adapter 阶段和 training_fast 阶段各自推断工具默认值。
- `context_policy_version` 和 `prompt_template_version` 必须能解释初始 prompt、上下文压缩和 provider request projection 的构造方式。
- `feedback_policy`、`test_feedback_policy`、`hidden_feedback_visible_to_model` 和 `max_test_runs` 决定中间反馈是否可见，必须显式写入，不能靠实现默认值。

### 3.5 run_mode

第一版建议只定义三个值：

```text
run_mode:
  full_audit
  training_fast
  training_debug
```

语义：

- `full_audit`：完整评测审计模式，保留最大量 artifact，用于复核、展示、debug 和 acceptance。
- `training_fast`：在线训练默认模式，减少 raw provider artifact 和超大 prepared messages 写入，但必须保留关键 hash、reward、patch、timing 和 audit reference。
- `training_debug`：训练调试模式，比 `training_fast` 多保留部分 model call 和 context artifact，用于定位 token、mask、reward、工具调用问题。

重要不变量：

```text
run_mode 只能改变记录粒度、预算和执行策略。
run_mode 不能改变任务语义。
run_mode 不能让 hidden verifier 或 reward metadata 进入模型可见上下文。
```

### 3.6 budgets

```text
budgets:
  max_turns
  max_wall_seconds
  max_model_calls
  max_model_call_seconds
  request_timeout_seconds
  max_output_tokens
  max_prompt_tokens
  max_total_tokens
  max_context_tokens
  max_tool_observation_tokens
  max_tool_calls
  max_verifier_seconds
  max_workspace_materialization_seconds
  provider_retry_budget
  reasoning_effort
  thinking_mode
  max_artifact_bytes
  no_progress_policy
```

训练模式建议默认更紧：

- `max_turns` 可以先从 12 到 20 开始。
- `request_timeout_seconds` 应低于 full-audit evaluation 模式。
- `reasoning_effort` 或 `thinking_mode` 应能显式区分评测审计模式和训练 rollout 模式，训练模式不应默认开启高成本明文 thinking。
- `no_progress_policy` 应允许把长时间只读探索提前终止，并产生明确的 `status=no_progress`、diagnostics 和 reward 策略。是否把这类 episode 作为 negative sample 进入训练，由 policy 决定，contract 不默认替用户选择。

### 3.7 workspace_policy

```text
workspace_policy:
  execution_mode
  workspace_backend
  snapshot_key
  dependency_state_ref
  copy_on_write
  cleanup_policy
  docker_resource_limits
```

要求：

- 每条 episode 必须使用隔离 workspace。
- 并发 episode 不能共享可写工作区。
- 如果使用 snapshot 或 Docker volume 复用，必须保证从 clean state 派生，不能把上一次 rollout 的文件改动、测试产物或环境残留泄漏给下一条 episode。

### 3.8 recorder_policy

```text
recorder_policy:
  mode
  save_raw_provider_request
  save_raw_provider_response
  save_reasoning_trace
  save_prepared_messages
  prepared_messages_retention
  artifact_compression
  artifact_sampling_policy
```

建议：

- `full_audit` 默认保留完整审计证据。
- `training_fast` 默认关闭明文 reasoning trace，减少 raw provider response 和超大 prepared messages 落盘。
- 即使是 `training_fast`，也必须保留 `model_input_hash`、`provider_request_projection_hash`、patch hash、reward metadata reference 和 trajectory reference。

### 3.9 verifier_policy

```text
verifier_policy:
  final_verifier_mode
  baseline_policy
  final_reward_policy
  execution_strategy
  verifier_timeout_seconds
```

第一版 `execution_strategy` 建议只允许：

```text
blocking_in_episode
worker_pool_blocking
```

含义：

- `blocking_in_episode`：当前 episode 内同步执行 verifier。
- `worker_pool_blocking`：提交给 verifier worker pool 并等待结果返回。

第一版不建议使用：

```text
async_reward_backfill
```

原因是普通 `RepoHarnessVerlAgentLoop.run(...)` 返回给 verl 时通常需要 reward。真正的 reward backfill 应该放到 fully async 阶段，与 MessageQueue、sample staleness、partial rollout 和 off-policy 风险一起设计。

## 4. RepoHarnessEpisodeResult

`RepoHarnessEpisodeResult` 描述“一条 episode 的结果如何被训练器和审计系统消费”。

```text
RepoHarnessEpisodeResult
  schema_version
  contract_version
  episode_id
  run_id
  status
  status_reason
  training_view
  audit_ref
  reward
  verifier_summary
  patch_summary
  timing_summary
  resource_summary
  budget_consumption
  generation_records
  diagnostics
  retryable
  error_summary
```

### 4.1 status

第一版建议状态集合：

```text
status:
  succeeded
  failed
  timeout
  no_progress
  invalid_task
  infrastructure_error
  cancelled
```

说明：

- `succeeded` 表示 episode 完整结束，不一定表示任务成功，只表示轨迹和 reward 可以被消费。
- `failed` 表示模型完成了 episode，但 final verifier 或任务结果失败。
- `timeout` 表示超过 wall clock、模型调用或工具执行预算。
- `no_progress` 表示触发训练模式的 no-progress 策略。
- `invalid_task` 表示任务或环境本身不适合训练。
- `infrastructure_error` 表示 Docker、文件系统、provider、Ray worker 等基础设施失败。
- `cancelled` 预留给后续 fully async / partial rollout。

### 4.2 reward

```text
reward:
  score
  reward_version
  invalid_for_training
  invalid_reason
  reward_metadata_ref
  source
```

约束：

- `score` 第一版对应 RepoHarness `RewardMetadata.final_reward`。
- `invalid_for_training=true` 的样本可以保留 audit，但不应直接进入有效 RL batch。
- reward 的完整解释保存在 `reward_metadata_ref`，不要把隐藏细节塞进 `training_view`。
- `training_fast` 不能绕过 final verifier。当前 RepoHarness 的 reward、metrics 和 run outcome 都以 final verifier 为权威来源；训练模式可以减少记录体积，但不能把中间 feedback test 或诊断性工具输出直接当成最终 accepted reward。

### 4.3 verifier_summary

```text
verifier_summary:
  final_verifier_status
  accepted
  timeout
  error_type
  parser_confidence
  fail_to_pass
  pass_to_pass
  final_verifier_ref
```

`verifier_summary` 是训练和筛选需要的紧凑信息。完整 stdout、stderr、test cases 和 evaluator-only 证据必须留在 audit artifacts。

对于 pre-verl final-only 软件工程任务，还要继承现有硬约束：

```text
test_feedback_policy:
  disabled

max_test_runs:
  0
```

这类任务的 final verifier 是正式 reward 边界，不应在 rollout 过程中向模型暴露隐藏 fail-to-pass / pass-to-pass 结果。

### 4.4 patch_summary

```text
patch_summary:
  has_patch
  changed_files
  added_lines
  removed_lines
  diff_sha256
  patch_ref
```

用途：

- 支持 no-progress 判断。
- 支持 reward 中的 patch size penalty。
- 支持训练样本筛选和人工复查。

### 4.5 diagnostics

```text
diagnostics:
  failure_category
  failure_type
  blocks_training
  no_progress
  repeated_tool_call_loop
  context_limit_failure
  provider_transient
  environment_failure_category
  hidden_details_ref
```

约束：

- `hidden_details_ref` 可以指向 evaluator-only artifact。
- 任何 hidden details 都不能进入模型可见上下文。

## 5. 各阶段对本 contract 的使用方式

Harness runtime 和 training_fast 阶段负责：

```text
RepoHarnessEpisodeRequest
  -> runtime facade
  -> faster workspace / recorder / verifier / timing
  -> RepoHarnessEpisodeResult
```

verl adapter 阶段负责：

```text
verl non-tensor sample
  -> RepoHarnessEpisodeRequest
  -> RepoHarnessRuntime.run_episode(...)
  -> RepoHarnessEpisodeResult
  -> AgentLoopOutput
```

所有阶段都不能绕过 `RepoHarnessEpisodeResult.training_view` 和 `audit_ref` 自己拼训练字段。

## 6. Runtime facade 与现有入口关系

第一版实现时，`RepoHarnessRuntime.run_episode(...)` 最自然的底座是 `src/repo_harness/evaluation/runner.py::run_task(...)` 的主链路，因为它已经串起：

```text
load config
load task
create RunRecorder
create workspace
baseline verifier
resolved verifier plan
initial messages
AgentLoop.run(...)
final patch capture
final verifier
reward metadata
metrics
run outcome
run metadata
finalize run
```

但 shared contract 要求把这条链路抽成可组合 runtime facade，而不是让 verl adapter 长期直接调用 CLI 级 `run_task(...)`。原因是 `run_task(...)` 绑定命令行配置、输出目录、provider config、baseline 策略和一次性运行语义；在 Ray worker 或 fully async 环境中，需要更明确的 request / result schema、并发隔离和可控资源策略。

`AgentLoop.run(...)` 也不能单独替代完整 episode facade，因为它不负责 task loading、workspace lifecycle、baseline gate、final verifier、reward、export audit 和 run metadata。

## 7. 第一版不变量

1. `run_id` 和 `episode_id` 必须足够唯一，不能让并发 episode 写同一个 run directory。
2. final verifier 完整结果不能进入同一条 rollout 的模型可见上下文。
3. hidden tests、gold patch、reward metadata 和 accepted / failed 标签不能进入 verl dataset non-tensor fields。
4. 第一版 `RepoHarnessVerlAgentLoop.run(...)` 返回前必须已经有 reward score 或明确的 invalid / infrastructure error 状态。
5. `training_fast` 可以减少 artifact，但不能删除 audit reference、关键 hash、reward metadata reference 和 timing summary。
6. episode status 不能把基础设施错误当作模型失败直接训练，必须通过 `invalid_for_training` 或 diagnostics 阻断。
7. `AgentLoop.run(...)` 只能作为 episode runtime 内部子步骤，不能替代完整 episode facade。
8. `agent_policy` 必须显式固定 scaffold、工具、权限、上下文和反馈策略，不能由不同阶段各自使用隐式默认值。
