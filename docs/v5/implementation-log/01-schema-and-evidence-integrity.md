# V5 Stage 1 schema and evidence integrity

日期：2026-05-05

## 目标

在 Stage 0 baseline proof 已经通过之后，先落地 V5 的机器产物契约和 pre-acceptance evidence integrity gate，再进入 Stage 2 的 task subset freeze。Stage 1 不执行真实 provider run，不冻结最终 task set，也不生成训练导出样本。

## 结论

V5 Stage 1 已通过。核心产物：

```text
runs/v5-stage1-schema-and-evidence-20260505T143520Z/
```

`inspect-v5-evidence-integrity --assert-complete` 对以下文件返回通过：

```text
runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json
```

## 实现内容

- 增加 V5 Stage 1 schema version 常量。
- 增加字段级 schema tracking table，覆盖 V5 implementation plan 中列出的核心 schema。
- 增加 `repo-harness build-v5-schema-fixtures`，生成 valid fixtures、negative fixtures、`v5_schema_tracking_table.json`、`v5_artifact_inspect_tracking_table.json` 和 `v5_acceptance_lineage_schema_report.json`。
- 增加 `repo-harness build-v5-evidence-integrity`，从显式传入的 critical evidence manifest 和 pre-acceptance command log 生成 `v5_pre_acceptance_evidence_integrity_report.json`。
- 增加 `repo-harness inspect-v5-evidence-integrity`，只读检查 pre-acceptance evidence integrity report。
- 增加 V5 后续阶段 inspect skeleton CLI：`inspect-v5-task-set`、`inspect-v5-task-visibility`、`inspect-v5-run-matrix`、`inspect-v5-provider-gate`、`inspect-v5-provider-cost-budget`、`inspect-v5-export-pack`、`inspect-v5-demo-artifacts`、`inspect-v5-inputs` 和 `inspect-v5-acceptance`。
- 修复审查发现的 schema tracking 精度问题：`V5AcceptanceReport` 现在记录嵌套 required fields，`V5ExportResultPackManifest` 现在记录 preference pair export 和 blocked report 的二选一约束。
- 明确 pre-acceptance evidence integrity 只检查 acceptance report 生成之前已经存在的 evidence，不提前引用 acceptance report、post-report inspect output 或 acceptance bundle command lineage。

## 主要修改文件

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v5_evidence.py`
- `tests/unit/test_v5_evidence_integrity.py`
- `docs/v5/implementation-log/01-schema-and-evidence-integrity.md`
- `docs/v5/review/implementation/01-schema-and-evidence-integrity-review.md`

## 新增或更新的 schema

- `repo_harness_v5_schema_tracking_table_v0`
- `repo_harness_v5_artifact_inspect_tracking_table_v0`
- `repo_harness_v5_critical_evidence_manifest_v0`
- `repo_harness_v5_pre_acceptance_evidence_integrity_report_v0`
- `repo_harness_v5_acceptance_lineage_schema_report_v0`

## 新增或更新的 CLI / inspect 命令

```bash
repo-harness build-v5-schema-fixtures --output-dir OUTPUT_DIR --fail-if-output-exists
repo-harness build-v5-evidence-integrity --critical-evidence-manifest MANIFEST --pre-acceptance-command-log COMMAND_LOG --output REPORT --fail-if-output-exists
repo-harness inspect-v5-evidence-integrity REPORT --assert-complete
repo-harness inspect-v5-task-set MANIFEST --assert-complete
repo-harness inspect-v5-task-visibility REPORT --assert-clean
repo-harness inspect-v5-run-matrix MANIFEST --assert-complete
repo-harness inspect-v5-provider-gate REPORT --assert-consistent
repo-harness inspect-v5-provider-cost-budget REPORT --assert-consistent
repo-harness inspect-v5-export-pack MANIFEST --assert-clean
repo-harness inspect-v5-demo-artifacts INDEX --assert-share-safe
repo-harness inspect-v5-inputs INPUTS --assert-complete
repo-harness inspect-v5-acceptance REPORT --assert-core-complete
repo-harness inspect-v5-acceptance REPORT --assert-resume-ready
```

所有命令都显式接收输入路径和输出路径，不扫描 latest run。输出存在时默认失败。

## 新增或更新的 tests

- `tests/unit/test_v5_evidence_integrity.py`

覆盖内容：

- schema fixtures 覆盖 implementation plan 中的核心 schema。
- CLI help 暴露 Stage 1 命令。
- CLI help 暴露所有 Stage 1 tracking table 声明的 V5 inspect skeleton。
- Schema tracking table 记录 nested required fields 和 one-of required fields。
- Inspect skeleton 能拒绝 task set、export pack 和 acceptance report 的 negative fixture。
- 正例 pre-acceptance evidence integrity report 通过。
- sha256 drift 负例被拒绝。
- post-report reference 负例被拒绝。
- builder 拒绝覆盖已有输出。

Stage 0 + Stage 1 相关单测结果：

```text
13 passed in 0.55s
```

## 机器产物

关键文件和 sha256：

| 文件 | sha256 |
| --- | --- |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_schema_tracking_table.json` | `d61672c8decda21dc71d7a144d50b7c55c04a176eda039c8baf5779330024abf` |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_artifact_inspect_tracking_table.json` | `7a295497a0f6910399203d3c627303da3dc82d43d0e35b0af062a09f607d8f77` |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_acceptance_lineage_schema_report.json` | `ce4e95a93c6bf5ec4235185e04fd9b80d99d496974e1ff48b122e1f0e98081d6` |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_critical_evidence_manifest.json` | `eece94707eb48bfc66d44c814b980bb68f240fdcae397a4520606775887b507f` |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json` | `89fd2211a74b3791b33faaefa80c90bdf6f2df3b30e7182cb30da7051e53d28c` |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/build_v5_schema_fixtures_command_log_entry.json` | `21701a891c5300d67bb4879b661a80663461366017e274ab0ab288c06350bef4` |
| `runs/v5-stage1-schema-and-evidence-20260505T143520Z/build_v5_evidence_integrity_command_log_entry.json` | `6bdc5b038b6ec5a025c6e0994ea5bdf570389fd110dc22fad4610d8ebe0b7632` |

Schema fixture 目录：

```text
runs/v5-stage1-schema-and-evidence-20260505T143520Z/tests/fixtures/v5/
```

## 验证命令和结果

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py -q
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py src/repo_harness/schema_versions.py
PATH=.venv/bin:$PATH repo-harness build-v5-schema-fixtures --output-dir runs/v5-stage1-schema-and-evidence-20260505T143520Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness build-v5-evidence-integrity --critical-evidence-manifest runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_critical_evidence_manifest.json --pre-acceptance-command-log runs/v5-stage0-preimplementation-20260505T143530Z/v5_preimplementation_command_log.jsonl --output runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v5-evidence-integrity runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage1-schema-and-evidence-20260505T143520Z/tests/fixtures/v5/task_set_valid.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance runs/v5-stage1-schema-and-evidence-20260505T143520Z/tests/fixtures/v5/acceptance_report_valid_core.json --assert-core-complete
```

结果：

- 单元测试通过，`13 passed`。
- 编译通过。
- Schema fixture builder 通过。
- Evidence integrity builder 通过。
- Evidence integrity inspect 通过。
- Task set inspect skeleton 正例通过，库存不足负例被拒绝。
- Export pack inspect skeleton 缺少 blocked partition 负例被拒绝。
- Acceptance inspect skeleton 正例通过，post-report output 负例被拒绝。

## 正例证据

- `v5_schema_tracking_table.json` 覆盖 `V5EvidenceRef`、task set、task inventory、task visibility、`V5AcceptanceInputs`、`V5AcceptanceReport`、provider gate、cost budget、run matrix、matrix cell、matrix compare scope、export pack、reward taxonomy、failure taxonomy、preference blocked report、resume artifact index、result summary、public demo bundle、demo transcript index、claim gate 和 interview result pack。
- `v5_artifact_inspect_tracking_table.json` 记录 Stage 0 到 Stage 6 的主要 artifact 和对应 inspect 命令。
- `v5_acceptance_lineage_schema_report.json` 明确把 pre-acceptance evidence integrity、acceptance report reference integrity 和 acceptance bundle command lineage integrity 分开。
- `v5_pre_acceptance_evidence_integrity_report.json` 中 `status=passed`，findings 为空。

## 负例证据

- sha256 drift fixture 会被 `inspect-v5-evidence-integrity --assert-complete` 拒绝。
- post-report reference fixture 会被 `inspect-v5-evidence-integrity --assert-complete` 和 `inspect-v5-acceptance --assert-core-complete` 拒绝。
- task set 库存不足 fixture 会被 `inspect-v5-task-set --assert-complete` 拒绝。
- export pack 缺少 blocked partition fixture 会被 `inspect-v5-export-pack --assert-clean` 拒绝。
- builder 对已存在输出会失败，避免覆盖旧 evidence。

## 允许降级项

无。Stage 1 的 evidence integrity gate 是后续 acceptance inputs 和 acceptance report 的前置契约，不允许降级为 warning。

## 禁止降级项

- 不得让 pre-acceptance evidence integrity report 引用尚未生成的 V5 acceptance report。
- 不得把 acceptance report reference integrity 或 acceptance bundle command lineage integrity 放入 pre-acceptance evidence integrity 的输入集合。
- 不得把 provider raw request / response、credential marker、evaluator-only evidence 或 reward scalar 放入 model-visible、trainable 或 public-safe 内容。

## 已知限制

- Stage 1 只定义 schema 和 evidence integrity gate，不实现 V5 task set、provider gate、run matrix、export pack、demo artifacts 或 acceptance report。
- Stage 2B 的任务库存缺口仍未解决，后续必须补齐 2 个 PR / issue candidates，或者走正式范围变更。

## 是否偏离设计文档

没有偏离。Stage 1 按 implementation plan 先定义机器产物契约、schema fixture、inspect skeleton 和 pre-acceptance evidence integrity gate，没有提前执行 provider run matrix 或训练导出。

## Subagent 或等价自审结论

已安排只读 subagent 审查 Stage 1 evidence。审查记录保存到：

```text
docs/v5/review/implementation/01-schema-and-evidence-integrity-review.md
```

## 是否可以进入下一阶段

初轮只读审查发现 2 个 P2，均已修复并重新生成 Stage 1 机器产物。等待复审完成后确认；若无新的 P1 / P2 finding，则可以进入 V5 Stage 2A。
