# Stage 11.5 执行计划：真实 RepoHarness episode runtime bridge

状态：待实施。本文件是 Stage 11.5 的执行计划，用于把已经完成的 adapter、schema、recorder、workspace、verifier、reward、budget 和资源租约能力接进真实 `RepoHarnessRuntime.run_episode(...)` 路径。Stage 11.5 是 Stage 12 真实端到端 smoke 的前置阶段。

前置状态：

- Stage 0H 到 Stage 10 已完成并提交。
- Stage 11 已完成 `RepoHarnessVerlAgentLoop`、`VerlLLMGateway`、verl kwargs request mapping、adapter visibility 和 fake `LLMServerClient` smoke，提交为 `0a1f4946 feat: add stage11 verl adapter bridge`。
- 当前 `RepoHarnessRuntime.run_episode(...)` 已经是异步入口，但主体仍以 `minimal_gateway` 单轮 facade 为主；它能够验证 token、mask、log probability、reward boundary、timing、resource 和 visibility contract，但不能代表真实软件工程 episode 闭环。

## 1. 阶段目标

Stage 11.5 的目标是新增一条真实 runtime bridge，让 `RepoHarnessRuntime.run_episode(...)` 在 `runtime_execution_mode=real_episode` 时进入真实 RepoHarness episode 路径：

```text
RepoHarnessEpisodeRequest
  -> runtime-only resolver / options
  -> workspace snapshot / isolated writable lease
  -> RunRecorder
  -> ToolExecutor / ToolExecutionContext
  -> AgentLoop with LLMGatewayModelClientAdapter
  -> one or more LLMGateway.generate_turn(...) calls
  -> tool calls and tool observations
  -> final verifier
  -> reward boundary
  -> TrainingView assembled from per-turn token facts
  -> RepoHarnessEpisodeResult
```

完成后应该证明：

1. `runtime_execution_mode=real_episode` 可以在本地跑通至少一条极小仓库任务，并真实执行 workspace、工具、agent loop、final verifier、reward、artifact、timing 和 resource summary。
2. `runtime_execution_mode=minimal_gateway` 继续保留，用于 contract、adapter 和 DataProto 结构测试，但不能被文档、测试或报告描述成完整软件工程 episode 端到端验收。
3. 真实 agent loop 的模型调用必须通过 `LLMGatewayModelClientAdapter` 进入 `LLMGateway`，不能绕回旧 provider client。
4. `TrainingView` 不能从最终 transcript 重新分词伪造。assistant generation token 必须来自每轮 `LLMGatewayResponse` / `GenerationRecord`；工具 observation token 必须来自明确的 tool observation projection，并使用 `response_mask=0`、`response_logprobs=0.0`。
5. final verifier 和 reward boundary 必须使用真实 `VerifierResult`，不能用 `minimal_final_verifier_status` 伪装真实 reward。

## 2. 非目标和边界

Stage 11.5 不做下面这些事情：

1. 不启动真实 Ray、SGLang、vLLM、SGLang server manager、vLLM server manager 或 PPO / GRPO trainer。
2. 不实现 `VerlLLMGateway` 的真实 GPU 推理验收。真实模型和真实 `LLMServerClient.generate(...)` 链路留到 Stage 12-B。
3. 不实现小 batch trainer loss smoke。`calculate_log_probs=True`、trainer loss 输入形状和 invalid 样本进入 trainer 前的策略留到 Stage 12-C。
4. 不新增模型可见 context refs。`repo_harness_model_visible_context_refs` 第一版仍然拒绝；如果后续需要启用，必须先补 schema 投影、visibility 测试和 request mapping 测试。
5. 不把本地绝对路径写入 `RepoHarnessEpisodeRequest`、`TrainingView.extra_fields`、未来 `AgentLoopOutput.extra_fields` 或任何可进入训练 batch 的字段。
6. 不把 fake/mock route 样本标记为 formal online RL 可训练样本。Stage 11.5 本地 fake/mock gateway 只用于真实 runtime debug smoke；formal converter 验收仍必须走 Stage 12-A 的 `RepoHarnessVerlAgentLoop + fake LLMServerClient` route=`verl` 路径。

## 3. 当前实现基础

Stage 11.5 应复用已有能力，而不是重写一套新 harness：

- `RepoHarnessRuntimeOptions` 已经是 runtime-only 配置容器，可以承载本地路径、callable、executor、cleanup callback、verifier pool 和 resource lease manager。
- `RepoHarnessRuntimeOptions.execution_mode` 当前已经存在，但命名仍偏泛化。Stage 11.5 应把语义固定为 `runtime_execution_mode` 或 `episode_runtime_mode`，并提供清楚的兼容路径，避免和 `RepoHarnessEpisodeRequest.run_mode` 混淆。
- `LLMGatewayModelClientAdapter` 已经能把旧 `ModelRequestContext` 转成 `LLMGatewayRequest`，并把 `LLMGatewayResponse` 转回旧 `ModelResponse`。真实 agent loop bridge 应使用它，而不是让 agent loop 直接调用旧 provider。
- Stage 6 已经有 `WorkspaceSnapshotManager`、snapshot facts、workspace lease、cleanup status、symlink 边界和 dependency copy 安全规则。
- Stage 7 已经有 `VerifierWorkerPool` 和 reward boundary helper。
- Stage 8 已经有 training budget、no-progress hard stop 和上下文瘦身策略。
- Stage 9 已经有 resource lease manager、gateway route limiter、run directory single-writer 和 cleanup diagnostics。

## 4. 建议新增或扩展的模块

优先保持改动集中在 `src/repo_harness/rl/`，必要时调用现有 `repo_harness.agent_loop`、`repo_harness.tools`、`repo_harness.workspace`、`repo_harness.verifier` 和 `repo_harness.trajectory`。

建议新增或扩展：

```text
src/repo_harness/rl/runtime.py
  RuntimeExecutionMode 或等价 Literal
  RepoHarnessRuntimeOptions.runtime_execution_mode
  real_episode 分发入口
  RealEpisodeRuntimeDependencies 或等价 runtime-only resolver

src/repo_harness/rl/real_episode.py
  可选。若 runtime.py 过大，可把真实 episode bridge 拆到这里。
  构造 workspace、recorder、agent loop、verifier、reward、training view assembly。

src/repo_harness/rl/training_view_builder.py
  可选。若 token provenance 逻辑复杂，可单独放置。
  从 per-turn GenerationRecord 和 tool observation projection 构造 TrainingView。

src/repo_harness/rl/generation_record_collector.py
  可选。若 collector 逻辑不适合放在 runtime.py，可单独放置。
  在 LLMGatewayResponse 转成旧 ModelResponse 之前保存每轮 runtime-only token facts。
```

测试建议新增：

```text
tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py
tests/unit/test_repo_harness_rl_stage11_5_training_view_provenance.py
tests/unit/test_repo_harness_rl_stage11_5_workspace_isolation.py
```

如果可以复用现有测试文件，也要保证测试名称中明确写出 Stage 11.5 覆盖点，方便后续阶段回归。

## 5. runtime execution mode 设计

Stage 11.5 应先固定 runtime-only execution mode：

```python
RuntimeExecutionMode = Literal["minimal_gateway", "real_episode"]
```

建议在 `RepoHarnessRuntimeOptions` 中增加清晰字段：

```python
runtime_execution_mode: RuntimeExecutionMode = "minimal_gateway"
```

兼容策略：

1. 如果保留旧字段 `execution_mode`，它只能作为兼容 alias，不能继续作为文档主名称。
2. `RepoHarnessEpisodeRequest.run_mode` 仍只表达 recorder / artifact profile，取值例如 `full_audit`、`training_fast`、`training_debug`。
3. `runtime_execution_mode` 不进入 request schema、不进入 `TrainingView.extra_fields`、不进入 `AgentLoopOutput.extra_fields`，除非以 `repo_harness_runtime_execution_mode` 这种 flat scalar diagnostic 字段进入离线审计字段；即使进入，也不能影响 formal online RL eligibility。

分发规则：

```text
runtime_execution_mode=minimal_gateway:
  保留现有 Stage 2 到 Stage 11 的最小路径。

runtime_execution_mode=real_episode:
  进入真实 workspace、agent loop、tool、verifier、reward 和 artifact 路径。

未知 runtime_execution_mode:
  返回结构化 RepoHarnessEpisodeResult：
    status=infrastructure_error
    status_reason=unsupported_runtime_execution_mode
    invalid_for_training=True
    invalid_for_online_rl=True
  并附带 audit diagnostic。不能让异常直接冒泡成非结构化 traceback。
```

## 6. runtime-only resolver 和本地路径边界

真实 episode 需要本地路径、任务定义、workspace source、run directory 和 verifier callable，但这些都不能塞进 `RepoHarnessEpisodeRequest`。

建议扩展 `RepoHarnessRuntimeOptions`，用 runtime-only resolver 承载本地信息：

```text
task_resolver:
  根据 request.task_id、task_ref、run_config_ref 找到任务定义和 source 信息。

workspace_resolver:
  根据任务定义构造 source checkout、snapshot key 和 dependency state。

run_dir_resolver:
  根据 request.run_id 和 output_dir 分配 run directory，并继续遵守 Stage 9 single-writer 规则。

agent_loop_factory:
  构造 AgentLoop、scaffold、allowed tools、context config、training budget policy。

verifier_factory:
  根据 task、workspace lease 和 runtime config 构造真实 final verifier callable。
```

要求：

1. `RepoHarnessEpisodeRequest.task_ref.task_path` 仍只允许相对路径或 opaque ref；绝对路径只能来自 runtime-only resolver。
2. resolver 返回的本地绝对路径只能用于本地执行和 artifact 写入，不能进入训练 batch 可传播字段。
3. resolver 失败时应返回 `invalid_task` 或 `infrastructure_error`，不能让异常逃逸成无结构 traceback。
4. 任务定义不合法、缺少 source、verifier 命令不合法时默认 `invalid_task`。
5. workspace materialization、snapshot cache、文件系统、Docker、recorder、run directory lock、dependency copy 失败默认 `infrastructure_error`。

## 7. workspace bridge

真实 episode 必须使用隔离 workspace：

```text
source task input
  -> source checkout / source facts
  -> WorkspaceSnapshotManager.get_or_create_snapshot(...)
  -> acquire_workspace(...)
  -> writable workspace lease
  -> tool execution and patch generation
  -> release_workspace(...)
```

实施要求：

1. 同一个 snapshot key 可以被多个 episode 复用，但每个 episode 必须拿到独立 writable lease。
2. agent 工具只能作用在当前 lease workspace，不能写 snapshot、cache root、run directory 或其他 episode workspace。
3. workspace release 必须走 Stage 6 已有 ownership check；重复 release 或 cleanup failure 必须进入 `ResourceSummary.cleanup_status` 和 diagnostics。
4. `ResourceSummary` 只能暴露 snapshot key、lease id、workspace opaque reference、cleanup status 和 cache hit 等可审计字段，不能暴露 `/Users/...`、临时 cache root 或 Docker host path。
5. Stage 11.5 至少要有一个测试覆盖两个 real episode 复用同一个 snapshot key 并发或连续运行，确认 patch、workspace 文件、artifact manifest 和 cleanup 不互相污染。

第一版可以用本地目录复制作为正确性基线，不要求 warm container pool、overlayfs 或 APFS clone 性能优化。

## 8. agent loop bridge

真实 episode 的 agent loop 必须走现有 `AgentLoop`，并用 `LLMGatewayModelClientAdapter` 注入 `LLMGateway`：

```text
LLMGateway
  -> LLMGatewayModelClientAdapter
  -> AgentLoop(model_client=adapter, tool_executor=ToolExecutor(...))
  -> AgentLoop.run(...)
```

实施要求：

1. 不允许 real episode 路径直接构造 OpenAI、DeepSeek、旧 replay provider 或旧 mock provider client 绕过 gateway。
2. `LLMGatewayModelClientAdapter.to_gateway_request(...)` 必须继续传递 recorder profile、request timeout、budget state、tool schema、context revision 和 tracing facts。
3. `AgentLoop.run(...)` 是同步函数。Stage 11.5 如果在 async `run_episode(...)` 中调用它，必须使用受控 executor，不能阻塞 event loop，也不能创建无界线程。
4. executor 取消语义必须按 Stage 2 和 Stage 9 的边界写清楚：外层 coroutine 被取消时，不能承诺强杀已经运行中的同步代码，但必须保证资源 lease、run directory lock、cleanup diagnostics 和 episode result 状态可控。
5. hard stop、timeout、no-progress、context limit、max model calls 和 provider retry 的预算消耗必须继续由 Stage 8 逻辑记录，不能因为 real episode bridge 接入而退回静态估算。

第一版可以先实现一个受控的本地 fake gateway real episode smoke：fake gateway 返回一个会触发工具调用的 assistant message，工具执行后下一轮返回最终 patch 或最终回答。重点是证明多轮和工具 observation 进入真实 agent loop，而不是证明模型能力。

### 8.1 generation record collector

真实 agent loop 仍然使用旧 `ModelResponse` 协议，而 `LLMGatewayModelClientAdapter.to_model_response(...)` 会把 `LLMGatewayResponse` 转成旧 `ModelResponse`。旧 `ModelResponse` 当前不携带正式训练所需的 `output_token_ids`、`output_logprobs`、`route`、`inference_backend`、`policy_version` 等完整 token facts。因此 Stage 11.5 必须新增 runtime-only generation record collector 或等价 callback，不能只依赖转换后的 `ModelResponse`。

采集要求：

1. `LLMGatewayModelClientAdapter` 或 real episode bridge 必须接收一个 runtime-only collector / callback。
2. 每轮 `LLMGatewayResponse` 在转换成旧 `ModelResponse` 之前，必须把下面事实写入 collector：
   - `prompt_ids`
   - `output_token_ids`
   - `output_logprobs`
   - `response_mask`
   - `route`
   - `inference_backend`
   - `provider_request_id`
   - `model_call_id`
   - `turn`
   - `context_revision`
   - `policy_version`
   - `global_steps` / `min_global_steps` / `max_global_steps`
3. collector 是 runtime-only 对象，不能进入 `RepoHarnessEpisodeRequest`，不能进入模型可见 message metadata，也不能把完整明细塞进 `TrainingView.extra_fields` 或未来 `AgentLoopOutput.extra_fields`。
4. collector 中的 facts 应用于构造 `GenerationRecord` 和 `TrainingView.response_spans`。如果 collector 缺少某轮 assistant generation 的 token facts，结果必须默认 `invalid_for_online_rl=True`，不能从 assistant text 重新分词补洞。
5. 测试必须证明多轮 real episode 的 `TrainingView.response_ids` 和 `TrainingView.response_logprobs` 来自 collector 中保存的 `LLMGatewayResponse` facts，而不是来自最终 transcript 或 assistant message content retokenization。

## 9. RunRecorder 和 artifact bridge

真实 episode 必须使用真实 `RunRecorder`：

1. `request.run_mode=full_audit` 时保留完整审计产物。
2. `request.run_mode=training_fast` 时继续使用 Stage 3 的 artifact retention facts，不能把 raw provider request / response 明文落盘。
3. `request.run_mode=training_debug` 时 preview 只能来自已脱敏 payload。
4. transcript、events、artifact manifest、patch、tool output、verifier result、reward metadata、timing summary 和 resource summary 必须能通过 `AuditRef` 或 opaque refs 回查。
5. `AuditRef` 内部可以结构化，但未来 batch 传播仍只能使用 flat `repo_harness_*` opaque refs。

验收时至少比较一条相同任务在 `full_audit` 与 `training_fast` 下的 artifact manifest，确认 `training_fast` 仍有可审计 facts，并且 artifact bytes 比 `full_audit` 至少下降 50%。如果极小真实 episode 因为任务过小、raw provider payload 太短或固定 metadata 占比太高而无法稳定达到 50%，必须在 diagnostics 和执行报告中记录原因，不能只用主观的“明显少于”作为验收标准。

## 10. verifier 和 reward bridge

Stage 11.5 不能再使用 `minimal_final_verifier_status` 作为真实 reward 依据。真实路径必须：

```text
task verifier spec
  -> runtime-only verifier callable
  -> VerifierWorkerPool 或受控 direct path
  -> VerifierResult
  -> build_stage7_reward_boundary(...)
  -> reward summary / verifier summary / invalid flags
```

状态映射要求：

1. final verifier accepted -> `status=succeeded`。
2. final verifier rejected -> `status=failed`。
3. verifier command 不合法、任务定义不合法、baseline invalid -> `status=invalid_task`，默认不可训练。
4. workspace、Docker、dependency、recorder、verifier pool、文件系统错误 -> `status=infrastructure_error`，默认不可训练。
5. verifier timeout、provider timeout、agent loop timeout -> `status=timeout`，默认不可训练。
6. no-progress hard stop -> `status=no_progress`，默认不可训练，除非后续显式 reward policy 改写。

测试必须覆盖 accepted、rejected、invalid_task、infrastructure_error 和 timeout 至少五类结果中的核心分支。

## 11. TrainingView token provenance bridge

这是 Stage 11.5 最容易出错的部分，必须单独实现和测试。

禁止做法：

```text
final transcript text
  -> tokenizer.encode(...)
  -> response_ids
```

正确做法：

```text
每轮 LLMGatewayResponse
  -> GenerationRecord
  -> assistant_generation span, response_mask=1, response_logprobs=真实或 fake gateway 提供值

每条 tool observation
  -> tool observation projection
  -> tool_observation span, response_mask=0, response_logprobs=0.0

所有 span 按 agent loop 时间顺序拼接
  -> TrainingView.response_ids
  -> TrainingView.response_mask
  -> TrainingView.response_logprobs
  -> TrainingView.response_spans
```

要求：

1. assistant generation token 必须来自 `LLMGatewayResponse.output_token_ids`，不能从 assistant message content 重新分词。
2. 如果 `LLMGatewayResponse.output_logprobs is None`，该 episode 默认 `invalid_for_online_rl=True`，不能进入 formal online RL。
3. tool observation token projection 必须有明确来源。第一版可以使用 fake/mock gateway 提供的测试 tokenizer 或 runtime-only projector，但必须在 `response_spans` 中记录 `source_type=tool_observation`、`response_mask_value=0` 和 `logprob_policy=tool_observation_zero_logprob`。
4. 如果 real episode 无法为 tool observation 生成 token projection，应返回 diagnostic-only result 或标记 `invalid_for_online_rl=True`，不能静默丢失 tool observation。
5. `TrainingView.extra_fields.repo_harness_llm_gateway_route` 必须和所有 `generation_records[*].gateway_route` 一致。
6. route 非 `verl` 的 real episode 可以用于 debug smoke，但 formal converter 必须拒绝。
7. assistant generation token facts 必须来自 generation record collector。collector 缺失、collector 记录和 `LLMGatewayResponse` 不一致、或者实现尝试使用 assistant text retokenization，都必须在测试中被捕获。

## 12. timing、resource 和 budget bridge

真实 episode result 的摘要必须来自真实分项，而不是静态占位值。

TimingSummary 至少要解释：

```text
rollout_wall_seconds
agent_loop_seconds 或 agent_loop_overhead_seconds
model_call_seconds
tool_seconds
workspace_seconds
final_verifier_seconds
reward_compute_seconds
artifact_write_seconds
cleanup_seconds
queue_wait_seconds
timing_unattributed_seconds
```

要求：

1. 用于计算 `timing_explained_ratio` 的分桶不能双重计数。如果 `agent_loop_seconds` 包含模型和工具时间，应把它定义为 residual overhead，或者单独说明不参与 explained ratio 加总。
2. `BudgetConsumption.used_wall_seconds` 必须和 `TimingSummary.rollout_wall_seconds` 对齐。
3. `BudgetConsumption.used_model_call_seconds` 必须和实测 `TimingSummary.model_call_seconds` 对齐。
4. `BudgetConsumption.used_model_calls` 必须统计主模型调用和 provider retry 后补计的模型调用事实。
5. `BudgetConsumption.used_tool_calls` 必须来自真实 tool execution count。
6. cleanup 被取消或失败时，资源释放仍必须进入受保护路径，并写入 diagnostics。

## 13. visibility 和安全边界

Stage 11.5 必须继续沿用 Stage 0H 到 Stage 11 已经固定的可见性规则：

1. `raw_prompt` 只能包含模型可见内容。
2. hidden verifier、gold patch、accepted label、完整 reward metadata、provider secret、evaluator-only logs 不能进入 request、tool observation、TrainingView、AgentLoopOutput、TransferQueue 或 DataProto。
3. 工具不能读取 run directory、reward metadata、final verifier artifact、gold patch、hidden verifier、acceptance bundle 或本地绝对路径。
4. `ResourceSummary`、`AuditRef` projection、artifact refs 和 run refs 必须使用 opaque refs；不能暴露本地绝对路径。
5. `LLMGatewayResponse.extra_fields` 与未来 `AgentLoopOutput.extra_fields` 仍是不同边界。gateway 侧可以保留 provider / rollout 诊断信息，但 batch 传播字段只能是 flat `repo_harness_*` scalar 或 opaque refs。

测试建议模拟模型尝试通过工具读取敏感路径，并断言被拒绝。

## 14. 建议测试计划

新增 Stage 11.5 测试应至少覆盖：

1. `runtime_execution_mode=minimal_gateway` 继续走现有最小路径，旧 Stage 2 到 Stage 11 目标测试不回退。
2. `runtime_execution_mode=real_episode` 用 fake/mock gateway 跑通极小仓库任务，真实执行 workspace、工具、verifier、reward 和 recorder。
3. real episode 中模型必须通过 `LLMGatewayModelClientAdapter` 调用 gateway；测试可用 spy gateway 断言收到 `LLMGatewayRequest`，并检查 recorder profile、tool schema、budget state 和 tracing facts。
4. 多轮工具调用能够生成 `response_spans`：至少包含 assistant generation span、tool observation span 和后续 assistant generation span。
5. tool observation span 的 `response_mask=0`，对应 log probability 全部为 `0.0`。
6. final verifier accepted 产生 `status=succeeded` 和 `reward_score`；final verifier rejected 产生 `status=failed` 和失败 reward。episode 成功状态和正式在线强化学习可训练资格必须分开判断：如果 route 不是 `verl`，即使 verifier accepted，也仍然必须 `invalid_for_online_rl=True`，不能进入 formal online RL batch。
7. verifier command invalid 或 task invalid 产生 `status=invalid_task`，默认不可训练。
8. workspace / dependency / recorder / verifier pool 错误产生 `status=infrastructure_error`，默认不可训练。
9. timeout 和 cancellation 能释放 workspace lease、run directory lock、route slot 和 episode slot。
10. 两个 real episode 复用同一个 snapshot key 时，workspace patch、artifact manifest、cleanup status 和 run directory 不互相污染。
11. `training_fast` real episode 不保存 raw provider payload，只保存 retention facts。
12. real episode result 的 `TimingSummary` 和 `BudgetConsumption` 对齐。
13. real episode result 的 `ResourceSummary` 不泄漏本地绝对路径。
14. route 非 `verl` 的 fake/mock real episode 保持 diagnostic-only，不被 formal online RL batch validator 接受。
15. real episode 中任意一轮 gateway 缺失 `output_logprobs` 时，结果必须 `invalid_for_online_rl=True`，并且 formal batch validator 必须拒绝该样本。
16. generation record collector 保存的 per-turn token facts 是 `TrainingView.response_ids` 和 `TrainingView.response_logprobs` 的来源；测试应使用与 assistant message content 不一致的 token ids，确认实现没有从文本重新分词。

建议测试文件：

```text
tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py
```

如果后续 Stage 12 前需要拆分更大的集成测试，可以再把 provenance、visibility 和 resource 用例从该合并测试文件中拆出；Stage 11.5 第一版以实际存在的合并测试文件作为验收入口。

## 15. 验收命令

Stage 11.5 实施完成后建议至少运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage11_agent_loop.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage11_request_mapping.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py \
  tests/unit/test_workspace_reuse_stage6.py \
  tests/unit/test_repo_harness_rl_stage7_reward_boundary.py \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_contract_fixtures.py \
  tests/unit/test_repo_harness_verl_stage0h_shape_rules.py \
  tests/unit/test_repo_harness_verl_stage0h_visibility.py \
  tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py \
  tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py \
  tests/unit/test_repo_harness_rl_stage2_runtime.py \
  tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py \
  tests/unit/test_repo_harness_rl_stage4_timing_resource.py \
  tests/unit/test_repo_harness_rl_stage5_gateway_routes.py \
  tests/unit/test_repo_harness_rl_stage5_provider_gateway.py

PYTHONPATH=src uv run --extra dev python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY

if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  src/repo_harness/workspace \
  src/repo_harness/verifier; then
  exit 1
fi
```

`src/repo_harness_verl` 可以 import verl，因为它是可选 adapter 包；`src/repo_harness/rl`、agent loop core、workspace core 和 verifier core 不能 import verl。

## 16. 阶段完成定义

Stage 11.5 完成时，应能清晰回答下面问题：

1. `minimal_gateway` 和 `real_episode` 的语义是否已经在 runtime-only options 中固定，并且没有污染 request schema？
2. real episode 是否真实执行了 workspace、工具、agent loop、verifier、reward 和 recorder？
3. real episode 的所有模型调用是否都经过 `LLMGateway`？
4. `TrainingView` 是否由 per-turn token facts 和 tool observation projection 拼接，而不是从最终 transcript 重新分词？
5. `TimingSummary`、`ResourceSummary` 和 `BudgetConsumption` 是否能解释真实 episode 的主要耗时和资源事实？
6. invalid、timeout、no-progress、infrastructure error 和缺失 log probability 样本是否默认不会进入 formal online RL？
7. fake/mock route 是否只被用于 debug/runtime smoke，而不是 formal online RL converter 验收？
8. Stage 12-A 是否已经有足够基础去接 `RepoHarnessVerlAgentLoop + fake LLMServerClient + real_episode` 路径？

只有这些问题都有测试或审计证据支撑后，才建议进入 Stage 12 的分层 smoke。
