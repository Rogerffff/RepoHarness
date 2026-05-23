# Stage 16C 执行计划：公开环境入口和模型行为提示

本文是 Stage 16C 的具体执行计划。它承接
[post_stage15_training_infra_stage_plan.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md)
中 Stage 16C 的高层路线，并建立在 Stage 16A 的安全最小 `execute_bash`、
Stage 16B 的 `diagnostic_shell` 生命周期，以及 Stage 16B.5 的远端
Docker-capable 训练执行后端验收已经完成的基础上。

Stage 16C 的核心目标不是继续放宽 shell，而是把“模型应该如何理解当前公开工作环境”
这件事变成可审计、可测试、可复现的基础设施。真实软件工程模型在 SWE 任务里经常会猜测：

```text
仓库路径是不是 /workspace 或 /testbed
应该运行什么测试命令
是否需要 source conda activate
是否需要 pip install -e .
应该从哪里读失败测试
是否能使用隐藏的 FAIL_TO_PASS / PASS_TO_PASS selector
```

这些猜测会造成大量无效动作，也可能诱导模型碰到 Stage 16A、Stage 16B 和 Stage 16B.5 刚刚封住的边界。
Stage 16C 要做的是：给模型一份安全的、公开的、足够具体的环境说明，让它优先使用结构化工具和公开测试入口，而不是用 shell 盲猜。

## 1. 阶段目标

Stage 16C 必须完成下面几件事：

1. 新增 `PublicEnvironmentContext` 或等价 runtime-only builder。
   这个 builder 从任务、workspace、verifier、scaffold 和 runtime 配置中提取模型可见的公开环境事实。
2. 把公开环境事实注入模型提示词或 scaffold 上下文，明确告诉模型：
   - 当前仓库的公开工作目录语义。
   - 应该使用 workspace-relative 路径。
   - 读文件、搜索、编辑、查看补丁、运行公开测试分别应该使用哪些工具。
   - 公开测试入口是什么，是否可用，输出是什么级别。
   - 依赖是否已经预置，模型是否允许自己安装依赖。
   - `diagnostic_shell` 是否可用，以及它和 `execute_bash`、结构化工具的区别。
3. 为公开测试入口建立更清晰的工具和提示语义。
   当前 `run_tests` 已经可以在 `public_only` 或 `structured_public_feedback`
   下调用 `run_feedback_public(...)`。Stage 16C 需要决定第一版是：
   - 保留 `run_tests`，但把模型可见描述改成“公开测试入口或当前配置的安全反馈入口”；
   - 或新增 `run_public_tests` 作为更明确的模型可见工具名，再将它路由到公开反馈路径。
4. 防止公开环境说明泄漏 evaluator-only 信息。
   公开环境上下文不能包含 `FAIL_TO_PASS`、`PASS_TO_PASS`、gold patch、test patch、
   hidden verifier、official verifier 结果、official selector、reward metadata、run directory
   真实路径或 runtime-private artifact 路径。
5. 新增 prompt/scaffold 对照测试，证明模型可见提示不再鼓励猜测 `/workspace`、
   `/repo-harness-run`、conda 路径、隐藏测试 selector 或无效公开测试入口。
6. 生成 Stage 16C 本地 evidence，记录公开环境上下文、提示词泄漏扫描、公开测试路由和
   scaffold 对照结果。

## 2. 非目标

Stage 16C 不做下面这些事情：

- 不放宽 Stage 16A 的 `execute_bash` allowlist。
- 不扩大 Stage 16B 的 `diagnostic_shell` 权限，也不放宽 Stage 16B.5 的 remote Docker-capable backend 安全 profile。
- 不把完整产品态 Bash 重新放入正式训练主路径。
- 不实现 official verifier、gold patch healthcheck 或 no-op healthcheck。它们属于 Stage 16D。
- 不实现 patch hygiene、test-only patch 检测或训练目标清洁度。它们属于 Stage 16E。
- 不执行 20 到 30 题代表性诊断扩展。它属于 Stage 16.5。
- 不修改 `reference/verl`。
- 不要求远端 GPU。

## 3. 设计原则

### 3.1 公开环境事实只能来自可信 runtime

`PublicEnvironmentContextBuilder` 不能从模型输出、tool observation 或 command output 中推导公开环境入口。
它必须从下面这些可信来源读取事实：

```text
task schema
resolved verifier plan
run config
scaffold definition
workspace adapter capability facts
test_feedback_policy
diagnostic_shell enablement facts
dependency environment facts
```

如果这些来源缺失或互相矛盾，builder 必须 fail closed。例如：

```text
public_test_entry_status = unavailable
public_test_unavailable_reason = missing_public_feedback_plan
dependency_install_policy = not_model_managed
```

不能为了给模型“看起来完整”的提示而编造命令。

### 3.2 模型看到的是公开 workspace 语义，不是宿主机路径

模型提示中可以说明：

```text
Use workspace-relative paths.
The repository root is the default working directory for structured tools.
Use read_file, grep, list_files or glob_files for inspection.
Use edit_file for source changes.
Use git_diff before the final answer.
Use run_tests or run_public_tests for the configured public test feedback.
```

模型提示中不能出现：

```text
/Users/...
/private/...
/workspace/RepoHarness/...
/repo-harness-run
runs/.../runtime_private
.repo_harness_runtime
.repo_harness_env_overlay
Docker volume mount path
Vast.ai workspace path
```

如果需要给模型一个“工作目录”的概念，第一版建议使用语义化名称，例如：

```text
repository root
episode workspace
current repository workspace
```

而不是绝对路径。

### 3.3 公开测试入口不等于 hidden verifier

Stage 16C 允许模型运行公开测试或公开反馈，但必须严格区分：

```text
public feedback:
  可进入模型观察，不能包含 hidden selector 或官方结果。

hidden final verifier:
  只能用于最终 verifier / reward boundary，不能在中间工具结果中暴露给模型。

official verifier / gold patch healthcheck:
  Stage 16D 的范围，Stage 16C 不应提前暴露。
```

因此：

- `test_feedback_policy=public_only` 时，模型只能看到公开状态和有限摘要。
- `test_feedback_policy=structured_public_feedback` 时，模型只能看到结构化公开摘要。
- `test_feedback_policy=oracle_hidden_feedback` 不能被 Stage 16C 自动当成公开测试入口。
- `test_feedback_policy=disabled` 时，公开测试入口应明确不可用，不能伪装成可用。

### 3.4 结构化工具优先

Stage 16C 的提示词必须延续 Claude Code 式工具分工：

```text
读文件：read_file
搜索：grep / list_files / glob_files
编辑：edit_file
查看补丁：git_diff
公开测试：run_tests 或 run_public_tests
复杂同题诊断：diagnostic_shell，仅在显式启用时使用
安全最小 shell：execute_bash，仅用于 Stage 16A allowlist 内命令
```

这里的 `grep` 指 RepoHarness 模型可见的结构化搜索工具或等价 harness-owned 搜索入口，
不是 `execute_bash` 中裸执行的 shell `grep` 命令。Stage 16C 的 prompt 和工具说明必须避免让模型误以为
应该通过 `execute_bash` 组合 `grep -R`、`find`、`cat` 或 Python 文件读取来替代结构化工具。

提示词不能暗示模型应该用 `cat`、`sed`、`find`、`python open(...)`、`pip install`
或 `source conda activate` 来完成默认动作。

## 4. 建议模块归属

### 4.1 新增公开环境上下文模型

建议新增：

```text
src/repo_harness/tasks/public_environment.py
```

第一版可以包含：

```python
class PublicTestEntry(BaseModel):
    status: Literal["available", "unavailable", "disabled"]
    tool_name: Literal["run_tests", "run_public_tests"] | None
    feedback_policy: str
    model_visible_summary: str
    command_template_label: str | None
    hidden_feedback_visible: bool = False

class PublicEnvironmentContext(BaseModel):
    context_version: str
    workspace_semantics: str
    default_cwd_label: str
    path_policy_summary: str
    preferred_tool_order: list[str]
    public_test_entry: PublicTestEntry
    dependency_policy_summary: str
    diagnostic_shell_summary: str
    forbidden_environment_guess_categories: list[str]
    model_visible_prompt_block: str
    context_digest: str
```

字段可以按现有 schema 风格调整，但必须保留下面几类事实：

```text
workspace 语义
默认路径说明
公开测试入口可用性
依赖安装策略
工具分工
禁止猜测或禁止访问的环境类别
上下文 digest
```

`command_template_label` 只能是模型可见安全标签或预定义枚举，例如
`configured_public_feedback`、`structured_public_feedback` 或 `public_tests_unavailable`。
它不能携带原始测试命令、`pytest -k ...` selector、绝对路径、隐藏 verifier 名称、
official verifier 名称、`FAIL_TO_PASS`、`PASS_TO_PASS` 或其他 evaluator-only 标记。

注意：`forbidden_environment_guess_categories` 只能使用类别化、语义化表述，例如
`host_absolute_paths`、`non_public_runtime_artifacts`、`non_public_evaluation_materials`、
`ad_hoc_dependency_installation`。它不能直接携带 `/workspace`、`/repo-harness-run`、
conda 路径、宿主机路径或隐藏 artifact 文件名。具体字符串只允许出现在
`stage16c_prompt_leak_scan_report.json` 这类审计报告的检测规则或计数中，不能进入
模型可见 prompt、tool schema、TrainingView、DataProto 或 SFT export。

### 4.2 Builder 入口

建议提供：

```python
build_public_environment_context(...)
```

输入可以包括：

```text
task metadata
resolved verifier plan
test_feedback_policy
scaffold allowed tools
workspace backend facts
diagnostic_shell enablement facts
dependency environment facts
```

输出必须是模型可见安全对象。builder 内部要调用现有 visibility / forbidden marker helper，或者新增同等级别检查。

### 4.3 Scaffold 注入点

需要检查并修改：

```text
src/repo_harness/scaffolds/patch_focused_react.py
src/repo_harness/scaffolds/simple_react.py
src/repo_harness/scaffolds/planner_coder_verifier.py
src/repo_harness/agent_loop/loop.py
```

第一版优先在 patch-focused scaffold 中落地，因为它是当前 SWE agent 训练主线。其他 scaffold 可以只记录 unsupported diagnostics，除非实现成本很低。

注入方式建议：

```text
system / developer prompt 中加入 PublicEnvironmentContext.model_visible_prompt_block
RunRecorder 写入 public_environment_context.json
run metadata 写入 public_environment_context_digest
TrainingView / DataProto 只保留 digest 或安全摘要，不携带完整 prompt block
```

### 4.4 公开测试工具入口

现有 `run_tests` 已经支持公开反馈路径。Stage 16C 的执行计划允许两种实现方案：

方案 A：保留 `run_tests`，升级描述和上下文。

```text
优点：代码变动较小，兼容现有工具。
要求：模型可见描述必须写清它不是任意 shell 命令，也不是 hidden verifier。
```

方案 B：新增 `run_public_tests`，作为更明确的模型可见工具名。

```text
优点：模型更容易理解，和 hidden final verifier 的边界更清楚。
要求：必须避免和 run_tests 形成两套不一致的实现；第一版可以内部复用 run_tests 公共反馈路径。
```

我建议 Stage 16C 第一版默认采用方案 A，也就是 `run_tests_only`。
只有当本阶段的 prompt/scaffold 对照显示工具命名本身明显影响模型理解时，才新增
`run_public_tests` 作为别名；即使新增别名，也不能同时引入多套 verifier 路由。
如果新增 `run_public_tests`，必须满足：

```text
input schema 第一版不允许任意 command 字符串。
只能调用 run_feedback_public(...) 或等价公开反馈路径。
不能调用 run_feedback(...) hidden oracle。
不能暴露 FAIL_TO_PASS、PASS_TO_PASS、hidden selector 或 official result。
工具结果必须写入 public_test_result_ref，并保留 sanitized preview。
```

## 5. 数据流

Stage 16C 的目标数据流如下：

```text
task / verifier plan / runtime config / scaffold
-> PublicEnvironmentContextBuilder
-> PublicEnvironmentContext
-> scaffold prompt block
-> model-visible initial prompt
-> tools: read_file / grep / edit_file / git_diff / run_tests
-> RunRecorder public_environment_context artifact
-> visibility scan
-> TrainingView safe digest / summary
```

其中公开测试数据流如下：

```text
model calls run_tests or run_public_tests
-> ToolExecutor checks test_feedback_policy
-> verifier.run_feedback_public(...)
-> sanitized public tool observation
-> recorder feedback artifact
-> no hidden selector in model-visible content
```

如果 `test_feedback_policy=disabled`，则：

```text
public_test_entry.status = disabled
run_tests returns test_feedback_disabled
prompt tells model public feedback is unavailable
```

如果 `test_feedback_policy=oracle_hidden_feedback`，Stage 16C 不应自动宣称公开测试可用。除非任务同时提供独立 public feedback plan，否则：

```text
public_test_entry.status = unavailable
hidden_feedback_visible = false
```

## 6. 安全边界

### 6.1 禁止泄漏字段

`PublicEnvironmentContext`、scaffold prompt、tool schema、RunRecorder 公开 artifact、TrainingView、DataProto
和 export 中都不能出现：

```text
FAIL_TO_PASS
PASS_TO_PASS
gold_patch
test_patch
hidden_verifier
official_verifier_result
official_selector
accepted_label
reward_metadata
reward_extra_info
provider_secret
repo-harness-run
runtime_private
.repo_harness_runtime
.repo_harness_env_overlay
宿主机绝对路径
```

注意：模型可见 prompt 不应直接使用 `hidden verifier`、`gold patch` 这类容易诱导模型寻找非公开材料的词。
更安全的表述是“不要尝试访问 evaluator-only 文件、隐藏验证材料或非公开证据”。
同时，prompt 不能出现具体 evaluator-only artifact 名称、路径或 selector 内容。

### 6.2 路径和命令提示

公开环境提示不能告诉模型：

```text
cd /workspace
cd /testbed
source /opt/conda/bin/activate
pip install -e .
python setup.py develop
cat /repo-harness-run/...
find .git
```

如果任务确实需要依赖准备，提示只能说明：

```text
Dependencies are prepared by the harness when available.
Do not install dependencies into the repository unless a future controlled tool explicitly allows it.
```

### 6.3 公开测试不可进入 reward 边界

公开测试工具结果可以帮助模型调试，但不能替代最终 verifier / reward boundary。

Stage 16C 需要确保：

```text
run_tests public result != final verifier result
public pass/fail != reward finality
public feedback artifact != hidden final verifier artifact
```

如果模型使用公开测试并修复成功，最终是否可训练仍由真实 final verifier、reward boundary、visibility gate、token provenance 和 formal batch validator 决定。

## 7. 实施步骤

### Step 1：盘点当前公开反馈和 scaffold 形状

只读检查：

```text
src/repo_harness/tools/minimal.py
src/repo_harness/scaffolds/patch_focused_react.py
src/repo_harness/scaffolds/policies.py
src/repo_harness/agent_loop/loop.py
src/repo_harness/verifier/runner.py
tests/unit/test_test_feedback_policy.py
tests/unit/test_scaffold_patch_focused_react.py
```

输出一份小型 inventory，建议写入 Stage 16C evidence：

```text
stage16c_existing_public_feedback_inventory.json
```

至少记录：

```text
run_tests 当前工具名和 schema
run_feedback_public 当前可用性
test_feedback_policy 四种模式
patch_focused_react 默认策略
diagnostic_shell scaffold 是否独立
execute_bash 是否仍是安全最小工具
```

### Step 2：新增 PublicEnvironmentContext

新增 schema 和 builder。验收要求：

```text
公开字段通过 visibility scan。
缺失 public feedback 时 fail closed。
hidden selector / reward metadata / official result 注入时拒绝。
上下文 digest 稳定。
同一输入重复构造 digest 相同。
公开 prompt block 不包含宿主绝对路径。
```

### Step 3：接入 scaffold prompt

优先接入 `patch_focused_react`。

建议新增或更新：

```text
patch_focused_react_public_environment
patch_focused_react_execute_bash_public_environment
patch_focused_react_diagnostic_shell_public_environment
```

也可以不新增 scaffold id，而是在现有 scaffold 中通过 runtime facts 注入 prompt block。
无论选择哪种实现，必须确保：

```text
tool allowlist 不因为 Stage 16C 自动扩大。
diagnostic_shell 仍必须显式启用。
execute_bash 仍使用 Stage 16A command policy。
run_tests / run_public_tests 的描述和实际路由一致。
```

### Step 4：公开测试入口语义收口

如果只升级 `run_tests`：

```text
更新 model_visible_description 和 model_visible_prompt。
增加 public_environment_context 中的 run_tests 提示。
补测试证明 run_tests 在 public_only / structured_public_feedback 下不泄漏 hidden selector。
```

如果新增 `run_public_tests`：

```text
新增 ToolDefinition。
第一版 input_schema 必须 additionalProperties=false。
内部复用公开 feedback 路径。
保留 run_tests 的兼容行为。
测试 run_public_tests 不可在 disabled / oracle-hidden-only 情况下伪造公开结果。
```

执行 agent 在实现前应选择其中一个方案，并在 `stage16c_acceptance_summary.json`
中记录：

```text
public_test_tool_strategy = run_tests_only | run_public_tests_alias
```

### Step 5：RunRecorder 和 visibility evidence

新增或复用 recorder artifact：

```text
public_environment_context.json
public_environment_prompt_block.txt
public_environment_context_visibility_report.json
```

公开 artifact 必须可传播；如果需要保留 raw debug，必须放入 runtime-private 证据目录，并在 manifest 中标明不可传播。

### Step 6：prompt/scaffold 对照

新增对照测试和报告：

```text
stage16c_scaffold_comparison_report.json
```

至少比较：

```text
旧 prompt 是否缺少公开测试入口说明。
新 prompt 是否包含结构化工具优先原则。
新 prompt 是否避免 /workspace、/repo-harness-run、conda 路径猜测。
新 prompt 是否明确依赖不由模型随意安装。
新 prompt 是否未暴露 hidden verifier / selector。
```

对照范围必须包含最终发送给模型的完整 prepared messages 和 tool protocol，而不仅是
`PublicEnvironmentContext.model_visible_prompt_block` 单独文本。也就是说，scaffold
提示、工具描述、工具 schema 摘要、system / developer message 拼接后的完整模型可见上下文
都要进入泄漏扫描和对照报告。

这不是模型效果评测；它是 prompt 结构验收。

## 8. 新增测试计划

Stage 16C 应新增下面这些测试文件或等价覆盖：

```text
tests/unit/test_repo_harness_stage16c_public_environment_context.py
tests/unit/test_repo_harness_stage16c_public_test_entry.py
tests/unit/test_repo_harness_stage16c_scaffold_prompt.py
tests/unit/test_repo_harness_stage16c_visibility.py
```

重点用例：

### PublicEnvironmentContext

```text
public_only 生成 available public test entry。
structured_public_feedback 生成 structured public test entry。
disabled 生成 disabled public test entry。
oracle_hidden_feedback 不能自动生成 public test entry。
hidden selector 字段注入会被拒绝。
gold patch / test patch / reward metadata 注入会被拒绝。
宿主绝对路径注入会被拒绝或脱敏。
context_digest 对同一输入稳定。
```

### Scaffold prompt

```text
提示包含 read_file / grep / edit_file / git_diff / run_tests 的工具分工。
提示不包含 /workspace、/testbed、/repo-harness-run、conda activate。
提示不鼓励 pip install -e .。
提示不暴露 FAIL_TO_PASS / PASS_TO_PASS。
diagnostic_shell 未启用时不出现在默认工具说明里。
diagnostic_shell 启用时说明它是同题诊断工具，不是 hidden verifier。
```

### Public test entry

```text
run_tests 在 public_only 下只返回公开摘要。
run_tests 在 structured_public_feedback 下只返回结构化公开摘要。
run_tests 在 disabled 下结构化拒绝。
run_tests 不能在 oracle_hidden_feedback 场景下暴露 hidden selector。
如果新增 run_public_tests，则它必须复用公开反馈路径，不能调用 hidden feedback。
```

### Visibility / export

```text
PublicEnvironmentContext 不进入 DataProto 的完整明细。
AgentLoopOutput.extra_fields 不携带完整 PublicEnvironmentContext 或完整 prompt block。
TrainingView 只保留 digest 或安全摘要。
TransferQueue、RolloutSample、DataProto.non_tensor_batch 和 offline export 只保留 digest 或安全摘要。
export / SFT 输出不包含 hidden selector。
RunRecorder 公开 artifact 通过 path leak scan。
```

## 9. 既有回归测试

Stage 16C 实现完成后，至少运行下面这些已有测试：

```bash
PYTHONPATH=src uv run --extra dev python -m pytest -q \
  tests/unit/test_test_feedback_policy.py \
  tests/unit/test_scaffold_patch_focused_react.py \
  tests/unit/test_command_policy.py \
  tests/unit/test_repo_harness_stage16a_execute_bash.py \
  tests/unit/test_repo_harness_stage16b_diagnostic_shell_tool.py \
  tests/unit/test_repo_harness_verl_stage16b5_acceptance.py \
  tests/integration/test_repo_harness_stage16b_docker_diagnostic_session.py \
  tests/unit/test_tools.py \
  tests/integration/test_tool_execution.py
```

如果本地 Docker 不可用，Docker integration 可以 skip，但 Stage 16C 的 acceptance summary
必须如实记录：

```text
docker_backend_available
docker_stage16b_regression_executed
docker_stage16b_regression_status
```

不能把 skip 当成通过。

## 10. 本地 evidence

Stage 16C 完成后建议生成：

```text
runs/repo-harness-verl-stage16c-local-<timestamp>/
```

目录中至少包含：

```text
stage16c_acceptance_summary.json
stage16c_existing_public_feedback_inventory.json
stage16c_public_environment_context_report.json
stage16c_prompt_leak_scan_report.json
stage16c_public_test_entry_report.json
stage16c_scaffold_comparison_report.json
stage16c_command_log.sanitized.jsonl
runtime_private/stage16c_command_log.raw.jsonl
```

`stage16c_acceptance_summary.json` 至少包含：

```text
stage = "16C"
public_environment_context_builder_present = true
public_environment_context_visibility_passed = true
public_test_tool_strategy
public_test_entry_available_count
public_test_entry_disabled_count
hidden_selector_leak_count = 0
host_path_leak_count = 0
prompt_forbidden_guess_count = 0
run_tests_public_feedback_sanitized = true
execute_bash_allowlist_changed = false
diagnostic_shell_scope_changed = false
stage16a_regression_passed
stage16b_regression_passed
stage16b5_regression_passed
```

## 11. 验收标准

Stage 16C 只有满足下面条件才算完成：

```text
PublicEnvironmentContextBuilder 已实现并有测试。
模型可见 prompt block 不泄漏 hidden selector、reward metadata、official result 或宿主路径。
模型提示明确结构化工具优先原则。
公开测试入口语义和实际 run_tests / run_public_tests 路由一致。
test_feedback_policy=disabled 和 oracle_hidden_feedback-only 场景不会伪造公开测试入口。
Stage 16A execute_bash allowlist 没有被放宽。
Stage 16B diagnostic_shell 权限没有被扩大。
本地 Stage 16C evidence 可生成并通过 path leak scan。
新增 Stage 16C 测试和关键前置回归通过。
```

## 12. 提交范围

Stage 16C 提交应只包含：

```text
37-stage-16c-execution-plan.md
PublicEnvironmentContext 相关实现
scaffold prompt / tool description 的 Stage 16C 修改
run_tests 或 run_public_tests 的公开入口修改
Stage 16C 测试
Stage 16C 本地 evidence
```

不要混入：

```text
未跟踪 HTML 资料
training_design 临时资料
vastai_cli.md
pyrightconfig.json
reference/verl 修改
Stage 16D official verifier healthcheck
Stage 16E patch hygiene
Stage 16.5 代表性诊断扩展
```

## 13. 进入 Stage 16D 的条件

只有满足下面条件，才进入 Stage 16D：

```text
公开环境上下文和 prompt 不泄漏 evaluator-only 信息。
公开测试入口已经明确可用或明确不可用，不能模糊。
模型提示不会引导猜测 /workspace、/repo-harness-run、conda path 或 hidden selector。
run_tests / run_public_tests 公开反馈和 hidden final verifier 边界清楚。
Stage 16A execute_bash、Stage 16B diagnostic_shell 和 Stage 16B.5 remote Docker-capable backend 的安全边界仍然通过回归。
```

Stage 16C 通过不表示 verifier 环境健康已经完成。official verifier、gold patch 和 no-op
healthcheck 仍然必须在 Stage 16D 单独实现和验收。
