# V5 Stage 2B 补充 PR / issue 任务集复审记录

## 审查范围

本记录覆盖 V5 Stage 2B 的实现、测试和机器产物：

- `src/repo_harness/v5_task_set.py`
- `src/repo_harness/v5_evidence.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/schema_versions.py`
- `tests/unit/test_v5_task_set.py`
- `runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_candidate_report.json`
- `runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json`
- `runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json`

## 初轮只读复审发现

初轮只读 subagent 复审没有修改文件，结论是不建议以当时实现直接放行进入 Stage 3A 的真实 provider agent run matrix。发现如下：

### P1：`merge-v5-task-set` 对 supplemental report 过度信任

问题：`merge_task_set_manifests` 只检查 supplemental report 的 `status` 和 `accepted_task_definition_refs` 数量，未深度校验：

- `schema_version`
- `live_probes_executed=true`
- `required_supplemental_count=2`
- `selected_candidate_ids` 与 accepted refs 是否一致
- `candidate_records` 的 `freeze_ready`、`agent_run_ready` 和 visibility counters
- 失败候选的 `failure_owner`、`failure_category`、`stdout_sha256` 和 `stderr_sha256`
- candidate command log refs

风险：离线 fixture 或手工拼装的 supplemental report 可能关闭 `12 total / 8 PR-issue` 严格任务库存门。

处理：已修复。新增 `_validate_supplemental_report_for_merge`，合并前强制检查 live probe lineage、默认顺序中最早两个 ready candidates、selected records、accepted refs、失败候选字段和 command log refs。单元测试新增 offline report 被拒绝的负例。

### P2：supplemental report 没有独立 inspect 路径

问题：`v5_supplemental_pr_issue_candidate_report.json` 使用新 schema，但 `inspect-v5-task-set` 当时只接受 `V5TaskSetManifest` 和 `V5TaskInventoryReport`。

处理：已修复。新增 `V5SupplementalPRIssueCandidateReport` schema spec 和 `_inspect_v5_supplemental_pr_issue_report_deep`。正式产物已经通过：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_candidate_report.json --assert-complete
```

### P2：默认 supplemental registry 未覆盖实施计划完整默认顺序

问题：实施计划列出 7 个默认候选，但实现只覆盖前 4 个。

处理：已修复。`DEFAULT_SUPPLEMENTAL_CANDIDATES` 现在覆盖：

1. `pallets/click#3364`
2. `python-attrs/attrs#1428`
3. `pypa/packaging#1124`
4. `hynek/structlog#620`
5. `chalk/chalk#335`
6. `sindresorhus/execa#1176`
7. `clap-rs/clap#6340`

单元测试新增 registry 顺序覆盖检查。

### P3：Stage 2B negative coverage 较薄

问题：初版测试主要覆盖 happy path 和单个 supplemental merge rejection。

处理：已部分修复。新增 offline supplemental report rejection、single supplemental rejection、supplemental report inspect 和 default registry coverage。其余更细粒度的负例，例如 selected refs 被篡改、candidate command log 空文件、失败候选字段缺失，可以在后续 Stage 3 或 Stage 6 acceptance hardening 中继续扩展。

## 修复后验证

已通过：

```bash
PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v5_task_set.py src/repo_harness/v5_evidence.py src/repo_harness/cli/main.py src/repo_harness/schema_versions.py
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_v5_task_set.py tests/unit/test_v5_evidence_integrity.py -q
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_candidate_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-set runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-task-visibility runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json --assert-clean
```

修复后的完整测试通过：

```text
752 passed in 601.83s
```

提交前已重新运行阶段相关测试和必要回归。

## 当前机器产物核查

正式 supplemental report：

```text
runs/v5-stage2b-supplemental-pr-issue-20260505T151015Z/v5_supplemental_pr_issue_candidate_report.json
status=passed
accepted_supplemental_count=2
selected_candidate_ids=["pallets/click#3364", "python-attrs/attrs#1428"]
live_probes_executed=true
```

正式 merged task set：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_set_manifest.json
task_set_stage=stage2b_merged_12
accepted_auditable_task_count=12
pr_issue_task_count=8
swebench_like_anchor_count=4
strict_inventory_gate=passed
claims_full_inventory_gate=true
```

正式 merged visibility report：

```text
runs/v5-stage2b-merged-task-set-20260505T152756Z/v5_task_visibility_scan_report.json
model_visible_leak_count=0
share_safe_violation_count=0
trainable_payload_contamination_count=0
```

## 第二轮只读复审结论

第二轮只读 subagent 复审确认：

- P1 无剩余问题。
- P2 无剩余问题。
- 正式 supplemental report、merged task set、merged inventory report 和 merged visibility report 均可通过对应 inspect。
- 当前正式 merged artifact 可以作为 Stage 2B 通过产物。
- 允许进入 Stage 3A。

第二轮复审提出 1 个 P3：merge 校验“最早满足条件的 2 个候选”时仍使用 supplemental report 自带的 `candidate_order`。该 P3 已修复。当前实现改为使用代码中的 `V5_DEFAULT_SUPPLEMENTAL_CANDIDATE_ORDER` 独立重算默认候选顺序，单元测试新增“调换前两个默认候选顺序时 inspect 和 merge 都失败”的负例。

## 剩余风险和后续项

- P3 后续增强：继续增加 selected refs 篡改、失败候选字段缺失、candidate command log 空文件和 visibility leak 的专门负例。
- 当前正式 Stage 2B 只执行前 4 个默认候选。后 3 个默认候选作为 fallback registry entries 已覆盖，但没有执行正式 probe，因为前 2 个候选已经满足补位门。
- Stage 3 run matrix 必须绑定 merged task set，不能绑定 Stage 2A initial 10 task set。

## 复审结论

初轮 P1 和两个 P2 已完成代码修复、测试补充和正式 inspect 复核。第二轮只读 subagent 复审确认没有剩余 P1 / P2，并允许进入 V5 Stage 3A。第二轮提出的 P3 已在本阶段内修复。
