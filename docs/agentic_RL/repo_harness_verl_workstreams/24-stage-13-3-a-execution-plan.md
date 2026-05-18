# Stage 13.3-A 执行计划：fully async runtime adapter 本地实现

本文是 Stage 13.3-A 的具体实施计划。它承接 `01-sequential-implementation-plan.md`
中 Stage 13.3-A 的高层路线，并建立在 Stage 13.0、Stage 13.1 和 Stage 13.2
已经完成的基础上。

Stage 13.3-A 的目标不是远端 GPU 训练，也不是证明真实 `FullyAsyncTrainer`
已经完成多步训练和参数同步。它的目标是：在本地补齐 RepoHarness 到 verl
fully async runtime 的 producer、MessageQueue 写入、trainer-side filtering 和资源生命周期
adapter，让 Stage 13.2 已经完成的样本结构桥接真正进入一个可执行的本地 runtime 路径。

## 1. 前置状态

Stage 13.0 已经固定：

```text
SampleIdentity
RewardFinalityFacts
FormalAsyncOnlineRLSample
formal async batch validator
trajectory digest / generation record digest 绑定
pending / stale / timeout / cancelled / visibility rejected 样本拒绝规则
```

Stage 13.1 已经提供：

```text
RepoHarnessRuntime.start_episode(...)
AsyncEpisodeHandle
AsyncEpisodeSnapshot
wait_result(timeout=...) 不取消底层 episode
cancel() 快速返回 snapshot
runtime.close() 下 real_episode 资源释放保护
run_id 单写入者保护
```

Stage 13.2 已经完成：

```text
RepoHarnessEpisodeResult
-> FormalAsyncOnlineRLSample
-> RepoHarnessFullyAsyncQueueFacts
-> RolloutSample.full_batch.non_tensor_batch
-> MessageQueue bytes payload visibility gate
-> DataProto assembly 前结构校验
-> trainer batch 前 valid sample selection helper
```

Stage 13.3-A 必须复用这些已有 contract 和 helper，不重新发明第二套 async sample
schema，也不能放松 Stage 0H 到 Stage 12.6 固定的 token、mask、log probability、
route、generation record、response span 和 visibility 不变量。

## 2. 当前 reference/verl 接口事实

Stage 13.3-A 仍然不直接启动 `fully_async_main`，但实现必须对齐当前
`reference/verl` 的真实接口形状。

当前 `reference/verl/verl/experimental/fully_async_policy/message_queue.py` 中：

```text
async MessageQueue.put_sample(sample: Any) -> bool
async MessageQueueClient.put_sample(sample: Any) -> bool
async MessageQueueClient.get_sample() -> tuple[Any | None, int]，用于正常队列样本和 termination signal
async MessageQueueClient.shutdown()
```

其中 `FullyAsyncRollouter._process_single_sample_streaming(...)` 会把
`RolloutSample` 序列化成 bytes 后调用：

```python
await self.message_queue_client.put_sample(sample=ray.cloudpickle.dumps(rollout_sample))
```

当前 `reference/verl/verl/experimental/fully_async_policy/fully_async_trainer.py`
中的 `_get_samples_from_queue(...)` 会：

```text
循环调用 message_queue_client.get_sample() 并解包为 (sample, queue_len)
直到收集到 required_samples 条 queue entry，或 sample is None 表示 termination signal
对非 None bytes 执行 ray.cloudpickle.loads(...)
调用 assemble_batch_from_rollout_samples(...)
```

当前 reference trainer 不会自动理解 RepoHarness 的 rejected / diagnostic 样本。
因此 Stage 13.3-A 第一版需要在 `src/repo_harness_verl` 中提供 trainer-side helper /
wrapper / adapter，在调用 reference assembly 或 fake trainer step 之前先筛选样本。

## 3. 本阶段目标

Stage 13.3-A 第一版需要完成下面本地闭环：

```text
task source / request source
-> RepoHarnessRuntime.start_episode(...)
-> AsyncEpisodeHandle.wait_result(...)
-> RepoHarnessEpisodeResult
-> build_queue_facts_from_episode_result(...)
-> attach_queue_facts_to_rollout_sample(...)
-> serialize_rollout_sample_for_message_queue(...)
-> fake or local MessageQueueClient.put_sample(...)
-> trainer-side sample filter
-> selected valid samples
-> local fake trainer step report
```

这个闭环应该证明：

- producer 能从本地任务源启动多个 async episode。
- producer 只在 episode 终态后生成 `RolloutSample`。
- MessageQueue payload 写入前后都经过 visibility gate。
- trainer-side filtering 不会把 invalid、partial、stale、visibility rejected、
  pending reward、cancelled、timeout 或 diagnostic 样本计入 `required_samples`。
- 本地 fake trainer step 只消费 valid samples。
- 参数版本 facts 和 stale 统计可以解释样本的参数版本窗口。
- producer 取消、queue 写入失败、trainer filter 失败时不会泄漏 workspace、run directory、
  hidden runtime directory、recorder lock 或 async handle。

## 4. 阶段边界

Stage 13.3-A 应该做：

- 新增 RepoHarness fully async producer / queue / trainer-side filtering 的本地 adapter。
- 使用 Stage 13.1 的 `RepoHarnessRuntime.start_episode(...)` 和 `AsyncEpisodeHandle`。
- 使用 Stage 13.2 的 `RepoHarnessFullyAsyncQueueFacts`、
  `build_queue_facts_from_episode_result(...)`、
  `attach_queue_facts_to_rollout_sample(...)`、
  `serialize_rollout_sample_for_message_queue(...)`、
  `deserialize_message_queue_payload(...)`、
  `validate_rollout_sample_for_trainer_batch(...)` 和
  `select_valid_rollout_samples_for_required_count(...)`。
- 提供 fake `MessageQueueClient` 或本地 in-memory queue，用于模拟 reference
  `put_sample(...)`、`get_sample()`、`shutdown()` 的行为。
- 提供 trainer-side selection helper，明确输出 selected valid samples 和 rejection report。
- 提供本地参数版本时钟或 fake trainer control loop，用于构造 fresh / stale / post-sync-like
  样本分类，不宣称真实 `update_weights(...)` 已经发生。
- 生成本地 evidence report，说明 producer、queue、filter、参数版本、partial/stale
  和资源生命周期结果。

Stage 13.3-A 不应该做：

- 不启动远端 GPU 实例。
- 不运行真实多步 `FullyAsyncTrainer`。
- 不要求真实模型收敛。
- 不宣称真实 parameter synchronization 已经完成。
- 不把普通 `main_ppo` 或 `actor_rollout_ref.rollout.mode=async` 当成 RepoHarness
  fully async 完成。
- 不默认修改 `reference/verl`。
- 不直接修改 `RolloutSample` dataclass。
- 不让 partial rollout、pending reward、stale trajectory、timeout、cancelled、
  missing logprobs、non-verl route 或 visibility rejected 样本进入 policy loss。

如果实施过程中发现必须修改 `reference/verl` 的 queue consumption、rollout sample path
或 trainer sample path，必须先暂停 Stage 13.3-A 实现，补充设计说明，列出：

```text
需要修改的 reference/verl 文件
修改原因
兼容性测试
回退方式
是否影响 Stage 13.3-B 远端 smoke
```

## 5. 建议新增模块

建议新增：

```text
src/repo_harness_verl/fully_async_runtime.py
```

这个模块属于 `repo_harness_verl`，因为它面向 verl fully async runtime adapter。
它不应该放进 `repo_harness.rl` core，也不应该让 `repo_harness.rl` import `verl`、
`ray`、`torch` 或 `tensordict`。

建议在 `fully_async_runtime.py` 中提供以下结构。具体名称可以在实现时按现有代码风格微调。

### 5.1 `RepoHarnessFullyAsyncProducerConfig`

职责：描述本地 producer loop 的 runtime-only 配置。

建议字段：

```text
required_samples
max_queue_backlog
producer_concurrency
episode_wait_timeout_seconds
queue_put_timeout_seconds
current_global_steps
staleness_threshold
partial_rollout_supported
partial_rollout_status
visibility_scan_status
visibility_scan_digest
serializer
```

要求：

- `required_samples > 0`。
- `max_queue_backlog >= required_samples`。
- `partial_rollout_supported` 第一版默认 `false`。
- `visibility_scan_status="passed"` 时必须有 `visibility_scan_digest`。
- 这些配置是 runtime adapter 配置，不进入 `TrainingView`、`AgentLoopOutput`
  或 DataProto batch 的非 namespaced 字段。

### 5.2 `RepoHarnessFullyAsyncProducerResult`

职责：记录 producer loop 的本地执行结果。

建议字段：

```text
started_episode_count
completed_episode_count
cancelled_episode_count
timeout_episode_count
queue_put_success_count
queue_put_failure_count
produced_sample_count
valid_candidate_count
rejected_candidate_count
diagnostic_candidate_count
queue_size_after_produce
producer_diagnostics
```

要求：

- 每个 `AsyncEpisodeHandle` 的终态必须可追踪到 `run_id`、`episode_id`
  和 `sample_attempt_id`。
- queue 写入失败不能吞掉 episode result，必须保留 diagnostic。
- producer cancellation 后必须等待或确认资源安全释放。

### 5.3 `InMemoryFullyAsyncMessageQueueClient`

职责：作为本地 fake MessageQueue client，模拟当前 reference `MessageQueueClient`
的最小行为。

建议方法：

```python
async def put_sample(self, sample: bytes | None) -> bool
async def get_sample(self) -> tuple[bytes | None, int]
async def get_queue_size(self) -> int
async def get_statistics(self) -> dict[str, object]
async def shutdown(self) -> None
```

行为要求：

- `put_sample(None)` 表示 termination signal。
- `get_sample()` 返回 `(sample, queue_len)`，与 reference trainer 当前调用形状一致。
- queue 满时第一版可以拒绝写入并返回 `False`，也可以按 reference 行为丢弃 oldest；
  但必须在 report 中记录 `dropped_samples` 或 `queue_put_failure_count`。
- `put_sample(None)` 是 termination signal，必须即使队列已满也能入队并唤醒 consumer；
  如果因此丢弃 oldest，需要记录 `dropped_samples`，不能因为队列满而拒绝 termination signal。
- fake queue 不应该绕过 Stage 13.2 的 bytes payload visibility gate。

### 5.4 `run_fully_async_producer_loop(...)`

职责：从 episode request / task source 启动 async episode，并把终态样本写入 queue。

建议输入：

```python
runtime: RepoHarnessRuntime
requests: Sequence[RepoHarnessEpisodeRequest]
llm_gateway_factory 或 llm_gateway
message_queue_client
producer_config
rollout_sample_factory
```

第一版可以接受已经构造好的 request 列表和 fake gateway；不要求实现真实 dataset
sampler 或 Ray rollouter。

执行规则：

1. 对每个 request 调用 `RepoHarnessRuntime.start_episode(...)`。
2. 调用 `AsyncEpisodeHandle.wait_result(...)` 获取终态结果。
3. 终态结果必须先经过 Stage 13.2 queue facts 构造。只有被 queue facts 分类为
   valid candidate 的样本才进入 formal async validator。
4. rejected / diagnostic 样本必须保留 queue facts、rejection reason 和 lifecycle diagnostic；
   不能因为 formal validator 失败而被吞掉，也不能计入 `required_samples`。
5. Stage 13.3-A 本地 fake queue 可以把 rejected / diagnostic payload 放入 backlog，
   用于验证 trainer-side filter；但进入真实 policy-loss MessageQueue 的路径，必须在
   reference assembly 前过滤，或者把 rejected / diagnostic 放入 diagnostic side channel /
   report。不能让真实 `FullyAsyncTrainer` 把 rejected queue entry 计入 `required_samples`。
6. valid / rejected / diagnostic 样本都可以进入 queue diagnostics；只有 valid 样本可以被
   trainer-side filter 计入 `required_samples`。
7. 每个写入 queue 的 payload 必须经过
   `serialize_rollout_sample_for_message_queue(...)`。
8. producer loop 被取消时，已启动 handle 必须调用 `cancel()` 或等待终态，并记录 lifecycle
   diagnostics。
9. producer 不得在 wait timeout 时把 pending handle 伪造成 terminal sample。

### 5.5 `select_valid_samples_from_message_queue(...)`

职责：模拟 trainer 从 queue 读取 samples，然后筛选出本地 fake trainer step 可消费的
valid samples。

建议行为：

1. 循环调用 `message_queue_client.get_sample()`。
2. 遇到 `None` termination signal 时停止。
3. 对 bytes payload 调用
   `deserialize_message_queue_payload(payload, visibility_scan_status=..., visibility_scan_digest=...)`。
   visibility scan ledger 必须来自 producer、fake queue sidecar 或等价可信外部记录，
   不能反序列化后再从 payload 内部自证。
4. 对 rollout sample 调用 `validate_rollout_sample_for_trainer_batch(...)`。
5. 使用 `select_valid_rollout_samples_for_required_count(...)` 或等价逻辑选择 valid samples。
6. trainer-side helper 不能在读取到 `required_samples` 条原始 queue entry 后停止；
   它必须继续读取，直到 selected valid sample count 达到 `required_samples`，或遇到
   termination signal、max dequeue limit 或 timeout。
7. invalid、partial、stale、visibility rejected、pending reward、timeout、cancelled、
   diagnostic 样本只能进入 rejection report，不能计入 valid sample count。
8. 如果 valid sample 不足，返回 `insufficient_valid_samples=true`，不能用坏样本补齐。

### 5.6 `FakeFullyAsyncTrainerStepReport`

职责：表达本地 fake trainer step 的结果，不伪装成真实 verl trainer step。

建议字段：

```text
required_samples
selected_valid_sample_count
selected_sample_ids
current_global_steps
next_global_steps
current_param_version
next_param_version
stale_sample_count
filtered_stale_sample_count
partial_rejected_count
visibility_rejected_count
pending_reward_rejected_count
real_policy_loss_executed
fake_selection_step_executed
policy_loss_execution_mode
```

要求：

- Stage 13.3-A 第一版必须设置 `real_policy_loss_executed=false`。
- 可以额外记录 `fake_selection_step_executed=true` 和
  `policy_loss_execution_mode=fake_local_selection_only`。
- 真实 policy loss、真实 parameter synchronization 和真实 global step 属于 Stage 13.3-B。

## 6. 参数版本和 stale 样本策略

Stage 13.3-A 不要求真实 `update_weights(...)`，但必须让版本 facts 变得可测试。

建议实现一个本地 fake parameter clock：

```text
current_global_steps
current_param_version
trigger_parameter_sync_step
staleness_threshold
```

本地测试至少构造：

- fresh valid sample：`max_global_steps` 与 `current_global_steps` 差距不超过阈值。
- stale sample：`current_global_steps - max_global_steps > staleness_threshold`。
- post-sync-like sample：fake parameter clock 前进后产生的新 sample，版本窗口能解释为新参数版本之后的样本。

Stage 13.3-A 的 report 应明确：

```text
stale_sample_count
filtered_stale_sample_count
current_global_steps
next_global_steps
current_param_version
next_param_version
trajectory_param_versions 或等价 repo_harness_* 字段
```

注意：这些只是本地 adapter-side 版本事实模拟，不代表真实 `FullyAsyncTrainer`
已经完成 parameter synchronization。

## 7. partial rollout 第一版策略

Stage 13.3-A 第一版继续固定：

```text
partial_rollout_supported=false
partial_rollout_status=unsupported_in_stage13_3_a 或 partial
```

要求：

- partial trajectory、resume-required trajectory、incomplete episode 都不能进入 policy loss。
- partial 样本必须有明确 rejection reason，例如
  `partial_rollout_unsupported_in_stage13_3_a`。
- 不在 Stage 13.3-A 实现 resume。
- 如果 `AsyncEpisodeHandle.snapshot()` 表示 pending / running / cancelling，不能把它转换成
  terminal `RolloutSample`。

## 8. visibility 和 audit 边界

Stage 13.3-A 必须继续执行以下检查：

- `RolloutSample` 序列化前 visibility。
- MessageQueue bytes payload visibility。
- 反序列化后 scan ledger 与内部 batch 字段逐项一致。
- DataProto non-tensor batch / meta_info visibility。
- 可传播 report 中不能出现本机绝对路径、完整 `AuditRef`、hidden verifier、
  完整 reward metadata、ground truth、gold patch、provider secret 或 evaluator-only log。

本地 evidence 可以保留 runtime-private raw diagnostics，但必须标记为本地私有；
`stage13_3a_acceptance_summary.json` 中只能放可传播、安全、脱敏字段。

## 9. 本阶段测试计划

建议新增测试文件：

```text
tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py
tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py
tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py
tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

### 9.1 Producer loop 测试

必须覆盖：

- producer 调用 `RepoHarnessRuntime.start_episode(...)`，而不是直接调用同步
  `run_episode(...)`。
- terminal `RepoHarnessEpisodeResult` 被转换成 `RolloutSample` 并写入 queue。
- pending handle 不会被转换成 sample。
- `wait_result(timeout=...)` 超时不会产生 terminal sample。
- queue put failure 返回结构化 diagnostic，不吞掉 episode result。
- producer cancellation 会取消或等待已启动 handles，并记录 cleanup diagnostics。

### 9.2 MessageQueue filtering 测试

必须构造超过 `required_samples` 的 backlog，例如：

```text
required_samples = 2
queue payloads = [
  valid,
  invalid_for_training,
  invalid_missing_logprobs,
  invalid_non_verl_route,
  partial,
  stale,
  visibility_rejected_or_malformed_visibility_payload,
  pending_reward_or_pending_finality,
  cancelled,
  timeout,
  diagnostic,
  valid
]
```

断言：

- selected valid samples 只有两个 valid 样本。
- invalid / missing logprobs / non-verl route / partial / stale / visibility rejected /
  pending reward 或 pending finality / cancelled / timeout / diagnostic 都不计入 valid sample count。
- rejected reasons 中保留每个 rejected sample 的原因。
- 如果 valid 样本不足，返回 insufficient report，不能用 rejected 样本补齐。

### 9.3 参数版本测试

必须覆盖：

- fresh sample 通过。
- `current_global_steps - max_global_steps > staleness_threshold` 的样本被拒绝。
- fake parameter clock 前进后，report 中能看到 `current_param_version` 或等价字段变化。
- post-sync-like 样本写入后，`trajectory_param_versions`、`min_global_steps`、
  `max_global_steps` 或等价 `repo_harness_*` 字段可解释。

### 9.4 partial rollout 测试

必须覆盖：

- `partial_rollout_supported=false` 时 partial 样本被拒绝。
- `partial_rollout_status` 和 rejection reason 进入 report。
- incomplete episode / pending snapshot 不能生成 terminal `RolloutSample`。

### 9.5 资源生命周期测试

必须覆盖：

- producer loop 取消后，没有 active handle 泄漏。
- queue 写入失败后，run directory lock 和 workspace lease 能释放。
- fake queue shutdown 后，producer 不继续写入无界 backlog。
- `runtime.close()` 后 producer helper 不再启动新 episode。

## 10. 本地 evidence

Stage 13.3-A 实施完成后，建议生成本地 evidence 目录，例如：

```text
runs/stage13_3a-local-<timestamp>/
```

建议文件：

```text
stage13_3a_command_log.jsonl
stage13_3a_local_adapter_report.json
stage13_3a_message_queue_filter_report.json
stage13_3a_parameter_version_report.json
stage13_3a_resource_lifecycle_report.json
stage13_3a_visibility_report.json
stage13_3a_acceptance_summary.json
```

`stage13_3a_acceptance_summary.json` 至少包含：

```text
repo_harness_commit
reference_verl_commit
dirty_worktree
producer_loop_passed
message_queue_filter_passed
required_samples
selected_valid_sample_count
rejected_sample_count
diagnostic_sample_count
stale_sample_count
filtered_stale_sample_count
partial_rejected_count
visibility_rejected_count
resource_lifecycle_passed
acceptance_ready
blocking_issues
```

如果工作区未提交或存在未跟踪 Stage 13.3-A 实现文件，`acceptance_ready` 必须为 `false`。

## 11. 验收命令

实施完成后至少运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

同时运行 Stage 13.0 到 Stage 13.2 目标回归：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_lifecycle.py \
  tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py \
  tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py \
  tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_2_message_queue.py \
  tests/unit/test_repo_harness_verl_stage13_2_reference_interface.py \
  tests/unit/test_repo_harness_verl_stage13_2_staleness_and_refill.py \
  tests/unit/test_repo_harness_verl_stage13_2_trainer_batch_visibility.py
```

运行关键前置回归：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_repo_harness_rl_stage12_5_command_environment.py \
  tests/unit/test_repo_harness_rl_stage12_5_dependency_environment.py
```

普通 import 和 verl import 边界检查：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
import repo_harness.rl
import repo_harness_verl
loaded = set(sys.modules)
for name in ("torch", "ray", "tensordict", "verl"):
    assert name not in loaded, f"ordinary import loaded heavy dependency: {name}"
print("ordinary_import_ok")
PY

if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl src/repo_harness/agent_loop src/repo_harness/workspace src/repo_harness/verifier; then
  exit 1
fi
```

文档和实现空白检查：

```bash
git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/24-stage-13-3-a-execution-plan.md \
  src/repo_harness_verl \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

## 12. 通过标准

Stage 13.3-A 只有在下面条件同时满足时才能标记完成：

- 本地 producer loop 能通过 `RepoHarnessRuntime.start_episode(...)` 启动 episode，
  等待终态，并生成 queue payload。
- fake MessageQueue backlog 同时包含 valid、invalid、missing logprobs、non-verl route、
  partial、stale、visibility rejected、pending reward 或 pending finality、cancelled、
  timeout 和 diagnostic 样本。
- trainer-side filter 只选择 valid 样本，且 valid sample count 满足 `required_samples`。
- rejected / diagnostic 样本不会进入 policy loss，也不会被计入 required sample count。
- sample identity、reward finality、generation record digest、trajectory digest 和
  queue facts 绑定一致。
- 参数版本 facts 和 stale 统计在本地 fake parameter clock 下可解释。
- partial rollout 第一版被明确拒绝，并且不实现 resume。
- producer cancellation、queue failure、filter failure 和 runtime close 不造成资源泄漏。
- visibility gate 覆盖 pre-serialization、MessageQueue payload、DataProto-like batch
  和可传播 evidence。
- `repo_harness.rl` core 不 import `verl`。
- Stage 13.0 到 Stage 13.2 目标回归继续通过。

Stage 13.3-A 通过后，只能说明本地 fully async runtime adapter 和 trainer-side
filtering 路径准备好。真实 GPU、多步 `FullyAsyncTrainer`、parameter synchronization
和 post-sync 新样本写入仍然属于 Stage 13.3-B。
