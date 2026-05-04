# V4 阶段 1：Schema、inspect 命令和 acceptance skeleton

## 目标

本阶段先定义 V4 机器产物契约和 inspect 命令骨架，避免后续阶段先生成业务产物再补验收口径。阶段 1 不启动 rollout queue，不构造正式 V4 task definitions，不生成 export，不执行 final V4 acceptance。

## 实现内容

- 新增 V4 acceptance inputs、acceptance report、acceptance bundle、rollout、task freeze、task validity、tool lifecycle、agent run integration、trajectory store、export quality、cards 和 contamination scan 的 schema version 常量。
- 新增 `src/repo_harness/v4_stage1.py`，集中维护 V4 artifact set inspect skeleton、V4 acceptance inputs skeleton、V4 acceptance report skeleton 和 artifact-to-inspect tracking table。
- 新增必须覆盖的 V4 inspect 命令入口：
  - `inspect-v4-inputs`
  - `inspect-rollout-queue`
  - `inspect-rollout-leases`
  - `inspect-rollout-retry`
  - `inspect-rollout-budget`
  - `inspect-resource-locks`
  - `inspect-resource-usage`
  - `inspect-rollout-resume`
  - `inspect-run-selection-query`
  - `inspect-v4-task-freeze`
  - `inspect-v4-task-validity`
  - `inspect-v4-tool-contract`
  - `inspect-v4-tool-lifecycle`
  - `inspect-v4-agent-run-integration`
  - `inspect-v4-trajectory-store`
  - `inspect-v4-export-quality`
  - `inspect-v4-cards`
  - `inspect-v4-contamination-scan`
  - `inspect-v4-acceptance`
- 扩展现有 `inspect-acceptance-bundle`，使其能识别 V4 acceptance bundle schema，并传递复核 V4 acceptance report；V3 bundle 路径保持原逻辑。
- 新增机器产物到 inspect 命令追踪表，并用测试保证文档产物与代码契约保持一致。
- 新增 Stage 1 schema fixture 目录和 negative fixture 目录。

## 主要修改文件

- `src/repo_harness/schema_versions.py`
- `src/repo_harness/v4_stage1.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v3_acceptance.py`
- `tests/unit/test_v4_stage1_skeleton.py`
- `tests/fixtures/v4/stage1/valid/schema_fixtures.json`
- `tests/fixtures/v4/stage1/negative/missing_schema_version.json`
- `tests/fixtures/v4/stage1/negative/sha_mismatch_v4_inputs.json`
- `docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json`

## 机器产物

- `docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json`
  - sha256：`a32b91ef2da60d8ffaba415817fcd269447033ecfd21012125966e2cd115c5bc`
- `tests/fixtures/v4/stage1/valid/schema_fixtures.json`
  - sha256：`2f1c1c20c2c97743791b5a90509e4c38ac94170e3d05ea6b48e2f5a7e0f439e7`
- `tests/fixtures/v4/stage1/negative/missing_schema_version.json`
  - sha256：`c85737af1325177f1104da2c3ebc4b1ff28f42a8746d8c915f43a45347f3fcb3`
- `tests/fixtures/v4/stage1/negative/sha_mismatch_v4_inputs.json`
  - sha256：`083d204ce4969685b5df9d532a6762229918269f2083d71915362e8f996c86be`

## 验证命令

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_stage1_skeleton.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_implementation_inputs.py tests/integration/test_v3_acceptance_stage12.py::test_v3_acceptance_allows_historical_repo_command_input_drift tests/integration/test_v3_acceptance_stage12.py::test_v3_acceptance_rejects_unmarked_repo_command_input_drift -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-implementation-inputs docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness --help
```

## 验证结果

- `compileall src` 通过。
- 修复审查问题后，Stage 1 skeleton 单元测试通过：`13 passed`。
- Stage 0 implementation inputs、Stage 1 skeleton 和 V3 historical command log targeted regression 通过：`34 passed`。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。
- Stage 0 `inspect-v4-implementation-inputs --assert-complete` 通过。
- CLI help 输出包含 Stage 1 要求的 V4 inspect 命令。

## 正例证据

- 所有 V4 schema version 都在 `tests/fixtures/v4/stage1/valid/schema_fixtures.json` 中有最小 fixture 记录。
- 每个进入 V4 范围的 P0、P1-2、P1-4 和 final acceptance 机器产物都在 `artifact_inspect_tracking_table.json` 中映射到 inspect 命令。
- tracking table 中列出的目录类产物现在都由对应 skeleton inspect 检查存在性和最低 schema version。
- tracking table 中列出的直接 manifest 类关联产物通过 `artifact_refs_by_name` 被 skeleton inspect 递归复核。
- 全局污染扫描行统一为 `contamination_scan_report.json` 绑定 `task_visibility_scan_report.json` 和 `contamination_scan_summary.json`，避免追踪表与 skeleton fixture 命名漂移。
- `inspect-v4-inputs` 要求显式 `input_refs_by_category`，并要求 `selection_mode=explicit` 和 `latest_run_auto_selection=false`。
- `inspect-v4-inputs --assert-complete` 会按类别递归调用对应 skeleton inspect，避免只验证路径和 sha256 而漏掉内部 schema 失败。
- `inspect-v4-acceptance` 会传递复核 `acceptance_inputs_ref`，并间接复核绑定的阶段产物 skeleton 契约。
- V4 acceptance bundle skeleton 会通过现有 `inspect-acceptance-bundle` 入口被识别并传递复核 V4 acceptance report。

## 负例证据

单元测试覆盖以下失败路径：

- 缺少 `schema_version` 时 inspect 失败。
- V4 acceptance inputs 中 file ref 缺少 sha256 时失败。
- V4 acceptance inputs 中 file ref sha256 不匹配时失败。
- RUN_SELECTION_MANIFEST 中出现报告类产物路径时失败。
- ACCEPTANCE_INPUTS 缺少已纳入的 P1-2 `tool_contract` 类别和 P1-4 `cards` 类别时失败。
- ACCEPTANCE_INPUTS 试图启用 latest run 自动选择时失败。
- RUN_SELECTION_MANIFEST 自身试图启用 latest run 自动选择时失败。
- schema version 不匹配时失败。
- acceptance inputs 绑定的 cards 目录缺少 tracking table 中列出的 `run_card.json` 时，递归复核失败。

## 允许降级项

- 阶段 1 的 inspect 命令是 skeleton：只检查显式路径、schema version、最低必填字段和关键边界，不证明业务产物已经完整实现。
- V4 acceptance inputs / report / bundle skeleton 只定义验收契约，不代表 V4 final acceptance 已经执行。

## 禁止降级项

- inspect 命令不得读取 latest run、默认当前目录或未声明环境变量来猜输入。
- RUN_SELECTION_MANIFEST 不得绑定报告类产物路径。
- ACCEPTANCE_INPUTS 不得缺少本阶段已纳入的 P1-2 和 P1-4 产物类别。
- Stage 1 不得把 feasibility 候选计入 accepted / auditable task definitions。

## 已知限制

- Stage 1 没有实现 rollout queue、task source freeze、tool lifecycle audit、agent run integration、export quality 或 cards 的业务逻辑。
- 当前 schema fixture 是最小 fixture，用于锁定 schema version 和 inspect 入口；后续阶段必须扩展成真实机器产物 fixture 和更细字段级负例。
- `inspect-v4-cards` skeleton 当前使用 `cards_manifest.json` 来锚定 card 目录，后续 Stage 7 需要扩展为逐项检查 `dataset_card.md`、`dataset_card.json`、`run_card.json`、`export_card.json`、`provenance_summary.json`、`contamination_scan_summary.json` 和 `repro_command_index.json`。

## 是否偏离设计文档

没有偏离设计文档。阶段 1 只建立 schema、inspect skeleton、acceptance skeleton、fixture 和追踪表，没有提前进入阶段 2 或更后续范围。

## 审查结论

subagent 初审发现 2 个 P2 和 1 个 P3。已修复：tracking table 与 inspect 契约不一致、V4 acceptance skeleton 未递归复核绑定产物、schema mismatch 和 RUN_SELECTION_MANIFEST latest-run 负例缺口。复审未发现 P1 / P2，并指出一个 P3 命名漂移；该 P3 已通过统一全局污染扫描追踪表和 fixture 修复。完整审查记录保存在 `docs/v4/review/implementation/01-schema-and-inspect-review.md`。

## 是否可以进入下一阶段

在阶段 1 只读审查没有 P1 / P2 阻塞发现，且提交前 diff 检查和阶段验证继续通过后，可以进入阶段 2。
