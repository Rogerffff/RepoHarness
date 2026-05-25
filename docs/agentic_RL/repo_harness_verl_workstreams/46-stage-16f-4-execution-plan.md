# Stage 16F.4 执行计划：`run_task(...)` 与 `run_episode` 入口一致性审计

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.4 的目标是用小规模、可机器复验的 parity audit，回答一个具体问题：

```text
旧测评入口 run_task(...)
和新测评入口 repo-harness run-episode-task
在模型可见上下文、工具集合、公开环境、verifier、patch hygiene、reward 和训练资格事实上是否一致？
```

这一阶段不是迁移阶段，不负责让旧 `run_task(...)` 内部转调 `run_episode(...)`。它只负责比较、归因和给出下一阶段是否可以迁移的证据。

完成后应该得到：

```text
run_task_run_episode_parity_report.json
stage16f4_acceptance_summary.json
stage16f4_blocking_differences.json
stage16f4_expected_differences.json
```

如果差异是预期差异，必须解释为什么安全。如果差异会影响 Stage 17 数据冻结、SFT target、preference pair、reward evidence 或 formal online RL gate，则必须标为 blocking，不能进入 Stage 16F.5。

## 2. 前置条件

执行前必须确认：

```text
Stage 16F.0 status=passed
Stage 16F.1 status=passed
Stage 16F.2 status=passed
Stage 16F.3 status=passed
Stage 16F.3 commit 已存在
```

当前 Stage 16F.3 提交为：

```text
fce58d83 feat: add stage16f3 run episode task entry
```

必须读取以下输入：

```text
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_run_task_run_episode_gap_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/stage16f1_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_2/stage16f2_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_acceptance_summary.json
```

如果 `run-episode-task --assert-projection-complete` 不能通过，Stage 16F.4 必须停止，不能用旧 `run_task(...)` 的成功结果替代新入口验收。

## 3. 非目标

Stage 16F.4 不做以下事情：

1. 不删除或废弃旧 `run_task(...)`。
2. 不让旧 `run_task(...)` 内部转调 `run_episode(...)`。
3. 不修改 Stage 16A 到 Stage 16E 已经建立的安全边界。
4. 不运行远端 GPU 训练。
5. 不运行 20 到 30 题代表性诊断扩展。
6. 不把 `mock`、`fake`、`replay`、`openai` 或 `deepseek` 轨迹标记为 formal online RL policy loss 样本。
7. 不把 parity audit 的通过结果等同于 Stage 17 数据集已经冻结。

如果执行过程中发现必须重构旧入口才能完成比较，应把该问题记录为 Stage 16F.5 的迁移前置项，而不是在 Stage 16F.4 中顺手重写。

## 4. 对比样本范围

第一版 parity audit 应选择 3 到 5 个小任务。前四类是硬性覆盖要求，不能只跑简单 happy path 后把未覆盖项计为 0：

```text
1. 已知 final verifier rejected 的微型任务。
2. 已知 final verifier accepted 的微型任务。
3. 使用 public test feedback 的任务。
4. 使用 patch hygiene cleaned final.patch 的任务。
5. 如果 fixture 已存在，可加入一个 replay route 任务；如果 replay 路径尚未稳定，则记录 deferred，不阻塞本阶段。
```

验收报告必须显式记录：

```text
accepted_case_count >= 1
rejected_case_count >= 1
public_feedback_case_count >= 1
patch_hygiene_case_count >= 1
replay_route_case_status = covered | deferred_with_reason
```

如果 public feedback 或 patch hygiene 没有被真实覆盖，Stage 16F.4 不能通过。`replay` route 可以延期，但必须写明原因、风险和下一阶段补测位置。

`public_feedback_case_count` 只能由真实轨迹中的公开测试反馈事件计数，不能只看 `RunConfig.test_feedback_policy`、scaffold 配置或任务声明。每个 public feedback case 必须同时记录：

```text
old_public_feedback_observed
new_public_feedback_observed
old_public_feedback_tool_call_id_or_event_ref
new_public_feedback_tool_call_id_or_event_ref
public_feedback_observation_digest
```

如果旧入口或新入口没有真实出现 `run_tests` 工具调用、公开测试反馈 observation、`verifier_result_preview.accepted` 或等价公开反馈事件，该样本不能计入 `public_feedback_case_count`。

`patch_hygiene_case_count` 至少需要一个 `cleaned_patch_empty=false` 的样本，并且必须记录非空 `final.patch` / `final.diff` 的 sha256。空 patch 样本可以作为额外对照，但不能单独满足 patch hygiene 覆盖要求。

每个任务必须分别运行：

```text
repo-harness run-task TASK_PATH --config RUN_CONFIG --output-dir OLD_RUNS --run-id RUN_ID_OLD
repo-harness run-episode-task TASK_PATH --config RUN_CONFIG --output-dir NEW_RUNS --run-id RUN_ID_NEW --assert-projection-complete
```

如果同一个 `RunConfig` 不能同时服务两个入口，应新增最小 fixture，并在报告中记录：

```text
run_config_pairing_reason
old_run_config_sha256
new_run_config_sha256
expected_config_difference
```

不能悄悄用不同工具集合、不同 feedback policy 或不同 verifier plan 跑两个入口，然后把结果写成一致。

## 5. 必须比较的字段

### 5.1 模型可见上下文

必须比较：

```text
initial_messages_digest
raw_prompt_digest
public_environment_context_digest
public_environment_prompt_block_digest
scaffold_id
tool_protocol_digest
tool_schema_snapshot_digest
allowed_tool_names
allowed_tool_names_digest
```

如果两个入口的 digest 不一致，必须把差异分类为：

```text
expected_difference
implementation_gap
legacy_projection_missing
run_episode_projection_missing
```

其中 `implementation_gap` 会阻塞 Stage 16F.5。

### 5.2 工具集合和工具执行语义

必须比较：

```text
allowed_tool_registry_digest
allowed_tool_names
execute_bash_description_digest
diagnostic_shell_availability
diagnostic_shell_backend
diagnostic_shell_exec_semantics
run_tests_feedback_policy
tool_call_pairing_status
tool_visibility_gate_status
```

重点确认：

```text
Stage 16A execute_bash 最小训练工具面没有被 run_episode 放宽。
Stage 16B diagnostic_shell 只有显式 scaffold 启用时才出现。
run directory、runtime-private 路径、hidden evaluator 信息不会进入任何模型可见工具输出。
```

### 5.3 Verifier、reward 和反馈策略

必须比较：

```text
resolved_verifier_plan_digest
test_feedback_policy
feedback_tests_passed_policy
final_verifier_command_digest
final_verifier_status
verifier_summary.accepted
reward_summary.score
reward_summary.invalid_for_training
reward_summary.invalid_reason
public_feedback_observed
public_feedback_tool_call_id_or_event_ref
public_feedback_observation_digest
```

如果旧入口和新入口的 final verifier 结果不同，必须区分：

```text
真实模型行为差异
workspace state 差异
final verifier factory 差异
test feedback policy 差异
projection 读取差异
```

不能只记录“一个 accepted，一个 rejected”而不归因。

### 5.4 Patch hygiene 和 official prediction 相关事实

必须比较：

```text
final.patch sha256
final.diff sha256
final_patch_hygiene_report.cleaned_patch_sha256
final_patch_hygiene_report.cleaned_diff_sha256
final_patch_hygiene_report.status
final_patch_hygiene_report.only_filtered_changes
final_patch_hygiene_report.filtered_file_count
final_patch_hygiene_report.flagged_file_count
final_patch_hygiene_report.cleaned_patch_empty
nonempty_cleaned_patch_observed
```

新入口必须读取 `compat_projection/final.patch`、`compat_projection/final.diff` 和 `compat_projection/final_patch_hygiene_report.json`，不能绕过 Stage 16F.3 的 projection binding helper。

如果旧入口的根目录 `final.patch` 与新入口的 `compat_projection/final.patch` 不一致，必须记录：

```text
patch_difference_status
old_patch_sha256
new_cleaned_patch_sha256
changed_file_set_difference
patch_hygiene_difference_reason
```

只有 patch 内容一致，或者差异被明确归因为模型行为差异，才能算通过。由于 mock / replay 路径可能产生不同模型行为，计划内允许存在 `expected_model_behavior_difference`，但不能存在 patch hygiene 规则差异。

### 5.5 训练资格和 provider route 事实

必须比较：

```text
provider_route
llm_gateway_route
invalid_for_training
invalid_for_online_rl
formal_online_rl_eligible
policy_loss_candidate
training_view_available
generation_records_available
response_logprobs_available
```

规则：

```text
mock / fake / replay / openai / deepseek 默认不能成为 formal online RL 或 policy loss candidate。
route=verl 才可能成为 formal online RL 候选，但 Stage 16F.4 第一版不要求运行 route=verl。
外部 API provider 轨迹可以作为测评、SFT 候选或 preference 候选，但不能伪装成 online RL 样本。
```

如果报告中出现非 `verl` route 的 `policy_loss_candidate=true`，Stage 16F.4 必须失败。

## 6. 新增 parity helper 和报告

建议新增或等价实现：

```text
src/repo_harness/evaluation/episode_parity.py
```

它负责：

```text
读取旧 run_task run directory。
读取新 run_episode compat_projection。
调用 Stage 16F.3 projection validator。
生成字段级差异。
分类 expected / blocking / diagnostic-only difference。
输出公开安全报告。
```

必须新增机器验收命令或等价脚本：

```text
repo-harness inspect-stage16f4-parity PARITY_DIR --assert-complete
```

如果暂时不新增 CLI 命令，必须至少提供可测试的 Python helper，并在 evidence 中记录：

```text
inspect_stage16f4_parity_cli_status = deferred
python_helper_assert_complete_status = passed
```

但 Stage 16F.4 不应该只生成 Markdown。必须有机器可读报告和测试。

## 7. Evidence 目录和文件

建议生成：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_parity_input_manifest.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_run_task_run_episode_parity_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_blocking_differences.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_expected_differences.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_projection_binding_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_test_report.json
```

公开 evidence 不能包含：

```text
本机绝对路径
真实 workspace 路径
真实 run directory 路径
runtime-private 真实路径
hidden verifier 原文
gold patch
test patch
raw_patch_sha256
raw_diff_sha256
raw_patch_ref
raw_diff_ref
raw_final_patch
raw_final_diff
audit-only patch artifact metadata
provider secret
FAIL_TO_PASS / PASS_TO_PASS 原文
```

允许公开：

```text
sha256
opaque ref
聚合计数
安全字段名
差异类别
相对 fixture 路径
```

## 8. Blocking difference 判定

以下任一情况必须阻塞 Stage 16F.5：

```text
run_episode projection 缺少 Stage 16F.3 必需绑定字段。
run_episode projection validator 未通过。
新旧入口工具集合或工具 schema 存在非预期差异。
public_environment_context_digest 存在非预期差异。
resolved_verifier_plan_digest 存在非预期差异。
test_feedback_policy 存在非预期差异。
final_patch_hygiene_report 的 cleaned patch 口径不一致。
非 verl route 被标记为 policy_loss_candidate。
公开 evidence 出现路径泄漏或 evaluator-only 标记。
run_task 成功但 run_episode 入口因缺少 final verifier factory、feedback facade 或 projection binding 失败。
```

以下差异可以记录为 expected difference，但必须解释：

```text
run_id 不同。
运行目录不同。
时间戳不同。
artifact 文件名或 artifact id 不同。
mock 模型行为导致 final.patch 内容不同。
旧入口缺少 TrainingView，而新入口有 TrainingView projection。
旧入口缺少 GenerationRecord，而新入口有 generation record projection。
```

## 9. 测试计划

新增测试建议：

```text
tests/unit/test_repo_harness_stage16f4_parity_report.py
tests/unit/test_repo_harness_stage16f4_parity_cli.py
tests/unit/test_repo_harness_stage16f4_projection_binding.py
```

测试覆盖：

```text
1. 旧 run_task 和新 run-episode-task 都运行成功，并生成 parity report。
2. 缺少新入口 projection binding 字段时，parity assert-complete 失败。
3. 篡改 compat_projection/final.patch 时，parity assert-complete 失败。
4. 非 verl route 被标记为 policy_loss_candidate 时，parity assert-complete 失败。
5. public_environment_context_digest 非预期差异会进入 blocking differences。
6. run_id、timestamp、artifact id 这类允许差异不会阻塞。
7. 公开 parity evidence 不泄漏本机绝对路径或 evaluator-only 标记。
8. 旧入口和新入口的 `final_patch_hygiene_report` 都必须投影为 public-safe 字段，不能把 raw patch audit 字段带入公开 parity evidence。
9. `public_feedback_case_count` 必须来自真实公开测试反馈事件；仅配置了 `public_only` 不能计数。
10. `patch_hygiene_case_count` 必须至少包含一个 `cleaned_patch_empty=false` 的样本；空 patch 不能单独满足覆盖要求。
```

前置回归：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16f3_run_episode_task_cli.py \
  tests/unit/test_repo_harness_stage16f3_run_episode_projection.py \
  tests/unit/test_repo_harness_stage16f3_provider_route_qualification.py \
  tests/unit/test_repo_harness_stage16f2_episode_execution_spec.py \
  tests/unit/test_repo_harness_stage16f2_real_episode_spec_consumption.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_repo_harness_stage16c_public_environment_context.py \
  tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py
```

实施后验收：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16f4_parity_report.py \
  tests/unit/test_repo_harness_stage16f4_parity_cli.py \
  tests/unit/test_repo_harness_stage16f4_projection_binding.py

PYTHONPATH=src PATH=.venv/bin:$PATH python -m compileall -q src

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness
import repo_harness.execution
loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
if loaded:
    raise SystemExit(f"unexpected heavy imports: {loaded}")
print("ordinary_import_ok", loaded)
PY

git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/46-stage-16f-4-execution-plan.md \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4 \
  src/repo_harness/evaluation \
  tests/unit/test_repo_harness_stage16f4_parity_report.py \
  tests/unit/test_repo_harness_stage16f4_parity_cli.py \
  tests/unit/test_repo_harness_stage16f4_projection_binding.py
```

## 10. 通过标准

Stage 16F.4 只有在以下条件全部满足时才能通过：

```text
stage16f4_acceptance_summary.status = passed
stage16f4_complete = true
stage16f3_input_status = passed
parity_task_count >= 3
run_task_completed_count >= 3
run_episode_task_completed_count >= 3
accepted_case_count >= 1
rejected_case_count >= 1
public_feedback_case_count >= 1
patch_hygiene_case_count >= 1
nonempty_cleaned_patch_case_count >= 1
public_feedback_observed_case_count >= 1
final_verifier_accepted_case_count >= 1
final_verifier_rejected_case_count >= 1
projection_validator_passed_count == run_episode_task_completed_count
blocking_difference_count = 0
public_path_leak_scan_passed = true
non_verl_policy_loss_candidate_count = 0
public_raw_patch_audit_field_count = 0
patch_hygiene_policy_difference_count = 0
resolved_verifier_plan_unexpected_difference_count = 0
tool_schema_unexpected_difference_count = 0
public_environment_unexpected_difference_count = 0
```

如果存在 blocking differences，Stage 16F.4 可以提交诊断结果，但必须写：

```text
status = failed
ready_for_stage16f5 = false
blocking_reasons = [...]
```

不能把“发现了差异”包装成通过。

## 11. 完成后的下一步

如果 Stage 16F.4 通过，可以进入：

```text
Stage 16F.5：旧 run_task 降级策略和内部迁移计划
```

如果 Stage 16F.4 不通过，应先修 blocking differences，再决定是否重跑 parity audit。只有当新入口能够证明与旧入口在关键 Harness 事实上一致，Stage 16F.5 的旧入口降级策略才可以继续推进。这里的 Stage 16F.5 与后续独立的 Stage 16.5 不是同一个阶段；Stage 16.5 指 20 到 30 题代表性诊断扩展，也应该在本阶段通过后才默认使用 `run_episode` 入口。
