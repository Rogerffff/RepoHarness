# Stage 13.2 执行计划：接入 verl fully async Rollouter / MessageQueue 结构路径

本文是 Stage 13.2 的具体实施计划。它承接 `01-sequential-implementation-plan.md`
中 Stage 13.2 的高层路线，并建立在 Stage 13.0 和 Stage 13.1 已完成的基础上：

```text
Stage 13.0:
  fully async contract hardening
  sample identity / reward finality / formal async batch validator
  reference/verl fully async interface inventory

Stage 13.1:
  RepoHarnessRuntime.start_episode(...)
  AsyncEpisodeHandle
  wait_result / cancel / close / snapshot 生命周期
  real_episode 资源释放边界
```

Stage 13.2 的目标不是远端 GPU 训练，也不是让完整 `fully_async_main` 跑完训练步。
它的目标是把 RepoHarness 已有的异步 episode 结果，安全投影到 verl
`fully_async_policy` 的 `RolloutSample -> MessageQueue -> DataProto` 样本流中，
先证明结构、字段、可见性、样本身份和 reward finality 绑定都正确。

## 1. 前置状态

Stage 13.1 已完成并提交：

```text
5cb5e807 feat: add stage13 async episode facade
```

Stage 13.1 已经提供：

- `RepoHarnessRuntime.start_episode(...)`
- `AsyncEpisodeHandle`
- `AsyncEpisodeState`
- `AsyncEpisodeStartError`
- `AsyncEpisodeSnapshot` runtime 投影
- 同一 `run_id` 单写入者保护
- `wait_result(timeout=...)` 不取消底层 episode
- `cancel()` 和 `runtime.close()` 的结构化取消结果
- `real_episode` close 后 workspace lease 正常释放

Stage 13.2 必须复用 Stage 13.0 / Stage 13.1 的 contract，不重新定义另一套
fully async sample schema。

## 2. 当前 reference/verl 接口事实

根据 Stage 13.0 的 inventory 和当前 `reference/verl` 源码，Stage 13.2 需要以如下
接口事实为准。

### 2.1 真实入口

fully async 的真实入口是：

```text
python -m verl.experimental.fully_async_policy.fully_async_main
```

Stage 13.2 不应该把普通 `main_ppo` 加 `actor_rollout_ref.rollout.mode=async`
误写成 RepoHarness fully async 接入完成。

### 2.2 RolloutSample 字段

当前 `reference/verl/verl/experimental/fully_async_policy/detach_utils.py`
中的 `RolloutSample` 字段为：

```text
full_batch
sample_id
epoch
rollout_status
```

因此第一版不要直接修改 `RolloutSample` dataclass。RepoHarness 的 sample identity、
trajectory digest、reward finality、visibility scan status 等事实应通过下面两条路径投影：

```text
full_batch.non_tensor_batch["repo_harness_*"]
rollout_status["repo_harness_*"]
```

其中：

- 每个样本自己的字段优先放在 `full_batch.non_tensor_batch`。
- 聚合或队列可观察字段可以放在 `rollout_status`。
- 进入 `rollout_status` 的字段最终可能被 `assemble_batch_from_rollout_samples(...)`
  加上 `fully_async/` 前缀后进入 `DataProto.meta_info`，所以仍必须通过 visibility 检查。

### 2.3 MessageQueue 序列化方式

当前 `FullyAsyncRollouter._process_single_sample_streaming(...)` 会执行：

```python
await self.message_queue_client.put_sample(
    sample=ray.cloudpickle.dumps(rollout_sample),
)
```

当前 `FullyAsyncTrainer._get_samples_from_queue(...)` 会从 `MessageQueue` 取出 bytes，
然后执行：

```python
queue_samples = [ray.cloudpickle.loads(x) for x in queue_samples]
batch = assemble_batch_from_rollout_samples(queue_samples, ...)
```

这意味着 Stage 13.2 必须同时覆盖两个边界：

1. `RolloutSample` 在序列化前必须经过 visibility 和 formal async eligibility 检查。
2. 已序列化 bytes 进入 queue 时，外层必须带可信的 `repo_harness_visibility_scan_status`
   和 `repo_harness_visibility_scan_digest` 或等价 ledger fact。

## 3. 本阶段目标

Stage 13.2 第一版需要完成下面闭环：

```text
RepoHarnessEpisodeResult
-> FormalAsyncOnlineRLSample
-> repo_harness_* flat queue facts
-> RolloutSample.full_batch.non_tensor_batch / rollout_status
-> pre-serialization visibility gate
-> MessageQueue payload gate
-> DataProto assembly 后 visibility gate
-> valid sample count / refill eligibility
```

这个闭环可以使用本地结构测试、fake MessageQueue client 和 lightweight DataProto stand-in 完成。
如果本地环境具备 `reference/verl` 所需依赖，可以增加真实 `RolloutSample` / `DataProto`
兼容测试；如果缺少 `torch`、`ray` 或 `tensordict`，真实 import 测试必须清楚标记为
dependency preflight skipped，不能用假对象冒充真实 fully async trainer 已经跑通。

## 4. 阶段边界

Stage 13.2 应该做：

- 新增 RepoHarness 到 fully async `RolloutSample` / `MessageQueue` 的 projection helper。
- 使用 Stage 13.0 的 `SampleIdentity`、`RewardFinalityFacts`、
  `FormalAsyncOnlineRLSample` 和 formal async batch validator。
- 把 RepoHarness 的可传播事实投影为 `repo_harness_*` namespaced flat 字段。
- 对 `RolloutSample` 序列化前、queue payload、DataProto non-tensor batch 和 meta_info
  做 visibility 检查。
- 验证 pending、cancelled、timeout、stale、missing logprobs、non-verl route、
  visibility rejected 样本不会计入 valid sample count。
- 记录 `actor_rollout_ref.actor.use_rollout_log_probs`、
  `algorithm.rollout_correction.bypass_mode`、
  `async_training.require_batches`、
  `async_training.staleness_threshold`、
  `async_training.partial_rollout` 等配置事实。

Stage 13.2 不应该做：

- 不启动远端 GPU 实例。
- 不运行真实多步 fully async trainer。
- 不要求模型收敛。
- 不改 `reference/verl` submodule。
- 不直接修改 `RolloutSample` dataclass，除非实施中发现无法通过非侵入方式完成结构 smoke；
  如果必须 patch，应先暂停并单独写出补充设计。
- 不把 pending reward、provisional reward、stale reward、timeout、cancelled、
  missing verifier evidence 或 sample identity 不匹配的样本放进有效 policy loss。
- 不把完整 `AuditRef`、本机绝对路径、hidden verifier、完整 reward metadata、
  ground truth、evaluator-only logs 或 provider secret 放进 MessageQueue / DataProto。

Stage 13.2 通过后，只能说明本地 fully async 样本流结构已经准备好。只有 Stage 13.3
远端最小 fully async smoke 通过后，才能说 RepoHarness 完成第一版 verl fully async
agentic RL 链路 smoke。

## 5. 建议新增模块

建议新增：

```text
src/repo_harness_verl/fully_async_bridge.py
```

这个模块属于 `repo_harness_verl`，因为它面向 verl fully async 样本流，不应该放进
训练后端无关的 `repo_harness.rl` core。

建议提供下面 helper，具体名称可以按实现时的代码风格调整。

### 5.1 `RepoHarnessFullyAsyncQueueFacts`

建议定义一个 `StrictBaseModel`，只包含可以传播到 queue / batch 的安全字段。

建议字段：

```text
schema_version
sample_id
sample_attempt_id
episode_id
run_id
task_id
dataset_uid
dataset_index
rollout_uid
uid
global_steps
min_global_steps
max_global_steps
policy_version_ref 或 policy_version_digest
generation_record_digest
trajectory_digest
reward_state
reward_score_source
final_verifier_status
reward_job_id
visibility_scan_status
visibility_scan_digest
final_verifier_ref
reward_metadata_ref
audit_manifest_ref
valid_for_policy_loss
sample_classification
rejection_reason
staleness
partial_rollout_supported
partial_rollout_status
invalid_reason
```

限制：

- 只能输出 flat scalar 或 opaque ref。
- 不能输出结构化 `AuditRef`。
- 不能输出完整 reward metadata。
- 不能输出本机路径。
- 不能输出 hidden verifier、gold patch、ground truth 或 evaluator-only 内容。

### 5.2 `build_queue_facts_from_episode_result(...)`

输入：

```python
RepoHarnessEpisodeResult
SampleIdentity
RewardFinalityFacts
```

输出：

```python
RepoHarnessFullyAsyncQueueFacts
```

实现要求：

- 必须先执行 sample classification，生成 `valid`、`rejected` 或 `diagnostic` facts。
- 只有 valid candidate 才构造或接收 `FormalAsyncOnlineRLSample`，并调用
  `validate_formal_async_online_rl_batch(...)`。
- 被拒绝样本也可以生成 rejected facts、audit reason 和可见性安全的 queue diagnostics，
  但 `valid_for_policy_loss` 必须是 `false`。
- 只有 `reward_state=final_verifier_completed` 且 final verifier / reward metadata 绑定可信的样本，
  才允许标记为 `sample_classification=valid`。
- final verifier rejected 但 verifier evidence 可信的样本，可以作为 negative training sample；
  它不能被误归类为 infrastructure failure。
- pending、cancelled、timeout、stale、visibility rejected、missing logprobs、non-verl route
  样本必须被分类为 diagnostic / rejected sample，不能计入 valid sample count。

### 5.3 `attach_queue_facts_to_rollout_sample(...)`

输入：

```python
rollout_sample
RepoHarnessFullyAsyncQueueFacts
```

行为：

- 把每个样本自己的 `repo_harness_*` 字段写入 `rollout_sample.full_batch.non_tensor_batch`。
- 把聚合可观察字段写入 `rollout_sample.rollout_status`。
- 写入前必须保证 batch 维度一致。如果 `full_batch` 长度不是 1，必须明确处理 repeat 后的
  per-row 值，不能只写一个 Python 标量后让 DataProto 隐式扩展。
- 写入后必须调用 `validate_pre_serialization_rollout_sample_visibility(...)`。

建议第一版只支持单样本 `RolloutSample`。如果 `len(full_batch) > 1`，可以返回结构化错误或
显式按长度重复字段，但不能静默写错。

### 5.4 `serialize_rollout_sample_for_message_queue(...)`

目标是把 visibility gate 固定在 queue 前。

建议语义：

```text
RolloutSample
-> validate_pre_serialization_rollout_sample_visibility(...)
-> cloudpickle / serializer
-> validate_fully_async_queue_payload_visibility(bytes, scan_status, scan_digest)
-> bytes
```

第一版可以不强依赖 `ray.cloudpickle`。如果本地没有 Ray，可使用 `cloudpickle` 或
标准 `pickle` 做结构测试，并在报告中写明 serializer。实现时应优先使用 `cloudpickle`；
标准 `pickle` 只能作为最低限度 bytes gate 负例和形状测试，不得作为 Ray 序列化兼容证据。
真实 Ray 序列化兼容测试可以作为 dependency preflight。

### 5.5 `validate_rollout_sample_for_trainer_batch(...)`

目标是在 Trainer 从 queue 取出样本并组 `DataProto` 前再做一次检查。

它至少要校验：

- `repo_harness_visibility_scan_status=passed`
- `generation_record_digest` 存在且格式安全
- `trajectory_digest` 存在且格式安全
- `reward_state=final_verifier_completed`
- `reward_score_source=trusted_final_verifier`
- `final_verifier_ref` 和 `reward_metadata_ref` 是 opaque ref
- 不是 stale / pending / cancelled / timeout / visibility rejected
- 对应 `FormalAsyncOnlineRLSample` 通过 `validate_formal_async_online_rl_batch(...)`

这一步不能只看 `reward_score` 是否存在。

## 6. DataProto 和 batch 组装边界

Stage 13.2 必须特别注意 `assemble_batch_from_rollout_samples(...)` 的行为。

当前 reference/verl 里它会：

```text
1. 对每个 RolloutSample 调用 addition_process(rs.full_batch)
2. DataProto.concat(...)
3. 如果缺 response_mask，则调用 compute_response_mask(...)
4. 把 rollout_status 加上 fully_async/ 前缀写入 meta_info
5. 根据 non_tensor_batch["min_global_steps"] / ["max_global_steps"] 计算 partial 统计
```

其中 `addition_process(rs.full_batch)` 会读取并弹出 `full_batch.meta_info["metrics"]`，
并要求每条 metrics 记录至少包含：

```text
generate_sequences
tool_calls
```

如果 Stage 13.2 做真实 reference assembly 兼容测试，`full_batch.meta_info["metrics"]`
必须存在，并且每条记录必须包含上面两个字段。缺少 `metrics` 时不能伪装成真实 assembly
通过；合法 metrics 应该能正确投影为 `non_tensor_batch["processing_times"]` 和
`non_tensor_batch["tool_calls_times"]`。

因此 Stage 13.2 需要保证：

- RepoHarness 的 `response_mask` 已经存在时不能被重新计算成错误值。
- `rollout_log_probs` / `response_logprobs` provenance 不能丢。
- `min_global_steps` 和 `max_global_steps` 必须存在并与 `SampleIdentity` 一致。
- `rollout_status` 被加上 `fully_async/` 前缀后，仍不能包含 hidden evaluator 字段或本机路径。
- `meta_info["reward_extra_keys"]` 不能携带完整 reward metadata 键或 evaluator-only 路径。
- DataProto concat / select / pop / meta_info 传播后仍要通过 visibility 检查。

第一版可以使用已有 `repo_harness_verl.visibility.validate_dataproto_visibility(...)`
和新增 helper 做检查。必要时应补充 Stage 10 / Stage 13.0 visibility helper 的负例测试。

## 7. staleness、partial rollout 和 refill 策略

Stage 13.2 不实现真实 parameter synchronization，也不实现真实 partial rollout resume。
但是必须固定本地结构策略。

### 7.1 staleness

建议第一版定义：

```text
staleness = current_global_steps - max_global_steps
```

如果超过 `async_training.staleness_threshold`：

- 样本进入 diagnostic / rejected 分类。
- `reward_state` 可以是 `stale` 或 `invalid_reward`，但不能伪装成 final verifier completed valid sample。
- 不计入 valid sample count。

### 7.2 partial rollout

Stage 13.2 不把 partial trajectory 放入 policy loss。

如果 `async_training.partial_rollout=True`，第一版只记录配置事实和 unsupported diagnostics：

```text
partial_rollout_supported=false
partial_rollout_status=unsupported_in_stage13_2
```

partial trajectory 必须被拒绝进入 formal batch，除非未来阶段实现完整 resume 和 reward finality 绑定。

### 7.3 refill / resample

第一版默认 owner 仍在 `repo_harness_verl` trainer helper / batch collector 侧。
RepoHarness core 只提供 sample classification、formal validator 和 audit facts。

valid sample count 只能统计：

```text
reward_state=final_verifier_completed
formal async validator passed
visibility_scan_status=passed
route=verl
response_logprobs present
sample identity and reward finality binding matched
not stale
not partial
```

当前 reference trainer 的 `_get_samples_from_queue(...)` 是先按
`required_samples = actor.ppo_mini_batch_size * async_training.require_batches`
收集 queue payload bytes，然后再反序列化并组 batch。因此 Stage 13.2 的 adapter /
batch collector 必须在反序列化后继续按 valid sample count 过滤和补样。pending、timeout、
stale、visibility rejected、missing logprobs、non-verl route 等 payload 只能进入
diagnostics 或 rejected sample report，不能因为已经占用了 MessageQueue slot 就满足
trainer 所需的有效样本数。

## 8. 测试计划

建议新增测试文件：

```text
tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py
tests/unit/test_repo_harness_verl_stage13_2_message_queue.py
tests/unit/test_repo_harness_verl_stage13_2_trainer_batch_visibility.py
tests/unit/test_repo_harness_verl_stage13_2_staleness_and_refill.py
tests/unit/test_repo_harness_verl_stage13_2_reference_interface.py
```

### 8.1 fully async bridge 测试

覆盖：

- 从可信 `RepoHarnessEpisodeResult` 构造 `RepoHarnessFullyAsyncQueueFacts`。
- `generation_record_digest` 和 `trajectory_digest` 与 `SampleIdentity` 一致。
- final verifier accepted 和 final verifier rejected 都可以成为 valid sample，前提是 evidence 可信。
- pending verifier、cancelled、timeout、stale、missing logprobs、non-verl route 被拒绝。
- forged `trajectory_digest`、forged `generation_record_digest`、错误 `sample_attempt_id`
  被 formal async gate 拒绝。

### 8.2 MessageQueue payload 测试

覆盖：

- 序列化前缺少 `repo_harness_visibility_scan_status=passed` 时拒绝。
- 已序列化 bytes 缺少 scan status / digest 时拒绝。
- 嵌套 `ground_truth`、`reward_extra_info`、hidden verifier、本机绝对路径在
  `non_tensor_batch`、`meta_info` 或 `rollout_status` 中均被拒绝。
- 合法 opaque refs 通过。
- fake MessageQueue client 只接受通过 visibility gate 的 payload。

### 8.3 Trainer batch / DataProto visibility 测试

覆盖：

- 多个合法 sample 拼 batch 后，`non_tensor_batch` 中的 `repo_harness_*` 字段长度与 batch size 对齐。
- 真实 reference assembly 兼容测试中，缺少 `meta_info["metrics"]` 必须失败，不能伪装成
  `assemble_batch_from_rollout_samples(...)` 已通过。
- 合法 `meta_info["metrics"]` 中的 `generate_sequences` 和 `tool_calls` 能正确进入
  `non_tensor_batch["processing_times"]` 和 `non_tensor_batch["tool_calls_times"]`。
- `min_global_steps`、`max_global_steps` 存在并可计算 staleness / partial stats。
- `response_mask`、`rollout_log_probs`、`rm_scores` 形状正确。
- DataProto `meta_info` 中 `fully_async/repo_harness_*` 或其他 visibility facts 不泄漏本机路径。
- DataProto concat / select / pop 后再次运行 visibility 检查。

### 8.4 staleness / refill 测试

覆盖：

- stale 样本不计入 valid sample count。
- pending reward 样本不计入 valid sample count。
- cancelled / timeout 样本不计入 valid sample count。
- final verifier rejected 且 evidence 可信的 negative sample 可以计入 valid sample count。
- valid sample 不足时，batch collector 返回 refill needed，而不是把 invalid 样本补进去。

### 8.5 reference interface 测试

覆盖：

- 继续使用 Stage 13.0 inventory，确认 `RolloutSample` 字段没有漂移。
- 确认 `MessageQueue.put_sample`、`MessageQueueClient.put_sample`、
  `FullyAsyncTrainer._fit_generate` 的签名没有漂移。
- 如果本地依赖足够，增加 optional real import smoke；如果缺依赖，必须输出清晰 skipped reason。

## 9. 验收命令

建议本地验收命令：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src
```

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_2_message_queue.py \
  tests/unit/test_repo_harness_verl_stage13_2_trainer_batch_visibility.py \
  tests/unit/test_repo_harness_verl_stage13_2_staleness_and_refill.py \
  tests/unit/test_repo_harness_verl_stage13_2_reference_interface.py
```

前置目标回归：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py \
  tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py \
  tests/unit/test_repo_harness_verl_stage12_5_batch_refill.py \
  tests/unit/test_repo_harness_verl_stage12_5_transferqueue_visibility.py \
  tests/unit/test_repo_harness_verl_stage12_5_dataproto_padding.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py
```

普通 import 边界：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
before = {name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules}
import repo_harness.rl
import repo_harness_verl
after = {name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules}
print("ordinary_import_ok", sorted(before), sorted(after))
PY
```

RepoHarness core 不得 import verl：

```bash
if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl; then
  exit 1
fi
```

格式检查：

```bash
git diff --check -- \
  src/repo_harness_verl \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_2_message_queue.py \
  tests/unit/test_repo_harness_verl_stage13_2_trainer_batch_visibility.py \
  tests/unit/test_repo_harness_verl_stage13_2_staleness_and_refill.py \
  tests/unit/test_repo_harness_verl_stage13_2_reference_interface.py \
  docs/agentic_RL/repo_harness_verl_workstreams/23-stage-13-2-execution-plan.md
```

## 10. Evidence 建议

Stage 13.2 是本地结构 smoke，不要求生成远端 GPU evidence bundle。
但如果实现中生成本地报告，建议目录形如：

```text
runs/stage13-2-local-<timestamp>/
```

建议文件：

```text
stage13_2_acceptance_summary.json
fully_async_bridge_report.json
message_queue_visibility_report.json
dataproto_batch_projection_report.json
staleness_and_refill_policy_report.json
reference_interface_inventory_report.json
stage13_2_command_log.jsonl
```

这些文件如果包含本机路径，只能作为本地私有 evidence；进入 summary 的可传播字段必须脱敏。

## 11. 完成标准

Stage 13.2 完成需要同时满足：

1. RepoHarness 的 `RepoHarnessEpisodeResult` 可以转换为 formal async queue facts。
2. queue facts 只能包含 `repo_harness_*` flat scalar 和 opaque refs。
3. `RolloutSample` 序列化前 visibility gate 能拒绝 hidden evaluator 字段和本机路径。
4. MessageQueue bytes payload 必须有可信 visibility scan status / digest。
5. DataProto assembly 后的 non-tensor batch 和 meta_info 继续通过 visibility 检查。
6. pending、cancelled、timeout、stale、missing logprobs、non-verl route、visibility rejected
   样本不能进入 valid sample count。
7. final verifier rejected 且 evidence 可信的样本可以作为 negative training sample。
8. `actor_rollout_ref.actor.use_rollout_log_probs` 和 `algorithm.rollout_correction.bypass_mode`
   的配置事实被记录，不能关闭 rollout logprob provenance。
9. Stage 13.0 / Stage 13.1 目标回归通过。
10. `src/repo_harness/rl` 仍不 import `verl`，普通 `import repo_harness_verl`
    不拉起 heavy trainer dependencies。

完成 Stage 13.2 后，仍然不能宣称 fully async 训练链路已经打通。下一阶段 Stage 13.3
才会在远端 GPU 上运行最小真实 fully async smoke，验证真实 Rollouter、MessageQueue、
Trainer、parameter synchronization 和 RepoHarness async episode facade 共同工作。
