# Stage 13.3-B 远端 fully async smoke 运行手册

本文记录 RepoHarness 接入 verl fully async 链路时，在远端 `2 x RTX PRO 6000` 实例上执行 Stage 13.3-B smoke 遇到的问题、根因、解决方案和推荐配置。目标是让后续远端训练或 smoke 可以直接复用这份排障经验，减少重复配置和重复踩坑。

本文不包含任何 Vast.ai API key、SSH 私钥、Hugging Face token 或 provider secret。远端实例控制命令可以参考 `docs/agentic_RL/vastai_cli.md`，但不要把其中的本机认证信息复制到报告或证据包。

## 本次最终通过状态

最终通过的远端 smoke 信息如下：

```text
阶段：Stage 13.3-B
实例：Vast.ai Instance ID 37021004
硬件：2 x NVIDIA RTX PRO 6000 Blackwell Workstation Edition，每张约 96GB 显存
镜像：verlai/verl:sgl056.latest
模型：Qwen/Qwen2.5-Coder-7B-Instruct
训练方式：LoRA training + merged weight sync to SGLang
rollout 后端：SGLang
checkpoint engine：nccl
trainer step：4/4 完成
max current_param_version：4
parameter sync count：5
Batch assembly completed：8 次
successful loop collection：8 次
最终实例状态：exited
```

本地证据包位置：

```text
runs/stage13_3b-remote-final-20260518T174537Z/stage13_3b_final_evidence.tar.gz
```

关键验收摘要位置：

```text
runs/stage13_3b-remote-final-20260518T174537Z/runs/stage13_3b-20260518T174537Z/stage13_3b_acceptance_summary.json
```

最终验收摘要中关键字段：

```json
{
  "acceptance_passed": true,
  "completed_trainer_step_count": 4,
  "max_current_param_version": 4,
  "parameter_sync_count": 5,
  "batch_assembly_completed_count": 8,
  "successful_loop_collection_count": 8,
  "remote_command_exit_code": 0
}
```

## 推荐实例和是否需要 4 卡

Stage 13.3-B 级别的 smoke 不需要直接租 4 卡。当前推荐是：

```text
首选：2 x RTX PRO 6000，单卡 96GB
磁盘：至少 300GB
镜像：verlai/verl:sgl056.latest
```

2 卡足够跑通以下目标：

- 一个 GPU 用于 trainer；
- 一个 GPU 用于 SGLang rollout；
- 使用 LoRA 降低训练侧优化器显存；
- 使用 merged weight sync 把权重同步到 SGLang；
- 完成 3 到 4 个 fully async trainer step；
- 至少一次训练后参数同步，当前 smoke 已经推进到 `current_param_version=4`。

以下情况再考虑 4 卡：

- 要做全参数 7B 更新，而不是 LoRA；
- 要提高 `required_samples`、并发 rollout 数或 batch size；
- 要同时跑多个 rollout replica；
- 要测试更大模型；
- 要恢复动态 SGLang LoRA adapter loading 路径，而不是 merged weight sync；
- 要做更接近真实吞吐压测，而不是功能 smoke。

## 最终推荐配置核心

最终通过的方向是：

```text
LoRA training
-> trainer 侧只训练 LoRA 参数，降低优化器状态显存
-> 同步到 SGLang 时使用 merged weight sync
-> 不走 SGLang 动态 LoRA adapter request
```

关键配置项：

```text
actor_rollout_ref.hybrid_engine=False
actor_rollout_ref.rollout.name=sglang
actor_rollout_ref.rollout.mode=async
actor_rollout_ref.rollout.checkpoint_engine.backend=nccl
actor_rollout_ref.rollout.multi_turn.enable=True
actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness
actor_rollout_ref.rollout.agent.num_workers=1
actor_rollout_ref.rollout.agent.agent_loop_config_path=<repo_harness_agent_loop_config.yaml>

actor_rollout_ref.model.lora_rank=8
actor_rollout_ref.model.lora_alpha=16
actor_rollout_ref.model.target_modules='["q_proj","v_proj"]'
actor_rollout_ref.model.lora.merge=True

actor_rollout_ref.actor.ppo_mini_batch_size=1
actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1
actor_rollout_ref.actor.ppo_epochs=1
actor_rollout_ref.actor.fsdp_config.param_offload=True
actor_rollout_ref.actor.fsdp_config.optimizer_offload=True
actor_rollout_ref.actor.fsdp_config.use_orig_params=True

rollout.nnodes=1
rollout.n_gpus_per_node=1
trainer.nnodes=1
trainer.n_gpus_per_node=1

async_training.trigger_parameter_sync_step=2
async_training.require_batches=1
async_training.staleness_threshold=1
async_training.partial_rollout=False
rollout.total_rollout_steps=8
```

`rollout.total_rollout_steps=8` 在当前 `required_samples=1`、`trigger_parameter_sync_step=2` 的配置下，能够产生 4 个 trainer progress step。更短的 debug 可以用 `rollout.total_rollout_steps=2`，只用于快速确认链路，不作为最终验收。

## 必须设置或避免的环境变量

建议设置：

```bash
export TORCH_CUDA_ARCH_LIST=12.0
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=true
export CUDA_DEVICE_MAX_CONNECTIONS=1
```

不要设置：

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

原因：SGLang 的 `TorchMemorySaver` 在本次镜像中不接受 `expandable_segments=True`，会在启动阶段失败。这个配置对某些普通 PyTorch OOM 有帮助，但在本次 SGLang fully async 路径中反而是启动阻断项。

## AgentLoop 配置

远端需要生成一个明确的 agent loop 配置文件，例如：

```yaml
- name: repo_harness
  _target_: stage13_3b_runtime.Stage13BRepoHarnessAgentLoop
```

Hydra 参数必须指向真实路径：

```text
actor_rollout_ref.rollout.agent.agent_loop_config_path=<run_dir>/repo_harness_agent_loop_config.yaml
actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness
actor_rollout_ref.rollout.multi_turn.enable=True
```

如果漏掉 `multi_turn.enable=True`，verl 的数据准备路径可能把样本改成默认单轮 agent，导致绕开 RepoHarness agent loop。

命令运行时需要保证 Python 能导入本地 RepoHarness 和 reference verl：

```bash
PYTHONPATH=src:reference/verl:<run_dir>/scripts:$PYTHONPATH \
python -m verl.experimental.fully_async_policy.fully_async_main ...
```

## 数据集字段要求

训练 parquet 至少需要包含：

```text
prompt
raw_prompt
agent_name=repo_harness
repo_harness_task_ref
uid
index
session_id
global_steps
```

推荐显式设置：

```text
data.train_files=<stage13_3b_train.parquet>
data.val_files=<stage13_3b_val.parquet>
data.prompt_key=prompt
data.return_raw_chat=True
data.train_batch_size=0
data.gen_batch_size=1
data.max_prompt_length=4096
data.max_response_length=256
```

如果没有 `raw_prompt`，`RepoHarnessVerlAgentLoop` 会拒绝构造 `RepoHarnessEpisodeRequest`。如果没有正确的 `repo_harness_task_ref`，真实 runtime bridge 无法解析对应任务。

## 问题记录和解决方案

### 1. PyTorch 编译架构设置错误

现象：

```text
远端启动或编译扩展时出现 Blackwell 架构相关失败
```

解决：

```bash
export TORCH_CUDA_ARCH_LIST=12.0
```

原因：RTX PRO 6000 Blackwell 需要明确 CUDA 架构列表，避免扩展编译或运行时使用不兼容默认值。

### 2. checkpoint engine 找不到 nccl 注册

现象：

```text
Checkpoint engine nccl not registered
```

解决：

```bash
pip install cupy-cuda12x==13.6.0
```

本次镜像中安装后 `nccl` checkpoint engine 才能正常注册和使用。

### 3. Ray placement 或 CPU 资源等待

现象：

```text
Ray placement group pending
组件启动后长时间等待资源
```

解决方向：

```text
reward.num_workers=1
ray_kwargs.ray_init.num_cpus=48
actor_rollout_ref.rollout.agent.num_workers=1
```

Stage 13.3-B smoke 不需要大量 reward worker。减少 worker 数可以避免因为 CPU slot 或 Ray placement 策略导致启动卡住。

### 4. vLLM 与镜像内 PyTorch / CUDA 不兼容

现象示例：

```text
vllm 0.11.0 undefined symbol with torch 2.9.1
vllm 0.21.0 requires libcudart.so.13
```

本次处理：

- 不把 vLLM 作为 Stage 13.3-B 主路径；
- 使用 SGLang；
- 如 reference/verl 导入链路仍需要 vLLM 模块，可以在 smoke 中提供最小 vLLM stub，只满足导入，不承诺真实 vLLM 功能。

建议：

```text
Stage 13.3-B 首选 SGLang。
除非专门测试 vLLM，否则不要在同一轮远端 smoke 中反复切换 vLLM 版本。
```

### 5. SGLang attention backend 默认走到不兼容后端

现象：

```text
SGLang adapter 选择 trtllm_mha 或其他当前镜像不可用 attention backend
```

解决：

```text
强制 SGLang adapter attention backend 使用 flashinfer
```

本次远端使用了 reference/verl 侧临时补丁，把 SGLang server adapter 的：

```text
attention_backend
decode_attention_backend
prefill_attention_backend
```

统一设成 `flashinfer`。后续如果要固定为仓库实现，应该把它做成显式配置项或运行脚本 patch，而不是散落在手工修改中。

### 6. SGLang LoRA 对 Qwen q/k/v 维度推断不完整

现象：

```text
get_hidden_dim NotImplemented
或 SGLang LoRA utils 无法识别 Qwen q_proj / k_proj / v_proj 的维度
```

本次临时修复逻辑：

```python
if module_name == "q_proj":
    return config.hidden_size, head_dim * config.num_attention_heads
elif module_name == "k_proj":
    return config.hidden_size, head_dim * config.num_key_value_heads
elif module_name == "v_proj":
    return config.hidden_size, head_dim * config.num_key_value_heads
```

最终通过配置使用了 `model.lora.merge=True`，因此不再依赖动态 LoRA adapter request，但这个 Qwen LoRA 维度补丁仍然是前面排障时用到的关键经验。

### 7. 动态 SGLang LoRA adapter 没有被加载

现象：

```text
ValueError: Got LoRA adapter that has never been loaded: verl_actor_lora_name
All loaded adapters: dict_keys([])
```

定位证据：

```text
CheckpointEngineManager.update_weights backend=nccl replicas=1 global_steps=0
SGLangRollout.update_weights called global_steps=0 peft_config_present=False base_sync_done=False
```

根因：

```text
fully async 分离式 nccl checkpoint engine 路径只把权重张量传给 rollout worker。
它没有把 PEFT / LoRA 的 peft_config 一起传到 SGLangRollout.update_weights。
但是 SGLang generate request 仍然带了 lora_path=verl_actor_lora_name。
于是 SGLang 试图使用一个从未加载过的 adapter。
```

不要误判为显存问题。这是参数同步事实链缺失，不是 GPU 不够。

最终解决方案：

```text
actor_rollout_ref.model.lora.merge=True
```

并确保 SGLang generate request 在 merge 模式下不要再携带动态 LoRA adapter path。也就是说：

```text
训练侧仍然用 LoRA，降低优化器显存；
同步到 SGLang 时使用合并后的权重；
SGLang 侧不再依赖动态 LoRA adapter loading。
```

### 8. 全参数 7B 更新在 2 卡 smoke 中显存不足

现象：

```text
CUDA out of memory
出现在 Adam optimizer state 初始化或 actor update 附近
```

结论：

```text
如果坚持全参数 7B 更新，2 x RTX PRO 6000 不一定足够稳定。
但 Stage 13.3-B smoke 不需要全参数更新。
```

本次通过方案：

```text
LoRA training + param/optimizer offload + merged weight sync
```

因此不需要为了 Stage 13.3-B smoke 直接租 4 卡。

## 推荐排障顺序

远端训练失败时，按下面顺序判断：

1. 先看 Ray 是否成功启动。
2. 再看 trainer 和 rollouter 是否都创建成功。
3. 再看初始参数同步是否出现：

```text
CheckpointEngineManager.update_weights backend=nccl
SGLangRollout.update_weights called
```

4. 再看 RepoHarness agent loop 是否产生 formal online RL 样本。
5. 再看 MessageQueue 是否收集到样本：

```text
Loop collection completed: 1/1 samples
```

6. 再看 batch assembly：

```text
Batch assembly completed
```

7. 最后看 actor update 和参数版本推进：

```text
actor/loss
timing_s/update_actor
self.current_param_version: 1
self.current_param_version: 2
...
```

如果出现下面错误，优先按本文对应章节处理：

```text
Checkpoint engine nccl not registered
Got LoRA adapter that has never been loaded
CUDA out of memory
invalid_for_training_sample_in_formal_batch
RepoHarnessVerlAdapterError
```

## 最终 smoke 成功判定

Stage 13.3-B 的远端 smoke 至少应该满足：

```text
远端命令退出码为 0
Training Progress 到 100% 且达到 4/4
Batch assembly completed 至少 4 次
current_param_version 至少达到 2，推荐达到 4
MessageQueue 至少成功收集 required sample 多次
日志中没有 RepoHarnessVerlAdapterError
日志中没有 invalid_for_training_sample_in_formal_batch
日志中没有 Got LoRA adapter that has never been loaded
日志中没有 CUDA out of memory
日志中没有 Traceback
stage13_3b_acceptance_summary.json 中 acceptance_passed=true
```

本次最终通过日志满足：

```text
Training Progress: 100% ... 4/4
self.current_param_version: 4
Batch assembly completed: 8 次
successful_loop_collection_count: 8
```

## 证据打包清单

远端完成后，应至少打包以下文件：

```text
stage13_3b_acceptance_summary.json
stage13_3b_parameter_sync_report.json
stage13_3b_trainer_steps_report.json
stage13_3b_message_queue_backlog_report.json
stage13_3b_valid_sample_filter_report.json
stage13_3b_fully_async_final_lora_merge_stdout.log
run_stage13_3b_fully_async_final_lora_merge.sh
scripts/stage13_3b_runtime.py
repo_harness_agent_loop_config.yaml
stage13_3b_train.parquet
stage13_3b_val.parquet
stage13_3b_task_pool_manifest.json
stage13_3b_source_map.json
stage13_3b_preflight.json
fixture_manifest.json
fixture_sha256_report.json
fully_async_import_inventory.json
real_episode_runs_final_lora_merge/
```

打包示例：

```bash
RUN_DIR="$(cat /tmp/stage13_3b_run_dir)"
tar -czf /tmp/stage13_3b_final_evidence.tar.gz \
  "$RUN_DIR/stage13_3b_acceptance_summary.json" \
  "$RUN_DIR/stage13_3b_parameter_sync_report.json" \
  "$RUN_DIR/stage13_3b_trainer_steps_report.json" \
  "$RUN_DIR/stage13_3b_message_queue_backlog_report.json" \
  "$RUN_DIR/stage13_3b_valid_sample_filter_report.json" \
  "$RUN_DIR/stage13_3b_fully_async_final_lora_merge_stdout.log" \
  "$RUN_DIR/run_stage13_3b_fully_async_final_lora_merge.sh" \
  "$RUN_DIR/scripts/stage13_3b_runtime.py" \
  "$RUN_DIR/repo_harness_agent_loop_config.yaml" \
  "$RUN_DIR/stage13_3b_train.parquet" \
  "$RUN_DIR/stage13_3b_val.parquet" \
  "$RUN_DIR/stage13_3b_task_pool_manifest.json" \
  "$RUN_DIR/stage13_3b_source_map.json" \
  "$RUN_DIR/stage13_3b_preflight.json" \
  "$RUN_DIR/fixture_manifest.json" \
  "$RUN_DIR/fixture_sha256_report.json" \
  "$RUN_DIR/fully_async_import_inventory.json" \
  "$RUN_DIR/real_episode_runs_final_lora_merge"

sha256sum /tmp/stage13_3b_final_evidence.tar.gz
```

下载示例：

```bash
mkdir -p runs/stage13_3b-remote-final-<timestamp>
scp vastai6:/tmp/stage13_3b_final_evidence.tar.gz \
  runs/stage13_3b-remote-final-<timestamp>/stage13_3b_final_evidence.tar.gz
```

本地复核示例：

```bash
tar -tzf runs/stage13_3b-remote-final-<timestamp>/stage13_3b_final_evidence.tar.gz
python -m json.tool \
  runs/stage13_3b-remote-final-<timestamp>/runs/stage13_3b-*/stage13_3b_acceptance_summary.json
```

## 日志检查命令

最终 smoke 日志应通过下面检查：

```bash
LOG="<run_dir>/stage13_3b_fully_async_final_lora_merge_stdout.log"

grep -E "Training Progress:.*100%.*4/4|current_param_version: 4|Batch assembly completed" "$LOG"

if grep -E "RepoHarnessVerlAdapterError|invalid_for_training_sample_in_formal_batch|Got LoRA adapter that has never been loaded|CUDA out of memory|Traceback" "$LOG"; then
  echo "stage13_3b_failed"
  exit 1
fi
```

## 实例收尾

Smoke 完成或遇到无法继续的问题时，应暂停实例，保留磁盘数据：

```bash
.venv/bin/vastai stop instance <instance_id>
.venv/bin/vastai show instance <instance_id>
```

期望状态：

```text
Status exited
```

不要默认执行 `destroy instance`。`destroy instance` 会删除实例磁盘数据，只有用户明确要求删除时才执行。

## 当前 caveat

本次 smoke 可以证明第一版 fully async 真实链路已经跑通，但仍有几个边界需要后续增强：

1. 本次最终证据中唯一真实 episode run 数量是 `1`。后续如果要提高说服力，应加入更多唯一任务和更多任务类型。
2. 本次成功配置规避了动态 SGLang LoRA adapter loading，使用的是 merged weight sync。动态 adapter 路径如果未来要支持，需要补齐 `nccl` checkpoint engine 对 `peft_config` 的传递。
3. 本次是 smoke，不是吞吐压测。吞吐优化、更多 rollout replica、更大 batch 和多任务稳定性应放到后续阶段。
4. 远端对 reference/verl 和 SGLang 的临时补丁需要整理成正式 patch 或运行脚本 patch，避免下一台实例重新手工修改。
