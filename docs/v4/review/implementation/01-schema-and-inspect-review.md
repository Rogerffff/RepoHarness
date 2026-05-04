# V4 阶段 1 只读审查记录：Schema、inspect 命令和 acceptance skeleton

## 审查范围

本次审查覆盖 V4 阶段 1 的 schema version、inspect skeleton、acceptance skeleton、fixture、机器产物追踪表和 V3 acceptance bundle 兼容分派。审查对象包括：

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/v4_stage1.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v3_acceptance.py`
- `tests/unit/test_v4_stage1_skeleton.py`
- `tests/fixtures/v4/stage1/`
- `docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json`
- `docs/v4/implementation-log/01-schema-and-inspect.md`

## 初审结论

subagent 初审未发现 P1 问题，但发现 2 个 P2 和 1 个 P3，因此初审时不允许进入阶段 2。

### P2-1：追踪表声称覆盖的产物多于实际 inspect 契约

初审认为，`artifact_inspect_tracking_table.json` 中列出的 P0-2、P0-3、P1-2、P1-4、trajectory store 和全局污染扫描产物，多于 `V4_ARTIFACT_SET_SPECS` 实际检查的文件集合，容易形成“表格声称覆盖但代码没有检查”的假阳性。

修复结果：

- 目录类 skeleton inspect 已扩展为检查 tracking table 中列出的全部对应文件。
- `inspect-v4-cards` 现在检查 `dataset_card.md`、`dataset_card.json`、`run_card.json`、`export_card.json`、`provenance_summary.json`、`contamination_scan_summary.json` 和 `repro_command_index.json`。
- `inspect-v4-export-quality` 现在检查 Stage 6 追踪表列出的 export quality 产物。
- `inspect-v4-tool-contract`、`inspect-v4-tool-lifecycle`、`inspect-v4-agent-run-integration`、`inspect-v4-trajectory-store` 都扩展为检查追踪表列出的文件集合。
- 直接 manifest 类 skeleton 使用 `artifact_refs_by_name` 递归复核关联文件，例如 task freeze、task validity 和 contamination scan。

### P2-2：V4 acceptance inspect 没有按类别递归复核绑定产物契约

初审认为，`inspect_v4_acceptance` 只传递调用 `inspect_v4_inputs`，而 `inspect_v4_inputs` 只检查路径、sha256、必需类别和 tracking table，不会调用对应阶段 inspect，因此内部 schema 或必需文件缺失可能漏检。

修复结果：

- `inspect_v4_inputs(..., assert_complete=True)` 新增 `_inspect_bound_acceptance_categories`。
- 该逻辑会按 `input_refs_by_category` 调用对应 skeleton inspect，例如 rollout、task freeze、task validity、tool contract、tool lifecycle、agent run integration、trajectory store、export quality 和 cards。
- `inspect_v4_acceptance(..., assert_complete=True)` 会先复核 `acceptance_inputs_ref`，因此也会传递触发绑定产物递归复核。
- 新增负例：acceptance inputs 绑定的 cards 目录缺少 `run_card.json` 时，递归复核失败。

### P3-1：负例测试覆盖还有空洞

初审认为，测试缺少 schema version mismatch 和 RUN_SELECTION_MANIFEST 自身 `latest_run_auto_selection=true` 的负例。

修复结果：

- 新增 schema version mismatch 负例。
- 新增 RUN_SELECTION_MANIFEST `latest_run_auto_selection=true` 负例。

## 复审结论

subagent 复审结论如下：

- 未发现 P1 问题。
- 未发现 P2 问题。
- 可以进入阶段 2。
- 已确认 tracking table 不再只是列命令或检查少数锚点。
- 已确认 `inspect_v4_inputs(..., assert_complete=True)` 会按类别递归调用对应 skeleton inspect。
- 已确认 `inspect_v4_acceptance(..., assert_complete=True)` 会通过 `acceptance_inputs_ref` 间接触发绑定产物复核。
- 已确认测试补上 schema version mismatch、V4 acceptance inputs latest run 自动选择和 RUN_SELECTION_MANIFEST latest run 自动选择负例。
- 已确认 V3 acceptance bundle inspect 仍不受 V4 dispatch 影响。

复审指出一个 P3：全局污染扫描追踪表使用 `task_visibility_scan_report.json`，而 skeleton fixture 围绕 `contamination_scan_report.json`。该问题不阻塞阶段 2，但容易造成命名歧义。

修复结果：

- tracking table 的全局污染扫描行统一列出 `contamination_scan_report.json`、`task_visibility_scan_report.json` 和 `contamination_scan_summary.json`。
- `inspect-v4-contamination-scan` skeleton 要求 `contamination_scan_report.json` 通过 `artifact_refs_by_name` 绑定并复核 `task_visibility_scan_report.json` 和 `contamination_scan_summary.json`。
- Stage 1 fixture 同步补齐 `task_visibility_scan_report.json`。

## 验证记录

只读审查和本地验证覆盖以下命令：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_stage1_skeleton.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_stage1_skeleton.py tests/unit/test_v4_implementation_inputs.py tests/integration/test_v3_acceptance_stage12.py::test_v3_acceptance_allows_historical_repo_command_input_drift tests/integration/test_v3_acceptance_stage12.py::test_v3_acceptance_rejects_unmarked_repo_command_input_drift -q
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-implementation-inputs docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json --assert-complete
```

## 阶段准入结论

阶段 1 审查通过。没有 P1 / P2 阻塞问题，P3 已修复。完成提交前验证后，可以进入阶段 2。
