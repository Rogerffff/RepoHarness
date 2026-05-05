# V5 Stage 5 Demo Artifacts 和 Interview Result Pack 实施日志

## 目标

Stage 5 的目标是把 V5 的机器证据整理成面试官可以快速理解、现场可以追问、简历可以安全引用的展示材料。本阶段不放宽 Stage 3C 和 Stage 4 已经阻断的强表述：当前仍不能声明多 provider 可比结论、preference export 已完成，或者 export stress test 已完成。

本阶段输入如下：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json
runs/v5-stage3b-run-matrix-20260505T164640Z/execution/v5_run_matrix_manifest_executed.json
runs/v5-stage4-export-pack-20260505T174200Z/v5_export_result_pack_manifest.json
runs/v5-stage4-export-pack-20260505T174200Z/v5_resume_claim_gate_report.json
docs/12-resume-narrative-and-demo-artifacts.md
```

## 实现内容

本阶段新增 CLI：

```bash
repo-harness build-v5-demo-artifacts
repo-harness build-v5-interview-result-pack
```

`build-v5-demo-artifacts` 生成 demo card、canonical walkthrough、public-safe bundle、resume artifact index、repro command index、result summary、redacted transcript index、permission/network risk audit、Claude Code invariant mapping、negative inspect report 和 Stage 5 final claim gate。

`build-v5-interview-result-pack` 生成 interview result pack manifest、简历 claim templates、简历 bullet 草稿、interview Q&A evidence 和 public-safe artifact mapping。

## 主要修改文件

- `src/repo_harness/v5_demo_artifacts.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v5_demo_artifacts.py`

## 新增或更新的 inspect 行为

`inspect-v5-demo-artifacts --assert-share-safe` 现在会对 Stage 5 产物执行更深层检查：

- `V5ResumeArtifactIndex` 只能引用 `public_safe` 且 `share_safe=true` 的 artifact。
- Public demo bundle 的 provider 私有载荷计数、evaluator-only 内容计数和模型可见泄漏计数必须为 `0`。
- Demo transcript index 的 `model_visible_leak_count` 必须为 `0`。
- Result summary 必须包含 trainable、diagnostic、blocked、mock / replay 和 synthetic-safe stress records 的分区统计。
- Result summary 的真实 provider accepted rate 分母必须明确排除 credential missing skip、mock / replay records 和 synthetic-safe stress records。
- Stage 5 resume artifact index 必须绑定 `stage5_final` claim gate。
- Stage 5 claim gate 必须保留对多 provider、preference export 和 stress test 强表述的阻断。
- Interview result pack 必须记录 `blocked_claims_enforced=true` 且 `copy_safe_blocked_claims_count=0`。

## 新增或更新的测试

`tests/unit/test_v5_demo_artifacts.py` 覆盖：

- `build-v5-demo-artifacts` 可以从任务库存、executed run matrix、export pack 和 Stage 4 claim gate 生成 public-safe demo artifacts。
- `inspect-v5-demo-artifacts --assert-share-safe` 可以复核 `v5_resume_artifact_index.json`。
- Stage 5 claim gate 的 `stage=stage5_final`，`demo_share_safe_status=passed`。
- Result summary 的真实 provider 分母为实际 provider run，且明确排除 mock / replay records。
- `build-v5-interview-result-pack` 可以生成 interview result pack manifest。
- `inspect-v5-demo-artifacts --assert-share-safe` 可以复核 interview result pack manifest。
- Interview result pack 记录 `blocked_claims_enforced=true` 和 `copy_safe_blocked_claims_count=0`。

## 机器产物

正式 Stage 5 产物目录：

```text
runs/v5-stage5-demo-artifacts-20260505T181800Z/
```

关键产物如下：

```text
runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_artifact_index.json
sha256: 1053d267704f8fa05db992e88bf9373b339ef8640c2e36b31d34669ade524226

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_public_demo_bundle_manifest.json
sha256: b7af659882b523c00bfef1521857b6296621f60fa0a1ca31d2d23d5009e063e4

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_result_summary_table.json
sha256: 3209d4260cd52d978d512ed9d23d8ca6cbbb2c2cceaceea32277a7730cb528ce

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_demo_card.md
sha256: ba927dee6a44ec951e4bae1b11ce693a25bd9f90e3e4d50012d2d9421bb83d70

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_demo_card.json
sha256: 01a54af6daa21a3fb3fbb0ebe022e58755ba1cbab0fe17fac18c4913458936e3

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_canonical_demo_walkthrough.md
sha256: 4e4bc18524276880e0a1431a995a6c07e2fe5be070430e4e01acfb867eb8c9c2

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_demo_transcript_index.json
sha256: a658504436ca2334c97027d6b04e3278a53c2c724006285160c74289a81511a4

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_claim_gate_report.json
sha256: eff8f876cec262e0f8b7260398339a4be7a8fabe055544d0c56c25def013ffdf

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_result_pack_manifest.json
sha256: b7d6faa74346a36d8354e0ddb15349b55e5cb3e71d17f14e4bbc9764a0413a60

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_claim_templates.json
sha256: d56aab7acf4b0bd4261fe2775d107716d76ba0d098a10c1da136228bf587cc82

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_resume_bullets.md
sha256: 5c0df14ef903153b6c28d50e7d35d8b9bff25bcc169d7fd711aee8456b55e507

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_interview_qa_evidence.json
sha256: 9d12fe017641b4e8d6e6671d2b643c6df90b82cfc7b04b35f35410fde3148556

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_public_safe_artifact_mapping.json
sha256: 56d908d0345690304b6bdaa5962d70e24c028f66dce8f3ae28ddf9d2655df62b
```

Command log：

```text
runs/v5-stage5-demo-artifacts-20260505T181800Z/build_v5_demo_artifacts_command_log_entry.json
sha256: bcfe6562219dde219e78cfc877c159ede0a5263f3802bdf578863eb07fc861ba

runs/v5-stage5-demo-artifacts-20260505T181800Z/build_v5_interview_result_pack_command_log_entry.json
sha256: b992627e80d9286c3d5a7ea23c48bfdc7d0b66f22ec2dfb99365ece54c4e8753

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_stage5_demo_artifacts_command_log.jsonl
sha256: 237b91c2f220bfb1ccbd8386fef88ff005ffd003fd6f8673e4266b8416fcad8d

runs/v5-stage5-demo-artifacts-20260505T181800Z/v5_stage5_interview_result_pack_command_log.jsonl
sha256: 620b277aaab72ee1bf542dc876da7a8ad4aa8b103eab5fef0a08c98815921661
```

## 验证命令和结果

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

`rg` 密钥、Authorization marker、Bearer marker、raw provider marker 和 provider raw request / response phrase 扫描无输出。

V2 regression inspect、V3 acceptance inspect、V3 acceptance bundle immutable inspect，以及 Stage 0 到 Stage 5 的 V5 inspect 链均已通过。本阶段没有在包含 V5 源码变更的当前工作区重新运行旧 V4 doc-sync bundle immutable inspect；V4 closure baseline 继续只由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和对应 command log 绑定。

## 正例证据

- `v5_resume_artifact_index.json` 的 `share_safe_status=passed`。
- `v5_public_demo_bundle_manifest.json` 的 provider 私有载荷计数、evaluator-only 内容计数和模型可见泄漏计数均为 `0`。
- `v5_result_summary_table.json` 分列真实 provider trainable records、mock / replay records、diagnostic records、blocked records 和 synthetic-safe stress records。
- `v5_result_summary_table.json` 的真实 provider accepted rate 分母明确排除 credential missing skip、mock / replay records 和 synthetic-safe stress records。
- `v5_resume_claim_gate_report.json` 的 `stage=stage5_final`，`demo_share_safe_status=passed`。
- `v5_interview_result_pack_manifest.json` 的 `blocked_claims_enforced=true`，`copy_safe_blocked_claims_count=0`。

## 负例证据

- Public demo bundle 如果引入 provider 私有载荷、evaluator-only 内容或模型可见泄漏，`inspect-v5-demo-artifacts --assert-share-safe` 会失败。
- Provider、preference pair 或 stress test 仍然被 claim gate 阻断时，interview result pack 不允许把对应强表述放入 copy-safe bullets。
- Result summary 如果缺少分区统计或分母排除规则，`inspect-v5-demo-artifacts --assert-share-safe` 会失败。

## 允许降级项

- Stage 5 可以生成 public-safe demo artifact 和 interview result pack，但不能把它写成 `resume_ready_acceptance` 已通过。
- Demo walkthrough 可以讲通 evidence chain，但必须说明 canonical run 的 final verifier 未执行，不能写成 accepted patch demonstration。

## 禁止降级项

- 不允许把 provider 私有载荷、evaluator-only 证据、隐藏 verifier 细节、credential marker 或 reward 数值写入 public-safe bundle。
- 不允许在 copy-safe bullets 中写入被 claim gate 阻断的强表述。
- 不允许把 mock / replay、structured skip、diagnostic-only 或 stress records 混入真实 provider accepted rate。

## 已知限制

- `resume_ready_acceptance` 仍然 blocked，因为当前只有一个真实 provider family，且没有真实可比较 preference pair。
- `interview-grade evaluation pack` 的完整强表述仍在 blocked claims 中；当前只能保守描述为 public-safe demo artifacts 和 result summary 已生成。

## 自审结论

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段执行等价独立只读自审，记录见：

```text
docs/v5/review/implementation/08-demo-artifacts-and-interview-result-pack-review.md
```

当前没有剩余 P1 或 P2。允许进入 V5 Stage 6，但 Stage 6 必须引用 Stage 5 final claim gate，不得回退引用 Stage 3C 或 Stage 4 的 partial claim gate。
