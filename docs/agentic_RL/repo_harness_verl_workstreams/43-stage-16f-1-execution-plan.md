# Stage 16F.1 执行计划：受控同步关键 Harness 修复

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.1 的目标是根据 Stage 16F.0 生成的 inventory，受控同步已经确认会影响训练数据质量和测评可信度的 Harness 修复。它是一个小范围、可审计的同步阶段，不是完整入口迁移阶段。

Stage 16F.1 只处理 Stage 16F.0 标记为必须优先处理的同步项，尤其是：

```text
P1：diagnostic_shell 的 bash -lc / sh -lc / shell=True 语义差异。
P1：模型可见 diagnostic shell 不能访问 RepoHarness run directory。
P1：Stage 16E patch hygiene 与 official prediction hygiene 必须作为训练工作树基线，并和测评工作树修复进行差异核对。
```

这一阶段完成后，训练工作树应该具备一个更接近测评工作树真实 SWE-Bench 诊断能力的 Harness 基线，但仍不宣称 `run_task(...)` 和 `run_episode(real_episode)` 已经统一。入口统一留给 Stage 16F.2 到 Stage 16F.4。

## 2. 输入依据

Stage 16F.1 必须以 Stage 16F.0 的公开产物为输入：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_required_sync_items.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_module_diff_matrix.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_diagnostic_shell_semantics_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_run_task_run_episode_gap_report.json
```

执行前必须确认：

```text
stage16f0_acceptance_summary.status == passed
stage16f0_acceptance_summary.sync_performed == false
stage16f0_acceptance_summary.code_behavior_modified == false
stage16f0_acceptance_summary.ready_for_stage16f1 == true
```

如果 Stage 16F.0 产物不存在、无法解析、或者状态不是 `passed`，Stage 16F.1 必须停止。

其中 Stage 16F.1 必须优先处理的 P1 同步项至少包括：

```text
sync_item_id=p1_diagnostic_shell_bash_lc_semantics
sync_item_id=p1_run_directory_not_model_visible
sync_item_id=p1_patch_and_official_prediction_hygiene
must_be_addressed_in_stage16f1=true
```

如果 Stage 16F.0 后续 inventory 增加新的 `must_be_addressed_in_stage16f1=true` 项，执行 agent 必须把它加入 Stage 16F.1 同步状态报告；不能只处理本文档手写列出的三项。

Stage 16F.0 的全部 `required_sync_items` 都必须出现在 Stage 16F.1 的状态报告中。P1 项必须完成或证明已经由当前训练工作树覆盖；P2 / P3 项可以同步，也可以明确延期，但不能缺席。

## 3. 非目标

Stage 16F.1 不做以下事情：

1. 不实现 `EpisodeExecutionSpec` 或 `EpisodeExecutionSpecBuilder`。
2. 不新增 `run-episode-task` 或 `run-episode-batch` 命令。
3. 不把 `run_task(...)` 重写为 `run_episode(real_episode)` 包装层。
4. 不做 run directory projection。
5. 不运行 20 到 30 题代表性 harness 诊断。
6. 不运行远端 GPU 训练。
7. 不把测评工作树的运行目录、HTML 报告、本机路径、云服务配置或私有日志同步进训练工作树。
8. 不用测评工作树实现覆盖 Stage 16A 到 Stage 16E 已有的更严格边界。

如果某项修复需要大规模重构入口或重写 builder，必须延后到 Stage 16F.2 或单独拆分。

## 4. 工作方式

同步方式优先级：

```text
1. 手工移植小范围逻辑。
2. cherry-pick 小提交，但只在提交边界干净、不会覆盖当前 Stage 16A 到 Stage 16E 边界时使用。
3. 重新实现等价逻辑，并在报告中记录为什么没有直接移植。
4. 对暂不处理的 P2 / P3 项写出 defer reason。
```

Stage 16F.1 的核心原则是：

```text
只同步已经明确影响 Harness 可靠性的行为修复。
每个行为修复都必须有测试。
每个同步项都必须回写到 sync report。
不能静默改变模型可见工具面。
不能放松 execute_bash、diagnostic_shell、patch hygiene、visibility 或 formal online RL gate。
```

## 5. 产物目录

建议新增公开安全目录：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/
```

公开产物建议包括：

```text
stage16f1_sync_execution_report.json
stage16f1_manual_port_manifest.json
stage16f1_required_sync_item_status.json
stage16f1_diagnostic_shell_semantics_report.json
stage16f1_run_directory_visibility_report.json
stage16f1_patch_hygiene_comparison_report.json
stage16f1_provider_failure_accounting_decision_report.json
stage16f1_module_diff_after_report.json
stage16f1_test_report.json
stage16f1_public_leak_scan_report.json
stage16f1_acceptance_summary.json
```

公开产物只能记录：

```text
commit hash
relative path
sha256
模块名
测试命令
聚合结果
runtime-private:<artifact-kind>:<sha256> 不透明引用
```

公开产物不能记录本机绝对路径、真实工作树路径、真实私有运行证据目录路径、云服务配置、原始 gold patch、原始 test patch、隐藏 verifier 内容、官方测试选择器原文或未脱敏模型响应。

## 6. Step 1：同步 diagnostic_shell 的 bash 语义

Stage 16F.0 已确认：

```text
测评工作树 diagnostic shell path:
  Docker diagnostic shell = bash -lc
  Local diagnostic shell = bash -lc

训练工作树 diagnostic shell path:
  Docker diagnostic shell = sh -lc
  Local diagnostic shell = shell=True
```

Stage 16F.1 必须修复训练工作树的 diagnostic shell path：

```text
Docker persistent diagnostic session:
  由 sh -lc 改为 bash -lc。

Local filesystem-persistent diagnostic session:
  不能继续依赖 shell=True 默认 shell。
  第一版应显式使用 bash -lc。
  如果 bash 不可用，返回结构化 diagnostic_shell_bash_unavailable。
```

同时需要记录或新增 facts：

```text
diagnostic_session_execution_shell = bash
diagnostic_session_execution_argv_digest
diagnostic_session_shell_semantics_version
diagnostic_session_shell_login_mode = login
diagnostic_session_shell_interactive_mode = non_interactive
diagnostic_session_shell_startup_policy = recorded
diagnostic_session_shell_home_policy
diagnostic_session_shell_bash_env_policy
diagnostic_session_shell_env_policy
```

说明：`bash -lc` 是 non-interactive login shell。Stage 16F.1 第一版优先对齐测评工作树已经使用的 `bash -lc` 诊断语义，因此不能把该事实记录为 `non_login`。如果后续阶段决定改成 `bash -c`，必须在诊断语义报告中记录为有意差异，并解释 `source`、`conda activate`、`set -o pipefail` 等行为是否仍然等价。

测试要求：

```text
diagnostic_shell 能执行 bash-only 语法。
diagnostic_shell 能执行 source script.sh。
diagnostic_shell 能执行 set -o pipefail，并正确传播管道失败。
diagnostic_shell 在 Docker backend 下使用 bash -lc。
diagnostic_shell 在 Local test override backend 下不使用 shell=True。
diagnostic_shell 运行 shopt -q login_shell 的结果必须和 diagnostic_session_shell_login_mode=login 一致。
diagnostic_shell 必须记录 HOME、BASH_ENV 和 ENV 的处理策略，避免未审计的启动文件影响模型可见诊断行为。
如果 bash 不存在，返回结构化错误而不是回退到 sh。
```

注意：

1. 非 diagnostic shell 的内部 Docker maintenance command 可以继续使用现有语义，除非它影响模型可见诊断行为。
2. Stage 16F.1 只要求 diagnostic path 对齐，不要求全仓库所有 `sh -lc` 都消失。
3. 如果测试环境没有 Docker，可以保留 Docker 测试为 conditional，但必须至少用单元测试或命令构造测试证明 Docker diagnostic argv 是 `bash -lc`。

## 7. Step 2：确认 run directory 不进入模型可见 diagnostic shell

Stage 16B 已经要求 Docker diagnostic session 不挂载 run directory。Stage 16F.1 需要把测评工作树的确认经验固化成训练工作树回归，证明这一点不会在同步中退化。

必须覆盖：

```text
diagnostic projection workspace 不包含 run directory。
diagnostic shell 不能读取真实 run directory。
diagnostic shell 不能读取 runtime-private 私有证据目录。
diagnostic shell 输出和 typed metadata 不泄漏真实 run directory 路径。
Docker container mount list 不包含 run directory。
Local test override 只能 diagnostic side channel，不能进入正式训练候选。
```

建议测试：

```text
diagnostic_shell 执行 ls /repo-harness-run 或等价路径时失败或不可见。
diagnostic_shell 执行容器内 projection mount point 枚举时只看到 diagnostic-visible projection workspace。
diagnostic_shell 不能看到 final_patch_hygiene_report 的 raw patch 私有路径。
```

如果某些路径只在 Docker 环境可测，Local 单元测试必须至少覆盖 projection 和 path redaction 行为。

## 8. Step 3：Stage 16E patch hygiene 与测评工作树修复核对

Stage 16E 已经在训练工作树建立统一 patch hygiene 基线。Stage 16F.1 不应盲目用测评工作树的旧过滤逻辑覆盖它，而应做差异核对。

必须比较：

```text
训练工作树 src/repo_harness/workspace/patch_hygiene.py
测评工作树 official prediction hygiene 相关逻辑
训练工作树 scripts/pre_verl/build_swebench_official_inputs.py
测评工作树 scripts/pre_verl/build_swebench_official_inputs.py
```

重点检查是否遗漏：

```text
.modified / .new / 旁路副本文件
异常 quoted path
test-like 文件策略
patch.txt / *.orig / *.rej
临时诊断脚本
依赖目录和缓存目录
runtime-private 变体
only-filtered patch 拒绝
official prediction eligibility 传播
```

执行原则：

```text
如果 Stage 16E 已经覆盖且测试更严格，保留训练工作树实现。
如果测评工作树有 Stage 16E 未覆盖的真实 bug fix，手工移植到统一 patch hygiene policy 或 official input builder。
如果差异属于数据集策略，而不是通用 hygiene policy，写入 defer reason，留给 Stage 17 dataset policy。
```

必须生成：

```text
stage16f1_patch_hygiene_comparison_report.json
```

该报告至少包含：

```json
{
  "compared_modules": [],
  "source_only_rules": [],
  "target_only_rules": [],
  "rules_ported": [],
  "rules_deferred": [],
  "false_positive_risk": [],
  "false_negative_risk": [],
  "required_tests_added": []
}
```

## 9. Step 4：Provider failure accounting 决策

Stage 16F.0 将 provider failure accounting 标为 P2。Stage 16F.1 可以选择同步，也可以明确延期，但不能沉默。

需要检查：

```text
DeepSeek / OpenAI provider timeout
empty response
provider exception
retry-only rerun
provider-only rerun denominator
official_prediction_eligible=false 传播
模型语义失败和基础设施失败分离
```

如果 Stage 16F.1 同步该项，必须增加测试证明：

```text
provider timeout 不计为模型 resolved failure。
empty response 结构化进入 provider failure 或 diagnostic。
provider-only rerun 不污染 official prediction eligibility。
```

如果延期，必须生成：

```text
stage16f1_provider_failure_accounting_decision_report.json
```

并写明：

```text
deferred_to_stage = 16F.2 或 16F.3
risk_if_deferred
why_not_blocking_stage16f1
```

## 10. Step 5：同步报告和模块差异收口

完成代码同步或延期决策后，必须生成：

```text
stage16f1_required_sync_item_status.json
stage16f1_module_diff_after_report.json
```

`stage16f1_required_sync_item_status.json` 至少包含：

```json
{
  "schema_version": 1,
  "source_required_sync_items_sha256": "...",
  "items": [
    {
      "sync_item_id": "...",
      "priority": "P1|P2|P3",
      "must_be_addressed_in_stage16f1": true,
      "action_taken": "ported|already-covered|deferred|not-applicable",
      "target_commits_or_files": [],
      "tests": [],
      "blocks_stage16f1_completion": false,
      "defer_reason": null,
      "deferred_to_stage": null
    }
  ]
}
```

其中 `items` 必须覆盖 Stage 16F.0 的全部 `required_sync_items`，包括：

```text
p1_diagnostic_shell_bash_lc_semantics
p1_run_directory_not_model_visible
p1_patch_and_official_prediction_hygiene
p2_provider_failure_accounting
p2_episode_spec_builder_prerequisite
```

如果 `p2_episode_spec_builder_prerequisite` 不在 Stage 16F.1 实施，必须写为：

```text
action_taken = deferred
deferred_to_stage = 16F.2
blocks_stage16f1_completion = false
```

所有 Stage 16F.0 中 `blocks_stage16f1_completion=true` 的 P1 项，在 Stage 16F.1 结束时必须变成：

```text
action_taken = ported 或 already-covered
blocks_stage16f1_completion = false
```

否则 Stage 16F.1 不能通过。

## 11. 需要修改的预期文件范围

Stage 16F.1 预计可能修改：

```text
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/tools/minimal.py
src/repo_harness/workspace/patch_hygiene.py
scripts/pre_verl/build_swebench_official_inputs.py
tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py
tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py
tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py
tests/unit/test_pre_verl_swebench_official_inputs.py
```

如果执行时需要修改 `evaluation.runner`、`rl.runtime`、`ContextBuilder` 或 scaffold 文件，必须先确认该修改不是 Stage 16F.2 的 EpisodeExecutionSpec 工作。若属于入口统一，必须延期。

Stage 16F.1 提交不能包含：

```text
另一个工作树的运行目录
HTML 报告
云服务配置
本机绝对路径
未脱敏日志
训练设计参考资料
Stage 16F.2 入口迁移代码
```

## 12. 验收测试建议

最低本地测试：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py \
  tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py \
  tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py \
  tests/unit/test_pre_verl_swebench_official_inputs.py
```

如果测试文件名在实际仓库中不同，执行 agent 必须先用 `rg --files tests | rg '16b|diagnostic|16e|patch_hygiene|official_inputs|command_policy'` 找到真实路径，并在报告中写明替代命令。

关键回归：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_export.py \
  tests/unit/test_reward.py

PATH=.venv/bin:$PATH python -m compileall -q src scripts/pre_verl

PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness
loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
if loaded:
    raise SystemExit(f"unexpected heavy imports: {loaded}")
print("ordinary_import_ok")
PY
```

RepoHarness core verl import scan：

```bash
rg -n "from repo_harness_verl|import repo_harness_verl|from verl|import verl" \
  src/repo_harness/rl \
  src/repo_harness/workspace \
  src/repo_harness/export \
  src/repo_harness/reward \
  src/repo_harness/tasks \
  src/repo_harness/context \
  scripts/pre_verl
```

如果该扫描有命中，必须解释是否属于既有允许入口。Stage 16F.1 不应新增 core eager verl import。

## 13. 公开 evidence 泄漏扫描

必须扫描：

```text
docs/agentic_RL/repo_harness_verl_workstreams/43-stage-16f-1-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/**/*.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/**/*.jsonl
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/**/*.md
```

不得出现：

```text
本机绝对路径
真实工作树路径
真实私有运行证据目录路径
云服务密钥路径
原始 hidden verifier 内容
原始 gold patch
原始 test patch
官方测试选择器原文
```

允许出现：

```text
runtime-private:<artifact-kind>:<sha256>
相对路径
commit hash
sha256
模块名
测试命令
```

## 14. Acceptance summary

必须生成 `stage16f1_acceptance_summary.json`：

```json
{
  "schema_version": 1,
  "stage": "16F.1",
  "status": "passed|blocked|failed",
  "stage16f1_complete": true,
  "stage16f0_input_status": "passed",
  "sync_performed": true,
  "code_behavior_modified": true,
  "diagnostic_shell_bash_lc_synced": true,
  "run_directory_visibility_guard_preserved": true,
  "patch_hygiene_comparison_completed": true,
  "p1_required_sync_items_remaining": 0,
  "provider_failure_accounting_decision_recorded": true,
  "public_path_leak_scan_passed": true,
  "ready_for_stage16f2": true,
  "blocking_reasons": []
}
```

合法状态语义：

```text
status=passed：
  stage16f1_complete=true
  ready_for_stage16f2=true
  p1_required_sync_items_remaining=0

status=blocked：
  stage16f1_complete=false
  ready_for_stage16f2=false
  blocking_reasons 非空

status=failed：
  stage16f1_complete=false
  ready_for_stage16f2=false
  blocking_reasons 非空
```

## 15. 通过标准

Stage 16F.1 可以通过的最低条件：

1. Stage 16F.0 输入产物存在且 summary 为 `passed`。
2. `diagnostic_shell` 的模型可见 path 在训练工作树中使用显式 `bash -lc` 或等价可审计 bash 入口。
3. Local diagnostic shell 不再依赖不透明 `shell=True`。
4. Docker diagnostic shell 不再使用 `sh -lc`。
5. run directory 和私有证据目录仍不能进入模型可见 diagnostic shell。
6. Stage 16E patch hygiene 与测评工作树 official prediction hygiene 差异已比较，新增规则已同步或明确延期。
7. Stage 16F.0 的 P1 required sync items 全部 `action_taken=ported|already-covered`。
8. P2 provider failure accounting 已同步或写出延期决策。
9. 相关测试和关键回归通过。
10. 公开 evidence 泄漏扫描通过。
11. 没有新增 RepoHarness core 到 `repo_harness_verl` 或 `verl` 的 eager import。

## 16. 进入 Stage 16F.2 的条件

只有 Stage 16F.1 通过后，才能进入 Stage 16F.2。

Stage 16F.2 的重点将是：

```text
定义 EpisodeExecutionSpec / EpisodeExecutionSpecBuilder。
把 run_task(...) 中成熟的 prompt、工具、scaffold、public_environment、verifier plan 构造逻辑抽到中立模块。
让 run_episode(real_episode) 消费同一个共享规格。
```

Stage 16F.1 不能提前实现这些内容，但必须为它提供更干净的 Harness 基线。
