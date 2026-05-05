# V5 Stage 3A Provider Gate 和成本预算自审记录

## 审查范围

本记录覆盖 V5 Stage 3A provider gate、provider smoke structured evidence、provider raw content redaction policy 和 provider cost budget 的实现、测试和正式机器产物：

- `src/repo_harness/v5_provider_gate.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_provider_gate.py`
- `runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_registry_report.json`
- `runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json`
- `runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_smoke_report.json`
- `runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_raw_content_redaction_report.json`
- `runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_status_normalization_report.json`
- `runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json`

## 审查方式

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段按实施规则执行等价独立只读自审。自审只读取代码、测试和机器产物，不修改文件；发现需要修复的问题后，再单独进入修复步骤。

审查重点如下：

- OpenAI fallback 或 structured skip 是否可能被误计为真实 provider accepted run。
- provider raw request、provider raw response、Authorization marker 或 provider credential 原始值是否可能进入模型可见内容、训练内容或 public-safe 证据。
- cost budget 是否能阻止调用数量和成本代理值 overrun。
- builder 是否全部使用显式输入路径，默认不覆盖旧输出，并写入 command log。
- inspect 是否能不重新执行 builder 就复核关键不变量。

## 审查发现

### P2：cost budget builder 对自定义输出文件名缺少显式覆盖保护

问题：初版 `build_provider_cost_budget_report` 使用固定输出文件名集合检查 `v5_provider_cost_budget_report.json`、`build_v5_provider_cost_budget_command_log_entry.json` 和 `v5_stage3a_provider_cost_budget_command_log.jsonl` 是否已经存在。如果调用者传入非标准 `--output custom_cost_budget.json`，并且该文件已经存在，初版检查不会拒绝覆盖。

风险：V5 builder 的通用要求是输出已经存在时默认失败；非标准输出名也必须遵守这个规则，否则可能覆盖旧 evidence。

处理：已修复。`build_provider_cost_budget_report` 现在会额外检查 `output_path.exists()`，只要目标输出本身已经存在就失败。新增单元测试 `test_v5_provider_cost_budget_refuses_existing_custom_output`。

状态：已关闭。

### P3：Stage 3A provider smoke 是 structured no-call smoke，不是真实 provider API smoke

问题：本阶段 `v5_provider_smoke_report.json` 记录的是 credential 和 adapter structured probe，没有调用 provider API，因此 raw request / response redaction report 中的 raw artifact count 为 `0`。这符合 Stage 3A 不执行真实 provider agent run 的安全边界，但它还不能证明真实 provider response artifact 的 redaction 行为。

风险：如果后续文档把 Stage 3A structured smoke 写成真实 provider run 或真实 raw artifact redaction proof，会造成 claim 过强。

处理：本阶段文档和机器产物明确写明 `provider_api_called=false`、`actual_real_provider_calls=0`。Stage 3B 必须在真实 provider run 之后重新产生 raw artifact scan，不能把 Stage 3A 的 policy-only zero counts 当作真实 provider raw artifact redaction proof。

状态：记录为后续项，不阻塞进入 Stage 3B。

## 已核查的不变量

### OpenAI fallback 不会被误计为 primary provider

已核查：

- Provider registry 中 `openai.adapter_status=fallback_only`。
- Provider credential gate 中 `openai.adapter_status=fallback_only`。
- Provider status normalization report 中 `fallback_success_counts_as_primary_openai_run=false`。
- `inspect-v5-provider-gate --assert-consistent` 会拒绝 OpenAI 被标记成 `primary_supported`。
- 单元测试覆盖 OpenAI primary 篡改负例。

结论：当前实现不会把 OpenAI fallback 或 OpenAI fallback readiness 计为真实 primary OpenAI provider comparison evidence。

### Structured skip 不会进入真实 provider accepted rate

已核查：

- `credential_missing_skip`、`adapter_not_implemented_skip`、`cost_limited_structured_skip` 和 `primary_provider_comparison_not_enabled_skip` 都包含 `counts_toward_real_provider_accepted_rate=false`。
- `inspect-v5-provider-gate --assert-consistent` 检查每个 structured skip 不能计入真实 provider accepted rate。
- Provider cost budget 的 cost-limited skip 也必须包含 `counts_toward_real_provider_accepted_rate=false`。

结论：当前实现不会把 credential missing、adapter missing 或 cost-limited skip 计为真实 provider accepted run。

### Raw provider content 和 credential 原始值没有进入 Stage 3A 产物

已核查：

- `v5_provider_credential_gate_report.json` 中 `raw_secret_value_present=false`。
- `v5_provider_raw_content_redaction_report.json` 中 raw request / response 的 model-visible、trainable 和 public-safe 计数全部为 `0`。
- 使用 raw credential / Authorization 专门模式扫描正式 Stage 3A 产物无命中：

```bash
rg -n "\\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\\b|Authorization|Bearer" runs/v5-stage3a-provider-gate-20260505T155636Z
```

结果：无输出。

结论：本阶段没有把 raw provider request、raw provider response、Authorization marker 或 provider credential 原始值写入机器产物。

### Cost budget overrun 被拒绝

已核查：

- Builder 拒绝 `actual_real_provider_calls > max_real_provider_calls`。
- Builder 拒绝 `actual_cost_proxy_usd > max_cost_usd`。
- Inspect 也会复核 call count 和 cost proxy 未超过预算。
- 单元测试覆盖 provider call count overrun。

结论：当前 cost budget 在 Stage 3A 能阻止 overrun 产物被写成通过状态。

### Builder 和 command log

已核查：

- `build-v5-provider-gate` 显式接收 `--task-set-manifest` 和 `--output-dir`。
- `build-v5-provider-cost-budget` 显式接收 `--provider-gate-report` 和 `--output`。
- 两个 builder 默认拒绝覆盖已有输出。
- 两个 builder 都写入 command log entry 和 JSONL command log。
- command log 记录 argv、cwd、input refs、output refs、stdout sha256、stderr sha256、exit code 和工具版本。

结论：当前 Stage 3A builder 满足显式输入、显式输出和 command log 绑定要求。

### Inspect 可独立复核

已核查：

- `inspect-v5-provider-gate --assert-consistent` 可以读取 provider gate report，并进一步读取 registry、smoke、redaction 和 normalization refs。
- `inspect-v5-provider-cost-budget --assert-consistent` 可以读取 cost budget report，并进一步复核 provider gate ref。
- Inspect 不重新执行 builder，不读取 latest run，不依赖环境变量推断输入。

结论：当前 inspect 具备只读复核 Stage 3A 关键不变量的能力。

## 验证结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_provider_gate.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py tests/unit/test_v5_provider_gate.py -q
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-gate runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-cost-budget runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-evidence-integrity runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json --assert-clean
PATH=.venv/bin:$PATH python -m pytest -q
```

完整测试结果：

```text
759 passed in 605.05s
```

## 剩余风险和后续项

- Stage 3B 必须执行真实 provider smoke 或真实 provider agent run，并对真实 raw provider artifacts 做 redaction scan。Stage 3A 的 raw content report 是 policy-only zero-count gate，不能替代真实运行后的 raw artifact proof。
- 如果后续要让 OpenAI 计入 `resume_ready_acceptance` 的第二个真实 provider family，必须正式实现 primary OpenAI provider path，并同步修改 runner、experiment config allowlist、factory 测试和 comparison gate。当前 fallback-only 证据不能升级为 provider comparison evidence。
- Anthropic Claude adapter 未实现，不阻塞 `core_acceptance`，但会阻塞任何三 provider 或 Anthropic provider run 相关强表述。

## 复审结论

P2 已修复，当前没有剩余 P1 或 P2。P3 已作为 Stage 3B 后续项记录。允许进入 V5 Stage 3B，但 Stage 3B 必须继续绑定当前 Stage 3A provider gate 和 cost budget，且不能把 Stage 3A 的 structured smoke readiness 或 structured skip 计为真实 provider agent run evidence。
