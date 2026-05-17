# Stage 12.6 执行计划：Stage 12.5 修改后远端 RL 链路回归 smoke

本文是 Stage 12.6 的具体实施计划。它承接
`01-sequential-implementation-plan.md` 中新增的 Stage 12.6 高层定义，用于指导远端
`2 * RTX PRO 6000` GPU 环境中的回归 smoke。

Stage 12.6 的目标不是继续扩大训练规模，也不是开始 Stage 13 fully async。它只验证一件事：

```text
Stage 12.5 提交后的当前代码
-> 在新的远端 GPU 实例上
-> 仍然可以跑通真实 RepoHarness + verl RL 链路
-> 并且共享依赖环境、隐藏 runtime 目录、命令策略、formal batch validator、batch refill 没有破坏 trainer 小步路径
```

## 1. 阶段边界

Stage 12.6 必须坚持下面边界：

- 不实现 fully async AgentLoop。
- 不做大规模 SWE-Bench 训练。
- 不要求模型收敛，不要求 checkpoint 有实际质量提升。
- 不关闭 `response_logprobs`、formal batch validator、visibility gate、verifier、reward boundary 或 artifact evidence 来制造通过结果。
- 不把 fake log probability、mock server、debug fixture 或手工构造 DataProto 当作正式通过证据。
- 不因为模型没有修好任务就判定基础设施失败。模型格式错误、工具调用错误、verifier rejected、command policy blocked 和 infrastructure error 必须分开统计。
- 不在远端 smoke 中顺手修改 shared contract。如果远端发现必须改代码，必须记录 patch，标记为带条件通过或未通过，然后回到本地做正式修复和提交。

## 2. 远端环境默认选择

用户会重新租用一台新的远端实例，不复用 Stage 12-B/C 的旧实例。因此 Stage 12.6 必须完整记录 preflight，而不能假设旧环境状态仍然存在。

默认环境：

```text
GPU：2 * RTX PRO 6000，单卡 96GB
镜像：verlai/verl:sgl056.latest
模型：Qwen/Qwen2.5-Coder-7B-Instruct
推理后端：SGLang
训练 smoke：GRPO / main_ppo 小步 trainer path
任务规模：极小真实仓库任务池
```

如果实际镜像、GPU、CUDA、torch、Ray、verl、SGLang 或 transformers 版本和上述默认值不同，必须写入 `stage12_6_preflight.json`，并在 `stage12_6_acceptance_summary.json` 中解释差异。

preflight 还必须记录：

- 操作系统和 glibc / musl 信息。
- Docker / container 镜像的实际 image id 或 digest。因为 `verlai/verl:sgl056.latest` 是浮动标签，不能只记录 tag 名称。
- `nvidia-smi`、驱动版本、CUDA runtime / toolkit 版本。
- CPU 核数、系统内存、磁盘容量、可用磁盘空间、`/dev/shm` 大小。
- Ray 临时目录、Ray dashboard 可用性、执行前是否存在遗留 Ray 进程。
- `reference/verl` 或实际安装的 `verl` 来源、commit / version、安装路径。

## 3. 上次 Stage 12-C 已知远端配置经验

Stage 12-C 完整 trainer smoke 的成功证据位于：

```text
runs/stage12c-full-trainer-20260516T235102Z/
```

当时成功跑完 2 个 trainer step 的关键配置是：

```text
python -m verl.trainer.main_ppo
algorithm.adv_estimator=grpo
data.train_batch_size=2
data.max_prompt_length=4096
data.max_response_length=256
actor_rollout_ref.model.path=Qwen/Qwen2.5-Coder-7B-Instruct
actor_rollout_ref.model.use_remove_padding=True
actor_rollout_ref.model.enable_gradient_checkpointing=True
actor_rollout_ref.model.enable_activation_offload=True
actor_rollout_ref.actor.ppo_mini_batch_size=2
actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1
actor_rollout_ref.actor.ppo_epochs=1
actor_rollout_ref.actor.fsdp_config.param_offload=True
actor_rollout_ref.actor.fsdp_config.optimizer_offload=True
actor_rollout_ref.rollout.name=sglang
actor_rollout_ref.rollout.mode=async
actor_rollout_ref.rollout.tensor_model_parallel_size=1
actor_rollout_ref.rollout.gpu_memory_utilization=0.25
actor_rollout_ref.rollout.prompt_length=4096
actor_rollout_ref.rollout.response_length=256
actor_rollout_ref.rollout.max_model_len=4608
actor_rollout_ref.rollout.max_num_seqs=2
actor_rollout_ref.rollout.max_num_batched_tokens=6144
actor_rollout_ref.rollout.calculate_log_probs=True
actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1
+actor_rollout_ref.rollout.engine_kwargs.sglang.attention_backend=flashinfer
actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness
actor_rollout_ref.rollout.agent.num_workers=1
critic.enable=False
reward.reward_model.enable=False
trainer.n_gpus_per_node=2
trainer.total_training_steps=2
trainer.val_before_train=False
trainer.test_freq=-1
trainer.save_freq=-1
ray_kwargs.ray_init.num_cpus=24
```

Stage 12.6 第一版应从这组保守配置开始，而不是重新调大 batch 或上下文长度。

这里的 `actor_rollout_ref.rollout.mode=async` 是 verl / SGLang rollout 服务的既有成功配置，表示 rollout server 使用 async 模式；它不等于 Stage 13 要设计的 RepoHarness fully async AgentLoop，也不表示 Stage 12.6 已经实现 episode interrupt、resume、async reward backfill 或跨参数版本 trajectory 处理。

完整 trainer 命令必须以 Stage 12-C 成功命令为基线，原始证据是：

```text
runs/stage12c-full-trainer-20260516T235102Z/stage12c_full_trainer_command_log.jsonl
```

除了上面列出的关键项，Stage 12.6 执行计划和脚本还应默认保留这些保守项，除非 preflight 证明当前镜像需要调整：

```text
data.return_raw_chat=True
data.shuffle=False
data.filter_overlong_prompts=False
data.truncation=left
data.dataloader_num_workers=0
actor_rollout_ref.actor.use_dynamic_bsz=False
actor_rollout_ref.actor.use_kl_loss=False
actor_rollout_ref.actor.entropy_coeff=0
actor_rollout_ref.actor.optim.lr=1e-6
actor_rollout_ref.rollout.n=1
actor_rollout_ref.rollout.temperature=0.0
actor_rollout_ref.rollout.top_p=1.0
actor_rollout_ref.rollout.val_kwargs.n=1
actor_rollout_ref.rollout.val_kwargs.temperature=0.0
trainer.resume_mode=disable
trainer.logger=['console']
trainer.save_freq=-1
trainer.test_freq=-1
```

### 3.1 flash attention / flashinfer 注意事项

上次成功运行时日志中出现过 `Flash Attention 2 only supports torch.float16 and torch.bfloat16 dtypes` 相关 warning，但最终 trainer step 通过。因此 Stage 12.6 不应把这个 warning 直接视为失败。

默认策略：

- SGLang backend 默认继续使用 `+actor_rollout_ref.rollout.engine_kwargs.sglang.attention_backend=flashinfer`。
- preflight 必须检查 `flashinfer_python` 或当前镜像中等价 flashinfer 组件是否可导入。
- 如果 `flashinfer` 后端启动失败，允许回退到当前 SGLang 镜像支持的后端，但必须先记录：
  - 原始异常。
  - SGLang 版本。
  - 可用 attention backend。
  - 回退后的配置。
  - 回退是否影响 log probability、token ids 或 trainer global step。
- 不能为了绕开后端问题关闭 `calculate_log_probs=True`。

### 3.2 显存配置注意事项

上次成功 smoke 使用了非常保守的显存配置。Stage 12.6 仍应沿用：

```text
rollout.gpu_memory_utilization=0.25
rollout.max_model_len=4608
rollout.max_num_seqs=2
rollout.max_num_batched_tokens=6144
data.max_prompt_length=4096
data.max_response_length=256
ppo_micro_batch_size_per_gpu=1
log_prob_micro_batch_size_per_gpu=1
activation_offload=True
param_offload=True
optimizer_offload=True
```

如果发生 OOM，先降低 `train_batch_size`、`max_prompt_length`、`max_response_length`、`max_num_batched_tokens` 或 `gpu_memory_utilization`，不要先放弃 formal validator、verifier 或 reward boundary。

## 4. 任务池设计

Stage 12.6 必须使用极小真实仓库任务池，至少包含三类任务。

### 4.1 无外部依赖基线任务

目的：验证没有第三方依赖时，当前 Stage 12.5 改动没有破坏基础 `real_episode` 链路。

建议任务：

```text
repo：已有 calculator / tiny Python fixture
bug：divide by zero 未显式抛出 ValueError，或简单字符串处理错误
verifier：pytest 单文件
```

验收重点：

- 模型可以完成 `read_file -> edit_file -> final answer`。
- final verifier accepted 或 verifier rejected 均可，但必须分类正确。
- `TrainingView`、`AgentLoopOutput`、DataProto visibility 通过。

### 4.2 带第三方 Python 依赖的极小任务

目的：真实验证 dependency environment cache 的 cold / warm 行为，而不是空跑。

本计划选择依赖：

```text
tomli==2.0.1
```

选择理由：

- `tomli` 是纯 Python 小包，安装快，不需要 C / CUDA / Rust / native build。
- Python 3.11 / 3.12 自带 `tomllib`，但 `tomli` 仍然是明确的第三方包，适合验证 dependency cache。
- 依赖体积小，远端网络或 package index 抖动时影响较小。

建议任务：

```text
repo：tiny_tomli_config
pyproject.toml / requirements.txt：声明 tomli==2.0.1
源码：config_reader.py 使用 tomli 读取 TOML 配置
bug：把整数配置错误地当作字符串返回，或缺少默认值处理
verifier：pytest 验证 tomli import、配置解析和修复后的行为
```

验收重点：

- cold cache run 中创建 dependency environment。
- warm cache run 命中同一个 `base_environment_key` / `overlay_environment_key`。
- warm run 不重复完整 dependency setup。
- 模型可见输出中不能出现真实 dependency environment 路径。
- `HOME`、`XDG_CACHE_HOME`、`PIP_CACHE_DIR`、`UV_CACHE_DIR`、`TMPDIR`、`PYTHONPYCACHEPREFIX` 使用每条 episode 独立隐藏 runtime 目录，不跨轨迹共享。

### 4.3 需要从当前 episode workspace 源码 import 的任务

目的：证明测试 import 的是当前 episode workspace 中被模型修改后的源码，而不是 shared dependency environment 中的旧源码。

建议任务：

```text
repo：tiny_src_layout_package
layout：src/tiny_pkg/...
依赖环境：只安装 pytest 和第三方依赖，不执行 pip install -e .
运行时：通过 pythonpath_entries 或等价 runtime spec 指向当前 workspace/src
bug：函数逻辑错误
verifier：pytest 从 tiny_pkg import 当前 workspace 源码
```

验收重点：

- shared environment 不包含当前 repo editable install。
- 模型修改 `src/tiny_pkg/...` 后，verifier import 到修改后的 workspace 源码。
- source snapshot、workspace lease、environment key 三者在报告中能区分。

## 5. 命令策略受控负例

Stage 12.6 必须增加一个不进入 trainer batch 的 diagnostic task 或脚本化 episode，用来验证共享依赖环境保护模式。

必须触发并记录下面命令：

```bash
env
which python
python -c "import sys; print(sys.executable)"
python -m pip install requests
```

验收要求：

- 这些命令被结构化分类为 `command_policy_blocked` 或等价安全拒绝原因。
- 拒绝结果不能伪装成 verifier infrastructure error。
- 可见输出、command artifact、summary report 中不能泄漏：
  - 真实 dependency environment 路径。
  - workspace 绝对路径。
  - run directory。
  - `.repo_harness_runtime`。
  - `.repo_harness_env_overlay`。
- 该 diagnostic task 不进入 formal online RL batch，不参与 policy loss。

## 6. 实施顺序

### Stage 12.6-0：本地准备和远端前置确认

本地准备：

- 确认当前本地 commit 已包含 Stage 12.5 实现。
- 确认 `01-sequential-implementation-plan.md` 中 Stage 12.6 高层计划已经提交或会随执行计划提交。
- 新增或确认 Stage 12.6 任务 fixtures：
  - 无外部依赖基线任务。
  - `tomli==2.0.1` 依赖任务。
  - `src/` layout workspace import 任务。
  - command policy diagnostic task。
- 生成 fixture manifest 和 sha256 report。

远端前置确认：

```bash
git rev-parse HEAD
git status --short
nvidia-smi
python --version
df -h
df -h /dev/shm || true
free -h || true
ps -ef | grep -E 'ray|sglang|vllm' | grep -v grep || true
ray status || true
python - <<'PY'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), torch.cuda.get_device_properties(i).total_memory)
PY
python - <<'PY'
import importlib
for name in ["ray", "verl", "sglang", "transformers", "flashinfer_python"]:
    try:
        mod = importlib.import_module(name)
        print(name, "ok", getattr(mod, "__version__", "unknown"))
    except Exception as exc:
        print(name, "error", repr(exc))
PY
python - <<'PY'
import importlib.util
import pathlib
for name in ["verl", "sglang", "ray", "transformers"]:
    spec = importlib.util.find_spec(name)
    print(name, spec.origin if spec else "missing")
for candidate in ["reference/verl/.git", "/workspace/RepoHarness/reference/verl/.git"]:
    path = pathlib.Path(candidate)
    print(candidate, "exists" if path.exists() else "missing")
PY
python - <<'PY'
from transformers import AutoTokenizer
AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
print("tokenizer_ok")
PY
```

输出写入：

```text
stage12_6_preflight.json
stage12_6_command_log.sanitized.jsonl
runtime_private/stage12_6_command_log.raw.jsonl
git_state_before_after.json
```

### Stage 12.6-1：cold cache dependency / workspace smoke

运行一轮单任务或小任务池，强制使用新的 cache root。

必须记录：

- dependency environment key。
- source snapshot key。
- workspace lease id。
- cache miss。
- dependency setup seconds。
- workspace materialization seconds。
- setup command 分类。
- runtime hidden directory policy。

输出：

```text
environment_cache_report.json
workspace_cache_report.json
verifier_recorder_tool_hot_path_report.json
```

### Stage 12.6-2：warm cache smoke

使用同一任务池和同一 cache root 再运行一轮。

必须证明：

- dependency environment key 与 cold run 一致。
- source snapshot key 与 cold run 一致。
- dependency environment 是 cache hit。
- workspace snapshot 是 cache hit 或安全复用。
- 没有重复执行完整 dependency setup。

输出继续写入：

```text
environment_cache_report.json
workspace_cache_report.json
```

### Stage 12.6-3：并发 real episode smoke

并发运行 2 到 4 条极小任务。

要求：

- 每条 episode 有独立 workspace lease。
- 每条 episode 有独立 hidden runtime directory。
- artifact manifest 不能串写。
- run directory single-writer 约束仍成立。
- cleanup 后没有 orphan lease。
- final verifier / reward boundary 状态可审计。

输出：

```text
concurrent_episode_report.json
real_episode_task_pool_report.json
```

### Stage 12.6-4：命令策略和路径可见性 smoke

执行第 5 节的受控负例，并扫描全部可传播 evidence。

扫描范围：

- `TrainingView.extra_fields`。
- `AgentLoopOutput.extra_fields`。
- DataProto non-tensor batch。
- DataProto meta_info。
- 模型可见 tool output。
- command artifact。
- command log。
- profile JSON。
- acceptance summary。

输出：

```text
command_policy_and_runtime_visibility_report.json
evidence_path_leak_scan_report.json
visibility_and_batch_validation_report.json
```

路径泄漏扫描必须分层：

- 用户可传播或可上传的 summary evidence 必须脱敏。
- runtime-private raw evidence 如果为了远端调试保留真实路径，必须标记为本地私有。
- runtime-private raw evidence 不得进入 batch、公开报告或 `stage12_6_acceptance_summary.json` 的可传播字段。

### Stage 12.6-5：formal batch 和 refill smoke

从真实 episode result 中收集样本。

必须验证：

- valid 样本全部 `route=verl`。
- valid 样本都有 `response_logprobs`。
- valid 样本都有 `generation_records`。
- valid 样本都有 `response_spans`。
- `response_ids`、`response_mask`、`response_logprobs` 长度一致。
- assistant generation span 与 generation records token / logprob 对齐。
- missing logprobs、mixed route、overflow、empty response、invalid_for_online_rl、路径 visibility 失败全部被拒绝。
- verifier rejected 但基础设施可信的样本可以作为 negative sample，不能和 infrastructure error 混淆。
- 如果 valid 样本不足，refill attempts、invalid reason distribution 和 insufficient valid batch reason 必须可审计。

输出：

```text
formal_batch_and_refill_report.json
batch_refill_resample_report.json
dataproto_padding_profile.json
```

### Stage 12.6-6：真实 trainer global step smoke

目标：证明真实 `DataProto -> trainer -> global step` 路径跑过。

禁止把下面内容当作通过：

```text
只调用 compute_advantage
只调用 compute_policy_loss
只构造 DataProto
只跑 AgentLoopOutput postprocess
```

默认 trainer 命令从 Stage 12-C 成功配置开始，保守运行 1 到 2 个 global step。

必须记录：

- trainer command。
- Ray init 参数。
- actor / rollout / SGLang 配置。
- `calculate_log_probs=True`。
- valid sample 数量。
- invalid sample 过滤数量。
- DataProto tensor / non-tensor shape。
- prompt length / response length / padding ratio / loss mask ratio。
- `training/global_step` 或等价 trainer progress 证据。
- `actor/loss`、`actor/pg_loss` 或等价 policy loss 证据。
- GPU / Ray / SGLang 或 vLLM profile。

输出：

```text
dataproto_and_trainer_smoke_report.json
trainer_throughput_profile.json
inference_server_profile.json
tokenization_profile.json
ray_worker_resource_profile.json
system_resource_profile.json
```

### Stage 12.6-7：acceptance bundle

最终生成：

```text
runs/stage12_6-remote-<timestamp>/
  stage12_6_preflight.json
  stage12_6_command_log.sanitized.jsonl
  runtime_private/stage12_6_command_log.raw.jsonl
  git_state_before_after.json
  fixture_manifest.json
  fixture_sha256_report.json
  environment_cache_report.json
  workspace_cache_report.json
  concurrent_episode_report.json
  command_policy_and_runtime_visibility_report.json
  trainer_throughput_profile.json
  verifier_recorder_tool_hot_path_report.json
  batch_refill_resample_report.json
  dataproto_padding_profile.json
  evidence_path_leak_scan_report.json
  real_episode_task_pool_report.json
  formal_batch_and_refill_report.json
  dataproto_and_trainer_smoke_report.json
  inference_server_profile.json
  tokenization_profile.json
  ray_worker_resource_profile.json
  system_resource_profile.json
  visibility_and_batch_validation_report.json
  stage12_6_acceptance_summary.json
```

如果执行脚本合并了报告文件，`stage12_6_acceptance_summary.json` 必须写清：

```json
{
  "canonical_evidence_mapping": {
    "trainer_throughput_profile": "dataproto_and_trainer_smoke_report.json",
    "dataproto_padding_profile": "dataproto_and_trainer_smoke_report.json"
  }
}
```

## 7. 远端命令日志要求

所有远端关键命令必须同时形成两类日志：

```text
stage12_6_command_log.sanitized.jsonl
runtime_private/stage12_6_command_log.raw.jsonl
```

`runtime_private/stage12_6_command_log.raw.jsonl` 可以保留真实 `cwd`、`stdout_path`、`stderr_path`、workspace path、run directory 和远端调试所需路径，但必须明确标记为本地私有，不进入 batch、不进入公开报告、不进入 acceptance summary 的可传播字段。

`stage12_6_command_log.sanitized.jsonl` 是可传播 summary evidence，必须脱敏真实 dependency environment path、workspace path、run directory、`.repo_harness_runtime` 和 `.repo_harness_env_overlay`。

每条记录至少包含：

```text
name
cmd
cwd
started_at
ended_at
returncode
stdout_path
stderr_path
structured_failure_reason
```

真实路径可以保存在 runtime-private raw log 中，但可传播 summary 必须脱敏。

## 8. 通过标准

Stage 12.6 通过必须同时满足：

- 远端代码基于明确 commit。
- 远端执行前后 `git status --short` 可审计。
- 至少一轮 cold cache 和一轮 warm cache 完成。
- `tomli==2.0.1` 依赖任务证明 dependency environment cache 真实生效。
- `src/` layout 任务证明 verifier import 当前 workspace 源码。
- 至少一组 2 到 4 条并发 real episode 完成，且无 workspace、artifact、run directory、hidden runtime directory 串扰。
- 命令策略受控负例被结构化拒绝，并且不进入 trainer batch。
- 至少产生一个通过 formal batch validator 的 valid online RL sample。
- 至少完成一个真实 trainer global step。
- valid online RL sample 来自真实 `route=verl`、真实 `response_logprobs`、真实 generation records、真实 response spans 和真实 trainer 输入路径。
- invalid、timeout、infrastructure error、model format failure、verifier rejected、command policy blocked 分类可审计。
- 可传播 evidence 中没有真实 dependency environment path、workspace path、run directory、`.repo_harness_runtime` 或 `.repo_harness_env_overlay`。

## 9. 失败分类

Stage 12.6 失败时必须归入下面分类之一：

```text
remote_preflight_failure
model_download_failure
sglang_backend_failure
flashinfer_backend_failure
trainer_oom
trainer_config_error
repo_harness_adapter_failure
dependency_cache_failure
workspace_cache_failure
command_policy_too_strict
path_visibility_failure
formal_batch_validation_failure
batch_refill_failure
dataproto_shape_failure
trainer_global_step_failure
model_format_failure
verifier_rejected
infrastructure_error
```

如果失败是模型没有修复任务，但 infrastructure、batch、trainer 都正常，不能标记为 infra failure。

## 10. 执行后实例处理

远端完成后：

- 如果 Stage 12.6 通过，保留 evidence，推送代码或把 evidence 下载回本地，然后暂停 Vast.ai 实例。
- 如果出现无法继续的问题，先保存 stdout、stderr、command log、preflight、failure summary，再暂停实例。
- 暂停实例使用 Vast.ai CLI，保留数据，不要 destroy：

```bash
vastai stop instance <INSTANCE_ID>
```

实例 ID 必须从 `vastai show instances` 或用户提供的信息中确认，不能猜。

## 11. 后续关系

只有 Stage 12.6 通过后，才进入 Stage 13 fully async。

如果 Stage 12.6 未通过，Stage 13 必须先降级为：

```text
远端 smoke 阻断问题修复
或 fully async 接口预研
```

不能声称 RepoHarness 已经具备高吞吐 agentic RL infra。
