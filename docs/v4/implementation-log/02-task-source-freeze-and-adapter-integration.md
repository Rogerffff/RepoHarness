# V4 Stage 2: Task Source Freeze And Adapter Integration

## 目标

阶段 2 的目标是把阶段 0 冻结的 V4 PR / issue feasibility 输入转换为 RepoHarness 自有的、可检查的 task freeze 与 task validity 机器产物。阶段 2 不把历史 feasibility `freeze_ready` 直接计为最终验收结果，而是通过显式 task adapter 边界、污染扫描、source / verifier / flaky / dependency / review evidence 引用和阶段检查命令建立 accepted / auditable task definition 的本阶段门槛。

## 实现内容

- 新增 `repo-harness build-v4-task-freeze`，显式读取 `v4_implementation_input_manifest.json`，生成阶段 2 机器产物。
- 新增阶段 2 专用 `inspect-v4-task-freeze` 和 `inspect-v4-task-validity` 强检查逻辑。
- 生成 8 个 V4 PR / issue accepted / auditable task definitions，并保留 5 个 public SWE-Bench-like 候选作为 diagnostic extension pool。
- 保留 Task Adapter 所有权边界：Task Adapter 只转换 frozen task input 和 evidence refs，不执行 dependency setup、source checkout、source materialization、baseline verifier、post-patch verifier 或 flaky probe。
- 使用统一 `V4ContaminationDenylist` 扫描 adapter-visible task input 与 generated task definition。
- 让 final acceptance inputs 递归复核 task freeze / task validity 时调用阶段 2 专用 inspect，而不是只走 Stage 1 skeleton。

## 主要修改文件

- `src/repo_harness/v4_task_freeze.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/v4_stage1.py`
- `tests/unit/test_v4_task_freeze.py`
- `tests/unit/test_v4_stage1_skeleton.py`
- `docs/v4/evidence/schema-and-inspect/artifact_inspect_tracking_table.json`

## 机器产物

目录：`docs/v4/evidence/task-source-freeze/`

- `task_freeze_manifest.json`
- `pr_task_construction_manifest.json`
- `source_archive_manifest.json`
- `source_materialization_report.json`
- `baseline_verifier_report.json`
- `post_patch_verifier_report.json`
- `flaky_detection_report.json`
- `environment_stability_report.json`
- `dependency_cache_report.json`
- `license_provenance_review_report.json`
- `use_boundary_review_report.json`
- `task_validity_report.json`
- `generated_task_definition.jsonl`
- `evaluator_only_evidence_manifest.json`
- `adapter_visible_task_input_manifest.json`
- `task_visibility_scan_report.json`

## 验证命令

- `PATH=.venv/bin:$PATH python -m compileall src`
- `PATH=.venv/bin:$PATH repo-harness build-v4-task-freeze --implementation-inputs docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json --output-dir docs/v4/evidence/task-source-freeze`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-task-freeze docs/v4/evidence/task-source-freeze/task_freeze_manifest.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v4-task-validity docs/v4/evidence/task-source-freeze/task_validity_report.json --assert-complete`
- `PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v4_stage1_skeleton.py tests/unit/test_v4_task_freeze.py tests/unit/test_v4_implementation_inputs.py -q`
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete`
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`

## 验证结果

- Compileall 通过。
- 阶段 2 build 通过。
- `inspect-v4-task-freeze --assert-complete` 通过。
- `inspect-v4-task-validity --assert-complete` 通过。
- 阶段 0 / 阶段 1 / 阶段 2 单元测试组合通过：46 passed。
- V2 acceptance inspect 通过。
- V3 acceptance inspect 通过。
- V3 acceptance bundle immutable inspect 通过。

## 正例证据

- `task_freeze_manifest.json` 记录 `accepted_auditable_task_definition_count=8`，`pr_issue_accepted_auditable_task_definition_count=8`，`diagnostic_public_swebench_like_pool_count=5`。
- `task_validity_report.json` 中每个 accepted task 均包含 fixed revision、source archive hash、source tree hash、adapter-visible input hash、evaluator-only evidence manifest hash、baseline verifier plan hash、baseline evidence ref、post-patch evidence ref、flaky evidence ref、environment stability score、dependency cache、license / provenance review status 和 use-boundary review status。
- `inspect_v4_task_validity` 会逐 task 交叉校验 accepted rows 与 source materialization、baseline verifier、post-patch verifier、flaky detection、environment stability、dependency cache、license / provenance review 和 use-boundary review 报告。

## 负例证据

测试覆盖以下失败场景：

- adapter-visible input 中出现 gold patch 或 pull request marker 时失败。
- source materialization 两次 source tree hash 不一致时失败。
- flaky probe 状态不稳定却标记 accepted 时失败。
- post-patch verifier 失败时 accepted validity inspect 失败。
- baseline verifier 失败或 raw output 被复制时失败。
- evaluator-only manifest 复制 provider raw response、raw patch、raw test patch 或 raw verifier output 时失败。
- `inspect-v4-task-freeze` 递归复核发现 invalid task validity 时失败。
- accepted count 被膨胀、evidence ref 与绑定报告不一致、绑定报告缺少 accepted task identity 时失败。
- environment stability 或 dependency cache 报告缺少门槛字段时失败。
- license / provenance review、manual review note 或 Task Adapter ownership boundary 缺失时失败。

## 允许降级项

- 5 个 public SWE-Bench-like 候选只作为 diagnostic extension pool，不计入本阶段 8 个 accepted / auditable task definitions。
- 阶段 2 使用 feasibility run 中已冻结的 Docker、flaky 和 source archive evidence ref 派生 sanitized Stage 2 报告；不在本阶段重新运行完整 Docker verifier。

## 禁止降级项

- 不允许把 feasibility `freeze_ready` 直接计入最终 V4 acceptance。
- 不允许将 PR body、PR diff、review comments、fix commit URL、merge commit URL、raw verifier output、provider raw response、reward、hidden selector 或 raw patch 放入 adapter-visible input 或 trainable payload。
- 不允许 Task Adapter 执行 dependency setup、source checkout、source materialization、baseline verifier、post-patch verifier 或 flaky probe。

## 已知限制

- 阶段 2 只完成 task source freeze 和 adapter integration 产物，不执行 rollout queue、agent run、export quality、cards 或 final acceptance。
- public SWE-Bench-like 扩展池仍需后续 RepoHarness 自有 source materialization、verifier probe、visibility scan 和 final acceptance 才能计入 accepted / auditable。

## 是否偏离设计文档

没有偏离。阶段 2 保持在 P0-2 范围内，没有扩张到完整 SWE-Bench leaderboard、provider matrix、context strategy 或分布式 rollout。

## Subagent 或等价自审结论

阶段 2 经过三轮只读 subagent 审查。前两轮发现 P1/P2 问题：accepted counting 门槛不够硬、final acceptance 递归复核绕过阶段 2 专用 inspect、evaluator-only 原始内容隔离不完整、accepted task 缺少 baseline evidence ref、绑定报告没有逐 task 强绑定、计数只检查下限。上述问题均已修复。最终复审结论：未发现 P1/P2/P3，允许进入阶段 3。

## 是否可以进入下一阶段

可以进入阶段 3。
