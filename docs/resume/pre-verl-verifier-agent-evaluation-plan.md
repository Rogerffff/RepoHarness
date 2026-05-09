# 接入 verl 之前的 RepoHarness 验证器可信度与智能体评测计划

## 1. 目标

本文档定义接入 `verl` 之前必须优先完成的一组可执行工作。目标不是训练出一个更强的编码智能体，而是先证明 RepoHarness 本身已经具备面向软件工程智能体训练和评测的可信基础设施能力：

```text
冻结任务 -> 可执行仓库环境 -> 真实 provider agent run -> 独立 final verifier -> 轨迹与结果分区 -> 可审计报告 -> 可追溯验收证据
```

本阶段需要产出两份核心报告：

1. `RepoHarness Verifier Correctness Report`，中文名称为“RepoHarness 验证器可信度报告”。
2. `RepoHarness Agent Evaluation Report`，中文名称为“RepoHarness 智能体评测报告”。

这两份报告是后续接入 `verl` 的前置证据。它们要回答两个面试官最容易追问的问题：

1. RepoHarness 用来判断补丁是否修复任务的 verifier 是否可信。
2. RepoHarness 统计真实 agent evaluation 分数时，分母、失败类型、污染边界和证据链是否清楚。

本文档中的 `build-pre-verl-*` 和 `inspect-pre-verl-*` 命令是需要新增或复用既有 builder / inspect 能力形成的计划入口。当前仓库尚未实现这些 pre-verl 专用命令时，不能把它们描述为已经可执行的现有命令。

## 2. 当前基线

当前 V5 已经通过 `core_acceptance`，但 `resume_ready_acceptance` 仍然是 blocked。最新可引用验收目录是：

```text
runs/v5-final-acceptance-accepted-20260506T130655Z/
```

当前可作为本计划起点的事实如下：

- 已有 12 个 accepted / auditable task definitions，其中 8 个来自 PR / issue flow，4 个来自 SWE-Bench-like anchors。
- 已有 7 条真实 DeepSeek provider run metadata，其中 1 条通过 strict final verifier。
- 已有 2 条 real provider trainable records，对应 1 条 SFT 样本和 1 条 reinforcement learning rollout 样本。
- 已有 1 条 diagnostic record 和 1 条 blocked record。
- OpenAI / DeepSeek 在 2 个任务上已经有 provider-axis supplemental proof，但它不能替代 scaffold comparison、budget comparison 和真实可比较 preference pair。
- V5 acceptance inputs、reference integrity report、final command log 和 acceptance bundle 已经完成不可变证据绑定。

以上基线事实只能理解为“与当前已绑定验收材料一致”。后续实施时，最终结论仍必须以显式传入的路径、sha256、size_bytes 和 command log 为准，不能依赖本文档中的自然语言描述替代机器绑定。

因此，本计划不重复证明 V5 core acceptance，而是在 V5 core acceptance 之上扩展评测规模和报告能力。

## 3. 非目标和禁止表述

本阶段不做以下事情：

- 不接入 `verl`。
- 不训练模型。
- 不在 SWE-Bench Lite 上训练后再报告 SWE-Bench Lite 分数。
- 不声称完成 SWE-Bench Lite 或 SWE-Bench Verified 公开榜单复现。
- 不声称结果可以和公开 leaderboard 直接比较。
- 不声称已经完成完整 preference export。
- 不声称已经训练出 coding agent。
- 不声称 RepoHarness 是生产级安全沙箱。

本阶段允许使用的表述是：

```text
RepoHarness 已经可以在自定义冻结评测集上生成可审计的 verifier correctness report 和 agent evaluation report。报告中的每个 accepted、rejected、diagnostic、blocked、empty patch、environment failed 和 verifier failed 结论都能追溯到任务定义、源码哈希、provider run、补丁、verifier plan、trajectory、command log 和 evidence bundle。
```

## 4. 任务集合设计

本阶段构建一个新的“接入 verl 前评测任务集”，不要覆盖或悄悄替换现有 V5 core task set。

### 4.1 任务来源

计划任务集合分三层：

```text
Tier 0: 23 个 SWE-Bench Lite development instances，用作自定义冻结开发评测子集。
Tier 1: 50 个 curated SWE-Bench Lite tasks，用作自定义冻结精选评测子集。
Tier 2: 10 到 20 个 GitHub issue flow tasks
```

其中，23 个 development instances 用于快速开发和调试，50 个 curated SWE-Bench Lite tasks 用于更稳定的评测统计，GitHub issue flow tasks 用于证明 RepoHarness 不只服务于标准 benchmark，也能覆盖真实或半真实工程任务。

该任务集合是 RepoHarness 自定义冻结评测集，不构成 SWE-Bench Lite 官方分数，也不得和公开 leaderboard 直接比较。任何报告中出现的 `SWE-Bench Lite development instances` 或 `curated SWE-Bench Lite tasks` 都必须同时写明 `custom_frozen_subset=true` 和 `leaderboard_comparable=false`。

如果某个 SWE-Bench Lite development instance 在当前数据源中不能被稳定解析或不能准备可执行环境，必须标记为 `blocked_dataset_or_environment`，不能临时替换成别的任务后仍然声称“23 个 development instances 全部完成”。

### 4.2 GitHub issue flow task 的最低要求

每个 GitHub issue flow task 必须明确区分模型可见内容和 evaluator-only 内容。

模型可见内容可以包括：

- issue 标题。
- issue 摘要。
- 问题复现描述。
- 允许模型读取的仓库源码。
- 必要的公开失败现象说明。

模型不可见内容必须包括：

- gold patch。
- raw pull request diff。
- review comment。
- hidden test patch。
- official resolved status。
- fix commit URL。
- merge commit URL。
- final verifier raw output。
- reward scalar 和 reward label。

具体例子：

```text
task_id: github_issue_click_3364
model_visible:
  issue_summary: 点击按钮后状态没有更新。
  allowed_source_tree: 固定 commit 的公开源码。
evaluator_only:
  hidden_test_patch: 用于复现点击状态错误的测试补丁。
  gold_patch: 原始修复补丁，只能用于 verifier correctness，不得进入模型上下文。
verifier:
  baseline: 应用 hidden_test_patch 后，未修复源码必须失败。
  candidate: 应用 candidate patch 和 hidden_test_patch 后，测试必须通过。
```

## 5. 阶段 0：基线冻结

### 5.1 目标

冻结本计划的输入、当前代码状态和既有 V5 core evidence，避免后续报告引用漂移。

### 5.2 产物

建议输出目录：

```text
runs/pre-verl-eval-stage0-baseline-YYYYMMDDTHHMMSSZ/
```

必须生成：

```text
pre_verl_baseline_check_report.json
pre_verl_input_binding.json
pre_verl_stage0_command_log.jsonl
```

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-baseline
repo-harness inspect-pre-verl-baseline PRE_VERL_INPUT_BINDING --assert-baseline-complete
```

### 5.3 最低检查

必须记录以下内容：

- `pwd`
- `git status --short`
- `git log -1 --oneline`
- 当前 V5 core acceptance report 路径和 sha256。
- 当前 V5 export pack manifest 路径和 sha256。
- 当前 V5 result summary table 路径和 sha256。
- 当前 V5 acceptance bundle 路径和 sha256。

建议执行：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-accepted-20260506T130655Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-accepted-20260506T130655Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

如果当前工作区存在无关既有改动，只能记录，不能删除、回滚或纳入本计划产物。

## 6. 阶段 1：扩展任务冻结和可见性扫描

### 6.1 目标

构建一个明确的、不可变的、可机器检查的任务集合，用于后续 verifier correctness 和 agent evaluation。

### 6.2 产物

建议输出目录：

```text
runs/pre-verl-eval-stage1-task-freeze-YYYYMMDDTHHMMSSZ/
```

必须生成：

```text
pre_verl_task_set_manifest.json
pre_verl_task_inventory_report.json
pre_verl_task_visibility_scan_report.json
pre_verl_task_source_binding.json
pre_verl_task_freeze_command_log.jsonl
```

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-task-set
repo-harness inspect-pre-verl-task-set PRE_VERL_TASK_SET_MANIFEST --assert-task-freeze-complete
repo-harness inspect-pre-verl-task-visibility PRE_VERL_TASK_VISIBILITY_SCAN_REPORT --assert-clean
```

### 6.3 任务状态分类

每个任务必须被分类为以下状态之一：

```text
accepted_for_verifier_correctness
accepted_for_agent_evaluation
diagnostic_only
blocked_dataset_or_environment
blocked_visibility_risk
blocked_verifier_missing
blocked_dependency_unstable
```

同一个任务可以进入 verifier correctness，但不进入 agent evaluation。例如：某个任务有可靠 gold patch 和 verifier，可以用于 verifier correctness；但它的依赖安装需要外部网络且不可缓存，就不能进入真实 provider agent evaluation。

### 6.4 通过条件

阶段 1 最低通过条件：

- 至少 23 个 SWE-Bench Lite development instances 被绑定；不能运行的任务必须有 blocked reason。
- 至少 50 个 curated SWE-Bench Lite tasks 被绑定；不能运行的任务必须有 blocked reason。
- 至少 10 个 GitHub issue flow tasks 被绑定；如果不足 10 个，必须生成 blocked report，不能假装完成。
- 所有 accepted task 都有 source tree hash。
- 所有 accepted task 都有 verifier plan。
- 所有 accepted task 都通过 visibility scan。
- 模型可见内容中 hidden artifact leakage finding 数量为 0。

### 6.5 分母层级

任务冻结报告必须显式拆分分母，不能只给一个总数。

至少包含：

```text
planned_denominator
bound_task_denominator
runnable_denominator
verifier_correctness_denominator
agent_evaluation_planned_denominator
real_provider_terminal_outcome_denominator
trainable_export_eligible_denominator
```

这些分母的含义如下：

- `planned_denominator`：计划纳入的任务数量，包括可能失败或 blocked 的任务。
- `bound_task_denominator`：已经绑定 task definition、source tree hash 和输入来源的任务数量。
- `runnable_denominator`：依赖、环境和 verifier plan 均准备完成，理论上可以运行 verifier 的任务数量。
- `verifier_correctness_denominator`：已经具备 no-op、gold patch 或明确豁免、determinism 和 visibility 检查条件的任务数量。
- `agent_evaluation_planned_denominator`：计划交给真实 provider agent run 的任务数量。
- `real_provider_terminal_outcome_denominator`：完成真实 provider 调用、产生结构化终止结果，并排除 diagnostic-only、structured skip、mock、replay、fallback success 和 synthetic-safe stress record 后的任务数量。
- `trainable_export_eligible_denominator`：通过 strict final verifier boundary 且允许进入训练导出的真实 provider run 数量。

任何 `accepted_rate`、`resolved_rate`、`pass@1` 或类似比例都必须声明使用哪个分母。第一版报告推荐只使用 `accepted_rate`，避免使用容易让人误解为公开 benchmark 口径的 `resolved_rate`。

## 7. 阶段 2：Verifier Correctness Report

### 7.1 目标

证明 RepoHarness 的 verifier 能正确区分“没有修复”“错误修复”和“有效修复”，并且同一输入下结果稳定。

### 7.2 每个任务的检查项

每个进入 `accepted_for_verifier_correctness` 的任务都必须运行以下检查，除非报告中给出结构化豁免原因。任何缺少必需检查且没有豁免的任务，只能进入 `diagnostic_only` 或 `blocked`，不能进入 agent evaluation 强分数，也不能进入 trainable export。

#### 7.2.1 gold patch replay

如果任务有 gold patch，则从冻结源码创建干净 workspace，应用 gold patch，再运行 formal verifier。

通过含义：

```text
gold patch 在 RepoHarness verifier 中能够通过。
```

失败含义：

```text
该任务的 verifier 或依赖环境可能与原始 benchmark 不一致，不能直接用于 agent evaluation 分数。
```

#### 7.2.2 no-op fail

不应用任何候选补丁，只应用 evaluator-only 测试补丁，然后运行 verifier。

通过含义：

```text
未修复源码会失败，verifier 不会产生明显 false positive。
```

失败含义：

```text
空补丁也能通过，说明 verifier 太弱，该任务必须 blocked 或 diagnostic-only。
```

#### 7.2.3 invalid patch fail

应用一个格式正确但逻辑错误的补丁，再运行 verifier。

通过含义：

```text
verifier 能拒绝错误修复。
```

失败含义：

```text
verifier 只能检测补丁是否存在，不能检测问题是否真正修复。
```

#### 7.2.4 strict patch replay

如果任务已经有真实 provider final patch，则从冻结源码重建 verification workspace，应用 provider final patch，再运行 final verifier。

通过含义：

```text
agent workspace 中产生的补丁可以在独立 verification workspace 中复放。
```

#### 7.2.5 verifier determinism

对同一个源码、同一个补丁、同一个 verifier 连续运行 3 次。

通过含义：

```text
3 次结果完全一致，包括 accepted、exit_code、timed_out、关键 failure category。
```

失败含义：

```text
verifier 存在不稳定性，任务不能进入强 agent evaluation 分数，只能进入 diagnostic-only 或 flaky bucket。
```

### 7.3 报告字段

必须生成：

```text
pre_verl_verifier_correctness_report.json
pre_verl_verifier_correctness_summary.md
pre_verl_docker_phase_coverage_matrix.json
pre_verl_verifier_correctness_command_log.jsonl
```

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-verifier-correctness
repo-harness inspect-pre-verl-verifier-correctness PRE_VERL_VERIFIER_CORRECTNESS_REPORT --assert-verifier-correctness-complete
repo-harness inspect-pre-verl-docker-phase-coverage PRE_VERL_DOCKER_PHASE_COVERAGE_MATRIX --assert-docker-phase-coverage-complete
```

报告至少包含：

```text
total_tasks
accepted_for_verifier_correctness_count
gold_patch_replay_pass_count
gold_patch_replay_fail_count
no_op_fail_pass_count
no_op_fail_unexpected_pass_count
invalid_patch_fail_pass_count
invalid_patch_unexpected_pass_count
strict_patch_replay_success_count
verifier_deterministic_count
verifier_flaky_count
environment_setup_failed_count
blocked_count
hidden_leakage_finding_count
evidence_hash_drift_finding_count
parser_confidence_mean
low_parser_confidence_count
patch_apply_failed_count
pass_to_pass_regression_count
final_verifier_boundary_missing_count
```

其中：

- `parser_confidence_mean` 和 `low_parser_confidence_count` 用于标记任务解析、补丁抽取或 verifier 输出解析是否足够可信。
- `patch_apply_failed_count` 用于区分模型没有修复和补丁无法应用。
- `pass_to_pass_regression_count` 用于记录候选补丁破坏原本应通过测试的情况。
- `final_verifier_boundary_missing_count` 必须为 0，任何缺少 final verifier boundary 的 run 都不能进入 accepted 或 trainable export。

### 7.4 Docker phase coverage matrix

`pre_verl_docker_phase_coverage_matrix.json` 用来证明可执行仓库环境不是一个黑盒。它必须按任务记录每个关键阶段是否执行、是否成功、耗时、失败类型和 evidence ref。

至少覆盖以下阶段：

```text
source_checkout_or_restore
dependency_install_or_cache_restore
baseline_test_patch_apply
candidate_patch_apply
verifier_command_run
artifact_collection
workspace_cleanup
```

每个阶段至少记录：

```text
phase_name
attempted
succeeded
duration_ms
failure_category
failure_owner
command_log_ref
stdout_ref
stderr_ref
```

汇总指标至少包括：

```text
tasks_with_all_required_phases_count
source_restore_failed_count
dependency_install_failed_count
baseline_test_patch_apply_failed_count
candidate_patch_apply_failed_count
verifier_command_failed_count
artifact_collection_failed_count
workspace_cleanup_failed_count
p50_phase_duration_ms_by_phase
p95_phase_duration_ms_by_phase
```

如果某个任务因为数据集缺失、依赖不可恢复或平台不支持而没有进入某个阶段，必须写入 blocked reason，不能把未执行阶段统计成通过。

### 7.5 面试可展示例子

可以展示类似下面的单任务证据链：

```text
任务: v5_task_008
冻结源码: source_tree_sha256 = ...
provider: DeepSeek V4 Pro
模型输出: final patch
baseline 检查: 未修复源码 + hidden test patch 失败
candidate 检查: provider final patch + hidden test patch 通过
final_verifier_status: accepted
导出结果: 生成 1 条 SFT 样本和 1 条 reinforcement learning rollout 样本
```

这能说明 RepoHarness 不是把 provider 输出直接当成训练样本，而是用 strict final verifier 做训练数据边界。

## 8. 阶段 3：Agent Evaluation Report

### 8.1 目标

在固定任务、固定源码、固定 verifier、固定工具策略、固定 context policy、固定 budget 的前提下，运行真实 provider agent evaluation，并给出明确分母。

本阶段必须把 baseline、provider、scaffold 和 budget 都当作正式受控轴。第一版可以只完成单 provider 主线评测，但报告必须明确哪些轴被固定、哪些轴被比较、哪些轴仍然 blocked。

### 8.2 第一轮推荐 provider 和模型

建议先用 DeepSeek 完成主线评测，因为当前 DeepSeek API 余额更充足。

```text
强 API model: DeepSeek V4 Pro，作为第一轮正式评测主模型。
中等或低成本 API model: DeepSeek V4 Flash，作为链路烟测和失败分类调试模型。
补充 provider-axis proof: OpenAI gpt-5.4-nano 链路烟测，OpenAI gpt-5.5 小规模正式对比，前提是余额允许。
本地 coder model: 第二轮目标；如果本地模型、推理服务或工具调用协议尚未准备好，必须标记为 blocked_local_model_runtime_not_ready。
```

如果 provider 余额耗尽、服务不可用或模型没有产出可验证补丁，必须生成 blocked evidence，不能把失败 run 伪装为 accepted 或 trainable。

第一版 Agent Evaluation Report 可以只要求强 API model 和中等或低成本 API model 完成。文档原建议中的本地 coder model 不作为第一版硬门槛，但必须在报告中明确它是 `deferred`、`blocked` 还是已经执行，避免让读者误以为本地模型评测已经完成。

### 8.3 第一轮评测范围

第一轮不要直接跑全部任务。建议按以下顺序递进：

```text
Smoke: 2 个任务
Pilot: 23 个 SWE-Bench Lite development instances
Main: 23 个 development instances + 50 个 curated Lite tasks
Extension: Main + 10 到 20 个 GitHub issue flow tasks
```

如果 Smoke 阶段出现 credential、provider adapter、patch extraction 或 final verifier 问题，必须先修链路或生成 blocked report，不能直接扩大到 Main。

### 8.4 实验矩阵和受控变量

每个 evaluation cell 必须记录：

```text
task_id
source_tree_hash
baseline_id
provider_id
model_id
scaffold_id
budget_policy_id
tool_policy_id
context_policy_id
verifier_plan_ref
environment_id
provider_registry_snapshot_ref
dependency_cache_ref
docker_image_or_environment_ref
```

Provider 对比必须固定 task、source tree、final verifier plan、tool policy、context policy、scaffold、budget 和 environment id。

Scaffold 对比必须固定 task、source tree、final verifier plan、tool policy、context policy、provider、budget 和 environment id。

Budget 对比必须固定 task、source tree、final verifier plan、tool policy、context policy、provider、scaffold 和 environment id。

如果某个对比没有满足这些受控变量，只能写成 `observational_result`，不能写成 controlled comparison。

### 8.5 预算、重复运行和 provider 配置

每轮真实 provider evaluation 必须显式记录：

```text
max_real_provider_calls
max_cost_usd
max_input_tokens
max_output_tokens
episode_timeout_seconds
verifier_timeout_seconds
retry_policy
model_exact_id
temperature
top_p
seed_policy
provider_registry_snapshot_ref
credential_gate_report_ref
cost_budget_report_ref
dependency_cache_ref
docker_image_or_environment_ref
```

如果 provider 不支持 seed，必须写成 `seed_policy=provider_seed_unavailable`。如果 provider 不返回 token 或 cost metadata，必须写成 `unavailable_provider_metadata`，不能填估算值冒充真实返回值。

### 8.6 统计口径

报告必须明确区分以下数量：

```text
total_planned_tasks
actual_agent_run_tasks
actual_provider_call_count
submitted_patch_count
empty_patch_count
accepted_count
rejected_count
diagnostic_only_count
blocked_count
environment_setup_failed_count
verifier_failed_count
verifier_timed_out_count
provider_error_count
cost_limited_skip_count
credential_missing_skip_count
```

`accepted_rate` 的默认分母字段命名为 `real_provider_terminal_outcome_denominator`，含义是：

```text
完成真实 provider 调用、产生结构化终止结果，并且已经排除 diagnostic-only、structured skip、mock、replay、fallback success 和 synthetic-safe stress record 之后的任务数量。
```

不得把以下记录混入 accepted rate 分母：

```text
mock record
replay record
credential missing skip
adapter not implemented skip
cost-limited structured skip
fallback success
diagnostic-only record
synthetic-safe stress record
```

### 8.7 统计有效性

每个核心比例必须同时报告点估计和不确定性。

至少包含：

```text
accepted_rate_point_estimate
accepted_rate_denominator_name
accepted_rate_denominator_value
accepted_rate_wilson_interval_95
empty_patch_rate_point_estimate
verifier_failure_rate_point_estimate
environment_failure_rate_point_estimate
```

如果使用 bootstrap，必须记录：

```text
bootstrap_method
bootstrap_replicates
bootstrap_seed_policy
bootstrap_interval_95
```

Provider、scaffold 和 budget 对比优先使用 paired comparison。只有同一组任务、同一源码、同一 verifier plan 和同一环境都满足时，才能声明 paired comparison。否则必须标记为 `observational_result`。

### 8.8 延迟和资源指标

报告必须记录：

```text
mean_episode_time
p50_episode_time
p95_episode_time
mean_verifier_time
p95_verifier_time
mean_tool_call_count
p95_tool_call_count
mean_generated_token_count
p95_generated_token_count
provider_cost_estimate
```

如果 token 或 cost 无法从 provider 返回值可靠获得，字段必须标记为 `unavailable_provider_metadata`，不能填猜测值。

### 8.9 产物

必须生成：

```text
pre_verl_agent_evaluation_report.json
pre_verl_agent_evaluation_summary.md
pre_verl_agent_evaluation_run_matrix_manifest.json
pre_verl_agent_evaluation_failure_taxonomy.json
pre_verl_agent_evaluation_command_log.jsonl
```

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-agent-evaluation-run-matrix
repo-harness run-pre-verl-agent-evaluation
repo-harness build-pre-verl-agent-evaluation-report
repo-harness inspect-pre-verl-agent-evaluation PRE_VERL_AGENT_EVALUATION_REPORT --assert-agent-evaluation-pilot-complete
```

如果运行 OpenAI / DeepSeek provider-axis comparison，还必须生成：

```text
pre_verl_provider_axis_comparison_report.json
```

该报告必须包含：

```text
comparison_axis
controlled_variables
compared_cells
comparison_validity
actual_records_by_provider
blocked_claims
```

## 9. 阶段 4：Agent Runtime Invariant Audit

### 9.1 目标

本阶段检查真实 agent run 的运行时轨迹是否满足 RepoHarness 的 agent runtime 不变量。这个阶段不是评估模型聪明不聪明，而是评估 harness 是否正确记录、约束和回放智能体交互。

必须检查：

- query loop 是否有明确开始、结束和终止原因。
- `tool_use` 和 `tool_result` 是否一一配对。
- 工具调用是否遵守 tool policy。
- 权限边界是否阻止 risky command、credential 读取和 evaluator-only 证据泄漏。
- context compaction 是否保留必要任务状态，同时不引入 hidden evidence。
- transcript diagnostics 是否能解释失败、超时、空补丁、补丁无法应用和 verifier 失败。

### 9.2 产物

必须生成：

```text
pre_verl_agent_runtime_trace_report.json
pre_verl_tool_contract_matrix.json
pre_verl_permission_boundary_report.json
pre_verl_context_compaction_stress_report.json
pre_verl_transcript_diagnostics_report.json
pre_verl_agent_runtime_invariant_command_log.jsonl
```

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-agent-runtime-audit
repo-harness inspect-pre-verl-agent-runtime-audit PRE_VERL_AGENT_RUNTIME_TRACE_REPORT --assert-runtime-invariants-clean
```

### 9.3 硬门槛

以下 finding 必须为 0：

```text
unpaired_tool_use_count
unpaired_tool_result_count
tool_policy_violation_count
permission_boundary_violation_count
credential_access_finding_count
evaluator_only_model_visible_finding_count
context_compaction_hidden_evidence_finding_count
transcript_missing_terminal_state_count
```

如果某条 trajectory 没有 terminal state 或缺少 tool result 配对，它不能进入 agent evaluation 强分数，也不能进入训练导出。

## 10. 阶段 5：Training Export Audit

### 10.1 目标

本阶段把训练导出审计提升为一等阶段。它不是为了证明已经训练模型，而是为了证明接入 `verl` 之前的 SFT、reinforcement learning rollout、failure dataset 和 preference 相关数据边界是干净、可追溯、可阻断的。

### 10.2 产物

必须生成：

```text
pre_verl_export_result_pack_manifest.json
pre_verl_sft_export.jsonl
pre_verl_rl_rollout_export.jsonl
pre_verl_failure_dataset.jsonl
pre_verl_preference_pair_blocked_report.json
pre_verl_reward_source_taxonomy_report.json
pre_verl_reward_boundary_audit_report.json
pre_verl_export_contamination_scan_report.json
pre_verl_training_export_audit_command_log.jsonl
```

如果存在真实可比较 preference pair，可以用合规的 preference export manifest 替代 `pre_verl_preference_pair_blocked_report.json`。如果不存在真实可比较 preference pair，必须生成 blocked report，并且 claim gate 必须禁止 `preference export completed` 表述。

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-export-audit
repo-harness inspect-pre-verl-export-audit PRE_VERL_EXPORT_RESULT_PACK_MANIFEST --assert-export-clean
repo-harness inspect-pre-verl-reward-boundary PRE_VERL_REWARD_BOUNDARY_AUDIT_REPORT --assert-reward-boundary-clean
```

### 10.3 硬门槛

以下 finding 必须为 0：

```text
non_accepted_run_in_trainable_export_count
diagnostic_only_in_trainable_payload_count
blocked_record_in_trainable_payload_count
reward_scalar_model_visible_count
reward_label_model_visible_count
provider_raw_request_in_trainable_payload_count
provider_raw_response_in_trainable_payload_count
credential_marker_in_trainable_payload_count
final_verifier_raw_output_in_trainable_payload_count
```

每条可训练样本必须绑定：

```text
task_ref
source_tree_ref
trajectory_ref
final_patch_ref
final_verifier_boundary_ref
reward_metadata_ref
export_record_sha256
```

没有 strict final verifier accepted boundary 的 run，只能进入 failure dataset、diagnostic-only 或 blocked 分区。

## 11. 阶段 6：报告绑定、claim gate 和 public-safe 展示包

### 11.1 目标

将阶段 1 到阶段 5 的报告绑定为一个接入 `verl` 前的评测证据包，并由 claim gate 决定哪些数字和表述可以写进简历或面试材料。

### 11.2 产物

建议输出目录：

```text
runs/pre-verl-eval-final-YYYYMMDDTHHMMSSZ/
```

必须生成：

```text
pre_verl_evaluation_inputs.json
pre_verl_evaluation_report.json
pre_verl_evaluation_reference_integrity_report.json
pre_verl_evaluation_bundle_manifest.json
pre_verl_evaluation_bundle_command_lineage_report.json
build_pre_verl_evaluation_bundle_command_log_entry.json
inspect_pre_verl_evaluation_bundle_command_log_entry.json
pre_verl_evaluation_final_command_log.jsonl
pre_verl_public_safe_scan_report.json
pre_verl_resume_claim_gate_report.json
pre_verl_result_summary_table.json
pre_verl_public_demo_index.json
pre_verl_demo_card.md
pre_verl_demo_card.json
pre_verl_interview_qa.md
pre_verl_interview_qa_evidence.json
pre_verl_interview_summary.md
```

建议新增或复用的命令：

```bash
repo-harness build-pre-verl-evaluation-inputs
repo-harness inspect-pre-verl-evaluation-inputs PRE_VERL_EVALUATION_INPUTS --assert-evaluation-inputs-complete
repo-harness build-pre-verl-evaluation-report
repo-harness inspect-pre-verl-evaluation PRE_VERL_EVALUATION_REPORT --assert-evaluation-report-complete
repo-harness build-pre-verl-claim-gate
repo-harness inspect-pre-verl-claim-gate PRE_VERL_RESUME_CLAIM_GATE_REPORT --assert-claims-consistent
repo-harness build-pre-verl-evaluation-bundle
repo-harness inspect-pre-verl-evaluation-bundle PRE_VERL_EVALUATION_BUNDLE --final-command-log PRE_VERL_FINAL_COMMAND_LOG --assert-immutable
repo-harness inspect-pre-verl-public-safe PRE_VERL_PUBLIC_SAFE_SCAN_REPORT --assert-share-safe
```

### 11.3 public-safe 展示内容

面向面试官可以展示：

- 任务来源统计。
- verifier correctness 汇总。
- agent evaluation 汇总。
- provider-axis comparison 边界。
- failure taxonomy。
- latency summary。
- accepted run 的 sanitized walkthrough。
- 训练导出 readiness 状态。

不能展示：

- provider raw request。
- provider raw response。
- credential marker。
- hidden test patch。
- gold patch 原文。
- raw pull request diff。
- final verifier raw output。
- reward scalar。
- reward label。

### 11.4 泄漏扫描范围

`pre_verl_public_safe_scan_report.json` 和 export contamination scan 必须覆盖以下位置：

```text
adapter_visible_task_input
prepared_messages
model_visible_transcript
trajectory_observations
tool_results
context_compaction_summary
stdout
stderr
trainable_sft_payload
trainable_rl_rollout_payload
failure_dataset
public_demo_index
interview_summary
interview_qa
demo_card
```

以下内容不得出现在上述模型可见、可训练或 public-safe 位置：

```text
evaluator_only_evidence
gold_patch
raw_test_patch
hidden_test_selector
raw_provider_request
raw_provider_response
credential_marker
credential_path
final_verifier_raw_output
reward_scalar
reward_label
official_resolved_status
raw_pr_diff
review_comment
fix_commit_url
merge_commit_url
```

### 11.5 claim gate 硬门槛

`pre_verl_resume_claim_gate_report.json` 必须把每个可写进简历或面试材料的数字映射到 evidence ref。

至少包含：

```text
allowed_claims
blocked_claims
claim_to_evidence_refs
claim_to_denominator
claim_to_sha256
claim_to_public_safe_artifact
```

如果某个 claim 没有 path、sha256 和 denominator，必须进入 `blocked_claims`。

### 11.6 最终证据链硬门槛

最终证据包必须满足以下机器检查：

- `pre_verl_evaluation_inputs.json` 只能绑定报告生成前已经存在的 evidence。
- `pre_verl_evaluation_reference_integrity_report.json` 必须递归检查被绑定 JSON 内部的 evidence refs。
- `pre_verl_evaluation_bundle_manifest.json` 必须绑定最终 public-safe 展示包、评测报告、verifier correctness report、agent evaluation report、agent runtime invariant audit、training export audit、Docker phase coverage matrix、claim gate 和 command logs。
- `pre_verl_evaluation_bundle_command_lineage_report.json` 必须证明 bundle build entry 和 bundle inspect entry 都指向当前最终 bundle，而不是 previous bundle 或 pre-final bundle。
- `pre_verl_public_safe_scan_report.json` 必须证明 public-safe demo index、interview summary 和 walkthrough 中没有 hidden tests、gold patch、raw provider request、raw provider response、credential marker、reward scalar 和 final verifier raw output。
- `pre_verl_evaluation_final_command_log.jsonl` 必须绑定构建最终 bundle 和检查最终 bundle 的命令 entry。

## 12. 阶段 7：接入 verl 前的决策门

只有以下条件全部满足，才建议进入 `verl` 接入：

- 阶段 1 任务冻结通过。
- 阶段 2 verifier correctness report 通过。
- 阶段 3 agent evaluation report 至少完成 Pilot。
- 阶段 4 agent runtime invariant audit 通过。
- 阶段 5 training export audit 通过。
- 阶段 6 claim gate 和 public-safe 展示包通过。
- hidden leakage finding 数量为 0。
- evidence hash drift finding 数量为 0。
- no-op unexpected pass 的任务没有进入 agent evaluation accepted denominator。
- verifier flaky 的任务没有进入强分数统计。
- failed、diagnostic-only、blocked 记录没有进入 trainable export。
- public-safe 展示包通过 share-safe 检查。

建议新增或复用的最终决策命令：

```bash
repo-harness inspect-pre-verl-readiness PRE_VERL_EVALUATION_REPORT --assert-verl-ready
```

如果阶段 2 或阶段 3 没有通过，仍然可以接入 `verl` 做技术 smoke test，但不能把它描述为建立在可信 benchmark 上的训练闭环，只能描述为 adapter feasibility proof。

## 13. 推荐实施顺序

建议按以下顺序执行：

```text
第 1 步：冻结 23 个 development instances 和 50 个 curated Lite tasks。
第 2 步：补充 10 到 20 个 GitHub issue flow tasks。
第 3 步：对全部任务做 visibility scan 和 verifier readiness 分类。
第 4 步：先跑 no-op fail 和 gold patch replay。
第 5 步：对可用任务跑 verifier determinism 3 次复测。
第 6 步：用 DeepSeek V4 Flash 跑 2 个任务链路烟测。
第 7 步：用 DeepSeek V4 Pro 跑 23 个 development instances。
第 8 步：如果 Pilot 稳定，再扩展到 50 个 curated Lite tasks。
第 9 步：如果预算允许，用 OpenAI 做 2 到 5 个任务的 provider-axis comparison。
第 10 步：执行 agent runtime invariant audit。
第 11 步：执行 training export audit。
第 12 步：生成 claim gate、pre-verl evaluation bundle 和 public-safe interview summary。
```

## 14. 大厂面试推荐讲法

完成本计划后，推荐使用下面的项目叙事：

```text
我没有直接把 SWE 轨迹塞进强化学习框架，而是先构建了 RepoHarness 的 verifier correctness、agent evaluation、runtime invariant audit 和 training export audit 证据层。系统会冻结任务、源码、verifier 和工具策略；对每个任务运行 no-op、gold patch、错误补丁和真实 provider patch 的严格复放检查；再用真实 provider agent run 生成 accepted、rejected、diagnostic 和 blocked 分区。只有通过 strict final verifier 的真实 provider run 才能进入 SFT 和 reinforcement learning rollout export。每个可展示数字都由 claim gate 绑定 path、sha256、分母、command log 和 public-safe artifact。完成这些之后，再把可信 trajectory 接入 verl，做小规模 agentic post-training 实验。
```

这比直接说“我接入了 verl”更有说服力，因为它先回答了训练前最关键的问题：任务是否可信，verifier 是否可信，reward 边界是否可信，训练样本是否干净。

## 15. 最小可交付版本

如果时间有限，最小可交付版本是：

```text
任务集:
  23 个 SWE-Bench Lite development instances
  10 个 GitHub issue flow tasks

Verifier Correctness:
  no-op fail
  gold patch replay
  strict patch replay
  verifier determinism 3 次复测
  visibility scan

Agent Evaluation:
  DeepSeek V4 Flash 2 个任务 smoke
  DeepSeek V4 Pro 23 个任务 Pilot
  明确 accepted、rejected、diagnostic、blocked、empty patch、environment failed、verifier failed

Runtime and Export Audit:
  agent runtime invariant audit
  training export audit
  reward boundary audit
  public-safe leakage scan

展示包:
  pre_verl_evaluation_report.json
  pre_verl_resume_claim_gate_report.json
  pre_verl_result_summary_table.json
  pre_verl_interview_summary.md
  pre_verl_interview_qa.md
  public-safe accepted run walkthrough
```

最小版本通过后，再扩展到 50 个 curated Lite tasks 和 OpenAI / DeepSeek provider-axis comparison。
