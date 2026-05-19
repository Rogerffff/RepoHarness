# Stage 14.0 执行计划：fully async 远端链路验收器和脚本化

本文是 Stage 14.0 的具体执行计划。它承接
`01-sequential-implementation-plan.md` 中 Stage 14.0 的高层路线，并建立在
Stage 13.3-B 已经远端跑通真实 fully async 多步 smoke 的基础上。

Stage 14.0 的目标不是继续扩大训练规模，也不是实现 partial rollout / resume。它的目标是：
把 Stage 13.3-B 这次“人手动排障后跑通”的远端 fully async smoke，变成仓库内可复用、
可机器验收、可复查、可重新执行的标准流程。

本阶段默认使用用户准备的同类远端环境：

```text
GPU：2 * RTX PRO 6000，单卡约 96GB 显存
镜像：verlai/verl:sgl056.latest
模型：Qwen/Qwen2.5-Coder-7B-Instruct
训练策略：LoRA training
权重同步策略：merged weight sync to SGLang
rollout 后端：SGLang
```

这套配置只是 Stage 14.0 的开发 smoke baseline，建议命名为
`dev_smoke_2x96gb_lora_merged_sync`。它不能被描述成正式训练唯一配置，也不能被外推为
4 卡、8 卡、全参数强化学习或其他模型后端已经可用。

## 1. 阶段目标和非目标

### 1.1 必须完成的目标

Stage 14.0 必须完成下面四类能力：

1. **远端 fully async smoke 脚本化**
   - 能从一个固定训练 profile 生成远端运行目录、训练数据、agent loop 配置、运行脚本和证据目录。
   - 能记录远端环境矩阵、模型 revision、tokenizer / chat template 来源、`reference/verl`
     来源、远端 patch manifest、命令日志和实例信息。
   - 能在 smoke 结束后打包 evidence，并支持用户用 Vast.ai CLI 暂停实例。

2. **机器验收器**
   - 必须实现最小可执行的 `inspect-stage14-fully-async-acceptance` 或等价验收脚本。
   - 只写计划、只写文档或者只给人工检查清单不算 Stage 14.0 通过。
   - 验收器必须能在本地下载后的 evidence 目录或 tarball 上独立判断通过或失败。

3. **canonical evidence schema**
   - 固定 Stage 14.0 acceptance summary、profile、preflight、remote patch manifest、
     command log、parameter sync、trainer step、MessageQueue、visibility、staleness、
     batch provenance、resource cleanup 和 path leak scan 的字段要求。
   - 允许具体执行时合并文件，但必须在 acceptance summary 中写清
     `canonical evidence item -> actual path` 映射。

4. **Stage 13.3-B 链路回归**
   - 使用新的脚本和新的验收器，在同类远端实例上重新跑一条短步数 fully async smoke。
   - 至少完成 3 到 4 个真实 trainer progress step。
   - 至少发生一次训练后参数同步。
   - 参数同步后仍有新的 RepoHarness valid 样本进入 policy-loss queue 并被 trainer 消费。

### 1.2 本阶段不做的事情

Stage 14.0 不做：

- 不实现 partial rollout / resume。
- 不打开真实 `async_training.partial_rollout=True` 并让 partial trajectory 进入 policy loss。
- 不做模型收敛验收。
- 不做大规模 SWE-Bench 训练。
- 不把 4 卡、8 卡、多节点或者全参数 7B RL 作为通过条件。
- 不把旧 `repo-harness run-task`、`run-batch`、`run-experiment` 和离线 export 迁移到
  `RepoHarnessRuntime.run_episode(...)`。
- 不把动态 SGLang LoRA adapter loading 修复作为主目标。当前通过路径仍然是
  LoRA training + merged weight sync。

如果执行中发现必须修改 `reference/verl`、monkey patch trainer hook 或注入远端 helper，
必须把 patch 文件、sha256、启用方式、回退方式写入 `remote_patch_manifest`。没有登记的
远端 patch 不能通过验收。

## 2. 当前已知基线

Stage 13.3-B 已有一份通过的远端证据包：

```text
runs/stage13_3b-remote-final-20260518T174537Z/stage13_3b_final_evidence.tar.gz
```

关键摘要：

```text
acceptance_passed=true
completed_trainer_step_count=4
max_current_param_version=4
parameter_sync_count=5
batch_assembly_completed_count=8
successful_loop_collection_count=8
real_episode_run_count=1
```

这个证据足以说明第一版 fully async 链路成立，但它还不是 Stage 14.0 的最终形态，原因是：

- 证据验收主要依赖人工读报告和日志。
- 远端运行脚本、agent loop runtime helper 和 profile 还没有收口成正式 builder。
- 真实 episode 数量很少，本阶段只要求复现同类 baseline，不要求多任务扩展。
- trainer batch 中 log probability provenance 的记录需要成为正式证据项，而不是只靠口头判断。
- 远端 patch、运行环境和证据映射需要更严格地机器检查。

## 3. 推荐实现文件和模块归属

Stage 14.0 应优先把验收和脚本化能力放在 RepoHarness-verl 边界模块中，不要污染
RepoHarness core 的普通评测入口。

建议新增或修改：

```text
src/repo_harness_verl/stage14_acceptance.py
src/repo_harness_verl/stage14_remote_smoke.py
src/repo_harness/cli/main.py
tests/unit/test_repo_harness_verl_stage14_acceptance.py
tests/unit/test_repo_harness_verl_stage14_remote_smoke_builder.py
docs/agentic_RL/repo_harness_verl_workstreams/26-stage-14-0-execution-plan.md
```

职责建议：

```text
stage14_acceptance.py:
  Stage 14.0 evidence schema
  acceptance summary validation
  tarball / directory manifest validation
  log negative pattern scan
  public evidence path leak scan
  canonical evidence item mapping validation
  inspect_stage14_fully_async_acceptance(...)

stage14_remote_smoke.py:
  training profile dataclass / pydantic schema
  dev_smoke_2x96gb_lora_merged_sync profile
  remote run directory skeleton builder
  sanitized command log helper
  remote patch manifest helper
  smoke command builder
  evidence collection manifest builder

cli/main.py:
  repo-harness inspect-stage14-fully-async-acceptance <evidence-path> --assert-complete
  可选：repo-harness build-stage14-remote-smoke-kit ...
```

如果实现时认为 CLI 太早，可以先提供 `python -m repo_harness_verl.stage14_acceptance`
等价入口，但 Stage 14.0 完成前必须有一个稳定命令可供用户和自动化调用。

## 4. Stage 14.0 evidence contract

### 4.1 canonical evidence items

Stage 14.0 的 evidence 可以是目录，也可以是 tarball。验收器必须接受两种形式：

```text
repo-harness inspect-stage14-fully-async-acceptance <evidence-dir> --assert-complete
repo-harness inspect-stage14-fully-async-acceptance <evidence.tar.gz> --assert-complete
```

canonical evidence items 至少包括：

```text
stage14_acceptance_summary.json
stage14_command_log.sanitized.jsonl
stage14_training_profile.json
stage14_remote_preflight.json
stage14_environment_matrix.json
stage14_remote_patch_manifest.json
stage14_fixture_manifest.json
stage14_fixture_sha256_report.json
stage14_fully_async_import_inventory.json
stage14_trainer_steps_report.json
stage14_parameter_sync_report.json
stage14_message_queue_report.json
stage14_policy_loss_gate_report.json
stage14_valid_sample_filter_report.json
stage14_visibility_report.json
stage14_staleness_report.json
stage14_batch_provenance_report.json
stage14_resource_cleanup_report.json
stage14_path_leak_scan_report.json
stage14_stdout.sanitized.log
run_stage14_fully_async_smoke.sh
repo_harness_agent_loop_config.yaml
stage14_train.parquet
stage14_val.parquet
stage14_task_pool_manifest.json
stage14_source_map.json
runtime_private_manifest.json
```

如果具体执行计划为了减少文件数量而合并报告，必须在 `stage14_acceptance_summary.json`
中提供：

```json
{
  "canonical_evidence_map": {
    "stage14_parameter_sync_report.json": "reports/training_runtime_report.json",
    "stage14_message_queue_report.json": "reports/training_runtime_report.json"
  }
}
```

验收器以 canonical item 是否被完整覆盖为准，而不是只看文件名是否逐字匹配。

公开 canonical evidence 只能包含可传播、已脱敏内容。真实远端 stdout、Ray 原始日志、原始命令输出、
完整远端路径和 runtime-only 调试文件如果需要保留，必须放在私有区，例如：

```text
runtime_private/stage14_stdout.raw.log
runtime_private/ray_logs/
runtime_private/raw_command_outputs/
```

私有文件只能进入 `runtime_private_manifest.json` 和 sha256 绑定，不进入公开 acceptance summary 的
可传播字段，也不能进入训练 batch、MessageQueue、DataProto 或公开报告。公开 canonical item 中的
JSON、log、YAML、shell script、parquet、source map 和 markdown 都必须经过 path leak scan。

### 4.2 acceptance summary 最小字段

`stage14_acceptance_summary.json` 至少需要包含：

```text
schema_version
stage
acceptance_passed
created_at
repo_harness_commit
repo_harness_git_status_short
remote_git_status_short
required_samples
verl_commit_or_package_version
remote_patch_manifest_sha256
training_profile_name
image
instance_id
gpu_count
gpu_memory_gb_per_device
inference_backend
training_strategy
weight_sync_strategy
model_id
model_revision
tokenizer_revision
chat_template_digest
fixture_manifest_sha256
remote_command_exit_code
completed_trainer_step_count
parameter_sync_count
current_param_version
valid_sample_count
final_verifier_rejected_trainable_count
formal_validator_rejected_count
diagnostic_sample_count
policy_loss_gate_passed
policy_loss_gate_mode
policy_loss_queue_invalid_sample_count
message_queue_produced_sample_count
message_queue_consumed_sample_count
message_queue_dropped_sample_count
post_sync_valid_sample_count
staleness_threshold
stale_sample_count
filtered_stale_sample_count
max_observed_staleness
trainer_batch_logprob_provenance_passed
trainer_batch_digest
visibility_scan_passed
path_leak_scan_passed
resource_cleanup_passed
stdout_sha256
evidence_tarball_sha256
instance_final_status
canonical_evidence_map
known_scope_notes
```

### 4.3 验收器必须拒绝的情况

`inspect-stage14-fully-async-acceptance --assert-complete` 必须拒绝：

- `acceptance_passed` 不是 `true`。
- `remote_command_exit_code` 不是 `0`。
- `completed_trainer_step_count < 3`。
- `parameter_sync_count < 1`。
- `current_param_version < 1`。
- `valid_sample_count < 1`。
- `post_sync_valid_sample_count < 1`。
- `policy_loss_gate_passed` 不是 `true`。
- `policy_loss_queue_invalid_sample_count != 0`。
- `message_queue_consumed_sample_count < completed_trainer_step_count * required_samples`。
- `message_queue_dropped_sample_count != 0`，除非执行计划显式允许受控 drop，并有逐样本 ledger 证明没有影响 valid sample count。
- `trainer_batch_logprob_provenance_passed` 不是 `true`。
- `visibility_scan_passed` 不是 `true`。
- `path_leak_scan_passed` 不是 `true`。
- `resource_cleanup_passed` 不是 `true`。
- `instance_final_status` 不是 `exited`，或者实例最终状态缺失、不可解释。
- 本地或远端 `git status --short` 非空，但 `stage14_remote_patch_manifest.json` 没有逐项列出
  modified / untracked 文件、sha256、用途和启用方式。
- 任一 consumed policy-loss sample 的 staleness 超过 `staleness_threshold`。
- 任一超过 staleness threshold 的 sample 没有出现在 filtered stale ledger 中。
- `canonical_evidence_map` 缺少任一 canonical item。
- `remote_patch_manifest_sha256` 与实际 `stage14_remote_patch_manifest.json` 不一致。
- stdout 中出现关键错误模式，例如：

```text
RepoHarnessVerlAdapterError
invalid_for_training_sample_in_formal_batch
Got LoRA adapter that has never been loaded
CUDA out of memory
Traceback
```

- 可传播 evidence 中出现真实本机路径、workspace path、dependency environment path、
  `.repo_harness_runtime`、`.repo_harness_env_overlay`、provider secret、Hugging Face token、
  Vast.ai API key、SSH 私钥、hidden verifier、gold patch 或完整 reward metadata。

验收器不能为了检查 evidence 而反序列化不可信的 `cloudpickle` payload。对 MessageQueue 和
RolloutSample 的检查只能依赖外层 ledger、digest、manifest、summary 和公开安全投影。

### 4.4 policy-loss gate 证据

Stage 14.0 不能只在训练结束后统计 `policy_loss_queue_invalid_sample_count=0`。必须有
`stage14_policy_loss_gate_report.json` 或等价报告，证明坏样本在进入真实 policy-loss queue 前
已经被挡住，或者证明 trainer-side gate 在 `FullyAsyncTrainer` assembly 前真实执行。

报告至少需要记录：

```text
policy_loss_gate_mode
policy_loss_gate_passed
sample_ledger
produced_sample_count
accepted_for_policy_loss_count
rejected_sample_count
side_channel_sample_count
consumed_sample_count
invalid_consumed_sample_count
required_samples
```

`sample_ledger` 每条记录至少包含：

```text
sample_id
trajectory_digest
status
reward_state
route
generation_record_digest
visibility_scan_digest
staleness
gate_decision
gate_rejection_reason
side_channel_ref
trainer_step_index
consumed_by_policy_loss
```

通过要求：

```text
invalid_consumed_sample_count == 0
accepted_for_policy_loss_count >= completed_trainer_step_count * required_samples
message_queue_consumed_sample_count >= completed_trainer_step_count * required_samples
每个 completed trainer step 都能回查到至少一个 valid sample_id
```

如果 Stage 14.0 采用 source gate，真实 policy-loss MessageQueue 只能接收 valid 样本。
如果采用 trainer-side gate，必须证明 gate 在 reference assembly 和 policy loss 前执行，
并且会持续取样直到凑够 required valid samples 或遇到明确 timeout / termination signal。

## 5. 远端训练 profile

### 5.1 默认 profile

默认 profile 名称：

```text
dev_smoke_2x96gb_lora_merged_sync
```

必填字段：

```text
profile_name
gpu_count
gpu_memory_gb_per_device
image
model_id
inference_backend
training_strategy
weight_sync_strategy
rollout_total_steps
trigger_parameter_sync_step
required_samples
staleness_threshold
partial_rollout
max_prompt_length
max_response_length
gpu_memory_utilization
max_model_len
max_num_seqs
max_num_batched_tokens
repo_harness_agent_loop_name
task_pool_name
expected_completed_trainer_steps_min
expected_parameter_sync_count_min
```

默认值建议：

```text
profile_name=dev_smoke_2x96gb_lora_merged_sync
gpu_count=2
gpu_memory_gb_per_device=96
image=verlai/verl:sgl056.latest
model_id=Qwen/Qwen2.5-Coder-7B-Instruct
inference_backend=sglang
training_strategy=lora
weight_sync_strategy=merged_weight_sync
rollout_total_steps=8
trigger_parameter_sync_step=2
required_samples=1
staleness_threshold=1
partial_rollout=false
max_prompt_length=4096
max_response_length=256
gpu_memory_utilization=0.25
max_model_len=4608
max_num_seqs=2
max_num_batched_tokens=6144
repo_harness_agent_loop_name=repo_harness
expected_completed_trainer_steps_min=3
expected_parameter_sync_count_min=1
```

### 5.2 Hydra 参数要求

远端运行命令必须显式包含或由 profile 生成以下关键配置：

```text
actor_rollout_ref.hybrid_engine=False
actor_rollout_ref.rollout.name=sglang
actor_rollout_ref.rollout.mode=async
actor_rollout_ref.rollout.checkpoint_engine.backend=nccl
actor_rollout_ref.rollout.calculate_log_probs=True
actor_rollout_ref.rollout.multi_turn.enable=True
actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness
actor_rollout_ref.rollout.agent.num_workers=1
actor_rollout_ref.rollout.agent.agent_loop_config_path=<run_dir>/repo_harness_agent_loop_config.yaml
actor_rollout_ref.rollout.gpu_memory_utilization=0.25
actor_rollout_ref.rollout.max_model_len=4608
actor_rollout_ref.rollout.max_num_seqs=2
actor_rollout_ref.rollout.max_num_batched_tokens=6144
actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1

actor_rollout_ref.model.lora_rank=8
actor_rollout_ref.model.lora_alpha=16
actor_rollout_ref.model.target_modules='["q_proj","v_proj"]'
actor_rollout_ref.model.lora.merge=True
actor_rollout_ref.model.trust_remote_code=True
actor_rollout_ref.model.use_remove_padding=True
actor_rollout_ref.model.enable_gradient_checkpointing=True
actor_rollout_ref.model.enable_activation_offload=True

actor_rollout_ref.actor.use_rollout_log_probs=True
actor_rollout_ref.actor.ppo_mini_batch_size=1
actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1
actor_rollout_ref.actor.ppo_epochs=1
actor_rollout_ref.actor.fsdp_config.param_offload=True
actor_rollout_ref.actor.fsdp_config.optimizer_offload=True
actor_rollout_ref.actor.fsdp_config.use_orig_params=True

critic.enable=False
reward.reward_model.enable=False
algorithm.rollout_correction.bypass_mode=True

rollout.nnodes=1
rollout.n_gpus_per_node=1
trainer.nnodes=1
trainer.n_gpus_per_node=1

async_training.trigger_parameter_sync_step=2
async_training.require_batches=1
async_training.staleness_threshold=1
async_training.partial_rollout=False
rollout.total_rollout_steps=8

data.prompt_key=prompt
data.return_raw_chat=True
data.train_batch_size=0
data.gen_batch_size=1
```

上述参数必须以 Stage 13.3-B 已经跑通的脚本为基准。如果当前 `reference/verl` 版本改名或不再支持
某个参数，profile builder 必须在 preflight 中记录“当前等价参数是什么”或返回
`profile_generation_failure`，不能静默丢掉 `calculate_log_probs`、rollout log probability、
LoRA merge、offload、SGLang engine 限制或参数同步相关配置。

### 5.2.1 SGLang flashinfer 要求

Stage 13.3-B 排障已经证明当前镜像可能默认选择不兼容的 SGLang attention backend。Stage 14.0
profile 必须明确优先使用 Hydra 参数或等价配置强制：

```text
actor_rollout_ref.rollout.engine_kwargs.sglang.attention_backend=flashinfer
actor_rollout_ref.rollout.engine_kwargs.sglang.decode_attention_backend=flashinfer
actor_rollout_ref.rollout.engine_kwargs.sglang.prefill_attention_backend=flashinfer
```

如果当前 `reference/verl` 不接受这些 Hydra key，允许使用远端 patch 或启动脚本 patch，但必须：

```text
写入 stage14_remote_patch_manifest.json
记录 patch sha256
记录启用命令
记录回退方式
```

只检查 `flashinfer availability` 但不强制 SGLang 使用 `flashinfer`，不能作为 Stage 14.0 acceptance。

### 5.3 环境变量要求

远端脚本必须记录并设置：

```bash
export TORCH_CUDA_ARCH_LIST=12.0
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=true
export CUDA_DEVICE_MAX_CONNECTIONS=1
```

远端脚本不能设置：

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

原因是当前 SGLang `TorchMemorySaver` 不接受该配置，本次 Stage 13.3-B 排障已经证明它会造成启动失败。

### 5.4 远端依赖预检

preflight 必须检查：

```text
python version
torch version
torch cuda availability
GPU count and name
Ray version
transformers version
SGLang version
verl source path or package version
reference/verl commit if using repository reference
cupy-cuda12x availability
flashinfer availability
repo_harness import
repo_harness_verl import
fully_async_main import
RepoHarnessVerlAgentLoop target import
```

如果 `checkpoint_engine.backend=nccl` 缺少 `cupy-cuda12x`，脚本可以安装或提示安装：

```bash
pip install cupy-cuda12x==13.6.0
```

安装动作必须进入命令日志和 preflight report。

## 6. 真实 trainer batch log probability provenance

Stage 14.0 必须有 `stage14_batch_provenance_report.json`。它用于证明进入 policy loss 的真实 batch
仍然绑定了 rollout token、response mask、old log probability、generation record 和 policy version。

### 6.1 最低通过线

最低通过线必须记录：

```text
batch_digest
response_ids_digest
response_mask_digest
rollout_log_probs_digest
response_spans_digest
generation_record_digest
trajectory_digest
policy_version_digest
tokenizer_digest
chat_template_digest
sampling_params_digest
batch_size
response_token_count
assistant_generation_token_count
tool_observation_masked_token_count
span_logprob_policy_summary
rollout_log_probs_present
rollout_log_probs_shape
response_ids_shape
response_mask_shape
provenance_passed
```

并满足：

```text
rollout_log_probs_present=true
response_ids_shape 与 response_mask_shape 对齐
rollout_log_probs_shape 与 response_ids_shape 对齐
generation_record_digest 与 queue facts / side evidence 中的 digest 一致
trajectory_digest 与 queue facts / side evidence 中的 digest 一致
response_spans_digest 非空，并且 span policy summary 能解释 assistant token 与 tool observation token
tool observation token 的 mask / logprob 策略满足 Stage 0H 到 Stage 13 已固定的规则
policy_version_digest 非空
provenance_passed=true
```

### 6.2 hook 归属

如果现有 `reference/verl` 没有现成 hook 可以写出上述报告，允许使用远端 helper 或 monkey patch。
但必须满足：

- patch 文件进入 `stage14_remote_patch_manifest.json`。
- patch sha256 写入 acceptance summary。
- patch 启用方式写入 command log。
- patch 只记录 digest、shape、计数和安全摘要，不写完整 token 序列、完整 reward metadata 或真实路径。
- patch 有回退说明，说明不启用时 smoke 只能作为 debug run，不能作为 Stage 14.0 acceptance。

不能把“没有 hook 所以跳过 provenance 检查”作为通过理由。

## 7. 远端执行流程

Stage 14.0 远端执行建议分为九步：

```text
14.0-R0 本地准备和代码状态检查
14.0-R1 远端实例预检
14.0-R2 远端代码同步和依赖预检
14.0-R3 生成 training profile、数据集、agent loop 配置和 run script
14.0-R4 执行短步数 fully async smoke
14.0-R5 生成 reports 和 acceptance summary
14.0-R6 打包 evidence tarball 并计算 sha256
14.0-R7 下载 evidence 到本地
14.0-R8 本地 inspect-stage14-fully-async-acceptance --assert-complete
14.0-R9 暂停 Vast.ai 实例并记录状态
```

### 7.1 本地准备

本地执行前必须记录：

```bash
git rev-parse HEAD
git status --short
```

正式 acceptance 原则上要求本地工作区和远端工作区都可解释。如果远端需要临时 patch，
必须有 `stage14_remote_patch_manifest.json`。

如果本地或远端验收工作区的 `git status --short` 非空，`stage14_remote_patch_manifest.json`
必须逐项列出：

```text
path
git_status_code
sha256
purpose
enabled_by_command_or_import
rollback_or_cleanup_note
public_or_private
```

未登记的 modified / untracked 文件会导致 `inspect-stage14-fully-async-acceptance --assert-complete`
失败。

### 7.2 远端 smoke 命令

远端命令必须使用真实 fully async 入口：

```bash
PYTHONPATH=src:reference/verl:<run_dir>/scripts:$PYTHONPATH \
python -m verl.experimental.fully_async_policy.fully_async_main \
  <profile generated hydra args...>
```

不能使用普通 `main_ppo` 冒充 fully async。
不能用本地 fake queue 或 fake trainer 代替 `FullyAsyncTrainer`。

### 7.3 实例收尾

完成或遇到无法继续的问题时，必须暂停实例而不是销毁实例：

```bash
.venv/bin/vastai stop instance <instance_id>
.venv/bin/vastai show instance <instance_id>
```

期望状态：

```text
Status exited
```

如果 Vast.ai CLI 不可用，可以让用户手动在控制台暂停实例，但最终 evidence 必须记录实例最终状态。

## 8. 本地实现测试计划

### 8.1 acceptance schema 测试

新增：

```text
tests/unit/test_repo_harness_verl_stage14_acceptance.py
```

覆盖：

- 合法 Stage 14.0 evidence directory 通过。
- 合法 Stage 14.0 evidence tarball 通过。
- 缺少 canonical evidence item 被拒绝。
- `completed_trainer_step_count < 3` 被拒绝。
- `parameter_sync_count < 1` 被拒绝。
- `post_sync_valid_sample_count < 1` 被拒绝。
- `policy_loss_queue_invalid_sample_count != 0` 被拒绝。
- `message_queue_dropped_sample_count != 0` 默认被拒绝。
- `trainer_batch_logprob_provenance_passed=false` 被拒绝。
- stdout 出现 `Traceback`、`CUDA out of memory`、`invalid_for_training_sample_in_formal_batch`
  等关键错误被拒绝。
- remote patch manifest sha256 不匹配被拒绝。
- evidence tarball 中可传播 JSON 泄漏 `/Users/...`、`/workspace/...`、
  `.repo_harness_env_overlay`、`.repo_harness_runtime`、provider secret marker 被拒绝。
- 公开 evidence 中的 JSON、log、YAML、shell script、parquet、source map 泄漏真实远端路径被拒绝。
- tarball 安全检查必须拒绝：绝对路径 entry、`..` 路径穿越、normalize 后重复路径、
  指向 tarball 外部的符号链接或硬链接、device / fifo 等非常规 entry、超过大小上限的单文件或总包。
- `runtime_private/stage14_stdout.raw.log` 等私有文件如果存在，只能出现在
  `runtime_private_manifest.json` 中，并且不能被公开 summary 直接引用为可传播字段。
- 验收器不会反序列化 cloudpickle payload。

### 8.2 remote smoke builder 测试

新增：

```text
tests/unit/test_repo_harness_verl_stage14_remote_smoke_builder.py
```

覆盖：

- `dev_smoke_2x96gb_lora_merged_sync` profile 生成的 Hydra args 包含所有关键配置。
- profile 固定 `gpu_memory_utilization=0.25`、`max_model_len=4608`、`max_num_seqs=2`、
  `max_num_batched_tokens=6144`，并且这些值来自 profile schema，而不是散落在字符串模板中。
- `use_remove_padding`、`enable_gradient_checkpointing`、`enable_activation_offload` 生成在
  `actor_rollout_ref.model.*` 下。
- `log_prob_micro_batch_size_per_gpu` 生成在 `actor_rollout_ref.rollout.*` 下。
- 不设置 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`。
- 设置 `TORCH_CUDA_ARCH_LIST=12.0`。
- 生成的 `repo_harness_agent_loop_config.yaml` 指向正确 target。
- 生成的 parquet schema 包含 `prompt`、`raw_prompt`、`agent_name`、`repo_harness_task_ref`、
  `uid`、`index`、`session_id`、`global_steps`。
- command log 会对环境变量和路径做脱敏。
- remote patch manifest 可以记录 patch path、sha256、enable command 和 rollback note。

### 8.3 回归测试

Stage 14.0 本地实现后至少运行：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src

PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_remote_smoke_builder.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_rl_stage13_0_reward_finality.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_2_message_queue.py \
  tests/unit/test_repo_harness_verl_stage13_2_trainer_batch_visibility.py \
  tests/unit/test_repo_harness_verl_stage13_2_staleness_and_refill.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

如果测试文件名在实际仓库中不同，执行计划实现前必须先用 `rg --files tests` 确认真实路径，
不能把不存在的测试文件写进最终验收命令。

## 9. 远端验收计划

用户准备相同的 `2 * 96GB GPU` 远端实例后，执行步骤为：

1. 本地确认 Stage 14.0 代码提交已经推送。
2. 远端拉取该提交。
3. 运行 Stage 14.0 preflight。
4. 运行 `dev_smoke_2x96gb_lora_merged_sync` 短步数 fully async smoke。
5. 生成并打包 evidence。
6. 下载 evidence 到本地。
7. 本地运行：

```bash
PYTHONPATH=src uv run --extra dev repo-harness \
  inspect-stage14-fully-async-acceptance \
  runs/stage14_0-remote-<timestamp>/stage14_0_evidence.tar.gz \
  --assert-complete
```

8. 暂停 Vast.ai 实例。

远端通过标准：

```text
completed_trainer_step_count >= 3
parameter_sync_count >= 1
current_param_version >= 1
valid_sample_count >= 1
post_sync_valid_sample_count >= 1
policy_loss_queue_invalid_sample_count == 0
policy_loss_gate_passed == true
message_queue_dropped_sample_count == 0
message_queue_consumed_sample_count >= completed_trainer_step_count * required_samples
trainer_batch_logprob_provenance_passed == true
visibility_scan_passed == true
path_leak_scan_passed == true
resource_cleanup_passed == true
所有 consumed sample 的 staleness <= staleness_threshold
inspect-stage14-fully-async-acceptance --assert-complete 退出码为 0
实例最终状态为 exited
```

## 10. 失败分类

Stage 14.0 失败时必须分类，不能只写 `infrastructure_error`：

```text
remote_preflight_failure
dependency_install_failure
fully_async_import_failure
profile_generation_failure
agent_loop_registration_failure
dataset_schema_failure
trainer_startup_failure
rollout_backend_failure
checkpoint_engine_failure
parameter_sync_failure
message_queue_failure
policy_loss_gate_failure
batch_assembly_failure
policy_loss_batch_provenance_failure
visibility_failure
staleness_filter_failure
path_leak_failure
resource_cleanup_failure
evidence_manifest_failure
acceptance_inspector_failure
vastai_instance_lifecycle_failure
```

每个失败都必须写入 summary 或 failure taxonomy report，并保留足够的命令、日志、环境和
patch manifest 证据，方便下一轮远端复现。

## 11. 和后续阶段的关系

Stage 14.0 通过后，只能说明：

```text
fully async 远端链路可以用固定 profile 脚本化复现；
evidence 可以被机器验收；
Stage 13.3-B 的成功不再只依赖人工读日志。
```

Stage 14.0 通过后，仍不能说明：

```text
多任务池稳定；
partial rollout / resume 可用；
旧 CLI / offline export 已经迁移到 run_episode；
动态 SGLang LoRA adapter loading 已修复；
全参数 7B RL 或更多 GPU 配置已经可用。
```

后续顺序应保持：

```text
Stage 14.0：远端链路可复现验收器和脚本化
Stage 14.1：多任务 real episode 扩展和远端负例 side channel
Stage 14.2：partial checkpoint contract
Stage 14.3：RepoHarness pause / resume facade 原型
Stage 15：真实 verl partial_rollout=True 远端 smoke
Stage 16 或独立路线：旧 CLI / offline export 与 run_episode 统一
```
