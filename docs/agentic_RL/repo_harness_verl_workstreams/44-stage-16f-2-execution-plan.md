# Stage 16F.2 执行计划：定义共享 EpisodeExecutionSpec

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.2 的目标是把旧测评入口 `run_task(...)` 中已经成熟的任务解析、上下文构造、工具注册、scaffold、公开环境、verifier plan 和反馈策略，抽成一个中立的 `EpisodeExecutionSpec` 规格。后续测评入口和训练入口都应该消费这份规格，而不是各自重新拼接 prompt、工具集合和 verifier 事实。

这一阶段是入口统一的结构前置阶段，不是完整迁移阶段。Stage 16F.2 完成后，应该能够证明：

```text
同一任务和同一 run config
-> EpisodeExecutionSpecBuilder
-> 同一份 initial_messages / raw_prompt
-> 同一份 allowed tools / tool registry
-> 同一份 public_environment_context
-> 同一份 feedback policy
-> 同一份 resolved verifier plan projection
```

同时，`run_episode(real_episode)` 应该具备消费该规格的本地能力，至少在单元测试中证明它不再只能依赖外部手工传入的 `raw_prompt`、默认 `ToolExecutor()`、空 `resolved_verifier_plan` 和固定 `test_feedback_policy=disabled`。

## 2. 前置条件

执行前必须确认：

```text
Stage 16F.0 status=passed
Stage 16F.1 status=passed
Stage 16F.1 commit 已存在
```

当前 Stage 16F.1 提交为：

```text
997d434d feat: sync stage16f diagnostic shell semantics
```

必须读取并使用以下输入：

```text
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_0/stage16f0_run_task_run_episode_gap_report.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/stage16f1_acceptance_summary.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_1/stage16f1_required_sync_item_status.json
```

如果 Stage 16F.1 没有通过，或者 `p2_episode_spec_builder_prerequisite` 没有明确延期到 Stage 16F.2，Stage 16F.2 必须停止。

## 3. 非目标

Stage 16F.2 不做以下事情：

1. 不新增 `run-episode-task` 或 `run-episode-batch` 命令。
2. 不把 `run_task(...)` 重写成 `run_episode(real_episode)` 包装层。
3. 不删除或废弃旧 `run_task(...)`。
4. 不做旧 run directory projection。
5. 不运行 20 到 30 题代表性 harness 诊断。
6. 不运行远端 GPU 训练。
7. 不改变 formal online RL gate，不放宽 token id、log probability、generation record、visibility 或 response span 不变量。
8. 不把外部 API provider 轨迹伪装成可进入 policy loss 的 `route=verl` 样本。

如果某项改动需要 CLI、projection、批量调度、official harness 真实运行或远端模型调用，必须延后到 Stage 16F.3 到 Stage 16F.6。

## 4. 模块归属和导入边界

`EpisodeExecutionSpec` 和 `EpisodeExecutionSpecBuilder` 必须放在中立模块，不能放在只属于测评入口或只属于强化学习入口的模块。

建议新增：

```text
src/repo_harness/execution/__init__.py
src/repo_harness/execution/spec.py
src/repo_harness/execution/builder.py
```

导入边界要求：

```text
repo_harness.execution 不能 import repo_harness_verl。
repo_harness.execution 不能 eager import torch、ray、verl、tensordict。
repo_harness.execution 不能 import repo_harness.evaluation.runner。
repo_harness.rl.runtime 可以消费 EpisodeExecutionSpec。
repo_harness.evaluation.runner 后续可以消费 EpisodeExecutionSpec。
repo_harness.rl.runtime 不能反向依赖 evaluation.runner。
```

如果需要复用 `evaluation.runner` 中已有逻辑，必须先把该逻辑移动或复制到中立模块，再由 `evaluation.runner` 和 `rl.runtime` 共同调用。不能通过从 `execution` 反向 import `evaluation.runner` 来实现。

## 5. 新增核心对象

### 5.1 EpisodeExecutionSpec

建议新增 Pydantic schema：

```text
EpisodeExecutionSpec
EpisodeExecutionSpecTaskFacts
EpisodeExecutionSpecRunConfigFacts
EpisodeExecutionSpecToolFacts
EpisodeExecutionSpecContextFacts
EpisodeExecutionSpecVerifierFacts
EpisodeExecutionSpecFeedbackFacts
EpisodeExecutionSpecBudgetFacts
```

`EpisodeExecutionSpec` 至少包含：

```text
schema_version
spec_id
spec_payload_sha256
task_id
run_id
task_definition_sha256
run_config_sha256
scaffold_id
allowed_tool_names
tool_registry_digest
tool_schema_snapshot_digest 或 tool_schema_snapshot_projection_digest
public_environment_context_digest
initial_messages_digest
raw_prompt_digest
resolved_verifier_plan_digest
test_feedback_policy
feedback_tests_passed_policy
permission_mode
network_policy
max_turns
max_tool_calls
max_test_runs
max_tool_output_chars
run_mode_hint
provider_route_policy
diagnostic_only_reason
```

`spec_payload_sha256` 是对去掉该 digest 字段后的 canonical spec payload 计算得到的摘要；它不能把自身字段再纳入哈希，否则不同实现会出现自引用 digest 歧义。

`initial_messages` 可以保存在 spec 中，但必须经过现有 visibility 检查，不能包含 evaluator-only 信息、本机绝对路径、运行时私有路径、隐藏 verifier 原文、官方测试选择器原文、原始正确补丁或原始测试补丁。

### 5.2 EpisodeExecutionSpecBuilder

`EpisodeExecutionSpecBuilder` 第一版只做本地构造，不负责远端执行。建议提供两个层级：

```text
build_spec_from_loaded_task(...)
build_spec_from_task_path_and_run_config(...)
```

第一版最低要求：

1. 接收已经加载的 task、run config、run workspace、workspace facade、dependency state、resolved verifier plan 和 scaffold。
2. 调用同一个 `ContextBuilder.build_initial_messages(...)` 生成模型首轮上下文。
3. 调用同一个 `resolve_feedback_policy(...)` 和 `resolve_allowed_tools(...)` 生成反馈策略和工具集合。
4. 生成 `tool_registry_for_allowed_tools(...)` 对应的 registry digest。
5. 生成 `build_public_environment_context(...)` 对应的公开环境上下文和 digest。
6. 生成可审计的 spec digest。

如果 builder 第一版不能自己创建 workspace 或 resolved verifier plan，必须把它写成显式输入；不能偷偷回退成空 verifier plan、默认工具集合或默认关闭公开测试反馈。

## 6. `run_episode(real_episode)` 消费 spec 的边界

Stage 16F.2 必须让 real episode 路径具备消费 `EpisodeExecutionSpec` 的能力，但不要求新增 CLI。

推荐实现之一：

```text
RepoHarnessEpisodeRequest 增加轻量字段：
  episode_execution_spec_ref
  episode_execution_spec_sha256
  raw_prompt_source = external | episode_execution_spec

RepoHarnessRuntime.run_episode(...) 或内部 real episode path 接收 runtime-only spec：
  execution_spec: EpisodeExecutionSpec | None
```

另一种可接受实现：

```text
新增中立 helper：
  build_episode_request_from_execution_spec(...)

该 helper 生成 RepoHarnessEpisodeRequest.raw_prompt、task_ref、budgets、visibility policy 和 audit refs。
```

无论采用哪种实现，都必须满足：

1. 如果 request 同时有外部 `raw_prompt` 和 `EpisodeExecutionSpec.initial_messages`，两者 digest 必须一致；不一致时结构化拒绝，不能静默以其中一方为准。
2. real episode 的 `AgentLoop` 初始消息必须来自 spec 或与 spec digest 一致。
3. real episode 的 `ToolExecutor` 必须使用 spec 里的 `allowed_tool_names` 对应 registry，不能继续无条件使用默认 `ToolExecutor()`。
4. real episode 的 `ToolExecutionContext.resolved_verifier_plan` 必须来自 spec，不能继续默认为 `None`。
5. real episode 的 `test_feedback_policy` 和 `feedback_tests_passed_policy` 必须来自 spec，不能继续固定为 `disabled`。
6. 如果 request 携带 `episode_execution_spec_sha256`，该值必须等于实际传入 spec 的 `spec_payload_sha256`；不一致时必须结构化拒绝。
7. 如果 request 与 spec 同时携带任务或运行配置事实，必须校验以下字段一致，或者明确证明 request 是由该 spec 派生：

```text
task_id
run_id
task_ref 或 task_definition_sha256
run_config_ref 或 run_config_sha256
budgets，包括 max_turns、max_tool_calls、max_test_runs、max_tool_output_chars
permission_mode
network_policy
run_mode_hint
allowed_tool_names
tool_registry_digest
resolved_verifier_plan_digest
test_feedback_policy
feedback_tests_passed_policy
```

任何不一致都必须结构化拒绝，不能只依赖 `raw_prompt_digest` 一项绑定。这样可以防止“request 属于任务 B，但 runtime 套用了任务 A 的 prompt、工具、verifier plan 或权限事实”的错误。

8. spec 相关字段只能进入 audit / evidence / runtime metadata，不能进入 `TrainingView.extra_fields`、`AgentLoopOutput.extra_fields` 或 DataProto 非张量 batch，除非该字段已经通过 visibility gate 并且是明确的 batch-safe projection。
9. 完整 `ResolvedVerifierPlan` 如果包含隐藏测试选择器、官方测试选择器或 evaluator-only 细节，只能作为 runtime-private artifact 或运行时对象存在。公开 spec artifact、公开 evidence、`TrainingView`、`AgentLoopOutput` 和 DataProto 只能保存 `resolved_verifier_plan_digest`、不透明引用或 batch-safe projection。

## 7. `run_task(...)` 的处理边界

Stage 16F.2 不要求改写 `run_task(...)` 主流程，但建议做最小接入之一：

```text
方案 A：run_task(...) 暂不消费 spec，但新增 parity fixture，证明 builder 输出和 run_task 当前构造结果一致。
方案 B：run_task(...) 在构造 initial_messages 前调用 builder 的子函数，但仍保持旧控制流。
```

不允许在 Stage 16F.2 直接做：

```text
run_task(...) -> RepoHarnessRuntime.run_episode(...)
run_task(...) 输出 run_episode projection
run_task(...) deprecated warning
```

这些属于 Stage 16F.3 到 Stage 16F.5。

## 8. 需要覆盖的 Stage 16F.0 gap

Stage 16F.2 必须显式关闭或推进这些 gap：

```text
raw_prompt_source
context_builder_participation
tool_executor_registry
resolved_verifier_plan
test_feedback_policy
```

每个 gap 必须在 `stage16f2_gap_closure_report.json` 中记录：

```text
gap_id
previous_run_task_behavior
previous_run_episode_behavior
stage16f2_action
status = closed | partially_closed | deferred
remaining_work
deferred_to_stage
tests
```

`patch_hygiene_facts` 仍可延期到 Stage 16F.4 parity audit，但必须在报告中明确说明 Stage 16E / Stage 16F.1 已经建立 patch hygiene 基线。

## 9. 预期文件范围

预计新增或修改：

```text
src/repo_harness/execution/__init__.py
src/repo_harness/execution/spec.py
src/repo_harness/execution/builder.py
src/repo_harness/rl/episode.py
src/repo_harness/rl/runtime.py
tests/unit/test_repo_harness_stage16f2_episode_execution_spec.py
tests/unit/test_repo_harness_stage16f2_real_episode_spec_consumption.py
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_2/*.json
```

可能修改但需谨慎：

```text
src/repo_harness/context/builder.py
src/repo_harness/scaffolds/*
src/repo_harness/tools/*
src/repo_harness/tasks/public_environment.py
```

如果执行时需要修改 `src/repo_harness/evaluation/runner.py`，必须明确说明该修改只是抽取共享构造逻辑，不是把 `run_task(...)` 改成 `run_episode(...)` 包装层。

不应修改：

```text
src/repo_harness_verl/*
reference/verl/*
远端训练脚本
Stage 14 / Stage 15 fully async trainer path
```

除非只是补充不改变行为的导入边界测试。

## 10. 测试计划

新增测试建议：

```text
tests/unit/test_repo_harness_stage16f2_episode_execution_spec.py
tests/unit/test_repo_harness_stage16f2_real_episode_spec_consumption.py
```

必须覆盖：

1. `EpisodeExecutionSpecBuilder` 生成的 `initial_messages` 与直接调用 `ContextBuilder` 的结果 digest 一致。
2. `public_environment_context_digest` 写入 spec，且 public environment payload 不含 evaluator-only 信息。
3. `allowed_tool_names` 与 `tool_registry_for_allowed_tools(...)` 一致。
4. scaffold 为 `patch_focused_react_diagnostic_shell` 时，spec 允许 `diagnostic_shell`；普通 scaffold 不允许。
5. spec 中的 tool schema digest 和实际 ToolExecutor registry digest 一致。
6. spec 中的 `test_feedback_policy` 与 `resolve_feedback_policy(...)` 一致。
7. spec 中的 `resolved_verifier_plan_digest` 与输入 verifier plan 一致。
8. real episode 消费 spec 后，`ToolExecutionContext.resolved_verifier_plan` 不再是 `None`。
9. real episode 消费 spec 后，`test_feedback_policy` 不再被固定成 `disabled`，而是来自 spec。
10. real episode 消费 spec 后，`ToolExecutor` 使用 spec 的 allowed tool registry，不再默认开放不一致工具。
11. request 外部 `raw_prompt` 与 spec 初始消息 digest 不一致时结构化拒绝。
12. request 的 `task_id` 与 spec 的 `task_id` 不一致时结构化拒绝。
13. request 的 budgets、permission 或 network policy 与 spec 不一致时结构化拒绝。
14. request 声称的 `episode_execution_spec_sha256` 与实际 spec 的 `spec_payload_sha256` 不一致时结构化拒绝。
15. spec 的完整 verifier plan 不能进入公开 evidence、`TrainingView`、`AgentLoopOutput` 或 DataProto；只允许 digest、不透明引用或 batch-safe projection。
16. provider route 生成的 spec 必须默认 `invalid_for_online_rl=true` 或有明确 diagnostic / SFT 候选原因。
17. `EpisodeExecutionSpec` 和 builder 普通导入不加载 `torch`、`ray`、`tensordict`、`verl`。
18. `repo_harness.execution` 不 import `repo_harness_verl`，不 import `repo_harness.evaluation.runner`。

建议回归：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_context_builder.py \
  tests/unit/test_repo_harness_stage16c_public_environment_context.py \
  tests/unit/test_repo_harness_stage16c_visibility.py \
  tests/unit/test_repo_harness_stage16c_scaffold_prompt.py \
  tests/unit/test_test_feedback_policy.py \
  tests/unit/test_pre_verl_run_config_preflight.py \
  tests/unit/test_repo_harness_rl_stage11_5_real_episode_runtime.py
```

Stage 13 到 Stage 15 的训练链路关键回归建议至少保留：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_verl_stage13_2_fully_async_bridge.py \
  tests/unit/test_repo_harness_verl_stage13_3a_async_producer.py \
  tests/unit/test_repo_harness_rl_stage13_1_async_facade.py
```

导入边界：

```bash
PYTHONPATH=src PATH=.venv/bin:$PATH python - <<'PY'
import sys
import repo_harness
import repo_harness.execution
loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
if loaded:
    raise SystemExit(f"unexpected heavy imports: {loaded}")
print("ordinary_import_ok")
PY

python - <<'PY'
from pathlib import Path

root = Path("src/repo_harness/execution")
forbidden = (
    "repo_harness_verl",
    "from verl",
    "import verl",
    "repo_harness.evaluation.runner",
)
matches = []
for path in sorted(root.rglob("*.py")):
    text = path.read_text()
    for marker in forbidden:
        if marker in text:
            matches.append((str(path), marker))
if matches:
    for path, marker in matches:
        print(f"{path}: forbidden import marker {marker!r}")
    raise SystemExit(1)
print("repo_harness.execution import boundary ok")
PY
```

## 11. 公开报告

建议新增：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_2/
```

公开报告建议包括：

```text
stage16f2_spec_schema_report.json
stage16f2_builder_boundary_report.json
stage16f2_gap_closure_report.json
stage16f2_run_episode_consumption_report.json
stage16f2_import_boundary_report.json
stage16f2_visibility_report.json
stage16f2_test_report.json
stage16f2_acceptance_summary.json
```

公开报告只能记录：

```text
相对路径
sha256
schema version
字段名
测试命令
聚合结果
runtime-private:<artifact-kind>:<sha256> 不透明引用
```

公开报告不能记录本机绝对路径、真实工作树路径、真实运行目录路径、隐藏 verifier 原文、官方测试选择器原文、原始正确补丁、原始测试补丁、未脱敏模型响应或私有云服务配置。

## 12. Acceptance summary

必须生成 `stage16f2_acceptance_summary.json`：

```json
{
  "schema_version": 1,
  "stage": "16F.2",
  "status": "passed|blocked|failed",
  "stage16f2_complete": true,
  "stage16f1_input_status": "passed",
  "episode_execution_spec_schema_added": true,
  "episode_execution_spec_builder_added": true,
  "builder_import_boundary_passed": true,
  "context_builder_digest_parity_passed": true,
  "tool_registry_digest_parity_passed": true,
  "public_environment_digest_present": true,
  "resolved_verifier_plan_digest_present": true,
  "run_episode_consumes_spec": true,
  "raw_prompt_mismatch_rejected": true,
  "run_task_rewrite_performed": false,
  "run_episode_task_cli_added": false,
  "public_path_leak_scan_passed": true,
  "ready_for_stage16f3": true,
  "blocking_reasons": []
}
```

合法状态语义：

```text
status=passed：
  stage16f2_complete=true
  ready_for_stage16f3=true

status=blocked 或 failed：
  stage16f2_complete=false
  ready_for_stage16f3=false
  blocking_reasons 非空
```

## 13. 通过标准

Stage 16F.2 可以通过的最低条件：

1. 新增中立 `EpisodeExecutionSpec` schema 和 builder。
2. builder 不依赖 `repo_harness_verl`、`verl`、`torch`、`ray`、`tensordict` 或 `evaluation.runner`。
3. builder 生成的 initial messages 与 `ContextBuilder` 直接输出一致。
4. builder 生成的 allowed tools、tool registry digest、public environment digest、feedback policy 和 verifier plan digest 可审计。
5. real episode 能消费 spec，且不再只能依赖外部手写 raw prompt、默认 ToolExecutor、空 verifier plan 和固定 disabled feedback policy。
6. raw prompt 与 spec 不一致时结构化拒绝。
7. provider route 样本仍不能进入 formal online RL policy loss。
8. 相关本地测试和关键回归通过。
9. 公开 evidence 泄漏扫描通过。
10. 没有提前新增 CLI、projection 或 `run_task(...)` 到 `run_episode(...)` 的迁移。

## 14. 进入 Stage 16F.3 的条件

只有 Stage 16F.2 通过后，才能进入 Stage 16F.3。

Stage 16F.3 的重点将是：

```text
新增 run-episode-task / run-episode-batch 实验性 CLI。
让 CLI 读取现有 task definition 和 run config。
构造 EpisodeExecutionSpec。
调用 RepoHarnessRuntime.run_episode(real_episode)。
写出旧评测工具可消费的 run directory projection。
```

Stage 16F.2 不应提前实现这些 CLI 和 projection，但必须让 Stage 16F.3 有一个可复用、可审计的共享 episode 规格。
