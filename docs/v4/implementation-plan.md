# RepoHarness V4 Implementation Plan

## 0. 文档定位

本文把 `docs/v4/scope-and-roadmap.md` 中已经收敛后的 V4 范围，转化为可以逐阶段实现、逐阶段验收、逐阶段审查的工程实施计划。

本文不是 V4 已经完成的声明，也不是完整 SWE-Bench Lite / SWE-Bench Verified 榜单复现计划。V4 的目标是在 V3 已经通过的真实 Docker backend、真实 repository-level task、固定 SWE-Bench-like 小子集、context compaction、export audit 和 final acceptance 机制之上，继续增强 RepoHarness 稳定产出更多真实、可比较、训练友好 agent 轨迹的能力。

本阶段最小完成范围由三条 P0 主线和两个已经明确纳入的轻量 P1 增强组成：

1. P0-1：单机 rollout 和实验编排升级。
2. P0-2：受控固定任务集扩展和人工可审计 PR / issue 任务构造。
3. P0-3：训练导出质量、trajectory packing 和 failure / reward 审计升级。
4. P1-2：轻量 audit-only 权限、工具生命周期和 hook 审计事实。
5. P1-4：轻量 dataset card、run card、export card，以及 provenance、污染扫描和复现命令索引。

本阶段只为 P1-1 provider / scaffold / budget matrix 保留必要元数据，不实现完整评测矩阵，不生成 provider 对比报告，不把 provider 或 scaffold 排名作为验收目标。本阶段不实现 P1-3 context strategy / project context / session continuation，也不实现任何 P2 候选。

## 1. 前置输入和可信基线

### 1.1 V3 基线

V4 实施前必须确认 V3 closure commit `17b1b95 fix: handle excluded post acceptance docs` 仍然是当前分支祖先，并且当前 V3 final acceptance 证据仍然可 inspect：

```bash
git merge-base --is-ancestor 17b1b95 HEAD
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

若任一检查失败，停止 V4 实施并先修复或解释基线偏移。V4 不修改 V3 acceptance 产物，不重写 V3 final report，不把旧 V2 时代 Docker 未实现表述覆盖 V3 final acceptance 事实。

### 1.2 V4 范围输入

V4 实施以以下文档为范围输入：

- `docs/v4/scope-and-roadmap.md`
- `docs/v4/swe-task-feasibility-experiment-plan.md`
- `docs/v4/pr-issue-task-source-plan.md`
- `docs/v4/review/scope-review.md`
- `docs/v4/review/pr-issue-task-source-plan-review.md`

范围冲突时，优先级为：

1. 当前 V3 final acceptance 机器证据。
2. `docs/v4/scope-and-roadmap.md` 中已经收敛的 P0、P1 本阶段取舍和 P2 不进入范围。
3. V4 feasibility 和 PR / issue task source 前置设计文档。
4. V1 / V2 历史文档和旧架构描述。

### 1.3 V4 任务前置 feasibility 证据

V4 implementation plan 可以使用当前已经完成的本机 feasibility 证据作为输入，但不能把它们直接计为 V4 final accepted / auditable task definitions。它们必须先接入 RepoHarness task adapter、run selection、ACCEPTANCE_INPUTS、acceptance bundle 和 V4 final acceptance。

当前可作为实施输入的 PR / issue feasibility run：

```text
runs/v4-pr-issue-task-source-feasibility-20260504T063745Z/
```

关键事实：

- 8 个 PR / issue 候选达到 `freeze_ready`。
- 8 个候选全部通过 Docker feasibility、flaky probe、adapter-visible task statement freeze、adapter-visible denylist scan 和 training export boundary report。
- 8 个候选覆盖 Go、Python、JavaScript / TypeScript、Rust。
- `accepted_counting_allowed = false`，原因是这些候选尚未接入 RepoHarness task adapter、run selection、acceptance inputs 和 final V4 acceptance。

V4 implementation 应优先把这 8 个 freeze-ready PR / issue 候选作为 P0-2 的任务接入池：

- `go_cobra_2356` -> `v4_go_cobra_completion_args`
- `go_testify_1531` -> `v4_go_testify_numeric_equal_values`
- `go_toml_1041` -> `v4_go_toml_error_position`
- `py_click_3208` -> `v4_py_click_help_hint_shadowing`
- `py_pluggy_646` -> `v4_py_pluggy_multi_hook_unregister`
- `js_execa_1176` -> `v4_js_execa_escaped_template_newlines`
- `js_yargs_2332` -> `v4_js_yargs_completion_parser_config`
- `rust_fd_1805` -> `v4_rust_fd_exec_null_separator`

当前可作为 public SWE-Bench-like 扩展输入的 feasibility 证据：

```text
runs/v4-swe-task-feasibility-20260504T044301Z/
```

初始 public SWE-Bench-like 候选包括：

- `django__django-11283`
- `astropy__astropy-14182`
- `sphinx-doc__sphinx-7686`
- `matplotlib__matplotlib-18869`
- `scikit-learn__scikit-learn-10297`

这些 public SWE-Bench-like 候选已经通过初始 official gold patch probe，但仍需 RepoHarness 自有 source materialization、adapter-visible input freeze、evaluator-only evidence manifest、RepoHarness 自有 verifier probe、flaky probe 和最终 V4 acceptance 才能计入 V4 accepted / auditable task definitions。

当前 public SWE-Bench-like feasibility 中的 selection summary 和相关 manifest 只能作为 audit-only implementation metadata 绑定。即使某个文件名或字段名包含 adapter-visible，也不能直接进入模型可见任务输入；因为这些汇总材料可能包含 `patch_sha256`、`test_patch_sha256`、fail-to-pass / pass-to-pass 计数、官方来源字段或 selector-derived metadata。V4 必须从这些 audit-only 材料重新派生 sanitized model-visible task input，并证明派生输入不包含 patch、test patch、hidden selector、official-result、verifier-result 或 official harness 事实。

## 2. V4 实施不变量

### 2.1 可见性和污染边界

以下内容不得进入模型可见上下文、prepared messages、tool observation、模型可见 trajectory payload、SFT assistant target、preference target、rollout action 或 rollout observation payload：

- evaluator-only evidence。
- reward-only evidence。
- gold patch。
- raw test patch。
- hidden test selector。
- official harness report。
- official report。
- official resolved status。
- provider raw response。
- Authorization marker。
- provider credential marker。
- PR diff。
- PR body。
- review comments 和 review suggestions。
- commit messages after base。
- fix commit URL。
- merge commit URL。
- Docker verifier stdout / stderr 原始日志。
- flaky probe verifier 原始日志。
- hidden selector 命中细节。
- reward scalar、reward label、verifier 原始输出、verifier trace。reward scalar 和 reward label 的唯一例外是非模型可见、字段路径受 allowlist 约束的 structured reward / RewardMetadata / audit-only metadata。
- Claude / Codex / LLM coding session URL 或相关 AI marker，除非它们只作为 audit-only provenance 并且没有进入模型可见输入。

adapter-visible task input 只允许包含经过审查的问题陈述、公开复现症状、允许的仓库上下文、任务执行说明和安全 source ref。模型可见训练文本只允许使用模型当时实际可见的 task input、仓库文件、工具结果和经过 export policy 标记为 trainable 的 observation。非模型可见 structured reward、RewardMetadata 和 audit-only metadata 必须由 allowlist policy、字段路径和 visibility policy 单独约束。

### 2.2 final verifier 权威性

final verifier 仍然是 accepted / rejected / inconclusive 的权威来源。reward audit、reward hacking risk audit、patch quality metrics、LLM judge 风险检查、dataset card 或 export card 都只能作为诊断、过滤、分层或人工审查辅助，不能把 final verifier 未接受的样本提升为 accepted。

### 2.3 单机优先和 Docker 边界

V4 只实现单机 queue、lease、retry、resource lock、batch resume 和 run selection query。Docker backend 继续描述为 Docker-based executable repository environment，不是生产级安全沙箱，不提供多租户隔离承诺。

### 2.4 P1/P2 本阶段边界

本阶段纳入 P1-2 和 P1-4，必须像 P0 一样有 schema、inspect 命令、正例、负例、acceptance inputs 或 acceptance bundle 绑定方式。

本阶段不实现：

- 完整 provider / scaffold / budget 评测矩阵。
- provider leaderboard。
- context strategy comparison。
- ProjectContextSnapshot。
- session continuation。
- Frozen MCP snapshot。
- 代码检索专项评测。
- 只读子代理和 sidechain transcript。
- prompt injection / instruction conflict diagnostic tasks。
- 用户可配置、项目可配置、插件可配置或技能 frontmatter 可配置的完整 hook 系统。
- before_model_call / after_model_call hook。
- stop hook、session hook、file changed hook、subagent hook、远程会话 hook。
- 能改写工具输入、工具结果、模型历史、final verifier、reward 主事实或 training target 的 hook。

### 2.5 全局污染 denylist 和扫描面

V4 必须定义统一的 `V4ContaminationDenylist` 或等价规则集，不能让每个阶段维护互不一致的局部 denylist。阶段实现可以按产物拆分扫描器，但必须引用同一份 denylist version、denylist sha256 和 allowlist policy version。

统一扫描面至少覆盖：

- adapter-visible task input。
- prepared messages。
- model-visible transcript records。
- events。
- artifacts manifest。
- run metadata。
- checkpoints。
- context compaction 或 content replacement facts。
- export records。
- dataset card、run card、export card。
- provenance summary。
- repro command index。
- implementation log。
- acceptance inputs、acceptance report、acceptance command log 和 acceptance bundle。

统一 denylist 至少包含：

- evaluator-only evidence、gold patch、raw test patch、hidden selector、FAIL_TO_PASS / PASS_TO_PASS 原始 selector。
- official harness report、official report、official resolved status。
- provider raw response、provider credential marker、Authorization marker。
- verifier raw output、verifier trace、Docker verifier stdout / stderr、flaky verifier stdout / stderr、hidden selector 命中细节。
- reward scalar、reward label、reward-only evidence，禁止进入模型可见文本、prompt、action、observation、assistant target、SFT target 和 preference target。
- PR body、PR diff、review comment、review suggestion、raw commit message after base、fix commit URL、merge commit URL。
- Claude / Codex / LLM session URL、AI coding session marker。
- 本机绝对路径、credential path、secret-like token。

reward scalar 和 reward label 可以出现在非模型可见的 reinforcement learning rollout structured reward 字段、RewardMetadata、reward audit report 或 audit-only metadata 中，但必须满足全部条件：字段路径在 allowlist policy 中显式列出；字段带有 `model_visible=false` 或等价 visibility 标记；不能拼接进自然语言 observation、assistant target、prompt fragment、SFT target 或 preference target；export audit 必须验证字段路径和 visibility policy。

负例测试必须覆盖每一种扫描面和每一类高风险 denylist 项。允许保留的 provenance 只能是脱敏摘要、hash、size、purpose、source kind 和 boundary status，并且必须明确标记为 audit-only 或 evaluator-only。允许保留的 structured reward 字段只能位于非模型可见 allowlisted path 中。

## 3. 代码和文档落点

V4 应尽量沿用 V3 已有模块边界，避免重命名和大规模重构。建议落点如下：

```text
src/repo_harness/
  schema_versions.py
  cli/
    main.py
  evaluation/
    experiment.py
    schemas.py
  rollout/
    schemas.py
    queue.py
    lease.py
    worker.py
    selection.py
    inspect.py
  tasks/
    schemas.py
    adapter.py
    v4_pr_issue.py
    v4_swebench_like.py
    source_freeze.py
    visibility.py
  workspace/
    docker_adapter.py
    schemas.py
  verifier/
    runner.py
    schemas.py
    v4_task_verifier.py
  permissions/
    schemas.py
    system.py
    trace.py
  tools/
    minimal.py
    lifecycle.py
  hooks/
    audit.py
    schemas.py
  trajectory/
    recorder.py
    schemas.py
    inspect.py
  export/
    exporter.py
    audit.py
    packing.py
    quality.py
    cards.py
  reward/
    schemas.py
    audit.py
  run_metadata/
    schemas.py
    writer.py
    reader.py
```

如果实现时发现新模块会造成过度拆分，可以把 `rollout/`、`hooks/` 或 `cards.py` 的能力先落在已有模块中，但机器产物、schema version、inspect 命令和 tests 不能省略。implementation log 应以机器产物和 inspect 契约为主，不以新增目录数量作为完成信号；如果阶段实现复用已有 `evaluation`、`tools`、`permissions`、`export` 或 `run_metadata` 模块，也应视为合格路径。

建议新增或更新的测试目录：

```text
tests/unit/test_v4_rollout_schemas.py
tests/unit/test_v4_rollout_queue.py
tests/unit/test_v4_task_freeze.py
tests/unit/test_v4_visibility_policy.py
tests/unit/test_v4_tool_lifecycle_trace.py
tests/unit/test_v4_export_quality.py
tests/unit/test_v4_cards.py
tests/integration/test_v4_rollout_resume.py
tests/integration/test_v4_task_adapter.py
tests/integration/test_v4_export_audit.py
tests/integration/test_v4_acceptance.py
tests/fixtures/v4/
```

## 4. 阶段 0：基线确认和实施输入冻结

### 4.1 目标

确认 V3 仍然可信，冻结 V4 implementation 输入，避免后续阶段隐式读取未跟踪 `runs/` 目录或浮动 GitHub 状态。

### 4.2 主要工作

1. 执行 V3 baseline inspect。
2. 记录当前 V4 feasibility 输入 manifest 的 path、sha256、schema version 和生成命令。
3. 生成 V4 implementation input manifest。
4. 定义哪些 feasibility 产物可以进入受版本控制的小型 fixtures，哪些大体积 source archive 只能通过显式输入路径、sha256 和 local artifact root 绑定。

### 4.3 建议机器产物

- `v4_implementation_input_manifest.json`
- `v4_feasibility_input_binding.json`
- `v4_baseline_check_report.json`
- `v4_implementation_input_audit_report.json`

### 4.4 验收和 negative tests

通过条件：

- `17b1b95` 是当前 HEAD 祖先。
- V3 acceptance report inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- V4 PR / issue feasibility input manifest sha256 可复核。
- V4 implementation input manifest 不包含 raw patch、raw PR body、PR diff、provider raw response 或 verifier raw output。
- feasibility input manifest 的内部计数一致：例如 `candidate_count == len(candidate_results)`，`passed_count`、`failed_count`、`freeze_ready_count` 等汇总字段必须与明细行一致。若原始 probe manifest 存在历史计数不一致，implementation input binding 必须指向已校正或上层 summary manifest，并把原始不一致记录为 audit note，不能让不一致 manifest 直接进入 accepted counting gate。

负例：

- 输入 manifest 指向不存在的 run path 时 inspect 失败。
- 输入 manifest sha256 与实际文件不一致时 inspect 失败。
- adapter-visible 输入中出现 PR URL、issue URL、PR 编号、fix commit hash、gold patch marker、AI session URL 或 hidden selector marker 时 inspect 失败。
- feasibility manifest 的汇总计数与明细行不一致，且没有被上层 binding 明确降级为 audit-only historical probe artifact 时 inspect 失败。

本阶段必须新增独立 inspect：

```bash
repo-harness inspect-v4-implementation-inputs v4_implementation_input_manifest.json --assert-complete
```

`inspect-v4-inputs` 可以复用同一底层检查逻辑，但必须明确区分 Stage 0 的 implementation inputs 和 final acceptance 的 acceptance inputs，避免用最终验收输入文件替代前置冻结门。

## 5. 阶段 1：V4 schema、inspect 命令和 acceptance skeleton

### 5.1 目标

先定义 V4 的机器产物契约，再实现业务逻辑。每个进入本阶段范围的 P0、P1-2、P1-4 产物都必须有 schema、inspect 命令、正例 fixture、负例 fixture和 acceptance report 字段。

### 5.2 主要工作

1. 新增 V4 schema version 常量。
2. 定义 P0-1 rollout orchestration schema。
3. 定义 P0-2 task construction / freeze schema。
4. 定义 P0-3 export quality / reward audit schema。
5. 定义 P1-2 permission trace、tool lifecycle trace、hook audit schema。
6. 定义 P1-4 dataset card、run card、export card schema。
7. 定义 V4 acceptance report schema。
8. 定义 V4 acceptance inputs schema。
9. 定义 V4 acceptance bundle manifest 扩展。
10. 新增 inspect 命令骨架。

### 5.3 必须覆盖的 inspect 命令

建议命令名称：

```bash
repo-harness inspect-v4-inputs V4_ACCEPTANCE_INPUTS.json --assert-complete
repo-harness inspect-v4-implementation-inputs V4_IMPLEMENTATION_INPUT_MANIFEST.json --assert-complete
repo-harness inspect-rollout-queue RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-rollout-leases RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-rollout-retry RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-rollout-budget RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-resource-locks RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-resource-usage RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-rollout-resume RUN_OR_QUEUE_DIR --assert-complete
repo-harness inspect-run-selection-query RUN_SELECTION_QUERY_REPORT.json --assert-complete
repo-harness inspect-v4-task-freeze TASK_FREEZE_MANIFEST.json --assert-complete
repo-harness inspect-v4-task-validity TASK_VALIDITY_REPORT.json --assert-complete
repo-harness inspect-v4-tool-contract RUN_DIR --assert-frozen
repo-harness inspect-v4-tool-lifecycle RUN_DIR --assert-complete
repo-harness inspect-v4-agent-run-integration RUN_DIR --assert-complete
repo-harness inspect-v4-trajectory-store RUN_DIR --assert-readable
repo-harness inspect-v4-export-quality EXPORT_DIR --assert-complete
repo-harness inspect-v4-cards CARD_DIR --assert-complete
repo-harness inspect-v4-contamination-scan SCAN_REPORT.json --assert-clean
repo-harness inspect-v4-acceptance V4_ACCEPTANCE_REPORT.json --assert-complete
```

如果命令名称需要按现有 CLI 风格调整，implementation log 必须说明调整原因，并保持每个机器产物都有 inspect 覆盖。

### 5.4 建议机器产物

- `v4_acceptance_inputs.json`
- `v4_acceptance_report.json`
- `v4_acceptance_bundle_manifest.json`
- schema fixture 目录和 negative fixture 目录。

### 5.5 验收和 negative tests

通过条件：

- 所有 V4 schema 都有最小 valid fixture。
- 所有进入本阶段的机器产物都有 inspect 命令。
- inspect 命令不读取隐式 latest run，不从当前目录猜测输入，不依赖未声明环境变量。
- acceptance inputs 显式绑定 selected run refs / role refs、P0 机器产物、本阶段 P1-2 / P1-4 机器产物、V2/V3 回归证据和 export audit 证据。

负例：

- 缺少 schema version 时失败。
- 缺少 sha256 或 sha256 不匹配时失败。
- RUN_SELECTION_MANIFEST 中出现报告类产物路径而不是 selected run refs / role refs 时失败。
- ACCEPTANCE_INPUTS 缺少 P1-2 / P1-4 已纳入产物时失败。
- acceptance script 自动选择 latest run 时测试失败。

### 5.6 机器产物到 inspect 命令追踪表

Stage 1 必须维护一张机器产物到 inspect 命令的追踪表。若 implementation plan 后续新增机器产物，必须同步更新此表和对应 fixture。

| 范围 | 机器产物 | inspect 覆盖 |
| --- | --- | --- |
| Stage 0 input freeze | `v4_implementation_input_manifest.json`、`v4_feasibility_input_binding.json`、`v4_baseline_check_report.json` | `inspect-v4-implementation-inputs` |
| P0-1 queue | `rollout_queue_manifest.json`、`worker_run_log.jsonl` | `inspect-rollout-queue` |
| P0-1 lease | `lease_state_report.json` | `inspect-rollout-leases` |
| P0-1 retry | `retry_policy_report.json` | `inspect-rollout-retry` |
| P0-1 budget | `budget_control_report.json` | `inspect-rollout-budget` |
| P0-1 resource locks | `resource_lock_report.json` | `inspect-resource-locks` |
| P0-1 resource usage | `resource_usage_report.json` | `inspect-resource-usage` |
| P0-1 resume | `batch_resume_report.json`、`checkpoint_state_report.json` | `inspect-rollout-resume` |
| P0-1 selection | `run_selection_query_report.json` | `inspect-run-selection-query` |
| P0-2 task freeze | `pr_task_construction_manifest.json`、`source_archive_manifest.json`、`adapter_visible_task_input_manifest.json`、`evaluator_only_evidence_manifest.json` | `inspect-v4-task-freeze` |
| P0-2 task validity | `source_materialization_report.json`、`baseline_verifier_report.json`、`post_patch_verifier_report.json`、`flaky_detection_report.json`、`environment_stability_report.json`、`dependency_cache_report.json`、`license_provenance_review_report.json`、`use_boundary_review_report.json`、`task_validity_report.json` | `inspect-v4-task-validity` |
| P1-2 tool contract | `permission_policy_snapshot.json`、`hook_policy_snapshot.json`、`mcp_policy_snapshot.json`、`tool_contract_v4_snapshot.json` | `inspect-v4-tool-contract` |
| P1-2 lifecycle | `permission_decision_trace.jsonl`、`tool_lifecycle_trace.jsonl`、`hook_audit_report.json` | `inspect-v4-tool-lifecycle` |
| Stage 5 run integration | `v4_agent_run_integration_report.json`、`runspec_metadata_report.json`、`final_verifier_boundary_report.json`、`prepared_messages_binding_report.json` | `inspect-v4-agent-run-integration` |
| Stage 5 trajectory store | `transcript.jsonl`、`events.jsonl`、`artifacts.json`、`run_config_facts.json`、`run_metadata.json` 或 interrupted facts | `inspect-v4-trajectory-store` |
| P0-3 export quality | `trajectory_quality_manifest.json`、`sample_tier_manifest.json`、`failure_dataset.jsonl`、`packing_manifest.json`、`reward_audit_report.json`、`reward_hacking_risk_audit_report.json`、`patch_quality_report.json`、`test_overfitting_risk_audit_report.json`、`preference_pair_trainability_report.json`、`blocked_pair_report.json` | `inspect-v4-export-quality` |
| P1-4 cards | `dataset_card.md`、`dataset_card.json`、`run_card.json`、`export_card.json`、`provenance_summary.json`、`contamination_scan_summary.json`、`repro_command_index.json` | `inspect-v4-cards` |
| 全局污染扫描 | `task_visibility_scan_report.json`、`contamination_scan_summary.json`、export audit scan reports、acceptance bundle scan facts | `inspect-v4-contamination-scan` 和相关阶段 inspect 递归覆盖 |
| Final acceptance | `run_selection_manifest.json`、`v4_acceptance_inputs.json`、`v4_acceptance_report.json`、`acceptance_bundle_manifest.json`、`acceptance_command_log.jsonl` | `inspect-v4-inputs`、`inspect-v4-acceptance`、`inspect-acceptance-bundle` |

## 6. 阶段 2：V4 task source freeze 和 task adapter integration

### 6.1 目标

把 feasibility run 中已经 freeze-ready 的候选转化为 RepoHarness 可执行、可审计、可验收的正式任务定义。这个阶段只证明任务和 verifier 可运行，不评测 agent 能力。

### 6.2 任务池策略

默认接入策略：

- 优先接入 8 个 PR / issue freeze-ready 候选。
- 同时接入 5 个 public SWE-Bench-like 候选作为扩展池和回归锚点。
- 最终 V4 acceptance 至少需要 8 个 accepted / auditable task definitions。
- 至少 4 个 accepted / auditable task definitions 必须来自 V4 PR / issue 构造流程。
- diagnostic-only、quarantined、rejected 不计入最低数量。

PR / issue 候选不因为 feasibility `freeze_ready` 自动计数。只有完成 RepoHarness adapter 接入、source materialization repeat check、baseline verifier、post-patch verifier、flaky probe、visibility scan、task validity inspect 和 acceptance inputs 绑定后，才能计入 V4 accepted / auditable。

### 6.3 主要工作

1. 定义 `V4TaskSourceManifest`、`V4TaskDefinition`、`V4EvaluatorOnlyEvidenceManifest`、`V4TaskValidityReport`。
2. 将 adapter-visible task definitions 迁入受控 fixture 或通过显式 input manifest 绑定。
3. 将 evaluator-only evidence 通过 manifest 绑定到 verifier / audit，不暴露给 task adapter。
4. 实现 PR / issue task adapter。
5. 实现 public SWE-Bench-like V4 task adapter 扩展。
6. 实现 source archive materialization。
7. 实现 source materialization repeat check。
8. 实现 baseline verifier report。
9. 实现 post-patch verifier probe report。
10. 实现 flaky detection report。
11. 实现 task validity report。
12. 实现 task quarantine / diagnostic-only / rejected 状态。
13. 实现 environment stability report，记录 dependency install 稳定性、verifier runtime 分布、Docker platform facts、timeout、flaky signal、cache hit / miss 和 environment stability score。
14. 实现 dependency cache report，记录 cache source、cache key、cache artifact hash、hit / miss、invalidation reason、network policy by phase 和是否允许 verifier 阶段联网。
15. 实现 license / provenance / use-boundary review report，并把 review status 纳入 accepted / auditable task gate。

模块所有权边界：

- Task Adapter 只负责把 frozen task input 转成规范化 task definition 和 evidence refs，不负责执行依赖安装、source checkout、baseline verifier 或 post-patch verifier。
- Source materialization 由 Workspace Adapter 或 source freeze 组件执行，并输出 source tree hash、archive hash 和 materialization facts。
- Dependency setup、dependency cache 和 Docker execution facts 由 Workspace Adapter / Eval Runner 执行并记录。
- Baseline verifier、post-patch verifier 和 flaky probe 由 Verifier / Eval Runner 执行，Task Adapter 只能引用其 evidence refs。
- Visibility scan 和 task validity inspect 可以聚合上述产物，但不能让 adapter 读取 evaluator-only evidence 内容。

### 6.4 建议机器产物

- `pr_task_construction_manifest.json`
- `source_archive_manifest.json`
- `source_materialization_report.json`
- `baseline_verifier_report.json`
- `post_patch_verifier_report.json`
- `flaky_detection_report.json`
- `environment_stability_report.json`
- `dependency_cache_report.json`
- `license_provenance_review_report.json`
- `use_boundary_review_report.json`
- `task_validity_report.json`
- `generated_task_definition.jsonl`
- `evaluator_only_evidence_manifest.json`
- `adapter_visible_task_input_manifest.json`
- `task_visibility_scan_report.json`

### 6.5 验收和 negative tests

通过条件：

- 至少 8 个 task definitions 达到 accepted / auditable。
- 至少 4 个 accepted / auditable task definitions 来自 V4 PR / issue 构造流程。
- 每个 accepted / auditable task 都有 fixed revision、source archive hash、source tree hash、adapter-visible input hash、evaluator-only evidence manifest hash、baseline verifier plan hash、post-patch verifier evidence ref 和 flaky probe evidence ref。
- PR / issue 任务可以追溯到 repository URL、issue / PR / fix source、selected fixed revision、patch source kind 和 patch apply probe。
- bug-fix fail-to-pass 在 baseline 上失败被记录为有效任务信号；pass-to-pass、setup、依赖或 broad regression failure 才能导致 unstable / quarantined。
- 每个 accepted / auditable task 都有 license review、provenance review 和 use-boundary review 通过状态；存在 AI/session marker、manual license review 或 provenance ambiguity 的候选必须有 audit-only boundary note 和人工审查状态。
- 每个 accepted / auditable task 都有 environment stability score、dependency cache facts 和 verifier phase network policy。

负例：

- gold patch 进入 adapter-visible input 时失败。
- raw test patch 进入 adapter-visible input 时失败。
- PR body、PR diff、review comment、fix commit URL、merge commit URL、AI session URL 或 provider raw response 进入 adapter-visible input 时失败。
- official harness report、official report、official resolved status、verifier raw output、verifier trace、Docker verifier stdout / stderr、flaky verifier stdout / stderr、reward scalar、reward label 或 hidden selector 命中细节进入 adapter-visible input 或 trainable payload 时失败。
- source materialization 两次 source tree hash 不一致时失败。
- flaky probe 结果不稳定却标记 accepted 时失败。
- 没有关联 provenance 或人工 review note 的 PR / issue task 被计入 4 个新增任务时失败。
- license review、provenance review、use-boundary review、environment stability score 或 dependency cache facts 缺失时，任务不能计入 accepted / auditable。
- verifier 阶段需要联网但未显式记录 network exception 和 dependency snapshot 时，任务不能计入 accepted / auditable。

## 7. 阶段 3：单机 rollout queue、lease、retry、resource lock 和 batch resume

### 7.1 目标

把 V3 的单次或少量验收式运行升级为可恢复、可审计、可查询的单机批处理 rollout 编排。

### 7.2 主要工作

1. 实现 rollout queue manifest。
2. 实现 queue item 状态：queued、leased、running、accepted、failed、invalid、retried、skipped、quarantined。
3. 实现 run leasing：获取、续约、完成、释放、过期。
4. 实现 resource lock：source workspace、Docker image build、dependency cache、task materialization。
5. 实现 retry policy：provider error、environment error、tool error、verifier inconclusive、timeout、interrupted 分类别重试。
6. 实现 budget control：token、wall time、tool count、test run count、provider retry、Docker execution time 和 Docker resource facts 都必须有 budget policy、consumed value、remaining value 和 enforcement result。
7. 实现 worker run log。
8. 实现 command log lineage。
9. 实现 resource usage facts。
10. 实现 batch resume。
11. 实现 run selection query。Stage 3 只验收 queue-native predicates，例如 queue status、lease status、task role、task source tag、provider mode、scaffold id、retry state 和 worker id；final verifier status、sample tier、export tier 等后置字段的 query 验收放到 Stage 5、Stage 6 或 final acceptance。
12. 实现 checkpoint state schema，但只用于 rollout orchestration 的阶段恢复，不实现 P1-3 session continuation。

### 7.3 建议机器产物

- `rollout_queue_manifest.json`
- `worker_run_log.jsonl`
- `lease_state_report.json`
- `batch_resume_report.json`
- `checkpoint_state_report.json`
- `retry_policy_report.json`
- `resource_lock_report.json`
- `budget_control_report.json`
- `resource_usage_report.json`
- `run_selection_query_report.json`

### 7.4 验收和 negative tests

通过条件：

- worker 中断后再次运行，completed run 不被重复执行。
- expired lease 可以被重新认领，active lease 不被第二个 worker 抢占。
- retry policy 按失败类别执行，不把 retry 后 fallback 成功写成 primary success。
- budget control 能在 token、wall time、tool count、test run count、provider retry 或 Docker time 超限前阻断后续动作，并记录 structured budget_exhausted fact。
- resource lock 能防止同一 source materialization 或 Docker image build 被并发破坏。
- Stage 3 run selection query 能根据 queue status、lease status、task role、provider mode、scaffold id、task source tag、retry state 和 worker id 生成显式 selection report。final verifier status 和 sample tier 查询只能用 synthetic fixture 验证 predicate 解析，不能作为 Stage 3 真实 run 验收硬门。
- checkpoint state 至少记录 `checkpoint_schema_version`、`run_id`、`queue_item_id`、`phase_id`、`phase_sha256`、`next_phase`、`run_directory_lock_ref`、`resume_attempt`、`resume_allowed`、`unrecoverable_reason`、`created_at` 和 `checkpoint_payload_sha256`。
- batch resume 不得继承 hidden verifier result、reward、run outcome、failure diagnostics 或 evaluator-only evidence 内容给同一 agent loop；只能继承允许的 queue state、workspace state ref、public task context 和 non-leaking run facts。

负例：

- 无 lease 的 worker 写入 run 状态时失败。
- expired lease 没有进入 reclaim 流程时失败。
- fallback provider 的成功被标成 primary provider accepted 时失败。
- retry 超过 policy max attempts 仍继续执行时失败。
- budget policy 缺失、budget consumed value 超过 limit 仍继续执行、或 budget_exhausted 未写入 worker log 时失败。
- run selection query 缺少 query predicate 或输入 manifest hash 时失败。
- Stage 3 把尚未产生的 final verifier status 或 sample tier 当作真实 run query 硬门时失败。
- checkpoint phase sha256 不匹配、run directory lock 缺失、checkpoint payload 被篡改、或 hidden verifier / reward / outcome fact 被继承到 resumed agent context 时失败。
- batch resume 被实现成跨实验长期 session continuation 或默认长期用户记忆时失败。

## 8. 阶段 4：P1-2 轻量 audit-only permission、tool lifecycle 和 hook 审计

### 8.1 目标

在不实现完整产品式 hook 系统的前提下，把工具调用、权限判断、hook 审计事实转化为可检查的训练轨迹事实。

### 8.2 主要工作

1. 定义 `PermissionDecisionTraceEntry`。
2. 定义 `ToolLifecycleTraceEntry`。
3. 定义 `HookAuditEntry`。
4. 定义 `HookPolicySnapshot` V4 扩展。
5. 在工具查找、schema validation、permission decision、execution start、execution end、artifact ref、truncation、tool_result pairing 处记录 lifecycle facts。
6. 在 allow、deny、ask、safety deny、hook deny 样例中记录 permission trace。
7. 实现 before_tool / after_tool / tool_error audit-only hook event。
8. 实现 hook audit report。
9. 实现 tool contract V4 snapshot。
10. 实现 PermissionPolicySnapshot V4 或等价冻结事实。
11. 继承 V3 MCP disabled / frozen external tool surface facts，记录 `mcp_enabled=false`、`dynamic_tool_discovery_allowed=false` 和 stable external tool surface hash；这不是实现 MCP。
12. 校验稳定工具顺序、tool schema hash、tool result pairing policy、large output artifact policy 和动态工具面冻结状态。
13. 确保 hook 产物默认 audit-only，不进入模型上下文或训练 target。

### 8.3 最低字段要求

`permission_decision_trace.jsonl` 至少包含：

- `schema_version`
- `run_id`
- `turn_id`
- `tool_call_id`
- `decision_stage`
- `rule_source`
- `matched_rule`
- `permission_mode`
- `headless_or_interactive`
- `hook_override`
- `content_safety_check`
- `final_decision`
- `reason`
- `created_at`

`tool_lifecycle_trace.jsonl` 至少包含：

- `schema_version`
- `run_id`
- `turn_id`
- `tool_call_id`
- `tool_name`
- `lookup_status`
- `schema_validation_status`
- `permission_decision_ref`
- `hook_decision_ref`
- `execution_status`
- `artifact_refs`
- `truncation_status`
- `tool_result_pairing_status`
- `error_type`
- `duration_ms`

### 8.4 建议机器产物

- `hook_policy_snapshot.json`
- `hook_audit_report.json`
- `tool_lifecycle_trace.jsonl`
- `permission_decision_trace.jsonl`
- `permission_policy_dataset_manifest.json`
- `permission_policy_snapshot.json`
- `mcp_policy_snapshot.json`
- `tool_contract_v4_snapshot.json`

### 8.5 验收和 negative tests

通过条件：

- 至少覆盖 allow、deny、ask、safety deny、hook deny 五类 permission decision 样例。
- 每个 tool call 都有 lifecycle entry。
- 每个 tool call 都能追溯到 permission decision 或显式 no-permission-required fact。
- tool_result pairing status 与 transcript 中 tool call / tool result 一致。
- hook audit facts 不改写 final verifier、reward 主事实、历史 transcript、tool input、tool result 或 training target。
- PermissionPolicySnapshot、HookPolicySnapshot、MCP disabled / frozen facts、stable tool order 和 tool schema hash 都进入 tool contract snapshot。
- 动态新增工具、动态 MCP discovery、运行中变更工具 schema 或工具顺序漂移都会被 inspect 拒绝。

负例：

- hook 产物进入 model-visible prepared messages 时失败。
- hook 改写 tool result 却仍标记 audit-only 时失败。
- tool call 缺少 tool result pairing status 时失败。
- permission deny 被执行为 allowed tool call 时失败。
- safety deny 被 fallback 成普通 deny 且丢失 reason 时失败。
- tool order 与 tool schema snapshot 不一致、MCP dynamic discovery 被启用、或 tool contract 缺少 permission / hook / MCP policy snapshot ref 时失败。

## 9. 阶段 5：agent run 集成和 RunSpec 元数据保留

### 9.1 目标

把 V4 task definitions、rollout queue、Docker execution、agent loop、tool lifecycle trace、final verifier 和 trajectory store 串成可执行端到端 run。

### 9.2 主要工作

1. 扩展 RunSpec，保留 P1-1 元数据字段。
2. 将 V4 task adapter 接入 agent loop。
3. 将 V4 rollout queue item 转化为 RunSpec。
4. 将 Docker source materialization 与 resource lock 绑定。
5. 将 tool lifecycle trace 和 permission trace 接入 run recorder。
6. 将 final verifier 结果写入 evaluator-only / audit facts。
7. 将 run outcome、failure diagnostics 和 patch artifact 写入 run metadata。
8. 保持 PreparedMessages 与 export observation 绑定。

### 9.3 建议机器产物

- `v4_agent_run_integration_report.json`
- `runspec_metadata_report.json`
- `final_verifier_boundary_report.json`
- `prepared_messages_binding_report.json`
- `interrupted_run_recovery_report.json`
- `trajectory_store_integrity_report.json`

本阶段必须新增 inspect：

```bash
repo-harness inspect-v4-agent-run-integration RUN_DIR --assert-complete
```

### 9.4 P1-1 本阶段元数据字段

每个 V4 run 至少保留以下 P1-1 provider / scaffold / budget 元数据：

- `provider_id`
- `provider_mode`
- `model_id`
- `scaffold_id`
- `budget_policy_id`
- `fallback_policy_id`
- `token_usage`
- `provider_error_category`
- `tool_policy_id`
- `verifier_id`
- `environment_id`

每个 V4 run 还必须保留以下 P0 task provenance 和 visibility 元数据：

- `task_source_tag`
- `task_family`
- `task_visibility_policy_id`

这些字段用于后续审计和质量分析，不构成 provider / scaffold / budget matrix，不允许导出为 provider 排名或 scaffold 对比结论。

### 9.5 验收和 negative tests

通过条件：

- completed run 至少生成 transcript、events、artifacts、run_config_facts、run_metadata、final patch 或 no-patch fact。
- interrupted / crashed run 保留可读 transcript、events、artifacts、run_config_facts 和 structured interrupted / crash facts。
- final verifier hidden facts 不能被同一次 agent loop 读取。
- export observation 能够回指 prepared messages、model input hash 和 context revision。
- `v4_agent_run_integration_report.json` 能绑定 RunSpec、task definition、rollout queue item、Docker facts、tool lifecycle trace、permission trace、final verifier result ref、run metadata 和 trajectory store facts。
- trajectory store inspect 覆盖 ArtifactRef 可解析性、sha256、size_bytes、relative path、redaction status、retention policy、stable `record_id` / `event_id`、events offset、transcript offset、RunRecorder 幂等、半写 artifact、finalize 重入和 crash-readable 状态。
- PreparedMessages 绑定检查至少覆盖 `prepared_messages_ref`、`prepared_messages_sha256`、`model_input_hash`、`tool_schema_snapshot_hash`、`content_replacement_state_hash`、`context_revision`、`tool_observation_ref` 和 `observation_source_event_ref`。
- Stage 5 run selection query 可以开始覆盖真实 final verifier status；sample tier 查询仍留到 Stage 6 或 final acceptance。

负例：

- final verifier result 出现在同一次 run 的 model-visible observation 中时失败。
- run 缺少 `scaffold_id`、`tool_policy_id`、`verifier_id` 或 `environment_id` 时无法进入 trainable export。
- provider fallback 成功缺少 fallback policy ref 时无法进入 accepted role。
- `v4_agent_run_integration_report.json` 缺少 final verifier boundary、PreparedMessages binding、interrupted / crashed run fact 或 RunSpec 元数据时 inspect 失败。
- ArtifactRef sha256 不匹配、half-written artifact 未标记、record_id / event_id 不稳定、RunRecorder finalize 重入产生重复 terminal facts、或 PreparedMessages 绑定缺少 tool schema hash / content replacement hash / observation source event ref 时失败。

## 10. 阶段 6：P0-3 export quality、trajectory packing、failure dataset 和 reward audit

### 10.1 目标

让 V4 导出不只是“没有污染”，而是能明确区分成功样本、部分成功样本、失败样本、diagnostic-only 样本和 trainable 样本，并能输出可分析的 failure dataset、packed trajectory 和 reward hacking risk audit。

### 10.2 主要工作

1. 定义 sample tiers：success、partial_success、failure、invalid、diagnostic_only、trainable。
2. 定义 failure taxonomy。
3. 实现 trajectory quality manifest。
4. 实现 failure dataset export。
5. 实现 trajectory packing manifest。
6. 实现 preference pair trainability report。
7. 实现 patch quality report。
8. 实现 minimal patch / excessive patch diagnostic，至少记录 patch 文件数、行数、测试文件比例、生成文件改动、重复改动和非相关改动风险。
9. 实现 test-overfitting risk audit，至少检查只改测试、绕过 verifier、删除失败路径、硬编码隐藏 selector、污染 evaluator-only evidence、删除或削弱断言、修改 verifier 配置等风险。
10. 实现 reward audit report。
11. 实现 reward hacking risk audit report。
12. 定义 RewardMetadata V4 schema。
13. 定义 SFT export、rollout export 和 preference pair export 的 V4 schema、valid fixture 和 negative fixture。
14. 扩展 export audit，保证 V2/V3 export 契约仍然成立。

### 10.3 建议机器产物

- `trajectory_quality_manifest.json`
- `sample_tier_manifest.json`
- `failure_dataset.jsonl`
- `packing_manifest.json`
- `reward_audit_report.json`
- `reward_hacking_risk_audit_report.json`
- `patch_quality_report.json`
- `test_overfitting_risk_audit_report.json`
- `preference_pair_trainability_report.json`
- `blocked_pair_report.json`

### 10.4 `no_trainable_preference_pair` 处理

V4 不允许把 V3 的 `preference_pair_baseline_blocked` warning 静默吞掉。实施路径：

1. 在 sample tier 中区分可比较成功、可比较失败、partial success、diagnostic-only。
2. 定义 preference pair 可训练条件：同 task、同 fixed source、同 verifier、同 tool policy、同 context policy、同 scaffold 或明确 compare scope、不同 outcome 且无污染。
3. 对不可训练 pair 输出 blocked reason。
4. 如果 V4 final acceptance 仍没有可训练 preference pair，必须输出 `blocked_pair_report.json`，其中包含 `preference_pair_baseline_blocked` warning、`no_trainable_preference_pair` blocked reason、样本数量、被拒绝原因分布和下一步修复入口。

### 10.5 验收和 negative tests

通过条件：

- trainable payload 不包含 evaluator-only evidence、reward-only evidence、gold patch、hidden selector、official report、provider raw response 或 verifier raw output。
- 每个 packed sample 保留原始 trajectory ref。
- failure dataset 可以追溯到 run id、task id、failure category、source component 和 evidence ref。
- outcome tier 和 trainability status 必须分开记录；例如 verifier accepted 不自动等于 trainable，diagnostic-only failure 也不能被误写成 trainable failure sample。
- failure dataset 必须绑定 task、turn、tool call、workspace state ref、final verifier result ref、failure source component 和 evidence ref。
- RewardMetadata 至少包含 `reward_version`、`formula`、`components`、`sources`、`invalid_for_training`、`invalid_reason`、`acceptance_policy_version` 和 `reward_clip_range`。
- SFT export、reinforcement learning rollout export 和 preference pair export 都必须有 valid fixture 和 negative fixture。
- reward audit 不替代 final verifier。
- patch quality metrics 不把 verifier rejected 样本提升为 accepted。
- minimal patch / excessive patch diagnostic 只作为诊断事实，不替代 final verifier。
- test-overfitting risk audit 能识别 test-only edit、verifier bypass、hidden selector hardcoding、evaluator-only leakage 和删除失败路径等风险。
- Stage 6 run selection query 可以覆盖真实 sample tier、trainable status、diagnostic-only status 和 failure category。

负例：

- reward scalar 出现在训练 target 文本时失败。
- hidden selector 命中细节出现在 trainable payload 时失败。
- packed sample 丢失原始 trajectory ref 时失败。
- verifier rejected 样本被 reward audit 改成 accepted 时失败。
- outcome tier 与 trainability status 混用、RewardMetadata 缺少 version / formula / invalid_for_training、failure dataset 缺少 task / turn / tool / workspace / verifier binding、或任一 export 格式缺少 negative fixture 时失败。
- 只改测试、删除 verifier 路径、硬编码 hidden selector、删除失败断言或读取 evaluator-only evidence 的 patch 没有被 test-overfitting audit 标记时失败。
- excessive patch 被当作 accepted 主事实或 reward 主事实时失败。

## 11. 阶段 7：P1-4 dataset card、run card、export card

### 11.1 目标

把 V4 任务来源、运行条件、模型条件、导出边界、污染扫描、失败分布和复现命令汇总成人工可读和机器可读的审计卡片。

### 11.2 主要工作

1. 实现 dataset card JSON 和 Markdown。
2. 实现 run card JSON。
3. 实现 export card JSON。
4. 实现 provenance summary。
5. 实现 contamination scan summary。
6. 实现 repro command index。
7. 实现 `inspect-v4-cards`。

### 11.3 建议机器产物

- `dataset_card.md`
- `dataset_card.json`
- `run_card.json`
- `export_card.json`
- `provenance_summary.json`
- `contamination_scan_summary.json`
- `repro_command_index.json`

### 11.4 验收和 negative tests

通过条件：

- dataset card 列出任务来源、license / provenance summary、accepted / diagnostic / quarantined / rejected 分布。
- run card 列出 selected run refs、provider mode、scaffold id、budget policy、Docker facts、resource usage summary。
- export card 列出 sample tiers、trainable / diagnostic 分流、污染扫描状态、blocked sources、export policy。
- repro command index 覆盖 V3 baseline checks、V4 task freeze inspect、rollout inspect、export audit、card inspect 和 final acceptance inspect。

负例：

- card 声称数据无需人工审查即可直接训练时失败。
- card 声称公开 leaderboard 可比时失败。
- card 把 Docker backend 描述成生产级安全沙箱时失败。
- card 缺少 contamination scan summary 时失败。
- dataset card、run card、export card、provenance summary、repro command index 或 implementation log 包含 raw PR body、raw commit message、真实 AI session URL、详细 AI marker 文本、provider raw response、verifier raw output 或 hidden selector detail 时失败。允许保留脱敏后的 audit-only 风险摘要、hash、size、purpose 和 boundary status。

## 12. 阶段 8：V4 final acceptance 和 acceptance bundle

### 12.1 目标

以显式 RUN_SELECTION_MANIFEST、ACCEPTANCE_INPUTS 和不可变 acceptance bundle 完成 V4 最终验收。验收脚本不得自动选择最新 run，不得隐式读取当前目录，不得把 feasibility run 直接计为 accepted。

### 12.2 最终验收输入

建议 final rerun 目录结构：

```text
runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/
  run_selection_manifest.json
  v4_acceptance_inputs.json
  acceptance/
    v4_acceptance_report.json
    acceptance_bundle_manifest.json
    acceptance_command_log.jsonl
```

`run_selection_manifest.json` 只绑定 selected run refs / role refs，不绑定所有报告类产物。P0 和本阶段 P1-2 / P1-4 机器产物通过 `v4_acceptance_inputs.json` 或 acceptance bundle 绑定。

final acceptance directory 必须是新目录。任何 build 命令如果发现目标 acceptance directory、acceptance report、bundle manifest 或 acceptance command log 已存在，默认必须失败，除非用户显式选择新的 run id 或归档旧目录。V4 final acceptance 不允许覆盖旧 evidence，也不允许在旧目录中追加生成看似新的验收结果。

### 12.3 V4 acceptance roles

建议至少包含以下 role：

- `v3_regression`
- `v2_regression`
- `real_repository_regression`
- `swebench_like_regression`
- `v4_pr_issue_task_freeze`
- `v4_swebench_like_task_freeze`
- `v4_rollout_orchestration`
- `v4_rollout_resume`
- `v4_agent_run_integration`
- `v4_export_quality`
- `v4_tool_lifecycle_audit`
- `v4_cards`

### 12.4 最终硬门

V4 final acceptance 必须证明：

1. V3 acceptance report inspect 仍通过。
2. V3 acceptance bundle immutable inspect 仍通过。
3. V2 regression 仍通过或有明确非阻塞 skip 口径。
4. 至少 8 个 accepted / auditable task definitions。
5. 至少 4 个 accepted / auditable task definitions 来自 V4 PR / issue 构造流程。
6. P0-1 rollout queue、lease、retry、budget control、resource lock、resource usage、run selection query、batch resume、checkpoint state 通过 inspect。
7. P0-2 task freeze、source materialization、baseline verifier、post-patch verifier、flaky detection、task validity 通过 inspect。
8. P0-3 trajectory quality、sample tier、failure dataset、packing、reward audit、patch quality、test-overfitting risk audit 通过 inspect。
9. P1-2 permission decision trace、tool lifecycle trace、hook audit-only facts 和 tool contract snapshot 通过 inspect。
10. P1-4 dataset card、run card、export card、provenance summary、contamination summary 和 repro command index 通过 inspect。
11. Stage 5 agent run integration 通过 inspect：completed / interrupted / crashed run artifact、run metadata、RunSpec 元数据、final verifier hidden-facts 单向边界和 export observation 回指都必须成立。
12. trainable payload 污染扫描通过。
13. evaluator-only evidence 没有进入 model-visible context 或 trainable payload。
14. final verifier 仍然是 accepted / rejected / inconclusive 主事实来源。
15. RUN_SELECTION_MANIFEST 和 ACCEPTANCE_INPUTS 都显式、不可变、可 sha256 复核。

### 12.5 建议验收命令

```bash
PATH=.venv/bin:$PATH pytest
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness build-v4-run-selection-manifest --query V4_QUERY_SPEC.json --output runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/run_selection_manifest.json
PATH=.venv/bin:$PATH repo-harness build-v4-acceptance-inputs \
  --run-selection runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/run_selection_manifest.json \
  --v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json \
  --v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json \
  --v3-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json \
  --implementation-inputs V4_IMPLEMENTATION_INPUT_MANIFEST.json \
  --rollout-queue ROLLOUT_QUEUE_MANIFEST.json \
  --lease-state LEASE_STATE_REPORT.json \
  --retry-policy RETRY_POLICY_REPORT.json \
  --budget-control BUDGET_CONTROL_REPORT.json \
  --resource-locks RESOURCE_LOCK_REPORT.json \
  --resource-usage RESOURCE_USAGE_REPORT.json \
  --batch-resume BATCH_RESUME_REPORT.json \
  --run-selection-query RUN_SELECTION_QUERY_REPORT.json \
  --task-freeze TASK_FREEZE_MANIFEST.json \
  --task-validity TASK_VALIDITY_REPORT.json \
  --tool-contract TOOL_CONTRACT_V4_SNAPSHOT.json \
  --tool-lifecycle TOOL_LIFECYCLE_TRACE.jsonl \
  --agent-run-integration V4_AGENT_RUN_INTEGRATION_REPORT.json \
  --trajectory-store TRAJECTORY_STORE_INTEGRITY_REPORT.json \
  --export-quality EXPORT_QUALITY_DIR \
  --cards CARD_DIR \
  --command-log ACCEPTANCE_COMMAND_LOG_INPUT.jsonl \
  --pre-acceptance-doc docs/v4/implementation-plan.md \
  --pre-acceptance-doc docs/v4/review/implementation-plan-review.md \
  --output runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/v4_acceptance_inputs.json \
  --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-rollout-queue RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-rollout-leases RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-rollout-retry RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-rollout-budget RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-resource-locks RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-resource-usage RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-rollout-resume RUN_OR_QUEUE_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-run-selection-query RUN_SELECTION_QUERY_REPORT.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-task-freeze TASK_FREEZE_MANIFEST.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-task-validity TASK_VALIDITY_REPORT.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-tool-contract SELECTED_RUN_DIR --assert-frozen
PATH=.venv/bin:$PATH repo-harness inspect-v4-tool-lifecycle SELECTED_RUN_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-agent-run-integration SELECTED_RUN_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-trajectory-store SELECTED_RUN_DIR --assert-readable
PATH=.venv/bin:$PATH repo-harness inspect-v4-export-quality EXPORT_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-cards CARD_DIR --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-contamination-scan CONTAMINATION_SCAN_REPORT.json --assert-clean
PATH=.venv/bin:$PATH repo-harness build-v4-acceptance-report --acceptance-inputs runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/v4_acceptance_inputs.json --output runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/acceptance/v4_acceptance_report.json --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness build-v4-acceptance-bundle --acceptance-report runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/acceptance/v4_acceptance_report.json --output runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/acceptance/acceptance_bundle_manifest.json --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-YYYYMMDDTHHMMSSZ/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

如果 full `pytest` 受时间限制无法在每个开发阶段运行，阶段验收可以先运行对应单元测试和集成测试；final acceptance 前必须运行完整测试或记录明确阻塞事实。`inspect-v4-acceptance` 必须递归复核所有通过 `v4_acceptance_inputs.json` 或 acceptance bundle 绑定的机器产物 path、sha256、schema version、role ref 和 command log lineage，不能只检查 acceptance report 顶层字段。

## 13. 阶段顺序和退出门

| 阶段 | 名称 | 必须完成后才能进入下一阶段的退出门 |
| --- | --- | --- |
| 0 | 基线确认和输入冻结 | V3 inspect 通过，V4 implementation input manifest 可复核 |
| 1 | Schema / inspect / acceptance skeleton | P0、P1-2、P1-4 schema 和 inspect 命令都有正例与负例 |
| 2 | Task source freeze 和 adapter integration | 至少 8 个 task definitions 通过 accepted / auditable task validity inspect，其中至少 4 个来自 V4 PR / issue 构造流程 |
| 3 | Rollout orchestration | queue、lease、retry、budget control、resource lock、resume、checkpoint state、resource usage、run selection query 都能 inspect |
| 4 | P1-2 audit-only trace | permission trace、tool lifecycle trace、hook audit report 都能 inspect，且无模型可见污染 |
| 5 | Agent run 集成 | V4 task 能通过 queue 产生可审计 run，`v4_agent_run_integration_report.json` 可 inspect，final verifier 单向边界成立 |
| 6 | Export quality | sample tiers、failure dataset、packing、reward audit、patch quality、test-overfitting risk audit 都能 inspect |
| 7 | P1-4 cards | dataset card、run card、export card 和 repro command index 都能 inspect |
| 8 | Final acceptance | V2/V3 regression、V4 P0、P1-2、P1-4 和 acceptance bundle 全部通过 |

若任一阶段未通过，不应靠降低污染规则或放宽 final verifier 权威性继续推进。可以使用 diagnostic-only、quarantined、rejected 或 skipped_with_reason 降级，但降级样本不能计入 accepted / auditable 最低数量。

## 14. 本阶段明确不完成清单

implementation log 和 final acceptance report 必须继续明确以下能力本阶段不完成：

- 完整 provider / scaffold / budget 评测矩阵。
- `provider_eval_matrix_report.json`
- `provider_compare_scope.json`
- `scaffold_comparison_report.json`
- `scaffold_quality_metrics.json`
- `per_scaffold_export_quality.jsonl`
- context strategy comparison。
- `context_strategy_registry.json`
- `context_strategy_comparison_report.json`
- `context_replacement_trace.jsonl`
- `project_context_snapshot.json`
- `session_continuation_manifest.json`
- Frozen MCP snapshot。
- 代码检索专项评测。
- 受控只读子代理和 sidechain transcript。
- prompt injection / instruction conflict diagnostic tasks。
- 完整 Claude Code / Codex 产品式 hook 系统。
- 分布式强化学习 rollout 集群。
- 强化学习算法训练。
- reward model 训练。
- 完整 SWE-Bench Lite / SWE-Bench Verified 榜单复现。
- 生产级安全沙箱。

## 15. 实施日志和审查要求

每个阶段完成后，建议新增一份 implementation log：

```text
docs/v4/implementation-log/01-schema-and-inspect.md
docs/v4/implementation-log/02-task-freeze-and-adapters.md
docs/v4/implementation-log/03-rollout-orchestration.md
docs/v4/implementation-log/04-tool-lifecycle-audit.md
docs/v4/implementation-log/05-agent-run-integration.md
docs/v4/implementation-log/06-export-quality.md
docs/v4/implementation-log/07-cards.md
docs/v4/implementation-log/08-final-acceptance.md
```

每个阶段进入下一阶段前应安排只读审查，至少覆盖：

- 范围一致性。
- 训练数据和污染边界。
- 工程可执行性。
- 验收和 negative test 覆盖。
- 任务数据 freeze 和 source materialization 可复现性。

P1 / P2 范围扩张必须被记录为 P2 或 P3 风险，不能在没有用户明确确认和 scope 更新的情况下进入本阶段实施。

## 16. 最终完成定义

V4 可以认为进入 final acceptance 完成状态，必须同时满足：

1. V3 baseline inspect 通过。
2. 完整测试或最终验收要求的测试矩阵通过。
3. 至少 8 个 accepted / auditable task definitions 通过 inspect。
4. 至少 4 个 accepted / auditable task definitions 来自 V4 PR / issue 构造流程。
5. 单机 rollout queue、lease、retry、budget control、resource lock、resource usage、batch resume、checkpoint state 和 run selection query 通过 inspect。
6. task freeze、source materialization、baseline verifier、post-patch verifier、flaky detection 和 task validity 通过 inspect。
7. agent run integration 通过 inspect，证明 completed / interrupted / crashed run facts、RunSpec 元数据、final verifier 单向边界和 PreparedMessages / export observation 绑定成立。
8. P1-2 permission trace、tool lifecycle trace、hook audit-only facts 通过 inspect。
9. P0-3 export quality、sample tiers、failure dataset、packing、reward audit、patch quality、test-overfitting risk audit 通过 inspect。
10. P1-4 dataset card、run card、export card、provenance summary、contamination scan summary、repro command index 通过 inspect。
11. trainable payload 污染扫描通过。
12. `preference_pair_baseline_blocked` / `no_trainable_preference_pair` 得到明确处理：要么产生合规 trainable preference pair，要么生成 blocked pair report。
13. RUN_SELECTION_MANIFEST 显式绑定 selected run refs / role refs。
14. ACCEPTANCE_INPUTS 或 acceptance bundle 显式绑定 P0、P1-2、P1-4 机器产物。
15. final verifier 权威性、evaluator-only evidence 隔离、PreparedMessages 与 export observation 绑定继续成立。
16. 文档和 cards 没有声称训练了 coding agent、复现了公开 leaderboard、实现了生产级安全沙箱或完整 Claude Code / Codex 产品。
