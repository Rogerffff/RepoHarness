# verl fully_async_policy 与 CaRR DeepSearch 项目回顾

本文档用于回顾 verl 中 `fully_async_policy` 的基础架构，以及它在先前 CaRR DeepSearch 训练项目中的接入方式。重点不是复述所有代码细节，而是帮助重新建立一套清晰的心智模型：为什么需要 fully async、四个核心组件如何协作、样本如何从 Rollouter 进入 Trainer、`partial_rollout` 如何中断和恢复长轨迹，以及 CaRR 项目当时在 Agent Loop 层做了哪些适配。

本文基于本地 CaRR 项目中的 verl 代码快照 `14d71c0e90338b8b655fde980c6aa22be20de98b` 和 CaRR DeepSearch 项目经验复盘编写。`fully_async_policy` 位于 verl 的 experimental 目录，后续官方接口和命名可能变化；阅读新版 verl 时，应以新版代码为准重新核对类名和配置项。

本文是 RepoHarness 接入 verl 的背景材料，重点解释 fully async 和 CaRR 的经验。RepoHarness 未来接入 verl 的正式架构计划见 [repo_harness_verl_architecture_plan.md](repo_harness_verl_architecture_plan.md)。

相关代码路径：

- `verl/experimental/fully_async_policy/`
- `examples/carr_deepsearch/tools/carr_agent_loop.py`
- `examples/carr_deepsearch/config/carr_grpo_async.yaml`

## 0. 术语说明

为避免概念混淆，本文先约定几个术语：

- `fully async`：全异步训练架构，意思是 Rollouter 持续生成样本、Trainer 持续训练，中间通过队列解耦，而不是每一步都等待一整批 rollout 完成。
- `staleness`：样本生成时使用的参数版本落后于 Trainer 当前参数版本的程度。
- `partial rollout`：参数同步或队列反压时，中断正在执行的 rollout，保存中间状态，参数同步后再恢复继续执行。
- `rollout_log_probs`：Rollouter 在生成 token 时记录的每个生成 token 的 log probability，用于 Trainer 侧作为旧策略概率。
- `old log probability`：PPO 或 GRPO 训练中，分母所用的旧策略对已生成 token 的 log probability。
- `response_mask`：训练 mask，`1` 表示模型生成 token 参与损失，`0` 表示工具输出、环境 observation 或其他非模型生成 token 不参与损失。
- `partial output`：被中断 rollout 返回的临时 `AgentLoopOutput`，它主要保存恢复所需状态，不代表可训练完整样本。
- `wall-clock budget`：真实时间预算，例如一条 search trajectory 最多允许运行多少秒。
- `compact tensor view`：训练侧实际消费的紧凑张量视图，也就是 prompt、response、mask、log probability 等字段。

## 1. 一句话总结

verl 的 `fully_async_policy` 不是简单地把 `AgentLoopBase.run()` 写成异步函数，而是把原本同步的“生成样本、计算奖励、训练更新、同步权重”流水线拆成相互解耦的四个 Ray 组件：

```text
FullyAsyncRollouter
  持续生成样本
    -> MessageQueue
      缓冲已完成样本
        -> FullyAsyncTrainer
          持续消费样本并训练
            -> ParameterSynchronizer
              定期把 Trainer 侧新权重同步给 Rollouter
```

在这个架构里，Agent Loop 只位于 Rollouter 侧。它负责把一条 prompt 跑成一条完整 trajectory；Trainer 不关心工具调用过程，只消费已经完成并组装好的训练 batch。

## 2. 为什么需要 fully async

普通同步强化学习训练通常是这样的：

```text
生成整批 rollout
  -> 等整批全部完成
    -> 计算 reward
      -> 计算 advantage
        -> 更新 actor
          -> 同步权重
            -> 下一批 rollout
```

这个流程对普通单轮问答问题还可以接受，因为每条样本耗时差异不大。但对 DeepSearch 或软件工程智能体任务来说，一个 batch 内部的样本耗时差异会非常大：

```text
样本 1：20 秒完成
样本 2：45 秒完成
样本 3：180 秒完成
样本 4：360 秒超时
```

同步训练必须等最慢的样本结束，前面已经完成的样本会空等。CaRR DeepSearch 项目的长尾问题就来自这里：有些问题几轮搜索就能回答，有些问题需要几十轮 `search -> open -> find`，甚至被 wall-clock budget 截断。fully async 的目标就是消除这个同步栅栏，让快样本先进入训练。

## 3. 四个核心组件

### 3.1 FullyAsyncRollouter

`FullyAsyncRollouter` 是样本生产者。它运行在独立的 rollout 资源池上，负责从数据集中逐条取样本、启动 Agent Loop、等待 trajectory 生成完成，并把完成的样本放入 `MessageQueue`。

它内部有三类队列或者任务集合：

```text
pending_queue
  Rollouter 内部的待生成样本队列。

active_tasks
  当前正在执行的 rollout coroutine 集合。

cancel_queue
  partial rollout 被中断后，等待恢复继续执行的样本队列。
```

这里容易混淆的是 `pending_queue` 和 `MessageQueue`。二者不是同一层东西：

```text
pending_queue:
  FullyAsyncRollouter 内部使用。
  存放还没有生成完成、等待被 Agent Loop 处理的样本。

MessageQueue:
  Rollouter 和 Trainer 之间使用。
  存放已经生成完成、可以被 Trainer 消费的样本。
```

完整流向是：

```text
dataloader
  -> _feed_samples()
    -> pending_queue
      -> _processor_worker()
        -> active_tasks
          -> Agent Loop / vLLM / SGLang
            -> 完成后的 RolloutSample
              -> MessageQueue
```

### 3.2 MessageQueue

`MessageQueue` 是 Rollouter 和 Trainer 中间的 Ray Actor 队列。Rollouter 调用 `put_sample()` 写入已完成样本，Trainer 调用 `get_sample()` 读取样本。

它的作用非常单纯：

```text
Rollouter:
  生成完成一条样本
    -> MessageQueue.put_sample(...)

Trainer:
  从 MessageQueue 取够 required_samples 条样本
    -> assemble_batch_from_rollout_samples(...)
    -> 执行训练 step
```

因此，`MessageQueue` 里面的样本已经完成 rollout。它不是待生成任务队列，也不负责执行 Agent Loop。

### 3.3 FullyAsyncTrainer

`FullyAsyncTrainer` 是训练消费者。它不再直接调用 rollout 生成，而是从 `MessageQueue` 中取样本。取够一组样本后，它会把多个 `RolloutSample` 合并成一个 `DataProto`，然后继续执行常规 PPO 或 GRPO 训练步骤：

```text
从 MessageQueue 取样本
  -> 组装 DataProto
    -> 计算 reward
      -> 处理 old log probability
        -> 计算 reference log probability
          -> 计算 advantage
            -> 更新 critic
              -> 更新 actor
                -> 判断是否需要同步参数
```

这里的 `required_samples` 通常由下面的公式决定：

```text
required_samples = actor.ppo_mini_batch_size * async_training.require_batches
```

也就是说，Trainer 每一次训练 step 会从队列中收集 `required_samples` 条已经完成的 rollout 样本。

### 3.4 ParameterSynchronizer

`ParameterSynchronizer` 负责把 Trainer 侧更新后的 actor 权重同步给 Rollouter 侧的推理服务。

一次参数同步大致是：

```text
Trainer 触发参数同步
  -> Rollouter.pause()
  -> MessageQueue.update_param_version(...)
  -> actor worker group 与 rollout worker group 同步权重
  -> 校验两侧参数 fingerprint
  -> Rollouter.update_param_version(...)
  -> Rollouter.resume()
```

如果启用了 `partial_rollout`，`Rollouter.pause()` 会通知正在运行的 Agent Loop 和推理 server 尽快取消当前生成请求，保存中间状态，然后在权重同步结束后恢复。

### 3.5 `RayWorkerGroup` 与 `FullyAsyncRayWorkerGroup` 这层

在本地 verl 代码快照中，并没有一个字面类名叫 `FullyAsyncRayWorkerGroup`。更准确的代码事实是：`FullyAsyncRollouter` 和 `FullyAsyncTrainer` 的初始化参数里都会接收 `ray_worker_group_cls: RayWorkerGroup = RayWorkerGroup`，并通过 verl 原有的 `ResourcePoolManager`、`role_worker_mapping` 和 `RayWorkerGroup` 机制组织训练和 rollout worker。

因此，如果在讨论 fully async 时提到 `FullyAsyncRayWorkerGroup`，可以把它理解成“fully async 模式下使用的 Ray worker group 编排层”，而不是一个新的 Agent Loop 算法，也不是 RepoHarness 需要重新实现的类。

这一层大致负责下面几件事情：

```text
ResourcePoolManager:
  管理 trainer resource pool 和 rollout resource pool。

role_worker_mapping:
  把 Actor、Rollout、Critic、RefPolicy 等角色映射到具体 Ray worker class。

RayWorkerGroup:
  把这些 Ray worker 按资源池组织起来，提供远程调用、初始化、参数同步协作等能力。

FullyAsyncRollouter / FullyAsyncTrainer:
  在自己的构造函数中接收 ray_worker_group_cls，
  但真正的样本生产、队列消费和训练流程仍由 Rollouter、MessageQueue、Trainer、ParameterSynchronizer 这些组件完成。
```

这层和前面四个核心组件的关系可以这样理解：

```text
RayWorkerGroup / resource pool 层:
  负责“这些 worker 跑在哪里、如何被 Ray 组织、如何被远程调用”。

FullyAsyncRollouter:
  负责“哪些样本要被生成、哪些 Agent Loop task 正在运行、什么时候把完成样本放入 MessageQueue”。

FullyAsyncTrainer:
  负责“什么时候从 MessageQueue 取样本、如何组 batch、如何执行 PPO 或 GRPO 更新”。

ParameterSynchronizer:
  负责“训练侧新参数如何同步到 rollout 侧推理 worker 或推理 server”。
```

对 RepoHarness 接入来说，这个边界很重要。第一版接入 verl 时，RepoHarness 不应该直接依赖或改造 `RayWorkerGroup` 这一层，也不应该把 `FullyAsyncRayWorkerGroup` 当成自己的稳定接口。RepoHarness 应该先面对更窄的两个接口：`AgentLoopBase.run(...)` 和 `LLMServerClient`。等后续进入 fully async 阶段，再把 RepoHarness 的 pause、resume、partial state 和 cancellation 语义对齐到 verl 已有的 Rollouter、Trainer、ParameterSynchronizer 和 Ray worker group 编排层。

## 4. 启动流程

fully async 的入口是 `fully_async_main.py` 中的 `FullyAsyncTaskRunner`。启动时它会做下面这些事情：

```text
1. 加载 tokenizer 和 processor。
2. 创建 trainer resource pool。
3. 创建 rollout resource pool。
4. 创建 FullyAsyncRollouter。
5. 创建 FullyAsyncTrainer。
6. 创建 MessageQueue 和 MessageQueueClient。
7. 把 MessageQueueClient 分别传给 Rollouter 和 Trainer。
8. 创建 ParameterSynchronizer。
9. 加载 checkpoint。
10. 做一次初始参数同步。
11. 同时启动 rollouter.fit() 和 trainer.fit()。
```

最后一步最关键：Rollouter 和 Trainer 是并行运行的。Rollouter 负责不断生产样本，Trainer 负责不断消费样本，中间只通过 `MessageQueue` 连接。

## 5. 一个样本的完整生命周期

一条训练样本在 fully async 中的生命周期如下：

```text
数据集样本
  -> FullyAsyncRollouter._feed_samples()
    -> 封装成 RolloutSample
      -> 放入 pending_queue
        -> FullyAsyncRollouter._processor_worker()
          -> 创建 _process_single_sample_streaming(...) task
            -> FullyAsyncAgentLoopManager.generate_single_sample_async(...)
              -> FullyAsyncAgentLoopWorker.generate_sequences_no_post(...)
                -> 具体 Agent Loop 的 run(...)
                  -> vLLM 或 SGLang generate_for_partial(...)
                    -> AgentLoopOutput
                      -> 更新 RolloutSample
                        -> MessageQueue.put_sample(...)
                          -> FullyAsyncTrainer._get_samples_from_queue()
                            -> assemble_batch_from_rollout_samples(...)
                              -> 训练
```

如果样本正常完成，Rollouter 会把完整 `RolloutSample` 放入 `MessageQueue`。如果样本被 partial rollout 中断，Rollouter 不会把它交给 Trainer，而是把携带中间状态的结果放入 `cancel_queue`，等待参数同步后继续执行。

## 6. 三个容易混淆的计数器

fully async 中有三个重要计数器：

```text
global_steps:
  Trainer 实际执行了多少次本地训练 step。

local_trigger_step:
  当前参数同步周期内，Trainer 已经训练了多少次。

current_param_version:
  已经同步给 Rollouter 的 actor 参数版本。
```

例如：

```text
async_training.trigger_parameter_sync_step = 4
```

那么时间线是：

```text
Trainer global step 1:
  训练一次，不同步参数。

Trainer global step 2:
  训练一次，不同步参数。

Trainer global step 3:
  训练一次，不同步参数。

Trainer global step 4:
  训练一次，触发参数同步，current_param_version 从 0 变成 1。
```

因此，一个参数版本可能覆盖多个 Trainer 本地训练 step。日志中按 `current_param_version` 记录的 step，通常不是每一次本地训练 step。

## 7. Staleness 控制

staleness 表示样本生成时的参数版本落后于 Trainer 当前训练版本。

例如：

```text
Rollouter 使用参数 v0 生成 sample_1。
Trainer 已经训练并同步到 v1。
Trainer 在 v1 阶段从队列里取到 sample_1。
```

此时 `sample_1` 就是 stale sample。

Rollouter 通过 `max_required_samples` 和 `staleness_samples` 间接控制当前参数版本窗口中还能继续生产多少样本。核心公式是：

```text
required_samples =
  actor.ppo_mini_batch_size * async_training.require_batches

max_required_samples =
  required_samples * (1 + async_training.staleness_threshold) * async_training.trigger_parameter_sync_step
```

其中 `required_samples` 是 Trainer 每次训练 step 需要从 `MessageQueue` 中取出的样本数量，`max_required_samples` 是 Rollouter 在一个参数同步窗口内的生产上限参考。

需要注意两个实现细节：

```text
参数同步后：
  staleness_samples 会被重置为当前 active_tasks 数量
  加上 MessageQueue 中已经完成但还没有被 Trainer 消费的样本数量。

非 partial 模式：
  还会把 cancel_queue 中等待恢复的样本数量也计入 staleness_samples。
```

这说明 `staleness_threshold` 不是一个直接写在样本上的“旧样本比例限制”，而是通过 Rollouter 的生产节流间接影响 stale 样本数量。

一般理解可以是：

```text
staleness_threshold = 0:
  尽量保持同步，旧版本样本很少。

staleness_threshold > 0:
  允许 Rollouter 多生产一些旧版本样本，让 Trainer 在参数同步后仍然有样本可以立刻训练。
```

它本质上是吞吐与 on-policy 程度之间的权衡。值越大，吞吐越高，但 off-policy 程度也越高。

还有一个容易忽略的边界：在当前代码中，如果 `partial_rollout=true`，`staleness_samples >= max_required_samples` 触发的 self-pause 会被跳过，Rollouter 主要依靠 `queue_full` 反压和外部参数同步暂停来控制生产节奏。因此，partial 模式下不能把 `staleness_threshold` 理解成严格的硬性旧样本比例上限。

## 8. rollout_log_probs 的作用

在同步 PPO 或 GRPO 训练中，Trainer 通常会在 actor 更新前，用与 rollout 对齐的旧策略参数重新计算 `old_log_probs`。这里的“旧策略”不是训练后任意当前参数，而是生成这批样本时应当对应的策略版本。

fully async 中不能简单使用 Trainer 当前已经更新后的参数来当作旧策略。样本可能由旧参数生成，而 Trainer 当前已经更新到了新参数。如果用更新后的参数重新计算 old log probability，PPO 或 GRPO 的重要性采样分母就不再对应“生成该 token 时的策略”。

因此 fully async 默认要求：

```yaml
actor_rollout_ref.rollout.calculate_log_probs: true
actor_rollout_ref.actor.use_rollout_log_probs: true
algorithm.rollout_correction.bypass_mode: true
```

含义是：

```text
Rollouter 生成 token 时，同时保存每个生成 token 的 log probability。
Trainer 训练时，在 bypass_mode=true 的默认路径下，直接把 rollout_log_probs 当作 old_log_probs。
```

这样可以保证 old log probability 与生成 token 的参数版本一致。对于异步训练来说，这是非常重要的正确性边界。

如果 `algorithm.rollout_correction.bypass_mode=false`，fully async 还可以走 decoupled PPO 或 rollout correction 路径，由 Trainer 重新计算 old log probability，并结合 rollout 阶段保存的 log probability 做修正。这条路径更复杂，训练成本也更高，但可以更精细地处理 off-policy 偏差。

## 9. partial rollout 的中断与恢复

`partial_rollout` 解决的是参数同步时的长尾等待问题。

不启用 `partial_rollout` 时：

```text
Trainer 请求同步参数
  -> Rollouter 暂停接收新任务
  -> 等所有 active_tasks 自然完成
  -> 同步参数
  -> 恢复生成
```

如果某个 DeepSearch 样本还在跑几十轮工具调用，同步就可能要等很久。

启用 `partial_rollout` 时：

```text
Trainer 请求同步参数
  -> Rollouter 通知 AgentLoopWorker 和推理 server 取消当前请求
  -> Agent Loop 保存当前 AgentData 和 AgentState
  -> 返回 is_cancel=True 的 AgentLoopOutput
  -> Rollouter 把未完成样本放入 cancel_queue
  -> 同步参数
  -> Rollouter 从 cancel_queue 恢复样本
  -> Agent Loop 从保存状态继续运行
```

这里的核心不是“丢弃样本”，而是“中断后恢复”。中断输出不会进入 Trainer。只有样本最终完整完成后，才会被放入 `MessageQueue`。

在当前实现中，取消不只来自参数同步。如果 `partial_rollout=true` 且 `MessageQueue` 已经满了，Rollouter 也会触发 `queue_full` 反压，并通过 cancel-based drain 尽快清理正在执行的任务，避免完成样本继续堆积。

## 10. partial rollout 在 Agent Loop 层如何实现

fully async 的 Agent Loop Worker 会把一个 `cancellation_event` 传给具体的 Agent Loop：

```text
agent_loop.run(
  sampling_params,
  cancellation_event=self.cancellation_event,
  output=上次中断保存的 partial output,
  ...
)
```

Agent Loop 在运行状态机时需要检查：

```text
如果 cancellation_event 已经设置：
  返回一个 is_cancel=True 的 AgentLoopOutput。
```

不过，在 CaRR 的 async partial 路径里，中断恢复并不是只靠这一处 `cancellation_event.is_set()`。正在模型生成时，主要由 `generate_for_partial(...)` 返回 `is_cancel=True` 来表示推理 server 已经被取消。Agent Loop 会先把已经生成出来的 token 和对应 log probability 追加到 `AgentData` 中，再构造带中间状态的取消输出。

这个取消输出通常不包含可训练 token，而是通过 `extra_fields` 保存中间状态：

```text
extra_fields["is_cancel"] = True
extra_fields["agent_data"] = 当前 AgentData
extra_fields["agent_state"] = 当前状态机状态
```

恢复时，Agent Loop 看到传入的 `output.extra_fields["is_cancel"] == True`，就从中恢复 `agent_data` 和 `agent_state`，继续执行状态机。

## 11. vLLM 和 SGLang 的 generate_for_partial

fully async 版 vLLM 和 SGLang server 都提供了 `generate_for_partial(...)`。它的核心机制是让两个异步任务竞争：

```text
真实生成任务:
  模型继续生成 token。

cancel event 等待任务:
  等待 Rollouter 或 ParameterSynchronizer 发出取消信号。
```

如果模型先生成完成：

```text
返回 token_ids、log_probs、is_cancel=False。
```

如果取消信号先到：

```text
返回当前已经生成的 token_ids、log_probs、is_cancel=True。
```

这就是 partial rollout 能保存已经生成 token 并在同步后继续的基础。

## 12. CaRR 项目的两条 Agent Loop 路径

CaRR 项目里的 `carr_agent_loop.py` 有两条路径。

第一条是普通路径：

```text
CaRRToolAgentLoop
  注册名：carr_tool_agent
  继承：ToolAgentLoop
  用途：普通多轮 search agent rollout
```

它的状态机大致是：

```text
PENDING
  -> GENERATING
    -> PROCESSING_TOOLS
      -> GENERATING
        -> ...
          -> TERMINATED
```

如果配置了额外的 interaction 机制，状态机中还可以出现 `INTERACTING` 状态；CaRR DeepSearch 的主线通常关注 `search`、`open`、`find` 这些工具调用，所以最常见的是 `GENERATING` 和 `PROCESSING_TOOLS` 之间的循环。

每轮模型输出后，它解析 `<tool_call>`，然后调用：

```text
browser.search
browser.open
browser.find
```

工具结果会被加入下一轮 prompt，但对应 token 的 `response_mask` 是 `0`，表示这些 token 是环境 observation，不参与模型训练损失。

第二条是 fully async 路径：

```text
CaRRAsyncPartialToolAgentLoop
  注册名：carr_async_partial_tool_agent
  用途：支持 partial rollout 的 CaRR search agent
```

这条路径保存的不只是通用 `AgentData`，还保存 CaRR 自己的业务状态。

## 13. CaRR 额外保存了哪些状态

CaRR reward server 需要一份特殊格式的 `reward_history`。因此 CaRR 的 async partial Agent Loop 必须在中断恢复时保存这些字段：

```text
reward_history
pending_tool_calls
turn_idx
hit_limit
hit_budget
termination_reason
total_tool_calls
search_count
open_count
find_count
parse_error_count
content_early_stopped
real_rollout_start_s
active_rollout_wall_time_s
assistant_turn_in_progress
param_version_start
last_param_version
```

如果只保存普通 token 序列，而不保存这些状态，恢复后 reward history 会断裂，工具调用计数也会错误，最终 reward 和诊断指标都会变得不可信。

## 14. CaRR 的 AgentLoopOutput

CaRR 完成一条 trajectory 后，会返回 `AgentLoopOutput`。它包含训练侧实际消费的紧凑张量视图：

```text
prompt_ids
response_ids
response_mask
response_logprobs
num_turns
metrics
```

普通 `CaRRToolAgentLoop` 会在 `extra_fields` 中保存 CaRR reward 和诊断需要的内容：

```text
messages
tool_call_counts
search_count
open_count
find_count
parse_error_count
termination_reason
task_unfinished
rollout_elapsed_s
response_length
hit_limit
hit_budget
termination_* 诊断标志
```

`CaRRAsyncPartialToolAgentLoop` 在完成输出中还会额外保存 partial rollout 和参数版本相关字段：

```text
param_version_start
param_version_end
param_version_span
active_rollout_elapsed_s
real_rollout_elapsed_s
is_cancel
```

这里可以看到一个重要边界：

```text
AgentLoopOutput 的 batch 字段服务于训练。
extra_fields 服务于 reward、诊断和日志。
```

## 15. 四种 fully async 模式

verl 的 fully async 可以用三个参数组合出四种模式：

```text
async_training.staleness_threshold
async_training.trigger_parameter_sync_step
async_training.partial_rollout
```

最保守模式：

```text
staleness_threshold = 0
trigger_parameter_sync_step = 1
partial_rollout = false
```

含义：基本等价于同步训练。

流式同步模式：

```text
staleness_threshold = 0
trigger_parameter_sync_step > 1
partial_rollout = false
```

含义：Rollouter 一次生产一个同步周期需要的样本，Trainer 分批消费，但仍然尽量不使用旧版本样本。

异步 stale 模式：

```text
staleness_threshold > 0
partial_rollout = false
```

含义：允许旧版本样本进入队列，但参数同步时要等待在飞任务自然完成。

异步 partial 模式：

```text
staleness_threshold > 0
partial_rollout = true
```

含义：允许旧版本样本，并且参数同步时可以中断在飞任务，同步后恢复。

CaRR DeepSearch 需要区分配置文件默认值和正式异步主线。`examples/carr_deepsearch/config/carr_grpo_async.yaml` 的默认值是 `staleness_threshold: 0.0`、`partial_rollout: false`，更像 sync-stream 探针口径；`scripts/run_rl_async.sh` 中的 `ASYNC_PROFILE=async_partial` 以及正式异步训练脚本会覆盖为 `partial_rollout=true`、`staleness_threshold>0`。因此，准确表述是：CaRR 的 async partial profile 和正式异步主线使用的是“异步 partial 模式”，而配置文件默认值本身不是这个模式。

## 16. 对 RepoHarness 的启发

CaRR 的经验说明，fully async 能显著缓解长尾 agent rollout 的同步栅栏问题，但代价是 Agent Loop 必须拥有清晰的状态保存和恢复边界。

对 RepoHarness 来说，这个难度会更高。CaRR 主要保存搜索状态和 reward history；RepoHarness 未来如果支持 partial rollout，可能还需要保存：

```text
workspace 状态
文件修改状态
工具执行状态
trajectory recorder 状态
patch 状态
verifier 状态
artifact refs
context compaction 状态
policy_version_start 和 policy_version_end
```

因此，RepoHarness 接入 verl 的合理顺序应该是：

```text
第一阶段：
  普通 AgentLoop 接入，不启用 fully async。

第二阶段：
  启用 fully async，但 partial_rollout=false。

第三阶段：
  在 RepoHarness 内部定义可恢复的 episode state，再启用 partial_rollout=true。
```

这个顺序可以先验证 token、mask、reward、trajectory、log probability 的正确性，再处理最复杂的中断恢复问题。

这里的三阶段是粗粒度技术顺序。更细的 RepoHarness 接入阶段划分，包括 `EnvService Mode`、fully async 队列化和多训练后端适配，见 [repo_harness_verl_architecture_plan.md](repo_harness_verl_architecture_plan.md)。
