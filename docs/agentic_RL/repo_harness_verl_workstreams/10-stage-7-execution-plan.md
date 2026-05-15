# Stage 7 执行计划：verifier worker pool 和 reward 边界

状态：待实施。本文件只定义 Stage 7 的执行计划，还没有开始代码实现。
前置状态：Stage 0H、Stage 1、Stage 2、Stage 3、Stage 4、Stage 5、Stage 6 已完成。Stage 6 已在提交 `15a16430` 中完成 workspace snapshot、dependency path copy 安全边界、workspace lease、ResourceSummary 投影和相关测试。

## 1. 阶段目标

Stage 7 的目标是把 final verifier 的执行从单条 episode 内部的直接同步调用，演进为可池化、可限流、可计时、可审计的执行边界，同时保持第一版在线强化学习样本最重要的不变量：

```text
EpisodeResult 返回前必须已经得到 final verifier 结果和 reward。
```

也就是说，本阶段允许优化 verifier 的执行调度方式，但不允许改变 reward 的语义边界。

目标流程是：

```text
episode 完成 agent loop
  -> 提交 final verifier job
  -> verifier worker pool 排队和执行
  -> episode 等待 verifier result
  -> 根据 verifier result 计算 reward metadata
  -> 写入 final verifier artifact 和 reward metadata artifact
  -> 构造 RepoHarnessEpisodeResult
  -> 返回 TrainingView / 后续 AgentLoopOutput 所需字段
```

完成后应该能做到：

1. final verifier 可以通过有限并发的 worker pool 执行。
2. 每次 verifier job 都能记录 `pool_id`、`worker_id`、排队等待时间、执行时间、超时状态和失败类别。
3. `TimingSummary` 能体现 verifier 排队等待和执行耗时。
4. `ResourceSummary` 能体现 verifier worker pool 和 worker 的资源使用事实。
5. final verifier 结果和 reward metadata 仍然通过 `AuditRef` 可回查。
6. verifier timeout、verifier 基础设施错误、workspace 污染或 parser 低置信度不能被伪装成普通模型失败样本。

## 2. 必须保持的边界

1. Stage 7 不做 asynchronous reward backfill。不能先返回没有 reward 的普通成功样本，再由后台补 reward。
2. Stage 7 不允许返回“看起来是 `status=succeeded`、但实际没有 final verifier result 或 reward metadata”的 online RL 样本。
3. Stage 7 不改变 final verifier 的权威边界。模型可见的 public feedback 仍然不能替代 hidden final verifier。
4. Stage 7 不改变 reward 公式的核心含义。已有 `compute_reward_metadata(...)` 可以被封装和增强审计事实，但不能把 verifier 基础设施失败当成模型语义失败。
5. Stage 7 不把 reward metadata、hidden verifier 输出、accepted label、fail-to-pass / pass-to-pass hidden 细节放进模型可见 prompt、`raw_prompt`、`response_ids` 或训练可传播的开放字段。
6. Stage 7 不实现 Stage 8 的 no-progress 策略优化。no-progress 默认仍然保守处理为 `status=no_progress` 且 `invalid_for_training=true`，除非后续明确 reward policy 支持。
7. Stage 7 不实现 Stage 9 的全局分布式资源租约。第一版 worker pool 可以是单进程本地池，但必须有清晰的本地生命周期和关闭语义。
8. Stage 7 不实现 Stage 11 的 `RepoHarnessVerlAgentLoop` 或 `VerlLLMGateway`，也不能引入 `verl` import。
9. Stage 7 不改变默认 CLI / SWE-Bench 路径的行为，除非通过显式配置启用 verifier worker pool，并且保留回退到当前同步 verifier 的能力。

## 3. 第一版覆盖范围

必须覆盖：

- verifier worker pool 的最小结构和有限并发执行。
- final verifier job 的提交、排队、执行、结果返回和关闭语义。
- queue wait、worker id、pool id、execution duration、timeout、exception 的结构化记录。
- final verifier 结果到 reward metadata 的同步计算边界。
- `TimingSummary` 和 `ResourceSummary` 的 verifier 字段填充。
- infrastructure error、timeout、invalid task、model failure 的状态区分。
- reward、final verifier、hidden details 的 visibility 测试。

可以只做接口或最小实现：

- baseline verifier cache。可以保留字段和计划，但不要在 Stage 7 第一版把 baseline cache 作为训练样本有效性的前提。
- 多进程或跨机器 worker pool。第一版只需要本地 bounded executor 或等价调度。
- worker 长驻容器。warm container pool 属于 Stage 6 后续优化或 Stage 9 资源租约，不在本阶段默认实现。

如果实施时发现完整接入 `evaluation/runner.py` 风险较高，应采用两层策略：

1. 先实现独立 verifier pool 和 reward boundary helper，用 fake verifier callable 覆盖 contract。
2. 再用可选配置把 runtime facade 或 runner 中的 final verifier 调用切到 pool，不破坏默认路径。

## 4. 需要先阅读和确认的代码位置

实施前先只读检查：

```text
src/repo_harness/verifier/runner.py
src/repo_harness/verifier/schemas.py
src/repo_harness/verifier/acceptance.py
src/repo_harness/reward/calculator.py
src/repo_harness/reward/schemas.py
src/repo_harness/rl/runtime.py
src/repo_harness/rl/episode.py
src/repo_harness/rl/timing.py
src/repo_harness/rl/training_view.py
src/repo_harness/rl/visibility.py
src/repo_harness/evaluation/runner.py
src/repo_harness/trajectory/recorder.py
src/repo_harness/workspace/reuse.py
tests/unit/test_reward.py
tests/integration/test_verifier_micro_repos.py
tests/unit/test_repo_harness_rl_stage4_timing_resource.py
tests/unit/test_repo_harness_rl_stage5_gateway_routes.py
tests/unit/test_workspace_reuse_stage6.py
```

需要重点确认：

- `PytestVerifier.run_final(...)` 当前如何返回 `VerifierResult`。
- `VerifierResult.timeout`、`VerifierResult.error_type`、`parser_confidence`、`accepted` 如何表达 verifier 成功、失败和不可信结果。
- `compute_reward_metadata(...)` 当前如何把 final verifier 结果转换为 `RewardMetadata`。
- `RewardMetadata.invalid_for_training` 和 `invalid_reason` 如何阻断训练样本。
- `RepoHarnessEpisodeResult.status`、`TrainingView.reward_score`、`invalid_for_training`、`invalid_for_online_rl` 当前如何组合。
- `TimingSummary` 是否已有 `queue_wait_seconds`、`verifier_seconds`、`final_verifier_seconds`、`reward_compute_seconds`。
- `ResourceSummary` 是否已有 `verifier_worker_pool_id`、`verifier_worker_id`、`queue_wait_seconds_by_resource`。

## 5. 建议新增或调整的模块

建议新增：

```text
src/repo_harness/verifier/pool.py
```

建议包含以下结构：

```text
VerifierPoolOptions
VerifierJob
VerifierJobResult
VerifierWorkerPool
VerifierWorkerPoolClosedError
VerifierExecutionError
```

职责建议：

- `VerifierPoolOptions`：配置 `pool_id`、`max_workers`、`max_pending_jobs`、`queue_timeout_seconds`、`default_execution_timeout_seconds`、是否记录 worker diagnostics。
- `VerifierJob`：描述一次 final verifier 任务，至少包含 `job_id`、`run_id`、`episode_id`、`task_id`、`verifier_stage`、`timeout_seconds` 和一个 runtime-only callable。这个 callable 只能存在于运行时对象中，不能进入 artifact、schema dump、`TrainingView.extra_fields` 或未来 `AgentLoopOutput.extra_fields`。
- `VerifierJobResult`：承载 `VerifierResult` 或结构化错误，并记录 `pool_id`、`worker_id`、`queue_wait_seconds`、`execution_seconds`、`submitted_at`、`started_at`、`finished_at`、`timeout`、`error_type`、`diagnostics`。
- `VerifierWorkerPool`：负责有限并发提交、排队等待计时、执行 final verifier、关闭 executor。
- `VerifierWorkerPoolClosedError`：关闭后再次提交时抛出的明确错误。
- `VerifierExecutionError`：把 verifier callable 抛出的异常转换成结构化基础设施错误。

第一版可以使用 `concurrent.futures.ThreadPoolExecutor` 或 `asyncio` 受控 executor。需要特别注意，普通 `ThreadPoolExecutor(max_workers=N)` 只限制正在运行的 worker 数量，不限制内部待执行队列长度；这不等于真正的 verifier 限流。无论选哪种方式，都必须满足：

1. `max_workers` 必须大于等于 1，并且不能无界增长。
2. pending job 数量必须有硬上限，例如使用 bounded queue、bounded semaphore 或等价机制实现 `max_pending_jobs`。
3. 如果没有拿到 verifier slot，必须在 `queue_timeout_seconds` 内返回结构化 `queue_timeout`，不能无限排队，也不能把 job 悄悄塞进无界 executor 队列。
4. worker id 必须稳定可记录，例如 `verifier-worker-0`、`verifier-worker-1`。
5. pool id 必须稳定可记录，例如显式配置或 `verifier-pool-local-v1`。
6. `close()` / `aclose()` / context manager 必须释放 executor 资源。
7. 关闭后再次提交 job 必须失败为明确异常，不能悄悄创建新线程池。

## 6. queue wait、timeout 和 cancellation 语义

Stage 7 需要把 verifier 的等待和执行分开记录。

建议语义：

```text
submitted_at:
  episode 提交 verifier job 的时间。

started_at:
  某个 worker 真正开始执行 verifier callable 的时间。

finished_at:
  verifier callable 返回结果或失败的时间。

queue_wait_seconds:
  started_at - submitted_at。

execution_seconds:
  finished_at - started_at。
```

timeout 至少分两类：

```text
queue_timeout:
  job 等待 verifier slot 或 worker 的时间超过 queue_timeout_seconds。

execution_timeout:
  verifier 执行时间超过 timeout_seconds，或者底层 workspace command timeout。
```

需要特别注意：如果第一版用线程池包装现有同步 verifier，外层 coroutine 被取消或 `future.result(timeout=...)` 超时，不一定能强制杀掉底层同步 verifier 线程。计划实施时必须写清楚真实能力：

- 底层 `PytestVerifier` 仍应依赖 `WorkspaceAdapter.run_command(..., timeout_sec=...)` 控制 pytest 命令超时。
- pool 层的 timeout 可以返回结构化 timeout result，但不能假装已经强制终止所有不可中断的同步代码。
- cleanup 必须由 episode runtime 或 runner 的 `try/finally` 保护，不能只依赖 pool future 自动释放资源。
- 如果 cancellation 发生在 verifier job 已提交之后，结果必须记录为 `cancelled` 或 `timeout`，并尽可能记录 job 是否已经开始执行。
- `queue_timeout` 必须发生在 job 进入无界 executor 队列之前。实现时不能先提交到无界队列，再在外层等待超时；这种写法会让 verifier 任务在后台继续堆积，训练场景下会造成资源耗尽和不可审计的延迟。

## 7. 状态映射和 reward 边界

Stage 7 必须明确区分“模型没有解决任务”和“基础设施无法给出可信 reward”。

建议映射规则：

| 输入事实 | EpisodeResult.status | 训练默认处理 |
| --- | --- | --- |
| final verifier accepted 且 reward metadata 有效 | `succeeded` | 可以训练，reward 来自 `RewardMetadata.final_reward` |
| final verifier rejected，但 verifier 本身可信 | `failed` | 可以按 reward policy 作为模型失败样本训练 |
| final verifier timeout | `timeout` | 默认 `invalid_for_training=true`，不能作为普通模型失败 |
| verifier parser 低置信度 | `infrastructure_error` 或 `invalid` | 默认 `invalid_for_training=true` |
| verifier command 不合法或任务 verifier 配置不合法 | `invalid_task` | 默认不可训练 |
| workspace、Docker、文件系统、recorder、pool executor 异常 | `infrastructure_error` | 默认不可训练 |
| 外层 episode 取消 | `cancelled` | 默认不可训练 |
| no-progress | `no_progress` | Stage 7 默认不可训练，后续 Stage 8 再细化 |

reward 计算规则：

1. `RewardMetadata` 必须在 `RepoHarnessEpisodeResult` 返回前完成。
2. `TrainingView.reward_score` 只能来自已完成且可消费的 reward metadata。
3. 如果 reward metadata 标记 `invalid_for_training=true`，则 `TrainingView.invalid_for_training` 也必须为 true。
4. 如果 final verifier 或 reward 计算失败，不能返回普通 `succeeded` 样本，也不能只把 reward 置为 0 后继续训练。
5. final verifier rejected 可以是模型失败样本；final verifier timeout 或 verifier infrastructure error 不是模型失败样本。
6. Stage 7 helper 不能直接信任现有 `compute_reward_metadata(...)` 对 `invalid_for_training` 的判断。当前 reward calculator 的 invalid 判断只覆盖部分错误类型，Stage 7 必须在 helper 中包裹或更新 reward 计算，把 verifier command、workspace、dependency、Docker、pool executor 等基础设施错误统一标记为不可训练。

Stage 7 需要显式覆盖下面错误类型：

| final verifier error_type 或 pool error | EpisodeResult.status | RewardMetadata / TrainingView 默认处理 |
| --- | --- | --- |
| `test_command_error` | `invalid_task` | `invalid_for_training=true`，不能产生可训练 reward_score |
| `dependency_error` | `infrastructure_error` | `invalid_for_training=true`，不能作为模型负样本 |
| `verification_workspace_error` | `infrastructure_error` | `invalid_for_training=true`，不能作为模型负样本 |
| `docker_error` 或 `container_error` | `infrastructure_error` | `invalid_for_training=true`，不能作为模型负样本 |
| `pool_executor_error` | `infrastructure_error` | `invalid_for_training=true`，不能作为模型负样本 |
| `queue_timeout` | `timeout` | `invalid_for_training=true`，不能作为模型负样本 |

## 8. AuditRef、artifact 和 visibility 规则

Stage 7 必须保留可审计性，但不能泄漏 hidden evaluator 信息。

建议 artifact 边界：

```text
final verifier artifact:
  保存完整 verifier result 或摘要，位于 run artifact 中，只通过 AuditRef 回查。

reward metadata artifact:
  保存完整 RewardMetadata，位于 run artifact 中，只通过 AuditRef 回查。

TrainingView.extra_fields:
  只允许 repo_harness_* namespaced flat scalar 和 opaque ref。
```

禁止进入模型可见字段或 batch 可传播开放字段的内容：

- hidden verifier stdout / stderr 全文。
- fail-to-pass / pass-to-pass hidden 测试名称明细。
- accepted label 的原始 evaluator-only 事实。
- 完整 reward components 和 reward sources。
- 本地绝对 run directory。
- final verifier artifact 的本地绝对路径。
- gold patch、hidden selector、evaluator-only logs。

允许进入 batch 可传播字段的内容必须是短小且不泄漏路径的字段，例如：

```text
repo_harness_reward_metadata_ref = "rh://..."
repo_harness_final_verifier_ref = "rh://..."
repo_harness_verifier_worker_pool_id = "verifier-pool-local-v1"
repo_harness_verifier_worker_id = "verifier-worker-0"
repo_harness_status = "failed"
repo_harness_invalid_for_training = false
```

注意：完整 `AuditRef` 仍然可以作为 `RepoHarnessEpisodeResult.audit_ref` 的结构化对象存在，但未来不能嵌套进入 `AgentLoopOutput.extra_fields`。

## 9. TimingSummary 和 ResourceSummary 接入

Stage 7 需要把 verifier worker pool 的事实写入 Stage 4 已经建立的 summary 体系。

`TimingSummary` 建议填充：

```text
queue_wait_seconds:
  episode 等待 verifier worker 的总排队时间，或所有资源等待时间总和。

verifier_seconds:
  verifier 相关总耗时，可以包含 baseline verifier 和 final verifier 的互斥分桶总和。

final_verifier_seconds:
  final verifier 实际执行时间。

reward_compute_seconds:
  reward metadata 计算耗时。

verifier_call_count:
  至少包含 final verifier 调用次数。
```

如果 `queue_wait_seconds` 已经包含 verifier wait，则 `agent_loop_seconds` 不能再次包含同一段等待时间。Stage 4 已经明确 `TimingSummary` 的解释字段应尽量是互斥分桶；Stage 7 实施时需要继续遵守，避免通过重复计数把解释率伪装成 1.0。

`ResourceSummary` 建议填充：

```text
verifier_worker_pool_id
verifier_worker_id
queue_wait_seconds_by_resource["verifier_worker"]
cleanup_status
```

这些字段不能包含本地绝对路径。`queue_wait_seconds_by_resource` 的 key 应使用稳定资源名称，例如 `verifier_worker`，不要使用 `/Users/.../pool.lock` 或线程对象 repr。

## 10. 与现有 runner 的接入策略

Stage 7 不应该一次性重写完整 `evaluation/runner.py`。建议分三步接入：

1. 新增 `VerifierWorkerPool`，用 fake verifier callable 单独测试 pool 行为。
2. 新增 reward boundary helper，例如：

```text
run_final_verifier_and_compute_reward(...)
```

这个 helper 接收 final verifier callable、pool、reward inputs 和 recorder / audit refs，返回结构化结果。

3. 在 runtime facade 或 evaluation runner 中增加可选配置：

```text
verifier_execution_strategy = "direct_blocking" | "worker_pool_blocking"
```

默认仍可保持 `direct_blocking`，避免破坏现有 CLI 和 SWE-Bench 测试路径。启用 `worker_pool_blocking` 时，runner 仍然必须等待 reward 后再返回。

如果 Stage 7 第一版只接入 runtime facade，而没有完全覆盖 CLI / SWE-Bench 路径，执行报告必须如实说明。不能把“pool helper 已经实现”描述成“所有现有 runner 路径都已经自动使用 verifier worker pool”。

## 11. 测试计划

建议新增测试：

```text
tests/unit/test_verifier_worker_pool_stage7.py
tests/unit/test_repo_harness_rl_stage7_reward_boundary.py
```

必须覆盖：

1. `VerifierWorkerPool` 使用 `max_workers=1` 时，两个 job 会产生可观测 queue wait。
2. job result 包含 `pool_id`、`worker_id`、`queue_wait_seconds`、`execution_seconds`。
3. pool 关闭后再次提交 job 会得到明确错误。
4. verifier callable 抛异常时，结果映射为 infrastructure error，不会伪装成模型失败。
5. verifier timeout 时，episode status 映射为 `timeout`，并且默认不可训练。
6. final verifier accepted 时，reward 在 EpisodeResult 返回前已经存在。
7. final verifier rejected 但 verifier 可信时，episode status 为 `failed`，reward 按 policy 给出，且不是 infrastructure error。
8. reward metadata 标记 invalid 时，TrainingView 也必须 `invalid_for_training=true`。
9. final verifier `error_type=test_command_error` 时，episode status 必须是 `invalid_task`，`TrainingView.invalid_for_training=true`，`reward_score` 不能进入可训练样本。
10. final verifier `error_type=dependency_error` 或 `verification_workspace_error` 时，episode status 必须是 `infrastructure_error`，默认不可训练。
11. pool pending queue 已满或等待超过 `queue_timeout_seconds` 时，返回 `queue_timeout`，不会把 job 塞进无界等待队列。
12. `VerifierJob` 中的 callable 是 runtime-only 字段，不能进入 artifact、schema dump、`TrainingView.extra_fields` 或未来 `AgentLoopOutput.extra_fields`。
13. hidden verifier 细节、完整 reward metadata、accepted label 不进入 `raw_prompt`、`response_ids`、`TrainingView.extra_fields`。
14. `TimingSummary` 包含 queue wait、final verifier execution 和 reward compute 时间，且没有明显双重计数。
15. `ResourceSummary` 包含 verifier pool id、worker id 和 verifier wait resource key。
16. `src/repo_harness/rl` 和新增 verifier pool 模块不 import `verl`。

需要继续跑前置阶段回归：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
PATH=.venv/bin:$PATH python -m pytest -q \
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
  tests/unit/test_repo_harness_verl_stage0h_visibility.py
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_reward.py
PATH=.venv/bin:$PATH python -m pytest -q tests/integration/test_verifier_micro_repos.py
rg -n "(^|\\s)(import|from)\\s+verl" src/repo_harness/rl src/repo_harness/verifier
```

如果 `tests/integration/test_verifier_micro_repos.py` 在本地环境因为依赖或 Docker 状态无法稳定运行，执行报告必须明确说明原因，并至少跑 verifier / reward 的单元测试替代验证。

## 12. 验收标准

Stage 7 完成时必须满足：

1. verifier worker pool 可以 blocking 执行 final verifier，并同步返回 reward。
2. `RepoHarnessEpisodeResult` 返回前已经有可解释的 reward 或明确 invalid 状态。
3. queue wait、worker id、pool id 可追踪，并进入 `TimingSummary` / `ResourceSummary`。
4. verifier timeout、verifier infrastructure error、parser low confidence 不会被误训为普通模型失败。
5. `test_command_error`、`dependency_error`、`verification_workspace_error`、`queue_timeout` 等错误类型有明确状态映射，并且默认不可训练。
6. worker pool 有真实 pending job 上限；没有拿到 verifier slot 时会结构化返回 `queue_timeout`，不能无限排队。
7. final verifier rejected 和 verifier infrastructure failure 被清晰区分。
8. reward metadata 和 hidden verifier 细节不会进入模型可见字段或训练 batch 可传播开放字段。
9. 所有新增字段都使用 Stage 1 的 schema / visibility 风格，默认禁止未知字段，开放字段使用明确 allowlist。
10. 不引入 `verl` import，不实现 Stage 10 converter，不实现 Stage 11 adapter。
11. 现有 Stage 0H 到 Stage 6 的目标回归测试仍然通过。

## 13. 明确不属于 Stage 7 的事项

下面这些事项必须留到后续阶段：

- Stage 8：训练预算、no-progress 控制、上下文瘦身和更细的 reward policy。
- Stage 9：跨 episode 并发安全、全局资源租约、分布式 worker pool 生命周期。
- Stage 10：`TrainingView` 到 `AgentLoopOutput` 的正式转换。
- Stage 11：`RepoHarnessVerlAgentLoop` 和 `VerlLLMGateway`。
- Stage 12：真实端到端 verl smoke、DataProto 和 TransferQueue 验收。
- Stage 13：fully async reward backfill、中断恢复、异步样本补偿。

如果实施中需要为这些阶段预留字段，必须只做 schema 兼容，不要提前改变运行语义。
