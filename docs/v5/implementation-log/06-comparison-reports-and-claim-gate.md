# V5 Stage 3C Comparison Reports 和阶段性 Claim Gate 实施日志

## 目标

Stage 3C 的目标是在 Stage 3B 已经产生真实 DeepSeek provider agent run evidence 之后，判断是否具备 `resume_ready_acceptance` 所需的第二个真实 provider family。如果第二个真实 provider family 不可用，则必须生成结构化 blocked claim，禁止使用 multi-provider 和 controlled multi-provider comparison 强表述。

本阶段输入如下：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json
```

## 实现内容

本阶段新增 CLI：

```bash
repo-harness build-v5-comparison-reports
```

该 builder 生成以下机器产物：

- `v5_matrix_compare_scope_report.json`
- `v5_provider_comparison_report.json`
- `v5_scaffold_comparison_report.json`
- `v5_budget_comparison_report.json`
- `v5_resume_claim_gate_report.json`
- `build_v5_comparison_reports_command_log_entry.json`
- `v5_stage3c_comparison_reports_command_log.jsonl`

本阶段结论是：当前只有 `deepseek` 一个真实 provider family 具有实际 run evidence，`openai` 仍是 fallback-only，`anthropic_claude` 仍是 adapter not implemented。因此 Stage 3C 不执行 resume-ready provider comparison，而是生成 blocked claim。

## 主要修改文件

- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_run_matrix.py`

## 新增或更新的 schema

- `repo_harness_v5_matrix_compare_scope_report_v0`
- `repo_harness_v5_provider_comparison_report_v0`
- `repo_harness_v5_scaffold_comparison_report_v0`
- `repo_harness_v5_budget_comparison_report_v0`
- `repo_harness_v5_resume_claim_gate_report_v0`

`inspect-v5-run-matrix` 现在会根据 schema version 路由到 run matrix manifest、matrix cell result 或 matrix compare scope report 的深度检查，避免把 compare scope report 错误当成 run matrix manifest 检查。

## 新增或更新的测试

`tests/unit/test_v5_run_matrix.py` 新增覆盖：

- `build-v5-comparison-reports` 可以从 executed run matrix 生成 compare scope report。
- `inspect-v5-run-matrix` 可以独立复核 `v5_matrix_compare_scope_report.json`。
- `v5_resume_claim_gate_report.json` 会把 `multi-provider agent runs` 写入 blocked claims。
- provider comparison report 会明确 `resume_ready_provider_comparison_satisfied=false`，并且只记录 `deepseek` 一个真实 provider family。

## 机器产物

正式 Stage 3C 产物目录：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/
```

Matrix compare scope report：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_matrix_compare_scope_report.json
sha256: 50147f21106ad2b29589d6029396ce2bcd24a124b2a40b4a4fac4e66b6ebbf45
```

Provider comparison report：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_provider_comparison_report.json
sha256: 8b7be9802324edfd768f4e6cf64eca36a2d1cd52307caa87d92955d6953d260d
```

Scaffold comparison report：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_scaffold_comparison_report.json
sha256: 522b4b08ed6341b7df7461f6725d8f18a63f2af5aac54fea407f6f522c976fb5
```

Budget comparison report：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_budget_comparison_report.json
sha256: bd3a1bba4a5f2227043a47743c4f2b0c0a98f06f08dc033d7ad96cb9ec691c0b
```

Resume claim gate report：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_resume_claim_gate_report.json
sha256: 38216e52cbd8ce093a0540b62d669f1f16d51e4522df7e80279f917496f12cba
```

Command entry：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/build_v5_comparison_reports_command_log_entry.json
sha256: eba628a1e63015ccfd8c2630b325e4d56a037678122297365713d1f2cdeacb23
```

Command log：

```text
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_stage3c_comparison_reports_command_log.jsonl
sha256: 50bf87679d7e462c0c481bddac385bdfc7cbbcb12070445ca6010941af578ccc
```

## 验证命令和结果

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

`rg` 密钥和 Authorization marker 扫描无输出。

本阶段单元测试结果：

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

## 正例证据

- `v5_matrix_compare_scope_report.json` 的 `comparison_axis=diagnostic_baseline`。
- `comparison_validity=diagnostic_only`。
- `compared_task_ids` 包含 4 个真实 DeepSeek run task：`v5_task_003`、`v5_task_004`、`v5_task_005` 和 `v5_task_007`。
- `counts_toward_core_comparison_proof=true`。
- `counts_toward_resume_ready_provider_comparison=false`。
- `v5_provider_comparison_report.json` 中 `provider_families_with_actual_runs=["deepseek"]`。
- `v5_provider_comparison_report.json` 中 `resume_ready_provider_comparison_satisfied=false`。
- `v5_resume_claim_gate_report.json` 中 `provider_claim_status=blocked_single_provider_family_deepseek_only`。

## 负例证据

- `v5_resume_claim_gate_report.json` 把以下强表述放入 `blocked_claims`：
  - `multi-provider agent runs`
  - `controlled multi-provider comparison`
  - `resume-ready provider comparison`
  - `scaffold comparison conclusion`
  - `budget comparison conclusion`
  - `preference export completed`
  - `interview-grade evaluation pack`
  - `resumable export stress tests`
- `v5_scaffold_comparison_report.json` 明确 `comparison_validity=invalid`，原因是 Stage 3B 只执行了 `simple_react`。
- `v5_budget_comparison_report.json` 明确 `comparison_validity=invalid`，原因是 Stage 3B 只执行了 constrained budget。

## 允许降级项

- Stage 3C 可以以 `diagnostic_baseline` 形式满足 core comparison proof 的最低可追溯证据，但不得把它写成 provider、scaffold 或 budget 结论。
- Stage 3C 可以允许 “one DeepSeek real provider family evidence” 这类弱表述。

## 禁止降级项

- 不允许使用 `multi-provider agent runs`。
- 不允许使用 `controlled multi-provider comparison`。
- 不允许使用 `scaffold comparison conclusion` 或 `budget comparison conclusion`。
- 不允许把 OpenAI fallback-only 或 Anthropic Claude adapter-not-implemented skip 计入真实 provider family。

## 已知限制

- 当前 Stage 3C 没有第二个真实 provider family，因此 `resume_ready_acceptance` 的 provider comparison 门仍然 blocked。
- 当前 Stage 3C 没有执行 alternate scaffold 或 alternate budget cells，因此 scaffold / budget conclusion 仍然 blocked。
- Stage 4 和 Stage 5 必须重新生成最终版 `v5_resume_claim_gate_report.json`，不能直接用 Stage 3C 的 `stage3_partial` claim gate 作为 final acceptance claim gate。

## 自审结论

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段执行等价独立只读自审，记录见：

```text
docs/v5/review/implementation/06-comparison-reports-and-claim-gate-review.md
```

当前没有剩余 P1 或 P2。允许进入 V5 Stage 4，但 Stage 4 必须继续把 preference pair、export pack 和最终 claim gate 与当前 Stage 3C blocked claims 对齐。
