# Stage 13.0 执行计划：fully async 前置 contract hardening

本文是 Stage 13.0 的具体实施计划。它承接
`01-sequential-implementation-plan.md` 中的 Stage 13 总路线，用于在真正接入
verl fully async 训练路径之前，先固定异步 episode 生命周期、reward finality、样本身份、
资源租约和 visibility / batch gate 的安全 contract。

Stage 12.6 已经证明同步真实链路可以跑通：

```text
RepoHarness real_episode
-> route=verl 真实模型 rollout
-> final verifier
-> reward boundary
-> TrainingView
-> AgentLoopOutput
-> DataProto
-> trainer global step
```

Stage 13.0 的目标不是把这条链路直接改成 fully async，而是先回答一个更基础的问题：
当 rollout、verifier、reward、trainer 和 parameter synchronization 不再同步收口时，
什么样的样本才允许进入 policy loss，什么样的资源可以释放，什么样的迟到结果可以绑定回原样本。

## 1. 阶段边界

Stage 13.0 必须坚持下面边界：

- 不启动真实远端 GPU 训练。
- 不接入 `verl.experimental.fully_async_policy.fully_async_main` 的真实 trainer 主路径。
- 不实现 `RepoHarnessRuntime.start_episode(...)` 的完整可运行异步 facade；这属于 Stage 13.1。
- 不实现真实 trajectory resume。第一版只要求 schema 能表达 `resume_supported=false`、
  `resume_status=unsupported_in_stage13_1` 或等价结构化状态。
- 不修改 `reference/verl` 的 `RolloutSample` dataclass。Stage 13.0 只做接口 inventory 和 contract
  hardening；如果后续必须 patch verl，应该放到 Stage 13.2 的实施计划中单独说明。
- 不改变 Stage 0H 到 Stage 12.6 已经固定的 token、mask、log probability、route、
  generation record、response span 和 visibility 不变量。
- 不把 pending reward、provisional reward、stale reward、missing verifier evidence 或
  sample identity 不匹配的样本放入 formal online RL batch。
- 不把本机路径、hidden verifier、完整 reward metadata、ground truth、evaluator-only logs、
  hidden runtime directory 或完整 `AuditRef` 放入 DataProto、MessageQueue 或 batch 可传播字段。

Stage 13.0 通过后，只表示 fully async 所需的安全 contract 已经稳定，不能宣称
RepoHarness 已经完成 fully async agentic RL 链路。

## 2. 产物范围

### 2.1 建议新增或修改的代码模块

建议优先保持实现范围小而清晰：

```text
src/repo_harness/rl/async_contracts.py
src/repo_harness/rl/async_validation.py
src/repo_harness_verl/fully_async_inventory.py
tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py
tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py
tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py
tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py
tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py
```

如果实现时发现某些 helper 更适合放到已有模块中，可以按代码库现有边界调整，但要保持下面原则：

- `src/repo_harness/rl` 可以定义训练后端无关的 async contract 和 validator。
- `src/repo_harness_verl` 可以读取或投影 verl fully async 的接口形状，但不能让
  `src/repo_harness/rl` 直接 import `verl`。
- `reference/verl` 只作为只读接口来源。Stage 13.0 不应该修改 submodule。

### 2.2 建议新增 schema / contract

建议新增训练后端无关 schema，名称可以按实现时的代码风格调整：

```text
AsyncEpisodeStatus
AsyncEpisodeSnapshot
AsyncEpisodeHandleRef
AsyncEpisodeLifecycleFacts
ResumeCapability
SampleIdentity
RewardFinalityFacts
RewardBindingFacts
AsyncBatchEligibilityFacts
FullyAsyncInterfaceInventory
```

这些 schema 的语义建议如下。

`AsyncEpisodeStatus` 至少覆盖：

```text
created
queued
running
cancelling
cancelled
timeout
failed
final_verifier_running
final_verifier_completed
reward_finalized
cleanup_running
completed
orphaned
```

这不是替代现有 `RepoHarnessEpisodeResult.status`。它描述的是异步生命周期状态；
现有 `status=succeeded|failed|invalid|timeout|...` 仍然描述 episode 的最终业务结果。

`AsyncEpisodeSnapshot` 至少包含：

```text
episode_id
run_id
task_id
sample_attempt_id
async_status
episode_status
resource_lease_refs
audit_refs
created_at
updated_at
resume_supported
resume_status
cancel_requested
cleanup_status
orphan_diagnostics
```

`SampleIdentity` 至少包含：

```text
sample_id
sample_attempt_id
episode_id
run_id
task_id
dataset_uid
dataset_index
rollout_uid
uid
session_id
global_steps
min_global_steps
max_global_steps
policy_version
generation_record_digest
trajectory_digest
```

其中 `sample_attempt_id` 是 fully async 的关键字段。同一个 `episode_id` 可以因为重采样、
失败重试或恢复运行产生多个 attempt。迟到 reward、迟到 verifier 结果和 MessageQueue 中的样本
都必须绑定到正确的 `sample_attempt_id`，不能只靠 `episode_id` 判断。
`dataset_uid` 和 `dataset_index` 都是可选字段，但至少需要其中一个；`rollout_uid` 和 `uid`
也都是可选字段，但至少需要其中一个。这样 schema 实现时不会把“或”误当作字段名。
`min_global_steps` 和 `max_global_steps` 用来表达 fully async rollout 可能跨越的参数版本范围；
真实 verl fully async batch 会使用 `non_tensor_batch["min_global_steps"]` 和
`non_tensor_batch["max_global_steps"]` 计算 partial / staleness 统计，因此这两个事实不能只作为
后续附加字段临时出现。

`RewardFinalityFacts` 至少包含：

```text
reward_state
reward_score
reward_score_source
final_verifier_status
verifier_outcome
final_verifier_ref
reward_metadata_ref
reward_job_id
sample_attempt_id
trajectory_digest
generation_record_digest
finalized_at
invalid_reason
```

`reward_state` 建议覆盖：

```text
pending_verifier
final_verifier_running
final_verifier_completed
invalid_reward
cancelled
timeout
stale
rejected_by_visibility
```

formal online RL batch 只允许：

```text
reward_state=final_verifier_completed
reward_score_source=trusted_final_verifier
final_verifier_status=accepted 或 rejected
final_verifier_ref 非空 opaque ref
reward_metadata_ref 非空 opaque ref
reward_job_id 非空
sample_attempt_id 与 SampleIdentity 一致
trajectory_digest 与 TrainingView / GenerationRecord 事实一致
```

如果 `reward_score` 是非空数值，但缺少上述任意可信绑定，仍然必须拒绝进入有效 policy loss。

### 2.3 和现有 schema 的兼容策略

Stage 13.0 不能破坏 Stage 0H 到 Stage 12.6 的 fixture 和本地回归。建议采用下面兼容策略：

- 新增字段默认 optional，旧 canonical fixture 可以继续 roundtrip。
- formal async validation helper 必须显式调用，不能让旧离线 fixture 自动被当作 fully async 样本。
- 对现有同步 `RepoHarnessEpisodeResult`，可以通过 `verifier_summary`、`reward`、
  `audit_ref.important_artifact_refs` 和 `generation_records` 派生一个 `RewardFinalityFacts`，
  但派生结果必须写明 `derived_from_sync_episode=true` 或等价 diagnostics。
- 如果派生缺少 `final_verifier_ref` 或 `reward_metadata_ref`，则只能作为 diagnostic sample，
  不能进入 formal async online RL batch。
- `TrainingView` 仍然只承载 batch 可见 token、mask、logprob、reward score 和 flat extra fields。
  完整 finality facts、reward metadata、audit ref 和 verifier evidence 不能塞进
  `TrainingView.extra_fields`。

## 3. 实施顺序

### 3.1 Stage 13.0-0：verl fully async interface inventory

目标：先冻结当前 `reference/verl` 的 fully async 接口形状，避免后续 adapter 按抽象理解实现，
却和真实代码不一致。

建议新增 `src/repo_harness_verl/fully_async_inventory.py`，通过轻量 source inspection 生成 inventory。
第一版尽量不要 eager import `torch`、`ray`、`tensordict` 或完整 `verl` 依赖；可以读取源码文件、
解析文本或使用 `ast`。如果当前环境可以安全 import，再把 import 结果作为 optional diagnostics。

inventory 至少记录：

```text
reference_verl_commit
fully_async_main_module = verl.experimental.fully_async_policy.fully_async_main
FullyAsyncTaskRunner 类位置
FullyAsyncRollouter 类位置
MessageQueue / MessageQueueClient 类位置
RolloutSample dataclass 字段
FullyAsyncTrainer._fit_generate(...) 签名或源码位置
FullyAsyncTrainer._compute_old_log_prob(...) 签名或源码位置
actor_rollout_ref.actor.use_rollout_log_probs 配置路径
algorithm.rollout_correction.bypass_mode 配置路径
data.train_batch_size 语义：fully async 中应为 0
data.gen_batch_size 语义：fully async streaming 中应为 1
async_training.require_batches
async_training.trigger_parameter_sync_step
async_training.staleness_threshold
async_training.partial_rollout
```

验收测试建议：

```text
tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py
```

测试至少断言：

- inventory 不需要 import `repo_harness.rl` 以外的 heavy trainer 依赖。
- 能找到 `fully_async_main.py`、`fully_async_rollouter.py`、`message_queue.py`、
  `fully_async_trainer.py`。
- 能确认真实入口会通过 `FullyAsyncTaskRunner` 组装 `FullyAsyncRollouter`、
  `FullyAsyncTrainer` 和 `MessageQueue`。
- 能确认当前 `RolloutSample` 主要字段是 `full_batch`、`sample_id`、`epoch`、`rollout_status`。
- 能确认后续 RepoHarness facts 第一版应放在 `rollout_status` 或
  `DataProto.non_tensor_batch["repo_harness_*"]`，而不是默认直接修改 verl dataclass。

本步骤可以生成本地 evidence：

```text
runs/stage13_0-local-<timestamp>/fully_async_interface_inventory.json
```

### 3.2 Stage 13.0-1：SampleIdentity 和 attempt binding contract

目标：固定 fully async 中样本身份的最小事实链。

建议新增或修改：

```text
src/repo_harness/rl/async_contracts.py
src/repo_harness/rl/async_validation.py
```

需要实现：

- `SampleIdentity` schema。
- `compute_generation_record_digest(...)` helper。
- `compute_training_view_trajectory_digest(...)` helper。
- `validate_sample_identity_binding(...)` helper。
- `validate_late_reward_binding(...)` helper。

digest 计算要求：

- 使用稳定 JSON canonicalization，例如排序 key、固定 separators。
- digest 输入必须包含足够区分样本的事实，例如：
  - `episode_id`
  - `run_id`
  - `sample_attempt_id`
  - `prompt_ids` 或 `prompt_digest`
  - prompt / context revision，例如 `context_revision`、`raw_prompt_digest` 或等价模型可见上下文摘要
  - `response_ids`
  - `response_mask`
  - `response_logprobs` 的稳定表示
  - `response_spans`
  - `generation_records` 的 `model_call_id`、`output_token_ids`、`output_logprobs`、
    `gateway_route`、`min_global_steps`、`max_global_steps`
- 不能包含本机绝对路径、完整 reward metadata、hidden verifier 或 evaluator-only 字段。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py
```

测试至少覆盖：

- 同一个 `episode_id` 的两个不同 `sample_attempt_id` 会产生不同 binding。
- 相同 response token 但不同 `prompt_ids` 或不同 prompt digest 时，`trajectory_digest` 不同。
- 迟到 reward 的 `sample_attempt_id` 不匹配时被拒绝。
- 迟到 reward 的 `trajectory_digest` 不匹配时被拒绝。
- 只看 `episode_id` 不能通过 binding validator。
- digest 不包含本机绝对路径或 evaluator-only 字段。

### 3.3 Stage 13.0-2：RewardFinalityFacts 和 formal async batch gate

目标：把“有 reward 数值”和“可以进入 policy loss”彻底分开。

需要实现：

- `RewardFinalityFacts` schema。
- `RewardBindingFacts` 或等价 schema。
- `validate_reward_finality_for_policy_loss(...)` helper。
- `formal_async_online_rl_sample_from_episode_result(...)` 或等价 helper。
- `validate_formal_async_online_rl_batch(...)` helper。

正式 fully async online RL batch 需要同时满足：

```text
route=verl
response_logprobs 非空
response_ids / response_mask / response_logprobs 长度一致
generation_records 非空
response_spans 覆盖每个 response token
assistant_generation span 与 generation_records token / logprob 一致
TrainingView.online_rl_eligible=True
invalid_for_training=False
invalid_for_online_rl=False
RewardFinalityFacts.reward_state=final_verifier_completed
RewardFinalityFacts.reward_score_source=trusted_final_verifier
final_verifier_ref 非空 opaque ref
reward_metadata_ref 非空 opaque ref
reward_job_id 非空
SampleIdentity.sample_attempt_id 匹配
trajectory_digest 匹配
visibility scan 通过
```

以下样本必须拒绝：

- `reward_state=pending_verifier`。
- `reward_state=final_verifier_running`。
- `reward_state=timeout`。
- `reward_state=cancelled`。
- `reward_state=stale`。
- 有 `reward_score`，但没有 `final_verifier_ref`。
- 有 `reward_score`，但 `reward_score_source=provisional`、`provider_reported`、
  `heuristic` 或空值。
- `reward_job_id` 不匹配。
- `sample_attempt_id` 不匹配。
- `trajectory_digest` 不匹配。
- route 不是 `verl`。
- 缺少 `response_logprobs`。
- 缺少 `generation_records`。
- visibility rejected。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py
tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py
```

这些测试需要和现有 Stage 10 / Stage 12.5 formal validator 回归一起运行，确保没有打开旧洞口。

### 3.4 Stage 13.0-3：AsyncEpisodeSnapshot 和资源生命周期 diagnostics

目标：先让异步生命周期和资源释放状态有结构化表达，不要求马上提供真正可运行的
`start_episode(...)`。

需要实现：

- `AsyncEpisodeSnapshot` schema。
- `AsyncEpisodeLifecycleFacts` schema。
- `ResumeCapability` schema。
- cleanup deadline、recorder lock timeout、orphan diagnostics 字段。
- final audit writer / run directory lock 状态的 diagnostics 字段。

第一版 `resume` 语义：

```text
resume_supported=false
resume_status=unsupported_in_stage13_1
resume_ref=None
```

取消和 cleanup 语义：

- 如果底层同步 AgentLoop、工具、verifier 或 recorder 仍可能运行，snapshot 必须能表达
  `cleanup_status=waiting_for_worker` 或等价状态。
- 如果 verifier timeout 后底层 callable 仍运行，workspace lease 不能显示为已经安全释放。
- 如果 cleanup deadline 到期，必须记录 `orphaned` 或 `cleanup_failed` diagnostics，
  不能静默成功。
- final audit 写入完成前，同一个 `run_id` 不能被新 episode 复用。

验收测试建议：

```text
tests/unit/test_repo_harness_rl_stage13_0_async_lifecycle.py
```

测试至少覆盖：

- snapshot 可以表达 unsupported resume。
- cleanup deadline 到期时产生 diagnostics。
- final verifier 仍运行时，workspace lease 不能被标为 safely released。
- final audit 写入完成前，run directory single writer 仍保持占用。

### 3.5 Stage 13.0-4：Async queue / DataProto visibility hardening

目标：为 Stage 13.2 的 MessageQueue 接入提前固定 visibility 规则。

真实 `FullyAsyncRollouter` 会把 `RolloutSample` 放入 Ray actor 边界，Ray 会通过 cloudpickle
机制序列化该对象。因此 Stage 13.0 必须明确：visibility scan 发生在序列化前。
如果后续 validator 只能看到 opaque bytes，不能把它当成已经通过 visibility 检查。

需要实现或补强：

- async reward queue visibility validator。
- async result queue visibility validator。
- reward backfill ledger visibility validator。
- DataProto non-tensor batch / meta_info 的 fully async 附加字段检查。
- pre-serialization `RolloutSample` visibility scanner，至少检查：
  - `RolloutSample.full_batch.non_tensor_batch`
  - `RolloutSample.full_batch.meta_info`
  - `RolloutSample.rollout_status`
  - 其中携带的 `repo_harness_*` facts
- queue payload gate：只有带 `repo_harness_visibility_scan_status=passed` 或等价事实的样本
  才能进入 async queue；缺失 scan status 或 scan failed 的 payload 必须拒绝。

允许传播的字段应该继续使用 flat scalar 和 `repo_harness_*` namespace，例如：

```text
repo_harness_episode_id
repo_harness_run_id
repo_harness_task_id
repo_harness_sample_attempt_id
repo_harness_generation_record_digest
repo_harness_trajectory_digest
repo_harness_reward_state
repo_harness_reward_job_id
repo_harness_final_verifier_ref
repo_harness_reward_metadata_ref
repo_harness_visibility_scan_status
repo_harness_visibility_scan_digest
repo_harness_min_global_steps
repo_harness_max_global_steps
```

禁止传播：

```text
完整 AuditRef 对象
本机绝对路径
workspace path
run_dir path
hidden verifier
gold patch
ground_truth
完整 reward metadata
provider secret
evaluator-only logs
raw setup logs
hidden runtime directory
```

验收测试建议：

```text
tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py
```

测试至少覆盖：

- nested `ground_truth` 被拒绝。
- nested `reward_extra_info` 被拒绝。
- nested absolute path 被拒绝。
- `DataProto.meta_info` 中出现完整 `AuditRef` 被拒绝。
- `RolloutSample` 序列化前缺少 `repo_harness_visibility_scan_status=passed` 时被拒绝。
- 已经变成 opaque bytes 的 queue payload 不能被视为已扫描安全，除非外层有可信 scan digest。
- 合法 `repo_harness_*` opaque refs 和 flat scalar 被接受。

## 4. 本地 evidence

Stage 13.0 完成后建议生成：

```text
runs/stage13_0-local-<timestamp>/
  fully_async_interface_inventory.json
  sample_identity_contract_report.json
  reward_finality_contract_report.json
  async_lifecycle_contract_report.json
  async_visibility_contract_report.json
  stage13_0_acceptance_summary.json
```

`stage13_0_acceptance_summary.json` 至少记录：

- 当前代码提交哈希或 dirty 状态。
- `reference/verl` commit。
- 是否修改了 `reference/verl`，预期应为 false。
- Stage 13.0 新增测试结果。
- Stage 0H 到 Stage 12.6 关键回归结果。
- fully async interface inventory 的路径。
- 是否有 heavy import 依赖被普通 import 触发。
- 是否有未提交或未跟踪文件影响 evidence 可复现性。

本阶段不要求远端 GPU evidence。

## 5. 验收命令

实施完成后建议运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage13_0_sample_identity.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage13_0_fully_async_inventory.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py
```

还需要运行前置 contract 回归：

```bash
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
  tests/unit/test_repo_harness_rl_stage5_provider_gateway.py \
  tests/unit/test_workspace_reuse_stage6.py \
  tests/unit/test_verifier_worker_pool_stage7.py \
  tests/unit/test_repo_harness_rl_stage7_reward_boundary.py \
  tests/unit/test_repo_harness_rl_stage8_budget_policy.py \
  tests/unit/test_repo_harness_rl_stage9_resource_leases.py \
  tests/unit/test_repo_harness_rl_stage9_concurrency_runtime.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage11_gateway.py \
  tests/unit/test_repo_harness_verl_stage11_request_mapping.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py \
  tests/unit/test_repo_harness_verl_stage12a_local_preflight.py \
  tests/unit/test_repo_harness_rl_stage12_5_acceptance_contract.py \
  tests/unit/test_repo_harness_rl_stage12_5_dependency_environment.py \
  tests/unit/test_repo_harness_rl_stage12_5_command_environment.py \
  tests/unit/test_repo_harness_rl_stage12_5_formal_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage12_5_executor_limits.py \
  tests/unit/test_repo_harness_rl_stage12_5_verifier_pool_default.py \
  tests/unit/test_repo_harness_rl_stage12_5_tool_timing.py \
  tests/unit/test_repo_harness_verl_stage12_5_batch_refill.py \
  tests/unit/test_repo_harness_verl_stage12_5_transferqueue_visibility.py \
  tests/unit/test_workspace_reuse_stage12_5_fast_materialization.py
```

普通 import 验收：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY
```

verl import 边界扫描：

```bash
if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl; then
  exit 1
fi
```

文档和 diff 检查：

```bash
git diff --check -- \
  src/repo_harness/rl \
  src/repo_harness_verl \
  tests/unit \
  docs/agentic_RL/repo_harness_verl_workstreams/21-stage-13-0-execution-plan.md
```

## 6. 完成标准

Stage 13.0 可以标记完成，必须同时满足：

- 新增 async contract schema 可以 roundtrip。
- 旧 Stage 0H 到 Stage 12.6 fixture 和关键回归不被破坏。
- formal async online RL batch 会拒绝 pending reward、provisional reward、stale reward、
  missing verifier evidence、missing reward metadata、sample identity mismatch、
  trajectory digest mismatch 和 visibility rejected 样本。
- 同一个 `episode_id` 的多个 attempt 不会互相绑定 reward。
- `AsyncEpisodeSnapshot` 可以表达取消、超时、unsupported resume、cleanup deadline 和 orphan diagnostics。
- final verifier timeout 后的 workspace 生命周期 contract 有测试覆盖。
- final audit 写入完成前 run directory single writer contract 有测试覆盖。
- async queue、result queue、reward backfill ledger、DataProto non-tensor batch 和 meta_info 的
  visibility 负例有测试覆盖。
- fully async interface inventory 能记录当前 `reference/verl` 的真实入口、类、字段和关键配置。
- `src/repo_harness/rl` 不 import `verl`。
- `repo_harness_verl` 普通 import 不要求 `torch`、`ray`、`tensordict` 或 `reference/verl`。

## 7. 明确不做的事

Stage 13.0 不做：

- 不实现 `RepoHarnessRuntime.start_episode(...)` 的完整运行路径。
- 不启动 Ray。
- 不启动 SGLang 或 vLLM。
- 不运行远端 GPU。
- 不修改 `reference/verl`。
- 不接入 `MessageQueue` 的真实生产消费路径。
- 不做 parameter synchronization。
- 不实现真实 resume。
- 不实现 async reward backfill worker。
- 不声称完成 RepoHarness fully async 训练链路。

这些内容分别留给 Stage 13.1、Stage 13.2 和 Stage 13.3。
