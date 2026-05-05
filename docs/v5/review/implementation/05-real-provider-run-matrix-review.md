# V5 Stage 3B 最小真实 Provider Agent Run Matrix 自审记录

## 审查范围

本记录覆盖 V5 Stage 3B run matrix planning、DeepSeek 真实 provider agent loop 执行、matrix result inspect、raw provider artifact redaction 和 final verifier boundary：

- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_run_matrix.py`
- `runs/v5-stage3b-run-matrix-20260505T164640Z/v5_run_matrix_manifest.json`
- `runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json`
- `runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_matrix_cell_results.jsonl`
- `runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_stage3b_run_matrix_execution_report.json`
- `runs/v5-stage3b-run-matrix-20260505T164640Z/execution/agent_runs/`

## 审查方式

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段按实施规则执行等价独立只读自审。自审只读取代码、测试和机器产物，不修改文件；发现需要修复的问题后，再单独进入修复步骤。

审查重点如下：

- 是否真的产生了 DeepSeek provider API 调用，而不是 credential readiness、structured skip 或 fallback success。
- 是否把未执行 final verifier 的 run 错误标记为 accepted。
- model-visible task input 是否只包含 adapter-visible 内容。
- raw provider request、raw provider response、Authorization marker 或 provider credential 原始值是否进入模型可见内容、训练内容或 public-safe 证据。
- provider cost budget 是否限制调用数量。
- run matrix inspect 是否能独立复核 executed evidence。

## 审查发现

### P2：完整 `run_task` 路径在 provider call 之前被 baseline quality gate 阻断

问题：初版 Stage 3B runner 直接调用 `run_task`。正式运行中，两个早期尝试目录显示 provider call 没有发生：

```text
runs/v5-stage3b-run-matrix-20260505T161616Z/
runs/v5-stage3b-run-matrix-20260505T161657Z/
```

第一次尝试因 generated task YAML 使用相对 archive path 失败。第二次修正为绝对 archive path 后，完整 `run_task` 仍然在 baseline quality gate 阶段以 `low_parser_confidence` 阻断，`actual_provider_calls=0`。

风险：如果只看 `agent_run_started=true` 或 planned matrix，不看 `actual_provider_call_count`，会把没有发生真实 provider 调用的结果误当作 Stage 3B 通过证据。

处理：已修复。`run-v5-run-matrix` 现在使用 `minimal_provider_agent_loop` 执行一轮真实 `AgentLoop`，直接调用 DeepSeek provider，并写入 trajectory、transcript、raw provider request / response、metrics 和 final verifier boundary。Inspect 以 `actual_provider_call_count > 0` 作为真实 provider evidence 的核心条件，且要求至少 6 条。

状态：已关闭。

### P2：无 provider call 时不应标记为 `primary_attempted`

问题：早期实现只要没有模型错误就把 cell result 标记为 `primary_attempted`。当 `run_task` 在 provider call 之前被 baseline gate 阻断时，`model_error_type` 为空，但 `actual_provider_call_count=0`，这会产生误导性的 primary attempted 计数。

风险：provider comparison 或 provider floor 统计可能把未发生 provider call 的 cell 当作真实尝试。

处理：已修复。当前 `_run_one_cell` 只有在存在 DeepSeek `model_call_completed` event 且无 model error 时才标记为 `primary_attempted`。无 provider call 或 model error 都不会计入 core real provider floor。

状态：已关闭。

### P3：Stage 3B 最小运行不是 final verifier accepted run

问题：`minimal_provider_agent_loop` 为了满足 core 下限，只执行 one-turn no-tool-call provider loop，不运行 final verifier。

风险：后续 Stage 4、Stage 5 或 Stage 6 如果把这些记录写成 accepted run，会违反 final verifier 权威性不变量。

处理：每条 run 写入 `final_verifier_boundary.json`，明确 `final_verifier_ran=false`、`accepted=false`、`counts_toward_primary_accepted_rate=false`。Stage 3B 文档和 result summary 也只称其为真实 provider agent loop evidence，不称其为 accepted run。

状态：记录为后续约束，不阻塞进入 Stage 3C。

## 已核查的不变量

### 真实 provider 调用已经发生

已核查：

```text
actual_provider_calls=6
real_agent_run_task_count=6
real_provider_families_with_actual_runs=["deepseek"]
provider_api_called=true
core_real_provider_floor_satisfied=true
```

每条 matrix cell result 的 `actual_provider_call_count=1`，并且 trajectory events 中存在 `model_call_completed`，其中 `provider=deepseek`。

结论：Stage 3B 的 core real provider floor 已经由真实 DeepSeek provider 调用满足。

### Final verifier 权威性没有被绕过

已核查：

- 每条 result 的 `final_verifier_status=not_executed_stage3b_minimal_provider_loop`。
- 每条 run 的 `final_verifier_boundary.json` 中 `final_verifier_ran=false`。
- 每条 run 的 `accepted=false`。
- 每条 result 的 `counts_toward_primary_accepted_rate=false`。

结论：当前实现没有把 patch quality、provider response 或 agent final answer 提升为 accepted。Accepted 状态仍然只能由 final verifier 决定。

### Model-visible 输入没有包含 evaluator-only evidence

已核查：

- `minimal_provider_agent_loop` 的 system message 明确说明 hidden evaluator evidence、reward metadata、raw provider payload 和 post-patch verifier logs 不可用。
- user message 只包含 sanitized task statement、visible constraints、source tree hash、scaffold、budget 和 allowed tools。
- user message 不包含 gold patch、raw test patch、hidden selector、official resolved status、review comment、fix commit URL、merge commit URL、reward scalar 或 reward label。

结论：Stage 3B model-visible task input 只来自 adapter-visible 内容和固定控制变量。

### Raw provider artifacts 已脱敏

已核查：

- 每条 result 的 `raw_provider_artifact_count=2`。
- 每条 result 的 `raw_provider_redaction_failure_count=0`。
- 每条 result 的 `all_raw_provider_artifacts_redacted=true`。
- 使用 raw credential / Authorization 专门模式扫描正式 Stage 3B 产物无输出：

```bash
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer" runs/v5-stage3b-run-matrix-20260505T164640Z
```

结论：本阶段没有把 raw provider credential、Authorization marker 或 Bearer marker 写入机器产物。

### Provider cost budget 未超出

已核查：

```text
actual_provider_calls=6
max_real_provider_calls=24
```

结论：Stage 3B 实际 provider call 数量低于 Stage 3A cost budget 上限。

### Inspect 可独立复核 executed evidence

已核查：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --assert-complete
```

结果：

```text
Inspect V5 run matrix: complete
Inspect V5 run matrix: passed
```

新增单元测试也构造了不依赖网络的 executed manifest，证明 inspect 能在不重新执行 provider call 的情况下复核 6 条真实 provider evidence 结构。

## 验证结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_run_matrix.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_run_matrix.py -q
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
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/v5_run_matrix_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --assert-complete
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

## 剩余风险和后续项

- Stage 3C 需要检查第二个真实 provider family 是否可用。如果不可用，必须生成 blocked claim，不能把 DeepSeek 单 provider evidence 写成 multi-provider evidence。
- Stage 4 需要把 Stage 3B 的未 accepted run 正确分入 diagnostic-only、failure 或 blocked 相关分区，不能进入 accepted trainable payload。
- Stage 5 public-safe bundle 不能包含 raw provider request、raw provider response、reward scalar、reward label 或 final verifier raw output。

## 复审结论

P2 已修复，当前没有剩余 P1 或 P2。P3 已作为后续约束记录。允许进入 V5 Stage 3C。Stage 3C 的进入条件是继续绑定当前 Stage 3B executed manifest，并且不能把单 provider core evidence 升级成 `resume_ready_acceptance` 的多 provider 强表述。
