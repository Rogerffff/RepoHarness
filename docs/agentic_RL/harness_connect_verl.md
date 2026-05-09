你的直觉是对的，但需要把“接入 verl 分布式 rollout worker”和“给 RepoHarness 加 Gateway”这两件事区分开：

**你当然可以继续用 verl 的 Agent Loop 训练。更推荐的第一版方案不是把 RepoHarness 完全搬进 verl，也不是让 RepoHarness 直接去管理 AsyncLLMServer，而是写一个很薄的 `RepoHarnessVerlAgentLoop`，让它调用你已有的 RepoHarness runtime；RepoHarness 内部的 LLM backend 换成一个 `VerlLLMGateway`，这个 gateway 再调用 verl 已经提供的 `LLMServerClient` / 旧版本里的 `AsyncLLMServerManager`。**

也就是说，图里的黄色 `AgentLoop` 仍然可以存在，但它不要再承载全部业务逻辑。它只是一个 adapter：

```text
PPOTrainer
  → AgentLoopManager.generate_sequences
    → AgentLoopWorker
      → RepoHarnessVerlAgentLoop.run(...)
        → RepoHarnessRuntime.run_episode(...)
          → Docker workspace / tools / permission / verifier / trajectory store
          → VerlLLMGateway.generate_turn(...)
            → verl LLMServerClient / AsyncLLMServerManager
              → AsyncLLMServer
                → vLLM / SGLang model runner
```

这就是我说的“Gateway”。它不是一定要新起一个网络服务，也不是要你重写 verl 的 `AsyncLLMServerManager`。在第一版里，它可以只是 RepoHarness 里的一个 Python adapter class。

---

## 1. 你之前 Deep Search Agent 的做法没有错，但现在要换“嵌入方式”

你之前训练 deep search agent 时，大概率是这样的：

```text
CustomAgentLoop / CustomAgentLoopBase
  → 维护 search context
  → 调用 self.llm_server_client.generate(...)
  → 调用 search tool
  → 拼接 observation
  → 返回 AgentLoopOutput
```

这很适合 search agent，因为 search tool、context、reward 都比较轻，直接写在 verl 的 `AgentLoopBase.run()` 里很自然。

但 RepoHarness 不一样。它已经是一个完整系统：

```text
task adapter
Docker workspace backend
tool runtime
permission policy
agent loop
trajectory store
verifier / reward
experiment runner
export audit
acceptance bundle
```

如果你把这些全部塞进 verl 的自定义 AgentLoop 代码里，会有几个问题：

第一，RepoHarness 的独立性会下降。你以后想用 OpenAI / DeepSeek provider 做 offline rollout，或者用 SGLang standalone 做数据生成，就会被 verl 的内部结构绑住。

第二，Docker、artifact、verifier、resume、audit 这些逻辑会和 Ray worker 生命周期耦合，调试会变难。

第三，RepoHarness 的核心价值是一个 agentic post-training harness / trajectory data plane，而不是 verl 的某个工具函数。你应该保留这个独立抽象。

所以更好的方式是：

```text
verl 自定义 AgentLoop = thin wrapper
RepoHarnessRuntime = 真正的 agent / env / verifier 系统
VerlLLMGateway = RepoHarness 调用 verl 推理能力的 adapter
```

也就是：**不是不能继续用 verl Agent Loop，而是不要再把业务逻辑写进 verl Agent Loop；让 verl Agent Loop 只负责把 verl 的训练/推理能力接入 RepoHarness。**

---

## 2. 图里每个模块该怎么映射到 RepoHarness

你贴的图是 verl Agent Loop 的标准架构。官方文档里也说，Agent Loop 的目标是支持可插拔 user-defined agent loop、提供统一 generate API、在多个 inference server 之间做 request-level load balance；它的 non-goal 是定义工具本身以及工具如何调用。也就是说，verl 本来就希望“工具和环境逻辑由你自己实现”，它只管给 AgentLoop 提供生成接口和训练闭环。([Verl][1])

对应到你的 RepoHarness：

| 图中模块                                           | 在 RepoHarness 接入时的角色                                              |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| `PPOTrainer`                                   | 还是 verl 的训练入口，负责 PPO/GRPO/DAPO 等训练                                |
| `AgentLoopManager`                             | 还是 verl 的 rollout orchestration，负责 wake/sleep server、分 batch、收集结果 |
| `AgentLoopWorker`                              | 还是 verl 的 Ray worker，负责并发运行多个 agent loop coroutine                |
| 黄色 `AgentLoop`                                 | 这里替换成 `RepoHarnessVerlAgentLoop`，但它只是薄封装                          |
| 紫色 `AsyncLLMServerManager` / `LLMServerClient` | 不要重写；作为 RepoHarness 的 LLM backend 被调用                             |
| 粉色 `AsyncLLMServer`                            | verl 管理的 vLLM/SGLang server，不建议 RepoHarness 直接管理                  |
| 底部 `ModelRunner / FSDP`                        | verl 训练/推理权重同步系统，RepoHarness 不应该直接碰                               |
| Docker / tools / verifier                      | 不在图里；由 RepoHarness 自己负责                                           |

所以你的 RepoHarness 接入点不是底部的 `ModelRunner`，也不是粉色的 `AsyncLLMServer`，而是黄色 `AgentLoop` 这一层。

但这个黄色 `AgentLoop` 里不要重写 RepoHarness 的 agent 逻辑，而是：

```python
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    async def run(self, sampling_params, **dataset_fields):
        gateway = VerlLLMGateway(self.llm_server_client, tokenizer=self.tokenizer)
        runtime = RepoHarnessRuntime.from_dataset_fields(
            dataset_fields,
            llm_gateway=gateway,
            mode="online_rl",
        )
        episode = await runtime.run_episode()
        return episode.to_verl_agent_loop_output()
```

这样你仍然用 verl 的分布式 rollout，但 RepoHarness 还是 RepoHarness。

---

## 3. `AsyncLLMServer`、`AsyncLLMServerManager`、`LLMServerClient`、Gateway 到底是什么关系？

这里名称有一点版本差异。你图里写的是 `AsyncLLMServerManager`，verl v0.5 文档里也是这个名字；最新文档和当前代码更偏向 `LLMServerClient` / `LLMServerManager`。语义上它们是一类东西：**它们不是模型本体，而是多个 AsyncLLMServer 上方的 proxy / manager / client。** v0.5 文档说 `AsyncLLMServerManager` 会在第一轮选择 least-request server，后续轮次把同一个 `request_id` 发到同一个 server；最新文档里 `LLMServerClient` 也承担 load balance 和 sticky session。([Verl][2]) ([Verl][1])

分层可以这样看：

```text
RepoHarness LLM Gateway
  └── VerlLLMGateway
        └── LLMServerClient / AsyncLLMServerManager
              └── AsyncLLMServer
                    └── vLLM / SGLang Async Engine
                          └── ModelRunner / FSDP / Megatron workers
```

其中：

**`AsyncLLMServer`** 是具体推理 server 抽象。verl 文档说它支持两类 API：OpenAI chat completion 和 token-in-token-out generate，并且官方支持 vLLM 和 SGLang 的 AsyncLLMServer。([Verl][1])

**`LLMServerClient` / `AsyncLLMServerManager`** 是你在 agent loop 里实际应该调用的对象。它负责在多个 server 之间做 load balance，并且通过 `request_id` 做 sticky session，让同一个多轮 agent episode 后续请求尽量打到同一个 server，从而更容易命中 prefix / KV cache。当前 verl 代码里的 `LLMServerClient` 也明确描述了 least in-flight load balancing 和 sticky session。([GitHub][3])

**`LLMServerManager`** 更偏 server 生命周期管理：启动 rollout replicas、初始化全局 load balancer、返回 client。当前代码里 `LLMServerManager.get_client()` 会返回 `LLMServerClient` 或 fully async 下的 `FullyLLMServerClient`。([GitHub][3])

**你说的 Gateway** 则是 RepoHarness 自己定义的接口层。它不负责 Ray、FSDP、vLLM engine 细节；它负责把 RepoHarness 的一次“模型调用”转换成 verl 能理解的 `prompt_ids + sampling_params + request_id`，再把 verl 返回的 token-level output 转换成 RepoHarness 的 `GenerationRecord`。

最小形式就是：

```python
class VerlLLMGateway:
    def __init__(self, llm_client, tokenizer):
        self.llm_client = llm_client
        self.tokenizer = tokenizer

    async def generate_turn(
        self,
        *,
        episode_id: str,
        turn_id: int,
        prompt_ids: list[int],
        sampling_params: dict,
        context_revision: str,
    ) -> "GenerationRecord":
        output = await self.llm_client.generate(
            request_id=episode_id,          # sticky session key
            prompt_ids=prompt_ids,
            sampling_params=sampling_params,
        )

        # 当前 verl 可能返回 list[int]，也可能返回 TokenOutput，取决于版本/模式
        token_ids = getattr(output, "token_ids", output)
        log_probs = getattr(output, "log_probs", None)
        stop_reason = getattr(output, "stop_reason", None)
        extra_fields = getattr(output, "extra_fields", {})

        text = self.tokenizer.decode(token_ids, skip_special_tokens=False)

        return GenerationRecord(
            episode_id=episode_id,
            turn_id=turn_id,
            prompt_ids=prompt_ids,
            output_token_ids=token_ids,
            output_text=text,
            logprobs=log_probs,
            stop_reason=stop_reason,
            policy_version=extra_fields.get("global_steps"),
            min_policy_version=extra_fields.get("min_global_steps"),
            max_policy_version=extra_fields.get("max_global_steps"),
            context_revision=context_revision,
        )
```

所以，**Gateway 不是“再做一个 AsyncLLMServerManager”，而是 RepoHarness 对外部 LLM rollout backend 的统一适配层。**

---

## 4. 你应该直接接 `AsyncLLMServerManager` 吗？

分情况。

### 情况 A：RepoHarness 嵌在 verl AgentLoop 里

这种情况下，**可以用现成的 `LLMServerClient` / `AsyncLLMServerManager`，但不要自己创建它。**

verl 的 `AgentLoopManager` 会负责：

```text
wake_up async LLM servers
sync weights between inference engine and training engine
split batch to AgentLoopWorker
gather AgentLoopOutput
sleep servers and release KV cache / offload weights
```

这些都属于 trainer / rollout lifecycle，不应该由 RepoHarness 接管。verl 文档里的 rollout phase 正是这个顺序：`PPOTrainer` 调 `AgentLoopManager.generate_sequences`，然后 manager wake up server、切 batch 给 AgentLoopWorker；在 agent loop 里调用 `LLMServerClient.generate`；所有 prompt 完成后再 sleep server。([Verl][1])

所以你应该这样用：

```text
AgentLoopBase.__init__ 里拿到 verl 给的 llm_server_client
    ↓
RepoHarnessVerlAgentLoop.run 里构造 VerlLLMGateway
    ↓
RepoHarnessRuntime 调 gateway.generate_turn
    ↓
gateway 调 llm_server_client.generate
```

不要在 RepoHarness 里单独 new 一个 `AsyncLLMServerManager`。

### 情况 B：RepoHarness 完全独立运行在 verl 外面

这种情况下，**不建议直接接 verl 内部的 `AsyncLLMServerManager`。**

原因是 verl 的 manager/client 很多时候依赖 Ray actor handle、trainer 配置、worker group、权重同步、wake/sleep lifecycle。你如果在一个独立 RepoHarness 进程里直接拿它，会把 RepoHarness 绑死到 verl 内部实现，还要自己处理权重同步和 server 生命周期。

这时更合理的是做一个外部服务化方案：

```text
RepoHarness AgentServer
  → RepoHarness LLMGateway HTTP/gRPC/Ray adapter
    → 某个 rollout service
      → vLLM / SGLang / verl-created server
```

但这已经是第二阶段甚至第三阶段的架构了。它更接近 Forge 的 `AgentServer <-> RolloutEngine -> DataPool -> Trainer` 模式。你上传的 Forge/infra 材料里也强调，大厂方案通常把 Agent 独立为 trajectory producer，中间通过 Gateway Server 和 Data Pool 把 Agent 侧与训推引擎隔离。 

### 情况 C：折中方案

我最建议你先做这个：

```text
verl AgentLoopBase 仍然存在
但它只做 RepoHarnessRuntime 的 adapter
RepoHarnessRuntime 仍然是独立库
RepoHarness LLMGateway 在 online RL 时包一层 verl LLMServerClient
```

这样你能吃到 verl 的分布式 rollout、权重同步、PPO/GRPO 训练，同时不破坏 RepoHarness 的独立性。

---

## 5. 为什么不能只“接 Ray rollout worker”？

因为 SWE agent 的 rollout 不是一次模型生成，而是一条长 episode。

普通 RLVR 是：

```text
prompt_ids → generate response_ids → reward
```

SWE agent 是：

```text
task
  → render context
  → model generate action
  → parse tool call
  → permission check
  → run Docker tool
  → observation truncation / compaction
  → render next context
  → model generate next action
  → ...
  → patch capture
  → strict patch replay
  → final verifier
  → reward
  → training export
```

Ray rollout worker / AsyncLLMServer 只负责其中这一段：

```text
prompt_ids → response_token_ids
```

它不知道：

```text
这个 response 是第几轮？
这个 response 是否形成 tool_call？
tool observation 哪些 token 不应该训练？
hidden verifier 是否泄漏？
这条 trajectory 是否 diagnostic-only？
Docker setup failure 是否应该过滤？
context compaction 后的 prompt revision 是哪个？
policy_version 是多少？
```

所以你需要 Gateway，不是因为 verl 缺一个 server manager，而是因为 RepoHarness 需要一个 **训练友好的 LLM 调用边界**。

这个边界至少要保证：

```text
1. 输入是 prompt_ids，而不是只给 messages
2. 输出保留真实 output_token_ids
3. 保留 logprobs / policy_version / stop_reason
4. 使用 episode_id 做 sticky session
5. 每次 generation 都进入 trajectory provenance
6. response_mask 能区分模型 token 和工具 observation token
7. 不从最终 transcript 文本重新 tokenize 训练样本
```

verl 文档也明确警告，多轮 agent 框架常用 OpenAI chat completion + messages，但把最终 messages 重新 apply chat template 得到的 token IDs，不一定等于每一轮真实 `prompt_ids + response_ids` 拼出来的 token IDs；这种不一致对 serving 问题不大，但对 RL training 是 critical，文档里甚至提到观察到 PPO 不收敛。([Verl][1])

这就是为什么我一直强调：**RepoHarness 不能只保存 transcript text；online RL 路径必须保存 token-level GenerationRecord。**

---

## 6. 第一版最推荐架构：Thin Adapter Mode

我建议你第一版按这个架构做：

```text
┌──────────────────────────────────────────────────────────────┐
│ verl PPOTrainer / GRPO Trainer                               │
│   └── AgentLoopManager.generate_sequences                    │
│       └── AgentLoopWorker                                    │
│           └── RepoHarnessVerlAgentLoop.run                   │
│               └── RepoHarnessRuntime.run_episode             │
│                   ├── TaskAdapter                            │
│                   ├── DockerWorkspaceBackend                 │
│                   ├── ToolRuntime                            │
│                   ├── PermissionPolicy                       │
│                   ├── ContextManager                         │
│                   ├── TrajectoryStore                        │
│                   ├── FinalVerifier                          │
│                   └── VerlLLMGateway                         │
│                       └── verl LLMServerClient.generate      │
│                           └── AsyncLLMServer                 │
│                               └── vLLM / SGLang              │
└──────────────────────────────────────────────────────────────┘
```

这时你只需要在 RepoHarness 里抽象一个 backend：

```python
class LLMGateway(Protocol):
    async def generate_turn(
        self,
        request: GenerationRequest,
    ) -> GenerationRecord:
        ...
```

然后实现几个 backend：

```text
OpenAITextGateway       # debug / offline
DeepSeekTextGateway     # debug / offline
LocalVLLMGateway        # offline data generation
VerlLLMGateway          # online RL
SGLangGateway           # later
```

你的 RepoHarness agent loop 永远只依赖 `LLMGateway`，而不是直接依赖 OpenAI、DeepSeek 或 verl。

---

## 7. `AgentLoopOutput` 应该怎么从 RepoHarness trajectory 转出来？

verl 的 `AgentLoopOutput` 至少包括：

```python
prompt_ids: list[int]
response_ids: list[int]
response_mask: list[int]
```

其中 `response_ids` 可以包含 LLM 生成 token 和 tool response token；`response_mask` 中，1 表示 LLM generated token，0 表示 tool response token。([Verl][1])

对 RepoHarness 来说，一个 episode 可以转成：

```text
prompt_ids:
  初始 system / task / repo instruction token ids

response_ids:
  assistant turn 1 output token ids
  tool observation 1 token ids
  assistant turn 2 output token ids
  tool observation 2 token ids
  ...
  final assistant output token ids

response_mask:
  assistant turn token → 1
  tool observation token → 0
  permission denied observation → 0
  feedback verifier visible result → 0
  formal final verifier hidden result → 不进入 response_ids
  diagnostic-only artifact → 不进入 response_ids
```

你自己的 RepoHarness trajectory store 还应该保存更丰富的内容：

```text
GenerationRecord
ToolCallRecord
ToolResultRecord
PatchDiffRecord
VerifierRecord
RewardMetadata
FailureReason
ArtifactRefs
AuditBundle
```

也就是说：

```text
verl AgentLoopOutput = 训练需要的 compact tensor view
RepoHarness trajectory = 可审计、可回放、可过滤的 evidence view
```

这两者不要混在一起。

---

## 8. 这里有一个很关键的坑：context compaction / reset

你的 RepoHarness 有 context compaction，这很好，但接 verl 的标准 `AgentLoopOutput` 时要小心。

verl 的标准 multi-turn AgentLoopOutput 更自然适合这种轨迹：

```text
初始 prompt
  + assistant output
  + tool observation
  + assistant output
  + tool observation
  + ...
```

也就是上下文基本单调增长。

但很多真实 Agent 会做 destructive context management：

```text
前 20 轮 observation 太长
  → summarize
  → 丢掉大量原始 observation
  → 后续 prompt 只保留 summary + 当前关键 state
```

这时，每一轮模型生成时真正看到的是：

```text
prompt_ids_turn_t = compacted context
```

而不是：

```text
initial prompt + all previous raw observations
```

如果你最后仍然把整条 trajectory flatten 成一个线性序列，那么训练时计算 logprob 的条件上下文可能和 rollout 时真实条件上下文不一致。这就是 Forge 文章里说的 Agent 独立、TITO、context management 会让 token 一致性工程变复杂的原因之一。

所以第一版有三个选择：

### 选择 1：先限制 context compaction

在第一版 verl online RL 中，先禁用 destructive compaction，或者只做不改变训练语义的截断策略。这样最容易跑通。

### 选择 2：把 compaction 变成显式 model-visible 事件

例如：

```text
tool observation: [Context was compacted. Current memory summary: ...]
```

并把 summary 作为 mask=0 的 observation token 加入 response_ids。这样模型至少知道上下文变化。但如果旧 token 仍然出现在 flat training sequence 中，严格说还是有差异。

### 选择 3：升级 trajectory schema，按 model call 训练

也就是不再把一条 episode 压成一个简单的 `prompt_ids + response_ids`，而是保存：

```text
turn_1: prompt_ids_1 → output_ids_1
turn_2: prompt_ids_2 → output_ids_2
turn_3: prompt_ids_3 → output_ids_3
```

这更接近 Forge / slime / ROLL 那种 agent-native trajectory data plane，但需要你改 trainer batch 构造，不能完全依赖 verl 的简单 AgentLoopOutput。

我建议你第一版先走选择 1 或 2，等跑通后再做选择 3。**这也是为什么 RepoHarness 需要自己的 GenerationRecord，而不是只依赖 verl 的 AgentLoopOutput。**

---

## 9. 如果 Docker / verifier 不方便跑在 Ray worker 里怎么办？

这是 RepoHarness 接入 verl 时的另一个现实问题。

如果 `AgentLoopWorker` 所在机器都能访问 Docker daemon、数据集、repo cache、artifact volume，那么可以让 RepoHarnessRuntime 直接在 Ray worker 里启动容器。

但 SWE harness 经常会遇到：

```text
Ray worker 没有 Docker 权限
容器并发过高
artifact 路径不稳定
repo cache 不在本机
verification workspace 需要单独资源
pytest / build 阻塞 event loop
```

这时可以把 RepoHarness 环境执行部分拆成 EnvService：

```text
RepoHarnessVerlAgentLoop.run
  → EnvService.start_episode(task)
  → EnvService.next_prompt_ids()
  → verl LLMServerClient.generate(...)
  → EnvService.submit_model_output(token_ids, text)
  → EnvService.execute_tool(...)
  → ...
  → EnvService.final_verify()
  → return AgentLoopOutput
```

这种模式下：

```text
Ray worker 负责 RL rollout coroutine
RepoHarness EnvService 负责 Docker / tools / verifier / artifacts
verl LLMServerClient 负责模型生成
```

这比把 Docker 全塞进 Ray worker 更稳，也更接近 ROCK / AgentServer 的方向。

---

## 10. 第二阶段：RepoHarness-native AgentServer Mode

当你第一版跑通后，可以再升级成真正解耦模式：

```text
Trainer / Rollout Orchestrator
  → 分发 task
RepoHarness AgentServer
  → 管理 env / tools / verifier / trajectory
  → 调 LLMGateway 生成
  → 写 DataPool / TransferQueue / SampleBuffer
Trainer
  → 消费 sample
  → 计算 advantage / loss
  → 更新模型
  → 同步 rollout weights
```

这就更接近 Forge / ROLL / slime。Forge 材料里就是把 Agent 作为 trajectory producer，通过 Gateway Server 和 Data Pool 解耦 Agent 与训推引擎；你上传的 infra 总结里也把这个模式写成 `RLFramework -> [AgentServer <-> RolloutEngine] -> AsyncBuffer -> Trainer`。 

如果后续走这条路，你需要额外实现：

```text
SampleBuffer / DataPool
policy_version tracking
staleness filtering
rollout_logprobs storage
weight sync protocol
trajectory-to-training-batch converter
failure filtering before training
```

verl 的 fully async 文档里也能看到类似方向：fully async policy 把 Trainer 和 Rollouter 完全解耦，支持异步 sample generation、stream inference/training、freshness control、partial rollout；其中 `staleness_threshold` 控制 stale sample，`use_rollout_log_probs=True` 用 rollout 阶段的 logprob 保证 old_log_prob 和 rollout tokens/参数版本对应。([Verl][4])

如果你要做更进一步的数据平面解耦，verl 文档里的 TransferQueue 也很相关；它被定位为高性能数据存储与传输模块，用来解耦 post-training workflow 里不同计算任务之间的数据依赖，并支持 fine-grained / sub-sample-level 数据管理。([Verl][5])

但这不是第一版必须做的。第一版先用 AgentLoopBase thin wrapper 跑通 online RL，性价比最高。

---

## 11. 你现在应该怎么改 RepoHarness？

我建议按这个顺序。

### 第一步：把 RepoHarness 的 LLM provider 改成统一 Gateway

不要让 AgentLoop 直接调用 OpenAI / DeepSeek：

```python
class RepoHarnessRuntime:
    def __init__(self, llm_gateway: LLMGateway, ...):
        self.llm_gateway = llm_gateway
```

### 第二步：新增 `VerlLLMGateway`

它只做几件事：

```text
1. 接收 prompt_ids
2. 用 episode_id 作为 request_id 调用 verl client
3. 拿回 output_token_ids / logprobs / stop_reason / extra_fields
4. decode 成 text 给 tool parser
5. 写入 GenerationRecord
```

注意：不要用 OpenAI chat completion API 做 online RL 主路径。verl 文档明确说明 AsyncLLMServer 支持 chat completion 和 token-in-token-out，但多轮 RL 中应优先考虑 token-in-token-out，因为 text/message round-trip 会造成 token mismatch。([Verl][1])

### 第三步：新增 `RepoHarnessVerlAgentLoop`

它继承 verl 的 `AgentLoopBase`，但内部只做 adapter：

```python
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    async def run(self, sampling_params: dict, **kwargs):
        task = RepoHarnessTaskAdapter.from_verl_dataset_fields(kwargs)

        gateway = VerlLLMGateway(
            llm_client=self.llm_server_client,  # 或旧版本的 async_llm_server_manager
            tokenizer=self.tokenizer,
        )

        runtime = RepoHarnessRuntime(
            task=task,
            llm_gateway=gateway,
            mode="online_rl",
        )

        episode = await runtime.run_episode()

        return AgentLoopOutput(
            prompt_ids=episode.training_view.prompt_ids,
            response_ids=episode.training_view.response_ids,
            response_mask=episode.training_view.response_mask,
        )
```

具体成员名要按你的 verl 版本调整；核心是这个结构。

### 第四步：RepoHarness 内部生成两份 view

```text
training_view:
  prompt_ids
  response_ids
  response_mask
  reward fields needed by verl

audit_view:
  transcript.jsonl
  events.jsonl
  artifact refs
  verifier evidence
  patch diff
  failure reason
  acceptance bundle
```

### 第五步：先不要碰 verl 的 `AgentLoopWorker`

除非你要改 Ray worker 调度、并发策略或 worker 生命周期，否则不要改 `AgentLoopWorker`。官方文档里 `AgentLoopWorker` 是负责接收 chunk、为每个 prompt spawn 用户定义的 `AgentLoopBase`、并发调度 coroutines 的那一层；你真正需要实现的是 `AgentLoopBase.run()`。([Verl][1])

---

## 12. 最终回答你的问题

你问：

> 现在如果要接入我的 RepoHarness，是不是不能像之前那样直接继承 AgentLoopWorker 了？是不是应该在 RepoHarness 的 agent loop 中增加一层 LLM Gateway / Rollout Engine Adapter，例如接 verl 的 AsyncLLMServer，或者再多加一层 AsyncLLMServerManager，或者直接接入现成的 verl AsyncLLMServerManager？

我的建议是：

**不要直接继承/改造 `AgentLoopWorker`，也不要在 RepoHarness 里重新实现一层 `AsyncLLMServerManager`。**

第一版最佳方案是：

```text
继续使用 verl AgentLoop 架构
但只实现一个薄的 RepoHarnessVerlAgentLoop
把 RepoHarnessRuntime 作为独立系统调用
在 RepoHarnessRuntime 内部使用 VerlLLMGateway
VerlLLMGateway 包装 verl 已经传入的 LLMServerClient / AsyncLLMServerManager
```

也就是：

```text
RepoHarness 不直接接 AsyncLLMServer
RepoHarness 接自己的 LLMGateway
LLMGateway 的 verl backend 调现成的 LLMServerClient / AsyncLLMServerManager
```

一句话：

**verl 的 rollout worker / AsyncLLMServer 解决“高吞吐生成 token”；RepoHarness 的 Gateway 解决“我的完整 SWE agent harness 如何以 token 对齐、可审计、可切换 backend 的方式调用这个生成能力”。**

等这个 thin-wrapper 版本跑通之后，你再考虑把 RepoHarness 升级成独立 AgentServer + DataPool / TransferQueue + async sample buffer，那时才真正接近 Forge / ROLL 那种完整大厂式解耦架构。

[1]: https://verl.readthedocs.io/en/latest/advance/agent_loop.html "Agent Loop — verl  documentation"
[2]: https://verl.readthedocs.io/en/v0.5.x/advance/agent_loop.html "Agent Loop — verl  documentation"
[3]: https://raw.githubusercontent.com/verl-project/verl/main/verl/workers/rollout/llm_server.py "raw.githubusercontent.com"
[4]: https://verl.readthedocs.io/en/latest/advance/fully_async.html "Recipe: Fully Async Policy Trainer — verl  documentation"
[5]: https://verl.readthedocs.io/en/latest/data/transfer_queue.html "TransferQueue Data System — verl  documentation"
