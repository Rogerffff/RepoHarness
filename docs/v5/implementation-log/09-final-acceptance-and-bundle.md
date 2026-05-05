# V5 Stage 6 Final Acceptance 和 Acceptance Bundle 实施日志

## 目标

Stage 6 的目标是生成 V5 acceptance inputs、acceptance report、post-report reference integrity report、acceptance bundle、final command log、final acceptance 文档和 walkthrough，并严格保持 evidence 时序：

1. Acceptance inputs 只绑定 acceptance report 生成之前已经存在的证据。
2. Acceptance report 不引用 post-report inspect output 或 bundle final output。
3. Acceptance bundle 在 report 之后绑定 post-report output、pre-bundle command log 和 post-acceptance 文档。
4. Final command log 在 bundle 构建之后生成，避免 bundle builder 读取随后还会追加的日志。

## 实现内容

本阶段新增 CLI：

```bash
repo-harness build-v5-acceptance-inputs
repo-harness build-v5-acceptance-report
repo-harness build-v5-pre-bundle-command-log
repo-harness build-v5-acceptance-bundle
repo-harness plan-acceptance-bundle-inspect-entry
repo-harness build-v5-final-command-log
```

同时更新：

- `inspect-v5-inputs --assert-complete`：增加 acceptance inputs 深度检查。
- `inspect-v5-acceptance`：支持 reference integrity output/input 和 command log entry output。
- `inspect-acceptance-bundle`：支持 V5 acceptance bundle manifest，并允许通过 `--final-command-log` 检查 final command log lineage。

## 主要修改文件

- `src/repo_harness/v5_acceptance.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v3_acceptance.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_acceptance.py`
- `docs/v5/final-acceptance.md`
- `docs/v5/walkthrough.md`

## 新增或更新的 schema

- `repo_harness_v5_acceptance_bundle_manifest_v0`
- `repo_harness_v5_acceptance_report_reference_integrity_report_v0`
- `repo_harness_v5_acceptance_bundle_command_lineage_report_v0`
- `repo_harness_v5_final_acceptance_pretest_report_v0`

## 机器产物

正式 Stage 6 产物目录：

```text
runs/v5-final-acceptance-20260505T191500Z/
```

关键产物：

```text
runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_inputs.json
sha256: 31d30d00558b5c7ac761403fbfe5abb1c0b8e0c648139afd662a73bcd54e1dca

runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json
sha256: 575175f7be7f0c006c84af0e77bf32f877f0eaa4224ccd27bad0f0739bbe3522

runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report_reference_integrity_report.json
sha256: 4f75d92a7602d67675229959293ba14ab5ba3d6ef00e61b855adc7a35fedd9a4

runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_manifest.json
sha256: 73d327ea6efd11124d14f113ee4720ca31e7553e792799c52dec2d12371e4386

runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_command_lineage_report.json
sha256: ebfdbd4626d0530fc04acc909776b76126c50c3a447598c0ac3af17ec54afb79

runs/v5-final-acceptance-20260505T191500Z/v5_stage6_command_log_draft.jsonl
sha256: 9134a984c184962fba15b590687c9acadbfe5f5b13954995eca4e9d14faf5fd6

runs/v5-final-acceptance-20260505T191500Z/v5_pre_bundle_command_log.jsonl
sha256: a79ea87085d3e921addc9edbe6507b6094d79c8f3aca78430c20e76283e38a2f

runs/v5-final-acceptance-20260505T191500Z/build_v5_acceptance_bundle_command_log_entry.json
sha256: 7986c917da7cd91913f868781204679128d1bcb590a9b1d1debcace125c1bbcc

runs/v5-final-acceptance-20260505T191500Z/inspect_acceptance_bundle_command_log_entry.json
sha256: 39177d70a7a2850a2d6da8d00b0fe156ff5b5f1a9fe970832351612b1502b152

runs/v5-final-acceptance-20260505T191500Z/v5_final_acceptance_command_log.jsonl
sha256: f3fa4c190db753cb6f3f1252975b7699f95fd6c1f94f5249369981a4162ea4e6

runs/v5-final-acceptance-20260505T191500Z/v5_final_acceptance_pretest_report.json
sha256: 5b7d61260640ccbd7e881d4f20f0f19e5a8c2c4dee2eff3144f732b9cd106597
```

Post-acceptance 文档：

```text
docs/v5/final-acceptance.md
sha256: 8dd1b18a7722e337b46bd6f52dd43ddcd5c835acf193b8213df4cba188eb0bcb

docs/v5/walkthrough.md
sha256: c2ab4f484af7817f87f6658b629458a64bdfca85429bf4b5be8ad10511941fbe
```

## 验证命令和结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_acceptance.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py tests/unit/test_v5_provider_gate.py tests/unit/test_v5_run_matrix.py tests/unit/test_v5_export_pack.py tests/unit/test_v5_demo_artifacts.py tests/unit/test_v5_acceptance.py -q
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json --assert-core-complete --reference-integrity-output runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report_reference_integrity_report.json --command-log-entry-output runs/v5-final-acceptance-20260505T191500Z/inspect_v5_acceptance_core_command_log_entry.json
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-20260505T191500Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

测试结果：

```text
tests/unit/test_v5_acceptance.py: 1 passed in 0.24s
V5 focused tests: 54 passed in 1.87s
Full test suite: 766 passed in 622.16s
```

按预期失败并记录为降级证据：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json --assert-resume-ready --reference-integrity-input runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report_reference_integrity_report.json --command-log-entry-output runs/v5-final-acceptance-20260505T191500Z/inspect_v5_acceptance_resume_ready_command_log_entry.json
```

失败原因是 `resume_ready_acceptance.status` 仍为 `blocked`，这与 Stage 5 claim gate 一致。

## 正例证据

- `core_acceptance.status=passed`。
- `resume_ready_acceptance.status=blocked`，并记录阻断原因。
- `v5_acceptance_report_reference_integrity_report.json` 中 `unbound_critical_evidence_finding_count=0`。
- `v5_acceptance_bundle_manifest.json` immutable inspect 通过。
- Final command log 同时包含 `build-v5-acceptance-bundle` 和 `inspect-acceptance-bundle` entry。

## 负例证据

- `inspect-v5-acceptance --assert-resume-ready` 按预期失败，避免误用完整强简历表述。
- Acceptance report 如果引用 acceptance inputs 之外的关键证据，reference integrity report 会记录未绑定证据。
- Acceptance bundle 如果文档、report、post-report output、pre-bundle command log 或 final command log 漂移，immutable inspect 会失败。

## 允许降级项

- V5 可以以 `core_acceptance.status=passed` 收口。
- `resume_ready_acceptance.status=blocked` 是允许降级项，但最终文档和简历必须使用保守表述。

## 禁止降级项

- 不允许把 Stage 0 V4 baseline proof 变成 Stage 6 当前工作区旧 V4 bundle 复检要求。
- 不允许把 post-report inspect output 或 bundle final output 放入 acceptance inputs。
- 不允许把 resume-ready blocked 状态写成完整简历完成。
- 不允许把 `inspect-v5-acceptance --assert-complete` 解释成只检查 core acceptance；它仍等价于 resume-ready 检查。

## 已知限制

- 当前没有第二个真实 provider family 的实际运行证据。
- 当前没有真实可比较 preference pair。
- Scaffold comparison 和 budget comparison 仍是 blocked conclusion，不是胜负结论。
- Export stress test 未执行，不能声称完成 resumable export stress tests。

## 自审结论

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段执行等价独立只读自审，记录见：

```text
docs/v5/review/implementation/09-final-acceptance-and-bundle-review.md
```

当前没有剩余 P1 或 P2。V5 core acceptance 已通过；resume-ready acceptance 阻断原因清楚、已被 claim gate 和 acceptance report 绑定。
