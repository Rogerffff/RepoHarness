# V5 Stage 4 Export Result Pack 实施日志

> 历史记录说明：本日志记录的是 2026-05-05 首次 Stage 4 export pack 实施状态。后续 hardening 已经撤回“未通过 final verifier 的真实 provider run 可以进入 SFT 或 reinforcement learning rollout trainable 分区”的做法。当前可信状态以 `docs/v5/implementation-log/10-hardening-fixes.md`、`docs/v5/final-acceptance.md` 和最新 hardening evidence 为准；本文件中的 `real_provider_trainable_records=2` 只能作为历史假阳性记录理解，不能作为当前 V5 验收结论。

## 目标

Stage 4 的目标是从 Stage 3 的真实 provider run evidence 生成严格分区、可审计、可导出的训练数据结果包。这个阶段不声称已经训练模型，也不把 Stage 3B 的最小 provider run 写成 final verifier accepted。首次实现曾把未通过 final verifier 的运行写成 sanitized plan / rollout format examples；后续 hardening 已经确认这是历史假阳性，当前可信实现要求 SFT 和 reinforcement learning rollout trainable 分区只能接收 `accepted=true` 且 `final_verifier_status=accepted` 的真实 provider run。

本阶段输入如下：

```text
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json
runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_resume_claim_gate_report.json
```

## 实现内容

本阶段新增 CLI：

```bash
repo-harness build-v5-export-pack
```

该 builder 生成以下机器产物：

- `v5_export_result_pack_manifest.json`
- `v5_sft_export.jsonl`
- `v5_rl_rollout_export.jsonl`
- `v5_failure_dataset.jsonl`
- `v5_diagnostic_only_records.jsonl`
- `v5_blocked_export_records.jsonl`
- `v5_preference_pair_blocked_report.json`
- `v5_reward_source_taxonomy_report.json`
- `v5_failure_taxonomy_report.json`
- `v5_export_audit_report.json`
- `v5_duplicate_record_report.json`
- `v5_training_payload_visibility_report.json`
- `v5_export_partition_summary.json`
- `v5_resume_claim_gate_report.json`
- `build_v5_export_pack_command_log_entry.json`
- `v5_stage4_export_pack_command_log.jsonl`

## 主要修改文件

- `src/repo_harness/v5_export_pack.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_export_pack.py`

## 新增或更新的 schema

- `repo_harness_v5_export_result_pack_manifest_v0`
- `repo_harness_v5_sft_record_v0`
- `repo_harness_v5_rl_rollout_record_v0`
- `repo_harness_v5_failure_dataset_record_v0`
- `repo_harness_v5_diagnostic_only_record_v0`
- `repo_harness_v5_blocked_export_record_v0`
- `repo_harness_v5_preference_pair_blocked_report_v0`
- `repo_harness_v5_reward_source_taxonomy_report_v0`
- `repo_harness_v5_failure_taxonomy_report_v0`
- `repo_harness_v5_export_audit_report_v0`
- `repo_harness_v5_duplicate_record_report_v0`
- `repo_harness_v5_training_payload_visibility_report_v0`
- `repo_harness_v5_export_partition_summary_v0`

`inspect-v5-export-pack --assert-clean` 现在会对 Stage 4 manifest 执行深度检查，包括 JSONL 记录数量、分区计数、preference pair blocked report、reward source taxonomy、export audit，以及 diagnostic-only / blocked record 不得进入 trainable payload。

## 新增或更新的测试

`tests/unit/test_v5_export_pack.py` 覆盖：

- `build-v5-export-pack` 可以从 executed run matrix 和 Stage 3C claim gate 生成 export pack。
- `inspect-v5-export-pack --assert-clean` 可以复核 export pack。
- 首次 manifest 曾记录 `real_provider_trainable_records=2`、`diagnostic_records=1`、`blocked_records=1`；该 trainable 计数已经被 hardening 撤回，当前可信 hardening export pack 中 `real_provider_trainable_records=0`。
- preference pair blocked report 会禁用 `preference export completed` 强表述。
- Stage 4 claim gate 会把 `preference_pair_claim_status` 设为 `blocked_no_real_comparable_pair`。

## 机器产物

正式 Stage 4 产物目录：

```text
runs/v5-stage4-export-pack-20260505T174200Z/
```

Export result pack manifest：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_export_result_pack_manifest.json
sha256: 7f1b8f9fc8ce37e5516013b24b329482c2d9c2619e4098b57e4b5a8c49699640
```

SFT export：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_sft_export.jsonl
sha256: e8f7fc2cd931b7b447ccaa6ea445076acec6623a98c24f2c6bb8acc108672a34
```

Reinforcement learning rollout export：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_rl_rollout_export.jsonl
sha256: 77c6e90d86ef35ff454a4d07b441f8e646493d60ab4bff540ca7414a463ab59e
```

Failure dataset：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_failure_dataset.jsonl
sha256: dc290b099c7bdb9568d783f213d7b1ed2d4e8dc5d41ae8bcfd0642e2eceb53ce
```

Diagnostic-only records：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_diagnostic_only_records.jsonl
sha256: e00f120100072c5405336c92b4ca7f8b94cfce3c06913a0b2717896e725b6a21
```

Blocked export records：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_blocked_export_records.jsonl
sha256: 0d1e7f69dc23067b2c3f9c4577cb1e1e93f38b8c611a543ae4173c40e7520068
```

Preference pair blocked report：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_preference_pair_blocked_report.json
sha256: 87e0ddda0fac9f5b9a15476f665a2f58feb40cab9445af199c2872bf8d601650
```

Reward source taxonomy report：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_reward_source_taxonomy_report.json
sha256: 167045dbd55c0ed1c7f16b9640d60886c7fae3d85a1d46b0feda79ade451b086
```

Failure taxonomy report：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_failure_taxonomy_report.json
sha256: d2aa6e3da1a4023d7dae81ad0d6cc0ac21f2506733ae2ee80e26ffa5e263b135
```

Export audit report：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_export_audit_report.json
sha256: 53cbdbbaba0051feb7bec46dd073bc1d886c1c3d2ac3d1f68a5d1bcf36b6e0d4
```

Stage 4 claim gate report：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_resume_claim_gate_report.json
sha256: ff17e5f28c346be57e9b135335dd7652cec1654e0233e1dd6694e7c80b282189
```

Command entry：

```text
runs/v5-stage4-export-pack-20260505T174200Z/build_v5_export_pack_command_log_entry.json
sha256: f4306ed834af0363e446bc423a920513fec4efd86dd63c9e6b63c01daeb05c77
```

Command log：

```text
runs/v5-stage4-export-pack-20260505T174200Z/v5_stage4_export_pack_command_log.jsonl
sha256: 8f144acb9f2e658889b1a6bf1adad50898a589d4e5d47570319f7cce87524948
```

## 验证命令和结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_export_pack.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_export_pack.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py tests/unit/test_v5_provider_gate.py tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py -q
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness build-v5-export-pack --executed-run-matrix-manifest runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --stage3-claim-gate-report runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_resume_claim_gate_report.json --output-dir runs/v5-stage4-export-pack-20260505T174200Z --fail-if-output-exists
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
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_matrix_compare_scope_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_resume_claim_gate_report.json
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-20260505T174200Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage4-export-pack-20260505T174200Z/v5_resume_claim_gate_report.json
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer|raw_deepseek_provider_request|raw_deepseek_provider_response" runs/v5-stage4-export-pack-20260505T174200Z
```

`rg` 密钥、Authorization marker、Bearer marker 和 raw provider artifact marker 扫描无输出。

测试结果：

```text
tests/unit/test_v5_export_pack.py: 1 passed in 0.20s
V5 focused tests: 52 passed in 1.16s
Full test suite: 764 passed in 744.93s
```

V2 regression inspect、V3 acceptance inspect、V3 acceptance bundle immutable inspect，以及 Stage 0 到 Stage 4 的 V5 inspect 链均已通过。本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync bundle immutable inspect；V4 closure baseline 继续只由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和对应 command log 绑定。

## 正例证据

- 历史假阳性：首次 Stage 4 记录过 `partition_counts.real_provider_trainable_records=2`。当前可信 hardening 结果已经将其修正为 `0`，因为没有任何真实 provider run 通过 final verifier。
- `partition_counts.diagnostic_records=1`。
- `partition_counts.blocked_records=1`。
- `partition_counts.mock_or_replay_records=0`。
- `partition_counts.synthetic_safe_stress_records=0`，并记录 stress partition status 为 `not_executed`。
- `v5_preference_pair_blocked_report.json` 中 `claim_gate_effect=disable_preference_export_completed_claim`。
- `v5_resume_claim_gate_report.json` 中 `stage=stage4_partial`。
- `preference_pair_claim_status=blocked_no_real_comparable_pair`。
- `export_pack_status=passed`。

## 负例证据

- `inspect-v5-export-pack --assert-clean` 会检查 diagnostic-only 和 blocked record 不能标记为 trainable。
- `inspect-v5-export-pack --assert-clean` 会检查 export audit 中 provider raw、reward scalar、reward label 和 trainable contamination 计数必须为 `0`。
- Stage 4 claim gate 继续把 `preference export completed` 放入 `blocked_claims`。

## 允许降级项

- 不再允许把未通过 final verifier 的 SFT 和 reinforcement learning rollout 样本作为 trainable 或可用降级项。它们只能作为历史假阳性背景说明；当前可信 trainable 分区必须为空，直到出现通过 final verifier 的真实 provider run。
- Stress partition 可以记录为 `0` 和 `not_executed`，因为 V5 P1 stress test 不属于 Stage 4 core 工作。

## 禁止降级项

- 不允许把 `accepted=false` 的 Stage 3B provider runs 写成 final verifier accepted。
- 不允许把 preference pair blocked report 改写成 preference export completed。
- 不允许把 diagnostic-only 或 blocked records 计入 trainable payload。
- 不允许把 raw provider request / response、reward scalar 或 reward label 放入 trainable payload。

## 已知限制

- Stage 4 仍不能通过 `resume_ready_acceptance`，因为 multi-provider comparison、preference pair 和 demo share-safe 状态仍然 blocked 或 pending。
- Stage 5 必须重新生成最终版 claim gate，并把 demo share-safe 状态从 `pending_stage5` 更新为 passed 或 blocked。

## 自审结论

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段执行等价独立只读自审，记录见：

```text
docs/v5/review/implementation/07-export-result-pack-review.md
```

该历史自审结论已被 hardening 撤回。当前可信结论是：Stage 4 的分区结构、failure / diagnostic / blocked evidence 和 preference blocked report 仍有展示价值，但 trainable export 未完成，不能作为 V5 core acceptance passed 的证据。
