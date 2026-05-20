# Stage 15.1 执行计划：本地 partial rollout adapter 和 resume scheduler

## 1. 阶段定位

Stage 15.1 的目标是在本地、同进程、fake queue / fake trainer 环境中实现第一版 RepoHarness partial rollout adapter。它要证明下面这条链路在代码层面成立：

```text
RepoHarness episode 在安全 turn boundary 暂停
-> 生成 PartialEpisodeCheckpoint
-> checkpoint 进入 resume queue / diagnostic side channel
-> resume scheduler 在同一 runtime ownership scope 内恢复原始 AsyncEpisodeHandle
-> episode 继续执行到 final verifier / reward finality
-> 终态样本通过 formal online RL / formal async validator
-> valid completed sample 进入 policy-loss candidate queue
```

这一阶段仍然不是远端 GPU smoke，也不是正式接入 `reference/verl` 的真实 `partial_rollout=True` 参数同步中断路径。Stage 15.1 的价值是把 RepoHarness 自己的 partial checkpoint / resume / queue gate 行为做成稳定本地组件，为 Stage 15.2 远端真实 `partial_rollout=True` smoke 做准备。

Stage 15.1 必须继承 Stage 15.0 的关键结论：

```text
verl 原生 partial_rollout=True:
  当前更多发生在 CheckpointEngineManager / rollout server / FullyLLMServerClient 层。
  abort / aborted 可能被 FullyLLMServerClient 内部自动续生成消费。
  它不能直接等同于 RepoHarness PartialEpisodeCheckpoint。

RepoHarness PartialEpisodeCheckpoint:
  只能在 RepoHarness 安全 turn boundary 生成。
  必须绑定 live AsyncEpisodeHandle、ResumeStateStore、workspace lease、recorder cursor、generation records、tool observation projection、visibility digest 和 durable writer lease。
```

## 2. 前置状态

Stage 15.0 已经完成接口盘点和本地 evidence：

```text
commit: fd0150fc
message: feat: add stage15 partial rollout inventory
evidence: runs/repo-harness-verl-stage15-0-20260520T120647Z/
```

Stage 14.2 已经固定 partial checkpoint contract：

```text
commit: d9c589ae
message: feat: add stage14.2 partial checkpoint contract
```

Stage 14.3 已经实现本地同进程 turn-boundary pause / resume facade：

```text
commit: eed69eb3
message: feat: add stage14.3 pause resume facade
```

Stage 13.3-A 已经有本地 fake MessageQueue、trainer-side selection、parameter version facts 和 queue visibility ledger：

```text
src/repo_harness_verl/fully_async_runtime.py
src/repo_harness_verl/fully_async_bridge.py
```

Stage 15.1 必须复用这些已有能力，不重新定义 checkpoint schema，不绕过 formal async validator，也不把 partial checkpoint 塞进 `AgentLoopOutput`、`DataProto` 或 policy-loss MessageQueue。

## 3. 非目标

Stage 15.1 不做：

```text
不启动远端 GPU
不运行真实 fully_async_main
不启用真实 async_training.partial_rollout=True 远端训练
不修改 reference/verl
不 patch FullyAsyncRollouter / FullyAsyncTrainer / MessageQueue
不实现跨进程、跨 Ray actor、跨机器或 worker 崩溃后的 durable resume
不支持 KV cache resume
不支持模型请求中、工具执行中、final verifier 执行中、reward 写入中或 cleanup 执行中的热迁移
不把 PartialEpisodeCheckpoint 本身当作 trainable sample
不放松 route、logprob、generation record、response span、reward finality、visibility、path leak 和 audit ref 边界
```

如果 Stage 15.1 发现必须修改 `reference/verl` 才能完成本地目标，应停止并更新计划；真正的 reference patch 应进入 Stage 15.2 或单独 follow-up。

## 4. 建议新增模块和职责

建议新增：

```text
src/repo_harness_verl/partial_rollout.py
```

该模块只属于 adapter / local runtime helper 层，不进入 `repo_harness.rl` core。RepoHarness core 继续提供通用的 `AsyncEpisodeHandle`、`PartialEpisodeCheckpoint`、`ResumeStateStore`、formal batch validator 和 `TrainingView` schema。

建议新增的主要对象：

```text
PartialRolloutProducerConfig
PartialRolloutRequest
PartialRolloutQueueItem
PartialRolloutDiagnostic
PartialRolloutProducerReport
ResumeSchedulerConfig
ResumeSchedulerReport
ResumeAttemptFacts
PolicyLossGateReport
InMemoryPartialResumeQueue
InMemoryPartialDiagnosticChannel
RepoHarnessPartialRolloutProducer
RepoHarnessResumeScheduler
```

这些对象的职责如下：

- `RepoHarnessPartialRolloutProducer`：启动或接管本地 `AsyncEpisodeHandle`，在受控 turn boundary 请求 pause，把生成的 `PartialEpisodeCheckpoint` 写入 resume queue，而不是 policy-loss queue。
- `InMemoryPartialResumeQueue`：本地同进程 resume queue，只保存 batch-safe metadata、opaque handle ref、checkpoint digest、resume token 和 runtime-private handle binding；不持久化本机绝对路径。
- `InMemoryPartialDiagnosticChannel`：记录无法 resume、不可训练、stale、visibility rejected、timeout、cancelled、missing logprob、non-verl route 等样本。
- `ResumeSchedulerConfig`：必须包含 `resume_wait_timeout_seconds` 和 `resume_cancel_wait_timeout_seconds`，禁止 scheduler 无限等待恢复后的 episode。
- `RepoHarnessResumeScheduler`：从 resume queue 读取 checkpoint，验证同 runtime ownership 和 `ResumeStateStore` entry，然后调用 `AsyncEpisodeHandle.resume(...)`，使用有界 `wait_result(timeout=...)` 等待终态 result，并只把终态 valid completed sample 交给 policy-loss source gate。
- `PolicyLossGateReport`：记录哪些样本被选择、哪些被拒绝、拒绝原因、是否进入 policy-loss candidate queue。

## 5. partial rollout producer 语义

producer 第一版只支持受控 turn-boundary pause。建议测试中使用 Stage 14.3 已有的 fake gateway / fixture，让 episode 至少完成一轮工具调用后 pause。

producer 的基本流程：

```text
1. 调用 RepoHarnessRuntime.start_episode(...)
2. 记录 runtime ownership scope、run_id、episode_id、sample_attempt_id
3. 调用 handle.request_pause_at_next_turn_boundary(...)
4. 等待 PauseOutcome
5. 如果 outcome.status=paused 且 checkpoint 存在：
     - 校验 validate_partial_checkpoint_for_resume_preparation(...)
     - 校验 checkpoint 不能进入 policy loss
     - 写入 partial resume queue
     - 写入 producer ledger
6. 如果 pause timeout / cancelled / terminal before pause：
     - 写入 diagnostic side channel
     - 不写入 policy-loss queue
```

这里的 `pause_timeout` 必须特别小心。Stage 14.3 中 `request_pause_at_next_turn_boundary(timeout=...)` 的 timeout 只表示“调用方等待暂停结果超时”，不表示底层 pause request 已被撤销。也就是说，pause request 仍然可能在后续 turn boundary 触发 checkpoint。

因此 Stage 15.1 producer 必须采用下面两种语义之一，不能让 producer 返回后留下无人管理的 pending pause：

```text
推荐默认语义：
  pause timeout 后，producer 调用 handle.cancel(reason=stage15_1_pause_timeout)
  并进行有界 wait_result(...)，直到 terminal cancelled / diagnostic 收口，
  或者记录 cleanup_running / cancelling diagnostic。
  该路径必须证明不会有延迟 checkpoint 入队。

允许的替代语义：
  pause timeout 后，producer 不结束 ownership，
  而是把 handle 保留在 producer active ledger 中，
  状态记录为 pause_pending，
  后续 checkpoint 到达时仍由同一个 producer / scheduler 接管。
```

第一版建议使用“timeout 后取消并有界等待”的语义，因为它更容易证明不会产生脱离 producer ledger 的延迟 checkpoint。

producer 必须记录：

```text
checkpoint_id
content_digest
trajectory_digest
generation_record_digest
run_id
episode_id
sample_attempt_id
handle_ref
resume_token
lease_token_digest
recorder_cursor_digest
visibility_scan_digest
current_param_version_at_pause
min_global_steps_at_pause
max_global_steps_at_pause
partial_rollout_status
diagnostic_reason
```

其中 `handle_ref` 和 `resume_token` 是 runtime-only opaque 值，不能进入 `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields`、DataProto 或可传播 batch 字段。

## 6. resume queue 和同 ownership 约束

Stage 15.1 的 resume queue 必须绑定同一个 runtime ownership scope。它不能只靠 checkpoint schema 通过就恢复。

进入 resume 的最低条件：

```text
checkpoint schema roundtrip 通过
checkpoint.content_digest 与 queue item 记录一致
checkpoint.run_id 与 queue item 一致
checkpoint_id 与 queue item 一致
ResumeStateStore 中存在同一 checkpoint entry
AsyncEpisodeHandle 仍然 live
handle_ref 指向当前 runtime registry 中的 active handle
lease_token / recorder_cursor_digest / generation_record_digest 一致
workspace facts、source snapshot facts 和 workspace lease state 一致
checkpoint 状态是 resume_preparation 或等价安全状态
writer lease 仍属于当前 runtime
```

缺少任意条件时：

```text
不能尝试 resume
不能进入 policy-loss queue
必须进入 diagnostic side channel
```

要特别覆盖下面几类负例：

```text
合法 schema 但缺少 ResumeStateStore entry
合法 schema 但 live handle 不存在
合法 schema 但 handle_ref 属于另一个 runtime
checkpoint content_digest 被篡改
lease_token mismatch
recorder_cursor_digest mismatch
generation_record_digest mismatch
workspace facts mismatch
checkpoint 已经被消费过
同一个 checkpoint 被重复 resume
```

## 7. resume scheduler 语义

resume scheduler 的目标不是让 partial checkpoint 进入训练，而是把 partial checkpoint 恢复成终态 episode。

基本流程：

```text
1. 从 InMemoryPartialResumeQueue 读取 queue item
2. 校验 checkpoint 和 runtime ownership
3. 调用 handle.resume(checkpoint)
4. 使用 handle.wait_result(timeout=resume_wait_timeout_seconds) 有界等待终态结果
5. 如果终态 result succeeded / failed 且 reward finality 完整：
     - 重新计算 terminal sample 的 trajectory digest
     - 构造 formal online RL sample / formal async sample
     - 通过 policy-loss source gate 后写入 valid completed queue
6. 如果 terminal result timeout / cancelled / infrastructure_error / invalid / stale：
     - 写入 diagnostic side channel
     - 不写入 policy-loss queue
```

resume 后等待终态结果不能无限阻塞。`ResumeSchedulerConfig` 必须至少包含：

```text
resume_wait_timeout_seconds
resume_cancel_wait_timeout_seconds
```

如果 `handle.wait_result(timeout=resume_wait_timeout_seconds)` 超时，scheduler 必须：

```text
1. 将该 resume attempt 标记为 resume_timeout。
2. 调用 handle.cancel(reason=stage15_1_resume_timeout) 或等价取消路径。
3. 使用 resume_cancel_wait_timeout_seconds 做有界等待。
4. 如果取消收口完成，记录 terminal cancelled / timeout diagnostic。
5. 如果取消仍未完成，记录 cancelling / cleanup_running diagnostic，并保留 active handle 状态。
6. 不把该样本写入 policy-loss candidate queue。
7. 不留下不可解释的 run_id lock、workspace lease 或 active handle 泄漏。
```

测试必须证明：resume 后底层 episode 不返回时，scheduler 会结构化拒绝该样本；该样本不会进入 policy-loss queue；同一个 `run_id` 要么可以重试，要么被明确记录为仍处于 cancelling / cleanup_running diagnostic，而不是静默卡死。

resume scheduler 必须生成 `resume_attempt_id`。第一版建议格式：

```text
<checkpoint_id>:resume-attempt-<n>
```

每个 checkpoint 最多只能有一个成功消费的 resume attempt。失败 attempt 可以保留在 diagnostic report 中，但不能被重复计算成 policy-loss sample。

## 8. policy-loss source gate

Stage 15.1 的 gate 必须只允许“resume 后终态、完整、可训练、可见性通过、非 stale”的样本进入 policy-loss candidate queue。

必须拒绝：

```text
PartialEpisodeCheckpoint 本身
pending reward
partial_rollout_status != complete / not_requested
missing response_logprobs
mixed route
non-verl route
empty response
overflow
visibility rejected
stale
cancelled
timeout
infrastructure_error
invalid_task
missing final verifier outcome
missing reward metadata ref
missing generation records
generation_records 和 TrainingView token 不一致
```

可信 final verifier rejected 的终态样本可以是 trainable negative，但必须满足：

```text
route=verl
logprob 完整
token provenance 完整
reward_state=final
final_verifier_status=rejected
reward_score 为负向或低分
invalid_for_training=false
invalid_for_online_rl=false
visibility scan passed
```

如果 Stage 15.1 暂时不专门构造 trainable negative，可以只确保这条逻辑没有被破坏，不把它作为本阶段必须远端证明的条件。

## 9. staleness、global steps 和参数版本

resume 后必须重新计算全局训练步数窗口。不能直接复用 checkpoint 产生时的旧 `trajectory_digest` 或旧 `max_global_steps` 作为终态样本 freshness 依据。

这里要区分两个事实：

```text
global steps:
  用来计算 staleness。
  Stage 13.2 / 13.3-A 现有口径是 current_global_steps - max_global_steps。

param version:
  用来记录参数同步事实和版本窗口。
  它不能替代 current_global_steps 参与 staleness 判定。
```

建议 scheduler 在每次 resume terminal result 上记录：

```text
source_partial_checkpoint_id
resume_attempt_id
current_global_steps_at_resume
current_global_steps_at_terminal
current_param_version_at_resume
current_param_version_at_terminal
trajectory_param_versions
min_global_steps
max_global_steps
staleness
staleness_threshold
staleness_status
```

如果：

```text
current_global_steps_at_terminal - max_global_steps > staleness_threshold
```

或现有 helper 的等价 staleness 规则判定过期，则：

```text
episode 可以完成
reward 可以记录
但样本不能进入 policy loss
必须进入 stale diagnostic report
```

## 10. queue 和 selector 关系

Stage 15.1 可以复用 Stage 13.3-A 的 fake MessageQueue 和 `select_valid_samples_from_message_queue(...)`，但要保持两条队列分离：

```text
partial resume queue:
  放 PartialEpisodeCheckpoint / resume request / diagnostic control
  不被 fake trainer 直接消费

policy-loss candidate queue:
  只放 resumed completed valid sample
  可被 fake trainer selector 消费
```

这里要区分两类测试队列，不能混在一起：

```text
gate-produced policy-loss candidate queue:
  只能由 Stage 15.1 source gate 写入。
  只允许 resumed completed valid sample。
  不允许出现 partial、stale、visibility rejected、timeout 或 diagnostic 样本。

adversarial selector backlog:
  由测试手工构造，用来复用 Stage 13.3-A selector 的防御性校验。
  可以故意放入 partial disguised as complete、stale、visibility rejected、timeout 和 diagnostic entry。
  这只是负例测试输入，不能代表真实 source gate 的输出。
```

selector 仍必须满足 Stage 13.3-A 的规则：

```text
不能读取 required_samples 条原始 entry 就停止
必须继续读取直到 selected valid sample count 达到 required_samples
或遇到 termination signal / max dequeue limit / timeout
```

测试必须构造：

```text
resume queue 中有 valid checkpoint、tampered checkpoint、missing store checkpoint、duplicate checkpoint
gate-produced policy-loss candidate queue 中只有 valid completed
adversarial selector backlog 中有 valid completed、partial disguised as complete、stale、visibility rejected、timeout、diagnostic
required_samples=2
selector 最终只选择 2 个 valid completed samples
```

## 11. reference/verl 兼容边界

Stage 15.1 默认不修改 `reference/verl`，但必须根据 Stage 15.0 patch plan 做本地兼容测试。

至少需要验证：

```text
如果 future wrapper 要拦截 FullyAsyncRollouter -> MessageQueue 的 source gate，
那么本地 policy-loss candidate queue 产物必须能被 Stage 13.2 RolloutSample / DataProto bridge 接受。
```

也就是说，Stage 15.1 的 terminal valid sample 必须能走：

```text
RepoHarnessEpisodeResult
-> RepoHarnessFullyAsyncQueueFacts
-> attach_queue_facts_to_rollout_sample(...)
-> serialize / deserialize MessageQueue payload
-> validate_rollout_sample_for_trainer_batch(...)
-> assemble reference-compatible DataProto shape
```

同时必须继承 Stage 14.2 的 `TransferQueue` 边界：

```text
PartialEpisodeCheckpoint 不允许进入 TransferQueue payload。
runtime-private checkpoint ref、handle_ref、resume token、workspace path 和 recorder cursor 真实路径不允许进入 TransferQueue payload。
TransferQueue 只能看到 terminal valid sample 的 batch-safe repo_harness_* 投影和 opaque ref。
```

但 Stage 15.1 不需要真实启动 `FullyAsyncTrainer`，也不需要修改 `reference/verl` 的 `_get_samples_from_queue(...)`。

## 12. evidence 和本地验收目录

Stage 15.1 完成后应新增本地验收目录：

```text
runs/repo-harness-verl-stage15-1-<timestamp>/
```

建议包含：

```text
stage15_1_command_log.jsonl
stage15_1_acceptance_summary.json
stage15_1_partial_rollout_producer_report.json
stage15_1_resume_scheduler_report.json
stage15_1_policy_loss_gate_report.json
stage15_1_message_queue_report.json
stage15_1_staleness_report.json
stage15_1_visibility_report.json
stage15_1_resource_lifecycle_report.json
stage15_1_patch_manifest.json
stage15_1_canonical_evidence_map.json
```

`stage15_1_acceptance_summary.json` 至少需要包含：

```text
acceptance_passed
partial_checkpoint_count
resume_attempt_count
resumed_terminal_episode_count
resumed_valid_sample_count
resumed_policy_loss_selected_sample_count
partial_policy_loss_selected_sample_count
stale_policy_loss_selected_sample_count
diagnostic_policy_loss_selected_sample_count
duplicate_resume_rejected_count
missing_resume_state_rejected_count
tampered_checkpoint_rejected_count
visibility_rejected_count
stale_rejected_count
required_samples
selected_valid_sample_count
resource_cleanup_passed
path_leak_scan_passed
ordinary_import_ok
heavy_import_loaded
```

本地 evidence 不能泄漏：

```text
/Users/...
/workspace/...
/home/...
.repo_harness_env_overlay
.repo_harness_runtime
hidden verifier
gold patch
provider secret
```

如果需要保存 runtime-private raw evidence，应放在 `runtime_private/` 并在 public summary 中只写 opaque ref、sha256 和用途。

## 13. 建议测试文件

建议新增：

```text
tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_producer.py
tests/unit/test_repo_harness_verl_stage15_1_resume_scheduler.py
tests/unit/test_repo_harness_verl_stage15_1_policy_loss_gate.py
tests/unit/test_repo_harness_verl_stage15_1_staleness.py
tests/unit/test_repo_harness_verl_stage15_1_resource_lifecycle.py
tests/unit/test_repo_harness_verl_stage15_1_reference_compatibility.py
tests/unit/test_repo_harness_verl_stage15_1_acceptance.py
```

如果实现选择把多个小模块合并在一个测试文件中，也可以，但必须覆盖下面所有行为。

### 13.1 producer 测试

必须覆盖：

```text
producer 可以产生至少 2 个 partial checkpoints
partial checkpoint 被写入 resume queue，不进入 policy-loss queue
pause timeout 进入 diagnostic side channel
terminal before pause 不伪造 partial checkpoint
producer cancel 后 active handle 被释放或结构化保留为 cancelling / diagnostic
pause timeout 后不会产生脱离 producer ledger 的延迟 checkpoint
```

### 13.2 resume scheduler 测试

必须覆盖：

```text
checkpoint 成功 resume 到 terminal result
resume 后终态样本通过 formal online RL
resume 后终态样本通过 formal async online RL
缺 ResumeStateStore entry 被拒绝
live handle 缺失被拒绝
handle_ref 属于另一个 runtime 被拒绝
runtime ownership scope mismatch 被拒绝
checkpoint content_digest 篡改被拒绝
lease_token mismatch 被拒绝
recorder_cursor_digest mismatch 被拒绝
generation_record_digest mismatch 被拒绝
workspace facts mismatch 被拒绝
duplicate resume 被拒绝
resume 后底层 episode 不返回时，scheduler timeout 后结构化拒绝
resume_timeout 样本不会进入 policy-loss queue
resume timeout 后同一个 run_id 可以重试，或被证明仍处于 cancelling / cleanup_running diagnostic
```

### 13.3 policy-loss gate 测试

必须覆盖：

```text
partial checkpoint 不能进入 policy loss
pending reward 不能进入 policy loss
stale terminal sample 不能进入 policy loss
visibility rejected sample 不能进入 policy loss
missing logprob sample 不能进入 policy loss
non-verl route sample 不能进入 policy loss
valid resumed completed sample 可以进入 policy-loss candidate queue
gate-produced policy-loss candidate queue 不包含 partial / stale / visibility rejected / timeout / diagnostic entry
adversarial selector backlog 可以手工注入坏样本，但 selector 必须跳过它们
PartialEpisodeCheckpoint 不能进入 TransferQueue payload
runtime-private resume ref、handle_ref、resume token、workspace path、recorder cursor 真实路径不能进入 TransferQueue payload
required_samples=2 时 selector 会跳过坏样本继续取样
```

### 13.4 staleness 测试

必须覆盖：

```text
resume 后 current_global_steps_at_terminal - max_global_steps 未超过阈值时可训练
resume 后 current_global_steps_at_terminal - max_global_steps 超过阈值时进入 stale diagnostic
stale 样本即使 final verifier accepted 也不能进入 policy loss
staleness report 记录 source_partial_checkpoint_id、resume_attempt_id、min_global_steps、max_global_steps、current_global_steps_at_terminal、current_param_version_at_terminal
```

### 13.5 reference compatibility 测试

必须覆盖：

```text
resumed completed sample 可以生成 RepoHarnessFullyAsyncQueueFacts
RolloutSample 顶层 sample_id 与 queue facts sample_id 一致
MessageQueue serialization / deserialization 需要 external visibility ledger
DataProto non_tensor_batch 中 repo_harness_* 字段按 batch 维度排列
partial / diagnostic 不会被包装成 reference-compatible valid RolloutSample
```

## 14. 前置回归命令

Stage 15.1 实现完成后至少执行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage15_0_inventory.py \
  tests/unit/test_repo_harness_verl_stage15_0_patch_plan.py \
  tests/unit/test_repo_harness_verl_stage15_0_acceptance.py

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py \
  tests/unit/test_repo_harness_rl_stage14_3_pause_resume_facade.py

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py \
  tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py \
  tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_producer.py \
  tests/unit/test_repo_harness_verl_stage15_1_resume_scheduler.py \
  tests/unit/test_repo_harness_verl_stage15_1_policy_loss_gate.py \
  tests/unit/test_repo_harness_verl_stage15_1_staleness.py \
  tests/unit/test_repo_harness_verl_stage15_1_resource_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage15_1_reference_compatibility.py \
  tests/unit/test_repo_harness_verl_stage15_1_acceptance.py
```

普通导入边界：

```bash
PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
import repo_harness.rl
import repo_harness_verl
loaded = [name for name in ("verl", "torch", "ray", "tensordict") if name in sys.modules]
print("ordinary_import_ok")
print("heavy_loaded=" + ",".join(loaded))
if loaded:
    raise SystemExit(1)
PY
```

RepoHarness core 不能 import `verl`：

```bash
if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness/rl; then
  exit 1
fi
```

空白检查：

```bash
git diff --check -- \
  src/repo_harness_verl \
  tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_producer.py \
  tests/unit/test_repo_harness_verl_stage15_1_resume_scheduler.py \
  tests/unit/test_repo_harness_verl_stage15_1_policy_loss_gate.py \
  tests/unit/test_repo_harness_verl_stage15_1_staleness.py \
  tests/unit/test_repo_harness_verl_stage15_1_resource_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage15_1_reference_compatibility.py \
  tests/unit/test_repo_harness_verl_stage15_1_acceptance.py \
  docs/agentic_RL/repo_harness_verl_workstreams/32-stage-15-1-execution-plan.md
```

## 15. 实现顺序建议

建议按下面顺序实施：

```text
1. 新增 partial_rollout.py 的数据结构、queue 和 diagnostic channel。
2. 实现 producer：只生成 checkpoint 和 resume queue item，不进入 policy-loss queue。
3. 实现 resume scheduler：校验同 runtime ownership 后 resume，并生成 terminal result ledger。
4. 实现 policy-loss source gate：只允许 terminal valid completed sample。
5. 接入 Stage 13.3-A fake queue / selector 做 required_samples=2 测试。
6. 生成本地 Stage 15.1 evidence。
7. 补 acceptance helper 或最小 inspect helper。
8. 跑 Stage 15.1 focused tests 和前置回归。
```

这个顺序可以防止一开始就把逻辑塞进 fake trainer selector，导致 partial checkpoint 和 terminal sample 的职责边界混在一起。

## 16. 通过标准

Stage 15.1 只有满足下面条件才算完成：

```text
1. 本地 fake partial rollout flow 稳定产生至少 2 个 partial checkpoints。
2. 至少 2 个 partial checkpoints 被 resume 成 terminal results。
3. 至少 2 个 resumed terminal samples 通过 formal online RL 和 formal async online RL。
4. required_samples=2 时，policy-loss selector 只选择 valid completed samples。
5. partial checkpoint、pending reward、stale、diagnostic、visibility rejected、timeout、cancelled、missing logprob、non-verl route 均未进入 policy-loss selected set。
6. gate-produced policy-loss candidate queue 中没有 partial、stale、diagnostic、visibility rejected、timeout 或 cancelled entry。
7. adversarial selector backlog 中的坏样本会被跳过，不能被当作 source gate 正常输出。
8. duplicate resume、missing ResumeStateStore、missing live handle、handle_ref 属于另一个 runtime、runtime ownership scope mismatch、workspace facts mismatch、digest mismatch、lease mismatch 都被结构化拒绝。
9. PartialEpisodeCheckpoint、runtime-private resume ref、handle_ref、resume token、workspace path、recorder cursor 真实路径不进入 TransferQueue payload。
10. terminal sample 的 trajectory digest 是 resume 后重新计算的，不复用 checkpoint digest。
11. evidence report 能解释 produced / resumed / completed / rejected / stale / selected 的逐样本 ledger。
12. 普通 import 不加载 verl、torch、ray、tensordict。
13. src/repo_harness/rl 没有 import verl。
14. 不修改 reference/verl。
15. 子代理只读复核没有 P1 / P2 阻断问题。
```

Stage 15.1 完成后，才能进入 Stage 15.2 远端 `partial_rollout=True` 多步 smoke。
