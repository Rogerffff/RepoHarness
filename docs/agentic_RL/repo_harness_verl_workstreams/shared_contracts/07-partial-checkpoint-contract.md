# Shared Contract 07：Partial Checkpoint Contract

本文档固定 Stage 14.2 的 partial episode checkpoint 契约。它描述的是“一个尚未完成的 episode 如何安全保存中间状态”，不是完整的 pause / resume runtime，也不是可以进入策略损失的训练样本。

```text
contract_version: repo_harness_verl_shared_contracts_v0
status: design_contract_v0_partial_checkpoint_gate
stage: 14.2
implementation_scope: local_schema_fixtures_validation_only
```

## 1. 阶段边界

Stage 14.2 只允许实现下面这些内容：

```text
PartialEpisodeCheckpoint schema
durable writer lease facts
recorder / artifact / transcript cursor facts
workspace / dependency environment facts
tool call / tool result pairing state
token provenance digest
reward finality facts
visibility-safe projection
canonical fixture and invalid fixture
tamper rejection tests
policy-loss rejection tests
```

Stage 14.2 不实现：

```text
verl partial_rollout=True
RepoHarnessRuntime.pause_episode(...)
RepoHarnessRuntime.resume_episode(...)
KV cache resume
正在运行的模型请求迁移
正在运行的工具、verifier、reward 或 cleanup 热迁移
partial checkpoint -> AgentLoopOutput policy-loss sample
远端 GPU smoke
```

如果某个 checkpoint 仍然是 partial，它必须默认：

```text
online_rl_eligible=false
invalid_for_training=true
invalid_for_online_rl=true
```

任何把 partial checkpoint 伪装成完整 formal online RL sample 的尝试都必须被拒绝。

## 2. 顶层对象

`PartialEpisodeCheckpoint` 至少需要表达：

```text
checkpoint_id
checkpoint_kind
checkpoint_status
episode_id
run_id
sample_attempt_id
resume_attempt_id
task_id
dataset_uid 或 dataset_index
rollout_uid 或 uid
policy_version
global_steps
min_global_steps
max_global_steps
trajectory_param_versions
current_param_version_at_checkpoint
created_at
turn_index
context_revision
```

`checkpoint_status` 第一版允许：

```text
partial
resume_preparation
invalid
tampered
stale
non_trainable
```

第一版不允许 `complete_for_policy_loss` 或等价状态。`resume_preparation` 只表示 checkpoint 已经通过恢复前置检查，不表示它已经恢复成功，也不表示它可以进入训练 batch。

## 3. Durable Writer Lease

partial checkpoint 必须记录 durable writer lease，而不能只依赖单进程内存 registry。最小字段包括：

```text
lease_token
owner_id
owner_kind
epoch
heartbeat_interval_seconds
acquired_at
last_heartbeat_at
release_state
release_at
lease_digest
```

规则：

1. `lease_digest` 必须根据 lease 内容重新计算，不能只信任 payload 自带值。
2. lease token、owner、epoch、heartbeat 或 release state 被篡改时必须拒绝。
3. 如果 run directory、worker、tool、verifier、recorder 或 cleanup 仍可能写入，checkpoint 不能进入 `resume_preparation`。
4. `resume_preparation` 要求 durable lease 仍然有效，避免在恢复准备阶段读到已经释放或丢失 ownership 的 run directory。

## 4. Recorder、Workspace 和 Tool Pairing

checkpoint 必须携带 recorder cursor facts：

```text
recorder_cursor_ref
recorder_cursor_digest
artifact_manifest_ref
artifact_manifest_digest
transcript_ref
transcript_digest
events_ref
events_digest
finalization_state
last_event_seq
last_artifact_seq
```

这些引用只能是 opaque ref，例如 `rh://...`，不能是 `/workspace/...`、`/Users/...`、`/tmp/...` 或真实 run directory。

workspace / dependency facts 必须只通过 opaque ref 和 digest 表达：

```text
workspace_snapshot_ref
workspace_snapshot_digest
source_snapshot_ref
source_snapshot_digest
workspace_lease_ref
workspace_lease_digest
dependency_environment_ref
dependency_environment_digest
workspace_state_ref
workspace_state_digest
patch_base_ref
patch_base_digest
```

tool pairing 必须说明已经完成和仍然 pending 的 tool call。`tool_pairing_status=closed` 时，所有 completed tool call 都必须有对应 tool result ref，不能缺失、重复或混入不可见 observation。

## 5. Token Provenance 和 Digest Binding

partial checkpoint 不能进入策略损失，但仍然必须保留到目前为止已经完成的 token provenance。最小字段包括：

```text
prompt_digest
raw_prompt_digest
tokenizer_digest
chat_template_digest
sampling_params_digest
policy_version_digest
response_ids
response_mask
response_logprobs
completed_response_spans
completed_generation_records
response_ids_digest
response_mask_digest
response_logprobs_digest
response_span_digest
generation_record_digest
trajectory_digest
```

规则：

1. `response_ids`、`response_mask`、`response_logprobs` 长度必须对齐。
2. `response_mask=0` 的工具 observation token 对应 `response_logprobs=0.0`。
3. `response_ids_digest`、`response_mask_digest`、`response_logprobs_digest`、`response_span_digest`、`generation_record_digest` 必须按当前内容重新计算。
4. `trajectory_digest` 必须绑定 sample identity、参数版本、上下文版本、token、span 和 generation record。
5. token 顺序、log probability、span 或 generation record 的任何篡改都必须被拒绝。

## 6. Reward Finality

partial checkpoint 可以记录 reward job 或 verifier 当前状态，但不能伪造最终 reward。规则：

```text
reward_state != final_verifier_completed 时，reward_score 必须为空
reward_state = final_verifier_completed 时，必须有 accepted 或 rejected final verifier status
partial / resume_preparation checkpoint 不能 claim final reward readiness
reward_finality_digest 必须根据 reward facts 重新计算
```

可信的 final verifier rejected 负样本属于完整 episode 结果的训练边界，不属于 partial checkpoint 的训练边界。

## 7. Visibility 和 Projection

checkpoint 内部可以保存 runtime-private opaque ref，例如：

```text
rh://runtime-private/writer-lease-0
```

但是下面这些位置只能看到 batch-safe projection，不能看到 runtime-private ref 的真实路径或嵌套结构：

```text
public canonical fixture
future AgentLoopOutput.extra_fields
DataProto tensor_batch / non_tensor_batch / meta_info
TransferQueue payload
acceptance summary
```

禁止出现：

```text
hidden_verifier
gold_patch
accepted_label
complete_reward_metadata
provider_secret
evaluator_only_logs
ground_truth
reward_extra_info
reward_extra_keys
extra_info
本机绝对路径
真实 run directory
真实 dependency environment 路径
```

`batch_safe_projection` 只能包含 `repo_harness_*` namespaced flat scalar 和 opaque refs。任何 runtime-private ref 进入 batch projection 都必须拒绝。

## 8. MessageQueue 和 Policy-Loss Gate

Stage 14.2 的 partial checkpoint 可以生成 diagnostic queue facts，但永远不能生成 valid policy-loss sample。

必须满足：

```text
PartialCheckpointQueueFacts.valid_for_policy_loss=false
sample_classification=partial_checkpoint 或 resume_preparation 或 diagnostic
rejection_reason 必须说明不可训练原因
```

下面三类负例必须固定：

```text
missing external visibility ledger
MessageQueue drop disguised as checkpoint
partial disguised as complete
```

如果未来 Stage 14.3 或更后续阶段实现 resume，也必须先把 checkpoint 恢复成新的完整 trajectory，再由完整 episode 结果通过 formal online RL gate。不能把 checkpoint 本身包装成 `FormalAsyncOnlineRLSample` 或 `RolloutSample`。

## 9. Canonical Fixtures

Stage 14.2 canonical fixture 位于：

```text
tests/fixtures/repo_harness_verl/stage14_2/
```

必须包含：

```text
canonical_partial_checkpoint.json
canonical_partial_checkpoint_public_projection.json
canonical_partial_checkpoint_roundtrip_report.json
canonical_partial_checkpoint_visibility_report.json
invalid_missing_generation_record_digest.json
invalid_missing_recorder_cursor.json
invalid_absolute_path_leak.json
invalid_forged_trainable_flag.json
invalid_reward_finality_forged.json
invalid_token_reorder.json
invalid_logprob_reorder.json
invalid_response_mask_value.json
invalid_response_span_reorder.json
invalid_stale_disguised_as_fresh.json
invalid_durable_lease_token_mismatch.json
invalid_reward_job_id_mismatch.json
invalid_missing_external_visibility_ledger.json
invalid_message_queue_drop_disguised_as_checkpoint.json
invalid_partial_disguised_as_complete.json
sha256_manifest.json
```

`canonical_partial_checkpoint.json` 是内部 checkpoint fixture，可以包含 runtime-private opaque refs，用来证明内部状态可以完整 roundtrip。`canonical_partial_checkpoint_public_projection.json` 是可传播公开投影 fixture，不能包含 runtime-private ref、本机绝对路径、hidden verifier、gold patch 或完整 reward metadata。

`sha256_manifest.json` 必须覆盖除自身之外的所有 fixture 文件。fixture roundtrip、visibility report、public projection 和 invalid fixture 的拒绝码必须由单元测试复核。

## 10. Stage 14.2 通过标准

Stage 14.2 完成时必须能证明：

1. canonical partial checkpoint 可以 schema roundtrip。
2. digest 绑定覆盖 token、span、generation record、lease、reward finality 和 content。
3. public projection 不泄漏 runtime-private ref、本机路径或 evaluator-only 字段。
4. writer 仍活跃时，checkpoint 不能进入 `resume_preparation`。
5. partial checkpoint 不能进入 `TrainingView`、`AgentLoopOutput`、DataProto、TransferQueue 或 fully async queue facts 的 valid policy-loss path。
6. invalid fixture 覆盖 tamper、visibility、reward finality、MessageQueue drop 和 partial disguised as complete。
7. `repo_harness.rl` 仍然不依赖 `verl`、`torch`、`ray` 或 `tensordict`。
