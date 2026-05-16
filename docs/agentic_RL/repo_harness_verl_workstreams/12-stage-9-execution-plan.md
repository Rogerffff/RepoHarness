# Stage 9 执行计划：并发安全和资源租约

状态：待实施。本文件只定义 Stage 9 的执行计划，还没有开始代码实现。
前置状态：Stage 0H、Stage 1、Stage 2、Stage 3、Stage 4、Stage 5、Stage 6、Stage 7、Stage 8 已完成。Stage 8 已在提交 `4a7ea803` 中完成训练预算、`no-progress` hard stop、上下文瘦身、`max_model_calls` 计数和相关测试。

## 1. 阶段目标

Stage 9 的目标是让 RepoHarness runtime 可以被多个 episode 并发调用，并且每条 episode 的可写资源彼此隔离、可审计、可释放。

本阶段要解决的问题是：

```text
verl / Ray 后续会并发调度多条 rollout
  -> RepoHarnessRuntime.run_episode(...) 会被并发调用
  -> run directory、workspace、artifact manifest、verifier worker、gateway route 都可能同时使用
  -> 如果缺少资源租约和本地并发限制，episode 之间可能互相覆盖文件、共享可写 workspace、泄漏 patch 或留下后台任务
```

Stage 9 第一版要形成下面的本地资源安全闭环：

```text
RepoHarnessEpisodeRequest
  -> ResourceConcurrencyPolicy / EpisodeResourceLease
  -> acquire episode-level resources: run directory / workspace / recorder
  -> wrap only the actual gateway call with gateway route slot
  -> execute verifier / reward / cleanup outside gateway route slot
  -> release workspace / recorder / verifier future / all acquired slots
  -> TimingSummary + ResourceSummary + audit diagnostics
```

完成后应该能做到：

1. 两条最小 episode 可以并发运行，且 `run_id`、`episode_id`、`run_dir`、`workspace_path`、artifact manifest 和 resource lease 不冲突。
2. `RunRecorder` 仍然只保护单个 run directory，不能被误用为全局并发控制。
3. workspace lease、route concurrency slot、verifier worker pool 和 cleanup 结果都能进入 `ResourceSummary` 或 audit diagnostics。
4. 外层取消、timeout 或 cleanup 失败时，不会静默留下“看起来可训练但资源状态未知”的样本。
5. Stage 9 完成后可以为 Stage 10 的 `TrainingView -> AgentLoopOutput` 转换和 Stage 11 的 verl adapter 提供稳定的并发运行前提。

## 2. 必须保持的边界

1. Stage 9 不实现 Stage 10 的 `TrainingView -> AgentLoopOutput` 转换，不接 DataProto，也不写 verl postprocess 逻辑。
2. Stage 9 不实现 Stage 11 的 `RepoHarnessVerlAgentLoop` 或 `VerlLLMGateway`，不能引入 `verl` import。
3. Stage 9 不实现完整 rollout scheduler。并发调度仍由未来 verl / Ray 负责；RepoHarness 只保证被并发调用时自己的资源边界可控。
4. Stage 9 不实现分布式锁服务、跨机器资源数据库或 Ray actor lease manager。第一版只做单机本地资源租约和本地 filesystem / semaphore 级约束。
5. Stage 9 不实现 warm container pool。container lease 可以预留结构和 summary 字段，但不能声称已经支持长驻容器池。
6. Stage 9 不改变 final verifier 和 reward 的权威边界。Stage 7 的 verifier worker pool 仍然必须同步等待 reward 后再返回 `EpisodeResult`。
7. Stage 9 不改变 Stage 8 的训练预算语义。并发限流导致的 queue timeout 应该是资源或基础设施状态，不能伪装成 `no_progress`。
8. Stage 9 不允许把本地绝对 `run_dir`、workspace path、snapshot cache root、Docker volume path、verifier artifact path 或 reward metadata path 放入模型可见字段、`TrainingView.extra_fields` 或未来 batch 可传播字段。
9. Stage 9 不默认改变现有 CLI / SWE-Bench 路径。第一版优先覆盖 `RepoHarnessRuntime.run_episode(...)` 和本地 helper；如果接入 CLI，必须通过显式配置启用并保持默认兼容。

## 3. 第一版覆盖范围

必须覆盖：

- episode 级资源租约 schema 或 helper。
- run directory 唯一性和 recorder 单 writer 约束。
- workspace lease 的 acquire / release / cleanup / diagnostics 边界。
- gateway route 本地并发限制和 queue wait / queue timeout 记录。
- verifier worker pool 与 episode resource summary 的组合记录。
- cancellation / timeout 后的资源释放和 cleanup diagnostics。
- 两条最小 episode 并发运行时的 run directory、workspace、artifact manifest 和 resource summary 隔离测试。
- `ResourceSummary`、`TrainingView.extra_fields`、audit opaque refs 的路径可见性检查。

可以只做接口或最小实现：

- Docker container lease。第一版可以只记录 `container_reuse_hit=false` 和 cleanup status，不做 warm container 复用。
- dependency cache 全局限流。Stage 6 已有 dependency path copy 安全边界，Stage 9 可以先把 dependency cache queue wait 作为预留字段。
- cross-process stale lease reclaim。第一版可以检测并报告 orphaned / cleanup_failed，不自动抢占或删除不属于当前 runtime 的资源。
- provider 侧真实 rate limit。第一版做本地 semaphore 和 queue timeout，不伪装成 provider 真实限速器。

如果实施时发现完整接入旧 `evaluation/runner.py` 风险较高，应采用两层策略：

1. 先实现独立 resource lease helper，用 fake gateway 和最小 runtime 路径覆盖并发安全。
2. 再以显式 option 把 runtime facade 接入 resource lease helper，保持默认 CLI 路径兼容。

## 4. 需要先阅读和确认的代码位置

实施前先只读检查：

```text
src/repo_harness/rl/runtime.py
src/repo_harness/rl/timing.py
src/repo_harness/rl/episode.py
src/repo_harness/rl/gateway.py
src/repo_harness/rl/provider_gateway.py
src/repo_harness/workspace/reuse.py
src/repo_harness/verifier/pool.py
src/repo_harness/trajectory/recorder.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/budget/schemas.py
src/repo_harness/config/schemas.py
tests/unit/test_workspace_reuse_stage6.py
tests/unit/test_verifier_worker_pool_stage7.py
tests/unit/test_repo_harness_rl_stage8_budget_policy.py
tests/unit/test_agent_loop_stage8_no_progress_stop.py
```

需要重点确认：

- `RepoHarnessRuntimeOptions` 当前有哪些 runtime-only 字段，例如 `cleanup_callback`、`config_path`、`output_dir`。
- `RunRecorder` 当前如何通过 `run.lock` 防止同一个 run directory 被两个 writer 同时打开。
- `WorkspaceSnapshotManager.acquire_workspace(...)` 和 `release_workspace(...)` 当前如何写 lease facts、校验路径归属和释放 workspace。
- `VerifierWorkerPool` 当前如何限制 `max_workers`、`max_pending_jobs`、`queue_timeout_seconds`，以及 execution timeout 后是否仍可能有后台任务。
- `ModelClientLLMGateway` 和其他 gateway 当前是否已有 `close()` / `aclose()` 生命周期。
- `TimingSummary.queue_wait_seconds` 和 `ResourceSummary.queue_wait_seconds_by_resource` 当前字段如何使用。
- `ResourceSummary.workspace_path`、`run_dir`、`lease_id`、`concurrency_group` 等字段是否已经禁止本地绝对路径。

## 5. 建议新增或调整的模块

建议新增：

```text
src/repo_harness/rl/resources.py
```

建议包含以下结构：

```text
ResourceConcurrencyPolicy
EpisodeResourceLease
ResourceLeaseDiagnostics
AsyncResourceLimiter
ResourceLeaseManager
ResourceLeaseHandle
ResourceLeaseError
```

职责建议：

- `ResourceConcurrencyPolicy`：描述本地并发限制，包含 `max_concurrent_episodes`、`max_workspace_leases`、`max_gateway_route_concurrency_by_route`、`route_queue_timeout_seconds`、`workspace_queue_timeout_seconds`、`recorder_lock_timeout_seconds`、`cleanup_timeout_seconds`。
- `EpisodeResourceLease`：记录一次 episode 实际占用的资源标识，至少包含 `episode_id`、`run_id`、`worker_id`、`concurrency_group`、`run_dir_ref`、`workspace_lease_id`、`gateway_route_slot_id`、`verifier_pool_id`、`acquired_at`、`released_at`、`cleanup_status` 和 diagnostics。
- `AsyncResourceLimiter`：本地 async semaphore 封装，负责 route / workspace / episode slot 的 acquire、queue wait、queue timeout 和 release。
- `ResourceLeaseManager`：组合多个 limiter，并把 acquire / release 事实投影到 `TimingSummary` 和 `ResourceSummary`。
- `ResourceLeaseHandle`：runtime-only handle，包含 release 回调和已获得的 slot；不能进入 schema dump 或 batch 可传播字段。
- `ResourceLeaseError`：资源租约获取失败、重复释放、错误 owner 释放、queue timeout 等明确异常或结构化错误。

如果实施时不想立即新增 `resources.py`，也可以先在 `runtime.py` 内部实现小型 helper，但必须保持类型和测试边界清晰，避免把并发逻辑散落到 gateway、workspace 和 recorder 中。

## 6. run directory 和 recorder 单 writer 规则

Stage 9 必须把 run directory 的唯一性写成可测试规则。

建议规则：

1. `run_id` 和 `episode_id` 必须是安全标识符，不能包含本地绝对路径、`..`、路径分隔符或 shell 特殊路径语义。
2. runtime 自动生成 run directory 时，必须使用唯一 `run_id` 或显式 run directory allocator。
3. 如果 request 指定的 `run_id` 对应 run directory 已经存在：
   - 如果存在 active `run.lock`，必须拒绝第二个 writer。
   - 如果存在 `FINALIZED` status，不能默认追加写入。
   - 如果存在 partial / interrupted 文件，Stage 9 第一版不做 resume，必须返回结构化 diagnostics 或要求显式 resume policy。
4. `RunRecorder` 的 `run.lock` 只保护单个 run directory。它不能证明 workspace、snapshot cache、Docker volume 或 gateway route 没有被并发污染。
5. artifact manifest 写入必须仍然是单 writer。并发 episode 不能写同一个 `artifacts.json`。
6. `AuditRef` 和 `TrainingView.extra_fields` 只能保存 opaque ref，例如 `repo_harness_audit_manifest_ref`、`repo_harness_resource_summary_ref`，不能保存本地绝对 manifest path。

测试必须覆盖：

```text
同一个 run_id 并发打开 recorder -> 第二个 writer 被拒绝
不同 run_id 并发写 artifact -> 两个 manifest 路径和 artifact id 不冲突
已有 FINALIZED run_dir -> 不被默认追加写入
```

## 7. workspace lease 规则

Stage 6 已经实现 workspace snapshot 和 lease。Stage 9 要把它纳入 episode 并发生命周期。

建议规则：

1. 每条 episode 必须获得自己的 writable workspace lease。
2. 多条 episode 可以共享只读 snapshot，但不能共享可写 workspace。
3. `WorkspaceLease.workspace_path` 必须形如 `leases/<snapshot_key>/<lease_id>`。
4. `release_workspace(...)` 只能删除当前 manager 拥有的 lease path；不能删除外部目录或其他 manager 的 lease。
5. 外层 cancellation、timeout、异常、verifier failure、gateway failure 都必须进入 `finally` 或等价 cleanup 路径。
6. cleanup 失败不能覆盖 episode 原始状态，但必须写入：

```text
ResourceSummary.cleanup_status
AuditDiagnostic(code="workspace_cleanup_failed", ...)
WorkspaceLease.diagnostics
```

7. Stage 9 第一版不自动 reclaim active stale lease。可以新增 inspect helper 或 diagnostics，把 stale active lease 标记为 `orphaned`，但不能静默删除。
8. 复制 dependency path 时继续沿用 Stage 6 的敏感路径和 symlink 边界；Stage 9 不能为了并发复用绕过该规则。

测试必须覆盖：

```text
两条 episode 基于同一个 snapshot 并发 acquire workspace -> workspace_path 不同
episode A 写入 patch / temp file -> episode B workspace 看不到该文件
release_workspace 重复调用 -> 不删除不属于自己的目录
cancellation 后 workspace lease 最终 released 或 cleanup_failed 且可审计
```

## 8. gateway route 并发限制

Stage 9 必须为 route 调用建立本地并发限制，避免后续多个 episode 在同一个 worker 内无界提交模型请求。

建议规则：

1. `ResourceConcurrencyPolicy.max_gateway_route_concurrency_by_route` 可以按 route 配置本地并发，例如：

```text
verl: 8
local_vllm: 4
local_sglang: 4
openai: 2
deepseek: 2
mock: 32
replay: 32
```

这些数字只是本地默认或测试配置，不代表真实 provider rate limit。

2. route slot acquire 必须记录：

```text
route
slot_id
queue_wait_seconds
queue_timeout_seconds
acquired_at
released_at
```

3. 如果 route slot queue timeout，episode 应该返回结构化不可训练结果：

```text
EpisodeResult.status = timeout
status_reason = "gateway_route_queue_timeout"
TrainingView.invalid_for_training = true
TrainingView.invalid_for_online_rl = true
```

第一版固定映射为 `timeout`，因为这是资源等待超过预算，不是模型语义失败，也不是任务定义本身不合法。

4. route slot 的持有范围必须只覆盖实际 `LLMGateway.generate_turn(...)` 调用，不能覆盖 workspace materialization、verifier、reward、recorder finalize 或 cleanup。否则非模型工作会占住模型并发 slot，导致后续 rollout 被错误限流。
5. route slot 必须在 gateway 调用结束、异常、取消或 timeout 后释放。
6. provider route 仍然默认 `invalid_for_online_rl=true`。route 并发限制不能改变 Stage 5 的 online RL route 闸门：正式 online PPO / GRPO 第一版仍然只允许 `route=verl`。
7. `LLMGatewayResponse.error` 仍然优先进入状态映射，不能被 route limiter 的成功 acquire 掩盖。

测试必须覆盖：

```text
max route concurrency = 1 时，两次 gateway 调用不能同时进入 fake gateway critical section
第二个请求等待 slot 后 queue_wait_seconds > 0
queue_timeout_seconds 很小时，第二个请求返回 gateway_route_queue_timeout 且不可训练
gateway 抛异常或 coroutine 被取消后 route slot 会释放
```

## 9. verifier worker pool 和资源 summary 组合

Stage 7 已经实现 verifier worker pool。Stage 9 要确保它和 episode resource summary 一致。

建议规则：

1. `VerifierWorkerPool` 仍然由 runtime option 或调用方显式传入，Stage 9 不创建全局隐藏 pool。
2. `VerifierJobResult.pool_id`、`worker_id`、`queue_wait_seconds` 必须进入：

```text
TimingSummary.queue_wait_seconds
ResourceSummary.verifier_worker_pool_id
ResourceSummary.verifier_worker_id
ResourceSummary.queue_wait_seconds_by_resource["verifier_worker"]
```

3. verifier queue timeout、execution timeout、pool closed、pool executor error 都不能被标记成普通模型失败。
4. 如果 verifier job 尚未开始就因为 queue timeout 或 cancellation 返回，必须保证它不会之后再执行。
5. 如果 verifier job 已经开始，Stage 9 不承诺强杀不可中断同步线程；必须依赖 verifier command timeout，并把真实能力写入 diagnostics。

测试必须覆盖：

```text
两个 verifier job 并发提交到 max_workers=1 的 pool -> 第二个记录 queue wait
queue_timeout job 不会进入 executor 后台执行
pool closed 后提交 job -> 明确失败且不可训练
```

## 10. cancellation、timeout 和 cleanup 规则

Stage 9 必须把资源释放作为 runtime contract，而不是只依赖 Python 对象析构。

建议规则：

1. `RepoHarnessRuntime.run_episode(...)` 内部必须有 `try/finally` 或等价结构，释放已经 acquire 的资源。
2. cleanup 顺序建议：

```text
stop accepting new model / verifier work
release gateway route slot
cancel or await verifier future according to Stage 7 contract
finalize or close recorder
release workspace lease
record cleanup diagnostics
build minimal EpisodeResult if possible
```

3. cleanup 失败不能覆盖原始 episode status。例如原始状态是 `timeout`，workspace cleanup 失败后仍然是 `timeout`，但 `ResourceSummary.cleanup_status="failed"`。
4. cancellation 默认结果：

```text
EpisodeResult.status = cancelled
TrainingView.invalid_for_training = true
TrainingView.invalid_for_online_rl = true
```

5. 如果 cancellation 发生在 result schema 还无法构造的极早阶段，可以向外抛出明确基础设施异常，但必须尽可能写出 run diagnostics 或 release 已获得资源。
6. 所有 cleanup diagnostics 不能包含本地绝对路径；如果需要离线排查，只能通过 opaque audit ref 回查。

测试必须覆盖：

```text
agent loop 中途取消 -> route slot released、workspace released 或 cleanup_failed、recorder lock closed
cleanup_callback 抛异常 -> 原始 status 保留，cleanup_failed diagnostics 存在
gateway timeout -> route slot released，下一条 episode 可以继续获取 slot
```

## 11. ResourceSummary 和 visibility 规则

Stage 9 要把资源租约事实写入 `ResourceSummary`，但不能把主机路径泄漏进训练字段。

允许进入 `ResourceSummary` 的字段示例：

```text
worker_id = "local-worker-0"
host_id = "host-<hash>"
concurrency_group = "training-fast-local"
lease_id = "lease-..."
workspace_path = "leases/<snapshot_key>/<lease_id>"
run_dir = "runs/<run_id>" 或 opaque relative ref
inference_route = "mock" / "verl" / ...
inference_concurrency_slot = "route-mock-slot-0"
queue_wait_seconds_by_resource = {
  "gateway_route": 0.012,
  "workspace_lease": 0.004,
  "verifier_worker": 0.031
}
cleanup_status = "completed" / "failed" / "skipped"
```

`cleanup_status` 必须使用 Stage 6 / ResourceSummary 侧的 canonical 取值，避免同一个字段同时出现 `ok`、`not_required`、`completed`、`skipped` 等多套语义。

建议 canonical 取值：

```text
not_started
completed
failed
skipped
```

当前 runtime helper 或旧路径如果产生其他清理状态，Stage 9 必须做规范化映射：

| 输入状态 | ResourceSummary.cleanup_status |
| --- | --- |
| `ok` | `completed` |
| `not_required` | `skipped` |
| `not_started` | `not_started` |
| `completed` | `completed` |
| `failed` | `failed` |
| `skipped` | `skipped` |

如果新增 schema validator，`ResourceSummary.cleanup_status` 应只接受上述 canonical 取值或 `None`。如果暂时不加 validator，测试必须覆盖 runtime 投影结果不会输出 `ok` 或 `not_required`。

禁止进入 `ResourceSummary`、`TrainingView.extra_fields` 或未来 batch 可传播字段：

- `/Users/...`、`/tmp/...`、Docker host mount path、snapshot cache root 等本地绝对路径。
- reward metadata path、final verifier artifact path、hidden evaluator path。
- 嵌套 `audit_ref` 对象。
- 未命名空间化的开放字段。

`TrainingView.extra_fields` 只能保留短小、扁平、以 `repo_harness_*` 命名的 opaque ref 或 scalar，例如：

```text
repo_harness_resource_summary_ref = "rh://audit/<episode_id>/resource-summary"
repo_harness_concurrency_group = "training-fast-local"
repo_harness_cleanup_status = "completed"
```

## 12. 状态映射建议

Stage 9 新增的资源错误需要固定状态映射，避免基础设施问题混入模型失败样本。

| 输入事实 | EpisodeResult.status | status_reason | 训练默认处理 |
| --- | --- | --- | --- |
| route slot queue timeout | `timeout` | `gateway_route_queue_timeout` | `invalid_for_training=true`、`invalid_for_online_rl=true` |
| workspace lease queue timeout | `timeout` | `workspace_lease_queue_timeout` | `invalid_for_training=true`、`invalid_for_online_rl=true` |
| duplicate active run writer | `infrastructure_error` | `run_directory_lock_conflict` | 默认不可训练 |
| existing finalized run directory without resume policy | `infrastructure_error` | `run_directory_already_finalized` | 默认不可训练 |
| workspace lease ownership mismatch | `infrastructure_error` | `workspace_lease_owner_mismatch` | 默认不可训练 |
| workspace cleanup failed after model failure | 保留原始 status | `cleanup_failed` 进入 diagnostics | 默认按原始状态和 reward policy；cleanup diagnostics 必须存在 |
| external cancellation | `cancelled` | `episode_cancelled` | 默认不可训练 |
| verifier pool queue timeout | `timeout` | `verifier_queue_timeout` | Stage 7 已覆盖，Stage 9 验证并发组合 |

说明：`run_directory_already_finalized` 固定为 `infrastructure_error`，因为这是 run directory / recorder 资源状态冲突，不是任务数据本身 invalid。只有 request 传入非法 `run_id`、非法 path ref 或不满足 schema 的任务引用时，才应该走 `invalid_task` 或 schema validation error。

如果 implementation 选择不同 status，必须在代码注释、测试和本文件后续更新中明确说明理由。

## 13. 建议实施步骤

### Step 1：只读盘点当前资源生命周期

输出当前资源生命周期表，至少覆盖：

```text
run directory
RunRecorder lock
artifact manifest
workspace snapshot
workspace lease
gateway route call
verifier worker job
cleanup callback
```

确认哪些资源已经有独立生命周期，哪些只存在隐含行为。

### Step 2：新增本地资源并发 helper

新增 `src/repo_harness/rl/resources.py` 或等价模块，先实现：

```text
ResourceConcurrencyPolicy
AsyncResourceLimiter
ResourceLeaseDiagnostics
ResourceLeaseError
```

最小要求：

- acquire 返回 queue wait。
- queue timeout 返回结构化错误。
- release 幂等，但错误 owner 释放必须可诊断。
- 不使用全局隐藏 singleton。并发 policy 和 manager 必须由 runtime option 或测试显式创建。

### Step 3：接入 runtime facade

在 `RepoHarnessRuntimeOptions` 中增加可选 resource manager / concurrency policy 字段。默认 `None` 时保持现有行为。

接入点：

```text
run_episode start -> acquire episode-level resources in fixed order
fixed order -> episode slot -> run directory / recorder -> workspace lease
gateway generate_turn -> acquire route slot -> call gateway -> release route slot
verifier reward boundary -> 合并 worker pool queue wait
finally -> release all acquired resources
```

多资源 acquire 必须有固定顺序，任意一步 acquire 失败、queue timeout 或 cancellation 时，必须按相反顺序释放已经拿到的前置资源。第一版不要在 `run_episode start` 长时间持有 route slot；route slot 只在实际 gateway 调用期间获取和释放。

如果当前最小 runtime 还没有真实 workspace manager，可先支持 runtime-only fake workspace lease，用测试证明接口和 summary 正确；真实 `WorkspaceSnapshotManager` 接入可以作为本阶段第二步。

### Step 4：完善 ResourceSummary 投影

把资源租约事实合并到 `_resource_summary(...)` 或等价 helper。

要求：

- `queue_wait_seconds_by_resource` 合并 gateway、workspace、verifier 的等待耗时。
- `cleanup_status` 反映最终 cleanup 结果。
- `lease_id`、`concurrency_group`、`inference_concurrency_slot` 不含本地绝对路径。
- 如果没有真实 artifact 文件，不写虚假的 summary path，只写 opaque ref 和结构化对象。

### Step 5：补并发和 cancellation 测试

新增 Stage 9 单元测试文件，建议：

```text
tests/unit/test_repo_harness_rl_stage9_resource_leases.py
tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py
```

测试要覆盖 happy path、冲突、queue timeout、取消和 cleanup failure，而不仅是 schema roundtrip。

### Step 6：回归前置阶段

Stage 9 实施完成后必须继续跑 Stage 0H 到 Stage 8 的目标回归，尤其是：

- Stage 4 `TimingSummary` / `ResourceSummary` 低解释率和路径可见性规则。
- Stage 5 route 闸门。
- Stage 6 workspace lease 安全边界。
- Stage 7 verifier pool 不后台执行未开始 job。
- Stage 8 budget / no-progress stop 不被 route queue timeout 混淆。

## 14. 测试计划

新增测试建议：

```text
tests/unit/test_repo_harness_rl_stage9_resource_leases.py
  - ResourceConcurrencyPolicy 默认值和 schema roundtrip。
  - AsyncResourceLimiter max_concurrency=1 时第二个 acquire 等待。
  - AsyncResourceLimiter queue_timeout 时不占用 slot。
  - release 后 slot 可被下一条 episode 获取。
  - double release 幂等，错误 owner release 有 diagnostics。
  - ResourceSummary 不接受本地绝对 workspace_path / run_dir / queue resource name。

tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py
  - 两条 fake gateway 最小 episode 并发运行，run_id、episode_id、audit ref、resource summary 不冲突。
  - gateway route concurrency=1 时 fake gateway critical section 不重叠。
  - route queue timeout 返回不可训练 `timeout` result。
  - 外层 cancellation 后 route slot 释放，下一条 episode 可以继续运行。
  - cleanup callback 抛异常时，原始 status 保留且 cleanup diagnostics 存在。
  - duplicate active run writer 被拒绝，不写同一个 artifact manifest。
```

回归测试建议：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m compileall -q src

PYTHONPATH=src PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage9_resource_leases.py \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py \
  tests/unit/test_workspace_reuse_stage6.py \
  tests/unit/test_verifier_worker_pool_stage7.py \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py \
  tests/unit/test_agent_loop_stage8_no_progress_stop.py \
  tests/unit/test_context_stage8_training_slimming.py

PYTHONPATH=src PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage5_gateway_routes.py \
  tests/unit/test_repo_harness_rl_stage5_provider_gateway.py \
  tests/unit/test_repo_harness_rl_stage4_timing_resource.py \
  tests/unit/test_repo_harness_rl_stage3_training_fast_recorder.py \
  tests/unit/test_repo_harness_rl_stage2_runtime.py \
  tests/unit/test_repo_harness_rl_stage1_schema_roundtrip.py \
  tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py \
  tests/unit/test_repo_harness_verl_contract_fixtures.py \
  tests/unit/test_repo_harness_verl_stage0h_shape_rules.py \
  tests/unit/test_repo_harness_verl_stage0h_visibility.py

rg -n "(^|\\s)(import|from)\\s+verl" \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  src/repo_harness/workspace \
  src/repo_harness/verifier
```

`rg` 无输出表示本阶段没有引入 `verl` import。

## 15. 阶段出口标准

Stage 9 完成时必须满足：

1. 两条最小 episode 可以并发运行，并且 run directory、workspace、artifact manifest、resource lease 不冲突。
2. route concurrency limiter 可以证明最大并发数生效，queue wait 和 queue timeout 可审计。
3. workspace lease 在成功、失败、timeout、cancelled、cleanup failure 情况下都有 release 或 cleanup diagnostics。
4. duplicate active run writer 不能写入同一个 artifact manifest。
5. `ResourceSummary` 可以反查 workspace lease、route slot、verifier worker pool 和 cleanup status。
6. `TimingSummary.queue_wait_seconds` 或 `queue_wait_seconds_by_resource` 能解释资源等待时间。
7. 所有新增 resource refs 和 batch 可传播字段都不包含本地绝对路径。
8. Stage 0H 到 Stage 8 目标回归通过。
9. `src/repo_harness/rl`、`agent_loop`、`workspace`、`verifier` 不出现 `verl` import。

## 16. 不建议在 Stage 9 做的事情

不要在 Stage 9 中做下面这些事情：

- 写 `RepoHarnessVerlAgentLoop`。
- 写 `VerlLLMGateway`。
- 连接 Ray、vLLM 或 SGLang server。
- 把 `TrainingView` 转成 `AgentLoopOutput`。
- 改 DataProto、TransferQueue 或 PPO / GRPO trainer。
- 做完整分布式 lease database。
- 自动删除不属于当前 manager 的 stale workspace。
- 把 provider route 样本标记为正式 online RL 可用。
- 用最终 transcript 重新分词来伪造正式训练 token。

## 17. 审查重点

Stage 9 实施完成后，sub agent 或人工审查应重点检查：

1. 是否存在任何共享可写 workspace。
2. 是否存在同一个 run directory 被两个 writer 追加写入。
3. route limiter 是否真的限制 concurrent gateway call，而不是只记录字段。
4. queue timeout 后的 job / gateway call 是否还会在后台继续执行。
5. cancellation 后 resource slot 是否释放。
6. cleanup failure 是否覆盖了原始 episode status。
7. `ResourceSummary` 和 `TrainingView.extra_fields` 是否泄漏本地绝对路径。
8. 是否为了通过测试引入了全局隐藏 singleton，导致后续 Ray worker 内状态难以审计。
9. 是否越界实现 Stage 10 / Stage 11。
