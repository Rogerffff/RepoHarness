# V5 Stage 4 Export Result Pack 自审记录

> 历史记录说明：本审查记录的是 2026-05-05 首次 Stage 4 export pack 的阶段审查。后续 hardening 已经修复未通过 final verifier 的记录进入 trainable export 的问题；当前可信状态是 `real_provider_trainable_records=0`，SFT 和 reinforcement learning rollout trainable 分区为空。本文件中关于 `real_provider_trainable_records=2` 或 `non_accepted_trainable_record_count=2` 的描述只保留为历史问题背景，不能作为当前 V5 验收证据。

## 审查范围

本记录覆盖 V5 Stage 4 export result pack builder、export pack inspect、preference pair blocked report、reward source taxonomy、failure taxonomy、export audit 和阶段性 claim gate：

- `src/repo_harness/v5_export_pack.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_export_pack.py`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_export_result_pack_manifest.json`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_sft_export.jsonl`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_rl_rollout_export.jsonl`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_failure_dataset.jsonl`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_diagnostic_only_records.jsonl`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_blocked_export_records.jsonl`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_preference_pair_blocked_report.json`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_export_audit_report.json`
- `runs/v5-stage4-export-pack-20260505T174200Z/v5_resume_claim_gate_report.json`

## 审查方式

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段按实施规则执行等价独立只读自审。自审只读取代码、测试和机器产物，不修改文件；发现需要修复的问题后，再单独进入修复步骤。

审查重点如下：

- Stage 4 是否把非 accepted Stage 3B provider runs 错误写成 accepted patch demonstrations。
- SFT、reinforcement learning rollout、failure、diagnostic-only 和 blocked 分区是否清楚。
- preference pair 不可比较时是否生成 blocked report 并禁用 `preference export completed`。
- reward scalar、reward label、raw provider request / response 和 evaluator-only evidence 是否进入 trainable payload。
- failure taxonomy 是否记录 failure owner 和 failure category。

## 审查发现

### P3：SFT 和 RL rollout 是格式样本，不是 accepted patch demonstration

问题：Stage 3B 的最小真实 provider run 没有执行 final verifier，因此 Stage 4 的 SFT 和 reinforcement learning rollout 不能被写成 accepted 修复样本。

风险：如果后续文档只写“trainable records”而不说明 final verifier 状态，读者可能误解为 accepted patch demonstrations。

历史处理：首次 Stage 4 曾让每条 SFT 和 RL rollout record 保留 `accepted=false`、`final_verifier_status=not_executed_stage3b_minimal_provider_loop`，并把它们解释为 plan / rollout format examples。后续 hardening 已经确认这种处理仍会让 trainable export 语义过强，当前可信实现要求这些记录不进入 SFT 或 reinforcement learning rollout trainable 分区。

状态：记录为后续文档约束，不阻塞进入 Stage 5。

## 已核查的不变量

### Final verifier 权威性未被绕过

已核查：

- SFT record 中 `accepted=false`。
- RL rollout record 中 `accepted=false`。
- 两类记录都保留 `final_verifier_status=not_executed_stage3b_minimal_provider_loop`。
- Export audit 写明这些记录不是 accepted patch outcomes。

结论：Stage 4 没有把 provider response 或 assistant final answer 提升为 final verifier accepted。

### Export 分区完整

已核查：

```text
历史假阳性：real_provider_trainable_records=2。当前可信 hardening 结果已经修正为 real_provider_trainable_records=0。
mock_or_replay_records=0
diagnostic_records=1
blocked_records=1
synthetic_safe_stress_records=0
```

结论：Stage 4 明确区分 trainable、diagnostic-only、blocked、mock / replay 和 synthetic-safe stress 分区。

### Diagnostic-only 和 blocked records 没有进入 trainable payload

已核查：

- `v5_diagnostic_only_records.jsonl` 中 `trainable=false`。
- `v5_blocked_export_records.jsonl` 中 `trainable=false`。
- `v5_export_audit_report.json` 中 `diagnostic_only_trainable_count=0`。
- `v5_export_audit_report.json` 中 `blocked_trainable_count=0`。
- `inspect-v5-export-pack --assert-clean` 会复核这些条件。

结论：diagnostic-only 和 blocked records 没有混入 trainable payload。

### Preference pair 强表述已被阻断

已核查：

- `v5_preference_pair_blocked_report.json` 中 `blocked_reason=no_real_comparable_pair_yet`。
- `claim_gate_effect=disable_preference_export_completed_claim`。
- Stage 4 claim gate 中 `preference_pair_claim_status=blocked_no_real_comparable_pair`。
- Stage 4 claim gate 的 `blocked_claims` 包含 `preference export completed`。

结论：当前没有真实可比较 preference pair，也没有允许 preference export completed 表述。

### Reward 和 raw provider 内容没有进入模型可见或训练内容

已核查：

- `v5_reward_source_taxonomy_report.json` 中 `reward_scalar_model_visible_count=0`。
- `v5_reward_source_taxonomy_report.json` 中 `reward_label_model_visible_count=0`。
- `v5_export_audit_report.json` 中 `provider_raw_trainable_count=0`。
- `v5_export_audit_report.json` 中 `provider_raw_model_visible_count=0`。
- `v5_export_audit_report.json` 中 `reward_scalar_model_visible_count=0`。
- `v5_export_audit_report.json` 中 `reward_label_model_visible_count=0`。
- 使用密钥和 raw provider marker 扫描 Stage 4 产物无输出：

```bash
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer|raw_deepseek_provider_request|raw_deepseek_provider_response" runs/v5-stage4-export-pack-20260505T174200Z
```

结论：Stage 4 产物没有暴露 raw provider artifact、credential marker、reward scalar 或 reward label。

## 验证结果

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

测试结果：

```text
tests/unit/test_v5_export_pack.py: 1 passed in 0.20s
V5 focused tests: 52 passed in 1.16s
Full test suite: 764 passed in 744.93s
```

V2 regression inspect、V3 acceptance inspect、V3 acceptance bundle immutable inspect，以及 Stage 0 到 Stage 4 的 V5 inspect 链均已通过。本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync bundle immutable inspect；V4 closure baseline 继续只由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和对应 command log 绑定。

## 剩余风险和后续项

- Stage 5 必须生成 public-safe demo bundle 和 result summary，并重新生成 final claim gate。
- Final documentation 必须清楚说明 Stage 4 的 SFT 和 RL rollout 是 sanitized format examples，不是 final verifier accepted patch demonstrations。
- 如果后续新增真实可比较 preference pair，必须重建 export pack 和 claim gate；不能手工修改 blocked report。

## 复审结论

当前没有剩余 P1 或 P2。P3 已作为后续文档约束记录。允许进入 V5 Stage 5，但 Stage 5 不得放宽 preference export completed、multi-provider、scaffold 或 budget 强表述，除非重新生成对应证据并通过 inspect。
