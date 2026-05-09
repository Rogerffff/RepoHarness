# RepoHarness 接入 verl 详细实施计划

本文档是在 [repo_harness_verl_architecture_plan.md](repo_harness_verl_architecture_plan.md) 的基础上继续细化的实施计划。上一篇文档回答“为什么这样接入”和“关键系统边界在哪里”，本文档回答“实际落地时应该分哪些阶段、改哪些接口、如何验证每一步没有破坏 RepoHarness 的可审计训练轨迹目标”。

本文档仍然是实施计划，不表示当前仓库已经完成这些接口。当前已经执行的仓库变更只有：把 verl 作为 Git submodule 加入本仓库，路径为 `reference/verl`，当前指向 `main` 分支 commit `f400fb7654b217632323b906f86e345e201fb736`。

## 0. 本计划的目标

RepoHarness 当前定位是软件工程智能体 Harness，核心价值是把真实或半真实仓库任务转成可执行、可审计、可导出的训练轨迹。接入 verl 的目标不是把 RepoHarness 改写成 verl 的一个工具插件，而是把 RepoHarness 变成可以服务 online reinforcement learning 的软件工程环境和轨迹数据层。

目标闭环如下：

```text
verl trainer
  -> verl AgentLoopManager / AgentLoopWorker
    -> RepoHarnessVerlAgentLoop.run(...)
      -> RepoHarness runtime
        -> executable workspace
        -> tools
        -> model generation through LLMGateway
        -> verifier
        -> reward metadata
        -> audit trajectory
      -> AgentLoopOutput
  -> PPO / GRPO / DAPO 等训练步骤
```

第一版成功标准不是大规模训练吞吐，而是跑通一条语义正确的 online rollout：

```text
verl 可以调用 RepoHarness 跑一条软件工程 episode。
RepoHarness 可以通过 verl 的 LLMServerClient 获取可训练模型的 token 生成。
RepoHarness 可以生成完整 audit trajectory。
RepoHarness 可以返回 verl 需要的 AgentLoopOutput。
prompt_ids、response_ids、response_mask、response_logprobs、reward_score 的含义正确。
final verifier、reward metadata 和 hidden evaluator evidence 不泄漏到模型可见上下文。
```

## 1. 代码依据与版本边界

### 1.1 verl submodule

本计划以当前新增的 submodule 为分析对象：

```text
路径：reference/verl
远端：https://github.com/verl-project/verl.git
分支：main
commit：f400fb7654b217632323b906f86e345e201fb736
```

需要注意：verl 的 Agent Loop 和 fully async 相关模块仍在快速演进，实施时必须以 submodule 当前 commit 为准，而不是只依赖旧项目经验或旧版文档中的类名。

### 1.2 verl 中与本计划直接相关的源码

普通 Agent Loop 路径：

```text
reference/verl/verl/experimental/agent_loop/agent_loop.py
reference/verl/verl/experimental/agent_loop/single_turn_agent_loop.py
reference/verl/verl/experimental/agent_loop/tool_agent_loop.py
reference/verl/verl/trainer/config/rollout/rollout.yaml
reference/verl/verl/workers/config/rollout.py
reference/verl/verl/trainer/ppo/ray_trainer.py
```

推理服务路径：

```text
reference/verl/verl/workers/rollout/llm_server.py
reference/verl/verl/workers/rollout/replica.py
reference/verl/verl/workers/rollout/vllm_rollout/vllm_async_server.py
reference/verl/verl/workers/rollout/sglang_rollout/async_sglang_server.py
```

fully async 路径：

```text
reference/verl/verl/experimental/fully_async_policy/fully_async_rollouter.py
reference/verl/verl/experimental/fully_async_policy/fully_async_trainer.py
reference/verl/verl/experimental/fully_async_policy/message_queue.py
reference/verl/verl/experimental/fully_async_policy/detach_utils.py
```

### 1.3 RepoHarness 中与本计划直接相关的源码

当前模型调用抽象：

```text
src/repo_harness/model_client/protocol.py
src/repo_harness/model_client/schemas.py
src/repo_harness/model_client/factory.py
src/repo_harness/model_client/providers/openai.py
src/repo_harness/model_client/providers/deepseek.py
src/repo_harness/model_client/replay.py
src/repo_harness/model_client/mock.py
```

当前 agent loop 和运行编排：

```text
src/repo_harness/agent_loop/loop.py
src/repo_harness/agent_loop/schemas.py
src/repo_harness/evaluation/runner.py
src/repo_harness/tools/
src/repo_harness/workspace/
src/repo_harness/verifier/
src/repo_harness/reward/
src/repo_harness/trajectory/
src/repo_harness/export/
```

相关设计文档：

```text
docs/02-system-architecture.md
docs/03-agent-loop-and-message-protocol.md
docs/07-verifier-reward-and-evaluation.md
docs/08-trajectory-store-and-training-export.md
docs/agentic_RL/repo_harness_verl_architecture_plan.md
docs/agentic_RL/verl_fully_async_carr_review.md
```

## 2. 实施原则

### 2.1 RepoHarness 保持独立系统边界

RepoHarness 不应该直接变成 verl 的一个内部工具函数集合。verl 负责训练、rollout 推理服务、参数同步、log probability 和 distributed worker 编排；RepoHarness 负责任务 materialization、workspace、工具执行、权限边界、agent loop 语义、trajectory、verifier、reward metadata 和 export audit。

最重要的边界是：

```text
verl 可以调用 RepoHarness。
RepoHarness 可以通过 Gateway 调用 verl 的推理能力。
RepoHarness 不直接管理 verl 的 Ray worker group、FSDP、Megatron、NCCL、vLLM server 生命周期或参数同步。
```

### 2.2 第一版优先语义正确，不优先吞吐

第一版不要直接从 fully async 开始。原因不是 fully async 不重要，而是软件工程任务的训练字段更容易出错：工具 observation 是否参与 loss、final verifier 是否泄漏、reward 是否只来自 final verifier、token ids 是否和 rollout 生成一致，这些问题必须先在普通 Agent Loop 路径里验证清楚。

第一版建议使用：

```text
verl 普通 AgentLoopBase 接入
一条 RepoHarness episode 完整跑完后返回 AgentLoopOutput
不启用 partial rollout
先使用短 horizon、小任务集、确定性 verifier
```

当这些语义边界稳定后，再演进到 fully async。

### 2.3 通过 LLMGateway 解耦训练后端

RepoHarness 不应该直接在内部到处调用 verl `LLMServerClient`。正确做法是新增 `LLMGateway` 层：

```text
RepoHarness runtime
  -> LLMGateway.generate_turn(...)
    -> VerlLLMGateway
      -> verl LLMServerClient.generate(...)
```

同一个 `LLMGateway` 抽象未来还可以支持：

```text
OpenAI provider
DeepSeek provider
local vLLM
SGLang
verl
slime 或其他 asynchronous reinforcement learning backend
```

这样 RepoHarness 的软件工程任务、工具、verifier、trajectory 和 export audit 都不会被 verl 绑定死。

### 2.4 训练视图和审计视图必须分离

RepoHarness 的完整 trajectory 是审计视图，不应该直接塞进 verl batch。verl 训练只需要紧凑的训练视图：

```text
prompt_ids
response_ids
response_mask
response_logprobs
reward_score
metrics
extra_fields 中的稳定审计引用
```

完整的 transcript、events、artifact manifest、patch、verifier evidence、reward metadata、run summary 等内容继续保存在 RepoHarness run directory 中，通过稳定引用回指，而不是直接进入模型可见上下文或训练 target。

## 3. verl 当前接口事实

### 3.1 自定义 Agent Loop 的注册方式

当前 verl 支持通过 `actor_rollout_ref.rollout.agent.agent_loop_config_path` 加载自定义 Agent Loop 配置。相关配置位于 `reference/verl/verl/trainer/config/rollout/rollout.yaml`：

```text
agent:
  num_workers: 8
  default_agent_loop: single_turn_agent
  agent_loop_config_path: null
```

配置注释中给出的形式是 Hydra instantiate 风格：

```yaml
- name: react_agent
  _target_: recipe.langgraph_agent.react_agent_loop.ReactAgentLoop
```

因此 RepoHarness 第一版应该提供一个可被 Hydra instantiate 的 `RepoHarnessVerlAgentLoop` 类，并通过一个 verl agent loop config 文件注册名称，例如 `repo_harness_agent`。

### 3.2 AgentLoopBase 的构造参数

当前 verl `AgentLoopBase.__init__(...)` 接收以下关键对象：

```text
trainer_config
server_manager
tokenizer
processor
dataset_cls
data_config
```

其中 `server_manager` 的实际类型是 `LLMServerClient`，它是 RepoHarness 的 `VerlLLMGateway` 应该包装的对象。`RepoHarnessVerlAgentLoop` 不应该自己启动或管理 LLM server。

### 3.3 AgentLoopBase.run(...) 的输入和输出

当前 verl 自定义 Agent Loop 需要实现：

```python
async def run(self, sampling_params: dict[str, Any], **kwargs) -> AgentLoopOutput:
    ...
```

`kwargs` 来自数据集样本的 non-tensor 字段，例如内置 `SingleTurnAgentLoop` 读取 `kwargs["raw_prompt"]`。RepoHarness 需要把自己的任务引用、run config 引用、workspace 策略、scaffold 选择、预算等信息放入 verl dataset 的 non-tensor 字段中，再由 `RepoHarnessVerlAgentLoop.run(...)` 解析。

这里必须提前设置硬边界：verl 的 non-tensor 字段会从 dataset 传入 `run(...)`，部分字段还可能在 worker 后处理或 output `extra_fields` 中继续传播。因此，RepoHarness 放入 verl dataset non-tensor 字段的内容只能是模型可见 prompt、任务引用、run config 引用、workspace 策略引用、预算、seed、split、tags 等非隐藏信息。隐藏测试、gold patch、final verifier hidden output、baseline evaluator-only logs、reward-only metadata 和 accepted / failed 标签不能直接放入这些字段；它们只能保存在 RepoHarness audit artifacts 中，并通过短的稳定引用回指。

`AgentLoopOutput` 的核心字段是：

```text
prompt_ids: list[int]
response_ids: list[int]
response_mask: list[int]
response_logprobs: Optional[list[float]]
routed_experts: Optional[Any]
multi_modal_data: Optional[dict[str, Any]]
reward_score: Optional[float]
num_turns: int
metrics: AgentLoopMetrics 或兼容 dict
extra_fields: dict[str, Any]
```

其中：

```text
response_ids:
  包含模型生成 token，也包含工具 observation token。

response_mask:
  对模型生成 token 填 1。
  对工具 observation token 和 padding 填 0。

response_logprobs:
  如果启用 rollout log probability，应与 response_ids 对齐。
  对工具 observation token 可以按 verl ToolAgentLoop 的做法填 0.0。
  对未启用 log probability 的调试路径可以为 None，但正式 PPO/GRPO online training 不应长期依赖 None。

reward_score:
  可以承载 RepoHarness final verifier 派生的标量 reward。
  不能承载会泄漏隐藏测试、gold patch 或 evaluator-only metadata 的文本。

routed_experts / multi_modal_data:
  当前 verl schema 中存在这些可选字段。
  第一版 RepoHarness 文本软件工程任务可以先设为 None。
  adapter 不能删除或破坏这些字段的 schema 兼容性；后续如果支持多模态工具或 MoE 路由审计，再按 verl 当前接口透传。
```

### 3.4 AgentLoopWorker 的职责

verl `AgentLoopWorker` 是调度层，不是 RepoHarness 应该继承的业务层。它负责：

```text
从 batch 中取出每条样本的 non-tensor 字段。
根据 agent_name 找到已注册 Agent Loop config。
Hydra instantiate 自定义 AgentLoopBase。
调用 agent_loop.run(sampling_params, **kwargs)。
将 AgentLoopOutput padding 和后处理成 DataProto。
```

RepoHarness 不应该第一版就改造 `AgentLoopWorker`。只有当后续需要非常特殊的 batch 后处理或 partial rollout 状态处理时，才考虑自定义 `agent_loop_manager_class` 或 worker class。

这也意味着 RepoHarness 不能依赖“worker 后处理会替我们清理敏感字段”。所有进入 verl non-tensor batch、`kwargs` 或 `extra_fields` 的内容都应先经过 RepoHarness 自己的 visibility policy 和 export/audit denylist 检查。

### 3.5 LLMServerClient 与 TokenOutput

当前 verl `LLMServerClient.generate(...)` 的关键调用形态是：

```python
output = await llm_client.generate(
    request_id=request_id,
    prompt_ids=prompt_ids,
    sampling_params=sampling_params,
    image_data=image_data,
    video_data=video_data,
)
```

返回对象是 `TokenOutput`，关键字段包括：

```text
token_ids: list[int]
log_probs: Optional[list[float]]
routed_experts: Optional[Any]
stop_reason: Optional[str]
num_preempted: Optional[int]
extra_fields: dict[str, Any]
```

vLLM 和 SGLang backend 都会在各自 server 中填充 token ids，并在启用配置时返回 log probability。fully async 的 `FullyLLMServerClient` 还会在 `extra_fields` 中维护 `global_steps`、`min_global_steps`、`max_global_steps` 等参数版本信息，用于分析 staleness。

### 3.6 fully async 的关键差异

fully async 模式不是换一个 `AgentLoopBase.run(...)` 就结束，而是引入：

```text
FullyAsyncRollouter
MessageQueue
FullyAsyncTrainer
参数同步流程
FullyLLMServerClient
partial rollout cancellation / resume
```

注意，当前 `reference/verl` 中没有名为 `ParameterSynchronizer` 的真实类。fully async 的参数同步流程主要体现在 `FullyAsyncTrainer.set_rollouter(...)` 建立 trainer 到 rollouter 的引用、`CheckpointEngineManager` 管理权重同步、`FullyAsyncTrainer._fit_update_weights(...)` 调用 `checkpoint_manager.update_weights(...)`，以及同步后调用 `rollouter.reset_staleness(...)` 更新 rollout 侧 staleness 状态。文档后续提到“参数同步”时，指的是这一组流程，而不是一个固定类名。

在 fully async 中：

```text
pending_queue:
  FullyAsyncRollouter 内部的待生成样本队列。

MessageQueue:
  Rollouter 和 Trainer 之间的 Ray Actor 队列，存放已经完成的 rollout sample。

FullyLLMServerClient:
  让 partial rollout 的中断和恢复尽量对 Agent Loop 透明。
```

RepoHarness 第一版不直接实现这些 fully async 能力，但实施计划必须预留 `episode_id`、`policy_version`、`partial_state_ref`、`cancellation`、`resume` 等字段和边界，否则后续会难以扩展。

## 4. RepoHarness 当前接口事实

### 4.1 当前 ModelClient 是同步 provider 抽象

当前 RepoHarness 的 `ModelClient` 协议位于 `src/repo_harness/model_client/protocol.py`：

```python
class ModelClient(Protocol):
    def generate(self, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        ...
```

当前 `ModelResponse` 主要面向 provider response、assistant message、tool calls、usage、finish reason 和 artifact 记录。它适合 OpenAI、DeepSeek、mock、replay 等 provider 路径，但不直接保存训练所需的 token-in-token-out 事实，例如：

```text
prompt_ids
output_token_ids
per-token log probability
policy version
response_mask 对齐信息
```

因此，接入 verl 时不建议直接把 `LLMServerClient` 塞进现有 `ModelClient`，而应该新增 `LLMGateway`，再用兼容 adapter 连接现有 `ModelClient`。

### 4.2 当前 AgentLoop 是同步 loop

当前 RepoHarness `AgentLoop.run(...)` 位于 `src/repo_harness/agent_loop/loop.py`。它做的事情包括：

```text
维护 messages 和 AgentLoopState。
调用 ContextManager.prepare_messages(...)。
构造 ModelRequestContext。
调用 self.model_client.generate(...)。
记录 model_call_started / model_call_completed event。
写入 assistant transcript。
解析 tool calls。
通过 ToolExecutor 执行工具。
把 ToolResult 回填 messages。
根据 final answer、budget、model error、tool limit 等条件停止。
```

这个 loop 当前是同步函数，而 verl `AgentLoopBase.run(...)` 是 async coroutine。第一版实施时有两个可选方向：

```text
方向 A：
  先抽一个 async RepoHarnessRuntime，但内部暂时通过线程执行同步 AgentLoop。
  优点是改动小。
  缺点是 token 级 generation record 和 cancellation 不够自然。

方向 B：
  把 RepoHarness agent loop 的模型生成路径抽成 async-compatible runtime。
  优点是更适合 verl 和后续 fully async。
  缺点是第一版改动更大。
```

建议第一版采用折中方式：先抽 runtime facade 和 LLMGateway 契约，把现有同步 loop 包起来；同时把新建的 verl online RL 路径设计成 async 接口，避免后续再次整体改名。

### 4.3 当前 Eval Runner 包含过多 CLI 级编排

当前 `src/repo_harness/evaluation/runner.py` 的 `run_task(...)` 是完整 CLI 入口级编排，包含：

```text
加载 run config。
加载 task。
创建 workspace adapter。
创建 source checkout / setup workspace / run workspace。
运行 baseline verifier。
构造 ResolvedVerifierPlan。
构造初始 context。
运行 AgentLoop。
运行 final verifier。
计算 reward metadata。
写 run summary、metrics、artifacts。
```

`RepoHarnessVerlAgentLoop.run(...)` 不应该直接粗暴调用当前 `run_task(...)`。原因是 `run_task(...)` 绑定 CLI config、输出目录、provider config、baseline 策略和一次性运行语义，不适合作为 Ray worker 内的可组合 episode runtime。

正确做法是逐步从 `run_task(...)` 中抽出可复用的 runtime facade：

```text
RepoHarnessRuntime.run_episode(...)
  输入：已解析任务、运行策略、workspace 策略、llm_gateway、recorder、预算。
  输出：EpisodeResult，包含 training_view 和 audit_view_ref。
```

CLI `run_task(...)` 后续也可以调用这个 runtime facade，从而减少重复逻辑。

### 4.4 当前 trajectory 和 export 已有审计边界

当前 RepoHarness 的 trajectory schema 已经区分：

```text
TranscriptRecord.model_visible
TranscriptRecord.trainable
TrajectoryEvent
ArtifactRef
RunSummary
MetricsRecord
```

当前 RL export 也已经使用 `reward.json` 中的 `final_reward`，并通过 export audit 检查 hidden / reward-only 字段不能进入训练数据。verl online RL 接入必须继承这个边界，而不是绕过它。

关键要求是：

```text
final verifier output 不进入 model-visible messages。
reward scalar 不进入 prompt、assistant target 或 tool observation 文本。
hidden tests、gold patch、baseline evaluator-only facts 不进入模型可见上下文。
训练 batch 只拿 reward_score 和稳定 audit ref。
完整 reward metadata 留在 RepoHarness audit artifacts 中。
```

## 5. 目标架构

第一版目标架构采用 Thin Adapter Mode：

```text
verl trainer
  -> AgentLoopManager.generate_sequences(...)
    -> AgentLoopWorker._run_agent_loop(...)
      -> RepoHarnessVerlAgentLoop.run(...)
        -> RepoHarnessEpisodeRequest.from_verl_kwargs(...)
        -> VerlLLMGateway(llm_client=self.server_manager, tokenizer=self.tokenizer)
        -> RepoHarnessRuntime.run_episode(...)
          -> ContextBuilder / ContextManager
          -> AgentLoop / ToolExecutor / WorkspaceAdapter
          -> FinalVerifier / RewardMetadata / RunRecorder
          -> GenerationRecord list
        -> EpisodeResult.to_verl_agent_loop_output()
```

### 5.1 Thin Adapter Mode 的运行前提和风险

这个架构意味着 RepoHarness runtime 会在 verl 的 Ray `AgentLoopWorker` 进程中执行。因此，第一版实现前必须确认运行环境满足下面条件：

```text
Python import:
  Ray worker 进程能 import RepoHarness core 包和可选的 repo_harness_verl adapter。

Python dependencies:
  Ray worker 环境具备 RepoHarness 执行任务所需的依赖，例如 pydantic、pytest、git、patch 相关工具和 provider / gateway 依赖。

task data:
  Ray worker 能访问 RepoHarness task yaml/json、预冻结任务索引、source archive、repo cache 或对象存储引用。

run directory:
  Ray worker 有可写的 run output root，并且每条 episode 使用唯一 episode_id / run_id，不能多个 rollout 并发写同一个目录。

workspace:
  每条 episode 使用隔离 workspace。使用 local process mode 时要隔离工作目录；使用 Docker-based executable repository environment 时，worker 所在机器必须能访问 Docker daemon，并具备创建容器、挂载 workspace 和清理容器所需权限。

artifact volume:
  RepoHarness audit artifacts、transcript、events、reward metadata 和 final patch 必须写入训练后还能读取的位置。
```

这些前提不满足时，问题会表现为 Ray worker import 失败、任务文件找不到、workspace 冲突、Docker 权限失败、artifact 丢失或者多个 episode 的审计轨迹互相污染。第一版 smoke run 应该先验证这些运行前提，而不是直接进入大规模训练。

这个架构里，新增代码可以按三个包组织：

```text
src/repo_harness/llm_gateway/
  RepoHarness 自己的 LLMGateway 抽象和 provider adapter。

src/repo_harness/rl/
  EpisodeRequest、EpisodeResult、TrainingView、GenerationRecord、
  verl/slime 等训练后端无关的数据契约。

src/repo_harness_verl/
  只依赖 verl 的薄适配包，包含 RepoHarnessVerlAgentLoop 和 VerlLLMGateway。
```

是否创建独立 `repo_harness_verl` 包可以在实现时根据依赖管理决定。如果不想让主包硬依赖 verl，也可以把 verl adapter 放在 `integrations/verl/` 或 extras dependency 下。原则是：RepoHarness core 不应该因为安装普通 CLI 就必须安装 verl 的完整训练依赖。

## 6. 分阶段实施路线

### 6.1 Stage 0：冻结 verl 参考版本和设计输入

目标：让后续实现有明确的源码依据，不再依赖口头记忆。

已经完成的动作：

```text
git submodule add https://github.com/verl-project/verl.git reference/verl
```

后续需要补齐的动作：

```text
1. 在文档中记录 reference/verl 的 commit：f400fb7654b217632323b906f86e345e201fb736。
2. 增加一个简短的 reference/verl 阅读索引。
3. 明确“本文档基于该 commit，升级 verl 时必须重新核对接口”。
4. 不把 reference/verl 当成 RepoHarness runtime dependency。
```

建议新增或更新：

```text
docs/agentic_RL/repo_harness_verl_detailed_implementation_plan.md
docs/agentic_RL/verl_source_reading_notes.md
```

验收方式：

```text
git submodule status reference/verl
git -C reference/verl rev-parse HEAD
```

并人工核对 `.gitmodules` 中路径和远端正确。

### 6.2 Stage 1：新增训练后端无关的 RL episode 契约

目标：先在 RepoHarness 内部定义和 verl 无关的数据契约，避免后续所有逻辑都围绕 verl 类型展开。

建议新增模块：

```text
src/repo_harness/rl/
  __init__.py
  schemas.py
  episode.py
  training_view.py
```

建议定义的核心概念：

```text
RepoHarnessEpisodeRequest:
  一条软件工程 episode 的输入。
  包含 task ref、run config ref、workspace policy、scaffold、预算、seed、dataset metadata。

GenerationRequest:
  RepoHarness runtime 请求模型生成的输入。
  包含 episode_id、turn_id、prompt_ids、sampling_params、tool schema、context revision。

GenerationRecord:
  一次模型生成的 token-level 事实。
  包含 prompt_ids、output_token_ids、output_text、logprobs、stop_reason、provider metadata、policy version metadata。

RepoHarnessTrainingView:
  训练侧紧凑视图。
  包含 prompt_ids、response_ids、response_mask、response_logprobs、reward_score、num_turns、metrics、audit_refs。

RepoHarnessAuditViewRef:
  指向 RepoHarness run directory、artifact manifest、reward metadata、verifier result 和 summary 的稳定引用。

RepoHarnessEpisodeResult:
  runtime 输出。
  包含 training_view、audit_view_ref、run_outcome、invalid_for_training、invalid_reason。
```

重要边界：

```text
RepoHarnessTrainingView 可以转换成 verl AgentLoopOutput。
RepoHarnessAuditViewRef 只做回指，不直接进入模型上下文。
GenerationRecord 记录 token ids 和 logprobs，不代替 transcript。
```

这一阶段不应该引入 verl import。`repo_harness/rl` 应该是训练后端无关层，将来可以被 slime 或其他后端复用。

建议测试：

```text
tests/unit/test_rl_episode_schemas.py
```

测试重点：

```text
response_ids 与 response_mask 等长。
response_logprobs 如果不为 None，长度必须等于 response_ids。
reward_score 在允许范围内，或者明确允许 None。
audit refs 不包含模型可见文本。
invalid_for_training=true 时必须有 invalid_reason。
```

### 6.3 Stage 2：新增 LLMGateway 抽象

目标：把 RepoHarness 的“模型生成”从 provider response 抽象升级为可以承载 token-in-token-out 的 generation 抽象。

建议新增模块：

```text
src/repo_harness/llm_gateway/
  __init__.py
  protocol.py
  schemas.py
  model_client_adapter.py
  replay_gateway.py
  mock_gateway.py
```

建议协议：

```python
class LLMGateway(Protocol):
    async def generate_turn(
        self,
        request: GenerationRequest,
        recorder: RunRecorder,
    ) -> GenerationRecord:
        ...
```

为什么用 async：

```text
verl AgentLoopBase.run(...) 是 async。
fully async 和 partial rollout 需要 cancellation。
slime 等轻量异步训练后端也更适合 async 接口。
```

与当前 `ModelClient` 的关系：

```text
当前 ModelClient:
  面向 OpenAI、DeepSeek、replay、mock provider。
  输出 ModelResponse。
  适合当前 CLI 评测和离线运行。

新增 LLMGateway:
  面向 token-level rollout。
  输出 GenerationRecord。
  适合 online reinforcement learning 和后续异步训练。
```

第一版不要删除 `ModelClient`。建议先做 adapter：

```text
ModelClientGateway:
  包装现有 ModelClient。
  用于普通 provider 路径兼容。
  如果 provider 没有 token ids / logprobs，就记录 token_level_status="text_only"。
  text_only 路径可以用于 debug 或离线轨迹，不作为 verl online RL 的正式训练路径。
```

`LLMGateway` 的最关键约束：

```text
1. 正式 verl online RL 路径必须能返回真实 output_token_ids。
2. 如果启用 PPO/GRPO 训练所需的 rollout log probabilities，必须返回与 output_token_ids 对齐的 logprobs。
3. Gateway 不解析工具调用，只返回模型生成事实。
4. Gateway 不写 reward，不运行 verifier。
5. Gateway 不把 raw provider secret 或 hidden evaluator metadata 写入模型可见消息。
```

建议测试：

```text
tests/unit/test_llm_gateway_schemas.py
tests/unit/test_model_client_gateway.py
```

测试重点：

```text
GenerationRecord 长度校验。
text_only provider 路径不能被标记为 token_level_trainable。
raw request / raw response artifact 的 redaction status 保持现有策略。
Gateway 不接受 reward metadata 字段作为输入。
```

### 6.4 Stage 3：抽出 RepoHarnessRuntime facade

目标：把当前 `evaluation/runner.py::run_task(...)` 中可复用的 episode 执行逻辑抽出来，供 CLI 和 verl adapter 共同调用。

建议新增模块：

```text
src/repo_harness/runtime/
  __init__.py
  episode_runtime.py
  request_builder.py
  result_builder.py
```

建议形态：

```python
class RepoHarnessRuntime:
    async def run_episode(
        self,
        request: RepoHarnessEpisodeRequest,
        llm_gateway: LLMGateway,
        recorder: RunRecorder,
    ) -> RepoHarnessEpisodeResult:
        ...
```

第一版可以内部复用当前同步组件：

```text
ContextBuilder
ContextManager
AgentLoop
ToolExecutor
WorkspaceAdapter
PytestVerifier
RewardMetadata calculator
RunRecorder
```

但需要把下面几类逻辑从 CLI 级 runner 中分离出来：

```text
任务解析和 runtime request 构造。
workspace materialization。
baseline verifier 和 final verifier 的策略。
agent loop 执行。
reward metadata 计算。
training_view 构造。
audit_view_ref 构造。
```

不要在 `RepoHarnessVerlAgentLoop.run(...)` 中直接调用当前 `run_task(...)`。`run_task(...)` 是 CLI 操作面，包含很多不适合 Ray worker 内部反复调用的行为，例如默认输出目录、run id 生成、config path 加载、异常处理和命令行验收产物写入。

这一阶段还必须明确 output ownership，也就是谁创建 run directory、谁创建 `RunRecorder`、谁负责 finalize 和 cleanup。建议新增一个小的分配组件：

```text
RunDirectoryAllocator:
  输入 trainer_run_id、task_id、dataset_item_id、global_step、rollout_index、worker_id。
  输出唯一 episode_id、run_id 和 run_dir。

EpisodeOutputPolicy:
  描述 run directory 命名、artifact retention、失败清理、并发冲突处理和 audit manifest 写入策略。

RepoHarnessRuntime:
  只消费已经分配好的 run_id/run_dir/recorder。
  不自己猜测输出目录。

RepoHarnessVerlAgentLoop:
  在进入 runtime 前调用 RunDirectoryAllocator。
  使用 with RunRecorder(...) as recorder 包住 runtime.run_episode(...)。
  确保异常路径也写入结构化 interrupted / failed evidence，或者明确返回 invalid episode。
```

这样做可以避免 Ray worker 并发运行时多个 episode 共写同一个 run directory，也能避免 CLI `run_task(...)` 和 verl rollout 路径各自发明不同的输出目录规则。

阶段性折中方案：

```text
第一步：
  RepoHarnessRuntime 可以先复用现有同步 AgentLoop。
  在 async run_episode 内部通过线程或受控 executor 调用同步部分。

第二步：
  把模型生成调用改为 LLMGateway。
  AgentLoop 内部可先通过同步桥调用 async gateway，但要把接口边界设计成未来可原生 async。

第三步：
  把 AgentLoop 主循环逐步迁移为 async，方便 fully async cancellation。
```

建议测试：

```text
tests/unit/test_runtime_episode_request.py
tests/integration/test_runtime_episode_replay.py
tests/integration/test_runtime_episode_reward_boundary.py
```

测试重点：

```text
同一个 replay 任务通过旧 run_task 和新 runtime facade 得到等价的 run outcome。
final verifier 仍然在 agent 停止后运行。
reward metadata 仍然只来自 final verifier。
baseline / final verifier 不进入 model-visible transcript。
```

### 6.5 Stage 4：构造 token-level training view

目标：让 RepoHarness 能把多轮软件工程 episode 转成 verl 可训练的 `prompt_ids`、`response_ids`、`response_mask` 和 `response_logprobs`。

这是第一版最容易出错的阶段，必须单独实施和测试。

正确构造方式：

```text
初始 prompt:
  使用 verl tokenizer / chat template 得到 prompt_ids。

每次模型生成:
  VerlLLMGateway 返回 output_token_ids。
  这些 token 追加到 response_ids。
  对应 response_mask 追加同长度的 1。
  如果返回 logprobs，则追加到 response_logprobs。
  如果返回 routed_experts，则按 verl schema 保存到 training_view 的可选 routed_experts 字段。

每次工具 observation:
  使用同一个 tokenizer / chat template 策略编码 observation。
  observation token 追加到 response_ids。
  对应 response_mask 追加同长度的 0。
  如果 response_logprobs 已经存在，则对 observation token 追加 0.0 占位。
```

禁止做法：

```text
不要在 episode 结束后把最终 messages 整体重新 apply chat template 来构造训练 token。
不要把工具 observation 标记为 response_mask=1。
不要把 final verifier hidden output 编码进 response_ids。
不要把 reward label 或 accepted/failed 文本写进模型可见 observation。
不要把 stop_reason 当作 token 边界。
```

这一阶段需要处理一个现实问题：当前 RepoHarness 的 provider response 是 message/text/tool-call 抽象，而 verl 训练需要 token-level continuation。建议把第一版 online RL 路径限制为 `VerlLLMGateway`：

```text
offline provider / replay:
  可以继续用于审计轨迹和调试。
  不承诺 token-level trainable。

verl online RL:
  必须使用 token-in-token-out。
  必须由 GenerationRecord 提供 output_token_ids。
```

建议测试：

```text
tests/unit/test_training_view_token_alignment.py
tests/unit/test_training_view_masks.py
tests/unit/test_training_view_no_final_verifier_leakage.py
```

测试样例应覆盖：

```text
单轮 final answer。
一轮工具调用加一轮 final answer。
工具 observation 很长时发生 deterministic truncation。
模型生成 logprobs 存在。
模型生成 logprobs 不存在但只是 debug path。
routed_experts 存在时可以从 GenerationRecord 透传到 TrainingView。
final verifier accepted 与 failed 两种结果。
```

### 6.6 Stage 5：实现 VerlLLMGateway

目标：把 RepoHarness `GenerationRequest` 转成当前 verl `LLMServerClient.generate(...)`，并把 `TokenOutput` 转回 `GenerationRecord`。

建议放置：

```text
src/repo_harness_verl/
  __init__.py
  gateway.py
  schemas.py
```

如果不想新增顶层包，也可以放在：

```text
src/repo_harness/integrations/verl/
```

建议职责：

```text
1. 保存 verl 注入的 llm_client 和 tokenizer。
2. 使用 episode_id 作为 request_id，保证 sticky session。
3. 转发 prompt_ids、sampling_params、image_data、video_data。
4. 接收 TokenOutput.token_ids。
5. 接收 TokenOutput.log_probs。
6. 接收 TokenOutput.routed_experts。
7. 接收 TokenOutput.stop_reason、num_preempted、extra_fields。
8. 解码 token_ids 得到 output_text，供 RepoHarness tool parser 使用。
9. 把 raw stop reason 和规范化 stop reason 记录到审计元数据。
10. 不运行工具，不计算 reward，不修改 workspace。
```

关键字段边界：

```text
TokenOutput.token_ids:
  只表示新生成 response token，不包含 prompt token。

TokenOutput.log_probs:
  只与 token_ids 对齐。
  如果为 None，不要伪造。
  如果为 [] 且 token_ids 非空，说明当前路径没有实际返回 log probability；在非强制 logprob 的 debug 路径中应规范化为 None。
  如果配置要求 rollout log probability，则 [] 或 None 都应视为不可训练错误。
  如果 log_probs 非空但长度不等于 token_ids，则报错。

TokenOutput.routed_experts:
  当前 verl schema 支持该可选字段。
  第一版可以透传到 GenerationRecord 和 TrainingView。
  如果暂时不支持 MoE routing replay，必须显式记录 unsupported_routed_experts，而不是静默丢弃。

TokenOutput.stop_reason:
  只进入 audit metadata。
  不进入 training batch 的核心张量字段。

TokenOutput.extra_fields.global_steps:
  可作为 policy_version 或 rollout_param_version 记录。
  普通非 fully async 路径可能没有该字段，必须允许缺省。
```

建议伪代码：

```python
class VerlLLMGateway:
    def __init__(self, *, llm_client, tokenizer):
        self.llm_client = llm_client
        self.tokenizer = tokenizer

    async def generate_turn(self, request, recorder):
        output = await self.llm_client.generate(
            request_id=request.episode_id,
            prompt_ids=request.prompt_ids,
            sampling_params=request.sampling_params,
            image_data=request.image_data,
            video_data=request.video_data,
        )

        token_ids = output.token_ids
        log_probs = normalize_log_probs(
            output.log_probs,
            token_ids=token_ids,
            require_log_probs=request.require_log_probs,
        )
        text = self.tokenizer.decode(token_ids, skip_special_tokens=False)

        return GenerationRecord(
            episode_id=request.episode_id,
            turn_id=request.turn_id,
            prompt_ids=request.prompt_ids,
            output_token_ids=token_ids,
            output_text=text,
            logprobs=log_probs,
            routed_experts=output.routed_experts,
            raw_stop_reason=output.stop_reason,
            normalized_stop_reason=normalize_stop_reason(output.stop_reason),
            num_preempted=output.num_preempted,
            policy_version=output.extra_fields.get("global_steps"),
            min_policy_version=output.extra_fields.get("min_global_steps"),
            max_policy_version=output.extra_fields.get("max_global_steps"),
        )
```

建议测试：

```text
tests/unit/test_verl_llm_gateway.py
```

使用 fake `LLMServerClient`，不启动 Ray 和 vLLM：

```text
fake client 返回 TokenOutput(token_ids=[...], log_probs=[...]).
fake client 返回 TokenOutput(token_ids=[...], log_probs=[]) 时，非强制 logprob 路径规范化为 None。
fake client 返回 TokenOutput(token_ids=[...], log_probs=[]) 且 require_log_probs=true 时，样本不可训练或报结构化错误。
fake client 返回 routed_experts 时可以透传。
确认 GenerationRecord 字段正确。
确认 request_id 使用 episode_id。
确认非空 log_probs 长度不匹配时报错。
确认 stop_reason 只进入 metadata。
```

### 6.7 Stage 6：实现 RepoHarnessVerlAgentLoop

目标：让 verl 可以通过自定义 `AgentLoopBase` 调用 RepoHarness runtime，并返回标准 `AgentLoopOutput`。

建议放置：

```text
src/repo_harness_verl/agent_loop.py
```

建议类形态：

```python
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    async def run(self, sampling_params: dict[str, Any], **kwargs) -> AgentLoopOutput:
        episode_request = RepoHarnessEpisodeRequest.from_verl_kwargs(
            kwargs,
            sampling_params=sampling_params,
            trainer_config=self.config,
            tokenizer_info=...,
        )
        gateway = VerlLLMGateway(
            llm_client=self.server_manager,
            tokenizer=self.tokenizer,
        )
        output_allocation = self.run_directory_allocator.allocate(episode_request)
        with RunRecorder(
            run_id=output_allocation.run_id,
            run_dir=output_allocation.run_dir,
            task_id=episode_request.task_id,
        ) as recorder:
            result = await self.runtime.run_episode(
                episode_request,
                llm_gateway=gateway,
                recorder=recorder,
            )
        return to_verl_agent_loop_output(result.training_view)
```

第一版需要支持的 `kwargs` 建议包括：

```text
agent_name:
  verl 用于选择 RepoHarnessVerlAgentLoop。

raw_prompt:
  verl 数据集默认字段，可以保留用于兼容。

extra_info:
  RepoHarness 第一版建议从 kwargs["extra_info"] 读取 task ref、run config ref、dataset item id、split、source、difficulty、tags 等非隐藏信息。
  原因是当前 verl 的 RLHFDataset 会保留 extra_info 字典，但不会自动把 extra_info 展平成顶层 kwargs。
  如果后续自定义 dataset adapter 决定把字段放在顶层，也必须提供兼容测试，不能让 Stage 6 和 Stage 7 的字段位置不一致。
```

不要把下面内容放进模型可见字段：

```text
gold_patch
hidden tests
final verifier expected output
reward scalar
accepted label
baseline hidden logs
```

`to_verl_agent_loop_output(...)` 的职责：

```text
1. 复制 training_view.prompt_ids。
2. 复制 training_view.response_ids。
3. 复制 training_view.response_mask。
4. 如果有 response_logprobs，则复制。
5. 如果有 routed_experts，则复制或显式记录不支持原因。
6. 填 reward_score，但只有 valid trainable episode 才填。
7. 填 num_turns。
8. 填 metrics。
9. 在 extra_fields 中放 audit refs、run_id、task_id、invalid_for_training、invalid_reason。
```

注意：`extra_fields` 会进入 verl 的 non-tensor batch 后处理路径，不能无限膨胀。完整审计信息只放 RepoHarness run directory；`extra_fields` 只放短引用和必要训练过滤信息。

还要注意，当前 verl 不会因为 `extra_fields.invalid_for_training=true` 自动过滤样本。`AgentLoopOutput.reward_score` 会在后处理中转成 `rm_scores`，但 invalid flag 本身只是 non-tensor metadata。因此第一版必须选择一个明确策略：

```text
策略 A：
  invalid episode 不填 reward_score，并在 adapter 或 trainer 前过滤这些样本。

策略 B：
  自定义 AgentLoopManager / trainer 前处理，读取 invalid_for_training 并过滤。

策略 C：
  在 smoke 阶段禁止产生 invalid episode，任何 invalid 都让 run fail fast。
```

推荐第一版先采用策略 C 做 smoke，随后实现策略 A 或 B。不能只把 invalid flag 放进 extra_fields 就假设 verl 会自动跳过训练。

建议配置文件：

```yaml
- name: repo_harness_agent
  _target_: repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop
  runtime_profile: online_rl_v0
```

verl 侧 rollout 配置需要：

```text
actor_rollout_ref.rollout.agent.agent_loop_config_path=...
actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness_agent
actor_rollout_ref.rollout.mode=async
actor_rollout_ref.rollout.calculate_log_probs=True
```

最后一项是否必须取决于具体训练算法和配置，但如果要在训练中直接使用 rollout 阶段 log probability，就必须启用并验证返回字段。

建议测试：

```text
tests/unit/test_repo_harness_verl_agent_loop_output.py
tests/integration/test_repo_harness_verl_agent_loop_fake_client.py
```

第一版可以用 fake verl client 和 tiny task，不需要启动完整 verl trainer。

### 6.8 Stage 7：构造 verl 数据集适配层

目标：让 verl dataloader 能把软件工程任务样本传给 `RepoHarnessVerlAgentLoop.run(...)`。

建议新增：

```text
src/repo_harness_verl/dataset.py
docs/agentic_RL/examples/repo_harness_verl_agent_loop_config.yaml
docs/agentic_RL/examples/repo_harness_verl_dataset_example.jsonl
```

最小 dataset row 可以包含：

```json
{
  "data_source": "repo_harness",
  "prompt": [{"role": "user", "content": "模型可见的任务摘要和必要上下文预览"}],
  "agent_name": "repo_harness_agent",
  "ability": "software_engineering",
  "extra_info": {
    "repo_harness_task_ref": "tasks/...",
    "repo_harness_run_config_ref": "configs/...",
    "dataset_item_id": "..."
  }
}
```

这里的 `prompt` 不应该只是无意义占位。虽然真正任务加载以 `extra_info.repo_harness_task_ref` 为准，但 verl dataloader 的长度过滤和 batch 构造会先看到 dataset row 中的 prompt。如果 prompt 只是短占位，可能绕过 verl 的 prompt length filter，等 RepoHarness runtime 构造真实初始上下文后才发现 `prompt_ids` 超过 `rollout_config.prompt_length`。

因此 Stage 7 需要提供一个实际 prompt 预估或预构造步骤：

```text
1. 读取 RepoHarness task。
2. 按 online RL runtime profile 构造模型可见 issue summary 和上下文预览。
3. 使用与 verl 训练一致的 tokenizer / chat template 估算 prompt_ids 长度。
4. 如果超过 rollout_config.prompt_length，提前过滤或降级为 invalid task。
5. dataset row 中仍然不能包含 hidden tests、gold patch、reward 或 final verifier facts。
```

需要决策的点：

```text
任务内容是否重复放在 raw_prompt 中：
  可以放模型可见 issue summary。
  不能放 hidden evaluator facts。

RepoHarness task yaml 是否由 Ray worker 直接读取：
  第一版可以读取本地路径。
  后续分布式集群需要共享文件系统或对象存储。

workspace 输出目录如何命名：
  应由 episode_id / task_id / global step / rollout index 组成，避免 Ray worker 并发冲突。
```

建议测试：

```text
tests/unit/test_verl_dataset_adapter.py
```

测试重点：

```text
dataset row 可以生成 verl 需要的 raw_prompt 和 non_tensor fields。
RepoHarnessEpisodeRequest.from_verl_kwargs(...) 能从 kwargs["extra_info"] 读取 task ref 和 run config ref。
hidden fields 被拒绝或只进入 verifier_only metadata。
agent_name 正确设置。
真实 prompt 预估长度不超过 rollout_config.prompt_length。
task_ref 不存在时报出结构化错误。
```

### 6.9 Stage 8：最小 smoke run

目标：在不追求训练效果的前提下，验证 verl 可以调用 RepoHarness episode 并收到可训练输出。

建议 smoke 层级：

```text
Level 1:
  不启动 verl trainer。
  直接实例化 RepoHarnessVerlAgentLoop，使用 fake LLMServerClient。

Level 2:
  启动 verl AgentLoopManager，但使用 fake / tiny rollout server。
  验证 DataProto 字段。

Level 3:
  启动最小 verl PPO/GRPO 配置，小模型，小数据，1-2 个 step。
  验证 trainer 能消费 RepoHarness AgentLoopOutput。
```

每一层必须检查：

```text
prompt_ids 非空。
len(prompt_ids) <= rollout_config.prompt_length。
response_ids 非空或有明确 invalid reason。
len(response_ids) <= rollout_config.response_length。
response_mask 长度等于 response_ids。
response_mask 至少包含模型生成 token 的 1。
工具 observation token 为 0。
calculate_log_probs=True 时，rollout_log_probs 存在且与 response_ids 对齐；工具 observation token 对应 0.0 或明确 mask 掉。
有效样本的 reward_score 来自 final verifier，并能在 verl 后处理中形成 rm_scores。
无效样本不会进入有效 PPO/GRPO reward batch，或者 smoke 阶段直接 fail fast。
extra_fields / non_tensor_batch 中只有短引用和必要 metadata，没有大段隐藏内容。
并发运行两个相同 task 不会 run directory 冲突。
final verifier、reward scalar、hidden tests、gold patch 不进入模型可见 token。
RepoHarness run directory 存在。
audit manifest 可以 inspect。
```

如果 Level 3 环境成本较高，可以先把它做成手动 smoke 命令，不纳入默认单元测试。但文档和脚本要清楚说明依赖 GPU、模型和 verl 安装。

## 7. fully async 演进计划

第一版 Thin Adapter Mode 跑通后，RepoHarness 必须继续向异步架构演进。原因是软件工程任务天然长尾：有的任务几轮工具调用完成，有的任务会卡在依赖安装、测试运行、长日志、反复修改和超时上。如果长期使用同步 batch rollout，训练吞吐会被最慢样本拖住。

### 7.1 Async Stage A：普通 async episode runtime

目标：先让 RepoHarness runtime 自身具备 async 形态，但不接入 partial rollout。

需要改造：

```text
AgentLoop 主循环支持 async。
LLMGateway 原生 async。
ToolExecutor 可以保留同步执行，但通过受控 executor 调用。
Workspace command execution 可以先同步，后续再异步化。
RunRecorder 写入仍保持顺序一致和可审计。
```

验收点：

```text
同一条 episode 在同步兼容路径和 async 路径下，模型可见 transcript 等价。
token provenance 不丢失。
tool call / tool result 配对不乱序。
```

### 7.2 Async Stage B：接入 verl FullyAsyncRollouter

目标：让 RepoHarness episode 可以作为 fully async rollout sample 被 `FullyAsyncRollouter` 持续生产，并通过 `MessageQueue` 交给 `FullyAsyncTrainer`。

关键理解：

```text
pending_queue:
  FullyAsyncRollouter 内部队列，存放等待执行的样本。

active_tasks:
  正在执行的 RepoHarness episode coroutine。

MessageQueue:
  Rollouter 和 Trainer 之间的队列，只放已完成并可训练的 RolloutSample。
```

RepoHarness 需要满足：

```text
episode 结束前不把样本交给 MessageQueue。
invalid episode 要有 invalid_reason。
超时、workspace failure、verifier failure 要生成结构化 training filter 信息。
extra_fields 中提供 run_id、task_id、audit_manifest_ref、invalid_for_training。
```

这阶段仍然可以不启用 `partial_rollout`，先接受参数 staleness 受阈值控制。

### 7.3 Async Stage C：支持 pause / cancellation / resume

目标：让 RepoHarness 能在 parameter sync 或 queue backpressure 时中断长 episode，并在之后恢复。

软件工程 episode 的 partial state 比 search agent 更复杂，至少需要保存：

```text
workspace state:
  当前 run workspace 或可恢复 patch / snapshot。

tool state:
  正在执行的命令状态、超时状态、工具输出截断状态。

agent loop state:
  messages、turn_count、scaffold_phase、budget_state、context_revision。

token state:
  prompt_ids、response_ids、response_mask、response_logprobs、每轮 GenerationRecord。

recorder state:
  已写入 transcript/events/artifacts 的位置和幂等 key。

verifier state:
  中间 feedback verifier 可以保存。
  final verifier 只能在 episode terminal 后运行。

policy version state:
  generation record 中的 global_steps、min_global_steps、max_global_steps 或等价字段。
```

这一阶段不能只保存 Python object，因为 Ray worker 重启、进程崩溃或长任务迁移都可能发生。应该把 partial state 保存为 RepoHarness artifact 或 checkpoint，并通过 `partial_state_ref` 引用。

### 7.4 Async Stage D：partial rollout 训练语义

目标：在启用 verl `partial_rollout=true` 后，RepoHarness 返回的部分结果不会污染训练 batch。

规则：

```text
partial output 只能用于恢复，不是可训练样本。
被中断但未完成 final verifier 的 episode 不能产生 final reward。
恢复后继续追加 response_ids、response_mask 和 response_logprobs。
跨参数版本生成的 token 要保留 policy version 范围。
如果 staleness 超过训练策略允许范围，样本应 invalid_for_training 或降权处理。
```

需要与 verl fully async 对齐的字段：

```text
TokenOutput.extra_fields.global_steps
TokenOutput.extra_fields.min_global_steps
TokenOutput.extra_fields.max_global_steps
AgentLoopOutput.metrics.num_preempted
RolloutSample.rollout_status
MessageQueue param version metadata
```

具体字段名要以实现时的 verl commit 为准。

## 8. 与 slime 或其他后端的关系

本计划虽然以 verl 为第一目标，但 `LLMGateway` 和 `RepoHarnessTrainingView` 不应该包含 verl 专属类型。这样后续接 slime 时，可以复用：

```text
RepoHarnessRuntime
LLMGateway protocol
GenerationRecord
TrainingView
AuditViewRef
reward boundary
token provenance
```

需要新增的是 slime 侧 adapter：

```text
SlimeLLMGateway:
  调用 slime 或其推理后端。

SlimeSampleAdapter:
  把 RepoHarnessTrainingView 转成 slime trainer 需要的 sample。

SlimeAsyncSchedulerAdapter:
  如果 slime 暴露自己的异步调度接口，则负责 pending / completed sample 的转换。
```

因此，RepoHarness 的核心抽象要按下面方式分层：

```text
repo_harness/rl:
  backend-neutral contracts

repo_harness/llm_gateway:
  backend-neutral generation protocol

repo_harness_verl:
  verl-specific adapter

repo_harness_slime:
  future slime-specific adapter
```

这样做可以避免当前项目被 verl 的 internal class name、Ray worker lifecycle 或 config 结构锁死。

## 9. 关键风险与规避策略

### 9.1 token 重新编码风险

风险：episode 结束后把最终 messages 重新 apply chat template，会产生和 rollout 实际生成不同的 token 序列。

规避：

```text
只使用 VerlLLMGateway 返回的 output_token_ids 作为模型生成 token。
工具 observation token 在插入当轮时立即编码和记录。
GenerationRecord 绑定 context_revision 和 model_input_hash。
```

### 9.2 response_mask 污染风险

风险：把工具 observation、verifier output、reward label 标成 `response_mask=1`，会让模型学习环境输出或隐藏评测信息。

规避：

```text
模型生成 token 才是 1。
工具 observation token 是 0。
padding 是 0。
final verifier hidden result 不进入 response_ids。
```

### 9.3 reward 泄漏风险

风险：为了让训练方便，把 accepted、failed、reward scalar 或 final verifier summary 写进 prompt 或 tool observation。

规避：

```text
reward_score 只进入 AgentLoopOutput.reward_score。
reward metadata 只进入 audit artifacts。
extra_fields 只放短引用和训练过滤信息。
export audit 增加 online RL record 检查。
```

### 9.4 Ray worker 与 workspace 并发冲突

风险：多个 Ray worker 同时运行 RepoHarness episode，写入同一个 run directory 或 workspace。

规避：

```text
episode_id 必须全局唯一。
run_dir 必须由 trainer run id、global step、sample index、rollout index 共同派生。
workspace materialization 必须隔离。
RunRecorder 不允许多个 episode 共写同一个目录。
```

### 9.5 verl 依赖污染 RepoHarness core

风险：主包一 import 就需要安装 verl、Ray、vLLM、SGLang，导致普通 RepoHarness CLI 难以运行。

规避：

```text
verl adapter 放在独立 integration 包或 optional extra。
RepoHarness core 只依赖 backend-neutral schema。
单元测试中用 fake client，避免默认启动 Ray。
```

### 9.6 fully async checkpoint 不完整

风险：partial rollout 只保存 messages，不保存 workspace、recorder、token、budget 和 policy version，恢复后轨迹不可审计。

规避：

```text
partial_state_ref 必须覆盖 workspace、agent loop、token provenance、recorder position、budget、policy version。
partial output 不能进入训练队列。
恢复后要能继续写同一条 audit trajectory，或者明确开启新 segment 并建立 parent ref。
```

## 10. 验收矩阵

### 10.1 文档和版本验收

```text
reference/verl 是 Git submodule。
.gitmodules 记录 reference/verl。
文档记录 verl commit。
文档列出依赖的 verl 文件和接口。
```

### 10.2 schema 和 gateway 验收

```text
RL episode schema 单元测试通过。
LLMGateway schema 单元测试通过。
VerlLLMGateway fake client 单元测试通过。
GenerationRecord 长度校验覆盖 token_ids/logprobs。
```

### 10.3 runtime 验收

```text
RepoHarnessRuntime 可以跑 replay / fake episode。
runtime 输出 audit_view_ref。
runtime 输出 training_view。
training_view 不包含 hidden evaluator facts。
final verifier 仍在 episode terminal 后运行。
```

### 10.4 verl adapter 验收

```text
RepoHarnessVerlAgentLoop 可以被 Hydra instantiate。
run(...) 返回 AgentLoopOutput。
AgentLoopOutput 字段长度一致。
response_mask 语义正确。
extra_fields 只包含短引用和必要 metadata。
batch 内可选字段一致，例如 `response_logprobs` 和 `routed_experts` 不能只在部分样本存在而没有明确填充或过滤策略，因为 verl 后处理会按 batch 首个样本决定是否拼接这些字段。
```

### 10.5 smoke run 验收

```text
fake LLMServerClient smoke run 通过。
最小 verl AgentLoopManager smoke run 通过。
可选 GPU 环境下最小 PPO/GRPO step 通过。
RepoHarness run directory 和 verl rollout output 可以互相回指。
```

### 10.6 export / audit 验收

```text
新增 online RL export 或 training_view audit。
检查 reward scalar 不进入 prompt/action/observation 文本。
检查 final verifier hidden result 不进入 model-visible transcript。
检查 raw provider response 不进入 training payload。
检查 token provenance 与 GenerationRecord 对齐。
```

## 11. 推荐实现顺序

推荐按下面顺序推进：

```text
1. 保留 reference/verl submodule 和当前详细实施计划。
2. 新增 backend-neutral rl schema。
3. 新增 LLMGateway schema 和 fake gateway。
4. 抽 RepoHarnessRuntime facade，但先复用现有同步 AgentLoop。
5. 实现 token-level TrainingView builder。
6. 实现 VerlLLMGateway fake-client 单元测试。
7. 实现 RepoHarnessVerlAgentLoop fake-client integration test。
8. 编写 verl agent loop config 和 dataset 示例。
9. 跑最小 verl AgentLoopManager smoke。
10. 跑最小 PPO/GRPO smoke。
11. 再开始 fully async 和 partial rollout。
```

不建议的顺序：

```text
一开始就改 FullyAsyncRollouter。
一开始就让 RepoHarness 管 LLMServerManager。
一开始就把 run_task(...) 直接塞进 RepoHarnessVerlAgentLoop。
一开始就把所有 provider 路径迁移到 token-level gateway。
一开始就训练大模型或跑大规模 SWE task。
```

## 12. 第一版完成后的能力边界

第一版完成后，可以合理描述为：

```text
RepoHarness 已经可以作为 verl 自定义 Agent Loop 的软件工程任务 runtime。
verl 可以通过 RepoHarnessVerlAgentLoop 调用 RepoHarness 生成 online RL rollout。
RepoHarness 可以通过 VerlLLMGateway 使用 verl 管理的 LLMServerClient。
训练侧可以消费 token-aligned AgentLoopOutput。
审计侧保留完整 RepoHarness trajectory、verifier evidence 和 reward metadata。
```

仍然不能描述为：

```text
已经完成大规模 agentic RL 系统。
已经完成 fully async SWE rollout service。
已经解决 partial rollout workspace checkpoint。
已经提供生产级分布式沙箱。
已经训练出有效的软件工程模型。
已经复现 SWE-Bench 公开榜单系统。
```

第一版的价值是建立正确的接口和语义闭环。规模化训练、fully async、partial rollout、slime backend、多节点 workspace service 和大规模任务调度，都应该作为后续版本继续推进。
