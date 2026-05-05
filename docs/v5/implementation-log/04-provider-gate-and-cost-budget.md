# V5 Stage 3A Provider Gate 和成本预算实施日志

## 目标

Stage 3A 的目标是在进入真实 provider agent run matrix 之前，先把 provider registry、credential gate、provider smoke structured evidence、provider raw content policy 和 cost budget 做成可复核的机器门。这个阶段只建立门控和状态归一化，不执行真实 agent run，也不把任何 structured skip、fallback success 或 credential presence 计为真实 provider accepted run。

本阶段绑定的 task set 是 Stage 2B 已关闭严格库存门的正式 merged task set：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json
sha256: e77e197cd5e277bb4a389d7ace0e8475e78b6a274f77efcfd0308231e336771b
```

## 实现内容

本阶段新增两个 builder：

- `repo-harness build-v5-provider-gate`
- `repo-harness build-v5-provider-cost-budget`

`build-v5-provider-gate` 生成以下机器产物：

- `v5_provider_registry_report.json`
- `v5_provider_credential_gate_report.json`
- `v5_provider_smoke_report.json`
- `v5_provider_raw_content_redaction_report.json`
- `v5_provider_status_normalization_report.json`
- `build_v5_provider_gate_command_log_entry.json`
- `v5_stage3a_provider_gate_command_log.jsonl`

`build-v5-provider-cost-budget` 生成以下机器产物：

- `v5_provider_cost_budget_report.json`
- `build_v5_provider_cost_budget_command_log_entry.json`
- `v5_stage3a_provider_cost_budget_command_log.jsonl`

本阶段 provider 事实如下：

- `deepseek`：当前代码中是 primary supported provider；本阶段只记录脱敏凭证来源可用和 Stage 3B primary smoke ready，不调用 provider API。
- `openai`：当前代码中仍然只能作为 DeepSeek fallback smoke，不计入 primary provider comparison，也不计入 resume-ready 的第二个真实 provider family。
- `anthropic_claude`：进入 provider registry 和 credential gate，但当前 adapter 未实现，只能记录 `adapter_not_implemented_skip`。

## 主要修改文件

- `src/repo_harness/v5_provider_gate.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_provider_gate.py`

## 新增或更新的 schema

- `repo_harness_v5_provider_registry_report_v0`
- `repo_harness_v5_provider_credential_gate_report_v0`
- `repo_harness_v5_provider_smoke_report_v0`
- `repo_harness_v5_provider_raw_content_redaction_report_v0`
- `repo_harness_v5_provider_status_normalization_report_v0`
- `repo_harness_v5_provider_cost_budget_report_v0`

## 新增或更新的 inspect 命令

`inspect-v5-provider-gate --assert-consistent` 现在会复核：

- provider families 覆盖 `openai`、`deepseek` 和 `anthropic_claude`。
- `deepseek` 必须是 `primary_supported`。
- `openai` 必须是 `fallback_only`，不能伪装成 primary provider。
- `anthropic_claude` 必须是 `adapter_not_implemented`，除非后续阶段正式实现 adapter。
- structured skips 必须记录 provider id、skip type、credential status、adapter status、skip reason、affected matrix cells、是否影响 core acceptance、是否影响 resume-ready acceptance，并且不得计入真实 provider accepted rate。
- provider raw content policy 必须是 audit-only redacted。
- `skipped_no_credentials` 必须归一化为 `credential_missing_skip`。
- `fallback_success` 不能计入 primary OpenAI provider run。
- report 和引用的 provider registry、smoke、redaction、normalization 报告中不能包含疑似 raw provider credential marker、Authorization marker 或 Bearer marker。

`inspect-v5-provider-cost-budget --assert-consistent` 现在会复核：

- actual call count 不能超过 max call count。
- actual cost proxy 不能超过 max cost。
- cost-limited structured skip 不能计入真实 provider accepted rate。
- provider gate ref 可以解析，并且引用的 provider gate 本身通过一致性检查。

## 新增或更新的测试

`tests/unit/test_v5_provider_gate.py` 新增覆盖：

- provider gate builder 在环境变量存在时不把任何 raw credential value 写入报告。
- DeepSeek、OpenAI 和 Anthropic Claude 的 adapter status 与当前代码事实一致。
- credential missing skip、OpenAI primary comparison disabled skip 和 Anthropic Claude adapter not implemented skip 都不能计入真实 provider accepted rate。
- Stage 3A provider gate 拒绝绑定 strict inventory gate 尚未通过的 task set。
- `inspect-v5-provider-gate` 拒绝 OpenAI 被错误标记成 `primary_supported`。
- `inspect-v5-provider-gate` 拒绝疑似 raw provider credential marker。
- provider cost budget builder 拒绝 overrun。
- provider cost budget builder 对自定义 `--output` 文件名也默认拒绝覆盖已有文件。
- CLI 暴露 `build-v5-provider-gate` 和 `build-v5-provider-cost-budget`，并且构建结果可由 inspect 复核。

## 机器产物

正式 Stage 3A 产物目录：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/
```

Provider registry report：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_registry_report.json
sha256: a070385fa89c0cd83c27656a85de11f03620b72215d29ea1a1e5af6a4b55b56b
```

Provider credential gate report：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json
sha256: 6934ac7082af1a3e3d9e81841da98922971651ed8cab6bb7a50e6935c76fd4e7
```

Provider smoke structured report：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_smoke_report.json
sha256: a4629cb34dfc243ff1d21ac13bf76a84d3ed0e4a70a8ffcc3c452c8559d75713
```

Provider raw content redaction report：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_raw_content_redaction_report.json
sha256: 42b865f694f011b3ed88310f37af0fbf9b51e349e06787adf9171cd6d558671a
```

Provider status normalization report：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_status_normalization_report.json
sha256: ec10091f332b20e09f4aff0f2ad14ace7641a7e66ddd95a01a0bdb4cc8333df7
```

Provider cost budget report：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json
sha256: 06e8ca1b4afbb63cb4bc00819013bf1f749676ee328fcfd93066f9597872cff0
```

Provider gate command entry：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/build_v5_provider_gate_command_log_entry.json
sha256: 8e87445de9dec30fe5ef9739011ebe716c444b71f79a62296674f8f7191eadac
```

Provider gate command log：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_stage3a_provider_gate_command_log.jsonl
sha256: e2949dac89f1d109098262ee7a2b4b8e023565e5bbb0c91b18e716bed9572c2b
```

Provider cost budget command entry：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/build_v5_provider_cost_budget_command_log_entry.json
sha256: 04d1f716464e84c3ced7823e4da65feab731b25d34e0680960edf09a76bc3459
```

Provider cost budget command log：

```text
runs/v5-stage3a-provider-gate-20260505T155636Z/v5_stage3a_provider_cost_budget_command_log.jsonl
sha256: be2422a5f5ecd476d31c99a4e57fb663f68918972128e6fa3ff91b2a05745efc
```

## 验证命令和结果

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

本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync acceptance bundle immutable inspect。V4 doc-sync bundle immutable proof 仍然只作为 Stage 0 preimplementation baseline proof 使用。

## 正例证据

- provider gate 绑定的 task set 是 Stage 2B merged task set，`strict_inventory_gate=passed`。
- DeepSeek adapter status 是 `primary_supported`，provider API 调用次数为 `0`，Stage 3A 不把凭证可用性直接计为真实 provider run。
- OpenAI adapter status 是 `fallback_only`，同时记录 `credential_missing_skip` 和 `primary_provider_comparison_not_enabled_skip`，均不计入真实 provider accepted rate。
- Anthropic Claude adapter status 是 `adapter_not_implemented`，只记录 `adapter_not_implemented_skip`。
- provider raw content redaction report 中 provider raw request / response 的 model-visible、trainable 和 public-safe 计数全部为 `0`。
- cost budget report 中 `max_real_provider_calls=24`、`actual_real_provider_calls=0`、`max_cost_usd=5.0`、`actual_cost_proxy_usd=0.0`，未超过预算。

## 负例证据

- 单元测试证明 OpenAI 被篡改成 `primary_supported` 时，`inspect-v5-provider-gate --assert-consistent` 会失败。
- 单元测试证明疑似 raw provider credential marker 进入 provider gate report 时，`inspect-v5-provider-gate --assert-consistent` 会失败。
- 单元测试证明 provider cost budget overrun 会被 builder 拒绝。
- 单元测试证明 cost budget 使用自定义输出文件名且文件已存在时，builder 默认拒绝覆盖。
- `rg` 使用 raw credential / Authorization 专门模式扫描正式 Stage 3A 产物，无命中。

## 允许降级项

- Stage 3A 可以只生成 structured provider smoke evidence，不要求执行真实 provider agent run。真实 provider agent run 属于 Stage 3B。
- OpenAI 可以保留为 fallback-only，不阻塞 `core_acceptance`，但会阻塞 `resume_ready_acceptance` 中的多 provider family 强表述，除非后续正式实现 primary OpenAI provider 并产生真实运行证据。
- Anthropic Claude adapter 未实现时可以记录 structured skip，不阻塞 `core_acceptance`。

## 禁止降级项

- 不允许把 OpenAI fallback success 标记成 primary OpenAI accepted run。
- 不允许把 credential missing skip、adapter not implemented skip 或 cost-limited structured skip 计入真实 provider accepted rate。
- 不允许把 provider raw request、provider raw response、Authorization marker 或 provider credential 原始值写入模型可见内容、训练内容、public-safe demo bundle 或最终验收文档。
- 不允许在 cost budget 已耗尽后继续发起真实 provider 调用。
- 不允许把本阶段的 provider smoke structured evidence 计为 Stage 3B 的真实 agent run evidence。

## 已知限制

- Stage 3A 没有执行真实 provider API 调用，也没有产生真实 provider agent run record。Stage 3B 必须使用当前 provider gate 和 cost budget 作为前置输入，再产生至少一个真实 provider family 的 agent run evidence。
- OpenAI primary provider 仍未启用。若后续要争取 `resume_ready_acceptance`，必须正式修改 primary provider allowlist、runner、experiment config 和测试，不能把 fallback evidence 直接升级为 provider comparison evidence。
- Anthropic Claude adapter 当前未实现。本阶段只证明 adapter skip 被明确记录且不会误计入真实 provider run。

## 是否偏离设计文档

没有偏离 Stage 3A 的安全边界。Stage 3A 完成 provider registry、credential gate、cost budget 和 provider smoke structured evidence，但不提前执行真实 provider run matrix。真实运行和 comparison proof 留给 Stage 3B 和 Stage 3C。

## 自审结论

当前环境无法启动新的只读 subagent，原因是 agent 线程数量已经达到上限。因此本阶段执行了等价独立只读自审，并把审查记录写入：

```text
docs/v5/review/implementation/04-provider-gate-and-cost-budget-review.md
```

自审发现 1 个 P2：`build-v5-provider-cost-budget` 对非标准 `--output` 文件名没有显式拒绝覆盖已有文件。该问题已修复，并新增单元测试。修复后没有剩余 P1 / P2。一个 P3 后续项是 Stage 3B 需要把真实 provider smoke / real agent run 的 raw artifact redaction 从“policy-only zero counts”升级为真实运行后的 artifact scan。

## 是否可以进入下一阶段

可以进入 Stage 3B。Stage 3B 必须显式绑定：

- Stage 2B merged task set。
- Stage 3A provider credential gate report。
- Stage 3A provider cost budget report。

Stage 3B 不能把 Stage 3A 的 structured skip 或 smoke readiness 计为真实 agent run evidence。
