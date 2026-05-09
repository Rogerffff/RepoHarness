# 第 1 章：当前运行架构和 `run_task`

本章目标不是先讲 V4 最复杂的任务来源，而是先用一个可以快速复跑、容易观察、产物完整的任务，把 `repo-harness run-task` 到底如何把一次单任务运行串起来讲清楚。

这一章使用的示例任务是：

```text
realrepo_local_buggy_calculator
```

它不是 SWE-Bench 任务，也不是真实 GitHub issue / pull request 任务。它来自项目内置的本地 repository fixture：

```text
tests/fixtures/repos/buggy_calculator
```

选择它的原因是：这个任务很小，issue、源码、测试、patch 都能直接看懂，因此适合先学习 `run_task` 的主链路。它仍然会走真实的 Docker backend、真实 provider、真实 tool call、真实 verifier、真实 reward 和真实 artifact 记录，所以它足够代表“运行骨架”；但是它不代表 V4 最成熟的任务构造能力。SWE-Bench-like 任务和 GitHub PR / issue freeze 会在第 2 章专门讲。

## 本章链路图

`run_task` 可以理解为“单任务轨迹生产编排器”。它不是一个简单的命令行 wrapper，而是把任务、配置、工作区、模型、工具、验证器、奖励和可审计产物串成一次完整 run 的核心入口。

```text
repo-harness run-task
  -> load_run_config
  -> load_task
  -> build_scaffold / resolve_feedback_policy / resolve_allowed_tools
  -> create_workspace_adapter
  -> create_source_checkout
  -> create_setup_workspace
  -> baseline verifier
  -> tool schema snapshot
  -> environment fingerprint
  -> run_config_facts
  -> create_agent_workspace
  -> ContextBuilder.build_initial_messages
  -> create_model_client
  -> ToolExecutionContext
  -> AgentLoop.run
  -> capture_final_patch
  -> final verifier
  -> compute_reward_metadata
  -> metrics / run_metadata / summary
```

用更贴近训练数据生产的语言说，这条链路做了四件事：

1. 先判断这个任务是不是值得交给 agent。也就是创建工作区、运行 baseline verifier，确认初始缺陷确实存在，既有行为没有坏掉。
2. 再把 agent 放进一个可执行仓库环境里。这里包括 Docker backend、权限策略、工具 schema、上下文消息和 provider client。
3. 然后记录 agent 的完整行为。包括每轮模型请求、模型响应、工具调用、工具结果、文件修改、测试反馈和最终回答。
4. 最后用独立 verifier 判断 patch 是否真的解决任务，并生成 reward、metrics、run metadata 和训练导出所需的审计引用。

## 本章使用的具体命令

本章复跑过的命令是：

```bash
PATH=.venv/bin:$PATH repo-harness run-task \
  runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2/task.yaml \
  --config runs/v3-core-realrepo-deepseek-20260504T000000Z/generated_inputs/realrepo_local_buggy_calculator_deepseek_docker_v2.yaml \
  --output-dir runs/tutorial-v4-deep-dive-20260505T082937Z \
  --run-id tutorial_realrepo_docker
```

命令结构可以拆成：

```text
repo-harness run-task <task_path> --config <run_config_path> --output-dir <output_parent_dir> --run-id <run_id>
```

其中：

```text
task_path =
runs/v3-core-realrepo-deepseek-20260504T000000Z/agent_loop_runs/v3_core_realrepo_local_buggy_calculator_deepseek_docker_v2/task.yaml

run_config_path =
runs/v3-core-realrepo-deepseek-20260504T000000Z/generated_inputs/realrepo_local_buggy_calculator_deepseek_docker_v2.yaml

output_parent_dir =
runs/tutorial-v4-deep-dive-20260505T082937Z

run_id =
tutorial_realrepo_docker
```

复跑生成的新 run 目录是：

```text
runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker
```

这个目录里最值得先看的文件是：

```text
task.yaml
run_config_facts.json
baseline.json
resolved_verifier_plan.json
transcript.jsonl
events.jsonl
artifacts.json
docker_backend_facts.json
container_execution_facts/manifest.json
final.patch
final.diff
verifier.json
reward.json
metrics.json
run_metadata.json
summary.md
```

这些文件不是随便散落的日志。它们分别回答：

```text
task.yaml                         这次到底跑的是什么任务
run_config_facts.json             这次到底用什么模型、工具、工作区、权限和 verifier 策略运行
baseline.json                     初始仓库是否是一个有效的修复任务
resolved_verifier_plan.json       最终 verifier 会依据哪些测试和策略判定
transcript.jsonl                  agent 和工具之间的消息轨迹
events.jsonl                      run 内部发生过哪些事件
artifacts.json                    所有 artifact 的索引、哈希、大小和相对路径
docker_backend_facts.json         Docker backend 是否真的启用，以及使用了什么镜像和策略
container_execution_facts/        每一次容器命令执行的结构化事实
final.patch / final.diff          agent 最后留下的代码改动
verifier.json                     final verifier 结果
reward.json                       reward 计算结果和训练可用性信息
metrics.json                      交互效率、测试次数、工具次数、成功状态等指标
run_metadata.json                 导出和验收最常引用的 run 级摘要
summary.md                        给人类快速扫一眼的摘要
```

## 示例任务来自哪里

这次示例任务不是 SWE-Bench 数据集任务。它的来源链路是：

```text
tests/fixtures/v3/real_repositories/real_repository_task_inputs.json
  -> repo-harness build-v3-task-set
  -> runs/v3-stage-04-task-adapter-20260502T170000Z/generated_tasks/real_repository/realrepo_local_buggy_calculator.yaml
  -> run-task 运行时复制到 run 目录里的 task.yaml
```

最源头的输入在：

```text
tests/fixtures/v3/real_repositories/real_repository_task_inputs.json
```

里面对应的记录是：

```text
task_id: realrepo_local_buggy_calculator
source_kind: fixed_local_mirror
remote_url: local://tests/fixtures/repos/buggy_calculator
source_path: tests/fixtures/repos/buggy_calculator
dataset_split: v3_stage_04
```

这说明它是一个项目内置的固定本地镜像任务。它的任务仓库是：

```text
tests/fixtures/repos/buggy_calculator
```

仓库中有：

```text
calculator.py
pyproject.toml
tests/test_calculator.py
```

任务 issue 是：

```text
Update calculator.divide so division by zero raises ValueError with a clear message instead of leaking ZeroDivisionError.
```

也就是说，`calculator.divide` 目前直接做：

```python
def divide(left: int, right: int) -> float:
    return left / right
```

当 `right == 0` 时，Python 会抛出 `ZeroDivisionError`。任务要求改成抛出带有清晰信息的 `ValueError`。

这个任务的测试分成两类：

```text
fail_to_pass_tests:
tests/test_calculator.py::test_divide_zero

pass_to_pass_tests:
tests/test_calculator.py::test_add
tests/test_calculator.py::test_divide_regular_numbers
```

`fail_to_pass_tests` 的含义是：在初始代码上应该失败，agent 修好后应该通过。`pass_to_pass_tests` 的含义是：在初始代码上应该通过，agent 修好后也应该继续通过，防止修复过程中破坏既有行为。

这就是为什么这个任务的 baseline exit code 是 `1`，但 baseline status 仍然是 `valid`。对于修复类任务，初始测试全绿反而不是一个好的信号，因为那可能说明任务没有暴露缺陷。正确状态是：目标失败测试失败，回归保护测试通过。

## `task.yaml` 和 `run_config` 分别控制什么

`task.yaml` 定义“要解决什么”。这个文件里的核心信息包括：

```text
id                         任务编号
repo                       源仓库路径或源仓库归档路径
repo_source_spec           源仓库如何物化，以及是否允许脏状态
issue                      模型可见的任务描述
expected_files             预期可能修改的文件
test_command               默认测试命令
fail_to_pass_tests         缺陷暴露测试
pass_to_pass_tests         回归保护测试
visibility                 哪些字段模型可见，哪些字段只给 verifier 或 reward 使用
environment                Python 版本、包管理器、setup 网络策略等环境声明
timeouts                   agent、setup、测试、final verifier 的超时时间
decontamination            数据污染相关的来源说明
```

`run_config` 定义“怎么运行”。这次使用的配置文件是：

```text
runs/v3-core-realrepo-deepseek-20260504T000000Z/generated_inputs/realrepo_local_buggy_calculator_deepseek_docker_v2.yaml
```

这个配置里的重点是：

```text
model.provider: deepseek
model.model_id: deepseek-v4-pro
model.temperature: 0.0
runtime.execution_mode: docker
runtime.permission_mode: auto
runtime.docker_backend.image_ref: repo-harness-v3-python:stage2
runtime.docker_backend.requested_container_platform: linux/arm64
runtime.docker_backend.network_policy: deny_agent_run
runtime.scaffold_id: simple_react
runtime.max_turns: 6
runtime.max_tool_calls: 8
runtime.max_test_runs: 1
evaluation.final_verifier_mode: strict_patch_replay
```

所以可以用一句话区分：

```text
task.yaml 说“修什么仓库里的什么问题”。
run_config 说“用什么模型、什么 Docker 环境、什么工具权限和什么验证策略来修”。
```

## 代码 walkthrough：`run_task` 的每一步

源码入口：

```text
src/repo_harness/evaluation/runner.py:69
```

函数签名是：

```python
def run_task(
    task_path: str | Path,
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    inject_interrupt_after: InjectInterruptPoint | None = None,
) -> Path:
```

这里最重要的参数是：

```text
task_path     第一个位置参数，指向 task.yaml
config_path   --config 参数，指向运行配置 YAML
output_dir    输出父目录
run_id        本次 run 的名字
```

### 1. 加载运行配置和任务定义

对应代码：

```text
src/repo_harness/evaluation/runner.py:78
src/repo_harness/evaluation/runner.py:86
```

代码先执行：

```python
config = load_run_config(config_path, output_dir=output_dir)
loaded = load_task(task_path)
```

这里会得到两个核心对象：

```text
RunConfig       从 run_config YAML 解析出来，描述模型、Docker、权限、预算和 verifier 模式
LoadedTask      从 task.yaml 解析出来，里面包括原始 TaskDefinition、RunnableTask 和 verifier_config
```

从这一刻开始，`run_task` 已经同时知道：

```text
我要修什么任务
我要用什么运行方式修这个任务
```

紧接着有几个硬性保护：

```text
model.provider 只能是 replay、fake、mock、deepseek、openai 中被允许的形式
openai 只能作为 DeepSeek fallback 的内部 smoke run，不能作为主 provider 随便使用
final_verifier_mode 必须是 strict_patch_replay
```

这说明当前正式路径不允许“模型跑完后直接相信工作区结果”。必须把最终 patch 拿出来，在新的 verification workspace 里重新应用，再跑 verifier。

### 2. 解析 scaffold、反馈策略和工具列表

对应代码：

```text
src/repo_harness/evaluation/runner.py:87
src/repo_harness/evaluation/runner.py:88
src/repo_harness/evaluation/runner.py:93
```

代码会构造：

```text
scaffold        当前是 simple_react
feedback_policy 测试反馈如何暴露给模型
allowed_tools   模型允许调用哪些工具
```

这三个对象的解析都发生在 `run_task` 刚加载完 `RunConfig` 和 `TaskDefinition` 之后，也就是在真正创建 Docker workspace 之前。它们的作用是先确定“本次 agent 应该以什么交互模式运行、测试反馈能不能给模型看、模型能调用哪些工具”。

### 2.1 `scaffold` 是如何解析的

输入来自 run config：

```yaml
runtime:
  scaffold_id: simple_react
```

对应代码：

```text
src/repo_harness/evaluation/runner.py:87
src/repo_harness/scaffolds/registry.py:46
src/repo_harness/scaffolds/simple_react.py:14
src/repo_harness/scaffolds/schemas.py:11
```

执行逻辑是：

```python
scaffold = build_scaffold(config.runtime.scaffold_id)
```

`build_scaffold("simple_react")` 会进入 scaffold registry。默认 registry 里注册了几种 scaffold：

```text
simple_react
patch_focused_react
single_shot_patch
planner_coder_verifier
```

当前配置选择的是 `simple_react`，所以最终得到一个 `ScaffoldDefinition` 对象。这个对象不是模型消息本身，而是一组运行策略元数据，核心字段包括：

```text
scaffold_id: simple_react
scaffold_version: repo_harness_simple_react_v1
prompt_fragment: 一段告诉模型如何迭代、读文件、改文件、跑测试、检查 diff 的 scaffold 指令
allowed_tools_policy: repo_harness_simple_react_allowed_tools_v0
phase_transition_policy: repo_harness_simple_react_single_phase_v0
default_stop_policy: repo_harness_simple_react_stop_policy_v0
default_test_feedback_policy: oracle_hidden_feedback
default_feedback_tests_passed_policy: stop_immediately
allows_final_answer_without_tool: true
allows_feedback_verifier_repair: true
allowed_tools: DEFAULT_TOOL_ORDER
initial_phase: act
```

这里容易混淆的是：`simple_react` 的默认反馈策略是 `oracle_hidden_feedback` 和 `stop_immediately`，但本次 run config 显式覆盖了它们，所以最终运行时不是使用这两个默认值。默认值仍然会被记录下来，用于审计“运行配置覆盖了 scaffold 默认值”。

这两个字段分别属于两组不同的模式。

第一组是 `TestFeedbackPolicy`，也就是“模型可见测试反馈策略”。它回答的问题是：agent 在中途调用 `run_tests` 时，系统是否真的运行测试，以及把哪些测试反馈回流给模型。代码定义在：

```text
src/repo_harness/evaluation/schemas.py:24
```

当前一共有四种：

```text
disabled
public_only
structured_public_feedback
oracle_hidden_feedback
```

它们的含义分别是：

```text
disabled
  禁用模型可见的测试反馈。
  模型不能通过 run_tests 获得测试结果。如果模型直接调用 run_tests，工具结果会返回 test_feedback_disabled。
  如果模型尝试通过 bash 执行 pytest 这类公开测试命令，command policy 也会识别为测试命令并拒绝或路由，避免绕过。
  final verifier 仍然会在 agent 停止后运行，所以 disabled 不是“不验证”，而是“中途不给模型测试反馈”。
  这个模式最接近 SWE-Bench-like final-only 评测。

public_only
  允许模型获得公开测试反馈，但反馈比较粗。
  实现上会走 public feedback verifier，不运行 evaluator-only hidden suite。
  返回给模型的内容类似 public_status、pass_ratio、error_type，不包含 hidden fail-to-pass / pass-to-pass 细节。

structured_public_feedback
  也只允许公开测试反馈，但返回格式更结构化。
  实现上同样走 public feedback verifier，不运行 evaluator-only hidden suite。
  返回给模型的内容类似 JSON 风格的 public_feedback，包括 accepted、pass_ratio、error_type。
  本章示例 run 使用的就是这个模式。

oracle_hidden_feedback
  允许 run_tests 调用 feedback verifier，并把 accepted、fail_to_pass、pass_to_pass 等结构化反馈回流给模型。
  这个模式会让模型看到 evaluator-only 风格的强反馈，因此适合调试、研究对照或早期 replay 回归，不适合伪装成正式 final-only benchmark。
  对 SWE-Bench-like final-only 任务，schema 校验会阻止使用 oracle_hidden_feedback。
```

第二组是 `FeedbackTestsPassedPolicy`，也就是“feedback verifier 已经 accepted 之后，AgentLoop 如何处理”。它回答的问题是：如果 agent 中途调用 `run_tests`，并且反馈结果已经显示通过，循环要不要马上结束。代码定义在：

```text
src/repo_harness/evaluation/schemas.py:33
```

当前一共有三种：

```text
stop_immediately
require_model_final
continue
```

它们的含义分别是：

```text
stop_immediately
  一旦 run_tests 的反馈结果 accepted=true，AgentLoop 立刻把 agent_stop_reason 设为 feedback_tests_passed。
  之后仍然会进入 capture_final_patch 和 formal final verifier。
  这个模式成本低，适合 replay 回归或希望尽快停止的实验，但真实 provider 场景里有时会少一轮模型总结或检查 final diff 的机会。

require_model_final
  即使 run_tests 已经 accepted=true，也不立刻停止。
  系统会把测试通过的工具结果回流给模型，要求模型再给出 final answer，或者有机会调用 git_diff 检查最终改动。
  本章示例 run 使用的就是这个模式，因此它在测试通过后仍然继续到模型 final answer。

continue
  把 run_tests accepted=true 当作普通工具反馈，不因为测试通过而触发特殊停止。
  是否继续完全交给模型行为、最大轮数、最大工具调用次数、最大测试次数、超时和 scaffold stop policy。
  这个模式适合研究“即使已有正反馈，模型是否会继续探索或引入回归”的行为，但成本和不确定性更高。
```

还有一个解析后的特殊值叫：

```text
not_applicable
```

它不是 run config 里直接配置的 `FeedbackTestsPassedPolicy`，而是当 `test_feedback_policy=disabled` 时解析出来的结果。原因是模型没有可用的中途测试反馈，就不可能出现“feedback verifier 已经 accepted，因此要不要停止”的情形。

放回本章示例，`simple_react` scaffold 默认是：

```text
default_test_feedback_policy: oracle_hidden_feedback
default_feedback_tests_passed_policy: stop_immediately
```

但是本次 run config 显式写了：

```yaml
runtime:
  test_feedback_policy: structured_public_feedback
  feedback_tests_passed_policy: require_model_final
```

所以最终解析结果是：

```text
resolved_test_feedback_policy: structured_public_feedback
resolved_feedback_tests_passed_policy: require_model_final
hidden_feedback_visible_to_model: false
```

这说明本次 agent 可以调用 `run_tests`，但只能得到结构化公开反馈；当公开反馈显示测试通过时，不会立刻停止，而是继续等待模型输出 final answer。

`scaffold` 解析完成后，主要进入三个地方：

```text
1. ContextBuilder
   用来生成模型初始消息中的 scaffold metadata 和 scaffold_prompt_fragment。

2. AgentLoop
   用来判断当前 phase、停止策略、final answer 是否有效，以及每个 phase 允许哪些工具。

3. run_config_facts.json / run_metadata.json
   用来记录本次 run 实际采用的 scaffold_id、scaffold_version、allowed_tools_policy、phase_policy 和 stop_policy。
```

在本次 run 的产物中可以看到：

```json
{
  "scaffold_id": "simple_react",
  "scaffold_version": "repo_harness_simple_react_v1",
  "allowed_tools_policy": "repo_harness_simple_react_allowed_tools_v0",
  "phase_policy": "repo_harness_simple_react_single_phase_v0",
  "stop_policy": "repo_harness_simple_react_stop_policy_v0"
}
```

这些字段出现在：

```text
runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/run_config_facts.json
runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/run_metadata.json
```

### 2.2 `feedback_policy` 是如何解析的

输入同时来自 run config、scaffold 默认值和任务类型。

本次 run config 中显式写了：

```yaml
runtime:
  test_feedback_policy: structured_public_feedback
  feedback_tests_passed_policy: require_model_final
```

对应代码：

```text
src/repo_harness/evaluation/runner.py:88
src/repo_harness/scaffolds/policies.py:17
src/repo_harness/evaluation/schemas.py:52
```

执行逻辑是：

```python
feedback_policy = resolve_feedback_policy(
    run_config=config,
    scaffold=scaffold,
    task=loaded.runnable_task,
)
```

解析顺序可以理解为：

```text
第一步：读取 run_config.runtime.test_feedback_policy。
如果 run config 显式配置了，就优先使用 run config。
如果 run config 没有配置，再看任务是不是 SWE-Bench-like final-only。
如果是 SWE-Bench-like final-only，默认禁用中途测试反馈。
否则使用 scaffold.default_test_feedback_policy 或任务默认策略。

第二步：读取 run_config.runtime.feedback_tests_passed_policy。
如果测试反馈策略是 disabled，则 resolved_feedback_tests_passed_policy 固定为 not_applicable。
如果测试反馈策略不是 disabled，就优先使用 run config 配置。
如果 run config 没有配置，再使用 scaffold 默认值或 provider 默认值。

第三步：计算 hidden_feedback_visible_to_model。
只有 resolved_test_feedback_policy 是 oracle_hidden_feedback 时，这个字段才会是 true。
```

本次任务不是 SWE-Bench-like final-only，且 run config 显式覆盖了测试反馈策略，所以最终解析结果是：

```json
{
  "schema_version": "repo_harness_resolved_feedback_policy_facts_v2_v0",
  "scaffold_default_test_feedback_policy": "oracle_hidden_feedback",
  "scaffold_default_feedback_tests_passed_policy": "stop_immediately",
  "runtime_test_feedback_policy": "structured_public_feedback",
  "runtime_feedback_tests_passed_policy": "require_model_final",
  "resolved_test_feedback_policy": "structured_public_feedback",
  "resolved_feedback_tests_passed_policy": "require_model_final",
  "hidden_feedback_visible_to_model": false,
  "swe_bench_like_final_only": false
}
```

这几个字段的含义是：

```text
scaffold_default_test_feedback_policy
  scaffold 原本建议的测试反馈策略。

runtime_test_feedback_policy
  run config 显式配置的测试反馈策略。

resolved_test_feedback_policy
  最终实际生效的测试反馈策略。

resolved_feedback_tests_passed_policy
  如果中途测试已经通过，agent loop 如何处理。
  本次是 require_model_final，意思是测试通过后不会立刻停止，而是要求模型继续给出 final answer。

hidden_feedback_visible_to_model
  本次是 false，意思是不会把 evaluator-only 隐藏反馈暴露给模型。
```

`feedback_policy` 解析完成后，主要进入四个地方：

```text
1. allowed_tools 解析
   如果 resolved_test_feedback_policy 是 disabled，就会从 allowed_tools 中移除 run_tests。

2. ContextBuilder
   决定模型初始上下文中的 test_command 是否可见，以及测试反馈相关提示如何组织。

3. ToolExecutionContext 和 AgentLoop
   决定 run_tests 工具执行后，什么内容可以作为 tool result 回流给模型。

4. run_config_facts.json / run_metadata.json
   记录完整 feedback_policy_resolution，方便后续审计训练轨迹是否泄漏隐藏 verifier 信息。
```

本次 run 中可以在这些位置看到它：

```text
run_config_facts.json 的 feedback_policy_resolution
run_metadata.json 的 feedback_policy_resolution
events.jsonl 中 model_call_started / model_call_completed 事件的 hidden_feedback_visible_to_model、test_feedback_policy 等字段
```

### 2.3 `allowed_tools` 是如何解析的

输入来自 scaffold 和刚才解析出的 feedback policy。

对应代码：

```text
src/repo_harness/evaluation/runner.py:93
src/repo_harness/scaffolds/policies.py:72
src/repo_harness/tools/minimal.py:20
```

执行逻辑是：

```python
allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
```

对于 `simple_react`，基础工具列表来自 `DEFAULT_TOOL_ORDER`：

```text
list_files
read_file
grep
edit_file
create_file
bash
run_tests
git_diff
```

然后根据反馈策略做一次过滤：

```python
allowed = list(scaffold.allowed_tools)
if feedback_policy.resolved_test_feedback_policy == TestFeedbackPolicy.disabled:
    allowed = [name for name in allowed if name != "run_tests"]
```

本次 `resolved_test_feedback_policy` 是 `structured_public_feedback`，不是 `disabled`，所以 `run_tests` 会保留。最终 `allowed_tools` 就是完整 8 个工具：

```text
list_files
read_file
grep
edit_file
create_file
bash
run_tests
git_diff
```

`allowed_tools` 解析完之后，它不是只作为内存变量用一下，而是会进入很多关键产物和执行路径：

```text
1. ContextBuilder 初始消息
   模型初始 user message 里会包含 allowed_tools 列表。

2. AgentLoop
   AgentLoop 每一轮会根据 allowed_tool_names 判断模型请求的工具是否允许。

3. ToolRegistry
   run_task 会调用 tool_registry_for_allowed_tools(allowed_tools)，把工具名转成 ToolDefinition。

4. tool_schema_snapshot artifact
   每个 ToolDefinition 会被固化成模型可见工具 schema，包括工具名、输入 schema、输出 schema、是否只读、是否需要权限、最大输出长度等。

5. provider request
   真实 provider 调用时，工具定义会被转换成 provider 的 tool schema，一起发给模型。

6. run_config_facts.json
   记录 tool_protocol.tool_order、tool_schema_snapshot_ref 和 tool_schema_snapshot_sha256。

7. events.jsonl
   model_call_started / model_call_completed 事件会记录当轮 allowed_tools。
```

本次 run 的工具 schema snapshot 在：

```text
runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/artifacts/tutorial_realrepo_docker_artifact_000013_tool_schema_snapshot.json
```

它里面的顶层信息是：

```json
{
  "schema_version": "repo_harness_tool_schema_snapshot_v2_v0",
  "snapshot_id": "tool_schema_snapshot_2a6791e9eadc",
  "snapshot_sha256": "2a6791e9eadcb22fa185d9b9a91fc2ae3476f745b23109e8a73ef5d7ffe5006c",
  "tool_order": [
    "list_files",
    "read_file",
    "grep",
    "edit_file",
    "create_file",
    "bash",
    "run_tests",
    "git_diff"
  ]
}
```

每个工具还会有自己的条目。以 `read_file` 为例，会记录：

```text
name: read_file
tool_version: repo_harness_read_file_v0
model_visible_description: Read a UTF-8 text file using a workspace-relative path...
input_schema: path、start_line、end_line、offset、limit 等参数
output_schema: content_preview
read_only: true
destructive: false
permission_required: true
max_output_chars: 4000
```

所以这一步解析完成后，严格来说有三层“产物”：

```text
内存对象：
  scaffold: ScaffoldDefinition
  feedback_policy: ResolvedFeedbackPolicyFacts
  allowed_tools: list[str]
  allowed_tool_registry: ToolRegistry
  tool_protocol: ToolProtocolFacts

模型可见内容：
  initial_messages 中的 scaffold_prompt_fragment、allowed_tools、budget、permission_mode、execution_mode、network_policy
  provider raw request 中的工具 schema

落盘审计产物：
  run_config_facts.json
  run_metadata.json
  artifacts/*_tool_schema_snapshot.json
  events.jsonl 中的 model_call_started / model_call_completed 事件
```

这次 run 的工具顺序最终记录在 `run_config_facts.json` 里：

```text
list_files
read_file
grep
edit_file
create_file
bash
run_tests
git_diff
```

注意，工具列表不是只在代码里隐式存在。`run_task` 后面会写 `tool_schema_snapshot`，把当时模型看到的工具 schema 固化成 artifact。这样未来做训练导出或者验收时，可以知道模型当时到底有哪些工具、每个工具参数长什么样。

### 3. 创建 run 目录并启动 RunRecorder

对应代码：

```text
src/repo_harness/evaluation/runner.py:94
src/repo_harness/evaluation/runner.py:98
src/repo_harness/evaluation/runner.py:104
src/repo_harness/evaluation/runner.py:114
```

代码会计算：

```text
actual_run_id = tutorial_realrepo_docker
run_dir = runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker
```

如果目录已存在，直接报错。这是为了避免覆盖旧 evidence。

然后进入：

```python
with RunRecorder(...) as recorder:
```

`RunRecorder` 是本次运行的审计记录器。它负责写：

```text
events.jsonl
transcript.jsonl
artifacts/
artifacts.json
run_status.json
summary.md
```

第一条事件是 `run_started`，里面记录了 `task_path`。随后 `run_task` 会把加载后的任务定义写入：

```text
run_dir/task.yaml
```

这个 `task.yaml` 是运行快照。即使原始任务文件之后被修改，这次 run 仍然可以通过快照复核当时跑的任务内容。

### 4. 创建 workspace backend

对应代码：

```text
src/repo_harness/evaluation/runner.py:116
src/repo_harness/evaluation/runner.py:117
src/repo_harness/evaluation/runner.py:141
```

代码调用：

```python
adapter = create_workspace_adapter(config=config, run_id=actual_run_id, run_dir=run_dir)
```

这一步根据 `runtime.execution_mode` 创建 workspace adapter。当前配置是：

```text
runtime.execution_mode: docker
```

所以实际创建的是 Docker backend，而不是本地进程 backend。

如果 Docker backend 初始化失败，代码会写结构化失败文件和事件，而不是静默退回本地执行。这一点很重要：V4 里 Docker execution mode 是 evidence 的一部分，不能“说是 Docker，实际上本地跑”。

这次 run 里的 Docker 后端事实在：

```text
runs/tutorial-v4-deep-dive-20260505T082937Z/tutorial_realrepo_docker/docker_backend_facts.json
```

可以看到：

```text
backend: docker
image_ref: repo-harness-v3-python:stage2
requested_container_platform: linux/arm64
network_policy: deny_agent_run
cleanup_status: completed
```

这里要注意表达边界：RepoHarness 可以说是 Docker-based executable repository environment，但不能把它夸成生产级安全沙箱。

### 5. 物化源代码、执行 setup、捕获依赖状态

对应代码：

```text
src/repo_harness/evaluation/runner.py:143
src/repo_harness/evaluation/runner.py:150
src/repo_harness/evaluation/runner.py:151
src/repo_harness/evaluation/runner.py:169
```

代码先创建 source checkout：

```python
source = adapter.create_source_checkout(loaded.runnable_task)
```

对于这个任务，来源是本地 fixed mirror：

```text
tests/fixtures/repos/buggy_calculator
```

Docker adapter 会把它物化到 run 管理的工作区中，并记录 source checkout facts。

然后创建 setup workspace：

```python
setup = adapter.create_setup_workspace(source)
```

再执行 setup 命令：

```python
setup_result = _run_setup_command(...)
```

这个任务没有 `setup_command`，所以 setup 阶段是一个受记录的 noop。即使没有 setup 命令，run 也会记录这个阶段已经发生过，避免审计时看不出它是“没做”还是“漏了”。

最后捕获 dependency state：

```python
dependency_state = adapter.capture_dependency_state(strategy=dependency_strategy)
```

对于本任务：

```text
dependency_state.strategy: none
```

意思是没有额外依赖安装状态需要恢复。更复杂的任务如果有 setup command，可能会需要记录或重放依赖状态。

### 6. 运行 baseline verifier

对应代码：

```text
src/repo_harness/evaluation/runner.py:176
src/repo_harness/evaluation/runner.py:203
src/repo_harness/evaluation/runner.py:205
src/repo_harness/evaluation/runner.py:233
src/repo_harness/evaluation/runner.py:268
```

这里分两种路径：

```text
如果是 SWE-Bench-like 任务，走 swebench_like_runtime_plan 的 baseline 逻辑。
如果不是 SWE-Bench-like 任务，就用 PytestVerifier 在 setup workspace 上跑 baseline。
```

当前示例任务不是 SWE-Bench-like，所以走普通 PytestVerifier：

```python
baseline_verifiers = [
    verifier.run_baseline(setup, loaded.verifier_config, recorder)
    for _ in range(2)
]
```

这里 baseline 会跑两次，目的是降低偶然性，辅助判断 flaky。最终写入：

```text
baseline.json
artifacts/*_baseline_verifier_results.json
events.jsonl 中的 baseline_completed 事件
```

这次结果的关键字段是：

```text
baseline status: valid
baseline exit code: 1
baseline rerun count: 2
initial_fail_to_pass_tests: tests/test_calculator.py::test_divide_zero
initial_pass_to_pass_tests:
  - tests/test_calculator.py::test_add
  - tests/test_calculator.py::test_divide_regular_numbers
```

这里最容易误解的是 `baseline exit code: 1`。它不是说任务不能跑，而是说初始仓库确实有 bug，目标失败测试失败了。只要 fail-to-pass 和 pass-to-pass 的语义符合预期，baseline status 就可以是 `valid`。

### 7. 写工具 schema、环境指纹和运行配置事实

对应代码：

```text
src/repo_harness/evaluation/runner.py:280
src/repo_harness/evaluation/runner.py:285
src/repo_harness/evaluation/runner.py:304
src/repo_harness/evaluation/runner.py:313
```

baseline 通过质量门之后，代码会先写工具 schema snapshot：

```python
_, tool_schema_snapshot_ref, tool_protocol = write_tool_schema_snapshot(...)
```

然后构造环境指纹：

```python
environment_fingerprint = build_local_environment_fingerprint(...)
```

再构造运行配置事实：

```python
run_config_facts = build_run_config_facts(...)
run_config_facts_ref = write_run_config_facts(run_dir, run_config_facts)
```

`run_config_facts.json` 非常重要。它不是原始 run_config YAML 的简单复制，而是一次运行的“解析后事实”。它会把以下内容放在一起：

```text
provider 和 model_id
temperature 和 max_output_tokens
scaffold_id 和 scaffold_version
工具顺序、工具协议版本和 tool schema snapshot 引用
Docker backend 是否启用
网络策略
权限策略
source checkout facts
environment_spec_hash
feedback policy resolution
final_verifier_mode
reward formula version
```

换句话说，未来看到一条 transcript 时，不能只问“模型说了什么、调用了什么工具”，还要知道“它当时是在什么工具契约、什么模型配置、什么工作区策略下产生的”。`run_config_facts.json` 就是回答这个问题的核心文件。

### 8. baseline 质量门

对应代码：

```text
src/repo_harness/evaluation/runner.py:334
src/repo_harness/evaluation/runner.py:335
src/repo_harness/evaluation/runner.py:346
```

如果 baseline 不能进入 agent run，`run_task` 会调用：

```python
_finalize_quality_gate_run(...)
```

然后提前结束。

这种情况包括 setup 失败、任务无效、测试解析置信度太低、初始状态不符合 fail-to-pass / pass-to-pass 语义等。它的设计意义是：不要把坏任务交给 agent 生产训练轨迹，否则后面的失败无法区分是 agent 不会修，还是任务本身不成立。

当前示例任务 baseline valid，所以继续进入 agent 阶段。

### 9. 写 resolved verifier plan，创建 agent workspace

对应代码：

```text
src/repo_harness/evaluation/runner.py:347
src/repo_harness/evaluation/runner.py:355
src/repo_harness/evaluation/runner.py:356
```

`ResolvedVerifierPlan` 把 verifier 相关信息固化下来：

```text
test_command
initial_fail_to_pass_tests
initial_pass_to_pass_tests
flaky_tests
parser_confidence
resolved_verifier_plan_id
```

然后创建 agent workspace：

```python
run_workspace = adapter.create_agent_workspace(...)
```

这里的关键点是：agent 不直接在 setup workspace 上改代码。`run_task` 会从 source checkout 创建一个 agent workspace，并按 dependency state 策略恢复必要状态。这样 baseline、agent 修改、final verifier 分别有清晰边界。

### 10. 构造模型初始上下文

对应代码：

```text
src/repo_harness/evaluation/runner.py:363
```

代码调用：

```python
initial_messages = ContextBuilder().build_initial_messages(...)
```

这一步会把任务描述、工作区信息、工具使用约束、scaffold 指令等组成模型初始消息。

对这个任务来说，模型可见的核心任务信息来自 `task.yaml` 的：

```text
issue
expected_files
visibility 中标记为 model_visible 的字段
```

模型不可见或不应该直接暴露的内容包括：

```text
fail_to_pass_tests
pass_to_pass_tests
gold_patch
decontamination 中 reward_only 的信息
```

这一点对训练和评测很重要：模型应该根据 issue 和可见仓库信息解决问题，而不是直接看到 evaluator-only 的答案或测试选择。

### 11. 创建 model client 和工具执行上下文

对应代码：

```text
src/repo_harness/evaluation/runner.py:375
src/repo_harness/evaluation/runner.py:377
```

创建模型客户端：

```python
model = create_model_client(config.model)
```

这次配置是：

```text
provider: deepseek
model_id: deepseek-v4-pro
```

所以它会创建 DeepSeek provider client。后续 provider 细节会在第 4 章展开讲，包括 raw request、raw response、OpenAI-compatible message format、工具 schema 如何传给 provider。

接着创建：

```python
tool_context = ToolExecutionContext(...)
```

这个对象把工具执行所需的上下文打包起来，包括：

```text
run_id 和 task_id
workspace_facade，也就是 Docker adapter
run_workspace，也就是 agent 可修改的工作区
artifact_writer，也就是 RunRecorder
permission_context，包括权限模式、网络策略和测试命令
verifier_feedback_facade，也就是 PytestVerifier
resolved_verifier_plan
tool output 限制
测试反馈策略
预算管理器
```

后续工具调用不是直接随便执行 shell 命令，而是通过 `ToolExecutor` 和 `ToolExecutionContext` 进入 workspace facade，再由 Docker adapter 执行或读写文件。

### 12. 进入 AgentLoop

对应代码：

```text
src/repo_harness/evaluation/runner.py:397
src/repo_harness/evaluation/runner.py:405
```

核心调用是：

```python
loop_state = AgentLoop(...).run(...)
```

这里进入多轮 agent loop。`run_task` 传进去的信息包括：

```text
initial_messages
tool_context
recorder
max_turns
context_config
budget_manager
task_deadline_monotonic
run_config_facts_ref
tool_schema_snapshot_ref
provider options
temperature / max_output_tokens / seed
request timeout
raw request logging policy
retry policy
```

这说明 `AgentLoop` 自己不负责重新理解任务来源、Docker 后端、baseline 或 final verifier。它只负责在已经准备好的上下文里进行：

```text
模型调用
工具调用解析
权限判断
工具执行
工具结果回流
上下文压缩
预算计数
停止条件判断
transcript 和 event 记录
```

这次真实 run 中，agent 的工具调用序列是：

```text
list_files
read_file calculator.py
read_file tests/test_calculator.py
edit_file calculator.py
run_tests
read_file calculator.py
```

最后：

```text
model_call_count: 6
tool_call_count: 6
test_run_count: 1
agent_stop_reason: final_answer
```

这些结果可以在 `run_metadata.json` 和 `events.jsonl` 中看到。

### 13. 捕获 final patch

对应代码：

```text
src/repo_harness/evaluation/runner.py:438
```

agent loop 结束后，代码调用：

```python
capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
```

这一步会从 agent workspace 中提取最终改动，写出：

```text
final.patch
final.diff
artifacts/*_final_patch.patch
artifacts/*_final_diff.diff
```

对训练和评测来说，这一步很关键。最终 verifier 验证的不是“当前 agent workspace 看起来通过了测试”，而是“从干净源码出发，应用 final.patch 后能不能通过验证”。

### 14. 运行 final verifier

对应代码：

```text
src/repo_harness/evaluation/runner.py:439
src/repo_harness/evaluation/runner.py:452
src/repo_harness/evaluation/runner.py:467
src/repo_harness/evaluation/runner.py:476
```

这里有三种主要路径：

```text
如果任务已经超时，生成 task_timeout 的 final verifier error result。
如果是 SWE-Bench-like 任务，调用 run_swebench_like_final_verifier。
否则创建 verification workspace，应用 final.patch，然后调用 PytestVerifier.run_final。
```

当前示例任务不是 SWE-Bench-like，所以走普通 strict patch replay：

```python
verification = adapter.create_verification_workspace(
    source_checkout=source,
    dependency_state=dependency_state,
    final_patch_path=capture.patch_path,
    setup_command=loaded.runnable_task.setup_command,
    recorder=recorder,
)
final_verifier = verifier.run_final(verification, resolved_plan, recorder)
```

这一步的语义是：

```text
从干净 source checkout 创建 verification workspace
恢复必要 dependency state
应用 agent 产生的 final.patch
运行 resolved verifier plan 中的测试
得到 formal final verifier result
```

这次 run 的 final verifier 结果是：

```text
accepted: true
pass_ratio: 1.0
fail_to_pass: 1/1
pass_to_pass: 2/2
command: pytest -q
```

结果写入：

```text
verifier.json
artifacts/*_final_verifier_result.json
events.jsonl 中的 verifier_final 事件
```

### 15. 计算 reward、metrics 和 run outcome

对应代码：

```text
src/repo_harness/evaluation/runner.py:517
src/repo_harness/evaluation/runner.py:541
src/repo_harness/evaluation/runner.py:542
src/repo_harness/evaluation/runner.py:548
src/repo_harness/evaluation/runner.py:573
```

`run_task` 会调用：

```python
reward = compute_reward_metadata(...)
```

reward 的输入包括：

```text
final_verifier
patch_stats
turn_count
tool_call_count
test_run_count
final_verifier_ref
final_patch_ref
final_diff_ref
events_ref
```

这说明 reward 是 final verifier 之后的元数据，不应该反过来影响 final verifier。V4 后续 export quality audit 也会专门检查：final verifier 是权威边界，reward 只能引用允许的字段路径，不能把 evaluator-only 信息污染进模型可见训练 payload。

这次 run 的 reward 关键值是：

```text
final_reward: 0.996
accepted_bonus: 1.0
fail_to_pass_score: 1.0
pass_to_pass_score: 1.0
patch_size_penalty: 0.004
invalid_for_training: false
```

`run_task` 随后会推导：

```text
final_verifier_status: accepted
run_outcome: success
```

并写入：

```text
reward.json
metrics.json
verifier.json
```

### 16. 写 summary、run_finished event 和 run_metadata

对应代码：

```text
src/repo_harness/evaluation/runner.py:576
src/repo_harness/evaluation/runner.py:595
src/repo_harness/evaluation/runner.py:612
src/repo_harness/evaluation/runner.py:624
src/repo_harness/evaluation/runner.py:626
```

最后阶段会生成：

```text
summary.md
run_finished event
run_metadata.json
```

`run_metadata.json` 是后续 inspect、export、acceptance 最常引用的 run 级摘要。它把关键结论集中起来：

```text
run_status: completed
run_outcome: success
final_verifier_status: accepted
reward_status: present
agent_stop_reason: final_answer
model_call_count: 6
tool_call_count: 6
test_run_count: 1
training_export_ready: true
```

最后：

```python
recorder.finalize_run(summary)
adapter.cleanup_workspaces()
return run_dir
```

`run_task` 返回的是本次 run 目录路径。

## 从产物反推一次 run 的阅读顺序

如果你以后拿到一个陌生 run 目录，不建议一开始就看完整 `events.jsonl`，因为它很长。可以按这个顺序读：

1. 先看 `summary.md` 和 `run_metadata.json`。确认任务是否完成、最终是否 accepted、agent 为什么停止、工具和模型调用次数是多少。
2. 再看 `task.yaml`。确认任务来源、issue、repo、fail-to-pass、pass-to-pass 和 visibility。
3. 再看 `run_config_facts.json`。确认 provider、model、Docker backend、工具协议、权限策略和 final verifier mode。
4. 再看 `baseline.json`。确认这个任务初始状态是否有效。
5. 再看 `transcript.jsonl`。理解 agent 每轮看到什么、想调用什么工具、工具返回什么。
6. 再看 `final.patch` 和 `final.diff`。确认最终改了什么。
7. 再看 `verifier.json` 和 `reward.json`。确认为什么这次算成功，以及 reward 是怎么来的。
8. 最后需要审计细节时再看 `events.jsonl`、`artifacts.json` 和 `container_execution_facts/manifest.json`。

## 本章核心理解

`run_task` 的职责可以概括成一句话：

```text
它把一个任务定义和一个运行配置，变成一次可执行、可审计、可验证、可导出的 agent 轨迹。
```

它和 `AgentLoop` 的边界是：

```text
run_task 负责端到端编排。
AgentLoop 负责多轮模型调用和工具调用。
```

也就是说：

```text
任务加载、工作区创建、baseline、上下文构造、provider client、final verifier、reward、metadata 都属于 run_task 的编排范围。
模型请求、工具请求、工具结果回流、上下文压缩、预算和停止原因属于 AgentLoop 的核心范围。
```

如果面试中被问到“你这个 harness 是怎么跑一个任务的”，不要只说“调用模型，然后跑测试”。更完整的回答应该是：

```text
RepoHarness 的单任务入口是 run_task。它先加载任务定义和运行配置，创建 Docker-based executable repository environment，然后物化源码并运行 baseline verifier，确认任务初始状态有效。之后它冻结工具 schema、环境指纹和 run_config_facts，创建 agent workspace，构造模型初始上下文，进入 AgentLoop。AgentLoop 中模型通过受控工具读文件、改文件和运行测试，所有请求、响应、工具结果都会写入 transcript、events 和 artifacts。agent 停止后，run_task 从 agent workspace 捕获 final.patch，再在独立 verification workspace 中做 strict patch replay，运行 final verifier。最后根据 final verifier、patch stats 和交互计数计算 reward，写出 metrics、run_metadata 和 summary。这样一次运行既能用于评测，也能作为训练轨迹导出前的可审计来源。
```

## 和 SWE-Bench-like / GitHub PR 任务的关系

本章示例任务是轻量 real repository fixture，不是 V4 的最终任务来源代表。它的价值是帮助先看清 `run_task` 主链路。

后续第 2 章会把任务来源切换到更成熟的 V4 语境：

```text
SWE-Bench-like 任务：
  重点看任务如何从固定子集构造，如何处理 fail-to-pass / pass-to-pass，如何做 final-only verifier，以及哪些信息是 evaluator-only。

GitHub PR / issue task freeze：
  重点看 V4 如何冻结真实 PR / issue 输入，如何生成 adapter-visible task input，如何隔离模型可见信息和 verifier / reward 信息。
```

所以本章和第 2 章的关系是：

```text
第 1 章：先学会 run_task 如何运行一个任务。
第 2 章：再学任务本身如何从 SWE-Bench-like 数据和 GitHub PR / issue 构造出来。
```

## 面试追问与推荐回答

### 问：为什么第一章不用 SWE-Bench 或 GitHub PR 任务，而是用 `realrepo_local_buggy_calculator`？

答：因为第一章的目标是讲清 `run_task` 的运行骨架，而不是先讲复杂任务来源。`realrepo_local_buggy_calculator` 很小，issue、源码、测试和 patch 都能直接看懂，但它仍然走真实 Docker backend、真实 provider、真实工具调用、baseline、final verifier、reward 和 artifact 记录。用它能先把链路看清楚。SWE-Bench-like 和 GitHub PR / issue 的构造细节会在下一章单独讲。

### 问：这个任务是 SWE-Bench 数据集里的任务吗？

答：不是。它来自项目内置的本地 fixed mirror：`tests/fixtures/repos/buggy_calculator`。源头输入是 `tests/fixtures/v3/real_repositories/real_repository_task_inputs.json`，经过 `build-v3-task-set` 生成 repository-level task。SWE-Bench-like 任务是另一条 adapter 链路，任务编号通常类似 `pytest-dev__pytest-8365` 或 `sympy__sympy-24909`。

### 问：为什么 baseline exit code 是 1，任务仍然 valid？

答：对于修复类任务，初始代码应该暴露缺陷，所以 fail-to-pass 测试在 baseline 阶段失败是合理的。RepoHarness 判断 baseline 是否 valid，不是简单看所有测试是否通过，而是看 fail-to-pass 测试是否确实失败、pass-to-pass 测试是否保持通过，以及测试解析和依赖状态是否可信。

### 问：`run_task` 和 `AgentLoop` 的边界是什么？

答：`run_task` 是端到端编排层，负责加载任务和配置、创建工作区、跑 baseline、构造上下文、创建模型客户端、运行 final verifier、计算 reward 和写 metadata。`AgentLoop` 是交互层，负责模型多轮调用、工具调用、工具结果回流、上下文管理、预算和停止条件。

### 问：为什么 final verifier 要用 strict patch replay？

答：因为不能只相信 agent workspace 当前状态。agent workspace 可能包含中间状态、缓存、副作用或未被正确记录的改动。strict patch replay 会从干净源码出发，应用 `final.patch`，再在独立 verification workspace 中运行 verifier。这样最终结果更接近可复核评测，也更适合训练数据审计。

### 问：`run_config_facts.json` 为什么重要？

答：训练轨迹不能只保存 transcript。还必须知道这条轨迹是在什么模型、什么工具 schema、什么 Docker backend、什么权限策略、什么 feedback policy、什么 verifier mode 下产生的。`run_config_facts.json` 把这些解析后的运行事实固化下来，后续 export 和 acceptance 可以引用它，而不是重新猜测当时的运行环境。

### 问：如果要一句话介绍这条链路，怎么说？

答：RepoHarness 的 `run_task` 会把一个任务定义和一个运行配置转成一次完整的 agent rollout：先验证初始任务有效，再让模型在受控工具和 Docker workspace 中修改仓库，随后捕获 final patch，在独立验证工作区中严格重放 patch 并运行 final verifier，最后生成 reward、metrics、transcript、events、artifacts 和 run metadata，形成可审计、可导出的训练轨迹。
