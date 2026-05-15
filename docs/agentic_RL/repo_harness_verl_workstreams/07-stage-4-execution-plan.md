# Stage 4 执行计划：实现 TimingSummary 和 ResourceSummary

状态：已完成。当前完成范围覆盖 `RepoHarnessRuntime.run_episode(...)` runtime facade 和最小 run directory summarizer；完整 CLI / legacy runner / 多轮 AgentLoop 路径尚未在 Stage 4 中正式接入。
前置状态：Stage 0H、Stage 1、Stage 2、Stage 3 已完成。Stage 3 已经完成 `run_mode` 到 `RecorderProfile` 的正式映射，并为 runtime facade / recorder smoke 路径提供了最小 timing attribution。Stage 4 需要把 timing/resource 从“最小可用”推进到“可审计、可解释、可用于训练吞吐分析”。

## 1. 阶段目标

Stage 4 的目标是让每条 RepoHarness episode 都输出结构化 `TimingSummary` 和 `ResourceSummary`，并且能够回答下面的问题：

```text
这条 episode 慢在哪里？
是模型调用慢，还是 workspace / Docker / verifier / artifact 写入慢？
这条 episode 使用了什么 workspace、Docker、snapshot、dependency cache、权限和网络策略？
如果失败、timeout 或 infrastructure error，已经发生过的耗时和资源事实是否仍然可审计？
```

Stage 4 不是性能优化阶段，不实现 workspace/container 复用，不实现 verifier worker pool，也不实现 verl adapter。Stage 4 只做结构化记录、summary 汇总、artifact/ref 回指和验收测试，为后续 Stage 5 到 Stage 12 提供可靠观测面。

## 2. 必须保持的边界

1. `TimingSummary` 和 `ResourceSummary` 不能改变任务语义、reward 语义、verifier 权威边界或 `TrainingView` token 事实。
2. 本阶段不能把本地绝对路径写入 `TrainingView.extra_fields`、future `AgentLoopOutput.extra_fields` 或 batch 可传播字段。
3. `TrainingView.extra_fields` 只能新增短小、扁平、`repo_harness_*` 命名空间字段，例如 `repo_harness_timing_summary_ref` 和 `repo_harness_resource_summary_ref`。
4. 结构化 `AuditRef` 内部可以记录 summary 相关引用，但进入 batch 的只能是 opaque ref，不能嵌套完整 `audit_ref` 对象。
5. `ResourceSummary.workspace_path` 和 `ResourceSummary.run_dir` 如果存在，必须是相对路径、opaque ref 或可安全公开的短引用，不能是 `/Users/...` 这类本地绝对路径。
6. 模型 provider 上报的 `duration_ms` 可以作为 provider metadata 保留，但不能直接当成 outer wall time attribution。Stage 3 已经修复该问题，Stage 4 需要保持这个边界。
7. 每条 `TimingSummary` 必须解释至少 95% 的 `rollout_wall_seconds`。无法解释的部分必须进入 `timing_unattributed_seconds` 和 diagnostics。
8. `TimingSummary` 和 `BudgetConsumption` 必须使用同一套实测耗时账本。至少 runtime facade 路径中，`BudgetConsumption.used_wall_seconds` 要和 `TimingSummary.rollout_wall_seconds` 对齐，`BudgetConsumption.used_model_call_seconds` 要和实测 `TimingSummary.model_call_seconds` 对齐。
9. 用于解释率计算的 timing 字段必须是互斥分桶，不能把包含关系的字段重复相加。`agent_loop_seconds` 如果参与 explained sum，应表示扣除 model、tool、context prepare 等子阶段后的 residual agent loop overhead。
10. 本阶段不能引入 `verl` import，不能实现 `RepoHarnessVerlAgentLoop`、`VerlLLMGateway`、`AgentLoopOutput` 转换器或 Ray/vLLM/SGLang 调度。

## 3. 第一版覆盖范围

Stage 4 的总目标是“每条 episode 都能输出 timing/resource summary”，但当前 Stage 2 / Stage 3 的 `RepoHarnessRuntime.run_episode(...)` 还没有完整接入旧 `run_task(...)`、workspace、verifier、reward 和 recorder 主路径。因此 Stage 4 第一版实施范围必须明确分层。

第一版必须覆盖：

- `RepoHarnessRuntime.run_episode(...)` runtime facade 路径。
- runtime facade 的 success、failed、timeout、invalid_task、infrastructure_error 结果。
- 从最小 run directory / recorder artifact 读取 facts 的 summarizer。
- `TimingSummary`、`ResourceSummary`、`BudgetConsumption` 的一致性测试。
- `TrainingView.extra_fields` 和 `AuditRef` 中的 timing/resource opaque refs。

第一版可以准备接口但不能夸大声称已经完整覆盖：

- 旧 `evaluation/runner.py` / CLI 完整任务路径。
- 完整 `agent_loop/loop.py` 多轮工具调用路径。
- workspace materialization、Docker setup、baseline verifier、final verifier、reward compute 的真实生产路径。

如果 Stage 4 实施时要声称覆盖完整 runner / CLI path，就必须实际接入以下位置并补 integration 测试：

```text
src/repo_harness/evaluation/runner.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/context/manager.py
src/repo_harness/reward/calculator.py
```

否则最终汇报必须明确写成：“Stage 4 已覆盖 runtime facade 和 run directory summarizer；完整 CLI / legacy runner path 仍是后续接入或扩展项。”

## 4. 需要先阅读和确认的代码位置

实施前先只读检查这些文件：

```text
src/repo_harness/rl/timing.py
src/repo_harness/rl/runtime.py
src/repo_harness/rl/training_view.py
src/repo_harness/rl/visibility.py
src/repo_harness/trajectory/recorder.py
src/repo_harness/trajectory/schemas.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/context/manager.py
src/repo_harness/model_client/schemas.py
src/repo_harness/model_client/mock.py
src/repo_harness/model_client/replay.py
src/repo_harness/model_client/providers/common.py
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/evaluation/runner.py
src/repo_harness/export/exporter.py
src/repo_harness/export/audit.py
```

同时搜索这些关键词，确认现有耗时和资源事实来源：

```text
duration_ms
ModelCallEvent
TrajectoryEvent
workspace_materialization
docker_setup
baseline_verifier
final_verifier
artifact_write
cleanup_status
workspace_backend
docker_image
snapshot_key
dependency_cache
network_policy
permission_policy
```

## 5. Schema 和 contract 调整

当前 `src/repo_harness/rl/timing.py` 已有 `TimingSummary` 和 `ResourceSummary`，但 Stage 4 需要补齐 contract 字段和校验。

建议对 `TimingSummary` 增加默认安全字段：

```text
dependency_restore_seconds
timing_unattributed_seconds
timing_diagnostics
provider_reported_model_call_seconds
timing_bucket_policy
```

字段语义：

- `dependency_restore_seconds`：dependency state 恢复或依赖缓存加载耗时。Stage 6 做环境复用前可以为 `0`。
- `timing_unattributed_seconds`：外层 wall time 中暂时无法归因的部分。
- `timing_diagnostics`：解释为什么有未归因时间、为什么某些字段只能用近似值、哪些来源缺失。
- `provider_reported_model_call_seconds`：provider 或 gateway 上报的模型耗时，只作为参考，不参与 outer wall time 归因。
- `timing_bucket_policy`：说明解释率使用的分桶策略，例如 `exclusive_runtime_facade_v1`，防止后续误把 nested duration 重复计入。

建议对 `ResourceSummary` 增加默认安全字段：

```text
docker_image_ref
dependency_cache_key
cpu_limit
memory_limit
disk_limit
inference_route
inference_backend
inference_concurrency_slot
```

如果现有 `dependency_state_key`、`docker_resource_limits_effective` 已能承载部分事实，不要重复制造多个相互矛盾字段。新增字段必须有默认值或可选值，保证 Stage 0H / Stage 1 / Stage 2 / Stage 3 fixture roundtrip 不被破坏。

## 6. Timing 汇总设计

Stage 4 建议在 `src/repo_harness/rl/timing.py` 中新增轻量 helper，而不是把所有计算散落在 runtime、runner 和 export 中。

建议新增：

```text
TimingAttribution
TimingAccumulator
compute_timing_explained_ratio(...)
build_timing_summary(...)
summarize_timing_from_run_dir(...)
```

第一版支持两类输入路径：

1. runtime facade live spans  
   直接使用 `perf_counter()` 记录 `rollout_wall_seconds`、`model_call_seconds`、`cleanup_seconds`、artifact summary 写入耗时等。Stage 3 已经有最小模型调用计时，Stage 4 需要把它沉淀成复用 helper。

2. existing run directory / event path  
   从 `events.jsonl`、`transcript.jsonl`、`artifacts.json`、`ModelCallEvent`、workspace command result、verifier result 中汇总已有耗时事实。优先读取真实 `duration_ms` 和 manifest size，不要只靠外层 wall clock 猜。

时间归因规则：

- `rollout_wall_seconds` 是 episode 外层总耗时。
- `model_call_seconds` 来自 runtime 实测 gateway/model call 等待时间；provider reported duration 只进入参考字段。
- `context_prepare_seconds` 优先来自 context preparation event duration。
- `tool_seconds` 优先来自 tool execution / workspace command event duration。
- `baseline_verifier_seconds` 和 `final_verifier_seconds` 优先来自 verifier result 或对应 event duration。
- `artifact_write_seconds` 可以先用 `RunRecorder.write_artifact(...)` 附近的实测耗时和 manifest 汇总近似值。
- `cleanup_seconds` 来自 cleanup callback 或 runner cleanup 路径。
- `agent_loop_seconds` 在 Stage 4 解释率计算中不能表示“包含模型、工具、上下文准备的总 agent loop 时间”。如果它参与 explained sum，它必须表示扣除 `model_call_seconds`、`tool_seconds`、`context_prepare_seconds` 等子阶段后的 residual agent loop overhead。
- `explained_seconds` 只能由互斥分桶相加得到，不能同时加“父阶段总耗时”和“子阶段耗时”。
- `timing_unattributed_seconds = max(0, rollout_wall_seconds - explained_seconds)`。
- `timing_explained_ratio = min(1.0, explained_seconds / rollout_wall_seconds)`，`rollout_wall_seconds=0` 时可视为 `1.0`。
- 如果发现某些来源字段可能是 nested duration，必须把它们标记为 diagnostic/reference，不参与 explained sum。
- 如果 `timing_explained_ratio < 0.95`，必须写入 diagnostics，Stage 4 验收不能把该 episode 标为满足 timing gate。

## 7. BudgetConsumption 对账规则

Stage 4 需要把 `TimingSummary` 和 `BudgetConsumption` 视为同一条 episode 的两份账本，而不是两套独立估算。

runtime facade 第一版必须满足：

```text
BudgetConsumption.used_wall_seconds == TimingSummary.rollout_wall_seconds
BudgetConsumption.used_model_call_seconds == TimingSummary.model_call_seconds
BudgetConsumption.used_artifact_bytes == TimingSummary.artifact_bytes_written
```

如果某个字段因为完整 runner / CLI path 尚未接入而暂时无法精确统计，应遵守：

- 可以填 `0` 或 `None`，但必须在 diagnostics 中说明来源缺失。
- 不能一个 summary 写实测值，另一个 summary 留空或写另一套估算。
- timeout、cancelled、invalid_task、infrastructure_error 也要保留已经发生过的 `used_wall_seconds` 和 `used_model_call_seconds`。

这条规则是 Stage 8 训练预算控制和 no-progress 控制的前置条件。

## 8. Resource 汇总设计

Stage 4 需要把“资源事实”从 runtime-only path 和现有 runner/workspace path 中抽出来，形成 `ResourceSummary`。

第一版数据来源：

- `RepoHarnessRuntimeOptions.execution_mode` -> `execution_mode`
- `RepoHarnessEpisodeRequest.llm_gateway_route` -> `inference_route`
- `RepoHarnessEpisodeRequest.inference_backend` -> `inference_backend`
- runtime-only resolver / options -> 只用于内部解析，不能把绝对路径泄漏到 batch 字段
- workspace adapter / Docker adapter -> `workspace_backend`、`docker_image_id`、`docker_image_digest`、`docker_volume_ids`、`docker_resource_limits_effective`
- task/environment refs -> `snapshot_key`、`dependency_state_key` 或 `dependency_cache_key`
- permission / network policy config -> `permission_policy_ref`、`network_policy`
- cleanup callback / runner cleanup -> `cleanup_status`

路径投影规则：

- 本地绝对 `output_dir`、`workspace_path`、`project_root` 只能留在 runtime-only options 或本地 artifact，不进入 batch 可传播字段。
- `ResourceSummary.run_dir` 建议使用 `runs/<run_id>` 或 `rh://audit/<episode_id>/run-dir` 这类相对或 opaque ref。
- `ResourceSummary.workspace_path` 如果无法安全相对化，应留空，并在 diagnostics 中说明。

## 9. Summary artifact 和引用

Stage 4 需要让 summary 可以被后续审计回查。

建议第一版行为：

- `RepoHarnessEpisodeResult.timing_summary` 和 `resource_summary` 始终直接包含结构化对象。
- 如果 runtime 有可写 run directory 或 recorder，则写入：

```text
timing_summary.json
resource_summary.json
```

- `AuditRef.important_artifact_refs` 增加 opaque ref：

```text
timing_summary: rh://audit/<episode_id>/timing-summary
resource_summary: rh://audit/<episode_id>/resource-summary
```

- `TrainingView.extra_fields` 增加 batch-safe flat refs：

```text
repo_harness_timing_summary_ref
repo_harness_resource_summary_ref
```

这些字段必须通过 Stage 0H visibility 规则：短小、扁平、namespaced、opaque，不包含绝对路径，不包含完整 timing/resource JSON。

## 10. 建议修改文件

预计主要修改：

```text
src/repo_harness/rl/timing.py
src/repo_harness/rl/runtime.py
src/repo_harness/rl/training_view.py
src/repo_harness/rl/visibility.py
```

可能需要修改：

```text
src/repo_harness/trajectory/recorder.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/context/manager.py
src/repo_harness/evaluation/runner.py
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/export/exporter.py
src/repo_harness/export/audit.py
```

预计新增测试：

```text
tests/unit/test_repo_harness_rl_stage4_timing_resource.py
```

如果实际接入 runner / workspace path，还需要补充已有 integration 测试或新增更小的 fixture。

## 11. 实施顺序

1. 先补 Stage 4 测试草案，锁定 success、failed、timeout、invalid_task、infrastructure_error 都有 `TimingSummary` 和 `ResourceSummary`。
2. 在 `timing.py` 中扩展 schema 字段，保证新增字段都有默认值，不破坏旧 fixture roundtrip。
3. 实现 `TimingAccumulator` 或等价 helper，把 Stage 3 runtime 中的手写 timing 计算迁移到 helper。
4. 实现 `compute_timing_explained_ratio(...)`，要求输入分桶互斥，并用测试覆盖未归因时间、diagnostics 和 nested duration 不参与 explained sum。
5. 在 runtime facade 中使用 helper 构造 `TimingSummary`，确保 provider reported `duration_ms` 不参与 outer wall attribution。
6. 同步填充 `BudgetConsumption.used_wall_seconds`、`used_model_call_seconds` 和可获得的 `used_artifact_bytes`，并测试它们和 `TimingSummary` 对齐。
7. 实现 `ResourceSummary` helper，从 request、runtime options、resolved inputs 和 cleanup 状态构造安全资源摘要。
8. 在 `AuditRef.important_artifact_refs` 和 `TrainingView.extra_fields` 中加入 `repo_harness_timing_summary_ref`、`repo_harness_resource_summary_ref` 等 opaque refs。
9. 如果存在可写 recorder/run directory，写入 `timing_summary.json` 和 `resource_summary.json`；如果没有本地 artifact 写入路径，也要返回结构化 summary 对象和 opaque ref。
10. 增加 run_dir/event summarizer 测试：从一个最小 `events.jsonl` / `artifacts.json` 汇总 model/tool/artifact count 和 bytes。
11. 明确最终汇报范围：如果没有接入旧 runner / CLI path，不能声称完整 CLI path 已正式产出 summary。
12. 复跑 Stage 3、Stage 2、Stage 1、Stage 0H 相关回归测试，确认 visibility、schema、runtime、recorder 没有回退。

## 12. 验收标准

Stage 4 完成时，需要满足：

- 成功、失败、timeout、invalid_task、infrastructure_error 都有 `TimingSummary` 和 `ResourceSummary`。
- `TimingSummary.timing_explained_ratio >= 0.95`；如果低于该值，必须有 `timing_unattributed_seconds` 和 `timing_diagnostics`。
- `model_call_seconds` 使用 runtime 实测耗时；provider reported duration 只能进入参考字段。
- 用于 `timing_explained_ratio` 的 timing 字段必须是互斥分桶；`agent_loop_seconds` 如果参与计算，只能是 residual overhead，不能和 model/tool/context 子阶段双重计数。
- runtime facade 路径中，`BudgetConsumption.used_wall_seconds` 与 `TimingSummary.rollout_wall_seconds` 对齐，`BudgetConsumption.used_model_call_seconds` 与 `TimingSummary.model_call_seconds` 对齐。
- `TimingSummary` 至少能区分 model、context prepare、tool、workspace、Docker、baseline verifier、final verifier、reward、artifact、cleanup 和 queue wait 的字段，即使某些字段第一版为 `0`。
- `ResourceSummary` 至少能记录 execution mode、workspace backend、inference route/backend、cleanup status，以及可获得的 Docker、snapshot、dependency、network 和 permission facts。
- `TrainingView.extra_fields` 只新增 namespaced flat opaque refs，不包含完整 JSON、绝对路径或嵌套 `audit_ref`。
- `AuditRef` 能回查 timing/resource summary 的 opaque ref。
- `ResourceSummary.workspace_path` 和 `ResourceSummary.run_dir` 不接受本地绝对路径泄漏。
- `src/repo_harness/rl` 不 import `verl`。
- Stage 0H、Stage 1、Stage 2、Stage 3 回归测试继续通过。
- 最终汇报必须明确 Stage 4 覆盖范围。如果只覆盖 runtime facade 和 run directory summarizer，不能写成完整 CLI / legacy runner path 已覆盖。

## 13. 非目标

Stage 4 明确不做：

- 不实现 workspace/container 复用；这是 Stage 6。
- 不实现 verifier worker pool；这是 Stage 7。
- 不实现训练预算 no-progress 控制；这是 Stage 8。
- 不实现并发资源租约；这是 Stage 9。
- 不实现 `TrainingView` 到 `AgentLoopOutput` 的转换；这是 Stage 10。
- 不实现 `RepoHarnessVerlAgentLoop` 或 `VerlLLMGateway`；这是 Stage 11。
- 不实现真实 Ray GPU resource scheduling。
- 不把详细 timing/resource JSON 直接塞进 batch 字段。

## 14. 建议验收命令

基础命令：

```bash
uv run --extra dev python -m compileall -q src
uv run --extra dev python -m pytest -q tests/unit/test_repo_harness_rl_stage4_timing_resource.py
```

Stage 3、Stage 2、Stage 1、Stage 0H 回归命令：

```bash
uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py \
  tests/unit/test_repo_harness_rl_stage2_runtime.py \
  tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py \
  tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py \
  tests/unit/test_repo_harness_verl_contract_fixtures.py \
  tests/unit/test_repo_harness_verl_stage0h_shape_rules.py \
  tests/unit/test_repo_harness_verl_stage0h_visibility.py
```

如果修改触及 recorder、export 或 runner，需要补跑：

```bash
uv run --extra dev python -m pytest -q \
  tests/unit/test_run_recorder.py \
  tests/unit/test_provider_artifact_binding.py \
  tests/unit/test_export.py \
  tests/integration/test_export_from_run.py \
  tests/integration/test_v3_export_audit.py
```

最终汇报时需要列出：

- 实际修改的文件。
- 新增或修改的 schema 字段。
- `TimingSummary` 解释率计算方式。
- `TimingSummary` 与 `BudgetConsumption` 的一致性验证结果。
- 成功、失败、timeout、invalid_task、infrastructure_error 的 summary 覆盖情况。
- `TrainingView.extra_fields` 和 `AuditRef` 中新增的 opaque refs。
- 哪些 resource facts 因 Stage 6 / Stage 7 / Stage 9 未实施而仍为空或占位。
- Stage 4 实际覆盖的是 runtime facade / run directory summarizer，还是已经包含完整 CLI / legacy runner path。
