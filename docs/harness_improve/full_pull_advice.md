我的建议是：**你应该把本地参考代码库分成三类拉取：核心架构参考、训练/rollout 基础设施参考、baseline/对照参考。**

你的项目最终可以吸收三条线：

```text
Prime / Verifiers:
  内部环境如何拆成 TaskSet / Harness / User / Sandbox / Rubric。

Synthetic environment blog:
  环境 pipeline 如何分成 control / execution / verification / training interface，
  以及为什么长程任务需要 artifact、checkpoint、staleness、policy attribution。

Polar / ProRL-Agent-Server:
  如何把任意 existing harness 通过 model proxy + rollout service 接进异步 RL。
```

你上传的那篇博客本质上把 synthetic environment generation 定位成基础设施问题，而不是单纯的数据生成问题；它强调控制面、执行面、验证面、训练接口，以及 long-horizon 环境里的 replay、checkpoint、policy attribution 和 versioned artifact。这个 framing 正好适合你的 RepoHarness 项目。

---

# 1. 最优先拉取：PrimeIntellect-ai/verifiers

```bash
git clone https://github.com/PrimeIntellect-ai/verifiers.git
```

这是**最重要的参考库**。Prime 官方 README 把 Verifiers 定义成用于创建 LLM RL environments 和 evals 的库，并且明确说一个 environment 包含 dataset/task inputs、model harness，以及 reward function/rubric；这些 environments 可以用于 RL training、evaluation、synthetic data generation 和 agent harness 实验。([GitHub][1])

你最应该看这些目录：

```text
verifiers/verifiers/v1/
verifiers/packages/harnesses/
verifiers/packages/tasksets/
verifiers/verifiers/envs/
verifiers/verifiers/rubrics/
verifiers/verifiers/serve/
verifiers/verifiers/rl/
```

其中最关键的是：

```text
verifiers/verifiers/v1/task.py
verifiers/verifiers/v1/taskset.py
verifiers/verifiers/v1/harness.py
verifiers/verifiers/v1/env.py
verifiers/verifiers/v1/state.py
verifiers/verifiers/v1/user.py
verifiers/verifiers/v1/sandbox.py
verifiers/verifiers/v1/artifact.py
verifiers/verifiers/v1/runtime.py
```

Verifiers v1 的 README 说得非常清楚：`Taskset` 定义“要尝试什么”，`Harness` 定义“模型或 agent 如何尝试”，`Env` 则把一个 taskset/harness pair 适配到 eval/training worker API。它还强调 `Task` 是 immutable/serializable input data，`State` 是 mutable/serializable rollout output，而 clients、sandboxes、MCP sessions、tool backends 这些 runtime handles 是进程本地资源。([GitHub][2])

这正是你现在要做的第一步：**把 RepoHarness 从 monolithic harness 拆成 v1-style ownership。**

你应该重点学习它的 ownership 规则：

```text
Taskset owns:
  task loading
  task prompts
  task controls
  task-owned tools
  user behavior
  task-specific lifecycle
  metrics
  rewards
  stop conditions

Harness owns:
  rollout execution
  model/client defaults
  command agents
  framework adapters
  endpoint interception
  primary sandbox placement
  execution artifacts

Env owns:
  making one Taskset/Harness pair usable by eval/training workers
```

Verifiers 文档也明确说，如果工具定义了 task 的 action space、observation 或 success condition，它属于 taskset；如果代码描述的是“一个模型或外部 agent 如何尝试任意任务”，它属于 harness。这个原则对你拆 RepoHarness 非常重要。([Prime Intellect Docs][3])

## 你应该如何用到自己的项目

你可以在自己项目里做一个类似结构：

```text
repoharness/
  core/
    task.py
    state.py
    artifact.py
    env.py

  tasksets/
    interactive_refactor.py
    repo_permission_bench.py
    swe_bench_lite.py

  harnesses/
    repo_harness.py
    mini_swe_baseline.py
    external_shell_harness.py

  usersim/
    user.py
    approver.py

  permissions/
    spec.py
    gate.py
    effects.py

  sandbox/
    spec.py
    docker_runtime.py

  rubrics/
    swe.py
    permission.py
    user_burden.py

  train/
    verl_adapter.py
```

你的 `RepoHarness` 不应该再拥有 task、hidden tests、reward、user hidden constraints。它应该只拥有：

```text
agent loop
context construction
tool routing
permission gate invocation
user channel invocation
event logging
trajectory construction
```

具体任务、用户模拟、权限策略、scoring 都从 `TaskSet/UserSimSpec/PermissionSpec/Rubric` 注入。

---

# 2. 必看：PrimeIntellect-ai/verifiers PR #1067

```bash
# 不需要单独 clone，clone verifiers 后可以看 git history；
# 也可以在 GitHub 上打开 PR:
# https://github.com/PrimeIntellect-ai/verifiers/pull/1067
```

这个 PR 是你之前提到的 Composable Environments 的原点之一。PR 标题是 “feat: composable Task/Agent/Environment architecture”，已在 2026-04-01 合并。PR summary 说得非常直接：原来的 `opencode_swe`、`opencode_lean` 等环境把 task logic 和 agent logic 绑在一起，导致给已有 agent 添加新任务时也要从头写完整 environment；新方案引入 `Task`、`TaskSet`、`SandboxTaskSet`、`Harness`、`SandboxSpec`、`ComposableEnv`。([GitHub][4])

你最应该记住 PR 里的这几条：

```text
Task:
  one fully-bound instance

TaskSet:
  collection + behavior for tasks

SandboxTaskSet:
  TaskSet with sandbox setup/resource needs

SandboxSpec:
  per-instance sandbox requirements:
  image, CPU, memory, GPU type, timeout

Harness:
  agent-side config:
  install script, run command, declared paths

ComposableEnv:
  wires TaskSet + Harness together
```

PR 还特别强调：**Rubrics own all scoring**，taskset 提供 `get_rubric()`，rubric 可以跑测试、读文件、算 reward；`keep_sandbox_for_scoring=True` 让 sandbox 在 rollout 结束后保持存活，从而使 scoring 可以 retry、可以和 rollout 解耦。([GitHub][4])

这对你的项目非常重要。你的 `Rubric` 不要只是一个 `reward_fn(output)`，而应该是：

```text
final hidden tests
public tests
forbidden diff checker
permission violation checker
test tampering checker
API compatibility checker
user burden score
denial recovery score
```

---

# 3. 必拉：PrimeIntellect-ai/research-environments

```bash
git clone https://github.com/PrimeIntellect-ai/research-environments.git
```

这个库是 Verifiers 设计在真实 research environments 上的实例。它的 README 直接展示了 composable architecture：

```python
taskset = R2EGymTaskSet()
harness = opencode_harness(system_prompt="You are a coding agent...")
env = ComposableEnv(taskset=taskset, harness=harness)
```

同一个 README 还列出了目录分工：`tasksets/swe/` 放 SWE tasksets，包括 R2E-Gym、SWE-bench、Multi-SWE、OpenSWE；`tasksets/lean/` 放 Lean；`tasksets/math/` 放 math；`harnesses/opencode/` 是 OpenCode harness；`environments/opencode_swe/`、`opencode_lean/`、`opencode_math/` 是组合后的环境。([GitHub][5])

你最应该看：

```text
research-environments/tasksets/swe/
research-environments/tasksets/lean/
research-environments/tasksets/math/
research-environments/harnesses/opencode/
research-environments/environments/opencode_swe/
research-environments/environments/opencode_lean/
research-environments/environments/opencode_math/
```

如果仓库里还有这些目录，也要重点看：

```text
research-environments/environments/swe_composable/
research-environments/environments/swe_user_sim/
research-environments/environments/rlm_lean/
```

PR #1067 的 linked commit 提到 `swe_user_sim` 是一个 multi-agent UserSimEnv，包含 clueless、junior_dev、senior_dev、default 四种 user persona；它还提到 `swe_composable` 用 ComposableEnv + SWE task adapter + ReActAgent proof-of-concept，用约 60 行替代了更大的旧环境实现。([GitHub][4])

## 你应该如何参考它

你不要照搬它的所有代码，而是学它的**组合方式**：

```text
同一个 TaskSet 可以被不同 Harness 跑：
  SWETaskSet + OpenCodeHarness
  SWETaskSet + RepoHarness
  SWETaskSet + MiniSWEHarness

同一个 Harness 可以跑不同 TaskSet：
  RepoHarness + SWEBenchTaskSet
  RepoHarness + InteractiveRefactorTaskSet
  RepoHarness + RepoPermissionTaskSet
```

你的第一个自建 taskset 可以是：

```text
InteractiveRefactorTaskSet
  task:
    repo snapshot
    initial user request
    hidden constraints
    forbidden paths
    public tests
    hidden tests
    permission policy
    user simulator profile
    reward rubric
```

例如：

```yaml
id: payments_refactor_001
prompt: "帮我重构 payments 模块，旧的 PaymentClient 太乱了。"
repo: fixtures/payments_service
hidden_constraints:
  forbidden_paths:
    - src/refunds/**
    - infra/prod/**
  public_api_must_remain_compatible: true
  no_test_deletion: true
permission:
  read_repo: allow
  edit_payments: require_user_approval
  edit_refunds: deny
  push_main: deny
user_sim:
  persona: engineering_manager
  hidden_constraints:
    - "不要修改 refunds"
    - "public API 不能变"
rubric:
  hidden_tests: pytest hidden_tests/payments
  api_contract: python checks/api_contract.py
```

---

# 4. 必拉：NVIDIA-NeMo/ProRL-Agent-Server，也就是 Polar

```bash
git clone --branch stable https://github.com/NVIDIA-NeMo/ProRL-Agent-Server.git
```

这个库对应你刚看的 Polar 论文，是你做 “Polar-lite” 的主要参考。它的 README 说 Polar 是一个面向真实 agent harness 的 RL rollout framework，核心有三点：Harness as Environment、Smart Rollout Pipeline、Rollout as a Service。([GitHub][6])

Polar 的架构是：Rollout Server 管理并分发 client requests 到 Gateway Nodes；Gateway Nodes 异步准备 runtime、执行 agents、构建 trajectories、评估结果；agent harnesses 通过一个 proxy 被监听，这个 proxy 位于 agent execution processes 和 inference servers 之间。([GitHub][6])

你最应该看这些目录：

```text
ProRL-Agent-Server/src/polar/
ProRL-Agent-Server/src/polar/agent/
ProRL-Agent-Server/src/polar/config/
ProRL-Agent-Server/src/polar/gateway/
ProRL-Agent-Server/src/polar/platform/
ProRL-Agent-Server/src/polar/rollout/
ProRL-Agent-Server/src/polar/runtime/
ProRL-Agent-Server/src/polar/trajectory/
ProRL-Agent-Server/examples/
ProRL-Agent-Server/src/slime_bridge/
```

GitHub 文件树也显示 `src/polar` 下有 `agent`、`config`、`gateway`、`platform`、`rollout`、`runtime`、`trajectory` 这些核心模块。([GitHub][7])

Polar README 的 CLI 使用方式也很值得参考，它把本地运行拆成五个命令：

```text
polar serve_rollout
polar serve_gateway
polar dashboard
polar submit
polar status
```

这说明它不是一个 trainer 内部函数，而是一个 service boundary。([GitHub][6])

## 你应该如何应用到 RepoHarness

你不需要完整复刻 Polar，但应该做一个 **Polar-lite**：

```text
repo-rollout serve
repo-rollout worker
repo-rollout submit task.yaml
repo-rollout status
repo-rollout export-verl-batch
```

架构可以是：

```text
verl trainer
    |
    v
RepoRolloutServer
    |
    v
GatewayWorker
    |
    v
ComposableEnv Runtime
    |
    v
RepoHarness / ExternalShellHarness
    |
    v
ModelProxy
    |
    v
vLLM / SGLang / OpenAI-compatible endpoint
```

你需要参考 Polar 的三块：

### A. Rollout service

做一个非阻塞 API：

```python
POST /rollouts
GET /rollouts/{id}
GET /rollouts/{id}/artifacts
```

### B. Gateway worker lifecycle

你可以先简化为：

```text
INIT:
  创建 sandbox，准备 repo，安装依赖

RUNNING:
  执行 RepoHarness / external harness

POSTRUN:
  运行 rubric，构建 trajectory artifact，保存结果
```

后面再加：

```text
READY pool
runtime prewarming
partial recovery
timeout partial trace
```

### C. Model proxy / trace capture

先只做 OpenAI-compatible chat completions proxy：

```text
agent harness -> /v1/chat/completions proxy -> inference backend
```

记录：

```python
CompletionRecord:
  session_id
  request_id
  prompt_messages
  response_message
  prompt_token_ids
  response_token_ids
  response_logprobs
  finish_reason
  policy_version
  timestamp
```

这一步会让你的项目从“白盒 harness”升级为“可以接外部 native harness 的 rollout infrastructure”。

---

# 5. 建议拉取：PrimeIntellect-ai/renderers

```bash
git clone https://github.com/PrimeIntellect-ai/renderers.git
```

这个库可能比你第一眼感觉的重要得多。它解决的是多轮 agent RL 中非常致命的问题：**训练器看到的 token ids 必须和 sampler 当时实际采样的 token ids 一致。**

renderers README 说，它是 programmable chat templates for LLM training and inference；renderer 可以把 messages 渲染成 token ids，把 completion ids 解析成结构化 assistant messages，并在多轮 rollout 中扩展上下文而不重新渲染 model-sampled history。([GitHub][8])

它还明确解释了为什么 RL 需要 renderer：trainer 必须看到 sampler 看到的 exact token ids；如果使用 `apply_chat_template` 重渲染历史，会出现 boolean round-trip、BPE retokenization drift、tool-call XML drift、thinking 被剥离、scaffold 改写历史等问题。([GitHub][8])

这和 Polar 论文里的 token-faithful trajectory reconstruction 是同一个问题。

## 你应该如何用到 RepoHarness

如果你短期只是做简历 MVP，可以先不实现完整 renderer。
但你应该在 artifact schema 里预留：

```python
Trace:
  prompt_ids: list[int] | None
  response_ids: list[int] | None
  loss_mask: list[int] | None
  response_logprobs: list[float] | None
  renderer_name: str | None
  tokenizer_name: str | None
  tokenization_source: "proxy" | "renderer" | "re_rendered"
```

如果后续你做 Polar-style model proxy，建议认真参考 renderers 的 `bridge_to_next_turn` 思想，避免把 transcript 重新 tokenize 后交给 verl。

---

# 6. 建议拉取：SWE-agent/mini-swe-agent

```bash
git clone https://github.com/SWE-agent/mini-swe-agent.git
```

这不是 Prime 或 Polar 的库，但对你的项目非常重要，因为它是你最好的 baseline。mini-swe-agent README 明确强调它几乎只有 bash、线性 history、`subprocess.run` 独立执行，并且说如果你做 FT/RL、不想 overfit 到特定 agent scaffold，mini-swe-agent 是默认选择之一。([GitHub][9])

你应该用它做两件事：

```text
1. baseline harness:
   MiniSWEHarness

2. 叙事对照:
   simple SWE repair 用 bash-only loop 足够；
   你的 RepoHarness 解决 interactive / permissioned / long-horizon SWE。
```

你的 README 可以写：

```text
For simple single-shot SWE repair, mini-swe-agent is a strong baseline.
RepoHarness focuses on interactive, permissioned, long-horizon software tasks
where user approvals, hidden constraints, scoped capabilities, replayable artifacts,
and async RL metadata matter.
```

---

# 7. 你已经在用，但仍要对照：verl

```bash
git clone https://github.com/verl-project/verl.git
```

verl 是你的训练后端，不是 environment 设计参考的主来源。它 README 说 verl 是 flexible、efficient、production-ready 的 LLM RL training library，支持 FSDP/FSDP2/Megatron-LM 训练，以及 vLLM、SGLang、HF Transformers 用于 rollout generation。([GitHub][10])

你最应该参考的是：

```text
verl 的 multi-turn rollout support
verl 的 server-based RL / SGLang integration
verl 的 rollout batch 数据结构
verl 的 reward manager / advantage 计算接口
```

verl README 也提到 SGLang fully supported，并且 SGLang RL Group 正在构建 multi-turn agentic RL、server-based RL、partial rollout 等特性。([GitHub][10])

你要避免一个坑：**不要让 RepoHarness 直接变成 verl 内部的一个巨大 environment 函数。**
更好的方式是：

```text
RepoHarness rollout service -> TrajectoryArtifact -> VerlAdapter -> verl batch
```

这样你的项目仍然和训练框架解耦。

---

# 8. 可选参考：PrimeIntellect-ai/prime-rl

```bash
git clone https://github.com/PrimeIntellect-ai/prime-rl.git
```

因为你已经选择 verl，prime-rl 不应该成为你的主实现参考。但它值得看，因为它代表 Prime 对 async RL 系统边界的理解。

prime-rl README 把 PRIME-RL 定位为 async RL training at scale，并强调 fully asynchronous RL、可训练 1000+ GPU 规模、原生集成 verifiers environments，包括 SWE 和 agentic environments。([GitHub][11])

你应该重点看：

```text
prime-rl/configs/
prime-rl/examples/
prime-rl/src/prime_rl/
prime-rl/docs/
```

你主要借鉴：

```text
训练配置如何引用 env
rollouts_per_example 如何配置
eval/training config 如何保持一致
async RL 中 policy version / rollout step / eval step 怎么记录
```

但不建议你把 prime-rl 接进项目。你的主线应该仍然是 verl。

---

# 9. 可选参考：PrimeIntellect-ai/rlm-harness

```bash
git clone https://github.com/PrimeIntellect-ai/rlm-harness.git
```

这个库是 RLM-style rollouts 的 command harness。它的 README 说它是 “Harness for RLM-style rollouts. Only for RL training”，支持 CLI 和 Python SDK，并通过环境变量配置模型、base URL、tools、max depth、execution timeout、compaction 等。([GitHub][12])

你可以参考它的：

```text
command harness packaging
environment-variable configuration
tool enable/disable surface
context compaction threshold
session directory layout
```

但是它不是你项目的主参考，因为你的项目更关注：

```text
SWE repo environment
permission system
user simulator
verl async RL adapter
```

---

# 10. 可选参考：PrimeIntellect-ai/community-environments

```bash
git clone https://github.com/PrimeIntellect-ai/community-environments.git
```

这个库是社区环境集合。它的 README 说这是 training-ready RL environments + evals，并提供 `prime env init`、`vf-eval`、`prime env push` 这种环境创建/测试/发布流程。([GitHub][13])

你可以用它看：

```text
别人如何组织一个 environment package
pyproject.toml 如何写
README 如何描述环境
CI/publish 风格
```

但它对你核心架构帮助不如 `verifiers` 和 `research-environments`。

---

# 11. 可选参考：PrimeIntellect-ai/mcp-demo

```bash
git clone https://github.com/PrimeIntellect-ai/mcp-demo.git
```

这是一个很小的 MCP environments demo。GitHub 页面显示它只有少量 commits，包含 `configs`、`environments`、`main.py` 等。([GitHub][14])

你可以把它当成 MCP adapter 的玩具参考，但不建议投入太多时间。你的 MCP 设计应该先抽象成：

```text
ToolAdapter:
  BashTool
  FileEditTool
  MCPTool
  BrowserTool
```

等 RepoHarness 的 TaskSet/Harness/Rubric/UserSim/PermissionSpec 稳定后再接 MCP。

---

# 12. 我会怎么安排本地参考目录

你可以这样组织：

```bash
mkdir -p ~/agent-rl-refs
cd ~/agent-rl-refs

# Core composable environment design
git clone https://github.com/PrimeIntellect-ai/verifiers.git
git clone https://github.com/PrimeIntellect-ai/research-environments.git

# Polar-style rollout-as-a-service / model proxy
git clone --branch stable https://github.com/NVIDIA-NeMo/ProRL-Agent-Server.git

# Token-faithful multi-turn traces
git clone https://github.com/PrimeIntellect-ai/renderers.git

# Baseline
git clone https://github.com/SWE-agent/mini-swe-agent.git

# Your trainer
git clone https://github.com/verl-project/verl.git

# Optional
git clone https://github.com/PrimeIntellect-ai/prime-rl.git
git clone https://github.com/PrimeIntellect-ai/rlm-harness.git
git clone https://github.com/PrimeIntellect-ai/community-environments.git
git clone https://github.com/PrimeIntellect-ai/mcp-demo.git
```

---

# 13. 参考优先级

我会按这个顺序看：

| 优先级 | 仓库                                        | 你最该学什么                                                    |
| --- | ----------------------------------------- | --------------------------------------------------------- |
| P0  | `PrimeIntellect-ai/verifiers`             | Taskset/Harness/Env/State/User/Rubric ownership           |
| P0  | `PrimeIntellect-ai/research-environments` | SWE/Lean/Math tasksets 和 OpenCode harness 如何组合            |
| P0  | `NVIDIA-NeMo/ProRL-Agent-Server`          | rollout server、gateway、runtime、trajectory、model proxy     |
| P1  | `PrimeIntellect-ai/renderers`             | token-faithful trace construction，避免 retokenization drift |
| P1  | `SWE-agent/mini-swe-agent`                | bash-only minimal baseline                                |
| P1  | `verl-project/verl`                       | 你的训练接口、multi-turn rollout、server-based RL                 |
| P2  | `PrimeIntellect-ai/prime-rl`              | async RL 配置和 verifiers integration 思路                     |
| P2  | `PrimeIntellect-ai/rlm-harness`           | command harness 包装方式                                      |
| P2  | `community-environments`                  | environment package 组织方式                                  |
| P3  | `mcp-demo`                                | MCP environment 小 demo                                    |

---

# 14. 最重要的实现路线

你不要同时实现所有东西。推荐按四阶段走。

## 阶段 1：Prime-style internal refactor

目标：先把你当前 monolithic RepoHarness 拆开。

```text
TaskSet
Harness
SandboxSpec
UserSimSpec
PermissionSpec
Rubric
Artifact
```

最低可运行例子：

```python
env = RepoComposableEnv(
    taskset=InteractiveRefactorTaskSet(split="train"),
    harness=RepoHarness(),
    sandbox_spec=DockerSandboxSpec(),
    user_sim_spec=EngineeringManagerUserSimSpec(),
    permission_spec=SWESafePermissionSpec(),
    rubric=InteractiveSWERubric(),
)
artifact = await env.run_one(policy, seed=0)
```

这一步主要参考：

```text
verifiers/verifiers/v1/
verifiers/packages/tasksets/
verifiers/packages/harnesses/
research-environments/tasksets/swe/
research-environments/harnesses/opencode/
```

## 阶段 2：做 RepoPermissionBench / InteractiveRefactorBench

目标：做一个小 benchmark，证明你的项目不是空架构。

```text
20-100 个小 repo task
每个 task 有：
  repo snapshot
  hidden constraints
  permission policy
  user simulator profile
  hidden tests
  forbidden diff checker
```

指标：

```text
hidden_test_pass_rate
permission_violation_rate
forbidden_diff_rate
unnecessary_approval_count
denial_recovery_rate
user_turn_count
tool_call_count
```

这一步主要参考：

```text
research-environments/tasksets/swe/
mini-swe-agent baseline
verifiers rubrics/lifecycle decorators
```

## 阶段 3：Polar-lite rollout service

目标：把 rollout 从 trainer 内部函数变成 service。

```text
RepoRolloutServer
GatewayWorker
RuntimePool
ArtifactStore
EvaluatorRegistry
TraceBuilder
```

最小版 API：

```text
POST /rollouts
GET /rollouts/{id}
GET /rollouts/{id}/artifact
```

这一步主要参考：

```text
ProRL-Agent-Server/src/polar/rollout/
ProRL-Agent-Server/src/polar/gateway/
ProRL-Agent-Server/src/polar/runtime/
ProRL-Agent-Server/src/polar/trajectory/
```

## 阶段 4：verl adapter + token-faithful trace

目标：让 artifact 可以被 verl 消费。

```python
TrajectoryArtifact -> VerlSampleBatch
```

artifact 里至少保存：

```text
prompt_ids
response_ids
loss_mask
response_logprobs
reward
reward_components
policy_version
taskset_version
harness_version
permission_spec_version
user_sim_spec_version
rubric_version
staleness
```

这一步主要参考：

```text
ProRL-Agent-Server/src/slime_bridge/
PrimeIntellect-ai/renderers
verl multi-turn rollout / server-based RL docs
```

ProRL 的 Slime bridge README 很值得看，因为它说明了一个 trainer bridge 需要做什么：提交 async task batches、追踪 rollout ids 和 policy versions、给任务打上 `{group_id, policy_version, rollout_step}`，过滤 off-policy stale groups，把 Polar trajectories 转成 trainer samples，并做 group-normalized reward shaping。([GitHub][15])

你用的是 verl，不是 Slime，但 bridge 的边界设计可以照搬。

---

# 15. 你项目最终可以这样定位

最终 README 的一句话可以写成：

```text
RepoHarness is a composable rollout infrastructure for interactive SWE agent RL.
It combines Prime-style TaskSet/Harness/Sandbox/Rubric composition with
Polar-style rollout-as-a-service and model-call trajectory capture, and exports
permission-aware, user-aware, token-faithful trajectory artifacts to verl.
```

中文就是：

**RepoHarness 不是一个 Claude Code clone，而是一个面向交互式 SWE agent RL 的可组合环境与 rollout 基础设施。它内部参考 Prime 的 TaskSet/Harness/Rubric 解耦，外部参考 Polar 的 rollout server/model proxy/trajectory builder，并通过 UserSim + PermissionSpec 训练真实任务中的用户交互和权限边界。**

最先应该真正精读和仿照的是：

```text
1. verifiers/verifiers/v1/
2. verifiers/packages/harnesses/
3. verifiers/packages/tasksets/
4. research-environments/tasksets/swe/
5. research-environments/harnesses/opencode/
6. ProRL-Agent-Server/src/polar/{rollout,gateway,runtime,trajectory}
7. ProRL-Agent-Server/src/slime_bridge/
8. renderers/renderers/
9. mini-swe-agent/src/minisweagent/
```

这套组合足够支撑你的项目从“我写了一个 SWE harness 并接入 verl”升级为：

**我实现了一个训练-使用一致、可组合、可异步 rollout、可验证、可接真实用户/模拟用户/权限系统的 SWE agent environment pipeline。**

[1]: https://github.com/PrimeIntellect-ai/verifiers "GitHub - PrimeIntellect-ai/verifiers: Our library for RL environments + evals · GitHub"
[2]: https://github.com/PrimeIntellect-ai/verifiers/tree/main/verifiers/v1 "verifiers/verifiers/v1 at main · PrimeIntellect-ai/verifiers · GitHub"
[3]: https://docs.primeintellect.ai/verifiers/byo-harness "Byo Harness - Prime Intellect Docs"
[4]: https://github.com/PrimeIntellect-ai/verifiers/pull/1067 "feat: composable Task/Agent/Environment architecture by hallerite · Pull Request #1067 · PrimeIntellect-ai/verifiers · GitHub"
[5]: https://github.com/PrimeIntellect-ai/research-environments "GitHub - PrimeIntellect-ai/research-environments: Environments by the Prime Intellect Research Team · GitHub"
[6]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server "GitHub - NVIDIA-NeMo/ProRL-Agent-Server: Agentic RL on Any Harness at Scale · GitHub"
[7]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/tree/stable/src/polar "ProRL-Agent-Server/src/polar at stable · NVIDIA-NeMo/ProRL-Agent-Server · GitHub"
[8]: https://github.com/PrimeIntellect-ai/renderers "GitHub - PrimeIntellect-ai/renderers: Programmable chat templates for LLM training and inference. · GitHub"
[9]: https://github.com/SWE-agent/mini-swe-agent "GitHub - SWE-agent/mini-swe-agent: The 100 line AI agent that solves GitHub issues or helps you in your command line. Radically simple, no huge configs, no giant monorepo—but scores >74% on SWE-bench verified! · GitHub"
[10]: https://github.com/volcengine/verl "GitHub - verl-project/verl: verl/HybridFlow: A Flexible and Efficient RL Post-Training Framework · GitHub"
[11]: https://github.com/PrimeIntellect-ai/prime-rl "GitHub - PrimeIntellect-ai/prime-rl: Agentic RL Training at Scale · GitHub"
[12]: https://github.com/PrimeIntellect-ai/rlm-harness "GitHub - PrimeIntellect-ai/rlm-harness: Harness for RLM-style rollouts. Only for RL training · GitHub"
[13]: https://github.com/PrimeIntellect-ai/community-environments "GitHub - PrimeIntellect-ai/community-environments: Lightly-reviewed collection of community environments · GitHub"
[14]: https://github.com/PrimeIntellect-ai/mcp-demo "GitHub - PrimeIntellect-ai/mcp-demo: MCP Environments demo · GitHub"
[15]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/tree/stable/src/slime_bridge "ProRL-Agent-Server/src/slime_bridge at stable · NVIDIA-NeMo/ProRL-Agent-Server · GitHub"
