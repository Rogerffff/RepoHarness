# RepoHarness 完整代码链路学习笔记

```text
document_role: learning_notes
authority: non_authoritative
update_policy: user_confirmed_only
```

## 1. 文档用途

本文用于记录用户与 codex 沿真实代码阅读 RepoHarness 完整链路时共同确认的
理解，包括调用关系、运行边界、核心数据对象、状态所有权和失败路径。

本文是学习材料，不是架构、契约或当前进度的权威来源。发生不一致时，分别以
真实代码、阶段执行计划和下列权威文档为准：

- `docs/agentic_RL/repo_harness_rh2_workstreams/00-project-status.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/05-fully-async-execution-plan.md`
- `docs/agentic_RL/repo_harness_rh2_workstreams/fa/implementation-notes.md`
- `docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`

## 2. 维护约定

- 讲解过程不自动写入本文。
- 只有用户明确提出需要记录，并与 codex 确认写入内容和表达方式后才更新。
- 每条笔记尽量附具体文件、函数或测试路径，避免只留下抽象结论。
- 已实现、临时实现、计划实现和外部参考实现必须明确区分。
- 如果旧笔记被新代码或新决策推翻，保留修订原因，不静默改写历史认识。

## 3. 单个链路节点的建议记录格式

```text
节点名称：
代码入口：
上游调用者：
输入对象：
输出对象：
运行位置（进程 / 线程 / event loop / async task）：
可变状态 owner：
正常路径：
失败与取消路径：
反压方式：
当前实现状态：
与训练语义的关系：
仍未理解或待验证的问题：
```

## 4. 待学习目录

### 4.1 完整链路总览与关键身份

当前先建立下面这条最小主线。这里包含外部运行时基座 slime，因为 RH2 的
rollout 函数正是由 slime 调用；如果省略这一段，就无法解释 RH2 从哪里获得
任务、推理资源和训练后端。

```text
Ray Driver：reference/slime/train_async.py
  │
  ├─ 创建 Placement Group，预留训练和 rollout GPU
  │
  ├─ 创建 RolloutManager CPU Ray Actor
  │    ├─ 启动 SGLang Router CPU 子进程
  │    ├─ 创建并管理 SGLangEngine GPU Ray Actors
  │    ├─ 持有 DataSource 普通 Python 对象
  │    ├─ 动态加载 RH2 generate_rollout 函数
  │    └─ 创建权重更新 Lock CPU Ray Actor
  │
  ├─ 创建多个 Megatron trainer GPU Ray Actors
  │    └─ 把 RolloutManager ActorHandle 传给每个 trainer
  │
  └─ 调用 RolloutManager.generate.remote(rollout_id)
       └─ 后续进入 RH2 rollout entry
```

这一层先区分下列不同事物：

| 对象 | 是否独立进程 | 主要作用 |
|---|---|---|
| `train_async.py` Driver | 是 | 创建组件并编排训练循环 |
| Placement Group | 否 | Ray 调度器中的资源预留 |
| `RolloutManager` | 是，CPU Ray Actor | rollout 控制面 |
| SGLang Router | 是，CPU 子进程 | 接收请求并选择 SGLang server |
| `SGLangEngine` | 是，GPU Ray Actor | 启停、更权和恢复推理服务的控制面 |
| SGLang server | 是，由 engine 启动的子进程 | 在 GPU 上执行真实模型推理 |
| `DataSource` | 否 | `RolloutManager` 进程内的数据与游标对象 |
| `rollout_engine_lock` | 是，CPU Ray Actor | 跨进程串行协调权重传输 |

Actor、ActorHandle、ObjectRef、Placement Group 和 rank 的通用解释见
`python_async_concurrency_foundations.md` 的 4.3、4.7 和 4.10 节。

### 4.2 slime 启动基座：RolloutManager、DataSource 与 Trainer Actors

#### 4.2.1 代码入口与返回值

代码入口：

- `reference/slime/train_async.py`
- `reference/slime/slime/ray/placement_group.py::create_rollout_manager`
- `reference/slime/slime/ray/rollout.py::RolloutManager`

Driver 调用：

```python
rollout_manager, num_rollout_per_epoch = create_rollout_manager(
    args,
    pgs["rollout"],
)
```

这里的 `rollout_manager` 是 `RolloutManager` 的 ActorHandle，不是远程对象
本身；`num_rollout_per_epoch` 是用全局数据集长度和 rollout batch 大小计算的
epoch 参考值。

`RolloutManager` 申请 `1 CPU / 0 GPU`，而且创建它时没有指定
`PlacementGroupSchedulingStrategy`。因此它由 Ray 使用普通集群 CPU 调度，
不会占用为训练和 rollout GPU Actor 预留的八个 bundle。传给它的 `pg` 只是
一个资源布局句柄，供它随后创建 SGLang engine 时使用。

#### 4.2.2 启动 SGLang rollout servers

`RolloutManager.__init__` 调用：

```python
self.servers, rollout_init_handles = start_rollout_servers(args, pg)
```

`start_rollout_servers` 可能根据配置创建多个模型、多个 server group 和多个
`SGLangEngine` Ray Actor，所以不会只返回一个 ActorHandle。

`self.servers` 是当前 `RolloutManager` 进程里的普通字典：

```text
dict[model_name, RolloutServer]
  └─ RolloutServer.server_groups
       └─ ServerGroup.all_engines
            └─ SGLangEngine ActorHandles
```

`RolloutServer` 和 `ServerGroup` 是用于组织 router 地址、engine 分组和控制
操作的普通 Python 对象；真正的远程 engine 句柄保存在其内部。

这里的 Router 不是 slime 自己实现的路由算法。slime 依赖外部
`sglang-router` 包：slime 负责启动 Router 子进程、传入策略与注册
workers；SGLang Router 在运行时真正执行 worker 选择和请求转发。

每个 engine 创建后还会执行：

```python
init_ref = engine.init.remote(...)
```

`rollout_init_handles` 保存的是这些初始化调用的 ObjectRef，而不是 engine
ActorHandle。随后：

```python
ray.get(rollout_init_handles)
```

显式等待所有 engine 完成模型加载、端口初始化和服务准备；任何远程初始化
异常也会在这里传播。没有这个等待，后续 rollout 可能在服务尚未就绪时发出
请求。

#### 4.2.3 创建 DataSource

```python
data_source_cls = load_function(self.args.data_source_path)
self.data_source = data_source_cls(args)
```

这里有两个容易混淆的配置：

```text
data_source_path
  Python 类路径，例如
  slime.rollout.data_source.RolloutDataSourceWithBuffer

prompt_data
  实际 JSONL 等任务数据文件路径
```

`load_function` 先导入 DataSource 类；实例化时，这个类再从
`args.prompt_data` 加载任务数据。最终的 `self.data_source` 是
`RolloutManager` 进程内的普通 Python 对象，不是新的 Ray Actor。

默认实现主要拥有：

- prompt/task 数据集；
- `sample_offset` 和 `epoch_id`；
- `sample_group_index` 和 `sample_index`；
- 同一 prompt 展开 `n_samples_per_prompt` 个 Sample 的逻辑；
- shuffle、save/load，以及 buffer 版本的样本退回能力。

调用 `get_samples()` 时游标就会推进，并不等待 trainer 消费完成。fully async
模式下，“DataSource 已分派”“rollout 已完成”和“trainer 已消费”是三个不同
状态；相关恢复问题见基础知识文档 4.10 节。

#### 4.2.4 动态加载 rollout 函数

```python
self.generate_rollout = load_function(
    self.args.rollout_function_path
)
```

命令行中的 Python 符号路径会被加载为 `RolloutManager` 进程内的普通函数
对象。之后：

```python
call_rollout_fn(
    self.generate_rollout,
    args,
    rollout_id,
    self.data_source,
    evaluation=False,
)
```

才真正调用这个函数。slime stock fully async 和 RH2 fully async 可以使用不同
的 `rollout_function_path`，但共享同一个 `train_async.py` 训练入口。

#### 4.2.5 创建权重更新 Lock Actor

```python
self.rollout_engine_lock = Lock.options(
    num_cpus=1,
    num_gpus=0,
).remote()
```

这是由 `RolloutManager` 发起创建、但独立运行的另一个 CPU Ray Actor。它用
一份远程 `_locked` 状态串行协调 trainer 向 SGLang engine 传输权重，避免
并发 NCCL 权重广播冲突。

后续创建 trainer 时，Driver 会把 `RolloutManager` ActorHandle 传给每个
trainer：

```text
trainer
  -> 调用 RolloutManager.get_updatable_engines_and_lock()
  -> 得到 SGLang engine ActorHandles 和 Lock ActorHandle
  -> 通过 Lock ActorHandle 执行 acquire/release
```

这个锁只负责串行化相关权重传输，不单独保证 fully async 下的生成暂停、
策略版本一致性或更新中断恢复；这些由后续 coordinator 和版本协议处理。

#### 4.2.6 创建训练 Actor 组

Driver 随后调用：

```python
actor_model, critic_model = create_training_models(
    args,
    pgs,
    rollout_manager,
)
```

当前 GRPO 配置不使用独立 value/critic model，因此 `critic_model=None`。
`actor_model` 也不是单个远程 Actor，而是 Driver 进程内的普通
`RayTrainGroup` 管理对象：

```text
RayTrainGroup（Driver 内普通对象）
  └─ _actor_handlers
       ├─ MegatronTrainRayActor rank 0 ActorHandle
       ├─ MegatronTrainRayActor rank 1 ActorHandle
       ├─ MegatronTrainRayActor rank 2 ActorHandle
       └─ MegatronTrainRayActor rank 3 ActorHandle
```

真实调用栈是：

```text
create_training_models
  -> allocate_train_group
     -> RayTrainGroup.__init__
        -> _allocate_gpus_for_actor
           -> 循环创建各 MegatronTrainRayActor
```

在 `actor_num_nodes=1、actor_num_gpus_per_node=4` 时，训练
`world_size=4`，所以创建四个独立训练进程。每个进程是一个 global rank；
Megatron 稍后再根据 TP/DP/PP/EP 配置把这些 ranks 组成不同通信组。

#### 4.2.7 从实现类到四个远程实例

默认实现类由运行时选择：

```python
actor_impl = MegatronTrainRayActor
TrainRayActor = ray.remote(**actor_options)(actor_impl)
```

这里分三层：

```text
actor_impl
  定义行为的普通 Python 类

TrainRayActor
  Ray 包装后的远程 Actor 类，还没有具体进程

TrainRayActor.options(...).remote(...)
  创建一个远程实例，返回 ActorHandle
```

动态包装而不是在固定类上写死 `@ray.remote`，是因为 slime 允许注入自定义
`actor_cls`，并根据运行参数设置 `runtime_env`、NIXL tensor transport 等
Actor 选项。

循环创建每个 rank 时还会指定：

```python
PlacementGroupSchedulingStrategy(
    placement_group=pg,
    placement_group_bundle_index=
        reordered_bundle_indices[rank],
)
```

`reordered_bundle_indices` 是按照实际节点 IP 和物理 GPU ID 重排后的
`list[int]`。它把训练 rank 绑定到预留资源中的确定 bundle，避免 Ray 从
集群任意 GPU 重新调度。`num_gpus_per_actor=0.4` 是 Ray 的逻辑资源记账，
允许 actor/critic 等角色共用 bundle；它不是 40% 显存上限。当前 GRPO 没有
critic，不能据此推断剩余 0.6 一定被其他模型使用。

#### 4.2.8 两阶段初始化与 distributed rendezvous

创建远程实例时，Python 自动调用继承自基类的构造函数：

```text
TrainRayActor.__init__
  -> 设置 MASTER_ADDR / MASTER_PORT
  -> 设置 WORLD_SIZE / RANK / LOCAL_RANK
```

这里的 `__init__` 是 Python 构造函数。稍后显式调用的 `init` 是另一个普通
方法：

```text
RayTrainGroup.async_init（Driver 内普通同步方法）
  -> 对四个 Actor 提交 actor.init.remote(...)
  -> 返回四个 ObjectRef

外层 ray.get(ObjectRef 列表)
  -> 等待四个 rank 全部完成
```

必须先 fan-out 全部远程调用、再统一等待。每个 rank 都会在
`dist.init_process_group()` 中等待其他 ranks；如果 Driver 逐个提交并立即
`ray.get`，rank 0 会等待尚未提交的 rank 1~3，形成死锁。

远程调用进入：

```text
MegatronTrainRayActor.init
  -> super().init，即 TrainRayActor.init
     -> 绑定当前 CUDA 设备
     -> 建立 PyTorch distributed process group
     -> 建立 Gloo 控制通信组
     -> 尝试设置 NUMA affinity
  -> 初始化 Megatron TP/DP/PP/EP 全局状态
  -> 读取 Hugging Face config/tokenizer
  -> 构造模型、optimizer、scheduler
  -> 从 checkpoint 恢复 loaded_rollout_id
  -> 构造权重备份与 SGLang 权重更新器
  -> 返回 start_rollout_id = loaded_rollout_id + 1
```

rank 0 最先选择一个可访问 IP 和空闲端口作为 rendezvous 地址；其余 rank
使用同一地址完成进程发现和通信初始化。这个地址主要用于启动集合，不表示
后续所有 NCCL 张量都经过 rank 0。

四个 Actor 各自返回 `start_rollout_id`，Driver 检查它们完全一致，防止不同
训练 rank 从不同 checkpoint 进度恢复。

#### 4.2.9 当前阅读断点

目前已读完 `create_training_models(...)` 中训练 Actor 的创建、资源绑定和
`async_init()` 主路径。为了不阻塞主链阅读，暂不深入 Ray 调度器、TCPStore、
NCCL bootstrap、NUMA 或 Megatron 模型构造内部。

下一段继续看 `create_training_models` 的收尾：把 `RolloutManager`
ActorHandle 传给 trainer、恢复 DataSource 状态；随后回到 `train_async.py`
查看首次 `actor_model.update_weights()` 和
`rollout_manager.generate.remote(...)`。

### 4.3 RH2 rollout entry、持续 worker 与调度

本节记录从 `RolloutManager.generate()` 进入 RH2，到单个 member 被交给
`RolloutOrchestrator.generate()` 之前的真实运行路径。这里先说明运行位置、
对象所有权和并发形态；`collect_batch()` 内部的队列、反压、组收齐和停机协议
尚未逐行学习，留给下一段补充。

#### 4.3.1 从同步 Ray Actor 方法进入异步 RH2 链路

Driver 通过 Ray RPC 调用：

```python
rollout_manager.generate.remote(rollout_id)
```

真正执行 `RolloutManager.generate()` 的是独立 CPU Ray Actor 进程。该方法经
`call_rollout_fn(...)` 调用 RH2 注册的同步入口：

```text
reference/slime/slime/ray/rollout.py::RolloutManager.generate
  -> RolloutManager._get_rollout_data
  -> call_rollout_fn(self.generate_rollout, ...)
  -> rh2/experiments/fa_bringup/rollout_entry.py::generate_rollout
```

`generate_rollout()` 必须是同步函数，因为 slime 的 `call_rollout_fn()` 不会
`await` 它。该同步入口用 `slime.utils.async_utils.run(...)` 把
`generate_rollout_async(...)` 提交给同一 Actor 进程中的持久
`AsyncLoopThread`，Actor 主线程在 `.result()` 处等待结果：

```text
RolloutManager Ray Actor 进程
  ├─ Actor 主线程
  │    generate_rollout(...)
  │      -> 把 coroutine 提交到后台 loop
  │      -> 同步等待本次 batch 返回
  │
  └─ AsyncLoopThread
       └─ asyncio event loop
            └─ generate_rollout_async(...)
```

这里没有创建新的 Ray Actor。`AsyncLoopThread` 只是当前 Actor 进程中的普通
后台线程，它拥有一个长期运行的 asyncio event loop。

#### 4.3.2 两个进程内单例与一个实际唯一的 orchestrator

当前生产路径中存在两个不同的进程内单例：

| 对象 | 单例实现 | 主要职责 |
|---|---|---|
| `BringupService` | 类变量 `BringupService._instance` + `_SERVICE_LOCK` | 一次性装配 tokenizer、renderer、adapter、capture、评分和单 execution 编排能力 |
| `FaRolloutService` | `rollout_entry.py` 模块变量 `_SERVICE` | 持续取任务、维持并发 execution、接收完成结果并为调用方收集 batch |

它们都是**当前 `RolloutManager` Python 进程内**的单例，不是 Ray 集群全局
单例。另一个 Actor 进程会有自己的 Python 解释器、模块变量和类变量；当前
Actor 崩溃重启后，这些对象也会重新初始化。

首次调用 `generate_rollout_async(...)` 时：

```text
generate_rollout_async
  -> _bootstrap_via_glue(args, data_buffer)
  -> BringupService.get(args)
       -> 首次：构造 BringupService
       -> await service.async_start(args)
       -> 保存到 BringupService._instance
  -> args.rh2_orchestrator = service.orchestrator
  -> args.rh2_sampling_params = 显式采样配方
  -> _build_service(args, data_buffer)
  -> 保存到 rollout_entry._SERVICE
```

`RolloutOrchestrator` 类本身没有 singleton pattern，理论上仍可直接创建多个
实例。但是当前生产装配路径只在 `BringupService.async_start()` 中创建一次：

```text
BringupService 单例
  └─ self.orchestrator = RolloutOrchestrator(...)
       └─ 同一个引用写入 args.rh2_orchestrator
            └─ FaRolloutService 的 execute_member 闭包调用它
```

因此准确说法是：**每个当前 `RolloutManager` 进程在这条装配路径上实际使用
一个 orchestrator；不是该类从语言层面禁止创建第二个对象。**

#### 4.3.3 当前进程中的线程、event loop、Task 和外部进程

当前已经确认的执行拓扑是：

```text
RolloutManager Ray Actor 进程（CPU 控制面）
│
├─ 线程 T0：Ray Actor 主线程
│    └─ 同步进入 generate_rollout，并等待异步 batch 结果
│
├─ 线程 T1：slime AsyncLoopThread，event loop L1
│    ├─ BringupService / FaRolloutService
│    ├─ ContinuousExecutionWorker（一个长期 asyncio Task）
│    ├─ 多个 RolloutOrchestrator.generate execution Task
│    ├─ Docker CLI 异步子进程管理
│    └─ GradingQueue 的多个 asyncio worker Task
│
└─ 线程 T2：Anthropic adapter 线程，event loop L2
     ├─ aiohttp HTTP handler Task
     ├─ ModelCallProxy
     ├─ capture stage / commit
     └─ 到 SGLang 的 HTTP 请求

宿主机 Docker daemon 管理：
  ├─ 多个 rollout 容器
  │    └─ 每个容器内的 Claude Code 进程及其 bash/test 子进程
  └─ clean grading 容器

rollout GPU 侧：
  └─ SGLang router / server（由 slime 管理，不在 orchestrator 进程中做模型前向）
```

`ContinuousExecutionWorker` 不是线程池。它在 L1 中通过
`asyncio.create_task(...)` 维持最多 `rh2_fa_concurrency` 个 execution Task。
每个 execution Task 调用同一个：

```python
await orchestrator.generate(args, member, sampling_params)
```

如果并发上限是 8，运行时可能同时存在 8 个 `generate()` 协程、8 个 rollout
容器和 8 个 Claude Code 进程，但仍只有一个 `RolloutOrchestrator` 对象。

每次 `generate()` 调用拥有独立的协程帧和局部变量，例如各自的 `task`、
`sid`、`sandbox`、`hook` 和 `audit`；`orchestrator.config`、`audits` 以及注入的
共享服务引用则由这些调用共同访问。共享可变状态必须由明确 owner、锁或消息
传递保护。特别是 T1 与 T2 会共同接触 capture/proxy 状态，不能因为它们位于
同一 Python 进程就假设并发访问天然安全。

#### 4.3.4 三个服务对象的职责边界

```text
BringupService
  负责“把执行一条 member 所需的长期基础设施装配好”
  持有 tokenizer、renderer、CaptureRegistry、ModelCallProxy、
  AnthropicAdapter、GradingQueue、SWEGradingManager 和 RolloutOrchestrator。

FaRolloutService
  负责“持续派发多个 member，并收集可返回给 slime 的完整组/batch”
  持有 task source、ContinuousExecutionWorker、BoundedDeliveryQueue、
  group collector 和 completed backlog。

RolloutOrchestrator
  负责“把一个 member 从任务解析执行到训练资格结果”
  单次调用覆盖任务解析、rollout 容器、harness、capture 收口、评分、
  projection、EligibilityGate、交付/拒绝、清理和 execution audit。
```

这里的关键边界是：orchestrator 只处理一个 execution/member，不负责判断一个
PromptGroup 是否收齐，也不负责从 ready groups 中选择满足训练 batch schedule
的组合。这些属于外层 assembler、queue 和 batch admission。

#### 4.3.5 RolloutOrchestrator 的依赖注入接线

`BringupService.async_start()` 创建 orchestrator 时，把真实执行能力作为函数或
对象传入，而不是让 orchestrator 在内部自行寻找全局组件：

| orchestrator 字段 | 生产接线 | 含义 |
|---|---|---|
| `_task_resolver` | `BringupService._resolve_task` | `Sample` 转为冻结 `RolloutTaskSpec` |
| `_adapter_factory` | `BringupService._adapter_factory` | 为本 execution 创建绑定 capture hook 的 session adapter |
| `_harness_driver` | `ClaudeCodeDriver` | 在 rollout 容器内安装并运行 Claude Code |
| `_grading_submit` | `BringupService._grading_submit` | 把评分请求提交给 `GradingQueue` |
| `_docker` | 默认 `run_docker` | 启动、检查和清理 Docker 容器 |
| `_leaf_facts_fn` | `bringup_leaf_facts` | 描述叶链与模型调用 capture 的回链关系 |
| `_mount_planner` | 默认实现 | 只允许 public bundle 进入 rollout 容器 |

例如传入的 `self._grading_submit` 是 Python 绑定方法：它同时引用
`BringupService._grading_submit` 这个函数和当前 `BringupService` 实例。
orchestrator 以后调用该字段时，方法仍能通过绑定实例访问真正由
`BringupService` 持有的 `grading_queue`。这表示 orchestrator 获得了“提交
评分”这一项窄能力，并没有取得 `GradingQueue` 的生命周期所有权。

绑定方法、对象引用和依赖注入的通用 Python 解释见
`python_async_concurrency_foundations.md` 的 4.3.13、4.3.14 和 4.3.16。

#### 4.3.6 `_build_service` 的闭包接线与设计取舍

`_build_service(args, data_buffer)` 没有创建新的 orchestrator。真正的
`RolloutOrchestrator` 已由 `BringupService.async_start()` 创建，随后
`ensure_fa_started()` 把同一个对象引用挂到 slime 的 `args`：

```python
args.rh2_orchestrator = service.orchestrator
```

这里的 `args` 是 slime 使用的、可动态挂属性的 Namespace 类对象，不是普通
`dict`。当前它同时承载两类内容：

```text
静态训练/rollout 配置
  rollout_batch_size、rollout_temperature、rollout_top_p 等。

RH2 运行期接线
  rh2_orchestrator、rh2_sampling_params。
```

`_build_service()` 取回已挂载对象，并定义两个闭包：

```python
def group_source():
    groups = data_buffer.get_samples(1)
    ...

async def execute_member(member):
    return await orchestrator.generate(
        args,
        member,
        dict(sampling_params),
    )
```

因此真实引用图是：

```text
BringupService._instance.orchestrator --+
                                       +-> 同一个 RolloutOrchestrator 实例
args.rh2_orchestrator -----------------+
                                       |
execute_member 闭包 ------------------+

FaRolloutService
  -> group_source 闭包
       -> data_buffer
  -> execute_member 闭包
       -> orchestrator、args、sampling_params
```

把含有 `rh2_orchestrator` 属性的 `args` 再传给
`orchestrator.generate(args, ...)` 不会自动递归。Python 只是传递对象引用；
只有 `generate()` 的方法体主动再次调用 `args.rh2_orchestrator.generate()` 才会
递归，当前实现没有这样做。

这种接线让 `FaRolloutService` 只依赖两个窄能力：

```text
group_source()
  给出下一个 PromptGroup 的成员。

execute_member(member)
  执行一个 RolloutExecution 并返回叶链结果。
```

它不需要 import slime 的 `DataSource` 类型，也不需要理解
`BringupService`、Claude Code、SGLang 或评分系统如何构造。本地测试可以注入
假 `group_source` 和假 `execute_member`，只验证持续 worker、队列与组装逻辑。

三个对象没有合并成一个大 service，主要是因为它们负责不同时间尺度：

| 对象 | 生命周期与职责 |
|---|---|
| `BringupService` | 当前进程长期基础设施的创建、启动和接线 |
| `RolloutOrchestrator` | 一个 member/execution 从任务解析到清理的生命周期 |
| `FaRolloutService` | 跨许多 execution 和 batch 的持续派发、缓冲与收集 |

技术上也可以让 `FaRolloutService` 直接保存 `data_buffer`、`orchestrator`、`args`
和 `sampling_params` 字段，或者把全部逻辑并入 `BringupService`。当前闭包方案不是
Python 或 fully async 的强制要求；它选择的是更窄的依赖表面和更容易替换的测试
接口。全部并入 `BringupService` 会让一个类同时负责 HTTP adapter 线程、模型
捕获、评分基础设施、单 execution 生命周期和持续 batch 调度，容易演化成难以
独立测试和维护的 God Object（职责过多的巨型对象）。

当前实现也有需要诚实记录的过渡债务：

1. `args` 混合了静态配置与运行期服务引用，类型和 ownership 不够明确；
2. `BringupService._instance` 与模块变量 `_SERVICE` 构成两套进程内单例机制；
3. 闭包让真实依赖不如显式构造字段容易从类型签名发现；
4. `_SERVICE` 捕获首次调用时的 `args`、`data_buffer` 和采样参数，因此依赖
   “一个 RolloutManager 进程只服务一个训练 run/数据源”的当前运行假设；
5. `BringupService` 已经持有长期 runtime 基础设施，名称仍带有历史 bring-up
   色彩，低估了实际职责。

这些问题说明当前接线仍带有 slime 集成胶水性质，但不推翻职责拆分本身。未来
若要收敛接口，更清晰的方向是引入显式、带类型的 runtime dependencies/factory，
而不是把所有 ownership 重新并回一个巨型 service。闭包、浅拷贝、绑定方法和
可调用对象的通用解释见 `python_async_concurrency_foundations.md` 的 4.3.17。

#### 4.3.7 当前阅读断点

目前已经确认入口、对象装配、运行拓扑和并发单位。下一段从
`FaRolloutService.collect_batch()` 开始，逐行学习：

```text
_ensure_worker
  -> ContinuousExecutionWorker.run
  -> _task_source / member backlog
  -> in_flight execution Task
  -> BoundedDeliveryQueue
  -> interim/final PromptGroup collector
  -> completed backlog
  -> starvation、drain 与账目守恒
```

在读完这部分前，不把当前过渡 collector 的行为误写成最终 FA-2 assembler
契约，也不提前扩写本笔记的队列和反压结论。

### 4.4 环境物化、Docker sandbox 与 Claude Code harness

待记录。

### 4.5 Anthropic adapter、ModelCallProxy 与 SGLang

待记录。

### 4.6 capture、token provenance 与 trajectory projection

待记录。

### 4.7 clean grading、reward facts 与 EligibilityGate

待记录。

### 4.8 PromptGroup、batch admission 与 DP schedule

待记录。

### 4.9 slime train data、Megatron loss 与权重更新

待记录。

### 4.10 超时、取消、重试、崩溃恢复与熔断

待记录。

### 4.11 当前临时实现、未接通部分与演进路径

待记录。

## 5. 术语与疑问清单

待记录。
