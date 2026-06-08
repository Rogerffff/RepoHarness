# 外部参考代码对 RepoHarness 重定位和新架构设计的分析

本文依据以下本地材料和外部参考代码完成：

- `docs/harness_improve/full_pull_advice.md`
- `docs/harness_improve/polar_advice.md`
- `docs/harness_improve/2605.24220v1.pdf`
- `reference/ProRL-Agent-Server`
- `reference/verifiers`
- `reference/research-environments`
- `reference/renderers`
- `reference/mini-swe-agent`

本文只分析架构参考价值，不要求也不包含 RepoHarness 源码改动。

## 1. 总体结论

RepoHarness 当前最合理的新定位不是继续做一个单体 SWE harness，也不是直接复刻 Claude Code、Codex、mini-swe-agent 或 Polar。更合理的定位是：

```text
RepoHarness 是面向交互式软件工程智能体强化学习的可组合环境与 rollout 基础设施。

内部使用 Prime-style 的 TaskSet / Harness / Sandbox / User / Permission / Rubric / Artifact ownership。
外部使用 Polar-style 的 rollout-as-a-service、gateway lifecycle 和 model API proxy。
训练接口输出 token-faithful、permission-aware、user-aware 的轨迹工件，再由 verl adapter 转成训练批次。
```

这个组合是合理的，但必须分阶段落地：

1. 第一阶段先把 RepoHarness 内部从单体入口拆成可组合 environment ownership，保留当前 `run_episode(real_episode)` 作为兼容入口。
2. 第二阶段先做 RepoHarness native capture，确保 `prompt_ids`、`response_ids`、`response_logprobs`、`response_mask` 来自真实采样路径，而不是事后重新 tokenization。
3. 第三阶段再做 Polar-lite rollout service，训练器通过 HTTP 或队列提交 rollout task，不直接 import RepoHarness 内部函数。
4. 第四阶段再做 OpenAI-compatible model proxy，把 mini-swe-agent、OpenCode、Codex-like、Claude-Code-like 等外部 harness 接入同一个轨迹构建层。
5. 第五阶段再考虑 prefix merging、staleness filtering、runtime pool、dashboard、多 provider proxy 等复杂能力。

不建议现在完整复制 Polar，因为当前 RepoHarness 的核心差异是用户交互、权限边界、隐藏约束、文件变更审计和训练投影安全。Polar 主要解决任意已有 harness 的低侵入训练接入，它没有替代 RepoHarness 自己的 user simulator、permission system、hidden verifier 和 artifact governance。

## 2. 本地拉取状态

本次已将目标仓库拉取到 `reference/` 下。当前本地状态如下：

| 仓库目录 | 远端仓库 | 分支 | 当前提交 |
| --- | --- | --- | --- |
| `reference/ProRL-Agent-Server` | `https://github.com/NVIDIA-NeMo/ProRL-Agent-Server.git` | `stable` | `8bc67cc32607c31988406a2de460b350970efc88`，`vLLM support, more harness shortcuts and Readability Updates (#37)` |
| `reference/verifiers` | `https://github.com/PrimeIntellect-ai/verifiers.git` | `main` | `a01ce52fca6ecf4a611f3730101e470fdd0fdf36`，`feat(v1/sandbox): canonical /vf/model bridge... (#1560)` |
| `reference/research-environments` | `https://github.com/PrimeIntellect-ai/research-environments.git` | `main` | `4c08260f07d1f907d3adee93bf55b94e177865c9`，`Restrict opencode verifiers version (#498)` |
| `reference/renderers` | `https://github.com/PrimeIntellect-ai/renderers.git` | `main` | `596c15ffd9da779290bfd0fdcad520688de14a4e`，`feat(nemotron3): add Nemotron-3 Ultra chat-template variant (#77)` |
| `reference/mini-swe-agent` | `https://github.com/SWE-agent/mini-swe-agent.git` | `main` | `2afd0fb81bacbf0aacfac9ded6f093c5acd0bf7c`，`Fix: Stop cleanly on limit breach when stdin is non-interactive (#850)` |

说明：`ProRL-Agent-Server` 的 `stable` 分支存在并已按建议使用。其他仓库使用远端默认的 `main` 分支。本文中的代码路径均以当前本地拉取状态为准。

## 3. Polar / ProRL-Agent-Server 分析

### 3.1 核心定位

Polar 的定位是“把真实 agent harness 当作 RL environment”，但它不是让每个 harness 改写成统一 Gym-style environment。它选择在模型 API 边界放置 proxy，让原 harness 原样运行，同时捕获模型请求、响应 token、logprobs 和 provider 格式转换结果，再重建训练器可消费的 trajectory。

`docs/harness_improve/2605.24220v1.pdf` 中最关键的架构事实是：

- Rollout Server 接收 task request，将一个 task 展开成多个 session。
- Gateway Node 负责 runtime 初始化、harness 执行、completion capture、trajectory reconstruction、evaluation 和 cleanup。
- Model API proxy 位于 harness 和 inference server 之间，支持 Anthropic Messages、OpenAI Chat Completions、OpenAI Responses、Google generateContent 等入口。
- Trajectory builder 提供 `per_request` 和 `prefix_merging` 两种策略。
- 训练样本必须保持 token-faithful，不能只把 transcript 重新 tokenize。
- outcome reward 直接广播到 request-level trace 会导致 noisy credit assignment，论文实验中观察到 reward hacking。

### 3.2 关键代码位置

Rollout 服务入口：

- `reference/ProRL-Agent-Server/src/polar/rollout/server.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/manager.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/pipeline.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/balancer.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/models.py`

`TaskRequest` 位于 `src/polar/rollout/models.py`，包含：

```text
task_id
instruction
num_samples
timeout_seconds
runtime
agent
builder
evaluator
callback_url
metadata
```

这个 shape 对 RepoHarness 很重要，因为它把训练提交、runtime、agent harness、trajectory builder、evaluator 和 async metadata 放在同一个 public request contract 里。RepoHarness 现有 `RepoHarnessEpisodeRequest` 更偏内部 episode 契约，后续若做 rollout service，应当引入类似 `RolloutTaskRequest`，而不是让 verl worker 直接理解 RepoHarness 内部对象。

Gateway 生命周期：

- `reference/ProRL-Agent-Server/src/polar/gateway/node.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/dispatcher.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/session.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/storage.py`

`GatewayNodeManager` 将 session 分成：

```text
INIT:
  创建 runtime，执行 prepare actions。

READY:
  保存已经初始化好的 runtime，等待 run slot。

RUNNING:
  执行 harness.setup、harness.run_steps、harness.postprocess。

POSTRUN:
  构建 trajectory，执行 evaluator，运行 postrun steps，清理 runtime，回调 rollout server。
```

这个分层比 RepoHarness 当前“在 `run_episode` 中完成所有动作”更适合长链路异步强化学习。它给 Stage 16G.3 以后的真实 rollout 提供了一个很清楚的执行平面：workspace materialization、bash 执行、patch hygiene、verifier、artifact projection 都应该是 gateway lifecycle 的阶段，而不是全部塞在 trainer 调用栈中。

Model proxy 和 provider 兼容：

- `reference/ProRL-Agent-Server/src/polar/gateway/server.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/proxy.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/detection.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/transform/openai_chat.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/transform/openai_responses.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/transform/anthropic.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/transform/google.py`

`gateway/server.py` 的 catch-all `proxy_request` 会检测 API 类型，将请求转换成 OpenAI Chat Completions 形状，转发到 inference backend，然后保存 completion，再转换回原 provider 响应。非 streaming 和 streaming 路径都会调用 `state.storage.save_message(...)` 保存：

```text
original_request
transformed_request
response
model_requested
model_used
api_type
session metadata
```

这一点对 RepoHarness 的外部 harness 接入非常关键。短期内 RepoHarness 可以先做 native capture，因为它自己控制 agent loop。中期如果要训练 mini-swe-agent、OpenCode、Codex-like 或 Claude-Code-like harness，就应该使用 model API proxy，而不是强行把这些 harness 的内部循环改写成 RepoHarness tool loop。

Runtime 和 agent harness adapter：

- `reference/ProRL-Agent-Server/src/polar/runtime/models.py`
- `reference/ProRL-Agent-Server/src/polar/runtime/base.py`
- `reference/ProRL-Agent-Server/src/polar/runtime/docker.py`
- `reference/ProRL-Agent-Server/src/polar/runtime/apptainer.py`
- `reference/ProRL-Agent-Server/src/polar/agent/models.py`
- `reference/ProRL-Agent-Server/src/polar/agent/base.py`
- `reference/ProRL-Agent-Server/src/polar/agent/presets/shell.py`
- `reference/ProRL-Agent-Server/src/polar/agent/presets/codex.py`
- `reference/ProRL-Agent-Server/src/polar/agent/presets/claude_code.py`
- `reference/ProRL-Agent-Server/src/polar/agent/presets/opencode.py`

`RuntimeSpec` 把 backend、image、prepare、eval_prepare、env、network、workdir、CPU、memory、GPU、internet、kwargs 等配置绑定在 session 上。`AgentSpec` 把 harness、model_name、settings、env、MCP server、skills_path 和 custom shell command 绑定在 agent 上。`BaseHarness` 只需要把 AgentSpec 转成一组 `ExecInput`，也就是“如何运行这个 harness”。

RepoHarness 可以借鉴这个分工：

```text
TaskSet / Task:
  定义要解决什么、隐藏约束是什么、评分规则是什么。

HarnessSpec / HarnessRunner:
  定义用 RepoHarness native loop、mini-swe-agent、OpenCode、Codex-like 还是外部 shell command 来尝试任务。

RuntimeSpec / SandboxSpec:
  定义 episode 容器、网络、依赖、workspace、resource budget。

Rollout gateway:
  把三者组合成真实执行过程。
```

Trajectory builder：

- `reference/ProRL-Agent-Server/src/polar/trajectory/models.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/builder/record_utils.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/builder/per_request.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/builder/prefix_merging.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/registry.py`

`Trace` 的字段非常值得 RepoHarness 对齐：

```text
prompt_ids
response_ids
loss_mask
prompt_messages
response_messages
tools
finish_reason
response_logprobs
reward
metadata
```

RepoHarness 当前 `src/repo_harness/rl/training_view.py` 已经有 `prompt_ids`、`response_ids`、`response_mask`、`response_logprobs`、`response_spans` 和 `reward_score`。方向是兼容的。缺口不是字段名字，而是 token provenance：这些 token 必须来自真实 sampled response 或 renderer/proxy 证明过的 token stream，不能依赖最终 messages 的重新渲染。

`prefix_merging.py` 的关键思想是：

```text
assistant 真实采样 token 使用 response_ids 原样拷贝，loss_mask=1。
harness 插入的 tool result、interstitial 和下一轮 canonical prompt token 使用 prompt_ids 中的 canonical tail，loss_mask=0。
只有当后续 prompt 与前一个 prompt 存在严格 token prefix 关系时才合并。
遇到 context compaction、subagent 或 prompt rewriting 时自然断链。
```

这一点对长 SWE rollout 很重要。RepoHarness 可以先保守地保留 per-request 或 per-turn trace，但 schema 必须允许未来 prefix merging。不能把 session-level reward 简单广播给每个 request-level trace 后直接训练。

Evaluator：

- `reference/ProRL-Agent-Server/src/polar/trajectory/evaluator/base.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/evaluator/swebench_harness.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/evaluator/test_on_output.py`

Polar 的 evaluator 是 registry-backed strategy，接收 trajectory、session_dir、artifacts_dir、runtime 等上下文。RepoHarness 的 verifier 和 reward boundary 更复杂，但可以借鉴“evaluator 是 postrun strategy，不是 harness 内部 side effect”的边界。

Slime bridge：

- `reference/ProRL-Agent-Server/src/slime_bridge/README.md`
- `reference/ProRL-Agent-Server/src/slime_bridge/rollout.py`
- `reference/ProRL-Agent-Server/src/slime_bridge/adapter.py`
- `reference/ProRL-Agent-Server/src/slime_bridge/reward_post_process.py`
- `reference/ProRL-Agent-Server/src/slime_bridge/config.py`

Slime bridge 最大的参考价值是它被放在 `polar` 包之外，说明 trainer adapter 不应该污染 rollout 核心。它负责：

```text
提交 async task batches
追踪 rollout id 和 policy version
给任务 metadata 打上 group_id、policy_version、rollout_step
过滤过旧的 off-policy group
暂停和恢复 gateway generation 以配合权重更新
把 Polar Trajectory 转成训练框架 Sample
过滤空 token、超长 trace、缺失 logprob 的样本
做 trajectory-aware group-normalized reward shaping
```

RepoHarness 对接 verl 时也应该保持这个方向：

```text
repo_harness_rollout_service
  不依赖 verl。

repo_harness_verl_adapter
  读取 RolloutGroupArtifact / TrainTrace，做 batch packing、staleness filtering、policy loss eligibility。
```

### 3.3 可借鉴点

1. `TaskRequest` 作为 rollout service 的 public contract。
2. rollout server 和 gateway node 分离。
3. gateway 生命周期分成 INIT、READY、RUNNING、POSTRUN。
4. runtime、agent harness、trajectory builder、evaluator 都用独立 spec 注入。
5. model API proxy 放在 harness 和 inference server 中间，而不是改 harness 内部循环。
6. completion record 同时保存 original request、transformed request、response 和 metadata。
7. `Trace` 以 token ids、loss mask、logprobs 和 messages 同时表达训练与审计。
8. prefix merging 使用严格 token prefix 条件，而不是文本相似度或消息 JSON 猜测。
9. trainer bridge 放在核心 rollout 包外。
10. metadata 中显式保留 `group_id`、`policy_version`、`rollout_step`，便于异步强化学习处理 staleness。

### 3.4 不能照搬点

1. 不应立刻复刻完整分布式 gateway、dashboard、多 provider proxy、Apptainer HPC 支持和复杂 runtime pool。RepoHarness 当前更需要先稳定 task ownership、bash 执行底座、hidden verifier 隔离和 TrainingView provenance。
2. Polar 默认 evaluator 在只有 outcome reward 时会广播 reward 到每个 trace。论文自己也说明 request-level reward broadcasting 会导致 reward hacking。RepoHarness 不应把这个默认策略直接用于长 SWE rollout。
3. `CompletionWriter` 在队列满时允许丢弃 on-disk persistence，虽然内存副本仍是 authoritative，但 RepoHarness 的审计和 acceptance 体系更强调可追溯证据，不能把训练关键原始记录只做 best-effort。
4. Polar 的安全重点是 native harness rollout，不覆盖 RepoHarness 需要的权限审批、用户隐藏约束、文件变更原子语义、public projection leak scan 等机制。
5. Polar 的 provider transform 复杂度高，RepoHarness 第一版 proxy 应优先只支持 OpenAI-compatible Chat Completions，避免工程范围爆炸。

## 4. PrimeIntellect verifiers 分析

### 4.1 核心定位

`reference/verifiers/verifiers/v1/README.md` 对 v1 的定义非常直接：

```text
Taskset defines what is being attempted.
Harness defines how the model or agent attempts it.
Env adapts one taskset/harness pair to the existing eval/training worker API.
```

这正是 RepoHarness 当前重定位最需要吸收的 ownership 规则。RepoHarness 不应该继续让一个单体 runtime 同时拥有任务加载、用户模拟、权限策略、工具表面、执行循环、hidden tests、reward 和 export projection。更合理的是把这些拆成一组可组合对象。

### 4.2 关键代码位置

v1 核心对象：

- `reference/verifiers/verifiers/v1/task.py`
- `reference/verifiers/verifiers/v1/taskset.py`
- `reference/verifiers/verifiers/v1/harness.py`
- `reference/verifiers/verifiers/v1/env.py`
- `reference/verifiers/verifiers/v1/state.py`
- `reference/verifiers/verifiers/v1/runtime.py`
- `reference/verifiers/verifiers/v1/user.py`
- `reference/verifiers/verifiers/v1/sandbox.py`
- `reference/verifiers/verifiers/v1/artifact.py`
- `reference/verifiers/verifiers/v1/config.py`
- `reference/verifiers/verifiers/v1/ENVIRONMENT_BEST_PRACTICES.md`

旧 composable 实验实现：

- `reference/verifiers/verifiers/envs/experimental/composable/composable_env.py`
- `reference/verifiers/verifiers/envs/experimental/composable/task.py`
- `reference/verifiers/verifiers/envs/experimental/composable/harness.py`
- `reference/verifiers/verifiers/envs/experimental/composable/tasksets/swe/swe_tasksets.py`
- `reference/verifiers/verifiers/envs/experimental/composable/harnesses/opencode.py`
- `reference/verifiers/verifiers/envs/experimental/composable/harnesses/mini_swe_agent.py`
- `reference/verifiers/verifiers/envs/experimental/composable/harnesses/rlm.py`

打包 harness 例子：

- `reference/verifiers/packages/harnesses/harnesses/opencode.py`
- `reference/verifiers/packages/harnesses/harnesses/mini_swe_agent.py`
- `reference/verifiers/packages/harnesses/harnesses/rlm.py`

### 4.3 Task

`Task` 位于 `verifiers/v1/task.py`。它是 `dict` 子类，但 `freeze()` 之后不可变，并且会做这些检查：

- `task.runtime` 不允许存在，runtime handle 应该在 state/runtime 层。
- `prompt` 和 `system_prompt` 会 normalize。
- `tools`、`toolsets`、`sandbox`、`artifacts`、`model` 会转成可序列化 config。
- `max_turns` 必须是整数。
- 所有字段最终必须可序列化。

RepoHarness 可以借鉴：

```text
Task 只放输入事实和任务控制，不放运行时句柄。
隐藏测试、权限策略、用户隐藏约束可以属于 TaskSet/Rubric/UserSimSpec，但进入模型可见投影前必须有 public-safe 视图。
每条 task 只覆盖真正按样本变化的字段，不复制全局默认配置。
```

### 4.4 TaskSet

`Taskset` 位于 `verifiers/v1/taskset.py`。它拥有：

- task loading
- split selection
- taskset_id
- taskset-side system prompt
- user
- bindings
- objects
- artifacts
- toolsets
- lifecycle handlers
- metrics / rewards / advantages

RepoHarness 应该将这些职责从 runtime 中剥离：

```text
InteractiveRefactorTaskSet:
  加载仓库任务、用户需求、隐藏约束、public tests、hidden tests、permission policy。

SWEBenchTaskSet:
  加载 SWE-Bench / SWE-Gym 风格任务、base commit、测试计划和 scoring metadata。

PermissionBenchTaskSet:
  加载专门评测越权编辑、用户审批、拒绝恢复能力的任务。
```

### 4.5 Harness

`Harness` 位于 `verifiers/v1/harness.py`。它拥有：

- rollout execution
- program config
- model/client defaults
- endpoint interception
- primary sandbox placement
- command/framework adapter
- execution artifacts

它支持多种 `ProgramConfig`：

```text
base endpoint-backed tool loop
importable Python program
local or sandboxed command
```

RepoHarness 应该将“怎么尝试一个任务”放在 HarnessSpec/HarnessRunner：

```text
RepoHarnessNativeHarness:
  使用 RepoHarness 自己的 tool registry、permission gate、artifact recorder 和 TrainingView。

MiniSWEHarness:
  使用 mini-swe-agent shell command，模型调用走 proxy。

OpenCodeHarness:
  使用 OpenCode command，模型调用走 proxy。

ExternalShellHarness:
  用任意 shell command 执行外部 agent。
```

注意：RepoHarness 自己不应该再拥有 task 的 hidden reward 或用户隐藏约束。它应该只负责执行协议、工具路由、权限询问、event logging 和 trajectory construction。

### 4.6 Env

`Env` 位于 `verifiers/v1/env.py`。它只把一个 Taskset 和一个 Harness 适配到已有 eval/training worker API。`EnvConfig` 明确禁止在根配置上继续添加额外字段，要求环境专属字段放到 `TasksetConfig` 或 `HarnessConfig`。

这个规则对 RepoHarness 很有价值：它防止“新需求都往 EnvConfig 或 RuntimeOptions 上塞”，从而保持 ownership 清晰。

RepoHarness 未来可以定义：

```text
RepoComposableEnv:
  taskset: RepoTaskSet
  harness: HarnessSpec
  sandbox: SandboxSpec
  user_sim: UserSimSpec
  permission: PermissionSpec
  rubric: Rubric
```

但根对象应尽量只做组合和 worker adapter，不应继续承载领域逻辑。

### 4.7 State

v1 的 `State` 复用顶层 `verifiers.State`，但通过 `State.for_task(...)` 进入 v1 contract。`reference/verifiers/verifiers/types.py` 中有重要 helper：

- `state.runtime_state()`
- `state.get_model()`
- `state.get_client(...)`
- `state.get_endpoint_config(...)`
- `state.get_tools()`
- `state.add_tool(...)`
- `state.add_step_reward(...)`

这说明 `State` 是 rollout output 和 runtime handle 的桥，但 runtime handle 不属于 Task。RepoHarness 当前已有 `RepoHarnessEpisodeResult`、TrainingView、artifact refs、run metadata 等对象，后续可以引入一个更清晰的 `EpisodeState`：

```text
serializable output:
  messages / events / metrics / reward / artifacts / final_patch / diagnostics

runtime handles:
  model client / sandbox / workspace facade / artifact writer / permission session
```

序列化前必须 strip runtime handles。

### 4.8 User

`User` 位于 `verifiers/v1/user.py`。它可以有 `scope`、bindings、objects、artifacts 和 sandbox，并通过 `get_response(task, state, messages)` 返回环境中的 user messages。

这对 RepoHarness 非常重要。RepoHarness 如果要训练真实交互式 SWE agent，就不能只把用户审批当作一个工具返回值。更合理的是：

```text
UserSimSpec / User:
  定义用户画像、隐藏偏好、批准策略、拒绝策略、澄清回复、疲劳成本。

PermissionSpec:
  定义哪些路径、命令、网络、git 操作需要 allow / deny / approval。

Harness:
  只负责在需要时调用 user channel 或 permission gate。
```

### 4.9 Sandbox

`SandboxConfig` 位于 `verifiers/v1/sandbox.py`，字段包含 image、CPU、memory、disk、GPU、network、timeout、setup commands、scope 等。RepoHarness 当前已有 workspace backend 和 Docker adapter，但 Stage 16G.3 如果引入宽 Bash，就必须将 sandbox spec 升级为一等对象。

特别需要对齐的点：

```text
每个 episode 一个隔离 workspace。
bash、read_file、grep、apply_patch 看到同一个 candidate workspace。
默认无网络或显式网络 policy。
hidden verifier、gold patch、runtime-private artifact 不挂载到 rollout workspace。
最终 grading 在 clean grader checkout 中重放 cleaned final.patch。
```

### 4.10 Artifact

`ArtifactConfig` 位于 `verifiers/v1/artifact.py`，只定义 path、format、key、optional，并从 runtime 中收集。RepoHarness 的 artifact 需求更强，已有 raw restricted audit artifact 和 public projection。可借鉴的是 ownership，不是功能复杂度：

```text
TaskSet / Harness / User / Toolset 可以声明自己要收集的 artifact。
ArtifactStore 负责 materialization、脱敏、引用和生命周期。
TrainingView 只引用 public-safe opaque ref，不泄露本机路径。
```

### 4.11 Rubric / Reward

verifiers 中旧 `Rubric` 位于 `verifiers/rubrics/rubric.py`，v1 中更推荐用 lifecycle decorators 和 scoring utils：

- `reference/verifiers/verifiers/v1/utils/scoring_utils.py`
- `@vf.metric`
- `@vf.reward`
- `@vf.advantage`

对 RepoHarness 来说，Rubric 不应该只是 `reward_fn(output)`。它至少应该能组合：

```text
hidden tests
public tests
forbidden diff checker
test tamper checker
permission violation checker
API compatibility checker
user burden score
denial recovery score
process reward 或行为 judge
```

这些 scoring 逻辑应属于 TaskSet/Rubric，而不是 Harness。

### 4.12 可借鉴点

1. 用 TaskSet 和 Harness 明确分开“尝试什么”和“如何尝试”。
2. Task 冻结后不可变，禁止 runtime handle 混入 task data。
3. Env 只做 worker adapter，不让根配置继续膨胀。
4. User 是一等对象，适合承载 RepoHarness 的用户模拟和审批交互。
5. Sandbox、Artifact、Toolset、bindings 都是可声明、可组合对象。
6. lifecycle handlers 让 setup、update、reward、cleanup 等逻辑按 owner 收敛。
7. packaged harnesses 展示了如何把外部 CLI agent 包装成可复用 Harness。

### 4.13 不能照搬点

1. verifiers v1 很新，仓库里仍保留旧 experimental composable 代码。RepoHarness 应借鉴 ownership，不应直接依赖旧实验 API。
2. Prime 的 sandbox 生态、package loader、registry 和 `prime env push` 流程不适合作为 RepoHarness 主线。
3. verifiers 的默认 Base Harness 更适合通用 tool loop，不覆盖 RepoHarness 的五道安全防线、file mutation 原子语义和 public projection leak scan。
4. v1 的 reward/scoring 机制可作为抽象参考，但 RepoHarness 的 reward boundary、policy_loss eligibility 和 hidden verifier 隔离比它更严格，不能降级。

## 5. research-environments 分析

### 5.1 当前仓库结构差异

`reference/research-environments/README.md` 仍提到旧的 `tasksets/swe/`、`harnesses/opencode/` 等目录，但当前本地仓库主要把具体环境放在 `environments/` 下。例如：

- `reference/research-environments/environments/swe`
- `reference/research-environments/environments/rlm_swe`
- `reference/research-environments/environments/opencode_swe`
- `reference/research-environments/environments/mini_swe_agent_plus`
- `reference/research-environments/environments/opencode_deepdive`
- `reference/research-environments/environments/opencode_science`

分析时应以当前代码为准。

### 5.2 SWE environment

关键文件：

- `reference/research-environments/environments/swe/README.md`
- `reference/research-environments/environments/swe/swe/swe.py`

`load_environment(...)` 做了三件事：

1. 用 `make_swe_taskset(backend=task_type, **swe_kwargs)` 创建 SWE taskset。
2. 用 `rlm_harness(...)` 创建 harness。
3. 用 `ComposableEnv(taskset=taskset, harness=..., keep_sandbox_for_scoring=True, ...)` 组合成环境。

这说明一个 SWE environment 不应直接等同于某个 agent loop。SWE taskset 可以换 harness，harness 也可以换 taskset。RepoHarness 应该把当前的 SWE 仓库任务、交互式 refactor 任务、权限任务都定义成 TaskSet，然后将 RepoHarness native harness、mini-swe-agent harness、OpenCode harness 作为可替换执行器。

### 5.3 RLM SWE environment

关键文件：

- `reference/research-environments/environments/rlm_swe/README.md`
- `reference/research-environments/environments/rlm_swe/rlm_swe/rlm_swe.py`
- `reference/research-environments/environments/rlm_swe/rlm_swe/behavior.py`

它在基础 SWE task reward 之外引入 behavior reward shaping。重要设计是：

```text
task_reward = base rubric reward
behavior_reward = behavior judge 对可观察行为的评分
final_reward = task_reward + alpha * behavior_reward，只在 task_reward == 1.0 时叠加
```

这对 RepoHarness 的用户交互和权限训练很有参考价值。RepoHarness 可以将行为奖励定义为：

```text
是否先复现问题
是否运行目标测试和更广测试
是否避免无关文件改动
是否正确请求权限
被拒绝后是否恢复
是否避免修改 public tests 来作弊
是否向用户给出清晰进展
```

但行为奖励不能替代 hidden verifier。它应该作为 solved rollout 的质量加分或 offline analysis 信号，而不是让 unsolved patch 因为“行为看起来好”获得高主 reward。

### 5.4 OpenCode SWE environment

关键文件：

- `reference/research-environments/environments/opencode_swe/README.md`
- `reference/research-environments/environments/opencode_swe/opencode_swe/opencode_swe.py`

`opencode_swe` 展示了如何将 OpenCode harness 与 SWE taskset 组合。它把 OpenCode provider 配成 intercepted model，例如：

```text
provider_key="intercepted"
model_id="intercepted/model"
provider_timeout_ms=3600000
```

这说明外部 harness 的模型调用边界应由环境或 harness config 控制，训练基础设施可以把真实模型 endpoint 替换成 proxy。

### 5.5 mini-swe-agent-plus

关键文件：

- `reference/research-environments/environments/mini_swe_agent_plus/README.md`

这个环境记录了大量真实 SWE rollout 工程问题：

- sandbox timeout
- command timeout
- sandbox out-of-memory
- sandbox image pull error
- patch broke test collection
- test output tail 收集
- deterministic patch breakage 不应触发重试
- setup / upload / background job 的 retry 策略

这些经验对 RepoHarness 的 verifier 和 runtime error taxonomy 很有价值。RepoHarness 不应把所有失败都压成 `infrastructure_error` 或 `verifier_failed`，而应明确区分：

```text
agent patch broke public test collection
sandbox timeout
command timeout
hidden verifier failure
public test diagnostic failure
training ineligible due to tamper
runtime infrastructure failure
```

### 5.6 可借鉴点

1. 同一个 SWE taskset 可以接 RLM、OpenCode、mini-swe-agent-plus 等 harness。
2. `keep_sandbox_for_scoring=True` 体现 rollout 和 scoring 的解耦需求。
3. 环境 loader 将 taskset args、harness args、sandbox args 分开。
4. 行为奖励可以作为 solved rollout 的质量塑形信号。
5. README changelog 记录了大量真实运行风险，可以作为 RepoHarness error taxonomy 的参考。

### 5.7 不能照搬点

1. 当前 research-environments 仍依赖 Prime sandbox 和 verifiers experimental composable API，不能直接作为 RepoHarness 主实现依赖。
2. 部分环境 loader 使用大量 kwargs 透传，容易掩盖 ownership。RepoHarness 应建立更严格的 Pydantic spec。
3. OpenCode / RLM / mini-swe-agent-plus 的环境主要解决 SWE patch outcome，不覆盖 RepoHarness 的用户审批、权限边界和 public projection 安全。
4. 行为 judge 依赖外部模型，不能成为 formal gate 的唯一依据。

## 6. renderers 分析

### 6.1 核心定位

`reference/renderers/README.md` 将 renderers 定义为 programmable chat templates。它解决的是多轮 RL 中非常关键的问题：

```text
训练器看到的 token ids 必须和 sampler 当时实际采样的 token ids 一致。
```

如果每轮都把 messages 用 `apply_chat_template` 重新渲染，可能出现：

- boolean round-trip：`false` 变成 `False`
- BPE retokenization drift
- tool-call XML drift
- historical thinking 被模板剥离
- max sequence length 截断后 anchor 失效
- agent scaffold 改写历史

这些问题都会让训练 token 和行为策略 token 不一致。

### 6.2 关键代码位置

- `reference/renderers/renderers/base.py`
- `reference/renderers/tests/test_bridge.py`
- `reference/renderers/tests/test_incremental.py`
- `reference/renderers/tests/test_roundtrip.py`
- `reference/renderers/tests/test_sampled_mask.py`
- `reference/renderers/tests/test_build_helpers.py`

`RenderedTokens` 位于 `renderers/base.py`，包含：

```text
token_ids
message_indices
sampled_mask
is_content
message_roles
message_tool_names
multi_modal_data
```

这些字段给训练样本构建提供了更强的 per-token attribution。RepoHarness 当前 `ResponseSpan` 已经表达 assistant_generation、tool_observation、environment_observation 等来源。如果要和 renderers 对齐，可以将 `message_indices`、`sampled_mask`、`is_content` 的思想映射到 `response_spans` 和 `response_mask`：

```text
assistant sampled token:
  response_mask=1
  source_type=assistant_generation

tool result / environment observation / canonical interstitial:
  response_mask=0
  source_type=tool_observation 或 environment_observation

renderer 无法证明安全续接:
  断链，形成新的 trace 或标记为 retokenized_ineligible
```

### 6.3 bridge_to_next_turn

`Renderer.bridge_to_next_turn(...)` 的契约是：

```text
如果返回值不为 None，那么返回 token 序列必须以 previous_prompt_ids + previous_completion_ids 开头。
它只追加下一轮 prompt 所需的新 token，不重新渲染过去模型采样的 assistant token。
如果不能证明安全，就返回 None，让调用方 fallback。
```

关键规则：

- clean stop 时使用已有 close token。
- truncation 时可以合成 canonical close，并把它作为非 loss prompt context。
- `new_messages` 中拒绝 assistant role，因为 assistant 内容是模型采样历史，重新渲染会替换真实 token。
- DefaultRenderer 无法证明模板 close，因此始终返回 None。

### 6.4 build_training_sample

`build_training_sample(...)` 使用 `sampled_mask` 和 `message_indices` 构造 loss mask。它强调：

- 默认应训练 renderer 标记为 sampled 的 token。
- 如果 renderer 没有 `sampled_mask`，必须显式提供 role filter。
- 对 tool response 做 SFT 时，应只训练正文，不训练模板 scaffold。

RepoHarness 的 TrainingView 已经有显式 `response_mask`，但如果未来要支持 renderer-driven prompt construction，应该记录：

```text
renderer_name
tokenizer_name
tokenization_source: proxy | renderer | re_rendered
bridge_status: bridged | fallback_full_render | unsafe_retokenized
```

如果 tokenization_source 是 `re_rendered`，不应默认进入 formal online policy loss。

### 6.5 可借鉴点

1. `bridge_to_next_turn` 是避免 retokenization drift 的核心接口。
2. `sampled_mask` 与 `is_content` 区分“模型是否采样”和“是否消息正文”。
3. `message_indices` 能用一次 render 构造 per-token attribution。
4. 不可证明安全时返回 None，而不是猜测。
5. hand-coded renderer 和 DefaultRenderer 的能力差异应进入 training eligibility。

### 6.6 不能照搬点

1. renderers 不是 rollout service，也不处理 sandbox、verifier、permission 和 artifacts。
2. 它需要特定 tokenizer 和模型模板，RepoHarness 不能假设所有 provider 都可用 hand-coded renderer。
3. 对外部 closed harness，model proxy 捕获的真实 token ids 比 renderer 重新构造更可靠。
4. renderer 不能修复 agent scaffold 在渲染前改写历史的问题，只能检测或规避 token 模板层 drift。

## 7. mini-swe-agent 分析

### 7.1 核心定位

mini-swe-agent 的价值是极简 baseline。它不是复杂训练基础设施，也不是权限化交互环境。它回答的问题是：

```text
如果只给模型 bash、线性历史和简单环境执行，模型能在 SWE 任务上做到什么程度？
```

这非常适合作为 RepoHarness 的对照组。

### 7.2 关键代码位置

- `reference/mini-swe-agent/README.md`
- `reference/mini-swe-agent/src/minisweagent/agents/default.py`
- `reference/mini-swe-agent/src/minisweagent/environments/local.py`
- `reference/mini-swe-agent/src/minisweagent/models/litellm_model.py`
- `reference/mini-swe-agent/src/minisweagent/models/utils/actions_toolcall.py`
- `reference/mini-swe-agent/src/minisweagent/config/mini.yaml`
- `reference/mini-swe-agent/docs/advanced/control_flow.md`

`DefaultAgent` 的核心循环很小：

```text
Agent.run 初始化 system/user messages。
Agent.step 调用 query，然后 execute_actions。
Model.query 返回 bash tool call。
Environment.execute 执行命令。
Model.format_observation_messages 把结果追加回 messages。
直到出现 role=exit。
```

`LocalEnvironment.execute(...)` 使用 `subprocess.run(shell=True)` 执行命令。每次动作独立，命令状态不跨 shell session 持久化。提交靠 magic command：

```bash
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
```

`actions_toolcall.py` 只定义一个 `bash` tool，参数是：

```json
{"command": "string"}
```

### 7.3 对 RepoHarness 的参考价值

mini-swe-agent 适合做：

1. bash-only baseline。
2. 验证“模型可见工具面越简单，模型能力上限是什么”。
3. 对照 RepoHarness 的结构化编辑、权限审批、用户模拟是否带来增益。
4. 对照 Stage 16G.3 采用宽 Bash 后，RepoHarness 是否仍然需要私有 DSL。
5. 作为 Polar-lite external harness 的第一批 proxy 接入对象。

### 7.4 不能照搬点

1. mini-swe-agent 没有隐藏约束和权限系统。
2. 它没有强 artifact visibility 分层。
3. 它没有 token-faithful trajectory builder。
4. 它没有 async rollout service。
5. 它默认 local subprocess 并不等同于 RepoHarness 需要的 SEE 等价隔离。
6. 它对用户交互和审批的表达很弱，不适合作为 RepoHarness 的最终产品形态。

## 8. 对 RepoHarness 新架构的建议

### 8.1 建议采用的总体组合

我建议采用：

```text
Prime-style composable environment
+
Polar-style rollout-as-a-service / model proxy
+
verl adapter
```

这个组合合理，原因如下：

1. Prime-style ownership 解决 RepoHarness 内部“谁拥有任务、用户、权限、sandbox、reward”的问题。
2. Polar-style rollout service 解决“训练器如何异步消费长链路 harness 执行”的问题。
3. Model proxy 解决“如何低侵入接入外部真实 harness，并保留 token-level provenance”的问题。
4. renderers 解决“native capture 或 proxy 不可用时，如何尽量减少 multi-turn token drift”的问题。
5. mini-swe-agent 提供最小 bash-only baseline，避免 RepoHarness 只和自己比较。

### 8.2 建议的新分层

建议将 RepoHarness 长期架构拆成以下层：

```text
Core object model:
  Task
  TaskSet
  State
  Artifact
  Rubric
  UserSim
  PermissionSpec
  SandboxSpec

Harness layer:
  RepoHarnessNativeHarness
  MiniSWEHarness
  OpenCodeHarness
  ExternalShellHarness

Runtime / execution plane:
  EnvironmentRuntime
  EpisodeWorkspace
  SEEEquivalentSandbox
  ToolExecutor
  CommandMonitor
  TestTrustClassifier
  PatchHygiene

Rollout service:
  RolloutServer
  GatewayWorker
  SessionLifecycle
  ModelProxy
  CompletionCapture
  TrajectoryBuilder
  EvaluatorRunner

Training interface:
  RolloutGroupArtifact
  TrainTrace
  VerlAdapter
  PolicyLossEligibility
  StalenessFilter
```

### 8.3 RepoHarness 在这个架构中的位置

RepoHarness 不应该等同于整个 environment。更准确地说：

```text
RepoHarnessNativeHarness 是一个 Harness。
InteractiveRefactorTaskSet / SWEBenchTaskSet / PermissionBenchTaskSet 是 TaskSet。
RepoPermissionRubric / SWERubric / UserBurdenRubric 是 Rubric。
RepoRolloutServer 是 rollout infrastructure。
VerlAdapter 是训练框架桥接层。
```

这样做的好处是：

- 同一个任务可以用 RepoHarness、mini-swe-agent、OpenCode、Codex-like harness 运行。
- 同一个 RepoHarness harness 可以运行 SWE repair、权限任务、交互式 refactor、用户模拟任务。
- 训练数据不再绑定单一工具表面，可以比较不同 harness action protocol 的 RL gain。
- formal gates 可以针对 artifact schema、token provenance、reward boundary 和 permission facts，而不是绑死某个入口函数。

### 8.4 Stage 16G.3 的影响

当前 Stage 16G.3 正处于设计冻结前，外部代码给出的方向和 `docs/harness_improve/bash_tool_advice.md` 一致：

```text
模型可见工具应更接近 bash(command: string)。
内部用 SEE 等价执行底座、网络隔离、git/test 防作弊、artifact 分层和 training eligibility 守住边界。
```

但这里有硬前提：

```text
如果不能证明每个 episode 有隔离 workspace、默认断网、hidden verifier 不挂载、最终 grading 在 clean checkout 中 replay cleaned final.patch，那么宽 Bash 不能进入 swe_public_core。
```

建议 Stage 16G.3 不要继续强化 `command_profile_id + structured args` 作为模型主表面。可以把 project test routing 做成内部 classifier：

```text
模型调用:
  bash("python -m pytest tests/test_parser.py::test_empty_input -q")

内部记录:
  semantic_command_kind = project_test
  runner = pytest
  selector = tests/test_parser.py::test_empty_input
  public_test_source_clean = true
  official_feedback_eligible = true
```

这样模型学习的是真实 SWE agent 行为，RepoHarness 学到的是可审计和可训练的执行事实。

### 8.5 TrainingView 的建议升级

RepoHarness 当前 `TrainingView` 已经有良好基础。建议未来增加或明确以下事实：

```text
tokenization_source:
  proxy_capture
  native_gateway_capture
  renderer_bridge
  full_rerender

renderer_name:
  qwen3
  qwen35
  default
  none

token_provenance_status:
  behavior_policy_exact
  renderer_bridge_exact
  retokenized_ineligible
  missing_logprobs

trace_builder:
  per_request
  per_turn
  prefix_merging

session_credit_assignment:
  outcome_reward_session_level
  process_reward_trace_level
  group_normalized
```

formal online RL 守门逻辑应坚持：

```text
缺少 response_logprobs 不能进 formal policy loss。
非 verl route 或非 behavior-policy token 不能默认进 online RL。
full_rerender token 不能默认进 online policy loss。
session-level reward 不能盲目广播到大量 request-level traces 后训练。
```

## 9. 建议实施路线

### Phase 1：Prime-style ownership 冻结

目标是定义 RepoHarness 自己的 composable object model，不需要立刻大改所有旧代码。

建议产物：

```text
Task
TaskSet
HarnessSpec
SandboxSpec
UserSimSpec
PermissionSpec
Rubric
ArtifactSpec
EpisodeState
ComposableEnv
```

第一批 taskset：

```text
SWEBenchLikeTaskSet
InteractiveRefactorTaskSet
RepoPermissionBenchTaskSet
```

第一批 harness：

```text
RepoHarnessNativeHarness
MiniSWEHarness
```

### Phase 2：Stage 16G.3 宽 Bash 的 SEE 等价底座

只在硬门槛满足后开放：

```text
bash(command: string)
每个 episode 隔离 workspace
默认 network=none
同一 episode 工具共享 candidate workspace
命令审计、测试分类、git/history/network/test tamper monitor
raw artifact restricted，sanitized artifact model-visible
clean final.patch 在 grader-only checkout 中 replay
```

### Phase 3：RepoHarness native token capture

先在 RepoHarness 自己的 LLMGateway 路径记录：

```text
prompt_ids
response_ids
response_logprobs
loss mask
tool schema
finish reason
policy_version
rollout_step
group_id
```

这一步不需要完整 proxy，但 schema 要和 proxy capture 兼容。

### Phase 4：Polar-lite rollout service

实现最小 API：

```text
POST /rollouts
GET /rollouts/{id}
GET /rollouts/{id}/artifact
POST /callbacks/session_result
```

内部按 gateway lifecycle 执行：

```text
INIT -> READY -> RUNNING -> POSTRUN -> CLEANUP
```

### Phase 5：OpenAI-compatible model proxy

第一版只支持：

```text
POST /v1/chat/completions
non-streaming
token ids
logprobs
session_id
completion journal
```

第一批 external harness：

```text
mini-swe-agent
OpenCode
```

### Phase 6：verl adapter

verl 不应直接 import `RepoHarnessRuntime.run_episode`。建议改成：

```text
verl worker
  -> submit rollout group
  -> receive RolloutGroupArtifact
  -> pack TrainTrace
  -> apply policy loss eligibility
```

adapter 负责：

```text
batch packing
staleness filtering
group normalization
invalid sample filtering
policy_loss_candidate gating
metrics export
```

### Phase 7：prefix merging 与更强 credit assignment

等长轨迹真实数据稳定后，再做：

```text
prefix_merging
session-level reward normalization
process reward model
behavior judge
trace-level advantage assignment
```

## 10. 后续阅读关键文件清单

### Polar / ProRL-Agent-Server

- `reference/ProRL-Agent-Server/README.md`
- `reference/ProRL-Agent-Server/src/polar/rollout/models.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/server.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/manager.py`
- `reference/ProRL-Agent-Server/src/polar/rollout/balancer.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/server.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/node.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/storage.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/completion_writer.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/detection.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/transform/openai_chat.py`
- `reference/ProRL-Agent-Server/src/polar/gateway/transform/anthropic.py`
- `reference/ProRL-Agent-Server/src/polar/runtime/models.py`
- `reference/ProRL-Agent-Server/src/polar/agent/models.py`
- `reference/ProRL-Agent-Server/src/polar/agent/base.py`
- `reference/ProRL-Agent-Server/src/polar/agent/presets/shell.py`
- `reference/ProRL-Agent-Server/src/polar/agent/presets/codex.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/models.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/builder/record_utils.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/builder/per_request.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/builder/prefix_merging.py`
- `reference/ProRL-Agent-Server/src/polar/trajectory/evaluator/swebench_harness.py`
- `reference/ProRL-Agent-Server/src/slime_bridge/README.md`
- `reference/ProRL-Agent-Server/src/slime_bridge/rollout.py`
- `reference/ProRL-Agent-Server/src/slime_bridge/adapter.py`
- `reference/ProRL-Agent-Server/src/slime_bridge/reward_post_process.py`
- `reference/ProRL-Agent-Server/examples/swegym_slime_grpo/polar_config.yaml`

### Prime verifiers

- `reference/verifiers/verifiers/v1/README.md`
- `reference/verifiers/verifiers/v1/ENVIRONMENT_BEST_PRACTICES.md`
- `reference/verifiers/verifiers/v1/task.py`
- `reference/verifiers/verifiers/v1/taskset.py`
- `reference/verifiers/verifiers/v1/harness.py`
- `reference/verifiers/verifiers/v1/env.py`
- `reference/verifiers/verifiers/v1/runtime.py`
- `reference/verifiers/verifiers/v1/user.py`
- `reference/verifiers/verifiers/v1/sandbox.py`
- `reference/verifiers/verifiers/v1/artifact.py`
- `reference/verifiers/verifiers/v1/config.py`
- `reference/verifiers/verifiers/v1/utils/scoring_utils.py`
- `reference/verifiers/verifiers/types.py`
- `reference/verifiers/verifiers/rubrics/rubric.py`
- `reference/verifiers/packages/harnesses/harnesses/opencode.py`
- `reference/verifiers/packages/harnesses/harnesses/mini_swe_agent.py`
- `reference/verifiers/packages/harnesses/harnesses/rlm.py`
- `reference/verifiers/verifiers/envs/experimental/composable/composable_env.py`
- `reference/verifiers/verifiers/envs/experimental/composable/task.py`
- `reference/verifiers/verifiers/envs/experimental/composable/harness.py`
- `reference/verifiers/verifiers/envs/experimental/composable/tasksets/swe/swe_tasksets.py`

### research-environments

- `reference/research-environments/README.md`
- `reference/research-environments/environments/swe/README.md`
- `reference/research-environments/environments/swe/swe/swe.py`
- `reference/research-environments/environments/rlm_swe/README.md`
- `reference/research-environments/environments/rlm_swe/rlm_swe/rlm_swe.py`
- `reference/research-environments/environments/rlm_swe/rlm_swe/behavior.py`
- `reference/research-environments/environments/opencode_swe/README.md`
- `reference/research-environments/environments/opencode_swe/opencode_swe/opencode_swe.py`
- `reference/research-environments/environments/mini_swe_agent_plus/README.md`

### renderers

- `reference/renderers/README.md`
- `reference/renderers/renderers/base.py`
- `reference/renderers/renderers/qwen3.py`
- `reference/renderers/renderers/qwen35.py`
- `reference/renderers/renderers/glm45.py`
- `reference/renderers/tests/test_bridge.py`
- `reference/renderers/tests/test_incremental.py`
- `reference/renderers/tests/test_roundtrip.py`
- `reference/renderers/tests/test_sampled_mask.py`
- `reference/renderers/tests/test_build_helpers.py`

### mini-swe-agent

- `reference/mini-swe-agent/README.md`
- `reference/mini-swe-agent/src/minisweagent/agents/default.py`
- `reference/mini-swe-agent/src/minisweagent/environments/local.py`
- `reference/mini-swe-agent/src/minisweagent/models/litellm_model.py`
- `reference/mini-swe-agent/src/minisweagent/models/utils/actions_toolcall.py`
- `reference/mini-swe-agent/src/minisweagent/config/mini.yaml`
- `reference/mini-swe-agent/docs/advanced/control_flow.md`

### RepoHarness 当前对照文件

- `src/repo_harness/rl/runtime.py`
- `src/repo_harness/rl/training_view.py`
- `src/repo_harness/evaluation/episode_projection.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/tools/file_mutation.py`
- `src/repo_harness/rl/visibility.py`
- `docs/agentic_RL/repo_harness_verl_workstreams/56-stage-16g-3-preplan-design-decisions.md`
- `docs/harness_improve/bash_tool_advice.md`

## 11. 最终建议

RepoHarness 应该采用“Prime-style 可组合环境 + Polar-style rollout service / model proxy + verl adapter”的新定位。这个方向合理，而且比单独做 `RepoHarness + verl` 更强，因为它同时回答了三个问题：

```text
环境内部如何拆分 ownership？
已有真实 harness 如何低侵入接入训练？
长链路 SWE rollout 如何输出 token-faithful、可审计、可过滤的训练轨迹？
```

但实施上必须避免三个误区：

1. 不要把 RepoHarness 改成 Polar clone。RepoHarness 的独特价值是用户模拟、权限边界、文件变更审计、hidden verifier 和 public projection 安全。
2. 不要把 Prime verifiers 代码直接作为主依赖。应学习它的 ownership 和 loader discipline，结合 RepoHarness 现有 gate、inspector 和 artifact 安全体系重建本项目对象模型。
3. 不要把 mini-swe-agent 当作目标架构。它是极好的 baseline，但不是交互式、权限化、长链路训练基础设施。

最短可行路径是：

```text
先冻结 composable ownership。
再完成 SEE 等价 Bash 执行底座。
再做 native token capture。
再做 Polar-lite rollout service。
再接一个 OpenAI-compatible proxy 和 mini-swe-agent external harness。
最后再把 verl adapter 改为消费 RolloutGroupArtifact，而不是直接消费 RepoHarness 内部 episode 对象。
```

这样 RepoHarness 才能从“一个已经接入 verl 的 SWE harness”升级为“面向真实和半真实软件工程智能体训练的环境工厂、rollout 服务和训练轨迹基础设施”。
