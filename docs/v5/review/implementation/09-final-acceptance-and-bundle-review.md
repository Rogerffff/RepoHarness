# V5 Stage 6 Final Acceptance 和 Acceptance Bundle 自审记录

## 审查范围

本记录覆盖 V5 Stage 6 acceptance inputs、acceptance report、reference integrity report、acceptance bundle、final command log、final acceptance 文档和 walkthrough：

- `src/repo_harness/v5_acceptance.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/v3_acceptance.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_acceptance.py`
- `docs/v5/final-acceptance.md`
- `docs/v5/walkthrough.md`
- `runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_inputs.json`
- `runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json`
- `runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_manifest.json`

## 审查方式

原计划使用只读 subagent 做阶段复审，但当前会话启动新 subagent 时返回 agent 线程数量已达到上限。因此本阶段按实施规则执行等价独立只读自审。自审只读取代码、测试和机器产物；发现需要修复的问题后，再单独进入修复步骤。

审查重点如下：

- Acceptance inputs 是否只绑定 pre-report evidence。
- Acceptance report 是否引用了 acceptance inputs 之外的关键证据。
- Bundle builder 是否读取随后才生成的 final command log。
- Final command log 是否同时绑定 bundle build entry 和 planned inspect entry。
- Final acceptance docs 是否误用 resume-ready 强表述。
- 旧 V4 doc-sync bundle 是否被错误当成 Stage 6 当前工作区阶段门。

## 审查发现

### P2：comparison proof task 计数最初没有识别 Stage 3C 的 `compared_task_ids`

问题：首次生成 `runs/v5-final-acceptance-20260505T190500Z/v5_acceptance_report.json` 时，Stage 6 report builder 只读取 `comparison_task_count` 或 `task_count`，没有读取 Stage 3C compare scope 的真实字段 `compared_task_ids`，导致 core acceptance 被错误判定为 failed。

修复：`src/repo_harness/v5_acceptance.py` 的 `_core_failures` 已更新为按顺序读取 `comparison_task_count`、`task_count` 和 `len(compared_task_ids)`。修复后重新运行 Stage 6 单元测试、全量测试，并重建正式目录 `runs/v5-final-acceptance-20260505T191500Z/`。

状态：已修复。早期失败目录 `runs/v5-final-acceptance-20260505T190500Z/` 只作为失败尝试，不作为通过证据。

## 已核查的不变量

### Evidence 时序无循环

已核查：

- `v5_acceptance_inputs.json` 中 `post_report_outputs_included=false`。
- `v5_acceptance_inputs.json` 中 `bundle_final_outputs_included=false`。
- `v5_acceptance_report.json` 没有引用 reference integrity output 或 bundle output。
- `v5_pre_bundle_command_log.jsonl` 在 bundle 构建前生成。
- `v5_final_acceptance_command_log.jsonl` 在 bundle 构建和 planned inspect entry 之后生成。

结论：Stage 6 没有把后生成证据放回 acceptance report 输入。

### Reference integrity 通过

已核查：

- `v5_acceptance_report_reference_integrity_report.json` 中 `unbound_critical_evidence_finding_count=0`。
- `post_report_output_used_as_report_input_count=0`。
- `bundle_output_used_as_report_input_count=0`。

结论：Acceptance report 的关键证据都来自 acceptance inputs。

### Bundle command lineage 通过

已核查：

- `v5_acceptance_bundle_manifest.json` 绑定 acceptance report、post-report inspect output、pre-bundle command log 和 post-acceptance docs。
- `v5_final_acceptance_command_log.jsonl` 包含 `build-v5-acceptance-bundle` entry。
- `v5_final_acceptance_command_log.jsonl` 包含 `inspect-acceptance-bundle` planned entry。
- `inspect-acceptance-bundle --final-command-log ... --assert-immutable` 通过。

结论：V5 bundle command lineage 可复核。

### Claim gate 降级生效

已核查：

- `core_acceptance.status=passed`。
- `resume_ready_acceptance.status=blocked`。
- `inspect-v5-acceptance --assert-resume-ready` 按预期失败。
- `docs/v5/final-acceptance.md` 和 `docs/v5/walkthrough.md` 说明 resume-ready 阻断原因，并使用保守表述。

结论：Stage 6 没有把 core acceptance 误写成 resume-ready acceptance。

### V4 baseline 没有被误用

已核查：

- Stage 6 没有在当前 V5-mutated 工作区重新运行旧 V4 doc-sync bundle immutable inspect。
- V4 baseline proof 只通过 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和 command log 进入 acceptance inputs。

结论：Stage 6 遵守 V4 immutable baseline gate 时序修订。

## 验证结果

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
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_bundle_manifest.json --final-command-log runs/v5-final-acceptance-20260505T191500Z/v5_final_acceptance_command_log.jsonl --assert-immutable
```

测试结果：

```text
tests/unit/test_v5_acceptance.py: 1 passed in 0.24s
V5 focused tests: 54 passed in 1.87s
Full test suite: 766 passed in 622.16s
```

按预期失败：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-final-acceptance-20260505T191500Z/v5_acceptance_report.json --assert-resume-ready
```

## 剩余风险和后续项

- Resume-ready 仍需要第二个真实 provider family、真实可比较 preference pair、scaffold 对比和 budget 对比。
- 旧失败目录 `runs/v5-final-acceptance-20260505T190500Z/` 不得被引用为通过证据。
- 如果后续更新 `docs/v5/final-acceptance.md` 或 `docs/v5/walkthrough.md`，必须生成 V5 doc-sync acceptance bundle。

## 复审结论

当前没有剩余 P1 或 P2。V5 core acceptance 已通过，resume-ready blocked 是明确且被证据绑定的允许降级项。
