# Stage 16F.5 执行计划：旧 `run_task(...)` 降级策略和防误用边界

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.5 的目标不是继续扩大旧 `run_task(...)`，也不是立刻把旧入口重写成 `run_episode(real_episode)` 的包装层。本阶段的目标是把旧 `run_task(...)` 明确降级为 legacy compatibility entrypoint，同时建立机器可检查的防误用边界：

```text
新的测评、训练数据准备、Stage 16.5 代表性诊断和 Stage 17 数据冻结：
  默认使用 repo-harness run-episode-task

旧 run_task(...)：
  保留给历史回归、旧 acceptance evidence、旧导出兼容、对照实验和回滚路径
```

Stage 16F.4 已经证明在固定三例小规模样本上，旧 `run_task(...)` 和新 `run-episode-task` 的关键公开投影语义可以对齐。Stage 16F.5 接下来要做的是把这个结论固化到工具和 evidence 里，避免后续执行 agent、评测脚本或训练数据构建脚本继续把旧入口当作新的 canonical Harness 入口。

本阶段完成后，应该能够回答：

```text
一个 run directory 是由 legacy run_task 产生，还是由 canonical run_episode 入口产生？
这个 run 是否可以作为 Stage 17 之后的 canonical training data source？
如果一个流程仍然读取旧 run_task 产物，它是否明确知道自己处在 compatibility mode？
```

## 2. 前置条件

执行前必须确认：

```text
Stage 16F.0 status=passed
Stage 16F.1 status=passed
Stage 16F.2 status=passed
Stage 16F.3 status=passed
Stage 16F.4 status=passed
Stage 16F.4 commit 已存在
```

当前 Stage 16F.4 提交为：

```text
11118db4 feat: add stage16f4 run episode parity audit
```

必须读取并参考：

```text
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/46-stage-16f-4-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_run_task_run_episode_parity_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_4/stage16f4_blocking_differences.json
```

如果 Stage 16F.4 evidence 不能通过 `inspect-stage16f4-parity --assert-complete`，本阶段必须停止。

## 3. 非目标

Stage 16F.5 不做以下事情：

1. 不删除 `repo-harness run-task` 命令。
2. 不破坏现有 `run-task`、`run-batch`、`run-experiment`、旧 export、旧 acceptance 的兼容性。
3. 不要求 `run_task(...)` 在本阶段内部转调 `run_episode(real_episode)`。
4. 不把历史 `run_task(...)` run directory 批量迁移成 `run_episode` run directory。
5. 不运行 20 到 30 题代表性诊断扩展。
6. 不运行远端 GPU 训练。
7. 不把外部 API、mock 或 replay 轨迹伪装成 formal online RL policy-loss 样本。

如果执行过程中发现必须重写旧 `run_task(...)` 主流程才能完成本阶段，应停止并把问题记录为后续独立迁移阶段，而不是在 Stage 16F.5 中顺手大改。

## 4. 核心设计决策

### 4.1 旧入口先降级，不立即重写

Stage 16F.5 的默认决策是：

```text
run_task(...) 保留。
run_task(...) 标记为 legacy compatibility path。
run_task(...) 产物默认不是新的 canonical training data source。
run-episode-task 成为后续新测评和训练数据准备的默认入口。
```

也就是说，本阶段不是计划文档中“第三步：让 `run_task(...)` 在内部构造 `EpisodeExecutionSpec`，并尽可能转调 `run_episode(real_episode)`”的最终实现。那一步仍然可以作为后续重构目标，但不作为当前阶段的硬要求。

原因是旧 `run_task(...)` 仍然承载很多历史职责：

```text
旧 acceptance evidence
旧 V3 / V4 / V5 回归
旧 export 兼容
已有 SWE-Bench 诊断脚本
run-batch / run-experiment 历史控制流
```

直接重写它会扩大风险，反而可能阻碍 Stage 16.5 和 Stage 17。

### 4.2 新训练数据事实来源默认必须是 canonical entrypoint

Stage 16.5、Stage 17 和后续训练数据准备工具默认应读取：

```text
repo-harness run-episode-task 产物
或者后续等价的 run_episode batch / experiment 入口产物
```

如果某个工具读取旧 `run_task(...)` 产物，必须显式记录：

```text
legacy_compatibility_mode=true
canonical_entrypoint_required_for_new_training=true
formal_training_data_candidate=false
recommended_replacement=repo-harness run-episode-task
```

这不是说旧 `run_task(...)` 产物永远不能用于诊断或历史导出，而是说它不能再被默认当作 Stage 17 之后的新训练数据主事实来源。

## 5. 实现范围

### 5.1 新增 legacy entrypoint metadata

旧 `run_task(...)` 每次运行时，必须写入一个机器可读的 legacy metadata 文件，建议为：

```text
legacy_entrypoint_report.json
```

最小字段：

```json
{
  "schema_version": "repo_harness_stage16f5_legacy_entrypoint_report_v0",
  "entrypoint": "run_task",
  "entrypoint_classification": "legacy_compatibility",
  "canonical_entrypoint": "run_episode_task",
  "recommended_replacement": "repo-harness run-episode-task",
  "legacy_run_task_still_supported": true,
  "legacy_run_task_internal_run_episode_delegate": false,
  "formal_online_rl_eligible": false,
  "policy_loss_candidate": false,
  "formal_training_data_candidate": false,
  "new_training_data_default_candidate": false,
  "new_training_data_default_entrypoint": false,
  "training_data_eligibility_asserted": false,
  "historical_export_compatibility_allowed": true,
  "compatibility_use_cases": [
    "historical_acceptance",
    "legacy_export",
    "regression_comparison",
    "rollback_path"
  ]
}
```

该文件不能包含本机绝对路径、运行时私有路径、隐藏 verifier 信息、gold patch 内容或 provider secret。

### 5.2 新入口也要写 canonical entrypoint metadata

`run-episode-task` 产物中也应该写入对应的 canonical metadata，建议为：

```text
entrypoint_report.json
```

最小字段：

```json
{
  "schema_version": "repo_harness_stage16f5_entrypoint_report_v0",
  "entrypoint": "run_episode_task",
  "entrypoint_classification": "canonical_run_episode_task",
  "canonical_entrypoint": "run_episode_task",
  "episode_execution_spec_sha256": "...",
  "compat_projection_complete": true,
  "formal_online_rl_eligible": false,
  "policy_loss_candidate": false,
  "new_training_data_default_entrypoint": true,
  "training_data_eligibility_asserted": false
}
```

注意：这里的 `new_training_data_default_entrypoint=true` 只表示它是新的默认入口产物，不表示样本已经满足 SFT、preference、reward 或 online RL 的全部训练资格。实际训练资格仍然必须经过 visibility、patch hygiene、reward boundary、verifier summary、token provenance、generation records 和 formal gate。

如果实现中为了兼容已有报告临时保留旧字段名 `new_training_data_default_candidate`，该字段只能作为“默认入口”的兼容别名，不能被任何 export、registry、reward builder、preference selector 或 policy-loss selector 当作训练资格。新的机器检查应优先使用：

```text
new_training_data_default_entrypoint
training_data_eligibility_asserted
```

`formal_online_rl_eligible` 和 `policy_loss_candidate` 不能在实现中硬编码。它们必须来自 `provider_route_qualification.json`、formal gate 或等价训练资格判定结果。第一版 smoke 使用 `mock` 或 `replay` route 时，这两个字段应为 `false`；后续如果出现真实 `route=verl` 样本，metadata 必须保留真实 gate 结果，而不是因为 Stage 16F.5 的示例字段把它错误降级。

### 5.3 不改变旧导出默认行为，但新增新阶段检查

本阶段不应该让旧导出突然失败。旧 export 仍然要兼容历史 run directory。

但是新建 Stage 16F.5 inspector 时，必须能区分：

```text
legacy run_task 产物
canonical run_episode_task 产物
历史兼容导出
新训练数据默认入口
```

建议新增：

```text
inspect-stage16f5-entrypoint-policy
```

它读取一个 evidence 目录或一组 run directory，检查：

```text
legacy_run_task_report_present
canonical_run_episode_task_report_present
legacy_entrypoint_training_candidate_blocked
canonical_entrypoint_projection_bound
non_verl_policy_loss_candidate_count
public_path_leak_scan_passed
```

### 5.4 旧 run_task 的命令行提醒

可以在 `repo-harness run-task` 的命令行输出中增加一条温和提醒，但不能破坏依赖 stdout 的旧脚本。

建议第一版优先写入 run directory metadata，不强制向 stdout / stderr 输出 warning。如果要输出，必须满足：

```text
不改变原有“任务运行完成：...”这一行。
不让旧脚本误判失败。
可以通过 structured report 读取，不依赖人读终端。
```

### 5.5 run-batch 和 run-experiment 的继承语义

如果 `run-batch` 或 `run-experiment` 内部仍调用旧 `run_task(...)`，它们不需要在本阶段迁移，但必须继承 legacy metadata。

也就是说，批量或实验运行的每个子 run directory 里都应能看到：

```text
entrypoint_classification=legacy_compatibility
canonical_entrypoint=run_episode_task
```

本阶段不要求新增 `run-episode-batch`，但必须在 evidence 中记录：

```text
run_episode_batch_status=deferred_to_later_stage
```

`run-batch` 和 `run-experiment` 不能只在计划中声明兼容。当前代码中两条路径都可能通过旧 `run_task(...)` 产生子 run，因此 Stage 16F.5 的实现验收必须同时覆盖两条路径：

```text
1. 运行一个最小 run-batch smoke，并证明每个子 run directory 都写出 legacy_entrypoint_report.json。
2. 运行一个最小 run-experiment smoke，并证明每个子 run directory 都写出 legacy_entrypoint_report.json。
```

如果某条路径确实不调用旧 `run_task(...)`，可以记录 `not_applicable`，但必须由代码路径检查或测试证明。不能只测试其中一条路径，然后把另一条路径写成 covered。不能用笼统的 `deferred_with_reason` 让 `run-batch` 或 `run-experiment` 在没有继承测试或代码路径证明的情况下通过。

## 6. 需要新增或修改的文件

预计涉及：

```text
src/repo_harness/evaluation/runner.py
src/repo_harness/evaluation/episode_runner.py
src/repo_harness/evaluation/entrypoint_policy.py
src/repo_harness/cli/main.py
tests/unit/test_repo_harness_stage16f5_entrypoint_policy.py
tests/unit/test_repo_harness_stage16f5_legacy_run_task_metadata.py
tests/unit/test_repo_harness_stage16f5_run_episode_task_metadata.py
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_entrypoint_policy_report.json
```

如果实现时发现不需要新增 `entrypoint_policy.py`，可以把逻辑放在现有 evaluation 模块中，但必须保持：

```text
不 import repo_harness_verl
不 eager import torch / ray / tensordict / verl
```

## 7. Evidence 要求

必须生成公开安全 evidence：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_entrypoint_policy_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_legacy_run_task_sample_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_run_episode_task_sample_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_test_report.json
```

`stage16f5_acceptance_summary.json` 最小字段：

```json
{
  "schema_version": "repo_harness_stage16f5_acceptance_summary_v0",
  "status": "passed",
  "stage16f5_complete": true,
  "ready_for_stage16_5": true,
  "stage16f4_input_status": "passed",
  "legacy_run_task_still_supported": true,
  "legacy_run_task_internal_run_episode_delegate": false,
  "legacy_run_task_training_candidate_blocked": true,
  "legacy_formal_online_rl_eligible_count": 0,
  "legacy_policy_loss_candidate_count": 0,
  "legacy_new_training_data_default_candidate_count": 0,
  "legacy_new_training_data_default_entrypoint_count": 0,
  "legacy_formal_training_data_candidate_count": 0,
  "canonical_run_episode_task_default_for_new_evaluation": true,
  "run_episode_task_projection_binding_required": true,
  "historical_export_compatibility_preserved": true,
  "run_batch_legacy_metadata_inherited": true,
  "run_experiment_legacy_metadata_status": "covered",
  "public_path_leak_scan_passed": true,
  "blocking_reason_count": 0
}
```

如果 `run-experiment` 被判定为 `not_applicable`，summary 必须额外写明：

```text
run_experiment_legacy_metadata_status="not_applicable"
run_experiment_not_applicable_reason
run_experiment_code_path_checked=true
```

除此之外，`covered_or_deferred_with_reason` 不能作为通过状态。

公开 evidence 不能包含：

```text
本机绝对路径
workspace 真实路径
run directory 真实路径
runtime_private 真实路径
hidden verifier 原文
gold patch 内容
provider secret
raw patch audit 字段
```

如果需要引用运行时私有 artifact，只能使用：

```text
runtime-private:<artifact-kind>:<sha256>
```

不能使用真实路径。

## 8. 验收标准

Stage 16F.5 通过必须满足：

```text
1. run_task(...) 仍能完成至少一个旧入口 smoke。
2. run_task(...) run directory 写出 legacy_entrypoint_report.json。
3. legacy_entrypoint_report.json 明确 entrypoint_classification=legacy_compatibility。
4. legacy_entrypoint_report.json 明确 new_training_data_default_candidate=false。
4a. legacy_entrypoint_report.json 明确 new_training_data_default_entrypoint=false。
4b. legacy_entrypoint_report.json 明确 formal_training_data_candidate=false。
4c. legacy_entrypoint_report.json 明确 training_data_eligibility_asserted=false。
5. run_episode_task 仍能完成至少一个 canonical entry smoke。
6. run_episode_task 产物写出 canonical entrypoint report。
7. run_episode_task projection validator 仍然通过。
8. inspect-stage16f5-entrypoint-policy --assert-complete 通过。
9. 旧 export / reward / patch hygiene 关键回归不被破坏。
10. 普通 import 不加载 torch、ray、tensordict、verl。
11. run-batch 或 run-experiment 的 legacy metadata 继承已被 smoke 测试覆盖；如果某路径不适用，必须由代码路径检查证明 `not_applicable`。
12. run-batch 和 run-experiment 两条路径都必须各自被 smoke 测试或代码路径检查覆盖，不能只覆盖其中一条。
```

不允许出现：

```text
legacy run_task 被标记为 formal online RL eligible。
legacy run_task 被标记为 policy loss candidate。
legacy run_task 被标记为 formal training data candidate。
legacy run_task 被标记为 new training data default candidate。
legacy run_task 被标记为 new training data default entrypoint。
legacy run_task 缺少 formal_training_data_candidate 字段却被 inspector 静默当作 false。
run_episode_task 缺少 compat_projection binding 却被标记为 canonical complete。
公开 evidence 泄漏本机路径或 runtime-private 真实路径。
```

## 9. 测试计划

新增测试建议：

```bash
PATH=.venv/bin:$PATH PYTHONPATH=src python -m pytest -q \
  tests/unit/test_repo_harness_stage16f5_entrypoint_policy.py \
  tests/unit/test_repo_harness_stage16f5_legacy_run_task_metadata.py \
  tests/unit/test_repo_harness_stage16f5_run_episode_task_metadata.py \
  tests/unit/test_repo_harness_stage16f5_batch_experiment_inheritance.py
```

新增测试必须包含以下负例：

```text
篡改 legacy_entrypoint_report.formal_online_rl_eligible=true，inspector 必须失败。
篡改 legacy_entrypoint_report.policy_loss_candidate=true，inspector 必须失败。
篡改 legacy_entrypoint_report.new_training_data_default_candidate=true，inspector 必须失败。
篡改 legacy_entrypoint_report.new_training_data_default_entrypoint=true，inspector 必须失败。
篡改 legacy_entrypoint_report.formal_training_data_candidate=true，inspector 必须失败。
删除 formal_training_data_candidate 字段，inspector 必须失败，不能静默按 false 处理。
删除 run-batch 或 run-experiment 子 run 的 legacy metadata，inspector 必须失败，除非该路径被证明为 not_applicable。
```

关键回归：

```bash
PATH=.venv/bin:$PATH PYTHONPATH=src python -m pytest -q \
  tests/unit/test_repo_harness_stage16f4_parity_report.py \
  tests/unit/test_repo_harness_stage16f4_parity_cli.py \
  tests/unit/test_repo_harness_stage16f4_projection_binding.py \
  tests/unit/test_repo_harness_stage16f3_run_episode_task_cli.py \
  tests/unit/test_repo_harness_stage16f3_run_episode_projection.py \
  tests/unit/test_repo_harness_stage16e_patch_hygiene_policy.py \
  tests/unit/test_export.py
```

导入边界：

```bash
PYTHONDONTWRITEBYTECODE=1 PATH=.venv/bin:$PATH PYTHONPATH=src python - <<'PY'
import sys
import repo_harness
import repo_harness.execution
loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
if loaded:
    raise SystemExit(f"unexpected heavy imports: {loaded}")
print("ordinary_import_ok", loaded)
PY
```

格式和公开 evidence 检查：

```bash
git diff --check -- \
  docs/agentic_RL/repo_harness_verl_workstreams/47-stage-16f-5-execution-plan.md \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5 \
  src/repo_harness/evaluation \
  src/repo_harness/cli/main.py \
  tests/unit/test_repo_harness_stage16f5_entrypoint_policy.py \
  tests/unit/test_repo_harness_stage16f5_legacy_run_task_metadata.py \
  tests/unit/test_repo_harness_stage16f5_run_episode_task_metadata.py \
  tests/unit/test_repo_harness_stage16f5_batch_experiment_inheritance.py
```

## 10. 与 Stage 16.5 和 Stage 17 的关系

Stage 16F.5 通过后：

```text
Stage 16.5 的 20 到 30 题代表性 harness 诊断应默认使用 run-episode-task。
Stage 17 的数据 registry 和训练轨迹准备应默认读取 run_episode 入口产物。
旧 run_task 可以继续用于历史复验和 parity 对照，但不能作为新训练数据主入口。
```

如果某个后续工具仍然必须读取旧 `run_task(...)`，它必须在自己的 evidence 中解释：

```text
为什么不能使用 run-episode-task？
读取的是历史兼容数据还是新训练候选数据？
是否已经阻止该样本进入 formal online RL / policy loss？
是否存在等价的 run_episode projection？
```

## 11. 后续阶段预留

Stage 16F.5 不是最终迁移终点。后续可以再单独设计：

```text
Stage 16F.6：run-episode-batch / run-episode-experiment。
Stage 16F.7：旧 run_task 内部转调 run_episode 的可选重构。
Stage 16F.8：旧 run_task deprecation warning 和文档迁移。
```

这些后续阶段必须建立在 Stage 16.5 代表性诊断和 Stage 17 数据准备需求之上，不能为了形式上的入口统一而破坏当前已经稳定的历史回归链路。

## 12. 完成标准

本阶段完成时必须能清楚说明：

```text
旧 run_task 还存在，但已经不是新的 canonical training / evaluation source。
新测评和训练数据准备默认使用 run-episode-task。
旧 run_task 产物带有机器可读 legacy metadata。
run-episode-task 产物带有机器可读 canonical metadata。
inspector 能拒绝 legacy run_task 被误标为新训练默认候选的情况。
历史兼容路径没有被破坏。
```
