# Stage 14.2 执行计划：partial checkpoint contract

## 1. 阶段定位

Stage 14.2 的目标是先固定 RepoHarness 自己的 partial episode checkpoint contract。这个阶段只回答一个问题：

```text
一个尚未完成的 episode，是否可以安全、可审计、可校验地保存中间状态？
```

本阶段不实现真实 verl `partial_rollout=True`，不实现完整 pause / resume runtime，不把 partial trajectory 放进 policy loss，也不启动远端 GPU smoke。Stage 14.2 通过以后，Stage 14.3 才可以基于稳定 contract 实现最小 turn-boundary pause / resume facade。

## 2. 前置状态

Stage 14.0 已经证明单任务 fully async 远端链路可复现验收通过。Stage 14.1 已经扩展到多任务真实 episode、可信 trainable negative、diagnostic side channel 和更严格的证据验收。

当前 Stage 14.2 必须延续 Stage 0H 以来的顺序原则：

```text
先固定 contract / schema / canonical fixture / 拒绝规则
再做 runtime facade
最后再做真实远端 partial rollout smoke
```

因此 Stage 14.2 的产物应该主要是本地代码、contract 文档、fixtures 和单元测试。

## 3. 非目标

Stage 14.2 不做下面这些事情：

- 不修改 `reference/verl`。
- 不启用 verl `partial_rollout=True`。
- 不实现 `RepoHarnessRuntime.pause_episode(...)` 或 `resume_episode(...)` 的完整执行路径。
- 不支持正在运行的模型请求、工具命令、verifier、reward 写入或 cleanup 的热迁移。
- 不承诺 KV cache resume。
- 不把 partial checkpoint 转换为 `AgentLoopOutput` policy-loss 样本。
- 不启动 Vast.ai / GPU 训练。
- 不迁移旧 `repo-harness run-task`、`run-batch`、离线 export 或 SWE-Bench 评测路径。

如果实现过程中发现必须修改 runtime 行为才能表达 contract，应先把该行为记录为 Stage 14.3 的前置问题，不能在 Stage 14.2 中顺手实现。

## 4. 计划新增文件

建议新增或修改下面这些文件：

```text
docs/agentic_RL/repo_harness_verl_workstreams/shared_contracts/07-partial-checkpoint-contract.md
src/repo_harness/rl/partial_checkpoint.py
tests/fixtures/repo_harness_verl/stage14_2/
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py
```

如果实现时发现 `partial_checkpoint.py` 过大，可以拆成：

```text
src/repo_harness/rl/partial_checkpoint.py
src/repo_harness/rl/partial_checkpoint_validation.py
```

但第一版应避免过度拆分，优先保持 contract 可读。

## 5. Schema 设计边界

### 5.1 顶层对象

新增 `PartialEpisodeCheckpoint`，建议包含：

```text
schema_version
checkpoint_id
checkpoint_kind
checkpoint_status
episode_id
run_id
sample_attempt_id
resume_attempt_id
task_id
dataset_uid
dataset_index
rollout_uid / uid
policy_version
global_steps
min_global_steps
max_global_steps
current_param_version_at_checkpoint
created_at
turn_index
context_revision
```

`checkpoint_status` 第一版建议限定为：

```text
partial
resume_preparation
invalid
tampered
stale
non_trainable
```

Stage 14.2 中不能出现 `complete_for_policy_loss` 或等价状态。只要 checkpoint 仍然是 partial，就默认不可训练。

### 5.2 Sample identity 和参数时钟

checkpoint 需要绑定 Stage 13.0 的 sample identity 语义，但不能直接假装自己是完整 `FormalAsyncOnlineRLSample`。

必须记录：

```text
sample_attempt_id
resume_attempt_id
episode_id
run_id
task_id
dataset_uid / dataset_index
rollout_uid / uid
global_steps
min_global_steps
max_global_steps
trajectory_param_versions
current_param_version_at_checkpoint
staleness_status
staleness_threshold
```

规则：

- `resume_attempt_id` 只能表示一次恢复尝试，不能把旧 prefix 伪装成新的 fresh trajectory。
- `current_param_version_at_checkpoint - max_global_steps` 或等价 staleness 指标必须可重新计算。
- 如果 checkpoint 已经 stale，必须进入 diagnostic / rejected side channel，不能进入 policy loss。

### 5.3 Durable writer lease facts

新增 `DurableWriterLeaseFacts` 或等价结构，至少包含：

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

`release_state` 第一版建议限定为：

```text
active
released
expired
lost
cleanup_failed
unknown
```

规则：

- 单进程内存 registry 不能作为远端 Ray / 多进程 / resume 的唯一 writer 保护。
- checkpoint 必须表达当前 writer lease 是否仍 active。
- 如果底层 worker、tool、verifier、recorder 或 cleanup 仍可能写入，checkpoint 必须标记为不可恢复或需要 resume 前重新占用 durable lease。
- lease token 不匹配、epoch 回退、heartbeat 缺失或 release 状态伪造必须被拒绝。

### 5.4 Recorder、artifact 和 transcript cursor

新增 `RecorderCursorFacts` 或等价结构，至少包含：

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

规则：

- 所有 refs 必须是 opaque refs，例如 `rh://...`，不能是本机绝对路径。
- `finalization_state` 不能伪造完整终态。partial checkpoint 默认不是 run finalization。
- 如果 recorder cursor 缺失、artifact manifest digest 缺失、transcript digest 缺失或 events digest 缺失，checkpoint 不可恢复。

### 5.5 Workspace 和 dependency facts

新增 `WorkspaceCheckpointFacts` 或等价结构，至少包含：

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

规则：

- 不能包含 `/workspace/...`、`/Users/...`、`/tmp/...`、真实 dependency environment 路径或 run directory。
- dependency environment 只能用 opaque ref 和 digest 表达。
- source snapshot、workspace snapshot 和 lease digest 必须绑定，不能混用 snapshot A 和 lease B。

### 5.6 Tool pairing state

新增 `ToolPairingState` 或等价结构，至少包含：

```text
pending_tool_call_ids
completed_tool_call_ids
tool_result_refs
tool_result_visibility_digest
observation_token_projection_digest
tool_pairing_status
```

规则：

- 未闭合 tool call、重复 tool result、缺失 tool result、缺失 observation token projection 或 tool result visibility 失败时，checkpoint 只能是不可训练状态。
- tool observation token 如果已经进入 `response_ids`，必须有 `response_mask=0` 和 `response_logprobs=0.0` 的 span 解释。

### 5.7 Token provenance 和 generation records

新增 `CheckpointTokenProvenance` 或等价结构，至少包含：

```text
prompt_digest
raw_prompt_digest
tokenizer_digest
chat_template_digest
sampling_params_digest
policy_version_digest
response_ids_digest
response_mask_digest
response_logprobs_digest
response_span_digest
generation_record_digest
trajectory_digest
completed_generation_records
completed_response_spans
```

规则：

- 已完成模型回合的 token、mask、logprob、generation records 和 response spans 必须可重新计算 digest。
- token 重排、logprob 重排、span 重排、generation record 删除、policy version 篡改、sampling params 篡改必须被拒绝。
- `response_logprobs=None` 的 partial checkpoint 可以用于 diagnostic，但不能声明 formal online RL 可用。

### 5.8 Reward finality

新增 `CheckpointRewardFinalityFacts` 或等价结构，至少包含：

```text
reward_state
reward_job_id
final_verifier_status
reward_score
reward_finality_digest
```

规则：

- partial checkpoint 默认没有 final reward。
- `reward_state=final` 不能和 `checkpoint_status=partial` 共同声明为可训练。
- `reward_job_id` mismatch、final verifier 伪造、reward metadata 细节泄漏必须被拒绝。
- checkpoint 不能包含完整 reward metadata、hidden verifier、accepted label 细节或 gold patch。

## 6. Digest 和 tamper 规则

Stage 14.2 必须提供稳定 helper：

```python
compute_partial_checkpoint_content_digest(...)
compute_partial_checkpoint_visibility_digest(...)
compute_partial_checkpoint_generation_record_digest(...)
compute_partial_checkpoint_trajectory_digest(...)
validate_partial_checkpoint_roundtrip(...)
validate_partial_checkpoint_for_resume_preparation(...)
validate_partial_checkpoint_not_trainable(...)
```

这些 helper 必须：

- 使用稳定 JSON canonicalization。
- 拒绝本机绝对路径。
- 拒绝 evaluator-only marker，例如 `ground_truth`、`reward_extra_info`、`hidden_verifier`、`gold_patch`。
- 重新计算 digest，而不是只信任输入字段。
- 对 `model_copy(...)` 后的字段删除、字段替换、token 重排、logprob 重排、span 重排和 generation record 篡改给出结构化拒绝原因。

## 7. Visibility 规则

checkpoint 字段分三类：

```text
模型可见字段
batch-safe opaque refs / flat scalar
runtime-private refs
```

Stage 14.2 必须验证：

- 模型可见字段只能包含模型真实已经看到的 prompt、assistant 文本摘要或工具 observation 摘要。
- batch-safe 字段只能包含 `repo_harness_*` namespaced flat scalar 或 opaque refs。
- runtime-private refs 可以存在于 checkpoint 内部，但不能进入 future `AgentLoopOutput.extra_fields`、DataProto、TransferQueue 或 public acceptance summary。
- public canonical fixture、future `AgentLoopOutput.extra_fields`、DataProto、TransferQueue 和 acceptance summary 只能看到 batch-safe projection；它们不能看到 runtime-private ref 的真实路径、嵌套结构、run directory、workspace directory 或 dependency environment path。
- checkpoint public fixture 不能出现本机绝对路径。
- checkpoint 不能出现 hidden verifier、gold patch、完整 reward metadata、provider secret 或 evaluator-only logs。

## 8. Canonical fixtures

建议新增目录：

```text
tests/fixtures/repo_harness_verl/stage14_2/
```

建议新增文件：

```text
canonical_partial_checkpoint.json
canonical_partial_checkpoint_roundtrip_report.json
canonical_partial_checkpoint_visibility_report.json
invalid_missing_generation_record_digest.json
invalid_missing_recorder_cursor.json
invalid_absolute_path_leak.json
invalid_forged_trainable_flag.json
invalid_reward_finality_forged.json
invalid_token_reorder.json
invalid_logprob_reorder.json
invalid_response_span_reorder.json
invalid_stale_disguised_as_fresh.json
invalid_durable_lease_token_mismatch.json
invalid_reward_job_id_mismatch.json
invalid_missing_external_visibility_ledger.json
invalid_message_queue_drop_disguised_as_checkpoint.json
invalid_partial_disguised_as_complete.json
sha256_manifest.json
```

如果 fixture 数量过多，可以把 invalid 样例放入一个 JSONL 文件，但每个样例必须有清晰的 `expected_rejection_code`。

## 9. 测试计划

### 9.1 Schema roundtrip

新增：

```text
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py
```

覆盖：

- canonical checkpoint 可以 `model_validate -> model_dump_json -> model_validate`。
- digest roundtrip 稳定。
- optional / default 字段不会破坏 canonical fixture。
- schema 包不 import `verl`。

### 9.2 Visibility

新增：

```text
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py
```

覆盖：

- 绝对路径泄漏被拒绝。
- hidden verifier / gold patch / reward metadata / provider secret 被拒绝。
- runtime-private refs 不进入 batch-safe projection。
- opaque refs 合法，嵌套 dict 不允许偷放 evaluator-only 字段。

### 9.3 Tamper rejection

新增：

```text
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py
```

覆盖：

- token reorder 被拒绝。
- logprob reorder 被拒绝。
- response span reorder 被拒绝。
- generation record 删除或 policy version 篡改被拒绝。
- durable lease token mismatch 被拒绝。
- `AsyncEpisodeSnapshot` 或 writer-active facts 表示底层 worker 仍可能写入时，checkpoint 不能进入 `resume_preparation`。
- recorder cursor digest mismatch 被拒绝。
- artifact manifest digest mismatch 被拒绝。
- reward job id mismatch 被拒绝。
- stale disguised as fresh 被拒绝。
- missing external visibility ledger 被拒绝。
- MessageQueue drop disguised as checkpoint 被拒绝。
- partial disguised as complete 被拒绝。

### 9.4 Policy-loss gate

新增：

```text
tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py
```

覆盖：

- partial checkpoint 不能构造 formal online RL sample。
- partial checkpoint 不能进入 `AgentLoopOutput` policy-loss 转换。
- partial checkpoint 不能进入 Stage 13.2 / Stage 13.3 的 fully async queue facts valid path。测试必须覆盖 `PartialEpisodeCheckpoint -> build_queue_facts / formal async sample path -> rejected as diagnostic 或 resume_preparation`，防止 checkpoint 被包装成 `FormalAsyncOnlineRLSample` 或 valid `RolloutSample`。
- partial checkpoint 只能输出 diagnostic / resume preparation facts。
- `checkpoint_status=partial` 且 `reward_state=final` 的伪造可训练状态被拒绝。

## 10. 验收命令

本地验收建议执行：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m compileall -q src

PYTHONPATH=src PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py

PYTHONPATH=src PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_task_pool.py
```

Import boundary 检查：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness.rl
print("ordinary_import_ok")
for name in ["torch", "ray", "tensordict", "verl"]:
    if name in sys.modules:
        raise SystemExit(f"unexpected heavy import: {name}")
PY

if rg -n '(^|\\s)(import|from)\\s+verl' src/repo_harness/rl tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_*.py; then
  exit 1
fi
```

文档和 fixture 检查：

```bash
git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/29-stage-14-2-execution-plan.md \
  docs/agentic_RL/repo_harness_verl_workstreams/shared_contracts/07-partial-checkpoint-contract.md \
  src/repo_harness/rl/partial_checkpoint.py \
  tests/fixtures/repo_harness_verl/stage14_2 \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py
```

## 11. 完成标准

Stage 14.2 只有在下面条件同时满足时才算完成：

- `PartialEpisodeCheckpoint` 或等价 schema 已经落地。
- shared contract 文档或 canonical fixture 已经固定。
- canonical checkpoint 可以 roundtrip，并且 sha256 manifest 稳定。
- visibility scan 能拒绝本机路径、evaluator-only 字段和 runtime-private 字段外泄。
- tamper tests 覆盖 token、logprob、span、generation record、lease、recorder、workspace、reward finality 和 staleness。
- partial checkpoint 明确不能进入 policy loss。
- `repo_harness.rl` 仍不依赖 `verl`、`torch`、`ray` 或 `tensordict`。
- 不修改远端训练脚本、不启动 GPU、不声称 pause / resume 已经实现。

## 12. 风险和边界提醒

最容易走偏的地方有三个：

1. 把 checkpoint 当成完整样本。  
   只要 episode 没有完成 final verifier 和 reward finality，checkpoint 就不能进入 policy loss。

2. 只做内存锁，不做 durable lease facts。  
   Stage 14.2 虽然不实现远端 lease 服务，但 contract 必须能表达跨进程 writer lease，否则 Stage 14.3 / Stage 15 会缺少恢复安全边界。

3. 只保存 token，不保存来源绑定。  
   token ids、logprobs、response spans、generation records、tokenizer、chat template、sampling params 和 policy version 必须一起绑定进 digest。单独保存 response ids 没有训练安全意义。
