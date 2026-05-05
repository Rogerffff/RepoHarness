# V5 Stage 2B 补充 PR / issue 任务集实施日志

## 目标

Stage 2B 的目标是补齐 Stage 2A 之后仍然存在的严格任务库存缺口。Stage 2A 已经正式接入 10 个初始候选，其中 PR / issue flow 任务只有 6 个。按照 `docs/v5/implementation-plan.md`，Stage 2B 必须默认补齐 2 个 PR / issue accepted / auditable task definitions，使正式 V5 task set 达到：

- accepted / auditable task definitions 至少 12 个。
- PR / issue flow accepted / auditable task definitions 至少 8 个。
- SWE-Bench-like anchor accepted / auditable task definitions 至少 3 个。

本阶段没有启动 agent run，没有调用 provider API，也没有把补位 preflight 产物计为训练样本。新增补位任务默认只作为 accepted / auditable inventory 和 Stage 3 run matrix backup，不自动进入核心 comparison cells。

## 实现内容

本阶段新增两个 Stage 2B builder：

- `repo-harness build-v5-supplemental-pr-issue-candidates`
- `repo-harness merge-v5-task-set`

`build-v5-supplemental-pr-issue-candidates` 对显式传入的候选按照文档默认顺序执行补位 probe。正式运行使用了以下 4 个候选：

1. `pallets/click#3364`
2. `python-attrs/attrs#1428`
3. `pypa/packaging#1124`
4. `hynek/structlog#620`

前两个候选通过补位门并被选中。后两个候选没有被选中，但保留了失败归属、失败类别、失败命令名称、stdout sha256 和 stderr sha256，供审计替补原因。

每个候选生成的关键产物包括：

- source materialization report。
- source archive manifest。
- dependency probe report。
- baseline verifier probe report。
- post-patch verifier probe report。
- flaky probe report。
- adapter-visible denylist scan report。
- training export boundary probe report。
- provider raw content leak probe report。
- candidate command log。
- supplemental task definition。

`merge-v5-task-set` 将 Stage 2A initial 10 task set 与 Stage 2B accepted supplemental tasks 合并，并重新生成 merged task set manifest、inventory report、visibility scan report 和 merge command log。

## 主要修改文件

- `src/repo_harness/v5_task_set.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_task_set.py`

## 新增或更新的 schema

- `repo_harness_v5_supplemental_pr_issue_candidate_report_v0`
- `repo_harness_v5_supplemental_pr_issue_probe_report_v0`

`inspect-v5-task-set` 现在可以直接检查 `v5_supplemental_pr_issue_candidate_report.json`。该检查会验证：

- `live_probes_executed=true`。
- `required_supplemental_count=2`。
- `accepted_supplemental_count>=2`。
- `selected_candidate_ids` 是默认顺序中最早满足补位门的 2 个候选。
- 被选中候选满足 `freeze_ready=true`、`agent_run_ready=true`、visibility counters 全为 0、baseline verifier expected failure、post-patch verifier passed 和 flaky probe stable。
- 未通过候选记录 `failure_owner`、`failure_category`、`replacement_reason`、`failed_command_name`、`stdout_sha256` 和 `stderr_sha256`。
- candidate command log refs 可以解析，并且至少包含 1 条命令记录。

## 新增或更新的 inspect 命令

- `repo-harness inspect-v5-task-set V5_SUPPLEMENTAL_PR_ISSUE_CANDIDATE_REPORT --assert-complete`
- `repo-harness inspect-v5-task-set V5_MERGED_TASK_SET_MANIFEST --assert-complete`
- `repo-harness inspect-v5-task-visibility V5_MERGED_TASK_VISIBILITY_SCAN_REPORT --assert-clean`

## 新增或更新的测试

`tests/unit/test_v5_task_set.py` 新增 Stage 2B 覆盖：

- supplemental candidates 与 Stage 2A task set 合并后关闭 `12 total / 8 PR-issue` 严格库存门。
- offline supplemental report 不能关闭正式库存门。
- 少于 2 个 supplemental tasks 时合并失败。
- 默认 supplemental candidate registry 覆盖实施计划列出的 7 个候选。
- supplemental report 可以由 `inspect-v5-task-set --assert-complete` 独立检查。

## 机器产物

正式 supplemental candidate report：

```text
runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_candidate_report.json
sha256: 16f0b7e0f1e6afdec6bec97cfd57f47788d051b9b6676f170916add70843144c
```

正式 supplemental command log：

```text
runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_command_log.jsonl
sha256: 37efaca1a614307f4f3015d950380170c463a4edcbdb3081dba57764471b7771
```

正式 supplemental builder command entry：

```text
runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/build_v5_supplemental_pr_issue_candidates_command_log_entry.json
sha256: 1a848f025823bd44f66547095e0a2f1feae7ebe3f2644ac9940521c969eda306
```

正式 merged task set manifest：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json
sha256: e77e197cd5e277bb4a389d7ace0e8475e78b6a274f77efcfd0308231e336771b
```

正式 merged inventory report：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_inventory_report.json
sha256: 8c62cb43ca097cb13c32b7ac5e6d041045dce15be93a47d13e7da033b369b87b
```

正式 merged visibility report：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json
sha256: 12a7131b560626efbfbd0abc274f0126f2dd52383e7d2fa058f582820811a94d
```

正式 merge command entry：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/merge_v5_task_set_command_log_entry.json
sha256: d2111b88c2e6bea2402c80145f94aa64f86d5bcb211592ba99f0407a2aea6dcd
```

正式 merge command log：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_stage2b_merge_command_log.jsonl
sha256: 2d303ae18290fa36659ff1a74394d73e87ce1f59b2a8bdcbf91f42db93d9dccb
```

## 验证命令和结果

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_task_set.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py src/repo_harness/schema_versions.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_task_set.py tests/unit/test_v5_evidence_integrity.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_preimplementation.py tests/unit/test_v5_evidence_integrity.py tests/unit/test_v5_task_set.py -q
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation runs/v5-stage0-preimplementation-20260505T143530Z/v5_preflight_input_binding.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-evidence-integrity runs/v5-stage1-schema-and-evidence-20260505T143520Z/v5_pre_acceptance_evidence_integrity_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2a-initial-task-set-20260505T145206Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2a-initial-task-set-20260505T145206Z/v5_task_visibility_scan_report.json --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_candidate_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json --assert-clean
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

完整测试结果：

```text
752 passed in 601.83s
```

注意：修复 supplemental report inspect、merge 深度门和默认候选顺序独立重算后，已经重新运行 Stage 2B 相关单元测试、补充 report inspect、merged task set inspect、visibility inspect 和完整测试。

## 正例证据

- `pallets/click#3364`：baseline with tests expected failure，post-patch verifier 通过 3 次，visibility counters 全为 0。
- `python-attrs/attrs#1428`：baseline with tests expected failure，post-patch verifier 通过 3 次，visibility counters 全为 0。
- 合并后 task set 计数为 `12 accepted / auditable`、`8 PR / issue`、`4 SWE-Bench-like anchors`。
- merged visibility report 的 `model_visible_leak_count=0`、`share_safe_violation_count=0`、`trainable_payload_contamination_count=0`。

## 负例证据

- `pypa/packaging#1124` 未进入补位选择，记录 `failure_category=candidate_probe_failed` 和失败命令 `v5_pr_issue_packaging_1124_post_patch_verifier_probe_verifier_3`。
- `hynek/structlog#620` 未进入补位选择，记录 `failure_category=candidate_probe_failed` 和失败命令 `v5_pr_issue_structlog_620_post_patch_verifier_probe_verifier_3`。
- 单元测试证明 offline supplemental report 不能通过 `inspect-v5-task-set --assert-complete`，也不能通过 `merge-v5-task-set` 关闭库存门。
- 单元测试证明少于 2 个 supplemental tasks 时合并失败。

## 允许降级项

- Stage 2B 只补齐 accepted / auditable inventory 和 run matrix backup，不要求新增补位任务进入 provider、scaffold 或 budget comparison cells。
- `pypa/packaging#1124` 和 `hynek/structlog#620` 作为替补失败候选保留审计证据，不影响前两个默认候选成功补位。

## 禁止降级项

- 不允许用 offline fixture、手写 supplemental report 或少于 2 个 supplemental tasks 关闭严格任务库存门。
- 不允许让 adapter-visible input 包含 evaluator-only patch、raw diff、provider raw content、credential marker、reward scalar 或 reward label。
- 不允许把 Stage 2B supplemental probes 计为真实 provider run、agent run 或训练样本。
- 不允许绕过 `inspect-v5-task-set` 和 `inspect-v5-task-visibility` 直接进入 Stage 3 real provider run matrix。

## 已知限制

- 当前正式补位只运行到前 4 个默认候选；因为前 2 个已经满足补位门，没有触发后续 fallback 候选。代码注册表已经覆盖实施计划列出的 7 个默认候选。
- `chalk/chalk#335`、`sindresorhus/execa#1176` 和 `clap-rs/clap#6340` 是后续 fallback registry entries，本阶段未执行它们的正式 probe。

## 是否偏离设计文档

没有偏离 Stage 2B 默认目标。Stage 2B 没有降低任务库存门，也没有修改 scope、preflight plan 或 review 记录。正式 task set 已经通过 `12 total / 8 PR-issue / 3 SWE-Bench-like` 严格门。

## 审查结论

初轮只读 subagent 复审发现 1 个 P1、2 个 P2 和 1 个 P3：

- P1：`merge-v5-task-set` 对 supplemental report 过于信任。
- P2：`v5_supplemental_pr_issue_candidate_report.json` 没有可用 inspect 路径。
- P2：默认 supplemental registry 未覆盖实施计划列出的 7 个候选。
- P3：Stage 2B negative test 覆盖较薄。

上述 P1 和 P2 已修复，P3 中最关键的 offline report rejection、single supplemental rejection 和 registry coverage 已补测试。第二轮只读 subagent 复审确认没有剩余 P1 / P2，并允许进入 Stage 3A。第二轮复审提出 1 个 P3：merge 使用 supplemental report 自带 `candidate_order` 判断默认候选顺序。该 P3 已修复，当前 inspect 和 merge 都使用 `V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER` 独立重算默认候选顺序，并新增调换前两个默认候选顺序时失败的单元测试。

## 是否可以进入下一阶段

可以进入 Stage 3A。Stage 3A 仍然必须保护当前 merged task set，后续 acceptance inputs 必须绑定 `runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json`，不能回退到 Stage 2A initial 10 task set。
