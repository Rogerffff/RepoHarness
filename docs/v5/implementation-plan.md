# RepoHarness V5 Implementation Plan

## 0. 文档定位

本文把 `docs/v5/scope-and-roadmap.md` 和 `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md` 中已经收敛的 V5 范围，转化为可以逐阶段实现、逐阶段验收、逐阶段审查的工程实施计划。

V5 的目标不是新增一个宽泛的大版本，也不是复刻 Claude Code、Codex、OpenHands、SWE-agent 或官方 SWE-Bench harness。V5 的目标是在 V4 已经具备的可执行、可审计、可导出闭环之上，交付一个面向简历和面试展示的最终结果包。这个结果包必须让面试官能清楚看到：

1. 任务来自真实或半真实软件工程场景，而不是只来自玩具 fixture。
2. 每条真实 agent run 都有固定任务、固定源码、固定 verifier、固定工具策略和可追溯 trajectory。
3. provider、scaffold 和 budget 的比较只在受控变量一致时成立，不混用不同任务、不同 verifier 或不同运行条件。
4. 训练导出样本能够区分 trainable、diagnostic-only、blocked、mock / replay 和 stress records。
5. 所有关键结论都能通过 path、sha256、command log、inspect 命令和 acceptance bundle 追溯。

本文不是 V5 已经完成的声明。本文也不把当前 preflight 产物直接升级为最终 accepted task、真实 provider run 或训练样本。当前 preflight 产物只能作为 V5 implementation 的输入证据，必须被 V5 schema、inspect、acceptance inputs 和 acceptance bundle 重新绑定后，才能计入 V5 最终验收。

## 1. 前置输入和当前决策

### 1.1 范围输入

V5 implementation 以以下文档为范围输入：

- `docs/v5/scope-and-roadmap.md`
- `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md`
- `docs/v5/review/scope-review.md`
- `docs/v5/review/task-source-feasibility-and-run-matrix-preflight-plan-review.md`
- `docs/v4/implementation-plan.md`
- `docs/v4/swe-task-feasibility-experiment-plan.md`
- `docs/v4/pr-issue-task-source-plan.md`
- `docs/12-resume-narrative-and-demo-artifacts.md`
- `docs/13-agentic-technical-report-reading-map.md`

范围冲突时，优先级为：

1. 当前 V4 closure baseline 的机器证据和 inspect 结果。
2. `docs/v5/scope-and-roadmap.md` 中定义的 `core_acceptance`、`resume_ready_acceptance` 和 blocked claims 规则。
3. V5 task source feasibility 和 run matrix preflight 的机器产物。
4. V5 review 记录中的已处理问题和仍需保留的风险边界。
5. V1 到 V4 历史设计文档。

### 1.2 V4 closure baseline

V5 实施前必须确认 V4 最新 closure baseline 仍然成立。V5 范围文档指定的 V4 closure commit 为：

```text
e0da89c test: refresh V4 acceptance evidence after hardening
```

Stage 0 必须执行并记录以下命令：

```bash
git merge-base --is-ancestor e0da89c HEAD
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable
```

如果任何命令失败，V5 implementation 不得继续扩大范围。必须先修复 V4 baseline 或生成结构化阻塞报告。

这些命令是 V5 preimplementation baseline gate，只能在 V5 修改 `src/`、`tests/` 或 V4 doc-sync bundle 已绑定文档之前，在可信工作区执行并记录。通过结果必须写入 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和对应 command log。V5 一旦开始实现并修改源码、测试或新版本文档，旧 V4 doc-sync acceptance bundle 的 `--assert-immutable` 检查不得再作为同一工作区的阶段门；如果确实需要重新运行该不可变检查，必须使用精确还原到 V4 doc-sync bundle 绑定字节的独立 worktree 或快照，并把结果作为 Stage 0 baseline proof 的补充证据绑定。

V4 latest acceptance bundle 必须使用文档同步后的 bundle：

```text
runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json
runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl
```

原始 `acceptance_bundle_manifest.json` 只能作为历史 bundle 记录，不能作为 V5 latest V4 baseline。原因是 doc-sync bundle 额外绑定了当前 `docs/v4/final-acceptance.md` 和 `docs/v4/walkthrough.md` 的最新哈希。

### 1.3 已完成的 V5 preflight 输入

当前已经完成 10 个候选的 source materialization、dependency probe、verifier execution、flaky probe、visibility probe 和初始 run matrix freeze。对应输入目录为：

```text
runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/
```

关键事实如下：

| 项目 | 当前事实 |
| --- | --- |
| 初始冻结候选数量 | 10 个 |
| PR / issue 候选 | 6 个 |
| SWE-Bench-like anchor 候选 | 4 个 |
| flaky probe | 10 / 10 stable，0 个 flaky suspected |
| visibility probe | passed，0 个 model-visible leak，0 个 share-safe violation |
| agent-run-ready | 10 个 |
| comparison-ready | 9 个 |
| provider comparison ready | 4 个 |
| scaffold comparison ready | 4 个 |
| budget comparison ready | 4 个 |
| planned matrix cells | 24 个 |
| 本轮是否执行真实 agent run | 否 |
| 本轮是否调用 provider API | 否 |

关键输入产物：

- `runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/reports/v5_flaky_probe_report_amended.json`
- `runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/v5_visibility_probe_summary.json`
- `runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/run_matrix/v5_run_matrix_preflight_manifest.json`
- `runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/run_matrix/v5_task_selection_preflight_report.json`
- `runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/run_matrix/v5_resume_claim_gate_preflight_report.json`
- `runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/manifests/v5_run_matrix_freeze_evidence_manifest.json`

### 1.4 当前进入 implementation plan 的决策

当前 10 个候选已经足够进入 V5 implementation plan，以及真实运行主线的前置开发工作。原因是它们满足以下实施启动条件：

1. 至少 6 个候选达到 agent-run-ready。
2. 至少 4 个候选达到 comparison-ready。
3. provider、scaffold、budget 三个比较轴各自至少有 2 个候选任务。
4. flaky probe 和 visibility probe 没有发现阻塞问题。
5. 已经有 demo-ready 候选和 backup 候选。

但是当前 10 个候选还没有满足 V5 `core_acceptance` 中的严格任务库存门：

```text
至少 12 个 accepted / auditable task definitions
至少 8 个 PR / issue flow tasks
至少 3 个 SWE-Bench-like anchor tasks
```

因此本文采用以下实施决策：

1. V5 可以立即基于 10 个初始候选编写 implementation plan，并启动 Stage 0、Stage 1 和 Stage 2A 的实现工作。
2. Stage 3 的 provider registry、credential gate、cost budget schema 和 provider smoke scaffold 可以提前开发，但不得把真实 run matrix 执行和 Stage 3 退出门建立在未完成的严格任务库存门之上。
3. 进入 Stage 3 真实 provider agent run matrix 前，必须补齐严格任务库存门，默认方式是再补 2 个 PR / issue 候选，并让它们通过与当前 10 个候选同样的 source materialization、dependency、verifier、flaky 和 visibility probe。
4. 如果后续明确决定把 V5 `core_acceptance` 的任务数量门从 `12 total / 8 PR-issue` 调整为 `10 total / 6 PR-issue`，必须先修改 `docs/v5/scope-and-roadmap.md` 和 preflight plan，并生成 review 记录；不能只在 implementation plan 中悄悄降低标准。

## 2. V5 实施不变量

### 2.1 证据时序不变量

V5 evidence integrity 必须分成三层：

1. `pre_acceptance_evidence_integrity`：只检查 V5 acceptance inputs 生成之前已经存在的 evidence。
2. `acceptance_report_reference_integrity`：由 `inspect-v5-acceptance` 在 acceptance report 生成之后检查。
3. `acceptance_bundle_command_lineage_integrity`：由 `inspect-acceptance-bundle --assert-immutable` 在 acceptance bundle 构建之后检查。

不得让 `v5_pre_acceptance_evidence_integrity_report.json` 预先引用尚未生成的 V5 acceptance report。不得让 V5 acceptance report 把 post-report inspect outputs 或 bundle final outputs 当作自己的输入证据。

### 2.2 可见性和污染边界不变量

以下内容不得进入 adapter-visible task input、prepared messages、model-visible transcript、trainable payload、public-safe demo bundle 或 final acceptance docs：

- evaluator-only evidence。
- gold patch。
- raw test patch。
- hidden test selector。
- official harness report。
- official resolved status。
- raw PR body。
- raw PR diff。
- review comment。
- fix commit URL。
- merge commit URL。
- provider raw request。
- provider raw response。
- Authorization marker。
- provider credential marker。
- credential path。
- final verifier raw output。
- reward scalar。
- reward label。
- post-patch passing log。
- Claude / Codex / LLM coding session URL。

Reward scalar 和 reward label 只能出现在非模型可见的 structured reward、RewardMetadata 或 audit-only metadata 字段中，并且必须通过 allowlist path 和 visibility policy 检查。

### 2.3 final verifier 权威性不变量

Final verifier 是 accepted、rejected、inconclusive 和 pass-to-pass regression 的权威来源。Patch quality、reward audit、LLM judge audit-only note、failure taxonomy、demo card 和 result summary 都不能把 final verifier 未接受的 run 提升为 accepted。

### 2.4 provider / scaffold / budget 比较不变量

任何比较结论都必须声明：

- `comparison_axis`
- `controlled_variables`
- `compared_cells`
- `comparison_validity`

Provider 比较必须固定 task、source tree、final verifier plan、tool policy、context policy、scaffold、budget 和 environment id。Scaffold 比较必须固定 task、source tree、final verifier plan、tool policy、context policy、provider、budget 和 environment id。Budget 比较必须固定 task、source tree、final verifier plan、tool policy、context policy、provider、scaffold 和 environment id。

Mock、replay、fallback success、credential missing skip、adapter not implemented skip 和 cost-limited structured skip 都不得混入真实 provider accepted rate。

### 2.5 简历声明门不变量

V5 使用两层验收：

1. `core_acceptance`：证明 V5 工程闭环、证据完整性、任务冻结、最小真实运行、训练导出和 acceptance bundle 成立。
2. `resume_ready_acceptance`：在 `core_acceptance` 基础上，额外证明多真实 provider、真实可比较 preference pair、share-safe demo bundle 和 canonical demo walkthrough 支撑强简历表述。

如果只通过 `core_acceptance`，最终文档和简历不得使用以下表述：

- `multi-provider agent runs`
- `controlled multi-provider comparison`
- `preference export completed`
- `interview-grade evaluation pack` 的完整强表述
- `resumable export stress tests`

这些表述是否允许使用，必须由 `v5_resume_claim_gate_report.json` 决定。

## 3. 代码和文档落点

V5 应尽量沿用 V4 和现有模块边界，避免大规模重命名。建议新增或扩展的模块如下：

```text
src/repo_harness/
  schema_versions.py
  cli/
    main.py
  v5_evidence.py
  v5_task_set.py
  v5_run_matrix.py
  v5_provider_gate.py
  v5_export_pack.py
  v5_demo_artifacts.py
  v5_acceptance.py
  tasks/
    adapter.py
    source_freeze.py
    visibility.py
  model_client/
    factory.py
    schemas.py
    providers/
      deepseek.py
      openai.py
      anthropic.py
  scaffolds/
    registry.py
    simple_react.py
    planner_coder_verifier.py
  evaluation/
    runner.py
    schemas.py
  rollout/
    queue.py
    worker.py
  export/
    exporter.py
    audit.py
    pairing.py
  reward/
    schemas.py
  run_metadata/
    reader.py
    writer.py
```

如果实现时发现新增 `v5_*` 模块会造成过度拆分，可以把能力放在已有模块中，但必须保留 V5 schema version、inspect 命令、fixture、negative tests、implementation log 和 acceptance inputs 绑定。

### 3.1 CLI / Python API 落地表

V5 的每个关键机器产物都必须有明确 builder。Builder 不得扫描 latest run，不得覆盖已有输出；除非命令名明确是 `update` 或 `append`，默认都必须支持 `--fail-if-output-exists`。

| 阶段 | CLI 命令 | Python API 建议入口 | 关键输入 | 关键输出 | 覆盖策略 | 测试入口 |
| --- | --- | --- | --- | --- | --- | --- |
| Stage 0 | `repo-harness build-v5-preimplementation` | `repo_harness.v5_evidence.build_preimplementation_inputs` | V2 / V3 / V4 acceptance refs、V5 preflight refs | `v5_baseline_check_report.json`、`v5_preflight_input_binding.json`、`v5_preimplementation_command_log.jsonl` | `--fail-if-output-exists` | `tests/unit/test_v5_evidence_integrity.py`、`tests/integration/test_v5_acceptance.py` |
| Stage 1 | `repo-harness build-v5-schema-fixtures` | `repo_harness.v5_evidence.build_schema_fixtures` | schema registry、fixture root | valid fixtures、negative fixtures、`v5_artifact_inspect_tracking_table.json` | `--fail-if-output-exists` | `tests/unit/test_v5_evidence_integrity.py` |
| Stage 1 | `repo-harness build-v5-evidence-integrity` | `repo_harness.v5_evidence.build_pre_acceptance_integrity_report` | critical evidence manifest、pre-acceptance command log | `v5_pre_acceptance_evidence_integrity_report.json` | `--fail-if-output-exists` | `tests/unit/test_v5_evidence_integrity.py` |
| Stage 2 | `repo-harness build-v5-task-set` | `repo_harness.v5_task_set.build_task_set_manifest` | preflight input binding、adapter-visible task drafts、evaluator-only manifest | `v5_task_set_manifest.json`、`v5_task_inventory_report.json`、`v5_task_visibility_scan_report.json` | `--fail-if-output-exists` | `tests/unit/test_v5_task_set.py`、`tests/integration/test_v5_task_freeze.py` |
| Stage 2B | `repo-harness build-v5-supplemental-pr-issue-candidates` | `repo_harness.v5_task_set.build_supplemental_pr_issue_candidates` | candidate inventory、default supplement list、output root | supplemental probe reports、supplemental task refs | `--fail-if-output-exists` | `tests/unit/test_v5_task_set.py` |
| Stage 2B | `repo-harness merge-v5-task-set` | `repo_harness.v5_task_set.merge_task_set_manifests` | initial task set、supplemental accepted tasks | merged `v5_task_set_manifest.json`、merged inventory | `--fail-if-output-exists` | `tests/unit/test_v5_task_set.py` |
| Stage 3 | `repo-harness build-v5-provider-gate` | `repo_harness.v5_provider_gate.build_provider_gate_report` | provider registry config、credential presence facts | `v5_provider_registry_report.json`、`v5_provider_credential_gate_report.json` | `--fail-if-output-exists` | `tests/unit/test_v5_provider_gate.py` |
| Stage 3 | `repo-harness build-v5-provider-cost-budget` | `repo_harness.v5_provider_gate.build_cost_budget_report` | provider gate、budget config | `v5_provider_cost_budget_report.json` | `--fail-if-output-exists` | `tests/unit/test_v5_provider_gate.py` |
| Stage 3 | `repo-harness build-v5-run-matrix` | `repo_harness.v5_run_matrix.build_run_matrix_manifest` | task set、provider gate、scaffold registry、budget policies | `v5_run_matrix_manifest.json`、planned matrix cells | `--fail-if-output-exists` | `tests/unit/test_v5_run_matrix.py` |
| Stage 3 | `repo-harness run-v5-run-matrix` | `repo_harness.v5_run_matrix.run_matrix_cells` | run matrix manifest、provider budget report | `v5_matrix_cell_results.jsonl`、run dirs、trajectory refs | resumable with explicit queue state; no silent overwrite | `tests/integration/test_v5_provider_run_matrix.py` |
| Stage 3 | `repo-harness build-v5-comparison-reports` | `repo_harness.v5_run_matrix.build_comparison_reports` | matrix cell results、controlled variables refs | provider / scaffold / budget comparison reports | `--fail-if-output-exists` | `tests/unit/test_v5_run_matrix.py` |
| Stage 4 | `repo-harness build-v5-export-pack` | `repo_harness.v5_export_pack.build_export_result_pack` | accepted runs、trajectory refs、final verifier boundaries | SFT、RL rollout、preference or blocked report、failure dataset、export manifest | `--fail-if-output-exists` | `tests/unit/test_v5_export_pack.py`、`tests/integration/test_v5_export_pack.py` |
| Stage 5 | `repo-harness build-v5-demo-artifacts` | `repo_harness.v5_demo_artifacts.build_demo_artifacts` | task set、run matrix results、export pack、claim gate | demo card、walkthrough、public-safe bundle、result summary | `--fail-if-output-exists` | `tests/unit/test_v5_demo_artifacts.py` |
| Stage 5 | `repo-harness build-v5-interview-result-pack` | `repo_harness.v5_demo_artifacts.build_interview_result_pack` | demo artifacts、resume claim gate、docs/12 mapping | result pack manifest、resume bullets、interview Q&A evidence | `--fail-if-output-exists` | `tests/unit/test_v5_demo_artifacts.py` |
| Stage 6 | `repo-harness build-v5-acceptance-inputs` | `repo_harness.v5_acceptance.build_acceptance_inputs` | all pre-acceptance evidence refs | `v5_acceptance_inputs.json` | `--fail-if-output-exists` | `tests/unit/test_v5_acceptance.py` |
| Stage 6 | `repo-harness build-v5-acceptance-report` | `repo_harness.v5_acceptance.build_acceptance_report` | V5 acceptance inputs | `v5_acceptance_report.json` | `--fail-if-output-exists` | `tests/unit/test_v5_acceptance.py` |
| Stage 6 | `repo-harness build-v5-acceptance-bundle` | `repo_harness.v5_acceptance.build_acceptance_bundle` | acceptance report、post-report inspect output、pre-bundle command log、docs refs | `v5_acceptance_bundle_manifest.json` | `--fail-if-output-exists` | `tests/integration/test_v5_acceptance.py` |
| Stage 6 doc sync | `repo-harness build-v5-acceptance-bundle --doc-sync-from-bundle V5_ACCEPTANCE_BUNDLE` | `repo_harness.v5_acceptance.build_doc_sync_bundle` | previous V5 bundle、updated final docs、doc-sync command log | doc-sync acceptance bundle manifest、doc-sync final command log | `--fail-if-output-exists` | `tests/integration/test_v5_acceptance.py` |

每个 builder 的最低实现要求：

- 输入必须全部显式传入路径，不能隐式读取 latest run。
- 输出目录必须由 `--output-dir` 或 `--output` 显式指定。
- 输出已经存在时默认失败。
- 命令必须写入 command log entry，包含 argv、cwd、input_refs、output_refs、started_at、finished_at、exit_code、stdout / stderr sha256。
- 对应 inspect 命令必须能在不重新执行 builder 的情况下检查输出。

建议新增测试文件：

```text
tests/unit/test_v5_evidence_integrity.py
tests/unit/test_v5_task_set.py
tests/unit/test_v5_task_visibility.py
tests/unit/test_v5_provider_gate.py
tests/unit/test_v5_run_matrix.py
tests/unit/test_v5_export_pack.py
tests/unit/test_v5_demo_artifacts.py
tests/unit/test_v5_acceptance.py
tests/integration/test_v5_task_freeze.py
tests/integration/test_v5_provider_run_matrix.py
tests/integration/test_v5_export_pack.py
tests/integration/test_v5_acceptance.py
tests/fixtures/v5/
```

建议新增文档：

```text
docs/v5/implementation-plan.md
docs/v5/implementation-log/00-baseline-and-preflight-freeze.md
docs/v5/implementation-log/01-schema-and-evidence-integrity.md
docs/v5/implementation-log/02-task-set-freeze.md
docs/v5/implementation-log/03-provider-scaffold-budget-matrix.md
docs/v5/implementation-log/04-export-result-pack.md
docs/v5/implementation-log/05-demo-artifacts.md
docs/v5/implementation-log/06-final-acceptance.md
docs/v5/final-acceptance.md
docs/v5/walkthrough.md
docs/v5/review/implementation/
```

## 4. 阶段 0：V4 closure baseline 和 V5 preflight 输入冻结

### 4.1 目标

确认 V4 closure baseline 可信，并把当前 V5 preflight 产物冻结为 implementation input。这个阶段不运行 agent，不调用 provider API，不生成 V5 accepted task，只做输入可信度和文档同步。

### 4.2 主要工作

1. 在 V5 修改源码、测试或 V4 doc-sync bundle 已绑定文档之前，执行一次 V2、V3、V4 baseline inspect 和 bundle inspect。
2. 生成 `v5_baseline_check_report.json`，记录命令、exit code、stdout / stderr sha256、当前 HEAD 和 V4 closure baseline。
3. 生成 `v4_review_findings_closure_report.json`，逐项绑定 V4 修复前 finding、修复 commit、重新生成 evidence、inspect 命令和最新 acceptance bundle。
4. 生成 `v5_documentation_sync_report.json`，检查项目入口文档是否仍然把 V4 描述为待修复状态，是否仍引用旧 V4 acceptance 路径，是否已经纳入 V5 文档入口。
5. 生成 `v5_preflight_input_binding.json`，绑定当前 10 候选 preflight 产物的 path、sha256、size_bytes、schema_version、producer command 和 visibility。
6. 明确当前 10 候选只是 `initial_10_candidate_batch`，不能直接宣称满足 `12 total / 8 PR-issue`。

### 4.3 建议机器产物

- `v5_baseline_check_report.json`
- `v4_review_findings_closure_report.json`
- `v5_documentation_sync_report.json`
- `v5_preflight_input_binding.json`
- `v5_preimplementation_command_log.jsonl`

### 4.4 必须实现或扩展的 inspect 命令

```bash
repo-harness inspect-v5-preimplementation V5_PREFLIGHT_INPUT_BINDING --assert-complete
```

### 4.5 验收和 negative tests

通过条件：

- `e0da89c` 是当前 HEAD 的祖先。
- V2、V3、V4 acceptance inspect 和 bundle inspect 已在 Stage 0 preimplementation baseline 上全部通过，并由 `v5_baseline_check_report.json` 绑定。
- `v5_preflight_input_binding.json` 显式绑定当前 10 候选 preflight 产物。
- input binding 中的所有 artifact path 存在，sha256 匹配。
- input binding 清楚标记 `full_v5_threshold_status=partial_below_12_total_and_8_pr_issue_preflight_threshold`。
- `v5_documentation_sync_report.json` 不把 V4 旧 acceptance 目录写成最新 baseline。

负例：

- input binding 引用不存在的 preflight artifact 时失败。
- input binding 引用旧的未修正 verifier execution 报告时失败。
- sha256 不匹配时失败。
- 把当前 10 候选写成已经满足 `12 total / 8 PR-issue` 时失败。
- 文档同步报告未覆盖 `docs/00-reading-guide.md`、`docs/01-project-positioning-and-requirements.md`、`docs/12-resume-narrative-and-demo-artifacts.md` 和 `docs/v4/final-acceptance.md` 时失败。
- 文档同步报告未覆盖 `README.md` 或 `AGENTS.md` 时失败。

## 5. 阶段 1：V5 schema、inspect skeleton 和 evidence integrity gate

### 5.1 目标

先定义 V5 的机器产物契约，再实现业务逻辑。V5 每个会进入 final acceptance 的产物都必须有 schema、inspect 命令、正例 fixture、负例 fixture和 artifact tracking table。

### 5.2 主要工作

1. 新增 V5 schema version 常量。
2. 定义 `V5EvidenceRef`。
3. 定义 `V5CriticalEvidenceClass`。
4. 定义 `V5PreAcceptanceEvidenceIntegrityReport`。
5. 定义 `V5TaskSetManifest`、`V5TaskInventoryReport`、`V5TaskVisibilityScanReport`。
6. 定义 `V5RunMatrixManifest`、`V5ProviderCredentialGateReport`、`V5ProviderCostBudgetReport`、`V5MatrixCellResult`、`V5MatrixCompareScopeReport`。
7. 定义 `V5ExportResultPackManifest`、`V5RewardSourceTaxonomyReport`、`V5FailureTaxonomyReport`、`V5PreferencePairBlockedReport`。
8. 定义 `V5ResumeArtifactIndex`、`V5ResultSummaryTable`、`V5PublicDemoBundleManifest`、`V5DemoTranscriptIndex`。
9. 定义 `V5AcceptanceInputs`、`V5AcceptanceReport` 和 V5 acceptance bundle 扩展。
10. 实现 inspect 命令骨架。
11. 维护 `v5_artifact_inspect_tracking_table.json`。

### 5.2.1 Schema 字段级契约

Stage 1 必须先落地字段级 schema 契约，不能只定义类名。每个 schema 都必须有 required fields、枚举值、跨字段约束、valid fixture 和 negative fixture。下面是最小契约表；实现时可以增加字段，但不能删除这些字段。

| Schema | Required fields | 稳定枚举 / 关键约束 | Fixture |
| --- | --- | --- | --- |
| `V5EvidenceRef` | `path`、`sha256`、`size_bytes`、`kind`、`purpose`、`visibility`、`share_safe`、`producer_command`、`producer_stage`、`inspect_command` | `visibility` 必须是 `model_visible`、`trainable`、`diagnostic_only`、`audit_only`、`evaluator_only`、`public_safe` 之一；`share_safe=true` 时不得引用 evaluator-only 或 provider raw artifact。 | `tests/fixtures/v5/evidence_ref_valid.json`、`tests/fixtures/v5/evidence_ref_sha256_mismatch.json` |
| `V5AcceptanceInputs` | `schema_version`、`created_at`、`current_head`、`v2_acceptance_report_ref`、`v3_acceptance_report_ref`、`v3_acceptance_bundle_ref`、`v4_acceptance_inputs_ref`、`v4_acceptance_report_ref`、`v4_doc_sync_acceptance_bundle_ref`、`v4_doc_sync_final_command_log_ref`、`v5_evidence_refs`、`stress_test_executed` | V4 bundle 必须指向 doc-sync bundle；不得包含 post-report inspect outputs 或 bundle final outputs。 | `tests/fixtures/v5/acceptance_inputs_valid.json`、`tests/fixtures/v5/acceptance_inputs_post_report_leak.json` |
| `V5AcceptanceReport` | `schema_version`、`acceptance_inputs_ref`、`core_acceptance.status`、`core_acceptance.required_checks`、`resume_ready_acceptance.status`、`resume_ready_acceptance.required_checks`、`allowed_claims`、`blocked_claims`、`claim_gate_report_ref`、`acceptance_report_reference_integrity.expected_check` | `core_acceptance.status` 和 `resume_ready_acceptance.status` 必须是 `passed`、`failed`、`blocked` 之一；`acceptance_report_reference_integrity.expected_check` 只能描述待检集合，不能引用 post-report integrity report。 | `tests/fixtures/v5/acceptance_report_valid_core.json`、`tests/fixtures/v5/acceptance_report_references_post_report_output.json` |
| `V5ProviderCredentialGateReport` | `schema_version`、`provider_families`、`credential_status_by_provider`、`adapter_status_by_provider`、`structured_skips`、`raw_secret_value_present`、`provider_raw_content_policy` | provider family 至少覆盖 `openai`、`deepseek`、`anthropic_claude`；credential status 必须是 `present`、`missing`、`not_configured`；adapter status 必须是 `primary_supported`、`fallback_only`、`adapter_not_implemented`。 | `tests/fixtures/v5/provider_gate_valid.json`、`tests/fixtures/v5/provider_gate_secret_leak.json` |
| `V5ProviderCostBudgetReport` | `max_real_provider_calls`、`max_cost_usd`、`cost_proxy_formula`、`actual_real_provider_calls`、`actual_cost_proxy_usd`、`cost_limited_structured_skip`、`budget_exhausted_before_run` | `actual_real_provider_calls <= max_real_provider_calls`；`actual_cost_proxy_usd <= max_cost_usd`；超过预算后的 matrix cell 必须 structured skip。 | `tests/fixtures/v5/provider_cost_budget_valid.json`、`tests/fixtures/v5/provider_cost_budget_overrun.json` |
| `V5RunMatrixManifest` | `schema_version`、`task_set_ref`、`provider_gate_ref`、`provider_cost_budget_ref`、`planned_matrix_cells`、`controlled_variables_refs`、`comparison_axes`、`agent_run_started`、`provider_api_called` | 每个 comparison axis 至少声明 `provider`、`scaffold`、`budget` 或 `diagnostic_baseline`；planned cell 不等于实际 accepted run。 | `tests/fixtures/v5/run_matrix_valid.json`、`tests/fixtures/v5/run_matrix_missing_controlled_variables.json` |
| `V5MatrixCellResult` | `task_id`、`provider_id`、`provider_mode`、`normalized_provider_status`、`scaffold_id`、`budget_policy_id`、`tool_policy_id`、`context_policy_id`、`environment_id`、`source_tree_hash`、`run_id`、`run_dir`、`final_verifier_status`、`trajectory_ref`、`final_verifier_boundary_ref`、`controlled_variables_ref` | `normalized_provider_status` 必须是 `primary_attempted`、`credential_missing_skip`、`adapter_not_implemented_skip`、`cost_limited_structured_skip`、`fallback_success`、`provider_error` 之一；`fallback_success` 不得计入 primary accepted rate。 | `tests/fixtures/v5/matrix_cell_valid.json`、`tests/fixtures/v5/matrix_cell_fallback_marked_primary.json` |
| `V5ExportResultPackManifest` | `schema_version`、`sft_export_ref`、`rl_rollout_export_ref`、`failure_dataset_ref`、`preference_pair_export_ref` 或 `preference_pair_blocked_report_ref`、`partition_counts`、`reward_source_taxonomy_ref`、`failure_taxonomy_ref`、`export_audit_ref` | `partition_counts` 必须包含 `real_provider_trainable_records`、`mock_or_replay_records`、`diagnostic_records`、`blocked_records`、`synthetic_safe_stress_records`；diagnostic 和 blocked 样本不得计入 trainable。 | `tests/fixtures/v5/export_pack_valid.json`、`tests/fixtures/v5/export_pack_missing_blocked_partition.json` |
| `V5ResumeClaimGateReport` | `schema_version`、`stage`、`allowed_claims`、`blocked_claims`、`blocking_reasons`、`provider_claim_status`、`preference_pair_claim_status`、`demo_share_safe_status`、`stress_test_claim_status`、`source_reports` | `stage` 必须是 `stage3_partial`、`stage4_partial`、`stage5_final`、`acceptance_final` 之一；final acceptance 只能引用 `stage5_final` 或 `acceptance_final`。 | `tests/fixtures/v5/claim_gate_valid_final.json`、`tests/fixtures/v5/claim_gate_allows_blocked_provider.json` |
| `V5InterviewResultPackManifest` | `schema_version`、`demo_card_ref`、`walkthrough_ref`、`result_summary_ref`、`resume_templates_ref`、`resume_bullets_ref`、`interview_qa_evidence_ref`、`public_safe_mapping_ref` | 所有 refs 必须 `share_safe=true`；不得引用 provider raw request / response 或 evaluator-only evidence。 | `tests/fixtures/v5/interview_result_pack_valid.json`、`tests/fixtures/v5/interview_result_pack_raw_provider_leak.json` |

所有 negative fixture 都必须由对应 inspect 命令拒绝。Schema 字段名一旦进入 fixture，不得在后续阶段随意改名；如果确实需要重命名，必须同步更新 schema version、fixtures、inspect、builder、implementation log 和 review 记录。

### 5.3 必须覆盖的 inspect 命令

```bash
repo-harness inspect-v5-preimplementation V5_PREFLIGHT_INPUT_BINDING --assert-complete
repo-harness inspect-v5-evidence-integrity V5_PRE_ACCEPTANCE_EVIDENCE_INTEGRITY_REPORT --assert-complete
repo-harness inspect-v5-task-set V5_TASK_SET_MANIFEST --assert-complete
repo-harness inspect-v5-task-visibility V5_TASK_VISIBILITY_SCAN_REPORT --assert-clean
repo-harness inspect-v5-run-matrix V5_RUN_MATRIX_MANIFEST --assert-complete
repo-harness inspect-v5-provider-gate V5_PROVIDER_CREDENTIAL_GATE_REPORT --assert-consistent
repo-harness inspect-v5-export-pack V5_EXPORT_RESULT_PACK_MANIFEST --assert-clean
repo-harness inspect-v5-demo-artifacts V5_RESUME_ARTIFACT_INDEX --assert-share-safe
repo-harness inspect-v5-inputs V5_ACCEPTANCE_INPUTS --assert-complete
repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-core-complete
repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-resume-ready
```

如果保留 `inspect-v5-acceptance --assert-complete`，它必须等价于 `--assert-resume-ready`。不能让 `--assert-complete` 只检查 `core_acceptance`。

### 5.4 建议机器产物

- `v5_schema_tracking_table.json`
- `v5_artifact_inspect_tracking_table.json`
- `v5_pre_acceptance_evidence_integrity_report.json`
- `v5_unbound_evidence_negative_case_report.json`
- `v5_acceptance_lineage_schema_report.json`

### 5.5 验收和 negative tests

通过条件：

- 每个 V5 schema 都有 valid fixture。
- 每个进入 acceptance inputs 的产物都有 inspect 覆盖。
- inspect 命令必须显式接收输入路径，不得扫描 latest run。
- Evidence ref 必须记录 path、sha256、size_bytes、kind、purpose、visibility、producer_command、producer_stage 和 inspect_command。
- Acceptance report reference integrity 和 acceptance bundle command lineage 不被放入 pre-acceptance evidence integrity 的输入集合。

负例：

- evidence ref 缺少 sha256 时失败。
- evidence ref sha256 drift 时失败。
- acceptance report 引用 acceptance inputs 之外的 final verifier evidence 时失败。
- command log 中 `inspect-v5-acceptance` 指向旧 report 时失败。
- post-acceptance docs 被错误放入 acceptance report 输入时失败。
- trainable export record 引用没有 final verifier boundary 支撑的 outcome 时失败。

## 6. 阶段 2：V5 task subset freeze 和严格任务库存闭环

### 6.1 目标

把当前 preflight 中 10 个稳定候选转化为 RepoHarness V5 可执行、可审计、可验收的正式 task definitions，并在进入 Stage 3 真实 provider agent run matrix 前补齐 `12 total / 8 PR-issue / 3 SWE-Bench-like` 的严格任务库存门。

### 6.2 任务池策略

Stage 2 分成两个子阶段：

1. Stage 2A：接入当前 10 个初始冻结候选，优先保证 agent run、comparison proof 和 demo 能启动。
2. Stage 2B：补 2 个 PR / issue 候选，或者通过正式范围变更降低任务库存门。默认路径是补 2 个 PR / issue 候选。Stage 2B 不阻塞 provider registry、credential gate 和 cost budget schema 的开发，但阻塞 Stage 3 的真实 provider agent run matrix 退出门。

当前 10 个候选的内部映射、PR / issue 来源细节和 evaluator-only evidence 继续保留在 audit-only artifact 中。正式 adapter-visible task input 不得包含 PR URL、fix commit URL、raw PR body、raw PR diff、hidden selector、上游测试 patch 或 provider raw content。

### 6.3 主要工作

1. 定义 V5 task inventory schema。
2. 将当前 10 个候选的 sanitized task input 接入 V5 task adapter。
3. 把 evaluator-only evidence manifest 与 adapter-visible task input 显式隔离。
4. 复用 preflight source archive 和 dependency evidence，但必须在 V5 task set manifest 中重新绑定 path、sha256 和 producer command。
5. 为每个 task 生成 `task_id`、`task_family`、`source_kind`、`repo_url_or_archive_id`、`base_commit`、`source_archive_sha256`、`source_tree_hash`、`task_input_hash`、`adapter_visible_input_ref`、`evaluator_only_evidence_ref`、`baseline_verifier_plan_ref`、`final_verifier_plan_ref`、`fail_to_pass_evidence_ref`、`pass_to_pass_evidence_ref`、`flaky_probe_report_ref`、`license_provenance_ref`、`dependency_cache_ref`、`environment_stability_ref`、`contamination_scan_ref`、`visibility_scan_ref` 和 `task_diversity_ref`。
6. 生成 `v5_task_diversity_report.json`，统计语言、仓库规模、目标文件数量、测试类型、修改复杂度、任务难度和展示角色。
7. 生成 `v5_task_visibility_scan_report.json`，覆盖 adapter-visible input、candidate metadata 摘要、preflight manifest、command log 和 public-safe demo bundle 候选。
8. 补齐 2 个 PR / issue 候选时，必须重新执行 source materialization、dependency、baseline verifier、post-patch verifier、flaky probe 和 visibility probe。
9. 对无法稳定运行但有诊断价值的候选，标记为 `diagnostic_only` 或 `quarantined`，不得计入 accepted / auditable。

### 6.3.1 Stage 2B 补任务执行路径

Stage 2B 的默认目标是补齐 2 个 PR / issue accepted / auditable tasks，使任务库存达到 `12 total / 8 PR-issue / 3 SWE-Bench-like`。默认补位顺序如下：

1. `pallets/click#3364`
2. `python-attrs/attrs#1428`
3. `pypa/packaging#1124`
4. `hynek/structlog#620`
5. `chalk/chalk#335`
6. `sindresorhus/execa#1176`，如果前面候选不足并且依赖 probe 稳定。
7. `clap-rs/clap#6340`，只作为多样性 fallback，默认 diagnostic-first。

补位执行命令必须复用 V5 preflight 的同一条 probe 链路，而不是手工写入 task manifest：

```bash
PATH=.venv/bin:$PATH repo-harness build-v5-supplemental-pr-issue-candidates \
  --candidate-id pallets/click#3364 \
  --candidate-id python-attrs/attrs#1428 \
  --candidate-id pypa/packaging#1124 \
  --candidate-id hynek/structlog#620 \
  --source-preflight-root runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z \
  --output-dir runs/v5-stage2b-supplemental-pr-issue-YYYYMMDDTHHMMSSZ \
  --fail-if-output-exists
```

每个补位候选必须依次生成：

- source materialization report。
- source archive manifest。
- dependency probe report。
- baseline verifier probe report。
- post-patch verifier probe report。
- flaky probe report。
- adapter-visible denylist scan report。
- training export boundary probe report。
- provider raw content leak probe report。
- candidate command log。

补位成功规则：

- 取默认候选顺序中最早达到 `freeze_ready=true`、`agent_run_ready=true`、visibility counters 全为 0 的 2 个候选。
- 如果某个候选失败，必须记录 `failure_owner`、`failure_category`、stdout / stderr sha256 和替补原因，然后继续下一个候选。
- 如果默认列表跑完仍不足 2 个，才允许进入 GitHub candidate expansion，并记录 `github_discovery_query_log.jsonl`。
- 新增 2 个候选默认只用于补齐 accepted / auditable inventory 和 run matrix backup，不自动进入 provider / scaffold / budget 核心 comparison cells；除非 Stage 3 run matrix 显式重算并更新 controlled variables。

补位合并命令：

```bash
PATH=.venv/bin:$PATH repo-harness merge-v5-task-set \
  --base-task-set V5_INITIAL_10_TASK_SET_MANIFEST \
  --supplemental-report V5_STAGE2B_SUPPLEMENTAL_PR_ISSUE_REPORT \
  --output V5_TASK_SET_MANIFEST \
  --output-inventory V5_TASK_INVENTORY_REPORT \
  --fail-if-output-exists
```

合并后必须重新运行：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set V5_TASK_SET_MANIFEST --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility V5_TASK_VISIBILITY_SCAN_REPORT --assert-clean
```

`v5_task_set_manifest.json` 必须同时记录 initial 10 task refs、supplemental 2 task refs、每个 supplemental task 的 producer command 和是否进入 run matrix backup。Acceptance inputs 必须绑定 merged task set，而不是只绑定 initial 10 task set。

### 6.4 建议机器产物

- `v5_task_inventory_report.json`
- `v5_task_set_manifest.json`
- `v5_task_construction_report.json`
- `v5_swebench_like_subset_manifest.json`
- `v5_pr_issue_task_manifest.json`
- `v5_task_diversity_report.json`
- `v5_task_stability_report.json`
- `v5_task_visibility_scan_report.json`
- `v5_adapter_visible_task_input_manifest.json`
- `v5_evaluator_only_evidence_manifest.json`
- `v5_supplemental_pr_issue_candidate_report.json`

### 6.5 验收和 negative tests

通过条件：

- Stage 2A：当前 10 个候选全部进入 V5 task inventory，并保持 `initial_batch_freeze_ready` 状态。
- Stage 2B 或范围变更后：至少 12 个 task definitions 达到 accepted / auditable。
- Stage 2B 或范围变更后：至少 8 个 accepted / auditable task definitions 来自 PR / issue flow。
- 至少 3 个 accepted / auditable task definitions 来自 SWE-Bench-like anchors。
- 每个 accepted / auditable task 都有 fixed revision、source archive hash、source tree hash、task input hash、adapter-visible input hash、evaluator-only evidence hash、baseline verifier plan、final verifier plan、fail-to-pass evidence、pass-to-pass evidence、flaky probe evidence、license provenance ref、environment stability facts、dependency facts、contamination scan facts 和 visibility facts。
- `inspect-v5-task-set --assert-complete` 通过。
- `inspect-v5-task-visibility --assert-clean` 通过。

负例：

- gold patch 进入 adapter-visible input 时失败。
- raw test patch 进入 adapter-visible input 时失败。
- raw PR body、raw PR diff、review comment、fix commit URL、AI session URL 或 provider raw response 进入 adapter-visible input 时失败。
- official resolved status、hidden selector、verifier raw output、reward scalar 或 reward label 进入 trainable payload 时失败。
- source materialization 两次 source tree hash 不一致时失败。
- flaky probe 不稳定却标记 accepted 时失败。
- 当前 10 个候选被错误写成已经满足 `12 total / 8 PR-issue` 时失败。

## 7. 阶段 3：Provider registry、credential gate 和真实 run matrix

### 7.1 目标

在 RepoHarness agent loop 中执行真实 provider agent runs，并形成最小 provider / scaffold / budget comparison proof。Stage 3 是 V5 简历展示价值最高、风险也最高的阶段，必须把 provider credential、成本预算、structured skip、raw content redaction 和 comparison controlled variables 作为机器门处理。

### 7.2 provider 策略

当前代码事实是：

- `deepseek` 可以作为 primary real provider。
- `openai` 当前只允许作为 DeepSeek fallback smoke run，不能直接计入 primary provider comparison。
- `anthropic_claude` 需要进入 provider registry 和 credential gate；如果 adapter 尚未实现，只能记录 `adapter_not_implemented_skip`，不能计入真实 provider family。

V5 Stage 3 的默认实现策略是：

1. 先完成 provider registry 和 credential gate，不调用 provider API。
2. 执行低成本 provider smoke，验证 raw request / response redaction 和 structured skip。
3. 在 Stage 2B 严格任务库存门关闭后，让 DeepSeek 先产生至少 1 个真实 provider family 的实际 agent run evidence，满足 `core_acceptance` 的真实 provider 下限。
4. 如果 OpenAI 可以被实现为 primary provider 并通过 smoke，则用 OpenAI 作为第二个真实 provider family，争取 `resume_ready_acceptance` 的 multi-provider gate。
5. 如果 Anthropic Claude adapter 可以在 V5 范围内安全实现并通过 smoke，则作为第三个 provider family 或 structured skip 记录；如果实现成本过高，不阻塞 `core_acceptance`。
6. OpenAI fallback success 只能作为 fallback evidence，不能伪装成 primary OpenAI provider accepted run。

### 7.3 run matrix 形状

Stage 3 先使用当前初始 10 候选中的 6 个 primary agent-run tasks，并保留 4 个 backup tasks。最终 run matrix 必须显式记录 task role、provider family、scaffold、budget、tool policy、context policy、environment id 和 final verifier plan。

最小 core matrix：

- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入 comparison proof。
- 至少 1 个真实 provider family 有实际 agent run evidence。
- 至少 2 个 scaffold：`simple_react` 和 `planner_coder_verifier`。
- 至少 2 档 budget：`standard` 和 `constrained`。

Resume-ready matrix：

- 至少 2 个真实 provider family 各有至少 2 条真实 agent run records。
- Provider 比较至少覆盖 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget`。
- Scaffold 比较至少覆盖 2 个任务，在同一真实 provider、同一 budget、同一 source tree、同一 verifier plan、同一 tool policy 和同一 context policy 下比较 `simple_react` 与 `planner_coder_verifier`。
- Budget 比较至少覆盖 2 个任务，在同一真实 provider、同一 scaffold、同一 source tree、同一 verifier plan、同一 tool policy 和同一 context policy 下比较 `standard` 与 `constrained`。

### 7.4 主要工作

1. 定义 `v5_provider_registry_report.json`。
2. 定义并实现 `v5_provider_credential_gate_report.json`。
3. 定义并实现 `v5_provider_cost_budget_report.json`，记录 `max_real_provider_calls`、`max_cost_usd`、cost proxy、actual calls 和 cost-limited structured skip。
4. 实现或扩展 provider smoke，使 DeepSeek、OpenAI 和 Anthropic Claude 都能产生 accepted、provider_error、credential_missing_skip、adapter_not_implemented_skip 或 cost_limited_structured_skip。
5. 如果要让 OpenAI 计入 resume-ready provider family，必须解除当前 primary 限制并新增测试，证明 `model.provider=openai` 作为 primary provider 时不会与 fallback policy 混淆。这个变更必须同时覆盖 `model_client.factory`、`evaluation.runner`、`evaluation.schemas.ExperimentConfig.model_provider` allowlist 和对应单元 / 集成测试，避免出现单任务入口可运行但实验矩阵调度入口拒绝 OpenAI primary 的断层。
6. 如果实现 Anthropic Claude adapter，必须提供官方 SDK 或 HTTP 调用策略、redaction policy、credential policy、token usage proxy 和 negative tests。
7. 定义 V5 provider status normalization，把现有 smoke 报告中的 `skipped_no_credentials` 归一化为 V5 的 `credential_missing_skip`，并把 `fallback_success`、`provider_error`、`adapter_not_implemented_skip` 和 `cost_limited_structured_skip` 分别写入稳定枚举。旧状态可以作为 raw status 保留在 audit-only 字段中，但 result summary 和 claim gate 只能使用 V5 归一化状态。
8. 实现 `v5_run_matrix_manifest.json` 和 `v5_matrix_cell_results.jsonl`。
9. 每个 matrix cell 必须绑定 run_id、run_dir、source_tree_hash、final verifier status、token usage、wall time、tool call count、test run count、invalid tool call count、permission denial count、patch stats、trajectory ref、final verifier boundary ref、transcript protocol integrity ref 和 controlled variables ref。
10. 实现 `v5_matrix_compare_scope_report.json`，只允许在 controlled variables 相同的 cell 之间生成比较结论。
11. 生成 Stage 3 版本的 `v5_resume_claim_gate_report.json`，根据真实运行结果暂时允许或阻断 provider / scaffold / budget 相关表述。Stage 4 和 Stage 5 完成后必须重新生成最终版本，不能让 Stage 3 的旧 claim gate 决定最终简历表述。

### 7.5 建议机器产物

- `v5_provider_registry_report.json`
- `v5_provider_credential_gate_report.json`
- `v5_provider_smoke_report.json`
- `v5_provider_cost_budget_report.json`
- `v5_run_matrix_manifest.json`
- `v5_matrix_cell_results.jsonl`
- `v5_matrix_compare_scope_report.json`
- `v5_scaffold_comparison_report.json`
- `v5_budget_comparison_report.json`
- `v5_provider_comparison_report.json`
- `v5_resume_claim_gate_report.json`
- `v5_provider_raw_content_redaction_report.json`
- `v5_provider_status_normalization_report.json`

### 7.6 验收和 negative tests

通过条件：

- `inspect-v5-provider-gate --assert-consistent` 通过。
- `inspect-v5-run-matrix --assert-complete` 通过。
- 至少 1 个真实 provider family 有实际 agent run evidence。
- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入 comparison proof。
- 每个 structured skip 都记录 provider id、credential status、skip reason、affected matrix cells、是否影响 `core_acceptance`、是否影响 `resume_ready_acceptance`。
- `v5_provider_cost_budget_report.json` 中的实际调用量和成本代理值没有超过预算。
- Stage 3 版本的 `v5_resume_claim_gate_report.json` 与真实 provider family 数量一致，并明确 preference pair 状态和 demo share-safe 状态仍待 Stage 4 / Stage 5 最终重算。

负例：

- OpenAI fallback success 被标记成 primary OpenAI accepted run 时失败。
- credential missing skip 被计入真实 provider accepted rate 时失败。
- 旧 `skipped_no_credentials` 状态没有归一化为 V5 `credential_missing_skip` 就进入 result summary 或 claim gate 时失败。
- mock / replay run 被计入真实 provider accepted rate 时失败。
- provider raw request 或 provider raw response 进入 transcript model-visible content、trainable payload、public-safe demo bundle 或 final acceptance docs 时失败。
- comparison report 混用了不同 source tree、不同 final verifier plan、不同 scaffold、不同 budget、不同 tool policy 或不同 context policy 时失败。
- 达到 `max_real_provider_calls` 或 `max_cost_usd` 后继续发起真实 provider 调用时失败。

## 8. 阶段 4：Training export result pack

### 8.1 目标

把真实 agent run trajectory 转成可解释、可审计、可导出的训练数据结果包。V5 不声称已经训练模型，但必须证明 RepoHarness 可以产出被严格分区和审计的 SFT、reinforcement learning rollout、failure dataset、diagnostic-only record 和 blocked record。

### 8.2 主要工作

1. 定义 V5 export result pack schema。
2. 从 Stage 3 的真实 provider runs 生成至少 1 个合规 SFT 样本。
3. 从 Stage 3 的真实 provider runs 生成至少 1 个合规 reinforcement learning rollout 样本。
4. 生成至少 1 个 failure dataset 样本。
5. 生成至少 1 个 diagnostic-only 样本，说明为什么不能训练。
6. 生成至少 1 个 blocked export 样本，说明阻断原因。
7. 尝试从同一 task、同一 source tree、同一 final verifier plan、同一 tool policy、同一 context policy或允许差异的 compare scope 中生成真实可比较 preference pair。
8. 如果没有真实可比较 preference pair，生成 `v5_preference_pair_blocked_report.json`，并让 `v5_resume_claim_gate_report.json` 禁止 preference export 强表述。
9. 实现 reward source taxonomy，至少区分 `unit_test`、`rule_based_verifier`、`rubric`、`llm_judge_audit_only` 和 `mixed`。每类 reward source 必须记录 `authoritative_for_outcome`、`allowed_in_trainable_reward` 和 `model_visible_allowed`，其中 `llm_judge_audit_only` 不得作为 final verifier outcome 的权威来源，也不得作为 trainable reward 的唯一来源。
10. 实现 failure taxonomy 和 failure owner 统计。Failure owner 必须使用稳定枚举：`model_behavior`、`environment_unstable`、`provider_error`、`verifier_or_config_issue`、`permission_or_policy`、`dependency_external`、`task_source_provenance`、`cost_budget` 和 `unknown`。如果多个 owner 同时成立，必须记录 primary owner、secondary owners 和归属优先级说明。
11. 实现 duplicate detection、contamination scan、trainable payload visibility scan 和 export boundary audit。
12. 重新生成最终版 `v5_resume_claim_gate_report.json`，合并 Stage 3 provider 结果、Stage 4 preference pair 状态和 export pack 状态。这个最终版可以暂时把 demo share-safe 状态标为 `pending_stage_5`，但不得允许任何依赖 Stage 5 的强表述。

### 8.3 建议机器产物

- `v5_export_result_pack_manifest.json`
- `v5_sft_export.jsonl`
- `v5_rl_rollout_export.jsonl`
- `v5_preference_pair_export.jsonl`
- `v5_preference_pair_blocked_report.json`
- `v5_failure_dataset.jsonl`
- `v5_failure_taxonomy_report.json`
- `v5_reward_source_taxonomy_report.json`
- `v5_export_audit_report.json`
- `v5_duplicate_record_report.json`
- `v5_training_payload_visibility_report.json`
- `v5_export_partition_summary.json`

### 8.4 验收和 negative tests

通过条件：

- `inspect-v5-export-pack --assert-clean` 通过。
- 至少 1 个 SFT export 样本合规。
- 至少 1 个 reinforcement learning rollout export 样本合规。
- 至少 1 个 failure dataset 样本合规。
- diagnostic-only 和 blocked records 与 trainable records 分区。
- 每条 trainable record 都绑定 prepared messages、model input hash、trajectory、final verifier boundary、reward metadata、reward source type、export policy 和 contamination scan。
- Preference pair 要么真实可比较，要么 blocked report 完整，并且 claim gate 禁止 preference export 强表述。
- Export result pack manifest 明确分列 `real_provider_trainable_records`、`mock_or_replay_records`、`diagnostic_records`、`blocked_records` 和 `synthetic_safe_stress_records`；如果 P1 stress test 没有执行，stress 分区必须记录为 `not_executed` 或 0，不能省略。

负例：

- reward scalar 或 reward label 进入 SFT target、preference target 或自然语言 observation 时失败。
- chosen / rejected 来自不同 task、不同 source tree、不同 verifier plan 或不可比较 compare scope 时失败。
- final verifier boundary 缺失的 record 被标记 trainable 时失败。
- `llm_judge_audit_only` 被当作 trainable reward 的唯一权威来源时失败。
- failure owner 缺少稳定枚举、primary owner 或归属优先级说明时失败。
- mock / replay record 与 real provider trainable record 混入同一统计分母时失败。
- diagnostic-only record 被导出为 trainable 时失败。
- duplicate record 未被识别时失败。

## 9. 阶段 5：Interview demo card、public-safe bundle 和 result summary

### 9.1 目标

把 V5 的机器证据整理成面试官可以快速理解、现场可以追问、简历可以引用的展示材料。这个阶段不是写宣传页，而是生成可以追溯到 evidence ref 的技术索引。

### 9.2 主要工作

1. 生成 `v5_interview_demo_card.md` 和 `v5_interview_demo_card.json`。
2. 生成 `v5_canonical_demo_walkthrough.md`，绑定一个代表性任务和一条真实 run。
3. 生成 `v5_public_demo_bundle_manifest.json`，只包含 `share_safe=true` 的 artifact。
4. 生成 `v5_resume_artifact_index.json`。
5. 生成 `v5_repro_command_index.json`。
6. 生成 `v5_result_summary_table.json`。
7. 生成 `v5_demo_transcript_index.json`，只引用 redacted transcript excerpt。
8. 生成 `v5_permission_network_risk_audit_report.json`。
9. 生成 `v5_claude_code_invariant_mapping.json`。
10. 给 canonical walkthrough 增加至少一个负例 inspect 演示，例如 sha256 drift、未绑定 final verifier evidence 或 evaluator-only evidence 泄漏被拒绝。
11. 重新生成最终版 `v5_resume_claim_gate_report.json`，合并 provider、scaffold、budget、preference pair、export pack、result summary 和 public-safe demo 状态。Final acceptance 只能引用这个最终版 claim gate。
12. 生成 `v5_interview_result_pack_manifest.json`，作为面试展示入口总清单。
13. 生成 `v5_resume_claim_templates.json` 和 `v5_resume_bullets.md`，按 `core_acceptance`、`resume_ready_acceptance` 和 `stress_test_completed` 三种状态分别给出可复制文本。
14. 生成 `v5_interview_qa_evidence.md` 和 `v5_interview_qa_evidence.json`，把常见面试追问映射到 evidence ref。
15. 生成 `v5_public_safe_artifact_mapping.json`，把 `docs/12-resume-narrative-and-demo-artifacts.md` 中的基础展示 artifact 类型映射到 V5 public-safe artifact。

### 9.3 demo walkthrough 必须回答的问题

`v5_canonical_demo_walkthrough.md` 必须用 5 分钟任务剧情讲清楚：

1. 原始失败是什么。
2. agent 如何定位相关文件。
3. 哪个关键工具 observation 改变了下一步动作。
4. final patch 改了哪些文件和核心逻辑。
5. final verifier 为什么接受。
6. 导出样本为什么 trainable，或者为什么 diagnostic-only。
7. acceptance inputs 如何绑定这条 run。
8. 现场负例 inspect 如何证明证据漂移或泄漏会被拒绝。

### 9.4 result summary 指标

`v5_result_summary_table.json` 必须至少包含：

- accepted rate，按 overall、provider family、scaffold、budget 和 task family 分组。
- pass-to-pass regression rate。
- failure type distribution。
- failure owner distribution。
- token usage summary。
- wall time summary。
- cost proxy summary。
- provider comparison conclusion，并绑定 controlled variables。
- scaffold comparison conclusion，并绑定 controlled variables。
- budget comparison conclusion，并绑定 controlled variables。
- trainable、diagnostic、blocked、mock / replay 和 synthetic-safe stress records 的分区统计。

指标分母必须显式定义。真实 provider accepted rate 不得包含 credential missing skip、adapter not implemented skip、cost-limited skip、fallback success、mock / replay 或 synthetic-safe stress records。Overall accepted rate 默认只统计实际启动并到达 final verifier 或结构化 terminal outcome 的真实 primary provider runs；diagnostic-only、quarantined、structured skip、fallback success、mock / replay 和 synthetic-safe stress records 必须分区展示，不能混入 overall accepted rate。

`v5_claude_code_invariant_mapping.json` 必须逐项覆盖 query loop、tool contract、tool result pairing、permission boundary、subagent / task 边界、MCP disabled / frozen facts、hook audit-only facts、plugin / skill 非目标边界、context compaction 或既有 compaction evidence、transcript diagnostics 和 artifact refs。每一项都必须包含：

- `claude_code_invariant`
- `repo_harness_evidence_ref`
- `implemented_scope`
- `explicit_non_goal`
- `resume_demo_relevance`

如果某项只复用 V3 / V4 既有证据，而 V5 没有新增实现，必须在 `implemented_scope` 中写清楚，不能伪装成 V5 新能力。

### 9.5 建议机器产物

- `v5_interview_demo_card.md`
- `v5_interview_demo_card.json`
- `v5_canonical_demo_walkthrough.md`
- `v5_resume_artifact_index.json`
- `v5_public_demo_bundle_manifest.json`
- `v5_repro_command_index.json`
- `v5_result_summary_table.json`
- `v5_demo_transcript_index.json`
- `v5_permission_network_risk_audit_report.json`
- `v5_claude_code_invariant_mapping.json`
- `v5_demo_negative_inspect_report.json`
- `v5_interview_result_pack_manifest.json`
- `v5_resume_claim_templates.json`
- `v5_resume_bullets.md`
- `v5_interview_qa_evidence.md`
- `v5_interview_qa_evidence.json`
- `v5_public_safe_artifact_mapping.json`

### 9.6 验收和 negative tests

通过条件：

- `inspect-v5-demo-artifacts --assert-share-safe` 通过。
- Demo card 中每个数字都能追溯到 evidence ref。
- Public demo bundle 中所有 artifact 都是 `share_safe=true`。
- Interview result pack 中所有 artifact 都能追溯到 public-safe evidence ref 或明确标记为 internal-only，不得把 internal-only artifact 放进 public bundle。
- Resume bullets 和 claim templates 必须由 `v5_resume_claim_gate_report.json` 决定启用状态；被 blocked 的 claim 不得出现在可复制 bullets 中。
- Interview Q&A evidence index 必须至少覆盖任务真实性、provider 比较、公平变量、训练导出边界、final verifier 权威性、evidence integrity、public-safe demo 和非目标边界。
- `v5_public_safe_artifact_mapping.json` 必须把 docs/12 中的展示 artifact 类型映射到 V5 具体文件，并标记 `share_safe`、`visibility` 和 `redaction_status`。
- canonical walkthrough 不包含 provider raw request、provider raw response、Authorization marker、credential marker、hidden verifier detail、本机私密路径、evaluator-only raw evidence 或未脱敏 transcript。
- result summary 的分母定义清楚，不混合 real provider、mock / replay 和 stress records。
- Claude Code invariant mapping 明确区分“借鉴架构不变量”和“不复刻产品能力”。

负例：

- demo bundle 引入 provider raw request、provider raw response、Authorization marker 或 provider credential marker 时失败。
- resume bullets 使用 `multi-provider agent runs`、`preference export completed` 或 `resumable export stress tests`，但 claim gate 没有允许对应 claim 时失败。
- interview Q&A evidence 引用 evaluator-only raw evidence 或 provider raw artifact 时失败。
- walkthrough 引用 evaluator-only raw evidence 时失败。
- result summary 把 credential missing skip 算入真实 provider 失败率时失败。
- result summary 把 mock / replay accepted rate 混入真实 provider accepted rate 时失败。
- Claude Code mapping 把 RepoHarness 描述成 Claude Code 产品复刻时失败。

## 10. 阶段 6：Final acceptance、acceptance bundle 和 post-acceptance docs

### 10.1 目标

生成 V5 acceptance inputs、V5 acceptance report、post-report inspect outputs、V5 acceptance bundle，以及 V5 final acceptance / walkthrough 文档。这个阶段必须严格遵守 evidence 时序，避免循环引用。

### 10.2 acceptance inputs 必须绑定

V5 acceptance inputs 至少绑定：

- V2 acceptance report。
- V3 acceptance report。
- V3 acceptance bundle。
- V4 latest acceptance inputs。
- V4 latest acceptance report。
- V4 latest doc-sync acceptance bundle。
- V4 latest doc-sync final command log。
- V5 baseline check report。
- V4 review findings closure report。
- V5 documentation sync report。
- V5 preflight input binding。
- V5 pre-acceptance evidence integrity report。
- V5 task set manifest。
- V5 task inventory report。
- V5 task diversity report。
- V5 task visibility scan report。
- V5 run matrix manifest。
- V5 provider credential gate report。
- V5 provider cost budget report。
- V5 resume claim gate report。
- V5 export result pack manifest。
- V5 preference pair blocked report，如果没有真实可比较 preference pair。
- V5 failure taxonomy report。
- V5 reward source taxonomy report。
- V5 interview demo card。
- V5 canonical demo walkthrough。
- V5 public demo bundle manifest。
- V5 resume artifact index。
- V5 repro command index。
- V5 result summary table。
- V5 demo transcript index。
- V5 permission / network risk audit report。
- V5 Claude Code invariant mapping。
- V5 pre-report command log。
- V5 implementation logs。
- V5 review records。
- V5 final acceptance pre-test evidence。

这些 V4 latest refs 是 Stage 0 baseline proof 的显式证据引用，不表示 Stage 6 要在已经包含 V5 源码变更的当前工作区重新执行旧 V4 doc-sync bundle immutable inspect。Stage 6 对 V4 基线的检查口径是复核 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和 command log lineage 是否绑定了 Stage 0 的通过结果。

如果实际执行 P1 export stress test，acceptance inputs 还必须绑定 `v5_export_stress_manifest.json`、`v5_export_resume_report.json` 和相关 stress result summary；如果没有执行 P1 stress test，acceptance inputs 必须记录 `stress_test_executed=false` 或等价字段，final acceptance 和简历表述不得声称完成 export stress test。

Acceptance inputs 不得绑定 post-report inspect outputs 或 bundle final outputs。
Acceptance inputs 中的 V5 command logs 只能绑定 acceptance report 生成之前已经存在的 pre-report command log。Post-report inspect command entries、bundle build entry、final command log 和 doc-sync command log 必须按后续时序进入 acceptance bundle 或 doc-sync bundle，不能提前进入 acceptance report 输入。

### 10.3 Post-report inspect 和 pre-bundle outputs

这些产物在 V5 acceptance report 生成之后产生，不能作为 acceptance report 输入：

- `v5_acceptance_report_reference_integrity_report.json`
- `inspect_v5_acceptance_core_command_log_entry`
- `inspect_v5_acceptance_resume_ready_command_log_entry`
- V5 pre-bundle command log。

它们必须进入 final command log 或 acceptance bundle 的 post-report outputs section。`V5_PRE_BUNDLE_COMMAND_LOG` 可以作为 `build-v5-acceptance-bundle` 的显式输入，但不能作为 acceptance report 输入。

### 10.4 bundle final outputs

这些产物在 acceptance bundle 构建期间或之后产生，不能作为 acceptance report 输入：

- V5 acceptance bundle manifest。
- V5 acceptance bundle command lineage report。
- `build_v5_acceptance_bundle_command_log_entry`
- final acceptance command log。
- `inspect_acceptance_bundle_command_log_entry`
- Post-acceptance `docs/v5/final-acceptance.md`。
- Post-acceptance `docs/v5/walkthrough.md`。

如果 V5 final acceptance 文档或 walkthrough 在 bundle 构建后更新，必须生成 V5 doc-sync acceptance bundle 和 doc-sync final command log，规则与 V4 doc-sync bundle 相同：新的 doc-sync bundle 必须绑定更新后的文档哈希、原始 V5 bundle ref、doc-sync build command entry 和 doc-sync inspect command entry。后续引用 V5 latest acceptance bundle 时，必须优先引用 doc-sync bundle，而不是原始 bundle。

### 10.5 退出门命令

Stage 6 必须至少执行以下命令。这里把 command log 拆成 pre-bundle command log、bundle build command entry 和 post-bundle inspect command entry，避免 bundle 构建命令读取一个随后还会追加的 final command log：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation V5_PREFLIGHT_INPUT_BINDING --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs V5_ACCEPTANCE_INPUTS --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-core-complete --reference-integrity-output V5_ACCEPTANCE_REPORT_REFERENCE_INTEGRITY_REPORT --command-log-entry-output INSPECT_V5_ACCEPTANCE_CORE_COMMAND_LOG_ENTRY
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-resume-ready --reference-integrity-input V5_ACCEPTANCE_REPORT_REFERENCE_INTEGRITY_REPORT --command-log-entry-output INSPECT_V5_ACCEPTANCE_RESUME_READY_COMMAND_LOG_ENTRY
PATH=.venv/bin:$PATH repo-harness build-v5-pre-bundle-command-log --base-command-log V5_STAGE6_COMMAND_LOG_DRAFT --command-log-entry INSPECT_V5_ACCEPTANCE_CORE_COMMAND_LOG_ENTRY --command-log-entry INSPECT_V5_ACCEPTANCE_RESUME_READY_COMMAND_LOG_ENTRY --output V5_PRE_BUNDLE_COMMAND_LOG --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness build-v5-acceptance-bundle --acceptance-report V5_ACCEPTANCE_REPORT --post-report-inspect-output V5_ACCEPTANCE_REPORT_REFERENCE_INTEGRITY_REPORT --pre-bundle-command-log V5_PRE_BUNDLE_COMMAND_LOG --bundle-build-command-log-entry-output BUILD_V5_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY --documentation-ref docs/v5/final-acceptance.md --documentation-ref docs/v5/walkthrough.md --output V5_ACCEPTANCE_BUNDLE --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness plan-acceptance-bundle-inspect-entry --acceptance-bundle V5_ACCEPTANCE_BUNDLE --final-command-log V5_FINAL_ACCEPTANCE_COMMAND_LOG --output INSPECT_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY
PATH=.venv/bin:$PATH repo-harness build-v5-final-command-log --pre-bundle-command-log V5_PRE_BUNDLE_COMMAND_LOG --command-log-entry BUILD_V5_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY --command-log-entry INSPECT_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY --output V5_FINAL_ACCEPTANCE_COMMAND_LOG --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle V5_ACCEPTANCE_BUNDLE --final-command-log V5_FINAL_ACCEPTANCE_COMMAND_LOG --assert-immutable
```

`INSPECT_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY` 是一个 planned command entry。它的 argv 可以包含 `--final-command-log V5_FINAL_ACCEPTANCE_COMMAND_LOG`，但该 entry 对 `V5_FINAL_ACCEPTANCE_COMMAND_LOG` 只能记录 path、purpose 和 `sha256_policy=self_reference_omitted`，不能要求在 final command log 内部提前写入自身 sha256。`inspect-acceptance-bundle` 的实际 exit code、stdout / stderr sha256 和 bundle lineage 检查结果必须写入 `v5_acceptance_bundle_command_lineage_report.json` 或等价 post-final proof，避免 final command log 对自身形成不可满足的哈希循环。

如果 `resume_ready_acceptance` 没有通过，Stage 6 仍可以生成 `core_acceptance.status=passed` 的 report，但 `inspect-v5-acceptance --assert-resume-ready` 必须失败，并且 final acceptance 文档必须使用降级表述。

### 10.6 建议机器产物

- `v5_acceptance_inputs.json`
- `v5_acceptance_report.json`
- `v5_acceptance_report_reference_integrity_report.json`
- `v5_acceptance_bundle_manifest.json`
- `v5_acceptance_bundle_command_lineage_report.json`
- `v5_stage6_command_log_draft.jsonl`
- `v5_pre_bundle_command_log.jsonl`
- `build_v5_acceptance_bundle_command_log_entry.json`
- `inspect_acceptance_bundle_command_log_entry.json`
- `v5_final_acceptance_command_log.jsonl`
- `v5_final_acceptance_pretest_report.json`
- `v5_acceptance_bundle_manifest_doc_sync_*.json`，如果 post-bundle 文档发生更新。
- `v5_final_acceptance_command_log_doc_sync_*.jsonl`，如果 post-bundle 文档发生更新。

### 10.7 验收和 negative tests

通过条件：

- `inspect-v5-inputs --assert-complete` 通过。
- `inspect-v5-acceptance --assert-core-complete` 通过。
- 如果使用完整强简历表述，`inspect-v5-acceptance --assert-resume-ready` 必须通过。
- `build-v5-acceptance-bundle` 显式接收 acceptance report、post-report inspect output、pre-bundle command log 和 documentation refs，不扫描 latest run，不读取随后还会生成或追加的 final command log。
- `inspect-acceptance-bundle --assert-immutable` 通过。
- Acceptance report 包含 `core_acceptance.status`、`resume_ready_acceptance.status`、`allowed_claims`、`blocked_claims`、`claim_gate_report_ref` 和 `acceptance_report_reference_integrity.expected_check`。该字段只能描述待执行的 post-report inspect、acceptance inputs hash 和允许的 critical evidence ref 集合，不能引用 `v5_acceptance_report_reference_integrity_report.json` 本身。

负例：

- acceptance report 引用未进入 acceptance inputs 的 critical evidence 时失败。
- acceptance report 引用 post-report inspect output 或 bundle final output 时失败。
- `inspect_v5_acceptance_core_command_log_entry` 和 `inspect_v5_acceptance_resume_ready_command_log_entry` 被合并成无法区分的单条记录时失败。
- bundle builder 读取随后还会追加的 final command log 时失败。
- bundle command lineage 指向旧 acceptance report 时失败。
- bundle 构建命令覆盖已经存在的 bundle 时失败。
- final acceptance docs 使用了 claim gate 禁止的强表述时失败。

## 11. 阶段间依赖和执行顺序

推荐执行顺序如下：

1. Stage 0：冻结 V4 closure baseline 和 V5 preflight input。
2. Stage 1：先实现 schema、inspect skeleton 和 evidence integrity gate。
3. Stage 2A：接入当前 10 个初始候选。
4. Stage 3A：实现 provider registry、credential gate、cost budget 和 provider smoke。
5. Stage 2B：补齐 2 个 PR / issue 候选，或通过正式范围变更修改严格任务库存门。默认是补齐。
6. Stage 3B：执行最小真实 provider agent runs，先满足 `core_acceptance` 的真实 provider 下限。
7. Stage 3C：如果第二个真实 provider family 可用，执行 resume-ready provider comparison；如果不可用，生成 blocked claim。
8. Stage 4：从 Stage 3 runs 生成 export result pack，并重新生成最终 claim gate 的 export / preference 部分。
9. Stage 5：生成 demo card、public-safe bundle 和 result summary，并重新生成最终版 `v5_resume_claim_gate_report.json`。
10. Stage 6：构建 V5 acceptance inputs、acceptance report、acceptance bundle 和 post-acceptance docs。

这样安排的原因是：当前任务池已经足够启动 implementation plan、schema、inspect、task adapter 和 provider gate 开发，但严格任务库存门仍是 Stage 3 真实 run matrix 的前置门。补齐 2 个 PR / issue 候选不能被遗忘，也不能被推迟到 final acceptance 才发现阻塞。

## 12. 最低完成、简历完成和降级路径

### 12.1 `core_acceptance` 最低完成

`core_acceptance` 必须满足：

- 全量测试通过。
- V2 / V3 当前兼容性 inspect 通过；V4 closure baseline 的 immutable inspect 通过结果已经由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和 command log 绑定，并由 `inspect-v5-preimplementation` 复核。不得要求已经包含 V5 源码变更的当前工作区重新通过旧 V4 doc-sync bundle immutable inspect。
- V5 pre-acceptance evidence integrity inspect 通过。
- V5 task set inspect 通过。
- 至少 12 个 accepted / auditable task definitions，除非范围文档经过正式修订。
- 至少 8 个 accepted / auditable task definitions 来自 PR / issue flow，除非范围文档经过正式修订。
- 至少 3 个 accepted / auditable task definitions 来自 SWE-Bench-like anchors。
- V5 run matrix inspect 通过。
- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入 comparison proof。
- 至少 1 个真实 provider family 有实际 agent run evidence。
- V5 provider cost budget report 通过检查。
- V5 export pack inspect 通过。
- V5 acceptance report inspect 通过。
- 至少 1 个合规 SFT、RL rollout 和 failure dataset 样本。
- 至少 1 个 diagnostic-only 样本，并由 `inspect-v5-export-pack` 证明没有进入 trainable payload。
- 至少 1 个 blocked export 样本，并由 `inspect-v5-export-pack` 记录阻断原因、failure owner 和 failure category。
- Preference pair 要么真实可比较，要么有完整 blocked report，并在 claim gate 中禁用 preference export 强表述。
- 0 个 trainable payload contamination finding。
- 0 个 evaluator-only evidence model-visible finding。
- 0 个 acceptance report unbound critical evidence finding。
- 0 个 provider credential raw value 泄漏 finding。
- 0 个 provider raw request / response 进入 model-visible content、trainable payload、public-safe demo bundle 或 final acceptance docs。
- 0 个 risky command 或 network policy finding 进入模型可见训练内容。
- Result summary 分列 real provider trainable records、mock / replay records、diagnostic records、blocked records 和 synthetic-safe stress records。
- Result summary 展示 accepted rate、pass-to-pass regression rate、failure type distribution、failure owner distribution、token usage、wall time、cost proxy、provider / scaffold / budget comparison conclusion 和 trainable / diagnostic / blocked / mock-replay 分区统计。
- V5 acceptance bundle immutable inspect 通过。

### 12.2 `resume_ready_acceptance` 简历完成

`resume_ready_acceptance` 额外要求：

- 至少 2 个真实 provider family 各有至少 2 条真实 agent run records。
- Provider comparison 满足 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget`。
- Scaffold comparison 至少覆盖 2 个任务。
- Budget comparison 至少覆盖 2 个任务。
- 至少 1 个真实可比较 preference pair 通过 compare scope gate。
- Canonical demo walkthrough 和 public-safe demo bundle 通过 share-safe 检查。
- `v5_resume_claim_gate_report.json` 明确允许使用完整强表述。

### 12.3 降级路径

如果只有 1 个真实 provider family 有实际运行：

- 可以争取 `core_acceptance`。
- 不得使用 `multi-provider agent runs` 或完整 `controlled multi-provider comparison` 表述。
- `v5_resume_claim_gate_report.json` 必须把这些强表述放入 `blocked_claims`。

如果没有真实可比较 preference pair：

- 可以争取 `core_acceptance`。
- 必须生成 `v5_preference_pair_blocked_report.json`。
- 不得写 `preference export completed`。

如果最终没有补齐 `12 total / 8 PR-issue`：

- 默认不能通过当前范围定义下的 `core_acceptance`。
- 必须补 2 个 PR / issue 候选，或者正式修改范围文档、preflight plan 和 review 记录。
- 不能进入 Stage 3 真实 provider agent run matrix 的退出门，已经完成的 provider gate 或 smoke 只能作为前置实现证据。

如果 provider API、成本或凭证导致真实运行不足：

- 必须 structured skip。
- 不能用 mock / replay 代替真实 provider run。
- 如果没有任何真实 provider family 实际运行，V5 简历目标应标记为 blocked。

## 13. P1 增强的进入条件

P1 只能在 P0 主线稳定后进入。P1 不得降低 P0 evidence integrity、visibility、final verifier boundary 或 acceptance bundle 的标准。

可以考虑的 P1：

1. Multi-provider matrix expansion：从 2 个 provider family 扩到 3 个 provider family。
2. Provider adapter polish：增强 latency、rate limit、context length、token usage 和 cost proxy。
3. Context strategy micro-comparison：比较 keep-recent、summary 和 artifact-only。
4. Code retrieval diagnostic：增加 file localization 和 retrieval trace。
5. Prompt injection diagnostic-only task：只做 diagnostic，不进入 trainable payload。
6. Export stress test：生成 1,000 条以上 synthetic-safe stress records，验证 sharded export、resume 和 duplicate detection。

P1 export stress test 完成前，不得使用 `resumable export stress tests` 的简历表述。

## 14. Review 和 implementation log 要求

每个阶段完成后必须写 implementation log，并进行独立 review。

Implementation log 至少包含：

- 本阶段目标。
- 修改的模块和文档。
- 新增或更新的 schema。
- 新增或更新的 inspect 命令。
- 新增或更新的 tests。
- 生成的机器产物 path 和 sha256。
- 执行过的验证命令。
- 未完成项和 blocked claims。

Review 至少从以下角度检查：

1. 任务数量和来源是否真实满足范围文档。
2. Provider / scaffold / budget 比较是否保持 controlled variables。
3. Evidence integrity 是否有时序循环或 unbound reference。
4. Trainable payload 是否存在 evaluator-only、reward、provider raw content 或 hidden verifier 泄漏。
5. Result summary 的分母是否清楚。
6. Resume claim gate 是否禁止了没有证据支撑的强表述。
7. Acceptance bundle 是否绑定 command lineage。

V5 final acceptance 前，必须确保所有 P1 / P2 review findings 要么修复，要么结构化记录为不阻塞项，并由 `v5_resume_claim_gate_report.json` 反映对简历表述的影响。
