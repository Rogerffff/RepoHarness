# V5 Stage 3C Comparison Reports 和 Claim Gate 自审记录

## 审查范围

本记录覆盖 V5 Stage 3C comparison reports、diagnostic comparison scope、provider / scaffold / budget blocked reports 和阶段性 resume claim gate：

- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_run_matrix.py`
- `runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_matrix_compare_scope_report.json`
- `runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_provider_comparison_report.json`
- `runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_scaffold_comparison_report.json`
- `runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_budget_comparison_report.json`
- `runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_resume_claim_gate_report.json`

## 审查方式

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段按实施规则执行等价独立只读自审。自审只读取代码、测试和机器产物，不修改文件；发现需要修复的问题后，再单独进入修复步骤。

审查重点如下：

- 是否把 DeepSeek 单 provider evidence 错误升级为 multi-provider evidence。
- 是否把 diagnostic baseline comparison proof 写成 provider、scaffold 或 budget 胜率结论。
- `v5_resume_claim_gate_report.json` 是否明确阻断不满足条件的强表述。
- compare scope inspect 是否能独立复核 controlled variables 和 compared cells。
- 机器产物中是否出现 raw provider credential、Authorization marker 或 Bearer marker。

## 审查发现

### P2：`inspect-v5-run-matrix` 初版没有按 schema 路由 compare scope report

问题：Stage 3B 时 `inspect-v5-run-matrix` 的 expected schema 已包含 `V5MatrixCompareScopeReport`，但深度检查函数总是按 run matrix manifest 读取 `planned_matrix_cells`。这会导致真正的 compare scope report 在深度检查时被误判缺少 manifest 字段。

风险：Stage 3C 的 `v5_matrix_compare_scope_report.json` 无法被只读 inspect 正确复核。

处理：已修复。`inspect-v5-run-matrix` 现在根据 `schema_version` 分别路由：

- `V5RunMatrixManifest` 使用 run matrix manifest deep check。
- `V5MatrixCellResult` 使用 cell result deep check。
- `V5MatrixCompareScopeReport` 使用 compare scope deep check。

新增单元测试覆盖 compare scope report inspect。

状态：已关闭。

### P3：当前 comparison proof 只能是 diagnostic baseline

问题：Stage 3B 只执行了 DeepSeek、`simple_react` 和 constrained budget 的 6 个 cells，因此 Stage 3C 不能生成 provider、scaffold 或 budget 有效比较结论。

风险：后续文档或简历 bullet 如果写成 “controlled multi-provider comparison” 或 “scaffold/budget comparison conclusion”，会超过证据边界。

处理：`v5_resume_claim_gate_report.json` 已把 multi-provider、provider comparison、scaffold comparison、budget comparison、preference export 和完整 interview-grade evaluation pack 都放入 `blocked_claims`。`v5_matrix_compare_scope_report.json` 只声明 `diagnostic_baseline`，并设置 `comparison_validity=diagnostic_only`。

状态：记录为后续约束，不阻塞进入 Stage 4。

## 已核查的不变量

### Provider comparison 强表述已被阻断

已核查：

```text
provider_families_with_actual_runs=["deepseek"]
actual_records_by_provider.deepseek=6
resume_ready_provider_comparison_satisfied=false
provider_claim_status=blocked_single_provider_family_deepseek_only
```

`blocked_claims` 中包含：

```text
multi-provider agent runs
controlled multi-provider comparison
resume-ready provider comparison
```

结论：当前 Stage 3C 没有把 DeepSeek 单 provider evidence 伪装成 multi-provider evidence。

### Scaffold 和 budget 结论已被阻断

已核查：

- `v5_scaffold_comparison_report.json` 中 `observed_values=["simple_react"]`，`comparison_validity=invalid`。
- `v5_budget_comparison_report.json` 中 `observed_values=["stage3b_constrained_one_turn_no_tool_calls"]`，`comparison_validity=invalid`。
- `v5_resume_claim_gate_report.json` 中 `blocked_claims` 包含 `scaffold comparison conclusion` 和 `budget comparison conclusion`。

结论：当前 Stage 3C 没有生成 scaffold 或 budget 结论。

### Core comparison proof 是 diagnostic-only

已核查：

```text
comparison_axis=diagnostic_baseline
comparison_validity=diagnostic_only
compared_task_ids=["v5_task_003", "v5_task_004", "v5_task_005", "v5_task_007"]
counts_toward_core_comparison_proof=true
counts_toward_resume_ready_provider_comparison=false
```

结论：当前比较证据只能作为 core 层面的 diagnostic comparison proof，不能支撑 resume-ready provider comparison。

### Claim gate 没有提前允许 Stage 4 / Stage 5 表述

已核查：

- `preference_pair_claim_status=pending_stage4`。
- `demo_share_safe_status=pending_stage5`。
- `stress_test_claim_status=not_claimed`。
- `blocked_claims` 包含 `preference export completed`、`interview-grade evaluation pack` 和 `resumable export stress tests`。

结论：Stage 3C claim gate 没有提前允许依赖 Stage 4 或 Stage 5 的强表述。

### Raw credential 和 provider marker 未泄漏

已核查：

```bash
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer" runs/v5-stage3c-comparison-reports-20260505T171500Z
```

结果：无输出。

结论：Stage 3C 产物没有 raw provider credential、Authorization marker 或 Bearer marker。

## 验证结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_run_matrix.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_run_matrix.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py tests/unit/test_v5_provider_gate.py tests/unit/test_v5_run_matrix.py -q
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness build-v5-comparison-reports --executed-run-matrix-manifest runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --provider-gate-report runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json --output-dir runs/v5-stage3c-comparison-reports-20260505T171500Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_matrix_compare_scope_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_resume_claim_gate_report.json
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-evidence-integrity runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-gate runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-cost-budget runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/v5_run_matrix_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --assert-complete
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer" runs/v5-stage3c-comparison-reports-20260505T171500Z
```

单元测试结果：

```text
4 passed in 0.39s
```

完整 V5 相关测试结果：

```text
51 passed in 1.51s
```

完整测试结果：

```text
763 passed in 712.91s
```

本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync acceptance bundle immutable inspect。V4 doc-sync bundle immutable proof 仍然只作为 Stage 0 preimplementation baseline proof 使用。

## 剩余风险和后续项

- Stage 4 必须把 preference pair 状态重新计算并生成真实 preference pair 或 blocked report；不能沿用 Stage 3C 的 `pending_stage4`。
- Stage 5 必须重新生成 final claim gate，并把 public-safe demo bundle 状态从 `pending_stage5` 更新为 passed 或 blocked。
- 如果后续实现第二个真实 provider family，必须重新生成 provider comparison report 和 claim gate；当前 Stage 3C blocked report 不能被手工改成 passed。

## 复审结论

P2 已修复，当前没有剩余 P1 或 P2。P3 已作为后续约束记录。允许进入 V5 Stage 4，但 Stage 4 不得放宽当前 provider / scaffold / budget blocked claims，除非对应真实运行证据已经重新生成并通过 inspect。
