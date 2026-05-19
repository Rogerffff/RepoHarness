# Stage 13.3-B 执行计划：远端 GPU 多步 fully async smoke

本文是 Stage 13.3-B 的具体执行计划。它承接
`01-sequential-implementation-plan.md` 中 Stage 13.3-B 的高层路线，并建立在
Stage 13.0、Stage 13.1、Stage 13.2 和 Stage 13.3-A 已完成的基础上。

Stage 13.3-B 的目标不是训练出有意义的模型，也不是验证大规模吞吐收益。它的目标是：
在远端 2 张 RTX PRO 6000 GPU 的环境中，使用真实 `reference/verl` fully async
训练入口，证明 RepoHarness 的异步 episode producer、MessageQueue、trainer-side
filtering、FullyAsyncTrainer 和参数同步能够共同跑通一个多步 agentic RL smoke。

本阶段通过后，才能说 RepoHarness 完成第一版 verl fully async agentic RL 链路
smoke。Stage 13.0 到 Stage 13.3-A 通过只能说明本地 contract、结构桥接和 runtime
adapter 已准备好。

## 1. 阶段目标和非目标

### 1.1 必须证明的目标

Stage 13.3-B 必须证明下面这条真实链路：

```text
RepoHarness fully async producer
-> RepoHarnessRuntime.start_episode(...)
-> AsyncEpisodeHandle.wait_result(...)
-> final_verifier_completed
-> TrainingView / AgentLoopOutput
-> RolloutSample
-> MessageQueue
-> DataProto assembly
-> FullyAsyncTrainer global step
-> parameter synchronization
-> sync 后继续产生和消费 RepoHarness 样本
```

验收口径：

- 至少完成 3 到 4 个真实 `FullyAsyncTrainer` global step。
- 每个成功 trainer step 都必须消费至少一个有效 `route=verl` RepoHarness 样本。
- 至少发生一次参数同步，`current_param_version` 或当前 verl 版本等价字段至少达到
  `1`。
- 参数同步后仍有新的 RepoHarness 样本进入 MessageQueue，并被 trainer 消费或被
  可解释地分类。
- `DataProto.non_tensor_batch` 或等价结构中必须能解释每条 trajectory 的参数版本窗口，
  包括 `trajectory_param_versions`、`min_global_steps`、`max_global_steps`、
  `global_steps` 或等价 `repo_harness_*` 字段。
- invalid、partial、stale、visibility rejected、pending reward、cancelled、
  timeout、missing logprob、non-verl route 样本不能进入 policy loss。
- MessageQueue、DataProto、meta_info、TransferQueue 类路径和最终 evidence 必须通过
  visibility 检查。
- 远端运行结束后，workspace、run directory、hidden runtime directory、recorder、
  verifier worker 和 Ray 资源没有不可解释的 orphan 或泄漏。

### 1.2 本阶段不要求

Stage 13.3-B 不要求：

- 模型收敛。
- SWE-Bench 大规模训练。
- partial rollout resume 成功。
- 大吞吐性能达标。
- 修改 `reference/verl` 核心训练逻辑。
- 证明 4 卡或多节点配置。

如果真实模型在某个简单任务上工具协议跟随失败，可以记录为模型行为失败或任务级失败，
但不能因此放松 formal batch validator、visibility gate、route gate 或 log probability
要求。

## 2. 默认远端环境

默认使用用户提供的远端实例：

```text
GPU: 2 * RTX PRO 6000
镜像: verlai/verl:sgl056.latest
磁盘: 300GB 或更高
模型: Qwen/Qwen2.5-Coder-7B-Instruct
RepoHarness 分支: codex/repo-harness-verl-stage0h
verl 入口: python -m verl.experimental.fully_async_policy.fully_async_main
```

2 张 GPU 的资源划分建议：

```text
trainer.n_gpus_per_node = 1
rollout.n_gpus_per_node = 1
```

这样可以满足 fully async 的资源隔离要求：一张 GPU 给 trainer，一张 GPU 给 rollouter。
如果 2 卡因为当前 verl 版本的资源池约束无法启动，再记录为
`resource_pool_incompatibility`，然后由用户决定是否改租 4 卡。第一轮不主动要求 4 卡。

## 3. 关键兼容性风险

`reference/verl/docs/advance/fully_async.md` 写明当前 fully async 推荐使用
`megatron/fsdp + vLLM`，并且 vLLM 需要基于 AgentLoop 的 server mode。用户当前远端镜像是
`verlai/verl:sgl056.latest`，Stage 12.6 同步链路使用过 SGLang 配置。

因此 Stage 13.3-B 必须把后端兼容性作为预检门，而不能默认假设 SGLang fully async 一定可用。

默认策略：

1. 先检查当前 `reference/verl` fully async 主路径实际支持的 rollout backend。
2. 如果当前版本的 fully async 明确支持 SGLang，并且启动级 dry run 通过，可以继续使用 SGLang。
3. 如果当前 fully async 主路径要求 vLLM server mode，则使用 vLLM。由于
   `reference/verl/docs/advance/fully_async.md` 明确写到当前支持模式是
   `megatron/fsdp + vLLM`，执行时不能因为 Stage 12.6 曾经使用过 SGLang 就跳过 vLLM 预检。
4. 如果当前镜像缺少可用 vLLM 或 vLLM server mode 依赖，则停止并记录
   `fully_async_backend_incompatibility`，不能用普通 `main_ppo` 或
   `actor_rollout_ref.rollout.mode=async` 冒充 fully async 通过。

这个风险必须写入 `stage13_3b_preflight.json`。

## 4. 远端执行总流程

Stage 13.3-B 分为八个子步骤。

```text
13.3-B-0 远端实例和代码预检
13.3-B-1 fully async 入口和后端兼容性预检
13.3-B-2 任务池、数据集和 fixture 冻结
13.3-B-3 RepoHarness fully async adapter 远端快速回归
13.3-B-4 真实 fully async 多步 trainer smoke
13.3-B-5 负例过滤和 partial / stale / visibility 诊断
13.3-B-6 evidence 汇总、可见性扫描和资源收口
13.3-B-7 失败分类、停机和同步证据
```

每一步都必须写入命令日志。真实模型运行命令、配置文件、环境变量、有效 commit、
fixture sha256、模型 revision、Ray 日志目录和最终报告路径都需要可追溯。

## 4.1 真实 fully async 集成路径

Stage 13.3-B 的主验收路径必须使用当前 `reference/verl` 的真实
`FullyAsyncRollouter`、`MessageQueue` 和 `FullyAsyncTrainer`，而不是只运行
Stage 13.3-A 的本地 fake queue 或本地 producer helper。

允许使用 Stage 13.3-A 中新增的 helper 做下面几件事：

```text
生成 RepoHarness queue facts
执行 trainer-side valid sample filter
生成 diagnostic / rejected side channel report
检查 MessageQueue payload visibility
生成远端 evidence report
```

不允许用 Stage 13.3-A 的本地 producer helper 完全替代 `FullyAsyncRollouter` 后仍宣称
parameter synchronization 通过。原因是 reference fully async 的参数同步发生在
`FullyAsyncTrainer` 和 `FullyAsyncRollouter` 之间；如果绕过真实 rollouter，就无法证明
trainer 到 rollouter 的 `update_weights(...)`、`reset_staleness(...)` 和 sync 后继续 rollout
这条路径真实工作。

因此执行时必须先确认下面两点：

1. `FullyAsyncRollouter` 能通过 `RepoHarnessVerlAgentLoop` 或等价注册入口调用
   RepoHarness `real_episode` runtime。
2. trainer-side filtering 在进入 reference `assemble_batch_from_rollout_samples(...)` 前生效，
   或者 policy-loss MessageQueue 从源头只接收已经通过 RepoHarness formal validator 的 valid
   sample。

Stage 13.3-B 必须新增一个真实链路形状 gate。这个 gate 在多步训练前运行，目标是证明下面
链路确实闭合：

```text
fully_async_main
-> FullyAsyncRollouter
-> RepoHarnessVerlAgentLoop
-> AgentLoopManager._postprocess(...)
-> DataProto.non_tensor_batch
-> RolloutSample
-> MessageQueue
```

gate 必须同时检查两类字段。第一类是 RepoHarness 审计字段，它们位于
`DataProto.non_tensor_batch` 中，使用 `repo_harness_*` 命名空间，并且必须是按 batch 维度排列
的数组或列表，不能是单个标量。至少需要检查：

```text
repo_harness_valid_for_policy_loss
repo_harness_llm_gateway_route
repo_harness_reward_state
repo_harness_sample_id
repo_harness_sample_attempt_id
repo_harness_trajectory_digest
repo_harness_generation_record_digest
repo_harness_visibility_scan_status
repo_harness_visibility_scan_digest
```

第二类是当前 `reference/verl` assembly 真实消费或生成的参数版本字段，不能误写成不存在的
`repo_harness_trajectory_param_versions`：

```text
DataProto.non_tensor_batch["min_global_steps"]
DataProto.non_tensor_batch["max_global_steps"]
DataProto.non_tensor_batch["global_steps"]
DataProto.meta_info["trajectory_param_versions"]
```

其中 `min_global_steps`、`max_global_steps` 和 `global_steps` 也必须按 batch 维度排列。
`trajectory_param_versions` 在当前 reference 路径中写入 `meta_info`，用于解释 trainer 消费的
trajectory 参数版本窗口。

如果这些字段只存在于 Stage 13.3-A 的本地 helper 输出中，而没有出现在真实
`FullyAsyncRollouter -> RolloutSample -> MessageQueue` 路径里，必须停止并记录
`adapter_integration_gap`。

真实 `FullyAsyncTrainer._get_samples_from_queue(...)` 不会自动理解 RepoHarness rejected 或
diagnostic 样本。它会收集 `required_samples` 个原始 queue entry 后直接反序列化和 assemble。
因此 Stage 13.3-B 的 policy-loss MessageQueue 源头必须只接收 valid sample。rejected、
diagnostic、partial、stale-over-threshold 和 visibility rejected 样本只能进入 side channel
report，不能进入真实 trainer 的 policy-loss queue。

如果当前 `reference/verl` 没有可插入的过滤点，或者当前代码还没有把
`RepoHarnessVerlAgentLoop` 接到 `FullyAsyncRollouter` 的真实 AgentLoop 路径，必须停止并记录
`adapter_integration_gap`，不能用普通同步 trainer 或本地 fake trainer 替代。

## 5. 13.3-B-0：远端实例和代码预检

远端启动后先执行只读或低风险命令，生成 `stage13_3b_preflight.json`。

必须记录：

```text
hostname
instance_id，如果可用
GPU 型号和数量
nvidia-smi 输出摘要
CUDA 版本
Python 版本
torch 版本
Ray 版本
verl import 路径和版本或 commit
SGLang 版本和可用性
vLLM 版本和可用性
flashinfer / flash attention 后端可用性
transformers 版本
tokenizer / chat template 来源
Docker 镜像或容器镜像摘要，如果可用
RepoHarness git commit
reference/verl git commit 或目录摘要
磁盘剩余空间
```

推荐命令骨架：

```bash
set -euo pipefail
cd /workspace/RepoHarness
git fetch --all --prune
git checkout codex/repo-harness-verl-stage0h
git rev-parse HEAD
python -m compileall -q src
python - <<'PY'
import importlib, json, sys
mods = ["torch", "ray", "transformers", "verl", "sglang", "vllm"]
out = {"python": sys.version}
for name in mods:
    try:
        mod = importlib.import_module(name)
        out[name] = getattr(mod, "__version__", "imported")
    except Exception as exc:
        out[name] = {"import_error": type(exc).__name__, "message": str(exc)}
print(json.dumps(out, indent=2, sort_keys=True))
PY
nvidia-smi
```

如果本地最新提交尚未推送，执行前必须先由本机推送，或者用明确的 `rsync` / patch bundle
方式同步，并在 preflight 中记录同步方式。不能在远端使用一个不可复现的脏工作区运行最终
验收。

## 6. 13.3-B-1：fully async 入口和后端兼容性预检

必须验证真实入口存在：

```bash
python - <<'PY'
import importlib
mods = [
    "verl.experimental.fully_async_policy.fully_async_main",
    "verl.experimental.fully_async_policy.fully_async_trainer",
    "verl.experimental.fully_async_policy.fully_async_rollouter",
    "verl.experimental.fully_async_policy.message_queue",
]
for name in mods:
    importlib.import_module(name)
print("fully_async_import_ok")
PY
```

必须记录当前配置形状：

```text
async_training.trigger_parameter_sync_step
async_training.require_batches
async_training.staleness_threshold
async_training.partial_rollout
data.train_batch_size
data.gen_batch_size
rollout.total_rollout_steps
rollout.n_gpus_per_node
trainer.n_gpus_per_node
actor_rollout_ref.hybrid_engine
actor_rollout_ref.actor.use_rollout_log_probs
actor_rollout_ref.rollout.calculate_log_probs
algorithm.rollout_correction.bypass_mode
actor_rollout_ref.rollout.multi_turn.enable
actor_rollout_ref.rollout.agent.agent_loop_config_path 或当前版本等价 agent loop 注册入口
actor_rollout_ref.rollout.agent.default_agent_loop 或当前版本等价默认 agent loop key
```

后端选择策略：

- 第一候选：SGLang fully async，如果当前 `reference/verl` 和镜像都支持。
- 第二候选：vLLM server mode fully async，如果 SGLang 不支持。
- 不允许候选：普通 `main_ppo`、同步 Stage 12-C trainer、小函数 loss smoke。

如果切换后端，必须在 `stage13_3b_preflight.json` 写明：

```text
requested_backend
selected_backend
fallback_reason
required_imports
missing_imports
attention_backend
```

Stage 12.6 里曾经遇到 flash attention / flashinfer 后端差异。本阶段默认先使用
`flashinfer`；如果不可用，可以回退到当前镜像支持的后端，但必须记录，且不能关闭
`calculate_log_probs=True`。

## 7. 13.3-B-2：任务池、数据集和 fixture 冻结

远端真实任务池至少包含三类极小真实仓库任务：

1. 无外部依赖基线任务，例如一个 calculator 修复任务。
2. 带第三方 Python 依赖任务，例如依赖 `tomli`、`packaging` 或其他小型纯 Python 包的任务。
3. 需要从当前 episode workspace 源码 import 的任务，例如 `src/` layout 或本地 helper import。

任务池可以复用 Stage 12.6 中已经验证过的 fixture，但必须在当前 worktree 内冻结到可审计位置，
不能依赖另一个 worktree 的未记录路径。必须生成：

```text
fixture_manifest.json
fixture_sha256_report.json
stage13_3b_task_pool_manifest.json
```

数据集要求：

- `data.train_files` 必须指向本阶段冻结生成的 `stage13_3b_train.parquet` 或等价训练数据文件。
- `data.val_files` 必须指向本阶段冻结生成的 validation 文件；如果不做验证，也必须提供空的或最小
  validation fixture，并设置 `trainer.val_before_train=False`、`trainer.test_freq=-1`。
- 每条样本必须包含 RepoHarness adapter 需要的 `repo_harness_*` 字段。
- 每条样本必须包含 `raw_prompt`，并且 `raw_prompt` 只能包含模型可见内容。
- 每条样本必须显式包含 `agent_name=repo_harness` 或能被当前 verl 配置稳定映射到
  `repo_harness` agent loop。
- 每条样本必须包含 `repo_harness_task_ref` 或当前 request mapping 支持的等价 task reference。
- `uid`、`index`、`session_id`、`global_steps` 等 verl 控制字段可以存在，但不能进入模型可见内容。
- 任务可以重复采样，但每次必须有新的 `sample_attempt_id`、`episode_id` 和 `run_id`。
- 任务池数量应支持 3 到 4 个 trainer step。默认 `ppo_mini_batch_size=2`、
  `require_batches=1` 时，3 到 4 个 step 需要 6 到 8 个有效样本。考虑模型行为失败、过滤样本和
  `rollout.total_rollout_steps=16` 的默认设置，建议准备 16 到 20 条 rollout 尝试，任务本身可以
  重复，但每次 attempt 必须有独立身份。

必须生成实际 agent loop 配置文件，例如：

```yaml
- name: repo_harness
  _target_: repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop
```

同时必须在训练命令中设置：

```text
actor_rollout_ref.rollout.multi_turn.enable=True
actor_rollout_ref.rollout.agent.agent_loop_config_path=<repo_harness_agent_loop_config.yaml>
actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness
```

如果不启用 `multi_turn`，当前 verl 路径可能把样本强制映射到 `single_turn_agent`，从而绕开
`RepoHarnessVerlAgentLoop`。这种情况必须视为 `agent_loop_registration_failure`。

## 8. 13.3-B-3：RepoHarness adapter 远端快速回归

在启动真实 fully async trainer 前，先在远端同一代码环境里跑一组快速回归，确认远端没有
缺少本地 Stage 13.3-A 的实现。

建议命令：

```bash
PYTHONPATH=src python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

这一步不是最终验收，只是避免远端环境和本地代码不一致。

## 9. 13.3-B-4：真实 fully async 多步 trainer smoke

### 9.1 默认训练参数

推荐第一轮 smoke 使用下面的保守目标：

```text
model = Qwen/Qwen2.5-Coder-7B-Instruct
trainer.n_gpus_per_node = 1
rollout.n_gpus_per_node = 1
data.train_batch_size = 0
data.gen_batch_size = 1
actor_rollout_ref.hybrid_engine = False
actor_rollout_ref.actor.ppo_mini_batch_size = 2
async_training.require_batches = 1
required_samples_per_trainer_step = 2
async_training.trigger_parameter_sync_step = 2
async_training.staleness_threshold = 1
async_training.partial_rollout = False
rollout.total_rollout_steps = 16
target_trainer_global_steps = 4
actor_rollout_ref.rollout.calculate_log_probs = True
actor_rollout_ref.actor.use_rollout_log_probs = True
algorithm.rollout_correction.bypass_mode = True
critic.enable = False
reward.reward_model.enable = False
```

`ppo_mini_batch_size=2` 是默认推荐，因为它和 Stage 12 同步 trainer smoke 的小批量设置更接近，
也更适合 2 张 GPU 的资源池。若当前 fully async 配置要求更小批量，允许回退到
`ppo_mini_batch_size=1`，但必须在报告中说明，并仍然完成 3 到 4 个 trainer step。

`rollout.total_rollout_steps` 不能随意降到 10。按照当前 reference 公式：

```text
total_train_steps = int(total_rollout_steps / (required_samples * trigger_parameter_sync_step))
```

在 `required_samples=2`、`trigger_parameter_sync_step=2` 时，`total_rollout_steps=12`
只能提供 3 个 trainer step，`total_rollout_steps=16` 才能提供 4 个 trainer step。因此默认使用
`16`，最低不能低于 `12`。

### 9.2 命令模板

实际命令必须以远端 preflight 确认后的配置为准。下面是模板，不是最终逐字执行命令：

```bash
PYTHONPATH=src:reference/verl:${PYTHONPATH:-} \
python -m verl.experimental.fully_async_policy.fully_async_main \
  algorithm.adv_estimator=grpo \
  data.train_files=<stage13_3b_train.parquet> \
  data.val_files=<stage13_3b_val.parquet> \
  data.prompt_key=prompt \
  data.return_raw_chat=True \
  data.train_batch_size=0 \
  data.gen_batch_size=1 \
  data.max_prompt_length=4096 \
  data.max_response_length=256 \
  data.filter_overlong_prompts=False \
  data.truncation=left \
  actor_rollout_ref.model.path=Qwen/Qwen2.5-Coder-7B-Instruct \
  actor_rollout_ref.hybrid_engine=False \
  actor_rollout_ref.model.use_remove_padding=True \
  actor_rollout_ref.model.enable_gradient_checkpointing=True \
  actor_rollout_ref.model.enable_activation_offload=True \
  actor_rollout_ref.actor.ppo_mini_batch_size=2 \
  actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.actor.ppo_epochs=1 \
  actor_rollout_ref.actor.use_rollout_log_probs=True \
  actor_rollout_ref.actor.fsdp_config.param_offload=True \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=True \
  actor_rollout_ref.rollout.name=<sglang_or_vllm_from_preflight> \
  actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
  actor_rollout_ref.rollout.gpu_memory_utilization=0.25 \
  actor_rollout_ref.rollout.prompt_length=4096 \
  actor_rollout_ref.rollout.response_length=256 \
  actor_rollout_ref.rollout.max_model_len=4608 \
  actor_rollout_ref.rollout.max_num_seqs=2 \
  actor_rollout_ref.rollout.max_num_batched_tokens=6144 \
  actor_rollout_ref.rollout.calculate_log_probs=True \
  actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.rollout.multi_turn.enable=True \
  actor_rollout_ref.rollout.agent.agent_loop_config_path=<repo_harness_agent_loop_config.yaml> \
  actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness \
  actor_rollout_ref.rollout.agent.num_workers=1 \
  async_training.trigger_parameter_sync_step=2 \
  async_training.require_batches=1 \
  async_training.staleness_threshold=1 \
  async_training.partial_rollout=False \
  rollout.nnodes=1 \
  rollout.n_gpus_per_node=1 \
  rollout.n=1 \
  rollout.total_rollout_steps=16 \
  trainer.nnodes=1 \
  trainer.n_gpus_per_node=1 \
  trainer.total_epochs=1 \
  trainer.val_before_train=False \
  trainer.test_freq=-1 \
  trainer.save_freq=-1 \
  trainer.logger='["console"]' \
  critic.enable=False \
  reward.reward_model.enable=False \
  algorithm.rollout_correction.bypass_mode=True \
  ray_kwargs.ray_init.num_cpus=24
```

如果执行时选择镜像内置的 `verl`，而不是当前仓库的 `reference/verl`，命令也必须至少保留
`PYTHONPATH=src:${PYTHONPATH:-}`，并在 `stage13_3b_preflight.json` 记录：

```text
verl_source = image_installed 或 reference_verl
verl_import_path
repo_harness_import_path
agent_loop_config_path
```

执行时必须保存：

```text
原始命令
展开后的 Hydra 配置
stdout / stderr
Ray 日志路径
RepoHarness run directory
MessageQueue 统计
trainer metrics
parameter sync 日志
```

### 9.3 OOM 或后端失败时的调整顺序

如果出现显存不足，按下面顺序调整：

1. 降低 `actor_rollout_ref.rollout.gpu_memory_utilization`。
2. 降低 `max_num_batched_tokens`。
3. 降低 `max_model_len`、`max_prompt_length` 或 `max_response_length`。
4. 降低 `rollout.total_rollout_steps`，但不能低于 `12`，否则无法完成 3 个 trainer step。
5. 将 `ppo_mini_batch_size` 从 `2` 降到 `1`，并重新计算 required samples。

不允许通过下面方式绕过问题：

- 关闭 `calculate_log_probs`。
- 关闭 formal batch validator。
- 把 `route=mock` 或 provider route 当成正式样本。
- 跳回普通同步 trainer。
- 用函数级 `compute_advantage` 或 `compute_policy_loss` 代替真实 trainer step。

## 10. 13.3-B-5：负例过滤和 partial / stale / visibility 诊断

真实 fully async trainer 的 policy-loss MessageQueue 不应该接收 rejected 或 diagnostic 样本。
因此负例验证分两类进行。

### 10.1 trainer 主路径负例

主路径只允许 valid candidate 进入 policy-loss queue。必须证明 trainer 实际消费的 batch 中：

```text
repo_harness_valid_for_policy_loss = true
repo_harness_llm_gateway_route = "verl"
repo_harness_invalid_for_training != true
repo_harness_invalid_for_online_rl != true
response_logprobs 非空
repo_harness_generation_record_digest 非空
repo_harness_trajectory_digest 非空
side evidence 中可回查到非空 generation_records
trajectory digest 匹配
reward_state = final_verifier_completed
partial_rollout_supported = false
partial_rollout_status = not_requested 或 complete
```

完整 `generation_records` 不应被塞进 policy-loss batch。trainer batch 里只需要传播 digest、
opaque audit refs 和 batch-safe facts；完整 generation record 明细必须留在 side evidence 或
run artifact 中供审计回查。

### 10.2 受控负例和诊断 side channel

下列负例可以通过 Stage 13.3-A 的本地 helper 在远端环境中构造，也可以通过短路径注入产生。
它们必须进入 diagnostic report 或 rejected report，不能进入真实 trainer policy loss：

```text
non-verl route
missing response_logprobs
missing generation_records
forged trajectory digest
pending reward
timeout
cancelled
visibility rejected
partial rollout
stale trajectory 超出阈值
```

必须生成：

```text
stage13_3b_valid_sample_filter_report.json
stale_and_partial_trajectory_report.json
formal_batch_and_visibility_report.json
```

## 11. 13.3-B-6：证据汇总和资源收口

本阶段必须生成下面 canonical evidence。具体执行计划可以合并部分报告文件，但
`stage13_3b_acceptance_summary.json` 必须写清 canonical item 到实际文件的映射。

```text
stage13_3b_preflight.json
fixture_manifest.json
fixture_sha256_report.json
stage13_3b_task_pool_manifest.json
fully_async_rollouter_profile.json
fully_async_message_queue_report.json
async_episode_lifecycle_report.json
reward_backfill_ledger_report.json
stale_and_partial_trajectory_report.json
formal_batch_and_visibility_report.json
trainer_global_step_report.json
parameter_sync_report.json
resource_cleanup_and_orphan_report.json
stage13_3b_parameter_sync_report.json
stage13_3b_trainer_steps_report.json
stage13_3b_message_queue_backlog_report.json
stage13_3b_valid_sample_filter_report.json
stage13_3b_visibility_report.json
stage13_3b_resource_lifecycle_report.json
stage13_3b_command_log.jsonl
stage13_3b_acceptance_summary.json
```

参数同步报告必须区分两类事件：

```text
初始化阶段的 _fit_update_weights，通常 current_param_version 仍为 0
训练过程中 local_trigger_step 达到 trigger_parameter_sync_step 后发生的参数同步，current_param_version >= 1
```

Stage 13.3-B 通过只能依赖第二类事件。`stage13_3b_parameter_sync_report.json` 必须引用原始
stdout、Ray worker log 或 trainer metrics，证明训练后发生过至少一次 `current_param_version >= 1`
的同步。不能把初始化时的 version 0 权重同步算作本阶段通过。

`stage13_3b_acceptance_summary.json` 至少包含：

```text
stage = "13.3-B"
repo_commit
reference_verl_commit
remote_instance_summary
selected_backend
model_id
task_pool_id
completed_trainer_step_count
target_trainer_step_count
parameter_sync_observed
current_param_version
trigger_parameter_sync_step
valid_sample_count
rejected_sample_count
diagnostic_sample_count
post_sync_sample_count
stale_sample_count
filtered_stale_sample_count
partial_rollout_supported
partial_rollout_rejected_count
visibility_passed
resource_cleanup_passed
acceptance_ready
blocking_failures
canonical_evidence_mapping
```

路径可见性要求：

- 可传播 summary evidence 不能包含本机绝对路径、远端私有路径、provider secret、hidden verifier、
  gold patch 或完整 reward metadata。
- runtime-private raw evidence 如果保留真实路径，必须标记为本地私有，不能进入 batch、公开 summary
  或 acceptance summary 的可传播字段。

资源收口要求：

- 所有 `run_status.json` 最终不能停在 `RUNNING`。
- Ray 进程、SGLang / vLLM server、RepoHarness producer、verifier worker 和 executor 必须关闭或
  有结构化 orphan diagnostics。
- workspace lease、hidden runtime directory、dependency environment overlay 和 recorder lock 不得
  出现不可解释残留。
- 如果用户要求节省费用，执行结束或阻断后应通过 Vast.ai 命令行或用户确认的方式暂停实例。

## 12. 13.3-B-7：失败分类

如果 Stage 13.3-B 没有通过，必须归类为下面之一，不能只写笼统
`infrastructure_error`：

```text
remote_preflight_failure
fully_async_backend_incompatibility
fully_async_shape_gate_failure
adapter_integration_gap
agent_loop_registration_failure
message_queue_shape_failure
formal_batch_visibility_failure
trainer_sample_filter_failure
trainer_global_step_failure
parameter_sync_failure
post_sync_rollout_failure
reward_backfill_mismatch
resource_lifecycle_failure
model_tool_protocol_failure
model_task_failure
gpu_memory_failure
ray_resource_pool_failure
```

每个 failure 都必须包含：

```text
first_failed_command
log_ref
affected_evidence_item
whether_retry_safe
recommended_next_action
```

## 13. 本地和远端验收命令

远端运行前，本地至少执行：

```bash
PYTHONPATH=src python -m compileall -q src
PYTHONPATH=src python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

远端运行后至少执行：

```bash
PYTHONPATH=src python -m compileall -q src
PYTHONPATH=src python -m pytest -q \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_batch_gate.py \
  tests/unit/test_repo_harness_verl_stage13_0_async_visibility.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_cancellation.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_snapshot.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py
```

verl import 边界检查：

```bash
if rg -n '(^|\\s)(import|from)\\s+verl' \
  src/repo_harness/rl \
  src/repo_harness/agent_loop \
  src/repo_harness/workspace \
  src/repo_harness/verifier; then
  echo "RepoHarness core must not import verl"
  exit 1
fi
```

Stage 13.3-B 远端报告生成完成后，必须做 JSON 可读性检查和 evidence manifest 检查：

```bash
python - <<'PY'
import json
from pathlib import Path
run_dir = Path("runs/<stage13_3b_run_dir>")
required = [
    "stage13_3b_acceptance_summary.json",
    "stage13_3b_preflight.json",
    "stage13_3b_trainer_steps_report.json",
    "stage13_3b_parameter_sync_report.json",
    "stage13_3b_valid_sample_filter_report.json",
]
missing = [name for name in required if not (run_dir / name).exists()]
if missing:
    raise SystemExit(f"missing evidence: {missing}")
for path in run_dir.glob("*.json"):
    json.loads(path.read_text())
print("stage13_3b_evidence_json_ok")
PY
```

## 14. 需要用户确认的默认决策

除非用户明确修改，Stage 13.3-B 默认采用下面决策。

1. 继续使用 `2 * RTX PRO 6000`，不主动租 4 卡。
2. 模型使用 `Qwen/Qwen2.5-Coder-7B-Instruct`。
3. 镜像使用 `verlai/verl:sgl056.latest`。
4. trainer 和 rollouter 各使用 1 张 GPU。
5. 以后端兼容性预检为准。若 SGLang fully async 启动级 dry run 通过，可以使用 SGLang；否则优先使用当前 reference fully async 文档支持的 vLLM server mode。
6. `actor_rollout_ref.hybrid_engine=False` 是硬性参数，因为 `FullyAsyncRollouter` 不接受 hybrid engine。
7. `actor_rollout_ref.rollout.multi_turn.enable=True`，并使用真实 agent loop config 注册 `repo_harness`。
8. 训练命令默认使用 `PYTHONPATH=src:reference/verl:${PYTHONPATH:-}`；如果使用镜像内置 verl，也必须保留 `PYTHONPATH=src:${PYTHONPATH:-}`。
9. `data.prompt_key=prompt`、`data.return_raw_chat=True`、`data.train_files` 和 `data.val_files` 必须显式设置。
10. `async_training.partial_rollout=False`，本阶段不实现 partial resume。
11. valid sample 的 `partial_rollout_status` 应是 `not_requested` 或 `complete`；`unsupported_in_stage13_3b` 只用于 rejected 或 diagnostic side channel。
12. `async_training.trigger_parameter_sync_step=2`，目标完成 3 到 4 个 trainer step。
13. 默认 `ppo_mini_batch_size=2`、`require_batches=1`，每个 trainer step 需要 2 个有效样本。
14. 默认 `rollout.total_rollout_steps=16`；如果降级，不能低于 `12`。
15. 任务池准备 16 到 20 次 rollout 尝试，覆盖无外部依赖、第三方 Python 依赖和 workspace 源码 import。
16. 负例通过 diagnostic side channel 或受控构造验证，不把 rejected 样本放进真实 policy-loss queue。
17. 完整 generation records 留在 side evidence，不进入 policy-loss batch；batch 中只传播 digest 和 batch-safe facts。
18. 如果模型工具协议失败，只记录并重试简单任务，不放松 formal validator。
19. 如果 2 卡资源池无法启动 fully async，则停止并向用户汇报是否需要 4 卡，而不是擅自改为同步训练。

## 15. 最小通过结论模板

Stage 13.3-B 通过时，最终结论应包含：

```text
Stage 13.3-B passed.
remote_backend = <sglang_or_vllm>
model = Qwen/Qwen2.5-Coder-7B-Instruct
completed_trainer_step_count = <n>
current_param_version = <n>
parameter_sync_observed = true
valid_route_verl_sample_count = <n>
post_sync_sample_count = <n>
rejected_sample_count = <n>
partial_rollout_supported = false
partial_rollout_rejected_count = <n>
visibility_passed = true
resource_cleanup_passed = true
evidence_dir = <path>
```

如果没有通过，结论必须给出 failure taxonomy、阻断命令、日志引用和下一步建议。
