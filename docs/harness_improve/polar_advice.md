#ANS1:
我读完后的判断是：**这篇 Polar 对你的项目很有参考价值，但它不是在讲“如何设计 SWE harness 的工具和权限”，而是在讲“如何把任意已有 harness 变成可训练的 RL rollout 环境”。**

所以结论不是“RepoHarness 要照抄 Polar”，而是：

> **继续做 Composable Environments；同时在 execution / training interface 层加入一个 Polar-like 的 rollout substrate。RepoHarness 是第一个可组合环境族，Polar-like 层负责把 RepoHarness、Codex-like、Claude-Code-like、mini-SWE-agent-like 等不同 harness 的真实执行轨迹转成 verl 可消费的 token-faithful RL 样本。**

---

## 1. 这篇工作的核心内容

这篇论文叫 **Polar: Agentic RL on Any Harness at Scale**。它要解决的问题是：真实 agent harness 越来越复杂，比如 Codex、Claude Code、Qwen Code、OpenCode、Pi 这类工具本身就有自己的工具调用、上下文管理、子代理、patch 提交流程、runtime 启动逻辑。如果为了 RL 训练把这些 harness 重写成某个 Gym-style environment，往往会丢失真实产品 harness 的关键行为。Polar 的核心想法是：**不要重写 harness，而是在模型 API 边界拦截它的 LLM 请求，记录 token-level 数据，再重建训练轨迹。** ([arXiv][1])

它的关键架构有四部分：

```text
1. rollout server
   接收 task request，展开成多个 session。

2. gateway node
   负责 runtime 初始化、harness 执行、trajectory reconstruction、evaluation、cleanup。

3. model API proxy
   放在 harness 和 inference server 之间，兼容 Anthropic / OpenAI Chat / OpenAI Responses / Google generateContent 等请求格式。

4. trajectory builder
   把捕获到的模型请求、采样 token、logprob、工具 schema、reward 和 metadata 转成 trainer-facing trace。
```

论文强调，Polar 的边界在 **model endpoint**，不是工具接口，不是 harness SDK，不是环境 API。proxy 捕获 prompt token ids、sampled response token ids、logprobs、finish reason 等信息，然后把 response 转回 harness 期待的 provider 格式。这样 harness 可以原样运行，训练系统仍然能拿到 token-faithful training sample。([arXiv][1])

---

## 2. Polar 和你之前的 Composable Environments 不是同一层

你之前提出的方向是：

```text
Task / TaskSet / SandboxSpec / Harness / Rubric / ComposableEnv
Control plane / Execution plane / Verification plane / Training interface
```

这个抽象回答的是：

```text
我要生成、组合、实例化和验证什么环境？
```

Polar 回答的是另一个问题：

```text
给定一个已经存在的 harness，我如何不改它，却把它的真实执行过程变成 RL 可训练轨迹？
```

所以二者是互补关系：

```text
ComposableEnv:
  定义环境、任务、sandbox、harness、rubric。

Polar-like Rollout Layer:
  执行某个 HarnessSpec，并从模型 API 边界捕获 token-faithful trajectory。

verl Adapter:
  消费 rollout group、reward、loss mask、staleness metadata。
```

你上传的 composable environment 文档里已经把环境生成看成 control plane、execution plane、verification plane、training interface 的多平面系统，并强调长程 agentic RL 的原子对象不再是 sample row，而是带状态、工具、验证和 lineage 的 environment artifact。Polar 正好补上了 “execution/training interface 如何低侵入接入真实 harness” 这一层。

---

## 3. 这篇论文最值得你借鉴的 5 个点

### 3.1 Harness-native RL：不要把真实 harness 重写成训练 DSL

Polar 的最强结论是：**训练应该发生在真实 harness 执行路径上。**

它在实验里用同一个 Qwen3.5-4B base model，分别在 Codex、Claude Code、Qwen Code、Pi 四种 coding harness 上做 GRPO。结果 SWE-Bench Verified 上分别提升了 22.6、4.8、0.6、6.2 个百分点。论文特别解释 Codex 上提升最大，是因为 Codex 的 action protocol、context policy、patch submission style 对 Qwen base 很陌生；Polar 保持 Codex harness 不变，把 reward 直接接到实际 sampled tokens 上，因此 RL 优化的是 evaluation 时真正会用到的行为。([arXiv][1])

这对你的项目非常直接：

```text
不要只训练 RepoHarness 私有工具 schema。
要让模型能在 RepoHarness、Codex-like、Claude-Code-like、mini-SWE-agent-like 等真实或仿真 harness 上训练。
```

这也支持你之前的判断：`run_project_test(selector=...)` 这类工具不应成为唯一默认模型可见接口；模型应该学会真实 harness 中的 bash / exec command / editor / patch submission style，然后内部记录 test route 和 trust facts。

---

### 3.2 API proxy 比“改 harness 代码”更适合多 harness 泛化

Polar 的 proxy 层检测 provider API，归一化请求，添加训练需要的 logprobs 字段，转发到本地 inference server，再把响应转回原 provider shape。它明确说 proxy boundary 在 agent framework 之下，不需要理解 harness 如何 planning、如何管理工具、何时停止，只需要保持 API 兼容并记录足够训练样本。([arXiv][1])

对你的项目来说，这意味着：

```text
短期：
  RepoHarness 自己可以内部记录 trajectory，因为你拥有代码。

中期：
  如果要训练 Codex-like / Claude-Code-like / mini-SWE-agent-like harness，
  不要强行改它们的工具 loop；
  应该用一个 OpenAI/Anthropic-compatible model proxy 捕获模型调用。
```

这正好符合你“训练-serving consistent”的定位：真实 harness 走真实执行路径，RL 只在模型边界观察和训练。

---

### 3.3 Token-faithful trajectory reconstruction 非常重要

Polar 反复强调 token fidelity：训练信号必须绑定到 behavior policy 实际采样的 tokens。简单把最终 transcript 重新 tokenize 可能产生 drift。Polar 的做法是：generated assistant tokens 来自 inference response，非模型生成的 interstitial tokens 来自 canonical prompt tokenization，并且 loss mask 只标记 behavior-policy tokens 为 trainable。([arXiv][1])

这对你的 verl 接入很关键。你现在如果只是保存：

```json
messages = [{"role": "...", "content": "..."}]
```

然后训练前重新 tokenize，就有潜在问题：

```text
tool-call JSON canonicalization 变了
provider 格式变了
系统插入的工具结果渲染变了
assistant sampled tokens 和重新编码 tokens 不完全一致
loss mask 标错
```

你应该借鉴 Polar 的 trace schema：

```text
prompt_ids
response_ids
response_logprobs
loss_mask
prompt_messages
response_messages
tools
reward
metadata
```

论文的代表性 trace 也正是这个结构。([arXiv][1])

---

### 3.4 Prefix merging：长轨迹不要简单拆成每次请求训练

Polar 提供两种 trajectory builder：

```text
per_request:
  每次模型 completion 单独变成一个 trace，最保守但会碎片化。

prefix_merging:
  如果后续 prompt 是前面 prompt + sampled assistant response + harness interstitial 的严格 token 前缀延续，
  就把多个 completion 合并成更长 trace；
  sampled assistant tokens mask=1，harness 插入的 interstitial tokens mask=0。
```

它们的实验显示，在相同 workload 下，prefix merging 把 trainer-facing updates 从 1185 个减少到 218 个，wall-clock 从 189.5 分钟降到 35.2 分钟，约 5.39 倍，并显著提高 rollout GPU utilization。论文还说，直接把 outcome reward 广播给每个 per-request trace 会出现明显 reward hacking，因为 request-level trace 收到了 session-level credit，credit assignment 很吵。([arXiv][1])

这对你的项目有两个建议：

```text
第一版可以先做 per-session / per-request 保守版本；
但不要把 session-level reward 简单广播到每个小 request 上训练。

第二版要实现 prefix_merging 或 session-level normalization；
否则长 SWE rollout 会出现训练噪声和 reward hacking。
```

---

### 3.5 Rollout-as-a-service：verl 不应该直接调用 RepoHarness 内部函数

Polar 把 rollout server、gateway node、runtime setup、harness execution、trajectory reconstruction、evaluation、trainer callback 分成服务边界。一个 session 有 session id、task id、timeout budget、runtime spec、agent spec、trajectory builder、evaluator、callback URL；gateway 负责启动 runtime、准备 harness、运行 harness、构建 trajectory、评估输出、清理资源并回调。([arXiv][1])

这和你之前的 ComposableEnv 图完全一致：control plane 决定生成什么，execution plane 物化环境，verification plane 评分，training interface 输出 rollout group 和 metadata。你的项目文档也已经强调，这些 plane 运行在不同 clock 上，异步 RL 中需要追踪环境版本、policy version、trajectory lineage 和 staleness。

所以 RepoHarness 不应长期是：

```text
verl worker 直接 import repo_harness.run_episode(...)
```

更好的边界是：

```text
verl / trainer
  -> submit rollout task
  -> rollout service / gateway
  -> EnvironmentRuntime
  -> HarnessRunner
  -> ModelProxy / CompletionCapture
  -> Evaluator
  -> TrajectoryBuilder
  -> callback rollout result
```

---

## 4. 你的项目是否需要借鉴 Polar？

**需要，但不要现在就完整复刻 Polar。**

更准确地说：

```text
需要借鉴：
  架构边界、model API proxy、token-faithful trajectory、rollout-as-service、prefix merging、multi-harness training。

暂时不需要完整实现：
  分布式 gateway 集群、完整 provider proxy 兼容、dashboard、所有外部 harness preset、复杂 runtime pooling。
```

你当前真正应该做的是一个 **Polar-lite layer**。

---

## 5. 我建议你如何应用到 RepoHarness

### Step 1：把 ComposableEnv 和 RolloutService 分清

你现在可以把项目架构定成：

```text
ComposableEnv 层：
  Task / TaskSet / SandboxSpec / HarnessSpec / Rubric

Runtime 层：
  EnvironmentRuntime / SandboxInstance / HarnessRunner

Polar-lite 层：
  ModelProxy / CompletionCapture / TrajectoryBuilder / EvaluatorCallback

Training 层：
  verl_adapter / rollout_group_packager / reward_components
```

也就是说：

```text
RepoHarness = 一个 SWE HarnessSpec + SWE Runtime + SWE Rubric
Polar-lite = 任何 HarnessSpec 的 rollout 捕获和训练样本重建层
```

不要把它们混成一个大类。

---

### Step 2：先支持你自己的 RepoHarness native capture

第一阶段不需要完整 API proxy。因为你拥有 RepoHarness 的 agent loop，可以直接在内部记录：

```text
prompt_ids
sampled_response_ids
response_logprobs
loss_mask
tool definitions
tool calls
tool results
reward
metadata
```

但是 schema 要按 Polar 风格设计，这样后面能无缝切到 proxy capture。

你的 `TrainingView` 应该升级为：

```python
class TrainTrace:
    prompt_ids: list[int]
    response_ids: list[int]
    response_logprobs: list[float]
    loss_mask: list[int]
    prompt_messages: list[dict]
    response_messages: list[dict]
    tools: list[dict] | None
    reward: float | None
    metadata: dict
```

不要只保存 messages 后再 retokenize。

---

### Step 3：下一步做 OpenAI-compatible proxy，只支持一种协议即可

第二阶段做一个最小代理：

```text
POST /v1/chat/completions
```

支持：

```text
request capture
tool schema capture
prompt token ids capture
sampled token ids capture
logprobs capture
response transformation
session_id 绑定
```

不必一开始支持 Anthropic Messages、OpenAI Responses、Google generateContent。Polar 支持多 provider 是为了通用性；你的项目 MVP 先支持 OpenAI-compatible 就够了。

这样你后续可以让外部 harness 指向：

```text
OPENAI_BASE_URL=http://localhost:xxxx/v1
MODEL=your_model
```

然后运行：

```text
mini-swe-agent
your RepoHarness shell mode
Codex-like local harness
Qwen Code-like harness
```

这就是你项目从“自己写 harness”升级到“可训练任意 harness”的关键。

---

### Step 4：先实现 per_request builder，再实现 prefix_merging

第一版 trajectory builder：

```text
per_request:
  每个 captured completion 变成一个 trace。
  不把 final reward 简单广播到每个 trace 直接训练。
  先用于离线分析、SFT、debug。
```

第二版：

```text
prefix_merging:
  识别 append-only conversation chains。
  sampled assistant tokens loss_mask=1。
  harness 插入 tool result / canonical context loss_mask=0。
```

尤其注意 Polar 的警告：**不要简单把 session-level reward 广播给每个 request-level trace**。它们观察到这种做法会导致 reward hacking。你的 SWE rollout 很长，尤其容易踩这个坑。([arXiv][1])

---

### Step 5：为每个 rollout session 加 metadata

Polar 的 task payload 里有：

```text
task_id
instruction
num_samples
timeout_seconds
runtime backend / image / workdir / prepare
agent harness / model_name
builder strategy
evaluator strategy
callback_url
metadata: group_id, policy_version, rollout_step
```

你应该给 RepoHarness 的 rollout artifact 加类似字段：

```json
{
  "env_id": "...",
  "task_id": "...",
  "taskset_id": "...",
  "sandbox_spec_id": "...",
  "harness_id": "repoharness_swe_bash_editor_v1",
  "rubric_id": "...",
  "builder": "per_request|prefix_merging",
  "policy_version": 114,
  "rollout_step": 2030,
  "group_id": "...",
  "tool_schema_version": "...",
  "runtime_image_digest": "...",
  "evaluator_digest": "...",
  "verdict": "...",
  "reward_components": {...}
}
```

这会让你后续接 async verl 时能处理 staleness、replay、过滤和分组。

---

### Step 6：把外部 harness 当作 HarnessSpec，而不是新环境

你现在的 ComposableEnv 可以这样扩展：

```yaml
HarnessSpec:
  id: claude_code_like_v1
  adapter: shell_command
  command: "claude-code ..."
  model_proxy: openai_proxy
  tool_surface: external_black_box
  expected_provider_api: anthropic_messages

HarnessSpec:
  id: repoharness_native_v1
  adapter: python_native
  command: null
  model_proxy: native_capture
  tool_surface: bash_editor

HarnessSpec:
  id: mini_swe_agent_v1
  adapter: shell_command
  command: "mini-swe-agent ..."
  model_proxy: openai_proxy
```

这样，TaskSet、SandboxSpec、Rubric 可以复用；HarnessSpec 可以切换。

这正是 Polar 实验告诉你的：同一基础模型在不同 harness 上表现差异很大，harness-native RL 能补齐 action protocol / context policy / patch submission 的适配差距。([arXiv][1])

---

## 6. 这对你当前 Stage 16G.3 的影响

你当前 Stage 16G.3 计划里仍然有强烈 “结构化 public command profile / run_project_test 模型可见工具” 的味道：例如它规划了 `run_public_command(command_profile_id, args...)`，并要求 pytest 命令通过 `run_public_command` 时被拒绝、提示使用 `run_project_test`；同时 inspector 还要验证 `raw_freeform_argv_supported=false`、`argv_must_resolve_to_enabled_profile=true`。

结合微软 MAI 和这篇 Polar，我建议你继续修正为：

```text
模型可见：
  bash(command) 或 run_public_command(command)
  editor / apply_patch

内部：
  ProjectTestRouter
  PublicTestTrustClassifier
  CommandMonitor
  SafetyGate
  TrainingEligibilityFacts
```

Polar 的核心不是“给模型更安全的 DSL”，而是“保留真实 harness 执行路径，并在模型 API 边界捕获训练信号”。所以你的 Stage 16G.3 不应继续强化 RepoHarness 私有 DSL，而应让 RepoHarness 的 surface 更接近真实 harness，并把审计放在 runtime / monitor / verifier / training facts 层。

---

## 7. 暂时不需要借鉴的部分

你现在**暂时不需要**完整复刻以下部分：

```text
1. 完整分布式 rollout server / gateway 集群
2. 多 provider proxy：Anthropic + OpenAI Chat + Responses + Google 全兼容
3. dashboard UI
4. Codex / Claude Code / Gemini CLI / Qwen Code / OpenCode / Pi 全部适配
5. Apptainer + Docker 双 runtime
6. 复杂 runtime pooling / evaluator prewarm
```

理由很简单：你当前最大的风险还是 **SWE 环境与工具面是否真实、sandbox 是否稳、trajectory schema 是否可训练**。在这些没稳定前，做完整 Polar 会把工程复杂度拉爆。

你应该先做：

```text
Polar-lite:
  native capture -> per_request trace -> verl adapter
  OpenAI proxy -> one external harness -> per_request trace
  prefix_merging -> later
```

---

## 8. 一个推荐路线图

### Phase A：RepoHarness 仍先作为第一个 SWE ComposableEnv

完成：

```text
Task / TaskSet / SandboxSpec / HarnessSpec / Rubric / ComposableEnv
SWEHarness v1: bash(command) + editor/apply_patch
Hidden test rubric
Anti-tamper monitor
TrainingView v2
```

### Phase B：Polar-lite native capture

在 RepoHarness 自己的 agent loop 里记录：

```text
prompt_ids
response_ids
response_logprobs
loss_mask
tool schema
reward
metadata
```

先不要代理外部 harness。

### Phase C：verl adapter 接 TrainTrace，而不是接 RepoHarness 内部对象

让 verl 只消费：

```text
RolloutGroupArtifact
TrainTrace[]
reward_components
metadata
```

不要让 verl import `RepoHarness.run_episode`。

### Phase D：OpenAI-compatible model proxy

实现最小：

```text
/v1/chat/completions
session_id
token ids / logprobs capture
request/response journal
```

接一个最简单外部 harness：

```text
mini-swe-agent-like bash harness
```

### Phase E：Harness-native RL 对比

做小规模对比：

```text
same model + same tasks

1. RepoHarness native
2. mini-swe-agent-like
3. Codex-like command surface
```

看：

```text
base performance
RL gain
invalid tool-call rate
verification rate
permission violation
trajectory length
training sample fidelity
```

### Phase F：prefix_merging + session normalization

等你有长轨迹后，再做：

```text
prefix_merging
session-level reward normalization
no blind reward broadcasting
staleness metadata
```

---

## 9. 最终建议

**你的项目需要借鉴 Polar，但应借鉴它的“训练边界”思想，而不是立刻复制它的完整系统。**

最应该吸收的是：

```text
1. Harness-as-environment：
   不要为了训练重写真实 harness。

2. Model API proxy：
   在模型 API 边界捕获 token-level 训练信号。

3. Token-faithful trace：
   训练 tokens 必须来自实际 sampled response ids，不靠事后 retokenize。

4. Rollout-as-a-service：
   训练器和环境执行解耦，通过 task submit / callback / artifact 连接。

5. Prefix merging：
   长轨迹需要合并和精确 loss mask，不能粗暴按 request 切片广播 reward。

6. Multi-harness adaptation：
   不同 harness action protocol 差异很大，harness-native RL 可以显著提升陌生 harness 表现。
```

你当前项目最好的定位可以更新为：

```text
RepoHarness is a composable interactive SWE environment family.
A Polar-lite rollout layer turns RepoHarness and external coding harnesses
into token-faithful rollout groups for verl.
```

这会比单纯 “RepoHarness + verl” 强很多，也比只做 “Composable Environments” 更完整：前者定义环境，后者打通训练。

[1]: https://arxiv.org/pdf/2605.24220 "Polar: Agentic RL on Any Harness at Scale"



#ANS2:
我读完后的结论是：**这篇 Polar 不是在推翻我们之前给你设计的 Prime-style composable environment pipeline，而是在补上另一个非常关键的层：如何把任意现有 agent harness 以低侵入方式接入 RL。**

你可以把它理解成：

```text
Prime / ComposableEnv 关注：
  如何把环境内部拆成 TaskSet / Harness / Sandbox / Rubric 等可组合模块。

Polar 关注：
  当一个 harness 已经存在，甚至是闭源 CLI / 二进制 / 产品级工具时，
  如何不改 harness 内部，也能把它变成 RL rollout source。

你的 RepoHarness 最佳方向：
  内部采用 Prime-style composable design；
  外部增加 Polar-style model API proxy + rollout service + trajectory reconstruction。
```

换句话说，**Prime 帮你设计“环境工厂”；Polar 帮你设计“任何 harness 都能被训练器消费的 rollout 基础设施”。**

---

# 1. 这篇 Polar 的核心内容

这篇论文叫 **Polar: Agentic RL on Any Harness at Scale**，arXiv v1 提交于 2026 年 5 月 22 日。论文的出发点是：现在很多 agentic RL 依赖复杂的 custom harness，这些 harness 负责长上下文、多轮工具调用、多 agent orchestration、context compaction、工具格式、执行策略等；但把这些 harness 改写成某个 RL 框架要求的 environment API 很麻烦，而且容易丢失 native harness 里的训练信号。Polar 的目标就是：**不用打开或重写 harness，也能做 RL。** ([arXiv][1])

它的中心问题非常直接：

```text
Can we train agents with RL without opening the box?
```

它的答案是：可以。因为无论 Claude Code、Codex、Qwen Code、OpenCode 还是别的 coding harness，最终都要调用模型 API。Polar 不把 harness 改造成 Gym 环境，而是在 **LLM API 边界** 插入一个 provider-compatible proxy，监听 harness 发出的模型请求，捕获 prompt、response、token ids、logprobs、finish reason 等，然后把这些模型调用重构成 trainer 可消费的 RL trajectory。论文明确说，Polar 使用 agent 的 LLM API traffic 作为 rollout interface，而不是把 agent harness 本身改造成 RL interface。([arXiv][2])

---

# 2. Polar 的架构：Rollout Server + Gateway Node + Model Proxy

Polar 有两个核心组件：

```text
Rollout Server:
  负责接收 TaskRequest、扩展成多个 session、调度 gateway、维护状态、接收 callback。

Gateway Node:
  负责启动 runtime、准备 harness、运行 harness、代理模型调用、构造 trajectory、运行 evaluator、清理资源。
```

论文里说，一个 session 是调度单元，包含 session id、task id、timeout budget、runtime spec、agent spec、trajectory builder、evaluator、callback URL 等。Gateway 负责 session 生命周期：启动 runtime、准备 harness、运行 harness 命令、从 captured completions 构造 trajectories、执行 evaluation、回传结果。([arXiv][2])

它的 proxy 流程是四步：

```text
1. Detect provider API
   识别 Anthropic Messages、OpenAI Chat、OpenAI Responses、Google generateContent 等请求格式。

2. Normalize request
   把不同 provider 请求转换成本地 inference server 能消费的 OpenAI Chat Completions 形状，并补上 logprobs=true 等训练需要的字段。

3. Capture token-level data
   记录 request messages、response messages、prompt token ids、sampled response token ids、finish reason、logprobs。

4. Return provider shape
   再把 response 转回原 harness 期待的 provider schema。
```

论文强调，这个 proxy boundary 位于 agent framework 之下，不需要理解 harness 如何 planning、如何管理工具、如何停止；它只需要保持 API 兼容，并记录足够信息来重构训练样本。([arXiv][2])

这点非常关键：**Polar 的核心不是发明新 agent loop，而是把 existing/native harness 的模型调用变成可训练数据。**

---

# 3. Polar 的真正难点：token-faithful trajectory reconstruction

很多 agent harness 的最终日志只是文本 transcript。如果你把 transcript 重新 tokenize 成训练样本，会遇到 **retokenization drift**：重新编码出来的 token ids 可能不是行为策略实际采样时的 token ids。RL 需要把 reward 绑定到当时真实 sampled tokens 上，否则 policy gradient 信号会错位。论文专门强调，agent RL 的训练信号只有绑定到 behavior policy 实际采样的 tokens 上才是正确的。([arXiv][2])

Polar 提供两种 trajectory builder：

```text
per_request:
  每次 LLM completion 都变成一个 trace。
  保守、无损，但会把一个多轮 agent session 切成很多短样本。

prefix_merging:
  如果 harness 的 conversation history 是 append-only，就把多个 completion 合成更长 trace。
  但遇到 context compaction、subagent boundary 等情况会自然断链。
```

一个 trace 包含：

```text
prompt token ids
response token ids
loss mask
prompt messages
response messages
tool definitions
log probabilities
reward
metadata
```

论文里的 correctness invariant 很重要：

```text
Every trainable token matches the behavior policy during rollout,
and any non-generated tokens are masked out.
```

也就是说，模型真正采样出来的 assistant tokens 才进入 loss；工具结果、系统拼接、canonical interstitial tokens 之类非模型生成内容要用 loss mask 盖掉。([arXiv][2])

这部分对你的项目很重要，因为你接 verl 时不能只保存：

```text
messages + reward
```

更理想的是保存：

```text
prompt_ids
response_ids
loss_mask
response_logprobs
reward
metadata
```

---

# 4. Polar 的异步 rollout staging

Polar 不是把所有事情塞进一个同步 rollout 函数里。它把 gateway 内部拆成几个 worker pool：

```text
INIT:
  启动 runtime，执行 prepare actions。

READY:
  保存已经初始化好的 runtime，等待 run slot。

RUNNING:
  执行 harness。

POSTRUN:
  构造 trajectory，运行 evaluator，执行 post-run hooks，发送 callback，清理资源。
```

论文指出，长程 harness rollout 混合了很多不同成本：runtime startup、dependency preparation、harness execution、evaluator setup、test execution、patch application、teardown。Polar 用 stage-isolated execution 避免这些成本互相阻塞，并且 evaluator 如果需要 clean runtime，可以在 agent run 时提前 prewarm。即使 harness 超时，只要模型调用已经被捕获，gateway 仍然进入 post-run，恢复 partial traces 并记录 timeout status。([arXiv][2])

这和你之前看的 synthetic environment 文章高度一致：那篇文章强调 long-horizon async RL 里，generation、execution、verification、training consumption 是不同 clock 的服务，trajectory store 不只是日志，而是训练决策的一部分。

---

# 5. 实验结果：它确实能让现有 coding harness 做 RL

Polar 用 Qwen3.5-4B 作为 base checkpoint，在 SWE-Gym 训练，然后在 SWE-Bench Verified 上评估。它保持 Codex、Claude Code、Qwen Code、Pi 这些 harness 不变，只通过 Polar 捕获模型调用和构造训练 trace。结果是：

```text
Codex harness:
  3.8% -> 26.4%，+22.6

Claude Code harness:
  29.8% -> 34.6%，+4.8

Qwen Code harness:
  34.6% -> 35.2%，+0.6

Pi harness:
  34.2% -> 40.4%，+6.2
```

论文解释说，Codex 这行提升最大，可能是因为 Qwen base model 原本不熟悉 Codex 的 action protocol、context policy 和 patch submission style；Polar 把 reward 绑定到模型在 Codex execution path 中实际采样的 tokens 上，所以 GRPO 直接优化了模型在这个 native harness 下需要用到的行为。([arXiv][2])

它还做了 trajectory builder ablation：在同一 workload 和 topology 下，prefix merging 把 trainer stream 从 1,185 个 request-level updates 降到 218 个 merged-trace updates，wall-clock time 从 189.5 分钟降到 35.2 分钟，大约 5.39×；rollout GPU utilization 从 20.4% 提高到 87.7%。论文也提到，简单把 session-level outcome reward 广播到每个 per-request trace 会产生明显 reward hacking，因为 request-level trace 收到 session-level credit 后 credit assignment 很 noisy。([arXiv][2])

此外，Polar 还被用作离线 SFT 数据生成服务：用固定 checkpoint 和 harness 分布式跑任务，然后用 SWE-Bench evaluator 过滤最终 patch。论文报告，在 1,638 次 SWE-Gym attempts 中接受 504 条轨迹，接受率 30.8%。([arXiv][2])

官方 GitHub README 也把 Polar 定位为 “RL rollout framework for real-world agent harnesses”，强调三点：Harness as Environment、Smart Rollout Pipeline、Rollout as a Service；README 还说 Polar trainer-agnostic，通过 HTTP server boundaries 连接训练框架，并列出 Slime integration 和未来更多 trainer bridges，包括 VERL。([GitHub][3])

---

# 6. 它和 Prime / ComposableEnv 的关系

我建议你这样理解：

| 方向    | Prime / ComposableEnv                       | Polar                                         |
| ----- | ------------------------------------------- | --------------------------------------------- |
| 主要问题  | 如何把 environment 拆成可组合模块                     | 如何不改 existing harness 也能训练                    |
| 视角    | environment factory / white-box composition | black-box harness instrumentation             |
| 核心边界  | TaskSet / Harness / SandboxSpec / Rubric    | model API proxy / rollout server / gateway    |
| 适合场景  | 你能控制环境和任务生成                                 | 你要训练 Claude Code、Codex、OpenCode、闭源 CLI        |
| 训练对象  | 可组合环境里产生的 rollout                           | native harness 真实执行路径里的模型调用                   |
| 对你的价值 | 帮你设计 RepoHarness 内部结构                       | 帮你设计 RepoHarness 与 verl / 外部 harness 的低侵入训练接口 |

这两个方向不冲突。它们是在不同层解决问题。

之前我们说：

```text
RepoHarness 不应该是一个 monolithic environment。
它应该是 Harness 层；
具体 environment 由 TaskSet + SandboxSpec + UserSimSpec + PermissionSpec + Rubric 组合出来。
```

Polar 则说：

```text
即使某个 harness 已经是一个黑盒 CLI，
也可以通过模型 API proxy 把它变成 RL rollout source。
```

所以更完整的项目叙事应该是：

```text
RepoHarness 内部：
  Prime-style composable environment pipeline。

RepoHarness 外部：
  Polar-style low-intrusion rollout service and model-call capture。

训练接口：
  artifact -> verl async RL。
```

---

# 7. 你的项目要不要借鉴 Polar？

我的建议是：**需要借鉴，但不要全盘照抄。**

你不应该把项目改成“只做一个 Polar clone”。原因是：

第一，你现在自己控制 RepoHarness 源码，不像 Polar 面对的是任意 closed-source / opaque harness。既然你能控制内部，就应该保留 Prime-style 白盒设计，这样才能做 user simulator、permission system、process reward、event log、forbidden diff checker、trajectory replay 等细粒度能力。

第二，Polar 主要解决的是“native harness 如何接入 RL”；它本身并没有重点解决你最关心的 user simulator、permission approval、真实长期任务、用户隐藏约束、权限边界 reward。Polar 的 evaluator registry 可以扩展 custom reward，但论文主体仍然主要是 SWE-Gym/SWE-Bench outcome reward 和 coding harness 训练。([arXiv][2])

第三，对简历项目来说，完整复刻 Polar 的 provider-compatible proxy、streaming transform、distributed gateway、runtime pooling、Slime bridge、Apptainer/HPC 支持，工程量太大，容易分散你项目最有辨识度的部分。

但你应该借鉴 Polar 的 **五个关键思想**。

---

# 8. 你应该借鉴的五个设计

## 8.1 增加一个 Model API Proxy / Capture Layer

你现在的 RepoHarness 可能是直接调用模型 client 或 verl rollout worker。为了让项目更像真实 agentic RL infra，我建议加一个可选的 `ModelProxy`：

```text
RepoHarness / ExternalHarness
        |
        | OpenAI-compatible / Anthropic-compatible API call
        v
ModelProxy
        |
        | records token ids, logprobs, prompts, responses
        v
vLLM / SGLang / verl inference backend
```

最小版不需要同时兼容 Anthropic、OpenAI Responses、Google。你可以先做 **OpenAI Chat Completions-compatible proxy**：

```python
POST /v1/chat/completions
```

记录：

```python
CompletionRecord:
  session_id
  request_id
  provider_format
  prompt_messages
  response_messages
  prompt_token_ids
  response_token_ids
  response_logprobs
  finish_reason
  model_name
  policy_version
  timestamp
```

这样你的项目就能说：

> RepoHarness can train native agent harnesses through a model API boundary, without rewriting the harness as a verl environment.

这和 Polar 的核心思想对齐。

---

## 8.2 把 rollout 改成 service，而不是 trainer 内部函数

现在如果你的 verl adapter 直接调用：

```python
reward = repoharness.run(task, model)
```

这还像传统单体 runner。

更好的结构是：

```text
verl trainer
   |
   | submit rollout group
   v
RepoHarness Rollout Server
   |
   | dispatch sessions
   v
Gateway Worker
   |
   | runtime init -> harness run -> trajectory build -> evaluation
   v
Artifact Store
   |
   | callback / polling
   v
VerlAdapter
```

你可以先做单机异步版，不需要分布式。关键是抽象边界：

```python
class RolloutServer:
    async def submit(self, request: TaskRequest) -> TaskHandle: ...
    async def status(self, task_id: str) -> TaskStatus: ...
    async def result(self, task_id: str) -> list[TrajectoryArtifact]: ...
```

对应 Polar 的 API 风格是：submit 非阻塞任务、poll task status、gateway callback session result、status inspect。论文附录给出的 representative payload 也包含 instruction、num_samples、timeout、runtime、agent、builder、evaluator、callback_url、metadata，其中 metadata 里包括 group_id、policy_version、rollout_step。([arXiv][2])

---

## 8.3 设计 TraceBuilder，而不是简单保存 transcript

你需要一个独立的 `TraceBuilder` 模块：

```text
CompletionRecords + EventLog + Reward
        |
        v
TraceBuilder
        |
        v
Trainer-facing traces
```

最小实现两个 builder：

```text
per_request:
  每个模型调用一个 trace。
  适合调试和 SFT。

episode_merge / prefix_merge:
  把 append-only 主对话合并成更长 trace。
  适合 RL，减少 request-level reward broadcasting 的 credit assignment 问题。
```

你的 trace schema 可以直接参考 Polar：

```python
Trace:
  prompt_ids: list[int]
  response_ids: list[int]
  loss_mask: list[int]
  response_logprobs: list[float]
  prompt_messages: list[dict]
  response_messages: list[dict]
  tools: list[dict] | None
  reward: float
  metadata: dict
```

对你的项目还要额外加：

```python
metadata:
  task_id
  taskset_id
  env_version
  harness_version
  permission_spec_id
  user_sim_spec_id
  rubric_version
  policy_version
  session_id
  trace_builder
  num_tool_calls
  num_user_turns
  num_permission_requests
  num_permission_denials
  num_permission_violations
```

这样你不是只把 trajectory 存成日志，而是变成真正的 training artifact。

---

## 8.4 把 evaluator / rubric 做成 registry

Polar 的 evaluator 是 registry-backed custom strategies，运行在 trajectory construction 之后；内置 evaluator 包括 session-completion reward、test-on-output evaluator、SWE-Bench/SWE-Gym harness evaluator，也支持 rule-based verification、agent-as-judge、task-specific reward shaping。([arXiv][2])

你的项目也应该这样做：

```python
EvaluatorRegistry:
  swe_hidden_tests
  forbidden_diff
  permission_compliance
  user_burden
  denial_recovery
  test_tampering
  api_contract
  llm_judge_summary_quality
```

一个 interactive SWE task 的 reward 可以是：

```python
reward = (
    4.0 * hidden_tests
  + 1.0 * public_tests
  + 1.0 * api_contract
  + 1.5 * permission_compliance
  + 0.5 * user_burden_score
  - 3.0 * forbidden_diff
  - 2.0 * test_tamper
  - 1.0 * repeated_denied_action
)
```

这部分是你比 Polar 更强的地方：Polar 主要展示 outcome reward 和 SWE-Bench evaluator；你的项目可以展示 **permission-aware / user-aware process evaluation**。

---

## 8.5 支持 external harness adapter

这是 Polar 对你项目定位最直接的启发。

你现在有自己的 RepoHarness。你可以加一个 `ExternalShellHarnessAdapter`：

```python
class ExternalShellHarnessAdapter:
    def prepare(self, session):
        write_provider_config(
            base_url=session.model_proxy_url,
            api_key="dummy",
            model=session.model_name,
        )

    def command(self, session):
        return [
            "codex",
            "--model", session.model_name,
            "--prompt-file", "/task/instruction.txt",
        ]
```

然后你可以接：

```text
repo_harness        # 你自己的 white-box harness
mini_swe_agent      # baseline
opencode            # external CLI
codex_cli_style     # 如果合法可用
claude_code_style   # 如果合法可用
qwen_code           # external coding harness
```

这样你项目的格局就变了：

```text
不是：
  我写了一个 harness。

而是：
  我实现了一个训练系统，可以运行自己的 composable harness，
  也可以以低侵入方式训练/评估外部 native harness。
```

这正是 Polar 的 “any harness” 价值。

---

# 9. 你的项目应该如何重构成 Prime + Polar 混合架构

我建议你的最终架构长这样：

```text
RepoHarness Project
│
├── Environment Composition Layer        # Prime-style
│   ├── TaskSet
│   ├── SandboxSpec
│   ├── UserSimSpec
│   ├── PermissionSpec
│   └── Rubric
│
├── Harness Layer
│   ├── RepoHarness                      # 你的白盒 harness
│   ├── MiniSWEHarness                   # baseline
│   └── ExternalShellHarness             # Polar-style native harness adapter
│
├── Runtime / Rollout Service Layer       # Polar-style
│   ├── RolloutServer
│   ├── GatewayWorker
│   ├── RuntimePool
│   ├── ModelProxy
│   └── TraceBuilder
│
├── Verification Layer
│   ├── HiddenTestEvaluator
│   ├── PermissionEvaluator
│   ├── UserBurdenEvaluator
│   └── DiffEvaluator
│
├── Artifact Layer
│   ├── CompletionRecordStore
│   ├── EventLogStore
│   ├── TrajectoryArtifactStore
│   └── SnapshotStore
│
└── Training Interface
    ├── VerlAdapter
    ├── OfflineSFTExporter
    └── EvalRunner
```

这个结构可以很好地解释：

```text
TaskSet       决定任务是什么
Harness       决定 agent 如何行动
SandboxSpec   决定在哪里执行
UserSimSpec   决定用户如何交互
PermissionSpec决定什么动作允许/审批/禁止
Rubric        决定如何评分
ModelProxy    捕获 native harness 的模型调用
TraceBuilder  把模型调用变成 token-faithful traces
RolloutServer 把长任务异步调度成服务
VerlAdapter   把 artifact 转成训练样本
```

---

# 10. 一个具体例子：你的 interactive refactor task 如何用 Polar-style pipeline 跑

假设你有任务：

```text
用户：帮我重构 payments 模块，旧的 PaymentClient 太乱了。
隐藏约束：
  - 不要修改 refunds
  - public API 不能变
  - 不要删除测试
  - DB migration 需要 DBA 审批
```

你可以生成一个 `TaskRequest`：

```json
{
  "task_id": "interactive-refactor-payments-001",
  "instruction": "帮我重构 payments 模块，旧的 PaymentClient 太乱了。",
  "num_samples": 8,
  "timeout_seconds": 3600,

  "runtime": {
    "backend": "docker",
    "image": "repoharness/python-node:3.11",
    "network": "disabled",
    "workdir": "/workspace",
    "prepare": [
      {"type": "copy_repo", "source": "fixtures/payments_service"},
      {"type": "exec", "command": "pip install -e ."}
    ]
  },

  "agent": {
    "harness": "repoharness",
    "model_name": "qwen-3.5-4b-current",
    "model_base_url": "http://gateway/session/proxy/v1"
  },

  "env": {
    "taskset": "InteractiveRefactorTaskSet",
    "user_sim_spec": "eng_manager_medium_v1",
    "permission_spec": "swe_safe_v1"
  },

  "builder": {
    "strategy": "event_aware_prefix_merge"
  },

  "evaluator": {
    "strategy": "interactive_swe_rubric",
    "refresh_runtime": true,
    "config": {
      "hidden_tests": "pytest hidden_tests/payments",
      "api_contract": "python checks/api_contract.py",
      "forbidden_paths": ["src/refunds/**", "infra/prod/**"]
    }
  },

  "metadata": {
    "group_id": "grpo-group-123",
    "policy_version": 114,
    "rollout_step": 2007,
    "env_template_version": "interactive_refactor_v1"
  }
}
```

执行过程：

```text
1. RolloutServer 接收 TaskRequest。
2. 它扩展成 8 个 session，用于 GRPO group。
3. GatewayWorker 预热 8 个 sandbox。
4. 每个 sandbox 运行 RepoHarness。
5. RepoHarness 的模型请求全部指向 ModelProxy。
6. ModelProxy 转发到 vLLM/SGLang/verl inference backend，并记录 token ids、logprobs。
7. RepoHarness 与 bash/file tools、permission gate、user simulator 交互。
8. POSTRUN 阶段运行 hidden tests、diff checker、permission checker、user burden evaluator。
9. TraceBuilder 构造 token-faithful traces。
10. ArtifactStore 保存 trajectory、score、repo diff、permission events、user events、policy version。
11. VerlAdapter 把 artifact 转为 verl 可消费 batch。
```

这就把你的项目从：

```text
RepoHarness 跑一个任务，返回 reward。
```

升级成：

```text
一个 async rollout service 运行 composable environments，
通过 model proxy 捕获 native harness 轨迹，
通过 evaluator registry 评分，
通过 artifact store 和 verl adapter 消费。
```

---

# 11. 你暂时不需要完整实现哪些 Polar 功能

为了简历项目和个人长期项目，我建议你不要一开始做这些：

```text
1. 不要一开始兼容 Anthropic / OpenAI Chat / OpenAI Responses / Google 四套协议。
   先做 OpenAI-compatible proxy。

2. 不要一开始支持 streaming provider transform。
   可以先只支持 non-streaming；streaming 后面补。

3. 不要一开始做分布式 gateway cluster。
   先做单机 async worker pool：INIT / READY / RUNNING / POSTRUN。

4. 不要一开始做 Docker + Apptainer + HPC。
   先做 Docker runtime。

5. 不要一开始实现复杂 prefix merging。
   先做 per_request + simple episode_merge；
   然后再加 event-aware prefix merge。

6. 不要把自己的 RepoHarness 完全当黑盒。
   因为你拥有源码，白盒 event log 对 permission/user-sim reward 更有价值。
```

你的目标不是复刻 Polar，而是吸收它最能增强你项目叙事的部分。

---

# 12. 我建议你采用的最小版本：Polar-lite for RepoHarness

你可以把下一阶段目标定义为：

```text
RepoHarness-PolarLite:
  A low-intrusion rollout service for composable interactive SWE environments.
```

最小模块：

```text
1. OpenAI-compatible ModelProxy
   记录 prompt_ids / response_ids / logprobs / messages / policy_version。

2. RolloutServer
   submit task group，返回 task_id，异步执行 num_samples。

3. GatewayWorker
   INIT / RUNNING / POSTRUN 三阶段即可，不一定先做 READY buffer。

4. TraceBuilder
   per_request + episode_merge。

5. EvaluatorRegistry
   hidden tests + forbidden diff + permission reward + user burden。

6. VerlAdapter
   把 Trace + reward_components + metadata 转成 verl batch。

7. ExternalShellHarnessAdapter
   能跑 mini-swe-agent 或 opencode 风格 CLI baseline。
```

这样你就能在 README 里写：

```text
RepoHarness supports two integration modes:
1. White-box composable environments:
   TaskSet + Harness + SandboxSpec + UserSimSpec + PermissionSpec + Rubric.

2. Black-box native harness RL:
   existing CLI harnesses can be launched unchanged behind a model API proxy;
   token-faithful traces are reconstructed and consumed by verl.
```

这句话非常强。

---

# 13. 它会如何改变你的项目定位？

之前我们给你的定位是：

```text
RepoHarness:
  composable environment pipeline for interactive SWE agent RL.
```

看完 Polar 以后，我建议升级为：

```text
RepoHarness:
  a composable and low-intrusion rollout infrastructure for interactive SWE agent RL.

It combines:
  Prime-style environment composition
  +
  Polar-style native-harness trajectory capture
  +
  permission/user simulation for realistic long-horizon SWE tasks
  +
  verl-compatible async training consumption.
```

简历上可以写成：

```text
Built RepoHarness, a composable rollout infrastructure for interactive SWE agent RL. 
It decouples TaskSet, Harness, SandboxSpec, UserSimSpec, PermissionSpec, and Rubric, 
and adds a Polar-style model API proxy to capture token-faithful trajectories from native agent harnesses. 
Integrated with verl for async GRPO rollouts with hidden-test, permission-compliance, and user-burden rewards.
```

---

# 14. 最终判断

**需要借鉴 Polar，但你的核心仍然应该是 Prime-style composable environment + user/permission-aware SWE tasks。**

Polar 给你的最大启发不是“把 RepoHarness 变成黑盒”，而是：

```text
不要让训练框架依赖 harness 内部实现；
把模型调用边界、trajectory reconstruction、rollout scheduling、evaluation、training consumption 明确拆开。
```

所以最终最好的设计是：

```text
内部：
  TaskSet / SandboxSpec / Harness / UserSimSpec / PermissionSpec / Rubric 解耦。

外部：
  RolloutServer / GatewayWorker / ModelProxy / TraceBuilder / Evaluator / VerlAdapter 解耦。

训练数据：
  不再是 prompt-response-reward，
  而是 token-faithful trajectory artifact + environment metadata + reward components。
```

这会让你的项目从“一个 Claude Code-like SWE harness”进一步升级成：

**一个既能构造环境、又能运行 native harness、还能服务异步 RL 的 agentic RL infrastructure 项目。**

[1]: https://arxiv.org/abs/2605.24220 "[2605.24220] Polar: Agentic RL on Any Harness at Scale"
[2]: https://arxiv.org/pdf/2605.24220 "Polar: Agentic RL on Any Harness at Scale"
[3]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server "GitHub - NVIDIA-NeMo/ProRL-Agent-Server: Agentic RL on Any Harness at Scale · GitHub"
