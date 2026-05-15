# Shared Contract 04：Timing 与 Resource

本文档定义 RepoHarness 为支持训练吞吐分析、环境复用和并发 episode 运行所需的 timing 与 resource contract。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0
scope: planning_only_not_current_implementation
```

## 1. 设计目标

当前测评结论显示，使用 DeepSeek V4 Pro thinking mode 顺序生成轨迹时，主要瓶颈是模型调用等待，其次是每条任务独立 Docker setup、baseline 和 final verifier 的固定成本。

因此，RepoHarness 接入 online reinforcement learning 前，需要把耗时拆清楚：

```text
轨迹慢，是模型调用慢？
还是 Docker setup 慢？
还是 verifier 慢？
还是 artifact 写入慢？
还是上下文准备和大文件读取导致下一轮 prompt 变慢？
```

第一版 contract 先要求每条 episode 都产出结构化 `TimingSummary`，再在 training_fast 阶段逐步优化。

注意：`TimingSummary` 不应该只在 episode 外层打一个 wall clock。RepoHarness 现有结构里已经有多种事件级耗时来源：

- `TrajectoryEvent.duration_ms` 可以承载工具、workspace、verifier、artifact 等事件耗时。
- `ModelCallEvent.duration_ms` 可以承载模型调用耗时。
- workspace command result 中已经有命令执行耗时和 timeout 事实。

第一版实现应该优先汇总这些已有事实，再补充缺失阶段的计时。

## 2. TimingSummary

```text
TimingSummary
  schema_version
  contract_version
  rollout_wall_seconds
  queue_wait_seconds
  workspace_materialization_seconds
  docker_setup_seconds
  baseline_verifier_seconds
  agent_loop_seconds
  model_call_seconds
  context_prepare_seconds
  tool_seconds
  verifier_seconds
  final_verifier_seconds
  reward_compute_seconds
  artifact_write_seconds
  cleanup_seconds
  model_call_count
  tool_call_count
  verifier_call_count
  artifact_count
  artifact_bytes_written
```

字段解释：

- `rollout_wall_seconds`：从 episode 开始到 result 构造完成的总 wall clock。
- `queue_wait_seconds`：后续 fully async 或 worker pool 中等待资源的时间，第一版普通 agent loop 可以为 `0`。
- `workspace_materialization_seconds`：source checkout、snapshot restore、copy-on-write workspace 创建等耗时。
- `docker_setup_seconds`：依赖安装、Docker setup 或 dependency state 恢复耗时。
- `baseline_verifier_seconds`：baseline verifier 耗时。
- `agent_loop_seconds`：模型与工具多轮交互的总耗时。
- `model_call_seconds`：所有模型调用等待时间总和。
- `context_prepare_seconds`：准备 messages、压缩上下文、写 ModelInputSnapshot 等耗时。
- `tool_seconds`：工具执行总耗时，不含模型调用。
- `final_verifier_seconds`：最终验证器耗时。
- `artifact_write_seconds`：写 transcript、events、artifact、manifest 的近似耗时。
- `cleanup_seconds`：容器、工作区、临时文件清理耗时。

## 3. ResourceSummary

```text
ResourceSummary
  schema_version
  contract_version
  execution_mode
  workspace_backend
  worker_id
  host_id
  snapshot_key
  snapshot_cache_hit
  snapshot_restore_strategy
  dependency_state_key
  dependency_cache_hit
  baseline_cache_hit
  container_reuse_hit
  docker_image_id
  docker_image_digest
  docker_volume_ids
  docker_resource_limits_effective
  network_policy
  permission_policy_ref
  workspace_path
  run_dir
  concurrency_group
  lease_id
  verifier_worker_pool_id
  verifier_worker_id
  queue_wait_seconds_by_resource
  cleanup_status
```

用途：

- 判断不同 worker 是否复用了同一个 snapshot。
- 判断并发 episode 是否写入了独立 workspace 和 run directory。
- 定位 Docker volume、workspace cache 或 artifact path 污染问题。
- 判断 workspace snapshot、dependency cache、baseline cache 和 warm container 复用是否命中，以及是否仍保持 clean-state 语义。
- 证明 Docker-based executable repository environment、权限策略、网络策略、worker pool 和资源复用没有绕过当前 RepoHarness 的边界。

说明：

- `network_policy` 记录训练 episode 的网络访问策略，例如禁用、受限或允许的范围。它不是生产级安全沙箱承诺，只是可审计的运行事实。
- `permission_policy_ref` 指向本次 episode 使用的权限策略或 policy manifest。
- `docker_resource_limits_effective` 记录实际生效的 CPU、memory、timeout、volume、mount 等限制。
- `lease_id` 用于跟踪 snapshot、Docker volume、dependency cache 或 verifier worker pool 的资源租约。
- `queue_wait_seconds_by_resource` 用于拆分等待模型、workspace、verifier worker、Docker daemon 或 artifact writer 的排队耗时。

## 4. BudgetState

`EpisodeRequest.budgets` 是输入配置；episode result 中还需要输出实际预算消耗：

```text
BudgetConsumption
  max_turns
  used_turns
  max_wall_seconds
  used_wall_seconds
  max_model_call_seconds
  used_model_call_seconds
  max_tool_calls
  used_tool_calls
  max_artifact_bytes
  used_artifact_bytes
  stop_reason
```

要求：

- 如果停止原因是 no-progress，必须在 `stop_reason` 和 diagnostics 中同时体现。
- 如果停止原因是 provider timeout，不能直接当成模型语义失败。
- 如果停止原因是 verifier timeout，应由 reward metadata 标记是否 `invalid_for_training`。

## 5. 并发安全 contract

RepoHarness 不需要在第一版实现完整 rollout scheduler；verl 负责 rollout 调度。但 RepoHarness runtime 必须可以被多个 episode 并发调用。

最低要求：

1. 每条 episode 有唯一 `episode_id` 和 `run_id`。
2. 每条 episode 写独立 `run_dir`。
3. 每条 episode 使用隔离 `workspace_path`。
4. `RunRecorder` 锁只能保护单个 run directory，不能作为全局并发控制。
5. Docker volume、snapshot cache、dependency cache 如果共享，必须只读或通过 lease 管理。
6. cleanup 失败必须写入 diagnostics，不能静默吞掉。
7. provider、workspace、verifier 和 artifact writer 可以各自有 concurrency limit。
8. `RunRecorder` 现有锁可以防止同一个 run directory 被两个进程同时写入，但不能证明 workspace、Docker volume 或 snapshot cache 没有污染；这些资源必须有独立隔离策略。

## 6. 环境复用 contract

training_fast 阶段可以引入环境复用，但必须保持 clean-state 语义。

建议 snapshot key：

```text
snapshot_key:
  repo_ref
  base_commit
  environment_id
  docker_image_digest
  setup_command_hash
  dependency_lock_hash
  toolchain_version
  harness_version
```

复用策略：

```text
snapshot_restore:
  从只读 clean snapshot 恢复。

copy_on_write:
  每条 episode 只写自己的派生 workspace。

dependency_state_ref:
  记录依赖状态来源，支持审计和复现。
```

禁止：

- 多条 episode 共享同一个可写工作区。
- 把上一个 rollout 的测试输出、临时文件、patch 或缓存状态暴露给下一个 rollout。
- 在没有 hash / ref 记录的情况下复用环境。

## 7. verifier worker pool contract

第一版 verifier 优化可以做 worker pool，但仍然必须等待 reward 返回。

```text
verifier_execution_strategy:
  blocking_in_episode
  worker_pool_blocking
```

`worker_pool_blocking` 的语义：

```text
episode 提交 final verifier
  -> verifier worker 执行
  -> episode await verifier result
  -> compute reward
  -> return EpisodeResult
```

它不是：

```text
episode 先返回无 reward sample
  -> verifier 后补 reward
```

后者需要 fully async 阶段另行设计。

## 8. 第一版不变量

1. 每条 episode 必须输出 `TimingSummary`，即使失败也要输出已知耗时。
2. 基础设施失败必须和模型失败分开记录。
3. 环境复用不能破坏 clean workspace 和 final verifier 可信度。
4. verifier worker pool 第一版必须 blocking wait，不能 silent reward backfill。
5. verl 兼容 timing 字段可以进入 `TrainingView.verl_metrics`，RepoHarness 详细 timing 字段必须通过 `extra_fields` 的 compact 引用或 `audit_ref` 指向完整 artifact。
6. timing summary 必须能区分模型等待、工具执行、Docker setup、baseline verifier、final verifier、artifact 写入和 context prepare，不能只输出总耗时。
