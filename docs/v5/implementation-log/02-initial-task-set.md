# V5 Stage 2A 初始任务集接入实现日志

日期：2026-05-05

## 阶段目标

Stage 2A 的目标是把当前已经完成 preflight 的 10 个稳定候选，转换为 V5 正式可审计 task definitions，并且明确记录这些任务只满足初始批次接入要求，还没有满足 V5 `core_acceptance` 的严格任务库存门。

本阶段不得把当前 10 个候选写成已经满足 `12 total / 8 PR-issue`，也不得把 preflight 产物直接计为最终真实 provider run、最终 accepted task 或训练样本。

## 实现内容

- 新增 `repo_harness.v5_task_set.build_task_set_manifest`，对应 CLI 为 `repo-harness build-v5-task-set`。
- `build-v5-task-set` 显式接收以下输入路径：
  - `v5_preflight_input_binding.json`
  - adapter-visible task draft JSONL
  - evaluator-only evidence manifest
  - run matrix preflight manifest
  - task selection preflight report
  - visibility scan report
  - flaky probe report
  - 一个或多个 source materialization report
- 生成 10 个 sanitized adapter-visible task input 文件。
- 生成 10 个正式 V5 task definition 文件。
- 生成 `v5_task_set_manifest.json`、`v5_task_inventory_report.json`、`v5_task_visibility_scan_report.json`、`v5_task_diversity_report.json`、`v5_task_stability_report.json` 和相关分组 manifest。
- 扩展 `inspect-v5-task-set --assert-complete`，使其能深度检查 task definition refs、adapter-visible refs、evaluator-only refs、source archive refs、verifier evidence refs 和 Stage 2A 的 partial inventory gate。
- 扩展 `inspect-v5-task-visibility --assert-clean`，确保 model-visible leak、share-safe violation 和 trainable payload contamination 均为 0。

## 主要修改文件

- `src/repo_harness/v5_task_set.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_task_set.py`

## 新增或更新的 schema

- `repo_harness_v5_task_definition_v0`
- `repo_harness_v5_task_construction_report_v0`
- `repo_harness_v5_pr_issue_task_manifest_v0`
- `repo_harness_v5_swebench_like_subset_manifest_v0`
- `repo_harness_v5_task_diversity_report_v0`
- `repo_harness_v5_task_stability_report_v0`
- `repo_harness_v5_adapter_visible_task_input_manifest_v0`
- `repo_harness_v5_evaluator_only_evidence_manifest_v0`

## 新增或更新的命令

新增 builder：

```bash
repo-harness build-v5-task-set
```

更新 inspect：

```bash
repo-harness inspect-v5-task-set V5_TASK_SET_MANIFEST --assert-complete
repo-harness inspect-v5-task-visibility V5_TASK_VISIBILITY_SCAN_REPORT --assert-clean
```

## 机器产物

产物目录：

```text
runs/v5-stage2a-initial-task-set-20260505T145206Z/
```

关键文件和 sha256：

| 文件 | sha256 |
| --- | --- |
| `v5_task_set_manifest.json` | `539d120203f2429fdfc2d3fbeec45cbb37dc49ca86cf60479a81727987cdf0c9` |
| `v5_task_inventory_report.json` | `e57708dda7fd4fdb154b8607a2ee4a3da2cee3b5a090f3ae262fcae19ad3a636` |
| `v5_task_visibility_scan_report.json` | `037359e1d5cf9464cdce9027569e79261118798847d5f75a8b8591022087da28` |
| `v5_task_diversity_report.json` | `7e24ac78204a889db48bcb1f093fbbd56491816e600e85555149a29c2c3096a1` |
| `v5_task_stability_report.json` | `fcbe0fd228a1ce2d7dba9d567100b16737efc5b145a0246af4f796970428699b` |
| `build_v5_task_set_command_log_entry.json` | `8b9d5000431742290851c6750c5a032cd19c0aeb2f836fe04d6ad978bca7c906` |
| `v5_stage2a_command_log.jsonl` | `0fe43c1145ba8975956476b7def8742fd8152d06061475745bd89c5181e83d69` |

## 任务库存结果

- accepted / auditable task definitions：10 个。
- PR / issue flow tasks：6 个。
- SWE-Bench-like anchor tasks：4 个。
- agent-run-ready：10 个。
- comparison-ready：9 个。
- 当前库存门状态：`blocked_pending_stage2b`。
- 是否宣称完整库存门通过：否。
- Stage 2B 是否仍然必需：是，默认需要补齐 2 个 PR / issue 候选。

## 多样性结果

- Go：3 个任务。
- JavaScript：1 个任务。
- Python：6 个任务。
- PR / issue flow：6 个任务。
- SWE-Bench-like anchor：4 个任务。
- demo-ready：2 个任务。

## 验证命令

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_task_set.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py src/repo_harness/schema_versions.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_task_set.py -q
PATH=.venv/bin:$PATH repo-harness build-v5-task-set --preflight-input-binding runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --adapter-visible-task-draft runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/adapter_visible/v5_adapter_visible_task_draft.jsonl --evaluator-only-evidence-manifest runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/visibility/v5_evaluator_only_evidence_manifest.json --run-matrix-preflight-manifest runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/run_matrix/v5_run_matrix_preflight_manifest.json --task-selection-preflight-report runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/run_matrix/v5_task_selection_preflight_report.json --visibility-scan-report runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/reports/v5_task_visibility_scan_report.json --flaky-probe-report runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/reports/v5_flaky_probe_report_amended.json --source-materialization-report runs/v5-source-materialization-preflight-20260505T082123Z/reports/v5_source_materialization_report.json --source-materialization-report runs/v5-swe-anchor-supplement-preflight-20260505T100000Z/reports/v5_swe_anchor_supplement_source_materialization_report.json --output-dir runs/v5-stage2a-initial-task-set-20260505T145206Z --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2a-initial-task-set-20260505T145206Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2a-initial-task-set-20260505T145206Z/v5_task_visibility_scan_report.json --assert-clean
```

验证结果：

- compileall 通过。
- `tests/unit/test_v5_task_set.py` 通过，结果为 `22 passed`。
- `build-v5-task-set` 通过。
- `inspect-v5-task-set --assert-complete` 通过。
- `inspect-v5-task-visibility --assert-clean` 通过。

## 正例证据

- `v5_task_set_manifest.json` 记录 `task_set_stage=stage2a_initial_10`。
- `accepted_auditable_task_count=10`，`pr_issue_task_count=6`，`swebench_like_anchor_count=4`。
- `strict_inventory_gate=blocked_pending_stage2b`。
- `supplemental_required=true`。
- `claims_full_inventory_gate=false`。
- `v5_task_visibility_scan_report.json` 中 `model_visible_leak_count=0`，`share_safe_violation_count=0`，`trainable_payload_contamination_count=0`。

## 负例证据

`tests/unit/test_v5_task_set.py` 覆盖以下负例：

- 当前 10 个初始候选被错误宣称为完整库存门已通过时，`inspect-v5-task-set --assert-complete` 失败。
- adapter-visible task input 出现 `raw_pr_diff`、`provider_raw_content`、`hidden_selector`、`reward_scalar` 等 forbidden marker 时，`inspect-v5-task-visibility --assert-clean` 失败。
- `inspect-v5-task-visibility` 会重新读取 `adapter_visible_input_refs` 指向的实际模型可见文件；如果报告计数未更新但文件内容发生污染，inspect 仍会失败。
- 输出目录存在时 builder 拒绝覆盖旧 evidence。

## 允许降级项

- Stage 2A 允许严格任务库存门暂时处于 `blocked_pending_stage2b`，因为 Stage 2B 的默认目标就是补齐 2 个 PR / issue 候选。
- Stage 2A 允许当前 10 个候选来自 preflight evidence，但不能把这些 preflight 产物直接计为最终真实 provider run 或训练样本。

## 禁止降级项

- 不能把当前 10 个候选描述为已经满足 `12 total / 8 PR-issue`。
- 不能把 evaluator-only evidence、gold patch、raw test patch、raw PR diff、provider raw content 或 reward scalar / label 放进 adapter-visible input。
- 不能在 Stage 2A 或后续阶段把旧 V4 doc-sync bundle immutable inspect 当作当前 V5 源码变更后的阶段门。

## 已知限制

- Stage 2A 只接入当前 10 个初始冻结候选。Stage 2B 仍然必须补齐 2 个 PR / issue 候选，或者正式修订 scope、preflight plan 和 review 记录。
- 本阶段没有执行真实 provider agent run，也没有调用 provider API。

## 是否偏离设计文档

没有偏离。实现保留了 Stage 2A 的 partial inventory gate，并明确阻止把当前 10 个候选写成完整任务库存门已经通过。

## 审查结论

初轮独立只读 subagent 复审发现 2 个 P2：adapter-visible forbidden marker 变体覆盖不足，以及 `inspect-v5-task-visibility` 过度依赖报告计数。两项均已修复并补充测试。主流程自审允许进入 Stage 2B，修复后仍需再次完成只读复审确认。

修复后独立只读 subagent 复审结论：P1 无，P2 无，允许进入 Stage 2B。复审提出 1 个 P3：单元测试没有穷举全部 forbidden marker 变体。该 P3 已通过参数化测试修复，覆盖 `raw pr diff`、`raw_pr_diff`、`raw pr body`、`raw_pr_body`、`hidden selector`、`hidden_selector`、`gold patch`、`gold_patch`、`raw test patch`、`raw_test_patch`、`provider raw content`、`provider_raw_content`、`reward scalar`、`reward_scalar`、`reward label` 和 `reward_label`。
