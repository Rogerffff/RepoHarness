# RepoHarness 接入 verl 的架构计划

本文档是 `docs/agentic_RL/harness_connect_verl.md` 的正式分析版，用于说明 RepoHarness 应该如何接入 verl，形成面向软件工程智能体强化学习训练的架构路线。本文暂时不展开具体 schema 字段、命令行参数和文件级实施清单，而是聚焦最关键的系统边界与接口设计：`RepoHarnessVerlAgentLoop`、`LLMGateway`、`VerlLLMGateway`、RepoHarness runtime、verl `LLMServerClient`、训练 view 和审计 view 的关系。

状态说明：本文描述的是 RepoHarness 未来接入 verl 的架构计划，不表示当前仓库已经实现 `RepoHarnessVerlAgentLoop`、`VerlLLMGateway`、`LLMGateway`、`training_view` 或 `audit_view`。截至本文档编写时，RepoHarness 已具备可执行 workspace、工具运行、agent loop、trajectory、verifier、reward metadata 和 export audit 等基础能力；verl online reinforcement learning 接入仍属于后续计划。本文中的 `RepoHarnessRuntime` 指拟抽出的 runtime facade，也就是对当前 RepoHarness 任务执行、agent loop、workspace、tool runtime、verifier 和 trajectory recorder 的统一调用外观，不表示当前代码已经存在同名类。

相关背景材料：

- [verl_fully_async_carr_review.md](verl_fully_async_carr_review.md)：回顾 verl `fully_async_policy` 和 CaRR DeepSearch 项目的 async partial 经验。
- [repo_harness_verl_detailed_implementation_plan.md](repo_harness_verl_detailed_implementation_plan.md)：在本文架构边界基础上继续细化的分阶段实施计划，包含当前 `reference/verl` submodule 源码依据、接口拆分、测试策略、fully async 演进和验收矩阵。
- [harness_connect_verl.md](harness_connect_verl.md)：早期讨论稿，保留了更接近问答过程的解释。

## 0. 术语说明

- `LLMGateway`：RepoHarness 自己的模型生成调用抽象，用来屏蔽 OpenAI、DeepSeek、本地 vLLM、SGLang、verl 等不同 backend。
- `VerlLLMGateway`：`LLMGateway` 的 verl backend，负责把 RepoHarness 的模型生成请求转成 verl `LLMServerClient.generate(...)` 请求。
- `token-in-token-out`：模型生成接口直接接收 token ids 并返回真实生成 token ids，避免从最终文本重新分词导致训练 token 序列漂移。
- `sticky session`：多轮 episode 使用同一个 `request_id` 路由到同一台推理 server，尽量复用前缀缓存。
- `training_view`：训练侧实际消费的紧凑张量视图，包含 prompt、response、mask、log probability、reward 和回指审计证据的稳定标识。
- `audit_view`：RepoHarness 保存的完整审计视图，包含 transcript、events、artifacts、patch、verifier evidence、reward metadata 和 failure reason。
- `model-visible observation`：模型在同一次 rollout 中实际能看到的 observation。final verifier hidden result、reward label 和 audit-only artifact 不应进入这类上下文。
- `destructive compaction`：会丢弃或改写原始上下文 token 的压缩方式，可能导致训练时条件上下文和 rollout 时条件上下文不一致。
- `smoke test`：小规模连通性验证，用少量任务确认接口、字段和训练批次可以跑通，不代表性能或完整验收。

## 1. 核心结论

RepoHarness 不应该被改造成 verl 内部的一组工具函数，也不应该直接接管 verl 的 `AsyncLLMServer`、`LLMServerManager` 或 `AgentLoopWorker`。

更合理的第一版接入方式是：

```text
verl 负责：
  policy model
  rollout inference server
  log probability
  PPO / GRPO / DAPO 等训练算法
  checkpoint
  参数同步
  训练指标

RepoHarness 负责：
  软件工程任务 materialization
  executable workspace
  tool runtime
  permission boundary
  context management
  agent loop orchestration
  trajectory store
  final verifier
  reward metadata
  export audit
```

二者之间通过一层薄适配连接：

```text
RepoHarnessVerlAgentLoop
  作为 verl AgentLoopBase 的实现

VerlLLMGateway
  作为 RepoHarness LLMGateway 的 verl backend
```

一句话概括：

```text
verl 管训练和高吞吐 token 生成；
RepoHarness 管真实软件工程环境、工具执行、verifier 和可审计轨迹；
Gateway 用 token 对齐的方式把二者连接起来。
```

## 2. 第一版推荐架构：Thin Adapter Mode

第一版不需要把 RepoHarness 拆成独立服务，也不需要修改 verl 的 rollout worker。最小架构如下：

```text
verl PPO / GRPO Trainer
  -> AgentLoopManager.generate_sequences(...)
    -> AgentLoopWorker
      -> RepoHarnessVerlAgentLoop.run(...)
        -> RepoHarnessRuntime.run_episode(...)
          拟抽出的 RepoHarness runtime facade
          -> TaskAdapter
          -> WorkspaceBackend
          -> ToolRuntime
          -> PermissionPolicy
          -> ContextManager
          -> TrajectoryStore
          -> FinalVerifier
          -> LLMGateway
            -> VerlLLMGateway.generate_turn(...)
              -> verl LLMServerClient.generate(...)
                -> AsyncLLMServer
                  -> vLLM 或 SGLang
```

这个模式里，`RepoHarnessVerlAgentLoop` 只是 verl 与 RepoHarness 之间的薄封装。RepoHarness 的业务逻辑仍然留在拟抽出的 RepoHarness runtime facade 内部，而不是被搬进 verl 的 worker 代码里。

## 3. 为什么接入点是 AgentLoopBase，而不是 AgentLoopWorker

verl 的 Agent Loop 架构中，`AgentLoopWorker` 是框架调度层。它负责：

```text
接收 batch chunk
创建用户自定义 AgentLoop
并发运行多个 agent loop coroutine
收集 AgentLoopOutput
后处理为 DataProto
```

因此，RepoHarness 第一版不应该继承或改造 `AgentLoopWorker`。真正应该实现的是 `AgentLoopBase.run(...)`。

设计形态如下：

```python
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    async def run(self, sampling_params: dict, **kwargs) -> AgentLoopOutput:
        task = RepoHarnessTaskAdapter.from_verl_dataset_fields(kwargs)

        gateway = VerlLLMGateway(
            llm_client=self.llm_server_client,
            tokenizer=self.tokenizer,
        )

        runtime = RepoHarnessRuntime(
            task=task,
            llm_gateway=gateway,
            mode="online_rl",
        )

        episode = await runtime.run_episode()
        return episode.to_verl_agent_loop_output()
```

实际代码的参数名需要根据所用 verl 版本调整。这里的 `RepoHarnessRuntime` 是概念性 facade 名称，落地时可以是当前 `AgentLoop`、evaluation runner、task runner 或一个新抽出的 runtime wrapper；系统含义应该保持不变。

## 4. LLMGateway 是 RepoHarness 的关键解耦层

RepoHarness 当前和未来都不应该直接依赖某一个模型 provider 或某一个训练框架。它应该依赖自己的 `LLMGateway` 抽象。

统一抽象可以理解为：

```text
RepoHarnessRuntime
  需要模型生成时
    -> 调用 LLMGateway.generate_turn(...)
```

`LLMGateway` 背后可以有多个 backend：

```text
OpenAIGateway
  用于 debug、评测、离线轨迹和蒸馏数据。

DeepSeekGateway
  用于 debug、评测、离线轨迹和蒸馏数据。

LocalVLLMGateway
  用于独立本地 rollout 或离线数据生成。

SGLangGateway
  用于独立高吞吐 rollout。

VerlLLMGateway
  用于 verl online reinforcement learning。
```

这个设计有两个好处。

第一，RepoHarness 不会被 verl 绑定死。以后如果要接入 slime、ROLL、AReaL、SGLang-native trainer 或其他训练后端，只需要新增一个 Gateway backend 或 trainer adapter，而不是重写 RepoHarness agent loop。

第二，RepoHarness 可以同时保留真实 provider 路径和开源权重训练路径。OpenAI、DeepSeek、Claude 这类 provider 可以继续用于评测、蒸馏、偏好数据和离线 trajectory；verl `LLMServerClient` 则用于真正需要可训练 policy 的 online reinforcement learning。

`LLMGateway` 与当前 RepoHarness provider client 的关系可以分阶段处理。第一版不需要立刻替换现有 `ModelClient` 抽象，可以先在 online RL 路径增加一个兼容 adapter，让 RepoHarness agent loop 通过统一 Gateway 调用模型；现有 OpenAI、DeepSeek、mock、replay provider 可以被包装成 Gateway backend。等 token-level generation record、mask 和 rollout log probability 契约稳定后，再逐步把普通 provider 路径也迁移到同一层抽象下。

## 5. VerlLLMGateway 的职责

`VerlLLMGateway` 不是再实现一套 `AsyncLLMServerManager`。在当前 verl 官方文档和较新源码中，Agent Loop 通常通过 `LLMServerClient` 调用推理服务；旧材料或旧版本中可能出现 `AsyncLLMServerManager` 这个名称。两者在本文中的关注点相同：它们都是 verl 已经提供的推理 server client 或 manager，不应该由 RepoHarness 重新实现。

`VerlLLMGateway` 只是 RepoHarness 侧的适配层，负责把 RepoHarness 的一次模型调用转换成 verl 的 token-in-token-out 生成请求。

它的职责包括：

```text
1. 接收 RepoHarness 当前 turn 的 prompt_ids。
2. 使用 episode_id 作为 request_id，保证多轮 episode 的 sticky session。
3. 调用 verl 传入的 LLMServerClient.generate(...)。
4. 接收真实 output_token_ids。
5. 如果当前 verl 配置启用了 rollout log probabilities，则同步记录 response_logprobs，并在转换 `AgentLoopOutput` 时映射到训练侧需要的 `rollout_log_probs`。
6. 如果当前 verl 版本或 rollout backend 返回 stop reason、policy version 或 rollout engine metadata，则记录到 RepoHarness generation record；如果没有返回，则以显式缺省值记录。
7. 解码 output_token_ids，交给 RepoHarness 的 tool parser 使用。
8. 将生成结果写入 RepoHarness 的 GenerationRecord。
```

伪代码如下：

```python
class VerlLLMGateway:
    def __init__(self, llm_client, tokenizer):
        self.llm_client = llm_client
        self.tokenizer = tokenizer

    async def generate_turn(self, request: GenerationRequest) -> GenerationRecord:
        output = await self.llm_client.generate(
            request_id=request.episode_id,
            prompt_ids=request.prompt_ids,
            sampling_params=request.sampling_params,
        )

        token_ids = getattr(output, "token_ids", output)
        log_probs = getattr(output, "log_probs", None)
        stop_reason = getattr(output, "stop_reason", None)
        text = self.tokenizer.decode(token_ids, skip_special_tokens=False)

        return GenerationRecord(
            episode_id=request.episode_id,
            turn_id=request.turn_id,
            prompt_ids=request.prompt_ids,
            output_token_ids=token_ids,
            output_text=text,
            logprobs=log_probs,
            stop_reason=stop_reason,
            backend="verl",
        )
```

这里最重要的是：online reinforcement learning 路径必须尽量使用 token-in-token-out。不能把最终 transcript 文本重新套 chat template 再分词作为训练样本，因为多轮工具调用、长 observation 和 context compaction 会导致 token 序列不一致。`VerlLLMGateway` 的最低正确性要求是记录真实生成 token；log probability、stop reason 和 policy version 等字段则根据 verl 版本、rollout backend 和配置能力逐步补齐。

## 6. RepoHarnessVerlAgentLoop.run(...) 的职责边界

`RepoHarnessVerlAgentLoop.run(...)` 应该很薄。它不应该重新实现 RepoHarness 的工具系统，也不应该在里面手写 Docker、verifier、trajectory store 等逻辑。

它只做五件事：

```text
1. 从 verl dataset fields 中解析出 RepoHarness task。
2. 创建 VerlLLMGateway。
3. 创建或调用 RepoHarnessRuntime。
4. 等待 RepoHarnessRuntime 跑完一个 episode。
5. 把 RepoHarness episode 转换成 AgentLoopOutput。
```

也就是说：

```text
RepoHarnessVerlAgentLoop.run(...)
  是 verl 调 RepoHarness 的入口。

RepoHarnessRuntime.run_episode(...)
  才是真正的软件工程智能体执行过程。
```

这个边界有利于保留 RepoHarness 的独立价值，也方便未来把 runtime 从 Ray worker 内部迁移到独立 EnvService 或 AgentServer。

## 7. Training View 与 Audit View 必须分开

RepoHarness 的 trajectory 很丰富，包含 transcript、events、tool calls、tool results、artifacts、patch、verifier result、reward metadata 和 export audit。verl 训练不需要消费全部这些内容。

因此，每条 episode 应该生成两份 view：

```text
training_view:
  面向 verl trainer。
  包含 prompt_ids、response_ids、response_mask、rollout_log_probs、reward 等训练必需内容。
  同时保存 episode_id、task_id、run_id、trajectory_ref、policy_version、generation_record_refs 等稳定引用，用于回指 audit_view。

audit_view:
  面向 RepoHarness 审计、回放、验收和导出。
  包含 transcript、events、artifact refs、patch diff、verifier evidence、reward metadata、failure reason 等完整证据。
```

二者关系是：

```text
verl AgentLoopOutput = 训练需要的紧凑张量视图
RepoHarness trajectory = 可审计、可回放、可过滤的 evidence view
```

不能为了让 verl 更容易训练，就把 RepoHarness 的审计事实压扁成不可追溯的纯文本序列。也不能把 hidden final verifier result 或 reward label 泄漏进同一次 rollout 的 model-visible observation。

## 8. AgentLoopOutput 的基础映射

RepoHarness episode 转成 `AgentLoopOutput` 时，基础映射可以这样理解：

```text
prompt_ids:
  初始 system、task、repository instruction 和首轮上下文 token。

response_ids:
  assistant turn token
  tool observation token
  assistant turn token
  tool observation token
  ...
  final assistant token

response_mask:
  assistant 生成 token -> 1
  tool observation token -> 0
  permission denied observation -> 0
  visible intermediate feedback -> 0
  formal final verifier hidden result -> 不进入 response_ids
  audit-only artifact -> 不进入 response_ids
```

这样可以保证训练损失只作用在模型自己生成的 token 上，而不是工具输出、测试日志、verifier 结果或审计证据上。

除了上面三个基础字段，当前 verl `AgentLoopOutput` 的常见边界还包括：

```text
response_logprobs:
  rollout 阶段生成 token 时得到的 log probability。

reward_score:
  可以进入训练 batch 的标量 reward 或 reward tensor 来源。

num_turns:
  episode 中的轮次统计。

metrics:
  rollout timing、tool calls 等指标。

extra_fields:
  训练后处理、reward manager 或审计回指需要的非张量元数据。
```

RepoHarness 的完整 verifier evidence 应继续保存在 `audit_view` 中。训练侧可以接收 final reward 的标量结果和审计引用，但不应该把 final verifier hidden result 直接放进模型可见上下文。

## 9. 第一版执行流程

第一版完整流程如下：

```text
1. verl Trainer 从数据集中取一条任务样本。
2. AgentLoopManager 将样本分发给 AgentLoopWorker。
3. AgentLoopWorker 创建 RepoHarnessVerlAgentLoop。
4. RepoHarnessVerlAgentLoop.run(...) 解析 RepoHarness task。
5. RepoHarnessRuntime 创建 workspace 和 trajectory recorder。
6. RepoHarnessRuntime 需要模型输出时，调用 LLMGateway。
7. online RL 模式下，LLMGateway 路由到 VerlLLMGateway。
8. VerlLLMGateway 调用 verl LLMServerClient.generate(...)。
9. RepoHarnessRuntime 解析模型输出并执行工具。
10. 多轮循环直到 episode 结束。
11. RepoHarnessRuntime 运行 final verifier。
12. RepoHarnessRuntime 生成 reward metadata 和 audit artifacts。
13. RepoHarnessVerlAgentLoop 把 episode.training_view 转换成 AgentLoopOutput。
14. verl Trainer 消费 AgentLoopOutput 继续训练。
```

这个流程不要求 RepoHarness 直接管理 vLLM 或 SGLang server，也不要求 RepoHarness 理解 FSDP、Megatron、Ray worker group 或 NCCL 参数同步细节。更具体地说，当前本地 verl 快照中的 `FullyAsyncRollouter` 和 `FullyAsyncTrainer` 是通过 `ray_worker_group_cls: RayWorkerGroup = RayWorkerGroup` 接入 Ray worker group 编排层；如果讨论中把这层称为 `FullyAsyncRayWorkerGroup`，RepoHarness 也只应把它理解为 verl 内部训练和 rollout worker 编排机制，而不是 RepoHarness 自己的稳定接入接口。

## 10. 第一版最低配置前提

第一版接入虽然不展开具体字段，但仍然有几个前置条件：

```text
verl 侧：
  能通过配置加载自定义 Agent Loop。
  数据集中能够指定或推导出自定义 agent_name。
  rollout backend 能提供 token-in-token-out 生成路径。
  如果要训练 PPO/GRPO，rollout 阶段应启用 log probability 记录。

RepoHarness 侧：
  模型生成调用必须经过 LLMGateway。
  online RL 路径必须能接收 prompt_ids 并保存 output_token_ids。
  episode 结束后必须能生成 training_view 和 audit_view。
  training_view 必须能稳定回指 audit_view。
```

在 verl 配置上，具体名称会随版本变化，但通常需要关注 `actor_rollout_ref.rollout.mode`、自定义 Agent Loop 注册方式、`agent_name` 选择方式、`calculate_log_probs` 和 rollout backend 类型。第一版不要依赖“最终 messages 重新 apply chat template”来构造训练 token。

## 11. 为什么第一版不要直接上 fully async

第一版最重要的是验证语义正确性，而不是吞吐最大化。需要先证明：

```text
prompt_ids 与 response_ids 正确。
response_mask 正确。
tool observation 不参与训练损失。
rollout_log_probs 与生成 token 对齐。
final verifier reward 没有泄漏到模型可见上下文。
RepoHarness trajectory 可以回指训练样本。
```

如果这些边界没有跑通，直接引入 fully async、staleness 和 partial rollout 会让问题更难定位。

因此建议第一版：

```text
使用普通 verl AgentLoop。
每个 RepoHarnessVerlAgentLoop.run(...) 完整跑完一条 episode。
不启用 partial rollout。
先选择小型任务、短 horizon、确定性 verifier。
```

## 12. 为什么规模化训练后续应走异步架构

虽然第一版不建议直接上 fully async，但如果目标是高吞吐、多 GPU 持续训练和长尾软件工程任务规模化，从软件工程任务性质和当前主流 agentic reinforcement learning infra 方向看，后续应当优先演进到异步架构。

原因如下。

第一，软件工程任务天然长尾：

```text
有些任务只需要读一两个文件。
有些任务需要修改多个模块。
有些任务需要安装依赖。
有些任务需要跑慢测试。
有些任务会遇到 flaky test、环境失败或 verifier 超时。
```

如果坚持同步 batch rollout，一个最慢任务会拖住整个训练 step。

第二，工具调用和 verifier 会引入大量非 GPU 时间。Rollouter 等待 Docker、文件系统、测试命令和 verifier 时，Trainer 不应该空闲。

第三，大厂和主流研究系统都在把 agent runtime 与 trainer 解耦。常见方向是：

```text
AgentServer / EnvService
  负责环境交互和 trajectory 生产。

RolloutEngine / LLMGateway
  负责高吞吐 token 生成。

AsyncBuffer / DataPool / TransferQueue
  负责样本缓冲、staleness 控制和训练数据传输。

Trainer
  负责 advantage、loss、参数更新和权重同步。
```

从能力边界看，RepoHarness 更接近 AgentServer、EnvService 和 trajectory data plane。因此，对规模化软件工程智能体训练来说，异步化不是额外优化，而是走向持续训练和高资源利用率的关键方向。

## 13. fully async 的演进路线

建议分阶段演进。

### 阶段一：普通 AgentLoop 接入

目标：

```text
RepoHarnessVerlAgentLoop.run(...) 能完整跑完一条 episode。
VerlLLMGateway 能正确调用 LLMServerClient。
AgentLoopOutput 能被 verl trainer 消费。
RepoHarness audit_view 能回指训练样本。
```

这一阶段不处理中断恢复。

### 阶段二：EnvService Mode

如果 Ray worker 不适合直接运行 Docker、依赖安装和 verifier，可以把 RepoHarness 环境执行拆成独立服务：

```text
RepoHarnessVerlAgentLoop.run(...)
  -> EnvService.start_episode(...)
  -> EnvService.next_prompt_ids(...)
  -> VerlLLMGateway.generate_turn(...)
  -> EnvService.submit_model_output(...)
  -> EnvService.execute_tool(...)
  -> EnvService.final_verify(...)
  -> AgentLoopOutput
```

这样 Ray worker 主要负责 rollout coroutine，RepoHarness EnvService 负责 workspace、tools、verifier 和 artifacts。

### 阶段三：fully async，但 partial_rollout=false

目标是先让 Rollouter 和 Trainer 解耦，但不要求中断恢复。

```text
Rollouter 持续生成完整 RepoHarness episode。
MessageQueue 缓冲已完成样本。
Trainer 持续消费样本训练。
verl 的参数同步流程定期把 trainer 侧新权重同步给 rollout 侧推理服务。
```

在当前 `reference/verl` submodule 中，不应把这一步理解成存在一个固定名为 `ParameterSynchronizer` 的类。更准确的代码事实是：fully async 参数同步主要由 `FullyAsyncTrainer.set_rollouter(...)`、`CheckpointEngineManager`、`_fit_update_weights(...)`、`checkpoint_manager.update_weights(...)` 和 `rollouter.reset_staleness(...)` 共同完成。具体说明见 [repo_harness_verl_detailed_implementation_plan.md](repo_harness_verl_detailed_implementation_plan.md)。

这一步需要引入：

```text
policy_version
rollout_log_probs
staleness metrics
sample filtering
queue backpressure
```

但还不需要保存半途中的 workspace 状态。

### 阶段四：fully async + partial_rollout=true

这是最复杂但也是最适合长任务规模化的一步。

RepoHarness 需要支持：

```text
保存 episode state。
保存 workspace state 或可恢复 workspace reference。
保存 tool state。
保存 trajectory recorder state。
保存 context manager state。
保存已生成 token、logprobs 和 masks。
记录 param_version_start 和 param_version_end。
在参数同步后从中断点恢复。
```

它还需要和 verl fully async 的中断恢复接口对齐：

```text
cancellation_event:
  参数同步或队列反压时，通知 Agent Loop 尽快停止当前执行。

is_cancel=True:
  Agent Loop 返回的取消标志，表示这不是完整可训练样本。

extra_fields:
  保存 RepoHarness episode state、workspace reference、trajectory recorder state 和当前 AgentState。

generate_for_partial(...):
  如果 rollout backend 支持 partial generation，则保存已生成 token 和 log probability，参数同步后继续生成。
```

只有当这些状态边界都稳定以后，才应该打开 `partial_rollout=true`。

### 阶段五：RepoHarness-native AgentServer + 多训练后端

最终形态可以进一步解耦：

```text
RepoHarness AgentServer
  -> 生产可审计 trajectory
  -> 写入 SampleBuffer / DataPool

verl / slime / 其他 trainer
  -> 从 SampleBuffer 消费样本
  -> 训练 policy
  -> 同步 rollout weights
```

这时 RepoHarness 不再只是 verl 的 `AgentLoopBase` 实现，而是一个 framework-neutral 的软件工程智能体环境服务。

这一节是 [verl_fully_async_carr_review.md](verl_fully_async_carr_review.md) 中三阶段技术顺序的 RepoHarness 细化版本。CaRR 回顾文档里的三阶段强调普通 AgentLoop、fully async、partial rollout 的粗粒度顺序；本文的五阶段额外拆出了 EnvService 和多训练后端两个工程落地点。

## 14. 与 slime 等其他后端的关系

给 RepoHarness 增加 `LLMGateway`、trainer adapter 和 sample adapter 的一个重要目的，就是避免把系统锁死在 verl。

未来接入 slime 时，整体思路应该类似：

```text
RepoHarnessRuntime
  -> LLMGateway
    -> SlimeSGLangGateway 或 SlimeRolloutGateway
```

但这里需要区分两层 adapter：

```text
LLMGateway:
  负责模型生成调用解耦。
  例如把 RepoHarness 的 prompt_ids 或消息上下文发给 SGLang、vLLM、verl LLMServerClient 或 slime 侧 serving endpoint。

trainer adapter / sample adapter:
  负责把 RepoHarness trajectory 转成训练框架可消费的样本。
  对 slime 来说，这可能是 slime Sample、custom rollout function 输出、rollout buffer item 或 data buffer 样本。
```

因此，接入 slime 不能只靠新增一个 `SlimeGateway` 完成。还必须有 RepoHarness trajectory 到 slime `Sample.tokens`、`loss_mask`、`rollout_log_probs`、`reward`、`status` 和 metadata 的转换层。

也就是说：

```text
RepoHarness 只稳定自己的环境、轨迹和 reward 边界。
不同强化学习训练框架通过 adapter 接入。
```

这样 RepoHarness 的长期定位会更清楚：

```text
不是某一个 trainer 的插件；
而是软件工程智能体强化学习的 runtime、environment、trajectory 和 audit data plane。
```

## 15. 风险与约束

第一，token 对齐是最高风险。RepoHarness 必须记录真实生成 token，而不能只保存最终文本。

第二，reward boundary 必须严格。final verifier 和 reward metadata 不能泄漏进同一次 rollout 的模型可见上下文。

第三，context compaction 会让训练语义复杂。第一版最好限制 destructive compaction，或者把 compaction 作为显式 model-visible observation，并确保 mask 正确。

第四，Ray worker 上直接运行 Docker 可能不稳定。需要尽早评估 EnvService Mode。

第五，fully async 的 staleness 会带来 off-policy 风险。必须保存 rollout log probabilities、policy version 和样本新鲜度指标。

第六，partial rollout 对 RepoHarness 来说比 search agent 更难。软件工程任务包含 workspace、patch、tool execution、verifier 和 artifacts，不能只保存 token 状态。

## 16. 推荐路线

推荐路线如下：

```text
1. 先完成普通 AgentLoop 接入。
2. 通过 VerlLLMGateway 跑通 token-in-token-out generation。
3. 生成 training_view 和 audit_view。
4. 让 verl 消费 AgentLoopOutput 完成小任务训练 smoke test。
5. 再拆 EnvService，降低 Ray worker 与 Docker/verifier 的耦合。
6. 再启用 fully async 且 partial_rollout=false。
7. 最后设计 RepoHarness 可恢复 episode state，再启用 partial_rollout=true。
8. 保持 LLMGateway 和 trainer adapter 抽象，后续接 slime 或其他训练后端。
```

这个路线能同时满足两个目标：

```text
短期：
  尽快复用 verl 已经实现的训练、rollout server、log probability 和参数同步能力。

长期：
  保持 RepoHarness 的独立性，让它演进成可接多个强化学习训练后端的软件工程智能体环境与轨迹基础设施。
```
