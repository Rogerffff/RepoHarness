# Pre-verl AgentLoop 正式评测执行计划

## 目标

本计划用于接替上一轮 `single_shot_patch_no_tools` 诊断性结果，执行一轮真正经过 RepoHarness 核心 AgentLoop 的 pre-verl 智能体评测。

这轮评测的目标不是证明 RepoHarness 是官方 SWE-Bench Lite 排行榜复现，也不是训练模型，而是生成一套在接入 `verl` 之前更可信的工程证据：

- 23 个已物化的 SWE-Bench Lite development instances 可以通过统一任务定义进入 RepoHarness 运行链路。
- 真实 provider 调用必须发生在 RepoHarness `AgentLoop` 内，模型必须通过工具读取、搜索、编辑和查看差异。
- final verifier 必须由 RepoHarness 核心评测路径执行，隐藏测试补丁、gold patch、隐藏选择器和 verifier 原始输出不能进入模型可见内容。
- 每个失败样本都要能区分是模型修错、工具或上下文策略不足、预算不足、环境或 verifier 问题，还是 provider 额度、限流、鉴权或传输失败。
- 上一轮无工具单轮结果只作为诊断参考，不作为 baseline，不参与正式通过率叙事。

## 当前事实核对

当前仓库已经实现了真正的通用运行链路：

- `repo-harness run-task` 会加载 `TaskDefinition`，创建 source checkout、setup workspace、agent workspace、调用 `AgentLoop`、捕获 final patch，并执行 strict final verifier。
- `AgentLoop` 会把 scaffold、allowed tools、tool schema、context revision、prepared messages、provider request / response 引用、tool use / tool result 和最终 verifier 证据写入 trajectory。
- DeepSeek 和 OpenAI provider 适配器已经支持 OpenAI-compatible tool calling；当 allowed tools 非空时，请求体会包含 `tools`，`tool_choice` 为 `auto`。

但当前 pre-verl 23 题 pilot 的命令 `run-pre-verl-agent-evaluation-pilot` 不满足正式评测要求：

- 它在 `pre_verl_evaluation.py` 里硬编码 `scaffold_id=single_shot_patch_no_tools`。
- 它直接构造 prompt、调用 DeepSeek provider、解析 unified diff，然后单独执行补丁和 verifier 逻辑。
- 它没有经过通用 `AgentLoop` 的工具调用、context manager、permission system、tool schema snapshot 和 run metadata 链路。

因此，正式评测必须废弃这条 pilot 路径。可以保留历史产物作为诊断参考，但后续 baseline、scaffold comparison、budget comparison 和失败归因都不能再使用它。

实施上应直接移除 `repo-harness run-pre-verl-agent-evaluation-pilot` 的 CLI 入口，包括 `main.py` 中的 subparser、命令分发分支和面向用户的 help 文本。历史函数如果还需要保留给旧 evidence 读取或测试，只能作为内部历史兼容代码存在，不能再通过 `repo-harness` 命令行直接执行。新增测试必须证明：

- `repo-harness --help` 不再展示 `run-pre-verl-agent-evaluation-pilot`。
- 直接执行 `repo-harness run-pre-verl-agent-evaluation-pilot ...` 会失败。
- 正式 pre-verl 聚合器拒绝 `scaffold_id=single_shot_patch_no_tools`、`baseline_source` 缺失、没有 `run_task_run_dir` 的结果记录。
- 正式 pre-verl 聚合器同时拒绝旧 pilot command name、旧 pilot stage、旧 pilot report schema，例如 `run-pre-verl-agent-evaluation-pilot`、`pre_verl_agent_evaluation_pilot` 和 `single_provider_call_then_strict_final_verifier`。
- 每条正式结果的 command lineage 必须包含对应的 `repo-harness run-task` argv、run dir、`run_metadata.json`、tool schema snapshot 和 AgentLoop events。
- 旧 pilot 产物只能进入 `diagnostic_only_historical_reference` 分区，不能进入 baseline 分母、accepted rate、training export 或 claim gate。

## 输入兼容性结论

当前 materialized SWE-Bench Lite development task set 还不能被 `repo-harness run-task` 直接消费。

具体原因：

- `runs/pre-verl-eval-stage1-materialized-task-set-20260507T040000Z/task_definitions/*.json` 的 schema 是 `repo_harness_pre_verl_task_definition_v0`。
- `repo-harness run-task` 期望的是 `repo_harness_task_definition_v*`，也就是 `TaskDefinition`，需要包含 `id`、`task_version`、`dataset_name`、`repo_source_spec`、`issue`、`test_command`、`timeouts`、`environment`、`visibility` 等字段。
- 现有 pre-verl task definition 是审计清单，主要绑定 adapter-visible input、materialization entry、verifier plan 和 evidence refs，不是可运行任务定义。
- SWE-Bench Lite development final verifier 需要在独立 verification workspace 中应用模型 final patch，再应用 evaluator-only hidden test patch，然后执行冻结 selector。通用 `PytestVerifier.run_final` 不会自动应用 hidden test patch；这部分必须进入核心 final verifier adapter，而不能放在外部脚本里手写。

所以正式执行前必须补一个“TaskDefinition 生成和 run-task 兼容性门”：

1. 从 materialization report 和 adapter-visible input 生成 `run-task` 可消费的 `TaskDefinition` 文件。
2. `TaskDefinition.metadata` 必须绑定 pre-verl SWE-Bench development runtime plan 或等价 evaluator-only verifier adapter 输入。
3. `repo-harness run-task` 必须在核心 final verifier 路径中识别该 metadata，并调用 RepoHarness 内部的 SWE-Bench-like strict replay verifier adapter。
4. 外部脚本只负责批量调度 `repo-harness run-task`，不得自己应用 hidden test patch，不得自己调用 provider，不得自己解析 provider diff。

如果第 3 点当前代码不支持，必须先实现为核心链路能力，再跑正式评测。

这个兼容性门必须有机器检查命令，不能只靠人工确认。建议新增：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-task-definitions \
  PRE_VERL_AGENTLOOP_TASK_DEFINITION_MANIFEST \
  --assert-run-task-compatible \
  --assert-evaluator-only-hidden-inputs \
  --assert-no-hidden-material-in-model-visible-fields
```

该 inspect 至少检查：

- 23 个 development instances 都生成了 `repo_harness_task_definition_v*` 格式的 `TaskDefinition`。
- 每个 `TaskDefinition` 都能被 `repo-harness run-task` 解析，不需要外部脚本补字段。
- `hidden_test_patch_ref`、fail-to-pass selectors、pass-to-pass selectors、gold patch、official outcome、final verifier raw output 只存在 evaluator-only metadata 或 verifier adapter input 中。
- adapter-visible issue、prepared messages、context seed、tool results 和 transcript 不包含隐藏测试补丁、隐藏 selector、gold patch、官方结果或 reward。
- `TaskDefinition.metadata.pre_verl_agentloop_baseline_source` 必须等于 `repo_harness_agentloop_run_task`。
- `TaskDefinition.metadata.swe_bench_like_final_only` 和 `TaskDefinition.metadata.final_only` 必须为 true。tags 可以冗余记录 `swe_bench_like_final_only` 和 `final_only`，但不能作为 metadata 缺失时的替代触发条件。
- inspect 必须用正式 scaffold、run config 和 `ContextBuilder` 渲染一份 prepared messages，并断言模型可见的 `test_command is None`、`test_command_visibility == redacted_final_only`。
- prepared messages、issue、context metadata、tool results 和 transcript 扫描必须证明没有 hidden selector、hidden test patch、gold patch、official outcome、accepted、reward 或 final verifier raw output。

## Final Verifier Adapter 语义

正式 pre-verl SWE-Bench Lite development verifier 采用以下顺序：

1. 从冻结 source tree 创建独立 verification workspace。
2. 先应用模型最终补丁，也就是 `final.patch`。
3. 再应用 evaluator-only hidden test patch。
4. 执行冻结的 fail-to-pass 和 pass-to-pass selector。
5. 根据 strict final verifier 结果写出 accepted、rejected、timeout 或 environment failure。

选择这个顺序的原因是：如果模型自己修改了测试文件，甚至无意覆盖了隐藏测试补丁要修改的区域，后应用 hidden test patch 可以把这种冲突显式记录为模型补丁和隐藏测试补丁冲突，而不是提前把隐藏测试补丁放进 workspace 后让模型补丁覆盖它。

归因规则：

- 模型补丁无法应用到冻结源码：`failure_owner=model_patch_format_or_path`，`failure_category=model_patch_apply_failed`。
- 模型补丁可应用，但 hidden test patch 在模型补丁之后无法应用：如果同一 hidden test patch 已经在 clean frozen source 上通过 materialization 自检，则记为 `failure_owner=model_patch_quality`，`failure_category=hidden_test_patch_conflict_after_candidate_patch`。
- hidden test patch 在 clean frozen source 上也无法应用：该任务不能进入正式 runnable 分母，记为 `failure_owner=harness_or_environment`。
- 模型补丁和 hidden test patch 都可应用，但 final verifier 拒绝：`failure_owner=model_patch_quality`，`failure_category=model_patch_rejected_by_final_verifier`。

必须新增 final verifier adapter 自检：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-final-verifier-adapter \
  PRE_VERL_FINAL_VERIFIER_ADAPTER_REPORT \
  --assert-model-patch-before-hidden-test-patch \
  --assert-clean-source-hidden-patch-self-check \
  --assert-boundary-artifacts-complete
```

该报告必须绑定 `final.patch`、`final.diff`、`verifier.json`、`events.jsonl`、`run_metadata.json`、verification workspace id、verifier adapter id、hidden patch apply result 和 selector refs。模型可见 workspace 和 agent trajectory 不得包含 hidden test patch 内容。

## 核心 Harness 修复方案

这里需要修的是 RepoHarness 核心 `run-task` final verifier adapter，不是在外部测评脚本中手动实现 verifier。

当前 `run-task` 已经有 SWE-Bench-like 特殊路径：`evaluation/runner.py` 会通过 `load_swebench_like_runtime_plan()` 识别 `task.metadata.v3_adapter == "swebench_like_fixed"`，然后调用 `run_swebench_like_final_verifier()`。这条历史 V3 路径的 verifier workspace 来自已经应用过 evaluator-only verifier patch 的 `baseline_workspace_ref`，然后再应用模型 `final.patch`。这个顺序可以保留给 V3 历史 acceptance 兼容，但不能作为正式 pre-verl SWE-Bench Lite development baseline 的语义。

正式 pre-verl 的实现应采用版本化修复，避免破坏旧 V3 evidence。实现时固定使用一种 metadata，不保留替代写法，避免和 V3 loader 混在一起。

1. 新增 pre-verl 专用 runtime plan metadata：

```json
{
  "pre_verl_adapter": "swebench_lite_dev_agentloop_v0",
  "pre_verl_swebench_dev_manifest_path": "...",
  "pre_verl_agentloop_mode": "formal_baseline",
  "pre_verl_agentloop_baseline_source": "repo_harness_agentloop_run_task"
}
```

2. `repo-harness run-task` 必须识别这个新 metadata，并进入新的核心 adapter，例如：

```text
load_pre_verl_swebench_dev_runtime_plan(task)
run_pre_verl_swebench_dev_final_verifier(...)
```

外部脚本只能生成 `TaskDefinition` 和 `RunConfig`，然后调用 `repo-harness run-task`。外部脚本不得调用 `git apply`、不得运行 pytest selector、不得根据测试结果写 accepted。

`evaluation/runner.py` 的 dispatch 规则必须写成硬逻辑：

```text
pre_verl_plan = load_pre_verl_swebench_dev_runtime_plan(task)
legacy_v3_plan = load_swebench_like_runtime_plan(task)
formal_pre_verl_mode = is_formal_pre_verl_agentloop_run(task, config)

if pre_verl_plan and legacy_v3_plan:
  raise ConfigError("pre-verl adapter metadata conflicts with legacy V3 adapter")

if formal_pre_verl_mode and legacy_v3_plan and not pre_verl_plan:
  raise ConfigError("formal pre-verl baseline cannot use v3_adapter=swebench_like_fixed")

if pre_verl_plan:
  baseline_verifiers = [build_pre_verl_baseline_verifier(pre_verl_plan)]
  baseline_status = "valid"
  use run_pre_verl_swebench_dev_final_verifier for final verifier
elif legacy_v3_plan:
  use existing run_swebench_like_final_verifier for historical V3 compatibility only
else:
  use ordinary PytestVerifier.run_final
```

同样的冲突规则必须用于 baseline verifier、final verifier、run metadata 和 aggregation inspect，不能只在 final verifier 分支检查。当前 `evaluation/runner.py` 的 baseline 阶段只认识旧 `swebench_like_runtime_plan`，所以实现新 adapter 时必须同步接入 baseline 分支：如果 `pre_verl_plan` 存在，baseline 只能使用 `build_pre_verl_baseline_verifier(pre_verl_plan)`，不能落回普通 `PytestVerifier.run_baseline()`。

`formal_pre_verl_mode` 必须由 `repo-harness run-task` 自己根据固定的 `TaskDefinition.metadata` 字段判定，不能只靠外部聚合器事后判断，也不能由 `RunConfig` 或 tags 替代触发。实现时必须同时要求以下四个 metadata 字段：

```text
TaskDefinition.metadata.pre_verl_adapter = "swebench_lite_dev_agentloop_v0"
TaskDefinition.metadata.pre_verl_swebench_dev_manifest_path = "..."
TaskDefinition.metadata.pre_verl_agentloop_mode = "formal_baseline"
TaskDefinition.metadata.pre_verl_agentloop_baseline_source = "repo_harness_agentloop_run_task"
```

判定规则：

```text
formal_pre_verl_mode = (
  task.metadata.pre_verl_adapter == "swebench_lite_dev_agentloop_v0"
  and task.metadata.pre_verl_swebench_dev_manifest_path is present
  and task.metadata.pre_verl_agentloop_mode == "formal_baseline"
  and task.metadata.pre_verl_agentloop_baseline_source == "repo_harness_agentloop_run_task"
)
```

如果任何一个字段缺失或值不匹配，`run-task` 不得进入正式 pre-verl adapter；如果同一 `TaskDefinition` 同时包含旧 `v3_adapter=swebench_like_fixed`，必须直接失败。`RunConfig` 可以记录 provider、budget、workspace、context 等普通配置，但不能作为进入 pre-verl adapter 的替代触发来源。正式外部脚本必须生成这些 metadata 字段；聚合器只能复核，不能成为唯一防线。

3. 新 runtime plan 必须显式绑定 clean frozen source，而不是预先应用 hidden test patch 的 workspace。manifest 至少包含：

```text
clean_source_checkout_ref
source_tree_sha256
hidden_test_patch_ref
fail_to_pass_selectors_ref
pass_to_pass_selectors_ref
environment_spec_ref
hidden_patch_clean_source_self_check_ref
gold_patch_replay_ref 或明确豁免
```

禁止把 `baseline_workspace_ref` 作为正式 pre-verl final verification workspace 的起点。正式 pre-verl adapter 的 workspace 起点必须是 `clean_source_checkout_ref` 或从同一 clean source materialization 重新创建的 source checkout。历史 `baseline_workspace_ref` 即使经过 inspect 证明干净，也只能作为历史 V3 兼容字段，不作为正式 pre-verl final verification 起点，避免语义回退。

4. 新 final verifier adapter 的内部顺序必须是：

```text
copy clean_source_checkout -> verification_workspace
apply model final.patch
if model patch apply failed:
  write final_verifier_boundary.json
  final_verifier_status = not_executed
  failure_category = model_patch_apply_failed
  failure_owner = model_patch_format_or_path
else:
  apply evaluator-only hidden_test.patch
  if hidden patch apply failed:
    write final_verifier_boundary.json
    if hidden_patch_clean_source_self_check_ref.status == passed:
      failure_category = hidden_test_patch_conflict_after_candidate_patch
      failure_owner = model_patch_quality
    else:
      failure_category = hidden_test_patch_apply_failed_on_clean_source
      failure_owner = harness_or_environment
  else:
    run fail-to-pass selectors
    run pass-to-pass selectors
    write final_verifier_boundary.json
    accepted = all fail-to-pass pass and all pass-to-pass pass
```

即使模型没有生成补丁、补丁为空、模型补丁无法应用、verification workspace 创建失败、hidden patch 冲突、selector timeout 或 selector rejected，也必须写出 `final_verifier_boundary.json`。这个 boundary 是证明该样本确实进入核心 adapter 的最低证据，不能只在 accepted 或 selector 已执行时生成。

5. baseline 自检和 final verification 要分开：

- baseline 自检可以在另一个 audit-only workspace 中对 clean source 应用 hidden test patch，并证明隐藏补丁本身可应用。
- final verification 不能从这个已经打过 hidden test patch 的 workspace 复制；它必须重新从 clean source 创建。
- baseline 自检产物只能作为 evaluator-only evidence，不进入 model-visible transcript、tool result、trainable export 或 public-safe demo。

6. `final_verifier_boundary.json` 必须新增或确认这些字段：

```json
{
  "verifier_adapter_id": "pre_verl_swebench_lite_dev_final_verifier_v0",
  "verification_workspace_source": "clean_frozen_source",
  "workspace_creation_input_ref": "...",
  "clean_source_tree_sha256": "...",
  "after_model_patch_tree_sha256": "...",
  "after_hidden_test_patch_tree_sha256": "...",
  "patch_application_order": [
    "model_final_patch",
    "evaluator_only_hidden_test_patch"
  ],
  "model_final_patch_apply_result_ref": "...",
  "hidden_test_patch_apply_result_ref": "...",
  "hidden_patch_clean_source_self_check_ref": "...",
  "fail_to_pass_result_ref": "...",
  "pass_to_pass_result_ref": "...",
  "accepted_authority": "strict_final_verifier_only"
}
```

7. 对应 inspect 必须做命令级顺序检查，而不只是检查字段存在：

- command log 中 `model_final_patch_apply` 必须出现在 `hidden_test_patch_apply` 之前。
- `hidden_test_patch_apply` 必须出现在 fail-to-pass / pass-to-pass verifier command 之前。
- boundary 必须分阶段绑定 `clean_source_tree_sha256`、`after_model_patch_tree_sha256` 和 `after_hidden_test_patch_tree_sha256`。inspect 必须证明 `workspace_creation_input_ref` 指向 clean source checkout，而不是已预打 hidden patch 的 workspace。
- 如果 command log 中出现 `hidden_test_patch_apply` 早于 `model_final_patch_apply`，inspect 必须失败。
- 如果正式 pre-verl `TaskDefinition`、run result 或 aggregation record 使用 `v3_adapter=swebench_like_fixed` 且没有新 pre-verl adapter id，inspect 必须硬失败，不能降级后继续留在正式分母。只有历史 V3 evidence 可以进入 `diagnostic_only_historical_reference` 分区。

8. 必须新增负例测试：

- 构造一个旧 V3-style plan：`baseline_workspace_ref` 已经包含 hidden test patch，再应用模型补丁。正式 pre-verl inspect 必须拒绝。
- 构造 command log 顺序为 hidden patch 先、模型补丁后的 boundary，inspect 必须失败。
- 构造 hidden test patch 内容出现在 prepared messages 或 transcript 的样本，inspect 必须失败。
- 构造 final verifier boundary 缺少 `patch_application_order` 或 workspace source 的样本，inspect 必须失败。
- 构造一个合法的 clean-source -> model patch -> hidden patch -> selector 的最小 fixture，inspect 必须通过。

9. 回归要求：

- V2 / V3 / V4 既有 acceptance inspect 不得被这个新 adapter 破坏。
- 历史 V3 `swebench_like_fixed` evidence 可以继续按原口径复核，但不能被 pre-verl 正式 baseline 使用。
- V3 adapter 代码中必须明确标记为 legacy 或 `historical_compatibility_only`。它可以保留给 `inspect-v3-acceptance`、V4 / V5 历史证据复核和旧 artifact replay，但正式 pre-verl AgentLoop baseline 必须硬拒绝 `v3_adapter=swebench_like_fixed`。
- 新 pre-verl 专用 adapter 使用 `pre_verl_adapter=swebench_lite_dev_agentloop_v0`，并固定执行 clean source、模型补丁、隐藏测试补丁、冻结 selector 的顺序。
- 只有当 pre-verl、V4、V5 所有回归证据都不再需要执行旧 V3 runtime 后，才能考虑把 V3 adapter 从运行路径删除，只保留历史 artifact inspect。
- 文档、result summary 和 claim gate 必须把旧 V3/V5 evidence、旧 pilot evidence 和新 pre-verl AgentLoop baseline evidence 分开列出。

## 外部评测脚本边界

新增外部脚本建议放在：

```text
scripts/pre_verl/run_agentloop_evaluation.py
```

这个脚本只做调度和证据整理，不能重写智能体循环。允许做的事情：

- 读取显式输入路径：task set manifest、SWE-Bench development materialization report、run config template、任务选择清单。
- 为每个任务生成 `TaskDefinition` 和 `RunConfig` 文件。
- 逐个调用：

```bash
PATH=.venv/bin:$PATH repo-harness run-task TASK_DEFINITION --config RUN_CONFIG --output-dir RUN_ROOT --run-id RUN_ID
```

- 调用既有 inspect 命令，例如 `inspect-run`、`inspect-tool-contract`、后续新增的 pre-verl aggregation inspect。
- 汇总每个 run 的 `run_metadata.json`、`metrics.json`、`final.patch`、`final.diff`、`events.jsonl`、`transcript.jsonl`、`artifacts/` 引用。
- 写出 run matrix manifest、configuration manifest、failure taxonomy、result summary、command log 和 sha256 refs。

明确禁止：

- 直接调用 DeepSeek 或 OpenAI provider。
- 自己拼接 prompt。
- 自己解析模型返回的 diff。
- 自己应用 final patch 或 hidden test patch。
- 自己运行 final verifier 并把结果写成 accepted。
- 把 provider raw request、provider raw response、credential、hidden test patch、gold patch、隐藏 selector、final verifier raw output 放入模型可见内容或训练导出。

## 正式主配置

第一轮正式 AgentLoop baseline 使用 `patch_focused_react`。

原因：

- 它允许模型真实读取、搜索和编辑源码。
- 它不允许 `bash` 和 `create_file`，工具面比 `simple_react` 和 `planner_coder_verifier` 更保守。
- 在 `test_feedback_policy=disabled` 后，`run_tests` 会被移除，实际工具为：

```text
list_files
read_file
grep
edit_file
git_diff
```

建议主配置：

```yaml
model:
  provider: deepseek
  model_id: deepseek-v4-pro
  temperature: 0.0
  max_output_tokens: 4096
  retry_policy: none
  credential_policy: local_secret_file_redacted
  provider_request_logging: redact_secrets
  provider_specific_options:
    allow_local_secret_file: true
    thinking:
      type: disabled

runtime:
  scaffold_id: patch_focused_react
  permission_mode: auto
  test_feedback_policy: disabled
  feedback_tests_passed_policy: require_model_final
  max_turns: 24
  max_tool_calls: 96
  max_test_runs: 0
  task_timeout_sec: 1200
  seed: 42

workspace:
  keep_workspace: true
  default_command_timeout_sec: 90
  network_policy: deny_agent_run
  max_tool_output_chars: 12000

context_management:
  max_context_tokens: 120000
  tool_result_aggregate_budget_chars: 40000
  keep_recent_turns: 6
  keep_recent_test_results: 0
  summarize_old_test_outputs: true

evaluation:
  final_verifier_mode: strict_patch_replay
  rerun_final_verifier: true
```

DeepSeek V4 Flash 只用于链路烟测。正式 baseline 使用 DeepSeek V4 Pro。

`allowed_tools_after_resolution` 不应作为手写主配置字段。正式配置只写 `scaffold_id`、`test_feedback_policy`、budget、context 和 provider 参数；`resolved_tools` 必须由 `scaffold + test_feedback_policy + task visibility` 推导，并写入 configuration manifest 作为审计结果。

23 题正式 baseline 开始前必须冻结预算，生成：

```text
formal_budget_freeze_manifest.json
```

该 manifest 至少绑定 `max_turns`、`max_tool_calls`、`max_test_runs`、`task_timeout_sec`、`command_timeout_sec`、`max_output_tokens`、temperature、provider model id、scaffold version、prompt sha256、resolved tools 和 context policy。23 题开始后，只要修改任一字段，就必须新建 baseline id，不能把新旧结果混在同一个分母中。

## 测试可见性策略

SWE-Bench Lite development instances 的正式策略：

- `test_feedback_policy=disabled`
- `max_test_runs=0`
- 模型不可见 `test_command`
- 模型不可见 fail-to-pass selectors
- 模型不可见 pass-to-pass selectors
- 模型不可见 hidden test patch
- 模型不可见 gold patch
- 模型不可见 final verifier raw output
- 模型不可见 accepted / reward / score

对于 SWE-Bench Lite development final-only task，正式 pre-verl 模式必须在代码层拒绝任何非 `disabled` 的测试反馈策略。也就是说，即使外部脚本误传 `structured_public_feedback`，`repo-harness run-task` 或 pre-verl run config inspect 也必须失败，不能悄悄把 `run_tests` 加回工具集合。

建议新增检查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-run-config \
  PRE_VERL_AGENTLOOP_RUN_CONFIG_MANIFEST \
  --assert-final-only-test-feedback-disabled \
  --assert-resolved-tools-derived \
  --assert-no-hidden-feedback-visible
```

GitHub issue flow tasks 的策略：

- 如果测试命令和测试文件已经由 visibility scan 证明是公开、模型可见且不包含 evaluator-only 信息，可以使用 `structured_public_feedback`。
- 如果无法证明公开可见，则同样使用 `disabled`。
- 禁止在正式展示评测中使用 `oracle_hidden_feedback`。

## Scaffold prompt 风险控制

历史版本的 `patch_focused_react` prompt 包含一些经验型提示，例如路径 fallback、环境派生路径组件、operator regression 等。这些提示不一定违规，但正式展示时容易被追问是否针对某些任务特调。

本计划采用保守口径：

- 正式 baseline 只使用中性化后的 `patch_focused_react` prompt。该 prompt 只描述通用流程：读取相关源码、搜索、做最小持久补丁、查看最终 diff、在允许时通过配置化反馈策略运行测试。
- 历史经验型提示不能进入正式 baseline prompt。禁止在 baseline prompt 中写入某一类题目的具体修复策略，例如“路径组件无效时返回 None 触发 fallback”“不要把某些字符替换成下划线”“某类 operator regression 应该保留 quantity 或 prefix”等。
- 必须把 scaffold prompt 文本、scaffold version、prompt sha256、allowed tools、resolved tools 全部写入 configuration manifest。
- 报告中必须说明这是“完整 scaffold package baseline”，不是“纯推理流程对比”。
- 跑完后不得根据结果修改 prompt 再把新结果和旧结果混在同一个 baseline 中。
- 如果后续要研究历史经验型 prompt 是否提高分数，只能作为单独的 prompt ablation，并且必须固定任务、源码、provider、工具权限、测试可见性、预算和 final verifier。历史经验型 prompt 的结果不得与中性 baseline 混在同一个分母中。

## Scaffold comparison 策略

本轮可以先不把 scaffold comparison 作为正式通过门。原因是当前不同 scaffold 的默认工具权限不同，直接比较会混入工具差异。

如果本轮一定要做 scaffold comparison，只能按“完整 scaffold package comparison”报告：

- `patch_focused_react` resolved tools：`list_files/read_file/grep/edit_file/git_diff`
- `planner_coder_verifier` 在默认阶段工具中可能允许 `create_file` 和 `bash`
- 如果 `planner_coder_verifier` 分数更高，不能直接说阶段化推理更好，只能说“在当前默认 scaffold package 下表现更好”

后续更严格的消融必须做“同工具推理流程比较”：

- 两者强制使用同一组 resolved tools：

```text
list_files
read_file
grep
edit_file
git_diff
```

- 固定 provider、model、temperature、source tree、final verifier plan、test visibility、context policy、budget、environment id。
- 只让 scaffold 的 phase policy 和 prompt strategy 不同。

## Smoke Test 设计

正式 23 题前先跑 5 个任务，不只挑最容易的任务。

建议 smoke task set：

1. `pre_verl_dev_002_sqlfluff__sqlfluff_2419`
   上一轮 single-shot accepted，用于确认新 AgentLoop 路径不退化。

2. `pre_verl_dev_006_marshmallow_code__marshmallow_1359`
   上一轮 patch apply failed，且有 `src/` 路径和 traceback 相关风险，用于验证工具读源码能不能减少错路径和错上下文。

3. `pre_verl_dev_003_sqlfluff__sqlfluff_1733`
   上一轮 empty patch，用于验证多轮工具流程是否能避免只输出分析、不产出补丁。

4. `pre_verl_dev_017_pylint_dev__astroid_1268`
   上一轮能到达 final verifier 但被拒绝，用于观察工具化修复是否能提升补丁质量。

5. `pre_verl_dev_019_pydicom__pydicom_1694`
   pydicom 仓库任务，用于覆盖不同仓库、路径定位和依赖环境差异。

Smoke 第一轮预算使用宽松配置：

```yaml
max_turns: 24
max_tool_calls: 96
max_test_runs: 0
task_timeout_sec: 1200
command_timeout_sec: 90
max_output_tokens: 4096
temperature: 0.0
```

Smoke 必须观察这些字段：

- `agent_stop_reason` 是否为 `max_turns`、`max_tool_calls`、`context_limit`、`model_error` 或 `final_answer`。
- `tool_call_count` 是否接近 96。
- `invalid_tool_call_count` 是否偏高。
- `permission_denial_count` 是否偏高。
- `edit_file` 是否反复因为 `old_text` 匹配失败。
- `read_file` 输出是否经常被截断。
- `grep` 是否能定位关键文件。
- `git_diff` 是否在 final answer 前出现。
- final patch 是否为空。
- final patch 是否能应用到冻结源码。
- hidden test patch 是否能在 provider patch 后应用。
- final verifier 是 accepted、rejected、timeout，还是没有执行。

预算调整规则：

- 如果模型已经定位到正确文件并开始编辑，但因为 `max_turns` 或 `max_tool_calls` 停止，正式预算应提高。
- 如果模型大部分时间在无效搜索、读错路径、调用不允许工具，优先归因到 scaffold、上下文策略或工具 schema，不应只加预算。
- 如果 smoke 成功样本的实际消耗明显低于上限，正式预算取成功样本较高分位消耗的 1.3 到 1.5 倍，同时设置硬上限。
- 如果 provider 出现额度、限流、鉴权或传输失败，停止继续消耗并生成 blocked evidence。

Smoke 通过门槛不能只靠 blocked reason 替代链路证据。正式 23 题前至少满足：

- 5 个 smoke task 中至少 4 个产生真实 provider terminal outcome。
- 产生真实 provider terminal outcome 的 smoke task 都必须生成 `final_verifier_boundary.json`。
- 5 个 smoke task 中至少 3 个的模型补丁可以应用到 clean source，并且已经尝试后应用 hidden test patch。
- 至少 1 个 smoke task 产生可应用的非空模型补丁。
- 0 个 provider credential raw value 泄漏。
- 0 个 hidden test patch、gold patch、隐藏 selector、final verifier raw output 进入 prepared messages、model-visible transcript、tool result、stdout、stderr 或训练导出。
- 如果 smoke 因 provider 额度、鉴权、限流或服务故障无法满足上述门槛，必须生成 provider blocked evidence，并停止正式测评。

## 23 题正式评测

通过 smoke 后执行全部 23 个 materialized SWE-Bench Lite development instances。

正式结果必须分母清晰：

- `planned_development_instance_count=23`
- `runnable_development_instance_count=23`
- `real_provider_terminal_outcome_count`
- `accepted_count`
- `rejected_by_final_verifier_count`
- `empty_patch_count`
- `patch_apply_failed_count`
- `hidden_test_patch_apply_failed_count`
- `environment_setup_failed_count`
- `provider_or_budget_blocked_count`
- `budget_exhausted_count`
- `harness_or_environment_failure_count`

报告中的 accepted rate 必须写成自定义冻结子集结果，不能写成 SWE-Bench Lite 官方分数。

至少同时报告两个分数，并写清公式：

```text
planned_subset_accept_rate = accepted_count / planned_development_instance_count
terminal_outcome_accept_rate = accepted_count / real_provider_terminal_outcome_count
```

如果某个任务因为 provider 额度、环境物化、TaskDefinition 兼容性或 verifier adapter 自检失败没有产生 terminal outcome，必须保留在 planned denominator 中，并在 terminal denominator 之外单独列出 blocked reason。

## 失败归因规则

每个失败任务都要进入人工可审计归因，不允许只给一个 rejected。

正式 failure owner 枚举必须固定，inspect 拒绝未知值：

- `model_patch_quality`：模型给出可应用补丁，但 final verifier 拒绝。
- `model_patch_format_or_path`：模型没有输出可用补丁、final patch 为空、补丁路径不在冻结源码中、路径前缀错误，或模型补丁无法应用到 clean source。
- `budget_policy`：模型接近完成但达到 turn、tool call、上下文或 task timeout 上限。
- `tool_contract`：工具 schema、tool call parsing、tool use / tool result 配对、edit_file 契约导致明显失败。
- `context_policy`：关键文件没有进入可检索范围，或者 read_file / grep 结果截断导致错误判断。
- `harness_or_environment`：source checkout、dependency setup、hidden test patch apply、verification workspace 创建或 final verifier 执行异常。
- `provider_or_budget`：鉴权、额度、限流、provider timeout、provider transport error。

正式 failure category 枚举也必须固定，至少包括：

```text
accepted
empty_patch
model_patch_apply_failed
hidden_test_patch_conflict_after_candidate_patch
hidden_test_patch_apply_failed_on_clean_source
model_patch_rejected_by_final_verifier
verifier_timeout_budget
verification_workspace_creation_failed
environment_setup_failed
provider_budget_or_rate_limited
provider_authentication_failed
provider_transport_failed
budget_exhausted_before_final_answer
tool_contract_violation
context_policy_failure
```

至少要抽查：

- 所有 accepted 样本。
- 所有 environment 或 harness 归因样本。
- 所有 budget exhausted 样本。
- 每个主要失败类别至少 2 个样本。
- 上一轮 single-shot 的 3 个 accepted 样本是否仍然 accepted。

## 机器产物

外部脚本应输出这些产物：

```text
pre_verl_agentloop_configuration_manifest.json
pre_verl_agentloop_task_definition_manifest.json
pre_verl_agentloop_task_definition_inspect_report.json
pre_verl_agentloop_run_config_manifest.json
pre_verl_agentloop_prompt_and_tool_policy_report.json
formal_budget_freeze_manifest.json
pre_verl_agentloop_smoke_run_matrix_manifest.json
pre_verl_agentloop_smoke_failure_taxonomy.json
pre_verl_agentloop_formal_run_matrix_manifest.json
pre_verl_agentloop_formal_result_summary.json
pre_verl_agentloop_failure_taxonomy.json
pre_verl_agentloop_failure_review_notes.md
pre_verl_agentloop_final_verifier_adapter_report.json
pre_verl_agentloop_final_verifier_boundary_index.json
pre_verl_agentloop_command_log.jsonl
```

`pre_verl_agentloop_final_verifier_boundary_index.json` 必须有独立 inspect，不能只作为普通文件引用。建议新增：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-pre-verl-agentloop-boundary-index \
  PRE_VERL_AGENTLOOP_FINAL_VERIFIER_BOUNDARY_INDEX \
  --assert-all-formal-runs-bound \
  --assert-command-order \
  --assert-clean-source-origin \
  --assert-run-task-lineage \
  --assert-no-legacy-adapter
```

该 inspect 必须逐条检查 23 题正式 run：

- 每条 formal run 都有 `final_verifier_boundary.json`，包括 empty patch、patch apply failed、hidden patch conflict、timeout 和 rejected。
- 每个 boundary 的 `verifier_adapter_id` 是 `pre_verl_swebench_lite_dev_final_verifier_v0`。
- 每个 boundary 都绑定 `workspace_creation_input_ref`、三阶段 source tree hash、model patch apply result、hidden patch apply result 和 selector result 或明确的未执行原因。
- command lineage 中 `repo-harness run-task` 是该 run 的执行入口。
- command order 满足 model final patch 先于 hidden test patch，hidden test patch 先于 selector command。
- 没有正式记录使用旧 `v3_adapter=swebench_like_fixed`、旧 pilot command name、旧 pilot stage 或旧 pilot schema。

每条 run 必须保留：

```text
run_metadata.json
metrics.json
final.patch
final.diff
events.jsonl
transcript.jsonl
artifacts/
final_verifier_boundary.json
```

所有产物必须绑定 `path`、`sha256`、`size_bytes`，并记录 command log。

## 进入正式 baseline 的硬门槛

只有满足以下条件，才能把结果标记为正式 AgentLoop baseline：

- `repo-harness run-pre-verl-agent-evaluation-pilot` CLI 入口已经移除或机器级禁用。
- 正式 aggregation manifest 中 `baseline_source=repo_harness_agentloop_run_task`。
- 正式 aggregation manifest 中 `forbidden_scaffold_ids=["single_shot_patch_no_tools"]`，并且实际结果中 0 条记录使用 forbidden scaffold。
- 正式 `TaskDefinition`、run result、aggregation record 和 command lineage 中 0 条记录使用旧 `v3_adapter=swebench_like_fixed` 作为正式 pre-verl adapter。
- 所有正式结果都有 `run_task_run_dir`，并且该目录包含 `run_metadata.json`、`events.jsonl`、`transcript.jsonl`、`metrics.json`、`final.patch` 或明确的 no-patch terminal artifact。
- 23 个 `TaskDefinition` 全部通过 `inspect-pre-verl-agentloop-task-definitions --assert-run-task-compatible --assert-evaluator-only-hidden-inputs --assert-no-hidden-material-in-model-visible-fields`。
- SWE-Bench Lite development final-only task 的 run config 全部通过 `inspect-pre-verl-agentloop-run-config --assert-final-only-test-feedback-disabled`。
- final verifier adapter 通过 `inspect-pre-verl-final-verifier-adapter --assert-model-patch-before-hidden-test-patch --assert-clean-source-hidden-patch-self-check --assert-boundary-artifacts-complete`。
- 23 题 formal boundary index 通过 `inspect-pre-verl-agentloop-boundary-index --assert-all-formal-runs-bound --assert-command-order --assert-clean-source-origin --assert-run-task-lineage --assert-no-legacy-adapter`。
- 5 个 smoke task 中至少 4 个产生真实 provider terminal outcome。
- 产生真实 provider terminal outcome 的 smoke task 都有 `final_verifier_boundary.json`。
- 5 个 smoke task 中至少 3 个的模型补丁可以应用到 clean source，并且已经尝试后应用 hidden test patch。
- smoke 中至少 1 个任务完成可应用的非空 final patch。
- 23 题正式 baseline 开始前已经生成 `formal_budget_freeze_manifest.json`。
- smoke 中没有 provider credential raw value 泄漏。
- smoke 中没有 hidden test patch、gold patch、隐藏 selector、final verifier raw output 进入 prepared messages、model-visible transcript、tool result、stdout、stderr 或训练导出。
- `repo-harness run-task` 的 run metadata、tool schema snapshot、events、transcript、final patch、final verifier result 都可读。
- 23 题正式运行全部来自 `repo-harness run-task`。
- 23 题结果中每个非 accepted 样本都有 failure owner 和 failure category。
- 所有 accepted 样本都由 strict final verifier 接受。

如果 `run-task` 不能安全消费当前 materialized SWE-Bench Lite dev tasks，则不能开始正式评测，必须先修核心链路兼容性。

## 后续严格消融

正式 baseline 完成后，再做这些增强：

- 中性 baseline prompt 与历史经验型 prompt 的 prompt ablation。
- `patch_focused_react` 与 `planner_coder_verifier` 的同工具对比。
- `patch_focused_react` 与 `planner_coder_verifier` 的完整 scaffold package 对比。
- budget comparison：同任务、同 provider、同 scaffold、同工具、同上下文策略，只改变预算。
- DeepSeek V4 Pro 与 OpenAI provider 的 provider comparison，前提是两边都有足够额度，并且完全固定 scaffold、工具、预算、上下文和 final verifier。

这些消融不能覆盖第一轮正式 baseline 的分母和结论，只能作为后续分析维度。
