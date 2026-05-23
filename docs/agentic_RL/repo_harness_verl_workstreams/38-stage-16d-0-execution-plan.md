# Stage 16D.0 执行计划：跨 worktree verifier / harness 状态同步

创建日期：2026-05-24

## 1. 背景

当前训练 worktree 是：

```text
training_worktree
```

另一个评测和 harness 诊断 worktree 是：

```text
evaluation_worktree
```

评测 worktree 已经产出同步说明：

```text
evaluation worktree docs/resume/cross-worktree-verifier-harness-sync-20260523.md
```

`training_worktree` 和 `evaluation_worktree` 都只是公开文档里的 label。执行时可以用本机路径
解析这些 label，但本机绝对路径不能写入任何计划提交到仓库的公开 evidence、manifest、JSON、
JSONL、Markdown 或日志。

这份说明指出，评测 worktree 已经在 SWE-bench Verified 分数差距排查中修复或验证了一批
verifier、official harness、diagnostic shell、公开测试提示和 patch hygiene 问题。

训练 worktree 即将进入 Stage 16D：

```text
official verifier / gold patch / no-op healthcheck
```

如果直接在训练 worktree 的旧 verifier / harness 语义上执行 Stage 16D，可能会重复排查评测
worktree 已经修复的问题，也可能把过时 verifier 结果误当成训练数据结论。因此 Stage 16D
之前新增 Stage 16D.0，用来做定向同步和输入冻结。

## 2. 阶段目标

Stage 16D.0 的目标不是直接完成 official verifier healthcheck，也不是把两个 worktree 无差别
合并。它只解决四件事：

1. 复核评测 worktree 的同步说明是否与实际代码、提交和测试一致。
2. 把评测 worktree 中与训练链路相关的 verifier / harness 修复分成：
   - 已经在训练 worktree 等价实现；
   - 必须同步；
   - 强烈建议同步；
   - 只同步结论，不同步代码；
   - 暂不同步。
3. 为 Stage 16D 准备小规模 verifier healthcheck seed set，包括 gold patch、no-op、gold unhealthy、
   local official flaky、模型语义失败但 harness 正常、positive path 等类别。
4. 同步后跑训练 worktree 的关键回归，证明没有破坏 Stage 13 到 Stage 16C 的 verl 训练链路、
   formal online reinforcement learning gate、工具可见性和 evidence 规则。

## 3. 非目标

Stage 16D.0 不做下面这些事情：

```text
不全量合并 evaluation worktree 到训练 worktree。
不把评测 worktree 的所有临时文档、HTML 报告、实验脚本或未完成诊断代码混入训练 worktree。
不执行完整 SWE-bench Verified 500 题 official harness。
不建立 Stage 17 的完整 R2E-Gym / SWE-Gym / 内部任务 registry。
不扩大 execute_bash 或 diagnostic_shell 权限。
不改变 Stage 13 到 Stage 15 fully async / partial rollout 已通过的训练链路语义。
不把 invalid、environment unhealthy、oracle invalid 或 verifier-no-discrimination 样本放进训练。
```

## 4. 前置条件

开始 Stage 16D.0 之前，训练 worktree 至少应满足：

1. Stage 16A 的 `execute_bash` 安全最小工具面已经通过。
2. Stage 16B 的 `diagnostic_shell` 生命周期和训练资格 gate 已经通过。
3. Stage 16B.5 的远端 Docker-capable backend smoke 已经通过，或者其结论已经被记录为
   `remote_docker_diagnostic_profile_verified=true`。
4. Stage 16C 的公开环境上下文、本地 evidence 和 prompt leak scan 已经通过。
5. Stage 16C 必须先单独提交。若训练 worktree 仍存在 Stage 16C 相关未提交修改，例如
   `src/repo_harness/tasks/public_environment.py`、`37-stage-16c-execution-plan.md` 或 Stage 16C
   测试文件，Stage 16D.0 必须停止执行。执行 agent 不能把 Stage 16C 代码和跨 worktree
   同步代码混在同一个提交、同一份 inventory 基线或同一份 regression report 中。

建议执行前记录：

```bash
export EVAL_WORKTREE=<local evaluation worktree path>
git status --short
git log --oneline -20
git -C "$EVAL_WORKTREE" status --short
git -C "$EVAL_WORKTREE" log --oneline -30
```

`EVAL_WORKTREE` 的真实值只能出现在执行日志或 runtime-private 私有报告中。任何计划提交到
`docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/` 的公开 JSON、Markdown、JSONL、
shell script、log 或 manifest 不能写入本机绝对路径，只能写入 label、commit、sha256 和相对
evidence 引用。

## 5. 输入资料

### 5.1 必读文档

```text
evaluation worktree docs/resume/cross-worktree-verifier-harness-sync-20260523.md
evaluation worktree docs/resume/swebench-verified-score-gap-investigation-progress.md
evaluation worktree docs/resume/pre-verl-persistent-diagnostic-session-implementation-plan.md
docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/34-stage-16a-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/35-stage-16b-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/36-stage-16b-5-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/37-stage-16c-execution-plan.md
```

### 5.2 评测 worktree 建议同步提交

同步说明列出的提交需要逐项核验，而不是盲目 cherry-pick。

必须核验的提交：

```text
a0cd2fa3 feat: add persistent diagnostic sessions
13437b12 fix: keep diagnostic dependency environment read-only
368ad041 fix: surface diagnostic timeout and disable user site
48a66da3 fix: block diagnostic dependency mutations
f6ead6f5 fix: prepare dependency image for diagnostic shell
6c7757b9 fix: run diagnostic shell through bash
aaec6639 fix: isolate diagnostic dependency preparation
c0cc1b40 fix: expose repo-specific public test hints
cfbbe4b5 fix: derive public test hints for score-gap probes
dd3a6ec1 fix: guide score-gap probes toward targeted tests
d2fc8e7d fix: harden diagnostic shell audit guards
9c9daf4a fix: strip diagnostic temp files from official predictions
```

强烈建议核验的提交：

```text
7cb8c25e fix: keep diagnostic shell patches clean
8e3e916a fix: avoid diagnostic shell test patch false positives
c8867f55 fix: exclude diagnostic backup files from patches
32309442 fix: strip diagnostic reject artifacts from patches
5f3a88f0 fix: strip quoted diagnostic patch leftovers
2cffe78b fix: strip tmp diagnostic leftovers
71b1ae5b fix: strip diagnostic artifacts from SWE-bench predictions
07f8c90f fix: harden diagnostic shell environment guidance
```

只同步结论、不默认同步代码的文档提交：

```text
70843853 docs: record repr60 official audit
eb8a8676 docs: record repr50 official audit
e25f56ce docs: record repr40 official audit
910b6695 docs: record repr30 dependency prepare findings
118e518c docs: record public test hint probe
a514409a docs: record targeted public test guidance
531625ac docs: add cross-worktree harness sync inventory
```

## 6. 执行步骤

### 6.1 建立 cross-worktree inventory

新增产物：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/cross_worktree_verifier_fix_inventory.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_required_cherrypicks.json
```

inventory 必须逐项记录：

```text
source_commit
source_worktree_label
source_doc_sha256
source_evidence_ref
source_files_changed
topic
claimed_fix
actual_code_evidence
actual_test_evidence
current_verl_worktree_status
sync_decision
sync_method
target_files
risk_if_skipped
risk_if_synced
required_regression_tests
```

公开 inventory 禁止记录 `source_worktree_path`、`target_worktree_path` 或任何本机绝对路径。
如果执行 agent 需要保留真实路径用于复现，必须写入未提交的 runtime-private 私有报告，并在公开
inventory 中只记录该私有报告的 sha256。

`sync_decision` 只能使用下面枚举：

```text
already_equivalent
sync_required
sync_recommended
conclusion_only
defer
reject
```

`sync_method` 只能使用下面枚举：

```text
cherry_pick_clean
manual_port
new_stage_specific_implementation
document_only
no_action
```

### 6.2 核验评测 worktree 文档是否属实

执行 agent 必须至少检查：

```bash
export EVAL_WORKTREE=<local evaluation worktree path>
git -C "$EVAL_WORKTREE" show --name-status --oneline <commit>
git -C "$EVAL_WORKTREE" show --stat --oneline <commit>
git -C "$EVAL_WORKTREE" show <commit> -- <关键文件>
```

重点核验：

1. `diagnostic_shell` 生命周期、Docker / local backend、timeout、dependency guard 是否实际存在。
2. Git history、hidden evaluator、dependency mutation、test patch false positive 等 guard 是否有测试。
3. `repo_harness_public_test_command` 或公开测试提示是否真实进入 ContextBuilder。
4. official prediction 构建脚本是否真实剥离：

   ```text
   测试文件改动
   patch.txt
   tmp/
   .repo_harness_tmp/
   *.orig
   *.rej
   quoted path leftovers
   顶层诊断脚本
   ```

5. 20 题 gold patch smoke、no-op 风险、repr60 official audit 是否有实际 evidence 路径或文档记录。

如果发现评测 worktree 文档与代码不一致，不能把对应项标成 `sync_required`；应标成
`defer` 或 `conclusion_only`，并在 inventory 里写明原因。

如果评测 worktree 不是干净状态，执行 agent 不能忽略。必须在公开 inventory 中记录：

```text
source_dirty_status = clean 或 dirty
source_dirty_file_count
source_dirty_files_sha256
source_dirty_participates_in_claims = true / false
```

公开 inventory 仍然不能写本机绝对路径。若 dirty diff 需要保留，写入 runtime-private 私有报告；
公开 inventory 只记录文件标签、sha256、主题和是否影响本次结论。若 dirty 内容影响同步结论，
优先要求评测 worktree 先提交或拆分，否则对应项标成 `defer`。

### 6.3 对照训练 worktree 已有实现

执行 agent 必须对照当前训练 worktree 已完成的 Stage 16A / 16B / 16B.5 / 16C，避免重复移植。

重点对照：

```text
src/repo_harness/tasks/command_policy.py
src/repo_harness/tools/minimal.py
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/context/builder.py
src/repo_harness/tasks/public_environment.py
tests/unit/test_command_policy.py
tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py
tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py
tests/unit/test_repo_harness_stage16c_public_environment_context.py
```

示例判定：

```text
如果训练 worktree 已经有更严格的 execute_bash allowlist，则评测 worktree 的旧 shell guard
不应直接覆盖，只能作为测试样例补充。

如果训练 worktree 已经有 Stage 16C public_environment_context，但没有 repo-specific public test
hint 推导，则应标记为 sync_recommended 或 new_stage_specific_implementation。

如果训练 worktree 没有 scripts/pre_verl/build_swebench_official_inputs.py，则评测 worktree 的
official prediction patch hygiene 逻辑不能简单标成 already_equivalent。
```

`scripts/pre_verl/build_swebench_official_inputs.py` 是单独核验项。当前训练 worktree 如果没有
这个脚本或等价 official prediction builder，执行 agent 必须把 official prediction hygiene 标成
`sync_required`、`sync_recommended` 或 `new_stage_specific_implementation`，不能只凭 Stage 16E
计划或 final patch hygiene 口头要求标成已经覆盖。

子代理复核已经确认：评测 worktree 的同步清单总体可信，但其中若干主题不能机械 cherry-pick。
执行 agent 必须特别注意下面两个差异：

1. 评测 worktree 的 Docker diagnostic shell 后续修复包含 `bash -lc`、只读 root filesystem、
   workspace writable、依赖环境只读、dependency image preparation 和 dependency prepare isolation。
   当前训练 worktree 虽然已经完成 Stage 16B / 16B.5，但仍必须逐项核验 Docker diagnostic
   backend 是否真的具备这些事实，尤其不能只因为远端 smoke 通过就标成 `already_equivalent`。
2. 训练 worktree 的 Stage 16C `public_environment` 目前会严格拒绝 `/workspace`、`/testbed`、
   `conda activate` 等字符串；评测 worktree 的 score-gap public test hints 则包含官方 harness
   或 testbed 风格命令。Stage 16D.0 不能用评测 worktree 的具体 prompt 覆盖 Stage 16C，
   而应该把这些经验转成 repository profile / public test metadata adapter。也就是说，
   模型可见 public test hint 必须先通过 Stage 16C visibility gate，不能因为来自评测 worktree
   就绕过 forbidden substring 检查。

### 6.4 定向同步或移植

同步原则：

1. 优先同步 verifier、official prediction、patch hygiene、public test hint 和 guard 测试。
2. 不用评测 worktree 的旧实现覆盖训练 worktree 中已经更严格的 Stage 16A / 16B / 16C 实现。
3. 对同一主题如果训练 worktree 已有更强策略，只补测试和结论，不补旧代码。
4. 如果提交无法 clean cherry-pick，必须手动移植并写入 `manual_port_reason`。
5. 所有移植都必须保留训练 worktree 的 verl import 边界：`repo_harness` core 不能新增对 `verl` 的直接依赖。

建议分批提交：

```text
提交 1：Stage 16D.0 inventory 和 seed manifest 文档。
提交 2：必要 verifier / official prediction / patch hygiene 代码同步。
提交 3：必要公开测试 hint 或 diagnostic guard 测试同步。
```

如果代码改动很少，也可以合并提交 2 和提交 3，但不能把无关 HTML、临时报告、vastai / spheron
凭据文档或未审查训练设计草稿混入。

### 6.5 准备 Stage 16D seed task manifest

新增产物：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_seed_task_manifest.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_gold_patch_source_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_noop_patch_source_report.json
```

seed manifest 不是 Stage 17 的完整训练 registry。它只是 Stage 16D 的小规模健康检查输入。

每条 seed 至少包含：

```json
{
  "instance_id": "sphinx-doc__sphinx-8638",
  "seed_role": "model_semantic_failure_harness_normal",
  "source_dataset": "swebench_verified",
  "source_worktree_label": "evaluation_worktree",
  "source_commit": "commit hash for the evaluated source state",
  "source_doc_sha256": "sha256 of the source evidence document",
  "source_evidence_ref": "docs/resume/swebench-verified-score-gap-investigation-progress.md",
  "gold_patch_source": "dataset_gold_patch_or_manual_fixture_or_not_available",
  "noop_patch_source": "empty_patch_or_marker_patch_or_not_available",
  "gold_health_status": "not_checked_in_stage16d_0",
  "noop_health_status": "not_checked_in_stage16d_0",
  "official_validation_backend": "swebench_official_harness",
  "known_harness_issue": null,
  "known_environment_issue": null,
  "public_test_hint_status": "unknown_or_available_or_unavailable",
  "diagnostic_shell_public_test_observation_status": "not_checked_in_stage16d_0",
  "public_tests_ran_semantics": "not_equivalent_to_model_never_ran_public_tests",
  "training_use_recommendation": "diagnostic_only_until_stage16d_healthcheck_passes"
}
```

必须覆盖这些 seed role：

```text
gold_patch_smoke_pass_candidate
noop_oracle_risk
gold_unhealthy
local_official_flaky
model_semantic_failure_harness_normal
positive_path_official_resolved
```

建议第一版 seed：

```text
gold patch smoke：评测 worktree 中 20 题 gold patch smoke 集合，或其可追溯 evidence。
noop_oracle_risk：django__django-10097。
gold_unhealthy：psf__requests-2317。
local_official_flaky：psf__requests-1766。
model_semantic_failure_harness_normal：django__django-16502、sphinx-doc__sphinx-8638。
positive_path_official_resolved：从 repr60 official resolved 样本中抽取至少 3 题，覆盖不同 repository profile。
```

如果某个 seed 暂时没有可执行 patch 或本地 official harness 输入，仍然可以进入 manifest，但必须标记：

```text
training_use_recommendation = diagnostic_only_until_stage16d_healthcheck_passes
```

不能伪装成已经通过 Stage 16D healthcheck。

seed manifest 中还必须保留下面两个说明字段，防止把评测结论外推成训练结论：

```text
evidence_scope
generalization_limit
```

例如 repr60 的 `42/60` 和调整后 `42/58 = 72.4%` 只能记录为代表性诊断样本结果，
不能写成 Verified 500 的稳定预期。`psf__requests-1766` 只能记录为 candidate false negative
或 local official flaky；`psf__requests-2317` 必须记录为 gold-unhealthy，不能包装成模型能力问题。

### 6.6 生成同步回归报告

新增产物：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/stage16d_sync_regression_report.json
```

报告至少包含：

```text
schema_version
created_at
source_worktree_commit
source_worktree_label
source_dirty_status
source_dirty_files_sha256
target_worktree_commit_before
target_worktree_commit_after
synced_commit_count
manual_port_count
already_equivalent_count
deferred_count
rejected_count
regression_commands
regression_results
blocking_failures
remaining_risks
```

## 7. 必跑回归

### 7.1 Stage 16 相关回归

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py \
  tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py \
  tests/unit/test_repo_harness_verl_stage16b5_acceptance.py \
  tests/unit/test_repo_harness_stage16c_public_environment_context.py \
  tests/unit/test_repo_harness_stage16c_public_test_entry.py \
  tests/unit/test_repo_harness_stage16c_scaffold_prompt.py \
  tests/unit/test_repo_harness_stage16c_visibility.py
```

### 7.2 Verifier / feedback / visibility 回归

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_test_feedback_policy.py \
  tests/unit/test_feedback_tests_passed_policy.py \
  tests/integration/test_tool_execution.py \
  tests/unit/test_context_builder.py \
  tests/unit/test_v3_visibility_policy.py \
  tests/unit/test_v4_task_freeze.py \
  tests/unit/test_v4_export_quality.py \
  tests/unit/test_v4_stage1_skeleton.py \
  tests/integration/test_repo_harness_verl_stage12a_visibility_dataproto.py
```

### 7.3 verl 训练链路关键回归

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_verl_stage13_3a_message_queue_filter.py \
  tests/unit/test_repo_harness_verl_stage13_3a_parameter_versions.py \
  tests/unit/test_repo_harness_verl_stage13_3a_resource_lifecycle.py \
  tests/unit/test_repo_harness_verl_stage15_1_partial_rollout_resume.py \
  tests/unit/test_repo_harness_verl_stage15_0_acceptance.py
```

### 7.4 通用检查

```bash
PATH=.venv/bin:$PATH python -m compileall -q src

if rg -n '(^|[^A-Za-z_])(import verl|from verl)' src/repo_harness src/repo_harness/workspace src/repo_harness/tasks; then
  echo 'unexpected core verl import'
  exit 1
fi

git diff --check
```

如果某些历史 evidence 测试依赖缺失，本阶段不能把它们解释成同步成功或失败；应在
`stage16d_sync_regression_report.json` 中写成 `historical_evidence_missing`，并说明是否影响
本阶段目标。

### 7.5 公开 evidence 路径和 oracle 泄漏扫描

Stage 16D.0 必须对即将提交的公开产物执行机器化扫描。扫描范围至少覆盖：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/**/*.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/**/*.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/**/*.jsonl
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/**/*.log
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/**/*.sh
docs/agentic_RL/repo_harness_verl_workstreams/stage16d_0/**/*manifest*
```

扫描必须拒绝下面这些公开泄漏：

```text
local user home absolute path pattern，例如 /Users/<local-user>/ 或 /home/<local-user>/
/private/
/workspace
/testbed
runtime_private
FAIL_TO_PASS
PASS_TO_PASS
gold_patch
test_patch
hidden_verifier
```

如果某个词只作为枚举字段名或安全规则说明出现，必须使用明确的 allowlisted context，并在
`stage16d_sync_regression_report.json` 中记录原因。seed manifest 和公开 evidence 默认不允许
出现这些字符串的原始值。

## 8. 训练资格和数据边界

Stage 16D.0 生成的所有 seed、报告和同步 evidence 默认都是诊断材料。

在 Stage 16D 正式 healthcheck 通过之前：

```text
gold_unhealthy 样本不能作为模型失败样本。
noop_oracle_risk 样本不能作为模型成功或失败样本。
local_official_flaky 样本不能作为模型失败样本。
model_semantic_failure_harness_normal 只能作为候选诊断样本，不能跳过 Stage 16D healthcheck 直接进入训练。
positive_path_official_resolved 也不能只凭评测 worktree 记录进入训练，必须在训练 worktree 的 manifest 中保留 source evidence 和后续 healthcheck 结果。
```

Stage 16D.0 不能把下面内容放进模型可见 prompt、TrainingView、AgentLoopOutput、DataProto 或
policy-loss queue：

```text
gold patch 内容
test patch 内容
FAIL_TO_PASS / PASS_TO_PASS selector
official report 原始 hidden details
完整 reward metadata
评测 worktree 的 runtime_private 路径
本机绝对路径
```

## 9. 公开 evidence 和私有 evidence

公开 evidence 可以包含：

```text
commit hash
文件 sha256
seed role
health status 枚举
训练使用建议
相对路径或 opaque ref
```

私有 evidence 可以包含：

```text
本机 worktree 绝对路径
原始 official harness 日志路径
临时运行目录
runtime_private raw log
```

私有 evidence 必须放入明确的 `runtime_private/` 或不提交目录，并通过公开 manifest 的 sha256
绑定。公开 JSON / Markdown / log 不能泄漏本机绝对路径、hidden selector、gold patch 内容或
runtime-private 目录结构。

## 10. 验收标准

Stage 16D.0 通过必须满足：

1. `cross_worktree_verifier_fix_inventory.md` 完成，并逐项核验同步说明中的主要提交。
2. `stage16d_required_cherrypicks.json` 完成，并清楚区分 `sync_required`、`sync_recommended`、
   `already_equivalent`、`conclusion_only`、`defer` 和 `reject`。
3. 必要代码同步或手动移植完成，且每个移植都有测试或明确诊断理由。
4. `stage16d_seed_task_manifest.json` 完成，至少覆盖 6 类 seed role。
5. `stage16d_gold_patch_source_report.json` 和 `stage16d_noop_patch_source_report.json` 完成，
   且没有声称尚未执行的 healthcheck 已通过。
6. `stage16d_sync_regression_report.json` 完成，记录所有必跑回归结果。
7. Stage 16A / 16B / 16B.5 / 16C 关键回归仍然通过。
8. Stage 13 到 Stage 15 的 fully async / partial rollout 关键回归仍然通过。
9. `repo_harness` core 仍然没有直接 import `verl`。
10. 没有无关 HTML、训练设计草稿、云服务凭据文档、远端原始日志或 runtime-private raw evidence
    被混入提交。
11. 对评测 worktree 提到的 Docker diagnostic backend 事实完成逐项核验，至少包括：

    ```text
    shell_entrypoint = bash -lc 或等价 Bash 语义
    root_filesystem_read_only
    workspace_writable
    dependency_environment_read_only
    dependency_prepare_isolated_from_agent_workspace
    run_directory_not_mounted
    ```

    如果当前训练 worktree 只完成了其中一部分，必须在 inventory 中标成 `sync_required`、
    `sync_recommended` 或 `defer`，不能标成 `already_equivalent`。
12. Stage 16C public environment 与评测 worktree public test hints 的冲突已经被显式分类。
    任何包含 `/testbed`、`/workspace` 或其他 Stage 16C 禁止字符串的 public command，都必须先
    进入 adapter / profile 设计，不能直接进入模型可见 prompt。

## 11. Stage 16D.0 后才能进入 Stage 16D 的条件

只有当 Stage 16D.0 通过后，Stage 16D 才能开始正式设计：

```text
official verifier / gold patch / no-op healthcheck
```

Stage 16D 应消费 Stage 16D.0 的 seed manifest 和同步报告，而不是重新从两个 worktree 的历史中
人工查找输入。Stage 16D 的任务是实际运行 healthcheck、建立 official verifier manifest、记录
proxy / official disagreement，并把 healthcheck 结果变成 Stage 17 task registry 可以复用的字段。
