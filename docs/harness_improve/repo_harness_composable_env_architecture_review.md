# RepoHarness 可组合环境架构澄清与重构建议

本文面向当前的 RepoHarness + verl fully async RL 训练链路设计讨论。目标不是提出一个脱离当前代码的全新架构，而是把现有架构、外部建议、微软 MAI-Thinking-1 报告中的合成环境设计思想，以及 PrimeIntellect `research-environments` 的可组合环境思想放到同一张图里，判断当前项目是否应该调整，以及应该怎样调整。

本文的结论先放在前面：建议实施“可组合环境”方向，但不建议做一次性大重写。更合理的路线是先在现有 `run_episode(real_episode)` 主链路外层补一个薄的环境组合层，再逐步把 Stage 16G.3 从“窄命令 DSL”修正为“强隔离环境保护下的真实 Bash 风格工具表面”。当前已经完成的 Stage 16G.1 工具 profile、Stage 16G.2 结构化文件变更、训练投影、可见性扫描和 policy loss 守门员都应该保留，不能因为引入新架构而绕过。

需要特别说明：本文是 design-freeze 候选分析，不是已经替代 `55-stage-16g-3-execution-plan.md` 的正式阶段决策。是否把 Stage 16G.3 主路线从窄命令 DSL 调整为 SEE-gated Bash，还需要你确认后再写入正式 stage execution plan、acceptance summary 和 inspector 契约。本文的作用是把判断依据、风险边界和推荐实施方式讲清楚。

---

## 一、先用一句话重新定位当前项目

当前项目可以这样描述：

```text
RepoHarness 是一个面向软件工程智能体训练和评测的执行与审计 harness。

它把一个仓库任务变成可执行 workspace，向模型暴露受控工具，记录多步 agent 轨迹，
运行 verifier 得到奖励和评测结果，再把可训练的部分投影给 verl fully async RL。
```

更完整的闭环是：

```text
task
-> executable workspace
-> model-visible tools
-> agent loop
-> trajectory
-> verifier
-> reward / evaluation / export
-> verl async training interface
```

这里最容易混淆的一点是：RepoHarness 现在已经承担了很多“环境”责任，但它本质上更像一个 `Harness`，也就是“让 agent 在仓库里行动、记录轨迹、执行工具、保护边界”的执行接口。真正完整的训练环境还应该包含 task family、sandbox 规格、user simulator、permission policy、rubric、curriculum、trajectory lineage、staleness metadata 等对象。

因此，建议后续把项目的叙事从：

```text
RepoHarness = 一个 SWE RL 环境
```

调整为：

```text
RepoHarness = 可复用的 SWE agent execution harness
Composable SWE Environment = TaskSet + SandboxSpec + RepoHarness + PermissionSpec + UserSimSpec + Rubric + TrainingAdapter
```

这个调整不是改名字这么简单，而是让代码边界和训练边界更加清楚。

---

## 二、当前 RepoHarness 的真实架构

### 2.1 当前 canonical 主链路

根据当前 AGENTS.md、Stage 16G.2C 完成报告、代码导览和源码，当前训练链路的主入口已经不是旧的 `run_task(...)`，而是：

```text
RepoHarnessRuntime.run_episode(real_episode)
```

当前真实执行路径可以概括为：

```text
TaskDefinition / RunnableTask + RunConfig
-> EpisodeExecutionSpecBuilder
-> EpisodeExecutionSpec
-> RepoHarnessEpisodeRequest
-> RepoHarnessRuntime.run_episode(real_episode)
-> workspace snapshot / lease
-> AgentLoop
-> LLMGateway
-> ToolExecutor
-> model-visible tools
-> RunRecorder / trajectory / artifacts
-> final patch capture
-> verifier / reward boundary
-> RepoHarnessEpisodeResult
-> TrainingView
-> write_run_episode_compat_projection
-> 14 个公开投影文件 + manifest + provider_route_qualification
```

更具体一点：

```text
src/repo_harness/tasks/schemas.py
  TaskDefinition / RunnableTask / EnvironmentSpec

src/repo_harness/execution/builder.py
  把 task、run config、verifier、tool profile、feedback policy 绑定成 EpisodeExecutionSpec

src/repo_harness/execution/spec.py
  保存一次 episode 的公开执行事实和绑定摘要

src/repo_harness/rl/runtime.py
  run_episode(real_episode) 的主入口，负责 workspace 准备、agent loop、verifier、reward、结果组装

src/repo_harness/tools/minimal.py
  模型可见工具 registry 和 ToolExecutor 分发

src/repo_harness/tools/file_mutation.py
  结构化文件写入、patch、删除、移动、建目录的共享原子执行核心

src/repo_harness/workspace/adapter.py
  当前 real_episode 主路径使用的 local workspace adapter

src/repo_harness/workspace/docker_adapter.py
  已有 Docker backend 能力，但还不是 16G.3 所需要的每个 episode 一个长期隔离 SEE

src/repo_harness/verifier/runner.py
  pytest verifier 和 public/final verifier 入口

src/repo_harness/rl/training_view.py
  把 assistant token、tool observation、mask、logprob、span 投影成训练视图

src/repo_harness/evaluation/episode_projection.py
  写出 14 个公开文件，并执行 policy loss 资格守门
```

### 2.2 当前系统可以按四个平面理解

你给的图片和 `docs/harness_improve/env_design.md` 中的文章把环境系统分成四个平面：control plane、execution plane、verification plane、training interface。把这个框架映射到 RepoHarness 当前代码，可以看到当前项目已经有很多组件，但这些组件还没有被一个统一的环境组合对象串起来。

#### 2.2.1 Control Plane：目前很薄，还没有成为一等对象

外部文章里的 control plane 负责决定“生成什么环境、用什么难度、哪个模板版本、哪些样本有训练价值”。

当前 RepoHarness 里相关能力分散在：

```text
TaskDefinition / RunnableTask
RunConfig
Stage evidence summary
provider route policy
acceptance gate
training_design 文档
```

当前缺少的一等对象包括：

```text
TaskSet
Curriculum / Scheduler
EnvTemplateRegistry
SignalQualityTracker
```

这不是当前项目的致命问题，因为 Stage 16 还在补 harness 能力和训练链路守门。但如果要进入 Stage 17 真实数据冻结、Stage 20 warm-start 数据生成和 Stage 21 正式 RL，这一层必须逐步补上，否则后面会很难回答下面这些问题：

```text
这条 trajectory 来自哪个 task family？
这个 task family 的模板版本是多少？
当前样本难度是怎么安排的？
这个 verifier 信号是否稳定？
失败样本是环境质量问题、模型能力问题，还是工具能力问题？
哪些轨迹应该保留、降权、丢弃、重跑或者恢复？
```

#### 2.2.2 Execution Plane：当前能力最强，但“环境”和“harness”边界不够清楚

execution plane 负责把任务物化成可执行环境，并向 agent 暴露工具。

当前 RepoHarness 的强项就在这里：

```text
workspace snapshot / lease
LocalWorkspaceAdapter
DockerWorkspaceAdapter
dependency environment
ToolRegistry
ToolExecutor
structured file mutation
permission context
public environment prompt
diagnostic shell
RunRecorder
```

但是当前耦合点也主要在这里：

1. `RepoHarnessRuntime.run_episode(real_episode)` 当前默认是 local workspace snapshot + local process adapter，不是微软报告里那种每个 agentic task 一个新隔离容器的 SEE。
2. `DockerWorkspaceAdapter` 已经存在，但它的普通 `run_command` 更接近“每次命令一个 docker run”，还不是“一个 episode 一个持久隔离 sandbox instance”。
3. 当前模型可见的 `bash` 不是微软报告中的宽 Bash。它是受限命令工具，不支持管道、重定向、shell 组合等真实工程常见操作。
4. Stage 16G.3 旧计划中的 `run_public_command(command_profile_id, args)` 太像训练一个 RepoHarness 专用 DSL，而不是训练一个能迁移到 Claude Code / Codex / SWE-agent 风格环境的工程 agent。

这就是为什么 Stage 16G.3 的设计需要重新审视：真正的方向不是继续把 Bash 收窄，而是先把环境边界变强，然后在强边界内让模型使用更接近真实工程的 Bash。

#### 2.2.3 Verification Plane：已经有基础，但需要更明确地区分“反馈”和“最终评分”

verification plane 负责评估结果、打分、判断是否保留轨迹、运行测试。

当前 RepoHarness 里对应模块包括：

```text
ResolvedVerifierPlan
PytestVerifier
run_tests
final verifier
reward_boundary
patch_hygiene
outcome_policy
episode_projection provider_route_qualification
```

当前已经做得比较好的地方是：

1. public feedback 和 final verifier 有分层意识。
2. policy loss 守门员不会因为外部 provider 或 mock provider 的轨迹看起来成功就让它进入训练损失。
3. patch hygiene 会把 runtime-private、缓存、临时文件等不应该进入最终 patch 的内容过滤掉。
4. visibility 和 public projection 有多层 forbidden marker 扫描。

但如果 Stage 16G.3 改成更真实的 Bash，verification plane 需要进一步增强：

1. 最终评分最好在 clean checkout 上重放清洁后的 `final.patch`，而不是无条件信任 rollout container 的最终状态。
2. 需要把 public test observation、official feedback eligibility、diagnostic value、reward hacking suspicion 分开记录。
3. 如果模型修改了测试文件、测试配置、pytest 插件、依赖解析、git 历史或网络路径，不能简单地“照常评分”，应该进入隔离、降权、拒绝训练或人工复查路径。

#### 2.2.4 Training Interface：当前已经很接近目标，但缺少完整环境 lineage

training interface 负责把 rollout 转成 verl 可以消费的训练对象，并处理异步训练中的 staleness、policy version、rollout group metadata。

当前已有：

```text
TrainingView
GenerationRecord
response_mask
response_spans
response_logprobs
invalid_for_training
invalid_for_online_rl
provider_route_qualification
partial checkpoint / pause resume
async contracts
```

这是当前项目很重要的优势：你已经不是只在做一个“能跑 SWE-Bench 的脚本”，而是在做一个能和 fully async RL 训练接口对接的 harness。

但现在缺少一个更明确的 `TrajectoryArtifact` 或 `RolloutArtifact` 概念，把下面这些信息绑定在一起：

```text
env_id
taskset_id
template_version
sandbox_spec_id
harness_spec_id
rubric_version
policy_snapshot_id
rollout_start_global_step
rollout_finish_global_step
staleness
tool_surface_digest
permission_policy_digest
workspace_snapshot_digest
final_patch_digest
verifier_result_digest
reward_boundary_result
training_view_ref
```

这些信息现在不是完全没有，而是分散在 request、spec、recorder、projection manifest、stage evidence、run facts 等位置。短期可以接受，长期会影响异步训练的数据审计和实验复现。

---

## 三、模型建议到底是什么意思

`docs/harness_improve/harness_design_advice.md` 和 `docs/harness_improve/env_design.md` 的核心意思不是“把项目推翻重写”，而是提醒你：一个面向长期 RL 训练的 SWE 环境，不应该只看成一个 agent loop，也不应该只看成一个工具列表，而应该看成一个可组合、可版本化、可审计的环境流水线。

可以拆成三层理解。

### 3.1 第一层：RepoHarness 不应该等同于完整 Env

外部建议中的关键对象是：

```text
Task
TaskSet
SandboxTaskSet
SandboxSpec
Harness
Rubric
ComposableEnv
EnvironmentRuntime
SandboxInstance
AgentRollout
Validation / Scoring
Trajectory / Score / Artifact
```

映射到你的项目：

```text
Task
  单个仓库修复任务，对应 TaskDefinition / RunnableTask

TaskSet
  一组同源任务，例如 SWE-Bench-like、内部合成任务、真实 issue 任务、评测 worktree 同步任务

SandboxSpec
  执行镜像、CPU、内存、GPU、timeout、网络策略、挂载策略、依赖预装状态

Harness
  AgentLoop + ToolExecutor + context manager + permission gate + recorder

PermissionSpec
  模型能看什么、能写什么、网络是否开放、测试反馈是否允许、诊断 shell 是否允许

UserSimSpec
  用户交互模拟策略，例如无用户、固定追问、需求澄清、review 反馈

Rubric
  public tests、hidden tests、diff checker、状态检查、reward hacking monitor、trajectory judge

ComposableEnv
  TaskSet + SandboxSpec + Harness + PermissionSpec + UserSimSpec + Rubric 的组合

TrajectoryArtifact
  一次 rollout 的轨迹、patch、分数、环境 lineage、policy metadata、训练投影引用

VerlAdapter
  把 TrajectoryArtifact 转换成 verl fully async RL 可以消费的 rollout group / batch
```

所以建议的核心句子可以写成：

```text
RepoHarness 应该是 Harness 层，而不是所有环境概念的总和。
训练环境应该由 TaskSet、SandboxSpec、PermissionSpec、UserSimSpec、Rubric 和 RepoHarness 组合出来。
```

### 3.2 第二层：不要训练一个过窄的 RepoHarness 专用命令语言

Stage 16G.3 旧计划的方向是：

```text
run_public_command(command_profile_id, args)
run_project_test(selector)
scratch_python(code)
```

这个方向的优点是安全、可控、容易做 schema 验证。但它有一个很大的风险：模型学到的是 RepoHarness 私有 DSL，而不是常见 SWE agent 会用的工程动作。

微软 MAI-Thinking-1 报告中的 SWE agentic RL 工具表面更接近：

```text
Bash(command: string)
String replace editor
```

Bash 是完整 Linux shell 风格的命令字符串，可以使用管道、重定向、shell 组合和脚本。安全边界主要不靠把 Bash 解析成很窄的 allowlist，而靠 SEE，也就是隔离的 Sandbox Execution Environment：

```text
每个任务一个新隔离容器
默认无网络
依赖预装或通过受控缓存代理
隐藏测试不暴露
评分时执行 verifier
检测网络访问、git 历史搜索、测试篡改等 reward hacking 行为
```

这对 RepoHarness 的启发是：

```text
不要把 Bash 收窄到模型不会做真实工程。
应该把环境边界收紧到 Bash 做不了越界事情。
```

这句话非常重要。它不是说“开放 Bash 就安全了”，而是说安全责任应该从“模型工具 schema 层的字符串限制”下沉到“环境隔离、挂载策略、网络策略、评分重放、行为监控、训练资格守门”这些更可靠的边界上。

### 3.3 第三层：async RL 需要环境 lineage，而不只是 trajectory JSON

fully async RL 和普通离线评测的区别是：

```text
rollout 可能由较旧的 policy snapshot 生成；
执行过程可能持续较长时间；
verifier 可能延迟完成；
trainer 消费时 policy 已经更新了很多步；
同一条轨迹可能需要保留、降权、丢弃、恢复或重跑。
```

因此，一条训练轨迹不能只记录：

```text
prompt
response
reward
```

还需要记录：

```text
它来自哪个环境模板；
哪个 taskset；
哪个 sandbox 规格；
哪个 tool surface；
哪个 permission policy；
哪个 verifier / rubric 版本；
由哪个 policy snapshot 生成；
开始和结束时 trainer global step 是多少；
staleness 是否超过阈值；
是否有 reward hacking 可疑行为；
是否因为 provider route、缺少 logprob 或 verifier 问题而不能进入 policy loss。
```

你当前的 `TrainingView` 和 `episode_projection` 已经解决了“训练投影是否安全、是否有资格进入 policy loss”的核心问题。建议补的是更高一层的环境 lineage，而不是推翻已有投影。

---

## 四、我是否建议实施这些建议

建议实施，但要分阶段实施。

### 4.1 建议实施的理由

#### 理由一：它能把项目从“工具很多的 agent loop”提升成“可训练环境系统”

简历项目和长期个人项目最需要清楚表达你的系统边界。现在 RepoHarness 已经有很多硬能力，但如果对外讲成“我做了一个 SWE agent harness”，容易被理解成 SWE-agent、OpenHands 或 Codex 的简化复刻。

如果改成下面这种叙事，项目价值会更清楚：

```text
我做的是一个面向 fully async RL 的 SWE environment pipeline。
RepoHarness 是其中可复用的 agent execution harness。
任务集合、沙箱、权限、评分、轨迹投影和 verl 训练接口都被显式版本化和审计。
```

这个叙事更接近微软报告和 PrimeIntellect 可组合环境的方向，也更符合你当前已经完成的 Stage 13 到 Stage 16G.2 的成果。

#### 理由二：它能避免 Stage 16G.3 走向过窄 DSL

如果继续按旧 Stage 16G.3 计划做 `run_public_command(command_profile_id, args)`，短期很安全，但长期会让模型学习一套 RepoHarness 私有命令接口。

真实 SWE agent 通常需要：

```text
find / xargs / sed / awk / python scripts
pytest selector
git diff / git status
临时脚本
管道
重定向
多命令组合
项目自带工具
```

如果这些都被拆成大量结构化小工具，模型就会被训练成“会用 RepoHarness 表单”，而不是“会在真实仓库环境里工作”。

因此 Stage 16G.3 更适合改成：

```text
强隔离 sandbox + bash(command:string) + 内部命令分类 / test routing / reward hacking monitor
```

#### 理由三：它能降低后续扩展成本

如果 RepoHarness 继续把 task、sandbox、harness、rubric、training export 都混在一个 runtime 流程里，后续每新增一个维度都会出现乘法复杂度：

```text
新的 task family
新的 sandbox 类型
新的工具 profile
新的 verifier
新的 user simulator
新的 provider route
新的训练导出格式
```

可组合环境把这些变成加法：

```text
新增 TaskSet，不需要重写 Harness。
新增 HarnessSpec，不需要重写 TaskSet。
新增 Rubric，不需要重写 SandboxSpec。
新增 VerlAdapter 字段，不需要改变工具执行。
```

#### 理由四：它更适合 async RL 的数据审计

在 fully async RL 中，trajectory 的质量不仅由 reward 决定，还由生成时的 policy、执行时长、环境版本、staleness、verifier 可信度和 reward hacking 风险共同决定。

当前 `TrainingView` 已经守住了 policy loss 资格。下一步应该让 `TrajectoryArtifact` 把环境 lineage 也绑定进去，这样才能回答：

```text
这条样本为什么能训练？
它来自哪个环境版本？
它是否过期？
它是否只适合 eval，不适合 policy loss？
它是否因为工具越界或测试篡改被 quarantine？
```

### 4.2 不建议大重写的理由

虽然建议实施方向，但不建议立刻大改。

原因很实际：

1. Stage 16G.1 和 Stage 16G.2 刚完成，已经建立了工具 profile、结构化文件变更、projection linkage 和多层安全扫描。大重写会破坏刚建立的 acceptance 不变量。
2. 当前 `EpisodeExecutionSpec` 已经承担了很多“环境绑定事实”的功能，完全可以作为新 `RepoEnvSpec` 的底层兼容层，而不需要推翻。
3. 当前 `run_episode(real_episode)` 已经是 canonical 主入口。应该在它上方和旁边补环境组合对象，而不是再创造一个平行主入口。
4. 宽 Bash 的前提是强 sandbox。当前 real_episode 主路径还是 local process，所以不能先开放 Bash 再补隔离。
5. Stage 17、Stage 20、Stage 21 的闸门仍然是 false。当前应该继续做 16G.3 到 16G.6 的 harness 能力和安全边界，而不是把架构重构当成进入正式训练的理由。

---

## 五、建议后的目标架构

目标架构可以分成六层。这里不是要求马上全部实现，而是给出后续演进的稳定方向。

### 5.1 Task 和 TaskSet 层

职责：

```text
定义任务来自哪里、属于哪个任务族、如何生成、如何版本化、如何抽样。
```

建议对象：

```python
class TaskRef:
    task_id: str
    task_definition_sha256: str
    source_kind: str
    source_commit: str | None

class TaskSetRef:
    taskset_id: str
    taskset_version: str
    task_family: str
    generation_template_id: str | None
    generation_template_version: str | None
```

映射当前代码：

```text
TaskDefinition / RunnableTask -> TaskRef
stage workstream / generated tasks -> TaskSetRef
```

短期可以先只做 ref，不急着做完整任务生成器。

### 5.2 SandboxSpec 层

职责：

```text
定义执行环境如何隔离、使用什么镜像、允许多少资源、网络策略是什么、挂载什么、不挂载什么。
```

建议对象：

```python
class SandboxSpec:
    sandbox_spec_id: str
    backend: Literal["local_snapshot", "docker_see", "remote_see"]
    image: str | None
    network_policy: str
    cpu_limit: str | None
    memory_limit: str | None
    gpu_policy: str | None
    timeout_seconds: int
    mount_policy_id: str
    dependency_cache_policy: str
    persistence_scope: Literal["per_command", "per_episode"]
```

当前映射：

```text
tasks.EnvironmentSpec
SweBenchLikeEnvironmentSpec
workspace.backend_factory
workspace.docker_adapter
dependency_environment
RepoHarnessEpisodeRequest.network_policy
```

关键建议：

```text
16G.3 的宽 Bash 只能绑定 backend="docker_see" 或更强隔离后端。
backend="local_snapshot" 只能继续暴露受限命令工具，不能伪装成 SEE 已完成。
```

### 5.3 HarnessSpec 层

职责：

```text
定义 agent 如何行动：工具表面、system prompt、上下文策略、预算策略、recorder 策略、是否允许诊断工具。
```

建议对象：

```python
class HarnessSpec:
    harness_id: str
    harness_version: str
    tool_profile_id: str
    tool_registry_digest: str
    context_policy_id: str
    budget_policy_id: str
    recorder_policy_id: str
```

当前映射：

```text
stage16g_tool_profile.py
ToolRegistry
ToolExecutor
AgentLoop
public_environment.py
budget.py
RunRecorder
```

关键建议：

```text
RepoHarness 本身应该稳定为 Harness 层。
它不应该直接吞掉 TaskSet、SandboxSpec、Rubric 和 VerlAdapter 的所有职责。
```

### 5.4 PermissionSpec 和 UserSimSpec 层

职责：

```text
PermissionSpec 决定模型能看什么、能写什么、能不能联网、能不能拿测试反馈、能不能用诊断 shell。
UserSimSpec 决定是否存在用户模拟器，以及用户如何追问、澄清、拒绝或提供反馈。
```

建议对象：

```python
class PermissionSpec:
    permission_mode: str
    network_policy: str
    model_visible_path_policy_id: str
    test_feedback_policy: str
    diagnostic_tool_policy: str
    evaluator_material_policy: str

class UserSimSpec:
    user_simulator_id: str
    mode: Literal["none", "scripted", "llm_judge", "interactive"]
    max_user_turns: int
```

当前映射：

```text
PermissionContext
test_feedback_policy
visibility.py
public_environment.py
diagnostic_session.py
```

短期重点不是做复杂 user simulator，而是先让这些策略成为环境组合的一部分，避免散落在 request、spec、runtime、prompt 里。

### 5.5 RubricSpec 层

职责：

```text
定义最终如何评分、哪些反馈可以给模型、哪些检查只能在 evaluator 侧运行、哪些行为会导致训练无效。
```

建议对象：

```python
class RubricSpec:
    rubric_id: str
    rubric_version: str
    public_feedback_policy: str
    final_verifier_plan_digest: str
    patch_replay_policy: str
    reward_hacking_monitor_id: str
    accepted_policy_id: str
```

当前映射：

```text
ResolvedVerifierPlan
PytestVerifier
reward_boundary.py
patch_hygiene.py
outcome_policy.py
episode_projection.py 的 policy loss 守门
```

Stage 16G.3 后建议增加：

```text
ProjectTestRouter
CommandTrustClassifier
RewardHackingMonitor
CleanCheckoutPatchReplayVerifier
```

其中 `ProjectTestRouter` 不一定是模型可见工具。更好的方式是模型运行 `bash("python -m pytest ...")`，内部 router 识别它是项目测试命令，并记录：

```text
test_command_kind
test_selector
test_source_origin
official_feedback_eligible
diagnostic_value
public_feedback_visible
```

### 5.6 TrainingAdapter 和 TrajectoryArtifact 层

职责：

```text
把一次 rollout 变成可审计、可重放、可过滤、可训练或可评测的 artifact。
```

建议对象：

```python
class RepoEnvSpec:
    env_id: str
    env_version: str
    task_ref: TaskRef
    taskset_ref: TaskSetRef
    sandbox_spec: SandboxSpec
    harness_spec: HarnessSpec
    permission_spec: PermissionSpec
    user_sim_spec: UserSimSpec
    rubric_spec: RubricSpec

class TrajectoryArtifact:
    trajectory_id: str
    env_id: str
    episode_id: str
    policy_snapshot_id: str | None
    rollout_start_global_step: int | None
    rollout_finish_global_step: int | None
    staleness_steps: int | None
    final_patch_ref: str | None
    verifier_result_ref: str | None
    reward_boundary_ref: str | None
    training_view_ref: str | None
    invalid_for_training: bool
    invalid_for_online_rl: bool
```

当前映射：

```text
RepoHarnessEpisodeRequest
RepoHarnessEpisodeResult
TrainingView
generation_records
episode_projection manifest
RunRecorder artifacts
```

关键建议：

```text
不要把 VerlAdapter 写进 verifier 或 tool executor。
VerlAdapter 只消费 TrajectoryArtifact，并根据 policy route、logprob、mask、staleness、reward boundary 判断是否能进入训练。
```

---

## 六、Stage 16G.3 应该如何调整

### 6.1 旧 Stage 16G.3 计划的问题

旧计划的核心是：

```text
run_public_command(command_profile_id, args)
run_project_test(selector)
scratch_python(code)
```

它的好处是安全、结构化、容易做审计。但它不适合作为长期 SWE RL 主工具表面，因为：

1. 它把真实 shell 使用切成了很多表单字段，模型会学到非真实工程习惯。
2. 它把 pytest 这类项目测试从正常 shell 命令里拿出来，容易形成 RepoHarness 专用动作。
3. 它无法覆盖真实工程里常见的命令组合、临时脚本、管道、重定向和项目自带工具。
4. 它把安全责任放在命令 schema 和 allowlist 上，长期会非常难维护。

### 6.2 建议的新 Stage 16G.3 目标

建议把 Stage 16G.3 目标改成：

```text
SEE-gated Bash tool surface + internal project test routing + reward hacking monitor
```

也就是：

```text
模型可见层：
  bash(command: string)
  structured editor / apply_patch / write_file 等文件变更工具

环境保护层：
  每个 episode 一个隔离 sandbox
  默认无网络
  不挂载 host run directory、runtime-private artifact、隐藏评测材料
  stdout / stderr / exit code / duration / truncation 全量记录
  raw artifact 与 model-visible sanitized output 分离

内部解释层：
  ProjectTestRouter
  CommandTrustClassifier
  RewardHackingMonitor
  PatchHygiene
  CleanCheckoutPatchReplayVerifier

训练守门层：
  invalid_for_training
  invalid_for_online_rl
  provider_route_qualification
  staleness policy
  policy loss closed until hard gates pass
```

### 6.3 需要先解决的命名冲突

当前 `src/repo_harness/tools/minimal.py` 里已经有一个名为 `bash` 的工具，但它不是微软报告中的宽 Bash。它是受限命令工具。

因此 Stage 16G.3 需要先做命名决策。建议二选一：

```text
方案 A：
  保留工具名 bash，但通过 tool profile 明确区分：
    bash.mode = "restricted_diagnostic"
    bash.mode = "see_full_shell"

方案 B：
  把当前受限 bash 迁移为 repo_command 或 restricted_bash，
  把新 SEE Bash 命名为 bash。
```

我更建议方案 B。原因是长期对齐 Claude Code、Codex、SWE-agent 和微软报告时，`bash(command:string)` 这个名字最好留给真实 Bash 风格工具。当前受限工具继续叫 `bash` 会让文档、训练日志和评测报告都产生歧义。

短期为了不破坏已有 acceptance，可以先做兼容别名：

```text
旧 profile 仍然解析 bash -> restricted_bash handler
新 profile 才解析 bash -> see_bash handler
```

但文档和 evidence 里必须写清楚是哪一种。

### 6.4 宽 Bash 的硬门槛

在满足下面条件之前，不建议把 `bash(command:string)` 暴露给 `swe_public_core`：

```text
1. 每个 episode 都有新隔离 sandbox instance。
2. 默认无网络。
3. 容器内没有 provider secret、host secret、真实本机路径、runtime-private artifact 或 evaluator-only artifact。
4. sandbox 内不能看到 host 的 run directory、隐藏评测材料、参考答案、隐藏测试 patch、gold patch 或未来 git 历史。
5. CPU、memory、进程数、文件数、磁盘写入量、单命令超时和 episode 总超时都有硬限制。
6. Bash 对 workspace 的所有写入都能被 capture_final_patch、patch hygiene 和 mutation attribution 发现。
7. stdout / stderr / exit code / duration / truncation / command category 都被记录。
8. raw command artifact 和 model-visible output 严格分离，模型不能通过 artifact ref 读到 raw evaluator-only 内容。
9. `TrainingView` 中工具 observation 必须保持 mask=0，不能把环境输出误计入 policy token loss。
10. 运行最终 verifier 时使用 clean checkout 重放清洁 final.patch。
11. grading 前要重置或覆盖模型修改过的 visible tests；隐藏测试只在 grading 阶段注入。
12. 模型修改 visible test、测试框架、测试配置、依赖解析或 git 历史时，能够被 monitor 标记。
13. Python socket、curl、wget、包管理器联网、git remote 等网络访问 probe 在默认无网络模式下必须失败。
14. git future history scrub 是硬门槛，不能让模型通过本地 git 历史找到未来修复。
15. 任何可疑 reward hacking 行为都能让轨迹进入 quarantine、invalid_for_training 或至少 invalid_for_online_rl。
16. Stage 16G.3 仍然不打开正式 policy loss。
```

这些门槛里，最关键的是第一条和第十条。没有隔离 sandbox，就不应该开放宽 Bash；没有 clean checkout patch replay，就不应该把宽 Bash rollout 的最终 workspace 状态直接当成可信评分对象。这里列的是设计讨论中的验收方向，真正进入 Stage 16G.3 implementation plan 时，还应该把 `56-stage-16g-3-preplan-design-decisions.md` 中的 hard gate 转成机器可检查的 inspector 字段白名单和 source digest。

---

## 七、推荐实施路线

这里给出一条对当前项目风险较低的实施路线。它不是让你一次性完成全部内容，而是把后续阶段切成可以验收的增量。

### 阶段 0：写清楚设计决策，不改主链路行为

目标：

```text
冻结 Stage 16G.3 的新设计方向，明确旧 run_public_command DSL 计划不再作为主路线。
```

这一步必须先由你确认。确认前，它只能叫 design-freeze candidate，不能在文档里写成已经正式替代旧计划的事实。

建议产物：

```text
docs/agentic_RL/repo_harness_verl_workstreams/57-stage-16g-3-design-freeze.md
docs/harness_improve/repo_harness_composable_env_architecture_review.md
```

要写清楚：

```text
16G.3 主目标变成 SEE-gated Bash，而不是窄命令 DSL。
当前 local_process real_episode 不满足宽 Bash 条件。
Stage 16G.3 可以实现 schema、adapter、monitor、inspector，但不能打开 policy loss。
旧 run_tests 保留兼容，但 run_project_test 不作为默认模型可见主工具。
```

### 阶段 1：新增薄的环境组合 schema

目标：

```text
先建立对象边界，不急着改执行行为。
```

建议新增：

```text
src/repo_harness/environment/spec.py
```

或者为了避免和已有 `tasks.EnvironmentSpec` 混淆，可以命名为：

```text
src/repo_harness/composable_env/spec.py
```

建议包含：

```text
TaskRef
TaskSetRef
SandboxSpec
HarnessSpec
PermissionSpec
UserSimSpec
RubricSpec
RepoEnvSpec
TrajectoryArtifactRef
```

第一阶段只做两件事：

1. 从现有 `RunnableTask + RunConfig + ResolvedVerifierPlan + EpisodeExecutionSpec` 构造 `RepoEnvSpec`。
2. 把 `RepoEnvSpec` 的 digest 写入 `RepoHarnessEpisodeRequest` 或 `EpisodeExecutionSpec` 的公开事实中。

不要立刻迁移所有 runtime 参数，避免破坏已经稳定的主链路。

### 阶段 2：把当前 `bash` 工具语义拆清楚

目标：

```text
消除“bash 这个名字到底是受限命令还是完整 shell”的歧义。
```

建议做法：

```text
restricted_bash
  当前受限命令工具，继续使用 evaluate_model_bash_command 之类的安全策略。

see_bash
  新的 SEE 后端 Bash，schema 是 command:string，但只有 sandbox gate 通过时才能注册。

bash
  在旧 profile 中兼容映射到 restricted_bash。
  在新 SEE profile 中映射到 see_bash。
```

这一步还不一定真的开放 SEE Bash，只需要让 registry、profile delta 和文档能表达两种不同语义。

### 阶段 3：实现 SEE-equivalent execution substrate

目标：

```text
给宽 Bash 一个真正安全的执行底座。
```

建议方向：

```text
新增 EpisodeSandboxAdapter 或 SEEWorkspaceAdapter。
复用 DockerWorkspaceAdapter 的已有能力，但不要只做 per-command docker run。
每个 episode 创建一个持久 sandbox instance。
每次 bash tool call 是新 shell process，但文件系统 side effect 在本 episode 内持久。
episode 结束后销毁 sandbox。
```

要特别注意：

```text
run_dir 不应被完整挂载进 sandbox。
runtime-private artifact 不应被挂载。
隐藏评测材料不应被挂载。
网络默认关闭。
依赖缓存如果需要，必须是明确的只读或受控代理。
所有命令输出都需要 model-visible sanitized view 和 raw audit artifact 两套视图。
```

如果这一步没有完成，Stage 16G.3 inspector 应该明确输出：

```text
see_bash_enabled = false
wide_bash_model_visible = false
stage16g3_policy_loss_allowed = false
```

这样比“本地 subprocess 先跑起来再说”更安全，也更符合 16G.2 建立的安全风格。

### 阶段 4：内部 ProjectTestRouter，而不是默认模型工具

目标：

```text
让模型通过 Bash 运行真实项目测试，但内部仍能识别测试反馈的可信度。
```

建议行为：

```text
模型调用：
  bash("python -m pytest tests/unit/test_x.py -q")

内部记录：
  command_category = "project_test"
  test_runner = "pytest"
  selector = "tests/unit/test_x.py"
  feedback_visibility = "public"
  official_feedback_eligible = true 或 false
  diagnostic_value = "high"
```

这比给模型一个 `run_project_test(selector)` 更接近真实工程，同时又保留了训练审计需要的结构化事实。

现有 `run_tests` 可以继续保留，作为：

```text
兼容工具
最小 public feedback 工具
safe_structured_only profile 的默认测试工具
```

但它不应该成为长期 SWE RL 主路线中的唯一测试入口。

### 阶段 5：新增 reward hacking monitor 和 clean checkout verifier

目标：

```text
宽 Bash 下，不靠禁止一切风险动作来安全，而靠检测、隔离、降权和最终重放评分来安全。
```

至少要检测：

```text
网络访问尝试
host path 探测
runtime artifact 探测
隐藏评测路径探测
git 未来历史或参考答案搜索
测试文件篡改
测试框架或配置篡改
依赖解析或 monkey patch 行为
过量资源消耗
非预期后台进程
```

最终 verifier 建议改成：

```text
1. 从原始任务状态创建 clean checkout。
2. 应用 patch hygiene 后的 final.patch。
3. 重置或覆盖 public visible tests 中被模型修改过的部分。
4. 仅在 grader 侧注入隐藏测试或隐藏评测逻辑。
5. 运行 final verifier。
6. 把结果送入 reward boundary。
```

这里要注意：微软报告中描述的是 grader 在同一 SEE session 里执行测试，但你的项目如果开放更宽 Bash，并且当前已经有 patch hygiene 和 projection safety 的设计传统，那么 clean checkout replay 是更稳妥的本地适配方案。

### 阶段 6：把 TrajectoryArtifact 变成训练消费的主对象

目标：

```text
让 verl 训练消费的是带环境 lineage 的 artifact，而不是散落的 result 字段。
```

建议 `TrajectoryArtifact` 绑定：

```text
RepoEnvSpec digest
EpisodeExecutionSpec digest
tool_registry_digest
policy_snapshot_id
generation_records
TrainingView
reward_boundary result
final patch refs
verifier result refs
staleness metadata
invalid flags
quarantine reasons
```

`write_run_episode_compat_projection(...)` 可以继续存在，作为兼容投影。新的 artifact 层应该调用它，而不是替代它。

第一版 `TrajectoryArtifact` 更准确地说应该是 lineage manifest 或 wrapper。它不能绕开 `RepoHarnessEpisodeResult`、`TrainingView` 和 `write_run_episode_compat_projection(...)` 另建训练入口，也不能让后续实现者重新制造一条和 `run_episode(real_episode)` 平行的训练主链路。它的职责是把已经存在的 result、projection、artifact、policy metadata 和 environment digest 绑定得更清楚。

### 阶段 7：最后再补 control plane

目标：

```text
进入 Stage 17 / 20 / 21 前，建立任务抽样、难度调度、模板版本和信号质量追踪。
```

建议对象：

```text
TaskSetRegistry
EnvTemplateRegistry
CurriculumScheduler
SignalQualityTracker
Replay / Resume Queue
```

这一层可以晚一点做，因为现在最紧急的是 16G.3 的执行环境和 Bash 工具表面。但不能完全不做，否则正式 RL 数据会缺少足够的来源审计。

---

## 八、不建议做的事情

### 8.1 不建议现在直接重写 runtime

`RepoHarnessRuntime.run_episode(real_episode)` 已经是当前 canonical 入口。应该保留它，并逐步让它接受更明确的 `RepoEnvSpec` 或从 `EpisodeExecutionSpec` 反推出 `RepoEnvSpec`。

不要再做一个平行的主入口，否则会重复 Stage 16F 已经解决过的新旧入口分裂问题。

### 8.2 不建议把宽 Bash 绑定到 local_process

当前 real_episode 主路径使用 local workspace snapshot 和 local process adapter。这个路径不应该承载宽 Bash。

如果为了开发方便需要本地 smoke，可以明确叫：

```text
allow_unisolated_local_bash_for_tests
```

并且只允许在测试中使用，公开 inspector 必须显示：

```text
production_see_gate = false
policy_loss_allowed = false
```

### 8.3 不建议移除结构化文件变更工具

即使未来有宽 Bash，也不应该删除：

```text
write_file
apply_patch
delete_file
move_file
mkdir
```

原因是：

1. 结构化文件工具更适合精确记录编辑意图。
2. `file_mutation.py` 已经有 preflight、snapshot、apply、rollback 的原子语义。
3. 结构化编辑可以和 Bash 互补，不是替代关系。
4. 对一些 profile，例如 `safe_structured_only`，结构化编辑仍然是更安全的默认工具。

### 8.4 不建议把 `run_project_test` 作为长期默认模型可见工具

`run_project_test` 可以作为内部 router 或兼容工具存在，但长期主路线应该让模型通过 Bash 运行项目测试。

更推荐：

```text
模型可见：
  bash("python -m pytest ...")

内部记录：
  ProjectTestRouter 识别并标注测试命令
```

这样既真实，又可审计。

### 8.5 不建议用 LLM monitor 代替硬边界

微软报告提到可以使用 LLM monitor 发现 reward hacking，但这不能替代：

```text
网络隔离
挂载隔离
隐藏材料不暴露
git 历史清理
clean checkout patch replay
规则型 monitor
policy loss 守门
```

LLM monitor 可以是后续增强，不应该是第一道防线。

### 8.6 不建议在 16G.3 打开正式 policy loss

Stage 16G.3 的目标应该是工具能力和环境隔离，不是正式训练放量。即使看到某些 rollout 通过了 verifier，也不应该让它进入 policy loss，除非：

```text
route == "verl"
llm_gateway_route == "verl"
logprob provenance 完整
invalid_for_training == false
invalid_for_online_rl == false
SEE gate 通过
reward hacking monitor 未触发高风险
staleness policy 通过
```

当前阶段最稳妥的结论仍然是：

```text
stage17b_real_data_freeze_allowed = false
stage20_warm_start_data_generation_allowed = false
stage21_formal_rl_allowed = false
```

---

## 九、把当前模块映射到建议架构

| 建议架构对象 | 当前已有对应 | 当前缺口 | 建议动作 |
| --- | --- | --- | --- |
| `Task` | `TaskDefinition`、`RunnableTask` | 基本够用 | 保留，补 `TaskRef` |
| `TaskSet` | stage 文档、任务来源约定 | 不是一等对象 | 增加 `TaskSetRef` 和后续 registry |
| `SandboxSpec` | `EnvironmentSpec`、`SweBenchLikeEnvironmentSpec`、workspace backend | 没有统一 SEE spec | 新增 `SandboxSpec`，明确 local 与 SEE 差异 |
| `Harness` | `AgentLoop`、`ToolExecutor`、`ToolRegistry`、`RunRecorder` | 与 env/runtime 概念混在一起 | 定义 `HarnessSpec`，让 RepoHarness 作为 harness 层 |
| `PermissionSpec` | `PermissionContext`、visibility、feedback policy | 分散在 request/spec/prompt/runtime | 收敛成环境组合的一部分 |
| `UserSimSpec` | 基本没有 | 缺用户模拟维度 | 短期 `mode="none"`，保留扩展位 |
| `Rubric` | `ResolvedVerifierPlan`、`PytestVerifier`、`reward_boundary` | 缺 clean replay 和 monitor spec | 增加 `RubricSpec` |
| `EnvironmentRuntime` | `RepoHarnessRuntime.run_episode` | 当前默认 local_process，不是 SEE runtime | 保留入口，增加 SEE backend |
| `SandboxInstance` | Docker diagnostic container、workspace lease | 缺每 episode 持久容器 | Stage 16G.3A 实现 |
| `TrajectoryArtifact` | `RepoHarnessEpisodeResult`、`TrainingView`、projection manifest | lineage 分散 | 新增 artifact ref 或 manifest 层 |
| `VerlAdapter` | `TrainingView`、`episode_projection`、async contracts | staleness/lineage 还不完整 | 让 projection 消费 `TrajectoryArtifact` |

---

## 十、建议的最终系统图

可以把目标架构想成这样：

```text
Control Plane
  TaskSetRegistry
  CurriculumScheduler
  EnvTemplateRegistry
  SignalQualityTracker
        |
        v
RepoEnvSpec
  TaskRef
  TaskSetRef
  SandboxSpec
  HarnessSpec
  PermissionSpec
  UserSimSpec
  RubricSpec
        |
        v
Environment Runtime
  materialize workspace
  create SEE sandbox instance
  expose RepoHarness tool surface
  run AgentLoop
        |
        v
Verification Plane
  ProjectTestRouter
  RewardHackingMonitor
  CleanCheckoutPatchReplayVerifier
  RewardBoundary
        |
        v
TrajectoryArtifact
  trajectory
  patch
  score
  environment lineage
  policy metadata
  staleness metadata
  invalid flags
        |
        v
Training Interface
  TrainingView
  provider_route_qualification
  verl rollout group / batch
```

这张图里，RepoHarness 的核心位置是：

```text
Environment Runtime 中的 Harness 层
```

而不是：

```text
所有层的混合体
```

这个边界清楚以后，后续你可以很自然地支持：

```text
同一 TaskSet + 不同 Harness
同一 Harness + 不同 TaskSet
同一任务 + 不同 SandboxSpec
同一 rollout + 不同 Rubric
同一 TrajectoryArtifact + eval-only 或 trainable 两种消费路径
```

---

## 十一、对当前项目最重要的设计判断

### 判断一：当前架构不需要推倒重来

当前架构的核心链路是合理的：

```text
run_episode(real_episode)
EpisodeExecutionSpec
ToolExecutor
RunRecorder
TrainingView
episode_projection
policy loss guard
```

这些都应该保留。

真正需要调整的是：

```text
把环境组合对象补出来；
把 sandbox SEE 边界补强；
把受限 bash 和真实 bash 分清；
把 verifier 从 rollout 状态信任改成 clean patch replay；
把 trajectory lineage 提升为一等训练数据事实。
```

### 判断二：Stage 16G.3 旧计划需要改方向

旧计划可以保留一部分内部能力，例如 command classification、test routing、artifact logging。但模型可见工具表面不建议以 `run_public_command(command_profile_id, args)` 为主。

更好的方向是：

```text
先做 SEE gate；
再暴露 bash(command:string)；
项目测试通过内部 router 标注；
reward hacking 通过 monitor 和 verifier replay 防护；
policy loss 继续关闭。
```

### 判断三：宽 Bash 是目标，不是当前立即可开的开关

由于当前 real_episode 主路径还不是每 episode 隔离 SEE，宽 Bash 只能作为 gated capability 出现在设计和 schema 中，不能默认开放到 `swe_public_core`。

正确的 acceptance 语义应该是：

```text
实现了 SEE 审计和 hard gate，才允许 wide_bash_model_visible = true。
没有通过 SEE gate，就只能显示 planned_not_enabled 或 diagnostic_only。
```

### 判断四：训练资格守门必须继续保守

当前项目非常重要的优势是没有把“能跑通”误认为“能训练”。这个原则要继续保留。

即使 Stage 16G.3 后宽 Bash 可用，也不意味着自动打开 Stage 17、Stage 20 或 Stage 21。正式训练还需要：

```text
真实 verl route
完整 token / logprob provenance
环境 lineage
staleness policy
reward hacking monitor
clean verifier replay
数据 split freeze
acceptance inspector
```

---

## 十二、建议下一步最小行动

如果现在要把这个设计真正推进，我建议下一步只做四件事：

1. 新增一份 Stage 16G.3 design freeze 文档，明确旧 DSL 计划被修正为 SEE-gated Bash 路线。
2. 新增薄的 `RepoEnvSpec` / `SandboxSpec` / `HarnessSpec` / `RubricSpec` schema，不改变现有 runtime 行为。
3. 写一个 `inspect-stage16g3-design-freeze` 或类似 inspector，检查：
   ```text
   当前是否错误开放 wide bash；
   当前是否错误允许 policy loss；
   当前是否明确区分 restricted bash 和 SEE bash；
   当前是否记录 sandbox hard gate；
   当前是否声明 Stage 17 / 20 / 21 仍然关闭。
   ```
4. 开始实现 SEE backend capability audit，而不是先写 `run_public_command` DSL。

这四步的好处是风险低、能和当前 acceptance 风格一致，也能把项目架构叙事立刻变清楚。

---

## 十三、本文参考依据

本地项目依据：

```text
AGENTS.md
docs/harness_improve/harness_design_advice.md
docs/harness_improve/env_design.md
docs/harness_improve/bash_tool_advice.md
docs/harness_improve/main_20260602_2.pdf
docs/agentic_RL/repo_harness_verl_workstreams/55-stage-16g-3-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/56-stage-16g-3-preplan-design-decisions.md
docs/agentic_RL/code_guide_index.html
docs/agentic_RL/code_guide_t5_execute.html
docs/agentic_RL/code_guide_t8_projection.html
docs/agentic_RL/code_guide_side_safety.html
```

本地源码依据：

```text
src/repo_harness/rl/runtime.py
src/repo_harness/rl/episode.py
src/repo_harness/rl/training_view.py
src/repo_harness/rl/visibility.py
src/repo_harness/evaluation/episode_projection.py
src/repo_harness/execution/spec.py
src/repo_harness/execution/builder.py
src/repo_harness/tools/minimal.py
src/repo_harness/tools/file_mutation.py
src/repo_harness/workspace/adapter.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/workspace/patch_hygiene.py
src/repo_harness/verifier/runner.py
src/repo_harness/tasks/schemas.py
src/repo_harness/tasks/public_environment.py
```

外部参考：

```text
PrimeIntellect research-environments:
https://github.com/PrimeIntellect-ai/research-environments

Prime Intellect Verifiers environments:
https://docs.primeintellect.ai/verifiers/environments
```

其中 PrimeIntellect `research-environments` README 中的可组合架构明确写到，环境由可复用的 `TaskSet` 和 `Harness` 通过 `ComposableEnv` 组合出来。Prime Intellect Verifiers 文档也强调环境由 taskset、harness、工具、沙箱、上下文管理和评分规则组成。这一点和本文建议的 RepoHarness 目标架构一致，但本文没有照搬其代码结构，而是按当前 RepoHarness 的 Stage 16G 进度和 verl fully async RL 训练链路做了适配。
