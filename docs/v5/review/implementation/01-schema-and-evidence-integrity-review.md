# V5 Stage 1 schema and evidence integrity review

日期：2026-05-05

## 审查方式

本轮先完成主流程自审，并安排只读 subagent 对 Stage 1 schema 和 evidence integrity evidence 进行独立复核。审查对象：

```text
runs/v5-stage1-schema-and-evidence-20260505T143520Z/
```

## 审查维度

- `build-v5-schema-fixtures` 是否显式输出，不扫描 latest run。
- `build-v5-evidence-integrity` 是否显式接收 critical evidence manifest、pre-acceptance command log 和输出路径。
- `inspect-v5-evidence-integrity --assert-complete` 是否通过。
- Pre-acceptance evidence integrity 是否只覆盖 acceptance report 生成之前的证据。
- 是否错误提前引用 acceptance report reference integrity、acceptance bundle command lineage 或 post-report inspect output。
- Schema tracking table 是否覆盖 V5 implementation plan 中的核心 schema。
- Negative tests 是否覆盖 sha256 drift、post-report reference、输出覆盖风险、inspect skeleton 可调用性和 schema tracking 精度。

## 发现

### P1

初轮只读审查发现 2 个 P2：

- V5 inspect skeleton 只在 tracking table 中声明，CLI 实际不可调用。
- `V5AcceptanceReport` 和 `V5ExportResultPackManifest` 的 schema tracking 没有完整表达 implementation plan 中的 nested required fields 和 preference pair 二选一约束。

处理：均已修复。CLI 已暴露 Stage 1 tracking table 声明的 V5 inspect skeleton；schema tracking 已记录 `core_acceptance.status`、`core_acceptance.required_checks`、`resume_ready_acceptance.status`、`resume_ready_acceptance.required_checks`、`acceptance_report_reference_integrity.expected_check`，并记录 `preference_pair_export_ref` 或 `preference_pair_blocked_report_ref` 的二选一 required fields。

### P2

无。

### P3：后续阶段需要把 skeleton inspect 扩展为业务字段深检

Stage 1 已经落地 schema tracking、fixture 和 pre-acceptance evidence integrity gate。后续 Stage 2 到 Stage 6 仍需要把 `inspect-v5-task-set`、`inspect-v5-run-matrix`、`inspect-v5-export-pack`、`inspect-v5-demo-artifacts`、`inspect-v5-inputs` 和 `inspect-v5-acceptance` 扩展为对应业务产物的完整字段级检查。

处理：这是 implementation plan 中后续阶段的正常工作，不阻止进入 Stage 2A。

## 已确认通过项

- `python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py -q` 通过，结果为 `13 passed`。
- `python -m compileall src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py src/repo_harness/schema_versions.py` 通过。
- `build-v5-schema-fixtures` 通过。
- `build-v5-evidence-integrity` 通过。
- `inspect-v5-evidence-integrity --assert-complete` 通过。
- `inspect-v5-task-set --assert-complete` 对 valid fixture 通过。
- `inspect-v5-task-set --assert-complete` 对库存不足 negative fixture 失败。
- `inspect-v5-export-pack --assert-clean` 对缺少 blocked partition 的 negative fixture 失败。
- `inspect-v5-acceptance --assert-core-complete` 对 valid fixture 通过，对 post-report output negative fixture 失败。
- `v5_pre_acceptance_evidence_integrity_report.json` 的 `status` 为 `passed`，findings 为空。
- `v5_schema_tracking_table.json` 已记录 nested required fields 和 one-of required fields。

## 修复记录

已修复初轮 subagent 审查提出的 2 个 P2。Stage 1 主流程没有修改无关既有改动。

## 时序边界复核

Stage 1 没有把 V5 acceptance report、post-report inspect output、pre-bundle command log、acceptance bundle manifest、final command log 或 doc-sync output 放入 pre-acceptance evidence integrity report。

## 是否允许进入下一阶段

主流程自审允许进入 V5 Stage 2A。修复后独立只读 subagent 复审也允许进入 V5 Stage 2A。

修复后 subagent 复审结论：

- P1：未发现阻止进入 Stage 2A 的问题。
- P2：未发现阻止进入 Stage 2A 的问题。
- P3：未发现需要在 Stage 2A 前修复的问题。

复审确认 `repo-harness --help` 已暴露 Stage 1 tracking table 中声明的 V5 inspect skeleton；`v5_schema_tracking_table.json` 已记录 `V5AcceptanceReport` 的 nested required fields，并已记录 `V5ExportResultPackManifest` 的 preference pair export 或 blocked report 二选一约束；`v5_pre_acceptance_evidence_integrity_report.json` 的 `status` 为 `passed`，`findings` 为空；valid fixture 可以通过对应 inspect，negative fixture 会被拒绝；`inspect-v5-evidence-integrity --assert-complete` 通过。
