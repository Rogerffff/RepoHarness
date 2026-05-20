# Stage 14.1 补充执行计划：远端失败后的本地修复和重新验收

本文是 Stage 14.1 的补充执行计划。它承接
`27-stage-14-1-execution-plan.md`，专门处理第一次 Stage 14.1 远端 smoke
暴露出的三个问题：

```text
1. 训练链路已经跑通，但可信 trainable negative 没有进入正式事实链。
2. policy loss 确实消费了多个 RepoHarness 样本，但每个被消费样本没有完整 artifact 回查证据。
3. 公开 evidence 中泄漏了 runtime_private 路径和 evaluator-only 标记。
```

本计划不改变 Stage 14.1 的总体目标。Stage 14.1 仍然是：

```text
多任务 real episode
可信 final verifier rejected trainable negative
diagnostic side channel
fresh batch provenance
可机器验收的远端 fully async 多步训练 evidence
```

## 1. 当前失败状态

### 1.1 已经确认跑通的部分

最近一次远端 smoke 在 `2 * RTX PRO 6000`、`verlai/verl:sgl056.latest`、
`Qwen/Qwen2.5-Coder-1.5B-Instruct`、`full training`、`NIXL CUDA weight sync`
配置下，已经确认真实训练主链路可以跑通：

```text
verl fully_async_main
-> FullyAsyncRollouter
-> RepoHarnessVerlAgentLoop
-> RepoHarnessRuntime(real_episode)
-> tools / final verifier / reward boundary
-> TrainingView / AgentLoopOutput
-> MessageQueue
-> FullyAsyncTrainer
-> optimizer step
-> parameter synchronization
```

远端已观察到：

```text
completed_trainer_step_count = 4
global_steps = 8
current_param_version = 4
policy loss hook 记录到 8 条被消费样本
样本 route = verl
NIXL CUDA 参数同步成功
```

这说明当前失败不是显存问题，不是 `fully_async_main` 启动问题，也不是参数同步主链路问题。

### 1.2 没有通过 Stage 14.1 验收的部分

Stage 14.1 仍然没有通过，原因是证据链和样本语义没有闭合：

```text
trainable_negative_eligible_count = 0
policy-loss batch 中的 negative-control 样本仍显示 status=succeeded
每轮只有 1 个 real episode summary 落地，但 policy loss 消费了 8 条样本
公开 evidence 出现 runtime_private 路径
公开 evidence 出现 hidden_verifier evaluator-only 标记
```

因此当前只能表述为：

```text
fully async 多步训练链路已经跑通；
Stage 14.1 多任务、可信负样本、artifact 回查和公开 evidence 验收尚未通过。
```

## 2. 本地修复目标

本地修复必须先完成下面四件事。完成前不应再次启动远端 GPU 做正式 Stage 14.1 验收。

### 2.1 新增仓库内正式 negative-control fixture

之前远端为了快速构造负样本，使用了运行时生成的 fixture：

```text
runtime_private/generated_fixtures/stage14_negative_boundary
```

这个做法不适合作为正式 evidence，因为它会把 `runtime_private` 路径带入公开 manifest。

Stage 14.1 补充实现必须新增一个仓库内正式 fixture，例如：

```text
tests/fixtures/repos/stage14_negative_boundary/
tests/fixtures/tasks/task_stage14_negative_boundary.yaml
```

该 fixture 的要求：

```text
1. 任务目标必须是正常目标，不能要求模型故意写错。
2. final verifier 必须有清晰、稳定、可解释的 rejected 条件。
3. 如果模型给出语义不完整 patch，final verifier rejected 必须被分类为可信模型失败。
4. 可信 final verifier rejected 样本必须保持 invalid_for_training=false。
5. 可信 final verifier rejected 样本必须保持 invalid_for_online_rl=false。
6. fixture 文件中不能出现 hidden_verifier、gold patch、reward metadata 原文等 evaluator-only 标记。
```

公开 task fixture 只能包含模型可见任务目标、仓库引用和可执行环境引用。真正 verifier 逻辑、
期望输出、边界断言和 evaluator-only 配置必须以 evaluator-only 方式绑定，不能写进模型可见 prompt、
task pool 公开字段或公开 evidence。公开 evidence 中如果需要引用 verifier，只能使用：

```text
opaque verifier ref
sha256
文件大小
用途
是否 runtime-private
```

推荐 fixture 形态：

```text
仓库：一个极小 Python 包或单文件模块。
任务：要求实现正常功能。
verifier：同时检查普通路径和边界路径。
负样本触发方式：小模型如果只修普通路径、漏掉边界路径，就会 final verifier rejected。
```

不要使用下面做法：

```text
不要在 prompt 中要求模型故意失败。
不要在远端 runtime_private 临时创建任务。
不要把 hidden verifier 描述写入模型可见字段或公开 evidence。
不要把 verifier-only 信息写进 task pool manifest 的公开字段。
```

### 2.2 修复 trainable negative 的正式事实投影

Stage 14.1 必须证明 final verifier rejected 的可信负样本进入正式事实链。需要检查并修复：

```text
RepoHarnessEpisodeResult.status
RepoHarnessEpisodeResult.invalid_for_training
RepoHarnessEpisodeResult.invalid_for_online_rl
TrainingView.extra_fields.repo_harness_status
TrainingView.extra_fields.repo_harness_invalid_for_training
TrainingView.extra_fields.repo_harness_invalid_for_online_rl
reward boundary facts
final verifier facts
stage14 policy-loss hook records
stage14_1_trainable_negative_report.json
```

可信负样本的目标状态必须是：

```text
episode status = failed
final_verifier_status = rejected
reward_state = final 或 final_verifier_completed
invalid_for_training = false
invalid_for_online_rl = false
route = verl
response_ids 非空
response_logprobs 非空
generation_records 非空
visibility_scan_passed = true
policy_loss_consumed = true 或 eligible 但未被本轮消费
```

如果当前 batch facts 在 final verifier 完成前生成，应修改投影时机或补充最终 facts merge 逻辑。

如果当前 postprocess 只依赖 `summary.md` 或不完整运行目录，应改成优先读取结构化事实，例如：

```text
RepoHarnessEpisodeResult
TrainingView
generation_records
final verifier result
reward boundary report
policy-loss hook records
```

### 2.3 修复 policy-loss 样本到 artifact 的回查关系

远端观察到 policy loss hook 有 8 条被消费样本，但 `runtime_private/real_episode_runs/`
只有 1 个真实 episode summary。这说明训练侧和审计侧没有一一对齐。

Stage 14.1 本地修复必须让每个被 policy loss 消费的样本都至少能回查到：

```text
sample_id
episode_id
run_id
task_id
trajectory_digest
generation_record_digest
final verifier status
reward state
artifact reference
trainer_step_index
global_step
parameter_version
min_global_steps
max_global_steps
```

`sample_id` 必须唯一。`stage14_1_policy_loss_sample_ledger.json` 中
`consumed_by_policy_loss=true` 的记录数量必须等于 policy loss hook 实际记录的消费数量。
每条 consumed 记录都必须写出 `trainer_step_index`、`global_step`、`parameter_version`、
`min_global_steps` 和 `max_global_steps`，用于证明参数同步前后的样本窗口可以解释。

可以选择两种实现方式之一：

```text
方式 A：每个被消费样本都落地一个完整 real episode summary。
方式 B：不复制完整目录，但写出明确的 sample -> artifact reference ledger。
```

如果采用方式 B，必须新增或补强：

```text
stage14_1_policy_loss_sample_ledger.json
stage14_1_episode_artifact_ref_report.json
stage14_1_task_pool_report.json
```

验收器必须拒绝：

```text
policy loss 消费样本没有 artifact reference
artifact reference 指向不存在的 run artifact
artifact reference 和 sample_id / trajectory_digest 不一致
artifact reference 只指向一个 summary，但多个样本共用且无法区分
```

### 2.4 修复公开 evidence 脱敏和 manifest 规则

Stage 14.1 公开 evidence 不允许包含：

```text
runtime_private
/workspace/...
/Users/...
.repo_harness_env_overlay
.repo_harness_runtime
hidden_verifier
gold_patch
reward metadata 原文
provider secret
evaluator-only logs
```

如果 raw evidence 必须保留真实路径或 evaluator-only 内容，只能放入：

```text
runtime_private/
```

公开 evidence 只能记录：

```text
opaque ref
sha256
文件大小
用途
是否 runtime-private
```

需要补强扫描范围：

```text
json
jsonl
yaml
yml
txt
log
sh
py
parquet
source map
manifest
```

特别注意：fixture manifest、task pool report、parquet source map、acceptance summary 不能泄漏
`runtime_private` 或 evaluator-only 标记。

## 3. 建议修改文件

本地建议修改或新增：

```text
src/repo_harness_verl/stage14_acceptance.py
src/repo_harness_verl/stage14_remote_smoke.py
src/repo_harness_verl/stage14_task_pool.py
tests/unit/test_repo_harness_verl_stage14_acceptance.py
tests/unit/test_repo_harness_verl_stage14_remote_smoke.py
tests/unit/test_repo_harness_verl_stage14_task_pool.py
tests/fixtures/repos/stage14_negative_boundary/
tests/fixtures/tasks/task_stage14_negative_boundary.yaml
```

如果发现问题在 `RepoHarnessVerlAgentLoop`、`RepoHarnessRuntime(real_episode)` 或
`TrainingView -> AgentLoopOutput` 转换路径中，也允许修改：

```text
src/repo_harness_verl/agent_loop.py
src/repo_harness_verl/conversion.py
src/repo_harness/rl/runtime.py
```

但修改必须保持下面边界：

```text
repo_harness.rl 不能 import verl。
正式 online RL 样本仍必须 route=verl。
non-verl route、missing logprobs、visibility rejected、partial、stale、pending reward 不能进入 policy loss。
```

## 4. 本地测试计划

### 4.1 fixture 和 task pool 测试

新增或补强测试：

```text
tests/unit/test_repo_harness_verl_stage14_task_pool.py
```

覆盖：

```text
negative-control fixture 路径存在。
negative-control task yaml 不包含 hidden_verifier / gold_patch / runtime_private。
task pool 至少包含 3 个唯一 task id。
task pool 至少包含 accepted、dependency、negative-control、diagnostic side-channel 分类。
fixture manifest 不包含本地绝对路径。
fixture sha256 稳定。
```

### 4.2 trainable negative 投影测试

在本地构造最小 `RepoHarnessEpisodeResult` 或运行极小 fake episode，验证：

```text
final verifier rejected
status=failed
invalid_for_training=false
invalid_for_online_rl=false
reward_state=final
route=verl
logprobs 存在
generation_records 存在
```

验收器必须将其计入：

```text
trainable_negative_eligible_count
```

如果该样本进入 policy loss ledger，则还必须计入：

```text
trainable_negative_consumed_count
```

此外必须新增一个链路级测试，覆盖：

```text
RepoHarnessEpisodeResult(final verifier rejected)
-> TrainingView / AgentLoopOutput
-> queue facts 或 policy-loss sample ledger
-> stage14_1_trainable_negative_report.json
```

该测试重点断言：

```text
status=failed
final_verifier_status=rejected
reward_state=final
invalid_for_training=false
invalid_for_online_rl=false
```

这些字段不能在转换、postprocess、hook 记录或 ledger 生成阶段被改写成 `succeeded`。

### 4.3 artifact ledger 测试

构造一个 policy loss ledger，包含 3 条被消费样本。测试：

```text
每条样本都能找到 episode artifact reference。
artifact reference 的 run_id / episode_id / trajectory_digest 和样本一致。
只有 1 个 summary 却声称 3 个 consumed sample 时必须拒绝。
artifact reference 指向不存在文件时必须拒绝。
```

### 4.4 public evidence 脱敏测试

新增负例 evidence 包或 fixture，证明 inspector 会拒绝：

```text
runtime_private 路径出现在公开 json。
hidden_verifier 出现在公开 manifest。
/workspace/... 出现在公开 parquet source map。
.repo_harness_env_overlay 出现在公开 log。
公开 .py helper 未进入 patch manifest。
```

### 4.5 回归命令

本地至少运行：

```bash
PYTHONPATH=src:reference/verl:$PYTHONPATH PATH=.venv/bin:$PATH python -m compileall -q src

PYTHONPATH=src:reference/verl:$PYTHONPATH PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_remote_smoke.py \
  tests/unit/test_repo_harness_verl_stage14_task_pool.py \
  tests/unit/test_repo_harness_rl_stage13_0_async_contracts.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py

git diff --check -- \
  src/repo_harness_verl \
  src/repo_harness/rl \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_remote_smoke.py \
  tests/unit/test_repo_harness_verl_stage14_task_pool.py \
  tests/fixtures/repos \
  tests/fixtures/tasks \
  docs/agentic_RL/repo_harness_verl_workstreams/28-stage-14-1-follow-up-execution-plan.md

if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl src/repo_harness/agent_loop src/repo_harness/workspace src/repo_harness/verifier
then
  exit 1
fi
```

## 5. 本地提交要求

远端复测前必须先提交本地修复。

提交前必须确认：

```text
git status --short 中没有未登记的 Stage 14.1 代码或 fixture 修改。
新增 fixture 已进入 git。
新增测试已通过。
执行计划文档已更新。
```

建议拆分提交：

```text
commit 1: Stage 14.1 negative fixture 和 task pool 修复
commit 2: Stage 14.1 acceptance / evidence inspector 修复
commit 3: Stage 14.1 postprocess / artifact ledger 修复
```

如果修改范围很小，也可以合并成一个提交，但提交信息必须说明它是 Stage 14.1 remote follow-up。

## 6. 远端复测计划

### 6.1 远端准备

远端继续使用：

```text
GPU：2 * RTX PRO 6000，单卡约 96GB 显存
镜像：verlai/verl:sgl056.latest
模型：Qwen/Qwen2.5-Coder-1.5B-Instruct
训练策略：full training，lora_rank=0
权重同步：NIXL CUDA
rollout 后端：SGLang
```

远端步骤：

```text
1. 启动或新租 Vast.ai 实例。
2. 拉取本地提交后的最新分支。
3. 运行远端 preflight。
4. 生成 Stage 14.1 smoke kit。
5. 运行 fully_async_main。
6. postprocess 生成 Stage 14.1 reports。
7. 打包 evidence tarball。
8. 停止 Ray。
9. 暂停 Vast.ai 实例。
10. 下载 evidence 到本地。
11. 本地运行 inspect-stage14-fully-async-acceptance --assert-complete。
```

### 6.2 远端必须产生的报告

远端 evidence 至少包含：

```text
stage14_acceptance_summary.json
stage14_training_profile.json
stage14_hydra_overrides.json
stage14_environment_matrix.json
stage14_trainer_steps_report.json
stage14_parameter_sync_report.json
stage14_batch_provenance_report.json
stage14_1_task_pool_report.json
stage14_1_trainable_negative_report.json
stage14_1_side_channel_report.json
stage14_1_policy_loss_sample_ledger.json
stage14_1_episode_artifact_ref_report.json
stage14_public_path_leak_report.json
stage14_remote_patch_manifest.json
stage14_command_log.sanitized.jsonl
runtime_private/stage14_command_log.raw.jsonl
fixture_manifest.json
fixture_sha256_report.json
```

如果具体实现合并了报告文件，必须在：

```text
stage14_acceptance_summary.json.canonical_evidence_map
```

中清楚写明每个 canonical evidence item 对应哪个实际文件。

命令日志必须沿用公开和私有分层：

```text
公开 evidence：stage14_command_log.sanitized.jsonl
私有 evidence：runtime_private/stage14_command_log.raw.jsonl
```

公开命令日志不能包含远端真实路径、provider secret、evaluator-only 标记、raw Hydra secret、
`runtime_private` 真实路径或完整 raw command。私有命令日志可以保留完整命令，但只能进入
runtime-private manifest 和 sha256 报告，不能作为公开 canonical evidence 传播。

### 6.3 远端通过标准

远端 Stage 14.1 补充验收必须满足：

```text
completed_trainer_step_count >= 3
current_param_version >= 1
parameter_sync_count >= 2
valid_sample_count >= completed_trainer_step_count * required_samples
unique_real_episode_count >= 3
unique_task_id_count >= 3
policy_loss_consumed_unique_episode_count >= 3
policy_loss_consumed_unique_task_id_count >= 3
trainable_negative_eligible_count >= 1
policy_loss_queue_invalid_sample_count == 0
message_queue_dropped_sample_count == 0
fresh_trainer_batch_tensor_provenance_passed == true
public_path_leak_scan_passed == true
side_channel_sample_count >= 1
formal_validator_rejected_count 可以作为额外诊断指标，但不能替代 side channel 验收
instance_final_status 必须来自 evidence 打包或最终验收前重新采集的实例状态
规范化接受状态：actual_status=exited 或 cur_state=stopped
```

如果 `stage14_acceptance_summary.json` 中仍写着 `running`，即使事后已经人工暂停实例，
`--assert-complete` 也不能通过。执行脚本必须在打包 evidence 前或最终验收前重新采集 Vast.ai
实例状态，并把规范化后的状态写入 summary。

### 6.4 远端失败时的处理

如果再次失败，必须按失败类型处理：

```text
训练启动失败：
  记录 CUDA、SGLang、NIXL、Ray、Hydra 配置，停止实例，回本地修配置。

训练链路完成但 trainable negative 仍为 0：
  不允许冒充通过。记录每个 negative attempt 的 verifier / reward / batch facts。

policy loss 消费样本和 artifact ledger 不一致：
  不允许修 evidence 强行通过。回本地修 artifact ledger 或 runtime artifact emission。

公开 evidence 泄漏路径或 evaluator-only 标记：
  停止远端，回本地修 manifest / sanitizer / source map。
```

任何失败都必须生成：

```text
stage14_1_remote_diagnostic_findings.json
```

并写清楚：

```text
训练链路是否完成
trainer step 数
参数同步是否发生
policy loss 消费样本数
失败的验收项
是否暂停实例
下一步建议
```

## 7. 不能宣称通过的情况

出现以下任一情况，Stage 14.1 不能宣称通过：

```text
只有 trainer step 成功，但 trainable_negative_eligible_count = 0。
只有 hook record 显示多任务，但 artifact ledger 无法回查每条样本。
只有 runtime_private raw evidence 能证明事实，公开 evidence 无法安全传播。
diagnostic 样本进入 policy-loss MessageQueue。
missing logprobs / non-verl route / partial / stale 样本进入 policy loss。
batch provenance digest 来自手工修复，而不是 fresh trainer hook。
公开 evidence 包含 runtime_private、hidden_verifier、/workspace、/Users 等敏感内容。
```

## 8. 完成后的交付

Stage 14.1 补充验收通过后，应交付：

```text
本地代码提交
远端 evidence tarball
远端 evidence sha256
inspect-stage14-fully-async-acceptance --assert-complete 输出
stage14_1_remote_diagnostic_findings.json 或成功摘要
Vast.ai instance final status
```

最终汇报必须明确区分：

```text
训练链路是否跑通
Stage 14.1 多任务验收是否通过
trainable negative 是否真实合规
每个 policy-loss 样本是否可回查 artifact
公开 evidence 是否可以安全传播
```
