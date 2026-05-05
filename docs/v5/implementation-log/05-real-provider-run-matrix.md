# V5 Stage 3B 最小真实 Provider Agent Run Matrix 实施日志

## 目标

Stage 3B 的目标是在 Stage 3A provider gate 和 cost budget 已经通过的前提下，执行满足 `core_acceptance` 下限的最小真实 provider agent run evidence。这个阶段只争取 `core_acceptance` 要求中的真实 provider family 和真实 agent run 数量下限，不声明多 provider comparison，不声明 preference export completed，也不把未执行 final verifier 的运行结果提升为 accepted。

本阶段绑定的输入如下：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json
```

## 实现内容

本阶段新增并落地两个 CLI：

```bash
repo-harness build-v5-run-matrix
repo-harness run-v5-run-matrix
```

`build-v5-run-matrix` 从 Stage 2B merged task set 中选择 6 个 agent-run-ready 任务，生成固定控制变量和每个 cell 的 runnable task YAML。选择的任务如下：

- `v5_task_003`
- `v5_task_004`
- `v5_task_005`
- `v5_task_007`
- `v5_pr_issue_click_3364`
- `v5_pr_issue_attrs_1428`

`run-v5-run-matrix` 对每个 cell 执行一轮 DeepSeek primary provider 的 `AgentLoop`，固定条件如下：

- provider：`deepseek`
- model：`deepseek-v4-flash`
- scaffold：`simple_react`
- turn budget：`1`
- tool call budget：`0`
- test run budget：`0`
- raw provider logging policy：`redact_secrets`
- model-visible task input：只使用 adapter-visible task statement 和 visible constraints。

重要边界：本阶段的运行路径是 `minimal_provider_agent_loop`。它证明真实 provider agent loop evidence 和 raw provider artifact redaction，但不执行 final verifier，也不产生 accepted run。每条 run 都写入 `final_verifier_boundary.json`，其中 `final_verifier_ran=false`、`accepted=false`、`counts_toward_primary_accepted_rate=false`。

## 主要修改文件

- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_run_matrix.py`

## 新增或更新的 schema

- `repo_harness_v5_run_matrix_manifest_v0`
- `repo_harness_v5_matrix_cell_result_v0`
- `repo_harness_v5_stage3b_final_verifier_boundary_v0`
- `repo_harness_v5_stage3b_minimal_metrics_v0`
- `repo_harness_v5_stage3b_minimal_run_config_facts_v0`

## 新增或更新的 inspect 命令

`inspect-v5-run-matrix --assert-complete` 现在会复核：

- planned matrix cell 数量和 `planned_matrix_cell_count` 一致。
- OpenAI fallback-only adapter 不能作为 primary provider cell。
- 执行后 `agent_run_started=true` 时，`provider_api_called` 必须为 `true`。
- 执行后至少有 6 条 matrix cell result。
- 执行后至少有 6 个 `actual_provider_call_count > 0` 的真实 provider agent run evidence。
- 执行后至少包含 `deepseek` provider family 的真实 provider evidence。
- 每个真实 provider result 必须包含 trajectory、transcript、artifact manifest 和 final verifier boundary 引用。
- raw provider artifact redaction failure count 必须为 `0`。
- execution report 中 `actual_provider_calls` 不能超过 cost budget 上限。

## 新增或更新的测试

`tests/unit/test_v5_run_matrix.py` 覆盖：

- run matrix builder 可以生成 planned manifest，并由 inspect 复核。
- builder 会拒绝 DeepSeek credential 不存在的 provider gate。
- inspect 可以复核执行后的真实 provider evidence 结构，且要求 6 条实际 provider call evidence。

## 机器产物

正式 Stage 3B 产物目录：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/
```

Run matrix planned manifest：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/v5_run_matrix_manifest.json
sha256: 2f27739b640a3e59f4b5c998071c0f2c5a6ff69ff6475d6afdae740aeaecc238
```

Build command entry：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/build_v5_run_matrix_command_log_entry.json
sha256: 534d4c97eb5867d5b38fb8a50054ede9a62649e49ff59e1506fc04077f0a3b04
```

Build command log：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/v5_stage3b_run_matrix_build_command_log.jsonl
sha256: 511829e663f6af36eb92dfd1c4238d4c3555365f7a99eae383d92c58af365870
```

Executed run matrix manifest：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json
sha256: e1f03beab6267aebda6a3c725961b73dfbd9315e5ebfe524e622df91d62ad8f6
```

Matrix cell results：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_matrix_cell_results.jsonl
sha256: a699e6483d966a35e38e247346d2afef8112867c5a81edb53d87cb3d6101fedf
```

Execution report：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_stage3b_run_matrix_execution_report.json
sha256: 67d7da7fff1ff974d0f9551a3819764efa3237946bef06020f93a9726085e0b9
```

Run command entry：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/run_v5_run_matrix_command_log_entry.json
sha256: 38e7b432731a125f003c7f65e6071d5f1e6f5db41f26d24034b7a5530caf2e89
```

Run command log：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_stage3b_run_matrix_run_command_log.jsonl
sha256: 00560b4f0e1f292f870149b3e8170d43e16f3fd6204a53896924656b63b6fcad
```

## 验证命令和结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_run_matrix.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_run_matrix.py -q
PATH=.venv/bin:$PATH repo-harness build-v5-run-matrix --task-set-manifest runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --provider-gate-report runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json --provider-cost-budget-report runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json --output-dir runs/v5-stage3b-run-matrix-20260505T164640Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/v5_run_matrix_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness run-v5-run-matrix --run-matrix-manifest runs/v5-stage3b-run-matrix-20260505T164640Z/v5_run_matrix_manifest.json --provider-cost-budget-report runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json --output-dir runs/v5-stage3b-run-matrix-20260505T164640Z/execution --allow-local-secret-file --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --assert-complete
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py tests/unit/test_v5_provider_gate.py tests/unit/test_v5_run_matrix.py -q
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-evidence-integrity runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-gate runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-cost-budget runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json --assert-consistent
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer" runs/v5-stage3b-run-matrix-20260505T164640Z
```

`rg` 密钥和 Authorization marker 扫描无输出。

完整 V5 相关测试结果：

```text
50 passed in 1.01s
```

完整测试结果：

```text
762 passed in 597.41s
```

本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync acceptance bundle immutable inspect。V4 doc-sync bundle immutable proof 仍然只作为 Stage 0 preimplementation baseline proof 使用。

## 正例证据

- `planned_matrix_cell_count=6`。
- 执行后 `agent_run_started=true`。
- 执行后 `provider_api_called=true`。
- `actual_provider_calls=6`。
- `real_agent_run_task_count=6`。
- `real_provider_families_with_actual_runs=["deepseek"]`。
- `core_real_provider_floor_satisfied=true`。
- 每条 result 的 `actual_provider_call_count=1`。
- 每条 result 的 `normalized_provider_status=primary_attempted`。
- 每条 result 的 `final_verifier_status=not_executed_stage3b_minimal_provider_loop`。
- 每条 result 的 `raw_provider_artifact_count=2`，且 `raw_provider_redaction_failure_count=0`。

## 负例证据

- 早期尝试目录 `runs/v5-stage3b-run-matrix-20260505T161616Z/` 因 generated task YAML 使用相对 archive path，在 provider call 之前失败；该目录不作为 Stage 3B 通过证据。
- 早期尝试目录 `runs/v5-stage3b-run-matrix-20260505T161657Z/` 因完整 `run_task` baseline quality gate 在 provider call 前阻断，`actual_provider_calls=0`；该目录不作为 Stage 3B 通过证据。
- `inspect-v5-run-matrix --assert-complete` 会拒绝 provider call count 不足 6 的 executed manifest。
- 单元测试证明 DeepSeek credential 缺失时 builder 拒绝进入 planned run matrix。

## 允许降级项

- Stage 3B 允许只满足单一真实 provider family 的 `core_acceptance` 下限，不要求第二个真实 provider family。第二个真实 provider family 属于 Stage 3C / `resume_ready_acceptance`。
- Stage 3B 允许只记录 final verifier boundary，不要求把最小 provider run 标记为 accepted。accepted run 和训练导出分区由后续 Stage 4 按 final verifier 权威边界处理。

## 禁止降级项

- 不允许把 Stage 3B 的 `not_executed_stage3b_minimal_provider_loop` 写成 accepted。
- 不允许把 DeepSeek 以外的 OpenAI fallback-only evidence 计入 primary provider comparison。
- 不允许把 raw provider request 或 raw provider response 写入模型可见内容、训练内容、public-safe bundle 或 final acceptance docs。
- 不允许把早期失败目录作为 Stage 3B 通过证据。

## 已知限制

- 当前 Stage 3B 只完成 DeepSeek 单 provider family 的真实 agent loop evidence，因此还不能使用 `multi-provider agent runs` 或完整 `controlled multi-provider comparison` 强表述。
- 当前运行路径是 one-turn no-tool-call minimal loop，主要证明真实 provider 调用、trajectory 记录、raw provider artifact redaction 和固定控制变量绑定；它不是完整修复任务执行，也不是 final verifier accepted run。

## 是否偏离设计文档

没有偏离 Stage 3B 的 core 下限目标。实现上没有继续强行使用完整 `run_task` baseline gate，因为该 gate 会在真实 provider call 之前阻断当前 V5 候选任务。新的 `minimal_provider_agent_loop` 明确保留了 fixed task、fixed source hash、fixed provider、fixed scaffold、fixed budget、trajectory、raw provider artifacts 和 final verifier boundary，并且不声明 accepted。

## 自审结论

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段执行等价独立只读自审，记录见：

```text
docs/v5/review/implementation/05-real-provider-run-matrix-review.md
```

当前没有剩余 P1 或 P2。允许进入 V5 Stage 3C，但 Stage 3C 必须根据第二个真实 provider family 是否可用生成 provider comparison evidence 或 blocked claim，不能把 Stage 3B 的单 provider evidence 改写成 resume-ready multi-provider evidence。
