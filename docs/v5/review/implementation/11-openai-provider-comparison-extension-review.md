# V5 OpenAI Provider Comparison Extension Review

## 审查范围

本审查覆盖 OpenAI provider comparison 扩展：

- OpenAI primary provider 接入。
- V5 provider gate、run matrix、comparison report 和 claim gate。
- 新增低成本 `gpt-5.4-nano` 链路测试证据。
- 新增正式 `gpt-5.5` 与 DeepSeek 成对 provider comparison evidence。
- 相关单元测试、实现日志和范围文档同步。

## 第一轮只读审查

审查方式：subagent 只读审查，没有修改文件。

### P1

无。

### P2

发现：provider comparison validity gate 对 `final_verifier_plan_ref` 的受控变量一致性判断不可靠。

具体问题：

- Stage 3C 把 `final_verifier_plan_ref` 列为受控变量。
- 但旧的 matrix cell result 没有把 `cell.final_verifier_plan_ref` 写到 result 顶层。
- `_provider_comparison_key()` 只读 result 顶层字段，导致实际得到 `None`。
- 这样 DeepSeek 和 OpenAI 两侧即使 final verifier plan 不一致，也可能因为两边都是 `None` 而被配对并标为 `valid`。
- 初版报告 `runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final/v5_provider_comparison_report.json` 中 `provider_pairs.controlled_variables.final_verifier_plan_ref` 显示为 `null`。

处理：

- `_cell_identity()` 现在写入 `final_verifier_plan_ref`。
- `_provider_comparison_key()` 和 provider pair 报告现在通过 `_controlled_value()` 读取受控变量。
- 如果旧 result 缺少顶层字段，`_controlled_value()` 会回读 `controlled_variables_ref` 指向的 JSON。
- 新增负例测试：当 DeepSeek 和 OpenAI 都是 `primary_attempted`，但 final verifier plan 不一致时，provider comparison 必须保持 `invalid`，`resume_ready_provider_comparison_satisfied=false`，`provider_pairs=[]`。
- 没有重新调用 provider API，只重新生成 comparison report，输出到 `comparison_reports_gpt55_final_v2/`。

### P3

发现：初版测试缺少 provider comparison controlled-variable mismatch 负例。

处理：已通过 `tests/unit/test_v5_run_matrix.py` 新增 final verifier plan mismatch 负例覆盖。

## 第二轮只读复审

审查方式：subagent 只读复审，没有修改文件，也没有运行 provider API。

复审结论：

- 未发现新的 P1 或 P2。
- `src/repo_harness/v5_run_matrix.py` 已经把 `final_verifier_plan_ref` 纳入 provider comparison key。
- 旧 result 缺少顶层 `final_verifier_plan_ref` 时，会回读 `controlled_variables_ref`。
- `tests/unit/test_v5_run_matrix.py` 已新增 final verifier plan 不一致时 comparison invalid 的负例。
- `runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v2/v5_provider_comparison_report.json` 中两组 provider pair 都包含非空 `final_verifier_plan_ref`，并且 provider comparison 仍为 `valid`。

## 安全和边界核查

OpenAI raw request / response：

- 仍通过 `write_provider_request_artifact()` 和 `write_provider_response_artifact()` 写入。
- payload 中 `export_allowed=false`。
- payload 中 `training_payload_allowed=false`。
- artifact redaction status 为 `redacted`。
- 没有进入 model-visible task input、trainable payload 或 public-safe demo bundle。

凭证扫描：

```text
files_scanned=291
raw_secret_marker_hits=0
authorization_bearer_hits=0
```

Provider claim gate：

- 允许 provider-axis 的 `multi-provider agent runs`。
- 允许 provider-axis 的 `controlled multi-provider comparison`。
- 继续阻断 `scaffold comparison conclusion`、`budget comparison conclusion`、`preference export completed`、完整 `interview-grade evaluation pack` 和 `resumable export stress tests`。

## 验证命令

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_v5_run_matrix.py tests/unit/test_provider_client.py tests/unit/test_model_client_factory.py tests/unit/test_v5_provider_gate.py
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-gate runs/v5-openai-provider-comparison-20260505T194739Z/provider_gate/v5_provider_credential_gate_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-cost-budget runs/v5-openai-provider-comparison-20260505T194739Z/provider_gate/v5_provider_cost_budget_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/nano_execution_concise/v5_run_matrix_manifest_executed.json
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/formal_execution_gpt55_retry/v5_run_matrix_manifest_executed.json
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v2/v5_matrix_compare_scope_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
```

结果：

```text
773 passed
V2 acceptance inspect passed
V3 acceptance inspect passed
V3 acceptance bundle immutable inspect passed
V5 provider gate inspect passed
V5 provider cost budget inspect passed
V5 low-cost OpenAI run matrix inspect passed
V5 formal DeepSeek/OpenAI run matrix inspect passed
V5 provider comparison scope inspect passed
```

## 是否允许提交

允许提交。

剩余限制不是阻塞项：

- 当前 provider comparison proof 只覆盖 provider axis。
- 还没有补齐 scaffold comparison、budget comparison、preference pair、Stage 4 export regeneration、Stage 5 demo regeneration 或 Stage 6 final acceptance regeneration。
- 因此不能把本次扩展描述成 V5 final acceptance 已通过，也不能声明完整 resume-ready acceptance 已通过。
