# Stage 16F.0 执行计划：跨工作树同步前冻结和差异盘点

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.0 是 Stage 16F 的强制前置阶段，目标是在任何 cherry-pick、手工移植、`EpisodeExecutionSpecBuilder` 实现、`run-episode-task` 命令实现之前，先冻结训练工作树和测评工作树的状态，并生成可以审计的同步 inventory。

这一阶段回答的问题是：

```text
两个工作树当前分别在哪个 commit？
哪些 dirty 文件参与同步，哪些不参与同步？
共同 canonical baseline 应该是什么？
哪些模块存在差异？
哪些差异必须同步，哪些可以延后？
当前 run_episode(real_episode) 和 run_task(...) 的入口差异有哪些已经被确认？
diagnostic_shell 的 bash / sh / shell=True 语义差异是否存在，应该如何进入 Stage 16F.1？
```

这一阶段不尝试解决这些差异。它只生成可靠、公开安全、可机器检查的差异盘点和同步决策输入。

## 2. 前置条件

执行 Stage 16F.0 前必须满足：

1. Stage 16E 相关实现已经单独提交，或者明确暂停执行 Stage 16F.0。
2. 本训练工作树中未提交文件已经分类，不能把 Stage 16E 或其他阶段的未提交修改混进 Stage 16F.0 baseline。
3. 测评工作树中的当前进度文档、待同步提交、dirty 文件和运行产物已经可读。
4. 不在公开文档或公开 evidence 中记录本机绝对路径。真实路径只能出现在私有运行证据目录中，或者完全不写入本仓库。
5. Stage 16F.0 执行者必须只做 inventory 和报告生成，不做代码同步，不做行为修改。

如果任一条件不满足，Stage 16F.0 必须输出结构化 `blocked` summary，而不是继续生成不可靠 inventory。

当前已知执行监督 gate：

```text
如果训练工作树中仍存在 Stage 16E / patch hygiene / official prediction hygiene 相关未提交改动，
Stage 16F.0 不能输出 status=passed。

允许输出：
  status=blocked
  stage16f0_complete=false
  ready_for_stage16f1=false
  blocking_reasons 包含 stage16e_not_committed_or_target_worktree_dirty

不允许输出：
  status=passed
  ready_for_stage16f1=true
```

执行 agent 可以在 blocked summary 中记录当前 dirty 文件摘要，但不能把这些 dirty 文件当成已经冻结的 canonical baseline，也不能继续生成宣称可进入 Stage 16F.1 的完整 inventory。

## 3. 非目标

本阶段不做以下事情：

1. 不 cherry-pick 测评工作树提交。
2. 不手工移植代码。
3. 不修改 `run_task(...)`、`run_episode(real_episode)`、`AgentLoop` 或 workspace adapter 行为。
4. 不实现 `EpisodeExecutionSpec` 或 `EpisodeExecutionSpecBuilder`。
5. 不新增 `run-episode-task` 命令。
6. 不运行大规模 SWE-Bench 评测。
7. 不把测评工作树的历史运行目录、HTML 报告、云服务配置、本机路径或临时调试文件提交进训练工作树。

## 4. 产物目录

建议新增公开安全目录：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/
```

公开产物建议包括：

```text
stage16f0_git_baseline_report.json
stage16f0_source_worktree_inventory.json
stage16f0_target_worktree_inventory.json
stage16f0_dirty_file_report.json
stage16f0_module_diff_matrix.json
stage16f0_required_sync_items.json
stage16f0_diagnostic_shell_semantics_report.json
stage16f0_run_task_run_episode_gap_report.json
stage16f0_public_evidence_policy.json
stage16f0_path_leak_scan_report.json
stage16f0_acceptance_summary.json
```

如果需要记录真实本机路径、原始 `git diff`、完整 dirty 文件内容或私有运行产物位置，只能写入不提交的私有目录，并在公开报告中使用下面这种不透明引用：

```text
runtime-private:<artifact-kind>:<sha256>
```

公开报告不能出现：

```text
本机绝对路径
真实 workspace 路径
真实 run directory 路径
真实私有运行证据目录路径
云服务密钥路径
隐藏 verifier 路径
gold patch 原文
test patch 原文
官方失败到通过测试集合标记和官方通过到通过测试集合标记的原始内容
```

## 5. Git baseline 语义

`stage16f0_git_baseline_report.json` 必须定义 canonical baseline 的 Git 语义。至少包含：

```json
{
  "schema_version": 1,
  "stage": "16F.0",
  "canonical_branch_or_commit": "...",
  "sync_base_commit": "...",
  "training_worktree_head_before_sync": "...",
  "evaluation_worktree_head_before_sync": "...",
  "integration_commit_after_sync": null,
  "training_worktree_head_after_sync": null,
  "evaluation_worktree_head_after_sync": null,
  "training_worktree_matches_canonical_after_sync": false,
  "evaluation_worktree_matches_canonical_after_sync": false,
  "stage16f0_only_inventory_no_sync_performed": true
}
```

说明：

1. Stage 16F.0 可以只指定即将使用的 canonical branch 或 base commit，不要求完成同步后的 integration commit。
2. 如果本阶段尚未创建 integration commit，`integration_commit_after_sync` 必须为 `null`，不能伪造。
3. 如果两个工作树没有指向同一个 canonical commit，必须记录原因和下一阶段 gate。

## 6. 工作树 inventory

### 6.1 训练工作树 inventory

`stage16f0_target_worktree_inventory.json` 至少包含：

```json
{
  "worktree_label": "training-worktree",
  "head_commit": "...",
  "branch": "...",
  "dirty_status": "clean|dirty",
  "dirty_files": [],
  "stage16e_committed": true,
  "untracked_file_policy": "excluded_from_stage16f0_public_evidence",
  "repo_harness_version_facts": {},
  "known_stage_boundaries": [
    "Stage 16A",
    "Stage 16B",
    "Stage 16C",
    "Stage 16D",
    "Stage 16E"
  ]
}
```

### 6.2 测评工作树 inventory

`stage16f0_source_worktree_inventory.json` 至少包含：

```json
{
  "worktree_label": "evaluation-worktree",
  "head_commit": "...",
  "branch": "...",
  "dirty_status": "clean|dirty",
  "dirty_files": [],
  "source_progress_doc_ref": "runtime-private:source-doc:<sha256>",
  "source_progress_doc_sha256": "...",
  "required_candidate_commits": [],
  "candidate_dirty_files": [],
  "candidate_runtime_artifacts": []
}
```

公开报告只能写 `worktree_label`、commit、sha256、相对路径和不透明引用。不能写本机绝对路径。

## 7. Dirty 文件处理

如果任一工作树存在 dirty 文件，必须生成 `stage16f0_dirty_file_report.json`。每条 dirty 文件至少包含：

```json
{
  "worktree_label": "evaluation-worktree|training-worktree",
  "relative_path": "...",
  "status": "modified|added|deleted|untracked|renamed|copied|typechanged|unmerged",
  "old_relative_path": "...|null",
  "new_relative_path": "...|null",
  "current_sha256": "...|null",
  "base_blob_sha256": "...|null",
  "old_blob_sha256": "...|null",
  "new_blob_sha256": "...|null",
  "diff_sha256": "...",
  "diff_summary": "...",
  "participates_in_sync": true,
  "reason_if_not_synced": null,
  "public_safe": true
}
```

规则：

1. 没有进入 dirty report 的 dirty 文件，不能作为 Stage 16F.1 同步来源。
2. `participates_in_sync=true` 的 dirty 文件必须有 `diff_sha256` 和 diff 摘要。
3. `modified` 文件应同时记录 `current_sha256` 和 `base_blob_sha256`。如果 base blob 无法获取，必须写明原因。
4. `added` 或 `untracked` 文件应记录 `current_sha256`，`base_blob_sha256` 可以为 `null`。
5. `deleted` 文件没有当前文件内容，因此 `current_sha256` 必须为 `null`，并尽量记录 `base_blob_sha256` 和 `diff_sha256`。
6. `renamed` 和 `copied` 文件必须记录 `old_relative_path`、`new_relative_path`、`old_blob_sha256`、`new_blob_sha256` 和 `diff_sha256`。
7. `typechanged` 文件必须记录类型变化摘要，并记录变化前后的 blob hash；如果无法获取，必须写明原因。
8. `unmerged` 文件不能作为 Stage 16F.1 同步来源，必须先人工解决或标记 `participates_in_sync=false`。
9. 如果 dirty 文件包含密钥、本机路径、运行日志、HTML 报告、云服务配置或私有 evidence，只能标记为 `participates_in_sync=false`。
10. `participates_in_sync=true` 不代表马上同步，只代表 Stage 16F.1 可以把它作为候选来源。

## 8. 模块级差异矩阵

必须生成 `stage16f0_module_diff_matrix.json`。它是 Stage 16F.1 的主要输入，不能只写主题级结论。

建议覆盖模块：

```text
command_policy
diagnostic_session
workspace_adapter
docker_adapter
public_environment
patch_hygiene
official_input_builder
healthcheck_builder
healthcheck_inspector
provider_failure_accounting
evaluation_runner
rl_runtime
tool_registry
context_builder
run_task_entrypoint
run_episode_entrypoint
training_view_projection
official_prediction_hygiene
```

最低文件映射要求：

```text
command_policy:
  src/repo_harness/tasks/command_policy.py

diagnostic_session:
  src/repo_harness/workspace/diagnostic_session.py
  src/repo_harness/tools/minimal.py
  src/repo_harness/permissions/system.py

workspace_adapter:
  src/repo_harness/workspace/adapter.py

docker_adapter:
  src/repo_harness/workspace/docker_adapter.py

public_environment:
  src/repo_harness/tasks/public_environment.py
  src/repo_harness/context/builder.py

patch_hygiene:
  src/repo_harness/workspace/patch_hygiene.py

official_input_builder:
  scripts/pre_verl/build_swebench_official_inputs.py

model_client:
  src/repo_harness/model_client/**/*.py

scaffold:
  src/repo_harness/scaffolds/**/*.py

evaluation_runner:
  src/repo_harness/evaluation/runner.py

rl_runtime:
  src/repo_harness/rl/runtime.py
```

如果某个路径在其中一个工作树不存在，不能简单忽略，必须在 `source_file_sha256s` 或 `target_file_sha256s` 中记录 `status=missing`。执行者可以根据实际代码再补充更多文件，但不能少于上述最低映射。

每项至少包含：

```json
{
  "module_name": "diagnostic_session",
  "source_files": [],
  "target_files": [],
  "source_file_sha256s": [
    {"relative_path": "...", "sha256": "...", "status": "present|missing"}
  ],
  "target_file_sha256s": [
    {"relative_path": "...", "sha256": "...", "status": "present|missing"}
  ],
  "source_module_digest": "...",
  "target_module_digest": "...",
  "module_digest_algorithm": "stable_json_sha256(sorted file records)",
  "source_commit": "...",
  "target_commit": "...",
  "decision": "sync|defer|ignore|manual-port",
  "reason": "...",
  "required_tests": [],
  "risk_if_deferred": "...",
  "public_evidence_ref": "runtime-private:module-diff:<sha256>"
}
```

聚合 digest 口径：

```text
source_module_digest 和 target_module_digest 必须由文件记录稳定排序后计算。
每条文件记录至少包含 relative_path、sha256 和 status。
status=missing 的文件 sha256 必须为 null。
如果一个模块包含多个文件，不能只给单个不可解释的 source_sha256 / target_sha256。
```

决策语义：

```text
sync：Stage 16F.1 应优先同步。
manual-port：逻辑必须同步，但不能直接 cherry-pick，需要手工移植。
defer：确认有差异，但可以延后到 Stage 16F.2 或更晚。
ignore：确认不需要同步，必须写明原因。
```

没有出现在 `module_diff_matrix` 中的模块，不允许在 Stage 16F.1 被静默同步。

## 9. P1 同步项：diagnostic_shell 执行 shell 语义

必须生成 `stage16f0_diagnostic_shell_semantics_report.json`，并把它作为 P1 同步项。

报告至少包含：

```json
{
  "source_diagnostic_shell_exec_semantics": {},
  "target_diagnostic_shell_exec_semantics": {},
  "docker_backend_shell": "bash -lc|sh -lc|other|unknown",
  "local_backend_shell": "bash -lc|shell_true|other|unknown",
  "uses_bash_lc": true,
  "uses_sh_lc": false,
  "uses_shell_true": false,
  "conda_activate_supported": "supported|unsupported|unknown",
  "pipefail_supported": "supported|unsupported|unknown",
  "source_command_policy_sha256": "...",
  "target_command_policy_sha256": "...",
  "p1_sync_required": true,
  "reason": "..."
}
```

必须检查的代码和行为线索包括：

```text
Docker diagnostic shell 是否显式使用 bash -lc。
Docker diagnostic shell 是否仍使用 sh -lc。
Local diagnostic shell 是否仍使用 shell=True。
命令事实中是否记录 execution_shell、execution_argv_digest、shell_semantics_version。
是否有测试覆盖 source、conda activate、set -o pipefail、管道失败传播和 bash-only 语法。
```

如果训练工作树仍使用 `sh -lc` 或 `shell=True`，Stage 16F.1 必须先同步或修复该项。不能等到 parity audit 后再处理。

## 10. run_task 与 run_episode 入口差异报告

必须生成 `stage16f0_run_task_run_episode_gap_report.json`。该报告只盘点差异，不实现修复。

至少覆盖：

```text
raw_prompt 来源
ContextBuilder 是否参与 run_episode
scaffold_id 来源
allowed_tool_registry 来源
ToolExecutor 是否默认构造
public_environment_context 是否注入
test_feedback_policy 是否一致
resolved_verifier_plan 是否一致
patch_hygiene facts 是否一致
TrainingView 是否可用
GenerationRecord 是否可用
provider route 是否被标记 invalid_for_online_rl
route=verl 是否仍通过 formal gate
```

每个差异至少记录：

```json
{
  "gap_id": "...",
  "component": "...",
  "run_task_behavior": "...",
  "run_episode_behavior": "...",
  "risk": "...",
  "required_stage": "16F.1|16F.2|16F.3|16F.4",
  "blocks_stage17": true
}
```

## 11. required sync items

必须生成 `stage16f0_required_sync_items.json`。它是 Stage 16F.1 的任务输入。

每项至少包含：

```text
decision=sync/defer/ignore/manual-port
```

```json
{
  "sync_item_id": "...",
  "priority": "P1|P2|P3",
  "source": "commit|dirty-file|documented-finding|manual-inspection",
  "source_ref": "...",
  "target_modules": [],
  "summary": "...",
  "risk_if_not_synced": "...",
  "recommended_action": "cherry-pick|manual-port|write-new-implementation|defer",
  "required_tests": [],
  "blocks_stage16f1_entry": false,
  "must_be_addressed_in_stage16f1": true,
  "blocks_stage16f1_completion": true
}
```

字段语义：

```text
blocks_stage16f1_entry:
  是否阻止进入 Stage 16F.1。Stage 16F.0 发现的 P1 同步项通常不阻止进入 Stage 16F.1，因为 Stage 16F.1 正是用来处理这些同步项。

must_be_addressed_in_stage16f1:
  是否必须在 Stage 16F.1 中处理，或者明确写出延期理由。

blocks_stage16f1_completion:
  是否阻止 Stage 16F.1 标记完成。P1 同步项通常应设置为 true。
```

P1 必须至少评估：

```text
diagnostic_shell bash -lc / sh -lc / shell=True 语义差异
run directory 不挂载到模型可见 shell
Git history / evaluator-only 防泄漏
patch hygiene 和 official prediction hygiene 差异
provider failure / timeout / empty response 结构化记账差异
```

## 12. 公开 evidence 泄漏扫描

必须生成 `stage16f0_path_leak_scan_report.json`。

扫描范围至少包括：

```text
docs/agentic_RL/repo_harness_verl_workstreams/42-stage-16f-0-execution-plan.md
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/**/*.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/**/*.jsonl
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/**/*.md
```

必须拒绝或记录为阻断：

```text
本机绝对路径
真实 source worktree 路径
真实 target worktree 路径
真实 run directory 路径
真实私有运行证据目录路径
隐藏 verifier 路径
gold patch 原文
test patch 原文
官方失败到通过测试集合标记和官方通过到通过测试集合标记的原始内容
云服务密钥或配置路径
```

`stage16f0_path_leak_scan_report.json` 必须支持 `allowlisted_contexts`，用于区分“计划文档中的规则说明术语”和“正式公开 evidence 中的真实路径或敏感标记”。推荐策略：

```text
计划文档和执行计划文档：
  允许在规则说明段落中描述风险类别，但不能出现真实本机路径、真实工作树路径或真实私有目录路径。

stage16f_0 公开 JSON、JSONL、manifest 和报告：
  不允许出现真实路径，也不允许出现未脱敏的敏感标记原文。

allowlisted_contexts：
  必须记录文件、章节、允许原因和匹配模式。
  不能用于豁免 stage16f_0 公开 evidence 中的真实路径。
```

允许出现：

```text
runtime-private:<artifact-kind>:<sha256>
相对路径
模块名
文件名
commit hash
sha256
```

## 13. 验收 summary

必须生成 `stage16f0_acceptance_summary.json`，至少包含：

```json
{
  "schema_version": 1,
  "stage": "16F.0",
  "status": "passed|blocked|failed",
  "stage16f0_complete": true,
  "inventory_generated": true,
  "git_baseline_report_present": true,
  "module_diff_matrix_present": true,
  "required_sync_items_present": true,
  "diagnostic_shell_semantics_report_present": true,
  "run_task_run_episode_gap_report_present": true,
  "public_evidence_policy_present": true,
  "path_leak_scan_policy_ref": "stage16f0_public_evidence_policy.json",
  "public_path_leak_scan_passed": true,
  "stage16e_committed_before_stage16f0": true,
  "sync_performed": false,
  "code_behavior_modified": false,
  "ready_for_stage16f1": true,
  "blocking_reasons": []
}
```

如果 `sync_performed=true` 或 `code_behavior_modified=true`，Stage 16F.0 必须失败，因为这说明执行越界。

合法状态语义：

```text
status=passed：
  stage16f0_complete=true
  ready_for_stage16f1=true
  blocking_reasons=[]

status=blocked：
  stage16f0_complete=false
  ready_for_stage16f1=false
  blocking_reasons 必须非空
  只能说明前置条件不满足，不能视为 Stage 16F.0 通过

status=failed：
  stage16f0_complete=false
  ready_for_stage16f1=false
  blocking_reasons 必须非空
```

## 14. 建议实现方式

第一版可以用脚本或手工生成报告，但必须保证报告可复查。

建议新增脚本时放在：

```text
scripts/stage16f/build_stage16f0_inventory.py
```

脚本输入建议使用命令行参数或环境变量传入工作树路径，但公开输出不能写入真实路径：

```text
--source-worktree-label evaluation-worktree
--source-worktree-path <private>
--target-worktree-label training-worktree
--target-worktree-path <private>
--output-dir docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0
```

如果新增脚本，必须新增对应单元测试或最小 golden fixture，覆盖：

```text
本机路径脱敏
dirty 文件 sha256 记录
module_diff_matrix 字段完整性
diagnostic_shell shell 语义识别
public path leak scan
```

如果第一版手工生成 JSON，也必须提供机器校验脚本或最小验证命令，不能只靠人工阅读。

## 15. 建议验证命令

文档和公开 evidence 检查：

```bash
git diff --check -- \
  docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md \
  docs/agentic_RL/repo_harness_verl_workstreams/42-stage-16f-0-execution-plan.md \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0
```

JSON parse 检查：

```bash
python - <<'PY'
from pathlib import Path
import json

root = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0")
for path in sorted(root.glob("*.json")):
    json.loads(path.read_text())
print("stage16f0_json_parse_ok")
PY
```

Stage 16E 冻结前置检查：

```bash
python - <<'PY'
import subprocess

status = subprocess.check_output(["git", "status", "--short"], text=True)
dirty_lines = [line for line in status.splitlines() if line.strip()]
stage16e_markers = [
    "patch_hygiene",
    "build_swebench_official_inputs.py",
    "reward_boundary.py",
    "exporter.py",
    "pairing.py",
    "41-stage-16e-execution-plan.md",
]
stage16e_dirty = [
    line for line in dirty_lines
    if any(marker in line for marker in stage16e_markers)
]
if stage16e_dirty:
    raise SystemExit(
        "stage16e_not_committed_or_target_worktree_dirty: "
        + repr(stage16e_dirty[:20])
    )
print("stage16e_precondition_ok")
PY
```

公开路径和敏感标记扫描必须使用读取 `stage16f0_public_evidence_policy.json` 的 policy-aware scanner。下面的命令只是最小结构示例，不能退化成不读取 policy 的硬编码全文扫描：

```bash
python - <<'PY'
from pathlib import Path
import json

public_root = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0")
policy_path = public_root / "stage16f0_public_evidence_policy.json"
policy = json.loads(policy_path.read_text()) if policy_path.exists() else {
    "allowlisted_contexts": []
}

planning_docs = [
    Path("docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md"),
    Path("docs/agentic_RL/repo_harness_verl_workstreams/42-stage-16f-0-execution-plan.md"),
]
needles = [
    "/" + "Users" + "/",
    "/" + "private" + "/",
    "/" + "workspace" + "/",
    "/" + "testbed",
    "runtime" + "_" + "private",
    "runtime" + "-" + "private" + "/",
    ".repo" + "_harness" + "_runtime",
    ".repo" + "_harness" + "_env" + "_overlay",
    "repo" + "-" + "harness" + "-" + "run",
    "runtime" + "_" + "private" + "/",
    "FAIL" + "_TO" + "_PASS",
    "PASS" + "_TO" + "_PASS",
    "gold" + "_patch",
    "test" + "_patch",
    "hidden" + "_verifier",
]

def _is_allowlisted(path: Path, needle: str) -> bool:
    path_text = path.as_posix()
    for item in policy.get("allowlisted_contexts", []):
        if item.get("path") != path_text:
            continue
        if needle not in item.get("allowed_needles", []):
            continue
        if not item.get("reason"):
            raise SystemExit(f"allowlist entry missing reason for {path_text}")
        return True
    return False

findings = []

for path in planning_docs:
    text = path.read_text(errors="ignore")
    for needle in needles:
        if needle in text and not _is_allowlisted(path, needle):
            findings.append((str(path), needle, "planning_doc_not_allowlisted"))

if public_root.exists():
    for path in public_root.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for needle in needles:
            if needle in text:
                findings.append((str(path), needle, "public_evidence_forbidden"))

if findings:
    raise SystemExit(f"public leak findings: {findings[:20]}")
print("stage16f0_public_leak_scan_ok")
PY
```

如果新增 Python 脚本或代码：

```bash
PATH=.venv/bin:$PATH python -m compileall src scripts tests
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_stage16f0_inventory.py
```

普通导入和重依赖检查：

```bash
PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness

loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
if loaded:
    raise SystemExit(f"unexpected heavy imports: {loaded}")
print("ordinary_import_ok")
PY
```

## 16. 通过标准

Stage 16F.0 可以通过的最低条件：

1. Stage 16E 已单独提交。若 Stage 16E 未提交，只能输出 `status=blocked`，不能算 Stage 16F.0 通过。
2. `stage16f0_git_baseline_report.json` 存在并记录 canonical baseline 语义。
3. `stage16f0_source_worktree_inventory.json` 和 `stage16f0_target_worktree_inventory.json` 存在。
4. dirty 文件处理完整，未进入 dirty report 的 dirty 文件不能作为同步来源。
5. `stage16f0_module_diff_matrix.json` 覆盖指定模块，并为每项给出 `sync / defer / ignore / manual-port` 决策。
6. `stage16f0_diagnostic_shell_semantics_report.json` 明确识别 `bash -lc`、`sh -lc`、`shell=True` 差异，并给出是否 P1 同步。
7. `stage16f0_run_task_run_episode_gap_report.json` 明确记录 `raw_prompt`、`ToolExecutor()`、`resolved_verifier_plan`、`test_feedback_policy` 等已知差异。
8. `stage16f0_required_sync_items.json` 能作为 Stage 16F.1 的直接输入。
9. `stage16f0_public_evidence_policy.json` 存在。
10. `stage16f0_path_leak_scan_report.json` 声明自己按 `stage16f0_public_evidence_policy.json` 执行，并且公开 evidence 泄漏扫描通过。
11. `stage16f0_acceptance_summary.json` 标记 `status=passed`、`stage16f0_complete=true`、`sync_performed=false`、`code_behavior_modified=false`、`ready_for_stage16f1=true`。

如果 Stage 16F.0 输出 `status=blocked`，它只能作为前置条件失败的结构化报告，不能作为通过结果，也不能进入 Stage 16F.1。

## 17. 进入 Stage 16F.1 的条件

只有满足以下条件，才能进入 Stage 16F.1：

1. Stage 16F.0 summary 为 `passed`。
2. 没有公开 evidence 泄漏。
3. P1 同步项已经明确列出。
4. canonical baseline 语义已经明确。
5. module diff matrix 已经明确哪些模块要同步、哪些要手工移植、哪些要延后。
6. 两个工作树的 dirty 文件状态已经可审计。

如果 Stage 16F.0 输出 `blocked`，下一步只能先处理 blocking reason，不能进入 Stage 16F.1。
