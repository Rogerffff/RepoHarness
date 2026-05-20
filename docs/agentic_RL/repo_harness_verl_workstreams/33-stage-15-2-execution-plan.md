# Stage 15.2 执行计划：远端 GPU partial_rollout=True 多步 smoke

本文是 Stage 15.2 的具体执行计划。它承接
`01-sequential-implementation-plan.md` 中 Stage 15.2 的高层路线，并建立在
Stage 15.0 的接口盘点、Stage 15.1 的本地 partial rollout adapter / resume scheduler
已经完成的基础上。

Stage 15.2 的目标不是证明模型收敛，也不是做大规模 SWE-Bench 训练。它的目标是：
在远端 2 张 96GB GPU 的真实 verl fully async 环境中，打开真实
`async_training.partial_rollout=True`，证明 RepoHarness 的 partial checkpoint / resume
链路能够和真实 trainer、真实 MessageQueue、真实参数同步和真实 policy loss 路径共同跑通。

本阶段通过后，才能说 RepoHarness 已经具备第一版真实
`partial_rollout=True` agentic RL smoke。Stage 15.1 通过只能说明本地同进程 adapter、
resume scheduler 和 policy-loss gate 已经准备好。

## 1. 阶段目标和非目标

### 1.1 必须证明的目标

Stage 15.2 必须证明下面这条真实链路：

```text
远端 fully_async_main
-> FullyAsyncRollouter / RepoHarnessVerlAgentLoop
-> RepoHarnessRuntime real_episode
-> 安全 turn boundary partial checkpoint
-> RepoHarnessResumeScheduler 恢复原始 live AsyncEpisodeHandle
-> terminal episode / final verifier / reward finality
-> TrainingView / AgentLoopOutput
-> RolloutSample / MessageQueue
-> FullyAsyncTrainer policy loss
-> parameter synchronization
-> 参数同步后继续产生和消费 RepoHarness 样本
```

验收口径：

- `async_training.partial_rollout=True` 或当前 `reference/verl` 等价配置真实生效，不能只在
  RepoHarness 本地 fake producer 中模拟。
- 至少生成 2 个 `PartialEpisodeCheckpoint`。
- 至少 2 个 checkpoint 被 resume 到 terminal episode。
- 至少 2 个 resumed completed samples 进入 policy loss。
- 进入 policy loss 的 resumed samples 必须来自至少 2 个唯一
  `source_partial_checkpoint_id`，至少 2 个唯一 `resume_attempt_id`，且
  `policy_loss_consumed_sample_id` 必须唯一。
- partial checkpoint、pending reward、diagnostic、timeout、cancelled、visibility rejected、
  missing logprob、non-verl route 和 stale 样本不能进入 policy loss。
- trainer 至少完成 3 个 progress step，目标是 3 到 4 个 step。
- 至少发生 1 次训练后 parameter synchronization。
- 参数同步之后仍有新的 resumed RepoHarness valid sample 进入或被 policy loss 消费。
- `trajectory_param_versions`、`min_global_steps`、`max_global_steps`、
  `current_param_version`、`staleness` 和 `filtered_stale_sample_count` 必须可解释。
- 必须实现或使用 `inspect-stage15-partial-rollout-acceptance` 等价机器验收命令。

### 1.2 本阶段不要求

Stage 15.2 不要求：

- 模型收敛。
- 7B 或更大模型训练。
- 4 卡、8 卡或多节点训练。
- 跨进程、跨 Ray actor、跨机器、worker 崩溃后的 durable resume。
- KV cache resume。
- 自然长任务触发 partial rollout。第一版可以使用受控 turn-boundary partial trigger。
- 旧 `repo-harness run-task`、`run-batch`、`run-experiment` 和离线 export 迁移。
- 大规模吞吐达标。

如果远端无法证明真实 `partial_rollout=True` 信号能够到达 RepoHarness，不能用
Stage 15.1 的本地 fake queue 冒充通过。此时应记录为
`partial_rollout_signal_not_visible_to_repo_harness`，并停止进入完整验收。

## 2. 前置状态

Stage 15.0 已经完成接口盘点：

```text
commit: fd0150fc
message: feat: add stage15 partial rollout inventory
evidence: runs/repo-harness-verl-stage15-0-20260520T120647Z/
```

Stage 15.1 已经完成本地 partial rollout adapter 和 resume scheduler：

```text
commit: f79b985c
message: feat: add stage15 partial rollout resume adapter
evidence: runs/repo-harness-verl-stage15-1-20260520T133350Z/
```

Stage 15.2 必须复用 Stage 15.0 / Stage 15.1 的对象和边界：

```text
PartialEpisodeCheckpoint
ResumeStateStore
AsyncEpisodeHandle
RepoHarnessPartialRolloutProducer
RepoHarnessResumeScheduler
PolicyLossGateReport
FormalAsyncOnlineRLSample
validate_formal_async_online_rl_batch(...)
```

不能重新定义 checkpoint schema，不能绕过 formal async validator，也不能把
partial checkpoint 本身放进 policy-loss MessageQueue。

## 3. 默认远端环境和 profile

默认远端 profile：

```text
profile_name = dev_smoke_2x96gb_small_full_sync_partial_rollout
GPU = 2 * RTX PRO 6000 或等价 2 * 96GB GPU
镜像 = verlai/verl:sgl056.latest
模型 = Qwen/Qwen2.5-Coder-1.5B-Instruct
训练策略 = full training
lora_rank = 0
rollout backend = SGLang
weight sync = NIXL CUDA
partial_rollout = true
partial_trigger = controlled_turn_boundary
```

Stage 15.2 的正式通过证据默认必须使用真实 SGLang rollout 服务。如果远端 preflight 证明当前
`reference/verl` 的 fully async partial rollout 只能在 vLLM 后端启动，执行 agent 不能静默切换并
宣称 Stage 15.2 完成。此时只能生成 `fully_async_backend_incompatible` 或 partial evidence，除非先更新
高层计划、另起独立 profile 名称，并取得用户确认。

默认先使用 2 张 96GB GPU，不主动要求 4 卡。只有当远端 preflight 明确证明资源池、显存、
Ray placement group 或 backend 约束无法在 2 卡上启动时，才记录
`resource_pool_incompatibility` 并向用户报告是否需要改租 4 卡。

资源划分建议：

```text
trainer.n_gpus_per_node = 1
rollout.n_gpus_per_node = 1
```

实际 Hydra key 必须以当前 `reference/verl` 为准。执行前需要先做配置解析 dry run，
把最终生效的 overrides 写入 `stage15_hydra_overrides.json`。

## 4. 关键风险和硬性前置门

### 4.1 verl 原生 partial rollout 不等于 RepoHarness checkpoint

Stage 15.0 已经确认：verl 原生 `partial_rollout=True` 主要发生在参数同步、
推理服务 abort / resume generation、`FullyLLMServerClient` 续生成等路径中。它可能不会天然把
“中断点”传给 `RepoHarnessVerlAgentLoop`。

因此 Stage 15.2 必须先通过一个真实信号门：

```text
async_training.partial_rollout=True
-> 参数同步或受控触发导致 rollout partial / abort / resume 路径执行
-> RepoHarnessVerlAgentLoop 或其 wrapper 能观察到可解释 partial boundary
-> 生成 PartialEpisodeCheckpoint
-> checkpoint 进入 resume queue 或 diagnostic side channel
```

如果信号不能到达 RepoHarness，必须输出：

```text
stage15_partial_checkpoint_report.json:
  partial_signal_visible_to_repo_harness = false
  patch_or_wrapper_required = true
  failure_code = partial_rollout_signal_not_visible_to_repo_harness
```

不能继续声称 Stage 15.2 通过。

### 4.2 policy-loss MessageQueue 只能接收 valid terminal sample

真实 `FullyAsyncTrainer` 消费 MessageQueue 时不会理解 RepoHarness 的所有 rejected /
diagnostic 语义。Stage 15.2 不能把 partial checkpoint、pending reward、diagnostic 或 stale
样本放入真实 policy-loss MessageQueue 后再指望 trainer-side 过滤。

硬性规则：

```text
真实 policy-loss MessageQueue:
  只允许 valid terminal complete sample。

diagnostic side channel:
  partial checkpoint
  pending reward
  stale
  visibility rejected
  missing logprob
  non-verl route
  timeout / cancelled
  partial resume timeout
  format failure
```

如果为了测试 negative gate 需要构造坏样本，必须放在 diagnostic side channel 或受控本地
filter test 中，不能让真实 trainer 把它们计入 `required_samples`。

### 4.3 远端 patch 和 helper 必须进入 manifest

如果 Stage 15.2 需要任何远端 patch、monkey patch、`sitecustomize.py`、运行时 helper、
SGLang wrapper、NIXL wrapper 或 `reference/verl` 修改，必须登记到：

```text
stage15_remote_patch_manifest.json
```

每个条目至少包含：

```text
relative_path
sha256
purpose
enabled_by
rollback_method
public_or_runtime_private
```

未登记 patch 或 helper 不能通过验收。如果没有 patch，manifest 也必须存在，并写明：

```json
{
  "patch_required": false,
  "files": [],
  "reason": "no_remote_patch_or_helper_used"
}
```

### 4.4 public / runtime_private evidence 分层

公开 evidence 不能泄漏远端绝对路径、workspace path、dependency environment path、hidden
runtime path、provider raw payload、evaluator-only 信息或 verifier hidden expectation。

命令日志必须分层：

```text
stage15_command_log.sanitized.jsonl
runtime_private/stage15_command_log.raw.jsonl
```

公开 JSON、JSONL、YAML、shell script、Python helper、文本日志、parquet、source map 和 manifest
都必须经过 path leak scan。runtime-private raw evidence 可以保留真实路径，但必须标记为
`runtime_private`，不能进入公开 acceptance summary 的可传播字段。

## 5. 远端执行总流程

Stage 15.2 分为十个子步骤：

```text
15.2-0 本地代码和测试预检
15.2-1 远端实例、镜像、依赖和代码同步预检
15.2-2 fully async partial rollout 配置解析和 backend dry run
15.2-3 真实 partial signal / RepoHarness checkpoint 形状 gate
15.2-4 任务池和数据集冻结
15.2-5 受控 partial checkpoint 生成 smoke
15.2-6 resume scheduler 远端集成 smoke
15.2-7 真实 fully async trainer 多步 smoke
15.2-8 diagnostic / rejected / stale / visibility side channel 验证
15.2-9 evidence 打包、机器验收、实例暂停和同步
```

每一步都必须写入 sanitized command log 和 raw command log。失败也必须生成结构化 failure
taxonomy，不能只留下 stdout。

## 6. 15.2-0 本地代码和测试预检

远端执行前，本地必须完成：

```bash
PYTHONPATH=src uv run --extra dev python -m compileall -q src
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_resume.py \
  tests/unit/test_repo_harness_verl_stage15_0_inventory.py \
  tests/unit/test_repo_harness_verl_stage15_0_patch_plan.py \
  tests/unit/test_repo_harness_verl_stage15_0_acceptance.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_schema.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_visibility.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_tamper.py \
  tests/unit/test_repo_harness_rl_stage14_2_partial_checkpoint_policy_gate.py \
  tests/unit/test_repo_harness_rl_stage14_3_pause_resume_facade.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
PYTHONPATH=src uv run --extra dev python - <<'PY'
import sys
import repo_harness.rl
import repo_harness_verl
for name in ("verl", "torch", "ray", "tensordict"):
    assert name not in sys.modules, name
print("ordinary_import_ok")
PY
if rg -n '(^|\s)(import|from)\s+verl' src/repo_harness; then
  exit 1
fi
git diff --check -- \
  src/repo_harness \
  src/repo_harness_verl \
  tests/unit \
  docs/agentic_RL/repo_harness_verl_workstreams
```

如果本地有未提交代码，远端 evidence 必须记录准确 commit 和 patch manifest。推荐在远端执行前
先提交本地 Stage 15.2 计划与任何新增验收器代码，避免 evidence 指向不可复现工作区。

## 7. 15.2-1 远端实例和依赖预检

远端实例启动后，先执行只读预检，不直接启动训练：

```text
检查 GPU 数量、显存、驱动、CUDA、NCCL、NIXL、Python、Ray、torch、transformers、
SGLang、vLLM、verl、reference/verl commit、RepoHarness commit、磁盘剩余空间、模型缓存目录。
```

输出：

```text
stage15_environment_matrix.json
stage15_remote_preflight.json
stage15_command_log.sanitized.jsonl
runtime_private/stage15_command_log.raw.jsonl
```

`stage15_environment_matrix.json` 至少包含：

```text
image_name
python_version
cuda_version
torch_version
ray_version
sglang_version
vllm_version
transformers_version
verl_package_version_or_commit
reference_verl_commit
repo_harness_commit
gpu_model
gpu_count
gpu_memory_gb_each
checkpoint_engine_backend
checkpoint_engine_resolved_config
weight_sync_strategy
rollout_backend
model_id
model_revision
```

如果远端代码需要从 GitHub 拉取，必须确认：

```text
git rev-parse HEAD
git status --short
```

如果 `git status --short` 非空，必须进入 `stage15_remote_patch_manifest.json`。未登记的 dirty
worktree 不能通过验收。

## 8. 15.2-2 fully async partial rollout 配置解析和 backend dry run

这一阶段先解析配置，不直接跑完整训练。

必须生成 RepoHarness agent loop YAML，例如：

```yaml
- name: repo_harness
  _target_: repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop
```

同时必须在 resolved config 或 dataset parquet 中证明 `agent_name=repo_harness` 已经进入
`DataProto.non_tensor_batch`。如果某条样本缺少 `agent_name=repo_harness`，verl 可能回退到
`single_turn_agent`，这条样本不能作为 Stage 15.2 的有效证据。

训练命令模板必须显式设置关键字段。实际 key 以当前 `reference/verl` 为准，下面是必须覆盖的语义：

```bash
REPO_ROOT=<absolute_repo_root>
PYTHONPATH=$REPO_ROOT/src:$REPO_ROOT/reference/verl:$PYTHONPATH \
python -m verl.experimental.fully_async_policy.fully_async_main \
  data.train_files=<stage15_train.parquet> \
  data.val_files=<stage15_val.parquet> \
  data.prompt_key=prompt \
  data.return_raw_chat=True \
  data.train_batch_size=0 \
  data.gen_batch_size=1 \
  trainer.nnodes=1 \
  trainer.n_gpus_per_node=1 \
  rollout.nnodes=1 \
  rollout.n_gpus_per_node=1 \
  actor_rollout_ref.model.path=Qwen/Qwen2.5-Coder-1.5B-Instruct \
  actor_rollout_ref.model.lora_rank=0 \
  actor_rollout_ref.hybrid_engine=False \
  actor_rollout_ref.actor.ppo_mini_batch_size=1 \
  actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.actor.ppo_epochs=1 \
  actor_rollout_ref.actor.use_rollout_log_probs=True \
  critic.enable=False \
  reward.reward_model.enable=False \
  algorithm.rollout_correction.bypass_mode=True \
  actor_rollout_ref.rollout.mode=async \
  actor_rollout_ref.rollout.multi_turn.enable=True \
  actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness \
  actor_rollout_ref.rollout.agent.agent_loop_config_path=<repo_harness_agent_loop.yaml> \
  actor_rollout_ref.rollout.calculate_log_probs=True \
  actor_rollout_ref.rollout.name=sglang \
  async_training.partial_rollout=True \
  async_training.trigger_parameter_sync_step=2 \
  async_training.require_batches=1 \
  async_training.staleness_threshold=1 \
  rollout.total_rollout_steps=16 \
  actor_rollout_ref.rollout.checkpoint_engine.backend=nixl \
  +actor_rollout_ref.rollout.checkpoint_engine.engine_kwargs.nixl.device=cuda
```

需要特别检查：

- `actor_rollout_ref.hybrid_engine=False`。当前 fully async 路径不应使用 hybrid engine。
- `actor_rollout_ref.rollout.multi_turn.enable=True`。否则 verl 可能走 `single_turn_agent`。
- `actor_rollout_ref.rollout.agent.agent_loop_config_path` 必须是完整真实 key。
- `actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness` 必须生效，不能回退到
  `single_turn_agent`。
- `trainer.nnodes`、`trainer.n_gpus_per_node`、`rollout.nnodes`、`rollout.n_gpus_per_node` 必须
  显式设置为 2 卡 smoke 可执行的值，不能继承 8 卡默认值。
- `actor_rollout_ref.actor.ppo_mini_batch_size`、`ppo_micro_batch_size_per_gpu`、`ppo_epochs`、
  `data.gen_batch_size`、`async_training.require_batches` 必须设置为小 batch smoke 值，不能继承
  256 样本级别的默认训练配置。
- `actor_rollout_ref.actor.use_rollout_log_probs=True` 必须生效，确保 policy loss 使用 rollout
  侧 log probabilities，且 Stage 15 batch provenance 能回查。
- `critic.enable=False`、`reward.reward_model.enable=False`、`algorithm.rollout_correction.bypass_mode=True`
  必须与当前 smoke profile 一致，避免引入本阶段不验收的 critic / reward model 路径。
- NIXL 权重同步的配置必须使用当前 verl 真实嵌套 key，例如
  `actor_rollout_ref.rollout.checkpoint_engine.backend=nixl`，不能使用误导性的顶层
  `checkpoint_engine.backend=nixl`。
- `async_training.partial_rollout=True` 必须出现在最终 Hydra resolved config 中。
- `data.train_files` 和 `data.val_files` 必须指向 Stage 15.2 自己生成的 parquet，不允许误用默认数据集。
- `data.train_batch_size`、`data.gen_batch_size` 和 `async_training.require_batches` 必须显式记录，
  并与 `stage15_training_profile.json` 中的 `required_samples` 或等价字段一致。
- 远端命令必须使用绝对 `REPO_ROOT` 生成 `PYTHONPATH`。公开 evidence 只能保留脱敏后的
  `$REPO_ROOT/src:$REPO_ROOT/reference/verl`，真实绝对路径只能进入 `runtime_private`。
- 如果 SGLang fully async partial dry run 失败，不能静默切换 vLLM 并宣称正式通过。除非用户确认并
  更新高层计划和 profile，否则 vLLM fallback 只允许形成 partial evidence。

输出：

```text
stage15_hydra_overrides.json
stage15_backend_preflight_report.json
```

## 9. 15.2-3 真实 partial signal / checkpoint 形状 gate

多步训练前必须先跑一个小型 gate，证明真实链路形状闭合。

gate 需要证明：

```text
fully_async_main 或等价远端入口启动
-> FullyAsyncRollouter 调用 RepoHarnessVerlAgentLoop
-> RepoHarnessRuntime real_episode 启动
-> controlled turn boundary 产生 PartialEpisodeCheckpoint
-> checkpoint 写入 resume queue 或 diagnostic side channel
-> partial checkpoint 没有进入 policy-loss MessageQueue
```

gate 必须记录：

```text
partial_rollout_enabled
partial_signal_visible_to_repo_harness
native_partial_rollout_enabled
native_abort_resume_observed
native_abort_signal_visible_to_repo_harness
controlled_turn_boundary_trigger_used
repo_harness_checkpoint_generated_by_controlled_trigger
partial_checkpoint_count
partial_checkpoint_ids
source_episode_ids
source_run_ids
checkpoint_content_digests
checkpoint_generation_record_digests
checkpoint_visibility_scan_digests
policy_loss_consumed_partial_count
```

这些字段必须把两件事情分开说明：

```text
verl 原生 partial rollout / abort / resume_generation 信号是否真实发生；
RepoHarness 是否使用受控 turn-boundary trigger 生成 PartialEpisodeCheckpoint。
```

如果最终 checkpoint 是由 `controlled_turn_boundary_trigger_used=true` 产生的，报告必须明确写出
`repo_harness_checkpoint_generated_by_controlled_trigger=true`，不能把它误描述成 verl 底层
`abort / resume_generation` 直接产生的 checkpoint boundary。

如果 `partial_signal_visible_to_repo_harness=false`，Stage 15.2 不继续跑完整训练；此时输出
patch plan / wrapper plan 即可。

## 10. 15.2-4 任务池和数据集冻结

Stage 15.2 的数据集可以复用 Stage 14.1 的极小任务池，但要加入受控 partial trigger 字段。

建议包含：

```text
accepted_baseline:
  repo: tests/fixtures/repos/security_probe
  task_ref: tests/fixtures/tasks/task_security_probe.yaml
  目标：无外部依赖基线任务。

accepted_src_layout:
  repo: tests/fixtures/repos/import_config_bug
  task_ref: tests/fixtures/tasks/task_002.yaml
  目标：覆盖 src / package import。

accepted_create_file:
  repo: tests/fixtures/repos/missing_helper_file
  task_ref: tests/fixtures/tasks/task_003_create_file.yaml
  目标：覆盖 create_file 工具。

partial_resume_control:
  repo: 使用上述任一极小任务，但通过 dataset kwargs / runtime-only config 控制 turn-boundary pause。
  目标：稳定产生至少 2 个 checkpoint。
```

每条 parquet row 必须包含真实 `RepoHarnessVerlAgentLoop` 需要的字段：

```text
raw_prompt
agent_name = repo_harness
repo_harness_task_ref
repo_harness_run_config_ref
repo_harness_runtime_execution_mode = real_episode
repo_harness_run_mode = training_fast
repo_harness_partial_rollout_control
repo_harness_expected_route = verl
```

`repo_harness_partial_rollout_control` 是 runtime-only 或 dataset control 字段，不能进入模型可见 prompt，
也不能进入 TrainingView / AgentLoopOutput / DataProto 的模型可见字段。公开 evidence 只能记录
其 opaque ref、sha256、用途和非敏感摘要。

输出：

```text
stage15_fixture_manifest.json
stage15_fixture_sha256_report.json
stage15_dataset_manifest.json
```

## 11. 15.2-5 受控 partial checkpoint 生成 smoke

这一阶段的目标是产生至少 2 个 partial checkpoints。

必须验证：

```text
partial_checkpoint_count >= 2
source_partial_checkpoint_id 唯一数量 >= 2
每个 checkpoint 都有 content_digest / trajectory_digest / generation_record_digest
每个 checkpoint 都有 batch-safe projection
每个 checkpoint 都不能通过 policy-loss gate
每个 checkpoint 都能进入 resume queue 或 diagnostic side channel
```

需要额外构造或捕获至少一条 partial negative：

```text
partial checkpoint 被错误标记为 complete 的样本必须被拒绝
缺少 external visibility ledger 的 checkpoint 必须被拒绝
message queue drop 伪装成 checkpoint 的样本必须被拒绝
```

输出：

```text
stage15_partial_checkpoint_report.json
stage15_visibility_report.json
stage15_side_channel_report.json
```

## 12. 15.2-6 resume scheduler 远端集成 smoke

这一阶段必须从真实 partial checkpoint 恢复至少 2 条 terminal episode。

resume 条件：

```text
同一 rollouter worker / 同一 Ray actor / 同一 runtime ownership scope
live AsyncEpisodeHandle 存在
ResumeStateStore entry 存在
checkpoint_id、content_digest、run_id、lease_token、recorder cursor digest、
generation record digest 均匹配
resume_wait_timeout_seconds 有界
resume_cancel_wait_timeout_seconds 有界
```

resume 失败时：

```text
进入 diagnostic side channel
不能进入 policy-loss queue
不能留下 run_id lock、workspace lease、active handle 或 run_status=RUNNING
```

resume 成功后：

```text
resumed_terminal_episode_count >= 2
resumed_valid_sample_count >= 2
resumed samples 重新通过 formal online RL 和 formal async validator
resumed samples 重新绑定 response_ids / response_logprobs / generation_records / response_spans
```

输出：

```text
stage15_resume_scheduler_report.json
stage15_resource_lifecycle_report.json
```

## 13. 15.2-7 真实 fully async trainer 多步 smoke

这一阶段运行真实 trainer 多步 smoke。目标是 3 到 4 个 trainer progress step，至少一次训练后
parameter synchronization。

参数同步计数必须区分初始化同步和训练后同步。`fully_async_main` 启动时可能执行一次初始化
`_fit_update_weights(...)`，这不能被单独当作 Stage 15.2 的参数同步成功。报告需要分别记录：

```text
initial_parameter_sync_count
post_train_parameter_sync_count
post_train_parameter_sync_after_step
parameter_sync_count
```

通过标准使用 `post_train_parameter_sync_count >= 1`，并要求同步之后仍有新的 resumed valid sample
被生成或进入 policy loss。

建议参数：

```text
required_samples = 1 或当前 profile 可稳定支持的最小值
trigger_parameter_sync_step = 2
total_rollout_steps >= 16
completed_trainer_step_count 目标 = 3 到 4
```

如果 `required_samples > 1`，所有按 step 计算的验收都必须乘以 `required_samples`。例如：

```text
message_queue_consumed_sample_count >= completed_trainer_step_count * required_samples
accepted_for_policy_loss_count >= completed_trainer_step_count * required_samples
```

policy-loss 消费样本必须满足：

```text
route = verl
response_ids 非空
response_logprobs 非空并长度一致
generation_records 非空
response_spans 与 generation_records 对齐
reward_state = final
visibility_scan_passed = true
invalid_for_training = false
invalid_for_online_rl = false
partial_rollout_status = complete 或 not_requested
source_partial_checkpoint_id / resume_attempt_id 对 resumed sample 可回查
```

必须记录每条被 policy loss 消费的样本：

```text
policy_loss_consumed_sample_id
episode_id
run_id
task_id
trainer_step
global_step
parameter_version
min_global_steps
max_global_steps
trajectory_param_versions
source_partial_checkpoint_id
resume_attempt_id
training_view_digest
generation_record_digest
trajectory_digest
response_ids_digest
response_mask_digest
rollout_log_probs_digest
```

输出：

```text
stage15_policy_loss_gate_report.json
stage15_trainer_steps_report.json
stage15_parameter_sync_report.json
stage15_batch_provenance_report.json
stage15_message_queue_report.json
```

## 14. 15.2-8 diagnostic / rejected / stale / visibility side channel

Stage 15.2 必须证明坏样本不会进入 policy loss。可以使用受控构造，不要求都由真实模型自然产生。

必须覆盖：

```text
partial_checkpoint_not_terminal
pending_reward
stale_trajectory
visibility_rejected
missing_logprob
non_verl_route
timeout
cancelled
resume_timeout
message_queue_drop
partial_disguised_as_complete
```

每类样本必须记录：

```text
sample_id
classification
rejection_reason
side_channel_ref
policy_loss_consumed = false
visibility_scan_status
staleness
partial_rollout_status
reward_state
```

输出：

```text
stage15_side_channel_report.json
stage15_staleness_report.json
stage15_visibility_report.json
```

## 15. 15.2-9 evidence 打包、验收和实例暂停

远端结束时必须生成 canonical evidence 目录，并打包成 tarball。

公开 evidence 至少包含：

```text
stage15_acceptance_summary.json
stage15_partial_checkpoint_report.json
stage15_resume_scheduler_report.json
stage15_policy_loss_gate_report.json
stage15_trainer_steps_report.json
stage15_parameter_sync_report.json
stage15_staleness_report.json
stage15_message_queue_report.json
stage15_side_channel_report.json
stage15_visibility_report.json
stage15_batch_provenance_report.json
stage15_remote_patch_manifest.json
stage15_resource_lifecycle_report.json
stage15_path_leak_scan_report.json
stage15_command_log.sanitized.jsonl
stage15_training_profile.json
stage15_hydra_overrides.json
stage15_environment_matrix.json
stage15_fixture_manifest.json
stage15_fixture_sha256_report.json
stage15_canonical_evidence_map.json
```

私有 evidence 至少包含：

```text
runtime_private/stage15_command_log.raw.jsonl
runtime_private/raw_stdout.log
runtime_private/raw_stderr.log
runtime_private/ray_logs/
```

`stage15_acceptance_summary.json` 至少包含：

```text
acceptance_passed
training_profile_name
partial_rollout_enabled
native_partial_rollout_enabled
native_abort_resume_observed
native_abort_signal_visible_to_repo_harness
controlled_turn_boundary_trigger_used
repo_harness_checkpoint_generated_by_controlled_trigger
partial_checkpoint_count
resume_attempt_count
resumed_terminal_episode_count
resumed_valid_sample_count
resumed_policy_loss_consumed_sample_count
resumed_policy_loss_consumed_unique_checkpoint_count
resumed_policy_loss_consumed_unique_resume_attempt_count
partial_policy_loss_consumed_sample_count
pending_reward_policy_loss_consumed_sample_count
stale_policy_loss_consumed_sample_count
diagnostic_policy_loss_consumed_sample_count
completed_trainer_step_count
parameter_sync_count
initial_parameter_sync_count
post_train_parameter_sync_count
post_train_parameter_sync_after_step
current_param_version
post_sync_resumed_valid_sample_count
message_queue_produced_sample_count
message_queue_consumed_sample_count
message_queue_dropped_sample_count
side_channel_sample_count
policy_loss_queue_invalid_sample_count
visibility_rejected_policy_loss_consumed_sample_count
missing_logprob_policy_loss_consumed_sample_count
non_verl_route_policy_loss_consumed_sample_count
timeout_policy_loss_consumed_sample_count
cancelled_policy_loss_consumed_sample_count
resume_timeout_policy_loss_consumed_sample_count
trainer_batch_logprob_provenance_passed
visibility_scan_passed
path_leak_scan_passed
resource_cleanup_passed
instance_final_status
training_profile_sha256
hydra_overrides_sha256
fixture_manifest_sha256
public_path_leak_scan_passed
runtime_private_evidence_present
remote_patch_manifest_sha256
evidence_tarball_sha256
```

实例最终状态必须重新采集，不能沿用训练结束时写入的旧状态。接受的规范化状态：

```text
actual_status = exited
或
cur_state = stopped / paused / exited
```

如果 summary 仍写 `running`，即使事后实例已经暂停，也不能通过
`--assert-complete`。

## 16. 机器验收命令

Stage 15.2 必须实现或复用下面等价命令：

```bash
PYTHONPATH=src uv run --extra dev repo-harness inspect-stage15-partial-rollout-acceptance \
  <stage15_evidence.tar.gz> \
  --assert-complete
```

验收器必须检查：

- tarball 安全：拒绝绝对路径、`..` 路径穿越、符号链接、硬链接、device、fifo、
  重复 normalize 后路径、超过大小上限的文件。
- profile / Hydra / environment matrix / acceptance summary 一致。
- patch manifest 覆盖所有公开 helper 和远端修改。
- public evidence 路径泄漏扫描通过。扫描范围必须覆盖公开 JSON、JSONL、YAML、shell script、
  Python helper、文本日志、parquet、source map 和 sanitized command log。
- runtime-private evidence 存在但不进入 public summary 可传播字段。
- `partial_rollout_enabled=true`。
- partial checkpoint、resumed sample、resume attempt、policy-loss consumed sample 的唯一性。
- partial checkpoint、pending reward、stale、diagnostic、visibility rejected、missing logprob、
  non-verl route、timeout、cancelled 和 resume timeout 样本没有进入 policy loss。
- resumed terminal valid samples 进入 policy loss。
- batch logprob provenance 包含 response ids、mask、rollout log probabilities 的 shape 和 digest。
- 至少 3 个 trainer step，至少 1 次训练后 parameter sync。
- 参数同步后至少 1 个 resumed valid sample 被生成或消费。
- `runtime_private` 文件名和远端真实绝对路径不能出现在 public summary 的可传播字段中。
- 远端实例最终状态是 stopped / paused / exited 等价状态。

## 17. 通过标准

Stage 15.2 通过必须满足：

```text
partial_rollout_enabled = true
partial_checkpoint_count >= 2
resumed_terminal_episode_count >= 2
resumed_policy_loss_consumed_sample_count >= 2
resumed_policy_loss_consumed_unique_checkpoint_count >= 2
resumed_policy_loss_consumed_unique_resume_attempt_count >= 2
partial_policy_loss_consumed_sample_count = 0
pending_reward_policy_loss_consumed_sample_count = 0
stale_policy_loss_consumed_sample_count = 0
diagnostic_policy_loss_consumed_sample_count = 0
policy_loss_queue_invalid_sample_count = 0
visibility_rejected_policy_loss_consumed_sample_count = 0
missing_logprob_policy_loss_consumed_sample_count = 0
non_verl_route_policy_loss_consumed_sample_count = 0
timeout_policy_loss_consumed_sample_count = 0
cancelled_policy_loss_consumed_sample_count = 0
resume_timeout_policy_loss_consumed_sample_count = 0
message_queue_dropped_sample_count = 0
completed_trainer_step_count >= 3
post_train_parameter_sync_count >= 1
post_sync_resumed_valid_sample_count >= 1
trainer_batch_logprob_provenance_passed = true
visibility_scan_passed = true
path_leak_scan_passed = true
resource_cleanup_passed = true
public_path_leak_scan_passed = true
runtime_private_evidence_present = true
instance_final_status = stopped / paused / exited 等价状态
```

任何一个条件不满足，都不能把 Stage 15.2 标记为完成。可以保留为 partial evidence，
但必须在 summary 中写：

```text
acceptance_passed = false
failure_code = ...
```

## 18. 失败分类

远端失败必须落到结构化分类，至少包括：

```text
remote_preflight_failed
fully_async_backend_incompatible
partial_rollout_config_not_effective
partial_rollout_signal_not_visible_to_repo_harness
checkpoint_generation_failed
resume_scheduler_ownership_missing
resume_timeout
policy_loss_queue_contaminated
trainer_step_not_completed
parameter_sync_missing
post_sync_resumed_sample_missing
logprob_provenance_missing
visibility_or_path_leak
resource_cleanup_failed
instance_not_stopped
evidence_incomplete
profile_hydra_mismatch
patch_manifest_incomplete
```

失败不是坏事，但失败必须可解释、可复现、可审计。尤其是
`partial_rollout_signal_not_visible_to_repo_harness` 和 `resume_scheduler_ownership_missing`，它们代表
Stage 15.0 / Stage 15.1 与真实 verl runtime 的衔接还缺 patch 或 wrapper，不应被包装成普通模型失败。

## 19. 实施顺序建议

推荐执行顺序：

1. 本地补 `inspect-stage15-partial-rollout-acceptance` 或等价验收器。
2. 本地补 Stage 15.2 evidence schema / report builder 测试。
3. 本地跑 Stage 15.0 / 15.1 / 14.3 / 13.3-A 关键回归。
4. 启动远端 2 * 96GB GPU 实例。
5. 做远端 preflight 和 backend dry run。
6. 先跑 partial signal / checkpoint shape gate。
7. gate 通过后再跑完整多步 trainer smoke。
8. 生成 evidence，运行验收器。
9. 暂停实例，重新采集实例最终状态。
10. 下载 evidence 到本地，复跑验收器，并交给子代理只读复核。

如果第 6 步失败，不继续烧 GPU 跑完整训练；优先补 patch plan 或 wrapper plan。

## 20. 与后续阶段的关系

Stage 15.2 通过后，可以说：

```text
RepoHarness 的第一版真实 verl partial rollout / resume agentic RL smoke 已经跑通。
```

但它仍不代表：

```text
跨机器 durable resume 已完成
KV cache resume 已完成
长任务自然 partial 触发已经稳定
大规模 SWE-Bench 训练已经完成
旧 CLI / 离线 export 已迁移到 RepoHarnessRuntime.run_episode(...)
```

这些都应进入 Stage 16 或后续独立路线，不能在 Stage 15.2 里顺手扩大范围。
