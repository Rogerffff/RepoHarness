根据 2026-06-04 的文档、你上传的架构图，以及微软 2026-06-02 的 MAI-Thinking-1 报告，我的建议是：**你的项目应该从“RepoHarness + verl 的 SWE RL 工具链”升级为“Composable Environments + RepoHarness 作为第一个 SWE 环境族 + verl 作为训练消费端”的架构。**

但我不建议你现在就做“各行各业通用 agent 平台”。最合理的路线是：

```text
短期：
  以 SWE 为主战场，把 RepoHarness 重构成可组合环境系统的第一个 domain。

中期：
  加 user simulator / approver simulator，训练真实用户约束下的软件工程能力。

长期：
  再扩展到 mocked enterprise tool-use 环境，例如 ticket、inventory、calendar、email、booking、CRM。
```

一句话压缩：

> **RepoHarness 不应该只是一个 SWE-bench 风格 issue runner；它应该变成一个训练/评测/模拟/服务一致的 interactive agent environment runtime。**

---

## 1. 你的直觉是对的：真实 agentic RL 不只是 SWE-bench issue solving

微软报告把 agentic RL 分成两个大类：一类是 SWE，需要模型在真实代码库容器中读写文件、运行 shell、检查 repo state；另一类是 general tool use，需要模型在有初始状态、工具 schema、grader 的交互式状态环境中调用工具，场景包括 inventory management、scheduling、report creation、customer support 等企业场景。微软还说这些 general tool-use 环境通常有大量工具，单个环境甚至超过 50 个工具，用来训练模型在复杂工具集合中选择合适工具。([Microsoft AI][1])

这说明你现在的判断是正确的：**如果目标是 Claude Code / Codex 这类真实 agent，训练环境不能只覆盖“给一个 issue，修一个 patch，跑 hidden tests”。** 真实任务里会有用户反馈、权限、工具选择、长程状态、隐藏约束、部分验证、外部系统状态、成本/延迟/用户负担等维度。

但微软的做法也给了一个边界：他们没有把 SWE 和 general tool-use 混成一坨，而是用同一个 multi-step agentic loop 支持不同环境类型。SWE 环境是 repo/container/test；general tool-use 环境是 mocked backend、seeded database、tool schema、initial state、grader。([Microsoft AI][1])

所以你的项目应该学的是：

```text
同一套 agent loop / trajectory / sandbox / verifier / training interface，
支持多个 environment family。
```

而不是：

```text
把 SWE、订票、邮件、客服、浏览器、MCP 全部塞进一个 RepoHarness 类里。
```

---

## 2. 当前 RepoHarness 是否把太多东西写在一起了？

**从训练环境架构角度看，是的。**

你当前的 RepoHarness 已经在做这些事情：

```text
task definition
tool surface
sandbox / workspace
command policy
file mutation
public tests
hidden verifier
TrainingView projection
run_episode
evidence / inspector
verl linkage
```

这些都重要，但如果全部缠在一个 SWE-specific runner 里，后续会出现三个问题：

第一，**很难加新环境族**。例如你想加一个“mocked Jira + GitHub + Slack”的任务，如果 Task、Harness、Sandbox、Rubric、TrainingView 都绑定在 RepoHarness SWE 逻辑里，就会不断复制 runner。

第二，**很难做 user simulator**。真实用户交互不是 SWE grader 的一部分，也不完全是 tool 的一部分；它应该是环境状态和 harness loop 中的独立参与者。

第三，**很难接 async RL**。你上传的 synthetic environment 文档说得很准确：一旦进入长程 tool-use / coding / browser / stateful workflow，训练对象不再是一个 sample row，而是带状态、工具、约束、验证、版本和 lineage 的 environment artifact；控制面、执行面、验证面、训练接口会以不同速度运行，必须解耦。

Cursor Composer 2 也是这个方向：它的 RL infrastructure 分成 training、environments、inference、evaluations 四个解耦服务；stateful codebase environments 是一等对象；长 rollout 会做 policy-aware checkpointing，并依赖环境状态快照来恢复。([arXiv][2])

所以结论是：

```text
不要把 RepoHarness 删除重写；
但要把它从“一个 monolithic SWE runner”
重构成“ComposableEnv 框架下的 SWE environment family”。
```

---

## 3. 建议采用 Composable Environments 抽象

你图里的抽象非常合理：

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

我建议你直接采用这套概念，但先做最小版本。

### 核心对象可以这样定义

```python
@dataclass
class Task:
    id: str
    prompt: str
    metadata: dict
    hidden_state_ref: str | None = None

@dataclass
class TaskSet:
    id: str
    domain: str
    tasks: list[Task]
    generator_version: str
    difficulty: str

@dataclass
class SandboxSpec:
    image: str
    cpu: int
    memory_gb: int
    gpu: str | None
    timeout_sec: int
    network_policy: str
    mounts: list[str]

@dataclass
class HarnessSpec:
    id: str
    tool_surface: str
    prompt_template: str
    permission_policy: str
    user_simulator: str | None = None

@dataclass
class Rubric:
    id: str
    graders: list[str]
    reward_components: list[str]
    keep_discard_policy: str

@dataclass
class ComposableEnv:
    taskset: TaskSet
    sandbox: SandboxSpec
    harness: HarnessSpec
    rubric: Rubric
```

这不是为了代码优雅，而是为了让你后续可以自由组合：

```text
同一个 TaskSet:
  可以用 Bash+Editor harness
  也可以用 ClaudeCode-like harness
  也可以用 strict structured harness

同一个 Harness:
  可以跑 SWERepairTaskSet
  可以跑 InteractiveRefactorTaskSet
  可以跑 ToolUseInventoryTaskSet

同一个 Rubric:
  可以评 hidden tests
  可以评 permission violation
  可以评 user burden
  可以评 final state database consistency
```

你上传的 composable environments 文档也强调，Task、TaskSet、SandboxTaskSet、Harness、SandboxSpec、ComposableEnv 的拆分价值在于：任务定义、sandbox requirements 和 agent execution 可以独立变化；如果 tasks、harnesses、sandboxes、rubrics 可组合，synthetic environment generation 就从模板扩展变成了环境工厂。

---

## 4. 四个 plane 应该如何落到你的项目里？

你上传的图片里有 control plane、execution plane、verification plane、training interface。这个非常适合你的 RepoHarness + verl 项目。

### 4.1 Control plane：决定生成什么环境

职责：

```text
选择 task family
选择 difficulty
选择 harness profile
选择 sandbox spec
选择 rubric
记录 template version
记录 signal quality
做 curriculum / difficulty scheduling
```

对应模块：

```text
repoharness/envs/control/
  registry.py
  scheduler.py
  difficulty.py
  template_versions.py
  signal_quality.py
```

短期不需要复杂调度，先实现：

```text
固定 taskset + fixed difficulty + fixed harness
```

但数据结构要留好：

```json
{
  "env_id": "interactive_refactor/payments_042",
  "taskset_id": "interactive_refactor_v0",
  "template_version": "v0.1",
  "difficulty": "medium",
  "harness_id": "swe_bash_editor_v1",
  "rubric_id": "hidden_tests_permission_v1"
}
```

### 4.2 Execution plane：真正物化环境

职责：

```text
初始化 repo / database / mock backend
启动 sandbox
暴露工具 surface
执行 agent rollout
记录事件
保存状态快照
```

对应模块：

```text
repoharness/runtime/
  environment_runtime.py
  sandbox_instance.py
  rollout_runner.py
  tool_surface.py
  state_snapshot.py
```

这部分对应微软的 SEE。微软报告里每个 agentic task 都有一个 SEE session 执行工具，工具输出进入上下文，最终 rollout 和 SEE 一起送到 grader；SEE 是 fresh isolated container，任务结束后销毁，默认网络隔离。([Microsoft AI][1])

### 4.3 Verification plane：评估结果和轨迹

职责：

```text
运行 hidden tests
运行 public/partial checks
检查 forbidden diff
检查 permission violations
检查 user constraints
LLM monitor / AI judge
决定 keep / discard / quarantine
```

对应模块：

```text
repoharness/verification/
  rubric.py
  graders.py
  monitors.py
  test_reset.py
  keep_discard.py
```

微软的 SWE 防 reward hacking 也正是在这里处理：网络搜索、local git history search、test tampering、LLM monitor、test reset、hidden test only applied at grading。([Microsoft AI][1])

### 4.4 Training interface：把环境轨迹变成 verl 可消费样本

职责：

```text
rollout group batching
reward components
trajectory artifact
policy_version
staleness tag
environment_version
tool_schema_version
sandbox_digest
verifier_digest
```

对应模块：

```text
repoharness/train/
  verl_adapter.py
  rollout_group.py
  reward_packager.py
  staleness.py
  training_view.py
```

你上传的 synthetic environment 文档说得很重要：async RL 下，环境实例可能在 policy version 114 生成、在 121 才被验证；训练系统不应该只看到 solved/failed，而应该看到带 state lineage、verifier outputs、tool traces、checkpoint ancestry 的 versioned interaction artifact。

---

## 5. User simulator 是否应该加？

**应该加，但要先限定在 SWE，而不是马上做所有行业。**

我建议你先做：

```text
Permissioned Interactive SWE UserSim
```

不要一开始做：

```text
通用订票 / 邮件 / 客服 / 日程 / 购物全场景 simulator
```

原因是 SWE 有天然可验证性：

```text
repo state 可重置
hidden tests 可做 reward
diff 可审计
permission violation 可检测
sandbox 成熟
任务容易开源和展示
```

你上传的项目定位文档也建议：不要做完整 Claude Code clone，不要试图覆盖各行各业；以 SWE 为第一个 domain，把项目定位成 training-serving consistent 的 permissioned interactive SWE agent runtime，并用 user/approver simulator、replayable trajectories、verl multi-turn rollout 展示价值。

### User simulator 的正确形态

不要只写一个 prompt：

```text
你是用户，请和 agent 对话。
```

这会不可控，也很难评估。

应该做成：

```text
结构化 hidden state + LLM natural-language surface
```

例如：

```yaml
UserSimState:
  true_goal: "refactor payments retry logic"
  hidden_constraints:
    - "do not modify refunds module"
    - "do not change public API"
    - "do not delete existing tests"
    - "production config must not be touched"
  expertise: "engineering_manager"
  patience: 0.6
  approval_policy:
    read_repo: allow
    edit_src_payments: approve_if_plan_clear
    edit_refunds: deny
    modify_tests: require_explanation
    run_public_tests: allow
    network: deny
```

agent 可以问：

```text
“我需要修改 src/payments 和 tests/payments，可以吗？”
```

simulator 返回：

```json
{
  "decision": "approve_with_conditions",
  "granted_scopes": ["src/payments/**", "tests/payments/**"],
  "conditions": [
    "不要改 refunds",
    "不要改 public API",
    "最终展示 diff 和测试结果"
  ]
}
```

这个设计直接对应真实 Claude/Codex 的 approval + sandbox 思想。Codex 官方文档明确区分 sandbox 和 approval：sandbox 是技术边界，approval 决定何时停下来询问；在你的 RL 训练里没有真人，所以 approval 可以由 deterministic user/approver simulator 替代。([OpenAI开发者][3])

---

## 6. User simulator 的训练价值是什么？

它可以训练普通 SWE-bench 没法训练的能力：

```text
什么时候应该澄清需求
什么时候应该请求权限
如何请求最小权限
被拒绝后如何恢复
如何避免触碰禁区
如何减少用户负担
如何在最终回答中准确说明验证情况
如何处理用户中途新增约束
```

这些正是实际 Claude Code / Codex 使用中会出现的问题。Codex 官方把 harness 描述为协调 user、model、tools 的 agent loop；Codex App Server 还强调 thread lifecycle、event history、tool execution/extensions、MCP/skills 参与同一 policy model。([OpenAI][4])

Claude Code SDK 也显示其真实能力不只是 Bash 和文件编辑，还包括 hooks、subagents、MCP、permissions、sessions、Monitor、WebSearch、WebFetch、AskUserQuestion 等工具/机制。([Claude API Docs][5])

所以 user simulator 不是装饰，它是把训练从：

```text
solve issue
```

升级到：

```text
solve user task under constraints and permissions
```

---

## 7. 是否应该做非 SWE 的工具使用环境？

**可以，但作为第二阶段，不要抢在 SWE permissioned env 之前。**

微软 general tool-use 的 synthetic env 设计非常值得你后续参考：它们生成 self-contained closed-world environments，包含 seeded databases、tool definitions、verifiable tasks；流程分三步：environment bootstrapping、task creation、verification and refinement；还会生成 environment-specific personas，并加入“有工具描述但不需要用工具”的任务来缓解过度调用工具。([Microsoft AI][1])

你的长期路线可以是：

```text
Domain 1:
  SWERepairEnv / InteractiveRefactorEnv

Domain 2:
  MockEnterpriseToolUseEnv
  - seeded database
  - fake Jira / Slack / Calendar / Email / Inventory APIs
  - task: schedule, update ticket, summarize report, book resource
  - grader: final DB state + tool usage + final answer

Domain 3:
  Browser / computer-use-like env
  - later
```

但是短期不要真的做 Gmail、订票、邮件真实服务。应该做 **closed-world mocked backend**，因为微软也是用 mocked backends 模拟 realistic API/MCP behavior，而不是让训练 rollout 访问真实外部服务。([Microsoft AI][1])

---

## 8. 你当前 Stage 16G.3 应如何调整？

我建议把 Stage 16G.3 重新定位为：

```text
Stage 16G.3:
  First Harness Implementation: SWE Bash+Editor Dynamic Diagnostics
```

它不是整个环境系统的总架构，而只是一个 HarnessSpec。

你原计划里有一段把 `run_public_command` 限定为仓库检查、compile smoke、任务声明命令，并要求测试优先走模型可见 `run_project_test`；这会训练出“评测 DSL”倾向。

更合理的修正是：

```text
模型可见：
  bash(command) 或 run_public_command(command)

内部保留：
  ProjectTestRouter
  PublicTestProfile
  CommandProfile
  trust classification
  test contamination detection

模型不可见默认主工具：
  run_project_test
```

你上传的另一个 agent 建议也是这个方向：`run_project_test` 不应作为 Claude/Codex 风格 swe_public_core 的默认模型可见工具；模型应通过 `run_public_command` 输入 pytest、tox、npm test 等命令，内部再用 ProjectTestRouter 识别为 project_test 并标记 test_source_origin、official_feedback_eligible、diagnostic_value。

结合微软报告，我会进一步说：

```text
如果 SEE / Docker sandbox 做好了：
  更接近 MAI 的 bash(command) + editor。

如果 SEE 还没做好：
  暂时保留受限 run_public_command(command)，但不要把它伪装成最终形态。
```

微软 SWE RL 的工具面是 Bash + String replace editor；Bash schema 是宽的，安全边界主要在 SEE、网络隔离、git 清洗、test reset、monitor，而不是模型可见命令 DSL。([Microsoft AI][1])

---

## 9. 建议的 repo 结构

你可以逐步重构成这样：

```text
repoharness/
  core/
    events.py
    trajectory.py
    artifacts.py
    ids.py

  envs/
    base/
      task.py
      taskset.py
      sandbox_taskset.py
      sandbox_spec.py
      harness_spec.py
      rubric.py
      composable_env.py

    swe/
      tasks.py
      repo_init.py
      swe_harness.py
      swe_rubrics.py
      hidden_tests.py

    interactive_swe/
      task_generator.py
      user_sim.py
      approver_sim.py
      permission_policies.py
      rubrics.py

    tooluse/
      mock_backend.py
      tool_registry.py
      seeded_db.py
      task_generator.py
      rubrics.py

  runtime/
    environment_runtime.py
    sandbox_instance.py
    rollout_runner.py
    snapshot.py

  tools/
    bash.py
    editor.py
    file_ops.py
    mcp_adapter.py

  permissions/
    effects.py
    policy.py
    gate.py
    audit.py

  verification/
    graders.py
    monitors.py
    llm_judge.py
    keep_discard.py

  train/
    verl_adapter.py
    rollout_group.py
    reward_packager.py
    staleness.py

  storage/
    trajectory_store.py
    env_artifact_store.py
```

注意：这不是要求你马上全实现，而是要求你**现在不要继续把新功能塞进一个 SWE runner**。

---

## 10. 最小可执行路线图

我建议按这个顺序推进。

### Phase 0：保住现有 SWE 能力，不要马上大重写

把已有 RepoHarness 包成：

```text
SWERepairTaskSet
SWESandboxSpec
SWEHarnessSpec
SWERubric
ComposableEnv(SWERepairTaskSet, SWESandboxSpec, SWEHarnessSpec, SWERubric)
```

即使内部暂时还是旧 runner，也先把外层接口定下来。

### Phase 1：统一 event / trajectory schema

所有 serve / simulate / train / eval 都使用同一套事件：

```json
{
  "episode_id": "...",
  "env_id": "...",
  "policy_version": "...",
  "events": [
    {"type": "user_message"},
    {"type": "assistant_message"},
    {"type": "tool_call"},
    {"type": "tool_result"},
    {"type": "permission_request"},
    {"type": "permission_decision"},
    {"type": "user_simulator_message"},
    {"type": "verifier_result"},
    {"type": "reward_component"}
  ]
}
```

这一步很关键，因为它连接：

```text
serving
debugging
RL rollout
offline replay
SFT/OPD data
reward analysis
```

你上传的建议文档也把统一 trajectory/event schema 视为最小可展示版本的模块 A，因为它连接 serving、debugging、RL rollout、offline replay、eval analysis、trajectory filtering 和 SFT data generation。

### Phase 2：把 Stage 16G.3 改成 SWEHarness v1

实现：

```text
model-visible:
  bash(command) / run_public_command(command)
  str_replace_editor or your file tools
  todo/update_plan

internal:
  ProjectTestRouter
  PublicTestProfile
  TestTrustClassifier
  HiddenTestRubric
  AntiTamperMonitor
```

同时保持：

```text
hidden verifier 不可见
network 默认关闭
git future history 清洗
grading 前 reset tests
test tampering monitor
raw artifact restricted
```

### Phase 3：加 permission engine

不要只做 Bash denylist，而是做 effect-based permission：

```text
read_file(path)
write_file(path)
delete_file(path)
run_command(command)
network_access(domain)
modify_tests(path)
modify_ci(path)
read_secret(path)
call_mcp_tool(server, tool)
```

每个工具调用都变成：

```text
tool input
-> effect extraction
-> permission gate
-> allow / deny / require simulated approval
-> execution
```

这比“限制工具 surface”更接近 Claude/Codex 的运行时拦截思想。你上传的能力差距文档也强调，Claude Code 的关键不变量不是无限能力，而是强能力配合结构化权限决策、审计事件和可恢复反馈。

### Phase 4：加 user simulator / approver simulator

先做 20–50 个 permissioned SWE 任务：

```text
InteractiveRefactorBench-50
RepoPermissionBench-50
```

任务例子：

```text
重构 payments，但不能改 refunds
修 security bug，但不能打印 secret
升级 parser，但 public API 不可变
删除 legacy flag，但不能改已有 tests
增加 feature，但必须先提交 plan
```

reward：

```text
hidden_tests_pass
forbidden_diff_penalty
permission_violation_penalty
unnecessary_approval_penalty
denial_recovery_reward
user_burden_penalty
truthful_final_report_reward
```

这类任务比普通 SWE-bench 更能展示你的项目价值。你上传的建议也说，最有辨识度的方向不是“又一个 coding agent loop”，而是 interactive、permissioned、long-horizon software tasks，其中包含 user approvals、hidden constraints、scoped capabilities 和 training-serving consistency。

### Phase 5：接 verl

verl 不应该直接知道 RepoHarness 内部细节。它应该消费：

```text
RolloutGroupArtifact
  env_id
  task_id
  policy_version
  tool_schema_version
  trajectory
  response_masks
  reward_components
  verifier_results
  keep_discard
  staleness_metadata
```

这样以后你换 SWE env、tool-use env、browser env，不需要改 verl adapter，只换 ComposableEnv。

---

## 11. 不建议现在做什么？

### 不建议一：马上做全行业模拟

微软 general tool-use 的确覆盖 inventory、scheduling、report creation、customer support 等场景；但你作为项目，直接做全行业会变得空泛。([Microsoft AI][1])

先做：

```text
SWE + user simulator + permission
```

再做：

```text
一个小型 MockEnterpriseToolUseEnv
```

### 不建议二：把 user simulator 做成纯 LLM prompt

纯 LLM user sim 会不稳定。应该是：

```text
structured hidden state 决定真值
LLM 只负责自然语言表达
```

### 不建议三：把工具数量当亮点

Claude Code / Codex 的亮点不是工具数量，而是：

```text
agent loop
sandbox
permissions
event history
tool execution
extensions
consistent policy model
```

Codex App Server 文档也强调：Codex harness 不只是 loop，还包括 thread lifecycle、persistence、config/auth、shell/file tools in sandbox、MCP/skills under consistent policy model。([OpenAI][6])

### 不建议四：把 ComposableEnv 做成巨型抽象工程

先做外层接口，不要一次性微服务化。

```text
先 modular monolith
后 service decomposition
```

等你真的遇到规模问题，再拆成服务：

```text
control service
runtime service
verification service
trajectory store
training adapter
```

---

## 12. 对你当前问题的最终判断

**是，你应该把项目设计成 Composable Environments。**

但建议表述更精确：

```text
RepoHarness 是第一个 ComposableEnv family：SWE。
verl 是 training interface。
User simulator / approver simulator 是 interactive SWE family 的环境组件。
Bash/editor 是 SWEHarness 的 tool surface。
Rubric 负责 hidden tests、permission、user burden、anti-tamper。
SandboxSpec 负责 Docker/SEE/network/git/test reset。
```

不是：

```text
RepoHarness = 所有逻辑的大总管。
```

也不是：

```text
立刻做通用个人助理训练平台。
```

你的最终项目定位可以改成：

```text
RepoHarness:
Composable interactive agent environments for SWE RL.

Core idea:
The same environment runtime supports real user sessions, simulated user rollouts,
offline evaluation, and verl training. SWE is the first domain; general tool-use
mock environments are supported by the same TaskSet / Harness / SandboxSpec / Rubric abstraction.
```

这比“RepoHarness + verl 异步 RL”更强，因为它回答的是当前 agentic RL 里真正重要的问题：

```text
如何生成可执行环境？
如何保持训练/部署 harness 一致？
如何模拟真实用户和权限？
如何验证长程状态？
如何防 reward hacking？
如何把异步 rollout 安全地喂给 trainer？
```


[1]: https://microsoft.ai/wp-content/uploads/2026/06/main_20260602_2.pdf "MAI-Thinking-1: Building a Hill-Climbing Machine"
[2]: https://arxiv.org/html/2603.24477 "Composer 2 Technical Report"
[3]: https://developers.openai.com/codex/concepts/sandboxing "Sandbox – Codex | OpenAI Developers"
[4]: https://openai.com/my-MM/index/unrolling-the-codex-agent-loop/ "Unrolling the Codex agent loop | OpenAI"
[5]: https://docs.anthropic.com/en/docs/claude-code/sdk "Agent SDK overview - Claude Code Docs"
[6]: https://openai.com/index/unlocking-the-codex-harness/ "Unlocking the Codex harness: how we built the App Server | OpenAI"
