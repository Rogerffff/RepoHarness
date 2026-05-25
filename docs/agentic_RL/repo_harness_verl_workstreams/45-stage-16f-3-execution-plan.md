# Stage 16F.3 执行计划：新增 run_episode 测评入口和兼容投影

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.3 的目标是新增实验性的测评入口，让测评任务可以通过 canonical `RepoHarnessRuntime.run_episode(real_episode)` 链路执行，而不是继续只能依赖旧的同步 `run_task(...)` 入口。

这一阶段要完成的是“入口可用”和“产物可审计”，不是立即删除旧入口。完成后应该能证明：

```text
现有 task definition + RunConfig
-> EpisodeExecutionSpecBuilder
-> RepoHarnessEpisodeRequest
-> RepoHarnessRuntime.run_episode(real_episode)
-> RepoHarnessEpisodeResult
-> 兼容旧评测工具的 run directory projection
```

这条链路必须复用 Stage 16F.2 已经实现的 `EpisodeExecutionSpec`，不能重新拼接 prompt、工具集合、公开环境、verifier plan 或反馈策略。

## 2. 前置条件

执行前必须确认：

```text
Stage 16F.0 status=passed
Stage 16F.1 status=passed
Stage 16F.2 status=passed
Stage 16F.2 commit 已存在
```

当前 Stage 16F.2 提交为：

```text
c6b6faca feat: add stage16f2 episode execution spec
```

必须读取并使用以下输入：

```text
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_run_task_run_episode_gap_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/stage16f1_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_2/stage16f2_acceptance_summary.json
```

如果 Stage 16F.2 没有通过，或者 `repo_harness.execution` 导入边界被破坏，Stage 16F.3 必须停止。

## 3. 非目标

Stage 16F.3 不做以下事情：

1. 不删除、废弃或重写旧 `run_task(...)`。
2. 不要求旧 `run_task(...)` 内部转调 `run_episode(...)`。
3. 不做 20 到 30 题代表性 harness 诊断；那属于独立的 Stage 16.5。
4. 不做完整 `run_task(...)` 与 `run_episode(...)` parity audit；那属于 Stage 16F.4。
5. 不运行远端 GPU 训练。
6. 不把外部 API provider 轨迹伪装成 formal online RL 样本。
7. 不放宽 Stage 16A / 16B / 16C / 16E 已经建立的工具、安全、公开环境和 patch hygiene 边界。
8. 不把 provider route 的 debug token ids 当成可进入 policy loss 的真实 token provenance。

如果执行中发现必须修改旧 `run_task(...)` 主流程才能继续，应停止并把问题记录到 Stage 16F.4 或 Stage 16F.5，而不是在 Stage 16F.3 里顺手重构。

## 4. 新增命令范围

### 4.1 必须新增的命令

必须新增实验性命令：

```text
repo-harness run-episode-task
```

建议参数：

```text
repo-harness run-episode-task TASK_PATH --config RUN_CONFIG \
  [--output-dir RUNS_DIR] \
  [--run-id RUN_ID] \
  [--gateway-route mock|replay|openai|deepseek] \
  [--assert-projection-complete]
```

第一版可以从 `RunConfig.model.provider` 推导 `gateway-route`。如果同时传入命令行 route 和配置 provider，必须一致；不一致时结构化拒绝，不能静默选择其中一个。

### 4.2 可以新增的轻量批量命令

可以新增实验性命令：

```text
repo-harness run-episode-batch
```

但第一版只能是顺序执行的薄包装：

```text
读取 RunConfig.tasks 或显式 task list
逐个调用 run-episode-task 的内部实现
写 batch manifest
不做并发调度
不做重试策略
不做采样策略
不做 Ray / rollout worker 调度
```

如果实现压力较大，可以只实现 `run-episode-task`，并在 Stage 16F.3 evidence 中明确：

```text
run_episode_batch_status = deferred_to_stage16_5_or_stage17
```

但不能把未实现的 batch 命令写成已通过。

## 5. 模块归属

建议新增中立测评执行模块：

```text
src/repo_harness/evaluation/episode_runner.py
src/repo_harness/evaluation/episode_projection.py
```

职责边界：

```text
episode_runner:
  读取 task definition 和 RunConfig。
  构造 workspace 和 resolved verifier plan。
  根据同一份 ResolvedVerifierPlan 构造 real_episode_final_verifier_factory。
  调用 EpisodeExecutionSpecBuilder。
  构造 RepoHarnessEpisodeRequest。
  构造 LLMGateway。
  调用 RepoHarnessRuntime.run_episode(real_episode)。

episode_projection:
  把 RepoHarnessEpisodeResult 和 run_episode 运行目录投影成旧评测工具可消费的 run directory 结构。
  写 compat_projection_manifest.json。
  校验 projection 与源 episode 的 digest 绑定。
```

导入边界：

```text
repo_harness.evaluation.episode_runner 可以 import repo_harness.execution 和 repo_harness.rl。
repo_harness.evaluation.episode_runner 不能 import repo_harness_verl。
repo_harness.evaluation.episode_runner 不能 eager import torch、ray、verl、tensordict。
repo_harness.execution 仍然不能 import evaluation.runner 或 evaluation.episode_runner。
repo_harness.rl.runtime 仍然不能反向依赖 evaluation.runner 或 evaluation.episode_runner。
```

## 5.1 Final verifier factory 绑定要求

`run-episode-task` 不能只把 `ResolvedVerifierPlan` 放进 `EpisodeExecutionSpec`，还必须为 `RepoHarnessRuntime` 显式提供 final verifier factory 或等价 `final_verifier_callable`。

原因是 `run_episode(real_episode)` 的 terminal verifier 阶段需要实际执行 final verifier。如果缺少 factory，当前 runtime 会结构化失败：

```text
real_episode requires final_verifier_callable or real_episode_final_verifier_factory
```

实现要求：

```text
final verifier factory 必须绑定同一份 ResolvedVerifierPlan。
final verifier factory 必须使用同一 workspace lease。
final verifier factory 必须写 verifier artifact 和 summary。
final verifier accepted / rejected 必须进入 RepoHarnessEpisodeResult。
reward summary 和 compat projection 必须能看到 final verifier outcome。
```

测试要求：

```text
构造一个 final verifier accepted 的 smoke。
构造一个 final verifier rejected 的 smoke。
确认 final verifier 确实运行，而不是被 mock summary 伪造。
确认 accepted / rejected 能进入 RepoHarnessEpisodeResult、reward 和 projection。
```

## 6. EpisodeExecutionSpec 使用要求

`run-episode-task` 必须通过 `EpisodeExecutionSpecBuilder` 构造 spec，并把同一份 spec 传给 `run_episode(real_episode)`。

必须写出公开安全的 spec artifact 或 spec report，至少包含：

```text
episode_execution_spec_schema_version
episode_execution_spec_sha256
task_definition_sha256
run_config_sha256
tool_registry_digest
tool_schema_snapshot_digest
public_environment_context_digest
resolved_verifier_plan_digest
initial_messages_digest
raw_prompt_digest
```

公开 spec artifact 不能包含：

```text
完整 ResolvedVerifierPlan
hidden test selector 原文
FAIL_TO_PASS / PASS_TO_PASS 原文
gold patch
test patch
runtime-private 真实路径
workspace 真实路径
run directory 真实路径
provider secret
```

如果 spec public payload 被 visibility gate 拒绝，`run-episode-task` 必须停止，不能退回到手工 raw prompt。

## 7. LLMGateway 构造边界

`run-episode-task` 必须明确构造 `LLMGateway`，不能让 `run_episode(...)` 自己猜模型。

第一版允许的 route：

```text
mock
replay
openai
deepseek
```

语义要求：

```text
mock:
  用 MockLLMGateway 或等价轻量 gateway。
  可用于 CLI smoke 和 projection smoke。
  默认 formal_online_rl_eligible=false。
  默认 policy_loss_candidate=false。

replay:
  使用现有 replay / fake model client，并通过 ModelClientLLMGateway 适配成 LLMGateway。
  必须保留 replay script provenance。
  默认 formal_online_rl_eligible=false。
  默认 policy_loss_candidate=false。

openai / deepseek:
  仅用于测评、诊断、SFT 候选或 preference 候选。
  如果缺少真实 output_logprobs、response token provenance 或 route=verl 事实，必须 invalid_for_online_rl=true。
```

不允许：

```text
把 mock / replay route 样本当成 formal online RL 样本。
把 provider route 样本改写成 route=verl。
把 provider debug token ids 当成真实 trainer token provenance。
把 missing output_logprobs 的 provider 样本放入 formal online RL policy loss。
```

## 8. RepoHarnessEpisodeRequest 构造要求

`run-episode-task` 构造的 request 必须绑定 spec：

```text
raw_prompt_source = episode_execution_spec
raw_prompt = []
episode_execution_spec_ref = rh://episode-execution-spec/<sha256>
episode_execution_spec_sha256 = spec.spec_payload_sha256
task_ref.task_id = spec.task_facts.task_id
task_ref.task_ref = spec.task_facts.task_ref
task_ref.repo_ref = spec.task_facts.repo_ref
task_ref.base_commit = spec.task_facts.base_commit
task_ref.source_archive_ref = spec.task_facts.source_archive_sha256
task_definition_sha256 = spec.task_facts.task_definition_sha256
run_config_sha256 = spec.run_config_facts.run_config_sha256
permission_mode = spec.run_config_facts.permission_mode
network_policy = spec.run_config_facts.network_policy
run_mode_hint = spec.run_config_facts.run_mode_hint
run_mode = training_fast 或 training_debug
llm_gateway_route = RunConfig.model.provider 映射后的 route
provider_route_policy_examples = [合法 ProviderRoutePolicy 对象] 或 runtime/projection metadata
allowed_tool_names = spec.allowed_tool_names
tool_registry_digest = spec.tool_facts.tool_registry_digest
resolved_verifier_plan_digest = spec.verifier_facts.resolved_verifier_plan_digest
test_feedback_policy = spec.feedback_facts.test_feedback_policy
feedback_tests_passed_policy = spec.feedback_facts.feedback_tests_passed_policy
budgets.max_turns = spec.budget_facts.max_turns
budgets.max_tool_calls = spec.budget_facts.max_tool_calls
budgets.max_test_runs = spec.budget_facts.max_test_runs
budgets.max_tool_observation_tokens = spec.budget_facts.max_tool_output_chars
```

诊断语义不能通过新增 `RepoHarnessEpisodeRequest.run_mode` 枚举值表达。第一版应使用现有 `training_fast` 或 `training_debug`，并把 `run_episode_task_diagnostic_mode`、`diagnostic_only_reason`、provider route policy 等写入 runtime metadata、projection manifest 或 evidence 报告。

如果需要写入 `provider_route_policy_examples`，必须构造合法对象，不能直接写入 `spec.provider_route_policy` 字符串。示例：

```text
ProviderRoutePolicy(
  route = llm_gateway_route,
  invalid_for_online_rl = true,
  allowed_uses = ["evaluation", "teacher_data_generation", "sft_export", "preference_data"]
)
```

如果 `RunConfig.model.provider=fake`，第一版必须显式映射为 `llm_gateway_route=mock`，或者结构化拒绝并说明 `fake_provider_route_requires_mock_mapping`。不能把 `fake` 直接写入 `GatewayRoute`。

如果 request 与 spec 绑定不一致，必须在模型调用前结构化失败，且 gateway request count 必须为零。

## 9. 兼容 run directory projection

Stage 16F.3 必须新增 `run_episode` 到旧评测目录的兼容投影。

建议写入：

```text
compat_projection_manifest.json
compat_projection_status.json
task_projection.json
run_config_facts.json 或 run_config_projection.json
episode_execution_spec_report.json
transcript.jsonl
events.jsonl
artifacts.json
metrics.json
reward.json 或 reward_summary.json
verifier.json 或 verifier_summary.json
final.patch
final.diff
final_patch_hygiene_report.json
public_environment_context.json
public_environment_prompt_block.txt
tool_schema_snapshot.json
training_view_projection.json 或 not_available reason
generation_records_projection.json 或 not_available reason
provider_failure_facts.json 或 not_applicable reason
```

`task_projection.json` 不是原始 `task.yaml` 的复制。它只能包含公开安全字段，例如：

```text
task_id
task_version
dataset_name
issue_statement
expected_files
task_definition_sha256
visibility_policy_summary
source_evidence_ref 或 source_sha256
```

原始 task YAML 可能包含 hidden verifier selector、`FAIL_TO_PASS`、`PASS_TO_PASS`、gold patch、test patch 或 evaluator-only 字段，因此只能保存为 runtime-private / evaluator-only artifact，公开 projection 最多写入 opaque ref 和 sha256。

`events.jsonl`、`transcript.jsonl`、`artifacts.json`、`metrics.json` 等也必须是 sanitized projection，不能直接复制 `run_episode` 原始运行目录文件。如果原始事件或 artifact manifest 中包含 provider raw request / raw response、workspace 真实路径、run directory 真实路径、runtime-private 真实路径或 raw command artifact 路径，公开 projection 必须改写为 opaque ref、sha256、聚合计数或脱敏摘要。

其中 `final.patch`、`final.diff` 和 official prediction 相关文件必须使用 Stage 16E cleaned patch hygiene 口径。raw patch / raw diff 只能作为 runtime-private artifact 存在，不能进入公开 projection。

## 10. Projection 绑定字段

`compat_projection_manifest.json` 必须包含可以机器校验的绑定字段：

```text
compat_projection_schema_version
projection_created_from_run_episode = true
projection_source_episode_id
projection_source_run_id
projection_source_result_digest
projection_source_training_view_digest
projection_source_generation_records_digest
episode_execution_spec_schema_version
episode_execution_spec_sha256
task_definition_sha256
run_config_sha256
resolved_verifier_plan_digest
test_feedback_policy
feedback_tests_passed_policy
permission_mode
network_policy
run_mode_hint
allowed_tool_names_digest
budget_facts_digest
provider_route_policy
llm_gateway_route
tool_registry_digest
tool_schema_snapshot_digest
public_environment_context_digest
initial_messages_digest
raw_prompt_digest
```

校验要求：

```text
projection_source_run_id 必须等于 source episode 的 run_id。
episode_execution_spec_sha256 必须等于 source spec 的 spec_payload_sha256。
task_definition_sha256 和 run_config_sha256 必须等于 source spec 中的值。
resolved_verifier_plan_digest、feedback policy、permission、network、budget 和 provider route 字段必须等于 source spec 或 request 中的值。
allowed_tool_names_digest 必须由 source spec 的 allowed_tool_names 稳定计算得出。
tool_registry_digest 和 public_environment_context_digest 必须等于 source spec 中的值。
如果 TrainingView 或 generation_records 不存在，必须写明 not_available reason，不能伪造 digest。
```

如果 projection 绑定字段缺失或不一致，该 projection 只能标记为 diagnostic，不能作为 Stage 17 数据冻结、SFT target、preference pair、reward evidence 或 official prediction 的可信来源。

## 11. 公开和私有证据分层

公开 projection 和公开 evidence 不能泄漏：

```text
本机绝对路径
workspace 真实路径
run directory 真实路径
runtime_private 真实路径
diagnostic session root
shared dependency environment 真实路径
provider secret
hidden verifier selector
gold patch
test patch
FAIL_TO_PASS / PASS_TO_PASS 原文
```

允许公开：

```text
sha256
聚合计数
脱敏摘要
rh://... opaque ref
runtime-private:<artifact-kind>:<sha256> opaque ref
```

注意：公开 JSON、JSONL、Markdown、log、shell script、YAML 和 patch projection 都必须经过路径泄漏扫描。

## 12. 非 verl route 样本资格

`mock`、`replay`、`openai`、`deepseek` 等非 `route=verl` 产生的 episode 必须写明训练资格：

```text
route = mock | replay | openai | deepseek
invalid_for_online_rl = true
formal_online_rl_eligible = false
policy_loss_candidate = false
diagnostic_or_sft_candidate = true 或 false
provider_response_logprobs_available = false 或 true
token_provenance = provider_text_retokenized_debug_only 或等价说明
```

`mock` 和 `replay` 在 Stage 16F.3 只能作为 CLI smoke、projection smoke、评测或诊断来源。它们不能因为本地 smoke 产生了 token ids 或 logprobs 就被标记为 policy loss 候选。

只有当后续阶段有 `route=verl`、真实 rollout token provenance、response mask、response span、generation record 和 log probability 绑定时，样本才可能进入正式 online RL。Stage 16F.3 不能改变这个边界。

## 13. 与旧 run_task 的关系

Stage 16F.3 完成后：

```text
run_task(...) 仍然存在。
run_task(...) 仍然服务历史 acceptance、旧 export 和旧报告。
run-episode-task 是新测评实验默认入口候选。
```

本阶段可以在旧 `run_task(...)` 文档或 evidence 中增加 legacy 说明，但不要求修改旧入口行为。

Stage 16F.4 才做正式 parity audit，比较旧 `run_task(...)` 和新 `run-episode-task` 的模型可见上下文、工具面、verifier、reward 和 patch hygiene 是否一致。

## 14. 测试计划

必须新增或更新测试，至少覆盖：

```text
tests/unit/test_repo_harness_stage16f3_run_episode_task_cli.py
tests/unit/test_repo_harness_stage16f3_run_episode_projection.py
tests/unit/test_repo_harness_stage16f3_provider_route_qualification.py
```

建议覆盖场景：

1. `run-episode-task` 可以读取现有 task YAML 和 RunConfig。
2. `run-episode-task` 会构造 `EpisodeExecutionSpec`，并把 spec 传入 `run_episode(real_episode)`。
3. request/spec 绑定不一致时，在 gateway 调用前失败。
4. replay 或 mock route 能生成兼容 projection。
5. final verifier accepted / rejected 两条路径都能运行，并投影到 result、reward 和 projection。
6. projection manifest 中的 `episode_execution_spec_sha256`、`task_definition_sha256`、`run_config_sha256`、`tool_registry_digest` 与 source spec 一致。
7. projection 缺少绑定字段时，inspector 或 helper 拒绝把它标记为可信。
8. mock / replay / provider route 样本默认 `invalid_for_online_rl=true`，不能进入 formal online RL 候选。
9. projection 中的 `final.patch` 和 `final.diff` 使用 cleaned patch hygiene 口径。
10. public evidence leak scan 能拒绝本机路径、runtime-private 真实路径、hidden selector、gold patch、test patch。
11. `repo_harness.execution` 仍然不 import `repo_harness_verl` 或重依赖。

## 15. 建议验收命令

Stage 16F.3 聚焦测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16f3_run_episode_task_cli.py \
  tests/unit/test_repo_harness_stage16f3_run_episode_projection.py \
  tests/unit/test_repo_harness_stage16f3_provider_route_qualification.py
```

Stage 16F.2 和关键前置回归：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16f2_episode_execution_spec.py \
  tests/unit/test_repo_harness_stage16f2_real_episode_spec_consumption.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_repo_harness_stage16c_public_environment_context.py \
  tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py \
  tests/unit/test_pre_verl_swebench_official_inputs.py
```

编译检查：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
```

普通导入边界：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness
import repo_harness.execution
loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
if loaded:
    raise SystemExit(f"unexpected heavy imports: {loaded}")
print("ordinary_import_ok", loaded)
PY
```

CLI smoke：

```bash
PATH=.venv/bin:$PATH python -m repo_harness.cli.main run-episode-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/stage16f3_run_episode_task_mock.yaml \
  --output-dir runs/stage16f3-local-smoke \
  --run-id stage16f3-mock-smoke \
  --assert-projection-complete
```

实际执行时如果 fixture 路径不存在，必须新增最小 fixture，而不是复用包含隐藏 oracle 的旧 fixture。

## 16. Evidence 文件

本阶段建议新增：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_cli_smoke_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_projection_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_provider_route_qualification_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_visibility_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_3/stage16f3_test_report.json
```

`stage16f3_acceptance_summary.json` 至少包含：

```text
schema_version
stage = 16F.3
status
stage16f3_complete
stage16f2_input_status
run_episode_task_cli_added
run_episode_batch_cli_status
episode_execution_spec_used_by_cli
run_episode_real_episode_path_executed
final_verifier_factory_bound
final_verifier_accepted_path_verified
final_verifier_rejected_path_verified
compat_projection_written
compat_projection_binding_verified
non_verl_route_online_rl_rejected
public_path_leak_scan_passed
ready_for_stage16f4
blocking_reasons
```

## 17. 通过标准

Stage 16F.3 可以通过的最低条件：

1. `run-episode-task` 命令存在，并能在本地 mock 或 replay 模式完成一个真实 `run_episode(real_episode)`。
2. 该命令必须使用 `EpisodeExecutionSpecBuilder`，不能手工重新拼 prompt 和工具列表。
3. `RepoHarnessRuntime.run_episode(...)` 必须收到同一份 spec。
4. `run_episode(real_episode)` 必须通过显式 final verifier factory 完成 final verifier accepted / rejected 两条路径。
5. final verifier outcome 必须进入 `RepoHarnessEpisodeResult`、reward summary 和 compat projection。
6. 兼容 projection 必须写出，并带有完整绑定字段。
7. projection 绑定字段必须能机器校验。
8. projection 不能泄漏本机路径、runtime-private 真实路径、hidden selector、gold patch 或 test patch。
9. mock / replay / provider route 样本必须默认不能进入 formal online RL。
10. Stage 16F.2 聚焦测试仍然通过。
11. Stage 16A / 16B / 16C / 16E 的关键工具、安全、公开环境和 patch hygiene 回归仍然通过。
12. 没有新增 `repo_harness.execution` 到 `repo_harness_verl` 或重依赖的导入。

## 18. 进入 Stage 16F.4 的条件

只有 Stage 16F.3 通过后，才能进入 Stage 16F.4。

Stage 16F.4 的重点将是：

```text
选择 3 到 5 个小任务。
分别用旧 run_task(...) 和新 run-episode-task 执行。
比较 initial_messages、工具集合、public_environment、verifier、reward、patch hygiene 和训练资格。
生成 run_task_run_episode_parity_report.json。
修复非预期差异。
```

Stage 16F.3 不要求证明完全 parity，但必须让 Stage 16F.4 有可运行的新测评入口和可机器校验的 projection。
