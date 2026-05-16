# Stage 8 执行计划：训练预算、no-progress 控制和上下文瘦身

状态：待实施。本文件只定义 Stage 8 的执行计划，还没有开始代码实现。
前置状态：Stage 0H、Stage 1、Stage 2、Stage 3、Stage 4、Stage 5、Stage 6、Stage 7 已完成。Stage 7 已在提交 `0ae4e37c` 中完成 verifier worker pool、同步 reward boundary、verifier queue wait / worker id 追踪、基础设施错误不可训练边界和相关测试。

## 1. 阶段目标

Stage 8 的目标是减少在线强化学习 rollout 中的无效长轨迹和过大上下文成本，让训练模式下的 episode 可以更早、更清楚、更可审计地停止。

本阶段要解决的问题是：

```text
agent loop 持续重复搜索、反复读取大文件、没有补丁进展、工具输出过大
  -> prompt 越来越大
  -> 模型调用更慢
  -> verifier 和 reward 之前浪费大量非模型时间
  -> 无进展样本如果没有明确 invalid 边界，可能误训模型
```

Stage 8 第一版要形成下面的训练预算闭环：

```text
RepoHarnessEpisodeRequest.budgets
  -> TrainingBudgetPolicy / BudgetManager 映射
  -> agent loop / tool system / context manager 执行预算
  -> budget exhausted 或 no-progress hard stop
  -> RepoHarnessEpisodeResult.status / BudgetConsumption / diagnostics
  -> TrainingView 默认不可训练，除非后续显式 reward policy 允许
```

完成后应该能做到：

1. 训练模式可以使用比 full audit 更保守的轮次、模型调用、工具调用、工具输出、上下文和 verifier 预算。
2. no-progress 不只是 diagnostic warning，可以在训练模式下触发明确 hard stop。
3. no-progress stop 结果默认 `status=no_progress`，并且 `invalid_for_training=true`、`invalid_for_online_rl=true`。
4. 上下文和工具输出瘦身策略可配置、可审计、可回放。
5. `BudgetConsumption.stop_reason`、`audit_diagnostics`、`TimingSummary` 和 recorder events 能解释为什么提前停止。

## 2. 必须保持的边界

1. Stage 8 不做 Stage 9 的并发资源租约，不解决多 episode 全局调度。
2. Stage 8 不做 Stage 10 的 `TrainingView -> AgentLoopOutput` 转换，不接 DataProto。
3. Stage 8 不做 Stage 11 的 `RepoHarnessVerlAgentLoop` 或 `VerlLLMGateway`，不能引入 `verl` import。
4. Stage 8 不改变 final verifier 权威边界。提前 no-progress stop 后如果没有可信 final verifier 和 reward policy，不能伪装成普通模型失败样本。
5. Stage 8 不允许通过最终 transcript 重新分词来伪造训练 token，也不允许静默截断 response 后继续训练。
6. Stage 8 不允许把完整 no-progress hidden diagnostics、reward metadata、hidden verifier 细节或本地绝对路径放进模型可见 prompt、`raw_prompt`、`TrainingView.extra_fields` 或未来 batch 可传播字段。
7. Stage 8 不默认改变现有 CLI / SWE-Bench 路径的行为。训练预算 hard stop 应通过 `run_mode=training_fast`、显式 policy 或 runtime option 启用。
8. no-progress 作为 negative sample 进入训练必须等后续显式 reward policy；Stage 8 第一版默认全部过滤。

## 3. 第一版覆盖范围

必须覆盖：

- 训练预算 policy schema。
- `RepoHarnessEpisodeRequest.budgets` 到现有 `BudgetManager` / runtime budget 的稳定映射。
- no-progress hard stop 的原因枚举、状态映射和审计记录。
- 工具输出和上下文瘦身的第一版策略约束。
- `BudgetConsumption` 的实际消耗字段和 `stop_reason` 填充。
- no-progress、context too large、tool output too large、max turns、max model calls、max tool calls 的测试。
- visibility 检查，确保 no-progress diagnostics 和上下文瘦身 facts 不泄漏 evaluator-only 内容。

可以只做接口或最小实现：

- ranked snippets 的完整算法。第一版可以先做明确的 range read / grep context / max output caps。
- 复杂 patch progress heuristic。第一版可以复用现有 read-only streak、repeated input、empty search、near turn budget without patch 信号。
- provider-specific token estimator 完整准确性。第一版可以使用现有 projection estimate 和已有 context budget facts。
- 多 agent 或多 scaffold 的差异化预算调度。

如果实施时发现完整接入 `AgentLoop.run(...)` 风险较高，应采用两层策略：

1. 先新增训练预算和 no-progress policy helper，用单元测试覆盖 stop decision。
2. 再以可选参数把 hard stop 接入 agent loop 或 runtime facade，保持默认路径兼容。

## 4. 需要先阅读和确认的代码位置

实施前先只读检查：

```text
src/repo_harness/rl/episode.py
src/repo_harness/rl/runtime.py
src/repo_harness/budget/schemas.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/agent_loop/schemas.py
src/repo_harness/context/manager.py
src/repo_harness/context/schemas.py
src/repo_harness/context/budget.py
src/repo_harness/tools/minimal.py
src/repo_harness/tools/schemas.py
src/repo_harness/evaluation/runner.py
src/repo_harness/evaluation/schemas.py
src/repo_harness/trajectory/recorder.py
tests/unit/test_repo_harness_rl_stage7_reward_boundary.py
tests/unit/test_repo_harness_rl_stage4_timing_resource.py
tests/unit/test_reward.py
```

需要重点确认：

- `EpisodeBudgets` 已经有哪些字段：`max_turns`、`max_wall_seconds`、`max_model_calls`、`max_model_call_seconds`、`request_timeout_seconds`、`max_output_tokens`、`max_prompt_tokens`、`max_total_tokens`、`max_context_tokens`、`max_tool_observation_tokens`、`max_tool_calls`、`max_verifier_seconds`、`max_workspace_materialization_seconds`、`provider_retry_budget`、`max_artifact_bytes`、`no_progress_policy`。
- `BudgetManager` 当前有哪些字段：`max_turns`、`max_tool_calls`、`max_test_runs`、`task_timeout_sec`、`command_timeout_sec`、`verifier_timeout_sec`、`max_tool_output_chars`、`max_context_tokens`、`max_output_tokens`、`max_artifact_bytes`。
- `AgentLoop.run(...)` 当前如何调用 `_budget_stop_reason(...)`、`_record_budget_exhausted(...)`、`_build_loop_progress_summary(...)`。
- 当前 no-progress diagnostic 已有信号：`long_read_only_streak`、`repeated_tool_input`、`empty_search_accumulation`、`near_turn_budget_without_patch`、`near_turn_budget_with_patch`。
- `ContextManager.prepare_messages(...)` 当前如何做 tool result artifact、context reduction、tool result aggregate budget。
- `ToolExecutor` / `ToolExecutionContext` 当前如何限制工具输出大小和写 artifact。

## 5. 建议新增或调整的模块

建议新增：

```text
src/repo_harness/rl/budget.py
```

建议包含以下结构：

```text
TrainingBudgetPolicy
NoProgressPolicy
NoProgressDecision
BudgetStopDecision
TrainingBudgetProjection
build_training_budget_policy(...)
budget_manager_from_episode_budgets(...)
map_budget_stop_to_episode_status(...)
```

职责建议：

- `TrainingBudgetPolicy`：训练模式下的预算聚合策略，包含轮次、模型调用、工具调用、工具输出、上下文、verifier、workspace materialization、artifact bytes 和 no-progress hard stop 配置。
- `NoProgressPolicy`：控制 hard stop 是否启用、阈值、触发信号、是否允许模型可见 convergence nudge、是否允许进入训练。
- `NoProgressDecision`：根据 loop progress summary 生成结构化停止决策。
- `BudgetStopDecision`：统一表达 `max_turns`、`max_model_calls`、`max_tool_calls`、`context_too_large`、现有 `context_limit` 系列原因、`tool_output_budget_exceeded`、`no_progress`、`generation_timeout_loop` 等停止原因。
- `TrainingBudgetProjection`：把 `EpisodeBudgets` 映射到 `BudgetManager`、context config override、tool output limits 和 gateway request timeout。

如果实施需要接入 agent loop，可在 `src/repo_harness/agent_loop/loop.py` 中增加可选参数：

```text
training_budget_policy: TrainingBudgetPolicy | None = None
```

默认 `None` 时保持当前行为；启用时才使用 Stage 8 的 hard stop 策略。

## 6. 预算字段映射规则

Stage 8 必须明确 `EpisodeBudgets` 到运行时预算的映射，避免 CLI、runtime facade 和后续 verl adapter 各自猜默认值。

建议第一版映射：

| EpisodeBudgets 字段 | 运行时目标 | 缺失时默认 |
| --- | --- | --- |
| `max_turns` | `BudgetManager.max_turns` | full audit 保持现有配置；training_fast 使用保守默认，例如 12 |
| `max_wall_seconds` | episode 外层 timeout / `task_timeout_sec` | 不强行覆盖现有 CLI 默认 |
| `max_model_calls` | agent loop 所有模型调用上限 | 缺失时可等同 `max_turns` |
| `max_model_call_seconds` / `generation_timeout_seconds` | gateway request timeout | 使用更小的已配置值 |
| `max_output_tokens` | gateway sampling params 和 `BudgetManager.max_output_tokens` | full audit 保持配置；training_fast 更小 |
| `max_prompt_tokens` / `max_context_tokens` | context budget 和 preflight | 缺失时使用 provider context resolver |
| `max_tool_observation_tokens` | 进入训练序列的 tool observation cap | Stage 8 可以先记录 policy，不构造 Stage 10 mask |
| `max_tool_calls` | `BudgetManager.max_tool_calls` | full audit 保持配置；training_fast 更小 |
| `max_verifier_seconds` | Stage 7 verifier job timeout | 已由 Stage 7 支持，Stage 8 统一 policy |
| `max_workspace_materialization_seconds` | workspace materialization timeout | 第一版可只记录和诊断，不强行接 Stage 6 manager |
| `provider_retry_budget` | gateway / provider retry policy | 第一版必须可传递，不做复杂 retry scheduler |
| `max_artifact_bytes` | recorder / training_fast artifact budget | 继承 Stage 3 边界 |

缺失策略：

- Schema 字段可以保持可选，避免破坏 Stage 0H fixture。
- 训练模式 helper 必须输出“实际采用的默认值”和 policy version。
- 不能把本地绝对 path、hidden verifier、gold patch 或 reward metadata 写进预算 policy 的 batch 可传播字段。

### 6.1 `max_model_calls` 计数口径

Stage 8 必须先明确模型调用计数口径，再实现 `max_model_calls` hard stop。当前 `BudgetManager` 和 `BudgetState` 还没有 `max_model_calls` 或 `model_call_count` 字段，不能只在文档中声明预算而没有 result 层审计。

第一版建议：

1. 扩展 `BudgetManager`，新增 `max_model_calls: int | None`。
2. 扩展 `BudgetState`，新增 `model_call_count: int`。
3. 扩展 `BudgetConsumption`，新增 `max_model_calls` 和 `used_model_calls`，或者至少在 Stage 8 helper 中提供等价可审计字段。如果改 schema，必须保持 Stage 0H fixture 兼容，字段默认值应安全。
4. `model_call_count` 统计所有会调用模型 provider / gateway 的路径，包括：
   - 主 agent loop 模型调用。
   - proactive auto compact 调用。
   - reactive compact 调用。
   - provider retry 产生的额外模型请求。
   - 未来 scaffold repair 或 parser repair 如果调用模型，也必须计入。
5. 不统计纯工具调用、context prepare、本地 parser repair、verifier 和 reward compute。
6. 超限判断应发生在下一次模型调用提交之前，而不是等调用完成后才发现超限。这样可以避免超过预算的 provider request 已经被发送出去。
7. 如果当前模型调用已经开始，Stage 8 不要求强行中断；应让该调用按已有 timeout / cancellation 语义结束，然后记录已用模型调用数。
8. `max_model_calls` 触发时应使用明确 stop reason，例如 `max_model_calls_exceeded`，默认 `status=timeout` 或 `status=invalid` 需要按下面状态映射表固定，不得伪装成 no-progress。

测试必须覆盖：主模型调用计数、auto compact / reactive compact 计数、超限前停止、`BudgetConsumption.used_model_calls` 与 loop facts 一致。

## 7. no-progress hard stop 规则

Stage 8 第一版可以复用现有 loop progress summary，但要把 warning 升级为训练模式可选 hard stop。

建议 stop reason 枚举：

```text
no_progress_read_only_loop
no_progress_repeated_tool_input
no_progress_empty_search_loop
no_progress_no_patch_after_budget
no_progress_tool_error_loop
generation_timeout_loop
context_too_large
context_limit
context_limit_after_reactive_compact
context_limit_reactive_compact_disabled
auto_compact_failed_preflight
reactive_compact_failed
prompt_length_exceeded
response_length_exceeded
max_model_calls_exceeded
```

这些 stop reason 不能统一映射为 `status=no_progress`。Stage 8 必须固定 `stop_reason -> EpisodeResult.status -> training validity -> reward_score policy`，避免 timeout、context budget 和 no-progress 被混为同一类。

建议第一版映射：

| stop_reason | EpisodeResult.status | training validity | reward_score policy |
| --- | --- | --- | --- |
| `no_progress_read_only_loop` | `no_progress` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `no_progress_repeated_tool_input` | `no_progress` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `no_progress_empty_search_loop` | `no_progress` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `no_progress_no_patch_after_budget` | `no_progress` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `no_progress_tool_error_loop` | `no_progress` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `generation_timeout_loop` | `timeout` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `max_model_calls_exceeded` | `timeout` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `context_too_large` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `context_limit` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `context_limit_after_reactive_compact` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `context_limit_reactive_compact_disabled` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `auto_compact_failed_preflight` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `reactive_compact_failed` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `prompt_length_exceeded` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |
| `response_length_exceeded` | `invalid` | `invalid_for_training=true`、`invalid_for_online_rl=true` | `None` |

`BudgetConsumption.stop_reason` 必须等于具体 stop reason，不能只写泛化的 `no_progress`、`timeout` 或 `invalid`。

必须写入 audit diagnostics：

```text
AuditDiagnostic.code = stop reason
AuditDiagnostic.message = 可读解释
```

必须写入 recorder event。event 类型必须按照 stop reason 分类，不能把所有提前停止都记录成 no-progress：

```text
no_progress_*:
  event_type = "no_progress_hard_stop"

generation_timeout_loop:
  event_type = "generation_timeout"

max_model_calls_exceeded 或其他明确预算上限：
  event_type = "budget_hard_stop"
  如果现有路径已经使用 "budget_exhausted"，可以沿用该事件名，但 data.stop_reason 必须保留具体原因。

context_too_large、context_limit 系列、auto_compact_failed_preflight、reactive_compact_failed、prompt_length_exceeded、response_length_exceeded:
  event_type = "context_budget_hard_stop"

severity = "warning"
data.stop_reason = 具体 stop reason
data.policy_version
data.signals
data.thresholds
data.trainable = false
```

禁止：

- 只把 reward 置为 0 后继续作为可训练样本。
- 把 no-progress hidden diagnostic 全量写入模型可见消息。
- 把完整工具输出、文件内容或本地路径塞进 `TrainingView.extra_fields`。
- hard stop 已经触发的同一轮不能再注入新的 convergence nudge。nudge 只能发生在明确会继续进入下一轮模型调用之前；如果 policy 决定 hard stop，则必须直接停止并记录 event。

## 8. 上下文和工具输出瘦身规则

Stage 8 第一版应优先利用已有 tool 和 context 机制，避免一次性重写工具系统。

建议先覆盖：

1. `read_file` 默认范围读取或最大字符限制。
2. `grep` 默认短 context、最大匹配数和最大扫描文件数。
3. `read_tool_result_artifact` 分页读取，不允许一次性把超大 artifact 全量放回模型上下文。
4. 工具输出超过 `max_tool_output_chars` 时，返回摘要、hash、artifact ref 和截断原因。
5. context manager 对 tool result aggregate budget 的裁剪必须记录 facts。
6. context preflight 超过 hard limit 时，必须产生 `context_too_large` 或现有 `context_limit` 系列 stop reason，并默认不可训练；现有 `context_limit`、`context_limit_after_reactive_compact`、`context_limit_reactive_compact_disabled`、`auto_compact_failed_preflight`、`reactive_compact_failed` 都必须进入上方映射表，不能漏成可训练样本。

如果某个工具需要新增参数，优先用向后兼容方式：

```text
read_file:
  start_line
  max_lines
  max_bytes

grep:
  context_lines
  max_matches
  output_mode
```

不要改变工具的基础语义；只改变训练模式下的默认限制和输出投影。

## 9. reward 和 training view 边界

Stage 8 必须和 Stage 7 reward boundary 对齐。

默认规则：

- `no_progress` 不进入正式 online RL batch。
- `context_too_large` 不进入正式 online RL batch。
- `generation_timeout_loop` 不进入正式 online RL batch。
- `max_turns` 如果没有可信 final verifier 和 reward policy，默认不可训练。
- 只有 final verifier rejected 且 verifier 本身可信时，才可以作为模型失败样本。

`TrainingView.extra_fields` 允许的 Stage 8 字段示例：

```text
repo_harness_budget_policy_ref = "rh://budget/..."
repo_harness_stop_reason = "no_progress_read_only_loop"
repo_harness_no_progress_ref = "rh://diagnostics/..."
repo_harness_context_budget_ref = "rh://context-budget/..."
```

这些字段必须是 flat scalar 或 opaque refs。不能出现：

```text
repo_harness_no_progress_diagnostics = {...嵌套对象...}
repo_harness_context_full_messages = [...]
repo_harness_large_tool_output = "...完整输出..."
```

## 10. 与 runtime 和 agent loop 的接入策略

建议分三层实施：

1. `rl/budget.py`：纯 schema / helper，能根据 `EpisodeBudgets` 和 `run_mode` 生成训练预算策略。
2. `RepoHarnessRuntime` minimal path：支持 `max_model_calls`、`max_wall_seconds`、prompt / response overflow、gateway timeout、no-progress terminal result 的结构化返回。
3. `AgentLoop.run(...)` 可选接入：启用 training policy 时，把 no-progress summary 转为 hard stop，并把 `BudgetConsumption` / recorder event 写完整。

注意：Stage 8 不要求完整 CLI 默认路径马上启用 hard stop。执行报告必须说清楚覆盖的是 runtime facade、agent loop 可选策略，还是完整 CLI 路径。

## 11. 测试计划

建议新增测试：

```text
tests/unit/test_repo_harness_rl_stage8_budget_policy.py
tests/unit/test_agent_loop_stage8_no_progress_stop.py
tests/unit/test_context_stage8_training_slimming.py
```

必须覆盖：

1. `EpisodeBudgets` 可以映射为 `TrainingBudgetPolicy` 和 `BudgetManager`，缺失字段有可审计默认值。
2. `run_mode=training_fast` 使用训练默认预算，`full_audit` 不被强制变短。
3. `max_turns`、`max_model_calls`、`max_tool_calls` 触发结构化 stop reason。
4. `max_model_calls` 统计主模型调用、auto compact、reactive compact 和 retry 调用；超限发生在下一次模型调用提交之前。
5. no-progress read-only loop 触发 `status=no_progress`，默认不可训练。
6. repeated tool input 触发 no-progress hard stop，并写入 audit diagnostic。
7. empty search accumulation 触发 no-progress hard stop，并写入 recorder event。
8. hard stop 触发的同一轮不会再注入 convergence nudge；只有继续下一轮模型调用时才允许 nudge。
9. `generation_timeout_loop` 返回 `status=timeout`，不能映射成 no-progress。
10. context too large、现有 `context_limit` 系列、auto / reactive compact preflight 失败、prompt overflow、response overflow 返回 `status=invalid`，不能映射成 no-progress。
11. recorder event 类型要随 stop reason 变化：只有 `no_progress_*` 使用 `no_progress_hard_stop`，预算上限使用 `budget_hard_stop` 或现有 `budget_exhausted`，generation timeout 使用 `generation_timeout`，上下文预算类停止使用 `context_budget_hard_stop`，并且所有事件都必须写入 `data.stop_reason`。
12. tool output 超限时，模型可见内容是摘要 / hash / artifact ref，不是完整超大输出。
13. `TrainingView.extra_fields` 不含嵌套 no-progress diagnostics、不含本地绝对路径、不含完整工具输出。
14. `BudgetConsumption.used_turns`、`used_tool_calls`、`used_model_calls`、`used_model_call_seconds`、`stop_reason` 与 runtime / loop facts 一致。
15. Stage 7 verifier timeout 和 Stage 8 generation timeout 不会混淆。
16. `src/repo_harness/rl`、`src/repo_harness/agent_loop`、`src/repo_harness/context` 不引入 `verl`。

需要继续跑前置阶段回归：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py \
  tests/unit/test_agent_loop_stage8_no_progress_stop.py \
  tests/unit/test_context_stage8_training_slimming.py \
  tests/unit/test_verifier_worker_pool_stage7.py \
  tests/unit/test_repo_harness_rl_stage7_reward_boundary.py \
  tests/unit/test_repo_harness_rl_stage6_resource_summary.py \
  tests/unit/test_workspace_reuse_stage6.py \
  tests/unit/test_repo_harness_rl_stage5_gateway_routes.py \
  tests/unit/test_repo_harness_rl_stage4_timing_resource.py \
  tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py \
  tests/unit/test_repo_harness_rl_stage2_runtime.py \
  tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py \
  tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py \
  tests/unit/test_repo_harness_verl_contract_fixtures.py \
  tests/unit/test_repo_harness_verl_stage0h_shape_rules.py \
  tests/unit/test_repo_harness_verl_stage0h_visibility.py \
  tests/unit/test_reward.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_verifier_micro_repos.py
rg -n "(^|\\s)(import|from)\\s+verl" src/repo_harness/rl src/repo_harness/agent_loop src/repo_harness/context
```

如果 agent loop 或 context integration 测试受本地环境影响，执行报告必须明确说明，并至少保留 helper 级单元测试覆盖。

## 12. 验收标准

Stage 8 完成时必须满足：

1. 训练预算 policy 可以从 `EpisodeBudgets` 稳定生成，并记录 policy version 和默认值来源。
2. no-progress hard stop 可以触发、可审计、可过滤。
3. no-progress 默认不可训练，不能带普通 reward_score 进入 online RL batch。
4. `generation_timeout_loop`、`max_model_calls_exceeded`、`context_too_large`、现有 `context_limit` 系列、prompt / response overflow 不会被误映射为 no-progress。
5. `max_model_calls` 有明确计数口径，并能在结果层审计 `used_model_calls`。
6. hard stop 和 convergence nudge 的先后语义明确：停止优先，继续下一轮时才允许 nudge。
7. context too large 和 tool output too large 有明确 stop reason 或 slimming facts。
8. `BudgetConsumption.stop_reason` 与 episode status / diagnostics 对齐。
9. 工具输出和上下文瘦身不删除 audit ref；完整证据仍可通过 opaque refs 离线回查。
10. `TrainingView.extra_fields` 只包含 `repo_harness_*` flat scalar 和 opaque refs。
11. 现有 Stage 0H 到 Stage 7 的目标回归测试仍然通过。
12. 不引入 `verl` import，不实现 Stage 10 converter，不实现 Stage 11 adapter。

## 13. 明确不属于 Stage 8 的事项

下面这些事项必须留到后续阶段：

- Stage 9：两条 episode 并发运行时的 run directory、workspace、artifact manifest 和资源租约冲突测试。
- Stage 10：`TrainingView -> AgentLoopOutput` 转换、DataProto shape、TransferQueue visibility。
- Stage 11：`RepoHarnessVerlAgentLoop`、`VerlLLMGateway`、Hydra config 和 verl server client。
- Stage 12：端到端 verl smoke、性能 smoke、Vast.ai 真实推理服务验收。
- Stage 13：fully async reward backfill、中断恢复、policy staleness 和异步样本补偿。

如果 Stage 8 需要为后续阶段预留字段，只能做 schema 兼容，不要提前改变训练 batch 语义。
