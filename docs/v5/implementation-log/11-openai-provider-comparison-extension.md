# V5 OpenAI Provider Comparison Extension

## 目标

本次扩展目标是在不放宽 V5 证据边界的前提下，把 OpenAI 从原先的 fallback-only 状态提升为可进入 V5 run matrix 的第二个真实 primary provider family，并用同一批任务、同一 scaffold、同一 budget、同一 tool policy、同一 context policy、同一 environment id 和同一 source tree hash 生成 provider comparison proof。

本次扩展只覆盖 provider axis。它不声明 scaffold comparison conclusion、budget comparison conclusion、preference export completed、完整 interview-grade evaluation pack 或 V5 final acceptance 重新通过。

## 定价和模型依据

已按 OpenAI 官方 pricing 文档确认：

- `gpt-5.4-nano` 可作为低成本链路测试模型。标准价格为 input `$0.20 / 1M tokens`、cached input `$0.02 / 1M tokens`、output `$1.25 / 1M tokens`。
- `gpt-5.5` 可作为正式代码任务评测模型。标准价格为 input `$5.00 / 1M tokens`、cached input `$0.50 / 1M tokens`、output `$30.00 / 1M tokens`。
- 官方文档地址：`https://developers.openai.com/api/docs/pricing`。

## 实现内容

主要修改文件：

- `src/repo_harness/model_client/providers/openai.py`
- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/v5_provider_gate.py`
- `src/repo_harness/v5_run_matrix.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_provider_client.py`
- `tests/unit/test_model_client_factory.py`
- `tests/unit/test_v5_provider_gate.py`
- `tests/unit/test_v5_run_matrix.py`
- `docs/v5/implementation-plan.md`

关键变更：

- `model.provider=openai` 现在可以作为 primary provider 构建 `OpenAIProviderClient`，不再只能作为 DeepSeek fallback smoke。
- OpenAI provider 支持在没有官方 Python SDK 时使用 Chat Completions HTTP fallback，仍然只写入 redacted raw request / response artifact。
- OpenAI provider 对 GPT-5 系列做了请求参数适配：`max_tokens` 转为 `max_completion_tokens`，并移除 `temperature`，避免 `gpt-5.4-nano` 和 `gpt-5.5` 的不兼容参数错误。
- `build-v5-provider-gate` 在显式 `--allow-local-secret-file` 时允许 DeepSeek 和 OpenAI 使用本地脱敏 secret file 作为 active credential source，报告只记录 `local_secret_file_redacted`。
- `build-v5-run-matrix` 新增 `--provider-id`、`--openai-model-id` 和 `--deepseek-model-id`，可以显式生成 DeepSeek / OpenAI 成对 provider cells。
- `run-v5-run-matrix` 不再把 provider、model、event filter 和 result family 写死为 DeepSeek。
- `build-v5-comparison-reports` 可以识别 `2 个任务 x DeepSeek/OpenAI x 同一 scaffold x 同一 budget` 的 provider comparison pair，并在满足条件时把 provider comparison 标为 `valid`。
- `inspect-v5-run-matrix` 允许部分 provider comparison matrix 作为补充证据存在；只有 `--assert-complete` 或 manifest 自身声明 `status=passed` 时才强制 6 条 core run floor。

## 机器产物

本次证据根目录：

```text
runs/v5-openai-provider-comparison-20260505T194739Z/
```

关键路径和 sha256：

```text
98a9e5ae64ed255a89b6838ffad331d0f59c643578b0e21629744c6d19535390  runs/v5-openai-provider-comparison-20260505T194739Z/provider_gate/v5_provider_credential_gate_report.json
68cd06ca678ac973308c282255a0af7bc9887001c5a537c72dcfa0a3c5c6969f  runs/v5-openai-provider-comparison-20260505T194739Z/provider_gate/v5_provider_cost_budget_report.json
42dc938d1e901a17601ccb9b9c8cb1eba8ff141ba7405790fced1c745b358e63  runs/v5-openai-provider-comparison-20260505T194739Z/nano_execution_concise/v5_run_matrix_manifest_executed.json
f80f167c48e6e9cd974d347431459915aab1f469f014df405d4fbf83f8c4cd43  runs/v5-openai-provider-comparison-20260505T194739Z/nano_execution_concise/v5_matrix_cell_results.jsonl
f61b80fcaca4153b8a651f619c458d3aa57024de8228c908032d0d019ac6d770  runs/v5-openai-provider-comparison-20260505T194739Z/formal_execution_gpt55_retry/v5_run_matrix_manifest_executed.json
76c22f058d97e1a10bd15267351ef8616295a380d178546447799afb48648084  runs/v5-openai-provider-comparison-20260505T194739Z/formal_execution_gpt55_retry/v5_matrix_cell_results.jsonl
26e96310dd02e70d842961602089f450221274736e4169ac484ad725a4a98520  runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_matrix_compare_scope_report.json
9d5ec96363c821d71c14d0ed291d7877bebbe14ec7e4cbf8fa18f752cc39e526  runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_provider_comparison_report.json
2e585717df16c8712877ae6bd61df467a16af5d8b6a39e1d59cde6b8cc091180  runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_resume_claim_gate_report.json
```

说明：`comparison_reports_gpt55_final/` 是首次正式 comparison report，后续只读审查发现其中 `provider_pairs.controlled_variables.final_verifier_plan_ref` 没有从 `controlled_variables_ref` 回填，已经由 `comparison_reports_gpt55_final_v2/` 取代。再后续 hardening follow-up 发现 `final_v2` 的 resume-ready 字段边界过强，已经由 `comparison_reports_gpt55_final_v3/` 取代。`final_v3` 没有重新调用 provider API，只重新读取既有 `formal_execution_gpt55_retry` evidence 生成 comparison report。

## 正例证据

低成本链路测试：

- 模型：`gpt-5.4-nano`
- 任务：`v5_task_005`，SWE-Bench-like anchor。
- 任务：`v5_pr_issue_click_3364`，GitHub PR / issue flow。
- 结果：两条 OpenAI real provider calls 均为 `primary_attempted`。
- token usage：
  - `v5_task_005`：input `800`，output `152`。
  - `v5_pr_issue_click_3364`：input `833`，output `149`。

正式 provider comparison：

- OpenAI 模型：`gpt-5.5`。
- DeepSeek 模型：`deepseek-v4-flash`。
- 任务：`v5_task_005` 和 `v5_pr_issue_click_3364`。
- 结果：4 个 cells 均为 `primary_attempted`。
- `v5_provider_comparison_report.json` 记录 `actual_records_by_provider.deepseek=2`、`actual_records_by_provider.openai=2`。
- `v5_matrix_compare_scope_report.json` 记录 `comparison_axis=provider`、`comparison_validity=valid`、`provider_pair_count=2`。
- 最新 conservative follow-up 中，`v5_resume_claim_gate_report.json` 只允许 `provider-axis supplemental comparison proof for two tasks across DeepSeek and OpenAI`。它不再允许把这组补充证据写成 `multi-provider agent runs` 或 `controlled multi-provider comparison completed`，因为当前 Stage 4 / Stage 5 / Stage 6 仍没有 trainable export、scaffold comparison、budget comparison 和 preference pair 的通过证据。

## 负例证据和修复

- 初始 `gpt-5.4-nano` 链路返回 `unsupported_parameter`，原因是 GPT-5 系列不接受旧的 `max_tokens` 参数。已修复为 `max_completion_tokens`。
- 初始 `gpt-5.5` 正式调用返回 `unsupported_value`，原因是该模型不接受显式 `temperature=0.0`。已在 OpenAI GPT-5 系列请求中移除显式 `temperature`。
- 上述失败调用均没有出现余额耗尽、鉴权失败或限流；没有触发充值等待。

## 验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_provider_client.py tests/unit/test_model_client_factory.py tests/unit/test_v5_provider_gate.py tests/unit/test_v5_run_matrix.py
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-gate runs/v5-openai-provider-comparison-20260505T194739Z/provider_gate/v5_provider_credential_gate_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-cost-budget runs/v5-openai-provider-comparison-20260505T194739Z/provider_gate/v5_provider_cost_budget_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/nano_execution_concise/v5_run_matrix_manifest_executed.json
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/formal_execution_gpt55_retry/v5_run_matrix_manifest_executed.json
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-openai-provider-comparison-20260505T194739Z/comparison_reports_gpt55_final_v3/v5_matrix_compare_scope_report.json --assert-complete
```

结果：

```text
33 passed
provider gate inspect passed
provider cost budget inspect passed
low-cost OpenAI run matrix inspect passed
formal DeepSeek/OpenAI run matrix inspect passed
provider comparison scope inspect passed
```

额外执行 secret marker 扫描：

```text
files_scanned=284
raw_secret_marker_hits=0
authorization_bearer_hits=0
```

## 允许降级项

- Stage 3B 的 provider runs 仍是 one-turn、no-tool-call、diagnostic-only agent loop，不执行 final verifier，因此不能把这些运行计为 accepted task 或 trainable accepted record。
- 当前 claim gate 只允许 provider-axis supplemental proof 表述，不能写成整体 resume-ready multi-provider comparison completed。

## 禁止降级项

- 不能把 OpenAI fallback success 计入 primary OpenAI provider evidence。
- 不能把 raw provider request / response 放入 model-visible transcript、trainable payload、public-safe demo bundle 或 final acceptance docs。
- 不能因为 provider comparison valid 就声明 scaffold comparison 或 budget comparison conclusion。
- 不能声明 V5 final acceptance 已重新通过；本次没有重新生成 Stage 4、Stage 5 或 Stage 6 final acceptance bundle。

## 已知限制和后续项

- `scaffold comparison conclusion` 和 `budget comparison conclusion` 仍然被 `v5_resume_claim_gate_report.json` 阻断。
- `preference export completed`、`interview-grade evaluation pack` 和 `resumable export stress tests` 仍然被阻断。
- 如果要把这组 provider comparison proof 纳入 V5 final acceptance，需要重新生成 Stage 4 export pack、Stage 5 demo artifacts、Stage 6 acceptance inputs、acceptance report 和 acceptance bundle。
