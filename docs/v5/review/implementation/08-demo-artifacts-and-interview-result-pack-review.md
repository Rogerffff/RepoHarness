# V5 Stage 5 Demo Artifacts 和 Interview Result Pack 自审记录

## 审查范围

本记录覆盖 V5 Stage 5 public-safe demo artifacts、result summary、claim gate、interview result pack 和对应 inspect 逻辑：

- `src/repo_harness/v5_demo_artifacts.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_demo_artifacts.py`
- `runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_artifact_index.json`
- `runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_public_demo_bundle_manifest.json`
- `runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_result_summary_table.json`
- `runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_claim_gate_report.json`
- `runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_result_pack_manifest.json`

## 审查方式

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段按实施规则执行等价独立只读自审。自审只读取代码、测试和机器产物；发现需要修复的问题后，再单独进入修复步骤。

审查重点如下：

- Public-safe bundle 是否只引用 `share_safe=true` 且 `visibility=public_safe` 的 artifact。
- Demo card、walkthrough、result summary 和 resume bullets 是否错误使用被 claim gate 阻断的强表述。
- Result summary 是否明确真实 provider accepted rate 的分母，且不混入 mock / replay、structured skip、diagnostic-only 或 stress records。
- Canonical walkthrough 是否把 final verifier 未执行的 run 错误写成 accepted patch demonstration。
- Interview Q&A evidence 和 public-safe mapping 是否引用 evaluator-only 原始证据或 provider 私有载荷。

## 审查发现

### P3：Stage 5 result summary 是展示摘要，不是最终 acceptance report

问题：Stage 5 的 result summary 已经能解释任务库存、真实 provider run、导出分区和 claim gate 状态，但它不是 Stage 6 的 final acceptance report。

风险：如果后续文档把 Stage 5 result summary 直接写成 final acceptance report，可能混淆展示材料和验收权威报告。

处理：Stage 5 claim gate 只写 `stage5_final`，并保留 `resume_ready_acceptance_status=blocked`。Stage 6 必须单独生成 `v5_acceptance_inputs.json`、`v5_acceptance_report.json` 和 acceptance bundle。

状态：记录为 Stage 6 文档约束，不阻塞进入 Stage 6。

## 已核查的不变量

### Public-safe bundle 未引用内部私密证据

已核查：

- `v5_public_demo_bundle_manifest.json` 中所有 artifact refs 都是 `visibility=public_safe` 且 `share_safe=true`。
- `provider_raw_content_count=0`。
- `evaluator_only_content_count=0`。
- `model_visible_leak_count=0`。
- `public_marker_scan.finding_count=0`。
- 外部敏感 marker 扫描无输出。

结论：Public-safe bundle 没有引用 provider 私有载荷、evaluator-only 原始证据或 credential marker。

### Claim gate 没有放宽 blocked 强表述

已核查：

- `v5_resume_claim_gate_report.json` 中 `stage=stage5_final`。
- `demo_share_safe_status=passed`。
- `provider_claim_status=blocked_single_provider_family_deepseek_only`。
- `preference_pair_claim_status=blocked_no_real_comparable_pair`。
- `blocked_claims` 仍包含 `multi-provider agent runs`、`controlled multi-provider comparison`、`preference export completed`、`interview-grade evaluation pack` 和 `resumable export stress tests`。
- `v5_interview_result_pack_manifest.json` 中 `blocked_claims_enforced=true`，`copy_safe_blocked_claims_count=0`。

结论：Stage 5 允许 public-safe demo artifact 表述，但没有允许 resume-ready 或 preference export 强表述。

### Result summary 分母定义清楚

已核查：

- `real_provider_runs.denominator=6`。
- `real_provider_runs.accepted_count=0`。
- `real_provider_runs.accepted_rate=0.0`。
- `real_provider_runs.denominator_excludes` 明确包含 `credential_missing_skip`、`adapter_not_implemented_skip`、`cost_limited_structured_skip`、`fallback_success`、`mock_or_replay_records`、`synthetic_safe_stress_records` 和 `diagnostic_only_records`。
- 分区统计包含 `real_provider_trainable_records=2`、`mock_or_replay_records=0`、`diagnostic_records=1`、`blocked_records=1`、`synthetic_safe_stress_records=0`。

结论：Result summary 没有把 skip、mock / replay、diagnostic-only 或 stress records 混入真实 provider accepted rate。

### Final verifier 权威性未被绕过

已核查：

- Canonical demo card 中 `accepted=false`。
- Canonical walkthrough 明确说明 Stage 3B 是最小真实 provider loop，没有执行 final verifier。
- Result summary 的 failure distribution 记录 `final_verifier_not_executed=6`。
- Stage 5 没有把任何 Stage 3B run 写成 accepted patch demonstration。

结论：Stage 5 没有用 demo card、walkthrough 或 result summary 覆盖 final verifier 权威性。

## 验证结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_demo_artifacts.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_demo_artifacts.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py tests/unit/test_v5_provider_gate.py tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py tests/unit/test_v5_demo_artifacts.py -q
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness build-v5-demo-artifacts --task-set-manifest runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --executed-run-matrix-manifest runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --export-pack-manifest runs/v5-stage4-export-pack-20260505T174200Z/v5_export_result_pack_manifest.json --stage4-claim-gate-report runs/v5-stage4-export-pack-20260505T174200Z/v5_resume_claim_gate_report.json --output-dir runs/v5-stage5-demo-artifacts-20260505T181800Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness build-v5-interview-result-pack --resume-artifact-index runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_artifact_index.json --stage5-claim-gate-report runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_claim_gate_report.json --docs12-path docs/12-resume-narrative-and-demo-artifacts.md --output-dir runs/v5-stage5-demo-artifacts-20260505T181800Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-evidence-integrity runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-gate runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_credential_gate_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-provider-cost-budget runs/v5-stage3a-provider-gate-20260505T155636Z/v5_provider_cost_budget_report.json --assert-consistent
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-run-matrix runs/v5-stage3c-comparison-reports-20260505T171500Z/v5_matrix_compare_scope_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-export-pack runs/v5-stage4-export-pack-20260505T174200Z/v5_export_result_pack_manifest.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_artifact_index.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_public_demo_bundle_manifest.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_result_summary_table.json --assert-share-safe
PATH=.venv/bin:$PATH repo-harness inspect-v5-demo-artifacts runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_result_pack_manifest.json --assert-share-safe
rg -n "\bsk-(proj-|ant-api03-)?[A-Za-z0-9_-]{12,}\b|Authorization|Bearer|raw_deepseek_provider_request|raw_deepseek_provider_response|provider raw request|provider raw response" runs/v5-stage5-demo-artifacts-20260505T181800Z
```

单元测试结果：

```text
tests/unit/test_v5_demo_artifacts.py: 1 passed in 0.23s
V5 focused tests: 53 passed in 1.61s
Full test suite: 765 passed in 706.29s
```

V2 regression inspect、V3 acceptance inspect、V3 acceptance bundle immutable inspect，以及 Stage 0 到 Stage 5 的 V5 inspect 链均已通过。本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync bundle immutable inspect；V4 closure baseline 继续只由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和对应 command log 绑定。

## 剩余风险和后续项

- Stage 6 必须引用 Stage 5 的 `v5_resume_claim_gate_report.json`，不能回退引用 Stage 3C 或 Stage 4 partial claim gate。
- Stage 6 final acceptance 文档必须继续说明 `resume_ready_acceptance` 当前 blocked，除非后续新增第二个真实 provider family 和真实可比较 preference pair。
- Stage 6 acceptance bundle 必须把 Stage 5 command log 和 artifact refs 绑定进去。

## 复审结论

当前没有剩余 P1 或 P2。P3 已作为 Stage 6 文档约束记录。允许进入 V5 Stage 6。
