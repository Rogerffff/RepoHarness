# Stage 14.1 执行计划：多任务 real episode 扩展和远端负例 side channel

本文是 Stage 14.1 的具体执行计划。它承接 Stage 14.0 已经完成的
`inspect-stage14-fully-async-acceptance` 验收器、远端 smoke profile、证据包结构和
fully async 链路脚本化能力。

Stage 14.1 的目标不是扩大模型规模，也不是实现 partial rollout / resume。它的目标是：
在 Stage 14.0 已经跑通的 `dev_smoke_2x96gb_small_full_sync` profile 上，把“单类任务、少量样本”
扩展成“多任务池、可训练负样本候选、diagnostic side channel 和更严格 batch provenance”的
可机器验收远端 smoke。

默认远端 profile 仍然是：

```text
GPU：2 * RTX PRO 6000，单卡约 96GB 显存
镜像：verlai/verl:sgl056.latest
模型：Qwen/Qwen2.5-Coder-1.5B-Instruct
训练策略：full training，lora_rank=0
权重同步策略：NIXL CUDA weight sync
rollout 后端：SGLang
```

## 1. 阶段目标和非目标

### 1.1 必须完成的目标

Stage 14.1 必须完成下面五类能力：

1. **多任务真实 episode 池**
   - 远端 evidence 至少包含 `unique_real_episode_count >= 3`。
   - 远端 evidence 至少包含 `unique_task_id_count >= 3`。
   - 被 policy loss 实际消费的样本也必须来自多任务池，至少满足
     `policy_loss_consumed_unique_episode_count >= 3` 和 `policy_loss_consumed_unique_task_id_count >= 3`。
   - 任务池必须覆盖无外部依赖任务、轻量第三方 Python 依赖任务、`src/` layout 或等价 workspace import 任务。
   - 每个真实 episode 都必须经过 `RepoHarnessVerlAgentLoop -> RepoHarnessRuntime(real_episode) -> tools -> final verifier -> reward boundary -> TrainingView -> AgentLoopOutput -> MessageQueue`。

2. **可信 trainable negative 候选**
   - 至少产生 1 个可信 final verifier rejected 的 trainable negative 候选。
   - 该样本必须满足 route、token、logprob、generation record、response span、visibility、final verifier finality 和 reward finality 全部合规。
   - 报告必须区分 `trainable_negative_eligible_count` 和 `trainable_negative_consumed_count`。
   - 不能把 timeout、cancelled、format failure、missing logprob、non-verl route、visibility rejected、partial 或 stale 样本当作 trainable negative。

3. **diagnostic / rejected side channel**
   - 至少产生 1 个受控 diagnostic 或 formal validator rejected 样本。
   - diagnostic / rejected 样本必须走物理隔离 side channel，例如 `stage14_1_side_channel_report.json` 或独立 artifact。
   - 真实 policy-loss MessageQueue 不能接收 diagnostic / rejected 样本。

4. **post-sync 多样本训练链路**
   - 至少完成 3 到 4 个 trainer step。
   - 至少发生一次训练后 parameter synchronization。
   - 至少 2 个 parameter synchronization 之后产生的 valid sample 进入 policy-loss queue。
   - summary 和底层 report 必须明确写出 `post_sync_policy_loss_consumed_sample_count >= 2`、
     `post_sync_policy_loss_consumed_unique_episode_count >= 2`，并解释 `trajectory_param_versions`、
     `min_global_steps` 和 `max_global_steps`。

5. **fresh batch provenance**
   - Stage 14.1 的 fresh remote run 必须由真实 trainer hook 或等价远端 helper 直接产出 `response_ids`、`response_mask`、`rollout_log_probs` 的 digest 和 shape。
   - Stage 14.1 的正式验收不能继续依赖 Stage 14.0 repaired evidence 中的 `component_digest_source=repaired_from_stage14_summary_and_raw_run_script`。

### 1.2 本阶段不做的事情

Stage 14.1 不做：

- 不打开真实 `async_training.partial_rollout=True`。
- 不让 partial trajectory 进入 policy loss。
- 不实现 partial checkpoint、resume 或 durable resume。
- 不做模型收敛验收。
- 不做大规模 SWE-Bench 训练。
- 不把旧 `repo-harness run-task`、`run-batch`、`run-experiment` 和离线 export 迁移到 `RepoHarnessRuntime.run_episode(...)`。
- 不升级到 4 卡、8 卡或 7B 全参数训练，除非 Stage 14.1 smoke 遇到明确的容量阻断并形成单独 profile 变更记录。

## 2. 任务池设计

### 2.1 默认任务池

Stage 14.1 默认使用仓库内现有极小 fixture，并在实施时新增一个冻结的轻量第三方依赖 fixture。
它不依赖外部 SWE-Bench 数据。

建议任务池：

```text
accepted_baseline:
  repo: tests/fixtures/repos/security_probe
  task_ref: tests/fixtures/tasks/task_security_probe.yaml
  目标：无外部依赖基线任务，final verifier accepted。

accepted_src_layout:
  repo: tests/fixtures/repos/import_config_bug
  task_ref: tests/fixtures/tasks/task_002.yaml
  目标：覆盖 package / source import 任务，final verifier accepted。

accepted_create_file:
  repo: tests/fixtures/repos/missing_helper_file
  task_ref: tests/fixtures/tasks/task_003_create_file.yaml
  目标：覆盖创建缺失源码文件的简单真实任务，final verifier accepted。

accepted_dependency:
  repo: tests/fixtures/repos/dependency_packaging_smoke
  task_ref: tests/fixtures/tasks/task_dependency_packaging_smoke.yaml
  dependency: tomli==2.0.1
  目标：覆盖 dependency environment / setup 路径。若该 fixture 尚不存在，Stage 14.1 实施时必须新增。
       该 fixture 必须固定纯 Python 小依赖、锁定版本、记录 wheel 或 sdist 的 sha256，
       并把 setup policy 写入 task fixture，避免远端临时联网安装变成不可复现变量。

trainable_negative_control:
  repo: tests/fixtures/repos/buggy_calculator
  task_ref: tests/fixtures/tasks/task_001.yaml
  目标：使用固定 negative-control prompt variant 和有限重试，争取产生可信 final verifier rejected 样本。
       不允许在 prompt 中直接要求模型“故意写错代码”；负样本必须表现为模型在正常任务目标下给出语义不完整或错误 patch。

diagnostic_control:
  task_ref: side-channel-only，不写入真实 policy-loss MessageQueue。
  目标：构造 missing logprob、non-verl route、visibility rejected 或 format failure 样本；
       样本必须进入 side channel，不能进入 policy-loss MessageQueue。
```

Stage 14.1 的任务池必须精确到可执行的 task yaml，不能只记录 repository fixture。新增第三方依赖 fixture 时，
必须同时新增 `tests/fixtures/repos/...` 和 `tests/fixtures/tasks/...yaml`，并进入 `stage14_fixture_manifest.json`、
`stage14_fixture_sha256_report.json`、本地 `git diff --check` 检查和远端 evidence manifest。

如果远端镜像已经缓存了 `tomli==2.0.1` 的 wheel，可以优先使用缓存；如果必须下载，下载命令、package index、
sha256 和安装位置必须进入 evidence。共享依赖环境测试仍必须证明该环境不会被 episode 命令写入或污染。

### 2.2 trainable negative 的口径

可信 trainable negative 必须同时满足：

```text
episode_status = failed
final_verifier_status = rejected
reward_state = final 或 final_verifier_completed
route = verl
response_ids 非空
response_logprobs 非空并和 response_ids 对齐
generation_records 非空并和 TrainingView token provenance 对齐
visibility_scan_passed = true
invalid_for_training = false
invalid_for_online_rl = false
partial_rollout_supported = false
partial_rollout_status = not_requested 或 complete
```

该样本可以进入 policy loss，reward / outcome 是负向。它不能和 infrastructure error 或 evaluator failure 混在一起。

Stage 14.1 需要固定 negative-control 策略：

```text
task_ref = tests/fixtures/tasks/task_001.yaml
max_negative_control_attempts = 3
每次尝试必须使用独立 run_id、sample_id、attempt_id 和 prompt_digest。
每次尝试必须进入 stage14_1_task_pool_report.json 和 stage14_1_trainable_negative_report.json。
```

如果所有尝试都被真实模型修对，或者只产生 format failure、timeout、infrastructure error 这类不可训练失败，
Stage 14.1 不能通过 `--assert-complete`。此时应记录：

```text
trainable_negative_eligible_count = 0
stage14_1_status = pending_trainable_negative
```

为了降低远端不稳定性，Stage 14.1 可以同时准备多个 normal-goal negative-control 候选任务，
但每个候选都必须是正常模型可见目标，不能要求模型故意写错。推荐策略是让 verifier 覆盖更细边界，
例如除基本功能外再检查异常路径、边界输入或配置导入行为；如果模型提交的 patch 语义不完整，final verifier
可以可信 rejected。所有候选任务、prompt variant、attempt 上限和失败分类必须写入
`stage14_1_trainable_negative_report.json`，不能在远端执行时临时手工替换而不留证据。

### 2.3 diagnostic side channel 的口径

diagnostic 样本包括：

```text
missing_logprobs
non_verl_route
visibility_rejected
model_format_failure
timeout
cancelled
partial_rollout_unsupported
pending_reward
pending_verifier
stale_trajectory
```

这些样本不能写入真实 policy-loss MessageQueue。它们只能写入 side channel report、artifact 或独立 diagnostic queue。

Stage 14.1 的 diagnostic control 不能进入 `data.train_files` 这条真实
`FullyAsyncRollouter -> MessageQueue -> FullyAsyncTrainer` 主路径。若需要构造 diagnostic 样本，
必须由 postprocess、side-channel helper 或独立 diagnostic queue 生成，并在
`stage14_1_side_channel_report.json` 中证明：

```text
policy_loss_queue_inserted = false
policy_loss_consumed = false
policy_loss_sample_ledger_ref = null
```

## 3. 推荐实现文件和模块归属

建议修改或新增：

```text
src/repo_harness_verl/stage14_acceptance.py
src/repo_harness_verl/stage14_remote_smoke.py
src/repo_harness_verl/stage14_task_pool.py
tests/unit/test_repo_harness_verl_stage14_acceptance.py
tests/unit/test_repo_harness_verl_stage14_remote_smoke.py
tests/unit/test_repo_harness_verl_stage14_task_pool.py
tests/fixtures/repos/<optional_dependency_fixture>/
docs/agentic_RL/repo_harness_verl_workstreams/27-stage-14-1-execution-plan.md
```

职责建议：

```text
stage14_task_pool.py:
  Stage14TaskPoolEntry schema
  Stage14TaskPoolSpec schema
  默认 Stage 14.1 任务池构造
  task pool manifest 写出
  fixture sha256 helper

stage14_remote_smoke.py:
  扩展远端 smoke kit builder，支持 Stage 14.1 多任务池
  写出 train / val parquet
  写出 accepted 和 negative-control train rows
  diagnostic-control 只能写入 side-channel helper 输入或独立 diagnostic queue 配置，
  不能写入真实 policy-loss `data.train_files`

stage14_acceptance.py:
  扩展 inspect-stage14-fully-async-acceptance
  检查 unique episode / task count
  检查 trainable negative eligibility / consumption
  检查 side channel 物理隔离
  检查 fresh batch provenance，不接受 repaired digest 作为 Stage 14.1 完整通过证据
```

如果实现时认为新模块过重，可以先把 `Stage14TaskPoolSpec` 放在 `stage14_remote_smoke.py`，但代码中必须保持清晰的 schema 和测试覆盖。

## 4. Evidence contract 变更

Stage 14.1 继续使用 Stage 14.0 canonical evidence items，并新增或加严以下报告。

### 4.1 新增报告

```text
stage14_1_task_pool_report.json
stage14_1_trainable_negative_report.json
stage14_1_side_channel_report.json
stage14_1_policy_loss_sample_ledger.json
stage14_1_batch_provenance_report.json
```

具体执行可以把这些报告合并到已有 Stage 14 文件中，但 `stage14_acceptance_summary.json` 的
`canonical_evidence_map` 必须写清楚映射关系。

### 4.2 acceptance summary 新增字段

Stage 14.1 summary 在 Stage 14.0 字段基础上新增：

```text
stage = 14.1
unique_real_episode_count
unique_task_id_count
policy_loss_consumed_unique_episode_count
policy_loss_consumed_unique_task_id_count
trajectory_digest_count
valid_sample_count
accepted_count
final_verifier_rejected_trainable_count
trainable_negative_eligible_count
trainable_negative_consumed_count
formal_validator_rejected_count
diagnostic_sample_count
side_channel_sample_count
invalid_reason_distribution
post_sync_valid_sample_count
post_sync_policy_loss_consumed_sample_count
post_sync_policy_loss_consumed_unique_episode_count
post_sync_final_verifier_rejected_trainable_count
trajectory_param_versions
min_global_steps
max_global_steps
policy_loss_queue_valid_sample_count
policy_loss_queue_invalid_sample_count
message_queue_produced_sample_count
message_queue_consumed_sample_count
message_queue_dropped_sample_count
fresh_trainer_batch_tensor_provenance_passed
batch_provenance_source
```

`batch_provenance_source` 必须是：

```text
trainer_hook
remote_helper_hook
```

不能是：

```text
repaired_from_stage14_summary_and_raw_run_script
manual_reconstruction
unknown
```

### 4.3 task pool report

`stage14_1_task_pool_report.json` 至少包含：

```text
task_pool_name
task_pool_digest
task_count
unique_task_id_count
entries[]
```

每个 `entries[]` 至少包含：

```text
task_id
task_category
repo_fixture_ref
task_ref
expected_outcome_class
dependency_profile
source_layout
negative_control
diagnostic_control
fixture_sha256
```

### 4.4 trainable negative report

`stage14_1_trainable_negative_report.json` 至少包含：

```text
trainable_negative_eligible_count
trainable_negative_consumed_count
eligible_samples[]
rejected_non_trainable_failure_samples[]
```

每个 eligible sample 至少包含：

```text
sample_id
attempt_id
prompt_digest
task_id
episode_id
run_id
trajectory_digest
generation_record_digest
visibility_scan_digest
final_verifier_status
reward_state
reward_score
route
response_token_count
response_logprob_count
policy_loss_consumed
trainer_step_index 或 null
```

### 4.5 side channel report

`stage14_1_side_channel_report.json` 至少包含：

```text
side_channel_sample_count
by_reason
samples[]
```

每个 side channel sample 至少包含：

```text
sample_id
reason
source
route
would_have_been_policy_loss_valid
policy_loss_queue_inserted = false
diagnostic_ref
```

## 5. Inspector 加严规则

Stage 14.1 的 inspector 必须拒绝：

1. `unique_real_episode_count < 3`。
2. `unique_task_id_count < 3`。
3. `policy_loss_consumed_unique_episode_count < 3`。
4. `policy_loss_consumed_unique_task_id_count < 3`。
5. `accepted_count < 1`。
6. `trainable_negative_eligible_count < 1`。
7. `diagnostic_sample_count < 1` 且 `formal_validator_rejected_count < 1`。
8. `post_sync_policy_loss_consumed_sample_count < 2`。
9. `post_sync_policy_loss_consumed_unique_episode_count < 2`。
10. `trajectory_param_versions`、`min_global_steps` 或 `max_global_steps` 缺失，或无法解释 post-sync 样本窗口。
11. `policy_loss_queue_invalid_sample_count != 0`。
12. `message_queue_dropped_sample_count != 0`。Stage 14.1 默认不接受 dropped policy-loss queue sample；
   如果未来要测试受控 drop，必须作为独立 diagnostic 阶段处理，不能通过 Stage 14.1 `--assert-complete`。
13. `trainable_negative_consumed_count > trainable_negative_eligible_count`。
14. trainable negative 样本缺少 final verifier finality、reward finality、route、logprob、generation record、response span 或 visibility digest。
15. side channel 样本出现在 policy-loss MessageQueue ledger 中。
16. `batch_provenance_source` 是 repaired / manual / unknown。
17. `stage14_batch_provenance_report.json` 缺少真实 tensor digest 和 shape。
18. summary 中的 `valid_sample_count`、`formal_validator_rejected_count`、`post_sync_valid_sample_count`
    与 task pool、policy-loss ledger、side channel report 或 trainer step report 中的计数不一致。
19. batch provenance digest 没有绑定 `sample_id`、`trainer_step_index`、`trajectory_digest`
    和 `stage14_1_policy_loss_sample_ledger.json` 中的 policy-loss sample 记录。

## 6. 本地实现步骤

### 6.1 task pool schema 和 builder

1. 新增 `Stage14TaskPoolEntry` 和 `Stage14TaskPoolSpec`。
2. 编写默认 Stage 14.1 task pool。
3. 生成 task pool manifest 和 fixture sha256 report。
4. 增加单元测试覆盖：
   - 至少 3 个唯一 task id。
   - 至少一个 accepted category。
   - 至少一个 trainable negative control category。
   - 至少一个 diagnostic control category。
   - fixture 路径必须存在。
   - manifest 中不能出现本机绝对路径。

### 6.2 remote smoke kit 扩展

1. `write_stage14_remote_smoke_kit(...)` 或新函数支持 `stage="14.1"`。
2. 写出多任务 train / val parquet。
3. 每一行必须包含：
   ```text
   prompt
   raw_prompt
   agent_name=repo_harness
   repo_harness_task_ref
   uid
   index
   session_id
   global_steps
   repo_harness_task_category
   repo_harness_expected_outcome_class
   ```
4. diagnostic control 不得写入真实 policy-loss MessageQueue。如果需要构造 diagnostic 样本，应在 postprocess 或 side channel helper 中生成。

### 6.3 acceptance inspector 扩展

1. 读取 Stage 14.1 新增报告。
2. 验证 summary 与底层 report count 一致。
3. 验证 trainable negative eligibility。
4. 验证 side channel 与 policy-loss queue 物理隔离。
5. 验证 fresh batch provenance。
   - 每条 batch provenance 记录必须绑定 `sample_id`、`trainer_step_index` 和 `trajectory_digest`。
   - `stage14_1_policy_loss_sample_ledger.json` 中每个 consumed sample 必须能找到对应 tensor digest 和 shape。
   - provenance digest 必须来自真实 trainer hook 或 remote helper hook，不能来自 summary / raw script 的离线补强。
6. 增加负例测试：
   - 缺少 trainable negative。
   - side channel 样本进入 policy-loss queue。
   - trainable negative 缺少 logprob。
   - `trainable_negative_consumed_count` 大于 eligible count。
   - batch provenance source 是 repaired。
   - batch provenance digest 未绑定 policy-loss ledger。
   - unique task id 不足。

## 7. 远端执行策略

远端执行仍使用 `2 * 96GB GPU` 和 `dev_smoke_2x96gb_small_full_sync`。

执行顺序：

```text
1. 本地提交 Stage 14.1 代码。
2. 远端拉取该提交。
3. 运行 preflight。
4. 生成 Stage 14.1 smoke kit。
5. 运行 fully_async_main。
6. postprocess 生成 Stage 14.1 reports。
7. 本地下载 evidence tarball。
8. 本地运行 inspect-stage14-fully-async-acceptance --assert-complete。
```

如果远端真实模型无法自然产生 trainable negative：

```text
1. 不允许把 infrastructure error 或 diagnostic 样本冒充 trainable negative。
2. 可以调整模型可见 negative-control prompt，但必须记录 prompt digest、尝试次数和结果。
3. 如果有限重试后仍没有可信 rejected 样本，Stage 14.1 不能标记为 complete。
```

## 8. 验收命令

本地实现后至少运行：

```bash
PYTHONPATH=src:reference/verl:$PYTHONPATH PATH=.venv/bin:$PATH python -m compileall -q src

PYTHONPATH=src:reference/verl:$PYTHONPATH PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_remote_smoke.py \
  tests/unit/test_repo_harness_verl_stage14_task_pool.py \
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

git diff --check -- \
  src/repo_harness_verl \
  tests/unit/test_repo_harness_verl_stage14_acceptance.py \
  tests/unit/test_repo_harness_verl_stage14_remote_smoke.py \
  tests/unit/test_repo_harness_verl_stage14_task_pool.py \
  tests/fixtures/repos \
  tests/fixtures/tasks \
  docs/agentic_RL/repo_harness_verl_workstreams/27-stage-14-1-execution-plan.md

PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import repo_harness.rl
import repo_harness_verl
print("ordinary_import_ok")
PY

if rg -n '(^|\s)(import|from)\s+verl' \
  src/repo_harness/rl src/repo_harness/agent_loop src/repo_harness/workspace src/repo_harness/verifier
then
  exit 1
fi
```

如果 `tests/unit/test_repo_harness_verl_stage14_task_pool.py` 在实施前尚不存在，实施时必须创建该测试文件，不能把不存在的测试文件留在最终验收命令中。

## 9. 通过标准

Stage 14.1 只有同时满足以下条件，才能标记为完成：

```text
本地 Stage 14.1 单元测试通过。
Stage 13 / Stage 14 关键回归通过。
远端 fresh Stage 14.1 evidence 通过 inspect-stage14-fully-async-acceptance --assert-complete。
unique_real_episode_count >= 3。
unique_task_id_count >= 3。
policy_loss_consumed_unique_episode_count >= 3。
policy_loss_consumed_unique_task_id_count >= 3。
accepted_count >= 1。
trainable_negative_eligible_count >= 1。
diagnostic_sample_count >= 1 或 formal_validator_rejected_count >= 1。
policy_loss_queue_invalid_sample_count == 0。
message_queue_dropped_sample_count == 0。
valid_sample_count >= completed_trainer_step_count * required_samples。
post_sync_valid_sample_count >= 2。
post_sync_policy_loss_consumed_sample_count >= 2。
post_sync_policy_loss_consumed_unique_episode_count >= 2。
trajectory_param_versions / min_global_steps / max_global_steps 可解释。
fresh_trainer_batch_tensor_provenance_passed == true。
batch_provenance_source 不是 repaired / manual / unknown。
```

完成后可以进入 Stage 14.2。Stage 14.1 通过不表示 partial rollout / resume 可用，也不表示模型收敛。
